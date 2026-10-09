"""
PATHWAYS: pathway runs, attribution, AESA gap, back-cast, solution space, theoretical limit
===========================================================================================
Reads the projection state (validation.run_boss -> projection.main() locals, in memory only)
and re-calls engine.forward() with copies of `fwd_inputs` modified by levers.py;
nothing in the model changes and no baseline output is written (the baseline is
unchanged: tests/test_regression_model_v1.py). With every lever off the run IS the
Reference (tested to 1e-9: annual carbon, upfront, maintenance within 2026-2050,
floor area by typology, demand bands, committed range, cumulative LoE AR / AtP).

Runs (naming.py vocabulary; the Reference projection unless stated; settings Moderate and Ambitious):
  REF                 the Reference (every lever off); LOW, HIGH: the replacement variants
  levers              L1 Dwelling size, L2 Vacancy rate, L3 Overbuild absorption, L4 Building
                      retention, L5 Material carbon, each alone
  pathways            P1 Right-sized dwellings (L1), P2 Occupied stock (L2 + L3), P3 Retained
                      stock (L4), P4 Low-carbon materials (L5), P5 Combined (every lever)
  attribution         Shapley values over the 16 pathway subsets (main) and the 32 lever
                      subsets (SI), exact arithmetic; demand bands by run (exact by band)
  variants            the Reference and P5 under Low and High replacement (full projection runs
                      with REPLACEMENT_VARIANT changed, as tools/replacement_scenarios.py)
  sensitivities       P5 with full roll-out by 2030 and by 2045 (all three variants); P4 and P5
                      with the apartments held at r = 1 (L5)
  theoretical limit   TL (TL1-TL6 at full strength from 2027) and TL, gradual adoption (SI)

AESA gap: boundaries B_AR, B_AtP by year for the Reference from outputs/pb_annual.csv;
cumulative LoE = ratio of sums (aesa.cumulative_loe). Back-cast on P5 Moderate,
P5 Ambitious and the Reference: a uniform factor k on all 2027-2050 construction (floor area by
typology; carbon linear in floor area; 2026 fixed), scipy.optimize.brentq for
cumulative LoE AR = 1; AtP: the minimum attainable LoE (2026 cohort alone).
Solution space (Horup et al. 2025, Fig. 6 style) on the Reference.

Writes outputs/data/pathways/ (release names: naming.columns / naming.keys): runs.csv,
annual.csv, bands.csv, shapley_pathways.csv, shapley_levers.csv, shapley_subsets.csv,
shapley_theoretical_limit.csv, shapley_theoretical_limit_subsets.csv, backcast.json,
solution_space.csv, levers.json, theoretical_limit.json; and the pathway figures
(style.save_figure). The documents (LEVERS_TABLE.md, the methods draft, the ASSUMPTIONS
section) are written by tools/pathways_methods.py --sections.

    python pathways.py          (run_all.py --pathways-only runs it with the tests)
"""
import contextlib
import io
import itertools
import json
import math
import os
import sys
import time
from fractions import Fraction

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import aesa  # noqa: E402
import engine  # noqa: E402
import events as EV  # noqa: E402
import figure_plan as FP  # noqa: E402
import layout  # noqa: E402
import levers as LV  # noqa: E402
import naming as N  # noqa: E402
import style  # noqa: E402
import validation  # noqa: E402

RAMP_ADOPTED = LV.ADOPTION_ADOPTED

OUT = layout.data('pathways', frozen=False)
FILE_PB_ANNUAL = layout.data('aesa/annual.csv', frozen=False)
FILE_PB_RESULTS = layout.data('aesa/results.json', frozen=False)
FILE_BOSS_RESULTS = layout.data('baseline/projection.json', frozen=False)
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'
QUICK = os.environ.get('PATHWAY_QUICK') == '1'
RUN_MODE = 'QUICK RUN, not for reporting' if QUICK else 'full'

WINDOW = (2026, 2050)
REFERENCE = 'REF'
# the Reference and the two replacement variants, as tools/replacement_scenarios.py
SCENARIOS = {'LOW': (N.SCENARIOS['LOW'], dict(REPLACEMENT_VARIANT='LOW')),
             'REF': (N.SCENARIOS['REF'], dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0)),
             'HIGH': (N.SCENARIOS['HIGH'], dict(REPLACEMENT_VARIANT='HIGH'))}
IDENTITY_RTOL = 1e-9
GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.05), 2)     # solution space: 0-100% in 5% steps
BRENTQ_XTOL = 1e-15
M6 = 1e6


# ============================================================
# CONTEXT: one projection state per scenario
# ============================================================
def boundaries():
    """B_AR and B_AtP (kg/yr) by year 2026-2050 for the Reference, and P_NZ, from outputs/pb_annual.csv."""
    a = pd.read_csv(FILE_PB_ANNUAL)
    a = a[(a['scenario'] == REFERENCE) & (a['year'] >= WINDOW[0]) & (a['year'] <= WINDOW[1])].set_index('year')
    if list(a.index) != list(range(WINDOW[0], WINDOW[1] + 1)):
        raise SystemExit(f'{FILE_PB_ANNUAL}: Reference boundaries incomplete over {WINDOW}.')
    return a['B_AR_kgCO2e'].values, a['B_AtP_kgCO2e'].values, a['P_NZ'].values


def base_context(B, scenario, bounds):
    """Everything a lever run needs from one projection state (no copy of the data is changed)."""
    projection = validation.projection
    fi = B['fwd_inputs']
    fy = np.asarray(B['forecast_years'])
    typ = list(B['typ_names'])
    pop = B['df_forecast']['PopTotal_50th'].values
    growth = B['df_forecast']['PopGrowth_50th'].clip(lower=0).values
    hh = B['households_forecast']['50th']
    ji = B['join_info']['50th']
    if fi['soil_on_replacement'] or fi['dev_2025'] != 0.0:
        raise SystemExit('pathways: written for SOIL_ON_REPLACEMENT = False and the market_excess join.')
    b_ar, b_atp, p_nz = bounds
    if not np.allclose(pop[1:], p_nz, rtol=1e-12, atol=0):
        raise SystemExit(f'{scenario}: NZ population differs from the pb_annual.csv Reference path.')
    E_nojoin = engine.forward(pop, hh, growth, **fi)          # projection l. 1543 (input to market_excess)
    prof = {t: B['EV_PROFILE'][B['EV_PROFILE']['Typology'] == t].reset_index(drop=True) for t in typ}
    after = np.arange(fy[-1] + 1, fy[-1] + int(B['EV_PROFILE']['Age'].max()) + 1)
    fac = {(t, k): EV.row_factors(prof[t], after, projection.DECARB_MODE, projection.DECARB_ITEM_CASE, projection.DECARB_A45,
                                  hold=hold)
           for t in typ for k, hold in (('upper', '2025'), ('lower', '2050'))}
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    a45 = {t: float(B['MAT_STAGE']['A4-A5'][t].sum()) for t in typ}
    return dict(
        scenario=scenario, B=B, years=fy, typ=typ, pop=pop, growth=growth, hh=hh,
        fwd_inputs=fi, size_ref=B['size_ref'], olf=B['OLF_USED'], v0=float(B['v_forward']), rate_demol=float(B['demolition_rate']),
        rate_unc=np.asarray(fi['rate_unc'], float), long_run_residual=float(B['unconsented_rate']),
        held_shares=B['held_shares'], a13_2025=a13, red13=B['RED13_TOT'], a45_2025=a45, red45=B['RED45_TOT'],
        join=ji['join'], join_redev=ji['redev'], O26=float(ji['O26']), rho=float(B['rho_other']),
        gap_ref=projection.OVERBUILD_GAP_REF, E_nojoin=E_nojoin, profile=prof, committed_factors=fac,
        c14={t: float(B['stage_int'].loc['C1-C4', t]) for t in typ}, soil=B['SOIL_INTENSITY'],
        events=fi['events'], b_ar=b_ar, b_atp=b_atp)


# ============================================================
# ONE RUN AND ITS METRICS
# ============================================================
def run(ctx, params, active, ramp_name=None, l5_apartments_held=False):
    """engine.forward with the levers in `active` ({lever: 'moderate' | 'ambitious'})."""
    fi, join, redev, info = LV.apply(ctx, params, active, ramp_name, ctx['E_nojoin'], l5_apartments_held)
    E = engine.forward(ctx['pop'], ctx['hh'], ctx['growth'], join=join, join_redev=redev, **fi)
    return dict(E=E, inputs=fi, info=info, active=dict(active), ramp=ramp_name or RAMP_ADOPTED,
                l5_apartments_held=l5_apartments_held, scenario=ctx['scenario'])


def committed(ctx, gfa_t):
    """Committed after 2050 (kt): the 2026-2050 cohorts' later replacements and repaints
    (events.committed; upper: 2025 factors, lower: 2050 factors held) and all their C1-C4
    (2025 factors), as projection l. 2274-2289, with this run's floor area by typology."""
    b = {'upper': 0.0, 'lower': 0.0}
    for k, t in enumerate(ctx['typ']):
        for key in b:
            b[key] += EV.committed(gfa_t[k], ctx['years'], ctx['profile'][t], ctx['committed_factors'][(t, key)])
    c = sum(gfa_t[k][1:].sum() * ctx['c14'][t] for k, t in enumerate(ctx['typ']))
    return dict(B_upper_kt=b['upper'] / M6, B_lower_kt=b['lower'] / M6, C_kt=c / M6,
                upper_kt=(b['upper'] + c) / M6, lower_kt=(b['lower'] + c) / M6)


def soil_by_year(ctx, E, soil_path=None):
    """Soil carbon by year (kg): soil factor x floor area x soil-bearing share. soil_path: a run's own
    factor by typology and year (TL5); None = the Reference factor."""
    if soil_path is None:
        s = np.array([ctx['soil'][t] for t in ctx['typ']])
        return (s[:, None] * E['gfa_t']).sum(axis=0) * E['soil_share']
    s = np.array([np.asarray(soil_path[t], float) for t in ctx['typ']])
    return (s * E['gfa_t']).sum(axis=0) * E['soil_share']


def _soil_path(R):
    return R['info'].get('soil_path')


def carbon_parts(ctx, R):
    """Annual carbon split by cohort: upfront by construction year (soil and non-soil) and
    in-window events by cohort year i and occurrence year j (ev[i, j]). Sum = E['carbon']."""
    E = R['E']
    soil = soil_by_year(ctx, E, _soil_path(R))
    up = E['upfront']
    ev = np.zeros((len(ctx['years']), len(ctx['years'])))
    for k, t in enumerate(ctx['typ']):
        ev += E['gfa_t'][k][:, None] * ctx['events'][t]
    rebuilt = up + ev.sum(axis=0)
    if not np.allclose(rebuilt, E['carbon'], rtol=1e-12, atol=1e-6):
        raise SystemExit('carbon_parts: upfront + events by cohort does not reproduce the annual carbon.')
    return dict(up=up, soil=soil, nonsoil=up - soil, ev=ev)


def metrics(ctx, R, label, setting):
    """Every reported quantity of one run (window 2026-2050 unless stated)."""
    E, info, fi = R['E'], R['info'], R['inputs']
    f = slice(1, None)
    gfa_t = E['gfa_t']
    I = E['carbon'][f]
    soil = soil_by_year(ctx, E, _soil_path(R))[f]
    a13 = sum((gfa_t[k] * info['a13'][t])[f].sum() for k, t in enumerate(ctx['typ']))
    a45 = sum((gfa_t[k] * (ctx['a45_2025'][t] - np.asarray(ctx['red45'][t], float)))[f].sum()
              for k, t in enumerate(ctx['typ']))
    up = E['upfront'][f].sum()
    if not math.isclose(a13 + a45 + soil.sum(), up, rel_tol=1e-12):
        raise SystemExit(f'{label}: A1-A3 + A4-A5 + soil does not equal upfront.')
    com = committed(ctx, gfa_t)
    v_impl = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
    dwell = E['dwell_in_scope'][f]
    built_all = engine.requirement(E)[f]
    loe_ar, loe_atp = aesa.cumulative_loe(I, ctx['b_ar']), aesa.cumulative_loe(I, ctx['b_atp'])
    gfa = gfa_t[:, f].sum()
    S = E['pop'] / E['hh']
    size = fi['size']
    size_minus_occ = min(float((np.broadcast_to(np.asarray(size[t], float), S.shape) - S * np.asarray(fi['olf'][t], float))[f].min())
                         for t in ctx['typ'])
    held = R['info'].get('l1_held')
    row = dict(run=label, scenario=ctx['scenario'], setting=setting, levers=LV.label(R['active']),
               adoption=R['ramp'], l5_apartments_held=R['l5_apartments_held'],
               gfa_Mm2=gfa / M6, gfa_2027_2050_Mm2=gfa_t[:, 2:].sum() / M6,
               **{f'gfa_{t}_Mm2': gfa_t[k][f].sum() / M6 for k, t in enumerate(ctx['typ'])},
               carbon_kt=I.sum() / M6, upfront_kt=up / M6, b_inwindow_kt=E['b_t'][:, f].sum() / M6,
               soil_kt=soil.sum() / M6, a13_kt=a13 / M6, a45_kt=a45 / M6,
               carbon_excl_soil_kt=(I.sum() - soil.sum()) / M6,
               committed_lower_kt=com['lower_kt'], committed_upper_kt=com['upper_kt'],
               committed_B_lower_kt=com['B_lower_kt'], committed_B_upper_kt=com['B_upper_kt'],
               committed_C_kt=com['C_kt'],
               committed_years_B_AR_2050_lower=com['lower_kt'] * M6 / ctx['b_ar'][-1],
               committed_years_B_AR_2050_upper=com['upper_kt'] * M6 / ctx['b_ar'][-1],
               B_AR_kt=ctx['b_ar'].sum() / M6, B_AtP_kt=ctx['b_atp'].sum() / M6,
               LoE_AR=loe_ar, LoE_AtP=loe_atp,
               remaining_reduction_AR=1.0 - 1.0 / loe_ar, remaining_reduction_AtP=1.0 - 1.0 / loe_atp,
               dwellings_built=dwell.sum(), dwellings_built_all_categories=built_all.sum(),
               dwellings_built_min_year=float(min(dwell.min(), built_all.min())),
               mean_dwelling_size_m2=gfa / dwell.sum(),
               carbon_per_m2_kg=I.sum() / gfa, carbon_per_dwelling_t=I.sum() / dwell.sum() / 1e3,
               implied_vacancy_min=float(v_impl[f].min()), implied_vacancy_2050=float(v_impl[-1]),
               implied_vacancy_max=float(v_impl[f].max()),
               stock_vacancy_2050=float(np.broadcast_to(E['v'], E['hh'].shape)[-1]),
               D_minus_occ_min_m2=float((E['D'] - E['occ'])[f].min()),
               extra_clip_max_m2=float(np.abs(E['extra_clip'][f]).max()),
               attached_share_2050=float(sum(fi['shares'][t].iloc[-1] for t in LV.ATTACHED)),
               near_term_join_dwellings=float(E['join'][f].sum()),
               existing_dwellings_released=float(-np.minimum(E['change'][f], 0.0).sum()),
               vacancy_change_dwellings=float(E['change'][f].sum()),
               size_minus_occupied_min_m2=size_minus_occ,
               l1_held_typology_years=int(sum(h[f].sum() for h in held.values())) if held else 0)
    return row


def annual_rows(ctx, R, label):
    E = R['E']
    v_impl = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
    soil = soil_by_year(ctx, E, _soil_path(R))
    rows = []
    for i, y in enumerate(ctx['years']):
        if y < WINDOW[0]:
            continue
        j = i - 1
        rows.append(dict(run=label, scenario=ctx['scenario'], year=int(y),
                         carbon_kt=E['carbon'][i] / M6, upfront_kt=E['upfront'][i] / M6,
                         b_kt=E['b_t'][:, i].sum() / M6, soil_kt=soil[i] / M6,
                         gfa_Mm2=E['gfa_t'][:, i].sum() / M6,
                         **{f'gfa_{t}_Mm2': E['gfa_t'][k, i] / M6 for k, t in enumerate(ctx['typ'])},
                         dwellings_built=E['dwell_in_scope'][i], dwelling_size_m2=E['D'][i],
                         occupied_area_m2=E['occ'][i], implied_vacancy=v_impl[i],
                         stock_vacancy=float(np.broadcast_to(E['v'], E['hh'].shape)[i]),
                         vacancy_change_dwellings=E['change'][i], near_term_join_dwellings=E['join'][i],
                         B_AR_kt=ctx['b_ar'][j] / M6, B_AtP_kt=ctx['b_atp'][j] / M6,
                         LoE_AR=E['carbon'][i] / ctx['b_ar'][j], LoE_AtP=E['carbon'][i] / ctx['b_atp'][j]))
    return rows


# ============================================================
# DEMAND BANDS (projection bookkeeping, l. 1555-1575 and 1700-1745)
# ============================================================
# definition 'with_retirement_villages' (as projection.export_results) and 'in_scope' (the band
# figures): naming.BANDS_WITH_RETIREMENT_VILLAGES / BANDS_IN_SCOPE, labels naming.band_data_label
BAND_ORDER = [N.band_data_label(b) for b in N.BANDS_WITH_RETIREMENT_VILLAGES]
_IN_SCOPE_KEYS = {'growth': ('growth',), 'smaller_households': ('hs_pos',), 'extra_space': ('extra',),
                  'vacancy': ('vac',), 'replacement': ('repl', 'unc'), 'redevelopment': ('wave',),
                  'overbuild_2026': ('join',), 'maintenance': ('bev',)}
FIG_BANDS = [(N.band_data_label(b), _IN_SCOPE_KEYS[b]) for b in N.BANDS_IN_SCOPE]


def band_arrays(ctx, R):
    """Annual floor area (m2) and carbon (kg) by demand band, as projection: the redevelopment
    wave is the run's residual path above the long-run residual, x last year's stock x D."""
    E, fi = R['E'], R['inputs']
    D = E['D']
    wave = (np.asarray(fi['rate_unc'], float) - ctx['long_run_residual']) * E['prev'] * D
    g = dict(growth=E['growth'], hs_pos=E['hs_pos'], extra=E['extra'], vac=(E['allow'] + E['change']) * D,
             repl=E['demol'] * D, unc=E['unc'] * D - wave, wave=wave, join=E['join'] * D + E['gfa_adj'],
             rv=E['rv'] * D)
    one = np.ones(len(ctx['years']))
    repl_u = np.clip(E['demol'] + E['unc'] + E['join_redev'], 0.0, None)
    gross_u = np.maximum(E['d_hh'], 0.0) + E['allow'] + E['change'] + E['demol'] + E['unc'] + E['join']
    jg = E['join'] * D + E['gfa_adj']
    frac = dict(growth=one, hs_pos=one, extra=one, vac=one, repl=0.0 * one, unc=0.0 * one, wave=0.0 * one,
                join=np.divide((E['join'] - E['join_redev']) * D + E['gfa_adj'], jg, out=one.copy(), where=jg != 0),
                rv=1.0 - np.divide(repl_u, gross_u, out=np.zeros_like(one), where=gross_u != 0))
    shares = fi['shares']
    sp = _soil_path(R)
    if sp is None:
        mat = {t: np.asarray(fi['intensity'][t], float) - ctx['soil'][t] for t in ctx['typ']}
        soil = ctx['soil']
    else:                              # T5: material part before the soil adjustment, soil on its own path
        mat = {t: np.asarray(R['info']['intensity_material'][t], float) for t in ctx['typ']}
        soil = {t: np.asarray(sp[t], float) for t in ctx['typ']}
    c = {k: sum(v * shares[t].values * mat[t] + v * shares[t].values * frac[k] * soil[t] for t in ctx['typ'])
         for k, v in g.items()}
    c['bev'] = E['b_t'].sum(axis=0)
    return g, c


def band_rows(ctx, R, label):
    """Two definitions: 'with_retirement_villages' (projection.export_results: every band incl. the
    negative retirement-village band; carbon excludes maintenance) and 'in_scope' (the band figures:
    retirement villages removed from every band in proportion; demolition + residual one band;
    maintenance as a carbon band)."""
    g, c = band_arrays(ctx, R)
    f = slice(1, None)
    keys = ['growth', 'hs_pos', 'extra', 'vac', 'repl', 'unc', 'wave', 'join', 'rv']
    rows = [dict(run=label, scenario=ctx['scenario'], definition='with_retirement_villages', band=b,
                 gfa_Mm2=g[k][f].sum() / M6, carbon_kt=c[k][f].sum() / M6) for b, k in zip(BAND_ORDER, keys)]
    E = R['E']
    tot_g, tot_c = E['total'][f], E['carbon'][f]
    raw_g = {b: sum((g[k] if k != 'bev' else 0.0 * g['growth']) for k in ks)[f] for b, ks in FIG_BANDS}
    raw_c = {b: sum(c[k] for k in ks)[f] for b, ks in FIG_BANDS}
    sg, sc = sum(raw_g.values()), sum(raw_c.values())
    fg = np.divide(tot_g, sg, out=np.zeros_like(tot_g), where=sg != 0)     # 0 / 0 only in banked zero-building years (TL)
    fc = np.divide(tot_c, sc, out=np.zeros_like(tot_c), where=sc != 0)
    rows += [dict(run=label, scenario=ctx['scenario'], definition='in_scope', band=b,
                  gfa_Mm2=(raw_g[b] * fg).sum() / M6, carbon_kt=(raw_c[b] * fc).sum() / M6) for b, _ in FIG_BANDS]
    return rows


# ============================================================
# ATTRIBUTION
# ============================================================
def subsets(items):
    return [frozenset(s) for n in range(len(items) + 1) for s in itertools.combinations(items, n)]


def shapley(value, players=LV.LEVERS):
    """Shapley value of each player for the REDUCTION v(empty) - v(all), computed in exact
    rational arithmetic on the float run values (Fraction), so the efficiency property
    sum_i phi_i = v(empty) - v(all) holds exactly. value: {frozenset: float}."""
    n = len(players)
    v = {k: Fraction(x) for k, x in value.items()}
    phi = {}
    for i in players:
        s = Fraction(0)
        for S in subsets([p for p in players if p != i]):
            wgt = Fraction(math.factorial(len(S)) * math.factorial(n - len(S) - 1), math.factorial(n))
            s += wgt * (v[S] - v[S | {i}])
        phi[i] = s
    return phi


# ============================================================
# BACK-CAST AND SOLUTION SPACE (carbon linear in floor area and in intensity)
# ============================================================
def linear_split(ctx, R):
    """Annual carbon (kg, 2026-2050) = fixed + later_nonsoil + later_soil, where `fixed` is
    the 2026 cohort (its upfront and its in-window events) and `later_*` the 2027-2050
    cohorts: their upfront (non-soil / soil) and their in-window events (non-soil)."""
    p = carbon_parts(ctx, R)
    n = len(ctx['years'])
    first = np.zeros(n)
    first[1] = p['up'][1]
    fixed = first + p['ev'][1]
    later_nonsoil = np.where(np.arange(n) >= 2, p['nonsoil'], 0.0) + p['ev'][2:].sum(axis=0)
    later_soil = np.where(np.arange(n) >= 2, p['soil'], 0.0)
    f = slice(1, None)                                        # 2026-2050 (2025 is the anchor year)
    if not np.allclose((fixed + later_nonsoil + later_soil)[f], R['E']['carbon'][f], rtol=1e-12, atol=1e-6):
        raise SystemExit('linear_split does not reproduce the annual carbon.')
    return dict(fixed=fixed[f], later_nonsoil=later_nonsoil[f], later_soil=later_soil[f],
                gfa_later=R['E']['gfa_t'][:, 2:].sum())


def scaled_carbon(split, k_demand, k_intensity=1.0):
    """Annual carbon with every 2027-2050 cohort's floor area x k_demand and its non-soil
    carbon per m2 x k_intensity (2026 and its events unchanged)."""
    return split['fixed'] + k_demand * (k_intensity * split['later_nonsoil'] + split['later_soil'])


def backcast(ctx, R, label):
    """k on all 2027-2050 construction such that cumulative LoE AR = 1 (brentq); AtP
    minimum at k = 0."""
    s = linear_split(ctx, R)
    bar, batp = ctx['b_ar'].sum(), ctx['b_atp'].sum()
    loe = lambda k, b: scaled_carbon(s, k).sum() / b
    lo_ar, hi_ar = loe(0.0, bar), loe(1.0, bar)
    out = dict(run=label, LoE_AR_at_k1=hi_ar, LoE_AtP_at_k1=loe(1.0, batp),
               LoE_AR_min_k0=lo_ar, LoE_AtP_min_k0=loe(0.0, batp),
               carbon_fixed_2026_cohort_kt=s['fixed'].sum() / M6,
               carbon_2027_2050_cohorts_kt=(s['later_nonsoil'] + s['later_soil']).sum() / M6,
               gfa_2027_2050_Mm2=s['gfa_later'] / M6)
    if lo_ar < 1.0 < hi_ar:
        k = brentq(lambda k: loe(k, bar) - 1.0, 0.0, 1.0, xtol=BRENTQ_XTOL, rtol=4 * np.finfo(float).eps)
        k_closed = (bar - s['fixed'].sum()) / (s['later_nonsoil'] + s['later_soil']).sum()
        out.update(k_AR=k, k_AR_closed_form=k_closed, cut_AR=1.0 - k, LoE_AR_at_k=loe(k, bar),
                   gfa_2027_2050_at_k_Mm2=k * s['gfa_later'] / M6)
    else:
        out.update(k_AR=None, cut_AR=None, note_AR='LoE AR = 1 not bracketed by k in [0, 1]')
    out['AtP_attainable'] = bool(out['LoE_AtP_min_k0'] <= 1.0)
    return out, s


def solution_space(split0, bar, batp):
    rows = []
    for d in GRID:
        for i in GRID:
            I = scaled_carbon(split0, 1.0 - d, 1.0 - i).sum()
            rows.append(dict(demand_reduction=float(d), intensity_reduction=float(i), carbon_kt=I / M6,
                             LoE_AR=I / bar, LoE_AtP=I / batp))
    return pd.DataFrame(rows)


def effective_coordinates(split, split0):
    """demand = 1 - GFA_P / GFA_0 (2027-2050 cohorts); intensity = 1 - (C_P / GFA_P) / (C_0 / GFA_0),
    C = non-soil carbon of the 2027-2050 cohorts within the window (upfront + in-window events)."""
    d = 1.0 - split['gfa_later'] / split0['gfa_later']
    c, c0 = split['later_nonsoil'].sum(), split0['later_nonsoil'].sum()
    i = 1.0 - (c / split['gfa_later']) / (c0 / split0['gfa_later'])
    return float(d), float(i)


# ============================================================
# MAIN
# ============================================================
def load_factors_building():
    return pd.read_csv(validation.projection.FILE_FACTORS_BUILDING)


def boss_state(scenario):
    with contextlib.redirect_stdout(io.StringIO()):
        return validation.run_boss(**SCENARIOS[scenario][1])


def run_name(pathway_or_lever, setting, ramp_name=None, apt_held=False):
    """'REF' (a variant id: no lever), 'P3-moderate', 'L1-ambitious', 'P5-moderate-by2045',
    'P4-ambitious-apartments-held'."""
    if pathway_or_lever in N.SCENARIOS:
        return pathway_or_lever
    return (f'{pathway_or_lever}-{setting}' + (f'-{ramp_name}' if ramp_name else '')
            + ('-apartments-held' if apt_held else ''))


def shapley_rows(value, players, setting, metric, level, groups):
    phi = shapley(value, players)
    full = frozenset(players)
    total = Fraction(value[frozenset()]) - Fraction(value[full])
    rows = [dict(level=level, setting=setting, metric=metric, player=pl, name=groups[pl], reduction=float(phi[pl]),
                 share_of_reference_minus_P5=float(phi[pl] / total)) for pl in players]
    return rows, (phi, total)


def compute(scenarios=tuple(SCENARIOS), verbose=True):
    """All runs. Returns a dict of tables and the objects the figures and tests need."""
    t0 = time.time()
    bounds = boundaries()
    states = {s: boss_state(s) for s in scenarios}
    if REFERENCE not in states:
        raise ValueError('The Reference (REF) is required.')
    params = LV.resolve(states[REFERENCE], load_factors_building(), validation.projection)
    LV.stop_checks(params)
    ctxs = {s: base_context(states[s], s, bounds) for s in scenarios}
    cache = {}

    def get(scen, active, ramp_name=None, apt_held=False):
        key = (scen, LV.label(active), ramp_name or RAMP_ADOPTED, apt_held)
        if key not in cache:
            cache[key] = run(ctxs[scen], params, active, ramp_name, apt_held)
        return cache[key]

    named = [(REFERENCE, REFERENCE, '', {}, None, False)]       # (name, scenario, setting, active, ramp, apt_held)
    for s in LV.SETTINGS:
        for L in LV.LEVERS:
            named.append((run_name(L, s), REFERENCE, s, {L: s}, None, False))
    for s in LV.SETTINGS:
        for P in ('P1', 'P2', 'P3', 'P4', 'P5'):
            named.append((run_name(P, s), REFERENCE, s, LV.pathway_levers(P, s), None, False))
    for scen in scenarios:
        if scen != REFERENCE:
            named.append((scen, scen, '', {}, None, False))       # the variant without levers
            for s in LV.SETTINGS:
                named.append((run_name('P5', s), scen, s, LV.pathway_levers('P5', s), None, False))
        for rs in LV.ADOPTION_SENSITIVITIES:
            for s in LV.SETTINGS:
                named.append((run_name('P5', s, rs['name']), scen, s, LV.pathway_levers('P5', s), rs['name'], False))
    for s in LV.SETTINGS:                                        # L5 sensitivity: apartments held at r = 1
        for P in ('P4', 'P5'):
            named.append((run_name(P, s, apt_held=True), REFERENCE, s, LV.pathway_levers(P, s), None, True))
    rows, annual, bands = [], [], []
    for name, scen, s, active, rn, ah in named:
        R = get(scen, active, rn, ah)
        rows.append(metrics(ctxs[scen], R, name, s))
        annual += annual_rows(ctxs[scen], R, name)
        bands += band_rows(ctxs[scen], R, name)
    runs_df = pd.DataFrame(rows)
    p0 = runs_df[runs_df['run'] == runs_df['scenario']].set_index('scenario')      # each variant without levers
    for col in ('carbon_kt', 'LoE_AR', 'LoE_AtP', 'gfa_Mm2', 'committed_lower_kt', 'committed_upper_kt'):
        runs_df[f'delta_{col}_vs_reference_pct'] = [100.0 * (r[col] / p0.loc[r['scenario'], col] - 1.0)
                                                   for _, r in runs_df.iterrows()]
    bands_df = pd.DataFrame(bands)
    b0 = bands_df[bands_df['run'] == bands_df['scenario']].set_index(['scenario', 'definition', 'band'])
    for col in ('gfa_Mm2', 'carbon_kt'):
        bands_df[f'delta_{col}_vs_reference'] = [r[col] - b0.loc[(r['scenario'], r['definition'], r['band']), col]
                                                 for _, r in bands_df.iterrows()]

    # ---- Shapley: four pathways (P1-P4; 16 subsets) and five levers (32 subsets), Reference --
    ref = ctxs[REFERENCE]
    shap_p, shap_l, shap_runs, shap_exact = [], [], [], {}
    pnames = {P: LV.PATHWAY_NAMES[P] for P in LV.PATHWAYS}
    for s in LV.SETTINGS:
        for level, players, names, expand in (
                ('pathways', tuple(LV.PATHWAYS), pnames, lambda S: [L for P in S for L in LV.PATHWAYS[P]]),
                ('levers', LV.LEVERS, LV.LEVER_NAMES, lambda S: list(S))):
            vals = {'carbon_kt': {}, 'LoE_AR': {}}
            for S in subsets(players):
                active = {L: s for L in expand(S)}
                m = metrics(ref, get(REFERENCE, active), LV.label(active), s)
                vals['carbon_kt'][S] = m['carbon_kt']
                vals['LoE_AR'][S] = m['LoE_AR']
                shap_runs.append(dict(level=level, setting=s, subset='+'.join(p for p in players if p in S) or 'none',
                                      levers=LV.label(active), n_players=len(S), carbon_kt=m['carbon_kt'],
                                      LoE_AR=m['LoE_AR'], LoE_AtP=m['LoE_AtP'], gfa_Mm2=m['gfa_Mm2']))
            for metric, v in vals.items():
                r_, ex = shapley_rows(v, players, s, metric, level, names)
                (shap_p if level == 'pathways' else shap_l).extend(r_)
                shap_exact[(level, s, metric)] = ex

    # ---- back-cast (P5 Moderate / Ambitious; the Reference) and solution space (Reference) ----
    R0 = get(REFERENCE, {})
    bc0, split0 = backcast(ref, R0, REFERENCE)
    gfa0_later = split0['gfa_later']
    bar, batp = ref['b_ar'].sum(), ref['b_atp'].sum()
    bcs, bc_points = {REFERENCE: bc0}, [dict(run=f'{REFERENCE} back-cast', demand_reduction=1.0 - bc0['k_AR'],
                                             intensity_reduction=0.0)]
    for s in LV.SETTINGS:
        R5 = get(REFERENCE, LV.pathway_levers('P5', s))
        bc, sp = backcast(ref, R5, f'P5-{s}')
        if bc['k_AR'] is not None:
            bc['equivalent_cut_vs_reference_floor_area'] = 1.0 - bc['k_AR'] * sp['gfa_later'] / gfa0_later
            bc['equivalent_cut_vs_reference_carbon_2027_2050_cohorts'] = 1.0 - (
                bc['k_AR'] * (sp['later_nonsoil'] + sp['later_soil']).sum()
                / (split0['later_nonsoil'] + split0['later_soil']).sum())
            d, i = effective_coordinates(sp, split0)
            bc_points.append(dict(run=f'P5-{s} back-cast', demand_reduction=1.0 - bc['k_AR'] * (1.0 - d),
                                  intensity_reduction=i))
        bcs[f'P5-{s}'] = bc
    space = solution_space(split0, bar, batp)
    markers = []
    for P in ('P1', 'P2', 'P3', 'P4', 'P5'):
        for s in LV.SETTINGS:
            Rp = get(REFERENCE, LV.pathway_levers(P, s))
            d, i = effective_coordinates(linear_split(ref, Rp), split0)
            run_loe = Rp['E']['carbon'][1:].sum() / bar
            markers.append(dict(run=f'{P}-{s}', demand_reduction=d, intensity_reduction=i, LoE_AR_run=run_loe,
                                LoE_AR_on_grid_at_coordinates=scaled_carbon(split0, 1.0 - d, 1.0 - i).sum() / bar,
                                LoE_AtP_run=run_loe * bar / batp))
    backcast_out = dict(
        run_mode=RUN_MODE, method='uniform factor k on the floor area by typology of every 2027-2050 cohort '
        '(construction-year upfront and its in-window events scale with k; 2026 and its events fixed); '
        'scipy.optimize.brentq on [0, 1], xtol 1e-15',
        B_AR_kt=bar / M6, B_AtP_kt=batp / M6, solution_space_markers=markers, backcast_points=bc_points,
        AtP_note=('not attainable within 2026-2050' if not bcs[REFERENCE]['AtP_attainable'] else 'attainable'), **bcs)

    # ---- diagnostics: L1 sizes held, released dwellings, end-of-ramp step of P2 --------------
    diag = {}
    a_ref = pd.DataFrame(annual)
    a_ref = a_ref[a_ref['scenario'] == REFERENCE].set_index(['run', 'year'])
    w = LV.ramp(ref['years'])
    for s in LV.SETTINGS:
        nm = run_name('P2', s)
        c35, c36 = a_ref.loc[(nm, 2035), 'carbon_kt'], a_ref.loc[(nm, 2036), 'carbon_kt']
        d35, d36 = a_ref.loc[(nm, 2035), 'dwellings_built'], a_ref.loc[(nm, 2036), 'dwellings_built']
        p35, p36 = a_ref.loc[(REFERENCE, 2035), 'carbon_kt'], a_ref.loc[(REFERENCE, 2036), 'carbon_kt']
        diag[f'end_of_ramp_step_{nm}'] = dict(
            w_2035_minus_w_2034=float(w[10] - w[9]), carbon_2035_kt=c35, carbon_2036_kt=c36,
            carbon_step_kt=c36 - c35, carbon_step_pct=100 * (c36 / c35 - 1), reference_carbon_step_kt=p36 - p35,
            step_relative_to_reference_kt=(c36 - c35) - (p36 - p35), dwellings_step=d36 - d35)
    out = dict(params=params, runs=runs_df, annual=pd.DataFrame(annual), bands=bands_df,
               shapley_pathways=pd.DataFrame(shap_p), shapley_levers=pd.DataFrame(shap_l),
               shapley_runs=pd.DataFrame(shap_runs), shapley_exact=shap_exact, backcast=backcast_out,
               space=space, diagnostics=diag, ctxs=ctxs, states=states, cache=cache, get=get,
               seconds=time.time() - t0)
    if verbose:
        print(f'pathways: {len(cache)} engine runs in {out["seconds"]:.1f} s')
    return out


def checks(res):
    """Identity of the no-lever run with the published Reference run, and the STOP conditions.
    The published files carry the release names (naming.identifier)."""
    ctx = res['ctxs'][REFERENCE]
    B = ctx['B']
    R0 = res['get'](REFERENCE, {})
    E0, Eb = R0['E'], B['engine_out']['50th']
    rel = lambda a, b: float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float))
                                    / np.maximum(np.abs(np.asarray(b, float)), 1e-300)))
    rep = {}
    rep['annual_carbon'] = rel(E0['carbon'][1:], B['carbon_total_typ'].sum(axis=1).values[1:])
    rep['gfa_by_typology'] = rel(E0['gfa_t'][:, 1:], Eb['gfa_t'][:, 1:])
    bres = json.load(open(FILE_BOSS_RESULTS))
    ident = N.identifier
    r0 = res['runs'][(res['runs']['run'] == REFERENCE) & (res['runs']['scenario'] == REFERENCE)].iloc[0]
    for k in ('carbon_kt', 'upfront_kt', 'soil_kt', 'b_inwindow_kt', 'gfa_Mm2'):
        rep[k] = abs(r0[k] / bres[ident(k)] - 1)
    rep['annual_carbon_json'] = rel(E0['carbon'][1:] / M6, bres['annual']['carbon_kt'][1:])
    for k in ('lower_kt', 'upper_kt', 'B_lower_kt', 'B_upper_kt', 'C_kt'):
        rep[f'committed_{k}'] = abs(r0[f'committed_{k}'] / bres['committed'][ident(k)] - 1)
    bd = res['bands']
    b0 = bd[(bd['run'] == REFERENCE) & (bd['scenario'] == REFERENCE)
            & (bd['definition'] == 'with_retirement_villages')].set_index('band')
    for x in bres['demand_bands']:
        for col in ('gfa_Mm2', 'carbon_kt'):
            rep[f"band {x['band']} {col}"] = abs(b0.loc[x['band'], col] - x[ident(col)]) / max(abs(x[ident(col)]), 1e-12)
    pbr = json.load(open(FILE_PB_RESULTS))
    for scen in res['ctxs']:
        rs = res['runs'][(res['runs']['run'] == scen) & (res['runs']['scenario'] == scen)].iloc[0]
        for col in ('LoE_AR', 'LoE_AtP'):
            rep[f'{scen} {col}'] = abs(rs[col] / pbr['deterministic'][scen][col] - 1)
        rep[f'{scen} carbon vs aesa results'] = abs(rs['carbon_kt'] / pbr['deterministic'][scen]['I_kt'] - 1)
    worst = max(rep, key=rep.get)
    if rep[worst] > IDENTITY_RTOL:
        raise SystemExit(f'STOP: identity not reproduced: {worst} relative difference {rep[worst]:.3e}')
    runs = res['runs']
    bad = runs[(runs['D_minus_occ_min_m2'] < 0) | (runs['extra_clip_max_m2'] > 0) | (runs['size_minus_occupied_min_m2'] < 0)]
    if len(bad):
        raise SystemExit(f'STOP: dwelling size below occupied area in {list(bad["run"] + " " + bad["scenario"])}')
    badv = runs[runs['implied_vacancy_min'] < LV.L2_VACANCY_FLOOR]
    if len(badv):
        raise SystemExit(f'STOP: implied vacancy below {LV.L2_VACANCY_FLOOR:.1%} in {list(badv["run"] + " " + badv["scenario"])}')
    badd = runs[runs['dwellings_built_min_year'] < 0]
    if len(badd):
        raise SystemExit(f'STOP: negative dwellings built in {list(badd["run"] + " " + badd["scenario"])}')
    for key, (phi, total) in res['shapley_exact'].items():
        if sum(phi.values()) != total:
            raise SystemExit(f'Shapley efficiency fails {key}.')
    return rep


def to_json(o):
    if isinstance(o, dict):
        return {str(k): to_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_json(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return [to_json(v) for v in o.tolist()]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def _csv(df, name):
    N.columns(df).to_csv(layout.writing(os.path.join(OUT, name)), index=False)


def _json(obj, name):
    with open(layout.writing(os.path.join(OUT, name)), 'w') as f:
        json.dump(N.keys(to_json(obj)), f, indent=2)


def write(res, identity):
    _csv(res['runs'], 'runs.csv')
    _csv(res['annual'], 'annual.csv')
    _csv(res['bands'], 'bands.csv')
    _csv(res['shapley_pathways'], 'shapley_pathways.csv')
    _csv(res['shapley_levers'], 'shapley_levers.csv')
    _csv(res['shapley_runs'], 'shapley_subsets.csv')
    _csv(res['space'], 'solution_space.csv')
    _json(res['backcast'], 'backcast.json')
    lv = dict(res['params'], diagnostics=res['diagnostics'], run_mode=RUN_MODE,
              identity_max_rel_diff=max(identity.values()), identity_checks=identity, sources=LV.SOURCES)
    _json(lv, 'levers.json')


# ============================================================
# THEORETICAL LIMIT TL (PATHWAYS v3; levers.apply_tl) -- a thought experiment, not a pathway
# ============================================================
T_RUNS = ('TL', 'TL-gradual')
T_ZERO_TOL_DWELLINGS = 1e-6     # floating-point noise of built = req + (0 - req) in banked zero years (~1e-12)
T_ZERO_TOL_M2 = 1e-3


def bank(raw):
    """Banking rule (TL): dwellings built can never be negative. raw_t = the requirement of the year
    (new households + vacancy allowance + vacancy change + removals + absorbed near-term excess),
    negative when the release of vacant / surplus dwellings exceeds it. Unused release is carried
    forward and used before any new building, until exhausted:

        D_t = raw_t - bank_{t-1};  built_t = max(0, D_t);  bank_t = max(0, -D_t)

    Index 0 (2025, the anchor year) is passed through. Returns built, bank, added, used (arrays)."""
    raw = np.asarray(raw, float)
    n = len(raw)
    built, bnk, added, used = raw.copy(), np.zeros(n), np.zeros(n), np.zeros(n)
    prev = 0.0
    for i in range(1, n):
        d = raw[i] - prev
        built[i] = max(0.0, d)
        bnk[i] = max(0.0, -d)
        added[i] = max(0.0, -raw[i])
        used[i] = min(prev, max(raw[i], 0.0))
        prev = bnk[i]
    return dict(built=built, bank=bnk, added=added, used=used)


def run_tl(ctx, params, pT, comps, ramp_name=LV.TL_FROM2027):
    """A TL-family run. 1) the TL inputs (levers.apply_tl); 2) the requirement without a join; 3) the
    banking rule on requirement + absorbed near-term excess; 4) engine.forward with the stock-adding
    join join_t = built_t - requirement_t (join_redev = 0), so the stock identity holds and dwellings
    built = built_t >= 0; 5) soil: the TL5 / TL6 soil factor of each year and the soil-bearing share
    clipped to [0, 1] (zero-building years) applied exactly through the intensity (see below)."""
    fi, join_abs, _, info = LV.apply_tl(ctx, params, pT, comps, ramp_name, ctx['E_nojoin'])
    n = len(ctx['years'])
    zeros = np.zeros(n)
    E1 = engine.forward(ctx['pop'], ctx['hh'], ctx['growth'], join=zeros, join_redev=zeros, **fi)
    req = np.asarray(engine.requirement(E1), float)
    bk = bank(req + np.asarray(join_abs, float))
    join_T = bk['built'] - req
    join_T[0] = 0.0
    E = engine.forward(ctx['pop'], ctx['hh'], ctx['growth'], join=join_T, join_redev=zeros, **fi)
    # Soil (TL5, TL6, and the banked zero-building years). The engine's soil-bearing share is
    # 1 - soil-free floor area / floor area built, which assumes the replacement (soil-free) floor area
    # does not exceed the floor area built. In banked zero-building years nothing is built while the
    # replacement term stays positive, so the physical soil-bearing area is max(0, built - soil-free):
    # the share is clipped to [0, 1] (0 where nothing is built). The soil factor of each year
    # (soil_path: TL5 lowest soil order, x (1 - s w) under TL6) and the clipped share are applied exactly
    # by replacing the engine's own soil term through the intensity:
    #     I'(y) = I(y) - s_eng x share(y) + soil_path(y) x share_eff(y)
    # so that carbon = (I - s_eng) x floor area + soil_path x floor area x share_eff. The share does not
    # depend on the intensity (checked identical in both passes); E['soil_share'] is then set to share_eff.
    share = E['soil_share'].copy()
    built_gfa = E['total']
    share_eff = np.where(built_gfa <= T_ZERO_TOL_M2, 0.0, np.clip(share, 0.0, 1.0))
    share_eff[0] = share[0]
    sp = info['soil_path'] or {t: np.full(n, float(ctx['soil'][t])) for t in ctx['typ']}
    clipped = bool(np.any(share_eff[1:] != share[1:]))
    info.update(soil_share_raw=share, soil_share_clipped_years=[int(y) for y, a, b in
                                                                zip(ctx['years'][1:], share[1:], share_eff[1:]) if a != b])
    if info['soil_path'] is not None or clipped:
        info['soil_path'] = sp
        info['intensity_material'] = {t: np.asarray(fi['intensity'][t], float) - ctx['soil'][t] for t in ctx['typ']}
        fi = dict(fi)
        for key in ('intensity', 'intensity_upfront'):
            fi[key] = {t: np.asarray(fi[key][t], float) - ctx['soil'][t] * share + np.asarray(sp[t], float) * share_eff
                       for t in ctx['typ']}
        E = engine.forward(ctx['pop'], ctx['hh'], ctx['growth'], join=join_T, join_redev=zeros, **fi)
        if not np.array_equal(E['soil_share'], share):
            raise SystemExit('TL soil: the soil-bearing share changed between passes.')
        E = dict(E, soil_share=share_eff)
    info.update(bank=bk, requirement_nojoin=req, join_absorbed=np.asarray(join_abs, float), join_T=join_T)
    return dict(E=E, inputs=fi, info=info, active={}, ramp=ramp_name or RAMP_ADOPTED, l5_apartments_held=False,
                scenario=ctx['scenario'], comps=tuple(info['comps']))


def tl_indicators(ctx, R):
    """Human-terms indicators of a TL-family run (2026-2050)."""
    E, info = R['E'], R['info']
    S = E['pop'] / E['hh']
    years = ctx['years']
    f = slice(1, None)
    size = {t: np.broadcast_to(np.asarray(R['inputs']['size'][t], float), S.shape) for t in ctx['typ']}
    built = np.asarray(engine.requirement(E), float)
    v_impl = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
    bk = info['bank']
    zero_years = [int(y) for y, b in zip(years[f], built[f]) if b <= T_ZERO_TOL_DWELLINGS]
    return dict(
        new_dwelling_size_m2={t: {int(y): float(size[t][i]) for i, y in enumerate(years) if y in (2026, 2027, 2035, 2050)}
                              for t in ctx['typ']},
        mean_new_dwelling_size_m2_by_year={int(y): float(E['D'][i]) for i, y in enumerate(years) if y >= 2026},
        m2_per_person_new_dwellings={int(y): float(E['D'][i] / S[i]) for i, y in enumerate(years) if y >= 2026},
        dwellings_built_all_categories={int(y): float(built[i]) for i, y in enumerate(years) if y >= 2026},
        dwellings_built_in_scope={int(y): float(E['dwell_in_scope'][i]) for i, y in enumerate(years) if y >= 2026},
        implied_vacancy={int(y): float(v_impl[i]) for i, y in enumerate(years) if y >= 2026},
        vacancy_change_release_dwellings=float(-np.minimum(E['change'][f], 0.0).sum()),
        near_term_surplus_absorbed_dwellings=float(-np.minimum(info['join_absorbed'][f], 0.0).sum()),
        bank={int(y): dict(raw=float(info['requirement_nojoin'][i] + info['join_absorbed'][i]),
                           built=float(bk['built'][i]), bank_end=float(bk['bank'][i]), added=float(bk['added'][i]),
                           used=float(bk['used'][i])) for i, y in enumerate(years) if y >= 2026},
        release_added_total=float(bk['added'][f].sum()), release_used_total=float(bk['used'][f].sum()),
        bank_unused_2050=float(bk['bank'][-1]), zero_building_years=zero_years, n_zero_building_years=len(zero_years))


def compute_tl(res, verbose=True):
    """TL, TL gradual adoption, the 64 Shapley subsets of TL1-TL6 relative to P5 Ambitious at full
    strength from 2027, metrics, bands, annual rows, gap. Appended to the pathway tables."""
    import Building_factors as BF
    t0 = time.time()
    ref = res['ctxs'][REFERENCE]
    B = ref['B']
    pT = LV.resolve_tl(BF.load_characteristics(), load_factors_building(),
                       pd.read_csv(validation.projection.FILE_FACTORS_TYPOLOGY), B['OLF_USED'])
    params = res['params']
    cache = {}

    def getT(comps, ramp_name=LV.TL_FROM2027):
        key = (tuple(c for c in LV.TL_COMPONENTS if c in comps), ramp_name)
        if key not in cache:
            cache[key] = run_tl(ref, params, pT, comps, ramp_name)
        return cache[key]

    full = LV.TL_COMPONENTS
    RT, RTr = getT(full), getT(full, LV.TL_GRADUAL)
    rows = [metrics(ref, RT, 'TL', 'TL'), metrics(ref, RTr, 'TL-gradual', 'TL')]
    for r_ in rows:
        r_['levers'] = 'P5-ambitious+' + '+'.join(LV.TL_COMPONENTS)
    p0 = res['runs'][(res['runs']['run'] == REFERENCE) & (res['runs']['scenario'] == REFERENCE)].iloc[0]
    for r_ in rows:
        for col in ('carbon_kt', 'LoE_AR', 'LoE_AtP', 'gfa_Mm2', 'committed_lower_kt', 'committed_upper_kt'):
            r_[f'delta_{col}_vs_reference_pct'] = 100.0 * (r_[col] / p0[col] - 1.0)
    annual = annual_rows(ref, RT, 'TL') + annual_rows(ref, RTr, 'TL-gradual')
    bands = band_rows(ref, RT, 'TL') + band_rows(ref, RTr, 'TL-gradual')
    bd = pd.DataFrame(bands)
    b0 = res['bands'][(res['bands']['run'] == res['bands']['scenario'])].set_index(['scenario', 'definition', 'band'])
    for col in ('gfa_Mm2', 'carbon_kt'):
        bd[f'delta_{col}_vs_reference'] = [r[col] - b0.loc[(r['scenario'], r['definition'], r['band']), col]
                                           for _, r in bd.iterrows()]
    # Shapley over TL1-TL6 (full strength from 2027), base = P5 Ambitious at full strength from 2027
    vals = {'carbon_kt': {}, 'LoE_AR': {}}
    sub_rows = []
    for S_ in subsets(full):
        R_ = getT(S_)
        m = metrics(ref, R_, LV.tl_label(S_), 'TL')
        vals['carbon_kt'][S_], vals['LoE_AR'][S_] = m['carbon_kt'], m['LoE_AR']
        sub_rows.append(dict(level='TL', subset=LV.tl_label(S_), n_players=len(S_), carbon_kt=m['carbon_kt'],
                             LoE_AR=m['LoE_AR'], LoE_AtP=m['LoE_AtP'], gfa_Mm2=m['gfa_Mm2'],
                             dwellings_built_min_year=m['dwellings_built_min_year']))
    shap_rows, exact = [], {}
    for metric, v in vals.items():
        r_, ex = shapley_rows(v, full, 'TL', metric, 'TL', LV.TL_NAMES)
        for x in r_:
            x['share_of_P5_ambitious_from2027_minus_TL'] = x.pop('share_of_reference_minus_P5')
        shap_rows += r_
        exact[metric] = ex
    p5s = res['runs'][(res['runs']['run'] == 'P5-ambitious') & (res['runs']['scenario'] == REFERENCE)].iloc[0]
    for metric in ('carbon_kt', 'LoE_AR'):
        shap_rows.append(dict(level='TL', setting='TL', metric=metric, player=LV.TL_FROM2027,
                              name=N._ascii(f"P5 Ambitious: adoption path -> {N.ADOPTION['from2027']} (separate line, "
                                            f"not a Shapley player)"),
                              reduction=float(p5s[metric] - vals[metric][frozenset()]),
                              share_of_P5_ambitious_from2027_minus_TL=float('nan')))
    # gap
    bar, batp = ref['b_ar'].sum(), ref['b_atp'].sum()
    gap = {}
    for name, R_ in (('TL', RT), ('TL-gradual', RTr)):
        loe = R_['E']['carbon'][1:].sum() / bar
        if loe > 1:
            bc, _ = backcast(ref, R_, name)
            E_ = R_['E']
            S_ = E_['pop'] / E_['hh']
            cut = 1.0 - bc['k_AR']
            dw = np.asarray(E_['dwell_in_scope'], float)[2:]
            gap[name] = dict(LoE_AR=loe, within_AR=False, backcast=bc, residual=dict(
                cut_of_2027_2050_construction=cut,
                dwellings_not_built_2027_2050=float(cut * dw.sum()),
                new_residents_housed_in_existing_dwellings=float(cut * (dw * S_[2:]).sum()),
                note='dwellings in scope (excl. retirement villages) of the 2027-2050 cohorts x (1 - k); residents = '
                     'sum over years of dwellings not built x S(t)'))
        else:
            sp = linear_split(ref, R_)
            gap[name] = dict(LoE_AR=loe, within_AR=True, margin_AR_kt=(bar - R_['E']['carbon'][1:].sum()) / M6,
                             margin_AR_share=1.0 - loe, LoE_AtP=R_['E']['carbon'][1:].sum() / batp,
                             LoE_AtP_min_k0=sp['fixed'].sum() / batp)
    # TL on the solution-space plane (MODEL v1.0.0 addition): its effective reductions of 2027-2050
    # floor area and of non-soil carbon per m2 against the Reference, as the P1-P5 markers
    # (effective_coordinates). TL5 and TL6 also lower soil carbon, which the plane does not show.
    split0 = linear_split(ref, res['get'](REFERENCE, {}))
    d_tl, i_tl = effective_coordinates(linear_split(ref, RT), split0)
    loe_tl = RT['E']['carbon'][1:].sum() / bar
    marker = dict(run='TL', demand_reduction=d_tl, intensity_reduction=i_tl, LoE_AR_run=loe_tl,
                  LoE_AR_on_grid_at_coordinates=scaled_carbon(split0, 1.0 - d_tl, 1.0 - i_tl).sum() / bar,
                  LoE_AtP_run=loe_tl * bar / batp,
                  note='TL5 and TL6 lower soil carbon loss, which the demand-intensity plane does not show')
    out = dict(params_T=pT, rows=rows, annual=annual, bands=bd, shapley=pd.DataFrame(shap_rows),
               subsets=pd.DataFrame(sub_rows), shapley_exact=exact, gap=gap, solution_space_marker=marker,
               indicators={'TL': tl_indicators(ref, RT), 'TL-gradual': tl_indicators(ref, RTr)},
               cache=cache, getT=getT, seconds=time.time() - t0)
    if verbose:
        print(f'pathways TL: {len(cache)} engine runs in {out["seconds"]:.1f} s')
    return out


def checks_tl(res, rt):
    """STOP conditions of the TL family: dwellings built >= 0 every year, the stock identity
    (engine dwellings built = banked dwellings), implied vacancy >= 0, size >= occupied area
    (within 1e-12 relative), 2026 unchanged, Shapley efficiency exact."""
    ref = res['ctxs'][REFERENCE]
    E0 = res['get'](REFERENCE, {})['E']
    for key, R in rt['cache'].items():
        E, bk = R['E'], R['info']['bank']
        built = np.asarray(engine.requirement(E), float)
        if (built[1:] < -T_ZERO_TOL_DWELLINGS).any() or (E['dwell_in_scope'][1:] < -T_ZERO_TOL_DWELLINGS).any() \
                or (E['total'][1:] < -T_ZERO_TOL_M2).any():
            raise SystemExit(f'STOP: negative dwellings built in TL run {key}.')
        if not np.allclose(built[1:], bk['built'][1:], rtol=1e-12, atol=1e-6):
            raise SystemExit(f'STOP: banking breaks the stock identity in TL run {key}.')
        v = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
        if (v[1:] < -1e-12).any():
            raise SystemExit(f'STOP: negative implied vacancy in TL run {key}.')
        S = E['pop'] / E['hh']
        for t in ref['typ']:
            occ = S * np.asarray(R['inputs']['olf'][t], float)
            size = np.broadcast_to(np.asarray(R['inputs']['size'][t], float), S.shape)
            if (size[1:] < occ[1:] * (1 - 1e-12)).any():
                raise SystemExit(f'STOP: dwelling size below the occupied area in TL run {key} ({t}).')
        if abs(E['carbon'][1] / E0['carbon'][1] - 1) > 1e-12 or abs(E['total'][1] / E0['total'][1] - 1) > 1e-12:
            raise SystemExit(f'TL run {key}: 2026 changed.')
    for metric, (phi, total) in rt['shapley_exact'].items():
        if sum(phi.values()) != total:
            raise SystemExit(f'TL Shapley efficiency fails ({metric}).')


def write_tl(res, rt):
    """Append the TL rows to the pathway tables and write theoretical_limit.json and the TL Shapley tables."""
    _csv(pd.concat([res['runs'], pd.DataFrame(rt['rows'])], ignore_index=True), 'runs.csv')
    _csv(pd.concat([res['annual'], pd.DataFrame(rt['annual'])], ignore_index=True), 'annual.csv')
    _csv(pd.concat([res['bands'], rt['bands']], ignore_index=True), 'bands.csv')
    _csv(rt['shapley'], 'shapley_theoretical_limit.csv')
    _csv(rt['subsets'], 'shapley_theoretical_limit_subsets.csv')
    rows = {r['run']: r for r in rt['rows']}
    out = dict(run_mode=RUN_MODE, disclaimer=LV.TL_DISCLAIMER, definition=dict(
        base='P5 Ambitious (L4 removals -40%; L2 / L3 replaced by TL1)', start=2027, bau=LV.TL_BAU_NOTE,
        tl6=dict(share=LV.TL6_SHARE, components=LV.TL6_COMPONENTS, source=LV.TL6_SOURCE, assumptions=LV.TL6_ASSUMPTIONS),
        adoption=('from2027: w = 1 for every lever in 2027-2050; 2026 observed and untouched (TL, gradual adoption: '
                  'the adopted logistic path, full by 2035)'),
        components=LV.TL_NAMES), resolved=rt['params_T'],
        metrics={k: {c: v for c, v in r.items() if isinstance(v, (int, float, str, bool, np.floating, np.integer))}
                 for k, r in rows.items()},
        indicators=rt['indicators'], gap=rt['gap'], solution_space_marker=rt['solution_space_marker'],
        shapley=N.columns(rt['shapley']).to_dict(orient='records'))
    _json(out, 'theoretical_limit.json')


def main():
    res = compute()
    identity = checks(res)
    print(f'pathways: identity REF (no lever) = the Reference run, max relative difference {max(identity.values()):.2e}')
    write(res, identity)
    rt = compute_tl(res)
    checks_tl(res, rt)
    write_tl(res, rt)
    res['T'] = rt
    if SAVE_FIGURES:
        figures(res)
    for k in T_RUNS:
        x = next(r_ for r_ in rt['rows'] if r_['run'] == k)
        print(f"{k}: floor area {x['gfa_Mm2']:.2f} Mm2, carbon {x['carbon_kt']:,.0f} kt, LoE AR {x['LoE_AR']:.3f}, "
              f"AtP {x['LoE_AtP']:.2f} ({x['delta_carbon_kt_vs_reference_pct']:+.1f}% vs the Reference)")
    r = res['runs']
    ref = r[(r['scenario'] == REFERENCE) & (r['adoption'] == RAMP_ADOPTED) & ~r['l5_apartments_held']]
    print(ref[['run', 'gfa_Mm2', 'carbon_kt', 'LoE_AR', 'LoE_AtP', 'delta_carbon_kt_vs_reference_pct']].to_string(index=False))
    return res


# ============================================================
# FIGURES (style.save_figure: outputs/headline/, outputs/diagnostics/pathways_si/)
# ============================================================
# Colours: the AR / AtP boundary pair of boundaries.py; pathways P1-P4 aqua, amber, pink, deep magenta
# (validated with the dataviz palette validator together with the boundary pair, all pairs,
# light surface: no failure; pink vs aqua in the CVD warn band, so every pathway is also
# identified by position and direct labels); P0 and P5 (totals) neutral.
AR_COLOR, ATP_COLOR = '#1F5FA8', '#C2571A'
P_COLOR = {'REF': '#9a9a9a', 'P1': '#1baf7a', 'P2': '#eda100', 'P3': '#e87ba4', 'P4': '#a0185a', 'P5': '#3b3b3b'}
INK, MUTED, GRID_COLOR = '#333333', '#777777', '#e1e0d9'
PW_ORDER = ('REF', 'P1', 'P2', 'P3', 'P4', 'P5')
NAMES = {'REF': N.SCENARIOS['REF'], **LV.PATHWAY_NAMES}
UNTARGETED = tuple(N.band_data_label(b) for b in N.UNTARGETED)
def _save(fig, name):
    target = FP.release_file(name)
    if target is not None:
        style.save_figure(fig, target)
    import matplotlib.pyplot as plt
    plt.close(fig)


def _style(ax, axis='y'):
    ax.grid(True, axis=axis, color=GRID_COLOR, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)


def _hline(ax, y, color, ls, label, x_text, x_range=None):
    """A cumulative boundary as a horizontal line (over x_range only, if given) with a direct label."""
    import figaudit
    import matplotlib.patheffects as pe
    kw = dict(color=color, lw=2.0, ls=ls, gid=figaudit.BOUNDARY,
              path_effects=[pe.Stroke(linewidth=4, foreground='white'), pe.Normal()])
    if x_range is None:
        ax.axhline(y, **kw)
    else:
        ax.plot(x_range, [y, y], **kw)
    ax.text(x_text, y, f' {label}', color=INK, fontsize=8, va='bottom', ha='left')


def _wrap(text, width=12):
    import textwrap
    return '\n'.join(textwrap.wrap(text, width))


def _run(res, name, scen=REFERENCE):
    """The runs row of `name` under variant `scen` (the no-lever run carries the variant id)."""
    r = res['runs']
    if name == REFERENCE:
        name = scen
    return r[(r['run'] == name) & (r['scenario'] == scen)].iloc[0]


def _pname(P, s='moderate'):
    return P if P == REFERENCE else f'{P}-{s}'


def _band_colors():
    projection = validation.projection
    return dict(zip([b for b, _ in FIG_BANDS],
                    [projection.DEMAND_COLORS[0], projection.HOUSESPLIT_COLOR, projection.DEMAND_COLORS[1], projection.DEMAND_COLORS[2],
                     projection.REPL_COLOR, projection.WAVE_COLOR, projection.JOIN_COLOR, projection.EVENTS_COLOR]))


def fig_bands_by_pathway(res):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    colors = _band_colors()
    bd = res['bands']
    bd = bd[(bd['scenario'] == REFERENCE) & (bd['definition'] == 'in_scope')]
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, col, ylab in ((axes[0], 'gfa_Mm2', 'floor area 2026-2050, Mm$^2$'),
                          (axes[1], 'carbon_kt', 'carbon 2026-2050, kt CO$_2$e')):
        fmt = (lambda v: f'{v:,.1f}') if col == 'gfa_Mm2' else (lambda v: f'{v:,.0f}')
        for i, P in enumerate(PW_ORDER):
            d = bd[bd['run'] == _pname(P)].set_index('band')
            pos, neg = 0.0, 0.0
            for band, _ in FIG_BANDS:                      # untargeted bands first, at the bottom
                v = float(d.loc[band, col])
                if abs(v) < 1e-12:
                    continue
                base = pos if v > 0 else neg
                ax.bar(i, v, bottom=base, color=colors[band], edgecolor='white', lw=1.0, width=0.62,
                       hatch='..' if band in UNTARGETED else None)
                if abs(v) > 0.035 * d[col].sum():
                    ax.text(i, base + v / 2, fmt(v), ha='center', va='center', fontsize=7, color='white')
                if v > 0:
                    pos += v
                else:
                    neg += v
            net = pos + neg
            ax.text(i - 0.33, pos, fmt(net), ha='left', va='bottom', fontsize=8.5, color=INK)
            if P != 'REF':                                  # stretch total as a whisker from the central total
                st = float(bd[bd['run'] == _pname(P, 'ambitious')][col].sum())
                ax.plot([i + 0.2, i + 0.2], [net, st], color=INK, lw=1.4)
                ax.plot([i + 0.12, i + 0.28], [st, st], color=INK, lw=1.4)
                ax.text(i + 0.3, st, fmt(st), ha='left', va='center', fontsize=7.5, color=MUTED)
        ax.set_xticks(range(len(PW_ORDER)))
        ax.set_xticklabels([f'{P}\n{_wrap(NAMES[P], 14)}' for P in PW_ORDER], fontsize=8.5)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_ylabel(ylab)
        _style(ax)
    axes[0].set_title('Floor area by demand band (in scope)', fontsize=10)
    axes[1].set_title('Carbon by demand band (in scope, incl. replacements & repaints within the window)', fontsize=10)
    handles = [Patch(facecolor=colors[b], hatch='..' if b in UNTARGETED else None, edgecolor='white',
                     label=b + (' (untargeted)' if b in UNTARGETED else '')) for b, _ in FIG_BANDS]
    handles.append(plt.Line2D([0], [0], color=INK, lw=1.4, label='stretch total (whisker from the central total)'))
    fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.12))
    p0, p5 = _run(res, 'REF'), _run(res, 'P5-moderate')
    fig.suptitle(f"What each pathway removes, by reason for building (S3-10, central): carbon {p0['carbon_kt']:,.0f} -> "
                 f"{p5['carbon_kt']:,.0f} kt (P5)", fontsize=11)
    fig.text(0.5, -0.16, 'Growth and house-splitting (hatched) are untargeted by design: population and household '
             'formation are exogenous (Pellan et al. 2024). Typology shares are the baseline mix in every run (L4 '
             'removed). Negative bands below zero: with P2 the vacancy rate falls and '
             'existing dwellings are released; the absorbed near-term surplus is paid back by 2050.',
             ha='center', fontsize=8, style='italic', wrap=True)
    fig.tight_layout()
    _save(fig, 'pw_1_bands_by_pathway')


def fig_shapley_waterfall(res):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    sh = res['shapley_pathways']
    sh = sh[sh['metric'] == 'carbon_kt'].set_index(['setting', 'player'])['reduction']
    bar_kt, batp_kt = res['backcast']['B_AR_kt'], res['backcast']['B_AtP_kt']
    p0, p5c, p5s = _run(res, 'REF'), _run(res, 'P5-moderate'), _run(res, 'P5-ambitious')
    fig, ax = plt.subplots(figsize=(13, 6.8))
    ax.bar(0, p0['carbon_kt'], color=P_COLOR['REF'], width=0.66)
    ax.text(0, p0['carbon_kt'], f"{p0['carbon_kt']:,.0f}", ha='center', va='bottom', fontsize=8.5, color=INK)
    prev, x = p0['carbon_kt'], 0
    labels = ['P0\nbaseline']
    for P in ('P1', 'P2', 'P3', 'P4'):
        x += 1
        c, s = float(sh[('moderate', P)]), float(sh[('ambitious', P)])
        ax.bar(x, -c, bottom=prev, color=P_COLOR[P], edgecolor='white', width=0.66)
        ax.plot([x - 1.33, x + 0.33], [prev, prev], color=MUTED, lw=0.6)
        ax.plot([x + 0.4, x + 0.4], [prev, prev - s], color=INK, lw=1.4)         # stretch Shapley value of the step
        ax.plot([x + 0.32, x + 0.48], [prev - s, prev - s], color=INK, lw=1.4)
        ax.text(x - 0.1, prev - c - 60, f"-{c:,.0f}\n({-100 * c / p0['carbon_kt']:.1f}%)\nstretch -{s:,.0f}",
                ha='center', va='top', fontsize=7.5, color=INK)
        prev -= c
        labels.append(f'{P}\n{_wrap(NAMES[P], 13)}')
    x += 1
    ax.plot([x - 1.33, x + 0.33], [prev, prev], color=MUTED, lw=0.6)
    ax.bar(x, p5c['carbon_kt'], color=P_COLOR['P5'], width=0.66)
    ax.plot([x + 0.18, x + 0.18], [p5c['carbon_kt'], p5s['carbon_kt']], color=INK, lw=1.4)
    ax.plot([x + 0.1, x + 0.26], [p5s['carbon_kt']] * 2, color=INK, lw=1.4)
    ax.text(x, p5c['carbon_kt'], f"{p5c['carbon_kt']:,.0f} ({p5c['delta_carbon_kt_vs_reference_pct']:+.1f}%)\nstretch "
            f"{p5s['carbon_kt']:,.0f} ({p5s['delta_carbon_kt_vs_reference_pct']:+.1f}%)", ha='center', va='bottom',
            fontsize=8, color=INK)
    labels.append('P5\nall')
    xc = x + 1.6
    ax.axvline(xc - 0.8, color=MUTED, lw=0.8, ls=':')
    for k, (nm, rr, rs, col) in enumerate((('REF', p0, None, P_COLOR['REF']), ('P5', p5c, p5s, P_COLOR['P5']))):
        xx = xc + 0.9 * k
        ax.bar(xx, rr['committed_lower_kt'], color='white', edgecolor=col, hatch='xx', width=0.66, lw=1.0)
        ax.plot([xx, xx], [rr['committed_lower_kt'], rr['committed_upper_kt']], color=col, lw=2.2)
        ax.plot([xx - 0.18, xx + 0.18], [rr['committed_upper_kt']] * 2, color=col, lw=2.2)
        txt = f"{rr['committed_lower_kt']:,.0f}-{rr['committed_upper_kt']:,.0f}"
        if rs is not None:
            ax.plot([xx + 0.42, xx + 0.42], [rs['committed_lower_kt'], rs['committed_upper_kt']], color=INK, lw=2.0)
            ax.plot([xx + 0.36, xx + 0.48], [rs['committed_lower_kt']] * 2, color=INK, lw=1.4)
            ax.plot([xx + 0.36, xx + 0.48], [rs['committed_upper_kt']] * 2, color=INK, lw=1.4)
            txt = f"stretch {rs['committed_lower_kt']:,.0f}-{rs['committed_upper_kt']:,.0f}\ncentral " + txt
        ax.text(xx, rr['committed_upper_kt'] + 250, txt, ha='center', va='bottom', fontsize=7.5, color=INK)
    ax.text(xc + 0.45, p0['committed_upper_kt'] * 1.35, 'committed\nafter 2050\n(not in LoE)', ha='center',
            va='bottom', fontsize=8, color=MUTED)
    ax.set_xticks(list(range(x + 1)) + [xc, xc + 0.9])
    ax.set_xticklabels(labels + ['P0\ncommitted', 'P5\ncommitted'], fontsize=8.5)
    _hline(ax, bar_kt, AR_COLOR, '-', f'AR budget {bar_kt:,.0f}', x - 1.6, x_range=[-0.4, x + 0.4])
    _hline(ax, batp_kt, ATP_COLOR, '--', f'AtP budget {batp_kt:,.0f}', x - 1.6, x_range=[-0.4, x + 0.4])
    ax.set_ylabel('cumulative carbon 2026-2050, kt CO$_2$e')
    ax.set_title(f"P0 -> P5 (S3-10): cumulative LoE AR {p0['LoE_AR']:.2f} -> {p5c['LoE_AR']:.2f} (stretch "
                 f"{p5s['LoE_AR']:.2f}), AtP {p0['LoE_AtP']:.1f} -> {p5c['LoE_AtP']:.1f} (stretch {p5s['LoE_AtP']:.1f})",
                 fontsize=11)
    _style(ax)
    fig.legend(handles=[Patch(color=P_COLOR[P], label=f'{P} {NAMES[P]}') for P in PW_ORDER] +
               [plt.Line2D([0], [0], color=INK, lw=1.4, label='stretch (whisker)'),
                Patch(facecolor='white', edgecolor=MUTED, hatch='xx', label='committed after 2050 (range)')],
               loc='lower center', ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.09))
    fig.text(0.5, -0.13, 'Steps are Shapley values over the 16 pathway subsets (order-free; they add up exactly to '
             'P0 - P5; Shapley 1953, Albrecht et al. 2002). Budgets: cumulative 2026-2050, 2 °C carrying capacity '
             '(Bjørn & Hauschild 2015).', ha='center', fontsize=8, style='italic')
    fig.tight_layout()
    _save(fig, 'pw_2_shapley_waterfall')


def fig_solution_space(res):
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.colors import LinearSegmentedColormap, LogNorm
    ref = res['ctxs'][REFERENCE]
    split0 = linear_split(ref, res['get'](REFERENCE, {}))
    bar, batp = ref['b_ar'].sum(), ref['b_atp'].sum()
    Z = res['space'].pivot(index='intensity_reduction', columns='demand_reduction', values='LoE_AR').values
    cmap = LinearSegmentedColormap.from_list('blue_seq', ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf',
                                                          '#184f95', '#0d366b'])
    fig, (ax, axin) = plt.subplots(1, 2, figsize=(15, 7.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    edges = np.concatenate([[-2.5], GRID * 100 + 2.5])
    pm = ax.pcolormesh(edges, edges, Z, cmap=cmap, norm=LogNorm(vmin=0.3, vmax=5.0), shading='flat')
    cb = fig.colorbar(pm, ax=axin, shrink=0.8)
    cb.set_label('cumulative LoE AR 2026-2050 (log scale)')
    cb.set_ticks([0.3, 0.5, 1, 2, 3, 5])
    cb.set_ticklabels(['0.3', '0.5', '1', '2', '3', '5'])
    cb.minorticks_off()
    fine = np.linspace(0, 1, 201)
    D, Ii = np.meshgrid(fine, fine)
    L_ar = np.vectorize(lambda d, i: scaled_carbon(split0, 1 - d, 1 - i).sum() / bar)(D, Ii)
    L_atp = L_ar * bar / batp
    levels = [lv for lv in (1, 2, 3, 5, 10) if L_ar.min() < lv < L_ar.max()]
    cs = ax.contour(D * 100, Ii * 100, L_ar, levels=levels, colors=['black' if lv == 1 else '#555555' for lv in levels],
                    linewidths=[2.4 if lv == 1 else 0.9 for lv in levels])
    ax.clabel(cs, fmt=lambda v: f'AR {v:g}', fontsize=8)
    if L_atp.min() < 1 < L_atp.max():
        c2 = ax.contour(D * 100, Ii * 100, L_atp, levels=[1], colors=[ATP_COLOR], linewidths=2.4)
        ax.clabel(c2, fmt=lambda v: 'AtP 1', fontsize=8)
        atp_note = ''
    else:
        atp_note = (f'AtP LoE = 1 is not attainable on this grid: minimum AtP LoE {L_atp.min():.2f} '
                    f'(100% demand cut, i.e. 2026 construction and its events alone).')
    halo = [pe.Stroke(linewidth=2.5, foreground='#0d366b'), pe.Normal()]
    marks = res['backcast']['solution_space_markers']
    # zoom inset on the pathway markers (they all sit at small cuts), with direct labels
    zx = (-1.5, 2.5 + 100 * max(m['demand_reduction'] for m in marks))
    zy = (min(-2.0, 100 * min(m['intensity_reduction'] for m in marks) - 2.0),
          2.5 + 100 * max(m['intensity_reduction'] for m in marks))
    axin.pcolormesh(edges, edges, Z, cmap=cmap, norm=LogNorm(vmin=0.3, vmax=5.0), shading='flat')
    for a_ in (ax, axin):
        for m in marks:
            P, s = m['run'].split('-')
            a_.scatter(100 * m['demand_reduction'], 100 * m['intensity_reduction'], s=90 if a_ is ax else 110, zorder=5,
                       facecolor=P_COLOR[P] if s == 'ambitious' else 'white', edgecolor=P_COLOR[P], linewidth=2.0,
                       label=f"{m['run']}: LoE AR {m['LoE_AR_run']:.2f}" if a_ is ax else None)
    for k, m in enumerate(marks):
        P, s = m['run'].split('-')
        axin.annotate(f'{P}{"s" if s == "ambitious" else "c"}', (100 * m['demand_reduction'], 100 * m['intensity_reduction']),
                      xytext=((-20, 6) if s == 'moderate' else (6, -12)), textcoords='offset points', fontsize=8,
                      color='white', path_effects=halo)
    fz = np.linspace(0, 1, 401)
    Dz, Iz = np.meshgrid(fz, fz)
    Lz = np.vectorize(lambda d, i: scaled_carbon(split0, 1 - d, 1 - i).sum() / bar)(Dz, Iz)
    lz = [lv for lv in (3, 3.5, 4, 4.5) if Lz.min() < lv < Lz.max()]
    cz = axin.contour(Dz * 100, Iz * 100, Lz, levels=lz, colors='#cccccc', linewidths=0.8)
    axin.clabel(cz, fmt=lambda v: f'AR {v:g}', fontsize=7)
    axin.set_xlim(*zx)
    axin.set_ylim(*zy)
    axin.set_xlabel('demand reduction (%)')
    axin.set_ylabel('intensity reduction (%)')
    axin.set_title('Zoom on the pathways (contours AR 3-4.5)', fontsize=10)
    ax.add_patch(plt.Rectangle((zx[0], zy[0]), zx[1] - zx[0], zy[1] - zy[0], fill=False, ec='white', lw=1.2))
    bc = res['backcast']
    for pnt in bc['backcast_points']:
        k = pnt['run'].split(' ')[0]
        ax.scatter(100 * pnt['demand_reduction'], 100 * pnt['intensity_reduction'], marker='D', s=60, zorder=6,
                   color='black', edgecolor='white',
                   label=f"{pnt['run']}: cut {100 * bc[k]['cut_AR']:.1f}% of 2027-2050 construction for LoE AR = 1")
    ax.set_xlim(-2.5, 102.5)
    ax.set_ylim(min(-2.5, zy[0] - 1.0), 102.5)
    ax.axhline(0, color='white', lw=0.6, ls=':')
    axin.axhline(0, color='white', lw=0.6, ls=':')
    ax.set_xlabel('demand reduction: cut of 2027-2050 floor area vs P0 (%)')
    ax.set_ylabel('intensity reduction: cut of non-soil carbon per m$^2$, 2027-2050 cohorts (%)')
    ax.set_title('Solution space on P0 (S3-10): cumulative LoE AR (c = central, open; s = stretch, filled)', fontsize=10.5)
    fig.legend(*ax.get_legend_handles_labels(), fontsize=7.5, loc='lower center', bbox_to_anchor=(0.5, -0.13),
               frameon=False, ncol=4)
    fig.text(0.5, -0.17, 'Right: zoom on the pathway markers (c = central, s = stretch; white box on the left). Cells: the 5% grid (solution_space.csv); contours: the same linear model on a 0.5% grid. '
             'Soil carbon and 2026 are not cut by the intensity axis. ' + atp_note, ha='center', fontsize=8,
             style='italic', wrap=True)
    fig.tight_layout()
    _save(fig, 'pw_3_solution_space')


def fig_annual(res):
    import matplotlib.pyplot as plt
    import figaudit
    a = res['annual']
    a = a[a['scenario'] == REFERENCE]
    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    ends = []
    series = [('REF', P_COLOR['REF'], '-')] + [(f'{P}-{s}', P_COLOR[P], '-' if s == 'moderate' else '--')
                                            for P in PW_ORDER[1:] for s in LV.SETTINGS]
    for name, col, ls in series:
        d = a[a['run'] == name]
        ax.plot(d['year'], d['carbon_kt'], color=col, ls=ls, lw=2.0 if name.split('-')[0] in ('REF', 'P5') else 1.6,
                label=f"{name}: {NAMES[name.split('-')[0]]}")
        ends.append((d['carbon_kt'].iloc[-1], name, col))
    d0 = a[a['run'] == 'REF']
    ax.plot(d0['year'], d0['B_AR_kt'], color=AR_COLOR, lw=2.0, gid=figaudit.BOUNDARY, label='boundary, acquired rights (AR)')
    ax.plot(d0['year'], d0['B_AtP_kt'], color=ATP_COLOR, lw=2.0, ls='--', gid=figaudit.BOUNDARY,
            label='boundary, ability to pay (AtP)')
    ends += [(d0['B_AR_kt'].iloc[-1], 'AR', AR_COLOR), (d0['B_AtP_kt'].iloc[-1], 'AtP', ATP_COLOR)]
    ends.sort()
    ylast = -1e9
    for v, nm, col in ends:
        y = max(v, ylast + 22)
        ax.annotate(f'{nm} {v:,.0f}', (2050, v), xytext=(2050.5, y), fontsize=7, color=INK, va='center',
                    arrowprops=dict(arrowstyle='-', color=col, lw=0.6))
        ylast = y
    ax.set_xlim(2026, 2054)
    ax.set_ylim(0, None)
    ax.set_xlabel('year')
    ax.set_ylabel('annual carbon, kt CO$_2$e per year')
    ax.set_title('Annual carbon by pathway (S3-10): central solid, stretch dashed, vs annual boundaries', fontsize=11)
    ax.legend(fontsize=7.5, frameon=False, loc='upper right', ncol=2)
    _style(ax)
    fig.text(0.5, -0.05, 'Time-resolved: upfront (A1-A5 + soil) in the construction year plus replacements & repaints '
             'within 2026-2050. 2026 is observed and identical in every run; the levers follow a logistic ramp '
             '2026-2035 (10% to 90% in 2027.5-2033.5).', ha='center', fontsize=8, style='italic')
    fig.tight_layout()
    _save(fig, 'pw_4_annual_SI')


def fig_envelope(res):
    import matplotlib.pyplot as plt
    import figaudit
    from matplotlib.patches import Patch
    bar_kt, batp_kt = res['backcast']['B_AR_kt'], res['backcast']['B_AtP_kt']
    ramps = [('by2030', 'by2030', 0.6, '--'), ('by2035', None, 1.0, '-'), ('by2045', 'by2045', 0.3, ':')]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(16, 6.2), gridspec_kw=dict(width_ratios=[1.35, 1]))
    names = [('REF', P_COLOR['REF'], None, 1.0)]
    for lab, rn, alpha, _ in ramps:
        for s, hatch in (('moderate', '///'), ('ambitious', None)):
            names.append((f'P5-{s}' + (f'-{rn}' if rn else ''), P_COLOR['P5'], hatch, alpha))
    scen = list(SCENARIOS)
    w = 0.12
    for i, sc in enumerate(scen):
        for k, (nm, col, hatch, alpha) in enumerate(names):
            r = _run(res, nm, sc)
            x = i + (k - (len(names) - 1) / 2) * w
            ax.bar(x, r['carbon_kt'], width=w * 0.92, color='white' if hatch else col, edgecolor=col, hatch=hatch,
                   alpha=alpha, lw=1.2)
            ax.text(x, r['carbon_kt'], f"{r['carbon_kt'] / 1e3:,.1f}", ha='center', va='bottom', fontsize=6.3,
                    color=INK, rotation=90)
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels([SCENARIOS[s][0] for s in scen])
    _hline(ax, bar_kt, AR_COLOR, '-', f'AR {bar_kt:,.0f}', len(scen) - 0.55)
    _hline(ax, batp_kt, ATP_COLOR, '--', f'AtP {batp_kt:,.0f}', len(scen) - 0.55)
    ax.set_xlim(-0.6, len(scen) - 0.1)
    ax.set_ylabel('cumulative carbon 2026-2050, kt CO$_2$e (labels: Mt)')
    ax.set_title('Cumulative carbon by replacement scenario and ramp', fontsize=10)
    handles = [Patch(color=P_COLOR['REF'], label='REF')]
    for lab, rn, alpha, _ in ramps:
        full = {'by2030': 'full by 2030', 'by2035': 'full by 2035 (adopted)', 'by2045': 'full by 2045'}[lab]
        handles += [Patch(facecolor='white', edgecolor=P_COLOR['P5'], hatch='///', alpha=alpha, label=f'P5 central, {full}'),
                    Patch(color=P_COLOR['P5'], alpha=alpha, label=f'P5 stretch, {full}')]
    ax.legend(handles=handles, fontsize=7.5, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=4)
    _style(ax)
    a = res['annual']
    a = a[a['scenario'] == REFERENCE]
    d = a[a['run'] == 'REF']
    ax2.plot(d['year'], d['carbon_kt'], color=P_COLOR['REF'], lw=2.0, label='REF')
    for lab, rn, alpha, ls in ramps:
        for s, lw in (('moderate', 1.4), ('ambitious', 2.4)):
            nm = f'P5-{s}' + (f'-{rn}' if rn else '')
            d = a[a['run'] == nm]
            ax2.plot(d['year'], d['carbon_kt'], color=P_COLOR['P5'], ls=ls, lw=lw, label=nm)
    d0 = a[a['run'] == 'REF']
    ax2.plot(d0['year'], d0['B_AR_kt'], color=AR_COLOR, lw=2.0, gid=figaudit.BOUNDARY, label='AR boundary')
    ax2.plot(d0['year'], d0['B_AtP_kt'], color=ATP_COLOR, lw=2.0, ls='--', gid=figaudit.BOUNDARY, label='AtP boundary')
    ax2.set_ylim(0, None)
    ax2.set_xlim(2026, 2050)
    ax2.set_xlabel('year')
    ax2.set_ylabel('annual carbon, kt CO$_2$e per year')
    ax2.set_title('Ramp sensitivity, S3-10: logistic, full by 2030 (dashed), 2035 (solid) or 2045 (dotted)', fontsize=10)
    ax2.legend(fontsize=7, frameon=False, loc='upper right', ncol=2)
    _style(ax2)
    fig.suptitle('Envelope: P0 and P5 under Low (S1), Reference (S3-10) and High (S2) replacement, and the ramp '
                 'sensitivities (2035 adopted after RECC, Pauliuk et al. 2024)', fontsize=11)
    fig.tight_layout()
    _save(fig, 'pw_5_envelope_SI')


def fig_l5_estimator(res):
    import matplotlib.pyplot as plt
    p = res['params']['L5']
    cases = pd.DataFrame(p['cases']).sort_values('ratio').reset_index(drop=True)
    x = cases['ratio'].values
    n = len(x)
    rng = np.random.default_rng(LV.L5_BOOTSTRAP_SEED)
    idx = rng.integers(0, n, size=(LV.L5_BOOTSTRAP_B, n))
    boot_sorted = np.sort(x[idx], axis=1)
    qs = np.linspace(0.02, 0.98, 97)
    curve = np.array([LV.hd_quantile(x, q) for q in qs])
    band = np.array([np.percentile(boot_sorted @ LV.hd_weights(n, q), [2.5, 97.5]) for q in qs])
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.fill_between(qs, band[:, 0], band[:, 1], color='#b7d3f6', label='bootstrap 95% band (B = 10,000, cases resampled)')
    ax.plot(qs, curve, color='#184f95', lw=2.0, label='Harrell-Davis quantile function')
    pos = (np.arange(1, n + 1) - 0.5) / n
    for typ, mk in (('Detached', 'o'), ('Townhouses', 's')):
        sel = cases['typology'].values == typ
        ax.scatter(pos[sel], x[sel], marker=mk, s=46, facecolor='white' if typ == 'Townhouses' else '#3b3b3b',
                   edgecolor='#3b3b3b', zorder=5, label=f'{typ} case ((i - 0.5) / n)')
    for i, cid in enumerate(cases['id']):
        ax.annotate(cid, (pos[i], x[i]), xytext=(4, -9), textcoords='offset points', fontsize=6.5, color=MUTED)
    for s, col in (('moderate', P_COLOR['P4']), ('ambitious', P_COLOR['P4'])):
        e = p['estimator'][s]
        ax.axvline(e['q'], color=col, lw=0.9, ls=':' if s == 'moderate' else '--')
        ax.errorbar(e['q'], e['r'], yerr=[[e['r'] - e['ci_lo']], [e['ci_hi'] - e['r']]], fmt='D', color=col,
                    ms=7, capsize=4, zorder=6, label=f"{s}: q = {e['q']:.2f}, r = {e['r']:.3f} "
                                                     f"(95% CI {e['ci_lo']:.3f}-{e['ci_hi']:.3f})")
    ax.axhline(1.0, color=MUTED, lw=0.8)
    ax.text(0.99, 1.005, 'pooled typology factor (r = 1)', ha='right', va='bottom', fontsize=7.5, color=MUTED)
    ax.set_xlim(0, 1)
    ax.set_xlabel('quantile q')
    ax.set_ylabel('A1-A3 per m$^2$ relative to the pooled typology factor (2025)')
    ax.set_title(f'L5 best-practice ratio: Harrell-Davis quantile of {n} independent case studies (detached, townhouses)',
                 fontsize=10.5)
    ax.legend(fontsize=7.5, loc='lower right', frameon=True, framealpha=0.92)
    _style(ax, 'both')
    fig.text(0.5, -0.06, 'Harrell & Davis (1982) Biometrika 69, 635; percentile bootstrap (Efron & Tibshirani 1993).\n'
             'q = 0.15 follows the top-15% convention of Commission Delegated Regulation (EU) 2021/2139, Annex I s. 7.7. '
             'Apartments (one independent case) are not in the sample.', ha='center', fontsize=8, style='italic')
    fig.tight_layout()
    _save(fig, 'pw_6_L5_estimator_SI')


def fig_shapley_levers(res):
    import matplotlib.pyplot as plt
    sh = res['shapley_levers']
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, metric, xl in ((axes[0], 'carbon_kt', 'reduction of cumulative carbon 2026-2050, kt CO$_2$e'),
                           (axes[1], 'LoE_AR', 'reduction of cumulative LoE AR')):
        for s in LV.SETTINGS:
            d = sh[(sh['metric'] == metric) & (sh['setting'] == s)].set_index('player')
            for k, L in enumerate(LV.LEVERS):
                y = k + (0.2 if s == 'moderate' else -0.2)
                col = P_COLOR[LV.LEVER_PATHWAY[L]]
                v = d.loc[L, 'reduction']
                ax.barh(y, v, height=0.38, color='white' if s == 'moderate' else col, edgecolor=col, lw=1.5)
                ax.text(max(v, 0), y, f' {v:,.0f} ({100 * d.loc[L, "share_of_reference_minus_P5"]:.0f}%) {s[0]}'
                        if metric == 'carbon_kt' else f' {v:.3f} {s[0]}', va='center', fontsize=7.5, color=INK)
        ax.set_yticks(range(len(LV.LEVERS)))
        ax.set_yticklabels([f'{L} {LV.LEVER_NAMES[L]}\n({LV.LEVER_PATHWAY[L]} {LV.PATHWAY_NAMES[LV.LEVER_PATHWAY[L]]})'
                            for L in LV.LEVERS], fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, color=INK, lw=0.6)
        ax.set_xlabel(xl)
        _style(ax, 'x')
        ax.set_xlim(min(0, ax.get_xlim()[0]), ax.get_xlim()[1] * 1.3)
    tot = {s: _run(res, 'REF')['carbon_kt'] - _run(res, f'P5-{s}')['carbon_kt'] for s in LV.SETTINGS}
    axes[0].set_title(f"Carbon: P0 - P5 = {tot['moderate']:,.0f} kt (central, open) / {tot['ambitious']:,.0f} kt "
                      f"(stretch, filled)", fontsize=10)
    axes[1].set_title('Cumulative LoE AR', fontsize=10)
    fig.suptitle('Shapley attribution of P0 - P5 to the five levers (S3-10; 32 subsets; values sum exactly to P0 - P5)',
                 fontsize=11)
    fig.tight_layout()
    _save(fig, 'pw_7_shapley_levers_SI')


T_STEPS = (('REF', 'P0\nbaseline'), ('P5-moderate', 'P5-central\nall pathways'), ('P5-ambitious', 'P5-stretch\nall pathways'),
           ('TL', 'T\nhyper-optimistic\ntheoretical limit'))
T_CAPTION = LV.TL_DISCLAIMER


def _step_run(res, name):
    if name == 'TL':
        return res['T']['cache'][(LV.TL_COMPONENTS, LV.TL_FROM2027)]
    if name == 'TL-gradual':
        return res['T']['cache'][(LV.TL_COMPONENTS, LV.TL_GRADUAL)]
    s = name.split('-')[1] if name != 'REF' else None
    return res['get'](REFERENCE, LV.pathway_levers(name.split('-')[0], s) if s else {})


def _human(res, name):
    """2027-2050: mean new-dwelling size (m2), floor area per person in new dwellings (m2), dwellings built per year."""
    E = _step_run(res, name)['E']
    S = E['pop'] / E['hh']
    w = slice(2, None)
    dw = E['dwell_in_scope'][w]
    return dict(size=E['total'][w].sum() / dw.sum(), per_person=E['total'][w].sum() / (dw * S[w]).sum(),
                per_year=float(np.asarray(engine.requirement(E))[w].mean()))


def _t_row(res, name):
    if name in T_RUNS:
        return next(r for r in res['T']['rows'] if r['run'] == name)
    return _run(res, name)


def fig_staircase(res):
    import matplotlib.pyplot as plt
    import figaudit
    import matplotlib.patheffects as pe
    from matplotlib.patches import Patch
    fig = plt.figure(figsize=(15, 11))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.55, wspace=0.18)
    ax = fig.add_subplot(gs[0, :])
    xs = np.arange(len(T_STEPS))
    p0 = _t_row(res, 'REF')
    halo = [pe.Stroke(linewidth=4, foreground='white'), pe.Normal()]
    for key, col, ls, nm in (('LoE_AR', AR_COLOR, '-', 'acquired rights (AR)'), ('LoE_AtP', ATP_COLOR, '--', 'ability to pay (AtP)')):
        ys = [_t_row(res, n)[key] for n, _ in T_STEPS]
        ax.step(np.r_[xs - 0.4, xs[-1] + 0.4], np.r_[ys, ys[-1]], where='post', color=col, ls=ls, lw=2.2,
                path_effects=halo, label=f'cumulative LoE, {nm}')
        ax.scatter(xs, ys, color=col, s=36, zorder=5)
        for x, y, (n, _) in zip(xs, ys, T_STEPS):
            d = 100 * (y / p0[key] - 1)
            ax.annotate(f'{y:.2f}' + ('' if n == 'REF' else f' ({d:+.0f}%)'), (x, y), xytext=(0, 7),
                        textcoords='offset points', ha='center', fontsize=8.5, color=INK, path_effects=halo)
    ax.axhline(1.0, color='black', lw=1.0, gid=figaudit.BOUNDARY)
    ax.text(-0.45, 1.0, 'LoE = 1', va='bottom', fontsize=8.5, color=INK)
    ax.set_yscale('log')
    ax.set_yticks([0.5, 1, 2, 5, 10, 20])
    ax.set_yticklabels(['0.5', '1', '2', '5', '10', '20'])
    ax.set_ylim(0.3, 30)
    ax.set_xlim(-0.5, len(T_STEPS) - 0.3)
    lab = []
    for n, l in T_STEPS:
        h = _human(res, n)
        lab.append(f"{l}\n{h['size']:.0f} m² per new dwelling\n{h['per_person']:.0f} m² per person\n"
                   f"{h['per_year'] / 1e3:.1f}k dwellings / yr")
    ax.set_xticks(xs)
    ax.set_xticklabels(lab, fontsize=8.5)
    ax.set_ylabel('cumulative level of exceedance 2026-2050 (log)')
    ax.set_title('From the baseline to the hyper-optimistic theoretical limit T (S3-10): cumulative LoE; indicators are '
                 '2027-2050 means', fontsize=11)
    g = res['T']['gap']['TL']
    if g['within_AR']:
        resid = f"T within the AR budget: margin {g['margin_AR_kt']:,.0f} kt"
    else:
        rs = g['residual']
        resid = (f"Residual to LoE AR = 1: cut {100 * rs['cut_of_2027_2050_construction']:.1f}% of 2027-2050 construction\n"
                 f"= {rs['dwellings_not_built_2027_2050']:,.0f} dwellings not built, "
                 f"{rs['new_residents_housed_in_existing_dwellings']:,.0f} new residents\nhoused in existing dwellings")
    ax.annotate(resid, (xs[-1], 1.0), xytext=(xs[-1] - 0.95, 0.55), fontsize=8.5, color=INK, ha='left', va='center',
                arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.6), path_effects=halo)
    ax.legend(fontsize=8.5, loc='upper right', frameon=False)
    _style(ax)
    colors = _band_colors()
    bd = pd.concat([res['bands'], res['T']['bands']], ignore_index=True)
    bd = bd[(bd['scenario'] == REFERENCE) & (bd['definition'] == 'in_scope')]
    runs = ['REF', 'P5-ambitious', 'TL']
    for j, (col, ylab, ttl) in enumerate((('gfa_Mm2', 'floor area 2026-2050, Mm$^2$', 'Floor area by demand band'),
                                          ('carbon_kt', 'carbon 2026-2050, kt CO$_2$e', 'Carbon by demand band'))):
        a = fig.add_subplot(gs[1, j])
        fmt = (lambda v: f'{v:,.1f}') if col == 'gfa_Mm2' else (lambda v: f'{v:,.0f}')
        for i, rn in enumerate(runs):
            d = bd[bd['run'] == rn].set_index('band')
            pos, neg = 0.0, 0.0
            for band, _ in FIG_BANDS:
                v = float(d.loc[band, col])
                if abs(v) < 1e-9:
                    continue
                base = pos if v > 0 else neg
                a.bar(i, v, bottom=base, color=colors[band], edgecolor='white', lw=1.0, width=0.6,
                      hatch='..' if band in UNTARGETED else None)
                if v > 0:
                    pos += v
                else:
                    neg += v
            a.text(i, pos, fmt(pos + neg), ha='center', va='bottom', fontsize=8.5, color=INK)
        a.axhline(0, color=INK, lw=0.8)
        a.set_xticks(range(len(runs)))
        a.set_xticklabels(['REF', 'P5-ambitious', 'T (limit)'], fontsize=9)
        a.set_ylabel(ylab)
        a.set_title(ttl, fontsize=10)
        _style(a)
    fig.legend(handles=[Patch(facecolor=colors[b], hatch='..' if b in UNTARGETED else None, edgecolor='white',
                              label=b + (' (untargeted)' if b in UNTARGETED else '')) for b, _ in FIG_BANDS],
               loc='lower center', ncol=3, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.text(0.5, -0.08, T_CAPTION + ' T1 no idle stock (v = 0, surplus absorbed), T2 no extra space (size = S x OLF), '
             'T3 minimum OLF of the case studies (A_1, 19.7 m² per person) for every typology, T4 each typology\'s best '
             f'case-study A1-A3, T5 lowest soil order, T6 urban densification ({100 * LV.TL6_SHARE:.0f}% of non-replacement '
             'floor area on developed land, zero soil; Auckland Council 2021); BAU decarbonisation applies. In its '
             'zero-building years (released vacant stock used, banking rule) every band is zero.', ha='center', fontsize=8,
             style='italic', wrap=True)
    _save(fig, 'pw_8_staircase')


def fig_T_shapley(res):
    import matplotlib.pyplot as plt
    sh = res['T']['shapley']
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, metric, xl in ((axes[0], 'carbon_kt', 'reduction of cumulative carbon 2026-2050, kt CO$_2$e'),
                           (axes[1], 'LoE_AR', 'reduction of cumulative LoE AR')):
        d = sh[sh['metric'] == metric].set_index('player')
        players = list(LV.TL_COMPONENTS) + [LV.TL_FROM2027]
        for k, pl in enumerate(players):
            v = float(d.loc[pl, 'reduction'])
            is_t = pl != LV.TL_FROM2027
            ax.barh(k, v, height=0.6, color='#3b3b3b' if is_t else 'white', edgecolor='#3b3b3b', lw=1.2,
                    hatch=None if is_t else '///')
            share = d.loc[pl, 'share_of_P5_ambitious_from2027_minus_TL']
            ax.text(v, k, (f' {v:,.0f}' if metric == 'carbon_kt' else f' {v:.3f}') +
                    (f' ({100 * share:.0f}%)' if is_t else ' (separate line)'), va='center', fontsize=8, color=INK)
        ax.set_yticks(range(len(players)))
        ax.set_yticklabels([f'{p} {LV.TL_NAMES[p]}' if p in LV.TL_NAMES else 'P5-stretch: ramp -> instant start'
                            for p in players], fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel(xl)
        ax.set_xlim(0, ax.get_xlim()[1] * 1.3)
        _style(ax, 'x')
    fig.suptitle(f'Shapley attribution of P5-stretch (instant start) - T to T1-T{len(LV.TL_COMPONENTS)} '
                 f'({2 ** len(LV.TL_COMPONENTS)} subsets, exact; S3-10)', fontsize=11)
    fig.text(0.5, -0.04, 'Shares are of P5-stretch with the instant start minus T. The hatched bar is the separate effect '
             'of starting P5-stretch at full strength in 2027 instead of on the logistic ramp. ' + T_CAPTION,
             ha='center', fontsize=8, style='italic', wrap=True)
    fig.tight_layout()
    _save(fig, 'pw_9_T_shapley_SI')


def fig_T_annual(res):
    import matplotlib.pyplot as plt
    import figaudit
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    series = (('REF', '#9a9a9a', '-', 2.0), ('P5-ambitious', '#3b3b3b', '--', 1.8), ('TL', 'black', '-', 2.6),
              ('TL-gradual', 'black', ':', 2.0))
    ref = res['ctxs'][REFERENCE]
    yrs = ref['years']
    ends = []
    for nm, col, ls, lw in series:
        E = _step_run(res, nm)['E']
        ax.plot(yrs[1:], E['carbon'][1:] / M6, color=col, ls=ls, lw=lw, label=nm)
        ends.append((E['carbon'][-1] / M6, nm))
        ax2.plot(yrs[1:], np.asarray(engine.requirement(E))[1:] / 1e3, color=col, ls=ls, lw=lw, label=nm)
    ylast = -1e9
    for v, nm in sorted(ends):                    # direct labels, nudged apart
        y = max(v, ylast + 35)
        ax.annotate(f'{nm} {v:,.0f}', (2050, v), xytext=(2050.5, y), fontsize=7.5, va='center', color=INK,
                    arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.5))
        ylast = y
    ax.plot(yrs[1:], ref['b_ar'] / M6, color=AR_COLOR, lw=2.0, gid=figaudit.BOUNDARY, label='AR boundary')
    ax.plot(yrs[1:], ref['b_atp'] / M6, color=ATP_COLOR, lw=2.0, ls='--', gid=figaudit.BOUNDARY, label='AtP boundary')
    ax.set_xlim(2026, 2053)
    ax.set_ylim(0, None)
    ax.set_xlabel('year')
    ax.set_ylabel('annual carbon, kt CO$_2$e per year')
    ax.set_title('Annual carbon: P0, P5-stretch, T and T with the logistic ramp', fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc='upper right')
    _style(ax)
    zy = res['T']['indicators']['TL']['zero_building_years']
    if zy:
        ax2.axvspan(min(zy) - 0.5, max(zy) + 0.5, color='#e1e0d9', zorder=0)
        ax2.text((min(zy) + max(zy)) / 2, ax2.get_ylim()[1] * 0.02 + 1, f'T: no new building\n{min(zy)}-{max(zy)}\n'
                 '(released vacant\nstock used)', ha='center', va='bottom', fontsize=8, color=INK)
    ax2.set_xlim(2026, 2050)
    ax2.set_ylim(0, None)
    ax2.set_xlabel('year')
    ax2.set_ylabel('dwellings built per year, thousands (all categories)')
    ax2.set_title('Dwellings built per year (banking rule: never negative)', fontsize=10)
    ax2.legend(fontsize=8, frameon=False, loc='upper right')
    _style(ax2)
    fig.text(0.5, -0.05, T_CAPTION, ha='center', fontsize=8, style='italic', wrap=True)
    fig.tight_layout()
    _save(fig, 'pw_10_T_annual_SI')


def figures(res):
    """The pathway figures (style.save_figure; each file is overwritten in place, so a
    pathways-only run replaces exactly the pathway figures)."""
    import matplotlib
    matplotlib.use('Agg')
    fig_bands_by_pathway(res)
    fig_shapley_waterfall(res)
    fig_solution_space(res)
    fig_annual(res)
    fig_envelope(res)
    fig_l5_estimator(res)
    fig_shapley_levers(res)
    if 'T' in res:
        fig_staircase(res)
        fig_T_shapley(res)
        fig_T_annual(res)


if __name__ == '__main__':
    main()
