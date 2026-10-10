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

AESA gap: boundaries B_AR, B_AtP by year for the Reference from outputs/data/aesa/annual.csv;
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
    """B_AR and B_AtP (kg/yr) by year 2026-2050 for the Reference, and P_NZ, from outputs/data/aesa/annual.csv."""
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
    # the same step for P2 under each adoption-path sensitivity: end year E -> E + 1 (P2 runs under
    # these windows are computed here only; they are not rows of runs.csv)
    yrs = list(ref['years'])
    p_ref = a_ref.loc[REFERENCE, 'carbon_kt']
    for rs in LV.ADOPTION_SENSITIVITIES:
        E = rs['end']
        wr = LV.ramp_named(ref['years'], rs['name'])
        for s in LV.SETTINGS:
            R = get(REFERENCE, LV.pathway_levers('P2', s), rs['name'], False)
            c = pd.Series(np.asarray(R['E']['carbon'], float) / M6, index=yrs)
            d = pd.Series(np.asarray(R['E']['dwell_in_scope'], float), index=yrs)
            diag[f"end_of_ramp_step_{run_name('P2', s, rs['name'])}"] = dict(
                end_year=E, w_E_minus_w_E_minus_1=float(wr[yrs.index(E)] - wr[yrs.index(E - 1)]),
                carbon_E_kt=float(c[E]), carbon_E_plus_1_kt=float(c[E + 1]), carbon_step_kt=float(c[E + 1] - c[E]),
                carbon_step_pct=float(100 * (c[E + 1] / c[E] - 1)),
                reference_carbon_step_kt=float(p_ref[E + 1] - p_ref[E]),
                step_relative_to_reference_kt=float((c[E + 1] - c[E]) - (p_ref[E + 1] - p_ref[E])),
                dwellings_step=float(d[E + 1] - d[E]))
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


def run_tl(ctx, params, pT, comps, ramp_name=LV.TL_FROM2027, base_setting=LV.TL_BASE_SETTING):
    """A TL-family run. 1) the TL inputs (levers.apply_tl); 2) the requirement without a join; 3) the
    banking rule on requirement + absorbed near-term excess; 4) engine.forward with the stock-adding
    join join_t = built_t - requirement_t (join_redev = 0), so the stock identity holds and dwellings
    built = built_t >= 0; 5) soil: the TL5 / TL6 soil factor of each year and the soil-bearing share
    clipped to [0, 1] (zero-building years) applied exactly through the intensity (see below)."""
    fi, join_abs, _, info = LV.apply_tl(ctx, params, pT, comps, ramp_name, ctx['E_nojoin'], base_setting)
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
    # ---- MODEL v2.0.0: TL relative to P5 Moderate (TL1-TL7, 128 subsets) -------------------------
    # TL = P5 Moderate + TL1-TL7 must be TL (P5 Ambitious + TL1-TL6) exactly: TL1-TL6 override every
    # Ambitious lever setting but L4, which TL7 sets to its Ambitious d.
    cache2 = {}

    def getT2(comps):
        key = tuple(c for c in LV.TL_COMPONENTS_V2 if c in comps)
        if key not in cache2:
            cache2[key] = run_tl(ref, params, pT, comps, LV.TL_FROM2027, LV.TL_BASE_SETTING_V2)
        return cache2[key]

    full2 = LV.TL_COMPONENTS_V2
    RT2 = getT2(full2)
    for k in ('carbon', 'total', 'upfront', 'dwell_in_scope'):
        a, b = np.asarray(RT2['E'][k], float), np.asarray(RT['E'][k], float)
        if not np.allclose(a, b, rtol=1e-12, atol=0.0):
            raise SystemExit(f'STOP: TL relative to P5 Moderate (TL1-TL7) differs from TL in {k!r}.')
    vals2 = {'carbon_kt': {}, 'LoE_AR': {}, 'LoE_AtP': {}}
    sub2 = []
    for S_ in subsets(full2):
        R_ = getT2(S_)
        m = metrics(ref, R_, LV.tl_label(S_, components=full2, base='moderate'), 'TL')
        for metric in vals2:
            vals2[metric][S_] = m[metric]
        sub2.append(dict(level='TL', subset=LV.tl_label(S_, components=full2, base='moderate'), n_players=len(S_),
                         carbon_kt=m['carbon_kt'], LoE_AR=m['LoE_AR'], LoE_AtP=m['LoE_AtP'], gfa_Mm2=m['gfa_Mm2'],
                         dwellings_built_min_year=m['dwellings_built_min_year']))
    shap2, exact2 = [], {}
    for metric, v in vals2.items():
        r_, ex = shapley_rows(v, full2, 'TL', metric, 'TL', LV.TL_NAMES)
        for x in r_:
            x['share_of_P5_moderate_from2027_minus_TL'] = x.pop('share_of_reference_minus_P5')
        shap2 += r_
        exact2[metric] = ex
    p5m = res['runs'][(res['runs']['run'] == 'P5-moderate') & (res['runs']['scenario'] == REFERENCE)].iloc[0]
    for metric in vals2:
        shap2.append(dict(level='TL', setting='TL', metric=metric, player=LV.TL_FROM2027,
                          name=N._ascii(f"P5 Combined: adoption path -> {N.ADOPTION['from2027']} (separate line, "
                                        f"not a Shapley player)"),
                          reduction=float(p5m[metric] - vals2[metric][frozenset()]),
                          share_of_P5_moderate_from2027_minus_TL=float('nan')))
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
               shapley_v2=pd.DataFrame(shap2), subsets_v2=pd.DataFrame(sub2), shapley_exact_v2=exact2, cache_v2=cache2,
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
    for metric, (phi, total) in list(rt['shapley_exact'].items()) + list(rt['shapley_exact_v2'].items()):
        if sum(phi.values()) != total:
            raise SystemExit(f'TL Shapley efficiency fails ({metric}).')


def write_tl(res, rt):
    """Append the TL rows to the pathway tables and write theoretical_limit.json and the TL Shapley tables."""
    _csv(pd.concat([res['runs'], pd.DataFrame(rt['rows'])], ignore_index=True), 'runs.csv')
    _csv(pd.concat([res['annual'], pd.DataFrame(rt['annual'])], ignore_index=True), 'annual.csv')
    _csv(pd.concat([res['bands'], rt['bands']], ignore_index=True), 'bands.csv')
    _csv(rt['shapley'], 'shapley_theoretical_limit.csv')
    _csv(rt['subsets'], 'shapley_theoretical_limit_subsets.csv')
    _csv(rt['shapley_v2'], 'shapley_theoretical_limit_moderate.csv')            # MODEL v2.0.0: TL1-TL7 vs P5 Moderate
    _csv(rt['subsets_v2'], 'shapley_theoretical_limit_moderate_subsets.csv')
    rows = {r['run']: r for r in rt['rows']}
    out = dict(run_mode=RUN_MODE, disclaimer=LV.TL_DISCLAIMER, definition=dict(
        base='P5 Ambitious (L4 removals -40%; L2 / L3 replaced by TL1)', start=2027, bau=LV.TL_BAU_NOTE,
        tl6=dict(share=LV.TL6_SHARE, components=LV.TL6_COMPONENTS, source=LV.TL6_SOURCE, assumptions=LV.TL6_ASSUMPTIONS),
        adoption=('from2027: w = 1 for every lever in 2027-2050; 2026 observed and untouched (TL, gradual adoption: '
                  'the adopted logistic path, full by 2035)'),
        components={k: LV.TL_NAMES[k] for k in LV.TL_COMPONENTS}), resolved=rt['params_T'],
        metrics={k: {c: v for c, v in r.items() if isinstance(v, (int, float, str, bool, np.floating, np.integer))}
                 for k, r in rows.items()},
        indicators=rt['indicators'], gap=rt['gap'], solution_space_marker=rt['solution_space_marker'],
        shapley=N.columns(rt['shapley']).to_dict(orient='records'),
        relative_to_P5_moderate=dict(
            definition='TL = P5 Combined (Moderate) with TL1-TL7 at full strength from 2027; identical to P5 Ambitious '
                       'with TL1-TL6 (TL1-TL6 override every Ambitious setting but L4; TL7 = L4 at d = 0.40)',
            components={k: LV.TL_NAMES[k] for k in LV.TL_COMPONENTS_V2},
            shapley=N.columns(rt['shapley_v2']).to_dict(orient='records')))
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
# FIGURES (outputs/diagnostics/pathways_si/; the headline figures H7-H10 are drawn by headline.py
# from the data files written above)
# ============================================================
NAMES = {'REF': N.SCENARIOS['REF'], **LV.PATHWAY_NAMES}
BAND_ID = {N.band_data_label(b): b for b in N.BANDS_IN_SCOPE}


def _save(fig, name, note=None):
    import matplotlib.pyplot as plt
    style.save_figure(fig, name, note=note)
    plt.close(fig)


def _run(res, name, scen=REFERENCE):
    """The runs row of `name` under variant `scen` (the no-lever run carries the variant id)."""
    r = res['runs']
    if name == REFERENCE:
        name = scen
    return r[(r['run'] == name) & (r['scenario'] == scen)].iloc[0]


def _line(run):
    """Colour, line style and width of a run in the release style."""
    S = style
    if run in ('REF', REFERENCE):
        return dict(color=S.REFERENCE, ls='-', lw=S.LW_BOLD)
    if run == 'TL':
        return dict(color=S.TL, ls='-', lw=S.LW_BOLD)
    if run == 'TL-gradual':
        return dict(color=S.TL_GRADUAL, ls='-', lw=S.LW)
    P, setting = run.split('-')[:2]
    return dict(color=S.PATHWAY[P], ls=S.SETTING[setting]['ls'], lw=S.LW_BOLD if P == 'P5' else S.LW)


def fig_annual(res):
    """D28: annual carbon of the Reference and P1-P5 (both settings) against the annual boundaries."""
    import matplotlib.pyplot as plt
    import plotting as P
    S = style
    a = res['annual']
    a = a[a['scenario'] == REFERENCE]
    fig, ax = plt.subplots(figsize=S.figsize('double', 92))
    for name in ['REF'] + [f'{p}-{s}' for p in ('P1', 'P2', 'P3', 'P4', 'P5') for s in LV.SETTINGS]:
        d = a[a['run'] == name]
        ax.plot(d['year'], d['carbon_kt'], label=N.run_label(name) if name != 'REF' else N.SCENARIOS['REF'],
                **_line(name))
    d0 = a[a['run'] == 'REF']
    P.boundary_lines(ax, d0['year'], d0['B_AR_kt'], d0['B_AtP_kt'])
    ax.set_xlim(2026, 2050)
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=S.FONT_SMALL)
    fig.tight_layout()
    _save(fig, 'D28_pathways_annual',
          'Reference variant; Moderate solid, Ambitious dashed. Construction (A1–A5 and soil) in the construction '
          'year plus maintenance (B2, B4) within 2026–2050. 2026 is observed and identical in every run; the levers '
          f"follow the adopted logistic adoption path ({N.ADOPTION['by2035']}).")


def fig_envelope(res):
    """D29: P5 under Low / Reference / High replacement and the adoption paths."""
    import matplotlib.pyplot as plt
    import plotting as P
    from matplotlib.patches import Patch
    S = style
    bar_kt, batp_kt = res['backcast']['B_AR_kt'], res['backcast']['B_AtP_kt']
    ramps = [('by2030', 'by2030', 0.55, '--'), ('by2035', None, 1.0, '-'), ('by2045', 'by2045', 0.3, ':')]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=S.figsize('double', 96), gridspec_kw=dict(width_ratios=[1.3, 1]))
    names = [('REF', S.REFERENCE, None, 1.0)]
    for lab, rn, alpha, _ in ramps:
        for s_, hatch in (('moderate', '////'), ('ambitious', None)):
            names.append((f'P5-{s_}' + (f'-{rn}' if rn else ''), S.PATHWAY['P5'], hatch, alpha))
    scen = list(SCENARIOS)
    w = 0.12
    for i, sc in enumerate(scen):
        for k, (nm, col, hatch, alpha) in enumerate(names):
            r = _run(res, nm, sc)
            x = i + (k - (len(names) - 1) / 2) * w
            ax.bar(x, r['carbon_kt'], width=w * 0.92, color='white' if hatch else col, edgecolor=col, hatch=hatch,
                   alpha=alpha, lw=S.LW_THIN)
            ax.text(x, r['carbon_kt'], f" {r['carbon_kt'] / 1e3:,.1f}", ha='center', va='bottom', fontsize=S.FONT_MIN,
                    rotation=90)
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels([SCENARIOS[s_][0] for s_ in scen])
    P.boundary_hline(ax, 'AR', bar_kt, label=f"{S.BOUNDARY['AR']['label']} budget: {bar_kt:,.0f} kt")
    P.boundary_hline(ax, 'AtP', batp_kt, label=f"{S.BOUNDARY['AtP']['label']} budget: {batp_kt:,.0f} kt")
    ax.set_xlim(-0.6, len(scen) - 0.4)
    ax.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e; labels: Mt)')
    P.thousands(ax.yaxis)
    ax.grid(axis='x', visible=False)
    P.panel(ax, 'a', 'Cumulative, by replacement variant and adoption path')
    handles = [Patch(color=S.REFERENCE, label='No pathway (the variant itself)')]
    for lab, rn, alpha, _ in ramps:
        handles += [Patch(facecolor='white', edgecolor=S.PATHWAY['P5'], hatch='////', alpha=alpha,
                          label=f"P5 Moderate, {N.ADOPTION[lab]}"),
                    Patch(color=S.PATHWAY['P5'], alpha=alpha, label=f"P5 Ambitious, {N.ADOPTION[lab]}")]
    handles += ax.get_legend_handles_labels()[0]
    ax.legend(handles=handles, fontsize=S.FONT_MIN, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.1),
              ncol=2)
    a = res['annual']
    a = a[a['scenario'] == REFERENCE]
    d = a[a['run'] == 'REF']
    ax2.plot(d['year'], d['carbon_kt'], label=N.SCENARIOS['REF'], **_line('REF'))
    for lab, rn, alpha, ls in ramps:
        for s_, lw in (('moderate', S.LW_THIN), ('ambitious', S.LW_BOLD)):
            nm = f'P5-{s_}' + (f'-{rn}' if rn else '')
            d = a[a['run'] == nm]
            ax2.plot(d['year'], d['carbon_kt'], color=S.PATHWAY['P5'], ls=ls, lw=lw,
                     label=N.run_label(nm) + ('' if rn else f", {N.ADOPTION['by2035']}"))
    d0 = a[a['run'] == 'REF']
    P.boundary_lines(ax2, d0['year'], d0['B_AR_kt'], d0['B_AtP_kt'], label=False)
    ax2.set_ylim(0, None)
    ax2.set_xlim(2026, 2050)
    ax2.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.panel(ax2, 'b', 'Annual, Reference: adoption paths')
    ax2.legend(fontsize=S.FONT_MIN, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=1)
    fig.tight_layout()
    _save(fig, 'D29_adoption_and_variants',
          'b: logistic adoption, full roll-out by 2030 (dashed), 2035 (solid, adopted after RECC, Pauliuk et al. '
          '2024) or 2045 (dotted); Moderate thin, Ambitious thick.')


def fig_l5_estimator(res):
    """D30: the L5 best-practice ratio, Harrell-Davis quantile of the independent case studies."""
    import matplotlib.pyplot as plt
    S = style
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
    fig, ax = plt.subplots(figsize=S.figsize('double', 92))
    ax.fill_between(qs, band[:, 0], band[:, 1], color=S.SEQUENTIAL[1], lw=0,
                    label=f'Bootstrap 95% band (B = {LV.L5_BOOTSTRAP_B:,}, cases resampled)')
    ax.plot(qs, curve, color=S.SEQUENTIAL[6], lw=S.LW_BOLD, label='Harrell–Davis quantile function')
    pos = (np.arange(1, n + 1) - 0.5) / n
    for typ, mk in (('Detached', 'o'), ('Townhouses', 's')):
        sel = cases['typology'].values == typ
        ax.scatter(pos[sel], x[sel], marker=mk, s=14, facecolor='white' if typ == 'Townhouses' else S.INK,
                   edgecolor=S.INK, lw=S.LW_THIN, zorder=5, label=f'{typ} case, at (i − 0.5) / n')
    for i, cid in enumerate(cases['id']):
        ax.annotate(cid, (pos[i], x[i]), xytext=(3, -7), textcoords='offset points', fontsize=S.FONT_MIN, color=S.MUTED)
    for s_ in LV.SETTINGS:
        e = p['estimator'][s_]
        ax.axvline(e['q'], color=S.PATHWAY['P4'], lw=S.LW_THIN, ls=S.SETTING[s_]['ls'])
        ax.errorbar(e['q'], e['r'], yerr=[[e['r'] - e['ci_lo']], [e['ci_hi'] - e['r']]], fmt='D', color=S.PATHWAY['P4'],
                    mfc='white' if s_ == 'moderate' else S.PATHWAY['P4'], ms=4, capsize=2, lw=S.LW, zorder=6,
                    label=f"{N.SETTINGS[s_]}: q = {e['q']:.2f}, r = {e['r']:.3f} (95% CI {e['ci_lo']:.3f}–{e['ci_hi']:.3f})")
    ax.axhline(1.0, color=S.MUTED, lw=S.LW_THIN)
    ax.text(0.99, 1.005, 'pooled typology factor (r = 1)', ha='right', va='bottom', fontsize=S.FONT_SMALL, color=S.MUTED)
    ax.set_xlim(0, 1)
    ax.set_xlabel('Quantile q')
    ax.set_ylabel('A1–A3 per m² relative to the pooled typology factor (2025)')
    ax.legend(fontsize=S.FONT_SMALL, loc='lower right', frameon=True, framealpha=0.92, edgecolor='none')
    fig.tight_layout()
    _save(fig, 'D30_l5_estimator',
          f'L5 best-practice ratio: Harrell–Davis quantile of {n} independent case studies (detached, townhouses); '
          'Harrell & Davis (1982) Biometrika 69, 635; percentile bootstrap (Efron & Tibshirani 1993). The Ambitious '
          'q = 0.15 follows the top-15% convention of Commission Delegated Regulation (EU) 2021/2139, Annex I s. 7.7. '
          'Apartments (one independent case) are not in the sample.')


def fig_shapley_levers(res):
    """D31: Shapley attribution of Reference - P5 to the five levers."""
    import matplotlib.pyplot as plt
    import plotting as P
    S = style
    sh = res['shapley_levers']
    fig, axes = plt.subplots(1, 2, figsize=S.figsize('double', 84))
    tot = {s_: _run(res, 'REF')['carbon_kt'] - _run(res, f'P5-{s_}')['carbon_kt'] for s_ in LV.SETTINGS}
    for ax, metric, xl, letter in ((axes[0], 'carbon_kt', 'Reduction of carbon 2026–2050 (kt CO₂e)', 'a'),
                                   (axes[1], 'LoE_AR', 'Reduction of the cumulative LoE AR', 'b')):
        for s_ in LV.SETTINGS:
            d = sh[(sh['metric'] == metric) & (sh['setting'] == s_)].set_index('player')
            for k, L in enumerate(LV.LEVERS):
                y = k + (-0.2 if s_ == 'moderate' else 0.2)
                col = S.PATHWAY[LV.LEVER_PATHWAY[L]]
                v = d.loc[L, 'reduction']
                ax.barh(y, v, height=0.38, color='white' if s_ == 'moderate' else col, edgecolor=col, lw=S.LW)
                ax.text(max(v, 0), y, f' {v:,.0f} ({100 * d.loc[L, "share_of_reference_minus_P5"]:.0f}%)'
                        if metric == 'carbon_kt' else f' {v:.3f}', va='center', fontsize=S.FONT_MIN)
        ax.set_yticks(range(len(LV.LEVERS)))
        ax.set_yticklabels([f'{L} {LV.LEVER_NAMES[L]}\n({LV.LEVER_PATHWAY[L]} {LV.PATHWAY_NAMES[LV.LEVER_PATHWAY[L]]})'
                            for L in LV.LEVERS], fontsize=S.FONT_SMALL)
        ax.invert_yaxis()
        ax.axvline(0, color=S.INK, lw=S.LW_THIN)
        ax.set_xlabel(xl)
        ax.grid(axis='y', visible=False)
        ax.set_xlim(min(0, ax.get_xlim()[0]), ax.get_xlim()[1] * 1.35)
        if metric == 'carbon_kt':
            P.thousands(ax.xaxis)
        P.panel(ax, letter, 'Carbon' if metric == 'carbon_kt' else 'Cumulative LoE AR')
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor='white', edgecolor=S.INK, label='Moderate (open)'),
                        Patch(color=S.INK, label='Ambitious (filled)')], loc='lower center', ncol=2,
               bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, 'D31_shapley_levers',
          f"Reference variant; 32 subsets, exact; the values add up to Reference − P5: {tot['moderate']:,.0f} kt "
          f"(Moderate) and {tot['ambitious']:,.0f} kt (Ambitious). Shares are of Reference − P5.")


T_STEPS = (('REF', N.SCENARIOS['REF']), ('P5-moderate', 'P5 Combined,\nModerate'),
           ('P5-ambitious', 'P5 Combined,\nAmbitious'), ('TL', 'TL Theoretical\nlimit'))
T_CAPTION = LV.TL_DISCLAIMER


def _step_run(res, name):
    if name == 'TL':
        return res['T']['cache'][(LV.TL_COMPONENTS, LV.TL_FROM2027)]
    if name == 'TL-gradual':
        return res['T']['cache'][(LV.TL_COMPONENTS, LV.TL_GRADUAL)]
    s_ = name.split('-')[1] if name != 'REF' else None
    return res['get'](REFERENCE, LV.pathway_levers(name.split('-')[0], s_) if s_ else {})


def _human(res, name):
    """2027-2050: mean new-dwelling size (m2), floor area per person in new dwellings (m2), dwellings built per year."""
    E = _step_run(res, name)['E']
    S_ = E['pop'] / E['hh']
    w = slice(2, None)
    dw = E['dwell_in_scope'][w]
    return dict(size=E['total'][w].sum() / dw.sum(), per_person=E['total'][w].sum() / (dw * S_[w]).sum(),
                per_year=float(np.asarray(engine.requirement(E))[w].mean()))


def _t_row(res, name):
    if name in T_RUNS:
        return next(r for r in res['T']['rows'] if r['run'] == name)
    return _run(res, name)


def fig_staircase(res):
    """D32: Reference -> P5 -> TL: cumulative LoE and the human terms; floor area and carbon by demand band."""
    import matplotlib.pyplot as plt
    import figaudit
    import plotting as P
    S = style
    fig = plt.figure(figsize=S.figsize('double', 150))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.75, wspace=0.28)
    ax = fig.add_subplot(gs[0, :])
    xs = np.arange(len(T_STEPS))
    p0 = _t_row(res, 'REF')
    for key, st_key in (('LoE_AR', 'AR'), ('LoE_AtP', 'AtP')):
        st = dict(S.BOUNDARY[st_key])
        lab = st.pop('label')
        ys = [_t_row(res, n)[key] for n, _ in T_STEPS]
        ax.step(np.r_[xs - 0.4, xs[-1] + 0.4], np.r_[ys, ys[-1]], where='post', label=f'Cumulative LoE, {lab}', **st)
        ax.scatter(xs, ys, color=st['color'], s=10, zorder=5)
        for x_, y, (n, _) in zip(xs, ys, T_STEPS):
            d = 100 * (y / p0[key] - 1)
            ax.annotate(f'{y:.2f}' + ('' if n == 'REF' else f' ({d:+.0f}%)'), (x_, y), xytext=(0, 4),
                        textcoords='offset points', ha='center', fontsize=S.FONT_SMALL)
    ax.axhline(1.0, color=S.INK, lw=S.LW, gid=figaudit.BOUNDARY)
    ax.text(-0.45, 1.0, 'LoE = 1', va='bottom', fontsize=S.FONT_SMALL)
    ax.set_yscale('log')
    ax.set_ylim(0.3, 30)
    P.log_ticks(ax.yaxis, (0.5, 1, 2, 5, 10, 20))
    ax.set_xlim(-0.5, len(T_STEPS) - 0.3)
    lab = []
    for n, l_ in T_STEPS:
        h = _human(res, n)
        lab.append(f"{l_}\n{h['size']:.0f} m² per new dwelling\n{h['per_person']:.0f} m² per person\n"
                   f"{h['per_year'] / 1e3:.1f}k dwellings per year")
    ax.set_xticks(xs)
    ax.set_xticklabels(lab, fontsize=S.FONT_SMALL)
    ax.set_ylabel('Cumulative level of exceedance, 2026–2050 (log scale)')
    g = res['T']['gap']['TL']
    if g['within_AR']:
        resid = f"TL within the AR budget: margin {g['margin_AR_kt']:,.0f} kt"
    else:
        rs = g['residual']
        resid = (f"Residual to LoE AR = 1: cut {100 * rs['cut_of_2027_2050_construction']:.1f}% of 2027–2050 "
                 f"construction\n= {rs['dwellings_not_built_2027_2050']:,.0f} dwellings not built, "
                 f"{rs['new_residents_housed_in_existing_dwellings']:,.0f} new residents\nhoused in existing dwellings")
    ax.annotate(resid, (xs[-1], 1.0), xytext=(xs[-1] - 1.25, 0.45), fontsize=S.FONT_SMALL, ha='left', va='center',
                arrowprops=dict(arrowstyle='-', color=S.MUTED, lw=S.LW_THIN))
    ax.legend(fontsize=S.FONT_SMALL, loc='upper right', frameon=False)
    ax.grid(axis='x', visible=False)
    P.panel(ax, 'a', 'From the Reference to the theoretical limit (indicators: 2027–2050 means)')
    bd = pd.concat([res['bands'], res['T']['bands']], ignore_index=True)
    bd = bd[(bd['scenario'] == REFERENCE) & (bd['definition'] == 'in_scope')]
    runs = ['REF', 'P5-ambitious', 'TL']
    for j, (col, ylab, ttl) in enumerate((('gfa_Mm2', 'Floor area 2026–2050 (Mm²)', 'Floor area by demand band'),
                                          ('carbon_kt', 'Embodied carbon 2026–2050 (kt CO₂e)', 'Carbon by demand band'))):
        a = fig.add_subplot(gs[1, j])
        fmt = (lambda v: f'{v:,.1f}') if col == 'gfa_Mm2' else (lambda v: f'{v:,.0f}')
        for i, rn in enumerate(runs):
            d = bd[bd['run'] == rn].set_index('band')
            parts = [(BAND_ID[b], float(d.loc[b, col])) for b, _ in FIG_BANDS
                     if not (col == 'gfa_Mm2' and BAND_ID[b] == 'maintenance')]
            up, dn = P.signed_stack(a, [i], parts, width=0.6)
            a.text(i, up[0], fmt(up[0] + dn[0]), ha='center', va='bottom', fontsize=S.FONT_SMALL)
        a.axhline(0, color=S.INK, lw=S.LW_THIN)
        a.set_xticks(range(len(runs)))
        a.set_xticklabels([N.SCENARIOS['REF'], 'P5 Ambitious', 'TL'], fontsize=S.FONT_SMALL)
        a.set_ylabel(ylab)
        if col == 'carbon_kt':
            P.thousands(a.yaxis)
        a.grid(axis='x', visible=False)
        P.panel(a, 'bc'[j], ttl)
    P.band_legend(fig, list(N.BANDS_IN_SCOPE), ncol=4, y=-0.01)
    fig.subplots_adjust(bottom=0.12)
    _save(fig, 'D32_tl_staircase',
          T_CAPTION + f" TL1 {LV.TL_NAMES['TL1']} (vacancy 0, 2026 overbuild absorbed), TL2 {LV.TL_NAMES['TL2']} (size = household "
          f"size × occupant load factor), TL3 {LV.TL_NAMES['TL3']} (the smallest occupant load factor of the case "
          f"studies, 19.7 m² per person, for every typology), TL4 {LV.TL_NAMES['TL4']} (each typology's best case-study "
          f"A1–A3), TL5 {LV.TL_NAMES['TL5']} (lowest soil order), TL6 {LV.TL_NAMES['TL6']} ({100 * LV.TL6_SHARE:.0f}% of "
          'non-replacement floor area on developed land, no soil carbon loss; Auckland Council 2021); the adopted '
          'decarbonisation applies. In its zero-building years (released vacant stock used, banking rule) every band '
          'is zero.')


def fig_T_shapley(res):
    """D33: Shapley attribution of P5 Ambitious (full strength from 2027) - TL to TL1-TL6."""
    import matplotlib.pyplot as plt
    import plotting as P
    S = style
    sh = res['T']['shapley']
    fig, axes = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    for ax, metric, xl, letter in ((axes[0], 'carbon_kt', 'Reduction of carbon 2026–2050 (kt CO₂e)', 'a'),
                                   (axes[1], 'LoE_AR', 'Reduction of the cumulative LoE AR', 'b')):
        d = sh[sh['metric'] == metric].set_index('player')
        players = list(LV.TL_COMPONENTS) + [LV.TL_FROM2027]
        for k, pl in enumerate(players):
            v = float(d.loc[pl, 'reduction'])
            is_t = pl != LV.TL_FROM2027
            ax.barh(k, v, height=0.6, color=S.TL if is_t else 'white', edgecolor=S.TL, lw=S.LW,
                    hatch=None if is_t else '////')
            share = d.loc[pl, 'share_of_P5_ambitious_from2027_minus_TL']
            ax.text(v, k, (f' {v:,.0f}' if metric == 'carbon_kt' else f' {v:.3f}') +
                    (f' ({100 * share:.0f}%)' if is_t else ' (separate line)'), va='center', fontsize=S.FONT_MIN)
        ax.set_yticks(range(len(players)))
        ax.set_yticklabels([f'{p_} {LV.TL_NAMES[p_]}' if p_ in LV.TL_NAMES
                            else f"P5 Ambitious: {N.ADOPTION['from2027']}" for p_ in players], fontsize=S.FONT_SMALL)
        ax.invert_yaxis()
        ax.set_xlabel(xl)
        ax.set_xlim(0, ax.get_xlim()[1] * 1.35)
        ax.grid(axis='y', visible=False)
        if metric == 'carbon_kt':
            P.thousands(ax.xaxis)
        P.panel(ax, letter, 'Carbon' if metric == 'carbon_kt' else 'Cumulative LoE AR')
    fig.tight_layout()
    _save(fig, 'D33_tl_shapley',
          f'Reference variant; {2 ** len(LV.TL_COMPONENTS)} subsets, exact. Shares are of P5 Ambitious at full strength '
          'from 2027 minus TL. The hatched bar is the separate effect of starting P5 Ambitious at full strength in 2027 '
          'instead of on the adopted adoption path (not a Shapley player). ' + T_CAPTION)


def fig_T_annual(res):
    """D34: TL: annual carbon and dwellings built per year (banking rule)."""
    import matplotlib.pyplot as plt
    import plotting as P
    S = style
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=S.figsize('double', 78))
    series = ('REF', 'P5-ambitious', 'TL', 'TL-gradual')
    ref = res['ctxs'][REFERENCE]
    yrs = ref['years']
    for nm in series:
        E = _step_run(res, nm)['E']
        lab = N.SCENARIOS['REF'] if nm == 'REF' else N.run_label(nm)
        ax.plot(yrs[1:], E['carbon'][1:] / M6, label=lab, **_line(nm))
        ax2.plot(yrs[1:], np.asarray(engine.requirement(E))[1:] / 1e3, label=lab, **_line(nm))
    P.boundary_lines(ax, yrs[1:], ref['b_ar'] / M6, ref['b_atp'] / M6)
    ax.set_xlim(2026, 2050)
    ax.set_ylim(0, None)
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(fontsize=S.FONT_MIN, frameon=False, loc='upper right')
    P.panel(ax, 'a', 'Annual carbon')
    zy = res['T']['indicators']['TL']['zero_building_years']
    if zy:
        ax2.axvspan(min(zy) - 0.5, max(zy) + 0.5, color=S.MUTED, alpha=0.12, lw=0, zorder=0)
        ax2.text((min(zy) + max(zy)) / 2, 1, f'TL: no new building\n{min(zy)}–{max(zy)}\n(released vacant\nstock used)',
                 ha='center', va='bottom', fontsize=S.FONT_MIN)
    ax2.set_xlim(2026, 2050)
    ax2.set_ylim(0, None)
    ax2.set_ylabel('Dwellings (thousand per year)')
    P.panel(ax2, 'b', 'Dwellings built, all categories (banking rule: never negative)')
    fig.tight_layout()
    _save(fig, 'D34_tl_dwellings', T_CAPTION)


def figures(res):
    """The pathway diagnostics D28-D34 (style.save_figure; each file is overwritten in place, so
    a pathways-only run replaces exactly these figures). H7-H10: headline.py."""
    import matplotlib
    matplotlib.use('Agg')
    style.apply()
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
