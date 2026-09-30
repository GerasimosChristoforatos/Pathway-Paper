"""A1: near-term join (nowcast + three channels) and replacement scenarios.

Pure-function tests on SYNTHETIC inputs (nothing here enters data/ or the
model), plus the identities the central run must satisfy under the join.
"""
import numpy as np
import pandas as pd
import pytest

import engine
from test_identities import close

YEARS = np.arange(2025, 2051)
SHARES = dict(redevelopment=0.5, vacancy=0.2, households=0.3)


# ------------------------------------------------------ replacement_path ----
def test_replacement_path_scenarios():
    long, recent = 0.001, 0.004
    assert close(engine.replacement_path('S1', long, recent, YEARS), np.full(len(YEARS), long))
    assert close(engine.replacement_path('S2', long, recent, YEARS), np.full(len(YEARS), recent))
    p = engine.replacement_path('S3', long, recent, YEARS, half_life=10)
    assert close(p[0], recent)
    assert close(p[10], (long + recent) / 2)                 # one half-life after 2025
    assert np.all(np.diff(p) < 0) and np.all(p > long)
    with pytest.raises(ValueError):
        engine.replacement_path('S4', long, recent, YEARS)


# --------------------------------------------------------- join_channels ----
@pytest.mark.parametrize('mode', ['permanent', 'reverting'])
@pytest.mark.parametrize('horizon', [3, 5, 10])
def test_join_channels_conserve_and_draw_down(mode, horizon):
    excess = {2026: 1000.0, 2027: -250.0}                    # negative excess treated symmetrically
    join, ch = engine.join_channels(YEARS, excess, SHARES, horizon, mode)
    tot = sum(excess.values())
    assert close(ch['redevelopment'].sum(), SHARES['redevelopment'] * tot)
    assert close(ch['vacancy'].sum(), SHARES['vacancy'] * tot)
    assert close(ch['vacancy_drawdown'].sum(), -SHARES['vacancy'] * tot)     # fully drawn down
    back = ch['household_reversion'].sum()
    assert close(back, 0.0 if mode == 'permanent' else -SHARES['households'] * tot)
    kept = SHARES['redevelopment'] + (SHARES['households'] if mode == 'permanent' else 0.0)
    assert close(join.sum(), kept * tot)
    # the drawdown of 2026's vacancy runs over exactly `horizon` years after 2026
    j26, c26 = engine.join_channels(YEARS, {2026: 1000.0}, SHARES, horizon, mode)
    nz = np.nonzero(c26['vacancy_drawdown'])[0]
    assert list(YEARS[nz]) == list(range(2027, 2027 + horizon))


# ------------------------------------------------------------ nowcast ----
def _synthetic_consents(annual_2026):
    idx = pd.date_range('2010-01-01', '2025-12-01', freq='MS')
    w = np.arange(1, 13) / 78.0                              # month m has weight m
    s = pd.Series(np.tile(w, len(idx) // 12) * 1200.0, index=idx)
    s.loc['2025-01-01':'2025-12-01'] = w * 1500.0
    obs = pd.Series(w[:7] * annual_2026, index=pd.date_range('2026-01-01', periods=7, freq='MS'))
    return pd.concat([s, obs]), w


def test_nowcast_year_methods_exact_on_synthetic_seasonality():
    s, w = _synthetic_consents(2000.0)
    n = engine.nowcast_year(s, 2026, 'seasonal_share', (2010, 2025))
    assert n['months_observed'] == list(range(1, 8))
    assert close(n['total'], 2000.0)                         # exact under fixed seasonal factors
    n = engine.nowcast_year(s, 2026, 'same_period_ratio', (2010, 2025))
    assert close(n['total'], 2000.0)                         # 2025 has the same seasonal shape
    n = engine.nowcast_year(s, 2026, 'last_12_months', (2010, 2025))
    assert close(n['total'], 1500.0 * w[7:].sum() + 2000.0 * w[:7].sum())
    with pytest.raises(ValueError):
        engine.nowcast_year(s, 2026, 'arima', (2010, 2025))


# -------------------------------------------------------- nowcast_join ----
def _toy_forward(join=None, join_redev=None):
    n = len(YEARS)
    pop = np.linspace(5.3e6, 6.3e6, n)
    hh = pop / np.linspace(2.65, 2.60, n)
    shares = pd.DataFrame({'Detached': np.full(n, 1.0)}, index=YEARS)
    return engine.forward(pop, hh, np.insert(np.diff(pop), 0, 0), 0.054, 0.00135, -0.0002, 0.0, 0.0,
                          0.05, shares, {'Detached': 150.0}, {'Detached': 50.0},
                          {'Detached': 400.0}, {'Detached': 300.0}, join=join, join_redev=join_redev)


def test_nowcast_join_reproduces_observed_pipeline():
    """With the join, 2026 completions (all categories) equal the observed-
    implied value, and 2027 completions equal W x c C_2026 + (1 - W) x the
    requirement net of the 2026 drawdown."""
    c, W, C25, C26 = 0.94, 0.5, 38000.0, 42000.0
    E0 = _toy_forward()
    join, info = engine.nowcast_join(E0, C25, C26, c, W, SHARES, 5, 'permanent')
    E1 = _toy_forward(join, info['channels']['redevelopment'])
    built = engine.requirement(E1)
    assert close(built[1], c * ((1 - W) * C26 + W * C25))
    R0 = engine.requirement(E0)
    j26, _ = engine.join_channels(YEARS, {2026: info['e26']}, SHARES, 5, 'permanent')
    assert close(built[2], W * c * C26 + (1 - W) * (R0[2] + j26[2]))
    # stock identity with the join
    net = E1['demol'] + E1['unc'] + E1['join_redev']
    assert close(np.diff(E1['stock'] + E1['stock_join']), (built - net)[1:])


# ----------------------------------------------------- excess_channels ----
def _toy_census():
    census = pd.DataFrame({'total_private': [1_850_000.0, 2_010_000.0],
                           'empty': [95_000.0, 108_000.0]}, index=[2018, 2023])
    rates = pd.DataFrame([dict(y0=2018, y1=2023, rate=0.0036, stock_years=9.6e6)])
    pop = {2018: 4.87e6, 2023: 5.16e6}
    return census, rates, pop


def test_excess_channels_shares_and_scenario_dependence():
    census, rates, pop = _toy_census()
    S = pd.Series({2018: 2.78, 2023: 2.76})
    ev1 = engine.excess_channels(census, rates, pop, S, 0.00113, 2018, 2023)
    assert close(sum(ev1['shares'].values()), 1.0)
    assert close(ev1['levels']['redevelopment'], (0.0036 - 0.00113) * 9.6e6)
    ev2 = engine.excess_channels(census, rates, pop, S, 0.0036, 2018, 2023)   # S2: in requirement
    assert ev2['levels']['redevelopment'] == 0.0
    assert close(ev2['levels']['vacancy'], ev1['levels']['vacancy'])
    # household channel excluded when census household size did NOT fall faster than the shape
    S_fast = pd.Series({2018: 2.78, 2023: 2.60})
    ev3 = engine.excess_channels(census, rates, pop, S_fast, 0.00113, 2018, 2023)
    assert not ev3['households_included'] and ev3['levels']['households'] == 0.0


# ------------------------------------------------- central run, A1 on ----
def test_central_run_2026_completions_equal_nowcast(B):
    if B['_join_mode'] != 'nowcast':
        pytest.skip('near-term join not in use')
    for pct in ('5th', '50th', '95th'):
        E = B['engine_out'][pct]
        ji = B['join_info'][pct]
        assert close(engine.requirement(E)[1], ji['O26'])
