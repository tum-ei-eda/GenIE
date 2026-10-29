import json
from pathlib import Path
from types import SimpleNamespace

from git import Repo
import pandas as pd
import pytest

from genie.steps.iss import iss_target
from genie.steps.mlonmcu import Bench, ISEBench, ISETrace
from genie.steps.spike import validate_plugin
from genie.steps.utils import clone


def plugin(tmp_path):
    library = tmp_path / "libextension.so"
    library.write_bytes(b"example-plugin")
    manifest = tmp_path / "spike_plugin.json"
    manifest.write_text(json.dumps({"schema": 1, "core": "XIsaacCore", "extlibs": [library.name],
                                    "extension_names": ["m2_XIsaacCore"]}))
    return manifest


def test_pinned_clone_refresh_keeps_selected_revision(tmp_path):
    origin = Repo.init(tmp_path / "origin")
    source = Path(origin.working_tree_dir) / "version.txt"
    source.write_text("pinned")
    origin.index.add(["version.txt"])
    pin = origin.index.commit("pinned revision").hexsha
    destination = tmp_path / "clone with spaces"
    clone(str(origin.working_tree_dir), destination, branch=pin)
    source.write_text("newer")
    origin.index.add(["version.txt"])
    origin.index.commit("upstream moved")
    clone(str(origin.working_tree_dir), destination, branch=pin, refresh=True)
    assert Repo(destination).head.commit.hexsha == pin
    assert (destination / "version.txt").read_text() == "pinned"


@pytest.mark.parametrize("runtime,target", [("htif", "spike_bm"), ("pk", "spike_pk")])
def test_spike_runtime_and_plugin_reach_mlonmcu(tmp_path, runtime, target):
    step = object.__new__(Bench)
    step.config = {var.name: var.default for var in step.config_vars}
    step.config.update(ISS="spike", TARGET="spike", SPIKE_RUNTIME=runtime,
                       SPIKE_EXE="/opt/matching-spike", SPIKE_PK="/opt/pk", ISAAC_GNU_INSTALL_DIR="/opt/gnu")
    cfg = step.get_mlonmcu_config()
    cfg["arch"] = "rv64im" if runtime == "pk" else "rv32im"
    manifest = plugin(tmp_path)
    args = step.get_mlonmcu_args(tmp_path, "run", "embench_iot/crc32", "probe", **cfg,
                                spike_plugin_manifest=manifest)
    assert args[args.index("--target") + 1] == target
    assert f"{target}.plugin_manifest={manifest}" in args
    assert f"{target}.legacy=false" in args
    assert "spike.exe=/opt/matching-spike" in args
    assert f"riscv_gcc_rv{64 if runtime == 'pk' else 32}.install_dir=/opt/gnu" in args
    assert not any("etiss" in str(arg) for arg in args)
    (tmp_path / "libextension.so").unlink()
    with pytest.raises(FileNotFoundError):
        validate_plugin(manifest)


@pytest.mark.parametrize("cls", [ISEBench, ISETrace])
def test_spike_measurements_use_stage_plugin_without_etiss_state(tmp_path, cls):
    step = object.__new__(cls)
    step.config = {var.name: var.default for var in step.config_vars}
    step.config.update(ISS="spike", TARGET="spike_bm", BENCH="embench_iot/crc32")
    step.in_stage = "final"
    step.extract_env = lambda kwargs: ({}, {})
    manifest = plugin(tmp_path)
    names = tmp_path / "names.csv"
    pd.DataFrame({"instr_lower": ["custom0", "custom1"]}).to_csv(names, index=False)
    state = SimpleNamespace(paths={"final.spike.plugin_manifest": manifest,
        "final.seal5.install_dir": tmp_path, "final.names_csv": names, "final.workdir": tmp_path,
        "demo.dir": tmp_path, "mlonmcu.home": tmp_path, "mgclient.lib_dir": tmp_path},
        metrics={"bench.Target": "spike_bm", "bench.Arch": "rv32im"})
    calls = []
    def run(**kwargs):
        calls.append(kwargs)
        return {}, {}
    step.run_mlonmcu_helper = run
    step.run(state)
    assert calls
    for call in calls:
        assert call["overrides"]["spike_plugin_manifest"] == manifest
        assert "etissvp_script" not in call["overrides"]


def test_invalid_iss_selection_fails():
    with pytest.raises(ValueError, match="ISS must"):
        iss_target({"ISS": "unknown"})
    with pytest.raises(ValueError, match="SPIKE_RUNTIME"):
        iss_target({"ISS": "spike", "SPIKE_RUNTIME": "unknown"})


@pytest.mark.parametrize("runner,cycle_field", [("verilator", "cycles"), ("renode", "model_cycles")])
def test_cfu_evaluation_uses_selected_stage_compiler_and_ledger(tmp_path, runner, cycle_field):
    from genie.steps.cfu import Evaluate
    step = object.__new__(Evaluate)
    step.config = {var.name: var.default for var in step.config_vars}
    step.config.update(ISAAC_ENCODING_POLICY="cfu", CFU_RUNNER=runner,
        CFU_PLAYGROUND_DIR=str(tmp_path), ISAAC_GNU_INSTALL_DIR=str(tmp_path), BENCH="embench_iot/crc32",
        ARCH="rv32im_zicsr_zifencei", ABI="ilp32", FPU="none")
    step.in_stage = "final"
    step.step_dir = str(tmp_path / "step")
    step.extract_env = lambda kwargs: ({}, {})
    index, ledger = tmp_path / "selected.yml", tmp_path / "manifest.json"
    index.write_text("candidates: []")
    ledger.write_text("{}")
    compiler = tmp_path / "selected-compiler"
    compiler.mkdir()
    state = SimpleNamespace(paths={"demo.dir": tmp_path, "mlonmcu.home": tmp_path,
        "final.index": index, "final.cfu.manifest": ledger, "final.seal5.install_dir": compiler})
    def execute(state, script, args, env, **kwargs):
        run = Path(args[args.index("--run-dir") + 1]) / "work"
        assert (run / "combined_index.yml").resolve() == index
        assert (run / "cfu_manifest.json").resolve() == ledger
        assert (run / "local/seal5/llvm_install").resolve() == compiler
        output = run / ("cfu_evaluation_combined" + ("_renode" if runner == "renode" else ""))
        output.mkdir()
        pd.DataFrame({"variant": ["baseline", "extended"], "validation": [True, True],
            cycle_field: [100, 80], "instructions": [50, 30], cycle_field + "_relative": [1, 0.8],
            "instructions_relative": [1, 0.6]}).to_csv(output / "compare.csv", index=False)
    step.run_script = execute
    _, metrics, paths = step.run(state)
    assert metrics[f"final.cfu.{cycle_field}_relative"] == 0.8
    assert paths["final.cfu.compare_csv"].is_file()
