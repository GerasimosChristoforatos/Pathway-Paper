"""
BUILDING FACTORS -- per-typology embodied-carbon factors from 16 case studies
============================================================================
Reads the case-study LCA results and writes the factor tables that Boss.py
consumes. Run this whenever the case-study data change; Boss reads only the
CSV outputs, never the workbooks.

OUTPUTS
  factors_material.csv   kg CO2e / m2 GFA, by typology x material x life-cycle
                         stage. Module D is written but flagged, never summed
                         into the headline.
  factors_typology.csv   one row per typology: occupancy load factor, design
                         occupants, floor space index, soil carbon loss
                         (average / low / high) and the embodied total.

POOLING
  Factors are intensities (kg/m2), so they are scale-invariant. Buildings are
  pooled with equal weight, after first averaging within detached sub-types so
  the six single-storey cases do not outvote the four two-storey ones
  ('equal_subtypes'). 'equal_buildings' and 'gfa_weighted' are available for
  sensitivity; on this data all three agree within ~1%.

SOIL
  Soil organic carbon loss is NOT a material. It is land-use change:
      SOC [kg/m2 GFA] = L_w [kg/m2 footprint] / floor space index
  It is kept as its own line so that no material decarbonisation rate is ever
  applied to it, and so that densification (a higher floor space index) reduces
  it automatically.

KNOWN DATA ISSUES, handled explicitly below
  1. T_4's absolute emissions are for the whole 887 m2 block, while the
     characteristics sheet reports it scaled to one 147.8 m2 dwelling. The
     block area is used for the per-m2 conversion; a reconciliation check
     against the published per-building intensities prints at runtime.
  2. The published case-study soil figures imply L_w = 58.406, while the soils
     sheet gives 58.769 (a systematic 0.62% difference). The sheet value is
     used; the discrepancy is reported.
"""

import os
import re
import numpy as np
import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================
DATA_DIR = 'data'
FILE_LCA = os.path.join(DATA_DIR, 'building_data.xlsx')   # one workbook, three sheets
SHEET_LCA = '1'                          # materials x stages, absolute kg CO2e
FILE_CHARS = FILE_LCA
SHEET_CHARS = '2'                        # GFA, occupancy load factor, footprint
SHEET_SOILS = '3'                        # soil carbon by soil order

OUT_MATERIAL = os.path.join(DATA_DIR, 'factors_material.csv')
OUT_TYPOLOGY = os.path.join(DATA_DIR, 'factors_typology.csv')

WEIGHT_SCHEME = 'equal_subtypes'         # 'equal_subtypes' | 'equal_buildings' | 'gfa_weighted'

STAGES = ['A1-A3', 'A4-A5', 'B2,B4', 'C1-C4']     # in scope
STAGE_D = 'D'                                      # outside the boundary
ALL_STAGES = STAGES + [STAGE_D]

# Materials reported in their own right. Everything else is binned into
# 'Others'. A material earns a line if it is a meaningful share of at least one
# typology AND a distinct decarbonisation rate for it is defensible.
# Only physically comparable materials are merged: the two concretes, and
# plastics with paint (both polymer/coating products). Glass, bricks, aluminium
# and the rest keep their identity inside 'Others' and are reported at full
# resolution in the supplementary table.
MATERIAL_GROUPS = {
    'CONCRETE (incl. reinforced)': ['CONCRETE', 'REINFORCED CONCRETE'],
    'STEEL':                       ['STEEL'],
    'TIMBER':                      ['TIMBER'],
    'PLASTICS & PAINT':            ['PLASTICS', 'PAINT'],
    'PLASTERBOARD':                ['PLASTERBOARD'],
}
OTHERS_LABEL = 'OTHERS'

# Dwellings per case study, where a case is a block rather than one dwelling.
# Used only to express design occupants per dwelling; everything else is an
# intensity and therefore scale-invariant.
DWELLINGS_PER_CASE = {'A_1': 63, 'A_2': 63, 'T_4': 6}

TYPOLOGY_OF = {'A': 'Apartments', 'T': 'Townhouses', 'DD': 'Detached', 'SD': 'Detached'}
SUBTYPE_OF = {'A': 'Apartment', 'T': 'Townhouse',
              'DD': '2-storey Detached', 'SD': '1-storey Detached'}
TYP_ORDER = ['Detached', 'Townhouses', 'Apartments']

# L_w implied by the soil figures published with the case studies, kept only to
# report the discrepancy with the soils sheet (which is the value used).
PUBLISHED_SOIL_LW = 58.406


# ============================================================
# LOADERS
# ============================================================
def load_lca(path=FILE_LCA, sheet=SHEET_LCA):
    """Flatten the pivot: building id rows followed by their material rows."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    labels = [str(v).strip() for v in raw.iloc[:, 0]]
    records, current = [], None
    for i, lab in enumerate(labels):
        if re.fullmatch(r'(A|T|DD|SD)_\d+', lab):
            current = lab
            continue
        if current is None or lab in ('nan', 'Row Labels', 'Grand Total'):
            continue
        vals = pd.to_numeric(raw.iloc[i, 1:1 + len(ALL_STAGES)], errors='coerce').values
        records.append([current, lab] + list(vals))
    df = pd.DataFrame(records, columns=['id', 'material'] + ALL_STAGES)
    if df.empty:
        raise ValueError(f"No building/material rows parsed from {path} / {sheet}.")
    return df.fillna(0.0)


def load_characteristics(path=FILE_CHARS, sheet=SHEET_CHARS):
    df = pd.read_excel(path, sheet_name=sheet)
    df = df.rename(columns={'ID': 'id'}).set_index('id')
    need = {'Total GFA', 'Footprint', 'OLF'}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"{path}/{sheet} is missing {missing}.")
    return df


def load_soil_factor(path=FILE_CHARS, sheet=SHEET_SOILS):
    s = pd.read_excel(path, sheet_name=sheet)
    name = s.columns[0]
    row = s[s[name].astype(str).str.contains('Area-weighted', case=False, na=False)]
    if row.empty:
        raise ValueError(f"No area-weighted soil row in {path}/{sheet}.")
    val = s.columns[1]
    # low / high are the extreme soil ORDERS (Raw, Organic), a bounding range
    # rather than a confidence interval; the aggregate row is excluded.
    orders = s.loc[~s.index.isin(row.index), val].astype(float)
    return float(row[val].iloc[0]), float(orders.min()), float(orders.max())


# ============================================================
# POOLING
# ============================================================
def pool(frame, value_cols, scheme=WEIGHT_SCHEME):
    """Pool building-level intensities to one row per typology."""
    if scheme == 'gfa_weighted':
        w = frame['GFA'] / frame.groupby('Typology')['GFA'].transform('sum')
        out = frame[value_cols].mul(w, axis=0).groupby(frame['Typology']).sum()
    elif scheme == 'equal_buildings':
        out = frame.groupby('Typology')[value_cols].mean()
    elif scheme == 'equal_subtypes':
        sub = frame.groupby(['Typology', 'Subtype'])[value_cols].mean()
        out = sub.groupby('Typology').mean()
    else:
        raise ValueError(f"Unknown WEIGHT_SCHEME '{scheme}'.")
    return out.reindex(TYP_ORDER)


# ============================================================
# MAIN
# ============================================================
def main():
    lca = load_lca()
    chars = load_characteristics()
    soil_avg, soil_low, soil_high = load_soil_factor()

    gfa = chars['Total GFA'].astype(float).copy()

    lca['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in lca['id']]
    lca['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in lca['id']]
    lookup = {raw: grp for grp, raws in MATERIAL_GROUPS.items() for raw in raws}
    lca['Material'] = [lookup.get(m, OTHERS_LABEL) for m in lca['material']]

    # absolute kg -> kg per m2 GFA
    area = lca['id'].map(gfa)
    if area.isna().any():
        raise ValueError(f"No floor area for {sorted(set(lca['id'][area.isna()]))}.")
    for s in ALL_STAGES:
        lca[s] = lca[s] / area

    # ---- reconciliation against the published per-building intensities ----
    per_building = lca.groupby('id')[STAGES].sum().sum(axis=1)
    if 'GWP' in chars.columns:   # optional published cross-check
        cmp = pd.DataFrame({'from_materials': per_building,
                            'published': chars['GWP']}).dropna()
        cmp['diff_pct'] = 100 * (cmp['from_materials'] / cmp['published'] - 1)
        worst = cmp['diff_pct'].abs().max()
        print(f"[check] material sums vs published intensities: "
              f"max |difference| = {worst:.2f}% "
              f"({'OK' if worst < 0.5 else 'INVESTIGATE'})")
        if worst >= 0.5:
            print(cmp[cmp['diff_pct'].abs() >= 0.5].round(2).to_string())

    # ---- duplicated case studies --------------------------------------------
    # Two cases whose per-m2 material x stage vectors are identical are one
    # design at two scales, not two observations. Pooling still weights them as
    # two, so the effective sample size is reported alongside n_buildings.
    vec = (lca.groupby(['id', 'material'])[ALL_STAGES].sum()
              .unstack('material').fillna(0.0))
    # Test: same non-zero pattern, and one constant ratio in every cell.
    dup_of, dup_ratio = {}, {}
    ids = list(vec.index)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            va, vb = vec.loc[a].values, vec.loc[b].values
            nz = np.abs(va) > 0
            if b in dup_of or not np.array_equal(nz, np.abs(vb) > 0):
                continue
            r = vb[nz] / va[nz]
            if np.ptp(r) < 1e-6 * abs(r.mean()) and abs(r.mean() - 1) < 0.01:
                dup_of[b] = dup_of.get(a, a)
                dup_ratio[b] = float(r.mean())
    for b, a in dup_of.items():
        print(f"[check] {b} = {a} x {dup_ratio[b]:.6f} in every material and stage "
              f"(a rescaled copy): ONE independent case, not two.")

    # ---- material x stage factors, pooled ----
    bm = (lca.groupby(['id', 'Typology', 'Subtype', 'Material'])[ALL_STAGES]
             .sum().reset_index())
    grid = pd.MultiIndex.from_product(
        [chars.index, list(MATERIAL_GROUPS) + [OTHERS_LABEL]], names=['id', 'Material'])
    bm = (bm.set_index(['id', 'Material']).reindex(grid)
            .drop(columns=['Typology', 'Subtype']).fillna(0.0).reset_index())
    bm['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in bm['id']]
    bm['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in bm['id']]
    bm['GFA'] = bm['id'].map(gfa)   # intensity conversion basis

    rows = []
    for mat in list(MATERIAL_GROUPS) + [OTHERS_LABEL]:
        pooled = pool(bm[bm['Material'] == mat], ALL_STAGES)
        for typ in TYP_ORDER:
            for stage in ALL_STAGES:
                rows.append({'Typology': typ, 'Material': mat, 'Stage': stage,
                             'kgCO2e_per_m2': float(pooled.loc[typ, stage])})
    mat_factors = pd.DataFrame(rows)

    # ---- typology-level characteristics ----
    chars = chars.copy()
    chars['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in chars.index]
    chars['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in chars.index]
    chars['GFA_used'] = gfa
    chars['Persons'] = chars['GFA_used'] / chars['OLF']
    chars['FSI'] = chars['GFA_used'] / chars['Footprint']
    chars['SOC_avg'] = soil_avg / chars['FSI']
    chars['SOC_low'] = soil_low / chars['FSI']
    chars['SOC_high'] = soil_high / chars['FSI']

    pooled_chars = pool(chars, ['FSI', 'SOC_avg', 'SOC_low', 'SOC_high'])

    # Occupancy load factor, pooled the same way as every other factor: a simple
    # average over case-study designs. This is scale-invariant, so it does not
    # matter whether a case study is recorded as a block or a single dwelling.
    # The people-conserving alternative (total floor area / total persons) is
    # printed alongside; it weights blocks by their resident count.
    olf = pool(chars, ['OLF'])['OLF'].reindex(TYP_ORDER)
    olf_people = (chars.groupby('Typology')['GFA_used'].sum()
                  / chars.groupby('Typology')['Persons'].sum()).reindex(TYP_ORDER)

    # Design occupants per dwelling, from the case studies where a dwelling
    # count exists. Apartments are modelled as blocks, so persons per dwelling
    # is supplied from the unit count recorded with the case study.
    chars['Dwellings'] = [DWELLINGS_PER_CASE.get(i, 1) for i in chars.index]
    chars['occ_per_dwelling'] = chars['Persons'] / chars['Dwellings']
    chars['size_per_dwelling'] = chars['GFA_used'] / chars['Dwellings']
    design = pool(chars, ['occ_per_dwelling'])['occ_per_dwelling'].to_dict()

    emb = (mat_factors[mat_factors['Stage'].isin(STAGES)]
           .groupby('Typology')['kgCO2e_per_m2'].sum().reindex(TYP_ORDER))
    modD = (mat_factors[mat_factors['Stage'] == STAGE_D]
            .groupby('Typology')['kgCO2e_per_m2'].sum().reindex(TYP_ORDER))

    typ_factors = pd.DataFrame({
        'Typology': TYP_ORDER,
        'n_buildings': [int((chars['Typology'] == t).sum()) for t in TYP_ORDER],
        'OLF_m2_per_person': olf.values,
        'OLF_people_conserving': olf_people.values,
        'design_occupants': [design[t] for t in TYP_ORDER],
        'FSI': pooled_chars['FSI'].values,
        'embodied_materials': emb.values,
        'SOC_avg': pooled_chars['SOC_avg'].values,
        'SOC_low': pooled_chars['SOC_low'].values,
        'SOC_high': pooled_chars['SOC_high'].values,
        'module_D': modD.values,
    })
    typ_factors['total_with_SOC'] = (typ_factors['embodied_materials']
                                     + typ_factors['SOC_avg'])

    # ---- spread across case studies (materials, in scope) -------------------
    # Each typology's factor rests on a handful of designs, so report how far it
    # moves: the range over individual buildings, and the range of the pooled
    # value when each building is left out in turn (jackknife). Neither is a
    # confidence interval; the sample is not random.
    b_emb = lca.groupby('id')[STAGES].sum().sum(axis=1).rename('emb').to_frame()
    b_emb['Typology'] = chars['Typology']
    b_emb['Subtype'] = chars['Subtype']
    b_emb['GFA'] = chars['GFA_used']
    loo = {t: [] for t in TYP_ORDER}
    for i in b_emb.index:
        t = b_emb.loc[i, 'Typology']
        rest = b_emb.drop(index=i)
        if (rest['Typology'] == t).any():
            loo[t].append(float(pool(rest, ['emb']).loc[t, 'emb']))
    independent = chars.index.difference(list(dup_of))
    typ_factors['n_independent'] = [int((chars.loc[independent, 'Typology'] == t).sum())
                                    for t in TYP_ORDER]
    typ_factors['emb_building_min'] = [b_emb.loc[b_emb.Typology == t, 'emb'].min() for t in TYP_ORDER]
    typ_factors['emb_building_max'] = [b_emb.loc[b_emb.Typology == t, 'emb'].max() for t in TYP_ORDER]
    typ_factors['emb_jackknife_min'] = [min(loo[t]) if loo[t] else np.nan for t in TYP_ORDER]
    typ_factors['emb_jackknife_max'] = [max(loo[t]) if loo[t] else np.nan for t in TYP_ORDER]

    mat_factors.to_csv(OUT_MATERIAL, index=False)
    typ_factors.to_csv(OUT_TYPOLOGY, index=False)

    # ==================================================================
    # SUMMARY
    # ==================================================================
    print(f"\nPooling: {WEIGHT_SCHEME} | soil factor L_w = {soil_avg:.3f} "
          f"(range {soil_low:.2f}-{soil_high:.2f}) kg/m2 footprint")
    print(f"NOTE: the published case-study soil figures imply L_w = "
          f"{PUBLISHED_SOIL_LW:.3f}, a {100 * (soil_avg / PUBLISHED_SOIL_LW - 1):.2f}% "
          f"difference.\n")

    print("EMBODIED CARBON BY MATERIAL  [kg CO2e / m2 GFA, stages "
          f"{', '.join(STAGES)}]")
    wide = (mat_factors[mat_factors['Stage'].isin(STAGES)]
            .pivot_table(index='Material', columns='Typology',
                         values='kgCO2e_per_m2', aggfunc='sum')
            .reindex(columns=TYP_ORDER))
    wide.loc['-- materials --'] = wide.sum()
    for t in TYP_ORDER:
        wide.loc['SOIL (land-use change)', t] = float(
            typ_factors.loc[typ_factors.Typology == t, 'SOC_avg'].iloc[0])
    wide.loc['== TOTAL =='] = wide.loc['-- materials --'] + wide.loc['SOIL (land-use change)']
    print(wide.round(1).to_string())

    print("\nBY LIFE-CYCLE STAGE  [kg CO2e / m2 GFA]")
    st = (mat_factors.pivot_table(index='Stage', columns='Typology',
                                  values='kgCO2e_per_m2', aggfunc='sum')
          .reindex(ALL_STAGES).reindex(columns=TYP_ORDER))
    st.loc['in-scope total'] = st.loc[STAGES].sum()
    print(st.round(1).to_string())
    print("Module D is reported but excluded from the in-scope total.")

    print("\nSUPPLEMENTARY -- full material resolution [kg CO2e/m2 GFA, in scope]")
    raw = lca.copy()
    raw['emb'] = raw[STAGES].sum(axis=1)
    full = (raw.pivot_table(index='id', columns='material', values='emb', aggfunc='sum')
            .reindex(chars.index).fillna(0.0))
    full['Typology'] = chars['Typology']
    full['Subtype'] = chars['Subtype']
    full['GFA'] = chars['GFA_used']
    cols = [c for c in full.columns if c not in ('Typology', 'Subtype', 'GFA')]
    supp = pool(full, cols).T.reindex(columns=TYP_ORDER)
    supp['mean'] = supp.mean(axis=1)
    print(supp.sort_values('mean', ascending=False).round(1).to_string())

    print("\nTYPOLOGY FACTORS")
    print(typ_factors.round(2).to_string(index=False))
    print(f"\nWritten: {OUT_MATERIAL}, {OUT_TYPOLOGY}")


if __name__ == '__main__':
    main()