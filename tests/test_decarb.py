"""Material decarbonisation (Boss.DECARB_MODE = 'horup_material'): Horup et al.
(2025) SI Table S4 paths applied to A1-A3 of mapped materials only. Soil, the
2025 factors, the other stages and the history stay unchanged; the reductions
are those tabulated, per material and year."""
import contextlib
import importlib
import io

import numpy as np
import pandas as pd
import pytest

from conftest import run_boss

import Building_factors as BF  # noqa: E402

S4 = pd.read_csv(BF.FILE_HORUP)


@pytest.fixture(scope='module')
def runs():
    return run_boss(DECARB_MODE='none'), run_boss(DECARB_MODE='horup_material')


def test_s4_paths_match_the_table():
    """Relative path = C(t)/C(2025) at Horup's years; linear in between."""
    p = BF.decarb_paths()
    for m, g in S4.groupby('material'):
        g = g.set_index('year')
        for y in BF.DECARB_KNOTS:
            assert p.loc[y, m] == pytest.approx(g.loc[y, 'premise_rel_ecoinvent'] / g.loc[2025, 'premise_rel_ecoinvent'],
                                                rel=1e-12)
        assert p.loc[2027, m] == pytest.approx(0.6 * p.loc[2025, m] + 0.4 * p.loc[2030, m], rel=1e-12)
        assert p.loc[2045, m] == pytest.approx(0.5 * p.loc[2040, m] + 0.5 * p.loc[2050, m], rel=1e-12)


def test_reductions_per_material_and_year_as_tabulated():
    """Pooled A1-A3 by class, recomputed independently from the case-study
    workbook and the S4 table, equals factors_a13_decarb.csv in every year."""
    lca, chars = BF.load_lca(), BF.load_characteristics()
    gfa = chars['Total GFA'].astype(float)
    lca['a13'] = lca['A1-A3'] / lca['id'].map(gfa)
    paths = BF.decarb_paths()
    dec = pd.read_csv(BF.OUT_DECARB)
    dec = dec[dec.Variant == 'horup_material'].set_index(['Typology', 'Material', 'Year'])['A13_kgCO2e_per_m2']
    group = {raw: grp for grp, raws in BF.MATERIAL_GROUPS.items() for raw in raws}
    for y in (2026, 2030, 2041, 2050):
        f = lca['material'].map(lambda m: paths.loc[y, BF.DECARB_S4[m]] if m in BF.DECARB_S4 else 1.0)
        b = (lca['a13'] * f).groupby([lca['id'], lca['material'].map(lambda m: group.get(m, BF.OTHERS_LABEL))]).sum()
        for (typ, mat), v in dec.xs(y, level='Year').items():
            ids = [i for i in chars.index if BF.TYPOLOGY_OF[i.rsplit('_', 1)[0]] == typ]
            per = pd.DataFrame({'v': [b.get((i, mat), 0.0) for i in ids],
                                'Typology': typ, 'Subtype': [BF.SUBTYPE_OF[i.rsplit('_', 1)[0]] for i in ids]})
            assert v == pytest.approx(BF.pool(per, ['v']).loc[typ, 'v'], rel=1e-12, abs=1e-12), (y, typ, mat)


def test_unmapped_classes_held_at_2025():
    dec = pd.read_csv(BF.OUT_DECARB)
    dec = dec[dec.Variant == 'horup_material']
    for mat in ('PLASTERBOARD', 'PLASTICS & PAINT'):
        d = dec[dec.Material == mat].pivot(index='Year', columns='Typology', values='A13_kgCO2e_per_m2')
        assert np.allclose(d.values, d.loc[2025].values, rtol=0, atol=0)


def test_soil_and_2025_unchanged(runs):
    b0, b1 = runs
    assert np.array_equal(b0['flow_annual']['SOIL'].values, b1['flow_annual']['SOIL'].values)
    assert b0['_soil'] == b1['_soil']
    assert np.array_equal(b0['carbon_total_typ'].loc[2025].values, b1['carbon_total_typ'].loc[2025].values)
    assert np.array_equal(b0['results']['50th']['total'], b1['results']['50th']['total'])   # floor area


def test_only_a1_a3_changes(runs):
    b0, b1 = runs
    for stg in ('A4-A5', 'B2,B4', 'C1-C4'):
        for t in b1['typ_names']:
            assert np.ndim(b1['stage_path'][stg][t]) == 0 and b1['stage_path'][stg][t] == b0['stage_path'][stg][t]
    d_total = b0['tot_carbon_median'] - b1['tot_carbon_median']
    d_upfront = b0['_upfront'] - b1['_upfront']
    assert d_total > 0 and d_upfront == pytest.approx(d_total, rel=1e-9)
    assert (b1['carbon_total_typ'].iloc[1:].values < b0['carbon_total_typ'].iloc[1:].values).all()


def test_history_unchanged(runs):
    import PB
    b0, b1 = runs
    h0 = PB.historical_emissions(b0, range(2016, 2026))
    h1 = PB.historical_emissions(b1, range(2016, 2026))
    assert np.array_equal(h0['I_sec_kg'].values, h1['I_sec_kg'].values)


def test_mc_bootstrap_stream_unchanged():
    """The decarbonised bootstrap reuses the same resampled cases: the 2025-factor
    draws are identical in both modes."""
    import Boss
    import MonteCarlo as MC
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            s0 = MC.build_setup(dict(DECARB_MODE='none'))
            s1 = MC.build_setup(dict(DECARB_MODE='horup_material'))
        assert np.array_equal(s0['boot_emb'], s1['boot_emb']) and np.array_equal(s0['boot_up'], s1['boot_up'])
        assert s1['boot_red'].shape == (MC.N_BOOT, len(s1['typ']), len(s1['fy']))
        assert np.allclose(s1['boot_red'][:, :, 0], 0.0)
    finally:
        importlib.reload(Boss)
