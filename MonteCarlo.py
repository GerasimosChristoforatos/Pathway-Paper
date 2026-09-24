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
  One full Boss.main() takes about two seconds, too slow for ~15,000 runs. The
  forward projection is therefore re-evaluated here from Boss's own functions
  and calibrated quantities (household-size path, stock calibration, typology
  mix, dwelling-size blend). Before any sampling, the engine is run at the
  central values and checked against Boss.main() year by year; the script stops
  if floor area, carbon or retirement-village units differ by more than 1e-9
  (relative). Total floor area is (in-scope dwellings) x (dwelling size): the
  demand bands are an accounting split of that total and are not needed here.

INPUTS AND DISTRIBUTIONS (each is a stated assumption)
  z_pop     Standard normal. Population = median + the published Stats NZ
            level spread at that quantile (5/25/50/75/95th knots, linear in z,
            linearly extrapolated beyond 5th/95th), comonotone across years:
            one draw is one rank in every year. Household size uses the SAME
            z, interpolating the Stats NZ Low / Medium / High projections
            (placed at z = -1.645 / 0 / +1.645). The variants differ only in
            fertility, mortality and migration, so low population and small
            households come together (older age structure).
  b, rho    Only when Boss.HH_SIZE_RESPONSE (a sensitivity; off by default,
            because the 2025 deviation is a DHE estimation artefact):
            Normal(b_hat, Newey-West SE) and Normal(rho_hat, sqrt((1-rho^2)/n))
            truncated to [0, 0.95].
  hh_rebase Triangular(k_occupied, k_occupied+away, 1): the factor on post-2018
            DHE household increments. The low end rebases on census occupied
            dwellings, the mode (Boss's choice) adds residents-away households,
            and 1 is the DHE series as published (i.e. the 2023 census
            undercounted households relative to 2018). The stock calibration
            is redone with each draw's households.
  regime    Uniform(0, 1): weight on the 2019-2023 census interval's net
            replacement rate (+0.36%/yr of stock) against the whole
            census-benchmarked window 1992-2023 (+0.15%/yr). It reads "how much
            of the recent redevelopment regime persists". The census dwelling
            counts show the same 2018-2023 rise with no household data.
  phi       Triangular(0.62, 0.80, 0.98): mix-trend damping. The width is the
            conventional damped-trend range [0.80, 0.98] (Hyndman &
            Athanasopoulos), centred on the adopted 0.80.
  slope_T,  Normal(0, Newey-West SE) added to each ALR mix slope (Townhouses,
  slope_A   Apartments vs Detached), independent of each other.
  size      Lognormal multiplier on dwelling size (all typologies together),
            sigma = RMS log deviation of annual typology sizes 2016-2025 from
            the adopted 2023-25 reference.
  complete  Uniform(0.92, 0.96): completion rate (Jones et al. 2024 bounds).
            The whole stock calibration is redone for each draw.
  pre_share Uniform(+/-0.05) around the measured 2013 empty share applied to
            pre-2013 censuses. The calibration is redone.
  vacancy   Triangular(min, 2023, max) of the measured empty-vacancy censuses
            (2013, 2018, 2023). It is reached linearly by 2050, and the
            vacancy-change term builds the difference.
  rv_share  Triangular(min, central, max) of the annual retirement-village
            share since 2011, around the 2016-2025 ratio of sums.
  carbon    A stratified bootstrap of the case studies (resampled within
            sub-type, duplicate cases removed, re-pooled as in
            Building_factors). A sub-type with one independent case (the
            apartments) has no bootstrap spread, so it gets a lognormal
            multiplier with the pooled between-building log-SD of the other
            sub-types.
NOT SAMPLED
  demolition rate: it trades one-for-one with the calibrated residual and
    cannot move the total.
  soil order: the area-weighted mean is used in the Monte Carlo; the soil-order
    extremes are a bounding scenario (Sensitivity.py), not a probability.
All other inputs are independent. Seeds are fixed, so runs are reproducible.
"""

import contextlib
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import matplotlib
from scipy import stats
from scipy.interpolate import PchipInterpolator
from scipy.stats import qmc

import Boss

N_UNCERTAINTY = 10000            # Latin hypercube draws for the percentiles
N_SOBOL = 1024                   # base sample; evaluations = N_SOBOL * (d + 2)
N_BOOT = 4000                    # carbon-factor bootstrap replicates
SEED = 20260924
PHI_RANGE = (0.62, 0.98)         # triangular, mode = Boss.DAMPING_PHI
SAVE_FIGURES = True
OUT_DIR = Boss.DATA_DIR
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


def build_setup():
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

    # ---- household size: Stats NZ shape per variant ----
    su['size_shape'] = {v: Boss.statsnz_size_shape(v, fy)[1:] for v in VARIANT_Z}
    hr = B['hh_response']
    su['b_hat'], su['b_se'] = hr['b'], hr['se_hac']
    su['rho_hat'] = hr['rho']
    su['rho_se'] = float(np.sqrt((1 - hr['rho'] ** 2) / hr['n_fit']))

    # ---- typology mix: ALR slopes and their HAC standard errors ----
    hs = B['hist_shares']
    win = hs.loc[hs.index >= Boss.TREND_WINDOW_START]
    yrs = win.index.values.astype(float)
    X = np.c_[np.ones(len(yrs)), yrs]
    su['alr_slope'], su['alr_se'] = {}, {}
    for n in typ[1:]:
        y = np.log(win[n] / win[typ[0]]).values
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        cov, _ = Boss.newey_west_cov(X, y - X @ beta)
        su['alr_slope'][n], su['alr_se'][n] = float(beta[1]), float(np.sqrt(cov[1, 1]))
    su['alr_2025'] = {n: float(np.log(B['shares_2025'][n] / B['shares_2025'][typ[0]])) for n in typ[1:]}

    # ---- dwelling size ----
    su['size_ref'] = np.array([B['size_ref'][t] for t in typ])
    dev = [np.log(B['hist_dwelling_size'][t].loc[2016:2025] / B['size_ref'][t]) for t in typ]
    su['size_sigma'] = float(np.sqrt(np.mean(np.concatenate([d.values for d in dev]) ** 2)))

    # ---- stock ----
    su['v_2023'] = float(B['v_forward'])
    cen = B['census']
    measured = cen.loc[cen['empty'].notna()]
    vm = (measured['empty'] / measured['total_private']).values
    su['v_range'] = (float(vm.min()), su['v_2023'], float(vm.max()))
    rs = B['hist_rv_share'].loc[2011:2025]
    su['rv_range'] = (float(rs.min()), float(B['rv_share']), float(rs.max()))
    su['pre_share'] = float(B['empty_share_measured'])
    su['k_range'] = (Boss.household_rebase_factor(B['hh_raw_dhe'], 'occupied'), float(B['hh_rebase_k']), 1.0)

    # ---- carbon factors ----
    tf = pd.read_csv(Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]
    bf = pd.read_csv(os.path.join(Boss.DATA_DIR, 'factors_building.csv'))
    su['soc'] = tf['SOC_avg'].values
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
# b and rho enter only when the 2025 household-size deviation is carried
# (HH_SIZE_RESPONSE, a sensitivity); hh_rebase only when households are rebased.
PARAMS = (['z_pop'] + (['b', 'rho'] if Boss.HH_SIZE_RESPONSE else [])
          + (['hh_rebase'] if Boss.HH_CENSUS_REBASE else [])
          + ['regime', 'phi', 'slope_T', 'slope_A', 'size', 'complete',
             'pre_share', 'vacancy', 'rv_share', 'carbon'])


def central(su):
    return dict(z_pop=0.0, b=su['b_hat'], rho=su['rho_hat'], hh_rebase=su['k_range'][1],
                regime=0.0, phi=Boss.DAMPING_PHI,
                slope_T=0.0, slope_A=0.0, size=1.0, complete=Boss.COMPLETION_RATE,
                pre_share=su['pre_share'], vacancy=su['v_2023'], rv_share=su['rv_range'][1],
                carbon=None)


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
    B, fy, typ = su['B'], su['fy'], su['typ']
    # ---- population and household size (same rank z) ----
    pop = su['pop50'] + interp_z(p['z_pop'], Z_KNOTS, su['spreads'])
    # historical households under this draw's census rebase
    k = p.get('hh_rebase', su['k_range'][1])
    hh_hist = Boss.annual_households(Boss.rebase_households(B['hh_raw_dhe'], k)).reindex(B['years_hist'])
    S_hist = B['hist_pop'] / hh_hist
    key = 'S_resp' if Boss.HH_SIZE_RESPONSE else 'S_matched'
    S_v = [Boss.respond_household_size(*su['size_shape'][v], S_hist, B['hist_pop'], fy,
                                       p.get('b', su['b_hat']), p.get('rho', su['rho_hat']))[key]
           for v in VARIANT_Z]
    S = interp_z(p['z_pop'], np.array(list(VARIANT_Z.values())), np.array(S_v))
    hh = pop / S
    d_hh = np.insert(np.diff(hh), 0, 0.0)
    if Boss.FLOOR_HOUSEHOLD_DECLINE:
        d_hh = np.maximum(d_hh, 0.0)

    # ---- stock: recalibrate for this completion rate / pre-2013 share ----
    c = p['complete']
    cal = B['calibrate_stock'](p['pre_share'], completion=c, hh=hh_hist)
    end = B['calib_end']
    # regime: weight on the 2019-2023 census interval's net replacement rate
    # against the whole census-benchmarked window (0 = long run, as in Boss)
    unc_recent = (float(cal['net'].loc[2019:end].sum() / cal['prev'].loc[2019:end].sum())
                  - Boss.DEMOLITION_RATE) if end >= 2019 else cal['rate_unc']
    unc = (1 - p['regime']) * cal['rate_unc'] + p['regime'] * unc_recent
    d_hh_2025 = float(hh_hist.loc[2025] - hh_hist.loc[2024])
    other_2025 = c * (B['hist_total_units'].loc[2025] + B['hist_rv_units'].loc[2025]) - d_hh_2025
    model_2025 = (cal['allow'].loc[2025] + cal['change'].loc[2025]
                  + (Boss.DEMOLITION_RATE + unc) * cal['stock'].shift(1).loc[2025])
    yh = B['years_hist']
    net = cal['net'][(yh >= Boss.DEMOLITION_CALIB_START) & (yh <= end)].values
    rho_o = float(np.clip(np.corrcoef(net[:-1], net[1:])[0, 1], 0.0, 0.95))
    dev = (other_2025 - model_2025) * rho_o ** np.arange(len(fy))
    dev[0] = 0.0
    v0 = float(cal['knots'][max(cal['knots'])])
    v = v0 + (p['vacancy'] - v0) * (fy - 2025) / (fy[-1] - 2025)
    inv = 1.0 / (1.0 - v)
    hh_prev = np.concatenate([[hh[0]], hh[:-1]])
    inv_prev = np.concatenate([[inv[0]], inv[:-1]])
    allow = d_hh * v * inv
    change = hh_prev * (inv - inv_prev)
    beyond = allow + change + (Boss.DEMOLITION_RATE + unc) * hh_prev * inv_prev + dev
    rv = -p['rv_share'] * (d_hh + beyond)
    dwell = d_hh + beyond + rv

    # ---- typology mix and dwelling size ----
    ahead = (fy - 2025).clip(min=0)
    damp = p['phi'] * (1 - p['phi'] ** ahead) / (1 - p['phi'])
    off = {typ[1]: p['slope_T'], typ[2]: p['slope_A']}
    ex = np.array([np.ones(len(fy))] + [np.exp(su['alr_2025'][n] + (su['alr_slope'][n] + off[n]) * damp)
                                        for n in typ[1:]])
    shares = ex / ex.sum(axis=0)                           # (typ, years)
    size = su['size_ref'] * p['size']
    D = 1.0 / (shares / size[:, None]).sum(axis=0)
    gfa = dwell * D
    gfa_t = shares * gfa                                   # (typ, years)

    # ---- carbon ----
    if p['carbon'] is None:
        emb, upf = su['emb_central'], su['up_central']
    else:
        k = min(int(p['carbon'] * N_BOOT), N_BOOT - 1)
        emb, upf = su['boot_emb'][k], su['boot_up'][k]
    carbon = ((emb + su['soc'])[:, None] * gfa_t).sum(axis=0)
    upfront = ((upf + su['soc'])[:, None] * gfa_t).sum(axis=0)
    return dict(gfa=gfa, carbon=carbon, upfront=upfront, rv_units=-rv, hh=hh, S=S)


def summarise(out):
    s = slice(1, None)                                     # 2026-2050
    return np.array([out['gfa'][s].sum() / 1e6, out['carbon'][s].sum() / 1e6,
                     out['upfront'][s].sum() / 1e6, out['rv_units'][s].sum(),
                     out['hh'][-1] / 1e6, out['S'][-1]])


OUTPUTS = ['GFA_Mm2', 'carbon_kt', 'upfront_kt', 'RV_units', 'households_2050_M', 'S_2050']


def validate(su):
    """The engine at central values must reproduce Boss.main() exactly."""
    B = su['B']
    o = project(su, central(su))
    R = B['results']['50th']
    ref = dict(gfa=R['total'], carbon=B['carbon_total_typ'].sum(axis=1).values,
               rv_units=-B['stock_fwd']['50th']['rv'])
    worst = 0.0
    for k, r in ref.items():
        rel = np.abs(o[k][1:] - r[1:]) / np.maximum(np.abs(r[1:]), 1e-9)
        worst = max(worst, float(rel.max()))
    print(f"[check] engine vs Boss.main(), central values, 2026-2050: max relative "
          f"difference {worst:.1e} ({'OK' if worst < 1e-9 else 'FAIL'})")
    if worst >= 1e-9:
        sys.exit("Engine does not reproduce Boss.main(); results would not be valid.")


# ============================================================
# DISTRIBUTIONS
# ============================================================
def distributions(su):
    tn_a = (0.0 - su['rho_hat']) / su['rho_se']
    tn_b = (0.95 - su['rho_hat']) / su['rho_se']

    def tri(lo, mode, hi):
        return stats.triang(c=(mode - lo) / (hi - lo), loc=lo, scale=hi - lo)
    typ = su['typ']
    return {
        'z_pop': stats.norm(0, 1),
        'b': stats.norm(su['b_hat'], su['b_se']),
        'rho': stats.truncnorm(tn_a, tn_b, loc=su['rho_hat'], scale=su['rho_se']),
        'hh_rebase': tri(*su['k_range']),
        'regime': stats.uniform(0, 1),
        'phi': tri(PHI_RANGE[0], Boss.DAMPING_PHI, PHI_RANGE[1]),
        'slope_T': stats.norm(0, su['alr_se'][typ[1]]),
        'slope_A': stats.norm(0, su['alr_se'][typ[2]]),
        'size': stats.lognorm(s=su['size_sigma'], scale=1.0),
        'complete': stats.uniform(*Boss.COMPLETION_RATE_BAND[:1],
                                  Boss.COMPLETION_RATE_BAND[1] - Boss.COMPLETION_RATE_BAND[0]),
        'pre_share': stats.uniform(su['pre_share'] - Boss.PRE2013_EMPTY_SHARE_BAND,
                                   2 * Boss.PRE2013_EMPTY_SHARE_BAND),
        'vacancy': tri(*su['v_range']),
        'rv_share': tri(*su['rv_range']),
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
def main():
    t0 = time.time()
    su = build_setup()
    validate(su)
    dists = distributions(su)

    print("\nINPUT DISTRIBUTIONS (5th / 50th / 95th)")
    for k in PARAMS:
        q = dists[k].ppf([0.05, 0.5, 0.95])
        print(f"   {k:<10} {q[0]:>12.5g} {q[1]:>12.5g} {q[2]:>12.5g}")
    print(f"   carbon-factor bootstrap: {N_BOOT} replicates; between-building log-SD "
          f"{su['between_sigma']:.3f} used for single-case sub-types")

    # ---- 1. uncertainty: Latin hypercube ----
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
    summ.to_csv(os.path.join(OUT_DIR, 'montecarlo_summary.csv'))
    pd.DataFrame(np.vstack([X, Y]).T, columns=PARAMS + OUTPUTS).to_csv(
        os.path.join(OUT_DIR, 'montecarlo_draws.csv'), index=False)
    fy = su['fy']
    pd.DataFrame({f'{k}_{p}': np.percentile(fan[k], p, axis=0) for k in fan for p in (5, 50, 95)},
                 index=fy).to_csv(os.path.join(OUT_DIR, 'montecarlo_annual.csv'))

    print(f"\nJOINT UNCERTAINTY, 2026-2050 ({N_UNCERTAINTY:,} Latin hypercube draws)")
    print(summ.round(3).to_string())

    # ---- 2. Sobol indices ----
    rng = np.random.default_rng(SEED + 2)
    res = stats.sobol_indices(func=lambda x: evaluate(su, x), n=N_SOBOL,
                              dists=[dists[k] for k in PARAMS], rng=rng)
    with np.errstate(all='ignore'), __import__('warnings').catch_warnings():
        __import__('warnings').simplefilter('ignore')    # BCa is undefined for zero-variance rows
        boot = res.bootstrap(confidence_level=0.95, n_resamples=999)
    rows = []
    for o, name in enumerate(OUTPUTS):
        for i, k in enumerate(PARAMS):
            rows.append(dict(output=name, input=k,
                             S1=res.first_order[o, i], S1_lo=boot.first_order.confidence_interval.low[o, i],
                             S1_hi=boot.first_order.confidence_interval.high[o, i],
                             ST=res.total_order[o, i], ST_lo=boot.total_order.confidence_interval.low[o, i],
                             ST_hi=boot.total_order.confidence_interval.high[o, i]))
    sob = pd.DataFrame(rows)
    sob.to_csv(os.path.join(OUT_DIR, 'montecarlo_sobol.csv'), index=False)
    print(f"\nSOBOL INDICES ({N_SOBOL * (len(PARAMS) + 2):,} evaluations; 95% bootstrap CI)")
    for name in ['GFA_Mm2', 'carbon_kt']:
        t = sob[sob.output == name].sort_values('ST', ascending=False)
        print(f"   {name}")
        for r in t.itertuples():
            if not np.isfinite(r.ST_lo):             # input cannot affect this output
                print(f"     {r.input:<10} n/a (does not enter this output)")
                continue
            print(f"     {r.input:<10} S1 {r.S1:6.3f} [{r.S1_lo:6.3f}, {r.S1_hi:6.3f}]   "
                  f"ST {r.ST:6.3f} [{r.ST_lo:6.3f}, {r.ST_hi:6.3f}]")
    print("   S1: variance explained by the input alone. ST: including interactions.")

    if SAVE_FIGURES:
        plot(su, fan, sob)
    print(f"\nWritten: montecarlo_summary.csv, montecarlo_draws.csv, montecarlo_annual.csv, "
          f"montecarlo_sobol.csv in {OUT_DIR}/  ({time.time() - t0:,.0f} s)")


def plot(su, fan, sob):
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fy = su['fy'][1:]
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    for a, k, lab, sc in [(ax[0], 'gfa', 'million m² per year', 1e6),
                          (ax[1], 'carbon', 'kt CO₂e per year', 1e6)]:
        f = fan[k][:, 1:] / sc
        a.fill_between(fy, *np.percentile(f, [5, 95], axis=0), color='#4C72B0', alpha=0.18,
                       label='5th-95th')
        a.fill_between(fy, *np.percentile(f, [25, 75], axis=0), color='#4C72B0', alpha=0.35,
                       label='25th-75th')
        a.plot(fy, np.percentile(f, 50, axis=0), color='#4C72B0', lw=2, label='median')
        c = project(su, central(su))[k][1:] / sc
        a.plot(fy, c, color='black', lw=1.2, ls='--', label='Boss central')
        a.set_ylabel(lab); a.set_xlim(2026, 2050); a.grid(alpha=0.3); a.legend(fontsize=8)
    ax[0].set_title('Annual built floor area (in scope), joint uncertainty')
    ax[1].set_title('Annual embodied carbon, joint uncertainty')
    t = sob[sob.output == 'carbon_kt'].sort_values('ST')
    y = np.arange(len(t))
    ax[2].barh(y - 0.2, t['ST'], 0.4, color='#DD8452', label='total (ST)')
    ax[2].barh(y + 0.2, t['S1'], 0.4, color='#55A868', label='first order (S1)')
    ax[2].set_yticks(y); ax[2].set_yticklabels(t['input'])
    ax[2].set_title('Sobol indices, cumulative carbon 2026-2050'); ax[2].legend(fontsize=8)
    ax[2].grid(alpha=0.3, axis='x')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'montecarlo.png'), dpi=130, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
