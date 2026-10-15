"""Pathway diagnostics (outputs/diagnostics/pathways/; figure_plan.DIAGNOSTICS['pathways']), from the data files only."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import levers as LV
import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S

LEVEL_STYLE = {'reference': dict(color=S.REFERENCE, lw=S.LW_BOLD, ls='-'),
               'moderate': dict(lw=S.LW_BOLD, ls='-'), 'ambitious': dict(lw=S.LW_THIN, ls=':'),
               'tl': dict(color=S.TL, lw=S.LW, ls='-')}
LEVEL_LABEL = {'reference': 'Reference', 'moderate': 'Moderate', 'ambitious': 'Ambitious', 'tl': 'TL (Level 4)'}


def _ref_annual():
    a = D.csv('pathways/annual.csv')
    return a[a['scenario'] == 'REF']


def d28():
    a = _ref_annual()
    ref = a[a['run'] == 'REF'].set_index('year')
    yrs = ref.index.values.astype(float)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 80), sharey=True)
    for k, (s, letter) in enumerate((('moderate', 'a'), ('ambitious', 'b'))):
        b = ax[k]
        S.boundary_zones(b, yrs, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
        b.plot(yrs, ref['carbon_kt'], color=S.REFERENCE, lw=S.LW_BOLD, label=N.SCENARIOS['REF'])
        for P_ in ('P1', 'P2', 'P3', 'P4', 'P5'):
            r = a[a['run'] == f'{P_}-{s}'].set_index('year')
            b.plot(yrs, r['carbon_kt'], color=S.PATHWAY[P_], lw=S.LW, label=f'{P_} {N.PATHWAYS[P_]}')
        t = a[a['run'] == 'TL'].set_index('year')
        b.plot(yrs, t['carbon_kt'], color=S.TL, lw=S.LW, label=N.TL['TL'])
        b.set_xlim(yrs[0], yrs[-1])
        b.set_ylim(0, None)
        P.panel(b, letter, N.SETTINGS[s])
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    fig.legend(handles=ax[0].get_legend_handles_labels()[0] + S.zone_handles(), loc='lower center', ncol=5,
               bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    S.save_figure(fig, 'D28_pathways_annual', source=['pathways/annual.csv'])


def d29():
    """The adoption weight and the native parameter of each lever at Reference, Moderate, Ambitious and TL."""
    p = D.js('pathways/levers.json')
    years = np.array(sorted(int(y) for y in p['adoption']['w']))
    w = np.array([p['adoption']['w'][str(y)] for y in years])
    fig, ax = plt.subplots(2, 5, figsize=S.figsize('double', 105))
    ax = ax.ravel()
    ax[0].plot(years, w, color=S.INK)
    ax[0].set_title('Adoption weight w(y)', fontsize=S.FONT_SMALL, loc='left')
    typ = list(p['L1']['size_ref'])

    def lvl(L, level):                         # native value(s) at full strength
        if level == 'tl':
            return p[L]['tl']
        return {'L1': p['L1']['f'], 'L2': p['L2']['r'], 'L4': p['L4']['v'], 'L5': p['L5']['d'],
                'L6': p['L6']['r'], 'L8': p['L8']['x'], 'L9': p['L9']['s']}[L][level]
    levels = ('reference', 'moderate', 'ambitious', 'tl')
    for k, L in enumerate(LV.LEVERS, start=1):
        b = ax[k]
        col = S.LEVER[L]
        if L in ('L3', 'L7'):                  # path levers: the target path by year at each level
            key = 'S' if L == 'L3' else 'target'
            for lev in levels:
                if lev == 'tl':
                    yv = np.full(len(years), p['L3']['tl'] if L == 'L3' else 0.0)
                else:
                    yv = np.array([p[L][key][lev][str(y)] for y in years])
                st = dict(LEVEL_STYLE[lev])
                st.setdefault('color', col)
                b.plot(years, yv, label=LEVEL_LABEL[lev], **st)
            b.set_ylabel('household size' if L == 'L3' else 'A4-A5 factor', fontsize=S.FONT_MIN)
        else:
            x = np.arange(len(levels))
            if L in ('L1', 'L2', 'L6', 'L8'):
                for j, t in enumerate(typ):
                    vals = []
                    for lev in levels:
                        v = lvl(L, lev)
                        if L == 'L8' and lev != 'tl':     # x as the soil factor
                            v = p['L8']['soil_factor_2025'][t] * (1 - v)
                        elif L == 'L8':
                            v = v[t]
                        else:
                            v = v[t] if isinstance(v, dict) else v
                        vals.append(v)
                    b.plot(x, vals, marker='o', ms=3, color=col, alpha=[1.0, 0.65, 0.35][j], label=t)
            elif L == 'L5':
                b.plot(x, [lvl(L, lev) if lev != 'tl' else 1.0 for lev in levels], marker='o', ms=3, color=col)
            else:
                b.plot(x, [lvl(L, lev) for lev in levels], marker='o', ms=3, color=col)
            b.set_xticks(x)
            b.set_xticklabels(['Ref', 'Mod', 'Amb', 'TL'], fontsize=S.FONT_MIN)
        b.set_title(f'{L} {N.LEVERS[L]} [{p["subrule"][L]}]', fontsize=S.FONT_MIN + 0.5, loc='left')
        b.tick_params(labelsize=S.FONT_MIN)
    ax[3].legend(fontsize=S.FONT_MIN - 0.5, loc='best')
    ax[1].legend(fontsize=S.FONT_MIN - 0.5, loc='best')
    fig.tight_layout()
    S.save_figure(fig, 'D29_ramps', note='Native parameter at each level (full strength); every level moves from the '
                                         'Reference along w(y) (2026 -> 2035). Moderate is the exact midpoint. L3 (and '
                                         'L7): the target paths by year before the adoption weighting w(y) is applied.',
                  source=['pathways/levers.json'])


def d31():
    la = D.csv('pathways/lever_annual.csv')
    fig, ax = plt.subplots(3, 3, figsize=S.figsize('double', 120), sharex=True)
    for k, L in enumerate(LV.LEVERS):
        b = ax.ravel()[k]
        for lev in ('reference', 'moderate', 'ambitious', 'tl'):
            r = la[(la['lever'] == L) & (la['level'] == lev)]
            st = dict(LEVEL_STYLE[lev])
            st.setdefault('color', S.LEVER[L])
            b.plot(r['year'], r['carbon_kt'], label=LEVEL_LABEL[lev], **st)
        b.set_title(f'{L} {N.LEVERS[L]}', fontsize=S.FONT_SMALL, loc='left')
        b.set_ylim(0, None)
        b.tick_params(labelsize=S.FONT_MIN)
    ax[0, 0].legend(fontsize=S.FONT_MIN)
    fig.supylabel('Embodied carbon (kt CO₂e per year)', fontsize=S.FONT_SIZE)
    fig.tight_layout()
    S.save_figure(fig, 'D31_lever_annual', source=['pathways/lever_annual.csv'])


def d32():
    r = D.csv('pathways/runs.csv')
    r = r[r['scenario'] == 'REF'].set_index('run')
    t = D.js('pathways/theoretical_limit.json')['runs']['TL']
    runs = ['REF', 'P5-moderate', 'P5-ambitious', 'TL']
    lab = [N.SCENARIOS['REF'], 'P5 Moderate', 'P5 Ambitious', N.TL['TL']]
    cols = [S.REFERENCE, S.PATHWAY['P5'], S.PATHWAY['P5'], S.TL]
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 70))
    x = np.arange(len(runs))
    ax[0].bar(x, [r.loc[k, 'LoE_AR'] for k in runs], color=cols, edgecolor=cols, lw=S.LW_SEAM)
    ax[0].axhline(1.0, **{k: v for k, v in S.BOUNDARY['AR'].items() if k != 'label'}, gid='boundary')
    S.boundary_hzones(ax[0], 1.0, float(r.loc['REF', 'B_AtP_kt'] / r.loc['REF', 'B_AR_kt']))
    ax[0].set_ylabel('Cumulative LoE of AR 2026-2050')
    P.panel(ax[0], 'a', 'Level of exceedance')
    ax[1].bar(x, [r.loc[k, 'mean_dwelling_size_m2'] for k in runs], color=cols, edgecolor=cols, lw=S.LW_SEAM)
    ax[1].set_ylabel('Mean new-dwelling size (m²)')
    P.panel(ax[1], 'b', 'Dwelling size')
    ax[2].bar(x, [r.loc[k, 'dwellings_built'] / 1e3 for k in runs], color=cols, edgecolor=cols, lw=S.LW_SEAM)
    ax[2].set_ylabel('Dwellings built 2026-2050 (thousand)')
    P.panel(ax[2], 'c', 'Dwellings built')
    for b in ax:
        b.set_xticks(x)
        b.set_xticklabels(lab, rotation=30, ha='right', fontsize=S.FONT_MIN + 0.5)
    fig.tight_layout()
    S.save_figure(fig, 'D32_tl_staircase',
                  note=f"TL re-occupies R = {t['R']:,.0f} released dwellings (TL3 {t['R3']:,.0f}, TL4 {t['R4']:,.0f}) "
                       f"at a share s = {t['share_of_need']:.3f} of need (G+ {t['G_plus']:,.0f}).",
                  source=['pathways/runs.csv', 'pathways/theoretical_limit.json'])


def d33():
    o = D.js('pathways/ordering_checks.json')
    la = D.csv('pathways/lever_annual.csv')
    cum = la.groupby(['lever', 'level'])['carbon_kt'].sum().unstack()
    fig, ax = plt.subplots(figsize=S.figsize('double', 75))
    x = np.arange(len(LV.LEVERS))
    for j, lev in enumerate(('reference', 'moderate', 'ambitious', 'tl')):
        v = [cum.loc[L, lev] for L in LV.LEVERS]
        st = dict(color=S.REFERENCE) if lev == 'reference' else dict(color=S.TL) if lev == 'tl' else {}
        cols = [st.get('color', S.LEVER[L]) for L in LV.LEVERS]
        if lev == 'moderate':
            ax.bar(x - 0.3 + 0.2 * j, v, width=0.2, facecolor='none', edgecolor=cols, lw=S.LW_OUTLINE, label='Moderate')
        else:
            ax.bar(x - 0.3 + 0.2 * j, v, width=0.2, color=cols, edgecolor=cols, lw=S.LW_SEAM,
                   label=LEVEL_LABEL[lev], alpha=0.55 if lev == 'reference' else 1.0)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{L}\n{N.LEVERS[L]}' for L in LV.LEVERS], fontsize=S.FONT_MIN)
    ax.set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax.yaxis)
    ax.legend(fontsize=S.FONT_MIN, ncol=4)
    rev = '; '.join(f"{r['lever']} {r['pair']} in {r['years'][0]}-{r['years'][-1]} (max {r['max_kt']:.0f} kt)"
                    for r in o['carbon_year_reversals']) or 'none'
    fig.tight_layout()
    S.save_figure(fig, 'D33_ordering_checks',
                  note=f"Native-parameter ordering Reference >= Moderate >= Ambitious >= TL: "
                       f"{len(o['violations'])} violations (per lever, typology and year). Cumulative carbon ordering "
                       f"holds for every lever. Annual-carbon reversals (timing only, not a STOP): {rev}.",
                  source=['pathways/ordering_checks.json', 'pathways/lever_annual.csv'])


def d34():
    lg = D.csv('pathways/reoccupation_log.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 75))
    for b, run, letter in ((ax[0], 'TL', 'a'), (ax[1], LV.TL_INSTANT_LABEL, 'b')):
        r = lg[lg['run'] == run]
        yr = r['year'].values
        b.plot(yr, r['gross_after_payback'] / 1e3, color=S.INK, lw=S.LW, label='Need after the overbuild payback')
        b.bar(yr, r['built'] / 1e3, width=0.75, color=S.REFERENCE, alpha=0.5, label='Dwellings built')
        b.bar(yr, r['reoccupied'] / 1e3, bottom=r['built'] / 1e3, width=0.75, facecolor='none',
              edgecolor=S.BAND['released_tl'][0], lw=S.LW_OUTLINE, label='Re-occupied (released dwellings)')
        b.plot(yr, (r['released_tl3'] + r['released_tl4']) / 1e3, color=S.BAND['released_tl'][0], ls='--',
               lw=S.LW, label='Released (TL3 + TL4)')
        bind = r[r['release_binds']]
        b.plot(bind['year'], bind['built'] / 1e3, 'v', color=S.AR, ms=4, label='Release constraint binds')
        b.axhline(0, color=S.INK, lw=S.LW_THIN)
        b.set_xlim(2025.5, 2050.5)
        P.panel(b, letter, 'TL' if run == 'TL' else 'Instant TL (sensitivity)')
    ax[0].set_ylabel('Dwellings per year (thousand)')
    ax[0].legend(fontsize=S.FONT_MIN)
    fig.tight_layout()
    S.save_figure(fig, 'D34_tl_dwellings', source=['pathways/reoccupation_log.csv'])


def d36():
    bd = D.csv('pathways/bands.csv')
    bd = bd[(bd['scenario'] == 'REF') & (bd['definition'] == 'in_scope')]
    runs = ['REF'] + [f'{P_}-{s}' for s in ('moderate', 'ambitious') for P_ in ('P1', 'P2', 'P3', 'P4', 'P5')] + ['TL']
    tab = bd.pivot(index='run', columns='band', values='carbon_kt').loc[runs]
    tab.columns = [P.band_id(c) for c in tab.columns]
    tab = tab[[b for b in N.BANDS_IN_SCOPE_TL if b in tab.columns]]
    r = D.csv('pathways/runs.csv')
    tot = r[r['scenario'] == 'REF'].set_index('run').loc[runs, 'carbon_kt'].values
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    x = np.arange(len(runs))
    P.bars_cumulative(ax, x, [(b, tab[b].values) for b in tab.columns], width=0.7, net=tot)
    ax.set_xticks(x)
    ax.set_xticklabels(runs, rotation=45, ha='right', fontsize=S.FONT_MIN + 0.5)
    ax.set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax.yaxis)
    P.band_legend(fig, list(tab.columns), ncol=4, y=-0.01,
                  extra=[Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label='Net total')])
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    S.save_figure(fig, 'D36_pathway_bands', source=['pathways/bands.csv', 'pathways/runs.csv'])


FIGURES = {'D28_pathways_annual': d28, 'D29_ramps': d29, 'D31_lever_annual': d31, 'D32_tl_staircase': d32,
           'D33_ordering_checks': d33, 'D34_tl_dwellings': d34, 'D36_pathway_bands': d36}
