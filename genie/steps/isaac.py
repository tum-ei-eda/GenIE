import pathlib
from time import sleep
from typing import Tuple, Optional, List, Dict

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate, PathsUpdate
from genie.config import Variable
from genie.state import State

import pandas as pd
from .service import service_vars, retarget_service

isaac_vars = [
    Variable(
        "ISAAC_LOG_LEVEL",
        Optional[str],
        "The ISAAC Toolkit logging level.",
        default="info",
    ),
    Variable(
        "ISAAC_PROGRESS",
        bool,
        "Show progress bars in ISAAC Toolkit.",
        default=False,
    ),
    Variable(
        "ISAAC_FORCE_OVERRIDE",
        bool,
        "Force override ISAAC Toolkit sessions.",
        default=True,
    ),
]

isaac_set_name_var = Variable(
    "ISAAC_SET_NAME",
    str,
    "TODO.",
    default="XIsaac",
)
isaac_core_name_var = Variable(
    "ISAAC_CORE_NAME",
    str,
    "TODO.",
    default="XIsaacCore",
)


def record_global_artifacts(index_file, **artifacts):
    """Publish retargeting installations for toolkit selection consumers."""
    import yaml
    index_file = pathlib.Path(index_file)
    data = yaml.safe_load(index_file.read_text())
    global_data = data.setdefault("global", {})
    existing = global_data.get("artifacts")
    if existing is None or existing == []:
        existing = {}
        global_data["artifacts"] = existing
    if not isinstance(existing, dict):
        raise ValueError("Candidate global artifacts must be a mapping or an empty list")
    existing.update({key: str(value) for key, value in artifacts.items()})
    index_file.write_text(yaml.safe_dump(data, sort_keys=False))


class ISAACStep(GenIEStep):

    config_vars = [
        *isaac_vars,
    ]

    def run_isaac_toolkit(
        self,
        args: List,
        sess_dir: Optional[pathlib.Path] = None,
        scripts_dir: Optional[pathlib.Path] = None,
        mgclient_lib_dir: Optional[pathlib.Path] = None,
        env: Optional[Dict] = None,
        has_force: bool = False,
        has_progress: bool = False,
        has_log: bool = True,
    ):
        assert scripts_dir is not None
        launch_script = scripts_dir / "launch.sh"
        assert launch_script.is_file(), f"Missing file: {launch_script}"
        python_exe = "python3"  # TODO
        command = [launch_script, python_exe, "-m", *args]
        if sess_dir is not None:
            command += ["--session", sess_dir]
        config = self.config
        log_level = config["ISAAC_LOG_LEVEL"]
        progress = config["ISAAC_PROGRESS"]
        force = config["ISAAC_FORCE_OVERRIDE"]
        if has_log and log_level is not None:
            command += ["--log", log_level]
        if progress and has_progress:
            command += ["--progress"]
        if force and has_force:
            command += ["--force"]
        if mgclient_lib_dir is not None:
            ld_lib_path = env.get("LD_LIBRARY_PATH", "")
            ld_lib_path_new = f"{mgclient_lib_dir}:{ld_lib_path}"
            env["LD_LIBRARY_PATH"] = ld_lib_path_new
        pythonpath = env.get("PYTHONPATH", "")
        tool_dir = scripts_dir.parent / "memgraph_experiments"  # TODO: convert to python module and install via pip
        pythonpath_new = f"{tool_dir}:{pythonpath}"
        env["PYTHONPATH"] = pythonpath_new
        check = True
        _ = self.run_subprocess(
            command,
            env=env,
            check=check,
            # **kwargs,
        )


@GenIEStep.factory.register()
class CreateSession(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.CreateSession"
    name = "Create Session"
    long_name = "Create ISAAC Session"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        run_dir = pathlib.Path(self.step_dir).parent
        sess_dir = run_dir / label
        self.run_isaac_toolkit(
            ["isaac_toolkit.session.create"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        paths_updates[f"{label}.dir"] = sess_dir
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class LoadConfig(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.LoadConfig"
    name = "Load Config"
    long_name = "Load ISAAC Config"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + [
        Variable(
            "ISAAC_TOOLKIT_CONFIG_YAML",
            Optional[str],
            "Custom ISAAC Toolkit config.",
            default=None,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        config_yaml = config["ISAAC_TOOLKIT_CONFIG_YAML"] or demo_dir / "cfg" / "isaac_toolkit" / "default.yml"
        config_yaml = pathlib.Path(config_yaml)
        if not config_yaml.is_file():
            raise FileNotFoundError(config_yaml)
        self.run_isaac_toolkit(
            ["isaac_toolkit.frontend.cfg.yaml", config_yaml],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        paths_updates["isaac.config_yaml"] = config_yaml
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class LoadArtifacts(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.LoadArtifacts"
    name = "Load Artifacts"
    long_name = "Load ISAAC Artifacts"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        in_label = "trace"
        run_dir = pathlib.Path(state_in.paths[f"{in_label}.output_dir"])
        self.run_isaac_toolkit(
            ["isaac_toolkit.flow.demo.stage.load", run_dir],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            has_progress=True,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class Analyze(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.Analyze"
    name = "Analyze Session"
    long_name = "Analyze ISAAC Session"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        self.run_isaac_toolkit(
            ["isaac_toolkit.flow.demo.stage.analyze"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class Visualize(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.Visualize"
    name = "Visualize Session"
    long_name = "Visualize ISAAC Session"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + [
        Variable(
            "ISAAC_SKIP_VISUALIZE",
            bool,
            "Do not create visualizations for ISAAC session.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        skip_visualize = config["ISAAC_SKIP_VISUALIZE"]
        if skip_visualize:
            return views_updates, metrics_updates, paths_updates
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        self.run_isaac_toolkit(
            ["isaac_toolkit.flow.demo.stage.visualize"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class PickChoices(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.PickChoices"
    name = "Pick Choices"
    long_name = "Pick ISAAC Choices"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        self.run_isaac_toolkit(
            ["isaac_toolkit.flow.demo.stage.pick"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        ise_potential_pkl = sess_dir / "table" / "ise_potential.pkl"
        assert ise_potential_pkl.is_file(), f"Missing file: {ise_potential_pkl}"
        ise_potential_df = pd.read_pickle(ise_potential_pkl)
        if ise_potential_df.empty or not ise_potential_df["has_potential"].all():
            raise ValueError("Input is unsuitable for instruction-set extension discovery")
        if len(ise_potential_df) == 1:
            new_metrics = {f"{label}.{key}": val for key, val in ise_potential_df.iloc[0].to_dict().items()}
        else:
            new_metrics = {f"{label}.potential.[{i}].{key}": val
                           for i, (_, row) in enumerate(ise_potential_df.iterrows())
                           for key, val in row.to_dict().items()}
        metrics_updates.update(new_metrics)
        choices_pkl = sess_dir / "table" / "choices.pkl"
        assert choices_pkl.is_file(), f"Missing file: {choices_pkl}"
        choices_df = pd.read_pickle(choices_pkl)
        if choices_df.empty:
            raise ValueError("No eligible discovery choices found")
        temp = {"num_choices": len(choices_df), "num_chocies": len(choices_df),
                "total_choices_rel_weight": choices_df["rel_weight"].sum()}
        new_metrics2 = {f"{label}.{key}": val for key, val in temp.items()}
        metrics_updates.update(new_metrics2)
        paths_updates.update({f"{label}.choices_pkl": choices_pkl,
                              f"{label}.ise_potential_pkl": ise_potential_pkl})
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class ReportChoices(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.ReportChoices"
    name = "Report Choices"
    long_name = "Report ISAAC Choices"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        import html
        import re

        sess = pathlib.Path(state_in.paths["sess.dir"])
        choices = pd.read_pickle(state_in.paths.get("sess.choices_pkl") or sess / "table/choices.pkl")
        if choices.empty:
            raise ValueError("No discovery choices to report")
        blocks = pd.read_pickle(sess / "table/llvm_bbs_new.pkl")
        merged = choices.merge(blocks[["func_name", "bb_name", "start", "end"]],
                               on=["func_name", "bb_name"], how="left", validate="many_to_one")
        dump = pathlib.Path(state_in.paths["trace.output_dir"]) / "generic_mlonmcu.dump"
        instructions = []
        for line in dump.read_text().splitlines():
            match = re.match(r"^\s*([0-9a-fA-F]+):", line)
            if match:
                instructions.append((int(match[1], 16), line))
        columns = ["func_name", "bb_name", "rel_weight", "num_instrs", "freq", "start", "end"]
        sections = []
        for i, row in merged.iterrows():
            if pd.isna(row.start) or pd.isna(row.end):
                raise ValueError(f"Missing block address for {row.func_name}/{row.bb_name}")
            start, end = int(row.start), int(row.end)
            snippet = "\n".join(line for address, line in instructions if start <= address < end)
            if not snippet:
                raise ValueError(f"No disassembly for block at {start:x}")
            values = [row.func_name, row.bb_name, f"{row.rel_weight:.6f}", row.num_instrs,
                      row.freq, f"0x{start:x}", f"0x{end:x}"]
            sections.append(f"<h2>Choice {i}</h2><table><tr>" +
                "".join(f"<th>{name}</th>" for name in columns) + "</tr><tr>" +
                "".join(f"<td>{html.escape(str(value))}</td>" for value in values) +
                f"</tr></table><pre><code>{html.escape(snippet)}</code></pre>")
        fragment = "\n".join(sections)
        output = pathlib.Path(self.step_dir)
        output.mkdir(parents=True, exist_ok=True)
        full, minimal = output / "choices_summary.html", output / "choices_summary_min.html"
        full.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                        '<title>Choices Summary</title><style>body{font-family:sans-serif;margin:2em}'
                        'table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.5em}'
                        'pre{background:#f5f5f5;padding:1em;overflow:auto}</style>'
                        '</head><body><h1>Choices Summary</h1>' +
                        fragment + "</body></html>")
        minimal.write_text(fragment)
        return {}, {}, {"sess.choices_summary_html": full, "sess.choices_summary_min_html": minimal}


@GenIEStep.factory.register()
class PurgeCDFGDB(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.PurgeCDFGDB"
    name = "Purge CDFG DB"
    long_name = "Purge Memgraph CDFG Database"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + [
        Variable("MEMGRAPH_HOST", str, "Hostname or URL of Memgraph Server", default="localhost"),
        Variable("MEMGRAPH_PORT", int, "Port of Memgraph Server", default=7687),
        Variable(
            "ISAAC_PURGE_CDFG_DB",
            bool,
            "Purge Memgraph CDFG DB.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        do_purge = config["ISAAC_PURGE_CDFG_DB"]
        if not do_purge:
            return views_updates, metrics_updates, paths_updates
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        # Purge reads the persisted session endpoint, unlike export/query which
        # honor environment overrides. Refuse an endpoint mismatch explicitly.
        import yaml
        session_config = yaml.safe_load((sess_dir / "config.yml").read_text())
        endpoint = session_config.get("memgraph", {})
        expected = (config.get("MEMGRAPH_HOST", "localhost"), config.get("MEMGRAPH_PORT", 7687))
        actual = (endpoint.get("hostname", "localhost"), endpoint.get("port", 7687))
        if actual != expected:
            raise ValueError(f"Purge session endpoint {actual} differs from configured endpoint {expected}")
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.memgraph.purge_db"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=False,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class PushCDFG(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.PushCDFG"
    name = "Push CDFG"
    long_name = "Push Memgraph CDFG"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + [
        Variable("CDFG_STAGE", int, "LLVM CDFG stage mask used for export and query.", default=32),
        Variable("MEMGRAPH_HOST", str, "Hostname or URL of Memgraph Server", default="localhost"),
        Variable("MEMGRAPH_PORT", int, "Port of Memgraph Server", default=7687),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        mgclient_lib_dir = pathlib.Path(state_in.paths["mgclient.lib_dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        cdfg_stage = self.config["CDFG_STAGE"]
        in_label = "trace"
        full_label = state_in.metrics[f"{in_label}.label"]
        config = self.config
        memgraph_host = config["MEMGRAPH_HOST"]
        memgraph_port = config["MEMGRAPH_PORT"]
        if memgraph_host:
            env["MEMGRAPH_HOST"] = memgraph_host
        if memgraph_port:
            env["MEMGRAPH_PORT"] = str(memgraph_port)
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.cdfg.memgraph", "--label", full_label, "--stage", cdfg_stage],
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        self.run_isaac_toolkit(
            ["isaac_toolkit.backend.memgraph.annotate_bb_weights", "--label", full_label],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class QueryCandidates(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.QueryCandidates"
    name = "Query Candidates"
    long_name = "Query ISE Candidates"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + [
        Variable("CDFG_STAGE", int, "LLVM CDFG stage mask used for export and query.", default=32),
        Variable(
            "ISAAC_QUERY_CONFIG_YAML",
            Optional[str],
            "Custom ISAAC Query config.",
            default=None,
        ),
        Variable("ISAAC_LIMIT_RESULTS", Optional[int], "Maximum database query results.", default=None),
        Variable("ISAAC_XLEN", Optional[int], "Query word size; otherwise use target metrics/toolkit default.", default=None, deprecated_names=["XLEN"]),
        Variable("ISAAC_MIN_ISO_WEIGHT", Optional[float], "Minimum isomorphism weight.", default=None),
        Variable("ISAAC_SCALE_ISO_WEIGHT", Optional[str], "Isomorphism-weight scaling mode.", default=None),
        Variable("ISAAC_SORT_BY", Optional[str], "Candidate metric used for query ordering.", default=None),
        Variable("ISAAC_TOPK", Optional[int], "Maximum retained query candidates.", default=None),
        Variable("ISAAC_PARTITION_WITH_MAXMISO", Optional[str], "MaxMISO partitioning mode.", default=None),
        Variable("MEMGRAPH_HOST", str, "Hostname or URL of Memgraph Server", default="localhost"),
        Variable("MEMGRAPH_PORT", int, "Port of Memgraph Server", default=7687),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        name = "initial"
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        work_dir = sess_dir / "work"
        out_dir = work_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        cdfg_stage = self.config["CDFG_STAGE"]
        in_label = "trace"
        full_label = state_in.metrics[f"{in_label}.label"]
        extra_args = []
        config = self.config
        isaac_query_config_yaml = config["ISAAC_QUERY_CONFIG_YAML"]
        if isaac_query_config_yaml:
            extra_args += ["--query-config-yaml", isaac_query_config_yaml]
        for key, option in (
            ("ISAAC_LIMIT_RESULTS", "--limit-results"), ("ISAAC_XLEN", "--xlen"),
            ("ISAAC_MIN_ISO_WEIGHT", "--min-iso-weight"), ("ISAAC_SCALE_ISO_WEIGHT", "--scale-iso-weight"),
            ("ISAAC_SORT_BY", "--sort-by"), ("ISAAC_TOPK", "--topk"),
            ("ISAAC_PARTITION_WITH_MAXMISO", "--partition-with-maxmiso"),
        ):
            value = config[key]
            if key == "ISAAC_XLEN" and value is None:
                value = state_in.metrics.get("target.xlen")
            if value is not None:
                if key in ("ISAAC_LIMIT_RESULTS", "ISAAC_TOPK", "ISAAC_MIN_ISO_WEIGHT") and value < 0:
                    raise ValueError(f"{key} must be nonnegative")
                if key == "ISAAC_XLEN" and value not in (32, 64):
                    raise ValueError("ISAAC_XLEN must be 32 or 64")
                extra_args += [option, str(value)]
        extra_args += ["--workdir", out_dir]
        extra_args += ["--label", full_label]
        extra_args += ["--stage", cdfg_stage]
        memgraph_host = config["MEMGRAPH_HOST"]
        memgraph_port = config["MEMGRAPH_PORT"]
        if memgraph_host:
            env["MEMGRAPH_HOST"] = memgraph_host
        if memgraph_port:
            env["MEMGRAPH_PORT"] = str(memgraph_port)
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.ise.query_candidates_from_db", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        combined_index_file = out_dir / "combined_index.yml"
        if not combined_index_file.is_file():
            raise FileNotFoundError(combined_index_file)
        names_csv = out_dir / "names.csv"
        assert names_csv.is_file(), f"Missing file: {names_csv}"
        names_df = pd.read_csv(names_csv)
        print("names_df", names_df)
        num_candidates = len(names_df)
        temp = {f"{name}.workdir": out_dir, f"{name}.index": combined_index_file,
                f"{name}.names_csv": names_csv}
        pdf = out_dir / "all_io_subs.pdf"
        if pdf.is_file():
            temp[f"{name}.all_io_subs_pdf"] = pdf
        query_metrics = out_dir / "combined_query_metrics.csv"
        if query_metrics.is_file():
            temp[f"{name}.query_metrics_csv"] = query_metrics
        temp2 = {f"{name}.num_candidates": num_candidates}
        if num_candidates == 0:
            raise ValueError("No candidates found. Aborting...")
        paths_updates.update(temp)
        metrics_updates.update(temp2)
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class GenerateInstrs(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.GenerateInstrs"
    name = "Generate Instrs"
    long_name = "Generate Instructions"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars

    in_stage = "initial"

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        name = self.in_stage
        label = "sess"
        print("state_in", state_in)
        index_file = pathlib.Path(state_in.paths[f"{name}.index"])
        assert index_file.is_file(), f"Missing file: {index_file}"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        work_dir = sess_dir / "work"
        out_dir = work_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        gen_dir = out_dir / "gen"
        gen_dir.mkdir(exist_ok=True)
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        extra_args = []
        extra_args += ["--workdir", out_dir]
        extra_args += ["--gen-dir", gen_dir]
        extra_args += ["--index", index_file]
        encoding_metrics = out_dir / "total_encoding_metrics.csv"
        encoding_score = out_dir / "encoding_score.csv"
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.analyze_encoding", index_file, "-o", encoding_metrics,
             "--score", encoding_score], scripts_dir=scripts_dir, env=env,
        )
        if not encoding_score.is_file():
            raise FileNotFoundError(encoding_score)
        paths_updates[f"{name}.encoding_score_csv"] = encoding_score
        # TODO: write $WORK/encoding_score${SUFFIX}.csv?
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.ise.generate_cdsl", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        paths_updates[f"{name}.gen_dir"] = gen_dir
        total_enc_metrics_csv = out_dir / "total_encoding_metrics.csv"
        assert total_enc_metrics_csv.is_file(), f"Missing file: {total_enc_metrics_csv}"
        total_enc_metrics_df = pd.read_csv(total_enc_metrics_csv)
        assert len(total_enc_metrics_df) == 1
        total_enc_metrics_dict = {
            f"{name}.enc_{key}": val for key, val in total_enc_metrics_df.iloc[0].to_dict().items()
        }
        metrics_updates.update(total_enc_metrics_dict)
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class GenerateETISSCore(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.GenerateETISSCore"
    name = "Generate ETISS Core"
    long_name = "Generate ETISS Core"
    inputs = []
    outputs = []

    in_stage = "initial"

    config_vars = ISAACStep.config_vars + [
        Variable(
            "ISAAC_BASE_EXTENSIONS",
            str,
            "TODO.",
            default="i,m,a,f,d,c,zicsr,zifencei",
        ),
        isaac_core_name_var,
        isaac_set_name_var,
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        name = self.in_stage
        label = "sess"
        index_file = pathlib.Path(state_in.paths[f"{name}.index"])
        assert index_file.is_file(), f"Missing file: {index_file}"
        gen_dir = pathlib.Path(state_in.paths[f"{name}.gen_dir"])
        assert gen_dir.is_dir(), f"Missing dir: {gen_dir}"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        work_dir = sess_dir / "work"
        out_dir = work_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        gen_dir = out_dir / "gen"
        gen_dir.mkdir(exist_ok=True)
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        # xlen = state_in.metrics["target.xlen"]
        # TODO: populate in CollectTargetMetrics
        xlen = state_in.metrics.get("target.xlen", 32)
        assert xlen in [32, 64]
        # TODO: move to isaac yaml
        config = self.config
        core_name = config["ISAAC_CORE_NAME"]
        set_name = config["ISAAC_SET_NAME"]
        base_extensions_str = config["ISAAC_BASE_EXTENSIONS"]
        extra_args = []
        extra_args += ["--workdir", out_dir]
        extra_args += ["--gen-dir", gen_dir]
        extra_args += ["--index", index_file]
        extra_args += ["--core-name", core_name]
        extra_args += ["--set-name", set_name]
        extra_args += ["--xlen", xlen]
        extra_args += ["--auto-encoding"]
        extra_args += ["--split"]
        if True:  # etiss only
            extra_args += ["--semihosting"]
            extra_args += ["--base-extensions", base_extensions_str]
            base_dir = demo_dir / "etiss_arch_riscv" / "rv_base"
            tum_dir = demo_dir / "etiss_arch_riscv"
            extra_includes_str = str(base_dir)
            extra_args += ["--base-dir", base_dir]
            extra_args += ["--tum-dir", tum_dir]
            extra_args += ["--extra-includes", extra_includes_str]
        # TODO: write $WORK/encoding_score${SUFFIX}.csv?
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.iss.generate_etiss_core", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class RetargetLLVM(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.RetargetLLVM"
    name = "Retarget LLVM"
    long_name = "Retarget LLVM"
    inputs = []
    outputs = []
    splitted = False
    in_stage = "initial"

    config_vars = ISAACStep.config_vars + service_vars + [
        Variable("USE_SEAL5_SERVICE", bool, "Retarget LLVM through the job API.", default=False),
        isaac_set_name_var,
        Variable("SEAL5_BUILD_DIR", Optional[str], "Reusable local Seal5 build workspace.", default=None),
        Variable("SEAL5_LLVM_REPO", Optional[str], "Override LLVM clone source for local retargeting.", default=None),
        Variable("SEAL5_LLVM_REF", Optional[str], "Override LLVM branch or tag used by the local adapter.", default=None),
        Variable(
            "USE_SEAL5_DOCKER",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "SEAL5_VERBOSE",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "SEAL5_CLEANUP",
            bool,
            "TODO.",
            default=True,
        ),
        # Variable(
        #     "ISAAC_SET_NAME",
        #     str,
        #     "TODO.",
        #     default="XIsaac",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config.get("USE_SEAL5_SERVICE", False):
            return retarget_service(self, state_in, compiler=True)
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        name = self.in_stage
        label = "sess"
        index_file = pathlib.Path(state_in.paths[f"{name}.index"])
        assert index_file.is_file(), f"Missing file: {index_file}"
        gen_dir = pathlib.Path(state_in.paths[f"{name}.gen_dir"])
        assert gen_dir.is_dir(), f"Missing dir: {gen_dir}"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        work_dir = sess_dir / "work"
        out_dir = work_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        gen_dir = out_dir / "gen"
        gen_dir.mkdir(exist_ok=True)
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        conventional_index = out_dir / "combined_index.yml"
        if index_file.resolve() != conventional_index.resolve():
            import shutil
            shutil.copy2(index_file, conventional_index)
        # xlen = state_in.metrics["target.xlen"]
        # TODO: populate in CollectTargetMetrics
        xlen = state_in.metrics.get("target.xlen", 32)
        assert xlen in [32, 64]
        # TODO: move to isaac yaml
        config = self.config
        docker_dir = demo_dir / "docker"
        seal5_script_local = docker_dir / "seal5_script_local.sh"
        env["SEAL5_SCRIPT_LOCAL"] = seal5_script_local
        mgclient_install_dir = pathlib.Path(state_in.paths.get("mgclient.install_dir") or pathlib.Path(state_in.paths["mgclient.lib_dir"]).parent)
        env["MGCLIENT_INSTALL_DIR"] = mgclient_install_dir
        env["MGCLIENT_ROOT"] = mgclient_install_dir
        enable_ccache = bool(state_in.paths.get("ccache.dir"))
        env["CCACHE"] = str(int(enable_ccache))
        ccache_dir = state_in.paths.get("ccache.dir") or ""
        env["CCACHE_DIR"] = ccache_dir
        cfg_dir = demo_dir / "cfg"
        seal5_cfg_dir = cfg_dir / "seal5"
        env["SEAL5_CFG_DIR"] = seal5_cfg_dir
        seal5_src_dir = pathlib.Path(state_in.paths.get("seal5.src_dir", demo_dir / "seal5"))  # TODO: drop fallback
        env["SEAL5_DIR"] = seal5_src_dir
        llvm_src_dir = pathlib.Path(
            state_in.paths.get("llvm.src_dir", demo_dir / "llvm-project")
        )  # TODO: drop fallback
        env["LLVM_DIR"] = llvm_src_dir
        env["LLVM_REPO"] = config["SEAL5_LLVM_REPO"] or str(llvm_src_dir)
        if config["SEAL5_LLVM_REF"]:
            env["LLVM_REF"] = config["SEAL5_LLVM_REF"]
        set_name = config["ISAAC_SET_NAME"]
        use_docker = config["USE_SEAL5_DOCKER"]
        shared_build = config["SEAL5_BUILD_DIR"] or state_in.paths.get("temporary.initial.seal5_build")
        if not use_docker and (config["SEAL5_LLVM_REPO"] or config["SEAL5_LLVM_REF"] or shared_build):
            # Toolkit versions overwrite LLVM_REPO/LLVM_REF before invoking the
            # script. Apply explicit overrides at that final adapter boundary.
            env["GENIE_SEAL5_SCRIPT"] = str(seal5_script_local)
            if shared_build:
                env["GENIE_SEAL5_HOME"] = str(pathlib.Path(shared_build).resolve())
            if config["SEAL5_LLVM_REPO"]:
                env["GENIE_LLVM_REPO"] = config["SEAL5_LLVM_REPO"]
            if config["SEAL5_LLVM_REF"]:
                env["GENIE_LLVM_REF"] = config["SEAL5_LLVM_REF"]
            env["SEAL5_SCRIPT_LOCAL"] = str(pathlib.Path(__file__).with_name("seal5_local_adapter.py"))
        extra_args = []
        extra_args += ["--workdir", out_dir]
        # extra_args += ["--label", ?]
        # print("splitted", self.splitted)
        # return views_updates, metrics_updates, paths_updates

        if self.splitted:
            seal5_name = "seal5_splitted"
            extra_args += ["--splitted"]
        else:
            seal5_name = "seal5"
        if use_docker:
            mode = "docker"
            extra_args += ["--docker"]
        else:
            mode = "local"
            extra_args += ["--local"]
        verbose = config["SEAL5_VERBOSE"]
        cleanup = config["SEAL5_CLEANUP"]
        if verbose:
            extra_args += ["--verbose"]
        if cleanup:
            extra_args += ["--cleanup"]
        cfg_files = [
            seal5_cfg_dir / "patches.yml",
            seal5_cfg_dir / "llvm.yml",
            seal5_cfg_dir / "git.yml",
            seal5_cfg_dir / "filter.yml",
            seal5_cfg_dir / "tools.yml",
            seal5_cfg_dir / "riscv.yml",
        ]
        extra_args += cfg_files
        # TODO: write $WORK/encoding_score${SUFFIX}.csv?
        self.run_isaac_toolkit(
            ["isaac_toolkit.flow.demo.stage.retargeting.llvm", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        seal5_out_dir = out_dir / mode / seal5_name
        seal5_llvm_install_dir = seal5_out_dir / "llvm_install"
        assert seal5_llvm_install_dir.is_dir(), f"Missing dir: {seal5_llvm_install_dir}"
        seal5_score_csv = seal5_out_dir / "seal5_score.csv"
        assert seal5_score_csv.is_file(), f"Missing file: {seal5_score_csv}"
        seal5_score_df = pd.read_csv(seal5_score_csv)
        assert len(seal5_score_df) > 0
        avg_seal5_score = seal5_score_df["seal5_score"].mean()
        total_count = len(seal5_score_df)
        unsupported_count = len(seal5_score_df[seal5_score_df["seal5_score"] < 1.0])
        has_unsupported = unsupported_count > 0
        seal5_metrics_dict = {
            f"{name}.{seal5_name}.avg_seal5_score": avg_seal5_score,
            f"{name}.{seal5_name}.total_count": total_count,
            f"{name}.{seal5_name}.unsupported_count": unsupported_count,
            f"{name}.{seal5_name}.has_unsupported": has_unsupported,
        }
        metrics_updates.update(seal5_metrics_dict)
        # print("seal5_score_df", seal5_score_df)

        paths_updates[f"{name}.{seal5_name}.seal5_score_csv"] = seal5_score_csv
        paths_updates[f"{name}.{seal5_name}.install_dir"] = seal5_llvm_install_dir
        temporary_build = pathlib.Path(shared_build) if shared_build and not use_docker else out_dir / mode / "temp" / "seal5_llvm"
        if temporary_build.is_dir():
            paths_updates[f"temporary.{name}.seal5_build"] = temporary_build
        diff_csv = seal5_out_dir / "seal5_reports" / "diff.csv"
        if diff_csv.is_file():
            paths_updates[f"{name}.{seal5_name}.diff_csv"] = diff_csv
        if self.splitted:
            record_global_artifacts(index_file, LLVM_INSTALL_DIR=seal5_llvm_install_dir)
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class RetargetISS(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.RetargetISS"
    name = "Retarget ISS"
    long_name = "Retarget ISS"
    inputs = []
    outputs = []

    in_stage = "initial"
    perf_sim = False

    config_vars = ISAACStep.config_vars + service_vars + [
        Variable("USE_ETISS_SERVICE", bool, "Retarget ETISS through the job API.", default=False),
        Variable("USE_ETISS_PERF_SERVICE", bool, "Retarget PerfSim through the job API.", default=False),
        Variable("USE_ETISS_PERF_DOCKER", bool, "Run PerfSim retargeting in Docker.", default=False),
        isaac_set_name_var,
        Variable(
            "USE_ETISS_DOCKER",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "ETISS_VERBOSE",
            bool,
            "TODO.",
            default=False,
        ),
        isaac_core_name_var,
        Variable(
            "ETISS_CLEANUP",
            bool,
            "TODO.",
            default=True,
        ),
        # Variable(
        #     "ISAAC_SET_NAME",
        #     str,
        #     "TODO.",
        #     default="XIsaac",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config.get("USE_ETISS_PERF_SERVICE" if self.perf_sim else "USE_ETISS_SERVICE", False):
            return retarget_service(self, state_in)
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        name = self.in_stage
        label = "sess"
        index_file = pathlib.Path(state_in.paths[f"{name}.index"])
        assert index_file.is_file(), f"Missing file: {index_file}"
        gen_dir = pathlib.Path(state_in.paths[f"{name}.gen_dir"])
        assert gen_dir.is_dir(), f"Missing dir: {gen_dir}"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        work_dir = sess_dir / "work"
        out_dir = work_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        gen_dir = out_dir / "gen"
        gen_dir.mkdir(exist_ok=True)
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        # The toolkit retargeting stages still require this conventional filename.
        # Keep the canonical state index authoritative for noninitial stages.
        conventional_index = out_dir / "combined_index.yml"
        if index_file.resolve() != conventional_index.resolve():
            import shutil
            shutil.copy2(index_file, conventional_index)
        if self.perf_sim:
            import yaml
            index_data = yaml.safe_load(conventional_index.read_text())
            artifacts = index_data.setdefault("global", {}).setdefault("artifacts", {})
            hls_output = state_in.paths.get(f"{name}.hls.default.output_dir")
            if hls_output:
                artifacts["HLS_DIR"] = str(pathlib.Path(hls_output).parent)
                conventional_index.write_text(yaml.safe_dump(index_data, sort_keys=False))
            if not artifacts.get("HLS_DIR"):
                raise ValueError("PerfSim retargeting requires HLS_DIR in the index or stage HLS output")
        # xlen = state_in.metrics["target.xlen"]
        # TODO: populate in CollectTargetMetrics
        xlen = state_in.metrics.get("target.xlen", 32)
        assert xlen in [32, 64]
        # TODO: move to isaac yaml
        config = self.config
        docker_dir = demo_dir / "docker"
        etiss_script_local = docker_dir / ("etiss_perf_script_local.sh" if self.perf_sim else "etiss_script_local.sh")
        env["ETISS_PERF_SCRIPT_LOCAL" if self.perf_sim else "ETISS_SCRIPT_LOCAL"] = etiss_script_local
        enable_ccache = bool(state_in.paths.get("ccache.dir"))
        env["CCACHE"] = str(int(enable_ccache))
        ccache_dir = state_in.paths.get("ccache.dir") or ""
        env["CCACHE_DIR"] = ccache_dir
        # TODO: use already cloned etiss repo?
        # core_name = config["ISAAC_CORE_NAME"]
        use_docker = config["USE_ETISS_PERF_DOCKER" if self.perf_sim else "USE_ETISS_DOCKER"]
        extra_args = []
        extra_args += ["--workdir", out_dir]
        # extra_args += ["--label", ?]
        # print("splitted", self.splitted)
        # return views_updates, metrics_updates, paths_updates

        if use_docker:
            mode = "docker"
            extra_args += ["--docker"]
        else:
            mode = "local"
            extra_args += ["--local"]
        verbose = config["ETISS_VERBOSE"]
        if verbose:
            extra_args += ["--verbose"]
        cleanup = config["ETISS_CLEANUP"]
        if cleanup:
            extra_args += ["--cleanup"]
        # TODO: write $WORK/encoding_score${SUFFIX}.csv?
        self.run_isaac_toolkit(
            ["isaac_toolkit.flow.demo.stage.retargeting." + ("iss_perf" if self.perf_sim else "iss"), *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        etiss_name = "etiss_perf" if self.perf_sim else "etiss"
        etiss_out_dir = out_dir / mode / etiss_name
        etiss_install_dir = etiss_out_dir / f"{etiss_name}_install"
        assert etiss_install_dir.is_dir(), f"Missing dir: {etiss_install_dir}"
        paths_updates[f"{name}.{etiss_name}.install_dir"] = etiss_install_dir
        if self.perf_sim:
            uarchs_csv = etiss_out_dir / "uarchs.csv"
            if not uarchs_csv.is_file():
                raise FileNotFoundError(uarchs_csv)
            paths_updates[f"{name}.etiss_perf.uarchs_csv"] = uarchs_csv
            from .service import extract_etiss_source
            paths_updates[f"{name}.etiss_perf.src_dir"] = extract_etiss_source(etiss_out_dir)
        temporary_build = out_dir / mode / "temp" / etiss_name
        if temporary_build.is_dir():
            paths_updates[f"temporary.{name}.{etiss_name}_build"] = temporary_build
        patch_stat = etiss_out_dir / "etiss_patch.stat"
        if patch_stat.is_file():
            paths_updates[f"{name}.{etiss_name}.patch_stat"] = patch_stat
        record_global_artifacts(index_file, **{
            "ETISS_PERF_INSTALL_DIR" if self.perf_sim else "ETISS_INSTALL_DIR": etiss_install_dir
        })
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class CompareISEBench(ISAACStep):
    """
    TODO.
    """

    perf_sim = False

    id = "ISAAC.CompareISEBench"
    name = "Compare ISE Bench"
    long_name = "Compare ISE Bench"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + []
    per_instr = False
    others = False
    in_stage = "initial"

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        index_file = pathlib.Path(state_in.paths[f"{self.in_stage}.index"])
        assert index_file.is_file(), f"Missing file: {index_file}"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        work_dir = sess_dir / "work"
        out_dir = work_dir / self.in_stage
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = "_others" if self.others else ""
        if self.per_instr:
            suffix += "_per_instr"
        report_compare = pathlib.Path(state_in.paths[f"{self.in_stage}.ise_bench{suffix}.output_dir"]) / "report.csv"
        report_compare_mem = pathlib.Path(state_in.paths[f"{self.in_stage}.ise_bench{suffix}_mem.output_dir"]) / "report.csv"
        for report in (report_compare, report_compare_mem):
            if not report.is_file():
                raise FileNotFoundError(report)
        compare_csv = out_dir / f"compare{suffix}.csv"
        if self.others:
            mem_csv = out_dir / "compare_others_mem.csv"
            for report, output, extra in ((report_compare, compare_csv, []),
                                          (report_compare_mem, mem_csv, ["--mem"])):
                self.run_subprocess(
                    [scripts_dir / "launch.sh", "python3", scripts_dir / "analyze_reuse.py",
                     report, "--print-df", "--output", output, *extra],
                    env=env, check=True, **kwargs,
                )
                if not output.is_file():
                    raise FileNotFoundError(output)
            return {}, {}, {f"{self.in_stage}.compare_others_csv": compare_csv,
                            f"{self.in_stage}.compare_others_mem_csv": mem_csv}
        extra_args = [report_compare, "--mem-report", report_compare_mem, "--print-df", "--output", compare_csv]
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.analyze_compare_perf" if self.perf_sim else "isaac_toolkit.utils.analyze_compare", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=None,
            has_force=False,
            env=env,
        )
        if self.per_instr:
            self.run_isaac_toolkit(
                ["isaac_toolkit.utils.annotate_per_instr_metrics", index_file, "--inplace", "--report", compare_csv],
                scripts_dir=scripts_dir,
                sess_dir=None,
                has_force=False,
                env=env,
            )
        assert compare_csv.is_file(), f"Missing file: {compare_csv}"
        paths_updates[f"{self.in_stage}.compare{suffix}_csv"] = compare_csv
        compare_df = pd.read_csv(compare_csv)
        if self.perf_sim:
            ranking = out_dir / "uarch_ranking.csv"
            self.run_isaac_toolkit(
                ["isaac_toolkit.utils.rank_uarchs", compare_csv, "--uarchs-csv",
                 state_in.paths[f"{self.in_stage}.etiss_perf.uarchs_csv"], "--output", ranking],
                scripts_dir=scripts_dir, sess_dir=None, has_force=False, env=env,
            )
            if not ranking.is_file():
                raise FileNotFoundError(ranking)
            paths_updates[f"{self.in_stage}.uarch_ranking_csv"] = ranking
        if not self.others and not self.per_instr and not self.perf_sim:
            assert len(compare_df) == 2
            cols = ["Run Instructions (rel.)", "ROM code (rel.)"]
            for col in cols:
                metrics_updates[f"{self.in_stage}.compare{suffix}.{col}"] = compare_df[col].iloc[1]
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class CompareISEPerfSimBench(CompareISEBench):
    """Merge instruction/cycle/memory reports and rank measured microarchitectures."""
    id = "ISAAC.CompareISEPerfSimBench"
    perf_sim = True


# @GenIEStep.factory.register()
# class CompareISEBenchOthers(GenIEStep):
#     """
#     TODO.
#     """
#
#     id = "ISAAC.CompareISEBenchOthers"
#     name = "Compare ISE Bench Others"
#     long_name = "Compare ISE Bench (Others)"
#     inputs = []
#     outputs = []
#
#     config_vars = [
#         # Variable(
#         #     "VERILOG_FILES",
#         #     List[Path],
#         #     "The paths of the design's Verilog files.",
#         # ),
#     ]
#
#     def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
#         kwargs, env = self.extract_env(kwargs)
#         views_updates: ViewsUpdate = {}
#         metrics_updates: MetricsUpdate = {}
#         # config = self.config
#         errors_count = 0
#         metrics_updates.update({"design__lint_error__count": errors_count})
#         sleep(5.0)
#         return views_updates, metrics_updates, {}
#
#
# @GenIEStep.factory.register()
# class CompareISEBenchPerInstr(GenIEStep):
#     """
#     TODO.
#     """
#
#     id = "ISAAC.CompareISEBenchPerInstr"
#     name = "Compare ISE Bench Per Instr"
#     long_name = "Compare ISE Bench (per Instr)"
#     inputs = []
#     outputs = []
#
#     config_vars = [
#         # Variable(
#         #     "VERILOG_FILES",
#         #     List[Path],
#         #     "The paths of the design's Verilog files.",
#         # ),
#     ]
#
#     def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
#         kwargs, env = self.extract_env(kwargs)
#         views_updates: ViewsUpdate = {}
#         metrics_updates: MetricsUpdate = {}
#         # config = self.config
#         errors_count = 0
#         metrics_updates.update({"design__lint_error__count": errors_count})
#         sleep(5.0)
#         return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class FilterCandidates(ISAACStep):
    """
    TODO.
    """

    id = "ISAAC.FilterCandidates"
    name = "Filter Candidates"
    long_name = "Filter ISE Candidates"
    inputs = []
    outputs = []

    config_vars = ISAACStep.config_vars + [
        Variable(
            "FILTER_MIN_SEAL5_SCORE",
            Optional[float],
            "Minimum compiler support score; null disables this threshold.",
            default=0.5,
            deprecated_names=["MIN_SEAL5_SCORE"],
        ),
        Variable(
            "FILTER_MIN_RUNTIME_REDUCTION_REL",
            Optional[float],
            "Minimum measured runtime reduction; null disables this threshold.",
            default=0.005,
        ),
        Variable(
            "FILTER_MIN_UTIL_REL",
            Optional[float],
            "Minimum utilization score for subsequent filtering; null disables this threshold.",
            default=0.005,
            deprecated_names=["MIN_UTIL_SCORE"],
        ),
    ]
    in_stage = "initial"
    out_stage = "filtered"

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        label = "sess"
        index_file = pathlib.Path(state_in.paths[f"{self.in_stage}.index"])
        assert index_file.is_file(), f"Missing file: {index_file}"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        work_dir = sess_dir / "work"
        out_dir = work_dir / self.out_stage
        out_dir.mkdir(parents=True, exist_ok=True)
        out_index = out_dir / "index.yml"
        if self.in_stage == self.out_stage:
            raise ValueError("Filtering requires a distinct output stage")
        if self.in_stage not in ("initial", "filtered", "filtered_selected"):
            raise ValueError(f"Unsupported filtering stage: {self.in_stage}")
        sankey = out_dir / "sankey.md"
        extra_args = [index_file, "-o", out_index, "--sankey", sankey]
        config = self.config
        thresholds = (
            [("--min-seal5-score", "FILTER_MIN_SEAL5_SCORE"),
             ("--min-runtime-reduction-rel", "FILTER_MIN_RUNTIME_REDUCTION_REL")]
            if self.in_stage == "initial" else [("--min-util-score", "FILTER_MIN_UTIL_REL")]
        )
        for option, key in thresholds:
            value = config[key]
            if value is not None:
                extra_args += [option, str(value)]
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.filter_index", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=None,
            has_force=False,
            env=env,
        )
        names_csv = out_dir / "names.csv"
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.names_helper", out_index, "-o", names_csv],
            scripts_dir=scripts_dir,
            sess_dir=None,
            has_force=False,
            env=env,
        )
        assert out_index.is_file(), f"Missing file: {out_index}"
        paths_updates[f"{self.out_stage}.index"] = out_index
        paths_updates[f"{self.out_stage}.workdir"] = out_dir
        paths_updates[f"{self.out_stage}.names_csv"] = names_csv
        if not sankey.is_file():
            raise FileNotFoundError(sankey)
        paths_updates[f"{self.out_stage}.sankey"] = sankey
        assert names_csv.is_file(), f"Missing file: {names_csv}"
        names_df = pd.read_csv(names_csv)
        print("names_df", names_df)
        num_candidates = len(names_df)
        prev_candidates = state_in.metrics[f"{self.in_stage}.num_candidates"]
        filtered_candidates = prev_candidates - num_candidates
        assert num_candidates > 0, "No candidates found. Aborting..."
        metrics_updates[f"{self.out_stage}.num_candidates"] = num_candidates
        metrics_updates[f"{self.out_stage}.filtered_candidates"] = filtered_candidates
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class CreateSpecGraph(ISAACStep):
    """Detect candidate specializations for a particular candidate stage."""

    id = "ISAAC.CreateSpecGraph"
    name = "Create Spec Graph"
    long_name = "Create Specialization Graph"
    inputs = []
    outputs = []
    config_vars = ISAACStep.config_vars
    in_stage = "filtered"

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        index_file = pathlib.Path(state_in.paths[f"{self.in_stage}.index"])
        if not index_file.is_file():
            raise FileNotFoundError(index_file)
        work_dir = pathlib.Path(state_in.paths[f"{self.in_stage}.workdir"])
        graph_file = work_dir / "spec_graph.pkl"
        self.run_isaac_toolkit(
            ["tool.detect_specializations", index_file, "--graph", graph_file, "--noop"],
            scripts_dir=pathlib.Path(state_in.paths["demo.dir"]) / "scripts",
            env=env,
        )
        if not graph_file.is_file():
            raise FileNotFoundError(graph_file)
        return {}, {}, {f"{self.in_stage}.spec_graph": graph_file}


@GenIEStep.factory.register()
class RetargetPerfSim(RetargetISS):
    id = "ISAAC.RetargetPerfSim"
    name = long_name = "Retarget Performance Simulator"
    perf_sim = True
