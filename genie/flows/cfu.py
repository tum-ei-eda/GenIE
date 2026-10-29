"""CFU-constrained ISS evaluation and VexRiscv discovery."""
from .flow import GenIEFlow
from .default import DefaultGenIEFlow, annotate
from .evaluation import ISSEvaluationFlow
from genie.steps import ISAAC, CFU, Misc, CI


@GenIEFlow.factory.register()
class CFUGenIEFlow(ISSEvaluationFlow):
    Steps = []
    for step in ISSEvaluationFlow.Steps:
        Steps.append(step)
        if issubclass(step, ISAAC.GenerateETISSCore):
            Steps.append(annotate(CFU.GenerateRTL, in_stage=step.in_stage))
        elif step is ISAAC.CompareISEBench:
            Steps.append(CFU.Evaluate)
    del step


@GenIEFlow.factory.register()
class CFUDiscoveryFlow(DefaultGenIEFlow):
    Steps = []
    for step in DefaultGenIEFlow.Steps:
        if step.id in ("Setup.SetupETISS", "Setup.SetupMLonMCU", "Setup.SetupSeal5"):
            continue
        Steps.append(step)
        if step is ISAAC.GenerateETISSCore:
            break
    del step
    Steps += [CFU.GenerateRTL, Misc.FixPermissions, CI.CreateSummary, CI.PrepareUploads, Misc.CleanupTempFiles]
    Substitutions = {"MLonMCU.Bench": CFU.DiscoveryBench, "MLonMCU.Trace": CFU.DiscoveryTrace}
