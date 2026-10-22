## GenIE Retargeting Service

GenIE can submit LLVM and ETISS retargeting jobs to an externally hosted service.
Both were built and evaluated together on CRC32 with five custom instructions.
LLVM validation used a dedicated worker from the verified current image; the
shared LLVM container still uses older scripts. PerfSim service execution remains
unverified; see the [migration gap](MIGRATION.md#retargeting-service-gap).

Check https://github.com/PhilippvK/isaac-docker-service for details.

### Using Retargeting Service in GenIE

Add `cfg/service.yml` after your benchmark configuration and set `SERVICE_URL`.
For LLVM, set `SEAL5_SERVICE_CONFIG` to a worker-compatible YAML file. Relative
patch/tool paths must exist inside the worker; host-local Seal5 configuration
is not automatically portable. `SEAL5_SERVICE_TAG` and `ETISS_SERVICE_TAG`
select workers. Service switches take precedence over their Docker switches.

For PerfSim, enable `USE_ETISS_PERF_SERVICE` and select `ETISS_PERF_SERVICE_TAG`
(default `etiss_perf`). It uses the stage's `hls.default.output_dir` parent, or
the index's `global.artifacts.HLS_DIR`, as the HLS upload root. The layout is
preserved in a deterministic gzip tar archive; links and special files are
rejected to match the worker's input contract. The available worker requires
`ISAAC_CORE_NAME=XIsaacCore`. Returned artifacts must contain the simulator,
`uarchs.csv`, `ini/` and `InstructionTrace_XISAAC.json`.

Extraction requires `zstd` and a Python build with `tarfile.data_filter` (including
maintained Python 3.10 versions with the extraction-filter backport).

### Configuring Retargeting Service

The transport in `genie.retargeting_service` implements the job API inspected in
the local `isaac-docker-service` source. It submits multipart `tag`, `cdsl`,
`cpdsl` and `config`; `etiss_perf` also requires `index` and `hls`. This API
requires the description/config upload fields even for jobs that do not consume
all of them. The caller must supply the appropriate files.

`submit` returns a `ServiceJob`; `wait` observes that handle and never submits a
replacement on timeout. A completed job can be downloaded using
`download_artifact`. The transport does not unpack artifacts or publish GenIE
state. The LLVM/ETISS retargeter bridge performs extraction, executable/report
validation and state publication. It stores a private job handle in the stage's
`service/<backend>_request/job.json`; retrying the same state/config resumes that
job rather than submitting again. Changed inputs are rejected. HTTP transport
unit tests use a simulated API; separate real-worker evidence is recorded in
[PROGRESS.md](../PROGRESS.md).

Failed or timed-out retargeter observations also fetch a finite worker-log
snapshot into the request's `worker.log`. The raised error gives that local path;
the saved job handle remains available for observation without resubmission.
If log retrieval fails, the original job failure/timeout is preserved.

ETISS service installs include a generated launcher with a baked-in worker
prefix. The bridge replaces its single `ETISS_DIR` assignment with a path
relative to the installed helper before publishing it. Unknown helper layouts
fail explicitly rather than retaining a worker-local path.

Worker artifacts can depend on libraries unavailable on the submitting host.
Set `ETISS_SERVICE_RUNTIME_IMAGE` to a compatible worker image ID/digest to run
the downloaded simulator in a temporary container. This runs the artifact's
original helper, not the worker's retargeting entrypoint. The bridge preserves
the native helper and records the selected runtime image in stage metrics.
Clearing the setting restores native execution when the service step is rerun.

The runtime mounts the installed simulator and input ELF/INI files read-only,
and the current run directory for output. If the installed ETISS header records
a build-time install prefix, the simulator is also mounted at that prefix inside
the container so older plugin loaders can find their libraries. It runs with
the caller's UID/GID and requires access to Docker. This option does not bundle
worker dependencies into the host installation.

After successful executable/report validation, the transfer archive is removed,
matching the prototype client. Set `SERVICE_KEEP_ARCHIVE=true` to retain it for
debugging. Failed validation retains the archive. Installed toolchains and worker
source/report exports remain available independently of that transfer archive.

`SERVICE_BUNDLE_COREDSL=true` recursively inlines the host's CoreDSL imports
into the submitted description. Shared dependencies are included once; missing
files and import cycles fail before submission. A source/hash manifest is saved
as `description_sources.json` beside the request. This pins the imported
architecture definitions instead of relying on the worker's `etiss_arch_riscv`
checkout. The default is true after real service validation exposed incompatible
worker descriptions. Set it false explicitly to resume an older unbundled job
or intentionally use worker-provided descriptions. Changing this option requires
a fresh stage/workspace, as with any changed service input.
Bundling does not pin the worker's generator or ETISS source version, so successful
local parsing alone does not establish remote execution parity.

For LLVM, semicolon-separated `ISAAC_SET_NAME` values select all corresponding
generated descriptions (`.splitted.core_desc` for split retargeting). Bundling
combines them into the API's single description upload and deduplicates shared
imports across sets. Multi-set requests require `SERVICE_BUNDLE_COREDSL=true`;
missing descriptions and empty set names fail before submission. Both combined
and split upload paths have lifecycle tests, and the real Seal5 parser has been
checked to retain both sets. Remote multi-set compiler execution is unverified.

With bundling enabled, a real five-instruction CRC32 service build and six-row
baseline/per-instruction evaluation passed. Instruction counts and ROM-code
measurements exactly match the local evaluation. This validates ETISS for that
workload/configuration, not LLVM or PerfSim workers; see
[SERVICE_SYNC.md](SERVICE_SYNC.md) and [PROGRESS.md](../PROGRESS.md).


When `ETISS_SERVICE_RUNTIME_IMAGE` is configured, GenIE installs both a
`run_helper.sh` wrapper and a separate `genie_etiss_processor.py` launcher.
The latter preserves the native binary and supports MLonMCU's PerfSim target,
which invokes the executable directly. It mounts ELF files referenced by the
INI and runs with the install's library paths. Disabling the runtime image
restores the helper and removes the direct launcher. Direct execution has been
validated with a service-built ETISS CRC32 workload; timing-enabled PerfSim
worker validation remains outstanding.


PerfSim retargeting also publishes `<stage>.etiss_perf.src_dir` by extracting
`etiss_perf_source.tar.gz`. The tree must contain
`src/bare_etiss_processor/get_metrics.py`; benchmark and retrace steps forward
it to MLonMCU automatically. Source extraction is validated before publication
and reused on resume.
