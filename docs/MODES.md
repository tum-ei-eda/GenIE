## GenIE Modes

### Local (`local`)

Install via: `pip install "genie[local]"`

Run with: `genie cfg/local.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE Python dependencies use custom venv
- Retargeting jobs are executed locally
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))


### Default (`default`)

Install via: `pip install "genie[default]"`

Run with: `genie cfg/default.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE dependencies share same user venv
- Retargeting jobs are executed locally
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))

### Docker (`docker`)

Install via: `pip install "genie[docker]"`

Run with: `genie cfg/docker.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE dependencies share same user venv
- Retargeting jobs are executed in temporary docker containers (see [`DOCKER.md`](./DOCKER.md))
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))

### Service (`service`)

Install via: `pip install "genie[service]"`

Run with: `genie cfg/service.yml ...`

**Details:**
- GenIE runs in user venv
- GenIE dependencies share same user venv
- Retargeting jobs are executed via Retargeting REST API
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))
- Needs externally hosted Retargeting Service (see [`SERVICE.md`](./SERVICE.md))

### Dockerized (`dockerized`)

Install via: `pip install "genie[dockerized]"`

Run with: `genie --dockerized cfg/dockerized.yml ...`

**Details:**
- GenIE runs in docker temporary container
- GenIE dependencies are pre-installed in container
- Retargeting jobs executed within the container (see [`DOCKER.md`](./DOCKER.md))
- Needs externally managed Memgraph DB Server (see [`MEMGRAPH.md`](./MEMGRAPH.md))

### Custom (`custom`)

Add your own modes, i.e. by modifying `cfg/custom.yml` to run hybrid local/docker jobs.

**Details:**
- See [`CONFIG.md`](./CONFIG.md)