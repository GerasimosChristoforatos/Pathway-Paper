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
"""

import contextlib
import importlib
import io
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import projection
import layout
import naming as N
import style

OUT_CSV = layout.data('baseline/sensitivity_one_at_a_time.csv')
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'   # set by run_all.py: save every figure
SHOW_FIGURES = not (os.environ.get('PATHWAY_SAVE_FIGURES') == '1')
N_PATHS = 6              # cases drawn in the annual-path figure (largest effects)

# sensitivity groups -> the categorical palette (style.QUALITATIVE, Okabe-Ito), one colour per group
GROUPS = ['Population', 'Household size', 'Stock', 'Dwelling size', 'Carbon factors', 'Replacement variant',
          '2026 overbuild: how it is booked', '2026 overbuild: rule variant']

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
    ('2026 overbuild: how it is booked', 'Temporary surplus with payback, absorption 0.20/yr',
     dict(OVERBUILD_BOOKING='surplus', OVERBUILD_ABSORPTION=0.20)),
    ('2026 overbuild: how it is booked', 'Temporary surplus with payback, absorption 0.10/yr',
     dict(OVERBUILD_BOOKING='surplus', OVERBUILD_ABSORPTION=0.10)),
    ('2026 overbuild: how it is booked', 'Booked as redevelopment, stock-neutral',
     dict(OVERBUILD_BOOKING='redevelopment')),
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
    paths = {}                                   # annual built floor area, per case

    # Carbon per m2 of each year's typology mix (identical across percentiles).
    shares = base['evolving_gfa_shares']
    mix_int = sum(shares[t].values * base['intensity'][t].values for t in base['typ_names'])
    for p in ('5th', '95th'):
        tot = base['results'][p]['total']
        rows.append(('Population', f'Population: Stats NZ {p} percentile', tot[1:].sum() / 1e6,
                     float((tot[1:] * mix_int[1:]).sum()) / 1e6))
        paths[f'Population: Stats NZ {p} percentile'] = tot

    for grp, lab, kw in CASES + DECARB_CASES[projection.DECARB_MODE]:
        st = run(**kw)
        g, c = totals(st)
        rows.append((grp, lab, g, c))
        paths[lab] = st['results']['50th']['total']

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
    else:
        print("factors_typology.csv has no spread columns: re-run Building_factors.py.")
    rows.append(('Carbon factors', 'Soil carbon: lowest soil order (Raw)', g0, carbon_with(emb0, tf['SOC_low'])))
    rows.append(('Carbon factors', 'Soil carbon: highest soil order (Organic)', g0, carbon_with(emb0, tf['SOC_high'])))

    out = pd.DataFrame(rows, columns=['group', 'case', 'GFA_Mm2', 'carbon_kt'])
    out['GFA_change_pct'] = 100 * (out['GFA_Mm2'] / g0 - 1)
    out['carbon_change_pct'] = 100 * (out['carbon_kt'] / c0 - 1)
    N.columns(out).to_csv(layout.writing(OUT_CSV), index=False)

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
def _save(fig, name, tight=True, note=None):
    if tight:
        fig.tight_layout()
    if SAVE_FIGURES:
        style.save_figure(fig, name, note=note)


POP_NOTE = ('Population rows: carbon is the floor area of the path times the Reference carbon per m² of each year '
            '(an approximation, listed as a known issue in the CHANGELOG); the engine carbon of the population paths, carbon and boundaries '
            'together, is in data/aesa/results.json (population_paths) and is the one used in H11. ')
PCT_NOTE = ('Percentages are relative to carbon 2026–2050 (time-resolved accounting); fixed absolute terms such as '
            'soil carbon loss therefore show larger percentage effects than under whole-life accounting.')

# Rows that are alternative settings of one parameter (both ends shown together in
# the main-text tornado); every other row is a parameter of its own.
PARAMETER = {
    'Population: Stats NZ 5th percentile': 'Population', 'Population: Stats NZ 95th percentile': 'Population',
    'Low replacement: long-run rate': 'Replacement variant',
    'High replacement: 2018-2023 rate persists': 'Replacement variant',
    N.SCENARIOS['REF_HL5']: 'Replacement half-life', N.SCENARIOS['REF_HL15']: 'Replacement half-life',
    'Household size: Stats NZ Low variant': 'Household-size variant',
    'Household size: Stats NZ High variant': 'Household-size variant',
    'Household size after 2043: flat (kink at 2043)': 'Household size after 2043',
    'Household size after 2043: secant-slope taper': 'Household size after 2043',
    'Household size after 2043: taper from the PCHIP end slope': 'Household size after 2043',
    'Completion rate 0.92': 'Completion rate', 'Completion rate 0.96': 'Completion rate',
    'Temporary surplus with payback, absorption 0.20/yr': '2026 overbuild payback',
    'Temporary surplus with payback, absorption 0.10/yr': '2026 overbuild payback',
    'A4-A5 held at 2025 (no generic 1%/yr)': 'A4-A5 path', "A4-A5 on each item's own Horup path": 'A4-A5 path',
    'Materials: jackknife low (all typologies)': 'Materials: jackknife',
    'Materials: jackknife high (all typologies)': 'Materials: jackknife',
    'Materials: lowest single case study': 'Materials: single case study',
    'Materials: highest single case study': 'Materials: single case study',
    'Soil carbon: lowest soil order (Raw)': 'Soil order', 'Soil carbon: highest soil order (Organic)': 'Soil order',
}


def top_parameters(cases, n, label='case', parameter=None, cols=('carbon_change_pct',)):
    """All rows of the n parameters with the largest absolute effect (max over cols and
    over the parameter's rows), so both ends of a paired parameter are shown; ascending
    order of the row effect (the tornado draws the largest at the top)."""
    parameter = PARAMETER if parameter is None else parameter
    eff = cases[list(cols)].abs().max(axis=1)
    par = cases[label].map(lambda c: parameter.get(c, c))
    top = eff.groupby(par).max().sort_values().tail(n).index
    return cases.assign(order=eff)[par.isin(top)].sort_values('order')


def group_colour(g):
    if g not in GROUPS:
        raise ValueError(f'Sensitivity group {g!r} has no colour (GROUPS).')
    return style.QUALITATIVE[GROUPS.index(g)]


def tornado(cases, out, fid):
    """D16: horizontal bars of the % change in floor area and carbon per case, all rows."""
    import plotting as P
    from matplotlib.patches import Patch
    S = style
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 24 + 3.6 * len(cases)), sharey=True)
    y = np.arange(len(cases))
    lim = max(5, np.nanmax(np.abs(cases[['GFA_change_pct', 'carbon_change_pct']].values)) * 1.3)
    for a, col, title, letter in [(ax[0], 'GFA_change_pct', 'Floor area', 'a'),
                                  (ax[1], 'carbon_change_pct', 'Embodied carbon', 'b')]:
        v = cases[col].values
        a.barh(y, v, color=[group_colour(g) for g in cases.group], height=0.7)
        for yi, vi in zip(y, v):
            if abs(vi) > 0.05:
                a.text(vi + (0.01 if vi >= 0 else -0.01) * lim, yi, f'{vi:+.1f}%', va='center',
                       ha='left' if vi >= 0 else 'right', fontsize=S.FONT_MIN)
        a.axvline(0, color=S.INK, lw=S.LW_THIN)
        a.set_xlim(-lim, lim)
        adopted = out.iloc[0]['GFA_Mm2' if col.startswith('GFA') else 'carbon_kt']
        a.set_xlabel('Change vs the Reference (%)')
        a.grid(axis='y', visible=False)
        P.panel(a, letter, f"{title} (Reference: {adopted:,.1f}{' Mm²' if col.startswith('GFA') else ' kt CO₂e'})")
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(cases.case, fontsize=S.FONT_MIN)
    present = [g for g in GROUPS if g in set(cases.group)]
    fig.legend(handles=[Patch(color=group_colour(g), label=g) for g in present], loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 10 / (24 + 3.6 * len(cases)), 1, 1))
    _save(fig, fid, tight=False,
          note='One assumption changed at a time from the Reference (the adopted settings), 2026–2050; bars are not additive and not a joint interval. The '
               'single-case carbon factors and the soil-order extremes (Raw / Organic) are bounds outside the Monte '
               'Carlo, not probability-weighted cases. ' + POP_NOTE + PCT_NOTE)


def figures(out, base, paths):
    import plotting as P
    S = style
    S.apply()
    cases = out[out.group != 'Reference'].copy()
    cases['order'] = cases[['GFA_change_pct', 'carbon_change_pct']].abs().max(axis=1)
    cases = cases.sort_values('order')

    # ---- D16: every one-at-a-time case (the largest parameters on the LoE: H11) ----
    tornado(cases, out, 'D16_one_at_a_time')

    # ---- D17: annual paths, WHEN each assumption matters ---------------------
    fy = np.asarray(base['forecast_years'])
    hist = base['hist_built_gfa']
    adopted = base['results']['50th']['total']
    ranked = (cases[cases.group != 'Carbon factors']
              .assign(a=lambda d: d.GFA_change_pct.abs())
              .sort_values('a', ascending=False))
    show = [c for c in ranked.case if c in paths and 'percentile' not in c][:N_PATHS]
    pop = [c for c in ('Population: Stats NZ 5th percentile', 'Population: Stats NZ 95th percentile') if c in paths]
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 92), gridspec_kw={'width_ratios': [1.25, 1, 1.15]})
    colour = {c: S.QUALITATIVE[1 + i] for i, c in enumerate(show)}
    colour.update({c: S.MUTED for c in pop})
    num = {c: i for i, c in enumerate(show + pop, 1)}          # cases numbered: legend (a) and bars (c)
    a = ax[0]
    hy = hist.index[hist.index >= 2010]
    a.plot(hy, hist.loc[hy] / 1e6, color=S.INK, lw=S.LW_BOLD, label='History (built)')
    lo, hi = paths.get(pop[0]) if pop else None, paths.get(pop[-1]) if pop else None
    if lo is not None and hi is not None:
        a.fill_between(fy[1:], lo[1:] / 1e6, hi[1:] / 1e6, label='Population 5th–95th percentile', **S.MC_BAND)
    a.plot(fy[1:], adopted[1:] / 1e6, color=S.INK, lw=S.LW_BOLD, ls='--', label='Reference')
    for c in show:
        a.plot(fy[1:], paths[c][1:] / 1e6, color=colour[c], lw=S.LW, label=f'{num[c]}  {c}')
    for c in pop:
        a.plot(fy[1:], paths[c][1:] / 1e6, color=colour[c], lw=S.LW, ls=':', label=f'{num[c]}  {c}')
    P.split(a)
    a.set_xlim(2010, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Floor area (Mm² per year)')
    P.panel(a, 'a', f'The {len(show)} largest effects, against history')
    a = ax[1]
    for c in show:
        a.plot(fy[1:], 100 * (paths[c][1:] / adopted[1:] - 1), color=colour[c], lw=S.LW)
    for c in pop:
        a.plot(fy[1:], 100 * (paths[c][1:] / adopted[1:] - 1), color=colour[c], lw=S.LW, ls=':')
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.set_xlim(2026, 2050)
    a.set_ylabel('Difference vs the Reference, each year (%)')
    P.panel(a, 'b', 'Early-year vs long-run effects')
    a = ax[2]
    carbon = out.set_index('case')['carbon_kt']
    bars = [('Reference', float(out.iloc[0]['carbon_kt']), S.INK)] + \
           [(c, float(carbon[c]), colour[c]) for c in show + pop]
    yb = np.arange(len(bars))[::-1]
    a.barh(yb, [v for _, v, _ in bars], color=[c for *_, c in bars], height=0.7)
    ref = bars[0][1]
    for yi, (lab, v, _) in zip(yb, bars):
        a.text(v, yi, f' {v:,.0f}' + ('' if lab == 'Reference' else f' ({100 * (v / ref - 1):+.1f}%)'),
               va='center', fontsize=S.FONT_MIN)
    a.set_yticks(yb)
    a.set_yticklabels(['Reference'] + [str(num[c]) for c in show + pop], fontsize=S.FONT_MIN)
    a.set_xlim(0, 1.45 * max(v for _, v, _ in bars))
    P.thousands(a.xaxis)
    a.grid(axis='y', visible=False)
    a.set_xlabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.panel(a, 'c', 'Cumulative carbon (% vs the Reference)')
    h_, l_ = ax[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.01), frameon=False, fontsize=S.FONT_MIN)
    fig.tight_layout(rect=(0, 0.25, 1, 1))
    _save(fig, 'D17_sensitivity_paths', tight=False,
          note='Cases numbered as in the legend. The Stats NZ household-size variants converge after about 2041 because their published projections end '
               'in 2043 and household size is held flat after that in every variant: an artefact of the projection '
               'horizon, not a model result. Population 5th / 95th: Stats NZ published percentiles, every other '
               'input at the adopted settings. ' + POP_NOTE)

    if SAVE_FIGURES:
        print("Figures written to outputs/diagnostics/sensitivity/ (D16, D17)")
    if SHOW_FIGURES:
        plt.show()


if __name__ == '__main__':
    main()
