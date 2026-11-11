"""
Build the national household-size knots of the Stats NZ 2023-base family and household projections. No values typed
by hand.

Sources (data/raw/, provenance in MANIFEST.csv), Stats NZ Aotearoa Data Explorer CSV exports, 2023(base)-2048:
  POPPR_FHH_008.csv  National family and household projections, population by living arrangement type, age, and sex
                     (people in households)
  POPPR_FHH_010.csv  National household projections, by household type
Projections: Low / Medium / High (the 5th / 50th / 95th percentile population projections) x living-arrangement
propensity A (held constant at 2023) / B (change modelled on the 2001-2023 censuses). DataInfo+:
https://datainfoplus.stats.govt.nz/item/nz.govt.stats/e7475c01-9e55-491d-a8fe-74efa8fba757

Output: data/derived/households_proj_2023base.csv
  Year, Variant (Low | Medium | High), Propensity (A | B), Population, Households, S
  Population = POPPR_FHH_008 living arrangement 'LAT' (total people), sex 3 (total), age 'TOTALALLAGES';
  Households = POPPR_FHH_010 measure 'HH' (total households); S = Population / Households.
The published average household size (measure 'AHS') is rounded to 0.1 and is not used.

Checks (STOP otherwise): family + one-person + other multi-person households = total households within 100 (Stats NZ
rounds each count to the nearest 100); the living-arrangement types sum to the total people within 100 per type
summed (rounding of each published count); every projection x year present exactly once; the 2023 base year is the
same in every projection; A and B share the population of each variant in every year (they differ only in the
living-arrangement propensities).
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_POP = os.path.join(HERE, 'raw', 'POPPR_FHH_008.csv')
SRC_HH = os.path.join(HERE, 'raw', 'POPPR_FHH_010.csv')
OUT = os.path.join(HERE, 'derived', 'households_proj_2023base.csv')
PROJECTIONS = {'LOWA': ('Low', 'A'), 'MEDIUMA': ('Medium', 'A'), 'HIGHA': ('High', 'A'),
               'LOWB': ('Low', 'B'), 'MEDIUMB': ('Medium', 'B'), 'HIGHB': ('High', 'B')}
YEARS = (2023, 2028, 2033, 2038, 2043, 2048)
ROUNDING = 100                       # Stats NZ rounds every published count to the nearest 100


def _stop(msg):
    raise SystemExit(f'STOP (build_households_2023): {msg}')


def _one(df, keys, what):
    if df.duplicated(keys).any():
        _stop(f'{what}: duplicate rows for {keys}.')
    got = set(map(tuple, df[keys].values.tolist()))
    want = {(p, y) for p in PROJECTIONS for y in YEARS}
    if not want <= {g[:2] for g in got}:
        _stop(f'{what}: missing projection x year: {sorted(want - {g[:2] for g in got})}.')


def population():
    d = pd.read_csv(SRC_POP)
    d = d.rename(columns={'PROJECTION_POPPR_FHH_008': 'proj', 'YEAR_POPPR_FHH_008': 'year',
                          'LAT_POPPR_FHH_008': 'lat', 'SEX_POPPR_FHH_008': 'sex', 'AGE_POPPR_FHH_008': 'age'})
    if not d['OBS_VALUE'].notna().all():
        _stop('POPPR_FHH_008 has empty values.')
    tot = d[(d['sex'] == 3) & (d['age'] == 'TOTALALLAGES')]
    _one(tot, ['proj', 'year', 'lat'], 'POPPR_FHH_008 totals')
    people = tot[tot['lat'] == 'LAT'].set_index(['proj', 'year'])['OBS_VALUE']
    if not (tot.loc[tot['lat'] == 'LAT', 'Living arrangement type'] == 'Total people').all():
        _stop("POPPR_FHH_008: 'LAT' is not 'Total people'.")
    parts = tot[tot['lat'] != 'LAT'].groupby(['proj', 'year'])
    n_parts = parts['OBS_VALUE'].count()
    gap = (parts['OBS_VALUE'].sum() - people).abs()
    if (gap > ROUNDING * n_parts).any():
        _stop(f'POPPR_FHH_008: living-arrangement types differ from the total by up to {gap.max():,.0f}.')
    return people, float(gap.max())


def households():
    d = pd.read_csv(SRC_HH)
    d = d.rename(columns={'PROJECTION_POPPR_FHH_010': 'proj', 'YEAR_POPPR_FHH_010': 'year',
                          'MEASURE_POPPR_FHH_010': 'measure'})
    if not d['OBS_VALUE'].notna().all():
        _stop('POPPR_FHH_010 has empty values.')
    _one(d, ['proj', 'year', 'measure'], 'POPPR_FHH_010')
    w = d.pivot(index=['proj', 'year'], columns='measure', values='OBS_VALUE')
    gap = (w['FHH'] + w['OPH'] + w['OMH'] - w['HH']).abs()
    if (gap > ROUNDING).any():
        _stop(f'POPPR_FHH_010: FHH + OPH + OMH differs from HH by up to {gap.max():,.0f} (> {ROUNDING}).')
    return w['HH'], float(gap.max())


def main():
    people, gap_pop = population()
    hh, gap_hh = households()
    rows = []
    for p, (variant, prop) in PROJECTIONS.items():
        for y in YEARS:
            rows.append(dict(Year=y, Variant=variant, Propensity=prop, Population=float(people[(p, y)]),
                             Households=float(hh[(p, y)]), S=float(people[(p, y)]) / float(hh[(p, y)])))
    out = pd.DataFrame(rows).sort_values(['Propensity', 'Variant', 'Year']).reset_index(drop=True)
    base = out[out['Year'] == YEARS[0]]
    if base[['Population', 'Households']].nunique().max() != 1:
        _stop('the 2023 base year differs between projections.')
    pa = out.pivot_table(index=['Variant', 'Year'], columns='Propensity', values='Population')
    if not (pa['A'] == pa['B']).all():
        _stop('A and B do not share the population of each variant.')
    out.to_csv(OUT, index=False, float_format='%.10g')
    print(f'build_households_2023: {len(out)} rows -> {OUT}; FHH + OPH + OMH - HH max |diff| {gap_hh:,.0f}; '
          f'living-arrangement types - total people max |diff| {gap_pop:,.0f}')
    print(out.pivot_table(index='Year', columns=['Propensity', 'Variant'], values='S').round(3).to_string())


if __name__ == '__main__':
    main()
