"""MODEL v3.3.1 tests (docs/CHANGELOG_v3_3_1.md): the final figure layout, figure code only plus one deterministic file.

  * deterministic equality with MODEL v3.3.0: every file of the v3.3.0 lock (tests/regression_model_v3_3.json: the
    deterministic files and, for the active profile, the Monte Carlo files) still has its v3.3.0 hash (no Monte Carlo
    re-run; every deterministic total unchanged);
  * the Fig5 waterfalls: the steps of each panel add up from the Reference to its end total (Moderate / Ambitious
    Pathway, TL), each end equals its run (1e-12); the TL steps from the Reference (pathways/waterfall_tl_from_reference
    .csv) equal the prefix subsets of the levers_tl Shapley game and their bands add up to each step's total (1e-9);
    any net-positive step is reported in the figure note;
  * Fig6: the markers lie on the analytic plane (1e-9) and every point of both AtP branches satisfies the contour
    equation (1 - x)(1 - y) = (B_AtP - C_2026) / C_ref and LoE_AR = B_AtP / B_AR (1e-9); one branch has y > 1, x < 1,
    the other x > 1, y < 1;
  * no PDF anywhere in the profile's output tree; the planned figures are PNG only; at most 8 main and 10 Extended Data
    figures."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT  # noqa: F401
import figure_plan as FP
import layout
import runprofile
import regression_v3 as R

RTOL = 1e-9


def _data(rel):
    return layout.data(rel, frozen=False)


def _js(rel):
    with open(_data(rel)) as f:
        return json.load(f)


LOCK33 = json.load(open(R.LOCK_V3_3))


# MODEL v4.0.0: test_deterministic_files_equal_v3_3 and test_montecarlo_files_equal_v3_3 are retired: v3.3.1 changed
# figure code only and checked the data against the v3.3.0 lock; MODEL v4.0.0 changes the model (docs/CHANGELOG_v4.md).
# Equality with v3.3 under the v3.3 settings: tests/test_model_v4.py; the current lock: tests/regression_model_v4.json.


@pytest.fixture(scope='module')
def ref_runs():
    r = pd.read_csv(_data('pathways/runs.csv'))
    return r[r['scenario'] == 'REF'].set_index('run')['carbon_kt']


def test_fig5_waterfall_panels_sum_to_totals(ref_runs):
    from figures import paper_main as PM
    paths, _, _ = PM.waterfall_paths()
    ends = {'moderate': 'pathway-moderate', 'ambitious': 'pathway-ambitious', 'tl': 'TL'}
    assert [k for k, *_ in paths] == ['moderate', 'ambitious', 'tl']
    for key, _, _, steps in paths:
        ids = [s for s, _ in steps]
        tot = np.array([t for _, t in steps])
        assert ids[0] == 'REF' and len(ids) == 10
        assert ids[1:] == ([f'TL{i}' for i in range(1, 10)] if key == 'tl' else [f'L{i}' for i in range(1, 10)])
        assert tot[0] == pytest.approx(ref_runs['REF'], rel=1e-12)
        assert tot[-1] == pytest.approx(ref_runs[ends[key]], rel=1e-12)
        assert np.diff(tot).sum() == pytest.approx(tot[-1] - tot[0], rel=RTOL)


def test_tl_steps_from_the_reference():
    w = pd.read_csv(_data('pathways/waterfall_tl_from_reference.csv'))
    tot = w.groupby('step').agg(c=('carbon_kt', 'sum'), t=('total_carbon_kt', 'first'))
    assert np.allclose(tot['c'], tot['t'], rtol=RTOL, atol=0)               # bands add up to each step's total
    sub = pd.read_csv(_data('pathways/shapley_subsets.csv'))
    sub = sub[sub['game'] == 'levers_tl'].set_index('subset')['carbon_kt']
    for k, t in enumerate(tot['t']):
        key = 'none' if k == 0 else '+'.join(f'L{i}' for i in range(1, k + 1))
        assert t == pytest.approx(sub[key], rel=1e-12), key


def test_fig5_net_positive_steps_reported():
    from figures import paper_main as PM
    paths, _, _ = PM.waterfall_paths()
    ups = [(k, s) for k, _, _, steps in paths for (s, t), (_, p) in zip(steps[1:], steps[:-1]) if t > p]
    note = json.load(open(os.path.join(layout.FIGURE_AUDIT, 'Fig4_pathways.json')))['note']      # MODEL v3.3.2: Fig4
    if ups:
        assert all(s in note for _, s in ups)
    else:
        assert 'Net-positive steps: none' in note


def test_fig6_markers_and_both_atp_branches():
    from figures import paper_main as PM
    bc = _js('pathways/backcast.json')
    r = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')
    for m in bc['solution_space_markers']:
        z = PM.fig6_loe(bc, m['demand_reduction'], m['intensity_reduction'])
        assert np.isclose(z, r.loc[m['run'], 'LoE_AR'], rtol=RTOL, atol=0), m['run']
    atp = bc['B_AtP_kt'] / bc['B_AR_kt']
    k = (bc['B_AtP_kt'] - bc['REF']['carbon_fixed_2026_cohort_kt']) / bc['REF']['carbon_2027_2050_cohorts_kt']
    ext = (-0.05, 1.10)                         # the v3.3.1 square; MODEL v3.3.2 plots -5% to 100% (no AtP branch)
    br = PM.fig6_branches(bc, atp, lim=ext)
    assert k < 0 and len(br) == 2 and not PM.fig6_branches(bc, atp)
    (x1, y1), (x2, y2) = br
    assert (x1 < 1).all() and (y1 > 1).all() and (x2 > 1).all() and (y2 < 1).all()
    lo, hi = ext
    for x, y in br:
        assert np.allclose((1 - x) * (1 - y), k, rtol=RTOL, atol=0)
        assert np.allclose(PM.fig6_loe(bc, x, y), atp, rtol=RTOL, atol=0)
        assert x.min() >= lo and x.max() <= hi and y.min() >= lo and y.max() <= hi
    for x, y in PM.fig6_branches(bc, 1.0):                                    # the AR line, exact
        assert np.allclose(PM.fig6_loe(bc, x, y), 1.0, rtol=RTOL, atol=0)


def test_no_pdf_written_png_only():
    assert runprofile.get('formats') == ('png',)
    pdfs = [os.path.join(d, f) for d, _, fs in os.walk(layout.OUT) for f in fs if f.lower().endswith('.pdf')]
    assert not pdfs, pdfs[:5]
    for _, fid, _ in FP.all_figures(profile_full=runprofile.name() == 'full'):
        assert os.path.exists(layout.figure(fid) + '.png'), fid


def test_display_item_limits():
    assert len(FP.PAPER_MAIN) <= 8 and len(FP.PAPER_EXTENDED) <= 10
    # MODEL v4.2.2: Fig5 is vacant for now (author's decision: no renumbering; the reduction by demand band is SF7)
    assert [h['id'] for h in FP.PAPER_MAIN] == [f'Fig{i}' for i in range(1, 9) if i != 5]
    assert [h['id'] for h in FP.PAPER_EXTENDED] == [f'ED{i}' for i in range(1, len(FP.PAPER_EXTENDED) + 1)]
