from pathlib import Path
from genie.steps.asip_synthesis_adapter import run


def test_asip_adapter_uses_repository_paths_and_combines_reports(tmp_path, monkeypatch):
    demo = tmp_path / "demo with spaces"
    constraints = demo / "constraints/CVA5/cva5_top.sdc"
    constraints.parent.mkdir(parents=True)
    constraints.write_text("create_clock")
    (demo / "syn_nangate.tcl").write_text("synthesize")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    (rtl / "files.txt").write_text("top.sv\n")
    output = tmp_path / "synthesis"
    calls = []
    def execute(args, **kwargs):
        calls.append(args)
        if args[0] == "dc_shell":
            assert kwargs["env"]["ROOT_PATH"] == str(demo)
            assert kwargs["env"]["CONSTRAINTS_FILE"] == str(constraints)
            assert kwargs["env"]["TECHLIB_PATH"] == "/library"
            for name in ("report_area_hier.log", "report_timing.log"):
                (output / "log" / name).write_text("report")
        elif "parse_area_report.py" in args[2]:
            kwargs["stdout"].write("area\n10\n")
        else:
            kwargs["stdout"].write("delay\n2\n")
    monkeypatch.setattr("genie.steps.asip_synthesis_adapter.subprocess.run", execute)
    run([str(output), str(rtl), "CVA5", "nangate45", "20"],
        env={"GENIE_DEMO_DIR": str(demo), "TECHLIB_PATH": "/library"})
    assert (output / "metrics.csv").read_text().splitlines() == ["area,delay", "10,2"]
    assert len(calls) == 3
