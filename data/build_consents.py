"""
Build the monthly consent input from the raw Stats NZ data. No values are typed by hand.

Source (MODEL v4.6.0 data freeze, consents to September 2026; unmodified in data/raw/, MANIFEST.csv):
  data/raw/BLD468601_20261111_075751_49.csv: Stats NZ Infoshare, Building consents - BLD, "Building consents by
  region (Monthly)", New Zealand, New, Actual: Dwelling units (Number, Value, Floor area; from 1965M04) and Houses /
  Apartments / Retirement village units / Townhouses, flats, units, and other dwellings (Number, Value, Floor area;
  from 1990M04), 1965M04-2026M09. Wide Infoshare layout: six header rows (title, area, building type, New, Actual,
  measure), one row per month 'YYYYMmm', '..' = missing, footer notes after the last month. Read by read_infoshare().

Earlier source (MODEL v4.0-v4.5, kept for provenance; read by extract()): Stats NZ, "Building consents issued: July
  2026", Download data -> CSV zip, file "Building consents by region (Monthly).csv"; Series_title_1 = 'New Zealand',
  Series_title_3 = 'New', Series_title_5 = 'Actual', Series_title_2 in the building types below, Series_title_4 in
  Number / Floor area / Value.

Written to data/derived/consents_monthly.csv with the column names the model uses (the layout of the workbook supplied before MODEL v4.0, plus the
retirement-village columns): Dwellings = Dwelling units, New, Number; Detached = Houses; Townhouses = Townhouses,
flats, units, and other dwellings; Apartments; RetirementVillage = Retirement village units; 'Consents - Consents'
(and GFA, Value) = the sum of Detached, Townhouses and Apartments (the model scope).

Before overwriting, the new months are compared with the existing derived file: every Stats NZ revision (month,
column, old, new) is written to data/derived/consents_revisions.csv, and the script STOPs if any month before 2024
differs by more than 1%.

    python data/build_consents.py [path/to/BLD468601_*.csv | path/to/building-consents-issued-<month>.zip]
"""
import glob
import os
import sys
import zipfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT = os.path.join(HERE, 'derived', 'consents_monthly.csv')
MEMBER = 'Building consents by region (Monthly).csv'

TYPES = {  # Stats NZ building type -> model name
    'Houses': 'Detached',
    'Townhouses, flats, units, and other dwellings': 'Townhouses',
    'Apartments': 'Apartments',
    'Retirement village units': 'RetirementVillage',
    'Dwelling units': 'AllDwellings',
}
MEASURES = {'Number': 'Consents', 'Floor area': 'GFA', 'Value': 'Value'}


REVISIONS = os.path.join(HERE, 'derived', 'consents_revisions.csv')
REVISION_STOP_BEFORE = 2024        # a revision above REVISION_STOP_REL in a month before this year stops the build
REVISION_STOP_REL = 0.01
INFOSHARE = 'BLD468601_*.csv'
INFOSHARE_TYPES = {  # Infoshare header (row 3) -> model name
    'Dwelling units': 'AllDwellings', 'Houses': 'Detached', 'Apartments': 'Apartments',
    'Retirement village units': 'RetirementVillage', 'Townhouses, flats, units, and other dwellings': 'Townhouses',
}


def latest_source():
    """The Infoshare export (MODEL v4.6.0 freeze) if present, else the latest release zip (earlier versions)."""
    for pat in (INFOSHARE, 'building-consents-issued-*.zip'):
        z = sorted(glob.glob(os.path.join(RAW, pat)))
        if z:
            return z[-1]
    sys.exit(f'No {INFOSHARE} or building-consents-issued-*.zip in {RAW}.')


def read_infoshare(path):
    """The wide Infoshare layout -> the same wide frame as extract() (columns 'Consents/Detached', ...; float, NaN
    where '..'). Status flags are not in this export, so the status frame is empty."""
    raw = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
    head = raw.iloc[:6]
    if head.iloc[0, 0] != 'Building consents by region (Monthly)' or head.iloc[1, 1] != 'New Zealand':
        raise ValueError(f'{os.path.basename(path)}: not the New Zealand "Building consents by region (Monthly)" table.')
    btype = head.iloc[2].replace('', pd.NA).ffill()
    cols = {}
    for j in range(1, raw.shape[1]):
        if head.iloc[3, j] not in ('New', '') or head.iloc[4, j] not in ('Actual', ''):
            raise ValueError(f'column {j}: expected New / Actual, got {head.iloc[3, j]!r} / {head.iloc[4, j]!r}')
        t, m = btype.iloc[j], head.iloc[5, j]
        if t not in INFOSHARE_TYPES or m not in MEASURES:
            raise ValueError(f'column {j}: unknown building type / measure {t!r} / {m!r}')
        cols[j] = f'{MEASURES[m]}/{INFOSHARE_TYPES[t]}'
    if len(set(cols.values())) != len(cols) or len(cols) != 15:
        raise ValueError(f'expected 15 distinct series, got {sorted(cols.values())}')
    body = raw.iloc[6:]
    body = body[body.iloc[:, 0].str.fullmatch(r'\d{4}M\d{2}')]
    idx = pd.to_datetime(body.iloc[:, 0].str.replace('M', '-', regex=False) + '-01')
    wide = pd.DataFrame({c: pd.to_numeric(body.iloc[:, j].replace('..', pd.NA), errors='raise').values
                         for j, c in cols.items()}, index=idx).astype(float).sort_index()
    wide.index.name = 'Date'
    if not wide.index.is_monotonic_increasing or wide.index.duplicated().any():
        raise ValueError('months not unique / increasing')
    full = pd.date_range(wide.index.min(), wide.index.max(), freq='MS')
    if len(full) != len(wide):
        raise ValueError('months missing in the Infoshare export')
    return wide, pd.DataFrame(index=wide.index)


def revisions(old_path, new):
    """Every cell of the existing derived file that the new data change (months present in both)."""
    old = pd.read_csv(old_path, index_col='Date', parse_dates=True)
    if list(old.columns) != list(new.columns):
        raise ValueError(f'column layout changed: {list(old.columns)} -> {list(new.columns)}')
    common = old.index.intersection(new.index)
    if len(common) != len(old):
        raise ValueError(f'months of the existing file missing from the new data: {old.index.difference(new.index)}')
    a, b = old.loc[common], new.loc[common]
    diff = ~((a == b) | (a.isna() & b.isna()))
    rows = [dict(month=f'{d:%Y-%m}', column=c, old=a.at[d, c], new=b.at[d, c],
                 rel=(b.at[d, c] - a.at[d, c]) / a.at[d, c] if a.at[d, c] else float('nan'))
            for (d, c), v in diff.stack().items() if v]
    return pd.DataFrame(rows, columns=['month', 'column', 'old', 'new', 'rel']), common


def extract(path):
    keep = []
    with zipfile.ZipFile(path) as zf, zf.open(MEMBER) as f:
        for chunk in pd.read_csv(f, chunksize=500_000, dtype={'Period': str}):
            m = ((chunk['Series_title_1'] == 'New Zealand') & (chunk['Series_title_3'] == 'New')
                 & (chunk['Series_title_5'] == 'Actual') & chunk['Series_title_2'].isin(TYPES)
                 & chunk['Series_title_4'].isin(MEASURES))
            keep.append(chunk[m])
    df = pd.concat(keep)
    if df.duplicated(['Series_title_2', 'Series_title_4', 'Period']).any():
        raise ValueError('Duplicate series/period rows in the extract.')
    # Period is YYYY.MM (text, so October stays '.10')
    df['Date'] = pd.to_datetime(df['Period'].str.replace('.', '-', regex=False) + '-01')
    df['col'] = df['Series_title_4'].map(MEASURES) + '/' + df['Series_title_2'].map(TYPES)
    wide = df.pivot(index='Date', columns='col', values='Data_value').sort_index()
    status = df.pivot(index='Date', columns='col', values='Status').sort_index()
    return wide, status


def to_model_layout(w):
    out = pd.DataFrame(index=w.index)
    for m in ('Consents', 'GFA', 'Value'):
        parts = [f'{m}/{t}' for t in ('Apartments', 'Detached', 'Townhouses')]
        out[f'{m} - {m}'] = w[parts].sum(axis=1, min_count=3)       # three typologies (model scope)
        for t in ('Apartments', 'Detached', 'Townhouses'):
            out[f'{m} - {m}/{t}'] = w[f'{m}/{t}']
        out[f'{m} - {m}/RetirementVillage'] = w[f'{m}/RetirementVillage']
    out['Dwellings'] = w['Consents/AllDwellings']
    out.index.name = 'Date'
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else latest_source()
    w, status = (read_infoshare if path.endswith('.csv') else extract)(path)
    out = to_model_layout(w)
    if os.path.exists(OUT):
        rev, common = revisions(OUT, out)
        bad = rev[(pd.to_datetime(rev['month']).dt.year < REVISION_STOP_BEFORE)
                  & ~(rev['rel'].abs() <= REVISION_STOP_REL)]
        if len(bad):
            raise SystemExit(f'STOP: Stats NZ revisions above {REVISION_STOP_REL:.0%} before {REVISION_STOP_BEFORE}:\n'
                             f'{bad.to_string(index=False)}')
        rev.to_csv(REVISIONS, index=False)
        print(f'compared with the existing {os.path.basename(OUT)} ({common.min():%Y-%m} .. {common.max():%Y-%m}): '
              f'{len(rev)} revised cells in {rev["month"].nunique()} months -> {REVISIONS}')
    # consistency: the four dwelling types sum to 'Dwelling units' every month
    four = w[[f'Consents/{t}' for t in ('Detached', 'Townhouses', 'Apartments', 'RetirementVillage')]].sum(axis=1, min_count=4)
    gap = (four - w['Consents/AllDwellings']).abs().max()     # months with all four types (from 1990-04)
    if gap > 0:
        raise ValueError(f'Dwelling types do not sum to Dwelling units (max gap {gap}).')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT)
    prov = status.iloc[:, 0] if status.shape[1] else pd.Series(dtype=str)
    print(f'{os.path.basename(path)} -> {OUT}: {out.index.min():%Y-%m} .. {out.index.max():%Y-%m}, '
          f'{len(out)} months; 4 types sum to Dwelling units in every month; '
          f'provisional months: {", ".join(f"{d:%Y-%m}" for d in prov.index[prov == "P"]) or "none flagged in the source"}')


if __name__ == '__main__':
    main()
