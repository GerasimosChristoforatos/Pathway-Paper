"""
PAPER FIGURES AND TABLES (MODEL v2.1.0): Fig1-Fig6, Table 1-2, PAPER.md
======================================================================
Every figure and table is drawn from the data files of outputs/data/ (layout.py) and nothing else:
no model is run here, so a figure can never disagree with the data it shows. Labels come from
naming.py, colours, sizes and saving from style.py (docs/PALETTE.md), titles, panels and draft
captions from figure_plan.py (docs/FIGURE_PLAN_v2.md).

Storyline (docs/FIGURE_PLAN_v2.md section 1): the Reference, P1-P5 at the Moderate setting with full
roll-out by 2035 (named without a setting suffix) and TL. Every other setting is in Extended Data
(extended_data.py) and the diagnostics.

For each figure this writes, in outputs/paper/:
  Fig<n>_<name>.png          300 dpi PNG, 183 mm (double) or 89 mm (single column) wide
  Fig<n>_<name>.pdf / .csv   with run_all.py --export only: the vector PDF and the source data (every plotted
                             value in long format: panel, series, x, value, unit), as Nature's Source Data files
and Table1_levers.md / .csv, Table2_results.md / .csv, and PAPER.md: the headline findings (one
sentence each, with the numbers and the data files they come from), every figure with its caption
(numbers filled from the data) and the tables.

    python paper.py            (run_all.py runs it after the pathway layer and the sensitivity tables)
"""
import json
import math
import os
import sys
import textwrap

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import layout as L  # noqa: E402
import naming as N  # noqa: E402
import plotting as P  # noqa: E402
import style as S  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch, Rectangle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

M6 = 1e6
REF = 'REF'
WINDOW = (2026, 2050)
PLAN = {h['id']: h for h in FP.PAPER}
STORY = [REF, 'P1-moderate', 'P2-moderate', 'P3-moderate', 'P4-moderate', 'P5-moderate', 'TL']
PATHWAY_IDS = ('P1', 'P2', 'P3', 'P4', 'P5')
WIDTH_MM = {'single': 89.0, 'double': 183.0}


# ============================================================
# DATA (outputs/data/ only) AND SAVING
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


def label(run):
    """Paper label of a storyline run: the pathways at Moderate by 2035 carry no setting suffix."""
    if run == REF:
        return N.SCENARIOS[REF]
    if run == 'TL':
        return f"TL {N.TL['TL']}"
    head = run.split('-')[0]
    return f'{head} {N.PATHWAYS[head]}'


def short(run):
    return 'Reference' if run == REF else run.split('-')[0]


def colour(run):
    if run == REF:
        return S.REFERENCE
    if run.startswith('TL'):
        return S.TL
    return S.PATHWAY[run.split('-')[0]]


class Source:
    """Source data of one figure: every plotted value as (panel, series, x, value, unit)."""

    def __init__(self, fid, base):
        self.fid, self.base, self.rows = fid, base, []

    def add(self, panel, series, x, values, unit):
        xs = np.atleast_1d(np.asarray(x, dtype=object))
        vs = np.atleast_1d(np.asarray(values, dtype=float))
        if len(xs) == 1 and len(vs) > 1:
            xs = np.repeat(xs, len(vs))
        if len(xs) != len(vs):
            raise ValueError(f'{self.fid}: {series}: {len(xs)} x values for {len(vs)} values')
        for xi, vi in zip(xs, vs):
            self.rows.append(dict(panel=panel, series=series, x=xi, value=float(vi), unit=unit))

    def write(self):
        pd.DataFrame(self.rows, columns=['panel', 'series', 'x', 'value', 'unit']).to_csv(
            L.writing(os.path.join(self.base, f'{self.fid}.csv')), index=False)


def save(fig, fid, src, width):
    """The figure (style.save_figure: PNG, with its audit record) and, with run_all.py --export
    (style.export_run), its vector PDF and source-data CSV; without --export an earlier PDF / CSV of the figure is
    removed, so no stale export survives. The PNG must print within its Nature width (89 or 183 mm), so a wider
    figure (labels outside the frame) is refused."""
    from PIL import Image
    if S.export_run():
        src.write()
    else:
        for ext in ('pdf', 'csv'):
            old = os.path.join(src.base, f'{fid}.{ext}')
            if os.path.exists(old):
                os.remove(old)
    S.save_figure(fig, fid)
    with Image.open(L.figure(fid) + '.png') as im:
        w_mm = im.size[0] / S.DPI * 25.4
    if w_mm > WIDTH_MM[width] + 1e-6:
        raise SystemExit(f'{fid}: {w_mm:.1f} mm wide; it prints at most {WIDTH_MM[width]:.0f} mm wide.')


def check(cond, msg):
    if not cond:
        raise SystemExit(f'paper: {msg}')


def runs_ref():
    r = read_csv('pathways/runs.csv')
    return r[r['scenario'] == REF].set_index('run')


def mc_summary():
    return read_csv('pathways/montecarlo_summary.csv').set_index(['run', 'quantity'])


def mc_key(run):
    return {REF: 'REF', 'P5-moderate': 'P5', 'TL': 'TL', 'TL-from2027': 'TL_from2027'}[run]


def budget_ratio(r):
    """B_AR / B_AtP of the Reference: every storyline run has the same budgets (the boundaries depend on the
    population path only), so LoE AtP = LoE AR x this ratio exactly (checked)."""
    k = float(r.loc[REF, 'B_AR_kt']) / float(r.loc[REF, 'B_AtP_kt'])
    for run in STORY:
        check(math.isclose(r.loc[run, 'B_AR_kt'], r.loc[REF, 'B_AR_kt'], rel_tol=1e-12), f'{run}: AR budget differs')
        check(math.isclose(r.loc[run, 'LoE_AtP'], r.loc[run, 'LoE_AR'] * k, rel_tol=1e-12), f'{run}: AtP not AR x k')
    return k


# ============================================================
# Fig1  How the model works (structure only; no numbers)
# ============================================================
def fig1(h=None, base=None):
    """Drawn on a millimetre grid of the printed figure (183 x 102 mm), so every box and label is
    placed at its print size. h, base: the plan entry and folder (default Fig1 in outputs/paper/; key_figures.py
    draws K6 with it)."""
    h = h or PLAN['Fig1']
    fid = h['file']
    src = Source(fid, base or L.PAPER)
    W, H = 183.0, 102.0
    fig = plt.figure(figsize=S.figsize('double', H))
    m = 0.6
    ax = fig.add_axes([m / W, m / H, 1 - 2 * m / W, 1 - 2 * m / H])
    ax.set_xlim(m, W - m)
    ax.set_ylim(m, H - m)
    ax.set_axis_off()

    def box(x, y, w, hh, title, sub=''):
        ax.add_patch(FancyBboxPatch((x, y), w, hh, boxstyle='round,pad=0,rounding_size=1.2', fc='white', ec=S.INK,
                                    lw=S.LW_THIN))
        ax.text(x + w / 2, y + hh / 2 + (1.6 if sub else 0), title, ha='center', va='center', fontsize=S.FONT_SIZE,
                fontweight='bold', color=S.INK)
        if sub:
            ax.text(x + w / 2, y + hh / 2 - 2.4, sub, ha='center', va='center', fontsize=S.FONT_SMALL, color=S.INK,
                    linespacing=1.1)

    def arrow(p, q, color=S.INK, lw=S.LW_THIN):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=6, color=color, lw=lw, shrinkA=0,
                                     shrinkB=0))

    def swatch(x, y, face, hatch):
        ax.add_patch(Rectangle((x, y - 1.8), 3.6, 3.6, fc=face, ec='#555555', lw=S.LW_THIN, hatch=hatch))

    def heading(x, y, text, color=S.INK):
        ax.text(x, y, text, fontsize=S.FONT_SMALL, fontweight='bold', color=color, va='center')

    dy = 6.0                                    # everything above the pathway rows sits 6 mm higher than in H1
    chain = [('Population', 'Stats NZ projections'), ('Households', 'household size'),
             ('Dwellings', 'required'), ('Floor area', 'm² per dwelling'),
             ('Embodied carbon', 'A1–A5, soil, B2/B4'), ('Level of exceedance', 'against the boundaries')]
    bw, y0, bh = 26.6, 82.0 + dy, 12.0
    xs = [1.0 + k * (bw + 4.0) for k in range(len(chain))]
    for (t, sub), x in zip(chain, xs):
        box(x, y0, bw, bh, t, sub)
    for xa, xb in zip(xs[:-1], xs[1:]):
        arrow((xa + bw, y0 + bh / 2), (xb, y0 + bh / 2), lw=S.LW)
    xb_, yb = 62.0, 70.0 + dy
    heading(xb_, yb + 5.5, 'Demand bands: why floor area is built')
    heading(1.0, yb + 5.5, 'Pathway levers')
    arrow((xs[2] + bw / 2, y0), (xs[2] + bw / 2, yb + 8.0))
    bands = [('growth', None), ('smaller_households', 'L2'), ('extra_space', 'L1'), ('vacancy', 'L3'),
             ('overbuild_2026', 'L4'), ('replacement', 'L5'), ('redevelopment', 'L5')]
    for k, (bid, lev) in enumerate(bands):
        y = yb - k * 5.6
        face, hatch = S.BAND[bid]
        swatch(xb_, y, face, hatch)
        ax.text(xb_ + 5.2, y, N.BANDS[bid] + (' (untargeted)' if bid in N.UNTARGETED else ''), va='center',
                fontsize=S.FONT_SMALL, color=S.INK)
        if lev:
            pw = [p for p, ls in N.PATHWAY_LEVERS.items() if lev in ls][0]
            if bid != 'redevelopment':
                ax.text(1.0, y, f'{lev} {N.LEVERS[lev]}', va='center', ha='left', fontsize=S.FONT_SMALL,
                        color=S.PATHWAY[pw], fontweight='bold')
                arrow((33.0, y), (xb_ - 1.0, y), color=S.PATHWAY[pw])
            else:
                arrow((33.0, y + 5.6), (xb_ - 1.0, y), color=S.PATHWAY[pw])
        src.add('bands', N.BANDS[bid], 'lever', 0 if lev is None else int(lev[1]), 'lever number (0: untargeted)')
    xc, yc = 117.0, 70.0 + dy
    heading(xc, yc + 5.5, 'Carbon by life-cycle stage')
    arrow((xs[4] + bw / 2, y0), (xs[4] + bw / 2, yc + 8.0))
    for k, sid in enumerate(('a1a3', 'a4a5', 'maintenance', 'soil')):
        y = yc - k * 5.6
        face, hatch = S.STAGE[sid]
        swatch(xc, y, face, hatch)
        ax.text(xc + 5.2, y, N.STAGES[sid], va='center', fontsize=S.FONT_SMALL, color=S.INK)
    # the levers on carbon per m2: L6 -> A1-A3, L7 -> A4-A5, L8 and L9 -> soil carbon loss
    for k, (levs, sid) in enumerate(((('L6',), 'a1a3'), (('L7',), 'a4a5'), (('L8',), 'soil'), (('L9',), 'soil'))):
        y = yc - 4 * 5.6 - 0.6 - k * 4.6
        pw = N.LEVER_PATHWAY[levs[0]]
        ax.text(xc, y, ' + '.join(f'{L_} {N.LEVERS[L_]}' for L_ in levs) + f' → {N.STAGES[sid].split(" (")[0]}',
                fontsize=S.FONT_SMALL, color=S.PATHWAY[pw], fontweight='bold', va='center')
        for L_ in levs:
            src.add('stages', N.STAGES[sid], 'lever', int(L_[1]), 'lever number')
    xa_ = xs[5]
    box(xa_, 54.0 + dy, bw, 15.0, 'AESA boundaries', 'AR: acquired rights\nAtP: ability to pay')
    arrow((xa_ + bw / 2, 69.0 + dy), (xa_ + bw / 2, y0))

    def row(y, items):
        """Labels side by side, each 4 mm after the end of the previous one (measured)."""
        x, r = 1.0, fig.canvas.get_renderer()
        for text, kw in items:
            t = ax.text(x, y, text, fontsize=S.FONT_SMALL, va='center', **kw)
            bb = t.get_window_extent(r).transformed(ax.transData.inverted())
            x = bb.x1 + 4.0
        if x - 4.0 > W - m:
            raise SystemExit('Fig1: a row of labels is wider than the figure.')

    heading(1.0, 32.0, 'Pathways (levers combined; Moderate setting, full roll-out by 2035)')
    row(27.5, [(f"{pw} {N.PATHWAYS[pw]} ({'+'.join(N.PATHWAY_LEVERS.get(pw, ('L1–L9',)))})",
                dict(color=S.PATHWAY[pw], fontweight='bold')) for pw in PATHWAY_IDS])
    heading(1.0, 21.5, 'Theoretical limit TL = P5 with TL1–TL10, each at its limit, adopted by 2030', color=S.TL)
    row(17.0, [(f"TL{k} {N.TL[f'TL{k}']}", dict(color=S.TL)) for k in range(1, 5)])
    row(12.5, [(f"TL{k} {N.TL[f'TL{k}']}", dict(color=S.TL)) for k in range(5, 8)])
    row(8.0, [(f"TL{k} {N.TL[f'TL{k}']}", dict(color=S.TL)) for k in range(8, 11)])
    ax.text(1.0, 3.0, 'TL: ' + N.TL_CAPTION + '.', fontsize=S.FONT_SMALL, color=S.MUTED, style='italic',
            va='center')
    save(fig, fid, src, h['width'])
    return dict(caption=h['caption'])


# ============================================================
# Fig2  Why floor area is built (history and projection; carbon by band)
# ============================================================
def stack_styled(ax, x, parts, width, **kw):
    """signed_stack with explicit styles: parts [(style dict, values)]; positive up, negative down."""
    x = np.atleast_1d(np.asarray(x, float))
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for st, v in parts:
        v = np.atleast_1d(np.asarray(v, float))
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        ax.bar(x, pos, bottom=up, width=width, **dict(st, **kw))
        ax.bar(x, neg, bottom=dn, width=width, **dict(st, **kw))
        up, dn = up + pos, dn + neg
    return up, dn


def unexplained_style():
    face, hatch, edge = S.UNEXPLAINED
    return S.fill(face, hatch, edge)


def bands_history_panel(a, src, letter='a'):
    """Floor area by demand band: history per census interval and the Reference projection (Fig2 a, K1)."""
    ba = read_csv('baseline/bands_annual.csv')
    bh = read_csv('baseline/bands_history.csv')
    sp = read_csv('baseline/bands_history_replacement_split.csv').set_index('interval')
    # (a) history: one column per census interval, the net replacement split into its census-measured part
    # and the unexplained building
    rep_lab = N.band_data_label('replacement_history')
    for iv, g in bh.groupby('interval', sort=False):
        y0, y1 = int(g['year_start'].iloc[0]), int(g['year_end'].iloc[0])
        faint = g['households_from'].iloc[0] != 'census'
        val = lambda bid: float(g[g['band'] == N.band_data_label(bid)]['floor_area_Mm2_per_year'].iloc[0])
        s = sp.loc[iv]
        check(math.isclose(s['net_replacement_census_Mm2_per_year'] + s['unexplained_building_Mm2_per_year'],
                           float(g[g['band'] == rep_lab]['floor_area_Mm2_per_year'].iloc[0]), rel_tol=1e-9, abs_tol=1e-12),
              f'Fig2: the replacement split of {iv} does not add up to the band')
        parts = [(P.band_style(bid), val(bid)) for bid in ('growth', 'smaller_households', 'extra_space', 'vacancy')]
        parts += [(P.band_style('replacement'), s['net_replacement_census_Mm2_per_year']),
                  (unexplained_style(), s['unexplained_building_Mm2_per_year'])]
        stack_styled(a, [y0 - 0.5 + (y1 - y0 + 1) / 2], parts, width=(y1 - y0 + 1) * 0.96,
                     alpha=0.45 if faint else 1.0)
        for bid in ('growth', 'smaller_households', 'extra_space', 'vacancy'):
            src.add(letter, N.BANDS[bid], f'{y0}-{y1}', val(bid), 'Mm2 per year (interval mean)')
        src.add(letter, N.REPLACEMENT_CENSUS, f'{y0}-{y1}', s['net_replacement_census_Mm2_per_year'],
                'Mm2 per year (interval mean)')
        src.add(letter, N.UNEXPLAINED, f'{y0}-{y1}', s['unexplained_building_Mm2_per_year'], 'Mm2 per year (interval mean)')
    years = sorted(ba['year'].unique())
    proj = [b_ for b_ in N.BANDS_IN_SCOPE if b_ != 'maintenance']
    parts = []
    for bid in proj:
        v = ba[ba['band'] == N.band_data_label(bid)].set_index('year').loc[years, 'floor_area_Mm2'].values
        parts.append((bid, v))
        src.add(letter, N.BANDS[bid], years, v, 'Mm2 per year')
    P.signed_stack(a, years, parts, width=0.82)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    P.split(a)
    lo, hi = a.get_ylim()
    a.set_ylim(lo, hi + 0.1 * (hi - lo))
    a.text(2025.0, 0.98, 'History: census intervals ', transform=a.get_xaxis_transform(), ha='right', va='top',
           fontsize=S.FONT_SMALL, color=S.MUTED)
    a.text(2026.0, 0.98, ' Reference', transform=a.get_xaxis_transform(), ha='left', va='top', fontsize=S.FONT_SMALL,
           color=S.MUTED)
    a.set_xlim(1991, 2050.6)
    a.set_ylabel('Floor area (Mm² per year)')
    a.grid(axis='x', visible=False)
    P.panel_label(a, letter)
    return ba


def bands_carbon_panel(b, src, letter='b'):
    """The Reference demand bands as carbon per year, maintenance its own layer (Fig2 b, K2)."""
    ba = read_csv('baseline/bands_annual.csv')
    years = sorted(ba['year'].unique())
    # (b) the Reference bands as carbon, maintenance its own layer
    cparts = []
    for bid in N.BANDS_IN_SCOPE:
        v = ba[ba['band'] == N.band_data_label(bid)].set_index('year').loc[years, 'carbon_kt'].values
        cparts.append((bid, v))
        src.add(letter, N.BANDS[bid], years, v, 'kt CO2e per year')
    up, dn = P.signed_stack(b, years, cparts, width=0.82)
    an = read_csv('baseline/annual.csv')
    an = an[an['source'] == 'projection'].set_index('year')
    check(np.allclose(up + dn, an.loc[years, 'carbon_kt'].values, rtol=1e-9, atol=1e-9),
          'Fig2: the carbon bands do not add up to the annual carbon')
    b.axhline(0, color=S.INK, lw=S.LW_THIN)
    b.set_xlim(2025.4, 2050.6)
    b.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(b.yaxis)
    b.grid(axis='x', visible=False)
    P.panel_label(b, letter)


def fig2():
    h = PLAN['Fig2']
    fid = h['file']
    src = Source(fid, L.PAPER)
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 84), gridspec_kw=dict(width_ratios=[1.75, 1]))
    ba = bands_history_panel(a, src)
    bands_carbon_panel(b, src)
    handles = P.band_handles(['growth', 'smaller_households', 'extra_space', 'vacancy', 'overbuild_2026', 'replacement',
                              'redevelopment', 'maintenance'])
    for hd in handles:
        if hd.get_label() == P.band_label('replacement'):
            hd.set_label(P.band_label('replacement') + ' (history: net, census-measured)')
    handles.append(Patch(label=N.UNEXPLAINED, **dict(unexplained_style())))
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), frameon=False,
               handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    save(fig, fid, src, h['width'])
    tot = ba.groupby('band')[['floor_area_Mm2', 'carbon_kt']].sum()
    unt = sum(tot.loc[N.band_data_label(b_), 'floor_area_Mm2'] for b_ in N.UNTARGETED)
    total = tot['floor_area_Mm2'].sum()
    num = dict(untargeted_share=unt / total, total=total,
               untargeted_carbon_share=sum(tot.loc[N.band_data_label(b_), 'carbon_kt'] for b_ in N.UNTARGETED)
               / tot['carbon_kt'].sum())
    cap = (h['caption'] + f" Over 2026–2050 the untargeted band (population growth) is {100 * num['untargeted_share']:.0f}% of the "
           f"{total:.1f} million m² built (a) and {100 * num['untargeted_carbon_share']:.0f}% of the carbon (b). History "
           '(a): interval means between censuses (vacancy on one definition, the pooled 2018/2023 empty share); the net '
           'replacement is census-measured (the census-interval rate of the dwelling-count identity × the previous '
           "year's stock) and the hatched band is the building that household formation, vacancy and census-measured "
           'replacement leave unexplained (it may be negative); the faint column after the latest census uses '
           'consent-derived households. Retirement villages (out of scope) are removed from every band in proportion. '
           '(b): maintenance (B2, B4) within 2026–2050 is its own layer.')
    return dict(num, caption=cap)


# ============================================================
# Fig3  Embodied carbon of the Reference (stages, materials, committed)
# ============================================================
STAGE_COLS = [('a1a3', 'a1a3_kt'), ('a4a5', 'a4a5_kt'), ('maintenance', 'maintenance_kt'), ('soil', 'soil_carbon_loss_kt')]


def stage_panel(a, src, letter='a'):
    """Annual Reference carbon by life-cycle stage (Fig3 a, K2)."""
    st = read_csv('baseline/annual_by_stage.csv').set_index('year')
    years, cols = st.index.values, STAGE_COLS
    base = np.zeros(len(years))
    for sid, col in cols:
        face, hatch = S.STAGE[sid]
        a.bar(years, st[col].values, bottom=base, width=0.82, **S.fill(face, hatch),
              label=N.STAGES[sid])
        src.add(letter, N.STAGES[sid], years, st[col].values, 'kt CO2e per year')
        base = base + st[col].values
    a.set_xlim(2025.4, 2050.6)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    a.legend(handles=a.get_legend_handles_labels()[0][::-1], loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2,
             fontsize=S.FONT_SMALL)
    P.panel_label(a, letter)


def material_panel(b, src, letter='b'):
    """Annual Reference carbon by material (Fig3 b, K2)."""
    st = read_csv('baseline/annual_by_stage.csv').set_index('year')
    mat = read_csv('baseline/annual_by_material.csv').pivot(index='year', columns='material', values='carbon_kt')
    years = st.index.values
    frame = mat.loc[years]
    handles = P.stack_materials(b, years, frame)
    for code_, lab, _ in S.MATERIAL:
        src.add(letter, lab, years, frame[code_].values, 'kt CO2e per year')
    b.set_xlim(years[0], years[-1])
    b.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(b.yaxis)
    b.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=S.FONT_SMALL)
    P.panel_label(b, letter)


def committed_panel(c, src, letter='c'):
    """Cumulative Reference carbon 2026-2050 by stage and the emissions committed after 2050 (Fig3 c, K2).
    Returns (committed record, 2050 AR boundary in kt per year)."""
    st = read_csv('baseline/annual_by_stage.csv').set_index('year')
    res = read_json('aesa/results.json')
    cols = STAGE_COLS
    # (c) cumulative 2026-2050 (stages) and committed after 2050, years of the 2050 AR boundary on the right
    com = res['committed'][REF]
    k_lo, k_hi = com['lower_kt'] / com['years_of_B_AR_2050_lower'], com['upper_kt'] / com['years_of_B_AR_2050_upper']
    check(math.isclose(k_lo, k_hi, rel_tol=1e-9), 'Fig3: the 2050 AR boundary differs between the committed bounds')
    bottom = 0.0
    for sid, col in cols:
        v = float(st[col].sum())
        face, hatch = S.STAGE[sid]
        c.bar(0, v, bottom=bottom, width=0.62, **S.fill(face, hatch))
        src.add(letter, N.STAGES[sid], 'cumulative 2026-2050', v, 'kt CO2e')
        bottom += v
    c.text(0, bottom, P.fmt_kt(bottom), ha='center', va='bottom', fontsize=S.FONT_SMALL)
    face, hatch = S.COMPONENT['committed']
    c.bar(1, com['lower_kt'], width=0.62, facecolor='white', edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN)
    c.bar(1, com['upper_kt'] - com['lower_kt'], bottom=com['lower_kt'], width=0.62, facecolor=face, edgecolor=S.MUTED,
          hatch=hatch, lw=S.LW_THIN, alpha=0.5)
    c.text(1, com['upper_kt'], f"{com['lower_kt']:,.0f}–\n{com['upper_kt']:,.0f}", ha='center', va='bottom',
           fontsize=S.FONT_MIN)
    src.add(letter, 'Committed after 2050, lower (2050 factors held)', 'after 2050', com['lower_kt'], 'kt CO2e')
    src.add(letter, 'Committed after 2050, upper (2025 factors)', 'after 2050', com['upper_kt'], 'kt CO2e')
    src.add(letter, 'Committed after 2050, lower', 'years of the 2050 AR boundary', com['years_of_B_AR_2050_lower'], 'years')
    src.add(letter, 'Committed after 2050, upper', 'years of the 2050 AR boundary', com['years_of_B_AR_2050_upper'], 'years')
    src.add(letter, 'AR boundary 2050', '2050', k_lo, 'kt CO2e per year')
    c.set_xticks([0, 1])
    c.set_xticklabels(['2026–\n2050', 'Committed\nafter 2050'])
    c.set_xlim(-0.6, 1.6)
    c.set_ylim(0, bottom * 1.12)
    c.set_ylabel('Embodied carbon (kt CO₂e)')
    P.thousands(c.yaxis)
    c.grid(axis='x', visible=False)
    sec = c.secondary_yaxis('right', functions=(lambda v: v / k_lo, lambda yv: yv * k_lo))
    sec.set_ylabel('Years of the 2050 AR boundary')
    c.legend(handles=[Patch(facecolor='white', edgecolor=S.MUTED, hatch=hatch, label='lower bound'),
                      Patch(facecolor=face, edgecolor=S.MUTED, hatch=hatch, alpha=0.5, label='range to the upper bound')],
             loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=1, fontsize=S.FONT_SMALL)
    P.panel_label(c, letter)
    return com, k_lo


def fig3():
    h = PLAN['Fig3']
    fid = h['file']
    src = Source(fid, L.PAPER)
    st = read_csv('baseline/annual_by_stage.csv').set_index('year')
    mat = read_csv('baseline/annual_by_material.csv').pivot(index='year', columns='material', values='carbon_kt')
    an = read_csv('baseline/annual.csv')
    an = an[an['source'] == 'projection'].set_index('year')
    years = st.index.values
    cols = STAGE_COLS
    check(np.allclose(sum(st[c] for _, c in cols).values, an.loc[years, 'carbon_kt'].values, rtol=1e-9, atol=0),
          'Fig3: the stages do not add up to the annual carbon')
    check(np.allclose(mat.loc[years].sum(axis=1).values, an.loc[years, 'carbon_kt'].values, rtol=1e-9, atol=0),
          'Fig3: the materials do not add up to the annual carbon')
    fig = plt.figure(figsize=S.figsize('double', 78))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.25, 0.75], wspace=0.42, left=0.065, right=0.93, bottom=0.30,
                          top=0.95)
    a, b, c = (fig.add_subplot(gs[k]) for k in range(3))
    stage_panel(a, src)
    material_panel(b, src)
    com, k_lo = committed_panel(c, src)
    save(fig, fid, src, h['width'])
    tot = {sid: float(st[col].sum()) for sid, col in cols}
    num = dict(carbon=sum(tot.values()), **{f'{k}_kt': v for k, v in tot.items()}, com_lo=com['lower_kt'],
               com_hi=com['upper_kt'], yrs_lo=com['years_of_B_AR_2050_lower'], yrs_hi=com['years_of_B_AR_2050_upper'],
               B_AR_2050=k_lo, concrete=float(mat['CONCRETE (incl. reinforced)'].sum()),
               timber=float(mat['TIMBER'].sum()))
    cap = (h['caption'] + f" Of the {num['carbon']:,.0f} kt CO₂e emitted in 2026–2050, materials (A1–A3) are "
           f"{tot['a1a3']:,.0f} kt, construction (A4–A5) {tot['a4a5']:,.0f} kt, maintenance {tot['maintenance']:,.0f} kt "
           f"and soil carbon loss {tot['soil']:,.0f} kt (a); by material (b) each material includes its maintenance "
           f"within 2026–2050. A further {num['com_lo']:,.0f}–{num['com_hi']:,.0f} kt is committed after 2050 (later B2/B4 "
           f"and C1–C4 of the 2026–2050 cohorts; lower bound with the 2050 factors held, upper bound at 2025 factors), "
           f"{num['yrs_lo']:.0f}–{num['yrs_hi']:.0f} years of the 2050 acquired-rights boundary ({k_lo:,.0f} kt a year; "
           'right axis of c). The committed emissions are not part of the level of exceedance 2026–2050.')
    return dict(num, caption=cap)


# ============================================================
# Fig4  Pathways by demand band
# ============================================================
TARGETED = ('smaller_households', 'extra_space', 'vacancy', 'overbuild_2026', 'replacement', 'redevelopment')


def fig4():
    h = PLAN['Fig4']
    fid = h['file']
    src = Source(fid, L.PAPER)
    bd = read_csv('pathways/bands.csv')
    bd = bd[(bd['scenario'] == REF) & (bd['definition'] == 'in_scope')]
    r = runs_ref()
    face, hatch = S.UNTARGETED_GROUP
    ust = S.fill(face, hatch)
    fig, axes = plt.subplots(1, 2, figsize=S.figsize('double', 84))
    xt = [N.SCENARIOS[REF]] + [f'{p}\n' + textwrap.fill(N.PATHWAYS[p], 11) for p in PATHWAY_IDS] + ['TL\nTheoretical\nlimit']
    for ax, col, unit, letter in ((axes[0], 'floor_area_Mm2', 'Mm2', 'a'), (axes[1], 'carbon_kt', 'kt CO2e', 'b')):
        ids = list(TARGETED) + (['maintenance'] if col == 'carbon_kt' else [])
        ref_total = float(r.loc[REF, col])
        for i, run in enumerate(STORY):
            d = bd[bd['run'] == run].set_index('band')
            unt = sum(float(d.loc[N.band_data_label(b_), col]) for b_ in N.UNTARGETED)
            parts = [(ust, unt)] + [(P.band_style(b_), float(d.loc[N.band_data_label(b_), col])) for b_ in ids]
            up, dn = stack_styled(ax, [i], parts, width=0.64)
            src.add(letter, f'{short(run)}: {N.UNTARGETED_GROUP}', short(run), unt, unit)
            for b_ in ids:
                src.add(letter, f'{short(run)}: {N.BANDS[b_]}', short(run), float(d.loc[N.band_data_label(b_), col]), unit)
            net = float(up[0] + dn[0])
            check(math.isclose(net, float(r.loc[run, col]), rel_tol=1e-9), f'Fig4: the bands of {run} do not add up')
            pc = 100 * (net / ref_total - 1)
            chg = '' if run == REF else ('\n0%' if round(pc) == 0 else f'\n{pc:+.0f}%')
            ax.text(i, up[0], (P.fmt_kt(net) if col == 'carbon_kt' else f'{net:.1f}') + chg, ha='center', va='bottom',
                    fontsize=S.FONT_MIN, linespacing=1.0)
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
        ax.set_xticks(range(len(STORY)))
        ax.set_xticklabels(xt, fontsize=S.FONT_MIN)
        ax.set_ylabel('Floor area 2026–2050 (Mm²)' if col == 'floor_area_Mm2' else 'Embodied carbon 2026–2050 (kt CO₂e)')
        ax.set_ylim(None, ax.get_ylim()[1] * 1.08)
        if col == 'carbon_kt':
            P.thousands(ax.yaxis)
        ax.grid(axis='x', visible=False)
        P.panel_label(ax, letter)
    ax = axes[1]
    extra = []
    S.boundary_hzones(ax, float(r.loc[REF, 'B_AR_kt']), float(r.loc[REF, 'B_AtP_kt']), label=False)
    for key in ('AR', 'AtP'):
        v = float(r.loc[REF, f'B_{key}_kt'])
        stl = dict(S.BOUNDARY[key])
        lab = stl.pop('label')
        extra.append(Line2D([0], [0], **stl, label=f'{lab} budget 2026–2050: {v:,.0f} kt'))
        src.add('b', f'{lab} budget 2026-2050', 'cumulative', v, 'kt CO2e')
    extra += S.zone_handles()
    handles = [Patch(label=N.UNTARGETED_GROUP, **dict(ust, edgecolor='#555555'))]
    handles += P.band_handles(list(TARGETED) + ['maintenance']) + extra
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), frameon=False,
               handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    save(fig, fid, src, h['width'])
    num = {run: dict(floor_area=float(r.loc[run, 'floor_area_Mm2']), carbon=float(r.loc[run, 'carbon_kt']),
                     d_carbon=float(r.loc[run, 'delta_carbon_kt_vs_reference_pct']),
                     d_floor_area=100 * (float(r.loc[run, 'floor_area_Mm2']) / float(r.loc[REF, 'floor_area_Mm2']) - 1))
           for run in STORY}
    cap = (h['caption'] + f" P5 Combined lowers carbon 2026–2050 by {-num['P5-moderate']['d_carbon']:.0f}% against the "
           f"Reference and TL by {-num['TL']['d_carbon']:.0f}%. Bottom segment (grey, dotted): the untargeted band "
           '(population growth), which no pathway acts on; negative bands (below zero) release '
           'existing dwellings; maintenance (B2, B4) within 2026–2050 is its own layer in b. Labels: total and change '
           'against the Reference. Lines in b: the cumulative AR and AtP budgets 2026–2050; shading: below AtP (darker green), between AtP and AR (light green), above AR (light red, boundary exceeded).')
    return dict(runs=num, caption=cap)


# ============================================================
# Fig5  Emissions against the boundaries (a) and the order-free attribution (b)
# ============================================================
FIG5_RUNS = [(REF, S.REFERENCE, S.LW_BOLD), ('P5-moderate', S.PATHWAY['P5'], S.LW), ('TL', S.TL, S.LW)]


def tl_built_2027(an):
    """TL dwellings built in 2027 and the 2027-2050 minimum (constant-share reoccupation: positive in every year of
    the deterministic TL, asserted by pathways.compute_tl and here)."""
    d = an[an['run'] == 'TL'].set_index('year')['dwellings_built']
    late = d.loc[2027:WINDOW[1]]
    check((late > 0).all(), 'TL: dwellings built <= 0 in a year of 2027-2050')
    return float(d.loc[2027]), float(late.min())


def fig5():
    h = PLAN['Fig5']
    fid = h['file']
    src = Source(fid, L.PAPER)
    an = read_csv('pathways/annual.csv')
    an = an[an['scenario'] == REF]
    mca = read_csv('pathways/montecarlo_annual.csv')
    mcs = mc_summary()
    aesa_mc = read_csv('aesa/montecarlo_annual.csv')
    r = runs_ref()
    k_atp = budget_ratio(r)
    b27, bmin = tl_built_2027(an)
    fig = plt.figure(figsize=S.figsize('double', 190))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.35], hspace=0.16, left=0.085, right=0.90, bottom=0.185, top=0.975)
    a, b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    # (a) annual emissions and boundaries
    ref_mc = mca[mca['run'] == 'REF'].set_index('year')
    am = aesa_mc[aesa_mc['scenario'] == REF].set_index('year')
    yrs = [y for y in ref_mc.index if y >= WINDOW[0]]
    for q, qa in (('p5', 'p5'), ('p95', 'p95')):
        check(np.allclose(ref_mc.loc[yrs, f'carbon_kt_{q}'].values, am.loc[yrs, f'I_sec_kgCO2e_{qa}'].values / M6,
                          rtol=1e-9, atol=0), 'Fig5: the Reference Monte Carlo band differs from the AESA layer')
    for run, col, lw in FIG5_RUNS:
        m = mca[mca['run'] == mc_key(run)].set_index('year').loc[yrs]
        a.fill_between(yrs, m['carbon_kt_p5'], m['carbon_kt_p95'], color=col, alpha=0.16, lw=0)
        d = an[an['run'] == run].set_index('year').loc[yrs]
        a.plot(yrs, d['carbon_kt'], color=col, lw=lw, label=label(run))
        src.add('a', label(run), yrs, d['carbon_kt'].values, 'kt CO2e per year')
        src.add('a', f'{label(run)}, Monte Carlo 5%', yrs, m['carbon_kt_p5'].values, 'kt CO2e per year')
        src.add('a', f'{label(run)}, Monte Carlo 95%', yrs, m['carbon_kt_p95'].values, 'kt CO2e per year')
    d0 = an[an['run'] == REF].set_index('year').loc[yrs]
    P.boundary_lines(a, yrs, d0['B_AR_kt'].values, d0['B_AtP_kt'].values)
    src.add('a', N.METRICS['AR'] + ' boundary', yrs, d0['B_AR_kt'].values, 'kt CO2e per year')
    src.add('a', N.METRICS['AtP'] + ' boundary', yrs, d0['B_AtP_kt'].values, 'kt CO2e per year')
    src.add('a', 'TL dwellings built, 2027', 2027, b27, 'dwellings')
    a.set_yscale('log', nonpositive='clip')
    a.set_ylim(5, 8000)
    a.set_xlim(WINDOW[0] - 0.5, WINDOW[1] + 0.5)
    a.set_ylabel('Embodied carbon and boundaries\n(kt CO₂e per year, log scale)')
    P.log_ticks(a.yaxis, (5, 10, 20, 50, 100, 200, 500, 1000, 2000))
    hd, lb = a.get_legend_handles_labels()
    hd.append(Patch(facecolor=S.REFERENCE, alpha=0.16, label='Monte Carlo 5–95% (each run)'))
    a.legend(handles=hd, loc='upper right', ncol=3, fontsize=S.FONT_MIN)
    P.panel_label(a, 'a')
    # (b) the Shapley waterfall in cumulative LoE AR
    sp = read_csv('pathways/shapley_pathways.csv')
    sp = sp[(sp['setting'] == 'moderate') & (sp['metric'] == 'LoE_AR')].set_index('player')['reduction']
    st = read_csv('pathways/shapley_theoretical_limit.csv')
    st = st[st['metric'] == 'LoE_AR'].set_index('player')['reduction']
    tl = read_json('pathways/theoretical_limit.json')
    ref, p5, tlr = (float(r.loc[k, 'LoE_AR']) for k in (REF, 'P5-moderate', 'TL'))
    check(math.isclose(ref - sum(sp[p] for p in ('P1', 'P2', 'P3', 'P4')), p5, rel_tol=1e-12),
          'Fig5: the pathway Shapley values do not add up to Reference - P5')
    tl_ids = [f'TL{k}' for k in range(1, 11)]
    f27 = float(st['by2030'])                           # TL's faster adoption (separate line)
    fre = float(st['reoccupation'])                     # constant-share reoccupation (separate line)
    share = float(tl['indicators']['TL']['reoccupation']['share_of_need'])
    check(math.isclose(p5 - f27 - fre - sum(st[t] for t in tl_ids), tlr, rel_tol=1e-12),
          'Fig5: P5 - faster adoption - reoccupation - TL1..TL10 does not reach TL')
    w = 0.66
    labels, x, prev = [], 0, ref

    def total(xx, v, col, lab, run):
        b.bar(xx, v, width=w, **S.fill(col))
        q = mcs.loc[(mc_key(run), 'LoE_AR')]
        b.errorbar(xx, v, yerr=[[v - q['p5']], [q['p95'] - v]], color=S.INK if run != 'TL' else '#8C8C8C',
                   capsize=2.0, lw=S.LW_THIN, capthick=S.LW_THIN)
        if run == 'TL':                    # left of the bar: the budget labels sit to its right
            b.text(xx - w / 2 - 0.04, q['p95'], f'{v:.2f}', ha='right', va='bottom', fontsize=S.FONT_MIN)
        else:
            b.text(xx + w / 2 + 0.04, q['p95'], f'{v:.2f}', ha='left', va='bottom', fontsize=S.FONT_MIN)
        labels.append(lab)
        src.add('b', lab, 'total', v, 'cumulative LoE AR 2026-2050')
        src.add('b', lab + ', Monte Carlo 5%', 'total', q['p5'], 'cumulative LoE AR 2026-2050')
        src.add('b', lab + ', Monte Carlo 95%', 'total', q['p95'], 'cumulative LoE AR 2026-2050')

    def step(xx, start, red, col, lab):
        b.bar(xx, -red, bottom=start, width=w, color=col, edgecolor='#555555', lw=S.LW_THIN)
        b.plot([xx - 1 + w / 2, xx - w / 2], [start, start], color=S.MUTED, lw=S.LW_THIN)
        b.text(xx, start - red, f'−{red:.2f}' if red >= 0 else f'+{-red:.2f}', ha='center', va='top',
               fontsize=S.FONT_MIN)
        labels.append(lab)
        src.add('b', lab, 'reduction', red, 'cumulative LoE AR 2026-2050')

    total(x, ref, S.REFERENCE, N.SCENARIOS[REF], REF)
    for p in ('P1', 'P2', 'P3', 'P4'):
        x += 1
        step(x, prev, float(sp[p]), S.PATHWAY[p], f'{p} {N.PATHWAYS[p]}')
        prev -= float(sp[p])
    x += 1
    total(x, p5, S.PATHWAY['P5'], f"P5 {N.PATHWAYS['P5']}", 'P5-moderate')
    x += 1
    step(x, p5, f27, S.PATHWAY['P5'], N.TL_FASTER_ADOPTION[0].upper() + N.TL_FASTER_ADOPTION[1:])
    x += 1
    step(x, p5 - f27, fre, S.PATHWAY['P5'], N.TL_REOCCUPATION_LINE.capitalize())
    prev = p5 - f27 - fre
    for t in tl_ids:
        x += 1
        step(x, prev, float(st[t]), S.LEVER[N.TL_LIMIT_OF[t]] if N.TL_LIMIT_OF[t] else '#7A7A7A', f'{t} {N.TL[t]}')
        prev -= float(st[t])
    x += 1
    total(x, tlr, S.TL, 'TL Theoretical limit', 'TL')
    x_last = x
    # committed after 2050, in multiples of the cumulative AR budget 2026-2050 (not part of the LoE)
    face, hatch = S.COMPONENT['committed']
    bar_ = float(r.loc[REF, 'B_AR_kt'])
    xc = x_last + 1.6
    b.axvline(xc - 0.8, color=S.MUTED, lw=S.LW_THIN, ls=':')
    for k, run in enumerate((REF, 'P5-moderate', 'TL')):
        xx = xc + k
        lo, hi = float(r.loc[run, 'committed_lower_kt']) / bar_, float(r.loc[run, 'committed_upper_kt']) / bar_
        b.bar(xx, lo, width=w, facecolor='white', edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN)
        b.bar(xx, hi - lo, bottom=lo, width=w, facecolor=face, edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN, alpha=0.5)
        b.text(xx, hi, f'{lo:.2f}–\n{hi:.2f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
        labels.append(f'{short(run)}\ncommitted\nafter 2050')
        src.add('b', f'{short(run)} committed after 2050, lower', 'multiples of the AR budget 2026-2050', lo, 'ratio')
        src.add('b', f'{short(run)} committed after 2050, upper', 'multiples of the AR budget 2026-2050', hi, 'ratio')
    S.boundary_hzones(b, 1.0, 1.0 / k_atp, label=False, xspan=(-0.6, x_last + 0.5))
    for key, v in (('AR', 1.0), ('AtP', 1.0 / k_atp)):
        stl = dict(S.BOUNDARY[key])
        lab = stl.pop('label')
        b.text(x_last + 0.5, v, f' {key} budget', va='center', ha='left', fontsize=S.FONT_MIN, color=stl['color'])
        src.add('b', f'{lab} budget 2026-2050', 'cumulative LoE AR units', v, 'cumulative LoE AR 2026-2050')
    g = tl['gap']['TL']
    q_tl = {k: float(mcs.loc[('TL', f'LoE_{k}'), 'probability_LoE_at_most_1']) for k in ('AR', 'AtP')}
    note = (f"TL: P(LoE AR ≤ 1) = {100 * q_tl['AR']:.1f}%, P(LoE AtP ≤ 1) = {100 * q_tl['AtP']:.1f}% (Monte Carlo)")
    if not g['within_AR']:
        rs = g['residual']
        note = (f"TL exceeds the AR budget (LoE AR {g['LoE_AR']:.2f}): reaching it means\n"
                f"{rs['dwellings_not_built_2027_2050']:,.0f} dwellings not built in 2027–2050, i.e. "
                f"{rs['new_residents_housed_in_existing_dwellings']:,.0f} new residents\nhoused in existing dwellings.\n"
                + note)
    b.annotate(note, xy=(x_last, tlr), xytext=(x_last - 7.9, ref * 0.98), fontsize=S.FONT_SMALL, color=S.INK,
               va='bottom', arrowprops=dict(arrowstyle='-', color=S.MUTED, lw=S.LW_THIN, shrinkA=2, shrinkB=4))
    src.add('b', 'TL, P(LoE AR <= 1)', 'Monte Carlo', q_tl['AR'], 'probability')
    src.add('b', 'TL, P(LoE AtP <= 1)', 'Monte Carlo', q_tl['AtP'], 'probability')
    b.set_xticks(list(range(x_last + 1)) + [xc, xc + 1, xc + 2])
    b.set_xticklabels([textwrap.fill(t_, 24) if '\n' not in t_ else t_ for t_ in labels], fontsize=S.FONT_MIN,
                      rotation=90, linespacing=1.0)
    b.set_xlim(-0.6, xc + 2.6)
    top = max(ref * 1.10, float(mcs.loc[('REF', 'LoE_AR'), 'p95']) * 1.04)
    b.set_ylim(0, top)
    b.set_ylabel(N.METRICS['cumulative_LoE'] + ', AR\n(committed: multiples of the AR budget)')
    sec = b.secondary_yaxis('right', functions=(lambda v: v * k_atp, lambda v: v / k_atp))
    sec.set_ylabel('Cumulative level of exceedance, AtP')
    b.grid(axis='x', visible=False)
    b.legend(handles=[Line2D([0], [0], color=S.INK, lw=S.LW_THIN, marker='|', ms=5, label='Monte Carlo 5–95%'),
                      Patch(facecolor='white', edgecolor=S.MUTED, hatch=hatch, label=N.COMPONENTS['committed'])],
             loc='lower center', bbox_to_anchor=(0.5, 0.0), bbox_transform=fig.transFigure, ncol=2,
             fontsize=S.FONT_SMALL)
    P.panel_label(b, 'b')
    save(fig, fid, src, h['width'])
    rs = g.get('residual', {})
    q = {run: {k: mcs.loc[(mc_key(run), k)] for k in ('carbon_kt', 'LoE_AR', 'LoE_AtP')} for run in (REF, 'P5-moderate', 'TL')}
    q_p5 = {k: float(mcs.loc[('P5', f'LoE_{k}'), 'probability_LoE_at_most_1']) for k in ('AR', 'AtP')}
    num = dict(ref=ref, p5=p5, tl=tlr, faster_adoption=f27, reoccupation=fre, reoccupation_share=share, k_atp=k_atp, q=q, p_tl=q_tl, p_p5=q_p5,
               dw=rs.get('dwellings_not_built_2027_2050', float('nan')), within_AR=bool(g['within_AR']),
               margin_AR_kt=float(g.get('margin_AR_kt', float('nan'))),
               res=rs.get('new_residents_housed_in_existing_dwellings', float('nan')),
               cut=g.get('backcast', {}).get('cut_AR', float('nan')),
               a50={run: float(an[(an['run'] == run) & (an['year'] == WINDOW[1])]['carbon_kt'].iloc[0])
                    for run, *_ in FIG5_RUNS},
               ar50=float(d0.loc[WINDOW[1], 'B_AR_kt']), atp50=float(d0.loc[WINDOW[1], 'B_AtP_kt']))
    cap = (h['caption'] + " (a) Annual embodied carbon against the annual AR and AtP boundaries (log scale), with the "
           'Monte Carlo 5–95% band of each run (5,000 Latin-hypercube draws of the Reference, each also run through P5 '
           'and TL with the levers applied identically and the TL targets held at their absolute values). '
           + N.tl_caption(share) + f" TL builds {b27:,.0f} dwellings in 2027 (at least {bmin:,.0f} a year in "
           '2027–2050). In 2050 the Reference emits '
           f"{num['a50'][REF]:,.0f} kt, P5 {num['a50']['P5-moderate']:,.0f} kt and TL {num['a50']['TL']:,.0f} kt "
           f"against an AR boundary of {num['ar50']:,.0f} kt and an AtP boundary of {num['atp50']:,.0f} kt. "
           f"(b) Order-free attribution (Shapley values, exact) of the cumulative LoE AR 2026–2050: the four pathways "
           f"(Moderate; they add up exactly to Reference − P5), two separate lines (not Shapley players): TL's faster "
           f"adoption, P5 with full roll-out by 2030 instead of 2035 ({-f27:+.2f} LoE AR), and re-occupying P5's released "
           f"dwellings at a constant {100 * share:.0f}% of each year's need ({-fre:+.2f}; the TL base), and TL1–TL10 "
           f"relative to that base (1,024 subsets; they add up exactly to base − TL). Right axis: the same quantity "
           f"as a cumulative AtP "
           f"level of exceedance (×{k_atp:.2f}; the budgets of every run are the Reference's). Whiskers: Monte Carlo "
           f"5–95% (Reference {q[REF]['LoE_AR']['p5']:.2f}–{q[REF]['LoE_AR']['p95']:.2f}, P5 "
           f"{q['P5-moderate']['LoE_AR']['p5']:.2f}–{q['P5-moderate']['LoE_AR']['p95']:.2f}, TL "
           f"{q['TL']['LoE_AR']['p5']:.2f}–{q['TL']['LoE_AR']['p95']:.2f}); P(LoE AR ≤ 1) for TL "
           f"{100 * q_tl['AR']:.1f}%, P(LoE AtP ≤ 1) {100 * q_tl['AtP']:.1f}%. Hatched bars: emissions committed after "
           '2050, in multiples of the cumulative AR budget 2026–2050 (not part of the level of exceedance). '
           + (f"TL stays within the AR budget by {g['margin_AR_kt']:,.0f} kt." if g['within_AR'] else
              f"TL exceeds the AR budget by {(g['LoE_AR'] - 1) * float(r.loc[REF, 'B_AR_kt']):,.0f} kt."))
    return dict(num, caption=cap)


# ============================================================
# Fig6  Solution space (single column)
# ============================================================
def bilinear(space):
    """The cumulative LoE on the plane is exactly LoE(d, i) = a + (1 - d)[(1 - i) b + c] (the 2026 cohort a
    fixed; the 2027-2050 cohorts' non-soil carbon b and soil carbon c scale with the cuts;
    pathways.scaled_carbon). The three constants are read from the grid and every grid cell is checked
    against them, so the contours are the data's, not a fit."""
    g = space.set_index(['demand_reduction', 'intensity_reduction'])['LoE_AR']
    a = g.loc[(1.0, 0.0)]
    c = g.loc[(0.0, 1.0)] - a
    b = g.loc[(0.0, 0.0)] - a - c
    f = lambda d, i: a + (1 - d) * ((1 - i) * b + c)
    err = max(abs(f(d, i) - v) / v for (d, i), v in g.items())
    check(err <= 1e-12, f'Fig6: the solution space is not bilinear in the cuts (max relative error {err:.1e})')
    return f, a


def fig6(h=None, base=None):
    """h, base: the plan entry and folder (default Fig6 in outputs/paper/; key_figures.py draws K4 with it)."""
    h = h or PLAN['Fig6']
    fid = h['file']
    src = Source(fid, base or L.PAPER)
    space = read_csv('pathways/solution_space.csv')
    bc = read_json('pathways/backcast.json')
    tl = read_json('pathways/theoretical_limit.json')['solution_space_marker']
    r = runs_ref()
    k_atp = budget_ratio(r)
    f, a0 = bilinear(space)
    atp_one = 1.0 / k_atp                                   # LoE AtP = 1 in LoE AR units
    atp_reachable = a0 < atp_one
    marks = [m for m in bc['solution_space_markers'] if m['run'].endswith('-moderate')]
    check(len(marks) == 5, 'Fig6: P1-P5 Moderate markers missing')
    fig = plt.figure(figsize=S.figsize('single', 100))
    ax = fig.add_axes([0.17, 0.33, 0.76, 0.64])
    dx = np.linspace(0, 100, 401)
    D, I = np.meshgrid(dx / 100, dx / 100)
    Z = f(D, I)
    # the boundary zones of style.py (below AtP, between AtP and AR, above AR) and the two budget contours
    S.boundary_field(ax, 100 * D, 100 * I, Z, 1.0, atp_one)
    lv = [v for v in (2, 3, 5) if Z.min() < v < Z.max()]
    ax.contour(100 * D, 100 * I, Z, levels=lv, colors=[S.MUTED], linewidths=[S.LW_THIN], linestyles=':')
    # contour labels at 50% intensity reduction: the plane is bilinear, so the demand cut of level v there is
    # d = 1 - (v - a0) / f_slope, with f_slope = f(0, 0.5) - a0
    slope = f(0.0, 0.5) - a0
    for v, txt, col in [(1.0, 'AR budget', S.AR), (atp_one, 'AtP budget', S.ATP)] + [(v, f'LoE AR {v:g}', S.MUTED) for v in lv]:
        d_v = 1.0 - (v - a0) / slope
        if 0.0 < d_v < 1.0:
            ax.text(100 * d_v, 50.0, txt, rotation=90, ha='center', va='center', fontsize=S.FONT_MIN, color=col,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.6, alpha=0.85), zorder=4)
    for m in marks:
        pw = m['run'].split('-')[0]
        ax.plot(100 * m['demand_reduction'], 100 * m['intensity_reduction'], marker='o', ms=4, mfc=S.PATHWAY[pw],
                mec=S.INK, mew=S.LW_THIN, lw=0, clip_on=False, zorder=5)
        src.add('markers', f'{pw} {N.PATHWAYS[pw]}', 'demand reduction', 100 * m['demand_reduction'], '%')
        src.add('markers', f'{pw} {N.PATHWAYS[pw]}', 'intensity reduction', 100 * m['intensity_reduction'], '%')
        src.add('markers', f'{pw} {N.PATHWAYS[pw]}', 'cumulative LoE AR (run)', m['LoE_AR_run'], 'level of exceedance')
    # P1 and P2 nearly coincide: every marker is labelled at a fixed place with a leader line to its true position
    label_at = {'P4': (1.0, 18.0), 'P3': (8.0, 18.0), 'P1': (15.0, 18.0), 'P2': (22.0, 18.0), 'P5': (28.0, 10.0)}
    for m in marks:
        pw = m['run'].split('-')[0]
        ax.annotate(pw, xy=(100 * m['demand_reduction'], 100 * m['intensity_reduction']), xytext=label_at[pw],
                    fontsize=S.FONT_MIN, color=S.INK, fontweight='bold', ha='left', va='bottom', annotation_clip=False,
                    arrowprops=dict(arrowstyle='-', color=S.MUTED, lw=S.LW_THIN, shrinkA=0, shrinkB=2.5))
    ax.plot(100 * tl['demand_reduction'], 100 * tl['intensity_reduction'], marker='*', ms=8, mfc=S.TL, mec='white',
            mew=S.LW_THIN, lw=0, zorder=6)
    for k in ('demand_reduction', 'intensity_reduction'):
        src.add('markers', 'TL Theoretical limit', k.replace('_', ' '), 100 * tl[k], '%')
    src.add('markers', 'TL Theoretical limit', 'cumulative LoE AR (run)', tl['LoE_AR_run'], 'level of exceedance')
    src.add('markers', 'TL Theoretical limit', 'cumulative LoE AR (plane at the coordinates)',
            tl['LoE_AR_on_grid_at_coordinates'], 'level of exceedance')
    for _, row_ in space.iterrows():
        src.add('grid', 'cumulative LoE AR', f"{100 * row_['demand_reduction']:.0f}% / {100 * row_['intensity_reduction']:.0f}%",
                row_['LoE_AR'], 'level of exceedance (demand / intensity reduction)')
    src.add('grid', 'LoE AtP = 1 in LoE AR units', 'all', atp_one, 'level of exceedance')
    src.add('grid', 'LoE AR at 100% / 100% (the 2026 cohort)', '100% / 100%', a0, 'level of exceedance')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel('Demand reduction: cut of\n2027–2050 floor area (%)')
    ax.set_ylabel('Intensity reduction: cut of\nnon-soil carbon per m² (%)')
    ax.grid(False)
    handles = [Line2D([0], [0], marker='o', mfc=S.PATHWAY[pw], mec='white', lw=0, ms=4, label=f'{pw} {N.PATHWAYS[pw]}')
               for pw in PATHWAY_IDS]
    handles += [Line2D([0], [0], marker='*', mfc=S.TL, mec='white', lw=0, ms=8, label='TL Theoretical limit')]
    handles += S.boundary_handles() + S.zone_handles()
    fig.legend(handles=handles, loc='lower center', ncol=2, bbox_to_anchor=(0.5, 0.0), frameon=False)
    save(fig, fid, src, h['width'])
    num = dict(tl_demand=100 * tl['demand_reduction'], tl_intensity=100 * tl['intensity_reduction'],
               p5_demand=100 * [m for m in marks if m['run'] == 'P5-moderate'][0]['demand_reduction'],
               p5_intensity=100 * [m for m in marks if m['run'] == 'P5-moderate'][0]['intensity_reduction'],
               cut_ref=100 * bc[REF]['cut_AR'], a0=a0, atp_one=atp_one, atp_reachable=atp_reachable)
    atp = ('The LoE AtP = 1 contour (dashed) lies at LoE AR = {:.2f}.'.format(atp_one) if atp_reachable else
           f"LoE AtP = 1 (LoE AR {atp_one:.2f}) is not reachable on the plane: the observed 2026 cohort alone, which no "
           f"cut changes, gives LoE AR {a0:.2f} (LoE AtP {a0 / atp_one:.2f}).")
    cap = (h['caption'] + f" Cutting 2027–2050 construction alone by {num['cut_ref']:.1f}% would bring the Reference to "
           f"LoE AR = 1 (back-cast); P5 sits at {num['p5_demand']:.0f}% demand and {num['p5_intensity']:.0f}% intensity "
           f"reduction, TL at {num['tl_demand']:.0f}% and {num['tl_intensity']:.0f}% (at these coordinates the plane "
           f"reads LoE AR {tl['LoE_AR_on_grid_at_coordinates']:.2f}; the TL run, with its lower soil carbon, "
           f"{tl['LoE_AR_run']:.2f}). {atp} Contours: the exact bilinear LoE of the plane, read from the 5% grid "
           '(outputs/data/pathways/solution_space.csv).')
    return dict(num, caption=cap)


# ============================================================
# Tables
# ============================================================
def md_table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return out


def table1():
    """Table 1: the levers (Moderate column first) and the TL assumptions TL1-TL10, from levers.json and
    theoretical_limit.json through levers.lever_table / levers.tl_table (the rows of LEVERS_TABLE.md)."""
    import levers as LV
    p, t = read_json('pathways/levers.json'), read_json('pathways/theoretical_limit.json')
    rows = [dict(item=r['item'], pathway=r['pathway'], band=r['band'], how=r['how'], assumption=r['assumption'],
                 moderate=r['moderate'], ambitious=r['ambitious'], source=r['source'], tag=r['tag'])
            for r in LV.lever_table(p)]
    rows += [dict(item=r['item'], pathway=r['pathway'], band=r['band'], how=r['how'], assumption=r['assumption'],
                  moderate=r['value'], ambitious='', source=r['source'], tag=r['tag']) for r in LV.tl_table(t)]
    check([r['item'].split()[0] for r in rows] == [f'L{k}' for k in range(1, 10)] + [f'TL{k}' for k in range(1, 11)],
          'Table 1: the rows are not L1-L9 and TL1-TL10')
    df = pd.DataFrame(rows)
    df.to_csv(L.writing(os.path.join(L.PAPER, 'Table1_levers.csv')), index=False)
    head = ['item', 'pathway', 'demand band targeted', 'how it works (model terms)', 'assumption',
            'Moderate (paper) / TL value', 'Ambitious (Extended Data)', 'source', 'tag']
    md = md_table(head, [[r[k] for k in ('item', 'pathway', 'band', 'how', 'assumption', 'moderate', 'ambitious',
                                         'source', 'tag')] for r in rows])
    return df, md


def table2():
    """Table 2: the Reference, P1-P5 (Moderate, by 2035) and TL; Monte Carlo 5-95% for the Reference, P5 and
    TL; P(LoE <= 1) for P5 and TL under AR and AtP."""
    r = runs_ref()
    mcs = mc_summary()
    rows = []
    for run in STORY:
        x = r.loc[run]
        d = dict(run=label(run), run_id=run, floor_area_Mm2=float(x['floor_area_Mm2']), carbon_kt=float(x['carbon_kt']),
                 committed_lower_kt=float(x['committed_lower_kt']), committed_upper_kt=float(x['committed_upper_kt']),
                 LoE_AR=float(x['LoE_AR']), LoE_AtP=float(x['LoE_AtP']),
                 carbon_change_vs_reference_pct=0.0 if run == REF else float(x['delta_carbon_kt_vs_reference_pct']))
        if run in (REF, 'P5-moderate', 'TL'):
            k = mc_key(run)
            for qn in ('carbon_kt', 'LoE_AR', 'LoE_AtP'):
                d[f'{qn}_mc_p5'] = float(mcs.loc[(k, qn), 'p5'])
                d[f'{qn}_mc_p95'] = float(mcs.loc[(k, qn), 'p95'])
            check(math.isclose(float(mcs.loc[(k, 'carbon_kt'), 'central_draw_max_rel_diff']) + 1.0, 1.0, abs_tol=1e-9),
                  f'Table 2: the central draw of {run} does not reproduce the deterministic run')
        if run in ('P5-moderate', 'TL'):
            for key in ('AR', 'AtP'):
                d[f'P_LoE_{key}_at_most_1'] = float(mcs.loc[(mc_key(run), f'LoE_{key}'), 'probability_LoE_at_most_1'])
        rows.append(d)
    df = pd.DataFrame(rows)
    df.to_csv(L.writing(os.path.join(L.PAPER, 'Table2_results.csv')), index=False)

    def rng(d, q, fmt):
        return f" ({format(d[f'{q}_mc_p5'], fmt)}–{format(d[f'{q}_mc_p95'], fmt)})" if f'{q}_mc_p5' in d else ''

    md = md_table(['run', 'floor area 2026–2050 (Mm²)', 'carbon 2026–2050 (kt CO₂e)', 'change vs Reference',
                   'committed after 2050 (kt CO₂e)', 'cumulative LoE AR', 'cumulative LoE AtP', 'P(LoE ≤ 1), AR / AtP'],
                  [[d['run'], f"{d['floor_area_Mm2']:.1f}", f"{d['carbon_kt']:,.0f}" + rng(d, 'carbon_kt', ',.0f'),
                    '–' if d['run_id'] == REF else f"{d['carbon_change_vs_reference_pct']:+.1f}%",
                    f"{d['committed_lower_kt']:,.0f}–{d['committed_upper_kt']:,.0f}",
                    f"{d['LoE_AR']:.2f}" + rng(d, 'LoE_AR', '.2f'), f"{d['LoE_AtP']:.1f}" + rng(d, 'LoE_AtP', '.1f'),
                    (f"{100 * d['P_LoE_AR_at_most_1']:.1f}% / {100 * d['P_LoE_AtP_at_most_1']:.1f}%"
                     if 'P_LoE_AR_at_most_1' in d else '–')] for d in rows])
    return df, md


# ============================================================
# PAPER.md
# ============================================================
def tl_gap_sentence(sh, f27, fre):
    """The gap between P5 and TL by its two largest Shapley contributions (TL1-TL10) and the two separate lines
    (TL's faster adoption; constant-share reoccupation); values from the data."""
    top = sorted((k for k in sh if k.startswith('TL')), key=lambda k: -sh[k])[:2]
    a, b = top
    return (f"Of the gap between P5 and TL, the largest contributions are {a} {N.TL[a].lower()} ({sh[a]:.2f} of LoE AR) "
            f"and {b} {N.TL[b].lower()} ({sh[b]:.2f}); TL's faster adoption (by 2030 instead of 2035) lowers it by "
            f"{f27:.2f}, and re-occupying released dwellings gradually, at a constant share of each year's need, "
            f"{'raises' if fre < 0 else 'lowers'} it by {abs(fre):.2f}.")


def findings(rr, t2):
    """The headline findings: one sentence each, with its numbers and the data files they come from."""
    f2, f3, f4, f5, f6 = (rr[k] for k in ('Fig2', 'Fig3', 'Fig4', 'Fig5', 'Fig6'))
    t = t2.set_index('run_id')
    ms = read_csv(L.montecarlo('summary', REF, frozen=False), index_col=0)
    q = f5['q']
    return [
        (f"New Zealand builds {t.loc[REF, 'floor_area_Mm2']:.1f} million m² of new residential floor area in 2026–2050 "
         f"in the Reference (Monte Carlo 90% interval {ms.loc['floor_area_Mm2', 'p5']:.1f}–"
         f"{ms.loc['floor_area_Mm2', 'p95']:.1f}); {100 * f2['untargeted_share']:.0f}% of it serves population growth, "
         'the only demand no pathway targets.',
         'data/pathways/runs.csv, data/montecarlo/summary_REF.csv, data/baseline/bands_annual.csv'),
        (f"Its embodied carbon is {f3['carbon']:,.0f} kt CO₂e within 2026–2050 (Monte Carlo "
         f"{q[REF]['carbon_kt']['p5']:,.0f}–{q[REF]['carbon_kt']['p95']:,.0f}; materials A1–A3 {f3['a1a3_kt']:,.0f} kt), "
         f"with a further {f3['com_lo']:,.0f}–{f3['com_hi']:,.0f} kt committed after 2050, {f3['yrs_lo']:.0f}–"
         f"{f3['yrs_hi']:.0f} years of the 2050 acquired-rights boundary.",
         'data/baseline/annual_by_stage.csv, data/aesa/results.json, data/pathways/montecarlo_summary.csv'),
        (f"This exceeds the sector's share of the 2 °C carrying capacity {f5['ref']:.2f}-fold by acquired rights "
         f"(Monte Carlo {q[REF]['LoE_AR']['p5']:.2f}–{q[REF]['LoE_AR']['p95']:.2f}) and "
         f"{t.loc[REF, 'LoE_AtP']:.1f}-fold by ability to pay ({q[REF]['LoE_AtP']['p5']:.1f}–"
         f"{q[REF]['LoE_AtP']['p95']:.1f}); the two principles are reported side by side, never averaged.",
         'data/pathways/runs.csv, data/pathways/montecarlo_summary.csv'),
        (f"Combining the four pathways (P5, Moderate, full roll-out by 2035) lowers carbon 2026–2050 by "
         f"{-f4['runs']['P5-moderate']['d_carbon']:.0f}%: the cumulative LoE AR falls from {f5['ref']:.2f} to "
         f"{f5['p5']:.2f} (Monte Carlo {q['P5-moderate']['LoE_AR']['p5']:.2f}–{q['P5-moderate']['LoE_AR']['p95']:.2f}; "
         f"P(LoE AR ≤ 1) = {100 * f5['p_p5']['AR']:.0f}%), far above the acquired-rights budget.", 'data/pathways/runs.csv, data/pathways/montecarlo_summary.csv'),
        (f"The hyper-optimistic theoretical limit (TL; a thought experiment with every lever at its limit, adopted by "
         f"2030, not a pathway) "
         f"reaches LoE AR {f5['tl']:.2f} (Monte Carlo {q['TL']['LoE_AR']['p5']:.2f}–{q['TL']['LoE_AR']['p95']:.2f}; "
         f"P(LoE AR ≤ 1) = {100 * f5['p_tl']['AR']:.1f}%)"
         + (f", within the acquired-rights budget by {f5['margin_AR_kt']:,.0f} kt," if f5['within_AR'] else
            f"; reaching the AR budget means not building {f5['dw']:,.0f} dwellings in 2027–2050,")
         + f" but LoE AtP {t.loc['TL', 'LoE_AtP']:.1f} (P(LoE AtP ≤ 1) = {100 * f5['p_tl']['AtP']:.0f}%); it re-occupies "
         f"all vacant dwellings and returns to the 1991 household size, the released dwellings meeting "
         f"{100 * f5['reoccupation_share']:.0f}% of each year's need.",
         'data/pathways/runs.csv, data/pathways/montecarlo_summary.csv, data/pathways/theoretical_limit.json'),
        (tl_gap_sentence(rr['_tl_shapley'], f5['faster_adoption'], f5['reoccupation']),
         'data/pathways/shapley_theoretical_limit.csv'),
        (f"No cut of 2027–2050 floor area or carbon per m² reaches the ability-to-pay budget: the observed 2026 cohort "
         f"alone gives a cumulative LoE AtP of {f6['a0'] / f6['atp_one']:.2f}." if not f6['atp_reachable'] else
         f"Cutting 2027–2050 construction alone by {f6['cut_ref']:.1f}% brings the Reference to LoE AR = 1.",
         'data/pathways/solution_space.csv, data/pathways/runs.csv'),
    ]


def write_md(rr, t1md, t2md, t2):
    lines = ['# Paper: headline findings, figures and tables', '',
             '_Generated by paper.py from outputs/data/ (do not edit by hand). Figures: PNG 300 dpi and vector PDF at '
             'Nature widths (89 mm single, 183 mm double column); the source data of every figure (every plotted value) '
             'in the CSV of the same name. P1–P5 are at the Moderate setting with full roll-out by 2035; other settings '
             'are in Extended Data (../extended_data/EXTENDED_DATA.md). Vocabulary: docs/RENAMING.md; palette: '
             'docs/PALETTE.md._', '']
    if quick_run():
        lines += ['> **QUICK RUN, not for reporting** (run_all.py --quick: fewer Monte Carlo draws).', '']
    lines += ['## Findings', '']
    for i, (text, files) in enumerate(findings(rr, t2), 1):
        lines.append(f'{i}. {N.typeset(text)} (Source: {files}.)')
    lines += ['', '## Figures', '']
    for h in FP.PAPER:
        f = h['file']
        data = f"Data (outputs/): {h['source']}" if h['source'].startswith('data/') else f"Data: {h['source']}"
        lines += [f"### {h['id']}. {N.typeset(h['title'])}", '', f'![{h["id"]}]({f}.png)', '',
                  f"**{h['id']}.** {N.typeset(rr[h['id']]['caption'])}", '',
                  f"Files: [{f}.png]({f}.png)" + (f", [{f}.pdf]({f}.pdf), source data [{f}.csv]({f}.csv)"
                                                    if S.export_run() else ' (PDF and source data: run_all.py --export)')
                  + f". {data}.", '']
    lines += ['## Tables', '', '### Table 1. Levers and the theoretical-limit assumptions', '',
              'Moderate is the setting of the paper; Ambitious is reported in Extended Data. '
              + N.typeset(FP.TL_NOTE), ''] + t1md
    lines += ['', 'File: [Table1_levers.csv](Table1_levers.csv). Full text with the adoption rule: '
              '../reports/LEVERS_TABLE.md.', '',
              '### Table 2. Results 2026–2050: the Reference, P1–P5 and TL', '',
              'P1–P5 at the Moderate setting, full roll-out by 2035. In brackets: Monte Carlo 5–95% (5,000 draws of the '
              'Reference, each also run through P5 and TL). P(LoE ≤ 1): share of the draws at or below the budget. '
              'Committed after 2050: lower–upper bound, not part of the level of exceedance.', ''] + t2md
    lines += ['', 'File: [Table2_results.csv](Table2_results.csv).']
    with open(md_path(), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(N.typeset(x) if x.startswith('|') else x for x in lines) + '\n')
    return lines


def md_path():
    return L.writing(os.path.join(L.PAPER, 'PAPER.md'))


FIGURES = dict(Fig1=fig1, Fig2=fig2, Fig3=fig3, Fig4=fig4, Fig5=fig5, Fig6=fig6)


def main(only=None):
    rr = {}
    for k, fn in FIGURES.items():
        if only and k not in only:
            continue
        rr[k] = fn()
        print(f'paper: {k} {PLAN[k]["file"]}')
    if not only:
        st = read_csv('pathways/shapley_theoretical_limit.csv')
        rr['_tl_shapley'] = st[st['metric'] == 'LoE_AR'].set_index('player')['reduction'].to_dict()
        _, t1md = table1()
        t2, t2md = table2()
        for f, title, md in (('Table1_levers', FP.TABLES[0]['title'], t1md), ('Table2_results', FP.TABLES[1]['title'], t2md)):
            with open(L.writing(os.path.join(L.PAPER, f'{f}.md')), 'w', encoding='utf-8') as fh:
                fh.write('\n'.join([f"# {N.typeset(title)}", '', '_Generated by paper.py from outputs/data/ (do not edit '
                                     'by hand); the same table in PAPER.md and as CSV._', ''] +
                                    [N.typeset(x) for x in md]) + '\n')
        write_md(rr, t1md, t2md, t2)
        print(f'paper: {os.path.relpath(md_path(), ROOT)}')
    return rr


if __name__ == '__main__':
    main([a for a in sys.argv[1:] if a.startswith('Fig')] or None)
