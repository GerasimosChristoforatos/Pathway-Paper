"""
Build the quarterly New Zealand GDP(E) series from the raw Stats NZ Infoshare
export. No values typed by hand.

Source (data/raw/, provenance in MANIFEST.csv):
  GDP_Data.xlsx
  Stats NZ Infoshare table SNE022AA, 'Series, GDP(E), Nominal, Actual, Total
  (Qrtly-Mar/Jun/Sep/Dec)', NZD millions, current prices; last updated
  19 March 2026 (stated in the file).

Used by PB.py for the final-consumption-expenditure upscaling of the ability-to-
pay boundary (Hjalsted et al. 2021, Eq. 6): GDP and final consumption
expenditure (FCE) by quarter.

Output: data/derived/nz_gdp_quarterly.csv
  quarter (e.g. 2016Q1), year, q, gdp_nzd_m, gne_nzd_m, fce_nzd_m,
  gcf_nzd_m, gfcf_nzd_m, inventories_nzd_m   (NZD millions, nominal)
"""
import os
import re

import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'GDP_Data.xlsx')
OUT = os.path.join(HERE, 'derived', 'nz_gdp_quarterly.csv')
TITLE = 'Series, GDP(E), Nominal, Actual, Total (Qrtly-Mar/Jun/Sep/Dec)'
COLUMNS = {  # header in the file -> output column
    'Gross Domestic Product - expenditure measure': 'gdp_nzd_m',
    'Gross National Expenditure': 'gne_nzd_m',
    'Final Consumption Expenditure': 'fce_nzd_m',
    'Gross Capital Formation': 'gcf_nzd_m',
    'Gross Fixed Capital Formation': 'gfcf_nzd_m',
    'Changes in Inventories': 'inventories_nzd_m',
}


def main():
    rows = list(openpyxl.load_workbook(SRC, data_only=True, read_only=True).active.iter_rows(values_only=True))
    if rows[0][0] != TITLE:
        raise ValueError(f'Unexpected table title {rows[0][0]!r}; expected {TITLE!r}.')
    header = list(rows[1])
    idx = {COLUMNS[h]: i for i, h in enumerate(header) if h in COLUMNS}
    if set(idx) != set(COLUMNS.values()):
        raise ValueError(f'Missing columns: {set(COLUMNS.values()) - set(idx)}')
    out = []
    for r in rows[2:]:
        m = re.fullmatch(r'(\d{4})Q([1-4])', str(r[0]).strip()) if r[0] is not None else None
        if not m:
            continue
        out.append(dict(quarter=str(r[0]).strip(), year=int(m.group(1)), q=int(m.group(2)),
                        **{k: float(r[i]) for k, i in idx.items()}))
    d = pd.DataFrame(out)
    if d.empty or d['quarter'].duplicated().any():
        raise ValueError('No quarters, or duplicated quarters, in the GDP(E) export.')
    # expenditure identity (published values are rounded to NZD 1 million)
    gap = (d['gne_nzd_m'] - d['fce_nzd_m'] - d['gcf_nzd_m']).abs().max()
    if gap > 3:
        raise ValueError(f'GNE != FCE + GCF by up to {gap} NZD million.')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    d.to_csv(OUT, index=False)
    print(f'{os.path.basename(SRC)} -> {OUT}: {len(d)} quarters {d.quarter.iloc[0]}..{d.quarter.iloc[-1]}; '
          f'GNE = FCE + GCF within {gap:g} NZD million')


if __name__ == '__main__':
    main()
