# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Sequence, Union, Optional

from .variable import Variable
from ..common import Path


def _prefix_to_wildcard(prefixes_raw: Union[str, Sequence[str]]):
    prefixes = prefixes_raw
    if isinstance(prefixes, str):
        prefixes = prefixes.split()
    return [f"{prefix}*" for prefix in prefixes]


genie_option_variables = [
    # Common
    Variable(
        "DESIGN_DIR",
        Optional[Path],
        "The directory of the design. Should be set via command-line arguments or :meth:`Config.load` flags and not actual configuration files. If using a configuration file, ``DESIGN_DIR`` will be the directory where that file exists.",
        default=".",
    ),
    # Variable(
    #     "DESIGN_NAME",
    #     str,
    #     "The name of the top level module of the design. Must be a valid C identifier, i.e., matches the regular expression `[_a-zA-Z][_a-zA-Z0-9]+`.",
    # ),
    Variable(
        "BENCH",
        str,
        "Name of the Benchmark/Workload",
    ),
]

genie_flow_common_variables = genie_option_variables
