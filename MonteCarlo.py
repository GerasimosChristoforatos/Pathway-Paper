"""
MONTE CARLO -- joint uncertainty and variance-based sensitivity for projection.py
===========================================================================
projection.py gives one central projection plus a population-only band. This script
samples every uncertain input at once, propagates them through the same model,
and reports:
  1. percentiles of the 2026-2050 totals (floor area, carbon, upfront carbon,
     retirement-village units, households and household size in 2050), and an
     annual fan;
  2. first-order and total Sobol indices: the share of output variance each
     input explains alone, and including its interactions (Saltelli et al.
     2010 / Jansen estimators, as implemented in scipy.stats.sobol_indices).

ENGINE
  One full projection.main() takes about three seconds, too slow for ~25,000 runs.
  Each draw therefore calls only the forward chain, through the SAME pure
  functions projection.main() uses (engine.py): stock calibration, 2025 deviation,
  replacement path, near-term market excess, forward projection. Everything
  taken from projection (data series, calibration window, fixed rates, settings) is
  copied once in build_setup(), so later changes to projection's module settings
  cannot leak into a draw. Before sampling, the central draw is checked against
  projection.main() year by year (floor area, carbon, upfront carbon, RV units,
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
  half_life Uniform(5, 15) years (MODEL v3.3.0): the half-life of the Reference's fade of net replacement from the
            2018-2023 census-interval rate to the 1991-2023 long-run rate. Not identifiable from the census record
            (seven censuses, six interval rates), so it is sampled over the range of the former half-life variants;
            the deterministic 10 yr is its median. It acts in the Reference variant only (Low / High / Very High
            replacement do not fade).
  carbon    A stratified bootstrap of the case studies (resampled within
            sub-type, duplicate cases removed, re-pooled as in
            Building_factors). A sub-type with one independent case (the
            apartments) has no bootstrap spread, so it gets a lognormal
            multiplier with the pooled between-building log-SD of the other
            sub-types.
  CENTRING: the deterministic projection run uses the MEDIAN of every sampled input.
  Inputs are independent. Seeds are fixed, so runs are reproducible.
NOT SAMPLED (held at the projection value in every draw)
  net replacement level: the MC is run separately within each projection variant of
    MC_SCENARIOS (the Reference; Low, High and Very High replacement); within the Reference the
    half-life is sampled (above). Variant differences are reported separately (Sensitivity.py).
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
from scipy import stats
from scipy.interpolate import PchipInterpolator
from scipy.stats import qmc

import projection
import engine
import layout
import naming as N
import runprofile

# MODEL v3.0.0 run profiles (runprofile.py): full = 5,000 Latin hypercube draws with the existing seed and the Sobol
# indices; light = 1,000 draws with their own fixed seed, Sobol off. N_BOOT (the carbon-factor bootstrap that defines
# the carbon input distribution) is part of the design and the same in both profiles.
N_UNCERTAINTY = runprofile.get('n_draws')          # Latin hypercube draws per scenario
N_SOBOL = 1024                   # base sample; evaluations = N_SOBOL * (d + 2)
RUN_SOBOL = runprofile.get('sobol')
N_BOOT = 4000                    # carbon-factor bootstrap replicates
SEED = runprofile.get('mc_seed')   # full: 20260924 (MODEL v1.1 onwards); light: 20261014
CONVERGENCE_STEPS = (100, 200, 500, 1000, 2000, 3000, 4000, 5000)
Z_KNOTS = stats.norm.ppf([0.05, 0.25, 0.50, 0.75, 0.95])
PCT_COLS = {5: 2, 25: 3, 50: 4, 75: 5, 95: 6}   # popdata.xlsx Table 1 (skiprows=5)
VARIANT_Z = {'Low': Z_KNOTS[0], 'Medium': 0.0, 'High': Z_KNOTS[-1]}


# ============================================================
# SET-UP: everything that does not change between draws
# ============================================================
def load_level_percentiles():
    """Published population LEVEL percentiles (5, 25, 50, 75, 95th), persons."""
    raw = pd.read_excel(projection.FILE_POP_PROJ, sheet_name=projection.POP_SHEET_PROJ, skiprows=5)
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
    """Snapshot of one projection run. settings: projection module settings for this run
    (the module is reloaded first, so nothing leaks between scenarios)."""
    if settings is not None:
        importlib.reload(projection)
        for k, v in settings.items():
            if not hasattr(projection, k):
                raise AttributeError(f"projection has no setting '{k}'.")
            setattr(projection, k, v)
    projection.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        B = projection.main()
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
        projection.household_size(*projection.statsnz_size_shape(v, fy, tail=projection.S_TAIL)[1:], B['hist_S'], B['hist_pop'],
                            fy, 0.0, anchor_year=projection.S_ANCHOR_YEAR)['S_matched']
        for v in VARIANT_Z])

    # ---- typology mix (fixed in every draw): projection's held mix, 2026 the observed mix ----
    su['shares'] = B['evolving_gfa_shares'].copy()

    # ---- snapshot of projection's data and settings used in every draw ----
    su.update(years_hist=B['years_hist'], hist_hh=B['hist_hh'],
              knots=engine.vacancy_knots(B['census'], float(B['empty_share_measured'])),
              units_all=B['hist_units_all_c'], rv_units=B['hist_rv_units_c'],
              calib_start=projection.DEMOLITION_CALIB_START, calib_end=B['calib_end'], demol_rate=projection.DEMOLITION_RATE,
              completion=projection.COMPLETION_RATE, olf=dict(B['OLF_USED']), rv_share=float(B['rv_share']),
              nr_window=tuple(projection.NET_REPLACEMENT_WINDOW),
              census_stock=B['census']['total_private'], consents_monthly=B['consents_monthly'],
              lag_w=B['lag_w'], census_uc=B['census_uc'],
              # replacement scenario and near-term market excess, as in the projection run
              scenario=B['_scenario'], s3_half_life=projection.REPLACEMENT_HALF_LIFE,
              recent=tuple(projection.RECENT_INTERVAL), join_mode=B['_join_mode'],
              nowcast=B['nowcast'], units_all_raw=B['hist_units_all'],
              near_gap_ref=projection.OVERBUILD_GAP_REF, near_mode=projection.OVERBUILD_BOOKING,
              near_absorption=projection.OVERBUILD_ABSORPTION,
              # MODEL v3.0.0: logistic absorption of the overbuild (None: never absorbed, the legacy Reference)
              near_absorb_w=(None if projection.OVERBUILD_ABSORPTION_END is None
                             or projection.OVERBUILD_BOOKING != 'surplus' else
                             engine.logistic_weights(fy, projection.OVERBUILD_ABSORPTION_START,
                                                     projection.OVERBUILD_ABSORPTION_END)),
              # observed 2026 floor area (fixed in every draw)
              gfa_2026=(B['gfa_nowcast']['total'] if B['gfa_nowcast'] else None))

    # ---- dwelling size ----
    su['size_ref'] = np.array([B['size_ref'][t] for t in typ])
    dev = [np.log(B['hist_dwelling_size'][t].loc[2016:2025] / B['size_ref'][t]) for t in typ]
    su['size_sigma'] = float(np.sqrt(np.mean(np.concatenate([d.values for d in dev]) ** 2)))

    # ---- carbon factors ----
    tf = pd.read_csv(projection.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]
    bf = pd.read_csv(projection.FILE_FACTORS_BUILDING)
    su['soc'] = tf['SOC_avg'].values
    su['soil_on_repl'] = projection.SOIL_ON_REPLACEMENT
    su['emb_central'] = tf['embodied_materials'].values
    mf = pd.read_csv(projection.FILE_FACTORS_MATERIAL)
    up = (mf[mf['Stage'].isin(['A1-A3', 'A4-A5'])].groupby('Typology')['kgCO2e_per_m2'].sum())
    su['up_central'] = up.reindex(typ).values
    # material decarbonisation of A1-A3 (projection.DECARB_MODE) and A4-A5 (projection.DECARB_A45): per
    # case study and year, resampled with the SAME building indices and multipliers as
    # the 2025 factors
    red = None
    su['decarb'] = B['DECARB'] is not None
    if projection.DECARB_A45 not in ('held', 'resch'):
        raise ValueError(f"MonteCarlo supports DECARB_A45 'held' or 'resch', not '{projection.DECARB_A45}'.")
    if su['decarb']:
        red = pd.DataFrame(0.0, index=bf['id'], columns=list(fy))
        if B['DECARB13'] is not None:
            variant = projection.BF.decarb_variant(projection.DECARB_MODE, projection.DECARB_ITEM_CASE)
            r = pd.read_csv(projection.FILE_FACTORS_DECARB_BLD)
            red = red + (r[r['Variant'] == variant]
                         .pivot(index='id', columns='Year', values='A13_reduction_kgCO2e_per_m2')
                         .reindex(index=bf['id'], columns=list(fy)))
        if projection.DECARB_A45 == 'resch':
            g = projection.BF.generic_path(fy)
            red = red + pd.DataFrame(np.outer(bf['A4-A5'].values, 1.0 - g), index=bf['id'], columns=list(fy))
        su['red_central'] = np.array([B['RED_TOT'][t] for t in typ])          # (typ, years)
    # time-resolved accounting: replacement / repaint kernels (and the event profile by
    # age at 2025 factors, for the AR base) per case study, resampled the same way
    su['tr'] = bool(B['TIME_RESOLVED'])
    extras = {}
    if su['tr']:
        ev = pd.read_csv(projection.BF.OUT_EVENTS_BLD)
        ev = ev[ev['Timing'] == projection.EVENT_TIMING]
        n = len(fy)
        K, A = {}, {}
        for i in bf['id']:
            p = ev[ev['id'] == i].reset_index(drop=True)
            if p.empty:
                K[i], A[i] = np.zeros(n * n), np.zeros(AGE_MAX + 1)
                continue
            f = projection.EV.row_factors(p, fy, projection.DECARB_MODE, projection.DECARB_ITEM_CASE, projection.DECARB_A45)
            K[i] = projection.EV.kernel(p, fy, f).ravel()
            A[i] = projection.EV.age_profile(p, AGE_MAX).values
        extras = dict(kernel=pd.DataFrame.from_dict(K, orient='index'),
                      age=pd.DataFrame.from_dict(A, orient='index'))
        su['K_central'] = B['EVENTS']
        su['age_central'] = np.array([projection.EV.age_profile(B['EV_PROFILE'][B['EV_PROFILE']['Typology'] == t],
                                                          AGE_MAX).values for t in typ])
    su['boot_emb'], su['boot_up'], su['between_sigma'], dec, ext = carbon_bootstrap(bf, typ, red, extras)
    if su['decarb']:
        su['boot_red'] = dec                                                    # (N_BOOT, typ, years)
    if su['tr']:
        su['boot_K'] = ext['kernel'].reshape(N_BOOT, len(typ), len(fy), len(fy))
        su['boot_age'] = ext['age']                                             # (N_BOOT, typ, ages)
    return su


AGE_MAX = 50                      # oldest event age kept for the AR-base profile (building lifespan)


def carbon_bootstrap(bf, typ, red=None, extras=None):
    """Stratified bootstrap of pooled typology factors (materials, in scope).
    red: optional A1-A3 reduction per case study (rows = id) and year (columns);
    its bootstrap uses the same resampled indices and multipliers, so the random
    stream, and every 2025-factor draw, is unchanged. extras: {name: DataFrame (rows
    = id)} resampled the same way. Returns (emb, up, sigma, reduction (N_BOOT, typ,
    years) or None, {name: (N_BOOT, typ, columns)})."""
    extras = extras or {}
    rng = np.random.default_rng(SEED + 1)
    bf = bf[bf['duplicate_of'].fillna('') == ''].copy()
    bf['emb'] = bf[projection.STAGES_IN_SCOPE].sum(axis=1)
    bf['up'] = bf[['A1-A3', 'A4-A5']].sum(axis=1)
    # pooled between-building log-SD within sub-types that have >= 2 cases
    logs = [np.log(g['emb']) - np.log(g['emb']).mean()
            for _, g in bf.groupby('Subtype') if len(g) >= 2]
    dof = sum(len(l) - 1 for l in logs)
    sigma = float(np.sqrt(sum((l ** 2).sum() for l in logs) / dof))
    emb = np.empty((N_BOOT, len(typ)))
    upf = np.empty((N_BOOT, len(typ)))
    dec = None if red is None else np.empty((N_BOOT, len(typ), red.shape[1]))
    ext = {k: np.empty((N_BOOT, len(typ), v.shape[1])) for k, v in extras.items()}
    for j, t in enumerate(typ):
        subs = [g for _, g in bf[bf['Typology'] == t].groupby('Subtype')]
        e_sub, u_sub, r_sub, x_sub = [], [], [], {k: [] for k in extras}
        for g in subs:
            idx = rng.integers(0, len(g), size=(N_BOOT, len(g)))
            e, u = g['emb'].values[idx].mean(axis=1), g['up'].values[idx].mean(axis=1)
            rr = None if red is None else red.loc[g['id']].values[idx].mean(axis=1)   # (N_BOOT, years)
            xx = {k: v.loc[g['id']].values[idx].mean(axis=1) for k, v in extras.items()}
            if len(g) == 1:                          # no spread: borrow it
                k = np.exp(rng.normal(-sigma ** 2 / 2, sigma, N_BOOT))   # mean-preserving
                e, u = e * k, u * k
                rr = None if rr is None else rr * k[:, None]
                xx = {n_: v * k[:, None] for n_, v in xx.items()}
            e_sub.append(e); u_sub.append(u); r_sub.append(rr)
            for n_, v in xx.items():
                x_sub[n_].append(v)
        emb[:, j] = np.mean(e_sub, axis=0)
        upf[:, j] = np.mean(u_sub, axis=0)
        if dec is not None:
            dec[:, j, :] = np.mean(r_sub, axis=0)
        for n_ in extras:
            ext[n_][:, j, :] = np.mean(x_sub[n_], axis=0)
    return emb, upf, sigma, dec, ext


# ============================================================
# ENGINE
# ============================================================
PARAMS = ['z_pop', 'size', 'complete', 'carbon', 'half_life']
HALF_LIFE_RANGE = (5.0, 15.0)    # MODEL v3.3.0: replacement half-life ~ U(5, 15) yr (Reference variant)
# The net replacement level is NOT sampled: the MC runs separately within each projection variant
# (MC_SCENARIOS, naming.SCENARIOS); within the Reference the half-life is sampled. The first entry is the
# Reference (its files carry the Sobol indices and figures).
MC_SCENARIOS = [('REF', dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0)),
                ('LOW', dict(REPLACEMENT_VARIANT='LOW')),
                ('HIGH', dict(REPLACEMENT_VARIANT='HIGH')),
                ('VHIGH', dict(REPLACEMENT_VARIANT='VHIGH'))]


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
    return dict(z_pop=0.0, size=1.0, complete=su['completion'], carbon=None, half_life=su['s3_half_life'])


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


def project(su, p, full=False):
    """One draw through the shared engine. Reads only su (a snapshot) and p;
    inputs not in p are held at their central values. full=True also returns the draw's
    engine inputs and intermediate results under 'draw' (pathways_mc.py applies the pathway
    levers to them); the outputs are the same either way."""
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
    if su['scenario'] == 'VHIGH':                     # the census trend, refitted for this draw's completion rate
        unc = engine.replacement_path('VHIGH', None, None, fy,
                                      trend=engine.replacement_trend(rates, *su['nr_window'])) - su['demol_rate']
    else:
        unc = engine.replacement_path(su['scenario'], unc_long, unc_recent, fy, p['half_life'])
    dv = engine.deviation_2025(cal, c * su['units_all'].loc[2025],
                               float(su['hist_hh'].loc[2025] - su['hist_hh'].loc[2024]),
                               su['demol_rate'] + float(unc[0]), yh, su['calib_start'], su['calib_end'])
    dev = dv['dev'] if su['join_mode'] == 'carried_deviation' else 0.0
    v = float(cal['knots'][max(cal['knots'])])        # vacancy-rate parameter: the published 2023 census value

    # ---- typology mix (fixed) and dwelling size ----
    shares = su['shares']
    size = {t: su['size_ref'][j] * p['size'] for j, t in enumerate(typ)}

    # ---- carbon factors ----
    if p['carbon'] is None:
        emb, upf = su['emb_central'], su['up_central']
        red = su['red_central'] if su['decarb'] else None
        events = su['K_central'] if su['tr'] else None
    else:
        kc = min(int(p['carbon'] * N_BOOT), N_BOOT - 1)
        emb, upf = su['boot_emb'][kc], su['boot_up'][kc]
        red = su['boot_red'][kc] if su['decarb'] else None
        events = {t: su['boot_K'][kc, j] for j, t in enumerate(typ)} if su['tr'] else None
    base = upf if su['tr'] else emb                   # construction-year materials (projection.ACCOUNTING)
    if red is None:                                   # 2025 factors held
        I = {t: base[j] + su['soc'][j] for j, t in enumerate(typ)}
        U = {t: upf[j] + su['soc'][j] for j, t in enumerate(typ)}
    else:                                             # A1-A3 (and A4-A5) decarbonised, by year
        I = {t: base[j] - red[j] + su['soc'][j] for j, t in enumerate(typ)}
        U = {t: upf[j] - red[j] + su['soc'][j] for j, t in enumerate(typ)}

    fwd = lambda join=None, redev=None: engine.forward(
        pop, hh, np.insert(np.diff(pop), 0, 0).clip(min=0), v, su['demol_rate'], unc,
        dev, dv['rho'], su['rv_share'], shares, size, su['olf'], I, U,
        join=join, join_redev=redev, soil={t: su['soc'][j] for j, t in enumerate(typ)},
        gfa_fixed=({1: su['gfa_2026']} if su['gfa_2026'] is not None else None),
        soil_on_replacement=su['soil_on_repl'], events=events)
    E = fwd()
    E_nojoin, join, ji = E, None, None
    if su['join_mode'] == 'market_excess':
        b26 = c * ((1.0 - su['lag_w']) * float(su['nowcast']['total'])
                   + su['lag_w'] * float(su['units_all_raw'].loc[2025]))
        join, ji = engine.market_excess(E, b26, dv['rho'], su['near_gap_ref'], su['near_mode'],
                                        su['near_absorption'], absorb_w=su['near_absorb_w'])
        E = fwd(join, ji['redev'])
    out = dict(gfa=E['total'], carbon=E['carbon'], upfront=E['upfront'], rv_units=E['rv_units'],
               hh=hh, S=S, extra_clip=E['extra_clip'], gfa_t=E['gfa_t'],
               I=np.array([I[t] for t in typ]), U=np.array([U[t] for t in typ]))
    if full:
        out['draw'] = dict(
            pop=pop, hh=hh, growth=np.insert(np.diff(pop), 0, 0).clip(min=0), unc_long=float(unc_long), red=red,
            kc=None if p['carbon'] is None else min(int(p['carbon'] * N_BOOT), N_BOOT - 1),
            fwd_inputs=dict(v=v, rate_demol=su['demol_rate'], rate_unc=unc, dev_2025=dev, rho_dev=dv['rho'],
                            rv_share=su['rv_share'], shares=shares, size=size, olf=su['olf'], intensity=I,
                            intensity_upfront=U, soil={t: su['soc'][j] for j, t in enumerate(typ)},
                            gfa_fixed=({1: su['gfa_2026']} if su['gfa_2026'] is not None else None),
                            soil_on_replacement=su['soil_on_repl'], events=events),
            E_nojoin=E_nojoin, E=E, join=join, join_info=ji, rho=float(dv['rho']))
    return out


def summarise(out):
    s = slice(1, None)                                     # 2026-2050
    return np.array([out['gfa'][s].sum() / 1e6, out['carbon'][s].sum() / 1e6,
                     out['upfront'][s].sum() / 1e6, out['rv_units'][s].sum(),
                     out['hh'][-1] / 1e6, out['S'][-1]])


OUTPUTS = ['GFA_Mm2', 'carbon_kt', 'upfront_kt', 'RV_units', 'households_2050_M', 'S_2050']


def validate(su):
    """The engine at central values must reproduce projection.main() exactly."""
    B = su['B']
    o = project(su, central(su))
    R = B['results']['50th']
    typ = su['typ']
    up_int = {t: B['U_INT'][t] for t in typ}
    ref = dict(gfa=R['total'], carbon=B['carbon_total_typ'].sum(axis=1).values,
               upfront=(sum(B['evol_typ_total'][t].values * (up_int[t] - B['SOIL_INTENSITY'][t]) for t in typ)
                        + np.insert(B['flow_annual']['SOIL'].values, 0, 0.0)),
               rv_units=-B['stock_fwd']['50th']['rv'], hh=B['households_forecast']['50th'],
               S=B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th'])
    worst = 0.0
    for k, r in ref.items():
        rel = np.abs(o[k][1:] - r[1:]) / np.maximum(np.abs(r[1:]), 1e-9)
        worst = max(worst, float(rel.max()))
    print(f"[check] MC draw vs projection.main(), central values, 2026-2050, floor area, carbon, "
          f"upfront, RV units, households, S: max relative difference {worst:.1e} "
          f"({'OK' if worst < 1e-9 else 'FAIL'})")
    if worst >= 1e-9:
        sys.exit("Engine does not reproduce projection.main(); results would not be valid.")


# ============================================================
# DISTRIBUTIONS
# ============================================================
def distributions(su):
    return {
        'z_pop': stats.norm(0, 1),
        'size': stats.lognorm(s=su['size_sigma'], scale=1.0),
        'complete': TwoPiece(projection.COMPLETION_RATE_BAND[0], su['completion'], projection.COMPLETION_RATE_BAND[1],
                             shape='uniform'),
        'carbon': stats.uniform(0, 1),
        'half_life': stats.uniform(HALF_LIFE_RANGE[0], HALF_LIFE_RANGE[1] - HALF_LIFE_RANGE[0]),
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
    summ['reference'] = cen                            # the deterministic Reference run (median inputs)
    summ['reference_percentile'] = [100 * float((Y[i] < cen[i]).mean()) for i in range(len(OUTPUTS))]
    summ.index = pd.Index([N.identifier(o) for o in OUTPUTS], name='output')
    draws = N.columns(pd.DataFrame(np.vstack([X, Y]).T, columns=PARAMS + OUTPUTS))
    annual = N.columns(pd.DataFrame({f'{k}_{p}': np.percentile(fan[k], p, axis=0)
                                     for k in fan for p in (5, 25, 50, 75, 95)},
                                    index=pd.Index(su['fy'], name='year')))
    summ.to_csv(layout.writing(layout.montecarlo('summary', name)))
    draws.to_csv(layout.writing(layout.montecarlo('draws', name)), index=False)
    annual.to_csv(layout.writing(layout.montecarlo('annual', name)))
    print(f"\nJOINT UNCERTAINTY within {name}, 2026-2050 ({N_UNCERTAINTY:,} Latin hypercube draws)")
    print(summ.loc[['floor_area_Mm2', 'carbon_kt', 'upfront_kt'],
                   ['mean', 'p5', 'p50', 'p95', 'reference', 'reference_percentile']].round(3).to_string())
    if reference:                                      # input distributions and convergence (diagnostics)
        qs = (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)
        pd.DataFrame([dict(input=k, **{f'q{int(100 * a):02d}': float(np.atleast_1d(dists[k].ppf(a))[0]) for a in qs},
                           sample_mean=float(X[i].mean()), sample_sd=float(X[i].std(ddof=1)))
                      for i, k in enumerate(PARAMS)]).to_csv(
            layout.writing(layout.data(f'montecarlo/input_distributions_{name}.csv')), index=False)
        conv = []
        for nn in [c for c in CONVERGENCE_STEPS if c <= N_UNCERTAINTY]:
            for o in ('GFA_Mm2', 'carbon_kt'):
                y = Y[OUTPUTS.index(o), :nn]
                conv.append(dict(n=nn, output=N.identifier(o), mean=float(y.mean()),
                                 **{f'p{p}': float(np.percentile(y, p)) for p in (5, 50, 95)}))
        pd.DataFrame(conv).to_csv(layout.writing(layout.data(f'montecarlo/convergence_{name}.csv')), index=False)
    if not reference or not RUN_SOBOL:
        return summ

    # ---- Sobol indices (reference scenario; full profile only) ----
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
    sob['output'] = sob['output'].map(N.identifier)
    sob.to_csv(layout.writing(layout.montecarlo('sobol', name)), index=False)
    print(f"\nSOBOL INDICES, {name} ({N_SOBOL * (len(PARAMS) + 2):,} evaluations; 95% bootstrap CI)")
    for oname in ['floor_area_Mm2', 'carbon_kt']:
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
    importlib.reload(projection)                       # restore module defaults
    print(f"\nWritten: summary_<variant>.csv, draws_<variant>.csv, annual_<variant>.csv, sobol_REF.csv in "
          f"{os.path.dirname(layout.montecarlo('summary', 'REF'))}/  ({time.time() - t0:,.0f} s)")


if __name__ == '__main__':
    main()
