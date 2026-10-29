# Memgraph setup

GenIE uploads LLVM CDFGs and queries instruction candidates over Memgraph's
Bolt endpoint. The default is `localhost:7687`.

## Docker

The normal platform startup command is:

```sh
docker run -p 7687:7687 -p 7444:7444 -p 3000:3000 \
  --name memgraph memgraph/memgraph-platform
```

This runs in the foreground. Add `-d` to detach. GenIE needs port 7687; the
other exposed ports are supplied by the platform image for its accompanying
services. GenIE's Docker setup step uses the same image and container name,
and starts or reuses that container. It publishes only the Bolt port.

To manage the database yourself, use:

```yaml
USE_MEMGRAPH_DOCKER: false
SKIP_MEMGRAPH_SETUP: true
MEMGRAPH_HOST: localhost
MEMGRAPH_PORT: 7687
```

The platform image's entrypoint is `supervisord`. Its Memgraph program runs
through `runuser -u memgraph` with working directory `/usr/lib/memgraph`.
Keep this entrypoint for normal operation. During migration validation,
launching the binary directly as root aborted with `SIGABRT` (exit 134).
Controlled checks reproduced the root-user failure; the `memgraph` user
remained running. The normal command above was not the cause of that failure.

For a separate, temporary validation database, choose a different container
name and host port. Do not reuse the production endpoint for tests that purge
the graph. The migration validation used its own container without existing
data volumes.

## Remote or native installation

Point `MEMGRAPH_HOST` and `MEMGRAPH_PORT` at the running database and set
`USE_MEMGRAPH_DOCKER: false`. Set `SKIP_MEMGRAPH_SETUP: true` to use an existing
installation. Leaving it false lets `Setup.SetupMemgraph` invoke the pinned
demo's native setup script.

The compiler's CDFG exporter also needs `libmgclient`. `Setup.SetupMgclient`
publishes its directory as `mgclient.lib_dir`; GenIE forwards that directory
when invoking the exporter and CFU firmware compiler.

## Diagnosing connection failures

Check the intended container, rather than assuming a successful `docker run -d`
means the database stayed running:

```sh
docker ps -a --filter name=memgraph
docker logs memgraph --tail 50
docker port memgraph 7687
```

A connection refusal can mean the container exited or the configured host port
is wrong. A host-port allocation error means another listener already owns
that port; use the existing intended database or choose a different port for
the new instance. GenIE does not replace that listener.

`ISAAC_PURGE_CDFG_DB` defaults to false. When enabled, purge checks that the
persisted session endpoint matches the configured endpoint before proceeding.
