"""Python phase entry points corresponding to the prototype flow scripts.

Run ``python -m genie.prototype --list`` or select a phase followed by normal
GenIE CLI arguments. Inputs are GenIE configuration and saved state, not the
prototype's experiment.ini/environment-suffix protocol.
"""
import argparse
import json
import sys

from .flows import GenIEFlow, SequentialGenIEFlow
from .flows.default import annotate
from .steps import ISAAC, MLonMCU, Candidates, Hardware, Evaluation, Reports, Misc, CI, Spike, CFU

PROTOTYPE_STEPS = {
    "flow_assign_compare.sh": [Candidates.AssignComparisonMetrics],
    "flow_assign_compare_others.sh": [Candidates.AssignReuseMetrics],
    "flow_assign_compare_per_instr.sh": [Candidates.AssignPerInstructionMetrics],
    "flow_assign_enc.sh": [Candidates.AssignEncodingScore],
    "flow_assign_fake_hls.sh": [Hardware.AssignFakeHLSScore],
    "flow_assign_hls.sh": [Hardware.AssignHLSScore],
    "flow_assign_seal5.sh": [Candidates.AssignSeal5Score],
    "flow_assign_syn.sh": [Candidates.AssignSynthesisMetrics],
    "flow_assign_util.sh": [Candidates.AssignUtilizationScore],
    "flow_bench.sh": [MLonMCU.Bench],
    "flow_bench_perf.sh": [MLonMCU.PerfSimBench],
    "flow_cleanup.sh": [Misc.CleanupTempFiles],
    "flow_cfu.sh": [CFU.Evaluate],
    "flow_cfu_discover.sh": [CFU.DiscoveryBench, CFU.DiscoveryTrace],
    "flow_compare.sh": [MLonMCU.ISEBench, ISAAC.CompareISEBench],
    "flow_compare_others.sh": [annotate(MLonMCU.ISEBench, others=True), annotate(ISAAC.CompareISEBench, others=True)],
    "flow_compare_per_instr.sh": [annotate(MLonMCU.ISEBench, per_instr=True), annotate(ISAAC.CompareISEBench, per_instr=True)],
    "flow_compare_perf.sh": [MLonMCU.ISEPerfSimBench, ISAAC.CompareISEPerfSimBench],
    "flow_etiss.sh": [ISAAC.RetargetISS],
    "flow_etiss_perf.sh": [ISAAC.RetargetPerfSim],
    "flow_fake_hls.sh": [Hardware.RunFakeHLS],
    "flow_filter.sh": [ISAAC.FilterCandidates],
    "flow_hls.sh": [Hardware.RunHLS, Reports.CollectImplementationMetrics],
    "flow_isaac_analyze.sh": [ISAAC.Analyze],
    "flow_isaac_analyze_perf.sh": [ISAAC.Analyze],
    "flow_isaac_cdfg.sh": [ISAAC.PurgeCDFGDB, ISAAC.PushCDFG],
    "flow_isaac_etiss.sh": [ISAAC.GenerateETISSCore],
    "flow_isaac_generate.sh": [ISAAC.GenerateInstrs],
    "flow_isaac_load.sh": [ISAAC.CreateSession, ISAAC.LoadConfig, ISAAC.LoadArtifacts],
    "flow_isaac_load_perf.sh": [ISAAC.CreateSession, ISAAC.LoadConfig, ISAAC.LoadArtifacts],
    "flow_isaac_pick.sh": [ISAAC.PickChoices, ISAAC.ReportChoices],
    "flow_isaac_query.sh": [ISAAC.QueryCandidates],
    "flow_isaac_visualize.sh": [ISAAC.Visualize],
    "flow_reanalyze.sh": [Evaluation.Reanalyze, Reports.CreateReanalysisDiff],
    "flow_report.sh": [CI.CreateSummary],
    "flow_retrace.sh": [MLonMCU.ISETrace],
    "flow_retrace_perf.sh": [MLonMCU.ISEPerfSimTrace],
    "flow_score.sh": [Candidates.ScoreCandidates],
    "flow_seal5.sh": [annotate(ISAAC.RetargetLLVM, splitted=False)],
    "flow_select.sh": [Candidates.SelectWithSpecializations],
    "flow_select_new.sh": [Candidates.SelectCandidates],
    "flow_sort.sh": [Candidates.SortCandidates],
    "flow_spec.sh": [ISAAC.CreateSpecGraph],
    "flow_spike.sh": [Spike.RetargetSpike],
    "flow_syn.sh": [Hardware.RunASIPSynthesis, Hardware.RunFPGASynthesis],
    "flow_trace.sh": [MLonMCU.Trace],
    "flow_trace_perf.sh": [MLonMCU.PerfSimTrace],
}


def phase_steps(name, stage=None, out_stage=None, splitted=None, build_arch=False):
    """Resolve native stage variants corresponding to prototype suffix flags."""
    steps = PROTOTYPE_STEPS[name]
    if name in ("flow_select.sh", "flow_select_new.sh"):
        stage = stage or ("filtered" if name == "flow_select.sh" else "filtered2")
        if name == "flow_select.sh" and stage == "filtered":
            steps = [Candidates.SelectWithSpecializations]
            destination = "filtered_selected"
        else:
            transitions = {"prelim": "final", "filtered2_selected": "final"}
            if name == "flow_select_new.sh":
                transitions["prelim_filtered"] = "final"
            transitions["filtered2"] = "prelim" if name == "flow_select_new.sh" else "filtered2_selected"
            if stage not in transitions:
                raise ValueError(f"Unsupported selection stage for {name}: {stage}")
            steps = [Candidates.SelectCandidates]
            destination = transitions[stage]
        out_stage = out_stage or destination
    if name == "flow_filter.sh" and stage:
        if stage in ("filtered2", "filtered2_selected"):
            return []  # The reference explicitly skips this pass.
        transitions = {"initial": "filtered", "filtered": "filtered2", "filtered_selected": "filtered2"}
        if stage not in transitions:
            raise ValueError(f"Unsupported filtering stage: {stage}")
        out_stage = out_stage or transitions[stage]
    if build_arch:
        supported = {"flow_compare.sh", "flow_compare_perf.sh", "flow_retrace.sh", "flow_retrace_perf.sh"}
        if name not in supported:
            raise ValueError("--build-arch applies only to aggregate comparison and retracing")
    resolved = []
    for step in steps:
        options = {}
        if build_arch and hasattr(step, "build_arch"):
            options["build_arch"] = True
        if stage:
            if not hasattr(step, "in_stage"):
                raise ValueError(f"{name} does not consume a candidate stage")
            options["in_stage"] = stage
        if out_stage:
            if not hasattr(step, "out_stage"):
                raise ValueError(f"{name} does not produce a new candidate stage")
            options["out_stage"] = out_stage
        if splitted is not None:
            if not issubclass(step, ISAAC.RetargetLLVM):
                raise ValueError("--splitted applies only to compiler retargeting")
            step = ISAAC.RetargetLLVM
            options["splitted"] = splitted
        resolved.append(annotate(step, **options))
    return resolved


def main():
    args = sys.argv[1:]
    if args == ["--list"]:
        print(json.dumps({name: [step.id for step in steps] for name, steps in sorted(PROTOTYPE_STEPS.items())}, indent=2))
        return
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("phase", choices=sorted(PROTOTYPE_STEPS))
    stages = ("initial", "filtered", "filtered_selected", "filtered2", "filtered2_selected",
              "prelim", "prelim_filtered", "final")
    parser.add_argument("--stage", choices=stages)
    parser.add_argument("--out-stage", choices=stages)
    parser.add_argument("--splitted", action="store_true", default=None)
    parser.add_argument("--build-arch", action="store_true",
                        help="Compose the architecture from individual instruction extensions")
    options, args = parser.parse_known_args(args)
    try:
        steps = phase_steps(options.phase, options.stage, options.out_stage, options.splitted, options.build_arch)
    except ValueError as exc:
        parser.error(str(exc))
    attributes = {"Steps": steps, "__module__": __name__}
    if options.phase == "flow_hls.sh":
        attributes["config_vars"] = [variable for variable in Hardware.RunHLS.config_vars
                                     if variable.name == "HLS_ENABLE"]
        attributes["gating_config_vars"] = {"ISAAC.RunHLS*": ["HLS_ENABLE"],
                                            "ISAAC.CollectImplementationMetrics*": ["HLS_ENABLE"]}
    flow = type("PrototypePhase", (SequentialGenIEFlow,), attributes)
    GenIEFlow.factory.register()(flow)
    from .__main__ import cli
    cli(args=["--flow", "PrototypePhase", *args], prog_name=f"genie.prototype {options.phase}")


if __name__ == "__main__":
    main()
