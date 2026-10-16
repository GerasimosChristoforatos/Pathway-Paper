"""Final check of the generated outputs (run_all.py, last step): stale terms of
earlier versions must not appear in any generated output or document of the run
(MODEL v3.0.0: the frozen-technology check run is no longer part of the pipeline): the storyline scenario of v1.0.2-v1.2 (S2 + damped mix
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
# every pathway and v3 output must exist after a run
PATHWAYS_OUTPUTS = [layout.data(f'pathways/{f}', frozen=False) for f in (
    'runs.csv', 'annual.csv', 'bands.csv', 'bands_annual.csv', 'shapley.csv', 'shapley_subsets.csv', 'backcast.json',
    'solution_space.csv', 'levers.json', 'theoretical_limit.json', 'lambda_sweep.csv', 'waterfall.csv', 'waterfall_tl_from_reference.csv',
    'lever_annual.csv', 'reoccupation_log.csv', 'ordering_checks.json', 'montecarlo_draws.csv',
    'montecarlo_summary.csv', 'montecarlo_annual.csv', 'montecarlo_draw_rules.json', 'montecarlo_importance.csv',
    'montecarlo_fits.csv', 'montecarlo_conditional_tl.csv', 'montecarlo_conditional_tl.json')] + [
    layout.data(f'sensitivity/{f}.csv', frozen=False) for f in (
        'reference_carbon', 'pathway_carbon', 'planetary_boundary', 'replacement_variants', 'tornado')] + [
    layout.data('baseline/overbuild_absorption_log.csv', frozen=False)] + [
    layout.report(f, frozen=False) for f in ('METHODS_DRAFT.md', 'LEVERS_TABLE.md')]


def generated_files():
    files = [os.path.join(d, f) for base in (layout.DATA, layout.REPORTS) for d, _, fs in os.walk(base) for f in fs
             if f.endswith(('.md', '.json', '.csv'))]
    files += [os.path.join(ROOT, 'README.md')]
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
    """Figure files in outputs/paper_main/, paper_extended/, supplementary/ or diagnostics/ that figure_plan.py does not
    plan."""
    planned = {os.path.relpath(layout.figure(f), layout.OUT) for _, f, _ in FP.all_figures()}
    found = set()
    for base in (layout.PAPER_MAIN, layout.PAPER_EXTENDED, layout.SUPPLEMENTARY, layout.DIAGNOSTICS):
        for d, _, fs in os.walk(base):
            found |= {os.path.relpath(os.path.join(d, os.path.splitext(f)[0]), layout.OUT)
                      for f in fs if f.endswith('.png')}
    return sorted(found - planned)


def pdf_files():
    """MODEL v3.3.1: figures are PNG only; any PDF under the profile's output tree is an error."""
    return sorted(os.path.relpath(os.path.join(d, f), layout.OUT) for d, _, fs in os.walk(layout.OUT)
                  for f in fs if f.lower().endswith('.pdf'))


def main():
    missing = pathways_missing()
    if missing:
        print(f'check_outputs: pathways outputs missing: {missing}')
        sys.exit(1)
    pdfs = pdf_files()
    if pdfs:
        print(f'check_outputs: PDF files present (PNG only since MODEL v3.3.1): {pdfs[:10]}')
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
