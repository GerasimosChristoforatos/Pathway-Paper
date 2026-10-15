"""Grouped one-at-a-time sensitivity tables (MODEL v3.0.0; docs/SENSITIVITY_PLAN.md).

    python tools/sensitivity_tables.py         (run_all.py runs it after the pathway Monte Carlo)

Writes outputs/data/sensitivity/:
  reference_carbon.csv     Reference carbon 2026-2050, rows grouped by type of change (D16)
  p5_carbon.csv            P5 Combined (Moderate) carbon 2026-2050 and its levels of exceedance, pathway
                           design rows (D41)
  planetary_boundary.csv   cumulative LoE AR and AtP of the Reference (D42)
  replacement_variants.csv the Reference, P5 and TL under Low / Reference / High replacement (ED13)
  tornado.csv              Fig7: the eight inputs of the Reference tornado (low / high), cumulative carbon and the
                           cumulative LoE AR and AtP (the budgets move only with the population path)

Every row has its group, the row label, its side (low / high / single), the value, the change vs the
central case and its basis. Rows are read from existing outputs; the only new runs are the P5 rows
with one lever (L1-L9) at Ambitious (the others Moderate) and P5 on the Stats NZ 5th / 95th population
paths (exact engine path: the projection's own percentile run, reproduced to 1e-12 before the levers
are applied; the AR and AtP budgets move with the path, data/aesa/results.json population_paths), and
TL under Low and High replacement (every other run of that table reproduces runs.csv to 1e-12).
One-at-a-time ranges are not additive and are not a joint interval.
"""
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

M6 = 1e6


def data(rel):
    return layout.data(rel, frozen=False)


# ---- 1. Reference carbon -----------------------------------------------------------------------
# (group, row label, side, case in sensitivity_one_at_a_time.csv, basis)
REF_ROWS = [
    ('Demographics', 'Population: Stats NZ 5th / 95th percentile', 'low', 'Population: Stats NZ 5th percentile (engine path)',
     'DATA: Stats NZ 2024-base stochastic projection; exact engine path'),
    ('Demographics', 'Population: Stats NZ 5th / 95th percentile', 'high', 'Population: Stats NZ 95th percentile (engine path)',
     'DATA: Stats NZ 2024-base stochastic projection; exact engine path'),
    ('Demographics', 'Household size: Stats NZ High / Low variant', 'low', 'Household size: Stats NZ High variant',
     'DATA: Stats NZ household projections (the High household-size variant gives fewer households)'),
    ('Demographics', 'Household size: Stats NZ High / Low variant', 'high', 'Household size: Stats NZ Low variant',
     'DATA: Stats NZ household projections'),
    ('Demographics', 'Household size after 2043: flat', 'single', 'Household size after 2043: flat (kink at 2043)',
     'JUDGEMENT: post-2043 tail (the Stats NZ series ends in 2043)'),
    ('Demographics', 'Household size after 2043: secant-slope taper', 'single',
     'Household size after 2043: secant-slope taper', 'JUDGEMENT: post-2043 tail'),
    ('Demographics', 'Household size after 2043: taper from the PCHIP end slope', 'single',
     'Household size after 2043: taper from the PCHIP end slope', 'JUDGEMENT: post-2043 tail'),
    ('Housing stock & calibration', 'Completion rate 0.92 / 0.96', 'low', 'Completion rate 0.92',
     'LITERATURE: Jones et al. 2024 bounds (citation to verify)'),
    ('Housing stock & calibration', 'Completion rate 0.92 / 0.96', 'high', 'Completion rate 0.96',
     'LITERATURE: Jones et al. 2024 bounds (citation to verify)'),
    ('Housing stock & calibration', "Completion lag on (Little's law)", 'single', "Completion lag on (Little's law)",
     'DATA: build duration from consents and dwellings under construction'),
    ('Housing stock & calibration', 'No census under-construction correction', 'single',
     'No census under-construction correction', 'DATA: census under-construction counts'),
    ('Housing stock & calibration', 'Dwelling-size window 2016-2025', 'single', 'Dwelling size: 2016-2025 reference',
     'DATA: consents'),
    ('Housing stock & calibration', '2026 overbuild absorbed by 2030 / by 2045', 'low', 'Overbuild absorbed by 2030',
     'THEORY: reversion to the equilibrium vacancy (Rosen & Smith 1983; Wheaton 1990; DiPasquale & Wheaton 1992; '
     'Gabriel & Nothaft 2001) fixes the direction, not the speed; speed bracketed'),
    ('Housing stock & calibration', '2026 overbuild absorbed by 2030 / by 2045', 'high', 'Overbuild absorbed by 2045',
     'THEORY: as above; adopted 2035 (the common RECC window)'),
    ('Housing stock & calibration', '2026 overbuild never absorbed (MODEL v2.1 Reference)', 'single',
     'Overbuild never absorbed (MODEL v2.1 Reference)', 'DECISION: the permanent-surplus bound'),
    ('Housing stock & calibration', 'Vacancy parameter: 1986-2023 census mean (one definition)', 'single',
     'Vacancy parameter: 1986-2023 census mean, one definition', 'DATA: Stats NZ censuses 1986-2023'),
    ('Housing stock & calibration', '2026 overbuild booked as stock-neutral redevelopment', 'single',
     'Booked as redevelopment, stock-neutral', 'DECISION (author): booking of observed 2026 building'),
    ('Housing stock & calibration', '2026 overbuild gap vs the 2026 requirement', 'single',
     'Gap measured against the 2026 requirement', 'DECISION (author): rule variant'),
    ('Replacement scenario', 'Low / High replacement', 'low', 'Low replacement: long-run rate',
     'DATA: 1991-2023 long-run rate'),
    ('Replacement scenario', 'Low / High replacement', 'high', 'High replacement: 2018-2023 rate persists',
     'DATA: 2018-2023 census-interval rate'),
    ('Replacement scenario', 'Replacement half-life 5 / 15 yr', 'low', 'Reference, replacement half-life 5 yr',
     'JUDGEMENT: the half-life is not identifiable from the census record'),
    ('Replacement scenario', 'Replacement half-life 5 / 15 yr', 'high', 'Reference, replacement half-life 15 yr',
     'JUDGEMENT: the half-life is not identifiable from the census record'),
    ('Carbon factors & technology', 'Single case study: lowest / highest', 'low', 'Materials: lowest single case study',
     'DATA: 16 NZ case studies (Christoforatos & Pickering 2025)'),
    ('Carbon factors & technology', 'Single case study: lowest / highest', 'high', 'Materials: highest single case study',
     'DATA: 16 NZ case studies (Christoforatos & Pickering 2025)'),
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
    ('Accounting', 'Event timing L / n', 'single', 'Event timing: interval L / n', 'DECISION: maintenance timing'),
]


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


# ---- 2. P5 carbon (pathway design) ---------------------------------------------------------------
PARAMS = {}


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
    E = engine.forward(pop, hh, growth, join=ji['join'], join_redev=ji['redev'], **fi)
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


def p5_table():
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

    c0, a0, t0 = run_row('REF', 'P5-moderate')
    rows = []

    def add(group, label, side, carbon, loe_ar, loe_atp, source, basis):
        rows.append(dict(group=group, row=label, side=side, carbon_kt=carbon, LoE_AR=loe_ar, LoE_AtP=loe_atp,
                         central_carbon_kt=c0, central_LoE_AR=a0, central_LoE_AtP=t0,
                         change_pct=100 * (carbon / c0 - 1), source=source, basis=basis))

    base = LV.pathway_levers('P5', 'moderate')
    cc = float(np.asarray(PW.run(ctx, params, base)['E']['carbon'], float)[1:].sum()) / M6
    if not np.isclose(cc, c0, rtol=1e-12, atol=0):     # the context reproduces the adopted P5 run
        raise SystemExit(f'sensitivity_tables: P5 Moderate {cc} kt does not reproduce runs.csv {c0} kt.')
    tags = {L: f"sub-rule {LV.SUBRULE[L]}" for L in LV.LEVERS}
    for L in LV.LEVERS:                                      # one lever at Ambitious, the others Moderate
        E = PW.run(ctx, params, dict(base, **{L: 'ambitious'}))['E']
        c = float(np.asarray(E['carbon'], float)[1:].sum()) / M6
        add('Ambition of one lever', f"{L} {N.LEVERS[L]} at Ambitious", 'single', c, c / bar, c / batp,
            'new run (tools/sensitivity_tables.py)', f"{tags[L]}: the Ambitious setting of {L}")
    add('Ambition of all', 'P5 Combined, Ambitious', 'single', *run_row('REF', 'P5-ambitious'),
        'data/pathways/runs.csv', 'DECISION (author): every lever at Ambitious')
    for side, nm in (('low', 'P5-moderate-by2030'), ('high', 'P5-moderate-by2045')):
        add('Roll-out timing', 'Full roll-out by 2030 / by 2045', side, *run_row('REF', nm), 'data/pathways/runs.csv',
            'LITERATURE: RECC (Pauliuk et al. 2024) adopted 2035; window rule of MODEL v1.1.0')
    add('Theoretical limit', 'TL (every lever at Level 4)', 'single', *run_row('REF', 'TL'), 'data/pathways/runs.csv',
        'DECISION (author): Level 4 of every lever')
    for side, sc in (('low', 'LOW'), ('high', 'HIGH')):
        add('Replacement scenario', 'Low / High replacement', side, *run_row(sc, 'P5-moderate'),
            'data/pathways/runs.csv', 'DATA: long-run rate / 2018-2023 rate persists')
    for side, pct in (('low', '5th'), ('high', '95th')):
        cp = percentile_context(PW, B, pct, bounds)
        E = PW.run(cp, params, base)['E']
        c = float(np.asarray(E['carbon'], float)[1:].sum()) / M6
        add('Demographics', 'Population: Stats NZ 5th / 95th percentile', side, c, c / pp[pct]['B_AR_kt'],
            c / pp[pct]['B_AtP_kt'], 'new run (exact engine path; budgets move with the path)',
            'DATA: Stats NZ 2024-base stochastic projection')
    return pd.DataFrame(rows)


# ---- 3. Planetary boundary --------------------------------------------------------------------------
PB_ROWS = [
    ('Carrying capacity', 'SOS / I_glob pair C: 1 W/m² planetary boundary', 'single', 'i_source_pair',
     'LITERATURE: Bjørn & Hauschild 2015'),
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


def pb_table():
    s = pd.read_csv(data('aesa/sensitivity.csv')).set_index('case')
    with open(data('aesa/results.json')) as f:
        r = json.load(f)
    ref = s.loc['reference']
    a0, t0 = float(ref['cum_LoE_AR']), float(ref['cum_LoE_AtP'])
    rows = []

    def add(group, label, side, ar, atp, source, basis):
        rows.append(dict(group=group, row=label, side=side, LoE_AR=ar, LoE_AtP=atp, central_LoE_AR=a0,
                         central_LoE_AtP=t0, change_AR_pct=100 * (ar / a0 - 1), change_AtP_pct=100 * (atp / t0 - 1),
                         source=source, basis=basis))

    for g, lab, side, case, basis in PB_ROWS:
        add(g, lab, side, float(s.loc[case, 'cum_LoE_AR']), float(s.loc[case, 'cum_LoE_AtP']),
            f'data/aesa/sensitivity.csv ({case})', basis)
    for side, pct in (('low', '5th'), ('high', '95th')):
        p = r['population_paths'][pct]
        add('Population source', 'Population: Stats NZ 5th / 95th percentile (carbon and boundaries together)', side,
            p['LoE_AR'], p['LoE_AtP'], 'data/aesa/results.json population_paths', 'DATA: Stats NZ stochastic projection')
    for lab, pair in (('Low / High replacement', ('LOW', 'HIGH')), ('Replacement half-life 5 / 15 yr', ('REF_HL5', 'REF_HL15'))):
        for side, k in zip(('low', 'high'), pair):
            d = r['deterministic'][k]
            add('Replacement scenario', lab, side, d['LoE_AR'], d['LoE_AtP'], f'data/aesa/results.json deterministic ({k})',
                'DATA / JUDGEMENT (replacement variants)')
    return pd.DataFrame(rows)


# ---- 4. Replacement variants of the Reference, P5 and TL (ED10) ------------------------------------
def replacement_variants():
    """The Reference, P5 Combined (Moderate, Ambitious) and TL under the Low, Reference and High replacement variants:
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
    for scen in ('LOW', 'REF', 'HIGH'):
        B = B_ref if scen == PW.REFERENCE else PW.boss_state(scen)
        ctx = PW.base_context(B, scen, bounds)
        for run, levels, setting in ((scen, {}, 'reference'),
                                     ('P5-moderate', LV.pathway_levers('P5', 'moderate'), 'moderate'),
                                     ('P5-ambitious', LV.pathway_levers('P5', 'ambitious'), 'ambitious'),
                                     ('TL', LV.tl_levels(LV.TL_COMPONENTS), 'tl')):
            m = PW.metrics(ctx, PW.run(ctx, params, levels), run, setting)
            o = runs[(runs['scenario'] == scen) & (runs['run'] == run)].iloc[0]
            for c in ('carbon_kt', 'LoE_AR', 'LoE_AtP', 'committed_lower_kt', 'committed_upper_kt'):
                if not np.isclose(m[c], o[c], rtol=1e-12, atol=0):
                    raise SystemExit(f'sensitivity_tables: {scen} {run} {c} {m[c]} does not reproduce runs.csv ({o[c]}).')
            rows.append(dict(scenario=scen, run='Reference' if run == scen else run,
                             source='data/pathways/runs.csv (reproduced)', **{c: float(m[c]) for c in cols}))
    return pd.DataFrame(rows)


# ---- 5. Fig7 tornado: eight inputs of the Reference ------------------------------------------------
TORNADO = [   # (input, low case, high case) in reference_table() rows
    ('Population (Stats NZ 5th / 95th percentile)', 'Population: Stats NZ 5th / 95th percentile'),
    ('Household size (Stats NZ High / Low variant)', 'Household size: Stats NZ High / Low variant'),
    ('Replacement (Low / High)', 'Low / High replacement'),
    ('Replacement half-life (5 / 15 yr)', 'Replacement half-life 5 / 15 yr'),
    ('Completion rate (0.92 / 0.96)', 'Completion rate 0.92 / 0.96'),
    ('Case-study carbon factors (jackknife)', 'Case studies: jackknife low / high'),
    ('Soil order (Raw / Organic)', 'Soil order: lowest (Raw) / highest (Organic)'),
    ('Overbuild absorption (by 2030 / by 2045)', '2026 overbuild absorbed by 2030 / by 2045'),
]


def tornado(ref):
    """Fig7: for each input its low and high case: cumulative carbon 2026-2050 and the cumulative LoE AR and AtP. The
    boundaries depend on the population path only (aesa): the population rows use that path's budgets
    (aesa/results.json population_paths), every other row the Reference budgets."""
    with open(data('aesa/results.json')) as f:
        r = json.load(f)
    a = pd.read_csv(data('aesa/annual.csv'))
    a = a[(a['scenario'] == 'REF') & (a['year'] >= 2026)]
    bar, batp = a['B_AR_kgCO2e'].sum() / M6, a['B_AtP_kgCO2e'].sum() / M6
    pp = r['population_paths']
    c0 = float(ref['central_carbon_kt'].iloc[0])
    rows = []
    for name, row in TORNADO:
        t = ref[ref['row'] == row].set_index('side')
        for side in ('low', 'high'):
            c = float(t.loc[side, 'carbon_kt'])
            if name.startswith('Population'):
                pct = '5th' if side == 'low' else '95th'
                b1, b2 = pp[pct]['B_AR_kt'], pp[pct]['B_AtP_kt']
            else:
                b1, b2 = bar, batp
            rows.append(dict(input=name, side=side, case=t.loc[side, 'case'], carbon_kt=c, LoE_AR=c / b1,
                             LoE_AtP=c / b2, central_carbon_kt=c0, central_LoE_AR=c0 / bar, central_LoE_AtP=c0 / batp,
                             change_carbon_pct=100 * (c / c0 - 1)))
    return pd.DataFrame(rows)


def main():
    ref = reference_table()
    out = {'sensitivity/reference_carbon.csv': ref, 'sensitivity/tornado.csv': tornado(ref),
           'sensitivity/p5_carbon.csv': p5_table(),
           'sensitivity/planetary_boundary.csv': pb_table(),
           'sensitivity/replacement_variants.csv': replacement_variants()}
    for rel, df in out.items():
        N.columns(df).to_csv(layout.writing(data(rel)), index=False)
        print(f'sensitivity_tables: {rel} ({len(df)} rows)')


if __name__ == '__main__':
    main()
