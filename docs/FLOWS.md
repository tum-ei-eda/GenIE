## GenIE Flows

GenIE uses Python-class defined Flows inspired by the OpenLane2 (now LibreLane) project.

### Selecting a flow

#### Via configuration files

TODO: check meta?

See [`CONFIG.md`](./CONFIG.md) for details!

#### On the command line

```sh
genie ... --flow DefaultGenIEFlow
```

### Available Flows

#### Default Flow (`DefaultGenIEFlow`)

To be renamed to `ISSGenIEFlow`...

**Usage:** Add `--flow DefaultGenIEFlow` to `genie` command.

#### RTL Flow (`RTLGenIEFlow`)

**Usage:** Add `--flow RTLGenIEFlow` to `genie` command.

**Details:**
- Same as default but using RTL simulations instead of ISS

#### PerfSim Flow (`PerfSimGenIEFlow`)

**Usage:** Add `--flow PerfSimGenIEFlow` to `genie` command.

**Details:**
- Same as default but using PerfSim instead of ISS

### Custom Flows

#### Via Python

Custom flows can be defined and registered within GenIE as follows:

```py
from genie.flows import GenIEFlow, DefaultGenIEFlow

# define custom steps...

@GenIEFlow.factory.register()
class CustomGenIEFlow(DefaultGenIEFlow):
    Steps = [
        MyCustomStep,
        ...,
    ]
    Substitutions = {
        "MLonMCU.Bench": MyCustomBench,
        ...,
    }
```

#### Via Config files

Simple substitutions can also be defined as follows: TODO
### Extended evaluation flows

`ISSEvaluationFlow` adds encoding/compiler score annotation, combined and
per-instruction benchmarks, custom tracing/reanalysis, diffs, utilization scores,
and candidate ordering before filtering. A representative CRC32 run has validated
these components; see [PROGRESS.md](../PROGRESS.md) for exact checkpoints.

`HardwareSelectionFlow` continues through filtered evaluation, HLS cost
annotation, specialization-aware selection, final regeneration/evaluation, and
ASIP/FPGA synthesis. Its configuration and Python orchestration are tested;
full physical-tool execution remains unverified. Supply HLS and technology-library
settings before running it. See [SETUP.md](SETUP.md) and [MIGRATION.md](MIGRATION.md).

For individual counterparts of the prototype `flow_*.sh` scripts, use
`python -m genie.prototype --list`. The phase interface accepts GenIE configuration
and saved state, plus candidate-stage options described in the migration guide.
