"""
Build the monthly consent input from the raw Stats NZ release. No values are typed by hand.

Source (downloaded unmodified into data/raw/, see README.md "Data provenance"):
  Stats NZ, "Building consents issued: <Month YYYY>", Download data -> CSV zip,
  file "Building consents by region (Monthly).csv" (Infoshare group
  Building consents - BLD).

Extracted: Series_title_1 = 'New Zealand', Series_title_3 = 'New',
Series_title_5 = 'Actual'; for Series_title_2 in the building types below and
Series_title_4 in Number / Floor area / Value. Written to
data/derived/consents_monthly.csv with the column names the model already
uses (consentdata.xlsx layout), plus the retirement-village columns the
legacy file lacks.

    python data/build_consents.py [path/to/building-consents-issued-<month>.zip]
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


def latest_zip():
    z = sorted(glob.glob(os.path.join(RAW, 'building-consents-issued-*.zip')), key=os.path.getmtime)
    if not z:
        sys.exit(f'No building-consents-issued-*.zip in {RAW}.')
    return z[-1]


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
    path = sys.argv[1] if len(sys.argv) > 1 else latest_zip()
    w, status = extract(path)
    out = to_model_layout(w)
    # consistency: the four dwelling types sum to 'Dwelling units' every month
    four = w[[f'Consents/{t}' for t in ('Detached', 'Townhouses', 'Apartments', 'RetirementVillage')]].sum(axis=1, min_count=4)
    gap = (four - w['Consents/AllDwellings']).abs().max()     # months with all four types (from 1990-04)
    if gap > 0:
        raise ValueError(f'Dwelling types do not sum to Dwelling units (max gap {gap}).')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT)
    prov = status.iloc[:, 0]
    print(f'{os.path.basename(path)} -> {OUT}: {out.index.min():%Y-%m} .. {out.index.max():%Y-%m}, '
          f'{len(out)} months; 4 types sum to Dwelling units in every month; '
          f'provisional months: {", ".join(f"{d:%Y-%m}" for d in prov.index[prov == "P"]) or "none"}')


if __name__ == '__main__':
    main()
