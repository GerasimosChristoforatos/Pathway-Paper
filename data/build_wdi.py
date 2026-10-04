"""
Build the country table of population and GDP per capita from the raw World
Bank World Development Indicators bulk CSV downloads. No values typed by hand.

Sources (data/raw/, provenance in MANIFEST.csv), World Bank WDI bulk CSV
archives (release 'Last Updated Date 2026-07-13', stated in each file):
  API_SP.POP.TOTL_DS2_en_csv_v2_460437.zip        Population, total
  API_NY.GDP.PCAP.PP.KD_DS2_en_csv_v2_436175.zip  GDP per capita, PPP (constant 2021 international $)
  API_NY.GDP.PCAP.CD_DS2_en_csv_v2_464091.zip     GDP per capita (current US$)

Aggregates (regions, income groups, 'World', ...) are dropped with the
archive's own Metadata_Country file: an aggregate is a row with no 'Region'.
The three archives must list the same economies.

Outputs:
  data/derived/wdi_economies.csv (long)
    country_code, country_name, year, SP.POP.TOTL, NY.GDP.PCAP.PP.KD, NY.GDP.PCAP.CD
    (missing values are empty; one row per economy and year 1990-latest)
  data/derived/wdi_world_aggregate.csv
    year and the same three indicators for the published 'World' aggregate (WLD);
    used only as the denominator when reporting coverage, never in a calculation.
"""
import io
import os
import zipfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT = os.path.join(HERE, 'derived', 'wdi_economies.csv')
OUT_WLD = os.path.join(HERE, 'derived', 'wdi_world_aggregate.csv')
FILES = {'SP.POP.TOTL': 'API_SP.POP.TOTL_DS2_en_csv_v2_460437.zip',
         'NY.GDP.PCAP.PP.KD': 'API_NY.GDP.PCAP.PP.KD_DS2_en_csv_v2_436175.zip',
         'NY.GDP.PCAP.CD': 'API_NY.GDP.PCAP.CD_DS2_en_csv_v2_464091.zip'}
FIRST_YEAR = 1990


def read_archive(code, name):
    with zipfile.ZipFile(os.path.join(RAW, name)) as z:
        data = [n for n in z.namelist() if n.startswith('API_')]
        meta = [n for n in z.namelist() if n.startswith('Metadata_Country')]
        if len(data) != 1 or len(meta) != 1:
            raise ValueError(f'{name}: expected one data and one Metadata_Country file, got {z.namelist()}')
        head = z.read(data[0]).decode('utf-8-sig').splitlines()[:3]
        d = pd.read_csv(io.BytesIO(z.read(data[0])), skiprows=4)
        m = pd.read_csv(io.BytesIO(z.read(meta[0])))
    if set(d['Indicator Code']) != {code}:
        raise ValueError(f'{name}: indicator {set(d["Indicator Code"])}, expected {code}.')
    updated = [h for h in head if 'Last Updated Date' in h]
    economies = set(m.loc[m['Region'].notna() & (m['Region'].astype(str).str.strip() != ''), 'Country Code'])
    years = [c for c in d.columns if c.isdigit() and int(c) >= FIRST_YEAR]
    long = (d[d['Country Code'].isin(economies | {'WLD'})]
            .melt(id_vars=['Country Code', 'Country Name'], value_vars=years, var_name='year', value_name=code))
    long['year'] = long['year'].astype(int)
    return long, economies, (updated[0] if updated else '?'), len(set(d['Country Code']) - economies)


def main():
    frames, sets = [], []
    for code, name in FILES.items():
        long, econ, updated, n_agg = read_archive(code, name)
        frames.append(long.set_index(['Country Code', 'Country Name', 'year']))
        sets.append(econ)
        print(f'  {code:<18} {len(econ)} economies, {n_agg} aggregates dropped; {updated.strip(",")}')
    if any(s != sets[0] for s in sets[1:]):
        raise ValueError('The archives do not list the same economies.')
    d = pd.concat(frames, axis=1).reset_index().rename(columns={'Country Code': 'country_code',
                                                                 'Country Name': 'country_name'})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wld = d[d['country_code'] == 'WLD'].drop(columns=['country_code', 'country_name'])
    d = d[d['country_code'] != 'WLD']
    d.sort_values(['country_code', 'year']).to_csv(OUT, index=False)
    wld.sort_values('year').to_csv(OUT_WLD, index=False)
    print(f'-> {OUT}: {d.country_code.nunique()} economies x {d.year.nunique()} years; WLD aggregate -> {OUT_WLD}')


if __name__ == '__main__':
    main()
