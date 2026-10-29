"""The Extended Data (outputs/paper_extended/; figure_plan.PAPER_EXTENDED and EXTENDED_TABLES) and the supplementary
figures (outputs/supplementary/; figure_plan.SUPPLEMENTARY; at most ten Extended Data items), from the
data files."""
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
from figures import style as S

M = 1e6
SRC = {h['file']: h['source'] for h in FP.PAPER_EXTENDED + FP.SUPPLEMENTARY}


def _save(fig, name, note=None):
    S.save_figure(fig, name, note=note, source=SRC[name])


def ed2():
    d = D.src('D07_net_replacement_rate')
    c = d['census']
    fig, ax = plt.subplots(figsize=S.figsize('double', 70))
    for _, r in c.iterrows():
        ax.bar((r['y0'] + r['y1']) / 2, 100 * r['rate'], width=r['y1'] - r['y0'] - 0.3,
               color=S.DISPLAY_BAND['net_replacement'], edgecolor=S.DISPLAY_BAND['net_replacement'], lw=S.LW_SEAM)
    for k, st in S.SCENARIO.items():
        st = dict(st)
        lab = st.pop('label')
        P.line(ax, d['years'], 100 * np.asarray(d['paths'][k]), label=lab, **st)
    ax.axhline(100 * d['demolition_rate'], color=S.MUTED, lw=S.LW_THIN, ls='--', label='Demolition (BRANZ SR214)')
    ax.axhline(100 * d['long_rate'], color=S.INK, lw=S.LW_THIN, ls=':', label='Long-run net rate 1991–2023')
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_ylabel('Net replacement (% of stock per year)')
    ax.legend(fontsize=S.FONT_MIN, ncol=2, loc='upper left')
    fig.tight_layout()
    _save(fig, 'SF3_census_replacement_rates', note='Bars: census-interval rates from dwelling counts (net of '
                                                    'unconsented additions); lines: the projection variants.')


# the projection in the Reference colour (a boundary colour is never used for a run)
PROJECTION_LINE = S.REFERENCE


def ed1():
    """3 x 1: population, households and cumulative floor area: history (black),
    the Reference projection (median, dark red) and the band of the Stats NZ population 5th-95th percentile paths (the
    data of figure_source/projection_paths.json; not a Monte Carlo band: the population percentiles are those of the
    Stats NZ projection run through the model). The households panel notes the rebasing of the Stats NZ dwelling and
    household estimates on the 2023 census."""
    d = D.src('projection_paths')
    hh = D.src('D02_households')
    f = d['df_forecast']
    fy = np.asarray(f['Year'])
    fig, ax = plt.subplots(3, 1, figsize=S.figsize('double', 150), sharex=True)
    panels = [('Population (million)', d['population_hist'], 'PopTotal', 1e6),
              ('Households (million)', d['households_hist'], 'households', 1e6),
              ('Floor area built, cumulative from 1991 (Mm²)', d['cumulative_floor_area_hist'], 'Cum_GFA_Total', 1e6)]
    for a, (lab, hist, key, sc), letter in zip(ax, panels, 'abc'):
        P.line(a, hist.index, hist.values / sc, color=S.INK, lw=S.LW, label='History')
        get = ((lambda p: np.asarray(d[f'households_{p}'])) if key == 'households'
               else (lambda p, key=key: np.asarray(f[f'{key}_{p}'])))
        xf, lo_, hi_, _ = P.pchip_band(fy.astype(float), get('5th') / sc, get('50th') / sc, get('95th') / sc,
                                       P.series_breaks(), name=f'ED1 {key}')
        a.fill_between(xf, lo_, hi_, **S.MC_BAND, label='Stats NZ population 5th–95th percentile')
        P.line(a, fy, get('50th') / sc, color=PROJECTION_LINE, lw=S.LW_BOLD, label='Reference projection (median)')
        P.split(a)
        a.set_ylabel(lab, fontsize=S.FONT_SMALL)
        P.panel(a, letter)
    ax[1].text(0.01, 0.97, f"History rebased on the {hh['S_ANCHOR_YEAR']} census (occupied + residents-away private "
               f"dwellings): Stats NZ household increments after 2018 × {hh['hh_rebase_k']:.3f}",
               transform=ax[1].transAxes, ha='left', va='top', fontsize=S.FONT_MIN, color=S.MUTED)
    ax[0].legend(fontsize=S.FONT_MIN, loc='lower right')
    ax[-1].set_xlabel('Year')
    fig.tight_layout()
    _save(fig, 'ED1_population_households_floor_area',
          note=f"Band: the Stats NZ population 5th-95th percentile paths run through the model (not the Monte Carlo). "
               f"Households rebased on the {hh['S_ANCHOR_YEAR']} census (k = {hh['hh_rebase_k']:.4f}).")


def ed3():
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
    P.line(ax[0], d['forecast_years'][1:], np.asarray(d['household_formation_50th'])[1:] / 1e3, color=S.INK,
               label='Projection (median)')
    ax[0].set_ylabel('New households per year (thousand)')
    h0, _ = ax[0].get_legend_handles_labels()         # the negative part in the legend
    h0.append(Patch(facecolor='none', edgecolor=S.BAND['smaller_households'][0], lw=S.LW_OUTLINE,
                    label='From household-size change, negative (households consolidating; outline)'))
    ax[0].legend(handles=h0, fontsize=S.FONT_MIN, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2,
                 frameon=False)
    P.panel(ax[0], 'a', 'Household formation by source')
    hs = d['household_size_hist']
    P.line(ax[1], hs.index, hs.values, color=S.INK, label='History')
    P.line(ax[1], d['projection_years'], d['projection_household_size'], color=S.REFERENCE, lw=S.LW_BOLD, ls='--',
               label='Reference projection')
    ax[1].set_ylabel('Household size (persons per household)')
    ax[1].legend(fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Household size')
    fig.tight_layout()
    _save(fig, 'ED2_household_formation_size')


def sf2():
    """(a) P(TL within AR) by population-rank quintile Q1-Q5 (Wilson 95%); (b) the 2050 population
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
    ax[0].set_ylabel('P(cumulative LoE of AR ≤ 1), Theoretical Limit')
    ax[0].set_ylim(-0.02, 1.02)
    P.panel(ax[0], 'a', 'By population quintile (Wilson 95%)')
    pop = d['P_NZ_2050'].to_numpy(float) / 1e6
    if thr['estimable']:
        cv = thr['curve']
        ax[1].plot(np.asarray(cv['P_NZ_2050']) / 1e6, cv['probability'], color=S.TL, lw=S.LW_BOLD)
        within = (d['TL_LoE_AR'].to_numpy(float) <= 1.0)
        ax[1].plot(pop[within], np.full(within.sum(), 1.02), '|', color=S.TL, ms=5, alpha=S.FIXED_FADES['rug'])
        ax[1].plot(pop[~within], np.full((~within).sum(), -0.02), '|', color=S.MUTED, ms=5, alpha=S.FIXED_FADES['rug'])
        lo, hi = thr['ci95']
        ax[1].axvspan(lo / 1e6, hi / 1e6, color=S.TL, alpha=S.FIXED_FADES['threshold_ci_span'], lw=0)
        ax[1].axvline(thr['threshold_P_NZ_2050'] / 1e6, color=S.TL, lw=S.LW_THIN, ls='--')
        ax[1].axhline(0.5, color=S.INK, lw=S.LW_THIN, ls=':')
        ax[1].set_ylabel('P(cumulative LoE of AR ≤ 1), Theoretical Limit')
        ax[1].set_ylim(-0.06, 1.06)
        note_b = (f"threshold {thr['threshold_P_NZ_2050'] / 1e6:.2f} M (95% CI {lo / 1e6:.2f}-{hi / 1e6:.2f} M; "
                  f"{thr['method']}, {thr['bootstrap_resamples']} resamples)")
        P.panel(ax[1], 'b', 'Population threshold (P = 50%)')
    else:
        ax[1].scatter(pop, d['TL_LoE_AR'], s=3, color=S.TL, alpha=S.OPACITY['scatter_tl'], lw=0)
        ax[1].axhline(1.0, **{k: val for k, val in S.BOUNDARY['AR'].items() if k != 'label'}, gid='boundary')
        ax[1].set_ylabel(f'{N.LOE_AR} 2026–2050, Theoretical Limit')
        ax[1].set_ylim(bottom=0)
        note_b = thr['note']
        P.panel(ax[1], 'b', 'TL LoE against the 2050 population (no threshold)')
    ax[1].set_xlabel('New Zealand population 2050 (million), Monte Carlo draws')
    fig.tight_layout()
    _save(fig, 'SF14_conditional_tl', note=f"P(within AR) = {j['p_within_AR']:.3f} (Wilson {j['wilson_95'][0]:.3f}-"
                                          f"{j['wilson_95'][1]:.3f}); (b) {note_b}.")


def ed10():
    """Roll-out timing (ED9): (a, b) annual carbon of the Moderate / Ambitious Pathway
    with full roll-out by 2030, 2035 (adopted) and 2045; (c) their cumulative carbon 2026-2050 as the
    running sum (same colours and line styles), the Reference cumulative a grey line (pathways/annual.csv; the 2050
    end values equal runs.csv carbon_kt, checked)."""
    a = D.csv('pathways/annual.csv')
    a = a[a['scenario'] == 'REF']
    ref = a[a['run'] == 'REF'].set_index('year')
    yrs = ref.index.values.astype(float)
    runs = D.csv('pathways/runs.csv')
    runs = runs[runs['scenario'] == 'REF'].set_index('run')['carbon_kt']
    VARIANTS = (('-by2030', ':', 'by 2030'), ('', '-', 'by 2035 (adopted)'), ('-by2045', '--', 'by 2045'))
    fig = plt.figure(figsize=S.figsize('double', 75))
    outer = fig.add_gridspec(1, 2, width_ratios=[2.1, 0.95], wspace=0.26)    # (c) has its own axis: more space
    gs = outer[0].subgridspec(1, 2, wspace=0.08)
    ax = [fig.add_subplot(gs[0])]
    ax.append(fig.add_subplot(gs[1], sharey=ax[0]))
    for b, s, letter in ((ax[0], 'moderate', 'a'), (ax[1], 'ambitious', 'b')):
        S.boundary_zones(b, yrs, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
        P.line(b, yrs, ref['carbon_kt'], color=S.REFERENCE, lw=S.LW_BOLD, label=N.SCENARIOS['REF'])
        for suffix, ls, lab in VARIANTS:
            r = a[a['run'] == f'{N.PATHWAY}-{s}{suffix}'].set_index('year')
            P.line(b, yrs, r['carbon_kt'], color=S.PATHWAY_SETTING[s], ls=ls, lw=S.LW)   # run colour
        b.set_xlim(yrs[0], yrs[-1])
        b.set_ylim(0, None)
        P.panel(b, letter, N.PATHWAY_RUNS[f'{N.PATHWAY}-{s}'])
    plt.setp(ax[1].get_yticklabels(), visible=False)
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    h0, _ = ax[0].get_legend_handles_labels()                       # AR, AtP, Reference; the roll-out styles in grey
    ax[0].legend(handles=h0 + [Line2D([0], [0], color=S.MUTED, ls=ls, lw=S.LW, label=f'Pathway, full roll-out {lab}')
                               for _, ls, lab in VARIANTS], fontsize=S.FONT_MIN)
    # (c) cumulative 2026-2050 (running sum from 2026)
    c = fig.add_subplot(outer[1])
    m = yrs >= 2026
    cref = np.cumsum(ref['carbon_kt'].values[m])
    assert np.isclose(cref[-1], runs['REF'], rtol=1e-9)
    P.line(c, yrs[m], cref, color=S.REFERENCE, lw=S.LW_BOLD, alpha=S.OPACITY['rollout_reference_cumulative'], label=N.SCENARIOS['REF'])
    ends = []
    for s in ('moderate', 'ambitious'):
        for suffix, ls, lab in VARIANTS:
            run = f'{N.PATHWAY}-{s}{suffix}'
            cum = np.cumsum(a[a['run'] == run].set_index('year').loc[yrs[m].astype(int), 'carbon_kt'].values)
            assert np.isclose(cum[-1], runs[run], rtol=1e-9), run
            P.line(c, yrs[m], cum, color=S.PATHWAY_SETTING[s], ls=ls, lw=S.LW)
            ends.append((run, float(cum[-1])))
        lo_, hi_ = min(v for r_, v in ends[-3:]), max(v for r_, v in ends[-3:])
        c.text(yrs[m][-1] + 0.4, (lo_ + hi_) / 2, N.PATHWAY_RUNS[f'{N.PATHWAY}-{s}'].replace(' ', '\n'), ha='left',
               va='center', fontsize=S.FONT_MIN, color=S.INK, linespacing=1.0, multialignment='center')
    c.text(yrs[m][-1] + 0.4, cref[-1], N.SCENARIOS['REF'], ha='left', va='center', fontsize=S.FONT_MIN,
           color=S.INK)
    c.set_xlim(yrs[m][0], yrs[m][-1])
    c.set_ylim(0, None)
    c.set_ylabel('Cumulative carbon 2026–2050 (kt CO₂e)')
    P.thousands(c.yaxis)
    P.panel(c, 'c', 'Cumulative')
    fig.subplots_adjust(left=0.07, right=0.91, bottom=0.11, top=0.92)
    _save(fig, 'ED9_rollout_timing', note='(c) Cumulative 2026-2050 (kt): ' + ', '.join(
        f'{N.run_label(r_)} {v:,.0f}' for r_, v in ends) + f'; Reference {cref[-1]:,.0f}.')


def sf3():
    sw = D.csv('pathways/lambda_sweep.csv')
    fig, ax = plt.subplots(figsize=S.figsize('double', 85))
    # each lever in its strategy colour (palette.toml [strategies]), told
    # apart by marker within its strategy (S.LEVER_MARKER); the legend has one column per strategy, headed by its name
    handles = {}
    for L in LV.LEVERS:
        sid = N.LEVER_STRATEGY[L]
        col, mk = S.STRATEGY[sid], S.LEVER_MARKER[N.STRATEGY_LEVERS[sid].index(L)]
        t = sw[(sw['lever'] == L) & sw['lam'].notna()].sort_values('lam')
        handles[L], = ax.plot(t['lam'], t['carbon_kt'], color=col, lw=S.LW, marker=mk, ms=2.6,
                              markerfacecolor=col, markeredgewidth=0, label=f'{L} {N.LEVERS[L]}')
        tl = sw[(sw['lever'] == L) & sw['lam'].isna()]
        ax.plot([1.15], tl['carbon_kt'], marker=mk, color=col, markeredgecolor=S.TL, markeredgewidth=0.9, ms=6, ls='none')
    rows = max(len(v) for v in N.STRATEGY_LEVERS.values()) + 1
    blank = Line2D([], [], ls='none', marker='none')
    leg_h, leg_l = [], []
    for sid, ls_ in N.STRATEGY_LEVERS.items():
        col_h = [(blank, N.STRATEGIES[sid])] + [(handles[L], f'{L} {N.LEVERS[L]}') for L in ls_]
        col_h += [(blank, '')] * (rows - len(col_h))
        leg_h += [h for h, _ in col_h]
        leg_l += [lab for _, lab in col_h]
    for x, lab in ((0, N.SCENARIOS['REF']), (0.5, 'Moderate'), (1.0, 'Ambitious'), (1.15, N.TL['TL'])):
        ax.axvline(x, color=S.MUTED, lw=S.LW_THIN, ls=':')
        ax.text(x, 1.0, lab, transform=ax.get_xaxis_transform(), ha='center', va='bottom', fontsize=S.FONT_MIN)
    ax.set_xlabel('λ: each lever from the Reference (0) to Ambitious (1); its Theoretical Limit at the right')
    ax.set_ylabel('Cumulative carbon 2026–2050 (kt CO₂e), lever alone')
    P.thousands(ax.yaxis)
    leg = ax.legend(leg_h, leg_l, fontsize=S.FONT_MIN, ncol=len(N.STRATEGY_LEVERS), loc='lower left', handlelength=2.2)
    for t_ in leg.get_texts():
        if t_.get_text() in N.STRATEGIES.values():
            t_.set_fontweight('bold')
    fig.tight_layout()
    _save(fig, 'SF10_lambda_sweep', note='L6 at λ = 0 is the lever off; a small step to λ > 0 reflects the constant '
                                         's_ref against the year-varying replacement share.')


def sf4():
    p = D.js('pathways/levers.json')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 70))
    for a, L, key, letter in ((ax[0], 'L5', 'ratio', 'a'), (ax[1], 'L8', 'ratio', 'b')):
        q = p[L]
        cases = pd.DataFrame(q['cases']).sort_values(key)
        typ = cases['Typology'] if 'Typology' in cases else cases['typology']
        y = np.arange(len(cases))
        a.scatter(cases[key], y, c=[S.TYPOLOGY[t] for t in typ], s=14, zorder=3)
        e = q['estimator']
        a.axvspan(e['ci_lo'], e['ci_hi'], color=S.MUTED, alpha=S.FIXED_FADES['ci_span'], lw=0, label='95% bootstrap interval')
        a.axvline(e['r'], color=S.INK, lw=S.LW, label=f"Ambitious r = {e['r']:.3f} (HD q0.15)")
        a.axvline(q['r']['moderate'], color=S.INK, lw=S.LW_THIN, ls='--', label=f"Moderate r = {q['r']['moderate']:.3f}")
        a.axvline(1.0, color=S.MUTED, lw=S.LW_THIN, ls=':')
        a.set_yticks(y)
        a.set_yticklabels(cases['id'], fontsize=S.FONT_MIN)
        a.set_xlabel('Case ratio (scale-free)')
        h_ = a.get_legend_handles_labels()[0] + [                  # the typology colours explained
            Line2D([0], [0], ls='none', marker='o', ms=4, color=S.TYPOLOGY[t], label=t) for t in S.TYPOLOGY]
        a.legend(handles=h_, fontsize=S.FONT_MIN, loc='lower right')
        P.panel(a, letter, f"{L} {N.LEVERS[L]} (n = {q['n']}, B = {e['bootstrap']['B']})")
    fig.tight_layout()
    c15 = p['L8'].get('check_with_A_1')
    _save(fig, 'SF11_hd_estimators',
          note=('L8 excludes the apartment case A_1: it is the one independent apartment case (A_2 its duplicate), so '
                'its ratio to the apartment pooled value is ~1 by construction'
                + (f" ({c15['A_1_ratio']:.4f}); with A_1 (n = {c15['n']}) r = {c15['r']:.3f} (95% CI "
                   f"{c15['ci_lo']:.3f}-{c15['ci_hi']:.3f}) against the adopted r = {c15['adopted_r']:.3f} "
                   f"(n = {c15['adopted_n']}; check only)" if c15 else '') + '.'))


VARIANT_LS = (('LOW', '--'), ('REF', '-'), ('HIGH', ':'), ('VHIGH', '-.'))     # + Very High


def _variant_label(k):
    # the Reference replacement variant is named apart from the Reference run (legend of ED3a)
    return 'Reference replacement' if k == 'REF' else N.SCENARIOS[k]


def ed9():
    a = D.csv('pathways/annual.csv')
    v = D.csv('sensitivity/replacement_variants.csv')
    ref = a[(a['scenario'] == 'REF') & (a['run'] == 'REF')].set_index('year')
    yrs = ref.index.values.astype(float)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 75), gridspec_kw={'width_ratios': [1.6, 1]})
    S.boundary_zones(ax[0], yrs, ref['B_AR_kt'].values, ref['B_AtP_kt'].values)
    for scen, ls in VARIANT_LS:
        for run, col in ((scen, S.REFERENCE), ('pathway-moderate', S.PATHWAY_SETTING['moderate']),
                         ('pathway-ambitious', S.PATHWAY_SETTING['ambitious']), ('TL', S.TL)):   # + Ambitious
            r = a[(a['scenario'] == scen) & (a['run'] == run)].set_index('year')
            P.line(ax[0], yrs, r['carbon_kt'], color=col, ls=ls, lw=S.LW)
    ax[0].set_xlim(yrs[0], yrs[-1])
    ax[0].set_ylim(0, None)
    ax[0].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[0].legend(handles=[Line2D([0], [0], color=S.REFERENCE, label=N.SCENARIOS['REF']),
                          Line2D([0], [0], color=S.PATHWAY_SETTING['moderate'], label=N.PATHWAY_RUNS['pathway-moderate']),
                          Line2D([0], [0], color=S.PATHWAY_SETTING['ambitious'],
                                 label=N.PATHWAY_RUNS['pathway-ambitious']),
                          Line2D([0], [0], color=S.TL, label=N.TL['TL'])] +
                 [Line2D([0], [0], color=S.MUTED, ls=ls, label=_variant_label(k)) for k, ls in VARIANT_LS],
                 fontsize=S.FONT_MIN)
    P.panel(ax[0], 'a', 'Annual')
    piv = v.pivot(index='run', columns='scenario', values='LoE_AR').loc[['Reference', 'pathway-moderate',
                                                                        'pathway-ambitious', 'TL']]
    x = np.arange(len(piv))
    wd = 0.8 / len(VARIANT_LS)
    for j, (scen, _) in enumerate(VARIANT_LS):
        ax[1].bar(x + (j - (len(VARIANT_LS) - 1) / 2) * wd, piv[scen], width=wd, color=S.SCENARIO[scen]['color'],
                  label=_variant_label(scen))
    ax[1].axhline(1, **{k: val for k, val in S.BOUNDARY['AR'].items() if k != 'label'}, gid='boundary')
    S.boundary_hzones(ax[1], 1.0, float(ref['B_AtP_kt'].sum() / ref['B_AR_kt'].sum()), lines=False)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([P.two_lines(r if r == 'Reference' else N.run_label(r)) for r in piv.index],
                          fontsize=S.FONT_MIN + 0.5, multialignment='center')     # two lines, centred
    ax[1].set_ylabel(f'{N.LOE_AR} 2026–2050')
    ax[1].legend(fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Cumulative')
    fig.tight_layout()
    _save(fig, 'ED3_replacement_variants')                          # ED8 -> ED3


def ed4():
    lg = D.csv('baseline/overbuild_absorption_log.csv')
    sa = D.csv('baseline/sensitivity_annual_carbon.csv')
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    yr = lg['year']
    P.line(ax[0], yr, lg['surplus_vacant'] / 1e3, color=S.BAND['overbuild_2026'][0], lw=S.LW_BOLD,
           label='Surplus still vacant U(t)')
    P.line(ax[0], yr, lg['cumulative_excess'] / 1e3, color=S.BAND['overbuild_2026'][0], ls=':', label='Cumulative excess C(t)')
    ax[0].bar(yr, -lg['payback_paid'] / 1e3, color='none', edgecolor=S.BAND['overbuild_absorbed'][0], lw=S.LW_OUTLINE,
              gid=P.NEG_BAR_GID, label='Payback (built less), per year')
    b2 = ax[0].twinx()
    P.line(b2, yr, 100 * lg['implied_vacancy'], color=S.INK, lw=S.LW_THIN, ls='--', label='Implied vacancy (right)')
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
             ('Overbuild never absorbed (MODEL v2.1 Reference)', S.MUTED, '-.', 'never absorbed')]   # dash-dot
    for case, col, ls, lab in cases:
        t = sa[sa['case'] == case]
        P.line(ax[1], t['year'], t['carbon_kt'], color=col, ls=ls, lw=S.LW, label=f'{lab}: {t["carbon_kt"].sum():,.0f} kt')
    ax[1].set_xlim(2026, 2050)
    ax[1].set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax[1].legend(fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Absorption timing (2026–2050 totals)')
    fig.tight_layout()
    _save(fig, 'SF5_overbuild_absorption', note='Theory fixes the direction (reversion to the equilibrium vacancy), '
                                                 'not the speed; 2035 is the common RECC window; speed bracketed.')


def edt1():
    """EDT1: each lever's native parameter by typology at Moderate, Ambitious and TL (Markdown + CSV)."""
    p = D.js('pathways/levers.json')
    typ = list(p['L4']['size_ref'])
    rows = []
    for L in LV.LEVERS:
        for t in typ:
            q = p[L]
            if L == 'L4':
                v = [q['f']['moderate'][t], q['f']['ambitious'][t], q['tl'][t]]
                par = 'f (share of the extra-space margin removed)'
            elif L in ('L5', 'L8'):
                v = [q['r']['moderate'], q['r']['ambitious'], q['tl'][t]]
                par = 'r (ratio to the Reference)'
            elif L == 'L7':
                s0 = q['soil_factor_2025'][t]
                v = [s0 * (1 - q['x']['moderate']), s0 * (1 - q['x']['ambitious']), q['tl'][t]]
                par = 'soil carbon loss (kg CO2e/m2 floor area)'
            elif L == 'L1':
                v = [q['S']['moderate']['2050'], q['S']['ambitious']['2050'], q['tl']]
                par = 'household size 2050 (all typologies)'
            elif L == 'L2':
                v = [q['v']['moderate'], q['v']['ambitious'], q['tl']]
                par = 'vacancy rate (all typologies)'
            elif L == 'L3':
                v = [q['d']['moderate'], q['d']['ambitious'], 1.0]
                par = 'd, reduction of demolition and surge (all typologies)'
            elif L == 'L9':
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
    L_ = ['# EDT1 Lever levels by typology: Moderate, Ambitious and Theoretical Limit', '',
          '| Lever | Sub-rule | Typology | Parameter | Moderate | Ambitious | TL |', '|---|---|---|---|---|---|---|']
    L_ += [f"| {r.lever} | {r.subrule} | {r.typology} | {r.parameter} | {r.moderate:.4g} | {r.ambitious:.4g} | "
           f"{r.tl:.4g} |" for r in df.itertuples()]
    with open(out + '.md', 'w') as f:
        f.write('\n'.join(L_) + '\n')


FIGURES = {'ED1_population_households_floor_area': ed1, 'ED2_household_formation_size': ed3,
           'ED3_replacement_variants': ed9, 'ED9_rollout_timing': ed10,      # ED8 dropped, ED10 -> ED9
           'SF3_census_replacement_rates': ed2, 'SF5_overbuild_absorption': ed4, 'SF10_lambda_sweep': sf3,
           'SF11_hd_estimators': sf4, 'SF14_conditional_tl': sf2}
TABLES = {'EDT1_levels_by_typology': edt1}
