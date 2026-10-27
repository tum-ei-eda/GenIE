import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("content,code,status", [(b"script", 0, "match"),
    (b"old script", 0, "different"), (b"", 1, "unavailable")])
def test_sync_audit_compares_bytes_and_reports_missing_script(tmp_path, content, code, status):
    path = Path(__file__).parents[2] / "scripts/audit_retargeting_sync.py"
    spec = importlib.util.spec_from_file_location("sync_audit", path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    source = tmp_path / "source.sh"
    source.write_bytes(b"script")
    def run(command, **kwargs):
        assert command == ["docker", "exec", "worker", "cat", "/scripts/run.sh"]
        return SimpleNamespace(returncode=code, stdout=content)
    row = audit.compare_file(source, "worker", "/scripts/run.sh", runner=run)
    assert row["status"] == status
    assert source.read_bytes() == b"script"
