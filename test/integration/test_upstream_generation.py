"""Exercise GenIE generation against the demo's actual typed toolchain sources."""
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from genie.steps.isaac import GenerateETISSCore
from genie.steps.cfu import GenerateRTL


def real_step(cls, stage, env):
    step = object.__new__(cls)
    step.in_stage = stage
    step.config = {var.name: var.default for var in cls.config_vars}
    step.config.update(ISAAC_ENCODING_POLICY="cfu", ISAAC_BASE_EXTENSIONS="i,m,zicsr,zifencei")
    step.extract_env = lambda kwargs: ({}, env.copy())

    def execute(args, **kwargs):
        kwargs.pop("check", None)
        result = subprocess.run(list(map(str, args)), capture_output=True, text=True, **kwargs)
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    step.run_subprocess = execute
    return step


def test_cfu_typed_generation_filtering_and_rtl_share_function_ids(tmp_path):
    demo = os.environ.get("GENIE_DEMO_SRC")
    if not demo:
        pytest.skip("Set GENIE_DEMO_SRC and the pinned M2-ISA-R/toolkit/tool source paths")
    from tool.gen.tree_utils import Assignment, Operation, Ref, Register, Statements
    from m2isar.frontends.coredsl2_set.parser import parse_cdsl2_set
    from isaac_toolkit.session import Session

    demo = Path(demo)
    session = tmp_path / "sess"
    Session.create(session).save()
    work = session / "work/initial"
    gen = work / "gen"
    gen.mkdir(parents=True)
    candidates = []
    for number, (name, operator, operation) in enumerate((("CADD", "+", "ADD"), ("CSUB", "-", "SUB"))):
        source = tmp_path / f"{name}.core_desc"
        source.write_text(f'''import "{demo / 'etiss_arch_riscv/rv_base/RVI.core_desc'}"
InstructionSet Candidate extends RV32I {{ instructions {{ {name} {{
operands: {{
unsigned<5> rd [[is_reg]] [[reg_class="GPR"]] [[reg_type="u32"]] [[out]];
unsigned<5> rs1 [[is_reg]] [[reg_class="GPR"]] [[reg_type="u32"]] [[in]];
unsigned<5> rs2 [[is_reg]] [[reg_class="GPR"]] [[reg_type="u32"]] [[in]];
}}
encoding: auto;
assembly: {{"{name.lower()}", "{{name(rd)}}, {{name(rs1)}}, {{name(rs2)}}"}};
behavior: {{ if (rd != 0) X[rd] = X[rs1] {operator} X[rs2]; }}
}} }} }}''')
        def register(operand):
            return Register("X", "gpr", children=[Ref(operand)])
        tree = Statements(children=[Assignment(children=[register("rd"), Operation(operation,
            children=[register("rs1"), register("rs2")], out_types=["unsigned<32>"])])])
        tree_file = tmp_path / f"{name}.pkl"
        tree_file.write_bytes(pickle.dumps(tree))
        candidates.append({"id": number, "artifacts": {"cdsl": str(source), "tree": str(tree_file)},
            "properties": {"InstrName": name, "EncodingPolicy": "cfu",
                "OperandNames": ["rd", "rs1", "rs2"], "OperandDirs": ["OUT", "IN", "IN"],
                "OperandTypes": ["REG"] * 3, "OperandRegClasses": ["GPR"] * 3, "OperandEncBits": [5] * 3,
                "#Loads": 0, "#Stores": 0, "#Mems": 0, "#Branches": 0, "#Terminators": 0}})
    index = work / "combined_index.yml"
    index.write_text(yaml.safe_dump({"candidates": candidates}))
    state = SimpleNamespace(paths={"demo.dir": demo, "sess.dir": session,
        "initial.index": index, "initial.workdir": work, "initial.gen_dir": gen}, metrics={"target.xlen": 32})
    env = {key: os.environ[key] for key in ("PATH", "PYTHONPATH") if key in os.environ}
    env["VENV_DIR"] = str(Path(sys.executable).parent.parent)
    for stage in ("initial", "filtered"):
        if stage == "filtered":
            work = session / "work/filtered"
            gen = work / "gen"
            gen.mkdir(parents=True)
            index = work / "index.yml"
            index.write_text(yaml.safe_dump({"candidates": [candidates[1]]}))
            state.paths.update({f"{stage}.index": index, f"{stage}.workdir": work, f"{stage}.gen_dir": gen})
        for cls in (GenerateETISSCore, GenerateRTL):
            step = real_step(cls, stage, env)
            state.paths.update(step.run(state)[2])
        validation = json.loads(Path(state.paths[f"{stage}.cfu.encoding_validation"]).read_text())
        assert validation["encoding_validation"] == "passed"
        manifest = json.loads(Path(state.paths[f"{stage}.cfu.manifest"]).read_text())
        assert manifest["instructions"]["XIsaac.CSUB"]["function_id"] == 1
        parsed = parse_cdsl2_set(gen / "XIsaac.core_desc", [str(demo / "etiss_arch_riscv/rv_base")])
        instructions = {insn.name: insn for insn in parsed["XIsaac"].instructions.values()}
        assert instructions["CSUB"].code == 0x100B
        rtl_dir = Path(state.paths[f"{stage}.cfu.rtl_dir"])
        report = json.loads((rtl_dir / "cfu_rtl.json").read_text())
        assert report["instructions"]["XIsaac.CSUB"]["function_id"] == 1
        assert "10'd1: selected_result" in (rtl_dir / "cfu.sv").read_text()
        if stage == "filtered":
            assert set(instructions) == {"CSUB"}
            assert "XIsaac.CADD" not in report["instructions"]
