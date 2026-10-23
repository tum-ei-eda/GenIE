"""Launch CLI jobs and retain their run locations for the monitor web app."""
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path


class RunManager:
    def __init__(self, workspace, runs_dir=None, attached=None):
        self.workspace = Path(workspace).resolve()
        self.runs_dir = Path(runs_dir or self.workspace / ".genie-web-runs").resolve()
        self.attached = Path(attached).resolve() if attached else None
        self.processes = {}
        self.lock = threading.RLock()

    def app(self):
        configs = []
        for folder in (self.workspace, self.workspace / "cfg"):
            if folder.is_dir():
                configs.extend(str(p.relative_to(self.workspace)) for p in folder.iterdir()
                               if p.is_file() and p.suffix in (".json", ".yml", ".yaml"))
        return dict(workspace=str(self.workspace), configs=sorted(configs))

    def directory(self, run_id):
        if run_id in ("", "attached") and self.attached:
            return self.attached
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ValueError("Unknown run")
        job = self.runs_dir / run_id
        if not (job / "job.json").is_file() or not job.resolve().is_relative_to(self.runs_dir):
            raise ValueError("Unknown run")
        return job / "run"

    def metadata(self, root):
        if self.attached and root == self.attached:
            return None
        return json.loads((root.parent / "job.json").read_text())

    @staticmethod
    def save(job, data):
        temporary = job / "job.json.tmp"
        temporary.write_text(json.dumps(data), encoding="utf8")
        temporary.replace(job / "job.json")

    def snapshot(self, root):
        meta = self.metadata(root)
        try:
            data = json.loads((root / "monitor.json").read_text())
        except FileNotFoundError:
            if meta is None:
                raise
            data = dict(name=meta["name"], status="starting", started=meta["started"], stages=[])
        if meta:
            if "returncode" not in meta and data.get("heartbeat", 0) < meta.get("attempt_started", meta["started"]):
                data = dict(name=meta["name"], status="starting", started=meta["started"], stages=[])
            data["label"] = meta["name"]
            data["created"] = meta["started"]
            data["can_resume"] = "returncode" in meta and self.resume_step(data, meta) is not None
            if "returncode" in meta:
                data["returncode"] = meta["returncode"]
                if meta["returncode"] != 0 or data["status"] in ("starting", "running"):
                    data.update(status="failed", finished=meta["finished"],
                                error=f"CLI exited with code {meta['returncode']}. See the flow log for details.")
                    for stage in data["stages"]:
                        if stage["status"] == "running":
                            stage.update(status="failed", finished=meta["finished"])
            elif data["status"] == "starting":
                with self.lock:
                    observed = root.parent.name in self.processes
                if not observed and time.time() - data["started"] > 15:
                    data.update(status="unresponsive", error="Runner startup is no longer observable. See the flow log.")
        if data["status"] == "running" and time.time() - data.get("heartbeat", 0) > 15:
            data.update(status="unresponsive", error="No recent heartbeat. The runner may have stopped or become unavailable.")
        return data

    def list(self):
        entries = []
        if self.attached:
            entries.append(("attached", self.attached))
        if self.runs_dir.is_dir():
            entries.extend((job.name, job / "run") for job in self.runs_dir.iterdir()
                           if re.fullmatch(r"[0-9a-f]{32}", job.name) and (job / "job.json").is_file())
        result = []
        for run_id, root in entries:
            try:
                data = self.snapshot(root)
                result.append(dict(id=run_id, name=data.get("label", data["name"]), status=data["status"], started=data.get("created", data["started"])))
            except (OSError, ValueError, KeyError):
                if run_id == "attached":
                    result.append(dict(id=run_id, name=root.name, status="waiting"))
        return sorted(result, key=lambda run: (run.get("started", float("-inf")), run["id"]), reverse=True)

    def console(self, root):
        if self.metadata(root) is not None:
            return root.parent / "cli.log"
        return None

    def launch(self, request):
        if not isinstance(request, dict):
            raise ValueError("Expected a run form object")
        if not isinstance(request.get("name", ""), str):
            raise ValueError("Run name must be text")
        name = request.get("name", "").strip() or time.strftime("Run %Y-%m-%d %H:%M:%S")
        if len(name) > 120:
            raise ValueError("Run name must be at most 120 characters")
        config_text = request.get("config_text", "")
        config_path = request.get("config_paths", request.get("config_path", ""))
        if isinstance(config_path, list):
            if not all(isinstance(value, str) for value in config_path):
                raise ValueError("Configuration paths must be text")
            config_paths = [value.strip() for value in config_path if value.strip()]
        elif isinstance(config_path, str):
            config_paths = [value.strip() for value in config_path.splitlines() if value.strip()]
        else:
            raise ValueError("Configuration paths must be a list or one path per line")
        config_path = "\n".join(config_paths)
        if not isinstance(config_text, str) or not isinstance(config_path, str):
            raise ValueError("Configuration must be text")
        if config_text.strip() and config_path.strip():
            raise ValueError("Choose a configuration path or pasted JSON, not both")
        inline = None
        if config_text.strip():
            inline = json.loads(config_text)
            if not isinstance(inline, dict):
                raise ValueError("Configuration JSON must be an object")
        else:
            paths = []
            if not config_paths:
                raise ValueError("Choose at least one configuration file")
            for config in config_paths:
                path = (self.workspace / config).resolve()
                if not path.is_relative_to(self.workspace) or not path.is_file():
                    raise ValueError("Choose existing configuration files within the workspace")
                if path.suffix not in (".json", ".yaml", ".yml"):
                    raise ValueError("Configuration must be JSON or YAML")
                paths.append(path)
        overrides = request.get("overrides", {})
        if not isinstance(overrides, dict) or any(not isinstance(k, str) or "=" in k for k in overrides):
            raise ValueError("Overrides must be a JSON object with configuration variable names")
        jobs = request.get("jobs")
        if jobs is not None and (type(jobs) is not int or not 1 <= jobs <= 1024):
            raise ValueError("Jobs must be an integer between 1 and 1024")
        controls = {}
        for field in ("from", "to", "skip"):
            controls[field] = request.get(field, "")
            if not isinstance(controls[field], str):
                raise ValueError("Step filters must be text")
        run_id = uuid.uuid4().hex
        job = self.runs_dir / run_id
        root = job / "run"
        root.mkdir(parents=True)
        if inline is not None:
            path = job / "submitted.json"
            path.write_text(json.dumps(inline, indent=2), encoding="utf8")
            paths = [path]
        command = [sys.executable, "-u", "-m", "genie", *map(str, paths), "--force-run-dir", str(root),
                   "--hide-progress-bar"]
        if inline is not None:
            command.extend(["--design-dir", str(self.workspace)])
        if jobs is not None:
            command.extend(["--jobs", str(jobs)])
        for key, value in overrides.items():
            command.extend(["--override-config", f"{key}={json.dumps(value)}"])
        for field in ("from", "to"):
            if controls[field]:
                command.extend(["--" + field, controls[field]])
        for step in controls["skip"].split(","):
            if step.strip():
                command.extend(["--skip", step.strip()])
        meta = dict(id=run_id, name=name, started=time.time(), configs=list(map(str, paths)), command=command)
        return self.start(job, meta)

    @staticmethod
    def resume_step(data, meta):
        stages = data["stages"]
        for stage in stages:
            if stage["status"] in ("failed", "interrupted", "running", "pending"):
                return stage["id"]
        if "--to" in meta["command"]:
            last = max((index for index, stage in enumerate(stages) if stage["status"] == "completed"), default=-1)
            if last + 1 < len(stages):
                return stages[last + 1]["id"]
        return None

    def resume(self, run_id):
        with self.lock:
            root = self.directory(run_id)
            meta = self.metadata(root)
            if meta is None:
                raise ValueError("Continue is available for runs created in this app")
            if "returncode" not in meta:
                raise ValueError("The previous CLI process must have exited before continuing")
            data = json.loads((root / "monitor.json").read_text())
            step = self.resume_step(data, meta)
            if step is None:
                raise ValueError("There are no unfinished stages to continue")
            # Use the exact resolved config and preceding state, rather than
            # accidentally loading output from a later deferred-error stage.
            resolved = root / "resolved.json"
            if not resolved.is_file():
                raise ValueError("No resolved configuration is available for this run")
            command = [sys.executable, "-u", "-m", "genie", str(resolved), "--force-run-dir", str(root),
                       "--hide-progress-bar", "--from", step]
            original = meta["command"]
            for index, value in enumerate(original[:-1]):
                if value in ("--jobs", "--skip"):
                    command.extend([value, original[index + 1]])
            target = next(i for i, stage in enumerate(data["stages"]) if stage["id"] == step)
            state = None
            for stage in reversed(data["stages"][:target + 1]):
                if "directory" not in stage:
                    continue
                directory = (root / stage["directory"]).resolve()
                if not directory.is_relative_to(root):
                    raise ValueError("Invalid stage directory")
                candidate = directory / ("state_in.json" if stage["id"] == step else "state_out.json")
                if candidate.is_file():
                    state = candidate
                    break
            if state is not None:
                command.extend(["--with-initial-state", str(state)])
            attempts = meta.setdefault("attempts", [])
            attempts.append(dict(started=meta.get("attempt_started", meta["started"]),
                                 finished=meta["finished"], returncode=meta["returncode"]))
            (root.parent / f"attempt-{len(attempts)}.monitor.json").write_text(json.dumps(data, indent=2))
            meta.pop("returncode", None)
            meta.pop("finished", None)
            meta["command"] = command
            return self.start(root.parent, meta, append=True)

    def start(self, job, meta, append=False):
        run_id, name = meta["id"], meta["name"]
        command = meta["command"]
        meta["attempt_started"] = time.time()
        self.save(job, meta)
        env = dict(os.environ)
        package_root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = package_root + os.pathsep + env.get("PYTHONPATH", "")
        try:
            with (job / "cli.log").open("ab" if append else "wb") as output:
                process = subprocess.Popen([sys.executable, "-u", "-m", "genie.web_runs", str(job)],
                                           cwd=self.workspace, env=env, stdout=output,
                                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                           start_new_session=True)
        except OSError as exc:
            meta.update(returncode=-1, finished=time.time())
            self.save(job, meta)
            (job / "cli.log").write_text(str(exc))
            return dict(id=run_id, name=name)
        with self.lock:
            self.processes[run_id] = process
        def wait():
            code = process.wait()
            with self.lock:
                if self.processes.get(run_id) is not process:
                    return  # A new attempt has already replaced this supervisor.
                # The supervisor persists the exit code even if this server stops.
                final = json.loads((job / "job.json").read_text())
                if "returncode" not in final:
                    final.update(returncode=code or -1, finished=time.time())
                    self.save(job, final)
                if self.processes.get(run_id) is process:
                    self.processes.pop(run_id, None)
        threading.Thread(target=wait, daemon=True).start()
        return dict(id=run_id, name=name)


def supervise(job):
    """Persist CLI completion independently of the HTTP server's lifetime."""
    job = Path(job)
    meta = json.loads((job / "job.json").read_text())
    try:
        result = subprocess.run(meta["command"], stdin=subprocess.DEVNULL)
        code = result.returncode
    except BaseException as exc:
        print(f"Could not execute CLI: {exc}", flush=True)
        code = -1
    meta.update(returncode=code, finished=time.time())
    RunManager.save(job, meta)
    return code


if __name__ == "__main__":
    sys.exit(supervise(sys.argv[1]))
