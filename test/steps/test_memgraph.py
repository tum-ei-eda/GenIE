from types import SimpleNamespace
from unittest.mock import Mock

from genie.steps.docker import StartMemgraphServer
from genie.steps.isaac import PurgeCDFGDB
import pytest


def test_memgraph_container_maps_fixed_internal_port(monkeypatch):
    import docker
    client = Mock()
    client.containers.list.return_value = []
    monkeypatch.setattr(docker, "from_env", lambda: client)
    step = object.__new__(StartMemgraphServer)
    step.config = {v.name: v.default for v in step.config_vars}
    step.config.update(MEMGRAPH_PORT=17687, MEMGRAPH_HOST="127.0.0.1", MEMGRAPH_CONTAINER="genie-test-db")
    step.extract_env = Mock(return_value=({}, {}))
    step.run(None)
    assert client.containers.run.call_args.kwargs["ports"] == {"7687/tcp": ("127.0.0.1", 17687)}


def test_purge_does_not_pass_unsupported_force_flag(tmp_path):
    step = object.__new__(PurgeCDFGDB)
    step.config = {"ISAAC_PURGE_CDFG_DB": True}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    (tmp_path / "config.yml").write_text("memgraph: {hostname: localhost, port: 7687}")
    step.run(SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": tmp_path}))
    assert step.run_isaac_toolkit.call_args.kwargs["has_force"] is False


def test_purge_rejects_session_endpoint_mismatch(tmp_path):
    import pytest
    step = object.__new__(PurgeCDFGDB)
    step.config = {"ISAAC_PURGE_CDFG_DB": True, "MEMGRAPH_HOST": "localhost", "MEMGRAPH_PORT": 17687}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    (tmp_path / "config.yml").write_text("memgraph: {hostname: localhost, port: 7687}")
    with pytest.raises(ValueError, match="differs from configured"):
        step.run(SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": tmp_path}))
    step.run_isaac_toolkit.assert_not_called()


def test_cdfg_export_uses_requested_stage_and_endpoint(tmp_path):
    from genie.steps.isaac import PushCDFG
    step = object.__new__(PushCDFG)
    step.config = {"CDFG_STAGE": 64, "MEMGRAPH_HOST": "127.0.0.1", "MEMGRAPH_PORT": 17687}
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    state = SimpleNamespace(paths={"demo.dir": tmp_path, "mgclient.lib_dir": tmp_path, "sess.dir": tmp_path},
                            metrics={"trace.label": "test-graph"})
    step.run(state)
    call = step.run_isaac_toolkit.call_args_list[0]
    assert call.args[0][call.args[0].index("--stage") + 1] == 64
    assert call.kwargs["env"]["MEMGRAPH_PORT"] == "17687"
    assert call.kwargs["env"]["MEMGRAPH_HOST"] == "127.0.0.1"


def query_step(tmp_path):
    from genie.steps.isaac import QueryCandidates
    step = object.__new__(QueryCandidates)
    step.config = {variable.name: variable.default for variable in step.config_vars}
    step.extract_env = Mock(return_value=({}, {}))
    def execute(args, **kwargs):
        output = args[args.index("--workdir") + 1]
        (output / "combined_index.yml").write_text("candidates: []\n")
        (output / "names.csv").write_text("instr\nCUSTOM0\n")
        (output / "all_io_subs.pdf").write_bytes(b"test PDF artifact")
    step.run_isaac_toolkit = Mock(side_effect=execute)
    state = SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": tmp_path},
                            metrics={"trace.label": "validation-trace", "target.xlen": 64})
    return step, state


def test_query_forwards_overrides_including_zero_and_publishes_artifacts(tmp_path):
    step, state = query_step(tmp_path)
    step.config.update(ISAAC_LIMIT_RESULTS=7, ISAAC_XLEN=32, ISAAC_MIN_ISO_WEIGHT=0.0,
        ISAAC_SCALE_ISO_WEIGHT="auto", ISAAC_SORT_BY="IsoWeight", ISAAC_TOPK=0,
        ISAAC_PARTITION_WITH_MAXMISO="auto")
    _, metrics, paths = step.run(state)
    args = step.run_isaac_toolkit.call_args.args[0]
    for option, value in (("--limit-results", "7"), ("--xlen", "32"), ("--min-iso-weight", "0.0"),
        ("--scale-iso-weight", "auto"), ("--sort-by", "IsoWeight"), ("--topk", "0"),
        ("--partition-with-maxmiso", "auto")):
        assert args[args.index(option) + 1] == value
    assert metrics["initial.num_candidates"] == 1
    assert paths["initial.names_csv"].is_file()
    assert paths["initial.all_io_subs_pdf"].is_file()


def test_query_defaults_use_target_xlen_without_overriding_optional_flags(tmp_path):
    step, state = query_step(tmp_path)
    step.run(state)
    args = step.run_isaac_toolkit.call_args.args[0]
    assert args[args.index("--xlen") + 1] == "64"
    assert "--topk" not in args and "--min-iso-weight" not in args


@pytest.mark.parametrize("key,value", [("ISAAC_LIMIT_RESULTS", -1), ("ISAAC_TOPK", -1),
                                      ("ISAAC_MIN_ISO_WEIGHT", -0.1), ("ISAAC_XLEN", 16)])
def test_query_rejects_invalid_overrides_before_database_access(tmp_path, key, value):
    step, state = query_step(tmp_path)
    step.config[key] = value
    with pytest.raises(ValueError, match=key):
        step.run(state)
    step.run_isaac_toolkit.assert_not_called()
