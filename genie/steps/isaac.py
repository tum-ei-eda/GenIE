import pathlib
from time import sleep
from typing import Tuple, Optional, List, Dict

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate, PathsUpdate
from genie.config import Variable
from genie.state import State

import pandas as pd

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
        if log_level is not None:
            command += ["--log", log_level]
        if progress and has_progress:
            command += ["--progress"]
        if force and has_force:
            command += ["--force"]
        if mgclient_lib_dir is not None:
            ld_lib_path = env.get("LD_LIBRARY_PATH", "")
            ld_lib_path_new = f"{mgclient_lib_dir}:{ld_lib_path}"
            env["LD_LIBRARY_PATH"] = ld_lib_path_new
        pythonpath = env.get("LD_LIBRARY_PATH", "")
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
        config_yaml = config["ISAAC_TOOLKIT_CONFIG_YAML"]
        if config_yaml is not None:
            self.run_isaac_toolkit(
                ["isaac_toolkit.frontend.cfg.yaml", config_yaml],
                scripts_dir=scripts_dir,
                sess_dir=sess_dir,
                has_force=True,
                env=env,
            )
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
        assert len(ise_potential_df) == 1
        new_metrics = {f"{label}.{key}": val for key, val in ise_potential_df.iloc[0].to_dict().items()}
        metrics_updates.update(new_metrics)
        choices_pkl = sess_dir / "table" / "choices.pkl"
        assert choices_pkl.is_file(), f"Missing file: {choices_pkl}"
        choices_df = pd.read_pickle(choices_pkl)
        temp = {"num_chocies": len(choices_df), "total_choices_rel_weight": choices_df["rel_weight"].sum()}
        new_metrics2 = {f"{label}.{key}": val for key, val in temp.items()}
        metrics_updates.update(new_metrics2)
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
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        raise NotImplementedError
        label = "sess"
        sess_dir = pathlib.Path(state_in.paths[f"{label}.dir"])
        assert sess_dir.is_dir(), f"Missing dir: {sess_dir}"
        self.run_isaac_toolkit(
            ["isaac_toolkit.report.choices"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        return views_updates, metrics_updates, paths_updates


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
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.memgraph.purge_db"],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
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

    config_vars = ISAACStep.config_vars

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
        cdfg_stage = 32  # TODO: move to isaac config
        in_label = "trace"
        full_label = state_in.metrics[f"{in_label}.label"]
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
        Variable(
            "ISAAC_QUERY_CONFIG_YAML",
            Optional[str],
            "Custom ISAAC Query config.",
            default=None,
        ),
        # TODO: move to flow/sess settings?
        # ISAAC_LIMIT_RESULTS
        # ISAAC_MIN_ISO_WEIGHT=0.05
        # ISAAC_SCALE_ISO_WEIGHT=${ISAAC_SCALE_ISO_WEIGHT:-"auto"}
        # XLEN=${XLEN:-32}
        # ISAAC_SORT_BY="IsoWeight"
        # ISAAC_TOPK
        # ISAAC_PARTITION_WITH_MAXMISO=auto
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
        cdfg_stage = 32  # TODO: move to isaac config
        in_label = "trace"
        full_label = state_in.metrics[f"{in_label}.label"]
        extra_args = []
        extra_args += ["--workdir", out_dir]
        extra_args += ["--label", full_label]
        extra_args += ["--stage", cdfg_stage]
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.ise.query_candidates_from_db", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        combined_index_file = out_dir / "combined_index.yml"
        names_csv = out_dir / "names.csv"
        assert names_csv.is_file(), f"Missing file: {names_csv}"
        names_df = pd.read_csv(names_csv)
        print("names_df", names_df)
        num_candidates = len(names_df)
        temp = {f"{name}.workdir": out_dir, f"{name}.index": combined_index_file}
        temp2 = {f"{name}.num_candidates": num_candidates}
        assert num_candidates > 0, "No candidates found. Aborting..."
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

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        name = "initial"
        label = "sess"
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
        # TODO: write $WORK/encoding_score${SUFFIX}.csv?
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.ise.generate_cdsl", *extra_args],
            scripts_dir=scripts_dir,
            sess_dir=sess_dir,
            has_force=True,
            env=env,
        )
        paths_updates[f"{name}.gen_dir"] = gen_dir
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

    config_vars = ISAACStep.config_vars + [
        Variable(
            "ISAAC_BASE_EXTENSIONS",
            str,
            "TODO.",
            default="i,m,a,f,d,c,zicsr,zifencei",
        ),
        Variable(
            "ISAAC_CORE_NAME",
            str,
            "TODO.",
            default="XIsaacCore",
        ),
        Variable(
            "ISAAC_SET_NAME",
            str,
            "TODO.",
            default="XIsaac",
        ),
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
class RetargetLLVM(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.RetargetLLVM"
    name = "Retarget LLVM"
    long_name = "Retarget LLVM"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class RetargetISS(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.RetargetISS"
    name = "Retarget ISS"
    long_name = "Retarget ISS"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CompareBench(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.CompareBench"
    name = "Compare Bench"
    long_name = "Compare Bench"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CompareBenchOthers(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.CompareBenchOthers"
    name = "Compare Bench Others"
    long_name = "Compare Bench (Others)"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CompareBenchPerInstr(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.CompareBenchPerInstr"
    name = "Compare Bench Per Instr"
    long_name = "Compare Bench (per Instr)"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class FilterCandidates(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.FilterCandidates"
    name = "Filter Candidates"
    long_name = "Filter ISE Candidates"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CreateSpecGraph(GenIEStep):
    """
    TODO.
    """

    id = "ISAAC.CreateSpecGraph"
    name = "Create Spec Graph"
    long_name = "Create Specialization Graph"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        scripts_dir = demo_dir / "scripts"
        sess_dir = self.run_dir
        assert scripts_dir is not None
        launch_script = scripts_dir / "launch.sh"
        assert launch_script.is_file(), f"Missing file: {launch_script}"
        python_exe = "python3"  # TODO
        command = [launch_script, python_exe, "-m", "mlonmcu.cli.main"]
        check = True
        args = []
        _ = self.run_subprocess(
            args,
            env=env,
            check=check,
            **kwargs,
        )
        return views_updates, metrics_updates, paths_updates
