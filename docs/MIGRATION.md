# Prototype migration

The reference is `isaac-demo` revision
`fb3acb1ddcb3af2903837cb45ddba19b289ed5a7`. Python orchestration uses GenIE steps,
typed configuration, and immutable state updates. Stage output directories replace
the prototype's environment-variable suffix selection. The full checklist and
validation evidence are maintained in [PROGRESS.md](../PROGRESS.md).

`ISSEvaluationFlow` adds scoring, retracing, reanalysis and filtering to discovery.
`HardwareSelectionFlow` also performs HLS, specialization-based selection, final
regeneration and evaluation, and synthesis. Full external execution remains
unverified. See [SETUP.md](SETUP.md) for configuration smoke checks.

## Reports and timing

`flow_report.sh` now renders the available measured tables, discovery summaries,
Sankeys and generated instruction sets from declared state paths, alongside
metrics/artifact availability. Successful steps publish monotonic execution
durations as `timing.<step-id>.seconds`; resumed summaries retain those available
timings without inventing values for older states. `CI_REPORT_CONFIG_KEYS`
selects typed configuration fields explicitly rather than dumping process
environment variables. Local CI bundles include declared HTML/PDF reports as
well as table/text artifacts.

## Annotation scripts without prototype implementations

The prototype's `flow_assign_compare.sh`, `flow_assign_compare_others.sh`, and
`flow_assign_syn.sh` contain no measurement annotation commands. The Python
counterparts add useful behavior with this explicit index schema:

```yaml
global:
  evaluation:
    comparison:
      compare_csv: []  # rows from the aggregate comparison report
    reuse:
      compare_others_csv: []
      compare_others_mem_csv: []
    synthesis:
      asip_syn.metrics_csv: []
      fpga_syn.metrics_csv: []
```

`ISAAC.AssignComparisonMetrics`, `ISAAC.AssignReuseMetrics`, and
`ISAAC.AssignSynthesisMetrics` preserve candidate data and existing global
artifacts. Missing measurements fail the step. Per-instruction comparison metrics
continue to be assigned by `ISAAC.CompareISEBench(per_instr=True)` using the
actual toolkit annotator.

`ISAAC.CreateReanalysisDiff` replaces the prototype's path-dependent diff helper
with a stage-specific text report and a CSV of block-level instruction counts and
runtime changes. The text contains unified assembly diffs. The prototype's optional
`diff-so-fancy` terminal rendering is not required for the plain report.

## Synthesis configuration

The standalone `flow_hls.sh` counterpart honors `HLS_ENABLE=false`, including
skipping implementation-report collection. `HLS_TOOL=nailgun` requires an
existing `HLS_NAILGUN_CELL_LIBRARY` when generating instruction hardware.
`HLS_TOOL=fake` uses the explicit fake model and records `stage.hls.model=fake`
in state; its schedules are modeled costs and contain no RTL. Synthesis rejects
that state unless synthesis is disabled. `FAKE_HLS_ENABLE` and `FAKE_HLS_TOOL`
control the standalone fake-HLS step. These switches do not automatically skip
every downstream consumer in `HardwareSelectionFlow`.

`ASIP_SYN_ENABLE` and `FPGA_SYN_ENABLE` independently control backend execution
and report annotation. Both default to true in the hardware selection flow.
Use the ISS evaluation flow when hardware generation is unnecessary.

| Canonical option | Accepted prototype aliases |
| --- | --- |
| `ASIP_SYN_CORE_NAME` | `ASIP_SYN_SYNOPSYS_CORE_NAME` |
| `ASIP_SYN_CLK_PERIOD` | `ASIP_SYN_SYNOPSYS_CLK_PERIOD`, `ASIP_SYN_SYNOPSYS_CLOCK_NS` |
| `ASIP_SYN_PDK` | `ASIP_SYN_SYNOPSYS_PDK` |
| `FPGA_SYN_CORE_NAME` | `FPGA_SYN_VIVADO_CORE_NAME` |
| `FPGA_SYN_CLK_PERIOD` | `FPGA_SYN_VIVADO_CLK_PERIOD`, `FPGA_SYN_VIVADO_CLOCK_NS` |
| `FPGA_SYN_PART` | `FPGA_SYN_VIVADO_PART` |

Prototype aliases emit configuration deprecation notices. Synthesis currently
uses the Synopsys/Vivado low-level adapters. The prototype's unimplemented fmax
search and unsupported OpenLane ASIP backend are not implemented by these steps.
`ASIP_SYN_TOOL` defaults to `synopsys` and `FPGA_SYN_TOOL` to `vivado`;
unsupported values fail before reading RTL or starting tools. Likewise,
`ASIP_SYN_SEARCH_FMAX=true` and `FPGA_SYN_SEARCH_FMAX=true` fail explicitly,
because fixed-clock synthesis does not provide an fmax search result.

## Selection and score columns

The discovery picking phase now runs `ISAAC.PickChoices` followed by
`ISAAC.ReportChoices`. Unsuitable potential results and empty choices fail
before candidate querying, matching the prototype's gates. The report writes
full and embeddable HTML summaries from the saved choices, block addresses and
trace disassembly, and publishes both paths in state. Address ranges exclude
the block end; text is escaped and the full report needs no external scripts.
`sess.num_choices` is the corrected metric name; the historical misspelling
`sess.num_chocies` remains as an alias for existing consumers.

`flow_select_new.sh --stage prelim_filtered` selects into `final`, alongside
the `prelim → final` and `filtered2 → prelim` transitions. Use `SELECT_TOPK`
for the selected invocation instead of the prototype's per-stage environment
variable names. The input index is preserved and output names are regenerated.

Selected-stage scoring follows the toolkit's existing options: `filtered_selected`
produces `filtered_score`, and `filtered2_selected` produces `prelim_score`.
Sorting uses those actual columns by default. This corrects a prototype mismatch
that silently preserved input order by sorting nonexistent metrics as zero.
`CANDIDATE_SORT_BY` remains available for an explicit column override.

## Retargeting service gap

LLVM and ETISS now support service execution through `cfg/service.yml` and a
native Python adapter. The adapter bypasses the configured toolkit's broken
service client, validates worker artifacts and publishes normal stage paths.
It persists the job handle before observation so retrying identical inputs
resumes the same job. Changed inputs require a fresh stage/workspace.
The adapter has simulated API/archive tests and real single-set LLVM/ETISS
worker/workload validation. The shared LLVM deployment is older; validation used
a dedicated current-image worker. PerfSim service execution additionally packages
the stage candidate index and HLS output directory; enable it separately using
`USE_ETISS_PERF_SERVICE`.

## CDFG stage selection

`CDFG_STAGE` is the LLVM stage mask used by both `ISAAC.PushCDFG` and
`ISAAC.QueryCandidates` (default `32`). Override both through the same GenIE
configuration, for example `-c CDFG_STAGE=64`.

Query overrides from the prototype are exposed as `ISAAC_LIMIT_RESULTS`,
`ISAAC_MIN_ISO_WEIGHT`, `ISAAC_SCALE_ISO_WEIGHT`, `ISAAC_SORT_BY`, `ISAAC_TOPK`
and `ISAAC_PARTITION_WITH_MAXMISO`. `ISAAC_XLEN` accepts the old `XLEN` alias;
when unset it uses the state's target word size, then the toolkit's default.
Unset optional controls preserve toolkit/query-YAML behavior, and explicit zero
values are forwarded. Negative limits/weights and unsupported word sizes fail
before database access. The step publishes names and, when generated by the
toolkit, the combined candidate PDF in stage state.

Select the target-specific query YAML explicitly with
`ISAAC_QUERY_CONFIG_YAML`. The CVA5 reuse-I/O preset is
`cfg/isaac/query/paper/cva5_reuseio.yml`; generic query defaults do not enable its
reuse-I/O and operand restrictions. When using a nondefault database port, keep
its `memgraph.port` consistent with `MEMGRAPH_PORT`.

## Run an individual Python phase

Every active reference `flow_*.sh` has an entry in `genie.prototype`. List their
Python step sequences or run one phase using ordinary GenIE configuration/state:

```sh
python -m genie.prototype --list
python -m genie.prototype flow_report.sh cfg/cva5_reuseio.yml \
  --design-dir /path/to/design --with-initial-state /path/to/state_out.json
```

The script name selects Python steps; it does not execute a shell flow script.
This interface uses GenIE state and configuration rather than `experiment.ini`
and shell suffix flags. Phase defaults follow their corresponding step classes
(e.g. specialization selection consumes the filtered stage). Use `--stage` and
`--out-stage` for candidate-stage variants, and `--splitted` for split compiler
retargeting. For example:

```sh
python -m genie.prototype flow_filter.sh --stage filtered cfg/cva5_reuseio.yml \
  --design-dir /path/to/design -i /path/to/state_out.json
python -m genie.prototype flow_seal5.sh --stage final --splitted cfg/cva5_reuseio.yml \
  --design-dir /path/to/design -i /path/to/state_out.json
```

The selection entry points preserve the distinct prototype transitions:
`flow_select.sh` selects filtered → filtered_selected and filtered2 →
filtered2_selected; `flow_select_new.sh` selects filtered2 → prelim. Both support
prelim → final. Filtering at filtered2/filtered2_selected is an explicit no-op
as in the reference. Unsupported transitions fail before flow execution. The inventory
is checked against all active matching scripts in the reference checkout when
`GENIE_DEMO_SRC` is set during tests. Inventory completeness does not establish
external-tool execution parity.

The ASIP step uses a Python adapter for the repository-root `syn_nangate.tcl`
and `constraints/<core>/<top>.sdc` layout. Set `ASIP_SYN_TECHLIB_PATH` (or provide
`TECHLIB_PATH` in the environment) to the installed technology-library directory;
`ASIP_SYN_TCL` optionally selects another Tcl script. Generated HLS SDC files
supersede the baseline constraints. Tool failures propagate and the adapter
checks the area/timing reports before combining their CSVs. FPGA execution keeps
the prototype's Vivado adapter and runs it from the prototype root so its relative
report-parser paths resolve.

Local compiler retargeting reuses the initial Seal5 build workspace when its
`temporary.initial.seal5_build` path is present in saved state. Set
`SEAL5_BUILD_DIR` to override that workspace explicitly. The final script-boundary
adapter preserves this setting across older toolkit versions. Installed compilers
and reports remain under their own candidate stage directories; build reuse does
not substitute an initial compiler for final retargeting.


PerfSim comparisons read `<stage>.etiss_perf.uarchs_csv` and evaluate a baseline
plus every generated microarchitecture. `ISAAC.CompareISEPerfSimBench` merges
instruction, cycle and memory reports and publishes `<stage>.uarch_ranking_csv`
using the toolkit's CPI ranking. The `flow_compare_perf.sh` Python phase selects
this analyzer automatically. Physical HLS and real PerfSim execution remain
separate validation requirements.


For `flow_compare.sh`, `flow_compare_perf.sh`, `flow_retrace.sh`, and
`flow_retrace_perf.sh`, pass `--build-arch` to compose `_xisaac<name>single`
extensions from the stage's names CSV. At `filtered` and `filtered_selected`,
this mode reuses `initial.seal5_splitted.install_dir` while retaining the requested
stage's simulator. Other stages use their own compiler, matching the prototype.


Filtering thresholds `FILTER_MIN_SEAL5_SCORE`,
`FILTER_MIN_RUNTIME_REDUCTION_REL`, and `FILTER_MIN_UTIL_REL` accept `null` to
disable the corresponding check; zero remains an explicit value. Prototype
names `MIN_SEAL5_SCORE` and `MIN_UTIL_SCORE` are accepted as aliases.

Composed architectures require the split compiler: their individual extensions
are absent from the combined compiler. This also applies to `--build-arch` at
other stages, where `<stage>.seal5_splitted.install_dir` is used.
