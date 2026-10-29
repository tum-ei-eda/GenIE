#!/usr/bin/env python3
"""Render publication figures and a resolved step inventory from current GenIE flows."""
import argparse
import html
import json
from pathlib import Path
import subprocess

from genie.flows.default import DefaultGenIEFlow, PerfSimGenIEFlow
from genie.flows.evaluation import ISSEvaluationFlow, HardwareSelectionFlow

FLOWS = [DefaultGenIEFlow, ISSEvaluationFlow, PerfSimGenIEFlow, HardwareSelectionFlow]
COLORS = {'shared': '#F1F4F8', 'extended': '#DDF1E9', 'replaced': '#DCEBFA', 'hardware': '#FFF0D5'}


def box(title, detail='', kind='shared'):
    return ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
            f'<TR><TD><B>{html.escape(title)}</B></TD></TR>'
            + (f'<TR><TD><FONT POINT-SIZE="10">{html.escape(detail).replace(chr(10), "<BR/>")}</FONT></TD></TR>' if detail else '')
            + '</TABLE>>')


def header(title, subtitle):
    return ['digraph G {', 'graph [rankdir=TB, bgcolor="white", pad="0.28", nodesep="0.22", ranksep="0.32", '
            'splines=polyline, fontname="Arial", labelloc=t, labeljust=l, '
            f'label={box(title, subtitle)}];',
            'node [shape=box, style="rounded,filled", color="#CBD5E1", fillcolor="#F1F4F8", '
            'fontname="Arial", fontsize=12, margin="0.07,0.04", penwidth=1.1];',
            'edge [color="#64748B", arrowsize=0.65, penwidth=1.2, fontname="Arial", fontsize=10];']


def comparison():
    g = header('GenIE | Flow comparison', 'Shared phases aligned across four registered Python flows · grouped steps, current implementation')
    titles = ['ISS · default', 'ISS · extended evaluation', 'Performance simulation', 'Hardware-aware selection']
    rows = [
        ('Setup', [('Setup & checks', 'Tools · session environment', 'shared')] * 4),
        ('Baseline', [('Benchmark & instruction trace', 'MLonMCU.Bench / Trace', 'shared'),
                      ('Benchmark & instruction trace', 'MLonMCU.Bench / Trace', 'shared'),
                      ('PerfSim benchmark & trace', 'PerfSimBench / PerfSimTrace', 'replaced'),
                      ('Benchmark & instruction trace', 'MLonMCU.Bench / Trace', 'shared')]),
        ('Discovery', [('Discover candidates', 'Load → analyze → pick → CDFG → query', 'shared')] * 4),
        ('Generation', [('Generate instructions & core', 'GenerateInstrs / GenerateETISSCore', 'shared'),
                        ('Generate + encoding metrics', 'GenerateInstrs / GenerateETISSCore\nAssignEncodingScore', 'extended'),
                        ('Generate instructions & core', 'GenerateInstrs / GenerateETISSCore', 'shared'),
                        ('Generate + encoding metrics', 'GenerateInstrs / GenerateETISSCore\nAssignEncodingScore', 'extended')]),
        ('Retargeting', [('LLVM + functional ISS', 'Combined / split LLVM · ETISS', 'shared'),
                         ('LLVM + functional ISS', 'Combined / split LLVM · ETISS\nCompiler-support annotation', 'extended'),
                         ('LLVM + timing simulator', 'HLS scheduling → PerfSim retargeting\nRetargetPerfSim replaces RetargetISS', 'replaced'),
                         ('LLVM + functional ISS', 'Combined / split LLVM · ETISS\nCompiler-support annotation', 'extended')]),
        ('Evaluation', [('Benchmark & compare', 'Aggregate + per-instruction evaluation', 'shared'),
                        ('Evaluate & reanalyze', 'Benchmarks + trace / reanalysis\nUtilization → score → sort', 'extended'),
                        ('PerfSim benchmark & compare', 'Microarchitecture sweep + CPI ranking\nPer-instruction evaluation retained', 'replaced'),
                        ('Evaluate & reanalyze', 'Benchmarks + trace / reanalysis\nUtilization → score → sort', 'extended')]),
        ('Refinement', [('Filter → regenerate', 'initial → filtered\nGenerate instructions & ETISS core', 'shared'),
                        ('Filter → regenerate', 'initial → filtered\nGenerate instructions & ETISS core', 'shared'),
                        ('Filter → regenerate', 'initial → filtered\nGenerate instructions & ETISS core', 'shared'),
                        ('Filter → select → reevaluate', 'filtered: ISS evaluation + HLS + scores\nfiltered_selected → final\nfinal: ISS evaluation + HLS + synthesis', 'hardware')]),
        ('Outputs', [('Report & finalize', 'Permissions · summary · bundle · cleanup', 'shared')] * 4),
    ]
    g.append('corner [shape=plain, label="PHASE", fontcolor="#64748B"];')
    for i, cls in enumerate(FLOWS):
        g.append(f'h{i} [fillcolor="#172B4D", fontcolor="white", color="#172B4D", width=3.15, label={box(titles[i], cls.__name__)}];')
    g.append('{rank=same; corner; h0; h1; h2; h3;}')
    g.append('corner -> h0 -> h1 -> h2 -> h3 [style=invis, weight=100];')
    for r, (phase, entries) in enumerate(rows):
        g.append(f'p{r} [shape=plain, fontcolor="#64748B", label="{phase}"];')
        if r:
            g.append(f'p{r-1} -> p{r} [style=invis, weight=100];')
        for c, (title, detail, kind) in enumerate(entries):
            g.append(f'n{r}_{c} [group="lane{c}", width=3.15, fillcolor="{COLORS[kind]}", label={box(title, detail)}];')
            g.append(f'{"h"+str(c) if not r else "n"+str(r-1)+"_"+str(c)} -> n{r}_{c};')
        g.append('{rank=same; ' + f'p{r}; ' + '; '.join(f'n{r}_{c}' for c in range(4)) + ';}')
        g.append(f'p{r} -> ' + ' -> '.join(f'n{r}_{c}' for c in range(4)) + ' [style=invis, weight=100];')
    g.append('legend [shape=plain, label=' + box('Reading the figure',
        'Gray: shared phase · green: added evaluation · blue: replacement · amber: expanded hardware refinement\n'
        'Colors describe structure, not validation. Physical HLS / timing-enabled PerfSim / synthesis validation is pending.\n'
        'Each column is a sequential flow; refinement expands the evaluation block at explicit candidate stages.') + '];')
    g.append('n7_1 -> legend [style=invis]; n7_2 -> legend [style=invis];')
    return '\n'.join(g + ['}'])


def refinement():
    g = header('GenIE | Candidate refinement', 'Main HardwareSelectionFlow path · solid arrows: candidate progression · dashed arrows: measurement feedback')
    nodes = {
        'initial': ('initial', 'Discovered candidate index', 'shared'),
        'first': ('FilterCandidates', 'Compiler support + measured runtime benefit', 'extended'),
        'filtered': ('filtered', 'Candidates surviving the first filter', 'shared'),
        'select': ('SelectWithSpecializations', 'Score / sort + specialization graph\nIterative selection under an encoding-cost budget', 'extended'),
        'selected': ('filtered_selected', 'Selected candidates', 'shared'),
        'finalize': ('SelectCandidates', 'Top-k if configured (0 = keep all)\nRename instructions and regenerate stage metadata', 'extended'),
        'final': ('final', 'Final instruction set', 'shared'),
        'e0': ('Evaluate initial candidates', 'Combined / split LLVM + ETISS\nAggregate + per-instruction benchmarks\nTrace → reanalysis → utilization → score / sort', 'extended'),
        'e1': ('Reevaluate filtered candidates', 'Repeat compiler / ISS evaluation + reanalysis\nHLS → implementation metrics → score / sort', 'hardware'),
        'e2': ('Evaluate final implementation', 'Repeat compiler / ISS evaluation + reanalysis\nHLS → score / sort → enabled synthesis\nAttach synthesis metrics → report', 'hardware'),
        'stop': ('Shorter registered flows', 'Default ISS / PerfSim / extended ISS\nstop after filtered-stage instruction\nand core generation; no automatic selection', 'shared'),
    }
    for ident, (title, detail, kind) in nodes.items():
        g.append(f'{ident} [fillcolor="{COLORS[kind]}", width={3.7 if ident.startswith("e") else 3.3}, label={box(title, detail)}];')
    g.append('initial -> first -> filtered -> select -> selected -> finalize -> final;')
    for state, evaluation in [('initial','e0'), ('filtered','e1'), ('final','e2')]:
        g.append(f'{{rank=same; {state}; {evaluation};}}')
        g.append(f'{state} -> {evaluation} [label=" stage artifacts", color="#26806A", constraint=false];')
    g.append('e0 -> first [style=dashed, color="#26806A", label=" measured benefit", constraint=false];')
    g.append('e1 -> select [style=dashed, color="#26806A", label=" updated scores / costs", constraint=false];')
    g.append('e0 -> e1 -> e2 [style=invis, weight=10];')
    g.append('{rank=same; filtered; stop; e1;}')
    g.append('filtered -> stop [style=dotted, arrowhead=none, constraint=false, color="#94A3B8"];')
    g.append('note [shape=plain, label=' + box('Explicit stages, shared evaluation',
        'Evaluation is repeated at initial, filtered, and final; dashed feedback does not imply an automatic runtime loop.\n'
        'HardwareSelectionFlow uses the solid path. Standalone phase APIs also expose filtered2 / filtered2_selected / prelim / prelim_filtered.\n'
        'HLS / synthesis depend on configuration and external tools. Physical hardware validation remains pending.') + '];')
    g.append('final -> note [style=invis]; e2 -> note [style=invis];')
    return '\n'.join(g + ['}'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('docs/figures'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    inventory = {flow.__name__: [{'id': step.id, 'in_stage': getattr(step, 'in_stage', None),
        'out_stage': getattr(step, 'out_stage', None)} for step in flow.Steps] for flow in FLOWS}
    (args.output_dir / 'flow_steps.json').write_text(json.dumps(inventory, indent=2) + '\n')
    for name, source in [('flow_comparison', comparison()), ('candidate_refinement', refinement())]:
        dot = args.output_dir / f'{name}.dot'
        dot.write_text(source + '\n')
        for extension in ('svg', 'pdf', 'png'):
            subprocess.run(['dot', f'-T{extension}', '-Gdpi=180', str(dot), '-o',
                            str(args.output_dir / f'{name}.{extension}')], check=True)
        print(f'Rendered {name}: SVG, PDF, PNG, DOT')


if __name__ == '__main__':
    main()
