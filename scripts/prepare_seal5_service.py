#!/usr/bin/env python3
"""Create an isolated retargeting-service build context with pinned upstream dependencies."""
import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INSTALL = r'''#!/bin/bash
set -euo pipefail
export PATH="/work/venv/bin:$PATH"
# The base image can contain editable installs and a different PYTHONPATH.
unset PYTHONPATH
M2ISAR_REF=59ba470011fafe5e814a2b9ca9504d8175fe25cc
SEAL5_REF=b8d5e0932f68547b802fd53b7f4b75ed44a0daf1
git clone https://github.com/tum-ei-eda/M2-ISA-R.git /opt/m2isar
git -C /opt/m2isar checkout "$M2ISAR_REF"
git clone https://github.com/tum-ei-eda/seal5.git /opt/genie-seal5/src
git -C /opt/genie-seal5/src checkout "$SEAL5_REF"
python -m pip install -e /opt/m2isar -e /opt/genie-seal5/src
# Reject an incompatible image baseline during the image build.
PYTHONPATH=/opt/genie-seal5/src:/opt/m2isar python -c 'from pathlib import Path; from seal5.settings import Seal5Settings; Seal5Settings.from_yaml_file(Path("/opt/seal5-baseline.yml"))'
python /opt/genie-seal5/configure_baseline.py
python -m pip check
'''


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"Choose a new build directory: {destination}")
    if source == destination or source in destination.parents:
        raise ValueError("The destination must be outside the source checkout")
    if not (source / "worker/llvm/prepare.py").is_file():
        raise FileNotFoundError(source / "worker/llvm/prepare.py")
    patch = ROOT / "genie/patches/service-seal5-main.patch"
    # Check compatibility before copying or writing anything.
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=source, check=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".venv", "venv", ".env", "jobs"))
    subprocess.run(["git", "apply", str(patch)], cwd=destination, check=True)
    overlay = destination / "worker/seal5-main"
    overlay.mkdir()
    (overlay / "install.sh").write_text(INSTALL)
    shutil.copyfile(ROOT / "scripts/configure_seal5_baseline.py", overlay / "configure_baseline.py")
    print(f"Prepared {destination}")
    print(f"Build: docker compose -f {destination / 'docker-compose.yml'} build worker-llvm")
    print("Existing containers were not changed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Audited isaac-docker-service checkout")
    parser.add_argument("destination", type=Path, help="New isolated build directory")
    args = parser.parse_args()
    prepare(args.source, args.destination)


if __name__ == "__main__":
    main()
