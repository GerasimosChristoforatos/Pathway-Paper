"""Methods draft, part 4 (MODEL v3.2.0): the attribution principle and system boundary of the (unchanged) v3.0
emissions accounting, the release accounting (A2), the zero-year soil guard, the history split (A3), the Reference
replacement wording, the completion-rate distribution and the check rows (A4, A5). Every number is read from the data
files (outputs/data/; settings from projection.py and engine.py); tools/methods.py assembles it.
Adapted from the v3.1.0 tools/accounting_methods.py with the emissions-accounting change (withdrawn) removed.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine  # noqa: E402
import MonteCarlo as MC  # noqa: E402
import layout  # noqa: E402
import pathways as PW  # noqa: E402
import projection  # noqa: E402


def _js(rel):
    with open(layout.data(rel, frozen=False)) as f:
        return json.load(f)


def lines():
    sc = _js('baseline/scenarios.json')['meta']
    tr = _js('baseline/projection.json')['replacement_trend']
    # mean excess of net replacement over the long-run rate 2026-2050 (percentage points): the Reference's exponential
    # fade (half-life 10 yr) and a linear path from the 2025 value to the long-run rate in 2050
    d0 = sc['recent_pct'] - sc['long_run_pct']
    k = np.arange(1, 26)
    ex_exp = float(np.mean(d0 * 0.5 ** (k / projection.REPLACEMENT_HALF_LIFE)))
    ex_lin = float(np.mean(d0 * (1.0 - k / 25.0)))
    hu = _js('baseline/history_unexplained.json')
    ob = _js('baseline/overbuild_2026.json')
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
         'lever and pathway run and TL are unchanged from MODEL v3.0.0 (tested to 1e-9); the TL waterfall steps and the '
         'TL1-TL9 Shapley values from the Moderate Pathway change (MODEL v3.2.0), and in the pathway Monte Carlo the draws with a '
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
         '### Replacement in the Reference and its variants (MODEL v3.3.0)', '',
         f"Net replacement fades from the 2018-23 census rate ({sc['recent_pct']:.2f}%) to the long-run 1991-2023 rate "
         f"({sc['long_run_pct']:.2f}%), half-life {projection.REPLACEMENT_HALF_LIFE:g} yr; BRANZ demolition "
         f"({sc['demolition_rate_pct']:.3f}%) only splits the net rate into the demolition, surge and "
         'unconsented-additions bands. The half-life is not identifiable from the census record (seven censuses, six '
         f"interval rates), so the Monte Carlo samples it, U({MC.HALF_LIFE_RANGE[0]:g}, {MC.HALF_LIFE_RANGE[1]:g}) yr, "
         'with the deterministic 10 yr as its median (it acts in the Reference variant only). The functional form '
         f"matters little for the cumulative surge: the mean excess over the long-run rate 2026-2050 is {ex_exp:.3f} pp "
         f"with the 10-yr half-life and {ex_lin:.3f} pp for a linear path that reaches the long-run rate in 2050.", '',
         f"Very High replacement (trend continues; a sensitivity variant): the {tr['n']} census-interval rates "
         f"{tr['window'][0]}-{tr['window'][1]} fitted by weighted least squares on the mean of each interval's years "
         f"(weights = interval length), rate = {tr['a']:.6f} + {tr['b']:.4e} x year, extrapolated 2026-2050: "
         f"{100 * tr['rate_2026']:.3f}% in 2026 and {100 * tr['rate_2050']:.3f}% in 2050. It is not adopted as the "
         'Reference: six interval rates (seven censuses), one of them negative (1996-2001), the 2013-2018 census '
         'definition break (empty / residents-away dwellings), and the unbounded extrapolation of a policy-driven '
         'wave.', '',
         '### Completion rate in the Monte Carlo', '',
         f"Uniform on [{projection.COMPLETION_RATE_BAND[0]:.2f}, {projection.COMPLETION_RATE_BAND[1]:.2f}] (MODEL v4.0.0). "
         f"The bounds are published completion milestones for Auckland consents (Jones, Greenaway-McGrevy & Crow 2025, "
         'Policy Quarterly 21(1), 63-68, footnote 12): 93% of 2018-2019 consents had a final inspection by July 2024 '
         '(lower bound of eventual completion) and more than 95% of 2018-2021 consents had a first inspection (upper '
         'bound; the article gives no point value, so the edge 0.96 is a stated judgement). The deterministic central '
         f"value {projection.COMPLETION_RATE:.3f} is their midpoint, and so the median of the Monte Carlo input. No shape "
         'inside the band is identified, hence uniform. Limitation: Auckland evidence applied nationally.', '',
         '### Consent-to-completion lag and pipeline years (MODEL v4.0.0)', '',
         f"Completions in month m = {projection.COMPLETION_RATE:.3f} x consents in month m - L, L = "
         f"{projection.COMPLETION_LAG_MONTHS} months, aggregated to calendar years. L is the midpoint of the median "
         'time to dwelling completion of 1.27-1.53 yr for Auckland consents as of July 2024 (Jones, Greenaway-McGrevy '
         '& Crow 2025, citing Greenaway-McGrevy & Jones 2023), consistent with the Stats NZ Experimental building '
         'indicators (dwelling-weighted median 455 days from consent to final inspection for December 2020 quarter '
         'consents, 533 days for September 2022 quarter consents). The same lag applies everywhere consents become '
         'dwellings: the stock identity, the census-interval net replacement rates (consents lagged L/12 years before '
         'each census date), the dwelling-size and typology-mix windows, historical floor area and the AR / AtP base, '
         f"and the projection start. Projection years whose twelve lagged months are all observed ({', '.join(map(str, ob.get('pipeline_years') or []))}) "
         'are pipeline years: their building is observed in every run (the market excess over the requirement), and '
         'the excess fades from the next year at the persistence rho re-estimated on the lagged history. Before April '
         '1990 the typology columns of the consent file are empty; those months are split by the April 1990 - March '
         '1991 typology ratios of all dwellings (they enter only the 1991 completions, which are used in the cumulative '
         'floor area from 1991 and nowhere else). Limitations: one fixed lag (no distribution of build times), Auckland '
         'evidence applied nationally. The rolling-origin hindcast of the census dwelling-count identity is not worse '
         'at L = 17 than at L = 0 (outputs/data/baseline/completion_lag_hindcast.csv).', '',
         '### Theoretical limit: constraints at Level 4 (MODEL v4.0.0)', '',
         f"Level 4 is the definitional limit of each lever, reached along the common adoption window, except household "
         f"size (TL1): its level ({lv['L1']['tl']:.4f}, the {lv['L1']['tl_year']} census maximum) is approached no "
         f"faster than the fastest change of household size observed between consecutive censuses 1991-2023 "
         f"({lv['L1']['tl_speed']['rate']:.5f} per year, {lv['L1']['tl_speed']['interval'][0]}-"
         f"{lv['L1']['tl_speed']['interval'][1]}; census-benchmarked households): S_TL(t) = min(S_ref(2026) + r (t - "
         f"2026), level), never below the Ambitious path. The level is reached in "
         f"{lv['L1']['tl_speed']['level_reached']:.1f}. Household size is a population-level outcome of age "
         'structure, partnering and housing costs; the speed limit keeps the theoretical limit within changes the New '
         'Zealand census record has shown. The instant-TL row keeps its definition (every level from 2027). In every '
         "theoretical-limit-family run the Reference's overbuild surplus (the positive market excess of the pipeline "
         'years and of the fading gap) enters the re-occupation pool with the TL1 / TL2 releases (constant share of '
         "each year's positive need, availability constraint, carry-forward); the re-occupied overbuild is booked in "
         "'Overbuild absorbed'. Releases of an observed (pipeline) year enter the pool in the first unobserved year.", '',
         '### Household-size projection (MODEL v4.0.0 note)', '',
         'Household size follows the Stats NZ 2018-base household projection shape (Medium variant), rebased on the '
         '2023 census; it is to be replaced by the 2023-base household projections when published. Sensitivities: '
         'the Stats NZ Low / High variants and the 2018-2023 census pace continued linearly from 2023, for the '
         'Reference, the Moderate / Ambitious Pathway and TL (sensitivity/household_size.csv).', '',
         '### Check and sensitivity rows', '',
         f"TL with re-occupation as fast as demand allows (deterministic sensitivity row): {fast['carbon_kt']:,.1f} kt, "
         f"LoE AR {fast['LoE_AR']:.3f} (TL: {tl['carbon_kt']:,.1f} kt, LoE AR {tl['LoE_AR']:.3f}).", '',
         f"L8 with the apartment case A_1 (n = {lv['L8']['check_with_A_1']['n']}): r = "
         f"{lv['L8']['check_with_A_1']['r']:.3f} against the adopted {lv['L8']['check_with_A_1']['adopted_r']:.3f} "
         f"(n = {lv['L8']['check_with_A_1']['adopted_n']}); report only (A_1's ratio to its pooled value is "
         f"{lv['L8']['check_with_A_1']['A_1_ratio']:.4f} by construction)."]
    return L
