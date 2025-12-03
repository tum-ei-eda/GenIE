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
from typing import Any, Dict, List, Mapping, Optional

from openlane.config.preprocessor import process_config_dict, extract_process_vars


def preprocess_dict(
    config_dict: Mapping[str, Any],
    design_dir: str,
    only_extract_process_info: bool = False,
    # pdk: Optional[str] = None,
    # pdkpath: Optional[str] = None,
    # scl: Optional[str] = None,
    readable_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    If readable_paths are set to None, refg:: will not work
    """
    # if None in (pdk, pdkpath, scl):
    #     if only_extract_process_info:
    #         pdkpath = ""
    #         scl = ""
    #         pdk = ""
    #     else:
    #         raise TypeError(
    #             "pdk, pdkpath and scl all need to be non-None unless only_extract_process_info is passed"
    #         )

    base_vars = {
        # Keys.pdk: pdk,
        # Keys.pdkpath: pdkpath,
        # Keys.scl: scl,
        # Keys.design_dir: design_dir,
    }

    preprocessed = process_config_dict(
        config_dict,
        base_vars,
        readable_paths,
    )
    if only_extract_process_info:
        preprocessed = extract_process_vars(preprocessed)

    return preprocessed
