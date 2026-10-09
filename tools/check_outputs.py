"""Final check of the generated outputs (run_all.py, last step): stale terms of
earlier versions must not appear in any generated output or document of the
adopted and frozen runs: the storyline scenario of v1.0.2-v1.2 (S2 + damped mix
trend), the retired decarbonisation names (horup_material, horup_class_v1_1, "mix
effect only") and the comparison runs removed in baseline-pb-v3 (--compare-modes,
DECARB_MODES, decarb_modes). CHANGELOG.md records them and is not checked.

    python tools/check_outputs.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import layout  # noqa: E402

STORYLINE = re.compile(r'storyline|S2-held|S3-10-trend|damped mix trend|intensification continues|horup_material|'
                       r'horup_class|mix effect only|compare-modes|DECARB_MODES|decarb_modes', re.I)
# every pathway output must exist after a run (outputs/data/pathways/, outputs/reports/)
PATHWAYS_OUTPUTS = [layout.data(f'pathways/{f}', frozen=False) for f in (
    'runs.csv', 'annual.csv', 'bands.csv', 'shapley_pathways.csv', 'shapley_levers.csv', 'shapley_subsets.csv',
    'backcast.json', 'solution_space.csv', 'levers.json', 'theoretical_limit.json', 'shapley_theoretical_limit.csv',
    'shapley_theoretical_limit_subsets.csv')] + [layout.report(f, frozen=False) for f in (
        'METHODS_DRAFT.md', 'LEVERS_TABLE.md')]


def generated_files():
    files = [os.path.join(d, f) for base in (layout.DATA, layout.REPORTS) for d, _, fs in os.walk(base) for f in fs
             if f.endswith(('.md', '.json', '.csv'))]
    files += [os.path.join(ROOT, 'README.md')]
    if os.environ.get('PATHWAY_QUICK') == '1':      # quick runs do not re-run the frozen AESA step
        files = [p for p in files if not (os.sep + layout.FROZEN + os.sep in p and os.sep + 'aesa' + os.sep in p)]
    return files


def storyline_hits():
    hits = {}
    for p in generated_files():
        with open(p, encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if STORYLINE.search(line):
                    hits.setdefault(os.path.relpath(p, ROOT), []).append(i)
    return hits


def pathways_missing():
    return [os.path.relpath(p, ROOT) for p in PATHWAYS_OUTPUTS if not os.path.exists(p)]


def unplanned_figures():
    """Figure files in outputs/headline/ or outputs/diagnostics/ that figure_plan.py does not plan."""
    planned = {os.path.relpath(layout.figure(f), layout.OUT) for _, f in FP.all_release_files()}
    found = set()
    for base in (layout.HEADLINE, layout.DIAGNOSTICS):
        for d, _, fs in os.walk(base):
            found |= {os.path.relpath(os.path.join(d, os.path.splitext(f)[0]), layout.OUT)
                      for f in fs if f.endswith(('.png', '.pdf'))}
    return sorted(found - planned)


def main():
    missing = pathways_missing()
    if missing:
        print(f'check_outputs: pathways outputs missing: {missing}')
        sys.exit(1)
    extra = unplanned_figures()
    if extra:
        print(f'check_outputs: figures not in figure_plan.py: {extra}')
        sys.exit(1)
    hits = storyline_hits()
    if hits:
        print(f'check_outputs: stale terms found in {hits}')
        sys.exit(1)
    print(f'check_outputs: no stale terms in {len(generated_files())} generated files; '
          f'{len(PATHWAYS_OUTPUTS)} pathway outputs present; every figure is planned')


if __name__ == '__main__':
    main()
