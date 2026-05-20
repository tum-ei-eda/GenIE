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