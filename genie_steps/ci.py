from time import sleep
from typing import List, Tuple

from openlane.steps.step import Step, ViewsUpdate, MetricsUpdate
from openlane.steps.step import GenIEStep
from openlane.config import Variable
from openlane.state import State
from openlane.common import Path


@Step.factory.register()
class PrepareUploads(GenIEStep):
    """
    TODO.
    """

    id = "CI.PrepareUploads"
    name = "Prepare Uploads"
    long_name = "Prepare CI Uploads"
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


@Step.factory.register()
class CreateSummary(GenIEStep):
    """
    TODO.
    """

    id = "CI.CreateSummary"
    name = "Create Summary"
    long_name = "Create CI Summary"
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

