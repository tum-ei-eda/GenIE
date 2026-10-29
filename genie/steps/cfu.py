"""Use the pinned demo's CFU discovery and runner scripts with GenIE stages."""
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from genie.config import Variable
from .isaac import ISAACStep, isaac_set_name_var
from .iss import iss_vars, encoding_policy_var
from .mlonmcu import MLonMCUStep
from .step import GenIEStep

cfu_vars = [
    *iss_vars, encoding_policy_var,
    next(var for var in MLonMCUStep.config_vars if var.name == "BENCH"),
    *[var for var in MLonMCUStep.config_vars if var.name in ("ARCH", "ABI", "FPU", "TARGET")],
    Variable("CFU_PLAYGROUND_DIR", Optional[str], "Pinned CFU-Playground checkout (7f8ec414).", default=None),
    Variable("CFU_EMBENCH_DIR", Optional[str], "Embench root containing src/ and support/.", default=None),
    Variable("CFU_DISCOVERY_COMPILER", Optional[str], "Baseline discovery clang executable.", default=None),
    Variable("CFU_SIM_TIMEOUT", int, "CFU execution timeout in seconds.", default=600),
    Variable("CFU_RUNNER", str, "CFU runner: verilator, renode, or fpga.", default="verilator"),
    Variable("CFU_INSTRUCTION_TRACE", bool, "Capture Verilator retirement traces.", default=False),
    Variable("CFU_RENODE_EXECUTABLE", Optional[str], "Renode executable.", default=None),
    Variable("CFU_RENODE_VIL", Optional[str], "Pinned Renode Verilator integration sources.", default=None),
    Variable("CFU_VIVADO", Optional[str], "Vivado executable for Arty synthesis.", default=None),
    Variable("CFU_BOARD_SERIAL", Optional[str], "Arty board JTAG serial.", default=None),
    Variable("CFU_SERIAL_PORT", Optional[str], "Arty UART device.", default=None),
    Variable("CFU_SYNTHESIZE_ONLY", bool, "Build FPGA images and resource reports without programming a board.", default=False),
]


class CFUStep(ISAACStep):
    inputs = []
    outputs = []
    in_stage = "initial"
    config_vars = ISAACStep.config_vars + cfu_vars + [isaac_set_name_var]

    def runner_inputs(self, state):
        config = self.config
        if config["ISAAC_ENCODING_POLICY"] != "cfu":
            raise ValueError("CFU steps require ISAAC_ENCODING_POLICY=cfu")
        if config["CFU_SIM_TIMEOUT"] <= 0:
            raise ValueError("CFU_SIM_TIMEOUT must be positive")
        if config["ARCH"] != "rv32im_zicsr_zifencei" or config["ABI"] != "ilp32" or config["FPU"] != "none":
            raise ValueError("The CFU firmware runner requires ARCH=rv32im_zicsr_zifencei, ABI=ilp32 and FPU=none")
        prefix, bench = config["BENCH"].split("/", 1)
        if prefix != "embench_iot" or not bench or Path(bench).name != bench:
            raise ValueError("CFU runners require an embench_iot/<benchmark> workload")
        home = state.paths.get("mlonmcu.home")
        if home is None:
            home = Path(state.paths.get("install.dir", Path(state.paths["demo.dir"]) / "install")) / "mlonmcu"
        home = Path(home)
        embench = Path(config.get("CFU_EMBENCH_DIR") or home / "deps/src/benchmarks/embench")
        if not config.get("CFU_PLAYGROUND_DIR") or not config.get("ISAAC_GNU_INSTALL_DIR"):
            raise ValueError("CFU runners require CFU_PLAYGROUND_DIR and ISAAC_GNU_INSTALL_DIR")
        return ["--root", config["CFU_PLAYGROUND_DIR"], "--gnu", config["ISAAC_GNU_INSTALL_DIR"],
                "--benchmark-dir", embench / "src" / bench, "--support-dir", embench / "support",
                "--timeout", str(config["CFU_SIM_TIMEOUT"])]

    def run_script(self, state, script, args, env, **kwargs):
        scripts = Path(state.paths["demo.dir"]) / "scripts"
        executable = scripts / script
        if not executable.is_file():
            raise FileNotFoundError(executable)
        env = env.copy()
        library = state.paths.get("mgclient.lib_dir")
        if library:
            env["LD_LIBRARY_PATH"] = str(library) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        self.run_subprocess([scripts / "launch.sh", "python3", executable, *args],
                            env=env, check=True, **kwargs)


@GenIEStep.factory.register()
class DiscoveryBench(CFUStep):
    id = "CFU.Bench"
    name = long_name = "Benchmark CFU VexRiscv"
    trace = False

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        label = "trace" if self.trace else "bench"
        output = Path(self.step_dir) / label
        compiler = self.config.get("CFU_DISCOVERY_COMPILER") or Path(state_in.paths["llvm.install_dir"]) / "bin/clang"
        args = self.runner_inputs(state_in) + ["--compiler", compiler, "--output", output]
        if self.trace:
            args += ["--trace"]
        self.run_script(state_in, "cfu_discover.py", args, env, **kwargs)
        report = json.loads((output / "sim/benchmark_metrics.json").read_text())
        if not report.get("validation") or report["cycles"] <= 0 or report["instructions"] <= 0:
            raise ValueError("CFU discovery benchmark did not validate")
        metrics = {f"{label}.label": f"cfu-{label}", f"{label}.Target": "cfu_playground",
                   f"{label}.Arch": "rv32im_zicsr_zifencei", "target.xlen": 32,
                   f"{label}.Run Cycles": report["cycles"], f"{label}.Run Instructions": report["instructions"]}
        paths = {f"{label}.output_dir": output}
        if self.trace:
            for filename in ("cfu_discovery.json", "sim/instruction_trace.csv", "firmware.dump"):
                if not (output / filename).is_file():
                    raise FileNotFoundError(output / filename)
            paths["trace.instr_trace"] = output / "sim/instruction_trace.csv"
        return {}, metrics, paths


@GenIEStep.factory.register()
class DiscoveryTrace(DiscoveryBench):
    id = "CFU.Trace"
    name = long_name = "Trace CFU VexRiscv"
    trace = True


@GenIEStep.factory.register()
class GenerateRTL(CFUStep):
    id = "CFU.GenerateRTL"
    name = long_name = "Generate CFU RTL"

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        if self.config["ISAAC_ENCODING_POLICY"] != "cfu":
            raise ValueError("CFU RTL requires ISAAC_ENCODING_POLICY=cfu")
        stage = self.in_stage
        output = Path(state_in.paths[f"{stage}.workdir"]) / "cfu_rtl"
        self.run_isaac_toolkit(
            ["isaac_toolkit.generate.hardware.cfu", "--index", state_in.paths[f"{stage}.index"],
             "--manifest", state_in.paths[f"{stage}.cfu.manifest"], "--output", output,
             "--set-name", self.config["ISAAC_SET_NAME"]],
            scripts_dir=Path(state_in.paths["demo.dir"]) / "scripts", has_log=False, env=env)
        for filename in ("cfu.sv", "cfu_rtl.json"):
            if not (output / filename).is_file():
                raise FileNotFoundError(output / filename)
        return {}, {}, {f"{stage}.cfu.rtl_dir": output}


def link_input(source, destination):
    source, destination = Path(source).resolve(), Path(destination)
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if destination.resolve() != source:
            raise ValueError(f"CFU evaluation input changed: {destination}")
    else:
        destination.symlink_to(source, target_is_directory=source.is_dir())


@GenIEStep.factory.register()
class Evaluate(CFUStep):
    id = "CFU.Evaluate"
    name = long_name = "Evaluate CFU Hardware"

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        stage, config = self.in_stage, self.config
        if config["ISAAC_SET_NAME"] != "XIsaac":
            raise ValueError("The demo CFU evaluation script requires ISAAC_SET_NAME=XIsaac")
        args = self.runner_inputs(state_in)
        runner = config["CFU_RUNNER"]
        if runner not in ("verilator", "renode", "fpga"):
            raise ValueError("CFU_RUNNER must be verilator, renode, or fpga")
        if config["CFU_INSTRUCTION_TRACE"] and runner != "verilator":
            raise ValueError("CFU retirement tracing requires Verilator")
        if config["CFU_SYNTHESIZE_ONLY"] and runner != "fpga":
            raise ValueError("CFU_SYNTHESIZE_ONLY requires the FPGA runner")
        for key, option in (("CFU_RENODE_EXECUTABLE", "--renode"), ("CFU_RENODE_VIL", "--vil-dir"),
                            ("CFU_VIVADO", "--vivado"), ("CFU_BOARD_SERIAL", "--board-serial"),
                            ("CFU_SERIAL_PORT", "--serial-port")):
            if config.get(key):
                args += [option, config[key]]
        if config["CFU_INSTRUCTION_TRACE"]:
            args += ["--instruction-trace"]
        if config["CFU_SYNTHESIZE_ONLY"]:
            args += ["--synthesize-only"]
        # Give the demo script its conventional layout while keeping each
        # GenIE stage's selected index, compiler and ledger authoritative.
        run = Path(self.step_dir) / "evaluation"
        work = run / "work"
        link_input(state_in.paths[f"{stage}.index"], work / "combined_index.yml")
        link_input(state_in.paths[f"{stage}.cfu.manifest"], work / "cfu_manifest.json")
        link_input(state_in.paths[f"{stage}.seal5.install_dir"], work / "local/seal5/llvm_install")
        args += ["--run-dir", run, "--selection", "combined", "--runner", runner]
        self.run_script(state_in, "cfu_evaluate.py", args, env, **kwargs)
        output = work / ("cfu_evaluation_combined" + ("_" + runner if runner != "verilator" else ""))
        paths = {f"{stage}.cfu.evaluation_dir": output}
        if config["CFU_SYNTHESIZE_ONLY"]:
            report = output / "resource_comparison.json"
            json.loads(report.read_text())
            paths[f"{stage}.cfu.resource_comparison"] = report
            return {}, {}, paths
        report = output / "compare.csv"
        frame = pd.read_csv(report)
        cycles = "model_cycles" if runner == "renode" else "cycles"
        if (len(frame) != 2 or frame["variant"].tolist() != ["baseline", "extended"] or
                not frame["validation"].eq(True).all() or
                not frame[[cycles, "instructions"]].gt(0).all().all()):
            raise ValueError("Invalid CFU comparison report")
        paths[f"{stage}.cfu.compare_csv"] = report
        metrics = {f"{stage}.cfu.{cycles}_relative": float(frame.iloc[1][cycles + "_relative"]),
                   f"{stage}.cfu.instructions_relative": float(frame.iloc[1]["instructions_relative"])}
        return {}, metrics, paths
