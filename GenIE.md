# GenIE

## Usage

Example commands:

```sh

python3 custom_script.py cfg/cva5_reuseio.yml --flow MyFlow -c BENCH=embench-iot/crc32 --to MLonMCU.Bench
python3 custom_script.py cfg/cva5_reuseio.yml --flow MyFlow -c BENCH=embench-iot/crc32 -c DEMO_DIR=/work/git/openlane_genie_flow/runs/RUN_2025-12-01_12-50-35/demo -c VENV_DIR=/work/git/openlane_genie_flow/runs/RUN_2025-12-01_12-50-35/demo/venv -c MEMGRAPH_CONTAINER=memgraph --to MLonMCU.Bench
```
