## GenIE Usage

```sh
CONFIG=cva5_reuseio
MODE=local
FLOW=DefaultGenIEFlow
BENCH=embench_iot/crc32
OUT_DIR=$(pwd)/out/$MODE

genie cfg/$CONFIG.yml cfg/$MODE.yml --flow $FLOW -c BENCH=$BENCH -c DESIGN_DIR=$OUT_DIR
# or: genie --dockerized cfg/$CONFIG.yml cfg/$MODE.yml --flow $FLOW -c BENCH=$BENCH -c DESIGN_DIR=$OUT_DIR
```

For details, check:
- [`CONFIG.md`](./CONFIG.md): Configuration options
- [`MODES.md`](./MODES.md): Available modes
- [`FLOWS.md`](./FLOWS.md): Available GenIE Flows
- [`WORKLOADS.md`](./WORKLOADS.md): Available workloads
- [`OUTPUTS.md`](./OUTPUTS.md): Generated output artifacts 