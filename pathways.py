"""
PATHWAYS v1: lever runs, attribution, AESA gap, back-cast, solution space
=========================================================================
Reads the Boss state (validation.run_boss -> Boss.main() locals) and re-calls
engine.forward() with copies of `fwd_inputs` modified by levers.py; nothing in
the model changes (engine.py, Boss.py, events.py, aesa.py, PB.py are only
called). With every lever off the run IS the reference central run (tested to
1e-9: annual carbon, upfront, in-window B, floor area by typology, demand
bands, committed range, cumulative LoE AR / AtP).

Runs (reference scenario S3-10 unless stated):
  P0              baseline (every lever off)
  L1..L5 at M, A  single levers
  P1 Avoid (L1+L2+L3), P2 Shift + Improve (L4+L5), P3 all five; each at M and A
  Shapley         all 2^5 subsets at M and at A (P3 attribution, exact arithmetic)
  envelope        P0 and P3 under S1 and S2 (full Boss runs with REPLACEMENT_SCENARIO
                  changed, as tools/replacement_scenarios.py and PB.scenario_runs)
  ramp sensitivity  P3 with the levers at full strength by 2045 (all three scenarios)

AESA gap: boundaries B_AR, B_AtP by year for S3-10 from outputs/pb_annual.csv
(population is not changed by any lever); cumulative LoE = ratio of sums
(aesa.cumulative_loe). Back-cast on P3-A: a uniform factor k on all 2027-2050
construction (floor area by typology; carbon is linear in floor area; 2026
fixed) solved with scipy.optimize.brentq for cumulative LoE AR = 1; for AtP the
minimum attainable LoE (k = 0, 2026 alone) is reported. Solution space (Horup
et al. 2025, Fig. 6 style): demand x intensity reduction grid on P0.

Writes outputs/pathways/: pathways_runs.csv, pathways_annual.csv,
pathways_bands.csv, shapley.csv, backcast.json, solution_space.csv,
levers.json, PATHWAYS_METHODS_DRAFT.md (tools/pathways_methods.py), and the
figures pw_1..pw_6 (outputs/figures/, listed in FIGURES.md).

    python pathways.py
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
import levers as LV  # noqa: E402
import validation  # noqa: E402

OUT = os.path.join(ROOT, 'outputs', 'pathways')
FIG_DIR = os.path.join(ROOT, 'outputs', 'figures')
FILE_PB_ANNUAL = os.path.join(ROOT, 'outputs', 'pb_annual.csv')
FILE_PB_RESULTS = os.path.join(ROOT, 'outputs', 'pb_results.json')
FILE_BOSS_RESULTS = os.path.join(ROOT, 'outputs', 'boss_results.json')
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'
QUICK = os.environ.get('PATHWAY_QUICK') == '1'
RUN_MODE = 'QUICK RUN, not for reporting' if QUICK else 'full'

WINDOW = (2026, 2050)
REFERENCE = 'S3-10'
# the three replacement scenarios, as tools/replacement_scenarios.py
SCENARIOS = {'S1': ('Low (S1)', dict(REPLACEMENT_SCENARIO='S1')),
             'S3-10': ('Reference (S3-10)', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=10.0)),
             'S2': ('High (S2)', dict(REPLACEMENT_SCENARIO='S2'))}
IDENTITY_RTOL = 1e-9
GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.05), 2)     # solution space: 0-100% in 5% steps
BRENTQ_XTOL = 1e-15
M6 = 1e6


# ============================================================
# CONTEXT: one Boss state per scenario
# ============================================================
def boundaries():
    """B_AR and B_AtP (kg/yr) by year 2026-2050 for S3-10, and P_NZ, from outputs/pb_annual.csv."""
    a = pd.read_csv(FILE_PB_ANNUAL)
    a = a[(a['scenario'] == REFERENCE) & (a['year'] >= WINDOW[0]) & (a['year'] <= WINDOW[1])].set_index('year')
    if list(a.index) != list(range(WINDOW[0], WINDOW[1] + 1)):
        raise SystemExit(f'{FILE_PB_ANNUAL}: S3-10 boundaries incomplete over {WINDOW}.')
    return a['B_AR_kgCO2e'].values, a['B_AtP_kgCO2e'].values, a['P_NZ'].values


def base_context(B, scenario, bounds):
    """Everything a lever run needs from one Boss state (no copy of the data is changed)."""
    Boss = validation.Boss
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
        raise SystemExit(f'{scenario}: NZ population differs from the pb_annual.csv S3-10 path.')
    E_nojoin = engine.forward(pop, hh, growth, **fi)          # Boss l. 1543 (input to market_excess)
    prof = {t: B['EV_PROFILE'][B['EV_PROFILE']['Typology'] == t].reset_index(drop=True) for t in typ}
    after = np.arange(fy[-1] + 1, fy[-1] + int(B['EV_PROFILE']['Age'].max()) + 1)
    fac = {(t, k): EV.row_factors(prof[t], after, Boss.DECARB_MODE, Boss.DECARB_ITEM_CASE, Boss.DECARB_A45,
                                  hold=hold)
           for t in typ for k, hold in (('upper', '2025'), ('lower', '2050'))}
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    a45 = {t: float(B['MAT_STAGE']['A4-A5'][t].sum()) for t in typ}
    return dict(
        scenario=scenario, B=B, years=fy, typ=typ, pop=pop, growth=growth, hh=hh,
        fwd_inputs=fi, size_ref=B['size_ref'], v0=float(B['v_forward']), rate_demol=float(B['demolition_rate']),
        rate_unc=np.asarray(fi['rate_unc'], float), long_run_residual=float(B['unconsented_rate']),
        held_shares=B['held_shares'], a13_2025=a13, red13=B['RED13_TOT'], a45_2025=a45, red45=B['RED45_TOT'],
        join=ji['join'], join_redev=ji['redev'], O26=float(ji['O26']), rho=float(B['rho_other']),
        gap_ref=Boss.NEAR_TERM_GAP_REF, E_nojoin=E_nojoin, profile=prof, committed_factors=fac,
        c14={t: float(B['stage_int'].loc['C1-C4', t]) for t in typ}, soil=B['SOIL_INTENSITY'],
        events=fi['events'], b_ar=b_ar, b_atp=b_atp)


# ============================================================
# ONE RUN AND ITS METRICS
# ============================================================
def run(ctx, params, active, ramp_full=LV.RAMP_FULL):
    """engine.forward with the levers in `active` ({lever: 'M' | 'A'})."""
    fi, join, redev, info = LV.apply(ctx, params, active, ramp_full, ctx['E_nojoin'])
    E = engine.forward(ctx['pop'], ctx['hh'], ctx['growth'], join=join, join_redev=redev, **fi)
    return dict(E=E, inputs=fi, info=info, active=dict(active), ramp_full=ramp_full, scenario=ctx['scenario'])


def committed(ctx, gfa_t):
    """Committed after 2050 (kt): the 2026-2050 cohorts' later replacements and repaints
    (events.committed; upper: 2025 factors, lower: 2050 factors held) and all their C1-C4
    (2025 factors), as Boss l. 2274-2289, with this run's floor area by typology."""
    b = {'upper': 0.0, 'lower': 0.0}
    for k, t in enumerate(ctx['typ']):
        for key in b:
            b[key] += EV.committed(gfa_t[k], ctx['years'], ctx['profile'][t], ctx['committed_factors'][(t, key)])
    c = sum(gfa_t[k][1:].sum() * ctx['c14'][t] for k, t in enumerate(ctx['typ']))
    return dict(B_upper_kt=b['upper'] / M6, B_lower_kt=b['lower'] / M6, C_kt=c / M6,
                upper_kt=(b['upper'] + c) / M6, lower_kt=(b['lower'] + c) / M6)


def soil_by_year(ctx, E):
    s = np.array([ctx['soil'][t] for t in ctx['typ']])
    return (s[:, None] * E['gfa_t']).sum(axis=0) * E['soil_share']


def carbon_parts(ctx, R):
    """Annual carbon split by cohort: upfront by construction year (soil and non-soil) and
    in-window events by cohort year i and occurrence year j (ev[i, j]). Sum = E['carbon']."""
    E = R['E']
    soil = soil_by_year(ctx, E)
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
    soil = soil_by_year(ctx, E)[f]
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
    row = dict(run=label, scenario=ctx['scenario'], setting=setting, levers=LV.label(R['active']),
               ramp_full=R['ramp_full'],
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
               near_term_join_dwellings=float(E['join'][f].sum()))
    return row


def annual_rows(ctx, R, label):
    E = R['E']
    v_impl = 1.0 - E['hh'] / (E['stock'] + E['stock_join'])
    soil = soil_by_year(ctx, E)
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
                         B_AR_kt=ctx['b_ar'][j] / M6, B_AtP_kt=ctx['b_atp'][j] / M6,
                         LoE_AR=E['carbon'][i] / ctx['b_ar'][j], LoE_AtP=E['carbon'][i] / ctx['b_atp'][j]))
    return rows


# ============================================================
# DEMAND BANDS (Boss bookkeeping, l. 1555-1575 and 1700-1745)
# ============================================================
BAND_ORDER = ['Growth (net of consolidation)', 'House-splitting', 'Extra space per dwelling', 'Vacancy allowance',
              'Demolition replacement', 'Calibrated stock residual (long run)',
              'Redevelopment wave (scenario - long run)', 'Near-term market excess',
              'Housed in RV units (out of scope)']
FIG_BANDS = [('Growth demand (net of consolidation)', ('growth',)), ('House-splitting demand', ('hs_pos',)),
             ('Consumption: extra space per dwelling', ('extra',)), ('Consumption: vacancy allowance', ('vac',)),
             ('Replacement: long-run background (net of unconsented additions)', ('repl', 'unc')),
             ('Replacement: recent redevelopment wave (fading)', ('wave',)),
             ('Near-term market excess (2026 observed building above requirement, fading at rho)', ('join',)),
             ('Replacements & repaints, within 2026-2050', ('bev',))]


def band_arrays(ctx, R):
    """Annual floor area (m2) and carbon (kg) by demand band, as Boss: the redevelopment
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
    mat = {t: np.asarray(fi['intensity'][t], float) - ctx['soil'][t] for t in ctx['typ']}
    c = {k: sum(v * shares[t].values * mat[t] + v * shares[t].values * frac[k] * ctx['soil'][t] for t in ctx['typ'])
         for k, v in g.items()}
    c['bev'] = E['b_t'].sum(axis=0)
    return g, c


def band_rows(ctx, R, label):
    """Two definitions: 'boss_results' (export_results: every band incl. the negative RV
    band; carbon excludes in-window events) and 'in_scope_figure' (fig_bands: RV removed
    from every band in proportion; demolition + residual one band; events as a carbon band)."""
    g, c = band_arrays(ctx, R)
    f = slice(1, None)
    keys = ['growth', 'hs_pos', 'extra', 'vac', 'repl', 'unc', 'wave', 'join', 'rv']
    rows = [dict(run=label, scenario=ctx['scenario'], definition='boss_results', band=b,
                 gfa_Mm2=g[k][f].sum() / M6, carbon_kt=c[k][f].sum() / M6) for b, k in zip(BAND_ORDER, keys)]
    E = R['E']
    tot_g, tot_c = E['total'][f], E['carbon'][f]
    raw_g = {b: sum((g[k] if k != 'bev' else 0.0 * g['growth']) for k in ks)[f] for b, ks in FIG_BANDS}
    raw_c = {b: sum(c[k] for k in ks)[f] for b, ks in FIG_BANDS}
    fg, fc = tot_g / sum(raw_g.values()), tot_c / sum(raw_c.values())
    rows += [dict(run=label, scenario=ctx['scenario'], definition='in_scope_figure', band=b,
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
    return pd.read_csv(validation.Boss.FILE_FACTORS_BUILDING)


def boss_state(scenario):
    with contextlib.redirect_stdout(io.StringIO()):
        return validation.run_boss(**SCENARIOS[scenario][1])


def compute(scenarios=tuple(SCENARIOS), verbose=True):
    """All runs. Returns a dict of tables and the objects the figures and tests need."""
    t0 = time.time()
    bounds = boundaries()
    states = {s: boss_state(s) for s in scenarios}
    if REFERENCE not in states:
        raise ValueError('The reference scenario S3-10 is required.')
    params = LV.resolve(states[REFERENCE], load_factors_building(), validation.Boss)
    if params['L4']['target']['M'] >= params['L4']['target']['A']:
        raise SystemExit(f"STOP (L4): Moderate target {params['L4']['target']['M']:.4f} >= Ambitious "
                         f"{params['L4']['target']['A']:.4f}.")
    ctxs = {s: base_context(states[s], s, bounds) for s in scenarios}
    cache = {}

    def get(scen, active, ramp_full=LV.RAMP_FULL):
        key = (scen, LV.label(active), ramp_full)
        if key not in cache:
            cache[key] = run(ctxs[scen], params, active, ramp_full)
        return cache[key]

    named = []                                  # (name, scenario, setting, active, ramp)
    named.append(('P0', REFERENCE, '', {}, LV.RAMP_FULL))
    for L in LV.LEVERS:
        for s in LV.SETTINGS:
            named.append((f'{L}-{s}', REFERENCE, s, {L: s}, LV.RAMP_FULL))
    for P, members in LV.BUNDLES.items():
        for s in LV.SETTINGS:
            named.append((f'{P}-{s}', REFERENCE, s, {L: s for L in members}, LV.RAMP_FULL))
    for scen in scenarios:
        if scen != REFERENCE:
            named.append(('P0', scen, '', {}, LV.RAMP_FULL))
            for s in LV.SETTINGS:
                named.append((f'P3-{s}', scen, s, {L: s for L in LV.LEVERS}, LV.RAMP_FULL))
        for s in LV.SETTINGS:
            named.append((f'P3-{s}-ramp{LV.RAMP_FULL_SENS}', scen, s, {L: s for L in LV.LEVERS}, LV.RAMP_FULL_SENS))
    rows, annual, bands = [], [], []
    for name, scen, s, active, rf in named:
        R = get(scen, active, rf)
        rows.append(metrics(ctxs[scen], R, name, s))
        annual += annual_rows(ctxs[scen], R, name)
        bands += band_rows(ctxs[scen], R, name)
    runs_df = pd.DataFrame(rows)
    p0 = runs_df[runs_df['run'] == 'P0'].set_index('scenario')
    for col in ('carbon_kt', 'LoE_AR', 'LoE_AtP', 'gfa_Mm2', 'committed_lower_kt', 'committed_upper_kt'):
        runs_df[f'delta_{col}_vs_P0_pct'] = [100.0 * (r[col] / p0.loc[r['scenario'], col] - 1.0)
                                            for _, r in runs_df.iterrows()]

    # ---- Shapley attribution of P3 (all 2^5 subsets, S3-10) and the fixed-order waterfall
    shap_rows, shap_runs = [], []
    shap_exact = {}
    for s in LV.SETTINGS:
        vals = {'carbon_kt': {}, 'LoE_AR': {}}
        for S in subsets(LV.LEVERS):
            active = {L: s for L in S}
            m = metrics(ctxs[REFERENCE], get(REFERENCE, active), LV.label(active), s)
            vals['carbon_kt'][S] = m['carbon_kt']
            vals['LoE_AR'][S] = m['LoE_AR']
            shap_runs.append(dict(setting=s, subset=LV.label(active), n_levers=len(S), carbon_kt=m['carbon_kt'],
                                  LoE_AR=m['LoE_AR'], LoE_AtP=m['LoE_AtP'], gfa_Mm2=m['gfa_Mm2']))
        for metric, v in vals.items():
            phi = shapley(v)
            full = frozenset(LV.LEVERS)
            shap_exact[(s, metric)] = (phi, Fraction(v[frozenset()]) - Fraction(v[full]))
            for pos, L in enumerate(LV.LEVERS, 1):
                shap_rows.append(dict(setting=s, metric=metric, method='shapley', lever=L,
                                      lever_name=LV.LEVER_NAMES[L], group=LV.LEVER_GROUP[L], order=pos,
                                      reduction=float(phi[L]),
                                      share_of_P0_minus_P3=float(phi[L] / (Fraction(v[frozenset()]) - Fraction(v[full])))))
            prev = frozenset()
            for pos, L in enumerate(LV.LEVERS, 1):          # fixed order Avoid -> Shift -> Improve
                cur = prev | {L}
                shap_rows.append(dict(setting=s, metric=metric, method='sequential', lever=L,
                                      lever_name=LV.LEVER_NAMES[L], group=LV.LEVER_GROUP[L], order=pos,
                                      reduction=v[prev] - v[cur], share_of_P0_minus_P3=(v[prev] - v[cur]) / (v[frozenset()] - v[full]),
                                      cumulative_after=v[cur]))
                prev = cur
    shap_df = pd.DataFrame(shap_rows)

    # ---- back-cast (P3-A; P0 for comparison) and solution space (P0) ------------
    ref = ctxs[REFERENCE]
    R0 = get(REFERENCE, {})
    R3A = get(REFERENCE, {L: 'A' for L in LV.LEVERS})
    bc3, split3 = backcast(ref, R3A, 'P3-A')
    bc0, split0 = backcast(ref, R0, 'P0')
    gfa0_later = split0['gfa_later']
    if bc3['k_AR'] is not None:
        bc3['equivalent_cut_vs_P0_floor_area'] = 1.0 - bc3['k_AR'] * split3['gfa_later'] / gfa0_later
        bc3['equivalent_cut_vs_P0_carbon_2027_2050_cohorts'] = 1.0 - (
            bc3['k_AR'] * (split3['later_nonsoil'] + split3['later_soil']).sum()
            / (split0['later_nonsoil'] + split0['later_soil']).sum())
    bar, batp = ref['b_ar'].sum(), ref['b_atp'].sum()
    space = solution_space(split0, bar, batp)
    markers = []
    for P in ('P1', 'P2', 'P3'):
        for s in LV.SETTINGS:
            Rp = get(REFERENCE, {L: s for L in LV.BUNDLES[P]})
            sp = linear_split(ref, Rp)
            d, i = effective_coordinates(sp, split0)
            grid_loe = scaled_carbon(split0, 1.0 - d, 1.0 - i).sum() / bar
            run_loe = Rp['E']['carbon'][1:].sum() / bar
            markers.append(dict(run=f'{P}-{s}', demand_reduction=d, intensity_reduction=i,
                                LoE_AR_run=run_loe, LoE_AR_on_grid_at_coordinates=grid_loe,
                                LoE_AtP_run=run_loe * bar / batp))
    backcast_out = dict(
        run_mode=RUN_MODE, method='uniform factor k on the floor area by typology of every 2027-2050 cohort '
        '(construction-year upfront and its in-window events scale with k; 2026 and its events fixed); '
        'scipy.optimize.brentq on [0, 1], xtol 1e-15',
        P3_A=bc3, P0=bc0, B_AR_kt=bar / M6, B_AtP_kt=batp / M6,
        solution_space_markers=markers,
        AtP_note=('not attainable within the window' if not bc3['AtP_attainable'] else 'attainable'))
    out = dict(params=params, runs=runs_df, annual=pd.DataFrame(annual), bands=pd.DataFrame(bands),
               shapley=shap_df, shapley_runs=pd.DataFrame(shap_runs), shapley_exact=shap_exact,
               backcast=backcast_out, space=space, ctxs=ctxs, states=states, cache=cache, get=get,
               seconds=time.time() - t0)
    if verbose:
        print(f'pathways: {len(cache)} engine runs in {out["seconds"]:.1f} s')
    return out


def checks(res):
    """Identity of P0 with the published reference run, and the STOP conditions."""
    ctx = res['ctxs'][REFERENCE]
    B = ctx['B']
    R0 = res['get'](REFERENCE, {})
    E0, Eb = R0['E'], B['engine_out']['50th']
    rel = lambda a, b: float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float)) / np.maximum(np.abs(np.asarray(b, float)), 1e-300)))
    rep = {}
    rep['annual_carbon'] = rel(E0['carbon'][1:], B['carbon_total_typ'].sum(axis=1).values[1:])
    rep['gfa_by_typology'] = rel(E0['gfa_t'][:, 1:], Eb['gfa_t'][:, 1:])
    bres = json.load(open(FILE_BOSS_RESULTS))
    r0 = res['runs'][(res['runs']['run'] == 'P0') & (res['runs']['scenario'] == REFERENCE)].iloc[0]
    rep['carbon_kt'] = abs(r0['carbon_kt'] / bres['carbon_kt'] - 1)
    rep['upfront_kt'] = abs(r0['upfront_kt'] / bres['upfront_kt'] - 1)
    rep['soil_kt'] = abs(r0['soil_kt'] / bres['soil_kt'] - 1)
    rep['b_inwindow_kt'] = abs(r0['b_inwindow_kt'] / bres['b_inwindow_kt'] - 1)
    rep['gfa_Mm2'] = abs(r0['gfa_Mm2'] / bres['gfa_Mm2'] - 1)
    rep['annual_carbon_json'] = rel(E0['carbon'][1:] / M6, bres['annual']['carbon_kt'][1:])
    for k in ('lower_kt', 'upper_kt', 'B_lower_kt', 'B_upper_kt', 'C_kt'):
        rep[f'committed_{k}'] = abs(r0[f'committed_{k}'] / bres['committed'][k] - 1)
    bd = res['bands']
    b0 = bd[(bd['run'] == 'P0') & (bd['scenario'] == REFERENCE) & (bd['definition'] == 'boss_results')].set_index('band')
    for x in bres['demand_bands']:
        for col in ('gfa_Mm2', 'carbon_kt'):
            rep[f"band {x['band']} {col}"] = abs(b0.loc[x['band'], col] - x[col]) / max(abs(x[col]), 1e-12)
    pbr = json.load(open(FILE_PB_RESULTS))
    for scen in res['ctxs']:
        rs = res['runs'][(res['runs']['run'] == 'P0') & (res['runs']['scenario'] == scen)].iloc[0]
        for col in ('LoE_AR', 'LoE_AtP'):
            rep[f'{scen} {col}'] = abs(rs[col] / pbr['deterministic'][scen][col] - 1)
        rep[f'{scen} carbon vs pb_results'] = abs(rs['carbon_kt'] / pbr['deterministic'][scen]['I_kt'] - 1)
    worst = max(rep, key=rep.get)
    if rep[worst] > IDENTITY_RTOL:
        raise SystemExit(f'STOP: identity not reproduced: {worst} relative difference {rep[worst]:.3e}')
    runs = res['runs']
    bad = runs[(runs['D_minus_occ_min_m2'] < 0) | (runs['extra_clip_max_m2'] > 0)]
    if len(bad):
        raise SystemExit(f'STOP: D < S x OLF in {list(bad["run"] + " " + bad["scenario"])}')
    badv = runs[runs['implied_vacancy_min'] < LV.L2_VACANCY_FLOOR]
    if len(badv):
        raise SystemExit(f'STOP: implied vacancy below {LV.L2_VACANCY_FLOOR:.1%} in {list(badv["run"] + " " + badv["scenario"])}')
    badd = runs[runs['dwellings_built_min_year'] < 0]
    if len(badd):
        raise SystemExit(f'STOP: negative dwellings built in {list(badd["run"] + " " + badd["scenario"])}')
    for (s, metric), (phi, total) in res['shapley_exact'].items():
        if sum(phi.values()) != total:
            raise SystemExit(f'Shapley efficiency fails ({s}, {metric}).')
    return rep


def to_json(o):
    if isinstance(o, dict):
        return {str(k): to_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_json(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return [to_json(v) for v in o.tolist()]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def write(res, identity):
    os.makedirs(OUT, exist_ok=True)
    res['runs'].to_csv(os.path.join(OUT, 'pathways_runs.csv'), index=False)
    res['annual'].to_csv(os.path.join(OUT, 'pathways_annual.csv'), index=False)
    res['bands'].to_csv(os.path.join(OUT, 'pathways_bands.csv'), index=False)
    res['shapley'].to_csv(os.path.join(OUT, 'shapley.csv'), index=False)
    res['shapley_runs'].to_csv(os.path.join(OUT, 'shapley_subsets.csv'), index=False)
    res['space'].to_csv(os.path.join(OUT, 'solution_space.csv'), index=False)
    with open(os.path.join(OUT, 'backcast.json'), 'w') as f:
        json.dump(to_json(res['backcast']), f, indent=2)
    lv = dict(res['params'], run_mode=RUN_MODE, identity_max_rel_diff=max(identity.values()),
              identity_checks=identity, sources=LV.SOURCES)
    with open(os.path.join(OUT, 'levers.json'), 'w') as f:
        json.dump(to_json(lv), f, indent=2)


def main():
    res = compute()
    identity = checks(res)
    print(f'pathways: identity P0 = reference run, max relative difference {max(identity.values()):.2e}')
    write(res, identity)
    if SAVE_FIGURES:
        figures(res)
    import pathways_methods                                   # tools/pathways_methods.py
    pathways_methods.main()
    r = res['runs']
    ref = r[(r['scenario'] == REFERENCE) & (r['ramp_full'] == LV.RAMP_FULL)]
    print(ref[['run', 'gfa_Mm2', 'carbon_kt', 'LoE_AR', 'LoE_AtP', 'delta_carbon_kt_vs_P0_pct']].to_string(index=False))
    return res


# ============================================================
# FIGURES (outputs/figures/, figaudit records; listed in FIGURES.md)
# ============================================================
# Colours: the AR / AtP boundary pair of PB.py; pathways encoded by lever group, the same
# in every figure: Avoid (L1-L3, P1) aqua, Shift and Improve (L4, L5, P2) amber (Improve
# hatched), P3 deep magenta, P0 neutral. Validated with the dataviz palette validator
# together with the boundary pair (all pairs, light surface): no failure; aqua and amber
# are below 3:1 contrast, so every series is also labelled directly.
AR_COLOR, ATP_COLOR = '#1F5FA8', '#C2571A'
P_COLOR = {'P0': '#3b3b3b', 'P1': '#1baf7a', 'P2': '#eda100', 'P3': '#a0185a'}
GROUP_COLOR = {'Avoid': P_COLOR['P1'], 'Shift': P_COLOR['P2'], 'Improve': P_COLOR['P2']}
GROUP_HATCH = {'Avoid': None, 'Shift': None, 'Improve': '///'}
INK, MUTED, GRID_COLOR = '#333333', '#777777', '#e1e0d9'
PW_FIGURES = {
    'pw_1_waterfall': ('paper', 'Cumulative within-window carbon 2026-2050 (S3-10), P0 to P3 by lever in the fixed '
                       'order Avoid (L1 size, L2 existing stock, L3 lifetime) -> Shift (L4 mix) -> Improve (L5 materials), '
                       'Moderate and Ambitious, against the cumulative AR and AtP boundaries; emissions committed after '
                       '2050 (later replacements & repaints + end of life, range) as separate hatched bars, not part of the LoE.'),
    'pw_2_annual': ('paper', 'Annual carbon 2026-2050 (S3-10) of P0 and the bundles P1 Avoid, P2 Shift + Improve and P3 '
                    '(Moderate solid, Ambitious dashed) against the annual AR and AtP boundaries.'),
    'pw_3_bands': ('paper', 'Floor area and carbon 2026-2050 by demand band (in scope; RV units removed from every band in '
                   'proportion, as boss_04) for P0, P1-A and P3-A (S3-10).'),
    'pw_4_solution_space': ('paper', 'Solution space (Horup et al. 2025, Fig. 6 style): cumulative LoE AR over uniform cuts '
                            'of 2027-2050 floor area (demand) and of non-soil carbon per m2 (intensity) applied to P0, with '
                            'the LoE AR = 1 contour, the 2, 3, 5 and 10 contours where inside the grid range (1, 2, 3 on P0, maximum 4.85), and the bundles P1-P3 (Moderate open, Ambitious filled) at '
                            'their effective coordinates; the AtP LoE = 1 contour is drawn where it exists on the grid.'),
    'pw_5_shapley_SI': ('supp', 'Shapley attribution of P0 - P3 (S3-10; all 32 lever subsets) to the five levers, on '
                        'cumulative within-window carbon and on cumulative LoE AR, Moderate and Ambitious.'),
    'pw_6_envelope_SI': ('supp', 'P0 and P3 under the replacement scenarios Low (S1), Reference (S3-10) and High (S2), '
                         'with the levers at full strength by 2035 (adopted) and by 2045 (ramp sensitivity): cumulative '
                         'carbon vs cumulative boundaries, and annual carbon (S3-10).'),
}


def _save(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    import figaudit
    figaudit.record(fig, name)
    fig.savefig(os.path.join(FIG_DIR, f'{name}.png'), dpi=130, bbox_inches='tight')
    import matplotlib.pyplot as plt
    plt.close(fig)


def _style(ax):
    ax.grid(True, axis='y', color=GRID_COLOR, lw=0.6)
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
    r = res['runs']
    return r[(r['run'] == name) & (r['scenario'] == scen)].iloc[0]


def fig_waterfall(res):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    sh = res['shapley']
    bar_kt, batp_kt = res['backcast']['B_AR_kt'], res['backcast']['B_AtP_kt']
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2), sharey=True)
    p0 = _run(res, 'P0')
    for ax, s in zip(axes, LV.SETTINGS):
        seq = sh[(sh['setting'] == s) & (sh['metric'] == 'carbon_kt') & (sh['method'] == 'sequential')]
        p3 = _run(res, f'P3-{s}')
        x = 0
        ax.bar(x, p0['carbon_kt'], color=P_COLOR['P0'], width=0.7)
        ax.text(x, p0['carbon_kt'], f"{p0['carbon_kt']:,.0f}", ha='center', va='bottom', fontsize=8, color=INK)
        prev = p0['carbon_kt']
        labels = ['P0']
        for _, r in seq.iterrows():
            x += 1
            ax.bar(x, r['reduction'], bottom=r['cumulative_after'], color=GROUP_COLOR[r['group']],
                   hatch=GROUP_HATCH[r['group']], edgecolor='white', width=0.7)
            ax.plot([x - 1.35, x + 0.35], [prev, prev], color=MUTED, lw=0.6)
            ax.text(x, prev, f"-{r['reduction']:,.0f}\n({-100 * r['reduction'] / p0['carbon_kt']:.1f}%)",
                    ha='center', va='bottom', fontsize=7.5, color=INK)
            prev = r['cumulative_after']
            labels.append(f"{r['lever']}\n{_wrap(LV.LEVER_NAMES[r['lever']])}")
        x += 1
        ax.plot([x - 1.35, x + 0.35], [prev, prev], color=MUTED, lw=0.6)
        ax.bar(x, p3['carbon_kt'], color=P_COLOR['P3'], width=0.7)
        ax.text(x, p3['carbon_kt'], f"{p3['carbon_kt']:,.0f}\n({p3['delta_carbon_kt_vs_P0_pct']:+.1f}%)",
                ha='center', va='bottom', fontsize=8, color=INK)
        labels.append(f'P3-{s}')
        x_c = x + 1.6
        ax.axvline(x_c - 0.8, color=MUTED, lw=0.8, ls=':')
        for k, (nm, rr, col) in enumerate((('P0', p0, P_COLOR['P0']), (f'P3-{s}', p3, P_COLOR['P3']))):
            xc = x_c + 0.9 * k
            ax.bar(xc, rr['committed_lower_kt'], color='white', edgecolor=col, hatch='xx', width=0.7, lw=1.0)
            ax.plot([xc, xc], [rr['committed_lower_kt'], rr['committed_upper_kt']], color=col, lw=2.2)
            ax.plot([xc - 0.2, xc + 0.2], [rr['committed_upper_kt']] * 2, color=col, lw=2.2)
            ax.text(xc, rr['committed_upper_kt'], f"{rr['committed_lower_kt']:,.0f}-\n{rr['committed_upper_kt']:,.0f}",
                    ha='center', va='bottom', fontsize=7.5, color=INK)
        ticks = list(range(x + 1)) + [x_c, x_c + 0.9]
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels + ['P0\ncommitted', f'P3-{s}\ncommitted'], fontsize=8)
        _hline(ax, bar_kt, AR_COLOR, '-', f'AR {bar_kt:,.0f}', x - 1.4, x_range=[-0.45, x + 0.45])
        _hline(ax, batp_kt, ATP_COLOR, '--', f'AtP {batp_kt:,.0f}', x - 1.4, x_range=[-0.45, x + 0.45])
        ax.set_title(f"{'Moderate' if s == 'M' else 'Ambitious'}: cumulative LoE AR {p0['LoE_AR']:.2f} -> "
                     f"{p3['LoE_AR']:.2f}, AtP {p0['LoE_AtP']:.1f} -> {p3['LoE_AtP']:.1f}", fontsize=10)
        ax.text(x_c + 0.45, p0['committed_upper_kt'] * 1.25, 'committed\nafter 2050\n(not in LoE)',
                ha='center', va='bottom', fontsize=8, color=MUTED)
        _style(ax)
    axes[0].set_ylabel('cumulative carbon 2026-2050, kt CO$_2$e')
    fig.legend(handles=[Patch(color=P_COLOR['P0'], label='P0 baseline'),
                            Patch(color=GROUP_COLOR['Avoid'], label='Avoid: L1-L3'),
                            Patch(color=GROUP_COLOR['Shift'], label='Shift: L4'),
                            Patch(facecolor=GROUP_COLOR['Improve'], hatch='///', edgecolor='white', label='Improve: L5'),
                            Patch(color=P_COLOR['P3'], label='P3 (all five)'),
                            Patch(facecolor='white', edgecolor=MUTED, hatch='xx', label='committed after 2050 (range)')],
               loc='lower center', ncol=6, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle('PATHWAYS: cumulative within-window carbon, P0 -> P3 (reference S3-10), fixed order Avoid -> Shift -> Improve',
                 fontsize=11)
    fig.text(0.5, -0.1, 'Steps are the marginal effect of adding each lever in this order (order-dependent; the '
             'order-free Shapley attribution is pw_5_shapley_SI). Boundaries: cumulative 2026-2050, 2 °C carrying '
             'capacity (Bjørn & Hauschild 2015).', ha='center', fontsize=8, style='italic')
    fig.tight_layout()
    _save(fig, 'pw_1_waterfall')


def fig_annual(res):
    import matplotlib.pyplot as plt
    a = res['annual']
    a = a[a['scenario'] == REFERENCE]
    fig, ax = plt.subplots(figsize=(12, 6))
    ends = []
    for name, col, ls in [('P0', P_COLOR['P0'], '-')] + [(f'{P}-{s}', P_COLOR[P], '-' if s == 'M' else '--')
                                                       for P in ('P1', 'P2', 'P3') for s in LV.SETTINGS]:
        d = a[a['run'] == name]
        ax.plot(d['year'], d['carbon_kt'], color=col, ls=ls, lw=2.0, label=f'{name}: {LV.BUNDLE_NAMES[name[:2]]}')
        ends.append((d['carbon_kt'].iloc[-1], name, col))
    d0 = a[a['run'] == 'P0']
    import figaudit
    ax.plot(d0['year'], d0['B_AR_kt'], color=AR_COLOR, lw=2.0, gid=figaudit.BOUNDARY, label='boundary, acquired rights (AR)')
    ax.plot(d0['year'], d0['B_AtP_kt'], color=ATP_COLOR, lw=2.0, ls='--', gid=figaudit.BOUNDARY,
            label='boundary, ability to pay (AtP)')
    ends += [(d0['B_AR_kt'].iloc[-1], 'AR', AR_COLOR), (d0['B_AtP_kt'].iloc[-1], 'AtP', ATP_COLOR)]
    ends.sort()
    ylast = -1e9
    for v, nm, col in ends:                      # direct labels, nudged apart
        y = max(v, ylast + 28)
        ax.annotate(f'{nm} {v:,.0f}', (2050, v), xytext=(2050.4, y), fontsize=7.5, color=INK, va='center',
                    arrowprops=dict(arrowstyle='-', color=col, lw=0.6))
        ylast = y
    ax.set_xlim(2026, 2053)
    ax.set_ylim(0, None)
    ax.set_xlabel('year')
    ax.set_ylabel('annual carbon, kt CO$_2$e per year')
    ax.set_title('Annual carbon by pathway (S3-10): Moderate solid, Ambitious dashed, vs annual boundaries', fontsize=11)
    ax.annotate('L2: vacancy reaches its target in 2035;\nthe one-off release of existing stock ends', (2036, a[a['run'] == 'P3-A']
                .set_index('year').loc[2036, 'carbon_kt']), xytext=(2037.5, 300), fontsize=8, color=INK,
                arrowprops=dict(arrowstyle='->', color=MUTED, lw=0.8))
    ax.legend(fontsize=8, frameon=False, loc='upper right', ncol=2)
    _style(ax)
    fig.text(0.5, -0.07, 'Time-resolved: upfront (A1-A5 + soil) in the construction year plus replacements & repaints '
             'within 2026-2050. 2026 is observed and identical in every run;\nlevers ramp in linearly 2027-2035. The '
             'step in 2036 (P1, P3) is L2: lowering the vacancy rate acts through the vacancy-change term of the stock '
             'identity while the rate falls, so the release of existing dwellings ends when the target is reached;\n'
             'afterwards only the lower vacancy allowance on new households remains.',
             ha='center', fontsize=8, style='italic')
    fig.tight_layout()
    _save(fig, 'pw_2_annual')


def fig_bands(res):
    import matplotlib.pyplot as plt
    Boss = validation.Boss
    colors = [Boss.DEMAND_COLORS[0], Boss.HOUSESPLIT_COLOR, Boss.DEMAND_COLORS[1], Boss.DEMAND_COLORS[2],
              Boss.REPL_COLOR, Boss.WAVE_COLOR, Boss.JOIN_COLOR, Boss.EVENTS_COLOR]
    bd = res['bands']
    bd = bd[(bd['scenario'] == REFERENCE) & (bd['definition'] == 'in_scope_figure')]
    runs = ['P0', 'P1-A', 'P3-A']
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    for ax, col, ylab, sc in ((axes[0], 'gfa_Mm2', 'floor area 2026-2050, Mm$^2$', 1.0),
                              (axes[1], 'carbon_kt', 'carbon 2026-2050, kt CO$_2$e', 1.0)):
        for i, rn in enumerate(runs):
            d = bd[bd['run'] == rn].set_index('band')
            pos, neg = 0.0, 0.0                       # positive bands stack up, negative bands down from 0
            fmt = (lambda v: f'{v:,.1f}') if col == 'gfa_Mm2' else (lambda v: f'{v:,.0f}')
            for (band, _), c in zip(FIG_BANDS, colors):
                v = float(d.loc[band, col]) * sc
                if abs(v) < 1e-12:
                    continue
                base = pos if v > 0 else neg
                ax.bar(i, v, bottom=base, color=c, edgecolor='white', lw=1.0, width=0.6,
                       label=band if i == 0 else None)
                if abs(v) > 0.03 * d[col].sum():
                    ax.text(i, base + v / 2, fmt(v), ha='center', va='center', fontsize=7.5, color='white')
                if v > 0:
                    pos += v
                else:
                    neg += v
            ax.text(i, pos, f'net {fmt(pos + neg)}', ha='center', va='bottom', fontsize=9, color=INK)
        ax.set_xticks(range(len(runs)))
        ax.set_xticklabels([f'{r}\n{LV.BUNDLE_NAMES[r[:2]]}' for r in runs], fontsize=9)
        ax.set_ylabel(ylab)
        ax.axhline(0, color=INK, lw=0.8)
        _style(ax)
    axes[0].set_title('Floor area by demand band (in scope)', fontsize=10)
    axes[1].set_title('Carbon by demand band (in scope, incl. replacements & repaints within the window)', fontsize=10)
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle('Why the floor area is built, P0 vs Avoid (P1-A) vs all levers (P3-A), S3-10', fontsize=11)
    fig.text(0.5, -0.16, 'Negative bands (below zero): with L2 the stock-wide vacancy rate falls 2027-2035, so existing '
             'dwellings are released and less is built; with the near-term surplus absorbed (L2), the excess built in '
             '2026-2028 is almost fully paid back by 2050 (net band near zero).', ha='center', fontsize=8, style='italic',
             wrap=True)
    fig.tight_layout()
    _save(fig, 'pw_3_bands')


def fig_solution_space(res):
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.colors import LinearSegmentedColormap, LogNorm
    ref = res['ctxs'][REFERENCE]
    split0 = linear_split(ref, res['get'](REFERENCE, {}))
    bar, batp = ref['b_ar'].sum(), ref['b_atp'].sum()
    sp = res['space']
    n = len(GRID)
    Z = sp.pivot(index='intensity_reduction', columns='demand_reduction', values='LoE_AR').values
    ramp = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
    cmap = LinearSegmentedColormap.from_list('blue_seq', ramp)
    fig, ax = plt.subplots(figsize=(9.5, 8))
    edges = np.concatenate([[-2.5], GRID * 100 + 2.5])
    pm = ax.pcolormesh(edges, edges, Z, cmap=cmap, norm=LogNorm(vmin=0.3, vmax=5.0), shading='flat')
    cb = fig.colorbar(pm, ax=ax, shrink=0.8)
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
    for m in res['backcast']['solution_space_markers']:
        P, s = m['run'].split('-')
        ax.scatter(100 * m['demand_reduction'], 100 * m['intensity_reduction'], s=90, zorder=5,
                   facecolor=P_COLOR[P] if s == 'A' else 'white', edgecolor=P_COLOR[P], linewidth=2.0,
                   label=f"{m['run']}: LoE AR {m['LoE_AR_run']:.2f}")
        ax.annotate(m['run'], (100 * m['demand_reduction'], 100 * m['intensity_reduction']),
                    xytext=((-30, 8) if s == 'M' else (6, 8)), textcoords='offset points', fontsize=8, color='white',
                    path_effects=[pe.Stroke(linewidth=2.5, foreground='#0d366b'), pe.Normal()])
    bc = res['backcast']
    if bc['P0'].get('k_AR') is not None:
        ax.scatter(100 * (1 - bc['P0']['k_AR']), 0, marker='D', s=60, color='black', zorder=5,
                   label=f"P0 back-cast: demand cut {100 * (1 - bc['P0']['k_AR']):.1f}% for LoE AR = 1")
    ax.set_xlim(-2.5, 102.5)
    ax.set_ylim(-2.5, 102.5)
    ax.set_xlabel('demand reduction: cut of 2027-2050 floor area vs P0 (%)')
    ax.set_ylabel('intensity reduction: cut of non-soil carbon per m$^2$, 2027-2050 cohorts (%)')
    ax.set_title('Solution space on P0 (S3-10): cumulative LoE AR', fontsize=11)
    ax.legend(fontsize=7.5, loc='upper right', frameon=True, framealpha=0.9)
    fig.text(0.5, -0.03, 'Cells: the 5% grid (solution_space.csv); contours: the same linear model on a 0.5% grid. '
             'Soil carbon and 2026 are not cut by the intensity axis. ' + atp_note, ha='center', fontsize=8,
             style='italic', wrap=True)
    fig.tight_layout()
    _save(fig, 'pw_4_solution_space')


def fig_shapley(res):
    import matplotlib.pyplot as plt
    sh = res['shapley'][res['shapley']['method'] == 'shapley']
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for ax, metric, xl in ((axes[0], 'carbon_kt', 'reduction of cumulative carbon 2026-2050, kt CO$_2$e'),
                           (axes[1], 'LoE_AR', 'reduction of cumulative LoE AR')):
        for j, s in enumerate(LV.SETTINGS):
            d = sh[(sh['metric'] == metric) & (sh['setting'] == s)].set_index('lever')
            for k, L in enumerate(LV.LEVERS):
                y = k + (0.2 if s == 'M' else -0.2)
                g = LV.LEVER_GROUP[L]
                ax.barh(y, d.loc[L, 'reduction'], height=0.38, color='white' if s == 'M' else GROUP_COLOR[g],
                        edgecolor=GROUP_COLOR[g], hatch=('///' if g == 'Improve' else None), lw=1.5)
                v = d.loc[L, 'reduction']
                ax.text(v, y, f' {v:,.0f} ({100 * d.loc[L, "share_of_P0_minus_P3"]:.0f}%) {s}' if metric == 'carbon_kt'
                        else f' {v:.3f} {s}', va='center', fontsize=7.5, color=INK)
        ax.set_yticks(range(len(LV.LEVERS)))
        ax.set_yticklabels([f'{L} {LV.LEVER_NAMES[L]}\n({LV.LEVER_GROUP[L]})' for L in LV.LEVERS], fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel(xl)
        ax.grid(True, axis='x', color=GRID_COLOR, lw=0.6)
        ax.set_axisbelow(True)
        for spn in ('top', 'right'):
            ax.spines[spn].set_visible(False)
        ax.set_xlim(0, ax.get_xlim()[1] * 1.3)
    tot = {s: _run(res, 'P0')['carbon_kt'] - _run(res, f'P3-{s}')['carbon_kt'] for s in LV.SETTINGS}
    axes[0].set_title(f"Carbon: P0 - P3 = {tot['M']:,.0f} kt (M, open) / {tot['A']:,.0f} kt (A, filled)", fontsize=10)
    axes[1].set_title('Cumulative LoE AR', fontsize=10)
    fig.suptitle('Shapley attribution of P0 - P3 to the levers (S3-10; all 32 subsets; values sum exactly to P0 - P3)',
                 fontsize=11)
    fig.tight_layout()
    _save(fig, 'pw_5_shapley_SI')


def fig_envelope(res):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    bar_kt, batp_kt = res['backcast']['B_AR_kt'], res['backcast']['B_AtP_kt']
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1.25, 1]))
    names = [('P0', P_COLOR['P0'], None, 1.0), ('P3-M', P_COLOR['P3'], '///', 1.0), ('P3-A', P_COLOR['P3'], None, 1.0),
             (f'P3-M-ramp{LV.RAMP_FULL_SENS}', P_COLOR['P3'], '///', 0.4),
             (f'P3-A-ramp{LV.RAMP_FULL_SENS}', P_COLOR['P3'], None, 0.4)]
    scen = list(SCENARIOS)
    w = 0.16
    for i, sc in enumerate(scen):
        for k, (nm, col, hatch, alpha) in enumerate(names):
            r = _run(res, nm, sc)
            x = i + (k - 2) * w
            ax.bar(x, r['carbon_kt'], width=w * 0.92, color='white' if hatch else col, edgecolor=col, hatch=hatch,
                   alpha=alpha, lw=1.2)
            ax.text(x, r['carbon_kt'], f"{r['carbon_kt'] / 1e3:,.1f}", ha='center', va='bottom', fontsize=6.5,
                    color=INK, rotation=90)
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels([SCENARIOS[s][0] for s in scen])
    _hline(ax, bar_kt, AR_COLOR, '-', f'AR {bar_kt:,.0f}', len(scen) - 0.55)
    _hline(ax, batp_kt, ATP_COLOR, '--', f'AtP {batp_kt:,.0f}', len(scen) - 0.55)
    ax.set_xlim(-0.6, len(scen) - 0.1)
    ax.set_ylabel('cumulative carbon 2026-2050, kt CO$_2$e (labels: Mt)')
    ax.set_title('Cumulative carbon by replacement scenario', fontsize=10)
    ax.legend(handles=[Patch(color=P_COLOR['P0'], label='P0'),
                       Patch(facecolor='white', edgecolor=P_COLOR['P3'], hatch='///', label='P3-M, full by 2035'),
                       Patch(color=P_COLOR['P3'], label='P3-A, full by 2035'),
                       Patch(facecolor='white', edgecolor=P_COLOR['P3'], hatch='///', alpha=0.4,
                             label=f'P3-M, full by {LV.RAMP_FULL_SENS}'),
                       Patch(color=P_COLOR['P3'], alpha=0.4, label=f'P3-A, full by {LV.RAMP_FULL_SENS}')],
              fontsize=8, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3)
    _style(ax)
    a = res['annual']
    a = a[a['scenario'] == REFERENCE]
    for nm, col, ls, lw in (('P0', P_COLOR['P0'], '-', 2.0), ('P3-M', P_COLOR['P3'], '-', 1.6),
                            ('P3-A', P_COLOR['P3'], '-', 2.4), (f'P3-M-ramp{LV.RAMP_FULL_SENS}', P_COLOR['P3'], ':', 1.6),
                            (f'P3-A-ramp{LV.RAMP_FULL_SENS}', P_COLOR['P3'], ':', 2.4)):
        d = a[a['run'] == nm]
        ax2.plot(d['year'], d['carbon_kt'], color=col, ls=ls, lw=lw, label=nm)
    import figaudit
    d0 = a[a['run'] == 'P0']
    ax2.plot(d0['year'], d0['B_AR_kt'], color=AR_COLOR, lw=2.0, gid=figaudit.BOUNDARY, label='AR boundary')
    ax2.plot(d0['year'], d0['B_AtP_kt'], color=ATP_COLOR, lw=2.0, ls='--', gid=figaudit.BOUNDARY, label='AtP boundary')
    ax2.set_ylim(0, None)
    ax2.set_xlim(2026, 2050)
    ax2.set_xlabel('year')
    ax2.set_ylabel('annual carbon, kt CO$_2$e per year')
    ax2.set_title(f'Ramp sensitivity, S3-10: full strength by 2035 (solid) or {LV.RAMP_FULL_SENS} (dotted)', fontsize=10)
    ax2.legend(fontsize=8, frameon=False, loc='upper right')
    _style(ax2)
    fig.suptitle('Envelope: P0 and P3 under Low (S1), Reference (S3-10) and High (S2) replacement, and the ramp '
                 'sensitivity', fontsize=11)
    fig.tight_layout()
    _save(fig, 'pw_6_envelope_SI')


FIGURES_MD_MARK = '## Pathways'


def update_figures_md():
    """Append (or replace) the Pathways sections of FIGURES.md, which tools/figures_report.py
    regenerates without them earlier in run_all.py."""
    path = os.path.join(ROOT, 'FIGURES.md')
    txt = open(path, encoding='utf-8').read()
    if FIGURES_MD_MARK in txt:
        txt = txt[:txt.index(FIGURES_MD_MARK)].rstrip('\n') + '\n'
    L = ['', f'{FIGURES_MD_MARK}: paper candidates (generated by pathways.py)', '']
    L += [f'- `{n}.png`: {d}' for n, (k, d) in PW_FIGURES.items() if k == 'paper']
    L += ['', f'{FIGURES_MD_MARK}: supplementary (generated by pathways.py)', '']
    L += [f'- `{n}.png`: {d}' for n, (k, d) in PW_FIGURES.items() if k == 'supp']
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt + '\n'.join(L) + '\n')


def figures(res):
    """pw_1..pw_6 -> outputs/figures/ (figaudit records), and their FIGURES.md section."""
    import matplotlib
    matplotlib.use('Agg')
    fig_waterfall(res)
    fig_annual(res)
    fig_bands(res)
    fig_solution_space(res)
    fig_shapley(res)
    fig_envelope(res)
    update_figures_md()


if __name__ == '__main__':
    main()
