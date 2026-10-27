from pathlib import Path
from types import SimpleNamespace
import json
import tarfile

from genie.steps.ci import CreateSummary, PrepareUploads


def test_report_bundle_preserves_duplicate_names(tmp_path):
    state = SimpleNamespace(metrics={"speedup": 1.5}, paths={})
    for name in ("initial", "filtered"):
        report = tmp_path / name / "metrics.csv"
        report.parent.mkdir()
        report.write_text(f"stage\n{name}\n")
        state.paths[f"{name}.metrics_csv"] = report
    summary = object.__new__(CreateSummary)
    summary.step_dir = str(tmp_path / "summary")
    state.paths.update(summary.run(state)[2])
    assert "speedup" in state.paths["ci.summary_md"].read_text()
    bundle = object.__new__(PrepareUploads)
    bundle.step_dir = str(tmp_path / "bundle")
    bundle.config = {"CI_ARTIFACT_KEYS": []}
    _, metrics, paths = bundle.run(state)
    manifest = json.loads(paths["ci.manifest_json"].read_text())
    assert metrics["ci.num_artifacts"] == 3
    with tarfile.open(paths["ci.upload_archive"]) as archive:
        csvs = [entry for entry in manifest if entry["source"].endswith(".csv")]
        assert len({entry["archive"] for entry in csvs}) == 2
        for entry in csvs:
            assert archive.extractfile(entry["archive"]).read() == Path(entry["source"]).read_bytes()


def test_summary_includes_experiment_sections_and_keeps_config_explicit(tmp_path):
    import pandas as pd
    choices = tmp_path / "choices.html"
    choices.write_text("<h2>Choice 0</h2><pre>add</pre>")
    potential = tmp_path / "potential.pkl"
    pd.DataFrame({"has_potential": [True]}).to_pickle(potential)
    comparison = tmp_path / "compare.csv"
    comparison.write_text('Arch,Run Instructions\nrv32im,100\nrv32im_xisaac,70\n')
    sankey = tmp_path / "sankey.md"
    sankey.write_text("```mermaid\nsankey-beta\nCandidates,Selected,2\n```\n")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "Custom.core_desc").write_text("InstructionSet Custom { /* ``` */ }\n")
    step = object.__new__(CreateSummary)
    step.step_dir = str(tmp_path / "summary")
    step.config = {"BENCH": "test/crc32", "PRIVATE_TOKEN": "not-for-report",
                   "CI_REPORT_CONFIG_KEYS": ["BENCH"]}
    state = SimpleNamespace(metrics={"timing.ISAAC.QueryCandidates.seconds": 1.25}, paths={
        "sess.choices_summary_min_html": choices, "sess.ise_potential_pkl": potential,
        "final.compare_csv": comparison, "final.sankey": sankey, "final.gen_dir": gen})
    report = step.run(state)[2]["ci.summary_md"].read_text()
    for value in ("test/crc32", "1.250000", "ISE potential", "Choice 0", "rv32im_xisaac",
                  "Candidates,Selected,2", "InstructionSet Custom", "````c"):
        assert value in report
    assert "PRIVATE_TOKEN" not in report and "not-for-report" not in report


def test_default_bundle_includes_html_and_pdf(tmp_path):
    paths = {}
    for extension in ("html", "pdf"):
        path = tmp_path / f"report.{extension}"
        path.write_bytes(b"report")
        paths[extension] = path
    step = object.__new__(PrepareUploads)
    step.step_dir = str(tmp_path / "bundle")
    step.config = {"CI_ARTIFACT_KEYS": []}
    _, metrics, _ = step.run(SimpleNamespace(paths=paths))
    assert metrics["ci.num_artifacts"] == 2
