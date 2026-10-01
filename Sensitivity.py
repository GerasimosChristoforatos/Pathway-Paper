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
                'Replacement scenario': '#1ABC9C', 'Near-term market excess': '#7F8C8D',
                'Near-term: how the excess is booked': '#7F8C8D', 'Near-term: rule variant': '#F39C12'}

# (group, label, {Boss setting: value})
CASES = [   # v1.1 lean set; the full v1.0.2 table is in the history (tag v1.0.2). All old options stay as flags.
    ('Replacement scenario', 'Low (S1): long-run rate, shares held', dict(REPLACEMENT_SCENARIO='S1')),
    ('Replacement scenario', 'Storyline: intensification continues (S2 + mix trend)', dict(REPLACEMENT_SCENARIO='S2')),
    ('Replacement scenario', 'S3: half-life 5 yr', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=5.0)),
    ('Replacement scenario', 'S3: half-life 15 yr', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=15.0)),
    ('Replacement scenario', 'High (S2): 2018-2023 rate persists, shares held',
     dict(REPLACEMENT_SCENARIO='S2', MIX_MODE='held')),
    ('Typology mix', 'S3-10 with the damped mix trend', dict(MIX_MODE='trend')),
    ('Household size', 'Stats NZ Low projection variant (S)', dict(HH_SIZE_VARIANT='Low')),
    ('Household size', 'Stats NZ High projection variant (S)', dict(HH_SIZE_VARIANT='High')),
    ('Household size', 'S after 2043: flat (kink at 2043)', dict(S_TAIL='flat')),
    ('Household size', 'S after 2043: secant-slope taper (v1.2)', dict(S_TAIL='taper_secant')),
    ('Household size', 'S after 2043: taper from the PCHIP end slope', dict(S_TAIL='taper')),
    ('Dwelling size', 'Dwelling size: 2016–2025 reference', dict(DWELLING_SIZE_REF=(2016, 2025))),
    ('Stock', 'Completion rate 0.92', dict(COMPLETION_RATE=0.92)),
    ('Stock', 'Completion rate 0.96', dict(COMPLETION_RATE=0.96)),
    ('Stock', "Completion lag on (Little's law)", dict(COMPLETION_LAG='littles_law')),
    ('Stock', 'No census under-construction correction', dict(CENSUS_UC_CORRECTION=False)),
    ('Near-term: how the excess is booked', 'Temporary surplus with payback, absorption 0.20/yr',
     dict(NEAR_TERM_MODE='surplus', NEAR_TERM_ABSORPTION=0.20)),
    ('Near-term: how the excess is booked', 'Temporary surplus with payback, absorption 0.10/yr',
     dict(NEAR_TERM_MODE='surplus', NEAR_TERM_ABSORPTION=0.10)),
    ('Near-term: how the excess is booked', 'Booked as redevelopment, stock-neutral (v1.1)',
     dict(NEAR_TERM_MODE='redevelopment')),
    ('Near-term: rule variant', 'Gap measured against the 2026 requirement', dict(NEAR_TERM_GAP_REF='2026')),
    ('Near-term: rule variant', 'Three-channel join (v1.0.2)', dict(NEAR_TERM_JOIN='nowcast')),
    ('Carbon factors', 'Soil on all floor area, incl. replacement', dict(SOIL_ON_REPLACEMENT=True)),
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
    present = [g for g in GROUP_COLORS if g in set(cases.group)]      # only groups shown
    handles = [plt.Rectangle((0, 0), 1, 1, color=GROUP_COLORS[g]) for g in present]
    ax[1].legend(handles, present, fontsize=8, loc='lower right')
    fig.text(0.01, 0.005, 'Note: the single-case carbon factors and the soil-order extremes (Raw / Organic) are bounds '
             'shown outside the Monte Carlo, not probability-weighted cases.', fontsize=8, style='italic')
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
    a.set_ylabel('Mm² per year'); a.legend(fontsize=7.5, loc='upper right')
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
