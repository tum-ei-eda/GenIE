# Development setup

Use Python 3.10 or newer and a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest pyfakefs
python -m pytest test -q
genie --help
```

The runtime installation fetches the OpenLane fork specified in `pyproject.toml`.
The `local` extra installs the additional toolkit/retargeting Python packages;
full workloads also need the tool sources, compiler/simulator builds, and a
running Memgraph database described in the mode documentation. The environment
used during migration is `/tmp/genie-venv`.

To check configuration and flow registration without starting external tools:

```sh
mkdir -p /tmp/genie-config-smoke
genie cfg/cva5_reuseio.yml cfg/local.yml \
  --flow ISSEvaluationFlow -c BENCH=embench_iot/crc32 \
  --design-dir /tmp/genie-config-smoke --only Misc.VerifyConfig
```

`ISSEvaluationFlow` extends the default flow with encoding and compiler score
annotation, retargeted tracing, reanalysis, utilization annotation, scoring, and
sorting before filtering. It is an integration work in progress; the configuration
check above does not validate its external tool commands. Hardware selection and
synthesis steps are registered separately and are not yet part of this flow.

See [migration progress](../PROGRESS.md) for the script coverage checklist,
verified behavior, and remaining work. In particular, the complete prototype
workflow is not yet implemented or validated.

`HardwareSelectionFlow` assembles the longer ISS workflow through final hardware
evaluation. It requires a working Nailgun installation or container, a cell
library YAML, Synopsys and Vivado tool adapters, and the prototype's Python
selection dependencies. For a configuration-only check:

```sh
mkdir -p /tmp/genie-hardware-config-smoke
genie cfg/cva5_reuseio.yml cfg/local.yml \
  --flow HardwareSelectionFlow -c BENCH=embench_iot/crc32 \
  -c HLS_NAILGUN_CELL_LIBRARY=/path/to/library.yaml \
  --design-dir /tmp/genie-hardware-config-smoke --only Misc.VerifyConfig
```

This flow evaluates the filtered candidate set, annotates HLS costs, performs
specialization-aware selection, regenerates a final set, and evaluates its ISS
and hardware results. Full external-tool execution remains unverified. The
iterative selection algorithm requires `SELECT_TOPK=0`; use `SELECT_MAX_COST` to
bound hardware cost.

Optional integration tests execute real ISAAC Toolkit utility modules through the
prototype launcher. Supply existing source checkouts and use the environment in
which their utility dependencies are installed:

```sh
GENIE_TOOLKIT_SRC=/path/to/isaac-toolkit \
GENIE_DEMO_SRC=/path/to/isaac-demo \
python -m pytest test -q
```

These tests exercise score CSV annotation, scoring, both candidate filtering
passes, sorting, names, and top-k selection. They do not emulate compiler,
simulator, HLS, or synthesis execution.

Older prototype dependency checkouts may need the compatibility corrections found
by workload validation. To make isolated copies without editing those sources:

```sh
python scripts/prepare_legacy_tools.py \
  --seal5-source /path/to/isaac-demo/seal5 \
  --logistro-source /path/to/venv/lib/python3.10/site-packages/logistro \
  --output /tmp/genie-compatible-tools
```

Use the emitted `seal5.src_dir` in the initial state's `paths`, and prepend the
emitted compatibility directory to `PYTHONPATH` for the run. The generated JSON
is an override description, not a complete GenIE state file. The helper corrects
the old GitPython tag API call and import-time abbreviated logging arguments.
It requires a fresh output directory and rejects unrecognized source patterns.
