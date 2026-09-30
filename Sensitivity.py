"""
SENSITIVITY -- one-at-a-time sensitivity of the 2026-2050 median projection
==========================================================================
Boss.py reports a population-only band. Every other structural assumption is
held at one value. This script re-runs Boss.main() with ONE assumption changed
at a time (all else at the adopted setting) and tabulates the effect on
cumulative built floor area and embodied carbon, 2026-2050, median population.

Population and carbon-factor rows need no re-run. The population percentiles
are already computed by Boss, and the typology mix does not depend on them, so
their carbon is floor area x each year's mix intensity. Carbon-factor rows
re-weight the adopted floor area by typology with alternative factors from
factors_typology.csv (jackknife range of the pooled material factor; extreme
soil orders).

One-at-a-time ranges show which assumptions matter. They are not a joint
uncertainty interval and must not be added in quadrature or summed.
"""

import contextlib
import importlib
import io
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import Boss

OUT_CSV = os.path.join(Boss.OUT_DIR, 'sensitivity_oat.csv')
FIG_DIR = os.path.join(Boss.OUT_DIR, 'figures')
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'   # set by run_all.py: write PNGs to FIG_DIR
SHOW_FIGURES = not (os.environ.get('PATHWAY_SAVE_FIGURES') == '1')
N_PATHS = 6              # cases drawn in the annual-path figure (largest effects)

GROUP_COLORS = {'Population': '#2E6DB4', 'Household size': '#E67E22', 'Households': '#D35400',
                'Stock': '#34495E', 'Typology mix': '#8E44AD', 'Dwelling size': '#16A085',
                'Carbon factors': '#C0392B', 'Near-term join (A1)': '#7F8C8D',
                'Replacement scenario': '#1ABC9C'}

# (group, label, {Boss setting: value})
CASES = [
    ('Household size', 'Stats NZ Low projection variant (S)', dict(HH_SIZE_VARIANT='Low')),
    ('Household size', 'Stats NZ High projection variant (S)', dict(HH_SIZE_VARIANT='High')),
    ('Household size', 'Carry 2025 deviation (rho estimated)', dict(HH_SIZE_RESPONSE=True)),
    ('Household size', 'S after 2043: 2038-43 secant slope', dict(S_TAIL='secant')),
    ('Household size', 'S after 2043: mean 2018-43 slope', dict(S_TAIL='mean_slope')),
    ('Household size', 'S after 2043: PCHIP end slope (original)', dict(S_TAIL='pchip_end_slope')),
    ('Household size', 'S anchored on observed 2025 (original)', dict(S_ANCHOR_YEAR=2025)),
    ('Household size', 'Carry 2025 deviation, rho = 0.9 (REJECTED: DHE estimation artefact)',
     dict(HH_SIZE_RESPONSE=True, DEVIATION_PERSISTENCE=0.9)),
    ('Households', 'DHE as published (no rebase; calib. to 2018)', dict(HH_CENSUS_REBASE=None)),
    ('Households', 'Census rebase: occupied dwellings only', dict(HH_CENSUS_REBASE='occupied')),
    # the household-identity sources have no census-interval rate, so no S3 path: run as S1
    ('Stock', 'Net replacement: household identity (original; S1)',
     dict(NET_REPLACEMENT_SOURCE='household_identity', REPLACEMENT_SCENARIO='S1')),
    ('Stock', 'Net replacement: household identity, constant empty share (S1)',
     dict(NET_REPLACEMENT_SOURCE='household_constant_empty_share', REPLACEMENT_SCENARIO='S1')),
    ('Stock', 'Net replacement: dwelling counts 2013-2023 only', dict(NET_REPLACEMENT_WINDOW=(2013, 2023))),
    ('Replacement scenario', 'S2: 2018-2023 rate persists (upper bound)', dict(REPLACEMENT_SCENARIO='S2')),
    ('Replacement scenario', 'S3: 2018-23 rate fades, half-life 5 yr',
     dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=5.0)),
    ('Replacement scenario', 'S1: long-run rate (lower bound)', dict(REPLACEMENT_SCENARIO='S1')),
    ('Replacement scenario', 'S3: 2018-23 rate fades, half-life 15 yr',
     dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=15.0)),
    ('Population', 'Projected 2026 growth (no population nowcast)', dict(NOWCAST_POPULATION=False)),
    ('Population', '2026 growth from the provisional 30 June release', dict(POP_NOWCAST_SOURCE='release_provisional')),
    ('Population', '2026 shortfall made up over 5 years (catch-up)', dict(POP_NOWCAST_CATCHUP_YEARS=5)),
    ('Near-term join (A1)', 'Carried 2025 deviation (original)', dict(NEAR_TERM_JOIN='carried_deviation')),
    ('Near-term join (A1)', 'No near-term join', dict(NEAR_TERM_JOIN='none')),
    ('Near-term join (A1)', 'Excess: all redevelopment', dict(EXCESS_CHANNELS='all_redevelopment')),
    ('Near-term join (A1)', 'Excess: all vacancy', dict(EXCESS_CHANNELS='all_vacancy')),
    ('Near-term join (A1)', 'Excess: equal shares', dict(EXCESS_CHANNELS='equal')),
    ('Near-term join (A1)', 'Vacancy drawn down over 3 yr', dict(VACANCY_DRAWDOWN_YEARS=3)),
    ('Near-term join (A1)', 'Vacancy drawn down over 10 yr', dict(VACANCY_DRAWDOWN_YEARS=10)),
    ('Near-term join (A1)', 'Household channel permanent', dict(HOUSEHOLD_CHANNEL='permanent')),
    ('Near-term join (A1)', 'Household channel reverts geometrically at rho',
     dict(HOUSEHOLD_CHANNEL='reverting')),
    ('Near-term join (A1)', 'Channel shares: population at census night (interpolated)',
     dict(CHANNEL_POP_DATE='census_night')),
    ('Near-term join (A1)', 'Channel shares: population at mid-year', dict(CHANNEL_POP_DATE='mid_year')),
    ('Near-term join (A1)', 'Nowcast Aug-Dec 2026: same-period ratio', dict(NOWCAST_METHOD='same_period_ratio')),
    ('Near-term join (A1)', 'Nowcast 2026: latest 12 months', dict(NOWCAST_METHOD='last_12_months')),
    ('Carbon factors', 'Soil on all floor area, incl. replacement (original)', dict(SOIL_ON_REPLACEMENT=True)),
    ('Typology mix', 'Damping phi = 0.5', dict(DAMPING_PHI=0.5)),
    ('Typology mix', 'Damping phi = 0.95', dict(DAMPING_PHI=0.95)),
    ('Typology mix', 'Trend window from 2016', dict(TREND_WINDOW_START=2016)),
    ('Dwelling size', 'Reference 2016-2025', dict(DWELLING_SIZE_REF=(2016, 2025))),
    ('Dwelling size', 'Reference 2025 only', dict(DWELLING_SIZE_REF=(2025, 2025))),
    ('Stock', 'No completion lag (original)', dict(COMPLETION_LAG=0)),
    ('Stock', 'Completion lag W = 0.99 (about 1 yr; W is a lower bound)', dict(COMPLETION_LAG=0.99)),
    ('Stock', 'Completion rate 0.92', dict(COMPLETION_RATE=0.92)),
    ('Stock', 'Completion rate 0.96', dict(COMPLETION_RATE=0.96)),
]


def run(**settings):
    """One silent Boss run with the given module settings; returns its state."""
    M = importlib.reload(Boss)          # fresh module globals every time
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        if not hasattr(M, k):
            raise AttributeError(f"Boss has no setting '{k}'.")
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


def totals(state):
    gfa = state['results']['50th']['total'][1:].sum() / 1e6
    carbon = state['carbon_total_typ'].iloc[1:].sum().sum() / 1e6
    return gfa, carbon


def main():
    base = run()
    g0, c0 = totals(base)
    rows = [('Adopted', 'Adopted settings', g0, c0)]
    paths = {}                                   # annual built floor area, per case

    # Carbon per m2 of each year's typology mix (identical across percentiles).
    shares = base['evolving_gfa_shares']
    mix_int = sum(shares[t].values * base['T_BASELINE_2025'][t] for t in base['typ_names'])
    for p in ('5th', '95th'):
        tot = base['results'][p]['total']
        rows.append(('Population', f'Stats NZ {p} percentile (level)', tot[1:].sum() / 1e6,
                     float((tot[1:] * mix_int[1:]).sum()) / 1e6))
        paths[f'Stats NZ {p} percentile (level)'] = tot

    for grp, lab, kw in CASES:
        st = run(**kw)
        g, c = totals(st)
        rows.append((grp, lab, g, c))
        paths[lab] = st['results']['50th']['total']

    # ---- carbon factors: re-weight the adopted floor area -------------------
    typ = base['typ_names']
    gfa_t = base['evol_typ_total'].iloc[1:].sum()          # m2 by typology
    # soil applies only to the soil-bearing floor area (item 8)
    soil_gfa_t = base['evol_typ_total'].mul(base['soil_frac'], axis=0).iloc[1:].sum()
    tf = pd.read_csv(Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]

    def carbon_with(emb, soc):
        return float(sum(gfa_t[t] * emb[t] + soil_gfa_t[t] * soc[t]
                         for t in typ)) / 1e6

    emb0, soc0 = tf['embodied_materials'], tf['SOC_avg']
    if 'emb_jackknife_min' in tf.columns:
        for lab, col in [('Materials: jackknife low (all typologies)', 'emb_jackknife_min'),
                         ('Materials: jackknife high (all typologies)', 'emb_jackknife_max'),
                         ('Materials: lowest single case study', 'emb_building_min'),
                         ('Materials: highest single case study', 'emb_building_max')]:
            rows.append(('Carbon factors', lab, g0, carbon_with(tf[col], soc0)))
    else:
        print("factors_typology.csv has no spread columns: re-run Building_factors.py.")
    rows.append(('Carbon factors', 'Soil: lowest soil order (Raw)', g0, carbon_with(emb0, tf['SOC_low'])))
    rows.append(('Carbon factors', 'Soil: highest soil order (Organic)', g0, carbon_with(emb0, tf['SOC_high'])))

    out = pd.DataFrame(rows, columns=['group', 'case', 'GFA_Mm2', 'carbon_kt'])
    out['GFA_change_pct'] = 100 * (out['GFA_Mm2'] / g0 - 1)
    out['carbon_change_pct'] = 100 * (out['carbon_kt'] / c0 - 1)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    print("=" * 96)
    print(" ONE-AT-A-TIME SENSITIVITY, 2026-2050 (median population unless stated)")
    print("=" * 96)
    print(f" {'group':<15}{'case':<44}{'GFA Mm2':>9}{'dGFA':>8}{'kt CO2e':>10}{'dC':>8}")
    for r in out.itertuples():
        c = f"{r.carbon_kt:>10,.0f}" if np.isfinite(r.carbon_kt) else f"{'':>10}"
        dc = f"{r.carbon_change_pct:>+7.1f}%" if np.isfinite(r.carbon_change_pct) else f"{'':>8}"
        print(f" {r.group:<15}{r.case:<44}{r.GFA_Mm2:>9.2f}{r.GFA_change_pct:>+7.1f}%{c}{dc}")
    print(" One-at-a-time ranges are NOT additive and are NOT a joint interval.")
    print(f"\nWritten: {OUT_CSV}")
    figures(out, base, paths)


# ============================================================
# FIGURES
# ============================================================
def _save(fig, name):
    fig.tight_layout()
    if SAVE_FIGURES:
        os.makedirs(FIG_DIR, exist_ok=True)
        fig.savefig(os.path.join(FIG_DIR, name), dpi=140, bbox_inches='tight')


def figures(out, base, paths):
    cases = out[out.group != 'Adopted'].copy()
    cases['order'] = cases[['GFA_change_pct', 'carbon_change_pct']].abs().max(axis=1)
    cases = cases.sort_values('order')

    # ---- 1. tornado: how much each assumption moves the totals ------------
    fig, ax = plt.subplots(1, 2, figsize=(16, 0.42 * len(cases) + 2), sharey=True)
    fig.suptitle('Sensitivity 1: one assumption changed at a time, 2026-2050 '
                 '(bars are NOT additive and NOT a joint interval)', fontsize=12)
    y = np.arange(len(cases))
    for a, col, title in [(ax[0], 'GFA_change_pct', 'Built floor area'),
                          (ax[1], 'carbon_change_pct', 'Embodied carbon')]:
        v = cases[col].values
        a.barh(y, v, color=[GROUP_COLORS.get(g, 'grey') for g in cases.group], height=0.7)
        for yi, vi in zip(y, v):
            if abs(vi) > 0.05:
                a.text(vi + (0.4 if vi >= 0 else -0.4), yi, f'{vi:+.1f}%', va='center',
                       ha='left' if vi >= 0 else 'right', fontsize=8)
        a.axvline(0, color='black', lw=1)
        lim = max(5, np.nanmax(np.abs(cases[['GFA_change_pct', 'carbon_change_pct']].values)) * 1.25)
        a.set_xlim(-lim, lim)
        a.set_title(f"{title}  (adopted: {out.iloc[0]['GFA_Mm2' if col.startswith('GFA') else 'carbon_kt']:,.1f}"
                    f"{' Mm²' if col.startswith('GFA') else ' kt'})")
        a.set_xlabel('% change from the adopted settings'); a.grid(alpha=0.3, axis='x')
    ax[0].set_yticks(y); ax[0].set_yticklabels(cases.case, fontsize=8.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in GROUP_COLORS.values()]
    ax[1].legend(handles, GROUP_COLORS.keys(), fontsize=8, loc='lower right')
    _save(fig, 'sens_1_tornado.png')

    # ---- 2. annual paths: WHEN each assumption matters ---------------------
    fy = np.asarray(base['forecast_years'])
    hist = base['hist_built_gfa']
    adopted = base['results']['50th']['total']
    ranked = (cases[cases.group != 'Carbon factors']
              .assign(a=lambda d: d.GFA_change_pct.abs())
              .sort_values('a', ascending=False))
    show = [c for c in ranked.case if c in paths and 'percentile' not in c][:N_PATHS]
    fig, ax = plt.subplots(1, 2, figsize=(16, 5.6), gridspec_kw={'width_ratios': [1.6, 1]})
    fig.suptitle('Sensitivity 2: when each assumption matters (annual built floor area)',
                 fontsize=12)
    a = ax[0]
    hy = hist.index[hist.index >= 2010]
    a.plot(hy, hist.loc[hy] / 1e6, color='black', lw=2.2, label='observed (built basis)')
    lo, hi = paths.get('Stats NZ 5th percentile (level)'), paths.get('Stats NZ 95th percentile (level)')
    if lo is not None and hi is not None:
        a.fill_between(fy[1:], lo[1:] / 1e6, hi[1:] / 1e6, color='grey', alpha=0.15,
                       label='population 5th-95th')
    a.plot(fy[1:], adopted[1:] / 1e6, color='black', lw=2.2, ls='--', label='adopted')
    cmap = plt.get_cmap('tab10')
    for i, c in enumerate(show):
        a.plot(fy[1:], paths[c][1:] / 1e6, color=cmap(i), lw=1.6, label=c)
    a.axvline(2025.5, color='grey', ls=':', lw=1)
    a.set_xlim(2010, 2050); a.set_ylim(0, None); a.grid(alpha=0.3)
    a.set_ylabel('million m² per year'); a.legend(fontsize=7.5, loc='upper right')
    a.set_title(f'The {len(show)} largest effects, against history')
    a = ax[1]
    for i, c in enumerate(show):
        a.plot(fy[1:], 100 * (paths[c][1:] / adopted[1:] - 1), color=cmap(i), lw=1.8, label=c)
    a.axhline(0, color='black', lw=1)
    a.set_xlim(2026, 2050); a.grid(alpha=0.3)
    a.set_ylabel('% difference from adopted, each year')
    a.set_title('Early-years vs long-run effects')
    _save(fig, 'sens_2_paths.png')

    if SAVE_FIGURES:
        print(f"Figures written to {FIG_DIR}/ (sens_1, sens_2)")
    if SHOW_FIGURES:
        plt.show()


if __name__ == '__main__':
    main()
