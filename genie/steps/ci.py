"""Portable run summaries and local CI artifact bundles."""
import json
from pathlib import Path
import tarfile
import csv
import html
import re

from genie.config import Variable
from genie.steps.step import GenIEStep


@GenIEStep.factory.register()
class CreateSummary(GenIEStep):
    id = "CI.CreateSummary"
    name = long_name = "Create CI Summary"
    inputs = []
    outputs = []
    config_vars = [
        Variable("CI_REPORT_CONFIG_KEYS", list[str], "Typed configuration keys to include in reports.",
                 default=["BENCH", "TARGET", "ARCH", "ABI", "OPTIMIZE", "ISAAC_SET_NAME"]),
    ]

    def run(self, state_in, **kwargs):
        destination = Path(self.step_dir) / "ci_report.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        def cell(value):
            return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")
        def table(columns, rows):
            return ["| " + " | ".join(map(cell, columns)) + " |",
                    "| " + " | ".join("---" for _ in columns) + " |", *[
                    "| " + " | ".join(map(cell, row)) + " |" for row in rows]]
        def detail(title, content):
            return [f"<details><summary>{html.escape(title)}</summary>", "", *content, "", "</details>", ""]
        lines = ["# GenIE run report", ""]
        config = getattr(self, "config", {})
        keys = config.get("CI_REPORT_CONFIG_KEYS", ["BENCH", "TARGET", "ARCH", "ABI", "OPTIMIZE", "ISAAC_SET_NAME"])
        selected = [(key, config[key]) for key in keys if key in config]
        if selected:
            lines += ["## Experiment configuration", "", *table(["Setting", "Value"], selected), ""]
        timings = [(key[len("timing."):-len(".seconds")], f"{float(value):.6f}")
                   for key, value in sorted(state_in.metrics.items())
                   if key.startswith("timing.") and key.endswith(".seconds")]
        if timings:
            lines += ["## Step execution times", "", *table(["Step", "Seconds"], timings), ""]
        potential = state_in.paths.get("sess.ise_potential_pkl")
        if potential and Path(potential).is_file():
            import pandas as pd
            frame = pd.read_pickle(potential)
            lines += ["## ISE potential", "", *table(frame.columns, frame.itertuples(index=False, name=None)), ""]
        choices = state_in.paths.get("sess.choices_summary_min_html")
        if choices and Path(choices).is_file():
            lines += ["## Choices", "", *detail("Selected discovery blocks", [Path(choices).read_text()])]
        for key, value in sorted(state_in.paths.items()):
            if value is None:
                continue
            path = Path(value)
            if not path.is_file():
                continue
            if key.endswith(".query_metrics_csv") or (".compare" in key and path.suffix == ".csv"):
                with path.open(newline="") as source:
                    reader = csv.reader(source)
                    columns = next(reader, [])
                    content = table(columns, reader) if columns else ["Empty report."]
                lines += [f"## {cell(key)}", "", *detail("Measured table", content)]
            elif key.endswith(".sankey"):
                lines += [f"## {cell(key)}", "", *detail("Candidate transitions", [path.read_text()])]
        for key, value in sorted(state_in.paths.items()):
            if value is None or not key.endswith(".gen_dir"):
                continue
            for path in sorted(Path(value).glob("*.core_desc")):
                if ".splitted." in path.name:
                    continue
                code = path.read_text()
                if not re.search(r"(?m)^\s*InstructionSet\s", code):
                    continue
                fence = "`" * max(3, max((len(match[0]) + 1 for match in re.finditer(r"`+", code)), default=3))
                lines += [f"## {cell(key)} CoreDSL", "", *detail(path.name, [fence + "c", code, fence])]
        lines += ["## Metrics", "", "| Metric | Value |", "| --- | --- |"]
        for key, value in sorted(state_in.metrics.items()):
            lines.append(f"| {cell(key)} | {cell(value)} |")
        lines += ["", "## Artifacts", "", "| Artifact | Path | Available |", "| --- | --- | --- |"]
        for key, value in sorted(state_in.paths.items()):
            if value is None:
                continue
            path = Path(value)
            lines.append(f"| {cell(key)} | {cell(path)} | {'yes' if path.exists() else 'no'} |")
        destination.write_text("\n".join(lines) + "\n")
        return {}, {}, {"ci.summary_md": destination}


@GenIEStep.factory.register()
class PrepareUploads(GenIEStep):
    """Bundle declared report artifacts locally for a CI runner to upload."""
    id = "CI.PrepareUploads"
    name = long_name = "Prepare CI Uploads"
    inputs = []
    outputs = []
    config_vars = [
        Variable("CI_ARTIFACT_KEYS", list[str], "State paths to bundle; empty selects report files.", default=[]),
    ]

    def run(self, state_in, **kwargs):
        directory = Path(self.step_dir)
        directory.mkdir(parents=True, exist_ok=True)
        archive = directory / "reports.tar.gz"
        manifest = directory / "manifest.json"
        keys = self.config["CI_ARTIFACT_KEYS"]
        if not keys:
            keys = [key for key, value in state_in.paths.items()
                    if value is not None and Path(value).suffix.lower() in (".csv", ".md", ".json", ".yaml", ".yml", ".html", ".pdf")]
        selected = []
        for i, key in enumerate(keys):
            path = Path(state_in.paths[key])
            if not path.is_file():
                raise FileNotFoundError(path)
            selected.append((key, path, f"artifacts/{i:04d}/{path.name}"))
        manifest.write_text(json.dumps([
            {"key": key, "source": str(path), "archive": member}
            for key, path, member in selected
        ], indent=2) + "\n")
        with tarfile.open(archive, "w:gz", dereference=True) as bundle:
            bundle.add(manifest, arcname="manifest.json")
            for key, path, member in selected:
                bundle.add(path, arcname=member)
        return {}, {"ci.num_artifacts": len(selected)}, {"ci.upload_archive": archive, "ci.manifest_json": manifest}
