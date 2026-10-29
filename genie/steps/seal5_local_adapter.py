#!/usr/bin/env python3
"""Preserve explicit GenIE overrides across the toolkit adapter."""
import os
import sys


def main():
    env = os.environ.copy()
    script = env.pop("GENIE_SEAL5_SCRIPT")
    for source, target in (("GENIE_LLVM_REPO", "LLVM_REPO"), ("GENIE_LLVM_REF", "LLVM_REF"),
                           ("GENIE_SEAL5_HOME", "SEAL5_HOME"), ("GENIE_SEAL5_M2ISAR_DIR", "SEAL5_M2ISAR_DIR")):
        value = env.pop(source, None)
        if value is not None:
            env[target] = value
    args = list(sys.argv[1:])
    os.execvpe(script, [script, *args], env)


if __name__ == "__main__":
    main()
