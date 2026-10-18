"""The figures of the paper, Fig1-Fig8 (outputs/paper_main/; figure_plan.PAPER_MAIN), drawn from the data files only.

MODEL v3.3.1 order (Nature Cities, at most eight display items): Fig1 model schematic, Fig2 floor area by demand band,
Fig3 Reference carbon, Fig4 Reference against the boundaries, Fig5 three sequential waterfalls, Fig6 solution space,
Fig7 Shapley value of each lever, Fig8 uncertainty (tornado; TL against the 2050 population)."""
import calendar
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
SRC = {h['file']: h['source'] for h in FP.PAPER_MAIN + FP.SUPPLEMENTARY}
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
# SF1 (Fig1 in MODEL v3.3.1): model schematic (boxes and arrows; no data drawn)
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


def sf1_schematic():
    """MODEL v3.3.1 (SF1 since v3.3.2): the model as boxes and arrows. Top row: the conversion chain to embodied carbon, compared with the
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
    _save(fig, 'SF1_model_schematic',
          note=f"Adoption: {ad['form']}, from {ad['start']} (w = 0) to {ad['end']} (w = 1). Lever names from "
               'naming.LEVERS; strategy colours style.STRATEGY.')


# ---------------------------------------------------------------------------
# Fig1: floor area, history (census intervals) and the Reference projection by demand band
# ---------------------------------------------------------------------------
FIG1_GAP = 0.05                 # MODEL v3.3.2: the gap between columns, as a share of the interval width (v3.3.1: 0.10)


OBSERVED_FILL = '#BDBDBD'       # MODEL v4.0.0: observed totals without a band split (the grey of D14)
PIPELINE_HATCH = '////'         # MODEL v4.0.0: building above modelled need in the pipeline years


def _month(iso):
    """'2026-07-01' -> 'July 2026' (None -> 'the last observed month')."""
    if not iso:
        return 'the last observed month'
    y, m = int(str(iso)[:4]), int(str(iso)[5:7])
    return f'{calendar.month_name[m]} {y}'


def _stack_bar(ax, a, b, parts, net, styles=None):
    """One stacked column over [a, b] (positive bands up from zero, negative down), with its net line."""
    x = np.array([a, b], float)
    up = dn = 0.0
    for bid, v in parts:
        st = (styles or {}).get(bid, P.band_style(bid))
        if v > 0:
            ax.fill_between(x, up, up + v, gid='band_area', **st)
            up += v
        elif v < 0:
            ax.fill_between(x, dn + v, dn, gid=P.NEG_GID, **st)
            dn += v
    if not np.isclose(up + dn, net, rtol=1e-9, atol=1e-12):
        raise SystemExit(f'Fig1: the pipeline bands ({up + dn}) differ from the total ({net}).')
    ax.plot(x, [net, net], color=S.INK, lw=S.LW, gid=P.NET_GID)


def fig1():
    """MODEL v4.0.0 (layout of v3.3.2): census-interval columns of the history to 2023 (FIG1_GAP between columns);
    2024-2025 observed completions (consents lagged) as total columns without a band split (household estimates
    between censuses are not independent of the consents); the pipeline years (2026-2027 at a 17-month lag) as
    annual columns split into the need bands plus the building above modelled need (hatched); the projection annual
    from the first unobserved year (2028), each year drawn over its own width."""
    hist = D.csv('baseline/bands_history.csv')
    proj = _band_frame(D.csv('baseline/bands_annual.csv'), 'floor_area_Mm2')
    ann = D.csv('baseline/annual.csv')
    ob = D.js('baseline/overbuild_2026.json')
    pipe = [int(y) for y in (ob.get('pipeline_years') or [2026])]
    tot = ann[ann['source'] == 'projection'].set_index('year')['floor_area_Mm2']
    hist_tot = ann[ann['source'] == 'history'].set_index('year')['floor_area_Mm2']
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    census = hist.groupby('interval')['households_from'].agg(lambda c: set(c) == {'census'})
    ivs = (hist[hist['interval'].map(census)][['interval', 'year_start', 'year_end']].drop_duplicates()
           .sort_values('year_start').reset_index(drop=True))
    edges = list(ivs['year_start'] - 0.5) + [float(ivs['year_end'].iloc[-1]) + 0.5]
    hb = {}
    for k, iv in ivs.iterrows():
        h = hist[hist['interval'] == iv['interval']]
        a, b = edges[k], edges[k + 1]
        w = b - a
        a, b = a + FIG1_GAP / 2 * w, b - FIG1_GAP / 2 * w        # half the gap on each side of every column
        parts = [(P.band_id(lab), np.array([v, v], float)) for lab, v in zip(h['band'], h['floor_area_Mm2_per_year'])]
        for bid, v in parts:
            hb.setdefault(bid, []).append(float(v[0]))
        obs = float(h['observed_built_Mm2_per_year'].iloc[0])
        # MODEL v3.2.0 (A3): the bands of the data add up to the observed floor area built
        P.stack_series(ax, [a, b], parts, net=[obs, obs], net_line=False)
        ax.plot([a, b], [obs, obs], color=S.INK, lw=S.LW, gid=P.NET_GID)
    y_hist_end = int(ivs['year_end'].iloc[-1])
    g = FIG1_GAP / 2
    obs_years = [y for y in hist_tot.index if y_hist_end < y < min(pipe)]
    for y in obs_years:                                           # observed totals, no band split
        ax.fill_between([y - 0.5 + g, y + 0.5 - g], 0, float(hist_tot.loc[y]), gid='observed_total',
                        **S.fill(OBSERVED_FILL))
        ax.plot([y - 0.5 + g, y + 0.5 - g], [hist_tot.loc[y]] * 2, color=S.INK, lw=S.LW, gid=P.NET_GID)
    hatched = dict(S.fill(S.BAND['overbuild_2026'][0], hatch=PIPELINE_HATCH, hatchcolor=S.HATCH_LIGHT))
    cols = [b for b in proj.columns if b != 'maintenance']
    for y in pipe:                                                # pipeline years: need bands + building above need
        _stack_bar(ax, y - 0.5 + g, y + 0.5 - g, [(bid, float(proj.loc[y, bid])) for bid in cols],
                   float(tot.loc[y]), styles={'overbuild_2026': hatched})
    fut = proj.loc[proj.index > max(pipe)]
    years = fut.index.values.astype(float)
    x0 = years[0] - 0.5 + g                                       # the same gap before the annual projection
    xs = np.concatenate([[x0], years, [years[-1] + 0.5]])
    ext = lambda v: np.concatenate([[v[0]], v, [v[-1]]])
    net = tot.loc[fut.index].values
    P.stack_series(ax, xs, [(b, ext(fut[b].values)) for b in cols], net=ext(net), net_line=False)
    ax.plot(xs, ext(net), color=S.INK, lw=S.LW, gid=P.NET_GID)
    P.split(ax)
    ax.set_xlim(edges[0] + FIG1_GAP / 2 * (edges[1] - edges[0]), xs[-1])
    lo_, hi_ = ax.get_ylim()
    ax.set_ylim(lo_, hi_ + 0.10 * (hi_ - lo_))                         # room for the labels
    ax.set_ylabel('Floor area built (Mm² per year)')
    ax.text(y_hist_end + 0.4, 0.98, 'History (census-interval means)', transform=ax.get_xaxis_transform(),
            ha='right', va='top', fontsize=S.FONT_SMALL, color=S.MUTED)
    lab_y = 0.98                                                  # narrow groups: vertical labels
    if obs_years:
        ax.text(np.mean(obs_years), lab_y, 'Observed', transform=ax.get_xaxis_transform(), ha='center', va='top',
                rotation=90, fontsize=S.FONT_MIN, color=S.MUTED)
    ax.text(np.mean(pipe), lab_y, 'Pipeline', transform=ax.get_xaxis_transform(), ha='center', va='top',
            rotation=90, fontsize=S.FONT_MIN, color=S.MUTED)
    ax.text(x0 + 0.4, 0.98, 'Projection (annual)', transform=ax.get_xaxis_transform(),
            ha='left', va='top', fontsize=S.FONT_SMALL, color=S.MUTED)
    neg = [b for b in proj.columns if (proj[b] < 0).any()]
    neg += [b for b in hb if b not in neg and any(v < 0 for v in hb[b])]
    present = [b for b in BANDS if b in proj.columns and (proj[b].abs() > 1e-12).any() and b != 'maintenance']
    if not (fut.get('overbuild_2026', 0) != 0).any() and 'overbuild_2026' in present:
        present.remove('overbuild_2026')                          # only the pipeline part is drawn
    hist_only = [b for b in hb if b not in present and any(abs(v) > 1e-12 for v in hb[b])]
    handles = paper_band_handles(present + hist_only)                    # only the bands present
    handles += [Patch(label='Building above modelled need (pipeline)', **dict(hatched, edgecolor='#555555',
                                                                              linewidth=S.LW_THIN))]
    if obs_years:
        handles += [Patch(label='Observed (consent-based; household estimates not independent)',
                          **dict(S.fill(OBSERVED_FILL), edgecolor='#555555', linewidth=S.LW_THIN))]
    handles += [Line2D([0], [0], color=S.INK, lw=S.LW, label='Floor area built (in scope)')]
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.02), frameon=False,
               fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.19, 1, 1))
    lag, rate = ob.get('completion_lag_months'), ob.get('completion_rate')
    _save(fig, 'Fig1_floor_area',
          note=(f"Completions = {rate:.3f} x consents lagged {lag} months (median consent-to-completion time 1.27-1.53 "
                f"yr, Jones, Greenaway-McGrevy & Crow 2025; consistent with the Stats NZ Experimental building "
                f"indicators). " if lag else '')
               + f"Pipeline years {', '.join(map(str, pipe))}: building observed (consents to "
               f"{_month(ob.get('consents_observed_to'))}); the part above modelled need fades from "
               f"{max(pipe) + 1} (ρ = {ob['rho']:.2f}) and is absorbed by {ob['absorption_end']}. 2026 population: "
               f"Stats NZ ERP nowcast. Negative bands drawn down from zero: "
               f"{', '.join(P.band_label(b) for b in neg)}. 2026-2050: {tot.loc[2026:2050].sum():.1f} Mm².")


# ---------------------------------------------------------------------------
# Fig2: Reference carbon by demand band, material and stage (annual) and cumulative (three attached columns)
# ---------------------------------------------------------------------------
def fig2():
    """MODEL v3.3.2 (Fig3 of v3.3.1): (a-c) annual by demand band, material and stage (shared axis; the demand legend
    inside panel a, two columns); (d) cumulative 2026-2050 as three attached columns of the same total (by demand band:
    positive bands stacked, negative bands outlined hanging down to the total, draw.bars_cumulative; by material; by
    stage), its own axis in kt, thin separators."""
    band = _band_frame(D.csv('baseline/bands_annual.csv'), 'carbon_kt')
    mat = D.csv('baseline/annual_by_material.csv').pivot(index='year', columns='material', values='carbon_kt')
    stg = D.csv('baseline/annual_by_stage.csv').set_index('year')
    years = band.index.values.astype(float)
    total = stg['carbon_kt'].values
    fig = plt.figure(figsize=S.figsize('double', 82))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 0.62], wspace=0.12)
    ax = [fig.add_subplot(gs[0])]
    ax += [fig.add_subplot(gs[k], sharey=ax[0]) for k in (1, 2)]
    P.stack_series(ax[0], years, [(b, band[b].values) for b in band.columns], net=total)
    P.panel(ax[0], 'a', 'By demand band')
    P.stack_materials(ax[1], years, mat, 1.0)
    P.panel(ax[1], 'b', 'By material')
    stages = [('a1a3', stg['a1a3_kt']), ('a4a5', stg['a4a5_kt']), ('soil', stg['soil_carbon_loss_kt']),
              ('maintenance', stg['maintenance_kt'])]
    P.nonnegative('stage', *[v.values for _, v in stages])
    bottom = np.zeros(len(years))
    for k, v in stages:
        ax[2].fill_between(years, bottom, bottom + v.values, label=N.STAGES[k], **S.fill(*S.STAGE[k][:1]))
        bottom = bottom + v.values
    if not np.allclose(bottom, total, rtol=1e-9):
        raise SystemExit('STOP: Fig2: the stages do not add up to the annual carbon.')
    P.panel(ax[2], 'c', 'By life-cycle stage')
    for a in ax:
        a.set_xlim(years[0], years[-1])
        P.thousands(a.yaxis)
    for a in ax[1:]:
        plt.setp(a.get_yticklabels(), visible=False)
    lo_, hi_ = ax[0].get_ylim()
    ticks = [t for t in ax[0].get_yticks() if lo_ <= t <= hi_]
    ax[0].set_ylim(lo_, hi_ * 1.55)                                   # room above the data for the legends
    ax[0].set_yticks(ticks)                                           # ticks only over the data range
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[2].legend(loc='upper right', fontsize=S.FONT_MIN)
    mh = [Patch(label=lab, **P.material_patch(code, c)) for code, lab, c in S.MATERIAL][::-1]
    ax[1].legend(handles=mh, loc='upper right', fontsize=S.FONT_MIN, ncol=2, columnspacing=0.8)
    shown = [b for b in BANDS if b in band.columns and (band[b].abs() > 1e-12).any()]      # only the bands present
    ax[0].legend(handles=paper_band_handles(shown) + [Line2D([0], [0], color=S.INK, lw=S.LW, label='Carbon (in scope)')],
                 loc='upper right', ncol=2, fontsize=S.FONT_MIN, handlelength=1.2, columnspacing=0.8,
                 labelspacing=0.3)
    # (d) cumulative 2026-2050: three attached columns of the same total
    d = fig.add_subplot(gs[3])
    c = float(total.sum())
    bsum = band.sum()
    msum = mat.sum()
    P.bars_cumulative(d, [0.0], [(b, bsum[b]) for b in band.columns if abs(bsum[b]) > 1e-12], 1.0, net=c)
    bot = 0.0
    for code, _, colour in S.MATERIAL:                                  # the material order of panel b
        if code in msum.index:
            d.bar([1.0], [msum[code]], bottom=[bot], width=1.0, **P.material_patch(code, colour))
            bot += float(msum[code])
    if not np.isclose(bot, c, rtol=1e-9):
        raise SystemExit('STOP: Fig2d: the materials do not add up to the cumulative carbon.')
    bot = 0.0
    for k, v in stages:
        d.bar([2.0], [float(v.sum())], bottom=[bot], width=1.0, **S.fill(S.STAGE[k][0]))
        bot += float(v.sum())
    if not np.isclose(bot, c, rtol=1e-9):
        raise SystemExit('STOP: Fig2d: the stages do not add up to the cumulative carbon.')
    for x in (0.5, 1.5):                                                # thin separators between the columns
        d.axvline(x, color='white', lw=0.8, zorder=6)
    d.axhline(c, color=S.INK, lw=S.LW_THIN, ls=':', zorder=6)
    d.set_xlim(-0.5, 2.5)
    d.set_xticks([0, 1, 2])
    d.set_xticklabels(['By\ndemand', 'By\nmaterial', 'By\nstage'], fontsize=S.FONT_MIN + 0.5)
    d.yaxis.tick_right()
    d.yaxis.set_label_position('right')
    d.spines['right'].set_visible(True)
    d.spines['left'].set_visible(False)
    d.set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(d.yaxis)
    d.grid(axis='x', visible=False)
    P.panel(d, 'd', 'Cumulative')
    fig.subplots_adjust(left=0.07, right=0.93, bottom=0.12, top=0.92)
    _save(fig, 'Fig2_reference_carbon', note=f'2026-2050: {c:,.0f} kt CO₂e; (d) the demand column: positive bands '
                                              f'stacked to {sum(v for v in bsum if v > 0):,.0f} kt, negative bands '
                                              'outlined, hanging down to the total.')


# ---------------------------------------------------------------------------
# Fig3: the Reference against the boundaries (Monte Carlo); cumulative column and the committed emissions
# ---------------------------------------------------------------------------
FIG3_INTERVAL = (2.5, 97.5)        # MODEL v3.3.2: the 95% interval of the cumulative carbon (percentiles of the draws)


def mc_cumulative_interval():
    """The Monte Carlo 95% interval (FIG3_INTERVAL percentiles) of the Reference cumulative carbon 2026-2050, from the
    per-draw totals (montecarlo/draws_REF.csv) with the percentile method of MonteCarlo.py (numpy.percentile, linear)."""
    d = D.csv('montecarlo/draws_REF.csv')['carbon_kt'].to_numpy(float)
    return tuple(float(v) for v in np.percentile(d, FIG3_INTERVAL))


def fig3():
    """MODEL v3.3.2 (Fig4 of v3.3.1): (a) unchanged; (b) the cumulative 2026-2050 column with its Monte Carlo 95%
    interval (whisker) and the AR / AtP budgets; the committed column: C1-C4 and B2/B4 after 2050 at the lower bound
    (2050 factors held) stacked, its range to the upper bound (2025 factors) a whisker; no numbers; a legend inside."""
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
    lo95, hi95 = mc_cumulative_interval()
    com = proj['committed']
    wd = 0.55
    whisk = dict(color=S.INK, lw=S.LW, capsize=3.0, capthick=S.LW, zorder=6)
    b.bar([0], [c], width=wd, **S.fill(S.REFERENCE))
    b.errorbar([0], [c], yerr=[[c - lo95], [hi95 - c]], fmt='none', **whisk)
    bar_, batp = float(a['B_AR_kgCO2e'].sum()) / M, float(a['B_AtP_kgCO2e'].sum()) / M
    for v, key in ((bar_, 'AR'), (batp, 'AtP')):
        st = {k: val for k, val in S.BOUNDARY[key].items() if k != 'label'}
        b.plot([-0.42, 0.42], [v, v], gid='boundary', **st)
        b.text(-0.44, v, f'{key} budget', ha='right', va='center', fontsize=S.FONT_MIN, color=st['color'])
    cc, bl, bu = float(com['C_kt']), float(com['B_lower_kt']), float(com['B_upper_kt'])
    b.bar([1], [cc], width=wd, **S.fill(S.COMPONENT['committed'][0]))
    b.bar([1], [bl], bottom=[cc], width=wd, **S.fill(S.COMPONENT['maintenance'][0]))
    top = cc + bl
    b.errorbar([1], [top], yerr=[[0.0], [bu - bl]], fmt='none', **dict(whisk, color=S.COMPONENT['maintenance'][0]))
    b.set_xlim(-1.3, 1.6)
    b.set_xticks([0, 1])
    b.set_xticklabels(['2026–2050', 'Committed\nafter 2050'], fontsize=S.FONT_MIN + 0.5)
    b.set_ylim(0, max(hi95, bar_, cc + bu) * 1.32)
    b.set_ylabel('Cumulative carbon (kt CO₂e)')
    P.thousands(b.yaxis)
    b.grid(axis='x', visible=False)
    hb = [Line2D([0], [0], color=S.REFERENCE, lw=5, label='Cumulative carbon 2026–2050 (95% interval)'),
          Line2D([0], [0], color=S.COMPONENT['maintenance'][0], lw=5, label='Committed after 2050: B2/B4 (range)'),
          Patch(label='Committed after 2050: C1–C4', **S.fill(S.COMPONENT['committed'][0]))]
    hb[0].set_marker('|')
    hb[0].set_markersize(9)
    hb[0].set_markeredgecolor(S.INK)
    hb[1].set_marker('|')
    hb[1].set_markersize(9)
    b.legend(handles=hb, loc='upper right', fontsize=S.FONT_MIN, handlelength=1.6)
    P.panel(b, 'b', 'Cumulative')
    _save(fig, 'Fig3_reference_boundaries',
          note=f'Cumulative 2026-2050 {c:,.0f} kt (LoE AR {c / bar_:.2f}, AtP {c / batp:.1f}); Monte Carlo 95% interval '
               f'{lo95:,.0f}-{hi95:,.0f} kt ({FIG3_INTERVAL[0]:g}th-{FIG3_INTERVAL[1]:g}th percentile of the cumulative '
               f'carbon of the draws); committed after 2050 {com["lower_kt"]:,.0f}-{com["upper_kt"]:,.0f} kt: C1-C4 '
               f'{cc:,.0f} kt (2025 factors) and B2/B4 after 2050 {bl:,.0f} kt (2050 factors held) to {bu:,.0f} kt '
               '(2025 factors).')


# ---------------------------------------------------------------------------
# Fig4: the Pathways: (a) annual carbon; (b-d) three sequential waterfalls from the Reference
# ---------------------------------------------------------------------------
def _step_strategy(step_id):
    """The PAS 2080 strategy of a waterfall step (Ln, or TLn = Level 4 of Ln)."""
    return N.LEVER_STRATEGY[N.TL_LIMIT_OF.get(step_id, step_id)]


def waterfall_paths():
    """MODEL v3.3.1 (Fig4 b-d): the three sequential paths from the Reference, [(panel key, end label, end colour,
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


def fig4():
    """MODEL v3.3.2: (a) full-width annual carbon 2026-2050: the Reference (black), the Moderate and Ambitious Pathway
    (bold; Moderate solid, Ambitious dotted), the Theoretical Limit (deep green, bold) and S1-S3 (thin, strategy
    colours; Moderate solid, Ambitious dotted) against AR / AtP and the zones, legend inside; (b-d) the three net
    waterfalls of MODEL v3.3.1 (Fig5): from the Reference in PAS 2080 lever order to the Moderate Pathway, the
    Ambitious Pathway and (TL1 ... TL9 cumulative) the Theoretical Limit."""
    an = D.csv('pathways/annual.csv')
    an = an[an['scenario'] == 'REF']
    ref = an[an['run'] == 'REF'].set_index('year')
    years = ref.index.values.astype(float)
    paths, bar_, batp = waterfall_paths()
    fig = plt.figure(figsize=S.figsize('double', 175))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.15], hspace=0.32, wspace=0.08)
    a = fig.add_subplot(gs[0, :])
    S.boundary_zones(a, years, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
    run = lambda r: an[an['run'] == r].set_index('year')['carbon_kt'].values
    for St in N.STRATEGIES:                                              # strategies first (thin, beneath)
        for s, ls in (('moderate', '-'), ('ambitious', ':')):
            a.plot(years, run(f'{St}-{s}'), color=S.STRATEGY[St], lw=S.LW_THIN * 1.4, ls=ls, zorder=4,
                   label=f'{St} {N.STRATEGIES[St]}' if s == 'moderate' else None)
    a.plot(years, ref['carbon_kt'].values, color=S.INK, lw=S.LW_BOLD, zorder=5, label=N.SCENARIOS['REF'])
    for s, ls in (('moderate', '-'), ('ambitious', ':')):
        a.plot(years, run(f'{N.PATHWAY}-{s}'), color=S.PATHWAY[N.PATHWAY], lw=S.LW_BOLD * 1.2, ls=ls, zorder=5,
               label=N.PATHWAY_RUNS[f'{N.PATHWAY}-{s}'])
    a.plot(years, run('TL'), color=S.TL, lw=S.LW_BOLD * 1.2, zorder=5, label=N.TL['TL'])
    a.set_xlim(years[0], years[-1])
    a.set_ylim(0, None)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(a.yaxis)
    h = a.get_legend_handles_labels()[0]
    h += [Line2D([0], [0], color=S.MUTED, lw=S.LW_THIN * 1.4, ls='-', label='Strategy at Moderate'),
          Line2D([0], [0], color=S.MUTED, lw=S.LW_THIN * 1.4, ls=':', label='Strategy at Ambitious')]
    h += S.zone_handles()
    a.legend(handles=h, loc='upper right', ncol=3, fontsize=S.FONT_MIN, handlelength=2.0, columnspacing=1.0)
    P.panel(a, 'a', 'Annual carbon against AR and AtP')
    ax = [fig.add_subplot(gs[1, 0])]
    ax += [fig.add_subplot(gs[1, k], sharey=ax[0]) for k in (1, 2)]
    ups = {}
    for b, (key, lab, col, steps), letter in zip(ax, paths, 'bcd'):
        S.boundary_hzones(b, bar_, batp)
        ups[key] = _net_waterfall_panel(b, steps, lab, col)
        P.panel(b, letter, f'{N.SCENARIOS["REF"]} → {lab}')
    for b in ax[1:]:
        plt.setp(b.get_yticklabels(), visible=False)
    ax[0].set_ylim(0, max(paths[0][3][0][1], bar_) * 1.1)
    ax[0].set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax[0].yaxis)
    hs = [Patch(label=f'{St} {N.STRATEGIES[St]}', **S.fill(S.STRATEGY[St])) for St in N.STRATEGIES]
    ax[2].legend(handles=hs, loc='upper right', fontsize=S.FONT_MIN, title='Waterfall steps', title_fontsize=S.FONT_MIN)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.97, bottom=0.08)
    up_txt = '; '.join(f'{k}: ' + ', '.join(f'{s} {d:+,.1f} kt' for s, d in v) for k, v in ups.items() if v)
    r = D.csv('pathways/runs.csv')
    r = r[r['scenario'] == 'REF'].set_index('run')
    _save(fig, 'Fig4_pathways',
          note='(a) Cumulative LoE AR: ' + ', '.join(f"{k} {r.loc[k, 'LoE_AR']:.2f}" for k in
                                                     ('REF', 'pathway-moderate', 'pathway-ambitious', 'TL'))
               + '. (b-d) Reference ' + f'{paths[0][3][0][1]:,.0f} kt -> '
               + ', '.join(f'{lab} {steps[-1][1]:,.0f} kt' for _, lab, _, steps in paths)
               + f'; budgets AR {bar_:,.0f} kt, AtP {batp:,.0f} kt. Steps in PAS 2080 order; each step is credited with '
               'what remains after the higher-priority measures; order-free Shapley values in Fig7. Net-positive steps: '
               + (up_txt if up_txt else 'none') + '.')


# ---------------------------------------------------------------------------
# Fig5: the reduction against the Reference by demand band (Moderate Pathway, Ambitious Pathway, TL)
# ---------------------------------------------------------------------------
FIG5_RUNS = ('pathway-moderate', 'pathway-ambitious', 'TL')


def reduction_by_band():
    """MODEL v3.3.2 (Fig5): {run: {band id: Reference - run (kt, cumulative 2026-2050, in scope)}} for FIG5_RUNS, from
    pathways/bands.csv (the in-scope bands add up to each run's carbon, pathways.py), and the column totals
    {run: Reference - run} from pathways/runs.csv."""
    bd = D.csv('pathways/bands.csv')
    bd = bd[(bd['scenario'] == 'REF') & (bd['definition'] == 'in_scope')]
    piv = bd.pivot(index='band', columns='run', values='carbon_kt')
    piv.index = [P.band_id(b) for b in piv.index]
    r = D.csv('pathways/runs.csv')
    r = r[r['scenario'] == 'REF'].set_index('run')['carbon_kt']
    order = [b for b in BANDS_TL if b in piv.index]
    red = {run: {b: float(piv.loc[b, 'REF'] - piv.loc[b, run]) for b in order} for run in FIG5_RUNS}
    tot = {run: float(r['REF'] - r[run]) for run in FIG5_RUNS}
    return red, tot


def fig5():
    """MODEL v3.3.2: three columns (Moderate Pathway, Ambitious Pathway, Theoretical Limit), height = the total
    reduction of cumulative carbon 2026-2050 against the Reference (value on top), stacked by demand band (Reference -
    run per band): positive band reductions stacked from zero, negative band reductions (credits from re-used dwellings
    that shrink with smaller new dwellings) outlined, hanging down from the top of the positive stack to the total
    (draw.bars_cumulative, net tick)."""
    red, tot = reduction_by_band()
    fig, ax = plt.subplots(figsize=S.figsize('double', 105))
    x = np.arange(len(FIG5_RUNS), dtype=float)
    bands = [b for b in red[FIG5_RUNS[0]] if any(abs(red[r][b]) > 1e-9 for r in FIG5_RUNS)]
    parts = [(b, np.array([red[r][b] for r in FIG5_RUNS])) for b in bands]
    up, dn, end = P.bars_cumulative(ax, x, parts, 0.56, net=np.array([tot[r] for r in FIG5_RUNS]))
    for xi, r, u in zip(x, FIG5_RUNS, up):
        ax.text(xi, u + 0.012 * max(up), f'{tot[r]:,.0f}', ha='center', va='bottom', fontsize=S.FONT_SMALL,
                fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([N.PATHWAY_RUNS.get(r, N.TL['TL']) for r in FIG5_RUNS])
    ax.set_xlim(-0.6, len(x) - 0.4 + 1.25)                               # room on the right for the legend
    ax.set_ylim(0, max(up) * 1.08)
    ax.set_ylabel('Reduction of cumulative carbon 2026-2050 vs the Reference (kt CO₂e)')
    P.thousands(ax.yaxis)
    ax.grid(axis='x', visible=False)
    negb = {b for b, v in parts if (v < -1e-9).any()}
    hb = []
    for b in bands[::-1]:                                                # top of the stack first
        lab = PAPER_BAND_LABEL.get(b, P.band_label(b))
        if b in negb and not any(red[r][b] > 1e-9 for r in FIG5_RUNS):
            hb.append(Patch(label=f'{lab} (credit shrinks)', **P.negative_bar_style(b)))
        else:
            hb.append(Patch(label=lab, **dict(P.band_style(b), edgecolor='#555555', linewidth=S.LW_THIN)))
    hb.append(Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label='Total reduction'))
    ax.legend(handles=hb, loc='center right', fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout()
    _save(fig, 'Fig5_reduction_by_demand',
          note='Reduction vs the Reference (kt): ' + ', '.join(f'{N.run_label(r)} {tot[r]:,.0f}' for r in FIG5_RUNS)
               + '. Negative band reductions (outlined): ' + '; '.join(
                   f"{P.band_label(b)} " + ', '.join(f'{red[r][b]:+,.0f}' for r in FIG5_RUNS) for b in bands if b in negb)
               + ' kt (Moderate, Ambitious, TL): the credits from re-used dwellings shrink when new dwellings are '
               'smaller, because each re-used dwelling is valued at the new-dwelling size it displaces.')


# ---------------------------------------------------------------------------
# Fig6: the solution space against AR and AtP
# ---------------------------------------------------------------------------
FIG6_LIM = (-0.05, 1.0)        # MODEL v3.3.2: both axes from -5% to 100% (v3.3.1: to 110%)
FIG6_N = 421                   # grid points per axis (0.25% steps)


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


def _spread(vals, min_gap):
    """Label positions (log10 units) for sorted values, pushed apart to at least min_gap, centred on the values."""
    pos = list(vals)
    for _ in range(200):
        moved = False
        for i in range(1, len(pos)):
            if pos[i] - pos[i - 1] < min_gap:
                d = (min_gap - (pos[i] - pos[i - 1])) / 2
                pos[i - 1] -= d
                pos[i] += d
                moved = True
        if not moved:
            break
    return pos


def fig6():
    """MODEL v3.3.2: x = cut in 2027-2050 floor area, y = cut in 2027-2050 total carbon per m2 (A1-A5, soil and
    maintenance of the new cohorts), both vs the Reference, from -5% to 100%; the zones from the analytic LoE_AR field;
    analytic LoE_AR contours and the exact AR line; markers: S1-S3 (Moderate filled, Ambitious hollow), the Moderate /
    Ambitious Pathway and TL at their effective coordinates (the analytic LoE at each marker equals the run's LoE AR:
    tests). Right: a slim LoE AR ruler (log) with the zones, AR = 1, AtP = B_AtP / B_AR, the plane floor C_2026 / B_AR
    (the 2026 observed cohort alone: the lowest LoE AR on the plane) and the runs. The AtP contour lies above 100% (C_2026
    > B_AtP) and is not drawn on the plane."""
    from figures import audit as figaudit
    bc = D.js('pathways/backcast.json')
    r = bc['REF']
    runs = D.csv('pathways/runs.csv')
    runs = runs[runs['scenario'] == 'REF'].set_index('run')['LoE_AR']
    lo, hi = FIG6_LIM
    atp_level = bc['B_AtP_kt'] / bc['B_AR_kt']                    # LoE_AtP = 1  <=>  LoE_AR = B_AtP / B_AR
    c26 = r['carbon_fixed_2026_cohort_kt']
    floor = c26 / bc['B_AR_kt']
    g = np.linspace(lo, hi, FIG6_N)
    X, Y = np.meshgrid(g, g)
    Z = fig6_loe(bc, X, Y)
    fig = plt.figure(figsize=S.figsize('double', 118))
    ax = fig.add_axes([0.08, 0.12, 0.52, 0.82])
    S.boundary_field(ax, 100 * X, 100 * Y, Z, 1.0, atp_level, lines=False)
    st = {k: v for k, v in S.BOUNDARY['AR'].items() if k != 'label'}
    for xb, yb in fig6_branches(bc, 1.0):                          # the AR line, exact
        ln, = ax.plot(100 * xb, 100 * yb, zorder=3, **st)
        ln.set_gid(figaudit.BOUNDARY)
    ax.axhline(0, color=S.INK, lw=S.LW_THIN * 0.7, zorder=2)
    ax.axvline(0, color=S.INK, lw=S.LW_THIN * 0.7, zorder=2)
    zmin, zmax = float(Z.min()), float(Z.max())
    levels = [v for v in (1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8) if zmin < v < zmax]
    cs = ax.contour(100 * X, 100 * Y, Z, levels=levels, colors=S.MUTED, linewidths=S.LW_THIN * 0.7)
    # labels where each contour crosses the diagonal x = y: (1 - x)^2 = k
    diag = {v: 1.0 - np.sqrt(fig6_k(bc, v)) for v in levels if fig6_k(bc, v) > 0}
    lab_levels = [v for v, d in diag.items() if 0.02 <= d <= 0.98]      # crossings inside the square only
    ax.clabel(cs, levels=lab_levels, fmt=lambda v: f'LoE AR {v:g}', fontsize=S.FONT_MIN,
              manual=[(100 * diag[v], 100 * diag[v]) for v in lab_levels])
    for m in bc['solution_space_markers']:
        run = m['run']
        xm, ym = 100 * m['demand_reduction'], 100 * m['intensity_reduction']
        if run == 'TL':
            ax.plot(xm, ym, color=S.TL, ls='none', **S.TL_MARKER, zorder=6)
            continue
        P_, s_ = run.split('-')
        ax.plot(xm, ym, marker='o', ms=5 if P_ != N.PATHWAY else 6.5, ls='none', color=S.PATHWAY[P_],
                markerfacecolor=S.PATHWAY[P_] if s_ == 'moderate' else 'none', markeredgewidth=1.0, zorder=5)
    ax.text(2, 97, f'2026 (observed) alone emits {c26:,.0f} kt = {c26 / bc["B_AtP_kt"]:.2f} × the 2026–2050 AtP '
            'budget', ha='left', va='top', fontsize=S.FONT_MIN + 0.5, color=S.BOUNDARY['AtP']['color'], zorder=4)
    ax.set_xlabel('Cut in 2027-2050 floor area vs the Reference (%)')
    ax.set_ylabel('Cut in 2027-2050 carbon per m² (A1-A5, soil, B2/B4) vs the Reference (%)')
    ax.set_xlim(100 * lo, 100 * hi)
    ax.set_ylim(100 * lo, 100 * hi)
    ax.grid(False)
    # the LoE AR ruler (log): zones, AR and AtP, the plane floor and the runs
    ru = fig.add_axes([0.625, 0.12, 0.018, 0.82])
    marks = [(N.SCENARIOS['REF'], float(runs['REF']), dict(color=S.REFERENCE, marker='s', ms=4)),
             (N.PATHWAY_RUNS['pathway-moderate'], float(runs['pathway-moderate']),
              dict(color=S.PATHWAY[N.PATHWAY], marker='o', ms=5)),
             (N.PATHWAY_RUNS['pathway-ambitious'], float(runs['pathway-ambitious']),
              dict(color=S.PATHWAY[N.PATHWAY], marker='o', ms=5, markerfacecolor='white')),
             (N.TL['TL'], float(runs['TL']), dict(color=S.TL, marker='o', ms=6)),
             ('AR = 1', 1.0, None), ('Plane floor (2026 observed)', floor, None),
             (f'AtP ({atp_level:.2f})', atp_level, None)]
    vmin, vmax = 0.8 * min(v for _, v, _ in marks), 1.25 * max(v for _, v, _ in marks)
    ru.set_yscale('log')
    ru.set_ylim(vmin, vmax)
    S.boundary_hzones(ru, 1.0, atp_level)
    ru.axhline(floor, color=S.INK, lw=S.LW_THIN, ls='--', zorder=4)
    for lab, v, mk in marks:
        if mk:
            ru.plot([0.5], [v], ls='none', zorder=6, clip_on=False, **mk)
    ru.set_xlim(0, 1)
    ru.set_xticks([])
    ru.yaxis.set_major_locator(plt.NullLocator())
    ru.yaxis.set_minor_locator(plt.NullLocator())
    for sp in ('top', 'right', 'bottom'):
        ru.spines[sp].set_visible(True)
    order = sorted(marks, key=lambda m: m[1])
    lv = np.log10([m[1] for m in order])
    span = np.log10(vmax) - np.log10(vmin)
    pos = _spread(lv, 0.055 * span)
    for (lab, v, mk), yl, yv in zip(order, pos, lv):
        txt = f'{lab}  {v:.2f}' if mk else f'{lab}' + ('' if lab.startswith('AtP') or lab.startswith('AR') else
                                                       f'  {v:.2f}')
        ru.annotate(txt, xy=(1.0, 10 ** yv), xytext=(1.6, 10 ** yl), textcoords=('axes fraction', 'data'),
                    xycoords=('axes fraction', 'data'), ha='left', va='center', fontsize=S.FONT_MIN + 0.5,
                    color=mk['color'] if mk else S.INK,
                    arrowprops=dict(arrowstyle='-', color=S.MUTED, lw=0.4, shrinkA=0, shrinkB=0))
    ru.set_title('LoE AR', fontsize=S.FONT_MIN + 0.5, pad=3)
    h = [Line2D([0], [0], marker='o', ls='none', color=S.PATHWAY[P_], markerfacecolor=S.PATHWAY[P_], ms=5,
                label=GROUP_LABEL[P_] if P_ != N.PATHWAY else 'Moderate / Ambitious Pathway') for P_ in RUN_GROUPS]
    h += [Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor=S.MUTED, ms=5, label='Moderate'),
          Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor='none', ms=5, label='Ambitious'),
          Line2D([0], [0], ls='none', color=S.TL, label=N.TL['TL'], **S.TL_MARKER),
          Line2D([0], [0], ls='none', color=S.REFERENCE, marker='s', ms=4, label=f"{N.SCENARIOS['REF']} (ruler)"),
          Line2D([0], [0], color=S.INK, lw=S.LW_THIN, ls='--', label='Plane floor (ruler)')]
    h += S.boundary_handles() + S.zone_handles()
    fig.legend(handles=h, loc='center left', bbox_to_anchor=(0.80, 0.5), frameon=False, fontsize=S.FONT_MIN + 0.5)
    note = (f"LoE AR = [{c26:,.0f} + {r['carbon_2027_2050_cohorts_kt']:,.0f} (1 - x)(1 - y)] / {bc['B_AR_kt']:,.0f} kt; "
            f"C_2026 = the 2026 cohort's emissions in the window; plane floor C_2026 / B_AR = {floor:.3f} (the lowest "
            f"LoE AR at x or y = 100%); AtP = B_AtP / B_AR = {atp_level:.3f} lies below the floor, so the AtP contour is "
            f"outside the plotted square (y = {100 * float(fig6_curve(bc, 0.0, atp_level)):.1f}% at x = 0). Axes "
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
SINGLE_CASE = S.MUTED                                         # MODEL v4.0.0: a row with one alternative case


def _yrs(text):
    m = re.search(r'(\d{4})-(\d{4})', text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def tornado_rows():
    """MODEL v3.3.1: the rows of the Fig8a tornado on the cumulative LoE AR 2026-2050, each input at its low and high
    end as defined by its row (sensitivity/tornado.csv; the AR base window from sensitivity/planetary_boundary.csv):
    [(label, LoE at the input's low end, LoE at its high end, {label: LoE} of intermediate cases[, LoE of a single
    alternative case])]. The colour follows the input, not the outcome (the Stats NZ Low household-size variant, the
    input's low end, gives the higher LoE). MODEL v4.0.0: rows with one alternative case and no low / high end (the
    household-size census pace, No 2026 data) carry it as a fifth element and are drawn in the muted grey."""
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
            ('Completion rate (0.93–0.96)', v('Completion rate (0.93 / 0.96)', 'low'),
             v('Completion rate (0.93 / 0.96)', 'high'), {}),
            ('Completion lag (15–19 months; central 17)', v('Completion lag (15 / 19 months)', 'low'),
             v('Completion lag (15 / 19 months)', 'high'),
             {'0 mo': v('Completion lag 0 months (one-sided)', 'high')}),
            ('Household size: 2018–2023 census pace (linear)', None, None, {},
             v('Household size: 2018-2023 census pace (one-sided)', 'high')),
            ('No 2026 data (consents to Dec 2025)', None, None, {}, v('No 2026 data (one-sided)', 'high')),
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
    against the 2050 population over the Monte Carlo draws (light points), LoE = 1 and the population at which the
    Firth logistic P(LoE AR <= 1) = 50% (line, labelled with its bootstrap 95% CI; MODEL v3.3.2: no secondary axis, no
    curve)."""
    rows, c0 = tornado_rows()
    rows = [r if len(r) == 5 else r + (None,) for r in rows]
    span = lambda r: abs(r[4] - c0) if r[4] is not None else abs(r[2] - r[1])
    rows = sorted(rows, key=span)
    has_single = any(r[4] is not None for r in rows)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 96), gridspec_kw={'width_ratios': [1.25, 1]})
    a = ax[0]
    for k, (lab, lo, hi, mid, one) in enumerate(rows):
        bars = ((one, SINGLE_CASE),) if one is not None else ((lo, LOW_END), (hi, HIGH_END))
        for val, col in bars:
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
                      Patch(label='Input at high end', **S.fill(HIGH_END))]
             + ([Patch(label='Single alternative case', **S.fill(SINGLE_CASE))] if has_single else []),
             loc='lower right', fontsize=S.FONT_MIN)
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
    if thr['estimable']:
        lo, hi = thr['ci95']
        x50 = thr['threshold_P_NZ_2050'] / 1e6
        b.axvline(x50, color=S.INK, lw=S.LW_THIN, ls='--', zorder=3, label='P(LoE AR ≤ 1) = 50%')
        b.text(x50, 0.04, f' {x50:.2f} M (95% CI {lo / 1e6:.2f}–{hi / 1e6:.2f} M)', transform=b.get_xaxis_transform(),
               ha='left', va='bottom', fontsize=S.FONT_MIN, color=S.INK)
    b.text(0.03, 0.97, f"TL within AR in {100 * j['p_within_AR']:.0f}% of draws", transform=b.transAxes, ha='left',
           va='top', fontsize=S.FONT_SMALL, color=S.TL)
    hb = b.get_legend_handles_labels()[0]
    hb.append(Line2D([0], [0], **dict(S.BOUNDARY['AR'], label='AR (LoE = 1)')))
    b.legend(handles=hb, loc='upper left', bbox_to_anchor=(0.0, 0.90), fontsize=S.FONT_MIN, markerscale=4)
    P.panel(b, 'b', 'Theoretical Limit against the 2050 population')
    fig.tight_layout()
    _save(fig, 'Fig8_uncertainty',
          note=f"(a) Reference LoE AR {c0:.3f}; population rows move the budgets with the path; the AR base-window row "
               f"moves the AR budget only; one-at-a-time ranges are not additive. (b) P(TL within AR) = "
               f"{j['p_within_AR']:.3f} (Wilson {j['wilson_95'][0]:.3f}-{j['wilson_95'][1]:.3f}; n = {j['n']:,}); "
               + (f"threshold {thr['threshold_P_NZ_2050'] / 1e6:.3f} M (95% CI {thr['ci95'][0] / 1e6:.3f}-"
                  f"{thr['ci95'][1] / 1e6:.3f} M; {thr['method']}, {thr['bootstrap_resamples']} resamples)."
                  if thr['estimable'] else thr.get('note', 'no threshold')))


FIGURES = {'Fig1_floor_area': fig1, 'Fig2_reference_carbon': fig2, 'Fig3_reference_boundaries': fig3,
           'Fig4_pathways': fig4, 'Fig5_reduction_by_demand': fig5, 'Fig6_solution_space': fig6,
           'Fig7_shapley_levers': fig7, 'Fig8_uncertainty': fig8, 'SF1_model_schematic': sf1_schematic}
