"""Monte Carlo diagnostics (outputs/diagnostics/montecarlo/), from the data files only."""
import numpy as np
import matplotlib.pyplot as plt

import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S

INPUT_LABELS = {'z_pop': 'Population (with household size)', 'size': 'Future dwelling size',
                'complete': 'Completion rate', 'carbon': 'Carbon factors (case-study bootstrap)',
                'half_life': 'Replacement half-life (yr)'}


def d20():
    """Sobol indices of the Reference (full profile only: the light profile does not compute them)."""
    sob = D.csv('montecarlo/sobol_REF.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 66))
    for a, o, letter, title in zip(ax, ['carbon_kt', 'floor_area_Mm2'], 'ab',
                                   ['Embodied carbon, 2026–2050', 'Built floor area, 2026–2050']):
        t = sob[(sob.output == o) & np.isfinite(sob.ST_lo)].sort_values('ST')
        y = np.arange(len(t))
        a.barh(y + 0.2, t.ST, 0.4, color=S.QUALITATIVE[5], xerr=[t.ST - t.ST_lo, t.ST_hi - t.ST], ecolor=S.INK,
               capsize=1.5, error_kw=dict(lw=S.LW_THIN), label='Total effect (incl. interactions), 95% CI')
        a.barh(y - 0.2, t.S1.clip(lower=0), 0.4, color=S.QUALITATIVE[2], label='First-order effect (on its own)')
        a.set_yticks(y)
        a.set_yticklabels([INPUT_LABELS.get(i, i) for i in t.input], fontsize=S.FONT_SMALL)
        a.set_xlim(0, max(0.7, t.ST_hi.max() + 0.08))
        a.set_xlabel('Share of output variance')
        a.grid(axis='y', visible=False)
        P.panel(a, letter, title)
    fig.legend(*ax[0].get_legend_handles_labels(), loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.01),
               frameon=False)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    S.save_figure(fig, 'D20_sobol', note='Reference; Saltelli / Jansen estimators (scipy.stats.sobol_indices); full '
                                         'profile only.', source=['montecarlo/sobol_REF.csv'])


def d37():
    c = D.csv('montecarlo/convergence_REF.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 62))
    for a, o, letter, unit in zip(ax, ['carbon_kt', 'floor_area_Mm2'], 'ab', ['kt CO₂e', 'Mm²']):
        t = c[c['output'] == o]
        # MODEL v3.1.0 (B3): four distinct styles (line style, marker, weight)
        for q, ls, mk, lw, lab in (('p5', ':', 'v', S.LW, '5th percentile'), ('p50', '-', 'o', S.LW_BOLD, 'Median (50th)'),
                                   ('p95', '-.', '^', S.LW, '95th percentile'), ('mean', '--', 's', S.LW, 'Mean')):
            a.plot(t['n'], t[q], color=S.REFERENCE, ls=ls, marker=mk, ms=3, lw=lw, label=lab)
        a.set_xscale('log')
        a.set_xlabel('Number of Latin hypercube draws')
        a.set_ylabel(f'2026–2050 total ({unit})')
        P.panel(a, letter, 'Embodied carbon' if o == 'carbon_kt' else 'Floor area')
    ax[0].legend(fontsize=S.FONT_MIN)
    fig.tight_layout()
    S.save_figure(fig, 'D37_mc_convergence', note=f"Percentiles over the first n draws (largest n = {c['n'].max():,}).",
                  source=['montecarlo/convergence_REF.csv'])


def d38():
    """MODEL v3.1.0 (B3): the carbon panel shows the resulting pooled A1-A3 factor of each draw by typology
    (kg CO2e/m2, 2025 technology; montecarlo/carbon_factors_REF.csv) instead of the uniform parameter behind it."""
    dr = D.csv('montecarlo/draws_REF.csv')
    q = D.csv('montecarlo/input_distributions_REF.csv').set_index('input')
    cf = D.csv('montecarlo/carbon_factors_REF.csv')
    cols = [c for c in ('z_pop', 'size', 'complete', 'half_life') if c in dr.columns]
    fig, ax = plt.subplots(1, len(cols) + 1, figsize=S.figsize('double', 55))
    for a, c in zip(ax, cols):
        a.hist(dr[c], bins=30, color=S.REFERENCE, alpha=0.6)
        for k in ('q05', 'q50', 'q95'):
            a.axvline(q.loc[c, k], color=S.INK, lw=S.LW_THIN, ls='-' if k == 'q50' else ':')
        a.set_title(INPUT_LABELS[c], fontsize=S.FONT_SMALL, loc='left')
        a.tick_params(labelsize=S.FONT_MIN)
    a = ax[-1]
    tcol = {'Detached': S.LEVER['L4'], 'Townhouses': S.LEVER['L8'], 'Apartments': S.LEVER['L2']}
    for t, g in cf.groupby('typology', sort=False):
        v = g['a1a3_kg_per_m2'].to_numpy(float)
        a.hist(v, bins=30, color=tcol.get(t, S.MUTED), alpha=0.55, label=t)
        a.axvline(np.median(v), color=tcol.get(t, S.MUTED), lw=S.LW_THIN)
    a.set_title('A1-A3 factor (kg CO₂e/m², 2025)', fontsize=S.FONT_SMALL, loc='left')
    a.legend(fontsize=S.FONT_MIN)
    a.tick_params(labelsize=S.FONT_MIN)
    fig.tight_layout()
    S.save_figure(fig, 'D38_mc_input_distributions',
                  note=f'{len(dr):,} draws; lines at the 5th, 50th and 95th percentiles of each input distribution; '
                       'carbon: the resulting pooled A1-A3 factor of each draw by typology (median line).',
                  source=['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv',
                          'montecarlo/carbon_factors_REF.csv'])


def d39():
    a = D.csv('pathways/montecarlo_annual.csv')
    s = D.csv('pathways/montecarlo_summary.csv')
    runs = [('REF', N.SCENARIOS['REF'], S.REFERENCE),
            ('pathway_moderate', N.PATHWAY_RUNS['pathway-moderate'], S.PATHWAY[N.PATHWAY]),
            ('pathway_ambitious', N.PATHWAY_RUNS['pathway-ambitious'], S.LEVER['L5']), ('TL', N.TL['TL'], S.TL)]
    fig, ax = plt.subplots(figsize=S.figsize('double', 75))
    for r, lab, col in runs:
        t = a[a['run'] == r]
        ax.fill_between(t['year'], t['carbon_kt_p5'], t['carbon_kt_p95'], color=col, alpha=0.15, lw=0)
        ax.plot(t['year'], t['carbon_kt_p50'], color=col, lw=S.LW_BOLD, label=f'{lab} (median, 5–95%)')
    ax.set_xlim(2026, 2050)
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(fontsize=S.FONT_SMALL)
    fig.tight_layout()
    p = s[(s['quantity'] == 'LoE_AR')].set_index('run')['probability_LoE_at_most_1']
    S.save_figure(fig, 'D39_pathway_mc', note='P(cumulative LoE AR <= 1): ' + ', '.join(
        f'{k} {v:.3f}' for k, v in p.items()) + '.', source=['pathways/montecarlo_annual.csv',
                                                            'pathways/montecarlo_summary.csv'])


FIGURES = {'D20_sobol': d20, 'D37_mc_convergence': d37, 'D38_mc_input_distributions': d38, 'D39_pathway_mc': d39}
