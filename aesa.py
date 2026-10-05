"""Absolute environmental sustainability assessment (AESA): pure functions for
the planetary-boundary layer (PB.py). No data are read here; every function
takes arrays or scalars and returns arrays or scalars, so each equation can be
tested on its own.

Notation (units: impacts and boundaries in kg CO2-eq per year):
  SOS        global carrying capacity for climate change (safe operating space)
  I_glob     global annual impact, from the same source as SOS
  I_base     mean annual sector impact over the base window
  P_NZ, P_W  New Zealand and world population; t0 = base year of the modifier

Principles:
  acquired rights (AR): Horup et al. (2025), Sci. Total Environ. 966, 178780,
      Eq. (1), p. 4;
  ability to pay (AtP): Hjalsted et al. (2021), J. Ind. Ecol. 25, 6-19,
      Table 2 Eq. (5) (individual share) and Eq. (6) (final-consumption-
      expenditure upscaling), p. 11; scaling factor alpha: Supporting
      Information, Eq. S1.
"""
import numpy as np
import pandas as pd


# ============================================================
# Acquired rights (Horup et al. 2025, Eq. 1)
# ============================================================
def population_modifier(p_nz, p_w, p_nz0, p_w0):
    """[P_NZ(t) / P_NZ(t0)] x [P_W(t0) / P_W(t)]: the change in New Zealand's
    share of world population since t0 (Horup et al. 2025, Eq. 1). Equals 1 at t0."""
    return (np.asarray(p_nz, float) / p_nz0) * (p_w0 / np.asarray(p_w, float))


def boundary_ar(sos, i_base, i_glob, p_nz, p_w, p_nz0, p_w0):
    """Acquired-rights boundary (Horup et al. 2025, Eq. 1):

        B_AR(t) = SOS x (I_base / I_glob) x [P_NZ(t) / P_NZ(t0)] x [P_W(t0) / P_W(t)]

    The sector keeps its base-window share of the global impact, applied to
    the safe operating space, adjusted for the change in population share."""
    return sos * (i_base / i_glob) * population_modifier(p_nz, p_w, p_nz0, p_w0)


# ============================================================
# Ability to pay (Hjalsted et al. 2021, Eqs. 5-6 and S1)
# ============================================================
def world_gdp_per_capita(pop_c, gdp_pc_c):
    """g_W over the covered countries: sum(P_c g_c) / sum(P_c), i.e. the
    population-weighted mean of the same countries entering alpha (not a
    published world aggregate)."""
    pop_c, gdp_pc_c = np.asarray(pop_c, float), np.asarray(gdp_pc_c, float)
    return float((pop_c * gdp_pc_c).sum() / pop_c.sum())


def alpha(pop_c, gdp_pc_c):
    """Scaling factor alpha (Hjalsted et al. 2021, SI Eq. S1), which makes the
    individual ability-to-pay shares of all countries add up to SOS:

        alpha = 1 / sum_c [ (P_c / P_W) x (g_W / g_c) ],

    with P_W = sum_c P_c and g_W = sum_c P_c g_c / P_W over the same countries.
    This is S1 written with per-capita GDP: S1 reads
    1 / sum_c [ (GDP_W / GDP_c) (P_c / P_W)^2 ] with GDP totals, and
    (GDP_W / GDP_c)(P_c / P_W)^2 = (P_c / P_W)(g_W / g_c)."""
    pop_c, gdp_pc_c = np.asarray(pop_c, float), np.asarray(gdp_pc_c, float)
    p_w = pop_c.sum()
    g_w = world_gdp_per_capita(pop_c, gdp_pc_c)
    return float(1.0 / ((pop_c / p_w) * (g_w / gdp_pc_c)).sum())


def alpha_eq_s1(pop_c, gdp_total_c):
    """alpha exactly as printed in Hjalsted et al. (2021) SI Eq. S1, with GDP
    totals: 1 / sum_c [ (GDP_W / GDP_c) x (P_c / P_W)^2 ]. Used to test that
    alpha() is the same quantity."""
    pop_c, gdp_total_c = np.asarray(pop_c, float), np.asarray(gdp_total_c, float)
    return float(1.0 / ((gdp_total_c.sum() / gdp_total_c) * (pop_c / pop_c.sum()) ** 2).sum())


def sosos_ind_atp(sos, p_w, g_w, g_local, alpha_):
    """Individual share of the safe operating space, ability to pay
    (Hjalsted et al. 2021, Eq. 5):

        SoSOS_ind(t) = SOS / P_W(t) x (g_W / g_local) x alpha

    g_W and g_local are GDP per capita in the base year (held fixed: static design)."""
    return sos / np.asarray(p_w, float) * (g_w / g_local) * alpha_


def boundary_atp(sosos_ind, p_local, s_sec):
    """Sector boundary by final-consumption-expenditure upscaling
    (Hjalsted et al. 2021, Eq. 6):

        B_AtP(t) = SoSOS_ind(t) x P_local(t) x s_sec

    s_sec = the sector's share of final consumption expenditure."""
    return np.asarray(sosos_ind, float) * np.asarray(p_local, float) * s_sec


def sector_share(sector_value, gdp, fce_share_of_gdp):
    """s_sec = sector expenditure / national final consumption expenditure,
    with FCE = GDP x (FCE share of GDP)."""
    return sector_value / (gdp * fce_share_of_gdp)


# ============================================================
# Level of exceedance
# ============================================================
def loe(impact, boundary):
    """Annual level of exceedance LoE(t) = I(t) / B(t); > 1 means the boundary is exceeded."""
    return np.asarray(impact, float) / np.asarray(boundary, float)


def cumulative_loe(impact, boundary):
    """Cumulative level of exceedance over a period: sum I(t) / sum B(t)
    (a ratio of sums, not the mean of the annual ratios)."""
    return float(np.sum(impact) / np.sum(boundary))


def mean_over(series, window):
    """Mean of a year-indexed pandas Series over the inclusive window (y0, y1);
    raises if a year is missing."""
    y0, y1 = window
    s = series.loc[y0:y1]
    if len(s) != y1 - y0 + 1 or s.isna().any():
        raise ValueError(f'Series incomplete over {y0}-{y1}.')
    return float(s.mean())


def mid_year_to_end_of_year(values_at_mid_year, years):
    """Date a series observed at mid-year (1 July or 30 June) at 31 December of
    the same year, as the mean of the values at mid-year t and mid-year t+1.
    values_at_mid_year: pandas Series indexed by year. Returns a Series for the
    requested years (each needs t and t+1)."""
    v = values_at_mid_year
    years = [int(y) for y in years]
    return pd.Series((v.loc[years].values + v.loc[[y + 1 for y in years]].values) / 2.0, index=years)
