"""Methods draft, part 4 (MODEL v3.2.0): the attribution principle and system boundary of the (unchanged) v3.0
emissions accounting, the release accounting (A2), the zero-year soil guard, the history split (A3), the Reference
replacement wording, the completion-rate distribution and the check rows (A4, A5). Every number is read from the data
files (outputs/data/; settings from projection.py and engine.py); tools/methods.py assembles it.
Adapted from the v3.1.0 tools/accounting_methods.py with the emissions-accounting change (withdrawn) removed.
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine  # noqa: E402
import layout  # noqa: E402
import pathways as PW  # noqa: E402
import projection  # noqa: E402


def _js(rel):
    with open(layout.data(rel, frozen=False)) as f:
        return json.load(f)


def lines():
    sc = _js('baseline/scenarios.json')['meta']
    hu = _js('baseline/history_unexplained.json')
    lv = _js('pathways/levers.json')
    runs = pd.read_csv(layout.data('pathways/runs.csv', frozen=False))
    ref = runs[runs['scenario'] == 'REF'].set_index('run')
    tl, fast = ref.loc['TL'], ref.loc[PW.TL_REOCCUPATION_FAST]
    L = ['### Attribution principle and system boundary (unchanged from MODEL v3.0.0)', '',
         'Emissions fully determined at construction (A1-A5, soil carbon loss) are attributed to the construction '
         'year; emissions depending on later decisions or technology (B, C1-C4) are time-resolved (in-window counted, '
         'remainder committed). System boundary: new residential construction, identical for the AR/AtP base '
         '(2016-2025) and the projection (2026-2050). Demand uses the existing stock (vacancy, overbuild absorption, '
         're-occupation, replacement); emissions of the existing stock are outside scope on both sides. The committed '
         'emissions of an investment decision are attributed to the decision (Davis & Socolow 2014, Environ. Res. Lett. '
         '9, 084018 [verify]).', '',
         '### Release accounting (bands.py; pathways.run)', '',
         'Positive demand bands are always gross need: population growth, smaller households, extra space, vacancy '
         '(the gross allowance: on new households and any vacancy-rate rise), the 2026 overbuild, demolition '
         'replacement and the recent replacement surge. Every release is its own negative band, booked in the year it '
         "is used: 'Overbuild absorbed' (the payback, taken on the gross need), 'Unconsented additions' (the calibrated "
         "residual of the census identity), 'Vacancy released' (a vacancy-rate fall in a run without any lever at its "
         "theoretical limit: used in the year it occurs, capped at that year's gross need, the rest carried forward) "
         "and 'Released dwellings (TL)' (the re-occupation pool). No release is netted inside a positive band and no "
         'band is rescaled: retirement-village units are a constant share of every dwelling built, so each in-scope '
         'band is its gross floor area times (1 - that share), exactly. If gross need minus usable releases is negative '
         'in a year, nothing is built and the unusable amount is carried forward against the next years: released '
         'dwellings remain available later, as they do in the theoretical-limit re-occupation pool. Whatever is still '
         "unusable in 2050 is booked in 2050 against its release band and as 'Surplus kept vacant (2050)', so the bands "
         'add up to the total in every year (checked to 1e-9). In every theoretical-limit-family run (TL, the TL steps '
         'of both waterfalls, every TL Shapley subset) the re-occupation pool holds every dwelling release present in '
         'the run (a vacancy-rate fall at any level, a household-size fall), with the constant-share rule, the '
         'availability constraint and attribution in proportion to the release of each source. The Reference, every '
         'lever and pathway run and TL are unchanged from MODEL v3.0.0 (tested to 1e-9); the TL waterfall steps before '
         'TL4 and the TL1-TL9 Shapley values from P5 Moderate change, and in the pathway Monte Carlo the draws with a '
         'negative-gross year (docs/CHANGELOG_v3_2.md).', '',
         '### Zero-year guard (engine.forward)', '',
         f'A year whose built floor area is below {engine.BUILT_ZERO_TOL_M2:g} m2 is a year in which nothing is built: '
         'its floor area, soil-bearing share and soil carbon are set to 0. The soil-bearing share is clipped to [0, 1] '
         'in every run. Without the guard the share 1 - soil-free / total is a ratio of floating-point noise and the '
         'soil carbon of a year without construction is non-zero (a MODEL v3.0.0 defect, found in pathway Monte Carlo '
         'draws; no deterministic run is affected).', '',
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
         f"{projection.COMPLETION_RATE_BAND[1]:.2f}; Jones, Greenaway-McGrevy & Crow 2024 [verify]) and the median at the "
         f"adopted {projection.COMPLETION_RATE:.2f}, which a two-piece distribution places at its join (Wallis 2014, "
         'Statistical Science 29(1)); the asymmetric bounds are kept without assuming a shape between them.', '',
         '### Check and sensitivity rows', '',
         f"TL with re-occupation as fast as demand allows (deterministic sensitivity row): {fast['carbon_kt']:,.1f} kt, "
         f"LoE AR {fast['LoE_AR']:.3f} (TL: {tl['carbon_kt']:,.1f} kt, LoE AR {tl['LoE_AR']:.3f}).", '',
         f"L6 with the apartment case A_1 (n = {lv['L6']['check_with_A_1']['n']}): r = "
         f"{lv['L6']['check_with_A_1']['r']:.3f} against the adopted {lv['L6']['check_with_A_1']['adopted_r']:.3f} "
         f"(n = {lv['L6']['check_with_A_1']['adopted_n']}); report only (A_1's ratio to its pooled value is "
         f"{lv['L6']['check_with_A_1']['A_1_ratio']:.4f} by construction)."]
    return L
