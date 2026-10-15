"""The figures of the paper, Fig1-Fig8 (outputs/paper_main/; figure_plan.PAPER_MAIN), drawn from the data files only."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

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


def _save(fig, name, note=None):
    S.save_figure(fig, name, note=note, source=SRC[name])


def _band_frame(df, value):
    """year x band id (data label -> id), in the fixed band order."""
    t = df.pivot(index='year', columns='band', values=value)
    t.columns = [P.band_id(c) for c in t.columns]
    order = [b for b in BANDS_TL if b in t.columns]
    return t[order]


# ---------------------------------------------------------------------------
# Fig1: floor area, history (census intervals) and the Reference projection by demand band
# ---------------------------------------------------------------------------
def fig1():
    hist = D.csv('baseline/bands_history.csv')
    proj = _band_frame(D.csv('baseline/bands_annual.csv'), 'floor_area_Mm2')
    ann = D.csv('baseline/annual.csv')
    tot = ann[ann['source'] == 'projection'].set_index('year')['floor_area_Mm2']
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    # history: interval means as steps over each census interval (years y0+1 .. y1); the observed building of the
    # interval is the net (the unexplained building closes the identity and may be negative)
    ivs = hist[['interval', 'year_start', 'year_end']].drop_duplicates().sort_values('year_start')
    edges = list(ivs['year_start'] - 0.5) + [float(ivs['year_end'].iloc[-1]) + 0.5]
    hb = {}
    for _, iv in ivs.iterrows():
        h = hist[hist['interval'] == iv['interval']]
        for lab, v in zip(h['band'], h['floor_area_Mm2_per_year']):
            hb.setdefault(P.band_id(lab), []).append(float(v))
    observed = [float(hist[hist['interval'] == i]['observed_built_Mm2_per_year'].iloc[0]) for i in ivs['interval']]
    # MODEL v3.2.0 (from v3.1.0) (A3): the bands of the data add up to the observed floor area built (no derived remainder here)
    hist_parts = []
    for b, v in hb.items():
        x, y = P.steps(edges, v)
        hist_parts.append((b, y))
    xo, yo = P.steps(edges, observed)
    P.stack_series(ax, x, hist_parts, net=yo, net_line=False)
    ax.plot(xo, yo, color=S.INK, lw=S.LW, gid=P.NET_GID)
    # projection 2026-2050: annual stack, positives up, negatives down, the net a black line
    years = proj.index.values.astype(float)
    P.stack_series(ax, years, [(b, proj[b].values) for b in proj.columns if b != 'maintenance'],
                   net=tot.loc[proj.index].values, net_line=True)
    ax.plot(years, tot.loc[proj.index].values, color=S.INK, lw=S.LW, gid=P.NET_GID)
    P.split(ax)
    ax.set_xlim(edges[0], 2050.5)
    ax.set_ylabel('Floor area built (Mm² per year)')
    ax.text(0.01, 0.98, 'History: census-interval means', transform=ax.transAxes, va='top', fontsize=S.FONT_SMALL,
            color=S.MUTED)
    ax.text(0.62, 0.98, 'Reference projection, annual', transform=ax.transAxes, va='top', fontsize=S.FONT_SMALL,
            color=S.MUTED)
    neg = [b for b in proj.columns if (proj[b] < 0).any()]
    neg += [b for b in hb if b not in neg and any(v < 0 for v in hb[b])]
    present = [b for b in BANDS if b in proj.columns and (proj[b].abs() > 1e-12).any() and b != 'maintenance']
    hist_only = [b for b in hb if b not in present and any(abs(v) > 1e-12 for v in hb[b])]
    handles = P.band_handles(present + hist_only, outline=False)          # only the bands present (B3)
    handles += [Line2D([0], [0], color=S.INK, lw=S.LW, label='Net: floor area built')]
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.02), frameon=False,
               fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    _save(fig, 'Fig1_floor_area',
          note=f'Negative bands drawn down from zero: {", ".join(P.band_label(b) for b in neg)}; the net (black) is the '
               f'floor area built. 2026-2050: {tot.loc[proj.index].sum():.1f} Mm².')


# ---------------------------------------------------------------------------
# Fig2: Reference carbon by demand band, material and stage
# ---------------------------------------------------------------------------
def fig2():
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
        raise SystemExit('STOP: Fig2: the stages do not add up to the annual carbon.')
    P.panel(ax[2], 'c', 'By life-cycle stage')
    for a in ax:
        a.set_xlim(years[0], years[-1])
        P.thousands(a.yaxis)
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[2].legend(loc='upper right', fontsize=S.FONT_MIN)
    mh = [Patch(label=lab, **P.material_patch(code, c)) for code, lab, c in S.MATERIAL][::-1]
    ax[1].legend(handles=mh, loc='upper right', fontsize=S.FONT_MIN)
    P.band_legend(fig, [b for b in BANDS if b in band.columns], ncol=5, y=-0.01, outline=False,
                  extra=[Line2D([0], [0], color=S.INK, lw=S.LW, label='Net (annual carbon)')])
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    _save(fig, 'Fig2_reference_carbon', note=f'2026-2050: {total.sum():,.0f} kt CO₂e.')


# ---------------------------------------------------------------------------
# Fig3: the Reference against the boundaries (Monte Carlo), cumulative column with the committed range and shares
# ---------------------------------------------------------------------------
def fig3():
    mc = D.csv('montecarlo/annual_REF.csv').set_index('year')
    a = D.csv('aesa/annual.csv')
    a = a[(a['scenario'] == 'REF') & (a['year'] >= 2026)].set_index('year')
    proj = D.js('baseline/projection.json')
    band = _band_frame(D.csv('baseline/bands_annual.csv'), 'carbon_kt').sum()
    mat = D.csv('baseline/annual_by_material.csv').groupby('material')['carbon_kt'].sum()
    stg = D.csv('baseline/annual_by_stage.csv')[['a1a3_kt', 'a4a5_kt', 'soil_carbon_loss_kt', 'maintenance_kt']].sum()
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
    ax.legend(handles=ax.get_legend_handles_labels()[0] + S.zone_handles(), loc='upper right', fontsize=S.FONT_MIN)
    # (b) cumulative column 2026-2050, the committed range after 2050 hollow on top, the budgets as ticks, shares
    b = fig.add_subplot(gs[1])
    c = float(proj['carbon_kt'])
    com = proj['committed']
    lo, hi = c + com['lower_kt'], c + com['upper_kt']
    b.bar([0], [c], width=0.6, color=S.REFERENCE, edgecolor=S.REFERENCE, lw=S.LW_SEAM, label='2026-2050')
    b.bar([0], [hi - c], bottom=[c], width=0.6, facecolor='none', edgecolor=S.REFERENCE, lw=S.LW_THIN,
          label='Committed after 2050 (range)')
    b.plot([-0.3, 0.3], [lo, lo], color=S.REFERENCE, lw=S.LW_THIN, ls='--')
    bar_, batp = float(a['B_AR_kgCO2e'].sum()) / M, float(a['B_AtP_kgCO2e'].sum()) / M
    for v, key in ((bar_, 'AR'), (batp, 'AtP')):
        st = dict(S.BOUNDARY[key])
        lab = st.pop('label')
        b.plot([-0.45, 0.45], [v, v], gid='boundary', label=f'{lab} budget 2026-2050', **st)
    # three thin bars ending at the total: material and stage are shares of it (all positive); the band bar keeps the
    # bands at their size (A2: no rescaling): gross positive bands stacked, the releases hanging down as outlined
    # segments from the gross top to the total (draw.bars_cumulative)
    shares = [('Demand band', [(k, band[k]) for k in band.index if band[k] != 0], 'band'),
              ('Material', [(k, mat[k]) for k, _, _ in S.MATERIAL if k in mat.index], 'material'),
              ('Stage', [('a1a3', stg['a1a3_kt']), ('a4a5', stg['a4a5_kt']), ('soil', stg['soil_carbon_loss_kt']),
                         ('maintenance', stg['maintenance_kt'])], 'stage')]
    xs = [0.75, 1.05, 1.35]
    for xpos, (title, parts, kind) in zip(xs, shares):
        pos = sum(v for _, v in parts if v > 0)
        neg = [(k, v) for k, v in parts if v < 0]
        if kind != 'band' and neg:
            raise SystemExit(f'STOP: Fig3: negative {kind} value.')
        del title
        if kind == 'band':
            P.bars_cumulative(b, [xpos], parts, 0.18, net=c)
            continue
        bottom = 0.0
        for k, v in parts:
            if v <= 0:
                continue
            st = (P.band_style(k) if kind == 'band' else
                  P.material_patch(k, dict((code, col) for code, _, col in S.MATERIAL)[k]) if kind == 'material'
                  else S.fill(S.STAGE[k][0]))
            b.bar([xpos], [c * v / pos], bottom=[bottom], width=0.18, **st)
            bottom += c * v / pos
    b.set_xlim(-0.45, 1.5)
    b.set_xticks([0] + xs)
    b.set_xticklabels(['Reference', 'By\nband', 'by\nmaterial', 'by\nstage'], fontsize=S.FONT_MIN + 0.5)
    b.set_ylim(0, max(hi, bar_) * 1.42)
    b.set_ylabel('Cumulative carbon (kt CO₂e)')
    P.thousands(b.yaxis)
    b.legend(loc='upper left', fontsize=S.FONT_MIN, ncol=1)
    P.panel(b, 'b', 'Cumulative 2026-2050')
    _save(fig, 'Fig3_reference_boundaries',
          note=f'Cumulative 2026-2050 {c:,.0f} kt (LoE AR {c / bar_:.2f}, AtP {c / batp:.1f}); committed after 2050 '
               f'{com["lower_kt"]:,.0f}-{com["upper_kt"]:,.0f} kt. Bands with a negative value are not in the share '
               'bar (they reduce the positive stack).')


# ---------------------------------------------------------------------------
# Fig4: pathways annual against the boundaries
# ---------------------------------------------------------------------------
def fig4():
    a = D.csv('pathways/annual.csv')
    a = a[a['scenario'] == 'REF']
    ref = a[a['run'] == 'REF'].set_index('year')
    years = ref.index.values.astype(float)
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    S.boundary_zones(ax, years, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
    ax.plot(years, ref['carbon_kt'].values, color=S.REFERENCE, lw=S.LW_BOLD, label=N.SCENARIOS['REF'])
    for P_ in RUN_GROUPS:
        for s, st in (('moderate', dict(lw=S.LW_BOLD, ls='-')), ('ambitious', dict(lw=S.LW_THIN, ls=':'))):
            r = a[a['run'] == f'{P_}-{s}'].set_index('year')
            ax.plot(years, r['carbon_kt'].values, color=S.PATHWAY[P_], **st,
                    label=GROUP_LABEL[P_] if s == 'moderate' else None)
    t = a[a['run'] == 'TL'].set_index('year')
    ax.plot(years, t['carbon_kt'].values, color=S.TL, lw=S.LW_BOLD, label=N.TL['TL'])
    ax.set_xlim(years[0], years[-1])
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(ax.yaxis)
    h, l_ = ax.get_legend_handles_labels()
    h += [Line2D([0], [0], color=S.MUTED, lw=S.LW_BOLD, ls='-', label='Moderate'),
          Line2D([0], [0], color=S.MUTED, lw=S.LW_THIN, ls=':', label='Ambitious')] + S.zone_handles()
    fig.legend(handles=h, loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    r = D.csv('pathways/runs.csv')
    r = r[r['scenario'] == 'REF'].set_index('run')
    _save(fig, 'Fig4_pathways_annual',
          note='Cumulative LoE AR: ' + ', '.join(f"{k} {r.loc[k, 'LoE_AR']:.2f}" for k in
                                                 ('REF', 'pathway-moderate', 'pathway-ambitious', 'TL')) + '.')


# ---------------------------------------------------------------------------
# Fig5: waterfall by demand band (Moderate)
# ---------------------------------------------------------------------------
WATERFALL_NOTE = ('Steps in PAS 2080 hierarchy order; each step is credited with what remains after higher-priority '
                  'measures. Order-free Shapley values in Fig8. Outlined segments: reduction in credits from re-used '
                  'dwellings (vacancy released, overbuild absorbed, re-occupation, unconsented additions), valued at '
                  'the new-dwelling size they displace.')


def _step_strategy(step_id):
    """The PAS 2080 strategy of a waterfall step (Ln, or TLn = Level 4 of Ln)."""
    return N.LEVER_STRATEGY[N.TL_LIMIT_OF.get(step_id, step_id)]


def _waterfall_panel(ax, name, steps, tab, tot, delta, bands, first, last, start_lab, end_lab, start_col, end_col):
    """One sequential waterfall from the end bar at step `first` (start_lab) through steps first+1 .. last to the end
    bar at step `last` (end_lab). Each step: a floating bar from the previous total to the new one, split by the change
    of each demand band: reductions filled downward from the previous total, any increase an outlined segment upward,
    so the bar ends at the new total (net tick; label = the change in kt)."""
    seq = [('end', first, start_lab, start_col)] + [('step', k, steps.loc[k, 'step_id'], None)
                                                     for k in range(first + 1, last + 1)]
    seq += [('end', last, end_lab, end_col)]
    x = np.arange(len(seq))
    width = 0.72
    for xi, (kind, k, lab, col) in zip(x, seq):
        if kind == 'end':
            ax.bar(xi, tot[k], width=width, gid='band_segment', **S.fill(col))
            ax.text(xi, tot[k] + 0.012 * tot.max(), f'{tot[k]:,.0f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
            continue
        d = delta.loc[k]
        prev = tot[k - 1]
        level = prev
        for b in bands:                                   # reductions: filled, downward from the previous total
            if d[b] < 0:
                ax.bar(xi, -d[b], bottom=level + d[b], width=width, gid='band_segment', **P.band_style(b))
                level += d[b]
        for b in bands:                                   # increases: outlined, upward
            if d[b] > 0:
                ax.bar(xi, d[b], bottom=level, width=width, gid=P.NEG_BAR_GID, **P.negative_bar_style(b))
                level += d[b]
        if not np.isclose(level, tot[k], rtol=1e-9, atol=1e-6):
            raise SystemExit(f'STOP: {name}: step {lab} does not end at its total.')
        ax.plot([xi - 0.36 * width, xi + 0.36 * width], [tot[k], tot[k]], color=S.INK, lw=S.LW_BOLD,
                solid_capstyle='butt', zorder=5, gid=P.NET_GID)
        ax.plot([xi - 1 + width / 2, xi - width / 2], [prev, prev], color=S.MUTED, lw=S.LW_THIN * 0.7, zorder=4)
        ax.text(xi, max(prev, level) + 0.012 * tot.max(), f'{tot[k] - prev:+,.0f}', ha='center', va='bottom',
                fontsize=S.FONT_MIN)
    labels, colours = [], []
    for kind, k, lab, _ in seq:
        if kind == 'end':
            labels.append(lab)
            colours.append(S.INK)
        else:
            labels.append(f'+{lab} {N.TL[lab] if lab in N.TL else N.LEVERS[lab]}')
            colours.append(S.STRATEGY[_step_strategy(lab)])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha='right', fontsize=S.FONT_MIN)
    for t, c in zip(ax.get_xticklabels(), colours):          # each step labelled in its strategy's colour
        t.set_color(c)
    # strategy brackets under the steps (PAS 2080: S1 Avoid, S2 Switch, S3 Improve)
    for St in N.STRATEGIES:
        xs = [xi for xi, (kind, k, lab, _) in zip(x, seq) if kind == 'step' and _step_strategy(lab) == St]
        if xs:
            ax.plot([min(xs) - 0.4, max(xs) + 0.4], [-0.025, -0.025], transform=ax.get_xaxis_transform(),
                    color=S.STRATEGY[St], lw=S.LW_BOLD * 1.6, solid_capstyle='butt', clip_on=False)
    ax.set_xlim(-0.6, len(x) - 0.4)


def waterfall(name, setting):
    """MODEL v3.3.0 (from the v3.2 true sequential waterfall): two panels, lever-level steps in PAS 2080 hierarchy order
    (L1 .. L9: S1 Avoid, S2 Switch, S3 Improve), split by demand band: (a) Reference -> +L1 ... +L9 -> the Moderate /
    Ambitious Pathway; (b) that Pathway -> +TL1 ... +TL9 -> Theoretical Limit. The order-free attribution is the
    Shapley values of Fig8; pathways/sequential_vs_shapley.csv compares the two."""
    w = D.csv('pathways/waterfall.csv')
    w = w[w['setting'] == setting]
    steps = w[['step', 'step_id', 'label']].drop_duplicates().sort_values('step').reset_index(drop=True)
    tab = w.pivot(index='step', columns='band', values='carbon_kt')
    tab.columns = [P.band_id(c) for c in tab.columns]
    tot = w.groupby('step')['total_carbon_kt'].first().values
    delta = tab.diff().iloc[1:]
    bands = [b for b in BANDS_TL if b in tab.columns]
    i_pw = int(steps.index[steps['step_id'] == list(N.LEVERS)[-1]][0])      # the last lever step = the Pathway
    pw_lab = N.PATHWAY_RUNS[f'{N.PATHWAY}-{setting}']
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 110), sharey=True,
                           gridspec_kw=dict(width_ratios=(i_pw + 2, len(steps) - i_pw + 1)))
    bar_, batp = float(w['B_AR_kt'].iloc[0]), float(w['B_AtP_kt'].iloc[0])
    for a in ax:
        S.boundary_hzones(a, bar_, batp)
    _waterfall_panel(ax[0], name, steps, tab, tot, delta, bands, 0, i_pw, N.SCENARIOS['REF'], pw_lab,
                     S.REFERENCE, S.PATHWAY[N.PATHWAY])
    _waterfall_panel(ax[1], name, steps, tab, tot, delta, bands, i_pw, len(steps) - 1, pw_lab, N.TL['TL'],
                     S.PATHWAY[N.PATHWAY], S.TL)
    P.panel(ax[0], 'a', f'{N.SCENARIOS["REF"]} -> {pw_lab}')
    P.panel(ax[1], 'b', f'{pw_lab} -> {N.TL["TL"]}')
    ax[0].set_ylim(0, max(tot.max(), bar_) * 1.08)
    ax[0].set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax[0].yaxis)
    shown = [b for b in bands if (delta[b].abs() > 1e-9).any()]
    extra = [Patch(label='Increase (outline)', facecolor='none', edgecolor=S.MUTED, lw=S.LW_OUTLINE),
             Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label='New total after the step')]
    extra += [Line2D([0], [0], color=S.STRATEGY[St], lw=S.LW_BOLD * 1.6, label=f'{St} {N.STRATEGIES[St]} (PAS 2080)')
              for St in N.STRATEGIES]
    P.band_legend(fig, shown, ncol=4, y=-0.01, outline=False, extra=extra + S.boundary_handles() + S.zone_handles())
    fig.tight_layout(rect=(0, 0.2, 1, 1))
    S.save_figure(fig, name, note=f'{N.SETTINGS[setting]}: Reference {tot[0]:,.0f} kt -> {pw_lab} {tot[i_pw]:,.0f} kt '
                                  f'-> TL {tot[-1]:,.0f} kt; budgets AR {bar_:,.0f} kt, AtP {batp:,.0f} kt. '
                                  + WATERFALL_NOTE, source=['pathways/waterfall.csv'])


def fig5():
    waterfall('Fig5_waterfall', 'moderate')


# ---------------------------------------------------------------------------
# Fig6: the solution space against AR and AtP
# ---------------------------------------------------------------------------
FIG6_GRID = np.linspace(0.0, 1.0, 201)
FIG6_Y_STEP = 0.10            # the y-axis is extended to the smallest multiple of 10% above the AtP curve at x = 0


def fig6_loe(bc, x, y):
    """LoE_AR of the analytic plane (MODEL v3.2.0, B2): [C_2026 + C_ref,2027-2050 (1 - x)(1 - y)] / B_AR, C_2026 = the
    2026 cohort's emissions in the window (identical in every run), C_ref,2027-2050 = every emission in the window of the
    Reference's 2027-2050 cohorts (A1-A5, soil carbon loss, in-window B2/B4); x = cut in 2027-2050 floor area, y = cut
    in total carbon per m2 (y > 1: net-negative carbon per m2)."""
    r = bc['REF']
    return (r['carbon_fixed_2026_cohort_kt'] + r['carbon_2027_2050_cohorts_kt'] * (1.0 - x) * (1.0 - y)) / bc['B_AR_kt']


def fig6_curve(bc, x, level):
    """MODEL v3.3.0: the exact iso-line LoE_AR(x, y) = level of the analytic plane, y(x) = 1 - k / (1 - x), k =
    (level B_AR - C_2026) / C_ref,2027-2050 (x < 1). level = 1: the AR line; level = B_AtP / B_AR: the AtP line."""
    r = bc['REF']
    k = (level * bc['B_AR_kt'] - r['carbon_fixed_2026_cohort_kt']) / r['carbon_2027_2050_cohorts_kt']
    return 1.0 - k / (1.0 - np.asarray(x, float))


def fig6():
    """MODEL v3.3.0 (from v3.2): one panel. x = cut in 2027-2050 floor area (<= 100%), y = cut in 2027-2050 total carbon
    per m2 (A1-A5, soil and maintenance of the new cohorts), both vs the Reference; the y-axis extended to the smallest
    multiple of 10% that shows the AtP curve; above y = 100% (light sparse hatch) carbon per m2 is net negative
    (carbon-storing construction). Analytic LoE_AR contours (labelled in LoE AR), the exact AR (solid red) and AtP
    (dark-red dotted) curves with the zones; markers: S1-S3 (Moderate filled, Ambitious hollow), the Moderate /
    Ambitious Pathway and Theoretical Limit at their effective coordinates (the analytic LoE at each marker equals the
    run's LoE AR: tests)."""
    from figures import audit as figaudit
    bc = D.js('pathways/backcast.json')
    r = bc['REF']
    atp_level = bc['B_AtP_kt'] / bc['B_AR_kt']                    # LoE_AtP = 1  <=>  LoE_AR = B_AtP / B_AR
    y_atp0 = float(fig6_curve(bc, 0.0, atp_level))
    ytop = max(1.0, np.ceil(round(y_atp0 / FIG6_Y_STEP, 9)) * FIG6_Y_STEP)
    if ytop <= y_atp0:
        ytop += FIG6_Y_STEP
    X, Y = np.meshgrid(FIG6_GRID, np.linspace(0.0, ytop, int(round(ytop * 200)) + 1))
    Z = fig6_loe(bc, X, Y)
    fig, ax = plt.subplots(figsize=S.figsize('double', 115))
    S.boundary_field(ax, 100 * X, 100 * Y, Z, 1.0, atp_level, lines=False)
    xs = np.linspace(0.0, 0.999, 2000)
    for key, level in (('AR', 1.0), ('AtP', atp_level)):           # the budget curves, exact
        yc = fig6_curve(bc, xs, level)
        ok = (yc >= 0.0) & (yc <= ytop)
        if ok.any():
            st = {k: v for k, v in S.BOUNDARY[key].items() if k != 'label'}
            ln, = ax.plot(100 * xs[ok], 100 * yc[ok], zorder=3, **st)
            ln.set_gid(figaudit.BOUNDARY)
    if ytop > 1.0:                                                 # net-negative carbon per m2
        ax.fill_between([0, 100], 100, 100 * ytop, facecolor='none', edgecolor=S.MUTED, hatch='/', lw=0,
                        alpha=0.35, zorder=1)
        ax.axhline(100, color=S.MUTED, lw=S.LW_THIN * 0.7, zorder=2)
        ax.text(2, 100 * (1.0 + ytop) / 2, 'net-negative carbon per m² (carbon-storing construction)', ha='left',
                va='center', fontsize=S.FONT_MIN + 0.5, color=S.INK, zorder=4)
    zmin, zmax = float(Z.min()), float(Z.max())
    levels = [v for v in (1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8) if zmin < v < zmax]
    cs = ax.contour(100 * X, 100 * Y, Z, levels=levels, colors=S.MUTED, linewidths=S.LW_THIN * 0.7)
    ax.clabel(cs, fmt=lambda v: f'LoE AR {v:g}', fontsize=S.FONT_MIN)
    for m in bc['solution_space_markers']:
        run = m['run']
        xm, ym = 100 * m['demand_reduction'], 100 * m['intensity_reduction']
        if run == 'TL':
            ax.plot(xm, ym, color=S.TL, ls='none', **S.TL_MARKER, zorder=6, clip_on=False)
            continue
        P_, st = run.split('-')
        ax.plot(xm, ym, marker='o', ms=5 if P_ != N.PATHWAY else 6.5, ls='none', color=S.PATHWAY[P_],
                markerfacecolor=S.PATHWAY[P_] if st == 'moderate' else 'none', markeredgewidth=1.0, zorder=5,
                clip_on=False)
    c26 = r['carbon_fixed_2026_cohort_kt']
    ax.text(2, 93, f'2026 (observed) alone emits {c26:,.0f} kt = {c26 / bc["B_AtP_kt"]:.2f} × the 2026–2050 AtP '
            'budget', ha='left', va='top', fontsize=S.FONT_MIN + 0.5, color=S.BOUNDARY['AtP']['color'], zorder=4)
    ax.set_xlabel('Cut in 2027-2050 floor area vs the Reference (%)')
    ax.set_ylabel('Cut in 2027-2050 carbon per m² (A1-A5, soil, B2/B4) vs the Reference (%)')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100 * ytop)
    ax.grid(False)
    h = [Line2D([0], [0], marker='o', ls='none', color=S.PATHWAY[P_], markerfacecolor=S.PATHWAY[P_], ms=5,
                label=GROUP_LABEL[P_] if P_ != N.PATHWAY else 'Moderate / Ambitious Pathway') for P_ in RUN_GROUPS]
    h += [Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor=S.MUTED, ms=5, label='Moderate'),
          Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor='none', ms=5, label='Ambitious'),
          Line2D([0], [0], ls='none', color=S.TL, label=N.TL['TL'], **S.TL_MARKER),
          Patch(facecolor='white', edgecolor=S.MUTED, hatch='//', lw=0.5, label='Net-negative carbon per m²')]
    h += S.boundary_handles() + S.zone_handles()
    fig.legend(handles=h, loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.02), frameon=False,
               fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    floor = c26 / bc['B_AR_kt']
    note = (f"LoE AR = [{c26:,.0f} + {r['carbon_2027_2050_cohorts_kt']:,.0f} (1 - x)(1 - y)] / {bc['B_AR_kt']:,.0f} kt; "
            f"C_2026 = the 2026 cohort's emissions in the window. Lowest LoE AR at x or y = 100%: {floor:.2f}. AtP "
            f"curve y = 1 - k / (1 - x), above y = 100% for every x (y = {100 * y_atp0:.1f}% at x = 0): the AtP budget "
            f"needs net-negative carbon per m² of 2027-2050 construction; y-axis to {100 * ytop:.0f}%.")
    _save(fig, 'Fig6_solution_space', note=note)


# ---------------------------------------------------------------------------
# Fig7: tornado of the Reference (carbon; LoE AR and AtP)
# ---------------------------------------------------------------------------
def fig7():
    t = D.csv('sensitivity/tornado.csv')
    wide = t.pivot(index='input', columns='side', values=['carbon_kt', 'LoE_AR', 'LoE_AtP'])
    c0, a0, p0 = (float(t[k].iloc[0]) for k in ('central_carbon_kt', 'central_LoE_AR', 'central_LoE_AtP'))
    rng = (wide[('carbon_kt', 'high')] - wide[('carbon_kt', 'low')]).abs().sort_values()
    order = list(rng.index)
    y = np.arange(len(order))
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 80), gridspec_kw={'width_ratios': [1.1, 1.3]})
    for k, inp in enumerate(order):
        lo, hi = wide.loc[inp, ('carbon_kt', 'low')], wide.loc[inp, ('carbon_kt', 'high')]
        for v, col in ((lo, S.LEVER['L8']), (hi, S.PATHWAY[N.PATHWAY])):
            ax[0].barh(k, v - c0, left=c0, height=0.6, color=col, edgecolor=col, lw=S.LW_SEAM)
    ax[0].axvline(c0, color=S.INK, lw=S.LW_THIN)
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(order, fontsize=S.FONT_MIN + 0.5)
    ax[0].set_xlabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax[0].xaxis)
    P.panel(ax[0], 'a', 'Cumulative carbon')
    b = ax[1]
    for key, central, off in (('LoE_AR', a0, 0.17), ('LoE_AtP', p0, -0.17)):
        colr = S.AR if key == 'LoE_AR' else S.ATP
        for k, inp in enumerate(order):
            lo, hi = wide.loc[inp, (key, 'low')], wide.loc[inp, (key, 'high')]
            b.plot([min(lo, hi), max(lo, hi)], [k + off, k + off], color=colr, lw=3.0, solid_capstyle='butt')
        b.axvline(central, color=colr, lw=S.LW_THIN, ls='--')
    b.axvline(1.0, color=S.INK, lw=S.LW_THIN)
    b.text(1.02, len(order) - 0.6, 'LoE = 1', fontsize=S.FONT_MIN, color=S.INK)
    b.set_xscale('log')
    P.log_ticks(b.xaxis, [1, 2, 3, 5, 10, 20, 30])
    b.set_yticks(y)
    b.set_yticklabels([])
    b.set_xlabel('Cumulative level of exceedance 2026-2050 (log scale)')
    b.legend(handles=[Line2D([0], [0], color=S.AR, lw=3, label='LoE of acquired rights (AR)'),
                      Line2D([0], [0], color=S.ATP, lw=3, label='LoE of ability to pay (AtP)')],
             loc='lower right', fontsize=S.FONT_MIN)
    P.panel(b, 'b', 'Levels of exceedance')
    ax[0].legend(handles=[Patch(color=S.LEVER['L8'], label='low case'), Patch(color=S.PATHWAY[N.PATHWAY], label='high case')],
                 loc='lower right', fontsize=S.FONT_MIN)
    fig.tight_layout()
    _save(fig, 'Fig7_tornado', note=f'Reference {c0:,.0f} kt (LoE AR {a0:.2f}, AtP {p0:.1f}); population rows move the '
                                    'budgets with the path; one-at-a-time ranges are not additive.')


# ---------------------------------------------------------------------------
# Fig8: Shapley value of each lever (Moderate hollow, Ambitious filled, TL dot)
# ---------------------------------------------------------------------------
def fig8():
    """MODEL v3.3.0: rows grouped by PAS 2080 strategy (S1 Avoid, S2 Switch, S3 Improve) in the lever order, each bar
    in its strategy's colour; Moderate hollow, Ambitious filled, TL dot (games from the Reference)."""
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
    _save(fig, 'Fig8_shapley_levers', note='Shapley values within each combined game (Reference -> Moderate Pathway, '
                                           '-> Ambitious Pathway, -> TL); standalone effects in ED10. Sum over levers '
                                           '(= Reference - Pathway / TL, exact): '
          + ', '.join(f'{k} {v:,.0f} kt' for k, v in tot.items()) + '; 512 subsets per game. Strategy-level Shapley '
          f'values (Moderate / Ambitious; 8 subsets): {strat}.')


FIGURES = {'Fig1_floor_area': fig1, 'Fig2_reference_carbon': fig2, 'Fig3_reference_boundaries': fig3,
           'Fig4_pathways_annual': fig4, 'Fig5_waterfall': fig5, 'Fig6_solution_space': fig6, 'Fig7_tornado': fig7,
           'Fig8_shapley_levers': fig8}
