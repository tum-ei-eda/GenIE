from pathlib import Path
"""Exercise stage isolation and command contracts without external toolchains."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from genie.steps.candidates import AssignSeal5Score, ScoreCandidates, SortCandidates
from genie.steps.isaac import CreateSpecGraph


@pytest.mark.parametrize("kind,tool", [("ASIP", "ol2"), ("FPGA", "unknown")])
@pytest.mark.parametrize("setting", ["TOOL", "SEARCH_FMAX"])
def test_synthesis_rejects_unsupported_mode_before_reading_artifacts(kind, tool, setting):
    from genie.steps.hardware import RunASIPSynthesis, RunFPGASynthesis
    cls = RunASIPSynthesis if kind == "ASIP" else RunFPGASynthesis
    step = object.__new__(cls)
    step.config = {v.name: v.default for v in cls.config_vars}
    step.extract_env = lambda kwargs: ({}, {})
    step.config[f"{kind}_SYN_{setting}"] = tool if setting == "TOOL" else True
    with pytest.raises(ValueError, match=f"{kind}_SYN_{setting}"):
        step.run(SimpleNamespace())


def harness(cls, tmp_path, stage="filtered"):
    work = tmp_path / stage
    work.mkdir()
    index = work / "index.yml"
    index.write_text("{}")
    step = object.__new__(cls)
    step.in_stage = stage
    step.config = {"ENC_WEIGHT": 2.0, "UTIL_WEIGHT": 3.0, "CANDIDATE_SORT_BY": None}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    state = SimpleNamespace(paths={
        f"{stage}.index": index, f"{stage}.workdir": work,
        "demo.dir": tmp_path / "demo",
    }, metrics={})
    return step, state, work, index


@pytest.mark.parametrize("stage,flags", [
    ("initial", []), ("filtered", ["--filtered"]), ("final", ["--final"]),
    ("prelim", ["--prelim", "--util-weight", "3.0", "--enc-weight", "2.0"]),
])
def test_score_stage(tmp_path, stage, flags):
    step, state, work, index = harness(ScoreCandidates, tmp_path, stage)
    assert step.run(state) == ({}, {}, {})
    assert step.run_isaac_toolkit.call_args.args[0] == [
        "isaac_toolkit.utils.annotate_score", index, "--inplace", *flags,
    ]


def test_missing_producer_report_prevents_mutation(tmp_path):
    step, state, work, index = harness(AssignSeal5Score, tmp_path)
    state.paths["filtered.seal5.seal5_score_csv"] = work / "missing.csv"
    with pytest.raises(FileNotFoundError):
        step.run(state)
    step.run_isaac_toolkit.assert_not_called()


def test_sort_publishes_stage_names(tmp_path):
    step, state, work, index = harness(SortCandidates, tmp_path)
    def execute(args, **kwargs):
        if args[0].endswith("names_helper"):
            args[-1].write_text("name\nfoo\n")
    step.run_isaac_toolkit.side_effect = execute
    assert step.run(state)[2] == {"filtered.names_csv": work / "names.csv"}
    assert step.run_isaac_toolkit.call_args_list[0].args[0][-1] == "filtered_score"


def test_specialization_graph_is_created_and_published(tmp_path):
    step, state, work, index = harness(CreateSpecGraph, tmp_path)
    def execute(args, **kwargs):
        assert args == ["tool.detect_specializations", index, "--graph", work / "spec_graph.pkl", "--noop"]
        args[3].write_bytes(b"graph")
    step.run_isaac_toolkit.side_effect = execute
    assert step.run(state)[2] == {"filtered.spec_graph": work / "spec_graph.pkl"}


def test_specialization_missing_output_is_failure(tmp_path):
    step, state, work, index = harness(CreateSpecGraph, tmp_path)
    with pytest.raises(FileNotFoundError):
        step.run(state)


@pytest.mark.parametrize("topk,expected", [(0, 3), (2, 2), (10, 3)])
def test_select_index_preserves_source_and_metadata(tmp_path, topk, expected):
    import yaml
    from genie.steps.candidates import SelectCandidates

    step, state, work, index = harness(SelectCandidates, tmp_path, "filtered2")
    original = {"metadata": {"set": "test"}, "candidates": [
        {"id": 10 + i, "name": f"c{i}"} for i in range(3)
    ]}
    index.write_text(yaml.safe_dump(original))
    step.config = {"SELECT_TOPK": topk, "SELECT_KEEP_IDS": False, "SELECT_KEEP_NAMES": True}
    def execute(args, **kwargs):
        args[-1].write_text("name\n")
    step.run_isaac_toolkit.side_effect = execute
    _, metrics, paths = step.run(state)
    selected = yaml.safe_load(paths["prelim.index"].read_text())
    assert selected["metadata"] == original["metadata"]
    assert [c["id"] for c in selected["candidates"]] == list(range(expected))
    assert yaml.safe_load(index.read_text()) == original
    assert metrics["prelim.num_candidates"] == expected
    assert f"Candidates,Dropped,{3 - expected}" in paths["prelim.sankey"].read_text()


@pytest.mark.parametrize("stage,strategy", [("initial", "all(limit=1)"), ("prelim", "all(limit=100)")])
def test_fake_hls_artifacts_and_stage_strategy(tmp_path, stage, strategy):
    from genie.steps.hardware import RunFakeHLS
    step, state, work, index = harness(RunFakeHLS, tmp_path, stage)
    step.config = {var.name: var.default for var in RunFakeHLS.config_vars}
    step.config.update(ISAAC_SET_NAME="XTest", FAKE_HLS_CORE="cv32e40p", FAKE_HLS_STRATEGIES=None)
    state.paths["sess.dir"] = tmp_path / "sess"
    def execute(args, **kwargs):
        assert args[-1] == strategy
        assert args[args.index("--index") + 1] == index
        output = work / "local" / "fake_hls"
        (output / "output").mkdir(parents=True)
        (output / "hls_schedules.csv").write_text("name,area\n")
        (output / "output" / "selected_solutions.yaml").write_text("{}")
    step.run_isaac_toolkit.side_effect = execute
    assert step.run(state)[2][f"{stage}.fake_hls.output_dir"] == work / "local" / "fake_hls"


def test_hls_annotation_requires_both_outputs(tmp_path):
    from genie.steps.hardware import AssignFakeHLSScore
    step, state, work, index = harness(AssignFakeHLSScore, tmp_path)
    schedules = work / "schedules.csv"
    schedules.write_text("name,area\n")
    state.paths.update({"filtered.fake_hls.schedules_csv": schedules,
                        "filtered.fake_hls.selected_solutions_yaml": work / "missing.yaml"})
    with pytest.raises(FileNotFoundError):
        step.run(state)
    step.run_isaac_toolkit.assert_not_called()


@pytest.mark.parametrize("kind", ["asip", "fpga"])
def test_synthesis_reuses_baseline_and_collects_metrics(tmp_path, kind):
    from genie.steps.hardware import RunASIPSynthesis, RunFPGASynthesis
    cls = RunASIPSynthesis if kind == "asip" else RunFPGASynthesis
    step, state, work, index = harness(cls, tmp_path)
    step.config = {v.name: v.default for v in cls.config_vars}
    prefix = f"{kind.upper()}_SYN"
    baseline = tmp_path / "existing baseline"
    baseline.mkdir()
    step.config[f"{prefix}_BASELINE_USE"] = str(baseline)
    scripts = tmp_path / "demo" / "scripts"
    scripts.mkdir(parents=True)
    for name in (f"{kind}_syn_script.sh", f"collect_{kind}_syn_metrics.py", "launch.sh"):
        (scripts / name).touch()
    rtl = work / "rtl"
    rtl.mkdir()
    (rtl / "files.txt").write_text("top.sv\n")
    state.paths["filtered.hls.default.rtl_dir"] = rtl
    def execute(args, **kwargs):
        if "--out" in args:
            assert args[args.index("--baseline-dir") + 1] == baseline
            args[-1].write_text("area\n10\n")
    step.run_subprocess = Mock(side_effect=execute)
    paths = step.run(state)[2]
    assert paths[f"filtered.{kind}_syn.baseline.output_dir"] == baseline
    assert paths[f"filtered.{kind}_syn.metrics_csv"].is_file()
    assert step.run_subprocess.call_count == 2


def test_hls_reused_baseline_copies_rtl_tree(tmp_path):
    from genie.steps.hardware import RunHLS
    step, state, work, index = harness(RunHLS, tmp_path)
    step.config = {v.name: v.default for v in RunHLS.config_vars}
    baseline = tmp_path / "baseline"
    core = baseline / "output" / "CVA5"
    (core / "nested").mkdir(parents=True)
    (core / "nested" / "top.sv").write_text("module top; endmodule")
    (core / "files.txt").write_text("nested/top.sv\n")
    gen = work / "gen"
    gen.mkdir()
    state.paths["filtered.gen_dir"] = gen
    step.config.update(HLS_BASELINE_USE=str(baseline), HLS_SKIP_DEFAULT=True, HLS_SKIP_CUSTOM=True)
    step.run_subprocess = Mock()
    state.metrics["filtered.hls.model"] = "fake"
    _, metrics, paths = step.run(state)
    assert metrics["filtered.hls.model"] == "nailgun"
    rtl = paths["filtered.hls.baseline.rtl_dir"]
    assert (rtl / "nested" / "top.sv").read_text() == "module top; endmodule"
    assert (rtl / "files.txt").read_text() == "nested/top.sv\n"
    step.run_subprocess.assert_not_called()


def test_reanalysis_uses_stage_trace_and_distinct_static_counts(tmp_path):
    from genie.steps.evaluation import Reanalyze
    step, state, work, index = harness(Reanalyze, tmp_path)
    trace = tmp_path / "trace"
    original = tmp_path / "sess"
    for path in [trace / "generic_mlonmcu", trace / "mlif/generic/linker.map",
                 trace / "etiss_instrs.log", trace / "generic_mlonmcu.dump",
                 original / "table/ise_instrs.pkl", work / "names.csv"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test")
    for label in ("ise_bench", "ise_bench_mem"):
        report_dir = work / label
        report_dir.mkdir()
        (report_dir / "report.csv").write_text("test")
        state.paths[f"filtered.{label}.output_dir"] = report_dir
    state.paths.update({"filtered.ise_trace.output_dir": trace, "sess.dir": original})
    def execute(args, **kwargs):
        if "--out" in args:
            args[args.index("--out") + 1].write_text("test")
    step.run_subprocess = Mock(side_effect=execute)
    paths = step.run(state)[2]
    assert paths["filtered.util_score_csv"].is_file()
    args = step.run_subprocess.call_args.args[0]
    assert args[args.index("--static-counts-custom-pkl") + 1].name == "static_counts_custom.pkl"
    assert args[args.index("--dynamic-counts-custom-pkl") + 1].name == "dynamic_counts_custom.pkl"
    modules = [call.args[0][0] for call in step.run_isaac_toolkit.call_args_list]
    assert modules[0] == "isaac_toolkit.session.create"
    assert modules[-1] == "isaac_toolkit.eval.ise.compare_sess"


def test_ise_trace_uses_stage_toolchain(tmp_path):
    from genie.steps.mlonmcu import ISETrace
    step, state, work, index = harness(ISETrace, tmp_path)
    llvm = work / "llvm"
    llvm.mkdir()
    etiss = work / "etiss"
    (etiss / "bin").mkdir(parents=True)
    (etiss / "bin/run_helper.sh").touch()
    step.config = {"ARCH": "rv32im", "BENCH": "embench_iot/crc32", "ISAAC_CORE_NAME": "XTest"}
    state.paths.update({"filtered.seal5.install_dir": llvm, "filtered.etiss.install_dir": etiss,
                        "mlonmcu.home": tmp_path, "mgclient.lib_dir": tmp_path})
    step.run_mlonmcu_helper = Mock(return_value=({}, {"filtered.ise_trace.output_dir": work / "trace"}))
    paths = step.run(state)[2]
    overrides = step.run_mlonmcu_helper.call_args.kwargs["overrides"]
    assert overrides["arch"] == "rv32im_xisaac"
    assert overrides["llvm_install_dir"] == llvm
    assert overrides["log_instrs"] is True
    assert paths["filtered.ise_trace.output_dir"] == work / "trace"


def test_hls_custom_and_shared_variants_publish_separate_artifacts(tmp_path):
    from genie.steps.hardware import RunHLS
    step, state, work, index = harness(RunHLS, tmp_path)
    step.config = {v.name: v.default for v in RunHLS.config_vars}
    source = tmp_path / "tools"
    (source / "nailgun").mkdir(parents=True)
    library = tmp_path / "library.yaml"
    library.write_text("{}")
    step.config.update(HLS_DIR=str(source), HLS_NAILGUN_SHARE_RESOURCES=True, HLS_NAILGUN_CELL_LIBRARY=str(library))
    gen = work / "gen"
    gen.mkdir()
    state.paths["filtered.gen_dir"] = gen
    variants = []
    def execute(args, **kwargs):
        if str(args[0]).endswith("hls_script_local.sh"):
            output = args[1]
            variant = output.parent.name
            variants.append(variant)
            core = output / "CVA5"
            core.mkdir(parents=True)
            (core / "files.txt").write_text("top.sv\n")
            (core / "top.sv").write_text("module top; endmodule\n")
            (output / "ISAX_XIsaac.sv").write_text("module extension; endmodule\n")
            (output / "selected_solutions.yaml").write_text("{}")
            if variant == "default":
                (output / "mlir").mkdir()
                (output / "mlir/ISAX_XISAAC.HLS_EN.mlir").write_text("lil.enc_immediates")
            if variant == "custom":
                assert any(str(arg).startswith("LN_PREDEFINED_SOLUTION_SELECTION=") for arg in args)
            if variant == "shared":
                arg = next(arg for arg in args if str(arg).startswith("MLIR_ENTRY_POINT_PATH="))
                shared_file = Path(arg.split("=", 1)[1])
                assert "lil.sharing_group = 1" in shared_file.read_text()
                assert not any(str(arg).startswith("ISAXES=") for arg in args)
        else:
            if "--output" in args:
                destination = args[args.index("--output") + 1]
            else:
                destination = args[-1]
            destination.write_text("test")
    step.run_subprocess = Mock(side_effect=execute)
    paths = step.run(state)[2]
    assert variants == ["baseline", "default", "custom", "shared"]
    assert paths["filtered.hls.schedules_csv"] == paths["filtered.hls.default.schedules_csv"]
    for variant in ("custom", "shared"):
        assert paths[f"filtered.hls.{variant}.selected_metrics_csv"].is_file()


def test_iterative_selection_passes_graph_costs_and_stage_outputs(tmp_path):
    import yaml
    from genie.steps.candidates import SelectWithSpecializations
    step, state, work, index = harness(SelectWithSpecializations, tmp_path)
    step.config = {v.name: v.default for v in step.config_vars}
    step.config.update(BENCH="embench_iot/crc32", SELECT_MAX_COST=100.0)
    package = tmp_path / "demo/mlonmcu/mlonmcu"
    package.mkdir(parents=True)
    (package / "__init__.py").touch()
    graph = work / "spec_graph.pkl"
    graph.touch()
    state.paths.update({"filtered.spec_graph": graph, "mlonmcu.home": tmp_path / "mlonmcu", "mgclient.lib_dir": tmp_path / "mgclient-lib"})
    def execute(args, **kwargs):
        assert args[args.index("--spec-graph") + 1] == graph
        assert args[args.index("--max-cost") + 1] == "100.0"
        assert kwargs["env"]["ARCH"] == "rv32imfd"
        assert kwargs["env"]["ABI"] == "ilp32d"
        assert kwargs["env"]["ISAAC_CORE_NAME"] == "XIsaacCore"
        assert kwargs["env"]["GLOBAL_ISEL"] == "0"
        assert kwargs["env"]["PYTHONPATH"].startswith(str(package.parent))
        assert kwargs["env"]["LD_LIBRARY_PATH"].startswith(str(tmp_path / "mgclient-lib"))
        assert "--topk" not in args
        args[args.index("--output") + 1].write_text(yaml.safe_dump({"candidates": [{"id": 1}]}))
        args[args.index("--sankey") + 1].write_text("diagram")
    step.run_subprocess = Mock(side_effect=execute)
    step.run_isaac_toolkit.side_effect = lambda args, **kwargs: args[-1].write_text("instr\n")
    _, metrics, paths = step.run(state)
    assert paths["filtered_selected.index"].is_file()
    assert metrics["filtered_selected.num_candidates"] == 1


def test_second_filter_applies_utilization_threshold_and_publishes_reports(tmp_path):
    from genie.steps.isaac import FilterCandidates
    step, state, work, index = harness(FilterCandidates, tmp_path)
    step.out_stage = "filtered2"
    step.config = {"FILTER_MIN_UTIL_REL": 0.02}
    state.paths["sess.dir"] = tmp_path
    state.metrics = {"filtered.num_candidates": 3}
    def execute(args, **kwargs):
        if args[0].endswith("filter_index"):
            assert args[args.index("--min-util-score") + 1] == "0.02"
            assert "--min-seal5-score" not in args
            args[args.index("-o") + 1].write_text("candidates: []")
            args[args.index("--sankey") + 1].write_text("diagram")
        else:
            args[-1].write_text("instr,instr_lower\nTEST,test\n")
    step.run_isaac_toolkit.side_effect = execute
    _, metrics, paths = step.run(state)
    assert metrics["filtered2.filtered_candidates"] == 2
    assert paths["filtered2.names_csv"].is_file()
    assert paths["filtered2.sankey"].is_file()


@pytest.mark.parametrize("kind", ["asip", "fpga"])
def test_disabled_synthesis_needs_no_hardware_artifacts(kind):
    from genie.steps.hardware import RunASIPSynthesis, RunFPGASynthesis
    cls = RunASIPSynthesis if kind == "asip" else RunFPGASynthesis
    step = object.__new__(cls)
    step.config = {f"{kind.upper()}_SYN_ENABLE": False}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_subprocess = Mock()
    assert step.run(None) == ({}, {}, {})
    step.run_subprocess.assert_not_called()


def test_synthesis_legacy_configuration_aliases(tmp_path):
    from genie.config import GenIEConfig
    from genie.steps.hardware import RunASIPSynthesis
    config, _ = GenIEConfig.load({"BENCH": "embench_iot/crc32", "ASIP_SYN_SYNOPSYS_CORE_NAME": "CoreX",
        "ASIP_SYN_SYNOPSYS_CLOCK_NS": 12.5, "ASIP_SYN_SYNOPSYS_PDK": "custom_library"},
        RunASIPSynthesis.get_all_config_variables(), design_dir=str(tmp_path))
    assert config["ASIP_SYN_CORE_NAME"] == "CoreX"
    assert config["ASIP_SYN_CLK_PERIOD"] == 12.5
    assert config["ASIP_SYN_PDK"] == "custom_library"


@pytest.mark.parametrize("per_instr,compiler", [(False, "seal5"), (True, "seal5_splitted")])
def test_ise_benchmark_selects_matching_compiler(tmp_path, per_instr, compiler):
    from genie.steps.mlonmcu import ISEBench
    step, state, work, index = harness(ISEBench, tmp_path, "initial")
    step.per_instr = per_instr
    step.config = {"BENCH": "embench_iot/crc32", "ISAAC_CORE_NAME": "XTest"}
    (work / "names.csv").write_text("instr_lower\ncustom0\n")
    for name in ("seal5", "seal5_splitted"):
        directory = work / name
        directory.mkdir()
        state.paths[f"initial.{name}.install_dir"] = directory
    etiss = work / "etiss"
    (etiss / "bin").mkdir(parents=True)
    (etiss / "bin/run_helper.sh").touch()
    state.paths.update({"mlonmcu.home": tmp_path, "mgclient.lib_dir": tmp_path, "initial.etiss.install_dir": etiss})
    state.metrics = {"bench.Target": "etiss", "bench.Arch": "rv32imfd"}
    step.run_mlonmcu_helper = Mock(return_value=({}, {}))
    step.run(state)
    assert step.run_mlonmcu_helper.call_args.kwargs["overrides"]["llvm_install_dir"] == work / compiler


def test_hls_disable_requires_no_tool_paths():
    from genie.steps.hardware import RunHLS
    step = object.__new__(RunHLS)
    step.config = {"HLS_ENABLE": False}
    assert step.run(None) == ({}, {}, {})


def test_hls_fake_dispatch_marks_modeled_artifacts(tmp_path):
    from genie.steps.hardware import RunHLS
    step, state, work, index = harness(RunHLS, tmp_path)
    step.config = {var.name: var.default for var in RunHLS.config_vars}
    step.config["HLS_TOOL"] = "fake"
    state.paths["sess.dir"] = tmp_path / "sess"
    def execute(args, **kwargs):
        assert args[0] == "isaac_toolkit.retargeting.fake_hls"
        output = work / "local/fake_hls"
        (output / "output").mkdir(parents=True)
        (output / "hls_schedules.csv").write_text("test")
        (output / "output/selected_solutions.yaml").write_text("[]")
    step.run_isaac_toolkit.side_effect = execute
    _, metrics, paths = step.run(state)
    assert metrics["filtered.hls.model"] == "fake"
    assert paths["filtered.hls.schedules_csv"] == paths["filtered.fake_hls.schedules_csv"]
    assert "filtered.hls.default.rtl_dir" not in paths


def test_synthesis_refuses_fake_hls_artifacts(tmp_path):
    from genie.steps.hardware import RunFPGASynthesis
    step, state, work, index = harness(RunFPGASynthesis, tmp_path)
    step.config = {var.name: var.default for var in step.config_vars}
    state.metrics["filtered.hls.model"] = "fake"
    with pytest.raises(ValueError, match="provides no RTL"):
        step.run(state)


def test_filter_legacy_configuration_aliases(tmp_path):
    from genie.config import GenIEConfig
    from genie.steps.isaac import FilterCandidates
    config, _ = GenIEConfig.load({"BENCH": "embench_iot/crc32", "MIN_SEAL5_SCORE": 0.75,
        "MIN_UTIL_SCORE": 0.02}, FilterCandidates.get_all_config_variables(), design_dir=str(tmp_path))
    assert config["FILTER_MIN_SEAL5_SCORE"] == 0.75
    assert config["FILTER_MIN_UTIL_REL"] == 0.02
