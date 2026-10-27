"""HTTP transport for the ISAAC retargeting service's job API.

Submission and observation are separate: a timeout never resubmits a job.
Artifact unpacking and GenIE stage-state publication belong to the caller.
"""
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import time
from urllib.parse import quote

import httpx


@dataclass(frozen=True, repr=False)
class ServiceJob:
    job_id: str
    token: str


class RetargetingService:
    def __init__(self, url, *, client=None, request_timeout=60.0):
        self.url = url.rstrip("/")
        self.client = client if client is not None else httpx.Client(timeout=request_timeout)
        self._owns_client = client is None

    def close(self):
        if self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def submit(self, tag, *, cdsl, cpdsl, config, index=None, hls=None):
        """Submit the API's required description/config files and optional PerfSim inputs."""
        if tag == "etiss_perf" and (index is None or hls is None):
            raise ValueError("etiss_perf requires index and hls uploads")
        inputs = {"cdsl": cdsl, "cpdsl": cpdsl, "config": config,
                  "index": index, "hls": hls}
        with ExitStack() as stack:
            files = {}
            for field, value in inputs.items():
                if value is not None:
                    path = Path(value)
                    files[field] = (path.name, stack.enter_context(path.open("rb")))
            response = self.client.post(f"{self.url}/jobs", data={"tag": tag}, files=files)
            response.raise_for_status()
            data = response.json()
        return ServiceJob(data["job_id"], data["token"])

    def _job_url(self, job, suffix=""):
        return f"{self.url}/jobs/{quote(job.job_id, safe='')}{suffix}"

    def status(self, job):
        response = self.client.get(self._job_url(job), params={"token": job.token})
        response.raise_for_status()
        return response.json()

    def wait(self, job, *, timeout=3600.0, poll_interval=5.0):
        """Observe an existing job; failures and timeouts leave the handle reusable."""
        if timeout <= 0 or poll_interval <= 0:
            raise ValueError("timeout and poll_interval must be positive")
        deadline = time.monotonic() + timeout
        while True:
            status = self.status(job)
            state = status["status"]
            if state == "finished":
                return status
            if state in ("failed", "cancelled", "canceled", "aborted"):
                raise RuntimeError(f"Retargeting job {job.job_id} ended with status {state}")
            if state not in ("queued", "running"):
                raise ValueError(f"Unknown retargeting job status: {state}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Retargeting job {job.job_id} is still {state}; resume observation")
            time.sleep(min(poll_interval, remaining))

    def download_artifact(self, job, destination):
        """Stream a completed artifact and publish it only after successful transfer."""
        return self._download(job, destination, "/artifact")

    def download_logs(self, job, destination):
        """Fetch a finite worker-log snapshot, including for failed/running jobs."""
        return self._download(job, destination, "/logs", {"stream": "false"})

    def _download(self, job, destination, suffix, parameters=None):
        import tempfile

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with self.client.stream("GET", self._job_url(job, suffix),
                                    params={"token": job.token, **(parameters or {})}) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                    temporary = Path(output.name)
                    for chunk in response.iter_bytes():
                        output.write(chunk)
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return destination


def extract_artifact(archive, destination):
    """Extract the worker's output/ archive using tarfile's data filter."""
    import shutil
    import subprocess
    import tarfile
    import tempfile

    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        temporary = Path(temporary)
        unpacked = temporary / "unpacked"
        unpacked.mkdir()
        with (temporary / "artifact.tar").open("wb") as output:
            subprocess.run(["zstd", "-d", "-c", str(archive)], stdout=output, check=True)
        with tarfile.open(temporary / "artifact.tar") as source:
            for member in source.getmembers():
                if not member.name.startswith("output/") and member.name.rstrip("/") != "output":
                    raise ValueError(f"Unexpected service artifact path: {member.name}")
            source.extractall(unpacked, filter="data")
        output = unpacked / "output"
        if not output.is_dir() or output.is_symlink():
            raise ValueError("Service artifact requires an output directory")
        shutil.move(str(output), destination)
    return destination
