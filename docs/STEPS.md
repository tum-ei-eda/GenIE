## GenIE Steps

### Step Annotations

There can be multiple instances of one step (to allow running it more than one with different options).

In Python the following syntax can be used to define annotated step variants:

```py
annotate(ISAAC.RetargetLLVM, splitted=False),
```

When referencing the step on the command line use the following name: `ISAAC.RetargetLLVM(splitted=False)`

### Lists of Steps

```
# CI/CD Steps
CI.PrepareUploads
CreateSummary

# Docker Steps
Docker.StartMemgraphServer

# ISAAC Steps
ISAAC.CreateSession
ISAAC.LoadConfig
ISAAC.LoadArtifacts
ISAAC.Analyze
ISAAC.Visualize
ISAAC.PickChoices
ISAAC.ReportChoices
ISAAC.PurgeCDFGDB
ISAAC.PushCDFG
ISAAC.QueryCandidates
ISAAC.GenerateInstrs
ISAAC.GenerateETISSCore
ISAAC.RetargetLLVM
ISAAC.RetargetISS
ISAAC.CompareISEBench
# ISAAC.CompareISEBenchOthers
ISAAC.FilterCandidates
ISAAC.CreateSpecGraph

# Misc Steps
Misc.VerifyConfig
Misc.CheckDeps
Misc.CheckMemgraph
Misc.FixPermissions
Misc.CleanupTempFiles

# MLonMCU Steps
MLonMCU.Bench
MLonMCU.RTLBench
MLonMCU.PerfSimBench
MLonMCU.ISEBench
MLonMCU.ISERTLBench
MLonMCU.ISEPerfSimBench
MLonMCU.Trace
MLonMCU.RTLTrace
MLonMCU.PerfSimTrace

# Setup Steps
Setup.Demo
Setup.SetupETISS
Setup.SetupLLVM
SetupMLonMCU
Setup.SetupM2ISAR
Setup.SetupPython
Setup.SetupMemgraph
Setup.SetupMgclient
Setup.SetupCCache
```