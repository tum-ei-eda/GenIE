from genie.flows import HardwareSelectionFlow
from genie.steps.isaac import record_global_artifacts
import yaml


def test_hardware_flow_producers_precede_stage_consumers():
    steps = HardwareSelectionFlow.Steps
    ids = [step.id for step in steps]
    assert len(ids) == len(set(ids))
    assert ids.index("ISAAC.FilterCandidates") < ids.index("ISAAC.CreateSpecGraph")
    for stage in ("filtered", "final"):
        hls = ids.index(f"ISAAC.RunHLS(in_stage={stage})")
        assert ids.index(f"ISAAC.GenerateInstrs(in_stage={stage})") < hls
        assert hls < ids.index(f"ISAAC.AssignHLSScore(in_stage={stage})")
        assert ids.index(f"MLonMCU.ISETrace(in_stage={stage})") < ids.index(f"ISAAC.Reanalyze(in_stage={stage})")
    assert ids.index("ISAAC.SelectWithSpecializations") < ids.index("ISAAC.GenerateInstrs(in_stage=final)")
    assert ids.index("ISAAC.RunHLS(in_stage=final)") < ids.index("ISAAC.RunASIPSynthesis(in_stage=final)")
    assert ids.index("CI.CreateSummary") < ids.index("CI.PrepareUploads") < ids.index("Misc.CleanupTempFiles")


def test_retargeting_artifacts_preserve_existing_index_data(tmp_path):
    index = tmp_path / "index.yml"
    data = {"global": {"artifacts": {"EXISTING": "keep"}}, "candidates": [{"id": 8}]}
    index.write_text(yaml.safe_dump(data))
    record_global_artifacts(index, LLVM_INSTALL_DIR=tmp_path / "llvm")
    result = yaml.safe_load(index.read_text())
    assert result["candidates"] == data["candidates"]
    assert result["global"]["artifacts"] == {"EXISTING": "keep", "LLVM_INSTALL_DIR": str(tmp_path / "llvm")}


def test_retargeting_artifacts_accept_empty_toolkit_list(tmp_path):
    index = tmp_path / "index.yml"
    index.write_text("global: {artifacts: []}\ncandidates: []\n")
    record_global_artifacts(index, ETISS_INSTALL_DIR=tmp_path / "etiss")
    data = yaml.safe_load(index.read_text())
    assert data["global"]["artifacts"] == {"ETISS_INSTALL_DIR": str(tmp_path / "etiss")}
