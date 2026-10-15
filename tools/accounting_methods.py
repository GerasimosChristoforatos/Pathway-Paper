"""Methods draft, part 4 (MODEL v3.1.0): emissions accounting (A1), release accounting (A2), the history split (A3),
the Reference replacement wording and the completion-rate distribution. Every number is read from the data files
(outputs/data/; settings from projection.py, inventory.py and MonteCarlo.py); tools/methods.py assembles it.
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import inventory as INV  # noqa: E402
import layout  # noqa: E402
import projection  # noqa: E402


def _js(rel):
    with open(layout.data(rel, frozen=False)) as f:
        return json.load(f)


def lines():
    acc = pd.read_csv(layout.data('sensitivity/accounting_rules.csv', frozen=False)).set_index('accounting')
    pb = _js('aesa/results.json')['components']
    sc = _js('baseline/scenarios.json')['meta']
    hu = _js('baseline/history_unexplained.json')
    lv = _js('pathways/levers.json')
    rule = projection.ACCOUNTING
    a = acc.loc[rule]
    cov = pb.get('soil_tail_coverage', {})
    L = ['### Emissions accounting (ACCOUNTING; inventory.py)', '',
         f"Adopted rule: **{rule}**. Every window counts all emissions occurring in it from residential construction "
         f"since {INV.B_SCOPE_START}, identically for the acquired-rights (AR) base window 2016-2025 and the projection "
         f"2026-2050 (every run and every Monte Carlo draw): the upfront emissions (A1-A5) of the window's own "
         f"construction; the soil carbon lost on converted land, emitted linearly over {INV.SOIL_OXIDATION_YEARS} years "
         "after conversion (IPCC 2006 Guidelines, Vol. 4, Ch. 2: default transition period D = 20 years), including the "
         "tails of earlier conversions; and the replacements and repaints (B2, B4) of every cohort since "
         f"{INV.B_SCOPE_START} that occur in the window. The pre-{INV.B_SCOPE_START} stock is out of scope on both sides "
         "(its soil and its maintenance are counted in neither the base nor the projection).", '',
         'Why this rule: the AR share is taken against global annual emissions, so the sector is measured as an annual '
         'emissions flow in both the base and the projection; counting in each window the emissions that occur in it, '
         'from the same stock in scope, keeps the base and the projection on one definition.', '',
         'In the projection the emissions of activity before 2026 (soil tails of the 2007-2025 conversions occurring in '
         '2026-2044; replacements and repaints of the 1992-2025 cohorts occurring in 2026-2050, on the run\'s '
         'decarbonisation paths) are the band **Legacy (pre-2026 activity)**: identical in every run (checked), so no '
         'lever can reduce it, and pathway changes exclude nothing. The soil of 2026-2050 conversions oxidised after '
         "2050 is a committed component, 'Soil, after 2050', reported separately from the B2/B4 and C1-C4 range. "
         'In the Monte Carlo the legacy soil is fixed (observed history; soil factors are not drawn) and the legacy '
         'B2/B4 follows each draw\'s case-study event profiles (the bootstrap of the carbon factors), on the central '
         'history, as the AR base of each draw does.', '',
         "Coverage: the soil tails of a window starting in year y need the conversions from y - 19; the adopted window "
         f"(2016 start) needs {cov.get('2016_2025', {}).get('first_conversion_needed', 1997)}, inside the history in "
         'scope. The base-window sensitivity rows use the same rule; a window whose tails reach before '
         f'{INV.B_SCOPE_START} (20-year and full windows) is flagged as partial (aesa/sensitivity.csv).', '',
         "Sensitivities: **instant** (soil at conversion; B2/B4 of each window's own cohorts; the rule of MODEL v3.0.0) "
         "and **cohort_window** (soil oxidised over 20 years but only each window's own cohorts, on both sides). "
         "cohort_window is deterministic only and rejected: the 10-year base and the 25-year projection windows capture "
         'different shares of slow-release emissions, so the two sides are not on one definition.', '',
         '| | inventory | instant | cohort_window |', '|---|---|---|---|']

    def row(label, col, fmt='{:,.0f}'):
        return f"| {label} | " + ' | '.join(fmt.format(acc.loc[r, col]) if pd.notna(acc.loc[r, col]) else 'n/a'
                                            for r in INV.RULES) + ' |'
    L += [row('AR base 2016-2025 (kt/yr)', 'AR_base_kt_per_yr'),
          row('  of which upfront A1-A5', 'AR_base_upfront_kt_per_yr'),
          row('  of which soil', 'AR_base_soil_kt_per_yr'),
          row('  of which B2/B4', 'AR_base_b2b4_kt_per_yr'),
          row('AR budget 2026-2050 (kt)', 'AR_budget_kt_2026_2050'),
          row('AtP budget 2026-2050 (kt)', 'AtP_budget_kt_2026_2050'),
          row('Reference carbon 2026-2050 (kt)', 'reference_carbon_kt'),
          row('  upfront A1-A5', 'reference_upfront_kt'),
          row('  soil (emitted in the window)', 'reference_soil_kt'),
          row('  B2/B4 of the new cohorts', 'reference_b2b4_kt'),
          row('  legacy (pre-2026 activity)', 'reference_legacy_kt'),
          row('Soil, after 2050 (kt, committed)', 'soil_after_2050_kt'),
          row('LoE AR, Reference', 'REF_LoE_AR', '{:.2f}'),
          row('LoE AR, P5 Moderate', 'P5_moderate_LoE_AR', '{:.2f}'),
          row('LoE AR, P5 Ambitious', 'P5_ambitious_LoE_AR', '{:.2f}'),
          row('LoE AR, TL', 'TL_LoE_AR', '{:.2f}'),
          row('LoE AtP, Reference', 'REF_LoE_AtP', '{:.1f}'),
          row('LoE AtP, TL', 'TL_LoE_AtP', '{:.2f}'),
          row('Monte Carlo share of draws with TL within AR', 'MC_share_TL_within_AR', '{:.3f}'), '']
    L += [f"Under the adopted rule the legacy alone is {a['reference_legacy_kt']:,.0f} kt, "
          f"{a['reference_legacy_kt'] / a['AR_budget_kt_2026_2050']:.2f} times the AR budget 2026-2050 "
          f"({a['AR_budget_kt_2026_2050']:,.0f} kt): no construction pathway 2026-2050 can bring the cumulative LoE AR "
          'to 1 (Fig6: the lowest LoE AR on the plane, at a 100% cut of 2027-2050 construction, includes the 2026 cohort '
          'and the legacy).', '',
          '### Release accounting (bands.py; pathways.run)', '',
          'Positive demand bands are always gross need: population growth, smaller households, extra space, vacancy '
          '(the gross allowance: on new households and any vacancy-rate rise), the 2026 overbuild, demolition '
          'replacement and the recent replacement surge. Every release is its own negative band, booked in the year it '
          "is used: 'Overbuild absorbed' (the payback), 'Unconsented additions' (the calibrated residual of the census "
          "identity), 'Vacancy released' (a vacancy-rate fall in a run without any lever at its theoretical limit: used "
          "in the year it occurs, capped at that year's gross need, the rest carried forward) and 'Released dwellings "
          "(TL)' (the re-occupation pool). No release is netted inside a positive band and no band is rescaled to fit a "
          'floor or a cap: retirement-village units are a constant share of every dwelling built, so each in-scope band '
          'is its gross floor area times (1 - that share), exactly. If gross need minus usable releases is negative in a '
          'year, nothing is built and the unusable amount is carried forward; whatever is still unusable in 2050 is '
          "booked in 2050 against its release band and as 'Surplus kept vacant (2050)', so the bands add up to the total "
          'in every year (checked to 1e-9). In every theoretical-limit-family run (TL, the TL steps of both waterfalls, '
          'every TL Shapley subset) the re-occupation pool holds every dwelling release present in the run (a '
          'vacancy-rate fall at any level, a household-size fall), with the constant-share rule, the availability '
          'constraint and attribution in proportion to the release of each source. With ACCOUNTING instant this '
          'reproduces every Reference, lever, pathway and TL total of MODEL v3.0.0 exactly; only the TL waterfall steps '
          'before TL4 and the TL1-TL9 Shapley values from P5 Moderate change (docs/CHANGELOG_v3.md).', '',
          '### History by census interval (validation.history_bands)', '',
          'The residual band of the history is split into the census-measured net replacement (the interval rate of the '
          'census dwelling-count identity x the previous year\'s stock x the year\'s dwelling size; it may be negative, '
          'e.g. 1996-2001), the retirement-village units (negative, out of scope) and the unexplained building (the '
          'remainder to the observed in-scope floor area built; it may be negative, e.g. 2013-2018). The bands add up '
          'to the observed floor area built in every interval (checked to 1e-9). Over 1992-2025 the unexplained '
          f"building sums to {hu['unexplained_dwellings_1992_2025']:,.0f} dwellings "
          f"({100 * hu['unexplained_share_of_built']:+.2f}% of the {hu['dwellings_built_1992_2025']:,.0f} built); the "
          'floor-area remainder equals the unexplained dwellings of the stock identity x the dwelling size '
          f"(difference {hu['difference_Mm2']:.1e} Mm²).", '',
          '### Replacement in the Reference', '',
          f"Net replacement fades from the 2018-23 census rate ({sc['recent_pct']:.2f}%) to the long-run 1991-2023 rate "
          f"({sc['long_run_pct']:.2f}%), half-life {projection.REPLACEMENT_HALF_LIFE:g} yr; BRANZ demolition "
          f"({sc['demolition_rate_pct']:.3f}%) only splits the net rate into the demolition, surge and "
          'unconsented-additions bands.', '',
          '### Completion rate in the Monte Carlo', '',
          f"Two-piece uniform on [{projection.COMPLETION_RATE_BAND[0]:.2f}, {projection.COMPLETION_RATE:.2f}] and "
          f"[{projection.COMPLETION_RATE:.2f}, {projection.COMPLETION_RATE_BAND[1]:.2f}], probability 1/2 on each piece: "
          f"the bounds of the observed completion rate ({projection.COMPLETION_RATE_BAND[0]:.2f}, "
          f"{projection.COMPLETION_RATE_BAND[1]:.2f}; Jones, Greenaway-McGrevy & Crow 2024) and the median at the adopted "
          f"{projection.COMPLETION_RATE:.2f}, which a two-piece distribution places at its join (Wallis 2014, Statistical "
          'Science 29(1)); the asymmetric bounds are kept without assuming a shape between them.', '',
          '### Check rows', '',
          f"L6 with the apartment case A_1 (n = {lv['L6']['check_with_A_1']['n']}): r = "
          f"{lv['L6']['check_with_A_1']['r']:.3f} against the adopted {lv['L6']['check_with_A_1']['adopted_r']:.3f} "
          f"(n = {lv['L6']['check_with_A_1']['adopted_n']}); report only (A_1's ratio to its pooled value is "
          f"{lv['L6']['check_with_A_1']['A_1_ratio']:.4f} by construction)."]
    return L
