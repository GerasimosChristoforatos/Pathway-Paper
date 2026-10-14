"""Accounting identities the model must satisfy exactly (floating-point tolerance).

Each test names the identity it checks. They guard the bookkeeping, not the
assumptions: a test here can only fail if a calculation is inconsistent with
itself.
"""
import numpy as np
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
    lhs = (B['d_hh'] + sc['allow'] + sc['change'] + sc['demol'] + sc['uncons'] + sc['rv']).loc[yh[1:]]
    rhs = B['hist_built_units'].loc[yh[1:]]           # completion rate x lagged consents
    assert close(lhs, rhs)


def test_history_reconstructed_by_demand_bands(B):
    """Sum of the historical demand bands == dwellings built x realised dwelling size, 1992-2025
    (== built floor area exactly when there is no completion lag)."""
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
             + R['join'] + R['absorbed'] + R['wave'])
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
    import engine
    S = B['stock_fwd'][pct]
    d_raw = np.insert(np.diff(B['households_forecast'][pct]), 0, 0)
    if (d_raw[1:] < 0).any():
        pytest.skip('household decline floored in this path; identity holds only for unfloored years')
    # dwellings from the engine's units (2026 floor area may be an observation, not dwellings x D)
    built_all = engine.requirement(B['engine_out'][pct])
    net_repl = S['demol'] + S['uncons'] + S['join_redev']
    d_stock = np.diff(S['stock'] + S['stock_join'])
    assert close(d_stock, (built_all - net_repl)[1:])


def test_rv_share_of_all_dwellings_built(B):
    """RV units == rv_share x all dwellings built (in scope + RV), 2026-2050."""
    import engine
    S = B['stock_fwd']['50th']
    rv = -S['rv']
    assert close((rv / engine.requirement(B['engine_out']['50th']))[1:], B['rv_share'])


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


def test_figure_bands_in_scope_sum_to_total(B):
    """The in-scope demand bands (each scaled by 1 - RV share) add up exactly to the typology total, every year
    2026-2050, for floor area and carbon; MODEL v3.0.0: only the bands negative by construction
    (naming.NEGATIVE_BANDS) are negative."""
    import naming as N
    for key, ref in (('gfa', B['evol_typ_total'].sum(axis=1).values[1:] / 1e6),
                     ('carbon', B['carbon_total_typ'].sum(axis=1).values[1:] / 1e6)):
        bands, total = B['fig_bands'][key]
        assert close(total, ref, rel=1e-12)
        assert all(np.all(np.asarray(v) >= 0) for _, v, b in bands if b not in N.NEGATIVE_BANDS)
        assert all(np.all(np.asarray(v) <= 0) for _, v, b in bands if b in N.NEGATIVE_BANDS)
        assert close(sum(v for _, v, _ in bands), ref, rel=1e-12)


def test_band_stack_is_the_total(B):
    """MODEL v3.0.0 time-series sign rule (figures.draw.stack_series): positives stacked up from zero, negatives
    down from zero; up + down equals the in-scope total every year (annual floor area, annual and cumulative carbon)
    to 1e-12; the net is drawn as one black line."""
    import matplotlib.pyplot as plt
    import naming as N
    from figures import draw as plotting
    yrs = np.asarray(B['forecast_years'])[1:]
    cases = [B['fig_bands']['gfa'], B['fig_bands']['carbon'],
             ([(l, np.cumsum(v), c) for l, v, c in B['fig_bands']['carbon'][0]],
              np.cumsum(B['fig_bands']['carbon'][1]))]
    for bands, total in cases:
        fig, ax = plt.subplots()
        up, dn = plotting.stack_series(ax, yrs, [(b, v) for b, (_, v, _) in zip(N.BANDS_IN_SCOPE, bands)],
                                       net=np.asarray(total, float))
        assert len([ln for ln in ax.get_lines() if ln.get_gid() == plotting.NET_GID]) == (1 if (dn < 0).any() else 0)
        plt.close(fig)
        assert close(up + dn, np.asarray(total, float), rel=1e-12)


def test_household_size_shape_passes_through_published_knots():
    """S_TAIL interpolation reproduces every published Stats NZ value exactly and is
    flat after the last knot."""
    import projection
    S_k, S_ann, _ = projection.statsnz_size_shape(projection.HH_SIZE_VARIANT, np.arange(2025, 2051), tail=projection.S_TAIL)
    yrs = S_k['Year'].astype(int).values
    assert close(S_ann.loc[yrs].values, S_k['S'].values, rel=1e-12)
    if projection.S_TAIL == 'hermite_clamped':
        assert close(S_ann.loc[yrs[-1]:].values, np.full(len(S_ann.loc[yrs[-1]:]), S_k['S'].values[-1]), rel=1e-12)


def test_d05_history_bands_sum_to_dwellings_built(B):
    """D05c history (validation.stock_identity_history, MODEL v1.1.0): per census interval, new
    households + vacancy + census-measured net replacement + retirement villages + unexplained
    building = dwellings built (in scope); the census-measured replacement is the interval's rate
    of the census dwelling-count identity (D07) x the previous year's stock; the unexplained band
    is the household-identity residual minus that replacement."""
    import validation
    h = validation.stock_identity_history(B)
    parts = ['new_households_per_year', 'vacancy_per_year', 'net_replacement_census_per_year',
             'retirement_villages_per_year', 'unexplained_building_per_year']
    assert np.allclose(h[parts].sum(axis=1), h['dwellings_built_per_year'], rtol=1e-12, atol=1e-6)
    built = B['hist_built_units']
    for r in h.itertuples():
        assert r.dwellings_built_per_year == pytest.approx(built.loc[r.year_start:r.year_end].mean(), rel=1e-12)
    rates = B['census_rates'].set_index('y1')['rate']
    for r in h[h['households_from'] == 'census'].itertuples():
        assert r.net_replacement_rate == pytest.approx(rates.loc[r.year_end], rel=1e-15)
    cal = validation._consistent_calibration(B)
    for r in h.itertuples():
        yrs = slice(r.year_start, r.year_end)
        assert r.net_replacement_census_per_year == pytest.approx(r.net_replacement_rate * cal['prev'].loc[yrs].mean(),
                                                                  rel=1e-12)
        assert r.unexplained_building_per_year == pytest.approx(
            r.household_identity_residual_per_year - r.net_replacement_census_per_year, rel=1e-9, abs=1e-6)
    assert list(h['interval'])[:6] == ['1991-1996', '1996-2001', '2001-2006', '2006-2013', '2013-2018', '2018-2023']


def test_d04_interval_sums_equal_annual_sums(B):
    """D04c history (validation.household_formation_history, MODEL v1.1.0): per census interval,
    interval mean x length = the sum of the annual values within the interval, for both parts; the
    two parts add up to the census-anchored change in households."""
    import validation
    h = validation.household_formation_history(B)
    pop, hh, S_ = B['hist_pop'], B['hist_hh'], B['hist_S']
    for r in h.itertuples():
        yrs = range(r.year_start, r.year_end + 1)
        pop_part = sum(float((pop.loc[y] - pop.loc[y - 1]) / S_.loc[y]) for y in yrs)
        d_hh = sum(float(hh.loc[y] - hh.loc[y - 1]) for y in yrs)
        assert r.from_population_growth_per_year * r.years == pytest.approx(pop_part, rel=1e-12)
        assert (r.from_population_growth_per_year + r.from_household_size_change_per_year) * r.years == \
            pytest.approx(d_hh, rel=1e-12)
        assert d_hh == pytest.approx(r.households_end - r.households_start, rel=1e-12)
