# GenIE Steps

## Step Annotations

There can be multiple instances of one step (to allow running it more than one with different options).

In Python the following syntax can be used to define annotated step variants:

```py
annotate(ISAAC.RetargetLLVM, splitted=False),
```

When referencing the step on the command line use the following name: `ISAAC.RetargetLLVM(splitted=False)`

## Registered steps

The following IDs are registered by `genie.steps`. Registration alone does not
prove that external tool execution is available; see [MIGRATION.md](MIGRATION.md)
and [PROGRESS.md](../PROGRESS.md) for validation status.

```text
CI.CreateSummary
CI.PrepareUploads
Docker.StartMemgraphDB
ISAAC.Analyze
ISAAC.AssignComparisonMetrics
ISAAC.AssignEncodingScore
ISAAC.AssignFakeHLSScore
ISAAC.AssignHLSScore
ISAAC.AssignPerInstructionMetrics
ISAAC.AssignReuseMetrics
ISAAC.AssignSeal5Score
ISAAC.AssignSynthesisMetrics
ISAAC.AssignUtilizationScore
ISAAC.CollectImplementationMetrics
ISAAC.CompareISEBench
ISAAC.CreateReanalysisDiff
ISAAC.CreateSession
ISAAC.CreateSpecGraph
ISAAC.FilterCandidates
ISAAC.GenerateETISSCore
ISAAC.GenerateInstrs
ISAAC.LoadArtifacts
ISAAC.LoadConfig
ISAAC.PickChoices
ISAAC.PurgeCDFGDB
ISAAC.PushCDFG
ISAAC.QueryCandidates
ISAAC.Reanalyze
ISAAC.ReportChoices
ISAAC.RetargetISS
ISAAC.RetargetLLVM
ISAAC.RetargetPerfSim
ISAAC.RunASIPSynthesis
ISAAC.RunFPGASynthesis
ISAAC.RunFakeHLS
ISAAC.RunHLS
ISAAC.ScoreCandidates
ISAAC.SelectCandidates
ISAAC.SelectWithSpecializations
ISAAC.SortCandidates
ISAAC.Visualize
MLonMCU.Bench
MLonMCU.ISEBench
MLonMCU.ISEPerfSimBench
MLonMCU.ISEPerfSimTrace
MLonMCU.ISERTLBench
MLonMCU.ISETrace
MLonMCU.PerfSimBench
MLonMCU.PerfSimTrace
MLonMCU.RTLBench
MLonMCU.RTLTrace
MLonMCU.Trace
Misc.CheckDeps
Misc.CheckMemgraph
Misc.CleanupTempFiles
Misc.FixPermissions
Misc.VerifyConfig
Setup.Demo
Setup.SetupCCache
Setup.SetupETISS
Setup.SetupLLVM
Setup.SetupM2ISAR
Setup.SetupMLonMCU
Setup.SetupMemgraph
Setup.SetupMgclient
Setup.SetupPython
```
