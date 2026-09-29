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
  One full Boss.main() takes about three seconds, too slow for ~24,000 runs.
  Each draw therefore calls only the forward chain, through the SAME pure
  functions Boss.main() uses (engine.py): stock calibration, 2025 deviation,
  damped mix, dwelling-size blend, forward projection. Everything taken from
  Boss (data series, calibration window, fixed rates, flags) is copied once in
  build_setup(), so later changes to Boss's module settings cannot leak into a
  draw. Before sampling, the central draw is checked against Boss.main() year
  by year (floor area, carbon, upfront carbon, RV units, households, household
  size); the script stops if any differs by more than 1e-9 (relative).
  tests/test_engine_equivalence.py proves the same on random draws against the
  frozen pre-unification code.
  Floor area follows Boss's definition: new households x occupied area + extra
  space (floored at zero) + other dwellings x realised size. The old MC engine
  used (all in-scope dwellings) x realised size, which differs only in a year
  where realised size falls below occupied area (the extra-space floor binds).

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
import matplotlib.pyplot as plt
from scipy import stats
from scipy.interpolate import PchipInterpolator
from scipy.stats import qmc

import Boss
import engine

N_UNCERTAINTY = 10000            # Latin hypercube draws for the percentiles
N_SOBOL = 1024                   # base sample; evaluations = N_SOBOL * (d + 2)
N_BOOT = 4000                    # carbon-factor bootstrap replicates
SEED = 20260924
PHI_RANGE = (0.62, 0.98)         # triangular, mode = Boss.DAMPING_PHI
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
    su['size_shape'] = {v: Boss.statsnz_size_shape(v, fy, tail=Boss.S_TAIL)[1:] for v in VARIANT_Z}
    hr = B['hh_response']
    su['b_hat'], su['b_se'] = hr['b'], hr['se_hac']
    su['rho_hat'] = hr['rho']
    su['rho_se'] = float(np.sqrt((1 - hr['rho'] ** 2) / hr['n_fit']))

    # ---- typology mix: Boss's ALR slopes, plus their HAC standard errors ----
    hs = B['hist_shares']
    su['alr_2025'], su['alr_slope'] = Boss.mix_trend(hs, B['shares_2025'], Boss.TREND_WINDOW_START, typ)
    win = hs.loc[hs.index >= Boss.TREND_WINDOW_START]
    yrs = win.index.values.astype(float)
    X = np.c_[np.ones(len(yrs)), yrs]
    su['alr_se'] = {}
    for n in typ[1:]:
        y = np.log(win[n] / win[typ[0]]).values
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        cov, _ = Boss.newey_west_cov(X, y - X @ beta)
        su['alr_se'][n] = float(np.sqrt(cov[1, 1]))

    # ---- snapshot of Boss's data and settings used in every draw ----
    su.update(years_hist=B['years_hist'], census=B['census'], hist_pop=B['hist_pop'],
              hh_raw_dhe=B['hh_raw_dhe'], units_all=B['hist_units_all_c'],
              rv_units=B['hist_rv_units_c'], calib_start=Boss.DEMOLITION_CALIB_START,
              calib_end=B['calib_end'], demol_rate=Boss.DEMOLITION_RATE,
              completion=Boss.COMPLETION_RATE, floor_decline=Boss.FLOOR_HOUSEHOLD_DECLINE,
              size_key='S_resp' if Boss.HH_SIZE_RESPONSE else 'S_matched',
              olf=dict(B['OLF_USED']), olf_per_resident=(Boss.DEMAND_BASIS == 'per_resident'),
              phi=Boss.DAMPING_PHI, s_anchor=Boss.S_ANCHOR_YEAR)

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
    su['k_range'] = (Boss.household_rebase_factor(B['hh_raw_dhe'], 'occupied', B['census_18_23']),
                     float(B['hh_rebase_k']), 1.0)

    # ---- carbon factors ----
    tf = pd.read_csv(Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]
    bf = pd.read_csv(Boss.FILE_FACTORS_BUILDING)
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
                regime=0.0, phi=su['phi'],
                slope_T=0.0, slope_A=0.0, size=1.0, complete=su['completion'],
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
    """One draw through the shared engine. Reads only su (a snapshot) and p."""
    fy, typ, yh = su['fy'], su['typ'], su['years_hist']
    # ---- population and household size (same rank z) ----
    pop = su['pop50'] + interp_z(p['z_pop'], Z_KNOTS, su['spreads'])
    # historical households under this draw's census rebase
    k = p.get('hh_rebase', su['k_range'][1])
    hh_hist = Boss.annual_households(Boss.rebase_households(su['hh_raw_dhe'], k)).reindex(yh)
    S_hist = su['hist_pop'] / hh_hist
    S_v = [Boss.respond_household_size(*su['size_shape'][v], S_hist, su['hist_pop'], fy,
                                       p.get('b', su['b_hat']), p.get('rho', su['rho_hat']),
                                       anchor_year=su['s_anchor'])[su['size_key']]
           for v in VARIANT_Z]
    S = interp_z(p['z_pop'], np.array(list(VARIANT_Z.values())), np.array(S_v))
    hh = pop / S

    # ---- stock: recalibrated for this draw's completion rate / pre-2013 share ----
    c = p['complete']
    cal = engine.calibrate_stock(yh, hh_hist, engine.vacancy_knots(su['census'], p['pre_share']),
                                 su['units_all'], su['rv_units'], c, su['demol_rate'],
                                 su['calib_start'], su['calib_end'])
    end = su['calib_end']
    # regime: weight on the 2019-2023 census interval's net replacement rate
    # against the whole census-benchmarked window (0 = long run, as in Boss)
    unc_recent = (engine.window_rate(cal, 2019, end) - su['demol_rate']) if end >= 2019 else cal['rate_unc']
    unc = (1 - p['regime']) * cal['rate_unc'] + p['regime'] * unc_recent
    dv = engine.deviation_2025(cal, c * su['units_all'].loc[2025],
                               float(hh_hist.loc[2025] - hh_hist.loc[2024]),
                               su['demol_rate'] + unc, yh, su['calib_start'], end)
    # vacancy: from the latest census value, reached linearly by 2050
    v0 = float(cal['knots'][max(cal['knots'])])
    v = v0 + (p['vacancy'] - v0) * (fy - 2025) / (fy[-1] - 2025)

    # ---- typology mix and dwelling size ----
    off = {typ[1]: p['slope_T'], typ[2]: p['slope_A']}
    shares = engine.mix_shares(su['alr_2025'], {n: su['alr_slope'][n] + off[n] for n in typ[1:]},
                               p['phi'], fy, typ)
    size = {t: su['size_ref'][j] * p['size'] for j, t in enumerate(typ)}

    # ---- carbon factors ----
    if p['carbon'] is None:
        emb, upf = su['emb_central'], su['up_central']
    else:
        kc = min(int(p['carbon'] * N_BOOT), N_BOOT - 1)
        emb, upf = su['boot_emb'][kc], su['boot_up'][kc]
    I = {t: emb[j] + su['soc'][j] for j, t in enumerate(typ)}
    U = {t: upf[j] + su['soc'][j] for j, t in enumerate(typ)}

    E = engine.forward(pop, hh, np.insert(np.diff(pop), 0, 0).clip(min=0), v, su['demol_rate'], unc,
                       dv['dev'], dv['rho'], p['rv_share'], shares, size, su['olf'], I, U,
                       floor_decline=su['floor_decline'], olf_per_resident=su['olf_per_resident'])
    return dict(gfa=E['total'], carbon=E['carbon'], upfront=E['upfront'], rv_units=E['rv_units'],
                hh=hh, S=S, extra_clip=E['extra_clip'], gfa_t=E['gfa_t'],
                I=np.array([I[t] for t in typ]), U=np.array([U[t] for t in typ]))


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
    typ = su['typ']
    up_int = {t: B['UPFRONT_2025'][t] for t in typ}
    ref = dict(gfa=R['total'], carbon=B['carbon_total_typ'].sum(axis=1).values,
               upfront=sum(B['evol_typ_total'][t].values * up_int[t] for t in typ),
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
    os.makedirs(OUT_DIR, exist_ok=True)
    summ.to_csv(os.path.join(OUT_DIR, 'montecarlo_summary.csv'))
    pd.DataFrame(np.vstack([X, Y]).T, columns=PARAMS + OUTPUTS).to_csv(
        os.path.join(OUT_DIR, 'montecarlo_draws.csv'), index=False)
    fy = su['fy']
    pd.DataFrame({f'{k}_{p}': np.percentile(fan[k], p, axis=0)
                  for k in fan for p in (5, 25, 50, 75, 95)},
                 index=fy).to_csv(os.path.join(OUT_DIR, 'montecarlo_annual.csv'))

    print(f"\nJOINT UNCERTAINTY, 2026-2050 ({N_UNCERTAINTY:,} Latin hypercube draws)")
    print(summ.round(3).to_string())

    # ---- 2. Sobol indices ----
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

    print(f"\nWritten: montecarlo_summary.csv, montecarlo_draws.csv, montecarlo_annual.csv, "
          f"montecarlo_sobol.csv in {OUT_DIR}/  ({time.time() - t0:,.0f} s)")
    figures()


# ============================================================
# FIGURES  (drawn from the CSVs, so PLOT_ONLY needs no re-run)
# ============================================================
INPUT_LABELS = {
    'z_pop': 'Population (with household size)',
    'hh_rebase': 'Census rebase of households, k',
    'regime': 'Redevelopment regime (long-run -> 2019-23)',
    'phi': 'Typology-trend damping, phi',
    'slope_T': 'Townhouse share trend',
    'slope_A': 'Apartment share trend',
    'size': 'Future dwelling size',
    'complete': 'Completion rate',
    'pre_share': 'Pre-2013 empty share',
    'vacancy': 'Vacancy rate',
    'rv_share': 'Retirement-village share',
    'carbon': 'Carbon factors (case-study bootstrap)',
    'b': 'Migration response, b',
    'rho': 'Deviation persistence, rho',
}
OUTPUT_LABELS = {
    'GFA_Mm2': ('Built floor area, 2026-2050', 'million m²', 1),
    'carbon_kt': ('Embodied carbon, 2026-2050', 'kt CO₂e', 1),
    'upfront_kt': ('Upfront carbon (A1-A5 + soil)', 'kt CO₂e', 1),
    'RV_units': ('Retirement-village units built', 'thousand units', 1e3),
    'households_2050_M': ('Households in 2050', 'million', 1),
    'S_2050': ('Household size in 2050', 'people per household', 1),
}
AXIS_LABELS = {
    'z_pop': 'population rank (standard deviations from median)',
    'hh_rebase': 'census rebase factor k (1 = as published)',
    'regime': 'weight on the 2019-23 redevelopment rate',
    'phi': 'damping phi',
    'size': 'dwelling size multiplier',
    'complete': 'share of consents built',
    'vacancy': 'vacancy rate',
    'rv_share': 'retirement-village share',
}
# Inputs that are an index into resampled replicates, not an ordered quantity:
# a scatter against them shows nothing, so the driver figure skips them.
UNORDERED_INPUTS = {'carbon'}
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
    fig.tight_layout()
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
    for a, k, hist, lab in [(ax[0], 'gfa', hist_gfa, 'million m² per year'),
                            (ax[1], 'carbon', hist_c, 'kt CO₂e per year')]:
        hy = hist.index[hist.index >= 2005]
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
        a.set_ylabel(lab); a.set_xlim(2005, 2050); a.set_ylim(0, None)
        a.grid(alpha=0.3); a.legend(fontsize=8, loc='upper right')
    ax[0].set_title('Built floor area (in scope)')
    ax[1].set_title('Embodied carbon (history estimated with 2025 factors)')
    _save(fig, 'mc_1_fan.png')

    # ---- 2. distributions of the totals ------------------------------------
    fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle('Monte Carlo 2: distribution of each result '
                 '(dashed = 5th / 50th / 95th, red = Boss central run)', fontsize=12)
    for a, o in zip(ax.ravel(), OUTPUT_LABELS):
        title, unit, sc = OUTPUT_LABELS[o]
        v = draws[o] / sc
        a.hist(v, bins=45, color=BLUE, alpha=0.75, edgecolor='white', linewidth=0.3)
        p5, p50, p95 = np.percentile(v, [5, 50, 95])
        for q in (p5, p50, p95):
            a.axvline(q, color='black', ls='--', lw=1 if q != p50 else 1.8)
        cen = summ.loc[o, 'central'] / sc
        a.axvline(cen, color='#C0392B', lw=2.2)
        fmt = (lambda x: f'{x:,.0f}') if p50 >= 100 else (lambda x: f'{x:.2f}' if p50 < 10 else f'{x:.1f}')
        a.set_title(f'{title}\nmedian {fmt(p50)}  [{fmt(p5)} - {fmt(p95)}]  |  central {fmt(cen)}')
        a.set_xlabel(unit); a.set_yticks([]); a.grid(alpha=0.3, axis='x')
    _save(fig, 'mc_2_distributions.png')

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
    _save(fig, 'mc_3_sobol.png')

    # ---- 4. how the main drivers move the result ----------------------------
    ranked = (sob[(sob.output == 'carbon_kt') & np.isfinite(sob.ST_lo)]
              .sort_values('ST', ascending=False).input.tolist())
    top = [k for k in ranked if k not in UNORDERED_INPUTS][:4]
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.6), sharey=True)
    fig.suptitle('Monte Carlo 4: how the biggest drivers move cumulative carbon '
                 '(each dot = one draw; red = median in 12 bins; carbon-factor draws are '
                 'unordered, see figure 3)', fontsize=11)
    sub = draws.sample(min(4000, len(draws)), random_state=1)
    for a, k in zip(ax, top):
        a.scatter(sub[k], sub['carbon_kt'] / 1e3, s=4, alpha=0.18, color=BLUE)
        bins = pd.qcut(draws[k], 12, duplicates='drop')
        mid = draws.groupby(bins, observed=True)[k].median()
        med = draws.groupby(bins, observed=True)['carbon_kt'].median() / 1e3
        a.plot(mid, med, color='#C0392B', lw=2.2)
        st_v = sob[(sob.output == 'carbon_kt') & (sob.input == k)].ST.iloc[0]
        a.set_title(f'{INPUT_LABELS.get(k, k)}\ntotal effect {st_v:.2f}', fontsize=9.5)
        a.set_xlabel(AXIS_LABELS.get(k, k), fontsize=8.5); a.grid(alpha=0.3)
    ax[0].set_ylabel('embodied carbon 2026-2050 (Mt CO₂e)')
    _save(fig, 'mc_4_drivers.png')

    if SAVE_FIGURES:
        print(f"Figures written to {FIG_DIR}/ (mc_1 ... mc_4)")
    if SHOW_FIGURES:
        plt.show()


if __name__ == '__main__':
    if PLOT_ONLY or '--plot-only' in sys.argv:
        figures()
    else:
        main()
