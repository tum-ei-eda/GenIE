## GenIE Outputs

### Base directory

Use `-c DESIGN_DIR=$(pwd)/path/to/out` on the `genie` command line to configure the base directory for all generated outputs and temporary files.

### Directory structure

Relative to `DESIGN_DIR`, GenIE will emit one directory for each "Run" containing the timestamp when the run was started:

```sh
# $(pwd)/path/to/out
runs/
  RUN_2025-12-03_15-56-17/
  RUN_2025-12-04_12-22-00/
  ...
```

### Run artifacts

For each run directory the strcuture is as follows:

```sh
# $(pwd)/path/to/out/RUN_2025-12-04_12-22-00
RUN_2025-12-04_12-22-00/
  # step-specific directories
  01-misc-verifyconfig/
  02-misc-checkdeps/
  ...

  # final state
  final/

  # isaac-demo clone dir
  demo/

  # sess/work dirs
  sess/
  
  # logfiles
  error.log
  flow.log
  warning.log

  # resolved global configuration
  resolved.json
```

### Step files

For each step (see [`STEPS.md`](./STEPS.md)), the following files can be emitted

```sh
# $(pwd)/path/to/out/RUN_2025-12-04_12-22-00/01-misc-verifyconfig/
01-misc-verifyconfig/
  config.json
  runtime.txt
  state_in.json
  state_out.json

# $(pwd)/path/to/out/RUN_2025-12-04_12-22-00/64-isaac-generateinstrs
64-isaac-generateinstrs/
  # " see above "
  COMMANDS
  isaac-generateinstrs.log
  isaac-generateinstrs.process_stats.json
```