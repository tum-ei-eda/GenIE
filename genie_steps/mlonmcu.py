from time import sleep
from typing import List, Tuple, Optional, Union

from openlane.steps.step import Step, ViewsUpdate, MetricsUpdate
from openlane.steps.step import GenIEStep
from openlane.config import Variable
from openlane.state import State
from openlane.common import Path


@Step.factory.register()
class Bench(GenIEStep):
    """
    TODO.
    """

    id = "MLonMCU.Bench"
    name = "Run Benchmark"
    long_name = "Run MLonMCU Benchmark"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "BENCH",
            str,
            "The benchmark.",
        ),
        Variable(
            "BACKEND",
            str,
            "TODO.",
            default="none",
        ),
        Variable(
            "LAYOUT",
            str,
            "TODO.",
            default="default",
        ),
        Variable(
            "ENABLE_VEXT",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "VLEN",
            Optional[int],
            "TODO.",
        ),
        Variable(
            "ELEN",
            Optional[int],
            "TODO.",
        ),
        Variable(
            "EMBEDDED_VEXT",
            bool,
            "TODO.",
            default=False,
        ),
        # TODO: share common (target) vars
        Variable(
            "TARGET",
            str,
            "TODO.",
            default="etiss_rv32",
        ),
        Variable(
            "FPU",
            str,
            "TODO.",
            default="default",
        ),
        Variable(
            "ARCH",
            str,
            "TODO.",
            default="rv32imfd",
        ),
        Variable(
            "ABI",
            str,
            "TODO.",
            default="ilp32d",
        ),
        Variable(
            "TARGET",
            str,
            "TODO.",
            default="etiss_rv32",
        ),
        Variable(
            "OPTIMIZE",
            Union[int, str],
            "TODO.",
            default="3",
        ),
        Variable(
            "UNROLL",
            Union[str, int],
            "TODO.",
            default=False,
        ),
        Variable(
            "AUTO_VECTORIZE",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "GLOBAL_ISEL",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "USE_MLONMCU_DOCKER",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "USE_MLONMCU_MIN_DOCKER",
            bool,
            "TODO.",
            default=False,
        ),
        Variable(
            "VERBOSE",
            bool,
            "TODO.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates


@Step.factory.register()
class Trace(GenIEStep):
    """
    TODO.
    """

    id = "MLonMCU.Trace"
    name = "Run Trace"
    long_name = "Run MLonMCU Trace"
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
        return views_updates, metrics_updates
