"""Generate the PATHWAYS v2 documents from outputs/pathways/ (nothing typed by hand):

  outputs/pathways/PATHWAYS_METHODS_DRAFT.md  equations, parameters with sources, L5 estimator,
                                              attribution, gap, results tables, checks, limitations
  outputs/pathways/LEVERS_TABLE.md            Table 1 of the paper: one row per lever

With --sections also the Pathways sections of FIGURES.md and ASSUMPTIONS.md (each replaces only
its own section; idempotent; run_all.py --pathways-only).

    python tools/pathways_methods.py [--sections]
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs', 'pathways')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))


def table(head, rows):
    L = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    L += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return L


def t_table_rows(t):
    r = t['resolved']
    T3, T4, T5 = r['T3'], r['T4'], r['T5']
    rr = ', '.join(f"{k} {v['r']:.3f}" + (f" ({v['building']})" if v['building'] else ' (held: one independent case)')
                   for k, v in T4.items())
    return [
        ['T1 No idle stock', 'stock-wide vacancy v = 0 from 2027; near-term surplus absorbed in full; banking rule '
         '(dwellings built never negative; unused release carried forward and used before any new building)',
         '`v`; `join` = banked built - requirement (stock-adding, join_redev = 0)', 'v = 0; absorption 1',
         'DECISION (author): theoretical limit of L2a / L2b', 'DECISION'],
        ['T2 No extra space', 'new-dwelling size = occupied area S(t) x OLF (L1 with f = 1)', '`size` per typology and year',
         f"f = 1 (2050 size {t['indicators']['T']['new_dwelling_size_m2']['Detached']['2050']:.1f} m2 with T3)",
         'DECISION (author): theoretical limit of L1', 'DECISION'],
        ['T3 Minimum space per person', 'OLF of every new building = the lowest design OLF (GFA / design occupants) among '
         'the independent case studies', '`olf` (all typologies)',
         f"{T3['olf']:.2f} m2/person ({T3['building']}, {T3['typology']}); replaces "
         + ', '.join(f'{k} {v:.2f}' for k, v in T3['replaces'].items()),
         'DATA: case studies, Christoforatos & Pickering (2025) SASBE, doi:10.1108/SASBE-06-2025-0304 '
         '(data/building_data.xlsx; duplicate ' + ', '.join(T3['excluded_duplicates']) + ' excluded)', 'DATA'],
        ['T4 Best materials', "each typology's A1-A3 per m2 at its own best independent case (on top of decarbonisation, as L5)",
         '`intensity`, `intensity_upfront` (A1-A3 term)', rr,
         'DATA: case studies (outputs/factors/factors_building.csv, 2025 factors)', 'DATA'],
        ['T5 Best soil', 'soil factor at the lowest soil order (SOC_low) for every typology, from 2027',
         'soil factor (applied exactly through the soil-bearing share)',
         ', '.join(f"{k} {v['soc_low']:.1f} (vs {v['soc_avg']:.1f})" for k, v in T5.items()) + ' kg CO2e/m2',
         'DATA: Christoforatos, Pickering & Schipper (2026) J. Environ. Manage. 415, 130603 (lowest of 10 soil orders; '
         'the existing lower-bound sensitivity)', 'DATA'],
    ]


def t_levers_table(t):
    L = ['', '## Theoretical limit T (PATHWAYS v3)', '', '> ' + t['disclaimer'], '',
         'T = P5-stretch (L3 removals -40%, L4 attached share 55.40%) with the overrides below, all at full strength '
         'from 2027 (no ramp); 2026 observed and untouched.', '']
    L += table(['assumption', 'definition', 'model terms', 'value', 'source', 'tag'], t_table_rows(t))
    return L


def t_methods(t, runs):
    ind, gap = t['indicators']['T'], t['gap']
    r = {n: runs[(runs['run'] == n) & (runs['scenario'] == 'S3-10')].iloc[0] for n in ('P0', 'P5-central', 'P5-stretch', 'T', 'T-ramp')}
    sh = pd.DataFrame(t['shapley'])
    L = ['', '## Theoretical limit T (PATHWAYS v3)', '', '> ' + t['disclaimer'], '',
         '**Definition.** T = P5-stretch with five overrides at full strength from 2027 (w = 1 for every lever in '
         '2027-2050, no ramp; 2026 observed and untouched): T1 no idle stock (v = 0; near-term surplus absorbed in full), '
         'T2 no extra space (new-dwelling size = occupied area S(t) · OLF), T3 minimum space per person (OLF of every new '
         'building = the lowest independent design OLF), T4 best materials (each typology at its own best independent '
         'case; apartments held), T5 best soil (lowest soil order). L3 (−40%) and L4 (55.40%) as P5-stretch.', '']
    L += table(['assumption', 'definition', 'model terms', 'value', 'source', 'tag'], t_table_rows(t))
    L += ['', '**Banking rule (T1).** raw_t = requirement_t + absorbed near-term excess_t (negative when the release of '
          'vacant or surplus dwellings exceeds the year\'s need); D_t = raw_t − bank_(t−1); built_t = max(0, D_t); '
          'bank_t = max(0, −D_t). The banked path enters engine.forward as a stock-adding join, join_t = built_t − '
          'requirement_t (join_redev = 0), so the stock identity holds and implied vacancy = stock_join / (households + '
          'stock_join) ≥ 0. Banked zero-building years carry floating-point noise of about 1e-12 dwellings; the checks '
          'use 1e-6 dwellings. The banking rule is applied in every T-family run (it binds only where the release exceeds '
          'the need).', '',
          '**Soil path (T5).** The engine takes one soil factor per typology; the year-dependent factor is applied exactly '
          'by lowering the intensity by (SOC_avg − SOC_path(y)) × soil-bearing share(y), the share being independent of '
          'the intensity (checked: identical in both passes; tested).', '',
          '### Results (S3-10)', '']
    rows = [[n, f"{x['gfa_Mm2']:.2f}", f"{x['carbon_kt']:,.0f}", f"{x['committed_lower_kt']:,.0f}-{x['committed_upper_kt']:,.0f}",
             f"{x['LoE_AR']:.3f}", f"{x['LoE_AtP']:.2f}", f"{100 * x['remaining_reduction_AR']:.1f}%",
             f"{x['delta_carbon_kt_vs_P0_pct']:+.1f}%"] for n, x in r.items()]
    L += table(['run', 'floor area (Mm²)', 'carbon 2026-2050 (kt)', 'committed after 2050 (kt)', 'LoE AR', 'LoE AtP',
                'AR reduction still needed', 'carbon vs P0'], rows)
    zy = ind['zero_building_years']
    L += ['', '**Human terms (T, 2027-2050).** New-dwelling size '
          + ', '.join(f"{k} {v['2050']:.1f} m²" for k, v in ind['new_dwelling_size_m2'].items())
          + f" (2050); floor area per person in new dwellings {ind['m2_per_person_new_dwellings']['2050']:.1f} m²; "
          f"vacant dwellings released by the vacancy change {ind['vacancy_change_release_dwellings']:,.0f} and near-term "
          f"surplus absorbed {ind['near_term_surplus_absorbed_dwellings']:,.0f}; release in excess of the yearly need "
          f"{ind['release_added_total']:,.0f} dwellings, used {ind['release_used_total']:,.0f}, unused in 2050 "
          f"{ind['bank_unused_2050']:,.0f}; no new building in {len(zy)} years"
          + (f" ({zy[0]}-{zy[-1]})" if zy else '') + '. Dwellings built per year, implied vacancy and the banking path by '
          'year: t_limit.json.', '']
    g = gap['T']
    if g['within_AR']:
        L += [f"**Gap.** T is within the AR budget: margin {g['margin_AR_kt']:,.0f} kt ({100 * g['margin_AR_share']:.1f}%)."]
    else:
        b = g['backcast']
        L += [f"**Gap.** T exceeds the AR budget (cumulative LoE AR {g['LoE_AR']:.3f}): a uniform cut of "
              f"{100 * b['cut_AR']:.1f}% of 2027-2050 construction (k = {b['k_AR']:.4f}, brentq) would reach LoE AR = 1. "
              f"AtP: T {b['LoE_AtP_at_k1']:.2f}; the minimum attainable (2026 cohort alone) is {b['LoE_AtP_min_k0']:.2f}, "
              'so AtP is not attainable within the window.']
    L += ['', '### Shapley attribution of P5-stretch (instant start) − T', '']
    rows = []
    for pl in ['T1', 'T2', 'T3', 'T4', 'T5', 'instant start']:
        c = sh[(sh['metric'] == 'carbon_kt') & (sh['player'] == pl)].iloc[0]
        a = sh[(sh['metric'] == 'LoE_AR') & (sh['player'] == pl)].iloc[0]
        share = c['share_of_P5s_instant_minus_T']
        rows.append([pl if pl == 'instant start' else f"{pl} {t['definition']['components'][pl]}",
                     f"{c['reduction']:,.0f}" + ('' if pd.isna(share) else f" ({100 * share:.0f}%)"), f"{a['reduction']:.3f}"])
    L += table(['player', 'carbon (kt)', 'LoE AR'], rows)
    L += ['', 'Players T1-T5 over 32 subsets, each applied with the instant start (exact rational arithmetic; the values add '
          'up to P5-stretch with the instant start − T). "instant start" is a separate line, not a player: P5-stretch on '
          'the logistic ramp minus P5-stretch at full strength from 2027. Sensitivity: T with the v2 logistic ramp '
          f"(T-ramp) gives LoE AR {r['T-ramp']['LoE_AR']:.3f}.", '',
          '### Limitations of T', '',
          '* T combines attributes of different buildings (the OLF of A_1, an apartment block, applied to every typology; '
          'each typology\'s best A1-A3 case; the lowest soil order everywhere) that have not been observed together; it is '
          'not a design, a policy or a feasible pathway.',
          '* T2 + T3 give every new dwelling the occupied area of the case-study minimum (about 20 m² per person); no '
          'design rule, accessibility standard or household-size variation is modelled.',
          '* T1 assumes every vacant dwelling is usable where it is needed (no spatial or condition mismatch; Napiontek et '
          'al. 2025 on hibernating stock) and an instant reallocation in 2027.',
          '* As in P1-P5, the renovation carbon of the kept stock (L3) and any rebound are not modelled; deterministic, '
          'median demographics; static budgets.']
    return L


def levers_table(p, t=None):
    import levers as LV
    rows = LV.lever_table(p)
    L = ['# Table 1. PATHWAYS v2 levers (generated by tools/pathways_methods.py from outputs/pathways/levers.json; '
         'do not edit by hand)', '']
    if p['run_mode'] != 'full':
        L += [f"> **{p['run_mode']}**", '']
    L += ['Reference scenario S3-10; each lever ramps in on a normalised logistic path from 2026 (observed, '
          'unchanged) to full strength in 2035. Tags: DATA (measured), LITERATURE (cited), DECISION (author).', '']
    L += table(['lever', 'pathway', 'demand band targeted', 'model parameter', 'central', 'stretch',
                'basis (full citation)', 'key assumption', 'tag'],
               [[r['lever'], r['pathway'], r['band'], r['parameter'], r['central'], r['stretch'], r['basis'],
                 r['assumption'], r['tag']] for r in rows])
    if t is not None:
        L += t_levers_table(t)
    with open(os.path.join(OUT, 'LEVERS_TABLE.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')


def main():
    import levers as LV
    p = json.load(open(os.path.join(OUT, 'levers.json')))
    runs = pd.read_csv(os.path.join(OUT, 'pathways_runs.csv'))
    bands = pd.read_csv(os.path.join(OUT, 'pathways_bands.csv'))
    shp = pd.read_csv(os.path.join(OUT, 'shapley_pathways.csv'))
    shl = pd.read_csv(os.path.join(OUT, 'shapley_levers.csv'))
    bc = json.load(open(os.path.join(OUT, 'backcast.json')))
    t_path = os.path.join(OUT, 't_limit.json')
    tlim = json.load(open(t_path)) if os.path.exists(t_path) else None
    levers_table(p, tlim)
    ref = runs[(runs['scenario'] == 'S3-10') & (runs['ramp'] == 'ramp2035') & ~runs['l5_apartments_held'].astype(bool)].set_index('run')
    p0 = ref.loc['P0']
    e5 = p['L5']['estimator']
    L = ['# PATHWAYS v2: methods (DRAFT; generated by tools/pathways_methods.py, do not edit by hand)', '']
    if p['run_mode'] != 'full':
        L += [f"> **{p['run_mode']}**", '']
    L += [
        'Four pathways for new residential construction in New Zealand, 2026-2050, built from six levers and applied '
        'to the frozen baseline (baseline-pb-v3.1, reference replacement scenario S3-10), assessed against the '
        'climate-change budgets of the planetary-boundary layer (acquired rights, AR; ability to pay, AtP). The '
        'model is unchanged: `pathways.py` re-calls `engine.forward()` with copies of the reference inputs modified '
        'by `levers.py` (hooks: outputs/pathways/HOOKS.md); no baseline output is rewritten (tests/test_baseline_lock.py, '
        'SHA-256 of every baseline output at tag baseline-PB_v3.1). With every lever off the run reproduces the '
        f"reference run (maximum relative difference {p['identity_max_rel_diff']:.1e}; tests/test_pathways.py). "
        'Table 1: outputs/pathways/LEVERS_TABLE.md.', '',
        '## Pathways and demand bands', '',
        '| pathway | levers | demand band targeted |', '|---|---|---|',
        f"| P1 {LV.PATHWAY_NAMES['P1']} | L1 {LV.LEVER_NAMES['L1']}, L4 {LV.LEVER_NAMES['L4']} | extra space per dwelling "
        'and the dwelling size of every non-growth band; L4 also lowers the occupied area per person (attached OLF), '
        'which slightly reduces the growth band |',
        f"| P2 {LV.PATHWAY_NAMES['P2']} | L2a {LV.LEVER_NAMES['L2a']}, L2b {LV.LEVER_NAMES['L2b']} | vacancy allowance "
        '(incl. the vacancy change) and the near-term market excess |',
        f"| P3 {LV.PATHWAY_NAMES['P3']} | L3 {LV.LEVER_NAMES['L3']} | long-run replacement (demolition) and the "
        'redevelopment wave |',
        f"| P4 {LV.PATHWAY_NAMES['P4']} | L5 {LV.LEVER_NAMES['L5']} | carbon per m² (A1-A3) of every band |",
        f"| P5 {LV.PATHWAY_NAMES['P5']} | all six | all of the above |", '',
        'Growth and house-splitting are untargeted by design: population and household formation are exogenous '
        '(as in Pellan et al. 2024). Every run reports floor area and carbon by demand band (Boss definitions; '
        'pathways_bands.csv), so the attribution by band is exact and needs no decomposition.', '',
        '## Conventions', '',
        f"* Ramp (all levers): s(y) = 1 / (1 + exp(−k (y − {p['ramp']['mid']}))), k = ln(81)/6 = {p['ramp']['k']:.4f} "
        '(s rises from 10% to 90% within 6 years); w(y) = (s(y) − s(2026)) / (s(2035) − s(2026)) for 2026 ≤ y ≤ 2035, '
        'w = 1 after 2035, w(2026) = 0. A lever moves a quantity from its baseline b to its target x as b + w(y)(x − b). '
        f"Sensitivity ramp2045 (P5): midpoint {p['ramp']['sensitivity']['mid']}, end {p['ramp']['sensitivity']['end']}, "
        'same k (the same adoption speed, five years later).',
        '* 2026 is observed (consented floor area fixed) and identical in every run.',
        '* Near-term market excess: frozen at the baseline path, in dwellings, except where L2b absorbs the surplus '
        '(it is the observed 2026 pipeline, not demand).',
        '* Accounting as the baseline (time-resolved): within-window carbon = upfront (A1-A5 + soil) in the '
        'construction year + replacements & repaints (B2, B4) in 2026-2050; later events and all C1-C4 of the '
        '2026-2050 cohorts are committed after 2050 (range: lower with the 2050 factors held, upper at 2025 factors; '
        '`events.committed` with each run\'s floor area by typology).', '',
        '## Levers as implemented (levers.py)', '',
        '    L1   size_t(y) = occ_t(y) + [1 − f w(y)] (size_ref_t − occ_t(y)),   occ_t(y) = S(y) · OLF_t',
        '    L4   att(y) = att0 + w(y)(att* − att0); Δ to townhouses / apartments ∝ their held shares; detached −Δ',
        '    L2a  v(y) = v0 + w(y)(v* − v0)',
        '    L2b  join = market_excess(E_nojoin, O26, ρ, 2027, surplus, absorption a)',
        '    L3   demol(y) = demol · (1 − w(y) d);  resid(y) = resid_LR + (resid_S3(y) − resid_LR)(1 − w(y) d)',
        '    L5   A1-A3_t(y) = [1 − w(y)(1 − r)] · (A1-A3_t,2025 − R13_t(y))   (A4-A5, B events, C1-C4, soil unchanged)', '',
        'S and OLF are the engine\'s (S = population / households of the median path; OLF per typology from the '
        'case studies), so occ_t is the occupied area the engine uses for the growth and extra-space bands. '
        'size_ref: realised new-dwelling size, mean of 2023-2025. L1 holds a typology / year at size_ref where '
        f"size_ref ≤ occ (never binds: {len(p['L1']['held'])} typology-years held). L2a acts through the stock "
        'identity: while v falls the vacancy-change term releases existing dwellings once (cumulative release in '
        'pathways_runs.csv, by year in pathways_annual.csv); under the logistic ramp the release peaks where w rises '
        'fastest (2029-2032). R13: the A1-A3 decarbonisation of the baseline (Horup et al. 2025, item level).', '',
        '## Parameters and sources', '']
    L += table(['setting', 'value', 'basis'], LV.register(p))
    L1 = p['L1']
    L += ['', '### L1: implied new-dwelling sizes', '']
    rows = []
    for t in L1['size_ref']:
        for y in LV.L1_REPORT_YEARS:
            c, s = LV.by_year(L1['implied']['central'][t], y), LV.by_year(L1['implied']['stretch'][t], y)
            rows.append([t, y, f"{L1['size_ref'][t]:.1f}", f"{c['occupied_m2']:.1f}", f"{c['size_m2']:.1f} ({c['cut_pct']:+.1f}%)",
                         f"{s['size_m2']:.1f} ({s['cut_pct']:+.1f}%)", f"{c['size_per_occupant_m2']:.1f} / {s['size_per_occupant_m2']:.1f}"])
    L += table(['typology', 'year', 'size_ref (m²)', 'occupied S·OLF (m²)', 'central (m², cut)', 'stretch (m², cut)',
                'm² per occupant, central / stretch'], rows)
    L += ['', f"Benchmarks: Pellan et al. (2024), individual dwellings 107 → 100 m² "
          f"({L1['benchmarks_pct']['Pellan2024']:+.1f}%); Pauliuk et al. (2024) LEMD EU_UK 37.7 → 31.2 m²/cap "
          f"({L1['benchmarks_pct']['Pauliuk2024_LEMD_EU_UK']:+.1f}%).", '']
    L += ['### L5: Harrell-Davis estimator', '',
          f"Sample: the {p['L5']['n']} independent case studies of the detached and townhouse typologies (duplicates "
          'excluded; apartments have one independent case and are not in the sample), 2025 A1-A3 per m² '
          '(outputs/factors/factors_building.csv). Scale-free ratio x_i = A1-A3_i / pooled A1-A3 of its typology '
          f"(pooling as Building_factors.pool; recomputed pooled values equal the model's to {p['L5']['pooled_check_max_abs']:.1e} kg/m²). "
          'Harrell & Davis (1982):', '',
          '    Q̂(q) = Σ_i W_i x_(i),   W_i = I_{i/n}(a, b) − I_{(i−1)/n}(a, b),   a = q(n + 1),   b = (1 − q)(n + 1)', '',
          'with I the regularised incomplete beta function, implemented directly and checked against '
          'scipy.stats.mstats.hdquantiles (≤ 1e-10). Interval: nonparametric bootstrap of the cases, '
          f"B = {p['L5']['bootstrap']['B']:,}, seed {p['L5']['bootstrap']['seed']}, percentile 95% (Efron & Tibshirani 1993). "
          'The pathway runs use the point estimate; the same r applies to all three typologies (apartments held at '
          'r = 1 as a sensitivity).', '']
    L += table(['setting', 'q', 'r (point)', '95% CI', 'scipy hdquantiles'],
               [[s, f"{e5[s]['q']:.2f}", f"{e5[s]['r']:.4f}", f"{e5[s]['ci_lo']:.4f}-{e5[s]['ci_hi']:.4f}",
                 f"{e5[s]['scipy_hdquantiles']:.4f}"] for s in LV.SETTINGS])
    L += ['']
    L += table(['case', 'typology', 'A1-A3 (kg/m²)', 'ratio x_i'],
               [[c['id'], c['typology'], f"{c['a13']:.1f}", f"{c['ratio']:.3f}"] for c in p['L5']['cases']])
    L += ['', '## Attribution', '',
          'Shapley values (Shapley 1953; for emissions decompositions Albrecht, François & Schoors 2002) of each '
          'player for the reduction v(∅) − v(N):', '',
          '    φ_i = Σ_{S ⊆ N∖{i}} |S|! (|N| − |S| − 1)! / |N|! · [v(S) − v(S ∪ {i})]', '',
          'Players: the four pathways (|N| = 4, 16 subsets; main) and the six levers (|N| = 6, 64 subsets; SI); every '
          'subset is a full run; v = cumulative within-window carbon (kt) or cumulative LoE AR. Computed in exact '
          'rational arithmetic on the run values, so Σ_i φ_i = P0 − P5 exactly (tested).', '',
          '## AESA gap', '',
          'Budgets B_AR(t), B_AtP(t) for S3-10 from outputs/pb_annual.csv (no lever changes population). Cumulative '
          'LoE = Σ I(t) / Σ B(t) over 2026-2050 (aesa.cumulative_loe); remaining reduction needed = 1 − 1/LoE.', '',
          '**Back-cast.** I(t; k) = F(t) + k · G(t), F the 2026 cohort (its upfront and in-window events), G the '
          '2027-2050 cohorts; scaling their floor area by k keeps the typology mix and the replacement share, hence '
          'the soil share. k solves Σ I(t; k) = Σ B_AR(t) (scipy.optimize.brentq on [0, 1], xtol 1e-15; checked '
          'against the closed form). AtP: the minimum attainable cumulative LoE is Σ F / Σ B_AtP (k = 0).', '',
          '**Solution space** (after Horup et al. 2025, Fig. 6): I(t; d, i) = F(t) + (1 − d)[(1 − i) G_ns(t) + '
          'G_soil(t)] on P0. Pathways sit at d = 1 − GFA_P / GFA_0 and i = 1 − (C_P / GFA_P) / (C_0 / GFA_0) '
          '(2027-2050 cohorts; C non-soil within the window); a negative i means more carbon per m² (L4 shifts floor '
          'area to typologies with more A1-A3 per m²).', '',
          '## Results (S3-10)', '']
    rows = []
    names = ['P0'] + [f'{P}-{s}' for P in ('P1', 'P2', 'P3', 'P4', 'P5') for s in LV.SETTINGS]
    for name in names:
        r = ref.loc[name]
        rows.append([name, f"{r['gfa_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}",
                     f"{r['committed_lower_kt']:,.0f}-{r['committed_upper_kt']:,.0f}", f"{r['LoE_AR']:.2f}",
                     f"{r['LoE_AtP']:.1f}", f"{100 * r['remaining_reduction_AR']:.1f}%",
                     f"{r['delta_carbon_kt_vs_P0_pct']:+.1f}%", f"{r['dwellings_built']:,.0f}",
                     f"{r['mean_dwelling_size_m2']:.1f}", f"{r['carbon_per_m2_kg']:.1f}",
                     f"{r['existing_dwellings_released']:,.0f}", f"{100 * r['implied_vacancy_min']:.2f}%"])
    L += table(['run', 'floor area (Mm²)', 'carbon 2026-2050 (kt)', 'committed after 2050 (kt)', 'LoE AR', 'LoE AtP',
                'AR reduction still needed', 'carbon vs P0', 'dwellings built', 'mean size (m²)', 'kg CO₂e/m²',
                'existing dwellings released', 'min implied vacancy'], rows)
    L += ['', '### Floor area cut by demand band, central (Mm², vs P0; in-scope figure definition)', '']
    bd = bands[(bands['scenario'] == 'S3-10') & (bands['definition'] == 'in_scope_figure')]
    blist = list(dict.fromkeys(bd['band']))
    rows = []
    for b in blist:
        if b.startswith('Replacements & repaints'):
            continue
        rows.append([b] + [f"{bd[(bd['run'] == f'{P}-central') & (bd['band'] == b)]['delta_gfa_Mm2_vs_P0'].iloc[0]:+.2f}"
                           for P in ('P1', 'P2', 'P3', 'P4', 'P5')])
    rows.append(['**total**'] + [f"{ref.loc[f'{P}-central', 'gfa_Mm2'] - p0['gfa_Mm2']:+.2f}" for P in ('P1', 'P2', 'P3', 'P4', 'P5')])
    L += table(['band', 'P1', 'P2', 'P3', 'P4', 'P5'], rows)
    L += ['', '### Shapley attribution of P0 − P5 (pathways)', '']
    srows = []
    for P in LV.PATHWAYS:
        line = [f'{P} {LV.PATHWAY_NAMES[P]}']
        for s in LV.SETTINGS:
            for metric, fmt in (('carbon_kt', '{:,.0f}'), ('LoE_AR', '{:.3f}')):
                x = shp[(shp['setting'] == s) & (shp['metric'] == metric) & (shp['player'] == P)].iloc[0]
                line.append(fmt.format(x['reduction']) + (f" ({100 * x['share_of_P0_minus_P5']:.0f}%)" if metric == 'carbon_kt' else ''))
        srows.append(line)
    srows.append(['P0 − P5'] + [v for s in LV.SETTINGS for v in (f"{p0['carbon_kt'] - ref.loc[f'P5-{s}', 'carbon_kt']:,.0f}",
                                                                   f"{p0['LoE_AR'] - ref.loc[f'P5-{s}', 'LoE_AR']:.3f}")])
    L += table(['pathway', 'central: carbon (kt)', 'central: LoE AR', 'stretch: carbon (kt)', 'stretch: LoE AR'], srows)
    L += ['', '### Shapley attribution of P0 − P5 (levers, SI)', '']
    srows = []
    for Lv in LV.LEVERS:
        line = [f'{Lv} {LV.LEVER_NAMES[Lv]}']
        for s in LV.SETTINGS:
            x = shl[(shl['setting'] == s) & (shl['metric'] == 'carbon_kt') & (shl['player'] == Lv)].iloc[0]
            line.append(f"{x['reduction']:,.0f} ({100 * x['share_of_P0_minus_P5']:.0f}%)")
        srows.append(line)
    L += table(['lever', 'central: carbon (kt)', 'stretch: carbon (kt)'], srows)
    L += ['', '### Back-cast', '',
          f"Cumulative budgets 2026-2050: AR {bc['B_AR_kt']:,.0f} kt, AtP {bc['B_AtP_kt']:,.0f} kt. The 2026 cohort "
          f"alone (construction and its in-window events, fixed) emits {bc['P0']['carbon_fixed_2026_cohort_kt']:,.0f} kt.", '']
    keys = ['P5-central', 'P5-stretch', 'P0']
    L += table([''] + keys,
               [['LoE AR at k = 1'] + [f"{bc[k]['LoE_AR_at_k1']:.3f}" for k in keys],
                ['k for cumulative LoE AR = 1'] + [f"{bc[k]['k_AR']:.4f}" for k in keys],
                ['cut of 2027-2050 construction (1 − k)'] + [f"{100 * bc[k]['cut_AR']:.1f}%" for k in keys],
                ['2027-2050 floor area at k (Mm²)'] + [f"{bc[k]['gfa_2027_2050_at_k_Mm2']:.2f}" for k in keys],
                ['equivalent floor-area cut vs P0'] + [f"{100 * bc[k]['equivalent_cut_vs_P0_floor_area']:.1f}%" if k != 'P0' else '-' for k in keys],
                ['minimum LoE AtP (k = 0)'] + [f"{bc[k]['LoE_AtP_min_k0']:.3f}" for k in keys]])
    L += ['', f"AtP: {bc['AtP_note']} (minimum cumulative LoE AtP with no construction after 2026: "
          f"{bc['P0']['LoE_AtP_min_k0']:.2f}).", '', '### Envelope, ramp and L5 sensitivities', '']
    erows = []
    for scen in ('S1', 'S3-10', 'S2'):
        for name in ('P0', 'P5-central', 'P5-stretch', 'P5-central-ramp2045', 'P5-stretch-ramp2045'):
            r = runs[(runs['scenario'] == scen) & (runs['run'] == name)].iloc[0]
            erows.append([scen, name, f"{r['gfa_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}", f"{r['LoE_AR']:.2f}",
                          f"{r['LoE_AtP']:.1f}", f"{r['delta_carbon_kt_vs_P0_pct']:+.1f}%"])
    for name in ('P4-central-aptheld', 'P4-stretch-aptheld', 'P5-central-aptheld', 'P5-stretch-aptheld'):
        r = runs[(runs['scenario'] == 'S3-10') & (runs['run'] == name)].iloc[0]
        erows.append(['S3-10', name + ' (L5: apartments held)', f"{r['gfa_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}",
                      f"{r['LoE_AR']:.2f}", f"{r['LoE_AtP']:.1f}", f"{r['delta_carbon_kt_vs_P0_pct']:+.1f}%"])
    L += table(['scenario', 'run', 'floor area (Mm²)', 'carbon (kt)', 'LoE AR', 'LoE AtP', 'carbon vs P0 of the scenario'], erows)
    L += ['', '### End of the ramp (P2)', '']
    L += table(['run', 'w(2035) − w(2034)', 'carbon 2035 → 2036 (kt)', 'P0 2035 → 2036 (kt)', 'step relative to P0 (kt)', 'dwellings 2035 → 2036'],
               [[k.replace('end_of_ramp_step_', ''), f"{d['w_2035_minus_w_2034']:.4f}", f"{d['carbon_step_kt']:+.1f}",
                 f"{d['P0_carbon_step_kt']:+.1f}", f"{d['step_relative_to_P0_kt']:+.1f}", f"{d['dwellings_step']:+,.0f}"]
                for k, d in p['diagnostics'].items() if k.startswith('end_of_ramp_step')])
    L += ['', '## Checks (tests/test_pathways.py, tests/test_baseline_lock.py)', '',
          '* P0 = reference run (≤ 1e-9 relative): annual carbon, upfront, in-window B, floor area by typology, '
          'demand bands, committed range, cumulative LoE AR / AtP; S1 and S2 P0 = the PB scenario runs.',
          '* Each lever at zero strength = the baseline; 2026 identical in every run; lever functions never modify '
          'their inputs; the logistic ramp is 0 in 2026, 1 from 2035 and monotone.',
          '* L1 sizes ≥ occupied area S·OLF in every typology, year and run; D ≥ S·OLF (engine extra_clip = 0); implied '
          f"vacancy ≥ {100 * p['L2a']['floor']:.1f}%; no negative dwellings built.",
          '* Harrell-Davis = scipy.stats.mstats.hdquantiles (≤ 1e-10); pathway and lever Shapley efficiency exact; '
          'demand bands add up to the totals; back-cast LoE AR = 1 (≤ 1e-9).',
          '* Baseline outputs: SHA-256 equal to tag baseline-PB_v3.1 (tests/baseline_manifest.json).', '',
          '## Limitations', '',
          '* L3 is an upper bound: the carbon of renovating the buildings kept in use is not modelled (Napiontek et '
          'al. 2025, Resour. Conserv. Recycl. 215, 108117).',
          f"* L5 rests on {p['L5']['n']} case studies; the stretch interval is wide ({e5['stretch']['ci_lo']:.2f}-"
          f"{e5['stretch']['ci_hi']:.2f}). The ratio is pooled across detached and townhouses (scale-free) and applied "
          'to apartments too (one independent apartment case; held at r = 1 as a sensitivity), and to the pooled '
          'A1-A3 of every item: the best-practice material mix is assumed transferable.',
          '* L1 keeps the engine\'s occupied area (S·OLF) and cuts only the space above it; the occupancy load factor '
          'per typology and design rules (minimum room sizes) are not modelled.',
          '* L4 changes the typology shares only (per-typology size, OLF and carbon factors unchanged); because the '
          'attached typologies carry more A1-A3 per m², L4 lowers floor area but raises carbon per m².',
          f"* L2a: v0 = {100 * p['L2a']['v0']:.2f}% is the published 2023 empty-dwelling share while the target range "
          f"({100 * p['L2a']['census_consistent_min']:.2f}-{100 * p['L2a']['census_consistent_max']:.2f}%) is on a "
          'consistent definition; targets rounded to 0.1 point. The release of existing dwellings acts once, while the '
          'rate falls.',
          '* The near-term excess is frozen in dwellings, so its floor area follows L1 and L4 through the blended size.',
          '* Levers are parameter changes on the baseline model; no behavioural, market or rebound response is '
          'modelled; interactions are those of the model (attributed by Shapley values).',
          '* The pathways are deterministic (median demographics); the baseline Monte Carlo is not re-run for them. '
          'Budgets are static (PB layer limitations apply).',
          '* Omitted in v2: ' + '; '.join(f'{a} ({b})' for a, b in LV.OMITTED) + '.', '',
          ] + (t_methods(tlim, runs) if tlim is not None else []) + ['', '## Sources', ''] + [f'* {v}' for v in p['sources'].values()]
    path = os.path.join(OUT, 'PATHWAYS_METHODS_DRAFT.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print(f'pathways_methods: {path} ({len(L)} lines), LEVERS_TABLE.md')


def sections():
    """The generated Pathways sections outside outputs/pathways/: FIGURES.md (pathways.update_figures_md)
    and ASSUMPTIONS.md (tools/assumptions.update_pathways_section). Both replace only their own
    section and are idempotent."""
    import pathways
    import assumptions
    pathways.update_figures_md()
    assumptions.update_pathways_section()


if __name__ == '__main__':
    main()
    if '--sections' in sys.argv:
        sections()
