from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path

from genie.steps.step import GenIEStep
from genie.steps.setup import SetupM2ISAR


def test_environment_carries_setup_venv_without_mutating_input():
    step = object.__new__(SetupM2ISAR)
    step.state_in = Future()
    step.state_in.set_result(SimpleNamespace(paths={"venv.dir": Path('/tmp/custom venv')}))
    original = {"PATH": "/bin"}
    kwargs, env = step.extract_env({"env": original, "check": True})
    assert env["VENV_DIR"] == "/tmp/custom venv"
    assert original == {"PATH": "/bin"}
    assert kwargs == {"check": True}


def test_explicit_launcher_environment_takes_precedence():
    step = object.__new__(SetupM2ISAR)
    step.state_in = Future()
    step.state_in.set_result(SimpleNamespace(paths={"venv.dir": "/tmp/state-venv"}))
    _, env = step.extract_env({"env": {"VENV_DIR": "/tmp/explicit-venv"}})
    assert env["VENV_DIR"] == "/tmp/explicit-venv"


def test_m2isar_setup_uses_selected_python_and_source(tmp_path):
    step = object.__new__(SetupM2ISAR)
    source = tmp_path / "custom source"
    source.mkdir()
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    step.config = {"M2ISAR_SRC_DIR": source}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_subprocess = Mock()
    state = SimpleNamespace(paths={"venv.dir": python.parent.parent, "demo.dir": tmp_path})
    assert step.run(state)[2] == {"m2isar.src_dir": source}
    assert step.run_subprocess.call_args.args[0] == [python, "-m", "pip", "install", "-e", source]


def test_mlonmcu_setup_uses_argument_list_and_venv_path(tmp_path):
    from genie.steps.setup import SetupMLonMCU
    step = object.__new__(SetupMLonMCU)
    step.step_dir = str(tmp_path / "step")
    source = tmp_path / "demo with spaces"
    (source / "scripts").mkdir(parents=True)
    script = source / "scripts/setup_mlonmcu.sh"
    script.touch()
    step.config = {"FORCE_REFRESH": False, "MLONMCU_DIR": None, "MLONMCU_HOME": None}
    step.extract_env = Mock(return_value=({}, {"PATH": "/usr/bin"}))
    step.run_subprocess = Mock()
    venv = tmp_path / "custom venv"
    state = SimpleNamespace(paths={"demo.dir": source, "install.dir": tmp_path / "install",
        "venv.dir": venv, "llvm.install_dir": tmp_path / "llvm",
        "etiss.install_dir": tmp_path / "etiss", "etiss.src_dir": tmp_path / "etiss-src"})
    step.run(state)
    assert step.run_subprocess.call_args.args[0] == [script]
    env = step.run_subprocess.call_args.kwargs["env"]
    assert env["VENV_DIR"] == str(venv)
    assert env["PATH"].startswith(str(venv / "bin") + ":")


def test_etiss_setup_accepts_disabled_ccache(tmp_path):
    from genie.steps.setup import SetupETISS
    step = object.__new__(SetupETISS)
    step.step_dir = str(tmp_path / "step")
    demo = tmp_path / "demo"
    (demo / "scripts").mkdir(parents=True)
    (demo / "scripts/setup_etiss.sh").touch()
    step.config = {"FORCE_REFRESH": False, "ETISS_SRC_DIR": None, "ETISS_INSTALL_DIR": None, "ENABLE_CCACHE": False}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_subprocess = Mock()
    state = SimpleNamespace(paths={"demo.dir": demo, "install.dir": tmp_path / "install", "ccache.dir": None})
    paths = step.run(state)[2]
    env = step.run_subprocess.call_args.kwargs["env"]
    assert env["CCACHE"] == "0"
    assert env["CCACHE_DIR"] == ""
    assert paths["etiss.install_dir"] == tmp_path / "install/etiss"


def test_toolkit_load_config_uses_default_and_publishes_source(tmp_path):
    from genie.steps.isaac import LoadConfig
    default = tmp_path / "cfg/isaac_toolkit/default.yml"
    default.parent.mkdir(parents=True)
    default.write_text("flow: {}")
    session = tmp_path / "sess"
    session.mkdir()
    step = object.__new__(LoadConfig)
    step.config = {"ISAAC_TOOLKIT_CONFIG_YAML": None}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    paths = step.run(SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": session}))[2]
    assert step.run_isaac_toolkit.call_args.args[0] == ["isaac_toolkit.frontend.cfg.yaml", default]
    assert paths["isaac.config_yaml"] == default


def test_seal5_adapter_restores_explicit_overrides_after_toolkit(monkeypatch):
    import os
    import sys
    from genie.steps.seal5_local_adapter import main
    monkeypatch.setenv("GENIE_SEAL5_SCRIPT", "/tmp/adapter with spaces.sh")
    monkeypatch.setenv("GENIE_LLVM_REPO", "/tmp/source with spaces")
    monkeypatch.setenv("GENIE_LLVM_REF", "custom-tag")
    monkeypatch.setenv("GENIE_SEAL5_HOME", "/tmp/shared build")
    monkeypatch.setenv("SEAL5_HOME", "/tmp/overwritten-default")
    monkeypatch.setenv("LLVM_REPO", "toolkit-default")
    monkeypatch.setenv("LLVM_REF", "toolkit-default")
    monkeypatch.setattr(sys, "argv", ["adapter", "/tmp/output with spaces", "input.core_desc"])
    execute = Mock()
    monkeypatch.setattr(os, "execvpe", execute)
    main()
    script, args, env = execute.call_args.args
    assert args == ["/tmp/adapter with spaces.sh", "/tmp/output with spaces", "input.core_desc"]
    assert env["LLVM_REPO"] == "/tmp/source with spaces"
    assert env["LLVM_REF"] == "custom-tag"
    assert "GENIE_LLVM_REF" not in env
    assert env["SEAL5_HOME"] == "/tmp/shared build"
