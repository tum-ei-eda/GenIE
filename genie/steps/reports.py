"""Implementation change reports for retargeted hardware and software."""
import difflib
from pathlib import Path
import re

import pandas as pd

from .candidates import CandidateStep
from .step import GenIEStep


def compare_rtl_trees(baseline, modified):
    """Return a unified text patch and line-change statistics."""
    baseline, modified = Path(baseline), Path(modified)
    files = {p.relative_to(root) for root in (baseline, modified) for p in root.rglob("*") if p.is_file()}
    patch = []
    changed = inserted = deleted = 0
    for relative in sorted(files):
        left, right = baseline / relative, modified / relative
        before = left.read_text().splitlines(keepends=True) if left.exists() else []
        after = right.read_text().splitlines(keepends=True) if right.exists() else []
        if before == after:
            continue
        changed += 1
        patch.extend(difflib.unified_diff(before, after, fromfile=f"a/{relative}", tofile=f"b/{relative}"))
        for tag, i, j, k, l in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            if tag in ("replace", "delete"):
                deleted += j - i
            if tag in ("replace", "insert"):
                inserted += l - k
    return "".join(patch), {"n_files_changed": changed, "n_insertions": inserted, "n_deletions": deleted}


@GenIEStep.factory.register()
class CollectImplementationMetrics(CandidateStep):
    id = "ISAAC.CollectImplementationMetrics"
    name = long_name = "Collect Implementation Metrics"

    def run(self, state_in, **kwargs):
        index, work, scripts = self.context(state_in)
        paths = {}
        rows = []
        baseline = state_in.paths.get(f"{self.in_stage}.hls.baseline.rtl_dir")
        if baseline:
            for variant in ("default", "custom", "shared"):
                rtl = state_in.paths.get(f"{self.in_stage}.hls.{variant}.rtl_dir")
                if not rtl:
                    continue
                patch, stats = compare_rtl_trees(baseline, rtl)
                output = Path(rtl).parent
                patch_file = output / "rtl.patch"
                stat_file = output / "rtl.patch.stat"
                patch_file.write_text(patch)
                stat_file.write_text(
                    f" {stats['n_files_changed']} files changed, {stats['n_insertions']} insertions(+), "
                    f"{stats['n_deletions']} deletions(-)\n"
                )
                prefix = f"{self.in_stage}.hls.{variant}"
                paths.update({f"{prefix}.rtl_patch": patch_file, f"{prefix}.rtl_patch_stat": stat_file})
        diff_csv = state_in.paths.get(f"{self.in_stage}.seal5.diff_csv")
        if diff_csv:
            frame = pd.read_csv(diff_csv)
            frame = frame[frame["phase"].isin([f"PHASE_{i}" for i in range(1, 6)])]
            rows.append({"step": "seal5", **{key: int(frame[key].sum()) for key in
                         ("n_files_changed", "n_insertions", "n_deletions")}})
        etiss_stat = state_in.paths.get(f"{self.in_stage}.etiss.patch_stat")
        if etiss_stat:
            text = Path(etiss_stat).read_text()
            def count(pattern):
                match = re.search(pattern, text)
                return int(match.group(1)) if match else 0
            rows.append({"step": "etiss", "n_files_changed": count(r"(\d+) files? changed"),
                         "n_insertions": count(r"(\d+) insertions?"), "n_deletions": count(r"(\d+) deletions?")})
        hls_metrics = state_in.paths.get(f"{self.in_stage}.hls.metrics_csv")
        if hls_metrics:
            frame = pd.read_csv(hls_metrics)
            rows.append({"step": "rtl", "n_files_changed": 1,
                         "n_insertions": int(frame["locs"].sum()), "n_deletions": 0})
        report = work / "combined_locs.csv"
        pd.DataFrame(rows, columns=["step", "n_files_changed", "n_insertions", "n_deletions"]).to_csv(report, index=False)
        paths[f"{self.in_stage}.combined_locs_csv"] = report
        return {}, {}, paths


@GenIEStep.factory.register()
class CreateReanalysisDiff(CandidateStep):
    """Compare selected basic blocks between baseline and ISE sessions."""
    id = "ISAAC.CreateReanalysisDiff"
    name = long_name = "Create Reanalysis Diff"

    def run(self, state_in, **kwargs):
        index, work, scripts = self.context(state_in)
        baseline = Path(state_in.paths["sess.dir"]) / "table"
        current = Path(state_in.paths[f"{self.in_stage}.reanalysis.dir"]) / "table"
        choices = pd.read_pickle(baseline / "choices.pkl")
        old_bbs = pd.read_pickle(baseline / "llvm_bbs_new.pkl")
        new_bbs = pd.read_pickle(current / "llvm_bbs_new.pkl")
        old_disass = pd.read_pickle(baseline / "disass.pkl")
        new_disass = pd.read_pickle(current / "disass.pkl")
        runtime = pd.read_pickle(current / "compare_runtime_per_llvm_bb.pkl")
        lines = ["=== DIFFS ===\n"]
        summary = []
        for i, choice in choices.iterrows():
            function, block = choice["func_name"], choice["bb_name"]
            label = f"{function}-{block}"
            lines.append(f"{i}) <{label}>\n")
            match = runtime.loc[runtime.index == label]
            if match.empty:
                lines.append("Not found!\n")
                continue
            if len(match) != 1:
                raise ValueError(f"Ambiguous runtime entry: {label}")
            def snippet(blocks, disassembly):
                rows = blocks[(blocks["func_name"] == function) & (blocks["bb_name"] == block)]
                if len(rows) != 1:
                    raise ValueError(f"Expected one block entry for {label}, found {len(rows)}")
                row = rows.iloc[0]
                instructions = disassembly[(disassembly["pc"] >= row["start"]) & (disassembly["pc"] < row["end"])]
                if len(instructions) != int(row["num_instrs"]):
                    raise ValueError(f"Disassembly count disagrees with block metadata for {label}")
                return instructions
            before = snippet(old_bbs, old_disass)
            after = snippet(new_bbs, new_disass)
            if len(before) == 0:
                raise ValueError(f"Cannot compare an empty baseline block: {label}")
            measurement = match.iloc[0]
            count_diff = len(after) - len(before)
            for description, value in (
                ("rel_weight [old]", measurement["rel_weight_"]),
                ("rel_weight [new]", measurement["rel_weight"]),
                ("rel_weight [diff]", measurement["diff"]),
                ("rel_weight [rel]", f"{measurement['diff_rel'] * 100:.2f}%"),
                ("num_instrs [old]", len(before)), ("num_instrs [new]", len(after)),
                ("num_instrs [diff]", count_diff),
                ("num_instrs [rel]", f"{count_diff / len(before) * 100:.2f}%"),
            ):
                lines.append(f"{description}: {value}\n")
            def assembly(frame):
                return [f"{row['instr']}  {row['args']}\n" for _, row in frame.iterrows()]
            lines.extend(difflib.unified_diff(assembly(before), assembly(after), fromfile="old", tofile="new"))
            summary.append({"func_name": function, "bb_name": block,
                            "old_num_instrs": len(before), "new_num_instrs": len(after),
                            "num_instrs_diff": count_diff, "runtime_diff_rel": measurement["diff_rel"]})
        report = work / "diff_summary.txt"
        report.write_text("".join(lines))
        table = work / "diff_summary.csv"
        pd.DataFrame(summary, columns=["func_name", "bb_name", "old_num_instrs", "new_num_instrs",
                                      "num_instrs_diff", "runtime_diff_rel"]).to_csv(table, index=False)
        return {}, {f"{self.in_stage}.diff.num_blocks": len(summary)}, {
            f"{self.in_stage}.diff_summary_txt": report, f"{self.in_stage}.diff_summary_csv": table,
        }
