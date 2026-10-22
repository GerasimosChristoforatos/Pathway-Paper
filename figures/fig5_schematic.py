"""Fig5 (MODEL v4.2.2): the model schematic, drawn from the data files only (figure_plan.PAPER_MAIN).

  a  the Reference chain: Population -> Households -> Dwellings -> Floor area -> Embodied carbon -> share of the 2 degC
     budget (AR, AtP), one caption per step, and the pipeline note (lag, pipeline years and absorption end from
     baseline/overbuild_2026.json);
  b  one horizontal bar of the six display bands (bands.DISPLAY); widths proportional to the Reference cumulative
     2026-2050 floor area in scope (baseline/bands_annual.csv summed by bands_display_map.csv). The market balance
     nets to about zero (the 2026 overbuild and its absorption), so it is drawn at a fixed width and labelled not to
     scale;
  c  each floor-area lever (L1-L5) under the band whose floor area its single-lever Ambitious run reduces most
     (pathways/bands.csv, in scope, Reference scenario; solid connector), a dashed connector to any further band with at
     least SECONDARY_SHARE of that lever's floor-area reduction; L6-L9 (no floor-area effect) under a separate carbon
     intensity bar. The mapping is derived from the model output and checked against the layout (LAYOUT) so that a
     change in the data cannot silently misplace a chip;
  d  the ambition ladder (Reference, Moderate, Ambitious, Theoretical Limit; adoption end from pathways/levers.json).
Drawing units are mm on the page."""
import textwrap

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

import bands as BANDS_MOD
import figure_plan as FP
import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S

W, H = 183.0, 118.0
SRC = {h['file']: h['source'] for h in FP.PAPER_MAIN}
SIX = [b for b in BANDS_MOD.DISPLAY_ORDER if b not in ('released_tl', 'maintenance')]
BAND_COLOUR = {'growth': S.BAND['growth'][0], 'smaller_households': S.BAND['smaller_households'][0],
               'extra_space': S.BAND['extra_space'][0], 'vacancy': S.BAND['vacancy'][0],
               'net_replacement': S.BAND['replacement'][0], 'market_balance': S.BAND['overbuild_2026'][0]}
BAND_TEXT = {'growth': 'Population growth', 'smaller_households': 'Household-\nsize change',
             'extra_space': 'Extra space', 'vacancy': 'Vacancy', 'net_replacement': 'Net\nreplacement',
             'market_balance': 'Market\nbalance'}
FLOOR_LEVERS = ('L1', 'L2', 'L3', 'L4', 'L5')
CARBON_LEVERS = ('L6', 'L7', 'L8', 'L9')
SECONDARY_SHARE = 0.20
MB_WIDTH = 5.0                                   # fixed width of the market balance segment (net about zero)
# chip placement: lever -> (expected primary band, chip row, chip centre offset from the band centre, mm)
LAYOUT = {'L5': ('growth', 0, 0.0), 'L1': ('smaller_households', 0, -1.0), 'L4': ('extra_space', 0, 3.0),
          'L2': ('vacancy', 1, -1.0), 'L3': ('net_replacement', 0, 5.0)}
LABEL_ROW = {'growth': 0, 'smaller_households': 1, 'extra_space': 0, 'vacancy': 1, 'net_replacement': 0,
             'market_balance': 1}


def band_widths():
    """{display band: Reference cumulative floor area 2026-2050, Mm2, in scope} (bands_annual.csv, bands_display_map)."""
    d = D.csv('baseline/bands_annual.csv')
    d = d[(d['year'] >= 2026) & (d['year'] <= 2050)]
    m = D.csv('bands_display_map.csv').set_index('band_id')['display_id']
    g = d.groupby([m[P.band_id(b)] for b in d['band']])['floor_area_Mm2'].sum()
    return {b: float(g.get(b, 0.0)) for b in SIX}


def lever_bands():
    """{lever: (primary band, [secondary bands], {band: reduction Mm2})} from the single-lever Ambitious runs
    (Reference - run per display band, floor area, in scope)."""
    d = D.csv('pathways/bands.csv')
    d = d[(d['scenario'] == 'REF') & (d['definition'] == 'in_scope')]
    m = D.csv('bands_display_map.csv').set_index('band_id')['display_id']
    out = {}
    for L in FLOOR_LEVERS:
        r = d[d['run'] == f'{L}-ambitious']
        red = (-r.groupby([m[P.band_id(b)] for b in r['band']])['delta_floor_area_Mm2_vs_reference'].sum())
        red = {b: float(red.get(b, 0.0)) for b in SIX}
        pos = {b: v for b, v in red.items() if v > 1e-9}
        prim = max(pos, key=pos.get)
        tot = sum(pos.values())
        sec = [b for b, v in pos.items() if b != prim and v >= SECONDARY_SHARE * tot]
        out[L] = (prim, sec, red)
    for L in CARBON_LEVERS:                     # no floor-area effect (asserted, not assumed)
        r = d[d['run'] == f'{L}-ambitious']
        assert np.allclose(r['delta_floor_area_Mm2_vs_reference'], 0.0, atol=1e-9), L
    return out


def _box(ax, x0, y0, w, h, text, edge, face='white', fs=S.FONT_SMALL, weight='normal', color=S.INK, lw=0.8,
         alpha=1.0, r=1.2):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f'round,pad=0,rounding_size={r}', facecolor=face,
                                edgecolor=edge, lw=lw, zorder=3, alpha=alpha))
    if alpha < 1:                                # tinted face: redraw the edge opaque
        ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f'round,pad=0,rounding_size={r}', facecolor='none',
                                    edgecolor=edge, lw=lw, zorder=3))
    ax.text(x0 + w / 2, y0 + h / 2, text, ha='center', va='center', fontsize=fs, fontweight=weight, color=color,
            zorder=4, linespacing=1.15)


def _arrow(ax, x0, y0, x1, y1, color=S.INK, lw=0.9):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=6, color=color, lw=lw,
                                 zorder=4, shrinkA=0, shrinkB=0))


def _title(ax, x, y, letter, text, ha='left'):
    ax.text(x, y, f'{letter}  {text}', ha=ha, va='baseline', fontsize=S.FONT_SIZE + 1, fontweight='bold',
            color=S.INK)


def fig5():
    ob = D.js('baseline/overbuild_2026.json')
    ad = D.js('pathways/levers.json')['adoption']
    widths = band_widths()
    lb = lever_bands()
    for L, (band, _, _) in LAYOUT.items():       # the layout must match the mapping the model output gives
        assert lb[L][0] == band, f'{L}: primary band {lb[L][0]} in the data, {band} in the layout'
    fig = plt.figure(figsize=(W * S.MM, H * S.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')

    # a  chain
    _title(ax, 2.0, 113.5, 'a', 'Reference model chain, 2026–2050')
    steps = [('Population', 'Stats NZ projection\n(2026 observed)'),
             ('Households', '÷ household size\n(2023 census anchor)'),
             ('Dwellings', '+ vacancy + replacement\n− unconsented'),
             ('Floor area', '× size by typology\n= need + extra space'),
             ('Embodied carbon', '× kg CO₂e per m²: A1–A5,\nsoil carbon, B2/B4')]
    bw, gap, by, bh = 26.0, (W - 4.0 - 6 * 26.0) / 5, 96.0, 10.0
    xs = [2.0 + i * (bw + gap) for i in range(6)]
    for (t, cap), x in zip(steps, xs):
        _box(ax, x, by, bw, bh, t, edge=S.INK, fs=S.FONT_SIZE, weight='bold')
        ax.text(x + bw / 2, by - 1.4, cap, ha='center', va='top', fontsize=S.FONT_MIN + 0.5, color=S.INK,
                linespacing=1.15)
    _box(ax, xs[5], by, bw, bh, 'Share of 2 °C budget\nAR · AtP', edge=S.AR, face=S.AR, alpha=0.08,
         fs=S.FONT_SIZE - 0.5, weight='bold')
    ax.text(xs[5] + bw / 2, by - 1.4, 'level of exceedance\n= carbon ÷ budget', ha='center', va='top',
            fontsize=S.FONT_MIN + 0.5, color=S.AR, linespacing=1.15)
    for i in range(5):
        _arrow(ax, xs[i] + bw + 0.4, by + bh / 2, xs[i + 1] - 0.4, by + bh / 2, color=S.AR if i == 4 else S.INK)
    py = ob['pipeline_years']
    ax.text(W / 2, 84.5, f"{py[0]}–{str(py[-1])[-2:]} from consents already issued ({ob['completion_lag_months']}-month "
            f"lag); surplus = market balance, absorbed by {ob['absorption_end']}", ha='center', va='center',
            fontsize=S.FONT_MIN + 0.5, style='italic', color=S.BAND['overbuild_2026'][0])

    # b  demand bands (widths = Reference cumulative floor area 2026-2050)
    _title(ax, 2.0, 78.0, 'b', 'Floor area split by demand  ·  ')
    ax.text(52.5, 78.0, 'c  levers placed on the band they shrink', ha='left', va='baseline',
            fontsize=S.FONT_SIZE + 1, fontweight='bold', color=S.INK)
    x0, x1, yb, hb, sep = 2.0, 124.0, 54.0, 6.0, 0.5
    pos_bands = [b for b in SIX if b != 'market_balance']
    scale = (x1 - x0 - MB_WIDTH - sep * (len(SIX) - 1)) / sum(widths[b] for b in pos_bands)
    cen, x = {}, x0
    for b in SIX:
        w = MB_WIDTH if b == 'market_balance' else widths[b] * scale
        ax.add_patch(Rectangle((x, yb), w, hb, facecolor=BAND_COLOUR[b], edgecolor='none', zorder=2))
        cen[b] = x + w / 2
        x += w + sep
    for b in SIX:
        val = widths[b]
        sub = (f'net {val:+.1f} Mm²\n(not to scale)'.replace('-', '−') if b == 'market_balance'
               else f'{val:.1f} Mm²')
        ytxt = yb + hb + 1.2 + (6.4 if LABEL_ROW[b] else 0.0)
        ax.text(cen[b], ytxt, BAND_TEXT[b] + '\n' + sub, ha='center', va='bottom', fontsize=S.FONT_MIN + 0.5,
                color=S.INK, linespacing=1.1)
        if LABEL_ROW[b]:
            ax.plot([cen[b], cen[b]], [yb + hb + 0.2, ytxt - 0.4], color=S.MUTED, lw=S.LW_THIN, zorder=1)
    ax.text(cen['growth'], yb + hb / 2, 'driver (exogenous)', ha='center', va='center', fontsize=S.FONT_SMALL,
            color='white', style='italic', zorder=4)
    ax.text(cen['market_balance'], yb - 1.0, f"absorbed\nby {ob['absorption_end']}", ha='center', va='top',
            fontsize=S.FONT_MIN, color=S.BAND['overbuild_2026'][0], style='italic', linespacing=1.1)

    # c  lever chips (edge = strategy colour); solid line to the primary band, dashed to a secondary band
    cw, ch = 20.5, 4.4
    row_y = {0: 44.5, 1: 37.5}
    chip_top = {}
    for L, (band, row, dx) in LAYOUT.items():
        c = S.STRATEGY[N.LEVER_STRATEGY[L]]
        xc, y = cen[band] + dx, row_y[row]
        _box(ax, xc - cw / 2, y, cw, ch, f'{L} {N.LEVERS[L]}', edge=c, fs=S.FONT_MIN + 0.5, lw=1.0)
        ax.plot([cen[band], xc], [yb, y + ch], color=c, lw=0.8, zorder=1)
        chip_top[L] = (xc, y + ch)
    ext = cen['extra_space']
    w_ext = widths['extra_space'] * scale
    for L in FLOOR_LEVERS:
        for k, b in enumerate(lb[L][1]):
            assert b == 'extra_space', f'{L}: secondary band {b} has no connector slot in the layout'
            xt = ext - w_ext / 2 + (3.0 if L == 'L5' else 6.5)
            xc, yt = chip_top[L]
            ax.plot([xc + (3.0 if L == 'L5' else 2.0), xt], [yt, yb], color=S.STRATEGY[N.LEVER_STRATEGY[L]],
                    lw=0.7, ls=(0, (2.0, 1.5)), zorder=1)
    # carbon intensity bar and L6-L9
    cx0, cx1 = 128.5, 150.5
    ax.add_patch(Rectangle((cx0, yb), cx1 - cx0, hb, facecolor='white', edgecolor=S.MUTED, lw=S.LW_THIN, zorder=2))
    ccen = (cx0 + cx1) / 2
    ax.text(ccen, yb + hb / 2, 'kg CO₂e per m²', ha='center', va='center', fontsize=S.FONT_SMALL, color=S.INK)
    ax.text(ccen, yb + hb + 1.2, 'Carbon intensity\n(all bands)', ha='center', va='bottom',
            fontsize=S.FONT_MIN + 0.5, color=S.INK, linespacing=1.1)
    for i, L in enumerate(CARBON_LEVERS):
        c = S.STRATEGY[N.LEVER_STRATEGY[L]]
        _box(ax, ccen - cw / 2 - 0.5, 44.0 - i * 7.6, cw + 1.0, 6.4, '\n'.join(textwrap.wrap(f'{L} {N.LEVERS[L]}', 20)),
             edge=c, fs=S.FONT_MIN + 0.5, lw=1.0)
    ax.plot([ccen, ccen], [44.0 + 6.4, yb], color=S.STRATEGY['S2'], lw=0.8, zorder=1)

    # legend: the three PAS 2080 strategies
    leg = [('S1', 'S1 Avoid — need less floor area'), ('S2', 'S2 Switch — lower-carbon land and materials'),
           ('S3', 'S3 Improve — cleaner construction')]
    for (St, t), lx in zip(leg, (2.0, 40.0, 92.0)):
        ax.add_patch(Rectangle((lx, 12.6), 2.4, 2.4, facecolor=S.STRATEGY[St], edgecolor='none'))
        ax.text(lx + 3.4, 13.8, t, ha='left', va='center', fontsize=S.FONT_SMALL, fontweight='bold',
                color=S.STRATEGY[St])
    ax.text(2.0, 7.5, 'Reference carbon = band floor area × carbon per m², plus maintenance (B2/B4). Pathways = '
            'Reference with levers applied; Shapley values in Fig7, sequential PAS 2080 waterfalls in Fig4.', ha='left', va='center', fontsize=S.FONT_MIN + 0.5, color=S.INK)
    ax.text(2.0, 3.8, f'Solid line: the band a lever reduces most (single-lever Ambitious run); dashed: a further band '
            f'with ≥ {SECONDARY_SHARE:.0%} of its floor-area reduction.', ha='left', va='center',
            fontsize=S.FONT_MIN + 0.5, color=S.MUTED)

    # d  ambition ladder
    _title(ax, 168.0, 78.0, 'd', 'Ambition levels', ha='center')
    lad = [('Theoretical Limit', 'physical or\nbest-observed limit', S.TL),
           ('Ambitious Pathway', 'documented frontier', S.PATHWAY_SETTING['ambitious']),
           ('Moderate Pathway', 'halfway to Ambitious', S.PATHWAY_SETTING['moderate']),
           ('Reference', 'observed trends', S.REFERENCE)]
    lx0, lw_, lh = 156.0, 25.5, 8.0
    ly = [57.0 - i * 9.4 for i in range(4)]
    for (t, sub, c), y in zip(lad, ly):
        ax.add_patch(Rectangle((lx0, y), lw_, lh, facecolor=c, edgecolor='none', zorder=2))
        ax.text(lx0 + lw_ / 2, y + lh - 2.2, t, ha='center', va='center', fontsize=S.FONT_SMALL, fontweight='bold',
                color='white', zorder=3)
        ax.text(lx0 + lw_ / 2, y + 2.6, sub, ha='center', va='center', fontsize=S.FONT_MIN, color='white', zorder=3,
                linespacing=1.05)
    _arrow(ax, 153.6, ly[-1], 153.6, ly[0] + lh, color=S.MUTED, lw=0.8)
    ax.text(lx0 + lw_ / 2, ly[-1] - 1.8, f"all levers phase in by {ad['end']}\nsame nine levers, rising ambition",
            ha='center', va='top', fontsize=S.FONT_MIN + 0.5, style='italic', color=S.INK, linespacing=1.15)

    note = ('Band widths (Reference cumulative floor area 2026–2050, in scope, Mm²): '
            + ', '.join(f"{BANDS_MOD.DISPLAY_LABEL[b].split(' (')[0]} {widths[b]:.3f}" for b in SIX)
            + '; market balance drawn at a fixed width. Lever → band (single-lever Ambitious runs, floor-area '
              'reduction Mm²): '
            + '; '.join(f"{L} → {lb[L][0]} ({lb[L][2][lb[L][0]]:.2f})"
                        + (' + ' + ', '.join(f'{b} ({lb[L][2][b]:.2f})' for b in lb[L][1]) if lb[L][1] else '')
                        for L in FLOOR_LEVERS)
            + '; L6–L9: carbon per m² (no floor-area change).')
    S.save_figure(fig, 'Fig5_model_schematic', note=note, source=SRC['Fig5_model_schematic'])


FIGURES = {'Fig5_model_schematic': fig5}
