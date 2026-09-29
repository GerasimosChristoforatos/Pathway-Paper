"""Engine equivalence: the unified engine (engine.py, called by Boss.py and
MonteCarlo.py) against FROZEN copies of the code before unification
(tests/legacy/, commit a25fbff).

  test_montecarlo_equivalence   new MonteCarlo.project() vs legacy project() on
                                random draws of ALL its inputs (from the input
                                distributions, and from widened ranges so the
                                tails are exercised)
  test_montecarlo_response_mode the same with the 2025 household-size
                                deviation carried (b, rho sampled)
  test_boss_equivalence         new Boss.main() vs legacy Boss.main() on random
                                draws of Boss's own settings, comparing every
                                band, stock term, household path and carbon table

Tolerance: 1e-9 x the largest absolute value of each compared series.
Draw counts: PATHWAY_EQUIV_MC_DRAWS (default 300) and
PATHWAY_EQUIV_BOSS_DRAWS (default 12; the recorded proof in
outputs/equivalence.md used 200). A summary is written to
outputs/equivalence.md.

These tests hold with the settings that existed before unification. Later
changes add new behaviour behind new flags; with those flags at their old
values the engine must keep reproducing the legacy code, and these tests
enforce that.
"""
import contextlib
import importlib
import io
import os
import sys
import traceback

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'legacy'))
TOL = 1e-9
from legacy_flags import LEGACY_FLAGS  # noqa: E402
N_MC = int(os.environ.get('PATHWAY_EQUIV_MC_DRAWS', 300))
N_BOSS = int(os.environ.get('PATHWAY_EQUIV_BOSS_DRAWS', 12))
REPORT = os.path.join(os.path.dirname(HERE), 'outputs', 'equivalence.md')
_summary = {}


def rel(a, b):
    """max |a - b| / max |b| over finite entries; inf if shapes or the
    positions of non-finite entries differ."""
    a, b = np.atleast_1d(np.asarray(a, float)), np.atleast_1d(np.asarray(b, float))
    if a.shape != b.shape or not np.array_equal(np.isfinite(a), np.isfinite(b)):
        return np.inf
    m = np.isfinite(b)
    if not m.any():
        return 0.0
    return float(np.abs(a[m] - b[m]).max() / max(np.abs(b[m]).max(), 1e-300))


def _fresh(name):
    mod = importlib.import_module(name)
    return importlib.reload(mod)


def _mc_pair(response=False):
    import Boss
    import Boss_legacy
    for B in (Boss, Boss_legacy):
        importlib.reload(B)
        B.SHOW_PLOTS = False
        B.HH_SIZE_RESPONSE = response
    for k, v in LEGACY_FLAGS.items():          # new code, old behaviour
        setattr(Boss, k, v)
    MC, MCL = _fresh('MonteCarlo'), _fresh('MonteCarlo_legacy')
    with contextlib.redirect_stdout(io.StringIO()):
        su, sul = MC.build_setup(), MCL.build_setup()
    return MC, MCL, su, sul


def _draws(MC, su, n, seed):
    """Half from the input distributions, half from widened ranges
    (0.1st-99.9th percentile of each distribution, uniformly)."""
    rng = np.random.default_rng(seed)
    d = MC.distributions(su)
    out = []
    for i in range(n):
        p = {}
        for k in MC.PARAMS:
            u = rng.uniform() if i % 2 == 0 else rng.uniform(0.001, 0.999)
            p[k] = float(d[k].ppf(u))
        if i % 2 == 1:   # widened: stretch continuous inputs beyond the distribution
            for k in ('phi', 'complete', 'vacancy', 'rv_share', 'regime'):
                if k in p:
                    lo, hi = d[k].ppf(0.0005), d[k].ppf(0.9995)
                    p[k] = float(rng.uniform(lo - 0.3 * (hi - lo), hi + 0.3 * (hi - lo)))
            p['phi'] = float(np.clip(p['phi'], 0.05, 0.995))
            p['regime'] = float(np.clip(p['regime'], 0.0, 1.0))
            p['complete'] = float(np.clip(p['complete'], 0.85, 1.0))
        out.append(p)
    return out


def _compare_mc(response):
    """Legacy MC floor area = in-scope dwellings x D. The unified engine uses
    Boss's definition, which adds extra_clip (> 0 only where the extra-space
    floor binds). So new == legacy + extra_clip (floor area), and carbon /
    upfront differ by extra_clip split by typology x intensity."""
    MC, MCL, su, sul = _mc_pair(response)
    worst = {k: 0.0 for k in ('gfa', 'carbon', 'upfront', 'rv_units', 'hh', 'S')}
    n = N_MC if not response else max(N_MC // 3, 100)
    n_clip = 0
    draws = _draws(MC, su, n, seed=7 if not response else 8) + [MC.central(su)]
    for p in draws:
        a, b = MC.project(su, p), MCL.project(sul, p)
        clip = a['extra_clip']
        clip_t = a['gfa_t'] / np.where(a['gfa'] == 0, 1, a['gfa']) * clip   # clip by typology
        exp = dict(gfa=b['gfa'] + clip, carbon=b['carbon'] + (a['I'][:, None] * clip_t).sum(axis=0),
                   upfront=b['upfront'] + (a['U'][:, None] * clip_t).sum(axis=0),
                   rv_units=b['rv_units'], hh=b['hh'], S=b['S'])
        n_clip += bool((clip[1:] > 0).any())
        for k in worst:
            worst[k] = max(worst[k], rel(a[k][1:], exp[k][1:]))
    return len(draws), worst, n_clip


def test_montecarlo_equivalence():
    n, worst, n_clip = _compare_mc(False)
    _summary['MonteCarlo.project, default mode'] = (n, worst, n_clip)
    assert max(worst.values()) <= TOL, worst


def test_montecarlo_response_mode():
    n, worst, n_clip = _compare_mc(True)
    _summary['MonteCarlo.project, 2025 deviation carried (b, rho sampled)'] = (n, worst, n_clip)
    assert max(worst.values()) <= TOL, worst


# ------------------------------------------------------------------ Boss ----
def boss_settings(rng):
    s = {}
    s['HH_CENSUS_REBASE'] = rng.choice(['occupied_plus_away', 'occupied', None], p=[.6, .2, .2])
    starts = [1992, 1996, 2001, 2006, 2013] + ([2019] if s['HH_CENSUS_REBASE'] else [])
    s['DEMOLITION_CALIB_START'] = int(rng.choice(starts))
    s['COMPLETION_RATE'] = float(rng.uniform(0.90, 0.98))
    s['DEMOLITION_RATE'] = float(rng.uniform(0.0005, 0.004))
    s['DAMPING_PHI'] = float(rng.uniform(0.3, 0.99))
    s['TREND_WINDOW_START'] = int(rng.integers(2006, 2017))
    s['DWELLING_SIZE_REF'] = [(2023, 2025), (2016, 2025), (2020, 2025), (2025, 2025)][rng.integers(4)]
    s['RV_SHARE_REF'] = [(2016, 2025), (2011, 2025), (2020, 2025)][rng.integers(3)]
    s['HH_SIZE_VARIANT'] = str(rng.choice(['Medium', 'Low', 'High']))
    s['HH_SIZE_RESPONSE'] = bool(rng.uniform() < 0.25)
    s['DEVIATION_PERSISTENCE'] = 'estimated' if rng.uniform() < 0.6 else float(rng.uniform(0, 0.95))
    s['FLOOR_HOUSEHOLD_DECLINE'] = bool(rng.uniform() < 0.8)
    s['POP_PERCENTILE_METHOD'] = 'published_levels' if rng.uniform() < 0.8 else 'cumulated_growth'
    s['CONSUMPTION_BASIS'] = str(rng.choice(['stock_vacancy', 'per_capita', 'per_household',
                                             'extra_space_plus_other'], p=[.7, .1, .1, .1]))
    s['HOUSEHOLD_METHOD'] = str(rng.choice(['matched_size', 'single_living_arrangement',
                                            'variant_pairing'], p=[.8, .1, .1]))
    s['DEMAND_BASIS'] = 'bim_olf' if rng.uniform() < 0.8 else 'per_resident'
    s['USE_GROSS_BASIS_OLF'] = bool(rng.uniform() < 0.2)
    s['RV_IN_STOCK'] = bool(rng.uniform() < 0.85)
    s['OTHER_CASE'] = str(rng.choice(['central', 'low', 'high']))
    s['EWMA_SPAN'] = int(rng.choice([10, 15, 20]))
    return s


def run_module(name, settings):
    M = importlib.reload(importlib.import_module(name))
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


def compare_boss(N, L):
    """Largest relative difference over every compared output."""
    out = {}
    for pct in ('5th', '50th', '95th'):
        for k in L['results'][pct]:
            out[f'results.{k}'] = max(out.get(f'results.{k}', 0), rel(N['results'][pct][k], L['results'][pct][k]))
        for k in L['stock_fwd'].get(pct, {}):
            out[f'stock_fwd.{k}'] = max(out.get(f'stock_fwd.{k}', 0), rel(N['stock_fwd'][pct][k], L['stock_fwd'][pct][k]))
        out['households'] = max(out.get('households', 0),
                                rel(N['households_forecast'][pct], L['households_forecast'][pct]))
    for k in ('carbon_total_typ', 'evol_typ_total', 'evol_typ_growth', 'evol_typ_vac', 'evol_typ_repl',
              'evol_typ_unc', 'evol_typ_rv', 'flow_annual', 'dem_mat', 'evolving_gfa_shares'):
        out[k] = rel(N[k].values, L[k].values)
    num = L['df_forecast'].select_dtypes('number').columns
    out['df_forecast'] = rel(N['df_forecast'][num].values, L['df_forecast'][num].values)
    for k in ('tot_carbon_median', 'unconsented_rate', 'other_dev_2025', 'rho_other', 'v_forward'):
        out[k] = rel(N[k], L[k])
    return out


def test_boss_equivalence():
    rng = np.random.default_rng(20260929)
    worst, errors, n_ok, bases = {}, [], 0, {}
    for i in range(N_BOSS):
        s = boss_settings(rng) if i else {}        # draw 0 = adopted settings
        res = {}
        for name in ('Boss', 'Boss_legacy'):
            try:
                res[name] = ('ok', run_module(name, {**LEGACY_FLAGS, **s} if name == 'Boss' else s))
            except Exception as e:  # noqa: BLE001
                res[name] = ('err', f'{type(e).__name__}: {e}')
        kinds = (res['Boss'][0], res['Boss_legacy'][0])
        if kinds == ('err', 'err'):
            assert res['Boss'][1] == res['Boss_legacy'][1], (s, res)
            errors.append((s, res['Boss'][1]))
            continue
        assert kinds == ('ok', 'ok'), (s, res['Boss'][1] if kinds[0] == 'err' else res['Boss_legacy'][1])
        d = compare_boss(res['Boss'][1], res['Boss_legacy'][1])
        for k, v in d.items():
            worst[k] = max(worst.get(k, 0), v)
        n_ok += 1
        bases[s.get('CONSUMPTION_BASIS', 'stock_vacancy')] = bases.get(s.get('CONSUMPTION_BASIS', 'stock_vacancy'), 0) + 1
    _summary['Boss.main, random settings'] = (n_ok, worst, errors, bases)
    bad = {k: v for k, v in worst.items() if v > TOL}
    assert not bad, bad


def teardown_module(module):
    lines = ['# Engine equivalence (generated by tests/test_engine_equivalence.py)', '',
             f'Unified engine vs frozen pre-unification code (tests/legacy/). Tolerance {TOL:g} '
             'x the largest absolute value of each series.', '']
    for lab, val in _summary.items():
        n, worst = val[0], val[1]
        lines.append(f'## {lab}: {n} draws, largest relative difference {max(worst.values()):.2e}')
        lines.append('')
        lines.append('| output | largest relative difference |')
        lines.append('|---|---|')
        for k, v in sorted(worst.items()):
            lines.append(f'| {k} | {v:.2e} |')
        if len(val) == 3:
            lines.append('')
            lines.append(f'Draws in which the extra-space floor binds in at least one year (new = legacy '
                         f'+ that term, verified above): {val[2]}.')
        if len(val) > 3:
            errors, bases = val[2], val[3]
            lines.append('')
            lines.append(f'Consumption bases drawn: {bases}.')
            if errors:
                lines.append(f'{len(errors)} settings raised the SAME exception in both versions (not '
                             'counted as draws): ' + '; '.join(sorted({e for _, e in errors})) + '.')
        lines.append('')
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, 'w') as f:
        f.write('\n'.join(lines))
