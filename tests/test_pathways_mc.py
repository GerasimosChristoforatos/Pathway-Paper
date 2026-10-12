"""Pathway Monte Carlo (MODEL v2.1.0; pathways_mc.py).

* The central draw reproduces the deterministic P5 Combined (Moderate) and TL runs to 1e-9 (every year
  with building and the 2026-2050 totals; zero-building years, none since MODEL v2.1.1, by the model's tolerances).
* The re-run carbon-factor bootstrap reproduces the saved setup exactly (no new random numbers).
* The Reference of the pathway Monte Carlo is the AESA Monte Carlo: its cumulative LoE AR and AtP
  percentiles equal those of data/aesa/results.json.
* Percentiles are ordered and the probabilities are fractions of the 5,000 draws.
* TL is never weaker than Ambitious in a draw (TL6 ratios capped; TL2 above every draw's household size); the
  L2 target is the Monte Carlo High variant; the insight files are consistent with the draws (P(TL within AR) and
  the exceeding draws; SRC / PRCC within [-1, 1] with ordered intervals).
"""
import contextlib
import io
import json
import os

import numpy as np
import pandas as pd
import pytest


import layout as L

pytestmark = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: fewer draws')


@pytest.fixture(scope='module')
def summary():
    return pd.read_csv(L.data('pathways/montecarlo_summary.csv', frozen=False))


def test_central_draw_reproduces_the_deterministic_runs():
    import MonteCarlo as MC
    import pathways_mc as PM
    ctx, params, pT, p5, tl = PM.deterministic()
    with contextlib.redirect_stdout(io.StringIO()):
        su = MC.build_setup(MC.MC_SCENARIOS[0][1])
    worst = PM.check_central(su, ctx, params, pT, p5, tl)       # raises SystemExit otherwise
    assert max(worst.values()) < 1e-9
    a13, red13, a45 = PM.bootstrap_factors(su)                  # raises unless the bootstrap is reproduced
    assert a13.shape == a45.shape == (MC.N_BOOT, len(su['typ']))


def test_reference_is_the_aesa_monte_carlo(summary):
    with open(L.data('aesa/results.json', frozen=False)) as f:
        mc = json.load(f)['mc']['REF']
    s = summary.set_index(['run', 'quantity'])
    for q in ('LoE_AR', 'LoE_AtP'):
        for p in (5, 50, 95):
            assert s.loc[('REF', q), f'p{p}'] == pytest.approx(mc[f'{q}_p{p}'], rel=1e-12)


def test_percentiles_ordered_and_probabilities(summary):
    d = pd.read_csv(L.data('pathways/montecarlo_draws.csv', frozen=False))
    assert len(d) == 5000
    for _, r in summary.iterrows():
        assert r['p5'] <= r['p25'] <= r['p50'] <= r['p75'] <= r['p95']
    for run in ('REF', 'P5', 'TL'):
        for q in ('LoE_AR', 'LoE_AtP'):
            p = summary.set_index(['run', 'quantity']).loc[(run, q), 'probability_LoE_at_most_1']
            assert p == pytest.approx(float(np.mean(d[f'{run}_{q}'] <= 1.0)), abs=0)


def test_draw_rules_and_insights():
    rules = json.load(open(L.data('pathways/montecarlo_draw_rules.json', frozen=False)))
    assert rules['TL2_floor_binds_draws'] == 0 and rules['n_draws'] == 5000
    assert rules['L2_target_vs_montecarlo_high_variant_max_abs_diff'] < 1e-12
    d = pd.read_csv(L.data('pathways/montecarlo_draws.csv', frozen=False))
    cs = json.load(open(L.data('pathways/montecarlo_conditional_tl.json', frozen=False)))
    assert cs['within_AR'] == int((d['TL_LoE_AR'] <= 1).sum())
    assert sorted(e['draw'] for e in cs['exceeding_draws']) == sorted(d.loc[d['TL_LoE_AR'] > 1, 'draw'])
    imp = pd.read_csv(L.data('pathways/montecarlo_importance.csv', frozen=False))
    for m in ('src', 'prcc'):
        assert (imp[f'{m}_lo'] <= imp[m]).all() and (imp[m] <= imp[f'{m}_hi']).all()
    assert imp['prcc'].abs().max() <= 1
    cond = pd.read_csv(L.data('pathways/montecarlo_conditional_tl.csv', frozen=False))
    assert (cond['or_lo'] <= cond['odds_ratio_per_sd']).all() and (cond['odds_ratio_per_sd'] <= cond['or_hi']).all()
