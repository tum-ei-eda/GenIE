# GenIE Modes

## Local (`local`)

Install via: `pip install "genie[local]"`

Run with: `genie cfg/local.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE Python dependencies use custom venv
- Retargeting jobs are executed locally
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))


## Default (`default`)

Install via: `pip install "genie[default]"`

Run with: `genie cfg/default.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE dependencies share same user venv
- Retargeting jobs are executed locally
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))

## Docker (`docker`)

Install via: `pip install "genie[docker]"`

Run with: `genie cfg/docker.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE dependencies share same user venv
- Retargeting jobs are executed in temporary docker containers (see [`DOCKER.md`](./DOCKER.md))
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))

## Service (`service`)

Use `cfg/service.yml` for LLVM/ETISS retargeting through an external job API.
Set `SERVICE_URL` and `SEAL5_SERVICE_CONFIG` for your workers. The adapter has
transport/artifact tests and real single-set LLVM/ETISS workload validation.
PerfSim service execution uses a separate opt-in switch and saved HLS outputs.
See [SERVICE.md](SERVICE.md).

## Dockerized (`dockerized`)

Install via: `pip install "genie[dockerized]"`

Run with: `genie --dockerized cfg/dockerized.yml ...`

**Details:**
- GenIE runs in docker temporary container
- GenIE dependencies are pre-installed in container
- Retargeting jobs executed within the container (see [`DOCKER.md`](./DOCKER.md))
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))

## Custom (`custom`)

Add your own modes, i.e. by modifying `cfg/custom.yml` to run hybrid local/docker jobs.

**Details:**
- See [`CONFIG.md`](./CONFIG.md)
