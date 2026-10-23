"""Submit real CLI runs over HTTP and immediately monitor them on the same server."""
import json
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from genie.monitor import handler_for
from genie.web_runs import RunManager


class WebRunsTest(unittest.TestCase):
    def test_failed_stage_can_be_retried_without_starting_a_second_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunManager(tmp)
            result = manager.launch(dict(config_text=json.dumps({
                "meta": {"flow": ["Misc.VerifyConfig"]}, "BENCH": "invalid"
            })))
            root = manager.directory(result["id"])
            def finished():
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    data = manager.snapshot(root)
                    if "returncode" in data:
                        return data
                    time.sleep(.05)
                self.fail("CLI retry did not finish")
            first = finished()
            self.assertEqual(first["status"], "failed")
            self.assertTrue(first["can_resume"])
            old_directory = first["stages"][0]["directory"]
            manager.resume(result["id"])
            retry = finished()
            self.assertEqual(retry["status"], "failed")
            self.assertNotEqual(retry["stages"][0]["directory"], old_directory)
            self.assertTrue((root / old_directory / "state_in.json").is_file())
            self.assertEqual(len(manager.list()), 1)
            self.assertEqual(len(manager.metadata(root)["attempts"]), 1)

    def test_submit_monitor_switch_and_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {"meta": {"flow": ["Misc.VerifyConfig"]}, "BENCH": "invalid"}
            (workspace / "config.json").write_text(json.dumps(config))
            manager = RunManager(workspace)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(manager=manager))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def get(path):
                with urlopen(base + path, timeout=10) as response:
                    return json.load(response)

            def post(body, path="/api/runs", **headers):
                request = Request(base + path, data=json.dumps(body).encode(),
                                  headers={"Content-Type": "application/json", **headers})
                with urlopen(request, timeout=10) as response:
                    self.assertEqual(response.status, 201)
                    return json.load(response)

            def finished(run_id):
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    data = get("/api/status?run=" + run_id)
                    if "returncode" in data:
                        return data
                    time.sleep(0.05)
                self.fail("CLI job did not finish")

            try:
                self.assertEqual(get("/api/runs"), [])
                self.assertTrue(get("/api/app")["launch_enabled"])
                self.assertIn("config.json", get("/api/app")["configs"])
                success = post(dict(name="Successful run", config_path="config.json",
                                    overrides={"BENCH": "test/web"}, jobs=1))
                first = get("/api/status?run=" + success["id"])
                self.assertIn(first["status"], ("starting", "running", "completed"))
                completed = finished(success["id"])
                self.assertEqual(completed["status"], "completed")
                self.assertEqual(completed["progress"]["completed"], 1)
                self.assertEqual(completed["label"], "Successful run")
                resolved = get("/api/data?run=" + success["id"] + "&name=resolved.json")
                self.assertEqual(resolved["BENCH"], "test/web")
                logs = get("/api/logs?run=" + success["id"])["logs"]
                self.assertTrue(any(log["name"] == "cli.log" for log in logs))
                with urlopen(base + "/api/log?run=" + success["id"] + "&name=cli.log") as response:
                    self.assertIn(b"Flow complete", response.read())
                self.assertIsInstance(get("/api/runs")[0]["started"], (int, float))
                (workspace / "base.json").write_text(json.dumps({"meta": {"flow": ["Misc.VerifyConfig", "Misc.VerifyConfig"]}, "BENCH": "invalid"}))
                (workspace / "service.yml").write_text("BENCH: test/overlay\n")
                partial = post(dict(name="Continue test", config_paths=["base.json", "service.yml"], to="Misc.VerifyConfig"))
                paused = finished(partial["id"])
                self.assertEqual([s["status"] for s in paused["stages"]], ["completed", "skipped"])
                self.assertTrue(paused["can_resume"])
                first_stage = dict(paused["stages"][0])
                first_state = manager.directory(partial["id"]) / first_stage["directory"] / "state_out.json"
                saved_mtime = first_state.stat().st_mtime_ns
                post({}, path="/api/runs/" + partial["id"] + "/resume")
                resumed = finished(partial["id"])
                self.assertEqual([s["status"] for s in resumed["stages"]], ["completed", "completed"])
                self.assertEqual(resumed["stages"][0]["directory"], first_stage["directory"])
                self.assertEqual(resumed["stages"][0]["elapsed"], first_stage["elapsed"])
                self.assertEqual(first_state.stat().st_mtime_ns, saved_mtime)
                self.assertFalse(resumed["can_resume"])
                self.assertEqual(get("/api/data?run=" + partial["id"] + "&name=resolved.json")["BENCH"], "test/overlay")
                with self.assertRaises(HTTPError) as caught:
                    post({}, path="/api/runs/" + partial["id"] + "/resume")
                self.assertEqual(caught.exception.code, 400)
                # Missing required config fails before the runner creates monitor.json.
                failed = post(dict(name="Invalid config", config_text='{"meta":{"flow":["Misc.VerifyConfig"]}}'))
                failure = finished(failed["id"])
                self.assertEqual(failure["status"], "failed")
                self.assertNotEqual(failure["returncode"], 0)
                self.assertEqual(failure["stages"], [])
                self.assertTrue(get("/api/logs?run=" + failed["id"])["logs"])
                self.assertEqual(get("/api/status?run=" + success["id"])["status"], "completed")
                restored = RunManager(workspace)
                self.assertEqual(len(restored.list()), 3)
                self.assertEqual(restored.snapshot(restored.directory(success["id"]))["status"], "completed")
                self.assertEqual(restored.snapshot(restored.directory(failed["id"]))["status"], "failed")
                for body in (dict(config_path="../outside.json"), dict(config_path="config.json", jobs=0),
                             dict(config_text="not json"), dict(config_text="[]"), dict(config_path="config.json", overrides=[])):
                    with self.assertRaises(HTTPError) as caught:
                        post(body)
                    self.assertEqual(caught.exception.code, 400)
                with self.assertRaises(HTTPError) as caught:
                    post(dict(config_path="config.json"), Origin="https://unrelated.example")
                self.assertEqual(caught.exception.code, 403)
                with self.assertRaises(HTTPError):
                    get("/api/status?run=../../")
                self.assertEqual(len(get("/api/runs")), 3)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
                with manager.lock:
                    processes = list(manager.processes.values())
                for process in processes:
                    process.wait(timeout=20)


if __name__ == "__main__":
    unittest.main()
