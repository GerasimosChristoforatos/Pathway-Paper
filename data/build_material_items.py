"""
Build the item-level (EPD-level) case-study LCA table used for the item-level
material decarbonisation of A1-A3 (projection.DECARB_MODE = 'horup_item'). No values
typed by hand.

Source (provenance in data/raw/MANIFEST.csv):
  data/raw/epd-level_materials.xlsx, sheet 'ROOOOOT' (header in row 2), supplied
  by the author: the 16 case-study LCAs of Christoforatos & Pickering (2025),
  Smart and Sustainable Built Environment, https://doi.org/10.1108/SASBE-06-2025-0304,
  one row per building element and EPD item, absolute kg CO2e per building,
  by life-cycle stage. data/building_data.xlsx (sheet 1) is the same data
  pivoted by building x material class.

Processing (all recorded here and in ASSUMPTIONS):
  * the item name (column EPD) and the class (column MATERIAL) are stripped of
    leading/trailing whitespace: five distinct item names in the source (34
    rows) end with a space (four aluminium items and the ceramic WC); the count
    is printed;
  * rows of the same building, class and item (the same EPD used in several
    elements) are summed; the number of source rows is kept in n_rows.

Check: summed by building x class, every stage (A1-A3, A4-A5, B2/B4, C1-C4, D)
equals data/building_data.xlsx sheet 1 (relative tolerance 1e-9). The run
stops otherwise.

Output: data/derived/material_items.csv
  id, typology_label, class, item, n_rows, A1-A3, A4-A5, B2,B4, C1-C4, D
  (absolute kg CO2e per case-study building)
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, 'raw', 'epd-level_materials.xlsx')
OUT = os.path.join(HERE, 'derived', 'material_items.csv')
SHEET = 'ROOOOOT'
STAGE_COLS = {'GWP_A1-A3_total': 'A1-A3', 'GWP_A4-A5_total': 'A4-A5', 'GWP_B2, B4_total': 'B2,B4',
              'GWP_C1-C4_total': 'C1-C4', 'GWP_D_total': 'D'}
TYPOLOGY_LABEL = {'A': 'Apartments', 'T': 'Townhouses', 'DD': '2-st Detached', 'SD': '1-st Detached'}


def main():
    x = pd.read_excel(SRC, sheet_name=SHEET, header=1)
    x = x.dropna(subset=['Code'])
    missing = set(STAGE_COLS) - set(x.columns)
    if missing:
        raise ValueError(f'{SRC}: columns {missing} not found.')
    n_ws = int(((x['EPD'] != x['EPD'].str.strip()) | (x['MATERIAL'] != x['MATERIAL'].str.strip())).sum())
    x['EPD'] = x['EPD'].str.strip()
    x['MATERIAL'] = x['MATERIAL'].str.strip()
    lab = x['Code'].map(lambda i: TYPOLOGY_LABEL[i.rsplit('_', 1)[0]])
    if (lab != x['Typology']).any():
        raise ValueError('Typology column inconsistent with the building code.')
    x = x.rename(columns={'Code': 'id', 'Typology': 'typology_label', 'MATERIAL': 'class', 'EPD': 'item',
                          **STAGE_COLS})
    stages = list(STAGE_COLS.values())
    x[stages] = x[stages].astype(float).fillna(0.0)
    keys = ['id', 'typology_label', 'class', 'item']
    d = x.groupby(keys, sort=True)[stages].sum()
    d.insert(0, 'n_rows', x.groupby(keys, sort=True).size())
    d = d.reset_index()

    # check against building_data.xlsx (building x class, all stages)
    sys.path.insert(0, ROOT)
    import Building_factors as BF
    ref = BF.load_lca().groupby(['id', 'material'])[BF.ALL_STAGES].sum()
    got = d.groupby(['id', 'class'])[stages].sum()
    got.index.names = ['id', 'material']
    got.columns = BF.ALL_STAGES
    if set(ref.index) != set(got.index):
        raise ValueError(f'building x class pairs differ: only in workbook {sorted(set(ref.index) - set(got.index))}, '
                         f'only in items {sorted(set(got.index) - set(ref.index))}.')
    got = got.reindex(ref.index)
    rel = np.abs(got.values - ref.values) / np.maximum(np.abs(ref.values), 1e-12)
    rel[np.abs(ref.values) < 1e-9] = np.abs(got.values - ref.values)[np.abs(ref.values) < 1e-9]
    if rel.max() > 1e-9:
        raise ValueError(f'Item table differs from building_data.xlsx (max relative difference {rel.max():g}).')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    d.to_csv(OUT, index=False)
    print(f'{len(x)} source rows, {len(d)} building x item rows, {d[["class", "item"]].drop_duplicates().shape[0]} '
          f'distinct class x item pairs, {d["id"].nunique()} buildings; {n_ws} source rows had item/class names '
          f'with leading/trailing whitespace (stripped).')
    print(f'Check against building_data.xlsx sheet 1 (building x class, {", ".join(stages)}): '
          f'max relative difference {rel.max():.1e}.')
    print(f'Written: {OUT}')


if __name__ == '__main__':
    main()
