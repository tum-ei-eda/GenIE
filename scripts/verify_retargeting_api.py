#!/usr/bin/env python3
"""Check GenIE's client against an actual service checkout using an isolated ASGI app.

Requires that checkout's API requirements plus httpx. No running service or
worker is changed; Redis is replaced with a queue mock and jobs use a temp dir.
"""
import argparse
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import MagicMock, patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service_source", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.service_source.resolve()))
    from api import api
    from fastapi.testclient import TestClient
    import httpx

    spec = importlib.util.spec_from_file_location(
        "genie_service_transport", Path(__file__).resolve().parents[1] / "genie/retargeting_service.py")
    transport = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = transport
    spec.loader.exec_module(transport)
    redis = MagicMock()
    redis.get.return_value = None
    redis.keys.return_value = []
    redis.scan_iter.return_value = iter(())
    redis.lrange.return_value = []
    redis.llen.return_value = 0
    with tempfile.TemporaryDirectory(prefix="genie-api-check-") as temporary:
        root = Path(temporary)
        jobs = root / "jobs"
        cdsl, cpdsl, config = (root / name for name in ("Core.core_desc", "Instructions.core_desc", "config.yaml"))
        cdsl.write_text(f'import "{cpdsl}"\nCore Demo provides Extension {{}}\n')
        cpdsl.write_text("InstructionSet Extension {}\n")
        config.write_text("{}\n")
        index, hls = root / "index.yaml", root / "hls.tar.gz"
        index.write_text("candidates: []\n")
        with tarfile.open(hls, "w:gz"):
            pass
        with patch.object(api, "r", redis), patch.object(api, "JOBS_DIR", str(jobs)), TestClient(api.app) as client:
            with transport.RetargetingService("http://testserver", client=client) as service:
                assert service.health()["ready"]
                service.workers()
                for tag in ("llvm", "etiss", "etiss_perf", "spike"):
                    job = service.submit(tag, cdsl=cdsl, cpdsl=cpdsl, config=config,
                                         **({"index": index, "hls": hls} if tag == "etiss_perf" else {}))
                    base = jobs / job.job_id
                    assert service.status(job)["status"] == "queued"
                    assert b'import "Instructions.core_desc"' in (base / "input/Core.core_desc").read_bytes()
                    try:
                        service.wait(job, timeout=0.001, poll_interval=0.001)
                    except TimeoutError:
                        pass
                    else:
                        raise AssertionError("Queued jobs must time out without resubmission")
                    assert redis.rpush.call_count == ("llvm", "etiss", "etiss_perf", "spike").index(tag) + 1
                    (base / "logs.txt").write_text("worker log snapshot\n")
                    assert service.download_logs(job, root / "worker.log").read_text() == "worker log snapshot\n"
                    status = api.load_status(job.job_id)
                    status["status"] = "finished"
                    api.save_status(job.job_id, status)
                    assert service.wait(job)["status"] == "finished"
                    tar = root / "artifact.tar"
                    with tarfile.open(tar, "w") as output:
                        info = tarfile.TarInfo("output/proof.txt")
                        info.size = len(tag)
                        output.addfile(info, io.BytesIO(tag.encode()))
                    with (base / "artifact.tar.zst").open("wb") as output:
                        subprocess.run(["zstd", "-q", "-c", str(tar)], stdout=output, check=True)
                    archive = service.download_artifact(job, root / "artifact.tar.zst")
                    destination = root / (tag + "-output")
                    transport.extract_artifact(archive, destination)
                    assert (destination / "proof.txt").read_text() == tag
                    try:
                        service.status(transport.ServiceJob(job.job_id, "wrong-token"))
                    except httpx.HTTPStatusError as error:
                        assert error.response.status_code == 403
                    else:
                        raise AssertionError("The API must reject an invalid token")
                job = service.submit("spike", cdsl=cdsl, cpdsl=cpdsl, config=config)
                service.abort(job)
                assert service.status(job)["status"] == "aborted"
                try:
                    service.wait(job)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("An aborted job must fail observation")
    print("API contract passed: llvm, etiss, etiss_perf, spike; tokens, timeout/resume, logs, artifacts and abort")


if __name__ == "__main__":
    main()
