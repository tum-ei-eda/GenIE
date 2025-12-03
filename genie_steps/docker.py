import shutil
import pathlib
from time import sleep
from typing import List, Tuple, Optional

from openlane.steps.step import Step, ViewsUpdate, MetricsUpdate
from openlane.steps.step import GenIEStep
from openlane.config import Variable
from openlane.state import State
from openlane.common import Path


@Step.factory.register()
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
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        image = config["MEMGRAPH_IMAGE"]
        name = config["MEMGRAPH_CONTAINER"]
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
            client.containers.run(image, detach=True, name=name, ports={"7687": 7687, "7444": 7444, "3000": 3000})
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
