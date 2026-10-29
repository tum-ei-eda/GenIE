# Seal5 and service sources

The merged Seal5 and M2-ISA-R fixes are consumed directly from upstream;
GenIE and the service proposal no longer carry compatibility patches for them.
The old marker migration that edited LLVM sources and moved stage-zero tags
has also been removed. The remaining image helper only enables LLVM lit
configuration and retains the required test paths in sparse checkouts.
The demo still has `LLVM_INCLUDE_TESTS=false` and excludes these paths.

## Rebuild corrections (2026-10-29)

The fetched demo main was `5b9a533`. Its `isaacnew-base-4` LLVM tag already
contained disassembler markers, conflicting with Seal5's insertion patch.
The proposed corrections keep **the LLVM baseline marker-free**; the custom insertion patch lives in the demo:

- LLVM `1d0af5ca8`: removes the four disassembler marker lines. Local tag `isaacnew-base-4` now points here.
- Seal5 `b8d5e09`: adds generic configuration-relative custom-file lookup. Seal5 resources remain unchanged. The ISAAC-specific patch lives under the demo’s `cfg/seal5/patches/` directory.
- Demo `be593a0`: updates the LLVM and Seal5 submodule refs together.
- Service `c08a90a`: consumes upstream sources without the obsolete compatibility patches or marker migration.

The demo selects the custom resource explicitly:

```yaml
- name: insert_markers_llvm19_isaacnew_base4
  target: llvm
  file: patches/insert_markers_llvm19_isaacnew_base4.patch
  onlyif: "settings.llvm.state.version.major == 19"
```

The unchanged default patch applies cleanly to stock LLVM 19.1.7. The demo-owned
custom patch applies cleanly against the corrected demo baseline. Inspection confirms 36 unique marker lines across 15 files after
application, and no disassembler insertion markers in the baseline itself.
Full image rebuild/runtime verification of these new commits awaits publication
of the updated images; no images were pulled, built or restarted for this cleanup.

## Setup

`Setup.SetupM2ISAR` and `Setup.SetupSeal5` install the pinned upstream sources
without applying compatibility patches. Existing automatic checkouts must match
the new pins and be clean. Use `M2ISAR_SRC_DIR` or `SEAL5_SRC_DIR` for an explicit
source override. GenIE's local LLVM default is `isaacnew-base-4`; its adapter
preserves that override because the toolkit still hardcodes the older tag.

## Rebuilding the service image

Prepare a separate build context from the audited service revision
`bfbb49f08618e321f060be4a76f2e1fd973de39e`:

```sh
python scripts/prepare_seal5_service.py \
  /path/to/isaac-docker-service \
  /path/to/isaac-docker-service-seal5-main
```

The script copies the checkout, applies the worker changes, and adds the
upstream dependency installer and LLVM lit configuration helper. It does not copy `.env`, job data, virtual environments, or Git
metadata. It rejects incompatible worker sources before copying them.
The LLVM preflight reads the typed model's `sets` attribute. Both the LLVM
and combined ETISS/LLVM Dockerfiles install the pinned typed M2-ISA-R and
upstream Seal5 into `/work/venv`. The image build checks that the baked-in
Seal5 baseline can be loaded by the new version.

Build the dedicated worker image yourself:

```sh
docker compose -p YOUR_EXISTING_COMPOSE_PROJECT \
  --env-file /path/to/isaac-docker-service/.env \
  -f /path/to/isaac-docker-service-seal5-main/docker-compose.yml \
  build worker-llvm
```

Omit `--env-file` if your deployment has no `.env` file. Use the existing
Compose project name so image names and volumes match the deployment.
After current jobs finish, recreate only that worker:

```sh
docker compose -p YOUR_EXISTING_COMPOSE_PROJECT \
  --env-file /path/to/isaac-docker-service/.env \
  -f /path/to/isaac-docker-service-seal5-main/docker-compose.yml \
  up -d --no-deps worker-llvm
```

For a deployment using `worker-etiss-combined`, substitute that service name
in both commands. Check your Compose file for the exact service name.
Rebuilding the image alone does not replace a running container. The API,
Redis and the ETISS-only worker do not need rebuilding solely for
this Seal5 port. Spike-specific behavior support is described below.

A prepared local build context is available at
`/tmp/genie-seal5-service-typed-spike`. No image build or container restart has been
performed for this port.


## Previous validation (before the marker-resource refresh)

The combined migration suite passes 149 tests without failures or skips.
The isolated service worker completed the full fused add/XOR pipeline:
typed parsing, transforms, patch generation/application, both C++ builds,
pattern generation, all three generated tests, installation, source deployment,
Seal5 export and report collection. Its outputs are under
`/tmp/genie-llvm-modern-validation/job/output`; the complete worker log is
`/tmp/genie-llvm-modern-validation/compiler-fused.log`.

The installed compiler emitted the custom `cadd` instruction from generated
LLVM IR. A linked RV32 executable passed in native Spike with the matching
GenIE-generated plugin, including normal and overflow results. Separate
opcode probes also checked zero-register behavior.

GenIE's `CFU.Evaluate` ran a deterministic 64-vector fused-operation benchmark
through the pinned demo runner on Verilator. Both baseline and extended
firmware passed. Their encoding audits found zero custom sites in the baseline
and one allocated custom instruction site in the extended loop. Results:

| Variant | Cycles | Instructions | Validation |
| --- | ---: | ---: | --- |
| Baseline | 1,216 | 591 | Passed |
| Extended | 1,217 | 527 | Passed |

These measurements show correct execution and fewer instructions for this
fixture; they do not show a cycle speedup. Reports are at
`/tmp/genie-cfu-fused-evaluation/run/evaluation/work/cfu_evaluation_combined`.
Earlier native CRC32 discovery and generation checks are described in
[MIGRATION.md](MIGRATION.md).

The initial add-only compiler built successfully but selected an equivalent
base ADD, causing its custom-selection test to fail. The fused instruction
avoids that ambiguous probe. Validation also exposed missing image lit
configuration and the extension test's missing RISC-V target; both are fixed
in the sources above. Renode, physical FPGA execution and arbitrary Spike
instruction behaviors were not covered by these native checks.

## Review and publication

| Directory | Branch | Commit | Remote |
| --- | --- | --- | --- |
| `/tmp/genie-seal5-base4-fix` | `fix/isaacnew-base-4-markers` | `b8d5e09` | `origin` (tum-ei-eda/seal5) |
| `/tmp/genie-llvm-markers-base4-fix` | `fix/isaacnew-base-4-markers` | `1d0af5ca8` | `origin` (PhilippvK/llvm-project) |
| `/tmp/genie-isaac-demo-latest` | `fix/isaacnew-base-4-markers` | `be593a0` | `origin` (PhilippvK/isaac-demo) |
| `/tmp/genie-service-migration-repo` | `genie-typed-seal5-markers` | `c08a90a` | `origin` (PhilippvK/isaac-docker-service) |

Nothing was pushed. Publish/merge Seal5 and LLVM first, then the demo's new
submodule refs and the service changes. The corrected tag must be published
before Docker builds that fetch it. From the LLVM fix directory, after publishing
the branch, update the existing remote tag with an explicit old-value lease:

```sh
git push --force-with-lease=refs/tags/isaacnew-base-4:1b05e25786acdea17acfcb97f346b3f9827ebe3f origin refs/tags/isaacnew-base-4
```

These checkouts are temporary; preserve them until published. The LLVM fix
checkout shares objects with `/tmp/genie-isaac-demo-latest/llvm-project`.
GenIE changes in `/var/tmp/ga87puy/genie_codex/GenIE` still need a commit and push.
