from typing import Tuple

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate
from genie.config import Variable
from genie.state import State


@GenIEStep.factory.register()
class StartMemgraphServer(GenIEStep):
    """
    TODO.
    """

    id = "Docker.StartMemgraphDB"
    name = "Start Memgraph DB Docker"
    long_name = "Start Memgraph DB Docker Container"
    inputs = []
    outputs = []

    config_vars = [
        # TODO: allow connecting to remote Server/DB with custom url and port?
        Variable(
            "MEMGRAPH_IMAGE",
            str,
            "Docker image for memgraph server.",
            default="memgraph/memgraph-platform",
        ),
        Variable(
            "MEMGRAPH_CONTAINER",
            str,
            "Name of docker conatainer.",
            default="memgraph",
        ),
        Variable("USE_MEMGRAPH_DOCKER", bool, "Run Memgraph CDFG in docker container.", default=True),
        # Variable("SKIP_MEMGRAPH_SETUP", bool, "Do not install memgraph db automatically.", default=False),
        Variable("MEMGRAPH_HOST", str, "Hostname or URL of Memgraph Server", default="localhost"),
        Variable("MEMGRAPH_PORT", int, "Port of Memgraph Server", default=7687),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        use_memgraph_docker = config["USE_MEMGRAPH_DOCKER"]
        if not use_memgraph_docker:
            return views_updates, metrics_updates, {}
        memgraph_host = config["MEMGRAPH_HOST"]
        memgraph_on_localhost = memgraph_host in ["localhost", "127.0.0.1"]
        if not memgraph_on_localhost:
            raise ValueError(
                f"Using non-local MEMGRAPH_HOST={memgraph_host} with USE_MEMGRAPH_DOCKER=true is not allowed"
            )
        image = config["MEMGRAPH_IMAGE"]
        name = config["MEMGRAPH_CONTAINER"]
        memgraph_port = config["MEMGRAPH_PORT"]
        # skip_memgraph_setup = config["SKIP_MEMGRAPH_SETUP"]
        # print("image", image)
        # print("name", name)
        import docker

        client = docker.from_env()
        is_existing = False
        is_running = False
        for container in client.containers.list(all=True):
            # print("container", container, dir(container), container.name, container.status)
            if container.name != name:
                continue
            is_existing = True
            if container.status == "running":
                is_running = True
            break

        # print("is_existing", is_existing)
        # print("is_running", is_running)
        if not is_existing:
            client.containers.run(
                image, detach=True, name=name, ports={f"{memgraph_port}": 7687, "7444": 7444, "3000": 3000}
            )
        elif not is_running:
            container.start()
        else:
            pass  # already ok
        # input(">>>")
        # print("frontend", frontend)
        # print("prog", prog)
        # views_updates["frontend"] = frontend
        # views_updates["prog"] = prog

        # input("!")
        # errors_count = 0
        # metrics_updates.update({"design__lint_error__count": errors_count})
        # sleep(5.0)
        return views_updates, metrics_updates, {}
