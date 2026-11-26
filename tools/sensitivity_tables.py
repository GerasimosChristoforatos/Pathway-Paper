"""Grouped one-at-a-time sensitivity tables.

    python tools/sensitivity_tables.py         (run_all.py runs it after the pathway Monte Carlo)

Writes outputs/data/sensitivity/:
  reference_carbon.csv     Reference carbon 2026-2050, rows grouped by type of change (D16; ED8)
  pathway_carbon.csv       the Moderate Pathway (every lever at Moderate)
                           carbon 2026-2050 and its levels of exceedance, pathway design rows (D41)
  planetary_boundary.csv   cumulative LoE AR and AtP of the Reference (D42; ED7)
  replacement_variants.csv the Reference, the Moderate / Ambitious Pathway and TL under Low / Reference / High / Very
                           High replacement (ED5)
  household_size.csv       the Reference, the Moderate / Ambitious Pathway and TL under the household-size
                           sensitivities (Stats NZ Medium B: living-arrangement propensities change; 2018-2023
                           census pace, linear from 2023)
  tl_sensitivity.csv       the Theoretical Limit sensitivities (every other lever at TL; Supplementary Table 13; the L10
                           rows also in ED8 panel b), deterministic and with the pathway Monte Carlo P(LoE AR <= 1)
  tornado.csv              Fig7a: the inputs of the Reference tornado (low / high), cumulative carbon and the
                           cumulative LoE AR and AtP (the budgets move only with the population path)

Every row has its group, the row label, its side (low / high / single), the value, the change vs the
central case and its basis. Rows are read from existing outputs; the only new runs are the Moderate Pathway rows
with one lever (L1-L10) at Ambitious (the others Moderate) and the Pathway on the Stats NZ 5th / 95th population
paths (exact engine path: the projection's own percentile run, reproduced to 1e-12 before the levers
are applied; the AR and AtP budgets move with the path, data/aesa/results.json population_paths), and
TL under the replacement variants (every other run of that table reproduces runs.csv to 1e-12).
One-at-a-time ranges are not additive and are not a joint interval.
"""
import contextlib
import io
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine  # noqa: E402
import layout  # noqa: E402
import levers as LV  # noqa: E402
import naming as N  # noqa: E402
import boundaries as BD  # noqa: E402
import validation  # noqa: E402

M6 = 1e6


def data(rel):
    return layout.data(rel)


# ---- 1. Reference carbon -----------------------------------------------------------------------
# (group, row label, side, case in sensitivity_one_at_a_time.csv, basis)
REF_ROWS = [
    ('Demographics', 'Population: Stats NZ 5th / 95th percentile', 'low', 'Population: Stats NZ 5th percentile (engine path)',
     'DATA: Stats NZ 2024-base stochastic projection; exact engine path'),
    ('Demographics', 'Population: Stats NZ 5th / 95th percentile', 'high', 'Population: Stats NZ 95th percentile (engine path)',
     'DATA: Stats NZ 2024-base stochastic projection; exact engine path'),
    ('Demographics', 'Living arrangements: propensities change (Stats NZ B)', 'single',
     'Living arrangements: propensities change (Stats NZ Medium B)',
     'DATA: Stats NZ 2023-base family and household projections, propensity B (change modelled on the 2001-2023 '
     'censuses) instead of A (held at 2023)'),
    ('Demographics', 'Household size: 2018-2023 census pace', 'single',
     'Household size: 2018-2023 census pace, linear from 2023',
     'DATA: census-benchmarked households 2018 and 2023; linear continuation (JUDGEMENT)'),
    ('Demographics', 'After 2048: held flat (zero slope)', 'single', 'Household size after 2048: held flat (zero slope)',
     'JUDGEMENT: post-2048 tail (the Stats NZ series ends in 2048); the end-slope rule'),
    ('Demographics', 'After 2048: PCHIP end slope', 'single', 'Household size after 2048: PCHIP end slope',
     'JUDGEMENT: post-2048 tail'),
    ('Housing stock & calibration', 'Completion rate 0.93 / 0.96', 'low', 'Completion rate 0.93',
     'LITERATURE: Greenaway-McGrevy & Jones 2023; Jones, Greenaway-McGrevy & Crow 2025 (Policy Quarterly 21(1)); 93% final inspection / >95% first inspection'),
    ('Housing stock & calibration', 'Completion rate 0.93 / 0.96', 'high', 'Completion rate 0.96',
     'LITERATURE: Greenaway-McGrevy & Jones 2023; Jones, Greenaway-McGrevy & Crow 2025 (Policy Quarterly 21(1)); 93% final inspection / >95% first inspection'),
    ('Housing stock & calibration', 'Completion rate 0.95', 'single', 'Completion rate 0.95',
     'DECISION: a rounded completion rate (the authors\' own assumption; central 0.945)'),
    ('Completion lag', 'Completion lag 15 / 19 months', 'low', 'Completion lag 15 months',
     'LITERATURE: median consent-to-completion time 1.27-1.53 yr (Jones, Greenaway-McGrevy & Crow 2025, citing Greenaway-McGrevy & Jones 2023)'),
    ('Completion lag', 'Completion lag 15 / 19 months', 'high', 'Completion lag 19 months',
     'LITERATURE: median consent-to-completion time 1.27-1.53 yr (Jones, Greenaway-McGrevy & Crow 2025, citing Greenaway-McGrevy & Jones 2023)'),
    ('Completion lag', 'Completion lag 0 months', 'single',
     'Completion lag 0 months (same calendar year)', 'DECISION: the same-year timing bound'),
    ('Completion lag', 'No 2026 data', 'single',
     'No 2026 data (consents to December 2025, projected 2026 population)',
     'CHECK: out-of-sample run without 2026 consents or the 2026 population nowcast'),
    ('Housing stock & calibration', 'No census under-construction correction', 'single',
     'No census under-construction correction', 'DATA: census under-construction counts'),
    ('Housing stock & calibration', 'Dwelling-size window 2016-2025', 'single', 'Dwelling size: 2016-2025 reference',
     'DATA: consents'),
    ('Housing stock & calibration', '2026 overbuild absorbed by 2030 / by 2045', 'low', 'Overbuild absorbed by 2030',
     'THEORY: reversion to the equilibrium vacancy (Rosen & Smith 1983; Wheaton 1990; DiPasquale & Wheaton 1992; '
     'Gabriel & Nothaft 2001) fixes the direction, not the speed; speed bracketed'),
    ('Housing stock & calibration', '2026 overbuild absorbed by 2030 / by 2045', 'high', 'Overbuild absorbed by 2045',
     'THEORY: as above; adopted 2035 (the common RECC window)'),
    ('Housing stock & calibration', 'No starting surplus', 'single', 'No starting surplus',
     'RULE (fixed in advance, F1): the 2024-2025 stock-identity residual exceeds the 1992-2023 census-interval mean + '
     '2 SD, so the excess is carried (adopted); this row carries none'),
    ('Housing stock & calibration', 'Starting surplus minus 2 SD', 'single', 'Starting surplus minus 2 SD',
     'RULE (F1): only the excess above the mean + 2 SD band carried'),
    ('Housing stock & calibration', '2026 overbuild never absorbed', 'single',
     'Overbuild never absorbed', 'DECISION: the permanent-surplus bound'),
    ('Housing stock & calibration', 'Vacancy parameter: 1986-2023 census mean (one definition)', 'single',
     'Vacancy parameter: 1986-2023 census mean, one definition', 'DATA: Stats NZ censuses 1986-2023'),
    ('Housing stock & calibration', '2026 overbuild booked as stock-neutral redevelopment', 'single',
     'Booked as redevelopment, stock-neutral', 'DECISION (author): booking of observed 2026 building'),
    ('Housing stock & calibration', '2026 overbuild gap vs the 2026 requirement', 'single',
     'Gap measured against the same-year requirement', 'DECISION (author): rule variant'),
    ('Replacement scenario', 'Low / High replacement', 'low', 'Low replacement: long-run rate',
     'DATA: 1991-2023 long-run rate'),
    ('Replacement scenario', 'Low / High replacement', 'high', 'High replacement: 2018-2023 rate persists',
     'DATA: 2018-2023 census-interval rate'),
    ('Replacement scenario', 'Very High replacement (trend continues)', 'single',
     'Very High replacement: 1991-2023 census trend continues',
     'DATA / JUDGEMENT: interval-length-weighted OLS trend of the census-interval rates 1991-2023, extrapolated '
     '(sensitivity, not adopted)'),
    ('Replacement scenario', 'Replacement half-life 5 / 15 yr', 'low', 'Reference, replacement half-life 5 yr',
     'JUDGEMENT: the half-life is not identifiable from the census record (sampled U(5, 15) yr in the Monte Carlo)'),
    ('Replacement scenario', 'Replacement half-life 5 / 15 yr', 'high', 'Reference, replacement half-life 15 yr',
     'JUDGEMENT: the half-life is not identifiable from the census record (sampled U(5, 15) yr in the Monte Carlo)'),
    ('Carbon factors & technology', 'Single case study: lowest / highest', 'low', 'Materials: lowest single case study',
     'DATA: 16 NZ case studies (Christoforatos & Pickering 2026)'),
    ('Carbon factors & technology', 'Single case study: lowest / highest', 'high', 'Materials: highest single case study',
     'DATA: 16 NZ case studies (Christoforatos & Pickering 2026)'),
    ('Carbon factors & technology', 'Case studies: jackknife low / high', 'low', 'Materials: jackknife low (all typologies)',
     'DATA: the case studies, leave-one-out'),
    ('Carbon factors & technology', 'Case studies: jackknife low / high', 'high',
     'Materials: jackknife high (all typologies)', 'DATA: the case studies, leave-one-out'),
    ('Carbon factors & technology', 'Frozen technology (2025 factors held)', 'single',
     'Frozen technology: 2025 factors held (no decarbonisation)', 'DECISION: the no-decarbonisation bound'),
    ('Carbon factors & technology', 'Decarbonisation: proxy-mapped items held', 'single',
     'Decarbonisation: proxy-mapped items held at 2025', 'LITERATURE: Horup et al. 2025 S4 mapping; DECISION'),
    ('Carbon factors & technology', 'Decarbonisation: NZ-made electricity-intensive items held', 'single',
     'Decarbonisation: NZ-made electricity-intensive items held at 2025', 'LITERATURE: Horup et al. 2025; DECISION'),
    ('Carbon factors & technology', 'Soil order: lowest (Raw) / highest (Organic)', 'low',
     'Soil carbon: lowest soil order (Raw)', 'LITERATURE: Christoforatos, Pickering & Schipper 2026'),
    ('Carbon factors & technology', 'Soil order: lowest (Raw) / highest (Organic)', 'high',
     'Soil carbon: highest soil order (Organic)', 'LITERATURE: Christoforatos, Pickering & Schipper 2026'),
    ('Carbon factors & technology', "A4-A5 on each item's own path / held at 2025", 'low',
     "A4-A5 on each item's own Horup path", 'LITERATURE: Horup et al. 2025'),
    ('Carbon factors & technology', "A4-A5 on each item's own path / held at 2025", 'high',
     'A4-A5 held at 2025 (no generic 1%/yr)', 'LITERATURE: Resch et al. 2021 (adopted generic path) vs held'),
    ('Carbon factors & technology', 'Soil carbon loss on all floor area, including replacement', 'single',
     'Soil on all floor area, incl. replacement', 'DECISION (author): no soil loss on rebuilt footprints (adopted)'),
    ('Carbon factors & technology', 'Module D credit, booked at construction (not netted)', 'single', 'Module D credit at 2025 factors, booked at construction (not netted)',
     'EN 15978 Module D (benefits beyond the system boundary), excluded from the model; the 2025 factors (the largest '
     'credit); carbon only, not converted to LoE'),
    ('Carbon factors & technology', 'Production decarbonisation: no-climate-policy backgrounds (Horup MAX)', 'single',
     'Production decarbonisation: no-climate-policy backgrounds (Horup MAX), A1-A3 x MAX / average path',
     'LITERATURE: Horup et al. 2025 Table S3, the maximum of the 9 prospective backgrounds (no climate policy) '
     'relative to their average, applied to the A1-A3 of construction and of the in-window events as lever L10; '
     'carbon only, not converted to LoE'),
    ('Accounting', 'Event timing L / n', 'single', 'Event timing: interval L / n', 'DECISION: maintenance timing'),
]
# rows reported in carbon only (ED8), never converted to a level of exceedance: they need no AR-base rule
# (boundaries.AR_BASE_RULE) and must not enter TORNADO. Module D: a consistent LoE would need Module D in the
# historical sector base as well. Production decarbonisation (Horup MAX): a carbon-factor path, shown as
# the carbon range of lever L10's evidence.
CARBON_ONLY_ROWS = ('Module D credit, booked at construction (not netted)',
                    'Production decarbonisation: no-climate-policy backgrounds (Horup MAX)')


def reference_table():
    oat = pd.read_csv(data('baseline/sensitivity_one_at_a_time.csv'))
    ann = pd.read_csv(data('baseline/sensitivity_annual_carbon.csv'))
    tot = ann.groupby('case')['carbon_kt'].sum()
    c0 = float(oat.loc[oat['case'] == 'Reference (adopted settings)', 'carbon_kt'].iloc[0])
    rows = []
    for g, lab, side, case, basis in REF_ROWS:
        if case in set(oat['case']):
            v = float(oat.loc[oat['case'] == case, 'carbon_kt'].iloc[0])
        else:                                          # the engine-path population rows (annual file)
            v = float(tot.loc[case])
        rows.append(dict(group=g, row=lab, side=side, case=case, carbon_kt=v, central_carbon_kt=c0,
                         change_pct=100 * (v / c0 - 1), basis=basis))
    return pd.DataFrame(rows)


# ---- 2. Moderate Pathway carbon (pathway design) ---------------------------------------------------
PARAMS = {}
HH_TABLE = {}


def percentile_context(PW, B, pct, bounds):
    """The pathway context of the projection's own population percentile run (pop, households and the
    2026 overbuild of that path; every other input as the Reference); reproduces engine_out[pct]."""
    ctx = PW.base_context(B, PW.REFERENCE, bounds)
    ctx['P'] = PARAMS['p']
    df, ji = B['df_forecast'], B['join_info'][pct]
    pop = df[f'PopTotal_{pct}'].values
    growth = df[f'PopGrowth_{pct}'].clip(lower=0).values
    hh = B['households_forecast'][pct]
    fi = ctx['fwd_inputs']
    E = engine.forward(pop, hh, growth, join=ji['join'], join_redev=ji['redev'],
                       stock_start=float(ji.get('start_surplus', 0.0)), **fi)
    ref = B['engine_out'][pct]
    for k in ('carbon', 'total'):
        if not np.allclose(np.asarray(E[k], float)[1:], np.asarray(ref[k], float)[1:], rtol=1e-12, atol=0):
            raise SystemExit(f'sensitivity_tables: the {pct} population context does not reproduce the projection ({k}).')
    ctx.update(pop=pop, growth=growth, hh=hh, excess=np.asarray(ji['excess'], float).copy(),
               join_reference=np.asarray(ji['join'], float))
    if not np.allclose(np.asarray(PW.run(ctx, ctx['P'], {})['E']['carbon'], float)[1:],
                       np.asarray(ref['carbon'], float)[1:], rtol=1e-12, atol=0):
        raise SystemExit(f'sensitivity_tables: the {pct} pathway run does not reproduce the projection.')
    return ctx


def pathway_table():
    import pathways as PW
    runs = pd.read_csv(data('pathways/runs.csv'))
    with open(data('aesa/results.json')) as f:
        aesa = json.load(f)
    pp = aesa['population_paths']
    B = PW.boss_state(PW.REFERENCE)
    bounds = PW.boundaries()
    ctx = PW.base_context(B, PW.REFERENCE, bounds)
    params = PARAMS.setdefault('p', PW.resolve_params(B))
    bar, batp = float(ctx['b_ar'].sum()) / M6, float(ctx['b_atp'].sum()) / M6

    def run_row(scen, name):
        r = runs[(runs['scenario'] == scen) & (runs['run'] == name)].iloc[0]
        return float(r['carbon_kt']), float(r['LoE_AR']), float(r['LoE_AtP'])

    PM_, PA_ = f'{LV.PATHWAY}-moderate', f'{LV.PATHWAY}-ambitious'
    c0, a0, t0 = run_row('REF', PM_)
    rows = []

    def add(group, label, side, carbon, loe_ar, loe_atp, source, basis):
        key = group if group in BD.AR_BASE_RULE else label
        if BD.ar_base_rule(key)[0] != BD.REFERENCE_BASE:           # these rows use the Reference (or path) budgets
            raise SystemExit(f'sensitivity_tables: pathway row {key!r} is classified {BD.ar_base_rule(key)[0]!r}.')
        rows.append(dict(group=group, row=label, side=side, carbon_kt=carbon, LoE_AR=loe_ar, LoE_AtP=loe_atp,
                         central_carbon_kt=c0, central_LoE_AR=a0, central_LoE_AtP=t0,
                         change_pct=100 * (carbon / c0 - 1), source=source, basis=basis))

    base = LV.pathway_levers(LV.PATHWAY, 'moderate')
    cc = float(np.asarray(PW.run(ctx, params, base)['E']['carbon'], float)[1:].sum()) / M6
    if not np.isclose(cc, c0, rtol=1e-12, atol=0):     # the context reproduces the adopted Moderate Pathway run
        raise SystemExit(f'sensitivity_tables: the Moderate Pathway {cc} kt does not reproduce runs.csv {c0} kt.')
    tags = {L: f"sub-rule {LV.SUBRULE[L]}" for L in LV.LEVERS}
    for L in LV.LEVERS:                                      # one lever at Ambitious, the others Moderate
        E = PW.run(ctx, params, dict(base, **{L: 'ambitious'}))['E']
        c = float(np.asarray(E['carbon'], float)[1:].sum()) / M6
        add('Ambition of one lever', f"{L} {N.LEVERS[L]} at Ambitious", 'single', c, c / bar, c / batp,
            'new run (tools/sensitivity_tables.py)', f"{tags[L]}: the Ambitious setting of {L}")
    add('Ambition of all', N.PATHWAY_RUNS[PA_], 'single', *run_row('REF', PA_),
        'data/pathways/runs.csv', 'DECISION (author): every lever at Ambitious')
    for side, nm in (('low', f'{PM_}-by2030'), ('high', f'{PM_}-by2045')):
        add('Roll-out timing', 'Full roll-out by 2030 / by 2045', side, *run_row('REF', nm), 'data/pathways/runs.csv',
            'LITERATURE: RECC (Pauliuk et al. 2024) adopted 2035; the adoption-window rule')
    add('Theoretical limit', 'TL (every lever at Level 4)', 'single', *run_row('REF', 'TL'), 'data/pathways/runs.csv',
        'DECISION (author): Level 4 of every lever')
    for side, sc in (('low', 'LOW'), ('high', 'HIGH')):
        add('Replacement scenario', 'Low / High replacement', side, *run_row(sc, PM_),
            'data/pathways/runs.csv', 'DATA: long-run rate / 2018-2023 rate persists')
    add('Replacement scenario', N.SCENARIOS['VHIGH'], 'single', *run_row('VHIGH', PM_), 'data/pathways/runs.csv',
        'DATA / JUDGEMENT: the 1991-2023 census trend continues (sensitivity, not adopted)')
    hs = HH_TABLE.get('t')
    if hs is not None:                                   # the household-size rows (household_size.csv)
        for _, r in hs[hs['run'] == PM_].iterrows():
            add('Demographics', r['row'], r['side'], r['carbon_kt'], r['LoE_AR'], r['LoE_AtP'],
                'sensitivity/household_size.csv (new run)', r['basis'])
    for side, pct in (('low', '5th'), ('high', '95th')):
        cp = percentile_context(PW, B, pct, bounds)
        E = PW.run(cp, params, base)['E']
        c = float(np.asarray(E['carbon'], float)[1:].sum()) / M6
        add('Demographics', 'Population: Stats NZ 5th / 95th percentile', side, c, c / pp[pct]['B_AR_kt'],
            c / pp[pct]['B_AtP_kt'], 'new run (exact engine path; budgets move with the path)',
            'DATA: Stats NZ 2024-base stochastic projection')
    return pd.DataFrame(rows)


# ---- 2b. Household-size sensitivities of the Reference, the Pathways and TL ---------------------
HH_VARIANTS = [   # (row, side, projection settings)
    ('Living arrangements: propensities change (Stats NZ B)', 'single', dict(HH_PROPENSITY='B')),
    ('Household size: 2018-2023 census pace', 'single', dict(HH_SIZE_PATH='census_pace')),
]
HH_BASIS = {'Living arrangements: propensities change (Stats NZ B)': 'DATA: Stats NZ 2023-base family and household '
                                                                    'projections, Medium B (living-arrangement '
                                                                    'propensities change) instead of Medium A',
            'Household size: 2018-2023 census pace': 'DATA: census-benchmarked households 2018 and 2023; linear '
                                                     'continuation from 2023 (JUDGEMENT)'}


def household_size_table():
    """The Reference, the Moderate / Ambitious Pathway and TL under the household-size sensitivities (deterministic):
    each run on the projection state with the household-size setting changed, the lever parameters of the central
    state (as the Monte Carlo: the run's own Reference household size plus the central gap; TL1 speed limit from the
    run's own 2026 household size). The population path, and so the AR / AtP budgets, are those of the Reference."""
    import pathways as PW
    runs = pd.read_csv(data('pathways/runs.csv'))
    bounds = PW.boundaries()
    B_ref = PW.boss_state(PW.REFERENCE)
    params = PARAMS.setdefault('p', PW.resolve_params(B_ref))
    plan = (('Reference', 'REF', {}), (f'{LV.PATHWAY}-moderate', None, LV.pathway_levers(LV.PATHWAY, 'moderate')),
            (f'{LV.PATHWAY}-ambitious', None, LV.pathway_levers(LV.PATHWAY, 'ambitious')),
            ('TL', None, LV.tl_levels(LV.TL_COMPONENTS)))
    central = {run: runs[(runs['scenario'] == 'REF') & (runs['run'] == (key or run))].iloc[0] for run, key, _ in plan}
    rows = []
    for row, side, settings in HH_VARIANTS:
        if BD.ar_base_rule(row)[0] != BD.REFERENCE_BASE:           # the Reference budgets are used below
            raise SystemExit(f'sensitivity_tables: {row!r} is not classified {BD.REFERENCE_BASE!r}.')
        with contextlib.redirect_stdout(io.StringIO()):
            B = validation.run_boss(**dict(PW.SCENARIOS[PW.REFERENCE][1], **settings))
        ctx = PW.base_context(B, PW.REFERENCE, bounds)
        for run, _, levels in plan:
            m = PW.metrics(ctx, PW.run(ctx, params, levels), run, 'sensitivity')
            c0 = central[run]
            rows.append(dict(row=row, side=side, settings=json.dumps(settings), run=run, carbon_kt=float(m['carbon_kt']),
                             LoE_AR=float(m['LoE_AR']), LoE_AtP=float(m['LoE_AtP']),
                             central_carbon_kt=float(c0['carbon_kt']), central_LoE_AR=float(c0['LoE_AR']),
                             central_LoE_AtP=float(c0['LoE_AtP']),
                             change_pct=100 * (float(m['carbon_kt']) / float(c0['carbon_kt']) - 1),
                             dwellings_built_min_year=float(m['dwellings_built_min_year']),
                             mean_household_size_2050=float(m['mean_household_size_2050']), basis=HH_BASIS[row]))
    return pd.DataFrame(rows)


# ---- 3. Planetary boundary --------------------------------------------------------------------------
PB_ROWS = [
    ('Carrying capacity', 'SOS / I_glob pair C: 1 W/m² planetary boundary', 'single', 'i_source_pair',
     'LITERATURE: Bjørn & Hauschild 2015'),
    ('Global impact', 'Global impact: EF 3.1', 'single', 'i_glob_ef31', 'LITERATURE: Andreasi Bassi et al. 2023'),
    ('Base window', 'AR base window 2021-2025 (5 yr, as Horup)', 'single', 'iii_base_window', 'LITERATURE: Horup et al. 2025'),
    ('Base window', 'AR base window 2006-2025 (20 yr)', 'single', 'iii_base_window_20', 'DECISION (author)'),
    ('Base window', 'AR base window 1992-2025 (full consistent history)', 'single', 'iii_base_window_full',
     'DECISION (author)'),
    ('Economic measures', 'GDP per capita in current US$', 'single', 'ii_gdp_measure', 'DATA: World Bank WDI'),
    ('Economic measures', 'α = 1 (Hjalsted et al. SI tables)', 'single', 'xiv_alpha_1', 'LITERATURE: Hjalsted et al. 2021'),
    ('Economic measures', 's_sec with the FCE share as a ratio of sums', 'single', 'v_ssec', 'DECISION (author)'),
    ('Population source', 'NZ population: raw Stats NZ 2024-base median', 'single', 'iv_pop_statsnz', 'DATA: Stats NZ'),
    ('Population source', 'NZ population: WPP 2024 median', 'single', 'iv_pop_wpp', 'DATA: UN WPP 2024'),
]


LATE_WINDOW = (2028, 2050)
LATE_RUNS = (('Reference', 'REF'), ('Moderate Pathway', 'pathway-moderate'), ('Ambitious Pathway', 'pathway-ambitious'),
             ('Theoretical Limit', 'TL'))


def loe_2028_2050():
    """loe_2028_2050.csv: the cumulative LoE of AR and AtP over 2028-2050 (carbon and budget both summed over the
    window; pipeline years 2026-2027 excluded; the AR base unchanged) of the Reference, the Pathways and TL
    (pathways/annual.csv, scenario REF). Supplementary Table 10, with the runs table."""
    a = pd.read_csv(data('pathways/annual.csv'))
    a = a[(a['scenario'] == 'REF') & (a['year'] >= LATE_WINDOW[0]) & (a['year'] <= LATE_WINDOW[1])]
    rows = []
    for name, run in LATE_RUNS:
        g = a[a['run'] == run]
        rows.append(dict(run=name, run_id=run, years=f'{LATE_WINDOW[0]}-{LATE_WINDOW[1]}',
                         carbon_kt=float(g['carbon_kt'].sum()), B_AR_kt=float(g['B_AR_kt'].sum()),
                         B_AtP_kt=float(g['B_AtP_kt'].sum()), LoE_AR=float(g['carbon_kt'].sum() / g['B_AR_kt'].sum()),
                         LoE_AtP=float(g['carbon_kt'].sum() / g['B_AtP_kt'].sum())))
    return pd.DataFrame(rows)


# ---- 3b. Theoretical Limit sensitivities (Supplementary Table 13; ED8 b) -----------------------------
# (run id in runs.csv, Monte Carlo run in montecarlo_draws.csv or None, row label, shown in the Extended Data, basis)
TL_ROWS = [
    ('TL', 'TL', 'Theoretical Limit (central)', True, 'every lever at Level 4 (levers.TL_RULE)'),
    ('TL-L10-all-classes', 'TL_L10_all_classes', LV.L10_TL_VARIANTS['all_classes']['label'], True,
     LV.L10_TL_VARIANTS['all_classes']['basis']),
    ('TL-L10-share-100', 'TL_L10_share_100', LV.L10_TL_VARIANTS['share_100']['label'], True,
     LV.L10_TL_VARIANTS['share_100']['basis']),
    ('TL-L1-by-age', 'TL_L1_by_age', 'L1 at TL: lowest observed census headship by age', False,
     'the lowest observed census headship of each age group (2013-2023), or the Stats NZ propensity-B rate where '
     'lower, on the projected age structure; the speed limit and never below L1 Ambitious (household_headship.py)'),
    ('TL-from2027', 'TL_from2027', 'Instant TL (every level from 2027)', False, 'no adoption window'),
    ('TL-reoccupation-fast', None, 'Re-occupation as fast as demand allows', False,
     'the re-occupation pool meets each year\'s need as far as it can (deterministic only)')]


def tl_sensitivity():
    """tl_sensitivity.csv: the Theoretical Limit sensitivities (every other lever at TL), deterministic
    (pathways/runs.csv) and P(LoE AR <= 1) over the pathway Monte Carlo draws with its Wilson 95% interval."""
    import mcstats
    r = pd.read_csv(data('pathways/runs.csv'))
    r = r[r['scenario'] == 'REF'].set_index('run')
    d = pd.read_csv(data('pathways/montecarlo_draws.csv'))
    c0 = float(r.loc['TL', 'carbon_kt'])
    rows = []
    for run, mc, label, ed, basis in TL_ROWS:
        x = r.loc[run]
        row = dict(run=run, row=label, extended_data=ed, carbon_kt=float(x['carbon_kt']), LoE_AR=float(x['LoE_AR']),
                   LoE_AtP=float(x['LoE_AtP']), change_vs_TL_pct=100.0 * (float(x['carbon_kt']) / c0 - 1.0),
                   P_LoE_AR_at_most_1=np.nan, wilson_lo=np.nan, wilson_hi=np.nan, n_draws=0, basis=basis)
        if mc is not None:
            v = d[f'{mc}_LoE_AR'].to_numpy(float)
            k, n = int((v <= 1.0).sum()), len(v)
            lo, hi = mcstats.wilson(k, n)
            row.update(P_LoE_AR_at_most_1=k / n, wilson_lo=lo, wilson_hi=hi, n_draws=n)
        rows.append(row)
    return pd.DataFrame(rows)


def pb_table():
    s = pd.read_csv(data('aesa/sensitivity.csv')).set_index('case')
    with open(data('aesa/results.json')) as f:
        r = json.load(f)
    ref = s.loc['reference']
    a0, t0 = float(ref['cum_LoE_AR']), float(ref['cum_LoE_AtP'])
    rows = []

    def add(group, label, side, ar, atp, source, basis, key=None):
        BD.ar_base_rule(key or label)                                # STOP on a row that is not classified
        rows.append(dict(group=group, row=label, side=side, LoE_AR=ar, LoE_AtP=atp, central_LoE_AR=a0,
                         central_LoE_AtP=t0, change_AR_pct=100 * (ar / a0 - 1), change_AtP_pct=100 * (atp / t0 - 1),
                         source=source, basis=basis))

    for g, lab, side, case, basis in PB_ROWS:
        add(g, lab, side, float(s.loc[case, 'cum_LoE_AR']), float(s.loc[case, 'cum_LoE_AtP']),
            f'data/aesa/sensitivity.csv ({case})', basis, key=case)
    for side, pct in (('low', '5th'), ('high', '95th')):
        p = r['population_paths'][pct]
        add('Population source', 'Population: Stats NZ 5th / 95th percentile (carbon and boundaries together)', side,
            p['LoE_AR'], p['LoE_AtP'], 'data/aesa/results.json population_paths', 'DATA: Stats NZ stochastic projection',
            key='Population: Stats NZ 5th / 95th percentile')
    for lab, pair in (('Low / High replacement', ('LOW', 'HIGH')), ('Replacement half-life 5 / 15 yr', ('REF_HL5', 'REF_HL15'))):
        for side, k in zip(('low', 'high'), pair):
            d = r['deterministic'][k]
            add('Replacement scenario', lab, side, d['LoE_AR'], d['LoE_AtP'], f'data/aesa/results.json deterministic ({k})',
                'DATA / JUDGEMENT (replacement variants)')
    # the summation window: carbon and budget both summed over 2028-2050 (the pipeline years excluded), the AR base
    # unchanged; and whole-life accounting (committed emissions after 2050 counted at construction, base recomputed)
    lt = loe_2028_2050()
    ref28 = lt[lt['run'] == 'Reference'].iloc[0]
    add('Summation window', '2028-2050 only (pipeline years excluded)', 'single', float(ref28['LoE_AR']),
        float(ref28['LoE_AtP']), 'data/loe_2028_2050.csv (Reference)', 'DECISION (author): the window without the '
        'observed pipeline years 2026-2027', key='window_2028_2050')
    add('Accounting', 'Whole-life accounting (committed emissions at construction)', 'single',
        float(s.loc['xii_whole_life', 'cum_LoE_AR']), float(s.loc['xii_whole_life', 'cum_LoE_AtP']),
        'data/aesa/sensitivity.csv (xii_whole_life)', 'DECISION (author): the static convention, base recomputed',
        key='xii_whole_life')
    d = r['deterministic']['VHIGH']
    add('Replacement scenario', N.SCENARIOS['VHIGH'], 'single', d['LoE_AR'], d['LoE_AtP'],
        'data/aesa/results.json deterministic (VHIGH)', 'DATA / JUDGEMENT: the 1991-2023 census trend continues')
    return pd.DataFrame(rows)


# ---- 4. Replacement variants of the Reference, the Pathways and TL (ED5) --------------------------
def replacement_variants():
    """The Reference, the Moderate / Ambitious Pathway and TL under the Low, Reference, High and Very High replacement
    variants:
    carbon and floor area 2026-2050, committed after 2050, cumulative LoE AR and AtP; every run recomputed with the
    pathway engine (pathways.run and pathways.metrics, the lever parameters of the Reference) and asserted to
    reproduce runs.csv to 1e-12."""
    import pathways as PW
    runs = pd.read_csv(data('pathways/runs.csv'))
    bounds = PW.boundaries()
    B_ref = PW.boss_state(PW.REFERENCE)
    params = PARAMS.setdefault('p', PW.resolve_params(B_ref))
    cols = ('gfa_Mm2', 'carbon_kt', 'committed_lower_kt', 'committed_upper_kt', 'LoE_AR', 'LoE_AtP')
    rows = []
    for scen in ('LOW', 'REF', 'HIGH', 'VHIGH'):
        if scen != PW.REFERENCE:                                     # the Reference budgets are used below
            key = N.SCENARIOS['VHIGH'] if scen == 'VHIGH' else 'Low / High replacement'
            if BD.ar_base_rule(key)[0] != BD.REFERENCE_BASE:
                raise SystemExit(f'sensitivity_tables: {key!r} is not classified {BD.REFERENCE_BASE!r}.')
        B = B_ref if scen == PW.REFERENCE else PW.boss_state(scen)
        ctx = PW.base_context(B, scen, bounds)
        for run, levels, setting in ((scen, {}, 'reference'),
                                     (f'{LV.PATHWAY}-moderate', LV.pathway_levers(LV.PATHWAY, 'moderate'), 'moderate'),
                                     (f'{LV.PATHWAY}-ambitious', LV.pathway_levers(LV.PATHWAY, 'ambitious'),
                                      'ambitious'),
                                     ('TL', LV.tl_levels(LV.TL_COMPONENTS), 'tl')):
            m = PW.metrics(ctx, PW.run(ctx, params, levels), run, setting)
            o = runs[(runs['scenario'] == scen) & (runs['run'] == run)].iloc[0]
            for c in ('carbon_kt', 'LoE_AR', 'LoE_AtP', 'committed_lower_kt', 'committed_upper_kt'):
                if not np.isclose(m[c], o[c], rtol=1e-12, atol=0):
                    raise SystemExit(f'sensitivity_tables: {scen} {run} {c} {m[c]} does not reproduce runs.csv ({o[c]}).')
            rows.append(dict(scenario=scen, run='Reference' if run == scen else run,
                             source='data/pathways/runs.csv (reproduced)', **{c: float(m[c]) for c in cols}))
    return pd.DataFrame(rows)


# ---- 5. Fig8a tornado: inputs of the Reference ------------------------------------------------
TORNADO = [   # (input, low case, high case) in reference_table() rows
    ('Population (Stats NZ 5th / 95th percentile)', 'Population: Stats NZ 5th / 95th percentile'),
    ('Living arrangements: Stats NZ B (one-sided)', 'Living arrangements: propensities change (Stats NZ B)'),
    ('Replacement (Low / High)', 'Low / High replacement'),
    ('Replacement: Very High (trend continues; one-sided)', 'Very High replacement (trend continues)'),
    ('Replacement half-life (5 / 15 yr)', 'Replacement half-life 5 / 15 yr'),
    ('Household size: 2018-2023 census pace (one-sided)', 'Household size: 2018-2023 census pace'),
    ('Completion rate (0.93 / 0.96)', 'Completion rate 0.93 / 0.96'),
    ('Completion lag (15 / 19 months)', 'Completion lag 15 / 19 months'),
    ('Completion lag 0 months (one-sided)', 'Completion lag 0 months'),
    ('No 2026 data (one-sided)', 'No 2026 data'),
    ('Case-study carbon factors (jackknife)', 'Case studies: jackknife low / high'),
    ('Soil order (Raw / Organic)', 'Soil order: lowest (Raw) / highest (Organic)'),
    ('Overbuild absorption (by 2030 / by 2045)', '2026 overbuild absorbed by 2030 / by 2045'),
]


def tornado(ref):
    """Fig7a: for each input its low and high case: cumulative carbon 2026-2050 and the cumulative LoE AR and AtP. The
    AR base follows the shared-parameter rule (boundaries.AR_BASE_RULE, recorded in aesa/results.json
    one_at_a_time_ar_base): a 'recompute' row uses the AR budget of its own I_sec,base, a 'reference_base' row the
    Reference budget; the population rows use that path's budgets (population_paths). AtP does not depend on the base."""
    with open(data('aesa/results.json')) as f:
        r = json.load(f)
    a = pd.read_csv(data('aesa/annual.csv'))
    a = a[(a['scenario'] == 'REF') & (a['year'] >= 2026)]
    bar, batp = a['B_AR_kgCO2e'].sum() / M6, a['B_AtP_kgCO2e'].sum() / M6
    pp = r['population_paths']
    oat = r['one_at_a_time_ar_base']
    c0 = float(ref['central_carbon_kt'].iloc[0])
    rows = []
    if any(row in CARBON_ONLY_ROWS for _, row in TORNADO):
        raise SystemExit('sensitivity_tables: a carbon-only row (CARBON_ONLY_ROWS) is in TORNADO.')
    for name, row in TORNADO:
        rule = BD.ar_base_rule(row)[0]
        if oat[row]['rule'] != rule:
            raise SystemExit(f'sensitivity_tables: aesa/results.json is stale for {row!r} (rule {oat[row]["rule"]!r}).')
        if rule == BD.RECOMPUTE and 'sides' not in oat[row]:
            raise SystemExit(f'sensitivity_tables: no recomputed AR base for {row!r}.')
        t = ref[ref['row'] == row].set_index('side')
        one_sided = 'single' in t.index
        if one_sided:                                 # a one-sided row (low = the central case)
            t = pd.DataFrame({'case': ['central', t.loc['single', 'case']],
                              'carbon_kt': [c0, t.loc['single', 'carbon_kt']]}, index=['low', 'high'])
        for side in ('low', 'high'):
            c = float(t.loc[side, 'carbon_kt'])
            if name.startswith('Population'):
                pct = '5th' if side == 'low' else '95th'
                b1, b2 = pp[pct]['B_AR_kt'], pp[pct]['B_AtP_kt']
            elif rule == BD.RECOMPUTE and not (one_sided and side == 'low'):
                b1, b2 = oat[row]['sides']['single' if one_sided else side]['B_AR_kt_2026_2050'], batp
            else:
                b1, b2 = bar, batp
            rows.append(dict(input=name, side=side, case=t.loc[side, 'case'], carbon_kt=c, LoE_AR=c / b1,
                             LoE_AtP=c / b2, central_carbon_kt=c0, central_LoE_AR=c0 / bar, central_LoE_AtP=c0 / batp,
                             change_carbon_pct=100 * (c / c0 - 1)))
    return pd.DataFrame(rows)


def main():
    ref = reference_table()
    HH_TABLE['t'] = household_size_table()
    out = {'sensitivity/reference_carbon.csv': ref, 'sensitivity/tornado.csv': tornado(ref),
           'sensitivity/household_size.csv': HH_TABLE['t'],
           'sensitivity/pathway_carbon.csv': pathway_table(),
           'sensitivity/planetary_boundary.csv': pb_table(), 'loe_2028_2050.csv': loe_2028_2050(),
           'sensitivity/tl_sensitivity.csv': tl_sensitivity(),
           'sensitivity/replacement_variants.csv': replacement_variants()}
    for rel, df in out.items():
        N.columns(df).to_csv(layout.writing(data(rel)), index=False)
        print(f'sensitivity_tables: {rel} ({len(df)} rows)')


if __name__ == '__main__':
    main()
