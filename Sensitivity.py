"""
SENSITIVITY -- one-at-a-time sensitivity of the 2026-2050 median projection
==========================================================================
projection.py reports a population-only band. Every other structural assumption is
held at one value. This script re-runs projection.main() with ONE assumption changed
at a time (all else at the adopted setting) and tabulates the effect on
cumulative built floor area and embodied carbon, 2026-2050, median population.

Population and carbon-factor rows need no re-run. The population percentiles
are already computed by projection, and the typology mix does not depend on them, so
their carbon is floor area x each year's mix intensity. Carbon-factor rows
re-weight the adopted floor area by typology with alternative factors from
factors_typology.csv (jackknife range of the pooled material factor; extreme
soil orders). When materials are decarbonised (projection.DECARB_MODE), an alternative
materials factor follows the adopted factor's relative path over time, and the
decarbonisation rows of DECARB_CASES for the adopted mode are added.

One-at-a-time ranges show which assumptions matter. They are not a joint
uncertainty interval and must not be added in quadrature or summed.

This module writes data only (MODEL v3.0.0 compute / draw separation): D16 and D17 are drawn by
figures/sensitivity.py and the Fig7 tornado by figures/paper_main.py, from the grouped tables of
tools/sensitivity_tables.py. MODEL v3.0.0 adds the overbuild-absorption timing rows (never / by 2030 / by 2045) and
the vacancy-parameter row (1986-2023 census mean).
"""

import contextlib
import importlib
import io

import numpy as np
import pandas as pd

import projection
import layout
import naming as N

OUT_CSV = layout.data('baseline/sensitivity_one_at_a_time.csv')
# MODEL v2.0.0: annual carbon 2026-2050 of every row (Extended Data sensitivity paths), with the population
# rows also from the exact engine paths of the projection (carbon and floor area of the 5th / 95th paths)
OUT_ANNUAL = layout.data('baseline/sensitivity_annual_carbon.csv')
POP_ENGINE = 'Population: Stats NZ {p} percentile (engine path)'

# (group, label, {projection setting: value})
CASES = [   # earlier, longer tables are preserved at the git tags (CHANGELOG)
    ('Replacement variant', 'Low replacement: long-run rate', dict(REPLACEMENT_VARIANT='LOW')),
    ('Replacement variant', N.SCENARIOS['REF_HL5'], dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=5.0)),
    ('Replacement variant', N.SCENARIOS['REF_HL15'], dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=15.0)),
    ('Replacement variant', 'High replacement: 2018-2023 rate persists', dict(REPLACEMENT_VARIANT='HIGH')),
    ('Household size', 'Household size: Stats NZ Low variant', dict(HH_SIZE_VARIANT='Low')),
    ('Household size', 'Household size: Stats NZ High variant', dict(HH_SIZE_VARIANT='High')),
    ('Household size', 'Household size after 2043: flat (kink at 2043)', dict(S_TAIL='flat')),
    ('Household size', 'Household size after 2043: secant-slope taper', dict(S_TAIL='taper_secant')),
    ('Household size', 'Household size after 2043: taper from the PCHIP end slope', dict(S_TAIL='taper')),
    ('Dwelling size', 'Dwelling size: 2016-2025 reference', dict(DWELLING_SIZE_REF=(2016, 2025))),
    ('Stock', 'Completion rate 0.92', dict(COMPLETION_RATE=0.92)),
    ('Stock', 'Completion rate 0.96', dict(COMPLETION_RATE=0.96)),
    ('Stock', "Completion lag on (Little's law)", dict(COMPLETION_LAG='littles_law')),
    ('Stock', 'No census under-construction correction', dict(CENSUS_UC_CORRECTION=False)),
    # MODEL v3.0.0: the Reference absorbs the overbuild by 2035 (logistic); the speed is bracketed here
    ('2026 overbuild: absorption', 'Overbuild never absorbed (MODEL v2.1 Reference)',
     dict(OVERBUILD_ABSORPTION_END=None)),
    ('2026 overbuild: absorption', 'Overbuild absorbed by 2030', dict(OVERBUILD_ABSORPTION_END=2030)),
    ('2026 overbuild: absorption', 'Overbuild absorbed by 2045', dict(OVERBUILD_ABSORPTION_END=2045)),
    ('2026 overbuild: how it is booked', 'Booked as redevelopment, stock-neutral',
     dict(OVERBUILD_BOOKING='redevelopment')),
    ('Stock', 'Vacancy parameter: 1986-2023 census mean, one definition', dict(VACANCY_PARAMETER='consistent_mean')),
    ('2026 overbuild: rule variant', 'Gap measured against the 2026 requirement', dict(OVERBUILD_GAP_REF='2026')),
    ('Carbon factors', 'Soil on all floor area, incl. replacement', dict(SOIL_ON_REPLACEMENT=True)),
]
# Carbon-factor and accounting rows of the adopted item-level, time-resolved run
# (none for the frozen check run, so the table of baseline v2 keeps its rows):
# frozen technology; the item-level decarbonisation sensitivities; A4-A5 held or on
# item paths; event timing L / n. (Whole life at construction is an accounting
# convention, not a parameter: it is a PB sensitivity row, pb_sensitivity.csv.)
FROZEN_CASE = ('Carbon factors', 'Frozen technology: 2025 factors held (no decarbonisation)',
               dict(DECARB_MODE='none', DECARB_A45='held'))
DECARB_CASES = {
    'none': [],
    'horup_item': [
        FROZEN_CASE,
        ('Carbon factors', 'Decarbonisation: proxy-mapped items held at 2025', dict(DECARB_ITEM_CASE='proxies_held')),
        ('Carbon factors', 'Decarbonisation: NZ-made electricity-intensive items held at 2025',
         dict(DECARB_ITEM_CASE='nz_elec_held')),
        ('Carbon factors', 'A4-A5 held at 2025 (no generic 1%/yr)', dict(DECARB_A45='held')),
        ('Carbon factors', "A4-A5 on each item's own Horup path", dict(DECARB_A45='item')),
        ('Carbon factors', 'Event timing: interval L / n', dict(EVENT_TIMING='n'))],
}

def run(**settings):
    """One silent projection run with the given module settings; returns its state."""
    M = importlib.reload(projection)          # fresh module globals every time
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        if not hasattr(M, k):
            raise AttributeError(f"projection has no setting '{k}'.")
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
    rows = [('Reference', 'Reference (adopted settings)', g0, c0)]
    years = np.asarray(base['forecast_years'])
    annual = {('Reference', 'Reference (adopted settings)'): base['carbon_total_typ'].sum(axis=1).values}

    # Carbon per m2 of each year's typology mix (identical across percentiles).
    shares = base['evolving_gfa_shares']
    mix_int = sum(shares[t].values * base['intensity'][t].values for t in base['typ_names'])
    for p in ('5th', '95th'):
        tot = base['results'][p]['total']
        rows.append(('Population', f'Population: Stats NZ {p} percentile', tot[1:].sum() / 1e6,
                     float((tot[1:] * mix_int[1:]).sum()) / 1e6))
        annual[('Population', f'Population: Stats NZ {p} percentile')] = np.concatenate(
            [[np.nan], tot[1:] * mix_int[1:]])          # the approximation of this row, by year
        annual[('Population', POP_ENGINE.format(p=p))] = np.asarray(base['engine_out'][p]['carbon'], float)

    for grp, lab, kw in CASES + DECARB_CASES[projection.DECARB_MODE]:
        st = run(**kw)
        g, c = totals(st)
        rows.append((grp, lab, g, c))
        annual[(grp, lab)] = st['carbon_total_typ'].sum(axis=1).values

    # ---- carbon factors: re-weight the adopted floor area -------------------
    typ = base['typ_names']
    gfa_t = base['evol_typ_total'].iloc[1:].sum()          # m2 by typology
    # soil applies only to the soil-bearing floor area (item 8)
    soil_gfa_t = base['evol_typ_total'].mul(base['soil_frac'], axis=0).iloc[1:].sum()
    tf = pd.read_csv(projection.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]

    emb0, soc0 = tf['embodied_materials'], tf['SOC_avg']
    gfa_y = base['evol_typ_total'].iloc[1:]                 # m2 by year and typology
    # decarbonised run: an alternative materials factor follows the adopted
    # factor's relative path, emb_alt x (materials intensity(t) / 2025 value)
    rel = (None if base['DECARB'] is None else
           {t: (np.asarray(base['T_INT'][t])[1:] - base['SOIL_INTENSITY'][t]) / emb0[t] for t in typ})

    # time-resolved run: the run's materials carbon (upfront + in-window replacements and
    # repaints) scaled by emb_alt / emb_2025 per typology (same stage composition)
    mat_c = ({t: float(base['carbon_total_typ'][t].iloc[1:].sum())
              - float((base['evol_typ_total'][t].values * base['soil_frac'])[1:].sum()) * base['SOIL_INTENSITY'][t]
              for t in typ} if base['TIME_RESOLVED'] else None)

    def carbon_with_annual(emb, soc):
        """carbon_with by year (kg), the same terms year by year (time-resolved accounting)."""
        if mat_c is None:
            return None
        out = np.zeros(len(years))
        for t in typ:
            soil_y = (base['evol_typ_total'][t].values * base['soil_frac']) * base['SOIL_INTENSITY'][t]
            mat_y = base['carbon_total_typ'][t].values - soil_y
            out += mat_y * emb[t] / emb0[t] + base['evol_typ_total'][t].values * base['soil_frac'] * soc[t]
        return out

    def carbon_with(emb, soc):
        if mat_c is not None:
            return float(sum(mat_c[t] * emb[t] / emb0[t] + soil_gfa_t[t] * soc[t] for t in typ)) / 1e6
        if rel is None:
            return float(sum(gfa_t[t] * emb[t] + soil_gfa_t[t] * soc[t]
                             for t in typ)) / 1e6
        return float(sum((gfa_y[t].values * emb[t] * rel[t]).sum() + soil_gfa_t[t] * soc[t]
                         for t in typ)) / 1e6

    if 'emb_jackknife_min' in tf.columns:
        for lab, col in [('Materials: jackknife low (all typologies)', 'emb_jackknife_min'),
                         ('Materials: jackknife high (all typologies)', 'emb_jackknife_max'),
                         ('Materials: lowest single case study', 'emb_building_min'),
                         ('Materials: highest single case study', 'emb_building_max')]:
            rows.append(('Carbon factors', lab, g0, carbon_with(tf[col], soc0)))
            annual[('Carbon factors', lab)] = carbon_with_annual(tf[col], soc0)
    else:
        print("factors_typology.csv has no spread columns: re-run Building_factors.py.")
    rows.append(('Carbon factors', 'Soil carbon: lowest soil order (Raw)', g0, carbon_with(emb0, tf['SOC_low'])))
    rows.append(('Carbon factors', 'Soil carbon: highest soil order (Organic)', g0, carbon_with(emb0, tf['SOC_high'])))
    annual[('Carbon factors', 'Soil carbon: lowest soil order (Raw)')] = carbon_with_annual(emb0, tf['SOC_low'])
    annual[('Carbon factors', 'Soil carbon: highest soil order (Organic)')] = carbon_with_annual(emb0, tf['SOC_high'])

    out = pd.DataFrame(rows, columns=['group', 'case', 'GFA_Mm2', 'carbon_kt'])
    out['GFA_change_pct'] = 100 * (out['GFA_Mm2'] / g0 - 1)
    out['carbon_change_pct'] = 100 * (out['carbon_kt'] / c0 - 1)
    N.columns(out).to_csv(layout.writing(OUT_CSV), index=False)
    # annual carbon of every row; each row's 2026-2050 sum must equal its total in the table
    tot = {(r.group, r.case): r.carbon_kt for r in out.itertuples()}
    arows = []
    for (grp, lab), v in annual.items():
        if v is None:
            continue
        v = np.asarray(v, float)
        if lab in [k[1] for k in tot] and np.isfinite(tot[(grp, lab)]):
            if not np.isclose(np.nansum(v[1:]) / 1e6, tot[(grp, lab)], rtol=1e-9):
                raise SystemExit(f'Sensitivity: annual carbon of {lab!r} does not add up to its total.')
        arows += [dict(group=grp, case=lab, year=int(y), carbon_kt=float(v[i]) / 1e6)
                  for i, y in enumerate(years) if y >= 2026]
    N.columns(pd.DataFrame(arows)).to_csv(layout.writing(OUT_ANNUAL), index=False)

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
