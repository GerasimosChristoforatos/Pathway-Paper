"""
Build the observed-population input for the 2026 nowcast (A1) from the raw
Stats NZ release page. No values typed by hand.

Source (data/raw/, provenance in MANIFEST.csv):
  national_population_estimates_june_2026.html
  Stats NZ, 'National population estimates: At 30 June 2026' (provisional).

Parsed: the estimated resident population at 30 June and the population
growth over the year ended June, from the release text:
  'The provisional estimated resident population ... was N at 30 June YYYY.'
  '... population grew by N (P percent)'

INTERIM SOURCE. These are provisional headline figures. The proper input is
the quarterly ERP series from Stats NZ Infoshare (Population -> Population
Estimates - DPE), to be supplied by the author; when it is, this script will
be replaced by a reader of that download.

Output: data/derived/population_nowcast.csv
"""
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'national_population_estimates_june_2026.html')
OUT = os.path.join(HERE, 'derived', 'population_nowcast.csv')


def main():
    t = open(SRC, encoding='utf-8', errors='ignore').read()
    erp = re.search(r'provisional estimated resident population of [^.]*? was ([\d,]+) at 30 June (\d{4})', t)
    grew = re.search(r'population grew by ([\d,]+) \(([\d.]+) percent\)', t)
    if not (erp and grew):
        raise ValueError('Expected statements not found in the population release page.')
    year = int(erp.group(2))
    row = dict(year_ended_june=year, erp_30_june=float(erp.group(1).replace(',', '')),
               growth_year_ended_june=float(grew.group(1).replace(',', '')),
               status='provisional', source=os.path.basename(SRC))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pd.DataFrame([row]).to_csv(OUT, index=False)
    print(f"{os.path.basename(SRC)} -> {OUT}: ERP {row['erp_30_june']:,.0f} at 30 June {year}; "
          f"growth {row['growth_year_ended_june']:,.0f} over the year ended June {year} (provisional)")


if __name__ == '__main__':
    main()
