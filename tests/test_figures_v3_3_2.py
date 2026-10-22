"""MODEL v3.3.2 tests (docs/CHANGELOG_v3_3_2.md): the final main-figure layout, figure code only.

  * the data are byte-identical to MODEL v3.3.1: every file of the v3.3.1 lock (tests/regression_model_v3_3_1.json;
    the deterministic files and, for the active profile, the Monte Carlo files) keeps its hash
    (tests/test_regression_model_v3.py checks the same lock file by file);
  * Fig5: each column total equals Reference - run (pathways/runs.csv) and the band reductions add up to it (1e-9);
  * Fig3b: the 95% interval comes from the per-draw cumulative carbon with the percentile method of MonteCarlo.py, which
    reproduces the stored 5th / 95th percentiles (montecarlo/summary_REF.csv) exactly;
  * Fig6: the markers lie on the analytic plane (1e-9); the plotted square is -5% to 90% (MODEL v4.2.2); the AR line is exact.
  * the schematic is a supplementary figure (SF1), not a main figure."""
import json

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT  # noqa: F401
import figure_plan as FP
import layout
import regression_v3 as R

RTOL = 1e-9
LOCK = json.load(open(R.LOCK))


def _data(rel):
    return layout.data(rel, frozen=False)


# MODEL v4.0.0: test_data_byte_identical_to_v3_3_1 is retired (a figure-only release check; MODEL v4.0.0 changes the
# model). The current lock: tests/regression_model_v4.json (tests/test_regression_model_v3.py).


def test_fig5_column_totals_are_reference_minus_run():
    from figures import paper_main as PM
    red, tot = PM.reduction_by_band()
    r = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')['carbon_kt']
    assert set(tot) == set(PM.FIG5_RUNS) == {'pathway-moderate', 'pathway-ambitious', 'TL'}
    for run in PM.FIG5_RUNS:
        assert tot[run] == pytest.approx(r['REF'] - r[run], rel=RTOL, abs=1e-9), run
        assert sum(red[run].values()) == pytest.approx(tot[run], rel=RTOL, abs=1e-9), run


def test_fig3_interval_from_the_draws():
    from figures import paper_main as PM
    d = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))['carbon_kt'].to_numpy(float)
    s = pd.read_csv(layout.montecarlo('summary', 'REF', frozen=False)).set_index('output').loc['carbon_kt']
    assert np.percentile(d, 5) == pytest.approx(s['p5'], rel=1e-12)
    assert np.percentile(d, 95) == pytest.approx(s['p95'], rel=1e-12)
    lo, hi = PM.mc_cumulative_interval()
    assert PM.FIG3_INTERVAL == (2.5, 97.5) and lo < s['p5'] < s['p95'] < hi


def test_fig6_markers_square_and_ar_line():
    from figures import paper_main as PM
    with open(_data('pathways/backcast.json')) as f:
        bc = json.load(f)
    r = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')
    for m in bc['solution_space_markers']:
        z = PM.fig6_loe(bc, m['demand_reduction'], m['intensity_reduction'])
        assert np.isclose(z, r.loc[m['run'], 'LoE_AR'], rtol=RTOL, atol=0), m['run']
    assert PM.FIG6_LIM == (-0.05, 0.85)                        # MODEL v4.2.2: clipped at 85%
    for x, y in PM.fig6_branches(bc, 1.0):
        assert np.allclose(PM.fig6_loe(bc, x, y), 1.0, rtol=RTOL, atol=0)
        assert x.min() >= -0.05 and y.max() <= 0.85


def test_schematic_is_supplementary():
    assert 'Fig1_model_schematic' not in {h['file'] for h in FP.PAPER_MAIN}
    assert FP.SUPPLEMENTARY[0]['file'] == 'SF1_model_schematic'
    assert [h['file'] for h in FP.PAPER_MAIN] == [
        'Fig1_floor_area', 'Fig2_reference_carbon', 'Fig3_reference_boundaries', 'Fig4_pathways',
        'Fig5_model_schematic', 'Fig6_solution_space', 'Fig7_shapley_levers', 'Fig8_uncertainty']
