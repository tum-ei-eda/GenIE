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
import json

import click

from .config import GenIEConfig
from ..flows.flow import universal_genie_flow_config_variables
from ..flows.cli import cloup_flow_opts


@click.group
def cli():
    pass


@click.command()
@click.option(
    "--file-name",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
    default="config.json",
    prompt="Please input the file name for the configuration file",
    help="The file name of the configuration file.",
)
@click.option(
    "--design-dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=".",
    prompt="Enter the base directory for your design",
    help="The top-level design directory. Typically, the configuration file goes in the design directory as well.",
)
@click.option(
    "--design-name",
    "--top-module",
    type=str,
    prompt="Enter the design name (which should be equal to the HDL name of your top module)",
    help="The name of the design, i.e. the name of the top-level module of the design.",
)
@cloup_flow_opts(
    config_options=False,
    run_options=False,
    sequential_flow_controls=False,
    jobs=False,
    accept_config_files=False,
)
def create_config(
    file_name,
    design_name,
    design_dir,
):
    """
    Generates an GenIE JSON configuration file for a design interactively.
    """
    config_dict = {
        "DESIGN_NAME": design_name,
        "meta": {
            "version": 2,
        },
    }
    config, _ = GenIEConfig.load(
        config_dict,
        universal_genie_flow_config_variables,
        design_dir=design_dir,
    )
    with open(file_name, "w") as f:
        print(
            json.dumps(config_dict, cls=config.get_encoder(), indent=4),
            file=f,
        )

    design_dir_opt = ""
    if os.path.abspath(design_dir) != os.path.abspath(os.path.dirname(file_name)):
        design_dir_opt = f"--design-dir {design_dir} "

    print(f"Wrote config to '{file_name}'.")
    print("To run this design, invoke:")
    print(f"\tgenie {design_dir_opt}{file_name}")


cli.add_command(create_config)

if __name__ == "__main__":
    cli()
