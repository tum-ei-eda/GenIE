## GenIE Command Line Interface

See `genie --help` for full details.

### Examples flags

Here are some relevant arguments:

```sh
# Containerization options
--docker-mount
--docker-tty
--docker-no-tty
--dockerized

# Sequential flow controls
--from MLonMCU.Bench  # Start flow at specific step
--to MLonMCU.Bench  # Stop flow at specific step
--only MLonMCU.Bench  # Only execute a specific step
--skip MLonMCU.Bench  # Skip a specific step

# Run options
--run-tag foo  # Override auto-generated run tag
--last-run  # Use the last run as the run tag

# Flow configuration options
--flow [DefaultGenIEFlow|RTLGenIEFlow|PerfSimGenIEFlow]
-c FOO=bar  # Override configs vars

# Logging options 
--condensed
--full
--show-progress-bar
--hide-progress-bar
--log-level [ALL or 0|DEBUG or 10|SUBPROCESS or 12|VERBOSE or 15|INFO or 20|WARNING or 30|ERROR or 40|CRITICAL or 50]

# Other options
--overwrite  # Overwrite run, if exists.
--design-dir DIRECTORY  # The top-level design directory
--with-initial-state FILE   # Use this JSON file as an initial state instead of latest `state_out.json`
```