# Flow web app

Start the lightweight Python server once, from your GenIE environment:

```sh
python -m genie.monitor --workspace /path/to/GenIE --port 8765
```

Open <http://localhost:8765>. Click **New run**, choose configuration files or paste
a JSON configuration, and press **Start and monitor**. The same page immediately
follows the CLI process and then its stages. There is no frontend build, new
Python dependency, or database.

Configuration files are paths on the experiment machine, relative to the selected
workspace. Add files with the picker or enter one path per line. Their order is
the CLI order; later files overlay earlier values. For example:

```text
cfg/cva5_reuseio.yml
cfg/service.yml
```

An overlay without flow metadata preserves the base config's selected flow.
The form also accepts a JSON object of config overrides, worker count, and optional
from/through/skip stage filters. Pasted JSON uses the workspace as its design
directory. Existing files retain the CLI's usual design-directory handling.

**CLI workers (parallel jobs)** maps to `genie --jobs`: it configures the CLI's
thread-pool workers. Sequential stages remain sequential, and individual tools
may use their own thread/build settings. It is not a number of concurrent runs.

The run selector switches between experiments without opening another page.
Each entry and the selected run heading show the original run timestamp in the
browser's local time. The selected run is retained in the URL for reloads.
Form-created jobs are stored under `.genie-web-runs/` in the workspace, or the
explicit `--runs-dir`. Config submissions, CLI logs, resolved config, states,
status snapshots, and launch metadata remain on disk. A small supervisor records
CLI completion even if the web server stops. Restart with the same workspace and
runs directory to reopen these runs.

## Continue a run

For a finished process with unfinished stages, **Continue run** restarts at the
first failed/interrupted/pending stage. A run stopped with **Through step** can
continue beyond that boundary. Continuation uses the saved resolved configuration
and the input state for that stage (or the preceding completed stage's output).
It preserves earlier completed stages, logs, durations, and files. New stage
attempts receive new directories; CLI output is appended. Total elapsed time is
wall-clock time from the original flow start, including pauses.

Continuation removes the previous from/through boundary, retains skip filters and
worker settings, and retries the unfinished stage from its beginning. It does not
resume a subprocess halfway through. Fixing the experiment's configuration calls
for a new run. A process must have a recorded exit before it can be continued;
a stale heartbeat alone is not enough. Startup failures without a resolved config
or stage plan must be corrected and submitted again. Currently the Continue
button applies to runs created by this app, whose launch metadata it owns.

## Monitor an existing CLI run

CLI invocation remains supported. To attach an existing run at startup:

```sh
python -m genie.monitor /path/to/run --workspace /path/to/GenIE --port 8765
```

Use `--read-only` with a run directory to disable creation and continuation. A
server can attach before the directory exists and wait for its status snapshot.
Runs made before monitoring was added have no snapshot and must be inspected on
disk or rerun. Custom nonsequential flows need equivalent stage hooks.

## Remote access

For a remote experiment machine, forward the port from your laptop:

```sh
ssh -N -L 8765:127.0.0.1:8765 USER@EXPERIMENT_HOST
```

Then open the same localhost URL. `--host 0.0.0.0` serves the app on the experiment
machine's network interfaces. This app has no login: anyone who can reach it can
read experiment files and launch flows with the server account's permissions.
Use localhost/SSH forwarding or a trusted network. POST requests require JSON and
reject cross-origin browser submissions. Stop the server with Ctrl-C; CLI jobs
continue independently.

## Stages, logs, and data

The page shows completed/total steps, a progress bar, total elapsed time, and
per-stage durations. Running timers refresh every second; finished durations stay
fixed. Hours and minutes are shown where applicable. Skipped steps are counted
separately. Older completed stages use their existing `runtime.txt` files.

Stages have consistent numeric positions from the flow plan. Finished stages
appear in reverse order in a collapsible section open by default. Pending stages
appear in execution order in a section closed by default. Active stages remain
above these sections. Whole-card colors indicate stage status. The active stage's
**Live monitor** opens automatically; finished stages' **Logs** remain collapsed.
Manual panel toggles are preserved during refreshes.

Open logs refresh once per second with the last 64 KiB of each stage `.log` file.
Full-log links are available above the tails. **Flow log** also includes CLI output,
so configuration/startup errors are visible before any stage has started.

Expand **Step data** for available `config.json`, `state_in.json`, and
`state_out.json`. **Run data** includes `resolved.json` and any of those files at
run level. The viewer provides expandable JSON, refresh, and raw JSON links.
State files also offer a searchable **Metrics table**, with nested metric objects
flattened into dotted names. A file still being written may require a refresh.

The runner records stage transitions directly in atomic `monitor.json` snapshots;
terminal output is not parsed. `stage.log` captures logger messages and tool logs
flush after each received line. Tools must flush their own buffered output before
GenIE can receive it. Heartbeats refresh every three seconds. Fifteen seconds
without one reports **unresponsive**, without inferring a terminal outcome.

Verification:

```sh
python -m unittest test.test_monitor test.test_web_runs -v
```

These tests cover real CLI success/failure/skip cases, live subprocess output,
HTTP logs and data boundaries, form submission, ordered config overlays, run
switching/persistence, and continuation without rerunning completed stages.
