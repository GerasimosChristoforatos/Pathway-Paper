"""
PATHWAYS (MODEL v3.3.0): lever, strategy, pathway and theoretical-limit runs, attribution, waterfalls, back-cast
======================================================================================================
Reads the projection state (validation.run_boss -> projection.main() locals, in memory only) and re-calls
engine.forward() with copies of `fwd_inputs` modified by levers.inputs(); nothing in the model changes and no
baseline output is written. With every lever off the run IS the Reference (tested to 1e-9). This module computes
and writes data only (CSV / JSON); the figures are drawn by the figures/ package from these files.

ONE RUN (run()): every run, the Reference included, follows the same order per year
    gross_t -> overbuild payback -> re-occupation -> built_t
  1. the lever inputs (levers.inputs) and the requirement without any join, E1 (engine.forward, join = 0);
  2. need_t = requirement_t + the dwellings released by TL2 (zero vacancy: -min(vacancy change, 0)), so that the
     release is re-occupied by the rule below instead of netted at once;
  3. the 2026 overbuild: the market excess of the REFERENCE (computed once, held fixed in every run) is absorbed
     along the Reference's logistic weights, the payback capped at max(gross_t, 0) with the shortfall carried
     (engine.absorb_overbuild);
  4. re-occupation (TL-family runs with TL1 and / or TL2 only): the dwellings released by TL1 (household decline:
     -min(d households, 0) / (1 - v)) and TL2 to 2050, R = R1 + R2, meet a constant share of each year's need
     after the payback (reoccupation());
  5. engine.forward with the stock-adding join = excess - payback + TL2 release - re-occupied, so the stock identity
     holds and the released dwellings stay vacant until re-occupied.

RUNS (naming.py vocabulary): the Reference (and the Low / High / Very High replacement variants); each lever alone at
Moderate, Ambitious and TL; the PAS 2080 strategies S1 Avoid, S2 Switch, S3 Improve (BSI 2023, Clause 4.3, Fig. 5)
and the Moderate / Ambitious Pathway (every lever) at Moderate and Ambitious; TL (every lever at Level 4); the
lambda-sweep of each lever; the Pathways adopted by 2030 / 2045; the instant TL (sensitivity row).
ATTRIBUTION: exact Shapley values (rational arithmetic) over every subset: the three strategies (8 subsets) and the
nine levers (512 subsets) at Moderate and Ambitious (Reference -> Moderate / Ambitious Pathway), the nine levers at
TL from the Reference (512), and TL1-TL9 from the Moderate Pathway (512; the TL waterfall's game). Every run is cached
by its lever setting (levers.key) and reused across strategies, games and variants.
WATERFALLS (sequential, PAS 2080 hierarchy order): (a) Reference -> +L1 ... +L9 at a setting (= the Moderate /
Ambitious Pathway), (b) that Pathway -> +TL1 ... +TL9 (= TL), by demand band, at Moderate and Ambitious (ED6); MODEL
v3.3.1: Reference -> TL1 ... TL9 cumulative (Fig5c; waterfall_tl_from_reference).
Each step is credited with what remains after the higher-priority measures; sequential_vs_shapley.csv compares the
steps with the order-free Shapley values. No timing step: TL is adopted on the same logistic as every level.

    python pathways.py          (run_all.py runs it)
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
import aesa  # noqa: E402
import bands as BANDS  # noqa: E402
import engine  # noqa: E402
import events as EV  # noqa: E402
import layout  # noqa: E402
import levers as LV  # noqa: E402
import naming as N  # noqa: E402
import runprofile  # noqa: E402
import validation  # noqa: E402

RAMP_ADOPTED = LV.ADOPTION_ADOPTED
OUT = layout.data('pathways', frozen=False)
FILE_PB_ANNUAL = layout.data('aesa/annual.csv', frozen=False)
FILE_PB_RESULTS = layout.data('aesa/results.json', frozen=False)
FILE_BOSS_RESULTS = layout.data('baseline/projection.json', frozen=False)
RUN_MODE = runprofile.name()

WINDOW = (2026, 2050)
REFERENCE = 'REF'
SCENARIOS = {'LOW': (N.SCENARIOS['LOW'], dict(REPLACEMENT_VARIANT='LOW')),
             'REF': (N.SCENARIOS['REF'], dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0)),
             'HIGH': (N.SCENARIOS['HIGH'], dict(REPLACEMENT_VARIANT='HIGH')),
             'VHIGH': (N.SCENARIOS['VHIGH'], dict(REPLACEMENT_VARIANT='VHIGH'))}      # MODEL v3.3.0
IDENTITY_RTOL = 1e-9
GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.05), 2)     # solution space: 0-100% in 5% steps
LAMBDA_GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.1), 1)
BRENTQ_XTOL = 1e-15
M6 = 1e6
REOCCUPATION_YEARS = (2027, 2050)
REOCCUPATION_TOL = 1e-9         # relative tolerance of the re-occupation identities
T_ZERO_TOL_DWELLINGS = 1e-6     # floating-point noise of dwellings built in a zero-building year
T_ZERO_TOL_M2 = engine.SOIL_ZERO_TOL_M2
SHAPLEY_METRICS = ('carbon_kt', 'LoE_AR', 'LoE_AtP')
ORDER_RTOL = 1e-12
TL_GAME = 'tl_from_moderate_pathway'            # TL1-TL9 from the Moderate Pathway (MODEL v3.0-v3.2: tl_from_p5_moderate)
TL_REOCCUPATION_FAST = 'TL-reoccupation-fast'   # A4 sensitivity row (reoccupation rule 'fast')


# ============================================================
# CONTEXT: one projection state per scenario (or one Monte Carlo draw, pathways_mc.draw_context)
# ============================================================
def boundaries():
    """B_AR and B_AtP (kg/yr) by year 2026-2050 for the Reference, and P_NZ, from outputs/data/aesa/annual.csv."""
    a = pd.read_csv(FILE_PB_ANNUAL)
    a = a[(a['scenario'] == REFERENCE) & (a['year'] >= WINDOW[0]) & (a['year'] <= WINDOW[1])].set_index('year')
    if list(a.index) != list(range(WINDOW[0], WINDOW[1] + 1)):
        raise SystemExit(f'{FILE_PB_ANNUAL}: Reference boundaries incomplete over {WINDOW}.')
    return a['B_AR_kgCO2e'].values, a['B_AtP_kgCO2e'].values, a['P_NZ'].values


def absorption_weights(years):
    """The Reference's overbuild absorption weights (projection settings), None when never absorbed."""
    P = validation.projection
    if P.OVERBUILD_ABSORPTION_END is None:
        return None
    return engine.logistic_weights(years, P.OVERBUILD_ABSORPTION_START, P.OVERBUILD_ABSORPTION_END)


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
    if fi['soil_on_replacement'] or fi['dev_2025'] != 0.0 or ji['mode'] != 'surplus':
        raise SystemExit('pathways: written for SOIL_ON_REPLACEMENT = False and the market_excess surplus join.')
    b_ar, b_atp, p_nz = bounds
    if not np.allclose(pop[1:], p_nz, rtol=1e-12, atol=0):
        raise SystemExit(f'{scenario}: NZ population differs from the aesa/annual.csv Reference path.')
    prof = {t: B['EV_PROFILE'][B['EV_PROFILE']['Typology'] == t].reset_index(drop=True) for t in typ}
    after = np.arange(fy[-1] + 1, fy[-1] + int(B['EV_PROFILE']['Age'].max()) + 1)
    fac = {(t, k): EV.row_factors(prof[t], after, projection.DECARB_MODE, projection.DECARB_ITEM_CASE, projection.DECARB_A45,
                                  hold=hold)
           for t in typ for k, hold in (('upper', '2025'), ('lower', '2050'))}
    return dict(
        scenario=scenario, B=B, years=fy, typ=typ, pop=pop, growth=growth, hh=hh,
        fwd_inputs=fi, size_ref=B['size_ref'], olf=B['OLF_USED'], v0=float(B['v_forward']),
        rate_demol=float(B['demolition_rate']), rate_unc=np.asarray(fi['rate_unc'], float),
        long_run_residual=float(B['unconsented_rate']),
        a13_2025={t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}, red13=B['RED13_TOT'],
        a45_2025={t: float(B['MAT_STAGE']['A4-A5'][t].sum()) for t in typ}, red45=B['RED45_TOT'],
        excess=np.asarray(ji['excess'], float).copy(), absorb_w=absorption_weights(fy),
        join_reference=np.asarray(ji['join'], float), profile=prof, committed_factors=fac,
        c14={t: float(B['stage_int'].loc['C1-C4', t]) for t in typ}, soil=B['SOIL_INTENSITY'],
        events=fi['events'], b_ar=b_ar, b_atp=b_atp)


# ============================================================
# RE-OCCUPATION (TL1 / TL2 releases)
# ============================================================
REOCCUPATION_RULES = ('constant_share', 'fast')   # adopted; 'fast' = as fast as demand allows (A4 sensitivity row)


def reoccupation(years, gross, released, rule='constant_share'):
    """Constant-share re-occupation (MODEL v3.0.0). The dwellings released in 2027-2050 by TL1 and TL2 (R in total)
    meet a constant share of each year's need after the overbuild payback:

        target_t = max(gross_t, 0) x s,   s = min(R, G+) / G+,   G+ = sum over 2027-2050 of max(gross_t, 0)

    The dwellings re-occupied up to year t never exceed those released up to t. Where that binds, the shortfall is
    BUILT (not carried) and the share is recomputed from the remaining pool for the remaining years:
    s = min(R - re-occupied so far, remaining G+) / remaining G+. built_t = max(gross_t, 0) - re-occupied_t >= 0.
    Where R > G+, s = 1 and the surplus R - G+ stays vacant in 2050. 2025 and 2026 pass through (2026 observed).

    rule 'fast' (MODEL v3.2.0, A4 sensitivity row): re-occupation as fast as demand allows,
    reoccupied_t = min(max(gross_t, 0), cumulative released to t - cumulative re-occupied to t-1)."""
    years = np.asarray(years)
    gross = np.asarray(gross, float)
    released = np.asarray(released, float)
    mask = (years >= REOCCUPATION_YEARS[0]) & (years <= REOCCUPATION_YEARS[1])
    n = len(years)
    gp = np.where(mask, np.maximum(gross, 0.0), 0.0)
    R, Gp = float(released[mask].sum()), float(gp.sum())
    reocc, share_t = np.zeros(n), np.zeros(n)
    binds = np.zeros(n, bool)
    if R > 0.0 and Gp <= 0.0:
        raise SystemExit('STOP: re-occupation: no positive need in 2027-2050.')
    share = min(R, Gp) / Gp if R > 0.0 else 0.0
    share0 = share
    tol = REOCCUPATION_TOL * max(R, 1.0)
    cum_rel = cum_re = 0.0
    idx = np.flatnonzero(mask)
    if rule == 'fast':
        for i in idx:
            cum_rel += released[i]
            reocc[i] = max(0.0, min(gp[i], cum_rel - cum_re))
            binds[i] = (cum_rel - cum_re) < gp[i] - tol and R > 0.0
            share_t[i] = reocc[i] / gp[i] if gp[i] > 0 else 0.0
            cum_re += reocc[i]
        idx = []
    elif rule != 'constant_share':
        raise ValueError(f'reoccupation rule {rule!r}: one of {REOCCUPATION_RULES}.')
    for j, i in enumerate(idx):
        cum_rel += released[i]
        target = gp[i] * share
        avail = cum_rel - cum_re
        a = max(0.0, min(target, avail))
        share_t[i] = share
        if avail < target - tol:                       # the release binds: build the shortfall, recompute s
            binds[i] = True
            pool = R - (cum_re + a)
            rem = float(gp[idx[j + 1:]].sum())
            share = min(pool, rem) / rem if rem > 0.0 else 0.0
        reocc[i] = a
        cum_re += a
    built = np.where(mask, gp - reocc, gross)
    return dict(built=built, reoccupied=reocc, share_by_year=share_t, release_binds=binds, R=R, G_plus=Gp,
                share=share0, reoccupied_total=cum_re, surplus_vacant_2050=R - cum_re,
                nonpositive_need=float(-np.minimum(gross[mask], 0.0).sum()),
                nonpositive_need_years=[int(y) for y, g in zip(years[mask], gross[mask]) if g <= 0.0], mask=mask)


# ============================================================
# ONE RUN AND ITS METRICS
# ============================================================
def carry_negative(years, gross, mask):
    """MODEL v3.2.0 (A2): a year whose gross building is negative (releases in the requirement, the unconsented
    additions, exceed the gross need) builds nothing; the unusable dwellings are carried forward and used, in full,
    against the next years' gross building. Returns (gross after the carry >= 0 in the masked years, negclip_t
    (dwellings carried out of year t), neg_used_t, carry at the end)."""
    g = np.asarray(gross, float).copy()
    clip, used = np.zeros(len(g)), np.zeros(len(g))
    carry = 0.0
    for i in np.flatnonzero(mask):
        if g[i] < 0.0:
            clip[i] = -g[i]
            carry += -g[i]
            g[i] = 0.0
        elif carry > 0.0:
            u = min(carry, g[i])
            used[i] = u
            g[i] -= u
            carry -= u
    return g, clip, used, carry


def use_in_year(gross, released, mask):
    """MODEL v3.2.0 (A2), runs without any lever at its theoretical limit: dwellings released by a vacancy-rate fall
    are used in the year they occur, capped at the year's gross need (after the payback); the rest is carried to the
    next years. Returns (used_t, carry at the end)."""
    used = np.zeros(len(gross))
    carry = 0.0
    for i in np.flatnonzero(mask):
        pool = carry + released[i]
        used[i] = min(pool, max(gross[i], 0.0))
        carry = pool - used[i]
    return used, carry


def run(ctx, p, levels, ramp_name=None, reocc_rule='constant_share'):
    """One run of the model with the levers at `levels` ({lever: 'moderate' | 'ambitious' | 'tl' | lambda}); see the
    module docstring for the order gross -> payback -> re-occupation -> built.

    MODEL v3.2.0 release accounting (A2; bands.py): the payback is taken on the GROSS need (the requirement with
    the dwellings released by a vacancy-rate fall added back); a negative gross year builds nothing and carries the
    unusable dwellings forward (carry_negative). In a theoretical-limit-family run (any lever at 'tl') every release
    present in the run, the vacancy-rate fall at any level and the household-size fall, enters the re-occupation pool
    (reoccupation(): constant share of each year's need, availability constraint, attribution in proportion to the
    release of each source). In any other run the vacancy release is used in the year it occurs, capped at the gross
    need, the rest carried (use_in_year). Whatever is still unusable in 2050 is kept vacant (bands: 'Surplus kept
    vacant (2050)')."""
    fi, info = LV.inputs(ctx, p, levels, ramp_name)
    years = np.asarray(ctx['years'])
    n = len(years)
    zeros = np.zeros(n)
    hh = info['hh']
    E1 = engine.forward(ctx['pop'], hh, ctx['growth'], join=zeros, join_redev=zeros, **fi)
    req = np.asarray(engine.requirement(E1), float)
    late = years >= REOCCUPATION_YEARS[0]
    v = np.broadcast_to(np.asarray(E1['v'], float), (n,))
    tl_family = bool(info['tl'])
    rel_v = np.where(late, -np.minimum(np.asarray(E1['change'], float), 0.0), 0.0)      # vacancy-rate fall
    if np.any(np.asarray(E1['change'], float)[~late] < 0.0):
        raise SystemExit('run: a vacancy-rate fall before 2027 (2026 is observed).')
    rel3 = (np.where(late, -np.minimum(np.asarray(E1['d_hh_raw'], float), 0.0) / (1.0 - v), 0.0)
            if tl_family else zeros)                                                      # household-size fall
    hh_fall_years = [int(y) for y, d in zip(years[late], np.asarray(E1['d_hh_raw'], float)[late]) if d < 0.0]
    need = req + rel_v                                # gross need: the vacancy release is not netted
    excess = ctx['excess']
    if ctx['absorb_w'] is None:                       # overbuild never absorbed (legacy Reference)
        ab = dict(paid=zeros, carry=zeros, cap_binds=np.zeros(n, bool), built=need + excess, U=np.cumsum(excess))
    else:
        _, ab = engine.absorb_overbuild(excess, ctx['absorb_w'], need)
    gross0 = ab['built']                              # need + excess - payback
    gross, negclip, neg_used, neg_carry = carry_negative(years, gross0, late)
    if tl_family:
        ro = reoccupation(years, gross, rel3 + rel_v, reocc_rule)
        reocc, used_v, vac_carry = ro['reoccupied'], zeros, 0.0
        pool_rem = ro['surplus_vacant_2050']
    else:
        ro = reoccupation(years, gross, zeros)
        used_v, vac_carry = use_in_year(gross, rel_v, late)
        reocc, pool_rem = zeros, 0.0
    built = ro['built'] - used_v
    join = excess - ab['paid'] + (rel_v - used_v) - reocc + (negclip - neg_used)
    E = engine.forward(ctx['pop'], hh, ctx['growth'], join=join, join_redev=zeros, **fi)
    R_tot = ro['R']
    s3 = float(rel3.sum() / R_tot) if R_tot > 0 else 0.0
    ro.update(released_tl1=rel3, released_tl2=rel_v if tl_family else zeros, gross=gross, need=need,
              requirement_nojoin=req, reoccupied_tl1=reocc * s3,
              reoccupied_tl2=reocc * (1.0 - s3) if R_tot > 0 else zeros,
              R1=float(rel3.sum()), R2=float(rel_v.sum()) if tl_family else 0.0)
    flows = dict(rel_v=rel_v, used_v=used_v, reocc=reocc, negclip=negclip, neg_used=neg_used,
                 vac_carry_end=float(vac_carry), pool_remainder=float(pool_rem), neg_carry_end=float(neg_carry))
    info.update(excess=excess, payback=ab['paid'], payback_carry=ab['carry'], payback_cap_binds=ab['cap_binds'],
                reoccupation=ro, flows=flows, tl_family=tl_family, households_fall_years=hh_fall_years,
                negative_gross_years=[int(y) for y, c in zip(years, negclip) if c > 0.0],
                vacancy_released=float(rel_v.sum()) if not tl_family else 0.0,
                built_check=built)
    if not np.allclose(engine.requirement(E)[late], built[late], rtol=1e-9, atol=1e-6):
        raise SystemExit(f'run {LV.label(levels)}: dwellings built differ from the release accounting.')
    return dict(E=E, inputs=fi, info=info, levels=dict(levels), ramp=ramp_name or RAMP_ADOPTED,
                scenario=ctx['scenario'])


def committed(ctx, gfa_t):
    """Committed after 2050 (kt): the 2026-2050 cohorts' later replacements and repaints (events.committed; upper:
    2025 factors, lower: 2050 factors held) and all their C1-C4 (2025 factors), with this run's floor area."""
    b = {'upper': 0.0, 'lower': 0.0}
    for k, t in enumerate(ctx['typ']):
        for key in b:
            b[key] += EV.committed(gfa_t[k], ctx['years'], ctx['profile'][t], ctx['committed_factors'][(t, key)])
    c = sum(gfa_t[k][1:].sum() * ctx['c14'][t] for k, t in enumerate(ctx['typ']))
    return dict(B_upper_kt=b['upper'] / M6, B_lower_kt=b['lower'] / M6, C_kt=c / M6,
                upper_kt=(b['upper'] + c) / M6, lower_kt=(b['lower'] + c) / M6)


def implied_vacancy(E):
    """1 - households / physical stock. The engine's required stock hh / (1 - v) plus the join stock (the overbuild
    still vacant, the TL2 release not yet re-occupied) plus the dwellings released by a household decline (TL1; d_hh
    is floored at 0 in the engine), release_t = -min(d_hh_raw, 0) / (1 - v_t)."""
    v = np.broadcast_to(np.asarray(E['v'], float), E['hh'].shape)
    rel = np.cumsum(-np.minimum(E['d_hh_raw'], 0.0) / (1.0 - v))
    return 1.0 - E['hh'] / (E['stock'] + E['stock_join'] + rel)


def stage_arrays(ctx, R):
    """Annual carbon by stage (kg): A1-A3, A4-A5 and soil (upfront), maintenance (B2, B4 in the window)."""
    E, info = R['E'], R['info']
    gfa_t = E['gfa_t']
    a13 = sum(gfa_t[k] * np.asarray(info['a13'][t], float) for k, t in enumerate(ctx['typ']))
    a45 = sum(gfa_t[k] * np.asarray(info['a45'][t], float) for k, t in enumerate(ctx['typ']))
    soil = np.asarray(E['soil'], float)
    return dict(a13=a13, a45=a45, soil=soil, maintenance=E['b_t'].sum(axis=0))


def quick(ctx, R):
    """The Shapley metrics of a run (2026-2050)."""
    I = float(np.sum(R['E']['carbon'][1:]))
    return dict(carbon_kt=I / M6, LoE_AR=I / float(np.sum(ctx['b_ar'])), LoE_AtP=I / float(np.sum(ctx['b_atp'])),
                gfa_Mm2=float(R['E']['gfa_t'][:, 1:].sum()) / M6)


def metrics(ctx, R, label, setting):
    """Every reported quantity of one run (window 2026-2050 unless stated)."""
    E, info, fi = R['E'], R['info'], R['inputs']
    f = slice(1, None)
    gfa_t = E['gfa_t']
    I = E['carbon'][f]
    st = stage_arrays(ctx, R)
    up = E['upfront'][f].sum()
    if not math.isclose(st['a13'][f].sum() + st['a45'][f].sum() + st['soil'][f].sum(), up, rel_tol=1e-12):
        raise SystemExit(f'{label}: A1-A3 + A4-A5 + soil does not equal upfront.')
    com = committed(ctx, gfa_t)
    v_impl = implied_vacancy(E)
    dwell = E['dwell_in_scope'][f]
    built_all = engine.requirement(E)[f]
    loe_ar, loe_atp = aesa.cumulative_loe(I, ctx['b_ar']), aesa.cumulative_loe(I, ctx['b_atp'])
    gfa = gfa_t[:, f].sum()
    S = E['pop'] / E['hh']
    size = fi['size']
    size_minus_occ = min(float((np.broadcast_to(np.asarray(size[t], float), S.shape)
                                - S * np.asarray(fi['olf'][t], float))[f].min()) for t in ctx['typ'])
    held = info.get('l4_held')
    ro = info['reoccupation']
    yy = np.asarray(ctx['years'])
    return dict(run=label, scenario=ctx['scenario'], setting=setting, levers=LV.label(R['levels']),
                adoption=R['ramp'], gfa_Mm2=gfa / M6, gfa_2027_2050_Mm2=gfa_t[:, 2:].sum() / M6,
                carbon_kt=I.sum() / M6, upfront_kt=up / M6, b_inwindow_kt=E['b_t'][:, f].sum() / M6,
                soil_kt=st['soil'][f].sum() / M6, a13_kt=st['a13'][f].sum() / M6, a45_kt=st['a45'][f].sum() / M6,
                carbon_excl_soil_kt=(I.sum() - st['soil'][f].sum()) / M6,
                committed_lower_kt=com['lower_kt'], committed_upper_kt=com['upper_kt'],
                committed_B_lower_kt=com['B_lower_kt'], committed_B_upper_kt=com['B_upper_kt'],
                committed_C_kt=com['C_kt'],
                B_AR_kt=ctx['b_ar'].sum() / M6, B_AtP_kt=ctx['b_atp'].sum() / M6,
                LoE_AR=loe_ar, LoE_AtP=loe_atp,
                remaining_reduction_AR=1.0 - 1.0 / loe_ar, remaining_reduction_AtP=1.0 - 1.0 / loe_atp,
                dwellings_built=dwell.sum(), dwellings_built_all_categories=built_all.sum(),
                dwellings_built_min_year=float(min(dwell.min(), built_all.min())),
                mean_dwelling_size_m2=gfa / dwell.sum(),
                carbon_per_m2_kg=I.sum() / gfa, carbon_per_dwelling_t=I.sum() / dwell.sum() / 1e3,
                implied_vacancy_min=float(v_impl[f].min()), implied_vacancy_2035=float(v_impl[10]),
                implied_vacancy_2050=float(v_impl[-1]), implied_vacancy_max=float(v_impl[f].max()),
                stock_vacancy_2050=float(np.broadcast_to(E['v'], E['hh'].shape)[-1]),
                D_minus_occ_min_m2=float((E['D'] - E['occ'])[f].min()),
                extra_clip_max_m2=float(np.abs(E['extra_clip'][f]).max()),
                overbuild_excess_dwellings=float(info['excess'][f].sum()),
                overbuild_absorbed_dwellings=float(info['payback'][f].sum()),
                overbuild_payback_carried_2050=float(info['payback_carry'][-1]),
                overbuild_cap_binding_years=';'.join(str(int(y)) for y in yy[info['payback_cap_binds']]),
                released_tl1=ro['R1'], released_tl2=ro['R2'], reoccupied=ro['reoccupied_total'],
                G_plus=ro['G_plus'], reoccupation_share=ro['share'],
                surplus_vacant_2050=(info['flows']['pool_remainder'] + info['flows']['vac_carry_end']
                                     + info['flows']['neg_carry_end']),
                vacancy_released_dwellings=float(info['flows']['used_v'][f].sum() + info['flows']['vac_carry_end']),
                households_fall_years=';'.join(str(y) for y in info['households_fall_years']),
                negative_gross_years=';'.join(str(y) for y in info['negative_gross_years']),
                reoccupation_binding_years=';'.join(str(int(y)) for y in yy[ro['release_binds']]),
                zero_building_years=';'.join(str(int(y)) for y, b in zip(yy[2:], engine.requirement(E)[2:])
                                             if b <= T_ZERO_TOL_DWELLINGS),
                vacancy_change_dwellings=float(E['change'][f].sum()),
                size_minus_occupied_min_m2=size_minus_occ,
                l4_held_typology_years=int(sum(h[f].sum() for h in held.values())) if held else 0,
                households_min_change=float(E['d_hh_raw'][f].min()),
                households_released=float(-np.minimum(E['d_hh_raw'][f], 0.0).sum()),
                brownfield_share=float(E['soil_free_gfa'][f].sum() / E['total'][f].sum()),
                replacement_share=float(E['soil_free_replacement_gfa'][f].sum() / E['total'][f].sum()),
                mean_household_size_2050=float(S[-1]))


def annual_rows(ctx, R, label):
    E, info = R['E'], R['info']
    v_impl = implied_vacancy(E)
    st = stage_arrays(ctx, R)
    ro = info['reoccupation']
    built = engine.requirement(E)
    rows = []
    for i, y in enumerate(ctx['years']):
        if y < WINDOW[0]:
            continue
        j = i - 1
        rows.append(dict(run=label, scenario=ctx['scenario'], year=int(y),
                         carbon_kt=E['carbon'][i] / M6, upfront_kt=E['upfront'][i] / M6,
                         a13_kt=st['a13'][i] / M6, a45_kt=st['a45'][i] / M6, soil_kt=st['soil'][i] / M6,
                         maintenance_kt=st['maintenance'][i] / M6, gfa_Mm2=E['gfa_t'][:, i].sum() / M6,
                         dwellings_built=E['dwell_in_scope'][i], dwellings_built_all_categories=built[i],
                         dwelling_size_m2=E['D'][i], occupied_area_m2=E['occ'][i], implied_vacancy=v_impl[i],
                         stock_vacancy=float(np.broadcast_to(E['v'], E['hh'].shape)[i]),
                         vacancy_change_dwellings=E['change'][i], overbuild_excess=info['excess'][i],
                         overbuild_payback=info['payback'][i], vacancy_released_used=info['flows']['used_v'][i],
                         released_tl1=ro['released_tl1'][i],
                         released_tl2=ro['released_tl2'][i], reoccupied=ro['reoccupied'][i],
                         households=E['hh'][i], household_size=E['pop'][i] / E['hh'][i],
                         brownfield_share=(E['soil_free_gfa'][i] / E['total'][i] if E['total'][i] > T_ZERO_TOL_M2 else 0.0),
                         B_AR_kt=ctx['b_ar'][j] / M6, B_AtP_kt=ctx['b_atp'][j] / M6,
                         LoE_AR=E['carbon'][i] / ctx['b_ar'][j], LoE_AtP=E['carbon'][i] / ctx['b_atp'][j]))
    return rows


# ============================================================
# DEMAND BANDS (projection bookkeeping; naming.BANDS_*_TL)
# ============================================================
BAND_ORDER_IN_SCOPE = [N.band_data_label(b) for b in BANDS.IN_SCOPE]
BAND_ORDER_RV = BAND_ORDER_IN_SCOPE[:-2] + [N.band_data_label('retirement_villages')] + BAND_ORDER_IN_SCOPE[-2:]


def band_set(ctx, R):
    """In-scope bands of a run (bands.in_scope): {band id: (floor area m2, carbon kg)} over the model years."""
    E, info = R['E'], R['info']
    return BANDS.in_scope(E, R['inputs'], info['excess'], info['payback'], info['flows'], ctx['long_run_residual'],
                          ctx['typ'])


def band_annual(ctx, R):
    """In-scope bands by year 2026-2050: {band label: (floor area m2 array, carbon kg array)}; the bands add up to the
    run's floor area and carbon in every year (bands.check, 1e-9; no rescaling)."""
    bs = band_set(ctx, R)
    f = slice(1, None)
    return {N.band_data_label(b): (bs[b][0][f], bs[b][1][f]) for b in BANDS.IN_SCOPE}


def band_rows(ctx, R, label):
    """Cumulative bands 2026-2050 under both definitions: in scope, and with the retirement-village units shown as
    their own (negative) band (every other band at its gross floor area; bands.with_retirement_villages)."""
    f = slice(1, None)
    rows = []
    rv = BANDS.with_retirement_villages(R['E'], R['inputs'], R['info']['excess'], R['info']['payback'],
                                        R['info']['flows'], ctx['long_run_residual'], ctx['typ'])
    for b, (gv, cv) in rv.items():
        rows.append(dict(run=label, scenario=ctx['scenario'], definition='with_retirement_villages',
                         band=N.band_data_label(b), gfa_Mm2=gv[f].sum() / M6, carbon_kt=cv[f].sum() / M6))
    rows += [dict(run=label, scenario=ctx['scenario'], definition='in_scope', band=b, gfa_Mm2=gv.sum() / M6,
                  carbon_kt=cv.sum() / M6) for b, (gv, cv) in band_annual(ctx, R).items()]
    return rows


def band_annual_rows(ctx, R, label):
    rows = []
    for b, (gv, cv) in band_annual(ctx, R).items():
        rows += [dict(run=label, year=int(y), band=b, gfa_Mm2=float(gv[i]) / M6, carbon_kt=float(cv[i]) / M6)
                 for i, y in enumerate(ctx['years'][1:])]
    return rows


# ============================================================
# ATTRIBUTION
# ============================================================
def subsets(items):
    return [frozenset(s) for n in range(len(items) + 1) for s in itertools.combinations(items, n)]


def shapley(value, players):
    """Shapley value of each player for the REDUCTION v(empty) - v(all), in exact rational arithmetic on the float
    run values (Fraction), so that sum_i phi_i = v(empty) - v(all) holds exactly. value: {frozenset: float}."""
    n = len(players)
    v = {k: Fraction(x) for k, x in value.items()}
    phi = {}
    for i in players:
        s = Fraction(0)
        for S in subsets([q for q in players if q != i]):
            wgt = Fraction(math.factorial(len(S)) * math.factorial(n - len(S) - 1), math.factorial(n))
            s += wgt * (v[S] - v[S | {i}])
        phi[i] = s
    return phi


def shapley_rows(value, players, game, metric, names):
    phi = shapley(value, players)
    full = frozenset(players)
    total = Fraction(value[frozenset()]) - Fraction(value[full])
    rows = [dict(game=game, metric=metric, player=pl, name=names[pl], reduction=float(phi[pl]),
                 share_of_total=float(phi[pl] / total) if total != 0 else float('nan')) for pl in players]
    return rows, (phi, total)


# ============================================================
# BACK-CAST AND SOLUTION SPACE (carbon linear in floor area and in intensity)
# ============================================================
def carbon_parts(ctx, R):
    """Annual carbon split by cohort: materials and construction A1-A5 in the construction year (mat), soil carbon
    loss in the construction year (soil) and in-window events of cohort i in occurrence year j (ev[i, j]).
    Sum = E['carbon']."""
    E = R['E']
    soil = np.asarray(E['soil'], float)
    mat = np.asarray(E['upfront'], float) - soil
    ev = np.zeros((len(ctx['years']), len(ctx['years'])))
    for k, t in enumerate(ctx['typ']):
        ev += E['gfa_t'][k][:, None] * ctx['events'][t]
    if not np.allclose(mat + soil + ev.sum(axis=0), E['carbon'], rtol=1e-12, atol=1e-6):
        raise SystemExit('carbon_parts: the cohort split does not reproduce the annual carbon.')
    return dict(mat=mat, soil=soil, ev=ev)


def linear_split(ctx, R):
    """Annual carbon (kg, 2026-2050) = fixed + later (MODEL v3.2.0): fixed = the 2026 cohort's emissions in the window
    (its A1-A5, soil carbon loss and in-window events; identical in every run, 2026 observed); later = every emission
    in the window of the 2027-2050 cohorts (A1-A5, soil carbon loss, in-window B2/B4), the quantity a cut in
    2027-2050 floor area (x) and in total carbon per m2 (y) scales by (1 - x)(1 - y) (Fig6)."""
    p = carbon_parts(ctx, R)
    n = len(ctx['years'])
    idx = np.arange(n)
    fixed = np.where(idx == 1, p['mat'] + p['soil'], 0.0) + p['ev'][1]
    later = np.where(idx >= 2, p['mat'] + p['soil'], 0.0) + p['ev'][2:].sum(axis=0)
    later_soil = np.where(idx >= 2, p['soil'], 0.0)
    f = slice(1, None)
    if not np.allclose((fixed + later)[f], R['E']['carbon'][f], rtol=1e-12, atol=1e-6):
        raise SystemExit('linear_split does not reproduce the annual carbon.')
    return dict(fixed=fixed[f], later=later[f], later_soil=later_soil[f], gfa_later=R['E']['gfa_t'][:, 2:].sum())


def scaled_carbon(split, k_demand, k_intensity=1.0):
    return split['fixed'] + k_demand * k_intensity * split['later']


def backcast(ctx, R, label):
    """k on all 2027-2050 construction such that cumulative LoE AR = 1 (brentq); AtP minimum at k = 0."""
    s = linear_split(ctx, R)
    bar, batp = ctx['b_ar'].sum(), ctx['b_atp'].sum()
    loe = lambda k, b: scaled_carbon(s, k).sum() / b
    lo_ar, hi_ar = loe(0.0, bar), loe(1.0, bar)
    out = dict(run=label, LoE_AR_at_k1=hi_ar, LoE_AtP_at_k1=loe(1.0, batp), LoE_AR_min_k0=lo_ar,
               LoE_AtP_min_k0=loe(0.0, batp), carbon_fixed_2026_cohort_kt=s['fixed'].sum() / M6,
               carbon_2027_2050_cohorts_kt=s['later'].sum() / M6,
               gfa_2027_2050_Mm2=s['gfa_later'] / M6)
    if lo_ar < 1.0 < hi_ar:
        k = brentq(lambda k: loe(k, bar) - 1.0, 0.0, 1.0, xtol=BRENTQ_XTOL, rtol=4 * np.finfo(float).eps)
        out.update(k_AR=k, k_AR_closed_form=(bar - s['fixed'].sum()) / s['later'].sum(),
                   cut_AR=1.0 - k, LoE_AR_at_k=loe(k, bar), gfa_2027_2050_at_k_Mm2=k * s['gfa_later'] / M6)
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
    """Fig6 coordinates of a run against the Reference (MODEL v3.2.0): x = cut in 2027-2050 floor area,
    1 - GFA_P / GFA_0; y = cut in 2027-2050 total carbon per m2 (A1-A5, soil and events of the 2027-2050 cohorts
    within the window), 1 - (C_P / GFA_P) / (C_0 / GFA_0). With the fixed part identical in every run,
    LoE_AR(x, y) = [fixed + C_0 (1 - x)(1 - y)] / B_AR reproduces the run's LoE exactly (tests)."""
    if not np.allclose(split['fixed'], split0['fixed'], rtol=1e-9, atol=1e-3):
        raise SystemExit('effective_coordinates: the fixed part (the 2026 cohort) differs from the Reference.')
    d = 1.0 - split['gfa_later'] / split0['gfa_later']
    c, c0 = split['later'].sum(), split0['later'].sum()
    return float(d), float(1.0 - (c / split['gfa_later']) / (c0 / split0['gfa_later']))


# ============================================================
# STATES
# ============================================================
def load_factors_building():
    return pd.read_csv(validation.projection.FILE_FACTORS_BUILDING)


def boss_state(scenario):
    with contextlib.redirect_stdout(io.StringIO()):
        return validation.run_boss(**SCENARIOS[scenario][1])


def household_size_variants(B_ref):
    """{variant: dict(S, pop)} of the Stats NZ household-size variants: the Reference projection with
    projection.HH_SIZE_VARIANT changed (the Reference itself for its own variant)."""
    out = {}
    for v in LV.L1_VARIANTS:
        if v == validation.projection.HH_SIZE_VARIANT:
            B = B_ref
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                B = validation.run_boss(**dict(SCENARIOS[REFERENCE][1], HH_SIZE_VARIANT=v))
        out[v] = dict(S=LV.household_size(B), pop=np.asarray(B['df_forecast']['PopTotal_50th'].values, float))
    return out


def resolve_params(B_ref):
    import Building_factors as BF
    return LV.resolve(B_ref, load_factors_building(), BF.load_characteristics(),
                      pd.read_csv(validation.projection.FILE_FACTORS_TYPOLOGY), validation.projection,
                      household_size_variants(B_ref), runprofile.get('bootstrap'))


def run_name(what, setting, ramp_name=None):
    """'REF' (a variant id), 'S2-moderate', 'L4-tl', 'pathway-moderate-by2045', 'L2-lambda0.3'."""
    if what in N.SCENARIOS:
        return what
    return f'{what}-{setting}' + (f'-{ramp_name}' if ramp_name else '')


# ============================================================
# COMPUTE
# ============================================================
def compute(scenarios=tuple(SCENARIOS), verbose=True):
    """All deterministic runs. Returns a dict of tables and the objects the checks need."""
    t0 = time.time()
    bounds = boundaries()
    states = {s: boss_state(s) for s in scenarios}
    if REFERENCE not in states:
        raise ValueError('The Reference (REF) is required.')
    params = resolve_params(states[REFERENCE])
    LV.stop_checks(params)
    ctxs = {s: base_context(states[s], s, bounds) for s in scenarios}
    cache = {}

    def get(scen, levels, ramp_name=None):
        k = (scen,) + LV.key(levels, ramp_name)
        if k not in cache:
            cache[k] = run(ctxs[scen], params, levels, ramp_name)
        return cache[k]

    ref = ctxs[REFERENCE]
    TL_ALL = LV.tl_levels(LV.TL_COMPONENTS)
    # ---- named runs ----
    named = [(REFERENCE, REFERENCE, 'reference', {}, None)]
    for s in ('moderate', 'ambitious', 'tl'):
        for L in LV.LEVERS:
            named.append((run_name(L, s), REFERENCE, s, {L: s}, None))
    for s in LV.SETTINGS:
        for P in tuple(LV.STRATEGIES) + (LV.PATHWAY,):
            named.append((run_name(P, s), REFERENCE, s, LV.pathway_levers(P, s), None))
    named.append(('TL', REFERENCE, 'tl', TL_ALL, None))
    named.append((LV.TL_INSTANT_LABEL, REFERENCE, 'tl', TL_ALL, LV.TL_FROM2027))
    for rs in LV.ADOPTION_SENSITIVITIES:
        for s in LV.SETTINGS:
            named.append((run_name(LV.PATHWAY, s, rs['name']), REFERENCE, s, LV.pathway_levers(LV.PATHWAY, s),
                          rs['name']))
    for scen in scenarios:
        if scen != REFERENCE:
            named.append((scen, scen, 'reference', {}, None))
            for s in LV.SETTINGS:
                named.append((run_name(LV.PATHWAY, s), scen, s, LV.pathway_levers(LV.PATHWAY, s), None))
            named.append(('TL', scen, 'tl', TL_ALL, None))
    rows, annual, bands, bands_annual = [], [], [], []
    for name, scen, s, levels, rn in named:
        R = get(scen, levels, rn)
        rows.append(metrics(ctxs[scen], R, name, s))
        annual += annual_rows(ctxs[scen], R, name)
        bands += band_rows(ctxs[scen], R, name)
        if scen == REFERENCE and rn is None:
            bands_annual += [dict(r, scenario=scen) for r in band_annual_rows(ctxs[scen], R, name)]
    # MODEL v3.2.0 (A4): TL with re-occupation as fast as demand allows (sensitivity row; not cached: its own rule)
    R_fast = run(ref, params, TL_ALL, reocc_rule='fast')
    rows.append(metrics(ref, R_fast, TL_REOCCUPATION_FAST, 'tl'))
    annual += annual_rows(ref, R_fast, TL_REOCCUPATION_FAST)
    runs_df = pd.DataFrame(rows)
    p0 = runs_df[runs_df['run'] == runs_df['scenario']].set_index('scenario')
    for col in ('carbon_kt', 'LoE_AR', 'LoE_AtP', 'gfa_Mm2', 'committed_lower_kt', 'committed_upper_kt'):
        runs_df[f'delta_{col}_vs_reference_pct'] = [100.0 * (r[col] / p0.loc[r['scenario'], col] - 1.0)
                                                   for _, r in runs_df.iterrows()]
    bands_df = pd.DataFrame(bands)
    b0 = bands_df[bands_df['run'] == bands_df['scenario']].set_index(['scenario', 'definition', 'band'])
    for col in ('gfa_Mm2', 'carbon_kt'):
        bands_df[f'delta_{col}_vs_reference'] = [r[col] - b0.loc[(r['scenario'], r['definition'], r['band']), col]
                                                 for _, r in bands_df.iterrows()]

    # ---- Shapley games (exact; every subset a cached run) ----
    games = [('strategies_moderate', tuple(LV.STRATEGIES), dict(LV.STRATEGY_NAMES),
              lambda S: {L: 'moderate' for P in S for L in LV.STRATEGIES[P]}),
             ('strategies_ambitious', tuple(LV.STRATEGIES), dict(LV.STRATEGY_NAMES),
              lambda S: {L: 'ambitious' for P in S for L in LV.STRATEGIES[P]}),
             ('levers_moderate', LV.LEVERS, dict(LV.LEVER_NAMES), lambda S: {L: 'moderate' for L in S}),
             ('levers_ambitious', LV.LEVERS, dict(LV.LEVER_NAMES), lambda S: {L: 'ambitious' for L in S}),
             ('levers_tl', LV.LEVERS, dict(LV.LEVER_NAMES), lambda S: {L: 'tl' for L in S}),
             (TL_GAME, LV.TL_COMPONENTS, dict(LV.TL_NAMES), lambda S: LV.tl_levels(S, 'moderate'))]
    shap_rows, sub_rows, shap_exact = [], [], {}
    for game, players, names, levels_of in games:
        vals = {m: {} for m in SHAPLEY_METRICS}
        for S in subsets(players):
            levels = levels_of(S)
            R = get(REFERENCE, levels)
            q = quick(ref, R)
            for m in SHAPLEY_METRICS:
                vals[m][S] = q[m]
            ro = R['info']['reoccupation']
            sub_rows.append(dict(game=game, subset='+'.join(x for x in players if x in S) or 'none',
                                 n_players=len(S), levels=LV.label(levels), **q,
                                 reoccupation_share=ro['share'], R=ro['R'],
                                 reoccupation_binding_years=int(ro['release_binds'].sum()),
                                 dwellings_built_min=float(np.min(engine.requirement(R['E'])[1:]))))
        for m in SHAPLEY_METRICS:
            r_, ex = shapley_rows(vals[m], players, game, m, names)
            shap_rows += r_
            shap_exact[(game, m)] = ex

    # ---- lambda-sweep per lever (Reference 0, Moderate 0.5, Ambitious 1) and the TL point ----
    sweep = []
    for L in LV.LEVERS:
        for lam in list(LAMBDA_GRID) + ['tl']:
            R = get(REFERENCE, {L: lam} if lam != 0.0 else {})
            sweep.append(dict(lever=L, name=LV.LEVER_NAMES[L], lam=lam if lam != 'tl' else float('nan'),
                              level='tl' if lam == 'tl' else {0.0: 'reference', 0.5: 'moderate', 1.0: 'ambitious'}.get(
                                  float(lam), ''), **quick(ref, R)))

    # ---- back-cast (the Pathways, TL, Reference) and solution space ----
    R0 = get(REFERENCE, {})
    bc0, split0 = backcast(ref, R0, REFERENCE)
    bar, batp = ref['b_ar'].sum(), ref['b_atp'].sum()
    bcs = {REFERENCE: bc0}
    for nm, levels in ((run_name(LV.PATHWAY, 'moderate'), LV.pathway_levers(LV.PATHWAY, 'moderate')),
                       (run_name(LV.PATHWAY, 'ambitious'), LV.pathway_levers(LV.PATHWAY, 'ambitious')), ('TL', TL_ALL)):
        bcs[nm], _ = backcast(ref, get(REFERENCE, levels), nm)
    space = solution_space(split0, bar, batp)
    markers = []
    for nm, levels in ([(run_name(P, s), LV.pathway_levers(P, s)) for P in tuple(LV.STRATEGIES) + (LV.PATHWAY,)
                        for s in LV.SETTINGS] + [('TL', TL_ALL)]):
        Rp = get(REFERENCE, levels)
        d, i = effective_coordinates(linear_split(ref, Rp), split0)
        I = Rp['E']['carbon'][1:].sum()
        markers.append(dict(run=nm, demand_reduction=d, intensity_reduction=i, LoE_AR_run=I / bar,
                            LoE_AR_on_grid_at_coordinates=scaled_carbon(split0, 1.0 - d, 1.0 - i).sum() / bar,
                            LoE_AtP_run=I / batp))
    backcast_out = dict(run_mode=RUN_MODE, method='uniform factor k on the floor area by typology of every 2027-2050 '
                        'cohort (2026 and its events fixed); scipy.optimize.brentq on [0, 1], xtol 1e-15',
                        B_AR_kt=bar / M6, B_AtP_kt=batp / M6, solution_space_markers=markers, **bcs)

    # ---- waterfalls ----
    wf = pd.concat([waterfall(ref, get, s) for s in LV.SETTINGS], ignore_index=True)
    wf_tl = waterfall_tl_from_reference(ref, get)
    seq_vs_shap = sequential_vs_shapley(wf, pd.DataFrame(shap_rows))

    # ---- per-lever annual carbon (single-lever runs) and the re-occupation log of the TL runs ----
    lever_annual = []
    for L in LV.LEVERS:
        for s in ('reference', 'moderate', 'ambitious', 'tl'):
            R = get(REFERENCE, {} if s == 'reference' else {L: s})
            lever_annual += [dict(lever=L, level=s, year=int(y), carbon_kt=R['E']['carbon'][i] / M6,
                                  gfa_Mm2=R['E']['gfa_t'][:, i].sum() / M6)
                             for i, y in enumerate(ref['years']) if y >= WINDOW[0]]
    reocc_log = []
    for nm, R in (('TL', get(REFERENCE, TL_ALL)), (LV.TL_INSTANT_LABEL, get(REFERENCE, TL_ALL, LV.TL_FROM2027)),
                  (TL_REOCCUPATION_FAST, R_fast)):
        ro = R['info']['reoccupation']
        for i, y in enumerate(ref['years']):
            if y >= WINDOW[0]:
                reocc_log.append(dict(run=nm, year=int(y), need=ro['need'][i], gross_after_payback=ro['gross'][i],
                                      released_tl1=ro['released_tl1'][i], released_tl2=ro['released_tl2'][i],
                                      share=ro['share_by_year'][i], reoccupied=ro['reoccupied'][i],
                                      reoccupied_tl1=ro['reoccupied_tl1'][i], reoccupied_tl2=ro['reoccupied_tl2'][i],
                                      release_binds=bool(ro['release_binds'][i]), built=ro['built'][i],
                                      cumulative_released=float(np.sum((ro['released_tl1'] + ro['released_tl2'])[:i + 1])),
                                      cumulative_reoccupied=float(np.sum(ro['reoccupied'][:i + 1]))))
    out = dict(params=params, runs=runs_df, annual=pd.DataFrame(annual), bands=bands_df,
               bands_annual=pd.DataFrame(bands_annual), shapley=pd.DataFrame(shap_rows),
               shapley_subsets=pd.DataFrame(sub_rows), shapley_exact=shap_exact, backcast=backcast_out, space=space,
               lambda_sweep=pd.DataFrame(sweep), waterfall=wf, waterfall_tl_from_reference=wf_tl,
               sequential_vs_shapley=seq_vs_shap,
               lever_annual=pd.DataFrame(lever_annual),
               reoccupation_log=pd.DataFrame(reocc_log), ctxs=ctxs, states=states, cache=cache, get=get,
               tl_levels=TL_ALL, seconds=time.time() - t0)
    out['ordering'] = ordering(out)
    if verbose:
        print(f'pathways: {len(cache)} engine runs in {out["seconds"]:.1f} s')
    return out


def waterfall(ctx, get, setting):
    """The sequential path in PAS 2080 hierarchy order (MODEL v3.3.0): (a) Reference -> +L1 -> ... -> +L9 at `setting`
    (= the Moderate / Ambitious Pathway), (b) -> +TL1 ... +TL9 (= TL); every step a cached run, each step's change
    split exactly into the in-scope demand bands; each step is credited with what remains after the higher-priority
    measures (order-dependent; the order-free values are the Shapley values)."""
    steps = [('REF', N.SCENARIOS['REF'], {})]
    acc = {}
    for L in LV.LEVERS:
        acc[L] = setting
        steps.append((L, f'+ {L} {N.LEVERS[L]}' + (f' (= {N.PATHWAY_RUNS[run_name(LV.PATHWAY, setting)]})'
                                                     if L == LV.LEVERS[-1] else ''), dict(acc)))
    for k in range(1, len(LV.TL_COMPONENTS) + 1):
        t = LV.TL_COMPONENTS[k - 1]
        steps.append((t, f'+ {t} {N.TL[t]}' + (' (= TL)' if k == len(LV.TL_COMPONENTS) else ''),
                      LV.tl_levels(LV.TL_COMPONENTS[:k], setting)))
    return waterfall_rows(ctx, get, setting, steps)


def waterfall_tl_from_reference(ctx, get):
    """MODEL v3.3.1 (Fig5c): the sequential path Reference -> +TL1 -> ... -> +TL9 (= TL), every limit added
    cumulatively from the Reference in PAS 2080 order (the other levers off: levers.tl_levels(.., 'reference')); each
    step a cached run, split exactly into the in-scope demand bands as in waterfall(). The step runs are the prefix
    subsets of the levers_tl Shapley game."""
    steps = [('REF', N.SCENARIOS['REF'], {})]
    for k in range(1, len(LV.TL_COMPONENTS) + 1):
        t = LV.TL_COMPONENTS[k - 1]
        steps.append((t, f'+ {t} {N.TL[t]}' + (' (= TL)' if k == len(LV.TL_COMPONENTS) else ''),
                      LV.tl_levels(LV.TL_COMPONENTS[:k], 'reference')))
    return waterfall_rows(ctx, get, 'tl', steps)


def waterfall_rows(ctx, get, setting, steps):
    """Rows of a sequential waterfall: steps [(step id, label, levels)], each a cached run, its in-scope bands
    checked to add up to its carbon (1e-9)."""
    bar = float(np.sum(ctx['b_ar'])) / M6
    rows, prev = [], None
    for i, (sid, lab, levels) in enumerate(steps):
        R = get(ctx['scenario'], levels)
        b = pd.DataFrame([r_ for r_ in band_rows(ctx, R, sid) if r_['definition'] == 'in_scope']).set_index('band')
        tot_c = float(np.asarray(R['E']['carbon'], float)[1:].sum()) / M6
        if abs(b['carbon_kt'].sum() / tot_c - 1) > 1e-9:
            raise SystemExit(f'STOP: waterfall ({setting}): the bands of step {sid} do not add up to its carbon')
        for band in b.index:
            rows.append(dict(setting=setting, step=i, step_id=sid, label=lab, band=band,
                             gfa_Mm2=float(b.loc[band, 'gfa_Mm2']), carbon_kt=float(b.loc[band, 'carbon_kt']),
                             delta_gfa_Mm2=0.0 if prev is None else float(prev.loc[band, 'gfa_Mm2'] - b.loc[band, 'gfa_Mm2']),
                             delta_carbon_kt=0.0 if prev is None else float(prev.loc[band, 'carbon_kt'] - b.loc[band, 'carbon_kt']),
                             total_carbon_kt=tot_c, LoE_AR=tot_c / bar, B_AR_kt=bar,
                             B_AtP_kt=float(np.sum(ctx['b_atp'])) / M6))
        prev = b
    return pd.DataFrame(rows)


def sequential_vs_shapley(wf, shap):
    """MODEL v3.3.0 diagnostics: per lever (Moderate, Ambitious; from the Reference) and per TL step (from the Moderate
    Pathway), the sequential waterfall step (PAS 2080 order; carbon reduction, kt) against the order-free Shapley
    value of the same player in its game (levers_moderate, levers_ambitious, TL_GAME). The Ambitious waterfall's TL
    steps start from the Ambitious Pathway, which has no Shapley game; their Shapley column is empty."""
    sh = shap[shap['metric'] == 'carbon_kt'].set_index(['game', 'player'])['reduction']
    rows = []
    for setting in LV.SETTINGS:
        g = wf[wf['setting'] == setting].groupby(['step', 'step_id'])['total_carbon_kt'].first().reset_index()
        for i in range(1, len(g)):
            pid = g.loc[i, 'step_id']
            seq = float(g.loc[i - 1, 'total_carbon_kt'] - g.loc[i, 'total_carbon_kt'])
            is_tl = pid in LV.TL_COMPONENTS
            game = (TL_GAME if setting == 'moderate' else None) if is_tl else f'levers_{setting}'
            shv = float(sh.loc[(game, pid)]) if game is not None else float('nan')
            rows.append(dict(setting=setting, part='TL from the Pathway' if is_tl else 'levers from the Reference',
                             player=pid, name=N.TL[pid] if is_tl else N.LEVERS[pid],
                             strategy='' if is_tl else LV.LEVER_STRATEGY[pid], game=game or '',
                             sequential_reduction_kt=seq, shapley_reduction_kt=shv,
                             sequential_minus_shapley_kt=seq - shv if game else float('nan'),
                             order=i))
    return pd.DataFrame(rows)


# ============================================================
# CHECKS (STOP conditions)
# ============================================================
def ordering(res):
    """Reference >= Moderate >= Ambitious >= TL per lever, typology and year, on each lever's native quantity as it
    enters the engine (single-lever runs): L4 dwelling size; L5 OLF; L1 households; L2 vacancy rate; L3 demolition
    and residual rates; L8 A1-A3 per m2; L9 A4-A5 per m2; L7 soil factor; L6 soil-bearing share. Also reported (not a
    STOP): the annual carbon of the single-lever runs by year, and asserted: their cumulative carbon."""
    ref = res['ctxs'][REFERENCE]
    get = res['get']
    years = ref['years']
    typ = ref['typ']
    levels = ('reference', 'moderate', 'ambitious', 'tl')

    def q(L, R):
        fi, info, E = R['inputs'], R['info'], R['E']
        bt = lambda a: np.broadcast_to(np.asarray(a, float), (len(years),))
        if L == 'L4':
            return {t: bt(fi['size'][t]) for t in typ}
        if L == 'L5':
            return {t: bt(fi['olf'][t]) for t in typ}
        if L == 'L1':
            return {'all': np.asarray(info['hh'], float)}
        if L == 'L2':
            return {'all': bt(fi['v'])}
        if L == 'L3':
            return {'demolition': bt(fi['rate_demol']), 'residual': bt(fi['rate_unc'])}
        if L == 'L8':
            return {t: bt(info['a13'][t]) for t in typ}
        if L == 'L9':
            return {t: bt(info['a45'][t]) for t in typ}
        if L == 'L7':
            return {t: bt(fi.get('soil', ref['soil'])[t]) for t in typ}
        if L == 'L6':
            return {'all': np.asarray(E['soil_share'], float)}
    out = dict(violations=[], carbon_year_reversals=[], cumulative=[])
    for L in LV.LEVERS:
        Rs = {s: get(REFERENCE, {} if s == 'reference' else {L: s}) for s in levels}
        Q = {s: q(L, Rs[s]) for s in levels}
        for a, b in zip(levels[:-1], levels[1:]):
            for k in Q[a]:
                x, y = Q[a][k], Q[b][k]
                bad = (y[1:] > x[1:] * (1 + ORDER_RTOL) + 1e-15)
                if L == 'L6':
                    bad = (y[1:] > x[1:] + 1e-12)
                if bad.any():
                    out['violations'].append(dict(lever=L, typology=k, pair=f'{a}>={b}',
                                                  years=[int(v) for v in years[1:][bad]]))
            ca = Rs[a]['E']['carbon'][1:]
            cb = Rs[b]['E']['carbon'][1:]
            rev = cb > ca * (1 + 1e-12)
            if rev.any():
                out['carbon_year_reversals'].append(dict(lever=L, pair=f'{a}>={b}', years=[int(v) for v in years[1:][rev]],
                                                         max_kt=float(np.max((cb - ca)[rev]) / M6)))
            out['cumulative'].append(dict(lever=L, pair=f'{a}>={b}', carbon_a_kt=ca.sum() / M6, carbon_b_kt=cb.sum() / M6,
                                          ok=bool(cb.sum() <= ca.sum() * (1 + 1e-12))))
    return out


def checks(res):
    """Identity of the no-lever run with the published Reference run, and the STOP conditions of MODEL v3.0.0."""
    ctx = res['ctxs'][REFERENCE]
    B = ctx['B']
    R0 = res['get'](REFERENCE, {})
    E0, Eb = R0['E'], B['engine_out']['50th']
    rel = lambda a, b: float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float))
                                    / np.maximum(np.abs(np.asarray(b, float)), 1e-300)))
    rep = {'annual_carbon': rel(E0['carbon'][1:], B['carbon_total_typ'].sum(axis=1).values[1:]),
           'gfa_by_typology': rel(E0['gfa_t'][:, 1:], Eb['gfa_t'][:, 1:]),
           'join': float(np.max(np.abs(E0['join'] - ctx['join_reference'])) / max(np.abs(ctx['join_reference']).max(), 1.0))}
    bres = json.load(open(FILE_BOSS_RESULTS))
    ident = N.identifier
    r0 = res['runs'][(res['runs']['run'] == REFERENCE) & (res['runs']['scenario'] == REFERENCE)].iloc[0]
    for k in ('carbon_kt', 'upfront_kt', 'soil_kt', 'b_inwindow_kt', 'gfa_Mm2'):
        rep[k] = abs(r0[k] / bres[ident(k)] - 1)
    for k in ('lower_kt', 'upper_kt', 'B_lower_kt', 'B_upper_kt', 'C_kt'):
        rep[f'committed_{k}'] = abs(r0[f'committed_{k}'] / bres['committed'][ident(k)] - 1)
    bd = res['bands']
    b0 = bd[(bd['run'] == REFERENCE) & (bd['scenario'] == REFERENCE) & (bd['definition'] == 'in_scope')].set_index('band')
    for x in bres['bands_in_scope']:                   # the same band accounting (bands.py) in both modules
        for col in ('gfa_Mm2', 'carbon_kt'):
            rep[f"band {x['band']} {col}"] = abs(b0.loc[x['band'], col] - x[ident(col)]) / max(abs(x[ident(col)]), 1e-9)
    pbr = json.load(open(FILE_PB_RESULTS))
    for scen in res['ctxs']:
        rs = res['runs'][(res['runs']['run'] == scen) & (res['runs']['scenario'] == scen)].iloc[0]
        for col in ('LoE_AR', 'LoE_AtP'):
            rep[f'{scen} {col}'] = abs(rs[col] / pbr['deterministic'][scen][col] - 1)
    worst = max(rep, key=rep.get)
    if rep[worst] > IDENTITY_RTOL:
        raise SystemExit(f'STOP: identity not reproduced: {worst} relative difference {rep[worst]:.3e}')
    stops = []
    excess_diff = 0.0
    for k, R in res['cache'].items():
        scen = k[0]
        c = res['ctxs'][scen]
        E, info = R['E'], R['info']
        lab = f'{scen} {LV.label(R["levels"])} {R["ramp"]}'
        excess_diff = max(excess_diff, float(np.max(np.abs(info['excess'] - c['excess']))))
        built = np.asarray(engine.requirement(E), float)[1:]
        if (built < -T_ZERO_TOL_DWELLINGS).any() or (E['dwell_in_scope'][1:] < -T_ZERO_TOL_DWELLINGS).any():
            stops.append(f'built_t < 0: {lab}')
        st = stage_arrays(c, R)
        if any((st[s][1:] < -1e-6).any() for s in st) or (E['gfa_t'][:, 1:] < -T_ZERO_TOL_M2).any():
            stops.append(f'negative stage / floor-area value: {lab}')
        if any((np.asarray(info['a13'][t]) < 0).any() or (np.asarray(info['a45'][t]) < 0).any() for t in c['typ']):
            stops.append(f'negative material intensity: {lab}')
        ro = info['reoccupation']
        rel_ = (ro['released_tl1'] + ro['released_tl2'])
        if (np.cumsum(ro['reoccupied']) > np.cumsum(rel_) + REOCCUPATION_TOL * max(ro['R'], 1.0)).any():
            stops.append(f'cumulative re-occupied > released: {lab}')
        if not info['tl']:
            v = implied_vacancy(E)[1:]
            if (v < LV.L2_VACANCY_FLOOR).any():
                stops.append(f'implied vacancy below {LV.L2_VACANCY_FLOOR:.1%}: {lab}')
            if (E['d_hh_raw'][1:] < 0).any():
                stops.append(f'households decline in a non-TL run: {lab}')
        S = E['pop'] / E['hh']
        for t in c['typ']:
            occ = S * np.asarray(R['inputs']['olf'][t], float)
            size = np.broadcast_to(np.asarray(R['inputs']['size'][t], float), S.shape)
            if (size[1:] < occ[1:] * (1 - 1e-12)).any():
                stops.append(f'dwelling size below the occupied area: {lab} ({t})')
        if abs(E['carbon'][1] / E0['carbon'][1] - 1) > 1e-12 and scen == REFERENCE:
            stops.append(f'2026 changed: {lab}')
    if excess_diff != 0.0:
        stops.append(f'the overbuild excess differs between runs (max {excess_diff:.3e} dwellings)')
    for key, (phi, total) in res['shapley_exact'].items():
        if sum(phi.values()) != total:
            stops.append(f'Shapley efficiency fails {key}')
    if res['ordering']['violations']:
        stops.append(f"ordering violated: {res['ordering']['violations'][:5]}")
    if not all(r['ok'] for r in res['ordering']['cumulative']):
        stops.append(f"cumulative carbon ordering violated: {[r for r in res['ordering']['cumulative'] if not r['ok']]}")
    runs = res['runs']
    for scen in res['ctxs']:
        r = runs[runs['scenario'] == scen].set_index('run')
        if not (r.loc['TL', 'carbon_kt'] <= r.loc[run_name(LV.PATHWAY, 'ambitious'), 'carbon_kt']
                <= r.loc[run_name(LV.PATHWAY, 'moderate'), 'carbon_kt']):
            stops.append(f'{scen}: TL <= Ambitious Pathway <= Moderate Pathway violated')
    if stops:
        raise SystemExit('STOP:\n  ' + '\n  '.join(stops[:30]))
    rep['overbuild_excess_max_abs_diff_between_runs'] = excess_diff
    return rep


# ============================================================
# WRITE (data only)
# ============================================================
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


def tl_summary(res):
    """theoretical_limit.json: definition, Level-4 values, re-occupation (R1, R2, G+, binding years), indicators."""
    ref = res['ctxs'][REFERENCE]
    yy = np.asarray(ref['years'])
    out = {}
    for nm, R in (('TL', res['get'](REFERENCE, res['tl_levels'])),
                  (LV.TL_INSTANT_LABEL, res['get'](REFERENCE, res['tl_levels'], LV.TL_FROM2027))):
        ro, E = R['info']['reoccupation'], R['E']
        S = E['pop'] / E['hh']
        out[nm] = dict(
            R1=ro['R1'], R2=ro['R2'], R=ro['R'], G_plus=ro['G_plus'], share_of_need=ro['share'],
            reoccupied=ro['reoccupied_total'], surplus_vacant_2050=ro['surplus_vacant_2050'],
            R_exceeds_G_plus=bool(ro['R'] > ro['G_plus']), release_binding_years=[int(y) for y in yy[ro['release_binds']]],
            nonpositive_need_years=ro['nonpositive_need_years'],
            reoccupied_attributed=dict(TL1=float(ro['reoccupied_tl1'].sum()), TL2=float(ro['reoccupied_tl2'].sum()),
                                       rule='in proportion R1 : R2'),
            household_size_by_year={int(y): float(S[i]) for i, y in enumerate(yy) if y >= 2026},
            mean_new_dwelling_size_m2={int(y): float(E['D'][i]) for i, y in enumerate(yy) if y >= 2026},
            m2_per_person_new_dwellings={int(y): float(E['D'][i] / S[i]) for i, y in enumerate(yy) if y >= 2026},
            implied_vacancy={int(y): float(v) for y, v in zip(yy, implied_vacancy(E)) if y >= 2026},
            dwellings_built={int(y): float(x) for y, x in zip(yy, engine.requirement(E)) if y >= 2026})
    return dict(run_mode=RUN_MODE, disclaimer=LV.TL_DISCLAIMER, bau=LV.TL_BAU_NOTE,
                definition=dict(levels='every lever at Level 4', adoption='normalised logistic 2026 -> 2035 (as every '
                                'level)', sensitivity=f'{LV.TL_INSTANT_LABEL}: every limit at full strength from 2027',
                                components={k: LV.TL_NAMES[k] for k in LV.TL_COMPONENTS},
                                note='TL6 = 100% brownfield makes TL7 zero within TL'),
                strength=res['params']['tl_strength'], runs=out)


def write(res, identity):
    _csv(res['runs'], 'runs.csv')
    _csv(res['annual'], 'annual.csv')
    _csv(res['bands'], 'bands.csv')
    _csv(res['bands_annual'], 'bands_annual.csv')
    _csv(res['shapley'], 'shapley.csv')
    _csv(res['shapley_subsets'], 'shapley_subsets.csv')
    _csv(res['space'], 'solution_space.csv')
    _csv(res['lambda_sweep'], 'lambda_sweep.csv')
    _csv(res['waterfall'], 'waterfall.csv')
    _csv(res['waterfall_tl_from_reference'], 'waterfall_tl_from_reference.csv')
    _csv(res['sequential_vs_shapley'], 'sequential_vs_shapley.csv')
    _csv(res['lever_annual'], 'lever_annual.csv')
    _csv(res['reoccupation_log'], 'reoccupation_log.csv')
    _json(res['backcast'], 'backcast.json')
    _json(res['ordering'], 'ordering_checks.json')
    _json(tl_summary(res), 'theoretical_limit.json')
    _json(dict(res['params'], run_mode=RUN_MODE, identity_max_rel_diff=max(identity.values()),
               identity_checks=identity, sources=LV.SOURCES), 'levers.json')


def main():
    res = compute()
    identity = checks(res)
    print(f'pathways: identity REF (no lever) = the Reference run, max relative difference '
          f'{max(v for k, v in identity.items() if k != "overbuild_excess_max_abs_diff_between_runs"):.2e}; '
          f'overbuild excess identical in every run (max difference {identity["overbuild_excess_max_abs_diff_between_runs"]})')
    write(res, identity)
    r = res['runs']
    show = r[(r['scenario'] == REFERENCE) & (r['adoption'] == RAMP_ADOPTED)]
    print(show[['run', 'gfa_Mm2', 'carbon_kt', 'LoE_AR', 'LoE_AtP', 'delta_carbon_kt_vs_reference_pct']].to_string(index=False))
    return res


if __name__ == '__main__':
    main()
