from pathlib import Path
import pytest

from genie.steps.mlonmcu import PerfSimBench, Bench
from genie.steps.isaac import RetargetPerfSim
from genie.flows import GenIEFlow


def test_perfsim_arguments_include_model_and_installation(tmp_path):
    step = object.__new__(PerfSimBench)
    step.config = {var.name: var.default for var in PerfSimBench.config_vars}
    config = step.get_mlonmcu_config()
    assert config["target"] == "etiss_perf"
    helper = tmp_path / "install/bin/run_helper.sh"
    args = step.get_mlonmcu_args(
        dest_dir=tmp_path, stage="run", bench_name="embench_iot/crc32", session_label="test",
        **config, etissvp_script=helper,
    )
    assert "perf_sim" in args
    assert "perf_sim.core=cv32e40pxisaac" in args
    assert f"etiss_perf.install_dir={helper.parent.parent}" in args
    assert f"etiss_perf.exe={helper.parent / 'bare_etiss_processor'}" in args


def test_iss_arguments_do_not_enable_perfsim(tmp_path):
    step = object.__new__(Bench)
    step.config = {var.name: var.default for var in Bench.config_vars}
    args = step.get_mlonmcu_args(dest_dir=tmp_path, stage="run", bench_name="test", session_label="test",
                                **step.get_mlonmcu_config())
    assert "perf_sim" not in args


def test_cross_benchmark_session_label(tmp_path):
    step = object.__new__(Bench)
    step.step_dir = str(tmp_path / "step")
    label = step.get_session_label(["embench_iot/crc32", "embench_iot/aha-mont64"], "run", "others")
    assert "crc32" in label and "aha-mont64" in label


def test_perfsim_flow_uses_perfsim_retargeting():
    flow = GenIEFlow.factory.get("PerfSimGenIEFlow")
    assert flow.Substitutions["ISAAC.RetargetISS"] is RetargetPerfSim


def test_perfsim_flow_generates_hls_before_retargeting():
    from genie.flows.default import PerfSimGenIEFlow
    ids = [step.id for step in PerfSimGenIEFlow.Steps]
    assert ids.index("ISAAC.GenerateETISSCore") < ids.index("ISAAC.RunHLS")
    assert ids.index("ISAAC.RunHLS") < ids.index("ISAAC.AssignHLSScore")
    assert ids.index("ISAAC.AssignHLSScore") < ids.index("ISAAC.RetargetPerfSim")


def test_perfsim_report_preserves_microarchitecture_column(tmp_path):
    step = object.__new__(PerfSimBench)
    step.config = {var.name: var.default for var in PerfSimBench.config_vars}
    args = step.get_mlonmcu_args(dest_dir=tmp_path, stage="run", bench_name="test",
                               session_label="test", **step.get_mlonmcu_config())
    assert "config2cols.limit=etiss_perf.final_arch,perf_sim.core" in args
    assert any("'config_perf_sim.core':'uArch'" in str(arg) for arg in args)


@pytest.mark.parametrize("build_arch", [False, True])
def test_perfsim_comparison_evaluates_all_microarchitectures(tmp_path, build_arch):
    from types import SimpleNamespace
    from genie.steps.mlonmcu import ISEPerfSimBench
    import pandas as pd
    install = tmp_path / "install"
    (install / "bin").mkdir(parents=True)
    (install / "bin/run_helper.sh").touch()
    names = tmp_path / "names.csv"
    pd.DataFrame({"instr_lower": ["custom0"]}).to_csv(names, index=False)
    uarchs = tmp_path / "uarchs.csv"
    pd.DataFrame({"uarch": ["fast", "small"]}).to_csv(uarchs, index=False)
    step = object.__new__(ISEPerfSimBench)
    step.in_stage = "filtered_selected" if build_arch else "initial"
    step.build_arch = build_arch
    step.config = {var.name: var.default for var in step.config_vars}
    step.extract_env = lambda kwargs: ({}, {})
    calls = []
    def run_helper(**kwargs):
        calls.append(kwargs)
        return {}, {}
    step.run_mlonmcu_helper = run_helper
    state = SimpleNamespace(paths={"mlonmcu.home": tmp_path, "demo.dir": tmp_path,
        "mgclient.lib_dir": tmp_path, "initial.names_csv": names,
        "initial.seal5.install_dir": install, "initial.etiss_perf.install_dir": install,
        "initial.etiss_perf.uarchs_csv": uarchs, "initial.etiss_perf.src_dir": tmp_path / "source"}, metrics={"bench.Arch": "rv32im"})
    if build_arch:
        state.paths["initial.seal5_splitted.install_dir"] = state.paths.pop("initial.seal5.install_dir")
        state.paths.update({key.replace("initial.", "filtered_selected."): value
                            for key, value in state.paths.items() if key.startswith("initial.")
                            and "seal5" not in key})
    step.run(state)
    full_arch = "rv32im_xisaaccustom0single" if build_arch else "rv32im_xisaac"
    assert calls[0]["overrides"]["config_gen"] == [
        {"etiss_perf.arch": "rv32im", "perf_sim.core": "fast"},
        {"etiss_perf.arch": full_arch, "perf_sim.core": "fast"},
        {"etiss_perf.arch": full_arch, "perf_sim.core": "small"}]
    assert calls[0]["overrides"]["compare_rows_to_compare"] == ["Run Instructions", "Run Cycles"]
    assert calls[0]["overrides"]["etiss_src_dir"] == tmp_path / "source"
    assert calls[1]["overrides"]["etiss_src_dir"] == tmp_path / "source"
    assert calls[1]["overrides"]["compare_rows_to_compare"] == ["ROM code"]



def test_filtered_retrace_reuses_initial_compiler(tmp_path):
    from types import SimpleNamespace
    from genie.steps.mlonmcu import ISETrace
    import pandas as pd
    compiler = tmp_path / "initial-compiler"
    compiler.mkdir()
    simulator = tmp_path / "selected-simulator"
    (simulator / "bin").mkdir(parents=True)
    (simulator / "bin/run_helper.sh").touch()
    names = tmp_path / "names.csv"
    pd.DataFrame({"instr_lower": ["custom1", "custom3"]}).to_csv(names, index=False)
    step = object.__new__(ISETrace)
    step.in_stage = "filtered"
    step.build_arch = True
    step.config = {var.name: var.default for var in step.config_vars}
    step.extract_env = lambda kwargs: ({}, {})
    calls = []
    def run_helper(**kwargs):
        calls.append(kwargs)
        return {}, {}
    step.run_mlonmcu_helper = run_helper
    step.run(SimpleNamespace(paths={"filtered.workdir": tmp_path,
        "filtered.names_csv": names, "initial.seal5_splitted.install_dir": compiler,
        "filtered.etiss.install_dir": simulator, "mlonmcu.home": tmp_path,
        "demo.dir": tmp_path, "mgclient.lib_dir": tmp_path}))
    overrides = calls[0]["overrides"]
    assert overrides["llvm_install_dir"] == compiler
    assert overrides["etissvp_script"] == simulator / "bin/run_helper.sh"
    assert overrides["arch"].endswith("_xisaaccustom1single_xisaaccustom3single")


def test_perfsim_uses_service_processor_wrapper(tmp_path):
    step = object.__new__(PerfSimBench)
    step.config = {var.name: var.default for var in PerfSimBench.config_vars}
    install = tmp_path / "install"
    (install / "bin").mkdir(parents=True)
    wrapper = install / "bin/genie_etiss_processor.py"
    wrapper.touch()
    args = step.get_mlonmcu_args(dest_dir=tmp_path, stage="run", bench_name="test",
        session_label="test", **step.get_mlonmcu_config(), etissvp_script=install / "bin/run_helper.sh")
    assert f"etiss_perf.exe={wrapper}" in args
