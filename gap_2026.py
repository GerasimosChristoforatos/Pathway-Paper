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
  Model             M = the central run's 2026 requirement (S1, long-run replacement).

Sequential decomposition of O - M (the order is a choice and is stated):
  (ii)  S2: what the 2018-23 replacement regime would add to M (full re-run,
        NET_REPLACEMENT_WINDOW = (2018, 2023)).
  (iii) population: actual growth in the year ended June 2026 (Stats NZ,
        provisional) minus the 2024-base projection median for that year,
        converted to dwellings as households / (1 - v) at the model's 2026
        household size and vacancy. Timing: projection growth is for years
        ended June and is applied by the model to calendar years (half-year
        offset, stated in MODEL_REVIEW 3.8).
  With M' = M + (ii) + (iii):
  (i)   pipeline: W x (c C25 - M'), completions in 2026 from 2025 consents
        above the requirement;
  (iv)  residual: (1 - W) x (c C26 - M'), completions from 2026 consents above
        the requirement, expressed as the rise in vacancy, or fall in household
        size, it would imply if built and not offset.
Also reported: where the 2018-23 excess building went, from census counts.

Writes outputs/gap_2026.md and outputs/gap_2026.json.
"""
import contextlib
import importlib
import io
import json
import os
import re

import numpy as np
import pandas as pd

import Boss
import validation

OUT_MD = os.path.join(Boss.OUT_DIR, 'gap_2026.md')
OUT_JSON = os.path.join(Boss.OUT_DIR, 'gap_2026.json')
POP_RELEASE = os.path.join(Boss.DATA_DIR, 'raw', 'national_population_estimates_june_2026.html')


def run(**settings):
    M = importlib.reload(Boss)
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


def requirement_2026(B):
    E = B['engine_out']['50th']
    return float(E['dwell_in_scope'][1] + E['rv_units'][1])


def actual_growth_ye_june_2026():
    """Provisional population growth, year ended June 2026, parsed from the
    saved Stats NZ release page (see MANIFEST). Returns (growth, text)."""
    t = open(POP_RELEASE, encoding='utf-8', errors='ignore').read()
    m = re.search(r"population grew by ([\d,]+) \(([\d.]+) percent\)", t)
    if not m:
        raise ValueError('Growth statement not found in the population release page.')
    return float(m.group(1).replace(',', '')), m.group(0)


def projected_growth_ye_june_2026():
    raw = pd.read_excel(Boss.FILE_POP_PROJ, sheet_name=Boss.POP_SHEET_PROJ, skiprows=5)
    g = Boss.locate_projection_block(raw).set_index('Year')
    return {p: float(g.loc[2026, f'PopGrowth_{p}']) * 1000 for p in ('5th', '50th', '95th')}


def boom_2018_2023(B):
    """Where 2018-23 completions went (census counts, private dwellings)."""
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
                net_removals=built - d_stock - d_uc, vacancy_rate_rise_absorbed=vac, households=hh)


def main():
    B = run()
    c, W = Boss.COMPLETION_RATE, B['lag_w']
    C25 = float(B['hist_units_all'].loc[2025])
    chk = validation.check_2026(B)
    if chk['status'] != 'observed':
        raise SystemExit('No 2026 consents in the consent file: nothing to decompose.')
    C26 = {'Jan-Jul 2026 / seasonal share': chk['observed_ytd'] / chk['seasonal_share'],
           'latest 12 months': chk['observed_last12']}
    M = requirement_2026(B)
    B2 = run(NET_REPLACEMENT_WINDOW=(2018, 2023))
    M_S2 = requirement_2026(B2)
    run()                                             # restore module defaults
    d_S2 = M_S2 - M
    E1, E2 = B['engine_out']['50th'], B2['engine_out']['50th']
    rep = lambda E: float(E['demol'][1] + E['unc'][1] - E['dev'][1])     # replacement at the calibrated rate
    s2_rate, s2_dev = rep(E2) - rep(E1), float(E2['dev'][1] - E1['dev'][1])
    dev_in_M = float(E1['dev'][1])                   # 2025 deviation carried into 2026 (S1)

    E = B['engine_out']['50th']
    S26, v26, stock25 = float(E['S'][1]), float(E['v'][1]), float(E['prev'][1])
    g_act, g_text = actual_growth_ye_june_2026()
    g_proj = projected_growth_ye_june_2026()
    d_pop_persons = g_act - g_proj['50th']
    d_pop = d_pop_persons / S26 / (1.0 - v26)        # households, plus vacancy allowance

    rows = []
    for lab, C in C26.items():
        O = c * ((1 - W) * C + W * C25)
        for scen, add_S2 in (('S1 (long-run replacement)', 0.0), ('S2 (2018-23 regime)', d_S2)):
            Mp = M + add_S2 + d_pop
            pipe = W * (c * C25 - Mp)
            resid = (1 - W) * (c * C - Mp)
            rows.append(dict(C26_estimate=lab, C26=C, scenario=scen, observed_implied=O, model=M,
                             S2_adds=add_S2, population=d_pop, pipeline=pipe, residual=resid,
                             gap=O - M, check=O - M - (add_S2 + d_pop + pipe + resid),
                             residual_vacancy_pp=100 * resid / stock25,
                             residual_S_fall=S26 - S26 * float(E['hh'][1]) / (float(E['hh'][1]) + resid * (1 - v26))))
    boom = boom_2018_2023(B)
    res = dict(completion_rate=c, lag_w=W, consents_2025=C25, model_requirement_2026=M,
               carried_2025_deviation_in_2026=dev_in_M, S2_rate_effect=s2_rate, S2_deviation_effect=s2_dev,
               model_requirement_2026_S2=M_S2, S_2026=S26, v_2026=v26, stock_2025=stock25,
               population_growth_ye_june_2026_actual=g_act, population_growth_source_text=g_text,
               population_growth_ye_june_2026_projection=g_proj, rows=rows, boom_2018_2023=boom)
    with open(OUT_JSON, 'w') as f:
        json.dump(res, f, indent=2)

    L = ['# 2026 gap decomposition (A1 evidence; nothing here is used to set a parameter)', '',
         f"Dwellings completed in 2026, all categories. Completion rate {c:.2f}, lag W = {W:.3f} yr; "
         f"2025 consents {C25:,.0f}; model 2026 requirement {M:,.0f} (S2: {M_S2:,.0f}). The requirement "
         f"already includes {dev_in_M:+,.0f} of the carried 2025 deviation (other_dev_2025 x rho). "
         f"S2 adds {d_S2:+,.0f}: {s2_rate:+,.0f} from the higher replacement rate and {s2_dev:+,.0f} because "
         f"a higher rate leaves less of 2025's building to be carried as a deviation.", '',
         f"Population, year ended June 2026: actual {g_act:,.0f} (Stats NZ release, provisional: "
         f"\"{g_text}\") vs 2024-base projection median {g_proj['50th']:,.0f} "
         f"(5th {g_proj['5th']:,.0f}, 95th {g_proj['95th']:,.0f}) -> {d_pop_persons:+,.0f} persons = "
         f"{d_pop:+,.0f} dwellings at S = {S26:.3f}, v = {100 * v26:.2f}%.", '',
         '| 2026 consents estimate | scenario | observed-implied completions | model | gap | (ii) S2 adds | '
         '(iii) population | (i) pipeline from 2025 | (iv) residual | residual as vacancy rise | '
         'or as fall in household size |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['C26_estimate']} ({r['C26']:,.0f}) | {r['scenario']} | {r['observed_implied']:,.0f} | "
                 f"{r['model']:,.0f} | {r['gap']:+,.0f} | {r['S2_adds']:+,.0f} | {r['population']:+,.0f} | "
                 f"{r['pipeline']:+,.0f} | {r['residual']:+,.0f} | {r['residual_vacancy_pp']:+.2f} pp | "
                 f"{-r['residual_S_fall']:+.4f} |")
    L += ['', 'Columns (ii)-(iv) sum to the gap exactly (sequential decomposition; the order is a choice).',
          '', '## Where the 2018-2023 excess building went (census counts, private dwellings)', '',
          f"Completions {boom['built']:,.0f}; net stock change {boom['d_stock']:,.0f}; of the rest, more under "
          f"construction {boom['d_under_construction']:+,.0f} and net removals (redevelopment) "
          f"{boom['net_removals']:,.0f}; a higher vacancy rate absorbed {boom['vacancy_rate_rise_absorbed']:+,.0f}; "
          f"households (occupied + away) {boom['households']:+,.0f}."]
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
