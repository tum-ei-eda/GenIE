import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from genie.prototype import PROTOTYPE_STEPS


def test_each_phase_has_concrete_python_steps():
    for name, steps in PROTOTYPE_STEPS.items():
        assert name.startswith("flow_") and name.endswith(".sh")
        assert steps
        for step in steps:
            step.assert_concrete()


def test_phase_inventory_matches_reference_checkout():
    source = os.environ.get("GENIE_DEMO_SRC")
    if not source:
        pytest.skip("Set GENIE_DEMO_SRC to audit prototype script coverage")
    scripts = {path.name for path in (Path(source) / "scripts").glob("flow_*.sh")}
    assert set(PROTOTYPE_STEPS) == scripts


def test_python_phase_cli_generates_real_report(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("BENCH: embench_iot/crc32\n")
    result = subprocess.run([sys.executable, "-m", "genie.prototype", "flow_report.sh", str(config),
        "-c", "BENCH=embench_iot/crc32", "--design-dir", str(tmp_path)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    reports = list(tmp_path.glob("runs/*/*/ci_report.md"))
    assert len(reports) == 1
    assert "GenIE run report" in reports[0].read_text()


@pytest.mark.parametrize("phase,stage,destination", [
    ("flow_filter.sh", "filtered", "filtered2"),
    ("flow_select.sh", "filtered", "filtered_selected"),
    ("flow_select.sh", "filtered2", "filtered2_selected"),
    ("flow_select_new.sh", "filtered2", "prelim"),
    ("flow_select_new.sh", "prelim", "final"),
    ("flow_select_new.sh", "prelim_filtered", "final"),
])
def test_phase_stage_transitions(phase, stage, destination):
    from genie.prototype import phase_steps
    step, = phase_steps(phase, stage)
    assert step.in_stage == stage
    assert step.out_stage == destination


def test_split_final_compiler_phase_and_reference_filter_skip():
    from genie.prototype import phase_steps
    step, = phase_steps("flow_seal5.sh", "final", splitted=True)
    assert step.in_stage == "final" and step.splitted is True
    assert phase_steps("flow_filter.sh", "filtered2") == []
    with pytest.raises(ValueError):
        phase_steps("flow_select.sh", "final")


def test_disabled_hls_phase_skips_all_artifact_consumers(tmp_path):
    config = tmp_path / 'disabled.yml'
    config.write_text('BENCH: embench_iot/crc32\nHLS_ENABLE: false\n')
    result = subprocess.run([sys.executable, '-m', 'genie.prototype', 'flow_hls.sh', str(config),
        '--design-dir', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(tmp_path.glob('runs/*/*/combined_locs.csv'))


@pytest.mark.parametrize("phase", ["flow_compare.sh", "flow_compare_perf.sh",
                                  "flow_retrace.sh", "flow_retrace_perf.sh"])
def test_build_arch_phase_preserves_stage_for_simulator(phase):
    from genie.prototype import phase_steps
    steps = phase_steps(phase, "filtered_selected", build_arch=True)
    assert steps[0].build_arch is True
    assert all(step.in_stage == "filtered_selected" for step in steps)


def test_build_arch_rejects_unrelated_phase():
    from genie.prototype import phase_steps
    with pytest.raises(ValueError, match="--build-arch"):
        phase_steps("flow_seal5.sh", build_arch=True)
