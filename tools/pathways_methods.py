"""Generate the pathway documents from outputs/pathways/ (nothing typed by hand; vocabulary of
naming.py):

  outputs/reports/PATHWAYS_METHODS_DRAFT.md  equations, parameters with sources, L5 estimator,
                                             attribution, gap, results tables, checks, limitations
  outputs/reports/LEVERS_TABLE.md            Table 1 of the paper: one row per lever and per TL assumption

from outputs/data/pathways/. With --sections also the Pathways section of
outputs/reports/ASSUMPTIONS.md (it replaces only its own section; idempotent; run_all.py
--pathways-only).

    python tools/pathways_methods.py [--sections]
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

REF = 'REF'
DATA = layout.data('pathways', frozen=False)


def table(head, rows):
    L = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    L += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return L


def tl_levers_table(t):
    import levers as LV
    L = ['', '## Theoretical limit TL', '', '> ' + t['disclaimer'], '',
         'TL = P5 Ambitious (L4 removals -40%; L1, L2 / L3 and L5 replaced by TL2, TL1 and TL4) with the overrides '
         'below, all at full strength from 1 January 2027 (no adoption path); 2026 observed and untouched. '
         + LV.TL_BAU_NOTE + ' Sensitivity (SI): ' + N.TL_GRADUAL + ', the same TL on the adopted logistic path.', '']
    L += table(['item', 'pathway', 'demand band targeted', 'how it works (model terms)', 'assumption', 'TL value',
                'source (full citation)', 'tag'],
               [[r['item'], r['pathway'], r['band'], r['how'], r['assumption'], r['value'], r['source'], r['tag']]
                for r in LV.tl_table(t)])
    L += ['', 'Table note: ' + t['disclaimer']]
    return L


def tl_methods(t, runs):
    import levers as LV
    ind, gap = t['indicators']['TL'], t['gap']
    r = {n: runs[(runs['run'] == n) & (runs['scenario'] == REF)].iloc[0]
         for n in (REF, 'P5-moderate', 'P5-ambitious', 'TL', 'TL-gradual')}
    sh = pd.DataFrame(t['shapley'])
    tl6 = t['definition']['tl6']
    L = ['', '## Theoretical limit TL', '', '> ' + t['disclaimer'], '',
         '**Definition.** TL = P5 Ambitious with six overrides at full strength from 1 January 2027 (w = 1 for every '
         'lever in 2027-2050, no adoption path; 2026 observed and untouched): TL1 No vacancy (v = 0; the 2026 overbuild '
         'absorbed in full), TL2 No extra space (new-dwelling size = occupied area S(t) · OLF), TL3 Minimum space per '
         'person (OLF of every new building = the lowest independent design OLF), TL4 Best-practice materials (each '
         'typology at its own best independent case; apartments held), TL5 Lowest-carbon soils (lowest soil order), '
         'TL6 Urban infill (a share s of the non-replacement new floor area on previously developed land, zero soil '
         'carbon loss). L4 (−40%) as P5 Ambitious; the typology shares stay at the Reference held mix. '
         + t['definition']['bau'] + ' The potentials hierarchy (theoretical > technical > realisable) places TL at '
         'the theoretical end; ' + N.TL_GRADUAL + ' is a sensitivity.', '']
    L += table(['item', 'how it works (model terms)', 'assumption', 'TL value', 'source (full citation)', 'tag'],
               [[x['item'], x['how'], x['assumption'], x['value'], x['source'], x['tag']] for x in LV.tl_table(t)])
    L += ['', f"Table note: {t['disclaimer']}", '',
          '**Banking rule (TL1).** raw_t = requirement_t + absorbed 2026 overbuild_t (negative when the release of '
          'vacant or surplus dwellings exceeds the year\'s need); D_t = raw_t − bank_(t−1); built_t = max(0, D_t); '
          'bank_t = max(0, −D_t). The banked path enters engine.forward as a stock-adding join, join_t = built_t − '
          'requirement_t (join_redev = 0), so the stock identity holds and implied vacancy = stock_join / (households + '
          'stock_join) ≥ 0. Banked zero-building years carry floating-point noise of about 1e-12 dwellings; the checks '
          'use 1e-6 dwellings. The banking rule is applied in every TL-family run (it binds only where the release '
          'exceeds the need).', '',
          '**Soil path (TL5, TL6).** The engine takes one soil factor per typology; the year-dependent factor is applied '
          'exactly by replacing the engine soil term in the intensity: I\'(y) = I(y) − SOC_avg · share(y) + SOC_path(y) · '
          'share(y), with share(y) the soil-bearing (non-replacement) share of the floor area built in year y, taken from '
          'the engine and independent of the intensity (identical in both passes; tested). TL5: SOC_path = SOC_low. TL6: '
          f"SOC_path(y) = SOC_TL5(y) · (1 − s w(y)), s = {tl6['components'][0]} × {tl6['components'][1]} = "
          f"{tl6['components'][0] * tl6['components'][1]:.3f}, rounded {tl6['share']}, i.e. a share s of each year's "
          'non-replacement floor area carries zero soil carbon loss and the rest the TL5 factor (tested to 1e-9). The '
          'engine share is 1 − soil-free / total floor area; in banked years with no new building (total ≈ 0, '
          'floating-point noise) it is undefined, so share(y) is clipped to [0, 1] and set to 0 where the floor area '
          'built is ≤ 1e-3 m² (pathways v3.1 correction; CHANGELOG).', '',
          f"**TL6 source and assumptions.** {tl6['source']}. Assumptions: " + '; '.join(tl6['assumptions'])
          + '. Tag: DATA (the Auckland shares) + DECISION (author: their national application to floor area).', '',
          '### Results (Reference)', '']
    rows = [[N.run_label(n), f"{x['floor_area_Mm2']:.2f}", f"{x['carbon_kt']:,.0f}",
             f"{x['committed_lower_kt']:,.0f}-{x['committed_upper_kt']:,.0f}",
             f"{x['LoE_AR']:.3f}", f"{x['LoE_AtP']:.2f}", f"{100 * x['remaining_reduction_AR']:.1f}%",
             f"{x['delta_carbon_kt_vs_reference_pct']:+.1f}%"] for n, x in r.items()]
    L += table(['run', 'floor area (Mm²)', 'carbon 2026-2050 (kt)', 'committed after 2050 (kt)', 'LoE AR', 'LoE AtP',
                'AR reduction still needed', 'carbon vs Reference'], rows)
    L += ['', f"Table note: {t['disclaimer']}"]
    zy = ind['zero_building_years']
    L += ['', '**Human terms (TL, 2027-2050).** New-dwelling size '
          + ', '.join(f"{k} {v['2050']:.1f} m²" for k, v in ind['new_dwelling_size_m2'].items())
          + f" (2050); floor area per person in new dwellings {ind['m2_per_person_new_dwellings']['2050']:.1f} m²; "
          f"vacant dwellings released by the vacancy change {ind['vacancy_change_release_dwellings']:,.0f} and 2026 "
          f"overbuild absorbed {ind['overbuild_2026_absorbed_dwellings']:,.0f}; release in excess of the yearly need "
          f"{ind['release_added_total']:,.0f} dwellings, used {ind['release_used_total']:,.0f}, unused in 2050 "
          f"{ind['bank_unused_2050']:,.0f}; no new building in {len(zy)} years"
          + (f" ({zy[0]}-{zy[-1]})" if zy else '') + '. Dwellings built per year, implied vacancy and the banking path by '
          'year: theoretical_limit.json.', '']
    g = gap['TL']
    if g['within_AR']:
        L += [f"**Gap.** TL is within the AR budget: margin {g['margin_AR_kt']:,.0f} kt ({100 * g['margin_AR_share']:.1f}%)."]
    else:
        b, rs = g['backcast'], g['residual']
        L += [f"**Gap.** TL exceeds the AR budget (cumulative LoE AR {g['LoE_AR']:.3f}): a uniform cut of "
              f"{100 * b['cut_AR']:.1f}% of 2027-2050 construction (k = {b['k_AR']:.4f}, brentq) would reach LoE AR = 1. "
              f"In people: {rs['dwellings_not_built_2027_2050']:,.0f} dwellings not built in 2027-2050 (in-scope dwellings "
              f"of the 2027-2050 cohorts × (1 − k)), i.e. {rs['new_residents_housed_in_existing_dwellings']:,.0f} new "
              'residents housed in existing dwellings (Σ_t dwellings not built_t × S(t), S = persons per household of the '
              'median path); where they would be housed is not modelled (TL1 already sets vacancy to zero). '
              f"AtP: TL {b['LoE_AtP_at_k1']:.2f}; the minimum attainable (2026 cohort alone) is {b['LoE_AtP_min_k0']:.2f}, "
              'so AtP is not attainable within 2026-2050.']
    L += ['', '### Shapley attribution of P5 Ambitious (full strength from 2027) − TL', '']
    rows = []
    comps = list(t['definition']['components'])
    for pl in comps + [LV.TL_FROM2027]:
        c = sh[(sh['metric'] == 'carbon_kt') & (sh['player'] == pl)].iloc[0]
        a = sh[(sh['metric'] == 'LoE_AR') & (sh['player'] == pl)].iloc[0]
        share = c['share_of_P5_ambitious_from2027_minus_TL']
        rows.append([N.ADOPTION['from2027'] + ' (separate line)' if pl == LV.TL_FROM2027
                     else f"{pl} {t['definition']['components'][pl]}",
                     f"{c['reduction']:,.0f}" + ('' if pd.isna(share) else f" ({100 * share:.0f}%)"),
                     f"{a['reduction']:.3f}"])
    L += table(['player', 'carbon (kt)', 'LoE AR'], rows)
    L += ['', f"Players TL1-TL{len(comps)} over {2 ** len(comps)} subsets, each applied at full strength from 2027 "
          '(exact rational arithmetic; the values add up to P5 Ambitious at full strength from 2027 − TL exactly; '
          'tested). "Full strength from 2027" is a separate line, not a player: P5 Ambitious on its adoption path minus '
          'P5 Ambitious at full strength from 2027. '
          f"Sensitivity: {N.TL_GRADUAL} gives LoE AR {r['TL-gradual']['LoE_AR']:.3f}.", '',
          '### Limitations of TL', '',
          '* TL combines attributes of different buildings and places (the OLF of A_1, an apartment block, applied to '
          'every typology; each typology\'s best A1-A3 case; the lowest soil order everywhere; Auckland\'s 2020/21 '
          'intensification share nationally) that have not been observed together; it is a hyper-optimistic thought '
          'experiment, not a design, a policy or a feasible pathway.',
          '* TL2 + TL3 give every new dwelling the occupied area of the case-study minimum (about 20 m² per person); no '
          'design rule, accessibility standard or household-size variation is modelled.',
          '* TL1 assumes every vacant dwelling is usable where it is needed (no spatial or condition mismatch; Napiontek '
          'et al. 2025 on hibernating stock) and an instant reallocation in 2027.',
          '* TL6 is an upper bound on the soil saving (assumption iii: some infill builds over garden soil) and transfers '
          'a dwelling-count share of one city to national floor area; its benefits beyond soil (infrastructure, '
          'transport energy) are outside the embodied-carbon scope, as for the removed denser typology mix.',
          '* As in P1-P5, the renovation carbon of the retained stock (L4) and any rebound are not modelled; '
          'deterministic, median demographics; static budgets.']
    return L


def levers_table(p, t=None):
    import levers as LV
    rows = LV.lever_table(p)
    L = ['# Table 1. Pathway levers and theoretical-limit assumptions (generated by tools/pathways_methods.py '
         'from outputs/pathways/levers.json and theoretical_limit.json; do not edit by hand)', '']
    if p['run_mode'] != 'full':
        L += [f"> **{p['run_mode']}**", '']
    L += ['The Reference projection; each lever follows a normalised logistic adoption path from 2026 (observed, '
          f"unchanged) to full strength in 2035 ({LV.RAMP_BASIS}; sensitivities: full roll-out by 2030 and by 2045). "
          'Levers L1-L5; the typology shares stay at the Reference held mix in every run. Tags: DATA (measured), '
          'LITERATURE (cited), DECISION (author).', '']
    L += table(['item', 'pathway', 'demand band targeted', 'how it works (model terms)', 'assumption', 'Moderate',
                'Ambitious', 'source (full citation)', 'tag'],
               [[r['item'], r['pathway'], r['band'], r['how'], r['assumption'], r['moderate'], r['ambitious'],
                 r['source'], r['tag']] for r in rows])
    n = p['denser_mix_pathways_v2']['note']
    L += ['', f"Removed: {N.DENSER_MIX}. {n['text']} Tag {n['tag']} (Reference): attached share "
          f"{100 * n['attached_share']['baseline']:.2f}% -> {100 * n['attached_share']['moderate']:.2f}% / "
          f"{100 * n['attached_share']['ambitious']:.2f}% (Moderate / Ambitious); carbon "
          f"{n['carbon_vs_reference_pct']['moderate']:+.2f}% / {n['carbon_vs_reference_pct']['ambitious']:+.2f}% vs the "
          f"Reference; floor area {n['floor_area_Mm2']['REF']:.2f} -> {n['floor_area_Mm2']['moderate']:.2f} / "
          f"{n['floor_area_Mm2']['ambitious']:.2f} Mm²; carbon per m² {n['carbon_per_m2_kg']['REF']:.1f} -> "
          f"{n['carbon_per_m2_kg']['moderate']:.1f} / {n['carbon_per_m2_kg']['ambitious']:.1f} kg CO₂e; lever Shapley "
          f"share of Reference − P5 {100 * n['shapley_share_of_reference_minus_P5']['moderate']:.1f}% / "
          f"{100 * n['shapley_share_of_reference_minus_P5']['ambitious']:.1f}%."]
    if t is not None:
        L += tl_levers_table(t)
    with open(layout.writing(layout.report('LEVERS_TABLE.md', frozen=False)), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')


def main():
    import levers as LV
    p = json.load(open(os.path.join(DATA, 'levers.json')))
    runs = pd.read_csv(os.path.join(DATA, 'runs.csv'))
    bands = pd.read_csv(os.path.join(DATA, 'bands.csv'))
    shp = pd.read_csv(os.path.join(DATA, 'shapley_pathways.csv'))
    shl = pd.read_csv(os.path.join(DATA, 'shapley_levers.csv'))
    bc = json.load(open(os.path.join(DATA, 'backcast.json')))
    t_path = os.path.join(DATA, 'theoretical_limit.json')
    tlim = json.load(open(t_path)) if os.path.exists(t_path) else None
    levers_table(p, tlim)
    ref = runs[(runs['scenario'] == REF) & (runs['adoption'] == LV.ADOPTION_ADOPTED)
               & ~runs['l5_apartments_held'].astype(bool)].set_index('run')
    p0 = ref.loc[REF]
    e5 = p['L5']['estimator']
    note = p['denser_mix_pathways_v2']['note']
    ad = p['adoption']
    L = ['# Pathways: methods (DRAFT; generated by tools/pathways_methods.py, do not edit by hand)', '']
    if p['run_mode'] != 'full':
        L += [f"> **{p['run_mode']}**", '']
    L += [
        'Five pathways for new residential construction in New Zealand, 2026-2050, built from five levers and applied '
        'to the Reference projection, assessed against the climate-change budgets of the AESA layer (acquired rights, '
        'AR; ability to pay, AtP). The model is unchanged: `pathways.py` re-calls `engine.forward()` with copies of '
        'the Reference inputs modified by `levers.py` (hooks: docs/HOOKS.md); no projection output is rewritten. With '
        'every lever off the run reproduces the Reference '
        f"(maximum relative difference {p['identity_max_rel_diff']:.1e}; tests/test_pathways.py). "
        'Table 1: outputs/reports/LEVERS_TABLE.md.', '',
        '## Pathways and demand bands', '',
        '| pathway | levers | demand band targeted |', '|---|---|---|',
        f"| P1 {LV.PATHWAY_NAMES['P1']} | L1 {LV.LEVER_NAMES['L1']} | {LV.BAND_TARGET['L1']} |",
        f"| P2 {LV.PATHWAY_NAMES['P2']} | L2 {LV.LEVER_NAMES['L2']}, L3 {LV.LEVER_NAMES['L3']} | "
        f"{LV.BAND_TARGET['L2']}; {LV.BAND_TARGET['L3']} |",
        f"| P3 {LV.PATHWAY_NAMES['P3']} | L4 {LV.LEVER_NAMES['L4']} | {LV.BAND_TARGET['L4']} |",
        f"| P4 {LV.PATHWAY_NAMES['P4']} | L5 {LV.LEVER_NAMES['L5']} | {LV.BAND_TARGET['L5']} |",
        f"| P5 {LV.PATHWAY_NAMES['P5']} | all five | all of the above |", '',
        '**Typology mix (denser mix removed).** ' + note['text'] + ' Values from tag pathways_v2 (Reference): '
        f"Moderate / Ambitious carbon {note['carbon_vs_reference_pct']['moderate']:+.2f}% / "
        f"{note['carbon_vs_reference_pct']['ambitious']:+.2f}% vs the Reference while carbon per m² rose from "
        f"{note['carbon_per_m2_kg']['REF']:.1f} to {note['carbon_per_m2_kg']['moderate']:.1f} / "
        f"{note['carbon_per_m2_kg']['ambitious']:.1f} kg CO₂e; its lever Shapley share was "
        f"{100 * note['shapley_share_of_reference_minus_P5']['moderate']:.1f}% / "
        f"{100 * note['shapley_share_of_reference_minus_P5']['ambitious']:.1f}%. The typology shares stay at the "
        'Reference held mix in every run (the Reference, P1-P5 and TL).', '',
        'Population growth and Smaller households are untargeted by design: population and household formation are '
        'exogenous (as in Pellan et al. 2024). Every run reports floor area and carbon by demand band '
        '(outputs/data/pathways/bands.csv), so the attribution by band is exact and needs no decomposition.', '',
        '## Conventions', '',
        f"* Adoption path (all levers): s(y) = 1 / (1 + exp(−k (y − {ad['mid']}))), k = ln(81)/6 = {ad['k']:.4f} "
        '(s rises from 10% to 90% within 6 years); w(y) = (s(y) − s(2026)) / (s(2035) − s(2026)) for 2026 ≤ y ≤ 2035, '
        'w = 1 after 2035, w(2026) = 0 (full roll-out by 2035, adopted). A lever moves a quantity from its Reference '
        f"value b to its target x as b + w(y)(x − b). Basis: {LV.RAMP_BASIS}. Sensitivities (P5), same k: full "
        f"roll-out by 2030 (midpoint {LV.ADOPTION_BY2030['mid']}, full strength {LV.ADOPTION_BY2030['end']}) and by "
        f"2045 (midpoint {LV.ADOPTION_BY2045['mid']}, full strength {LV.ADOPTION_BY2045['end']}; the same adoption "
        'speed ten years later).',
        '* 2026 is observed (consented floor area fixed) and identical in every run.',
        '* 2026 overbuild: held at the Reference path, in dwellings, except where L3 absorbs it (it is the observed '
        '2026 pipeline, not demand).',
        '* Accounting as the Reference (time-resolved): carbon 2026-2050 = upfront (materials and construction A1-A5 and '
        'soil carbon loss) in the construction year + maintenance (B2, B4) in 2026-2050; later events and all C1-C4 of '
        'the 2026-2050 cohorts are committed after 2050 (range: lower with the 2050 factors held, upper at 2025 '
        'factors; `events.committed` with each run\'s floor area by typology).', '',
        '## Levers as implemented (levers.py)', '',
        '    L1   size_t(y) = occ_t(y) + [1 − f w(y)] (size_ref_t − occ_t(y)),   occ_t(y) = S(y) · OLF_t',
        '    L2   v(y) = v0 + w(y)(v* − v0)',
        '    L3   join = market_excess(E_nojoin, O26, ρ, 2027, surplus, absorption a)',
        '    L4   demol(y) = demol · (1 − w(y) d);  resid(y) = resid_LR + (resid_REF(y) − resid_LR)(1 − w(y) d)',
        '    L5   A1-A3_t(y) = [1 − w(y)(1 − r)] · (A1-A3_t,2025 − R13_t(y))   (A4-A5, B events, C1-C4, soil unchanged)', '',
        'S and OLF are the engine\'s (S = population / households of the median path; OLF per typology from the '
        'case studies), so occ_t is the occupied area the engine uses for the population-growth and extra-space bands. '
        'size_ref: realised new-dwelling size, mean of 2023-2025. L1 removes a share f of the extra-space margin '
        '(size − S(y) · OLF): full strength in 2035, f held constant to 2050, so the sizes then follow S(y). L1 holds a '
        f"typology / year at size_ref where size_ref ≤ occ (never binds: {len(p['L1']['held'])} typology-years held). "
        'L2 acts through the stock identity: while v falls the vacancy-change term releases existing dwellings once '
        '(cumulative release in runs.csv, by year in annual.csv); under the logistic adoption path '
        'the release peaks where w rises fastest (2029-2032). R13: the A1-A3 decarbonisation of the Reference (Horup '
        'et al. 2025, item level).', '',
        '## Parameters and sources', '']
    L += table(['setting', 'value', 'basis'], LV.register(p))
    L1 = p['L1']
    L += ['', '### L1: implied new-dwelling sizes', '']
    rows = []
    for t in L1['size_ref']:
        for y in LV.L1_REPORT_YEARS:
            c, s = LV.by_year(L1['implied']['moderate'][t], y), LV.by_year(L1['implied']['ambitious'][t], y)
            rows.append([t, y, f"{L1['size_ref'][t]:.1f}", f"{c['occupied_m2']:.1f}", f"{c['size_m2']:.1f} ({c['cut_pct']:+.1f}%)",
                         f"{s['size_m2']:.1f} ({s['cut_pct']:+.1f}%)", f"{c['size_per_occupant_m2']:.1f} / {s['size_per_occupant_m2']:.1f}"])
    L += table(['typology', 'year', 'size_ref (m²)', 'occupied S·OLF (m²)', 'Moderate (m², cut)', 'Ambitious (m², cut)',
                'm² per occupant, Moderate / Ambitious'], rows)
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
               [[N.SETTINGS[s], f"{e5[s]['q']:.2f}", f"{e5[s]['r']:.4f}", f"{e5[s]['ci_lo']:.4f}-{e5[s]['ci_hi']:.4f}",
                 f"{e5[s]['scipy_hdquantiles']:.4f}"] for s in LV.SETTINGS])
    L += ['']
    L += table(['case', 'typology', 'A1-A3 (kg/m²)', 'ratio x_i'],
               [[c['id'], c['typology'], f"{c['a13']:.1f}", f"{c['ratio']:.3f}"] for c in p['L5']['cases']])
    L += ['', '## Attribution', '',
          'Shapley values (Shapley 1953; for emissions decompositions Albrecht, François & Schoors 2002) of each '
          'player for the reduction v(∅) − v(N):', '',
          '    φ_i = Σ_{S ⊆ N∖{i}} |S|! (|N| − |S| − 1)! / |N|! · [v(S) − v(S ∪ {i})]', '',
          'Players: the four pathways P1-P4 (|N| = 4, 16 subsets; main) and the five levers (|N| = 5, 32 subsets; SI); '
          'every subset is a full run; v = cumulative carbon 2026-2050 (kt) or cumulative LoE AR. Computed in exact '
          'rational arithmetic on the run values, so Σ_i φ_i = Reference − P5 exactly (tested).', '',
          '## AESA gap', '',
          'Budgets B_AR(t), B_AtP(t) for the Reference from outputs/pb_annual.csv (no lever changes population). '
          'Cumulative LoE = Σ I(t) / Σ B(t) over 2026-2050 (aesa.cumulative_loe); remaining reduction needed = 1 − 1/LoE.', '',
          '**Back-cast.** I(t; k) = F(t) + k · G(t), F the 2026 cohort (its upfront carbon and its maintenance in '
          '2026-2050), G the 2027-2050 cohorts; scaling their floor area by k keeps the typology mix and the replacement '
          'share, hence the soil share. k solves Σ I(t; k) = Σ B_AR(t) (scipy.optimize.brentq on [0, 1], xtol 1e-15; '
          'checked against the closed form). AtP: the minimum attainable cumulative LoE is Σ F / Σ B_AtP (k = 0).', '',
          '**Solution space** (after Horup et al. 2025, Fig. 6): I(t; d, i) = F(t) + (1 − d)[(1 − i) G_ns(t) + '
          'G_soil(t)] on the Reference. Pathways sit at d = 1 − floor area_P / floor area_REF and i = 1 − (C_P / floor '
          'area_P) / (C_REF / floor area_REF) (2027-2050 cohorts; C excludes soil carbon loss, within 2026-2050); a '
          'negative i would mean more carbon per m².', '',
          '## Results (Reference)', '']
    rows = []
    names = [REF] + [f'{P}-{s}' for P in ('P1', 'P2', 'P3', 'P4', 'P5') for s in LV.SETTINGS]
    for name in names:
        r = ref.loc[name]
        rows.append([N.run_label(name), f"{r['floor_area_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}",
                     f"{r['committed_lower_kt']:,.0f}-{r['committed_upper_kt']:,.0f}", f"{r['LoE_AR']:.2f}",
                     f"{r['LoE_AtP']:.1f}", f"{100 * r['remaining_reduction_AR']:.1f}%",
                     f"{r['delta_carbon_kt_vs_reference_pct']:+.1f}%", f"{r['dwellings_built']:,.0f}",
                     f"{r['mean_dwelling_size_m2']:.1f}", f"{r['carbon_per_m2_kg']:.1f}",
                     f"{r['existing_dwellings_released']:,.0f}", f"{100 * r['implied_vacancy_min']:.2f}%"])
    L += table(['run', 'floor area (Mm²)', 'carbon 2026-2050 (kt)', 'committed after 2050 (kt)', 'LoE AR', 'LoE AtP',
                'AR reduction still needed', 'carbon vs Reference', 'dwellings built', 'mean size (m²)', 'kg CO₂e/m²',
                'existing dwellings released', 'min implied vacancy'], rows)
    L += ['', '### Floor area cut by demand band, Moderate (Mm², vs the Reference; in-scope definition)', '']
    bd = bands[(bands['scenario'] == REF) & (bands['definition'] == 'in_scope')]
    blist = list(dict.fromkeys(bd['band']))
    rows = []
    for b in blist:
        if b == N.band_data_label('maintenance'):
            continue
        rows.append([b] + [f"{bd[(bd['run'] == f'{P}-moderate') & (bd['band'] == b)]['delta_floor_area_Mm2_vs_reference'].iloc[0]:+.2f}"
                           for P in ('P1', 'P2', 'P3', 'P4', 'P5')])
    rows.append(['**total**'] + [f"{ref.loc[f'{P}-moderate', 'floor_area_Mm2'] - p0['floor_area_Mm2']:+.2f}"
                                 for P in ('P1', 'P2', 'P3', 'P4', 'P5')])
    L += table(['band', 'P1', 'P2', 'P3', 'P4', 'P5'], rows)
    L += ['', '### Shapley attribution of Reference − P5 (pathways)', '']
    srows = []
    for P in LV.PATHWAYS:
        line = [f'{P} {LV.PATHWAY_NAMES[P]}']
        for s in LV.SETTINGS:
            for metric, fmt in (('carbon_kt', '{:,.0f}'), ('LoE_AR', '{:.3f}')):
                x = shp[(shp['setting'] == s) & (shp['metric'] == metric) & (shp['player'] == P)].iloc[0]
                line.append(fmt.format(x['reduction']) + (f" ({100 * x['share_of_reference_minus_P5']:.0f}%)"
                                                          if metric == 'carbon_kt' else ''))
        srows.append(line)
    srows.append(['Reference − P5'] + [v for s in LV.SETTINGS
                                       for v in (f"{p0['carbon_kt'] - ref.loc[f'P5-{s}', 'carbon_kt']:,.0f}",
                                                 f"{p0['LoE_AR'] - ref.loc[f'P5-{s}', 'LoE_AR']:.3f}")])
    L += table(['pathway', 'Moderate: carbon (kt)', 'Moderate: LoE AR', 'Ambitious: carbon (kt)', 'Ambitious: LoE AR'],
               srows)
    L += ['', '### Shapley attribution of Reference − P5 (levers, SI)', '']
    srows = []
    for Lv in LV.LEVERS:
        line = [f'{Lv} {LV.LEVER_NAMES[Lv]}']
        for s in LV.SETTINGS:
            x = shl[(shl['setting'] == s) & (shl['metric'] == 'carbon_kt') & (shl['player'] == Lv)].iloc[0]
            line.append(f"{x['reduction']:,.0f} ({100 * x['share_of_reference_minus_P5']:.0f}%)")
        srows.append(line)
    L += table(['lever', 'Moderate: carbon (kt)', 'Ambitious: carbon (kt)'], srows)
    L += ['', '### Back-cast', '',
          f"Cumulative budgets 2026-2050: AR {bc['B_AR_kt']:,.0f} kt, AtP {bc['B_AtP_kt']:,.0f} kt. The 2026 cohort "
          f"alone (construction and its maintenance in 2026-2050, fixed) emits {bc[REF]['carbon_fixed_2026_cohort_kt']:,.0f} kt.", '']
    keys = ['P5-moderate', 'P5-ambitious', REF]
    L += table([''] + [N.run_label(k) for k in keys],
               [['LoE AR at k = 1'] + [f"{bc[k]['LoE_AR_at_k1']:.3f}" for k in keys],
                ['k for cumulative LoE AR = 1'] + [f"{bc[k]['k_AR']:.4f}" for k in keys],
                ['cut of 2027-2050 construction (1 − k)'] + [f"{100 * bc[k]['cut_AR']:.1f}%" for k in keys],
                ['2027-2050 floor area at k (Mm²)'] + [f"{bc[k]['floor_area_2027_2050_at_k_Mm2']:.2f}" for k in keys],
                ['equivalent floor-area cut vs the Reference'] + [
                    f"{100 * bc[k]['equivalent_cut_vs_reference_floor_area']:.1f}%" if k != REF else '-' for k in keys],
                ['minimum LoE AtP (k = 0)'] + [f"{bc[k]['LoE_AtP_min_k0']:.3f}" for k in keys]])
    L += ['', f"AtP: {bc['AtP_note']} (minimum cumulative LoE AtP with no construction after 2026: "
          f"{bc[REF]['LoE_AtP_min_k0']:.2f}).", '', '### Replacement variants, adoption paths and L5 sensitivities', '']
    erows = []
    for scen in ('LOW', REF, 'HIGH'):
        for name in (scen, 'P5-moderate', 'P5-ambitious', 'P5-moderate-by2030', 'P5-ambitious-by2030',
                     'P5-moderate-by2045', 'P5-ambitious-by2045'):
            r = runs[(runs['scenario'] == scen) & (runs['run'] == name)].iloc[0]
            erows.append([N.SCENARIOS[scen], N.run_label(name), f"{r['floor_area_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}",
                          f"{r['LoE_AR']:.2f}", f"{r['LoE_AtP']:.1f}", f"{r['delta_carbon_kt_vs_reference_pct']:+.1f}%"])
    for name in ('P4-moderate-apartments-held', 'P4-ambitious-apartments-held', 'P5-moderate-apartments-held',
                 'P5-ambitious-apartments-held'):
        r = runs[(runs['scenario'] == REF) & (runs['run'] == name)].iloc[0]
        erows.append([N.SCENARIOS[REF], N.run_label(name) + ' (L5)', f"{r['floor_area_Mm2']:.2f}",
                      f"{r['carbon_kt']:,.0f}", f"{r['LoE_AR']:.2f}", f"{r['LoE_AtP']:.1f}",
                      f"{r['delta_carbon_kt_vs_reference_pct']:+.1f}%"])
    L += table(['projection variant', 'run', 'floor area (Mm²)', 'carbon (kt)', 'LoE AR', 'LoE AtP',
                'carbon vs the variant without levers'], erows)
    L += ['', '### End of the adoption path (P2)', '']
    L += table(['run', 'w(2035) − w(2034)', 'carbon 2035 → 2036 (kt)', 'Reference 2035 → 2036 (kt)',
                'step relative to the Reference (kt)', 'dwellings 2035 → 2036'],
               [[N.run_label(k.replace('end_of_ramp_step_', '')), f"{d['w_2035_minus_w_2034']:.4f}",
                 f"{d['carbon_step_kt']:+.1f}", f"{d['reference_carbon_step_kt']:+.1f}",
                 f"{d['step_relative_to_reference_kt']:+.1f}", f"{d['dwellings_step']:+,.0f}"]
                for k, d in p['diagnostics'].items() if k.startswith('end_of_ramp_step')])
    L += ['', '## Checks (tests/test_pathways.py, tests/test_regression_model_v1.py)', '',
          '* No lever = the Reference (≤ 1e-9 relative): annual carbon, upfront, maintenance 2026-2050, floor area by '
          'typology, demand bands, committed range, cumulative LoE AR / AtP; LOW and HIGH without levers = the AESA '
          'variant runs.',
          '* Each lever at zero strength = the Reference; 2026 identical in every run; lever functions never modify '
          'their inputs; the logistic adoption path is 0 in 2026, 1 from 2035 and monotone.',
          '* L1 sizes ≥ occupied area S·OLF in every typology, year and run; D ≥ S·OLF (engine extra_clip = 0); implied '
          f"vacancy ≥ {100 * p['L2']['floor']:.1f}%; no negative dwellings built.",
          '* Harrell-Davis = scipy.stats.mstats.hdquantiles (≤ 1e-10); pathway and lever Shapley efficiency exact; '
          'demand bands add up to the totals; back-cast LoE AR = 1 (≤ 1e-9).',
          '* Every number of the model reproduced to 1e-12 relative against the capture before the MODEL v1.0.0 '
          'refurbish (tests/test_regression_model_v1.py).', '',
          '## Limitations', '',
          '* L4 is an upper bound: the carbon of renovating the buildings kept in use is not modelled (Napiontek et '
          'al. 2025, Resour. Conserv. Recycl. 215, 108117).',
          f"* L5 rests on {p['L5']['n']} case studies; the Ambitious interval is wide ({e5['ambitious']['ci_lo']:.2f}-"
          f"{e5['ambitious']['ci_hi']:.2f}). The ratio is pooled across detached and townhouses (scale-free) and applied "
          'to apartments too (one independent apartment case; held at r = 1 as a sensitivity), and to the pooled '
          'A1-A3 of every item: the best-practice material mix is assumed transferable.',
          '* L1 keeps the engine\'s occupied area (S·OLF) and cuts only the space above it; the occupancy load factor '
          'per typology and design rules (minimum room sizes) are not modelled.',
          '* The typology mix is held at the Reference (the denser mix removed; see above): the infrastructure, '
          'operational-energy and land benefits of denser forms are outside the embodied-carbon scope.',
          f"* L2: v0 = {100 * p['L2']['v0']:.2f}% is the published 2023 empty-dwelling share while the target range "
          f"({100 * p['L2']['census_consistent_min']:.2f}% in {p['L2']['census_consistent_min_year']} to "
          f"{100 * p['L2']['census_consistent_max']:.2f}% in {p['L2']['census_consistent_max_year']}) is on a "
          'consistent definition; targets rounded to 0.1 point; 4.0% is the lowest NZ vacancy rate on that definition. '
          'The release of existing dwellings acts once, while the rate falls.',
          '* The 2026 overbuild is held in dwellings, so its floor area follows L1 through the blended size.',
          '* Levers are parameter changes on the Reference model; no behavioural, market or rebound response is '
          'modelled; interactions are those of the model (attributed by Shapley values).',
          '* The pathways are deterministic (median demographics); the Monte Carlo is not re-run for them. '
          'Budgets are static (AESA layer limitations apply).',
          '* Omitted: ' + '; '.join(f'{a} ({b})' for a, b in LV.OMITTED) + '.', '',
          ] + (tl_methods(tlim, runs) if tlim is not None else []) + ['', '## Sources', ''] + [f'* {v}' for v in p['sources'].values()]
    path = layout.writing(layout.report('PATHWAYS_METHODS_DRAFT.md', frozen=False))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print(f'pathways_methods: {path} ({len(L)} lines), LEVERS_TABLE.md')


def sections():
    """The Pathways section of outputs/reports/ASSUMPTIONS.md (tools/assumptions.update_pathways_section;
    it replaces only its own section and is idempotent)."""
    import assumptions
    assumptions.update_pathways_section()


if __name__ == '__main__':
    main()
    if '--sections' in sys.argv:
        sections()
