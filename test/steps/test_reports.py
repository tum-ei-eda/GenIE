from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from genie.steps.reports import compare_rtl_trees, CollectImplementationMetrics


def test_rtl_patch_counts_additions_deletions_and_replacements(tmp_path):
    before, after = tmp_path / "before", tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "top.sv").write_text("old\nkeep\n")
    (after / "top.sv").write_text("new\nkeep\nextra\n")
    (after / "extension.sv").write_text("extension\n")
    patch, counts = compare_rtl_trees(before, after)
    assert "-old" in patch and "+new" in patch
    assert "+extension" in patch
    assert counts == {"n_files_changed": 2, "n_insertions": 3, "n_deletions": 1}


def test_combined_locs_uses_prototype_phase_selection(tmp_path):
    index = tmp_path / "index.yml"
    index.write_text("{}")
    seal5 = tmp_path / "diff.csv"
    pd.DataFrame([
        {"phase": "PHASE_1", "n_files_changed": 2, "n_insertions": 8, "n_deletions": 3},
        {"phase": "OTHER", "n_files_changed": 100, "n_insertions": 100, "n_deletions": 100},
    ]).to_csv(seal5, index=False)
    stat = tmp_path / "etiss.stat"
    stat.write_text("1 file changed, 4 insertions(+), 2 deletions(-)\n")
    hls = tmp_path / "hls.csv"
    pd.DataFrame({"locs": [12, 6]}).to_csv(hls, index=False)
    state = SimpleNamespace(paths={"initial.index": index, "initial.workdir": tmp_path,
        "demo.dir": tmp_path, "initial.seal5.diff_csv": seal5,
        "initial.etiss.patch_stat": stat, "initial.hls.metrics_csv": hls})
    step = object.__new__(CollectImplementationMetrics)
    paths = step.run(state)[2]
    frame = pd.read_csv(paths["initial.combined_locs_csv"]).set_index("step")
    assert frame.loc["seal5", "n_insertions"] == 8
    assert frame.loc["etiss", "n_files_changed"] == 1
    assert frame.loc["rtl", "n_insertions"] == 18


def test_reanalysis_diff_uses_matching_block_and_runtime_tables(tmp_path):
    from genie.steps.reports import CreateReanalysisDiff
    baseline = tmp_path / "baseline/table"
    current = tmp_path / "new/table"
    baseline.mkdir(parents=True)
    current.mkdir(parents=True)
    pd.DataFrame({"func_name": ["main"], "bb_name": ["entry"]}).to_pickle(baseline / "choices.pkl")
    for directory, instructions in ((baseline, ["add", "mul"]), (current, ["custom"])):
        pd.DataFrame({"func_name": ["main"], "bb_name": ["entry"], "start": [0],
                      "end": [len(instructions) * 4], "num_instrs": [len(instructions)]}).to_pickle(directory / "llvm_bbs_new.pkl")
        pd.DataFrame({"pc": list(range(0, len(instructions) * 4, 4)), "instr": instructions,
                      "args": ["a0,a1"] * len(instructions)}).to_pickle(directory / "disass.pkl")
    pd.DataFrame({"rel_weight_": [0.8], "rel_weight": [0.5], "diff": [-0.3], "diff_rel": [-0.375]},
                 index=["main-entry"]).to_pickle(current / "compare_runtime_per_llvm_bb.pkl")
    index = tmp_path / "index.yml"
    index.write_text("{}")
    step = object.__new__(CreateReanalysisDiff)
    state = SimpleNamespace(paths={"initial.index": index, "initial.workdir": tmp_path, "demo.dir": tmp_path,
                                   "sess.dir": baseline.parent, "initial.reanalysis.dir": current.parent})
    _, metrics, paths = step.run(state)
    report = paths["initial.diff_summary_txt"].read_text()
    assert "main-entry" in report and "-mul" in report and "+custom" in report
    assert "-37.50%" in report
    assert metrics["initial.diff.num_blocks"] == 1
    assert pd.read_csv(paths["initial.diff_summary_csv"])["num_instrs_diff"].tolist() == [-1]


def test_attach_synthesis_measurements_preserves_candidates(tmp_path):
    import yaml
    from genie.steps.candidates import AssignSynthesisMetrics
    index = tmp_path / "index.yml"
    index.write_text(yaml.safe_dump({"candidates": [{"id": 5}], "global": {"artifacts": {"tool": "keep"}}}))
    state = SimpleNamespace(paths={"initial.index": index, "initial.workdir": tmp_path, "demo.dir": tmp_path})
    for kind in ("asip", "fpga"):
        report = tmp_path / f"{kind}.csv"
        pd.DataFrame({"variant": ["default"], "area": [123]}).to_csv(report, index=False)
        state.paths[f"initial.{kind}_syn.metrics_csv"] = report
    step = object.__new__(AssignSynthesisMetrics)
    step.config = {"ASIP_SYN_ENABLE": True, "FPGA_SYN_ENABLE": True}
    step.run(state)
    data = yaml.safe_load(index.read_text())
    assert data["candidates"] == [{"id": 5}]
    assert data["global"]["artifacts"] == {"tool": "keep"}
    assert data["global"]["evaluation"]["synthesis"]["asip_syn.metrics_csv"][0]["area"] == 123
