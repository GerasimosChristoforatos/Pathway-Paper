"""The Extended Data (outputs/paper_extended/; figure_plan.PAPER_EXTENDED and EXTENDED_TABLES), from the data files."""
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import figure_plan as FP
import layout
import levers as LV
import naming as N
from figures import data as D
from figures import draw as P
from figures import paper_main as PM
from figures import style as S

M = 1e6
SRC = {h['file']: h['source'] for h in FP.PAPER_EXTENDED}
LEVEL_STYLE = {'moderate': dict(ls='-', lw=S.LW_BOLD), 'ambitious': dict(ls=':', lw=S.LW)}


def _save(fig, name, note=None):
    S.save_figure(fig, name, note=note, source=SRC[name])


def ed1():
    d = D.src('D07_net_replacement_rate')
    c = d['census']
    fig, ax = plt.subplots(figsize=S.figsize('double', 70))
    for _, r in c.iterrows():
        ax.bar((r['y0'] + r['y1']) / 2, 100 * r['rate'], width=r['y1'] - r['y0'] - 0.3,
               color=S.BAND['replacement'][0], edgecolor=S.BAND['replacement'][0], lw=S.LW_SEAM)
    for k, st in S.SCENARIO.items():
        st = dict(st)
        lab = st.pop('label')
        ax.plot(d['years'], 100 * np.asarray(d['paths'][k]), label=lab, **st)
    ax.axhline(100 * d['demolition_rate'], color=S.MUTED, lw=S.LW_THIN, ls='--', label='Demolition (BRANZ SR214)')
    ax.axhline(100 * d['long_rate'], color=S.INK, lw=S.LW_THIN, ls=':', label='Long-run net rate 1991-2023')
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_ylabel('Net replacement (% of stock per year)')
    ax.legend(fontsize=S.FONT_MIN, ncol=2, loc='upper left')
    fig.tight_layout()
    _save(fig, 'ED1_census_replacement_rates', note='Bars: census-interval rates from dwelling counts (net of '
                                                    'unconsented additions); lines: the projection variants.')


def ed2():
    h = D.csv('baseline/household_formation_history.csv')
    d = D.src('D03_household_size')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    x = (h['year_start'] + h['year_end']) / 2
    w = h['year_end'] - h['year_start'] + 0.7
    a, b = h['from_population_growth_per_year'] / 1e3, h['from_household_size_change_per_year'] / 1e3
    ax[0].bar(x, a, width=w, color=S.GROWTH, label='From population growth')
    ax[0].bar(x, np.clip(b, 0, None), bottom=a, width=w, color=S.BAND['smaller_households'][0],
              label='From household-size change')
    neg = np.clip(b, None, 0)
    ax[0].bar(x, -neg, bottom=a + neg, width=w, facecolor='none', edgecolor=S.BAND['smaller_households'][0],
              lw=S.LW_OUTLINE, gid=P.NEG_BAR_GID)
    ax[0].plot(d['forecast_years'][1:], np.asarray(d['household_formation_50th'])[1:] / 1e3, color=S.INK,
               label='Projection (median)')
    ax[0].set_ylabel('New households per year (thousand)')
    ax[0].legend(fontsize=S.FONT_MIN)
    P.panel(ax[0], 'a', 'Household formation by source')
    hs = d['household_size_hist']
    ax[1].plot(hs.index, hs.values, color=S.INK, label='History')
    ax[1].plot(d['projection_years'], d['projection_household_size'], color=S.REFERENCE, lw=S.LW_BOLD, ls='--',
               label='Reference projection')
    ax[1].set_ylabel('Household size (persons per household)')
    ax[1].legend(fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Household size')
    fig.tight_layout()
    _save(fig, 'ED2_household_formation_size')


def ed3():
    d = D.src('projection_paths')
    f = d['df_forecast']
    fy = np.asarray(f['Year'])
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 65))
    panels = [('Population (million)', d['population_hist'], 'PopTotal', 1e6),
              ('Households (million)', d['households_hist'], 'households', 1e6),
              ('Floor area built, cumulative from 1991 (Mm²)', d['cumulative_floor_area_hist'], 'Cum_GFA_Total', 1e6)]
    for a, (lab, hist, key, sc), letter in zip(ax, panels, 'abc'):
        a.plot(hist.index, hist.values / sc, color=S.INK, label='History')
        get = (lambda p: np.asarray(d[f'households_{p}'])) if key == 'households' else (lambda p: np.asarray(f[f'{key}_{p}']))
        a.fill_between(fy, get('5th') / sc, get('95th') / sc, **S.MC_BAND, label='Population 5th-95th')
        a.plot(fy, get('50th') / sc, color=S.REFERENCE, lw=S.LW_BOLD, label='Reference (median)')
        P.split(a)
        a.set_ylabel(lab, fontsize=S.FONT_SMALL)
        P.panel(a, letter)
    ax[0].legend(fontsize=S.FONT_MIN)
    fig.tight_layout()
    _save(fig, 'ED3_cumulative_households_population_floor_area')


def ed4():
    dr = D.csv('pathways/montecarlo_draws.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 72), sharex=True)
    for a, q, letter in ((ax[0], 'LoE_AR', 'a'), (ax[1], 'LoE_AtP', 'b')):
        for r, col, lab in (('REF', S.REFERENCE, N.SCENARIOS['REF']), ('P5', S.PATHWAY['P5'], 'P5 Moderate'),
                            ('P5A', S.LEVER['L2'], 'P5 Ambitious'), ('TL', S.TL, N.TL['TL'])):
            a.scatter(dr['z_pop'], dr[f'{r}_{q}'], s=2, color=col, alpha=0.4, lw=0, label=lab)
        a.axhline(1.0, color=S.AR if q == 'LoE_AR' else S.ATP, lw=S.LW_BOUNDARY,
                  ls=S.BOUNDARY['AR' if q == 'LoE_AR' else 'AtP']['ls'], gid='boundary')
        a.set_yscale('log')
        a.set_xlabel('Population rank (z-score of the draw)')
        a.set_ylabel(f'Cumulative {q.replace("_", " ")} 2026-2050')
        P.panel(a, letter)
    ax[0].legend(fontsize=S.FONT_MIN, markerscale=4)
    fig.tight_layout()
    _save(fig, 'ED4_mc_scatter_population', note=f'{len(dr):,} Latin hypercube draws.')


def ed5():
    """MODEL v3.1.0 (B3): (a) P(TL within AR) by population-rank quintile Q1-Q5 (Wilson 95%); (b) the 2050 population
    at which P(TL LoE AR <= 1) = 50% (univariate logistic, bootstrap 95% interval) with the draws as a rug, or, when
    no draw (or every draw) has TL within AR, the TL LoE against the 2050 population. The Firth models stay in the
    data (pathways/montecarlo_conditional_tl.csv)."""
    j = D.js('pathways/montecarlo_conditional_tl.json')
    d = D.csv('pathways/montecarlo_draws.csv')
    thr = j['population_threshold']['adopted']
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 65))
    q = pd.DataFrame(j['by_population_quintile'])
    x = np.arange(len(q))
    ax[0].errorbar(x, q['p_within_AR'], yerr=[(q['p_within_AR'] - q['wilson_lo']).clip(lower=0),
                                              (q['wilson_hi'] - q['p_within_AR']).clip(lower=0)],
                   fmt='o', color=S.TL, capsize=2)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels([f'Q{int(k)}' for k in q['quintile']])
    ax[0].set_xlabel('Population-rank quintile (Q1 lowest)')
    ax[0].set_ylabel('P(TL cumulative LoE AR <= 1)')
    ax[0].set_ylim(-0.02, 1.02)
    P.panel(ax[0], 'a', 'By population quintile (Wilson 95%)')
    pop = d['P_NZ_2050'].to_numpy(float) / 1e6
    if thr['estimable']:
        cv = thr['curve']
        ax[1].plot(np.asarray(cv['P_NZ_2050']) / 1e6, cv['probability'], color=S.TL, lw=S.LW_BOLD)
        within = (d['TL_LoE_AR'].to_numpy(float) <= 1.0)
        ax[1].plot(pop[within], np.full(within.sum(), 1.02), '|', color=S.TL, ms=5, alpha=0.4)
        ax[1].plot(pop[~within], np.full((~within).sum(), -0.02), '|', color=S.MUTED, ms=5, alpha=0.4)
        lo, hi = thr['ci95']
        ax[1].axvspan(lo / 1e6, hi / 1e6, color=S.TL, alpha=0.12, lw=0)
        ax[1].axvline(thr['threshold_P_NZ_2050'] / 1e6, color=S.TL, lw=S.LW_THIN, ls='--')
        ax[1].axhline(0.5, color=S.INK, lw=S.LW_THIN, ls=':')
        ax[1].set_ylabel('P(TL cumulative LoE AR <= 1)')
        ax[1].set_ylim(-0.06, 1.06)
        note_b = (f"threshold {thr['threshold_P_NZ_2050'] / 1e6:.2f} M (95% CI {lo / 1e6:.2f}-{hi / 1e6:.2f} M; "
                  f"{thr['method']}, {thr['bootstrap_resamples']} resamples)")
        P.panel(ax[1], 'b', 'Population threshold (P = 50%)')
    else:
        ax[1].scatter(pop, d['TL_LoE_AR'], s=3, color=S.TL, alpha=0.35, lw=0)
        ax[1].axhline(1.0, **{k: val for k, val in S.BOUNDARY['AR'].items() if k != 'label'}, gid='boundary')
        ax[1].set_ylabel('TL cumulative LoE AR 2026-2050')
        ax[1].set_ylim(bottom=0)
        note_b = thr['note']
        P.panel(ax[1], 'b', 'TL LoE against the 2050 population (no threshold)')
    ax[1].set_xlabel('New Zealand population 2050 (million), Monte Carlo draws')
    fig.tight_layout()
    _save(fig, 'ED5_conditional_tl', note=f"P(within AR) = {j['p_within_AR']:.3f} (Wilson {j['wilson_95'][0]:.3f}-"
                                          f"{j['wilson_95'][1]:.3f}); (b) {note_b}.")


def ed6():
    r = D.csv('pathways/runs.csv')
    r = r[r['scenario'] == 'REF'].set_index('run')
    fig, ax = plt.subplots(figsize=S.figsize('double', 85))
    y = np.arange(len(LV.LEVERS))[::-1]
    for k, L in enumerate(LV.LEVERS):
        col = S.LEVER[L]
        for lev, off, st in (('moderate', 0.25, dict(facecolor='none', edgecolor=col, lw=S.LW_OUTLINE)),
                             ('ambitious', 0.0, dict(color=col, edgecolor=col, lw=S.LW_SEAM)),
                             ('tl', -0.25, dict(color=S.TL, edgecolor=S.TL, lw=S.LW_SEAM))):
            ax.barh(y[k] + off, r.loc[f'{L}-{lev}', 'delta_carbon_kt_vs_reference_pct'], height=0.24, **st)
    ax.set_yticks(y)
    ax.set_yticklabels([f'{L} {N.LEVERS[L]}' for L in LV.LEVERS])
    ax.axvline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_xlabel('Change of cumulative carbon 2026-2050 vs the Reference (%), lever alone')
    ax.legend(handles=[Patch(facecolor='none', edgecolor=S.MUTED, label='Moderate'), Patch(color=S.MUTED, label='Ambitious'),
                       Patch(color=S.TL, label='TL (Level 4)')], fontsize=S.FONT_SMALL, loc='lower left')
    fig.tight_layout()
    _save(fig, 'ED6_single_levers')


def ed7():
    PM.waterfall('ED7_waterfall_ambitious', 'ambitious')


def ed8():
    s = D.csv('pathways/shapley.csv')
    s = s[(s['game'] == 'tl_from_p5_moderate') & (s['metric'] == 'carbon_kt')].set_index('player')
    t = D.js('pathways/theoretical_limit.json')['runs']['TL']
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 72), gridspec_kw={'width_ratios': [1.4, 1, 1]})
    order = list(s['reduction'].sort_values().index)
    ax[0].barh(np.arange(len(order)), s.loc[order, 'reduction'], color=[S.LEVER[LV.TL_LEVER[k]] for k in order])
    ax[0].set_yticks(np.arange(len(order)))
    ax[0].set_yticklabels([f'{k} {N.TL[k]}' for k in order], fontsize=S.FONT_MIN + 0.5)
    ax[0].set_xlabel('Reduction from P5 Moderate (kt CO₂e; Shapley)')
    P.panel(ax[0], 'a', 'TL1-TL9 from P5 Moderate')
    yrs = sorted(int(y) for y in t['household_size_by_year'])
    ax[1].plot(yrs, [t['m2_per_person_new_dwellings'][str(y)] for y in yrs], color=S.TL)
    ax[1].set_ylabel('m² per person, new dwellings')
    P.panel(ax[1], 'b', 'Space per person')
    ax[2].plot(yrs, [100 * t['implied_vacancy'][str(y)] for y in yrs], color=S.TL)
    ax[2].set_ylabel('Implied vacancy (%)')
    P.panel(ax[2], 'c', 'Implied vacancy')
    ax[2].text(0.02, 0.02, 'Vacancy parameter -> 0 by 2035; physical vacancy falls\nas released stock is re-occupied over '
               '2027-2050', transform=ax[2].transAxes, fontsize=S.FONT_MIN, color=S.MUTED, va='bottom')
    fig.tight_layout()
    _save(fig, 'ED8_tl_shapley_indicators', note=f"TL re-occupies {t['reoccupied']:,.0f} released dwellings "
                                                 f"(attributed TL3 {t['reoccupied_attributed']['TL3']:,.0f}, TL4 "
                                                 f"{t['reoccupied_attributed']['TL4']:,.0f}, in proportion R3:R4). (c) The "
                                                 "vacancy parameter falls to 0 by 2035 (TL4); the physical (implied) "
                                                 "vacancy falls as the released stock is re-occupied over 2027-2050.")


def ed9():
    a = D.csv('pathways/annual.csv')
    a = a[a['scenario'] == 'REF']
    ref = a[a['run'] == 'REF'].set_index('year')
    yrs = ref.index.values.astype(float)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 75), sharey=True)
    for b, s, letter in ((ax[0], 'moderate', 'a'), (ax[1], 'ambitious', 'b')):
        S.boundary_zones(b, yrs, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
        b.plot(yrs, ref['carbon_kt'], color=S.REFERENCE, lw=S.LW_BOLD, label=N.SCENARIOS['REF'])
        for suffix, ls, lab in (('-by2030', ':', 'by 2030'), ('', '-', 'by 2035 (adopted)'), ('-by2045', '--', 'by 2045')):
            r = a[a['run'] == f'P5-{s}{suffix}'].set_index('year')
            b.plot(yrs, r['carbon_kt'], color=S.PATHWAY['P5'], ls=ls, lw=S.LW, label=f'P5, full roll-out {lab}')
        b.set_xlim(yrs[0], yrs[-1])
        b.set_ylim(0, None)
        P.panel(b, letter, f'P5 {N.SETTINGS[s]}')
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[0].legend(fontsize=S.FONT_MIN)
    fig.tight_layout()
    _save(fig, 'ED9_rollout_timing')


def ed10():
    sw = D.csv('pathways/lambda_sweep.csv')
    fig, ax = plt.subplots(figsize=S.figsize('double', 85))
    for L in LV.LEVERS:
        t = sw[(sw['lever'] == L) & sw['lam'].notna()].sort_values('lam')
        ax.plot(t['lam'], t['carbon_kt'], color=S.LEVER[L], lw=S.LW, marker='o', ms=2, label=f'{L} {N.LEVERS[L]}')
        tl = sw[(sw['lever'] == L) & sw['lam'].isna()]
        ax.plot([1.15], tl['carbon_kt'], marker='o', color=S.LEVER[L], markeredgecolor=S.TL, ms=6)
    for x, lab in ((0, 'Reference'), (0.5, 'Moderate'), (1.0, 'Ambitious'), (1.15, 'TL')):
        ax.axvline(x, color=S.MUTED, lw=S.LW_THIN, ls=':')
        ax.text(x, 1.0, lab, transform=ax.get_xaxis_transform(), ha='center', va='bottom', fontsize=S.FONT_MIN)
    ax.set_xlabel('λ: the native parameter from the Reference (0) to Ambitious (1); TL at the right')
    ax.set_ylabel('Cumulative carbon 2026-2050 (kt CO₂e), lever alone')
    P.thousands(ax.yaxis)
    ax.legend(fontsize=S.FONT_MIN, ncol=3, loc='lower left')
    fig.tight_layout()
    _save(fig, 'ED10_lambda_sweep', note='L9 at λ = 0 is the lever off; a small step to λ > 0 reflects the constant '
                                         's_ref against the year-varying replacement share.')


def ed11():
    p = D.js('pathways/levers.json')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 70))
    for a, L, key, letter in ((ax[0], 'L2', 'ratio', 'a'), (ax[1], 'L6', 'ratio', 'b')):
        q = p[L]
        cases = pd.DataFrame(q['cases']).sort_values(key)
        typ = cases['Typology'] if 'Typology' in cases else cases['typology']
        y = np.arange(len(cases))
        cols = {'Detached': S.LEVER['L1'], 'Townhouses': S.LEVER['L6'], 'Apartments': S.LEVER['L4']}
        a.scatter(cases[key], y, c=[cols[t] for t in typ], s=14, zorder=3)
        e = q['estimator']
        a.axvspan(e['ci_lo'], e['ci_hi'], color=S.MUTED, alpha=0.15, lw=0, label='95% bootstrap interval')
        a.axvline(e['r'], color=S.INK, lw=S.LW, label=f"Ambitious r = {e['r']:.3f} (HD q0.15)")
        a.axvline(q['r']['moderate'], color=S.INK, lw=S.LW_THIN, ls='--', label=f"Moderate r = {q['r']['moderate']:.3f}")
        a.axvline(1.0, color=S.MUTED, lw=S.LW_THIN, ls=':')
        a.set_yticks(y)
        a.set_yticklabels(cases['id'], fontsize=S.FONT_MIN)
        a.set_xlabel('Case ratio (scale-free)')
        a.legend(fontsize=S.FONT_MIN, loc='lower right')
        P.panel(a, letter, f"{L} {N.LEVERS[L]} (n = {q['n']}, B = {e['bootstrap']['B']})")
    fig.tight_layout()
    c15 = p['L6'].get('check_with_A_1')
    _save(fig, 'ED11_hd_estimators',
          note=('L6 excludes the apartment case A_1: it is the one independent apartment case (A_2 its duplicate), so '
                'its ratio to the apartment pooled value is ~1 by construction'
                + (f" ({c15['A_1_ratio']:.4f}); with A_1 (n = {c15['n']}) r = {c15['r']:.3f} (95% CI "
                   f"{c15['ci_lo']:.3f}-{c15['ci_hi']:.3f}) against the adopted r = {c15['adopted_r']:.3f} "
                   f"(n = {c15['adopted_n']}; check only)" if c15 else '') + '.'))


def ed12():
    p = D.js('pathways/levers.json')['L1']
    fig, ax = plt.subplots(figsize=S.figsize('double', 70))
    cols = {'Detached': S.LEVER['L1'], 'Townhouses': S.LEVER['L6'], 'Apartments': S.LEVER['L4']}
    for t, ser in p['consent_size_series'].items():
        yrs = sorted(int(y) for y in ser)
        ax.plot(yrs, [ser[str(y)] for y in yrs], color=cols[t], label=t)
        m = p['minima'][t]
        ax.plot([m['year']], [m['size_min']], 'o', color=cols[t], ms=5)
        ax.annotate(f"min {m['size_min']:.1f} m² ({m['year']})", (m['year'], m['size_min']), xytext=(4, -10),
                    textcoords='offset points', fontsize=S.FONT_MIN, color=cols[t])
        ax.axhline(p['size_ref'][t], color=cols[t], lw=S.LW_THIN, ls=':')
    ax.set_ylabel('Mean consented new-dwelling size (m²)')
    ax.legend(fontsize=S.FONT_SMALL)
    fig.tight_layout()
    _save(fig, 'ED12_consent_sizes', note='Dotted: the Reference size (2023-2025 mean). 1990 is the first year of the '
                                          'series and a recession year.')


def ed13():
    a = D.csv('pathways/annual.csv')
    v = D.csv('sensitivity/replacement_variants.csv')
    ref = a[(a['scenario'] == 'REF') & (a['run'] == 'REF')].set_index('year')
    yrs = ref.index.values.astype(float)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 75), gridspec_kw={'width_ratios': [1.6, 1]})
    S.boundary_zones(ax[0], yrs, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
    for scen, ls in (('LOW', '--'), ('REF', '-'), ('HIGH', ':')):
        for run, col in ((scen, S.REFERENCE), ('P5-moderate', S.PATHWAY['P5']), ('TL', S.TL)):
            r = a[(a['scenario'] == scen) & (a['run'] == run)].set_index('year')
            ax[0].plot(yrs, r['carbon_kt'], color=col, ls=ls, lw=S.LW)
    ax[0].set_xlim(yrs[0], yrs[-1])
    ax[0].set_ylim(0, None)
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[0].legend(handles=[Line2D([0], [0], color=S.REFERENCE, label='Reference / variant'),
                          Line2D([0], [0], color=S.PATHWAY['P5'], label='P5 Moderate'),
                          Line2D([0], [0], color=S.TL, label=N.TL['TL'])] +
                 [Line2D([0], [0], color=S.MUTED, ls=ls, label=N.SCENARIOS[k]) for k, ls in
                  (('LOW', '--'), ('REF', '-'), ('HIGH', ':'))], fontsize=S.FONT_MIN)
    P.panel(ax[0], 'a', 'Annual')
    piv = v.pivot(index='run', columns='scenario', values='LoE_AR').loc[['Reference', 'P5-moderate', 'P5-ambitious', 'TL']]
    x = np.arange(len(piv))
    for j, scen in enumerate(('LOW', 'REF', 'HIGH')):
        ax[1].bar(x + (j - 1) * 0.25, piv[scen], width=0.25, color=S.SCENARIO[scen]['color'], label=N.SCENARIOS[scen])
    ax[1].axhline(1, **{k: val for k, val in S.BOUNDARY['AR'].items() if k != 'label'}, gid='boundary')
    S.boundary_hzones(ax[1], 1.0, float(ref['B_AtP_kt'].sum() / ref['B_AR_kt'].sum()), lines=False)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(piv.index, rotation=30, ha='right', fontsize=S.FONT_MIN + 0.5)
    ax[1].set_ylabel('Cumulative LoE AR 2026-2050')
    ax[1].legend(fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Cumulative')
    fig.tight_layout()
    _save(fig, 'ED13_replacement_variants')


def ed14():
    lg = D.csv('baseline/overbuild_absorption_log.csv')
    sa = D.csv('baseline/sensitivity_annual_carbon.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    yr = lg['year']
    ax[0].plot(yr, lg['surplus_vacant'] / 1e3, color=S.BAND['overbuild_2026'][0], lw=S.LW_BOLD,
               label='Surplus still vacant U(t)')
    ax[0].plot(yr, lg['cumulative_excess'] / 1e3, color=S.BAND['overbuild_2026'][0], ls=':', label='Cumulative excess C(t)')
    ax[0].bar(yr, -lg['payback_paid'] / 1e3, color='none', edgecolor=S.BAND['overbuild_absorbed'][0], lw=S.LW_OUTLINE,
              gid=P.NEG_BAR_GID, label='Payback (built less), per year')
    b2 = ax[0].twinx()
    b2.plot(yr, 100 * lg['implied_vacancy'], color=S.INK, lw=S.LW_THIN, ls='--', label='Implied vacancy (right)')
    b2.set_ylabel('Implied vacancy (%)')
    b2.grid(False)
    ax[0].axhline(0, color=S.INK, lw=S.LW_THIN)
    ax[0].set_ylabel('Dwellings (thousand)')
    h = ax[0].get_legend_handles_labels()[0] + b2.get_legend_handles_labels()[0]
    ax[0].legend(handles=h, fontsize=S.FONT_MIN, loc='center right')
    P.panel(ax[0], 'a', 'Reference: absorbed by 2035')
    cases = [('Reference (adopted settings)', S.REFERENCE, '-', 'by 2035 (adopted)'),
             ('Overbuild absorbed by 2030', S.P2_ANCHOR, ':', 'by 2030'),
             ('Overbuild absorbed by 2045', S.P2_ANCHOR, '--', 'by 2045'),
             ('Overbuild never absorbed (MODEL v2.1 Reference)', S.MUTED, '-', 'never (MODEL v2.1)')]
    for case, col, ls, lab in cases:
        t = sa[sa['case'] == case]
        ax[1].plot(t['year'], t['carbon_kt'], color=col, ls=ls, lw=S.LW, label=f'{lab}: {t["carbon_kt"].sum():,.0f} kt')
    ax[1].set_xlim(2026, 2050)
    ax[1].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[1].legend(fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Absorption timing (2026-2050 totals)')
    fig.tight_layout()
    _save(fig, 'ED14_overbuild_absorption', note='Theory fixes the direction (reversion to the equilibrium vacancy), '
                                                 'not the speed; 2035 is the common RECC window; speed bracketed.')


def edt1():
    """EDT1: each lever's native parameter by typology at Moderate, Ambitious and TL (Markdown + CSV)."""
    p = D.js('pathways/levers.json')
    typ = list(p['L1']['size_ref'])
    rows = []
    for L in LV.LEVERS:
        for t in typ:
            q = p[L]
            if L == 'L1':
                v = [q['f']['moderate'][t], q['f']['ambitious'][t], q['tl'][t]]
                par = 'f (share of the extra-space margin removed)'
            elif L in ('L2', 'L6'):
                v = [q['r']['moderate'], q['r']['ambitious'], q['tl'][t]]
                par = 'r (ratio to the Reference)'
            elif L == 'L8':
                s0 = q['soil_factor_2025'][t]
                v = [s0 * (1 - q['x']['moderate']), s0 * (1 - q['x']['ambitious']), q['tl'][t]]
                par = 'soil carbon loss (kg CO2e/m2 floor area)'
            elif L == 'L3':
                v = [q['S']['moderate']['2050'], q['S']['ambitious']['2050'], q['tl']]
                par = 'household size 2050 (all typologies)'
            elif L == 'L4':
                v = [q['v']['moderate'], q['v']['ambitious'], q['tl']]
                par = 'vacancy rate (all typologies)'
            elif L == 'L5':
                v = [q['d']['moderate'], q['d']['ambitious'], 1.0]
                par = 'd, reduction of demolition and surge (all typologies)'
            elif L == 'L7':
                v = [q['target']['moderate']['2050'], q['target']['ambitious']['2050'], 0.0]
                par = 'A4-A5 factor 2050 (all typologies)'
            else:
                v = [q['s']['moderate'], q['s']['ambitious'], q['tl']]
                par = 's, brownfield share (all typologies)'
            rows.append(dict(lever=f'{L} {N.LEVERS[L]}', subrule=q['subrule'], typology=t, parameter=par,
                             moderate=v[0], ambitious=v[1], tl=v[2]))
    df = pd.DataFrame(rows)
    out = os.path.join(layout.PAPER_EXTENDED, 'EDT1_levels_by_typology')
    os.makedirs(layout.PAPER_EXTENDED, exist_ok=True)
    df.to_csv(out + '.csv', index=False)
    L_ = ['# EDT1 Lever levels by typology: Moderate (Level 2), Ambitious (Level 3), TL (Level 4)', '',
          '| Lever | Sub-rule | Typology | Parameter | Moderate | Ambitious | TL |', '|---|---|---|---|---|---|---|']
    L_ += [f"| {r.lever} | {r.subrule} | {r.typology} | {r.parameter} | {r.moderate:.4g} | {r.ambitious:.4g} | "
           f"{r.tl:.4g} |" for r in df.itertuples()]
    with open(out + '.md', 'w') as f:
        f.write('\n'.join(L_) + '\n')


FIGURES = {'ED1_census_replacement_rates': ed1, 'ED2_household_formation_size': ed2,
           'ED3_cumulative_households_population_floor_area': ed3, 'ED4_mc_scatter_population': ed4,
           'ED5_conditional_tl': ed5, 'ED6_single_levers': ed6, 'ED7_waterfall_ambitious': ed7,
           'ED8_tl_shapley_indicators': ed8, 'ED9_rollout_timing': ed9, 'ED10_lambda_sweep': ed10,
           'ED11_hd_estimators': ed11, 'ED12_consent_sizes': ed12, 'ED13_replacement_variants': ed13,
           'ED14_overbuild_absorption': ed14}
TABLES = {'EDT1_levels_by_typology': edt1}
