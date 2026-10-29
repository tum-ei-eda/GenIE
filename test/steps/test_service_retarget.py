import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from types import SimpleNamespace

import pytest
import yaml

from genie.retargeting_service import ServiceJob, extract_artifact
from genie.steps.isaac import RetargetLLVM, RetargetISS, RetargetPerfSim
from genie.steps.spike import RetargetSpike


def archive(tmp_path, entries):
    if not shutil.which("zstd"):
        pytest.skip("zstd required for the actual worker artifact format")
    tar = tmp_path / "source.tar"
    with tarfile.open(tar, "w") as output:
        for name, content in entries.items():
            item = tarfile.TarInfo(name)
            data = content if isinstance(content, bytes) else content.encode()
            item.size = len(data)
            output.addfile(item, io.BytesIO(data))
    compressed = tmp_path / "source.tar.zst"
    with compressed.open("wb") as output:
        subprocess.run(["zstd", "-c", str(tar)], stdout=output, check=True)
    return compressed


@pytest.mark.parametrize("cls,compiler,splitted,bundled,multiple", [
    (RetargetLLVM, True, False, False, False), (RetargetLLVM, True, True, False, False),
    (RetargetISS, False, False, False, False), (RetargetPerfSim, False, False, False, False),
    (RetargetISS, False, False, True, False),
    (RetargetLLVM, True, False, True, True), (RetargetLLVM, True, True, True, True),
    (RetargetSpike, False, False, True, False), (RetargetSpike, False, False, False, False),
])
def test_service_retarget_publishes_artifacts_and_resumes(tmp_path, monkeypatch, cls, compiler, splitted, bundled, multiple):
    import genie.steps.service as module
    step = object.__new__(cls)
    step.splitted = splitted
    step.config = {v.name: v.default for v in cls.config_vars}
    step.config.update(USE_SEAL5_SERVICE=compiler, USE_ETISS_SERVICE=not compiler)
    step.config["USE_ETISS_PERF_SERVICE"] = cls is RetargetPerfSim
    step.config["USE_SPIKE_SERVICE"] = cls is RetargetSpike
    step.config["SERVICE_BUNDLE_COREDSL"] = bundled
    keep_archive = compiler and not splitted and not multiple
    step.config["SERVICE_KEEP_ARCHIVE"] = keep_archive
    gen = tmp_path / "gen"
    gen.mkdir()
    llvm_filename = "XIsaac.splitted.core_desc" if splitted else "XIsaac.core_desc"
    (gen / llvm_filename).write_text("InstructionSet XIsaac {}")
    if multiple:
        step.config["ISAAC_SET_NAME"] = "XIsaac;Other"
        (gen / ("Other.splitted.core_desc" if splitted else "Other.core_desc")).write_text("InstructionSet Other {}")
    (gen / "XIsaacCore.core_desc").write_text('import "XIsaac.core_desc"\nCore XIsaacCore {}')
    config = tmp_path / "worker.yaml"
    config.write_text("riscv: {xlen: 32}\n")
    step.config["SEAL5_SERVICE_CONFIG"] = str(config)
    index = tmp_path / "index.yaml"
    index.write_text("candidates: []\nglobal: {artifacts: []}\n")
    state = SimpleNamespace(paths={"initial.gen_dir": gen, "initial.index": index,
                                   "sess.dir": tmp_path / "sess"})
    if cls is RetargetPerfSim:
        hls = tmp_path / "hls"
        (hls / "output").mkdir(parents=True)
        (hls / "hls_schedules.csv").write_text("instr,cycles\nCUSTOM0,2\n")
        (hls / "output/selected_solutions.yaml").write_text("{}\n")
        state.paths["initial.hls.default.output_dir"] = hls / "output"
    files = {"output/llvm_install/bin/clang": "compiler",
             "output/seal5_score.csv": "instr,seal5_score\nCUSTOM0,1\n",
             "output/etiss_install/bin/run_helper.sh": "#!/bin/bash\nETISS_DIR=/worker/install\n",
             "output/etiss_perf_install/bin/run_helper.sh": "#!/bin/bash\nETISS_DIR=/worker/install\n",
             "output/uarchs.csv": "uarch\nexample\n",
             "output/ini/example.ini": "[example]\n",
             "output/InstructionTrace_XISAAC.json": "{}"}
    files.update({"output/spike/libextension.so": "plugin",
                  "output/spike/spike_plugin.json": json.dumps({"schema": 1, "core": "XIsaacCore",
                     "extlibs": ["libextension.so"], "extension_names": ["m2_XIsaacCore"]})})
    if cls is RetargetPerfSim:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as source_tar:
            entry = tarfile.TarInfo("src/bare_etiss_processor/get_metrics.py")
            entry.size = 5
            source_tar.addfile(entry, io.BytesIO(b"#test"))
        files["output/etiss_perf_source.tar.gz"] = buffer.getvalue()
    source = archive(tmp_path, files)
    submitted = []
    class Service:
        def __init__(self, url): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, tag, **kwargs):
            submitted.append(tag)
            assert kwargs["cdsl"].name == (llvm_filename if compiler else "XIsaacCore.core_desc")
            if multiple:
                assert "InstructionSet XIsaac" in kwargs["cdsl"].read_text()
                assert "InstructionSet Other" in kwargs["cdsl"].read_text()
            if not compiler:
                description = kwargs["cdsl"] if bundled else kwargs["cpdsl"]
                assert "InstructionSet" in description.read_text()
                if bundled:
                    assert 'import "XIsaac.core_desc"' not in description.read_text()
                else:
                    assert kwargs["cpdsl"].name == "XIsaac.core_desc"
            if cls is RetargetPerfSim:
                assert tag == "etiss_perf"
                assert yaml.safe_load(kwargs["index"].read_text())["candidates"] == []
                with tarfile.open(kwargs["hls"], "r:gz") as upload:
                    assert upload.extractfile("hls_schedules.csv").read().startswith(b"instr,cycles")
                    assert "output/selected_solutions.yaml" in upload.getnames()
            return ServiceJob("job", "secret")
        def wait(self, job, **kwargs):
            handles = list((tmp_path / "sess").rglob("job.json"))
            assert json.loads(handles[0].read_text())["job_id"] == job.job_id
        def download_artifact(self, job, destination):
            shutil.copyfile(source, destination)
            return destination
    monkeypatch.setattr(module, "RetargetingService", Service)
    _, metrics, paths = step.run(state)
    name = "seal5_splitted" if splitted else "seal5" if compiler else "etiss_perf" if cls is RetargetPerfSim else "spike" if cls is RetargetSpike else "etiss"
    if cls is RetargetSpike:
        assert paths["initial.spike.plugin_manifest"].is_file()
    else:
        assert paths[f"initial.{name}.install_dir"].is_dir()
    if cls is RetargetPerfSim:
        assert (paths["initial.etiss_perf.src_dir"] / "src/bare_etiss_processor/get_metrics.py").is_file()
    assert len(list((tmp_path / "sess").rglob("artifact.tar.zst"))) == int(keep_archive)
    if compiler:
        assert metrics[f"initial.{name}.total_count"] == 1
    step.run(state)
    assert len(submitted) == 1
    artifact_key = "LLVM_INSTALL_DIR" if compiler else "ETISS_PERF_INSTALL_DIR" if cls is RetargetPerfSim else "SPIKE_PLUGIN_MANIFEST" if cls is RetargetSpike else "ETISS_INSTALL_DIR"
    assert yaml.safe_load(index.read_text())["global"]["artifacts"][artifact_key]
    (gen / (llvm_filename if compiler else "XIsaacCore.core_desc")).write_text("changed")
    with pytest.raises(ValueError, match="inputs differ"):
        step.run(state)
    assert len(submitted) == 1


def test_service_archive_rejects_escape_before_publication(tmp_path):
    source = archive(tmp_path, {"output/../../escape": "bad"})
    destination = tmp_path / "result"
    with pytest.raises(tarfile.FilterError):
        extract_artifact(source, destination)
    assert not destination.exists()
    assert not (tmp_path / "escape").exists()


def test_hls_upload_is_deterministic_and_rejects_links(tmp_path):
    from genie.steps.service import package_hls
    source = tmp_path / "hls"
    source.mkdir()
    (source / "schedule.csv").write_text("cycles\n2\n")
    first = package_hls(source, tmp_path / "first.tar.gz").read_bytes()
    import os
    os.utime(source / "schedule.csv", (123, 456))
    assert package_hls(source, tmp_path / "second.tar.gz").read_bytes() == first
    (source / "link").symlink_to(source / "schedule.csv")
    with pytest.raises(ValueError, match="without links"):
        package_hls(source, tmp_path / "bad.tar.gz")


def test_downloaded_etiss_helper_follows_install_tree_after_move(tmp_path):
    from genie.steps.service import relocate_etiss_helper
    install = tmp_path / "original"
    (install / "bin").mkdir(parents=True)
    helper = install / "bin/run_helper.sh"
    helper.write_text('#!/bin/bash\nETISS_DIR=/worker/output/installed\nprintf "%s" "$ETISS_DIR"\n')
    relocate_etiss_helper(install)
    relocate_etiss_helper(install)  # A retry remains idempotent.
    moved = tmp_path / "moved installation"
    install.rename(moved)
    result = subprocess.run(["bash", str(moved / "bin/run_helper.sh")], check=True,
                            capture_output=True, text=True)
    assert result.stdout == str(moved)


def test_unknown_etiss_helper_layout_fails_explicitly(tmp_path):
    from genie.steps.service import relocate_etiss_helper
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/run_helper.sh").write_text("#!/bin/bash\n")
    with pytest.raises(ValueError, match="ETISS_DIR assignment"):
        relocate_etiss_helper(tmp_path)


def test_service_runtime_wrap_restore_and_mounts(tmp_path):
    from genie.steps.service import configure_etiss_runtime, relocate_etiss_helper
    from genie.steps.etiss_runtime import runtime_command
    install = tmp_path / "installed"
    (install / "bin").mkdir(parents=True)
    helper = install / "bin/run_helper.sh"
    helper.write_text("#!/bin/bash\nETISS_DIR=/worker/install\n")
    helper.chmod(0o755)
    (install / "include/etiss").mkdir(parents=True)
    (install / "include/etiss/config.h").write_text('#define ETISS_INSTALL_DIR "/jobs/example/install"\n')
    configure_etiss_runtime(install, "worker@sha256:example")
    configure_etiss_runtime(install, "worker@sha256:example")
    relocate_etiss_helper(install)
    elf = tmp_path / "program.elf"
    elf.touch()
    ini = tmp_path / "custom.ini"
    ini.touch()
    command = runtime_command(helper, [str(elf), "nodmi", f"-i{ini}"], tmp_path)
    assert command[:3] == ["docker", "run", "--rm"]
    assert command[command.index("--entrypoint") + 1] == "/bin/bash"
    assert f"{install}:{install}:ro" in command
    assert f"{install}:/jobs/example/install:ro" in command
    assert f"{tmp_path}:{tmp_path}:rw" in command
    assert f"{ini}:{ini}:ro" in command
    assert command[-5:] == ["worker@sha256:example", str(helper.with_name("run_helper.native.sh")),
                           str(elf), "nodmi", f"-i{ini}"]
    configure_etiss_runtime(install, "")
    assert "ETISS_DIR=" in helper.read_text()
    assert not helper.with_name("run_helper.native.sh").exists()
    assert not helper.with_name("genie_runtime.json").exists()


def test_bundle_coredsl_deduplicates_imports_and_preserves_comments(tmp_path):
    from genie.steps.service import bundle_coredsl
    (tmp_path / "base.core_desc").write_text("InstructionSet Base {}\n")
    (tmp_path / "extension.core_desc").write_text('import "base.core_desc"\nInstructionSet Ext extends Base {}\n')
    top = tmp_path / "core.core_desc"
    top.write_text('/*\nimport "missing.core_desc"\n*/\n// import "missing.core_desc"\n'
                   'import "base.core_desc"\nimport "extension.core_desc"\nCore Example provides Ext {}\n')
    text, manifest = bundle_coredsl(top)
    assert text.count("InstructionSet Base") == 1
    assert text.index("InstructionSet Base") < text.index("InstructionSet Ext") < text.index("Core Example")
    assert len(manifest) == 3
    assert 'import "missing.core_desc"' in text
    previous = text
    (tmp_path / "base.core_desc").write_text("InstructionSet Base { /* changed */ }\n")
    text, changed_manifest = bundle_coredsl(top)
    assert text != previous and changed_manifest != manifest


def test_bundle_coredsl_rejects_cycles_and_missing_dependencies(tmp_path):
    from genie.steps.service import bundle_coredsl
    top = tmp_path / "core.core_desc"
    top.write_text('import "core.core_desc"\n')
    with pytest.raises(ValueError, match="Cyclic CoreDSL"):
        bundle_coredsl(top)
    top.write_text('import "missing.core_desc"\n')
    with pytest.raises(FileNotFoundError):
        bundle_coredsl(top)


def test_bundle_multiple_sets_keeps_shared_base_once(tmp_path):
    from genie.steps.service import bundle_coredsl
    base = tmp_path / "base.core_desc"
    base.write_text("InstructionSet Base {}\n")
    sources = []
    for name in ("First", "Second"):
        path = tmp_path / f"{name}.core_desc"
        path.write_text(f'import "base.core_desc"\nInstructionSet {name} extends Base {{}}\n')
        sources.append(path)
    text, manifest = bundle_coredsl(sources)
    assert text.count("InstructionSet Base") == 1
    assert "InstructionSet First" in text and "InstructionSet Second" in text
    assert len(manifest) == 3
    with pytest.raises(ValueError, match="At least one"):
        bundle_coredsl([])


def test_service_direct_processor_runtime_preserves_binary(tmp_path):
    from genie.steps.service import configure_etiss_runtime
    from genie.steps.etiss_runtime import runtime_command
    install = tmp_path / "install"
    (install / "bin").mkdir(parents=True)
    helper = install / "bin/run_helper.sh"
    helper.write_text("#!/bin/bash\nETISS_DIR=/old\n")
    processor = install / "bin/bare_etiss_processor"
    processor.write_bytes(b"original executable")
    configure_etiss_runtime(install, "test-image")
    wrapper = processor.with_name("genie_etiss_processor.py")
    command = runtime_command(wrapper, ["--help"], tmp_path)
    assert command[command.index("--entrypoint") + 1] == str(processor)
    assert command[-2:] == ["test-image", "--help"]
    assert f"LD_LIBRARY_PATH={install / 'lib'}:{install / 'lib64'}" in command
    assert processor.read_bytes() == b"original executable"
    configure_etiss_runtime(install, "")
    assert not wrapper.exists()
    assert processor.read_bytes() == b"original executable"


def test_direct_runtime_mounts_elf_referenced_from_ini(tmp_path):
    import json
    from genie.steps.etiss_runtime import runtime_command
    install = tmp_path / "install"
    (install / "bin").mkdir(parents=True)
    wrapper = install / "bin/genie_etiss_processor.py"
    wrapper.with_name("genie_runtime.json").write_text(json.dumps({"image": "test-image"}))
    external = tmp_path / "external"
    external.mkdir()
    elf = external / "program.elf"
    elf.touch()
    ini = tmp_path / "custom.ini"
    ini.write_text(f"[StringConfigurations]\nvp.elf_file={elf}\n")
    cwd = tmp_path / "run"
    cwd.mkdir()
    command = runtime_command(wrapper, [f"-i{ini}"], cwd)
    assert f"{elf}:{elf}:ro" in command
    command = runtime_command(wrapper, [f"--vp.elf_file={elf}"], cwd)
    assert f"{elf}:{elf}:ro" in command


@pytest.mark.parametrize("member", ["../../escape", "src/wrong.py"])
def test_etiss_source_rejects_escape_and_missing_metrics(tmp_path, member):
    from genie.steps.service import extract_etiss_source
    with tarfile.open(tmp_path / "etiss_perf_source.tar.gz", "w:gz") as output:
        entry = tarfile.TarInfo(member)
        entry.size = 1
        output.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises((tarfile.FilterError, FileNotFoundError)):
        extract_etiss_source(tmp_path)
    assert not (tmp_path / "etiss_perf_source").exists()
    assert not (tmp_path.parent / "escape").exists()
