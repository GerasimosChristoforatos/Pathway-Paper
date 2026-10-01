"""Item 2 of the CP2 decisions: the net-replacement scenarios S1, S2 and S3
(half-lives 5, 10, 15 years), side by side. EVIDENCE for the author's choice
of a central case or bracketing; nothing here sets a parameter, and 2026 is
not used to fit anything (the 2026 comparison is reported, not targeted).

Every number is computed from full Boss runs with the current defaults and
only REPLACEMENT_SCENARIO / S3_HALF_LIFE changed.

    python tools/replacement_scenarios.py      # -> outputs/replacement_scenarios.md, .json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import validation  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(ROOT, 'outputs', 'replacement_scenarios.md')
OUT_JSON = os.path.join(ROOT, 'outputs', 'replacement_scenarios.json')
# storylines (Boss.MIX_MODE = 'storyline'): S1 and S3 hold the mix, S2 keeps the damped trend
SCENARIOS = [('S1', 'S1: long-run rate, shares held', dict(REPLACEMENT_SCENARIO='S1')),
             ('S3-5', 'S3: fade, half-life 5 yr, shares held', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=5.0)),
             ('S3-10', 'S3: fade, half-life 10 yr, shares held (reference)',
              dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=10.0)),
             ('S3-15', 'S3: fade, half-life 15 yr, shares held', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=15.0)),
             ('S2', 'S2: 2018-2023 rate persists, damped mix trend (intensification continues)',
              dict(REPLACEMENT_SCENARIO='S2')),
             ('S3-10-trend', 'sensitivity: S3 half-life 10 with the damped mix trend (v1.0 mix)',
              dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=10.0, MIX_MODE='trend')),
             ('S2-held', 'sensitivity: S2 with shares held (maximum floor-area case)',
              dict(REPLACEMENT_SCENARIO='S2', MIX_MODE='held')),
             ('S1-noUC', 'sensitivity: S1 without the census UC correction',
              dict(REPLACEMENT_SCENARIO='S1', CENSUS_UC_CORRECTION=False)),
             ('S3-10-noUC', 'sensitivity: S3-10 without the census UC correction',
              dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=10.0, CENSUS_UC_CORRECTION=False)),
             ('S2-noUC', 'sensitivity: S2 without the census UC correction',
              dict(REPLACEMENT_SCENARIO='S2', CENSUS_UC_CORRECTION=False))]


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
        soil_kt=float(B['_soil'] / 1e6),
        rate_pct={int(y): float(100 * rate[i]) for i, y in enumerate(fy) if y in (2026, 2030, 2040, 2050)},
        net_removals_per_yr_mean=float(net_removals[f].mean()),
        net_removals={int(y): float(net_removals[i]) for i, y in enumerate(fy) if y in (2026, 2050)},
        gross_demolitions_per_yr_mean=float(gross_demol[f].mean()),
        gross_demolitions={int(y): float(gross_demol[i]) for i, y in enumerate(fy) if y in (2026, 2050)},
        cumulative_net_removals_share_of_2025_stock=float(net_removals[f].sum() / E['stock'][0]),
        redevelopment_channel=(float(ji['channels']['redevelopment'].sum()) if ji and 'channels' in ji
                               else float(ji['redev'][1:].sum()) if ji else None),
        join_net=float(ji['join'][f].sum()) if ji else None,
        channel_shares=dict(B['join_shares']) if B['join_shares'] else None,
        R26=ji['R26'] if ji else None, O26=ji['O26'] if ji else None, e26=ji['e26'] if ji else None,
        e27=ji['e27'] if ji else None)
    return out, B


def main():
    res, B1 = {}, None
    for key, lab, s in SCENARIOS:
        res[key], B = one(s)
        res[key]['label'] = lab
        B1 = B if key == 'S1' else B1
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
    with open(OUT_JSON, 'w') as f:
        json.dump(dict(meta=meta, scenarios=res), f, indent=2)

    s1 = res['S1']
    L = ['# Net-replacement scenarios S1 / S2 / S3 (item 2; generated by tools/replacement_scenarios.py)', '',
         f"Current defaults, near-term join `{meta['join_mode']}`; only the scenario changes. Net replacement = "
         f"demolition ({meta['demolition_rate_pct']:.3f}%/yr, BRANZ SR214) + residual. Long run 1991-2023: "
         f"{meta['long_run_pct']:.3f}%/yr (residual {meta['residual_long_pct']:+.3f}%, i.e. net unconsented "
         f"additions); 2018-2023 interval: {meta['recent_pct']:.3f}%/yr. Stock end-2025: "
         f"{meta['stock_2025']:,.0f} dwellings.", '',
         '## Totals and implied removals (median demographics)', '',
         '| scenario | floor area 2026-50 (Mm2) | vs S1 | carbon (kt) | rate 2026 / 2030 / 2040 / 2050 (%/yr) | '
         'net removals /yr, mean 2026-50 | gross demolitions /yr, mean (if long-run residual persists) | '
         'cumulative net removals, % of 2025 stock |', '|---|---|---|---|---|---|---|---|']
    for k, r in res.items():
        rp = ' / '.join(f"{r['rate_pct'][y]:.3f}" for y in (2026, 2030, 2040, 2050))
        L.append(f"| {r['label']} | {r['GFA_Mm2']:.2f} | {100 * (r['GFA_Mm2'] / s1['GFA_Mm2'] - 1):+.1f}% | "
                 f"{r['carbon_kt']:,.0f} | {rp} | {r['net_removals_per_yr_mean']:,.0f} | "
                 f"{r['gross_demolitions_per_yr_mean']:,.0f} | "
                 f"{100 * r['cumulative_net_removals_share_of_2025_stock']:.1f}% |")
    if s1['R26'] is not None:
        L += ['', '## Against the 2026 excess (reported, NOT fitted)', '',
              'O = observed-implied 2026 completions (all categories, nowcast consents); R = the scenario\'s '
              '2026 requirement before the join; the excess O - R is what the near-term join allocates. '
              'Share of the S1 excess = how much of it the scenario\'s own replacement requirement covers.', '',
              '| scenario | O 2026 | R 2026 | excess 2026 | share of S1 excess covered | 2027 lagged excess | '
              'channel shares (redevelopment / vacancy / households) | redevelopment channel, dwellings |',
              '|---|---|---|---|---|---|---|---|']
        for k, r in res.items():
            sh = r['channel_shares']
            L.append(f"| {r['label']} | {r['O26']:,.0f} | {r['R26']:,.0f} | {r['e26']:+,.0f} | "
                     f"{100 * (r['R26'] - s1['R26']) / s1['e26']:.0f}% | {r['e27']:+,.0f} | "
                     + (f"{sh['redevelopment']:.3f} / {sh['vacancy']:.3f} / {sh['households']:.3f}" if sh
                        else 'market excess: all redevelopment') + " | "
                     f"{r['redevelopment_channel']:+,.0f} |")
    L += ['', '## Census record of net replacement (dwelling-count identity)', '',
          'Corrected = 0.95 x consents - change in census private dwellings under construction (UC), '
          'applied when the completion lag is off (CENSUS_UC_CORRECTION).', '',
          '| interval | uncorrected (%/yr) | change in UC | corrected (%/yr) | net removals per year (corrected) |',
          '|---|---|---|---|---|']
    for h in hist:
        L.append(f"| {h['interval']} | {h['rate_uncorrected_pct']:+.3f} | "
                 f"{('%+,.0f' % h['d_uc']) if h['d_uc'] is not None else 'n/a (not corrected)'} | "
                 f"{h['rate_pct']:+.3f} | {h['net_removals_per_yr']:,.0f} |")
    L += ['', '| window | uncorrected (%/yr) | corrected (%/yr) |', '|---|---|---|']
    for lab, v in rate_cmp.items():
        L.append(f"| {lab} | {v['uncorrected']:+.3f} | {v['corrected']:+.3f} |")
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
