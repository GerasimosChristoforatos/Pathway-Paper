"""MODEL v3.0.0: the model rules and the STOP conditions, on the functions and on the outputs of the active run profile
(outputs/_light/ by default; PATHWAY_PROFILE=full for outputs/).

  * the Reference absorbs the 2026 overbuild by 2035 (logistic; payback capped at the year's building with carry);
    the excess is held fixed in every run;
  * the lever rule: Moderate is the exact midpoint of the native parameter; TLn at least as strong as Ambitious;
    the data STOP conditions (L5 sample, f_t in [0, 1], High >= Medium);
  * ordering Reference >= Moderate >= Ambitious >= TL; TL <= P5 in every Monte Carlo draw; L4 / L5 interaction;
  * built_t >= 0 in every run and year; implied vacancy >= 4.0% in every non-TL run; cumulative re-occupied <=
    cumulative released; Shapley efficiency; waterfall sums; material and stage values never negative.
"""
import json

import numpy as np
import pandas as pd
import pytest

import engine
import layout
import levers as LV

D = lambda rel: layout.data(rel, frozen=False)


def js(rel):
    with open(D(rel)) as f:
        return json.load(f)


# ------------------------------------------------------------------ overbuild absorption (engine) ----
def test_logistic_weights_endpoints():
    y = np.arange(2025, 2051)
    w = engine.logistic_weights(y, 2026, 2035)
    assert w[0] == 0 and w[1] == 0 and np.all(w[10:] == 1.0) and np.all(np.diff(w) >= 0)
    assert np.allclose(w, LV.ramp(y), rtol=0, atol=1e-15)       # the same rule as the levers


def test_absorb_overbuild_cap_and_carry():
    """A year whose building cannot absorb its payback builds nothing and carries the shortfall to the next years;
    the whole cumulative excess is paid back once w = 1."""
    n = 12
    excess = np.r_[0.0, 100.0, 50.0, 25.0, np.zeros(n - 4)]
    w = np.r_[0.0, 0.0, 0.3, 0.8, np.ones(n - 4)]
    need = np.r_[10.0, 10.0, 10.0, 5.0, np.full(n - 4, 30.0)]
    join, ab = engine.absorb_overbuild(excess, w, need)
    assert np.all(ab['built'] >= -1e-12)
    assert ab['cap_binds'][3] and ab['carry'][3] > 0
    assert np.isclose(ab['paid'].sum(), excess.sum()) and np.isclose(ab['U'][-1], 0.0)
    assert np.allclose(join, excess - ab['paid'])


def test_reference_absorbs_by_2035(B):
    ji = B['join_info']['50th']
    E = B['engine_out']['50th']
    yrs = np.asarray(B['forecast_years'])
    i35 = int(np.where(yrs == 2035)[0][0])
    assert np.allclose(E['stock_join'][i35:], 0.0, atol=1e-6)
    v_impl = 1 - E['hh'] / (E['stock'] + E['stock_join'])
    assert np.allclose(v_impl[i35:], B['v_forward'], rtol=1e-9)
    assert np.isclose(-ji['payback'][1:].sum(), ji['excess'][1:].sum(), rtol=1e-9)
    assert B['v_forward'] == pytest.approx(0.0539, abs=5e-5)          # frozen at the 2023 census value


def test_absorption_log():
    lg = pd.read_csv(D('baseline/overbuild_absorption_log.csv'))
    assert list(lg['year']) == list(range(2025, 2051))
    assert (lg['dwellings_built'] >= 0).all()
    assert np.allclose(lg['surplus_vacant'], lg['cumulative_excess'] - lg['payback_paid'].cumsum(), atol=1e-6)


def test_excess_identical_in_every_run():
    p = js('pathways/levers.json')
    assert p['identity_checks']['overbuild_excess_max_abs_diff_between_runs'] == 0.0


# ------------------------------------------------------------------ the lever rule ----
@pytest.fixture(scope='module')
def params():
    return js('pathways/levers.json')


@pytest.mark.parametrize('lever', LV.LEVERS)
def test_moderate_is_the_exact_midpoint(params, lever):
    years = np.arange(2025, 2051)
    nat = lambda lev: LV.native(params, lever, lev, years)
    ref, mod, amb = nat('reference'), nat('moderate'), nat('ambitious')
    if lever == 'L6':
        ref = params['L6']['s']['reference']
    if isinstance(mod, dict):
        for k in mod:
            assert mod[k] == pytest.approx((ref[k] + amb[k]) / 2, rel=1e-15, abs=1e-15), (lever, k)
    else:
        assert np.allclose(np.asarray(mod, float), (np.asarray(ref, float) + np.asarray(amb, float)) / 2,
                           rtol=1e-15, atol=1e-15), lever


def test_lever_data_stop_conditions(params):
    assert params['L5']['n'] == 16 and set(params['L5']['typologies']) == {'Detached', 'Townhouses', 'Apartments'}
    assert all(0.0 <= f <= 1.0 for f in params['L4']['f']['ambitious'].values())
    assert params['L1']['high_ge_medium_every_year']
    v = params['L1']['variants']
    assert all(v['High'][y] >= v['Medium'][y] for y in v['High'] if int(y) <= 2043)
    assert all(r['ok'] for r in params['tl_strength'])
    assert {k: round(m['size_min'], 1) for k, m in params['L4']['minima'].items()} == \
        {'Detached': 148.8, 'Townhouses': 105.8, 'Apartments': 91.0}
    assert params['L8']['estimator']['r'] == pytest.approx(0.827, abs=5e-4)


def test_ordering():
    o = js('pathways/ordering_checks.json')
    assert not o['violations'], o['violations'][:3]
    assert all(r['ok'] for r in o['cumulative'])


def test_tl_le_p5_every_draw():
    d = pd.read_csv(D('pathways/montecarlo_draws.csv'))
    assert (d['TL_carbon_kt'] <= d['P5A_carbon_kt'] * (1 + 1e-12)).all()
    assert (d['P5A_carbon_kt'] <= d['P5_carbon_kt'] * (1 + 1e-12)).all()


# ------------------------------------------------------------------ runs ----
@pytest.fixture(scope='module')
def ctx_params():
    import pathways as PW
    B = PW.boss_state(PW.REFERENCE)
    return PW.base_context(B, PW.REFERENCE, PW.boundaries()), PW.resolve_params(B)


def test_l1_l2_interaction(ctx_params):
    """With L5 off, L4 reproduces its standalone run; L5 changes the total floor area; with both on, the dwelling
    size is the L5-scaled size with the L4 cut applied to the scaled margin."""
    import pathways as PW
    ctx, p = ctx_params
    runs = pd.read_csv(D('pathways/runs.csv'))
    r = runs[runs['scenario'] == 'REF'].set_index('run')
    R1 = PW.run(ctx, p, {'L4': 'ambitious'})
    assert R1['E']['carbon'][1:].sum() / 1e6 == pytest.approx(r.loc['L4-ambitious', 'carbon_kt'], rel=1e-12)
    R2 = PW.run(ctx, p, {'L5': 'ambitious'})
    R0 = PW.run(ctx, p, {})
    assert R2['E']['total'][2:].sum() < R0['E']['total'][2:].sum() * (1 - 1e-3)
    R12 = PW.run(ctx, p, {'L4': 'ambitious', 'L5': 'ambitious'})
    w = LV.ramp(ctx['years'])
    S = np.asarray(ctx['pop'], float) / np.asarray(ctx['hh'], float)
    for t in ctx['typ']:
        k2 = 1 - w * (1 - p['L5']['r']['ambitious'])
        occ = S * float(ctx['olf'][t]) * k2
        base = float(ctx['size_ref'][t]) * k2
        f = p['L4']['f']['ambitious'][t]
        assert np.allclose(R12['inputs']['size'][t], occ + (1 - f * w) * (base - occ), rtol=1e-12)


def test_built_nonnegative_and_vacancy_floor():
    a = pd.read_csv(D('pathways/annual.csv'))
    assert (a['dwellings_built_all_categories'] >= -1e-6).all()
    s = pd.read_csv(D('pathways/shapley_subsets.csv'))
    assert (s['dwellings_built_min'] >= -1e-6).all()
    non_tl = a[~a['run'].str.contains('tl|TL')]
    assert (non_tl['implied_vacancy'] >= LV.L2_VACANCY_FLOOR).all()


def test_reoccupation_log():
    lg = pd.read_csv(D('pathways/reoccupation_log.csv'))
    for _, g in lg.groupby('run'):
        assert (g['cumulative_reoccupied'] <= g['cumulative_released'] + 1e-6).all()
        assert (g['built'] >= -1e-6).all()
        assert np.allclose(g['reoccupied'], g['reoccupied_tl1'] + g['reoccupied_tl2'], atol=1e-6)


def test_reoccupation_rule_recomputes_share():
    import pathways as PW
    years = np.arange(2025, 2051)
    gross = np.full(26, 100.0)
    rel = np.zeros(26)
    rel[5] = 1000.0                                           # released late: the early targets cannot be met
    ro = PW.reoccupation(years, gross, rel)
    assert ro['release_binds'][2] and ro['reoccupied'][2] == 0.0
    assert np.all(np.cumsum(ro['reoccupied']) <= np.cumsum(rel) + 1e-9)
    assert np.all(ro['built'] >= 0) and ro['reoccupied_total'] == pytest.approx(1000.0)


def test_shapley_efficiency():
    s = pd.read_csv(D('pathways/shapley.csv'))
    sub = pd.read_csv(D('pathways/shapley_subsets.csv'))
    for (game, metric), g in s.groupby(['game', 'metric']):
        t = sub[sub['game'] == game]
        v0 = float(t[t['n_players'] == 0][metric].iloc[0])
        v1 = float(t[t['n_players'] == t['n_players'].max()][metric].iloc[0])
        assert g['reduction'].sum() == pytest.approx(v0 - v1, rel=1e-9, abs=1e-9), (game, metric)


def test_waterfall_sums():
    w = pd.read_csv(D('pathways/waterfall.csv'))
    r = pd.read_csv(D('pathways/runs.csv'))
    r = r[r['scenario'] == 'REF'].set_index('run')
    for s, g in w.groupby('setting'):
        tot = g.groupby('step')['carbon_kt'].sum()
        assert np.allclose(tot.values, g.groupby('step')['total_carbon_kt'].first().values, rtol=1e-9)
        last = g[g['step'] == g['step'].max()]['total_carbon_kt'].iloc[0]
        p5 = g[g['step_id'] == 'P4']['total_carbon_kt'].iloc[0]
        assert p5 == pytest.approx(r.loc[f'P5-{s}', 'carbon_kt'], rel=1e-12)
        assert last == pytest.approx(r.loc['TL', 'carbon_kt'], rel=1e-12)


def test_material_and_stage_values_nonnegative():
    st = pd.read_csv(D('baseline/annual_by_stage.csv'))
    assert (st.drop(columns='year') >= 0).all().all()
    assert (pd.read_csv(D('baseline/annual_by_material.csv'))['carbon_kt'] >= 0).all()
    a = pd.read_csv(D('pathways/annual.csv'))
    assert (a[['a1a3_kt', 'a4a5_kt', 'soil_carbon_loss_kt', 'maintenance_kt']] >= -1e-9).all().all()


def test_run_meta():
    with open(layout.RUN_META) as f:
        m = json.load(f)
    import runprofile
    assert m['profile'] == runprofile.name() and m['n_draws'] == runprofile.get('n_draws')
    assert {'seeds', 'git_hash', 'input_hash', 'timestamp'} <= set(m)
