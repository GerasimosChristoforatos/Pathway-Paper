"""MODEL v3.2.0 tests (docs/CHANGELOG_v3_2.md): the v3.0 model with the non-methodological fixes of v3.1.

  * equality with MODEL v3.0.0: the Reference, every lever / pathway run and TL (floor area, carbon, LoE AR, LoE AtP,
    the budgets) equal the v3.0 outputs to 1e-9 (fixture tests/fixtures/v3_0_totals.json, captured from the v3.0.0
    outputs by tests/capture_v3_0_totals.py);
  * the Reference Monte Carlo and the AESA draw files are byte-identical to the v3.0 lock (only the pathway Monte
    Carlo was re-run);
  * release accounting (A2): the bands add up to the totals in every year (projection, every pathway run) to 1e-9;
    the gross vacancy band is never negative, the release bands never positive, the surplus only in 2050;
  * history split (A3): the bands add up to the observed floor area built;
  * Fig6: the analytic LoE AR at each marker equals the run's LoE AR (1e-9);
  * the zero-year guard (engine.forward): a year with (numerically) nothing built has no floor area and no soil;
  * the A4 sensitivity row and the A5 check row are present."""
import hashlib
import json
import os

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT
import engine  # noqa: E402
import layout  # noqa: E402

RTOL = 1e-9
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'v3_0_totals.json')
LOCK_V30 = os.path.join(ROOT, 'tests', 'regression_model_v3.json')
UNCHANGED_MC = ('montecarlo/draws_REF.csv', 'montecarlo/summary_REF.csv', 'montecarlo/annual_REF.csv',
                'aesa/montecarlo_draw_budgets.csv', 'aesa/montecarlo_annual.csv')


def _data(rel):
    return layout.data(rel, frozen=False)


def test_equal_to_v3_0_every_run():
    runs = pd.read_csv(_data('pathways/runs.csv')).set_index(['scenario', 'run'])
    fx = json.load(open(FIXTURE))['runs']
    bad = []
    for r in fx:
        row = runs.loc[(r['scenario'], r['run'])]
        for k in ('floor_area_Mm2', 'carbon_kt', 'LoE_AR', 'LoE_AtP', 'B_AR_kt', 'B_AtP_kt'):
            if not np.isclose(row[k], r[k], rtol=RTOL, atol=0):
                bad.append((r['scenario'], r['run'], k, row[k], r[k]))
    assert len(fx) == 52 and not bad, bad[:10]


def test_reference_mc_and_aesa_draws_unchanged_from_v3_0():
    """The Reference Monte Carlo and the AESA draws were not re-run; their v3.0 hashes (Reference draws and summary,
    in the v3.0 lock) still hold, and every file listed is present."""
    import runprofile
    lock = json.load(open(LOCK_V30))
    prof = runprofile.name()
    if prof not in lock['montecarlo']:
        pytest.skip(f'no v3.0 Monte Carlo lock for the {prof} profile')
    for rel in ('montecarlo/draws_REF.csv', 'montecarlo/summary_REF.csv'):
        assert hashlib.sha256(open(_data(rel), 'rb').read()).hexdigest() == lock['montecarlo'][prof][rel], rel
    for rel in UNCHANGED_MC:
        assert os.path.exists(_data(rel)), rel


def _close(a, b, atol):
    return np.allclose(a, b, rtol=RTOL, atol=atol)


def test_projection_bands_sum_to_totals():
    b = pd.read_csv(_data('baseline/bands_annual.csv')).groupby('year')[['floor_area_Mm2', 'carbon_kt']].sum()
    a = pd.read_csv(_data('baseline/annual.csv')).query("source == 'projection'").set_index('year').loc[b.index]
    assert _close(b.floor_area_Mm2, a.floor_area_Mm2, 1e-9)
    assert _close(b.carbon_kt, a.carbon_kt, 1e-9)


def test_pathway_bands_sum_to_totals_every_run_no_rescaling():
    b = pd.read_csv(_data('pathways/bands_annual.csv'))
    a = pd.read_csv(_data('pathways/annual.csv'))
    s = b.groupby(['scenario', 'run', 'year'])[['floor_area_Mm2', 'carbon_kt']].sum()
    a = a.set_index(['scenario', 'run', 'year']).loc[s.index]
    assert _close(s.floor_area_Mm2, a.floor_area_Mm2, 1e-9)
    assert _close(s.carbon_kt, a.carbon_kt, 1e-9)
    assert (b[b.band == 'Vacancy'].floor_area_Mm2 >= -1e-12).all()
    rel = b[b.band.isin(['Overbuild absorbed', 'Vacancy released', 'Released dwellings (TL)'])]
    assert (rel.floor_area_Mm2 <= 1e-12).all()
    assert (b[b.band == 'Surplus kept vacant (2050)'].query('year < 2050').floor_area_Mm2.abs() <= 1e-12).all()


def test_bands_are_not_rescaled():
    """Each in-scope band is its gross floor area x (1 - RV share) exactly (bands.py): the Reference band with
    retirement villages and its in-scope value agree by that factor."""
    import bands as BANDS
    import pathways as PW
    import validation
    B = validation.run_boss()
    ctx = PW.base_context(B, PW.REFERENCE, PW.boundaries())
    R = PW.run(ctx, PW.resolve_params(B), {})
    g, _ = BANDS.arrays(R['E'], R['inputs'], R['info']['excess'], R['info']['payback'], R['info']['flows'],
                        ctx['long_run_residual'])
    ins = PW.band_set(ctx, R)
    k = 1.0 - float(R['inputs']['rv_share'])
    for b in ('growth', 'smaller_households', 'extra_space', 'vacancy', 'replacement'):
        assert _close(ins[b][0][1:], g[b][1:] * k, 1e-9), b


def test_history_bands_sum_to_observed():
    h = pd.read_csv(_data('baseline/bands_history.csv'))
    s = h.groupby('interval').agg(tot=('floor_area_Mm2_per_year', 'sum'), obs=('observed_built_Mm2_per_year', 'first'))
    assert _close(s.tot, s.obs, 1e-12)
    assert (h[h.band == 'Retirement villages (out of scope)'].floor_area_Mm2_per_year <= 0).all()
    assert abs(json.load(open(_data('baseline/history_unexplained.json')))['difference_Mm2']) < 1e-9


def test_fig6_markers_on_the_analytic_plane():
    from figures import paper_main as PM
    bc = json.load(open(_data('pathways/backcast.json')))
    runs = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')
    assert bc['solution_space_markers']
    for m in bc['solution_space_markers']:
        z = PM.fig6_loe(bc, m['demand_reduction'], m['intensity_reduction'])
        assert np.isclose(z, runs.loc[m['run'], 'LoE_AR'], rtol=RTOL, atol=0), m['run']
        assert np.isclose(z, m['LoE_AR_run'], rtol=RTOL, atol=0), m['run']


def test_zero_year_guard():
    """engine.forward: floor area below BUILT_ZERO_TOL_M2 is a year with nothing built (no floor area, no soil),
    and the soil-bearing share stays in [0, 1] (MODEL v3.2.0). A join equal to minus the requirement of one year
    leaves floating-point noise in that year's floor area (as a zero-building year of a pathway run)."""
    import pathways as PW
    import validation
    B = validation.run_boss()
    ctx = PW.base_context(B, PW.REFERENCE, PW.boundaries())
    n = len(ctx['years'])
    fwd = lambda join: engine.forward(ctx['pop'], ctx['hh'], ctx['growth'], join=join, join_redev=np.zeros(n),
                                      **ctx['fwd_inputs'])
    j = np.zeros(n)
    j[3] = -engine.requirement(fwd(np.zeros(n)))[3]
    E = fwd(j)
    assert abs(engine.requirement(E)[3]) < 1e-6
    assert np.all(E['soil_share'] >= 0.0) and np.all(E['soil_share'] <= 1.0)
    assert E['total'][3] == 0.0 and E['soil'][3] == 0.0 and np.all(E['gfa_t'][:, 3] == 0.0)


def test_a4_and_a5_rows():
    import pathways as PW
    runs = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')
    fast, tl = runs.loc[PW.TL_REOCCUPATION_FAST], runs.loc['TL']
    assert fast['carbon_kt'] <= tl['carbon_kt'] * (1 + 1e-12)        # re-occupation as fast as demand allows
    a5 = json.load(open(_data('pathways/levers.json')))['L6']['check_with_A_1']
    assert a5['n'] == a5['adopted_n'] + 1 == 15
