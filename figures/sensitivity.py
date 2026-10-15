"""Sensitivity diagnostics (outputs/diagnostics/sensitivity/), from the data files only."""
import numpy as np
import matplotlib.pyplot as plt

from figures import data as D
from figures import draw as P
from figures import style as S


def _rows(ax, df, value, central, unit, log=False):
    df = df.reset_index(drop=True)
    groups = list(dict.fromkeys(df['group']))
    y = np.arange(len(df))[::-1]
    for k, r in df.iterrows():
        col = S.QUALITATIVE[groups.index(r['group']) % len(S.QUALITATIVE)]
        ax.barh(y[k], r[value] - central, left=central, height=0.7, color=col, edgecolor=col, lw=S.LW_SEAM)
    ax.axvline(central, color=S.INK, lw=S.LW_THIN)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['row']}" + (f" ({r['side']})" if r['side'] != 'single' else '') for _, r in df.iterrows()],
                       fontsize=S.FONT_MIN)
    ax.set_xlabel(unit)
    if log:
        ax.set_xscale('log')
    handles = [plt.Rectangle((0, 0), 1, 1, color=S.QUALITATIVE[i % len(S.QUALITATIVE)], label=g)
               for i, g in enumerate(groups)]
    ax.legend(handles=handles, fontsize=S.FONT_MIN, loc='lower right')


def d16():
    r = D.csv('sensitivity/reference_carbon.csv')
    fig, ax = plt.subplots(figsize=S.figsize('double', 150))
    _rows(ax, r, 'carbon_kt', float(r['central_carbon_kt'].iloc[0]), 'Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax.xaxis)
    fig.tight_layout()
    S.save_figure(fig, 'D16_one_at_a_time', note='Every one-at-a-time row of the Reference; not additive, not a joint '
                                                 'interval.', source=['sensitivity/reference_carbon.csv'])


def d17():
    a = D.csv('baseline/sensitivity_annual_carbon.csv')
    fig, ax = plt.subplots(figsize=S.figsize('double', 95))
    groups = list(dict.fromkeys(a['group']))
    for case, t in a.groupby('case', sort=False):
        g = t['group'].iloc[0]
        ref = g == 'Reference'
        ax.plot(t['year'], t['carbon_kt'], color=S.INK if ref else S.QUALITATIVE[groups.index(g) % 8],
                lw=S.LW_BOLD if ref else S.LW_THIN, alpha=1.0 if ref else 0.8, label=g if t.index[0] == a[a['group'] == g].index[0] else None)
    ax.set_xlim(2026, 2050)
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(fontsize=S.FONT_MIN, ncol=2)
    fig.tight_layout()
    S.save_figure(fig, 'D17_sensitivity_paths', source=['baseline/sensitivity_annual_carbon.csv'])


def d40():
    imp = D.csv('pathways/montecarlo_importance.csv')
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 70), sharey=True)
    inputs = list(dict.fromkeys(imp['input']))
    y = np.arange(len(inputs))
    runs = list(dict.fromkeys(imp['run']))
    for a, out, letter in zip(ax, ('floor_area_Mm2', 'carbon_kt', 'LoE_AR'), 'abc'):
        for j, run in enumerate(runs):
            t = imp[(imp['run'] == run) & (imp['output'] == out)].set_index('input').loc[inputs]
            off = (j - (len(runs) - 1) / 2) * 0.2
            col = {'REF': S.REFERENCE, 'P5': S.PATHWAY['P5'], 'TL': S.TL}.get(run, S.MUTED)
            a.errorbar(t['prcc'], y + off, xerr=[t['prcc'] - t['prcc_lo'], t['prcc_hi'] - t['prcc']], fmt='o', ms=3,
                       color=col, lw=S.LW_THIN, label=run)
        a.axvline(0, color=S.INK, lw=S.LW_THIN)
        a.set_xlim(-1, 1)
        a.set_xlabel('PRCC (95% bootstrap interval)')
        P.panel(a, letter, {'floor_area_Mm2': 'Floor area', 'carbon_kt': 'Carbon', 'LoE_AR': 'LoE AR'}[out])
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(inputs, fontsize=S.FONT_SMALL)
    ax[0].legend(fontsize=S.FONT_MIN)
    fig.tight_layout()
    S.save_figure(fig, 'D40_src_prcc', note=f"Bootstrap resamples: {int(imp['bootstrap_resamples'].iloc[0])}; SRC and "
                                            "R² in the data file.", source=['pathways/montecarlo_importance.csv'])


def d41():
    r = D.csv('sensitivity/p5_carbon.csv')
    fig, ax = plt.subplots(figsize=S.figsize('double', 90))
    _rows(ax, r, 'carbon_kt', float(r['central_carbon_kt'].iloc[0]), 'Cumulative carbon 2026-2050 (kt CO₂e)')
    P.thousands(ax.xaxis)
    fig.tight_layout()
    S.save_figure(fig, 'D41_p5_sensitivity', source=['sensitivity/p5_carbon.csv'])


def d42():
    r = D.csv('sensitivity/planetary_boundary.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 85), sharey=True)
    _rows(ax[0], r, 'LoE_AR', float(r['central_LoE_AR'].iloc[0]), 'Cumulative LoE of AR')
    _rows(ax[1], r, 'LoE_AtP', float(r['central_LoE_AtP'].iloc[0]), 'Cumulative LoE of AtP')
    ax[1].get_legend().remove()
    fig.tight_layout()
    S.save_figure(fig, 'D42_pb_sensitivity', source=['sensitivity/planetary_boundary.csv'])


FIGURES = {'D16_one_at_a_time': d16, 'D17_sensitivity_paths': d17, 'D40_src_prcc': d40, 'D41_p5_sensitivity': d41,
           'D42_pb_sensitivity': d42}
