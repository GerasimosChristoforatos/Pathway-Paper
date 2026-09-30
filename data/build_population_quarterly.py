"""
Build the quarterly population series from the raw Stats NZ Infoshare export.
No values typed by hand.

Source (data/raw/, provenance in MANIFEST.csv):
  DPE404001_20260930_042725_56.csv
  Stats NZ Infoshare, Population Estimates - DPE: 'Estimated Resident
  Population (Mean Quarter Ended) by Sex (1991+) (Qrtly-Mar/Jun/Sep/Dec)'.

IMPORTANT: these are MEAN-QUARTER values (the average population over the
quarter), not point estimates at the quarter's end. Each value is dated at the
middle of its quarter (centre, decimal year).

Uses the 'Total' column; if absent, Male + Female. Checks Total = Male + Female
where all three are present.

Output: data/derived/population_quarterly.csv
  year, quarter, centre (decimal year), male, female, total
"""
import csv
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'DPE404001_20260930_042725_56.csv')
OUT = os.path.join(HERE, 'derived', 'population_quarterly.csv')


def main():
    rows, header = [], None
    with open(SRC, newline='', encoding='utf-8-sig') as f:
        for r in csv.reader(f):
            if len(r) >= 3 and r[0] == '' and 'Male' in r:
                header = r
                continue
            m = re.fullmatch(r'(\d{4})Q([1-4])', r[0].strip()) if r else None
            if m and header:
                vals = {h: (float(x) if x.strip() not in ('', '..') else None) for h, x in zip(header[1:], r[1:])}
                rows.append(dict(year=int(m.group(1)), quarter=int(m.group(2)), **vals))
    if not rows:
        raise ValueError('No quarterly rows found in the DPE export.')
    d = pd.DataFrame(rows).rename(columns=str.lower)
    if 'total' not in d or d['total'].isna().any():
        d['total'] = d['total'].fillna(d['male'] + d['female']) if 'total' in d else d['male'] + d['female']
    both = d[['male', 'female', 'total']].notna().all(axis=1)
    worst = float((d.loc[both, 'total'] - d.loc[both, 'male'] - d.loc[both, 'female']).abs().max())
    if worst > 200:          # published figures are rounded to the nearest 100
        raise ValueError(f'Total differs from Male + Female by up to {worst:,.0f}.')
    d['centre'] = d['year'] + (d['quarter'] - 0.5) / 4.0
    d = d[['year', 'quarter', 'centre', 'male', 'female', 'total']]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    d.to_csv(OUT, index=False)
    last = d.iloc[-1]
    print(f"{os.path.basename(SRC)} -> {OUT}: {len(d)} quarters {d.year.iloc[0]}Q{d.quarter.iloc[0]}.."
          f"{int(last.year)}Q{int(last.quarter)}; total = male + female within {worst:,.0f}")


if __name__ == '__main__':
    main()
