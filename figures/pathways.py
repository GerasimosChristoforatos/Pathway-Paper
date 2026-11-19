"""Pathway diagnostics (outputs/diagnostics/pathways/; figure_plan.DIAGNOSTICS['pathways']), from the data files only."""
import matplotlib.pyplot as plt

import levers as LV
import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S


ED8_RUNS = (('reference', N.SCENARIOS['REF'], dict(color=S.REFERENCE, lw=S.LW_BOLD)),
            ('moderate', 'Moderate', dict(color=S.PATHWAY_SETTING['moderate'], lw=S.LW)),
            ('ambitious', 'Ambitious', dict(color=S.PATHWAY_SETTING['ambitious'], lw=S.LW)),
            ('tl', N.TL['TL'], dict(color=S.TL, lw=S.LW)))


def ed8_lever_annual():
    """ED7 (data D31): annual embodied carbon of each lever alone (4 x 3 grid, ten panels, shared y; the legend in the
    two empty cells), the Reference and
    the lever at Moderate, at Ambitious and at its Theoretical Limit, in the run colours of Fig3 / Fig4 (palette.toml
    [runs]); panel titles the lever names (no strategy-colour square, no lever-specific colour); PCHIP display interpolation through every annual value, not
    across the observed pipeline years -> modelled join (pathways/lever_annual.csv)."""
    la = D.csv('pathways/lever_annual.csv')
    brk = P.pipeline_breaks()
    nrow = -(-len(LV.LEVERS) // 3)
    fig, ax = plt.subplots(nrow, 3, figsize=S.figsize('double', 43 * nrow + 2), sharex=True, sharey=True)
    for b in ax.ravel()[len(LV.LEVERS):]:              # the empty cells hold the legend
        b.set_visible(False)
    for k, L in enumerate(LV.LEVERS):
        b = ax.ravel()[k]
        for lev, lab, st in ED8_RUNS:
            r = la[(la['lever'] == L) & (la['level'] == lev)].sort_values('year')
            b.plot(*P.pchip(r['year'].to_numpy(float), r['carbon_kt'].to_numpy(float), brk),
                   label=lab, zorder=3 if lev != 'reference' else 2, **st)
        P.panel(b, 'abcdefghijkl'[k], f'{L} {N.LEVERS[L]}')
        b.set_xlim(2026, 2050)
        b.set_ylim(0, None)
        P.thousands(b.yaxis)
    for b in ax[:, 0]:
        b.set_ylabel('kt CO₂e per year')
    for b in ax.ravel()[len(LV.LEVERS) - 3:len(LV.LEVERS)]:   # x tick labels on the last panel of each column
        b.xaxis.set_tick_params(labelbottom=True)
    h, l_ = ax[0, 0].get_legend_handles_labels()
    fig.tight_layout(h_pad=1.6)
    e0, e1 = ax.ravel()[len(LV.LEVERS)].get_position(), ax.ravel()[-1].get_position()
    fig.legend(h, l_, loc='center', ncol=2, frameon=False, fontsize=S.FONT_SMALL,
               bbox_to_anchor=((e0.x0 + e1.x1) / 2, (e0.y0 + e0.y1) / 2),
               title='Embodied carbon per year: the Reference\nand each lever alone at', title_fontsize=S.FONT_SMALL)
    S.save_figure(fig, 'ED7_lever_annual', note='Each panel: one lever alone; the other levers at the Reference. '
                                                'Lines: PCHIP display interpolation through the annual values.',
                  source=['pathways/lever_annual.csv', 'baseline/overbuild_2026.json'])


def sf14_tl_dwellings():
    lg = D.csv('pathways/reoccupation_log.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 75))
    for b, run, letter in ((ax[0], 'TL', 'a'), (ax[1], LV.TL_INSTANT_LABEL, 'b')):
        r = lg[lg['run'] == run]
        yr = r['year'].values
        P.line(b, yr, r['gross_after_payback'] / 1e3, color=S.INK, lw=S.LW, label='Need after the surplus payback')
        b.bar(yr, r['built'] / 1e3, width=0.75, color=S.NEUTRAL_DARK, alpha=S.FIXED_FADES['neutral_bars'], label='Dwellings built')
        b.bar(yr, r['reoccupied'] / 1e3, bottom=r['built'] / 1e3, width=0.75, facecolor='none',
              edgecolor=S.BAND['released_tl'][0], lw=S.LW_OUTLINE, label='Re-occupied (released dwellings)')
        pooled = 'released_pool' in r and (r['released_overbuild'] != 0).any()
        P.line(b, yr, (r['released_pool'] if 'released_pool' in r else r['released_tl1'] + r['released_tl2']) / 1e3,
               color=S.BAND['released_tl'][0], ls='--', lw=S.LW,
               label='Entering the pool (TL1 + TL2 + starting surplus + overbuild)' if pooled
               else 'Released (TL1 + TL2)')
        bind = r[r['release_binds']]
        if len(bind):                                  # a legend entry only where a marker is drawn
            b.plot(bind['year'], bind['built'] / 1e3, 'v', color=S.RELEASE_BINDS, ms=4, label='Release constraint binds')
        b.axhline(0, color=S.INK, lw=S.LW_THIN)
        b.set_xlim(2025.5, 2050.5)
        P.panel(b, letter, N.TL['TL'] if run == 'TL' else f"{N.TL['TL']}, instant start")
    for b in ax:                                       # own y scales: each panel labelled
        b.set_ylabel('Dwellings per year (thousand)')
    ax[0].legend(fontsize=S.FONT_MIN, loc='upper right')    # the empty corner (the 6-pt legend clears the pool peak)
    fig.tight_layout()
    S.save_figure(fig, 'SF15_tl_dwellings', note=f"(b) The {N.TL['TL']} at full strength from 2027 "
                                                 '(no phase-in; sensitivity).',
                  source=['pathways/reoccupation_log.csv'])


FIGURES = {'ED7_lever_annual': ed8_lever_annual, 'SF15_tl_dwellings': sf14_tl_dwellings}
