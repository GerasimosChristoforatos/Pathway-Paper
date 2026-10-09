"""
Build the replacement / repaint event table (time-resolved B2, B4) from the
LCAQuick root tables of the 16 case studies. No values typed by hand.

Source (provenance in data/raw/MANIFEST.csv):
  data/raw/Analytical_LCA_Results_Database.xlsx, supplied by the author: LCAQuick
  v3.6 root tables of the case studies of Christoforatos & Pickering (2025), one
  sheet per building (sheets T1_H, T2_W, T3_P are the model's T_1, T_2, T_3).
  Per line: no_of_full_replacements, no_of_repaints and GWP by stage (kg CO2e per
  building); per sheet: 'Building Lifespan' and 'GFA Approx.'.

What is taken from it (author decision): ONLY the event counts and the building
lifespan. Stage totals stay those of data/building_data.xlsx and of the item table
data/raw/epd-level_materials.xlsx (data/derived/material_items.csv), so the
factors of baseline-pb-v2 are unchanged. Each workbook line is matched one-to-one
to a row of the item table by building, item, B2/B4 and A1-A3 (to 1e-3 kg); the
item table gives its material class.

Excluded (16 lines, none carries B2/B4; listed in data/derived/lca_excluded_lines.csv):
  * 'Sand' and 'Granular fill' lines (12): site works, outside the case-study scope;
  * three unlabelled lines (no family, type, code or item): A_1 (A1-A3 ≈ 408 t, as
    in v2 and in the sheet's own summary) and DD_2 (0.96 and 733.44 kg A1-A3);
  * the T_1 aluminium window-frame line, whose A1-A3 (5,241.24 kg) differs by 10 kg
    from the item table (5,231.24 kg; the item table is kept); its counts are
    informational (no B2/B4).
Several sheet summary blocks (DD_2, DD_3, SD_3, SD_5, SD_6, T_4) do not equal their
own line sums; the line-level data are used.

Events (author decisions):
  * replacement lines (no_of_full_replacements n > 0, any class): n events, each
    = line B / n, on the item's own decarbonisation path. The 21 Colorsteel roof
    lines with 1 replacement and 1 repaint are one replacement event carrying the
    full line B (their B is 2.3-3.1% above one replacement of the initial stages;
    the repaint would fall in the same year);
  * PAINT lines with no_of_repaints m > 0: m events, each = line B / m, on the
    paint path;
  * non-paint lines with repaints only and B > 0 (three ZinaCore lines, T_1-T_3):
    m repaint events of B / m on the paint path (the emission is recoating);
  * other non-paint repaint counts carry no B (informational; no events).
Check: every line with B2/B4 > 0 has events; no event line has B2/B4 = 0.

Output: data/derived/lca_events.csv
  id, line, class, item, A1-A3, A4-A5, B2,B4, C1-C4, n_replacements, n_repaints,
  lifespan, event_type ('replacement' | 'repaint' | ''), n_events, event_path ('item' | 'paint' | '')
"""
import os
from collections import defaultdict

import numpy as np
import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, 'raw', 'Analytical_LCA_Results_Database.xlsx')
ITEMS_SRC = os.path.join(HERE, 'raw', 'epd-level_materials.xlsx')
OUT = os.path.join(HERE, 'derived', 'lca_events.csv')
OUT_EXCL = os.path.join(HERE, 'derived', 'lca_excluded_lines.csv')
SHEET_ID = {'T1_H': 'T_1', 'T2_W': 'T_2', 'T3_P': 'T_3'}
STAGES = {'GWP_A1-A3_total': 'A1-A3', 'GWP_A4-A5_total': 'A4-A5', 'GWP_B2, B4_total': 'B2,B4',
          'GWP_C1-C4_total': 'C1-C4'}
HEADER = ['family', 'type', 'code', 'code_description', 'unit_for_calculation', 'no_of_full_replacements',
          'no_of_repaints', *STAGES]
META = ('Building Lifespan', 'GFA Approx.')
SITE_WORKS = ('Sand', 'Granular fill')
N_EXCLUDED = 16


def cell(v):
    return '' if v is None else str(v).strip()


def read_sheet(ws):
    """Item lines of one root table: locate the header row and the lifespan / GFA
    fields programmatically (layouts differ); fail loudly if not found."""
    rows = list(ws.iter_rows(values_only=True))
    hdr = next((i for i, r in enumerate(rows) if r and 'family' in [cell(v) for v in r]), None)
    if hdr is None:
        raise ValueError(f'{ws.title}: item header row (family, type, ...) not found.')
    head = [cell(v) for v in rows[hdr]]
    missing = [h for h in HEADER if h not in head]
    if missing:
        raise ValueError(f'{ws.title}: header columns {missing} not found.')
    meta = {}
    for r in rows[:hdr]:
        c = [cell(v) for v in r]
        for j, x in enumerate(c):
            if x in META and j + 1 < len(c):
                meta[x] = float(c[j + 1])
    if set(meta) != set(META):
        raise ValueError(f'{ws.title}: fields {sorted(set(META) - set(meta))} not found.')
    col = {h: head.index(h) for h in HEADER}
    out = []
    for k, r in enumerate(rows[hdr + 1:]):
        if not r or all(v is None for v in r):
            continue
        d = {h: r[i] for h, i in col.items()}
        out.append(dict(line=k, family=cell(d['family']), item=cell(d['code_description']),
                        n_replacements=float(d['no_of_full_replacements'] or 0),
                        n_repaints=float(d['no_of_repaints'] or 0),
                        **{s: float(d[c] or 0) for c, s in STAGES.items()}))
    return out, meta


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    lines, meta = [], {}
    for ws in wb.worksheets:
        bid = SHEET_ID.get(ws.title, ws.title)
        rows, m = read_sheet(ws)
        meta[bid] = m
        lines += [dict(r, id=bid) for r in rows]
    d = pd.DataFrame(lines)

    it = pd.read_excel(ITEMS_SRC, sheet_name=0, header=1).dropna(subset=['Code'])
    it['EPD'] = it['EPD'].str.strip()
    it = it.fillna({c: 0.0 for c in STAGES})
    pool = defaultdict(list)
    for _, r in it.iterrows():
        pool[(r['Code'], r['EPD'], round(float(r['GWP_B2, B4_total']), 3),
              round(float(r['GWP_A1-A3_total']), 3))].append(r['MATERIAL'].strip())
    d['class'] = [pool[k].pop() if pool[k] else None
                  for k in zip(d['id'], d['item'], [round(float(v), 3) for v in d['B2,B4']],
                               [round(float(v), 3) for v in d['A1-A3']])]
    left = [(k, v) for k, v in pool.items() for _ in v]
    excl = d[d['class'].isna()].copy()
    if len(excl) != N_EXCLUDED or (excl['B2,B4'] != 0).any():
        raise ValueError(f'{len(excl)} unmatched lines (expected {N_EXCLUDED}), B2/B4 on them '
                         f'{excl["B2,B4"].sum():g}.')
    if len(left) != 1 or left[0][0][:2] != ('T_1', excl.loc[excl['id'] == 'T_1', 'item'].iloc[0]):
        raise ValueError(f'Item-table rows left unmatched: {left}.')
    excl['reason'] = np.where(excl['item'].isin(SITE_WORKS), 'site works (sand / granular fill), outside scope',
                     np.where(excl['item'].isin(['', 'None', 'nan']), 'unlabelled line (no family, type, code, item)',
                              'A1-A3 differs from the item table by 10 kg (item table kept)'))

    d = d[d['class'].notna()].copy()
    d['lifespan'] = d['id'].map(lambda b: meta[b]['Building Lifespan'])
    # the matched lines reproduce the item table by building x class x item, every stage
    # (except the T_1 aluminium row, whose workbook line is excluded)
    it['MATERIAL'] = it['MATERIAL'].str.strip()
    item_sum = it.groupby(['Code', 'MATERIAL', 'EPD'])[list(STAGES)].sum()
    item_sum.columns = list(STAGES.values())
    line_sum = d.groupby(['id', 'class', 'item'])[list(STAGES.values())].sum()
    line_sum.index.names = item_sum.index.names
    j = item_sum.join(line_sum, rsuffix='_lines', how='outer').fillna(0.0)
    worst = {s: float((j[s] - j[f'{s}_lines']).abs().max()) for s in STAGES.values()}
    if worst['B2,B4'] > 1e-6:
        raise ValueError(f'B2/B4 of the matched lines differs from the item table by {worst["B2,B4"]:g} kg.')
    diff = np.abs(j[list(STAGES.values())].values - j[[f'{s}_lines' for s in STAGES.values()]].values)
    bad = j[diff.max(axis=1) > 1e-6]
    if len(bad) != 1 or bad.index[0][0] != 'T_1':
        raise ValueError(f'Matched lines do not reproduce the item table: {list(bad.index)}.')

    paint = d['class'] == 'PAINT'
    rep = d['n_replacements'] > 0
    rpt = (d['n_repaints'] > 0) & (paint | ((d['B2,B4'] > 0) & ~rep))
    d['event_type'] = np.where(rep, 'replacement', np.where(rpt, 'repaint', ''))
    d['n_events'] = np.where(rep, d['n_replacements'], np.where(rpt, d['n_repaints'], 0.0))
    d['event_path'] = np.where(rep, 'item', np.where(rpt, 'paint', ''))
    if ((d['B2,B4'] > 0) & (d['n_events'] == 0)).any() or ((d['n_events'] > 0) & (d['B2,B4'] == 0)).any():
        raise ValueError('Event lines and lines carrying B2/B4 differ.')
    if (paint & rep).any():
        raise ValueError('A PAINT line has full replacements.')

    cols = ['id', 'line', 'class', 'item', 'A1-A3', 'A4-A5', 'B2,B4', 'C1-C4', 'n_replacements', 'n_repaints',
            'lifespan', 'event_type', 'n_events', 'event_path']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    d[cols].to_csv(OUT, index=False)
    excl[['id', 'line', 'family', 'item', 'A1-A3', 'A4-A5', 'B2,B4', 'C1-C4', 'reason']].to_csv(OUT_EXCL, index=False)

    # report
    ini = d['A1-A3'] + d['A4-A5'] + d['C1-C4']
    only_rep = rep & (d['n_repaints'] == 0)
    both = rep & (d['n_repaints'] > 0)
    r1 = d.loc[only_rep, 'B2,B4'] / (d.loc[only_rep, 'n_replacements'] * ini[only_rep])
    r2 = d.loc[both, 'B2,B4'] / (d.loc[both, 'n_replacements'] * ini[both])
    pl = paint & (d['n_repaints'] > 0)
    r3 = d.loc[pl, 'B2,B4'] / (d.loc[pl, 'n_repaints'] * ini[pl])
    host = ~paint & (d['n_repaints'] > 0) & ~rep
    print(f'{len(d) + len(excl)} workbook lines, {len(d)} matched to the item table, {len(excl)} excluded '
          f'(none carries B2/B4): {excl["reason"].value_counts().to_dict()}')
    print(f'lifespans: {sorted(set(m["Building Lifespan"] for m in meta.values()))} years')
    print(f'replacement-only lines {int(only_rep.sum())}: B / (n x (A1-A3 + A4-A5 + C1-C4)) median {r1.median():.4f}, '
          f'range {r1.min():.4f}-{r1.max():.4f}')
    print(f'replacement + repaint lines {int(both.sum())} (Colorsteel): ratio {r2.min():.4f}-{r2.max():.4f}; '
          'one replacement event carrying the full line B')
    print(f'PAINT lines with repaints {int(pl.sum())}: per-event B / initial median {r3.median():.3f}, range '
          f'{r3.min():.3f}-{r3.max():.3f}; B {d.loc[pl, "B2,B4"].sum() / 1e3:,.1f} t')
    print(f'non-paint lines with repaints and no replacement {int(host.sum())}: B {d.loc[host, "B2,B4"].sum():,.0f} kg '
          f'on {int((host & (d["B2,B4"] > 0)).sum())} lines (repaint events on the paint path); the rest informational')
    print(f'event lines {int((d["n_events"] > 0).sum())}, B2/B4 total {d["B2,B4"].sum() / 1e3:,.1f} t; written {OUT}')


if __name__ == '__main__':
    main()
