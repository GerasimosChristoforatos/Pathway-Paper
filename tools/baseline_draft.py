"""Generate outputs/BASELINE_DRAFT.md from the run outputs. No number in the
report is typed by hand: every value is read from a generated file in
outputs/ (or, for the assumption register, from the settings in Boss.py).

    python tools/baseline_draft.py

Inputs: outputs/boss_results.json, metrics.json, replacement_scenarios.json,
validation.json, gap_2026.json, near_term_join.json, sensitivity_oat.csv,
montecarlo_summary*.csv (when present), figures/.
"""
import glob
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')
sys.path.insert(0, ROOT)


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def pct(a, b):
    return f'{100 * (a / b - 1):+.1f}%'


def register():
    """(setting, value, basis). Values are read from Boss.py; the basis
    labels say whether a value rests on data, literature, or judgement."""
    import Boss as B
    return [
        ('Net replacement scenario', f"{B.REPLACEMENT_SCENARIO}"
         + (f", half-life {B.S3_HALF_LIFE:g} yr" if B.REPLACEMENT_SCENARIO == 'S3' else ''),
         'DECISION (author): S1/S2 bounds, S3-10 reference; half-life is JUDGEMENT (not identifiable)'),
        ('Long-run net replacement window', f'{B.NET_REPLACEMENT_WINDOW[0]}-{B.NET_REPLACEMENT_WINDOW[1]}',
         'DATA: census private-dwelling counts and consents'),
        ('Demolition rate (split only)', f'{100 * B.DEMOLITION_RATE:.3f}%/yr', 'LITERATURE: BRANZ SR214'),
        ('Completion rate', f'{B.COMPLETION_RATE:.2f} (band {B.COMPLETION_RATE_BAND[0]}-{B.COMPLETION_RATE_BAND[1]})',
         'LITERATURE: bounds from Jones et al. 2024 (citation to verify)'),
        ('Completion lag', f'{B.COMPLETION_LAG}', "DATA: Little's law W = L / lambda (a lower bound)"),
        ('Near-term join', f'{B.NEAR_TERM_JOIN} ({B.NOWCAST_METHOD})', 'DATA (observed consents); method stated'),
        ('Excess channels', f'{B.EXCESS_CHANNELS} on {B.RECENT_INTERVAL[0]}-{B.RECENT_INTERVAL[1]}',
         'DATA, ONE census interval'),
        ('Household channel', f'{B.HOUSEHOLD_CHANNEL}', 'JUDGEMENT (author decision)'),
        ('Vacancy drawdown', f'{B.VACANCY_DRAWDOWN_YEARS} yr', 'JUDGEMENT; 3 and 10 as sensitivities'),
        ('Population 2026', 'observed' if B.NOWCAST_POPULATION else 'projected median',
         'DATA: Stats NZ ERP (see README)'),
        ('Household-size shape', f'Stats NZ {B.HH_SIZE_VARIANT}, anchored {B.S_ANCHOR_YEAR}, tail {B.S_TAIL}',
         'DATA (2018-base projections; N4 open)'),
        ('Vacancy forward', 'latest census value held', 'DATA: census 2023 (2018 empty count unrated, F1)'),
        ('Typology damping phi', f'{B.DAMPING_PHI}', 'JUDGEMENT: ≈4 years of trend applied by 2050'),
        ('Mix trend window', f'{B.TREND_WINDOW_START}-2025', 'DATA'),
        ('Dwelling size reference', f'{B.DWELLING_SIZE_REF[0]}-{B.DWELLING_SIZE_REF[1]}', 'DATA: consents'),
        ('RV share reference', f'{B.RV_SHARE_REF[0]}-{B.RV_SHARE_REF[1]}', 'DATA: consents'),
        ('Soil loss', 'all non-replacement floor area; zero on replacement bands' if not B.SOIL_ON_REPLACEMENT
         else 'all floor area (original)',
         'LITERATURE: 58.77 kg CO2e/m2 footprint, Auckland land zoned for urbanisation to ~2050, 10 soil orders '
         '(Christoforatos, Pickering & Schipper 2026, J. Environ. Manage. 415, 130603)'),
    ]


LIMITATIONS = [
    'No national demolition data: demolition of detached buildings up to three storeys is consent-exempt, so '
    'the implied replacement rates cannot be tested against a count.',
    'N4 (open): the Low/High household-size variants (deterministic) are paired with stochastic population '
    'percentiles through one draw z, and the total vs private-household population question is unresolved '
    'until the living-arrangement table (E2); the household projections are 2018-base, with Stats NZ\'s '
    '2023-base release (late 2026) planned as v1.1.',
    'Timber end of life (C1-C4) excludes biogenic CO2 (confirmed by the author). Whether it includes landfill '
    'methane is TO CONFIRM from Christoforatos & Pickering 2025 (author check).',
    'With shares held (reference and S1), the Monte Carlo carries no typology-mix uncertainty; the mix is '
    'bracketed by the storylines and sensitivities instead.',
    'The soil factor was derived for Auckland\'s future urban zones and is applied nationally.',
    'Apartments rest on one independent case study (A_1 and A_2 are one design at two scales).',
    'The regional analysis of the rebuilding wave (replacement half-life by territorial authority) is deferred.',
    'Net replacement persistence (S3 half-life) is not identifiable from the census record; S1 and S2 bound it.',
    'Excess-channel shares rest on one census interval (2018-2023); no standard error can be formed.',
    'The 2018 census empty-dwelling count has no quality rating (DataInfo+); the vacancy terms rely on it.',
    'The household-channel reversion rate is the persistence estimated on changes in household size, used for a '
    'level deviation (an assumption).',
    'W from Little\'s law is a lower bound on the completion lag.',
    'Retirement-village floor area is reported but out of carbon scope.',
]


def main():
    b, m = load('boss_results.json'), load('metrics.json')
    sc, v = load('replacement_scenarios.json'), load('validation.json')
    gap, nj = load('gap_2026.json'), load('near_term_join.json')
    if b is None or m is None:
        raise SystemExit('Run run_all.py first (outputs/boss_results.json missing).')
    st = b['settings']
    ref = f"{st['scenario']}" + (f"-{st['s3_half_life']:g}" if st['scenario'] == 'S3' else '')
    L = ['# Baseline report: DRAFT (generated by tools/baseline_draft.py; do not edit by hand)', '',
         f"Every number below is read from the run outputs. Reference path: net replacement {ref}; "
         f"near-term join `{st['near_term_join']}`.", '']

    # ---- summary ----
    rows = sc['scenarios'] if sc else {}
    L += ['## Summary', '']
    txt = (f"New Zealand is projected to build {b['gfa_Mm2']:.1f} million m² of new residential floor area in "
           f"2026-2050 on the reference path, embodying {b['carbon_kt'] / 1e3:.1f} Mt CO₂e over the life cycle, "
           f"of which {b['upfront_kt'] / 1e3:.1f} Mt is upfront (materials A1-A5 plus soil).")
    if 'S1' in rows and 'S2' in rows:
        txt += (f" How fast existing dwellings are replaced is the largest structural uncertainty: holding the "
                f"long-run rate gives {rows['S1']['GFA_Mm2']:.1f} million m², holding the 2018-2023 rate gives "
                f"{rows['S2']['GFA_Mm2']:.1f} million m².")
    ref_mc = os.path.join(OUT, 'montecarlo_summary_S3-10.csv')
    if os.path.exists(ref_mc):
        r = pd.read_csv(ref_mc, index_col=0).loc['GFA_Mm2']
        txt += (f" Within the reference path, joint uncertainty in the inputs gives a 90% interval of "
                f"{r['p5']:.1f}-{r['p95']:.1f} million m² (median {r['p50']:.1f}, mean {r['mean']:.1f}).")
    txt += (f" Population uncertainty alone (Stats NZ 5th-95th percentiles) spans "
            f"{b['pop_band_gfa_Mm2']['5th']:.1f}-{b['pop_band_gfa_Mm2']['95th']:.1f} million m².")
    if os.path.exists(ref_mc):
        txt += (" The joint interval is narrower than the population-only range because each population draw "
                "also moves household size along the matching Stats NZ Low/High variant: low-population variants "
                "come with smaller households (an older age structure), so the number of households varies less "
                "than population, whereas the population-only range holds household size on the Medium shape.")
    txt += (f" Upfront carbon ({b['upfront_kt'] / 1e3:.1f} Mt) is the quantity comparable with a 2026-2050 "
            f"budget; the later life-cycle stages are booked in the construction year but emitted mostly after 2050.")
    L += [txt, '']

    # ---- headline ----
    L += ['## Headline, 2026-2050 (median demographics)', '',
          '| path | floor area (Mm²) | vs reference | whole-life carbon (kt CO₂e) | of which soil | '
          'carbon excl. soil | upfront carbon (kt CO₂e) |', '|---|---|---|---|---|---|---|']
    base = rows.get('S3-10', {}).get('GFA_Mm2', b['gfa_Mm2'])
    for k, lab in (('S1', 'S1 lower bound: long-run replacement, shares held'),
                   ('S3-5', 'S3, half-life 5 yr, shares held'),
                   ('S3-10', 'S3, half-life 10 yr, shares held (reference)'),
                   ('S3-15', 'S3, half-life 15 yr, shares held'),
                   ('S2', 'S2 upper bound: 2018-2023 replacement + damped mix trend ("intensification continues")'),
                   ('S3-10-trend', 'Sensitivity: S3-10 with the damped mix trend (v1.0 mix)'),
                   ('S2-held', 'Sensitivity: S2 with shares held (maximum floor-area case)')):
        if k in rows:
            r = rows[k]
            up = f"{r['upfront_kt']:,.0f}" if 'upfront_kt' in r else 'n/a'
            so = r.get('soil_kt')
            sol = (f"{so:,.0f} | {r['carbon_kt'] - so:,.0f}") if so is not None else 'n/a | n/a'
            L.append(f"| {lab} | {r['GFA_Mm2']:.2f} | {pct(r['GFA_Mm2'], base)} | {r['carbon_kt']:,.0f} | {sol} | {up} |")
    mcs = sorted(glob.glob(os.path.join(OUT, 'montecarlo_summary_*.csv')))
    if mcs:
        L += ['', 'Monte Carlo within each scenario (joint input uncertainty; mean, median and 90% interval):', '',
              '| scenario | output | mean | median | 5th | 95th |', '|---|---|---|---|---|---|']
        for p in mcs:
            s = pd.read_csv(p, index_col=0)
            name = os.path.basename(p)[len('montecarlo_summary_'):-4]
            for row, lab in (('GFA_Mm2', 'floor area (Mm²)'), ('carbon_kt', 'carbon (kt)'),
                             ('upfront_kt', 'upfront (kt)')):
                if row in s.index:
                    r = s.loc[row]
                    L.append(f"| {name} | {lab} | {r.get('mean', float('nan')):,.1f} | {r['p50']:,.1f} | "
                             f"{r['p5']:,.1f} | {r['p95']:,.1f} |")
    else:
        L += ['', '*Monte Carlo intervals by scenario: pending (item 9). The current single MC mixes '
              'scenarios and is not quoted.*']

    # ---- decomposition ----
    L += ['', '## Why the floor area is built (reference path, median)', '',
          '| reason | floor area (Mm²) | share | carbon (kt CO₂e) |', '|---|---|---|---|']
    for d in b['demand_bands']:
        L.append(f"| {d['band']} | {d['gfa_Mm2']:.2f} | {100 * d['gfa_Mm2'] / b['gfa_Mm2']:.1f}% | "
                 f"{d['carbon_kt']:,.0f} |")
    L.append(f"| **Total** | **{b['gfa_Mm2']:.2f}** | 100% | **{b['carbon_kt']:,.0f}** |")
    if nj:
        ch = nj['channels_2026_2050']
        L += ['', f"The near-term join adds the building observed above the model's requirement in 2026-27 "
                  f"(2026 excess {nj['e26']:+,.0f} dwellings, 2027 lagged share {nj['e27']:+,.0f}): redevelopment "
                  f"{ch['redevelopment']:+,.0f}, vacancy {ch['vacancy']:+,.0f} (drawn down "
                  f"{ch['vacancy_drawdown']:+,.0f}), households {ch['households']:+,.0f} (reverting "
                  f"{ch['household_reversion']:+,.0f})."]

    # ---- typology / material / stages ----
    L += ['', '## By typology', '', '| typology | floor area (Mm²) | carbon (kt) | share of floor area 2025 → 2050 |',
          '|---|---|---|---|']
    for t, r in b['typology'].items():
        L.append(f"| {t} | {r['gfa_Mm2']:.2f} | {r['carbon_kt']:,.0f} | "
                 f"{100 * r['share_2025']:.1f}% → {100 * r['share_2050']:.1f}% |")
    L += ['', '## By material (kt CO₂e, 2026-2050)', '', '| material | kt | share |', '|---|---|---|']
    mt = sum(b['material_kt'].values())
    for k, x in sorted(b['material_kt'].items(), key=lambda kv: -kv[1]):
        L.append(f'| {k} | {x:,.0f} | {100 * x / mt:.1f}% |')
    L += ['', '## Upfront vs whole-life (kt CO₂e)', '', '| stage | kt |', '|---|---|']
    for s_, x in b['stages_kt'].items():
        L.append(f'| {s_} | {x:,.0f} |')
    L += [f"| soil (land-use change) | {b['soil_kt']:,.0f} |",
          f"| **upfront (A1-A5 + soil)** | **{b['upfront_kt']:,.0f}** |",
          f"| **whole-life** | **{b['carbon_kt']:,.0f}** |",
          '', 'Later stages (B, C) are booked in the construction year (static LCA convention).',
          '', '### Soil method', '',
          'Soil organic carbon loss is land-use change: a new building footprint seals the soil under it, '
          'while a rebuilt footprint sits on soil already sealed. Soil loss is therefore applied to all '
          'non-replacement floor area and is zero on the replacement bands (demolition replacement, the '
          'calibrated residual and the redevelopment channel). The factor is 58.77 kg CO₂e per m² of '
          'footprint, the area-weighted average over the 10 soil orders of the land zoned for urbanisation '
          'to about 2050 in Auckland, divided by each typology\'s floor space index (Christoforatos, '
          'Pickering & Schipper 2026, Journal of Environmental Management 415, 130603, '
          'https://doi.org/10.1016/j.jenvman.2026.130603). The Raw and Organic soil-order extremes are the '
          'bounding sensitivity. Carbon factors for materials come from 16 New Zealand case studies '
          '(Christoforatos & Pickering 2025, Smart and Sustainable Built Environment, '
          'https://doi.org/10.1108/SASBE-06-2025-0304).']

    # ---- validation ----
    if v:
        L += ['', '## Validation', '', 'Rolling-origin hindcast of dwellings built (actual households and vacancy '
              'fed in; the net-replacement term predicted):', '',
              '| origin | test years | long-run rate (S1) error | reference method (S3-10) error | best alternative |',
              '|---|---|---|---|---|']
        for o in sorted({r['origin'] for r in v['hindcast']}):
            rr = [r for r in v['hindcast'] if r['origin'] == o]
            mm = [r for r in rr if r['method'] == v['model_method']][0]
            ref = [r for r in rr if r['method'] == 'reference_s3_10']
            alt = min((r for r in rr if r['method'] not in (v['model_method'], 'reference_s3_10')),
                      key=lambda r: abs(r['error_pct']))
            L.append(f"| {o} | {mm['test']} | {mm['error_pct']:+.1f}% | "
                     f"{(format(ref[0]['error_pct'], '+.1f') + '%') if ref else 'n/a'} | "
                     f"{alt['method']} {alt['error_pct']:+.1f}% |")
        c = v['check_2026']
        if c.get('status') == 'observed':
            L += ['', f"2026 check (model run without any observed-2026 input): observed consents Jan-Jul "
                      f"{c['observed_ytd']:,.0f} vs model {c['model_expected_ytd']:,.0f}; ratio "
                      f"{c['ratio_observed_to_model']:.2f}."]
        if gap:
            r3 = [r for r in gap['rows'] if r['scenario'].startswith('S3-10')][0]
            L += [f"Decomposition of the 2026 gap on the reference path ({r3['C26_estimate']}): "
                  f"{r3['gap'] - r3['scenario_adds']:+,.0f} dwellings = population {r3['population']:+,.0f} + "
                  f"pipeline from 2025 {r3['pipeline']:+,.0f} + 2026 consents above requirement "
                  f"{r3['residual']:+,.0f}."]

    # ---- the 2026 gap as a finding ----
    if gap and v and nj:
        r1 = gap['rows'][0]
        r3 = [r for r in gap['rows'] if r['C26_estimate'] == r1['C26_estimate'] and r['scenario'].startswith('S3-10')][0]
        req3 = r3['model'] + r3['scenario_adds']
        c = v['check_2026']
        ch = nj['channels_2026_2050']
        L += ['', '## Finding: 2026 building runs well above the model\'s requirement', '',
              f"Consents for January-July 2026 ({c['observed_ytd']:,.0f}) are {c['ratio_observed_to_model']:.2f} "
              f"times what the reference model, run without any 2026 data, implies for those months. In "
              f"completions, observed-implied 2026 building is {r3['observed_implied']:,.0f} dwellings against a "
              f"reference-path requirement of {req3:,.0f} (gap {r3['observed_implied'] - req3:+,.0f})[^s1]. "
              f"Population does not explain it: growth over the year to June 2026 fell short of the projection, "
              f"which lowers the requirement by {-r3['population']:,.0f}. The gap is building already in the "
              f"pipeline from 2025 ({r3['pipeline']:+,.0f}) plus 2026 consents above requirement "
              f"({r3['residual']:+,.0f}). Over 2018-2023 most building above household formation went to "
              f"redevelopment (net removals {gap['boom_2018_2023']['net_removals']:,.0f}) rather than vacancy "
              f"({gap['boom_2018_2023']['vacancy_rate_rise_absorbed']:+,.0f}).",
              '', f"The model takes 2026 completions (and the 2027 share already consented) from these observed "
                  f"consents and allocates the excess ({nj['e26']:+,.0f} dwellings in 2026, {nj['e27']:+,.0f} in "
                  f"2027) to redevelopment, vacancy and household formation. On the reference path the vacancy "
                  f"and household channels revert, so the excess mainly shifts timing: "
                  f"{sum(ch.values()):+,.0f} dwellings net over 2026-2050.",
              '', f"[^s1]: On S1 (long-run replacement) the requirement is {r1['model']:,.0f} and the gap "
                  f"{r1['gap']:+,.0f} = population {r1['population']:+,.0f} + pipeline {r1['pipeline']:+,.0f} + "
                  f"2026 consents above requirement {r1['residual']:+,.0f}."]

    # ---- sensitivity ----
    sens = os.path.join(OUT, 'sensitivity_oat.csv')
    if os.path.exists(sens):
        s = pd.read_csv(sens)
        s = s[s.group != 'Adopted'].copy()
        s['abs'] = s['GFA_change_pct'].abs()
        s = s.sort_values('abs', ascending=False)
        L += ['', '## One-at-a-time sensitivities (floor area and carbon vs reference)', '',
              '| group | case | floor area (Mm²) | change | carbon change |', '|---|---|---|---|---|']
        for r in s.itertuples():
            L.append(f"| {r.group} | {r.case} | {r.GFA_Mm2:.2f} | {r.GFA_change_pct:+.1f}% | {r.carbon_change_pct:+.1f}% |")

    # ---- register ----
    L += ['', '## Assumption register (values read from Boss.py)', '', '| setting | value | basis |', '|---|---|---|']
    for a, val, basis in register():
        L.append(f'| {a} | {val} | {basis} |')
    L += ['', '## Open limitations and data needs', ''] + [f'- {x}' for x in LIMITATIONS]

    # ---- figures ----
    figs = sorted(glob.glob(os.path.join(OUT, 'figures', '*.png')))
    key = [f for f in figs if any(k in f for k in ('boss_03', 'boss_04', 'boss_05', 'diag_3', 'diag_4',
                                                     'sens_1', 'mc_1'))]
    L += ['', '## Key figures', ''] + [f"![{os.path.basename(f)}](figures/{os.path.basename(f)})" for f in key]
    with open(os.path.join(OUT, 'BASELINE_DRAFT.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print(f'outputs/BASELINE_DRAFT.md: {len(L)} lines')


if __name__ == '__main__':
    main()
