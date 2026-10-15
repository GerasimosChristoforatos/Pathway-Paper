"""MODEL v3.3.0 tests (docs/CHANGELOG_v3_3.md): PAS 2080 restructure, Very High replacement, half-life in the MC.

  * equality with MODEL v3.2.0: the Reference, every lever / pathway run and TL (floor area, carbon, LoE AR, LoE AtP,
    the budgets) equal the v3.2 outputs to 1e-9 under the v3.2 -> v3.3 map of run ids (fixture
    tests/fixtures/v3_2_totals.json, captured from the v3.2.0 outputs by tests/capture_v3_2_totals.py);
  * strategies: S1-S3 partition L1-L9 in PAS 2080 order; the strategy runs exist, P1-P4 do not;
  * Shapley efficiency of the strategy, lever and TL games against the run totals (1e-9);
  * the two sequential waterfalls: steps add up to their totals, end at the Pathway and at TL, the deltas add up to
    Reference - Pathway and Pathway - TL, and sequential_vs_shapley.csv carries the same values;
  * band sums (projection, every pathway run, history); bands not rescaled; zero-year guard; built >= 0;
  * Fig6: the markers lie on the analytic plane; the exact AR / AtP curves give LoE = the level (1e-9); the y-axis
    reaches the AtP curve;
  * Very High replacement: the stored trend is the weighted least-squares fit of the stored census rates; the VHIGH
    runs exist; the Monte Carlo samples the half-life in U(5, 15)."""
import json

import numpy as np
import pandas as pd
import pytest

import engine  # noqa: E402
import layout  # noqa: E402
import naming as N  # noqa: E402
from conftest import ROOT  # noqa: F401,E402

RTOL = 1e-9
FIXTURE = 'tests/fixtures/v3_2_totals.json'
QUANTITIES = ('floor_area_Mm2', 'carbon_kt', 'LoE_AR', 'LoE_AtP', 'B_AR_kt', 'B_AtP_kt')
SETTINGS = ('moderate', 'ambitious')


def _data(rel):
    return layout.data(rel, frozen=False)


def _js(rel):
    with open(_data(rel)) as f:
        return json.load(f)


@pytest.fixture(scope='module')
def runs():
    return pd.read_csv(_data('pathways/runs.csv')).set_index(['scenario', 'run'])


def _close(a, b, atol):
    return np.allclose(a, b, rtol=RTOL, atol=atol)


# ------------------------------------------------------------------ equality with v3.2 ----
def test_equal_to_v3_2_under_the_map(runs):
    fx = json.load(open(FIXTURE))
    bad, n = [], 0
    for r in fx['runs']:
        if r['run_v3_3'] is None:                       # P1-P4: replaced by the strategy runs
            continue
        row = runs.loc[(r['scenario'], r['run_v3_3'])]
        n += 1
        for k in QUANTITIES:
            if not np.isclose(row[k], r[k], rtol=RTOL, atol=0):
                bad.append((r['scenario'], r['run'], r['run_v3_3'], k, row[k], r[k]))
    assert n == fx['meta']['n_mapped'] == 45 and not bad, bad[:10]


def test_map_is_a_permutation_of_the_levers():
    assert sorted(N.LEVER_V3_2) == sorted(N.LEVER_V3_2.values()) == [f'L{i}' for i in range(1, 10)]


# ------------------------------------------------------------------ strategies ----
def test_strategies_partition_the_levers_in_order():
    flat = [lv for st in ('S1', 'S2', 'S3') for lv in N.STRATEGY_LEVERS[st]]
    assert flat == [f'L{i}' for i in range(1, 10)]
    assert all(N.LEVER_STRATEGY[lv] == st for st, ls in N.STRATEGY_LEVERS.items() for lv in ls)
    import levers as LV
    assert {r['item'].split()[0]: r['strategy'].split()[0] for r in LV.lever_table(_js('pathways/levers.json'))} \
        == N.LEVER_STRATEGY


def test_strategy_runs_present_pathway_runs_absent(runs):
    ref = runs.loc['REF']
    for st in N.STRATEGIES:
        for s in SETTINGS:
            assert f'{st}-{s}' in ref.index
    assert not any(str(r).startswith(('P1-', 'P2-', 'P3-', 'P4-', 'P5-')) for r in ref.index)
    for s in SETTINGS:                                    # every strategy cuts carbon; the Pathway cuts more than each
        for st in N.STRATEGIES:
            assert ref.loc[f'{st}-{s}', 'carbon_kt'] < ref.loc['REF', 'carbon_kt']
            assert ref.loc[f'pathway-{s}', 'carbon_kt'] <= ref.loc[f'{st}-{s}', 'carbon_kt']


# ------------------------------------------------------------------ Shapley ----
def test_shapley_efficiency_against_run_totals(runs):
    s = pd.read_csv(_data('pathways/shapley.csv')).query("metric == 'carbon_kt'")
    ref = runs.loc['REF', 'carbon_kt']
    games = {'strategies_moderate': ('REF', 'pathway-moderate'), 'strategies_ambitious': ('REF', 'pathway-ambitious'),
             'levers_moderate': ('REF', 'pathway-moderate'), 'levers_ambitious': ('REF', 'pathway-ambitious'),
             'tl_from_moderate_pathway': ('pathway-moderate', 'TL')}
    for game, (a, b) in games.items():
        g = s[s['game'] == game]
        assert len(g) == (3 if game.startswith('strategies') else 9), game
        assert g['reduction'].sum() == pytest.approx(ref[a] - ref[b], rel=RTOL, abs=1e-9), game
    st = s[s['game'] == 'strategies_moderate'].set_index('player')
    assert sorted(st.index) == ['S1', 'S2', 'S3']


# ------------------------------------------------------------------ waterfalls ----
def test_two_sequential_waterfalls(runs):
    w = pd.read_csv(_data('pathways/waterfall.csv'))
    ref = runs.loc['REF', 'carbon_kt']
    sv = pd.read_csv(_data('pathways/sequential_vs_shapley.csv'))
    for s, g in w.groupby('setting'):
        tot = g.groupby('step').agg(c=('carbon_kt', 'sum'), t=('total_carbon_kt', 'first'), sid=('step_id', 'first'))
        assert _close(tot.c.values, tot.t.values, 1e-9)
        sid = list(tot.sid)
        assert sid == ['REF'] + [f'L{i}' for i in range(1, 10)] + [f'TL{i}' for i in range(1, 10)]
        t = tot.set_index('sid')['t']
        assert t['REF'] == pytest.approx(ref['REF'], rel=1e-12)
        assert t['L9'] == pytest.approx(ref[f'pathway-{s}'], rel=1e-12)
        assert t['TL9'] == pytest.approx(ref['TL'], rel=1e-12)
        d = -np.diff(t.values)                              # the step reductions
        assert d[:9].sum() == pytest.approx(ref['REF'] - ref[f'pathway-{s}'], rel=1e-9)
        assert d[9:].sum() == pytest.approx(ref[f'pathway-{s}'] - ref['TL'], rel=1e-9)
        q = sv[sv['setting'] == s].set_index('player')
        for i, p in enumerate(sid[1:]):
            if p in q.index:
                assert q.loc[p, 'sequential_reduction_kt'] == pytest.approx(d[i], rel=1e-9, abs=1e-9), (s, p)
                if q.loc[p, 'game'] != q.loc[p, 'game']:     # Ambitious TL steps: no Shapley game (empty)
                    continue
                assert q.loc[p, 'sequential_minus_shapley_kt'] == pytest.approx(
                    q.loc[p, 'sequential_reduction_kt'] - q.loc[p, 'shapley_reduction_kt'], abs=1e-9)
    assert set(sv[sv['setting'] == 'moderate']['player']) == {f'L{i}' for i in range(1, 10)} | \
        {f'TL{i}' for i in range(1, 10)}


# ------------------------------------------------------------------ bands ----
def test_projection_bands_sum_to_totals():
    b = pd.read_csv(_data('baseline/bands_annual.csv')).groupby('year')[['floor_area_Mm2', 'carbon_kt']].sum()
    a = pd.read_csv(_data('baseline/annual.csv')).query("source == 'projection'").set_index('year').loc[b.index]
    assert _close(b.floor_area_Mm2, a.floor_area_Mm2, 1e-9)
    assert _close(b.carbon_kt, a.carbon_kt, 1e-9)


def test_pathway_bands_sum_to_totals_every_run():
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
    assert abs(_js('baseline/history_unexplained.json')['difference_Mm2']) < 1e-9


def test_built_nonnegative_every_run():
    a = pd.read_csv(_data('pathways/annual.csv'))
    assert (a['floor_area_Mm2'] >= 0).all()


def test_zero_year_guard():
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
    assert np.all(E['soil_share'] >= 0.0) and np.all(E['soil_share'] <= 1.0)
    assert E['total'][3] == 0.0 and E['soil'][3] == 0.0


# ------------------------------------------------------------------ Fig6 ----
def test_fig6_markers_on_the_analytic_plane(runs):
    from figures import paper_main as PM
    bc = _js('pathways/backcast.json')
    ref = runs.loc['REF']
    want = [f'{st}-{s}' for st in N.STRATEGIES for s in SETTINGS] + ['pathway-moderate', 'pathway-ambitious', 'TL']
    assert sorted(m['run'] for m in bc['solution_space_markers']) == sorted(want)
    for m in bc['solution_space_markers']:
        z = PM.fig6_loe(bc, m['demand_reduction'], m['intensity_reduction'])
        assert np.isclose(z, ref.loc[m['run'], 'LoE_AR'], rtol=RTOL, atol=0), m['run']


def test_fig6_exact_budget_curves():
    from figures import paper_main as PM
    bc = _js('pathways/backcast.json')
    x = np.linspace(0.0, 0.95, 96)
    atp = bc['B_AtP_kt'] / bc['B_AR_kt']
    for level in (1.0, atp):
        y = PM.fig6_curve(bc, x, level)
        assert np.allclose(PM.fig6_loe(bc, x, y), level, rtol=RTOL, atol=0)
    y0 = float(PM.fig6_curve(bc, 0.0, atp))
    r = bc['REF']
    assert (y0 > 1.0) == (r['carbon_fixed_2026_cohort_kt'] > bc['B_AtP_kt'])
    ytop = max(1.0, np.ceil(round(y0 / PM.FIG6_Y_STEP, 9)) * PM.FIG6_Y_STEP)
    assert ytop >= y0 and ytop - PM.FIG6_Y_STEP < y0


# ------------------------------------------------------------------ replacement ----
def test_very_high_trend_is_the_weighted_ls_fit():
    tr = _js('baseline/projection.json')['replacement_trend']
    x, r, w = (np.asarray(tr[k], float) for k in ('x', 'rate', 'weight'))
    A = np.column_stack([np.ones_like(x), x]) * np.sqrt(w)[:, None]
    a, b = np.linalg.lstsq(A, r * np.sqrt(w), rcond=None)[0]
    assert tr['a'] == pytest.approx(a, rel=1e-9) and tr['b'] == pytest.approx(b, rel=1e-9)
    assert tr['rate_2026'] == pytest.approx(a + b * 2026, rel=1e-12)
    assert tr['rate_2050'] == pytest.approx(a + b * 2050, rel=1e-12)
    assert tr['n'] == len(x) == 6 and tr['window'] == [1991, 2023] and (r < 0).sum() == 1


def test_very_high_runs(runs):
    v = runs.loc['VHIGH']
    for r in ('VHIGH', 'pathway-moderate', 'pathway-ambitious', 'TL'):
        assert r in v.index
    assert v.loc['VHIGH', 'carbon_kt'] > runs.loc[('HIGH', 'HIGH'), 'carbon_kt'] > runs.loc[('REF', 'REF'), 'carbon_kt']


def test_half_life_sampled_in_the_monte_carlo():
    import MonteCarlo as MC
    d = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
    h = d[N.identifier('half_life')]
    assert tuple(MC.HALF_LIFE_RANGE) == (5, 15)
    assert h.min() >= 5.0 and h.max() <= 15.0 and h.nunique() == len(h)
