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
import os
import tempfile
from shutil import rmtree
from unittest import mock
from typing import Any, Optional, Iterable, Callable

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher
from _pytest.fixtures import SubRequest

from genie.config import Variable
from genie.common import Path, GenericDict


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, GenericDict) and isinstance(right, GenericDict) and op == "==":
        return_value = ["comparing GenericDict-derived objects"]
        left_d = left.to_raw_dict()
        right_d = right.to_raw_dict()

        for key in set(left_d.keys()).union(right_d.keys()):
            if left_d.get(key) != right_d.get(key):
                return_value.append(
                    f"  * mismatched values for '{key}': {repr(left_d.get(key))} vs. {repr(right_d.get(key))}"
                )
        return return_value


@pytest.fixture
def _mock_conf_fs():
    with Patcher() as patcher:
        rmtree("/run", ignore_errors=True)
        patcher.fs.create_dir("/cwd/src")
        os.chdir("/cwd")
        yield


class chdir(object):
    def __init__(self, path):
        self.path = path
        self.previous = None

    def __enter__(self):
        self.previous = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.previous)
        if exc_type is not None:
            raise exc_value


@pytest.fixture
def _chdir_tmp(request: SubRequest):
    keep_tmp = request.config.getoption("--keep-tmp")

    if not keep_tmp:
        with tempfile.TemporaryDirectory(prefix="genie_test_") as dir, chdir(dir):
            yield
    else:
        dir = tempfile.mkdtemp(prefix="genie_test_")
        with chdir(dir):
            print(f"\nTMP: {dir}")
            yield
            print(f"\nTMP: {dir}")


MOCK_FLOW_VARS = [
    Variable(
        "DESIGN_DIR",
        Path,
        "The directory of the design. Does not need to be provided explicitly.",
    ),
    Variable(
        "DESIGN_NAME",
        str,
        description="x",
    ),
]
COMMON_FLOW_VARS = MOCK_FLOW_VARS


def mock_variables(patch_in_objects: Optional[Iterable[Any]] = None):
    from genie.config import config

    if patch_in_objects is None:
        patch_in_objects = []
    patch_in_objects = patch_in_objects + [config]

    def decorator(f: Callable):
        for o in patch_in_objects:
            if hasattr(o, "flow_common_variables"):
                f = mock.patch.object(
                    o,
                    "flow_common_variables",
                    COMMON_FLOW_VARS,
                )(f)
            if hasattr(o, "removed_variables"):
                f = mock.patch.object(
                    o,
                    "removed_variables",
                    {"REMOVED_VARIABLE": "Variable sucked"},
                )(f)
            if hasattr(o, "universal_flow_config_variables"):
                f = mock.patch.object(
                    o,
                    "universal_flow_config_variables",
                    COMMON_FLOW_VARS,
                )(f)
            if hasattr(o, "all_variables"):
                f = mock.patch.object(
                    o,
                    "all_variables",
                    COMMON_FLOW_VARS,
                )(f)

        return f

    return decorator


@pytest.fixture
@mock_variables()
def mock_config():
    from genie.config import GenIEConfig

    mock_config, _ = GenIEConfig.load(
        {
            "DESIGN_NAME": "whatever",
        },
        COMMON_FLOW_VARS,
        design_dir="/cwd",
    )
    return mock_config


class MockProgress(object):
    def __init__(self, *args, **kwargs):
        self.add_task_called_count = 0
        self.start_called_count = 0
        self.stop_called_count = 0
        self.update_called_count = 0
        self.total = 100
        self.completed = 0
        self.description = "Progress"

    def add_task(self, *args):
        self.add_task_called_count += 1

    def start(self):
        self.start_called_count += 1

    def stop(self):
        self.stop_called_count += 1

    def update(
        self,
        _,
        description: Optional[str] = None,
        total: Optional[int] = None,
        completed: Optional[float] = None,
    ):
        if total_stages := total:
            self.total = total_stages

        if completed_stages := completed:
            self.completed = completed_stages

        if current_task_description := description:
            self.description = current_task_description

        self.update_called_count += 1


@pytest.fixture(autouse=True)
def _mock_progress():
    from genie.flows import flow

    with mock.patch.object(flow, "Progress", MockProgress):
        yield


def pytest_configure():
    pytest.COMMON_FLOW_VARS = COMMON_FLOW_VARS
    pytest.mock_variables = mock_variables


def pytest_addoption(parser):
    parser.addoption("--step-rx", action="store", default="^$")
    parser.addoption("--keep-tmp", action="store_true", default=False)
