"""The Reference and its replacement variants (naming.SCENARIOS): Low replacement, High
replacement and the Reference with half-lives 5 and 15 years, side by side. EVIDENCE for
the author's choice of the Reference and its bracket; nothing here sets a parameter, and
2026 is not used to fit anything (the 2026 comparison is reported, not targeted).

Every number is computed from full projection runs with the current defaults and
only REPLACEMENT_VARIANT / REPLACEMENT_HALF_LIFE changed.

    python tools/replacement_scenarios.py      # -> outputs/reports/scenarios.md, outputs/data/baseline/scenarios.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import layout  # noqa: E402
import naming as N  # noqa: E402
import validation  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = layout.report('scenarios.md')                    # frozen_technology/ in the frozen check run
OUT_JSON = layout.data('baseline/scenarios.json')
OUT_ANNUAL = layout.data('baseline/variants_annual.csv')        # MODEL v1.0.0 addition
# the Reference and its variants (typology shares held in every run); REF_HL5 and REF_HL15 are
# half-life sensitivities; the _NOUC rows drop the census under-construction correction
SCENARIOS = [(k, N.SCENARIOS[k], s) for k, s in (
    ('LOW', dict(REPLACEMENT_VARIANT='LOW')),
    ('REF_HL5', dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=5.0)),
    ('REF', dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0)),
    ('REF_HL15', dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=15.0)),
    ('HIGH', dict(REPLACEMENT_VARIANT='HIGH')),
    ('LOW_NOUC', dict(REPLACEMENT_VARIANT='LOW', CENSUS_UC_CORRECTION=False)),
    ('REF_NOUC', dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0, CENSUS_UC_CORRECTION=False)),
    ('HIGH_NOUC', dict(REPLACEMENT_VARIANT='HIGH', CENSUS_UC_CORRECTION=False)))]


def one(settings):
    B = validation.run_boss(**settings)
    E = B['engine_out']['50th']
    fy = B['forecast_years']
    f = slice(1, None)                                        # 2026-2050
    rate = np.asarray(B['rate_path'], float)
    resid_long = float(B['unconsented_rate'])                 # long-run residual (net unconsented additions)
    net_removals = E['demol'] + E['unc'] - E['dev']           # rate x last year's stock
    gross_demol = (rate - resid_long) * E['prev']             # if the long-run residual persists
    ji = B['join_info'].get('50th') if B['join_info'] else None
    out = dict(
        GFA_Mm2=float(B['results']['50th']['total'][f].sum() / 1e6),
        carbon_kt=float(B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6),
        upfront_kt=float(B['_upfront'] + B['_soil'] / 1e6),
        size_2050=float(E['D'][-1]),
        soil_kt=float(B['_soil'] / 1e6),
        rate_pct={int(y): float(100 * rate[i]) for i, y in enumerate(fy) if y in (2026, 2030, 2040, 2050)},
        net_removals_per_yr_mean=float(net_removals[f].mean()),
        net_removals={int(y): float(net_removals[i]) for i, y in enumerate(fy) if y in (2026, 2050)},
        gross_demolitions_per_yr_mean=float(gross_demol[f].mean()),
        gross_demolitions={int(y): float(gross_demol[i]) for i, y in enumerate(fy) if y in (2026, 2050)},
        cumulative_net_removals_share_of_2025_stock=float(net_removals[f].sum() / E['stock'][0]),
        redevelopment_channel=float(ji['redev'][1:].sum()) if ji else None,
        join_net=float(ji['join'][f].sum()) if ji else None,
        R26=ji['R26'] if ji else None, O26=ji['O26'] if ji else None, e26=ji['e26'] if ji else None,
        e27=ji['e27'] if ji else None)
    return out, B


def annual(key, B):
    """Annual floor area (in scope) and embodied carbon 2026-2050 of one variant (median demographics)."""
    fy = np.asarray(B['forecast_years'])
    g = np.asarray(B['results']['50th']['total'], float)
    c = B['carbon_total_typ'].sum(axis=1).values
    return [dict(variant=key, year=int(y), floor_area_Mm2=float(g[i]) / 1e6, carbon_kt=float(c[i]) / 1e6)
            for i, y in enumerate(fy) if i > 0]


def main():
    res, B1, rows = {}, None, []
    for key, lab, s in SCENARIOS:
        res[key], B = one(s)
        res[key]['label'] = lab
        rows += annual(key, B)
        B1 = B if key == 'LOW' else B1
    pd.DataFrame(rows).to_csv(layout.writing(OUT_ANNUAL), index=False)
    cr = B1['census_rates']
    long_pct = 100 * (float(B1['demolition_rate']) + float(B1['unconsented_rate']))
    import engine
    raw = engine.census_interval_rates(B1['census']['total_private'], B1['consents_monthly'],
                                       float(B1['_completion']), float(B1['lag_w']))      # no UC correction
    hist = [dict(interval=f"{int(r.y0)}-{int(r.y1)}", rate_pct=100 * float(r.rate),
                 rate_uncorrected_pct=100 * float(q.rate), d_uc=float(r.d_uc) if r.uc_corrected else None,
                 net_removals_per_yr=float((r.built - r.d_stock) / (r.y1 - r.y0)))
            for r, q in zip(cr.itertuples(), raw.itertuples())]
    w = [f'{a}-{b}' for a, b in ((1991, 2023), (2018, 2023))]
    rate_cmp = {lab: dict(uncorrected=100 * engine.census_window_rate(raw, *ab), corrected=100 * engine.census_window_rate(cr, *ab))
                for lab, ab in zip(w, ((1991, 2023), (2018, 2023)))}
    meta = dict(demolition_rate_pct=100 * float(B1['demolition_rate']),
                residual_long_pct=100 * float(B1['unconsented_rate']), long_run_pct=long_pct,
                recent_pct=100 * float(B1['rate_recent']), stock_2025=float(B1['engine_out']['50th']['stock'][0]),
                join_mode=B1['_join_mode'], census_intervals=hist, rate_windows=rate_cmp)
    with open(layout.writing(OUT_JSON), 'w') as f:
        json.dump(N.keys(dict(meta=meta, scenarios=res)), f, indent=2)

    s1 = res['LOW']
    L = ['# The Reference and its replacement variants (generated by tools/replacement_scenarios.py)', '',
         f"Current defaults, 2026 overbuild rule `{meta['join_mode']}`; only the replacement variant changes. Net "
         f"replacement = "
         f"demolition ({meta['demolition_rate_pct']:.3f}%/yr, BRANZ SR214) + residual. Long run 1991-2023: "
         f"{meta['long_run_pct']:.3f}%/yr (residual {meta['residual_long_pct']:+.3f}%, i.e. net unconsented "
         f"additions); 2018-2023 interval: {meta['recent_pct']:.3f}%/yr. Stock end-2025: "
         f"{meta['stock_2025']:,.0f} dwellings.", '',
         '## Totals and implied removals (median demographics)', '',
         '| variant | floor area 2026-2050 (Mm2) | vs Low | carbon (kt) | rate 2026 / 2030 / 2040 / 2050 (%/yr) | '
         'net removals /yr, mean 2026-2050 | gross demolitions /yr, mean (if long-run residual persists) | '
         'cumulative net removals, % of 2025 stock |', '|---|---|---|---|---|---|---|---|']
    for k, r in res.items():
        rp = ' / '.join(f"{r['rate_pct'][y]:.3f}" for y in (2026, 2030, 2040, 2050))
        L.append(f"| {r['label']} | {r['GFA_Mm2']:.2f} | {100 * (r['GFA_Mm2'] / s1['GFA_Mm2'] - 1):+.1f}% | "
                 f"{r['carbon_kt']:,.0f} | {rp} | {r['net_removals_per_yr_mean']:,.0f} | "
                 f"{r['gross_demolitions_per_yr_mean']:,.0f} | "
                 f"{100 * r['cumulative_net_removals_share_of_2025_stock']:.1f}% |")
    if s1['R26'] is not None:
        L += ['', '## Against the 2026 overbuild (reported, NOT fitted)', '',
              'O = observed-implied 2026 completions (all categories, nowcast consents); R = the variant\'s '
              '2026 requirement before the overbuild; the excess O - R is the 2026 overbuild. '
              'Share of the Low excess = how much of it the variant\'s own replacement requirement covers.', '',
              '| variant | O 2026 | R 2026 | excess 2026 | share of Low excess covered | gap_ref (2027) | '
              'booked as redevelopment, dwellings |',
              '|---|---|---|---|---|---|---|']
        for k, r in res.items():
            L.append(f"| {r['label']} | {r['O26']:,.0f} | {r['R26']:,.0f} | {r['e26']:+,.0f} | "
                     f"{100 * (r['R26'] - s1['R26']) / s1['e26']:.0f}% | {r['e27']:+,.0f} | "
                     f"{r['redevelopment_channel']:+,.0f} |")
    L += ['', '## Census record of net replacement (dwelling-count identity)', '',
          'Corrected = 0.95 x consents - change in census private dwellings under construction (UC), '
          'applied when the completion lag is off (CENSUS_UC_CORRECTION).', '',
          '| interval | uncorrected (%/yr) | change in UC | corrected (%/yr) | net removals per year (corrected) |',
          '|---|---|---|---|---|']
    for h in hist:
        L.append(f"| {h['interval']} | {h['rate_uncorrected_pct']:+.3f} | "
                 f"{format(h['d_uc'], '+,.0f') if h['d_uc'] is not None else 'n/a (not corrected)'} | "
                 f"{h['rate_pct']:+.3f} | {h['net_removals_per_yr']:,.0f} |")
    L += ['', '| window | uncorrected (%/yr) | corrected (%/yr) |', '|---|---|---|']
    for lab, v in rate_cmp.items():
        L.append(f"| {lab} | {v['uncorrected']:+.3f} | {v['corrected']:+.3f} |")
    with open(layout.writing(OUT_MD), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
