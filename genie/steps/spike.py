"""Stage-specific Spike plugin retargeting using the demo's typed models."""
import json
from pathlib import Path

from .isaac import ISAACStep, isaac_core_name_var, isaac_set_name_var, record_global_artifacts
from .iss import spike_vars
from .service import service_vars, retarget_service
from .step import GenIEStep


def validate_plugin(manifest, core=None):
    manifest = Path(manifest)
    data = json.loads(manifest.read_text())
    if data.get("schema") != 1 or not data.get("extlibs") or not data.get("extension_names"):
        raise ValueError(f"Invalid Spike plugin manifest: {manifest}")
    if core is not None and data.get("core") != core:
        raise ValueError(f"Spike plugin core differs from {core}")
    if not isinstance(data["extlibs"], list) or not isinstance(data["extension_names"], list):
        raise ValueError("Spike extension libraries and names must be lists")
    for library in data["extlibs"]:
        path = Path(library)
        path = path if path.is_absolute() else manifest.parent / path
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(path)
    return data


def retarget_spike(step, state, **kwargs):
    if step.config.get("USE_SPIKE_SERVICE", False):
        return retarget_service(step, state, backend="spike")
    kwargs, env = step.extract_env(kwargs)
    source = state.paths.get("m2isar.src_dir")
    if source:
        env["PYTHONPATH"] = str(source) + ":" + env.get("PYTHONPATH", "")
    stage, config = step.in_stage, step.config
    gen = Path(state.paths[f"{stage}.gen_dir"])
    work = gen.parent
    core = config["ISAAC_CORE_NAME"]
    top = gen / f"{core}.core_desc"
    if not top.is_file():
        raise FileNotFoundError(top)
    scripts = Path(state.paths["demo.dir"]) / "scripts"
    model = gen / f"{core}.m2isarmodel"
    if not model.is_file():
        step.run_isaac_toolkit(["m2isar.frontends.coredsl2.parser", top, "--output", gen],
                              scripts_dir=scripts, has_log=False, env=env)
    if not model.is_file():
        raise FileNotFoundError(model)
    env["MLONMCU_HOME"] = str(state.paths["mlonmcu.home"])
    args = ["isaac_toolkit.retargeting.iss.spike", "--workdir", work, "--label", "",
            "--spike-core", core]
    for key, option in (("SPIKE_INSTALL_DIR", "--spike-install-dir"),
                        ("SPIKE_SOURCE_DIR", "--spike-source-dir"),
                        ("SPIKE_BUILD_DIR", "--spike-build-dir")):
        if config.get(key):
            args += [option, config[key]]
    step.run_isaac_toolkit(args, scripts_dir=scripts, has_force=True, env=env)
    manifest = work / "local/spike/spike_plugin.json"
    validate_plugin(manifest, core)
    record_global_artifacts(state.paths[f"{stage}.index"], SPIKE_PLUGIN_MANIFEST=manifest)
    return {}, {}, {f"{stage}.spike.plugin_manifest": manifest}


@GenIEStep.factory.register()
class RetargetSpike(ISAACStep):
    id = "ISAAC.RetargetSpike"
    name = long_name = "Retarget Spike Plugin"
    inputs = []
    outputs = []
    in_stage = "initial"
    perf_sim = False
    config_vars = ISAACStep.config_vars + service_vars + spike_vars + [isaac_core_name_var, isaac_set_name_var]

    def run(self, state_in, **kwargs):
        return retarget_spike(self, state_in, **kwargs)
