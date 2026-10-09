"""
HEADLINE FIGURES (MODEL v1.0.0): the figures of the paper, H1-H11
=================================================================
Every figure is drawn from the data files of outputs/data/ (layout.py) and nothing else:
no model is run here, so a figure can never disagree with the data it shows. Labels come
from naming.py, colours, sizes and saving from style.py (docs/PALETTE.md), titles, panels
and draft captions from figure_plan.py (docs/FIGURE_PLAN.md).

For each figure Hx this writes, in outputs/headline/:
  Hx_<name>.png / .pdf   300 dpi PNG and vector PDF, 183 mm wide (Nature double column)
  Hx_<name>.csv          the source data: every plotted value in long format
                         (panel, series, x, value, unit), as Nature's Source Data files
and outputs/headline/HEADLINE.md: the headline findings (one sentence each, with the numbers
and the data files they come from) and every figure with its caption, the numbers in the
captions filled from the data.

    python headline.py            (run_all.py runs it after the pathways step)
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import layout as L  # noqa: E402
import naming as N  # noqa: E402
import plotting as P  # noqa: E402
import style as S  # noqa: E402

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch, Rectangle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

M6 = 1e6
REF = 'REF'
VARIANTS = ('LOW', 'REF', 'HIGH')
WINDOW = (2026, 2050)
PLAN = {h['id']: h for h in FP.HEADLINE}
TOP_N_H11 = 8                       # H11: the parameters with the largest effect on the cumulative LoE AR


# ============================================================
# DATA (outputs/data/ only)
# ============================================================
def path(rel):
    return L.data(rel, frozen=False)


def read_csv(rel, **kw):
    return pd.read_csv(path(rel), **kw)


def read_json(rel):
    with open(path(rel)) as f:
        return json.load(f)


def quick_run():
    return read_json('metrics.json').get('run_mode', 'full') != 'full'


class Source:
    """Source data of one figure: every plotted value as (panel, series, x, value, unit)."""

    def __init__(self, fid):
        self.fid, self.rows = fid, []

    def add(self, panel, series, x, values, unit):
        xs = np.atleast_1d(np.asarray(x, dtype=object))
        vs = np.atleast_1d(np.asarray(values, dtype=float))
        if len(xs) == 1 and len(vs) > 1:
            xs = np.repeat(xs, len(vs))
        for xi, vi in zip(xs, vs):
            self.rows.append(dict(panel=panel, series=series, x=xi, value=float(vi), unit=unit))

    def write(self):
        pd.DataFrame(self.rows, columns=['panel', 'series', 'x', 'value', 'unit']).to_csv(
            L.writing(os.path.join(L.HEADLINE, f'{self.fid}.csv')), index=False)


def save(fig, fid, src):
    """Source data, then the figure (style.save_figure: PNG and PDF); a headline figure must print
    at Nature's double-column width, so a PNG wider than 183 mm (labels outside the frame) is
    refused."""
    from PIL import Image
    src.write()
    S.save_figure(fig, fid)
    with Image.open(L.figure(fid) + '.png') as im:
        w_mm = im.size[0] / S.DPI * 25.4
    if w_mm > 183.0 + 1e-6:
        raise SystemExit(f'{fid}: {w_mm:.1f} mm wide; a headline figure prints at most 183 mm wide.')


def fill(fid, **numbers):
    return PLAN[fid]['caption'].format(**numbers)


# ============================================================
# H1  How the model works (structure only; no numbers)
# ============================================================
def h1():
    """Drawn on a millimetre grid of the printed figure (183 x 96 mm), so every box and label is
    placed at its print size."""
    import textwrap
    fid = PLAN['H1']['file']
    src = Source(fid)
    W, H = 183.0, 96.0
    fig = plt.figure(figsize=S.figsize('double', H))
    m = 0.6                              # the axes (always inside the tight bounding box) stop 0.6 mm short
    ax = fig.add_axes([m / W, m / H, 1 - 2 * m / W, 1 - 2 * m / H])     # of the edges; data units stay mm
    ax.set_xlim(m, W - m)
    ax.set_ylim(m, H - m)
    ax.set_axis_off()

    def box(x, y, w, h, title, sub='', fc='white'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.2', fc=fc, ec=S.INK,
                                    lw=S.LW_THIN))
        ax.text(x + w / 2, y + h / 2 + (1.6 if sub else 0), title, ha='center', va='center', fontsize=S.FONT_SIZE,
                fontweight='bold', color=S.INK)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 2.4, sub, ha='center', va='center', fontsize=S.FONT_SMALL, color=S.INK,
                    linespacing=1.1)

    def arrow(p, q, color=S.INK, lw=S.LW_THIN):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=6, color=color, lw=lw, shrinkA=0,
                                     shrinkB=0))

    def swatch(x, y, colour, hatch):
        ax.add_patch(Rectangle((x, y - 1.8), 3.6, 3.6, fc=colour, ec='#555555', lw=S.LW_THIN, hatch=hatch))

    def heading(x, y, text, color=S.INK):
        ax.text(x, y, text, fontsize=S.FONT_SMALL, fontweight='bold', color=color, va='center')

    # 1. the chain, population to level of exceedance
    chain = [('Population', 'Stats NZ projections'), ('Households', 'household size'),
             ('Dwellings', 'required'), ('Floor area', 'm² per dwelling'),
             ('Embodied carbon', 'A1–A5, soil, B2/B4'), ('Level of exceedance', 'against the boundaries')]
    bw, gap, y0, bh = 26.6, 4.0, 82.0, 12.0
    xs = [1.0 + k * (bw + gap) for k in range(len(chain))]
    for (t, sub), x in zip(chain, xs):
        box(x, y0, bw, bh, t, sub)
    for xa, xb in zip(xs[:-1], xs[1:]):
        arrow((xa + bw, y0 + bh / 2), (xb, y0 + bh / 2), lw=S.LW)
    # 2. demand bands, and the levers that act on them
    xb_, yb = 62.0, 70.0
    heading(xb_, yb + 5.5, 'Demand bands: why floor area is built')
    heading(1.0, yb + 5.5, 'Pathway levers')
    arrow((xs[2] + bw / 2, y0), (xs[2] + bw / 2, yb + 8.0))
    bands = [('growth', None), ('smaller_households', None), ('extra_space', 'L1'), ('vacancy', 'L2'),
             ('overbuild_2026', 'L3'), ('replacement', 'L4'), ('redevelopment', 'L4')]
    for k, (bid, lev) in enumerate(bands):
        y = yb - k * 5.6
        colour, hatch = S.BAND[bid]
        swatch(xb_, y, colour, hatch)
        ax.text(xb_ + 5.2, y, N.BANDS[bid] + (' (untargeted)' if bid in N.UNTARGETED else ''), va='center',
                fontsize=S.FONT_SMALL, color=S.INK)
        if lev:
            p = [pw for pw, ls in N.PATHWAY_LEVERS.items() if lev in ls][0]
            if bid != 'redevelopment':
                ax.text(1.0, y, f'{lev} {N.LEVERS[lev]}', va='center', ha='left', fontsize=S.FONT_SMALL,
                        color=S.PATHWAY[p], fontweight='bold')
                arrow((33.0, y), (xb_ - 1.0, y), color=S.PATHWAY[p])
            else:
                arrow((33.0, y + 5.6), (xb_ - 1.0, y), color=S.PATHWAY[p])
        src.add('bands', N.BANDS[bid], 'lever', 0 if lev is None else int(lev[1]), 'lever number (0: untargeted)')
    # 3. carbon components, and L5
    xc, yc = 117.0, 70.0
    heading(xc, yc + 5.5, 'Carbon components')
    arrow((xs[4] + bw / 2, y0), (xs[4] + bw / 2, yc + 8.0))
    for k, cid in enumerate(('materials_construction', 'soil', 'maintenance')):
        y = yc - k * 7.0
        colour, hatch = S.COMPONENT[cid]
        swatch(xc, y, colour, hatch)
        ax.text(xc + 5.2, y, textwrap.fill(N.COMPONENTS[cid], 24), va='center', fontsize=S.FONT_SMALL, color=S.INK,
                linespacing=1.1)
    yl5 = yc - 3 * 7.0 - 0.5
    ax.text(xc, yl5, f"L5 {N.LEVERS['L5']}:\ncarbon per m² (A1–A3)", fontsize=S.FONT_SMALL,
            color=S.PATHWAY['P4'], fontweight='bold', va='center', linespacing=1.1)
    ax.plot([xc - 1.0, xc - 3.0, xc - 3.0], [yl5, yl5, yc], color=S.PATHWAY['P4'], lw=S.LW_THIN,
            solid_joinstyle='miter')
    arrow((xc - 3.0, yc), (xc - 0.3, yc), color=S.PATHWAY['P4'])
    # 4. the boundaries feed the level of exceedance
    xa_ = xs[5]
    box(xa_, 54.0, bw, 15.0, 'AESA boundaries', 'AR: acquired rights\nAtP: ability to pay')
    arrow((xa_ + bw / 2, 69.0), (xa_ + bw / 2, y0))
    # 5. pathways and the theoretical limit
    def row(y, items):
        """Labels side by side, each 4 mm after the end of the previous one (measured)."""
        x, r = 1.0, fig.canvas.get_renderer()
        for text, kw in items:
            t = ax.text(x, y, text, fontsize=S.FONT_SMALL, va='center', **kw)
            bb = t.get_window_extent(r).transformed(ax.transData.inverted())
            x = bb.x1 + 4.0
        if x - 4.0 > W - m:
            raise SystemExit('H1: a row of labels is wider than the figure.')

    heading(1.0, 25.0, 'Pathways (levers combined)')
    row(20.0, [(f"{pw} {N.PATHWAYS[pw]} ({'+'.join(N.PATHWAY_LEVERS.get(pw, ('L1–L5',)))})",
                dict(color=S.PATHWAY[pw], fontweight='bold')) for pw in (f'P{k}' for k in range(1, 6))])
    heading(1.0, 13.0, 'Theoretical limit TL: each lever and the soil at its limit, from 2027', color=S.TL)
    row(8.0, [(f"TL{k} {N.TL[f'TL{k}']}", dict(color=S.TL)) for k in range(1, 7)])
    ax.text(1.0, 3.0, 'TL: ' + N.TL_CAPTION + '.', fontsize=S.FONT_SMALL, color=S.MUTED, style='italic',
            va='center')
    save(fig, fid, src)
    return dict(caption=fill('H1'))


# ============================================================
# H2  New residential floor area, 1991-2050
# ============================================================
def h2():
    fid = PLAN['H2']['file']
    src = Source(fid)
    an = read_csv('baseline/annual.csv')
    va = read_csv('baseline/variants_annual.csv')
    mc = read_csv(L.montecarlo('annual', REF, frozen=False), index_col=0)
    ms = read_csv(L.montecarlo('summary', REF, frozen=False), index_col=0)
    sc = read_json('baseline/scenarios.json')['scenarios']
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 70), gridspec_kw=dict(width_ratios=[2.6, 1]))
    hist = an[an['source'] == 'history']
    proj = an[an['source'] == 'projection']
    a.plot(hist['year'], hist['floor_area_Mm2'], color=S.INK, lw=S.LW, label='History, in scope (consents timed as '
           'completions × completion rate)')
    src.add('a', 'History', hist['year'], hist['floor_area_Mm2'], 'Mm2 per year')
    yr = mc.index.values[mc.index.values >= WINDOW[0]]
    lo, hi = mc.loc[yr, 'floor_area_5'] / M6, mc.loc[yr, 'floor_area_95'] / M6
    a.fill_between(yr, lo, hi, label='Monte Carlo 5–95% (Reference)', **S.MC_BAND)
    src.add('a', 'Monte Carlo 5%', yr, lo, 'Mm2 per year')
    src.add('a', 'Monte Carlo 95%', yr, hi, 'Mm2 per year')
    for k in ('LOW', 'HIGH', 'REF'):
        d = va[va['variant'] == k]
        st = dict(S.SCENARIO[k])
        lab = st.pop('label')
        a.plot(d['year'], d['floor_area_Mm2'], label=lab, **st)
        src.add('a', N.SCENARIOS[k], d['year'], d['floor_area_Mm2'], 'Mm2 per year')
    if not np.allclose(va[va['variant'] == REF]['floor_area_Mm2'].values, proj['floor_area_Mm2'].values, rtol=1e-12):
        raise SystemExit('H2: the Reference of variants_annual.csv differs from annual.csv.')
    a.axvline(2025.5, color=S.MUTED, lw=S.LW_THIN, ls=':')
    a.set_xlim(1991, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Floor area (Mm² per year)')
    a.legend(loc='upper left', ncol=1)
    P.panel_label(a, 'a')
    tot = {k: sc[k]['floor_area_Mm2'] for k in VARIANTS}
    p5, p95 = ms.loc['floor_area_Mm2', 'p5'], ms.loc['floor_area_Mm2', 'p95']
    for i, k in enumerate(VARIANTS):
        b.bar(i, tot[k], color=S.SCENARIO[k]['color'], width=0.62, edgecolor='white')
        b.text(i, tot[k] / 2, f'{tot[k]:.1f}', ha='center', va='center', fontsize=S.FONT_SMALL, color='white')
        src.add('b', N.SCENARIOS[k], 'cumulative 2026-2050', tot[k], 'Mm2')
    i = VARIANTS.index(REF)
    b.errorbar(i, tot[REF], yerr=[[tot[REF] - p5], [p95 - tot[REF]]], color=S.INK, capsize=2.5, lw=S.LW,
               capthick=S.LW)
    src.add('b', 'Reference, Monte Carlo 5%', 'cumulative 2026-2050', p5, 'Mm2')
    src.add('b', 'Reference, Monte Carlo 95%', 'cumulative 2026-2050', p95, 'Mm2')
    b.set_xticks(range(len(VARIANTS)))
    b.set_xticklabels([N.SCENARIOS[k].replace(' replacement', '\nreplacement') for k in VARIANTS])
    b.set_ylabel('Floor area 2026–2050 (Mm²)')
    b.grid(axis='x', visible=False)
    P.panel_label(b, 'b')
    fig.tight_layout()
    save(fig, fid, src)
    num = dict(gfa_ref=tot[REF], gfa_p5=p5, gfa_p95=p95, gfa_low=tot['LOW'], gfa_high=tot['HIGH'])
    return dict(num, caption=fill('H2', **num))


# ============================================================
# H3  Why floor area is built
# ============================================================
def h3():
    fid = PLAN['H3']['file']
    src = Source(fid)
    ba = read_csv('baseline/bands_annual.csv')
    bh = read_csv('baseline/bands_history.csv')
    fig, ax = plt.subplots(figsize=S.figsize('double', 78))
    # history: one bar per census interval (interval mean), spanning its years
    hist_ids = list(N.BANDS_HISTORY)
    for _, g in bh.groupby('interval', sort=False):
        y0, y1 = int(g['year_start'].iloc[0]), int(g['year_end'].iloc[0])
        faint = g['households_from'].iloc[0] != 'census'
        parts = [(('replacement' if b == 'replacement_history' else b),
                  float(g[g['band'] == N.band_data_label(b)]['floor_area_Mm2_per_year'].iloc[0])) for b in hist_ids]
        P.signed_stack(ax, [y0 - 0.5 + (y1 - y0 + 1) / 2], parts, width=(y1 - y0 + 1) * 0.96,
                     alpha=0.45 if faint else 1.0, align='center')
        for b, v in parts:
            src.add('history', N.band_data_label(b if b != 'replacement' else 'replacement_history'),
                    f'{y0}-{y1}', v, 'Mm2 per year (interval mean)')
    # projection: annual bands 2026-2050 (maintenance carries no floor area)
    proj_ids = [b for b in N.BANDS_IN_SCOPE if b != 'maintenance']
    years = sorted(ba['year'].unique())
    parts = []
    for b in proj_ids:
        v = ba[ba['band'] == N.band_data_label(b)].set_index('year').loc[years, 'floor_area_Mm2'].values
        parts.append((b, v))
        src.add('projection', N.BANDS[b], years, v, 'Mm2 per year')
    P.signed_stack(ax, years, parts, width=0.82)
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.axvline(2025.5, color=S.MUTED, lw=S.LW_THIN, ls=':')
    y_lo, y_hi = ax.get_ylim()
    ax.set_ylim(y_lo, y_hi + 0.1 * (y_hi - y_lo))          # head room for the two labels
    ax.text(2025.0, 0.98, 'History: census intervals ', transform=ax.get_xaxis_transform(), ha='right', va='top',
            fontsize=S.FONT_SMALL, color=S.MUTED)
    ax.text(2026.0, 0.98, ' Reference projection', transform=ax.get_xaxis_transform(), ha='left', va='top',
            fontsize=S.FONT_SMALL, color=S.MUTED)
    ax.set_xlim(1991, 2050.6)
    ax.set_ylabel('Floor area (Mm² per year)')
    ax.grid(axis='x', visible=False)
    P.band_legend(fig, ['growth', 'smaller_households', 'extra_space', 'vacancy', 'overbuild_2026', 'replacement',
                      'redevelopment'], y=-0.01, ncol=4)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    save(fig, fid, src)
    tot = ba.groupby('band')['floor_area_Mm2'].sum()
    untargeted = sum(tot[N.band_data_label(b)] for b in N.UNTARGETED)
    total = tot.sum()
    num = dict(untargeted_share=untargeted / total, total=total,
               extra_space=tot[N.band_data_label('extra_space')], vacancy=tot[N.band_data_label('vacancy')],
               overbuild=tot[N.band_data_label('overbuild_2026')],
               replacement=tot[N.band_data_label('replacement')] + tot[N.band_data_label('redevelopment')])
    cap = (fill('H3') + f" Over 2026–2050 the untargeted bands are {100 * num['untargeted_share']:.0f}% of the "
           f"{total:.1f} million m² built. History: interval means between censuses (vacancy on one definition, "
           'the pooled 2018/2023 empty share); the history\'s replacement band holds any redevelopment (not '
           'separable); the faint bar after the latest census uses consent-derived households. Retirement villages '
           '(out of scope) are removed from every band in proportion.')
    return dict(num, caption=cap)


# ============================================================
# H4  Embodied carbon 2026-2050 by component
# ============================================================
def h4():
    fid = PLAN['H4']['file']
    src = Source(fid)
    an = read_csv('baseline/annual.csv')
    an = an[an['source'] == 'projection'].set_index('year')
    pj = read_json('baseline/projection.json')
    mc = read_csv(L.montecarlo('annual', REF, frozen=False), index_col=0)
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 72), gridspec_kw=dict(width_ratios=[2.2, 1]))
    years = an.index.values
    comps = [('materials_construction', 'materials_construction_kt'), ('soil', 'soil_carbon_loss_kt'),
             ('maintenance', 'maintenance_kt')]
    total = sum(an[c].values for _, c in comps)
    if not np.allclose(total, an['carbon_kt'].values, rtol=1e-12, atol=0):
        raise SystemExit('H4: the components do not add up to the annual carbon.')
    base = np.zeros(len(years))
    for cid, col in comps:
        colour, hatch = S.COMPONENT[cid]
        a.bar(years, an[col].values, bottom=base, width=0.82, color=colour, hatch=hatch, edgecolor='white',
              lw=S.LW_THIN, label=N.COMPONENTS[cid])
        src.add('a', N.COMPONENTS[cid], years, an[col].values, 'kt CO2e per year')
        base = base + an[col].values
    src.add('a', 'Total (sum of the components)', years, an['carbon_kt'].values, 'kt CO2e per year')
    lo, hi = mc.loc[years, 'carbon_5'] / M6, mc.loc[years, 'carbon_95'] / M6
    a.plot(years, lo, color=S.INK, lw=S.LW_THIN, ls='--', label='Total, Monte Carlo 5–95%')
    a.plot(years, hi, color=S.INK, lw=S.LW_THIN, ls='--')
    src.add('a', 'Total, Monte Carlo 5%', years, lo, 'kt CO2e per year')
    src.add('a', 'Total, Monte Carlo 95%', years, hi, 'kt CO2e per year')
    a.set_xlim(2025.4, 2050.6)
    a.set_ylim(0, None)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    a.grid(axis='x', visible=False)
    a.legend(loc='upper right')
    P.panel_label(a, 'a')
    # (b) cumulative by material, and committed after 2050
    mat = pj['material_kt']
    com = pj['committed']
    x0 = 0
    bottom = 0.0
    for code_, label, colour in S.MATERIAL:
        v = float(mat[code_])
        b.bar(x0, v, bottom=bottom, width=0.6, **P.material_patch(code_, colour))
        if v > 0.035 * sum(mat.values()):
            b.text(x0 + 0.34, bottom + v / 2, f'{label} {v:,.0f}', va='center', ha='left', fontsize=S.FONT_MIN,
                   color=S.INK)
        src.add('b', label, 'cumulative 2026-2050', v, 'kt CO2e')
        bottom += v
    if not math.isclose(bottom, pj['carbon_kt'], rel_tol=1e-9):
        raise SystemExit('H4: the materials do not add up to the carbon 2026-2050.')
    colour, hatch = S.COMPONENT['committed']
    b.bar(1.6, com['lower_kt'], width=0.6, facecolor='white', edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN)
    b.bar(1.6, com['upper_kt'] - com['lower_kt'], bottom=com['lower_kt'], width=0.6, facecolor=colour,
          edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN, alpha=0.5)
    b.text(1.6, com['upper_kt'], f"{com['lower_kt']:,.0f}–\n{com['upper_kt']:,.0f}", ha='center', va='bottom',
           fontsize=S.FONT_SMALL)
    src.add('b', 'Committed after 2050, lower (2050 factors held)', 'after 2050', com['lower_kt'], 'kt CO2e')
    src.add('b', 'Committed after 2050, upper (2025 factors)', 'after 2050', com['upper_kt'], 'kt CO2e')
    b.set_xticks([0, 1.6])
    b.set_xticklabels(['2026–2050', 'Committed\nafter 2050'])
    b.set_xlim(-0.5, 2.3)
    b.set_ylabel('Embodied carbon (kt CO₂e)')
    b.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    b.grid(axis='x', visible=False)
    P.panel_label(b, 'b')
    fig.tight_layout()
    save(fig, fid, src)
    num = dict(carbon=pj['carbon_kt'], materials=float(an['materials_construction_kt'].sum()),
               soil=float(an['soil_carbon_loss_kt'].sum()), maintenance=float(an['maintenance_kt'].sum()),
               com_lo=com['lower_kt'], com_hi=com['upper_kt'])
    cap = (fill('H4') + f" Of the {num['carbon']:,.0f} kt CO₂e emitted in 2026–2050, materials and construction "
           f"are {num['materials']:,.0f} kt, soil carbon loss {num['soil']:,.0f} kt and maintenance "
           f"{num['maintenance']:,.0f} kt; a further {num['com_lo']:,.0f}–{num['com_hi']:,.0f} kt is committed "
           'after 2050. Dashed: Monte Carlo 5–95% of the annual total. Materials include their maintenance '
           'within 2026–2050.')
    return dict(num, caption=cap)


# ============================================================
# H5  Reference emissions against the AR and AtP boundaries
# ============================================================
def h5():
    fid = PLAN['H5']['file']
    src = Source(fid)
    an = read_csv('aesa/annual.csv')
    mc = read_csv('aesa/montecarlo_annual.csv')
    res = read_json('aesa/results.json')
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 72), gridspec_kw=dict(width_ratios=[1.6, 1]))
    r = an[(an['scenario'] == REF) & (an['year'] >= WINDOW[0])]
    m = mc[(mc['scenario'] == REF) & (mc['year'] >= WINDOW[0])]
    a.fill_between(m['year'], m['I_sec_kgCO2e_p5'] / M6, m['I_sec_kgCO2e_p95'] / M6, label='Monte Carlo 5–95%',
                   **S.MC_BAND)
    st = dict(S.SCENARIO[REF])
    lab = st.pop('label')
    a.plot(r['year'], r['I_sec_kgCO2e'] / M6, label=f'{lab} (embodied carbon)', **st)
    P.boundary_lines(a, r['year'], r['B_AR_kgCO2e'] / M6, r['B_AtP_kgCO2e'] / M6)
    a.set_yscale('log')
    a.set_xlim(WINDOW[0], WINDOW[1])
    a.set_ylabel('Embodied carbon and boundaries (kt CO₂e per year, log scale)')
    P.log_ticks(a.yaxis, (20, 50, 100, 200, 500, 1000, 2000, 5000))
    P.panel_label(a, 'a')
    src.add('a', 'Reference', r['year'], r['I_sec_kgCO2e'] / M6, 'kt CO2e per year')
    src.add('a', 'Monte Carlo 5%', m['year'], m['I_sec_kgCO2e_p5'] / M6, 'kt CO2e per year')
    src.add('a', 'Monte Carlo 95%', m['year'], m['I_sec_kgCO2e_p95'] / M6, 'kt CO2e per year')
    src.add('a', N.METRICS['AR'] + ' boundary', r['year'], r['B_AR_kgCO2e'] / M6, 'kt CO2e per year')
    src.add('a', N.METRICS['AtP'] + ' boundary', r['year'], r['B_AtP_kgCO2e'] / M6, 'kt CO2e per year')
    # (b) cumulative LoE by principle and variant, Monte Carlo 5-95%
    for i, k in enumerate(VARIANTS):
        y = len(VARIANTS) - 1 - i
        for j, (key, colour, mk) in enumerate((('AR', S.AR, 'o'), ('AtP', S.ATP, 's'))):
            v = res['deterministic'][k][f'LoE_{key}']
            lo, hi = res['mc'][k][f'LoE_{key}_p5'], res['mc'][k][f'LoE_{key}_p95']
            yy = y + (0.12 if key == 'AR' else -0.12)
            b.plot([lo, hi], [yy, yy], color=colour, lw=S.LW)
            b.plot(v, yy, marker=mk, color=colour, ms=4, lw=0)
            b.text(hi * 1.08, yy, f'{v:.2f}' if key == 'AR' else f'{v:.1f}', va='center', fontsize=S.FONT_MIN,
                   color=colour)
            src.add('b', f'{N.SCENARIOS[k]}, {key}', 'cumulative 2026-2050', v, 'level of exceedance')
            src.add('b', f'{N.SCENARIOS[k]}, {key}, Monte Carlo 5%', 'cumulative 2026-2050', lo, 'level of exceedance')
            src.add('b', f'{N.SCENARIOS[k]}, {key}, Monte Carlo 95%', 'cumulative 2026-2050', hi, 'level of exceedance')
    b.axvline(1.0, color=S.INK, lw=S.LW_THIN)
    b.set_xscale('log')
    b.set_yticks(range(len(VARIANTS)))
    b.set_yticklabels([N.SCENARIOS[k] for k in reversed(VARIANTS)])
    b.set_ylim(-0.6, len(VARIANTS) - 0.4)
    b.set_xlabel(N.METRICS['cumulative_LoE'] + ' (log scale)')
    b.grid(axis='y', visible=False)
    xl = b.get_xlim()
    b.set_xlim(min(0.8, xl[0]), xl[1] * 1.6)
    P.log_ticks(b.xaxis, (1, 2, 5, 10, 20, 50, 100))
    b.text(1.0, len(VARIANTS) - 0.45, ' LoE = 1: on the boundary', fontsize=S.FONT_MIN, color=S.INK, va='top')
    P.panel_label(b, 'b')
    st_ref = dict(S.SCENARIO[REF])
    handles = [Line2D([0], [0], color=st_ref['color'], lw=st_ref['lw'], ls=st_ref['ls'],
                      label=f"{st_ref['label']} (embodied carbon)"),
               Patch(label='Monte Carlo 5–95% (a: band; b: whiskers)', **{k: v for k, v in S.MC_BAND.items()
                                                                                    if k != 'lw'}),
               Line2D([0], [0], color=S.AR, lw=S.BOUNDARY['AR']['lw'], ls=S.BOUNDARY['AR']['ls'], marker='o', ms=4,
                      label=S.BOUNDARY['AR']['label']),
               Line2D([0], [0], color=S.ATP, lw=S.BOUNDARY['AtP']['lw'], ls=S.BOUNDARY['AtP']['ls'], marker='s',
                      ms=4, label=S.BOUNDARY['AtP']['label'])]
    fig.legend(handles=handles, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, fid, src)
    d = res['deterministic'][REF]
    num = dict(loe_ar=d['LoE_AR'], loe_atp=d['LoE_AtP'], ar_p5=res['mc'][REF]['LoE_AR_p5'],
               ar_p95=res['mc'][REF]['LoE_AR_p95'], atp_p5=res['mc'][REF]['LoE_AtP_p5'],
               atp_p95=res['mc'][REF]['LoE_AtP_p95'])
    cap = (fill('H5', **num) + f" Monte Carlo 5–95%: AR {num['ar_p5']:.2f}–{num['ar_p95']:.2f}, AtP "
           f"{num['atp_p5']:.1f}–{num['atp_p95']:.1f}; the AR boundary of each draw follows its population path and "
           'its case-study carbon factors (2025 technology), the AtP boundary its population path. Boundaries: 2 °C '
           'carrying capacity (Bjørn & Hauschild 2015) allocated by acquired rights (Horup et al. 2025) and ability '
           'to pay (Hjalsted et al. 2021).')
    return dict(num, caption=cap)


# ============================================================
# H6  Lock-in: emissions committed after 2050
# ============================================================
def h6():
    fid = PLAN['H6']['file']
    src = Source(fid)
    sc = read_json('baseline/scenarios.json')['scenarios']
    res = read_json('aesa/results.json')
    com = res['committed']
    bud = res['reference_2026_2050']
    fig, ax = plt.subplots(figsize=S.figsize('double', 72))
    w = 0.34
    for i, k in enumerate(VARIANTS):
        s, c = sc[k], com[k]
        mat = s['upfront_kt'] - s['soil_carbon_loss_kt']
        maint = s['carbon_kt'] - s['upfront_kt']
        if not math.isclose(maint, c['maintenance_kt_sum_of_annual'], rel_tol=1e-9):
            raise SystemExit(f'H6: maintenance of {k} differs between the scenario and AESA files.')
        bottom = 0.0
        for cid, v in (('materials_construction', mat), ('soil', s['soil_carbon_loss_kt']), ('maintenance', maint)):
            colour, hatch = S.COMPONENT[cid]
            ax.bar(i - w / 2 - 0.02, v, bottom=bottom, width=w, color=colour, hatch=hatch, edgecolor='white',
                   lw=S.LW_THIN, label=N.COMPONENTS[cid] if i == 0 else None)
            src.add('within 2026-2050', N.COMPONENTS[cid], N.SCENARIOS[k], v, 'kt CO2e')
            bottom += v
        ax.text(i - w / 2 - 0.02, bottom, P.fmt_kt(bottom), ha='center', va='bottom', fontsize=S.FONT_SMALL)
        colour, hatch = S.COMPONENT['committed']
        ax.bar(i + w / 2 + 0.02, c['lower_kt'], width=w, facecolor='white', edgecolor=S.MUTED, hatch=hatch,
               lw=S.LW_THIN, label=N.COMPONENTS['committed'] + ', lower bound (2050 factors held)' if i == 0 else None)
        ax.bar(i + w / 2 + 0.02, c['upper_kt'] - c['lower_kt'], bottom=c['lower_kt'], width=w, facecolor=colour,
               edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN, alpha=0.5,
               label='range to the upper bound (2025 factors)' if i == 0 else None)
        ax.text(i + w / 2 + 0.02, c['upper_kt'], f"{c['lower_kt']:,.0f}–{c['upper_kt']:,.0f}\n"
                f"({c['years_of_B_AR_2050_lower']:.0f}–{c['years_of_B_AR_2050_upper']:.0f} yr of the\n2050 AR "
                'boundary)', ha='center', va='bottom', fontsize=S.FONT_MIN)
        src.add('after 2050', 'Committed, lower', N.SCENARIOS[k], c['lower_kt'], 'kt CO2e')
        src.add('after 2050', 'Committed, upper', N.SCENARIOS[k], c['upper_kt'], 'kt CO2e')
        src.add('after 2050', 'Committed, lower, years of the 2050 AR boundary', N.SCENARIOS[k],
                c['years_of_B_AR_2050_lower'], 'years')
        src.add('after 2050', 'Committed, upper, years of the 2050 AR boundary', N.SCENARIOS[k],
                c['years_of_B_AR_2050_upper'], 'years')
    # the budgets are cumulative 2026-2050: drawn across the 2026-2050 bars only (the committed
    # emissions fall after 2050 and are not compared with them)
    import figaudit
    handles, labels = ax.get_legend_handles_labels()
    for key, v in (('AR', bud['B_AR_kt']), ('AtP', bud['B_AtP_kt'])):
        st = dict(S.BOUNDARY[key])
        lab = st.pop('label')
        for i in range(len(VARIANTS)):
            xc = i - w / 2 - 0.02
            ax.plot([xc - 0.62 * w, xc + 0.62 * w], [v, v], gid=figaudit.BOUNDARY, solid_capstyle='butt', zorder=4, **st)
        handles.append(Line2D([0], [0], **st))
        labels.append(f'{lab} budget 2026–2050: {v:,.0f} kt')
        src.add('budgets', f'{lab} budget 2026-2050', 'cumulative', v, 'kt CO2e')
    ax.set_xticks(range(len(VARIANTS)))
    ax.set_xticklabels([f'{N.SCENARIOS[k]}\n2026–2050 | after 2050' for k in VARIANTS])
    ax.set_ylabel('Embodied carbon (kt CO₂e)')
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.set_ylim(0, max(max(sc[k]['carbon_kt'], com[k]['upper_kt']) for k in VARIANTS) * 1.08)
    ax.grid(axis='x', visible=False)
    order = [0, 1, 2, 3, 4, 5, 6]
    fig.legend([handles[k] for k in order], [labels[k] for k in order], loc='lower center', ncol=3,
               bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    save(fig, fid, src)
    c = com[REF]
    num = dict(com_lo=c['lower_kt'], com_hi=c['upper_kt'], yrs_lo=c['years_of_B_AR_2050_lower'],
               yrs_hi=c['years_of_B_AR_2050_upper'], budget_ar=bud['B_AR_kt'], budget_atp=bud['B_AtP_kt'],
               carbon_ref=sc[REF]['carbon_kt'])
    cap = (fill('H6', **num) + ' Committed: replacements and repaints (B2, B4) after 2050 and the end of life '
           '(C1–C4) of the 2026–2050 cohorts; lower bound with the 2050 factors held, upper bound at 2025 factors; '
           'not part of the level of exceedance 2026–2050. Short lines over the 2026–2050 bars: the cumulative AR and '
           'AtP budgets 2026–2050 (the committed emissions fall after 2050 and are not compared with them).')
    return dict(num, caption=cap)


# ============================================================
# H7  What each pathway removes, by demand band
# ============================================================
H7_RUNS = [REF] + [f'P{k}-moderate' for k in range(1, 6)] + ['TL']


def h7():
    fid = PLAN['H7']['file']
    src = Source(fid)
    bd = read_csv('pathways/bands.csv')
    runs = read_csv('pathways/runs.csv')
    bd = bd[(bd['scenario'] == REF) & (bd['definition'] == 'in_scope')]
    r = runs[runs['scenario'] == REF].set_index('run')
    fig, axes = plt.subplots(1, 2, figsize=S.figsize('double', 80))
    import textwrap
    xt = ([N.SCENARIOS[REF]] + [f'P{k}\n' + textwrap.fill(N.PATHWAYS[f'P{k}'], 11) for k in range(1, 6)]
          + ['TL\nTheoretical\nlimit'])
    for ax, col, unit, letter in ((axes[0], 'floor_area_Mm2', 'Mm2', 'a'), (axes[1], 'carbon_kt', 'kt CO2e', 'b')):
        ids = [b for b in N.BANDS_IN_SCOPE if not (col == 'floor_area_Mm2' and b == 'maintenance')]
        for i, run in enumerate(H7_RUNS):
            d = bd[bd['run'] == run].set_index('band')
            parts = [(b, float(d.loc[N.band_data_label(b), col])) for b in ids]
            up, dn = P.signed_stack(ax, [i], parts, width=0.64)
            for b, v in parts:
                src.add(letter, f'{run}: {N.BANDS[b]}', run, v, unit)
            net = float(up[0] + dn[0])
            ax.text(i, up[0], P.fmt_kt(net) if col == 'carbon_kt' else f'{net:.1f}', ha='center', va='bottom',
                    fontsize=S.FONT_MIN)
            if run.startswith('P'):
                amb = run.replace('moderate', 'ambitious')
                v = float(bd[bd['run'] == amb][col].sum())
                ax.plot([i + 0.38], [v], marker='_', ms=7, mew=S.LW_BOLD, color=S.INK, lw=0)
                ax.plot([i + 0.38, i + 0.38], [net, v], color=S.INK, lw=S.LW_THIN)
                src.add(letter, f'{amb}: total', amb, v, unit)
                if not math.isclose(v, r.loc[amb, 'floor_area_Mm2' if col == 'floor_area_Mm2' else 'carbon_kt'],
                                    rel_tol=1e-9):
                    raise SystemExit(f'H7: the bands of {amb} do not add up to its total.')
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
        ax.set_xticks(range(len(H7_RUNS)))
        ax.set_xticklabels(xt, fontsize=S.FONT_MIN)
        ax.set_ylabel('Floor area 2026–2050 (Mm²)' if col == 'floor_area_Mm2' else 'Embodied carbon 2026–2050 (kt CO₂e)')
        if col == 'carbon_kt':
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
        ax.grid(axis='x', visible=False)
        P.panel_label(ax, letter)
    P.band_legend(fig, list(N.BANDS_IN_SCOPE), ncol=4, y=-0.01,
                extra=[Line2D([0], [0], color=S.INK, marker='_', ms=7, mew=S.LW_BOLD, lw=S.LW_THIN,
                              label='Ambitious total (bars: Moderate)')])
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    save(fig, fid, src)
    num = {run: dict(floor_area=r.loc[run, 'floor_area_Mm2'], carbon=r.loc[run, 'carbon_kt'],
                     d_carbon=r.loc[run, 'delta_carbon_kt_vs_reference_pct'])
           for run in H7_RUNS + [f'P{k}-ambitious' for k in range(1, 6)]}
    cap = (fill('H7') + f" P5 Combined lowers carbon 2026–2050 by {-num['P5-moderate']['d_carbon']:.0f}% "
           f"(Moderate) to {-num['P5-ambitious']['d_carbon']:.0f}% (Ambitious) against the Reference; TL by "
           f"{-num['TL']['d_carbon']:.0f}%. Bars: Moderate setting; whiskers: Ambitious totals. Untargeted bands "
           '(grey, dotted) are not acted on by any pathway; negative bands (below zero) release existing dwellings.')
    return dict(runs=num, caption=cap)


# ============================================================
# H8  Annual emissions 2026-2050 against the boundaries
# ============================================================
H8_RUNS = [(REF, S.REFERENCE, '-', S.LW_BOLD), ('P5-moderate', S.PATHWAY['P5'], '-', S.LW),
           ('P5-ambitious', S.PATHWAY['P5'], '--', S.LW), ('TL', S.TL, '-', S.LW),
           ('TL-gradual', S.TL_GRADUAL, '-', S.LW)]


def h8():
    fid = PLAN['H8']['file']
    src = Source(fid)
    an = read_csv('pathways/annual.csv')
    an = an[an['scenario'] == REF]
    fig, ax = plt.subplots(figsize=S.figsize('double', 72))
    ends = []
    for run, colour, ls, lw in H8_RUNS:
        d = an[an['run'] == run]
        ax.plot(d['year'], d['carbon_kt'], color=colour, ls=ls, lw=lw, label=N.run_label(run))
        src.add('a', N.run_label(run), d['year'], d['carbon_kt'], 'kt CO2e per year')
        ends.append((float(d['carbon_kt'].iloc[-1]), N.run_label(run).split(',')[0] if run.startswith('TL') else
                     N.run_label(run).replace('P5 Combined', 'P5'), colour))
    d0 = an[an['run'] == REF]
    P.boundary_lines(ax, d0['year'], d0['B_AR_kt'], d0['B_AtP_kt'])
    src.add('a', N.METRICS['AR'] + ' boundary', d0['year'], d0['B_AR_kt'], 'kt CO2e per year')
    src.add('a', N.METRICS['AtP'] + ' boundary', d0['year'], d0['B_AtP_kt'], 'kt CO2e per year')
    ax.set_xlim(WINDOW[0], WINDOW[1])
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(loc='upper right', ncol=2)
    fig.tight_layout()
    save(fig, fid, src)
    a50 = {run: float(an[(an['run'] == run) & (an['year'] == WINDOW[1])]['carbon_kt'].iloc[0]) for run, *_ in H8_RUNS}
    ar50 = float(d0[d0['year'] == WINDOW[1]]['B_AR_kt'].iloc[0])
    num = dict(carbon_2050=a50, B_AR_2050=ar50, B_AtP_2050=float(d0[d0['year'] == WINDOW[1]]['B_AtP_kt'].iloc[0]))
    cap = (fill('H8') + f" In 2050 the Reference emits {a50[REF]:,.0f} kt, P5 Ambitious {a50['P5-ambitious']:,.0f} kt "
           f"and TL {a50['TL']:,.0f} kt against an AR boundary of {ar50:,.0f} kt. 2026 is observed and identical in "
           'every run; the pathways follow the adopted logistic adoption path (full roll-out by 2035), TL is at full '
           'strength from 2027 (TL, gradual adoption: on the adopted path).')
    return dict(num, caption=cap)


# ============================================================
# H9  From the Reference to P5 Ambitious and TL (order-free attribution)
# ============================================================
def h9():
    fid = PLAN['H9']['file']
    src = Source(fid)
    runs = read_csv('pathways/runs.csv')
    r = runs[runs['scenario'] == REF].set_index('run')
    sp = read_csv('pathways/shapley_pathways.csv')
    sp = sp[sp['metric'] == 'carbon_kt'].set_index(['setting', 'player'])['reduction']
    st = read_csv('pathways/shapley_theoretical_limit.csv')
    st = st[st['metric'] == 'carbon_kt'].set_index('player')['reduction']
    tl = read_json('pathways/theoretical_limit.json')
    steps = [('P1', f"P1 {N.PATHWAYS['P1']}", sp[('ambitious', 'P1')], sp[('moderate', 'P1')], S.PATHWAY['P1']),
             ('P2', f"P2 {N.PATHWAYS['P2']}", sp[('ambitious', 'P2')], sp[('moderate', 'P2')], S.PATHWAY['P2']),
             ('P3', f"P3 {N.PATHWAYS['P3']}", sp[('ambitious', 'P3')], sp[('moderate', 'P3')], S.PATHWAY['P3']),
             ('P4', f"P4 {N.PATHWAYS['P4']}", sp[('ambitious', 'P4')], sp[('moderate', 'P4')], S.PATHWAY['P4'])]
    ref, p5a, p5m, tlr = (float(r.loc[k, 'carbon_kt']) for k in (REF, 'P5-ambitious', 'P5-moderate', 'TL'))
    if not math.isclose(ref - sum(s[2] for s in steps), p5a, rel_tol=1e-12):
        raise SystemExit('H9: the pathway Shapley values do not add up to Reference - P5 Ambitious.')
    tl_steps = [(f'TL{k}', f"TL{k} {N.TL[f'TL{k}']}", st[f'TL{k}'], None, S.TL) for k in range(1, 7)]
    f27 = float(st['from2027'])
    if not math.isclose(p5a - f27 - sum(s[2] for s in tl_steps), tlr, rel_tol=1e-12):
        raise SystemExit('H9: P5 Ambitious - full strength from 2027 - TL1..TL6 does not reach TL.')
    fig, ax = plt.subplots(figsize=S.figsize('double', 96))
    x, labels, prev = 0, [], ref
    w = 0.66

    def total(xx, v, colour, label):
        ax.bar(xx, v, width=w, color=colour, edgecolor='white')
        ax.text(xx, v, P.fmt_kt(v), ha='center', va='bottom', fontsize=S.FONT_SMALL)
        labels.append(label)
        src.add('cascade', label, 'total', v, 'kt CO2e, 2026-2050')

    def step(xx, start, red, colour, label, moderate=None):
        ax.bar(xx, -red, bottom=start, width=w, color=colour, edgecolor='white')
        ax.plot([xx - 1 + w / 2, xx - w / 2], [start, start], color=S.MUTED, lw=S.LW_THIN)
        ax.text(xx, min(start, start - red), f'−{red:,.0f}' if red >= 0 else f'+{-red:,.0f}', ha='center',
                va='top', fontsize=S.FONT_MIN)
        if moderate is not None:
            ax.plot(xx, start - moderate, marker='o', mfc='white', mec=S.INK, ms=3.5, lw=0, mew=S.LW_THIN)
            src.add('cascade', label + ' (Moderate, from the same level)', 'reduction', moderate, 'kt CO2e')
        labels.append(label)
        src.add('cascade', label, 'reduction', red, 'kt CO2e')

    total(x, ref, S.REFERENCE, N.SCENARIOS[REF])
    for _, lab, amb, mod, colour in steps:
        x += 1
        step(x, prev, amb, colour, lab, mod)
        prev -= amb
    x += 1
    total(x, p5a, S.PATHWAY['P5'], 'P5 Combined,\nAmbitious')
    ax.plot(x, p5m, marker='o', mfc='white', mec=S.INK, ms=3.5, lw=0, mew=S.LW_THIN)
    src.add('cascade', 'P5 Combined, Moderate', 'total', p5m, 'kt CO2e, 2026-2050')
    x += 1
    step(x, p5a, f27, S.TL_GRADUAL, N.ADOPTION['from2027'].capitalize())
    prev = p5a - f27
    for _, lab, red, _, colour in tl_steps:
        x += 1
        step(x, prev, red, '#7A7A7A', lab)
        prev -= red
    x += 1
    total(x, tlr, S.TL, 'TL Theoretical\nlimit')
    x_last = x
    # committed after 2050: companion bars right of a divider
    colour, hatch = S.COMPONENT['committed']
    xc = x_last + 1.6
    ax.axvline(xc - 0.8, color=S.MUTED, lw=S.LW_THIN, ls=':')
    for k, (run, lab) in enumerate(((REF, N.SCENARIOS[REF]), ('P5-ambitious', 'P5 Ambitious'), ('TL', 'TL'))):
        xx = xc + k
        lo, hi = float(r.loc[run, 'committed_lower_kt']), float(r.loc[run, 'committed_upper_kt'])
        ax.bar(xx, lo, width=w, facecolor='white', edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN)
        ax.bar(xx, hi - lo, bottom=lo, width=w, facecolor=colour, edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN,
               alpha=0.5)
        ax.text(xx, hi, f'{lo:,.0f}–\n{hi:,.0f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
        labels.append(f'{lab}\ncommitted\nafter 2050')
        src.add('committed after 2050', lab + ', lower', 'after 2050', lo, 'kt CO2e')
        src.add('committed after 2050', lab + ', upper', 'after 2050', hi, 'kt CO2e')
    import figaudit
    for key in ('AR', 'AtP'):
        v = float(r.loc[REF, f'B_{key}_kt'])
        stl = dict(S.BOUNDARY[key])
        lab = stl.pop('label')
        ax.plot([-0.5, x_last + 0.5], [v, v], gid=figaudit.BOUNDARY, **dict(stl, lw=S.LW))
        ax.text(x_last + 0.5, v, f' {key} budget\n {v:,.0f}', va='center', ha='left', fontsize=S.FONT_MIN,
                color=stl['color'])
        src.add('budgets', f'{lab} budget 2026-2050', 'cumulative', v, 'kt CO2e')
    g = tl['gap']['TL']
    if not g['within_AR']:
        rs = g['residual']
        ax.annotate(f"TL still exceeds the AR budget (LoE AR {g['LoE_AR']:.2f}): reaching it means\n"
                    f"{rs['dwellings_not_built_2027_2050']:,.0f} dwellings not built in 2027–2050, i.e. "
                    f"{rs['new_residents_housed_in_existing_dwellings']:,.0f}\nnew residents housed in existing "
                    'dwellings', xy=(x_last, tlr), xytext=(x_last - 6.6, ref * 0.80), fontsize=S.FONT_SMALL,
                    color=S.INK, va='bottom', arrowprops=dict(arrowstyle='-', color=S.MUTED, lw=S.LW_THIN,
                                                              shrinkA=2, shrinkB=4))
    ax.set_xticks(list(range(x_last + 1)) + [xc, xc + 1, xc + 2])
    ax.set_xticklabels(labels, fontsize=S.FONT_MIN, rotation=90)
    ax.set_xlim(-0.6, xc + 2.6)
    ax.set_ylim(0, ref * 1.07)
    ax.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(axis='x', visible=False)
    ax.legend(handles=[Line2D([0], [0], marker='o', mfc='white', mec=S.INK, ms=3.5, lw=0, mew=S.LW_THIN,
                              label='Moderate (step from the same level; P5 Moderate total)'),
                       Patch(facecolor='white', edgecolor=S.MUTED, hatch=hatch, label=N.COMPONENTS['committed'])],
              loc='upper right')
    fig.tight_layout()
    save(fig, fid, src)
    rs = g.get('residual', {})
    num = dict(ref=ref, p5a=p5a, p5m=p5m, tl=tlr, from2027=f27, loe_ar_tl=g['LoE_AR'],
               dw=rs.get('dwellings_not_built_2027_2050', float('nan')),
               res=rs.get('new_residents_housed_in_existing_dwellings', float('nan')),
               cut=g.get('backcast', {}).get('cut_AR', float('nan')))
    cap = (fill('H9', **num) + ' Steps: the Shapley value of each pathway (Ambitious bars; open circles: Moderate, '
           'drawn from the same level), the effect of starting P5 Ambitious at full strength in 2027 (a separate '
           'line, not a Shapley player) and the Shapley values of TL1–TL6; the values add up exactly to each '
           f"total. TL needs a further {100 * num['cut']:.1f}% cut of 2027–2050 construction to reach the AR budget.")
    return dict(num, caption=cap)


# ============================================================
# H10  Solution space: demand and intensity
# ============================================================
def bilinear(space):
    """The cumulative LoE on the plane is exactly LoE(d, i) = a + (1 - d)[(1 - i) b + c] (the
    2026 cohort a fixed; the 2027-2050 cohorts' non-soil carbon b and soil carbon c scale with
    the cuts; pathways.scaled_carbon). The three constants are read from the grid and every grid
    cell is checked against them, so the contours below are the data's, not a fit."""
    g = space.set_index(['demand_reduction', 'intensity_reduction'])['LoE_AR']
    a = g.loc[(1.0, 0.0)]
    c = g.loc[(0.0, 1.0)] - a
    b = g.loc[(0.0, 0.0)] - a - c
    f = lambda d, i: a + (1 - d) * ((1 - i) * b + c)
    err = max(abs(f(d, i) - v) / v for (d, i), v in g.items())
    if err > 1e-12:
        raise SystemExit(f'H10: the solution space is not bilinear in the cuts (max relative error {err:.1e}).')
    return f


def h10():
    fid = PLAN['H10']['file']
    src = Source(fid)
    space = read_csv('pathways/solution_space.csv')
    bc = read_json('pathways/backcast.json')
    tl = read_json('pathways/theoretical_limit.json')['solution_space_marker']
    f = bilinear(space)
    from matplotlib.colors import LinearSegmentedColormap, LogNorm
    cmap = LinearSegmentedColormap.from_list('seq', S.SEQUENTIAL)
    norm = LogNorm(vmin=0.25, vmax=5.0)
    marks = bc['solution_space_markers']
    # b: zoom on the pathway markers (TL is far out, in a). P1's effective intensity change is slightly
    # negative, so the zoom extends a little below 0; there the field is the same exact relation f
    # (non-soil carbon of the 2027-2050 cohorts scaled by 1 - i), not an extrapolated fit.
    dm = [100 * m['demand_reduction'] for m in marks]
    im = [100 * m['intensity_reduction'] for m in marks]
    zx = (min(0.0, min(dm)) - 1.0, max(dm) + 3.0)
    zy = (min(0.0, min(im)) - 1.0, max(im) + 2.0)
    fig = plt.figure(figsize=S.figsize('double', 92))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.045], wspace=0.30, left=0.075, right=0.95, bottom=0.30,
                          top=0.95)
    ax, az, cax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
    for a_, letter, (x0, x1), (y0, y1), levels in ((ax, 'a', (0, 100), (0, 100), (1, 2, 3, 5, 10)),
                                                   (az, 'b', zx, zy, (2, 2.5, 3, 3.5, 4, 4.5, 5))):
        dx, dy = np.linspace(x0, x1, 401), np.linspace(y0, y1, 401)
        D, I = np.meshgrid(dx / 100, dy / 100)
        Z = f(D, I)
        pm = a_.pcolormesh(dx, dy, Z, cmap=cmap, norm=norm, shading='auto', rasterized=True)
        lv = [v for v in levels if Z.min() < v < Z.max()]
        cs = a_.contour(100 * D, 100 * I, Z, levels=lv, colors=[S.INK if v == 1 else '#FFFFFF' for v in lv],
                        linewidths=[S.LW_BOLD if v == 1 else S.LW_THIN for v in lv])
        a_.clabel(cs, fmt=lambda v: f'{v:g}', fontsize=S.FONT_MIN)
        for m in marks:
            pw, st_ = m['run'].split('-')
            a_.plot(100 * m['demand_reduction'], 100 * m['intensity_reduction'], marker='o', ms=4 if a_ is ax else 5,
                    mfc=S.PATHWAY[pw] if st_ == 'ambitious' else 'white', mec=S.PATHWAY[pw], mew=S.LW, lw=0,
                    clip_on=False, zorder=5)
        a_.set_xlim(x0, x1)
        a_.set_ylim(y0, y1)
        a_.set_xlabel('Demand reduction:\ncut of 2027–2050 floor area (%)')
        a_.set_ylabel('Intensity reduction:\ncut of non-soil carbon per m² (%)')
        a_.grid(False)
        P.panel_label(a_, letter)
    ax.plot(100 * tl['demand_reduction'], 100 * tl['intensity_reduction'], marker='*', ms=8, mfc=S.TL, mec='white',
            mew=S.LW_THIN, lw=0, zorder=6)
    for p in bc['backcast_points']:
        ax.plot(100 * p['demand_reduction'], 100 * p['intensity_reduction'], marker='D', ms=3.5, mfc=S.INK, mec='white',
                mew=S.LW_THIN, lw=0, clip_on=False, zorder=6)
        src.add('a', p['run'], 'demand reduction', 100 * p['demand_reduction'], '%')
        src.add('a', p['run'], 'intensity reduction', 100 * p['intensity_reduction'], '%')
    ax.add_patch(Rectangle((max(zx[0], 0), max(zy[0], 0)), zx[1] - max(zx[0], 0), zy[1] - max(zy[0], 0), fill=False,
                           ec='white', lw=S.LW, ls='--', zorder=4))
    ax.text(zx[1] + 1, zy[1], 'b', color='white', fontsize=S.FONT_SMALL, fontweight='bold', va='bottom')
    for m in marks + [dict(tl, run='TL')]:
        lab = N.run_label(m['run']).replace('P5 Combined', 'P5')
        src.add('markers', lab, 'demand reduction', 100 * m['demand_reduction'], '%')
        src.add('markers', lab, 'intensity reduction', 100 * m['intensity_reduction'], '%')
        src.add('markers', lab, 'cumulative LoE AR (run)', m['LoE_AR_run'], 'level of exceedance')
        src.add('markers', lab, 'cumulative LoE AR (plane at the coordinates)', m['LoE_AR_on_grid_at_coordinates'],
                'level of exceedance')
    for _, row in space.iterrows():
        src.add('grid', 'cumulative LoE AR', f"{100 * row['demand_reduction']:.0f}% / {100 * row['intensity_reduction']:.0f}%",
                row['LoE_AR'], 'level of exceedance (demand / intensity reduction)')
    pb = az.get_position()
    cax.set_position([pb.x1 + 0.02, pb.y0, 0.014, pb.height])
    cb = fig.colorbar(pm, cax=cax)
    cb.set_label(N.METRICS['cumulative_LoE'] + ', AR (log scale)')
    cb.set_ticks([0.25, 0.5, 1, 2, 3, 5])
    cb.set_ticklabels(['0.25', '0.5', '1', '2', '3', '5'])
    cb.minorticks_off()
    handles = [Line2D([0], [0], marker='o', mfc=S.PATHWAY[pw], mec=S.PATHWAY[pw], lw=0, ms=4,
                      label=f'{pw} {N.PATHWAYS[pw]}') for pw in S.PATHWAY]
    handles += [Line2D([0], [0], marker='o', mfc='white', mec=S.INK, lw=0, ms=4, label='Moderate (open) / Ambitious (filled)'),
                Line2D([0], [0], marker='*', mfc=S.TL, mec='white', lw=0, ms=8, label='TL Theoretical limit (a)'),
                Line2D([0], [0], marker='D', mfc=S.INK, mec='white', lw=0, ms=3.5, label='Back-cast to LoE AR = 1 (a)'),
                Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label='LoE AR = 1')]
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), frameon=False)
    save(fig, fid, src)
    num = dict(tl_demand=100 * tl['demand_reduction'], tl_intensity=100 * tl['intensity_reduction'],
               p5a_demand=100 * [m for m in marks if m['run'] == 'P5-ambitious'][0]['demand_reduction'],
               p5a_intensity=100 * [m for m in marks if m['run'] == 'P5-ambitious'][0]['intensity_reduction'],
               cut_ref=100 * bc[REF]['cut_AR'])
    cap = (fill('H10') + f" Cutting 2027–2050 construction alone by {num['cut_ref']:.1f}% would bring the Reference "
           f"to LoE AR = 1 (back-cast); P5 Ambitious sits at {num['p5a_demand']:.0f}% demand and "
           f"{num['p5a_intensity']:.0f}% intensity reduction, TL at {num['tl_demand']:.0f}% and "
           f"{num['tl_intensity']:.0f}% (at these coordinates the plane reads LoE AR {tl['LoE_AR_on_grid_at_coordinates']:.2f}; "
           f"the TL run, with its lower soil carbon, {tl['LoE_AR_run']:.2f}). b: zoom on the pathway markers (dashed box in "
           "a); P1's effective intensity change is slightly negative, so b extends just below 0 on the same relation. "
           'Contours: the exact bilinear LoE of the plane, read from the 5% grid '
           '(outputs/data/pathways/solution_space.csv).')
    return dict(num, caption=cap)


# ============================================================
# H11  What moves the cumulative level of exceedance
# ============================================================
# AESA sensitivity rows that duplicate a one-at-a-time model-input row (same run, same boundaries):
# used only to check the conversion of the model-input rows, not drawn twice
AESA_DUPLICATES = {'vi_frozen': 'Frozen technology: 2025 factors held (no decarbonisation)',
                   'vii_proxies_held': 'Decarbonisation: proxy-mapped items held at 2025',
                   'viii_nz_elec_held': 'Decarbonisation: NZ-made electricity-intensive items held at 2025',
                   'ix_a45_held': 'A4-A5 held at 2025 (no generic 1%/yr)',
                   'x_a45_item': "A4-A5 on each item's own Horup path",
                   'xi_event_timing': 'Event timing: interval L / n'}
AESA_NOT_DRAWN = ('reference', 'xii_whole_life', 'note_soil_long_run')   # accounting convention; a note row


def h11_rows():
    """Every candidate row of H11 with its cumulative LoE AR and AtP 2026-2050:
    - model-input rows (one-at-a-time, data/baseline/sensitivity_one_at_a_time.csv): the boundaries
      do not depend on these inputs (they depend on the population path and the AESA method only),
      so LoE = Reference LoE x carbon / Reference carbon exactly, with the adopted boundaries, as the
      AESA sensitivity rows of the same runs (checked against them, 1e-9);
    - population 5th / 95th (data/aesa/results.json, population_paths): carbon and boundaries both
      follow the path (the one-at-a-time population rows are not used: their carbon is floor area x
      the mix intensity of the median run, an approximation);
    - AESA-method rows (data/aesa/sensitivity.csv): carrying capacity, base window, population
      source, GDP measure, s_sec, alpha, scope."""
    import re
    import Sensitivity
    import boundaries
    oat = read_csv('baseline/sensitivity_one_at_a_time.csv')
    aes = read_csv('aesa/sensitivity.csv').set_index('case')
    res = read_json('aesa/results.json')
    ref = res['deterministic'][REF]
    c0 = float(oat[oat['group'] == 'Reference']['carbon_kt'].iloc[0])
    if not math.isclose(c0, ref['I_kt'], rel_tol=1e-12):
        raise SystemExit('H11: the one-at-a-time Reference carbon differs from the AESA Reference.')
    rows = []
    for _, r in oat.iterrows():
        if r['group'] in ('Reference', 'Population'):
            continue
        k = r['carbon_kt'] / c0
        rows.append(dict(case=r['case'], parameter=Sensitivity.PARAMETER.get(r['case'], r['case']),
                         kind='model input', LoE_AR=ref['LoE_AR'] * k, LoE_AtP=ref['LoE_AtP'] * k,
                         source='data/baseline/sensitivity_one_at_a_time.csv'))
    by_case = {x['case']: x for x in rows}
    for case, lab in AESA_DUPLICATES.items():
        if case in aes.index and lab in by_case:
            for key in ('AR', 'AtP'):
                a, b = by_case[lab][f'LoE_{key}'], aes.loc[case, f'cum_LoE_{key}']
                if not math.isclose(a, b, rel_tol=1e-9):
                    raise SystemExit(f'H11: {lab} converted ({a}) differs from the AESA row {case} ({b}).')
    for p in ('5th', '95th'):
        pp = res['population_paths'][p]
        rows.append(dict(case=f'Population: Stats NZ {p} percentile (carbon and boundaries)', parameter='Population',
                         kind='model input', LoE_AR=pp['LoE_AR'], LoE_AtP=pp['LoE_AtP'],
                         source='data/aesa/results.json (population_paths)'))
    for case, r in aes.iterrows():
        if case in AESA_NOT_DRAWN or case in AESA_DUPLICATES:
            continue
        rows.append(dict(case=re.sub(r'^\([ivx]+\)\s*', '', r['label']), parameter=boundaries.PB_PARAMETER.get(case, case),
                         kind='AESA method', LoE_AR=r['cum_LoE_AR'], LoE_AtP=r['cum_LoE_AtP'],
                         source='data/aesa/sensitivity.csv'))
    d = pd.DataFrame(rows)
    d['AR_vs_ref_pct'] = 100 * (d['LoE_AR'] / ref['LoE_AR'] - 1)
    d['AtP_vs_ref_pct'] = 100 * (d['LoE_AtP'] / ref['LoE_AtP'] - 1)
    return d, ref


def h11():
    fid = PLAN['H11']['file']
    src = Source(fid)
    d, ref = h11_rows()
    par = dict(zip(d['case'], d['parameter']))
    import Sensitivity
    import textwrap
    top = Sensitivity.top_parameters(d, TOP_N_H11, label='case', parameter=par, cols=('AR_vs_ref_pct',))
    # one group per parameter (its rows side by side), the parameter with the largest effect at the top
    top = top.assign(param=top['case'].map(par), eff=top['AR_vs_ref_pct'].abs())
    rank = top.groupby('param')['eff'].max().sort_values(ascending=False)
    top = pd.concat([top[top['param'] == p_].sort_values('LoE_AR') for p_ in rank.index])
    ys, y, prev = [], 0.0, None
    for p_ in top['param']:
        if prev is not None:
            y -= 1.0 if p_ == prev else 1.6
        ys.append(y)
        prev = p_
    ys = np.array(ys)
    fig, ax = plt.subplots(figsize=S.figsize('double', 26 + 4.6 * len(top)))
    x0 = ref['LoE_AR']
    for yi, (_, r) in zip(ys, top.iterrows()):
        method = r['kind'] == 'AESA method'
        ax.barh(yi, r['LoE_AR'] - x0, left=x0, height=0.72, color=S.AR if method else S.REFERENCE,
                hatch='////' if method else None, edgecolor='white', lw=S.LW_THIN)
        ax.text(r['LoE_AR'] + (0.02 if r['LoE_AR'] >= x0 else -0.02) * x0, yi,
                f"{r['LoE_AR']:.2f} ({r['AR_vs_ref_pct']:+.0f}%)", va='center',
                ha='left' if r['LoE_AR'] >= x0 else 'right', fontsize=S.FONT_MIN)
    for _, r in d.iterrows():
        src.add('a', r['case'], r['kind'], r['LoE_AR'], 'cumulative LoE AR 2026-2050')
        src.add('a', r['case'], r['kind'] + ' (AtP)', r['LoE_AtP'], 'cumulative LoE AtP 2026-2050')
    src.add('a', 'Reference', 'reference', x0, 'cumulative LoE AR 2026-2050')
    ax.axvline(x0, color=S.INK, lw=S.LW)
    ax.set_yticks(ys)
    ax.set_yticklabels([textwrap.fill(c, 62) for c in top['case']], fontsize=S.FONT_SMALL, linespacing=1.0)
    lo, hi = top['LoE_AR'].min(), top['LoE_AR'].max()
    pad = 0.18 * (hi - lo)
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(ys.min() - 0.7, ys.max() + 0.7)
    ax.set_xlabel(f"{N.METRICS['cumulative_LoE']}, AR (Reference {x0:.2f})")
    ax.grid(axis='y', visible=False)
    fig.legend(handles=[Patch(facecolor=S.REFERENCE, label='Model input (boundaries as adopted; population: carbon '
                                                           'and boundaries)'),
                        Patch(facecolor=S.AR, hatch='////', edgecolor='white', label='AESA method')],
               loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, fid, src)
    big = top.loc[top.groupby('param')['eff'].idxmax()].sort_values('eff', ascending=False).head(3)
    num = dict(ref=x0, top=[(r['case'], r['LoE_AR'], r['AR_vs_ref_pct']) for _, r in big.iterrows()],
               pop={p_: float(d[d['case'].str.startswith(f'Population: Stats NZ {p_}')]['LoE_AR'].iloc[0])
                    for p_ in ('5th', '95th')})
    cap = (fill('H11') + f" The {TOP_N_H11} parameters with the largest effect on the cumulative LoE AR "
           f"(Reference {x0:.2f}), both ends of a paired parameter shown; every row: "
           f'outputs/headline/{fid}.csv (AtP: D18). Model-input rows hold the boundaries as adopted (the boundaries '
           'depend on the population path and the AESA method only), as the AESA sensitivity rows of the same runs; '
           'the population rows move the carbon and both boundaries together.')
    return dict(num, caption=cap)


# ============================================================
# HEADLINE.md
# ============================================================
def findings(r):
    """The headline findings: one sentence each, with its numbers and the data files they come from."""
    h2, h3, h4, h5, h6, h7, h9, h11_ = (r[k] for k in ('H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H9', 'H11'))
    p5m, p5a, tlr = (h7['runs'][k] for k in ('P5-moderate', 'P5-ambitious', 'TL'))
    runs = read_csv('pathways/runs.csv')
    runs = runs[runs['scenario'] == REF].set_index('run')
    top = ', '.join(f"{p:+.0f}% for '{c}'" for c, _, p in h11_['top'][:-1]) + \
        f" and {h11_['top'][-1][2]:+.0f}% for '{h11_['top'][-1][0]}'"
    return [
        (f"New Zealand builds {h2['gfa_ref']:.1f} million m² of new residential floor area in 2026–2050 in the "
         f"Reference (Monte Carlo 90% interval {h2['gfa_p5']:.1f}–{h2['gfa_p95']:.1f}); the replacement assumption "
         f"brackets it at {h2['gfa_low']:.1f}–{h2['gfa_high']:.1f} million m².",
         'data/baseline/scenarios.json, data/montecarlo/summary_REF.csv'),
        (f"{100 * h3['untargeted_share']:.0f}% of that floor area serves population growth and smaller households, "
         'which no construction pathway targets; the rest is extra space, vacancy, the 2026 overbuild, replacement and '
         'redevelopment.', 'data/baseline/bands_annual.csv'),
        (f"Its embodied carbon is {h4['carbon']:,.0f} kt CO₂e within 2026–2050 (materials and construction "
         f"{h4['materials']:,.0f} kt, soil carbon loss {h4['soil']:,.0f} kt, maintenance {h4['maintenance']:,.0f} kt), "
         f"with a further {h4['com_lo']:,.0f}–{h4['com_hi']:,.0f} kt committed after 2050.",
         'data/baseline/annual.csv, data/baseline/projection.json'),
        (f"This exceeds the sector's share of the 2 °C carrying capacity {h5['loe_ar']:.2f}-fold by acquired rights "
         f"(Monte Carlo {h5['ar_p5']:.2f}–{h5['ar_p95']:.2f}) and {h5['loe_atp']:.1f}-fold by ability to pay "
         f"({h5['atp_p5']:.1f}–{h5['atp_p95']:.1f}); the two principles are reported side by side, never averaged.",
         'data/aesa/results.json'),
        (f"The emissions committed after 2050 by the 2026–2050 cohorts equal {h6['yrs_lo']:.0f}–{h6['yrs_hi']:.0f} "
         'years of the 2050 acquired-rights boundary.', 'data/aesa/results.json'),
        (f"Combining all pathways (P5) lowers carbon 2026–2050 by {-p5m['d_carbon']:.0f}% (Moderate) to "
         f"{-p5a['d_carbon']:.0f}% (Ambitious): the cumulative LoE AR falls from "
         f"{runs.loc[REF, 'LoE_AR']:.2f} to {runs.loc['P5-moderate', 'LoE_AR']:.2f} and "
         f"{runs.loc['P5-ambitious', 'LoE_AR']:.2f}.", 'data/pathways/runs.csv'),
        (f"Even the hyper-optimistic theoretical limit (TL; a thought experiment, not a pathway) exceeds the "
         f"acquired-rights budget (LoE AR {h9['loe_ar_tl']:.2f}); reaching it means not building "
         f"{h9['dw']:,.0f} dwellings in 2027–2050, i.e. housing {h9['res']:,.0f} new residents in existing dwellings.",
         'data/pathways/theoretical_limit.json, data/pathways/runs.csv'),
        (f"Of the one-at-a-time sensitivities, the largest effects on the cumulative LoE AR (Reference "
         f"{h11_['ref']:.2f}) are {top}; the Stats NZ population 5th and 95th percentiles, which move the carbon and "
         f"both boundaries, give {h11_['pop']['5th']:.2f}–{h11_['pop']['95th']:.2f}.",
         f"outputs/headline/{PLAN['H11']['file']}.csv, data/aesa/results.json"),
    ]


def write_md(r):
    lines = ['# Headline findings and figures', '',
         '_Generated by headline.py from outputs/data/ (do not edit by hand). Figures: 183 mm wide (Nature double '
         'column), PNG 300 dpi and vector PDF; the source data of every figure (every plotted value) in the CSV of '
         'the same name. Vocabulary: docs/RENAMING.md; palette: docs/PALETTE.md._', '']
    if quick_run():
        lines += ['> **QUICK RUN, not for reporting** (run_all.py --quick: fewer Monte Carlo draws).', '']
    lines += ['## Findings', '']
    for i, (text, files) in enumerate(findings(r), 1):
        lines.append(f'{i}. {N.typeset(text)} (Source: {files}.)')
    lines += ['', '## Figures', '']
    for h in FP.HEADLINE:
        f = h['file']
        data = f"Data (outputs/): {h['source']}" if h['source'].startswith('data/') else f"Data: {h['source']}"
        lines += [f"### {h['id']}. {N.typeset(h['title'])}", '', f'![{h["id"]}]({f}.png)', '',
                  f"**{h['id']}.** {N.typeset(r[h['id']]['caption'])}", '',
                  f"Files: [{f}.png]({f}.png), [{f}.pdf]({f}.pdf), source data [{f}.csv]({f}.csv). {data}.", '']
    with open(L_path(), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    return lines


def L_path():
    return L.writing(os.path.join(L.HEADLINE, 'HEADLINE.md'))


FIGURES = dict(H1=h1, H2=h2, H3=h3, H4=h4, H5=h5, H6=h6, H7=h7, H8=h8, H9=h9, H10=h10, H11=h11)


def main(only=None):
    r = {}
    for k, fn in FIGURES.items():
        if only and k not in only:
            continue
        r[k] = fn()
        print(f'headline: {k} {PLAN[k]["file"]}')
    if not only:
        write_md(r)
        print(f'headline: {os.path.relpath(L_path(), ROOT)}')
    return r


if __name__ == '__main__':
    main([a for a in sys.argv[1:] if a.startswith('H')] or None)
