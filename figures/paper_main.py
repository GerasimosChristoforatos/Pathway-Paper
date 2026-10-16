"""The figures of the paper, Fig1-Fig8 (outputs/paper_main/; figure_plan.PAPER_MAIN), drawn from the data files only.

MODEL v3.3.1 order (Nature Cities, at most eight display items): Fig1 model schematic, Fig2 floor area by demand band,
Fig3 Reference carbon, Fig4 Reference against the boundaries, Fig5 three sequential waterfalls, Fig6 solution space,
Fig7 Shapley value of each lever, Fig8 uncertainty (tornado; TL against the 2050 population)."""
import re
import textwrap

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch, Rectangle

import figure_plan as FP
import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S

M = 1e6
SRC = {h['file']: h['source'] for h in FP.PAPER_MAIN}
BANDS = list(N.BANDS_IN_SCOPE)
BANDS_TL = list(N.BANDS_IN_SCOPE_TL)
RUN_COLOUR = dict(S.PATHWAY, REF=S.REFERENCE, TL=S.TL)
# MODEL v3.3.0: the PAS 2080 strategies S1-S3 and the Moderate / Ambitious Pathway (id prefix N.PATHWAY)
RUN_GROUPS = tuple(N.STRATEGIES) + (N.PATHWAY,)
GROUP_LABEL = {**{St: f'{St} {N.STRATEGIES[St]}' for St in N.STRATEGIES}, N.PATHWAY: 'Pathway (every lever)'}
PATHWAY_LABEL = {'REF': N.SCENARIOS['REF'], **GROUP_LABEL, 'TL': N.TL['TL']}
# MODEL v3.3.1: band labels of the paper legends (the data labels of naming.BANDS are unchanged)
PAPER_BAND_LABEL = {'growth': 'Population growth', 'maintenance': 'Maintenance (B2, B4)'}


def _save(fig, name, note=None):
    S.save_figure(fig, name, note=note, source=SRC[name])


def _band_frame(df, value):
    """year x band id (data label -> id), in the fixed band order."""
    t = df.pivot(index='year', columns='band', values=value)
    t.columns = [P.band_id(c) for c in t.columns]
    order = [b for b in BANDS_TL if b in t.columns]
    return t[order]


def paper_band_handles(bids):
    """Legend handles of the bands drawn (time-series figures: every band filled), with the paper labels."""
    out = P.band_handles(bids, outline=False)
    for h, b in zip(out, bids):
        if b in PAPER_BAND_LABEL:
            h.set_label(PAPER_BAND_LABEL[b])
    return out


# ---------------------------------------------------------------------------
# Fig1: model schematic (boxes and arrows; no data drawn)
# ---------------------------------------------------------------------------
FIG1_W, FIG1_H = 183.0, 96.0                  # drawing units = mm on the page
# top row: (key, label, x0, width); the levers sit under the step they act on (column key, sub-position)
FIG1_STEPS = [('population', 'Population', 1.0, 16.0), ('households', 'Households', 19.5, 19.0),
              ('dwellings', 'Dwellings', 41.0, 19.0), ('floor_area', 'Floor area', 62.5, 19.0),
              ('carbon', 'Embodied carbon\nA1–A5, soil, B2/B4', 84.0, 38.0),
              ('boundaries', 'compared with\nplanetary\nboundaries\n(AR, AtP)', 124.5, 21.0)]
FIG1_LEVER_PLACE = {'L1': ('households', None), 'L2': ('dwellings', None), 'L3': ('dwellings', None),
                    'L4': ('floor_area', None), 'L5': ('floor_area', None), 'L6': ('carbon', 'site / soil'),
                    'L7': ('carbon', 'site / soil'), 'L8': ('carbon', 'materials'), 'L9': ('carbon', 'A4–A5')}
FIG1_BAND_Y = {'S1': (56.0, 74.0), 'S2': (33.0, 53.0), 'S3': (18.0, 30.0)}   # strategy bands (bottom, top)
FIG1_PAD = {'S1': 1.5, 'S2': 4.0, 'S3': 4.0}      # space above the first lever box (room for the carbon sub-labels)


def _box(ax, x0, y0, w, h, text, edge, face='white', fontsize=S.FONT_SMALL, weight='normal', color=S.INK, lw=0.8,
         ls='-'):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle='round,pad=0,rounding_size=1.2', facecolor=face,
                                edgecolor=edge, lw=lw, ls=ls, zorder=3))
    ax.text(x0 + w / 2, y0 + h / 2, text, ha='center', va='center', fontsize=fontsize, fontweight=weight,
            color=color, zorder=4, linespacing=1.1)


def _arrow(ax, x0, y0, x1, y1, color=S.INK, ls='-', lw=0.8):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=6, color=color, lw=lw, ls=ls,
                                 zorder=4, shrinkA=0, shrinkB=0))


def fig1():
    """MODEL v3.3.1: the model as boxes and arrows. Top row: the conversion chain to embodied carbon, compared with the
    planetary boundaries; below, the three PAS 2080 strategy bands with each lever under the step it acts on; right,
    the ambition ladder of every lever (Levels 1-4). The adoption window is read from pathways/levers.json."""
    ad = D.js('pathways/levers.json')['adoption']
    fig = plt.figure(figsize=(FIG1_W * S.MM, FIG1_H * S.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, FIG1_W)
    ax.set_ylim(0, FIG1_H)
    ax.axis('off')
    top_y, top_h = 79.0, 15.0
    col = {}
    for i, (key, lab, x0, w) in enumerate(FIG1_STEPS):
        col[key] = (x0, w)
        is_pb = key == 'boundaries'
        _box(ax, x0, top_y, w, top_h, lab, edge=S.AR if is_pb else S.INK,
             fontsize=S.FONT_MIN + 0.5 if is_pb else S.FONT_SMALL,
             weight='normal' if is_pb else 'bold', ls='--' if is_pb else '-')
        if i:
            px0, pw = FIG1_STEPS[i - 1][2], FIG1_STEPS[i - 1][3]
            _arrow(ax, px0 + pw, top_y + top_h / 2, x0, top_y + top_h / 2, ls='--' if is_pb else '-')
    # strategy bands: a pale band in the strategy colour, the strategy named in the Population column
    band_x0, band_x1 = col['population'][0], col['carbon'][0] + col['carbon'][1]
    for St, (y0, y1) in FIG1_BAND_Y.items():
        ax.add_patch(Rectangle((band_x0, y0), band_x1 - band_x0, y1 - y0, facecolor=S.STRATEGY[St], alpha=0.16,
                               edgecolor='none', zorder=1))
        ax.text(band_x0 + 1.0, (y0 + y1) / 2, f'{St}\n{N.STRATEGIES[St]}', ha='left', va='center',
                fontsize=S.FONT_SIZE, fontweight='bold', color=S.STRATEGY[St], zorder=4, linespacing=1.0)
    # levers: stacked within their strategy band under their step; the carbon column split into sub-positions
    cw = (col['carbon'][1] - 3.0) / 2
    sub_x = {'site / soil': (col['carbon'][0] + 1.0, cw), 'materials': (col['carbon'][0] + 2.0 + cw, cw),
             'A4–A5': (col['carbon'][0] + (col['carbon'][1] - cw) / 2, cw)}
    slots = {}
    lever_h = 7.0
    for L, (key, sub) in FIG1_LEVER_PLACE.items():
        St = N.LEVER_STRATEGY[L]
        x0, w = sub_x[sub] if sub else (col[key][0] + 1.0, col[key][1] - 2.0)
        y0, y1 = FIG1_BAND_Y[St]
        k = slots.get((St, key, sub), 0)
        slots[(St, key, sub)] = k + 1
        yb = y1 - FIG1_PAD[St] - (k + 1) * lever_h - k * 1.5
        text = '\n'.join(textwrap.wrap(f'{L} {N.LEVERS[L]}', 17))
        _box(ax, x0, yb, w, lever_h, text, edge=S.STRATEGY[St], fontsize=S.FONT_MIN, lw=0.9)
    for sub, (x0, w) in sub_x.items():                       # what the carbon levers act on
        St = 'S3' if sub == 'A4–A5' else 'S2'
        ax.text(x0 + w / 2, FIG1_BAND_Y[St][1] - 0.5, sub, ha='center', va='top', fontsize=S.FONT_MIN,
                color=S.MUTED, style='italic', zorder=4)
    # ambition ladder: two rails, four rungs (Level 1 at the bottom), an arrow of increasing ambition
    lx0, lx1 = 151.0, 155.0
    rungs = [('Reference', 'Level 1: observed trends', S.REFERENCE),
             ('Moderate Pathway', 'Level 2: midpoint', S.PATHWAY[N.PATHWAY]),
             ('Ambitious Pathway', 'Level 3: documented frontier', S.PATHWAY[N.PATHWAY]),
             ('Theoretical Limit', 'Level 4: physical or\nbest-observed limit', S.TL)]
    ry = np.linspace(24.0, 86.0, len(rungs))
    for x in (lx0, lx1):
        ax.plot([x, x], [ry[0] - 5, ry[-1] + 5], color=S.INK, lw=0.9, zorder=3)
    for y, (name, desc, c) in zip(ry, rungs):
        ax.plot([lx0, lx1], [y, y], color=c, lw=2.2, solid_capstyle='butt', zorder=4)
        ax.text(lx1 + 2.0, y + 1.2, name, ha='left', va='bottom', fontsize=S.FONT_SMALL, fontweight='bold', color=c)
        ax.text(lx1 + 2.0, y + 0.6, desc, ha='left', va='top', fontsize=S.FONT_MIN, color=S.INK, linespacing=1.05)
    _arrow(ax, lx0 - 3.0, ry[0], lx0 - 3.0, ry[-1], color=S.MUTED, lw=0.7)
    ax.text(lx0 - 4.2, (ry[0] + ry[-1]) / 2, 'ambition (every lever)', rotation=90, ha='right', va='center',
            fontsize=S.FONT_MIN, color=S.MUTED)
    ax.text(FIG1_W / 2, 10.0, f"Levers adopt on a logistic path, full by {ad['end']}", ha='center', va='center',
            fontsize=S.FONT_MIN + 0.5, style='italic', color=S.MUTED)
    _save(fig, 'Fig1_model_schematic',
          note=f"Adoption: {ad['form']}, from {ad['start']} (w = 0) to {ad['end']} (w = 1). Lever names from "
               'naming.LEVERS; strategy colours style.STRATEGY.')


# ---------------------------------------------------------------------------
# Fig2: floor area, history (census intervals) and the Reference projection by demand band
# ---------------------------------------------------------------------------
FIG2_GAP = 0.10                 # the gap between census-interval columns, as a share of the interval width


def fig2():
    """MODEL v3.3.1 (from Fig1): history as census-interval columns separated by a small gap (FIG2_GAP of each interval,
    split between its two sides; none at the history | projection join), the projection annual from 2026, each year
    drawn over its own width (2025.5-2050.5) so history and projection meet at 2025.5 (a thin dotted line)."""
    hist = D.csv('baseline/bands_history.csv')
    proj = _band_frame(D.csv('baseline/bands_annual.csv'), 'floor_area_Mm2')
    ann = D.csv('baseline/annual.csv')
    ob = D.js('baseline/overbuild_2026.json')
    tot = ann[ann['source'] == 'projection'].set_index('year')['floor_area_Mm2']
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    ivs = hist[['interval', 'year_start', 'year_end']].drop_duplicates().sort_values('year_start').reset_index(drop=True)
    edges = list(ivs['year_start'] - 0.5) + [float(ivs['year_end'].iloc[-1]) + 0.5]
    hb = {}
    for k, iv in ivs.iterrows():
        h = hist[hist['interval'] == iv['interval']]
        a, b = edges[k], edges[k + 1]
        w = b - a
        a, b = a + FIG2_GAP / 2 * w, (b - FIG2_GAP / 2 * w if k < len(ivs) - 1 else b)
        parts = [(P.band_id(lab), np.array([v, v], float)) for lab, v in zip(h['band'], h['floor_area_Mm2_per_year'])]
        for bid, v in parts:
            hb.setdefault(bid, []).append(float(v[0]))
        obs = float(h['observed_built_Mm2_per_year'].iloc[0])
        # MODEL v3.2.0 (A3): the bands of the data add up to the observed floor area built
        P.stack_series(ax, [a, b], parts, net=[obs, obs], net_line=False)
        ax.plot([a, b], [obs, obs], color=S.INK, lw=S.LW, gid=P.NET_GID)
    years = proj.index.values.astype(float)
    xs = np.concatenate([[years[0] - 0.5], years, [years[-1] + 0.5]])
    ext = lambda v: np.concatenate([[v[0]], v, [v[-1]]])
    net = tot.loc[proj.index].values
    P.stack_series(ax, xs, [(b, ext(proj[b].values)) for b in proj.columns if b != 'maintenance'], net=ext(net),
                   net_line=False)
    ax.plot(xs, ext(net), color=S.INK, lw=S.LW, gid=P.NET_GID)
    P.split(ax)
    ax.set_xlim(edges[0] + FIG2_GAP / 2 * (edges[1] - edges[0]), xs[-1])
    lo_, hi_ = ax.get_ylim()
    ax.set_ylim(lo_, hi_ + 0.08 * (hi_ - lo_))                         # room for the two labels
    ax.set_ylabel('Floor area built (Mm² per year)')
    ax.text(P.HISTORY_SPLIT - 0.6, 0.98, 'History (census-interval means)', transform=ax.get_xaxis_transform(),
            ha='right', va='top', fontsize=S.FONT_SMALL, color=S.MUTED)
    ax.text(P.HISTORY_SPLIT + 0.6, 0.98, 'Projection (annual; 2026 observed)', transform=ax.get_xaxis_transform(),
            ha='left', va='top', fontsize=S.FONT_SMALL, color=S.MUTED)
    neg = [b for b in proj.columns if (proj[b] < 0).any()]
    neg += [b for b in hb if b not in neg and any(v < 0 for v in hb[b])]
    present = [b for b in BANDS if b in proj.columns and (proj[b].abs() > 1e-12).any() and b != 'maintenance']
    hist_only = [b for b in hb if b not in present and any(abs(v) > 1e-12 for v in hb[b])]
    handles = paper_band_handles(present + hist_only)                    # only the bands present
    handles += [Line2D([0], [0], color=S.INK, lw=S.LW, label='Floor area built (in scope)')]
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.02), frameon=False,
               fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    _save(fig, 'Fig2_floor_area',
          note=f"2026 overbuild: observed 2026 building above need, fading from 2027 (ρ = {ob['rho']:.2f}) and absorbed "
               f"by {ob['absorption_end']}. Negative bands drawn down from zero: "
               f"{', '.join(P.band_label(b) for b in neg)}. 2026-2050: {net.sum():.1f} Mm².")


# ---------------------------------------------------------------------------
# Fig3: Reference carbon by demand band, material and stage
# ---------------------------------------------------------------------------
def fig3():
    band = _band_frame(D.csv('baseline/bands_annual.csv'), 'carbon_kt')
    mat = D.csv('baseline/annual_by_material.csv').pivot(index='year', columns='material', values='carbon_kt')
    stg = D.csv('baseline/annual_by_stage.csv').set_index('year')
    years = band.index.values.astype(float)
    total = stg['carbon_kt'].values
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 78), sharey=True)
    P.stack_series(ax[0], years, [(b, band[b].values) for b in band.columns], net=total)
    P.panel(ax[0], 'a', 'By demand band')
    P.stack_materials(ax[1], years, mat, 1.0)
    P.panel(ax[1], 'b', 'By material')
    parts = [('a1a3', stg['a1a3_kt']), ('a4a5', stg['a4a5_kt']), ('soil', stg['soil_carbon_loss_kt']),
             ('maintenance', stg['maintenance_kt'])]
    P.nonnegative('stage', *[v.values for _, v in parts])
    bottom = np.zeros(len(years))
    for k, v in parts:
        ax[2].fill_between(years, bottom, bottom + v.values, label=N.STAGES[k], **S.fill(*S.STAGE[k][:1]))
        bottom = bottom + v.values
    if not np.allclose(bottom, total, rtol=1e-9):
        raise SystemExit('STOP: Fig3: the stages do not add up to the annual carbon.')
    P.panel(ax[2], 'c', 'By life-cycle stage')
    for a in ax:
        a.set_xlim(years[0], years[-1])
        P.thousands(a.yaxis)
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[2].legend(loc='upper right', fontsize=S.FONT_MIN)
    mh = [Patch(label=lab, **P.material_patch(code, c)) for code, lab, c in S.MATERIAL][::-1]
    ax[1].legend(handles=mh, loc='upper right', fontsize=S.FONT_MIN)
    shown = [b for b in BANDS if b in band.columns and (band[b].abs() > 1e-12).any()]      # only the bands present
    fig.legend(handles=paper_band_handles(shown) + [Line2D([0], [0], color=S.INK, lw=S.LW, label='Carbon (in scope)')],
               loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.01), frameon=False, handlelength=1.4,
               columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    _save(fig, 'Fig3_reference_carbon', note=f'2026-2050: {total.sum():,.0f} kt CO₂e.')


# ---------------------------------------------------------------------------
# Fig4: the Reference against the boundaries (Monte Carlo); cumulative column and the committed emissions by stage
# ---------------------------------------------------------------------------
def fig4():
    """MODEL v3.3.1 (from Fig3): (a) annual, Monte Carlo bands against AR and AtP, a minimal legend (lines and the two
    budget zones); (b) the cumulative 2026-2050 column with the AR / AtP budgets, and the committed emissions after 2050
    by stage only (C1-C4; B2/B4 after 2050 as a range: lower = 2050 factors held, upper = 2025 factors), labelled on
    the bar."""
    mc = D.csv('montecarlo/annual_REF.csv').set_index('year')
    a = D.csv('aesa/annual.csv')
    a = a[(a['scenario'] == 'REF') & (a['year'] >= 2026)].set_index('year')
    proj = D.js('baseline/projection.json')
    years = a.index.values.astype(float)
    fig = plt.figure(figsize=S.figsize('double', 88))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.3, 1.2], wspace=0.28)
    ax = fig.add_subplot(gs[0])
    ar, atp = a['B_AR_kgCO2e'].values / M, a['B_AtP_kgCO2e'].values / M
    S.boundary_zones(ax, years, ar, atp)
    q = {p: mc.loc[years.astype(int), f'carbon_{p}'].values / M for p in (5, 25, 50, 75, 95)}
    ax.fill_between(years, q[5], q[95], color=S.REFERENCE, alpha=0.12, lw=0, label='Monte Carlo 90% band')
    ax.fill_between(years, q[25], q[75], color=S.REFERENCE, alpha=0.25, lw=0, label='Monte Carlo 50% band')
    ax.plot(years, q[50], color=S.REFERENCE, lw=S.LW_BOLD, label='Monte Carlo median')
    ax.set_xlim(years[0], years[-1])
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.panel(ax, 'a', 'Annual: the Reference against AR and AtP')
    zones = [h for h in S.zone_handles() if h.get_label() != S.ZONE['exceeded']['label']]
    ax.legend(handles=ax.get_legend_handles_labels()[0] + zones, loc='upper right', fontsize=S.FONT_MIN)
    b = fig.add_subplot(gs[1])
    c = float(proj['carbon_kt'])
    com = proj['committed']
    wd = 0.55
    b.bar([0], [c], width=wd, **S.fill(S.REFERENCE))
    b.text(0, c * 1.01, f'{c:,.0f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
    bar_, batp = float(a['B_AR_kgCO2e'].sum()) / M, float(a['B_AtP_kgCO2e'].sum()) / M
    for v, key in ((bar_, 'AR'), (batp, 'AtP')):
        st = {k: val for k, val in S.BOUNDARY[key].items() if k != 'label'}
        b.plot([-0.42, 0.42], [v, v], gid='boundary', **st)
        b.text(-0.44, v, f'{key} budget\n{v:,.0f}', ha='right', va='center', fontsize=S.FONT_MIN, color=st['color'])
    # committed after 2050, by stage: C1-C4 at the bottom, B2/B4 lower (solid) and its range to the upper (hollow)
    cc, bl, bu = float(com['C_kt']), float(com['B_lower_kt']), float(com['B_upper_kt'])
    b.bar([1], [cc], width=wd, **S.fill(S.COMPONENT['committed'][0]))
    b.bar([1], [bl], bottom=[cc], width=wd, **S.fill(S.COMPONENT['maintenance'][0]))
    b.bar([1], [bu - bl], bottom=[cc + bl], width=wd, facecolor='none', edgecolor=S.COMPONENT['maintenance'][0],
          lw=S.LW_OUTLINE)
    lab = dict(ha='left', va='center', fontsize=S.FONT_MIN, color=S.INK)
    b.text(1 + wd / 2 + 0.04, cc / 2, f'C1–C4\n{cc:,.0f}', **lab)
    b.text(1 + wd / 2 + 0.04, cc + bu / 2, f'B2/B4 after 2050\n{bl:,.0f}–{bu:,.0f}', **lab)
    b.set_xlim(-1.3, 1.9)
    b.set_xticks([0, 1])
    b.set_xticklabels(['2026–2050', 'Committed\nafter 2050'], fontsize=S.FONT_MIN + 0.5)
    b.set_ylim(0, max(c, bar_, cc + bu) * 1.12)
    b.set_ylabel('Cumulative carbon (kt CO₂e)')
    P.thousands(b.yaxis)
    b.grid(axis='x', visible=False)
    P.panel(b, 'b', 'Cumulative')
    _save(fig, 'Fig4_reference_boundaries',
          note=f'Cumulative 2026-2050 {c:,.0f} kt (LoE AR {c / bar_:.2f}, AtP {c / batp:.1f}); committed after 2050 '
               f'{com["lower_kt"]:,.0f}-{com["upper_kt"]:,.0f} kt: C1-C4 {cc:,.0f} kt (2025 factors) and B2/B4 after '
               f'2050 {bl:,.0f} kt (2050 factors held) to {bu:,.0f} kt (2025 factors).')


# ---------------------------------------------------------------------------
# Fig5: three sequential waterfalls from the Reference (net steps coloured by strategy)
# ---------------------------------------------------------------------------
def _step_strategy(step_id):
    """The PAS 2080 strategy of a waterfall step (Ln, or TLn = Level 4 of Ln)."""
    return N.LEVER_STRATEGY[N.TL_LIMIT_OF.get(step_id, step_id)]


def waterfall_paths():
    """MODEL v3.3.1 (Fig5): the three sequential paths from the Reference, [(panel key, end label, end colour,
    [(step id, total kt)])]: Reference -> L1 ... L9 at Moderate and at Ambitious (pathways/waterfall.csv, the lever
    steps) and Reference -> TL1 ... TL9 cumulative (pathways/waterfall_tl_from_reference.csv)."""
    w = D.csv('pathways/waterfall.csv')
    wt = D.csv('pathways/waterfall_tl_from_reference.csv')
    out = []
    last = list(N.LEVERS)[-1]
    for s in ('moderate', 'ambitious'):
        g = w[w['setting'] == s].groupby(['step', 'step_id'])['total_carbon_kt'].first().reset_index()
        k = int(g.index[g['step_id'] == last][0])
        out.append((s, N.PATHWAY_RUNS[f'{N.PATHWAY}-{s}'], S.PATHWAY[N.PATHWAY],
                    list(zip(g['step_id'][:k + 1], g['total_carbon_kt'][:k + 1]))))
    g = wt.groupby(['step', 'step_id'])['total_carbon_kt'].first().reset_index()
    out.append(('tl', N.TL['TL'], S.TL, list(zip(g['step_id'], g['total_carbon_kt']))))
    return out, float(w['B_AR_kt'].iloc[0]), float(w['B_AtP_kt'].iloc[0])


def _net_waterfall_panel(ax, steps, end_lab, end_col):
    """One waterfall: the Reference bar, each step ONE solid bar from the previous total to the new total in its
    strategy's colour (a net increase drawn upward), its net change on top, and the end bar. Returns the net
    increases [(step id, kt)]."""
    x = np.arange(len(steps) + 1)
    wd = 0.72
    tot = [t for _, t in steps]
    ax.bar(x[0], tot[0], width=wd, gid='band_segment', **S.fill(S.REFERENCE))
    ax.text(x[0], tot[0] * 1.01, f'{tot[0]:,.0f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
    ups = []
    for i in range(1, len(steps)):
        sid, new = steps[i]
        prev = tot[i - 1]
        d = new - prev
        if d > 0:
            ups.append((sid, d))
        col = S.STRATEGY[_step_strategy(sid)]
        ax.bar(x[i], abs(d), bottom=min(prev, new), width=wd, gid='band_segment', **S.fill(col))
        ax.plot([x[i - 1] + wd / 2, x[i] - wd / 2], [prev, prev], color=S.MUTED, lw=S.LW_THIN * 0.7, zorder=4)
        ax.text(x[i], max(prev, new) + 0.012 * tot[0], f'{d:+,.0f}'.replace('-', '−'), ha='center', va='bottom',
                fontsize=S.FONT_MIN, rotation=90)
    ax.plot([x[-2] + wd / 2, x[-1] - wd / 2], [tot[-1], tot[-1]], color=S.MUTED, lw=S.LW_THIN * 0.7, zorder=4)
    ax.bar(x[-1], tot[-1], width=wd, gid='band_segment', **S.fill(end_col))
    ax.text(x[-1], tot[-1] * 1.01 + 0.004 * tot[0], f'{tot[-1]:,.0f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
    labels = [N.SCENARIOS['REF']] + [sid for sid, _ in steps[1:]] + [end_lab.replace(' ', '\n', 1)]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=S.FONT_MIN, rotation=90)
    for t, sid in zip(ax.get_xticklabels()[1:-1], [s for s, _ in steps[1:]]):
        t.set_color(S.STRATEGY[_step_strategy(sid)])
    ax.set_xlim(-0.6, len(x) - 0.4)
    ax.grid(axis='x', visible=False)
    return ups


def fig5():
    """MODEL v3.3.1: three panels sharing the axis, each sequential from the Reference in PAS 2080 lever order: (a)
    -> Moderate Pathway, (b) -> Ambitious Pathway, (c) TL1 ... TL9 cumulative -> Theoretical Limit; one net bar per
    step coloured by strategy; AR / AtP and the zones. The split by demand band is ED6."""
    paths, bar_, batp = waterfall_paths()
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 92), sharey=True)
    ups = {}
    for a, (key, lab, col, steps), letter in zip(ax, paths, 'abc'):
        S.boundary_hzones(a, bar_, batp)
        ups[key] = _net_waterfall_panel(a, steps, lab, col)
        P.panel(a, letter, f'{N.SCENARIOS["REF"]} → {lab}')
    ax[0].set_ylim(0, max(paths[0][3][0][1], bar_) * 1.1)
    ax[0].set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax[0].yaxis)
    h = [Patch(label=f'{St} {N.STRATEGIES[St]}', **S.fill(S.STRATEGY[St])) for St in N.STRATEGIES]
    fig.legend(handles=h + S.boundary_handles() + S.zone_handles(), loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.01), frameon=False, handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    up_txt = '; '.join(f'{k}: ' + ', '.join(f'{s} {d:+,.1f} kt' for s, d in v) for k, v in ups.items() if v)
    _save(fig, 'Fig5_waterfall',
          note='Reference ' + f'{paths[0][3][0][1]:,.0f} kt -> ' + ', '.join(f'{lab} {steps[-1][1]:,.0f} kt'
                                                                         for _, lab, _, steps in paths)
               + f'; budgets AR {bar_:,.0f} kt, AtP {batp:,.0f} kt. Steps in PAS 2080 order; each step is credited with '
               'what remains after the higher-priority measures; order-free Shapley values in Fig7. Net-positive steps: '
               + (up_txt if up_txt else 'none') + '.')


# ---------------------------------------------------------------------------
# Fig6: the solution space against AR and AtP
# ---------------------------------------------------------------------------
FIG6_LIM = (-0.05, 1.10)       # MODEL v3.3.1: both axes from -5% to 110%
FIG6_N = 461                   # grid points per axis (0.25% steps)


def fig6_loe(bc, x, y):
    """LoE_AR of the analytic plane (MODEL v3.2.0, B2): [C_2026 + C_ref,2027-2050 (1 - x)(1 - y)] / B_AR, C_2026 = the
    2026 cohort's emissions in the window (identical in every run), C_ref,2027-2050 = every emission in the window of the
    Reference's 2027-2050 cohorts (A1-A5, soil carbon loss, in-window B2/B4); x = cut in 2027-2050 floor area, y = cut
    in total carbon per m2 (y > 1: carbon-negative buildings; x > 1: negative construction)."""
    r = bc['REF']
    return (r['carbon_fixed_2026_cohort_kt'] + r['carbon_2027_2050_cohorts_kt'] * (1.0 - x) * (1.0 - y)) / bc['B_AR_kt']


def fig6_k(bc, level):
    """The constant of the iso-line LoE_AR = level: (1 - x)(1 - y) = k = (level B_AR - C_2026) / C_ref,2027-2050."""
    r = bc['REF']
    return (level * bc['B_AR_kt'] - r['carbon_fixed_2026_cohort_kt']) / r['carbon_2027_2050_cohorts_kt']


def fig6_curve(bc, x, level):
    """The iso-line LoE_AR(x, y) = level as y(x) = 1 - k / (1 - x) (x != 1). level = 1: the AR line; level =
    B_AtP / B_AR: the AtP contour (k < 0 when C_2026 > B_AtP: its branch with x < 1 has y > 1)."""
    return 1.0 - fig6_k(bc, level) / (1.0 - np.asarray(x, float))


def fig6_curve_x(bc, y, level):
    """MODEL v3.3.1: the same iso-line as x(y) = 1 - k / (1 - y) (y != 1); for the AtP contour with k < 0 the branch
    with y < 1 has x > 1 (negative construction)."""
    return 1.0 - fig6_k(bc, level) / (1.0 - np.asarray(y, float))


def fig6_branches(bc, level, lim=FIG6_LIM, n=4000):
    """The branches of the iso-line LoE_AR = level inside the square lim x lim, [(x, y)] arrays: for k < 0 the branch
    x < 1, y > 1 and the branch y < 1, x > 1; for k > 0 the branch x < 1, y < 1 (the other branch, x, y > 1, lies
    outside the square when k > (lim[1] - 1)^2)."""
    lo, hi = lim
    k = fig6_k(bc, level)
    out = []
    t = np.linspace(lo, 1.0 - 1e-9, n)
    for which in ('y_of_x', 'x_of_y'):
        if which == 'x_of_y' and k >= 0:
            continue
        if which == 'y_of_x':
            x, y = t, fig6_curve(bc, t, level)
        else:
            y, x = t, fig6_curve_x(bc, t, level)
        ok = (x >= lo) & (x <= hi) & (y >= lo) & (y <= hi)
        if ok.any():
            out.append((x[ok], y[ok]))
    return out


def fig6():
    """MODEL v3.3.1: x = cut in 2027-2050 floor area, y = cut in 2027-2050 total carbon per m2 (A1-A5, soil and
    maintenance of the new cohorts), both vs the Reference, from -5% to 110%. The zones from the analytic LoE_AR field
    over the whole square (x < 0 or y < 0: more than the Reference); hatched (light, sparse) y > 100% carbon-negative
    buildings and x > 100% negative construction; analytic LoE_AR contours, the AR line and both branches of the AtP
    contour, exact; markers: S1-S3 (Moderate filled, Ambitious hollow), the Moderate / Ambitious Pathway and TL at
    their effective coordinates (the analytic LoE at each marker equals the run's LoE AR: tests)."""
    from figures import audit as figaudit
    bc = D.js('pathways/backcast.json')
    r = bc['REF']
    lo, hi = FIG6_LIM
    atp_level = bc['B_AtP_kt'] / bc['B_AR_kt']                    # LoE_AtP = 1  <=>  LoE_AR = B_AtP / B_AR
    g = np.linspace(lo, hi, FIG6_N)
    X, Y = np.meshgrid(g, g)
    Z = fig6_loe(bc, X, Y)
    fig, ax = plt.subplots(figsize=S.figsize('double', 120))
    S.boundary_field(ax, 100 * X, 100 * Y, Z, 1.0, atp_level, lines=False)
    for key, level in (('AR', 1.0), ('AtP', atp_level)):           # the budget iso-lines, exact, every branch
        st = {k: v for k, v in S.BOUNDARY[key].items() if k != 'label'}
        for xb, yb in fig6_branches(bc, level):
            ln, = ax.plot(100 * xb, 100 * yb, zorder=3, **st)
            ln.set_gid(figaudit.BOUNDARY)
    hatch = dict(facecolor='none', edgecolor=S.MUTED, hatch='/', lw=0, alpha=0.35, zorder=1)
    ax.fill_between([100 * lo, 100 * hi], 100, 100 * hi, **hatch)              # y > 100%
    ax.fill_betweenx([100 * lo, 100 * hi], 100, 100 * hi, **hatch)             # x > 100%
    for f in (ax.axhline, ax.axvline):
        f(100, color=S.MUTED, lw=S.LW_THIN * 0.7, zorder=2)
        f(0, color=S.INK, lw=S.LW_THIN * 0.7, zorder=2)
    ax.text(2, 100 * (1.0 + hi) / 2, 'carbon-negative buildings', ha='left', va='center', fontsize=S.FONT_MIN + 0.5,
            color=S.INK, zorder=4)
    ax.text(100 * (1.0 + 0.7 * (hi - 1.0)), 30, 'negative construction', rotation=90, ha='center', va='center',
            fontsize=S.FONT_MIN + 0.5, color=S.INK, zorder=4)
    zmin, zmax = float(Z.min()), float(Z.max())
    levels = [v for v in (1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8) if zmin < v < zmax]
    cs = ax.contour(100 * X, 100 * Y, Z, levels=levels, colors=S.MUTED, linewidths=S.LW_THIN * 0.7)
    ax.clabel(cs, fmt=lambda v: f'LoE AR {v:g}', fontsize=S.FONT_MIN)
    for m in bc['solution_space_markers']:
        run = m['run']
        xm, ym = 100 * m['demand_reduction'], 100 * m['intensity_reduction']
        if run == 'TL':
            ax.plot(xm, ym, color=S.TL, ls='none', **S.TL_MARKER, zorder=6)
            continue
        P_, st = run.split('-')
        ax.plot(xm, ym, marker='o', ms=5 if P_ != N.PATHWAY else 6.5, ls='none', color=S.PATHWAY[P_],
                markerfacecolor=S.PATHWAY[P_] if st == 'moderate' else 'none', markeredgewidth=1.0, zorder=5)
    c26 = r['carbon_fixed_2026_cohort_kt']
    ax.text(2, 93, f'2026 (observed) alone emits {c26:,.0f} kt = {c26 / bc["B_AtP_kt"]:.2f} × the 2026–2050 AtP '
            'budget\nAtP requires negative construction or carbon-negative buildings', ha='left', va='top',
            fontsize=S.FONT_MIN + 0.5, color=S.BOUNDARY['AtP']['color'], zorder=4, linespacing=1.3)
    ax.set_xlabel('Cut in 2027-2050 floor area vs the Reference (%)')
    ax.set_ylabel('Cut in 2027-2050 carbon per m² (A1-A5, soil, B2/B4) vs the Reference (%)')
    ax.set_xlim(100 * lo, 100 * hi)
    ax.set_ylim(100 * lo, 100 * hi)
    ax.set_aspect('equal')
    ax.grid(False)
    h = [Line2D([0], [0], marker='o', ls='none', color=S.PATHWAY[P_], markerfacecolor=S.PATHWAY[P_], ms=5,
                label=GROUP_LABEL[P_] if P_ != N.PATHWAY else 'Moderate / Ambitious Pathway') for P_ in RUN_GROUPS]
    h += [Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor=S.MUTED, ms=5, label='Moderate'),
          Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor='none', ms=5, label='Ambitious'),
          Line2D([0], [0], ls='none', color=S.TL, label=N.TL['TL'], **S.TL_MARKER),
          Patch(facecolor='white', edgecolor=S.MUTED, hatch='//', lw=0.5, label='Beyond 100% cut')]
    h += S.boundary_handles() + S.zone_handles()
    fig.legend(handles=h, loc='center left', bbox_to_anchor=(0.70, 0.5), frameon=False, fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0, 0.70, 1))
    k_atp = fig6_k(bc, atp_level)
    note = (f"LoE AR = [{c26:,.0f} + {r['carbon_2027_2050_cohorts_kt']:,.0f} (1 - x)(1 - y)] / {bc['B_AR_kt']:,.0f} kt; "
            f"C_2026 = the 2026 cohort's emissions in the window. AtP contour (1 - x)(1 - y) = {k_atp:.5f} < 0 "
            f"(C_2026 > B_AtP): one branch with y > 100% (y = {100 * float(fig6_curve(bc, 0.0, atp_level)):.1f}% at "
            f"x = 0), one with x > 100% (x = {100 * float(fig6_curve_x(bc, 0.0, atp_level)):.1f}% at y = 0). Axes "
            f"{100 * lo:.0f}% to {100 * hi:.0f}%.")
    _save(fig, 'Fig6_solution_space', note=note)


# ---------------------------------------------------------------------------
# Fig7: Shapley value of each lever (Moderate hollow, Ambitious filled, TL dot)
# ---------------------------------------------------------------------------
def fig7():
    """MODEL v3.3.0 (Fig8 until v3.3.1): rows grouped by PAS 2080 strategy (S1 Avoid, S2 Switch, S3 Improve) in the
    lever order, each bar in its strategy's colour; Moderate hollow, Ambitious filled, TL dot (games from the
    Reference)."""
    s = D.csv('pathways/shapley.csv')
    s = s[s['metric'] == 'carbon_kt']
    g = {k: s[s['game'] == f'levers_{k}'].set_index('player')['reduction'] for k in ('moderate', 'ambitious', 'tl')}
    gs = {k: s[s['game'] == f'strategies_{k}'].set_index('player')['reduction'] for k in ('moderate', 'ambitious')}
    order = list(N.LEVERS)                                     # top to bottom: L1 .. L9
    y = np.arange(len(order))[::-1]
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    for k, L in zip(y, order):
        col = S.STRATEGY[N.LEVER_STRATEGY[L]]
        ax.barh(k + 0.18, g['ambitious'][L], height=0.34, color=col, edgecolor=col, lw=S.LW_SEAM)
        ax.barh(k - 0.18, g['moderate'][L], height=0.34, facecolor='none', edgecolor=col, lw=S.LW_OUTLINE * 1.2)
        ax.plot(g['tl'][L], k, ls='none', color=S.TL, zorder=5, **S.TL_MARKER)
    for St, ls in N.STRATEGY_LEVERS.items():                  # strategy separators and labels
        ks = [k for k, L in zip(y, order) if L in ls]
        if min(ks) > 0:
            ax.axhline(min(ks) - 0.5, color=S.MUTED, lw=S.LW_THIN * 0.7)
        ax.text(1.005, (min(ks) + max(ks)) / 2, f'{St} {N.STRATEGIES[St]}', transform=ax.get_yaxis_transform(),
                ha='left', va='center', fontsize=S.FONT_MIN + 0.5, color=S.STRATEGY[St], fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels([f'{L} {N.LEVERS[L]}' for L in order])
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.axvline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_xlabel('Reduction of cumulative carbon 2026-2050 vs the Reference (kt CO₂e; exact Shapley value)')
    P.thousands(ax.xaxis)
    ax.legend(handles=[Patch(facecolor='none', edgecolor=S.MUTED, label='Moderate (Level 2)'),
                       Patch(facecolor=S.MUTED, edgecolor=S.MUTED, label='Ambitious (Level 3)'),
                       Line2D([0], [0], ls='none', color=S.TL, label='Theoretical limit (Level 4)', **S.TL_MARKER)],
              loc='lower right')
    fig.tight_layout(rect=(0, 0, 0.9, 1))
    tot = {k: v.sum() for k, v in g.items()}
    strat = '; '.join(f"{St} {N.STRATEGIES[St]} {gs['moderate'][St]:,.0f} / {gs['ambitious'][St]:,.0f} kt"
                      for St in N.STRATEGIES)
    _save(fig, 'Fig7_shapley_levers', note='Shapley values within each combined game (Reference -> Moderate Pathway, '
                                           '-> Ambitious Pathway, -> TL); standalone effects in ED7. The TL dots are '
                                           'Shapley values within the TL game, so they include interactions at the limit '
                                           '(L5 with L4). Sum over levers (= Reference - Pathway / TL, exact): '
          + ', '.join(f'{k} {v:,.0f} kt' for k, v in tot.items()) + '; 512 subsets per game. Strategy-level Shapley '
          f'values (Moderate / Ambitious; 8 subsets): {strat}.')


# ---------------------------------------------------------------------------
# Fig8: uncertainty: (a) tornado of the Reference LoE AR; (b) TL against the 2050 population (Monte Carlo)
# ---------------------------------------------------------------------------
LOW_END, HIGH_END = S.LEVER['L8'], S.PATHWAY[N.PATHWAY]     # input at its low / high end (the colours of MODEL v3.0)


def _yrs(text):
    m = re.search(r'(\d{4})-(\d{4})', text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def tornado_rows():
    """MODEL v3.3.1: the rows of the Fig8a tornado on the cumulative LoE AR 2026-2050, each input at its low and high
    end as defined by its row (sensitivity/tornado.csv; the AR base window from sensitivity/planetary_boundary.csv):
    [(label, LoE at the input's low end, LoE at its high end, {label: LoE} of intermediate cases)]. The colour follows
    the input, not the outcome (the Stats NZ Low household-size variant, the input's low end, gives the higher LoE)."""
    t = D.csv('sensitivity/tornado.csv').set_index(['input', 'side'])
    pb = D.csv('sensitivity/planetary_boundary.csv')
    sc = D.js('baseline/scenarios.json')['meta']
    st = D.js('aesa/results.json')['settings']
    v = lambda inp, side: float(t.loc[(inp, side), 'LoE_AR'])
    rows = [('Population (Stats NZ 5th–95th percentile)',
             v('Population (Stats NZ 5th / 95th percentile)', 'low'),
             v('Population (Stats NZ 5th / 95th percentile)', 'high'), {}),
            ('Household size (Stats NZ low–high variant)',            # low variant: smaller households, more of them
             v('Household size (Stats NZ High / Low variant)', 'high'),
             v('Household size (Stats NZ High / Low variant)', 'low'), {}),
            (f"Replacement: Low ({sc['long_run_pct']:.2f}%) – Very High (trend)",
             v('Replacement (Low / High)', 'low'), v('Replacement: Very High (trend continues; one-sided)', 'high'),
             {'High': v('Replacement (Low / High)', 'high')}),
            ('Replacement half-life (5–15 yr)', v('Replacement half-life (5 / 15 yr)', 'low'),
             v('Replacement half-life (5 / 15 yr)', 'high'), {}),
            ('Completion rate (0.92–0.96)', v('Completion rate (0.92 / 0.96)', 'low'),
             v('Completion rate (0.92 / 0.96)', 'high'), {}),
            ('Carbon factors (case-study jackknife low–high)', v('Case-study carbon factors (jackknife)', 'low'),
             v('Case-study carbon factors (jackknife)', 'high'), {}),
            ('Soil order (lowest, Raw – highest, Organic)', v('Soil order (Raw / Organic)', 'low'),
             v('Soil order (Raw / Organic)', 'high'), {}),
            ('Overbuild absorption (by 2030 – by 2045)', v('Overbuild absorption (by 2030 / by 2045)', 'low'),
             v('Overbuild absorption (by 2030 / by 2045)', 'high'), {})]
    bw = pb[pb['group'] == 'Base window'].copy()
    if len(bw):
        bw['years'] = bw['row'].map(_yrs)
        bw['n'] = bw['years'].map(lambda y: y[1] - y[0] + 1)
        bw = bw.sort_values('n')
        c0 = st['AR_BASE_WINDOW']
        short, long_ = bw.iloc[0], bw.iloc[-1]
        rows.append((f"AR base window ({short['n']}–{long_['n']} yr; central {c0[0]}–{c0[1]})",
                     float(short['LoE_AR']), float(long_['LoE_AR']),
                     {f"{r['n']} yr": float(r['LoE_AR']) for _, r in bw.iloc[1:-1].iterrows()}))
    return rows, float(t['central_LoE_AR'].iloc[0])


def fig8():
    """MODEL v3.3.1: (a) tornado (Fig7 until v3.3.1) on the cumulative LoE AR: each input at its low end (blue) and high
    end (vermilion) as defined in its label, sorted by range, intermediate cases as ticks; (b) TL cumulative LoE AR
    against the 2050 population over the Monte Carlo draws (light points), the Firth logistic P(LoE AR <= 1) on the
    right axis, the 50% threshold with its bootstrap 95% CI."""
    rows, c0 = tornado_rows()
    rows = sorted(rows, key=lambda r: abs(r[2] - r[1]))
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 88), gridspec_kw={'width_ratios': [1.25, 1]})
    a = ax[0]
    for k, (lab, lo, hi, mid) in enumerate(rows):
        for val, col in ((lo, LOW_END), (hi, HIGH_END)):
            a.barh(k, val - c0, left=c0, height=0.62, **S.fill(col))
        for name, val in mid.items():
            a.plot([val, val], [k - 0.31, k + 0.31], color=S.INK, lw=S.LW_THIN)
            a.text(val, k + 0.33, name, ha='center', va='bottom', fontsize=S.FONT_MIN, color=S.INK)
    a.axvline(c0, color=S.INK, lw=S.LW_THIN)
    a.set_yticks(np.arange(len(rows)))
    a.set_yticklabels([r[0] for r in rows], fontsize=S.FONT_MIN + 0.5)
    a.set_xlabel('Reference cumulative LoE AR 2026-2050')
    a.grid(axis='y', visible=False)
    a.legend(handles=[Patch(label='Input at low end', **S.fill(LOW_END)),
                      Patch(label='Input at high end', **S.fill(HIGH_END))], loc='lower right', fontsize=S.FONT_MIN)
    P.panel(a, 'a', f'One at a time (Reference LoE AR {c0:.2f})')
    # (b) TL against the 2050 population
    j = D.js('pathways/montecarlo_conditional_tl.json')
    d = D.csv('pathways/montecarlo_draws.csv')
    thr = j['population_threshold']['adopted']
    b = ax[1]
    pop = d['P_NZ_2050'].to_numpy(float) / 1e6
    b.scatter(pop, d['TL_LoE_AR'], s=2, color=S.TL, alpha=0.25, lw=0, zorder=2, label='Draws (TL)')
    b.axhline(1.0, gid='boundary', zorder=3, **{k: v for k, v in S.BOUNDARY['AR'].items() if k != 'label'})
    b.set_xlabel('New Zealand population 2050 (million)')
    b.set_ylabel('TL cumulative LoE AR 2026-2050')
    b.set_ylim(bottom=0)
    b2 = b.twinx()
    b2.grid(False)
    b2.spines['right'].set_visible(True)
    if thr['estimable']:
        cv = thr['curve']
        b2.plot(np.asarray(cv['P_NZ_2050']) / 1e6, cv['probability'], color=S.INK, lw=S.LW_BOLD, zorder=4,
                label='P(LoE AR ≤ 1), Firth')
        lo, hi = thr['ci95']
        b.axvspan(lo / 1e6, hi / 1e6, color=S.INK, alpha=0.10, lw=0, zorder=1)
        x50 = thr['threshold_P_NZ_2050'] / 1e6
        b.axvline(x50, color=S.INK, lw=S.LW_THIN, ls='--', zorder=3)
        b2.text(x50, 0.52, f' {x50:.2f} M\n (95% CI {lo / 1e6:.2f}–{hi / 1e6:.2f})', ha='left', va='bottom',
                fontsize=S.FONT_MIN, color=S.INK)
    b2.set_ylim(-0.03, 1.03)
    b2.set_ylabel('P(TL cumulative LoE AR ≤ 1)')
    b.text(0.97, 0.90, f"TL within AR\nin {100 * j['p_within_AR']:.0f}% of draws", transform=b.transAxes, ha='right',
           va='top', fontsize=S.FONT_SMALL, color=S.TL)
    hb = b.get_legend_handles_labels()[0] + b2.get_legend_handles_labels()[0]
    hb.append(Line2D([0], [0], **dict(S.BOUNDARY['AR'], label='AR (LoE = 1)')))
    b.legend(handles=hb, loc='upper left', bbox_to_anchor=(0.0, 0.93), fontsize=S.FONT_MIN, markerscale=4,
             handlelength=1.0)
    P.panel(b, 'b', 'Theoretical Limit against the 2050 population')
    fig.tight_layout()
    _save(fig, 'Fig8_uncertainty',
          note=f"(a) Reference LoE AR {c0:.3f}; population rows move the budgets with the path; the AR base-window row "
               f"moves the AR budget only; one-at-a-time ranges are not additive. (b) P(TL within AR) = "
               f"{j['p_within_AR']:.3f} (Wilson {j['wilson_95'][0]:.3f}-{j['wilson_95'][1]:.3f}; n = {j['n']:,}); "
               + (f"threshold {thr['threshold_P_NZ_2050'] / 1e6:.3f} M (95% CI {thr['ci95'][0] / 1e6:.3f}-"
                  f"{thr['ci95'][1] / 1e6:.3f} M; {thr['method']}, {thr['bootstrap_resamples']} resamples)."
                  if thr['estimable'] else thr.get('note', 'no threshold')))


FIGURES = {'Fig1_model_schematic': fig1, 'Fig2_floor_area': fig2, 'Fig3_reference_carbon': fig3,
           'Fig4_reference_boundaries': fig4, 'Fig5_waterfall': fig5, 'Fig6_solution_space': fig6,
           'Fig7_shapley_levers': fig7, 'Fig8_uncertainty': fig8}
