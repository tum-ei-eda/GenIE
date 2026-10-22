#!/usr/bin/env python3
"""Compare deployed worker scripts with a service checkout without changing either."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


FILES = {
    "llvm": [("worker/llvm/run_retarget.sh", "/scripts/run_retarget.sh"),
             ("worker/llvm/prepare.py", "/scripts/prepare_llvm.py")],
    "combined": [("worker/etiss/retarget.sh", "/scripts/retarget_etiss.sh"),
                 ("worker/etiss_perf/retarget.sh", "/scripts/retarget_etiss_perf.sh"),
                 ("worker/etiss_perf/dispatch.sh", "/scripts/run_retarget.sh")],
    "perf": [("worker/etiss_perf/retarget.sh", "/scripts/retarget_etiss_perf.sh"),
             ("worker/etiss_perf/run_retarget.sh", "/scripts/run_retarget.sh")],
}


def compare_file(source, container, deployed, runner=subprocess.run):
    expected = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    result = runner(["docker", "exec", container, "cat", deployed], capture_output=True)
    actual = hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None
    return {"source": str(source), "container": container, "deployed_path": deployed,
            "source_sha256": expected, "deployed_sha256": actual,
            "error": getattr(result, "stderr", b"").decode(errors="replace")[:500] if result.returncode else None,
            "status": "match" if actual == expected else "different" if actual else "unavailable"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-dir", type=Path, required=True)
    parser.add_argument("--llvm-container")
    parser.add_argument("--combined-container")
    parser.add_argument("--perf-container")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    containers = {role: getattr(args, f"{role}_container") for role in FILES}
    if not any(containers.values()):
        parser.error("Select at least one worker container")
    rows = []
    for role, container in containers.items():
        if container:
            for source, deployed in [*FILES[role], ("worker/worker.py", "/app/worker.py")]:
                rows.append(compare_file(args.service_dir / source, container, deployed))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"files": rows}, indent=2) + "\n")
    print(f"{len(rows)} files checked: " + ", ".join(
        f"{sum(row['status'] == status for row in rows)} {status}"
        for status in ("match", "different", "unavailable")))
    return 0 if all(row["status"] == "match" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
