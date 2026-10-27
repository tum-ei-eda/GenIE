#!/usr/bin/env python3
"""Run the prototype's Synopsys Tcl and report parsers with explicit paths."""
import csv
import os
from pathlib import Path
import subprocess
import sys


def run(argv, env=None):
    output, rtl, core, technology, period, *constraints = argv
    output, rtl = Path(output).resolve(), Path(rtl).resolve()
    env = dict(os.environ if env is None else env)
    demo = Path(env["GENIE_DEMO_DIR"])
    top = "cva5_top" if core == "CVA5" else "top"
    constraint = Path(constraints[0]) if constraints else demo / "constraints" / core / f"{top}.sdc"
    tcl = Path(env.get("ASIP_SYN_TCL", str(demo / "syn_nangate.tcl")))
    for path in (rtl / "files.txt", constraint, tcl):
        if not path.is_file():
            raise FileNotFoundError(path)
    log = output / "log"
    gates = output / "out"
    log.mkdir(parents=True, exist_ok=True)
    gates.mkdir(parents=True, exist_ok=True)
    env.update(ROOT_PATH=str(demo), TECHLIB=technology, FILES_TXT=str(rtl / "files.txt"),
               GATE_DIR=str(gates), LOG_DIR=str(log), CLOCK_PERIOD=period,
               CONSTRAINTS_FILE=str(constraint.resolve()), TOPLEVEL=top)
    if "TECHLIB_PATH" not in env:
        raise ValueError("ASIP_SYN_TECHLIB_PATH must identify the synthesis technology libraries")
    with (log / "syn_nangate.log").open("w") as stream:
        subprocess.run(["dc_shell", "-f", str(tcl)], env=env, cwd=output,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    for report in ("report_area_hier.log", "report_timing.log"):
        if not (log / report).is_file():
            raise FileNotFoundError(log / report)
    scripts = demo / "scripts"
    tables = []
    for kind, report in (("area", "report_area_hier.log"), ("timing", "report_timing.log")):
        destination = output / f"{kind}.csv"
        with destination.open("w") as stream:
            subprocess.run([str(scripts / "launch.sh"), "python3", str(scripts / f"parse_{kind}_report.py"), str(log / report)],
                           env=env, cwd=demo, stdout=stream, check=True)
        with destination.open(newline="") as stream:
            tables.append(list(csv.reader(stream)))
    if len(tables[0]) != len(tables[1]):
        raise ValueError("Area and timing report tables have different row counts")
    with (output / "metrics.csv").open("w", newline="") as stream:
        csv.writer(stream).writerows([left + right for left, right in zip(*tables)])


if __name__ == "__main__":
    run(sys.argv[1:])
