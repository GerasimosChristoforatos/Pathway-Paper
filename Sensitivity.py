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
import matplotlib
matplotlib.use('Agg')

import Boss

OUT_CSV = os.path.join(Boss.DATA_DIR, 'sensitivity_oat.csv')

# (group, label, {Boss setting: value})
CASES = [
    ('Household size', 'Stats NZ Low projection variant (S)', dict(HH_SIZE_VARIANT='Low')),
    ('Household size', 'Stats NZ High projection variant (S)', dict(HH_SIZE_VARIANT='High')),
    ('Household size', 'Carry 2025 deviation (rho estimated)', dict(HH_SIZE_RESPONSE=True)),
    ('Household size', 'Carry 2025 deviation, rho = 0.9',
     dict(HH_SIZE_RESPONSE=True, DEVIATION_PERSISTENCE=0.9)),
    ('Households', 'DHE as published (no rebase; calib. to 2018)', dict(HH_CENSUS_REBASE=None)),
    ('Households', 'Census rebase: occupied dwellings only', dict(HH_CENSUS_REBASE='occupied')),
    ('Stock', 'Replacement regime 2019-2023 persists', dict(DEMOLITION_CALIB_START=2019)),
    ('Typology mix', 'Damping phi = 0.5', dict(DAMPING_PHI=0.5)),
    ('Typology mix', 'Damping phi = 0.95', dict(DAMPING_PHI=0.95)),
    ('Typology mix', 'Trend window from 2016', dict(TREND_WINDOW_START=2016)),
    ('Dwelling size', 'Reference 2016-2025', dict(DWELLING_SIZE_REF=(2016, 2025))),
    ('Dwelling size', 'Reference 2025 only', dict(DWELLING_SIZE_REF=(2025, 2025))),
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

    # Carbon per m2 of each year's typology mix (identical across percentiles).
    shares = base['evolving_gfa_shares']
    mix_int = sum(shares[t].values * base['T_BASELINE_2025'][t] for t in base['typ_names'])
    for p in ('5th', '95th'):
        tot = base['results'][p]['total']
        rows.append(('Population', f'Stats NZ {p} percentile (level)', tot[1:].sum() / 1e6,
                     float((tot[1:] * mix_int[1:]).sum()) / 1e6))

    for grp, lab, kw in CASES:
        g, c = totals(run(**kw))
        rows.append((grp, lab, g, c))

    # ---- carbon factors: re-weight the adopted floor area -------------------
    typ = base['typ_names']
    gfa_t = base['evol_typ_total'].iloc[1:].sum()          # m2 by typology
    tf = pd.read_csv(Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]

    def carbon_with(emb, soc):
        return float(sum(gfa_t[t] * (emb[t] + soc[t]) for t in typ)) / 1e6

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


if __name__ == '__main__':
    main()
