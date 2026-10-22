# Retargeting script synchronization audit

Inspected on 2026-10-21. This distinguishes running container contents from
the checkout at `/var/tmp/ga87puy/isaac-docker-service`, and from the local
prototype installation actually used by GenIE (`/var/tmp/ga87puy/isaac-demo-new`).
No existing worker was rebuilt, restarted, or modified during this audit.

| Component | Running container versus service checkout | Consequence |
| --- | --- | --- |
| Combined ETISS `/scripts/retarget_etiss.sh` | Diff contains only added progress messages in checkout | Retargeting commands match; progress reporting differs |
| Combined and dedicated PerfSim `/scripts/retarget_etiss_perf.sh` | Same deployed hash; checkout adds only progress messages | Retargeting commands match; progress reporting differs |
| Combined dispatcher `/scripts/run_retarget.sh` | Exact match to `worker/etiss_perf/dispatch.sh` | Routing script is current |
| LLVM `/scripts/run_retarget.sh` | Substantively older than checkout | Calls `/work/seal5_script.sh`; includes placeholder `result.txt` output |
| LLVM `/scripts/prepare_llvm.py` | Absent in running LLVM container | Current checkout's baseline-reset/preflight path is not deployed |
| `/app/worker.py` in inspected LLVM/ETISS containers | Older progress parser | Missing checkout's stage markers, Make progress and improved Ninja parsing |

The old LLVM wrapper does invoke a retargeting script before writing its
placeholder. This audit does **not** establish whether that old script produces
usable compilers; it establishes that the checkout's current LLVM pipeline is
not what the running container executes. Real LLVM service validation remains
pending. GenIE requires compiler executables/reports and does not accept the
placeholder as a compiler artifact.

Deployed hashes:

```text
combined ETISS retarget: d9d4d6b394fb3964c8de9eba870f2738fadd22a484ee8a536e1a4317a810c090
PerfSim retarget:        ec07b7020f31c15bb0b2ea31a2628ccf4d221594aa5ecd035b0e2522de4ea77a
combined dispatcher:    20e9665ce66565be3afced2d7f7f5aab44bf0a8c28020ed82b5299e5371e0ee6
LLVM wrapper:           dfe41788cc15fffc3173cdca500ddad678d652535a76eb433c24469e59da2218
worker.py:              dfdcf0d71f2cc0e1dabb63a0f444d58985b7ce380045bc58c4b3f53a623f5e75
```

The local prototype's PerfSim and Seal5 scripts exactly match the inspected
`isaac-demo` reference revision. Its ETISS script differs by one functional
guard: it checks that the 16-bit instruction set exists before dereferencing it
in the copied architecture implementation. The service ETISS implementation
does not contain that added guard. It builds job-local ETISS checkouts and
otherwise follows the same parser/generator/architecture/build/install stages,
with different artifact names and directory layout.

Copied running scripts and diffs can be reproduced from the read-only container
files. Snapshots from this audit are in `/tmp/genie-service-script-audit`.
Image tags alone are insufficient evidence of synchronization: the running
containers can retain an earlier image after a tag is rebuilt.

Repeat the deployed-file comparison with:

```sh
python scripts/audit_retargeting_sync.py \
  --service-dir /var/tmp/ga87puy/isaac-docker-service \
  --llvm-container isaac-docker-service-worker-llvm-1 \
  --combined-container isaac-docker-service-worker-etiss-combined-1 \
  --perf-container isaac-docker-service-worker-etiss-perf-1 \
  --output /tmp/deployed-sync.json
```

Exit 1 means at least one mismatch or unavailable file. The JSON includes each
source/deployed hash and access error; an unavailable result can mean Docker
access failed, not just a missing container file. The observed accessible run
checked ten files: **one match, eight different, one unavailable** (LLVM's missing
`prepare_llvm.py`). It performs no service rebuild, restart or file mutation.

The existing API on localhost:8080 reported ready and five idle workers before
validation. GenIE subsequently submitted real final ETISS job
`63f3d2b5-2b8e-44e4-96d8-fd92e7a4ca17`; build/download/validation completed with
exit 0. Runtime evaluation of its downloaded installation is recorded separately
in [PROGRESS.md](../PROGRESS.md).

Additional source provenance from that job:

| Source | Service worker | Local installation |
| --- | --- | --- |
| `etiss_arch_riscv` | `45e3067fcaac9e1cd79c4a008fa570c60055af92` | `5ea909ab11111dc54080ea45ae8cda960b0bb193` |
| M2-ISA-R Git HEAD | `051d3354811e94f6ed61f4fdc54188370884e828` | same HEAD; this does not prove identical working trees |
| ETISS job checkout | `cebb3788613fd8f6f4845eb93e9ad67b2806d7bd` | comparison with the actual local build checkout still pending |

The service simulator initially failed on the host due to missing Boost 1.71.
Running it in the original worker image, with both the downloaded install and
its embedded worker prefix mounted, resolves dynamic-library/plugin lookup.
The initial unbundled workload then reported repeated memory-access errors and
was stopped. A successful service build/download alone was therefore insufficient
evidence of successful benchmark execution.

Comparing the generated architectures extracted from actual local/service
source artifacts confirms differing floating-point and CSR register layouts,
plus differences in emitted instruction code. The copied architecture-specific
implementation differs only by the local 16-bit-set null guard. The worker's
M2-ISA-R tree also has an uncommitted nested-conditional generation fix; matching
Git HEAD alone does not establish matching generators.

A subsequent controlled run bundled the host's imported CoreDSL definitions into
the request without changing worker images, generator code, or retarget scripts.
Job `30b70bd6-50f1-4ad9-9a33-79db172f1cee` completed successfully. All 16 checked
register/instruction files generated by that worker match local output after
timestamp normalization. Its actual six-row CRC32 baseline/per-instruction
evaluation passed, with instruction counts and ROM-code measurements exactly
matching local results. This establishes a working correction for the imported
description mismatch for this configuration. It does not identify which upstream
definition change is individually responsible or validate other worker types.
