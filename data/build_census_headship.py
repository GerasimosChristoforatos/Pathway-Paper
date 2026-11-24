"""
Build the census living-arrangement inputs of L1 at TL (household_headship.py) from the raw Stats NZ tables. No values
are typed by hand.

Sources (unmodified in data/raw/, provenance in data/raw/MANIFEST.csv):
  census_living_arrangements/CEN23_FHH_036.csv  individual's role in family nucleus by 5-year age, people in households
                                                in occupied private dwellings, 2013, 2018, 2023 Censuses (the rates);
  census_living_arrangements/CEN23_FHH_018.csv  people in households by household composition and 5-year age
                                                (one-person people, the one-person shares by age);
  census_living_arrangements/CEN23_FHH_041.csv  households by household composition, 2013, 2018, 2023 (the calibration
                                                targets: stated family, other multi-person and one-person households);
  census_living_arrangements/CEN13_FHH_026.csv  households by household composition, 2001, 2006, 2013 (cross-check of
                                                the 2013 targets);
  DPE058AA.csv                                  estimated resident population by single year of age at 31 December,
                                                1991-2025 (the age shares of the back-check).
National rows only: the three 'Total - New Zealand' geographies of each census table must agree (they are identical
in these exports; the build STOPs if any cell differs by more than the random-rounding tolerance). Cells flagged 'c'
(confidential) are missing; in these exports only median-age cells are confidential, and the method uses none.

Role -> living-arrangement type (the five types of POPPR_FHH_008 plus children, kept separate as in POPPR_FHH_008):

  | CEN23_FHH_036 role                                                    | type                                 |
  |-----------------------------------------------------------------------|--------------------------------------|
  | Person living alone                                                   | one-person                           |
  | Spouse/partner only in a family nucleus                               | partner, couple without children     |
  | Parent and spouse/partner in a family nucleus (incl. grandparent)     | partner/parent, two-parent family    |
  | Sole parent in a family nucleus (incl. sole grandparent)              | parent, one-parent family            |
  | Child in a family nucleus                                             | child (zero headship)                |
  | Other person not in a family nucleus; person under 15 in a household  | other                                |
  |   of people under 15                                                  |                                      |
  | Individual's role unknown                                             | excluded (shares reported)           |

Age groups (the four of POPPR_FHH_008): 0-14, 15-39, 40-64, 65+ from the 5-year groups.

Outputs (data/derived/):
  census_living_arrangements.csv  year, age_group, type, people (stated roles; 'unknown' and 'total' rows too);
  census_household_targets.csv    year, family, other_multi_person, one_person, unidentifiable, total, stated
                                  households (family = one-family + two-family + three-or-more-family);
  census_one_person_share.csv     year, age (5-year), share of people in one-person households (FHH_018);
  erp_age_groups.csv              year (31 December), age_group, people (DPE058AA).

    python data/build_census_headship.py
"""
import csv
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
CLA = os.path.join(RAW, 'census_living_arrangements')
OUT = os.path.join(HERE, 'derived')
YEARS = ('2013', '2018', '2023')
GROUPS = {'0-14': ['0-4 years', '5-9 years', '10-14 years'],
          '15-39': [f'{a}-{a + 4} years' for a in range(15, 40, 5)],
          '40-64': [f'{a}-{a + 4} years' for a in range(40, 65, 5)],
          '65+': [f'{a}-{a + 4} years' for a in range(65, 90, 5)] + ['90 years and over']}
ROLE = {'one': 'Person living alone', 'cpl': 'Spouse/partner only in a family nucleus',
        'two': 'Parent and spouse/partner in a family nucleus', 'opp': 'Sole parent in a family nucleus',
        'child': 'Child in a family nucleus',
        'oth': ('Other person not in a family nucleus', 'Person under 15 in a household of people under 15'),
        'unknown': "Individual's role unknown", 'total': "Total - individual's role in family nucleus"}
# subtotals of FHH_036 that must equal the sum of their parts (random rounding: each cell +/- 3 at most)
ROLE_PARTS = {'Parent and spouse/partner in a family nucleus':
              ('Parent (other than grandparent) and spouse/partner in a family nucleus',
               'Grandparent in a parent role and spouse/partner in a family nucleus'),
              'Sole parent in a family nucleus': ('Sole parent (other than sole grandparent) in a family nucleus',
                                                  'Sole grandparent in a parent role in a family nucleus'),
              'Not in a family nucleus': ('Person under 15 in a household of people under 15',
                                          'Other person not in a family nucleus', 'Person living alone')}
ROUNDING = 3            # Stats NZ random rounding to base 3


def stop(msg):
    raise SystemExit(f'STOP (build_census_headship): {msg}')


def read_national(path, geo_col, n_geo=3, keep='9999'):
    """A census table, national rows only; STOP unless its n_geo 'Total - New Zealand' geographies agree."""
    d = pd.read_csv(path, dtype=str, keep_default_na=False)
    if 'OBS_VALUE' not in d.columns or geo_col not in d.columns:
        stop(f'{os.path.basename(path)}: columns OBS_VALUE / {geo_col} missing')
    d['v'] = pd.to_numeric(d['OBS_VALUE'], errors='coerce')
    keys = [c for c in d.columns if c not in (geo_col, 'Area', 'OBS_VALUE', 'v', 'OBS_STATUS', 'Observation Status',
                                              'Observation Value', 'Observation value', 'STRUCTURE', 'STRUCTURE_ID',
                                              'STRUCTURE_NAME', 'ACTION')]
    wide = d.pivot_table(index=keys, columns=geo_col, values='v', aggfunc='first')
    if wide.shape[1] != n_geo:
        stop(f'{os.path.basename(path)}: expected {n_geo} national geographies, found {list(wide.columns)}')
    spread = (wide.max(axis=1) - wide.min(axis=1)).max()
    if spread > ROUNDING:
        stop(f'{os.path.basename(path)}: the national geographies differ by up to {spread}')
    conf = d[d.get('OBS_STATUS', '') == 'c']
    out = d[d[geo_col] == keep].copy()
    return out, len(conf), conf


def living_arrangements():
    d, nconf, conf = read_national(os.path.join(CLA, 'CEN23_FHH_036.csv'), 'CEN23_GEO_008')
    role = "Individual's role in family nucleus"
    if set(d['Census year']) != set(YEARS):
        stop(f'CEN23_FHH_036: census years {sorted(set(d["Census year"]))}, expected {YEARS}')
    if nconf and not set(conf['Age']) <= {'Median - age'}:
        stop(f'CEN23_FHH_036: confidential cells outside the median-age rows: {sorted(set(conf["Age"]))}')
    need = {ROLE[k] for k in ('one', 'cpl', 'two', 'opp', 'child', 'unknown', 'total')} | set(ROLE['oth'])
    miss = need - set(d[role])
    if miss:
        stop(f'CEN23_FHH_036: roles missing {sorted(miss)}')
    ages = {a for g in GROUPS.values() for a in g}
    if ages - set(d['Age']):
        stop(f'CEN23_FHH_036: 5-year ages missing {sorted(ages - set(d["Age"]))}')
    rows = []
    for y in YEARS:
        t = d[d['Census year'] == y]
        for whole, parts in ROLE_PARTS.items():
            for a in ages:
                tw = t[(t[role] == whole) & (t['Age'] == a)]['v'].sum()
                tp = t[(t[role].isin(parts)) & (t['Age'] == a)]['v'].sum()
                if abs(tw - tp) > ROUNDING * (len(parts) + 1):
                    stop(f'CEN23_FHH_036 {y} {a}: {whole} {tw} != sum of parts {tp}')
        for g, a5 in GROUPS.items():
            s = t[t['Age'].isin(a5)].groupby(role)['v'].sum()
            val = {k: float(sum(s.get(r, 0.0) for r in (v if isinstance(v, tuple) else (v,)))) for k, v in ROLE.items()}
            known = sum(val[k] for k in ('one', 'cpl', 'two', 'opp', 'child', 'oth'))
            if abs(known + val['unknown'] - val['total']) > ROUNDING * 8 * len(a5):
                stop(f'CEN23_FHH_036 {y} {g}: stated + unknown {known + val["unknown"]} != total {val["total"]}')
            for k, v in val.items():
                rows.append(dict(year=int(y), age_group=g, type=k, people=v))
            rows.append(dict(year=int(y), age_group=g, type='stated', people=known))
    return pd.DataFrame(rows), nconf


def household_targets():
    d, nconf, _ = read_national(os.path.join(CLA, 'CEN23_FHH_041.csv'), 'CEN23_GEO_013')
    comp = 'Household composition'
    if set(d['Sources of household income']) != {'Total - sources of household income'}:
        stop('CEN23_FHH_041: expected the filter "Total - sources of household income" only')
    need = {'One-family household (with or without other people)', 'Two-family household (with or without other people)',
            'Three or more family household (with or without other people)', 'Other multi-person household',
            'One-person household', 'Household composition unidentifiable', 'Total - household composition',
            'Total stated - household composition'}
    if need - set(d[comp]):
        stop(f'CEN23_FHH_041: compositions missing {sorted(need - set(d[comp]))}')
    rows = []
    for y in YEARS:
        t = d[d['Census year'] == y].set_index(comp)['v']
        fam = float(t['One-family household (with or without other people)']
                    + t['Two-family household (with or without other people)']
                    + t['Three or more family household (with or without other people)'])
        r = dict(year=int(y), family=fam, other_multi_person=float(t['Other multi-person household']),
                 one_person=float(t['One-person household']),
                 unidentifiable=float(t['Household composition unidentifiable']),
                 total=float(t['Total - household composition']),
                 stated=float(t['Total stated - household composition']))
        if abs(r['family'] + r['other_multi_person'] + r['one_person'] - r['stated']) > ROUNDING * 5:
            stop(f'CEN23_FHH_041 {y}: family + other + one-person != stated households')
        if abs(r['stated'] + r['unidentifiable'] - r['total']) > ROUNDING * 3:
            stop(f'CEN23_FHH_041 {y}: stated + unidentifiable != total households')
        rows.append(r)
    out = pd.DataFrame(rows)
    # 2013 cross-check against the CEN13 series (CEN13_FHH_026)
    c, _, _ = read_national(os.path.join(CLA, 'CEN13_FHH_026.csv'), 'AREA_CEN13_FHH_026', n_geo=2)
    c13 = c[c['Year'] == '2013'].set_index('Household composition')['v']
    fam13 = float(c13['Total one-family household'] + c13['Total two-family household']
                  + c13['Three or more family household (with or without other people)'])
    r13 = out[out['year'] == 2013].iloc[0]
    for k, v in (('family', fam13), ('other_multi_person', float(c13['Total other multi-person household'])),
                 ('one_person', float(c13['One-person household']))):
        if abs(r13[k] - v) / v > 0.005:
            stop(f'2013 {k}: CEN23_FHH_041 {r13[k]} vs CEN13_FHH_026 {v} differ by more than 0.5%')
    out.attrs['cen13_2013_family'] = fam13
    return out


def one_person_shares():
    d, _, _ = read_national(os.path.join(CLA, 'CEN23_FHH_018.csv'), 'CEN23_GEO_002')
    comp = 'Household composition'
    ages = [a for g in GROUPS.values() for a in g]
    rows = []
    for y in YEARS:
        t = d[d['Census year'] == y]
        for a in ages:
            ta = t[t['Age'] == a].set_index(comp)['v']
            rows.append(dict(year=int(y), age=a, one_person=float(ta['One-person household']),
                             stated=float(ta['Total stated - household composition']),
                             share=float(ta['One-person household'] / ta['Total stated - household composition'])))
    return pd.DataFrame(rows)


def erp_age_groups():
    path = os.path.join(RAW, 'DPE058AA.csv')
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    head = next(r for r in rows if len(r) > 2 and r[1] == '0 Years')
    if not rows[0][0].startswith('Estimated Resident Population by Age and Sex'):
        stop('DPE058AA.csv: not the "Estimated Resident Population by Age and Sex (1991+) (Annual-Dec)" table')
    col = {name: i for i, name in enumerate(head)}
    single = [f'{a} Years' for a in range(95)]
    if any(c not in col for c in single + ['95 Years and Over', 'Total All Ages']):
        stop('DPE058AA.csv: single years of age 0-94 and "95 Years and Over" are needed')
    out = []
    for r in rows:
        if r and r[0].strip().isdigit() and len(r) == len(head):
            y = int(r[0])
            v = {a: float(r[col[f'{a} Years']]) for a in range(95)}
            v95 = float(r[col['95 Years and Over']])
            grp = {'0-14': sum(v[a] for a in range(0, 15)), '15-39': sum(v[a] for a in range(15, 40)),
                   '40-64': sum(v[a] for a in range(40, 65)), '65+': sum(v[a] for a in range(65, 95)) + v95}
            tot = float(r[col['Total All Ages']])
            if abs(sum(grp.values()) - tot) > 0.001 * tot:
                stop(f'DPE058AA {y}: age groups sum to {sum(grp.values())}, total {tot}')
            out += [dict(year=y, age_group=g, people=p) for g, p in grp.items()]
    if not out:
        stop('DPE058AA.csv: no year rows')
    return pd.DataFrame(out)


def main():
    la, nconf = living_arrangements()
    tg = household_targets()
    op = one_person_shares()
    erp = erp_age_groups()
    os.makedirs(OUT, exist_ok=True)
    la.to_csv(os.path.join(OUT, 'census_living_arrangements.csv'), index=False)
    tg.to_csv(os.path.join(OUT, 'census_household_targets.csv'), index=False)
    op.to_csv(os.path.join(OUT, 'census_one_person_share.csv'), index=False)
    erp.to_csv(os.path.join(OUT, 'erp_age_groups.csv'), index=False)
    print(f'build_census_headship: {len(la)} living-arrangement rows (confidential cells: {nconf}, median-age only), '
          f'{len(tg)} census target rows (2013 family households: CEN23_FHH_041 '
          f'{tg.loc[tg.year == 2013, "family"].iloc[0]:,.0f}, CEN13_FHH_026 {tg.attrs["cen13_2013_family"]:,.0f}), '
          f'{len(op)} one-person share rows, ERP age groups {int(erp.year.min())}-{int(erp.year.max())}')


if __name__ == '__main__':
    sys.exit(main())
