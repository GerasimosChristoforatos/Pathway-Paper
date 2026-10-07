"""Item-level material decarbonisation (Boss.DECARB_MODE = 'horup_item'): each
case-study EPD item follows one Horup et al. (2025) S4 path (or is held) by
data/material_item_map.csv. Checks: the item table reproduces the case-study
workbook; the mapping is complete and one-to-one; the 2025 class totals are
kept; the pooled reductions equal an independent recomputation; soil, the
other stages and the history are unchanged; the sensitivity cases hold
exactly the items they name."""
import contextlib
import importlib
import io

import numpy as np
import pandas as pd
import pytest

from conftest import run_boss

import Building_factors as BF  # noqa: E402

ITEMS = pd.read_csv(BF.FILE_ITEMS)
MAP = pd.read_csv(BF.FILE_ITEM_MAP)
DEC = pd.read_csv(BF.OUT_DECARB)
ITEM_VARIANTS = [BF.decarb_variant('horup_item', item_case=c) for c in BF.ITEM_CASES]


@pytest.fixture(scope='module')
def runs():
    # whole life at construction, A4-A5 held: isolates the A1-A3 decarbonisation
    wl = dict(ACCOUNTING='whole_life_at_construction', DECARB_A45='held')
    return run_boss(DECARB_MODE='none', **wl), run_boss(DECARB_MODE='horup_item', **wl)


def test_item_table_reproduces_workbook():
    ref = BF.load_lca().groupby(['id', 'material'])[BF.ALL_STAGES].sum()
    got = ITEMS.groupby(['id', 'class'])[BF.ALL_STAGES].sum()
    got.index.names = ref.index.names
    assert set(got.index) == set(ref.index)
    assert np.allclose(got.reindex(ref.index).values, ref.values, rtol=1e-9, atol=1e-9)


def test_mapping_complete_and_one_to_one():
    pairs = ITEMS[['class', 'item']].drop_duplicates()
    assert not MAP.duplicated(['class', 'item']).any()
    m = pairs.merge(MAP, on=['class', 'item'], how='outer', indicator=True)
    assert (m['_merge'] == 'both').all(), m[m['_merge'] != 'both'][['class', 'item']].values.tolist()
    assert set(MAP['label']) <= set(BF.ITEM_LABELS)
    assert set(MAP['s4_row']) - {BF.ITEM_HELD} <= set(BF.decarb_paths().columns)
    assert MAP['basis'].str.len().gt(0).all()
    held = MAP[MAP['label'] == 'held']
    assert len(held) == 1 and held['item'].iloc[0].startswith('Elevator')
    assert BF.load_items(s4_rows=BF.decarb_paths().columns)['s4_row'].notna().all()


def test_nz_low_carbon_electricity_items_follow_the_criterion():
    """NZ-made and electricity-intensive production (author criterion): the 5
    aluminium items, Pink Batts glass wool, Pacific Steel rebar, WPMA Radiata
    timber and Nelson Pine LVL; not Allied Concrete, GIB plasterboard,
    Colorsteel / ZinaCore, CLT or NZSIP."""
    nz = MAP[MAP['nz_low_carbon_electricity'] == 'yes']
    expect = MAP[(MAP['class'] == 'ALUMINIUM')
                 | ((MAP['class'] == 'GLASS WOOL') & MAP['item'].str.contains('Pink'))
                 | MAP['item'].str.contains('Pacific Steel') | MAP['item'].str.contains(r'\(WPMA\)')
                 | MAP['item'].str.contains('Nelson Pine')]
    assert set(nz['item']) == set(expect['item'])
    assert (MAP['class'] == 'ALUMINIUM').sum() == 5
    for excluded in ('Allied Concrete', 'GIB', 'Colorsteel', 'ZinaCore', 'cross-laminated', 'NZSIP'):
        assert not nz['item'].str.contains(excluded, regex=False).any(), excluded


def test_class_totals_preserved_at_2025():
    base = pd.read_csv(BF.OUT_MATERIAL)
    base = base[base.Stage == 'A1-A3'].set_index(['Typology', 'Material'])['kgCO2e_per_m2']
    for v in ITEM_VARIANTS:
        d = DEC[(DEC.Variant == v) & (DEC.Year == 2025)].set_index(['Typology', 'Material'])['A13_kgCO2e_per_m2']
        assert np.allclose(d.reindex(base.index).values, base.values, rtol=0, atol=1e-9), v


def test_reductions_recomputed_from_items_and_s4():
    chars = BF.load_characteristics()
    gfa = chars['Total GFA'].astype(float)
    it = BF.load_items()
    it['a13'] = it['A1-A3'] / it['id'].map(gfa)
    paths = BF.decarb_paths()
    group = {raw: grp for grp, raws in BF.MATERIAL_GROUPS.items() for raw in raws}
    held = {'central': lambda r: r.s4_row == BF.ITEM_HELD,
            'proxies_held': lambda r: r.s4_row == BF.ITEM_HELD or r.label == 'proxy',
            'nz_elec_held': lambda r: r.s4_row == BF.ITEM_HELD or r.nz_low_carbon_electricity == 'yes',
            }
    for case, is_held in held.items():
        dec = DEC[DEC.Variant == BF.decarb_variant('horup_item', item_case=case)]
        dec = dec.set_index(['Typology', 'Material', 'Year'])['A13_kgCO2e_per_m2']
        for y in (2026, 2033, 2050):
            f = [1.0 if is_held(r) else paths.loc[y, r.s4_row] for r in it.itertuples()]
            b = (it['a13'] * f).groupby([it['id'], it['class'].map(lambda m: group.get(m, BF.OTHERS_LABEL))]).sum()
            for (typ, mat), v in dec.xs(y, level='Year').items():
                ids = [i for i in chars.index if BF.TYPOLOGY_OF[i.rsplit('_', 1)[0]] == typ]
                per = pd.DataFrame({'v': [b.get((i, mat), 0.0) for i in ids], 'Typology': typ,
                                    'Subtype': [BF.SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in ids]})
                assert v == pytest.approx(BF.pool(per, ['v']).loc[typ, 'v'], rel=1e-12, abs=1e-12), (case, y, typ, mat)


def test_sensitivity_cases_order():
    """Holding items can only lower the reduction."""
    d = DEC[DEC.Year == 2050].groupby(['Variant', 'Typology'])['A13_kgCO2e_per_m2'].sum()
    c, ph, nz = (d.loc[v] for v in ITEM_VARIANTS)
    assert (ph >= c - 1e-12).all() and (nz >= c - 1e-12).all()


def test_soil_other_stages_and_2025_unchanged(runs):
    b0, b1 = runs
    assert np.array_equal(b0['flow_annual']['SOIL'].values, b1['flow_annual']['SOIL'].values)
    assert b0['_soil'] == b1['_soil']
    assert np.array_equal(b0['carbon_total_typ'].loc[2025].values, b1['carbon_total_typ'].loc[2025].values)
    assert np.array_equal(b0['results']['50th']['total'], b1['results']['50th']['total'])
    for stg in ('A4-A5', 'B2,B4', 'C1-C4'):
        for t in b1['typ_names']:
            assert np.ndim(b1['stage_path'][stg][t]) == 0 and b1['stage_path'][stg][t] == b0['stage_path'][stg][t]
    d_total = b0['tot_carbon_median'] - b1['tot_carbon_median']
    assert d_total > 0 and b0['_upfront'] - b1['_upfront'] == pytest.approx(d_total, rel=1e-9)


def test_history_unchanged(runs):
    import PB
    b0, b1 = runs
    h0 = PB.historical_emissions(b0, range(2016, 2026))
    h1 = PB.historical_emissions(b1, range(2016, 2026))
    assert np.array_equal(h0['I_sec_kg'].values, h1['I_sec_kg'].values)


def test_settings_that_do_not_apply_are_refused():
    with pytest.raises(ValueError):
        BF.decarb_variant('none', item_case='proxies_held')
    with pytest.raises(ValueError):
        BF.decarb_variant('horup_class_v1_1', item_case='proxies_held')
    with pytest.raises(ValueError):
        BF.decarb_variant('horup_material')            # the v1.1 name is retired


def test_mc_bootstrap_stream_unchanged():
    import Boss
    import MonteCarlo as MC
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            s0 = MC.build_setup(dict(DECARB_MODE='none'))
            s1 = MC.build_setup(dict(DECARB_MODE='horup_item'))
        assert np.array_equal(s0['boot_emb'], s1['boot_emb']) and np.array_equal(s0['boot_up'], s1['boot_up'])
        assert np.allclose(s1['boot_red'][:, :, 0], 0.0)
    finally:
        importlib.reload(Boss)
