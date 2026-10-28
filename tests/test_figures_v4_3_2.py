"""MODEL v4.3.2 tests (docs/CHANGELOG_v4_3_2.md): figure and palette changes only, from the committed outputs.

  * Fig1: the annual floor area built is one series 1992-2050 and its mean over every census interval equals the
    interval's observed floor area built (the identity the figure asserts before drawing the caps);
  * Fig3: no annual-value markers on the PCHIP lines; the 2026-2050 column in palette.toml [cumulative];
  * Fig7b: the Moderate Pathway on the paired draws, in its run colour, below the Ambitious Pathway and TL;
  * ED4 / ED5: the display-drop lists (the data files keep the rows; an unmapped row still stops); one row note per
    shown row, equal to the text copied into figure_plan (ED4_ROW_NOTES, ED5_ROW_NOTES) and the captions;
  * ED8: no strategy squares; SF10: each lever in its strategy colour, told apart by marker within its strategy;
  * the zone lightness-order check of tools/palette_check.py holds for the default palette and fails when broken."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT
import figure_plan as FP
import layout
import naming as N
from figures import style as S

sys.path.insert(0, os.path.join(ROOT, 'tools'))


def _data(rel):
    return layout.data(rel, frozen=False)


@pytest.fixture
def capture(monkeypatch):
    """Draw a figure without saving it: returns {name: (figure, note)}."""
    import matplotlib.pyplot as plt
    got = {}

    def fake(fig, name, note=None, source=None):
        got[name] = (fig, note)
    monkeypatch.setattr(S, 'save_figure', fake)
    yield got
    plt.close('all')


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


def test_fig1_draws_one_annual_line(capture):
    from figures import paper_main as PM
    from figures import draw as P
    PM.fig1()
    fig, note = capture['Fig1_floor_area']
    ax = fig.axes[0]
    net = [ln for ln in ax.get_lines() if ln.get_gid() == P.NET_GID]
    assert len(net) == 1
    x = net[0].get_xdata()
    assert x[0] == 1992 and x[-1] == 2050 and np.all(np.diff(x) == 1)
    caps = [ln for ln in ax.get_lines() if ln.get_gid() == 'census_interval_mean']
    assert len(caps) == pd.read_csv(_data('baseline/bands_history.csv'))['interval'].nunique()
    assert all(ln.get_color() == S.MUTED for ln in caps)


def test_fig3_no_annual_markers_and_cumulative_colour(capture):
    from matplotlib.colors import to_hex
    from figures import paper_main as PM
    PM.fig3()
    fig, note = capture['Fig3_reference_boundaries']
    a, b = fig.axes[:2]
    assert not [ln for ln in a.get_lines() if ln.get_marker() not in (None, 'None', '', ' ')]
    assert '(dots)' not in note and 'through the annual values' in note
    assert to_hex(b.patches[0].get_facecolor()).upper() == S.CUMULATIVE_FIG3B.upper()


def test_fig7b_moderate_pathway(capture):
    from matplotlib.colors import to_hex
    from figures import paper_main as PM
    PM.fig7()
    fig, note = capture['Fig7_uncertainty']
    b = fig.axes[1]
    labs = [c.get_label() for c in b.collections]
    mod = [c for c in b.collections if c.get_label().startswith(N.PATHWAY_RUNS['pathway-moderate'])]
    amb = [c for c in b.collections if c.get_label().startswith(N.PATHWAY_RUNS['pathway-ambitious'])]
    tl = [c for c in b.collections if c.get_label().startswith(N.TL['TL'] + ':')]
    assert len(mod) == len(amb) == len(tl) == 1, labs
    assert to_hex(mod[0].get_facecolor()[0], keep_alpha=False).upper() == S.PATHWAY_SETTING['moderate'].upper()
    assert mod[0].get_zorder() < amb[0].get_zorder() < tl[0].get_zorder()
    d = pd.read_csv(_data('pathways/montecarlo_draws.csv'))
    k = int((d['pathway_moderate_LoE_AR'] <= 1.0).sum())
    assert f'({k:,} of {len(d):,})' in mod[0].get_label()
    assert 'pathway_moderate' in note and 'Wilson' in note
    from matplotlib.text import Text
    assert any(t.get_text() == 'Reference, the Pathways and the Theoretical Limit vs the 2050 population'
               for t in fig.findobj(Text))


def test_ed4_drop_list_and_notes():
    from figures import sensitivity as SE
    r, c0, order, lines = SE.ed4_rows()
    assert set(SE.REF_NOT_SHOWN) <= set(r['row'])                 # the data file stays complete
    shown = [item['id'] for kind, item in order if kind == 'row']
    for rid in ('hh_after2043_flat', 'overbuild_gap', 'uc_correction', 'event_timing'):
        assert rid not in shown
    headers = [item for kind, item in order if kind == 'header']
    assert 'Accounting' not in headers
    assert all(any(kind == 'row' and item['group'] == h for kind, item in order) for h in headers)   # none empty
    assert len(lines) == len(shown) and tuple(lines) == FP.ED4_ROW_NOTES
    ed4 = next(h for h in FP.PAPER_EXTENDED if h['id'] == 'ED4')
    assert ed4['caption'].endswith(' '.join(FP.ED4_ROW_NOTES))
    for ln in lines:
        assert ' instead of ' in ln or ln.startswith(('Replacement',)), ln


def test_ed5_drop_list_and_notes(monkeypatch):
    from figures import data as D
    from figures import sensitivity as SE
    r, st, c, orders, lines = SE.ed5_rows()
    assert set(SE.PB_DROPPED) <= set(r['row'])
    for q in orders:
        shown = [item['id'] for kind, item in orders[q] if kind == 'row']
        assert 'alpha_1' not in shown and 'pop_source_raw' not in shown
    assert tuple(lines) == FP.ED5_ROW_NOTES
    ed5 = next(h for h in FP.PAPER_EXTENDED if h['id'] == 'ED5')
    assert ed5['caption'].endswith(' '.join(FP.ED5_ROW_NOTES))
    real = D.csv

    def extra(rel):                                               # an unknown row must still stop the figure
        t = real(rel)
        if rel == 'sensitivity/planetary_boundary.csv':
            t = pd.concat([t, t.iloc[[0]].assign(row='An unmapped row')], ignore_index=True)
        return t
    monkeypatch.setattr(D, 'csv', extra)
    with pytest.raises(SystemExit, match='rows without a display name'):
        SE.ed5_rows()


def test_notes_stop_when_code_and_outputs_disagree(monkeypatch):
    import projection as PR
    from figures import sensitivity as SE
    monkeypatch.setattr(PR, 'COMPLETION_RATE', 0.9)
    with pytest.raises(SystemExit, match='completion rate'):
        SE.ed4_rows()


def test_ed8_no_strategy_squares(capture):
    from matplotlib.patches import Rectangle
    from figures import pathways as PW
    PW.ed8_lever_annual()
    fig, _ = capture['ED8_lever_annual']
    for a in fig.axes:
        assert not [p for p in a.patches if isinstance(p, Rectangle) and not p.get_clip_on()]


def test_sf10_strategy_colours_and_markers(capture):
    from matplotlib.colors import to_hex
    from figures import paper_extended as PE
    import levers as LV
    PE.sf3()
    fig, _ = capture['SF10_lambda_sweep']
    ax = fig.axes[0]
    for L in LV.LEVERS:
        ln = [x for x in ax.get_lines() if x.get_label() == f'{L} {N.LEVERS[L]}']
        assert len(ln) == 1, L
        sid = N.LEVER_STRATEGY[L]
        assert to_hex(ln[0].get_color()).upper() == S.STRATEGY[sid].upper()
        assert ln[0].get_marker() == S.LEVER_MARKER[N.STRATEGY_LEVERS[sid].index(L)]
    assert max(len(v) for v in N.STRATEGY_LEVERS.values()) <= len(S.LEVER_MARKER)


def test_zone_lightness_order():
    import palette_check as PC
    ok, J = PC.zone_lightness_order(S)
    assert ok
    broken = type('Z', (), {'ZONE': dict(S.ZONE, within_ar=dict(S.ZONE['within_ar'], color='#0050FF'))})
    assert not PC.zone_lightness_order(broken)[0]
