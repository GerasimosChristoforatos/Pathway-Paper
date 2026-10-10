"""
INDEXES (MODEL v1.0.0): DIAGNOSTICS.md and the index of every output file
========================================================================
Writes, from the files the run produced (nothing is computed here):

  outputs/diagnostics/DIAGNOSTICS.md  every diagnostic figure (D01-D34, docs/FIGURE_PLAN.md) by
                                      group, with its content, the run-specific note the drawing
                                      script recorded (figaudit.py) and the script that draws it
  outputs/INDEX.md                    every file under outputs/ with one line on what it holds and
                                      which script writes it

FILES below is the registry of output files; tests/test_release.py checks that every file in
outputs/ (except the git-ignored logs) matches exactly one entry and that no entry is stale, so
a new output cannot be added without being described.

    python indexes.py            (run_all.py runs it after headline.py)
"""
import fnmatch
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import layout as L  # noqa: E402
import naming as N  # noqa: E402

# (pattern relative to outputs/, what it holds, the script that writes it)
FILES = [
    # headline
    ('headline/HEADLINE.md', 'The headline findings (one sentence each, with numbers and source files) and every '
     'headline figure with its caption', 'headline.py'),
    ('headline/H*.png', 'Headline figure, 300 dpi PNG, 183 mm wide', 'headline.py'),
    ('headline/H*.pdf', 'Headline figure, vector PDF (fonts embedded)', 'headline.py'),
    ('headline/H*.csv', 'Source data of the headline figure: every plotted value (panel, series, x, value, unit)',
     'headline.py'),
    # diagnostics
    ('diagnostics/DIAGNOSTICS.md', 'Every diagnostic figure by group, with its content and note', 'indexes.py'),
    ('diagnostics/*/D*.png', 'Diagnostic figure, 300 dpi PNG (DIAGNOSTICS.md)', 'see DIAGNOSTICS.md'),
    # data: baseline
    ('data/baseline/projection.json', 'The Reference projection: floor area, carbon (by stage, material, demand '
     'band), committed emissions after 2050, settings', 'projection.py'),
    ('data/baseline/annual.csv', 'History 1991-2025 and the Reference 2026-2050 by year: floor area, carbon and its '
     'components (materials and construction, soil carbon loss, maintenance)', 'projection.py'),
    ('data/baseline/bands_annual.csv', 'The in-scope demand bands of the Reference by year: floor area and carbon',
     'projection.py'),
    ('data/baseline/bands_history.csv', 'The demand bands of the history by census interval (interval means, one '
     'vacancy definition)', 'validation.py'),
    ('data/baseline/stock_identity_history.csv', 'Dwellings built by component per census interval (D05c): new '
     'households, vacancy, census-measured net replacement, retirement villages and unexplained building',
     'validation.py'),
    ('data/baseline/household_formation_history.csv', 'New households per census interval by source (D04c): from '
     'population growth and from household-size change', 'validation.py'),
    ('data/baseline/validation.json', 'Rolling-origin hindcast and the 2026 out-of-sample check', 'validation.py'),
    ('data/baseline/gap_2026.json', 'The 2026 gap between observed building and the requirement',
     'gap_2026.py'),
    ('data/baseline/overbuild_2026.json', 'The 2026 overbuild and how it is absorbed', 'tools/overbuild_2026.py'),
    ('data/baseline/scenarios.json', 'Totals of the projection variants (Low, Reference, High replacement and their '
     'sensitivities)', 'tools/replacement_scenarios.py'),
    ('data/baseline/variants_annual.csv', 'Annual floor area and carbon of every projection variant',
     'tools/replacement_scenarios.py'),
    ('data/baseline/reconciliation.json', 'Reconciliation of the totals between the scripts', 'tools/reconciliation.py'),
    ('data/baseline/reality_checks.json', 'Where the projection leaves the 1991-2025 range, and the 2026 to 2027 '
     'handover', 'tools/figures_report.py'),
    ('data/baseline/sensitivity_one_at_a_time.csv', 'Every one-at-a-time sensitivity: floor area and carbon',
     'Sensitivity.py'),
    ('data/baseline/sensitivity_annual_carbon.csv', 'Annual carbon 2026-2050 of every one-at-a-time sensitivity '
     '(and the population 5th / 95th percentile engine paths)', 'Sensitivity.py'),
    ('data/sensitivity/reference_carbon.csv', 'Grouped one-at-a-time sensitivity of the Reference carbon 2026-2050 '
     '(ED1, ED3)', 'tools/sensitivity_tables.py'),
    ('data/sensitivity/p5_carbon.csv', 'Grouped one-at-a-time sensitivity of P5 Combined (Moderate): carbon and '
     'cumulative LoE AR / AtP (ED2)', 'tools/sensitivity_tables.py'),
    ('data/sensitivity/planetary_boundary.csv', 'Grouped one-at-a-time sensitivity of the Reference cumulative LoE '
     'AR and AtP (ED4)', 'tools/sensitivity_tables.py'),
    # data: Monte Carlo
    ('data/montecarlo/draws_*.csv', 'Monte Carlo draws of a variant (Latin hypercube): inputs and outputs per draw',
     'MonteCarlo.py'),
    ('data/montecarlo/summary_*.csv', 'Monte Carlo summary of a variant: percentiles of floor area and carbon',
     'MonteCarlo.py'),
    ('data/montecarlo/annual_*.csv', 'Monte Carlo percentiles of a variant by year', 'MonteCarlo.py'),
    ('data/montecarlo/sobol_*.csv', 'Sobol indices of the Reference with bootstrap confidence intervals',
     'MonteCarlo.py'),
    # data: AESA
    ('data/aesa/results.json', 'Boundaries, levels of exceedance (deterministic, Monte Carlo, population paths), '
     'committed emissions and budgets', 'boundaries.py'),
    ('data/aesa/annual.csv', 'Annual carbon, boundaries and levels of exceedance by variant', 'boundaries.py'),
    ('data/aesa/montecarlo_annual.csv', 'Monte Carlo percentiles of carbon, boundaries and levels of exceedance by '
     'year', 'boundaries.py'),
    ('data/aesa/montecarlo_draw_budgets.csv', 'Each Monte Carlo draw of the Reference: carbon 2026-2050 and the '
     'cumulative AR and AtP budgets of that draw (read by pathways_mc.py)', 'boundaries.py'),
    ('data/aesa/sensitivity.csv', 'Every AESA sensitivity row: cumulative levels of exceedance', 'boundaries.py'),
    # data: pathways
    ('data/pathways/levers.json', 'Lever parameters and their sources', 'pathways.py'),
    ('data/pathways/runs.csv', 'Every pathway run: floor area, carbon, levels of exceedance, committed emissions',
     'pathways.py'),
    ('data/pathways/annual.csv', 'Annual carbon and boundaries of every pathway run', 'pathways.py'),
    ('data/pathways/bands.csv', 'Floor area and carbon by demand band of every pathway run', 'pathways.py'),
    ('data/pathways/shapley_*.csv', 'Shapley attribution (pathways, levers, theoretical limit) and its subsets',
     'pathways.py'),
    ('data/pathways/montecarlo_draws.csv', 'Pathway Monte Carlo: each saved Reference draw through P5 Combined '
     '(Moderate) and TL: inputs, carbon, floor area, budgets and levels of exceedance', 'pathways_mc.py'),
    ('data/pathways/montecarlo_summary.csv', 'Pathway Monte Carlo: percentiles of carbon, floor area and the levels '
     'of exceedance of the Reference, P5 and TL; P(LoE <= 1)', 'pathways_mc.py'),
    ('data/pathways/montecarlo_annual.csv', 'Pathway Monte Carlo: percentiles of annual carbon of the Reference, P5 '
     'and TL', 'pathways_mc.py'),
    ('data/pathways/backcast.json', 'Back-cast to LoE AR = 1 and the solution-space markers', 'pathways.py'),
    ('data/pathways/solution_space.csv', 'Cumulative LoE over the demand and intensity cuts (5% grid)',
     'pathways.py'),
    ('data/pathways/theoretical_limit.json', 'The theoretical limit TL: indicators, gap to the budgets, residual, '
     'solution-space marker', 'pathways.py'),
    # data: factors, metrics, frozen technology
    ('data/factors/factors_*.csv', 'Case-study carbon factors (materials, buildings, typologies, events, '
     'decarbonisation)', 'Building_factors.py'),
    ('data/metrics.json', 'The headline metrics of the run and the run mode', 'tools/metrics.py'),
    (f'data/{L.FROZEN}/*', 'The frozen-technology check run (2025 factors held): the same files as above',
     'run_all.py (frozen_* steps)'),
    # reports
    ('reports/RESULTS.md', 'Results summary', 'tools/results.py'),
    ('reports/ASSUMPTIONS.md', 'Every assumption and setting with its source', 'tools/assumptions.py'),
    ('reports/METHODS_DRAFT.md', 'Methods draft in three parts: baseline projection, planetary-boundary layer '
     '(AESA), pathways and the theoretical limit', 'tools/methods_draft.py'),
    ('reports/LEVERS_TABLE.md', 'The pathway levers, their settings and sources', 'tools/pathways_methods.py'),
    ('reports/validation.md', 'Validation report', 'validation.py'),
    ('reports/gap_2026.md', 'The 2026 gap', 'gap_2026.py'),
    ('reports/overbuild_2026.md', 'The 2026 overbuild', 'tools/overbuild_2026.py'),
    ('reports/scenarios.md', 'The projection variants', 'tools/replacement_scenarios.py'),
    ('reports/reality_checks.md', 'Reality checks: the projection against the 1991-2025 range',
     'tools/figures_report.py'),
    ('reports/reconciliation.md', 'Reconciliation of the totals', 'tools/reconciliation.py'),
    (f'reports/{L.FROZEN}_*.md', 'Report of the frozen-technology check run (2025 factors held)',
     'run_all.py (frozen_* steps)'),
    # audit and the index itself
    ('diagnostics/_audit/*.json', 'Audit record of a figure (headline and diagnostics): axes, year ranges, texts, note, '
     'drawing script (figaudit.py; read by the tests)', 'style.save_figure'),
    ('INDEX.md', 'This index', 'indexes.py'),
]
EXCLUDED = ('logs',)                    # console logs: git-ignored, not part of the release


def output_files():
    out = []
    for d, sub, files in os.walk(L.OUT):
        rel = os.path.relpath(d, L.OUT)
        if rel.split(os.sep)[0] in EXCLUDED:
            continue
        out += [os.path.normpath(os.path.join(rel, f)).replace(os.sep, '/') for f in files]
    return sorted(out)


def entry(rel):
    """The FILES entries a file matches."""
    return [e for e in FILES if fnmatch.fnmatch(rel, e[0])]


def audit(fid):
    p = os.path.join(L.FIGURE_AUDIT, f'{fid}.json')
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return json.load(f)


def diagnostics_md():
    lines = ['# Diagnostics', '',
             '_Generated by indexes.py from docs/FIGURE_PLAN.md and the figure audit records (do not edit by hand). '
             'Every figure: PNG 300 dpi, at most 183 mm wide (D06: single column, 89 mm), release style '
             '(docs/PALETTE.md) and vocabulary '
             '(docs/RENAMING.md). The figures of the paper are in ../headline/HEADLINE.md; the earlier file name of '
             'each figure is in docs/FIGURE_PLAN.md._', '']
    for group, rows in FP.DIAGNOSTICS.items():
        lines += [f'## {group.replace("_", " ").capitalize()}', '']
        for fid, content, _ in rows:
            a = audit(fid)
            lines += [f'### {fid[:3]}. {N.typeset(content)}', '', f'![{fid[:3]}]({group}/{fid}.png)', '']
            if a.get('note'):
                lines += [a['note'], '']
            lines += [f"File: [{group}/{fid}.png]({group}/{fid}.png); drawn by `{a.get('producer') or 'not drawn'}`.", '']
    path = L.writing(os.path.join(L.DIAGNOSTICS, 'DIAGNOSTICS.md'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path


def index_md():
    files = output_files()
    if 'INDEX.md' not in files:
        files.append('INDEX.md')
    rows = []
    for rel in sorted(files):
        m = entry(rel)
        rows.append((rel, m[0][1] if m else 'NOT INDEXED', m[0][2] if m else ''))
    lines = ['# Outputs', '',
             '_Generated by indexes.py (do not edit by hand): every file under outputs/ with what it holds and the '
             'script that writes it. Console logs (outputs/logs/) are not versioned. Data files use the release '
             'names of docs/RENAMING.md; their numbers are locked by tests/test_regression_model_v1.py._', '',
             '| file | content | written by |', '|---|---|---|']
    lines += [f'| `{r}` | {c} | {w} |' for r, c, w in rows]
    path = L.writing(os.path.join(L.OUT, 'INDEX.md'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    missing = [r for r, c, _ in rows if c == 'NOT INDEXED']
    return path, missing


def main():
    p = diagnostics_md()
    q, missing = index_md()
    print(f'indexes: {os.path.relpath(p, ROOT)}, {os.path.relpath(q, ROOT)}')
    if missing:
        raise SystemExit(f'indexes: files not in indexes.FILES: {missing}')


if __name__ == '__main__':
    main()
