"""
MONTE CARLO -- joint uncertainty and variance-based sensitivity for Boss.py
===========================================================================
Boss.py gives one central projection plus a population-only band. This script
samples every uncertain input at once, propagates them through the same model,
and reports:
  1. percentiles of the 2026-2050 totals (floor area, carbon, upfront carbon,
     retirement-village units, households and household size in 2050), and an
     annual fan;
  2. first-order and total Sobol indices: the share of output variance each
     input explains alone, and including its interactions (Saltelli et al.
     2010 / Jansen estimators, as implemented in scipy.stats.sobol_indices).

ENGINE
  One full Boss.main() takes about three seconds, too slow for ~25,000 runs.
  Each draw therefore calls only the forward chain, through the SAME pure
  functions Boss.main() uses (engine.py): stock calibration, 2025 deviation,
  replacement path, near-term market excess, forward projection. Everything
  taken from Boss (data series, calibration window, fixed rates, settings) is
  copied once in build_setup(), so later changes to Boss's module settings
  cannot leak into a draw. Before sampling, the central draw is checked against
  Boss.main() year by year (floor area, carbon, upfront carbon, RV units,
  households, household size); the script stops if any differs by more than
  1e-9 (relative).

INPUTS AND DISTRIBUTIONS (each is a stated assumption)
  z_pop     Standard normal. Population = median + the published Stats NZ
            level spread at that quantile (5/25/50/75/95th knots, linear in z,
            linearly extrapolated beyond 5th/95th), comonotone across years:
            one draw is one rank in every year. Household size uses the SAME
            z, interpolating the Stats NZ Low / Medium / High projections
            (placed at z = -1.645 / 0 / +1.645). The variants differ only in
            fertility, mortality and migration, so low population and small
            households come together (older age structure).
  size      Lognormal multiplier on dwelling size (all typologies together),
            sigma = RMS log deviation of annual typology sizes 2016-2025 from
            the adopted 2023-25 reference.
  complete  Two-piece uniform(0.92, 0.95, 0.96): completion rate (Jones et al.
            2024 bounds), median at the adopted 0.95 (a two-piece distribution
            has its median at that value; Wallis 2014). The stock calibration
            and the census dwelling-count replacement rates are redone for
            each draw.
  carbon    A stratified bootstrap of the case studies (resampled within
            sub-type, duplicate cases removed, re-pooled as in
            Building_factors). A sub-type with one independent case (the
            apartments) has no bootstrap spread, so it gets a lognormal
            multiplier with the pooled between-building log-SD of the other
            sub-types.
  CENTRING: the deterministic Boss run uses the MEDIAN of every sampled input.
  Inputs are independent. Seeds are fixed, so runs are reproducible.
NOT SAMPLED (held at the Boss value in every draw)
  net replacement: the MC is run separately within each scenario of
    MC_SCENARIOS (S3 half-life 10 = reference, S1 and S2); the half-life is
    fixed. Scenario differences are reported separately (Sensitivity.py).
  typology mix, the census rebase of households, the pre-2013 empty share,
    future vacancy and the retirement-village share: their total Sobol indices
    were about 0 in a full-input run (v1.0.2), so they are fixed (v1.1 lean MC).
  demolition rate: it trades one-for-one with the calibrated residual and
    cannot move the total.
  near-term market excess: recomputed in every draw with that draw's completion
    rate and scenario path; the observed consents and population are data.
  soil order: the area-weighted mean is used; the soil-order extremes are a
    bounding scenario (Sensitivity.py), not a probability.
"""

import contextlib
import importlib
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.interpolate import PchipInterpolator
from scipy.stats import qmc

import Boss
import engine

N_UNCERTAINTY = 5000             # Latin hypercube draws per scenario
N_SOBOL = 1024                   # base sample; evaluations = N_SOBOL * (d + 2)
N_BOOT = 4000                    # carbon-factor bootstrap replicates
SEED = 20260924
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'   # set by run_all.py: write PNGs to FIG_DIR
SHOW_FIGURES = not (os.environ.get('PATHWAY_SAVE_FIGURES') == '1')
# PLOT_ONLY: skip the ~15,000 model evaluations and redraw the figures from the
# CSVs written by the last full run. Also: python MonteCarlo.py --plot-only
PLOT_ONLY = False
OUT_DIR = Boss.OUT_DIR
FIG_DIR = os.path.join(Boss.OUT_DIR, 'figures')
Z_KNOTS = stats.norm.ppf([0.05, 0.25, 0.50, 0.75, 0.95])
PCT_COLS = {5: 2, 25: 3, 50: 4, 75: 5, 95: 6}   # popdata.xlsx Table 1 (skiprows=5)
VARIANT_Z = {'Low': Z_KNOTS[0], 'Medium': 0.0, 'High': Z_KNOTS[-1]}


# ============================================================
# SET-UP: everything that does not change between draws
# ============================================================
def load_level_percentiles():
    """Published population LEVEL percentiles (5, 25, 50, 75, 95th), persons."""
    raw = pd.read_excel(Boss.FILE_POP_PROJ, sheet_name=Boss.POP_SHEET_PROJ, skiprows=5)
    lab = raw.iloc[:, 0].astype(str)
    start = lab.index[lab.str.contains('Population (000)', regex=False)][0]
    rows = []
    for i in range(start + 1, len(raw)):
        yr = pd.to_numeric(pd.Series(lab[i]).str.extract(r'(\d{4})')[0], errors='coerce').iloc[0]
        if pd.isna(yr):
            break
        rows.append([int(yr)] + [float(raw.iat[i, c]) * 1000 for c in PCT_COLS.values()])
    return pd.DataFrame(rows, columns=['Year'] + list(PCT_COLS)).set_index('Year')


def build_setup(settings=None):
    """Snapshot of one Boss run. settings: Boss module settings for this run
    (the module is reloaded first, so nothing leaks between scenarios)."""
    if settings is not None:
        importlib.reload(Boss)
        for k, v in settings.items():
            if not hasattr(Boss, k):
                raise AttributeError(f"Boss has no setting '{k}'.")
            setattr(Boss, k, v)
    Boss.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        B = Boss.main()
    fy = B['forecast_years']
    typ = list(B['typ_names'])
    su = dict(B=B, fy=fy, typ=typ)

    # ---- population: spread around the median, per knot percentile ----
    lv = load_level_percentiles()
    spreads = []
    for p in PCT_COLS:
        f = PchipInterpolator(lv.index.values.astype(float), (lv[p] - lv[50]).values)
        sp = f(fy.astype(float))
        spreads.append(sp - sp[0])                       # all paths start at observed 2025
    su['pop50'] = B['df_forecast']['PopTotal_50th'].values
    su['spreads'] = np.array(spreads)                    # (5, years)

    # ---- household size: Stats NZ shape per variant, rebased on the census anchor ----
    su['S_variants'] = np.array([
        Boss.household_size(*Boss.statsnz_size_shape(v, fy, tail=Boss.S_TAIL)[1:], B['hist_S'], B['hist_pop'],
                            fy, 0.0, anchor_year=Boss.S_ANCHOR_YEAR)['S_matched']
        for v in VARIANT_Z])

    # ---- typology mix (fixed in every draw): Boss's storyline mix ----
    if B['mix_used'] == 'held':
        shares = B['evolving_gfa_shares'].copy()
    else:
        alr_2025, alr_slope = Boss.mix_trend(B['hist_shares'], B['shares_2025'], Boss.TREND_WINDOW_START, typ)
        shares = engine.mix_shares(alr_2025, alr_slope, Boss.DAMPING_PHI, fy, typ)
    if B['gfa_nowcast']:                          # 2026 = observed consented mix
        shares.loc[2026] = B['evolving_gfa_shares'].loc[2026].values
    su['shares'] = shares

    # ---- snapshot of Boss's data and settings used in every draw ----
    su.update(years_hist=B['years_hist'], hist_hh=B['hist_hh'],
              knots=engine.vacancy_knots(B['census'], float(B['empty_share_measured'])),
              units_all=B['hist_units_all_c'], rv_units=B['hist_rv_units_c'],
              calib_start=Boss.DEMOLITION_CALIB_START, calib_end=B['calib_end'], demol_rate=Boss.DEMOLITION_RATE,
              completion=Boss.COMPLETION_RATE, olf=dict(B['OLF_USED']), rv_share=float(B['rv_share']),
              nr_window=tuple(Boss.NET_REPLACEMENT_WINDOW),
              census_stock=B['census']['total_private'], consents_monthly=B['consents_monthly'],
              lag_w=B['lag_w'], census_uc=B['census_uc'],
              # replacement scenario and near-term market excess, as in the Boss run
              scenario=B['_scenario'], s3_half_life=Boss.S3_HALF_LIFE,
              recent=tuple(Boss.RECENT_INTERVAL), join_mode=B['_join_mode'],
              nowcast=B['nowcast'], units_all_raw=B['hist_units_all'],
              near_gap_ref=Boss.NEAR_TERM_GAP_REF, near_mode=Boss.NEAR_TERM_MODE,
              near_absorption=Boss.NEAR_TERM_ABSORPTION,
              # observed 2026 floor area (fixed in every draw)
              gfa_2026=(B['gfa_nowcast']['total'] if B['gfa_nowcast'] else None))

    # ---- dwelling size ----
    su['size_ref'] = np.array([B['size_ref'][t] for t in typ])
    dev = [np.log(B['hist_dwelling_size'][t].loc[2016:2025] / B['size_ref'][t]) for t in typ]
    su['size_sigma'] = float(np.sqrt(np.mean(np.concatenate([d.values for d in dev]) ** 2)))

    # ---- carbon factors ----
    tf = pd.read_csv(Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]
    bf = pd.read_csv(Boss.FILE_FACTORS_BUILDING)
    su['soc'] = tf['SOC_avg'].values
    su['soil_on_repl'] = Boss.SOIL_ON_REPLACEMENT
    su['emb_central'] = tf['embodied_materials'].values
    mf = pd.read_csv(Boss.FILE_FACTORS_MATERIAL)
    up = (mf[mf['Stage'].isin(['A1-A3', 'A4-A5'])].groupby('Typology')['kgCO2e_per_m2'].sum())
    su['up_central'] = up.reindex(typ).values
    su['boot_emb'], su['boot_up'], su['between_sigma'] = carbon_bootstrap(bf, typ)
    return su


def carbon_bootstrap(bf, typ):
    """Stratified bootstrap of pooled typology factors (materials, in scope)."""
    rng = np.random.default_rng(SEED + 1)
    bf = bf[bf['duplicate_of'].fillna('') == ''].copy()
    bf['emb'] = bf[Boss.STAGES_IN_SCOPE].sum(axis=1)
    bf['up'] = bf[['A1-A3', 'A4-A5']].sum(axis=1)
    # pooled between-building log-SD within sub-types that have >= 2 cases
    logs = [np.log(g['emb']) - np.log(g['emb']).mean()
            for _, g in bf.groupby('Subtype') if len(g) >= 2]
    dof = sum(len(l) - 1 for l in logs)
    sigma = float(np.sqrt(sum((l ** 2).sum() for l in logs) / dof))
    emb = np.empty((N_BOOT, len(typ)))
    upf = np.empty((N_BOOT, len(typ)))
    for j, t in enumerate(typ):
        subs = [g for _, g in bf[bf['Typology'] == t].groupby('Subtype')]
        e_sub, u_sub = [], []
        for g in subs:
            idx = rng.integers(0, len(g), size=(N_BOOT, len(g)))
            e, u = g['emb'].values[idx].mean(axis=1), g['up'].values[idx].mean(axis=1)
            if len(g) == 1:                          # no spread: borrow it
                k = np.exp(rng.normal(-sigma ** 2 / 2, sigma, N_BOOT))   # mean-preserving
                e, u = e * k, u * k
            e_sub.append(e); u_sub.append(u)
        emb[:, j] = np.mean(e_sub, axis=0)
        upf[:, j] = np.mean(u_sub, axis=0)
    return emb, upf, sigma


# ============================================================
# ENGINE
# ============================================================
PARAMS = ['z_pop', 'size', 'complete', 'carbon']
# Net replacement is NOT sampled: the MC runs separately within each scenario
# (MC_SCENARIOS); the S3 half-life is fixed. The first entry is the reference
# path (its files keep the plain names and carry the Sobol indices and figures).
MC_SCENARIOS = [('S3-10', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=10.0)),
                ('S1', dict(REPLACEMENT_SCENARIO='S1')),
                ('S2', dict(REPLACEMENT_SCENARIO='S2'))]   # S2 = storyline (mix trend), not 'high'


class TwoPiece:
    """Two-piece (split) distribution with its MEDIAN at m: probability 1/2
    on [lo, m] and 1/2 on [m, hi] (the two-piece family; Wallis 2014, Statistical
    Science 29(1)). Each half is a triangle peaking at m ('triangular', so the
    mode is also m) or flat ('uniform'). Used where the deterministic value is
    not the median of a one-piece distribution over the stated range, so that
    the deterministic run sits at the input medians (D3)."""

    def __init__(self, lo, m, hi, shape='triangular'):
        if not lo <= m <= hi:
            raise ValueError(f'TwoPiece needs lo <= m <= hi, got {lo}, {m}, {hi}.')
        self.lo, self.m, self.hi, self.shape = float(lo), float(m), float(hi), shape

    def ppf(self, u):
        u = np.asarray(u, float)
        lo, m, hi = self.lo, self.m, self.hi
        if self.shape == 'triangular':
            left = lo + (m - lo) * np.sqrt(np.clip(2 * u, 0, 1))
            right = hi - (hi - m) * np.sqrt(np.clip(2 * (1 - u), 0, 1))
        else:
            left = lo + (m - lo) * np.clip(2 * u, 0, 1)
            right = m + (hi - m) * np.clip(2 * u - 1, 0, 1)
        return np.where(u < 0.5, left, right)


def central(su):
    return dict(z_pop=0.0, size=1.0, complete=su['completion'], carbon=None)


def interp_z(z, zs, ys):
    """Linear in z through (zs, ys) along axis 0, extrapolated linearly."""
    if z <= zs[0]:
        k = 0
    elif z >= zs[-1]:
        k = len(zs) - 2
    else:
        k = int(np.searchsorted(zs, z)) - 1
    w = (z - zs[k]) / (zs[k + 1] - zs[k])
    return ys[k] + w * (ys[k + 1] - ys[k])


def project(su, p):
    """One draw through the shared engine. Reads only su (a snapshot) and p;
    inputs not in p are held at their central values."""
    p = {**central(su), **p}
    fy, typ, yh = su['fy'], su['typ'], su['years_hist']
    # ---- population and household size (same rank z) ----
    pop = su['pop50'] + interp_z(p['z_pop'], Z_KNOTS, su['spreads'])
    S = interp_z(p['z_pop'], np.array(list(VARIANT_Z.values())), su['S_variants'])
    hh = pop / S

    # ---- stock: recalibrated for this draw's completion rate ----
    c = p['complete']
    cal = engine.calibrate_stock(yh, su['hist_hh'], su['knots'], su['units_all'], su['rv_units'], c,
                                 su['demol_rate'], su['calib_start'], su['calib_end'])
    # census dwelling-count identity, recomputed for this draw's completion rate
    rates = engine.census_interval_rates(su['census_stock'], su['consents_monthly'], c, su['lag_w'],
                                         uc=su['census_uc'])
    unc_long = engine.census_window_rate(rates, *su['nr_window']) - su['demol_rate']
    unc_recent = engine.census_window_rate(rates, *su['recent']) - su['demol_rate']
    unc = engine.replacement_path(su['scenario'], unc_long, unc_recent, fy, su['s3_half_life'])
    dv = engine.deviation_2025(cal, c * su['units_all'].loc[2025],
                               float(su['hist_hh'].loc[2025] - su['hist_hh'].loc[2024]),
                               su['demol_rate'] + float(unc[0]), yh, su['calib_start'], su['calib_end'])
    dev = dv['dev'] if su['join_mode'] == 'carried_deviation' else 0.0
    v = float(cal['knots'][max(cal['knots'])])        # latest census vacancy, held

    # ---- typology mix (fixed) and dwelling size ----
    shares = su['shares']
    size = {t: su['size_ref'][j] * p['size'] for j, t in enumerate(typ)}

    # ---- carbon factors ----
    if p['carbon'] is None:
        emb, upf = su['emb_central'], su['up_central']
    else:
        kc = min(int(p['carbon'] * N_BOOT), N_BOOT - 1)
        emb, upf = su['boot_emb'][kc], su['boot_up'][kc]
    I = {t: emb[j] + su['soc'][j] for j, t in enumerate(typ)}
    U = {t: upf[j] + su['soc'][j] for j, t in enumerate(typ)}

    fwd = lambda join=None, redev=None: engine.forward(
        pop, hh, np.insert(np.diff(pop), 0, 0).clip(min=0), v, su['demol_rate'], unc,
        dev, dv['rho'], su['rv_share'], shares, size, su['olf'], I, U,
        join=join, join_redev=redev, soil={t: su['soc'][j] for j, t in enumerate(typ)},
        gfa_fixed=({1: su['gfa_2026']} if su['gfa_2026'] is not None else None),
        soil_on_replacement=su['soil_on_repl'])
    E = fwd()
    if su['join_mode'] == 'market_excess':
        b26 = c * ((1.0 - su['lag_w']) * float(su['nowcast']['total'])
                   + su['lag_w'] * float(su['units_all_raw'].loc[2025]))
        join, ji = engine.market_excess(E, b26, dv['rho'], su['near_gap_ref'], su['near_mode'],
                                        su['near_absorption'])
        E = fwd(join, ji['redev'])
    return dict(gfa=E['total'], carbon=E['carbon'], upfront=E['upfront'], rv_units=E['rv_units'],
                townhouse_2050=float(shares[typ[1]].iloc[-1]),
                hh=hh, S=S, extra_clip=E['extra_clip'], gfa_t=E['gfa_t'],
                I=np.array([I[t] for t in typ]), U=np.array([U[t] for t in typ]))


def summarise(out):
    s = slice(1, None)                                     # 2026-2050
    return np.array([out['gfa'][s].sum() / 1e6, out['carbon'][s].sum() / 1e6,
                     out['upfront'][s].sum() / 1e6, out['rv_units'][s].sum(),
                     out['hh'][-1] / 1e6, out['S'][-1], out['townhouse_2050']])


OUTPUTS = ['GFA_Mm2', 'carbon_kt', 'upfront_kt', 'RV_units', 'households_2050_M', 'S_2050',
           'townhouse_share_2050']


def validate(su):
    """The engine at central values must reproduce Boss.main() exactly."""
    B = su['B']
    o = project(su, central(su))
    R = B['results']['50th']
    typ = su['typ']
    up_int = {t: B['UPFRONT_2025'][t] for t in typ}
    ref = dict(gfa=R['total'], carbon=B['carbon_total_typ'].sum(axis=1).values,
               upfront=(sum(B['evol_typ_total'][t].values * (up_int[t] - B['SOIL_INTENSITY'][t]) for t in typ)
                        + np.insert(B['flow_annual']['SOIL'].values, 0, 0.0)),
               rv_units=-B['stock_fwd']['50th']['rv'], hh=B['households_forecast']['50th'],
               S=B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th'])
    worst = 0.0
    for k, r in ref.items():
        rel = np.abs(o[k][1:] - r[1:]) / np.maximum(np.abs(r[1:]), 1e-9)
        worst = max(worst, float(rel.max()))
    print(f"[check] MC draw vs Boss.main(), central values, 2026-2050, floor area, carbon, "
          f"upfront, RV units, households, S: max relative difference {worst:.1e} "
          f"({'OK' if worst < 1e-9 else 'FAIL'})")
    if worst >= 1e-9:
        sys.exit("Engine does not reproduce Boss.main(); results would not be valid.")


# ============================================================
# DISTRIBUTIONS
# ============================================================
def distributions(su):
    return {
        'z_pop': stats.norm(0, 1),
        'size': stats.lognorm(s=su['size_sigma'], scale=1.0),
        'complete': TwoPiece(Boss.COMPLETION_RATE_BAND[0], su['completion'], Boss.COMPLETION_RATE_BAND[1],
                             shape='uniform'),
        'carbon': stats.uniform(0, 1),
    }


def evaluate(su, X):
    """X: (d, n) in natural units -> (outputs, n)."""
    out = np.empty((len(OUTPUTS), X.shape[1]))
    for j in range(X.shape[1]):
        p = dict(zip(PARAMS, X[:, j]))
        out[:, j] = summarise(project(su, p))
    return out


# ============================================================
# MAIN
# ============================================================
def run_scenario(name, settings, reference):
    """Joint uncertainty within one net-replacement scenario. Every scenario
    uses the same seed (common random numbers), so differences between
    scenarios are not sampling noise. The reference scenario also gets the
    Sobol indices and keeps the plain file names read by figures() and metrics."""
    su = build_setup(settings)
    validate(su)
    dists = distributions(su)
    if reference:
        print("\nINPUT DISTRIBUTIONS (5th / 50th / 95th; the deterministic run uses the medians)")
        for k in PARAMS:
            q = np.atleast_1d(dists[k].ppf(np.array([0.05, 0.5, 0.95])))
            print(f"   {k:<10} {q[0]:>12.5g} {q[1]:>12.5g} {q[2]:>12.5g}")
        print(f"   carbon-factor bootstrap: {N_BOOT} replicates; between-building log-SD "
              f"{su['between_sigma']:.3f} used for single-case sub-types")

    lhs = qmc.LatinHypercube(d=len(PARAMS), seed=SEED).random(N_UNCERTAINTY)
    X = np.array([dists[k].ppf(lhs[:, i]) for i, k in enumerate(PARAMS)])
    Y = np.empty((len(OUTPUTS), N_UNCERTAINTY))
    fan = {k: np.empty((N_UNCERTAINTY, len(su['fy']))) for k in ('gfa', 'carbon')}
    for j in range(N_UNCERTAINTY):
        o = project(su, dict(zip(PARAMS, X[:, j])))
        Y[:, j] = summarise(o)
        fan['gfa'][j], fan['carbon'][j] = o['gfa'], o['carbon']
    cen = summarise(project(su, central(su)))
    q = np.percentile(Y, [5, 25, 50, 75, 95], axis=1)
    summ = pd.DataFrame(q.T, index=OUTPUTS, columns=['p5', 'p25', 'p50', 'p75', 'p95'])
    summ['mean'] = Y.mean(axis=1)
    summ['central'] = cen
    summ['central_pct'] = [100 * float((Y[i] < cen[i]).mean()) for i in range(len(OUTPUTS))]
    os.makedirs(OUT_DIR, exist_ok=True)
    draws = pd.DataFrame(np.vstack([X, Y]).T, columns=PARAMS + OUTPUTS)
    annual = pd.DataFrame({f'{k}_{p}': np.percentile(fan[k], p, axis=0)
                           for k in fan for p in (5, 25, 50, 75, 95)}, index=su['fy'])
    names = [f'_{name}'] + ([''] if reference else [])
    for sfx in names:
        summ.to_csv(os.path.join(OUT_DIR, f'montecarlo_summary{sfx}.csv'))
        draws.to_csv(os.path.join(OUT_DIR, f'montecarlo_draws{sfx}.csv'), index=False)
        annual.to_csv(os.path.join(OUT_DIR, f'montecarlo_annual{sfx}.csv'))
    print(f"\nJOINT UNCERTAINTY within {name}, 2026-2050 ({N_UNCERTAINTY:,} Latin hypercube draws)")
    print(summ.loc[['GFA_Mm2', 'carbon_kt', 'upfront_kt', 'townhouse_share_2050'],
                   ['mean', 'p5', 'p50', 'p95', 'central', 'central_pct']].round(3).to_string())
    if not reference:
        return summ

    # ---- Sobol indices (reference scenario) ----
    rng = np.random.default_rng(SEED + 2)
    res = stats.sobol_indices(func=lambda x: evaluate(su, x), n=N_SOBOL,
                              dists=[dists[k] for k in PARAMS], rng=rng)
    with np.errstate(all='ignore'), __import__('warnings').catch_warnings():
        __import__('warnings').simplefilter('ignore')    # BCa is undefined for zero-variance rows
        # SobolResult.bootstrap() takes no rng argument (scipy 1.17), and
        # scipy.stats.bootstrap then draws from numpy's global generator, so
        # the confidence intervals are reproducible only if that is seeded.
        np.random.seed(SEED + 3)
        boot = res.bootstrap(confidence_level=0.95, n_resamples=999)
    rows = []
    for o, oname in enumerate(OUTPUTS):
        for i, k in enumerate(PARAMS):
            rows.append(dict(output=oname, input=k,
                             S1=res.first_order[o, i], S1_lo=boot.first_order.confidence_interval.low[o, i],
                             S1_hi=boot.first_order.confidence_interval.high[o, i],
                             ST=res.total_order[o, i], ST_lo=boot.total_order.confidence_interval.low[o, i],
                             ST_hi=boot.total_order.confidence_interval.high[o, i]))
    sob = pd.DataFrame(rows)
    sob.to_csv(os.path.join(OUT_DIR, 'montecarlo_sobol.csv'), index=False)
    print(f"\nSOBOL INDICES, {name} ({N_SOBOL * (len(PARAMS) + 2):,} evaluations; 95% bootstrap CI)")
    for oname in ['GFA_Mm2', 'carbon_kt']:
        t = sob[sob.output == oname].sort_values('ST', ascending=False)
        print(f"   {oname}")
        for r in t.itertuples():
            if not np.isfinite(r.ST_lo):             # input cannot affect this output
                print(f"     {r.input:<10} n/a (does not enter this output)")
                continue
            print(f"     {r.input:<10} S1 {r.S1:6.3f} [{r.S1_lo:6.3f}, {r.S1_hi:6.3f}]   "
                  f"ST {r.ST:6.3f} [{r.ST_lo:6.3f}, {r.ST_hi:6.3f}]")
    print("   S1: variance explained by the input alone. ST: including interactions.")
    return summ


def main():
    t0 = time.time()
    for i, (name, settings) in enumerate(MC_SCENARIOS):
        run_scenario(name, settings, reference=(i == 0))
    importlib.reload(Boss)                       # restore module defaults
    print(f"\nWritten: montecarlo_summary[_<scenario>].csv, montecarlo_draws[_<scenario>].csv, "
          f"montecarlo_annual[_<scenario>].csv, montecarlo_sobol.csv in {OUT_DIR}/  "
          f"({time.time() - t0:,.0f} s)")
    figures()


# ============================================================
# FIGURES  (drawn from the CSVs, so PLOT_ONLY needs no re-run)
# ============================================================
INPUT_LABELS = {
    'z_pop': 'Population (with household size)',
    'size': 'Future dwelling size',
    'complete': 'Completion rate',
    'carbon': 'Carbon factors (case-study bootstrap)',
}
OUTPUT_LABELS = {
    'GFA_Mm2': ('Built floor area, 2026-2050', 'Mm²', 1),
    'carbon_kt': ('Embodied carbon, 2026-2050', 'kt CO₂e', 1),
}
BLUE = '#2E6DB4'


def _load_results():
    rd = lambda f: os.path.join(OUT_DIR, f)
    need = ['montecarlo_draws.csv', 'montecarlo_annual.csv', 'montecarlo_sobol.csv',
            'montecarlo_summary.csv']
    miss = [f for f in need if not os.path.exists(rd(f))]
    if miss:
        raise FileNotFoundError(f"Missing {miss} in {OUT_DIR}: run a full Monte Carlo first.")
    return (pd.read_csv(rd('montecarlo_draws.csv')),
            pd.read_csv(rd('montecarlo_annual.csv'), index_col=0),
            pd.read_csv(rd('montecarlo_sobol.csv')),
            pd.read_csv(rd('montecarlo_summary.csv'), index_col=0))


def _history():
    """Observed history on the model's built basis, from one silent Boss run."""
    Boss.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        st = Boss.main()
    typ = st['typ_names']
    gfa = st['hist_built_gfa']
    carbon = sum(st['hist_built_typ_gfa'][t] * st['T_BASELINE_2025'][t] for t in typ)
    fy = np.asarray(st['forecast_years'])
    central = {'gfa': pd.Series(st['results']['50th']['total'], index=fy),
               'carbon': st['carbon_total_typ'].sum(axis=1)}
    return gfa, carbon, central


def _save(fig, name):
    if SAVE_FIGURES:
        os.makedirs(FIG_DIR, exist_ok=True)
        fig.savefig(os.path.join(FIG_DIR, name), dpi=140, bbox_inches='tight')


def figures():
    draws, annual, sob, summ = _load_results()
    hist_gfa, hist_c, central = _history()
    yrs = annual.index.values
    fy = yrs[yrs >= 2026]
    has_q = 'gfa_25' in annual.columns

    # ---- 1. joint uncertainty over time ----------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.2))
    fig.suptitle('Monte Carlo 1: joint uncertainty over time '
                 f'({len(draws):,} Latin hypercube draws)', fontsize=12)
    for a, k, hist, lab in [(ax[0], 'gfa', hist_gfa, 'Mm² per year'),
                            (ax[1], 'carbon', hist_c, 'kt CO₂e per year')]:
        hy = hist.index[hist.index >= 1991]
        a.plot(hy, hist.loc[hy] / 1e6, color='black', lw=2, label='observed (built basis)')
        f = annual.loc[fy]
        a.fill_between(fy, f[f'{k}_5'] / 1e6, f[f'{k}_95'] / 1e6, color=BLUE, alpha=0.15,
                       label='5th-95th percentile')
        if has_q:
            a.fill_between(fy, f[f'{k}_25'] / 1e6, f[f'{k}_75'] / 1e6, color=BLUE, alpha=0.30,
                           label='25th-75th percentile')
        a.plot(fy, f[f'{k}_50'] / 1e6, color=BLUE, lw=2.2, label='Monte Carlo median')
        a.plot(fy, central[k].loc[fy] / 1e6, color='#C0392B', lw=1.5, ls='--',
               label='Boss central run')
        a.axvline(2025.5, color='grey', ls=':', lw=1)
        a.set_ylabel(lab); a.set_xlim(1991, 2050); a.set_ylim(0, None)
        a.grid(alpha=0.3); a.legend(fontsize=8, loc='upper right')
    ax[0].set_title('Built floor area (in scope)')
    ax[1].set_title('Embodied carbon (history estimated with 2025 factors)')
    fig.tight_layout()
    _save(fig, 'mc_1_fan.png')

    # ---- 3. what drives the uncertainty (Sobol) ----------------------------
    fig, ax = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle('Monte Carlo 3: what drives the uncertainty (Sobol indices, 95% CI)',
                 fontsize=12)
    for a, o in zip(ax, ['carbon_kt', 'GFA_Mm2']):
        t = sob[(sob.output == o) & np.isfinite(sob.ST_lo)].sort_values('ST')
        y = np.arange(len(t))
        a.barh(y + 0.2, t.ST, 0.4, color='#E67E22',
               xerr=[t.ST - t.ST_lo, t.ST_hi - t.ST], ecolor='#7f4a13', capsize=2,
               label='total effect (incl. interactions)')
        a.barh(y - 0.2, t.S1.clip(lower=0), 0.4, color='#27AE60',
               label='effect on its own')
        for yi, v in zip(y, t.ST):
            a.text(v + 0.012, yi + 0.2, f'{v:.2f}', va='center', fontsize=8)
        a.set_yticks(y)
        a.set_yticklabels([INPUT_LABELS.get(i, i) for i in t.input], fontsize=8.5)
        a.set_xlim(0, max(0.7, t.ST_hi.max() + 0.08))
        a.set_xlabel('share of output variance')
        a.set_title(OUTPUT_LABELS[o][0]); a.grid(alpha=0.3, axis='x')
        a.legend(fontsize=8, loc='lower right')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.text(0.5, 0.01, 'Within-scenario parametric uncertainty only; replacement scenario, typology mix, '
             'carbon-factor and soil bounds are reported separately (sens_1).',
             ha='center', fontsize=9, style='italic')
    _save(fig, 'mc_3_sobol.png')

    if SAVE_FIGURES:
        print(f"Figures written to {FIG_DIR}/ (mc_1, mc_3)")
    if SHOW_FIGURES:
        plt.show()


if __name__ == '__main__':
    if PLOT_ONLY or '--plot-only' in sys.argv:
        figures()
    else:
        main()
