"""
GAP 2026 -- decomposition of observed 2026 building against the model (A1 evidence)
=================================================================================
EVIDENCE ONLY. Nothing here sets or tunes a model parameter.

Unit: dwellings COMPLETED in calendar 2026, all categories (in scope +
retirement villages), the model's own unit.

  Observed-implied  O = c x [(1 - W) C26 + W C25]
      C25 = all dwellings consented in 2025 (observed); C26 = 2026 consents,
      estimated two ways: Jan-Jul 2026 / the 2010-2025 seasonal share of those
      months, and the latest 12 months. c, W = the model's completion rate and lag.
  Model             M = the 2026 requirement of the model WITHOUT observed 2026
                    inputs (validation.NO_2026_DATA: no consents nowcast, projected
                    population; the pre-A1 model), Low replacement (long-run rate).

Sequential decomposition of O - M (the order is a choice and is stated):
  (ii)  High replacement: what the 2018-23 replacement regime would add to M (full
        re-run); the Reference (fading, half-life 10 yr) is reported alongside.
  (iii) population: actual growth in the year ended June 2026 (Stats NZ
        mean-quarter ERP, DPE059AA) minus the 2024-base projection median for that year,
        converted to dwellings as households / (1 - v) at the model's 2026
        household size and vacancy. Timing: projection growth is for years
        ended June and is applied by the model to calendar years (half-year
        offset; see projection.NOWCAST_POPULATION, POPULATION CONVENTION).
  With M' = M + (ii) + (iii):
  (i)   pipeline: W x (c C25 - M'), completions in 2026 from 2025 consents
        above the requirement;
  (iv)  residual: (1 - W) x (c C26 - M'), completions from 2026 consents above
        the requirement, expressed as the rise in vacancy, or fall in household
        size, it would imply if built and not offset.
Also reported: where the 2018-23 excess building went, from census counts.

MODEL v4.0.0, with the monthly completion lag (projection.COMPLETION_LAG_MONTHS = L > 0): 2026
completions = c x consents issued Aug 2024 - Jul 2025 (L = 17), all observed, so
  O = c x lagged consents (the 2026 pipeline building of the run, B['pipe']),
  (i) pipeline = O - M' (every 2026 completion comes from a consent issued before 2026),
  (iv) residual = 0 (no 2026 consent completes within 2026 at L = 17).

Writes outputs/reports/gap_2026.md and outputs/data/baseline/gap_2026.json.
"""
import json

import pandas as pd

import layout
import naming as N
import projection
import validation

OUT_MD = layout.report('gap_2026.md')
OUT_JSON = layout.data('baseline/gap_2026.json')


def run(**settings):
    """The model WITHOUT observed 2026 inputs (validation.NO_2026_DATA), plus
    any further settings; module defaults are restored afterwards."""
    return validation.run_boss(**{**validation.NO_2026_DATA, **settings})


def requirement_2026(B):
    """Return the exact 2026 dwelling requirement before the observed pipeline.

    market_excess records R26 from the first, unjoined forward pass. The final
    engine output includes the pipeline join and has its floor area fixed to
    observed consented GFA, so it must not be used to recover the underlying
    requirement via floor area / dwelling size.
    """
    return float(B['join_info']['50th']['R26'])


def projected_growth_ye_june_2026():
    raw = pd.read_excel(projection.FILE_POP_PROJ, sheet_name=projection.POP_SHEET_PROJ, skiprows=5)
    g = projection.locate_projection_block(raw).set_index('Year')
    return {p: float(g.loc[2026, f'PopGrowth_{p}']) * 1000 for p in ('5th', '50th', '95th')}


def boom_2018_2023(B):
    """Where 2018-23 completions went (census counts, private dwellings).
    Completions are lagged W behind consents, so dwellings under construction
    at each census are already outside them: net removals = completions -
    change in stock. The change in dwellings under construction is reported
    for information only; subtracting it as well would count the pipeline twice."""
    cen, cr = B['census'], B['census_rates']
    r = cr[(cr['y0'] == 2018) & (cr['y1'] == 2023)].iloc[0]
    built = float(r['built'])
    d_stock = float(cen.loc[2023, 'total_private'] - cen.loc[2018, 'total_private'])
    d_uc = float(cen.loc[2023, 'under_construction'] - cen.loc[2018, 'under_construction'])
    v18 = cen.loc[2018, 'empty'] / cen.loc[2018, 'total_private']
    vac = float(cen.loc[2023, 'empty'] - v18 * cen.loc[2023, 'total_private'])
    hh = float((cen.loc[2023, 'occupied_private'] + cen.loc[2023, 'away'])
               - (cen.loc[2018, 'occupied_private'] + cen.loc[2018, 'away']))
    return dict(built=built, d_stock=d_stock, d_under_construction=d_uc,
                net_removals=built - d_stock, vacancy_rate_rise_absorbed=vac, households=hh)


def main():
    B = run(REPLACEMENT_VARIANT='LOW')              # the decomposition is stated on Low and High replacement
    c, W = projection.COMPLETION_RATE, B['lag_w']
    C25 = float(B['hist_units_all'].loc[2025])
    lag = int(B.get('lag_months', 0) or 0)
    if lag > 0:
        if not (B['pipe'] and 2026 in B['pipe']['years']):
            raise SystemExit(f'Completion lag {lag} months: 2026 is not a pipeline year; nothing to decompose.')
        C26 = {f'consents lagged {lag} months': B['pipe']['consents_all'][2026]}
    else:
        chk = validation.check_2026(B)
        if chk['status'] != 'observed':
            raise SystemExit('No 2026 consents in the consent file: nothing to decompose.')
        C26 = {'Jan-Jul 2026 / seasonal share': chk['observed_ytd'] / chk['seasonal_share'],
               'latest 12 months': chk['observed_last12']}
    M = requirement_2026(B)
    B2 = run(REPLACEMENT_VARIANT='HIGH')
    M_S2 = requirement_2026(B2)
    d_S2 = M_S2 - M
    M_S3 = requirement_2026(run(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0))
    d_S3 = M_S3 - M
    E1, E2 = B['engine_out']['50th'], B2['engine_out']['50th']
    rep = lambda E: float(E['demol'][1] + E['unc'][1] - E['dev'][1])     # replacement at the calibrated rate
    s2_rate, s2_dev = rep(E2) - rep(E1), float(E2['dev'][1] - E1['dev'][1])
    dev_in_M = float(E1['dev'][1])                   # 2025 deviation carried into 2026 (Low replacement)

    E = B['engine_out']['50th']
    S26, v26, stock25 = float(E['S'][1]), float(E['v'][1]), float(E['prev'][1])
    # the model's 2026 population nowcast (projection.NOWCAST_POPULATION): June qtr 2026 - June qtr 2025
    _q = pd.read_csv(projection.FILE_POP_QUARTERLY).set_index(['year', 'quarter'])['total']
    g_act = float(_q[(2026, 2)] - _q[(2025, 2)])
    g_text = 'mean-quarter ERP (Infoshare DPE059AA), June quarter 2026 minus June quarter 2025'
    g_proj = projected_growth_ye_june_2026()
    d_pop_persons = g_act - g_proj['50th']
    d_pop = d_pop_persons / S26 / (1.0 - v26)        # households, plus vacancy allowance

    rows = []
    for lab, C in C26.items():
        O = c * C if lag > 0 else c * ((1 - W) * C + W * C25)
        for scen, add_S2 in ((f"{N.SCENARIOS['LOW']} (long-run rate)", 0.0),
                             (f"{N.SCENARIOS['REF']} (2018-2023 rate fading, half-life 10 yr)", d_S3),
                             (f"{N.SCENARIOS['HIGH']} (2018-2023 rate persists)", d_S2)):
            Mp = M + add_S2 + d_pop
            pipe = (O - Mp) if lag > 0 else W * (c * C25 - Mp)
            resid = 0.0 if lag > 0 else (1 - W) * (c * C - Mp)
            rows.append(dict(C26_estimate=lab, C26=C, scenario=scen, observed_implied=O, model=M,
                             scenario_adds=add_S2, population=d_pop, pipeline=pipe, residual=resid,
                             gap=O - M, check=O - M - (add_S2 + d_pop + pipe + resid),
                             residual_vacancy_pp=100 * resid / stock25,
                             residual_S_fall=S26 - S26 * float(E['hh'][1]) / (float(E['hh'][1]) + resid * (1 - v26))))
    boom = boom_2018_2023(B)
    res = dict(completion_rate=c, lag_w=W, completion_lag_months=lag,
               completion_period_2026=('Jan-Dec 2026; consents Aug 2024-Jul 2025 shifted 17 months' if lag > 0
                                       else 'calendar 2026 consent estimate with lag W'),
               population_period_2026='year ended June 2026 (June-quarter mean ERP, 12 months)',
               model_requirement_2026_basis='unjoined engine.market_excess R26, before observed pipeline',
               consents_2025=C25, model_requirement_2026=M,
               carried_2025_deviation_in_2026=dev_in_M, HIGH_rate_effect=s2_rate, HIGH_deviation_effect=s2_dev,
               model_requirement_2026_HIGH=M_S2, model_requirement_2026_REF=M_S3, S_2026=S26, v_2026=v26,
               stock_2025=stock25,
               population_growth_ye_june_2026_actual=g_act, population_growth_source_text=g_text,
               population_growth_ye_june_2026_projection=g_proj, rows=rows, boom_2018_2023=boom)
    with open(layout.writing(OUT_JSON), 'w') as f:
        json.dump(N.keys(res), f, indent=2)

    L = ['# 2026 gap decomposition (A1 evidence; nothing here is used to set a parameter)', '',
         f"Dwellings completed in 2026, all categories. Completion rate {c:.3f}, "
         + (f"completion lag {lag} months (2026 completions = consents lagged {lag} months, all observed; "
            f"(i) is O - M' and (iv) is zero); " if lag > 0 else f"lag W = {W:.3f} yr; ") +
         f"2025 consents {C25:,.0f}; model 2026 requirement {M:,.0f} (pre-pipeline; High replacement: {M_S2:,.0f}). The requirement "
         f"already includes {dev_in_M:+,.0f} of the carried 2025 deviation (other_dev_2025 x rho). "
         f"High replacement adds {d_S2:+,.0f}: {s2_rate:+,.0f} from the higher replacement rate and {s2_dev:+,.0f} because "
         f"a higher rate leaves less of 2025's building to be carried as a deviation.", '',
         f"Population, year ended June 2026 (a 12-month June-to-June measure, not six months): actual {g_act:,.0f} (Stats NZ: "
         f"\"{g_text}\") vs 2024-base projection median {g_proj['50th']:,.0f} "
         f"(5th {g_proj['5th']:,.0f}, 95th {g_proj['95th']:,.0f}) -> {d_pop_persons:+,.0f} persons = "
         f"{d_pop:+,.0f} dwellings at S = {S26:.3f}, v = {100 * v26:.2f}%.", '',
         'Population growth is a June-to-June 12-month observation used as a proxy for the calendar-2026 change; it is not an observed Dec-to-Dec figure. ',
         '| 2026 consents estimate | variant | observed-implied completions | model (pre-pipeline) | gap | (ii) variant adds (vs Low) | '
         '(iii) population | (i) pipeline from 2025 | (iv) residual | residual as vacancy rise | '
         'or as fall in household size |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['C26_estimate']} ({r['C26']:,.0f}) | {r['scenario']} | {r['observed_implied']:,.0f} | "
                 f"{r['model']:,.0f} | {r['gap']:+,.0f} | {r['scenario_adds']:+,.0f} | {r['population']:+,.0f} | "
                 f"{r['pipeline']:+,.0f} | {r['residual']:+,.0f} | {r['residual_vacancy_pp']:+.2f} pp | "
                 f"{-r['residual_S_fall']:+.4f} |")
    L += ['', 'Columns (ii)-(iv) sum to the gap exactly (sequential decomposition; the order is a choice).',
          '', '## Where the 2018-2023 excess building went (census counts, private dwellings)', '',
          f"Completions {boom['built']:,.0f} (consents lagged, so the pipeline is already excluded); "
          f"net stock change {boom['d_stock']:,.0f}; net removals (the recent replacement surge) = completions - stock "
          f"change = {boom['net_removals']:,.0f}; a higher vacancy rate absorbed "
          f"{boom['vacancy_rate_rise_absorbed']:+,.0f}; households (occupied + away) {boom['households']:+,.0f}. "
          f"For information: dwellings under construction at census changed by "
          f"{boom['d_under_construction']:+,.0f} (not subtracted: the lag already accounts for them)."]
    with open(layout.writing(OUT_MD), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
