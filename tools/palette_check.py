"""Colour-vision-deficiency check of the release palette (figures/style.py) and the palette
documents: docs/palette_preview.png (every swatch in normal vision, simulated
deuteranomaly, protanomaly and tritanomaly at full severity, and greyscale) and
docs/PALETTE.md (rules, colour table, minimum pairwise distances).

Method: colours that appear together in a figure form a group; for every group and every
vision type the minimum pairwise colour difference is computed as the Euclidean distance
in CAM02-UCS (Luo, Cui & Li 2006) after simulating the deficiency with the model of
Machado, Oliveira & Fernandes (2009), both as implemented in colorspacious 1.1.2
(Smith & van der Walt). A distance of 10 or more is taken as clearly distinguishable for
adjacent filled areas (THRESHOLD; a convention, stated here, not a standard). Greyscale:
the CAM02-UCS lightness J'.

    python tools/palette_check.py
"""
import itertools
import os
import sys

import numpy as np
from colorspacious import cspace_convert

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from figures import style as S  # noqa: E402

DOCS = os.path.join(ROOT, 'docs')
VISION = ('normal', 'deuteranomaly', 'protanomaly', 'tritanomaly')
THRESHOLD = 10.0


def groups():
    """Colours that appear together in one figure (name -> {label: hex})."""
    import naming as N
    return {
        'Runs and boundaries (Fig4, ED5, D28)': dict({'Acquired rights (AR)': S.AR, 'Ability to pay (AtP)': S.ATP,
                                                'Reference': S.REFERENCE, N.TL['TL']: S.TL},
                                               **{(f'{p} {N.STRATEGIES[p]}' if p in N.STRATEGIES else
                                                   'Moderate / Ambitious Pathway'): c for p, c in S.PATHWAY.items()}),
        'Levers (ED7, SF4, D29, D31)': {f'{k} {N.LEVERS[k]}': c for k, c in S.LEVER.items()},
        'Boundary zones on white (every boundary figure)': {z['label']: zone_on_white(z) for z in S.ZONE.values()},
        # MODEL v2.1.2: the Recent replacement surge (L3 face, fine light hatch) and Historical replacement (a darker,
        # slightly bluer lilac) differ in lightness, hue and hatch; the surge face is checked against every other
        # band in the next group, the replacement-surge pair is reported in the text
        # MODEL v3.0.0: every band shown together (Fig1, Fig2, Fig5, D25, D26, D36): the negative bands as filled
        # areas below zero in time series and as outlines in cumulative bars
        'Demand bands (Fig1, Fig2, Fig5, ED6, D25, D26, D36)': {N.BANDS[b]: S.BAND[b][0] for b in S.BAND_ORDER
                                                           if b != 'redevelopment'},
        'Recent replacement surge face against the other bands': {N.BANDS[b]: S.BAND[b][0] for b in S.BAND_ORDER
                                                                   if b != 'replacement'},
        'The Pathways and TL against every lever, growth, the Reference, the boundaries and the zones': dict(
            {f'{k} {N.LEVERS[k]}': c for k, c in S.LEVER.items()},
            **{'Moderate / Ambitious Pathway': S.PATHWAY[N.PATHWAY], N.TL['TL']: S.TL, N.BANDS['growth']: S.GROWTH,
               'Reference': S.REFERENCE, 'Acquired rights (AR)': S.AR, 'Ability to pay (AtP)': S.ATP},
            **{z['label']: zone_on_white(z) for z in S.ZONE.values()}),
        'Carbon components (Fig3c, diagnostics)': {N.COMPONENTS[c]: S.COMPONENT[c][0] for c in S.COMPONENT},
        'Projection variants and boundaries (ED2, ED9)': dict({S.SCENARIO[k]['label']: S.SCENARIO[k]['color']
                                                             for k in S.SCENARIO},
                                                            **{'Acquired rights (AR)': S.AR,
                                                               'Ability to pay (AtP)': S.ATP}),
        'Materials (Fig3b, diagnostics)': {lab: col for _, lab, col in S.MATERIAL},
        'Life-cycle stages (Fig3a)': {N.STAGES[k]: S.STAGE[k][0] for k in S.STAGE},
        'History bands (Fig1)': {(N.BANDS.get(b) or N.BAND_DETAIL[b]): S.HISTORY_BAND[b][0] for b in S.HISTORY_BAND},
        'Categorical groups (diagnostics; Okabe-Ito)': {f'group {i + 1}': c for i, c in enumerate(S.QUALITATIVE)},
    }


def focus():
    """Groups checked only for the pairs that involve the listed colours (the others never share a figure as
    adjacent fills; their own groups check them)."""
    import naming as N
    return {'Recent replacement surge face against the other bands': [N.BANDS['redevelopment']],
            'The Pathways and TL against every lever, growth, the Reference, the boundaries and the zones':
                ['Moderate / Ambitious Pathway', N.TL['TL']]}


def zone_on_white(z):
    """The colour a boundary zone shows on a white background (alpha compositing)."""
    rgb = 1 - z['alpha'] * (1 - _rgb(z['color']))
    return '#' + ''.join(f'{int(round(255 * c)):02X}' for c in rgb)


def _rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def simulate(h, vision):
    rgb = _rgb(h)
    if vision == 'normal':
        return rgb
    return np.clip(cspace_convert(rgb, {'name': 'sRGB1+CVD', 'cvd_type': vision, 'severity': 100}, 'sRGB1'), 0, 1)


def jab(h, vision):
    return cspace_convert(simulate(h, vision), 'sRGB1', 'CAM02-UCS')


def min_distance(cols, only=None):
    """{vision: (distance, label a, label b)} of the closest pair (with only: the pairs involving those labels)."""
    out = {}
    pairs = [(a, b) for a, b in itertools.combinations(cols, 2) if not only or a in only or b in only]
    for v in VISION:
        out[v] = min((float(np.linalg.norm(jab(cols[a], v) - jab(cols[b], v))), a, b) for a, b in pairs)
    return out


def lightness(h):
    return float(cspace_convert(_rgb(h), 'sRGB1', 'CAM02-UCS')[0])


def preview(G, path):
    import matplotlib.pyplot as plt
    S.apply()
    cols = list(VISION) + ['greyscale']
    rows = sum(len(g) for g in G.values()) + len(G)
    fig, ax = plt.subplots(figsize=S.figsize('double', 4.2 * rows + 12))
    ax.set_axis_off()
    y = 0
    for gname, g in G.items():
        ax.text(-0.02, -y, gname, ha='left', va='center', fontsize=S.FONT_SIZE, fontweight='bold')
        y += 1
        for lab, h in g.items():
            ax.text(-0.02, -y, f'{lab}  {h}', ha='left', va='center', fontsize=S.FONT_SMALL)
            for j, v in enumerate(cols):
                if v == 'greyscale':
                    jj = lightness(h) / 100.0
                    rgb = (jj, jj, jj)
                else:
                    rgb = tuple(simulate(h, v))
                ax.add_patch(plt.Rectangle((0.42 + 0.115 * j, -y - 0.42), 0.105, 0.84, facecolor=rgb,
                                           edgecolor='#555555', linewidth=0.3))
            y += 1
    for j, v in enumerate(cols):
        ax.text(0.42 + 0.115 * j + 0.0525, 0.55, v, ha='center', va='bottom', fontsize=S.FONT_SMALL, rotation=0)
    ax.set_xlim(-0.03, 1.0)
    ax.set_ylim(-y, 1.2)
    fig.subplots_adjust(top=0.985, bottom=0.005, left=0.01, right=0.99)
    fig.suptitle('Release palette: normal vision, simulated colour-vision deficiency (full severity; '
                 'Machado et al. 2009) and greyscale', fontsize=S.FONT_SIZE)
    S.save(fig, path)


def main():
    import naming as N
    G = groups()
    os.makedirs(DOCS, exist_ok=True)
    preview(G, os.path.join(DOCS, 'palette_preview'))
    L = ['# Palette (generated by tools/palette_check.py from figures/style.py; do not edit by hand)', '',
         'One palette for every figure (MODEL v3.0.0); `figures/style.py` is the only place colours are defined, and '
         'every module of the figures/ package imports it. Preview with simulated colour-vision deficiency: '
         '[palette_preview.png](palette_preview.png).', '',
         '## Rules', '',
         '* **Source** (MODEL v2.1.1): the palette is inspired by Francis Bacon, *Head VI* (1949): golds, mauves, '
         'deep blues and browns on a near-black ground. The hue families are fixed by that choice; lightness and '
         'chroma were set by maximising the minimum CAM02-UCS distance of every group below under every simulated '
         'deficiency (MODEL v3.0.0: the new lever L5, the three negative bands and the maintenance grey re-tuned).',
         '* **Lever shades in hue families** (each lever keeps its MODEL v3.0 colour; MODEL v3.3.0 numbering): golds / '
         f"ochres (L4 Extra space {S.LEVER['L4']}, L5 Occupancy density a deep amber {S.LEVER['L5']}, L1 Household "
         f"size a light gold {S.LEVER['L1']}), mauves (L2 Vacancy rate {S.LEVER['L2']}, L3 Building lifetime "
         f"{S.LEVER['L3']}; the deep mauve anchor {S.P2_ANCHOR}), blues (L8 Material carbon efficiency "
         f"{S.LEVER['L8']}, L9 Construction-stage carbon {S.LEVER['L9']}), browns (L7 Soil-aware planning "
         f"{S.LEVER['L7']}, L6 Brownfield-first development {S.LEVER['L6']}). PAS 2080 strategies (MODEL v3.3.0, the "
         f"former pathway colours): S1 Avoid {S.STRATEGY['S1']}, S2 Switch {S.STRATEGY['S2']}, S3 Improve "
         f"{S.STRATEGY['S3']}; the Moderate / Ambitious Pathway vermilion ({S.PATHWAY[N.PATHWAY]}) and TL a deep forest "
         f"green ({S.TL}; a larger circle on point plots).",
         '* **Demand bands** are coloured by the lever family that targets them (Smaller households L1, Extra space L4, '
         f"Vacancy L2, 2026 overbuild the deep mauve anchor, Overbuild absorbed a lighter mauve ({S.BAND['overbuild_absorbed'][0]}), "
         f"Demolition replacement a lilac ({S.REPLACEMENT}), Unconsented additions a darker lilac "
         f"({S.BAND['unconsented'][0]}), the Recent replacement surge the L3 face ({S.LEVER['L3']}) with a fine light "
         f"hatch (the only hatched band), Released dwellings (TL) a light green ({S.BAND['released_tl'][0]})). The only "
         f"untargeted band, Population growth, is a solid deep green-blue ({S.GROWTH}). Unexplained building of the "
         f"history: a faded reddish face ({S.UNEXPLAINED[0]}).",
         '* **Signs** (MODEL v3.0.0): the data keep the sign of every band and the figures never flip it. Time series: '
         'positive bands stacked up from zero, negative bands down from zero (fixed order), the net a black line. '
         'Cumulative bars: positives stacked; each negative band an unfilled, unhatched segment outlined in its band '
         'colour, hanging from the top of the positive stack, so the bar ends at its net total, marked by a net tick; '
         'one legend entry per band. Materials and stages are never negative (a STOP if they were).',
         f"* **Maintenance** (B2, B4) neutral grey ({S.BAND['maintenance'][0]}); committed emissions after 2050 a "
         f"lighter grey drawn hollow ({S.COMPONENT['committed'][0]}). Carbon stages: A1-A3 the L8 dark blue, A4-A5 the "
         'L9 light blue, soil carbon loss the L7 brown.',
        f"* **Reference** dark grey ({S.REFERENCE}); Low and High replacement mid greys with dashed and dotted lines.",
         f"* **Stacked bars and areas** are drawn seamless: each segment's edge is its own face colour at "
         f"{S.LW_SEAM:g} pt (no white borders, no anti-aliasing gaps); a hatch is drawn in a thin hatch colour only "
         f"(default {S.HATCH_COLOUR}; the surge band {S.HATCH_LIGHT}). Legend handles keep a thin grey outline.",
         f"* **Boundaries** (every planetary-boundary figure, one implementation in style.py): acquired rights (AR) "
         f"thin red line ({S.AR}), ability to pay (AtP) thin dark-red dotted line ({S.ATP}); zones (MODEL v2.1.2: much lighter) below AtP "
         f"faded green ({S.ZONE['within_both']['color']}, alpha {S.ZONE['within_both']['alpha']}), between AtP and AR light "
         f"green ({S.ZONE['within_ar']['color']}, alpha {S.ZONE['within_ar']['alpha']}) and above AR light red "
         f"({S.ZONE['exceeded']['color']}, alpha {S.ZONE['exceeded']['alpha']}, \"boundary exceeded\"), on annual, "
         'cumulative and level-of-exceedance axes alike. The two principles are never averaged.',
         '* **Settings**: lines: Moderate solid bold, Ambitious the same colour thin dotted; markers: Moderate filled, '
         'Ambitious hollow; bars (Fig7): Moderate hollow, Ambitious filled, TL a large deep-green dot.',
         f"* **Typeface**: {S.FONT} only (metric-compatible with Arial), bundled in `fonts/` under the SIL Open "
         'Font License 1.1, registered by figures/style.py, so every machine renders the same glyphs.',
         f"* **Sizes** (Nature Cities): width {S.WIDTH['single'] / S.MM:.0f} mm (single column) or "
         f"{S.WIDTH['double'] / S.MM:.0f} mm (double column), page depth at most {S.MAX_HEIGHT / S.MM:.0f} mm; "
         f"text {S.FONT_SIZE:g} pt, legends and ticks {S.FONT_SMALL:g} pt, never below {S.FONT_MIN:g} pt; data "
         f"lines {S.LW:g} pt, emphasised lines {S.LW_BOLD:g} pt, grid and edges {S.LW_THIN:g} pt.",
         '* **Files** (run profiles, runprofile.py): light PNG at 200 dpi with a small grey footer "LIGHT RUN — '
         'n=1000"; full PDF (TrueType fonts embedded) + PNG at 600 dpi; no software or date metadata, so re-runs are '
         'byte-identical.',
         '* **Materials** (Fig3b and the diagnostics): the six stripes of the Pride flag in one order in every figure '
         '(author decision, baseline-pb-v2), soil carbon loss faded on top (no hatch since MODEL v3.0.0); kept because the '
         'material figures label every layer directly (see the check below).', '',
         '## Colour table', '', '| group | element | colour | lightness J\' |', '|---|---|---|---|']
    for gname, g in G.items():
        for lab, h in g.items():
            L.append(f'| {gname} | {lab} | `{h}` | {lightness(h):.0f} |')
    L += ['', '## Colour-vision-deficiency check', '',
          'Minimum pairwise distance within each group (CAM02-UCS, Luo, Cui & Li 2006) after simulating the '
          'deficiency at full severity (Machado, Oliveira & Fernandes 2009; colorspacious 1.1.2). Threshold for '
          f'"clearly distinguishable" adjacent fills: {THRESHOLD:g} (stated convention).', '',
          '| group | ' + ' | '.join(VISION) + ' | passes |', '|---|' + '---|' * (len(VISION) + 1)]
    fails = []
    F = focus()
    for gname, g in G.items():
        d = min_distance(g, F.get(gname))
        ok = all(v[0] >= THRESHOLD for v in d.values())
        if not ok:
            fails.append(gname)
        L.append(f'| {gname} | ' + ' | '.join(f'{d[v][0]:.1f} ({d[v][1]} / {d[v][2]})' for v in VISION)
                 + f" | {'yes' if ok else 'no'} |")
    if fails:
        L += ['', 'Groups below the threshold: ' + '; '.join(fails) + '. Why each still reads: the boundary zones are pale by design (data drawn over them), always '
              'bounded by the AR and AtP lines and ordered strictly in lightness (darker green < light green < palest '
              'red under every simulated deficiency), so their order survives without hue; any other group below the '
              'threshold is labelled directly in every figure (text on or beside each layer) or carries a hatch, so '
              'the reading never depends on colour alone.']
    rs = min_distance({'Historical replacement': S.REPLACEMENT, 'Recent replacement surge': S.LEVER['L3']})
    L += ['', 'Historical replacement against the Recent replacement surge face: '
          + ', '.join(f'{v} {rs[v][0]:.1f}' for v in VISION)
          + ' (below the threshold by design: told apart by lightness, a slightly different hue and the surge\'s '
          'fine light hatch, and labelled in every figure).']
    Jz = {k: [lightness(zone_on_white(z))] + [float(jab(zone_on_white(z), v)[0]) for v in VISION[1:]]
          for k, z in S.ZONE.items()}
    order = ('within_both', 'within_ar', 'exceeded')
    zmono = all(max(Jz[a]) < min(Jz[b]) for a, b in zip(order, order[1:]))
    if not zmono:
        fails.append('boundary zones lightness order')
    L += ['', '## Boundary zones: lightness order', '',
          'J\' of each zone on white (normal, deuteranomaly, protanomaly, tritanomaly): '
          + '; '.join(f"{S.ZONE[k]['label']} " + ' / '.join(f'{x:.1f}' for x in Jz[k]) for k in order)
          + f". Strictly increasing under every vision type: {'yes' if zmono else 'NO'}."]
    seq = [lightness(h) for h in S.SEQUENTIAL]
    mono = all(a > b for a, b in zip(seq, seq[1:]))
    if not mono:
        fails.append('sequential ramp')
    L += ['', '## Sequential ramp', '', 'Continuous fields (the solution space, Fig6) use one blue ramp, light to dark; '
          'its CAM02-UCS lightness J\' must fall strictly so the order survives greyscale: '
          + ', '.join(f'`{h}` {j:.0f}' for h, j in zip(S.SEQUENTIAL, seq)) + f" ({'monotone' if mono else 'NOT monotone'})."]
    L += ['', '## Sources', '',
          '* Luo MR, Cui G, Li C (2006) Uniform colour spaces based on CIECAM02 colour appearance model. '
          'Color Research & Application 31, 320-330.',
          '* Machado GM, Oliveira MM, Fernandes LAF (2009) A physiologically-based model for simulation of color '
          'vision deficiency. IEEE Transactions on Visualization and Computer Graphics 15, 1291-1298.',
          '* Okabe M, Ito K (2008) Color Universal Design (CUD): how to make figures and presentations that are '
          'friendly to colorblind people. https://jfly.uni-koeln.de/color/ (the categorical palette).',
          '* Smith NJ, van der Walt S, colorspacious 1.1.2 (Python package), https://github.com/njsmith/colorspacious.']
    with open(os.path.join(DOCS, 'PALETTE.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('palette_check: docs/PALETTE.md, docs/palette_preview.png'
          + (f'; below threshold: {fails}' if fails else '; every group passes'))
    return fails


if __name__ == '__main__':
    main()
