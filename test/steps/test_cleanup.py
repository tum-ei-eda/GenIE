from types import SimpleNamespace
import pytest
from genie.steps.misc import CleanupTempFiles


def test_cleanup_removes_only_declared_temporaries(tmp_path):
    step = object.__new__(CleanupTempFiles)
    step.step_dir = str(tmp_path / "cleanup")
    step.config = {"CLEANUP_ENABLE": True}
    temporary = tmp_path / "build"
    temporary.mkdir()
    (temporary / "object.o").touch()
    report = tmp_path / "report.csv"
    report.write_text("metrics")
    state = SimpleNamespace(paths={"temporary.build": temporary, "metrics_csv": report})
    _, metrics, paths = step.run(state)
    assert not temporary.exists()
    assert report.read_text() == "metrics"
    assert metrics["cleanup.removed_count"] == 1
    assert paths == {"temporary.build": None}


def test_cleanup_preflights_all_targets_before_deleting(tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    build = root / "build"
    build.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    step = object.__new__(CleanupTempFiles)
    step.step_dir = str(root / "cleanup")
    step.config = {"CLEANUP_ENABLE": True}
    state = SimpleNamespace(paths={"temporary.build": build, "temporary.external": external})
    with pytest.raises(ValueError):
        step.run(state)
    assert build.is_dir()
    assert external.is_dir()


def test_cleanup_rejects_permanent_artifact_inside_target(tmp_path):
    step = object.__new__(CleanupTempFiles)
    step.step_dir = str(tmp_path / "cleanup")
    step.config = {"CLEANUP_ENABLE": True}
    build = tmp_path / "build"
    build.mkdir()
    report = build / "metrics.csv"
    report.touch()
    with pytest.raises(ValueError):
        step.run(SimpleNamespace(paths={"temporary.build": build, "report": report}))
    assert report.exists()
