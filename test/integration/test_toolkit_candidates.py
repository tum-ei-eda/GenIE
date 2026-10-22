"""Run real toolkit CLIs when GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC are set."""
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from genie.steps.candidates import SortCandidates, SelectCandidates


def test_prelim_filtered_selection_phase_cli(tmp_path):
    from genie.state import State
    toolkit, demo = os.environ.get("GENIE_TOOLKIT_SRC"), os.environ.get("GENIE_DEMO_SRC")
    if not toolkit or not demo:
        pytest.skip("Set GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC for real CLI integration")
    work = tmp_path / "prelim_filtered"
    work.mkdir()
    index = work / "index.yml"
    index.write_text(yaml.safe_dump({"candidates": [
        {"id": i, "properties": {"InstrName": f"OLD{i}", "#Instrs": 2}, "metrics": {}}
        for i in range(3)
    ]}))
    initial = tmp_path / "state.json"
    initial.write_text(State(paths={"prelim_filtered.index": str(index),
        "prelim_filtered.workdir": str(work), "demo.dir": demo,
        "venv.dir": str(Path(sys.executable).parent.parent)}).dumps())
    config = tmp_path / "config.yml"
    config.write_text("BENCH: embench_iot/crc32\nSELECT_TOPK: 2\n")
    result = subprocess.run([sys.executable, "-m", "genie.prototype", "flow_select_new.sh",
        "--stage", "prelim_filtered", str(config), "--design-dir", str(tmp_path),
        "--with-initial-state", str(initial)], env=dict(os.environ, PYTHONPATH=toolkit),
        capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    selected = yaml.safe_load((tmp_path / "final" / "index.yml").read_text())["candidates"]
    assert [c["properties"]["InstrName"] for c in selected] == ["CUSTOM0", "CUSTOM1"]
    assert len(yaml.safe_load(index.read_text())["candidates"]) == 3
    assert (tmp_path / "final" / "sankey.md").is_file()


@pytest.mark.parametrize("stage,score_column", [
    ("filtered_selected", "filtered_score"),
    ("filtered2_selected", "prelim_score"),
])
def test_selected_stage_scoring_then_sorting(stage, score_column, tmp_path):
    from genie.steps.candidates import ScoreCandidates
    toolkit = os.environ.get("GENIE_TOOLKIT_SRC")
    demo = os.environ.get("GENIE_DEMO_SRC")
    if not toolkit or not demo:
        pytest.skip("Set GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC for real CLI integration")
    work = tmp_path / stage
    work.mkdir()
    index = work / "index.yml"
    index.write_text(yaml.safe_dump({"candidates": [
        {"id": i, "properties": {"InstrName": name, "#Instrs": 2},
         "metrics": {"util_score": benefit, "enc_weight": 0.1}}
        for i, (name, benefit) in enumerate((("LOW", 0.1), ("HIGH", 0.9)))
    ]}))
    state = SimpleNamespace(paths={f"{stage}.index": index, f"{stage}.workdir": work,
                                   "demo.dir": Path(demo)})
    env = dict(os.environ, PYTHONPATH=toolkit, VENV_DIR=str(Path(sys.executable).parent.parent))
    for cls in (ScoreCandidates, SortCandidates):
        step = object.__new__(cls)
        step.in_stage = stage
        step.config = {v.name: v.default for v in cls.config_vars}
        step.extract_env = lambda kwargs: ({}, env.copy())
        def execute(args, **kwargs):
            return subprocess.run([str(arg) for arg in args], **kwargs, capture_output=True, text=True)
        step.run_subprocess = execute
        state.paths.update(step.run(state)[2])
    candidates = yaml.safe_load(index.read_text())["candidates"]
    assert [c["properties"]["InstrName"] for c in candidates] == ["HIGH", "LOW"]
    assert candidates[0]["metrics"][score_column] > candidates[1]["metrics"][score_column]
    assert pd.read_csv(state.paths[f"{stage}.names_csv"])["instr"].tolist() == ["HIGH", "LOW"]


def test_sort_then_select_with_toolkit_cli(tmp_path):
    toolkit = os.environ.get("GENIE_TOOLKIT_SRC")
    demo = os.environ.get("GENIE_DEMO_SRC")
    if not toolkit or not demo:
        pytest.skip("Set GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC for real CLI integration")
    work = tmp_path / "filtered2"
    work.mkdir()
    index = work / "index.yml"
    index.write_text(yaml.safe_dump({"candidates": [
        {"id": 4, "properties": {"InstrName": "LOW", "#Instrs": 2}, "metrics": {"filtered2_score": 1.0}},
        {"id": 9, "properties": {"InstrName": "HIGH", "#Instrs": 3}, "metrics": {"filtered2_score": 3.0}},
    ]}))
    state = SimpleNamespace(paths={"filtered2.index": index, "filtered2.workdir": work, "demo.dir": Path(demo)})
    env = dict(os.environ, PYTHONPATH=toolkit, VENV_DIR=str(Path(sys.executable).parent.parent))
    def prepare(cls, config):
        step = object.__new__(cls)
        step.in_stage = "filtered2"
        step.config = {"ISAAC_LOG_LEVEL": "info", "ISAAC_PROGRESS": False,
                       "ISAAC_FORCE_OVERRIDE": False, **config}
        step.extract_env = lambda kwargs: ({}, env.copy())
        def execute(args, **kwargs):
            return subprocess.run([str(arg) for arg in args], **kwargs, capture_output=True, text=True)
        step.run_subprocess = execute
        return step
    sort = prepare(SortCandidates, {"CANDIDATE_SORT_BY": None})
    state.paths.update(sort.run(state)[2])
    assert pd.read_csv(state.paths["filtered2.names_csv"])["instr"].tolist() == ["HIGH", "LOW"]
    select = prepare(SelectCandidates, {"SELECT_TOPK": 1, "SELECT_KEEP_IDS": False, "SELECT_KEEP_NAMES": False})
    paths = select.run(state)[2]
    selected = yaml.safe_load(paths["prelim.index"].read_text())["candidates"]
    assert len(selected) == 1
    assert selected[0]["metrics"]["filtered2_score"] == 3.0
    assert selected[0]["id"] == 0
    assert selected[0]["properties"]["InstrName"] == "CUSTOM0"
    assert pd.read_csv(paths["prelim.names_csv"])["instr_lower"].tolist() == ["custom0"]


def test_real_annotation_scoring_and_filter_chain(tmp_path):
    from genie.steps.candidates import AssignEncodingScore, AssignUtilizationScore, AssignSeal5Score, ScoreCandidates
    from genie.steps.isaac import FilterCandidates
    toolkit, demo = os.environ.get("GENIE_TOOLKIT_SRC"), os.environ.get("GENIE_DEMO_SRC")
    if not toolkit or not demo:
        pytest.skip("Set GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC for real CLI integration")
    session = tmp_path / "sess"
    work = session / "work" / "initial"
    work.mkdir(parents=True)
    index = work / "combined_index.yml"
    candidates = [{"id": i, "properties": {"InstrName": name, "#Instrs": 2},
                   "metrics": {"runtime_reduction_rel": 0.1}} for i, name in enumerate(("GOOD", "UNSUPPORTED", "UNUSED"))]
    index.write_text(yaml.safe_dump({"candidates": candidates, "global": {"artifacts": {}}}))
    state = SimpleNamespace(paths={"initial.index": index, "initial.workdir": work,
                                   "demo.dir": Path(demo), "sess.dir": session},
                            metrics={"initial.num_candidates": 3})
    for suffix, frame in (
        ("encoding_score_csv", pd.DataFrame({"instr": ["GOOD", "UNSUPPORTED", "UNUSED"], "enc_score": [1, 1, 1], "weight": [0.1, 0.1, 0.1]})),
        ("util_score_csv", pd.DataFrame({"instr": ["GOOD", "UNSUPPORTED", "UNUSED"], "util_score": [0.6, 0.4, 0.001]})),
        ("seal5.seal5_score_csv", pd.DataFrame({"instr": ["GOOD", "UNSUPPORTED", "UNUSED"], "seal5_score": [1, 0, 1]})),
    ):
        path = work / (suffix + ".csv")
        frame.to_csv(path, index=False)
        state.paths[f"initial.{suffix}"] = path
    env = dict(os.environ, PYTHONPATH=toolkit, VENV_DIR=str(Path(sys.executable).parent.parent))
    def run(cls, stage="initial", extra=None):
        step = object.__new__(cls)
        step.in_stage = stage
        step.config = {v.name: v.default for v in cls.config_vars}
        step.config.update(extra or {})
        step.extract_env = lambda kwargs: ({}, env.copy())
        def execute(args, **kwargs):
            return subprocess.run([str(arg) for arg in args], **kwargs, capture_output=True, text=True)
        step.run_subprocess = execute
        views, metrics, paths = step.run(state)
        state.paths.update(paths)
        state.metrics.update(metrics)
    for cls in (AssignEncodingScore, AssignUtilizationScore, AssignSeal5Score, ScoreCandidates):
        run(cls)
    annotated = yaml.safe_load(index.read_text())["candidates"]
    assert annotated[0]["metrics"]["score"] > annotated[2]["metrics"]["score"]
    run(FilterCandidates)
    assert [c["properties"]["InstrName"] for c in yaml.safe_load(state.paths["filtered.index"].read_text())["candidates"]] == ["GOOD", "UNUSED"]
    # The prototype's second filter uses utilization rather than compiler score.
    class SecondFilter(FilterCandidates):
        out_stage = "filtered2"
    run(SecondFilter, "filtered", {"FILTER_MIN_UTIL_REL": 0.01})
    filtered = yaml.safe_load(state.paths["filtered2.index"].read_text())["candidates"]
    assert [c["properties"]["InstrName"] for c in filtered] == ["GOOD"]
    assert state.paths["filtered2.sankey"].is_file()
    assert state.metrics["filtered2.filtered_candidates"] == 1


def test_real_step_lifecycle_records_toolkit_artifacts(tmp_path, monkeypatch):
    from genie.config import GenIEConfig
    from genie.state import State
    toolkit, demo = os.environ.get("GENIE_TOOLKIT_SRC"), os.environ.get("GENIE_DEMO_SRC")
    if not toolkit or not demo:
        pytest.skip("Set GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC for real CLI integration")
    monkeypatch.setenv("PYTHONPATH", toolkit)
    monkeypatch.delenv("VENV_DIR", raising=False)
    work = tmp_path / "initial"
    work.mkdir()
    index = work / "combined_index.yml"
    index.write_text(yaml.safe_dump({"candidates": [
        {"id": 0, "properties": {"InstrName": "LOW", "#Instrs": 2}, "metrics": {"score": 1}},
        {"id": 1, "properties": {"InstrName": "HIGH", "#Instrs": 2}, "metrics": {"score": 4}},
    ]}))
    config, _ = GenIEConfig.load({"BENCH": "embench_iot/crc32"}, SortCandidates.get_all_config_variables(),
                                 design_dir=str(tmp_path))
    state = State(paths={"demo.dir": demo, "initial.index": str(index), "initial.workdir": str(work),
                         "venv.dir": str(Path(sys.executable).parent.parent)},
                  metrics={"timing.prior.seconds": 1.25})
    step = SortCandidates(config=config, state_in=state)
    directory = tmp_path / "sort-step"
    result = step.start(step_dir=str(directory))
    assert pd.read_csv(result.paths["initial.names_csv"])["instr"].tolist() == ["HIGH", "LOW"]
    assert (directory / "state_out.json").is_file()
    assert result.metrics["timing.ISAAC.SortCandidates.seconds"] >= 0
    assert result.metrics["timing.prior.seconds"] == 1.25
    assert "isaac_toolkit.utils.sort_index" in (directory / "COMMANDS").read_text()
    assert len(list(directory.glob("*.process_stats.json"))) == 2
    assert len(list(directory.glob("*.log"))) == 2


def test_perfsim_native_comparison_and_ranking(tmp_path):
    from genie.steps.isaac import CompareISEPerfSimBench
    toolkit = os.environ.get("GENIE_TOOLKIT_SRC")
    if not toolkit:
        pytest.skip("Set GENIE_TOOLKIT_SRC for real toolkit integration")
    index = tmp_path / "index.yml"
    index.write_text("candidates: []\n")
    rows = [dict(Model="crc32", Arch=arch, uArch=uarch,
                 **{"Run Instructions": instr, "Run Instructions (rel.)": instr / 100,
                    "Run Cycles": cycles, "Run Cycles (rel.)": cycles / 200,
                    "Run CPI": cycles / instr, "Total ROM": 1000, "Total RAM": 100,
                    "ROM code": 900, "ROM code (rel.)": 1})
            for arch, uarch, instr, cycles in [("rv32im", "fast", 100, 200),
                ("rv32im_xisaac", "fast", 80, 120), ("rv32im_xisaac", "small", 80, 240)]]
    pd.DataFrame(rows).to_csv(tmp_path / "report.csv", index=False)
    uarchs = tmp_path / "uarchs.csv"
    pd.DataFrame({"uarch": ["fast", "small"], "uarch_lower": ["fast", "small"],
                  "variant": ["a", "b"]}).to_csv(uarchs, index=False)
    step = object.__new__(CompareISEPerfSimBench)
    step.extract_env = lambda kwargs: ({}, {})
    def run_toolkit(args, **kwargs):
        subprocess.run([sys.executable, "-m", *map(str, args)],
            env=dict(os.environ, PYTHONPATH=toolkit), check=True, capture_output=True, text=True)
    step.run_isaac_toolkit = run_toolkit
    state = SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": tmp_path,
        "initial.index": index, "initial.ise_bench.output_dir": tmp_path,
        "initial.ise_bench_mem.output_dir": tmp_path, "initial.etiss_perf.uarchs_csv": uarchs})
    paths = step.run(state)[2]
    comparison = pd.read_csv(paths["initial.compare_csv"])
    ranking = pd.read_csv(paths["initial.uarch_ranking_csv"])
    assert len(comparison) == 3
    assert ranking["uArch"].tolist() == ["fast", "small"]
    assert ranking["Rank"].tolist() == [1, 2]


@pytest.mark.parametrize("threshold,expected", [(None, ["LOW", "HIGH"]), (0.0, ["LOW", "HIGH"]), (0.5, ["HIGH"])])
def test_optional_filter_threshold_with_real_toolkit(tmp_path, threshold, expected):
    from genie.steps.isaac import FilterCandidates
    toolkit, demo = os.environ.get("GENIE_TOOLKIT_SRC"), os.environ.get("GENIE_DEMO_SRC")
    if not toolkit or not demo:
        pytest.skip("Set GENIE_TOOLKIT_SRC and GENIE_DEMO_SRC for real CLI integration")
    work = tmp_path / "sess/work/initial"
    work.mkdir(parents=True)
    index = work / "index.yml"
    index.write_text(yaml.safe_dump({"candidates": [
        {"id": i, "properties": {"InstrName": name},
         "metrics": {"seal5_score": score, "runtime_reduction_rel": 0}}
        for i, (name, score) in enumerate([("LOW", 0.0), ("HIGH", 1.0)])]}))
    step = object.__new__(FilterCandidates)
    step.config = {var.name: var.default for var in step.config_vars}
    step.config.update(FILTER_MIN_SEAL5_SCORE=threshold, FILTER_MIN_RUNTIME_REDUCTION_REL=None)
    env = dict(os.environ, PYTHONPATH=toolkit, VENV_DIR=str(Path(sys.executable).parent.parent))
    step.extract_env = lambda kwargs: ({}, env.copy())
    def execute(args, **kwargs):
        return subprocess.run(list(map(str, args)), **kwargs, capture_output=True, text=True)
    step.run_subprocess = execute
    state = SimpleNamespace(paths={"initial.index": index, "sess.dir": work.parent.parent,
                                  "demo.dir": Path(demo)}, metrics={"initial.num_candidates": 2})
    paths = step.run(state)[2]
    selected = yaml.safe_load(paths["filtered.index"].read_text())["candidates"]
    assert [c["properties"]["InstrName"] for c in selected] == expected
    assert paths["filtered.names_csv"].is_file()
