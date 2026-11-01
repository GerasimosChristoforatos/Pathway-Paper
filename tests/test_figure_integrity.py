"""The figure tests that check drawn values against the data (tests/README.md):

  * the model scripts do not plot; drawing leaves outputs/data byte-identical; every planned figure is drawn and
    audited (smoke);
  * the sign rules of the drawing helpers: cumulative bars end at their net, stacked series up + down = net, materials
    and stages never negative;
  * the Fig4 waterfalls and the band reductions of the Pathways and TL add up to the run totals; the TL steps from the Reference;
    the net-positive steps reported; Fig3b's interval from the draws; Fig1's annual line against the census-interval
    means; the ED4 / ED5 notes stop when the code and the outputs disagree;
  * the palette file: a missing key, an unknown key, a value that is not "#RRGGBB" (and an opacity
    outside [0, 1]) are rejected;
  * SF2b: up + down = net for every column and year; the census-interval means of the annual line = the column nets;
    the projection's net replacement is one band, equal to the sum of its three parts;
  * ED10: an Extended Data item; every drawn history line equals its source data (not smoothed).
"""
import hashlib
import json
import os
import re

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT
import figure_plan as FP
import layout
import runprofile
from figures import draw as P
from figures import style as S

RTOL = 1e-9


def _data(rel):
    return layout.data(rel, frozen=False)


# ---------------------------------------------------------------------------
# model scripts, smoke, sign rules
# ---------------------------------------------------------------------------
MODEL_SCRIPTS = ('projection.py', 'Diagnostics.py', 'boundaries.py', 'MonteCarlo.py', 'pathways.py', 'pathways_mc.py',
                 'tools/figures_report.py', 'engine.py', 'levers.py')


@pytest.mark.parametrize('script', MODEL_SCRIPTS)
def test_model_scripts_do_not_plot(script):
    src = open(os.path.join(ROOT, script)).read()
    assert not re.search(r'^\s*(import|from)\s+(matplotlib|figures|style|plotting)\b', src, re.M), script
    assert 'savefig' not in src and 'plt.' not in src, script


def test_bars_cumulative_end_at_net():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    x = np.arange(3.0)
    parts = [('growth', np.array([5.0, 4.0, 3.0])), ('overbuild_absorbed', np.array([-1.0, -2.5, 0.0])),
             ('extra_space', np.array([2.0, 1.0, 1.0])), ('unconsented', np.array([-0.5, -0.5, -0.5]))]
    net = sum(v for _, v in parts)
    up, dn, end = P.bars_cumulative(ax, x, parts, width=0.6, net=net)
    assert np.allclose(end, net, rtol=0, atol=1e-9)
    neg = [a for a in ax.patches if a.get_gid() == P.NEG_BAR_GID]
    assert neg and all(a.get_facecolor()[3] == 0 and not a.get_hatch() for a in neg)
    with pytest.raises(SystemExit):
        P.bars_cumulative(ax, x, parts, width=0.6, net=net + 1.0)
    plt.close(fig)


def test_stack_series_up_minus_down_is_net():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    x = np.arange(2026.0, 2031.0)
    parts = [('growth', np.full(5, 3.0)), ('overbuild_absorbed', -np.linspace(0, 1, 5)), ('vacancy', np.full(5, 0.5))]
    net = sum(v for _, v in parts)
    up, dn = P.stack_series(ax, x, parts, net=net)
    assert np.allclose(up - np.abs(dn), net, atol=1e-9)
    assert len([ln for ln in ax.get_lines() if ln.get_gid() == P.NET_GID]) == 1
    plt.close(fig)


def test_material_and_stage_values_never_negative():
    with pytest.raises(SystemExit):
        P.nonnegative('stage', np.array([1.0, -0.1]))


def _records():
    d = layout.FIGURE_AUDIT
    return {f[:-5]: json.load(open(os.path.join(d, f))) for f in os.listdir(d) if f.endswith('.json')}


def test_every_planned_figure_is_drawn_and_audited():
    full = runprofile.name() == 'full'
    recs = _records()
    for g, fid, _ in FP.all_figures(profile_full=full):
        path = layout.figure(fid)
        for fmt in runprofile.get('formats'):
            assert os.path.exists(f'{path}.{fmt}'), (fid, fmt)
        assert fid in recs, fid
        assert recs[fid]['source'], fid
    assert os.path.exists(layout.FIGURES_INDEX)
    text = open(layout.FIGURES_INDEX).read()
    assert all(fid in text for _, fid, _ in FP.all_figures(profile_full=True))


def test_figures_leave_the_data_byte_identical():
    """--figures-only: drawing reads data only. A sample of figures from every module is redrawn in process and every
    file of outputs/data is hashed before and after."""
    def hashes():
        out = {}
        for d, _, fs in os.walk(layout.DATA):
            for f in fs:
                p = os.path.join(d, f)
                out[p] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        return out
    import importlib
    before = hashes()
    # one figure of every drawing module (main, Extended Data, Supplementary)
    for fid in ('Fig4_pathways', 'Fig6_shapley_levers', 'ED4_one_at_a_time', 'ED8_lever_annual', 'ED9_rollout_timing',
                'ED10_reality_checks', 'SF1_households', 'SF6_hindcast', 'SF7_completion_lag', 'SF8_prcc', 'SF11_mc_convergence'):
        mod = next(m for _, f, m in FP.all_figures() if f == fid)
        importlib.import_module(mod).FIGURES[fid]()
    assert hashes() == before


# ---------------------------------------------------------------------------
# waterfalls and TL steps
# ---------------------------------------------------------------------------
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
    note = json.load(open(os.path.join(layout.FIGURE_AUDIT, 'Fig4_pathways.json')))['note']      # Fig4
    if ups:
        assert all(s in note for _, s in ups)
    else:
        assert 'Net-positive steps: none' in note


# ---------------------------------------------------------------------------
# band reductions, Fig3b interval, Fig1 line
# ---------------------------------------------------------------------------
def test_fig5_column_totals_are_reference_minus_run():
    from figures import paper_main as PM
    red, tot = PM.reduction_by_band()
    r = pd.read_csv(_data('pathways/runs.csv')).query("scenario == 'REF'").set_index('run')['carbon_kt']
    assert set(tot) == set(PM.REDUCTION_RUNS) == {'pathway-moderate', 'pathway-ambitious', 'TL'}
    for run in PM.REDUCTION_RUNS:
        assert tot[run] == pytest.approx(r['REF'] - r[run], rel=RTOL, abs=1e-9), run
        assert sum(red[run].values()) == pytest.approx(tot[run], rel=RTOL, abs=1e-9), run


def test_fig3_interval_from_the_draws():
    from figures import paper_main as PM
    d = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))['carbon_kt'].to_numpy(float)
    s = pd.read_csv(layout.montecarlo('summary', 'REF', frozen=False)).set_index('output').loc['carbon_kt']
    assert np.percentile(d, 5) == pytest.approx(s['p5'], rel=1e-12)
    assert np.percentile(d, 95) == pytest.approx(s['p95'], rel=1e-12)
    lo, hi = PM.mc_cumulative_interval()
    # the 90% interval, 5th-95th percentile of the draws, equal to the stored summary
    assert PM.FIG3_INTERVAL == (5.0, 95.0)
    assert lo == pytest.approx(s['p5'], rel=1e-12) and hi == pytest.approx(s['p95'], rel=1e-12)


# ---------------------------------------------------------------------------
# ED4 / ED5 notes
# ---------------------------------------------------------------------------
def test_fig1_annual_line_matches_census_interval_means():
    a = pd.read_csv(_data('baseline/annual.csv'))
    h = pd.read_csv(_data('baseline/bands_history.csv'))
    hist = a[a['source'] == 'history'].set_index('year')['floor_area_Mm2']
    proj = a[a['source'] == 'projection'].set_index('year')['floor_area_Mm2']
    iv = h[['year_start', 'year_end', 'observed_built_Mm2_per_year']].drop_duplicates()
    y0 = int(iv['year_start'].min())
    years = list(hist.loc[y0:].index) + list(proj.index)
    assert years == list(range(y0, 2051)) and y0 == 1992
    for _, r in iv.iterrows():
        assert hist.loc[int(r['year_start']):int(r['year_end'])].mean() == pytest.approx(
            r['observed_built_Mm2_per_year'], rel=1e-9)


def test_notes_stop_when_code_and_outputs_disagree(monkeypatch):
    import projection as PR
    from figures import sensitivity as SE
    monkeypatch.setattr(PR, 'COMPLETION_RATE', 0.9)
    with pytest.raises(SystemExit, match='completion rate'):
        SE.ed4_rows()


# ---------------------------------------------------------------------------
# the palette file
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('bad, msg', [('extra_space     = "#DFA538"', 'missing key'),
                                      ('extra_space = "#DFA5"', 'not a "#RRGGBB"'),
                                      ('extra_space = "#DFA538"\nextra_spaces = "#000000"', 'unknown key')])
def test_load_palette_rejects(tmp_path, bad, msg):
    src = open(S.PALETTE_DEFAULT).read()
    line = next(x for x in src.splitlines() if x.startswith('extra_space'))
    txt = src.replace(line, '' if msg == 'missing key' else bad)
    f = tmp_path / 'p.toml'
    f.write_text(txt)
    with pytest.raises(S.PaletteError, match=msg):
        S.load_palette(str(f))


# ---------------------------------------------------------------------------
# palette file and SF2b
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('value', ['1.2', '-0.1', 'true', '"0.5"'])
def test_load_palette_rejects_opacity(tmp_path, value):
    src = open(S.PALETTE_DEFAULT).read()
    line = next(x for x in src.splitlines() if x.startswith('mc_band_90'))
    f = tmp_path / 'p.toml'
    f.write_text(src.replace(line, f'mc_band_90 = {value}'))
    with pytest.raises(S.PaletteError, match='not a number in'):
        S.load_palette(str(f))


@pytest.fixture(scope='module')
def sf2b():
    from figures import calibration as C
    return C.sf2b_columns()


def test_sf2b_up_plus_down_is_net(sf2b):
    from figures import calibration as C
    cols = sf2b['history'] + sf2b['annual']
    assert len(sf2b['history']) == 7 and len(sf2b['annual']) == 25
    for c in cols:
        parts = np.array(list(c['parts'].values()))
        assert c['up'] == pytest.approx(parts[parts > 0].sum(), rel=0, abs=1e-9)
        assert c['down'] == pytest.approx(parts[parts < 0].sum(), rel=0, abs=1e-9)
        assert c['up'] + c['down'] == pytest.approx(c['net'], rel=RTOL, abs=1e-9)
    from figures import data as D
    hist_net = {(r.year_start, r.year_end): r.dwellings_built_per_year
                for r in D.src('D05_stock_and_vacancy')['stock_identity_history'].itertuples()}
    for c in sf2b['history']:                               # the column net is the stock identity of the interval
        assert c['net'] == pytest.approx(hist_net[c['years']], rel=RTOL)
    for c in sf2b['annual']:                                # the line equals the net in every projection year
        assert c['line'] == pytest.approx(c['net'], rel=RTOL)
    # the drawn stacks: every column and year of the drawing helper checks up + down = net (draw._check_net); a
    # column whose parts do not add up to its net stops the figure
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    C.sf2b_draw(ax, sf2b)
    bad = dict(sf2b, history=[dict(sf2b['history'][0], net=sf2b['history'][0]['net'] + 1.0)] + sf2b['history'][1:])
    with pytest.raises(SystemExit):
        C.sf2b_draw(ax, bad)
    plt.close(fig)


def test_sf2b_net_replacement_is_one_band(sf2b):
    """The projection's demolition replacement, recent surge and unconsented additions are one band, Net replacement,
    in every year equal to the sum of the three D05 parts; the history's census-measured net replacement has the same
    label and colour."""
    from figures import calibration as C
    from figures import data as D
    pc = D.src('D05_stock_and_vacancy')['projection_components']
    for k, c in enumerate(sf2b['annual']):
        assert set(c['parts']) == set(C.FUT_IDS)
        assert c['parts']['net_replacement'] == pytest.approx(sum(float(pc[p][k]) for p in C.NET_REPLACEMENT_PARTS),
                                                              rel=1e-12, abs=1e-9)
    assert C.COMP['net_replacement'] == C.COMP['net_replacement_census'] == ('Net replacement',
                                                                              C.S.DISPLAY_BAND['net_replacement'])
    assert not set(C.NET_REPLACEMENT_PARTS) & set(C.SF2B_LEGEND)


def test_ed10_history_lines_equal_their_source():
    """ED10 is an Extended Data item (at most ten); every drawn history line is the source data, unsmoothed."""
    import matplotlib.pyplot as plt
    from figures import data as D
    from figures import validation as V
    ids = [h['id'] for h in FP.PAPER_EXTENDED]
    assert ids[-1] == 'ED10' and len(ids) <= 10
    assert not any(h['file'].endswith('reality_checks') for h in FP.SUPPLEMENTARY)
    fig, ax = plt.subplots()
    d = D.src('D15_reality_checks')
    for key in d['order']:
        hs = d['panels'][key]['history']
        assert V._history_line(ax, hs.index, hs.values) == 0.0
    with pytest.raises(SystemExit):                        # a line that is not its source stops the figure
        V.HISTORY_ATOL, old = -1.0, V.HISTORY_ATOL
        try:
            V._history_line(ax, [1, 2], [1.0, 2.0])
        finally:
            V.HISTORY_ATOL = old
    plt.close(fig)


def test_sf2b_line_means_equal_column_nets(sf2b):
    years, vals = sf2b['line']
    assert years[0] == 1992 and years[-1] == 2050 and np.all(np.diff(years) == 1)
    line = pd.Series(vals, index=years.astype(int))
    for c in sf2b['history']:
        y0, y1 = c['years']
        assert line.loc[y0:y1].mean() == pytest.approx(c['net'], rel=RTOL)
