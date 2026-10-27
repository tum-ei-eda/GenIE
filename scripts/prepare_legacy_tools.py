#!/usr/bin/env python3
"""Prepare isolated compatibility copies for older prototype dependencies.

The original checkouts/environment are read-only inputs. Output includes a state
path override for Seal5 and a PYTHONPATH overlay for the plotting dependency.
"""
import argparse
import json
from pathlib import Path
import shutil


def patched_copy(source, destination, relative_file, before, after):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents:
        raise ValueError("Compatibility output must be outside the source dependency")
    content = (source / relative_file).read_text()
    if before not in content and after not in content:
        raise ValueError(f"Unsupported dependency source: expected pattern absent in {source / relative_file}")
    if destination.exists():
        raise FileExistsError(f"Use a fresh output directory: {destination}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
    (destination / relative_file).write_text(content.replace(before, after))
    return destination


def prepare(seal5_source, logistro_source, output):
    output = Path(output).resolve()
    seal5 = patched_copy(seal5_source, output / 'seal5', 'seal5/tools/llvm.py',
        'repo.create_tag(f"seal5-{label}-base", "-f")',
        'repo.create_tag(f"seal5-{label}-base", force=True)')
    patched_copy(logistro_source, output / 'compat/logistro', '_args.py',
        'argparse.ArgumentParser(add_help=False)',
        'argparse.ArgumentParser(add_help=False, allow_abbrev=False)')
    result = {'paths': {'seal5.src_dir': str(seal5)}, 'environment': {'PYTHONPATH': str(output / 'compat')}}
    (output / 'compatibility.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal5-source', type=Path, required=True)
    parser.add_argument('--logistro-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.seal5_source, args.logistro_source, args.output), indent=2))


if __name__ == '__main__':
    main()
