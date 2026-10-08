"""PATHWAYS v2 (pathways.py, levers.py). Identity: with every lever off the run is the
reference central run (annual carbon, upfront, in-window B, floor area by typology,
demand bands, committed range, cumulative LoE AR / AtP) to 1e-9; each lever at zero
strength is the baseline; 2026 is unchanged in every run; the logistic ramp is 0 in
2026, 1 from 2035 and monotone; L1 dwelling sizes never fall below the occupied area;
implied vacancy >= 4.0% and no negative dwellings built in every run; the Harrell-Davis
estimator matches scipy; pathway and lever Shapley efficiency hold exactly; demand
bands add up to the totals; the back-cast gives cumulative LoE AR = 1. The byte lock
on the baseline outputs is tests/test_baseline_lock.py."""
import copy
import json
from fractions import Fraction

import numpy as np
import pytest

import levers as LV  # noqa: E402
import pathways as PW  # noqa: E402

TOL = 1e-9


@pytest.fixture(scope='module')
def res():
    return PW.compute(verbose=False)


def rel(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))


def p0_row(res, scen=PW.REFERENCE):
    r = res['runs']
    return r[(r['run'] == 'P0') & (r['scenario'] == scen)].iloc[0]


def test_identity_with_every_lever_off(res):
    rep = PW.checks(res)
    assert max(rep.values()) <= TOL, sorted(rep.items(), key=lambda kv: -kv[1])[:5]
    bres = json.load(open(PW.FILE_BOSS_RESULTS))
    pbr = json.load(open(PW.FILE_PB_RESULTS))
    r0 = p0_row(res)
    for k in ('carbon_kt', 'upfront_kt', 'b_inwindow_kt', 'gfa_Mm2', 'soil_kt'):
        assert r0[k] == pytest.approx(bres[k], rel=TOL), k
    assert r0['committed_lower_kt'] == pytest.approx(bres['committed']['lower_kt'], rel=TOL)
    assert r0['committed_upper_kt'] == pytest.approx(bres['committed']['upper_kt'], rel=TOL)
    assert r0['LoE_AR'] == pytest.approx(pbr['deterministic']['S3-10']['LoE_AR'], rel=TOL)
    assert r0['LoE_AtP'] == pytest.approx(pbr['deterministic']['S3-10']['LoE_AtP'], rel=TOL)
    B = res['ctxs'][PW.REFERENCE]['B']
    E0 = res['get'](PW.REFERENCE, {})['E']
    assert rel(E0['gfa_t'][:, 1:], B['evol_typ_total'].values.T[:, 1:]) <= TOL
    assert rel(E0['carbon'][1:], B['carbon_total_typ'].sum(axis=1).values[1:]) <= TOL
    bd = res['bands']
    b0 = bd[(bd['run'] == 'P0') & (bd['scenario'] == PW.REFERENCE) & (bd['definition'] == 'boss_results')]
    assert list(b0['band']) == [x['band'] for x in bres['demand_bands']]
    for x in bres['demand_bands']:
        row = b0[b0['band'] == x['band']].iloc[0]
        assert row['gfa_Mm2'] == pytest.approx(x['gfa_Mm2'], rel=TOL, abs=1e-12)
        assert row['carbon_kt'] == pytest.approx(x['carbon_kt'], rel=TOL, abs=1e-9)


def test_envelope_scenarios_reproduce_pb(res):
    pbr = json.load(open(PW.FILE_PB_RESULTS))
    for scen in ('S1', 'S2'):
        r = p0_row(res, scen)
        assert r['carbon_kt'] == pytest.approx(pbr['deterministic'][scen]['I_kt'], rel=TOL)
        assert r['LoE_AR'] == pytest.approx(pbr['deterministic'][scen]['LoE_AR'], rel=TOL)
        assert r['committed_upper_kt'] == pytest.approx(pbr['committed'][scen]['upper_kt'], rel=TOL)


def zero_strength(params):
    """Every lever at zero strength: L1 f = 0, L4 target = baseline attached share, L2a v* = v0,
    L2b absorption 0, L3 d = 0, L5 r = 1."""
    p = copy.deepcopy(params)
    for s in LV.SETTINGS:
        p['L1']['f'][s] = 0.0
        p['L4']['target'][s] = p['L4']['baseline_attached']
        p['L2a']['v_star'][s] = p['L2a']['v0']
        p['L2b']['absorption'][s] = 0.0
        p['L3']['d'][s] = 0.0
        p['L5']['r'][s] = {t: 1.0 for t in p['L5']['r'][s]}
    return p


@pytest.mark.parametrize('lever', LV.LEVERS)
def test_each_lever_at_zero_strength_is_the_baseline(res, lever):
    ctx = res['ctxs'][PW.REFERENCE]
    R = PW.run(ctx, zero_strength(res['params']), {lever: 'stretch'})
    R0 = res['get'](PW.REFERENCE, {})
    E, E0 = R['E'], R0['E']
    for k in ('carbon', 'upfront', 'total', 'stock', 'stock_join'):
        assert rel(E[k][1:], E0[k][1:]) <= TOL, k
    assert rel(E['gfa_t'][:, 1:], E0['gfa_t'][:, 1:]) <= TOL
    m, m0 = PW.metrics(ctx, R, 'x', 'stretch'), PW.metrics(ctx, R0, 'P0', '')
    for k in ('committed_lower_kt', 'committed_upper_kt', 'LoE_AR', 'LoE_AtP', 'soil_kt', 'a13_kt'):
        assert m[k] == pytest.approx(m0[k], rel=TOL), k


def test_logistic_ramp():
    y = np.arange(2025, 2051)
    w = LV.ramp(y)
    assert w[0] == 0 and w[1] == 0 and w[10] == 1 and (w[10:] == 1).all()
    assert (np.diff(w) >= 0).all() and (np.diff(w[1:11]) > 0).all()
    s = lambda t: 1 / (1 + np.exp(-np.log(81) / 6 * (t - 2030.5)))
    assert w[2] == pytest.approx((s(2027) - s(2026)) / (s(2035) - s(2026)), rel=1e-12)
    assert s(2027.5) == pytest.approx(0.1) and s(2033.5) == pytest.approx(0.9)    # 10% -> 90% in 6 years
    w45 = LV.ramp_named(y, 'ramp2045')
    assert w45[1] == 0 and w45[20] == 1 and (np.diff(w45) >= 0).all()


def test_2026_unchanged_in_every_run(res):
    for (scen, label, rn, ah), R in res['cache'].items():
        Eb = res['get'](scen, {})['E']
        E = R['E']
        for k in ('carbon', 'upfront', 'total', 'dwell_in_scope', 'join'):
            assert E[k][1] == pytest.approx(Eb[k][1], rel=1e-12), (scen, label, k)
        assert np.allclose(E['gfa_t'][:, 1], Eb['gfa_t'][:, 1], rtol=1e-12, atol=0), (scen, label)


def test_lever_inputs_not_modified(res):
    """levers.apply never modifies the reference inputs (pure functions)."""
    ctx = res['ctxs'][PW.REFERENCE]
    fi = ctx['fwd_inputs']
    before = (fi['shares'].values.copy(), {t: np.array(fi['intensity'][t], copy=True) for t in ctx['typ']},
              dict(fi['size']), np.array(fi['rate_unc'], copy=True), fi['v'])
    LV.apply(ctx, res['params'], {L: 'stretch' for L in LV.LEVERS}, E_nojoin=ctx['E_nojoin'])
    assert np.array_equal(before[0], fi['shares'].values)
    assert all(np.array_equal(before[1][t], fi['intensity'][t]) for t in ctx['typ'])
    assert before[2] == fi['size'] and np.array_equal(before[3], fi['rate_unc']) and before[4] == fi['v']


def test_l1_sizes_never_below_occupied_area(res):
    """size_t(y) >= S(y) OLF_t for every typology, year and run (no hold needed in v2)."""
    for (scen, label, rn, ah), R in res['cache'].items():
        E, size = R['E'], R['inputs']['size']
        S = E['pop'] / E['hh']
        for t in res['ctxs'][scen]['typ']:
            occ = S * float(res['ctxs'][scen]['olf'][t])
            assert (np.broadcast_to(np.asarray(size[t], float), S.shape)[1:] >= occ[1:]).all(), (scen, label, t)
        held = R['info'].get('l1_held')
        assert not held or not any(h[1:].any() for h in held.values())
    p = res['params']['L1']
    assert not p['held']
    for s in LV.SETTINGS:
        for t in p['size_ref']:
            for y in LV.L1_REPORT_YEARS:
                d = p['implied'][s][t][y]
                assert d['occupied_m2'] < d['size_m2'] <= p['size_ref'][t]


def test_constraints_in_every_run(res):
    """D >= S x OLF (engine extra_clip stays 0), implied vacancy >= 4.0%, no negative dwellings."""
    for (scen, label, rn, ah), R in res['cache'].items():
        E = R['E']
        assert ((E['D'] - E['occ'])[1:] >= 0).all() and (E['extra_clip'][1:] == 0).all(), (scen, label)
        v = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
        assert (v[1:] >= LV.L2_VACANCY_FLOOR).all(), (scen, label, v[1:].min())
        assert (E['dwell_in_scope'][1:] >= 0).all() and (np.asarray(PW.engine.requirement(E))[1:] >= 0).all()


def test_harrell_davis_matches_scipy(res):
    from scipy.stats.mstats import hdquantiles
    x = np.array([c['ratio'] for c in res['params']['L5']['cases']])
    assert len(x) == res['params']['L5']['n'] >= LV.L5_MIN_CASES
    for q in (0.05, 0.15, 0.25, 0.5, 0.75, 0.95):
        assert LV.hd_quantile(x, q) == pytest.approx(float(np.asarray(hdquantiles(x, prob=[q]))[0]), abs=1e-10)
    rng = np.random.default_rng(7)
    for n in (5, 14, 40):
        z = rng.lognormal(size=n)
        assert LV.hd_quantile(z, 0.3) == pytest.approx(float(np.asarray(hdquantiles(z, prob=[0.3]))[0]), abs=1e-10)
        assert LV.hd_weights(n, 0.3).sum() == pytest.approx(1.0, abs=1e-14)
    for s in LV.SETTINGS:
        e = res['params']['L5']['estimator'][s]
        assert e['r'] < 1 and e['ci_lo'] <= e['r'] <= e['ci_hi']
        assert e['r'] == pytest.approx(e['scipy_hdquantiles'], abs=1e-10)


def test_l5_sample_and_application(res):
    p = res['params']['L5']
    ids = [c['id'] for c in p['cases']]
    assert len(ids) == 14 and not any(i.startswith('A_') for i in ids)        # independent detached + townhouses
    assert p['pooled_check_max_abs'] < 1e-9
    for s in LV.SETTINGS:
        assert len(set(p['r'][s].values())) == 1 and p['r_apartments_held'][s]['Apartments'] == 1.0
    r0 = p0_row(res)
    r4 = res['runs'][(res['runs']['run'] == 'P4-stretch') & (res['runs']['scenario'] == PW.REFERENCE)].iloc[0]
    for k in ('a45_kt', 'soil_kt', 'b_inwindow_kt', 'committed_upper_kt', 'gfa_Mm2'):
        assert r4[k] == pytest.approx(r0[k], rel=1e-12), k


def test_l4_shares(res):
    ctx = res['ctxs'][PW.REFERENCE]
    sh = res['get'](PW.REFERENCE, {'L4': 'stretch'})['inputs']['shares']
    assert np.allclose(sh.sum(axis=1).values, 1.0, rtol=0, atol=1e-12)
    b = ctx['held_shares']
    d_t, d_a = sh['Townhouses'].iloc[-1] - b['Townhouses'], sh['Apartments'].iloc[-1] - b['Apartments']
    assert d_t / d_a == pytest.approx(b['Townhouses'] / b['Apartments'])
    p = res['params']['L4']
    assert p['target']['central'] < p['target']['stretch']
    assert p['target']['stretch'] == pytest.approx(p['baseline_attached'] + 0.16)


def test_shapley_efficiency_exact(res):
    r = res['runs']
    for (level, s, metric), (phi, total) in res['shapley_exact'].items():
        assert sum(phi.values()) == total, (level, s, metric)              # exact (Fraction arithmetic)
        p0 = r[(r['run'] == 'P0') & (r['scenario'] == PW.REFERENCE)].iloc[0][metric]
        p5 = r[(r['run'] == f'P5-{s}') & (r['scenario'] == PW.REFERENCE)].iloc[0][metric]
        assert total == Fraction(p0) - Fraction(p5)
    assert {k[0] for k in res['shapley_exact']} == {'pathways', 'levers'}
    sr = res['shapley_runs']
    assert len(sr[sr['level'] == 'pathways']) == 2 * 16 and len(sr[sr['level'] == 'levers']) == 2 * 64


def test_shapley_on_a_known_game():
    """Additive game with one pairwise interaction: the interaction is split equally."""
    a = dict(zip(LV.LEVERS, (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)))
    v = {S: 100.0 - sum(a[i] for i in S) - (6.0 if {'L1', 'L4'} <= S else 0.0) for S in PW.subsets(LV.LEVERS)}
    phi = PW.shapley(v, LV.LEVERS)
    assert float(phi['L1']) == pytest.approx(4.0) and float(phi['L4']) == pytest.approx(5.0)
    assert float(phi['L5']) == pytest.approx(6.0)


def test_band_sums_equal_totals(res):
    bd, r = res['bands'], res['runs']
    for (run, scen), g in bd.groupby(['run', 'scenario']):
        row = r[(r['run'] == run) & (r['scenario'] == scen)].iloc[0]
        for d in ('boss_results', 'in_scope_figure'):
            assert g[g['definition'] == d]['gfa_Mm2'].sum() == pytest.approx(row['gfa_Mm2'], rel=1e-12), (run, scen, d)
        assert g[g['definition'] == 'in_scope_figure']['carbon_kt'].sum() == pytest.approx(row['carbon_kt'], rel=1e-12)
        # the band deltas add up to the run's delta vs P0
        p0 = r[(r['run'] == 'P0') & (r['scenario'] == scen)].iloc[0]
        dg = g[g['definition'] == 'boss_results']['delta_gfa_Mm2_vs_P0'].sum()
        assert dg == pytest.approx(row['gfa_Mm2'] - p0['gfa_Mm2'], abs=1e-9)


def test_backcast(res):
    bc = res['backcast']
    for k in ('P0', 'P5-central', 'P5-stretch'):
        assert bc[k]['LoE_AR_at_k'] == pytest.approx(1.0, abs=1e-9), k
        assert bc[k]['k_AR'] == pytest.approx(bc[k]['k_AR_closed_form'], rel=1e-12)
        assert 0 < bc[k]['k_AR'] < 1
        assert bc[k]['LoE_AtP_min_k0'] > 1 and not bc[k]['AtP_attainable']
    sp = res['space']
    r0 = p0_row(res)
    c00 = sp[(sp['demand_reduction'] == 0) & (sp['intensity_reduction'] == 0)].iloc[0]
    assert c00['LoE_AR'] == pytest.approx(r0['LoE_AR'], rel=1e-12)
    c11 = sp[(sp['demand_reduction'] == 1) & (sp['intensity_reduction'] == 1)].iloc[0]
    assert c11['LoE_AtP'] == pytest.approx(bc['P0']['LoE_AtP_min_k0'], rel=1e-12)
