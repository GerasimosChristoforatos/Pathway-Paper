"""The completion lag (monthly, L = 17), the completion rate 0.945, the TL1 speed limit and the household-size
sensitivities.

  * the lag: L = 0 equals the calendar-year sums, the pipeline years, the observed building in every run;
  * TL1: the speed-limited path, its rate and the year its level is reached;
  * building >= 0 in every run and > 0 in every TL-family year of the deterministic runs (runs.csv).
Band sums, waterfall sums, Shapley efficiency, ordering and the solution-space markers are tested by the other test
files."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT

RTOL = 1e-9


def _data(rel):
    import layout
    return layout.data(rel)


def test_lag_zero_is_the_calendar_year_sums():
    import projection
    df = projection.load_consents()
    cols = list(projection.COL_TYPOLOGIES.values()) + [projection.COL_DWELLINGS_TOTAL]
    lagged, info = projection.lagged_consents(df, 0, cols, projection.COL_DWELLINGS_TOTAL)
    a = lagged.groupby('Year')[cols].sum()
    b = df.groupby(df['Date'].dt.year)[cols].sum()
    b.index.name = 'Year'
    pd.testing.assert_frame_equal(a.loc[1991:2025], b.loc[1991:2025], check_exact=True)


def test_pipeline_years_and_observed_building(B):
    import projection
    df = projection.load_consents()
    assert projection.pipeline_years(df, 0) == []
    assert projection.pipeline_years(df, 17) == [2026, 2027]
    # consents to September 2026 (MODEL v4.6.0): at L = 15, 2027 is observed too (October 2025 - September 2026);
    # with the data of MODEL v4.0-v4.5 (to July 2026) it was not
    assert projection.pipeline_years(df, 15) == [2026, 2027]
    assert projection.pipeline_years(df[df['Date'] <= '2026-07-01'], 15) == [2026]
    assert projection.pipeline_years(df, 19) == [2026, 2027]
    assert B['lag_months'] == projection.COMPLETION_LAG_MONTHS == 17
    assert B['pipe']['years'] == [2026, 2027] and B['absorption_start'] == 2027
    import engine
    built = np.asarray(engine.requirement(B['engine_out']['50th']), float)
    for k, y in enumerate(B['pipe']['years'], start=1):
        assert np.isclose(built[k], B['pipe']['built_all'][y], rtol=1e-9), (y, built[k])
        assert np.isclose(B['pipe']['built_all'][y], projection.COMPLETION_RATE * B['pipe']['consents_all'][y],
                          rtol=1e-12)
    ji = B['join_info']['50th']
    assert ji['n_observed'] == 2 and np.isclose(ji['gap_ref'], ji['O_obs'][-1] - ji['R_next'], rtol=1e-12)


def test_completion_rate_central_is_the_band_midpoint():
    import MonteCarlo as MC
    import projection
    lo, hi = projection.COMPLETION_RATE_BAND
    assert (lo, hi) == (0.93, 0.96) and projection.COMPLETION_RATE == pytest.approx((lo + hi) / 2, abs=1e-15)
    d = MC.distributions(dict(size_sigma=0.1, completion=projection.COMPLETION_RATE))['complete']
    assert d.ppf(0.5) == pytest.approx(projection.COMPLETION_RATE, abs=1e-12)
    assert d.ppf(0.0) == pytest.approx(lo) and d.ppf(1.0) == pytest.approx(hi)


def test_tl1_speed_limit():
    with open(_data('pathways/levers.json')) as f:
        lv = json.load(f)
    sp = lv['L1']['tl_speed']
    assert sp['on'] and sp['interval'] == [1996, 2001] and sp['start'] == 2026
    rates = [r['rate'] for r in sp['intervals']]
    assert sp['rate'] == max(rates) and sp['census_years'][0] == 1991 and sp['census_years'][-1] == 2023
    path = {int(y): v for y, v in sp['path'].items()}
    S = {int(y): v for y, v in lv['L1']['S_ref'].items()}
    gap = {int(y): v for y, v in lv['L1']['gap'].items()}
    w = {int(y): v for y, v in lv['adoption']['w'].items()}
    amb = {y: S[y] + w[y] * gap[y] for y in S}                    # the Ambitious path on the adoption window
    years = sorted(y for y in path if y >= 2026)
    for y in years:
        cap = min(sp['S_start'] + sp['rate'] * (y - 2026), sp['level'])
        assert path[y] == pytest.approx(max(cap, amb[y]), rel=1e-12)
    assert path[2026] == pytest.approx(sp['S_start'], rel=1e-15) and max(path.values()) <= sp['level'] + 1e-12
    assert np.isclose(sp['level_reached'], 2026 + (sp['level'] - sp['S_start']) / sp['rate'], rtol=1e-12)


def test_building_nonnegative_and_positive_in_tl_years():
    runs = pd.read_csv(_data('pathways/runs.csv'))
    assert (runs['dwellings_built_min_year'] >= -1e-6).all(), runs.loc[runs['dwellings_built_min_year'] < -1e-6, 'run']
    # the greedy re-occupation row (TL-reoccupation-fast: the pool meets each year's need as far as it can) builds
    # nothing in years the pool covers, by definition; it is reported (pathways/theoretical_limit.json), not a TL run
    tl = runs[(runs['run'].str.startswith('TL') | runs['run'].str.endswith('-tl'))
              & (runs['run'] != 'TL-reoccupation-fast')]
    assert len(tl) and (tl['dwellings_built_min_year'] > 0).all(), tl.loc[tl['dwellings_built_min_year'] <= 0, 'run']
    with open(_data('pathways/theoretical_limit.json')) as f:
        zb = json.load(f)['zero_building']
    assert zb['adopted_tl_family_runs_with_zero_years'] == [], zb


def test_household_size_sensitivity_table():
    t = pd.read_csv(_data('sensitivity/household_size.csv'))
    assert set(t['run']) == {'Reference', 'pathway-moderate', 'pathway-ambitious', 'TL'}
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sensitivity_tables as T
    assert len(t) == 4 * len(T.HH_VARIANTS)          # each household-size row for the four runs
    runs = pd.read_csv(_data('pathways/runs.csv'))
    ref = runs[runs['scenario'] == 'REF'].set_index('run')
    for _, r in t.iterrows():
        key = 'REF' if r['run'] == 'Reference' else r['run']
        assert np.isclose(r['central_carbon_kt'], ref.loc[key, 'carbon_kt'], rtol=1e-12)

def test_gap_2026_reports_pre_pipeline_dwelling_requirement(B):
    """The gap diagnostic uses the exact unjoined dwelling requirement, not final pipeline building."""
    import engine
    import gap_2026

    i26 = list(B['forecast_years']).index(2026)
    E = B['engine_out']['50th']
    expected = float(B['join_info']['50th']['R26'])

    assert gap_2026.requirement_2026(B) == pytest.approx(expected, rel=1e-12)
    # The final path includes the pipeline join; removing it recovers R26.
    assert float(engine.requirement(E)[i26] - E['join'][i26]) == pytest.approx(expected, rel=1e-12)


def test_ar_base_at_completion_rate_reproduces_the_run():
    """F5: the Monte Carlo's base at a completion rate (boundaries.history_at_completion) is the base of a projection
    run at that rate; at the run's own rate it reproduces the run."""
    import boundaries as BD
    from conftest import run_boss
    B = run_boss()
    typ = list(B['typ_names'])
    up, age = BD.reference_factors(B, typ)
    base = lambda h: BD.base_with_factors(h, typ, up, BD.AR_BASE_WINDOW, age)
    h0 = BD.historical_emissions(B, range(BD.HIST_START, 2026))
    assert base(BD.historical_emissions(BD.history_at_completion(B, float(B['built_factor'])),
                                        range(BD.HIST_START, 2026), with_events=False)) == pytest.approx(base(h0),
                                                                                                         rel=1e-12)
    B93 = run_boss(COMPLETION_RATE=0.93)
    h93 = BD.historical_emissions(BD.history_at_completion(B, 0.93), range(BD.HIST_START, 2026), with_events=False)
    assert base(h93) == pytest.approx(BD.window_base(B93, BD.AR_BASE_WINDOW)[0], rel=1e-12)
    assert base(h93) < base(h0)
