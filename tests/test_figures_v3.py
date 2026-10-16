"""MODEL v3.0.0 figures: compute / draw separation, the sign rules, the palette registry and the figure audit of the
active run profile."""
import hashlib
import json
import os
import re

import numpy as np
import pytest

from conftest import ROOT
import figure_plan as FP
import layout
import runprofile
from figures import draw as P
from figures import style as S

MODEL_SCRIPTS = ('projection.py', 'Diagnostics.py', 'boundaries.py', 'MonteCarlo.py', 'pathways.py', 'pathways_mc.py',
                 'tools/figures_report.py', 'engine.py', 'levers.py')


@pytest.mark.parametrize('script', MODEL_SCRIPTS)
def test_model_scripts_do_not_plot(script):
    src = open(os.path.join(ROOT, script)).read()
    assert not re.search(r'^\s*(import|from)\s+(matplotlib|figures|style|plotting)\b', src, re.M), script
    assert 'savefig' not in src and 'plt.' not in src, script


# ------------------------------------------------------------------ palette ----
def test_palette_registry_has_no_duplicates():
    for group, items in S.registry().items():
        seen = {}
        for k, v in items.items():
            assert v not in seen, f'{group}: {k} duplicates {seen.get(v)} {v}'
            seen[v] = k


def test_only_the_surge_is_hatched():
    assert [b for b, (_, h) in S.BAND.items() if h] == ['redevelopment']
    assert all(h is None for _, h in S.STAGE.values()) and all(h is None for _, h in S.COMPONENT.values())


def test_boundary_styles():
    assert S.BOUNDARY['AR']['ls'] == '-' and S.BOUNDARY['AtP']['ls'] == S.ATP_LS and S.ATP_LS[1][0] <= 1.0
    assert set(S.NEGATIVE_BANDS) == {'overbuild_absorbed', 'unconsented', 'vacancy_released', 'released_tl'}


# ------------------------------------------------------------------ sign rules ----
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


# ------------------------------------------------------------------ audit of the drawn figures ----
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


def test_audit_sign_and_boundary_rules():
    recs = _records()
    assert not {k: r['negative_bar_segments_filled'] for k, r in recs.items() if r.get('negative_bar_segments_filled')}
    assert not {k: r['band_rectangles_below_zero'] for k, r in recs.items() if r.get('band_rectangles_below_zero')}
    assert not {k: r['white_segment_edges'] for k, r in recs.items() if r.get('white_segment_edges')}
    for fid in FP.PB_FIGURES:
        r = recs[fid]
        # a budget level outside the plotted range may be stated on the figure instead (audit.BOUNDARY_OUTSIDE)
        assert (r['boundary_drawn'] and r['boundary_zones']) or r.get('boundary_outside'), fid
        assert set(r['atp_linestyles']) <= {'dotted'}, (fid, r['atp_linestyles'])
    bad = [k for k, r in recs.items() if r['maintenance_drawn'] and k not in FP.MAINTENANCE_ALLOWED
           ]
    assert not bad, bad


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
    for fid in ('Fig5_waterfall', 'Fig7_shapley_levers', 'SF3_lambda_sweep', 'D28_pathways_annual', 'D10_floor_area_bridge',
                'D25_annual_carbon_by_band', 'D01_population', 'D37_mc_convergence', 'D16_one_at_a_time'):
        mod = next(m for _, f, m in FP.all_figures() if f == fid)
        importlib.import_module(mod).FIGURES[fid]()
    assert hashes() == before
