"""
PLANETARY-BOUNDARY LAYER (AESA, climate change) on top of the model outputs
===========================================================================
Compares the sector's embodied carbon (A1-A5, B2, B4, C1-C4 + soil carbon
loss, booked in the construction year; 2026-2050) with a share of a global
carrying capacity for climate change, allocated by two principles reported as
a range and never averaged:

  AR   acquired rights   Horup et al. (2025), Sci. Total Environ. 966, 178780, Eq. (1)
  AtP  ability to pay    Hjalsted et al. (2021), J. Ind. Ecol. 25, 6-19, Eqs. (5)-(6), SI Eq. S1

Static carrying capacity: SOS, I_glob, GDP per capita and the sector share are
held fixed; the boundaries move only with New Zealand and world population.
The model itself is not changed: Boss.py, MonteCarlo.py and engine.py are only
called. Equations: aesa.py. Every constant below carries its source.

Writes outputs/pb_annual.csv, pb_mc_annual.csv, pb_sensitivity.csv,
pb_results.json and figures *_pb, pb_1..pb_5 (outputs/figures/ when
PATHWAY_SAVE_FIGURES=1, as run_all.py sets).

    python PB.py
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
import matplotlib
if os.environ.get('PATHWAY_SAVE_FIGURES') == '1':
    matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
from scipy.interpolate import PchipInterpolator  # noqa: E402

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'tools'))
import aesa  # noqa: E402
import Boss  # noqa: E402
import MonteCarlo as MC  # noqa: E402
import validation  # noqa: E402

DATA_DIR = os.path.join(ROOT_DIR, 'data')
OUT_DIR = os.path.join(ROOT_DIR, 'outputs')
FIG_DIR = os.path.join(OUT_DIR, 'figures')
SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'
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
_factor_note = ''                     # set from the Boss run in figures()
AR_COLOR, ATP_COLOR = '#1F5FA8', '#C2571A'   # validated pair (dataviz validator, light mode)
HALO = [pe.Stroke(linewidth=4, foreground='white'), pe.Normal()]
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


def historical_emissions(B, years, after=HIST_RATE_AFTER_LAST_CENSUS):
    """Sector emissions in past years (kg CO2e), same scope, factors and soil
    convention as the projection: built floor area by typology (consents x
    completion rate) x material intensity, plus soil on the non-replacement
    share of the floor area (engine.forward with soil_on_replacement=False)."""
    typ = list(B['typ_names'])
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
                       else f"long run {Boss.NET_REPLACEMENT_WINDOW[0]}-{Boss.NET_REPLACEMENT_WINDOW[1]}")
        else:
            raise ValueError(f'No census interval for {y}.')
    rate = pd.Series(rate, index=list(years))
    size = gfa / units
    soil_free = (rate * prev * (1.0 - rv) * size).clip(lower=0.0)
    soil_share = 1.0 - soil_free / gfa
    mat = sum(g[t] * (B['T_BASELINE_2025'][t] - B['SOIL_INTENSITY'][t]) for t in typ)
    soil = sum(g[t] * B['SOIL_INTENSITY'][t] for t in typ) * soil_share
    soil_all = sum(g[t] * B['SOIL_INTENSITY'][t] for t in typ)
    return pd.DataFrame(dict(I_sec_kg=mat + soil, materials_kg=mat, soil_kg=soil, soil_share=soil_share,
                             net_replacement_rate=rate, rate_source=src, gfa_m2=gfa,
                             I_soil_on_all_kg=mat + soil_all))


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
    c = Boss.load_consents()
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
    RESULTS.md): annual carbon and the NZ population path of each full Boss run."""
    import replacement_scenarios as RS
    out = {}
    for key, label, settings in RS.SCENARIOS:
        B = validation.run_boss(**settings)
        fy = np.asarray(B['forecast_years'])
        out[key] = dict(label=label, settings=settings,
                        I=pd.Series(B['carbon_total_typ'].sum(axis=1).values, index=fy),
                        pop=pd.Series(B['df_forecast']['PopTotal_50th'].values, index=fy))
    return out


def mc_runs(fy):
    """Re-run every saved Monte Carlo draw of each MC scenario through
    MonteCarlo.project() from its saved parameters (MonteCarlo.py unchanged);
    each draw must reproduce its saved outputs to MC_REL_TOL. Returns, per
    scenario, the annual carbon (draws x years) and NZ population (draws x years)."""
    out = {}
    for name, settings in MC.MC_SCENARIOS:
        with contextlib.redirect_stdout(io.StringIO()):
            su = MC.build_setup(settings)
        path = os.path.join(OUT_DIR, f'montecarlo_draws_{name}.csv')
        d = pd.read_csv(path)
        X = d[MC.PARAMS].to_numpy(float)
        Y = d[MC.OUTPUTS].to_numpy(float)
        carbon = np.empty((len(d), len(fy)))
        pop = np.empty((len(d), len(fy)))
        worst = 0.0
        for j in range(len(d)):
            o = MC.project(su, dict(zip(MC.PARAMS, X[j])))
            y = MC.summarise(o)
            worst = max(worst, float(np.max(np.abs(y - Y[j]) / np.maximum(np.abs(Y[j]), 1e-12))))
            carbon[j] = o['carbon']
            pop[j] = su['pop50'] + MC.interp_z(X[j, 0], MC.Z_KNOTS, su['spreads'])
            # the population path is the one the draw used: hh x S = pop
            if not np.allclose(o['hh'] * o['S'], pop[j], rtol=1e-12, atol=0):
                raise SystemExit(f'MC {name} draw {j}: population path not reproduced.')
        if worst > MC_REL_TOL:
            raise SystemExit(f'MC {name}: re-run draws differ from {os.path.basename(path)} by {worst:.1e} '
                             f'(> {MC_REL_TOL:g}); MC outputs are stale - rerun MonteCarlo.py.')
        print(f'  MC {name}: {len(d):,} draws re-run, max relative difference vs saved outputs {worst:.1e} (OK)')
        out[name] = dict(carbon=carbon, pop=pop)
    importlib.reload(Boss)
    return out


# ============================================================
# MAIN
# ============================================================
def main():
    t_start = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    B = validation.run_boss()
    fy = np.asarray(B['forecast_years'])                     # 2025..2050
    years_b = list(range(T0, PB_YEARS[1] + 1))
    pair = SOURCE_PAIRS[SOURCE_PAIR]

    # ---- sector history and base -------------------------------------------
    hist = historical_emissions(B, range(1992, 2026))
    hist_long = historical_emissions(B, range(1992, 2026), after='long_run')
    i_base = aesa.mean_over(hist['I_sec_kg'], AR_BASE_WINDOW)
    i_base_5 = aesa.mean_over(hist['I_sec_kg'], AR_BASE_WINDOW_SENS)
    i_base_long = aesa.mean_over(hist_long['I_sec_kg'], AR_BASE_WINDOW)
    i_base_soil_all = aesa.mean_over(hist['I_soil_on_all_kg'], AR_BASE_WINDOW)

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
    annual.to_csv(os.path.join(OUT_DIR, 'pb_annual.csv'), index=False)
    ref_I = runs['S3-10']['I']
    if not np.allclose(ref_I.values, B['carbon_total_typ'].sum(axis=1).values, rtol=1e-12):
        raise SystemExit('S3-10 scenario run differs from the central Boss run.')
    cum_det = {k: dict(label=r['label'], I_kt=float(r['I'].loc[slice(*PB_YEARS)].sum() / M6),
                       LoE_AR=cum(r['I'], b_ar), LoE_AtP=cum(r['I'], b_atp)) for k, r in runs.items()}

    # ---- Monte Carlo ---------------------------------------------------------
    print('PB: Monte Carlo (re-run from saved draws)')
    mc = mc_runs(fy)
    mc_rows, mc_cum = [], {}
    sel = (fy >= PB_YEARS[0]) & (fy <= PB_YEARS[1])
    pw_f = p_w.reindex(fy).values
    for name, m in mc.items():
        if not np.allclose(m['pop'][:, 0], p_nz.loc[T0], rtol=1e-12):
            raise SystemExit(f'MC {name}: draws do not share the observed {T0} population.')
        bar = aesa.boundary_ar(pair['sos'], i_base, pair['i_glob'], m['pop'], pw_f, p_nz.loc[T0], p_w.loc[T0])
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
        mc_cum[name] = {f'LoE_AR_p{p}': float(np.percentile(ca, p)) for p in MC_PCT}
        mc_cum[name].update({f'LoE_AtP_p{p}': float(np.percentile(ct, p)) for p in MC_PCT})
        mc_cum[name]['n_draws'] = int(len(ca))
    mc_annual = pd.DataFrame(mc_rows)
    mc_annual.to_csv(os.path.join(OUT_DIR, 'pb_mc_annual.csv'), index=False)

    # ---- deterministic sensitivities (reference scenario S3-10) -------------
    def cum_pair(pair_key=SOURCE_PAIR, ib=i_base, cp=comp, ssec=s_sec, pnz=p_nz):
        a, t = boundaries(pair_key, ib, cp, ssec, pnz, p_w)
        return cum(ref_I, a), cum(ref_I, t)
    ref_ar, ref_atp = cum_pair()
    sens = [('reference', 'Reference: pair A, PPP 2021 int-$, base 2016-2025, model population, mean of ratios',
             ref_ar, ref_atp),
            ('i_source_pair', f"(i) SOS/I_glob pair C: {SOURCE_PAIRS['C']['label']}", *cum_pair(pair_key='C')),
            ('ii_gdp_measure', f'(ii) GDP per capita, current US$ ({GDP_MEASURE_SENS}), b = {b_year}',
             *cum_pair(cp=comp_sens)),
            ('iii_base_window', f'(iii) AR base window {AR_BASE_WINDOW_SENS[0]}-{AR_BASE_WINDOW_SENS[1]} (5 yr, as Horup)',
             *cum_pair(ib=i_base_5)),
            ('iv_pop_statsnz', '(iv) NZ population: raw Stats NZ 2024-base median (no 2025 observation, no nowcast)',
             *cum_pair(pnz=nz_population_alt('statsnz_median', years_b))),
            ('iv_pop_wpp', '(iv) NZ population: WPP 2024 probabilistic median, New Zealand',
             *cum_pair(pnz=nz_population_alt('wpp_median', years_b))),
            ('v_ssec', '(v) s_sec with FCE share as ratio of sums', ref_ar,
             cum_pair(ssec=ss['s_sec_ratio_of_sums'])[1]),
]
    # carbon-factor rows: the other decarbonisation mode, and (decarbonised runs) the
    # STEEL class at the steel-profile rate; boundaries unchanged, I_sec re-run
    b_ar_ref, b_atp_ref = boundaries(SOURCE_PAIR, i_base, comp, s_sec, p_nz, p_w)

    def cum_I(**kw):
        Bx = validation.run_boss(**kw)
        I = pd.Series(Bx['carbon_total_typ'].sum(axis=1).values, index=np.asarray(Bx['forecast_years']))
        return cum(I, b_ar_ref), cum(I, b_atp_ref)
    if Boss.DECARB_MODE == 'none':
        sens.append(('vi_decarb', '(vi) Materials decarbonised, A1-A3 (Horup et al. 2025, SI Table S4)',
                     *cum_I(DECARB_MODE='horup_material')))
    else:
        sens.append(('vi_frozen', '(vi) Frozen technology: 2025 factors held (no decarbonisation)',
                     *cum_I(DECARB_MODE='none')))
        sens.append(('vii_steel_profile', '(vii) STEEL class at the steel-profile rate (Horup SI Table S4)',
                     *cum_I(DECARB_STEEL='steel_profile')))
    sens.append(('note_soil_long_run', 'Note (not in tornado): history 2024-25 at the long-run net replacement rate',
                 *cum_pair(ib=i_base_long)))
    sens_df = pd.DataFrame(sens, columns=['case', 'label', 'cum_LoE_AR', 'cum_LoE_AtP'])
    sens_df['AR_vs_ref_pct'] = 100 * (sens_df['cum_LoE_AR'] / ref_ar - 1)
    sens_df['AtP_vs_ref_pct'] = 100 * (sens_df['cum_LoE_AtP'] / ref_atp - 1)
    sens_df.to_csv(os.path.join(OUT_DIR, 'pb_sensitivity.csv'), index=False)

    # ---- results JSON ---------------------------------------------------------
    gfa = pd.Series(B['results']['50th']['total'], index=fy)
    dwell = pd.Series(B['engine_out']['50th']['dwell_in_scope'], index=fy)
    res = dict(
        settings=dict(SOURCE_PAIR=SOURCE_PAIR, T0=T0, PB_YEARS=list(PB_YEARS), AR_BASE_WINDOW=list(AR_BASE_WINDOW),
                      AR_BASE_WINDOW_SENS=list(AR_BASE_WINDOW_SENS), HIST_RATE_AFTER_LAST_CENSUS=HIST_RATE_AFTER_LAST_CENSUS,
                      GDP_MEASURE=GDP_MEASURE, GDP_MEASURE_SENS=GDP_MEASURE_SENS, WDI_COVERAGE_MIN=WDI_COVERAGE_MIN,
                      SSEC_WINDOW=list(SSEC_WINDOW), SSEC_FCE_SHARE=SSEC_FCE_SHARE, POP_NZ_SOURCE=POP_NZ_SOURCE,
                      DECARB_MODE=Boss.DECARB_MODE, DECARB_STEEL=Boss.DECARB_STEEL),
        source_pairs=SOURCE_PAIRS,
        components=dict(SOS_kg=pair['sos'], I_glob_kg=pair['i_glob'], pair_label=pair['label'],
                        I_sec_base_kg=i_base, I_sec_base_window=list(AR_BASE_WINDOW),
                        I_sec_base_5yr_kg=i_base_5, I_sec_base_long_run_2024_25_kg=i_base_long,
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
        deterministic=cum_det, mc=mc_cum,
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
            mc_base='In the Monte Carlo the boundaries vary only with each draw\'s NZ population path; I_sec,base '
                    'is the central historical estimate in every draw (it does not co-vary with the draw\'s carbon '
                    'factors, completion rate or dwelling size).'))
    with open(os.path.join(OUT_DIR, 'pb_results.json'), 'w') as f:
        json.dump(res, f, indent=2, default=float)

    print(f"\nPB layer ({pair['label']}; b = {b_year}): I_base {i_base / M6:,.1f} kt/yr | "
          f"B_AR 2026 {b_ar.loc[2026] / M6:,.1f} kt, 2050 {b_ar.loc[2050] / M6:,.1f} kt | "
          f"B_AtP 2026 {b_atp.loc[2026] / M6:,.2f} kt, 2050 {b_atp.loc[2050] / M6:,.2f} kt | "
          f"B_AtP/B_AR {ratio.min():.4f}")
    print(f"  alpha(b) {comp['alpha']:.4f}; alpha({ALPHA_CHECK_YEAR}) current US$ "
          f"{alpha_check[GDP_MEASURE_SENS]['alpha']:.4f} vs Hjalsted {ALPHA_HJALSTED_2017}; s_sec {s_sec:.7f}")
    print(f"  cumulative LoE 2026-2050, S3-10: AR {cum_det['S3-10']['LoE_AR']:.2f} "
          f"(MC p5-p95 {mc_cum['S3-10']['LoE_AR_p5']:.2f}-{mc_cum['S3-10']['LoE_AR_p95']:.2f}); "
          f"AtP {cum_det['S3-10']['LoE_AtP']:.1f} "
          f"(MC {mc_cum['S3-10']['LoE_AtP_p5']:.1f}-{mc_cum['S3-10']['LoE_AtP_p95']:.1f})")

    figures(B, hist, runs, mc, mc_annual, b_ar, b_atp, res, sens_df, gfa, dwell)
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
        ('Sector impact', 'the model\'s embodied carbon as scoped (A1-A5, B2, B4, C1-C4 + soil carbon loss), all '
         'booked in the construction year', 'DECISION (author); construction-year booking of B2/B4/C is a '
         'limitation to be revisited'),
        ('Carbon factors over time', f"Boss.DECARB_MODE = '{Boss.DECARB_MODE}'"
         + ('' if Boss.DECARB_MODE == 'none' else ' (A1-A3 of mapped materials, Horup et al. 2025)')
         + '; history and the AR base always at 2025 factors', 'DECISION (author); see the Boss register'),
        ('Allocation principles', 'acquired rights (Horup et al. 2025 Eq. 1) and ability to pay (Hjalsted et al. '
         '2021 Eqs. 5-6, SI S1), reported as a range, never averaged; the egalitarian-economic (EQ) principle of '
         'the earlier manuscript is not used', 'DECISION (author); LITERATURE'),
        ('SOS / I_glob pair', f"{SOURCE_PAIR}: {pa['label']}, SOS {pa['sos']:.3g}, I_glob {pa['i_glob']:.3g} kg "
         f"CO2-eq/yr; sensitivity C: {pc['label']}, SOS {pc['sos']:.3g}", 'DECISION (author) among LITERATURE '
         'values (Bjørn & Hauschild 2015, ESM2); see the source check'),
        ('Period and base year', f'{PB_YEARS[0]}-{PB_YEARS[1]}; t0 = {T0}', 'DECISION (author)'),
        ('AR base window', f'{AR_BASE_WINDOW[0]}-{AR_BASE_WINDOW[1]} (sensitivity {AR_BASE_WINDOW_SENS[0]}-'
         f'{AR_BASE_WINDOW_SENS[1]}, 5 yr as Horup et al. 2025)', 'DECISION (author); LITERATURE for the 5-yr row'),
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
        ('NZ population', 'the model\'s paths (central; each Monte Carlo draw); sensitivities: raw Stats NZ '
         '2024-base median (PCHIP on level, dated as above) and the WPP 2024 New Zealand median',
         'DATA (model); DECISION'),
        ('Monte Carlo', 'boundaries recomputed per draw from the draw\'s NZ population; I_sec,base held at the '
         'central estimate', 'DECISION (author)'),
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
    'B2, B4 and C1-C4 are booked in the construction year, so the impact of 2026-2050 includes future '
    'maintenance and end-of-life emissions of the buildings built in those years (to be revisited).',
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
    'outputs/pb_results.json).',
    'Monte Carlo: I_sec,base is the central historical estimate in every draw; it does not co-vary with the '
    'draw\'s carbon factors, completion rate or dwelling size (a co-varying base would cancel the factor '
    'uncertainty in LoE_AR).',
]


# ============================================================
# FIGURES
# ============================================================
def _save(fig, name):
    if SAVE_FIGURES:
        os.makedirs(FIG_DIR, exist_ok=True)
        fig.savefig(os.path.join(FIG_DIR, f'{name}.png'), dpi=130, bbox_inches='tight')
        plt.close(fig)


def _boundary_lines(ax, years, b_ar, b_atp, scale=M6, label=True, cumulative=False):
    """AR (solid) and AtP (dashed) boundary lines with a white halo and the range
    between them shaded; direct labels at the right end."""
    a = np.asarray(b_ar, float) / scale
    t = np.asarray(b_atp, float) / scale
    if cumulative:
        a, t = np.cumsum(a), np.cumsum(t)
    ax.fill_between(years, t, a, color='#7F8C8D', alpha=0.18, lw=0,
                    label='range between the two principles' if label else None)
    ax.plot(years, a, color=AR_COLOR, lw=2.2, path_effects=HALO,
            label='boundary, acquired rights (AR)' if label else None)
    ax.plot(years, t, color=ATP_COLOR, lw=2.2, ls='--', path_effects=HALO,
            label='boundary, ability to pay (AtP)' if label else None)
    for v, c, nm in ((a, AR_COLOR, 'AR'), (t, ATP_COLOR, 'AtP')):
        ax.annotate(f'{nm} {v[-1]:,.0f}' if v[-1] >= 10 else f'{nm} {v[-1]:,.1f}', (years[-1], v[-1]),
                    xytext=(4, 0), textcoords='offset points', va='center', fontsize=8, color='#333333')


def figures(B, hist, runs, mc, mc_annual, b_ar, b_atp, res, sens_df, gfa, dwell):
    global _factor_note
    _factor_note = ('case-study factors held at 2025' if B['DECARB'] is None else
                   'A1-A3 of mapped materials decarbonised after Horup et al. 2025; other stages, unmapped '
                   'materials and soil at 2025')
    fy = np.asarray(B['forecast_years'])
    py = fy[fy >= PB_YEARS[0]]
    typ = list(B['typ_names'])
    colors = B['stack_colors']
    bar_, batp_ = b_ar.loc[py].values, b_atp.loc[py].values
    pair = SOURCE_PAIRS[SOURCE_PAIR]
    cap = (f"Boundaries: {pair['label']}, SOS {pair['sos']:.3g} and I_glob {pair['i_glob']:.3g} kg CO₂e/yr; "
           f"AR = Horup et al. 2025 Eq. 1 (base {AR_BASE_WINDOW[0]}-{AR_BASE_WINDOW[1]}); AtP = Hjalsted et al. "
           f"2021 Eqs. 5-6 (GDP per capita PPP {res['components']['base_year_b']}). Both share one linear axis; "
           f"AtP is {100 * res['B_AtP_over_B_AR']['min']:.1f}% of AR in every year (static design), so it lies near the axis. "
           f"Carbon: {_factor_note}.")

    # ---- boss_05_annual_carbon_pb ------------------------------------------
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(18, 6.4))
    ct = B['carbon_total_typ'].loc[py]
    Boss.stack_typologies(a1, py, [ct[n] / M6 for n in typ], labels=typ, colors=colors, alpha=0.85)
    _boundary_lines(a1, py, bar_, batp_)
    a1.set_ylabel('kt CO₂e per year'); a1.set_title('Annual embodied carbon by typology vs boundaries (2026-2050)')
    a1.legend(loc='upper right', fontsize=8); a1.grid(alpha=0.3); a1.set_xlim(2026, 2051.5)
    Boss.plot_demand_bands(a2, py, *B['fig_bands']['carbon'])
    _boundary_lines(a2, py, bar_, batp_, label=False)
    a2.set_ylabel('kt CO₂e per year'); a2.set_title('Annual embodied carbon by demand type vs boundaries')
    Boss.demand_legend(a2); a2.grid(alpha=0.3); a2.set_xlim(2026, 2051.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.text(0.5, 0.01, cap, ha='center', fontsize=8.5, style='italic', wrap=True)
    _save(fig, 'boss_05_annual_carbon_pb')

    # ---- boss_06_cumulative_carbon_pb ---------------------------------------
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(18, 6.4))
    cc = ct.cumsum()
    Boss.stack_typologies(a1, py, [cc[n] / M6 for n in typ], labels=typ, colors=colors, alpha=0.85)
    _boundary_lines(a1, py, bar_, batp_, cumulative=True)
    a1.set_ylabel('kt CO₂e, cumulative from 2026'); a1.set_title('Cumulative carbon by typology vs cumulative boundaries')
    a1.legend(loc='upper left', fontsize=8); a1.grid(alpha=0.3); a1.set_xlim(2026, 2051.5)
    Boss.plot_demand_bands(a2, py, [(l, np.cumsum(v), c) for l, v, c in B['fig_bands']['carbon'][0]],
                           np.cumsum(B['fig_bands']['carbon'][1]))
    _boundary_lines(a2, py, bar_, batp_, label=False, cumulative=True)
    a2.set_ylabel('kt CO₂e, cumulative from 2026'); a2.set_title('Cumulative carbon by demand type vs cumulative boundaries')
    Boss.demand_legend(a2); a2.grid(alpha=0.3); a2.set_xlim(2026, 2051.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.text(0.5, 0.01, cap.replace('annual', 'cumulative'), ha='center', fontsize=8.5, style='italic', wrap=True)
    _save(fig, 'boss_06_cumulative_carbon_pb')

    # ---- fig_scenarios_pb (carbon panels) -------------------------------------
    import figures_report as FR
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(17, 5.8), gridspec_kw=dict(width_ratios=[2, 1]))
    m = mc_annual[mc_annual.scenario == 'S3-10'].set_index('year')
    a1.fill_between(m.index, m['I_sec_kgCO2e_p5'] / M6, m['I_sec_kgCO2e_p95'] / M6, color='#C0392B', alpha=0.12,
                    label='reference MC 5-95%')
    for key, lab, _, col in FR.SCEN:
        I = runs[key]['I'].loc[py]
        a1.plot(py, I / M6, color=col, lw=2 if key == 'S3-10' else 1.3, label=lab)
    _boundary_lines(a1, py, bar_, batp_)
    a1.set_ylim(0, None); a1.set_xlim(2026, 2051.5)
    a1.set_title('Annual embodied carbon by scenario vs boundaries'); a1.set_ylabel('kt CO₂e per year')
    a1.grid(alpha=0.3); a1.legend(fontsize=7.5, loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=3)
    ks = [k for k, *_ in FR.SCEN]
    short = {'S1': 'low', 'S3-10': 'reference', 'S2': 'storyline', 'S2-held': 'high'}
    a2.bar(range(len(ks)), [runs[k]['I'].loc[py].sum() / M6 for k in ks], color=[c for *_, c in FR.SCEN])
    for v, c, ls, nm in ((bar_.sum() / M6, AR_COLOR, '-', 'AR'), (batp_.sum() / M6, ATP_COLOR, '--', 'AtP')):
        a2.axhline(v, color=c, ls=ls, lw=2, path_effects=HALO)
        a2.annotate(f'cumulative boundary {nm}: {v:,.0f} kt', (len(ks) - 0.5, v), xytext=(0, 3),
                    textcoords='offset points', ha='right', fontsize=8, color='#333333')
    a2.set_xticks(range(len(ks))); a2.set_xticklabels([short[k] for k in ks])
    a2.set_title('Cumulative carbon 2026-2050 vs cumulative boundaries'); a2.set_ylabel('kt CO₂e'); a2.grid(alpha=0.3, axis='y')
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.text(0.5, -0.02, cap + ' Boundaries are the same in every scenario (same population path).',
             ha='center', fontsize=8.5, style='italic', wrap=True)
    _save(fig, 'fig_scenarios_pb')

    # ---- mc_1_fan_pb -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 5.6))
    h = hist['I_sec_kg']
    ax.plot(h.index, h / M6, color='black', lw=2, label='history, same soil convention as the projection')
    ax.axvspan(AR_BASE_WINDOW[0] - 0.5, AR_BASE_WINDOW[1] + 0.5, color='#F1C40F', alpha=0.12,
               label=f'AR base window {AR_BASE_WINDOW[0]}-{AR_BASE_WINDOW[1]}')
    blue = MC.BLUE
    ax.fill_between(m.index, m['I_sec_kgCO2e_p5'] / M6, m['I_sec_kgCO2e_p95'] / M6, color=blue, alpha=0.15,
                    label='carbon, MC 5th-95th percentile')
    ax.plot(m.index, m['I_sec_kgCO2e_p50'] / M6, color=blue, lw=2, label='carbon, MC median')
    for k, c, ls, nm in (('B_AR', AR_COLOR, '-', 'AR'), ('B_AtP', ATP_COLOR, '--', 'AtP')):
        ax.fill_between(m.index, m[f'{k}_kgCO2e_p5'] / M6, m[f'{k}_kgCO2e_p95'] / M6, color=c, alpha=0.25, lw=0)
        ax.plot(m.index, m[f'{k}_kgCO2e_p50'] / M6, color=c, ls=ls, lw=2, path_effects=HALO,
                label=f'boundary {nm}, MC median and 5th-95th (population only)')
    ax.axvline(2025.5, color='grey', ls=':', lw=1)
    ax.set_xlim(1992, 2050); ax.set_ylim(0, None); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc='upper left')
    ax.set_ylabel('kt CO₂e per year')
    ax.set_title('Monte Carlo (reference S3-10): embodied carbon fan and the two boundaries')
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    spread = 100 * float(np.max(np.abs(np.r_[m['B_AR_kgCO2e_p95'] / m['B_AR_kgCO2e_p50'] - 1,
                                              m['B_AR_kgCO2e_p5'] / m['B_AR_kgCO2e_p50'] - 1])))
    fig.text(0.5, 0.01, 'History 1992-2025 here applies soil only to non-replacement floor area (as the projection), '
             'unlike mc_1_fan (soil on all floor area). Boundary bands vary only with each draw\'s NZ population '
             f'(5th-95th within {spread:.1f}% of the median in every year).',
             ha='center', fontsize=8.5, style='italic', wrap=True)
    _save(fig, 'mc_1_fan_pb')

    # ---- pb_1_boundaries ------------------------------------------------------------
    yb = np.arange(T0, PB_YEARS[1] + 1)
    fig = plt.figure(figsize=(17, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 1, 1.1])
    a = fig.add_subplot(gs[0])
    a.plot(yb, b_ar.loc[yb] / M6, color=AR_COLOR, lw=2.2, label='B_AR (acquired rights)')
    a.plot(yb, b_atp.loc[yb] / M6, color=ATP_COLOR, lw=2.2, ls='--', label='B_AtP (ability to pay)')
    a.set_yscale('log'); a.grid(alpha=0.3, which='both'); a.legend(fontsize=8)
    for s, c in ((b_ar, AR_COLOR), (b_atp, ATP_COLOR)):
        for y in (T0, PB_YEARS[1]):
            a.annotate(f'{s.loc[y] / M6:,.1f}', (y, s.loc[y] / M6), xytext=(0, 6), textcoords='offset points',
                       ha='center', fontsize=8, color='#333333')
    a.set_ylabel('kt CO₂e per year (log scale)'); a.set_title('Boundaries 2025-2050')
    a = fig.add_subplot(gs[1])
    pm = aesa.population_modifier(B['df_forecast']['PopTotal_50th'].values[:len(yb)],
                                  world_population(list(yb)).values, res['components']['P_NZ_t0'],
                                  res['components']['P_W_t0'])
    a.plot(yb, pm, color='#333333', lw=2)
    a.axhline(1, color='grey', lw=0.8, ls=':')
    a.set_title('Population modifier [P_NZ(t)/P_NZ(2025)]·[P_W(2025)/P_W(t)]'); a.grid(alpha=0.3)
    a.set_ylabel('index, 2025 = 1')
    a = fig.add_subplot(gs[2]); a.axis('off')
    c = res['components']
    tab = [['SOS (kg CO₂e/yr)', f"{c['SOS_kg']:.3g}"], ['I_glob (kg CO₂e/yr)', f"{c['I_glob_kg']:.3g}"],
           [f'Ī_sec,base {AR_BASE_WINDOW[0]}-{AR_BASE_WINDOW[1]} (kt/yr)', f"{c['I_sec_base_kg'] / M6:,.1f}"],
           [f"α (b = {c['base_year_b']}, PPP)", f"{c['alpha']:.4f}"],
           ['g_W / g_NZ', f"{c['g_W_over_g_NZ']:.4f}"], ['s_sec', f"{c['s_sec']:.7f}"],
           ['B_AtP / B_AR (every year)', f"{res['B_AtP_over_B_AR']['min']:.4f}"]]
    t = a.table(cellText=tab, colLabels=['component', 'value'], loc='center', cellLoc='left', colWidths=[0.7, 0.3])
    t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.6)
    a.set_title('Components')
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.text(0.5, 0.01, f"{pair['label']}. Log axis: B_AtP is {100 * res['B_AtP_over_B_AR']['min']:.1f}% of B_AR in "
             'every year: both scale with P_NZ(t)/P_W(t) (static design), so their ratio is constant.',
             ha='center', fontsize=8.5, style='italic')
    _save(fig, 'pb_1_boundaries')

    # ---- pb_2_loe ----------------------------------------------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(16, 5.6), sharey=True)
    sc = [('S1', '#2E86AB', 'low (S1)'), ('S3-10', '#C0392B', 'reference (S3-10)'), ('S2', '#27AE60', 'storyline (S2)')]
    for a, k, ttl in ((ax[0], 'AR', 'Acquired rights'), (ax[1], 'AtP', 'Ability to pay')):
        for name, col, lab in sc:
            mm = mc_annual[mc_annual.scenario == name].set_index('year')
            a.fill_between(mm.index, mm[f'LoE_{k}_p5'], mm[f'LoE_{k}_p95'], color=col, alpha=0.15, lw=0)
            I = runs[name]['I'].loc[py]
            bb = b_ar if k == 'AR' else b_atp
            a.plot(py, I / bb.loc[py], color=col, lw=2, label=f'{lab}; band MC 5-95%')
        a.axhline(1, color='black', lw=1.2, ls='--', label='LoE = 1 (boundary)')
        a.set_yscale('log'); a.grid(alpha=0.3, which='both'); a.set_title(f'Level of exceedance, {ttl}')
        a.set_xlim(2026, 2050)
    ax[0].set_ylabel('LoE = annual carbon / boundary (log scale)'); ax[0].legend(fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.text(0.5, 0.01, f"{pair['label']}. Log axis: LoE_AtP is {1 / res['B_AtP_over_B_AR']['min']:.1f} x LoE_AR "
             'in every year. MC bands: within-scenario uncertainty (population, dwelling size, completion, carbon factors).',
             ha='center', fontsize=8.5, style='italic')
    _save(fig, 'pb_2_loe')

    # ---- pb_3_headroom -------------------------------------------------------------------
    I = runs['S3-10']['I'].loc[py]
    g = gfa.loc[py]
    d = dwell.loc[py]
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.6))
    a = ax[0]
    a.plot(py, I / g, color='black', lw=2, label='current intensity: I_sec(t) / GFA(t)')
    a.plot(py, b_ar.loc[py] / g, color=AR_COLOR, lw=2, label='intensity fitting B_AR: B_AR(t) / GFA(t)')
    a.plot(py, b_atp.loc[py] / g, color=ATP_COLOR, lw=2, ls='--', label='intensity fitting B_AtP: B_AtP(t) / GFA(t)')
    a.set_yscale('log'); a.set_ylabel('kg CO₂e per m² of new floor area (log)'); a.grid(alpha=0.3, which='both')
    a.set_title('Carbon intensity that fits each boundary'); a.legend(fontsize=8)
    a = ax[1]
    a.plot(py, g / M6, color='black', lw=2, label='projected floor area GFA(t)')
    a.plot(py, b_ar.loc[py] / (I / g) / M6, color=AR_COLOR, lw=2, label='GFA fitting B_AR at current intensity')
    a.plot(py, b_atp.loc[py] / (I / g) / M6, color=ATP_COLOR, lw=2, ls='--', label='GFA fitting B_AtP at current intensity')
    a.set_yscale('log'); a.set_ylabel('Mm² per year (log)'); a.grid(alpha=0.3, which='both')
    a.set_title('Floor area that fits each boundary'); a.legend(fontsize=8)
    a = ax[2]
    a.plot(py, I / d / 1e3, color='black', lw=2, label='carbon per new dwelling: I_sec(t) / dwellings(t)')
    a.plot(py, b_ar.loc[py] / d / 1e3, color=AR_COLOR, lw=2, label='B_AR(t) / dwellings(t)')
    a.plot(py, b_atp.loc[py] / d / 1e3, color=ATP_COLOR, lw=2, ls='--', label='B_AtP(t) / dwellings(t)')
    a.set_yscale('log'); a.set_ylabel('t CO₂e per new dwelling (log)'); a.grid(alpha=0.3, which='both')
    a.set_title('Boundary per new dwelling vs carbon per new dwelling'); a.legend(fontsize=8)
    for a in ax:
        a.set_xlim(2026, 2050)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.text(0.5, 0.01, 'Reference scenario S3-10, median demographics. I_sec(t): embodied carbon of the year\'s new '
             'floor area (kg CO₂e); GFA(t): in-scope floor area built (m²); dwellings(t): in-scope dwellings built '
             '(GFA / blended dwelling size).\nCurrent intensity = I_sec/GFA (' + _factor_note + '; also varies with '
             'mix and soil share). Fitting intensity = B_k/GFA; fitting floor area = B_k / (I_sec/GFA); per dwelling = '
             'B_k / dwellings. ' + pair['label'] + '.', ha='center', fontsize=8.5, style='italic')
    _save(fig, 'pb_3_headroom')

    # ---- pb_4_sensitivity (tornado) ---------------------------------------------------------
    s = sens_df[~sens_df['case'].isin(['reference']) & ~sens_df['case'].str.startswith('note')]
    fig, ax = plt.subplots(1, 2, figsize=(16, 5.2))
    ref = sens_df.set_index('case').loc['reference']
    for a, k, col, ttl in ((ax[0], 'AR', AR_COLOR, 'acquired rights'), (ax[1], 'AtP', ATP_COLOR, 'ability to pay')):
        v = s[f'cum_LoE_{k}'].values - ref[f'cum_LoE_{k}']
        order = np.argsort(np.abs(v))
        a.barh(range(len(s)), v[order], color=col, alpha=0.8)
        a.set_yticks(range(len(s))); a.set_yticklabels([s['label'].values[i] for i in order], fontsize=8)
        for i, j in enumerate(order):
            a.annotate(f"{s[f'cum_LoE_{k}'].values[j]:.2f} ({s[f'{k}_vs_ref_pct'].values[j]:+.1f}%)",
                       (max(v[j], 0.0), i), xytext=(4, 0), textcoords='offset points', ha='left', va='center',
                       fontsize=8)
        a.set_xlim(min(0.0, v.min()) - 0.05 * np.ptp(np.r_[v, 0]), v.max() + 0.35 * np.ptp(np.r_[v, 0]))
        a.axvline(0, color='black', lw=1)
        a.set_xlabel(f'change in cumulative LoE vs reference ({ref[f"cum_LoE_{k}"]:.2f})')
        a.set_title(f'Cumulative LoE 2026-2050, {ttl} (reference S3-10)'); a.grid(alpha=0.3, axis='x')
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.text(0.5, 0.01, 'One setting changed per row; labels show the cumulative LoE of that row. Rows that do not '
             'enter a principle (e.g. GDP measure for AR) show no change.', ha='center', fontsize=8.5, style='italic')
    _save(fig, 'pb_4_sensitivity')

    # ---- pb_5_demand_vs_boundary (supplementary) ------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 6))
    Boss.plot_demand_bands(ax, py, *B['fig_bands']['carbon'])
    _boundary_lines(ax, py, bar_, batp_)
    ax.set_ylabel('kt CO₂e per year'); ax.set_xlim(2026, 2051.5); ax.grid(alpha=0.3)
    ax.set_title('Annual carbon by demand type (in scope) vs the boundaries, reference S3-10')
    Boss.demand_legend(ax)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.text(0.5, 0.01, cap, ha='center', fontsize=8, style='italic', wrap=True)
    _save(fig, 'pb_5_demand_vs_boundary')
    if not SAVE_FIGURES:
        plt.show()


if __name__ == '__main__':
    main()
