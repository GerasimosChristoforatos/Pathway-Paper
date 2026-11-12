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
PREVIEW_DPI = 100                 # docs/palette_preview.png: a reference image, not a print figure
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
        # a lever is drawn in its strategy colour (SF9, told apart by
        # marker), so the strategies are the lever group
        'Strategies (Fig4-Fig6, SF9)': {N.STRATEGIES[k]: c for k, c in S.STRATEGY.items()},
        'Boundary zones on white (every boundary figure)': {z['label']: zone_on_white(z) for z in S.ZONE.values()},
        # demolition replacement, the recent surge and unconsented additions are parts of Net replacement and share
        # its colour (one band in every figure), so only 'replacement' stands for them
        # every band shown together (Fig1, Fig2, Fig5, D25, D26, D36): the negative bands as filled
        # areas below zero in time series and as outlines in cumulative bars
        'Demand bands (Fig1, Fig2, Fig5, ED6, D25, D26, D36)': {N.BANDS[b]: S.BAND[b][0] for b in S.BAND_ORDER
                                                           if b not in ('redevelopment', 'unconsented')},
        'The Pathways and TL against every strategy, growth, the Reference, the boundaries and the zones': dict(
            {N.STRATEGIES[k]: c for k, c in S.STRATEGY.items()},
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
        # the new palette groups
        'Fig3 (runs, boundaries, zones on white)': dict(
            {'Reference': S.REFERENCE, N.PATHWAY_RUNS['pathway-moderate']: S.PATHWAY_SETTING['moderate'],
             N.PATHWAY_RUNS['pathway-ambitious']: S.PATHWAY_SETTING['ambitious'], N.TL['TL']: S.TL,
             'Acquired rights (AR)': S.AR, 'Ability to pay (AtP)': S.ATP},
            **{z['label']: zone_on_white(z) for z in S.ZONE.values()}),
        'One at a time (Fig7a, ED4, ED5)': {'Input at low end': S.TORNADO_LOW, 'Input at high end': S.TORNADO_HIGH,
                                            'Single alternative case': S.TORNADO_SINGLE},
        # the palette-coverage groups
        'SF2b (components and the demand-band parts)': dict(
            {lab: col for c, (lab, col) in _sf2b().items()}),
        'Replacement variants and the Reference (ED3, SF3, SF6, ED10)': {S.SCENARIO[k]['label']: S.SCENARIO[k]['color']
                                                                        for k in S.SCENARIO},
        'Typologies (ED6, SF4, SF10)': dict(S.TYPOLOGY),
        'Sobol indices (ED7)': {'Total effect': S.SOBOL['total'], 'First-order effect': S.SOBOL['first_order']},
        'Lag variants (SF7)': {'Zero lag': S.LAG_VARIANT[0], '17-month lag': S.LAG_VARIANT[17]},
        'Re-occupation (SF14)': {'Released dwellings (TL)': S.BAND['released_tl'][0],
                                 'Release constraint binds': S.RELEASE_BINDS, 'Dwellings built': S.NEUTRAL_DARK},
        'Categorical groups (diagnostics; Okabe-Ito)': {f'group {i + 1}': c for i, c in enumerate(S.QUALITATIVE)},
    }


def _sf2b():
    """The SF2b parts as drawn (figures/calibration.COMP; the net-replacement pair shares one colour and one label)."""
    from figures import calibration as C
    return {c: v for c, v in C.COMP.items() if c != 'net_replacement'}


def focus():
    """Groups checked only for the pairs that involve the listed colours (the others never share a figure as
    adjacent fills; their own groups check them)."""
    import naming as N
    return {'The Pathways and TL against every strategy, growth, the Reference, the boundaries and the zones':
                ['Moderate / Ambitious Pathway', N.TL['TL']]}


ZONE_ORDER = ('within_both', 'within_ar')


def zone_lightness_order(style=S):
    """The property documented in figures/style.py: the two zones, composited on white at their fixed
    opacities, fall strictly in CAM02-UCS lightness J' within both < within AR only under normal vision and
    every simulated deficiency (each zone's maximum J' over the vision types below the next zone's minimum).
    Returns (holds, {zone: [J' normal, deuteranomaly, protanomaly, tritanomaly]})."""
    J = {k: [float(jab(zone_on_white(style.ZONE[k]), v)[0]) for v in VISION] for k in ZONE_ORDER}
    return all(max(J[a]) < min(J[b]) for a, b in zip(ZONE_ORDER, ZONE_ORDER[1:])), J


def palette_as_shown(style=S):
    """The palette groups of style.PALETTE with the boundary zones as they show on white (alpha
    compositing at the fixed opacities of style.ZONE_ALPHA); every other key as in the file."""
    zkey = {'within_both': 'within_both', 'within_ar_only': 'within_ar'}
    out = {g: dict(style.PALETTE[g]) for g in style.COLOUR_GROUPS}      # [opacity] holds numbers
    out['boundary_zones'] = {k: zone_on_white(dict(color=c, alpha=style.ZONE_ALPHA[zkey[k]]))
                             for k, c in style.PALETTE['boundary_zones'].items()}
    return out


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
    import matplotlib.pyplot as plt
    fig.savefig(path + '.png', dpi=PREVIEW_DPI, metadata={'Software': None})   # a small preview (< 500 KB)
    plt.close(fig)


def main():
    G = groups()
    os.makedirs(DOCS, exist_ok=True)
    preview(G, os.path.join(DOCS, 'palette_preview'))
    L = ['# Palette (generated by tools/palette_check.py from figures/style.py; do not edit by hand)', '',
         'One palette for every figure; `figures/style.py` is the only place colours are defined, and '
         'every module of the figures/ package imports it. Preview with simulated colour-vision deficiency: '
         '[palette_preview.png](palette_preview.png).', '',
         '## Rules', '',
         '* **Source**: the colours are the author\'s (palette.toml); every group drawn together keeps a minimum '
         'CAM02-UCS distance of 10 under every simulated deficiency, the boundary zones excepted (see the check '
         'below). Text is black ink (Nature: primarily black type); the colours are carried by lines, markers and '
         'fills, never by text.',
         f"* **Strategies** (palette.toml [strategies]): S1 Avoid {S.STRATEGY['S1']}, S2 Switch {S.STRATEGY['S2']}, "
         f"S3 Improve {S.STRATEGY['S3']}. A lever is drawn in its "
         f"strategy colour and told apart by marker ({', '.join(S.LEVER_MARKER)} within a strategy; SF9). The "
         f"Moderate Pathway pale yellow ({S.PATHWAY_SETTING['moderate']}), Ambitious Pathway orange "
         f"({S.PATHWAY_SETTING['ambitious']}) and TL a pale sage green ({S.TL}; a larger circle on point plots).",
         '* **Demand bands** (palette.toml [demand_bands]; detailed parts in [components]): '
         f"2026 overbuild {S.P2_ANCHOR}, Overbuild absorbed {S.BAND['overbuild_absorbed'][0]}, "
         f"Net replacement {S.REPLACEMENT} (demolition replacement, the recent surge and unconsented additions drawn "
         f"as one band: the census measures only the net), Released dwellings (TL) "
         f"{S.BAND['released_tl'][0]}. The only untargeted band, Population growth, is a solid deep violet ({S.GROWTH}). "
         "Market balance (the history stock-identity residual, the 2026-27 overbuild and its absorption) one band in "
         f"the demand-band colour ({S.DISPLAY_BAND['market_balance']}), as in Fig1 and SF2b.",
         '* **Signs**: the data keep the sign of every band and the figures never flip it. Time series: '
         'positive bands stacked up from zero, negative bands down from zero (fixed order), the net a black line. '
         'Cumulative bars: positives stacked up from zero, negatives solid below zero, the net total a black marker; '
         'one legend entry per band. Materials and stages are never negative (a STOP if they were).',
         f"* **Maintenance** (B2, B4) neutral grey ({S.BAND['maintenance'][0]}); committed C1-C4 after 2050 "
         f"({S.COMPONENT['committed'][0]}). Carbon stages (palette.toml [life_cycle_stages]): "
         f"A1-A3 {S.STAGE['a1a3'][0]}, A4-A5 {S.STAGE['a4a5'][0]}, soil carbon loss {S.STAGE['soil'][0]}.",
        f"* **Reference** mid grey ({S.REFERENCE}); Low and High replacement greys with dashed and dotted lines. "
        "The Fig3b 2026-2050 column is the Reference colour; its Monte Carlo intervals capped error bars at "
        f"opacity {S.OPACITY['fig3b_interval_bars']:g} (palette.toml [opacity]).",
         f"* **One at a time** (palette.toml [one_at_a_time]; Fig7a, ED4, ED5): input at its low end {S.TORNADO_LOW}, "
         f"at its high end {S.TORNADO_HIGH}, a single alternative case {S.TORNADO_SINGLE}.",
         f"* **Stacked bars and areas** are drawn seamless: each segment's edge is its own face colour at "
         f"{S.LW_SEAM:g} pt (no white borders, no anti-aliasing gaps); a hatch is drawn in a thin hatch colour only "
         f"(default {S.HATCH_COLOUR}; no demand band is hatched). Legend handles keep a thin grey outline.",
         f"* **Boundaries** (every planetary-boundary figure, one implementation in style.py; colours "
         f"from palette.toml [boundaries] and [boundary_zones], the zone opacities fixed in style.ZONE_ALPHA): acquired rights (AR) "
         f"thin brick-red line ({S.AR}), ability to pay (AtP) thin dark-maroon dotted line ({S.ATP}); very pale zones (told "
         'apart by the boundary lines and the legend) below AtP '
         f"({S.ZONE['within_both']['color']}, alpha {S.ZONE['within_both']['alpha']}), between AtP and AR "
         f"({S.ZONE['within_ar']['color']}, alpha {S.ZONE['within_ar']['alpha']}); nothing is filled above AR (the "
         'exceedance is read against the AR line), on annual, '
         'cumulative and level-of-exceedance axes alike. The two principles are never averaged.',
         '* **Settings**: lines: Moderate solid bold, Ambitious the same colour thin dotted; markers: Moderate filled, '
         'Ambitious hollow; bars (Fig6): Moderate filled, Ambitious hollow, TL a large dot.',
         f"* **Typeface**: {S.FONT} (fallback {S.FONT_FALLBACK}), bundled in `fonts/` under the SIL Open "
         'Font License 1.1, registered by figures/style.py, so every machine renders the same glyphs.',
         f"* **Sizes** (Nature Cities): width {S.WIDTH['single'] / S.MM:.0f} mm (single column) or "
         f"{S.WIDTH['double'] / S.MM:.0f} mm (double column), page depth at most {S.MAX_HEIGHT / S.MM:.0f} mm; "
         f"text {S.FONT_SIZE:g} pt, legends and ticks {S.FONT_SMALL:g} pt, never below {S.FONT_MIN:g} pt; data "
         f"lines {S.LW:g} pt, emphasised lines {S.LW_BOLD:g} pt, grid and edges {S.LW_THIN:g} pt.",
         '* **Files** (run profiles, runprofile.py): light PNG at 200 dpi with a small grey footer "LIGHT RUN — '
         'n=1000"; full PNG at 600 dpi; no software or date metadata, so re-runs are '
         'byte-identical.',
         '* **Materials** (Fig2b, Fig2d): six colours in one order in every figure (author decision); soil carbon '
         'loss solid on top, in the same colour as in the stage panels (the same quantity).', '',
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
              'bounded by the AR and AtP lines and ordered strictly in lightness (within both < within AR only '
              'under every simulated deficiency), so their order survives without hue; any other group below the '
              'threshold is labelled directly in every figure (text on or beside each layer) or carries a hatch, so '
              'the reading never depends on colour alone.']
    zmono, Jz = zone_lightness_order(S)
    order = ZONE_ORDER
    if not zmono:
        fails.append('boundary zones lightness order')
    L += ['', '## Boundary zones: lightness order', '',
          'J\' of each zone on white (normal, deuteranomaly, protanomaly, tritanomaly): '
          + '; '.join(f"{S.ZONE[k]['label']} " + ' / '.join(f'{x:.1f}' for x in Jz[k]) for k in order)
          + f". Strictly increasing under every vision type: {'yes' if zmono else 'NO'}. redraw.py warns when a "
          'palette breaks this order.']
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
