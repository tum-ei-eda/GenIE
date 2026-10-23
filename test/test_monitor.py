"""Monitor contracts, including a real CLI flow and HTTP log reads."""
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

from genie.monitor import RunStatus, handler_for, PAGE, with_progress


class MonitorTest(unittest.TestCase):
    def test_progress_and_durations(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            steps = [SimpleNamespace(id=str(i), name=str(i)) for i in range(4)]
            with patch("genie.monitor.time.time", return_value=100):
                status = RunStatus(root, "Timing", steps)
            try:
                with patch("genie.monitor.time.time", return_value=102):
                    status.stage("0", "running")
                with patch("genie.monitor.time.time", return_value=107):
                    status.stage("0", "completed")
                    status.stage("1", "skipped")
                    status.stage("2", "running")
                data = with_progress(json.loads((root / "monitor.json").read_text()), root, now=110)
                self.assertEqual(data["progress"], dict(total=4, completed=1, skipped=1))
                self.assertEqual(data["elapsed"], 10)
                self.assertEqual([s["elapsed"] for s in data["stages"]], [5, None, 3, None])
                with patch("genie.monitor.time.time", return_value=112):
                    status.finish("failed", "failed stage")
                data = with_progress(json.loads((root / "monitor.json").read_text()), root, now=999)
                self.assertEqual(data["elapsed"], 12)
                self.assertEqual(data["stages"][2]["elapsed"], 5)
            finally:
                status.stopped.set()
                status.heartbeat_thread.join()
            (root / "old").mkdir()
            (root / "old/runtime.txt").write_text("01:02:03.250")
            legacy = dict(status="completed", started=100, finished=200,
                          stages=[dict(status="completed", directory="old")])
            self.assertEqual(with_progress(legacy, root)["stages"][0]["elapsed"], 3723.25)

    def test_snapshot_and_http_log_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            # Harmless fixture outside the served run: symlinks must not expose it.
            outside_file = Path(outside) / "private-fixture.txt"
            outside_file.write_text("This fixture must never be served.")
            status = RunStatus(root, "Test", [SimpleNamespace(id="a", name="A")])
            stage_dir = root / "1-a"
            stage_dir.mkdir()
            (stage_dir / "tool.log").write_text("x" * 100000 + "LIVE END")
            (stage_dir / "escape.log").symlink_to(outside_file)
            (stage_dir / "config.json").write_text('{"nested": {"value": 42}, "text": "<script>"}')
            (root / "resolved.json").write_text('{"BENCH": "test/data"}')
            (stage_dir / "state_in.json").symlink_to(outside_file)
            status.stage("a", "running", stage_dir)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(root))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                def get(path):
                    with urlopen(base + path) as response:
                        return json.load(response)
                self.assertEqual(get("/api/status")["stages"][0]["status"], "running")
                self.assertEqual(get("/api/status")["stages"][0]["number"], 1)
                self.assertEqual(get("/api/files?stage=a"), ["config.json"])
                self.assertEqual(get("/api/files"), ["resolved.json"])
                self.assertEqual(get("/api/data?stage=a&name=config.json")["nested"]["value"], 42)
                self.assertEqual(get("/api/data?name=resolved.json")["BENCH"], "test/data")
                for path in ("/api/data?stage=a&name=state_in.json", "/api/data?name=../resolved.json",
                             "/api/data?name=monitor.json", "/api/files?stage=unknown"):
                    with self.assertRaises(HTTPError):
                        get(path)
                logs = get("/api/logs?stage=a")["logs"]
                self.assertEqual(len(logs), 1)
                self.assertTrue(logs[0]["text"].endswith("LIVE END"))
                self.assertEqual(len(logs[0]["text"]), 65536)
                with (stage_dir / "tool.log").open("a") as stream:
                    stream.write(" UPDATE")
                self.assertTrue(get("/api/logs?stage=a")["logs"][0]["text"].endswith(" UPDATE"))
                with urlopen(base + "/api/log?stage=a&name=tool.log") as response:
                    self.assertEqual(len(response.read()), 100015)
                with self.assertRaises(HTTPError):
                    get("/api/log?stage=a&name=escape.log")
                with self.assertRaises(HTTPError):
                    get("/api/logs?stage=../../etc")
                status.stopped.set()
                status.heartbeat_thread.join()
                data = json.loads((root / "monitor.json").read_text())
                data["heartbeat"] = time.time() - 60
                (root / "monitor.json").write_text(json.dumps(data))
                self.assertEqual(get("/api/status")["status"], "unresponsive")
                status.finish("failed", "test failure")
                self.assertEqual(get("/api/status")["stages"][0]["status"], "failed")
                with urlopen(base) as response:
                    self.assertIn(b"Live monitor", response.read())
                self.assertNotIn('<details open', PAGE)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()

    def test_live_subprocess_output_before_stage_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "run.py"
            script.write_text("""
import sys
from genie.steps import GenIEStep
from genie.flows import SequentialGenIEFlow
class Live(GenIEStep):
    id = "Test.Live"
    name = long_name = "Live subprocess"
    inputs = []
    outputs = []
    config_vars = []
    def run(self, state_in, **kwargs):
        self.run_subprocess([sys.executable, "-u", "-c", "import time; print('FIRST', flush=True); time.sleep(3); print('LAST', flush=True)"])
        return {}, {}, {}
class Flow(SequentialGenIEFlow):
    Steps = [Live, Live]
Flow({"BENCH": "test/live"}, design_dir=sys.argv[1]).start(tag="live")
""")
            import os
            env = dict(os.environ, PYTHONPATH=str(Path.cwd()))
            process = subprocess.Popen([sys.executable, str(script), tmp], env=env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                snapshot_path = Path(tmp) / "runs/live/monitor.json"
                deadline = time.monotonic() + 15
                observed = False
                while time.monotonic() < deadline and process.poll() is None:
                    if snapshot_path.exists():
                        snapshot = json.loads(snapshot_path.read_text())
                        first = snapshot["stages"][0]
                        if "directory" in first:
                            log = snapshot_path.parent / first["directory"] / "test-live.log"
                            if log.exists() and "FIRST" in log.read_text():
                                self.assertEqual(first["status"], "running")
                                self.assertEqual(snapshot["stages"][1]["status"], "pending")
                                observed = True
                                break
                    time.sleep(0.05)
                self.assertTrue(observed, "Did not observe subprocess output while stage was running")
                _, errors = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, errors.decode())
                self.assertEqual([s["status"] for s in json.loads(snapshot_path.read_text())["stages"]],
                                 ["completed", "completed"])
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                process.stderr.close()

    def test_real_cli_completed_failed_and_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            for tag, bench, extra, expected in [
                ("success", "test/smoke", [], "completed"),
                ("failure", "invalid", [], "failed"),
                ("skip", "test/smoke", ["--skip", "Misc.VerifyConfig"], "skipped"),
            ]:
                config.write_text(json.dumps({"meta": {"flow": ["Misc.VerifyConfig"]}, "BENCH": bench}))
                result = subprocess.run([sys.executable, "-m", "genie", str(config), "--run-tag", tag,
                                         "--hide-progress-bar", *extra], capture_output=True, text=True)
                snapshot = json.loads((Path(tmp) / "runs" / tag / "monitor.json").read_text())
                self.assertEqual(snapshot["stages"][0]["status"], expected, result.stdout + result.stderr)
                self.assertEqual(result.returncode == 0, expected != "failed")
                if expected == "completed":
                    self.assertTrue((Path(tmp) / "runs" / tag / "1-misc-verifyconfig" / "stage.log").is_file())


if __name__ == "__main__":
    unittest.main()
