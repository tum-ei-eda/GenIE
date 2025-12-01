from openlane.flows import Flow
from openlane.flows.sequential2 import SequentialFlow2
from openlane.steps import Yosys, Misc, OpenROAD, Magic, Netgen

import os
import re
from time import sleep
from typing import List, Optional, Set, Tuple

from openlane.steps.step import Step, StepException, ViewsUpdate, MetricsUpdate
from openlane.steps.step import GenIEStep
from openlane.config import Variable
from openlane.state import DesignFormat, State
from openlane.common import Path

from genie_steps import Setup, Misc, MLonMCU, ISAAC, CI, Docker


@Step.factory.register()
class MyStep(GenIEStep):
    """
    TODO.
    """

    id = "Flow.MyStep"
    name = "My Step"
    long_name = "My Step: Test"
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
        extra_args = []

        blackboxes = []

        model_list: List[str] = []
        model_set: Set[str] = set()
        config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates


@Flow.factory.register()
class MyFlow(SequentialFlow2):
    Steps = [
        # MyStep,
        Misc.VerifyConfig,
        Misc.CheckDeps,
        Docker.StartMemgraphServer,
        Setup.SetupDemo,
        Setup.SetupPython,
        Setup.SetupCCache,
        Setup.SetupMgclient,
        Setup.SetupLLVM,
        Setup.SetupETISS,
        Setup.SetupMLonMCU,
        # Setup.SetupM2ISAR,
        MLonMCU.Bench,
        MLonMCU.Trace,
        ISAAC.CreateSession,
        ISAAC.LoadArtifacts,
        ISAAC.Analyze,
        ISAAC.Visualize,
        ISAAC.PickChoices,
        ISAAC.PushCDFG,
        ISAAC.QueryCandidates,
        ISAAC.GenerateInstrs,
        # Assign Encoding Metrics/Score
        ISAAC.GenerateETISSCore,
        ISAAC.RetargetLLVM,
        # Assign Seal5 Metrics/Score
        ISAAC.RetargetISS,
        ISAAC.CompareBench,
        ISAAC.CompareBenchOthers,
        ISAAC.CompareBenchPerInstr,
        # Assign Compare
        ISAAC.FilterCandidates,
        ISAAC.CreateSpecGraph,
        # ...
        Misc.FixPermissions,
        CI.CreateSummary,
        CI.PrepareUploads,
        Misc.CleanupTempFiles,
        # MyStep,
    ]
    # ?


# flow = MyFlow(
#     {
#         "PDK": "sky130A",
#         "DESIGN_NAME": "spm",
#         # "VERILOG_FILES": ["./src/spm.v"],
#         "VERILOG_FILES": [],
#         # "CLOCK_PORT": "clk",
#         # "CLOCK_PERIOD": 10,
#     },
#     design_dir=".",
# )
# flow.start()


# from openlane.__main__ import cli
from openlane.__main2__ import cli

if __name__ == "__main__":
    cli()
