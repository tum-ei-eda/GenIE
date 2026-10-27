#!/usr/bin/env python3
"""Installed next to a service ETISS helper to run it in a compatible image."""
import configparser
import json
import os
from pathlib import Path
import sys


def runtime_command(helper, arguments, cwd):
    helper, cwd = Path(helper).resolve(), Path(cwd).resolve()
    config = json.loads(helper.with_name("genie_runtime.json").read_text())
    install = helper.parent.parent
    direct = helper.name == "genie_etiss_processor.py"
    mounts = {install: "ro", cwd: "rw"}
    for argument in arguments:
        candidate = argument[2:] if argument.startswith("-i/") else argument
        if argument.startswith("--") and "=" in argument:
            candidate = argument.split("=", 1)[1]
        if candidate.startswith("/"):
            path = Path(candidate).resolve()
            if path.exists() and path not in mounts:
                mounts[path] = "ro"
            if direct and argument.startswith("-i/") and path.is_file():
                ini = configparser.ConfigParser(interpolation=None, strict=False)
                ini.read(path)
                for section in ini.sections():
                    for key, value in ini.items(section):
                        if key in ("vp.elf_file", "vp.sw_binary_ram", "vp.sw_binary_rom"):
                            binary = Path(value)
                            if binary.is_absolute() and binary.is_file() and binary not in mounts:
                                mounts[binary] = "ro"
    command = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
               "--env", "HOME=/tmp", "--workdir", str(cwd), "--entrypoint",
               str(install / "bin/bare_etiss_processor") if direct else "/bin/bash"]
    if direct:
        command += ["--env", f"LD_LIBRARY_PATH={install / 'lib'}:{install / 'lib64'}"]
    for path, mode in sorted(mounts.items()):
        if ":" in str(path):
            raise ValueError("Docker runtime mount paths cannot contain ':'")
        command += ["--volume", f"{path}:{path}:{mode}"]
    prefix = config.get("install_prefix")
    if prefix and Path(prefix) != install:
        if not Path(prefix).is_absolute() or ":" in prefix or ".." in Path(prefix).parts or prefix == "/":
            raise ValueError("Invalid ETISS runtime install prefix")
        command += ["--volume", f"{install}:{prefix}:ro"]
    launcher = [] if direct else [str(helper.with_name("run_helper.native.sh"))]
    return [*command, config["image"], *launcher, *arguments]


def main():
    command = runtime_command(__file__, sys.argv[1:], Path.cwd())
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
