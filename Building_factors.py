"""
BUILDING FACTORS -- per-typology embodied-carbon factors from 16 case studies
============================================================================
Source and benchmarking of the 16 case studies: Christoforatos G, Pickering K
(2025), "Embodied impacts of residential stocks; multi-level assessment of
materials, buildings, typologies and functional units to support policymaking
towards sustainable housing", Smart and Sustainable Built Environment (ahead of
print), https://doi.org/10.1108/SASBE-06-2025-0304.
Soil factor (sheet 3): 58.77 kg CO2e / m2 footprint, the area-weighted average
over the 10 soil orders of the land zoned for urbanisation to about 2050 in
Auckland: Christoforatos G, Pickering K, Schipper LA (2026), Journal of
Environmental Management 415, 130603, https://doi.org/10.1016/j.jenvman.2026.130603.

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
  factors_building.csv   one row per case study: in-scope materials by stage
                         (kg/m2 GFA), soil loss, and which case (if any) it
                         duplicates. Read by MonteCarlo.py for the bootstrap.
  factors_a13_decarb.csv A1-A3 (kg/m2 GFA) by typology x material x year 2025-2050,
                         decarbonised with Horup et al. (2025) (Boss.DECARB_MODE),
                         per variant: class-level mapping of v1.1 (and its
                         steel-profile sensitivity); item-level mapping (and
                         its sensitivities). See decarb_variant().
  factors_building_a13_reduction.csv  the same reduction per case study and
                         year, for the Monte Carlo bootstrap.
  factors_a13_item_coverage.csv  item-level mapping: share of 2025 A1-A3 per
                         typology by label (direct / sec31 / proxy / held) and
                         by S4 row, and the implied A1-A3 reduction by 2050.

POOLING
  Factors are intensities (kg/m2), so they are scale-invariant. Buildings are
  pooled with equal weight, after first averaging within detached sub-types so
  the six single-storey cases do not outvote the four two-storey ones.
  Apartments rest on ONE independent case (A_1 and A_2 are one design at two
  scales); the typology table flags this (n_independent).

SOIL
  Soil organic carbon loss is NOT a material. It is land-use change:
      SOC [kg/m2 GFA] = L_w [kg/m2 footprint] / floor space index
  It is kept as its own line so that no material decarbonisation rate is ever
  applied to it, and so that densification (a higher floor space index) reduces
  it automatically.

KNOWN DATA ISSUES, handled explicitly below
  1. T_4's absolute emissions are for the whole 887 m2 block, while the
     characteristics sheet reports it scaled to one 147.8 m2 dwelling. The
     block area is used for the per-m2 conversion.
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
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))     # repository root: works from any directory
DATA_DIR = os.path.join(ROOT_DIR, 'data')
FILE_LCA = os.path.join(DATA_DIR, 'building_data.xlsx')   # one workbook, three sheets
SHEET_LCA = '1'                          # materials x stages, absolute kg CO2e
FILE_CHARS = FILE_LCA
SHEET_CHARS = '2'                        # GFA, occupancy load factor, footprint
SHEET_SOILS = '3'                        # soil carbon by soil order

OUT_DIR = os.path.join(ROOT_DIR, 'outputs', 'factors')     # derived files; data/ holds inputs only
OUT_MATERIAL = os.path.join(OUT_DIR, 'factors_material.csv')
OUT_TYPOLOGY = os.path.join(OUT_DIR, 'factors_typology.csv')
OUT_BUILDING = os.path.join(OUT_DIR, 'factors_building.csv')   # for MonteCarlo.py
OUT_DECARB = os.path.join(OUT_DIR, 'factors_a13_decarb.csv')    # A1-A3 by year (Boss.DECARB_MODE)
OUT_DECARB_BLD = os.path.join(OUT_DIR, 'factors_building_a13_reduction.csv')   # for MonteCarlo.py
OUT_ITEM_COVERAGE = os.path.join(OUT_DIR, 'factors_a13_item_coverage.csv')
OUT_EVENTS = os.path.join(OUT_DIR, 'factors_events.csv')            # B2/B4 events by age (Boss.ACCOUNTING)
OUT_EVENTS_BLD = os.path.join(OUT_DIR, 'factors_building_events.csv')   # the same per case study (MonteCarlo.py)
OUT_A45_ITEM = os.path.join(OUT_DIR, 'factors_a45_item.csv')        # A4-A5 on item paths (sensitivity)

# ---------------------------------------------------------------------------
# MATERIAL DECARBONISATION OF A1-A3 (Boss.DECARB_MODE)
# ---------------------------------------------------------------------------
# Relative change of GWP per unit of material production versus 2025: Horup et
# al. (2025), Sci. Total Environ. 966, 178780, Fig. 2 and Supplementary Table S4
# (average of the 9 premise scenarios; 2025, 2030, 2040, 2050), built by
# data/build_horup.py. Applied to A1-A3 only (Horup's scope); A4-A5, B2, B4,
# C1-C4 and soil are never changed (author decision). Between Horup's years the
# path is interpolated linearly (author decision; Horup state 'interpolated'
# without naming the method, p. 3).
#
# 'horup_class_v1_1' (baseline-pb-v1.1, then called 'horup_material'): case-study
# material CLASS -> S4 row (author decision). Classes without a counterpart in
# S4 keep their 2025 factor: PLASTERBOARD, PLASTICS, PAINT, FIBRE CEMENT,
# PLASTER, SIP and OTHERS. REINFORCED CONCRETE includes its rebar, decarbonised
# at the concrete-structure rate (S4 does not separate reinforcement). STEEL at
# the reinforcing-steel rate (conservative; steel profile is a sensitivity).
FILE_HORUP = os.path.join(DATA_DIR, 'derived', 'horup2025_table_s4.csv')
DECARB_YEARS = list(range(2025, 2051))
DECARB_KNOTS = (2025, 2030, 2040, 2050)
DECARB_S4 = {'CONCRETE': 'Concrete structure', 'REINFORCED CONCRETE': 'Concrete structure',
             'STEEL': 'Reinforcing steel', 'TIMBER': 'Construction wood', 'ALUMINIUM': 'Aluminium',
             'BRICKS': 'Clay brick', 'GLASS': 'Glass', 'GLASS WOOL': 'Mineral wool glass'}
DECARB_VARIANTS = {'horup_class_v1_1': {},                                  # the mapping above
                   'horup_class_v1_1_steel_profile': {'STEEL': 'Steel profile'}}   # sensitivity
#
# 'horup_item' (baseline-pb-v1.2): each EPD item of the case studies
# (data/derived/material_items.csv, built by data/build_material_items.py) ->
# one S4 row, or HELD, by data/material_item_map.csv (author decisions; the
# basis of each row is in the table): label 'direct' (S4 has the material),
# 'sec31' (Horup et al. 2025 p. 6: cementitious, wood-based and clay products
# follow concrete, wood and clay), 'proxy' (no S4 counterpart; author rule) or
# 'held' (2025 factor kept). Items are pooled per building, then per typology,
# exactly as the classes; the 2025 totals are the class totals. Sensitivities
# (ITEM_CASES): proxies held at 2025; items made in New Zealand with
# electricity-intensive production held at 2025 (column
# nz_low_carbon_electricity); the held lift at the S4 steel-profile rate.
FILE_ITEMS = os.path.join(DATA_DIR, 'derived', 'material_items.csv')
FILE_ITEM_MAP = os.path.join(DATA_DIR, 'material_item_map.csv')
ITEM_LABELS = ('direct', 'sec31', 'proxy', 'held')
ITEM_HELD = 'HELD'
ITEM_CASES = {'central': 'item-level mapping',
              'proxies_held': 'proxy-mapped items held at 2025',
              'nz_elec_held': 'NZ-made, electricity-intensive items held at 2025',
              'elevator_steel_profile': 'held lift at the S4 steel-profile rate'}
DECARB_MODES = ('none', 'horup_class_v1_1', 'horup_item')

# ---------------------------------------------------------------------------
# A4-A5 DECARBONISATION (Boss.DECARB_A45)
# ---------------------------------------------------------------------------
# A4-A5 cannot be separated by material process in the case-study data, so it
# follows a generic technological-progress factor: Resch E, Wiik MK, Tellnes LGF,
# Andresen I, Selvig E, Stoknes S (2021), Building and Environment 187, 107399,
# Table 1 (p. 4): production e^(-0.01 y), 'a ~1% yearly improvement' (half-life
# 69 years); y = years after 2025. The source gives an exponential decay, so
# e^(-0.01 (t - 2025)) is used rather than (1 - 0.01)^(t - 2025) (difference 0.1
# percentage point by 2050: -22.1% vs -22.2%). Resch et al. apply 2%/yr to
# transport (Table 1); A4-A5 also contains installation and wastage, so the 1%
# production rate is used for the combined stage (conservative for transport).
# Horup et al. (2025, Fig. 2A, pp. 5-6) show that this generic factor
# oversimplifies material-specific trends, which is why it is used only for the
# non-separable A4-A5 stage. Sensitivities: held at 2025; each item's own S4 path.
A45_DECAY = 0.01           # per year, Resch et al. (2021) Table 1, production


def generic_path(years, base=2025, rate=A45_DECAY):
    """Relative A4-A5 factor e^(-rate (t - base)); 1 at and before base."""
    t = np.asarray(years, float)
    return np.exp(-rate * np.clip(t - base, 0.0, None))


# ---------------------------------------------------------------------------
# REPLACEMENT / REPAINT EVENTS (time-resolved B2, B4; Boss.ACCOUNTING)
# ---------------------------------------------------------------------------
# From data/derived/lca_events.csv (data/build_lca_events.py; counts and lifespan
# from the LCAQuick root tables). Per event line: per-event impact = line B2/B4 /
# number of events, split into A1-A3 : A4-A5 : C1-C4 in proportion to the line's
# own initial stages (author decision; for paint lines the repaint composition
# differs from the first coat and cannot be separated in the file, so the same
# proportional split is used: negligible, since the paint path is the EPS proxy,
# -4% by 2050). Timing: n events evenly spaced, event k at k L / (n + 1) years
# after construction (LCAQuick derives n = ceil(L / RSL) - 1, so L / (n + 1) is
# the shortest service life consistent with the count; author decision);
# sensitivity k L / n. A fractional event year is split linearly between the two
# adjacent years. Event paths: replacements on the item's own S4 path; repaints
# (PAINT lines and the ZinaCore recoating lines) on the paint path (EPS proxy).
FILE_EVENTS = os.path.join(DATA_DIR, 'derived', 'lca_events.csv')
EVENT_TIMINGS = {'n+1': 'event k at k L / (n + 1) (adopted)', 'n': 'event k at k L / n (sensitivity)'}
EVENT_COMPONENTS = ('A1-A3', 'A4-A5', 'C1-C4')
PAINT_PATH = ('EPS', 'proxy', 'no')          # S4 row, label, NZ flag of the paint path (material_item_map)


def event_rows(timing='n+1'):
    """One row per event line x event x component x calendar offset (age, integer
    years after construction): absolute kg CO2e per building, with the material
    group and the S4 row / label / NZ flag of the path it follows."""
    ev = pd.read_csv(FILE_EVENTS)
    ev = ev[ev['n_events'] > 0].copy()
    mp = pd.read_csv(FILE_ITEM_MAP)
    ev = ev.merge(mp[['class', 'item', 's4_row', 'label', 'nz_low_carbon_electricity']], on=['class', 'item'],
                  how='left', validate='m:1')
    if ev['s4_row'].isna().any():
        raise ValueError('Event lines without an S4 mapping.')
    paint = ev['event_path'] == 'paint'
    ev.loc[paint, ['s4_row', 'label', 'nz_low_carbon_electricity']] = PAINT_PATH
    lookup = {raw: grp for grp, raws in MATERIAL_GROUPS.items() for raw in raws}
    ev = ev.rename(columns={'A1-A3': 'a13', 'A4-A5': 'a45', 'B2,B4': 'b', 'C1-C4': 'c',
                            'nz_low_carbon_electricity': 'nz', 'class': 'cls'})
    ini = ev['a13'] + ev['a45'] + ev['c']
    if (ini <= 0).any():
        raise ValueError('Event line with no initial A1-A3 + A4-A5 + C1-C4 to split by.')
    rows = []
    for r, tot in zip(ev.itertuples(index=False), ini):
        n, L = int(r.n_events), float(r.lifespan)
        per = r.b / n
        shares = {'A1-A3': r.a13 / tot, 'A4-A5': r.a45 / tot, 'C1-C4': r.c / tot}
        for k in range(1, n + 1):
            t = k * L / (n + 1) if timing == 'n+1' else k * L / n
            a0 = int(np.floor(t)); w1 = t - a0
            for age, w in ((a0, 1.0 - w1), (a0 + 1, w1)):
                if w <= 0:
                    continue
                for c in EVENT_COMPONENTS:
                    rows.append((r.id, lookup.get(r.cls, OTHERS_LABEL), age, c, r.s4_row, r.label, r.nz,
                                 per * shares[c] * w))
    out = pd.DataFrame(rows, columns=['id', 'Material', 'Age', 'Component', 'S4', 'label', 'nz', 'kg'])
    chk = out.groupby('id')['kg'].sum() - ev.groupby('id')['b'].sum()
    if chk.abs().max() > 1e-6:
        raise ValueError(f'Events do not add up to line B2/B4 (max {chk.abs().max():g} kg).')
    return out


def decarb_variant(mode, steel='reinforcing_steel', item_case='central'):
    """Variant name in factors_a13_decarb.csv / factors_building_a13_reduction.csv
    for a Boss setting (DECARB_MODE, DECARB_STEEL, DECARB_ITEM_CASE); None for
    'none'. A setting that does not apply to the mode must stay at its default."""
    if mode not in DECARB_MODES:
        raise ValueError(f"Unknown DECARB_MODE '{mode}'; expected one of {DECARB_MODES}.")
    if mode != 'horup_class_v1_1' and steel != 'reinforcing_steel':
        raise ValueError(f"DECARB_STEEL = '{steel}' applies to 'horup_class_v1_1' only.")
    if mode != 'horup_item' and item_case != 'central':
        raise ValueError(f"DECARB_ITEM_CASE = '{item_case}' applies to 'horup_item' only.")
    if mode == 'none':
        return None
    if mode == 'horup_class_v1_1':
        return {'reinforcing_steel': 'horup_class_v1_1', 'steel_profile': 'horup_class_v1_1_steel_profile'}[steel]
    if item_case not in ITEM_CASES:
        raise ValueError(f"Unknown DECARB_ITEM_CASE '{item_case}'; expected one of {tuple(ITEM_CASES)}.")
    return 'horup_item' if item_case == 'central' else f'horup_item_{item_case}'


def load_items(path=FILE_ITEMS, map_path=FILE_ITEM_MAP, s4_rows=None):
    """Item-level case-study LCA (absolute kg per building) joined to its S4
    mapping. Stops if an item is unmapped, mapped twice, or mapped to an
    unknown S4 row or label."""
    it = pd.read_csv(path)
    mp = pd.read_csv(map_path)
    if mp.duplicated(['class', 'item']).any():
        raise ValueError(f'{map_path}: items mapped more than once: '
                         f'{mp[mp.duplicated(["class", "item"], keep=False)][["class", "item"]].values.tolist()}')
    pairs = it[['class', 'item']].drop_duplicates()
    m = pairs.merge(mp, on=['class', 'item'], how='left', indicator=True)
    if (m['_merge'] != 'both').any():
        raise ValueError(f'{map_path}: unmatched items {m[m["_merge"] != "both"][["class", "item"]].values.tolist()}')
    extra = mp.merge(pairs, on=['class', 'item'], how='left', indicator=True)
    if (extra['_merge'] != 'both').any():
        raise ValueError(f'{map_path}: mapped items absent from {path}: '
                         f'{extra[extra["_merge"] != "both"][["class", "item"]].values.tolist()}')
    if not mp['label'].isin(ITEM_LABELS).all():
        raise ValueError(f'{map_path}: unknown labels {sorted(set(mp["label"]) - set(ITEM_LABELS))}.')
    if ((mp['label'] == 'held') != (mp['s4_row'] == ITEM_HELD)).any():
        raise ValueError(f"{map_path}: label 'held' and S4 row '{ITEM_HELD}' must coincide.")
    if not mp['nz_low_carbon_electricity'].isin(('yes', 'no')).all():
        raise ValueError(f'{map_path}: nz_low_carbon_electricity must be yes/no.')
    if s4_rows is not None:
        unknown = set(mp['s4_row']) - set(s4_rows) - {ITEM_HELD}
        if unknown:
            raise ValueError(f'{map_path}: S4 rows not in Table S4: {sorted(unknown)}')
    return it.merge(mp, on=['class', 'item'], how='left', validate='m:1')


def item_s4_row(items, case):
    """S4 row per item row for an item-level case, NaN where held at 2025."""
    row = items['s4_row'].where(items['s4_row'] != ITEM_HELD)
    if case == 'proxies_held':
        row = row.where(items['label'] != 'proxy')
    elif case == 'nz_elec_held':
        row = row.where(items['nz_low_carbon_electricity'] != 'yes')
    elif case == 'elevator_steel_profile':
        row = row.where(items['label'] != 'held', 'Steel profile')
    elif case != 'central':
        raise ValueError(f"Unknown item case '{case}'.")
    return row

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


def decarb_paths(path=FILE_HORUP, years=DECARB_YEARS):
    """Relative A1-A3 factor by S4 material and year (2025 = 1), linear between
    the S4 years. Returns DataFrame (years x material)."""
    d = pd.read_csv(path).pivot(index='year', columns='material', values='rel_to_2025')
    if list(d.index) != list(DECARB_KNOTS):
        raise ValueError(f'{path}: years {list(d.index)}, expected {DECARB_KNOTS}.')
    return pd.DataFrame({m: np.interp(years, d.index.values, d[m].values) for m in d.columns},
                        index=years)


# ============================================================
# POOLING
# ============================================================
def pool(frame, value_cols):
    """Pool building-level intensities to one row per typology: equal weight
    per sub-type within a typology, equal weight per building within a sub-type."""
    sub = frame.groupby(['Typology', 'Subtype'])[value_cols].mean()
    return sub.groupby('Typology').mean().reindex(TYP_ORDER)


def item_coverage(items, paths, ids):
    """Pooled 2025 A1-A3 (kg/m2) per typology by label and by S4 row (item-level
    mapping), as shares, and the implied A1-A3 reduction by 2050 per item case.
    Rows: Typology, Kind ('label' | 's4_row' | 'reduction_2050'), Key, Value."""
    rows = []
    for kind, col in (('label', 'label'), ('s4_row', 's4_row')):
        b = items.groupby(['id', col])['a13'].sum().unstack(fill_value=0.0).reindex(ids).fillna(0.0)
        keys = list(b.columns)
        b['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in b.index]
        b['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in b.index]
        p = pool(b.reset_index(drop=True), keys)
        share = p.div(p.sum(axis=1), axis=0)
        rows += [dict(Typology=t, Kind=kind, Key=k, Value=float(share.loc[t, k])) for t in TYP_ORDER for k in keys]
    y = DECARB_YEARS[-1]
    for case in ITEM_CASES:
        r = item_s4_row(items, case).map(lambda k: 1.0 if pd.isna(k) else paths.loc[y, k])
        b = pd.DataFrame({'a': items['a13'], 'b': items['a13'] * r, 'id': items['id']}).groupby('id').sum().reindex(ids)
        b['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in b.index]
        b['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in b.index]
        p = pool(b.reset_index(drop=True), ['a', 'b'])
        rows += [dict(Typology=t, Kind='reduction_2050', Key=case, Value=float(1 - p.loc[t, 'b'] / p.loc[t, 'a']))
                 for t in TYP_ORDER]
    return pd.DataFrame(rows)


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

    bld = lca.groupby('id')[ALL_STAGES].sum().reindex(chars.index)
    bld.insert(0, 'Typology', chars['Typology'])
    bld.insert(1, 'Subtype', chars['Subtype'])
    bld.insert(2, 'GFA', chars['GFA_used'])
    bld['FSI'] = chars['FSI']
    bld['SOC_avg'] = chars['SOC_avg']
    bld['duplicate_of'] = [dup_of.get(i, '') for i in bld.index]

    # ---- decarbonised A1-A3 by year (Horup et al. 2025, S4) ------------------
    # Pooling is linear, so pooling the decarbonised building values equals
    # decarbonising the pooled ones; done per case-study class, then grouped.
    paths = decarb_paths()
    dec_rows, red_rows = [], []
    ids = list(chars.index)
    for variant, override in DECARB_VARIANTS.items():
        s4 = {**DECARB_S4, **override}
        missing = set(s4.values()) - set(paths.columns)
        if missing:
            raise ValueError(f'S4 rows not found: {missing}')
        for y in DECARB_YEARS:
            r = lca['material'].map(lambda m: paths.loc[y, s4[m]] if m in s4 else 1.0)
            a13 = lca['A1-A3'] * r
            g = (a13.groupby([lca['id'], lca['Material']]).sum()
                    .reindex(pd.MultiIndex.from_product([ids, list(MATERIAL_GROUPS) + [OTHERS_LABEL]]))
                    .fillna(0.0).rename('a13').reset_index())
            g.columns = ['id', 'Material', 'a13']
            g['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in g['id']]
            g['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in g['id']]
            for mat in list(MATERIAL_GROUPS) + [OTHERS_LABEL]:
                pooled = pool(g[g['Material'] == mat], ['a13'])['a13']
                for typ in TYP_ORDER:
                    dec_rows.append(dict(Variant=variant, Typology=typ, Material=mat, Year=y,
                                         A13_kgCO2e_per_m2=float(pooled.loc[typ])))
            red = (lca['A1-A3'] - a13).groupby(lca['id']).sum().reindex(ids).fillna(0.0)
            red_rows += [dict(Variant=variant, id=i, Year=y, A13_reduction_kgCO2e_per_m2=float(red.loc[i]))
                         for i in ids]
    # item-level mapping (horup_item and its sensitivities): each item follows
    # one S4 row (or is held); summed per building x class, then grouped and
    # pooled exactly as above
    items = load_items(s4_rows=paths.columns)
    area_i = items['id'].map(gfa)
    if area_i.isna().any():
        raise ValueError(f"No floor area for {sorted(set(items['id'][area_i.isna()]))}.")
    items['a13'] = items['A1-A3'] / area_i
    items['Material'] = [lookup.get(m, OTHERS_LABEL) for m in items['class']]
    cls_items = items.groupby(['id', 'class'])['a13'].sum()
    cls_lca = lca.groupby(['id', 'material'])['A1-A3'].sum()
    cls_items.index.names = cls_lca.index.names
    worst = (cls_items.reindex(cls_lca.index).fillna(0.0) - cls_lca).abs().max()
    if set(cls_items.index) != set(cls_lca.index) or worst > 1e-9:
        raise ValueError(f'Item A1-A3 does not reproduce the class A1-A3 of {FILE_LCA} (max {worst:g}).')
    for case in ITEM_CASES:
        variant = decarb_variant('horup_item', item_case=case)
        row = item_s4_row(items, case)
        for y in DECARB_YEARS:
            r = row.map(lambda k: 1.0 if pd.isna(k) else paths.loc[y, k])
            a13 = items['a13'] * r
            g = (a13.groupby([items['id'], items['Material']]).sum()
                    .reindex(pd.MultiIndex.from_product([ids, list(MATERIAL_GROUPS) + [OTHERS_LABEL]]))
                    .fillna(0.0).rename('a13').reset_index())
            g.columns = ['id', 'Material', 'a13']
            g['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in g['id']]
            g['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in g['id']]
            for mat in list(MATERIAL_GROUPS) + [OTHERS_LABEL]:
                pooled = pool(g[g['Material'] == mat], ['a13'])['a13']
                for typ in TYP_ORDER:
                    dec_rows.append(dict(Variant=variant, Typology=typ, Material=mat, Year=y,
                                         A13_kgCO2e_per_m2=float(pooled.loc[typ])))
            red = (items['a13'] - a13).groupby(items['id']).sum().reindex(ids).fillna(0.0)
            red_rows += [dict(Variant=variant, id=i, Year=y, A13_reduction_kgCO2e_per_m2=float(red.loc[i]))
                         for i in ids]
    coverage = item_coverage(items, paths, ids)

    # ---- A4-A5 on each item's own S4 path (DECARB_A45 = 'item', sensitivity) ----
    items['a45'] = items['A4-A5'] / area_i
    row45 = item_s4_row(items, 'central')
    a45_rows = []
    for y in DECARB_YEARS:
        r = row45.map(lambda k: 1.0 if pd.isna(k) else paths.loc[y, k])
        g = ((items['a45'] * r).groupby([items['id'], items['Material']]).sum()
             .reindex(pd.MultiIndex.from_product([ids, list(MATERIAL_GROUPS) + [OTHERS_LABEL]]))
             .fillna(0.0).rename('a45').reset_index())
        g.columns = ['id', 'Material', 'a45']
        g['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in g['id']]
        g['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in g['id']]
        for mat in list(MATERIAL_GROUPS) + [OTHERS_LABEL]:
            pooled = pool(g[g['Material'] == mat], ['a45'])['a45']
            a45_rows += [dict(Typology=t, Material=mat, Year=y, A45_kgCO2e_per_m2=float(pooled.loc[t]))
                         for t in TYP_ORDER]
    a45_item = pd.DataFrame(a45_rows)
    base45 = mat_factors[mat_factors.Stage == 'A4-A5'].set_index(['Typology', 'Material'])['kgCO2e_per_m2']
    chk45 = a45_item[a45_item.Year == DECARB_YEARS[0]].set_index(['Typology', 'Material'])['A45_kgCO2e_per_m2']
    if (chk45 - base45.reindex(chk45.index).fillna(0.0)).abs().max() > 1e-9:
        raise ValueError('A4-A5 on item paths does not equal the 2025 A4-A5 factors in 2025.')

    # ---- replacement / repaint events by age (time-resolved B2, B4) ---------
    keys = ['Material', 'Age', 'Component', 'S4', 'label', 'nz']
    ev_pooled, ev_bld = [], []
    for timing in EVENT_TIMINGS:
        er = event_rows(timing)
        er['kg_m2'] = er['kg'] / er['id'].map(gfa)
        wide = er.pivot_table(index='id', columns=keys, values='kg_m2', aggfunc='sum').reindex(ids).fillna(0.0)
        bl = wide.stack(keys, future_stack=True).rename('kg_per_m2').reset_index()
        bl = bl[bl['kg_per_m2'] != 0]
        bl.insert(0, 'Timing', timing)
        ev_bld.append(bl)
        cols = list(wide.columns)
        flat = pd.DataFrame(wide.values, index=ids, columns=range(len(cols)))
        flat['Typology'] = [TYPOLOGY_OF[i.rsplit('_', 1)[0]] for i in flat.index]
        flat['Subtype'] = [SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in flat.index]
        pooled = pool(flat, list(range(len(cols))))
        for t in TYP_ORDER:
            for j, key in enumerate(cols):
                v = float(pooled.loc[t, j])
                if v != 0:
                    ev_pooled.append(dict(Timing=timing, Typology=t, **dict(zip(keys, key)), kg_per_m2=v))
    ev_pooled, ev_bld = pd.DataFrame(ev_pooled), pd.concat(ev_bld, ignore_index=True)
    b_fac = mat_factors[mat_factors.Stage == 'B2,B4'].groupby('Typology')['kgCO2e_per_m2'].sum()
    for timing, g in ev_pooled.groupby('Timing'):
        worst = float((g.groupby('Typology')['kg_per_m2'].sum() - b_fac).abs().max())
        if worst > 1e-9:
            raise ValueError(f'Pooled events ({timing}) do not add up to the B2/B4 factor ({worst:g} kg/m2).')

    dec = pd.DataFrame(dec_rows)
    chk = (dec[(dec.Year == DECARB_YEARS[0])].groupby(['Variant', 'Typology', 'Material'])['A13_kgCO2e_per_m2']
           .sum().reset_index())
    base = mat_factors[mat_factors.Stage == 'A1-A3'].set_index(['Typology', 'Material'])['kgCO2e_per_m2']
    worst = max(abs(r.A13_kgCO2e_per_m2 - base.loc[(r.Typology, r.Material)]) for r in chk.itertuples())
    if worst > 1e-9:
        raise ValueError(f'Decarbonised A1-A3 in 2025 differs from the 2025 factors by {worst:g}.')

    for p in (OUT_MATERIAL, OUT_TYPOLOGY, OUT_BUILDING, OUT_DECARB, OUT_DECARB_BLD, OUT_ITEM_COVERAGE, OUT_EVENTS,
              OUT_EVENTS_BLD, OUT_A45_ITEM):
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    mat_factors.to_csv(OUT_MATERIAL, index=False)
    typ_factors.to_csv(OUT_TYPOLOGY, index=False)
    bld.reset_index().to_csv(OUT_BUILDING, index=False)
    dec.to_csv(OUT_DECARB, index=False)
    pd.DataFrame(red_rows).to_csv(OUT_DECARB_BLD, index=False)
    coverage.to_csv(OUT_ITEM_COVERAGE, index=False)
    ev_pooled.to_csv(OUT_EVENTS, index=False)
    ev_bld.to_csv(OUT_EVENTS_BLD, index=False)
    a45_item.to_csv(OUT_A45_ITEM, index=False)

    # ==================================================================
    # SUMMARY
    # ==================================================================
    print(f"\nPooling: equal sub-types | soil factor L_w = {soil_avg:.3f} "
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
    print(f"\nWritten: {OUT_MATERIAL}, {OUT_TYPOLOGY}, {OUT_BUILDING}")


if __name__ == '__main__':
    main()
