from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from genie.steps.isaac import PickChoices, ReportChoices


@pytest.mark.parametrize("suitable,count,message", [(False, 1, "unsuitable"), (True, 0, "No eligible")])
def test_pick_rejects_unsuitable_or_empty_results(tmp_path, suitable, count, message):
    table = tmp_path / "table"
    table.mkdir()
    pd.DataFrame({"has_potential": [suitable]}).to_pickle(table / "ise_potential.pkl")
    pd.DataFrame({"rel_weight": [0.5] * count}).to_pickle(table / "choices.pkl")
    step = object.__new__(PickChoices)
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    state = SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": tmp_path})
    with pytest.raises(ValueError, match=message):
        step.run(state)


def test_pick_accepts_all_suitable_rows_and_publishes_paths(tmp_path):
    table = tmp_path / "table"
    table.mkdir()
    pd.DataFrame({"has_potential": [True, True]}).to_pickle(table / "ise_potential.pkl")
    pd.DataFrame({"rel_weight": [0.4, 0.5]}).to_pickle(table / "choices.pkl")
    step = object.__new__(PickChoices)
    step.extract_env = Mock(return_value=({}, {}))
    step.run_isaac_toolkit = Mock()
    _, metrics, paths = step.run(SimpleNamespace(paths={"demo.dir": tmp_path, "sess.dir": tmp_path}))
    assert metrics["sess.num_choices"] == 2
    assert metrics["sess.total_choices_rel_weight"] == pytest.approx(0.9)
    assert metrics["sess.potential.[1].has_potential"] is True
    assert paths["sess.choices_pkl"].is_file()


def test_choice_reports_use_block_ranges_and_escape_content(tmp_path):
    table = tmp_path / "table"
    table.mkdir()
    pd.DataFrame([dict(func_name="f<name>", bb_name="bb", rel_weight=0.5,
                       num_instrs=2, freq=7)]).to_pickle(table / "choices.pkl")
    pd.DataFrame([dict(func_name="f<name>", bb_name="bb", start=0x10,
                       end=0x18)]).to_pickle(table / "llvm_bbs_new.pkl")
    (tmp_path / "generic_mlonmcu.dump").write_text("  10: 00 add # <source>\n  14: 00 sub\n  18: 00 outside\n")
    step = object.__new__(ReportChoices)
    step.step_dir = str(tmp_path / "report")
    _, _, paths = step.run(SimpleNamespace(paths={"sess.dir": tmp_path, "trace.output_dir": tmp_path}))
    full = paths["sess.choices_summary_html"].read_text()
    fragment = paths["sess.choices_summary_min_html"].read_text()
    assert "<!doctype html>" in full and "<!doctype" not in fragment
    assert "f&lt;name&gt;" in full and "&lt;source&gt;" in full
    assert "sub" in fragment and "outside" not in fragment
