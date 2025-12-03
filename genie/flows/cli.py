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
from functools import partial

from cloup import (
    option,
    argument,
    option_group,
    Choice,
    Path,
)
from cloup.constraints import (
    mutually_exclusive,
)
from cloup.typing import Decorator

from openlane.flows.cli import (
    set_log_level_cb,
    set_worker_count_cb,
    initial_state_cb,
    only_cb,
    from_to_cb,
    condensed_cb,
    progressbar_cb,
)

from .flow import GenIEFlow
from ..common import cli, _get_process_limit
from ..logging import LogLevels


def cloup_flow_opts(
    *,
    config_options: bool = True,
    run_options: bool = True,
    sequential_flow_controls: bool = True,
    sequential_flow_reproducible: bool = False,
    log_level: bool = True,
    jobs: bool = True,
    accept_config_files: bool = True,
    _enable_debug_flags: bool = False,
    enable_overwrite_flag: bool = False,
    enable_initial_state_element: bool = False,
) -> Decorator:
    """
    Creates a wrapper that appends a number of GenIE flow-related flags to a
    function decorated with @cloup.command (https://cloup.readthedocs.io/en/stable/autoapi/cloup/index.html#cloup.command).

    The following keyword arguments will be passed to the decorated function.
    * Those postfixed ‡ are compatible with the constructor for :class:`Flow`.
    * Those postfixed § are compatible with the :meth:`Flow.start`.

    * Flow configuration options (if parameter ``config_options`` is ``True``):
        * ``flow_name``: ``Optional[str]``: A valid flow ID to be used with :meth:`Flow.factory.get`
        * ``config_override_strings``‡: ``Optional[Iterable[str]]``
    * Sequential flow controls (if parameter ``sequential_flow_controls`` is ``True``)
        * ``frm``§: ``Optional[str]``: Start from a step with this ID. Supported by sequential flows.
        * ``to``§: ``Optional[str]``: Stop at a step with this id. Supported by sequential flows.
        * ``skip``§: ``Iterable[str]``: Skip these steps. Supported by sequential flows.
    * Sequential flow reproducible (if parameter ``sequential_flow_reproducible`` is ``True``)
        * ``reproducible``§: ``str``: Create a reproducible for a step with is ID, aborting the flow afterwards. Supported by sequential flows.
    * Flow run options (if parameter ``run_options`` is ``True``):
        * ``tag``§: ``Optional[str]``
        * ``last_run``§: ``bool``: If ``True``, ``tag`` is guaranteed to be None.
        * ``with_initial_state``§: ``Optional[State]``
    * ``config_files``: ``Iterable[str]``: Paths to configuration files (if
      parameter  ``accept_config_files`` is ``True``)

    :param config_options: Enables flow configuration and starting CLI flags
    :param sequential_flow_controls: Enables flow control CLI flags
    :param flow_run_options: Enables tag CLI flags
    :param log_level: Enables ``--log-level`` CLI flag
    :param jobs: Enables ``-j/--jobs`` CLI flag
    :param accept_config_files: Accepts configuration file paths as CLI arguments
    :returns: The wrapper
    """
    o = partial(option, show_default=True)

    def decorate(f):
        if config_options:
            f = option_group(
                "Flow configuration options",
                o(
                    "-f",
                    "--flow",
                    "flow_name",
                    type=Choice(GenIEFlow.factory.list(), case_sensitive=False),
                    default=None,
                    help="The built-in GenIE flow to use for this run",
                ),
                o(
                    "-c",
                    "--override-config",
                    "config_override_strings",
                    type=str,
                    multiple=True,
                    help="For this run only- override a configuration variable with a certain value. In the format KEY=VALUE. Can be specified multiple times. Values must be valid JSON values, and keys must not use their deprecated names.",
                ),
            )(f)
        if run_options:
            f = o(
                "-i",
                "--with-initial-state",
                type=Path(
                    exists=True,
                    file_okay=True,
                    dir_okay=False,
                ),
                default=None,
                callback=initial_state_cb,
                help="Use this JSON file as an initial state. If this is not specified, the latest `state_out.json` of the run directory will be used. If none exist, an empty initial state is created.",
            )(f)
            f = o(
                "--design-dir",
                "design_dir",
                type=Path(
                    exists=True,
                    file_okay=False,
                    dir_okay=True,
                ),
                default=None,
                help="The top-level directory for your design that configuration objects may resolve paths relative to.",
            )(f)
            if enable_overwrite_flag:
                f = o(
                    "--overwrite",
                    is_flag=True,
                    default=False,
                    help="Overwrite run, if exists.",
                )(f)
            if _enable_debug_flags:
                f = option_group(
                    "Debug flags",
                    o(
                        "--force-run-dir",
                        "_force_run_dir",
                        type=Path(
                            exists=True,
                            file_okay=False,
                            dir_okay=True,
                        ),
                        hidden=True,
                        default=None,
                    ),
                )(f)
            f = option_group(
                "Run options",
                o(
                    "--run-tag",
                    "tag",
                    default=None,
                    type=str,
                    help="An optional name to use for this particular run of an GenIE-based flow. Used to create the run directory.",
                ),
                o(
                    "--last-run",
                    is_flag=True,
                    default=False,
                    help="Use the last run as the run tag.",
                ),
                constraint=mutually_exclusive,
            )(f)
        if sequential_flow_controls:
            f = option_group(
                "Sequential flow controls",
                o(
                    "-F",
                    "--from",
                    "frm",
                    type=str,
                    default=None,
                    callback=from_to_cb,
                    help="Start from a step with this id. Supported by sequential flows.",
                ),
                o(
                    "-T",
                    "--to",
                    type=str,
                    default=None,
                    callback=from_to_cb,
                    help="Stop at a step with this id. Supported by sequential flows.",
                ),
                o(
                    "--only",
                    type=str,
                    default=None,
                    expose_value=False,
                    is_eager=True,
                    callback=only_cb,
                    help="Shorthand to set both --from and --to to the same value. Overrides the values from both.",
                ),
                o(
                    "-S",
                    "--skip",
                    type=str,
                    multiple=True,
                    help="Skip these steps. Supported by sequential flows.",
                ),
            )(f)
        if sequential_flow_reproducible:
            f = o(
                "--reproducible",
                type=str,
                help="Create a reproducible for the step matching this ID, then abort the flow. Supported by sequential flows.",
            )(f)
        if log_level:
            f = o(
                "--log-level",
                type=cli.IntEnumChoice(LogLevels),
                default=None,
                help="A logging level. Set to VERBOSE or higher to silence subprocess logs. [default: unchanged from SUBPROCESS]",
                callback=set_log_level_cb,
                expose_value=False,
                show_default=False,
            )(f)
            f = o(
                "--show-progress-bar/--hide-progress-bar",
                type=bool,
                help="Whether to show the progress bar when running Flows. [default: show]",
                default=None,
                callback=progressbar_cb,
                expose_value=False,
            )(f)
            f = o(
                "--condensed/--full",
                type=bool,
                help="In condensed mode, subprocess logs are suppressed regardless of step, --hide-progress-bar is the default, and the log messages themselves are a bit more terse. Useful for debugging.",
                default=False,
                is_eager=True,
                callback=condensed_cb,
                expose_value=False,
            )(f)
        if jobs:
            f = o(
                "-j",
                "--jobs",
                type=int,
                default=_get_process_limit(),
                help="The maximum number of threads or processes that can be used by GenIE.",
                callback=set_worker_count_cb,
                expose_value=False,
            )(f)
        if enable_initial_state_element:
            f = o(
                "-e",
                "--initial-state-element-override",
                type=str,
                multiple=True,
                default=(),
                help="Elements to override in the used initial state in the format DESIGN_FORMAT_ID=PATH",
            )(f)
        if accept_config_files:
            f = argument(
                "config_files",
                nargs=-1,
                type=Path(
                    exists=True,
                    file_okay=True,
                    dir_okay=True,
                ),
            )(f)
        return f

    return decorate
