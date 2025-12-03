from genie.flows import GenIEFlow, SequentialGenIEFlow
from genie.steps import Setup, Misc, MLonMCU, ISAAC, CI, Docker
from genie.__main__ import cli


@GenIEFlow.factory.register()
class DefaultGenIEFlow(SequentialGenIEFlow):
    Steps = [
        # MyStep,
        Misc.VerifyConfig,
        Misc.CheckDeps,
        Docker.StartMemgraphServer,
        Setup.SetupDemo,
        Setup.SetupPython,
        Setup.SetupCCache,
        Setup.SetupMgclient,
        Setup.SetupLLVM,
        Setup.SetupETISS,
        Setup.SetupMLonMCU,
        # Setup.SetupM2ISAR,
        MLonMCU.Bench,
        MLonMCU.Trace,
        ISAAC.CreateSession,
        ISAAC.LoadArtifacts,
        ISAAC.Analyze,
        ISAAC.Visualize,
        ISAAC.PickChoices,
        ISAAC.PushCDFG,
        ISAAC.QueryCandidates,
        ISAAC.GenerateInstrs,
        # Assign Encoding Metrics/Score
        ISAAC.GenerateETISSCore,
        ISAAC.RetargetLLVM,
        # Assign Seal5 Metrics/Score
        ISAAC.RetargetISS,
        ISAAC.CompareBench,
        ISAAC.CompareBenchOthers,
        ISAAC.CompareBenchPerInstr,
        # Assign Compare
        ISAAC.FilterCandidates,
        ISAAC.CreateSpecGraph,
        # ...
        Misc.FixPermissions,
        CI.CreateSummary,
        CI.PrepareUploads,
        Misc.CleanupTempFiles,
        # MyStep,
    ]
    # ?


# flow = DefaultGenIEFlow({}, design_dir=".")
# flow.start()

if __name__ == "__main__":
    cli()
