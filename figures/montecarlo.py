"""Monte Carlo diagnostics (outputs/diagnostics/montecarlo/), from the data files only."""
import numpy as np
import matplotlib.pyplot as plt

import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S


def sf11_mc_convergence():
    c = D.csv('montecarlo/convergence_REF.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 62))
    for a, o, letter, unit in zip(ax, ['carbon_kt', 'floor_area_Mm2'], 'ab', ['kt CO₂e', 'Mm²']):
        t = c[c['output'] == o]
        # four distinct styles (line style, marker, weight)
        for q, ls, mk, lw, lab in (('p5', ':', 'v', S.LW, '5th percentile'), ('p50', '-', 'o', S.LW_BOLD, 'Median (50th)'),
                                   ('p95', '-.', '^', S.LW, '95th percentile'), ('mean', '--', 's', S.LW, 'Mean')):
            a.plot(t['n'], t[q], color=S.REFERENCE, ls=ls, marker=mk, ms=3, lw=lw, label=lab)
        a.set_xscale('log')
        a.set_xlabel('Number of Latin hypercube draws')
        a.set_ylabel(f'2026–2050 total ({unit})')
        P.thousands(a.yaxis)
        P.panel(a, letter, 'Embodied carbon' if o == 'carbon_kt' else 'Floor area')
    h, lab = ax[0].get_legend_handles_labels()                 # one legend below, clear of the lines
    fig.legend(h, lab, loc='lower center', ncol=4, fontsize=S.FONT_SMALL, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    S.save_figure(fig, 'SF11_mc_convergence', note=f"Percentiles over the first n draws (largest n = {c['n'].max():,}).",
                  source=['montecarlo/convergence_REF.csv'])


def _ed6_title(a, letter, title):
    """ED6 panel letter and input name: five narrow panels, so the name at the small size, on two lines when long."""
    P.panel(a, letter, P.two_lines(title) if len(title) > 18 else title)
    a.title.set_fontsize(S.FONT_SMALL)


def ed6_mc_input_distributions():
    """ED6 (data D38): the Monte Carlo input distributions, y = number of draws, panel titles the input
    names of naming.MC_INPUT (as ED7 and ED4). Population in physical units: the 2050 New Zealand population of each
    draw (pathways/montecarlo_draws.csv P_NZ_2050; the same draws as the Reference Monte Carlo, checked on every
    input column); dwelling size as the multiplier on the central future size; carbon factors: the resulting pooled
    A1-A3 factor of each draw by typology (typology colours). Lines: central value (solid), 5th / 95th percentile
    (dotted)."""
    from matplotlib.lines import Line2D
    dr = D.csv('montecarlo/draws_REF.csv')
    pw = D.csv('pathways/montecarlo_draws.csv')
    q = D.csv('montecarlo/input_distributions_REF.csv').set_index('input')
    cf = D.csv('montecarlo/carbon_factors_REF.csv')
    for c in ('z_pop', 'size', 'complete', 'half_life'):
        if not np.allclose(dr[c].to_numpy(float), pw[c].to_numpy(float), rtol=1e-12, atol=1e-12):   # CSV round-off
            raise SystemExit(f'STOP: ED6: the Reference and pathway Monte Carlo draws differ in {c}.')
    pop = pw['P_NZ_2050'].to_numpy(float) / 1e6
    panels = [('z_pop', pop, np.percentile(pop, [5, 50, 95]), '2050 population (million)'),
              ('size', dr['size'], [q.loc['size', k] for k in ('q05', 'q50', 'q95')],
               'Multiplier on the central future size'),
              ('complete', dr['complete'], [q.loc['complete', k] for k in ('q05', 'q50', 'q95')], 'Completion rate'),
              ('half_life', dr['half_life'], [q.loc['half_life', k] for k in ('q05', 'q50', 'q95')], 'Half-life (years)')]
    fig, ax = plt.subplots(1, 5, figsize=S.figsize('double', 62))
    for a, (c, v, qs, xl) in zip(ax, panels):
        a.hist(v, bins=30, color=S.NEUTRAL_DARK, alpha=S.FIXED_FADES['neutral_histogram'], lw=0)
        for k, x in enumerate(qs):
            a.axvline(x, color=S.INK, lw=S.LW_THIN, ls='-' if k == 1 else ':')
        _ed6_title(a, 'abcd'[ax.tolist().index(a)], N.MC_INPUT[c])
        a.set_xlabel(xl, fontsize=S.FONT_MIN + 0.5)
    a = ax[-1]
    for t, g in cf.groupby('typology', sort=False):
        v = g['a1a3_kg_per_m2'].to_numpy(float)
        a.hist(v, bins=30, color=S.TYPOLOGY[t], alpha=S.OPACITY['typology_histograms'], lw=0, label=t)
        for k, x in enumerate(np.percentile(v, [5, 50, 95])):
            a.axvline(x, color=S.TYPOLOGY[t], lw=S.LW_THIN, ls='-' if k == 1 else ':')
    _ed6_title(a, 'e', N.MC_INPUT['carbon'])
    a.set_xlabel('A1–A3 materials factor (kg CO₂e per m², 2025)', fontsize=S.FONT_MIN + 0.5)
    a.legend(fontsize=S.FONT_MIN, frameon=False, loc='upper right')
    for a in ax:
        a.tick_params(labelsize=S.FONT_MIN)
        a.grid(axis='x', visible=False)
    ax[0].set_ylabel('Number of draws')
    fig.legend(handles=[Line2D([0], [0], color=S.INK, lw=S.LW_THIN, ls='-', label='Central value (median)'),
                        Line2D([0], [0], color=S.INK, lw=S.LW_THIN, ls=':', label='5th / 95th percentile')],
               loc='lower center', ncol=2, frameon=False, fontsize=S.FONT_SMALL, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    # the apartments: whole embodied factor and the one independent case (factors_typology.csv, factors_building.csv)
    tf = D.csv('factors/factors_typology.csv').set_index('Typology')
    bf = D.csv('factors/factors_building.csv')
    ap = bf[(bf['Typology'] == 'Apartments') & bf['duplicate_of'].isna()]
    if len(ap) != 1 or int(tf.loc['Apartments', 'n_independent']) != 1:
        raise SystemExit('STOP: ED6: the apartments no longer rest on one independent case study; rewrite the note.')
    ap_case = float(ap['A1-A3'].iloc[0])
    ap_med = float(np.median(cf.loc[cf['typology'] == 'Apartments', 'a1a3_kg_per_m2']))
    if not ap_med < ap_case:
        raise SystemExit('STOP: ED6: the apartments median is not below the case value; rewrite the note.')
    S.save_figure(fig, 'ED6_mc_input_distributions',
                  note=f'{len(dr):,} Latin hypercube draws. Population: the 2050 New Zealand population of each draw '
                       '(the sampled standard-normal score mapped through the Stats NZ percentiles); carbon factors: the '
                       'pooled A1-A3 factor of each draw by typology. A1–A3 only (whole embodied A1–C4 is higher: '
                       f"apartments {tf.loc['Apartments', 'embodied_materials']:.0f} kg/m²). Apartments rest on one "
                       f'independent case study ({ap_case:.0f} kg/m² A1–A3) with a mean-preserving lognormal spread, so '
                       f'their median ({ap_med:.0f} kg/m²) lies slightly below the case value.',
                  source=['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv',
                          'montecarlo/carbon_factors_REF.csv', 'pathways/montecarlo_draws.csv',
                          'factors/factors_typology.csv', 'factors/factors_building.csv'])


def ed7_sobol():
    """ED7 (data D20): Sobol indices of the Reference (full profile only), input names of naming.MC_INPUT
    (as ED6), both panels x 0-1, y labels centred; total effect with its 95% interval and first-order effect."""
    sob = D.csv('montecarlo/sobol_REF.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 66))
    for a, o, letter, title in zip(ax, ['carbon_kt', 'floor_area_Mm2'], 'ab',
                                   ['Cumulative embodied carbon', 'Cumulative floor area built']):
        t = sob[(sob.output == o) & np.isfinite(sob.ST_lo)].sort_values('ST')
        y = np.arange(len(t))
        a.barh(y + 0.2, t.ST, 0.4, color=S.SOBOL['total'], xerr=[t.ST - t.ST_lo, t.ST_hi - t.ST], ecolor=S.INK,
               capsize=1.5, error_kw=dict(lw=S.LW_THIN), label='Total effect (incl. interactions), 95% interval')
        a.barh(y - 0.2, t.S1.clip(lower=0), 0.4, color=S.SOBOL['first_order'], label='First-order effect (on its own)')
        a.set_yticks(y)
        a.set_yticklabels([N.MC_INPUT[i] for i in t.input], fontsize=S.FONT_SMALL)
        a.set_xlim(0, 1)
        a.set_xlabel('Share of output variance')
        a.grid(axis='y', visible=False)
        P.panel(a, letter, title)
    fig.legend(*ax[0].get_legend_handles_labels(), loc='lower center', ncol=2, bbox_to_anchor=(0.5, 0.0),
               frameon=False, fontsize=S.FONT_SMALL)
    for a in ax:
        P.centre_ticklabels(fig, a)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    S.save_figure(fig, 'ED7_sobol', note='Reference, cumulative 2026–2050; Saltelli / Jansen estimators (scipy.stats.sobol_indices); 95% '
                                         'intervals by bootstrap of the Sobol samples; full profile only. Population '
                                         'and household size are one grouped input: both are drawn from one '
                                         'standard-normal score z (perfectly dependent), so their indices are grouped '
                                         'Sobol indices (Jacques, Lavergne & Devictor 2006).',
                  source=['montecarlo/sobol_REF.csv'])


SF12_HEADROOM = 1.25            # SF12: y top x this, so the legend sits above the 5th-95th bands


def sf12_pathway_mc():
    a = D.csv('pathways/montecarlo_annual.csv')
    s = D.csv('pathways/montecarlo_summary.csv')
    runs = [('REF', N.SCENARIOS['REF'], S.REFERENCE),                      # the run colours of Fig3 / Fig4
            ('pathway_moderate', N.PATHWAY_RUNS['pathway-moderate'], S.PATHWAY_SETTING['moderate']),
            ('pathway_ambitious', N.PATHWAY_RUNS['pathway-ambitious'], S.PATHWAY_SETTING['ambitious']),
            ('TL', N.TL['TL'], S.TL)]
    fig, ax = plt.subplots(figsize=S.figsize('double', 75))
    for r, lab, col in runs:
        t = a[a['run'] == r]
        yr = t['year'].to_numpy(float)
        xf, lo, hi, _ = P.pchip_band(yr, t['carbon_kt_p5'].to_numpy(float), t['carbon_kt_p50'].to_numpy(float),
                                     t['carbon_kt_p95'].to_numpy(float), P.series_breaks(), name=f'SF14 {r}')
        ax.fill_between(xf, lo, hi, color=col, alpha=S.OPACITY['mc_band'], lw=0)
        P.line(ax, yr, t['carbon_kt_p50'], color=col, lw=S.LW_BOLD, label=f'{lab} (median, 5th–95th percentile)')
    ax.set_xlim(2026, 2050)
    ax.set_ylim(0, ax.get_ylim()[1] * SF12_HEADROOM)                 # the legend above the bands (no overlap)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(fontsize=S.FONT_SMALL, frameon=False, loc='upper right', ncol=2)
    fig.tight_layout()
    p = s[(s['quantity'] == 'LoE_AR')].set_index('run')['probability_LoE_at_most_1']
    S.save_figure(fig, 'SF12_pathway_mc', note='P(cumulative LoE of AR <= 1): ' + ', '.join(
        f"{N.run_label(k.replace('_', '-'))} {v:.3f}" for k, v in p.items()) + '.', source=['pathways/montecarlo_annual.csv',
                                                            'pathways/montecarlo_summary.csv'])


FIGURES = {'ED6_mc_input_distributions': ed6_mc_input_distributions, 'ED7_sobol': ed7_sobol,
           'SF11_mc_convergence': sf11_mc_convergence, 'SF12_pathway_mc': sf12_pathway_mc}
