"""Versions from the audited ISAAC demo, shared by setup and provenance reports."""

DEMO_REVISION = "be593a037cfd17cf3280d82410bab306c56e42ae"
SEAL5_BASE_REVISION = "b8d5e0932f68547b802fd53b7f4b75ed44a0daf1"
SEAL5_PORT_REVISION = "b8d5e0932f68547b802fd53b7f4b75ed44a0daf1"
LLVM_BASE_REF = "isaacnew-base-4"
REVISIONS = {
    "llvm-project": "1d0af5ca8c8e74bda11d683f908a8b6edae9a9f3",
    "M2-ISA-R": "59ba470011fafe5e814a2b9ca9504d8175fe25cc",
    "isaac-toolkit": "43fae872a999e9bbbe491e9f173ad7aca8c070a4",
    "mlonmcu": "ee84b85f2d7bf4dd898717cb12a80cb05dc45250",
    "seal5": "b8d5e0932f68547b802fd53b7f4b75ed44a0daf1",
    "memgraph_experiments": "0e5dd5f97e948ca68a4092c30095d3952875d6d5",
    "isaac-docker-service": "bfbb49f08618e321f060be4a76f2e1fd973de39e",
    "etiss_arch_riscv": "45e3067fcaac9e1cd79c4a008fa570c60055af92",
    "etiss_arch_riscv/rv_base": "749b7cbdde9596a119b3f580039c58e40d5614d5",
}


def checkout_provenance(directory):
    """Describe actual source trees, including local edits and revision drift."""
    from pathlib import Path
    from git import Repo, InvalidGitRepositoryError, NoSuchPathError

    directory = Path(directory)
    result = {}
    for name, expected in {"demo": DEMO_REVISION, **REVISIONS}.items():
        path = directory if name == "demo" else directory / name
        try:
            repo = Repo(path)
            actual = repo.head.commit.hexsha
            dirty = repo.is_dirty(untracked_files=True)
            result[name] = {"expected": expected, "revision": actual, "dirty": dirty,
                            "matches": actual == expected and not dirty}
        except (InvalidGitRepositoryError, NoSuchPathError):
            result[name] = {"expected": expected, "revision": None, "matches": False}
    return result
