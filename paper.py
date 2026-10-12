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
    """plotting.signed_stack_styled (net-total convention) with explicit styles: parts [(style dict, values)]."""
    return P.signed_stack_styled(ax, x, [(dict(st, **kw), v) for st, v in parts], width)


def unexplained_style():
    face, hatch, edge = S.UNEXPLAINED
    return S.fill(face, hatch, edge)


def bands_history_panel(a, src, letter='a'):
    """Floor area by demand band: history per census interval and the Reference projection (Fig2, K1). letter None:
    a single-panel figure (no panel letter; source data under 'a')."""
    show = letter is not None
    letter = letter or 'a'
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
    if show:
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
    """Fig2 (MODEL v2.1.2): floor area by demand band, one panel (the old panel a): history one column per census
    interval, the Reference projection annual; the observed annual floor area built (consents-based, as the model
    uses it) as a thin line over the history columns (explained in the caption, not in the legend)."""
    h = PLAN['Fig2']
    fid = h['file']
    src = Source(fid, L.PAPER)
    fig, a = plt.subplots(figsize=S.figsize('double', 96))
    ba = bands_history_panel(a, src, letter=None)
    an = read_csv('baseline/annual.csv')
    hb = read_csv('baseline/bands_history.csv')
    obs = an[an['source'] == 'history'].set_index('year')['floor_area_Mm2']
    y_first = int(hb['year_start'].min())
    obs = obs.loc[y_first:WINDOW[0] - 1]
    # the history columns are interval means of the same series (checked)
    for iv, g in hb.groupby('interval', sort=False):
        y0, y1 = int(g['year_start'].iloc[0]), int(g['year_end'].iloc[0])
        check(math.isclose(float(g['floor_area_Mm2_per_year'].sum()), float(obs.loc[y0:y1].mean()), rel_tol=1e-9),
              f'Fig2: the history column {iv} is not the mean of the observed floor area')
    a.plot(obs.index, obs.values, color=S.INK, lw=S.LW_THIN, zorder=6)
    lo, hi = a.get_ylim()
    a.set_ylim(lo, max(hi, float(obs.max()) * 1.12))
    src.add('a', 'Observed floor area built (consents-based, as used by the model)', obs.index, obs.values,
            'Mm2 per year')
    handles = P.band_handles(['growth', 'smaller_households', 'extra_space', 'vacancy', 'overbuild_2026', 'replacement',
                              'redevelopment'])
    for hd in handles:
        if hd.get_label() == P.band_label('replacement'):
            hd.set_label(P.band_label('replacement') + ' (history: net, census-measured)')
    handles.append(Patch(label=N.UNEXPLAINED, **dict(unexplained_style(), edgecolor='#555555', linewidth=S.LW_THIN)))
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), frameon=False,
               handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    save(fig, fid, src, h['width'])
    tot = ba.groupby('band')['floor_area_Mm2'].sum()
    unt = sum(tot.loc[N.band_data_label(b_)] for b_ in N.UNTARGETED)
    total = tot.sum()
    num = dict(untargeted_share=unt / total, total=total)
    cap = (h['caption'] + f" Over 2026–2050 the untargeted band (population growth) is {100 * num['untargeted_share']:.0f}% of the "
           f"{total:.1f} million m² built. History: interval means between censuses (vacancy on one definition, the "
           'pooled 2018/2023 empty share); the net replacement is census-measured (the census-interval rate of the '
           "dwelling-count identity × the previous year's stock) and the faded red band is the building that household "
           'formation, vacancy and census-measured replacement leave unexplained (it may be negative); the faint column '
           'after the latest census uses consent-derived households. The thin line is the observed floor area built '
           'each year (consented floor area timed as completions, as the model uses it); each history column is its '
           'interval mean. Retirement villages (out of scope) are removed from every band in proportion. '
           + P.NEGATIVE_NOTE[0].upper() + P.NEGATIVE_NOTE[1:] + ' (a negative band is drawn down from the top of the '
           'stack, so each column ends at its net total, marked by a short tick).')
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


def material_bars(ax, src, letter, years, frame, width=0.82):
    """Annual carbon by material as stacked bars (style.MATERIAL order, soil carbon loss faded and hatched on
    top)."""
    base = np.zeros(len(years))
    handles = []
    for code_, lab, col in S.MATERIAL:
        v = frame[code_].values
        st = P.material_patch(code_, col)
        ax.bar(years, v, bottom=base, width=width, gid='band_segment', **st)
        handles.append(Patch(label=lab, **dict(st, edgecolor='#555555', linewidth=S.LW_THIN)))
        src.add(letter, lab, years, v, 'kt CO2e per year')
        base = base + v
    return handles[::-1], base


def fig3():
    """Fig3 (MODEL v2.1.2): the Reference embodied carbon per year 2026-2050, 1 x 3 panels with a shared y axis:
    (a) by demand band, (b) by life-cycle stage, (c) by material. No committed carbon (Fig4 b)."""
    h = PLAN['Fig3']
    fid = h['file']
    src = Source(fid, L.PAPER)
    st = read_csv('baseline/annual_by_stage.csv').set_index('year')
    mat = read_csv('baseline/annual_by_material.csv').pivot(index='year', columns='material', values='carbon_kt')
    ba = read_csv('baseline/bands_annual.csv')
    an = read_csv('baseline/annual.csv')
    an = an[an['source'] == 'projection'].set_index('year')
    years = st.index.values
    cols = STAGE_COLS
    total = an.loc[years, 'carbon_kt'].values
    check(np.allclose(sum(st[c] for _, c in cols).values, total, rtol=1e-9, atol=0),
          'Fig3: the stages do not add up to the annual carbon')
    check(np.allclose(mat.loc[years].sum(axis=1).values, total, rtol=1e-9, atol=0),
          'Fig3: the materials do not add up to the annual carbon')
    fig = plt.figure(figsize=S.figsize('double', 92))
    gs = fig.add_gridspec(1, 3, wspace=0.10, left=0.075, right=0.985, bottom=0.36, top=0.93)
    a = fig.add_subplot(gs[0])
    b = fig.add_subplot(gs[1], sharey=a)
    c = fig.add_subplot(gs[2], sharey=a)
    # (a) by demand band (net-total convention for a negative band)
    parts = []
    for bid in N.BANDS_IN_SCOPE:
        v = ba[ba['band'] == N.band_data_label(bid)].set_index('year').loc[years, 'carbon_kt'].values
        parts.append((bid, v))
        src.add('a', N.BANDS[bid], years, v, 'kt CO2e per year')
    up, dn = P.signed_stack(a, years, parts, width=0.82)
    check(np.allclose(up + dn, total, rtol=1e-9, atol=1e-9), 'Fig3: the bands do not add up to the annual carbon')
    # (b) by life-cycle stage
    base = np.zeros(len(years))
    sh = []
    for sid, col in cols:
        face, hatch = S.STAGE[sid]
        stl = S.fill(face, hatch)
        b.bar(years, st[col].values, bottom=base, width=0.82, gid='band_segment', **stl)
        sh.append(Patch(label=N.STAGES[sid], **dict(stl, edgecolor='#555555', linewidth=S.LW_THIN)))
        src.add('b', N.STAGES[sid], years, st[col].values, 'kt CO2e per year')
        base = base + st[col].values
    # (c) by material
    mh, _ = material_bars(c, src, 'c', years, mat.loc[years])
    for ax, letter, title in ((a, 'a', 'By demand band'), (b, 'b', 'By life-cycle stage'), (c, 'c', 'By material')):
        ax.set_xlim(2025.4, 2050.6)
        ax.grid(axis='x', visible=False)
        P.panel(ax, letter, title)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(a.yaxis)
    for ax in (b, c):
        ax.tick_params(labelleft=False)
    a.set_ylim(0, max(float((up).max()), float(base.max())) * 1.05)
    leg = dict(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, handlelength=1.2,
               columnspacing=0.8, labelspacing=0.3, frameon=False)
    a.legend(handles=P.band_handles(list(N.BANDS_IN_SCOPE))[::-1], ncol=2, **leg)
    b.legend(handles=sh[::-1], ncol=2, **leg)
    c.legend(handles=mh, ncol=2, **leg)
    save(fig, fid, src, h['width'])
    tot = {sid: float(st[col].sum()) for sid, col in cols}
    num = dict(carbon=sum(tot.values()), **{f'{k}_kt': v for k, v in tot.items()},
               concrete=float(mat['CONCRETE (incl. reinforced)'].sum()), timber=float(mat['TIMBER'].sum()))
    cap = (h['caption'] + f" Of the {num['carbon']:,.0f} kt CO₂e emitted in 2026–2050, materials (A1–A3) are "
           f"{tot['a1a3']:,.0f} kt, construction (A4–A5) {tot['a4a5']:,.0f} kt, maintenance {tot['maintenance']:,.0f} kt "
           f"and soil carbon loss {tot['soil']:,.0f} kt (b); by material (c) each material includes its maintenance "
           'within 2026–2050; by demand band (a) maintenance is its own layer. The emissions committed after 2050 are '
           'in Fig4 b. ' + P.NEGATIVE_NOTE[0].upper() + P.NEGATIVE_NOTE[1:] + ' (drawn down from the top of the stack; '
           'the bar ends at its net total, marked by a short tick).')
    return dict(num, caption=cap)


def history_carbon():
    """The sector's embodied carbon of the AR base window 2016-2025 at 2025 factors (aesa/annual.csv, history), kt."""
    an = read_csv('aesa/annual.csv')
    return an[an['scenario'] == 'history'].set_index('year')['I_sec_kgCO2e'] / M6


def fig4():
    """Fig4 (MODEL v2.1.2): the Reference against the boundaries. (a) annual carbon with the Monte Carlo 5-95% band,
    the thin history line joined to the projection, the annual AR and AtP boundaries; (b) cumulative column: carbon
    2026-2050 with its Monte Carlo whisker and the emissions committed after 2050 stacked above it (hatched, no
    whisker), the cumulative budgets spanning only the 2026-2050 column, LoE AR and AtP labelled."""
    h = PLAN['Fig4']
    fid = h['file']
    src = Source(fid, L.PAPER)
    an = read_csv('pathways/annual.csv')
    an = an[(an['scenario'] == REF) & (an['run'] == REF)].set_index('year').loc[WINDOW[0]:WINDOW[1]]
    mca = read_csv('pathways/montecarlo_annual.csv')
    m = mca[mca['run'] == 'REF'].set_index('year').loc[WINDOW[0]:WINDOW[1]]
    mcs = mc_summary()
    r = runs_ref()
    hc = history_carbon()
    com = read_json('aesa/results.json')['committed'][REF]
    fig = plt.figure(figsize=S.figsize('double', 84))
    gs = fig.add_gridspec(1, 2, width_ratios=[3.1, 1], wspace=0.32, left=0.075, right=0.975, bottom=0.25, top=0.95)
    a, b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    yrs = list(an.index)
    S.boundary_zones(a, yrs, an['B_AR_kt'].values, an['B_AtP_kt'].values)
    a.fill_between(yrs, m['carbon_kt_p5'], m['carbon_kt_p95'], color=S.REFERENCE, alpha=0.18, lw=0,
                   label='Reference, Monte Carlo 5–95%')
    a.plot(yrs, an['carbon_kt'], color=S.REFERENCE, lw=S.LW_BOLD, label='Reference')
    xh = list(hc.index) + [yrs[0]]
    yh = list(hc.values) + [float(an['carbon_kt'].iloc[0])]
    a.plot(xh, yh, color=S.INK, lw=S.LW_THIN, label='History (sector carbon at 2025 factors)')
    src.add('a', 'Reference', yrs, an['carbon_kt'].values, 'kt CO2e per year')
    src.add('a', 'Reference, Monte Carlo 5%', yrs, m['carbon_kt_p5'].values, 'kt CO2e per year')
    src.add('a', 'Reference, Monte Carlo 95%', yrs, m['carbon_kt_p95'].values, 'kt CO2e per year')
    src.add('a', 'History: sector carbon at 2025 factors (AR base window)', list(hc.index), hc.values, 'kt CO2e per year')
    src.add('a', N.METRICS['AR'] + ' boundary', yrs, an['B_AR_kt'].values, 'kt CO2e per year')
    src.add('a', N.METRICS['AtP'] + ' boundary', yrs, an['B_AtP_kt'].values, 'kt CO2e per year')
    a.axvline(WINDOW[0] - 0.5, color=S.MUTED, lw=S.LW_THIN, ls=':')
    a.set_xlim(int(hc.index.min()) - 0.5, WINDOW[1] + 0.5)
    a.set_ylim(0, max(float(m['carbon_kt_p95'].max()), float(hc.max())) * 1.08)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(a.yaxis)
    P.panel(a, 'a', 'Annual carbon and boundaries')
    # (b) the cumulative column
    w = 0.55
    car = float(r.loc[REF, 'carbon_kt'])
    q = mcs.loc[('REF', 'carbon_kt')]
    bar_ar, bar_atp = float(r.loc[REF, 'B_AR_kt']), float(r.loc[REF, 'B_AtP_kt'])
    S.boundary_hzones(b, bar_ar, bar_atp, label=False, xspan=(-w / 2 - 0.12, w / 2 + 0.12))
    b.bar(0, car, width=w, gid='band_segment', **S.fill(S.REFERENCE))
    # the whisker beside the column (left), so it does not run into the committed segment above
    xw = -w / 2 - 0.07
    b.plot([xw - 0.03, xw], [car, car], color=S.INK, lw=S.LW_THIN)
    b.errorbar(xw, car, yerr=[[car - q['p5']], [q['p95'] - car]], color=S.INK, capsize=2.5, lw=S.LW_THIN,
               capthick=S.LW_THIN)
    face, hatch = S.COMPONENT['committed']
    b.bar(0, com['lower_kt'], bottom=car, width=w, facecolor='white', edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN)
    b.bar(0, com['upper_kt'] - com['lower_kt'], bottom=car + com['lower_kt'], width=w, facecolor=face,
          edgecolor=S.MUTED, hatch=hatch, lw=S.LW_THIN, alpha=0.6)
    b.text(w / 2 + 0.06, car + com['upper_kt'] / 2, f"Committed\nafter 2050\n{com['lower_kt']:,.0f}–\n"
           f"{com['upper_kt']:,.0f} kt", ha='left', va='center', fontsize=S.FONT_MIN)
    b.text(w / 2 + 0.06, car * 0.5, f"2026–2050\n{car:,.0f} kt\nLoE AR {r.loc[REF, 'LoE_AR']:.2f}\n"
           f"LoE AtP {r.loc[REF, 'LoE_AtP']:.1f}", ha='left', va='center', fontsize=S.FONT_MIN)
    for key, v in (('AR', bar_ar), ('AtP', bar_atp)):
        b.text(-w / 2 - 0.16, v, f'{key} budget\n{v:,.0f} kt', ha='right', va='center', fontsize=S.FONT_MIN,
               color=S.BOUNDARY[key]['color'])
    src.add('b', 'Reference carbon 2026-2050', 'cumulative', car, 'kt CO2e')
    src.add('b', 'Reference carbon 2026-2050, Monte Carlo 5%', 'cumulative', float(q['p5']), 'kt CO2e')
    src.add('b', 'Reference carbon 2026-2050, Monte Carlo 95%', 'cumulative', float(q['p95']), 'kt CO2e')
    src.add('b', 'Committed after 2050, lower', 'after 2050', com['lower_kt'], 'kt CO2e')
    src.add('b', 'Committed after 2050, upper', 'after 2050', com['upper_kt'], 'kt CO2e')
    src.add('b', 'AR budget 2026-2050', 'cumulative', bar_ar, 'kt CO2e')
    src.add('b', 'AtP budget 2026-2050', 'cumulative', bar_atp, 'kt CO2e')
    b.set_xlim(-1.25, 1.25)
    b.set_xticks([0])
    b.set_xticklabels(['Reference'])
    b.set_ylim(0, (car + com['upper_kt']) * 1.06)
    b.set_ylabel('Embodied carbon, cumulative (kt CO₂e)')
    P.thousands(b.yaxis)
    b.grid(axis='x', visible=False)
    P.panel(b, 'b', 'Cumulative')
    hd, _ = a.get_legend_handles_labels()
    hd += [Patch(facecolor='white', edgecolor=S.MUTED, hatch=hatch, label=N.COMPONENTS['committed'])]
    hd += S.zone_handles()
    fig.legend(handles=hd, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.01), frameon=False,
               fontsize=S.FONT_SMALL)
    save(fig, fid, src, h['width'])
    num = dict(com_lo=com['lower_kt'], com_hi=com['upper_kt'], yrs_lo=com['years_of_B_AR_2050_lower'],
               yrs_hi=com['years_of_B_AR_2050_upper'])
    cap = (h['caption'] + f" (a) Annual embodied carbon of the Reference with its Monte Carlo 5–95% band (5,000 "
           f"Latin-hypercube draws) against the annual AR and AtP boundaries; the thin line is the sector carbon of "
           f"the AR base window {int(hc.index.min())}–{int(hc.index.max())} at 2025 factors (accounting as the "
           f"projection), joined to the projection in 2026. (b) Cumulative carbon 2026–2050, {car:,.0f} kt (Monte Carlo "
           f"{q['p5']:,.0f}–{q['p95']:,.0f}), LoE AR {r.loc[REF, 'LoE_AR']:.2f} and LoE AtP {r.loc[REF, 'LoE_AtP']:.1f} "
           f"against the cumulative budgets ({bar_ar:,.0f} kt AR, {bar_atp:,.0f} kt AtP; lines over the 2026–2050 "
           f"column only); stacked above it (hatched), the emissions committed after 2050 by the 2026–2050 cohorts "
           f"(later B2/B4 and C1–C4), {com['lower_kt']:,.0f}–{com['upper_kt']:,.0f} kt by the accounting choice (lower "
           f"bound with the 2050 factors held, upper bound at 2025 factors), {num['yrs_lo']:.0f}–{num['yrs_hi']:.0f} years "
           'of the 2050 AR boundary; they are not part of the level of exceedance and carry no whisker.')
    return dict(num, caption=cap)


# ============================================================
# Fig5  Pathways: cumulative carbon by band and by stage, and the band waterfall (K5)
# ============================================================
TL_TIMING = ('by2030', 'reoccupation')
TL_TIMING_LABEL = 'TL timing (adoption by 2030, gradual re-occupation)'


def band_waterfall(ax, src, letter):
    """The sequential waterfall Reference -> P1 ... P4 (= P5) -> TL timing -> TL1 ... TL10 (= TL) of carbon
    2026-2050, every step segmented by its exact demand-band deltas (pathways/waterfall_sequential.csv), against the
    cumulative budgets. MODEL v2.1.2: TL's faster adoption and the gradual re-occupation are one step, 'TL timing'
    (values and band segments summed; checked against the step totals); a dotted vertical line separates the
    pathways from the theoretical limit; end labels sit above each bar's top. Returns the step table."""
    w = read_csv('pathways/waterfall_sequential.csv')
    steps = w.drop_duplicates('step').sort_values('step')
    bands = list(w['band'].drop_duplicates())
    bid = {N.band_data_label(b): b for b in N.BANDS_IN_SCOPE}
    rows = []                                          # (sid, label, {band: delta}, total, LoE AR)
    for _, srow in steps.iterrows():
        sid = srow['step_id']
        d = w[w['step'] == srow['step']].set_index('band')
        deltas = {b: float(d.loc[b, 'delta_carbon_kt']) for b in bands}
        if sid in TL_TIMING:
            if rows and rows[-1][0] == 'TL timing':
                prev = rows.pop()
                deltas = {b: prev[2][b] + deltas[b] for b in bands}
            rows.append(('TL timing', TL_TIMING_LABEL, deltas, float(srow['total_carbon_kt']), float(srow['LoE_AR']),
                         d))
            continue
        rows.append((sid, srow['label'], deltas, float(srow['total_carbon_kt']), float(srow['LoE_AR']), d))
    check(sum(1 for r_ in rows if r_[0] == 'TL timing') == 1, 'waterfall: the TL timing steps are missing')
    bar_ar, bar_atp = float(steps['B_AR_kt'].iloc[0]), float(steps['B_AtP_kt'].iloc[0])
    S.boundary_hzones(ax, bar_ar, bar_atp, label=False)
    width = 0.7
    labels, xs = [], []
    prev_total = None
    tops = {}
    for x, (sid, lab, deltas, tot, loe, d) in enumerate(rows):
        if sid == 'REF':
            up, dn = P.signed_stack(ax, [x], [(bid[b], float(d.loc[b, 'carbon_kt'])) for b in bands], width=width)
            top = float(up[0])
            labels.append(N.SCENARIOS['REF'])
        else:
            cur, top = float(prev_total), float(prev_total)
            for b in bands:
                dv = deltas[b]
                if dv == 0.0:
                    continue
                ax.bar(x, -dv, bottom=cur, width=width, **P.band_style(bid[b]))
                cur -= dv
                top = max(top, cur)
                src.add(letter, f'{lab}: {N.BANDS[bid[b]]}', 'reduction', dv, 'kt CO2e 2026-2050')
            check(abs(cur - tot) <= 1e-6 * max(1.0, abs(cur)), f'waterfall: the band deltas of step {sid} do not reach its '
                  'total')
            ax.plot([x - 1 + width / 2, x - width / 2], [prev_total, prev_total], color=S.MUTED, lw=S.LW_THIN)
            labels.append(textwrap.fill(lab, 24))
        src.add(letter, lab, 'total', tot, 'kt CO2e 2026-2050')
        tops[sid] = (x, top, tot, loe)
        prev_total = tot
        xs.append(x)
    for sid in ('REF', 'P4', 'TL10'):
        x, top, tot, loe = tops[sid]
        ax.text(x, top + 0.012 * bar_ar * 4, f'{tot:,.0f}\nLoE AR {loe:.2f}', ha='center', va='bottom',
                fontsize=S.FONT_MIN, linespacing=1.0)
    xsep = tops['TL timing'][0] - 0.5
    ax.axvline(xsep, color=S.INK, lw=S.LW_THIN, ls=':')
    ax.text(xsep - 0.1, 0.98, 'Pathways (P) ', transform=ax.get_xaxis_transform(), ha='right', va='top',
            fontsize=S.FONT_MIN, color=S.MUTED)
    ax.text(xsep + 0.1, 0.98, ' Theoretical limit (TL)', transform=ax.get_xaxis_transform(), ha='left', va='top',
            fontsize=S.FONT_MIN, color=S.MUTED)
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_ylim(0, max(t[1] for t in tops.values()) * 1.16)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=90, fontsize=S.FONT_MIN, linespacing=1.0)
    ax.set_xlim(-0.6, xs[-1] + 0.6)
    ax.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(ax.yaxis)
    ax.grid(axis='x', visible=False)
    return dict(rows=rows, tops=tops, B_AR=bar_ar, B_AtP=bar_atp)


def waterfall_caption(wf):
    t = wf['tops']
    tl_t = [r_ for r_ in wf['rows'] if r_[0] == 'TL timing'][0]
    return (f"Reference {t['REF'][2]:,.0f} kt (LoE AR {t['REF'][3]:.2f}), P5 {t['P4'][2]:,.0f} kt ({t['P4'][3]:.2f}), "
            f"TL {t['TL10'][2]:,.0f} kt ({t['TL10'][3]:.2f}); cumulative AR budget {wf['B_AR']:,.0f} kt, AtP "
            f"{wf['B_AtP']:,.0f} kt. TL timing ({t['P4'][2] - tl_t[3]:+,.0f} kt reduction) combines TL's faster adoption "
            '(full roll-out by 2030 instead of 2035) and the gradual re-occupation of released dwellings; the dotted '
            'line separates the pathways (P) from the theoretical limit (TL). A segment above its step\'s start marks a '
            'band that grows at that step (a lever shifts building between bands); from TL timing on, the 2026-overbuild '
            'band also carries the re-occupation of released dwellings. Sequential steps depend on the order; the '
            'order-free Shapley values are in Table 2, ED8 and ED9.')


def fig5():
    """Fig5 (MODEL v2.1.2): pathways. (a) cumulative carbon 2026-2050 by demand band and (b) by life-cycle stage for
    the Reference, P1-P5 (Moderate) and TL, with the cumulative budgets and the boundary zones; (c) full width: the
    band waterfall (as K5)."""
    h = PLAN['Fig5']
    fid = h['file']
    src = Source(fid, L.PAPER)
    bd = read_csv('pathways/bands.csv')
    bd = bd[(bd['scenario'] == REF) & (bd['definition'] == 'in_scope')]
    r = runs_ref()
    bar_ar, bar_atp = float(r.loc[REF, 'B_AR_kt']), float(r.loc[REF, 'B_AtP_kt'])
    fig = plt.figure(figsize=S.figsize('double', 205))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.25], hspace=0.30, wspace=0.22, left=0.08, right=0.98,
                          bottom=0.215, top=0.975)
    a, b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1], sharey=None)
    c = fig.add_subplot(gs[1, :])
    xt = [N.SCENARIOS[REF]] + [f'{p}\n' + textwrap.fill(N.PATHWAYS[p], 12, break_long_words=False)
                               for p in PATHWAY_IDS] + ['TL\nTheoretical\nlimit']
    ref_total = float(r.loc[REF, 'carbon_kt'])
    num = {}
    for ax, letter in ((a, 'a'), (b, 'b')):
        S.boundary_hzones(ax, bar_ar, bar_atp, label=False)
    for i, run in enumerate(STORY):
        d = bd[bd['run'] == run].set_index('band')
        parts = [(b_, float(d.loc[N.band_data_label(b_), 'carbon_kt'])) for b_ in N.BANDS_IN_SCOPE]
        up, dn = P.signed_stack(a, [i], parts, width=0.64)
        net = float(up[0] + dn[0])
        check(math.isclose(net, float(r.loc[run, 'carbon_kt']), rel_tol=1e-9), f'Fig5: the bands of {run} do not add up')
        for b_, v in parts:
            src.add('a', f'{short(run)}: {N.BANDS[b_]}', short(run), v, 'kt CO2e 2026-2050')
        stg = [(sid, float(r.loc[run, col])) for sid, col in (('a1a3', 'a1a3_kt'), ('a4a5', 'a4a5_kt'),
                                                             ('maintenance', 'maintenance_kt'),
                                                             ('soil', 'soil_carbon_loss_kt'))]
        check(math.isclose(sum(v for _, v in stg), float(r.loc[run, 'carbon_kt']), rel_tol=1e-9),
              f'Fig5: the stages of {run} do not add up')
        base = 0.0
        for sid, v in stg:
            b.bar(i, v, bottom=base, width=0.64, gid='band_segment', **S.fill(*S.STAGE[sid]))
            src.add('b', f'{short(run)}: {N.STAGES[sid]}', short(run), v, 'kt CO2e 2026-2050')
            base += v
        pc = 100 * (net / ref_total - 1)
        lab = P.fmt_kt(net) + ('' if run == REF else ('\n0%' if round(pc) == 0 else f'\n{pc:+.0f}%'))
        for ax, y in ((a, float(up[0])), (b, base)):
            ax.text(i, y, lab, ha='center', va='bottom', fontsize=S.FONT_MIN, linespacing=1.0)
        num[run] = dict(carbon=net, d_carbon=float(r.loc[run, 'delta_carbon_kt_vs_reference_pct']),
                        floor_area=float(r.loc[run, 'floor_area_Mm2']))
    for ax, letter, title in ((a, 'a', 'By demand band'), (b, 'b', 'By life-cycle stage')):
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
        ax.set_xticks(range(len(STORY)))
        ax.set_xticklabels(xt, fontsize=S.FONT_MIN)
        ax.set_ylim(0, ref_total * 1.16)
        ax.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
        P.thousands(ax.yaxis)
        ax.grid(axis='x', visible=False)
        P.panel(ax, letter, title)
    b.legend(handles=[Patch(label=N.STAGES[sid], **dict(S.fill(*S.STAGE[sid]), edgecolor='#555555',
                                                        linewidth=S.LW_THIN)) for sid in ('soil', 'maintenance', 'a4a5', 'a1a3')],
             loc='upper right', fontsize=S.FONT_MIN, frameon=True, framealpha=0.9, edgecolor='none')
    wf = band_waterfall(c, src, 'c')
    P.panel(c, 'c', 'From the Reference to the theoretical limit (sequential, by demand band)')
    for key, v in (('AR', bar_ar), ('AtP', bar_atp)):
        src.add('a', f'{key} budget 2026-2050', 'cumulative', v, 'kt CO2e')
    P.band_legend(fig, list(N.BANDS_IN_SCOPE), ncol=4, y=-0.005, extra=S.boundary_handles() + S.zone_handles())
    save(fig, fid, src, h['width'])
    cap = (h['caption'] + f" (a, b) Cumulative embodied carbon 2026–2050 of the Reference, P1–P5 (Moderate, full "
           f"roll-out by 2035) and TL by demand band and by life-cycle stage, against the cumulative AR ({bar_ar:,.0f} kt) "
           f"and AtP ({bar_atp:,.0f} kt) budgets; labels: total and change against the Reference. P5 Combined lowers "
           f"carbon by {-num['P5-moderate']['d_carbon']:.0f}% and TL by {-num['TL']['d_carbon']:.0f}%. "
           + P.NEGATIVE_NOTE[0].upper() + P.NEGATIVE_NOTE[1:] + ' (drawn down from the top of the stack; the bar ends '
           'at its net total, marked by a short tick). (c) ' + waterfall_caption(wf) + ' '
           + N.tl_caption(read_json('pathways/theoretical_limit.json')['indicators']['TL']['reoccupation']['share_of_need']))
    return dict(runs=num, caption=cap)


FIG5_RUNS = [(REF, S.REFERENCE, S.LW_BOLD), ('P5-moderate', S.PATHWAY['P5'], S.LW), ('TL', S.TL, S.LW)]


def tl_built_2027(an):
    """TL dwellings built in 2027 and the 2027-2050 minimum (constant-share reoccupation: positive in every year of
    the deterministic TL, asserted by pathways.compute_tl and here)."""
    d = an[an['run'] == 'TL'].set_index('year')['dwellings_built']
    late = d.loc[2027:WINDOW[1]]
    check((late > 0).all(), 'TL: dwellings built <= 0 in a year of 2027-2050')
    return float(d.loc[2027]), float(late.min())


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


CONTOUR_LEVELS = (2, 3, 5)


def solution_space_panel(ax, src, letter=None):
    """The solution space (after Horup et al. 2025, Fig. 6): cumulative LoE AR over uniform cuts of 2027-2050 floor
    area (x) and non-soil carbon per m2 (y), in the boundary zones, with the budget contours. MODEL v2.1.2: contour
    labels horizontal, no background box ('Acquired rights: LoE = 1', 'LoE = 2', ...; 'Ability to pay: LoE = 1' when
    it lies on the plane); P1-P5 Moderate filled, Ambitious hollow, same colours, legend only; TL a larger circle.
    Returns the numbers of the caption."""
    key = letter or 'markers'
    space = read_csv('pathways/solution_space.csv')
    bc = read_json('pathways/backcast.json')
    tl = read_json('pathways/theoretical_limit.json')['solution_space_marker']
    r = runs_ref()
    k_atp = budget_ratio(r)
    f, a0 = bilinear(space)
    atp_one = 1.0 / k_atp                                   # LoE AtP = 1 in LoE AR units
    atp_reachable = a0 < atp_one
    marks = {m['run']: m for m in bc['solution_space_markers']}
    check(all(f'{p}-{s_}' in marks for p in PATHWAY_IDS for s_ in ('moderate', 'ambitious')),
          'solution space: P1-P5 Moderate and Ambitious markers missing')
    dx = np.linspace(0, 100, 401)
    D, I = np.meshgrid(dx / 100, dx / 100)
    Z = f(D, I)
    S.boundary_field(ax, 100 * D, 100 * I, Z, 1.0, atp_one)
    lv = [v for v in CONTOUR_LEVELS if Z.min() < v < Z.max()]
    ax.contour(100 * D, 100 * I, Z, levels=lv, colors=[S.MUTED], linewidths=[S.LW_THIN], linestyles=':')
    # horizontal labels just right of each contour, staggered in y; the plane is bilinear, so the demand cut of
    # level v at intensity cut y is d = 1 - (v - a0) / (f(0, y) - a0)
    lab = [(1.0, 'Acquired rights: LoE = 1', S.AR)] + ([(atp_one, 'Ability to pay: LoE = 1', S.ATP)]
                                                       if atp_reachable else [])
    lab += [(v, f'LoE = {v:g}', S.MUTED) for v in lv]
    for k, (v, txt, col) in enumerate(lab):
        y = 92.0 if v == 1.0 else 3.5                    # budgets near the top; LoE levels near the bottom
        d_v = 1.0 - (v - a0) / (f(0.0, y / 100) - a0)
        if 0.0 < d_v < 1.0:
            ax.text(100 * d_v + 1.2, y, txt, rotation=0, ha='left', va='center', fontsize=S.FONT_MIN, color=col,
                    zorder=4)
    for p in PATHWAY_IDS:
        for s_ in ('moderate', 'ambitious'):
            m = marks[f'{p}-{s_}']
            filled = s_ == 'moderate'
            ax.plot(100 * m['demand_reduction'], 100 * m['intensity_reduction'], marker='o', ms=4.5,
                    mfc=S.PATHWAY[p] if filled else 'white', mec=S.PATHWAY[p], mew=S.LW if not filled else S.LW_THIN,
                    lw=0, clip_on=False, zorder=5)
            nm = f'{p} {N.PATHWAYS[p]}, {N.SETTINGS[s_]}'
            src.add(key, nm, 'demand reduction', 100 * m['demand_reduction'], '%')
            src.add(key, nm, 'intensity reduction', 100 * m['intensity_reduction'], '%')
            src.add(key, nm, 'cumulative LoE AR (run)', m['LoE_AR_run'], 'level of exceedance')
    ax.plot(100 * tl['demand_reduction'], 100 * tl['intensity_reduction'], mfc=S.TL, mec='white', mew=S.LW_THIN,
            lw=0, zorder=6, **S.TL_MARKER)
    for k in ('demand_reduction', 'intensity_reduction'):
        src.add(key, 'TL Theoretical limit', k.replace('_', ' '), 100 * tl[k], '%')
    src.add(key, 'TL Theoretical limit', 'cumulative LoE AR (run)', tl['LoE_AR_run'], 'level of exceedance')
    src.add(key, 'TL Theoretical limit', 'cumulative LoE AR (plane at the coordinates)',
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
    handles = [Line2D([0], [0], marker='o', mfc=S.PATHWAY[p], mec=S.PATHWAY[p], lw=0, ms=4.5,
                      label=f'{p} {N.PATHWAYS[p]}') for p in PATHWAY_IDS]
    handles += [Line2D([0], [0], marker='o', mfc=S.INK, mec=S.INK, lw=0, ms=4.5, label='Moderate (filled)'),
                Line2D([0], [0], marker='o', mfc='white', mec=S.INK, mew=S.LW, lw=0, ms=4.5, label='Ambitious (hollow)'),
                Line2D([0], [0], mfc=S.TL, mec='white', lw=0, label='TL Theoretical limit', **S.TL_MARKER)]
    mod = marks['P5-moderate']
    num = dict(tl_demand=100 * tl['demand_reduction'], tl_intensity=100 * tl['intensity_reduction'],
               p5_demand=100 * mod['demand_reduction'], p5_intensity=100 * mod['intensity_reduction'],
               cut_ref=100 * bc[REF]['cut_AR'], a0=a0, atp_one=atp_one, atp_reachable=atp_reachable,
               tl_grid=tl['LoE_AR_on_grid_at_coordinates'], tl_run=tl['LoE_AR_run'])
    return num, handles


def solution_space_caption(num):
    atp = ('The ability-to-pay contour (LoE AtP = 1) lies at LoE AR = {:.2f}.'.format(num['atp_one']) if num['atp_reachable']
           else f"LoE AtP = 1 (LoE AR {num['atp_one']:.2f}) is not reachable on the plane: the observed 2026 cohort "
                f"alone, which no cut changes, gives LoE AR {num['a0']:.2f} (LoE AtP {num['a0'] / num['atp_one']:.2f}).")
    return (f"Cutting 2027–2050 construction alone by {num['cut_ref']:.1f}% would bring the Reference to LoE AR = 1 "
            f"(back-cast); P5 (Moderate) sits at {num['p5_demand']:.0f}% demand and {num['p5_intensity']:.0f}% intensity "
            f"reduction, TL at {num['tl_demand']:.0f}% and {num['tl_intensity']:.0f}% (at these coordinates the plane "
            f"reads LoE AR {num['tl_grid']:.2f}; the TL run, with its lower soil carbon, {num['tl_run']:.2f}). Filled "
            f"markers: Moderate; hollow: Ambitious. {atp} Contours: the exact bilinear LoE of the plane, read from the 5% "
            'grid (outputs/data/pathways/solution_space.csv).')


def fig6(h=None, base=None):
    """Fig6 (MODEL v2.1.2): (a) annual emissions 2026-2050, linear axis: the Reference, P5 (Moderate) and TL, each
    with its Monte Carlo 5-95% band, against the annual boundaries; (b) the solution space (as K4)."""
    h = h or PLAN['Fig6']
    fid = h['file']
    src = Source(fid, base or L.PAPER)
    an = read_csv('pathways/annual.csv')
    an = an[an['scenario'] == REF]
    mca = read_csv('pathways/montecarlo_annual.csv')
    fig = plt.figure(figsize=S.figsize('double', 100))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1], wspace=0.30, left=0.07, right=0.985, bottom=0.30, top=0.95)
    a, b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    yrs = list(range(WINDOW[0], WINDOW[1] + 1))
    d0 = an[an['run'] == REF].set_index('year').loc[yrs]
    S.boundary_zones(a, yrs, d0['B_AR_kt'].values, d0['B_AtP_kt'].values)
    for run, col, lw in FIG5_RUNS:
        m = mca[mca['run'] == mc_key(run)].set_index('year').loc[yrs]
        a.fill_between(yrs, m['carbon_kt_p5'], m['carbon_kt_p95'], color=col, alpha=0.18, lw=0)
        d = an[an['run'] == run].set_index('year').loc[yrs]
        a.plot(yrs, d['carbon_kt'], color=col, lw=lw, label=label(run))
        src.add('a', label(run), yrs, d['carbon_kt'].values, 'kt CO2e per year')
        src.add('a', f'{label(run)}, Monte Carlo 5%', yrs, m['carbon_kt_p5'].values, 'kt CO2e per year')
        src.add('a', f'{label(run)}, Monte Carlo 95%', yrs, m['carbon_kt_p95'].values, 'kt CO2e per year')
    src.add('a', N.METRICS['AR'] + ' boundary', yrs, d0['B_AR_kt'].values, 'kt CO2e per year')
    src.add('a', N.METRICS['AtP'] + ' boundary', yrs, d0['B_AtP_kt'].values, 'kt CO2e per year')
    a.set_xlim(WINDOW[0], WINDOW[1])
    a.set_ylim(0, None)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(a.yaxis)
    P.panel(a, 'a', 'Annual emissions')
    hd, _ = a.get_legend_handles_labels()
    hd.append(Patch(facecolor=S.REFERENCE, alpha=0.18, label='Monte Carlo 5–95% (each run)'))
    a.legend(handles=hd, loc='upper right', fontsize=S.FONT_MIN, frameon=True, framealpha=0.9, edgecolor='none')
    num, handles = solution_space_panel(b, src, 'b')
    P.panel(b, 'b', 'Solution space')
    fig.legend(handles=handles + S.zone_handles(), loc='lower center', ncol=4, bbox_to_anchor=(0.5, 0.0),
               frameon=False, fontsize=S.FONT_MIN)
    save(fig, fid, src, h['width'])
    mcs = mc_summary()
    q_tl = {k: float(mcs.loc[('TL', f'LoE_{k}'), 'probability_LoE_at_most_1']) for k in ('AR', 'AtP')}
    a50 = {run: float(an[(an['run'] == run) & (an['year'] == WINDOW[1])]['carbon_kt'].iloc[0]) for run, *_ in FIG5_RUNS}
    cap = (h['caption'] + f" (a) Annual embodied carbon 2026–2050 of the Reference, P5 Combined (Moderate) and TL, each "
           'with its Monte Carlo 5–95% band (5,000 Latin-hypercube draws of the Reference, each also run through P5 and '
           'TL with the levers applied identically and the TL targets held at their absolute values), against the '
           f"annual AR and AtP boundaries. In 2050 the Reference emits {a50[REF]:,.0f} kt, P5 {a50['P5-moderate']:,.0f} kt "
           f"and TL {a50['TL']:,.0f} kt against an AR boundary of {float(d0.loc[WINDOW[1], 'B_AR_kt']):,.0f} kt and an "
           f"AtP boundary of {float(d0.loc[WINDOW[1], 'B_AtP_kt']):,.0f} kt; TL: P(LoE AR ≤ 1) = {100 * q_tl['AR']:.1f}%, "
           f"P(LoE AtP ≤ 1) = {100 * q_tl['AtP']:.1f}% (Monte Carlo). (b) " + solution_space_caption(num) + ' '
           + N.tl_caption(read_json('pathways/theoretical_limit.json')['indicators']['TL']['reoccupation']['share_of_need']))
    return dict(num, caption=cap)


def story_numbers():
    """The numbers of the findings that no single figure carries any longer (MODEL v2.1.2): LoE of the Reference, P5
    and TL with their Monte Carlo summaries, the TL gap to the AR budget and the two separate lines of the TL
    attribution."""
    r = runs_ref()
    mcs = mc_summary()
    st = read_csv('pathways/shapley_theoretical_limit.csv')
    st = st[st['metric'] == 'LoE_AR'].set_index('player')['reduction']
    tl = read_json('pathways/theoretical_limit.json')
    g = tl['gap']['TL']
    rs = g.get('residual', {})
    q = {run: {k: mcs.loc[(mc_key(run), k)] for k in ('carbon_kt', 'LoE_AR', 'LoE_AtP')} for run in (REF, 'P5-moderate', 'TL')}
    return dict(ref=float(r.loc[REF, 'LoE_AR']), p5=float(r.loc['P5-moderate', 'LoE_AR']), tl=float(r.loc['TL', 'LoE_AR']),
                q=q, p_tl={k: float(mcs.loc[('TL', f'LoE_{k}'), 'probability_LoE_at_most_1']) for k in ('AR', 'AtP')},
                p_p5={k: float(mcs.loc[('P5', f'LoE_{k}'), 'probability_LoE_at_most_1']) for k in ('AR', 'AtP')},
                within_AR=bool(g['within_AR']), margin_AR_kt=float(g.get('margin_AR_kt', float('nan'))),
                dw=rs.get('dwellings_not_built_2027_2050', float('nan')),
                faster_adoption=float(st['by2030']), reoccupation=float(st['reoccupation']),
                reoccupation_share=float(tl['indicators']['TL']['reoccupation']['share_of_need']))


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
    # MODEL v2.1.2 figure set: Fig2 floor area, Fig3 carbon, Fig4 the Reference against the boundaries (committed),
    # Fig5 the pathways, Fig6 emissions and the solution space; the LoE numbers from story_numbers()
    f2, f6 = rr['Fig2'], rr['Fig6']
    f3 = dict(rr['Fig3'], **rr['Fig4'])
    f4 = rr['Fig5']
    f5 = rr['_story']
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
        rr['_story'] = story_numbers()
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
