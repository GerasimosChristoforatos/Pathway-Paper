"""Generate the documents of the pathways and the theoretical limit TL from outputs/data/pathways/
(no number typed by hand; reader-facing labels from naming.py):

  lines()                                    the pathways part of the methods draft (pathways and
                                             demand bands, levers, parameters with sources, L6
                                             estimator, attribution, AESA gap, results, checks,
                                             limitations, the theoretical limit TL, sources);
                                             tools/methods_draft.py merges it into
                                             outputs/reports/METHODS_DRAFT.md
  outputs/reports/LEVERS_TABLE.md            Table 1 of the paper: one row per lever and per TL assumption
                                             (main())

With --sections also the Pathways section of outputs/reports/ASSUMPTIONS.md (it replaces only
its own section; idempotent; run_all.py --pathways-only).

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
# the denser typology mix (naming.DENSER_MIX: lever of pathways_v2, removed in pathways_v3.1; never
# given a lever number): its text and values from levers.json denser_mix_pathways_v2 (levers.py)
DENSER_MIX_VALUES = 'Values from git tag pathways_v2 (Reference)'


def vacancy_sentence():
    """The release wording of the vacancy assumption of the Reference (naming.vacancy_wording),
    from outputs/data/baseline/overbuild_2026.json."""
    with open(layout.data('baseline/overbuild_2026.json', frozen=False)) as f:
        v = json.load(f)['vacancy']
    c = v['consistent']
    return N.vacancy_wording(v['v_forward'], v['consistent_max'], v['consistent_min'], min(c, key=c.get),
                             v['v_2050'])


def table(head, rows):
    L = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    L += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return L


def tl_levers_table(t):
    import levers as LV
    L = ['', '## Theoretical limit TL', '', '> ' + t['disclaimer'], '',
         'TL = P5 Combined (Moderate) with TL1-TL10, every lever and TL item at full strength from 1 January 2027 '
         '(no adoption path); 2026 observed and untouched; the banking rule applies (dwellings released by the vacancy, '
         'by larger households and by the absorbed 2026 overbuild are used before any new building). Each TL item is '
         'the limit of one lever (TL10 has no lever counterpart) and is asserted at least as strong as that lever\'s '
         'Ambitious setting (pathways.compute_tl stops otherwise). ' + LV.TL_BAU_NOTE, '']
    L += table(['item', 'limit of', 'TL value', 'vs Ambitious', 'how it works (model terms)', 'source (full citation)',
                'tag'],
               [[r['item'], r['pathway'], r['value'], r['assumption'].replace('vs Ambitious: ', ''), r['how'],
                 r['source'], r['tag']] for r in LV.tl_table(t)])
    L += ['', 'Table note: ' + t['disclaimer']]
    return L


def tl_methods(t, runs):
    import levers as LV
    ind, gap = t['indicators']['TL'], t['gap']
    r = {n: runs[(runs['run'] == n) & (runs['scenario'] == REF)].iloc[0]
         for n in (REF, 'P5-moderate', 'P5-ambitious', 'TL')}
    res_ = t['resolved']
    L = ['', '## Theoretical limit TL', '', '> ' + t['disclaimer'], '',
         '**Definition.** TL = P5 Combined (Moderate) with ten items at full strength from 1 January 2027 (w = 1 for '
         'every lever and item in 2027-2050; 2026 observed and untouched): '
         + '; '.join(f"{k} {v} (limit of {t['definition']['limit_of'][k] or 'no lever'})"
                     for k, v in t['definition']['components'].items())
         + '. The typology shares stay at the Reference held mix. ' + t['definition']['bau']
         + ' The potentials hierarchy (theoretical > technical > realisable) places TL at the theoretical end.', '']
    L += table(['item', 'limit of', 'TL value', 'vs Ambitious', 'how it works (model terms)', 'source (full citation)',
                'tag'],
               [[x['item'], x['pathway'], x['value'], x['assumption'].replace('vs Ambitious: ', ''), x['how'],
                 x['source'], x['tag']] for x in LV.tl_table(t)])
    L += ['', 'Strength check (every TL item against the Ambitious setting of its lever): '
          + '; '.join(f"{row[0]} {row[1]} vs {row[2]}: {'OK' if row[3] else 'WEAKER'}" for row in t['strength']) + '.',
          '', f"Table note: {t['disclaimer']}", '',
          f"**TL2 and TL6.** TL2 sets the household size to {res_['TL2']['S']:.4f}, the highest of the model's "
          f"household-size history ({res_['TL2']['year']}; history {res_['TL2']['history_first_year']}-"
          f"{res_['TL2']['history_last_year']}), from 2027. TL6 applies one rule to every typology: r_TL = min(own best "
          'independent case, r_Ambitious); it exceeds the Ambitious ratio only where case-study evidence of a better '
          'case exists ('
          + ', '.join(f"{k} r = {v['r']:.3f}" + (f" ({v['own_best_building']})" if v['exceeds_ambitious'] else
                                                  ' = r_Ambitious') for k, v in res_['TL6'].items()) + ').', '',
          '**Banking rule.** raw_t = requirement_t + absorbed 2026 overbuild_t − release_t, with release_t = −min(Δ '
          'households_t, 0) / (1 − v_t) the dwellings that a fall in households (TL2) no longer needs; D_t = raw_t − '
          'bank_(t−1); built_t = max(0, D_t); bank_t = max(0, −D_t). The banked path enters engine.forward as a '
          'stock-adding join, join_t = built_t − requirement_t (join_redev = 0), so the stock identity holds and the '
          'implied vacancy is never negative. Banked zero-building years carry floating-point noise of about 1e-12 '
          'dwellings; the checks use 1e-6 dwellings. In those years every demand band is zero except the maintenance '
          '(B2, B4) of the cohorts already built.', '',
          '**Soil (TL8, TL9).** The soil factor by year (TL8: lowest soil order) and the brownfield share of all new '
          'floor area (TL9: s = 0.89, London) are applied inside engine.forward; the soil-bearing share is clipped to '
          '[0, 1] and set to 0 where the floor area built is at most 1e-3 m² (banked zero-building years).', '',
          '### Results (Reference)', '']
    rows = [[N.run_label(n), f"{x['floor_area_Mm2']:.2f}", f"{x['carbon_kt']:,.0f}",
             f"{x['committed_lower_kt']:,.0f}-{x['committed_upper_kt']:,.0f}",
             f"{x['LoE_AR']:.3f}", f"{x['LoE_AtP']:.2f}", f"{x['delta_carbon_kt_vs_reference_pct']:+.1f}%"]
            for n, x in r.items()]
    L += table(['run', 'floor area (Mm²)', 'carbon 2026-2050 (kt)', 'committed after 2050 (kt)', 'LoE AR', 'LoE AtP',
                'carbon vs Reference'], rows)
    L += ['', f"Table note: {t['disclaimer']}"]
    zy, rel = ind['zero_building_years'], ind['released_dwellings']
    L += ['', '**Human terms (TL, 2027-2050).** New-dwelling size '
          + ', '.join(f"{k} {LV.by_year(v, 2050):.1f} m²" for k, v in ind['new_dwelling_size_m2'].items())
          + f" (2050); floor area per person in new dwellings {LV.by_year(ind['m2_per_person_new_dwellings'], 2050):.1f} m²; "
          f"household size {LV.by_year(ind['household_size_by_year'], 2050):.3f} (2050). Released dwellings: "
          f"{rel['vacancy_change']:,.0f} from the vacancy (TL3), {rel['household_decline']:,.0f} from the larger households "
          f"(TL2) and {rel['overbuild_2026_absorbed']:,.0f} from the 2026 overbuild (TL4); release in excess of the yearly "
          f"need {ind['release_added_total']:,.0f} dwellings, used {ind['release_used_total']:,.0f}, unused in 2050 "
          f"{ind['bank_unused_2050']:,.0f}; no new building in {len(zy)} years"
          + (f" ({zy[0]}-{zy[-1]})" if zy else '') + '. By year: outputs/data/pathways/theoretical_limit.json.', '']
    g = gap['TL']
    if g['within_AR']:
        L += [f"**Gap.** TL is within the AR budget (cumulative LoE AR {g['LoE_AR']:.3f}): margin "
              f"{g['margin_AR_kt']:,.0f} kt ({100 * g['margin_AR_share']:.1f}% of the budget). AtP: TL "
              f"{g['LoE_AtP']:.2f}; the minimum attainable (2026 cohort alone) is {g['LoE_AtP_min_k0']:.2f}, so AtP is not "
              'attainable within 2026-2050.']
    else:
        b, rs = g['backcast'], g['residual']
        L += [f"**Gap.** TL exceeds the AR budget (cumulative LoE AR {g['LoE_AR']:.3f}): a uniform cut of "
              f"{100 * b['cut_AR']:.1f}% of 2027-2050 construction would reach LoE AR = 1, i.e. "
              f"{rs['dwellings_not_built_2027_2050']:,.0f} dwellings not built and "
              f"{rs['new_residents_housed_in_existing_dwellings']:,.0f} new residents housed in existing dwellings."]
    L += ['', '### Shapley attribution of P5 Combined (Moderate, full strength from 2027) − TL', '']
    sh = pd.DataFrame(t['shapley'])
    rows = []
    for pl in list(t['definition']['components']) + [LV.TL_FROM2027]:
        c = sh[(sh['metric'] == 'carbon_kt') & (sh['player'] == pl)].iloc[0]
        a = sh[(sh['metric'] == 'LoE_AR') & (sh['player'] == pl)].iloc[0]
        share = c['share_of_P5_moderate_from2027_minus_TL']
        rows.append([N.ADOPTION['from2027'] + ' (separate line)' if pl == LV.TL_FROM2027
                     else f"{pl} {t['definition']['components'][pl]}",
                     f"{c['reduction']:,.0f}" + ('' if pd.isna(share) else f" ({100 * share:.0f}%)"),
                     f"{a['reduction']:.3f}"])
    L += table(['player', 'carbon (kt)', 'LoE AR'], rows)
    n_ = len(t['definition']['components'])
    L += ['', f"Players TL1-TL{n_} over {2 ** n_:,} subsets, each applied at full strength from 2027 (exact rational "
          'arithmetic; the values add up to P5 Combined (Moderate) at full strength from 2027 − TL exactly; tested). '
          '"Full strength from 2027" is a separate line, not a player: P5 Combined on its adoption path minus P5 '
          'Combined at full strength from 2027.', '',
          '### Limitations of TL', '',
          '* TL combines attributes of different buildings and places (the OLF of one apartment case for every '
          'typology; each typology\'s best A1-A3 case; the lowest soil order everywhere; London\'s brownfield share '
          'nationally; the 1991 household size) that have not been observed together; it is a hyper-optimistic thought '
          'experiment, not a design, a policy or a feasible pathway.',
          '* TL1 + TL10 give every new dwelling the occupied area of the case-study minimum (about 20 m² per person); no '
          'design rule, accessibility standard or household-size variation is modelled.',
          '* TL2 and TL3 assume every released dwelling is usable where it is needed (no spatial or condition mismatch; '
          'Napiontek et al. 2025 on hibernating stock) and an immediate reallocation in 2027.',
          '* TL7 treats A5 as energy-related (an upper bound of the construction-stage saving).',
          '* As in P1-P5, the renovation carbon of the retained stock (L5, TL5) and any rebound are not modelled; '
          'static budgets.']
    return L


def levers_table(p, t=None):
    import levers as LV
    rows = LV.lever_table(p)
    L = ['# Table 1. Pathway levers and the theoretical-limit assumptions (generated by tools/pathways_methods.py '
         'from outputs/data/pathways/levers.json and outputs/data/pathways/theoretical_limit.json; do not edit by '
         'hand)', '']
    if p['run_mode'] != 'full':
        L += [f"> **{p['run_mode']}**", '']
    L += ['The Reference projection; each lever follows a normalised logistic adoption path from 2026 (observed, '
          f"unchanged) to full strength in 2035 ({LV.RAMP_BASIS}; sensitivities: full roll-out by 2030 and by 2045). "
          'One rule for every adoption window 2026 → E (W = E − 2026): midpoint 2026 + W/2, speed k = ln(81) / (2W/3), '
          '10-90% of adoption within the middle two-thirds of the window; w(2026) = 0, w(E) = 1, w = 1 after E '
          f"(by 2035: midpoint 2030.5, k = {LV.RAMP_K:.4f}; by 2030: {LV.ADOPTION_BY2030['mid']:g}, "
          f"{LV.ADOPTION_BY2030['k']:.4f}; by 2045: {LV.ADOPTION_BY2045['mid']:g}, {LV.ADOPTION_BY2045['k']:.4f}). "
          'Levers L1-L9 in four pathway families (P1 Space per person, P2 Existing stock, P3 Construction, P4 Land; P5 '
          'combines them); business-as-usual decarbonisation applies in every run; only population growth is '
          'untargeted. The typology shares stay at the Reference held mix in every run. Tags: DATA (measured), '
          'LITERATURE (cited), DECISION (author).', '']
    L += table(['item', 'pathway', 'demand band targeted', 'how it works (model terms)', 'assumption', 'Moderate',
                'Ambitious', 'source (full citation)', 'tag'],
               [[r['item'], r['pathway'], r['band'], r['how'], r['assumption'], r['moderate'], r['ambitious'],
                 r['source'], r['tag']] for r in rows])
    n = p['denser_mix_pathways_v2']['note']
    L += ['', f"**Removed lever.** {n['text']} {DENSER_MIX_VALUES}: attached share "
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


def load_levers():
    """levers.json and, when it exists, theoretical_limit.json (outputs/data/pathways/)."""
    with open(os.path.join(DATA, 'levers.json')) as f:
        p = json.load(f)
    t_path = os.path.join(DATA, 'theoretical_limit.json')
    tlim = None
    if os.path.exists(t_path):
        with open(t_path) as f:
            tlim = json.load(f)
    return p, tlim


def lines():
    """The pathways part of the methods draft as Markdown lines: no document title (the caller
    adds it; tools/methods_draft.py demotes the '##' section headings by one level)."""
    import levers as LV
    p, tlim = load_levers()
    runs = pd.read_csv(os.path.join(DATA, 'runs.csv'))
    bands = pd.read_csv(os.path.join(DATA, 'bands.csv'))
    shp = pd.read_csv(os.path.join(DATA, 'shapley_pathways.csv'))
    shl = pd.read_csv(os.path.join(DATA, 'shapley_levers.csv'))
    bc = json.load(open(os.path.join(DATA, 'backcast.json')))
    ref = runs[(runs['scenario'] == REF) & (runs['adoption'] == LV.ADOPTION_ADOPTED)
               & ~runs['l6_apartments_held'].astype(bool)].set_index('run')
    p0 = ref.loc[REF]
    e6 = p['L6']['estimator']
    note = p['denser_mix_pathways_v2']['note']
    ad = p['adoption']
    pw_rows = [f"| {P} {LV.PATHWAY_NAMES[P]} | " + ', '.join(f'{L} {LV.LEVER_NAMES[L]}' for L in N.PATHWAY_LEVERS[P])
               + ' | ' + '; '.join(LV.BAND_TARGET[L] for L in N.PATHWAY_LEVERS[P]) + ' |' for P in N.PATHWAY_LEVERS]
    L = []
    if p['run_mode'] != 'full':
        L += [f"> **{p['run_mode']}**", '']
    L += [
        'Five pathways for new residential construction in New Zealand, 2026-2050, built from nine levers in four '
        'families and applied to the Reference projection, assessed against the climate-change budgets of the '
        'planetary-boundary layer (AESA; acquired rights, AR; ability to pay, AtP). The model is unchanged: '
        '`pathways.py` re-calls `engine.forward()` with copies of the Reference inputs modified by `levers.py` '
        '(hooks: docs/HOOKS.md); no projection output is rewritten. With every lever off the run reproduces the '
        f"Reference (maximum relative difference {p['identity_max_rel_diff']:.1e}; tests/test_pathways.py). "
        'Table 1: outputs/reports/LEVERS_TABLE.md.', '',
        '## Pathways and demand bands', '',
        '| pathway | levers | demand band or quantity targeted |', '|---|---|---|'] + pw_rows + [
        f"| P5 {LV.PATHWAY_NAMES['P5']} | all nine | all of the above |", '',
        'Only population growth is untargeted by design (population is exogenous, as in Pellan et al. 2024); smaller '
        'households are targeted by L2 Household occupancy. Every run reports floor area and carbon by demand band '
        '(outputs/data/pathways/bands.csv), so the attribution by band is exact and needs no decomposition.', '',
        '**Typology mix.** ' + note['text'] + ' ' + DENSER_MIX_VALUES + ': '
        f"Moderate / Ambitious carbon {note['carbon_vs_reference_pct']['moderate']:+.2f}% / "
        f"{note['carbon_vs_reference_pct']['ambitious']:+.2f}% vs the Reference while carbon per m² rose from "
        f"{note['carbon_per_m2_kg']['REF']:.1f} to {note['carbon_per_m2_kg']['moderate']:.1f} / "
        f"{note['carbon_per_m2_kg']['ambitious']:.1f} kg CO₂e. The typology shares stay at the Reference held mix in "
        'every run (the Reference, P1-P5 and TL).', '',
        '## Conventions', '',
        '* Adoption path (all levers), one rule for every adoption window from 2026 to its end year E '
        '(W = E − 2026 years): a normalised logistic s(y) = 1 / (1 + exp(−k (y − m))) with midpoint m = 2026 + W/2 '
        'and speed k = ln(81) / (2W/3), so that s rises from 10% to 90% within the middle two-thirds of the window; '
        'w(y) = (s(y) − s(2026)) / (s(E) − s(2026)) for 2026 ≤ y ≤ E, w(2026) = 0, w(E) = 1 and w = 1 after E. '
        f"Adopted, {N.ADOPTION['by2035']}: E = 2035, m = {ad['mid']}, k = ln(81)/6 = {ad['k']:.4f}. A lever moves a "
        f"quantity from its Reference value b to its target x as b + w(y)(x − b). Basis: {LV.RAMP_BASIS}. "
        f"Sensitivities (P5): full roll-out by 2030 and by 2045.",
        '* 2026 is observed (consented floor area fixed) and identical in every run; business-as-usual '
        'decarbonisation (A1-A3 after Horup et al. 2025, A4-A5 e^(−0.01 (y − 2025)) after Resch et al. 2021) applies '
        'in every run.',
        '* Accounting as the Reference (time-resolved): carbon 2026-2050 = materials and construction (A1-A5) and '
        'soil carbon loss in the construction year + maintenance (B2, B4), 2026-2050; later B2/B4 events and all '
        'C1-C4 of the 2026-2050 cohorts are committed after 2050.', '',
        '## Levers as implemented (levers.py)', '',
        '    L1   size_t(y) = occ_t(y) + [1 − f w(y)] (size_ref_t − occ_t(y)),   occ_t(y) = S(y) · OLF_t (never below occ)',
        '    L2   S(y) = max(S_ref(y), S_ref(y) + w(y)(S_target(y) − S_ref(y))),   households = population / S',
        '    L3   v(y) = v0 + w(y)(v* − v0)',
        '    L4   join = market_excess(E_nojoin, O26, ρ, 2027, surplus, absorption a)',
        '    L5   demol(y) = demol · (1 − w(y) d);  resid(y) = resid_LR + (resid_REF(y) − resid_LR)(1 − w(y) d)',
        '    L6   A1-A3_t(y) = [1 − w(y)(1 − r)] · (A1-A3_t,2025 − R13_t(y))',
        '    L7   A4-A5_t(y) = A4-A5_t,2025 · [ref(y) + w(y)(target(y) − ref(y))],   ref(y) = e^(−0.01 (y − 2025))',
        '    L8   soil_t(y) = soil_t · (1 − w(y) x)',
        '    L9   soil-free floor area(y) = replacement(y) + w(y) · max(0, s · total(y) − replacement(y))', '',
        'S and OLF are the engine\'s; L1 uses the household size after L2. L7 targets: Moderate e^(−(ln 2/25)(y − 2025)) '
        '(half the 2025 factor in 2050), Ambitious 1 − (y − 2025)/25 (zero in 2050); A5 is treated as energy-related '
        '(an upper bound). L9: s is a share of all new floor area; the replacement floor area already carries no soil '
        'loss in the Reference, so the brownfield floor area only adds where s · total exceeds it (no double '
        'counting; tested).', '',
        '## Parameters and sources', '']
    L += table(['setting', 'value', 'basis'], LV.register(p))
    L1 = p['L1']
    L += ['', '### L1: implied new-dwelling sizes (L1 alone)', '']
    rows = []
    for t in L1['size_ref']:
        for y in LV.L1_REPORT_YEARS:
            c, s_ = LV.by_year(L1['implied']['moderate'][t], y), LV.by_year(L1['implied']['ambitious'][t], y)
            rows.append([t, y, f"{L1['size_ref'][t]:.1f}", f"{c['occupied_m2']:.1f}", f"{c['size_m2']:.1f} ({c['cut_pct']:+.1f}%)",
                         f"{s_['size_m2']:.1f} ({s_['cut_pct']:+.1f}%)"])
    L += table(['typology', 'year', 'size_ref (m²)', 'occupied S·OLF (m²)', 'Moderate (m², cut)', 'Ambitious (m², cut)'], rows)
    L2 = p['L2']
    L += ['', '### L2: household size (persons per household)', '',
          f"Moderate: the Stats NZ {L2['variant_moderate']} variant (the variant with the largest household size in every "
          f"year, identified from the paths); Ambitious: its maximum, {L2['ambitious_level']:.4f} "
          f"({L2['ambitious_level_year']}), held, reached through the adoption path. History: {L2['S_2023']:.4f} in 2023, "
          f"maximum {L2['history_max']:.4f} ({L2['history_max_year']}). Ambitious ≥ Moderate ≥ Reference in every year "
          '(asserted).', '']
    L += table(['year', 'Reference', 'Moderate', 'Ambitious'],
               [[y, f"{LV.by_year(L2['S_ref'], y):.4f}", f"{LV.by_year(L2['S']['moderate'], y):.4f}",
                 f"{LV.by_year(L2['S']['ambitious'], y):.4f}"] for y in (2026, 2030, 2035, 2040, 2050)])
    L += ['', '### L6: Harrell-Davis estimator', '',
          f"Sample: the {p['L6']['n']} independent case studies of the detached and townhouse typologies (duplicates "
          'excluded; apartments have one independent case), 2025 A1-A3 per m². Scale-free ratio x_i = A1-A3_i / pooled '
          'A1-A3 of its typology. Harrell & Davis (1982):', '',
          '    Q̂(q) = Σ_i W_i x_(i),   W_i = I_{i/n}(a, b) − I_{(i−1)/n}(a, b),   a = q(n + 1),   b = (1 − q)(n + 1)', '',
          'checked against scipy.stats.mstats.hdquantiles (≤ 1e-10). Interval: nonparametric bootstrap of the cases, '
          f"B = {p['L6']['bootstrap']['B']:,}, seed {p['L6']['bootstrap']['seed']}, percentile 95% (Efron & Tibshirani 1993).", '']
    L += table(['setting', 'q', 'r (point)', '95% CI'],
               [[N.SETTINGS[s_], f"{e6[s_]['q']:.2f}", f"{e6[s_]['r']:.4f}", f"{e6[s_]['ci_lo']:.4f}-{e6[s_]['ci_hi']:.4f}"]
                for s_ in LV.SETTINGS])
    L9 = p['L9']
    L += ['', '### L8 and L9', '',
          f"L8: x = {p['L8']['x']['moderate']} / {p['L8']['x']['ambitious']} (Moderate / Ambitious; "
          'Christoforatos, Pickering & Schipper 2026). '
          f"L9: s = {L9['s']['moderate']} / {L9['s']['ambitious']} of all new floor area (UK DLUHC; {L9['note']}). The "
          'Reference implied share (replacement floor area / all new floor area) is '
          f"{100 * L9['reference_implied_share_mean_2026_2050']:.1f}% over 2026-2050 ("
          + ', '.join(f"{y}: {100 * LV.by_year(L9['reference_implied_share'], y):.1f}%" for y in (2026, 2030, 2040, 2050))
          + ').', '',
          '## Attribution', '',
          'Shapley values (Shapley 1953; Albrecht, François & Schoors 2002) of each player for the reduction '
          'v(∅) − v(N):', '',
          '    φ_i = Σ_{S ⊆ N∖{i}} |S|! (|N| − |S| − 1)! / |N|! · [v(S) − v(S ∪ {i})]', '',
          'Players: the four pathways P1-P4 (16 subsets; main) and the nine levers (512 subsets; Extended Data); every '
          'subset is a full run; exact rational arithmetic, so Σ_i φ_i = Reference − P5 exactly (tested).', '',
          '## AESA gap', '',
          'Budgets B_AR(t), B_AtP(t) for the Reference from outputs/data/aesa/annual.csv (no lever changes '
          'population). Cumulative LoE = Σ I(t) / Σ B(t) over 2026-2050; back-cast and solution space as in the '
          'planetary-boundary methods (k on the 2027-2050 cohorts, brentq; the plane bilinear in the cuts).', '',
          '## Results (Reference)', '']
    rows = []
    for name in [REF] + [f'{Lv}-{s_}' for s_ in LV.SETTINGS for Lv in LV.LEVERS] + \
            [f'{P}-{s_}' for s_ in LV.SETTINGS for P in ('P1', 'P2', 'P3', 'P4', 'P5')]:
        r = ref.loc[name]
        rows.append([N.run_label(name), f"{r['floor_area_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}",
                     f"{r['committed_lower_kt']:,.0f}-{r['committed_upper_kt']:,.0f}", f"{r['LoE_AR']:.2f}",
                     f"{r['LoE_AtP']:.1f}", f"{r['delta_carbon_kt_vs_reference_pct']:+.1f}%", f"{r['dwellings_built']:,.0f}",
                     f"{r['mean_household_size_2050']:.3f}", f"{100 * r['brownfield_share']:.1f}%",
                     f"{100 * r['implied_vacancy_min']:.2f}%"])
    L += table(['run', 'floor area (Mm²)', 'carbon 2026-2050 (kt)', 'committed after 2050 (kt)', 'LoE AR', 'LoE AtP',
                'carbon vs Reference', 'dwellings built', 'household size 2050', 'soil-free share', 'min implied vacancy'],
               rows)
    L += ['', '### Floor area change by demand band, Moderate (Mm², vs the Reference; in-scope definition)', '']
    bd = bands[(bands['scenario'] == REF) & (bands['definition'] == 'in_scope')]
    rows = []
    for b in dict.fromkeys(bd['band']):
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
        for s_ in LV.SETTINGS:
            for metric, fmt in (('carbon_kt', '{:,.0f}'), ('LoE_AR', '{:.3f}')):
                x = shp[(shp['setting'] == s_) & (shp['metric'] == metric) & (shp['player'] == P)].iloc[0]
                line.append(fmt.format(x['reduction']) + (f" ({100 * x['share_of_reference_minus_P5']:.0f}%)"
                                                          if metric == 'carbon_kt' else ''))
        srows.append(line)
    L += table(['pathway', 'Moderate: carbon (kt)', 'Moderate: LoE AR', 'Ambitious: carbon (kt)', 'Ambitious: LoE AR'],
               srows)
    L += ['', '### Shapley attribution of Reference − P5 (levers)', '']
    srows = []
    for Lv in LV.LEVERS:
        line = [f'{Lv} {LV.LEVER_NAMES[Lv]}']
        for s_ in LV.SETTINGS:
            x = shl[(shl['setting'] == s_) & (shl['metric'] == 'carbon_kt') & (shl['player'] == Lv)].iloc[0]
            line.append(f"{x['reduction']:,.0f} ({100 * x['share_of_reference_minus_P5']:.0f}%)")
        srows.append(line)
    L += table(['lever', 'Moderate: carbon (kt)', 'Ambitious: carbon (kt)'], srows)
    keys = ['P5-moderate', 'P5-ambitious', REF]
    L += ['', '### Back-cast', '',
          f"Cumulative budgets 2026-2050: AR {bc['B_AR_kt']:,.0f} kt, AtP {bc['B_AtP_kt']:,.0f} kt.", '']
    L += table([''] + [N.run_label(k) for k in keys],
               [['LoE AR at k = 1'] + [f"{bc[k]['LoE_AR_at_k1']:.3f}" for k in keys],
                ['k for cumulative LoE AR = 1'] + [f"{bc[k]['k_AR']:.4f}" for k in keys],
                ['cut of 2027-2050 construction (1 − k)'] + [f"{100 * bc[k]['cut_AR']:.1f}%" for k in keys],
                ['minimum LoE AtP (k = 0)'] + [f"{bc[k]['LoE_AtP_min_k0']:.3f}" for k in keys]])
    L += ['', '### Replacement variants, adoption paths and L6 sensitivities', '']
    erows = []
    for scen in ('LOW', REF, 'HIGH'):
        for name in (scen, 'P5-moderate', 'P5-ambitious', 'P5-moderate-by2030', 'P5-ambitious-by2030',
                     'P5-moderate-by2045', 'P5-ambitious-by2045'):
            r = runs[(runs['scenario'] == scen) & (runs['run'] == name)].iloc[0]
            erows.append([N.SCENARIOS[scen], N.run_label(name), f"{r['floor_area_Mm2']:.2f}", f"{r['carbon_kt']:,.0f}",
                          f"{r['LoE_AR']:.2f}", f"{r['LoE_AtP']:.1f}", f"{r['delta_carbon_kt_vs_reference_pct']:+.1f}%"])
    for name in ('P3-moderate-apartments-held', 'P3-ambitious-apartments-held', 'P5-moderate-apartments-held',
                 'P5-ambitious-apartments-held'):
        r = runs[(runs['scenario'] == REF) & (runs['run'] == name)].iloc[0]
        erows.append([N.SCENARIOS[REF], N.run_label(name) + ' (L6)', f"{r['floor_area_Mm2']:.2f}",
                      f"{r['carbon_kt']:,.0f}", f"{r['LoE_AR']:.2f}", f"{r['LoE_AtP']:.1f}",
                      f"{r['delta_carbon_kt_vs_reference_pct']:+.1f}%"])
    L += table(['projection variant', 'run', 'floor area (Mm²)', 'carbon (kt)', 'LoE AR', 'LoE AtP',
                'carbon vs the variant without levers'], erows)
    L += ['', '## Checks (tests/test_pathways.py, tests/test_regression_model_v2_1.py)', '',
          '* No lever = the Reference (≤ 1e-9 relative); each of L1-L9 at zero strength = the Reference; 2026 '
          'identical in every run; lever functions never modify their inputs.',
          '* L1 sizes ≥ occupied area S·OLF; implied vacancy ≥ '
          f"{100 * p['L3']['floor']:.1f}%; no negative dwellings built; no household decline in any pathway run.",
          '* L2 ordering (Ambitious ≥ Moderate ≥ Reference every year); L9 soil-free share ≥ the Reference share and = s '
          'where the target binds; Harrell-Davis = scipy; pathway, lever and TL Shapley efficiency exact; demand bands '
          'add up to the totals; back-cast LoE AR = 1.',
          '* Numerical locks: every number outside the pathway domain is unchanged to 1e-12 (tests/'
          'test_regression_model_v1.py, tests/test_regression_model_v2.py); every number of the pathway domain is '
          'locked by tests/regression_model_v2_1.json.', '',
          '## Limitations', '',
          '* L5 is an upper bound: the carbon of renovating the buildings kept in use is not modelled (Napiontek et '
          'al. 2025).',
          f"* L6 rests on {p['L6']['n']} case studies; the Ambitious interval is wide ({e6['ambitious']['ci_lo']:.2f}-"
          f"{e6['ambitious']['ci_hi']:.2f}); the ratio is applied to apartments too (held at r = 1 as a sensitivity).",
          '* L2 assumes household formation can follow a larger household size (co-living, multigenerational '
          'households) without modelling its drivers; the floor S ≥ S_ref means the lever never adds households.',
          '* L7 treats A5 as energy-related (an upper bound). L9 transfers an English share of brownfield floor area; '
          'no New Zealand statistic exists.',
          f"* L3 starts from the Reference, in which {vacancy_sentence()}; its targets absorb the post-2018 excess "
          'vacancy.',
          '* Levers are parameter changes on the Reference model; no behavioural, market or rebound response is '
          'modelled; interactions are those of the model (attributed by Shapley values).',
          '* Omitted: ' + '; '.join(f'{a} ({b})' for a, b in LV.OMITTED) + '.', '',
          ] + (tl_methods(tlim, runs) if tlim is not None else []) + ['', '## Sources', ''] + [f'* {v}' for v in p['sources'].values()]
    return L


def main():
    """LEVERS_TABLE.md (the pathways part of the methods draft is written by tools/methods_draft.py)."""
    levers_table(*load_levers())
    print('pathways_methods: outputs/reports/LEVERS_TABLE.md')


def sections():
    """The Pathways section of outputs/reports/ASSUMPTIONS.md (tools/assumptions.update_pathways_section;
    it replaces only its own section and is idempotent)."""
    import assumptions
    assumptions.update_pathways_section()


if __name__ == '__main__':
    main()
    if '--sections' in sys.argv:
        sections()
