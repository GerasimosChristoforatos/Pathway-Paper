"""The adopted household settings (households after the 2023 census = ERP / the household-size path) and the
household size from the Stats NZ 2023-base family and household projections."""
import os

import numpy as np
import pandas as pd
import pytest

from conftest import run_boss


def test_defaults_unchanged(B):
    import projection
    # adopted: the Stats NZ 2023-base household-size path, Medium A
    assert projection.HH_SIZE_PATH == 'statsnz_2023'
    assert (projection.HH_SIZE_VARIANT, projection.HH_PROPENSITY) == ('Medium', 'A')
    assert projection.HH_SIZE_PAIRED == {'5th': 'Low', '50th': None, '95th': 'High'}


def test_erp_bridge_households_are_erp_over_the_s_path():
    import projection
    B = run_boss()
    yb = [2024, 2025]
    S = projection.household_size_path(B['hist_S'], yb)        # anchored on 2023, unchanged by the bridge
    assert np.allclose(B['hist_hh'].loc[yb].values, B['hist_pop'].loc[yb].values / S, rtol=1e-12)
    assert np.isclose(B['hist_S'].loc[2023], B['hist_pop'].loc[2023] / B['hist_hh'].loc[2023], rtol=1e-15)


def test_household_projection_2023base_from_the_raw_tables():
    """data/derived/households_proj_2023base.csv is people in households (POPPR_FHH_008: LAT total, both sexes, all
    ages) over total households (POPPR_FHH_010: HH) of each projection, and Medium A / B give the published path."""
    import projection
    raw = os.path.join(os.path.dirname(projection.FILE_HOUSEHOLDS_PROJ_2023), '..', 'raw')
    p = pd.read_csv(os.path.join(raw, 'POPPR_FHH_008.csv'))
    p = p[(p['LAT_POPPR_FHH_008'] == 'LAT') & (p['SEX_POPPR_FHH_008'] == 3) & (p['AGE_POPPR_FHH_008'] == 'TOTALALLAGES')]
    h = pd.read_csv(os.path.join(raw, 'POPPR_FHH_010.csv'))
    h = h[h['MEASURE_POPPR_FHH_010'] == 'HH']
    d = pd.read_csv(projection.FILE_HOUSEHOLDS_PROJ_2023)
    assert len(d) == 36
    for _, r in d.iterrows():
        code = f"{r['Variant'].upper()}{r['Propensity']}"
        pop = p[(p['PROJECTION_POPPR_FHH_008'] == code) & (p['YEAR_POPPR_FHH_008'] == r['Year'])]['OBS_VALUE']
        hh = h[(h['PROJECTION_POPPR_FHH_010'] == code) & (h['YEAR_POPPR_FHH_010'] == r['Year'])]['OBS_VALUE']
        assert len(pop) == len(hh) == 1
        assert (r['Population'], r['Households']) == (float(pop.iloc[0]), float(hh.iloc[0]))
        assert r['S'] == pytest.approx(r['Population'] / r['Households'], rel=1e-9)
    s = lambda prop: projection.statsnz_2023_knots('Medium', prop)['S'].round(3).tolist()
    assert s('A') == [2.741, 2.689, 2.633, 2.584, 2.548, 2.524]
    assert s('B')[0] == 2.741 and s('B')[-1] == 2.648


def test_household_size_paths_rebased_and_paired(B):
    """S(t) = S_obs(2023) x S_StatsNZ(t) / S_StatsNZ(2023) for the median (Medium A) and the 5th / 95th population
    paths (Low A / High A: the same percentiles); through every knot; after 2048 linear at the rebased 2043-2048
    secant slope (S_TAIL 'pchip_secant')."""
    import projection
    fy = np.asarray(B['forecast_years'])
    S0 = float(B['hist_S'].loc[projection.S_ANCHOR_YEAR])
    for pct, v in (('5th', 'Low'), ('50th', 'Medium'), ('95th', 'High')):
        k, sh, _ = projection.statsnz_size_shape(v, fy, tail=projection.S_TAIL)
        assert np.allclose(sh.loc[k['Year']].values, k['S'].values, rtol=1e-12)
        want = S0 * sh.reindex(fy).values / float(sh.loc[projection.S_ANCHOR_YEAR])
        got = B['df_forecast'][f'PopTotal_{pct}'].values / B['households_forecast'][pct]
        assert np.allclose(got, want, rtol=1e-12), pct
        s = k['S'].values
        slope = S0 * (s[-1] - s[-2]) / 5.0 / float(sh.loc[projection.S_ANCHOR_YEAR])
        assert got[fy == 2050][0] == pytest.approx(got[fy == 2048][0] + 2 * slope, rel=1e-12)


def test_six_display_bands_sum_to_the_detailed_bands():
    import bands as BANDS
    import layout
    from figures import draw as P
    data = lambda rel: pd.read_csv(layout.data(rel))
    m = data('bands_display_map.csv')
    assert dict(zip(m['band_id'], m['display_id'])) == BANDS.DISPLAY
    assert len(set(BANDS.DISPLAY.values()) - {'released_tl', 'maintenance'}) == 6
    for rel, val, keys in (('baseline/bands_annual.csv', 'floor_area_Mm2', ['year']),
                           ('baseline/bands_annual.csv', 'carbon_kt', ['year']),
                           ('baseline/bands_history.csv', 'floor_area_Mm2_per_year', ['interval']),
                           ('pathways/bands_annual.csv', 'carbon_kt', ['scenario', 'run', 'year'])):
        d = data(rel)
        if 'definition' in d:
            d = d[d['definition'] == 'in_scope']
        d['display'] = [BANDS.DISPLAY[P.band_id(b)] for b in d['band']]
        detailed = d.groupby(keys)[val].sum()
        six = d.groupby(keys + ['display'])[val].sum().groupby(level=list(range(len(keys)))).sum()
        assert np.allclose(six.values, detailed.loc[six.index].values, rtol=1e-9, atol=1e-12), rel


def test_history_rv_allocated_pro_rata_in_scope():
    """The history's RV exclusion spread pro rata: no RV band, the same total in every interval."""
    import bands as BANDS
    import layout
    from figures import draw as P
    h = pd.read_csv(layout.data('baseline/bands_history.csv'))
    for iv, g in h.groupby('interval'):
        det = {P.band_id(b): v for b, v in zip(g['band'], g['floor_area_Mm2_per_year'])}
        al = BANDS.allocate_rv(det)
        assert 'retirement_villages' not in al
        assert np.isclose(sum(al.values()), g['observed_built_Mm2_per_year'].iloc[0], rtol=1e-9, atol=1e-12), iv


def test_starting_surplus_rule_and_propagation(B):
    """F1: the adopted STARTING_SURPLUS is what the rule fixed in advance gives on the Reference; the residuals are
    the D05 history's unexplained building; the surplus enters the absorption pool and the surplus stock and is
    absorbed by OVERBUILD_ABSORPTION_END."""
    import importlib
    import engine
    import projection
    import validation
    projection = importlib.reload(projection)          # the adopted settings (earlier run_boss calls change them)
    f = B['f1_residuals']
    assert f['rule_carry'] == (f['r_after'] > f['m'] + projection.F1_SD_MULTIPLE * f['s'])
    assert projection.STARTING_SURPLUS == ('carry' if f['rule_carry'] else 'none')
    assert f['n_after'] == 2 and f['after_years'] == [2024, 2025]
    n = np.asarray(f['interval_years'], float)
    r = np.asarray(f['interval_means'], float)
    assert f['m'] == pytest.approx(float(f['residual'].loc[1992:2023].mean()), rel=1e-12)    # time-weighted
    assert f['s'] == pytest.approx(float(np.sqrt((n * (r - f['m']) ** 2).sum() / n.sum())), rel=1e-12)
    h = validation.stock_identity_history(B).set_index('interval')['unexplained_building_per_year']
    assert np.allclose(h.values, list(r) + [f['r_after']], rtol=1e-10, atol=1e-6)
    s0 = B['start_surplus']
    assert s0 == pytest.approx(engine.starting_surplus(f, projection.STARTING_SURPLUS), rel=1e-15) and s0 > 0
    ji, E = B['join_info']['50th'], B['engine_out']['50th']
    fy = np.asarray(B['forecast_years'])
    assert ji['start_surplus'] == s0 and E['stock_join'][0] == pytest.approx(s0, rel=1e-15)
    assert np.allclose(E['stock_join'], ji['surplus'], rtol=1e-12, atol=1e-6)
    assert abs(E['stock_join'][fy == projection.OVERBUILD_ABSORPTION_END][0]) < 1e-6


def test_starting_surplus_engine():
    """engine.starting_surplus and the pool: none is 0, minus 2 SD subtracts 2 s per year, never negative; the
    starting surplus is paid back, never built (join = excess - payback)."""
    import engine
    res = dict(m=-500.0, s=3000.0, r_after=9000.0, n_after=2)
    assert engine.starting_surplus(res, 'none') == 0.0
    assert engine.starting_surplus(res, 'carry') == pytest.approx(19000.0)
    assert engine.starting_surplus(res, 'carry_minus_2sd') == pytest.approx(7000.0)
    assert engine.starting_surplus(dict(res, r_after=-1000.0), 'carry') == 0.0
    n = 12
    w = engine.logistic_weights(np.arange(2025, 2025 + n), 2026, 2031)
    need = np.full(n, 30000.0)
    join, ab = engine.absorb_overbuild(np.zeros(n), w, need, start=5000.0)
    assert ab['C'][0] == 5000.0 and ab['paid'].sum() == pytest.approx(5000.0) and abs(ab['U'][-1]) < 1e-9
    assert np.allclose(join, -ab['paid'])
