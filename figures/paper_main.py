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
PATHWAY_LABEL = {'REF': N.SCENARIOS['REF'], **{P_: f'{P_} {N.PATHWAYS[P_]}' for P_ in N.PATHWAYS}, 'TL': N.TL['TL']}


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
    hb['unexplained_building'] = [o - sum(hb[b][k] for b in hb if b != 'unexplained_building')
                                  for k, o in enumerate(observed)]
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
    handles = P.band_handles([b for b in BANDS if b != 'maintenance'], outline=False)
    handles += [Patch(label=N.BAND_DETAIL['replacement_history'], **P.band_style('replacement_history')),
                Patch(label=N.UNEXPLAINED, **P.band_style('unexplained_building')),
                Line2D([0], [0], color=S.INK, lw=S.LW, label='Net: floor area built')]
    fig.legend(handles=handles, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.02), frameon=False,
               fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    _save(fig, 'Fig1_floor_area',
          note=f'Negative bands drawn down from zero: {", ".join(N.BANDS[b] for b in neg)}; the net (black) is the '
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
    order = [b for b in band.columns if b == 'legacy'] + [b for b in band.columns if b != 'legacy']   # legacy: the base
    P.stack_series(ax[0], years, [(b, band[b].values) for b in order], net=total)
    P.panel(ax[0], 'a', 'By demand band')
    P.stack_materials(ax[1], years, mat, 1.0)
    P.panel(ax[1], 'b', 'By material')
    parts = [('legacy', stg['legacy_soil_kt'] + stg['legacy_b2b4_kt']), ('a1a3', stg['a1a3_kt']), ('a4a5', stg['a4a5_kt']),
             ('soil', stg['soil_carbon_loss_kt']), ('maintenance', stg['maintenance_kt'])]
    P.nonnegative('stage', *[v.values for _, v in parts])
    bottom = np.zeros(len(years))
    for k, v in parts:
        ax[2].fill_between(years, bottom, bottom + v.values, label=N.STAGES.get(k, N.BANDS.get(k)),
                           **S.fill(*S.STAGE[k][:1]))
        bottom = bottom + v.values
    if not np.allclose(bottom, total, rtol=1e-9):
        raise SystemExit('STOP: Fig2: the stages do not add up to the annual carbon.')
    P.panel(ax[2], 'c', 'By life-cycle stage')
    for a in ax:
        a.set_xlim(years[0], years[-1])
        P.thousands(a.yaxis)
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[2].legend(loc='upper right', fontsize=S.FONT_MIN)
    mh = [Patch(label=lab, **P.material_patch(code, c)) for code, lab, c in S.MATERIAL if code in mat.columns][::-1]
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
    stg = D.csv('baseline/annual_by_stage.csv')[['a1a3_kt', 'a4a5_kt', 'soil_carbon_loss_kt', 'maintenance_kt',
                                                  'legacy_soil_kt', 'legacy_b2b4_kt']].sum()
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
    leg = float(stg['legacy_soil_kt'] + stg['legacy_b2b4_kt'])
    sa = float(proj.get('soil_after_2050_kt', 0.0))            # MODEL v3.1.0: soil oxidised after 2050, own segment
    lo, hi = c + sa + com['lower_kt'], c + sa + com['upper_kt']
    if leg > 0:
        b.bar([0], [leg], width=0.6, **S.fill(S.COMPONENT['legacy'][0]), label=N.BANDS['legacy'])
    b.bar([0], [c - leg], bottom=[leg], width=0.6, color=S.REFERENCE, edgecolor=S.REFERENCE, lw=S.LW_SEAM,
          label='2026-2050 (new construction)' if leg > 0 else '2026-2050')
    if sa > 0:
        b.bar([0], [sa], bottom=[c], width=0.6, facecolor='none', edgecolor=S.COMPONENT['soil_after'][0],
              lw=S.LW_OUTLINE, hatch=None, label=N.COMPONENTS['soil_after'])
    b.bar([0], [hi - c - sa], bottom=[c + sa], width=0.6, facecolor='none', edgecolor=S.REFERENCE, lw=S.LW_THIN,
          label='Committed after 2050, B2/B4 and C1-C4 (range)')
    b.plot([-0.3, 0.3], [lo, lo], color=S.REFERENCE, lw=S.LW_THIN, ls='--')
    bar_, batp = float(a['B_AR_kgCO2e'].sum()) / M, float(a['B_AtP_kgCO2e'].sum()) / M
    for v, key in ((bar_, 'AR'), (batp, 'AtP')):
        st = dict(S.BOUNDARY[key])
        lab = st.pop('label')
        b.plot([-0.45, 0.45], [v, v], gid='boundary', label=f'{lab} budget 2026-2050', **st)
    # three thin 100% share bars
    shares = [('Demand band', [(k, band[k]) for k in band.index if band[k] != 0], 'band'),
              ('Material', [(k, mat[k]) for k, _, _ in S.MATERIAL if k in mat.index], 'material'),
              ('Stage', [('legacy', stg['legacy_soil_kt'] + stg['legacy_b2b4_kt']), ('a1a3', stg['a1a3_kt']),
                         ('a4a5', stg['a4a5_kt']), ('soil', stg['soil_carbon_loss_kt']),
                         ('maintenance', stg['maintenance_kt'])], 'stage')]
    xs = [0.75, 1.05, 1.35]
    for xpos, (title, parts, kind) in zip(xs, shares):
        pos = sum(v for _, v in parts if v > 0)
        neg = [(k, v) for k, v in parts if v < 0]
        if kind != 'band' and neg:
            raise SystemExit(f'STOP: Fig3: negative {kind} value.')
        del title
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
    b.set_xticklabels(['Reference', 'Share by\nband', 'by\nmaterial', 'by\nstage'], fontsize=S.FONT_MIN + 0.5)
    b.set_ylim(0, max(hi, bar_) * 1.42)
    b.set_ylabel('Cumulative carbon (kt CO₂e)')
    P.thousands(b.yaxis)
    b.legend(loc='upper left', fontsize=S.FONT_MIN, ncol=1)
    P.panel(b, 'b', 'Cumulative 2026-2050')
    _save(fig, 'Fig3_reference_boundaries',
          note=f'Cumulative 2026-2050 {c:,.0f} kt (LoE AR {c / bar_:.2f}, AtP {c / batp:.1f}), of which legacy '
               f'(pre-2026 activity) {leg:,.0f} kt; committed after 2050: soil {sa:,.0f} kt, B2/B4 and C1-C4 '
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
    leg = (ref['legacy_soil_kt'] + ref['legacy_b2b4_kt']).values           # MODEL v3.1.0: identical in every run
    if np.any(leg > 0):
        ax.fill_between(years, 0, leg, **S.fill(S.COMPONENT['legacy'][0]), label=N.BANDS['legacy'], zorder=1.5)
    ax.plot(years, ref['carbon_kt'].values, color=S.REFERENCE, lw=S.LW_BOLD, label=N.SCENARIOS['REF'])
    for P_ in ('P1', 'P2', 'P3', 'P4', 'P5'):
        for s, st in (('moderate', dict(lw=S.LW_BOLD, ls='-')), ('ambitious', dict(lw=S.LW_THIN, ls=':'))):
            r = a[a['run'] == f'{P_}-{s}'].set_index('year')
            ax.plot(years, r['carbon_kt'].values, color=S.PATHWAY[P_], **st,
                    label=f'{P_} {N.PATHWAYS[P_]}' if s == 'moderate' else None)
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
                                                 ('REF', 'P5-moderate', 'P5-ambitious', 'TL')) + '.')


# ---------------------------------------------------------------------------
# Fig5: waterfall by demand band (Moderate)
# ---------------------------------------------------------------------------
def waterfall(name, setting):
    w = D.csv('pathways/waterfall.csv')
    w = w[w['setting'] == setting]
    steps = w[['step', 'step_id', 'label']].drop_duplicates().sort_values('step')
    tab = w.pivot(index='step', columns='band', values='carbon_kt')
    tab.columns = [P.band_id(c) for c in tab.columns]
    tab = tab[[b for b in BANDS_TL if b in tab.columns]]
    tot = w.groupby('step')['total_carbon_kt'].first()
    x = np.arange(len(steps))
    fig, ax = plt.subplots(figsize=S.figsize('double', 105))
    bar_, batp = float(w['B_AR_kt'].iloc[0]), float(w['B_AtP_kt'].iloc[0])
    S.boundary_hzones(ax, bar_, batp)
    up, _, _ = P.bars_cumulative(ax, x, [(b, tab[b].values) for b in tab.columns], width=0.72, net=tot.values)
    for xi, t, u in zip(x, tot.values, up):
        ax.text(xi, u + 0.012 * tot.max(), f'{t:,.0f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
    ax.set_xticks(x)
    ax.set_xticklabels([lab.replace(' (= ', '\n(= ') for lab in steps['label']], rotation=60, ha='right',
                       fontsize=S.FONT_MIN)
    ax.set_xlim(-0.6, len(x) - 0.4)
    ax.set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax.yaxis)
    P.band_legend(fig, list(tab.columns), ncol=4, y=-0.01,
                  extra=S.boundary_handles() + S.zone_handles())
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    S.save_figure(fig, name, note=f'{N.SETTINGS[setting]}: Reference {tot.iloc[0]:,.0f} kt -> P5 '
                                  f'{tot.iloc[4]:,.0f} kt -> TL {tot.iloc[-1]:,.0f} kt; budgets AR {bar_:,.0f} kt, '
                                  f'AtP {batp:,.0f} kt. Sequential steps depend on their order (the order-free values '
                                  'are the Shapley values).',
                  source=['pathways/waterfall.csv'])


def fig5():
    waterfall('Fig5_waterfall', 'moderate')


# ---------------------------------------------------------------------------
# Fig6: the solution space against AR and AtP
# ---------------------------------------------------------------------------
def fig6():
    sp = D.csv('pathways/solution_space.csv')
    bc = D.js('pathways/backcast.json')
    d = np.sort(sp['demand_reduction'].unique())
    i = np.sort(sp['intensity_reduction'].unique())
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 92), sharey=True)
    ratio = bc['B_AR_kt'] / bc['B_AtP_kt']
    for a_, col, letter, title, ar, atp in ((ax[0], 'LoE_AR', 'a', 'Level of exceedance of AR', 1.0, 1.0 / ratio),
                                           (ax[1], 'LoE_AtP', 'b', 'Level of exceedance of AtP', ratio, 1.0)):
        Z = sp.pivot(index='intensity_reduction', columns='demand_reduction', values=col).loc[i, d].values
        X, Y = np.meshgrid(100 * d, 100 * i)
        S.boundary_field(a_, X, Y, Z, ar, atp)
        cs = a_.contour(X, Y, Z, levels=[0.5, 2, 3, 4, 8, 12, 16], colors=S.MUTED, linewidths=S.LW_THIN * 0.7)
        a_.clabel(cs, fmt='%g', fontsize=S.FONT_MIN)
        for m in bc['solution_space_markers']:
            run = m['run']
            if run == 'TL':
                a_.plot(100 * m['demand_reduction'], 100 * m['intensity_reduction'], color=S.TL, ls='none',
                        **S.TL_MARKER, zorder=6)
                continue
            P_, s = run.split('-')
            a_.plot(100 * m['demand_reduction'], 100 * m['intensity_reduction'], marker='o', ms=5, ls='none',
                    color=S.PATHWAY[P_], markerfacecolor=S.PATHWAY[P_] if s == 'moderate' else 'none',
                    markeredgewidth=1.0, zorder=5)
        a_.set_xlabel('Cut in 2027-2050 floor area (%)')
        a_.set_xlim(0, 100)
        a_.set_ylim(0, 100)
        a_.grid(False)
        P.panel(a_, letter, title)
    ax[0].set_ylabel('Cut in carbon per m² of 2027-2050 floor area (%)')
    h = [Line2D([0], [0], marker='o', ls='none', color=S.PATHWAY[P_], markerfacecolor=S.PATHWAY[P_], ms=5,
                label=f'{P_} {N.PATHWAYS[P_]}') for P_ in ('P1', 'P2', 'P3', 'P4', 'P5')]
    h += [Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor=S.MUTED, ms=5, label='Moderate'),
          Line2D([0], [0], marker='o', ls='none', color=S.MUTED, markerfacecolor='none', ms=5, label='Ambitious'),
          Line2D([0], [0], ls='none', color=S.TL, label=N.TL['TL'], **S.TL_MARKER)]
    h += S.boundary_handles() + S.zone_handles()
    fig.legend(handles=h, loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    _save(fig, 'Fig6_solution_space', note='Markers at each run\'s effective cuts of 2027-2050 floor area and of non-soil '
                                           'carbon per m²; soil effects (L8, L9) are not on the plane.')


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
        for v, col in ((lo, S.LEVER['L6']), (hi, S.PATHWAY['P5'])):
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
    ax[0].legend(handles=[Patch(color=S.LEVER['L6'], label='low case'), Patch(color=S.PATHWAY['P5'], label='high case')],
                 loc='lower right', fontsize=S.FONT_MIN)
    fig.tight_layout()
    _save(fig, 'Fig7_tornado', note=f'Reference {c0:,.0f} kt (LoE AR {a0:.2f}, AtP {p0:.1f}); population rows move the '
                                    'budgets with the path; one-at-a-time ranges are not additive.')


# ---------------------------------------------------------------------------
# Fig8: Shapley value of each lever (Moderate hollow, Ambitious filled, TL dot)
# ---------------------------------------------------------------------------
def fig8():
    s = D.csv('pathways/shapley.csv')
    s = s[s['metric'] == 'carbon_kt']
    g = {k: s[s['game'] == f'levers_{k}'].set_index('player')['reduction'] for k in ('moderate', 'ambitious', 'tl')}
    order = list(g['ambitious'].sort_values().index)
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=S.figsize('double', 90))
    for k, L in enumerate(order):
        col = S.LEVER[L]
        ax.barh(k + 0.18, g['ambitious'][L], height=0.34, color=col, edgecolor=col, lw=S.LW_SEAM)
        ax.barh(k - 0.18, g['moderate'][L], height=0.34, facecolor='none', edgecolor=col, lw=S.LW_OUTLINE * 1.2)
        ax.plot(g['tl'][L], k, ls='none', color=S.TL, zorder=5, **S.TL_MARKER)
    ax.set_yticks(y)
    ax.set_yticklabels([f'{L} {N.LEVERS[L]}' for L in order])
    ax.axvline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_xlabel('Reduction of cumulative carbon 2026-2050 vs the Reference (kt CO₂e; exact Shapley value)')
    P.thousands(ax.xaxis)
    ax.legend(handles=[Patch(facecolor='none', edgecolor=S.MUTED, label='Moderate (Level 2)'),
                       Patch(facecolor=S.MUTED, edgecolor=S.MUTED, label='Ambitious (Level 3)'),
                       Line2D([0], [0], ls='none', color=S.TL, label='Theoretical limit (Level 4)', **S.TL_MARKER)],
              loc='lower right')
    fig.tight_layout()
    tot = {k: v.sum() for k, v in g.items()}
    _save(fig, 'Fig8_shapley_levers', note='Sum over levers (= Reference - P5 / TL, exact): ' + ', '.join(
        f'{k} {v:,.0f} kt' for k, v in tot.items()) + '; 512 subsets per setting.')


FIGURES = {'Fig1_floor_area': fig1, 'Fig2_reference_carbon': fig2, 'Fig3_reference_boundaries': fig3,
           'Fig4_pathways_annual': fig4, 'Fig5_waterfall': fig5, 'Fig6_solution_space': fig6, 'Fig7_tornado': fig7,
           'Fig8_shapley_levers': fig8}
