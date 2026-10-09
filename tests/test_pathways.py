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
    """Every lever at zero strength: L1 f = 0, L2a v* = v0,
    L2b absorption 0, L3 d = 0, L5 r = 1."""
    p = copy.deepcopy(params)
    for s in LV.SETTINGS:
        p['L1']['f'][s] = 0.0
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
    w30 = LV.ramp_named(y, 'ramp2030')
    assert w30[1] == 0 and w30[5] == 1 and (w30[5:] == 1).all() and (np.diff(w30) >= 0).all()
    s30 = lambda t: 1 / (1 + np.exp(-np.log(81) / 6 * (t - 2028.5)))
    assert w30[2] == pytest.approx((s30(2027) - s30(2026)) / (s30(2030) - s30(2026)), rel=1e-12)


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


def test_no_l4_anywhere(res):
    """L4 removed (v3.1): the typology shares are the baseline (held) mix in every run, incl. T."""
    base = res['ctxs'][PW.REFERENCE]['fwd_inputs']['shares']
    assert 'L4' not in LV.LEVERS and all('L4' not in v for v in LV.PATHWAYS.values())
    for (scen, label, rn, ah), R in res['cache'].items():
        assert R['inputs']['shares'] is res['ctxs'][scen]['fwd_inputs']['shares'], (scen, label)
    rt_ = PW.compute_T(res, verbose=False)
    for key, R in rt_['cache'].items():
        assert R['inputs']['shares'].equals(base), key


def test_l4_v2_note_matches_tag():
    """The v2 L4 numbers cited in the documents are those of tag pathways_v2."""
    import io
    import pandas as pd
    txt = _git_show_tag('pathways_v2', 'outputs/pathways/pathways_runs.csv')
    if txt is None:
        pytest.skip('git or tag pathways_v2 not available')
    r = pd.read_csv(io.StringIO(txt))
    r = r[r['scenario'] == 'S3-10'].set_index('run')
    n = LV.L4_V2_NOTE
    for s in LV.SETTINGS:
        assert r.loc[f'L4-{s}', 'carbon_kt'] == n['carbon_kt'][s]
        assert r.loc[f'L4-{s}', 'delta_carbon_kt_vs_P0_pct'] == n['carbon_vs_P0_pct'][s]
        assert r.loc[f'L4-{s}', 'carbon_per_m2_kg'] == n['carbon_per_m2_kg'][s]


def test_l2a_unchanged(res):
    p = res['params']['L2a']
    assert p['v0'] == float(res['ctxs'][PW.REFERENCE]['B']['v_forward'])
    assert p['v_star'] == {'central': 0.047, 'stretch': 0.040}
    assert (p['census_consistent_min_year'], p['census_consistent_max_year']) == (1996, 2023)
    assert round(p['census_consistent_min'], 4) == 0.0401 and round(p['census_consistent_max'], 4) == 0.0538

def test_shapley_efficiency_exact(res):
    r = res['runs']
    for (level, s, metric), (phi, total) in res['shapley_exact'].items():
        assert sum(phi.values()) == total, (level, s, metric)              # exact (Fraction arithmetic)
        p0 = r[(r['run'] == 'P0') & (r['scenario'] == PW.REFERENCE)].iloc[0][metric]
        p5 = r[(r['run'] == f'P5-{s}') & (r['scenario'] == PW.REFERENCE)].iloc[0][metric]
        assert total == Fraction(p0) - Fraction(p5)
    assert {k[0] for k in res['shapley_exact']} == {'pathways', 'levers'}
    sr = res['shapley_runs']
    assert len(sr[sr['level'] == 'pathways']) == 2 * 16 and len(sr[sr['level'] == 'levers']) == 2 * 32


def test_shapley_on_a_known_game():
    """Additive game with one pairwise interaction: the interaction is split equally."""
    a = dict(zip(LV.LEVERS, (1.0, 2.0, 3.0, 4.0, 5.0)))
    v = {S: 100.0 - sum(a[i] for i in S) - (6.0 if {'L1', 'L2a'} <= S else 0.0) for S in PW.subsets(LV.LEVERS)}
    phi = PW.shapley(v, LV.LEVERS)
    assert float(phi['L1']) == pytest.approx(4.0) and float(phi['L2a']) == pytest.approx(5.0)
    assert float(phi['L5']) == pytest.approx(5.0)


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


# ============================================================
# THEORETICAL LIMIT T (PATHWAYS v3)
# ============================================================
import os  # noqa: E402
import subprocess  # noqa: E402

from conftest import ROOT  # noqa: E402


@pytest.fixture(scope='module')
def rt(res):
    return PW.compute_T(res, verbose=False)


def test_bank_rule_on_a_known_path():
    raw = np.array([5.0, 10.0, -30.0, 8.0, 12.0, 20.0, -5.0, 3.0])
    b = PW.bank(raw)
    assert list(b['built']) == [5.0, 10.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0]
    assert list(b['bank']) == [0.0, 0.0, 30.0, 22.0, 10.0, 0.0, 5.0, 2.0]
    assert b['added'][1:].sum() == 35.0 and b['used'][1:].sum() == 33.0


def test_T_banking_and_stock_identity(rt):
    """Dwellings built >= 0 every year (within floating-point noise of 1e-6 dwellings); the engine's
    dwellings built equal the banked path (stock identity: requirement + stock-adding join);
    cumulative release used <= released; implied vacancy never negative; v = 0 from 2027 under T1."""
    for key, R in rt['cache'].items():
        E, bk = R['E'], R['info']['bank']
        built = np.asarray(PW.engine.requirement(E), float)
        assert (built[1:] >= -PW.T_ZERO_TOL_DWELLINGS).all() and (bk['built'][1:] >= 0).all(), key
        assert np.allclose(built[1:], bk['built'][1:], rtol=1e-12, atol=1e-6), key
        assert (E['join_redev'] == 0).all()
        assert np.allclose(E['stock_join'], np.cumsum(E['join']), rtol=1e-12, atol=1e-6)
        assert np.all(np.cumsum(bk['used']) <= np.cumsum(bk['added']) + 1e-6), key
        assert bk['bank'][-1] == pytest.approx(bk['added'].sum() - bk['used'].sum(), abs=1e-6)
        v = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
        assert (v[1:] >= -1e-12).all(), key
        if 'T1' in key[0] and key[1] == LV.T_INSTANT:
            assert (np.broadcast_to(E['v'], E['hh'].shape)[2:] == 0).all()


def test_T2_size_equals_occupied_area(rt):
    R = rt['cache'][(LV.T_COMPONENTS, LV.T_INSTANT)]
    E = R['E']
    S = E['pop'] / E['hh']
    for t in res_typ(rt):
        occ = S * np.asarray(R['inputs']['olf'][t], float)
        size = np.asarray(R['inputs']['size'][t], float)
        assert np.allclose(size[2:], occ[2:], rtol=1e-12, atol=0), t
    assert np.allclose(E['D'][2:], E['occ'][2:], rtol=1e-12, atol=0)


def res_typ(rt):
    return list(rt['params_T']['T4'])


def test_T3_T4_T5_values(rt):
    import Building_factors as BF
    import pandas as pd
    fb = pd.read_csv(PW.validation.Boss.FILE_FACTORS_BUILDING)
    ind = fb[fb['duplicate_of'].fillna('') == '']['id']
    chars = BF.load_characteristics()
    p = rt['params_T']
    assert p['T3']['olf'] == float(chars.loc[ind, 'OLF'].min()) and p['T3']['building'] == 'A_1'
    assert 'A_2' in p['T3']['excluded_duplicates']
    for t, d in p['T4'].items():
        g = fb[(fb['Typology'] == t) & fb['id'].isin(ind)]
        pooled = fb[fb['Typology'] == t].groupby('Subtype')['A1-A3'].mean().mean()
        if t == 'Apartments':
            assert d['held'] and d['r'] == 1.0
        else:
            assert d['r'] == pytest.approx(float((g['A1-A3'] / pooled).min()), rel=1e-15)
    assert p['T4']['Detached']['building'] == 'SD_2'
    ft = pd.read_csv(PW.validation.Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology')
    for t, d in p['T5'].items():
        assert d['soc_low'] == ft.loc[t, 'SOC_low']


def test_T6_developed_share_carries_no_soil(res, rt):
    """T6: soil carbon on the developed share (s = 0.65) of the non-replacement floor area is 0; the rest equals
    the T5 path (1e-9)."""
    R = rt['cache'][(LV.T_COMPONENTS, LV.T_INSTANT)]
    E, info, p = R['E'], R['info'], rt['params_T']
    typ = res_typ(rt)
    w = LV.ramp_instant(E['years'])
    for t in typ:
        t5 = p['T5'][t]['soc_avg'] + w * (p['T5'][t]['soc_low'] - p['T5'][t]['soc_avg'])
        assert np.allclose(info['soil_path'][t], t5 * (1 - LV.T6_SHARE * w), rtol=1e-12, atol=0)
        assert info['soil_path'][t][1] == p['T5'][t]['soc_avg']               # 2026 untouched
    soil_bearing = sum(E['gfa_t'][k] * E['soil_share'] for k in range(len(typ)))
    t5_soil = sum((p['T5'][t]['soc_avg'] + w * (p['T5'][t]['soc_low'] - p['T5'][t]['soc_avg'])) * E['gfa_t'][k]
                  for k, t in enumerate(typ)) * E['soil_share']
    soil = PW.soil_by_year(res['ctxs'][PW.REFERENCE], E, info['soil_path'])
    developed = LV.T6_SHARE * w * t5_soil                 # what the developed share would carry under T5
    assert np.allclose(soil[2:], (t5_soil - developed)[2:], rtol=1e-9, atol=1e-6)
    pos = t5_soil[2:] > 0                                  # years with soil-bearing floor area (not the banked zero years)
    assert pos.sum() > 10 and np.allclose(soil[2:][pos] / t5_soil[2:][pos], 1 - LV.T6_SHARE, rtol=1e-9)
    assert (soil_bearing[2:][~pos] == 0).all()
    assert LV.T6_SHARE == round(LV.T6_COMPONENTS[0] * LV.T6_COMPONENTS[1], 2)


def test_T5_soil_exact(rt):
    """The soil path enters exactly: carbon - events = material part + soil_path x floor area x share."""
    R = rt['cache'][(LV.T_COMPONENTS, LV.T_INSTANT)]
    E, info = R['E'], R['info']
    typ = res_typ(rt)
    mat = sum(np.asarray(info['intensity_material'][t]) * E['gfa_t'][k] for k, t in enumerate(typ))
    soil = sum(np.asarray(info['soil_path'][t]) * E['gfa_t'][k] for k, t in enumerate(typ)) * E['soil_share']
    assert np.allclose((E['carbon'] - E['b_t'].sum(axis=0))[1:], (mat + soil)[1:], rtol=1e-12, atol=1e-3)


def test_T_2026_unchanged(res, rt):
    E0 = res['get'](PW.REFERENCE, {})['E']
    for key, R in rt['cache'].items():
        E = R['E']
        for k in ('carbon', 'upfront', 'total', 'dwell_in_scope', 'join'):
            assert E[k][1] == pytest.approx(E0[k][1], rel=1e-12), (key, k)


def test_T_shapley_efficiency_exact(rt):
    for metric, (phi, total) in rt['shapley_exact'].items():
        assert sum(phi.values()) == total, metric
    s = rt['subsets']
    assert len(s) == 64
    t = s[s['subset'] == 'T'].iloc[0]
    base = s[s['subset'] == 'P5-stretch-instant'].iloc[0]
    assert total == Fraction(base['LoE_AR']) - Fraction(t['LoE_AR'])


def test_T_checks_pass(res, rt):
    PW.checks_T(res, rt)


def _git_show_tag(tag, path):
    r = subprocess.run(['git', 'show', f'{tag}:{path}'], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


UNCHANGED_PREFIXES = ('P0', 'P2-', 'P3-', 'P4-', 'L2a-', 'L2b-', 'L3-', 'L5-')


@pytest.mark.parametrize('name', ['pathways_runs.csv', 'pathways_annual.csv', 'pathways_bands.csv'])
def test_unchanged_rows_byte_identical_to_v3(name):
    """v3.1 changes P1, P5, the Shapley values and T by design; every row of P0, P2, P3, P4 (central and
    stretch, all scenarios) and of the levers L2a, L2b, L3, L5 is byte-identical to tag pathways_v3."""
    old = _git_show_tag('pathways_v3', f'outputs/pathways/{name}')
    if old is None:
        pytest.skip('git or tag pathways_v3 not available')
    new = open(os.path.join(ROOT, 'outputs', 'pathways', name)).read().splitlines()
    old = old.splitlines()
    assert new[0] == old[0]                                              # same columns
    keep = lambda lines: sorted(l for l in lines[1:] if l.split(',')[0] == 'P0' or l.split(',')[0].startswith(UNCHANGED_PREFIXES[1:]))
    o, n = keep(old), keep(new)
    assert len(o) > 0 and o == n


def test_T_residual_in_people(rt):
    g = rt['gap']['T']
    if g['within_AR']:
        assert g['margin_AR_kt'] >= 0
        return
    R = rt['cache'][(LV.T_COMPONENTS, LV.T_INSTANT)]
    E = R['E']
    res_ = g['residual']
    cut = 1 - g['backcast']['k_AR']
    assert res_['dwellings_not_built_2027_2050'] == pytest.approx(cut * E['dwell_in_scope'][2:].sum(), rel=1e-12)
    S = E['pop'] / E['hh']
    assert res_['new_residents_housed_in_existing_dwellings'] == pytest.approx(cut * (E['dwell_in_scope'][2:] * S[2:]).sum(),
                                                                               rel=1e-12)
