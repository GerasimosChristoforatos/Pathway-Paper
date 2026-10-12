"""Pathways of MODEL v2.1.0 (pathways.py, levers.py; vocabulary of naming.py).

Identity and invariants: with every lever off the run is the Reference (annual carbon, upfront, maintenance
2026-2050, floor area by typology, demand bands, committed range, cumulative LoE AR / AtP) to 1e-9; each of L1-L9
at zero strength is the Reference; 2026 is unchanged in every run; the logistic adoption path is 0 in 2026, 1 from
2035 and monotone; L1 dwelling sizes never fall below the occupied area; implied vacancy >= 4.0%, no negative
dwellings built and no household decline in every pathway run.

Levers: L2 ordering (Ambitious >= Moderate >= Reference household size in every year; Moderate = the Stats NZ
variant with the largest S; Ambitious = its maximum held); L6 Harrell-Davis estimator matches scipy; L7 targets;
L8 soil factor; L9 no double counting (soil-free share >= the Reference share, = s where the target binds).

Attribution: pathway Shapley (16 subsets) and lever Shapley (512 subsets per setting) efficiency exact; demand
bands add up to the totals; the back-cast gives cumulative LoE AR = 1.

Theoretical limit: proportional reoccupation (built_t > 0, dwellings reoccupied = R) and stock identity; every TL item at least as strong as its Ambitious lever
(TL2 = the historical maximum household size, TL6 = min(own best independent case, r_Ambitious)); TL1 size = the
occupied area; TL9 brownfield share; TL Shapley over TL1-TL10 (1,024 subsets) exact; TL residual in people.
"""
import copy
import json
from fractions import Fraction

import numpy as np
import pytest

import levers as LV  # noqa: E402
import naming as N  # noqa: E402
import pathways as PW  # noqa: E402

TOL = 1e-9
REF = PW.REFERENCE


@pytest.fixture(scope='module')
def res():
    return PW.compute(verbose=False)


def rel(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))


def p0_row(res, scen=REF):
    """The run without levers of a projection variant (its id is the variant id)."""
    r = res['runs']
    return r[(r['run'] == scen) & (r['scenario'] == scen)].iloc[0]


def run_row(res, name, scen=REF):
    r = res['runs']
    return r[(r['run'] == name) & (r['scenario'] == scen)].iloc[0]


def test_identity_with_every_lever_off(res):
    rep = PW.checks(res)
    assert max(rep.values()) <= TOL, sorted(rep.items(), key=lambda kv: -kv[1])[:5]
    bres = json.load(open(PW.FILE_BOSS_RESULTS))
    pbr = json.load(open(PW.FILE_PB_RESULTS))
    r0 = p0_row(res)
    for k in ('carbon_kt', 'upfront_kt', 'b_inwindow_kt', 'gfa_Mm2', 'soil_kt'):
        assert r0[k] == pytest.approx(bres[N.identifier(k)], rel=TOL), k
    assert r0['committed_lower_kt'] == pytest.approx(bres['committed']['lower_kt'], rel=TOL)
    assert r0['committed_upper_kt'] == pytest.approx(bres['committed']['upper_kt'], rel=TOL)
    assert r0['LoE_AR'] == pytest.approx(pbr['deterministic'][REF]['LoE_AR'], rel=TOL)
    assert r0['LoE_AtP'] == pytest.approx(pbr['deterministic'][REF]['LoE_AtP'], rel=TOL)
    B = res['ctxs'][REF]['B']
    E0 = res['get'](REF, {})['E']
    assert rel(E0['gfa_t'][:, 1:], B['evol_typ_total'].values.T[:, 1:]) <= TOL
    assert rel(E0['carbon'][1:], B['carbon_total_typ'].sum(axis=1).values[1:]) <= TOL
    bd = res['bands']
    b0 = bd[(bd['run'] == REF) & (bd['scenario'] == REF) & (bd['definition'] == 'with_retirement_villages')]
    assert list(b0['band']) == [x['band'] for x in bres['demand_bands']]
    for x in bres['demand_bands']:
        row = b0[b0['band'] == x['band']].iloc[0]
        assert row['gfa_Mm2'] == pytest.approx(x['floor_area_Mm2'], rel=TOL, abs=1e-12)
        assert row['carbon_kt'] == pytest.approx(x['carbon_kt'], rel=TOL, abs=1e-9)


def test_replacement_variants_reproduce_aesa(res):
    pbr = json.load(open(PW.FILE_PB_RESULTS))
    for scen in ('LOW', 'HIGH'):
        r = p0_row(res, scen)
        assert r['carbon_kt'] == pytest.approx(pbr['deterministic'][scen]['I_kt'], rel=TOL)
        assert r['LoE_AR'] == pytest.approx(pbr['deterministic'][scen]['LoE_AR'], rel=TOL)
        assert r['committed_upper_kt'] == pytest.approx(pbr['committed'][scen]['upper_kt'], rel=TOL)


def zero_strength(params, ctx):
    """Every lever at zero strength: L1 f = 0; L2 target = the Reference household size; L3 v* = v0;
    L4 absorption 0; L5 d = 0; L6 r = 1; L8 x = 0; L9 s = 0 (L7: the target is the reference path, below)."""
    p = copy.deepcopy(params)
    S_ref = np.asarray(ctx['pop'], float) / np.asarray(ctx['hh'], float)
    for s in LV.SETTINGS:
        p['L1']['f'][s] = 0.0
        p['L2']['S_target'][s] = S_ref.copy()
        p['L3']['v_star'][s] = p['L3']['v0']
        p['L4']['absorption'][s] = 0.0
        p['L5']['d'][s] = 0.0
        p['L6']['r'][s] = {t: 1.0 for t in p['L6']['r'][s]}
        p['L8']['x'][s] = 0.0
        p['L9']['s'][s] = 0.0
    return p


@pytest.mark.parametrize('lever', LV.LEVERS)
def test_each_lever_at_zero_strength_is_the_reference(res, lever, monkeypatch):
    ctx = res['ctxs'][REF]
    # L7 at zero strength: its target is the reference A4-A5 path e^(-0.01 (y - 2025))
    monkeypatch.setattr(LV, 'a45_target', lambda years, setting: LV.a45_reference(years))
    R = PW.run(ctx, zero_strength(res['params'], ctx), {lever: 'ambitious'})
    R0 = res['get'](REF, {})
    E, E0 = R['E'], R0['E']
    for k in ('carbon', 'upfront', 'total', 'stock', 'stock_join', 'soil'):
        assert rel(E[k][1:], E0[k][1:]) <= TOL, k
    assert rel(E['gfa_t'][:, 1:], E0['gfa_t'][:, 1:]) <= TOL
    m, m0 = PW.metrics(ctx, R, 'x', 'ambitious'), PW.metrics(ctx, R0, REF, '')
    for k in ('committed_lower_kt', 'committed_upper_kt', 'LoE_AR', 'LoE_AtP', 'soil_kt', 'a13_kt', 'a45_kt'):
        assert m[k] == pytest.approx(m0[k], rel=TOL), k


def test_logistic_ramp():
    y = np.arange(2025, 2051)
    w = LV.ramp(y)
    assert w[0] == 0 and w[1] == 0 and w[10] == 1 and (w[10:] == 1).all()
    assert (np.diff(w) >= 0).all() and (np.diff(w[1:11]) > 0).all()
    s = lambda t: 1 / (1 + np.exp(-np.log(81) / 6 * (t - 2030.5)))
    assert w[2] == pytest.approx((s(2027) - s(2026)) / (s(2035) - s(2026)), rel=1e-12)
    assert np.array_equal(LV.ramp_named(y, 'by2035'), w) and np.array_equal(LV.ramp_named(y, None), w)
    w45, w30 = LV.ramp_named(y, 'by2045'), LV.ramp_named(y, 'by2030')
    assert w45[1] == 0 and w45[20] == 1 and (np.diff(w45) >= 0).all()
    assert w30[1] == 0 and w30[5] == 1 and (w30[5:] == 1).all() and (np.diff(w30) >= 0).all()
    f27 = LV.ramp_named(y, LV.TL_FROM2027)
    assert f27[0] == 0 and f27[1] == 0 and (f27[2:] == 1).all()


@pytest.mark.parametrize('E', [2030, 2035, 2040, 2045])
def test_adoption_window_rule(E):
    W = E - 2026
    r = LV.adoption_window(E)
    assert r['mid'] == 2026 + W / 2 and r['k'] == np.log(81) / (2 * W / 3)
    y = np.arange(2025, 2051)
    w = LV.ramp(y, mid=r['mid'], end=r['end'], k=r['k'])
    assert w[y == 2026][0] == 0 and w[y == E][0] == 1 and (w[y >= E] == 1).all() and (np.diff(w) >= 0).all()
    if E == 2035:
        assert np.array_equal(w, LV.ramp(y)) and LV.RAMP_K == r['k'] and LV.RAMP_MID == r['mid']


def test_2026_unchanged_in_every_run(res):
    for (scen, label, rn, ah), R in res['cache'].items():
        Eb = res['get'](scen, {})['E']
        E = R['E']
        for k in ('carbon', 'upfront', 'total', 'dwell_in_scope', 'join'):
            assert E[k][1] == pytest.approx(Eb[k][1], rel=1e-12), (scen, label, k)
        assert np.allclose(E['gfa_t'][:, 1], Eb['gfa_t'][:, 1], rtol=1e-12, atol=0), (scen, label)


def test_lever_inputs_not_modified(res):
    """levers.apply never modifies the reference inputs (pure functions)."""
    ctx = res['ctxs'][REF]
    fi = ctx['fwd_inputs']
    before = (fi['shares'].values.copy(), {t: np.array(fi['intensity'][t], copy=True) for t in ctx['typ']},
              dict(fi['size']), np.array(fi['rate_unc'], copy=True), fi['v'], dict(fi['soil']),
              np.array(ctx['hh'], copy=True))
    LV.apply(ctx, res['params'], {L: 'ambitious' for L in LV.LEVERS}, E_nojoin=ctx['E_nojoin'])
    assert np.array_equal(before[0], fi['shares'].values)
    assert all(np.array_equal(before[1][t], fi['intensity'][t]) for t in ctx['typ'])
    assert before[2] == fi['size'] and np.array_equal(before[3], fi['rate_unc']) and before[4] == fi['v']
    assert before[5] == fi['soil'] and np.array_equal(before[6], ctx['hh'])
    assert 'brownfield_share' not in fi


def test_l1_sizes_never_below_occupied_area(res):
    for (scen, label, rn, ah), R in res['cache'].items():
        E, size = R['E'], R['inputs']['size']
        S = E['pop'] / E['hh']
        for t in res['ctxs'][scen]['typ']:
            occ = S * float(res['ctxs'][scen]['olf'][t])
            assert (np.broadcast_to(np.asarray(size[t], float), S.shape)[1:] >= occ[1:] * (1 - 1e-12)).all(), (scen, label, t)


def test_constraints_in_every_run(res):
    """D >= S x OLF, implied vacancy >= 4.0%, no negative dwellings, no household decline in a pathway run."""
    for (scen, label, rn, ah), R in res['cache'].items():
        E = R['E']
        assert ((E['D'] - E['occ'])[1:] >= -1e-9).all() and (E['extra_clip'][1:] == 0).all(), (scen, label)
        v = PW.implied_vacancy(E)
        assert (v[1:] >= LV.L3_VACANCY_FLOOR - 1e-12).all(), (scen, label, v[1:].min())
        assert (E['dwell_in_scope'][1:] >= 0).all() and (np.asarray(PW.engine.requirement(E))[1:] >= 0).all()
        assert (np.diff(np.asarray(E['hh'], float)) >= 0).all(), (scen, label)


def test_l2_ordering_and_targets(res):
    p = res['params']['L2']
    ctx = res['ctxs'][REF]
    years = ctx['years']
    S_ref = np.asarray(ctx['pop'], float) / np.asarray(ctx['hh'], float)
    S_mod = np.array([p['S']['moderate'][y] for y in years])
    S_amb = np.array([p['S']['ambitious'][y] for y in years])
    assert (S_amb >= S_mod).all() and (S_mod >= S_ref - 1e-15).all()
    assert p['variant_moderate'] == 'High' and LV.L2_MODERATE_VARIANT == 'High'
    hi = np.array([p['variant_S']['High'][y] for y in years])
    assert all((hi[2:] >= np.array([p['variant_S'][v][y] for y in years])[2:]).all() for v in p['variant_S'])
    assert p['ambitious_level'] == pytest.approx(float(hi[2:].max()), rel=0) and p['ambitious_level_year'] == 2043
    assert round(p['ambitious_level'], 4) == 2.6933 and p['moderate_ge_reference_every_year']
    # the floor of l2_households never binds deterministically: the L2 run's S equals the formula
    w = LV.ramp(years)
    for s in LV.SETTINGS:
        hh, S = LV.l2_households(ctx['pop'], ctx['hh'], p['S_target'][s], w)
        assert np.allclose(S, S_ref + w * (np.asarray(p['S_target'][s]) - S_ref), rtol=1e-14, atol=0)


def test_l2_floor_never_adds_households():
    pop, hh = np.array([100.0, 100.0, 100.0]), np.array([40.0, 40.0, 40.0])
    hh2, S = LV.l2_households(pop, hh, np.array([2.0, 2.0, 2.0]), np.array([0.0, 0.5, 1.0]))
    assert np.array_equal(hh2, hh) and np.array_equal(S, pop / hh)


def test_harrell_davis_matches_scipy(res):
    from scipy.stats.mstats import hdquantiles
    x = np.array([c['ratio'] for c in res['params']['L6']['cases']])
    assert len(x) == res['params']['L6']['n'] >= LV.L6_MIN_CASES
    for q in (0.05, 0.15, 0.25, 0.5, 0.75, 0.95):
        assert LV.hd_quantile(x, q) == pytest.approx(float(np.asarray(hdquantiles(x, prob=[q]))[0]), abs=1e-10)
    for s in LV.SETTINGS:
        e = res['params']['L6']['estimator'][s]
        assert e['r'] < 1 and e['ci_lo'] <= e['r'] <= e['ci_hi']
    assert round(res['params']['L6']['estimator']['moderate']['r'], 3) == 0.916
    assert round(res['params']['L6']['estimator']['ambitious']['r'], 3) == 0.827


def test_l7_targets(res):
    y = np.arange(2025, 2051)
    m, a = LV.a45_target(y, 'moderate'), LV.a45_target(y, 'ambitious')
    assert m[0] == 1 and m[-1] == pytest.approx(0.5, rel=1e-14) and a[-1] == 0.0 and a[0] == 1
    assert (a <= m + 1e-15).all() and (m <= LV.a45_reference(y) + 1e-15).all()
    assert res['params']['L7']['reference_check_max_abs'] <= 1e-9


def test_l8_soil_factor(res):
    p = res['params']['L8']
    assert p['x'] == {'moderate': 0.073, 'ambitious': 0.146}
    ctx = res['ctxs'][REF]
    R = res['get'](REF, {'L8': 'ambitious'})
    w = LV.ramp(ctx['years'])
    for t in ctx['typ']:
        assert np.allclose(R['info']['soil_path'][t], float(ctx['soil'][t]) * (1 - w * 0.146), rtol=1e-15)


def test_l9_no_double_counting(res):
    """The soil-free floor area is max(replacement, s x total) at full strength: never below the Reference
    (replacement) share, and = s where the target binds."""
    ctx = res['ctxs'][REF]
    w = LV.ramp(ctx['years'])
    for s in LV.SETTINGS:
        R = res['get'](REF, {'L9': s})
        E = R['E']
        tot, sf, sr = E['total'], E['soil_free_gfa'], E['soil_free_replacement_gfa']
        share = sf[1:] / tot[1:]
        assert (share >= sr[1:] / tot[1:] - 1e-12).all()
        sv = res['params']['L9']['s'][s]
        exp = sr + w * np.maximum(0.0, sv * tot - sr)
        assert np.allclose(sf[1:], exp[1:], rtol=1e-12, atol=1e-6)
        full = (w == 1) & (sv * tot > sr)
        assert full.any() and np.allclose(sf[full] / tot[full], sv, rtol=1e-12)
    assert res['params']['L9']['s'] == {'moderate': 0.41, 'ambitious': 0.59}


def test_shapley_efficiency_exact(res):
    r = res['runs']
    for (level, s, metric), (phi, total) in res['shapley_exact'].items():
        assert sum(phi.values()) == total, (level, s, metric)
        p0 = r[(r['run'] == REF) & (r['scenario'] == REF)].iloc[0][metric]
        p5 = r[(r['run'] == f'P5-{s}') & (r['scenario'] == REF)].iloc[0][metric]
        assert total == Fraction(p0) - Fraction(p5)
    assert {k[0] for k in res['shapley_exact']} == {'pathways', 'levers'}
    sr = res['shapley_runs']
    assert len(sr[sr['level'] == 'pathways']) == 2 * 16 and len(sr[sr['level'] == 'levers']) == 2 * 512


def test_shapley_on_a_known_game():
    """Additive game with one pairwise interaction: the interaction is split equally."""
    a = dict(zip(LV.LEVERS, range(1, 10)))
    v = {S: 100.0 - sum(a[i] for i in S) - (6.0 if {'L1', 'L2'} <= S else 0.0) for S in PW.subsets(LV.LEVERS)}
    phi = PW.shapley(v, LV.LEVERS)
    assert float(phi['L1']) == pytest.approx(4.0) and float(phi['L2']) == pytest.approx(5.0)
    assert float(phi['L9']) == pytest.approx(9.0)


def test_pathway_composition():
    assert N.PATHWAY_LEVERS == {'P1': ('L1', 'L2'), 'P2': ('L3', 'L4', 'L5'), 'P3': ('L6', 'L7'), 'P4': ('L8', 'L9')}
    assert LV.pathway_levers('P5', 'moderate') == {L: 'moderate' for L in LV.LEVERS}
    assert N.UNTARGETED == ('growth',)


def test_band_sums_equal_totals(res):
    bd, r = res['bands'], res['runs']
    for (run, scen), g in bd.groupby(['run', 'scenario']):
        row = r[(r['run'] == run) & (r['scenario'] == scen)].iloc[0]
        for d in N.BAND_DEFINITION_IDS:
            assert g[g['definition'] == d]['gfa_Mm2'].sum() == pytest.approx(row['gfa_Mm2'], rel=1e-12), (run, scen, d)
        assert g[g['definition'] == 'in_scope']['carbon_kt'].sum() == pytest.approx(row['carbon_kt'], rel=1e-12)


def test_backcast(res):
    bc = res['backcast']
    for k in (REF, 'P5-moderate', 'P5-ambitious'):
        assert bc[k]['LoE_AR_at_k'] == pytest.approx(1.0, abs=1e-9), k
        assert 0 < bc[k]['k_AR'] < 1


# ============================================================
# THEORETICAL LIMIT TL
# ============================================================
@pytest.fixture(scope='module')
def rt(res):
    return PW.compute_tl(res, verbose=False)


def full(rt):
    return rt['cache'][LV.TL_COMPONENTS]


def test_reoccupation_rule_on_a_known_path():
    years = np.arange(2025, 2051)
    gross = np.linspace(100.0, 330.0, len(years))
    released = np.zeros(len(years))
    released[2], released[5] = 900.0, 300.0
    released[1] = 5000.0  # 2026 is outside the reoccupation years and is ignored
    ro = PW.reoccupation(years, gross, released)
    G = gross[2:].sum()
    assert ro['R'] == 1200.0 and ro['G'] == pytest.approx(G, rel=1e-15) and ro['share'] == pytest.approx(1200.0 / G)
    assert np.allclose(ro['built'][2:], gross[2:] * (1 - 1200.0 / G), rtol=1e-14, atol=0)
    assert np.array_equal(ro['built'][:2], gross[:2]) and (ro['reoccupied'][:2] == 0).all()
    assert ro['reoccupied'].sum() == pytest.approx(1200.0, rel=1e-14)
    assert (ro['built'][2:] > 0).all()


def test_TL_reoccupation_and_stock_identity(rt):
    for key, R in rt['cache'].items():
        E, ro = R['E'], R['info']['reoccupation']
        built = np.asarray(PW.engine.requirement(E), float)
        # built_t > 0 in every year 2027-2050 and the dwellings reoccupied add up to R
        assert (ro['built'][2:] > 0).all() and (built[2:] > 0).all(), key
        assert ro['reoccupied'].sum() == pytest.approx(ro['R'], rel=1e-12), key
        assert (ro['gross'] - ro['built']).sum() == pytest.approx(ro['R'], rel=1e-12), key
        assert ro['R'] == pytest.approx((ro['released_vacancy'] + ro['released_households']
                                         + ro['released_overbuild'])[2:].sum(), rel=1e-12), key
        assert np.allclose(ro['reoccupied'][2:], ro['gross'][2:] * ro['share'], rtol=1e-12, atol=0), key
        # the stock-adding join gives the engine's requirement = dwellings built; no redevelopment join
        assert np.allclose(built[2:], ro['built'][2:], rtol=1e-12, atol=1e-6), key
        assert (E['join_redev'] == 0).all()
        assert (PW.implied_vacancy(E)[1:] >= -1e-9).all(), key


def test_TL_releases_full(rt):
    """The full TL releases the 2027 vacancy fall, the TL2 household change and the 2026 overbuild."""
    ro = full(rt)['info']['reoccupation']
    assert ro['released_households'][2] > 0 and ro['released_vacancy'][2] > 0
    assert ro['released_overbuild'][2:].sum() == pytest.approx(16760, rel=1e-3)
    assert 0 < ro['share'] < 1


def test_TL_items_at_least_as_strong_as_ambitious(rt, res):
    assert all(r_[3] for r_ in rt['strength']), [r_ for r_ in rt['strength'] if not r_[3]]
    p = rt['params_T']
    assert p['TL2']['S'] == pytest.approx(2.7905, abs=5e-5) and p['TL2']['year'] == 1991
    r_amb = res['params']['L6']['estimator']['ambitious']['r']
    assert p['TL6']['Detached']['own_best_building'] == 'SD_2' and round(p['TL6']['Detached']['r'], 3) == 0.530
    for t in ('Townhouses', 'Apartments'):
        assert p['TL6'][t]['r'] == r_amb and not p['TL6'][t]['exceeds_ambitious']
    assert p['TL6']['Detached']['exceeds_ambitious']
    assert p['TL9']['s'] == 0.89 and p['TL9']['s'] >= res['params']['L9']['s']['ambitious']
    assert round(p['TL10']['olf'], 2) == 19.69


def test_TL1_size_equals_occupied_area(rt):
    R = full(rt)
    E = R['E']
    assert np.allclose(E['D'][2:], E['occ'][2:], rtol=1e-12, atol=0)


def test_TL_2026_unchanged(res, rt):
    E0 = res['get'](REF, {})['E']
    for key, R in rt['cache'].items():
        E = R['E']
        for k in ('carbon', 'upfront', 'total', 'dwell_in_scope', 'join'):
            assert E[k][1] == pytest.approx(E0[k][1], rel=1e-12), (key, k)


def test_TL_shapley_efficiency_exact(res, rt):
    assert len(rt['subsets']) == 2 ** 10
    for metric, (phi, total) in rt['shapley_exact'].items():
        assert sum(phi.values()) == total, metric
    s = rt['subsets'].set_index('subset')
    sh = rt['shapley']
    sep = (LV.TL_FROM2027, LV.TL_REOCCUPATION)
    p5m = run_row(res, 'P5-moderate')
    for metric in ('carbon_kt', 'LoE_AR'):
        m = sh[sh['metric'] == metric].set_index('player')['reduction']
        x = m.drop(list(sep)).sum()
        assert x == pytest.approx(s.loc[LV.TL_BASE_LABEL, metric] - s.loc['TL', metric], rel=1e-12)
        # the two separate lines close the gap to P5 Moderate on its adoption path exactly
        assert m.sum() == pytest.approx(p5m[metric] - s.loc['TL', metric], rel=1e-12)


def test_TL_checks_pass(res, rt):
    PW.checks_tl(res, rt)


def test_TL_residual_in_people(rt):
    g = rt['gap']['TL']
    if g['within_AR']:
        assert g['margin_AR_kt'] >= 0
        return
    E = full(rt)['E']
    cut = 1 - g['backcast']['k_AR']
    assert g['residual']['dwellings_not_built_2027_2050'] == pytest.approx(cut * E['dwell_in_scope'][2:].sum(), rel=1e-12)


def test_waterfall_reaches_P5_and_TL(res, rt):
    w = PW.waterfall_sequential(res, rt)
    st = w.drop_duplicates('step').set_index('step_id')
    assert st.loc['P4', 'total_carbon_kt'] == pytest.approx(run_row(res, 'P5-moderate')['carbon_kt'], rel=1e-12)
    assert st.loc['TL10', 'total_carbon_kt'] == pytest.approx(rt['rows'][0]['carbon_kt'], rel=1e-12)
    m27 = res['get'](REF, LV.pathway_levers('P5', 'moderate'), LV.TL_FROM2027)['E']['carbon'][1:].sum() / PW.M6
    assert st.loc['from2027', 'total_carbon_kt'] == pytest.approx(m27, rel=1e-9)
    base = rt['cache'][()]['E']['carbon'][1:].sum() / PW.M6
    assert st.loc[LV.TL_REOCCUPATION, 'total_carbon_kt'] == pytest.approx(base, rel=1e-9)
    ids = list(st.index)
    assert ids.index('P4') < ids.index('from2027') < ids.index(LV.TL_REOCCUPATION) < ids.index('TL1')
    for step, g in w.groupby('step'):
        assert g['carbon_kt'].sum() == pytest.approx(g['total_carbon_kt'].iloc[0], rel=1e-9)
