from genie.flows import GenIEFlow, SequentialGenIEFlow
from genie.steps import Setup, Misc, MLonMCU, ISAAC, CI, Docker


# def clone_class(cls, name=None):
#     name = name or cls.__name__ + "Clone"
#
#     # Copy only “real” attributes
#     namespace = {k: v for k, v in cls.__dict__.items() if k not in ("__dict__", "__weakref__")}
#
#     return type(name, cls.__bases__, namespace)


def annotate(cls, **kwargs):
    # cls = clone_class(cls)
    if len(kwargs) == 0:
        return cls

    orig_cls = cls

    class AnnotatedStep(cls):
        pass

    cls = AnnotatedStep

    extras = []
    for key, val in kwargs.items():
        assert hasattr(cls, key), f"Missing attr for class {orig_cls.__name__}: {key}"
        setattr(cls, key, val)
        extras.append(f"{key}={val}")

    extra_str = "(" + ",".join(extras) + ")"
    cls.id = cls.id + extra_str
    cls.name = cls.name + " " + extra_str
    cls.long_name = cls.long_name + extra_str
    return cls


@GenIEFlow.factory.register()
class DefaultGenIEFlow(SequentialGenIEFlow):
    Steps = [
        # MyStep,
        Misc.VerifyConfig,
        Misc.CheckDeps,
        Docker.StartMemgraphServer,
        Misc.CheckMemgraph,
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
        ISAAC.LoadConfig,
        ISAAC.LoadArtifacts,
        ISAAC.Analyze,
        ISAAC.Visualize,
        ISAAC.PickChoices,
        # ISAAC.ReportChoices,
        ISAAC.PurgeCDFGDB,
        ISAAC.PushCDFG,
        ISAAC.QueryCandidates,
        ISAAC.GenerateInstrs,
        ISAAC.GenerateETISSCore,
        annotate(ISAAC.RetargetLLVM, splitted=False),
        annotate(ISAAC.RetargetLLVM, splitted=True),
        # ISAAC.RetargetLLVM(splitted=True),
        # Assign Seal5 Metrics/Score
        ISAAC.RetargetISS,
        MLonMCU.ISEBench,
        ISAAC.CompareISEBench,
        # MLonMCU.ISEBenchOthers,
        # ISAAC.CompareISEBenchOthers,
        annotate(MLonMCU.ISEBench, per_instr=True),
        annotate(ISAAC.CompareISEBench, per_instr=True),
        # Assign Compare
        ISAAC.FilterCandidates,
        ISAAC.CreateSpecGraph,
        annotate(ISAAC.GenerateInstrs, in_stage="filtered"),
        annotate(ISAAC.GenerateETISSCore, in_stage="filtered"),
        annotate(ISAAC.RunHLS, in_stage="filtered"),
        annotate(ISAAC.SelectInstrs, in_stage="filtered", out_stage="filtered_selected"),
        # ...
        Misc.FixPermissions,
        CI.CreateSummary,
        CI.PrepareUploads,
        Misc.CleanupTempFiles,
        # MyStep,
    ]
