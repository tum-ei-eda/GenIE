import os
import pathlib
from time import sleep
from typing import Tuple, Optional, Union, Dict

from genie.steps.step import GenIEStep, ViewsUpdate, MetricsUpdate, PathsUpdate
from genie.config import Variable
from genie.state import State
from genie.common import Path

mlonmcu_docker_vars = [
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
        "MLONMCU_IMAGE",
        str,
        "TODO.",
        default="philippvk/isaac-quickstart-mlonmcu:latest",
    ),
    Variable(
        "MLONMCU_MIN_IMAGE",
        str,
        "TODO.",
        default="philippvk/isaac-quickstart-mlonmcu-min:latest",
    ),
]

ccache_vars = [
    Variable(
        "CCACHE_DIR",
        Optional[Path],
        "Existing ccache directory.",
    ),
    Variable(
        "ENABLE_CCACHE",
        bool,
        "Existing ccache directory.",
        default=True,
    ),
]
force_refresh_var = Variable(
    "FORCE_REFRESH",
    bool,
    "Update demo dir/repo even if already populated.",
    default=False,
)
