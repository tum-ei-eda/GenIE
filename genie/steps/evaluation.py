"""Reanalysis of retargeted application traces."""
from pathlib import Path

from .isaac import ISAACStep
from .step import GenIEStep
from .iss import iss_vars, target_var, iss_target


@GenIEStep.factory.register()
class Reanalyze(ISAACStep):
    id = "ISAAC.Reanalyze"
    name = long_name = "Reanalyze ISE Application"
    inputs = []
    outputs = []
    in_stage = "initial"
    config_vars = ISAACStep.config_vars + iss_vars + [target_var]

    def run(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        stage = self.in_stage
        work = Path(state_in.paths[f"{stage}.workdir"])
        trace = Path(state_in.paths[f"{stage}.ise_trace.output_dir"])
        scripts = Path(state_in.paths["demo.dir"]) / "scripts"
        original = Path(state_in.paths["sess.dir"])
        session = work / "reanalysis"
        names = Path(state_in.paths.get(f"{stage}.names_csv", work / "names.csv"))
        # Check all imported artifacts before creating a session.
        target = state_in.metrics.get("bench.Target", iss_target(self.config))
        spike = target.startswith("spike")
        trace_name = f"{target}_instrs.log" if spike else "etiss_instrs.log"
        files = [trace / "generic_mlonmcu", trace / "mlif/generic/linker.map",
                 trace / trace_name, trace / "generic_mlonmcu.dump",
                 original / "table/ise_instrs.pkl", names]
        for artifact in files:
            if not artifact.is_file():
                raise FileNotFoundError(artifact)
        def toolkit(module, *args, with_session=True):
            self.run_isaac_toolkit(
                [f"isaac_toolkit.{module}", *args], scripts_dir=scripts,
                sess_dir=session if with_session else None,
                has_force=True, env=env,
            )
        toolkit("session.create")
        toolkit("frontend.elf.riscv", files[0])
        toolkit("frontend.linker_map", files[1])
        toolkit("frontend.instr_trace.spike" if spike else "frontend.instr_trace.etiss",
                files[2], *([] if spike else ["--operands"]))
        toolkit("frontend.disass.objdump", files[3])
        instructions = work / "ise_instrs.pkl"
        self.run_subprocess(
            [scripts / "launch.sh", "python3", scripts / "update_ise_instrs_pkl.py",
             files[4], "--out", instructions, "--names-csv", names],
            env=env, check=True, **kwargs,
        )
        if not instructions.is_file():
            raise FileNotFoundError(instructions)
        toolkit("frontend.ise.instrs", instructions)
        for module in ("static.dwarf", "static.llvm_bbs", "static.mem_footprint", "static.linker_map"):
            toolkit(f"analysis.{module}")
        toolkit("analysis.dynamic.trace.trunc_trace", "--start-func", "mlonmcu_run")
        toolkit("analysis.dynamic.trace.trunc_trace", "--end-func", "stop_bench")
        toolkit("analysis.dynamic.trace.instr_operands", "--imm-only")
        for module in ("dynamic.histogram.opcode", "dynamic.histogram.instr",
                       "static.histogram.disass_instr", "static.histogram.disass_opcode",
                       "dynamic.trace.basic_blocks", "dynamic.trace.map_llvm_bbs_new",
                       "dynamic.trace.track_used_functions"):
            toolkit(f"analysis.{module}")
        for plot in ("runtime", "mem_footprint", "disass_counts"):
            toolkit(f"visualize.pie.{plot}", "--legend")
        toolkit("eval.ise.util")
        report = Path(state_in.paths[f"{stage}.ise_bench.output_dir"]) / "report.csv"
        mem_report = Path(state_in.paths[f"{stage}.ise_bench_mem.output_dir"]) / "report.csv"
        for artifact in (report, mem_report):
            if not artifact.is_file():
                raise FileNotFoundError(artifact)
        toolkit("eval.ise.compare_bench", "--report", report, "--mem-report", mem_report)
        toolkit("eval.ise.compare_sess", "--with", original)
        util = work / "util_score.csv"
        self.run_subprocess(
            [scripts / "launch.sh", "python3", scripts / "calc_util_score.py",
             "--dynamic-counts-custom-pkl", session / "table/dynamic_counts_custom.pkl",
             "--static-counts-custom-pkl", session / "table/static_counts_custom.pkl",
             "--out", util], env=env, check=True, **kwargs,
        )
        if not util.is_file():
            raise FileNotFoundError(util)
        return {}, {}, {f"{stage}.reanalysis.dir": session, f"{stage}.util_score_csv": util}
