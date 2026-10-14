"""
PLANETARY-BOUNDARY LAYER (AESA, climate change) on top of the model outputs
===========================================================================
Compares the sector's embodied carbon 2026-2050 (projection.ACCOUNTING: adopted
time-resolved, materials and construction A1-A5 and soil carbon loss in the construction
year and maintenance B2/B4 in the year it occurs; whole life at construction is a
sensitivity) with a share of a global
carrying capacity for climate change, allocated by two principles reported as
a range and never averaged:

  AR   acquired rights   Horup et al. (2025), Sci. Total Environ. 966, 178780, Eq. (1)
  AtP  ability to pay    Hjalsted et al. (2021), J. Ind. Ecol. 25, 6-19, Eqs. (5)-(6), SI Eq. S1

Static carrying capacity: SOS, I_glob, GDP per capita and the sector share are
held fixed; the boundaries move only with New Zealand and world population.
The model itself is not changed: projection.py, MonteCarlo.py and engine.py are only
called. Equations: aesa.py. Every constant below carries its source.

Writes outputs/data/aesa/ (annual.csv, montecarlo_annual.csv, montecarlo_draw_budgets.csv, sensitivity.csv,
results.json; layout.py) and the source data of the AESA diagnostics D18, D21-D27
(outputs/data/figure_source/<figure id>.json; figsource.py). MODEL v3.0.0: this module draws nothing; every figure
is drawn from the data files by the figures/ package (D18, D21-D27: figures/boundaries.py).

    python boundaries.py
"""
import contextlib
import importlib
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'tools'))
import aesa  # noqa: E402
import figsource  # noqa: E402
import layout  # noqa: E402
import projection  # noqa: E402
import MonteCarlo as MC  # noqa: E402
import naming as N  # noqa: E402
import validation  # noqa: E402

DATA_DIR = os.path.join(ROOT_DIR, 'data')
FILE_WPP = os.path.join(DATA_DIR, 'derived', 'wpp2024_population_median.csv')      # data/build_wpp.py
FILE_WDI = os.path.join(DATA_DIR, 'derived', 'wdi_economies.csv')                  # data/build_wdi.py
FILE_WDI_WLD = os.path.join(DATA_DIR, 'derived', 'wdi_world_aggregate.csv')        # data/build_wdi.py
FILE_GDP = os.path.join(DATA_DIR, 'derived', 'nz_gdp_quarterly.csv')               # data/build_gdp.py

# ---------------------------------------------------------------------------
# 1. CARRYING CAPACITY AND GLOBAL IMPACT (one switch; same-source pairs)
# ---------------------------------------------------------------------------
# Bjørn A, Hauschild MZ (2015) Int J Life Cycle Assess 20:1005-1018, Table 1
# (p. 1010) and ESM1 ('Climate change'); computed values in ESM2 (spreadsheet):
#   6.81E12 kg CO2-eq/yr: ESM2 sheet 'Climate change2degree' B26 = 6.8125E12,
#     the 2 °C TARGET (985 kg/person x 6,916,183,482); published to three
#     figures as 6.81E+12 by Sala et al. (2020) Table 3 and Horup et al. (2025)
#     Table 1. It is NOT the 1 W/m2 planetary boundary (Sala et al. 2020 label
#     it 'radiative forcing ... Rockström et al. 2009', which does not match B&H).
#   3.61E12 kg CO2-eq/yr: ESM2 sheet 'Climate change_RF' B26 = 3.6098E12, the
#     1 W/m2 planetary boundary (Rockström et al. 2009; 522 kg/person), rounded
#     to three figures as 6.81E12 is; '3.6 Gt' in ESM1 and Hjalsted et al. p. 10.
#   5.58E13 kg CO2-eq/yr: ESM2 'Climate change2degree' B30 ('Background
#     interventions_Global', typed input), global impact 2010 from Laurent et
#     al. (2013) PROSUITE D5.2 (8.1 t/person, ESM1). Laurent et al. (2013) is
#     not in hand: its land-use-change coverage and GWP basis are NOT VERIFIED.
# Pair B of the source check (6.81E12 with the EF3.1 normalisation factor
# 5.21E13) mixes sources and is not implemented (author decision).
SOURCE_PAIRS = {
    'A': dict(label='2 °C carrying capacity (Bjørn & Hauschild 2015)', sos=6.81e12, i_glob=5.58e13),
    'C': dict(label='1 W/m² planetary boundary (Bjørn & Hauschild 2015)', sos=3.61e12, i_glob=5.58e13),
}
SOURCE_PAIR = 'A'                  # primary (author decision); 'C' is the sensitivity

# ---------------------------------------------------------------------------
# 2. PERIOD, BASE YEAR, BASE WINDOW
# ---------------------------------------------------------------------------
T0 = 2025                          # base year of the population modifier (Horup Eq. 1)
PB_YEARS = (2026, 2050)
AR_BASE_WINDOW = (2016, 2025)      # mean annual sector impact, 10 years (manuscript)
AR_BASE_WINDOW_SENS = (2021, 2025)  # 5 years, as Horup et al. (2025) (2017-2021)
# Longer AR base windows (sensitivity rows; the 20-year one also as a non-adopted MC band).
# The history is consistent with the projection scope from 1992: consents by typology,
# retirement-village units and census-interval net replacement rates start in 1991, and
# the soil convention needs the previous year's stock (from 1991). Limitations: in
# 1996-2000 the census-interval net rate is negative, so soil applies to all floor area;
# pre-2013 vacancy rests on the estimated empty share; 2006-2025 includes the 2008-12 trough.
HIST_START = 1992
AR_BASE_WINDOW_20 = (2006, 2025)    # 20 years
AR_BASE_WINDOW_FULL = (HIST_START, 2025)   # the full consistent history (34 years)
# Historical soil convention = the projection's (engine.forward, soil_on_replacement
# False): soil only on floor area that is not net replacement. Net replacement in
# calendar year y = census-interval rate x last year's stock x (1 - RV share) x
# dwelling size, the interval being the one starting at or before y (2016-17:
# 2013-18; 2018-23: 2018-23). After the last census (2024-25): 'recent' = the
# 2018-23 rate carried (author decision), 'long_run' = the 1991-2023 rate (note).
HIST_RATE_AFTER_LAST_CENSUS = 'recent'

# ---------------------------------------------------------------------------
# 3. ABILITY TO PAY: GDP PER CAPITA AND SECTOR SHARE
# ---------------------------------------------------------------------------
GDP_MEASURE = 'NY.GDP.PCAP.PP.KD'  # WDI, PPP constant 2021 international $ (primary)
GDP_MEASURE_SENS = 'NY.GDP.PCAP.CD'  # WDI, current US$ (sensitivity; the only USD per-capita
#                                      measure in hand; Hjalsted et al. state 'USD/cap', World Bank 2019)
WDI_COVERAGE_MIN = 0.98            # base year b = latest year in which the economies reporting
#                                    GDP_MEASURE hold >= this share of the population of all WDI
#                                    economies (author decision; 0.99 is never reached)
ALPHA_CHECK_YEAR = 2017            # Hjalsted et al. (2021) SI p. S-1: alpha = 0.243 for 2017
ALPHA_HJALSTED_2017 = 0.243
SSEC_WINDOW = (2016, 2025)         # 10-year annual averages (manuscript, sheet 2.Equalitarian F2:F4)
SSEC_FCE_SHARE = 'mean_of_ratios'  # FCE/GDP: mean of the 40 quarterly ratios (manuscript);
#                                    'ratio_of_sums' is the sensitivity
SSEC_VALUE_COLUMNS = ('Value - Value/Detached', 'Value - Value/Townhouses',
                      'Value - Value/Apartments')   # retirement villages excluded (model scope)

# ---------------------------------------------------------------------------
# 4. POPULATION
# ---------------------------------------------------------------------------
# World: WPP 2024 probabilistic median (1 July). NZ: the model's own paths
# (central and per Monte Carlo draw). Dating: model year t is 31 December, so a
# mid-year series is dated at t as the mean of mid-year t and mid-year t+1.
POP_NZ_SOURCE = 'model'            # sensitivities: 'statsnz_median' (raw Stats NZ 2024-base
#                                    median at 30 June, PCHIP on level as MonteCarlo.py does for
#                                    the published percentiles), 'wpp_median' (WPP 2024, NZ row)

MC_REL_TOL = 1e-9                  # re-run MC draws must reproduce the saved draw outputs
MC_PCT = (5, 50, 95)
M6 = 1e6


# ============================================================
# DATA
# ============================================================
def world_population(years):
    """P_W(t), persons, dated 31 December t (mean of 1 July t and t+1)."""
    w = pd.read_csv(FILE_WPP).set_index('year')
    return aesa.mid_year_to_end_of_year(w['world'], years)


def nz_population_alt(source, years):
    """Alternative NZ paths for the population sensitivity, dated 31 December t."""
    if source == 'wpp_median':
        return aesa.mid_year_to_end_of_year(pd.read_csv(FILE_WPP).set_index('year')['new_zealand'], years)
    if source == 'statsnz_median':
        lv = MC.load_level_percentiles()                  # published levels, persons, 30 June
        f = PchipInterpolator(lv.index.values.astype(float), lv[50].values)
        need = np.arange(min(years), max(years) + 2)
        return aesa.mid_year_to_end_of_year(pd.Series(f(need.astype(float)), index=need), years)
    raise ValueError(f'Unknown NZ population source {source!r}.')


def historical_emissions(B, years, after=HIST_RATE_AFTER_LAST_CENSUS, events_from=None):
    """Sector emissions in past years (kg CO2e) at 2025 factors (the history is not
    decarbonised; actual past factors were likely higher, so the base is slightly
    conservative), with the same scope, accounting and soil convention as the
    projection: built floor area by typology (consents x completion rate) x
    construction-year intensity, plus soil on the non-replacement share of the floor
    area (engine.forward with soil_on_replacement=False). Time-resolved accounting
    (projection.ACCOUNTING): construction-year intensity = upfront (A1-A5), plus the
    replacement / repaint events of the cohorts built from events_from (default: the
    first of years) that occur in each year (b_kg), at 2025 factors."""
    typ = list(B['typ_names'])
    tr = bool(B.get('TIME_RESOLVED'))
    g = B['hist_built_typ_gfa'].loc[list(years), typ]
    gfa = g.sum(axis=1)
    units = B['hist_built_units'].loc[list(years)]
    rv = B['hist_rv_share'].loc[list(years)]
    prev = B['stock_cal']['prev'].loc[list(years)]
    cr = B['census_rates'].sort_values('y0')
    long_run = float(B['demolition_rate'] + B['unconsented_rate'])
    rate, src = [], []
    for y in years:
        w = cr[cr['y0'] <= y]
        if len(w) and y <= int(w['y1'].iloc[-1]):
            rate.append(float(w['rate'].iloc[-1])); src.append(f"{int(w['y0'].iloc[-1])}-{int(w['y1'].iloc[-1])}")
        elif y > int(cr['y1'].max()):
            last = cr.iloc[-1]
            rate.append(float(last['rate']) if after == 'recent' else long_run)
            src.append(f"{int(last['y0'])}-{int(last['y1'])} carried" if after == 'recent'
                       else f"long run {projection.NET_REPLACEMENT_WINDOW[0]}-{projection.NET_REPLACEMENT_WINDOW[1]}")
        else:
            raise ValueError(f'No census interval for {y}.')
    rate = pd.Series(rate, index=list(years))
    size = gfa / units
    soil_free = (rate * prev * (1.0 - rv) * size).clip(lower=0.0)
    soil_share = 1.0 - soil_free / gfa
    base_int = B['UPFRONT_2025'] if tr else B['T_BASELINE_2025']
    mat = sum(g[t] * (base_int[t] - B['SOIL_INTENSITY'][t]) for t in typ)
    soil = sum(g[t] * B['SOIL_INTENSITY'][t] for t in typ) * soil_share
    soil_all = sum(g[t] * B['SOIL_INTENSITY'][t] for t in typ)
    b = pd.Series(0.0, index=list(years))
    if tr:
        ef = int(years[0]) if events_from is None else int(events_from)
        gh = B['hist_built_typ_gfa'][typ]
        for t in typ:
            prof = B['EV_PROFILE'][B['EV_PROFILE']['Typology'] == t]
            b += hist_events(gh[t], projection.EV.age_profile(prof), list(years), ef)
    out = pd.DataFrame(dict(I_sec_kg=mat + soil + b, materials_kg=mat, b_kg=b, soil_kg=soil, soil_share=soil_share,
                            net_replacement_rate=rate, rate_source=src, gfa_m2=gfa,
                            I_soil_on_all_kg=mat + soil_all + b))
    for t in typ:                                  # for the base with other (MC) materials factors
        out[f'gfa_{t}'] = g[t]
    return out


def hist_events(gfa, age, years, events_from):
    """Replacement / repaint emissions in each of years (kg, 2025 factors) of the cohorts
    built from events_from (gfa: floor area by construction year; age: kg/m2 by age)."""
    out = []
    for y in years:
        cs = [c for c in gfa.index if events_from <= c < y and (y - c) in age.index]
        out.append(float(sum(gfa[c] * age[y - c] for c in cs)))
    return pd.Series(out, index=years)


def base_with_factors(hist, typ, emb, window=AR_BASE_WINDOW, age=None, events_from=None):
    """Ī_sec,base with construction-year materials factors emb (kg/m2 by typology,
    2025 technology) and, time-resolved, the event profiles age (kg/m2 by typology
    and age) of the cohorts built from events_from (default: the window's first
    year), on the observed floor area and soil of the history."""
    h = hist.loc[window[0]:window[1]]
    tot = sum(h[f'gfa_{t}'] * emb[j] for j, t in enumerate(typ)) + h['soil_kg']
    if age is not None:
        ef = window[0] if events_from is None else events_from
        for j, t in enumerate(typ):
            tot = tot + hist_events(hist[f'gfa_{t}'], pd.Series(age[j]), list(h.index), ef).values
    return float(tot.mean())


def legacy_events(B):
    """Replacement / repaint emissions in 2026-2050 (kg by year) of the cohorts built
    1992-2025 (wider-scope sensitivity), on the run's decarbonisation paths."""
    fy = np.asarray(B['forecast_years'])
    gh = B['hist_built_typ_gfa']
    out = np.zeros(len(fy))
    for t in B['typ_names']:
        prof = B['EV_PROFILE'][B['EV_PROFILE']['Typology'] == t].reset_index(drop=True)
        f = projection.EV.row_factors(prof, fy, projection.DECARB_MODE, projection.DECARB_ITEM_CASE, projection.DECARB_A45)
        age, kg = prof['Age'].to_numpy(int), prof['kg_per_m2'].to_numpy(float)
        for c in range(projection.B_SCOPE_START, 2026):
            for j, y in enumerate(fy[1:], start=1):
                hit = age == y - c
                if hit.any():
                    out[j] += gh.loc[c, t] * float((kg[hit] * f[hit, j]).sum())
    return pd.Series(out, index=fy)


def window_base(B, window, after=HIST_RATE_AFTER_LAST_CENSUS, col='I_sec_kg', scope=None):
    """Ī_sec,base over window, same accounting rule as the projection: upfront of the
    window's construction + the events, within the window, of the buildings built in it
    (scope 'since_1992': of every cohort since projection.B_SCOPE_START), at 2025 factors."""
    ef = projection.B_SCOPE_START if scope == 'since_1992' else window[0]
    h = historical_emissions(B, range(HIST_START, 2026), after, events_from=ef)
    return aesa.mean_over(h[col], window), h


def wdi_table():
    return pd.read_csv(FILE_WDI)


def wdi_components(wdi, measure, year):
    """alpha, g_W, g_NZ and coverage for one GDP measure and year, over the
    economies reporting both population and the measure (Hjalsted SI Eq. S1)."""
    d = wdi[wdi['year'] == year]
    all_pop = d['SP.POP.TOTL'].sum()
    ok = d['SP.POP.TOTL'].notna() & d[measure].notna()
    c = d[ok]
    p, g = c['SP.POP.TOTL'].values, c[measure].values
    wld = pd.read_csv(FILE_WDI_WLD).set_index('year').loc[year]
    world_gdp = float(wld['SP.POP.TOTL'] * wld[measure]) if pd.notna(wld[measure]) else float('nan')
    miss = d[~ok & d['SP.POP.TOTL'].notna()].sort_values('SP.POP.TOTL', ascending=False)
    nz = c[c['country_code'] == 'NZL']
    if nz.empty:
        raise ValueError(f'New Zealand has no {measure} in {year}.')
    return dict(measure=measure, year=int(year), alpha=aesa.alpha(p, g), g_W=aesa.world_gdp_per_capita(p, g),
                g_NZ=float(nz[measure].iloc[0]), n_economies=int(ok.sum()), n_all=int(d['SP.POP.TOTL'].notna().sum()),
                population_covered=float(p.sum()), population_share=float(p.sum() / all_pop),
                gdp_share_of_wdi_world=float((p * g).sum() / world_gdp),
                excluded=[dict(code=r.country_code, name=r.country_name, population=float(r['SP.POP.TOTL']))
                          for _, r in miss.iterrows()])


def base_year(wdi, measure, threshold):
    """Latest year in which the economies reporting the measure hold >= threshold
    of the population of all WDI economies."""
    for y in sorted(wdi['year'].unique(), reverse=True):
        d = wdi[wdi['year'] == y]
        ok = d['SP.POP.TOTL'].notna() & d[measure].notna()
        if d['SP.POP.TOTL'].notna().any() and d.loc[ok, 'SP.POP.TOTL'].sum() / d['SP.POP.TOTL'].sum() >= threshold:
            return int(y)
    raise ValueError(f'No year with {measure} coverage >= {threshold}.')


def sector_share_components(window=SSEC_WINDOW):
    """s_sec = residential consented value / national FCE (Hjalsted Eq. 6; manuscript
    sheet 2.Equalitarian F2:F4 and sheet 7). Annual averages over the window."""
    q = pd.read_csv(FILE_GDP)
    q = q[(q['year'] >= window[0]) & (q['year'] <= window[1])]
    n_years = window[1] - window[0] + 1
    if len(q) != 4 * n_years:
        raise ValueError(f'GDP(E): {len(q)} quarters in {window}, expected {4 * n_years}.')
    c = projection.load_consents()
    c['Date'] = pd.to_datetime(c['Date'])
    c = c[(c['Date'].dt.year >= window[0]) & (c['Date'].dt.year <= window[1])]
    if len(c) != 12 * n_years or c[list(SSEC_VALUE_COLUMNS)].isna().any().any():
        raise ValueError('Consents: incomplete months in the s_sec window.')
    value = float(c[list(SSEC_VALUE_COLUMNS)].to_numpy().sum() / n_years)          # NZD/yr
    gdp = float(q['gdp_nzd_m'].sum() * 1e6 / n_years)                              # NZD/yr
    mor = float((q['fce_nzd_m'] / q['gdp_nzd_m']).mean())
    ros = float(q['fce_nzd_m'].sum() / q['gdp_nzd_m'].sum())
    return dict(window=list(window), consented_value_nzd_per_yr=value, gdp_nzd_per_yr=gdp,
                fce_share_mean_of_ratios=mor, fce_share_ratio_of_sums=ros,
                s_sec_mean_of_ratios=aesa.sector_share(value, gdp, mor),
                s_sec_ratio_of_sums=aesa.sector_share(value, gdp, ros))


# ============================================================
# BOUNDARIES
# ============================================================
def boundaries(pair, i_base, comp, s_sec, p_nz, p_w):
    """B_AR and B_AtP (kg CO2e/yr) for year-indexed population Series that include T0."""
    sos, i_glob = SOURCE_PAIRS[pair]['sos'], SOURCE_PAIRS[pair]['i_glob']
    b_ar = aesa.boundary_ar(sos, i_base, i_glob, p_nz.values, p_w.values, p_nz.loc[T0], p_w.loc[T0])
    ind = aesa.sosos_ind_atp(sos, p_w.values, comp['g_W'], comp['g_NZ'], comp['alpha'])
    b_atp = aesa.boundary_atp(ind, p_nz.values, s_sec)
    return pd.Series(b_ar, index=p_nz.index), pd.Series(b_atp, index=p_nz.index)


def cum(impact, boundary, years=PB_YEARS):
    s = slice(*years)
    return aesa.cumulative_loe(impact.loc[s], boundary.loc[s])


# ============================================================
# RUNS
# ============================================================
def scenario_runs():
    """Deterministic scenarios of tools/replacement_scenarios.py (all rows of
    RESULTS.md): annual carbon and the NZ population path of each full projection run."""
    import replacement_scenarios as RS
    out = {}
    for key, label, settings in RS.SCENARIOS:
        B = validation.run_boss(**settings)
        fy = np.asarray(B['forecast_years'])
        out[key] = dict(label=label, settings=settings, committed=B.get('COMMITTED'),
                        b_inwindow=pd.Series(B['carbon_bev_typ'].sum(axis=1).values, index=fy),
                        I=pd.Series(B['carbon_total_typ'].sum(axis=1).values, index=fy),
                        pop=pd.Series(B['df_forecast']['PopTotal_50th'].values, index=fy))
    return out


def mc_runs(fy, hist):
    """Re-run every saved Monte Carlo draw of each MC scenario through
    MonteCarlo.project() from its saved parameters (MonteCarlo.py unchanged);
    each draw must reproduce its saved outputs to MC_REL_TOL. Returns, per
    scenario, the annual carbon (draws x years), NZ population (draws x years)
    and the AR base Ī_sec,base of each draw, recomputed from the draw's
    case-study carbon factors (2025 technology) on the observed history."""
    out = {}
    for name, settings in MC.MC_SCENARIOS:
        with contextlib.redirect_stdout(io.StringIO()):
            su = MC.build_setup(settings)
        path = layout.montecarlo('draws', name)
        d = pd.read_csv(path)
        X = d[[N.identifier(c) for c in MC.PARAMS]].to_numpy(float)
        Y = d[[N.identifier(c) for c in MC.OUTPUTS]].to_numpy(float)
        carbon = np.empty((len(d), len(fy)))
        pop = np.empty((len(d), len(fy)))
        ibase = np.empty(len(d))
        ibase20 = np.empty(len(d))
        kcar = MC.PARAMS.index('carbon')
        worst = 0.0
        for j in range(len(d)):
            o = MC.project(su, dict(zip(MC.PARAMS, X[j])))
            y = MC.summarise(o)
            worst = max(worst, float(np.max(np.abs(y - Y[j]) / np.maximum(np.abs(Y[j]), 1e-12))))
            carbon[j] = o['carbon']
            kc = min(int(X[j, kcar] * MC.N_BOOT), MC.N_BOOT - 1)        # the draw's bootstrap replicate
            if su['tr']:                                               # time-resolved base
                fac, age = su['boot_up'][kc], su['boot_age'][kc]
            else:
                fac, age = su['boot_emb'][kc], None
            ibase[j] = base_with_factors(hist, su['typ'], fac, AR_BASE_WINDOW, age)
            ibase20[j] = base_with_factors(hist, su['typ'], fac, AR_BASE_WINDOW_20, age)
            pop[j] = su['pop50'] + MC.interp_z(X[j, 0], MC.Z_KNOTS, su['spreads'])
            # the population path is the one the draw used: hh x S = pop
            if not np.allclose(o['hh'] * o['S'], pop[j], rtol=1e-12, atol=0):
                raise SystemExit(f'MC {name} draw {j}: population path not reproduced.')
        if worst > MC_REL_TOL:
            raise SystemExit(f'MC {name}: re-run draws differ from {os.path.basename(path)} by {worst:.1e} '
                             f'(> {MC_REL_TOL:g}); MC outputs are stale - rerun MonteCarlo.py.')
        print(f'  MC {name}: {len(d):,} draws re-run, max relative difference vs saved outputs {worst:.1e} (OK)')
        central = (base_with_factors(hist, su['typ'], su['up_central'], AR_BASE_WINDOW, su['age_central'])
                   if su['tr'] else base_with_factors(hist, su['typ'], su['emb_central']))
        out[name] = dict(carbon=carbon, pop=pop, i_base=ibase, i_base_central=central, i_base_20=ibase20)
    importlib.reload(projection)
    return out


# ============================================================
# MAIN
# ============================================================
def main():
    t_start = time.time()
    B = validation.run_boss()
    fy = np.asarray(B['forecast_years'])                     # 2025..2050
    years_b = list(range(T0, PB_YEARS[1] + 1))
    pair = SOURCE_PAIRS[SOURCE_PAIR]

    # ---- sector history and base -------------------------------------------
    # every base on the projection's accounting rule (window_base), at 2025 factors
    i_base, hist = window_base(B, AR_BASE_WINDOW)
    i_base_5, _ = window_base(B, AR_BASE_WINDOW_SENS)
    i_base_20, _ = window_base(B, AR_BASE_WINDOW_20)
    i_base_full, _ = window_base(B, AR_BASE_WINDOW_FULL)
    i_base_long, _ = window_base(B, AR_BASE_WINDOW, after='long_run')
    i_base_soil_all, _ = window_base(B, AR_BASE_WINDOW, col='I_soil_on_all_kg')
    i_base_wide, hist_wide = window_base(B, AR_BASE_WINDOW, scope='since_1992')
    w = slice(*AR_BASE_WINDOW)
    b_share_base = float(hist.loc[w, 'b_kg'].sum() / hist.loc[w, 'I_sec_kg'].sum())

    # ---- population ---------------------------------------------------------
    p_w = world_population(years_b)
    p_nz = pd.Series(B['df_forecast']['PopTotal_50th'].values, index=fy).loc[T0:]

    # ---- ability to pay -----------------------------------------------------
    wdi = wdi_table()
    b_year = base_year(wdi, GDP_MEASURE, WDI_COVERAGE_MIN)
    comp = wdi_components(wdi, GDP_MEASURE, b_year)
    comp_sens = wdi_components(wdi, GDP_MEASURE_SENS, b_year)
    alpha_check = {m: wdi_components(wdi, m, ALPHA_CHECK_YEAR) for m in (GDP_MEASURE_SENS, GDP_MEASURE)}
    ss = sector_share_components()
    s_sec = ss['s_sec_mean_of_ratios'] if SSEC_FCE_SHARE == 'mean_of_ratios' else ss['s_sec_ratio_of_sums']

    b_ar, b_atp = boundaries(SOURCE_PAIR, i_base, comp, s_sec, p_nz, p_w)
    ratio = (b_atp / b_ar)

    # ---- deterministic scenarios -------------------------------------------
    print('PB: deterministic scenarios')
    runs = scenario_runs()
    rows = []
    for key, r in runs.items():
        if not np.allclose(r['pop'].values, p_nz.reindex(r['pop'].index).fillna(r['pop']).values, rtol=0, atol=1e-6):
            raise SystemExit(f'Scenario {key}: NZ population differs from the central run.')
        I = r['I'].loc[T0:]
        for y in years_b:
            rows.append(dict(scenario=key, year=y, I_sec_kgCO2e=float(I.loc[y]) if y > T0 else float('nan'),
                             P_NZ=float(p_nz.loc[y]), P_W=float(p_w.loc[y]),
                             pop_modifier=float(aesa.population_modifier(p_nz.loc[y], p_w.loc[y], p_nz.loc[T0], p_w.loc[T0])),
                             B_AR_kgCO2e=float(b_ar.loc[y]), B_AtP_kgCO2e=float(b_atp.loc[y]),
                             LoE_AR=float(I.loc[y] / b_ar.loc[y]) if y > T0 else float('nan'),
                             LoE_AtP=float(I.loc[y] / b_atp.loc[y]) if y > T0 else float('nan')))
    for y in AR_BASE_WINDOW_RANGE():
        rows.append(dict(scenario='history', year=y, I_sec_kgCO2e=float(hist.loc[y, 'I_sec_kg'])))
    annual = pd.DataFrame(rows)
    N.columns(annual).to_csv(layout.writing(layout.data('aesa/annual.csv')), index=False)
    ref_I = runs['REF']['I']
    if not np.allclose(ref_I.values, B['carbon_total_typ'].sum(axis=1).values, rtol=1e-12):
        raise SystemExit('The REF variant run differs from the Reference projection run.')
    cum_det = {k: dict(label=r['label'], I_kt=float(r['I'].loc[slice(*PB_YEARS)].sum() / M6),
                       LoE_AR=cum(r['I'], b_ar), LoE_AtP=cum(r['I'], b_atp)) for k, r in runs.items()}

    # ---- population paths (MODEL v1.0.0 addition; the population rows of ED1, ED2 and ED4) ------------
    # The Stats NZ 5th / 95th percentile paths move both the embodied carbon (the projection's own
    # engine run of that path, every other input at the Reference) and the boundaries (population
    # modifier of AR, Horup et al. 2025 Eq. 1; per-capita AtP), with I_sec,base unchanged. The
    # median path reproduces the deterministic Reference (checked).
    pop_paths = {}
    for p in ('5th', '50th', '95th'):
        pnz_p = pd.Series(B['df_forecast'][f'PopTotal_{p}'].values, index=fy).loc[T0:]
        a_p, t_p = boundaries(SOURCE_PAIR, i_base, comp, s_sec, pnz_p, p_w)
        I_p = pd.Series(B['engine_out'][p]['carbon'], index=fy)
        w = slice(*PB_YEARS)
        pop_paths[p] = dict(I_kt=float(I_p.loc[w].sum() / M6), B_AR_kt=float(a_p.loc[w].sum() / M6),
                            B_AtP_kt=float(t_p.loc[w].sum() / M6), LoE_AR=cum(I_p, a_p), LoE_AtP=cum(I_p, t_p),
                            P_NZ_2050=float(pnz_p.loc[PB_YEARS[1]]))
    for k in ('LoE_AR', 'LoE_AtP'):
        if not np.isclose(pop_paths['50th'][k], cum_det['REF'][k], rtol=1e-12, atol=0):
            raise SystemExit(f'Population paths: the median path does not reproduce the Reference {k}.')

    # ---- Monte Carlo ---------------------------------------------------------
    print('PB: Monte Carlo (re-run from saved draws)')
    mc = mc_runs(fy, hist)
    mc_rows, mc_cum, mc_cum_fixed, mc_cum_20 = [], {}, {}, {}
    sel = (fy >= PB_YEARS[0]) & (fy <= PB_YEARS[1])
    pw_f = p_w.reindex(fy).values
    for name, m in mc.items():
        if not np.allclose(m['pop'][:, 0], p_nz.loc[T0], rtol=1e-12):
            raise SystemExit(f'MC {name}: draws do not share the observed {T0} population.')
        if not np.isclose(m['i_base_central'], i_base, rtol=1e-12):
            raise SystemExit(f'MC {name}: central-factor base {m["i_base_central"]:g} differs from {i_base:g}.')
        bar = aesa.boundary_ar(pair['sos'], m['i_base'][:, None], pair['i_glob'], m['pop'], pw_f,
                               p_nz.loc[T0], p_w.loc[T0])
        bar_fixed = aesa.boundary_ar(pair['sos'], i_base, pair['i_glob'], m['pop'], pw_f, p_nz.loc[T0], p_w.loc[T0])
        batp = aesa.boundary_atp(aesa.sosos_ind_atp(pair['sos'], pw_f, comp['g_W'], comp['g_NZ'], comp['alpha']),
                                 m['pop'], s_sec)
        la, lt = m['carbon'] / bar, m['carbon'] / batp
        for i, y in enumerate(fy):
            if not sel[i]:
                continue
            row = dict(scenario=name, year=int(y))
            for nm, arr in (('I_sec_kgCO2e', m['carbon']), ('B_AR_kgCO2e', bar), ('B_AtP_kgCO2e', batp),
                            ('LoE_AR', la), ('LoE_AtP', lt)):
                for p in MC_PCT:
                    row[f'{nm}_p{p}'] = float(np.percentile(arr[:, i], p))
            mc_rows.append(row)
        ca = m['carbon'][:, sel].sum(axis=1) / bar[:, sel].sum(axis=1)
        ct = m['carbon'][:, sel].sum(axis=1) / batp[:, sel].sum(axis=1)
        if name == 'REF':      # MODEL v2.0.0: each draw's cumulative budgets, read by the pathway Monte Carlo
            N.columns(pd.DataFrame(dict(
                draw=np.arange(len(ca)), carbon_kt_2026_2050=m['carbon'][:, sel].sum(axis=1) / M6,
                B_AR_kt_2026_2050=bar[:, sel].sum(axis=1) / M6, B_AtP_kt_2026_2050=batp[:, sel].sum(axis=1) / M6,
                LoE_AR=ca, LoE_AtP=ct))).to_csv(layout.writing(layout.data('aesa/montecarlo_draw_budgets.csv')),
                                                index=False)
        mc_cum[name] = {f'LoE_AR_p{p}': float(np.percentile(ca, p)) for p in MC_PCT}
        mc_cum[name].update({f'LoE_AtP_p{p}': float(np.percentile(ct, p)) for p in MC_PCT})
        mc_cum[name]['n_draws'] = int(len(ca))
        mc_cum[name].update({f'I_sec_base_kt_p{p}': float(np.percentile(m['i_base'], p) / M6) for p in MC_PCT})
        cf = m['carbon'][:, sel].sum(axis=1) / bar_fixed[:, sel].sum(axis=1)
        mc_cum_fixed[name] = {f'LoE_AR_p{p}': float(np.percentile(cf, p)) for p in MC_PCT}
        mc_cum_fixed[name].update({f'LoE_AtP_p{p}': float(np.percentile(ct, p)) for p in MC_PCT})
        # non-adopted variant: AR base over 20 years (2006-2025), per draw (no new random numbers)
        bar20 = aesa.boundary_ar(pair['sos'], m['i_base_20'][:, None], pair['i_glob'], m['pop'], pw_f,
                                 p_nz.loc[T0], p_w.loc[T0])
        c20 = m['carbon'][:, sel].sum(axis=1) / bar20[:, sel].sum(axis=1)
        mc_cum_20[name] = {f'LoE_AR_p{p}': float(np.percentile(c20, p)) for p in MC_PCT}
        mc_cum_20[name].update({f'I_sec_base_kt_p{p}': float(np.percentile(m['i_base_20'], p) / M6) for p in MC_PCT})
    mc_annual = pd.DataFrame(mc_rows)
    N.columns(mc_annual).to_csv(layout.writing(layout.data('aesa/montecarlo_annual.csv')), index=False)

    # ---- deterministic sensitivities (the Reference) --------------------------
    def cum_pair(pair_key=SOURCE_PAIR, ib=i_base, cp=comp, ssec=s_sec, pnz=p_nz):
        a, t = boundaries(pair_key, ib, cp, ssec, pnz, p_w)
        return cum(ref_I, a), cum(ref_I, t)
    ref_ar, ref_atp = cum_pair()
    sens = [('reference', 'Reference: carrying-capacity pair A, PPP 2021 int-$, base 2016-2025, model population, '
                          'mean of ratios',
             ref_ar, ref_atp),
            ('i_source_pair', f"(i) SOS/I_glob pair C: {SOURCE_PAIRS['C']['label']}", *cum_pair(pair_key='C')),
            ('ii_gdp_measure', f'(ii) GDP per capita, current US$ ({GDP_MEASURE_SENS}), b = {b_year}',
             *cum_pair(cp=comp_sens)),
            ('iii_base_window', f'(iii) AR base window {AR_BASE_WINDOW_SENS[0]}-{AR_BASE_WINDOW_SENS[1]} (5 yr, as Horup)',
             *cum_pair(ib=i_base_5)),
            ('iii_base_window_20', f'(iii) AR base window {AR_BASE_WINDOW_20[0]}-{AR_BASE_WINDOW_20[1]} (20 yr)',
             *cum_pair(ib=i_base_20)),
            ('iii_base_window_full', f'(iii) AR base window {AR_BASE_WINDOW_FULL[0]}-{AR_BASE_WINDOW_FULL[1]} '
             '(full consistent history)', *cum_pair(ib=i_base_full)),
            ('iv_pop_statsnz', '(iv) NZ population: raw Stats NZ 2024-base median (no 2025 observation, no nowcast)',
             *cum_pair(pnz=nz_population_alt('statsnz_median', years_b))),
            ('iv_pop_wpp', '(iv) NZ population: WPP 2024 probabilistic median, New Zealand',
             *cum_pair(pnz=nz_population_alt('wpp_median', years_b))),
            ('v_ssec', '(v) s_sec with FCE share as ratio of sums', ref_ar,
             cum_pair(ssec=ss['s_sec_ratio_of_sums'])[1]),
]
    # carbon-factor rows (boundaries unchanged, I_sec re-run): 'none' adopted: the
    # class-level decarbonisation; class-level adopted: frozen technology and the
    # STEEL class at the steel-profile rate; item-level adopted: frozen technology
    b_ar_ref, b_atp_ref = boundaries(SOURCE_PAIR, i_base, comp, s_sec, p_nz, p_w)

    def cum_I(base=None, add=None, **kw):
        """Cumulative LoE of a projection run with settings kw. base: its own AR base (a
        different accounting rule); add: emissions added to the run (kg by year)."""
        Bx = validation.run_boss(**kw)
        I = pd.Series(Bx['carbon_total_typ'].sum(axis=1).values, index=np.asarray(Bx['forecast_years']))
        if add is not None:
            I = I + add.reindex(I.index, fill_value=0.0)
        bar = b_ar_ref if base is None else boundaries(SOURCE_PAIR, base, comp, s_sec, p_nz, p_w)[0]
        return cum(I, bar), cum(I, b_atp_ref)
    if projection.DECARB_MODE == 'none':
        sens.append(('vi_decarb', '(vi) Materials decarbonised (A1-A3 item level, Horup et al. 2025 SI Table S4)',
                     *cum_I(DECARB_MODE='horup_item')))
    else:
        sens += [
            ('vi_frozen', '(vi) Frozen technology: 2025 factors held (A1-A3 and A4-A5 not decarbonised)',
             *cum_I(DECARB_MODE='none', DECARB_A45='held')),
            ('vii_proxies_held', '(vii) Proxy-mapped items held at 2025 (A1-A3)',
             *cum_I(DECARB_ITEM_CASE='proxies_held')),
            ('viii_nz_elec_held', '(viii) NZ-made, electricity-intensive items held at 2025 (A1-A3)',
             *cum_I(DECARB_ITEM_CASE='nz_elec_held')),
            ('ix_a45_held', '(ix) A4-A5 held at 2025 (no generic 1%/yr)', *cum_I(DECARB_A45='held')),
            ('x_a45_item', "(x) A4-A5 on each item's own Horup S4 path", *cum_I(DECARB_A45='item'))]
        if projection.ACCOUNTING == 'time_resolved':
            Bw = validation.run_boss(ACCOUNTING='whole_life_at_construction')
            base_w, _ = window_base(Bw, AR_BASE_WINDOW)
            sens += [
                ('xi_event_timing', '(xi) Event timing: interval L / n (instead of L / (n + 1))',
                 *cum_I(EVENT_TIMING='n')),
                ('xii_whole_life', '(xii) Accounting: whole life at construction (base on the same rule)',
                 *cum_I(base=base_w, ACCOUNTING='whole_life_at_construction')),
                ('xiii_wider_scope', f'(xiii) Wider scope: base and projection include the maintenance (B2, B4) of '
                 f'every cohort since {projection.B_SCOPE_START}',
                 *cum_I(base=i_base_wide, add=legacy_events(B)))]
    sens.append(('xiv_alpha_1', "(xiv) AtP with alpha = 1, as computed in Hjalsted et al.'s SI tables",
                 *cum_pair(cp=dict(comp, alpha=1.0))))
    sens.append(('note_soil_long_run', 'Note (not drawn in D18 or H11): history 2024-25 at the long-run net replacement rate',
                 *cum_pair(ib=i_base_long)))
    sens_df = pd.DataFrame(sens, columns=['case', 'label', 'cum_LoE_AR', 'cum_LoE_AtP'])
    sens_df['AR_vs_ref_pct'] = 100 * (sens_df['cum_LoE_AR'] / ref_ar - 1)
    sens_df['AtP_vs_ref_pct'] = 100 * (sens_df['cum_LoE_AtP'] / ref_atp - 1)
    N.columns(sens_df).to_csv(layout.writing(layout.data('aesa/sensitivity.csv')), index=False)

    # ---- results JSON ---------------------------------------------------------
    gfa = pd.Series(B['results']['50th']['total'], index=fy)
    dwell = pd.Series(B['engine_out']['50th']['dwell_in_scope'], index=fy)
    res = dict(
        settings=dict(SOURCE_PAIR=SOURCE_PAIR, T0=T0, PB_YEARS=list(PB_YEARS), AR_BASE_WINDOW=list(AR_BASE_WINDOW),
                      AR_BASE_WINDOW_SENS=list(AR_BASE_WINDOW_SENS), HIST_RATE_AFTER_LAST_CENSUS=HIST_RATE_AFTER_LAST_CENSUS,
                      GDP_MEASURE=GDP_MEASURE, GDP_MEASURE_SENS=GDP_MEASURE_SENS, WDI_COVERAGE_MIN=WDI_COVERAGE_MIN,
                      SSEC_WINDOW=list(SSEC_WINDOW), SSEC_FCE_SHARE=SSEC_FCE_SHARE, POP_NZ_SOURCE=POP_NZ_SOURCE,
                      DECARB_MODE=projection.DECARB_MODE,
                      **({'DECARB_ITEM_CASE': projection.DECARB_ITEM_CASE} if projection.DECARB_MODE == 'horup_item' else {})),
        source_pairs=SOURCE_PAIRS,
        components=dict(SOS_kg=pair['sos'], I_glob_kg=pair['i_glob'], pair_label=pair['label'],
                        I_sec_base_kg=i_base, I_sec_base_window=list(AR_BASE_WINDOW),
                        I_sec_base_b_share=b_share_base, I_sec_base_wider_scope_kg=i_base_wide,
                        accounting=projection.ACCOUNTING, decarb_a45=projection.DECARB_A45, event_timing=projection.EVENT_TIMING,
                        I_sec_base_5yr_kg=i_base_5, I_sec_base_long_run_2024_25_kg=i_base_long,
                        I_sec_base_20yr_kg=i_base_20, I_sec_base_full_kg=i_base_full,
                        I_sec_base_20yr_window=list(AR_BASE_WINDOW_20), I_sec_base_full_window=list(AR_BASE_WINDOW_FULL),
                        I_sec_base_soil_on_all_kg=i_base_soil_all,
                        LoE_AR_base_identity=pair['i_glob'] / pair['sos'],
                        base_year_b=b_year, alpha=comp['alpha'], g_W=comp['g_W'], g_NZ=comp['g_NZ'],
                        g_W_over_g_NZ=comp['g_W'] / comp['g_NZ'], s_sec=s_sec, s_sec_parts=ss,
                        P_NZ_t0=float(p_nz.loc[T0]), P_W_t0=float(p_w.loc[T0])),
        coverage={GDP_MEASURE: {k: v for k, v in comp.items()}, GDP_MEASURE_SENS: {k: v for k, v in comp_sens.items()}},
        alpha_check=dict(year=ALPHA_CHECK_YEAR, hjalsted_alpha=ALPHA_HJALSTED_2017, hjalsted_g_W_usd=1.07e4,
                         **{m: dict(alpha=v['alpha'], g_W=v['g_W'], n=v['n_economies'],
                                    population_share=v['population_share']) for m, v in alpha_check.items()}),
        history={int(y): dict(I_kt=float(r.I_sec_kg / M6), soil_share=float(r.soil_share),
                              rate_pct=float(100 * r.net_replacement_rate), rate_source=r.rate_source)
                 for y, r in hist.loc[AR_BASE_WINDOW[0]:AR_BASE_WINDOW[1]].iterrows()},
        boundaries={int(y): dict(B_AR_kt=float(b_ar.loc[y] / M6), B_AtP_kt=float(b_atp.loc[y] / M6),
                                 P_NZ=float(p_nz.loc[y]), P_W=float(p_w.loc[y])) for y in years_b},
        B_AtP_over_B_AR=dict(min=float(ratio.min()), max=float(ratio.max())),
        deterministic=cum_det, population_paths=pop_paths, mc=mc_cum, mc_base_fixed=mc_cum_fixed,
        mc_base_20yr=mc_cum_20,
        # maintenance within 2026-2050 twice: the projection's own total (committed['B_inwindow_kt'] ->
        # maintenance_kt) and this layer's sum of the annual series (equal to rounding)
        committed={k: dict(r['committed'],
                           maintenance_kt_sum_of_annual=float(r['b_inwindow'].loc[slice(*PB_YEARS)].sum() / M6),
                           b_share_inwindow=float(r['b_inwindow'].loc[slice(*PB_YEARS)].sum()
                                                  / r['I'].loc[slice(*PB_YEARS)].sum()),
                           years_of_B_AR_2050_upper=float(r['committed']['upper_kt'] * M6 / b_ar.loc[PB_YEARS[1]]),
                           years_of_B_AR_2050_lower=float(r['committed']['lower_kt'] * M6 / b_ar.loc[PB_YEARS[1]]))
                   for k, r in runs.items() if r.get('committed')},
        reference_2026_2050=dict(I_kt=float(ref_I.loc[slice(*PB_YEARS)].sum() / M6),
                                 B_AR_kt=float(b_ar.loc[slice(*PB_YEARS)].sum() / M6),
                                 B_AtP_kt=float(b_atp.loc[slice(*PB_YEARS)].sum() / M6),
                                 GFA_Mm2=float(gfa.loc[slice(*PB_YEARS)].sum() / M6)),
        sensitivity=sens_df.to_dict(orient='records'),
        notes=dict(
            wpp_manuscript_values='The manuscript world population 2025 (8,231,613,070) equals the WPP 2024 Median '
                                  'sheet x 1000; its 2026-2028 values differ from it by +/-0.5 person, consistent '
                                  'with a source at a higher precision than the 3-decimal thousands in this file; '
                                  'they are not a dating convention (the mean of 1 July t and t+1 differs by ~34 M).',
            mc_base='In the Monte Carlo the AR boundary varies with each draw\'s NZ population path and with '
                    'I_sec,base recomputed from the draw\'s case-study carbon factors (2025 technology) on the observed '
                    'history; the AtP boundary varies with population only. mc_base_fixed gives the bands with '
                    'I_sec,base held at its deterministic value.'))
    with open(layout.writing(layout.data('aesa/results.json')), 'w') as f:
        json.dump(N.keys(res), f, indent=2, default=float)

    print(f"\nPB layer ({pair['label']}; b = {b_year}): I_base {i_base / M6:,.1f} kt/yr | "
          f"B_AR 2026 {b_ar.loc[2026] / M6:,.1f} kt, 2050 {b_ar.loc[2050] / M6:,.1f} kt | "
          f"B_AtP 2026 {b_atp.loc[2026] / M6:,.2f} kt, 2050 {b_atp.loc[2050] / M6:,.2f} kt | "
          f"B_AtP/B_AR {ratio.min():.4f}")
    print(f"  alpha(b) {comp['alpha']:.4f}; alpha({ALPHA_CHECK_YEAR}) current US$ "
          f"{alpha_check[GDP_MEASURE_SENS]['alpha']:.4f} vs Hjalsted {ALPHA_HJALSTED_2017}; s_sec {s_sec:.7f}")
    print(f"  cumulative LoE 2026-2050, Reference: AR {cum_det['REF']['LoE_AR']:.2f} "
          f"(MC p5-p95 {mc_cum['REF']['LoE_AR_p5']:.2f}-{mc_cum['REF']['LoE_AR_p95']:.2f}); "
          f"AtP {cum_det['REF']['LoE_AtP']:.1f} "
          f"(MC {mc_cum['REF']['LoE_AtP_p5']:.1f}-{mc_cum['REF']['LoE_AtP_p95']:.1f})")

    # MODEL v3.0.0: the arrays of the AESA diagnostics (drawn by figures/boundaries.py)
    write_figure_sources(B, hist, runs, mc_annual, b_ar, b_atp, res, sens_df, gfa, dwell)
    print(f'PB done ({time.time() - t_start:,.0f} s)')
    return res


def AR_BASE_WINDOW_RANGE():
    return range(AR_BASE_WINDOW[0], AR_BASE_WINDOW[1] + 1)


# ============================================================
# ASSUMPTION REGISTER (read by tools/assumptions.py and tools/pb_methods.py)
# ============================================================
def assumption_register():
    """(setting, value, basis) for the PB layer; values read from the settings above."""
    pa, pc = SOURCE_PAIRS[SOURCE_PAIR], SOURCE_PAIRS['C']
    return [
        ('Impact category', 'climate change only', 'DECISION (author)'),
        ('Carrying capacity over time', 'static: SOS, I_glob, GDP per capita and s_sec held fixed; no IAM / '
         'Paris-aligned pathways', 'DECISION (author); limitation, Clausen et al. 2025, Sustain. Prod. Consum. 58, '
         '140-150 (pp. 143, 148)'),
        ('Sector impact', ('materials and construction (A1-A5) and soil carbon loss of each year\'s construction plus '
                           'the maintenance (B2, B4) occurring that year from buildings built in 2026-2050 '
                           '(time-resolved); later maintenance and end of life (C1-C4) are committed after 2050, '
                           'reported separately' if projection.ACCOUNTING == 'time_resolved' else
                           'the model\'s embodied carbon (A1-A5, B2, B4, C1-C4 + soil), all booked in the '
                           'construction year'),
         f"DECISION (author); projection.ACCOUNTING = '{projection.ACCOUNTING}'"),
        ('AR base on the same rule', f'Ī_sec,base = materials and construction (A1-A5) and soil carbon loss of {AR_BASE_WINDOW[0]}-'
         f'{AR_BASE_WINDOW[1]} construction + the maintenance (B2, B4) within {AR_BASE_WINDOW[0]}-{AR_BASE_WINDOW[1]} '
         'of the buildings built in it, at 2025 factors; '
         'base-window sensitivities on the same rule over their windows; wider scope (all cohorts since '
         f'{projection.B_SCOPE_START}) as a sensitivity', 'DECISION (author)'),
        ('Carbon factors over time', f"projection.DECARB_MODE = '{projection.DECARB_MODE}'"
         + {'none': '', 'horup_item': ' (A1-A3 by case-study EPD item, Horup et al. 2025; data/material_item_map.csv)'}[
             projection.DECARB_MODE]
         + f"; A4-A5 '{projection.DECARB_A45}' (Resch et al. 2021 Table 1: e^(-0.01 (t - 2025)))"
         + '; history and the AR base always at 2025 factors', 'DECISION (author); LITERATURE; see the projection register'),
        ('Allocation principles', 'acquired rights (Horup et al. 2025 Eq. 1) and ability to pay (Hjalsted et al. '
         '2021 Eqs. 5-6, SI S1), reported as a range, never averaged; the egalitarian-economic (EQ) principle of '
         'the earlier manuscript is not used', 'DECISION (author); LITERATURE'),
        ('SOS / I_glob pair', f"{SOURCE_PAIR}: {pa['label']}, SOS {pa['sos']:.3g}, I_glob {pa['i_glob']:.3g} kg "
         f"CO2-eq/yr; sensitivity C: {pc['label']}, SOS {pc['sos']:.3g}", 'DECISION (author) among LITERATURE '
         'values (Bjørn & Hauschild 2015, ESM2); see the source check'),
        ('Period and base year', f'{PB_YEARS[0]}-{PB_YEARS[1]}; t0 = {T0}', 'DECISION (author)'),
        ('AR base window', f'{AR_BASE_WINDOW[0]}-{AR_BASE_WINDOW[1]} (sensitivities {AR_BASE_WINDOW_SENS[0]}-'
         f'{AR_BASE_WINDOW_SENS[1]}, 5 yr as Horup et al. 2025; {AR_BASE_WINDOW_20[0]}-{AR_BASE_WINDOW_20[1]}, '
         f'20 yr, also as a non-adopted MC band; {AR_BASE_WINDOW_FULL[0]}-{AR_BASE_WINDOW_FULL[1]}, the full '
         'consistent history)', 'DECISION (author); LITERATURE for the 5-yr row'),
        ('History consistent with the projection scope', f'from {HIST_START}: consents by typology, retirement-'
         'village units and census-interval net replacement rates from 1991; the soil convention needs the previous '
         "year's stock", 'DATA; limitations: 1996-2000 negative census-interval net rate (soil on all floor area), '
         'pre-2013 vacancy on the estimated empty share, 2008-12 trough inside the 20-yr window'),
        ('Historical sector emissions', 'built floor area x 2025 case-study factors; soil only on non-replacement '
         'floor area (census-interval net replacement rate x last year\'s stock x (1 - RV share) x dwelling size), '
         f"2024-25 at the {'2018-23 rate carried' if HIST_RATE_AFTER_LAST_CENSUS == 'recent' else 'long-run rate'}",
         'DECISION (author): same convention as the projection; long-run 2024-25 rate reported as a note'),
        ('GDP per capita', f'{GDP_MEASURE} (PPP, constant 2021 international $); sensitivity {GDP_MEASURE_SENS} '
         '(current US$)', 'DECISION (author); DATA: World Bank WDI'),
        ('GDP base year b', f'latest year with >= {100 * WDI_COVERAGE_MIN:.0f}% of WDI-economy population '
         'reporting the PPP measure; held fixed (static)', 'DECISION (author); 99% is never reached'),
        ('alpha, g_W', 'computed over the covered economies (not a published world aggregate)',
         'LITERATURE: Hjalsted et al. 2021 SI Eq. S1'),
        ('Sector share s_sec', f'residential consented value (detached + townhouses + apartments) / national '
         f'final consumption expenditure, annual averages {SSEC_WINDOW[0]}-{SSEC_WINDOW[1]}; FCE share of GDP as '
         f'{SSEC_FCE_SHARE.replace("_", " ")}', 'LITERATURE: Hjalsted et al. 2021 Eq. 6; DATA: Stats NZ; '
         'DECISION: mean of quarterly ratios for continuity with the manuscript (ratio of sums is a sensitivity)'),
        ('World population', 'UN WPP 2024 probabilistic median (1 July), dated 31 December t as the mean of '
         '1 July t and t+1', 'DATA; DECISION (dating)'),
        ('NZ population', 'the model\'s paths (the Reference; each Monte Carlo draw); sensitivities: raw Stats NZ '
         '2024-base median (PCHIP on level, dated as above) and the WPP 2024 New Zealand median',
         'DATA (model); DECISION'),
        ('Monte Carlo', 'boundaries recomputed per draw from the draw\'s NZ population; I_sec,base recomputed per '
         'draw with the draw\'s 2025 carbon factors (historical floor area and soil as observed)', 'DECISION (author)'),
    ]


# Source check of the candidate SOS / I_glob values (documents in refs/, not versioned).
# value, what it is, where (paper + table/page), reference year, GWP basis, land-use-change CO2.
SOURCE_CHECK = [
    ('6.81E12', 'carrying capacity, 2 °C target (985 kg CO2-eq/person x 6,916,183,482)',
     'Bjørn & Hauschild 2015, Table 1 p. 1010; ESM1 "Climate change"; ESM2 sheet "Climate change2degree" B26 '
     '(6.8125E12). Reported as 6.81E+12 by Sala et al. 2020 Table 3 p. 7 (labelled radiative forcing / Rockström '
     '2009) and Horup et al. 2025 Table 1 p. 5',
     'gas weights from 2010 emissions (Laurent et al. 2013)',
     'ESM2: GWP100 IPCC AR5 (CH4 28, N2O 265); Table 1 cites Forster et al. 2007 (AR4)', 'n/a (capacity)'),
    ('3.61E12', 'carrying capacity, 1 W/m² planetary boundary (522 kg CO2-eq/person)',
     'Bjørn & Hauschild 2015, Table 1 p. 1010; ESM2 sheet "Climate change_RF" B26 (3.6098E12); "3.6 Gt" in ESM1, '
     'Hjalsted et al. 2021 p. 10 and SI Table S1', 'as above', 'as above', 'n/a (capacity)'),
    ('5.58E13', 'global impact ("background interventions", global)',
     'Bjørn & Hauschild 2015 ESM2 sheet "Climate change2degree" B30 (typed input); ESM1: 8.1 t/person from '
     'Laurent et al. 2013 (PROSUITE D5.2). EC-JRC "Normalization factors for testing" sheet 1.3: 5.589E13, '
     '8,100/person, "2010 or 2000"', '2010 (ESM1)', 'not stated; Laurent et al. 2013 not in hand',
     'NOT VERIFIED (Laurent et al. 2013 not in hand); 39.5 Gt CO2 in the ESM2 per-gas weights is consistent with '
     'inclusion (inference)'),
    ('5.21E13', 'EF 3.1 normalisation factor x population (7.55E3 kg/person x 6,895,889,018)',
     'Horup et al. 2025 Table 1 p. 5; Andreasi Bassi et al. 2023 (JRC EUR 31414 EN) Table 10', '2010 (Table 10)',
     'IPCC AR6 (EF 3.1, section 3.1)', 'EF 3.1 characterises CO2 (land use change) with CF 1 (Table 3); whether '
     'the global inventory behind the NF contains it is not stated there (inventory: Crenna et al. 2019, not in '
     'hand). Not used (pair B not implemented)'),
]


LIMITATIONS = [
    'Static carrying capacity: the carrying capacities are constant yearly values modelled at steady state and '
    'their timespan may not match the assessment period (Clausen et al. 2025, pp. 143 and 148).',
    ('Accounting (time-resolved): the sector impact of 2026-2050 counts materials and construction (A1-A5) and '
     'soil carbon loss in the construction year and maintenance (B2, B4) in the year it occurs. Maintenance after '
     '2050 and all end-of-life emissions (C1-C4) of the 2026-2050 cohorts are committed after 2050, outside 2026-2050; '
     'they are reported as a range (outputs/data/aesa/results.json "committed", Fig3c) in years of the 2050 AR boundary and are '
     'not compared with the 2026-2050 boundary. Whole life at construction is a sensitivity.'
     if projection.ACCOUNTING == 'time_resolved' else
     'B2, B4 and C1-C4 are booked in the construction year, so the impact of 2026-2050 includes future '
     'maintenance and end-of-life emissions of the buildings built in those years.'),
    'History at 2025 factors: the acquired-rights base (2016-2025) and the base-window sensitivities use the '
    '2025 case-study factors because no historical factor series exists for the case studies. If past production '
    'was more carbon-intensive than in 2025 (as the ~1%/yr technological progress assumed by Resch et al. 2021 '
    'implies), the base and hence the AR boundary are understated and the AR exceedance overstated '
    '(conservative); the size of this effect is not quantified. The base follows the '
    'projection\'s accounting rule (materials and construction and soil carbon loss of the base window\'s '
    'construction plus the maintenance within the base window of the cohorts built in it).',
    'The primary SOS (6.81E12) is the 2 °C carrying capacity of Bjørn & Hauschild (2015), not the 1 W/m² '
    'planetary boundary (3.61E12, sensitivity C). Sala et al. (2020, Table 3) label 6.81E12 as radiative forcing '
    'after Rockström et al. (2009), which does not match its derivation in Bjørn & Hauschild (2015).',
    'GWP basis: Bjørn & Hauschild (2015) ESM2 uses AR5 GWP100 factors (CH4 28, N2O 265; column "CFs (GWP100, '
    'IPCC5)") while their Table 1 cites Forster et al. (2007), i.e. AR4. The GWP basis of the case-study LCA '
    'factors used by the model is not documented in this repository (building_data.xlsx gives "GWP" columns '
    'only; source Christoforatos & Pickering 2025): to be confirmed by the author.',
    'I_glob = 5.58E13 (Bjørn & Hauschild 2015 ESM2, from Laurent et al. 2013, year 2010): Laurent et al. (2013) is '
    'not in hand, so whether it includes land-use-change CO2 (the sector impact includes soil carbon loss) and '
    'its GWP basis are NOT VERIFIED. The per-gas indicator scores in ESM2 sum to 54.0 Gt CO2-eq with 39.5 Gt CO2; '
    'a CO2 total of that size is consistent with inclusion of land-use-change CO2 (inference, not a sourced '
    'statement). The EC-JRC table "Normalization factors for testing" (Benini, Sala & Pant, version 0.1.1, 15 Dec 2015; sheet 1.3) gives the PROSUITE '
    'global value as 5.589E13 kg CO2-eq, 8,100 kg/person, "2010 or 2000".',
    'Final-consumption-expenditure upscaling: the numerator (consented residential value) is an investment flow '
    '(gross fixed capital formation), while Hjalsted et al. (2021) define the upscaling on final consumption and '
    'leave intermediate sectors as open (p. 16).',
    'Ability to pay: Hjalsted et al. (2021) state GDP as "USD/cap (2017)", World Bank (2019), without naming the '
    'series; current US$ is the sensitivity. The GDP coverage excludes economies without the measure (listed in '
    'outputs/data/aesa/results.json).',
    'Monte Carlo: I_sec,base is recomputed in every draw with that draw\'s case-study carbon factors (2025 '
    'technology), so the factor uncertainty is treated alike in the base and the projection; it does not '
    'co-vary with the draw\'s completion rate or dwelling size (historical floor area is observed).',
    'The numerical results in Hjalsted et al.\'s SI (Tables S4-S9) are reproduced only with α = 1; we apply α as '
    'specified in their Eq. 5 and SI Eq. S1, which ensures national shares sum to the global SOS. The authors have '
    'been contacted.',
]


# ============================================================
# FIGURE SOURCE DATA (MODEL v3.0.0: compute / draw separation)
# ============================================================
# The AESA diagnostics D18, D21-D27 are drawn by figures/boundaries.py from the arrays written here
# (outputs/data/figure_source/<figure id>.json, figsource.py); this module draws nothing.
VARIANTS = ('LOW', 'REF', 'HIGH')


def write_figure_sources(B, hist, runs, mc_annual, b_ar, b_atp, res, sens_df, gfa, dwell):
    """Write the exact arrays (and the run-specific note text) of the diagnostics of the planetary-boundary layer:
    D18 every AESA sensitivity row, D21 the Monte Carlo fan with the AR base window, D22 the boundaries,
    D23 the annual LoE, D24 the headroom, D25 / D26 annual and cumulative carbon by demand band, D27 the variants
    (totals; maintenance is drawn as its own layer only in Fig3 and the band breakdowns, D25 and D26).
    Units: kt CO2e (carbon and boundaries) unless named otherwise."""
    acc = ('construction (A1–A5 and soil) plus maintenance (B2, B4) occurring each year, buildings built from 2026; '
           'later events and C1–C4 are committed after 2050' if B['TIME_RESOLVED']
           else 'whole life booked at construction')
    factor_note = (acc + '; ' + ('case-study factors held at 2025' if B['DECARB'] is None else
                   'A1–A3 of the case-study items decarbonised after Horup et al. 2025 (item-level mapping), A4–A5 '
                   'e^(−0.01 (t − 2025)) after Resch et al. 2021, C1–C4 and soil at 2025'))
    fy = np.asarray(B['forecast_years'])
    py = fy[fy >= PB_YEARS[0]]
    bar_, batp_ = b_ar.loc[py].values, b_atp.loc[py].values
    pair = SOURCE_PAIRS[SOURCE_PAIR]
    ratio = 100 * res['B_AtP_over_B_AR']['min']
    cap = (f"Boundaries: {pair['label']}, SOS {pair['sos']:.3g} and I_glob {pair['i_glob']:.3g} kg CO₂e per year; "
           f"AR: Horup et al. 2025 Eq. 1 (base {AR_BASE_WINDOW[0]}–{AR_BASE_WINDOW[1]}); AtP: Hjalsted et al. 2021 "
           f"Eqs. 5–6 (GDP per capita, PPP, {res['components']['base_year_b']}); AtP is {ratio:.1f}% of AR in every "
           f"year (static design). Carbon: {factor_note}.")
    bands_c, total_c = B['fig_bands']['carbon']           # [(label, kt per year 2026-2050, band id)], total kt
    if [b for _, _, b in bands_c] != list(N.BANDS_IN_SCOPE):
        raise SystemExit('boundaries: the projection carbon bands do not match naming.BANDS_IN_SCOPE.')
    bands = {b: np.asarray(v, float) for _, v, b in bands_c}
    total_c = np.asarray(total_c, float)

    # ---- D25 / D26: carbon by demand band vs the boundaries (annual; cumulative from 2026) ----
    figsource.write('D25_annual_carbon_by_band', years=py, band_ids=list(N.BANDS_IN_SCOPE), bands_kt=bands,
                    net_kt=total_c, B_AR_kt=bar_ / M6, B_AtP_kt=batp_ / M6, caption=cap)
    figsource.write('D26_cumulative_carbon_by_band', years=py, band_ids=list(N.BANDS_IN_SCOPE),
                    bands_cum_kt={b: np.cumsum(v) for b, v in bands.items()}, net_cum_kt=np.cumsum(total_c),
                    B_AR_cum_kt=np.cumsum(bar_) / M6, B_AtP_cum_kt=np.cumsum(batp_) / M6, caption=cap)

    # ---- D27: the variants vs the boundaries --------------------------------------------------
    m = mc_annual[mc_annual.scenario == 'REF'].set_index('year')
    figsource.write('D27_variants_vs_boundaries', years=py, variants=list(VARIANTS),
                    annual_kt={k: runs[k]['I'].loc[py].values / M6 for k in VARIANTS},
                    cumulative_kt={k: float(runs[k]['I'].loc[py].sum() / M6) for k in VARIANTS},
                    mc_years=m.index.values, mc_p5_kt=m['I_sec_kgCO2e_p5'].values / M6,
                    mc_p95_kt=m['I_sec_kgCO2e_p95'].values / M6, B_AR_kt=bar_ / M6, B_AtP_kt=batp_ / M6,
                    B_AR_cum_kt=float(bar_.sum() / M6), B_AtP_cum_kt=float(batp_.sum() / M6), caption=cap)

    # ---- D21: Monte Carlo fan with the AR base window ------------------------------------------
    # the base-window history is the same series as the 'history' rows of aesa/annual.csv
    hb = hist.loc[AR_BASE_WINDOW[0]:AR_BASE_WINDOW[1], 'I_sec_kg']
    figsource.write('D21_fan_and_boundaries', base_window=list(AR_BASE_WINDOW), history_years=hb.index.values,
                    history_kt=hb.values / M6, mc_years=m.index.values,
                    **{f'{k}_{q}_kt': m[f'{k}_kgCO2e_{q}'].values / M6
                       for k in ('I_sec', 'B_AR', 'B_AtP') for q in ('p5', 'p50', 'p95')})

    # ---- D22: the boundaries -------------------------------------------------------------------
    yb = np.arange(T0, PB_YEARS[1] + 1)
    pm = aesa.population_modifier(B['df_forecast']['PopTotal_50th'].values[:len(yb)],
                                  world_population(list(yb)).values, res['components']['P_NZ_t0'],
                                  res['components']['P_W_t0'])
    c = res['components']
    tab = [['SOS (kg CO₂e per year)', f"{c['SOS_kg']:.3g}"], ['I_glob (kg CO₂e per year)', f"{c['I_glob_kg']:.3g}"],
           [f'Ī_sec,base {AR_BASE_WINDOW[0]}–{AR_BASE_WINDOW[1]} (kt/yr)', f"{c['I_sec_base_kg'] / M6:,.1f}"],
           [f"α (b = {c['base_year_b']}, PPP)", f"{c['alpha']:.4f}"],
           ['g_W / g_NZ', f"{c['g_W_over_g_NZ']:.4f}"], ['s_sec', f"{c['s_sec']:.7f}"],
           ['B_AtP / B_AR (every year)', f"{res['B_AtP_over_B_AR']['min']:.4f}"]]
    figsource.write('D22_boundaries', years=yb, B_AR_kt=b_ar.loc[yb].values / M6, B_AtP_kt=b_atp.loc[yb].values / M6,
                    population_modifier=np.asarray(pm, float), T0=T0, table=tab, pair_label=pair['label'],
                    atp_pct_of_ar=ratio)

    # ---- D23: annual level of exceedance by variant ----------------------------------------------
    d23 = {}
    for k in ('AR', 'AtP'):
        bb = b_ar if k == 'AR' else b_atp
        for name in VARIANTS:
            mm = mc_annual[mc_annual.scenario == name].set_index('year')
            d23[f'{name}_{k}'] = dict(mc_years=mm.index.values, p5=mm[f'LoE_{k}_p5'].values,
                                      p95=mm[f'LoE_{k}_p95'].values,
                                      loe=(runs[name]['I'].loc[py] / bb.loc[py]).values)
    figsource.write('D23_annual_loe', years=py, variants=list(VARIANTS), loe=d23,
                    atp_over_ar=res['B_AtP_over_B_AR']['min'], pair_label=pair['label'], factor_note=factor_note)

    # ---- D24: headroom -------------------------------------------------------------------------------
    I = runs['REF']['I'].loc[py]
    g = gfa.loc[py]
    d = dwell.loc[py]
    figsource.write('D24_headroom', years=py,
                    intensity=dict(reference=(I / g).values, fit_AR=(b_ar.loc[py] / g).values,
                                   fit_AtP=(b_atp.loc[py] / g).values),                    # kg CO2e per m2
                    floor_area=dict(reference=(g / M6).values, fit_AR=(b_ar.loc[py] / (I / g) / M6).values,
                                    fit_AtP=(b_atp.loc[py] / (I / g) / M6).values),        # Mm2 per year
                    per_dwelling=dict(reference=(I / d / 1e3).values, fit_AR=(b_ar.loc[py] / d / 1e3).values,
                                      fit_AtP=(b_atp.loc[py] / d / 1e3).values),           # t CO2e per dwelling
                    pair_label=pair['label'], factor_note=factor_note)

    # ---- D18: every AESA sensitivity row ---------------------------------------------------------------
    s = sens_df[~sens_df['case'].isin(['reference']) & ~sens_df['case'].str.startswith('note')]
    ref = sens_df.set_index('case').loc['reference']
    figsource.write('D18_aesa_sensitivity',
                    rows=s[['case', 'label', 'cum_LoE_AR', 'cum_LoE_AtP', 'AR_vs_ref_pct', 'AtP_vs_ref_pct']]
                    .reset_index(drop=True),
                    reference=dict(cum_LoE_AR=float(ref['cum_LoE_AR']), cum_LoE_AtP=float(ref['cum_LoE_AtP'])))


if __name__ == '__main__':
    main()
