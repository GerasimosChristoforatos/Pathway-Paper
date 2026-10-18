"""Report figures of the projection: the computations (MODEL v3.0.0, compute only).

    python tools/figures_report.py

Runs the projection variants (Low replacement, Reference, High replacement; validation.run_boss) and writes the
exact arrays of the report diagnostics as figure source data (figsource.write ->
outputs/data/figure_source/<file id>.json): D07_net_replacement_rate, D10_floor_area_bridge
(D11 is retired: with demolition replacement and unconsented additions split in every band set it equals D10),
D12_conversion_chain, D14_hindcast, D15_reality_checks, D19_variants. The figures are
drawn from those files by figures/validation.py (python -m figures <file ids>); nothing is drawn here.

Also writes where the projection leaves the 1991-2025 range -> outputs/data/baseline/reality_checks.json and
outputs/reports/reality_checks.md.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine  # noqa: E402
import figsource  # noqa: E402
import layout  # noqa: E402
import naming as N  # noqa: E402
import validation  # noqa: E402


# the Reference and the two replacement variants (typology shares held in all); labels: naming.SCENARIOS
SCEN = [('LOW', N.SCENARIOS['LOW'], dict(REPLACEMENT_VARIANT='LOW')),
        ('REF', N.SCENARIOS['REF'], dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0)),
        ('HIGH', N.SCENARIOS['HIGH'], dict(REPLACEMENT_VARIANT='HIGH')),
        ('VHIGH', N.SCENARIOS['VHIGH'], dict(REPLACEMENT_VARIANT='VHIGH'))]          # MODEL v3.3.0
VARS = ('LOW', 'REF', 'HIGH', 'VHIGH')            # MODEL v3.3.0: + Very High replacement
M6 = 1e6

# MODEL v3.0.0 floor-area bridge (D10; D11 retired): the demand bands of the definition 'with retirement villages'
# (naming.BANDS_WITH_RETIREMENT_VILLAGES), in the in-scope band order (positive bands, then the bands negative by
# construction), each with its key in projection results[...]; retirement villages (out of scope, negative) last.
# The 2026 overbuild is the market excess ('join', >= 0) and 'Overbuild absorbed' the payback ('absorbed', <= 0);
# 'Demolition replacement' is demolition at the BRANZ rate ('repl'), 'Unconsented additions' the calibrated
# long-run residual ('unc'). The bands add up to the in-scope total (checked below).
BRIDGE = [('growth', 'growth'), ('smaller_households', 'hs_pos'), ('extra_space', 'extra'), ('vacancy', 'vac'),
          ('overbuild_2026', 'join'), ('replacement', 'repl'), ('redevelopment', 'wave'),
          ('overbuild_absorbed', 'absorbed'), ('unconsented', 'unc'), ('retirement_villages', 'rv')]


def series(B):
    """Annual quantities, history (1991-2025) and projection (2026-2050)."""
    E, R = B['engine_out']['50th'], B['results']['50th']
    fy = np.asarray(B['forecast_years'])
    yh = np.asarray(B['years_hist'])
    c = float(B['_completion'])
    pop_f = pd.Series(E['pop'], index=fy)
    hp = B['hist_pop']
    long_rate = float(B['demolition_rate'] + B['unconsented_rate'])
    wave = (np.asarray(B['rate_path'], float) - long_rate) * E['prev']
    p = dict(
        built=pd.Series(engine.requirement(E), index=fy),
        removals_net=pd.Series(E['demol'] + E['unc'] + E['join_redev'], index=fy),
        removals_gross=pd.Series(E['demol'] + wave + E['join_redev'], index=fy),
        dpop=pop_f.diff(), gfa=pd.Series(R['total'], index=fy),
        S=pd.Series(E['S'], index=fy),
        # effective vacancy: the stock-adding near-term excess raises it above the exogenous rate
        v=pd.Series(100 * (1 - np.asarray(E['hh']) / (np.asarray(E['stock']) + np.asarray(E['stock_join']))), index=fy),
        size=pd.Series(R['total'] / np.where(E['dwell_in_scope'] == 0, np.nan, E['dwell_in_scope']), index=fy),
        dense=100 * (1 - B['evolving_gfa_shares']['Detached']),
        carbon=pd.Series(E['carbon'], index=fy), d_hh=pd.Series(E['d_hh'], index=fy),
        stock_2025=float(E['stock'][0]))
    built_h = c * B['hist_units_all_c']
    cr = B['census_rates']
    rem_h = pd.Series(np.nan, index=yh, dtype=float)
    for r in cr.itertuples():                        # census-interval net removals, annualised
        rem_h[(yh > r.y0) & (yh <= r.y1)] = (r.built - r.d_stock) / (r.y1 - r.y0)
    h = dict(built=built_h, removals_net=rem_h, dpop=hp.diff(), gfa=B['hist_built_gfa'],
             S=B['hist_S'], v=100 * B['stock_cal']['v'], size=B['hist_built_gfa'] / B['hist_built_units'],
             dense=100 * (1 - B['hist_shares']['Detached']))
    return p, h


def range_check(hist, proj, years=(2026, 2050)):
    h = hist.loc[1991:2025].replace([np.inf, -np.inf], np.nan).dropna()
    q = proj.loc[years[0]:years[1]].replace([np.inf, -np.inf], np.nan).dropna()
    lo, hi = float(h.min()), float(h.max())
    above, below = q[q > hi], q[q < lo]
    return dict(hist_min=lo, hist_max=hi, years_outside=int(len(above) + len(below)),
                max_above_pct=float(100 * (above.max() / hi - 1)) if len(above) and hi else 0.0,
                max_below_pct=float(100 * (1 - below.min() / lo)) if len(below) and lo else 0.0,
                first_outside=int(min(list(above.index) + list(below.index))) if len(above) + len(below) else None)


def _f(s):
    """A float series with an int year index (inf -> NaN, written as null)."""
    s = pd.Series(np.asarray(s, float), index=[int(i) for i in s.index])
    return s.replace([np.inf, -np.inf], np.nan)


def main():
    runs = {}
    for k, lab, s in SCEN:
        B = validation.run_boss(**s)
        runs[k] = dict(B=B, lab=lab, p=series(B)[0])
    hist = series(runs['REF']['B'])[1]
    ref = runs['REF']
    labels = {k: runs[k]['lab'] for k in VARS}

    # ---- D15 reality checks -------------------------------------------------
    # (key, panel title, y label, scale, projection quantity)
    panels = [
        ('built', 'Dwellings completed', 'Dwellings (thousand per year)', 1e3, lambda p: p['built']),
        ('removals_net', 'Implied net removals', 'Dwellings (thousand per year)', 1e3, lambda p: p['removals_net']),
        ('ppl_per_dw', 'People per new dwelling', 'Persons per new dwelling', 1, lambda p: p['dpop'] / p['built']),
        ('m2_per_res', 'New floor area per additional resident', 'Floor area per person (m²)', 1,
         lambda p: p['gfa'] / p['dpop']),
        ('S', 'Household size', 'Household size (persons per household)', 1, lambda p: p['S']),
        ('size', 'Average new-dwelling size', 'Floor area per dwelling (m²)', 1, lambda p: p['size']),
        ('vacancy', 'Vacancy rate (effective)', 'Vacancy rate (% of private dwellings)', 1, lambda p: p['v'])]
    hist_of = dict(built=hist['built'], removals_net=hist['removals_net'], ppl_per_dw=hist['dpop'] / hist['built'],
                   m2_per_res=hist['gfa'] / hist['dpop'], S=hist['S'], size=hist['size'], vacancy=hist['v'])
    rc = {}
    d15 = {}
    for key, title, unit, sc, f in panels:
        hs = hist_of[key]
        h = hs.loc[1991:2025].replace([np.inf, -np.inf], np.nan).dropna()
        d15[key] = dict(title=title, ylabel=unit, scale=sc, history=_f(hs / sc),
                        range_1991_2025=[float(h.min() / sc), float(h.max() / sc)],
                        projection={k: _f(f(runs[k]['p']).loc[2026:] / sc) for k in VARS})
        for k in VARS:
            rc.setdefault(k, {})[key] = range_check(hs, f(runs[k]['p']))
    # cumulative removals as % of the 2025 stock by 2050 (gross: demolition + redevelopment + 2026 overbuild)
    removals_pct = {k: float(100 * runs[k]['p']['removals_gross'].loc[2026:].sum() / runs[k]['p']['stock_2025'])
                    for k in VARS}
    _m2 = (hist['gfa'] / hist['dpop']).loc[1991:2025]
    # the last observed year -> the first modelled year handover against historical year-to-year changes (MODEL
    # v4.0.0: the last pipeline year with the completion lag, 2027 -> 2028; MODEL v3.3: 2026 -> 2027)
    Bref = ref['B']
    chg = 100 * Bref['hist_total_gfa'].pct_change().loc[1992:2025].values
    R0 = Bref['results']['50th']['total']
    y_obs = int(max(Bref['pipe']['years'])) if Bref.get('pipe') else 2026
    i_obs = list(Bref['forecast_years']).index(y_obs)
    step = 100 * (R0[i_obs + 1] / R0[i_obs] - 1)
    handover = dict(step_pct=float(step), last_observed_year=y_obs, first_model_year=y_obs + 1,
                    hist_median_pct=float(np.median(chg)), hist_min_pct=float(chg.min()), hist_max_pct=float(chg.max()))
    figsource.write('D15_reality_checks', panels=d15, order=[p[0] for p in panels], variants=list(VARS),
                    labels=labels, removals_pct_of_2025_stock=removals_pct,
                    m2_per_res_max=dict(year=int(_m2.idxmax()), value=float(_m2.max())),
                    handover_changes_pct=np.asarray(chg, float), handover=handover)

    # ---- D10 bridge -----------------------------------------------------------
    bridge = {}
    for k in VARS:
        R = runs[k]['B']['results']['50th']
        vals = {b: float(np.sum(R[x][1:])) / M6 for b, x in BRIDGE}
        total = float(np.sum(R['total'][1:])) / M6
        gap = abs(sum(vals.values()) - total) / max(abs(total), 1.0)
        if gap > 1e-9:
            raise SystemExit(f'figures_report: the bridge bands of {k} do not add up to the in-scope total '
                             f'({sum(vals.values()):.6f} vs {total:.6f} Mm2)')
        bridge[k] = dict(values=vals, total_in_scope=total)
    common = dict(bands=[b for b, _ in BRIDGE], results_keys={b: x for b, x in BRIDGE}, variants=list(VARS),
                  labels=labels, unit='Mm2, 2026-2050 (median population)', bridge=bridge)
    figsource.write('D10_floor_area_bridge', **common)

    # ---- D07 net replacement rate: census record and variant paths --------------
    long_rate = float(Bref['demolition_rate'] + Bref['unconsented_rate'])
    fy = np.asarray(Bref['forecast_years'])
    cr = Bref['census_rates']
    figsource.write('D07_net_replacement_rate',
                    census=pd.DataFrame(dict(y0=[int(r.y0) for r in cr.itertuples()],
                                             y1=[int(r.y1) for r in cr.itertuples()],
                                             rate=[float(r.rate) for r in cr.itertuples()])),
                    years=fy.astype(int),
                    paths={k: engine.replacement_path(k, long_rate, float(Bref['rate_recent']), fy, 10.0,
                                                      trend=Bref['replacement_trend'])
                           for k in VARS},
                    # MODEL v3.3.0: the Reference path continued to 2075 (dotted; its asymptote is the long-run rate),
                    # and the census trend of the Very High variant (coefficients: rate(t) = a + b t)
                    reference_extended=dict(years=list(range(2050, 2076)),
                                            rate=engine.replacement_path('REF', long_rate, float(Bref['rate_recent']),
                                                                         np.arange(2050, 2076), 10.0).tolist()),
                    trend=Bref['replacement_trend'],
                    labels=labels, long_rate=long_rate, rate_recent=float(Bref['rate_recent']),
                    demolition_rate=float(Bref['demolition_rate']),
                    unconsented_rate=float(Bref['unconsented_rate']),
                    window=list(validation.projection.NET_REPLACEMENT_WINDOW))

    # ---- D19 variants ------------------------------------------------------------
    mc = layout.montecarlo('annual', 'REF')
    mc_band = None
    if os.path.exists(mc):
        m = pd.read_csv(mc, index_col=0).loc[2026:]
        mc_band = dict(lo=_f(m['floor_area_5'] / M6), hi=_f(m['floor_area_95'] / M6),
                       file=os.path.relpath(mc, layout.data('', frozen=False)))
    figsource.write('D19_variants', variants=list(VARS), labels=labels, history_gfa=_f(hist['gfa'] / M6),
                    gfa={k: _f(runs[k]['p']['gfa'].loc[2026:] / M6) for k in VARS},
                    gfa_cumulative={k: float(runs[k]['p']['gfa'].loc[2026:].sum() / M6) for k in VARS},
                    carbon_cumulative_kt={k: float(runs[k]['B']['tot_carbon_median']) for k in VARS},
                    mc_band=mc_band)

    # ---- D12 conversion chain -------------------------------------------------
    p = ref['p']
    yrs = np.arange(2027, 2051)
    figsource.write('D12_conversion_chain', years=yrs,
                    chain={key: _f(p[key].loc[yrs]) for key in ('dpop', 'd_hh', 'built', 'gfa', 'carbon')},
                    intensity={k: _f((runs[k]['p']['carbon'] / runs[k]['p']['gfa']).loc[2026:2050]) for k in VARS},
                    variants=list(VARS), labels=labels)

    # ---- D14 validation ---------------------------------------------------------
    v = json.load(open(layout.data('baseline/validation.json')))
    figsource.write('D14_hindcast', hindcast=v['hindcast'], hindcast_as_published=v.get('hindcast_as_published') or [],
                    model_method=v['model_method'], check_2026=v['check_2026'],
                    read_from='baseline/validation.json')

    # ---- reality-check exceedances ----------------------------------------
    with open(layout.writing(layout.data('baseline/reality_checks.json')), 'w') as f:
        json.dump(N.keys(dict(rc, handover=handover)), f, indent=2)
    names = dict(built='dwellings completed', removals_net='net removals', ppl_per_dw='people per new dwelling',
                 m2_per_res='floor area per additional resident', S='household size', size='new-dwelling size',
                 vacancy='vacancy rate (effective, %)')
    L = ['# Reality checks (generated by tools/figures_report.py)', '',
         'Projection 2026-2050 against the 1991-2025 historical range (min-max).', '',
         '| variant | quantity | historical range | years outside | first year outside | max above (%) | max below (%) |',
         '|---|---|---|---|---|---|---|']
    for k, d in rc.items():
        for q, r in d.items():
            L.append(f"| {k} | {names[q]} | {r['hist_min']:,.2f} to {r['hist_max']:,.2f} | {r['years_outside']} | "
                     f"{r['first_outside'] or '-'} | {r['max_above_pct']:.1f} | {r['max_below_pct']:.1f} |")
    with open(layout.writing(layout.report('reality_checks.md')), 'w') as f:
        f.write('\n'.join(L) + '\n')

    print('figures_report: figure source data (D07, D10, D12, D14, D15, D19), '
          'outputs/data/baseline/reality_checks.json, outputs/reports/reality_checks.md')


if __name__ == '__main__':
    main()
