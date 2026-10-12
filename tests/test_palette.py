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
    d = PC.min_distance(cols)
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
    assert S.BAND['growth'] == (S.GROWTH, None)
    assert S.BAND['redevelopment'][0] == S.BAND['replacement'][0] and S.BAND['redevelopment'][1]
    assert S.BAND_HATCHCOLOR['redevelopment'] == S.HATCH_LIGHT
    assert S.BAND['overbuild_2026'][0] == S.LEVER['L4'] and S.BAND['vacancy'][0] == S.LEVER['L3']


def test_p5_and_tl_outside_every_family():
    fam = set(S.LEVER.values()) | {S.GROWTH, S.REFERENCE}
    assert S.PATHWAY['P5'] not in fam and S.TL not in fam and S.TL != S.PATHWAY['P5']
    assert PC.lightness(S.TL) > 30, 'TL must not be black'


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
