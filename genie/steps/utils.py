import shutil
import pathlib
from typing import Optional


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
