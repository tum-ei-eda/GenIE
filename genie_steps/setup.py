import os
import pathlib
from time import sleep
from typing import List, Tuple, Union, Optional

from git import Repo

from openlane.steps.step import Step, ViewsUpdate, MetricsUpdate
from openlane.steps.step import GenIEStep
from openlane.config import Variable
from openlane.state import State
from openlane.common import Path


# Makes sure all directories at the given path are created.
def mkdirs(path: Union[str, bytes, os.PathLike]):
    """Wrapper for os.makedirs which handels the special case where the path already exits."""
    if not os.path.exists(path):
        os.makedirs(path)


def is_populated(path):
    if not isinstance(path, Path):
        path = pathlib.Path(path)
    return path.is_dir() and os.listdir(path.resolve())


def clone(
    url: str,
    dest: Union[str, bytes, os.PathLike],
    branch: str = "",
    submodules: list = [],
    recursive: bool = False,
    refresh: bool = False,
):
    print("clone", url, dest, branch, submodules, recursive, refresh)
    """Helper function for cloning a repository.

    Parameters
    ----------
    url : str
        Clone URL of the repository.
    dest : Path
        Destination directory path.
    branch : str
        Optional branch name or commit reference/tag.
    submodules : list of strings
        Only affects when recursive is true. Submodules to be updated. If empty, all submodules will be updated.
    recursive : bool
        If the clone should be done recursively.
    refesh : bool
        Enables switching the url/branch if the repo already exists
    """
    mkdirs(dest)

    def update_submodules(repo):
        print("update_submodules")
        if recursive:
            print("recursive")
            if submodules:
                print("submodules")
                for submodule in submodules:
                    assert isinstance(submodule, str), f"Submodules should be a list of str. {submodule} is not str."
                repo.git.submodule("update", "--init", "--recursive", "--", *submodules)
            else:
                print("!submodules")
                repo.git.submodule("update", "--init", "--recursive")
        else:
            print("!recursive")
            # TODO: share code
            if submodules:
                print("submodules")
                for submodule in submodules:
                    assert isinstance(submodule, str), f"Submodules should be a list of str. {submodule} is not str."
                repo.git.submodule("update", "--init", "--", *submodules)
            else:
                print("!submodules")
                repo.git.submodule("update", "--init")

    if is_populated(dest):
        if refresh:
            repo = Repo(dest)
            # TODO: backup old remote?
            repo.remotes.origin.set_url(url)
            repo.remotes.origin.fetch()
            repo.git.checkout(branch)
            repo.git.pull("origin", branch)  # This should also work for specific commits
            update_submodules(repo)
    else:
        if branch:
            repo = Repo.clone_from(url, dest, recursive=recursive, no_checkout=True)
            repo.git.checkout(branch)
            update_submodules(repo)
        else:
            repo = Repo.clone_from(url, dest, recursive=recursive)
            update_submodules(repo)


def clone_demo_repo(url, dest, **kwargs):
    submodules = [
        "isaac-toolkit",  # TODO: via pip?
        "memgraph_experiments",
        "M2-ISA-R",  # TODO: via pip?
        "etiss",  # TODO: prebuilt?
        "mlonmcu",  # TODO: via pip?
        # "llvm-project",
        "seal5",  # TODO: via pip?
        "mgclient",  # TODO: prebuilt?
        "etiss_arch_riscv",
    ]
    clone(url, dest, submodules=submodules, **kwargs)


@Step.factory.register()
class SetupDemo(GenIEStep):
    """
    TODO.
    """

    id = "Setup.Demo"
    name = "Setup Demo"
    long_name = "Setup Demo Repository"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable("DEMO_REPO", str, "Clone URL of demo repo.", default="git@github.com:PhilippvK/isaac-demo.git"),
        Variable(
            "DEMO_REF",
            Optional[str],
            "Checkout non-default branch or tag",
        ),
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update demo dir/repo even if already populated.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        print("self", self, dir(self))
        print("step_dir", self.step_dir)
        config = self.config
        print("config", config)
        run_dir = pathlib.Path(self.step_dir).parent
        force_refresh = config["FORCE_REFRESH"]
        demo_dir = config.get("DEMO_DIR")
        if demo_dir is None:
            demo_repo = config.get("DEMO_REPO")
            assert demo_repo is not None
            demo_ref = config.get("DEMO_REF")
            demo_dir = run_dir / "demo"
            clone_demo_repo(demo_repo, demo_dir, branch=demo_ref, refresh=force_refresh)
        demo_dir = pathlib.Path(demo_dir)
        assert demo_dir.is_dir()
        # errors_count = 0
        # metrics_updates.update({"design__lint_error__count": errors_count})
        # views_updates["demo_dir"] = Path(demo_dir)
        # sleep(5.0)
        # self.config["DEMO_DIR"] = demo_dir
        return views_updates, metrics_updates


@Step.factory.register()
class SetupETISS(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupETISS"
    name = "Setup ETISS"
    long_name = "Setup ETISS"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable(
            "INSTALL_DIR",
            Optional[Path],
            "Existing install directory.",
        ),
        Variable(
            "ETISS_INSTALL_DIR",
            Optional[Path],
            "Existing ETISS install directory.",
        ),
        Variable(
            "CCACHE_DIR",
            Optional[Path],
            "Existing ccache directory.",
        ),
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update even if already populated.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        force_refresh = config["FORCE_REFRESH"]
        run_dir = pathlib.Path(self.step_dir).parent
        fallback_demo_dir = run_dir / "demo"
        demo_dir = config.get("DEMO_DIR") or fallback_demo_dir
        demo_dir = pathlib.Path(demo_dir)
        # fallback_install_dir = run_dir/ "install"
        fallback_install_dir = demo_dir / "install"
        install_dir = config.get("INSTALL_DIR") or fallback_install_dir
        install_dir = pathlib.Path(install_dir)
        # fallback_ccache_dir = run_dir / "ccache"
        fallback_ccache_dir = install_dir / "ccache"  # TODO: move to toplevel
        ccache_dir = config.get("CCACHE_DIR") or fallback_ccache_dir
        ccache_dir = pathlib.Path(ccache_dir)
        fallback_etiss_install_dir = install_dir / "etiss"
        etiss_install_dir = config.get("ETISS_INSTALL_DIR") or fallback_etiss_install_dir
        etiss_install_dir = pathlib.Path(etiss_install_dir)
        print("etiss_install_dir", etiss_install_dir)
        # input(">")
        if is_populated(etiss_install_dir) and not force_refresh:
            return views_updates, metrics_updates
        scripts_dir = demo_dir / "scripts"
        setup_etiss_script = scripts_dir / "setup_etiss.sh"
        print("demo_dir", demo_dir)
        print("setup_etiss_script", setup_etiss_script)
        assert setup_etiss_script.is_file()
        # command = self.get_command()
        command = [setup_etiss_script]
        env["INSTALL_DIR"] = install_dir  # TODO: eliminate, replace by ETISS_INSTALL_DIR
        env["CCACHE_DIR"] = ccache_dir
        env["CCACHE"] = "1"
        env["TOP_DIR"] = run_dir
        check = True

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )
        print("subprocess_result", subprocess_result)
        return views_updates, metrics_updates


@Step.factory.register()
class SetupLLVM(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupLLVM"
    name = "Setup LLVM"
    long_name = "Setup LLVM"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update even if already populated.",
            default=False,
        ),
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable(
            "INSTALL_DIR",
            Optional[Path],
            "Existing install directory.",
        ),
        Variable(
            "LLVM_INSTALL_DIR",
            Optional[Path],
            "Existing llvm install directory.",
        ),
        Variable(
            "MGCLIENT_INSTALL_DIR",
            Optional[Path],
            "Existing mgclient install directory.",
        ),
        # TODO: just expose DL URL?
        Variable(
            "DOWNLOAD_LLVM",
            bool,
            "Name of prebuilt llvm.",
            default=True,
        ),
        Variable(
            "LLVM_PREBUILT_NAME",
            Optional[str],
            "Name of prebuilt llvm.",
        ),
        Variable(
            "LLVM_PREBUILT_VERSION",
            Optional[str],
            "Version of prebuilt llvm.",
        ),
        Variable(
            "CCACHE_DIR",
            Optional[Path],
            "Existing ccache directory.",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        force_refresh = config["FORCE_REFRESH"]
        run_dir = pathlib.Path(self.step_dir).parent
        fallback_demo_dir = run_dir / "demo"
        demo_dir = config.get("DEMO_DIR") or fallback_demo_dir
        demo_dir = pathlib.Path(demo_dir)
        # fallback_install_dir = run_dir/ "install"
        fallback_install_dir = demo_dir / "install"
        install_dir = config.get("INSTALL_DIR") or fallback_install_dir
        install_dir = pathlib.Path(install_dir)
        # fallback_ccache_dir = run_dir / "ccache"
        fallback_ccache_dir = install_dir / "ccache"  # TODO: move to toplevel
        ccache_dir = config.get("CCACHE_DIR") or fallback_ccache_dir
        ccache_dir = pathlib.Path(ccache_dir)
        fallback_llvm_install_dir = install_dir / "llvm"
        llvm_install_dir = config.get("LLVM_INSTALL_DIR") or fallback_llvm_install_dir
        llvm_install_dir = pathlib.Path(llvm_install_dir)
        print("llvm_install_dir", llvm_install_dir)
        # input(">")
        if is_populated(llvm_install_dir) and not force_refresh:
            return views_updates, metrics_updates
        fallback_mgclient_install_dir = install_dir / "mgclient"
        mgclient_install_dir = config.get("MGCLIENT_INSTALL_DIR") or fallback_mgclient_install_dir
        mgclient_install_dir = pathlib.Path(mgclient_install_dir)
        print("mgclient_install_dir", mgclient_install_dir)
        scripts_dir = demo_dir / "scripts"
        setup_llvm_script = scripts_dir / "setup_llvm.sh"
        print("setup_llvm_script", setup_llvm_script)
        assert setup_llvm_script.is_file()
        download_llvm_script = scripts_dir / "download_llvm.sh"
        print("download_llvm_script", download_llvm_script)
        assert download_llvm_script.is_file()
        # command = self.get_command()
        download_llvm = config["DOWNLOAD_LLVM"]
        print("download_llvm", download_llvm)
        command = [download_llvm_script if download_llvm else setup_llvm_script]
        env["INSTALL_DIR"] = install_dir  # TODO: eliminate, replace by LLVM_INSTALL_DIR
        env["TOP_DIR"] = run_dir
        if download_llvm:
            # TODO: handle DL URL
            pass
        else:
            env["CCACHE_DIR"] = ccache_dir  # TODO: use ccache for mgclient!
            env["CCACHE"] = "1"
            env["MGCLIENT_INSTALL_DIR"] = mgclient_install_dir
            env["LLVM_BUILD_TYPE"] = "Release"
        check = True

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )
        print("subprocess_result", subprocess_result)
        return views_updates, metrics_updates


@Step.factory.register()
class SetupMLonMCU(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupMLonMCU"
    name = "Setup MLonMCU"
    long_name = "Setup MLonMCU"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable(
            "VENV_DIR",
            Optional[Path],
            "Existing venv directory.",
        ),
        Variable(
            "INSTALL_DIR",
            Optional[Path],
            "Existing install directory.",
        ),
        # TODO: get mlonmcu via pip
        Variable(
            "MLONMCU_DIR",
            Optional[Path],
            "Existing MLonMCU directory.",
        ),
        Variable(
            "MLONMCU_HOME",
            Optional[Path],
            "Existing MLonMCU home directory.",
        ),
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update even if already populated.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        force_refresh = config["FORCE_REFRESH"]
        run_dir = pathlib.Path(self.step_dir).parent
        fallback_demo_dir = run_dir / "demo"
        demo_dir = config.get("DEMO_DIR") or fallback_demo_dir
        demo_dir = pathlib.Path(demo_dir)
        # fallback_install_dir = run_dir/ "install"
        fallback_install_dir = demo_dir / "install"
        install_dir = config.get("INSTALL_DIR") or fallback_install_dir
        install_dir = pathlib.Path(install_dir)
        # fallback_ccache_dir = run_dir / "ccache"
        fallback_ccache_dir = install_dir / "ccache"  # TODO: move to toplevel
        ccache_dir = config.get("CCACHE_DIR") or fallback_ccache_dir
        ccache_dir = pathlib.Path(ccache_dir)
        # fallback_venv_dir = run_dir / "venv"
        fallback_venv_dir = demo_dir / "venv"  # TODO: move to toplevel
        venv_dir = config.get("VENV_DIR") or fallback_venv_dir
        venv_dir = pathlib.Path(venv_dir)
        fallback_mlonmcu_dir = demo_dir / "mlonmcu"
        mlonmcu_dir = config.get("ETISS_HOME") or fallback_mlonmcu_dir
        mlonmcu_dir = pathlib.Path(mlonmcu_dir)
        print("mlonmcu_dir", mlonmcu_dir)
        fallback_mlonmcu_home_dir = install_dir / "mlonmcu"
        mlonmcu_home_dir = config.get("ETISS_HOME") or fallback_mlonmcu_home_dir
        mlonmcu_home_dir = pathlib.Path(mlonmcu_home_dir)
        print("mlonmcu_home_dir", mlonmcu_home_dir)
        if is_populated(mlonmcu_home_dir) and not force_refresh:
            return views_updates, metrics_updates
        scripts_dir = demo_dir / "scripts"
        setup_mlonmcu_script = scripts_dir / "setup_mlonmcu.sh"
        print("setup_mlonmcu_script", setup_mlonmcu_script)
        assert setup_mlonmcu_script.is_file()
        # command = self.get_command()
        env["INSTALL_DIR"] = install_dir  # TODO: eliminate, replace by MLONMCU_HOME
        env["MLONMCU_HOME"] = mlonmcu_home_dir
        # TODO: install mlonmcu into venv?
        pythonpath = env.get("PYTHONPATH")
        new_pythonpath = f"{mlonmcu_dir}:{pythonpath}"
        env["PYTHONPATH"] = new_pythonpath
        # env["ETISS_DIR"] = ?  # TODO
        # env["ETISS_INSTALL_DIR"] = ?  # TODO
        # env["LLVM_INSTALL_DIR"] = ?  # TODO
        # env["MLONMCU_TEMPLATE"] = template  # TODO: expose
        env["TOP_DIR"] = run_dir
        # check = True
        # command = [setup_mlonmcu_script]
        command = f"source {venv_dir}/bin/activate && {setup_mlonmcu_script}"

        # subprocess_result = self.run_subprocess(
        import subprocess

        subprocess.check_output(command, env=env, shell=True, executable="/bin/bash")
        # subprocess_result = self.run_subprocess(
        #     [command],
        #     env=env,
        #     check=check,
        #     shell=True,
        #     **kwargs,
        # )
        # print("subprocess_result", subprocess_result)
        return views_updates, metrics_updates


@Step.factory.register()
class SetupM2ISAR(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupM2ISAR"
    name = "Setup M2ISAR"
    long_name = "Setup M2ISAR"
    inputs = []
    outputs = []

    config_vars = [
        # Variable(
        #     "VERILOG_FILES",
        #     List[Path],
        #     "The paths of the design's Verilog files.",
        # ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        # config = self.config
        errors_count = 0
        metrics_updates.update({"design__lint_error__count": errors_count})
        sleep(5.0)
        return views_updates, metrics_updates


@Step.factory.register()
class SetupPython(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupPython"
    name = "Setup Python"
    long_name = "Setup Python"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable(
            "VENV_DIR",
            Optional[Path],
            "Existing venv directory.",
        ),
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update even if already populated.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        print("self", self, dir(self))
        print("step_dir", self.step_dir)
        config = self.config
        print("config", config)
        run_dir = pathlib.Path(self.step_dir).parent
        # force_refresh = config["FORCE_REFRESH"]
        fallback_demo_dir = run_dir / "demo"
        demo_dir = config.get("DEMO_DIR") or fallback_demo_dir
        demo_dir = pathlib.Path(demo_dir)
        # fallback_venv_dir = run_dir / "venv"
        fallback_venv_dir = demo_dir / "venv"  # TODO: move to toplevel
        venv_dir = config.get("VENV_DIR") or fallback_venv_dir
        venv_dir = pathlib.Path(venv_dir)
        force_refresh = config["FORCE_REFRESH"]
        if is_populated(venv_dir) and not force_refresh:
            return views_updates, metrics_updates
        scripts_dir = demo_dir / "scripts"
        setup_python_script = scripts_dir / "setup_python.sh"
        print("demo_dir", demo_dir)
        print("setup_python_script", setup_python_script)
        assert setup_python_script.is_file()
        # command = self.get_command()
        command = [setup_python_script]
        env["VENV_DIR"] = venv_dir
        check = True

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )
        print("subprocess_result", subprocess_result)
        # errors_count = 0466
        # metrics_updates.update({"design__lint_error__count": errors_count})
        # sleep(5.0)
        return views_updates, metrics_updates


@Step.factory.register()
class SetupMgclient(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupMgclient"
    name = "Setup Mgclient"
    long_name = "Setup Mgclient"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable(
            "INSTALL_DIR",
            Optional[Path],
            "Existing install directory.",
        ),
        Variable(
            "MGCLIENT_INSTALL_DIR",
            Optional[Path],
            "Existing mgclient install directory.",
        ),
        Variable(
            "CCACHE_DIR",
            Optional[Path],
            "Existing ccache directory.",
        ),
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update even if already populated.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        force_refresh = config["FORCE_REFRESH"]
        run_dir = pathlib.Path(self.step_dir).parent
        fallback_demo_dir = run_dir / "demo"
        demo_dir = config.get("DEMO_DIR") or fallback_demo_dir
        demo_dir = pathlib.Path(demo_dir)
        # fallback_install_dir = run_dir/ "install"
        fallback_install_dir = demo_dir / "install"
        install_dir = config.get("INSTALL_DIR") or fallback_install_dir
        install_dir = pathlib.Path(install_dir)
        # fallback_ccache_dir = run_dir / "ccache"
        fallback_ccache_dir = install_dir / "ccache"  # TODO: move to toplevel
        ccache_dir = config.get("CCACHE_DIR") or fallback_ccache_dir
        ccache_dir = pathlib.Path(ccache_dir)
        fallback_mgclient_install_dir = install_dir / "mgclient"
        mgclient_install_dir = config.get("MGCLIENT_INSTALL_DIR") or fallback_mgclient_install_dir
        mgclient_install_dir = pathlib.Path(mgclient_install_dir)
        print("mgclient_install_dir", mgclient_install_dir)
        # input(">")
        if is_populated(mgclient_install_dir) and not force_refresh:
            return views_updates, metrics_updates
        scripts_dir = demo_dir / "scripts"
        setup_mgclient_script = scripts_dir / "setup_mgclient.sh"
        print("demo_dir", demo_dir)
        print("setup_mgclient_script", setup_mgclient_script)
        assert setup_mgclient_script.is_file()
        # command = self.get_command()
        command = [setup_mgclient_script]
        env["INSTALL_DIR"] = install_dir  # TODO: eliminate, replace by MGCLIENT_INSTALL_DIR
        env["CCACHE_DIR"] = ccache_dir  # TODO: use ccache for mgclient!
        env["TOP_DIR"] = run_dir
        check = True

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )
        print("subprocess_result", subprocess_result)
        return views_updates, metrics_updates


@Step.factory.register()
class SetupCCache(GenIEStep):
    """
    TODO.
    """

    id = "Setup.SetupCCache"
    name = "Setup CCache"
    long_name = "Setup CCache"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "DEMO_DIR",
            Optional[Path],
            "Existing DEMO_DIR clone.",
        ),
        Variable(
            "INSTALL_DIR",
            Optional[Path],
            "Existing install directory.",
        ),
        Variable(
            "CCACHE_DIR",
            Optional[Path],
            "Existing ccache directory.",
        ),
        Variable(
            "FORCE_REFRESH",
            bool,
            "Update even if already populated.",
            default=False,
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        config = self.config
        force_refresh = config["FORCE_REFRESH"]
        run_dir = pathlib.Path(self.step_dir).parent
        fallback_demo_dir = run_dir / "demo"
        demo_dir = config.get("DEMO_DIR") or fallback_demo_dir
        demo_dir = pathlib.Path(demo_dir)
        # fallback_install_dir = run_dir / "install"
        fallback_install_dir = demo_dir / "install"
        install_dir = config.get("INSTALL_DIR") or fallback_install_dir
        install_dir = pathlib.Path(install_dir)
        # fallback_ccache_dir = run_dir / "ccache"
        fallback_ccache_dir = install_dir / "ccache"  # TODO: move to toplevel
        ccache_dir = config.get("CCACHE_DIR") or fallback_ccache_dir
        ccache_dir = pathlib.Path(ccache_dir)
        if is_populated(ccache_dir) and not force_refresh:
            return views_updates, metrics_updates
        scripts_dir = demo_dir / "scripts"
        setup_ccache_script = scripts_dir / "setup_ccache.sh"
        print("demo_dir", demo_dir)
        print("setup_ccache_script", setup_ccache_script)
        assert setup_ccache_script.is_file()
        # command = self.get_command()
        command = [setup_ccache_script]
        env["INSTALL_DIR"] = install_dir  # TODO: eliminate
        env["CCACHE_DIR"] = ccache_dir
        env["TOP_DIR"] = run_dir
        check = True

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )
        print("subprocess_result", subprocess_result)
        return views_updates, metrics_updates
