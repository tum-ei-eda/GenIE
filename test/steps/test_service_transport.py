import httpx
import pytest

from genie.retargeting_service import RetargetingService, ServiceJob


def test_service_submit_observe_and_download(tmp_path):
    calls = []
    statuses = iter(["queued", "running", "finished"])
    def respond(request):
        calls.append(request)
        if request.method == "POST":
            body = request.read()
            for field in ("tag", "cdsl", "cpdsl", "config", "index", "hls"):
                assert f'name="{field}"'.encode() in body
            assert b"etiss_perf" in body
            return httpx.Response(200, json={"job_id": "job1", "token": "private"})
        assert request.url.params["token"] == "private"
        if request.url.path.endswith("/artifact"):
            return httpx.Response(200, content=b"compressed artifact")
        return httpx.Response(200, json={"status": next(statuses)})
    inputs = {}
    for field in ("cdsl", "cpdsl", "config", "index", "hls"):
        path = tmp_path / field
        path.write_bytes(field.encode())
        inputs[field] = path
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with RetargetingService("http://service", client=client) as service:
            job = service.submit("etiss_perf", **inputs)
            assert "private" not in repr(job)
            assert service.wait(job, poll_interval=0.001)["status"] == "finished"
            destination = service.download_artifact(job, tmp_path / "artifact.tar.zst")
            assert destination.read_bytes() == b"compressed artifact"
    assert sum(request.method == "POST" for request in calls) == 1


def test_service_timeout_resumes_existing_job_without_submission(monkeypatch):
    import genie.retargeting_service as module
    times = iter([0, 2, 3])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(times))
    statuses = iter(["running", "finished"])
    def respond(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"status": next(statuses)})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        service = RetargetingService("http://service", client=client)
        job = ServiceJob("existing", "private")
        with pytest.raises(TimeoutError, match="resume observation"):
            service.wait(job, timeout=1)
        assert service.wait(job)["status"] == "finished"


def test_service_failure_does_not_download_or_expose_token():
    def respond(request):
        assert request.url.path == "/jobs/existing"
        return httpx.Response(200, json={"status": "failed", "error": "private server details"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        service = RetargetingService("http://service", client=client)
        with pytest.raises(RuntimeError, match="failed") as error:
            service.wait(ServiceJob("existing", "secret"))
        assert "secret" not in str(error.value)


def test_failed_artifact_download_preserves_existing_file(tmp_path):
    def respond(request):
        return httpx.Response(404)
    destination = tmp_path / "artifact.tar.zst"
    destination.write_bytes(b"existing")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        service = RetargetingService("http://service", client=client)
        with pytest.raises(httpx.HTTPStatusError):
            service.download_artifact(ServiceJob("job", "token"), destination)
    assert destination.read_bytes() == b"existing"
    assert list(tmp_path.iterdir()) == [destination]


def test_perfsim_requires_schedule_inputs_before_http():
    with RetargetingService("http://service") as service:
        with pytest.raises(ValueError, match="index and hls"):
            service.submit("etiss_perf", cdsl="missing", cpdsl="missing", config="missing")


def test_service_log_download_is_a_finite_snapshot(tmp_path):
    def respond(request):
        assert request.url.path == "/jobs/job/logs"
        assert request.url.params["stream"] == "false"
        assert request.url.params["token"] == "private"
        return httpx.Response(200, content=b"worker diagnostics\n")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        service = RetargetingService("http://service", client=client)
        log = service.download_logs(ServiceJob("job", "private"), tmp_path / "worker.log")
    assert log.read_text() == "worker diagnostics\n"
