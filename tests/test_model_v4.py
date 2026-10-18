"""MODEL v4.0.0: the completion lag (monthly, L = 17), the completion rate 0.945, the TL1 speed limit, TL surplus pooling
and the household-size sensitivities (docs/CHANGELOG_v4.md).

  * equivalence: L = 0, completion rate 0.95, the TL1 speed limit and TL surplus pooling off reproduce every MODEL
    v3.3 run (the Reference projection and the 55 deterministic pathway runs of runs.csv: floor area, carbon,
    dwellings and committed emissions, 1e-9 relative; fixture tests/v3_3_runs_fixture.json from release/model-v3.3.2);
  * the lag: L = 0 equals the calendar-year sums, the pipeline years, the observed building in every run;
  * TL1: the speed-limited path, its rate and the year its level is reached;
  * building >= 0 in every run and > 0 in every TL-family year of the deterministic runs (runs.csv).
The legacy MODEL v2.1 Reference lock is tests/test_reference_legacy.py; band sums, waterfall sums, Shapley efficiency,
ordering and the Fig6 markers are tested by the existing tests on the regenerated data."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT

FIXTURE = os.path.join(ROOT, 'tests', 'v3_3_runs_fixture.json')
V33 = dict(COMPLETION_LAG_MONTHS=0, COMPLETION_RATE=0.95)        # projection settings of MODEL v3.3
RTOL = 1e-9


def _data(rel):
    import layout
    return layout.data(rel, frozen=False)


@pytest.fixture(scope='module')
def v33_flags():
    import levers as LV
    import pathways as PW
    old = (LV.TL1_SPEED_LIMIT, PW.TL_SURPLUS_POOLING)
    LV.TL1_SPEED_LIMIT, PW.TL_SURPLUS_POOLING = False, False
    yield
    LV.TL1_SPEED_LIMIT, PW.TL_SURPLUS_POOLING = old


def _levels(run):
    """(levels, ramp, re-occupation rule) of a run name of runs.csv."""
    import levers as LV
    import naming as N
    TL = LV.tl_levels(LV.TL_COMPONENTS)
    if run in N.SCENARIOS:
        return {}, None, 'constant_share'
    if run == 'TL':
        return TL, None, 'constant_share'
    if run == 'TL-from2027':
        return TL, LV.TL_FROM2027, 'constant_share'
    if run == 'TL-reoccupation-fast':
        return TL, None, 'fast'
    parts = run.split('-')
    what, setting = parts[0], parts[1]
    ramp = parts[2] if len(parts) > 2 else None
    if what in LV.LEVERS:
        return {what: setting}, ramp, 'constant_share'
    return LV.pathway_levers(what, setting), ramp, 'constant_share'


def test_v33_reference_projection_reproduced():
    import validation
    fx = json.load(open(FIXTURE))['meta']['reference_projection']
    B = validation.run_boss(**V33)
    assert B['lag_months'] == 0 and not B['pipe'] and B['absorption_start'] == 2026
    carbon = B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6
    gfa = B['results']['50th']['total'][1:].sum() / 1e6
    assert np.isclose(carbon, fx['carbon_kt'], rtol=RTOL, atol=0), carbon
    assert np.isclose(gfa, fx['floor_area_Mm2'], rtol=RTOL, atol=0), gfa


def test_v33_pathway_runs_reproduced(v33_flags):
    import pathways as PW
    import validation
    rows = pd.DataFrame(json.load(open(FIXTURE))['rows'])
    bounds = PW.boundaries()
    params, bad = None, []
    for scen, g in rows.groupby('scenario', sort=False):
        B = validation.run_boss(**dict(PW.SCENARIOS[scen][1], **V33))
        if params is None:
            assert scen == 'REF'
            params = PW.resolve_params(B)
        ctx = PW.base_context(B, scen, bounds)
        for _, r in g.iterrows():
            levels, ramp, rule = _levels(r['run'])
            m = PW.metrics(ctx, PW.run(ctx, params, levels, ramp, rule), r['run'], 'test')
            for col, key in (('floor_area_Mm2', 'gfa_Mm2'), ('carbon_kt', 'carbon_kt'), ('dwellings_built', 'dwellings_built'),
                             ('committed_lower_kt', 'committed_lower_kt'), ('committed_upper_kt', 'committed_upper_kt')):
                if not np.isclose(m[key], r[col], rtol=RTOL, atol=0):
                    bad.append((scen, r['run'], col, m[key], r[col]))
    assert not bad, bad[:10]
    assert len(rows) == 55


def test_lag_zero_is_the_calendar_year_sums():
    import projection
    df = projection.load_consents()
    cols = list(projection.COL_TYPOLOGIES.values()) + [projection.COL_DWELLINGS_TOTAL]
    lagged, info = projection.lagged_consents(df, 0, cols, projection.COL_DWELLINGS_TOTAL)
    a = lagged.groupby('Year')[cols].sum()
    b = df.groupby('Year')[cols].sum()
    pd.testing.assert_frame_equal(a.loc[1991:2025], b.loc[1991:2025], check_exact=True)


def test_pipeline_years_and_observed_building(B):
    import projection
    df = projection.load_consents()
    assert projection.pipeline_years(df, 0) == []
    assert projection.pipeline_years(df, 17) == [2026, 2027]
    assert projection.pipeline_years(df, 15) == [2026]
    assert projection.pipeline_years(df, 19) == [2026, 2027]
    assert B['lag_months'] == projection.COMPLETION_LAG_MONTHS == 17
    assert B['pipe']['years'] == [2026, 2027] and B['absorption_start'] == 2027
    E = B['engine_out']['50th']
    built = np.asarray(E['dwell_in_scope'] + E['rv_units'], float)
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
    amb = {int(y): v for y, v in lv['L1']['S']['ambitious'].items()}
    years = sorted(y for y in path if y >= 2026)
    for y in years:
        cap = min(sp['S_start'] + sp['rate'] * (y - 2026), sp['level'])
        assert path[y] <= max(cap, amb[y]) + 1e-12 and path[y] >= amb[y] - 1e-12
    assert np.isclose(sp['level_reached'], 2026 + (sp['level'] - sp['S_start']) / sp['rate'], rtol=1e-12)


def test_building_nonnegative_and_positive_in_tl_years():
    runs = pd.read_csv(_data('pathways/runs.csv'))
    assert (runs['dwellings_built_min_year'] >= -1e-6).all(), runs.loc[runs['dwellings_built_min_year'] < -1e-6, 'run']
    tl = runs[runs['run'].str.startswith('TL') | runs['run'].str.endswith('-tl')]
    assert len(tl) and (tl['dwellings_built_min_year'] > 0).all(), tl.loc[tl['dwellings_built_min_year'] <= 0, 'run']


def test_household_size_sensitivity_table():
    t = pd.read_csv(_data('sensitivity/household_size.csv'))
    assert set(t['run']) == {'Reference', 'pathway-moderate', 'pathway-ambitious', 'TL'}
    assert len(t) == 12
    runs = pd.read_csv(_data('pathways/runs.csv'))
    ref = runs[runs['scenario'] == 'REF'].set_index('run')
    for _, r in t.iterrows():
        key = 'REF' if r['run'] == 'Reference' else r['run']
        assert np.isclose(r['central_carbon_kt'], ref.loc[key, 'carbon_kt'], rtol=1e-12)
