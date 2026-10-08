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
soil orders). When materials are decarbonised (Boss.DECARB_MODE), an alternative
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

import Boss
import figaudit

OUT_CSV = os.path.join(Boss.OUT_DIR, 'sensitivity_oat.csv')
FIG_DIR = os.path.join(Boss.OUT_DIR, 'figures')
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'   # set by run_all.py: write PNGs to FIG_DIR
SHOW_FIGURES = not (os.environ.get('PATHWAY_SAVE_FIGURES') == '1')
N_PATHS = 6              # cases drawn in the annual-path figure (largest effects)

GROUP_COLORS = {'Population': '#2E6DB4', 'Household size': '#E67E22', 'Households': '#D35400',
                'Stock': '#34495E', 'Typology mix': '#8E44AD', 'Dwelling size': '#16A085',
                'Carbon factors': '#C0392B',
                'Replacement scenario': '#1ABC9C', 'Near-term market excess': '#7F8C8D',
                'Near-term: how the excess is booked': '#7F8C8D', 'Near-term: rule variant': '#F39C12'}

# (group, label, {Boss setting: value})
CASES = [   # earlier, longer tables are preserved at the git tags (CHANGELOG)
    ('Replacement scenario', 'Low (S1): long-run rate, shares held', dict(REPLACEMENT_SCENARIO='S1')),
    ('Replacement scenario', 'S3: half-life 5 yr', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=5.0)),
    ('Replacement scenario', 'S3: half-life 15 yr', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=15.0)),
    ('Replacement scenario', 'High (S2): 2018-2023 rate persists, shares held', dict(REPLACEMENT_SCENARIO='S2')),
    ('Household size', 'Household size: Stats NZ Low variant', dict(HH_SIZE_VARIANT='Low')),
    ('Household size', 'Household size: Stats NZ High variant', dict(HH_SIZE_VARIANT='High')),
    ('Household size', 'Household size after 2043: flat (kink at 2043)', dict(S_TAIL='flat')),
    ('Household size', 'Household size after 2043: secant-slope taper', dict(S_TAIL='taper_secant')),
    ('Household size', 'Household size after 2043: taper from the PCHIP end slope', dict(S_TAIL='taper')),
    ('Dwelling size', 'Dwelling size: 2016–2025 reference', dict(DWELLING_SIZE_REF=(2016, 2025))),
    ('Stock', 'Completion rate 0.92', dict(COMPLETION_RATE=0.92)),
    ('Stock', 'Completion rate 0.96', dict(COMPLETION_RATE=0.96)),
    ('Stock', "Completion lag on (Little's law)", dict(COMPLETION_LAG='littles_law')),
    ('Stock', 'No census under-construction correction', dict(CENSUS_UC_CORRECTION=False)),
    ('Near-term: how the excess is booked', 'Temporary surplus with payback, absorption 0.20/yr',
     dict(NEAR_TERM_MODE='surplus', NEAR_TERM_ABSORPTION=0.20)),
    ('Near-term: how the excess is booked', 'Temporary surplus with payback, absorption 0.10/yr',
     dict(NEAR_TERM_MODE='surplus', NEAR_TERM_ABSORPTION=0.10)),
    ('Near-term: how the excess is booked', 'Booked as redevelopment, stock-neutral',
     dict(NEAR_TERM_MODE='redevelopment')),
    ('Near-term: rule variant', 'Gap measured against the 2026 requirement', dict(NEAR_TERM_GAP_REF='2026')),
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
    mix_int = sum(shares[t].values * base['intensity'][t].values for t in base['typ_names'])
    for p in ('5th', '95th'):
        tot = base['results'][p]['total']
        rows.append(('Population', f'Population: Stats NZ {p} percentile', tot[1:].sum() / 1e6,
                     float((tot[1:] * mix_int[1:]).sum()) / 1e6))
        paths[f'Population: Stats NZ {p} percentile'] = tot

    for grp, lab, kw in CASES + DECARB_CASES[Boss.DECARB_MODE]:
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
def _save(fig, name, tight=True):
    if tight:
        fig.tight_layout()
    if SAVE_FIGURES:
        os.makedirs(FIG_DIR, exist_ok=True)
        figaudit.record(fig, name)
        fig.savefig(os.path.join(FIG_DIR, name), dpi=140, bbox_inches='tight')


TOP_N = 5        # main-text tornados show the TOP_N largest parameters (full versions: *_SI)
PCT_NOTE = ('Percentages are relative to within-window carbon (2026-2050); fixed absolute terms such as soil '
            'carbon therefore show larger percentage effects than under whole-life accounting.')

# Rows that are alternative settings of one parameter (both ends shown together in
# the main-text tornado); every other row is a parameter of its own.
PARAMETER = {
    'Population: Stats NZ 5th percentile': 'Population', 'Population: Stats NZ 95th percentile': 'Population',
    'Low (S1): long-run rate, shares held': 'Replacement scenario',
    'High (S2): 2018-2023 rate persists, shares held': 'Replacement scenario',
    'S3: half-life 5 yr': 'S3 half-life', 'S3: half-life 15 yr': 'S3 half-life',
    'Household size: Stats NZ Low variant': 'Household-size variant',
    'Household size: Stats NZ High variant': 'Household-size variant',
    'Household size after 2043: flat (kink at 2043)': 'Household size after 2043',
    'Household size after 2043: secant-slope taper': 'Household size after 2043',
    'Household size after 2043: taper from the PCHIP end slope': 'Household size after 2043',
    'Completion rate 0.92': 'Completion rate', 'Completion rate 0.96': 'Completion rate',
    'Temporary surplus with payback, absorption 0.20/yr': 'Near-term payback',
    'Temporary surplus with payback, absorption 0.10/yr': 'Near-term payback',
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


def tornado(cases, out, name, title_note=None):
    """Horizontal bars of the % change in floor area and carbon per case."""
    fig, ax = plt.subplots(1, 2, figsize=(16, 0.42 * len(cases) + 2), sharey=True)
    fig.suptitle('Sensitivity 1: one assumption changed at a time, 2026-2050 '
                 '(bars are NOT additive and NOT a joint interval)'
                 + (f'\n{title_note}' if title_note else ''), fontsize=12)
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
    ax[1].legend(handles, present, fontsize=8, loc='upper left', bbox_to_anchor=(1.01, 1.0))   # outside: no overlap
    fig.text(0.01, 0.005, 'Note: the single-case carbon factors and the soil-order extremes (Raw / Organic) are bounds '
             'shown outside the Monte Carlo, not probability-weighted cases.\n' + PCT_NOTE, fontsize=8, style='italic')
    fig.tight_layout(rect=(0, 0.5 / fig.get_figheight(), 1, 1 - 0.25 / fig.get_figheight()))   # note; suptitle
    _save(fig, name, tight=False)


def figures(out, base, paths):
    cases = out[out.group != 'Adopted'].copy()
    cases['order'] = cases[['GFA_change_pct', 'carbon_change_pct']].abs().max(axis=1)
    cases = cases.sort_values('order')

    # ---- 1. tornado: how much each assumption moves the totals ------------
    # full table for the Supplementary Material; main text: the TOP_N largest
    tornado(cases, out, 'sens_1_tornado_SI.png')
    tornado(top_parameters(cases, TOP_N), out, 'sens_1_tornado.png',
            title_note=f'{TOP_N} largest parameters (effect on carbon; both ends shown); all rows: sens_1_tornado_SI')

    # ---- 2. annual paths: WHEN each assumption matters ---------------------
    fy = np.asarray(base['forecast_years'])
    hist = base['hist_built_gfa']
    adopted = base['results']['50th']['total']
    ranked = (cases[cases.group != 'Carbon factors']
              .assign(a=lambda d: d.GFA_change_pct.abs())
              .sort_values('a', ascending=False))
    show = [c for c in ranked.case if c in paths and 'percentile' not in c][:N_PATHS]
    pop = [c for c in ('Population: Stats NZ 5th percentile', 'Population: Stats NZ 95th percentile') if c in paths]
    fig, ax = plt.subplots(1, 3, figsize=(22, 6.2), gridspec_kw={'width_ratios': [1.6, 1, 1.15]})
    fig.suptitle('Sensitivity 2: when each assumption matters (annual built floor area) and what it adds up to '
                 '(cumulative carbon)', fontsize=12)
    a = ax[0]
    hy = hist.index[hist.index >= 2010]
    a.plot(hy, hist.loc[hy] / 1e6, color='black', lw=2.2, label='observed (built basis)')
    lo, hi = paths.get(pop[0]) if pop else None, paths.get(pop[-1]) if pop else None
    if lo is not None and hi is not None:
        a.fill_between(fy[1:], lo[1:] / 1e6, hi[1:] / 1e6, color='grey', alpha=0.15,
                       label='population 5th-95th')
    a.plot(fy[1:], adopted[1:] / 1e6, color='black', lw=2.2, ls='--', label='adopted')
    cmap = plt.get_cmap('tab10')
    colour = {c: cmap(i) for i, c in enumerate(show)}
    colour.update({c: ('#7f8c8d' if '5th' in c else '#2c3e50') for c in pop})
    for c in show:
        a.plot(fy[1:], paths[c][1:] / 1e6, color=colour[c], lw=1.6, label=c)
    for c in pop:
        a.plot(fy[1:], paths[c][1:] / 1e6, color=colour[c], lw=1.4, ls=':', label=c)
    a.axvline(2025.5, color='grey', ls=':', lw=1)
    a.set_xlim(2010, 2050); a.set_ylim(0, None); a.grid(alpha=0.3)
    a.set_ylabel('Mm² per year'); a.legend(fontsize=7, loc='upper right')
    a.set_title(f'The {len(show)} largest effects and the population 5th / 95th percentiles, against history')
    a = ax[1]
    for c in show:
        a.plot(fy[1:], 100 * (paths[c][1:] / adopted[1:] - 1), color=colour[c], lw=1.8, label=c)
    for c in pop:
        a.plot(fy[1:], 100 * (paths[c][1:] / adopted[1:] - 1), color=colour[c], lw=1.4, ls=':', label=c)
    a.axhline(0, color='black', lw=1)
    a.set_xlim(2026, 2050); a.grid(alpha=0.3)
    a.set_ylabel('% difference from adopted, each year')
    a.set_title('Early-years vs long-run effects')
    # ---- 3. cumulative carbon 2026-2050 of every path shown ------------------
    a = ax[2]
    carbon = out.set_index('case')['carbon_kt']
    bars = [('adopted', float(out.iloc[0]['carbon_kt']), 'black')] + \
           [(c, float(carbon[c]), colour[c]) for c in show + pop]
    yb = np.arange(len(bars))[::-1]
    a.barh(yb, [v for _, v, _ in bars], color=[c for *_, c in bars], height=0.7,
           edgecolor=['#c0392b' if i == 0 else 'none' for i in range(len(bars))],
           linewidth=[2.2 if i == 0 else 0 for i in range(len(bars))])
    ref = bars[0][1]
    for yi, (lab, v, _) in zip(yb, bars):
        a.text(v, yi, f'  {v:,.0f} kt' + ('  (adopted)' if lab == 'adopted' else f'  ({100 * (v / ref - 1):+.1f}%)'),
               va='center', fontsize=7.5)
    a.set_yticks(yb); a.set_yticklabels([lab for lab, *_ in bars], fontsize=7.5)
    a.set_xlim(0, 1.32 * max(v for _, v, _ in bars)); a.grid(alpha=0.3, axis='x')
    a.set_xlabel('kt CO₂e, 2026-2050'); a.set_title('Cumulative carbon 2026-2050 (% vs adopted)')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.text(0.5, 0.008, 'The Stats NZ household-size variants (Low / Medium / High) converge after about 2041 because '
             'their published projections end in 2043; household size is held flat after that in every variant, '
             'so the convergence is an artefact of the projection horizon, not a model result. Population '
             '5th / 95th: Stats NZ published percentiles; household size, typology mix, dwelling size and carbon '
             'factors at the adopted settings.', ha='center', fontsize=8, style='italic', wrap=True)
    _save(fig, 'sens_2_paths.png', tight=False)

    if SAVE_FIGURES:
        print(f"Figures written to {FIG_DIR}/ (sens_1, sens_2)")
    if SHOW_FIGURES:
        plt.show()


if __name__ == '__main__':
    main()
