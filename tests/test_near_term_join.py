"""Near-term market excess, the 2026 nowcast estimators and replacement scenarios.

Pure-function tests on SYNTHETIC inputs (nothing here enters data/ or the
model), plus the identities the central run must satisfy under the join.
"""
import numpy as np
import pandas as pd
import pytest

import engine
from test_identities import close

YEARS = np.arange(2025, 2051)


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


# ------------------------------------------------------------ toy forward ----
def _toy_forward(join=None, join_redev=None):
    n = len(YEARS)
    pop = np.linspace(5.3e6, 6.3e6, n)
    hh = pop / np.linspace(2.65, 2.60, n)
    shares = pd.DataFrame({'Detached': np.full(n, 1.0)}, index=YEARS)
    return engine.forward(pop, hh, np.insert(np.diff(pop), 0, 0), 0.054, 0.00135, -0.0002, 0.0, 0.0,
                          0.05, shares, {'Detached': 150.0}, {'Detached': 50.0},
                          {'Detached': 400.0}, {'Detached': 300.0}, join=join, join_redev=join_redev)


# ------------------------------------------------ market excess (v1.1) ----
@pytest.mark.parametrize('mode,absorption', [('redevelopment', 0.0), ('surplus', 0.2), ('surplus', 0.0)])
def test_market_excess_rule(mode, absorption):
    E0 = _toy_forward()
    R = engine.requirement(E0)
    b26, rho = R[1] + 5000.0, 0.6
    join, ji = engine.market_excess(E0, b26, rho, '2027', mode, absorption)
    E1 = _toy_forward(join, ji['redev'])
    built = engine.requirement(E1)
    assert close(built[1], b26)                                    # 2026 = observed
    gap = b26 - R[2]
    k = np.arange(len(R))
    if mode == 'redevelopment':
        assert close(built[2:] - R[2:], gap * rho ** (k[2:] - 1))  # no absorption, no payback
        assert close(E1['stock_join'], np.zeros(len(R)))            # stock-neutral
    else:
        assert close(E1['stock_join'][1:], ji['surplus'][1:])       # surplus adds to the stock
        if absorption == 0.0:
            assert close(built[2:] - R[2:], gap * rho ** (k[2:] - 1))
    net = E1['demol'] + E1['unc'] + E1['join_redev']
    assert close(np.diff(E1['stock'] + E1['stock_join']), (built - net)[1:])


def test_population_nowcast_is_a_permanent_level_shift():
    """Observed 2026 growth shifts every later population level by (observed - projected)."""
    from conftest import run_boss
    base, now = run_boss(NOWCAST_POPULATION=False), run_boss()
    fy = list(base['forecast_years'])
    i26 = fy.index(2026)
    P = lambda B: B['df_forecast']['PopTotal_50th'].values
    assert close(P(now)[i26:] - P(base)[i26:], np.full(len(fy) - i26, now['pop_nowcast']['shift']))
    assert close(P(now)[:i26], P(base)[:i26])
