"""
Build the census dwelling-occupancy input from the raw Stats NZ downloads.
No values are typed by hand.

Sources (data/raw/, provenance in data/raw/MANIFEST.csv):
  CEN23_HOU_018_NZ_totals.xlsx  Aotearoa Data Explorer STATSNZ:CEN23_HOU_018(1.0),
      dwelling occupancy status x dwelling type (private / non-private),
      2013, 2018, 2023, 'Total - New Zealand' rows. Primary source.
  CEN23_TBT_001.csv             STATSNZ:CEN23_TBT_001(1.0), totals by topic for
      dwellings, NZ total (SDMX-CSV). Cross-check of the all-type totals.
  occ-unocc-2013.xlsx           2013 Census QuickStats about housing, Tables 1-2
      (the model's source for 1981-2013). Cross-check of 2013 private values.

Output data/derived/census_dwellings.csv: one row per census year and dwelling
type (private, non_private, total) with occupied, unoccupied, empty, away,
under_construction and all_statuses.

Why private only matters: from 2018 Stats NZ counts UNOCCUPIED NON-PRIVATE
dwellings (camping grounds, marae, ...) for the first time (DataInfo+,
'Dwelling occupancy status', saved in data/raw/). The model's stock is private
dwellings, and its 1981-2013 census values are private only, so 2018 and 2023
must be private only as well.

Stats NZ randomly rounds census counts (to base 3), so parts may differ from
totals by a few units; checks allow for that.

The xlsx is read from its XML directly: the ADE export's stylesheet is
rejected by openpyxl ('expected Fill'), and only cell values are needed.

    python data/build_census.py
"""
import html
import os
import re
import zipfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
HOU018 = os.path.join(RAW, 'CEN23_HOU_018_NZ_totals.xlsx')
TBT001 = os.path.join(RAW, 'CEN23_TBT_001.csv')
Q2013 = os.path.join(HERE, 'occ-unocc-2013.xlsx')
OUT = os.path.join(HERE, 'derived', 'census_dwellings.csv')
ROUNDING_TOL = 10          # random rounding to base 3 across a few summed cells

STATUS = {'Occupied Dwelling': 'occupied', 'Unoccupied Dwelling': 'unoccupied',
          'Empty Dwelling': 'empty', 'Residents Away': 'away',
          'Dwelling Under Construction': 'under_construction',
          'Total - dwelling occupancy status': 'all_statuses'}
TYPE = {'Private Dwelling': 'private', 'Non-private Dwelling': 'non_private',
        'Total - dwelling type': 'total'}


def xlsx_cells(path, sheet='xl/worksheets/sheet1.xml'):
    z = zipfile.ZipFile(path)
    ss = [html.unescape(re.sub(r'<[^>]+>', '', m))
          for m in re.findall(r'<si>(.*?)</si>', z.read('xl/sharedStrings.xml').decode(), flags=re.S)]
    grid = {}
    for rnum, body in re.findall(r'<row [^>]*r="(\d+)"[^>]*>(.*?)</row>', z.read(sheet).decode(), flags=re.S):
        for col, attr, inner in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', body, flags=re.S):
            v = re.search(r'<v>(.*?)</v>', inner or '')
            grid[(int(rnum), col)] = (ss[int(v.group(1))] if (v and 't="s"' in attr)
                                      else (v.group(1) if v else None))
    return grid


def clean(s):
    return re.sub(r'[· \s]+', ' ', s or '').strip()


def read_hou018():
    g = xlsx_cells(HOU018)
    colnum = lambda c: sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(c)))
    cols = sorted({c for (_, c) in g}, key=colnum)
    lab_col = cols[0]                                   # first used column holds the labels
    labels = {r: clean(g.get((r, lab_col))) for r in {r for (r, _) in g}}
    hdr = {lab: r for r, lab in labels.items()}
    r_year, r_stat, r_type = hdr['Census year'], hdr['Dwelling occupancy status'], hdr['Dwelling type']
    r_nz = [r for r, lab in labels.items() if lab == 'Total - New Zealand by regional council']
    if len(r_nz) != 1:
        raise ValueError("Expected one 'Total - New Zealand by regional council' row in CEN23_HOU_018.")
    recs = []
    for c in cols[2:]:
        y, st, ty, v = clean(g.get((r_year, c))), clean(g.get((r_stat, c))), clean(g.get((r_type, c))), g.get((r_nz[0], c))
        if not y:
            continue
        val = pd.to_numeric(v, errors='coerce')         # '_U ..' = not available
        recs.append(dict(year=int(y), status=STATUS[st], type=TYPE[ty], value=val))
    df = pd.DataFrame(recs)
    return df.pivot_table(index=['year', 'type'], columns='status', values='value', aggfunc='first')


def read_tbt001():
    t = pd.read_csv(TBT001)
    codes = {'do22': 'empty', 'do21': 'away', 'do3': 'under_construction', 'doTotal': 'all_statuses',
             'dt1': 'occupied_private', 'dt2': 'occupied_non_private', 'dtTotal': 'occupied_total'}
    t = t[t['CEN23_TBT_DWD_001'].isin(codes)]
    return t.assign(k=t['CEN23_TBT_DWD_001'].map(codes)).pivot_table(
        index='CEN23_YEAR_001', columns='k', values='OBS_VALUE', aggfunc='first')


def read_2013_quickstats():
    t1 = pd.read_excel(Q2013, sheet_name='Table 1', header=None)
    row = t1[pd.to_numeric(t1[0], errors='coerce') == 2013].iloc[0]
    t2 = pd.read_excel(Q2013, sheet_name='Table 2', header=None)
    nz = t2[t2[0].astype(str).str.strip().str.lower() == 'total new zealand'].iloc[0]
    return dict(occupied=float(row[1]), unoccupied=float(row[4]), under_construction=float(row[5]),
                away=float(nz[4]), empty=float(nz[5]))


def main():
    h = read_hou018()
    checks = []
    # 1. private parts sum to private totals (random rounding)
    for y in (2013, 2018, 2023):
        p = h.loc[(y, 'private')]
        checks.append((f'{y} private: empty + away = unoccupied', p['empty'] + p['away'] - p['unoccupied']))
        checks.append((f'{y} private: occupied + unoccupied + under construction = all',
                       p['occupied'] + p['unoccupied'] + p['under_construction'] - p['all_statuses']))
    # 2. all-type totals agree with the independent TBT_001 export
    t = read_tbt001()
    for y in (2018, 2023):
        for k in ('empty', 'away', 'under_construction', 'all_statuses'):
            checks.append((f'{y} total {k}: HOU_018 vs TBT_001', h.loc[(y, 'total'), k] - t.loc[y, k]))
        checks.append((f'{y} occupied private: HOU_018 vs TBT_001', h.loc[(y, 'private'), 'occupied'] - t.loc[y, 'occupied_private']))
    # 3. 2013 private equals the QuickStats file the model uses for 1981-2013
    q = read_2013_quickstats()
    for k in ('occupied', 'unoccupied', 'empty', 'away', 'under_construction'):
        checks.append((f'2013 private {k}: HOU_018 vs QuickStats', h.loc[(2013, 'private'), k] - q[k]))
    bad = [(lab, d) for lab, d in checks if pd.notna(d) and abs(d) > ROUNDING_TOL]
    for lab, d in checks:
        print(f'  [check] {lab}: difference {d:+.0f}')
    if bad:
        raise ValueError(f'Census cross-checks failed: {bad}')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    h.reset_index().to_csv(OUT, index=False)
    print(f'{os.path.basename(HOU018)} -> {OUT}; {len(checks)} cross-checks within +/-{ROUNDING_TOL} (random rounding)')
    np_ = h.xs('non_private', level='type')
    print('non-private dwellings included in all-type unoccupied counts (new from 2018): '
          + ', '.join(f"{y} {np_.loc[y, 'unoccupied']:,.0f}" for y in (2018, 2023)))


if __name__ == '__main__':
    main()
