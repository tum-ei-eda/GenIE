# CLI flow monitor

The monitor is a small read-only Python web server. There is no frontend build,
new dependency, database, or change to how experiments are configured.

Start your experiment normally, choosing a run tag so its URL can be prepared
before execution:

```sh
python -m genie cfg/cva5_reuseio.yml --run-tag experiment-web
```

In another terminal (using the same Python environment), serve its run directory:

```sh
python -m genie.monitor cfg/runs/experiment-web --port 8765
```

Use the actual run directory reported by GenIE if your configuration changes the
design directory. The server can start before the run directory exists. It waits
for the CLI to create `monitor.json`. Open <http://localhost:8765>.

For a remote experiment machine, forward the port from your laptop:

```sh
ssh -N -L 8765:127.0.0.1:8765 USER@EXPERIMENT_HOST
```

Then open the same localhost URL. Alternatively `--host 0.0.0.0` serves it on the
experiment machine's network interfaces. This exposes experiment logs without
authentication, so use it only on a trusted network. Stop the temporary server
with Ctrl-C; stopping it does not stop the flow. Keep it running after the CLI
finishes to inspect the completed experiment.

The page shows all planned stages, with pending, running, completed, failed, and
skipped states. Logs are collapsed initially. Expand **Live monitor** on a running
stage or **Logs** on a finished stage. Open panels refresh once per second,
showing the last 64 KiB of each top-level stage `.log` file. Full logs open through
the links above the tail. A separate collapsed flow log includes orchestration
messages. Stage errors and flow errors remain visible without expanding logs.

Each new invocation writes atomic `monitor.json` snapshots in its run directory.
The sequential runner records transitions directly; terminal output is not parsed.
`stage.log` captures Python logger messages, while existing tool logs are retained
and flushed after every line. A child tool that buffers its own output still needs
to flush before that output reaches GenIE. The heartbeat refreshes every three
seconds. After fifteen seconds without one the UI reports **unresponsive**;
it does not infer a terminal outcome. Ordinary exceptions and keyboard interrupts
are recorded immediately.

The monitor supports GenIE's existing sequential flows, including custom step
lists, gating, `--skip`, `--from`, and `--to`. Resuming an existing run replaces the
status plan with the current invocation. Previous log directories remain on disk;
the page follows stages executed by the current invocation. Runs made before this
feature have no status snapshot and must be inspected on disk or rerun. Custom
nonsequential flow implementations need equivalent stage hooks.

Verification:

```sh
python -m unittest test.test_monitor -v
```

The tests execute real CLI success, failure, and skip cases; observe subprocess
output before stage completion; and check HTTP status, log tails, and path limits.
