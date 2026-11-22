"""
Vacant dwellings by country from the OECD Affordable Housing Database, indicator HM1.1 (Housing stock and
construction), Figure HM1.1.2 (lever L2 at the Theoretical Limit). No values typed by hand.

Source (provenance in data/raw/MANIFEST.csv; the file itself is kept in refs/, which is git-ignored):
  refs/OECD_AHD_HM1-1_housing_stock.xlsx
  OECD (2024) Affordable Housing Database, indicator HM1.1 Housing stock and construction,
  https://webfs.oecd.org/els-com/Affordable_Housing_Database/HM1-1-Housing-stock-and-construction.xlsx
  sheet 'HM1.1.2' (Figure HM 1.1.2. Vacant dwellings and seasonal/holiday homes in selected countries): the data block
  M8:Q32, columns N (% vacant dwellings excluding seasonal and holiday homes), O (% seasonal/holiday homes), P (% vacant
  dwellings and seasonal/holiday homes; panel B) and Q (year); and sheet 'Vacant' (national counts of vacant units).

Output: data/derived/oecd_hm112_vacancy.csv
  country, vacant_excl_seasonal_pct, seasonal_pct, vacant_incl_seasonal_pct, year, cell_panel_b
"""
import os

import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'refs', 'OECD_AHD_HM1-1_housing_stock.xlsx')
OUT = os.path.join(HERE, 'derived', 'oecd_hm112_vacancy.csv')
SHEET = 'HM1.1.2'
TITLE = 'Figure HM 1.1.2. Vacant dwellings and seasonal/holiday homes in selected countries'
HEADER_P = '% vacant dwellings and seasonal/holiday homes'
ROWS = range(8, 33)


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f'{SRC} not found (refs/ is not versioned; see data/raw/MANIFEST.csv).')
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb[SHEET]
    if ws['A1'].value != TITLE or str(ws['P5'].value).strip() != HEADER_P:
        raise ValueError(f'{SHEET}: unexpected title or header (A1 {ws["A1"].value!r}, P5 {ws["P5"].value!r}).')
    num = lambda v: float(v) if isinstance(v, (int, float)) else None
    rows = [dict(country=str(ws[f'M{r}'].value).strip(), vacant_excl_seasonal_pct=num(ws[f'N{r}'].value),
                 seasonal_pct=num(ws[f'O{r}'].value), vacant_incl_seasonal_pct=num(ws[f'P{r}'].value),
                 year=int(ws[f'Q{r}'].value), cell_panel_b=f'P{r}')
            for r in ROWS if ws[f'M{r}'].value]
    d = pd.DataFrame(rows)
    vac = wb['Vacant']
    sw = [r for r in range(1, vac.max_row + 1) if vac.cell(r, 2).value == 'Sweden']
    if len(sw) != 1:
        raise ValueError("'Vacant': Sweden row not found once.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        f.write(f"# OECD (2024) Affordable Housing Database HM1.1, {os.path.basename(SRC)} sheet '{SHEET}' rows "
                f"{ROWS.start}-{ROWS.stop - 1}; Sweden national count of vacant units: sheet 'Vacant' row {sw[0]} "
                f"({', '.join(str(vac.cell(sw[0], c).value) for c in range(3, 10))}). Written by data/build_oecd_vacancy.py.\n")
        d.to_csv(f, index=False)
    lo = d.dropna(subset=['vacant_incl_seasonal_pct']).sort_values('vacant_incl_seasonal_pct').head(3)
    print(f'{os.path.basename(SRC)} [{SHEET}] -> {OUT}: {len(d)} countries; lowest panel B: '
          + ', '.join(f'{r.country} {r.vacant_incl_seasonal_pct:.4f}% ({r.year}, {r.cell_panel_b})' for r in lo.itertuples()))


if __name__ == '__main__':
    main()
