"""Pathway Monte Carlo (MODEL v2.0.0; pathways_mc.py).

* The central draw reproduces the deterministic P5 Combined (Moderate) and TL runs to 1e-9 (every year
  with building and the 2026-2050 totals; zero-building years zero by the model's tolerances).
* The re-run carbon-factor bootstrap reproduces the saved setup exactly (no new random numbers).
* The Reference of the pathway Monte Carlo is the AESA Monte Carlo: its cumulative LoE AR and AtP
  percentiles equal those of data/aesa/results.json.
* Percentiles are ordered and the probabilities are fractions of the 5,000 draws.
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
    a13, red13 = PM.bootstrap_a13(su)                           # raises unless the bootstrap is reproduced
    assert a13.shape == (MC.N_BOOT, len(su['typ']))


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
