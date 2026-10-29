# Prototype migration

The reference is `isaac-demo` revision
`be593a07f7fa017ff9a1bd886daae820322f566c`. Python orchestration uses GenIE steps,
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

## Current demo alignment

Source pins are recorded in `genie/upstream.py`. Setup writes
`upstream_sources.json` with the actual checkout revisions and dirty status.
Local Seal5 uses the [typed-parser main port](SEAL5_PORT.md), with a separate
runtime source path from the demo's historical Seal5 Gitlink.

`SpikeGenIEFlow` and `SpikeEvaluationFlow` use Spike plugin manifests instead
of ETISS installations. `cfg/spike.yml` selects HTIF by default; `SPIKE_RUNTIME=pk`
selects the proxy-kernel target. Set matching `SPIKE_EXE`, `SPIKE_INSTALL_DIR`
and `ISAAC_GNU_INSTALL_DIR` paths for local operation, or enable
`USE_SPIKE_SERVICE` and configure the retargeting API. The pinned upstream
Spike generator supports a restricted instruction behavior subset. GenIE's
bundled M2-ISA-R patch adds conditional writebacks and unsigned local variables
of 1–64 bits, including width truncation on assignment. Signed local variables,
shifts, loops, and other unsupported behavior still fail explicitly; arbitrary
discovered workloads are not assumed to fit this subset. A guarded RV32 add
with an unsigned temporary compiled and executed in native Spike, including
zero-register and overflow checks.

`CFUGenIEFlow` and `CFUDiscoveryFlow` use `cfg/cfu.yml`. CFU allocations persist
across regeneration in a session ledger. Generated RTL and upstream encoding
validation are retained with each stage. CFU evaluation uses the stage's
compiler and allocation manifest, with Verilator, Renode or FPGA execution
selected by `CFU_RUNNER`. Renode model cycles are reported separately from
hardware cycle measurements. These flows require external CFU Playground,
Embench and GNU toolchain installations.

The job API integration uses `/health`, `/workers`, job creation and status,
finite log retrieval, authenticated abort, and artifact downloads. Spike jobs
use the `spike` worker tag and validate the returned plugin manifest and
libraries. Existing workers are not automatically rebuilt or restarted.


### Current validation evidence

The latest fetched demo main is `5b9a533`; the proposed marker-fix integration
commit is `be593a0`. Seal5 and M2-ISA-R now contain the earlier fixes upstream,
so their compatibility patches have been removed. The pending Seal5/LLVM marker
correction is described in the port guide. The validation results below are
from before this source refresh; runtime checks against the forthcoming images
remain pending. See [SEAL5_PORT.md](SEAL5_PORT.md) for rebuilding
service images and for repository branches that need pushing.

| Check | Result | Scope |
| --- | --- | --- |
| Step and actual toolkit integration | 149 passed, no errors, failures or skips | Includes prototype inventory and real typed CFU generation, filtering, allocation persistence and RTL generation. |
| Service API contract | Passed | Actual pinned FastAPI application with mocked Redis: LLVM, ETISS, PerfSim and Spike; tokens, timeout/resume, logs, artifacts and abort. |
| Full Seal5 worker pipeline | Passed | Fused add/XOR: both C++ builds, pattern generation, patch application, all three generated tests, install, source deployment, export and reports. |
| Compiler and native Spike | Exited 0 | Installed compiler selected the custom instruction; linked RV32 executable passed normal and overflow cases with the matching GenIE-retargeted plugin. Separate opcode probes cover zero-register writes. |
| Native CFU evaluation | Both variants passed | GenIE `CFU.Evaluate`, pinned demo runner and Verilator; deterministic 64-vector fixture. Baseline: 1,216 cycles/591 instructions; extended: 1,217 cycles/527 instructions. |
| Native CFU discovery | Passed | CRC32 baseline bench/trace, session loading, analysis, visualization, selection, query, instruction generation and RTL. |
| Documentation and package | Strict HTML and wheel builds passed | Python 3.12/Sphinx 8.2.3 image; wheel contains CFU/Spike flows and all bundled patches. |

CFU static audits found zero custom instruction sites in the baseline firmware
and one allocated site in the extended loop. Firmware execution separately
validated all expected results. The fixture reduced instruction count but did
not reduce cycle count; it is a correctness check rather than evidence of a
workload speedup. Physical FPGA execution, Renode execution and arbitrary Spike
behavior subsets were not covered by these native checks.

#### Evidence locations

- Migration suite: `/tmp/genie-migration-e9e6-tests.xml` (149 tests).
- API verifier: `/tmp/genie-api-current.log`.
- Full compiler worker: `/tmp/genie-llvm-modern-validation/compiler-fused.log`.
- Installed compiler, exports and test reports: `/tmp/genie-llvm-modern-validation/job/output`.
- Compiled Spike probe: `/tmp/genie-llvm-modern-validation/job/probe-compiled.elf`; emitted custom instruction in `probe-fused.s`.
- CFU comparison and encoding audits: `/tmp/genie-cfu-fused-evaluation/run/evaluation/work/cfu_evaluation_combined`.
- Strict documentation: `/tmp/genie-docs-current-ci-output`.

CRC32 discovery used the pinned CFU Playground checkout and passed with
5,574,217 cycles and 4,179,652 instructions in both bench and trace runs.
`ISAAC.CreateSession`, `ISAAC.LoadConfig` and `ISAAC.LoadArtifacts` loaded the
ELF, map, trace, disassembly and compile commands. Analysis, visualization and
selection then completed, and an isolated Memgraph query returned ten
candidates. Generation assigned stable function IDs 0–9, passed the upstream
encoding validator and emitted `cfu.sv`. Artifacts are under
`/tmp/genie-cfu-native-validation`; final generation state is
`runs/RUN_2026-10-28_21-34-25`, with work in the session's `work/initial`.

#### Issues found and fixed during native validation

- Historical `RV32I.core_desc`/`RV64I.core_desc` emitter imports now resolve to the pinned architecture's `RVI.core_desc`.
- CFU subprocesses receive the setup state's `mgclient.lib_dir` through `LD_LIBRARY_PATH`.
- Choice reports recognize CFU's `firmware.dump` discovery artifact.
- Seal5 handles the typed model constructors, split encoding literals, current load CLI arguments, disabled patch resources and obsolete immediate-patch references.
- The service migration adds missing disassembler markers, refreshes the stage-zero revision and immediate inventory, retains generated tests in sparse checkouts and enables the LLVM lit configuration.
- Generated extension-listing tests select a RISC-V target explicitly.
- An initial add-only selection test failed because an equivalent base ADD was chosen. The final fused probe has a distinct multi-operation pattern and passed its generated selection test.

The native checks used isolated inputs, copied caches and temporary containers.
Existing service workers were not rebuilt or restarted. Service image rebuilding
and deployment remain the operator's actions, as requested.
