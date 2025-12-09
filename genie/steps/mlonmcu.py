import os
import pathlib

# from time import sleep
from typing import Tuple, Optional, Union, Dict, List

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate, PathsUpdate
from genie.config import Variable
from genie.state import State
from genie.common import Path
from .common_vars import mlonmcu_docker_vars
from .isaac import isaac_core_name_var

import yaml
import pandas as pd


# @GenIEStep.factory.register()
class MLonMCUStep(GenIEStep):
    """
    TODO.
    """

    config_vars = [
        Variable(
            "BENCH",
            str,
            "The benchmark.",
        ),
        Variable(
            "BACKEND",
            str,
            "TODO.",
            default="none",
        ),
        Variable(
            "LAYOUT",
            str,
            "TODO.",
            default="default",
        ),
        Variable(
            "ENABLE_VEXT",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "VLEN",
            Optional[int],
            "TODO.",
        ),
        Variable(
            "ELEN",
            Optional[int],
            "TODO.",
        ),
        Variable(
            "EMBEDDED_VEXT",
            bool,
            "TODO.",
            default=False,
        ),
        # TODO: share common (target) vars
        Variable(
            "TARGET",
            str,
            "TODO.",
            default="etiss_rv32",
        ),
        Variable(
            "FPU",
            str,
            "TODO.",
            default="default",
        ),
        Variable(
            "ARCH",
            str,
            "TODO.",
            default="rv32imfd",
        ),
        Variable(
            "ABI",
            str,
            "TODO.",
            default="ilp32d",
        ),
        Variable(
            "PLATFORM",
            str,
            "TODO.",
            default="mlif",
        ),
        Variable(
            "TOOLCHAIN",
            str,
            "TODO.",
            default="llvm",
        ),
        Variable(
            "TARGET",
            str,
            "TODO.",
            default="etiss_rv32",
        ),
        Variable(
            "OPTIMIZE",
            Union[int, str],
            "TODO.",
            default="3",
        ),
        Variable(
            "UNROLL",
            Union[str, int],
            "TODO.",
            default=False,
        ),
        Variable(
            "AUTO_VECTORIZE",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "GLOBAL_ISEL",
            bool,
            "TODO.",
            default=False,
        ),
        *mlonmcu_docker_vars,
        Variable(
            "MLONMCU_NUM_PARALLEL",
            Optional[str],
            "TODO.",
            default=None,
        ),
        Variable(
            "MLONMCU_MLIF_THREADS",
            Optional[str],
            "TODO.",
            default=None,
        ),
        Variable(
            "VERBOSE",
            bool,
            "TODO.",
            default=False,
        ),
    ]

    @property
    def run_dir(self):
        return pathlib.Path(self.step_dir).parent

    def get_mlonmcu_config(self):
        config = self.config
        ret = {}
        ret["target"] = config["TARGET"]
        ret["unroll"] = config["UNROLL"]
        ret["optimize"] = config["OPTIMIZE"]
        ret["arch"] = config["ARCH"]
        ret["abi"] = config["ABI"]
        ret["global_isel"] = config["GLOBAL_ISEL"]
        ret["backend"] = config["BACKEND"]
        ret["layout"] = config["LAYOUT"]
        ret["enable_vext"] = config["ENABLE_VEXT"]
        ret["vlen"] = config["VLEN"]
        ret["elen"] = config["ELEN"]
        ret["embedded_vext"] = config["EMBEDDED_VEXT"]
        ret["fpu"] = config["FPU"]
        ret["auto_vectorize"] = config["AUTO_VECTORIZE"]
        ret["verbose"] = config["VERBOSE"]
        ret["platform"] = config["PLATFORM"]
        ret["toolchain"] = config["TOOLCHAIN"]
        ret["num_parallel"] = config["MLONMCU_NUM_PARALLEL"]
        ret["mlif_threads"] = config["MLONMCU_MLIF_THREADS"]
        # TODO: parallel
        return ret

    def get_mlonmcu_args(
        self,
        dest_dir: Path,
        stage: str,
        bench_name: str,
        session_label: str,
        target: str,
        unroll: str,
        optimize: str,
        arch: str,
        abi: str,
        global_isel: bool,
        backend: str,
        layout: str,
        enable_vext: bool,
        vlen: Optional[int],
        elen: Optional[int],
        embedded_vext: bool,
        fpu: str,
        auto_vectorize: bool,
        verbose: bool,
        platform: str,
        toolchain: str,
        log_instrs: bool = False,
        num_parallel: Optional[str] = None,
        mlif_threads: Optional[str] = None,
        llvm_basic_block_sections: bool = False,
        compare_rows: bool = False,
        compare_rows_to_compare: Optional[List[str]] = None,
        llvm_install_dir: Optional[Path] = None,
        etissvp_script: Optional[Path] = None,
        etiss_cpu_arch: Optional[str] = None,
        config_gen: Optional[List[Dict]] = None,
    ):
        ret = ["flow", stage, "--dest", dest_dir, "--label", session_label]
        ret += [bench_name]
        ret += ["--target", target]
        ret += ["--backend", backend]
        assert platform == "mlif"
        if toolchain is not None:
            ret += ["-c", f"{platform}.toolchain={toolchain}"]
        if layout is not None:
            ret += ["-c", f"{backend}.desired_layout={layout}"]
        if unroll is not None:
            ret += ["-c", f"mlif.unroll_loops={unroll}"]
        if optimize is not None:
            ret += ["-c", f"mlif.optimize={optimize}"]
        if global_isel is not None:
            ret += ["-c", f"mlif.global_isel={int(global_isel)}"]
        if arch is not None:
            ret += ["-c", f"{target}.arch={arch}"]
        if abi is not None:
            ret += ["-c", f"{target}.abi={abi}"]
        if fpu is not None:
            ret += ["-c", f"{target}.fpu={fpu}"]
        if log_instrs:
            ret += ["-f", "log_instrs", "-c", "log_instrs.to_file=1"]
        if enable_vext:
            ret += ["-f", "vext"]
            if vlen is not None:
                ret += ["-c", f"vext.vlen={vlen}"]
            if elen is not None:
                ret += ["-c", f"vext.elen={elen}"]
            if auto_vectorize:
                ret += ["-f", "auto_vectorize"]
        if llvm_basic_block_sections:
            ret += ["-f", "llvm_basic_block_sections"]
        config2cols = (True,)
        if config2cols:
            config2cols_limit = [f"{target}.final_arch"]
            config2cols_limit_str = ",".join(config2cols_limit)
            ret += ["--post", "config2cols"]
            ret += ["-c", f"config2cols.limit={config2cols_limit_str}"]
        rename_cols = True
        if rename_cols:
            rename_cols_mapping = {f"config_{target}.final_arch": "Arch"}
            rename_cols_mapping_str = (
                "{" + ",".join([f"'{key}':'{val}'" for key, val in rename_cols_mapping.items()]) + "}"
            )
            ret += ["--post", "rename_cols"]
            ret += ["-c", f"rename_cols.mapping={rename_cols_mapping_str}"]
        if compare_rows:
            ret += ["--post", "compare_rows"]
            if compare_rows_to_compare is not None:
                compare_rows_to_compare_str = ",".join(map(lambda x: f"{x}", compare_rows_to_compare))
                ret += ["-c", f"compare_rows.to_compare={compare_rows_to_compare_str}"]
        if llvm_install_dir is not None:
            ret += ["-c", f"llvm.install_dir={llvm_install_dir}"]
        if etissvp_script is not None:
            assert target.startswith("etiss")
            ret += ["-c", f"etissvp.script={etissvp_script}"]
        if etiss_cpu_arch is not None:
            assert target.startswith("etiss")
            ret += ["-c", f"{target}.cpu_arch={etiss_cpu_arch}"]
        if config_gen is not None:
            assert isinstance(config_gen, list)
            for d in config_gen:
                assert isinstance(d, dict)
                temp = [f"{key}={val}" for key, val in d.items()]
                ret += ["--config-gen", *temp]
        if num_parallel is not None:
            if num_parallel == "auto":
                ret += ["--parallel"]
            else:
                ret += ["--parallel", str(num_parallel)]
        if mlif_threads is not None:
            if mlif_threads == "auto":
                raise NotImplementedError
            else:
                ret += ["-c", f"mlif.num_threads={mlif_threads}"]
        ret += ["-c", "run.export_optional=1"]
        if verbose:
            ret += ["-v"]
        # print("ret", ret)
        # input("!")
        return ret

    def get_mlonmcu_env(self, mlonmcu_home: Path, env: Optional[Dict] = None, mgclient_lib_dir: Optional[Path] = None):
        if env is None:
            env = os.environ.copy()
        config = self.config
        use_docker = config["USE_MLONMCU_DOCKER"]
        if not use_docker:
            env["MLONMCU_HOME"] = str(mlonmcu_home)
        if mgclient_lib_dir is not None:
            ld_lib_path = env.get("LD_LIBRARY_PATH", "")
            ld_lib_path_new = f"{mgclient_lib_dir}:{ld_lib_path}"
            env["LD_LIBRARY_PATH"] = ld_lib_path_new
        return env

    def get_mlonmcu_mounts(self, mlonmcu_home: Path):
        ret = {}
        run_dir = self.run_dir
        ret[run_dir] = run_dir
        config = self.config
        use_min_docker = config["USE_MLONMCU_MIN_DOCKER"]
        if use_min_docker:
            ret["MLONMCU_HOME"] = mlonmcu_home
        return ret

    def get_mlonmcu_command(
        self,
        mlonmcu_home: Path,
        scripts_dir: Optional[Path] = None,
        mgclient_lib_dir: Optional[Path] = None,
    ):
        config = self.config
        use_docker = config["USE_MLONMCU_DOCKER"]
        use_min_docker = config["USE_MLONMCU_MIN_DOCKER"]
        docker_engine = "docker"  # TODO
        run_dir = self.run_dir
        # TODO: handle venv
        if use_docker and use_min_docker:
            raise RuntimeError("USE_MLONMCU_DOCKER and USE_MLONMCU_MIN_DOCKER cannot both be enabled")

        if use_min_docker or use_docker:
            full_image = config["MLONMCU_IMAGE"]
            min_image = config["MLONMCU_MIN_IMAGE"]
            image = min_image if use_min_docker else full_image
            mounts = self.get_mlonmcu_mounts(mlonmcu_home)
            mount_args = sum(
                [["-v", f"{host_path}:{container_path}"] for host_path, container_path in mounts.items()], []
            )
            env = self.get_mlonmcu_env(mlonmcu_home, None, mgclient_lib_dir=mgclient_lib_dir)
            env_args = sum([["-e", f"{key}={val}"] for key, val in env.items()], [])
            command = [
                docker_engine,
                "run",
                "-i",
                "--rm",
                *env_args,
                *mount_args,
                "-e",
                f"MLONMCU_HOME={mlonmcu_home}",
                "-v",
                f"{mlonmcu_home}:{mlonmcu_home}",
                "-v",
                f"{run_dir}:{run_dir}",
                "--workdir",
                f"{run_dir}",
                image,
            ]
        else:
            assert scripts_dir is not None
            launch_script = scripts_dir / "launch.sh"
            assert launch_script.is_file(), f"Missing file: {launch_script}"
            python_exe = "python3"  # TODO
            command = [launch_script, python_exe, "-m", "mlonmcu.cli.main"]
        return command

    def run_mlonmcu(
        self,
        stage: str,
        dest_dir: Path,
        bench_name: str,
        session_label: str,
        mlonmcu_home: Optional[Path] = None,
        scripts_dir: Optional[Path] = None,
        mgclient_lib_dir: Optional[Path] = None,
        env: Optional[Dict] = None,
        overrides: Optional[Dict] = None,
    ):
        cfg = self.get_mlonmcu_config()
        if overrides:
            cfg.update(overrides)
        env = self.get_mlonmcu_env(mlonmcu_home, env, mgclient_lib_dir=mgclient_lib_dir)
        args = []
        args += self.get_mlonmcu_command(mlonmcu_home, scripts_dir=scripts_dir)
        args += self.get_mlonmcu_args(dest_dir, stage, bench_name, session_label=session_label, **cfg)
        check = True
        print("args", args)
        print("env", env)
        _ = self.run_subprocess(
            args,
            env=env,
            check=check,
            # **kwargs,
        )
        # print("subprocess_result", subprocess_result)
        pass

    def get_session_label(self, bench: str, stage: str, label: str):
        run_dir = self.run_dir
        run_name = run_dir.name.lower().replace("_", "-")
        stage = stage.lower().replace("_", "-")
        bench = bench.lower().replace("/", "-").replace("_", "-")
        label = "-".join(["genie", run_name, bench, stage, label])
        return label

    def get_session_dest(self, stage: str, label: str):
        step_dir = pathlib.Path(self.step_dir)
        dest = step_dir / label
        return dest

    def run_mlonmcu_helper(
        self,
        bench_name: str,
        stage: str,
        label: str,
        mlonmcu_home: Path,
        scripts_dir: Path,
        mgclient_lib_dir: Optional[Path],
        env: Dict,
        overrides: Optional[Dict] = None,
        is_single: bool = True,
    ):
        session_label = self.get_session_label(bench_name, stage, label)
        dest = self.get_session_dest(stage, label)
        self.run_mlonmcu(
            stage,
            dest,
            bench_name,
            session_label=session_label,
            mlonmcu_home=mlonmcu_home,
            env=env,
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            overrides=overrides,
        )
        paths_updates = {}
        metrics_updates = {}
        metrics_updates[f"{label}.label"] = session_label
        keep_cols = [
            "Model",
            "Frontend",
            "Platform",
            "Target",
            "Arch",
            "Total Cycles",
            "Total Cycles (Rel.)",
            "Total Instructions",
            "Total Instructions (rel.)",
            "Total CPI",
            "Run Cycles",
            "Run Cycles (Rel.)",
            "Run Instructions",
            "Run Instructions (rel.)",
            "Run CPI",
            "Total ROM",
            "Total RAM",
            "ROM code",
            "ROM code (rel.)",
        ]
        if is_single:
            paths_updates[f"{label}.output_dir"] = dest / "runs" / "0"
            report_csv = dest / "report.csv"  # use session report for all postprocess cols
            assert report_csv.is_file(), f"Missing file: {report_csv}"
            report_df = pd.read_csv(report_csv)
            assert len(report_df) == 1
            new_metrics = {
                f"{label}.{key}": val for key, val in report_df.iloc[0].to_dict().items() if key in keep_cols
            }
        else:
            paths_updates[f"{label}.output_dir"] = dest
            report_csv = dest / "report.csv"  # use session report for all postprocess cols
            assert report_csv.is_file(), f"Missing file: {report_csv}"
            report_df = pd.read_csv(report_csv)
            assert len(report_df) > 1
            new_metrics = {
                f"{label}.[{i}].{key}": val
                for i, series in report_df.iterrows()
                for key, val in series.to_dict().items()
                if key in keep_cols
            }
        # print("report_df", report_df)
        # print("report_df", report_df)
        # print("new_metrics", new_metrics)
        # input("!")
        log_instrs = overrides.get("log_instrs", False) if overrides is not None else False
        if log_instrs:
            assert is_single
            artifacts_yml = dest / "runs" / "0" / "artifacts.yml"
            assert artifacts_yml.is_file(), f"Missing file: {artifacts_yml}"
            with open(artifacts_yml, "r") as f:
                artifacts = yaml.safe_load(f)
            artifacts = artifacts["artifacts"]
            # print("artifacts", artifacts)
            found = list(filter(lambda x: "log_instrs" in x["flags"], artifacts))
            # print("found", found)
            log_instrs_csv = pathlib.Path(found[0]["path"])
            assert log_instrs_csv.is_file(), f"Missing file: {log_instrs_csv}"
            paths_updates[f"{label}.instr_trace"] = log_instrs_csv
            assert len(found) == 1
            # input("!")

        metrics_updates.update(new_metrics)
        return metrics_updates, paths_updates


@GenIEStep.factory.register()
class Bench(MLonMCUStep):
    """
    TODO.
    """

    id = "MLonMCU.Bench"
    name = "Run Benchmark"
    long_name = "Run MLonMCU Benchmark"
    # inputs = [DesignFormat.LLVM_INSTALL_DIR]
    inputs = []
    outputs = []

    config_vars = MLonMCUStep.config_vars + []

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        bench_name = config["BENCH"]
        mlonmcu_home = pathlib.Path(state_in.paths["mlonmcu.home"])
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        mgclient_lib_dir = pathlib.Path(state_in.paths["mgclient.lib_dir"])
        scripts_dir = demo_dir / "scripts"
        metrics_updates_, paths_updates_ = self.run_mlonmcu_helper(
            bench_name=bench_name,
            stage="run",
            label="bench",
            mlonmcu_home=mlonmcu_home,
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            env=env,
        )
        metrics_updates.update(metrics_updates_)
        paths_updates.update(paths_updates_)
        metrics_updates_, paths_updates_ = self.run_mlonmcu_helper(
            bench_name=bench_name,
            stage="compile",
            label="bench_mem",
            mlonmcu_home=mlonmcu_home,
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            env=env,
        )
        metrics_updates.update(metrics_updates_)
        paths_updates.update(paths_updates_)
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class ISEBench(MLonMCUStep):
    """
    TODO.
    """

    id = "MLonMCU.ISEBench"
    name = "Run ISE Benchmark"
    long_name = "Run MLonMCU ISE Benchmark"
    inputs = []
    outputs = []

    in_stage = "initial"
    per_instr = False
    others = False

    config_vars = MLonMCUStep.config_vars + [
        isaac_core_name_var,
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        bench_name = config["BENCH"]
        mlonmcu_home = pathlib.Path(state_in.paths["mlonmcu.home"])
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        mgclient_lib_dir = pathlib.Path(state_in.paths["mgclient.lib_dir"])
        scripts_dir = demo_dir / "scripts"
        splitted = True
        seal5_name = "seal5_splitted" if splitted else "seal5"

        names_csv = pathlib.Path(state_in.paths[f"{self.in_stage}.workdir"]) / "names.csv"  # TODO: save names path
        assert names_csv.is_file(), f"Missing file: {names_csv}"
        names_df = pd.read_csv(names_csv)
        assert len(names_df) > 0
        instr_names = list(names_df["instr_lower"].values)

        llvm_install_dir = pathlib.Path(state_in.paths[f"{self.in_stage}.{seal5_name}.install_dir"])
        assert llvm_install_dir.is_dir(), f"Missing dir: {llvm_install_dir}"
        etiss_install_dir = pathlib.Path(state_in.paths[f"{self.in_stage}.etiss.install_dir"])
        assert etiss_install_dir.is_dir(), f"Missing dir: {etiss_install_dir}"
        etissvp_script = etiss_install_dir / "bin" / "run_helper.sh"
        assert etissvp_script.is_file(), f"Missing file: {etissvp_script}"
        target = state_in.metrics["bench.Target"]
        arch = state_in.metrics["bench.Arch"]
        etiss_cpu_arch = config["ISAAC_CORE_NAME"]
        build_arch = False  # TODO: enable after filtered?
        if build_arch:
            raise NotImplementedError("BUILD_ARCH")
        else:
            full_arch = f"{arch}_xisaac"
        config_gen = [{f"{target}.arch": arch}, {f"{target}.arch": full_arch}]
        suffix = ""
        if self.others:
            suffix += "_others"
            raise NotImplementedError
        if self.per_instr:
            suffix += "_per_instr"
            assert splitted, "per_instr needs splitted"
            config_gen = [
                {f"{target}.arch": arch},
                *[{f"{target}.arch": f"{arch}_xisaac{instr_name}single"} for instr_name in instr_names],
            ]
            print("instr_names", instr_names)
            print("config_gen", config_gen)
        # TODO: enable num_parallel?
        overrides = {
            "compare_rows": True,
            "compare_rows_to_compare": ["Run Instructions"],
            "llvm_install_dir": llvm_install_dir,
            "etissvp_script": etissvp_script,
            "etiss_cpu_arch": etiss_cpu_arch,
            "config_gen": config_gen,
        }
        metrics_updates_, paths_updates_ = self.run_mlonmcu_helper(
            bench_name=bench_name,
            stage="run",
            label=f"{self.in_stage}.ise_bench{suffix}",
            mlonmcu_home=mlonmcu_home,
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            overrides=overrides,
            env=env,
            is_single=False,
        )
        metrics_updates.update(metrics_updates_)
        paths_updates.update(paths_updates_)
        overrides2 = {
            **overrides,
            "compare_rows_to_compare": ["ROM code"],
        }
        metrics_updates_, paths_updates_ = self.run_mlonmcu_helper(
            bench_name=bench_name,
            stage="compile",
            label=f"{self.in_stage}.ise_bench{suffix}_mem",
            mlonmcu_home=mlonmcu_home,
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            overrides=overrides2,
            env=env,
            is_single=False,
        )
        metrics_updates.update(metrics_updates_)
        paths_updates.update(paths_updates_)
        return views_updates, metrics_updates, paths_updates


@GenIEStep.factory.register()
class Trace(MLonMCUStep):
    """
    TODO.
    """

    id = "MLonMCU.Trace"
    name = "Run Trace"
    long_name = "Run MLonMCU Trace"
    inputs = []
    outputs = []

    config_vars = MLonMCUStep.config_vars + []

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate, PathsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        paths_updates: PathsUpdate = {}
        config = self.config
        bench_name = config["BENCH"]
        mlonmcu_home = pathlib.Path(state_in.paths["mlonmcu.home"])
        demo_dir = pathlib.Path(state_in.paths["demo.dir"])
        mgclient_lib_dir = pathlib.Path(state_in.paths["mgclient.lib_dir"])
        scripts_dir = demo_dir / "scripts"
        metrics_updates_, paths_updates_ = self.run_mlonmcu_helper(
            bench_name=bench_name,
            stage="run",
            label="trace",
            mlonmcu_home=mlonmcu_home,
            scripts_dir=scripts_dir,
            mgclient_lib_dir=mgclient_lib_dir,
            env=env,
            overrides={"log_instrs": True, "llvm_basic_block_sections": True},
        )
        metrics_updates.update(metrics_updates_)
        paths_updates.update(paths_updates_)
        return views_updates, metrics_updates, paths_updates
