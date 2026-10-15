"""
INDEXES (MODEL v3.0.0): the index of every output file (the figures: FIGURES.md, figures/index.py)
==================================================================================================
Writes, from the files the run produced (nothing is computed here):

  outputs/INDEX.md                    every file under outputs/ with one line on what it holds and
                                      which script writes it

FILES below is the registry of output files; main() stops the run (run_all.py step 'indexes') if a file under
outputs/ (except the git-ignored logs) matches no entry, so a new output cannot be added without being described.

    python indexes.py            (run_all.py runs it after the figures)
"""
import fnmatch
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import layout as L  # noqa: E402

# (pattern relative to outputs/, what it holds, the script that writes it)
FILES = [
    # paper (Fig1-Fig6, Tables 1-2), Extended Data (ED1-ED13) and key figures (K1-K6)
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
    ('data/baseline/bands_history_replacement_split.csv', 'The net replacement band of the history (census intervals) '
     'split into the census-measured net replacement and the unexplained building, in floor area (Fig2a)',
     'validation.py'),
    ('data/sensitivity/replacement_variants.csv', 'The Reference, P5 Combined (Moderate) and TL under Low / Reference '
     '/ High replacement: floor area, carbon, committed after 2050, cumulative LoE AR and AtP (ED10)',
     'tools/sensitivity_tables.py'),
    ('data/baseline/annual_by_stage.csv', 'Annual carbon of the Reference 2026-2050 by life-cycle stage (A1-A3, '
     'A4-A5, maintenance B2/B4, soil carbon loss) (Fig3)', 'projection.py'),
    ('data/baseline/annual_by_material.csv', 'Annual carbon of the Reference 2026-2050 by material (each with its '
     'maintenance within 2026-2050) and soil carbon loss (Fig3)', 'projection.py'),
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
    ('data/pathways/shapley*.csv', 'Exact Shapley values of every game (pathways, levers at Moderate / Ambitious / TL, TL1-TL9 from P5 Moderate) and every subset run',
     'pathways.py'),
    ('data/pathways/montecarlo_draws.csv', 'Pathway Monte Carlo: each saved Reference draw through P5 Combined '
     '(Moderate) and TL: inputs, carbon, floor area, budgets and levels of exceedance', 'pathways_mc.py'),
    ('data/pathways/montecarlo_summary.csv', 'Pathway Monte Carlo: percentiles of carbon, floor area and the levels '
     'of exceedance of the Reference, P5 and TL; P(LoE <= 1)', 'pathways_mc.py'),
    ('data/pathways/montecarlo_annual.csv', 'Pathway Monte Carlo: percentiles of annual carbon of the Reference, P5 '
     'and TL', 'pathways_mc.py'),
    ('data/pathways/montecarlo_draw_rules.json', 'Pathway Monte Carlo: draws where the L2 floor or the TL6 cap binds; '
     'the L2 target against the Monte Carlo High variant', 'pathways_mc.py'),
    ('data/pathways/montecarlo_importance.csv', 'Monte Carlo insight: SRC and PRCC of floor area, carbon and LoE AR of '
     'the Reference, P5 and TL, with bootstrap 95% intervals', 'pathways_mc.py'),
    ('data/pathways/montecarlo_fits.csv', 'Monte Carlo insight: LOWESS and least-squares curves of every input-output '
     'pair', 'pathways_mc.py'),
    ('data/pathways/montecarlo_conditional_tl.*', 'Monte Carlo insight: P(TL LoE AR <= 1) by the inputs (Firth '
     'logistic regression, quintiles, exceeding draws)', 'pathways_mc.py'),
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
    ('diagnostics/_audit/*.json', 'Audit record of a figure (paper, Extended Data and diagnostics): axes, year ranges, '
     'texts, note, drawing script, whether maintenance and the boundary styling are drawn (figaudit.py; read by the '
     'tests)', 'style.save_figure'),
    ('INDEX.md', 'This index', 'indexes.py'),
    # MODEL v3.0.0 figures and documents (figures/ package; figure_plan.py)
    ('FIGURES.md', 'Every figure with its file, data sources, caption and run-specific note', 'figures/index.py'),
    ('run_meta.json', 'Run metadata: profile, draws, seeds, git hash, input hash, timestamp, step timings', 'run_all.py'),
    ('paper_main/Fig*.png', 'Main-paper figure, PNG (profile dpi; FIGURES.md)', 'figures/paper_main.py'),
    ('paper_main/Fig*.pdf', 'Main-paper figure, vector PDF (full profile)', 'figures/paper_main.py'),
    ('paper_extended/ED*.png', 'Extended Data figure, PNG (profile dpi; FIGURES.md)', 'figures/paper_extended.py'),
    ('paper_extended/ED*.pdf', 'Extended Data figure, vector PDF (full profile)', 'figures/paper_extended.py'),
    ('paper_extended/EDT1_levels_by_typology.*', 'Extended Data table: lever levels by typology (Moderate, Ambitious, '
     'TL)', 'figures/paper_extended.py'),
    ('diagnostics/*/D*.png', 'Diagnostic figure, PNG (FIGURES.md)', 'figures/ (module named in FIGURES.md)'),
    ('diagnostics/*/D*.pdf', 'Diagnostic figure, vector PDF (full profile)', 'figures/ (module named in FIGURES.md)'),
    ('data/figure_source/*.json', 'Figure source data: the exact arrays a diagnostic draws (figsource.py)',
     'projection.py, Diagnostics.py, boundaries.py, tools/figures_report.py'),
    ('data/baseline/overbuild_absorption_log.csv', 'The 2026 overbuild in the Reference by year: excess, cumulative '
     'excess, absorption weight, target surplus and payback, payback paid and carried, surplus vacant, implied vacancy',
     'projection.py'),
    ('data/montecarlo/convergence_*.csv', 'Monte Carlo convergence: percentiles over the first n draws', 'MonteCarlo.py'),
    ('data/montecarlo/input_distributions_*.csv', 'Monte Carlo input distributions: quantiles and sample moments',
     'MonteCarlo.py'),
    ('data/pathways/waterfall.csv', 'Sequential waterfall Reference -> P1 ... P4 (= P5) -> TL1 ... TL9 (= TL) by demand '
     'band, Moderate and Ambitious', 'pathways.py'),
    ('data/pathways/bands_annual.csv', 'In-scope demand bands by year of every Reference-variant run', 'pathways.py'),
    ('data/pathways/lambda_sweep.csv', 'Lambda-sweep of each lever (Reference 0, Moderate 0.5, Ambitious 1) and TL',
     'pathways.py'),
    ('data/pathways/lever_annual.csv', 'Annual carbon of each lever alone at Reference, Moderate, Ambitious and TL',
     'pathways.py'),
    ('data/pathways/reoccupation_log.csv', 'TL and instant TL by year: need, releases (TL3, TL4), share, re-occupied, '
     'binding years, built', 'pathways.py'),
    ('data/pathways/ordering_checks.json', 'Ordering Reference >= Moderate >= Ambitious >= TL per lever, typology and '
     'year (violations, annual-carbon reversals, cumulative ordering)', 'pathways.py'),
    ('data/sensitivity/tornado.csv', 'Fig7: the eight inputs of the Reference tornado (low / high): carbon, LoE AR and AtP',
     'tools/sensitivity_tables.py'),
    ('data/sensitivity/accounting_rules.csv', 'MODEL v3.1.0: the three emissions accounting rules (inventory, instant, '
     'cohort_window): AR base split, AR and AtP budgets, Reference split incl. legacy, soil after 2050, LoE of the '
     'Reference, P5 Moderate / Ambitious and TL, Monte Carlo share of TL within AR', 'tools/accounting_rules.py'),
]

# console logs, and the light-profile and legacy-Reference mirrors (outputs/_light/, outputs/_legacy/): git-ignored,
# not part of the release
EXCLUDED = ('logs', '_light', '_legacy')


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
             'names of docs/RENAMING.md; the deterministic numbers are locked by tests/test_regression_model_v3.py, the '
             'Monte Carlo by its hash lock._', '',
             '| file | content | written by |', '|---|---|---|']
    lines += [f'| `{r}` | {c} | {w} |' for r, c, w in rows]
    path = L.writing(os.path.join(L.OUT, 'INDEX.md'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    missing = [r for r, c, _ in rows if c == 'NOT INDEXED']
    return path, missing


def main():
    q, missing = index_md()
    print(f'indexes: {os.path.relpath(q, ROOT)}')
    if missing:
        raise SystemExit(f'indexes: files not in indexes.FILES: {missing}')


if __name__ == '__main__':
    main()
