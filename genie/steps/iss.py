"""Shared ISS selection and Spike runtime configuration."""
from typing import Optional

from genie.config import Variable

target_var = Variable("TARGET", str, "MLonMCU execution target.", default="etiss_rv32")
encoding_policy_var = Variable("ISAAC_ENCODING_POLICY", str, "Instruction encoding policy: auto or cfu.", default="auto")
iss_vars = [
    Variable("ISS", str, "ISS backend: auto, etiss, or spike.", default="auto"),
    Variable("SPIKE_RUNTIME", str, "Spike runtime: htif or pk.", default="htif"),
    Variable("SPIKE_EXE", Optional[str], "Matching Spike executable.", default=None),
    Variable("SPIKE_PK", Optional[str], "Proxy kernel for spike_pk.", default=None),
    Variable("ISAAC_GNU_INSTALL_DIR", Optional[str], "GNU toolchain used with the selected XLEN.", default=None),
]
spike_vars = [
    *iss_vars, target_var,
    Variable("USE_SPIKE_SERVICE", bool, "Build Spike plugins through the retargeting job API.", default=False),
    Variable("SPIKE_INSTALL_DIR", Optional[str], "Spike installation with matching development headers.", default=None),
    Variable("SPIKE_SOURCE_DIR", Optional[str], "Optional matching Spike sources.", default=None),
    Variable("SPIKE_BUILD_DIR", Optional[str], "Optional matching Spike build directory.", default=None),
]


def iss_backend(config, target=None):
    backend = config.get("ISS", "auto")
    if backend == "auto":
        target = target or config.get("TARGET", "etiss_rv32")
        backend = "spike" if target.startswith("spike") else "etiss"
    if backend not in ("etiss", "spike"):
        raise ValueError("ISS must be auto, etiss, or spike")
    return backend


def iss_target(config):
    if iss_backend(config) == "spike":
        runtime = config.get("SPIKE_RUNTIME", "htif")
        if runtime not in ("htif", "pk"):
            raise ValueError("SPIKE_RUNTIME must be htif or pk")
        target = config.get("TARGET", "etiss_rv32")
        if target == "spike_bm" and runtime == "pk":
            return "spike_pk"
        return target if target.startswith("spike_") else "spike_pk" if runtime == "pk" else "spike_bm"
    return config.get("TARGET", "etiss_rv32")
