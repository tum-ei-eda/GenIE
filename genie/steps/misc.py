from time import sleep
from typing import Tuple

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate
from genie.state import State

from .utils import check_program


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
        required_commands = []
        fail_on_err = True
        command2package = {"pdfunite": "poppler-utils", "dot": "graphviz", "ninja": "ninja-build"}
        command2help = {"rustc": "TODO"}
        required_commands += ["cmake", "ninja", "wget", "dot", "pdfunite", "rustc"]
        # TODO: check versions?
        check_docker = True
        if check_docker:
            required_commands += ["docker"]
        check_python3 = True
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
