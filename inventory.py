"""
EMISSIONS ACCOUNTING RULES (MODEL v3.1.0): which emissions a window of years counts, identically for the acquired-
rights base window (boundaries.py) and the projection 2026-2050 (projection.py, every run and Monte Carlo draw).

Scope in every rule: residential construction since B_SCOPE_START (1992); the pre-1992 stock is out of scope on both
sides (its soil and its replacements / repaints are counted in neither the base nor the projection).

Soil oxidation. The soil carbon lost on land converted in year t is emitted linearly over SOIL_OXIDATION_YEARS = 20
years, t .. t + 19 (IPCC 2006 Guidelines, Vol. 4, Ch. 2: default transition period D = 20 years for soil carbon
stock changes after land-use conversion).

  'inventory' (adopted)  a window counts ALL emissions occurring in it from all cohorts since 1992: the upfront
                         A1-A5 of its own construction, the soil oxidation of every conversion since 1992 that
                         occurs in it (the 20-year tails of earlier conversions included) and the replacements and
                         repaints (B2, B4) of every cohort since 1992 that occur in it. In the projection the
                         emissions of pre-2026 activity (soil tails of 2007-2025 conversions, B of the 1992-2025
                         cohorts) are the legacy: identical in every run, reported as their own band; the oxidation
                         of 2026-2050 conversions after 2050 is the committed component 'Soil, after 2050'.
  'instant'              soil at conversion; B of each window's own cohorts only (MODEL v3.0.0). Sensitivity.
  'cohort_window'        soil spread over 20 years, but only each window's own cohorts, on both sides (no legacy).
                         Sensitivity, deterministic only; rejected because the 10-year base window and the 25-year
                         projection window capture different shares of slow-release emissions.

Pure functions (numpy / pandas only); no model module is imported.
"""
import numpy as np
import pandas as pd

RULES = ('inventory', 'instant', 'cohort_window')
SOIL_OXIDATION_YEARS = 20          # IPCC (2006) Vol. 4 Ch. 2, default transition period D
B_SCOPE_START = 1992               # residential construction in scope since this year (both sides)


def check_rule(rule):
    if rule not in RULES:
        raise ValueError(f'Unknown ACCOUNTING {rule!r}: one of {RULES}.')
    return rule


def spreads_soil(rule):
    """True when soil is oxidised over SOIL_OXIDATION_YEARS ('inventory', 'cohort_window')."""
    return check_rule(rule) != 'instant'


def has_legacy(rule):
    """True when a window counts the emissions of earlier cohorts ('inventory')."""
    return check_rule(rule) == 'inventory'


# ------------------------------------------------------------------ soil oxidation in time ----
def soil_kernel(n, period=SOIL_OXIDATION_YEARS, first=1):
    """K[i, j] = share of the soil lost on land converted in model year i that is emitted in model year j (n years,
    consecutive): 1 / period for 0 <= j - i < period. Rows before `first` are zero (index 0 = 2025 is the observed
    anchor of the projection; the oxidation of conversions up to 2025 is the legacy, legacy_soil())."""
    K = np.zeros((n, n))
    for i in range(first, n):
        K[i, i:min(n, i + period)] = 1.0 / period
    return K


def spread(conv, period=SOIL_OXIDATION_YEARS, first=1):
    """Soil conversions by year (array (..., n)) -> (emitted within the n years (..., n), emitted after the last year
    (..., total over cohorts)); the conversions before `first` are dropped (neither emitted nor after)."""
    conv = np.asarray(conv, float)
    n = conv.shape[-1]
    K = soil_kernel(n, period, first)
    emit = conv @ K
    inside = K.sum(axis=1)                                        # share of each cohort emitted inside
    keep = np.arange(n) >= first
    after = (conv * np.where(keep, 1.0 - inside, 0.0)).sum(axis=-1)
    return emit, after


def emitted_in(conv_by_year, years, cohort_from, cohort_to=None, period=SOIL_OXIDATION_YEARS):
    """Soil oxidation occurring in each of `years` (Series) from the conversions of cohorts cohort_from..cohort_to
    (conv_by_year: Series indexed by conversion year, kg)."""
    c = conv_by_year.loc[cohort_from:cohort_to] if cohort_to is not None else conv_by_year.loc[cohort_from:]
    out = []
    for y in years:
        live = c[(c.index <= y) & (c.index > y - period)]
        out.append(float(live.sum()) / period)
    return pd.Series(out, index=list(years), dtype=float)


def tail_coverage(window, period=SOIL_OXIDATION_YEARS, scope_start=B_SCOPE_START):
    """Whether the history in scope holds every conversion whose oxidation reaches the window: the first conversion
    year needed is window[0] - period + 1 (1997 for a 2016 start)."""
    need = int(window[0]) - period + 1
    return dict(first_conversion_needed=need, scope_start=int(scope_start), covered=bool(need >= scope_start))


def window_soil(conv_by_year, window, rule, period=SOIL_OXIDATION_YEARS, scope_start=B_SCOPE_START):
    """Soil counted in each year of a base window (Series over the window years, kg) under `rule`:
    instant = conversions of the year; cohort_window = oxidation in the window of the window's conversions;
    inventory = oxidation in the window of every conversion since scope_start."""
    years = list(range(int(window[0]), int(window[1]) + 1))
    rule = check_rule(rule)
    if rule == 'instant':
        return conv_by_year.reindex(years).astype(float)
    if rule == 'cohort_window':
        return emitted_in(conv_by_year, years, window[0], window[1], period)
    return emitted_in(conv_by_year, years, scope_start, None, period)


def legacy_soil(conv_by_year, forecast_years, period=SOIL_OXIDATION_YEARS, scope_start=B_SCOPE_START):
    """Oxidation in each forecast year (array over forecast_years; the first year, the 2025 anchor, is 0) of the
    conversions scope_start .. forecast_years[0] (the history up to 2025)."""
    fy = np.asarray(forecast_years)
    s = emitted_in(conv_by_year, fy[1:], scope_start, int(fy[0]), period)
    return np.r_[0.0, s.values]


# ------------------------------------------------------------------ history: soil conversions ----
def history_rates(years, census_rates, long_run_rate, nr_window, after):
    """Net replacement rate of each history year: the census interval that holds it; after the last census, the
    last interval's rate carried ('recent') or the long-run rate ('long_run'). Returns (rates Series, sources)."""
    cr = census_rates.sort_values('y0')
    rate, src = [], []
    for y in years:
        w = cr[cr['y0'] <= y]
        if len(w) and y <= int(w['y1'].iloc[-1]):
            rate.append(float(w['rate'].iloc[-1])); src.append(f"{int(w['y0'].iloc[-1])}-{int(w['y1'].iloc[-1])}")
        elif y > int(cr['y1'].max()):
            last = cr.iloc[-1]
            rate.append(float(last['rate']) if after == 'recent' else long_run_rate)
            src.append(f"{int(last['y0'])}-{int(last['y1'])} carried" if after == 'recent'
                       else f"long run {nr_window[0]}-{nr_window[1]}")
        else:
            raise ValueError(f'No census interval for {y}.')
    return pd.Series(rate, index=list(years)), src


def history_soil(gfa_typ, units, rv_share, prev, census_rates, long_run_rate, nr_window, soil_int, years, after):
    """Soil lost on land converted in each history year (kg, conversion year): soil factor x the soil-bearing floor
    area = all built floor area minus the in-scope net replacement (net rate x last year's stock x (1 - RV share) x
    dwelling size; land already settled), the projection's convention (engine.forward, soil_on_replacement=False).
    Returns a DataFrame (soil_kg, soil_all_kg, soil_share, net_replacement_rate, rate_source, gfa_m2)."""
    years = list(years)
    typ = list(gfa_typ.columns)
    g = gfa_typ.loc[years, typ]
    gfa = g.sum(axis=1)
    rate, src = history_rates(years, census_rates, long_run_rate, nr_window, after)
    size = gfa / units.loc[years]
    soil_free = (rate * prev.loc[years] * (1.0 - rv_share.loc[years]) * size).clip(lower=0.0)
    soil_share = 1.0 - soil_free / gfa
    soil_all = sum(g[t] * soil_int[t] for t in typ)
    return pd.DataFrame(dict(soil_kg=soil_all * soil_share, soil_all_kg=soil_all, soil_share=soil_share,
                             net_replacement_rate=rate, rate_source=src, gfa_m2=gfa))


# ------------------------------------------------------------------ history: replacements and repaints ----
def legacy_b(gfa_hist, prof, factors, forecast_years, scope_start=B_SCOPE_START):
    """Replacement / repaint emissions in each forecast year (array; the 2025 anchor 0) of the cohorts built
    scope_start .. forecast_years[0] (the history to 2025), one typology: gfa_hist Series by construction
    year (m2), prof the event rows (Age, kg_per_m2), factors = events.row_factors(prof, forecast_years, ...)."""
    fy = np.asarray(forecast_years)
    age, kg = prof['Age'].to_numpy(int), prof['kg_per_m2'].to_numpy(float)
    out = np.zeros(len(fy))
    for c in range(int(scope_start), int(fy[0]) + 1):
        for j in range(1, len(fy)):
            hit = age == fy[j] - c
            if hit.any():
                out[j] += float(gfa_hist.loc[c]) * float((kg[hit] * factors[hit, j]).sum())
    return out
