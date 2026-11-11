"""Methods draft of the planetary-boundary layer (AESA: absolute environmental sustainability
assessment, climate change; boundaries.py, equations in aesa.py) as implemented: equations,
constants with sources, alpha validation, coverage, source check, results. Every number is read
from outputs/data/aesa/results.json, outputs/data/aesa/sensitivity.csv and
outputs/data/metrics.json, or from the settings in boundaries.py; nothing is typed by hand.

lines() returns the Markdown of this part without its title (section headings at '##');
tools/methods.py merges it, one heading level down, into outputs/reports/METHODS_DRAFT.md,
the one methods document of the release.

    python tools/pb_methods.py          # writes outputs/reports/METHODS_DRAFT.md (all three parts)
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layout  # noqa: E402
import naming as N  # noqa: E402

SCEN_NAME = N.SCENARIOS
MAIN = ('REF', 'LOW', 'HIGH', 'VHIGH')   # the variants of the committed table (+ Very High)


def ordered(d):
    """(variant, value) pairs of d in the order of naming.SCENARIOS."""
    return [(k, d[k]) for k in SCEN_NAME if k in d] + [(k, v) for k, v in d.items() if k not in SCEN_NAME]


def ar_base_rule_lines(r):
    """The shared-parameter rule of the one-at-a-time rows (boundaries.AR_BASE_RULE, results.json
    one_at_a_time_ar_base): the statement, the recomputed bases and the rows that keep the Reference base."""
    import boundaries
    o = r['one_at_a_time_ar_base']
    ref = r['components']['I_sec_base_kg']
    L = ['## One-at-a-time rows and the AR base (shared-parameter rule)', '',
         'A shared uncertain parameter is sampled once and used wherever it applies (Groen & Heijungs 2017; Kim, '
         'Mutel & Hellweg 2025): the present-day carbon factors enter both the acquired-rights base and the '
         'projection, so rows that change their level, or an accounting convention, recompute the base; rows that '
         'change only future technology or siting do not. The recomputed base uses the function of the Monte Carlo '
         '(boundaries.base_with_factors) at the row\'s own factors; the classification is boundaries.AR_BASE_RULE.',
         '', '| row (recompute) | reason | case | Ī_sec,base (kt/yr) | vs the Reference |', '|---|---|---|---|---|']
    for k, v in o.items():
        for side, x in v.get('sides', {}).items():
            L.append(f"| {k} | {v['reason']} | {side} | {x['I_sec_base_kg'] / 1e6:,.1f} | "
                     f"{100 * (x['I_sec_base_kg'] / ref - 1):+.2f}% |")
    rec = [k for k, v in o.items() if v['rule'] == boundaries.RECOMPUTE and 'sides' not in v]
    keep = [k for k, v in o.items() if v['rule'] == boundaries.REFERENCE_BASE]
    L += ['', 'Also recomputed (by their definition, in aesa/sensitivity.csv): ' + ', '.join(rec) + '. Reference base '
          '(Ī_sec,base unchanged; the population rows move both budgets with the population path): '
          + '; '.join(f"{k} ({o[k]['reason']})" for k in keep) + '.']
    return L


def lines():
    """The AESA part as Markdown lines, without the title line (section headings at '##')."""
    import boundaries
    with open(layout.data('aesa/results.json')) as f:
        r = json.load(f)
    with open(layout.data('metrics.json')) as f:
        mm = json.load(f)
    m, run_mode = mm.get('aesa', {}), mm.get('run_mode', 'full')
    sens = pd.read_csv(layout.data('aesa/sensitivity.csv'))
    c, s, ss = r['components'], r['settings'], r['components']['s_sec_parts']
    b = c['base_year_b']
    cov = r['coverage']
    ac = r['alpha_check']
    y0, y1 = s['PB_YEARS']
    w0, w1 = s['AR_BASE_WINDOW']
    L = []
    if run_mode != 'full':
        L += ['> **' + run_mode + '** (run_all.py --profile light: fewer Monte Carlo draws, '
              'no Sobol indices).', '']
    L += [
         'The planetary-boundary layer is an absolute environmental sustainability assessment (AESA) of New '
         f'Zealand new residential construction, climate change only, {y0}-{y1}. Static carrying capacity; two '
         'allocation principles reported as a range and never averaged. This layer does not change the model; '
         'it reads the model\'s outputs.', '',
         '## Equations as implemented (aesa.py)', '',
         '**Acquired rights** (Horup et al. 2025, Sci. Total Environ. 966, 178780, Eq. 1, p. 4):', '',
         '    B_AR(t) = SOS · (Ī_sec,base / I_glob) · [P_NZ(t) / P_NZ(t0)] · [P_W(t0) / P_W(t)],   '
         f"t0 = {s['T0']}", '',
         f'Ī_sec,base is the mean annual sector impact {w0}-{w1} from this model\'s own history (same scope, '
         'accounting rule and soil convention as the projection; at the case-study factors, roughly contemporaneous with '
         'the base window and not back-cast'
         + ('' if s.get('DECARB_MODE', 'none') == 'none' else ': past construction used past technology, so the '
            'decarbonisation of A1-A3 applies only to 2026-2050') + '). Over the base window LoE_AR = I_glob / SOS = '
         f"{c['LoE_AR_base_identity']:.4f} by construction (the sector impact cancels); the information is in the "
         'trajectory relative to the base.', '',
         '**Ability to pay** (Hjalsted et al. 2021, J. Ind. Ecol. 25, 6-19, Table 2 Eqs. 5-6, p. 11; SI Eq. S1):', '',
         '    SoSOS_ind(t) = SOS / P_W(t) · (g_W / g_NZ) · α',
         '    B_AtP(t)     = SoSOS_ind(t) · P_NZ(t) · s_sec',
         '    α            = 1 / Σ_c [(P_c / P_W) (g_W / g_c)]   (SI Eq. S1 with GDP totals, rewritten per capita)', '',
         f'g = GDP per capita in base year b = {b}, held fixed; g_W = Σ P_c g_c / Σ P_c and P_W = Σ P_c over the '
         'same covered economies. B_AtP / B_AR = (g_W/g_NZ) · α · s_sec · (P_NZ(t0)/P_W(t0)) · (I_glob/Ī_sec,base) '
         f"is constant in this static design: {r['B_AtP_over_B_AR']['min']:.4f}.", '',
         '**Carbon factors.** ' + ({'none': 'All factors held at their 2025 case-study values (frozen technology).',
                                    'horup_item': 'A1-A3 of each case-study EPD item decarbonised 2026-2050 after '
                                    'Horup et al. (2025) SI Table S4 (item-level mapping, data/material_item_map.csv: '
                                    'direct, Horup p. 6, proxy or held), for construction and for the A1-A3 share of '
                                    'maintenance (B2, B4; replacement and repaint events); A4-A5 e^(-0.01 (t - 2025)) '
                                    'after Resch et al. (2021) Table 1; C1-C4, held items and soil carbon loss at 2025 '
                                    '(see outputs/reports/ASSUMPTIONS.md).'
                                    }[s.get('DECARB_MODE', 'none')]), '',
         '**Accounting.** ' + ('Time-resolved: the sector impact I_sec(t) counts the materials and construction '
                               '(A1-A5) and soil carbon loss of the construction in year t and the maintenance (B2, B4; '
                               'replacement and repaint events) that occurs in year t in buildings built from 2026. '
                               'Maintenance events after 2050 and all end-of-life emissions (C1-C4) of the 2026-2050 '
                               'cohorts are committed after 2050, reported below as a range and in years of the 2050 '
                               'AR boundary; they are not part of the cumulative LoE. On time-differentiated climate '
                               'accounting of New Zealand building elements see McLaren et al. (2025).'
                               if c.get('accounting') == 'time_resolved' else
                               'Whole life at construction: all stages A1-C4 booked in the construction year.'), '',
         '**Level of exceedance**: LoE_k(t) = I_sec(t) / B_k(t); cumulative LoE = Σ I_sec / Σ B_k over '
         f'{y0}-{y1} (ratio of sums).', '',
         '**Dating.** Model year t is 31 December (Stats NZ ERP history). The WPP 2024 series (1 July) and, in the '
         'sensitivities, the Stats NZ (30 June) and WPP New Zealand series are dated at t as the mean of mid-year t '
         'and t+1.', '',
         '## Constants and sources', '', '| quantity | value | source |', '|---|---|---|',
         f"| SOS | {c['SOS_kg']:.3g} kg CO2-eq/yr | {c['pair_label']}; ESM2 (see source check) |",
         f"| I_glob | {c['I_glob_kg']:.3g} kg CO2-eq/yr | Bjørn & Hauschild 2015 ESM2 B30 (Laurent et al. 2013, 2010); "
         f"equal to the EF 3.0 global factor ({boundaries.I_GLOB_EF30_PER_PERSON:.2E} kg CO2e per person, 2010; "
         'Andreasi Bassi et al. 2023, Table 10) |',
         f"| Ī_sec,base {w0}-{w1} | {c['I_sec_base_kg'] / 1e6:,.1f} kt/yr | this model, history on the projection's "
         'soil convention (boundaries.historical_emissions) |',
         f"| base year b | {b} | latest year with ≥ {100 * s['WDI_COVERAGE_MIN']:.0f}% of WDI-economy population "
         f"reporting {s['GDP_MEASURE']} |",
         f"| α (b, PPP) | {c['alpha']:.4f} | Hjalsted SI Eq. S1; WDI (release 2026-07-13) |",
         f"| g_W, g_NZ (b, PPP, 2021 int-$) | {c['g_W']:,.0f}, {c['g_NZ']:,.0f} (ratio {c['g_W_over_g_NZ']:.4f}) | WDI {s['GDP_MEASURE']} |",
         f"| consented value {ss['window'][0]}-{ss['window'][1]} | {ss['consented_value_nzd_per_yr']:,.1f} NZD/yr | "
         'Stats NZ building consents (data/derived/consents_monthly.csv): detached + townhouses + apartments |',
         f"| GDP(E) {ss['window'][0]}-{ss['window'][1]} | {ss['gdp_nzd_per_yr']:.7g} NZD/yr | Stats NZ SNE022AA (40 quarters / 10) |",
         f"| FCE / GDP | {ss['fce_share_mean_of_ratios']:.9f} (mean of 40 quarterly ratios); ratio of sums "
         f"{ss['fce_share_ratio_of_sums']:.6f} | Stats NZ SNE022AA |",
         f"| s_sec | {c['s_sec']:.7f} (ratio of sums: {ss['s_sec_ratio_of_sums']:.7f}, "
         f"{100 * (ss['s_sec_ratio_of_sums'] / ss['s_sec_mean_of_ratios'] - 1):+.2f}%) | Hjalsted Eq. 6; manuscript "
         'definition kept for continuity |',
         f"| P_NZ(t0), P_W(t0) | {c['P_NZ_t0']:,.0f}, {c['P_W_t0']:,.0f} | model (observed 2025 ERP); WPP 2024 median |",
         '', 's_sec uses the consented value of new residential building over national final consumption '
         'expenditure, following the FCE upscaling of Hjalsted et al. (2021) as a proxy of the priority households '
         'give to housing. In the national accounts residential construction is gross fixed capital formation, not '
         'final consumption; treating it as consumed follows the endogenisation of capital in consumption-based '
         'accounting (Södersten, Wood & Hertwich 2018).', '',
         '## Historical sector emissions (base window, case-study factors)', '',
         '| year | kt CO2e | soil share of floor area | net replacement rate (%/yr) | rate from |', '|---|---|---|---|---|']
    for y, h in r['history'].items():
        L.append(f"| {y} | {h['I_kt']:,.1f} | {h['soil_share']:.3f} | {h['rate_pct']:.3f} | {h['rate_source']} |")
    L += ['', f"Mean {w0}-{w1}: {c['I_sec_base_kg'] / 1e6:,.1f} kt/yr"
          + (f", of which maintenance (B2, B4) {100 * c['I_sec_base_b_share']:.2f}% (events within {w0}-{w1} of "
             f"the buildings built in it); wider maintenance scope (B2, B4 events of all cohorts built since 1992): "
             f"{c['I_sec_base_wider_scope_kg'] / 1e6:,.1f} kt/yr"
             if c.get('I_sec_base_b_share') is not None else '') + f". With soil on all floor area: {c['I_sec_base_soil_on_all_kg'] / 1e6:,.1f} kt/yr. Note: with the long-run net replacement "
          f"rate for 2024-25: {c['I_sec_base_long_run_2024_25_kg'] / 1e6:,.1f} kt/yr; {w1 - 4}-{w1} (5 yr): "
          f"{c['I_sec_base_5yr_kg'] / 1e6:,.1f} kt/yr.", '',
          '## α validation (Hjalsted et al. 2021 SI: α = 0.243 for 2017; world GDP per capita 1.07E+04 USD)', '',
          '| GDP measure | α 2017 | g_W 2017 | economies | population coverage |', '|---|---|---|---|---|']
    for k in (boundaries.GDP_MEASURE_SENS, boundaries.GDP_MEASURE):
        L.append(f"| {k} | {ac[k]['alpha']:.4f} | {ac[k]['g_W']:,.0f} | {ac[k]['n']} | {100 * ac[k]['population_share']:.2f}% |")
    L += ['', f"Hjalsted et al. state GDP as 'USD/cap (2017)', World Bank (2019), without naming the series. With "
          f"current US$ (WDI release 2026-07-13) α(2017) = {ac[boundaries.GDP_MEASURE_SENS]['alpha']:.4f} against 0.243 "
          f"({100 * (ac[boundaries.GDP_MEASURE_SENS]['alpha'] / ac['hjalsted_alpha'] - 1):+.1f}%); not tuned. Possible "
          'reasons, not tested: WDI revisions since the 2019 release, a different country set, and their use of '
          'UNSD rather than WDI population.', '',
          f'## Coverage, base year {b}', '', '| measure | economies | population share | share of WDI world GDP |',
          '|---|---|---|---|']
    for k, v in cov.items():
        L.append(f"| {k} | {v['n_economies']} of {v['n_all']} | {100 * v['population_share']:.2f}% | "
                 f"{100 * v['gdp_share_of_wdi_world']:.2f}% |")
    for k, v in cov.items():
        ex = ', '.join(f"{e['name']} ({e['population'] / 1e6:.1f} M)" for e in v['excluded'])
        L += ['', f'Excluded, {k}: {ex}.']
    L += ['', '## Source check (SOS and I_glob)', '',
          '| value (kg CO2-eq/yr) | what | where | reference year | GWP basis | land-use-change CO2 |',
          '|---|---|---|---|---|---|'] + [f'| {" | ".join(row)} |' for row in boundaries.SOURCE_CHECK]
    L += ['', f"Primary pair {s['SOURCE_PAIR']}: {boundaries.SOURCE_PAIRS[s['SOURCE_PAIR']]['label']}; sensitivity C: "
          f"{boundaries.SOURCE_PAIRS['C']['label']}. Global-impact sensitivity (acquired rights only): I_glob = "
          f"{boundaries.I_GLOB_EF31_PER_PERSON:.2E} kg CO2e per person x {boundaries.I_GLOB_EF31_POPULATION:,} persons "
          f"(2010) = {boundaries.SOURCE_PAIRS['EF31']['i_glob']:.3E} kg CO2e/yr, the EF 3.1 normalisation factor "
          f"(Andreasi Bassi et al. 2023, Table 10), with the SOS of pair {s['SOURCE_PAIR']}; AtP does not depend on "
          'I_glob.', '',
          *ar_base_rule_lines(r), '',
          '## Results', '']
    if m:
        L += [f"The {m['source_pair_label']} allocated by acquired rights gives {m['B_AR_2026_kt']:,.1f} kt CO2e in "
              f"2026 and {m['B_AR_2050_kt']:,.1f} kt in 2050; by ability to pay {m['B_AtP_2026_kt']:,.2f} and "
              f"{m['B_AtP_2050_kt']:,.2f} kt ({100 * m['B_AtP_over_B_AR']:.1f}% of AR in every year). Both "
              + ('rise: New Zealand\'s share of world population grows' if m['B_AR_2050_kt'] > m['B_AR_2026_kt']
                 else 'fall: New Zealand\'s share of world population declines') + f" between 2026 and 2050. Over "
              f"{y0}-{y1} the Reference emits {r['reference_2026_2050']['I_kt']:,.0f} kt against "
              f"cumulative boundaries of {r['reference_2026_2050']['B_AR_kt']:,.0f} kt (AR) and "
              f"{r['reference_2026_2050']['B_AtP_kt']:,.0f} kt (AtP): cumulative LoE {m['cum_LoE_AR_REF']:.2f} "
              f"(AR; Monte Carlo p5-p95 {m['cum_LoE_AR_REF_mc_p5']:.2f}-{m['cum_LoE_AR_REF_mc_p95']:.2f}) and "
              f"{m['cum_LoE_AtP_REF']:.1f} (AtP; {m['cum_LoE_AtP_REF_mc_p5']:.1f}-"
              f"{m['cum_LoE_AtP_REF_mc_p95']:.1f}).", '',
              '| variant | cumulative LoE AR | cumulative LoE AtP |', '|---|---|---|']
        L += [f"| {SCEN_NAME.get(k, k)} | {v['AR']:.2f} | {v['AtP']:.1f} |" for k, v in ordered(m['cum_LoE_by_scenario'])]
    cm = r.get('committed') or {}
    if cm:
        L += ['', '### Committed after 2050 (later B2/B4 and C1-C4; deterministic)', '',
              'Lower bound: maintenance events (B2, B4) after 2050 with the 2050 factors held; upper bound: at 2025 '
              'factors; C1-C4 at 2025 factors in both. Years of the 2050 AR boundary = committed / B_AR(2050). Not '
              'part of the cumulative LoE.', '',
              '| variant | maintenance (B2, B4) 2026-2050 (kt) | share of carbon 2026-2050 | committed after 2050 (kt) '
              '| years of B_AR(2050) |',
              '|---|---|---|---|---|']
        L += [f"| {SCEN_NAME.get(k, k)} | {v['maintenance_kt_sum_of_annual']:,.0f} | {100 * v['maintenance_share']:.1f}% | "
              f"{v['lower_kt']:,.0f}-{v['upper_kt']:,.0f} | {v['years_of_B_AR_2050_lower']:.1f}-"
              f"{v['years_of_B_AR_2050_upper']:.1f} |" for k, v in ordered(cm) if k in MAIN]
    L += ['', '### Deterministic sensitivities (the Reference)', '',
          '| case | cumulative LoE AR | vs the Reference | cumulative LoE AtP | vs the Reference |',
          '|---|---|---|---|---|']
    for _, x in sens.iterrows():
        L.append(f"| {x['label']} | {x['cum_LoE_AR']:.2f} | {x['AR_vs_ref_pct']:+.1f}% | {x['cum_LoE_AtP']:.1f} | "
                 f"{x['AtP_vs_ref_pct']:+.1f}% |")
    if r.get('mc_base_20yr'):
        w20 = c.get('I_sec_base_20yr_window', ['?', '?'])
        L += ['', f'### Monte Carlo with a {w20[0]}-{w20[1]} AR base (20 years; not adopted)', '',
              f"Ī_sec,base {w20[0]}-{w20[1]} = {c['I_sec_base_20yr_kg'] / 1e6:,.1f} kt/yr (adopted {w0}-{w1}: "
              f"{c['I_sec_base_kg'] / 1e6:,.1f}); full consistent history {c['I_sec_base_full_window'][0]}-"
              f"{c['I_sec_base_full_window'][1]}: {c['I_sec_base_full_kg'] / 1e6:,.1f} kt/yr. Same saved draws, base "
              'recomputed per draw (no new random numbers); AtP is unaffected.', '',
              '| variant | cumulative LoE AR p5 / p50 / p95 (20-yr base) | adopted base |', '|---|---|---|']
        L += [f"| {SCEN_NAME.get(k, k)} | {v['LoE_AR_p5']:.2f} / {v['LoE_AR_p50']:.2f} / {v['LoE_AR_p95']:.2f} | "
              f"{r['mc'][k]['LoE_AR_p5']:.2f} / {r['mc'][k]['LoE_AR_p50']:.2f} / {r['mc'][k]['LoE_AR_p95']:.2f} |"
              for k, v in ordered(r['mc_base_20yr'])]
    L += ['', '## Assumption register', '', '| setting | value | basis |', '|---|---|---|']
    L += [f'| {a} | {v} | {bb} |' for a, v, bb in boundaries.assumption_register()]
    L += ['', '## Limitations', ''] + [f'- {x}' for x in boundaries.LIMITATIONS]
    L += ['', '## Notes', ''] + [f'- {v}' for v in r['notes'].values()]
    return L


def main():
    """The methods draft is one document: run directly, this part writes it through tools/methods.py."""
    import methods
    methods.main()


if __name__ == '__main__':
    main()
