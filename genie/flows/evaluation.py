"""Extended ISS evaluation using explicit stage artifacts."""
from .flow import GenIEFlow
from .default import DefaultGenIEFlow, annotate
from genie.steps import ISAAC, MLonMCU, Candidates, Evaluation, Reports


@GenIEFlow.factory.register()
class ISSEvaluationFlow(DefaultGenIEFlow):
    """Evaluate, annotate, and reanalyze candidates before filtering.

    Hardware selection is intentionally a separate flow until its algorithm
    and tool dependencies have been configured explicitly.
    """
    Steps = []
    for step in DefaultGenIEFlow.Steps:
        Steps.append(step)
        if step is ISAAC.GenerateInstrs:
            Steps.append(Candidates.AssignEncodingScore)
        elif step is ISAAC.CompareISEBench:
            Steps.append(Candidates.AssignComparisonMetrics)
        elif step is ISAAC.RetargetISS:
            Steps.append(Candidates.AssignSeal5Score)
        elif step.id == "ISAAC.CompareISEBench(per_instr=True)":
            Steps.extend([
                MLonMCU.ISETrace,
                Evaluation.Reanalyze,
                Reports.CreateReanalysisDiff,
                Candidates.AssignUtilizationScore,
                Candidates.ScoreCandidates,
                Candidates.SortCandidates,
            ])
    del step


from genie.steps import Hardware, CI, Misc, Reports


def evaluate_stage(stage):
    """Produce the toolchains and measurements consumed by later stages."""
    return [
        annotate(ISAAC.GenerateInstrs, in_stage=stage),
        annotate(Candidates.AssignEncodingScore, in_stage=stage),
        annotate(ISAAC.GenerateETISSCore, in_stage=stage),
        annotate(ISAAC.RetargetLLVM, in_stage=stage, splitted=False),
        annotate(ISAAC.RetargetLLVM, in_stage=stage, splitted=True),
        annotate(ISAAC.RetargetISS, in_stage=stage),
        annotate(Candidates.AssignSeal5Score, in_stage=stage),
        annotate(MLonMCU.ISEBench, in_stage=stage),
        annotate(ISAAC.CompareISEBench, in_stage=stage),
        annotate(Candidates.AssignComparisonMetrics, in_stage=stage),
        annotate(MLonMCU.ISEBench, in_stage=stage, per_instr=True),
        annotate(ISAAC.CompareISEBench, in_stage=stage, per_instr=True),
        annotate(MLonMCU.ISETrace, in_stage=stage),
        annotate(Evaluation.Reanalyze, in_stage=stage),
        annotate(Reports.CreateReanalysisDiff, in_stage=stage),
        annotate(Candidates.AssignUtilizationScore, in_stage=stage),
    ]


@GenIEFlow.factory.register()
class HardwareSelectionFlow(ISSEvaluationFlow):
    """ISS discovery through hardware-aware selection and final evaluation."""
    # Reuse discovery and initial evaluation through the first filtering pass.
    Steps = []
    for step in ISSEvaluationFlow.Steps:
        Steps.append(step)
        if step is ISAAC.FilterCandidates:
            break
    del step
    Steps += [
        ISAAC.CreateSpecGraph,
        *evaluate_stage("filtered"),
        annotate(Hardware.RunHLS, in_stage="filtered"),
        annotate(Hardware.AssignHLSScore, in_stage="filtered"),
        annotate(Reports.CollectImplementationMetrics, in_stage="filtered"),
        annotate(Candidates.ScoreCandidates, in_stage="filtered"),
        annotate(Candidates.SortCandidates, in_stage="filtered"),
        Candidates.SelectWithSpecializations,
        annotate(Candidates.SelectCandidates, in_stage="filtered_selected", out_stage="final"),
        *evaluate_stage("final"),
        annotate(Hardware.RunHLS, in_stage="final"),
        annotate(Hardware.AssignHLSScore, in_stage="final"),
        annotate(Reports.CollectImplementationMetrics, in_stage="final"),
        annotate(Candidates.ScoreCandidates, in_stage="final"),
        annotate(Candidates.SortCandidates, in_stage="final"),
        annotate(Hardware.RunASIPSynthesis, in_stage="final"),
        annotate(Hardware.RunFPGASynthesis, in_stage="final"),
        annotate(Candidates.AssignSynthesisMetrics, in_stage="final"),
        Misc.FixPermissions,
        CI.CreateSummary,
        CI.PrepareUploads,
        Misc.CleanupTempFiles,
    ]
