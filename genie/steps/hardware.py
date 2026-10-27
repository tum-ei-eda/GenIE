"""Hardware evaluation steps using stage-specific candidate artifacts."""
from pathlib import Path
from typing import Optional

from genie.config import Variable
from .candidates import CandidateStep
from .isaac import isaac_set_name_var
from .step import GenIEStep
from .common_vars import synthesis_enable_vars


@GenIEStep.factory.register()
class RunFakeHLS(CandidateStep):
    """Run the toolkit's explicit fake-HLS model; never substitute it for HLS."""
    id = "ISAAC.RunFakeHLS"
    name = long_name = "Run Fake HLS"
    config_vars = CandidateStep.config_vars + [
        isaac_set_name_var,
        Variable("FAKE_HLS_ENABLE", bool, "Enable explicit fake-HLS evaluation.", default=True),
        Variable("FAKE_HLS_TOOL", str, "Fake-HLS model backend.", default="fake"),
        Variable("FAKE_HLS_CORE", str, "Core used by the fake hardware model.", default="cv32e40p"),
        Variable("FAKE_HLS_STRATEGIES", Optional[str], "Override enumeration strategies.", default=None),
    ]

    def run(self, state_in, **kwargs):
        if not self.config["FAKE_HLS_ENABLE"]:
            return {}, {}, {}
        if self.config["FAKE_HLS_TOOL"] != "fake":
            raise ValueError("Unsupported FAKE_HLS_TOOL")
        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        strategies = self.config["FAKE_HLS_STRATEGIES"] or (
            "all(limit=1)" if self.in_stage in ("initial", "filtered") else "all(limit=100)"
        )
        self.run_isaac_toolkit(
            ["isaac_toolkit.retargeting.fake_hls", "--workdir", work,
             "--set-name", self.config["ISAAC_SET_NAME"], "--core", self.config["FAKE_HLS_CORE"],
             "--index", index, "--strategies", strategies],
            scripts_dir=scripts, sess_dir=Path(state_in.paths["sess.dir"]),
            has_force=True, env=env,
        )
        output = work / "local" / "fake_hls"
        schedules = output / "hls_schedules.csv"
        solutions = output / "output" / "selected_solutions.yaml"
        for artifact in (schedules, solutions):
            if not artifact.is_file():
                raise FileNotFoundError(artifact)
        return {}, {}, {
            f"{self.in_stage}.fake_hls.schedules_csv": schedules,
            f"{self.in_stage}.fake_hls.selected_solutions_yaml": solutions,
            f"{self.in_stage}.fake_hls.output_dir": output,
        }


@GenIEStep.factory.register()
class AssignHLSScore(CandidateStep):
    id = "ISAAC.AssignHLSScore"
    name = long_name = "Assign HLS Score"
    backend = "hls"

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        prefix = f"{self.in_stage}.{self.backend}"
        schedules = Path(state_in.paths[f"{prefix}.schedules_csv"])
        solutions = Path(state_in.paths[f"{prefix}.selected_solutions_yaml"])
        for artifact in (schedules, solutions):
            if not artifact.is_file():
                raise FileNotFoundError(artifact)
        self.run_isaac_toolkit(
            ["isaac_toolkit.utils.annotate_hls_score", index, "--inplace",
             "--hls-schedules-csv", schedules, "--hls-selected-schedules-yaml", solutions],
            scripts_dir=scripts, env=env, has_log=False,
        )
        return {}, {}, {}


@GenIEStep.factory.register()
class AssignFakeHLSScore(AssignHLSScore):
    id = "ISAAC.AssignFakeHLSScore"
    name = long_name = "Assign Fake HLS Score"
    backend = "fake_hls"


class Synthesis(CandidateStep):
    """Evaluate HLS RTL variants and collect the prototype's synthesis reports."""
    kind = "asip"

    @classmethod
    def variables(cls, prefix):
        tool = "SYNOPSYS" if prefix == "ASIP_SYN" else "VIVADO"
        return CandidateStep.config_vars + synthesis_enable_vars + [
            Variable(f"{prefix}_TOOL", str, "Synthesis backend.", default=tool.lower()),
            Variable(f"{prefix}_SEARCH_FMAX", bool, "Request unsupported fmax search.", default=False),
            Variable(f"{prefix}_CORE_NAME", str, "Core to synthesize.", default="CVA5", deprecated_names=[f"{prefix}_{tool}_CORE_NAME"]),
            Variable(f"{prefix}_CLK_PERIOD", float, "Clock period in ns.", default=50.0, deprecated_names=[f"{prefix}_{tool}_CLK_PERIOD", f"{prefix}_{tool}_CLOCK_NS"]),
            Variable(f"{prefix}_BASELINE_USE", Optional[str], "Reuse a baseline synthesis directory.", default=None),
            Variable(f"{prefix}_SKIP_BASELINE", bool, "Skip baseline synthesis.", default=False),
            Variable(f"{prefix}_SKIP_DEFAULT", bool, "Skip default synthesis.", default=False),
            Variable(f"{prefix}_SKIP_SHARED", bool, "Skip shared synthesis.", default=True),
        ]

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        prefix = f"{self.kind.upper()}_SYN"
        config = self.config
        if not config[f"{prefix}_ENABLE"]:
            return {}, {}, {}
        expected_tool = "synopsys" if self.kind == "asip" else "vivado"
        if config[f"{prefix}_TOOL"] != expected_tool:
            raise ValueError(f"Unsupported {prefix}_TOOL: {config[f'{prefix}_TOOL']}")
        if config[f"{prefix}_SEARCH_FMAX"]:
            raise ValueError(f"{prefix}_SEARCH_FMAX is unimplemented; fixed-clock reports are available")
        if state_in.metrics.get(f"{self.in_stage}.hls.model") == "fake":
            raise ValueError("Fake HLS provides no RTL; disable synthesis or run Nailgun")
        index, work, scripts = self.context(state_in)
        period = config[f"{prefix}_CLK_PERIOD"]
        if period <= 0:
            raise ValueError(f"{prefix}_CLK_PERIOD must be positive")
        root = work / f"{self.kind}_syn"
        root.mkdir(parents=True, exist_ok=True)
        collect = []
        paths = {}
        for variant in ("baseline", "default", "shared"):
            if config[f"{prefix}_SKIP_{variant.upper()}"]:
                continue
            reuse = config[f"{prefix}_BASELINE_USE"] if variant == "baseline" else None
            if reuse:
                output = Path(reuse)
                if not output.is_dir():
                    raise FileNotFoundError(output)
            else:
                rtl = Path(state_in.paths[f"{self.in_stage}.hls.{variant}.rtl_dir"])
                if not (rtl / "files.txt").is_file():
                    raise FileNotFoundError(rtl / "files.txt")
                output = root / variant
                output.mkdir(parents=True, exist_ok=True)
                script = scripts / f"{self.kind}_syn_script.sh"
                if self.kind == "asip":
                    script = Path(__file__).with_name("asip_synthesis_adapter.py")
                    env["GENIE_DEMO_DIR"] = str(scripts.parent)
                    if config["ASIP_SYN_TECHLIB_PATH"]:
                        env["TECHLIB_PATH"] = config["ASIP_SYN_TECHLIB_PATH"]
                    if config["ASIP_SYN_TCL"]:
                        env["ASIP_SYN_TCL"] = config["ASIP_SYN_TCL"]
                if not script.is_file():
                    raise FileNotFoundError(script)
                technology = config["ASIP_SYN_PDK"] if self.kind == "asip" else config["FPGA_SYN_PART"]
                command = [script, output, rtl, config[f"{prefix}_CORE_NAME"], technology, str(period)]
                if self.kind == "asip":
                    constraints = state_in.paths.get(f"{self.in_stage}.hls.{variant}.constraints_sdc")
                    if constraints:
                        if not Path(constraints).is_file():
                            raise FileNotFoundError(constraints)
                        command.append(constraints)
                self.run_subprocess(command, env=env, check=True, cwd=scripts.parent, **kwargs)
            collect += [f"--{variant}-dir", output]
            paths[f"{self.in_stage}.{self.kind}_syn.{variant}.output_dir"] = output
        if not collect:
            return {}, {}, {}
        report = root / "metrics.csv"
        collector = scripts / f"collect_{self.kind}_syn_metrics.py"
        if not collector.is_file():
            raise FileNotFoundError(collector)
        launcher = scripts / "launch.sh"
        if not launcher.is_file():
            raise FileNotFoundError(launcher)
        self.run_subprocess(
            [launcher, "python3", collector, *collect, "--out", report],
            env=env, check=True, **kwargs,
        )
        if not report.is_file():
            raise FileNotFoundError(report)
        paths[f"{self.in_stage}.{self.kind}_syn.metrics_csv"] = report
        return {}, {}, paths


@GenIEStep.factory.register()
class RunASIPSynthesis(Synthesis):
    id = "ISAAC.RunASIPSynthesis"
    name = long_name = "Run ASIP Synthesis"
    kind = "asip"
    config_vars = Synthesis.variables("ASIP_SYN") + [
        Variable("ASIP_SYN_TECHLIB_PATH", Optional[str], "Synopsys technology-library directory.", default=None),
        Variable("ASIP_SYN_TCL", Optional[str], "Override synthesis Tcl script.", default=None),
        Variable("ASIP_SYN_PDK", str, "Synopsys technology library.", default="nangate45", deprecated_names=["ASIP_SYN_SYNOPSYS_PDK"]),
    ]


@GenIEStep.factory.register()
class RunFPGASynthesis(Synthesis):
    id = "ISAAC.RunFPGASynthesis"
    name = long_name = "Run FPGA Synthesis"
    kind = "fpga"
    config_vars = Synthesis.variables("FPGA_SYN") + [
        Variable("FPGA_SYN_PART", str, "Vivado FPGA part.", default="xc7a200tffv1156-1", deprecated_names=["FPGA_SYN_VIVADO_PART"]),
    ]


@GenIEStep.factory.register()
class RunHLS(CandidateStep):
    """Generate baseline/default Nailgun RTL using local or container execution."""
    id = "ISAAC.RunHLS"
    name = long_name = "Run HLS"
    config_vars = RunFakeHLS.config_vars + [
        Variable("HLS_ENABLE", bool, "Enable hardware generation/evaluation.", default=True),
        Variable("HLS_TOOL", str, "HLS backend: nailgun or fake.", default="nailgun"),
        Variable("USE_HLS_DOCKER", bool, "Run Nailgun in Docker.", default=False),
        Variable("HLS_IMAGE", str, "Nailgun container image.", default="philippvk/hls-quickstart:latest"),
        Variable("HLS_DIR", Optional[str], "Local isax-tools-integration source tree.", default=None),
        Variable("GUROBI_LIC", Optional[str], "Gurobi license path.", default=None),
        Variable("HLS_BASELINE_USE", Optional[str], "Reuse an existing baseline directory.", default=None),
        Variable("HLS_SKIP_CUSTOM", bool, "Skip custom initiation-interval schedules.", default=False),
        Variable("HLS_SKIP_SHARED", bool, "Skip resource-shared generation.", default=False),
        Variable("HLS_NAILGUN_SHARE_RESOURCES", bool, "Generate a shared hardware variant.", default=False),
        Variable("HLS_DEFAULT_USE", Optional[str], "Reuse default schedules for custom generation.", default=None),
        Variable("HLS_NAILGUN_OL2_ENABLE", bool, "Enable physical synthesis during HLS.", default=False),
        Variable("HLS_NAILGUN_OL2_CONFIG_TEMPLATE", Optional[str], "OpenLane configuration template.", default=None),
        Variable("HLS_NAILGUN_OL2_UNTIL_STEP", str, "Last physical synthesis step.", default="OpenROAD.Floorplan"),
        Variable("HLS_NAILGUN_OL2_TARGET_FREQ", float, "Target clock frequency in MHz.", default=20.0),
        Variable("HLS_NAILGUN_OL2_TARGET_UTIL", float, "Target utilization in percent.", default=20.0),
        Variable("HLS_SKIP_BASELINE", bool, "Skip baseline generation.", default=False),
        Variable("HLS_SKIP_DEFAULT", bool, "Skip default generation.", default=False),
        Variable("HLS_NAILGUN_CORE_NAME", str, "Nailgun core.", default="CVA5"),
        Variable("HLS_NAILGUN_CORE_NAME2", str, "Core output directory name.", default="CVA5"),
        Variable("HLS_NAILGUN_RESOURCE_MODEL", str, "Resource model: none or ol_sky130.", default="ol_sky130"),
        Variable("HLS_NAILGUN_CLOCK_NS", float, "HLS clock period.", default=100.0),
        Variable("HLS_NAILGUN_ILP_SOLVER", str, "Scheduling solver.", default="GUROBI"),
        Variable("HLS_NAILGUN_CELL_LIBRARY", Optional[str], "Cell library YAML file.", default=None),
        Variable("HLS_NAILGUN_SCHEDULE_TIMEOUT", int, "Schedule timeout in seconds.", default=10),
        Variable("HLS_NAILGUN_REFINE_TIMEOUT", int, "Refinement timeout in seconds.", default=10),
    ] + [Variable(f"HLS_NAILGUN_SCHED_ALGO_{algo}", bool, "Enable scheduling algorithm.", default=True)
         for algo in ("MS", "PA", "RA", "MI")]

    def run(self, state_in, **kwargs):
        import shutil

        if not self.config["HLS_ENABLE"]:
            return {}, {}, {}
        tool = self.config["HLS_TOOL"]
        if tool == "fake":
            views, metrics, paths = RunFakeHLS.run(self, state_in, **kwargs)
            prefix = f"{self.in_stage}.fake_hls."
            aliases = {key.replace(prefix, f"{self.in_stage}.hls.", 1): value
                       for key, value in paths.items() if key.startswith(prefix)}
            if paths:
                aliases[f"{self.in_stage}.hls.default.output_dir"] = paths[f"{prefix}output_dir"] / "output"
                metrics[f"{self.in_stage}.hls.model"] = "fake"
            return views, metrics, {**paths, **aliases}
        if tool != "nailgun":
            raise ValueError(f"Unsupported HLS_TOOL: {tool}")
        needs_library = not self.config["HLS_SKIP_DEFAULT"] or not self.config["HLS_SKIP_CUSTOM"] or (
            self.config["HLS_NAILGUN_SHARE_RESOURCES"] and not self.config["HLS_SKIP_SHARED"])
        library = self.config["HLS_NAILGUN_CELL_LIBRARY"]
        if needs_library and (not library or not Path(library).is_file()):
            raise ValueError("Nailgun requires an existing HLS_NAILGUN_CELL_LIBRARY")
        kwargs, env = self.extract_env(kwargs)
        index, work, scripts = self.context(state_in)
        config = self.config
        model = config["HLS_NAILGUN_RESOURCE_MODEL"]
        if model not in ("none", "ol_sky130"):
            raise ValueError(f"Unsupported resource model: {model}")
        gen = Path(state_in.paths[f"{self.in_stage}.gen_dir"]).resolve()
        if not gen.is_dir():
            raise FileNotFoundError(gen)
        root = work.resolve() / ("docker" if config["USE_HLS_DOCKER"] else "local") / "hls"
        sets = config["ISAAC_SET_NAME"].split(";")
        merged_name = sets[0] if len(sets) == 1 else "merged"
        paths = {}
        if config["HLS_NAILGUN_OL2_ENABLE"] and config["HLS_NAILGUN_CORE_NAME"] == "CVA5":
            raise ValueError("Nailgun physical synthesis does not support CVA5")
        for variant in ("baseline", "default", "custom", "shared"):
            if variant == "shared" and not config["HLS_NAILGUN_SHARE_RESOURCES"]:
                continue
            if config[f"HLS_SKIP_{variant.upper()}"]:
                continue
            dest = root / variant
            output = dest / "output"
            reuse = config["HLS_BASELINE_USE"] if variant == "baseline" else None
            if reuse:
                output = Path(reuse).resolve() / "output"
                if not output.is_dir():
                    raise FileNotFoundError(output)
            else:
                output.mkdir(parents=True, exist_ok=True)
                args = ["SKIP_AWESOME_LLVM=y", f"OL2_ENABLE={'y' if config['HLS_NAILGUN_OL2_ENABLE'] else 'n'}", "SIM_EN=n",
                        f"CORE={config['HLS_NAILGUN_CORE_NAME']}"]
                if variant == "baseline":
                    args += ["NO_ISAX=y"]
                else:
                    args += [f"ISAXES={','.join(s.upper() + '.HLS' for s in sets)}",
                             f"LN_ILP_SOLVER={config['HLS_NAILGUN_ILP_SOLVER']}",
                             f"USE_OL2_MODEL={'y' if model == 'ol_sky130' else 'n'}",
                             f"CELL_LIBRARY={config['HLS_NAILGUN_CELL_LIBRARY']}",
                             f"CLOCK_TIME={config['HLS_NAILGUN_CLOCK_NS']}",
                             f"SCHEDULE_TIMEOUT={config['HLS_NAILGUN_SCHEDULE_TIMEOUT']}",
                             f"REFINE_TIMEOUT={config['HLS_NAILGUN_REFINE_TIMEOUT']}"]
                    args += [f"SCHED_ALGO_{a}={'y' if config[f'HLS_NAILGUN_SCHED_ALGO_{a}'] else 'n'}"
                             for a in ("MS", "PA", "RA", "MI")]
                if config["HLS_NAILGUN_OL2_ENABLE"]:
                    template = config["HLS_NAILGUN_OL2_CONFIG_TEMPLATE"]
                    if not template or not Path(template).is_file():
                        raise ValueError("Physical synthesis requires a valid OL2 configuration template")
                    args += [f"OL2_CONFIG_TEMPLATE={template}",
                             f"OL2_UNTIL_STEP={config['HLS_NAILGUN_OL2_UNTIL_STEP']}",
                             f"OL2_TARGET_FREQ={config['HLS_NAILGUN_OL2_TARGET_FREQ']}",
                             f"OL2_TARGET_UTIL={config['HLS_NAILGUN_OL2_TARGET_UTIL']}"]
                if variant == "custom":
                    default = Path(config["HLS_DEFAULT_USE"]) if config["HLS_DEFAULT_USE"] else root / "default"
                    schedules = default / "hls_schedules.csv"
                    if not schedules.is_file():
                        raise FileNotFoundError(schedules)
                    solutions = output / "selected_solutions.yaml"
                    self.run_subprocess(
                        [scripts / "launch.sh", "python3", scripts / "select_hls_schedules.py",
                         schedules, "--output", solutions, "--prefer-ii", "2", "3", "4", "5", "6", "7", "8", "1"],
                        env=env, check=True, **kwargs,
                    )
                    if not solutions.is_file():
                        raise FileNotFoundError(solutions)
                    args += [f"LN_PREDEFINED_SOLUTION_SELECTION={solutions}"]
                if variant == "shared":
                    original_mlir = root / "default" / "output" / "mlir" / f"ISAX_{merged_name.upper()}.HLS_EN.mlir"
                    shared_mlir = root / f"ISAX_{merged_name.upper()}.HLS_EN_shared.mlir"
                    shared_mlir.write_text(original_mlir.read_text().replace(
                        "lil.enc_immediates", "lil.sharing_group = 1, lil.enc_immediates"))
                    args = [arg for arg in args if not arg.startswith("ISAXES=")]
                    args += [f"MLIR_ENTRY_POINT_PATH={shared_mlir}"]
                if config["USE_HLS_DOCKER"]:
                    mounts = {work.resolve(), gen}
                    if library:
                        mounts.add(Path(library).resolve().parent)
                    if config["HLS_NAILGUN_OL2_ENABLE"]:
                        mounts.add(Path(config["HLS_NAILGUN_OL2_CONFIG_TEMPLATE"]).resolve().parent)
                    license_path = config["GUROBI_LIC"]
                    if license_path:
                        mounts.add(Path(license_path).resolve().parent)
                    command = ["docker", "run", "--rm", "-i"]
                    for mount in sorted(mounts):
                        command += ["-v", f"{mount}:{mount}"]
                    if license_path:
                        command += ["-e", f"GUROBI_LIC={license_path}"]
                    command += [config["HLS_IMAGE"], output, gen, *args]
                else:
                    source = config["HLS_DIR"]
                    if not source or not (Path(source) / "nailgun").is_dir():
                        raise ValueError("HLS_DIR must contain a nailgun directory")
                    env["HLS_DIR"] = source
                    if config["GUROBI_LIC"]:
                        env["GUROBI_LIC"] = config["GUROBI_LIC"]
                    command = [scripts.parent / "docker" / "hls_script_local.sh", output, gen, *args]
                self.run_subprocess(command, env=env, check=True, **kwargs)
            rtl = dest / "rtl"
            rtl.mkdir(parents=True, exist_ok=True)
            file_list = output / config["HLS_NAILGUN_CORE_NAME2"] / "files.txt"
            entries = file_list.read_text().split()
            if variant != "baseline":
                extension = output / f"ISAX_{merged_name}.sv"
                shutil.copy2(extension, rtl / extension.name)
                entries.append(extension.name)
            for entry in file_list.read_text().split():
                relative = Path(entry)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"RTL manifest entry must be relative: {entry}")
                destination = rtl / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_list.parent / relative, destination)
            (rtl / "files.txt").write_text("\n".join(entries) + "\n")
            paths[f"{self.in_stage}.hls.{variant}.rtl_dir"] = rtl
            paths[f"{self.in_stage}.hls.{variant}.output_dir"] = output
            if config["HLS_NAILGUN_OL2_ENABLE"]:
                sdcs = list((output / "hw_syn" / "runs").glob("*/final/sdc/*.sdc"))
                if len(sdcs) != 1:
                    raise ValueError(f"Expected one final SDC for {variant}, found {len(sdcs)}")
                constraints = dest / "constraints.sdc"
                constraints.write_text("".join(line for line in sdcs[0].read_text().splitlines(keepends=True)
                                               if "set_driving_cell" not in line))
                paths[f"{self.in_stage}.hls.{variant}.constraints_sdc"] = constraints
            if variant != "baseline":
                schedules = dest / "hls_schedules.csv"
                metrics = dest / "hls_metrics.csv"
                selected_metrics = dest / "hls_selected_schedule_metrics.csv"
                solutions = output / "selected_solutions.yaml"
                commands = [
                    ["collect_hls_metrics.py", output, "--output", metrics],
                    ["parse_kconfig.py", output / "Kconfig", schedules],
                    ["get_selected_schedule_metrics.py", schedules, solutions, selected_metrics],
                ]
                for script, *args in commands:
                    self.run_subprocess([scripts / "launch.sh", "python3", scripts / script, *args],
                                        env=env, check=True, **kwargs)
                for artifact in (schedules, solutions, metrics, selected_metrics):
                    if not artifact.is_file():
                        raise FileNotFoundError(artifact)
                variant_prefix = f"{self.in_stage}.hls.{variant}"
                outputs = {"schedules_csv": schedules, "selected_solutions_yaml": solutions,
                           "metrics_csv": metrics, "selected_metrics_csv": selected_metrics}
                paths.update({f"{variant_prefix}.{key}": value for key, value in outputs.items()})
                if variant == "default":
                    paths.update({f"{self.in_stage}.hls.{key}": value for key, value in outputs.items()})
        return {}, {f"{self.in_stage}.hls.model": "nailgun"}, paths
