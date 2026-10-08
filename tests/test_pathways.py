"""PATHWAYS v1 (pathways.py, levers.py). Identity: with every lever off the run is the
reference central run (annual carbon, upfront, in-window B, floor area by typology,
demand bands, committed range, cumulative LoE AR / AtP) to 1e-9; each lever at zero
strength is the baseline; 2026 is unchanged in every run; Shapley efficiency holds
exactly; D >= S x OLF, implied vacancy >= 4.0% and no negative dwellings built in
every run; the back-cast gives cumulative LoE AR = 1; the baseline outputs are
byte-identical to tag baseline-PB_v3.1 (outside outputs/pathways/)."""
import copy
import json
import os
import subprocess
from fractions import Fraction

import numpy as np
import pytest

from conftest import ROOT

import levers as LV  # noqa: E402
import pathways as PW  # noqa: E402

TOL = 1e-9
TAG = 'baseline-PB_v3.1'
# written by run_all.py after the tests step (tools/check_outputs.AFTER_TESTS); compared
# with the tag by the final regression check (git diff --stat), not here
AFTER_TESTS = ('outputs/metrics.json', 'outputs/RESULTS.md', 'outputs/BASELINE_DRAFT.md',
               'outputs/PB_METHODS_DRAFT.md')


@pytest.fixture(scope='module')
def res():
    return PW.compute(verbose=False)


def rel(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))


def test_identity_with_every_lever_off(res):
    rep = PW.checks(res)
    assert max(rep.values()) <= TOL, sorted(rep.items(), key=lambda kv: -kv[1])[:5]
    bres = json.load(open(PW.FILE_BOSS_RESULTS))
    pbr = json.load(open(PW.FILE_PB_RESULTS))
    r0 = res['runs'][(res['runs']['run'] == 'P0') & (res['runs']['scenario'] == PW.REFERENCE)].iloc[0]
    assert r0['carbon_kt'] == pytest.approx(bres['carbon_kt'], rel=TOL)
    assert r0['upfront_kt'] == pytest.approx(bres['upfront_kt'], rel=TOL)
    assert r0['b_inwindow_kt'] == pytest.approx(bres['b_inwindow_kt'], rel=TOL)
    assert r0['committed_lower_kt'] == pytest.approx(bres['committed']['lower_kt'], rel=TOL)
    assert r0['committed_upper_kt'] == pytest.approx(bres['committed']['upper_kt'], rel=TOL)
    assert r0['LoE_AR'] == pytest.approx(pbr['deterministic']['S3-10']['LoE_AR'], rel=TOL)
    assert r0['LoE_AtP'] == pytest.approx(pbr['deterministic']['S3-10']['LoE_AtP'], rel=TOL)
    assert round(r0['LoE_AR'], 2) == 4.85 and round(r0['LoE_AtP'], 1) == 19.4
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
    # the bands add up to the totals, in both definitions
    for d in ('boss_results', 'in_scope_figure'):
        s = bd[(bd['run'] == 'P0') & (bd['scenario'] == PW.REFERENCE) & (bd['definition'] == d)]
        assert s['gfa_Mm2'].sum() == pytest.approx(r0['gfa_Mm2'], rel=1e-12)
    s = bd[(bd['run'] == 'P0') & (bd['scenario'] == PW.REFERENCE) & (bd['definition'] == 'in_scope_figure')]
    assert s['carbon_kt'].sum() == pytest.approx(r0['carbon_kt'], rel=1e-12)


def test_envelope_scenarios_reproduce_pb(res):
    pbr = json.load(open(PW.FILE_PB_RESULTS))
    for scen in ('S1', 'S2'):
        r = res['runs'][(res['runs']['run'] == 'P0') & (res['runs']['scenario'] == scen)].iloc[0]
        assert r['carbon_kt'] == pytest.approx(pbr['deterministic'][scen]['I_kt'], rel=TOL)
        assert r['LoE_AR'] == pytest.approx(pbr['deterministic'][scen]['LoE_AR'], rel=TOL)
        assert r['committed_upper_kt'] == pytest.approx(pbr['committed'][scen]['upper_kt'], rel=TOL)


def zero_strength(params):
    """Every lever at zero strength: L1 c = 0, L2 v* = v0 and absorption 0, L3 d = 0,
    L4 target = baseline attached share, L5 r = 1."""
    p = copy.deepcopy(params)
    for s in LV.SETTINGS:
        p['L1']['c'][s] = {t: 0.0 for t in p['L1']['c'][s]}
        p['L2']['v_star'][s] = p['L2']['v0']
        p['L2']['absorption'][s] = 0.0
        p['L3']['d'][s] = 0.0
        p['L4']['target'][s] = p['L4']['baseline_attached']
        p['L5']['r'][s] = {t: 1.0 for t in p['L5']['r'][s]}
    return p


@pytest.mark.parametrize('lever', LV.LEVERS)
def test_each_lever_at_zero_strength_is_the_baseline(res, lever):
    ctx = res['ctxs'][PW.REFERENCE]
    p0 = zero_strength(res['params'])
    R = PW.run(ctx, p0, {lever: 'A'})
    E0 = res['get'](PW.REFERENCE, {})['E']
    E = R['E']
    for k in ('carbon', 'upfront', 'total', 'stock', 'stock_join'):
        assert rel(E[k][1:], E0[k][1:]) <= TOL, k
    assert rel(E['gfa_t'][:, 1:], E0['gfa_t'][:, 1:]) <= TOL
    m, m0 = PW.metrics(ctx, R, 'x', 'A'), PW.metrics(ctx, res['get'](PW.REFERENCE, {}), 'P0', '')
    for k in ('committed_lower_kt', 'committed_upper_kt', 'LoE_AR', 'LoE_AtP', 'soil_kt', 'a13_kt'):
        assert m[k] == pytest.approx(m0[k], rel=TOL), k


def test_ramp():
    w = LV.ramp(np.arange(2025, 2051))
    assert w[0] == 0 and w[1] == 0 and w[2] == pytest.approx(1 / 9) and w[10] == 1 and w[-1] == 1
    w45 = LV.ramp(np.arange(2025, 2051), LV.RAMP_FULL_SENS)
    assert w45[2] == pytest.approx(1 / 19) and w45[20] == 1


def test_2026_unchanged_in_every_run(res):
    E0 = res['get'](PW.REFERENCE, {})['E']
    for (scen, label, rf), R in res['cache'].items():
        Eb = res['get'](scen, {})['E']
        E = R['E']
        for k in ('carbon', 'upfront', 'total', 'dwell_in_scope', 'join'):
            assert E[k][1] == pytest.approx(Eb[k][1], rel=1e-12), (scen, label, k)
        assert np.allclose(E['gfa_t'][:, 1], Eb['gfa_t'][:, 1], rtol=1e-12, atol=0), (scen, label)
    assert res['ctxs'][PW.REFERENCE]['fwd_inputs']['gfa_fixed'] == {1: E0['total'][1]}


def test_lever_inputs_not_modified(res):
    """levers.apply never modifies the reference inputs (pure functions)."""
    ctx = res['ctxs'][PW.REFERENCE]
    fi = ctx['fwd_inputs']
    before = (fi['shares'].values.copy(), {t: np.array(fi['intensity'][t], copy=True) for t in ctx['typ']},
              dict(fi['size']), np.array(fi['rate_unc'], copy=True), fi['v'])
    LV.apply(ctx, res['params'], {L: 'A' for L in LV.LEVERS}, E_nojoin=ctx['E_nojoin'])
    assert np.array_equal(before[0], fi['shares'].values)
    assert all(np.array_equal(before[1][t], fi['intensity'][t]) for t in ctx['typ'])
    assert before[2] == fi['size'] and np.array_equal(before[3], fi['rate_unc']) and before[4] == fi['v']


def test_shapley_efficiency_exact(res):
    for (s, metric), (phi, total) in res['shapley_exact'].items():
        assert sum(phi.values()) == total, (s, metric)            # exact (Fraction arithmetic)
        r = res['runs']
        p0 = r[(r['run'] == 'P0') & (r['scenario'] == PW.REFERENCE)].iloc[0][metric]
        p3 = r[(r['run'] == f'P3-{s}') & (r['scenario'] == PW.REFERENCE)].iloc[0][metric]
        assert total == Fraction(p0) - Fraction(p3)
        sh = res['shapley']
        seq = sh[(sh['setting'] == s) & (sh['metric'] == metric) & (sh['method'] == 'sequential')]
        assert seq['reduction'].sum() == pytest.approx(p0 - p3, rel=1e-12)


def test_shapley_on_a_known_game():
    """Additive game: each player's value is its own effect; one pairwise interaction is split equally."""
    a = dict(zip(LV.LEVERS, (1.0, 2.0, 3.0, 4.0, 5.0)))
    v = {S: 100.0 - sum(a[i] for i in S) - (6.0 if {'L1', 'L2'} <= S else 0.0) for S in PW.subsets(LV.LEVERS)}
    phi = PW.shapley(v)
    assert float(phi['L1']) == pytest.approx(4.0) and float(phi['L2']) == pytest.approx(5.0)
    assert float(phi['L5']) == pytest.approx(5.0)


def test_constraints_in_every_run(res):
    """D >= S x OLF every year (engine extra_clip stays 0), implied vacancy >= 4.0%, no
    negative dwellings built (in scope and all categories)."""
    for (scen, label, rf), R in res['cache'].items():
        E = R['E']
        assert ((E['D'] - E['occ'])[1:] >= 0).all(), (scen, label)
        assert (E['extra_clip'][1:] == 0).all(), (scen, label)
        v = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
        assert (v[1:] >= LV.L2_VACANCY_FLOOR).all(), (scen, label, v[1:].min())
        assert (E['dwell_in_scope'][1:] >= 0).all() and (np.asarray(PW.engine.requirement(E))[1:] >= 0).all()


def test_lever_definitions(res):
    p = res['params']
    assert p['L1']['c']['M'] == {t: 0.065 for t in p['L1']['c']['M']}
    for t, c in p['L1']['c']['A'].items():
        assert c == (0.0 if p['L1']['size_1991_1995'][t] >= p['L1']['size_ref'][t]
                     else pytest.approx(1 - p['L1']['size_1991_1995'][t] / p['L1']['size_ref'][t]))
    assert p['L4']['target']['M'] < p['L4']['target']['A']
    assert p['L4']['target']['A'] == pytest.approx(p['L4']['baseline_attached'] + 0.16)
    assert p['L5']['pooled_check_max_abs'] < 1e-9
    assert p['L5']['r']['M']['Apartments'] == 1.0 and p['L5']['cases']['Detached']['k_M'] == 4
    assert p['L5']['cases']['Townhouses']['k_M'] == 2
    # L4 shares sum to one and the attached increment splits in proportion
    ctx = res['ctxs'][PW.REFERENCE]
    sh = res['get'](PW.REFERENCE, {'L4': 'A'})['inputs']['shares']
    assert np.allclose(sh.sum(axis=1).values, 1.0, rtol=0, atol=1e-12)
    b = ctx['held_shares']
    d_t = sh['Townhouses'].iloc[-1] - b['Townhouses']
    d_a = sh['Apartments'].iloc[-1] - b['Apartments']
    assert d_t / d_a == pytest.approx(b['Townhouses'] / b['Apartments'])
    # L5 changes only A1-A3: A4-A5 and soil identical to P0
    r0 = res['runs'][(res['runs']['run'] == 'P0') & (res['runs']['scenario'] == PW.REFERENCE)].iloc[0]
    r5 = res['runs'][(res['runs']['run'] == 'L5-A') & (res['runs']['scenario'] == PW.REFERENCE)].iloc[0]
    assert r5['a45_kt'] == pytest.approx(r0['a45_kt'], rel=1e-12) and r5['soil_kt'] == pytest.approx(r0['soil_kt'], rel=1e-12)
    assert r5['b_inwindow_kt'] == pytest.approx(r0['b_inwindow_kt'], rel=1e-12)
    assert r5['committed_upper_kt'] == pytest.approx(r0['committed_upper_kt'], rel=1e-12)


def test_backcast(res):
    bc = res['backcast']['P3_A']
    assert bc['LoE_AR_at_k'] == pytest.approx(1.0, abs=1e-9)
    assert bc['k_AR'] == pytest.approx(bc['k_AR_closed_form'], rel=1e-12)
    assert 0 < bc['k_AR'] < 1
    assert bc['LoE_AtP_min_k0'] > 1 and not bc['AtP_attainable']
    assert res['backcast']['P0']['LoE_AR_at_k'] == pytest.approx(1.0, abs=1e-9)
    # linear split reproduces each run's carbon; the grid corner (0, 0) is P0
    sp = res['space']
    r0 = res['runs'][(res['runs']['run'] == 'P0') & (res['runs']['scenario'] == PW.REFERENCE)].iloc[0]
    c00 = sp[(sp['demand_reduction'] == 0) & (sp['intensity_reduction'] == 0)].iloc[0]
    assert c00['LoE_AR'] == pytest.approx(r0['LoE_AR'], rel=1e-12)
    c11 = sp[(sp['demand_reduction'] == 1) & (sp['intensity_reduction'] == 1)].iloc[0]
    assert c11['LoE_AtP'] == pytest.approx(bc['LoE_AtP_min_k0'], rel=1e-12)


def _git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)


def test_baseline_outputs_byte_identical_to_tag():
    """Every output tracked at tag baseline-PB_v3.1 (outside outputs/pathways/) has the
    tag's blob hash. Full runs only: a quick run rewrites the Monte Carlo outputs with
    fewer draws by design. The documents written after this step (AFTER_TESTS) are
    checked by the final regression diff."""
    if os.environ.get('PATHWAY_QUICK') == '1':
        pytest.skip('quick run: Monte Carlo outputs differ by design')
    ls = _git('ls-tree', '-r', TAG, '--', 'outputs/')
    if ls.returncode != 0:
        pytest.skip(f'git or tag {TAG} not available')
    tracked = [line.split(None, 3) for line in ls.stdout.splitlines()]
    files = {p: sha for _, _, sha, p in tracked if not p.startswith('outputs/pathways/') and p not in AFTER_TESTS}
    assert len(files) > 50
    cur = _git('hash-object', *files)
    assert cur.returncode == 0, cur.stderr
    changed = [p for p, h in zip(files, cur.stdout.split()) if files[p] != h]
    assert not changed, changed
