"""Accounting identities the model must satisfy exactly (floating-point tolerance).

Each test names the identity it checks. They guard the bookkeeping, not the
assumptions: a test here can only fail if a calculation is inconsistent with
itself.
"""
import numpy as np
import pandas as pd
import pytest

from conftest import run_boss

REL = 1e-9
PCTS = ['5th', '50th', '95th']


def close(a, b, rel=REL):
    a, b = np.asarray(a, float), np.asarray(b, float)
    scale = max(np.abs(b).max(), 1.0)
    return np.abs(a - b).max() <= rel * scale


# ---------------------------------------------------------------- inputs ----
def test_typology_floor_area_sums_to_published_total(B):
    """Sum of the three typology GFA columns == the published total, every year."""
    assert close(B['hist_typ_gfa'].sum(axis=1), B['hist_total_gfa'])


def test_historical_shares_sum_to_one(B):
    assert close(B['hist_shares'].sum(axis=1), 1.0)
    assert (B['hist_shares'].values > 0).all()


def test_blended_dwelling_size_is_dwelling_weighted(B):
    """Harmonic GFA-share blend of typology sizes == total GFA / total dwellings."""
    sizes, sh = B['hist_dwelling_size'], B['hist_shares']
    blended = 1.0 / sum(sh[t] / sizes[t] for t in B['typ_names'])
    assert close(blended, B['hist_total_gfa'] / B['hist_total_units'])


def test_factor_total_is_materials_plus_soil(B):
    """Typology intensity used == sum of in-scope material factors + soil."""
    for t in B['typ_names']:
        mats = B['MAT_INTENSITY'][t].sum()
        assert abs(mats + B['SOIL_INTENSITY'][t] - B['T_BASELINE_2025'][t]) < 1e-6


# ---------------------------------------------------------------- history ---
def test_historical_stock_identity(B):
    """Calibration: new households + vacancy allowance + vacancy change
    + demolitions + residual - RV units == in-scope dwellings built, every year."""
    sc, yh = B['stock_cal'], B['years_hist']
    import Boss
    lhs = (B['d_hh'] + sc['allow'] + sc['change'] + sc['demol'] + sc['uncons'] + sc['rv']).loc[yh[1:]]
    rhs = B['hist_built_units'].loc[yh[1:]]           # completion rate x lagged consents
    assert close(lhs, rhs)


def test_history_reconstructed_by_demand_bands(B):
    """Sum of the historical demand bands == dwellings built x realised dwelling size, 1992-2025
    (== built floor area exactly when there is no completion lag)."""
    import Boss
    YH = np.arange(1992, 2026)
    D = B['blended_dwelling_size'].loc[YH]
    sc = B['stock_cal']
    parts = [B['hist_growth'].loc[YH] - B['hist_avoided'].loc[YH],
             B['hist_hs_raw'].loc[YH].clip(lower=0),
             B['d_hh'].loc[YH] * (D - B['occupied_area_per_dwelling'].loc[YH])]
    parts += [sc[k].loc[YH] * D for k in ('allow', 'change', 'demol', 'uncons', 'rv')]
    assert close(sum(parts), B['hist_built_units'].loc[YH] * D, rel=1e-12)


# ---------------------------------------------------------------- forward ---
def test_population_paths_start_at_observed_2025(B):
    obs = B['hist_pop'].loc[2025]
    for p in PCTS:
        assert abs(B['df_forecast'][f'PopTotal_{p}'].iloc[0] - obs) < 1e-6


def test_projected_shares_sum_to_one(B):
    sh = B['evolving_gfa_shares']
    assert close(sh.sum(axis=1), 1.0)
    assert (sh.values > 0).all()


@pytest.mark.parametrize('pct', PCTS)
def test_forward_bands_sum_to_total(B, pct):
    """growth + house-splitting + extra space + vacancy + replacement + residual
    + RV (negative) == total, every year including the 2025 anchor."""
    R = B['results'][pct]
    parts = (R['growth'] + R['hs_pos'] + R['extra'] + R['vac'] + R['repl'] + R['unc'] + R['rv']
             + R['join'])
    assert close(parts, R['total'])


@pytest.mark.parametrize('pct', PCTS)
def test_forward_structural_identity(B, pct):
    """total == structural (new households x occupied area) + gross consumption."""
    R = B['results'][pct]
    assert close(R['total'][1:], (R['structural'] + R['c_gross'])[1:])


@pytest.mark.parametrize('pct', PCTS)
def test_forward_stock_identity(B, pct):
    """Change in dwelling stock == all dwellings built (in scope + RV) - net
    replacement (demolition + residual + the redevelopment channel of the
    near-term join), 2026-2050, where the stock includes the dwellings the join
    adds (vacancy and household channels). Holds exactly while household
    formation is not floored."""
    R, S = B['results'][pct], B['stock_fwd'][pct]
    D = B['future_dwelling_size'].values
    d_raw = np.insert(np.diff(B['households_forecast'][pct]), 0, 0)
    if (d_raw[1:] < 0).any():
        pytest.skip('household decline floored in this path; identity holds only for unfloored years')
    in_scope = R['total'] / D
    rv_units = -S['rv']
    built_all = in_scope + rv_units
    net_repl = S['demol'] + S['uncons'] + S['join_redev']
    d_stock = np.diff(S['stock'] + S['stock_join'])
    assert close(d_stock, (built_all - net_repl)[1:])


def test_rv_share_of_all_dwellings_built(B):
    """RV units == rv_share x all dwellings built (in scope + RV), 2026-2050."""
    R, S = B['results']['50th'], B['stock_fwd']['50th']
    in_scope = R['total'] / B['future_dwelling_size'].values
    rv = -S['rv']
    assert close((rv / (in_scope + rv))[1:], B['rv_share'])


def test_typology_split_sums_to_total(B):
    assert close(B['evol_typ_total'].sum(axis=1).values[1:], B['results']['50th']['total'][1:])


# ---------------------------------------------------------------- carbon ----
def test_material_plus_soil_equals_typology_carbon(B):
    fa = B['flow_annual']
    assert close(fa.sum(axis=1).values, B['carbon_total_typ'].iloc[1:].sum(axis=1).values)


def test_stages_plus_soil_equal_total_carbon(B):
    tot = B['tot_carbon_median']
    assert abs(B['_st_tot'] + B['_soil'] / 1e6 - tot) < 1e-6 * tot


def test_demand_band_carbon_sums_to_total(B):
    assert abs(B['dem_mat'].values.sum() / 1e6 - B['tot_carbon_median']) < 1e-6 * B['tot_carbon_median']


# ---------------------------------------------------------------- hygiene ---
def test_boss_is_deterministic_and_leaks_no_state(B):
    """A second run after a run with a changed setting reproduces the first."""
    run_boss(DEMOLITION_CALIB_START=2019, COMPLETION_RATE=0.92)
    B2 = run_boss()
    assert np.array_equal(B2['results']['50th']['total'], B['results']['50th']['total'])
    assert np.array_equal(B2['carbon_total_typ'].values, B['carbon_total_typ'].values)
