import click
import pytest
from genie.flows.cli import initial_state_cb
from genie.state import State


def test_initial_state_callback_returns_genie_state_with_stage_paths(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(State(paths={"filtered.workdir": str(tmp_path)}, metrics={"filtered.num_candidates": 2}).dumps())
    state = initial_state_cb(None, None, str(path))
    assert isinstance(state, State)
    assert state.paths["filtered.workdir"] == str(tmp_path)
    assert state.metrics["filtered.num_candidates"] == 2


def test_initial_state_callback_reports_invalid_input(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("not json")
    with pytest.raises(click.BadParameter):
        initial_state_cb(None, None, str(path))
    assert initial_state_cb(None, None, None) is None
