"""Palette and rendering rules of MODEL v2.1.1 (style.py, tools/palette_check.py, figaudit.py).

1. Colour-vision deficiency: every group of colours shown together keeps a minimum pairwise CAM02-UCS distance of
   palette_check.THRESHOLD under normal vision and simulated deuteranomaly, protanomaly and tritanomaly (Machado et
   al. 2009, full severity). The one documented exception is the boundary zones, unchanged since MODEL v2.1.0 and
   pale by design: their lightness order must hold under every vision type instead.
2. Semantics of the palette: the pathway families keep their tone order (P2: overbuild darker than vacancy, darker
   than replacement; P3 and P4: the first lever darker than the second); the surge band is the replacement face with
   a light hatch; Population growth is solid; P5 and TL are not black and not a lever colour.
3. Seamless stacks: style.fill draws each segment's edge in its own face colour at LW_SEAM; no figure of the release
   draws a white border between filled segments (figaudit.white_edges, recorded per figure).
"""
import json
import os
import sys

import pytest

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layout as L  # noqa: E402
import palette_check as PC  # noqa: E402
import style as S  # noqa: E402

ZONES = 'Boundary zones on white (every boundary figure)'


@pytest.mark.parametrize('group', [g for g in PC.groups() if g != ZONES])
def test_every_group_passes_the_cvd_check(group):
    cols = PC.groups()[group]
    d = PC.min_distance(cols, PC.focus().get(group))
    low = {v: x for v, x in d.items() if x[0] < PC.THRESHOLD}
    assert not low, (group, low)


def test_boundary_zones_keep_their_lightness_order():
    order = ('within_both', 'within_ar', 'exceeded')
    J = {k: [PC.lightness(PC.zone_on_white(S.ZONE[k]))]
         + [float(PC.jab(PC.zone_on_white(S.ZONE[k]), v)[0]) for v in PC.VISION[1:]] for k in order}
    assert all(max(J[a]) < min(J[b]) for a, b in zip(order, order[1:])), J


def test_family_tone_order():
    lt = PC.lightness
    assert lt(S.LEVER['L4']) < lt(S.LEVER['L3']) < lt(S.LEVER['L5'])      # overbuild < vacancy < replacement
    assert lt(S.LEVER['L6']) < lt(S.LEVER['L7']) and lt(S.LEVER['L8']) < lt(S.LEVER['L9'])
    assert lt(S.LEVER['L1']) < lt(S.LEVER['L2'])
    assert lt(S.COMPONENT['maintenance'][0]) < lt(S.COMPONENT['committed'][0])
    assert S.STAGE['a1a3'][0] == S.LEVER['L6'] and S.STAGE['a4a5'][0] == S.LEVER['L7']
    assert S.STAGE['soil'][0] == S.LEVER['L8']


def test_band_semantics():
    from colorspacious import cspace_convert
    assert S.BAND['growth'] == (S.GROWTH, None)
    # MODEL v2.1.2: Historical replacement darker than the surge face and of a slightly different hue; surge hatched
    assert S.BAND['redevelopment'][0] == S.LEVER['L5'] and S.BAND['redevelopment'][1]
    assert S.BAND['replacement'][0] == S.REPLACEMENT and PC.lightness(S.REPLACEMENT) < PC.lightness(S.LEVER['L5'])
    h = lambda c: cspace_convert(PC._rgb(c), 'sRGB1', 'JCh')[2]
    assert 5 < abs(h(S.REPLACEMENT) - h(S.LEVER['L5'])) < 40
    # lighter, same hue as model-v2.1.1 (210.7 deg; 3 deg allows the 8-bit rounding of a low-chroma colour)
    assert PC.lightness(S.GROWTH) > 40 and abs(h(S.GROWTH) - 210.7) < 3
    assert S.UNEXPLAINED[1] is None
    assert S.BAND_HATCHCOLOR['redevelopment'] == S.HATCH_LIGHT
    assert S.BAND['overbuild_2026'][0] == S.LEVER['L4'] and S.BAND['vacancy'][0] == S.LEVER['L3']


def test_p5_and_tl_outside_every_family():
    fam = set(S.LEVER.values()) | {S.GROWTH, S.REFERENCE}
    assert S.PATHWAY['P5'] not in fam and S.TL not in fam and S.TL != S.PATHWAY['P5']
    from colorspacious import cspace_convert
    J, C, hue = cspace_convert(PC._rgb(S.TL), 'sRGB1', 'JCh')
    assert 125 < hue < 165 and C > 20, 'TL: a forest green'
    zones = [PC.lightness(PC.zone_on_white(z)) for z in S.ZONE.values()]
    assert PC.lightness(S.TL) < min(zones) - 40, 'TL clearly darker than the boundary zones'
    assert S.TL_MARKER['marker'] == 'o'


def test_atp_dotted_and_zones_light():
    assert S.BOUNDARY['AtP']['ls'] == S.ATP_LS and S.ATP_LS[1][0] <= 1.0      # dots, not dashes
    on = {k: PC.lightness(PC.zone_on_white(z)) for k, z in S.ZONE.items()}
    assert on['within_both'] < on['within_ar'] < on['exceeded'] and on['within_both'] > 85


def test_fill_is_seamless():
    kw = S.fill('#123456', hatch='///')
    assert kw['facecolor'] == kw['edgecolor'] == '#123456'
    assert kw['linewidth'] == S.LW_SEAM and kw['hatch'] == '///' and kw['hatchcolor'] == S.HATCH_COLOUR


def test_no_white_borders_between_filled_segments():
    recs = [json.load(open(os.path.join(L.FIGURE_AUDIT, f))) for f in sorted(os.listdir(L.FIGURE_AUDIT))]
    assert recs
    missing = [r['figure'] for r in recs if 'white_segment_edges' not in r]
    assert not missing, missing
    bad = {r['figure']: r['white_segment_edges'] for r in recs if r['white_segment_edges']}
    assert not bad, bad


def _records():
    return [json.load(open(os.path.join(L.FIGURE_AUDIT, f))) for f in sorted(os.listdir(L.FIGURE_AUDIT))]


def test_atp_dotted_in_every_boundary_figure():
    """MODEL v2.1.2: every AtP boundary line is dotted (figaudit.styling)."""
    import figure_plan as FP
    recs = {r['figure']: r for r in _records()}
    for f in FP.PB_FIGURES:
        assert 'atp_linestyles' in recs[f], f
        assert set(recs[f]['atp_linestyles']) <= {'dotted'}, (f, recs[f]['atp_linestyles'])
    bad = {r['figure']: r['atp_linestyles'] for r in recs.values() if set(r.get('atp_linestyles', [])) - {'dotted'}}
    assert not bad, bad


def test_net_total_convention_for_negative_bands():
    """No band segment drawn down from zero (the old convention); a figure with negative bar segments marks the net
    totals with ticks (area figures have no tick: the stack is the total)."""
    recs = _records()
    down = {r['figure']: r['band_rectangles_below_zero'] for r in recs if r.get('band_rectangles_below_zero')}
    assert not down, down
    area_only = {'D25_annual_carbon_by_band', 'D26_cumulative_carbon_by_band'}
    no_tick = [r['figure'] for r in recs if r.get('negative_band_segments') and not r.get('net_total_ticks')
               and r['figure'] not in area_only]
    assert not no_tick, no_tick


def test_tl_colour_and_no_retired_colours():
    recs = {r['figure']: r for r in _records()}
    for f in ('Fig6_emissions_solution_space', 'K3_annual_emissions', 'K4_solution_space', 'D34_tl_dwellings',
              'ED7_rollout_timing', 'ED8_theoretical_limit'):
        assert recs[f]['tl_colour_used'], f
    old = {f: r['retired_colours'] for f, r in recs.items() if r.get('retired_colours')}
    assert not old, old
