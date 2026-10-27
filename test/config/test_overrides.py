from typing import Dict, List
from genie.config import GenIEConfig, Variable


def test_json_list_dict_and_bare_string_overrides(tmp_path):
    variables = [Variable("BENCH", str, "Benchmark."),
                 Variable("ITEMS", List[str], "Items.", default=[]),
                 Variable("WEIGHTS", Dict[str, int], "Weights.", default={})]
    config, _ = GenIEConfig.load({"BENCH": "initial"}, variables, design_dir=str(tmp_path),
        config_override_strings=['ITEMS=["embench_iot/crc32","embench_iot/aha-mont64"]',
                                 'WEIGHTS={"a":2,"b":3}', 'BENCH=embench_iot/crc32'])
    assert config["ITEMS"] == ["embench_iot/crc32", "embench_iot/aha-mont64"]
    assert config["WEIGHTS"] == {"a": 2, "b": 3}
    assert config["BENCH"] == "embench_iot/crc32"


def test_json_quoted_string_preserves_equals_and_spaces(tmp_path):
    config, _ = GenIEConfig.load({"BENCH": "initial"}, [Variable("BENCH", str, "Benchmark.")],
        design_dir=str(tmp_path), config_override_strings=['BENCH="path with spaces=value"'])
    assert config["BENCH"] == "path with spaces=value"


def test_bare_numeric_override_remains_compatible_with_auto_string_option(tmp_path):
    variables = [Variable("BENCH", str, "Benchmark."), Variable("JOBS", str, "Count or auto.", default="auto")]
    config, _ = GenIEConfig.load({"BENCH": "test"}, variables, design_dir=str(tmp_path),
                                 config_override_strings=["JOBS=2"])
    assert config["JOBS"] == "2"
