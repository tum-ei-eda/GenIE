# GenIE usage

Install and check the development environment using [SETUP.md](SETUP.md).
Create an output directory and select a target preset, mode, and flow:

```sh
mkdir -p out/local
genie cfg/cva5_reuseio.yml cfg/local.yml \
  --flow ISSEvaluationFlow -c BENCH=embench_iot/crc32 \
  --design-dir "$(pwd)/out/local"
```

The local setup requires the external source/tool installations and Memgraph
server. Select a target-specific query YAML with `ISAAC_QUERY_CONFIG_YAML`;
see [MIGRATION.md](MIGRATION.md) for CVA5 constraints and database routing.
The complete hardware flow additionally requires an HLS installation, cell
library, and synthesis technology/tool configuration.

Run only configuration verification without external tools:

```sh
genie cfg/cva5_reuseio.yml cfg/local.yml \
  --flow ISSEvaluationFlow -c BENCH=embench_iot/crc32 \
  --design-dir "$(pwd)/out/local" --only Misc.VerifyConfig
```

Resume a range of steps with saved GenIE state:

```sh
genie cfg/cva5_reuseio.yml cfg/local.yml \
  --flow ISSEvaluationFlow -c BENCH=embench_iot/crc32 \
  --design-dir "$(pwd)/out/local" --with-initial-state /path/to/state_out.json \
  --from ISAAC.CreateSession --to ISAAC.PickChoices
```

List or run an individual Python counterpart of a prototype phase:

```sh
python -m genie.prototype --list
python -m genie.prototype flow_filter.sh --stage filtered \
  cfg/cva5_reuseio.yml --design-dir "$(pwd)/out/local" \
  --with-initial-state /path/to/state_out.json
```

See [FLOWS.md](FLOWS.md), [CONFIG.md](CONFIG.md), [MODES.md](MODES.md), and
[PROGRESS.md](../PROGRESS.md) for current capabilities and validation limits.
