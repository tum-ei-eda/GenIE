# GenIE migration progress

## Current status

- Python phase entry points cover all **44 active prototype flow scripts**; complete switch/stage parity is still under review.
- **142 tests pass** with the real reference toolkit enabled. Setup and migration instructions are in `docs/SETUP.md` and `docs/MIGRATION.md`.
- Real CRC32 validation covers local and service-built LLVM/ETISS execution, discovery, 110-candidate code generation, combined/split compilers, ETISS, per-instruction and cross-workload evaluation, measured filtering, iterative selection, and final five-instruction compiler/simulator evaluation.
- Final aggregate instruction-count ratio: **0.73927**; physical speed/area is not measured.
- Remaining: real PerfSim service and multi-set LLVM execution, physical HLS/PerfSim/synthesis, complete per-script switch/stage audit, and end-to-end example execution. The chronological evidence below records saved states and active job handles.

## Objective

Set up GenIE from its docs/examples and replace every active `scripts/flow_*.sh` in the original prototype with Python orchestration integrated into the new GenIE flow, configuration, and state model. Existing Python classes do not by themselves prove behavioral parity.

## Reference and design

- Prototype: https://github.com/PhilippvK/isaac-demo
- Inspected revision: `fb3acb1ddcb3af2903837cb45ddba19b289ed5a7` (shallow clone in `/tmp/genie-isaac-demo`).
- GenIE design sources: `docs/FLOWS.md`, `docs/STEPS.md`, `docs/MODES.md`, `docs/CONFIG.md`, `examples/demo_script.py`, and current Python implementations.
- New design uses registered Python steps, sequential flows, typed configuration, and stage-specific state paths; prototype uses shell environment switches and shared run/work directories.
- Scope includes all active matching `.sh` files; `.old` and `.backup` files are historical references.

## Setup

- [x] Read usage, modes, flow, step, configuration, and Docker documentation.
- [x] Clone prototype and enumerate active flow scripts.
- [x] Create isolated environment at `/tmp/genie-venv`.
- [x] Install editable GenIE and test dependencies in `/tmp/genie-venv`; add missing `rapidfuzz` runtime dependency.
- [x] Verify configuration loading and example CLI execution: `examples/demo_script.py --flow ExampleGenIEFlow -c BENCH=embench_iot/crc32 --only Misc.VerifyConfig` exits 0. This is configuration-only execution, not an end-to-end example run.
- [x] Run representative CRC32 baseline benchmark and trace through GenIE using existing tools and isolated `/tmp` MLonMCU home. Discovery, compiler/simulator retargeting, measured filtering and iterative selection now have real execution evidence below. Physical hardware validation remains outstanding.

## Changes made (partial validation)

- Replace empty-command `ISAAC.CreateSpecGraph` placeholder with specialization detection using the stage index/workdir; publish the resulting graph path and fail on missing artifacts.
- Fix ISAAC launcher Python-path composition to preserve `PYTHONPATH` rather than copy `LD_LIBRARY_PATH`.
- Fix `SetupMLonMCU` to honor `MLONMCU_DIR` and `MLONMCU_HOME` (previously read `ETISS_HOME`).
- Use HTTPS for the default prototype clone URL.

## Prototype coverage checklist

Every active script has a registered Python phase (`python -m genie.prototype --list`). Checkboxes below require complete behavioral parity, including supported switches/stages; representative execution evidence is recorded separately. An unchecked box does not mean the implementation is absent.

| Verified | Prototype script | Current counterpart / gap |
| --- | --- | --- |
| [ ] | `flow_assign_compare.sh` | ISAAC.AssignComparisonMetrics; prototype is a TODO, native aggregate-report schema documented |
| [ ] | `flow_assign_compare_others.sh` | ISAAC.AssignReuseMetrics; prototype is a no-op, native aggregate-report schema documented |
| [ ] | `flow_assign_compare_per_instr.sh` | ISAAC.CompareISEBench(per_instr=True) invokes toolkit annotation |
| [ ] | `flow_assign_enc.sh` | ISAAC.AssignEncodingScore; GenerateInstrs publishes its producer path |
| [ ] | `flow_assign_fake_hls.sh` | ISAAC.AssignFakeHLSScore; real 110-candidate modeled annotation passed |
| [ ] | `flow_assign_hls.sh` | ISAAC.AssignHLSScore; RunHLS publishes schedules/solutions; external execution pending |
| [ ] | `flow_assign_seal5.sh` | ISAAC.AssignSeal5Score; real combined/split compiler scores verified |
| [ ] | `flow_assign_syn.sh` | ISAAC.AssignSynthesisMetrics; prototype has no annotation command, native measured-table attachment |
| [ ] | `flow_assign_util.sh` | ISAAC.AssignUtilizationScore; Reanalyze publishes its producer path |
| [ ] | `flow_bench.sh` | MLonMCU.Bench |
| [ ] | `flow_bench_perf.sh` | MLonMCU.PerfSimBench |
| [ ] | `flow_cleanup.sh` | Misc.CleanupTempFiles; guarded temporary state paths and retarget producer registration; legacy broad cleanup intentionally excluded |
| [ ] | `flow_compare.sh` | MLonMCU.ISEBench + ISAAC.CompareISEBench |
| [ ] | `flow_compare_others.sh` | ISEBench(others=True) + CompareISEBench(others=True); CRC32/AHA-Mont64 measured comparison passed |
| [ ] | `flow_compare_per_instr.sh` | annotated ISEBench + CompareISEBench |
| [ ] | `flow_compare_perf.sh` | MLonMCU.ISEPerfSimBench + CompareISEPerfSimBench; multi-uarch planning and real toolkit report/ranking tests pass; actual simulation pending |
| [ ] | `flow_etiss.sh` | ISAAC.RetargetISS |
| [ ] | `flow_etiss_perf.sh` | ISAAC.RetargetPerfSim; HLS prerequisite wired at step level, full execution pending |
| [ ] | `flow_fake_hls.sh` | ISAAC.RunFakeHLS; real 110-candidate model run passed (no physical hardware claim) |
| [ ] | `flow_filter.sh` | ISAAC.FilterCandidates; actual measured filter retained 15/110 candidates |
| [ ] | `flow_hls.sh` | ISAAC.RunHLS + CollectImplementationMetrics; four variants, SDC, diff/LOC implemented; external validation pending |
| [ ] | `flow_isaac_analyze.sh` | ISAAC.Analyze |
| [ ] | `flow_isaac_analyze_perf.sh` | ISAAC.Analyze (PerfSim parity requires verification) |
| [ ] | `flow_isaac_cdfg.sh` | ISAAC.PurgeCDFGDB + PushCDFG |
| [ ] | `flow_isaac_etiss.sh` | ISAAC.GenerateETISSCore |
| [ ] | `flow_isaac_generate.sh` | ISAAC.GenerateInstrs |
| [ ] | `flow_isaac_load.sh` | ISAAC.CreateSession + LoadConfig + LoadArtifacts |
| [ ] | `flow_isaac_load_perf.sh` | LoadArtifacts (PerfSim parity requires verification) |
| [ ] | `flow_isaac_pick.sh` | ISAAC.PickChoices + ReportChoices; suitability/empty gates and real two-choice HTML summaries verified |
| [ ] | `flow_isaac_query.sh` | ISAAC.QueryCandidates |
| [ ] | `flow_isaac_visualize.sh` | ISAAC.Visualize |
| [ ] | `flow_reanalyze.sh` | ISAAC.Reanalyze + CreateReanalysisDiff; real custom trace/session pipeline passed |
| [ ] | `flow_report.sh` | CI.CreateSummary; native experiment/timing/choices/query/Sankey/comparison/CoreDSL sections validated |
| [ ] | `flow_retrace.sh` | MLonMCU.ISETrace; actual custom ETISS trace and reanalysis passed |
| [ ] | `flow_retrace_perf.sh` | MLonMCU.ISEPerfSimTrace; target/model arguments tested, external execution pending |
| [ ] | `flow_score.sh` | ISAAC.ScoreCandidates; actual measured scoring/filtering passed |
| [ ] | `flow_seal5.sh` | ISAAC.RetargetLLVM |
| [ ] | `flow_select.sh` | ISAAC.SelectCandidates + SelectWithSpecializations; actual benchmark-driven selection retained five candidates |
| [ ] | `flow_select_new.sh` | ISAAC.SelectCandidates; native top-k plus real naming CLI integration passed for representative stage |
| [ ] | `flow_sort.sh` | ISAAC.SortCandidates; real toolkit CLI integration passed for representative stage |
| [ ] | `flow_spec.sh` | ISAAC.CreateSpecGraph; actual toolkit graph generation passed |
| [ ] | `flow_syn.sh` | ISAAC.RunASIPSynthesis + RunFPGASynthesis (fixed-clock orchestration; integration pending) |
| [ ] | `flow_trace.sh` | MLonMCU.Trace |
| [ ] | `flow_trace_perf.sh` | MLonMCU.PerfSimTrace |

## Known gaps and risks

- Default flow stops after filtered instruction regeneration; scoring, HLS, selection, synthesis, retracing, and reanalysis are not connected into a complete flow.
- CI summary/uploads, permissions, cleanup and M2-ISA-R setup now have Python implementations; real tool setup remains to be verified.
- RTL and PerfSim flow substitutions do not establish complete simulator retargeting parity.
- Existing steps still use prototype setup/launch helpers; replacing flow scripts must not merely delegate to those same flow scripts.
- Several prototype annotation scripts themselves are TODOs; document their intended behavior and implement useful Python behavior rather than treating a no-op as completion.
- HLS availability is explicitly limited in the repository README; real hardware validation depends on installed tools and any required licenses.

## Next work

1. Finish environment installation and establish CLI/test baseline.
2. Add meaningful tests for repaired stage artifact propagation and setup overrides.
3. Port score annotation, sorting, and selection with stage-aware paths.
4. Port remaining evaluation/retrace, HLS/synthesis, reporting, and cleanup orchestration.
5. Integrate complete flows and verify every coverage row against the prototype.

## Validation log

- Prototype clone and revision inspection succeeded.
- No end-to-end parity claim or completion claim has been made.

### Scoring and setup update

- Added registered `ISAAC.AssignEncodingScore`, `ISAAC.AssignUtilizationScore`, `ISAAC.AssignSeal5Score`, `ISAAC.ScoreCandidates`, and `ISAAC.SortCandidates` steps in `genie/steps/candidates.py`. They consume stage-specific state paths, validate input artifacts, and invoke toolkit modules without executing prototype flow scripts.
- These steps are registered but not yet connected into the default flow; encoding/utilization report producers still need to publish the corresponding state paths.
- Added eight passing command/artifact tests covering stage selection, preliminary score weights, missing producer reports, sorted name publication, and specialization graph output validation. External toolkit execution is mocked in these tests; behavioral parity is still unverified.
- Editable installation succeeded. `/tmp/genie-venv/bin/genie --help` succeeds and lists the four existing flows.
- `/tmp/genie-venv/bin/python -m pytest test -q`: **8 passed, 1 failed**. The pre-existing preprocessor test passes obsolete `pdk`, `pdkpath`, and `scl` keywords to an API that explicitly removed them. Investigate the intended GenIE configuration contract before changing that test or restoring the old OpenLane API.

### Candidate selection and configuration update

- Fixed a real setup defect discovered while resolving the old configuration test: the GenIE preprocessor discarded `design_dir`, so documented `dir::` expressions could not resolve reliably. It now seeds `DESIGN_DIR`. Updated the inherited test to use GenIE's actual API, which has no PDK keyword arguments.
- Added `ISAAC.SelectCandidates`: native Python top-k selection, stage-specific output index, optional ID/name preservation, candidate counts, names artifact, and Sankey report. Source indices remain unchanged. Covers the top-k algorithm behind `flow_select_new.sh` and preliminary/final transitions in `flow_select.sh`; iterative graph-based filtered selection remains outstanding.
- Added `ISAAC.RunFakeHLS`, `ISAAC.AssignHLSScore`, and `ISAAC.AssignFakeHLSScore`. Fake evaluation uses explicit fake-HLS configuration and checks both schedules and selected-solution artifacts. Real HLS execution remains outstanding.
- Tests cover source preservation and metadata propagation for top-k selection, fake-HLS stage strategy defaults/artifact publication, and rejection of incomplete HLS outputs. Toolkit subprocesses remain mocked; actual toolkit compatibility still requires integration verification.
- Configuration and candidate suite passed with 12 tests before hardware tests were added; final combined result recorded below.

- Final validation for this update: `/tmp/genie-venv/bin/python -m pytest test -q` — **15 passed**; `git diff --check` passed. Full external-tool parity remains unverified.

### Hardware orchestration update

- Added registered `ISAAC.RunHLS` for local/Docker Nailgun baseline/default generation, baseline reuse, resource-model and scheduling configuration, RTL manifest copying, HLS metric collection, schedule parsing, and selected-schedule metrics. It publishes stage-specific RTL and score input artifacts.
- Added `ISAAC.RunASIPSynthesis` and `ISAAC.RunFPGASynthesis` for baseline/default/shared jobs, baseline reuse, per-variant skips, ASIP constraints, and combined metrics. They use the existing low-level tool adapters, not `flow_syn.sh`.
- HLS custom-II scheduling, resource-sharing MLIR transformation, optional OpenLane synthesis/SDC extraction, RTL patch statistics, and combined LOC reporting remain unimplemented. No hardware flow is yet claimed equivalent.
- Synthesis fmax search is a TODO in the prototype; the new steps currently expose fixed-clock jobs only. Config names for core/period/library are normalized to the Python step configuration; document legacy aliases before completion.
- Added filesystem/subprocess tests proving nested baseline RTL copying and baseline reuse/metric collection for both synthesis types. Tool adapters are mocked in synthesis tests. No proprietary HLS, Synopsys, or Vivado invocation has been validated.
- `/tmp/genie-venv/bin/python -m pytest test -q`: **18 passed**. `git diff --check` passed.

### Retargeted application evaluation update

- Added `MLonMCU.ISETrace` for retargeted tracing with stage-specific compiler/simulator installations, combined or per-instruction architecture construction, and exported trace state.
- Added `ISAAC.Reanalyze`: session creation, ELF/map/trace/disassembly and ISE instruction import, static/dynamic analysis, visualizations, utilization, benchmark/session comparison, and utilization-score CSV publication. Uses Python orchestration of toolkit modules and existing non-flow Python utilities.
- Corrected a prototype bug: utilization now consumes `static_counts_custom.pkl` for static counts instead of passing dynamic counts twice. Textual diff summaries are still outstanding.
- Fixed `CompareISEBench` to consume the actual `ise_bench*_mem.output_dir` keys and use per-instruction-specific reports. Previously even the aggregate memory-report key was incorrect.
- Enabled configurable cross-workload benchmark lists in `ISEBench(others=True)` and reuse-report analysis in `CompareISEBench(others=True)`. The MLonMCU argument builder accepts benchmark lists. Full command parity and reuse analysis execution remain unverified.
- `ISEBench(build_arch=True)` now constructs per-instruction architecture extensions instead of raising an unimplemented error.
- Added tests for stage-specific tracing and the reanalysis command sequence/utilization artifacts; external modules remain mocked. Suite: **20 passed**.
- PerfSim retargeting/tracing and the simulator-specific frontend analysis variants remain open; existing PerfSim subclasses still lack the required target/feature configuration.

### Flow integration and reporting update

- Added `ISSEvaluationFlow`, extending the default ISS flow with encoding/compiler score annotation, ISE retracing/reanalysis, utilization annotation, scoring, and sorting before filtering. This still stops at filtered regeneration; hardware selection and subsequent final evaluation remain unfinished.
- Repaired the missing encoding-score producer: `GenerateInstrs` now runs `isaac_toolkit.utils.analyze_encoding` before code generation and publishes `stage.encoding_score_csv`, as required by the prototype.
- Replaced CI summary and upload-preparation sleep placeholders with a Markdown summary of state metrics/artifacts and a local report archive plus manifest. No external upload occurs. Artifact member paths preserve separate reports with identical filenames.
- Added `docs/SETUP.md` with installation, tests, and a reproducible configuration smoke command.
- Actual CLI smoke succeeded using `cfg/cva5_reuseio.yml cfg/local.yml --flow ISSEvaluationFlow -c BENCH=embench_iot/crc32 --design-dir /tmp/genie-config-smoke --only Misc.VerifyConfig`; all 47 steps were instantiated, only configuration verification executed. This validates flow/config integration, not the remaining external tool steps.
- Full suite: **21 passed**; report/bundle filesystem round-trip test added.
- Remaining priorities: replace cleanup/permission placeholders; implement PerfSim-specific commands; finish custom/shared HLS, graph-based selection and final-stage flow assembly; validate toolkit CLI compatibility with actual dependencies.

### Cleanup and real toolkit contract validation

- Replaced `Misc.FixPermissions` placeholder with optional owner-access restoration limited to the current run, skipping symbolic links. It no longer sleeps or publishes unrelated lint metrics.
- Replaced `Misc.CleanupTempFiles` placeholder with opt-in removal of state artifacts declared under `temporary.*`. It preflights every target, confines deletion to the run, rejects symlinks, protects declared permanent artifact paths, and clears deleted state entries. Temporary producers still need explicit registration; broad deletion of sessions/workdirs would destroy stage outputs in the new layout. Thus legacy cleanup coverage is still incomplete.
- Cloned configured toolkit branch `isaac-demo-newer-nov` at `b288f41d390316650003653080bdfb3d2cad270a` into `/tmp/genie-toolkit` and inspected actual command parsers and output locations for encoding, scoring, naming, sorting, and fake HLS.
- Added optional real-toolkit integration test (`GENIE_TOOLKIT_SRC` and `GENIE_DEMO_SRC`) that sorts an index, exports names, selects top-k, assigns new names, and reads the generated index/CSV. It executes toolkit CLIs through the prototype launcher using the isolated environment.
- Initial integration run exposed an incomplete fixture (`#Instrs` required by name assignment); fixed the fixture to match real candidate properties. The issue was test data, not a CLI compatibility failure.

- Validation: `GENIE_TOOLKIT_SRC=/tmp/genie-toolkit GENIE_DEMO_SRC=/tmp/genie-isaac-demo /tmp/genie-venv/bin/python -m pytest test -q` — **25 passed**, including the real CLI integration. `git diff --check` passed.

### PerfSim command configuration update

- PerfSim benchmark, trace, and ISE benchmark subclasses now select `PERF_TARGET`, enable the `perf_sim` feature, and pass configurable `PERF_UARCH`; retargeted commands include simulator script/install/executable overrides. ISS commands retain their original target behavior.
- Added `ISAAC.RetargetPerfSim`, using toolkit `iss_perf` and `ETISS_PERF_SCRIPT_LOCAL`; connected it in `PerfSimGenIEFlow`. Added `MLonMCU.ISEPerfSimTrace`.
- Made ISS/PerfSim retargeting stage-aware and bridge noninitial stage index names to the toolkit's required `combined_index.yml`. PerfSim validates the actual HLS dependency and can obtain `HLS_DIR` from stage HLS output state.
- Fixed cross-workload session labels to accept the benchmark lists added earlier (previously string methods would fail).
- Toolkit inspection confirms prototype PerfSim loading and analysis scripts themselves use ordinary load/analyze with explicit TODOs; those paths are shared intentionally, but performance-specific trace validation still needs an actual simulator run.
- Full PerfSim flow remains incomplete: HLS must be scheduled before PerfSim retargeting, baseline simulator setup and complete hardware artifacts must be configured, and real target execution is unverified.

- Validation for PerfSim update: full suite with real toolkit integration **29 passed**; new checks cover model/target/install arguments, ISS separation, cross-workload labels, and flow retargeting substitution. `git diff --check` passed.

### Custom/shared HLS and iterative selection update

- Extended `ISAAC.RunHLS` to run custom initiation-interval selection (`2 3 4 5 6 7 8 1` preference) and shared-resource generation, including MLIR sharing-group transformation. Each variant publishes its own RTL, schedules, metrics, and selected-solution artifacts; default aliases remain stable for score consumers.
- Added optional OpenLane HLS arguments and final SDC extraction with driving-cell removal for downstream synthesis. CVA5 physical synthesis is rejected, matching the prototype limitation. Docker mounts include cell-library/template parent paths.
- Added `ISAAC.SelectWithSpecializations`, invoking the existing Python iterative algorithm with a stage graph, benchmark, configured cost/benefit functions, optional cost bound, and MLonMCU home; publishes selected stage index/names/count/Sankey. This ports orchestration while retaining the prototype's underlying Python algorithm. Actual iterative MLonMCU execution remains unverified.
- Found a prototype CLI mismatch: `flow_select.sh` can pass `--topk` to `selection_algo.py`, which has no such parser option. The new iterative step rejects a nonzero top-k with an explanatory error; top-k remains supported by `ISAAC.SelectCandidates`.
- Added tests for all four HLS variant handoffs, shared MLIR contents, variant-specific output publication, and iterative selection graph/cost arguments. Hardware/iterative subprocesses are mocked.
- Still missing from HLS parity: RTL patch/stat exports and combined LOC reporting. Full final-stage flow assembly and actual tool verification remain outstanding.

- Validation for this update: full suite with real toolkit integration **31 passed**; `git diff --check` passed.

### Resumed: final-stage flow assembly

- Added `HardwareSelectionFlow`, assembling discovery/initial evaluation, filtered retargeting/evaluation, real HLS scoring, specialization-aware selection, final regeneration/retargeting/evaluation, HLS, both synthesis backends, reporting, and cleanup. Uses an explicit stage evaluation sequence with unique step IDs.
- Made LLVM retargeting stage-aware and bridged noninitial index filenames to the toolkit convention. Retargeting now records compiler/simulator install paths in canonical candidate indices for iterative selection.
- Fixed iterative selection execution directory: its existing Python algorithm resolves `scripts/mlonmcu_wrapper.sh` relative to the prototype root.
- Corrected the PerfSim HLS directory handoff to use the HLS variant directory, matching the toolkit annotation convention, rather than its `output` child.
- CLI configuration smoke for `HardwareSelectionFlow` succeeded with local/CVA5 configuration and an explicit library path. This verifies registration/configuration/step construction only, not external execution. Added usage to `docs/SETUP.md`.
- Added stage-producer ordering/unique-ID checks and index-artifact preservation test. Full external workload validation and the remaining flow-specific gaps are still required before completion.

- Validation: full suite including real toolkit CLI integration **33 passed**; `git diff --check` passed.

### Reporting and second-pass filter parity audit

- Fixed `FilterCandidates` for filtered/filtered-selected inputs: it now applies the configured utilization threshold, exports Sankey and names paths, rejects unsupported stage transitions, and publishes correctly spelled `filtered_candidates` counts. Previously the second pass silently applied no threshold.
- Added `ISAAC.CollectImplementationMetrics`: exports unified RTL patches and shortstat-compatible counts for default/custom/shared versus baseline, and combines compiler phase changes, ETISS patch counts, and HLS LOCs into `combined_locs.csv`. Integrated it after filtered/final HLS in `HardwareSelectionFlow`.
- LLVM/ISS retargeting now publishes existing diff/stat artifacts from the adapter output directories for combined LOC collection. Missing optional software change reports are omitted, matching prototype behavior.
- Added tests for inserted/deleted/replaced RTL lines, prototype compiler phase selection and LOC aggregation, and second-pass utilization thresholds/Sankey/name publication.
- Remaining gap audit: reanalysis textual diff report; cleanup temporary producer registration; no-op prototype annotation scripts require explicit coverage decisions; full mode/flow documentation and legacy option mapping; external benchmark/HLS/synthesis validation; per-script evidence review. The goal remains active.

- Validation: full suite including real toolkit candidate CLI integration **36 passed**; `git diff --check` passed.

### Reanalysis diffs and previously empty annotation flows

- Added `ISAAC.CreateReanalysisDiff`, producing stage-specific unified assembly diffs, block instruction counts, runtime weight changes, and a CSV summary. Connected it after reanalysis in ISS/hardware flows.
- Added aggregate comparison/reuse/synthesis annotation steps; the corresponding prototype shell scripts have no annotation implementation. New measured-table attachment semantics are documented in `docs/MIGRATION.md`; no invented per-instruction scores are assigned.
- Added filesystem tests for block matching/assembly changes/runtime summary and aggregate synthesis attachment preserving candidates/global artifacts.
- Refreshed stale coverage descriptions to reflect current implementation without claiming unverified end-to-end parity.
- Validation: full suite including real toolkit CLI integration **38 passed**; `git diff --check` passed.

### Setup and executable example audit

- Replaced broken `examples/demo_script.py` (references to deleted `CompareBench*` classes) with a registered example extending the current ISS flow. Importing the CLI after registration ensures `ExampleGenIEFlow` appears in its choices. Actual `--help` execution succeeded and includes the custom flow.
- Selected `venv.dir` now propagates into launcher environment extraction, including resumed states, without mutating caller-provided environments. Explicit `VENV_DIR` overrides remain supported.
- Replaced shell-string activation in `SetupMLonMCU` with a logged argument-list subprocess and explicit selected-venv PATH; paths with spaces are preserved.
- Implemented `SetupM2ISAR` (editable installation using selected Python and configurable source) and enabled it in the default setup sequence, because the local ETISS adapter invokes its parser/writer. No real M2-ISA-R installation has been executed yet.
- Tests cover environment propagation/override/input isolation, chosen M2-ISA-R source/interpreter, and MLonMCU launch arguments with spaces.

- Validation: full suite including real toolkit candidate integration **42 passed**; example help successfully lists `ExampleGenIEFlow`; `git diff --check` passed.

### Expanded real-toolkit pipeline validation

- Added a real CLI integration chain for encoding/utilization/Seal5 CSV annotations, score computation, first-pass compiler/runtime filtering, and second-pass utilization filtering. Verifies selected candidate identities, output names/Sankey artifacts, and count propagation.
- Validation: **43 passed**, including both real-toolkit integration scenarios (`GENIE_TOOLKIT_SRC=/tmp/genie-toolkit GENIE_DEMO_SRC=/tmp/genie-isaac-demo /tmp/genie-venv/bin/python -m pytest test -q`); `git diff --check` passed.
- Inspected current external availability: Docker, clang, cmake, ninja, ccache, mgconsole, Vivado 2024.1, and Synopsys dc_shell are present; host ETISS is unavailable. Docker has cached GenIE and retargeting-worker images and a running Memgraph container. No existing containers were modified.
- Read-only disposable-container checks show `philippvk/genie:latest` lacks MLonMCU and an installed workload toolchain, so its presence alone does not establish a runnable representative benchmark. The quickstart-min image likewise does not expose a ready full tool tree. Further environment setup/validation remains necessary.
- Added reproducible integration-test invocation and scope to `docs/SETUP.md`.

### Actual step lifecycle and disabled-cache validation

- Added integration through `GenIEConfig.load`, the real `SortCandidates` constructor and `start()`, the real logged subprocess helper, immutable state output, command recording, and process statistics. This closes the gap between prior direct-run harnesses and actual GenIE lifecycle execution.
- Real lifecycle sorting succeeds with `venv.dir` supplied only through state; no mocked subprocess runner is used.
- Fixed disabled-ccache setup: LLVM/ETISS/mgclient setup and compiler/simulator retargeting no longer call `Path(None)` when cache setup publishes a null path. Retargeting derives cache enablement from the available state path and passes an empty cache directory when disabled.
- Added a focused ETISS setup check with ccache disabled. External builds remain mocked in that check.

- Validation: full suite with three real-toolkit integration scenarios **45 passed**; `git diff --check` passed. Full workload/HLS/synthesis verification remains outstanding.

### PerfSim ordering and cleanup producer integration

- Corrected `PerfSimGenIEFlow` ordering: real HLS generation and schedule annotation now precede performance simulator retargeting, matching the toolkit's HLS dependency. Added a regression check for the producer/consumer ordering.
- LLVM and simulator retargeting register existing local disposable build trees under `temporary.*` (`seal5_llvm`, `etiss`, or `etiss_perf`), allowing opt-in cleanup to perform real work. Installation and report paths remain permanent state artifacts. Full prototype deletion of sessions/traces is deliberately not claimed: those remain inputs to later/resumed steps in the new model.
- PerfSim configuration-only smoke uses the local/CVA5 configuration plus explicit cell-library setting; no simulator/HLS execution is implied by that check.
- Requested an optional existing prototype/HLS checkout path to accelerate representative workload validation; independent implementation and validation can continue while awaiting it.

- Validation: PerfSim configuration smoke succeeded; full suite with real toolkit integration **46 passed**; `git diff --check` passed.

### Synthesis enable controls and legacy option compatibility

- Added shared `ASIP_SYN_ENABLE`/`FPGA_SYN_ENABLE` configuration to synthesis execution and annotation. Disabled backends return before reading hardware inputs; annotation only consumes reports from enabled backends.
- Added prototype aliases for tool-prefixed synthesis core, clock period/clock-ns, PDK and FPGA part options. Actual typed configuration loading verifies ASIP aliases resolve to canonical options.
- Documented canonical/legacy mapping and fixed-clock/backend scope in `docs/MIGRATION.md`.
- Tests cover independent backend disablement without hardware artifacts and legacy configuration parsing.

- Validation: full suite with real toolkit/lifecycle integration **49 passed**; `git diff --check` passed.

### Representative baseline workload executed

- Located existing `/var/tmp/ga87puy/isaac-demo-new` source/tool installations. Its MLonMCU Python environment is executable; the older `/var/tmp/ga87puy/isaac-demo` environment has a broken interpreter link.
- Prepared `/tmp/genie-workload-home` with copied environment/cache metadata and isolated writable results/logs/temp/deps locations. Reused existing sources and installations without invoking setup in their directories.
- Actual workload launch found a CLI defect: the inherited OpenLane `initial_state_cb` returned OpenLane State, causing GenIE step construction to treat it as a future. Implemented a GenIE-specific callback preserving stage paths, with invalid-JSON handling tests.
- Executed `ISSEvaluationFlow --only MLonMCU.Bench` for `embench_iot/crc32`: exit 0, saved state at `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-28-31/01-mlonmcu-bench/state_out.json`. Recorded **4,005,963 run instructions**, **4,005,963 run cycles**, **41,896 ROM-code bytes**, architecture `rv32imfd`, ETISS target.
- Executed `--from MLonMCU.Bench --to MLonMCU.Trace`: exit 0, saved state at `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-28-49/02-mlonmcu-trace/state_out.json`. Both `trace.output_dir` and `trace.instr_trace` exist; the latter points to generated `etiss_instrs.log`.
- Baseline/trace logs: `/tmp/genie-workload-bench.log`, `/tmp/genie-workload-trace.log`. Input state: `/tmp/genie-workload-state.json`. This validates baseline compiler/simulator integration, not custom-instruction discovery or hardware evaluation.
- Validation: full suite with real toolkit/lifecycle integration **51 passed**; `git diff --check` passed.

### Real artifact analysis and candidate picking

- Resumed from real CRC32 tracing and executed session creation, artifact loading, analysis, and visualization. Outputs saved under `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-29-40`; the visualization state is `05-isaac-visualize/state_out.json`. Log: `/tmp/genie-workload-analysis.log`.
- Candidate picking initially failed because `LoadConfig` silently skipped configuration when `ISAAC_TOOLKIT_CONFIG_YAML` was unset. Implemented default loading from the selected prototype checkout's `cfg/isaac_toolkit/default.yml`, validate existence, and publish `isaac.config_yaml`. Explicit configuration overrides still take precedence.
- Replayed only config loading/picking against existing analyzed state; completed successfully. State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-30-42/02-isaac-pickchoices/state_out.json`; log `/tmp/genie-workload-pick.log`.
- Real picker selected **2 basic blocks**, with combined relative weight **0.999479271459333**. This verifies progression beyond baseline execution into actual toolkit analysis and picking. Database querying, custom instruction generation/retargeting, and hardware remain to be validated.
- Added regression test for default configuration loading and source-path publication. Validation: **52 passed** with real toolkit integrations; `git diff --check` passed.

### Isolated CDFG database validation

- Started task-specific `genie-validation-memgraph` from the cached Memgraph platform image, bound only to `127.0.0.1:17687`. Existing Memgraph services were not purged or modified. Container remains available for query debugging.
- Corrected `Docker.StartMemgraphDB` port mapping (fixed container port 7687 maps to configured host port) and removed unrelated dashboard/debug port bindings.
- Corrected purge invocation: actual toolkit parser does not accept `--force`, so the step no longer passes it. Purge endpoint still follows session configuration and must be checked against requested host/port before enabling it in validation.
- Ran CDFG export/weight annotation and querying from real picked CRC32 state with `MEMGRAPH_PORT=17687`. Initial sandbox socket denial was retried with approved network access. Export and annotation succeeded; query reached subgraph generation, CDSL/FLAT generation, dataframe exports and pie export.
- Query then failed in an external plotting dependency parser: `ambiguous option: --log could match --logistro-human, --logistro-structured, --logistro-level`. Investigate dependency compatibility/argument handling before continuing; do not claim candidate-query completion.
- Query log: `/tmp/genie-workload-query.log`. Added regression tests for container port mapping and purge argument contract.
- Validation: full suite including real toolkit/lifecycle integration **54 passed**; `git diff --check` passed.

### Query dependency conflict resolved for validation

- Traced plotting failure to `logistro 2.0.1` `_args.py`: import-time `parse_known_args()` with abbreviation enabled treats application `--log` as ambiguous between its own options. Existing environment has Kaleido 1.5.0 and Plotly 7.1.0.
- Created a temporary source overlay at `/tmp/genie-validation-compat/logistro`, changing only parser construction to `allow_abbrev=False`. Existing installation was not edited. Reproducer importing logistro with application `--log info` succeeds with the overlay. This remains an external dependency compatibility fix to package/document for a reproducible final setup.
- Retried actual candidate query with `PYTHONPATH=/tmp/genie-validation-compat` against isolated Memgraph port 17687: **exit 0; 30 candidates**. Chromium/Kaleido plotting completed. Saved state: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-35-01/01-isaac-querycandidates/state_out.json`; log `/tmp/genie-workload-query-retry.log`.
- Actual index: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-29-40/sess/work/initial/combined_index.yml`.
- Purge now verifies persisted session `config.yml` database endpoint equals GenIE's configured host/port before invoking toolkit purge, preventing the known session/environment routing mismatch. Added endpoint-mismatch regression test.
- Validation: **55 passed** including real toolkit/lifecycle integrations; `git diff --check` passed. Instruction generation/retargeting and hardware validation remain outstanding.

### Real instruction generation and ETISS parser failure

- Ran instruction generation plus encoding annotation from real 30-candidate query state. Both completed. Generated per-candidate CoreDSL files and `initial.encoding_score_csv`; aggregate encoding weight **0.48150634765625**. State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-36-22/02-isaac-assignencodingscore/state_out.json`.
- ETISS core generation then failed for CUSTOM2, CUSTOM8, CUSTOM12, and CUSTOM21: named reference `temp0` does not exist. Inspection of generated `CUSTOM12.core_desc` shows `unsigned<32> outp0=temp0;` appears before the declaration/initialization of `temp0`. This is a real generated-code dependency-order issue, not a missing executable or step-state path. No candidates were silently dropped.
- Query used generic defaults allowing two outputs; target-specific query configuration still needs verification against CVA5's intended restrictions. Next action: validate target-specific query preset and/or fix source generator's statement dependency ordering without changing semantics.
- Generation log: `/tmp/genie-workload-generate.log`. Actual CDSL files: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-29-40/sess/work/initial/gen/`.
- Improved default subprocess logging: multiple toolkit commands within one step now receive separate numbered logs/process-stat files instead of overwriting earlier commands. Real lifecycle integration asserts both sorting/naming logs and stats persist.
- Validation after logging change: **55 passed** including real toolkit/lifecycle integrations. Full core generation/retargeting remains incomplete.

### Target-specific CVA5 generation succeeds

- Inspected forward-reference defect in external `tool.gen.cdsl` emitter/tree input. Did not rewrite generated statements or discard candidates. The generic two-output generator defect remains an external issue requiring a semantic ordering fix.
- Validated the actual repository CVA5 reuse-I/O query preset, changing only its database port to 17687 in `/tmp/genie-cva5-reuseio-query.yml`. Preset retains all documented filters, including reuse-I/O enabled, max two outputs, max one ordinary output operand and one inout operand.
- Ran actual query → instruction generation → encoding annotation → ETISS-core generation: **exit 0**, **110 candidates**, aggregate encoding weight **0.748443603515625**. Generated `XIsaac.core_desc`, `XIsaacCore.core_desc`, and corresponding `.m2isarmodel` files.
- State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-39-02/04-isaac-generateetisscore/state_out.json`; log `/tmp/genie-workload-cva5-generate.log`. Shared stage workdir now contains the target-preset outputs; earlier generic-run state paths reference this same location, so use logs for historical diagnostics.
- Added configurable `CDFG_STAGE` (default 32) consistently to export and query, replacing both hardcoded values. Regression test checks requested mask and database routing in export invocation. Documented explicit query preset selection in `docs/MIGRATION.md`.
- Validation: **56 passed** including real toolkit/lifecycle tests; `git diff --check` passed. Compiler/simulator retargeting and hardware execution remain outstanding.

### ETISS retargeting build and real-index schema fix

- Ran actual local ETISS retargeting from the 110-candidate CVA5 core. Initial GitHub DNS denial was retried with approved network access. The adapter cloned ETISS, generated implementation sources, configured/built/installed the simulator. The installed executable exists at `sess/work/initial/local/etiss/etiss_install/bin/bare_etiss_processor` under the analyzed run.
- GenIE then failed in its new artifact-recording helper: the actual queried index uses `global.artifacts: []`, whereas synthetic test indices used a mapping. Fixed normalization of an empty list/null to a mapping and retained rejection of malformed nonempty values. Added regression test. Wrapper completion still needs a retry; build existence alone is not claimed as end-to-end retargeting success.
- Actual log: `/tmp/genie-workload-retarget-etiss.log`; original stage input `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-39-02/04-isaac-generateetisscore/state_out.json`. Build cleanup was disabled to retain diagnostics.
- Fixed local LLVM adapter environment contract: supplies `LLVM_REPO` and `MGCLIENT_ROOT`, adds configurable `SEAL5_LLVM_REPO`/`SEAL5_LLVM_REF`, and supports deriving mgclient install root from its published library path. Compiler build has not yet been attempted; local detached source revision/default adapter ref compatibility needs checking first.

- Validation: **57 passed** including real toolkit/lifecycle integrations; `git diff --check` passed.

### ETISS retargeting wrapper verified; LLVM build started

- Retried actual ETISS retargeting with corrected empty-list artifact handling: **exit 0**. Saved state `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-47-50/01-isaac-retargetiss/state_out.json` publishes `initial.etiss.install_dir` and `temporary.initial.etiss_build`. The installed simulator is under the isolated run's stage workdir. Log: `/tmp/genie-workload-retarget-etiss-retry.log`.
- Confirmed existing LLVM checkout has tag `isaacnew-base-3` (the adapter default), despite detached HEAD and a different `main` branch. Source was not modified.
- Started actual combined LLVM retargeting (`ISAAC.RetargetLLVM(splitted=False)`) from successful ETISS state; live unified exec session **60074** at last poll. Log `/tmp/genie-workload-retarget-llvm.log`. Poll this session before any restart.
- Additional adapter inspection found its Python stage overwrites `LLVM_REPO`/`LLVM_REF` internally. Newly exposed optional override settings therefore still need an adapter bridge before they can be claimed effective; default-tag validation uses the current supported path.
- No new broad completion claim: split compiler retargeting, custom benchmarking/reanalysis, selection and hardware execution remain pending.

- Follow-up poll: LLVM session 60074 is **terminal, exit 2**. Failure occurred before compilation in external Seal5's `tools/llvm.py:124`: `repo.create_tag(name, "-f")` treats `-f` as a ref with the installed GitPython, producing `git tag -- seal5-default-base -f` and “Failed to resolve '-f' as a valid ref.” Next action is dependency/API compatibility correction in an isolated validation overlay, then retry; do not poll or restart the old session as live.

### LLVM dependency/API compatibility retry

- Created isolated `/tmp/genie-validation-seal5` source copy and corrected `Repo.create_tag(name, "-f")` to `Repo.create_tag(name, force=True)`. Existing Seal5 source was not edited. Added its path to `/tmp/genie-workload-llvm-state.json`.
- Retargeting retry passed the tag operation but failed in the legacy adapter's reset/clean path on the partial build directory (`.seal5` not a directory). Launched a retry with `RESET=0`; follow the live handle/log rather than restarting it.
- Added executable Python adapter bridge `genie/steps/seal5_local_adapter.py`: explicit `SEAL5_LLVM_REPO`/`SEAL5_LLVM_REF` are restored at the final script boundary after older toolkit stages overwrite their normal environment names. It forwards arguments directly, preserving paths with spaces. Added regression test.
- Full suite after adapter bridge: **58 passed** including real toolkit/lifecycle scenarios.

- RESET=0 retry reached dependency setup and hit sandbox DNS denial cloning CoreDSL2LLVM. Retried with approved network access. Current live unified exec handle: **10429**; log `/tmp/genie-workload-retarget-llvm-reset0.log`. Poll this handle before any restart. Earlier retry handles are terminal. `git diff --check` passed.

### Executable inventory for every prototype phase

- Added `genie.prototype`: `python -m genie.prototype --list` lists all **44** active `flow_*.sh` reference scripts and their concrete Python step sequences. Selecting a script name builds a native sequential phase and invokes the regular GenIE CLI; no prototype flow shell script is called.
- Added direct `ISAAC.AssignPerInstructionMetrics` so the standalone annotation phase consumes its existing comparison CSV without rerunning the benchmark analysis.
- Added reference-inventory equality check, concrete-step checks, and actual CLI execution of the report phase. Documented the new interface and its GenIE-state/stage semantics in `docs/MIGRATION.md`.
- Full external parity remains unproven: mapping completeness is structural evidence only. Phase classes use their documented stage defaults; annotated custom flows cover other transitions.
- LLVM session **10429 remains live** at last poll. Actual Seal5 log shows LLVM C++ compilation (389/4049 initial build tasks observed), confirming progress beyond dependency and patch setup. Internal log: `sess/work/initial/local/temp/seal5_llvm/.seal5/logs/seal5.log` beneath the analyzed run. Do not restart while this handle remains live.
- Validation: full suite including real toolkit/lifecycle and Python phase CLI **61 passed**; `git diff --check` passed.

### Prototype phase stage transitions

- Extended `genie.prototype` with explicit `--stage`, `--out-stage`, and compiler `--splitted` options, translating the reference suffix-stage branches into annotated Python steps.
- Preserved distinct old/new selection transitions: filtered → filtered_selected (iterative); old filtered2 → filtered2_selected; new filtered2 → prelim; prelim → final. Unsupported selection/filter stages fail before execution; filtered2 filter passes explicitly skip as in the reference.
- Added transition and split-compiler regression tests; existing native report CLI test still executes successfully. Updated `docs/MIGRATION.md` usage.
- Validation: full suite with real toolkit/lifecycle/phase CLI tests **67 passed**; `git diff --check` passed.
- LLVM session **10429 is still live**, verified again after tests; compilation continues in the same run. No restart was performed.

### Completed combined toolchain and real evaluation validation

- Earlier handles expired after completion; authoritative log/state inspection confirms combined LLVM retargeting **exit 0**, completed 11:03:05. Saved state: `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-54-04/01-isaac-retargetllvmsplittedfalse/state_out.json`. All **110 candidates have Seal5 score 1.0**, zero unsupported. Installed compiler and exported reports exist. Session 10429 is terminal and must not be restarted/polled.
- Specialization graph phase and explicit fake-HLS phase both completed on separate `/tmp/genie-fake-validation` data, avoiding annotation of the real hardware path. Graph state: `RUN_2026-10-21_10-00-11/1-isaac-createspecgraphin_stageinitial/state_out.json`; fake-HLS state: `RUN_2026-10-21_10-00-13/1-isaac-runfakehls/state_out.json` under the workload run root.
- Fixed aggregate benchmark compiler selection: combined evaluation now uses `seal5`, while per-instruction evaluation selects `seal5_splitted`. Added regression checks for both.
- Actual combined benchmark, memory benchmark, comparison analysis and aggregate annotation succeeded: `RUN_2026-10-21_14-47-21/03-isaac-assigncomparisonmetrics/state_out.json`. Relative run instructions **0.7827236547117384**, relative ROM code **0.9991407294252436**. Log `/tmp/genie-workload-compare.log`.
- Actual fake-HLS score annotation initially rejected injected `--log`; added optional logging-argument capability and disabled it for the toolkit utility that has no such option. Retry succeeded, annotating 110 candidates; state `RUN_2026-10-21_14-47-54/1-isaac-assignfakehlsscore/state_out.json`.
- Actual custom trace → reanalysis → native disassembly diff → utilization annotation completed: `RUN_2026-10-21_14-48-36/04-isaac-assignutilizationscore/state_out.json`, **110 utilization rows**. Native diff report generated in stage workdir. Log `/tmp/genie-workload-reanalysis.log`.
- Started split-compiler validation. Initial sandbox dependency fetch failed after adapter reset; approved-network retry is **live session 87342**. Log `/tmp/genie-workload-retarget-llvm-split.log`. Poll this handle rather than restart.
- Validation after compiler-selection/log-capability fixes: **69 passed** including real utility/lifecycle/phase tests; `git diff --check` passed. Real HLS/ASIP/FPGA execution, iterative selection, per-instruction evaluation and final coverage audit remain incomplete.

### Native ASIP adapter and synthesis path audit

- Verified split-compiler session **87342** remains live; internal Seal5 log reached LLVM CMake configuration after reset/setup. No job restart performed during this update.
- Found concrete prototype ASIP adapter path defects: it resolves `syn_nangate.tcl` and baseline constraints under `scripts/`, but the checkout stores both at its root. Its technology library path is hardcoded to another machine.
- Added native `asip_synthesis_adapter.py`: explicit root Tcl/constraints resolution, configured technology path, checked Synopsys execution, required report checks, parser execution through the selected launcher, and area/timing CSV combination. Registered it in ASIP synthesis instead of the broken shell adapter.
- Added `ASIP_SYN_TECHLIB_PATH` and `ASIP_SYN_TCL`; baseline reuse still avoids tool execution. Synthesis tool commands now run from the prototype root, fixing Vivado adapter relative report-parser paths.
- Regression test verifies repository-root paths, environment, tool invocation and combined report contents with a stubbed proprietary tool. Real Synopsys/FPGA execution is still unverified; these tests are not hardware results.
- Validation: **70 passed** including real toolkit/lifecycle/phase CLI scenarios; `git diff --check` passed. Documented synthesis settings in `docs/MIGRATION.md`.

### Real report bundle and iterative-selection environment

- Executed real `CI.CreateSummary` and `CI.PrepareUploads` using the completed custom reanalysis state: **exit 0**, bundled **9** declared report artifacts. Saved state `RUN_2026-10-21_14-58-51/02-ci-prepareuploads/state_out.json`; archive `reports.tar.gz` in that step directory under `/tmp/genie-workload-run/runs`. Log `/tmp/genie-workload-report-bundle.log`.
- Fixed iterative selection benchmark-wrapper configuration propagation: target, architecture, ABI, unroll/optimization, global-isel, backend and core name now come from GenIE's typed benchmark variables rather than prototype shell defaults. Extended the selection regression test to assert the environment contract.
- Full suite remains **70 passed**, including real toolkit/lifecycle/phase CLI scenarios; `git diff --check` passed. A fresh full hardware-flow configuration smoke was started after the shared-variable change.
- Split-compiler session **87342** remains verified live; the internal log reached incremental LLVM linking (38/194 observed). No restart performed. Per-instruction validation will use its actual resulting state when available.

- Latest `HardwareSelectionFlow --only Misc.VerifyConfig` smoke succeeded; log `/tmp/genie-hardware-config-smoke-latest.log`.

### Split compiler complete and reproducible dependency preparation

- Split-compiler session 87342 completed **exit 0** at 15:01:11 (7m09s). State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_14-54-02/01-isaac-retargetllvmsplittedtrue/state_out.json`; all **110 candidates score 1.0**, zero unsupported. The split LLVM installation exists alongside the combined installation. Session 87342 is terminal.
- Added `scripts/prepare_legacy_tools.py` to reproduce the validated GitPython tag-call/logging-parser corrections in isolated dependency copies. It reads original sources, checks expected source patterns, refuses existing output trees and emits explicit state/environment override JSON. Existing installations remain untouched. Executed it successfully against the actual older dependencies under `/tmp/genie-compatible-tools-repro`.
- Added source-preservation, override emission, existing-destination and unknown-pattern tests; documented exact usage in `docs/SETUP.md`. Full suite: **72 passed**, including real toolkit/lifecycle/phase tests; `git diff --check` passed.
- Started the real `flow_compare_per_instr.sh` Python phase using split compiler state and four parallel MLonMCU jobs. Log `/tmp/genie-workload-per-instr.log`; live handle recorded below. No smaller candidate subset was selected.

- Per-instruction evaluation live handle: **62565**, confirmed running at last poll. Poll this before any restart.

### Per-instruction and cross-workload phases validated

- Per-instruction evaluation session 62565 completed **exit 0**. Generated **111 comparison rows** (baseline plus all 110 candidates), runtime/code-size measurements and actual per-instruction metric annotations. State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-02-51/2-isaac-compareisebenchper_instrtrue/state_out.json`; log `/tmp/genie-workload-per-instr.log`. Session is terminal.
- Real cross-workload launch exposed a configuration parser bug: JSON list CLI overrides were being split as plain strings, yielding benchmark names with brackets/quotes. Fixed JSON container/quoted-string decoding while preserving legacy bare scalar conversion (including optional string thread counts). Added list/dict/quoted-string/numeric-string regression tests.
- Retried runtime/memory cross-workload comparison on **CRC32 and AHA-Mont64**, using the combined custom toolchain: **exit 0**. State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-05-50/2-isaac-compareisebenchotherstrue/state_out.json`; log `/tmp/genie-workload-reuse-retry.log`. No benchmark names were dropped to pass validation.
- Launched standalone reuse-report annotation from that state (`flow_assign_compare_others.sh` Python phase); log `/tmp/genie-workload-reuse-annotate.log`.
- Validation after CLI override fix: **75 passed** including actual utility/lifecycle/phase CLI scenarios; `git diff --check` passed. Remaining principal validation gaps are iterative selection and real HLS/PerfSim/synthesis, plus final per-script review.

- Standalone reuse-report annotation also completed **exit 0**, attaching measured runtime/memory tables to the index.

### Real measured filtering and iterative selection

- Merged actual reanalysis/utilization and per-instruction measurement state into `/tmp/genie-measured-candidates-state.json`; paths reference existing tool outputs, no candidate measurements were fabricated.
- Real scoring/sorting/filtering/specialization graph generation completed: **15 candidates retained** from 110. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-07-21/04-isaac-createspecgraph/state_out.json`; log `/tmp/genie-workload-filter-measured.log`.
- Exercised iterative selection with supported encoding-footprint costs (`enc_weight_per_instr`, `enc_weight_per_instr_sum`, budget 0.25) and real simulator-derived benefits. This is independent of physical HLS cost validation.
- Real launch exposed prototype-root namespace shadowing of editable MLonMCU and a missing `libmgclient` search path in its nested wrapper. Fixed selection environment to prepend actual MLonMCU source (when present) and propagate `mgclient.lib_dir`. Setup now publishes `mlonmcu.src_dir`. Regression assertions cover both paths.
- Selection retry completed **exit 0**, selecting **5 candidates**: CUSTOM24, CUSTOM30, CUSTOM78, CUSTOM87, CUSTOM88. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-10-54/1-isaac-selectwithspecializationsin_stagefilteredout_stagefiltered_selected/state_out.json`; log `/tmp/genie-workload-selection-retry2.log`. Index, names and Sankey outputs exist. Earlier failed selection/debug handles are terminal.
- Updated usage/flow documentation to current setup, saved-state resumption, phase interface and validation scope.
- Validation: **75 passed** including real toolkit/lifecycle/phase CLI tests; `git diff --check` passed. Physical HLS/PerfSim/synthesis and final-stage evaluation remain unverified.

### Final-stage generation and reusable compiler workspace

- Actual selected → final stage naming, instruction generation, encoding annotation and ETISS-core generation completed **exit 0** for **5 final candidates**. State: `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-12-49/04-isaac-generateetisscorein_stagefinal/state_out.json`; log `/tmp/genie-workload-final-generate.log`. Outputs are distinct from initial-stage generated artifacts.
- Added `SEAL5_BUILD_DIR` and reuse of saved `temporary.initial.seal5_build`, matching the reference's shared compiler-build workspace across stage variants. Extended the final adapter boundary to preserve the selected `SEAL5_HOME` after old toolkit overrides. Per-stage installations/reports remain independent.
- Started actual final combined-compiler retargeting from the five-candidate state. Initial sandbox dependency download denial was retried with approved network access. Current **live session 46194**; log `/tmp/genie-workload-final-llvm.log`. Poll before any restart.
- Validation after workspace propagation change: **75 passed** including real toolkit/lifecycle/phase CLI scenarios; `git diff --check` passed. The adapter test verifies explicit workspace propagation. Final toolchain/evaluation and physical hardware validation remain incomplete.

### Final compiler complete and HLS backend switches

- Final combined-compiler session 46194 completed **exit 0**. Saved state: `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-26-31/01-isaac-retargetllvmin_stagefinalsplittedfalse/state_out.json`. Shared build workspace produced a separate final-stage installation; session is terminal.
- Added explicit `HLS_ENABLE`, `HLS_TOOL`, `FAKE_HLS_ENABLE` and `FAKE_HLS_TOOL` handling. Nailgun validates its cell library only when needed. Fake dispatch records modeled-cost provenance in state and provides schedule aliases; synthesis rejects fake results because they provide no RTL.
- Disabled standalone `flow_hls.sh` now gates both generation and implementation-report collection. Regression coverage executes the actual CLI without input artifacts. Full hardware-flow downstream skipping is not claimed.
- Validation: **79 passed**, including real toolkit/lifecycle/phase CLI scenarios; `git diff --check` passed.
- Started actual final ETISS retargeting through aggregate benchmark comparison/annotation using the completed final compiler state. Log `/tmp/genie-workload-final-evaluation.log`; live session **1173**. Poll before restarting. Physical HLS/PerfSim/synthesis and final split/per-instruction evaluation remain outstanding.

- Session 1173 failed because the sandbox blocked ETISS source download. Network-enabled retry **24286 completed exit 0**: final simulator build, compiler score annotation, CRC32 runtime/memory comparison and aggregate report attachment. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-38-27/05-isaac-assigncomparisonmetricsin_stagefinal/state_out.json`; log `/tmp/genie-workload-final-evaluation-retry.log`. Both sessions are terminal.
- Five final instructions all have compiler score 1.0. Actual final CRC32 run uses **2,961,483 instructions**, compared with baseline **4,005,963** (ratio **0.7392686852**); ROM code **41,876 vs 41,896 bytes**. These are ETISS instruction-count results, not a physical timing claim.
- Started final tracing/reanalysis/diff/utilization annotation: session **60043**, log `/tmp/genie-workload-final-reanalysis.log`. Poll before restarting.
- Required `philippvk/hls-quickstart:latest` image is not cached. Existing GenIE/quickstart-min images did not expose a ready HLS source tree in their standard tool directories. Physical HLS remains unvalidated.

- Executed the registered example flow through `Misc.VerifyConfig`: **exit 0**, log `/tmp/genie-example-smoke.log`. Refreshed `docs/STEPS.md` from the actual registered IDs, correcting old names and adding the implemented phases.

- Final trace/reanalysis session 60043 completed **exit 0** at 15:41:08. Actual custom trace import, static/dynamic analysis, diff reports and utilization annotation passed for the five final instructions. Saved state `/tmp/genie-workload-run/runs/RUN_2026-10-21_15-39-41/04-isaac-assignutilizationscorein_stagefinal/state_out.json`; session is terminal.
- Latest verification after resetting stale fake-model provenance on successful Nailgun output: **79 tests passed** and `git diff --check` passed. No validation jobs remain running from this update.

### Stage parity audit: selected scores and preliminary selection

- Previous goal turn classified as **progress**: authoritative compiler/simulator execution, final benchmark/reanalysis evidence, HLS switch fixes, and maintained progress documentation. No prior validation jobs remain live.
- Compared actual `flow_select_new.sh`, `flow_score.sh`, `flow_sort.sh`, load/analyze PerfSim scripts and retargeting scripts with the Python phases.
- Added missing **prelim_filtered → final** selection to the phase CLI. Real CLI integration loads saved GenIE state, keeps two of three candidates, regenerates names, writes Sankey output and proves source preservation.
- Fixed selected-stage default sorting: toolkit scoring produces `filtered_score` for filtered_selected and `prelim_score` for filtered2_selected. Previously both prototype and Python sorting requested absent columns, silently preserving order because the toolkit defaults missing metrics to zero. Two real toolkit score→sort tests now prove descending benefit order on both stages. Explicit `CANDIDATE_SORT_BY` still overrides defaults.
- Newly confirmed gap: prototype retargeting has service branches, but Python LLVM/ISS retargeters currently expose only local/Docker. No `cfg/service.yml` exists. Toolkit ISS accepts `--service`, while configured LLVM stage does not; simply forwarding a common switch cannot close the gap. Updated `docs/MODES.md`, `docs/SERVICE.md` and `docs/MIGRATION.md` to remove the unsupported setup claim. Service adapters remain required work.
- PerfSim load/analyze shell scripts currently invoke the same toolkit load/analyze modules as their ISS equivalents and label extra PerfSim analysis as TODO. Python mapping matches those actual commands; this inspection does not establish physical PerfSim execution.
- Verification: **83 passed** with `GENIE_TOOLKIT_SRC=/tmp/genie-toolkit GENIE_DEMO_SRC=/tmp/genie-isaac-demo`; `git diff --check` passed. No long-running jobs started this turn.

### Service transport implementation

- Previous goal turn classified as **progress**: fixed selected-stage sorting and preliminary selection, added real toolkit regression coverage, and identified service-mode interface gaps.
- Inspected the configured toolkit service client and the available `/var/tmp/ga87puy/isaac-docker-service/api/api.py`. The old toolkit client cannot be used directly: it instantiates abstract `RetargetClient` instead of the selected concrete client, passes `force` to a function that does not accept it, and passes mismatched configuration arguments. Nonverbose execution also skips waiting. No external source was modified.
- Current available API requires multipart `cdsl`, `cpdsl`, `config`, plus `index`/`hls` for `etiss_perf`; job observation/download uses the returned token. These requirements differ from the old toolkit client's submission payload.
- Added `genie/retargeting_service.py`: separate submission, status polling, resumable job handles and streamed artifact download. Timeout never resubmits; failed jobs raise before artifact download; unsuccessful transfer preserves an existing destination. Job object repr omits its token.
- Added five HTTP transport tests covering full request/response lifecycle, timeout/resume without POST, terminal failure, failed download preserving destination, and early PerfSim input validation. These use `httpx.MockTransport`, not a real service worker.
- Validation: **88 passed** with actual reference toolkit tests enabled; `git diff --check` passed. No long-running jobs started. The transport is **not yet integrated** into GenIE retargeters; typed configuration, artifact extraction/layout verification, stage-state publication and real worker validation remain required.

### LLVM/ETISS service integration

- Previous goal turn classified as **progress**: implemented tested service submission/observation/download transport from the actual available API contract.
- Wired `USE_SEAL5_SERVICE` and `USE_ETISS_SERVICE` into the Python retargeters, with `SERVICE_URL`, timeout/poll interval, worker tags and explicit `SEAL5_SERVICE_CONFIG`. Added `cfg/service.yml`. Service switches take precedence over the Docker switches.
- Added a stage bridge that saves a private job handle **before waiting**, fingerprints URL/tag/description/config, and resumes identical requests. Changed inputs fail instead of reusing unrelated results. Combined and split compiler outputs remain separate. Service requests are not resubmitted on retry.
- Added real `.tar.zst` extraction using `zstd` and Python's data extraction filter into an isolated temporary directory. The worker's `output/` layout is required; path escapes are rejected before destination publication. Extraction prerequisites are checked before submitting remote work.
- LLVM/ETISS integration validates compiler/simulator executable paths, publishes standard install/report state, attaches global install artifacts, and derives compiler scores from toolkit status reports when necessary. Explicit worker-compatible Seal5 configuration avoids assuming host patch paths exist remotely.
- Adapter tests cover combined LLVM, split LLVM, ETISS, request-handle persistence before observation, retry without resubmission, fingerprint mismatch and actual compressed archive path-escape rejection. API worker execution remains simulated in these tests.
- Service-config `HardwareSelectionFlow --only Misc.VerifyConfig` smoke completed **exit 0**; log `/tmp/genie-service-config-smoke.log`. The first smoke attempt only failed because its design directory did not yet exist, then succeeded after creating it.
- PerfSim service upload integration is explicitly rejected rather than routed to the ordinary ETISS worker. Multi-set LLVM service upload packaging and real worker validation remain gaps. Local/Docker execution remains covered by the existing tests.

- Verification after integration: **92 tests passed** with actual reference toolkit tests enabled; `git diff --check` passed. No validation processes remain running from this turn. Real service workers and physical HLS/PerfSim/synthesis remain unvalidated.

### PerfSim service uploads

- Previous goal turn classified as **progress**: LLVM/ETISS service integration, artifact extraction and saved-job retry tests; no validation jobs were left running.
- Inspected actual PerfSim worker entrypoint, retarget script and HLS archive unpacker under `/var/tmp/ga87puy/isaac-docker-service/worker/etiss_perf`. It requires one core description, index YAML and an HLS directory archive, and produces `etiss_perf_install`, uarch/INI and monitor artifacts. The available templates require core `XIsaacCore`.
- Added independent `USE_ETISS_PERF_SERVICE`/`ETISS_PERF_SERVICE_TAG`, so ordinary ETISS service configuration does not silently choose the wrong worker. PerfSim bridge now uploads the stage index and HLS output root, preserving report paths. Index HLS_DIR remains supported as a fallback.
- HLS uploads use deterministic gzip/tar metadata and reject links/special files to match the worker unpacker's contract. Upload contents participate in the saved job fingerprint. The bridge normalizes its own published install-path annotation out of the request snapshot, so successful state publication does not turn an identical retry into a new request.
- PerfSim service integration test inspects real compressed upload contents and validates simulator/uarch/INI/monitor outputs from a synthetic worker archive, then retries without submitting another job. This is API/artifact-contract evidence, not real timing-model execution.
- Added deterministic archive/modified timestamp and symlink rejection checks. Service configuration smoke completed **exit 0**, log `/tmp/genie-service-config-smoke-perf.log`. Real workers, physical HLS/PerfSim/synthesis, multi-set compiler service packaging and broader parity review remain outstanding.

- Latest validation: **94 tests passed** with the real reference toolkit enabled; `git diff --check` passed. No long-running validation jobs remain from this turn.

### Final split-compiler validation and synthesis selector audit

- Previous goal turn classified as **progress**: PerfSim service upload/artifact integration and deterministic packaging tests. No jobs were left running.
- Started final five-candidate split LLVM retargeting from the actual final reanalysis state. Initial session **39394** is terminal with a sandbox DNS failure fetching CoreDSL2LLVM. Retried with network access; **session 7419 is verified live** and the internal build log is advancing through an incremental ~633-target build. Do not restart while it runs.
- Retry log `/tmp/genie-workload-final-split-llvm-retry.log`; internal build log `/tmp/genie-workload-run/runs/RUN_2026-10-21_09-29-40/sess/work/initial/local/temp/seal5_llvm/.seal5/logs/seal5.log`. Next validation after success is final per-instruction benchmark/comparison using its produced saved state.
- Audited prototype synthesis selectors. Added typed `ASIP_SYN_TOOL`, `FPGA_SYN_TOOL` and both `*_SEARCH_FMAX` options. Unsupported backends and fmax search now fail before artifact reads/tool execution instead of allowing ignored settings to produce misleading fixed-clock results. The reference's fmax code itself is TODO; no fmax implementation is claimed.
- Four regressions verify early rejection for ASIP/FPGA backend and fmax settings. Full validation: **98 passed** with the actual reference toolkit enabled; `git diff --check` passed.

### ETISS service artifact relocation

- Previous goal turn classified as **progress**: synthesis selector handling and real final split-compiler launch. Polled **7419**, confirmed still live with advancing linking log; no restart performed.
- Inspected actual installed ETISS helper and ETISS sources. `run_helper.sh` hardcodes its install prefix, so an otherwise valid service artifact would invoke worker-local paths after download. ETISS's `installDir()` itself derives its location from the loaded module, and its build uses relative RPATH.
- Added helper relocation before service install publication: replace exactly one expected ETISS_DIR assignment with a path relative to the script. The operation is idempotent; unknown generated-helper layouts fail explicitly. Original installations remain unchanged.
- Two regression tests exercise moving the installation (including a directory containing spaces for path resolution) and unknown-layout rejection. These test helper path resolution, not full simulator support for spaces in every upstream command.
- Copied actual final-stage ETISS installation into `/tmp/genie-relocated-etiss-staging`, relocated the helper, then moved the tree to `/tmp/genie-relocated-etiss-validation`. Ran actual CRC32 `MLonMCU.ISEBench(in_stage=final)` with that saved state: **exit 0**, session 28935 terminal. Log `/tmp/genie-relocated-etiss-bench.log`; saved state under `RUN_2026-10-21_20-05-11/01-mlonmcu-isebenchin_stagefinal/state_out.json`. This proves a locally built relocated install works with real benchmark execution; it is not real service worker validation.
- Full suite: **100 passed** with actual reference toolkit enabled; `git diff --check` passed. Final split-compiler **7419 remains live**; poll before any restart.

### Existing service validation and deployed-script synchronization

- Previous goal turn classified as **progress**: ETISS launcher relocation and real relocated-local-install benchmark. Continued polling final split compiler 7419 rather than restarting it.
- User identified the existing Compose service and requested checking script synchronization. Clarified that earlier service tests were simulated API/artifact contracts, not real worker execution. Started isolated stack was removed before using the existing one; existing service containers were not restarted or modified.
- Existing localhost:8080 API reports ready; five workers advertised LLVM/ETISS/PerfSim tags and were idle before submission. Submitted real ETISS job **63f3d2b5-2b8e-44e4-96d8-fd92e7a4ca17** through GenIE. Session **87304 completed exit 0**: real worker build, artifact download/extraction and state publication. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_20-08-20/01-isaac-retargetissin_stagefinal/state_out.json`; log `/tmp/genie-real-service-etiss.log`.
- Fixed a missing service input discovered before that submission: generated core descriptions import their generated instruction set. Upload it through the API's second description field, retaining its filename for API import rewriting. Its name/content now participate in retry fingerprinting. Multi-set service packaging remains unsupported.
- Compared deployed container script hashes and full diffs against `/var/tmp/ga87puy/isaac-docker-service` and local prototype scripts. Audit: `docs/SERVICE_SYNC.md`; snapshots `/tmp/genie-service-script-audit`. ETISS/PerfSim retarget script differences are progress messages; deployed worker.py also lacks newer progress parsing. **Running LLVM wrapper is substantially older**, lacks `/scripts/prepare_llvm.py`, and differs from the current checkout pipeline. No rebuild/restart performed.
- Local prototype PerfSim/Seal5 scripts match the inspected reference. Local ETISS has an additional 16-bit-instruction-set null guard absent from the reference and service implementation. Recorded this functional difference instead of assuming literal parity.
- Final split compiler **7419 completed exit 0**. Saved state `/tmp/genie-workload-run/runs/RUN_2026-10-21_20-02-07/01-isaac-retargetllvmin_stagefinalsplittedtrue/state_out.json`; all **5 score 1.0**, zero unsupported.
- Merged real service ETISS install into final split state and launched actual six-row baseline/per-instruction evaluation. Session **19800 is terminal, exit 2**: all simulator executions fail at the dynamic loader because **libboost_filesystem.so.1.71.0** is missing on the host. This is a worker-to-host runtime ABI/dependency gap; service artifact structural validation alone does not prove runtime portability. Log `/tmp/genie-final-per-instr-service.log`.
- Last suite after service companion upload fix: **100 passed** with actual reference toolkit enabled. Both real service/split-compiler handles are terminal. Remaining next actions include resolving worker-artifact runtime dependencies/execution environment and validating final per-instruction evaluation; real LLVM/PerfSim service execution remains unverified.

### Service runtime compatibility and architecture provenance

- Previous goal turn classified as **progress**: actual existing-service ETISS build, deployed-script audit, final split-compiler success and discovery of the host runtime dependency failure.
- Added opt-in `ETISS_SERVICE_RUNTIME_IMAGE`: service installs can preserve their native helper and run it in a temporary compatible Docker container with caller UID/GID. Installed simulator/ELF/INI inputs are mounted read-only; the current run directory is writable. Clearing the setting restores native execution. The chosen image is published in stage metrics by the service step.
- Existing completed ETISS job was resumed to configure runtime without a new build. First benchmark attempt failed on sandbox Docker permissions; approved retry loaded libraries but exposed ETISS plugin paths embedded under the worker's original `/jobs/.../etiss_install` prefix.
- Runtime configuration now reads `ETISS_INSTALL_DIR` from the installed config header and mounts the downloaded installation at that prefix inside the container too. Used exact original worker image ID `sha256:286c0e8db448131bfeb36853c172fce6bc26f56ab0585124be388e2e82768bef`; the current same-name tag points to a different image, reinforcing the synchronization finding.
- Library/plugin loading succeeded, but actual benchmark then produced repeated memory-access errors. Stopped only our validation process tree and its own temporary container `busy_jones`. Session **64981 terminal (143)**; no existing service worker was stopped/restarted. Failure log `/tmp/genie-final-per-instr-service-runtime-prefix.log`. Real service semantic/runtime parity is still **unproven**.
- Compared architecture source revisions: deployed service `etiss_arch_riscv` **45e3067fcaac9e1cd79c4a008fa570c60055af92**, local installation **5ea909ab11111dc54080ea45ae8cda960b0bb193**. M2-ISA-R Git HEAD matches at **051d3354811e94f6ed61f4fdc54188370884e828**; working-tree equality is not established. Service ETISS job checkout is **cebb3788613fd8f6f4845eb93e9ad67b2806d7bd**. These differences are evidence for further comparison, not a proven explanation of the memory errors.
- Added runtime wrap/restore, image/mount and embedded-prefix checks. Full suite **101 passed**, `git diff --check` passed.
- Started independent final per-instruction validation with the actual **local** final split compiler and local ETISS install, without substituting it for failed service validation. **Live session 47586**, log `/tmp/genie-final-per-instr-local.log`; poll before restart.

- Local final per-instruction session **47586 completed exit 0** at 20:38:15. Actual six-row baseline/five-instruction benchmark, comparison and toolkit metric annotation passed. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_20-37-45/02-isaac-compareisebenchin_stagefinalper_instrtrue/state_out.json`; log `/tmp/genie-final-per-instr-local.log`. All validation sessions from this turn are terminal. This completes the previously outstanding local final split/per-instruction check, while service workload semantics remain unresolved.

### Generated-architecture comparison and repeatable deployment audit

- Previous goal turn classified as **progress**: runtime wrapper/prefix compatibility fixes, service workload failure captured, and successful actual local final per-instruction evaluation. No jobs remained live.
- Extracted the actual compiled `ArchImpl/XIsaacCore` sources from both local and downloaded service source archives into `/tmp/genie-service-script-audit/{local-generated,service-built}`. Also copied worker parser output separately; avoided treating its unmodified generated architecture implementation as the compiled implementation.
- Confirmed functional generated differences: service floating-point registers use pointer aliases while local output uses a packed register bank; CSR layouts differ too. Emitted instruction code differs beyond timestamps (including casts/next-PC expressions). Actual compiled architecture-specific implementation differs only by the previously identified local null guard for the 16-bit set.
- The rv_base submodule differs (`749b7cbdde9596a119b3f580039c58e40d5614d5` service ancestry versus `da934064da56ca6c9c79bcaf1d3bba0b79d53150` local), with substantial RVI/RVF/RVD and other definition changes. Service M2-ISA-R has an uncommitted nested-conditional generation fix; local checked-out/installed instruction_transform comparison is identical. Same Git HEAD does not prove same installed code. No causal attribution for runtime memory errors is claimed yet.
- Added `scripts/audit_retargeting_sync.py`, a read-only deployed-file/hash audit with explicit container selection and JSON output. It records Docker/file-access errors separately from hash comparison. Does not mutate/restart services or source checkouts.
- Initial sandbox audit could not access Docker; approved retry checked ten deployed files: **1 match, 8 different, 1 unavailable** (missing LLVM prepare script). Output `/tmp/genie-service-script-audit/deployed-sync.json`. Exit 1 is expected for this mismatched deployment, not a failed audit command.
- Added three byte-match/mismatch/unavailable regressions. Full suite **104 passed**, `git diff --check` passed. Updated `docs/SERVICE_SYNC.md` with the reproducible audit command and generated-source evidence. No validation processes started beyond completed audits/tests.

### Pinning service CoreDSL inputs

- Previous goal turn classified as **progress**: generated source comparison and repeatable deployed-worker audit. No jobs remained active.
- Added opt-in `SERVICE_BUNDLE_COREDSL`: recursively inline host CoreDSL imports in declaration order, deduplicate shared files, preserve comments, and reject cycles/missing dependencies before submission. Request-side `description_sources.json` records source paths/hashes. Bundled contents participate in the existing job fingerprint. Worker sources/images remain unchanged.
- Parsed the actual five-instruction bundled core (12 source files, 145,903 bytes) with the real installed M2-ISA-R and generated its architecture. All **16 compared register/instruction files match** the known-good local generated sources after removing generation timestamps. Evidence `/tmp/genie-coredsl-bundle-validation/{parser.log,writer.log,comparison.json}`. This verifies local semantics-preserving packaging, not remote execution.
- Added deduplication/order/comment/source-change/cycle/missing-file tests and a bundled service-step lifecycle/retry case. Full suite **107 passed**; `git diff --check` passed. Bundling defaults false to preserve existing request identities; a changed request requires a fresh stage/workspace.
- Created independent `/tmp/genie-service-bundled-validation` state/index copies and submitted actual bundled ETISS service job **30b70bd6-50f1-4ad9-9a33-79db172f1cee** through the existing localhost API. **Live session 84196**, log `/tmp/genie-service-bundled-validation/retarget.log`. Worker log showed 95% build progress on last authoritative inspection. Poll before restart; after success evaluate its downloaded simulator against the local final compiler.

- Bundled service retarget session **84196 completed exit 0** at 21:06:09. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_21-04-48/01-isaac-retargetissin_stagefinal/state_out.json`. No worker image/script/source was changed.
- First evaluation launch failed because the isolated workdir lacked names.csv. Copied the original generated names file and retried. Also fixed `ISEBench` to honor the saved `<stage>.names_csv` path, falling back to its historical workdir path for older states.
- Actual bundled service six-row final per-instruction benchmark/comparison **session 94054 completed exit 0** at 21:11:33. State `/tmp/genie-workload-run/runs/RUN_2026-10-21_21-11-16/02-isaac-compareisebenchin_stagefinalper_instrtrue/state_out.json`; log `/tmp/genie-service-bundled-validation/per-instr-retry.log`.
- Compared actual local/service comparison tables: all six rows have identical `Run Instructions`, relative instruction counts, `ROM code`, and relative ROM-code measurements. Extracted actual bundled service generated sources and compared all **16 register/instruction files** with local: **16/16 match** after removing timestamps. Evidence `/tmp/genie-service-bundled-validation/generated-comparison.json`.
- This controlled source-only change resolves the earlier service memory-error workload for this configuration. It establishes imported-description mismatch as a working diagnosis/correction, without attributing the failure to one particular upstream instruction change or claiming other workloads/workers are verified.
- Changed `SERVICE_BUNDLE_COREDSL` default to **true** following successful real validation. Legacy unbundled job resumption requires explicit false; changing request contents continues to require a fresh workspace. Updated service configuration and documentation.
- Latest full suite **107 passed**, `git diff --check` passed. All validation sessions from this turn are terminal. Real LLVM/PerfSim service validation, stale LLVM deployment, multi-set compiler service packaging and physical hardware evaluation remain outstanding.

### Multi-set LLVM service packaging

- Previous goal turn classified as **progress**: real bundled ETISS service build/evaluation now matches local output; no validation jobs remained live. Revalidated worktree/progress before selecting remaining work.
- Fixed LLVM service handling of semicolon-separated `ISAAC_SET_NAME`: resolve/check each generated description, choose `.splitted.core_desc` for split retargeting, and combine all selected sets into one API description with shared imports included once. Previously the path contained the literal semicolon list and failed before submission.
- Extended CoreDSL bundling to multiple roots with shared dependency tracking. Empty names, missing descriptions and unbundled multi-set requests fail before HTTP submission. Single-set request semantics remain covered by existing tests.
- Added combined/split multi-set service lifecycle/retry tests plus shared-base deduplication coverage. Full suite **110 passed** with actual reference toolkit tests enabled; `git diff --check` passed.
- Actual parser validation: built two distinct set names from the real final five-instruction description, bundled their common RVI dependencies and ran `seal5.frontends.coredsl2_seal5.parser`: **exit 0**. The resulting trusted pickle contains both **First** and **Second**, each with **5 instructions**. Evidence `/tmp/genie-multiset-description-validation/{seal5-parser.log,gen_model/Combined.m2isarmodel}`.
- Initial parser experiment used syntactically invalid empty instruction-set bodies; corrected the fixture to actual generated instruction definitions before claiming parser coverage. The invalid attempt is preserved in parser.log for transparency.
- Updated service documentation. This completes multi-set upload packaging, **not** remote LLVM compile/execution validation. The existing LLVM worker deployment remains stale; no service rebuild/restart performed and no jobs are active from this turn.

### Dedicated current-image LLVM service validation

- Previous goal turn classified as **progress**: multi-set combined/split packaging and real Seal5 multi-set parser proof. No live jobs remained at its end.
- Revalidated deployed versus cached LLVM images: shared worker runs **fe424224f6c1839f3ec7f2970b10927726f65b3494556ce5ee39bdbf0f601bcd**; cached latest image is **8153019799d27441c807d36223f552bbef68fbdcc234ba89aab385ae30293fcf**. Verified cached image hashes for prepare_llvm.py, run_retarget.sh and worker.py exactly match current service checkout.
- Started only our dedicated `genie-llvm-validation-worker` from that pinned image, attached to existing API network/jobs volume but advertising **genie-llvm-validation** only. Shared worker containers were not modified/restarted. Only our explicitly tagged jobs are eligible for this worker.
- Submitted actual five-instruction compiler job **64d07f09-c904-458d-af77-7951e74ed6a1**. Session 86519 terminal: failed before compilation because my uploaded filter retained only XIsaac while removing referenced RV32I, triggering the old Seal5 filter's KeyError. Preserved the failed request.
- Corrected request config to retain parent sets while keeping only CUSTOM0..CUSTOM4 instructions; created independent `/tmp/genie-llvm-service-validation-v2` workspace. Real job **78fa5bde-3b45-47e1-8d4e-54b3d1dddfe4** is **verified live**, session **11881**. Worker log advanced through **330/4048 LLVM prerequisite targets** on last inspection. Do not restart while it runs. GenIE log `/tmp/genie-llvm-service-validation-v2/retarget.log`; worker log `/jobs/78fa5bde-3b45-47e1-8d4e-54b3d1dddfe4/logs.txt` inside our worker.
- Added finite service log download and automatic request-local `worker.log` capture on terminal failure/observation timeout, preserving original errors when diagnostics cannot be fetched. Re-observed the earlier failed job (no submission) and confirmed its original KeyError trace is saved locally under `/tmp/genie-llvm-service-validation/sess/work/final/service/seal5_request/worker.log`; diagnostic session 45515 is terminal.
- Added finite-log HTTP request regression. Full suite **111 passed** with actual reference toolkit enabled; `git diff --check` passed. Dedicated real LLVM build remains live; remote compiler artifacts/benchmark execution are not yet claimed.

### Query configuration parity audit

- Previous goal turn classified as **progress**: dedicated current-image LLVM service launch, corrected filter configuration and real failure-log capture. Re-polled session **11881**, still verified live. Its worker log advanced from ~864 to **1197/4048** prerequisite targets; no restart performed.
- Compared `flow_isaac_query.sh` and the actual toolkit parser with `ISAAC.QueryCandidates`. Added seven missing typed controls: result limit, XLEN (canonical ISAAC_XLEN with XLEN alias), minimum/scaled isomorphism weight, sorting, top-k and MaxMISO partitioning.
- Optional controls preserve toolkit/query-YAML defaults when unset; zero values are forwarded. Target XLEN is used when no explicit query XLEN is supplied. Negative limits/weights and invalid word sizes fail before database access.
- Query now publishes stage names CSV and the combined candidate PDF when the toolkit generates it, checks the index artifact, and raises an explicit empty-result error. The toolkit already combines PDFs; avoided duplicating that work.
- Added override/zero-value, target-default, artifact-publication and four invalid-parameter regressions. Full suite **117 passed**, `git diff --check` passed.
- Started actual override query (`topk=3`, result limit 5, minimum weight 0, scaling/sorting/partition controls) against isolated Memgraph port17687, using independent `/tmp/genie-query-overrides-validation`. Initial network-denied session 86760 is terminal; network-enabled session 44290 failed on my incomplete copied-session fixture (metadata without artifact contents), before the actual query.
- Corrected the fixture by copying the original **choices** table into the isolated session and retaining its metadata; this is the table the query consumes. Did not modify original session/index files or purge the graph DB. **Live session 20789**, log `/tmp/genie-query-overrides-validation/query-copied-table.log`; actual query reached graph rendering. Poll before any restart.
- Real LLVM service build **11881** also remains live. No success claims yet for either pending process. Updated migration docs with query controls and state artifacts.

### Query execution complete and choice-flow parity

- Previous intervening user-facing status turns supplied progress-file location/status only. Revalidated authoritative handles before continuing: query session **20789 completed exit 0**, LLVM **11881 remained live**; neither was restarted.
- Actual override query produced exactly **3 candidates** with requested limit/weight/sort/partition controls. Saved state `/tmp/genie-workload-run/runs/RUN_2026-10-22_09-39-45/01-isaac-querycandidates/state_out.json`. Published index **9,072 bytes**, names CSV **105 bytes**, combined PDF **53,450 bytes**. Original 110-candidate outputs remain separate.
- Audited `flow_isaac_pick.sh`: it gates unsuitable/empty results and generates full/minimal choice HTML. Python PickChoices lacked these gates and ReportChoices remained NotImplementedError.
- Implemented explicit all-row suitability and nonempty-choice gates, multiple potential-row metric support, saved choices/potential paths and corrected `sess.num_choices` metric (retaining legacy typo alias).
- Replaced ReportChoices placeholder with native HTML generation using choices, LLVM block addresses and saved trace disassembly. End-exclusive ranges, text escaping, full/minimal outputs and local styling; no prototype shell invocation or external browser scripts. Registered it after picking in both default and standalone prototype flows.
- Added four gate/multiple-row/report regressions. Full suite **121 passed** with real reference toolkit enabled; `git diff --check` passed.
- Real report CLI against full original session completed **exit 0**, two choice sections in both outputs. State under `/tmp/genie-workload-run/runs/RUN_2026-10-22_09-57-31`; log `/tmp/genie-choice-report-validation-full-session.log`. First attempt used the deliberately minimal query fixture, which lacks the block table, then reran against the correct full session. Report validation handle 84891 is terminal.
- LLVM job **78fa5bde-3b45-47e1-8d4e-54b3d1dddfe4**, session **11881**, remains verified live. Build advanced beyond its 4048-target prerequisite phase into another patched LLVM link phase (**37/194** most recently observed). Do not restart while live. Dedicated worker and shared service remain as previously recorded.

### LLVM service build and combined service-toolchain workload complete

- Prior interrupted turn classified as a **verified wait**: polled the same live LLVM job and observed installation/deployment progress. User paused/resumed; on resume re-polled authoritative handle 11881 and worker status rather than restarting.
- Actual LLVM job **78fa5bde-3b45-47e1-8d4e-54b3d1dddfe4** reached **finished**, worker elapsed **2303 seconds**. GenIE session **11881 completed exit 0** after download/extraction/report processing. State `/tmp/genie-workload-run/runs/RUN_2026-10-22_09-22-15/01-isaac-retargetllvmin_stagefinalsplittedfalse/state_out.json`.
- Downloaded compiler starts natively (`clang --version`: LLVM 19.1.6, source commit fa3a91bab8180a73b7c5b7139bfaf640cf75e593). All **5 custom instructions score 1.0**, zero unsupported; install and score/diff report state paths exist.
- Combined the real downloaded LLVM install with the previously validated bundled service ETISS install, then ran actual CRC32 aggregate runtime/memory comparison and annotation: **session 54159 completed exit 0**. State `/tmp/genie-workload-run/runs/RUN_2026-10-22_10-02-32/03-isaac-assigncomparisonmetricsin_stagefinal/state_out.json`; log `/tmp/genie-both-service-toolchains-bench.log`.
- Both-service-toolchain measurements match local: instruction-count ratio **0.7392686852075269**, ROM-code ratio **0.9995226274584684**. This verifies the current-image dedicated LLVM worker for this single-set five-instruction workload, not the stale shared LLVM worker or multi-set execution.
- `/tmp` had only ~9 GB free after worker artifact processing. Added `SERVICE_KEEP_ARCHIVE` (default false): delete the downloaded transfer archive only after all required artifact/report validation and state-index annotation succeed, matching the prototype client; retain on failure or explicit opt-in. Installed toolchains/source reports remain untouched.
- Re-observed the completed LLVM job (no new submission), confirmed installation reuse and removed its **1.2 GB** transfer archive through the new successful-validation lifecycle. Available space returned to ~10 GB. Retention true/false are covered by existing service lifecycle tests.
- Full suite after cleanup implementation **121 passed**; focused lifecycle suite after explicit retention-true coverage **15 passed**; `git diff --check` passed. Updated service/mode/migration docs to current measured validation scope.
- No validation jobs remain active from this turn. Our dedicated LLVM worker remains idle with its build cache for potential further validation; shared workers were not restarted/changed. HLS/source-library clarification remains pending; real PerfSim, multi-set LLVM workload, physical HLS/synthesis and final parity audit remain outstanding.

### Native report sections and persisted timing

- Previous goal turn classified as **progress**: real LLVM/ETISS service-toolchain evaluation completed and transfer-archive retention handling verified. No validation jobs remained live; dedicated LLVM worker is idle.
- Audited `flow_report.sh` / `gen_ci_summary.py`. Extended native CreateSummary beyond raw state listings: selected typed experiment config, available step timing, ISE potential, choice HTML, query/benchmark comparison tables, Sankeys and generated instruction-set CoreDSL, with existing complete metrics/artifact listings retained.
- Reports read declared artifact paths and use the new GenIE state/config model, not experiment.ini/vars.env or shell-flow delegation. Config fields are explicitly selected; no process-environment dump. Generated-code fences handle embedded backticks. Bundles now include HTML/PDF artifacts.
- Successful step lifecycle now persists measured monotonic execution seconds in state under `timing.<id>.seconds`; previous timing entries survive state resumption. Existing runtime.txt behavior remains. Historical states without timings do not receive invented values. Query step publishes available query-metrics CSV for reporting.
- Added summary-section/config-selection and HTML/PDF bundle regressions; extended actual-toolkit lifecycle integration to verify timing persistence. Full suite **123 passed**, `git diff --check` passed.
- Executed actual CreateSummary/PrepareUploads with measured compiler/simulator tables, real choice HTML, original full-query metrics/PDF and generated descriptions: **exit 0**. First report under `RUN_2026-10-22_10-11-03` was ~558 KB and bundled 33 artifacts. Refined the fixture to use original initial-query artifacts consistently with its 110-candidate stage instead of the separate three-candidate override test.
- Resumed report run includes recorded timing values and bundles **34 artifacts**, including two HTML reports and one PDF. Saved state `/tmp/genie-workload-run/runs/RUN_2026-10-22_10-12-20/02-ci-prepareuploads/state_out.json`; log `/tmp/genie-measured-summary-validation-resumed.log`. No validation processes remain live from this turn.
- Remaining includes real PerfSim/multi-set LLVM workload validation, physical HLS/synthesis prerequisites and final stage/switch audit. HLS/source/library clarification remains pending.


### PerfSim comparison parity (2026-10-22)

- Audited `flow_compare_perf.sh`: the native path previously evaluated only a fixed microarchitecture and used the instruction-only report analyzer, omitting the prototype ranking.
- ISEPerfSimBench now reads the stage's `etiss_perf.uarchs_csv`, runs the baseline plus every generated microarchitecture, and compares both instructions and cycles. MLonMCU exports `perf_sim.core` as `uArch`.
- Added ISAAC.CompareISEPerfSimBench, wired into the prototype phase and PerfSim flow, to merge cycle/instruction/memory reports with the real toolkit analyzer and publish `uarch_ranking_csv`. Local retargeting now publishes the same microarchitecture manifest path as service retargeting.
- Validation: argument and execution-plan tests cover two microarchitectures; real toolkit analyzer/ranker integration processes three fixture rows and verifies ordering/ranks. These fixture reports establish orchestration/report compatibility, not actual simulator performance. Full suite: 126 passing tests.
- Actual PerfSim worker execution and physical HLS remain outstanding.


### BUILD_ARCH phase switch and compiler reuse (2026-10-22)

- Audited aggregate comparison and retrace scripts, including performance variants. Their BUILD_ARCH branch composes selected per-instruction extensions and reuses the initial compiler specifically for filtered/filtered_selected stages.
- Added `--build-arch` to those four Python phases; unrelated phases reject it explicitly. Fixed ISEBench and ISETrace compiler lookup while retaining the selected stage's names and simulator.
- Tests cover each phase, unsupported use, multi-microarchitecture comparison with compiler reuse, and retrace architecture composition with different compiler/simulator stage paths. The existing 132-test suite passed; the additional retrace test passes (133 tests total). Real execution of this particular compiler-reuse branch remains pending.


### Optional filtering thresholds and prototype names (2026-10-22)

- Fixed declared optional thresholds: `null` now omits the corresponding toolkit argument rather than passing the invalid string `None`. Zero remains an explicit threshold.
- Added prototype configuration aliases `MIN_SEAL5_SCORE` -> `FILTER_MIN_SEAL5_SCORE` and `MIN_UTIL_SCORE` -> `FILTER_MIN_UTIL_REL`.
- Real toolkit tests verify null, zero and nonzero compiler-score thresholds with runtime filtering disabled; selected candidates and generated names are checked. Configuration loading verifies both legacy names. Full suite: **137 passed**; `git diff --check` passes.


### Performance phase audit and direct executable service runtime (2026-10-22)

- Inspected performance load/analyze shell scripts: they invoke the same toolkit load/analyze stages as the standard variants (their performance-specific behavior is a prototype TODO). Shared Python steps therefore preserve those commands.
- Found a real runtime gap in the installed MLonMCU `EtissPerfTarget`: it uses `bare_etiss_processor` directly and explicitly disallows the run helper. The service-compatible image wrapper previously covered only `run_helper.sh`.
- Added a separate `bin/genie_etiss_processor.py` launcher when configuring a service runtime image, preserving the original binary. MLonMCU performance arguments select this launcher when present. Docker runs the native executable directly with install library paths and the worker's embedded install prefix mounted. Clearing the runtime image removes both wrappers.
- Direct executable invocation mounts input ELF paths supplied as `--key=/path` or through the INI's `vp.elf_file` / binary configuration entries, alongside existing INI/install/workdir mounts.
- Real validation: service-built bundled ETISS install at `/tmp/genie-service-bundled-validation/sess/work/final/service/etiss/etiss_install`, existing final CRC32 ELF, isolated cwd `/tmp/genie-direct-runtime-smoke`; direct launcher exited **0**, `MLONMCU EXIT: 0`, **2,961,483 Run Instructions**, identical to the previously validated helper execution. An initial `--help` probe loaded the executable but the upstream binary treated that as fatal (exit139); the subsequent actual workload is the execution evidence.
- This validates native execution compatibility with the existing ETISS service artifact, not a timing-enabled PerfSim worker build. MLonMCU also requires `etiss_perf.src_dir`; source/metrics-script publication and real performance execution remain to be validated.
- Tests cover binary preservation/restoration, direct launcher selection and external ELF mounts; full suite **140 passed**.


### PerfSim source publication for MLonMCU (2026-10-22)

- Inspected installed MLonMCU `EtissPerfTarget.REQUIRED` and its metrics-script lookup: `etiss_perf.src_dir` must point to the source tree containing `src/bare_etiss_processor/get_metrics.py`.
- Both service and local PerfSim retargeting now unpack their generated source archive, validate that script, and publish `<stage>.etiss_perf.src_dir`. Benchmark and retrace pass the stage path into MLonMCU, including the compile/memory comparison run.
- Extraction uses the tar data filter in a temporary directory and publishes only after validation. Existing valid source trees are reused; escape paths and archives missing the metrics script fail without publishing a partial tree.
- Real archive validation used the existing bundled ETISS service's `etiss_source.tar.gz`: extracted source includes the 8,332-byte metrics script, and a second call reused the tree. This checks the shared archive handling against an actual worker artifact; it does not establish timing-enabled PerfSim build success.
- Full suite **142 passed**, including service artifact publication/resume, source escape/missing-script rejection and benchmark source forwarding; `git diff --check` passes. Real performance worker execution remains outstanding.


### Real BUILD_ARCH compiler and phase validation (2026-10-22)

- Real compiler probing corrected the earlier directory mapping: initial combined clang rejects `_xisaaccustom24single`, while initial split clang compiles it successfully. The prototype writes both variants into the same directory; GenIE retains separate artifacts. BUILD_ARCH must therefore select `seal5_splitted`, including for reused initial compilers.
- Fixed ISEBench and ISETrace accordingly. The earlier BUILD_ARCH entry's reference to the initial combined compiler is superseded by this evidence. Updated tests deliberately provide only the split artifact for composed-architecture branches.
- Actual Python phase command: `python -m genie.prototype flow_compare.sh --stage initial --build-arch cfg/cva5_reuseio.yml cfg/local.yml -c BENCH=embench_iot/crc32 --design-dir /tmp/genie-workload-run --with-initial-state /tmp/genie-workload-run/runs/RUN_2026-10-22_10-02-32/03-isaac-assigncomparisonmetricsin_stagefinal/state_out.json`, with isolated compatibility PYTHONPATH as in prior workloads.
- Terminal exit **0**: baseline and composed architecture (all 110 individual extensions), runtime and compile/memory reports, and toolkit comparison all succeeded. Baseline **4,005,963** instructions / **41,896** ROM code; composed **3,135,562** instructions / **41,860** ROM code. This is the initial candidate set, distinct from the final five-instruction result.
- Saved state: `/tmp/genie-workload-run/runs/RUN_2026-10-22_12-46-15/2-isaac-compareisebenchin_stageinitial/state_out.json`. Full suite after split-compiler correction: **142 passed**.
- Removed an existing MLonMCU debug print that dumped the inherited environment during execution.
