"""
Build the world and New Zealand population series from the raw UN World
Population Prospects 2024 probabilistic projections. No values typed by hand.

Source (data/raw/, provenance in MANIFEST.csv):
  UN_PPP2024_Output_PopTot.xlsx
  United Nations, DESA, Population Division (2024). World Population Prospects
  2024, Probabilistic Population Projections, file PPP/POPTOT
  (POP/DB/WPP/Rev.2024/PPP/POPTOT): total population (both sexes) as of
  1 July, thousands, 2024-2100.

Only the sheet 'Median' (the probabilistic median, '50 percent') is used; the
prediction-interval sheets are not read (the population uncertainty of the
model is the Stats NZ one; UN intervals are not combined with it).

Output: data/derived/wpp2024_population_median.csv
  year, world, new_zealand   (persons at 1 July = thousands x 1000)
"""
import os

import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'UN_PPP2024_Output_PopTot.xlsx')
OUT = os.path.join(HERE, 'derived', 'wpp2024_population_median.csv')
SHEET = 'Median'
AREAS = {'World': 'world', 'New Zealand': 'new_zealand'}   # 'Region, subregion, country or area *'
LOCATION_CODES = {'World': 900, 'New Zealand': 554}        # UN M49 codes, checked against the file


def main():
    ws = openpyxl.load_workbook(SRC, data_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r[0] == 'Index')
    header = list(rows[hi])
    if not any('as of 1 July (thousands)' in str(v) for v in rows[hi - 1] if v):
        raise ValueError('Unit line "as of 1 July (thousands)" not found above the header.')
    name_col, code_col = header.index('Region, subregion, country or area *'), header.index('Location code')
    years = [h for h in header if isinstance(h, int)]
    series = {}
    for r in rows[hi + 1:]:
        if r[name_col] in AREAS:
            if r[code_col] != LOCATION_CODES[r[name_col]]:
                raise ValueError(f'{r[name_col]}: location code {r[code_col]}, expected {LOCATION_CODES[r[name_col]]}.')
            if r[header.index('Variant')] != 'Median PI':
                raise ValueError(f'Unexpected variant {r[header.index("Variant")]!r} in sheet {SHEET}.')
            series[AREAS[r[name_col]]] = [float(r[header.index(y)]) * 1000.0 for y in years]
    if set(series) != set(AREAS.values()):
        raise ValueError(f'Rows not found: {set(AREAS.values()) - set(series)}')
    d = pd.DataFrame({'year': years, **series})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    d.to_csv(OUT, index=False)
    print(f'{os.path.basename(SRC)} [{SHEET}] -> {OUT}: {years[0]}-{years[-1]}; '
          f'world 2025 = {d.set_index("year").loc[2025, "world"]:,.0f}')


if __name__ == '__main__':
    main()
