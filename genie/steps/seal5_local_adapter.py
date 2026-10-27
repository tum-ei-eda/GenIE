#!/usr/bin/env python3
"""Preserve explicit GenIE overrides across the legacy toolkit adapter."""
import os
import sys


def main():
    env = os.environ.copy()
    script = env.pop("GENIE_SEAL5_SCRIPT")
    for source, target in (("GENIE_LLVM_REPO", "LLVM_REPO"), ("GENIE_LLVM_REF", "LLVM_REF"), ("GENIE_SEAL5_HOME", "SEAL5_HOME")):
        value = env.pop(source, None)
        if value is not None:
            env[target] = value
    os.execvpe(script, [script, *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
