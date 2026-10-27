"""Stage-aware candidate scoring and ordering from the prototype flows."""
import os
from pathlib import Path
from typing import Optional

from genie.config import Variable
from .isaac import ISAACStep, isaac_core_name_var
from .mlonmcu import MLonMCUStep
from .step import GenIEStep
from .common_vars import synthesis_enable_vars


class CandidateStep(ISAACStep):
    inputs = []
    outputs = []
    in_stage = "initial"

    def context(self, state):
        index = Path(state.paths[f"{self.in_stage}.index"])
        work = Path(state.paths[f"{self.in_stage}.workdir"])
        if not index.is_file():
            raise FileNotFoundError(index)
        return index, work, Path(state.paths["demo.dir"]) / "scripts"


class AssignScore(CandidateStep):
    """Attach a producer's CSV scores to the same stage's candidate index."""
    module = ""
    score_option = ""
    score_path = ""

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        report = Path(state_in.paths[f"{self.in_stage}.{self.score_path}"])
        if not report.is_file():
            raise FileNotFoundError(report)
        self.run_isaac_toolkit(
            [f"isaac_toolkit.utils.{self.module}", index, "--inplace", self.score_option, report],
            scripts_dir=scripts, env=env,
        )
        return {}, {}, {}


@GenIEStep.factory.register()
class AssignEncodingScore(AssignScore):
    id = "ISAAC.AssignEncodingScore"
    name = long_name = "Assign Encoding Score"
    module = "annotate_enc_score"
    score_option = "--enc-score-csv"
    score_path = "encoding_score_csv"


@GenIEStep.factory.register()
class AssignUtilizationScore(AssignScore):
    id = "ISAAC.AssignUtilizationScore"
    name = long_name = "Assign Utilization Score"
    module = "annotate_util_score"
    score_option = "--util-score-csv"
    score_path = "util_score_csv"


@GenIEStep.factory.register()
class AssignSeal5Score(AssignScore):
    id = "ISAAC.AssignSeal5Score"
    name = long_name = "Assign Seal5 Score"
    module = "annotate_seal5_score"
    score_option = "--seal5-score-csv"
    score_path = "seal5.seal5_score_csv"


@GenIEStep.factory.register()
class ScoreCandidates(CandidateStep):
    id = "ISAAC.ScoreCandidates"
    name = long_name = "Score Candidates"
    config_vars = CandidateStep.config_vars + [
        Variable("ENC_WEIGHT", float, "Encoding contribution to preliminary score.", default=1.0),
        Variable("UTIL_WEIGHT", float, "Utilization contribution to preliminary score.", default=1.0),
    ]

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        args = ["isaac_toolkit.utils.annotate_score", index, "--inplace"]
        if self.in_stage in ("prelim", "filtered2_selected"):
            args += ["--prelim", "--util-weight", str(self.config["UTIL_WEIGHT"]),
                     "--enc-weight", str(self.config["ENC_WEIGHT"])]
        elif self.in_stage in ("filtered", "filtered_selected"):
            args += ["--filtered"]
        elif self.in_stage in ("filtered2", "final"):
            args += [f"--{self.in_stage}"]
        elif self.in_stage != "initial":
            raise ValueError(f"Unsupported scoring stage: {self.in_stage}")
        self.run_isaac_toolkit(args, scripts_dir=scripts, env=env)
        return {}, {}, {}


@GenIEStep.factory.register()
class SortCandidates(CandidateStep):
    id = "ISAAC.SortCandidates"
    name = long_name = "Sort Candidates"
    config_vars = CandidateStep.config_vars + [
        Variable("CANDIDATE_SORT_BY", Optional[str], "Override score column used for ordering.", default=None),
    ]

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        # annotate_score uses --filtered for filtered_selected and --prelim
        # for filtered2_selected. Match its actual columns when ordering.
        score_stage = {"filtered_selected": "filtered",
                       "filtered2_selected": "prelim"}.get(self.in_stage, self.in_stage)
        column = self.config["CANDIDATE_SORT_BY"] or (
            "score" if score_stage == "initial" else f"{score_stage}_score"
        )
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.sort_index", index, "--inplace", "--by", column],
            scripts_dir=scripts, env=env,
        )
        names = work / "names.csv"
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.names_helper", index, "--output", names],
            scripts_dir=scripts, env=env,
        )
        if not names.is_file():
            raise FileNotFoundError(names)
        return {}, {}, {f"{self.in_stage}.names_csv": names}


@GenIEStep.factory.register()
class SelectCandidates(CandidateStep):
    """Select a prefix of an ordered index (prototype select_candidates.py).

    Graph-based iterative selection is a separate algorithm; this step covers
    the top-k transitions used by flow_select_new and preliminary/final stages.
    """
    id = "ISAAC.SelectCandidates"
    name = long_name = "Select Candidates"
    in_stage = "filtered2"
    out_stage = "prelim"
    config_vars = CandidateStep.config_vars + [
        Variable("SELECT_TOPK", int, "Maximum candidates; zero keeps all.", default=0),
        Variable("SELECT_KEEP_IDS", bool, "Preserve candidate IDs.", default=False),
        Variable("SELECT_KEEP_NAMES", bool, "Preserve existing candidate names.", default=False),
    ]

    def run(self, state_in, **kwargs):
        import copy
        import yaml

        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        topk = self.config["SELECT_TOPK"]
        if topk < 0:
            raise ValueError("SELECT_TOPK must be nonnegative")
        if self.in_stage == self.out_stage:
            raise ValueError("Selection requires a distinct output stage")
        data = yaml.safe_load(index.read_text())
        candidates = data["candidates"]
        if not isinstance(candidates, list):
            raise ValueError("Candidate index must contain a candidates list")
        selected = copy.deepcopy(candidates[:topk] if topk else candidates)
        if not self.config["SELECT_KEEP_IDS"]:
            for i, candidate in enumerate(selected):
                candidate["id"] = i
        data["candidates"] = selected
        out_dir = work.parent / self.out_stage
        out_dir.mkdir(parents=True, exist_ok=True)
        out_index = out_dir / "index.yml"
        out_index.write_text(yaml.safe_dump(data, sort_keys=False))
        names = out_dir / "names.csv"
        if self.config["SELECT_KEEP_NAMES"]:
            args = ["isaac_toolkit.utils.names_helper", out_index, "--output", names]
        else:
            args = ["isaac_toolkit.utils.assign_names", out_index, "--inplace", "--csv", names]
        self.run_isaac_toolkit(args, scripts_dir=scripts, env=env)
        if not names.is_file():
            raise FileNotFoundError(names)
        sankey = out_dir / "sankey.md"
        sankey.write_text(
            "```mermaid\nsankey-beta\n\n"
            f"Candidates,Selected,{len(selected)}\n"
            f"Candidates,Dropped,{len(candidates) - len(selected)}\n```\n"
        )
        return {}, {
            f"{self.out_stage}.num_candidates": len(selected),
            f"{self.out_stage}.dropped_candidates": len(candidates) - len(selected),
        }, {
            f"{self.out_stage}.index": out_index,
            f"{self.out_stage}.workdir": out_dir,
            f"{self.out_stage}.names_csv": names,
            f"{self.out_stage}.sankey": sankey,
        }


@GenIEStep.factory.register()
class SelectWithSpecializations(CandidateStep):
    """Run the prototype's iterative selection algorithm on stage artifacts."""
    id = "ISAAC.SelectWithSpecializations"
    name = long_name = "Select With Specializations"
    in_stage = "filtered"
    out_stage = "filtered_selected"
    config_vars = CandidateStep.config_vars + [
        var for var in MLonMCUStep.config_vars
        if var.name in ("BENCH", "TARGET", "ARCH", "ABI", "UNROLL", "OPTIMIZE", "GLOBAL_ISEL", "BACKEND")
    ] + [isaac_core_name_var] + [
        Variable("SELECT_TOPK", int, "Maximum selected candidates; zero is unlimited.", default=0),
        Variable("SELECT_MAX_COST", Optional[float], "Maximum total hardware cost.", default=None),
        Variable("SELECT_INSTR_COST_FUNC", str, "Instruction hardware cost function.", default="hls_area_per_instr"),
        Variable("SELECT_TOTAL_COST_FUNC", str, "Combined hardware cost function.", default="hls_area_per_instr_sum"),
        Variable("SELECT_INSTR_BENEFIT_FUNC", str, "Instruction performance benefit function.", default="speedup_per_instr"),
        Variable("SELECT_TOTAL_BENEFIT_FUNC", str, "Combined performance benefit function.", default="speedup"),
    ]

    def run(self, state_in, **kwargs):
        import yaml

        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        graph = Path(state_in.paths[f"{self.in_stage}.spec_graph"])
        if not graph.is_file():
            raise FileNotFoundError(graph)
        if self.in_stage == self.out_stage:
            raise ValueError("Selection requires a distinct output stage")
        topk = self.config["SELECT_TOPK"]
        if topk != 0:
            raise ValueError("The iterative selection CLI does not support SELECT_TOPK; use SELECT_MAX_COST")
        output = work.parent / self.out_stage
        output.mkdir(parents=True, exist_ok=True)
        out_index = output / "index.yml"
        sankey = output / "sankey.md"
        args = [scripts / "launch.sh", "python3", scripts / "selection_algo.py", index,
                "--output", out_index, "--spec-graph", graph, "--benchmark", self.config["BENCH"],
                "--use-mlonmcu", "--sankey", sankey]
        for option in ("instr_cost_func", "total_cost_func", "instr_benefit_func", "total_benefit_func"):
            args += ["--" + option.replace("_", "-"), self.config["SELECT_" + option.upper()]]
        if self.config["SELECT_MAX_COST"] is not None:
            args += ["--max-cost", str(self.config["SELECT_MAX_COST"])]
        env["MLONMCU_HOME"] = str(state_in.paths["mlonmcu.home"])
        mgclient_lib = state_in.paths.get("mgclient.lib_dir")
        if mgclient_lib:
            env["LD_LIBRARY_PATH"] = str(mgclient_lib) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        mlonmcu_source = Path(state_in.paths.get("mlonmcu.src_dir", scripts.parent / "mlonmcu"))
        if (mlonmcu_source / "mlonmcu" / "__init__.py").is_file():
            env["PYTHONPATH"] = str(mlonmcu_source) + os.pathsep + env.get("PYTHONPATH", "")
        for key in ("TARGET", "ARCH", "ABI", "UNROLL", "OPTIMIZE", "GLOBAL_ISEL", "BACKEND", "ISAAC_CORE_NAME"):
            value = self.config[key]
            if value is not None:
                env[key] = str(int(value)) if isinstance(value, bool) else str(value)
        self.run_subprocess(args, env=env, check=True, cwd=scripts.parent, **kwargs)
        if not out_index.is_file():
            raise FileNotFoundError(out_index)
        names = output / "names.csv"
        self.run_isaac_toolkit(["isaac_toolkit.utils.names_helper", out_index, "--output", names],
                               scripts_dir=scripts, env=env)
        for artifact in (names, sankey):
            if not artifact.is_file():
                raise FileNotFoundError(artifact)
        candidates = yaml.safe_load(out_index.read_text())["candidates"]
        return {}, {f"{self.out_stage}.num_candidates": len(candidates)}, {
            f"{self.out_stage}.index": out_index, f"{self.out_stage}.workdir": output,
            f"{self.out_stage}.names_csv": names, f"{self.out_stage}.sankey": sankey,
        }


class AttachEvaluationReports(CandidateStep):
    """Attach aggregate measurements without inventing per-instruction scores."""
    report_paths = ()
    report_group = ""

    def run(self, state_in, **kwargs):
        import json
        import yaml
        import pandas as pd

        index, work, scripts = self.context(state_in)
        reports = {}
        for suffix in self.report_paths:
            path = Path(state_in.paths[f"{self.in_stage}.{suffix}"])
            if not path.is_file():
                raise FileNotFoundError(path)
            # JSON conversion normalizes numpy values and missing CSV cells.
            reports[suffix] = json.loads(pd.read_csv(path).to_json(orient="records"))
        data = yaml.safe_load(index.read_text())
        data.setdefault("global", {}).setdefault("evaluation", {})[self.report_group] = reports
        index.write_text(yaml.safe_dump(data, sort_keys=False))
        return {}, {}, {}


@GenIEStep.factory.register()
class AssignComparisonMetrics(AttachEvaluationReports):
    id = "ISAAC.AssignComparisonMetrics"
    name = long_name = "Assign Comparison Metrics"
    report_group = "comparison"
    report_paths = ("compare_csv",)


@GenIEStep.factory.register()
class AssignReuseMetrics(AttachEvaluationReports):
    id = "ISAAC.AssignReuseMetrics"
    name = long_name = "Assign Reuse Metrics"
    report_group = "reuse"
    report_paths = ("compare_others_csv", "compare_others_mem_csv")


@GenIEStep.factory.register()
class AssignSynthesisMetrics(AttachEvaluationReports):
    id = "ISAAC.AssignSynthesisMetrics"
    name = long_name = "Assign Synthesis Metrics"
    report_group = "synthesis"
    report_paths = ("asip_syn.metrics_csv", "fpga_syn.metrics_csv")
    config_vars = CandidateStep.config_vars + synthesis_enable_vars

    def run(self, state_in, **kwargs):
        # Snapshot the active reports on this instance, preserving class defaults.
        self.report_paths = tuple(path for path in type(self).report_paths
                                  if self.config[f"{path.split('_syn')[0].upper()}_SYN_ENABLE"])
        if not self.report_paths:
            return {}, {}, {}
        return super().run(state_in, **kwargs)



@GenIEStep.factory.register()
class AssignPerInstructionMetrics(AssignScore):
    id = "ISAAC.AssignPerInstructionMetrics"
    name = long_name = "Assign Per-Instruction Metrics"
    module = "annotate_per_instr_metrics"
    score_option = "--report"
    score_path = "compare_per_instr_csv"
