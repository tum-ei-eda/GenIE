"""Bridge remote retargeting artifacts into stage-specific GenIE state."""
import hashlib
import json
import os
from pathlib import Path
import gzip
import tarfile
import re

import pandas as pd
import yaml

from genie.config import Variable
from genie.retargeting_service import RetargetingService, ServiceJob, extract_artifact


service_vars = [
    Variable("SERVICE_URL", str, "Retargeting API URL.", default="http://localhost:8080"),
    Variable("SERVICE_TIMEOUT", float, "Maximum job observation time in seconds.", default=3600.0),
    Variable("SERVICE_POLL_INTERVAL", float, "Job observation interval in seconds.", default=5.0),
    Variable("SEAL5_SERVICE_CONFIG", str, "Worker-compatible Seal5 YAML configuration.", default=""),
    Variable("SEAL5_SERVICE_TAG", str, "LLVM worker tag.", default="llvm"),
    Variable("ETISS_SERVICE_TAG", str, "ETISS worker tag.", default="etiss"),
    Variable("ETISS_PERF_SERVICE_TAG", str, "PerfSim worker tag.", default="etiss_perf"),
    Variable("ETISS_SERVICE_RUNTIME_IMAGE", str, "Optional compatible image for downloaded simulator execution.", default=""),
    Variable("SERVICE_BUNDLE_COREDSL", bool, "Inline local CoreDSL imports for service source parity.", default=True),
    Variable("SERVICE_KEEP_ARCHIVE", bool, "Retain the downloaded transfer archive after successful validation.", default=False),
]


def bundle_coredsl(source):
    """Inline one or more descriptions, deduplicating their shared imports."""
    seen, active, manifest = set(), set(), {}
    imports = re.compile(r'/\*.*?\*/|//[^\n]*|^[ \t]*import[ \t]+"([^"\n]+)"[ \t]*;?[ \t]*(?://[^\n]*)?$',
                         re.MULTILINE | re.DOTALL)
    def visit(path):
        path = Path(path).resolve()
        if path in active:
            raise ValueError(f"Cyclic CoreDSL import: {path}")
        if path in seen:
            return ""
        text = path.read_text()
        manifest[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        active.add(path)
        def replace(match):
            if match[1] is None:
                return match[0]
            imported = Path(match[1])
            return visit(imported if imported.is_absolute() else path.parent / imported)
        text = imports.sub(replace, text)
        active.remove(path)
        seen.add(path)
        return f"// Inlined {path.name}\n{text}\n"
    sources = [source] if isinstance(source, (str, Path)) else list(source)
    if not sources:
        raise ValueError("At least one CoreDSL description is required")
    return "".join(visit(path) for path in sources), manifest


def relocate_etiss_helper(install):
    """Remove the worker's baked-in install prefix from ETISS's launcher."""
    helper = Path(install) / "bin/run_helper.sh"
    if helper.with_name("run_helper.native.sh").is_file():
        helper = helper.with_name("run_helper.native.sh")
    original = helper.read_text()
    replacement = 'ETISS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"'
    relocated, count = re.subn(r"(?m)^ETISS_DIR=.*$", lambda _: replacement, original)
    if count != 1:
        raise ValueError("Expected one ETISS_DIR assignment in service run_helper.sh")
    helper.write_text(relocated)


def configure_etiss_runtime(install, image):
    helper = Path(install) / "bin/run_helper.sh"
    native = helper.with_name("run_helper.native.sh")
    settings = helper.with_name("genie_runtime.json")
    processor_wrapper = helper.with_name("genie_etiss_processor.py")
    if image:
        if not native.exists():
            helper.rename(native)
        helper.write_text(Path(__file__).with_name("etiss_runtime.py").read_text())
        helper.chmod(native.stat().st_mode | 0o100)
        runtime_config = {"image": image}
        header = Path(install) / "include/etiss/config.h"
        if header.is_file():
            match = re.search(r'^#define ETISS_INSTALL_DIR "([^"]+)"', header.read_text(), re.MULTILINE)
            if match:
                prefix = Path(match[1])
                if not prefix.is_absolute() or ".." in prefix.parts or prefix == Path("/"):
                    raise ValueError("Invalid ETISS worker install prefix")
                runtime_config["install_prefix"] = str(prefix)
        settings.write_text(json.dumps(runtime_config))
        if helper.with_name("bare_etiss_processor").is_file():
            processor_wrapper.write_text(Path(__file__).with_name("etiss_runtime.py").read_text())
            processor_wrapper.chmod(0o755)
    elif native.exists():
        native.replace(helper)
        settings.unlink(missing_ok=True)
        processor_wrapper.unlink(missing_ok=True)


def extract_etiss_source(destination, name="etiss_perf"):
    """Publish the source tree MLonMCU uses for its ETISS metrics script."""
    import tempfile
    import shutil
    destination = Path(destination)
    source = destination / f"{name}_source"
    metrics = Path("src/bare_etiss_processor/get_metrics.py")
    if not source.exists():
        archive = destination / f"{name}_source.tar.gz"
        with tempfile.TemporaryDirectory(dir=destination) as temporary:
            unpacked = Path(temporary) / "source"
            unpacked.mkdir()
            with tarfile.open(archive, "r:gz") as archive_file:
                archive_file.extractall(unpacked, filter="data")
            if not (unpacked / metrics).is_file():
                raise FileNotFoundError(unpacked / metrics)
            shutil.move(str(unpacked), source)
    if not (source / metrics).is_file():
        raise FileNotFoundError(source / metrics)
    return source


def package_hls(source, archive):
    """Package the HLS directory layout unchanged, without links or timestamps."""
    source, archive = Path(source), Path(archive)
    if not source.is_dir():
        raise FileNotFoundError(source)
    # Match the worker's file/directory-only upload contract.
    entries = sorted(source.rglob("*"))
    if any(path.is_symlink() or not (path.is_file() or path.is_dir()) for path in entries):
        raise ValueError("Service HLS uploads require regular files/directories, without links")
    if not entries:
        raise ValueError("Service HLS directory is empty")
    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as output:
                for path in entries:
                    info = output.gettarinfo(str(path), arcname=str(path.relative_to(source)))
                    info.mtime = info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    if path.is_file():
                        with path.open("rb") as content:
                            output.addfile(info, content)
                    else:
                        output.addfile(info)
    return archive


def retarget_service(step, state, *, compiler=False):
    from .isaac import record_global_artifacts
    import shutil
    import tarfile

    config, stage = step.config, step.in_stage
    perf_sim = not compiler and step.perf_sim
    if config["SERVICE_TIMEOUT"] <= 0 or config["SERVICE_POLL_INTERVAL"] <= 0:
        raise ValueError("Service timeout and poll interval must be positive")
    if not shutil.which("zstd") or not hasattr(tarfile, "data_filter"):
        raise RuntimeError("Service extraction requires zstd and Python with tarfile.data_filter")
    gen = Path(state.paths[f"{stage}.gen_dir"])
    index = Path(state.paths[f"{stage}.index"])
    name = "seal5_splitted" if compiler and step.splitted else "seal5" if compiler else "etiss_perf" if perf_sim else "etiss"
    if compiler:
        sets = [part.strip() for part in config["ISAAC_SET_NAME"].split(";")]
        if not all(sets):
            raise ValueError("ISAAC_SET_NAME must contain nonempty set names")
        descriptions = [gen / f"{name}{'.splitted' if step.splitted else ''}.core_desc" for name in sets]
        if len(descriptions) > 1 and not config["SERVICE_BUNDLE_COREDSL"]:
            raise ValueError("Multi-set LLVM service requests require SERVICE_BUNDLE_COREDSL")
    else:
        descriptions = [gen / f"{config['ISAAC_CORE_NAME']}.core_desc"]
    for path in [index, *descriptions]:
        if not path.is_file():
            raise FileNotFoundError(path)
    cdsl = descriptions[0]
    root = Path(state.paths["sess.dir"]) / "work" / stage / "service"
    root.mkdir(parents=True, exist_ok=True)
    inputs = root / f"{name}_request"
    inputs.mkdir(exist_ok=True)
    cpdsl = inputs / "unused.core_perf_dsl"
    cpdsl.write_text("")
    if compiler:
        worker_config = Path(config["SEAL5_SERVICE_CONFIG"])
        if not worker_config.is_file():
            raise ValueError("SEAL5_SERVICE_CONFIG must be a worker-compatible YAML file")
    else:
        worker_config = inputs / "config.yaml"
        worker_config.write_text("{}\n")
        # The API retains both description uploads under their own names.
        # The generated core imports its instruction set, which must travel
        # with it rather than referring to a path on the submitting host.
        if ";" in config["ISAAC_SET_NAME"] and not config["SERVICE_BUNDLE_COREDSL"]:
            raise ValueError("Service ETISS currently requires one ISAAC_SET_NAME")
        if not config["SERVICE_BUNDLE_COREDSL"]:
            cpdsl = gen / f"{config['ISAAC_SET_NAME']}.core_desc"
            if not cpdsl.is_file():
                raise FileNotFoundError(cpdsl)
    if config["SERVICE_BUNDLE_COREDSL"]:
        bundled, manifest = bundle_coredsl(descriptions)
        cdsl = inputs / cdsl.name
        cdsl.write_text(bundled)
        (inputs / "description_sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
    tag = config["SEAL5_SERVICE_TAG" if compiler else "ETISS_PERF_SERVICE_TAG" if perf_sim else "ETISS_SERVICE_TAG"]
    uploads = {}
    if perf_sim:
        hls_output = state.paths.get(f"{stage}.hls.default.output_dir")
        index_data = yaml.safe_load(index.read_text())
        artifacts = index_data.get("global", {}).get("artifacts") or {}
        hls_root = Path(hls_output).parent if hls_output else artifacts.get("HLS_DIR")
        if not hls_root:
            raise ValueError("PerfSim service requires stage HLS output or index HLS_DIR")
        if config["ISAAC_CORE_NAME"] != "XIsaacCore":
            raise ValueError("The PerfSim worker requires ISAAC_CORE_NAME=XIsaacCore")
        # Publishing this job's install path must not change its retry identity.
        artifacts.pop("ETISS_PERF_INSTALL_DIR", None)
        index_data.setdefault("global", {})["artifacts"] = artifacts
        request_index = inputs / "index.yaml"
        request_index.write_text(yaml.safe_dump(index_data, sort_keys=True))
        uploads = {"index": request_index, "hls": package_hls(hls_root, inputs / "hls.tar.gz")}
    digest = hashlib.sha256(
        config["SERVICE_URL"].encode() + b"\0" + tag.encode() + b"\0" +
        cdsl.name.encode() + b"\0" + cdsl.read_bytes() + b"\0" +
        cpdsl.name.encode() + b"\0" + cpdsl.read_bytes() + b"\0" + worker_config.read_bytes())
    for field, path in uploads.items():
        digest.update(field.encode() + b"\0")
        with Path(path).open("rb") as content:
            for chunk in iter(lambda: content.read(1024 * 1024), b""):
                digest.update(chunk)
    fingerprint = digest.hexdigest()
    handle = inputs / "job.json"
    with RetargetingService(config["SERVICE_URL"]) as service:
        if handle.exists():
            saved = json.loads(handle.read_text())
            if saved["fingerprint"] != fingerprint:
                raise ValueError("Saved service job inputs differ; use a fresh stage/workspace")
            job = ServiceJob(saved["job_id"], saved["token"])
        else:
            job = service.submit(tag, cdsl=cdsl, cpdsl=cpdsl, config=worker_config, **uploads)
            # Retain immediately, including when observation later times out.
            descriptor = os.open(handle, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as output:
                json.dump({"job_id": job.job_id, "token": job.token,
                           "fingerprint": fingerprint}, output)
        try:
            service.wait(job, timeout=config["SERVICE_TIMEOUT"], poll_interval=config["SERVICE_POLL_INTERVAL"])
        except (RuntimeError, TimeoutError) as error:
            log = inputs / "worker.log"
            try:
                service.download_logs(job, log)
            except Exception:
                # Failure to fetch diagnostics must not replace the job result.
                raise error
            raise type(error)(f"{error}; worker log saved to {log}") from error
        destination = root / name
        if not destination.exists():
            archive = service.download_artifact(job, inputs / "artifact.tar.zst")
            extract_artifact(archive, destination)
    install = destination / ("llvm_install" if compiler else f"{name}_install")
    executable = install / "bin" / ("clang" if compiler else "run_helper.sh")
    if not executable.is_file():
        raise FileNotFoundError(executable)
    if not compiler:
        relocate_etiss_helper(install)
        configure_etiss_runtime(install, config["ETISS_SERVICE_RUNTIME_IMAGE"])
    paths = {f"{stage}.{name}.install_dir": install}
    metrics = {}
    if not compiler and config["ETISS_SERVICE_RUNTIME_IMAGE"]:
        metrics[f"{stage}.{name}.runtime_image"] = config["ETISS_SERVICE_RUNTIME_IMAGE"]
    if perf_sim:
        for filename in ("uarchs.csv", "InstructionTrace_XISAAC.json"):
            if not (destination / filename).is_file():
                raise FileNotFoundError(destination / filename)
        if not (destination / "ini").is_dir():
            raise FileNotFoundError(destination / "ini")
        paths[f"{stage}.etiss_perf.uarchs_csv"] = destination / "uarchs.csv"
        paths[f"{stage}.etiss_perf.ini_dir"] = destination / "ini"
        paths[f"{stage}.etiss_perf.src_dir"] = extract_etiss_source(destination)
    if compiler:
        report = destination / "seal5_score.csv"
        if not report.is_file():
            # Workers publish status reports; retain the toolkit's score schema.
            _, env = step.extract_env({})
            step.run_isaac_toolkit(["isaac_toolkit.utils.seal5_score", "--output", report,
                "--seal5-status-csv", destination / "seal5_reports/status.csv",
                "--seal5-status-compact-csv", destination / "seal5_reports/status_compact.csv"],
                scripts_dir=Path(state.paths["demo.dir"]) / "scripts", env=env)
        scores = pd.read_csv(report)["seal5_score"]
        if scores.empty:
            raise ValueError("Service returned an empty compiler score report")
        paths[f"{stage}.{name}.seal5_score_csv"] = report
        metrics = {f"{stage}.{name}.{key}": value for key, value in {
            "avg_seal5_score": scores.mean(), "total_count": len(scores),
            "unsupported_count": int((scores < 1).sum()), "has_unsupported": bool((scores < 1).any())}.items()}
    for filename, key in (("seal5_reports/diff.csv", "diff_csv"), ("etiss_patch_full.stat", "patch_stat")):
        if (destination / filename).is_file():
            paths[f"{stage}.{name}.{key}"] = destination / filename
    record_global_artifacts(index, **{"LLVM_INSTALL_DIR" if compiler else "ETISS_PERF_INSTALL_DIR" if perf_sim else "ETISS_INSTALL_DIR": install})
    if not config["SERVICE_KEEP_ARCHIVE"]:
        (inputs / "artifact.tar.zst").unlink(missing_ok=True)
    return {}, metrics, paths
