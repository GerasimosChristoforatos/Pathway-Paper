"""Age-standardised household size from Stats NZ living-arrangement propensities (the TL1 diagnostic and the
"TL1 age-standardised" sensitivity, MODEL v4.7.0).

Data (unmodified, data/raw, MANIFEST.csv): POPPR_FHH_008 (people by living-arrangement type and age group, 2023 base
year and the 2028-2048 projections, Low / Medium / High x propensity A / B) and POPPR_FHH_010 (households by type).
The repository holds living arrangements by age for the 2023 base year only (no earlier census year), so the
"highest observed propensity of living with others" is the 2023 propensity; Stats NZ propensity B (living-arrangement
propensities change, modelled on the 2001-2023 censuses) is the second, projected, bound.

Method (headship rates by age group a: 0-14, 15-39, 40-64, 65+):
    h_a = [one-person + f (couple partners / 2 + two-parent partners / 2 + one-parent parents) + g other] / people_a
  f (households per family unit) and g (households per person in other living arrangements) are calibrated so that
  the 2023 rates reproduce the Stats NZ 2023 family and other-multi-person households; one-person people equal
  one-person households. S(y) = sum_a people_a(y) / sum_a h_a people_a(y) on a projection's age structure.
  'S_2023' applies the 2023 rates; 'S_min_2023_or_B' the lower headship of 2023 and of the same variant's propensity
  B projection in that year, by age group (more shared living in every age group). The ratio of a path to S_2023
  (the method's own propensity-A equivalent, so the aggregation to four age groups cancels) scales the model's
  rebased Reference household size (levers.py TL1; pathways.py, pathways_mc.py).
Check (tests/test_household_headship.py): S_2023 reproduces the Stats NZ Medium A household size (people in
households / households, data/derived/households_proj_2023base.csv) to within 0.025 at every knot. The largest
deviations are 0.022 (Medium, 0.85%, 2033), 0.024 (Low) and 0.021 (High); they come from the four broad age groups the table provides (sex-specific rates give
the same deviation). The v4.7 audit (draft PR 29, not merged) stated "within 0.02", which was rounded down. The scaling of
the model path uses the ratio to S_2023, the method's own propensity-A equivalent, so this aggregation bias cancels.
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'data', 'raw')
AGES = ('0-14 years', '15-39 years', '40-64 years', '65 years and over')
LAT = {'one': 'Person in one-person household', 'cpl': 'Partner in couple-without-children family',
       'two': 'Partner/parent in two-parent family', 'opp': 'Parent in one-parent family',
       'oth': 'Other living arrangement types', 'tot': 'Total people'}
KNOTS = (2023, 2028, 2033, 2038, 2043, 2048)
CHECK_TOL = 0.025         # S_2023 against the Stats NZ household size of the same variant (A), at every knot


def load():
    """(people by projection, year, age group and living arrangement; households by projection, year and type)."""
    p = pd.read_csv(os.path.join(RAW, 'POPPR_FHH_008.csv'))
    p = p[p['Sex'] == 'Total people'].drop(columns=['Observation value']).rename(
        columns={'Year at 30 June': 'y', 'Living arrangement type': 'lat', 'OBS_VALUE': 'v', 'Age': 'age'})
    h = pd.read_csv(os.path.join(RAW, 'POPPR_FHH_010.csv')).drop(columns=['Observation value']).rename(
        columns={'Year at 30 June': 'y', 'OBS_VALUE': 'v'})
    return p, h


def _people(p, proj, y):
    t = p[(p['Projection'] == proj) & (p['y'] == y)].pivot_table(index='age', columns='lat', values='v')
    return t.loc[list(AGES)]


def _households(h, proj, y, measure):
    return float(h[(h['Projection'] == proj) & (h['y'] == y) & (h['Measure'] == measure)]['v'].iloc[0])


def calibration(p, h):
    """(f, g): households per family unit and per person in other living arrangements, from the 2023 base year."""
    P = _people(p, 'Medium A', 2023)
    fam_units = P[LAT['cpl']].sum() / 2 + P[LAT['two']].sum() / 2 + P[LAT['opp']].sum()
    f = _households(h, 'Medium A', 2023, 'Family households') / fam_units
    g = _households(h, 'Medium A', 2023, 'Other multi-person households') / P[LAT['oth']].sum()
    one = P[LAT['one']].sum() / _households(h, 'Medium A', 2023, 'One-person households')
    if abs(one - 1.0) > 1e-9:
        raise SystemExit(f'household_headship: one-person people / one-person households = {one} (expected 1).')
    return float(f), float(g)


def headship(P, f, g):
    """Households per person by age group."""
    return (P[LAT['one']] + f * (P[LAT['cpl']] / 2 + P[LAT['two']] / 2 + P[LAT['opp']]) + g * P[LAT['oth']]) \
        / P[LAT['tot']]


def paths(variant='Medium'):
    """DataFrame by knot year: S_2023 (2023 rates), S_min_2023_or_B, the Stats NZ A and B household sizes (people in
    households / households) of the variant, and the ratios of the two alternatives to S_2023."""
    p, h = load()
    f, g = calibration(p, h)
    h23 = headship(_people(p, 'Medium A', 2023), f, g)
    rows = []
    for y in KNOTS:
        PA = _people(p, f'{variant} A', y)
        hB = headship(_people(p, f'{variant} B', y), f, g)
        pop = PA[LAT['tot']]
        rows.append(dict(year=y, S_2023=float(pop.sum() / (h23 * pop).sum()),
                         S_min_2023_or_B=float(pop.sum() / (np.minimum(h23, hB) * pop).sum())))
    t = pd.DataFrame(rows).set_index('year')
    d = pd.read_csv(os.path.join(ROOT, 'data', 'derived', 'households_proj_2023base.csv'))
    for prop in ('A', 'B'):
        s = d[(d['Variant'] == variant) & (d['Propensity'] == prop)].set_index('Year')['S']
        t[f'S_statsnz_{prop}'] = s.reindex(t.index).values
    t['ratio_min_2023_or_B'] = t['S_min_2023_or_B'] / t['S_2023']
    return t


def ratio_path(years, variant='Medium', column='ratio_min_2023_or_B'):
    """The ratio of an alternative to S_2023 by model year: linear between the knots, held after 2048 and at 1 before
    2023 (the model's 2024-2025 household size is observed)."""
    t = paths(variant)
    y = np.asarray(years, float)
    r = np.interp(y, t.index.values.astype(float), t[column].values)
    return np.where(y <= KNOTS[0], 1.0, r)


def households_per_person_fall(S_level, S_2050_2023_rates):
    """The fall in households per person at every age needed to hold household size at S_level when the 2023 rates on
    the 2050 population give S_2050_2023_rates: 1 - S_2050_2023_rates / S_level."""
    return 1.0 - float(S_2050_2023_rates) / float(S_level)
