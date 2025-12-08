from time import sleep
from typing import Tuple

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate
from genie.config import Variable
from genie.state import State

from .utils import check_program
from .common_vars import mlonmcu_docker_vars, ccache_vars


@GenIEStep.factory.register()
class VerifyConfig(GenIEStep):
    """
    TODO.
    """

    id = "Misc.VerifyConfig"
    name = "Verify Config"
    long_name = "Verify Config"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        # print("self", self, dir(self))
        # print("step_dir", self.step_dir)
        # print("config", config)
        # print("state_in", state_in)
        bench = config.get("BENCH")
        # print("bench", bench)
        assert bench is not None, "BENCH undefined"
        assert "/" in bench, "BENCH needs explicit frontend prefix"
        frontend, prog = bench.split("/", 1)
        # print("frontend", frontend)
        # print("prog", prog)
        # views_updates["frontend"] = frontend
        # views_updates["prog"] = prog

        # input("!")
        # errors_count = 0
        # metrics_updates.update({"design__lint_error__count": errors_count})
        # sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CheckDeps(GenIEStep):
    """
    TODO.
    """

    id = "Misc.CheckDeps"
    name = "CheckDeps"
    long_name = "Check Dependencies"
    inputs = []
    outputs = []

    config_vars = [
        Variable("USE_MEMGRAPH_DOCKER", bool, "Run Memgraph CDFG in docker container.", default=True),
        *mlonmcu_docker_vars,
        *ccache_vars,
        Variable("USE_ETISS_DOCKER", bool, "Run M2-ISA-R in docker container.", default=False),
        Variable("USE_SEAL5_DOCKER", bool, "Run Seal5 in docker container.", default=False),
        Variable("USE_HLS_DOCKER", bool, "Run HLS tools in docker container.", default=False),
        Variable("SKIP_MEMGRAPH_SETUP", bool, "Do not install memgraph db automatically.", default=False),
        Variable("MEMGRAPH_HOST", str, "Hostname or URL of Memgraph Server", default="localhost"),
        # Variable("MEMGRAPH_PORT", int, "Port of Memgraph Server", default=7687),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        required_commands = []
        fail_on_err = True
        config = self.config
        check_ccache = config["ENABLE_CCACHE"]
        command2package = {"pdfunite": "poppler-utils", "dot": "graphviz", "ninja": "ninja-build"}
        command2help = {"rustc": "curl https://sh.rustup.rs -sSf | sh"}
        required_commands += ["cmake", "ninja", "wget", "dot", "pdfunite", "rustc"]
        # TODO: check versions?
        use_memgraph_docker = config["USE_MEMGRAPH_DOCKER"]
        use_mlonmcu_docker = config["USE_MLONMCU_DOCKER"]
        use_etiss_docker = config["USE_ETISS_DOCKER"]
        use_seal5_docker = config["USE_SEAL5_DOCKER"]
        use_hls_docker = config["USE_HLS_DOCKER"]
        use_docker_list = [
            use_memgraph_docker,
            use_mlonmcu_docker,
            use_etiss_docker,
            use_seal5_docker,
            use_hls_docker,
        ]
        check_docker = any(use_docker_list)
        if check_ccache:
            required_commands += ["ccache"]
        if check_docker:
            required_commands += ["docker"]
        memgraph_host = config["MEMGRAPH_HOST"]
        skip_memgraph_setup = config["SKIP_MEMGRAPH_SETUP"]
        memgraph_on_localhost = memgraph_host not in ["localhost", "127.0.0.1"]
        check_memgraph = not use_memgraph_docker and memgraph_on_localhost and not skip_memgraph_setup
        if check_memgraph:
            required_commands += ["mgconsole"]
        check_python3 = True
        # TODO: check python version!
        if check_python3:
            required_commands += ["python3"]
        for command in required_commands:
            package = command2package.get(command) or command2help.get(command) or command
            check_program(command, allow_none=not fail_on_err, package=package)
        # config = self.config
        # errors_count = 0
        # metrics_updates.update({"design__lint_error__count": errors_count})
        # sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CheckMemgraph(GenIEStep):
    """
    TODO.
    """

    id = "Misc.CheckMemgraph"
    name = "CheckMemgraph"
    long_name = "Check Memgraph DB"
    inputs = []
    outputs = []

    config_vars = [
        Variable("SKIP_MEMGRAPH_CHECK", bool, "Do not check if CDFG is available.", default=False),
        Variable("MEMGRAPH_HOST", str, "Hostname or URL of Memgraph Server", default="localhost"),
        Variable("MEMGRAPH_PORT", int, "Port of Memgraph Server", default=7687),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        skip_memgraph_check = config["SKIP_MEMGRAPH_CHECK"]
        if skip_memgraph_check:
            return views_updates, metrics_updates, {}

        def check_port(host, port):
            # Source - https://stackoverflow.com/a
            # Posted by mrjandro, modified by community. See post 'Timeline' for change history
            # Retrieved 2025-12-03, License - CC BY-SA 4.0
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
            return False

        memgraph_host = config["MEMGRAPH_HOST"]
        memgraph_port = config["MEMGRAPH_PORT"]
        assert check_port(
            memgraph_host, memgraph_port
        ), f"Memgraph DB is not reachable via {memgraph_host}:{memgraph_port}. Please install/start Memgraph Server or set SKIP_MEMGRAPH_CHECK=true"
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class FixPermissions(GenIEStep):
    """
    TODO.
    """

    id = "Misc.FixPermissions"
    name = "Fix Permissions"
    long_name = "Fix Permissions"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}


@GenIEStep.factory.register()
class CleanupTempFiles(GenIEStep):
    """
    TODO.
    """

    id = "Misc.CleanupTempFiles"
    name = "Cleanup Temporary Files"
    long_name = "Cleanup Temporary Files"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates, {}
