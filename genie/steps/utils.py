import os
import shutil
import pathlib
from typing import Optional, Union
from git import Repo


def check_program(name: str, allow_none: bool = False, package: Optional[str] = None):
    # print("check_program", name, allow_none, package)
    path = shutil.which(name)
    if path is None:
        msg = f"Program {name} not found in path."
        if package is not None:
            msg += f" Try installing via `apt install {package}` or use prebuilt docker image."
        assert allow_none, msg
        return None
    # path = Path(os.readlink(path))
    path = pathlib.Path(path).resolve()
    return path


# Makes sure all directories at the given path are created.
def mkdirs(path: Union[str, bytes, os.PathLike]):
    """Wrapper for os.makedirs which handels the special case where the path already exits."""
    if not os.path.exists(path):
        os.makedirs(path)


def is_populated(path):
    if not isinstance(path, pathlib.Path):
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
    # print("clone", url, dest, branch, submodules, recursive, refresh)
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
        # print("update_submodules")
        if recursive:
            # print("recursive")
            if submodules:
                # print("submodules")
                for submodule in submodules:
                    assert isinstance(submodule, str), f"Submodules should be a list of str. {submodule} is not str."
                repo.git.submodule("update", "--init", "--recursive", "--", *submodules)
            else:
                # print("!submodules")
                repo.git.submodule("update", "--init", "--recursive")
        else:
            # print("!recursive")
            # TODO: share code
            if submodules:
                # print("submodules")
                for submodule in submodules:
                    assert isinstance(submodule, str), f"Submodules should be a list of str. {submodule} is not str."
                repo.git.submodule("update", "--init", "--", *submodules)
            else:
                # print("!submodules")
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
