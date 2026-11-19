"""
Build the material decarbonisation paths of Horup et al. (2025) from their
supplementary material. No values typed by hand.

Source (provenance in data/raw/MANIFEST.csv; the file itself is kept in refs/,
which is git-ignored):
  refs/Horup_2025_SI_mmc1.xlsx
  Horup L, Bruhn S, Hoxha E, Birgisdottir H, Secher AQ, Ohms P, Hauschild M
  (2025). Absolute sustainability assessment of the Danish building sector
  through prospective LCA. Sci. Total Environ. 966, 178780. Supplementary
  material (mmc1.xlsx), sheet 'Table S4' (in-sheet title 'Table S3: Material
  analysis (extended) of GWP by applying prospective background system').

For each material the sheet gives, in column C, the premise result (average of
the 9 scenarios) relative to ecoinvent 3.9.1 in 2025, 2030, 2040 and 2050, and
in column E the 'average mitigation potential 2025-2050'. The path relative to
2025 is C(t) / C(2025); the script checks that 1 - C(2050)/C(2025) equals
column E for every material.

Output: data/derived/horup2025_table_s4.csv
  material, year, premise_rel_ecoinvent, rel_to_2025, cell

Second output (MODEL v4.9.0, lever L10): the archetype sensitivity of sheet 'Table S3' (in-sheet title 'Table S3:
Sensitivity of archetypes used of GWP'): GWP per m2 of each Danish archetype by year 2025-2050 in three blocks,
'AVERAGE GWP per sqm', 'MIN GWP per sqm' and 'MAX GWP per sqm', over the 9 prospective backgrounds of 'Table S1'
(SSP1 / SSP2 / SSP5 x no climate policy / RCP2.6 / RCP1.9). Only 'Single family houses ' and 'Multi dwellings ' are
read (the trailing spaces are in the sheet).

Output: data/derived/horup2025_table_s3_archetypes.csv
  archetype, stat (avg | min | max), year, gwp_per_m2, rel_to_2025, cell
"""
import os

import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'refs', 'Horup_2025_SI_mmc1.xlsx')
OUT = os.path.join(HERE, 'derived', 'horup2025_table_s4.csv')
SHEET = 'Table S4'
YEARS = (2025, 2030, 2040, 2050)

# ---- Table S3 (archetypes; MODEL v4.9.0, L10) ----
OUT_S3 = os.path.join(HERE, 'derived', 'horup2025_table_s3_archetypes.csv')
SHEET_S3 = 'Table S3'
S3_TITLE = 'Table S3: Sensitivity of archetypes used of GWP'
S3_BLOCKS = {'avg': 'AVERAGE GWP per sqm', 'min': 'MIN GWP per sqm', 'max': 'MAX GWP per sqm'}
S3_ARCHETYPES = {'Single family houses ': 'Single family houses', 'Multi dwellings ': 'Multi dwellings'}
S3_YEARS = tuple(range(2025, 2051))
# check values (rel_to_2025 in 2050, each path on its own 2025 value; Horup et al. 2025, Table S3), tolerance 5e-4
S3_CHECK_2050 = {('Single family houses', 'avg'): 0.754, ('Single family houses', 'min'): 0.689,
                 ('Single family houses', 'max'): 0.953, ('Multi dwellings', 'avg'): 0.774,
                 ('Multi dwellings', 'min'): 0.670, ('Multi dwellings', 'max'): 0.952}
S3_TOL = 5e-4
SHEET_S1 = 'Table S1'
S1_SCENARIOS = ('SSP1-None', 'SSP2-None (eq. to RCP6)', 'SSP5-None', 'SSP1-RCP2.6', 'SSP2-RCP2.6', 'SSP5-RCP2.6',
                'SSP1-RCP1.9', 'SSP2-RCP1.9', 'SSP5-RCP1.9')
S3_NOTE = ('Horup et al. (2025) Sci. Total Environ. 966, 178780, supplementary mmc1.xlsx, sheet Table S3 (blocks '
           'AVERAGE / MIN / MAX GWP per sqm) over the 9 prospective backgrounds of sheet Table S1: '
           + '; '.join(S1_SCENARIOS) + '. Written by data/build_horup.py.')


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f'{SRC} not found (refs/ is not versioned; see data/raw/MANIFEST.csv).')
    ws = openpyxl.load_workbook(SRC, data_only=True)[SHEET]
    if 'Premise (average) relative to Ecoinvent' not in str(ws['C2'].value):
        raise ValueError(f'Unexpected header C2 = {ws["C2"].value!r}.')
    rows, cur, mitigation = [], None, {}
    for r in range(1, ws.max_row + 1):
        name, year, val = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value
        if year == YEARS[0]:
            cur = str(name).strip()
        if cur and year in YEARS:
            rows.append(dict(material=cur, year=int(year), premise_rel_ecoinvent=float(val), cell=f'C{r}'))
            if year == YEARS[-1]:
                mitigation[cur] = float(ws.cell(r, 5).value)
    d = pd.DataFrame(rows)
    if (d.groupby('material').size() != len(YEARS)).any():
        raise ValueError('A material lacks one of the years 2025/2030/2040/2050.')
    base = d[d['year'] == YEARS[0]].set_index('material')['premise_rel_ecoinvent']
    d['rel_to_2025'] = d['premise_rel_ecoinvent'] / d['material'].map(base)
    r50 = d[d['year'] == YEARS[-1]].set_index('material')['rel_to_2025']
    worst = max(abs((1 - r50[m]) - mitigation[m]) for m in r50.index)
    if worst > 1e-12:
        raise ValueError(f'1 - C(2050)/C(2025) differs from column E by {worst:g}.')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    d.to_csv(OUT, index=False)
    print(f'{os.path.basename(SRC)} [{SHEET}] -> {OUT}: {d.material.nunique()} materials; '
          f'1 - C2050/C2025 = column E for all (max difference {worst:.1e})')
    build_s3(openpyxl.load_workbook(SRC, data_only=True))


def build_s3(wb):
    """Table S3 archetype paths (avg / min / max) and the Table S1 scenario list (checked against S1_SCENARIOS)."""
    s1 = wb[SHEET_S1]
    found = [str(s1.cell(r, 2).value).strip() for r in range(1, s1.max_row + 1)
             if str(s1.cell(r, 2).value).strip() in S1_SCENARIOS]
    if tuple(found) != S1_SCENARIOS:
        raise ValueError(f'{SHEET_S1}: scenario list {found} differs from {S1_SCENARIOS}.')
    ws = wb[SHEET_S3]
    if ws['A1'].value != S3_TITLE:
        raise ValueError(f'{SHEET_S3}: unexpected title A1 = {ws["A1"].value!r}.')
    rows = []
    for stat, title in S3_BLOCKS.items():
        hits = [r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == title]
        if len(hits) != 1:
            raise ValueError(f'{SHEET_S3}: block header {title!r} found {len(hits)} times.')
        r0 = hits[0]
        if ws.cell(r0 + 1, 2).value != '1 m2':
            raise ValueError(f'{SHEET_S3}: unit row below {title!r} is {ws.cell(r0 + 1, 2).value!r}, not \'1 m2\'.')
        hdr = r0 + 2
        cols = {int(ws.cell(hdr, c).value): c for c in range(2, ws.max_column + 1)
                if isinstance(ws.cell(hdr, c).value, (int, float))}
        if tuple(sorted(cols)) != S3_YEARS:
            raise ValueError(f'{SHEET_S3}: year header of {title!r} is {sorted(cols)}, not 2025-2050.')
        for r in range(hdr + 1, hdr + 40):
            name = ws.cell(r, 1).value
            if name is None:
                break
            if name in S3_ARCHETYPES:
                for y in S3_YEARS:
                    c = ws.cell(r, cols[y])
                    rows.append(dict(archetype=S3_ARCHETYPES[name], stat=stat, year=y, gwp_per_m2=float(c.value),
                                     cell=c.coordinate))
    d = pd.DataFrame(rows)
    if len(d) != len(S3_BLOCKS) * len(S3_ARCHETYPES) * len(S3_YEARS):
        raise ValueError(f'{SHEET_S3}: {len(d)} values read, expected {3 * 2 * len(S3_YEARS)}.')
    base = d[d['year'] == 2025].set_index(['archetype', 'stat'])['gwp_per_m2']
    d['rel_to_2025'] = d['gwp_per_m2'] / [base[(a, s)] for a, s in zip(d['archetype'], d['stat'])]
    r50 = d[d['year'] == 2050].set_index(['archetype', 'stat'])['rel_to_2025']
    bad = {k: (float(r50[k]), v) for k, v in S3_CHECK_2050.items() if abs(float(r50[k]) - v) > S3_TOL}
    if bad:
        raise ValueError(f'{SHEET_S3}: 2050 values relative to 2025 differ from the check values: {bad}.')
    # envelope consistency: min <= avg <= max in every year (absolute values)
    piv = d.pivot_table(index=['archetype', 'year'], columns='stat', values='gwp_per_m2')
    if not ((piv['min'] <= piv['avg']) & (piv['avg'] <= piv['max'])).all():
        raise ValueError(f'{SHEET_S3}: min <= avg <= max fails in some year.')
    with open(OUT_S3, 'w') as f:
        f.write(f'# {S3_NOTE}\n')
        d[['archetype', 'stat', 'year', 'gwp_per_m2', 'rel_to_2025', 'cell']].to_csv(f, index=False)
    print(f'{os.path.basename(SRC)} [{SHEET_S3}] -> {OUT_S3}: {len(d)} values; 2050 / 2025 = '
          + ', '.join(f'{a} {s} {float(r50[(a, s)]):.4f}' for a, s in S3_CHECK_2050))


if __name__ == '__main__':
    main()
