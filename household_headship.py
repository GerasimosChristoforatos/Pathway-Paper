"""Age-specific household formation (headship) for L1 at TL: the lowest observed census headship of each age group,
or the Stats NZ propensity-B projected rate where lower.

Data (unmodified in data/raw, MANIFEST.csv; derived by data/build_census_headship.py):
  * census living arrangements by age, 2013, 2018 and 2023 (CEN23_FHH_036, people in households in occupied private
    dwellings) and the stated households by composition (CEN23_FHH_041): data/derived/census_living_arrangements.csv,
    census_household_targets.csv;
  * the Stats NZ 2023-base projections by living arrangement (POPPR_FHH_008) and households (POPPR_FHH_010): the
    projected age structures and propensity B;
  * ERP by age (DPE058AA), the age shares of the back-check: data/derived/erp_age_groups.csv.

Living-arrangement types (POPPR_FHH_008) and census roles (CEN23_FHH_036):

  | type                                  | census role                                                     | headship |
  |---------------------------------------|-----------------------------------------------------------------|----------|
  | person in one-person household        | person living alone                                             | 1        |
  | partner, couple-without-children      | spouse/partner only in a family nucleus                         | f / 2    |
  | partner/parent, two-parent family     | parent and spouse/partner (incl. grandparent in a parent role)  | f / 2    |
  | parent, one-parent family             | sole parent (incl. sole grandparent in a parent role)           | f        |
  | child in a two- or one-parent family  | child in a family nucleus                                       | 0        |
  | other living arrangement types        | other person not in a family nucleus; person under 15 in a      | g        |
  |                                       | household of people under 15                                    |          |
  | (excluded)                            | individual's role unknown                                       |          |

Method (age groups a: 0-14, 15-39, 40-64, 65+; census years c: 2013, 2018, 2023):
    h_a,c = [one-person + f_c (couple partners / 2 + two-parent partners / 2 + one-parent parents) + g_c other] / P_a,c
  P_a,c = people with a stated role. f_c (households per family unit) and g_c (households per person in other living
  arrangements) are calibrated so that census c reproduces its own stated family and other-multi-person households
  (CEN23_FHH_041; family = one-, two- and three-or-more-family households); one-person people equal one-person
  households. Unknown roles and unidentifiable households are treated as distributed like the stated ones (proportional
  allocation): the rates are taken on the stated basis and applied to whole populations.
  Propensity B enters as a ratio, so every rate is on the census basis: h_a^B,adj(y) = h_a,2023 x h_a^B(y) /
  h_a,2023^proj (POPPR rates, calibrated on POPPR_FHH_010 2023 as before).
  TL rate: h_a^TL(y) = min(min_c h_a,c, h_a^B,adj(y)) (never weaker than L1 Ambitious, the propensity-B path).
  S^TL(y) / S_2023(y) = [sum_a P_a(y) / sum_a h_a^TL(y) P_a(y)] / [sum_a P_a(y) / sum_a h_a,2023 P_a(y)] on the
  projected age structure P_a(y) of a population variant (the ratio method: aggregation and base-level differences
  cancel). The model's L1 at TL is S_ref(y) x that ratio, under the speed limit (levers.tl1_path).

Gates (STOP on failure):
  * calibration: 0 < f_c <= 1 and 0 < g_c < 1 at every census, and f_c within +/-5% of f_2013;
  * one-person people = one-person households at every census (within the random rounding of the two tables);
  * common basis: each source's age-group rates divided by its own all-ages rate (households per person in
    households) agree between the 2023 census and the 2023 projection base within 2% for 15-39, 40-64 and 65+
    (0-14 excluded, rate ~0).
Comparisons reported (household_headship.report()): census minus projection-base shares by age and type; the raw
level difference (people per household 2023: census 2.556 on usual residence vs POPPR 2.741 on the ERP base), which
cancels in the ratio; the back-check against the household-size history (ratio form, ERP age shares, 1991-2006).
Check (tests/test_household_headship.py): the POPPR 2023 rates reproduce the Stats NZ Medium A household size within
0.025 at every knot (the four broad age groups; this aggregation bias cancels in the ratio).
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'data', 'raw')
DERIVED = os.path.join(ROOT, 'data', 'derived')
AGES = ('0-14 years', '15-39 years', '40-64 years', '65 years and over')
GROUPS = ('0-14', '15-39', '40-64', '65+')                # the same four groups (census / ERP files)
LAT = {'one': 'Person in one-person household', 'cpl': 'Partner in couple-without-children family',
       'two': 'Partner/parent in two-parent family', 'opp': 'Parent in one-parent family',
       'oth': 'Other living arrangement types', 'tot': 'Total people'}
KNOTS = (2023, 2028, 2033, 2038, 2043, 2048)
CENSUSES = (2013, 2018, 2023)
CHECK_TOL = 0.025         # POPPR 2023 rates against the Stats NZ household size of the same variant (A), every knot
F_BAND = 0.05             # f_c within +/-5% of f_2013
COMMON_BASIS_TOL = 0.02   # normalised 2023 rates, census vs projection base, 15-39 / 40-64 / 65+
ONE_PERSON_TOL = 1e-3     # one-person people / one-person households - 1 (two tables, random rounding)
BACKCHECK_YEARS = (1991, 1996, 2001, 2006)


# ---------------------------------------------------------------- projection base (POPPR_FHH_008 / 010) ----
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
    """(f, g) of the projection base: households per family unit and per person in other living arrangements, 2023."""
    P = _people(p, 'Medium A', 2023)
    fam_units = P[LAT['cpl']].sum() / 2 + P[LAT['two']].sum() / 2 + P[LAT['opp']].sum()
    f = _households(h, 'Medium A', 2023, 'Family households') / fam_units
    g = _households(h, 'Medium A', 2023, 'Other multi-person households') / P[LAT['oth']].sum()
    one = P[LAT['one']].sum() / _households(h, 'Medium A', 2023, 'One-person households')
    if abs(one - 1.0) > 1e-9:
        raise SystemExit(f'household_headship: one-person people / one-person households = {one} (expected 1).')
    return float(f), float(g)


def headship(P, f, g):
    """Households per person by age group (projection-base living arrangements)."""
    return (P[LAT['one']] + f * (P[LAT['cpl']] / 2 + P[LAT['two']] / 2 + P[LAT['opp']]) + g * P[LAT['oth']]) \
        / P[LAT['tot']]


def projection_check(variant='Medium'):
    """By knot: the household size of the POPPR 2023 rates on the variant's A structure against Stats NZ's (CHECK_TOL)."""
    p, h = load()
    f, g = calibration(p, h)
    h23 = headship(_people(p, 'Medium A', 2023), f, g)
    rows = []
    for y in KNOTS:
        pop = _people(p, f'{variant} A', y)[LAT['tot']]
        rows.append(dict(year=y, S_2023=float(pop.sum() / (h23 * pop).sum())))
    t = pd.DataFrame(rows).set_index('year')
    d = pd.read_csv(os.path.join(DERIVED, 'households_proj_2023base.csv'))
    s = d[(d['Variant'] == variant) & (d['Propensity'] == 'A')].set_index('Year')['S']
    t['S_statsnz_A'] = s.reindex(t.index).values
    return t


# ---------------------------------------------------------------- census series ----
def census_people():
    """{census year: DataFrame by age group (GROUPS) of one, cpl, two, opp, child, oth, unknown, total, stated}."""
    d = pd.read_csv(os.path.join(DERIVED, 'census_living_arrangements.csv'))
    return {int(y): g.pivot_table(index='age_group', columns='type', values='people').loc[list(GROUPS)]
            for y, g in d.groupby('year')}


def census_targets():
    return pd.read_csv(os.path.join(DERIVED, 'census_household_targets.csv')).set_index('year')


def census_calibration():
    """{c: dict(f, g, one_person_ratio, family_units, unknown_share, unidentifiable_share)}; STOP on the gates."""
    P, T = census_people(), census_targets()
    out = {}
    for c in CENSUSES:
        C, t = P[c], T.loc[c]
        fam_units = C['cpl'].sum() / 2 + C['two'].sum() / 2 + C['opp'].sum()
        out[c] = dict(f=float(t['family'] / fam_units), g=float(t['other_multi_person'] / C['oth'].sum()),
                      one_person_ratio=float(C['one'].sum() / t['one_person']), family_units=float(fam_units),
                      unknown_share=float(C['unknown'].sum() / C['total'].sum()),
                      unknown_share_by_age={a: float(C.loc[a, 'unknown'] / C.loc[a, 'total']) for a in GROUPS},
                      unidentifiable_share=float(t['unidentifiable'] / t['total']))
    bad = [f'{c}: f {v["f"]:.4f} g {v["g"]:.4f}' for c, v in out.items()
           if not (0.0 < v['f'] <= 1.0 and 0.0 < v['g'] < 1.0)
           or abs(v['f'] / out[CENSUSES[0]]['f'] - 1.0) > F_BAND]
    if bad:
        raise SystemExit(f'STOP (household_headship): calibration constants implausible ({bad}; gate 0 < f <= 1, '
                         f'0 < g < 1, f within {F_BAND:.0%} of f_{CENSUSES[0]}).')
    off = {c: v['one_person_ratio'] for c, v in out.items() if abs(v['one_person_ratio'] - 1.0) > ONE_PERSON_TOL}
    if off:
        raise SystemExit(f'STOP (household_headship): one-person people != one-person households: {off}')
    return out


def census_headship(C, f, g):
    """Households per person with a stated role, by age group; children carry zero headship."""
    return (C['one'] + f * (C['cpl'] / 2 + C['two'] / 2 + C['opp']) + g * C['oth']) / C['stated']


def census_rates():
    """DataFrame (index GROUPS, columns CENSUSES): h_a,c."""
    P, cal = census_people(), census_calibration()
    return pd.DataFrame({c: census_headship(P[c], cal[c]['f'], cal[c]['g']) for c in CENSUSES}).loc[list(GROUPS)]


def common_basis_check():
    """The 2023 census and projection-base rates, each divided by its own all-ages rate; STOP above COMMON_BASIS_TOL
    for 15-39, 40-64 and 65+. Returns the comparison (dict)."""
    P, T, H = census_people(), census_targets(), census_rates()
    p, h = load()
    f0, g0 = calibration(p, h)
    Pp = _people(p, 'Medium A', 2023)
    hp = headship(Pp, f0, g0)
    hp.index = list(GROUPS)
    all_c = float(T.loc[2023, 'stated'] / P[2023]['stated'].sum())
    all_p = float((hp.values * Pp[LAT['tot']].values).sum() / Pp[LAT['tot']].sum())
    norm = pd.DataFrame({'census': H[2023] / all_c, 'projection': hp / all_p})
    norm['diff'] = norm['census'] / norm['projection'] - 1.0
    bad = norm.loc[['15-39', '40-64', '65+'], 'diff']
    if (bad.abs() > COMMON_BASIS_TOL).any():
        raise SystemExit(f'STOP (household_headship): normalised 2023 rates differ by more than '
                         f'{COMMON_BASIS_TOL:.0%}: {bad.round(4).to_dict()}')
    # the share comparison (census minus projection base, percentage points of people in each age group)
    C = P[2023]
    cen = C[['one', 'cpl', 'two', 'opp', 'child', 'oth']].div(C['stated'], axis=0)
    pro = pd.DataFrame({'one': Pp[LAT['one']], 'cpl': Pp[LAT['cpl']], 'two': Pp[LAT['two']], 'opp': Pp[LAT['opp']],
                        'child': Pp['Child in two-parent family'] + Pp['Child in one-parent family'],
                        'oth': Pp[LAT['oth']]}).div(Pp[LAT['tot']], axis=0)
    pro.index = list(GROUPS)
    return dict(normalised=norm, people_per_household=dict(census=1.0 / all_c, projection=1.0 / all_p),
                share_diff_pp=(cen - pro) * 100.0, f_projection=f0, g_projection=g0, h_projection=hp)


def tl_rates(variant='Medium'):
    """DataFrame by knot year and age group: h^TL_a(y) = min(min_c h_a,c, h^B,adj_a(y)), with the source of each
    minimum ('census YYYY' or 'B'). Returns (rates, source, h_B_adj)."""
    H = census_rates()
    p, h = load()
    f0, g0 = calibration(p, h)
    h23p = headship(_people(p, 'Medium A', 2023), f0, g0)
    h23p.index = list(GROUPS)
    cmin = H.min(axis=1)
    csrc = H.idxmin(axis=1).map(lambda c: f'census {c}')
    rates, src, hb = {}, {}, {}
    for y in KNOTS:
        b = headship(_people(p, f'{variant} B', y), f0, g0)
        b.index = list(GROUPS)
        badj = H[2023] * (b / h23p).where(h23p > 0, 1.0)
        hb[y] = badj
        rates[y] = np.minimum(cmin, badj)
        src[y] = pd.Series(np.where(badj < cmin, 'B', csrc), index=GROUPS)
    return pd.DataFrame(rates), pd.DataFrame(src), pd.DataFrame(hb)


def tl_paths(variant='Medium'):
    """DataFrame by knot: S_2023 (2023 census rates) and S_TL (TL rates) on the variant's projected A age structure,
    and their ratio."""
    H = census_rates()
    p, _ = load()
    R, _, _ = tl_rates(variant)
    rows = []
    for y in KNOTS:
        pop = _people(p, f'{variant} A', y)[LAT['tot']].values
        s23 = pop.sum() / (H[2023].values * pop).sum()
        stl = pop.sum() / (R[y].values * pop).sum()
        rows.append(dict(year=y, S_2023=float(s23), S_TL=float(stl), ratio=float(stl / s23)))
    return pd.DataFrame(rows).set_index('year')


def tl_ratio_path(years, variant='Medium', scale=1.0):
    """S^TL / S_2023 by model year: linear between the knots, held after 2048, 1 up to 2023 (the model's household
    size is observed through 2025; the speed limit starts in 2026). scale divides the TL rates (> 1: more shared)."""
    t = tl_paths(variant)
    y = np.asarray(years, float)
    r = np.interp(y, t.index.values.astype(float), t['ratio'].values) * float(scale)
    return np.where(y <= KNOTS[0], 1.0, r)


def back_check(hist_S):
    """Ratio form against the household-size history (census-benchmarked, the model's hist_S): for each earlier census
    year c, implied S_c / S_2023 = [sum P / sum h^TL P]_c / [sum P / sum h^TL P]_2023 on ERP age shares, against the
    observed S_c / S_2023. The TL rates are the census minima by age. Returns (DataFrame, the most-shared year or None,
    the scale that matches it)."""
    H = census_rates()
    erp = pd.read_csv(os.path.join(DERIVED, 'erp_age_groups.csv')).pivot_table(index='year', columns='age_group',
                                                                              values='people')[list(GROUPS)]
    h_tl = H.min(axis=1).values

    def implied(y):
        P = erp.loc[y].values
        return P.sum() / (h_tl * P).sum()
    s23 = implied(2023)
    rows = []
    for c in BACKCHECK_YEARS:
        imp = implied(c) / s23
        obs = float(hist_S.loc[c] / hist_S.loc[2023])
        rows.append(dict(year=c, implied_ratio=float(imp), observed_ratio=obs, gap=float(obs - imp),
                         S_obs=float(hist_S.loc[c]), more_shared=bool(obs > imp)))
    t = pd.DataFrame(rows).set_index('year')
    if not t['more_shared'].any():
        return t, None, 1.0
    yx = int(t['gap'].idxmax())
    return t, yx, float(t.loc[yx, 'observed_ratio'] / t.loc[yx, 'implied_ratio'])


def households_per_person_fall(S_level, S_2050_2023_rates):
    """The fall in households per person at every age needed to hold household size at S_level when the 2023 rates on
    the 2050 population give S_2050_2023_rates: 1 - S_2050_2023_rates / S_level."""
    return 1.0 - float(S_2050_2023_rates) / float(S_level)


def one_person_direction():
    """The one-person share of people by 5-year age (CEN23_FHH_018), 2013 and 2023, and whether it fell at every age
    15+."""
    d = pd.read_csv(os.path.join(DERIVED, 'census_one_person_share.csv'))
    w = d.pivot_table(index='age', columns='year', values='share')
    adult = [a for a in w.index if not a.startswith(('0-', '5-', '10-'))]
    return w, bool((w.loc[adult, 2023] < w.loc[adult, 2013]).all())
