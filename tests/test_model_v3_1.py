"""MODEL v3.1.0 tests (docs/CHANGELOG_v3.md, v3.1 section):

  * A2 equivalence: with ACCOUNTING 'instant' every Reference, lever, pathway and TL run total (floor area, carbon,
    LoE AR, LoE AtP) of MODEL v3.0.0 is reproduced to 1e-9 (fixture tests/fixtures/v3_0_totals.json, captured from the
    v3.0.0 outputs by tests/capture_v3_0_totals.py);
  * the legacy band (pre-2026 activity) is identical in every run;
  * the bands add up to the totals in every year: projection (baseline/bands_annual.csv), every pathway run
    (pathways/bands_annual.csv) and the history (baseline/bands_history.csv), to 1e-9; no gross vacancy band < 0;
  * Fig6: the analytic LoE AR at each marker equals the run's LoE AR (1e-9);
  * the inventory rule: AR base and projection on the same rule, soil kernel conserves the conversion."""
import contextlib
import io
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import inventory as INV  # noqa: E402
import layout  # noqa: E402

RTOL = 1e-9
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'v3_0_totals.json')


def _data(rel):
    return layout.data(rel, frozen=False)


def _levels(s):
    return {} if s == 'none' else dict(kv.split(':') for kv in s.split('+'))


@pytest.fixture(scope='module')
def instant_runs():
    """Every v3.0 run recomputed in process with ACCOUNTING 'instant' (same model otherwise)."""
    import accounting_rules as AR
    import boundaries as BD
    import levers as LV
    import pathways as PW
    import validation
    states = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for s in PW.SCENARIOS:
            states[s] = validation.run_boss(ACCOUNTING='instant', **PW.SCENARIOS[s][1])
        i_base, _ = BD.window_base(states['REF'], BD.AR_BASE_WINDOW, rule='instant')
        bounds = AR.budgets(states['REF'], i_base)
        params = PW.resolve_params(states['REF'])
    ctxs = {s: PW.base_context(states[s], s, bounds) for s in states}
    fx = json.load(open(FIXTURE))
    out = []
    for r in fx['runs']:
        ramp = None if r['adoption'] == LV.ADOPTION_ADOPTED else r['adoption']
        R = PW.run(ctxs[r['scenario']], params, _levels(r['levers']), ramp)
        q = PW.quick(ctxs[r['scenario']], R)
        out.append((r, q, float(np.sum(bounds[0])) / 1e6))
    return out


def test_a2_equivalence_with_v3_0(instant_runs):
    bad = []
    for r, q, b_ar in instant_runs:
        for k, v in (('carbon_kt', q['carbon_kt']), ('LoE_AR', q['LoE_AR']), ('LoE_AtP', q['LoE_AtP']),
                     ('floor_area_Mm2', q['gfa_Mm2'])):
            if not np.isclose(v, r[k], rtol=RTOL, atol=0):
                bad.append((r['scenario'], r['run'], k, v, r[k]))
        if not np.isclose(b_ar, r['B_AR_kt'], rtol=RTOL, atol=0):
            bad.append((r['run'], 'B_AR_kt', b_ar, r['B_AR_kt']))
    assert len(instant_runs) == 52
    assert not bad, bad[:10]


def test_legacy_identical_across_runs():
    a = pd.read_csv(_data('pathways/runs.csv'))
    for c in ('legacy_soil_kt', 'legacy_b2b4_kt'):
        v = a[c].to_numpy(float)
        assert np.all(v > 0), c
        assert np.max(np.abs(v - v[0])) <= RTOL * abs(v[0]), (c, v.min(), v.max())
    ref = pd.read_csv(_data('baseline/annual.csv')).query("source == 'projection'")
    yr = ref[(ref.year >= 2026) & (ref.year <= 2050)]
    assert np.isclose(yr.legacy_soil_kt.sum(), a.legacy_soil_kt.iloc[0], rtol=RTOL)
    assert np.isclose(yr.legacy_b2b4_kt.sum(), a.legacy_b2b4_kt.iloc[0], rtol=RTOL)


def _close(a, b, atol):
    return np.allclose(a, b, rtol=RTOL, atol=atol)


def test_projection_bands_sum_to_totals():
    b = pd.read_csv(_data('baseline/bands_annual.csv')).groupby('year')[['floor_area_Mm2', 'carbon_kt']].sum()
    a = pd.read_csv(_data('baseline/annual.csv')).query("source == 'projection'").set_index('year')
    a = a.loc[b.index]
    assert _close(b.floor_area_Mm2, a.floor_area_Mm2, 1e-9)
    assert _close(b.carbon_kt, a.carbon_kt, 1e-9)


def test_pathway_bands_sum_to_totals_every_run():
    b = pd.read_csv(_data('pathways/bands_annual.csv'))
    a = pd.read_csv(_data('pathways/annual.csv'))
    s = b.groupby(['scenario', 'run', 'year'])[['floor_area_Mm2', 'carbon_kt']].sum()
    a = a.set_index(['scenario', 'run', 'year']).loc[s.index]
    assert _close(s.floor_area_Mm2, a.floor_area_Mm2, 1e-9)
    assert _close(s.carbon_kt, a.carbon_kt, 1e-9)
    vac = b[b.band == 'Vacancy']
    assert (vac.floor_area_Mm2 >= -1e-12).all()
    rel = b[b.band.isin(['Overbuild absorbed', 'Vacancy released', 'Released dwellings (TL)'])]
    assert (rel.floor_area_Mm2 <= 1e-12).all()
    assert (b[b.band == 'Surplus kept vacant (2050)'].query('year < 2050').floor_area_Mm2.abs() <= 1e-12).all()


def test_history_bands_sum_to_observed():
    h = pd.read_csv(_data('baseline/bands_history.csv'))
    s = h.groupby('interval').agg(tot=('floor_area_Mm2_per_year', 'sum'), obs=('observed_built_Mm2_per_year', 'first'))
    assert _close(s.tot, s.obs, 1e-12)
    assert (h[h.band == 'Retirement villages (out of scope)'].floor_area_Mm2_per_year <= 0).all()
    u = json.load(open(_data('baseline/history_unexplained.json')))
    assert abs(u['difference_Mm2']) < 1e-9


def test_fig6_markers_on_the_analytic_plane():
    from figures import paper_main as PM
    bc = json.load(open(_data('pathways/backcast.json')))
    runs = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')
    assert bc['solution_space_markers']
    for m in bc['solution_space_markers']:
        z = PM.fig6_loe(bc, m['demand_reduction'], m['intensity_reduction'])
        assert np.isclose(z, runs.loc[m['run'], 'LoE_AR'], rtol=RTOL, atol=0), m['run']


def test_soil_kernel_conserves_and_spreads_over_20_years():
    K = INV.soil_kernel(25)
    assert np.allclose(K[1:6].sum(axis=1), 1.0, rtol=0, atol=1e-15) and K[0].sum() == 0
    conv = np.zeros(25)
    conv[3], conv[20] = 20.0, 10.0
    emit, after = INV.spread(conv)
    assert np.isclose(emit.sum() + after, 30.0, rtol=1e-15)
    assert np.isclose(after, 10.0 * 15 / INV.SOIL_OXIDATION_YEARS, rtol=1e-15)
    assert np.allclose(emit[3:20], 1.0) and emit[:3].sum() == 0


def test_accounting_rules_table():
    t = pd.read_csv(_data('sensitivity/accounting_rules.csv')).set_index('accounting')
    assert list(t.index) == list(INV.RULES) and bool(t.loc['inventory', 'adopted'])
    assert np.allclose(t.AtP_budget_kt_2026_2050, t.AtP_budget_kt_2026_2050.iloc[0])
    assert t.loc['instant', 'reference_legacy_kt'] == 0 and t.loc['instant', 'soil_after_2050_kt'] == 0
    inv = t.loc['inventory']
    parts = inv[['reference_upfront_kt', 'reference_soil_kt', 'reference_b2b4_kt', 'reference_legacy_kt']].sum()
    assert np.isclose(parts, inv.reference_carbon_kt, rtol=RTOL)
    assert np.isclose(inv.reference_legacy_soil_kt + inv.reference_legacy_b2b4_kt, inv.reference_legacy_kt, rtol=RTOL)
    assert inv.soil_tail_coverage_base == 'full'
