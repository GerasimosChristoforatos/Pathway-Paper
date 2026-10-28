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
    """MODEL v4.3.0 (ED9, from D31): annual embodied carbon of each lever alone (3 x 3, shared y), the Reference and
    the lever at Moderate, at Ambitious and at its Theoretical Limit, in the run colours of Fig3 / Fig4 (palette.toml
    [runs]); panel titles the lever names (MODEL v4.3.2: no strategy-colour square, no lever-specific colour); PCHIP display interpolation through every annual value, not
    across the observed pipeline years -> modelled join (pathways/lever_annual.csv)."""
    la = D.csv('pathways/lever_annual.csv')
    brk = P.pipeline_breaks()
    fig, ax = plt.subplots(3, 3, figsize=S.figsize('double', 130), sharex=True, sharey=True)
    for k, L in enumerate(LV.LEVERS):
        b = ax.ravel()[k]
        for lev, lab, st in ED8_RUNS:
            r = la[(la['lever'] == L) & (la['level'] == lev)].sort_values('year')
            b.plot(*P.pchip(r['year'].to_numpy(float), r['carbon_kt'].to_numpy(float), brk),
                   label=lab, zorder=3 if lev != 'reference' else 2, **st)
        b.text(0.0, 1.07, f'{L} {N.LEVERS[L]}', transform=b.transAxes, ha='left', va='center',
               fontsize=S.FONT_SIZE, color=S.INK)
        b.set_xlim(2026, 2050)
        b.set_ylim(0, None)
        P.thousands(b.yaxis)
    for b in ax[:, 0]:
        b.set_ylabel('kt CO₂e per year')
    h, l_ = ax[0, 0].get_legend_handles_labels()
    fig.legend(h, l_, loc='lower center', ncol=4, frameon=False, fontsize=S.FONT_SMALL, bbox_to_anchor=(0.5, 0.0),
               title='Embodied carbon per year: the Reference and each lever alone at', title_fontsize=S.FONT_SMALL)
    fig.tight_layout(rect=(0, 0.08, 1, 1), h_pad=1.6)
    S.save_figure(fig, 'ED8_lever_annual', note='Each panel: one lever alone; the other levers at the Reference. '
                                                'Lines: PCHIP display interpolation through the annual values.',
                  source=['pathways/lever_annual.csv', 'baseline/overbuild_2026.json'])


def sf15_tl_dwellings():
    lg = D.csv('pathways/reoccupation_log.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 75))
    for b, run, letter in ((ax[0], 'TL', 'a'), (ax[1], LV.TL_INSTANT_LABEL, 'b')):
        r = lg[lg['run'] == run]
        yr = r['year'].values
        P.line(b, yr, r['gross_after_payback'] / 1e3, color=S.INK, lw=S.LW, label='Need after the overbuild payback')
        b.bar(yr, r['built'] / 1e3, width=0.75, color=S.NEUTRAL_DARK, alpha=0.5, label='Dwellings built')
        b.bar(yr, r['reoccupied'] / 1e3, bottom=r['built'] / 1e3, width=0.75, facecolor='none',
              edgecolor=S.BAND['released_tl'][0], lw=S.LW_OUTLINE, label='Re-occupied (released dwellings)')
        pooled = 'released_pool' in r and (r['released_overbuild'] != 0).any()
        P.line(b, yr, (r['released_pool'] if 'released_pool' in r else r['released_tl1'] + r['released_tl2']) / 1e3,
               color=S.BAND['released_tl'][0], ls='--', lw=S.LW,
               label='Entering the pool (TL1 + TL2 + overbuild)' if pooled else 'Released (TL1 + TL2)')
        bind = r[r['release_binds']]
        b.plot(bind['year'], bind['built'] / 1e3, 'v', color=S.RELEASE_BINDS, ms=4, label='Release constraint binds')
        b.axhline(0, color=S.INK, lw=S.LW_THIN)
        b.set_xlim(2025.5, 2050.5)
        P.panel(b, letter, N.TL['TL'] if run == 'TL' else f"{N.TL['TL']} from 2027 (instant; sensitivity)")
    ax[0].set_ylabel('Dwellings per year (thousand)')
    ax[0].legend(fontsize=S.FONT_MIN)
    fig.tight_layout()
    S.save_figure(fig, 'SF15_tl_dwellings', source=['pathways/reoccupation_log.csv'])


FIGURES = {'ED8_lever_annual': ed8_lever_annual, 'SF15_tl_dwellings': sf15_tl_dwellings}   # MODEL v4.3.1 numbers
