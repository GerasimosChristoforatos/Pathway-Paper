"""
Residential GFA & Embodied Carbon Projection, New Zealand 2026-2050
====================================================================
Bottom-up demographic model of new residential floor area and its embodied
carbon (A1-A5, B2, B4, C1-C4, plus soil carbon loss) by typology, demand type
and material.

    total floor area = new dwellings required x realised dwelling size
    new dwellings    = new households + vacancy allowance + replacement

All input data are read from DATA_DIR. Case-study carbon and occupancy factors
come from building_factors.py (run it first). Figures are plotted, never saved.
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from scipy import stats

# ============================================================
# CONFIGURATION
# ============================================================
DATA_DIR = 'data'
VERBOSE = False     # True also prints historical diagnostics (occupancy, calibration)
SHOW_PLOTS = True   # False: build nothing on screen (used by Diagnostics / Sensitivity)
FILE_CONSENTS = os.path.join(DATA_DIR, 'consentdata.xlsx')
FILE_POP_PROJ = os.path.join(DATA_DIR, 'popdata.xlsx')
FILE_POP_HIST = os.path.join(DATA_DIR, 'histpopdata.xlsx')          # [FIX e] authoritative annual ERP
FILE_HOUSEHOLDS_HIST = os.path.join(DATA_DIR, 'oldhouseholddata.xlsx')
FILE_HOUSEHOLDS_PROJ = os.path.join(DATA_DIR, 'Householddata.xlsx')
# [Route A] Population paired with the 2018-base household projection to derive
# household size. ADOPTED: the ORIGINAL 2018-base subnational release (national
# totals aligned to the 2020-base national projection), the regional set in
# place when the household projection was produced. Its implied household size
# falls smoothly (2.730 -> 2.705 -> 2.691 -> 2.674 -> 2.666 -> 2.670), as
# living-arrangement change would. The later UPDATE (national totals aligned to
# the 2022-base projection) revised population down for COVID migration without
# a matching household revision, giving an artificially steep early fall
# (2.730 -> 2.667). After rebasing on observed 2025 the two give near-identical
# shapes: S(2050) 2.582 vs 2.564; total GFA 2026-2050 80.31 vs 82.69 Mm2 (-2.9%).
# The update is kept as a sensitivity.
FILE_POP_SIZE_PAIR = os.path.join(DATA_DIR, 'subnational-population-projections-2018base-2048.xlsx')
# FILE_POP_SIZE_PAIR = os.path.join(DATA_DIR, 'subnational-population-projections-2018base-2048-update.xlsx')
POP_SIZE_PAIR_SHEET = 'Table 1'

POP_SHEET_PROJ = 'Table 1'
POP_SHEET_HIST = 'Table 1'

# ---------------------------------------------------------------------------
# POPULATION PERCENTILES
# ---------------------------------------------------------------------------
# Stats NZ's stochastic projection publishes percentiles of the population
# LEVEL and, separately, of ANNUAL GROWTH. Its own footnote: "percentiles are
# non-additive except the 50th percentile (median)". Summing the 5th-percentile
# growth of every year is therefore NOT the 5th-percentile population path: it
# assumes a 1-in-20 low year every year for 25 years. On this data it put the
# 2048 population at 5.27 M (5th) and 7.81 M (95th) against the published
# 6.04 M and 7.01 M, roughly doubling the width of the band.
# 'published_levels' (ADOPTED): the median path is built as before (median
#     growth IS additive); the 5th/95th paths add the published spread of the
#     LEVEL around the median, PCHIP-interpolated between knots and shifted so
#     that all three paths start from the observed 2025 population:
#         Pop_p(t) = Pop_50(t) + [spread_p(t) - spread_p(2025)]
#     Each path then has the published marginal 5th/95th percentile width in
#     every year. It is a band of marginal quantiles, not a simulated path, and
#     removing the 2025 spread only approximates conditioning on observed 2025.
# 'cumulated_growth': the previous behaviour, kept for comparison only.
POP_PERCENTILE_METHOD = 'published_levels'
CONSENT_SHEET = 'Sheet1'

HOUSEHOLD_SHEET_HIST = 'Table 2'
HOUSEHOLD_SHEET_PROJ = 'Table 1'
HOUSEHOLD_VARIANT_MAP = {'5th': 'Low', '50th': 'Medium', '95th': 'High'}

# ---------------------------------------------------------------------------
# HOUSEHOLD METHOD -- how future households are obtained        [Route B]
# ---------------------------------------------------------------------------
# All three Stats NZ household variants (Low B / Medium B / High B) use the SAME
# 'B' living-arrangement assumption. They differ ONLY in fertility, mortality
# and migration -- i.e. they are population variants. The old method paired the
# 5th-percentile population (2024-base) with the Low B households (2018-base),
# so low-population was counted on BOTH sides of S = Pop / HH, from two different
# vintages. That double-counting is why the household-size band flipped sign
# (2.38 at the 5th vs 3.00 at the 95th by 2050).
#
# 'single_living_arrangement' (Route B): take household size from the Medium B
#     path, rebased on observed 2025 -- the one living-arrangement assumption
#     Stats NZ actually made -- and apply it to every population percentile:
#         S(t)            = Pop_50th(t) / HH_MediumB(t)
#         Households_p(t) = Pop_p(t) / S(t)
#     Population percentiles then carry population uncertainty alone.
# 'variant_pairing': the previous behaviour, kept for comparison.
#
# 'matched_size' (Route A, ADOPTED): household size is taken from a population
#     projection of (near-)matching vintage divided by the 2018-base household
#     projection, at their shared published knots:
#         S_StatsNZ(knot) = Pop_update(knot) / HH_MediumB(knot)
#     interpolated between knots with the same shape-preserving spline (PCHIP)
#     used for every other input, extended linearly past the last knot, and
#     applied as a SHAPE rebased on observed 2025 household size:
#         S(t)            = S_observed(2025) x S_StatsNZ(t) / S_StatsNZ(2025)
#         Households_p(t) = Pop_2024base_p(t) / S(t)
#     VINTAGE: see FILE_POP_SIZE_PAIR for which release is paired and why.
#     Both series are at 30 June; only the rebased shape is used, so the
#     half-year offset and any level difference do not enter the result.
# 'single_living_arrangement' (Route B): S = Pop_2024base_median / HH_MediumB.
# 'variant_pairing': the original behaviour.
HOUSEHOLD_METHOD = 'matched_size'
HH_SIZE_VARIANT = 'Medium'   # 'Low' | 'Medium' | 'High' -- sensitivity on S only

# ---------------------------------------------------------------------------
# HOUSEHOLD SIZE RESPONDS TO MIGRATION
# ---------------------------------------------------------------------------
# New households come from two engines: more people arriving, and the same
# people spreading into more households (household size falling). History shows
# the engines TAKE TURNS: in low-migration years household size falls fast, in
# high-migration years it rises (1992-2025: r = +0.64, p < 0.0001). The Stats NZ
# household-size path is built on a different population projection and cannot
# see this, so on its own it switches the second engine off overnight in 2026.
#
# Household size each year is therefore:
#   dS(t) = dS_StatsNZ(t) + e_2025 x rho^(t-2025)
#   e_2025 = 2025's observed fall MINUS the part explained by that year's low
#            migration:  dS_obs - [dS_StatsNZ(2025) + b x (pop growth 2025 -
#            the growth Stats NZ's path assumed for 2025)]
#   b   = response of household size to population growth, fitted 1992-2025
#         with a time trend (so the long decline is not attributed to migration)
#   rho = year-to-year persistence of deviations from that fit (its residuals)
# b has one job: removing the migration-driven part of 2025's fall, which ends
# when migration recovers. It is NOT applied every year: tried, it drives the
# median to 2.68 and the percentiles to 2.12-3.23, because our population differs
# from Stats NZ's by a persistent vintage gap, not a migration shock.
# Stats NZ's path stays the long-run anchor, so household size cannot drift
# (a naive fit carries 1992-2025's decline forward to 2.42 by 2050).
HH_SIZE_RESPONSE = True
DEVIATION_PERSISTENCE = 'estimated'   # 'estimated' | a number in [0, 1)
# The same principle is applied to dwellings built beyond household formation:
# 2025's deviation from the stock model fades at that series' own measured
# persistence (lag-1 autocorrelation of its 1992-2025 residual).

ANCHOR_SMOOTHING_YEARS = 3

COL_GFA = 'GFA - GFA'
COL_TYPOLOGIES = {
    'Detached': 'GFA - GFA/Detached',
    'Townhouses': 'GFA - GFA/Townhouses',
    'Apartments': 'GFA - GFA/Apartments',
}
# [FIX f] dwelling COUNTS, needed to measure realised dwelling size / utilisation
# ---------------------------------------------------------------------------
# DWELLING COUNTS -- which column supplies the denominator for dwelling size
# ---------------------------------------------------------------------------
# VERIFIED against Stats NZ (Building consents issued: March 2023): the
# 'Consents - Consents/...' columns ALREADY hold NEW DWELLINGS CONSENTED, not
# building permits. March 2023 file values 1,586 / 1,821 / 327 match the
# published 1,586 stand-alone houses / 1,820 townhouses-flats-units / 327
# apartments exactly. So no substitution is needed for that reason.
#
# What the file DOES omit is Stats NZ's fourth category, retirement village
# units (237 in March 2023; ~7% of all dwellings consented in the year ended
# March 2023). Critically, BOTH the counts AND the floor area in this file
# exclude them, so the file is internally consistent.
#
# COL_DWELLINGS_TOTAL: optional external total-dwellings column. If present it
# is used ONLY as a cross-check, never silently as a denominator, because an
# all-category dwelling count divided into three-typology floor area would
# understate dwelling size by roughly the retirement-village share.
COL_DWELLINGS_TOTAL = 'Dwellings'        # set to None to skip the cross-check
DWELLING_COUNT_SOURCE = 'typology_sum'   # 'typology_sum' | 'dwellings_column'

COL_CONSENT_COUNTS = {
    'Detached': 'Consents - Consents/Detached',
    'Townhouses': 'Consents - Consents/Townhouses',
    'Apartments': 'Consents - Consents/Apartments',
}
TYPOLOGY_COLORS = {'Detached': '#4C72B0', 'Townhouses': '#DD8452', 'Apartments': '#55A868'}

DEMAND_LABELS = ['Growth demand (net of consolidation)',
                 'Consumption: extra space per dwelling',
                 'Consumption: vacancy allowance',
                 'Consumption: replacement of demolished stock',
                 'House-splitting demand',
                 'Avoided floor area (consolidation)']
DEMAND_LABELS_LEGEND = DEMAND_LABELS[:4] + ['_nolegend_', DEMAND_LABELS[5]]
DEMAND_COLORS = ['#3498db', '#8e44ad', '#95a5a6', '#34495e', '#e67e22', 'none']
HOUSESPLIT_COLOR = DEMAND_COLORS[4]
# The calibrated residual is labelled for what it is. About half of it
# (1992-2025) is retirement-village units: they house households counted in the
# household series, and they ARE built, but they are outside the three-typology
# consent data. See the [check] printed under STOCK. Only the remainder is
# plausibly unconsented additions.
UNCONSENTED_LABEL = 'Residual: out-of-scope dwellings (retirement villages) and unconsented additions'
UNCONSENTED_COLOR = '#16a085'

TREND_WINDOW_START = 2012
DAMPING_PHI = 0.8

# --- [FIX d] consumption-rate calibration -------------------------------
# v2 used .ewm(span=35, adjust=False) starting at 1991. With adjust=False the
# recursion is SEEDED with the first observation, and after 34 steps that seed
# still carries (1-alpha)^34 = 14.3% weight -- more than any other single year,
# including the most recent. 1991 is also the one year whose growth demand is
# structurally undefined (there is no 1990 in the window to difference against),
# so its consumption residual is inflated by construction.
# Fix: adjust=True (weights properly normalised, no seed lump) and start in 1992.
# Span 15 gives a ~10-year half-life. A sensitivity table over spans and simple
# means is printed at runtime -- the result is insensitive to all of them.
CALIB_START_YEAR = 1992
EWMA_SPAN = 15
EWMA_ADJUST = True

# ---------------------------------------------------------------------------
# CONSUMPTION BASIS -- what consumption is assumed to scale with
# ---------------------------------------------------------------------------
# 'per_capita': consumption = Population x rate (m2 per person per year).
#     Scales with the population LEVEL. Historically ~83% of consumption is
#     extra space inside NEW dwellings, which scales with household FORMATION,
#     a flow. Forward, formation falls from ~24,200/yr to ~15,000/yr while the
#     population level keeps rising, so this basis builds a growing residual
#     ('other') with no mechanism behind it: 4.4x its historical average, and
#     ~42% of the whole projection.
# 'per_household': consumption = new households x rate (m2 per new household).
#     Scales with household formation, the thing that historically explained it.
#     Calibrated as a ratio of exponentially weighted SUMS (weighted consumption
#     / weighted household formation), not a weighted mean of annual ratios,
#     because the annual ratio is unstable when formation is low (17-183 m2).
#     Negative formation contributes zero consumption. Under this basis the
#     'Avoid' pathway lever also scales consumption, since a consumption term
#     that is floor area per new dwelling shrinks when dwellings are built
#     smaller; under 'per_capita' it cannot.
#
# FINDING -- neither basis is correct on its own; they BRACKET the answer.
#   per_capita    median 101.98 Mm2  -> upper bound. Carries a mechanism-free
#                 residual that grows to 4.4x its historical size.
#   per_household median  61.77 Mm2  -> lower bound. Assumes nothing is built
#                 unless a NEW household forms, so there is no replacement of
#                 demolished stock. At the 5th percentile, where households
#                 decline every year, it projects ~zero construction for 25
#                 years: the truncation guard fires in 25/25 years and the
#                 identity check FAILS. That is physically absurd.
# The ~40 Mm2 between them is roughly what replacement and vacancy should
# explain. Resolving it needs the stock module (dwelling stock, demolition,
# occupancy), not a choice of denominator.
#
# 'extra_space_plus_other' (ADOPTED): each part of consumption follows its own
#     driver, so nothing is left as an unexplained residual.
#       extra space = new households x (realised dwelling size - occupied area)
#                     -> follows household formation and dwelling size, and
#                        shrinks as the mix densifies.
#       other       = other_per_person x population
#                     -> held at its 1992-2025 historical level per person.
#     'Other' is replacement of demolished stock, vacancy change, second homes,
#     conversions, consent-to-occupancy timing and estimation error. Tested for
#     trend: robust (Theil-Sen) 95% interval includes zero, Mann-Kendall
#     p = 0.07, lag-1 autocorrelation +0.33 (which invalidates the ordinary
#     regression p = 0.046). No defensible trend, so it is held CONSTANT, with a
#     moving-block bootstrap interval as its own uncertainty band. Four ways of
#     holding 'other' to history all gave 52-63 Mm2, and this one agrees with
#     the per_household method (62.8 vs 61.8) by an independent route.
# 'stock_vacancy' (ADOPTED): 'other' is no longer a per-person constant. It is
#     the dwellings built beyond household formation, decomposed with census
#     vacancy data into three named terms:
#       vacancy allowance = new households x v / (1 - v)
#       vacancy change    = households(t-1) x [1/(1-v(t)) - 1/(1-v(t-1))]
#       replacement       = demolition rate x stock(t-1)
#     then converted to floor area at realised dwelling size. Vacancy v is
#     measured (census tables below); the demolition rate is the only calibrated term,
#     taken as the long-run residual over the calibration window.
#     Forward, v is held at its latest census value, so the vacancy-change term
#     is zero unless a scenario changes it.
#     Identity: total floor area = (new households + allowance + change
#                                   + replacement) x realised dwelling size.
CONSUMPTION_BASIS = 'stock_vacancy'
# 'per_capita' | 'per_household' | 'extra_space_plus_other' | 'stock_vacancy'

# 'Other' per person: which value of the bootstrap band drives the run.
OTHER_CASE = 'central'            # 'central' | 'low' | 'high'
OTHER_BOOTSTRAP_BLOCK = 4          # years per block (respects autocorrelation)
OTHER_BOOTSTRAP_N = 20000
OTHER_BOOTSTRAP_CI = (5, 95)       # -> 90% interval
OTHER_BOOTSTRAP_SEED = 42

# ---------------------------------------------------------------------------
# CENSUS DWELLING OCCUPANCY  (private dwellings only)
# ---------------------------------------------------------------------------
# Vacancy = EMPTY dwellings / (occupied + unoccupied private dwellings).
# Stats NZ defines unoccupied dwellings as PRIVATE dwellings that were empty or
# whose occupants were away, so no non-private adjustment is needed: non-private
# dwellings appear only in the occupied count and are excluded from the stock.
# 'Residents away' are NOT vacant: those households exist and are already in
# the household series. Counting them fails the replacement check below.
#
# 1981-2013: FILE_CENSUS_2013, Stats NZ 2013 Census QuickStats about housing.
#   Table 1 gives occupied private dwellings, unoccupied and under construction
#   for every census 1981-2013; Table 2 gives the 2013 empty / residents-away
#   split. Before 2013 only total unoccupied is published, so the 2013 empty
#   share (76.2%) is applied to earlier years -- the one assumption here, with
#   a sensitivity band. 2013 is measured.
# 2018, 2023: Stats NZ Census dwelling occupancy tables (NZ.Stat), measured.
# Only the RATIO is used: census counts and the household estimates series
# differ in level (census undercount), exactly as for household size.
FILE_CENSUS_2013 = os.path.join(DATA_DIR, 'occ-unocc-2013.xlsx')
CENSUS_LATER = {
    2018: dict(occupied_private=1664313, unoccupied=196506, empty=97842,
               away=98664, under_construction=16128),
    2023: dict(occupied_private=1793613, unoccupied=225168, empty=111666,
               away=113499, under_construction=27309),
}
PRE2013_EMPTY_SHARE_BAND = 0.05    # +/- on the empty share applied before 2013
DEMOLITION_CALIB_START = 1992      # calibration window for the unconsented-additions rate

# ---------------------------------------------------------------------------
# BUILT DWELLINGS, DEMOLITION AND UNCONSENTED ADDITIONS
# ---------------------------------------------------------------------------
# The dwelling stock works like a bucket. Each year:
#     stock change = dwellings BUILT - dwellings DEMOLISHED + UNCONSENTED additions
# Built = consents x COMPLETION_RATE (not every consent becomes a dwelling).
# Unconsented additions are dwellings that appear in the census without a
# new-dwelling consent: granny flats, garage and house conversions, sleep-outs,
# mobile homes. They meet housing need WITHOUT new construction, so they reduce
# the floor area (and carbon) that must be built -- shown as a negative band.
# Rearranged for what must be built:
#     built = new households + vacancy allowance + vacancy change
#             + demolitions - unconsented additions
# COMPLETION_RATE: Jones, Greenaway-McGrevy & Crow (2024), after
#   Greenaway-McGrevy & Jones (2023): 91-96% depending on the completion
#   milestone. Eventual completion lies between the code-compliance share
#   (~92%, counted early, so a lower bound) and the first-inspection share
#   (~96%, construction started, so an upper bound). 95% is their own assumption.
# DEMOLITION_RATE: Page (2009), BRANZ Study Report SR214 -- ~2,200 dwellings/yr
#   in 2001-2006 from the same census-and-consents identity used here, on a 2006
#   private stock of 1,631,019 = 0.135%/yr (Finland, measured 2000-12: 0.15%).
#   Held fixed; the unconsented-additions rate is the calibrated residual. The
#   two trade one-for-one, so the demolition band moves the SPLIT, not totals.
COMPLETION_RATE = 0.95
COMPLETION_RATE_BAND = (0.92, 0.96)
DEMOLITION_RATE = 0.00135
DEMOLITION_RATE_BAND = (0.0010, 0.0030)


# ---------------------------------------------------------------------------
# HOUSEHOLD DECLINE
# ---------------------------------------------------------------------------
# When households shrink, the model previously booked NEGATIVE structural
# demand -- freed dwellings offsetting new construction nationally. That
# assumes an empty house in a shrinking town can meet demand elsewhere, which
# Napiontek et al. (2025) show it cannot (hibernating stock). Population growth
# was already floored at zero; household formation is now floored the same way.
# Freed dwellings become vacancy, not negative construction. Never binds in
# history (minimum 9,900 new households/yr) or in the median projection; it
# binds only in low-population scenarios.
FLOOR_HOUSEHOLD_DECLINE = True

# [FIX f] Reference window for realised new-dwelling floor area, held constant
# over the projection (parallel to holding OLF constant).
DWELLING_SIZE_REF = (2023, 2025)

# ---------------------------------------------------------------------------
# CASE-STUDY FACTORS -- produced by building_factors.py, never hard-coded here
# ---------------------------------------------------------------------------
# factors_material.csv : kg CO2e/m2 GFA by typology x material x life-cycle
#                        stage, pooled over the 16 case-study buildings.
# factors_typology.csv : occupancy load factor, design occupants, floor space
#                        index, soil carbon loss, per typology.
#
# Soil organic carbon loss is carried as its OWN line, not as a material. It is
# land-use change (L_w / floor space index), so no material assumption should
# ever be applied to it.
#
# OCCUPANCY LOAD FACTOR is floor area per DESIGN occupant. The column used,
# 'OLF_m2_per_person', is pooled like every other factor (equal-subtype mean of
# building-level ratios; see building_factors.py). The people-conserving ratio
# of sums, 'OLF_people_conserving', is also written; they differ by 0.3% for
# Detached and 6.5% for Townhouses. OLF moves floor area BETWEEN the growth,
# house-splitting and extra-space bands; it does not change the total, which is
# (new households + vacancy + replacement - unconsented) x dwelling size.
#
# Setting USE_GROSS_BASIS_OLF = True instead derives it from consented dwelling
# size divided by design occupants; the reconciliation between the two prints
# at runtime.
FILE_FACTORS_MATERIAL = os.path.join(DATA_DIR, 'factors_material.csv')
FILE_FACTORS_TYPOLOGY = os.path.join(DATA_DIR, 'factors_typology.csv')
STAGES_IN_SCOPE = ['A1-A3', 'A4-A5', 'B2,B4', 'C1-C4']   # Module D excluded
USE_GROSS_BASIS_OLF = False
DEMAND_BASIS = 'bim_olf'

# Carbon intensity is held CONSTANT at its case-study value for the whole
# projection. No learning rate, no decarbonisation: this build reports what
# current construction practice implies, and nothing is assumed about future
# material supply.


# ============================================================
# LOADERS
# ============================================================

def load_historical_population(path=FILE_POP_HIST, sheet=POP_SHEET_HIST,
                               year_row_label='Year ended 31 December',
                               value_row_label='Estimated resident population'):
    """
    [FIX e] Read the annual Estimated Resident Population from the wide-format
    Stats NZ summary table (years across columns, indicators down rows).

    v2 read a 'Population_Sheet' that had been re-interpolated to monthly by
    hand and then picked one month per year. This reads the published annual
    ERP as at 31 December directly, which matches both the calendar-year consent
    totals and the 31-December household series. No interpolation is involved.
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    label_col = raw.iloc[:, 0].astype(str)

    yr_rows = label_col.index[label_col.str.contains(year_row_label, case=False, na=False)]
    val_rows = label_col.index[label_col.str.contains(value_row_label, case=False, na=False)]
    if len(yr_rows) == 0 or len(val_rows) == 0:
        raise ValueError(
            f"Could not find rows '{year_row_label}' / '{value_row_label}' in sheet "
            f"'{sheet}' of {path}. Check the table layout has not changed."
        )

    years = pd.to_numeric(raw.iloc[yr_rows[0], 1:], errors='coerce')
    values = pd.to_numeric(raw.iloc[val_rows[0], 1:], errors='coerce')
    df = pd.DataFrame({'Year': years.values, 'Population': values.values}).dropna()
    df['Year'] = df['Year'].round().astype(int)
    df = df.drop_duplicates('Year').sort_values('Year').reset_index(drop=True)
    if df.empty:
        raise ValueError(f"Parsed no population rows from {path}.")
    return df


def load_historical_households(path, sheet=HOUSEHOLD_SHEET_HIST, value_col_idx=1):
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    date_str = raw.iloc[:, 0].astype(str).str.strip()
    date_str_clean = date_str.str.replace(r'\s*R\s*$', '', regex=True)
    parsed_date = pd.to_datetime(date_str_clean, format='%d %b %Y', errors='coerce')
    value = pd.to_numeric(raw.iloc[:, value_col_idx], errors='coerce')
    df = pd.DataFrame({'Date': parsed_date, 'Households': value}).dropna().reset_index(drop=True)
    if df.empty:
        raise ValueError(f"Could not parse quarterly household rows from '{sheet}' in {path}.")
    return df


def locate_projection_block(df_raw, section_label='Annual population growth (000)',
                            min_year=2025, max_year=2050, search_window=40):
    label_col = df_raw.iloc[:, 0].astype(str)
    header_rows = label_col.index[
        label_col.str.contains(section_label, case=False, na=False, regex=False)].tolist()
    if not header_rows:
        raise ValueError(f"Could not find section '{section_label}' in the projection sheet.")
    header_idx = header_rows[0]

    raw = df_raw.iloc[:, [0, 2, 4, 6]].copy()
    raw.columns = ['YearRaw', 'PopGrowth_5th', 'PopGrowth_50th', 'PopGrowth_95th']
    raw['Year'] = pd.to_numeric(raw['YearRaw'].astype(str).str.extract(r'(\d{4})')[0], errors='coerce')

    years, r5, r50, r95 = [], [], [], []
    for i in range(header_idx + 1, min(header_idx + 1 + search_window, len(raw))):
        yr = raw.loc[i, 'Year']
        if pd.isna(yr) or not (min_year <= yr <= max_year):
            if years:
                break
            continue
        years.append(int(yr))
        r5.append(raw.loc[i, 'PopGrowth_5th'])
        r50.append(raw.loc[i, 'PopGrowth_50th'])
        r95.append(raw.loc[i, 'PopGrowth_95th'])
    return pd.DataFrame({'Year': years, 'PopGrowth_5th': r5,
                         'PopGrowth_50th': r50, 'PopGrowth_95th': r95})


def load_national_pop_projection(path=None, sheet=None, variant='Medium',
                                  area_label='New Zealand'):
    """[Route A] National population from the subnational projection table
    (knots across columns, regions down rows, High/Medium/Low per region).
    The base-year value is published only on the Medium row; it is shared by
    all three variants."""
    path = path or FILE_POP_SIZE_PAIR
    sheet = sheet or POP_SIZE_PAIR_SHEET
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    col0 = [str(x) for x in raw.iloc[:, 0].tolist()]
    col1 = [str(x).strip() for x in raw.iloc[:, 1].tolist()]
    area_rows = [i for i, v in enumerate(col0) if v.strip().lower().startswith(area_label.lower())]
    if not area_rows:
        raise ValueError(f"No '{area_label}' row in {path} / {sheet}.")
    a = area_rows[0]
    rows = {col1[i]: i for i in range(a, min(a + 3, len(col1)))}
    if variant not in rows or 'Medium' not in rows:
        raise ValueError(f"Variant rows {list(rows)} around '{area_label}' lack '{variant}'.")
    def _as_year(cell):
        # A year cell is either a whole number in range, or text like '2018(3)'.
        if isinstance(cell, (int, float, np.integer, np.floating)) and not pd.isna(cell):
            return int(cell) if float(cell).is_integer() and 2000 <= cell <= 2100 else None
        m = re.match(r'^\s*(\d{4})\s*(\(\d+\))?\s*$', str(cell))
        return int(m.group(1)) if m and 2000 <= int(m.group(1)) <= 2100 else None

    hdr = next((i for i in range(a)
                if sum(_as_year(raw.iat[i, j]) is not None for j in range(2, raw.shape[1])) >= 4), None)
    if hdr is None:
        raise ValueError(f"Could not find the knot-year header row in {path}.")
    years, vals = [], []
    for j in range(2, raw.shape[1]):
        yr = _as_year(raw.iat[hdr, j])
        if yr is None:
            continue
        v = pd.to_numeric(raw.iat[rows[variant], j], errors='coerce')
        if pd.isna(v):
            v = pd.to_numeric(raw.iat[rows['Medium'], j], errors='coerce')   # shared base year
        years.append(yr); vals.append(float(v))
    return pd.DataFrame({'Year': years, 'Population': vals})


def load_census_occupancy(path=None, later=None):
    """Census private-dwelling occupancy, one row per census year.
    Reads Tables 1 and 2 of the 2013 QuickStats workbook, then appends the
    later censuses. Columns: occupied_private, unoccupied, empty (NaN where not
    published), away, under_construction, total_private."""
    path = path or FILE_CENSUS_2013
    later = CENSUS_LATER if later is None else later
    t1 = pd.read_excel(path, sheet_name='Table 1', header=None)
    rows = {}
    for _, r in t1.iterrows():
        yr = pd.to_numeric(r[0], errors='coerce')
        if pd.notna(yr) and 1900 < yr < 2100 and float(yr).is_integer():
            rows[int(yr)] = dict(occupied_private=float(r[1]), unoccupied=float(r[4]),
                                 under_construction=float(r[5]), empty=np.nan, away=np.nan)
    if not rows:
        raise ValueError(f"No census years parsed from Table 1 of {path}.")
    t2 = pd.read_excel(path, sheet_name='Table 2', header=None)
    nz = t2[t2[0].astype(str).str.strip().str.lower() == 'total new zealand']
    if nz.empty:
        raise ValueError(f"No 'Total New Zealand' row in Table 2 of {path}.")
    y2013 = max(rows)
    rows[y2013]['away'] = float(nz.iloc[0][4])
    rows[y2013]['empty'] = float(nz.iloc[0][5])
    for yr, c in later.items():
        rows[yr] = {k: float(c.get(k, np.nan)) for k in
                    ('occupied_private', 'unoccupied', 'under_construction', 'empty', 'away')}
    df = pd.DataFrame.from_dict(rows, orient='index').sort_index()
    df['total_private'] = df['occupied_private'] + df['unoccupied']
    return df


def _extract_leading_year(cell, min_year, max_year):
    m = re.match(r'^(\d{4})', str(cell).strip())
    if not m:
        return None
    yr = int(m.group(1))
    return yr if min_year <= yr <= max_year else None


def extract_household_projection_block(path, sheet=HOUSEHOLD_SHEET_PROJ, variant_label='Medium',
                                       total_col_idx=4, min_year=2000, max_year=2050,
                                       search_window=15):
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    label_col = raw.iloc[:, 0].astype(str).str.strip()
    candidates = raw.index[label_col.str.match(rf'^{re.escape(variant_label)}\b',
                                               case=False, na=False)].tolist()
    for start_idx in candidates:
        years, totals = [], []
        for i in range(start_idx + 1, min(start_idx + search_window, len(raw))):
            yr = _extract_leading_year(raw.iat[i, 0], min_year, max_year)
            if yr is None:
                if years:
                    break
                continue
            total_val = pd.to_numeric(raw.iat[i, total_col_idx], errors='coerce')
            if pd.isna(total_val):
                break
            years.append(yr)
            totals.append(total_val)
        if len(years) >= 2:
            return pd.DataFrame({'Year': years,
                                 'Households': np.array(totals, dtype=float) * 1000})
    raise ValueError(f"No usable '{variant_label}' household block in {path}.")


def smooth_interpolate_and_extend(block_df, value_col, full_year_range):
    """
    Shape-preserving (PCHIP) interpolation between published knots, then linear
    extension beyond the last knot using the endpoint slope.

    [FIX e] This is now used for the POPULATION projection as well as households.
    v2 filled the population gaps with .interpolate('linear') followed by .ffill(),
    which left 2049 and 2050 as flat copies of the 2048 value. Both demographic
    inputs now go through one method.
    """
    known_years = block_df['Year'].values.astype(float)
    known_vals = block_df[value_col].values.astype(float)
    interpolator = PchipInterpolator(known_years, known_vals)

    last_known_year = known_years.max()
    within_years = full_year_range[full_year_range <= last_known_year].astype(float)
    ext_years = full_year_range[full_year_range > last_known_year].astype(float)
    within_vals = interpolator(within_years)

    if len(ext_years) > 0:
        eps = 0.5
        slope_at_end = float((interpolator(last_known_year)
                              - interpolator(last_known_year - eps)) / eps)
        ext_vals = float(within_vals[-1]) + slope_at_end * (ext_years - last_known_year)
    else:
        ext_vals = np.array([])

    return pd.DataFrame({'Year': np.concatenate([within_years, ext_years]).astype(int),
                         value_col: np.concatenate([within_vals, ext_vals])})


# ============================================================
# CORE HELPERS
# ============================================================

def fit_evolving_mix(hist_shares, shares_2025, forecast_years, phi, trend_window_start,
                     typ_names, ref_typology='Detached'):
    """Additive log-ratio (ALR) trend with geometric damping. Shares stay positive
    and sum to one by construction."""
    other = [n for n in typ_names if n != ref_typology]
    window = hist_shares.loc[hist_shares.index >= trend_window_start]

    alr_hist = {n: np.log(window[n] / window[ref_typology]) for n in other}
    slope = {n: np.polyfit(window.index.values, alr_hist[n].values, 1)[0] for n in other}
    alr_2025 = {n: np.log(shares_2025[n] / shares_2025[ref_typology]) for n in other}

    years_ahead = (forecast_years - 2025).clip(min=0)
    damp = phi * (1 - phi ** years_ahead) / (1 - phi)

    alr_f = {n: alr_2025[n] + slope[n] * damp for n in other}
    denom = 1 + sum(np.exp(alr_f[n]) for n in other)
    shares_out = {ref_typology: 1 / denom}
    for n in other:
        shares_out[n] = np.exp(alr_f[n]) / denom
    return pd.DataFrame(shares_out, index=forecast_years)[list(typ_names)]


def blend_per_gfa_share(shares, per_unit_dict, typ_names):
    """
    Harmonic mean weighted by GFA share.

    Verified identity: with GFA share s_i = X_i * n_i / sum(X_j * n_j),
        1 / sum(s_i / X_i)  ==  sum(X_j * n_j) / sum(n_i)
    i.e. this equals the ARITHMETIC mean weighted by the underlying unit
    (person, or dwelling) shares. So blended_X * dN == sum_i(X_i * dN_i) exactly.
    A plain GFA-share-weighted average would be wrong (36.73 vs 36.00 at 2025).

    Used for both m2/design-occupant (OLF) and m2/dwelling (realised size).
    """
    inv = pd.Series(0.0, index=shares.index)
    for name in typ_names:
        inv += shares[name] / per_unit_dict[name]
    return 1.0 / inv


def calibrate_consumption_rate(consumption, population, years,
                               start_year=CALIB_START_YEAR,
                               span=EWMA_SPAN, adjust=EWMA_ADJUST):
    """[FIX d] EWMA of the per-capita consumption rate, seed-artefact free."""
    rate = pd.Series(consumption / population, index=years)
    rate = rate.loc[rate.index >= start_year]
    return float(rate.ewm(span=span, adjust=adjust).mean().iloc[-1]), rate


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 78)
    print(" NZ RESIDENTIAL FLOOR AREA & EMBODIED CARBON, 2026-2050")
    print(f" demand split: growth / house-splitting / consumption  |  "
          f"'other' basis: {CONSUMPTION_BASIS}")
    print("=" * 78)

    typ_names = list(COL_TYPOLOGIES.keys())

    # ------------------------------------------------------------------
    # 0. CASE-STUDY FACTORS
    # ------------------------------------------------------------------
    mat_fac = pd.read_csv(FILE_FACTORS_MATERIAL)
    typ_fac = pd.read_csv(FILE_FACTORS_TYPOLOGY).set_index('Typology')
    missing = set(typ_names) - set(typ_fac.index)
    if missing:
        raise ValueError(f"{FILE_FACTORS_TYPOLOGY} has no rows for {missing}. "
                         f"Run building_factors.py first.")
    mat_scope = mat_fac[mat_fac['Stage'].isin(STAGES_IN_SCOPE)]
    MATERIALS = sorted(mat_scope['Material'].unique())
    # kg CO2e per m2 GFA, by typology and material (materials only; soil added
    # separately as its own line so that it is never treated as a material).
    MAT_INTENSITY = (mat_scope.pivot_table(index='Material', columns='Typology',
                                           values='kgCO2e_per_m2', aggfunc='sum')
                     .reindex(index=MATERIALS, columns=typ_names).fillna(0.0))
    SOIL_INTENSITY = {t: float(typ_fac.loc[t, 'SOC_avg']) for t in typ_names}
    OLF_NET_BIM = {t: float(typ_fac.loc[t, 'OLF_m2_per_person']) for t in typ_names}
    DESIGN_OCCUPANTS = {t: float(typ_fac.loc[t, 'design_occupants']) for t in typ_names}
    T_BASELINE_2025 = {t: float(typ_fac.loc[t, 'total_with_SOC']) for t in typ_names}

    # ------------------------------------------------------------------
    # 1. CONSENTS: floor area AND dwelling counts
    # ------------------------------------------------------------------
    df_consents = pd.read_excel(FILE_CONSENTS, sheet_name=CONSENT_SHEET)
    df_consents['Year'] = pd.to_datetime(df_consents['Date']).dt.year

    hist_typ_gfa = df_consents.groupby('Year')[list(COL_TYPOLOGIES.values())].sum()
    hist_typ_gfa.columns = typ_names
    hist_typ_gfa = hist_typ_gfa.loc[1991:2025]

    hist_typ_units = df_consents.groupby('Year')[list(COL_CONSENT_COUNTS.values())].sum()
    hist_typ_units.columns = typ_names
    hist_typ_units = hist_typ_units.loc[1991:2025]

    hist_total_gfa = df_consents.groupby('Year')[COL_GFA].sum().loc[1991:2025]

    # ---- dwelling-count denominator, with a coverage guard ----------
    typ_sum = hist_typ_units.sum(axis=1)
    ext = None
    if COL_DWELLINGS_TOTAL and COL_DWELLINGS_TOTAL in df_consents.columns:
        ext = df_consents.groupby('Year')[COL_DWELLINGS_TOTAL].sum().reindex(typ_sum.index)

    if ext is not None:
        ratio = (ext / typ_sum).loc[2015:2025].mean()
        gap = (ext - typ_sum).loc[2015:2025].mean()
        # The external column includes retirement village units, which the floor
        # area columns exclude, so it is a cross-check only, never the denominator.
        print(f"[check] scope: 3 typologies; the all-category dwelling column is "
              f"{100 * (ratio - 1):.1f}% higher ({gap:,.0f}/yr, retirement villages) "
              f"-> not used as denominator")

    if DWELLING_COUNT_SOURCE == 'dwellings_column':
        if ext is None:
            raise ValueError(f"DWELLING_COUNT_SOURCE='dwellings_column' but no "
                             f"'{COL_DWELLINGS_TOTAL}' column exists in {FILE_CONSENTS}.")
        print("   [!] Using the external column as the denominator. Ensure the FLOOR AREA")
        print("       columns cover the same categories, or dwelling size will be biased.")
        hist_total_units = ext
    else:
        hist_total_units = typ_sum

    # Reconciliation: the typology columns must sum to the published total,
    # otherwise splitting the forecast by typology share is invalid.
    recon = float((hist_total_gfa - hist_typ_gfa.sum(axis=1)).abs().max())
    print(f"\n[check] typology GFA columns vs published total: max |diff| = {recon:,.0f} m2")

    hist_shares = hist_typ_gfa.div(hist_typ_gfa.sum(axis=1), axis=0)
    shares_2025 = hist_shares.loc[2025]
    years_hist = hist_typ_gfa.index.values

    # ------------------------------------------------------------------
    # 2. DEMOGRAPHICS (all on a 31 December basis)
    # ------------------------------------------------------------------
    pop_df = load_historical_population()
    hist_pop = pop_df.set_index('Year')['Population'].reindex(years_hist)
    if hist_pop.isna().any():
        missing = list(hist_pop.index[hist_pop.isna()])
        raise ValueError(f"Population missing for {missing} in {FILE_POP_HIST}.")

    hh_raw = load_historical_households(FILE_HOUSEHOLDS_HIST)
    hh_raw['Year'] = hh_raw['Date'].dt.year
    hh_annual = hh_raw.loc[hh_raw.groupby('Year')['Date'].idxmax()].set_index('Year')['Households']
    hist_hh = hh_annual.reindex(years_hist)
    if hist_hh.isna().any():
        raise ValueError("Household series has gaps over 1991-2025.")

    hist_S = hist_pop / hist_hh
    print(f"[check] population source: {FILE_POP_HIST} (annual ERP at 31 Dec), "
          f"households at 31 Dec -> consistent basis")

    # ------------------------------------------------------------------
    # 3. REALISED DWELLING SIZE AND UTILISATION            [FIX f]
    # ------------------------------------------------------------------
    # OLF is floor area per DESIGN occupant, where design capacity = bedrooms+1.
    # Multiplying it by the ACTUAL household size S does NOT give a dwelling
    # size -- the denominators differ. v2 called S*OLF "avg_dwelling_size",
    # which was a mislabel. It is the floor area associated with the occupants
    # a dwelling actually houses, so it is renamed occupied_area_per_dwelling.
    # Realised dwelling size is measured directly instead: GFA / dwelling count.
    hist_dwelling_size = hist_typ_gfa / hist_typ_units          # m2 per dwelling, per typology

    # [FIX apt] resolve which OLF basis to use, and validate it.
    size_ref = {t: float(hist_dwelling_size[t].loc[DWELLING_SIZE_REF[0]:DWELLING_SIZE_REF[1]].mean())
                for t in typ_names}
    OLF_GROSS = {t: size_ref[t] / DESIGN_OCCUPANTS[t] for t in typ_names}
    OLF_USED = OLF_GROSS if USE_GROSS_BASIS_OLF else dict(OLF_NET_BIM)

    if VERBOSE:   # case-study vs consented occupancy; see Diagnostics D
        print("\n OCCUPANCY LOAD FACTOR -- case studies vs consented dwellings "
              f"({'GROSS, derived' if USE_GROSS_BASIS_OLF else 'NET, raw BIM'})")
        print(f"   {'Typology':<12}{'realised size':>14}{'design occ':>12}"
              f"{'OLF gross':>11}{'OLF cases':>13}{'gross/net':>11}")
        for t in typ_names:
            print(f"   {t:<12}{size_ref[t]:>14.1f}{DESIGN_OCCUPANTS[t]:>12.1f}"
                  f"{OLF_GROSS[t]:>11.2f}{OLF_NET_BIM[t]:>13.2f}"
                  f"{OLF_GROSS[t] / OLF_NET_BIM[t]:>11.2f}")
        print("   The case-study apartments are whole blocks (63 dwellings each), so their")
        print("   floor area ALREADY includes shared circulation: the apartment gap is a SIZE")
        print("   difference (62 m2/dwelling in the cases vs 98 m2 consented), not a basis")
        print("   mismatch. Detached cases are smaller than the consented average and")
        print("   townhouse cases larger, so the sample compresses the spread between")
        print("   typologies relative to what New Zealand actually builds.")

    blended_olf_bim = blend_per_gfa_share(hist_shares, OLF_NET_BIM, typ_names)
    blended_dwelling_size = hist_total_gfa / hist_total_units

    # Floor area per resident, MEASURED: realised dwelling size / actual occupancy.
    area_per_resident = blended_dwelling_size / hist_S

    if DEMAND_BASIS == 'per_resident':
        blended_olf = area_per_resident
    else:
        blended_olf = blend_per_gfa_share(hist_shares, OLF_USED, typ_names)

    occupied_area_per_dwelling = hist_S * blended_olf
    # Utilisation is always measured against the BIM DESIGN benchmark: how much
    # floor area we build per resident, versus how much the design allows for.
    utilisation = blended_olf_bim / area_per_resident
    design_capacity = blended_dwelling_size / blended_olf_bim

    # ------------------------------------------------------------------
    # 4. HISTORICAL DEMAND DECOMPOSITION
    # ------------------------------------------------------------------
    d_pop = hist_pop.diff().fillna(0).clip(lower=0)
    d_hh = hist_hh.diff().fillna(0)

    hist_growth = d_pop * blended_olf                    # floor area for extra people
    hist_structural = d_hh * occupied_area_per_dwelling  # floor area for extra households
    hist_hs_raw = hist_structural - hist_growth
    hist_hs_pos = hist_hs_raw.clip(lower=0)              # dilution
    hist_avoided = (-hist_hs_raw).clip(lower=0)          # consolidation

    # [FIX c] Consumption is the part of observed consenting not explained by
    # household formation. v2 computed  Total - Growth - HS_pos, which equals
    # Total - Structural ONLY in dilution years. In the 14 consolidation years
    # (HS_raw < 0) it silently used Total - Growth and never credited back the
    # avoided amount -- while the FORWARD model subtracted it. The two halves of
    # the model therefore used different definitions. Now both use
    #     Consumption = Total - Structural
    # which reduces to the old expression whenever HS_raw >= 0.
    hist_consumption = (hist_total_gfa - hist_structural).clip(lower=0)

    n_consol = int((hist_hs_raw < 0).sum())
    old_consumption = (hist_total_gfa - hist_growth - hist_hs_pos).clip(lower=0)
    if VERBOSE: print(f"[FIX c] consolidation years in history: {n_consol}/{len(years_hist)}; "
          f"definition gap closed = {(hist_consumption - old_consumption).sum() / 1e6:.2f} Mm2")

    rate_consumption, rate_series = calibrate_consumption_rate(
        hist_consumption.values, hist_pop.values, years_hist)

    # Per-household rate: ratio of exponentially weighted sums, 1992 onward.
    _m = years_hist >= CALIB_START_YEAR
    _c = hist_consumption.values[_m]; _h = d_hh.values[_m]
    _a = 2.0 / (EWMA_SPAN + 1.0)
    _w = (1.0 - _a) ** np.arange(len(_c))[::-1]
    rate_per_household = float((_w * _c).sum() / (_w * _h).sum())

    # 'Other' per person, 1992 onward, with a moving-block bootstrap interval.
    _extra_h = (d_hh * (blended_dwelling_size - occupied_area_per_dwelling)).clip(lower=0)
    other_pp_series = ((hist_consumption - _extra_h) / hist_pop).loc[CALIB_START_YEAR:]
    _o = other_pp_series.values
    _rng = np.random.default_rng(OTHER_BOOTSTRAP_SEED)
    _n, _L = len(_o), OTHER_BOOTSTRAP_BLOCK
    _nb = int(np.ceil(_n / _L))
    _boot = np.empty(OTHER_BOOTSTRAP_N)
    for _b in range(OTHER_BOOTSTRAP_N):
        _st = _rng.integers(0, _n - _L + 1, size=_nb)
        _boot[_b] = np.concatenate([_o[i:i + _L] for i in _st])[:_n].mean()
    other_pp = {'central': float(_o.mean()),
                'low': float(np.percentile(_boot, OTHER_BOOTSTRAP_CI[0])),
                'high': float(np.percentile(_boot, OTHER_BOOTSTRAP_CI[1]))}
    other_rate = other_pp[OTHER_CASE]

    # ------------------------------------------------------------------
    # STOCK, VACANCY AND REPLACEMENT  (census-based)
    # ------------------------------------------------------------------
    census = load_census_occupancy()
    measured = census['empty'].notna()
    empty_share_measured = float(census.loc[measured, 'empty'].iloc[0]
                                 / census.loc[measured, 'unoccupied'].iloc[0])
    census = census[census.index >= years_hist.min() - 5]     # relevant window only

    def census_vacancy(pre_share):
        empty = census['empty'].fillna(census['unoccupied'] * pre_share)
        return (empty / census['total_private']).to_dict()

    def calibrate_stock(pre_share, completion=None, demol=None):
        """Vacancy path (interpolated between census years, flat outside),
        stock, and the three-term decomposition of dwellings built beyond
        household formation. Returns the long-run demolition rate."""
        knots = census_vacancy(pre_share)
        yrs = years_hist.astype(float)
        v = pd.Series(np.interp(yrs, list(knots), list(knots.values())), index=years_hist)
        inv = 1.0 / (1.0 - v)
        stock = hist_hh / (1.0 - v)
        allow = d_hh * v / (1.0 - v)
        change = hist_hh.shift(1) * inv.diff()
        completion = COMPLETION_RATE if completion is None else completion
        demol = DEMOLITION_RATE if demol is None else demol
        beyond = completion * hist_total_units - d_hh   # BUILT dwellings beyond formation
        net = beyond - allow - change                    # = demolitions - unconsented additions
        prev = stock.shift(1)
        demolition = demol * prev
        uncons = net - demolition                        # negative: met without new building
        w = years_hist >= DEMOLITION_CALIB_START
        rate_unc = float(uncons[w].sum() / prev[w].sum())
        return dict(knots=knots, v=v, stock=stock, allow=allow, change=change, beyond=beyond,
                    net=net, demol=demolition, uncons=uncons, rate_unc=rate_unc,
                    completion=completion, demol_rate=demol)

    stock_cal = calibrate_stock(empty_share_measured)
    demolition_rate = DEMOLITION_RATE                  # fixed (BRANZ SR214)
    unconsented_rate = stock_cal['rate_unc']            # calibrated residual
    v_forward = float(stock_cal['knots'][max(stock_cal['knots'])])   # latest census, held
    # Build duration = dwellings under construction on census night / dwellings
    # consented that calendar year (consents from the model's own data).
    build_duration = {int(yr): float(census.loc[yr, 'under_construction'] / hist_total_units.loc[yr])
                      for yr in census.index if yr in hist_total_units.index}

    other_2025 = float(COMPLETION_RATE * hist_total_units.loc[2025] - d_hh.loc[2025])
    _net = stock_cal['net'][years_hist >= DEMOLITION_CALIB_START].values
    rho_other = float(np.clip(np.corrcoef(_net[:-1], _net[1:])[0, 1], 0.0, 0.95))
    other_model_2025 = float(stock_cal['allow'].loc[2025] + stock_cal['change'].loc[2025]
                             + (demolition_rate + unconsented_rate)
                             * stock_cal['stock'].shift(1).loc[2025])
    other_dev_2025 = other_2025 - other_model_2025

    def other_dwellings(hh_levels, d_households, demol=None, unc=None):
        """Built dwellings required beyond household formation, forward:
        vacancy allowance + demolition replacement + unconsented additions (<0).
        Vacancy is held at its latest census value, so vacancy change is zero."""
        demol = DEMOLITION_RATE if demol is None else demol
        unc = unconsented_rate if unc is None else unc
        prev = np.concatenate([[hh_levels[0]], hh_levels[:-1]]) / (1.0 - v_forward)
        allow = np.maximum(d_households, 0.0) * v_forward / (1.0 - v_forward)
        d_part, u_part = demol * prev, unc * prev
        units = allow + d_part + u_part
        # 2025's deviation from the stock model fades at its measured persistence.
        # Booked to the residual term (unconsented additions), which absorbs
        # whatever vacancy and demolition do not explain.
        dev = other_dev_2025 * rho_other ** np.arange(len(units))
        dev[0] = 0.0
        units, u_part = units + dev, u_part + dev
        return units, allow, d_part, u_part

    def consumption_gross(pop_level, d_households, extra_space=None, other_scale=1.0,
                          hh_levels=None, dwelling_size=None):
        """Gross consumption under the active basis. d_households must already
        be floored if FLOOR_HOUSEHOLD_DECLINE applies."""
        if CONSUMPTION_BASIS == 'per_household':
            return np.maximum(d_households, 0.0) * rate_per_household
        if CONSUMPTION_BASIS == 'extra_space_plus_other':
            return extra_space + other_rate * other_scale * pop_level
        if CONSUMPTION_BASIS == 'stock_vacancy':
            units = other_dwellings(hh_levels, d_households)[0]
            return extra_space + other_scale * units * dwelling_size
        return pop_level * rate_consumption

    # ------------------------------------------------------------------
    # 5. 2025 ANCHOR PROPORTIONS
    # ------------------------------------------------------------------
    w = slice(-ANCHOR_SMOOTHING_YEARS, None)
    # Consolidation is netted against GROWTH: new people absorbed into existing
    # households reduce the floor area growth would otherwise need.
    g_a = (hist_growth - hist_avoided).values[w].mean()
    h_a = hist_hs_pos.values[w].mean()
    c_a = hist_consumption.values[w].mean()
    tot_a = g_a + h_a + c_a
    anchor = {'growth': g_a / tot_a, 'housesplit': h_a / tot_a, 'consumption': c_a / tot_a}

    # [NEW g] historical consumption split, used both for reporting and to
    # apportion the 2025 anchor's consumption between the two sub-components.
    hist_extra_space = (d_hh * (blended_dwelling_size - occupied_area_per_dwelling)).clip(lower=0)
    hist_other_cons = hist_consumption - hist_extra_space
    anchor_extra_share = float(
        hist_extra_space.values[w].sum() / max(hist_consumption.values[w].sum(), 1e-9))
    anchor_extra_share = min(max(anchor_extra_share, 0.0), 1.0)

    # ------------------------------------------------------------------
    # 6. POPULATION PROJECTION                              [FIX e]
    # ------------------------------------------------------------------
    df_pop_proj_raw = pd.read_excel(FILE_POP_PROJ, sheet_name=POP_SHEET_PROJ, skiprows=5)
    pop_growth_block = locate_projection_block(df_pop_proj_raw)
    for col in ['PopGrowth_5th', 'PopGrowth_50th', 'PopGrowth_95th']:
        pop_growth_block[col] = pd.to_numeric(pop_growth_block[col], errors='coerce') * 1000

    forecast_years = np.arange(2025, 2051)
    df_forecast = pd.DataFrame({'Year': forecast_years})
    pop_2025_actual = float(hist_pop.loc[2025])

    for pct in ['5th', '50th', '95th']:
        smoothed = smooth_interpolate_and_extend(
            pop_growth_block[['Year', f'PopGrowth_{pct}']].dropna(),
            f'PopGrowth_{pct}', forecast_years)
        df_forecast[f'PopGrowth_{pct}'] = smoothed[f'PopGrowth_{pct}'].values
        levels = np.zeros(len(forecast_years))
        levels[0] = pop_2025_actual
        for i in range(1, len(forecast_years)):
            levels[i] = levels[i - 1] + df_forecast.loc[i, f'PopGrowth_{pct}']
        df_forecast[f'PopTotal_{pct}'] = levels

    if POP_PERCENTILE_METHOD == 'published_levels':
        # Published LEVEL percentiles (knots run past 2050, so no extrapolation).
        pop_level_block = locate_projection_block(df_pop_proj_raw, section_label='Population (000)',
                                                  min_year=2024, max_year=2078)
        for col in ['PopGrowth_5th', 'PopGrowth_50th', 'PopGrowth_95th']:
            pop_level_block[col] = pd.to_numeric(pop_level_block[col], errors='coerce') * 1000
        pop_level_block = pop_level_block.dropna()
        for pct in ['5th', '95th']:
            spread = pd.DataFrame({'Year': pop_level_block['Year'],
                                   'spread': pop_level_block[f'PopGrowth_{pct}']
                                   - pop_level_block['PopGrowth_50th']})
            sp = smooth_interpolate_and_extend(spread, 'spread', forecast_years)['spread'].values
            levels = df_forecast['PopTotal_50th'].values + (sp - sp[0])
            df_forecast[f'PopTotal_{pct}'] = levels
            df_forecast.loc[1:, f'PopGrowth_{pct}'] = np.diff(levels)
    elif POP_PERCENTILE_METHOD != 'cumulated_growth':
        raise ValueError(f"Unknown POP_PERCENTILE_METHOD '{POP_PERCENTILE_METHOD}'.")
    print(f"[check] population percentiles ({POP_PERCENTILE_METHOD}), 2048: "
          + " | ".join(f"{p} {df_forecast.loc[forecast_years == 2048, f'PopTotal_{p}'].iloc[0] / 1e6:.2f} M"
                       for p in ['5th', '50th', '95th']))

    if VERBOSE: print(f"[FIX e] population projection: {len(pop_growth_block)} published knots "
          f"-> PCHIP to 2050 (was linear interpolate + ffill, which froze 2049-50)")

    # ------------------------------------------------------------------
    # 7. HOUSEHOLD PROJECTION
    # ------------------------------------------------------------------
    hh_2025_actual = float(hist_hh.loc[2025])

    def _hh_from_variant(variant):
        blk = extract_household_projection_block(FILE_HOUSEHOLDS_PROJ, variant_label=variant)
        ann = smooth_interpolate_and_extend(blk, 'Households',
                                            np.arange(blk['Year'].min(), 2051))
        ann['HH_Growth'] = ann['Households'].diff()
        fwd = ann.loc[ann['Year'] >= 2026, 'HH_Growth'].values
        levels = [hh_2025_actual]
        for gr in fwd:
            levels.append(levels[-1] + gr)
        return np.array(levels)

    # Legacy variant pairing, always built so the two methods can be compared.
    hh_paired = {pct: _hh_from_variant(v) for pct, v in HOUSEHOLD_VARIANT_MAP.items()}
    S_path = df_forecast['PopTotal_50th'].values / hh_paired['50th']

    # [Route A] household size from the (near-)matched vintage pair
    _pop_k = load_national_pop_projection(variant=HH_SIZE_VARIANT).set_index('Year')['Population']
    _hh_k = extract_household_projection_block(FILE_HOUSEHOLDS_PROJ,
                                               variant_label=HH_SIZE_VARIANT).set_index('Year')['Households']
    _common = sorted(set(_pop_k.index) & set(_hh_k.index))
    S_knots = pd.DataFrame({'Year': _common,
                            'S': [_pop_k[y] / _hh_k[y] for y in _common]})
    _S_ann = smooth_interpolate_and_extend(S_knots, 'S', np.arange(min(_common), 2051)).set_index('Year')['S']
    S_statsnz = _S_ann.reindex(forecast_years).values
    S_matched = float(hist_S.loc[2025]) * S_statsnz / S_statsnz[0]

    if HOUSEHOLD_METHOD == 'matched_size':
        S_used = S_matched
    elif HOUSEHOLD_METHOD == 'single_living_arrangement':
        S_used = S_path
    else:
        S_used = None
    # ---- migration-responsive household size -------------------------------
    hh_response = None
    if HOUSEHOLD_METHOD == 'matched_size' and HH_SIZE_RESPONSE:
        _yr = years_hist[years_hist >= CALIB_START_YEAR]
        _dS = hist_S.diff().loc[_yr].values
        _dP = hist_pop.diff().loc[_yr].values
        _X = np.c_[np.ones(len(_yr)), _dP, _yr - _yr.mean()]
        _beta, *_ = np.linalg.lstsq(_X, _dS, rcond=None)
        b_resp = float(_beta[1])
        _res = _dS - _X @ _beta
        if DEVIATION_PERSISTENCE == 'estimated':
            rho = float(np.clip(np.corrcoef(_res[:-1], _res[1:])[0, 1], 0.0, 0.95))
        else:
            rho = float(DEVIATION_PERSISTENCE)
        _r2 = 1 - (_res ** 2).sum() / ((_dS - _dS.mean()) ** 2).sum()
        # The residuals are autocorrelated (that is what rho measures), so the
        # ordinary OLS standard error of b is invalid. Newey-West (1987) HAC
        # standard error, Bartlett kernel, lag floor(4 (n/100)^(2/9)).
        _n = len(_res)
        _L = int(np.floor(4 * (_n / 100) ** (2 / 9)))
        _Xe = _X * _res[:, None]
        _S = _Xe.T @ _Xe
        for _l in range(1, _L + 1):
            _G = _Xe[_l:].T @ _Xe[:-_l]
            _S += (1 - _l / (_L + 1)) * (_G + _G.T)
        _XtXi = np.linalg.inv(_X.T @ _X)
        _se_hac = float(np.sqrt((_XtXi @ _S @ _XtXi)[1, 1] * _n / (_n - _X.shape[1])))
        _se_ols = float(np.sqrt((_res ** 2).sum() / (_n - _X.shape[1]) * _XtXi[1, 1]))
        # population growth behind Stats NZ's household-size path (same vintage)
        _pk = _pop_k.reset_index().rename(columns={'index': 'Year'})
        _pref = smooth_interpolate_and_extend(_pk, 'Population',
                                              np.arange(int(_pk['Year'].min()), 2051)).set_index('Year')['Population']
        dP_ref = _pref.diff().reindex(forecast_years).values
        dS_snz = np.diff(S_matched)                              # 2026..2050
        dS_snz_2025 = float(S_matched[0] * (_S_ann.loc[2025] - _S_ann.loc[2024]) / _S_ann.loc[2025])
        dS_obs_2025 = float(hist_S.loc[2025] - hist_S.loc[2024])
        dP_obs_2025 = float(hist_pop.loc[2025] - hist_pop.loc[2024])
        e_2025 = dS_obs_2025 - (dS_snz_2025 + b_resp * (dP_obs_2025 - dP_ref[0]))
        fade = rho ** np.arange(1, len(forecast_years))
        # Migration explains part of 2025's fall (b x the migration shortfall);
        # that part does NOT continue once migration recovers. Only the
        # unexplained remainder e_2025 carries forward, fading at rho. b is not
        # applied year after year: our population differs from Stats NZ's by a
        # persistent VINTAGE gap, not a migration shock, and sustained migration
        # is housed rather than packed (2011-20: +75,800/yr, S rose only 0.002/yr).
        dS = dS_snz + e_2025 * fade
        S_resp = np.concatenate([[S_matched[0]], S_matched[0] + np.cumsum(dS)])
        S_by_pct = {pct: S_resp for pct in ['5th', '50th', '95th']}
        hh_response = dict(b=b_resp, se_hac=_se_hac, se_ols=_se_ols, hac_lag=_L,
                           rho=rho, r2=_r2, e_2025=e_2025, dS_obs_2025=dS_obs_2025,
                           dS_snz_2025=dS_snz_2025, dP_obs_2025=dP_obs_2025, dP_ref=dP_ref,
                           S_by_pct=S_by_pct, S_snz=S_matched.copy(), dS_hist=_dS, dP_hist=_dP,
                           years_fit=_yr)

    if S_used is not None:
        households_forecast = {pct: df_forecast[f'PopTotal_{pct}'].values
                               / (hh_response['S_by_pct'][pct] if hh_response else S_used)
                               for pct in ['5th', '50th', '95th']}
    else:
        households_forecast = hh_paired

    print(f"\n[Route A] household size from {FILE_POP_SIZE_PAIR} / {FILE_HOUSEHOLDS_PROJ} "
          f"({HH_SIZE_VARIANT})")
    print("   knot   " + "  ".join(f"{int(y)}" for y in S_knots['Year']))
    print("   S      " + "  ".join(f"{v:.3f}" for v in S_knots['S']))
    if hh_response:
        h = hh_response
        print(f"   household size responds to migration: b = {h['b']:.2e} per person "
              f"(r2 {h['r2']:.2f}), deviations persist rho = {h['rho']:.2f}/yr")
        print(f"   b standard error: OLS {h['se_ols']:.2e} | Newey-West HAC (lag {h['hac_lag']}) "
              f"{h['se_hac']:.2e} -> t = {h['b'] / h['se_hac']:.1f}")
        print(f"   2025: observed dS {h['dS_obs_2025']:+.4f} vs trend {h['dS_snz_2025']:+.4f} at "
              f"{h['dP_obs_2025']:,.0f} people (Stats NZ assumed {h['dP_ref'][0]:,.0f}) "
              f"-> deviation {h['e_2025']:+.4f}, fading")
        _mig = h['b'] * (h['dP_obs_2025'] - h['dP_ref'][0])
        print(f"   of 2025's fall: {_mig:+.4f} from low migration (ends as migration recovers), "
              f"{h['e_2025']:+.4f} unexplained (carries, fading)")
        print(f"   dwellings beyond formation: 2025 deviation {other_dev_2025:+,.0f}, "
              f"persistence {rho_other:.2f}/yr")
        print(f"   household size 2050: {h['S_by_pct']['50th'][-1]:.3f}  "
              f"(Stats NZ path alone {h['S_snz'][-1]:.3f})")
    print(f"   rebased on observed 2025 (S = {hist_S.loc[2025]:.3f}): "
          f"2030 {S_matched[5]:.3f} | 2040 {S_matched[15]:.3f} | 2050 {S_matched[-1]:.3f}")
    if VERBOSE:   # comparison against the earlier household methods
        print(f"   (median household size 2050: Route B {S_path[-1]:.3f} | Route A {S_matched[-1]:.3f})")

        print(f"\nHousehold method: {HOUSEHOLD_METHOD}")
        print(f"   {'Variant':<9}{'S 2050 paired':>15}{'S 2050 now':>13}"
              f"{'new HH/yr paired':>19}{'new HH/yr now':>16}")
        for pct in ['5th', '50th', '95th']:
            sp = df_forecast[f'PopTotal_{pct}'].values[-1] / hh_paired[pct][-1]
            sn = df_forecast[f'PopTotal_{pct}'].values[-1] / households_forecast[pct][-1]
            gp = np.diff(hh_paired[pct]).mean()
            gn = np.diff(households_forecast[pct]).mean()
            print(f"   {pct:<9}{sp:>15.3f}{sn:>13.3f}{gp:>19,.0f}{gn:>16,.0f}")
        print(f"   Observed S: 2019 = {hist_S.loc[2019]:.3f}, 2025 = {hist_S.loc[2025]:.3f}; "
              f"historical range {hist_S.min():.3f}-{hist_S.max():.3f}")

    # ------------------------------------------------------------------
    # 8. FORWARD MIX, OLF AND DWELLING SIZE
    # ------------------------------------------------------------------
    evolving_gfa_shares = fit_evolving_mix(hist_shares, shares_2025, forecast_years,
                                           DAMPING_PHI, TREND_WINDOW_START, typ_names)
    future_blended_olf_bim = blend_per_gfa_share(evolving_gfa_shares, OLF_NET_BIM, typ_names)

    # [FIX f] realised dwelling size held at its recent observed level per
    # typology (parallel to holding OLF constant); the blended value still moves
    # because the typology mix moves.
    future_dwelling_size = blend_per_gfa_share(evolving_gfa_shares, size_ref, typ_names)
    if DEMAND_BASIS == 'per_resident':
        # S is variant-specific, so area per resident is resolved per variant
        # inside the forecast loop; this holds the mix-driven part.
        future_blended_olf = None
    else:
        future_blended_olf = blend_per_gfa_share(evolving_gfa_shares, OLF_USED, typ_names)

    # ------------------------------------------------------------------
    # 9. FORWARD DEMAND
    # ------------------------------------------------------------------
    floor_report, growth_check, identity_report, stock_fwd = {}, {}, {}, {}
    results = {}
    # Under the stock basis the model reports BUILT floor area, so the observed
    # 2025 consents are converted with the completion rate.
    real_2025_total = float(hist_total_gfa.loc[2025]) * (
        COMPLETION_RATE if CONSUMPTION_BASIS == 'stock_vacancy' else 1.0)

    for col in ['5th', '50th', '95th']:
        pop_total = df_forecast[f'PopTotal_{col}'].values
        pop_growth = df_forecast[f'PopGrowth_{col}'].clip(lower=0).values
        hh_arr = households_forecast[col]

        S_f = pop_total / hh_arr
        if DEMAND_BASIS == 'per_resident':
            olf_f = future_dwelling_size.values / S_f
        else:
            olf_f = future_blended_olf.values
        occ_per_dw_f = S_f * olf_f
        d_hh_raw = np.insert(np.diff(hh_arr), 0, 0)
        d_hh_f = np.maximum(d_hh_raw, 0.0) if FLOOR_HOUSEHOLD_DECLINE else d_hh_raw
        floor_report[col] = {'years': int((d_hh_raw[1:] < 0).sum()),
                             'area': float((np.minimum(d_hh_raw, 0) * occ_per_dw_f)[1:].sum())}

        g_gross = pop_growth * olf_f
        structural = d_hh_f * occ_per_dw_f
        hs_raw = structural - g_gross
        hs_pos = np.maximum(0, hs_raw)
        hs_avoided = np.abs(np.minimum(0, hs_raw))
        g_demand = g_gross - hs_avoided          # growth net of consolidation (>= 0)

        # Extra space inside new dwellings beyond what their occupants require.
        extra_space = np.clip(d_hh_f * (future_dwelling_size.values - occ_per_dw_f), 0, None)
        c_gross = consumption_gross(pop_total, d_hh_f, extra_space,
                                    hh_levels=hh_arr, dwelling_size=future_dwelling_size.values)
        if CONSUMPTION_BASIS == 'stock_vacancy':
            _u, _a, _d, _n = other_dwellings(hh_arr, d_hh_f)
            stock_fwd[col] = dict(allow=_a, demol=_d, uncons=_n, repl=_d + _n,
                                  stock=hh_arr / (1.0 - v_forward))
            vac_gfa = _a * future_dwelling_size.values        # vacancy allowance, m2
            repl_gfa = _d * future_dwelling_size.values       # demolition replacement, m2
            unc_gfa = _n * future_dwelling_size.values        # unconsented additions, m2 (<0)
        else:
            vac_gfa = repl_gfa = unc_gfa = None               # 'other' not decomposed
        growth_check[col] = float(g_demand[1:].min())

        g_demand[0] = real_2025_total * anchor['growth']
        hs_pos[0] = real_2025_total * anchor['housesplit']
        hs_avoided[0] = 0.0
        c_gross[0] = real_2025_total * anchor['consumption']

        # [NEW g] Split consumption into the space it puts INSIDE new dwellings
        # beyond what their occupants require, and everything else.
        #   extra_space = dHH x (realised dwelling size - occupied area)
        #   other       = consumption - extra_space
        # Realised dwelling size is held at its recent observed level per
        # typology; the blended value still moves with the typology mix.
        extra_space[0] = c_gross[0] * anchor_extra_share
        other_cons = c_gross - extra_space
        if vac_gfa is None:
            vac_gfa = other_cons.copy()
            repl_gfa, unc_gfa = np.zeros_like(other_cons), np.zeros_like(other_cons)
        # 2025 is the observed anchor: split its 'other' in the 2026 proportions.
        _t1 = vac_gfa[1] + repl_gfa[1] + unc_gfa[1]
        _t1 = _t1 if abs(_t1) > 1e-9 else 1.0
        for _arr in (vac_gfa, repl_gfa, unc_gfa):
            _arr[0] = other_cons[0] * _arr[1] / _t1

        total = g_demand + hs_pos + c_gross
        identity_report[col] = float(
            np.abs(total[1:] - (structural + c_gross)[1:]).max()
            / max(np.abs((structural + c_gross)[1:]).mean(), 1e-9))

        results[col] = dict(total=total, growth=g_demand, growth_gross=g_gross,
                            hs_pos=hs_pos, hs_avoided=hs_avoided, c_gross=c_gross,
                            extra=extra_space, other=other_cons, vac=vac_gfa, repl=repl_gfa, unc=unc_gfa,
                            structural=structural, occ_per_dw=occ_per_dw_f, d_hh=d_hh_f)

        df_forecast[f'Ann_GFA_Total_{col}'] = total
        df_forecast[f'Ann_GFA_Growth_{col}'] = g_demand
        df_forecast[f'Ann_GFA_HouseSplit_Pos_{col}'] = hs_pos
        df_forecast[f'Ann_GFA_HouseSplit_Avoided_{col}'] = hs_avoided
        df_forecast[f'Ann_GFA_Consumption_{col}'] = c_gross
        df_forecast[f'Ann_GFA_Cons_ExtraSpace_{col}'] = extra_space
        df_forecast[f'Ann_GFA_Cons_Other_{col}'] = other_cons
        df_forecast[f'Ann_GFA_Cons_Vacancy_{col}'] = vac_gfa
        df_forecast[f'Ann_GFA_Cons_Replacement_{col}'] = repl_gfa
        df_forecast[f'Ann_GFA_Cons_Unconsented_{col}'] = unc_gfa

    # Projections are BUILT floor area under the stock basis, so history is put on
    # the same basis (consents x completion rate) wherever the two are joined.
    built_factor = COMPLETION_RATE if CONSUMPTION_BASIS == 'stock_vacancy' else 1.0
    hist_cum = (hist_total_gfa * built_factor).cumsum()
    gfa_2025_cum = float(hist_cum.loc[2025])
    for col in ['5th', '50th', '95th']:
        fwd = df_forecast[f'Ann_GFA_Total_{col}'].cumsum() - df_forecast[f'Ann_GFA_Total_{col}'].iloc[0]
        df_forecast[f'Cum_GFA_Total_{col}'] = gfa_2025_cum + fwd

    # ------------------------------------------------------------------
    # 10. TYPOLOGY SPLIT AND CARBON
    # ------------------------------------------------------------------
    def split_typ(vals):
        return pd.DataFrame({n: vals * evolving_gfa_shares[n].values for n in typ_names},
                            index=forecast_years)

    evol_typ_growth = split_typ(df_forecast['Ann_GFA_Growth_50th'].values)
    evol_typ_hs_pos = split_typ(df_forecast['Ann_GFA_HouseSplit_Pos_50th'].values)
    evol_typ_avoided = split_typ(df_forecast['Ann_GFA_HouseSplit_Avoided_50th'].values)
    evol_typ_cons = split_typ(df_forecast['Ann_GFA_Consumption_50th'].values)
    evol_typ_extra = split_typ(df_forecast['Ann_GFA_Cons_ExtraSpace_50th'].values)
    evol_typ_other = split_typ(df_forecast['Ann_GFA_Cons_Other_50th'].values)
    evol_typ_vac = split_typ(df_forecast['Ann_GFA_Cons_Vacancy_50th'].values)
    evol_typ_repl = split_typ(df_forecast['Ann_GFA_Cons_Replacement_50th'].values)
    evol_typ_unc = split_typ(df_forecast['Ann_GFA_Cons_Unconsented_50th'].values)
    evol_typ_total = split_typ(df_forecast['Ann_GFA_Total_50th'].values)

    # The 2025 row is the observed anchor. It is put on the same BUILT basis as
    # the projection (consents x completion rate), as the national total is.
    for n in typ_names:
        evol_typ_total.loc[2025, n] = hist_typ_gfa.loc[2025, n] * built_factor
        evol_typ_growth.loc[2025, n] = hist_typ_gfa.loc[2025, n] * built_factor * anchor['growth']
        evol_typ_hs_pos.loc[2025, n] = hist_typ_gfa.loc[2025, n] * built_factor * anchor['housesplit']
        evol_typ_avoided.loc[2025, n] = 0.0
        evol_typ_cons.loc[2025, n] = hist_typ_gfa.loc[2025, n] * built_factor * anchor['consumption']
        evol_typ_extra.loc[2025, n] = hist_typ_gfa.loc[2025, n] * built_factor * anchor['consumption'] * anchor_extra_share
        evol_typ_other.loc[2025, n] = hist_typ_gfa.loc[2025, n] * built_factor * anchor['consumption'] * (1 - anchor_extra_share)
        _o1 = float(df_forecast['Ann_GFA_Cons_Other_50th'].iloc[1]) or 1.0
        for _ev, _c in ((evol_typ_vac, 'Vacancy'), (evol_typ_repl, 'Replacement'),
                        (evol_typ_unc, 'Unconsented')):
            _ev.loc[2025, n] = (evol_typ_other.loc[2025, n]
                                * float(df_forecast[f'Ann_GFA_Cons_{_c}_50th'].iloc[1]) / _o1)

    # Constant over time: materials plus soil, no decarbonisation assumed.
    intensity = pd.DataFrame({n: np.full(len(forecast_years), T_BASELINE_2025[n])
                              for n in typ_names}, index=forecast_years)

    carbon_growth_typ = evol_typ_growth * intensity
    carbon_hs_pos_typ = evol_typ_hs_pos * intensity
    carbon_avoided_typ = evol_typ_avoided * intensity
    carbon_cons_typ = evol_typ_cons * intensity
    carbon_extra_typ = evol_typ_extra * intensity
    carbon_other_typ = evol_typ_other * intensity
    carbon_vac_typ = evol_typ_vac * intensity
    carbon_repl_typ = evol_typ_repl * intensity
    carbon_unc_typ = evol_typ_unc * intensity
    carbon_total_typ = evol_typ_total * intensity

    tot_carbon_median = float(carbon_total_typ.iloc[1:].sum().sum() / 1e6)

    # ==================================================================
    # VERIFICATION
    # ==================================================================
    print("\n" + "=" * 78)
    print(" VERIFICATION")
    print("=" * 78)
    print(" [1] Growth net of consolidation stays >= 0; household-decline floor")
    for c in ['5th', '50th', '95th']:
        fr = floor_report[c]
        ok = growth_check[c] >= -1e-6
        floor_txt = ("floor never binds" if fr['years'] == 0 else
                     f"households decline in {fr['years']} yr(s); "
                     f"{-fr['area'] / 1e6:.2f} Mm2 of negative structural demand "
                     f"{'floored to 0 (-> vacancy)' if FLOOR_HOUSEHOLD_DECLINE else 'kept'}")
        print(f"     {c:<5} {'OK  ' if ok else 'FAIL'}  {floor_txt}")
    print(" [2] Structural identity  total == structural + c_gross")
    _band = {c: results[c]['total'][1:].sum() / 1e6 for c in ['5th', '50th', '95th']}
    for c in ['5th', '50th', '95th']:
        print(f"     {c:<5} {'OK  ' if identity_report[c] < 1e-6 else 'FAIL'}  "
              f"max relative deviation = {identity_report[c]:.2e}")
    print(f" [3] Population-only band (household size, mix, dwelling size and carbon\n"
          f"     factors held fixed), total GFA 2026-2050 (Mm2): "
          f"5th {_band['5th']:.2f} | 50th {_band['50th']:.2f} | 95th {_band['95th']:.2f}")
    _mix_int_all = sum(evolving_gfa_shares[t].values * T_BASELINE_2025[t] for t in typ_names)
    if CONSUMPTION_BASIS == 'stock_vacancy':
        _sf = stock_fwd['50th']
        _prev = np.concatenate([[_sf['stock'][0]], _sf['stock'][:-1]])[1:]
        _D = future_dwelling_size.values[1:]
        base_net = DEMOLITION_RATE + unconsented_rate

        def _band_line(lab, cal, mark=''):
            dr = (cal['demol_rate'] + cal['rate_unc']) - base_net
            g_ = _band['50th'] + dr * (_prev * _D).sum() / 1e6
            c_ = tot_carbon_median + dr * (_prev * _D * _mix_int_all[1:]).sum() / 1e6
            print(f"     {lab:<34} demol {100*cal['demol_rate']:.3f}% | unconsented "
                  f"{100*cal['rate_unc']:+.3f}% -> built {g_:6.2f} Mm2 | {c_:9,.0f} kt{mark}")
        print(" [4] Stock-term sensitivities (median):")
        for sh in (empty_share_measured - PRE2013_EMPTY_SHARE_BAND, empty_share_measured,
                   empty_share_measured + PRE2013_EMPTY_SHARE_BAND):
            _band_line(f"pre-2013 empty share {100*sh:.0f}%", calibrate_stock(sh),
                       '  <- in use' if sh == empty_share_measured else '')
        for cr in COMPLETION_RATE_BAND:
            _band_line(f"completion rate {100*cr:.0f}%", calibrate_stock(empty_share_measured, completion=cr))
        for dr_ in DEMOLITION_RATE_BAND:
            _band_line(f"demolition rate {100*dr_:.2f}% (split only)",
                       calibrate_stock(empty_share_measured, demol=dr_))
    if CONSUMPTION_BASIS == 'extra_space_plus_other':
        _P = df_forecast['PopTotal_50th'].values[1:]
        _mix_int = sum(evolving_gfa_shares[t].values[1:] * T_BASELINE_2025[t]
                       for t in typ_names)
        print(f" [4] 'Other' uncertainty band (median demographics), 2026-2050:")
        for case in ['low', 'central', 'high']:
            dr = other_pp[case] - other_rate
            g_ = _band['50th'] + dr * _P.sum() / 1e6
            c_ = tot_carbon_median + dr * (_P * _mix_int).sum() / 1e6
            mark = '  <- in use' if case == OTHER_CASE else ''
            print(f"     {case:<8} other = {other_pp[case]:.4f} m2/person -> "
                  f"GFA {g_:6.2f} Mm2 | carbon {c_:9,.0f} kt{mark}")

    # ------------------------------------------------------------------
    # STOCK, VACANCY AND REPLACEMENT
    # ------------------------------------------------------------------
    sc = stock_cal
    wcal = years_hist >= DEMOLITION_CALIB_START
    print("\n" + "=" * 78)
    print(" STOCK, VACANCY, DEMOLITION AND UNCONSENTED ADDITIONS  (built basis)")
    print("=" * 78)
    print("   vacancy (empty / private dwellings): " +
          " | ".join(f"{y} {100*v:.2f}%" for y, v in sc['knots'].items()) +
          f"  -> held at {100*v_forward:.2f}% forward")
    print(f"   build duration (under construction / consents): " +
          " | ".join(f"{y} {d:.2f} yr" for y, d in build_duration.items()))
    nb_hist = COMPLETION_RATE * hist_total_units[wcal].mean()
    print(f"\n   The stock bucket, {DEMOLITION_CALIB_START}-2025 mean per year (dwellings):")
    print(f"     {'new households':<46}{d_hh[wcal].mean():>9,.0f}")
    print(f"     {'+ vacancy allowance':<46}{sc['allow'][wcal].mean():>9,.0f}")
    print(f"     {'+ vacancy change':<46}{sc['change'][wcal].mean():>9,.0f}")
    print(f"     {f'+ demolitions replaced ({100*DEMOLITION_RATE:.3f}% of stock, fixed)':<46}"
          f"{sc['demol'][wcal].mean():>9,.0f}")
    print(f"     {'- unconsented additions (calibrated residual)':<46}{sc['uncons'][wcal].mean():>9,.0f}")
    print(f"     {'= dwellings built':<46}{nb_hist:>9,.0f}")
    print(f"     {f'/ completion rate {COMPLETION_RATE:.2f} = consents':<46}"
          f"{hist_total_units[wcal].mean():>9,.0f}  (observed)")
    print(f"   unconsented additions = {100*unconsented_rate:+.3f}% of stock per year "
          f"({100*sc['uncons'][wcal].mean()/nb_hist:+.1f}% of building)")
    neg = int((sc['net'][wcal] < 0).sum())
    print(f"   single years where demolition < unconsented additions: {neg}/{int(wcal.sum())} "
          f"(vacancy interpolated between censuses; only the long-run rate is used)")
    # Plausibility check: what would 'residents away counted as vacant' require?
    _all = (census['unoccupied'] / census['total_private']).to_dict()
    _v = pd.Series(np.interp(years_hist.astype(float), list(_all), list(_all.values())),
                   index=years_hist)
    _prev = (hist_hh / (1 - _v)).shift(1)
    _net_all = (COMPLETION_RATE * hist_total_units - d_hh - d_hh * _v / (1 - _v)
                - hist_hh.shift(1) * (1 / (1 - _v)).diff())
    _unc_all = (_net_all - DEMOLITION_RATE * _prev)[wcal].mean()
    print(f"   [check] counting 'residents away' as vacant would need unconsented additions of "
          f"{_unc_all:,.0f}/yr ({100*_unc_all/nb_hist:+.0f}% of building) vs "
          f"{sc['uncons'][wcal].mean():,.0f} -> rejected as implausible")
    if ext is not None:
        # Retirement-village units: in the all-category dwelling count but not in
        # the three typology columns. Their residents are private households, so
        # when they are left out of 'built' they land in the residual.
        rv_built = COMPLETION_RATE * (ext - hist_total_units)
        rv_mean = float(rv_built[wcal].mean())
        rest = float(sc['uncons'][wcal].mean()) + rv_mean
        rest_rate = float((sc['uncons'] + rv_built)[wcal].sum() / sc['stock'].shift(1)[wcal].sum())
        print(f"   [check] of the residual {sc['uncons'][wcal].mean():,.0f}/yr, retirement-village units "
              f"built outside scope account for {-rv_mean:,.0f}/yr "
              f"({100 * rv_mean / -sc['uncons'][wcal].mean():.0f}%); remainder {rest:,.0f}/yr "
              f"({100 * rest_rate:+.3f}% of stock)")
        for a_, b_ in [(1992, 2005), (2006, 2015), (2016, 2025)]:
            print(f"            {a_}-{b_}: residual {sc['uncons'].loc[a_:b_].mean():7,.0f} | "
                  f"retirement villages {-rv_built.loc[a_:b_].mean():7,.0f}")
    if CONSUMPTION_BASIS == 'stock_vacancy':
        _sf = stock_fwd['50th']
        _nb = (results['50th']['total'][1:] / future_dwelling_size.values[1:]).mean()
        print(f"\n   Forward 2026-2050, median, dwellings per year:")
        for lab, v_ in [('new households', results['50th']['d_hh'][1:].mean()),
                        ('+ vacancy allowance', _sf['allow'][1:].mean()),
                        ('+ demolitions replaced', _sf['demol'][1:].mean()),
                        ('- unconsented additions', _sf['uncons'][1:].mean()),
                        ('= dwellings built', _nb)]:
            print(f"     {lab:<30}{v_:>9,.0f}{'' if lab.startswith('=') else f'{100*v_/_nb:>8.1f}%'}")

    if VERBOSE or CONSUMPTION_BASIS in ('per_capita', 'extra_space_plus_other'):   # only relevant to the per-person bases
        # ------------------------------------------------------------------
        # [FIX d] calibration sensitivity
        # ------------------------------------------------------------------
        print("\n" + "=" * 78)
        print(" [FIX d] CONSUMPTION-RATE CALIBRATION SENSITIVITY (m2/person/yr)")
        print("=" * 78)
        r_all = pd.Series(hist_consumption.values / hist_pop.values, index=years_hist)
        print(f"   v2 method  (span 35, adjust=False, from 1991) : "
              f"{r_all.ewm(span=35, adjust=False).mean().iloc[-1]:.4f}   <- seed artefact")
        for sp in [10, 15, 20, 35]:
            v = r_all.loc[CALIB_START_YEAR:].ewm(span=sp, adjust=True).mean().iloc[-1]
            mark = '  <-- ADOPTED' if sp == EWMA_SPAN else ''
            print(f"   EWMA span {sp:<3} adjust=True, from {CALIB_START_YEAR}       : {v:.4f}{mark}")
        print(f"   simple mean, last 10 years                    : {r_all.loc[2016:2025].mean():.4f}")
        print(f"   simple mean, last 5 years                     : {r_all.loc[2021:2025].mean():.4f}")
        sl = stats.linregress(r_all.loc[CALIB_START_YEAR:].index.values,
                              r_all.loc[CALIB_START_YEAR:].values)
        print(f"   linear trend {CALIB_START_YEAR}-2025: slope={sl.slope:+.5f}/yr, "
              f"p={sl.pvalue:.3f}, R2={sl.rvalue ** 2:.3f}")
        print("   -> no significant trend, and every choice lies within a narrow band,")
        print("      so the projection is not sensitive to this calibration decision.")
        print(f"   ADOPTED rate = {rate_consumption:.4f}")
        print(f"   Per-household rate (weighted sums) = {rate_per_household:.1f} m2 per new household")
        print(f"   CONSUMPTION_BASIS in use           = {CONSUMPTION_BASIS}")
        print("\n 'OTHER' PER PERSON (consumption beyond extra space), 1992-2025")
        _y = other_pp_series.index.values.astype(float)
        _ols = stats.linregress(_y, _o)
        _ts = stats.theilslopes(_o, _y)
        _mk = stats.kendalltau(_y, _o)
        _r1 = float(np.corrcoef(_o[:-1], _o[1:])[0, 1])
        print(f"   mean {other_pp['central']:.4f} m2/person | lag-1 autocorrelation {_r1:+.3f}")
        print(f"   ordinary trend  p = {_ols.pvalue:.3f}  (invalid: assumes independent years)")
        print(f"   Theil-Sen slope {_ts[0]:+.5f}/yr, 95% CI [{_ts[2]:+.5f}, {_ts[3]:+.5f}]"
              f" -> {'includes zero' if _ts[2] <= 0 <= _ts[3] else 'excludes zero'}")
        print(f"   Mann-Kendall    p = {_mk.pvalue:.3f}")
        print(f"   -> no defensible trend: held constant. Block bootstrap "
              f"({OTHER_BOOTSTRAP_BLOCK}-yr blocks, {OTHER_BOOTSTRAP_N:,} draws), "
              f"{OTHER_BOOTSTRAP_CI[1] - OTHER_BOOTSTRAP_CI[0]}% interval "
              f"[{other_pp['low']:.4f}, {other_pp['high']:.4f}]")
        print(f"   OTHER_CASE in use = {OTHER_CASE} ({other_rate:.4f} m2/person)")

    if VERBOSE:   # historical space diagnostics; see Diagnostics D, E
        # ------------------------------------------------------------------
        # [FIX f] utilisation diagnostic
        # ------------------------------------------------------------------
        print("\n" + "=" * 78)
        print(" [FIX f] DESIGN CAPACITY vs ACTUAL OCCUPANCY")
        print("=" * 78)
        print(" OLF (your BIM metric) = GFA / (bedrooms+1) = floor area per DESIGN occupant.")
        print(" S = actual people per dwelling. S x OLF is therefore NOT a dwelling size;")
        print(" it is the floor area matching the occupants actually housed. Renamed")
        print(" 'occupied_area_per_dwelling'. Realised dwelling size is measured directly.\n")
        print(f" {'Typology':<12}{'realised size':>14}{'your OLF':>10}{'design cap.':>13}{'implied beds':>14}")
        print(f" {'':<12}{'(m2/dwelling)':>14}{'(m2/occ)':>10}{'(occupants)':>13}{'':>14}")
        for t in typ_names:
            d = float(hist_dwelling_size[t].loc[DWELLING_SIZE_REF[0]:DWELLING_SIZE_REF[1]].mean())
            cap = d / OLF_USED[t]
            print(f" {t:<12}{d:>14.1f}{OLF_USED[t]:>10.2f}{cap:>13.2f}{cap - 1:>14.2f}")
        print(f"\n Blended, 2025: realised {blended_dwelling_size.loc[2025]:.1f} m2/dwelling | "
              f"occupied {occupied_area_per_dwelling.loc[2025]:.1f} m2 | "
              f"design capacity {design_capacity.loc[2025]:.2f} occupants | S {hist_S.loc[2025]:.3f}")
        print(f" UTILISATION (S / design capacity): 2025 = {utilisation.loc[2025]:.3f}, "
              f"range {utilisation.min():.3f}-{utilisation.max():.3f}, "
              f"2020-25 mean = {utilisation.loc[2020:2025].mean():.3f}")
        print(" Under-occupancy of roughly a third is what the consumption term has been")
        print(" absorbing. Quantified next.")

        # ------------------------------------------------------------------
        # [NEW g] splitting consumption: extra space vs extra dwellings
        # ------------------------------------------------------------------
        print("\n" + "=" * 78)
        print(" [NEW g] WHAT IS INSIDE 'CONSUMPTION'?")
        print("=" * 78)
        print(" Consumption = Total - Structural. Structural values each new household")
        print(" at its OCCUPIED area (S x OLF), but dwellings are actually built larger.")
        print(" That difference is real floor area and it lands in the residual:")
        print("   Extra space   = dHH x (realised dwelling size - occupied area)")
        print("   Other         = Consumption - Extra space")
        print("                 = Total - dHH x realised dwelling size")
        print(" 'Other' covers replacement of demolished stock, vacant/second homes,")
        print(" consent-to-occupation timing, and measurement error. It can go NEGATIVE")
        print(" when households form faster than dwellings are consented (people moving")
        print(" into existing stock), which is informative rather than a defect.\n")
        extra_space = d_hh * (blended_dwelling_size - occupied_area_per_dwelling)
        other = hist_consumption - extra_space
        print(f" {'Period':<12}{'Consumption':>13}{'Extra space':>13}{'Other':>10}{'space %':>10}")
        print(f" {'':<12}{'(Mm2/yr)':>13}{'(Mm2/yr)':>13}{'(Mm2/yr)':>10}{'':>10}")
        for lo, hi in [(1996, 2000), (2001, 2005), (2006, 2010), (2011, 2015),
                       (2016, 2020), (2021, 2025)]:
            cc = hist_consumption.loc[lo:hi].mean() / 1e6
            ee = extra_space.loc[lo:hi].mean() / 1e6
            oo = other.loc[lo:hi].mean() / 1e6
            print(f" {f'{lo}-{hi}':<12}{cc:>13.2f}{ee:>13.2f}{oo:>10.2f}{100 * ee / cc:>10.1f}")
        tot_c = hist_consumption.loc[1996:2025].sum()
        print(f"\n 1996-2025 overall: extra space = "
              f"{100 * extra_space.loc[1996:2025].sum() / tot_c:.0f}% of consumption; "
              f"other = {100 * other.loc[1996:2025].sum() / tot_c:.0f}%")
        print(" READING: most of what the model labels 'consumption' is not people buying")
        print(" second homes. It is new dwellings being larger than the occupants they")
        print(" house require. That is a space-per-person story, and it should be named")
        print(" as such in the paper. The annual split is noisy; use period means.")

    # ==================================================================
    # DASHBOARD
    # ==================================================================
    gfa_growth_typ = evol_typ_growth.iloc[1:].sum() / 1e6
    gfa_cons_typ = evol_typ_cons.iloc[1:].sum() / 1e6
    gfa_hs_typ = evol_typ_hs_pos.iloc[1:].sum() / 1e6
    gfa_built_typ = gfa_growth_typ + gfa_cons_typ + gfa_hs_typ
    carbon_built_typ = (carbon_growth_typ.iloc[1:].sum() + carbon_cons_typ.iloc[1:].sum()
                        + carbon_hs_pos_typ.iloc[1:].sum()) / 1e6

    print("\n" + "=" * 80)
    print(f" CUMULATIVE FORECAST SUMMARY (2026-2050) | Damping phi = {DAMPING_PHI}")
    print("=" * 80)
    print(f"{'Typology':<15} | {'Growth GFA':>12} | {'Consumption GFA':>15} | "
          f"{'Total GFA':>12} | {'Carbon':>13}")
    print(f"{'':<15} | {'(million m2)':>12} | {'(million m2)':>15} | "
          f"{'(million m2)':>12} | {'(kt CO2e)':>13}")
    print("-" * 80)
    for n in typ_names:
        print(f"{n:<15} | {gfa_growth_typ[n]:>12.2f} | {gfa_cons_typ[n]:>15.2f} | "
              f"{gfa_built_typ[n]:>12.2f} | {carbon_built_typ[n]:>13,.1f}")
    print("-" * 80)
    tot_built = gfa_built_typ.sum()
    tot_carbon = carbon_built_typ.sum()
    print(f"{'TOTAL MARKET':<15} | {gfa_growth_typ.sum():>12.2f} | {gfa_cons_typ.sum():>15.2f} | "
          f"{tot_built:>12.2f} | {tot_carbon:>13,.1f}")
    print("=" * 80)

    tot_avoided_gfa = df_forecast['Ann_GFA_HouseSplit_Avoided_50th'].iloc[1:].sum() / 1e6
    tot_avoided_c = carbon_avoided_typ.iloc[1:].sum().sum() / 1e6
    print("\nCONSOLIDATION SAVINGS:")
    print(f"   Had household size not risen, an additional {tot_avoided_gfa:.2f} million m2")
    print(f"   would have been required, embodying {tot_avoided_c:,.0f} kt CO2e")
    print(f"   ({100 * tot_avoided_gfa / tot_built:.1f}% of the total built baseline).")
    # ---- demand type summary: every band reported on its own ----
    bands = [('Growth (net of consolidation)', evol_typ_growth, carbon_growth_typ),
             ('House-splitting', evol_typ_hs_pos, carbon_hs_pos_typ),
             ('Consumption: extra space', evol_typ_extra, carbon_extra_typ),
             ('Consumption: vacancy allowance', evol_typ_vac, carbon_vac_typ),
             ('Consumption: demolition replacement', evol_typ_repl, carbon_repl_typ),
             ('Residual: RV units + unconsented', evol_typ_unc, carbon_unc_typ)]
    rows = [(lab, g.iloc[1:].sum().sum() / 1e6, c.iloc[1:].sum().sum() / 1e6) for lab, g, c in bands]
    tg = sum(r[1] for r in rows); tc = sum(r[2] for r in rows)
    print("\n BY DEMAND TYPE, 2026-2050 (median)")
    print(f"   {'':<34}{'floor area':>12}{'share':>8}{'carbon':>12}")
    print(f"   {'':<34}{'(Mm2)':>12}{'':>8}{'(kt CO2e)':>12}")
    for lab, g, c in rows:
        print(f"   {lab:<34}{g:>12.2f}{100 * g / tg:>7.1f}%{c:>12,.0f}")
    print(f"   {'TOTAL BUILT':<34}{tg:>12.2f}{100.0:>7.1f}%{tc:>12,.0f}")
    if CONSUMPTION_BASIS == 'stock_vacancy':
        # Demolition and the residual trade one-for-one in calibration (only
        # their sum is identified by the stock identity), so report the sum too.
        _net_g = rows[4][1] + rows[5][1]
        _net_c = rows[4][2] + rows[5][2]
        print(f"   {'(demolition + residual: identified net)':<34}{_net_g:>12.2f}"
              f"{100 * _net_g / tg:>7.1f}%{_net_c:>12,.0f}")
    if CONSUMPTION_BASIS == 'stock_vacancy':
        print(f"   {f'(consented equivalent, /{COMPLETION_RATE:.2f})':<34}{tg / COMPLETION_RATE:>12.2f}")
    print(f"   {'(avoided by consolidation, not built)':<34}{tot_avoided_gfa:>12.2f}{'':>8}{tot_avoided_c:>12,.0f}")
    print("=" * 80 + "\n")

    # ==================================================================
    # PLOTTING
    # ==================================================================
    stack_colors = [TYPOLOGY_COLORS[n] for n in typ_names]
    plot_years = forecast_years[1:]

    # FIG 1 population
    plt.figure(figsize=(12, 5))
    plt.plot(years_hist, hist_pop.values, color='black', linewidth=2, label='Historical (ERP, 31 Dec)')
    plt.plot(forecast_years, df_forecast['PopTotal_50th'], color='blue', linestyle='--',
             label='Projected Median')
    plt.fill_between(forecast_years, df_forecast['PopTotal_5th'], df_forecast['PopTotal_95th'],
                     color='blue', alpha=0.2, label='Uncertainty (5th/95th)')
    plt.ylabel('Population'); plt.title('New Zealand Population (1991-2050)')
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()

    # FIG 1b households
    plt.figure(figsize=(12, 5))
    plt.plot(years_hist, hist_hh.values, color='black', linewidth=2, label='Historical (31 Dec)')
    plt.plot(forecast_years, households_forecast['50th'], color='darkorange', linestyle='--',
             label='Projected Median')
    plt.fill_between(forecast_years, households_forecast['5th'], households_forecast['95th'],
                     color='darkorange', alpha=0.2,
                     label='5th-95th population percentile (household size fixed)')
    plt.axvline(2025, color='black', linestyle=':', alpha=0.6)
    plt.ylabel('Households'); plt.title('New Zealand Households (1991-2050)')
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()

    # FIG 2 cumulative GFA
    plt.figure(figsize=(13, 7))
    plt.plot(years_hist, hist_cum.values, color='black', linewidth=3, label=f'Historical (consents x {built_factor:.2f} = built)')
    plt.plot(df_forecast['Year'], df_forecast['Cum_GFA_Total_50th'], color='darkred',
             linewidth=2.5, label='Projected Total GFA (Median)')
    plt.fill_between(df_forecast['Year'], df_forecast['Cum_GFA_Total_5th'],
                     df_forecast['Cum_GFA_Total_95th'], color='darkred', alpha=0.2,
                     label='GFA Uncertainty Band')
    plt.ylabel('Cumulative New GFA (m2)')
    plt.title('Cumulative New Residential GFA Projection')
    plt.legend(loc='upper left'); plt.grid(True, alpha=0.3)
    plt.xlim(1991, 2050); plt.tight_layout()

    # FIG 3 annual GFA
    fig3, (bx1, bx2) = plt.subplots(1, 2, figsize=(18, 6))
    bx1.stackplot(plot_years, [evol_typ_total[n].iloc[1:] / 1e6 for n in typ_names],
                  labels=typ_names, colors=stack_colors, alpha=0.85)
    bx1.set_ylabel('Annual new GFA (million m2/yr)')
    bx1.set_title('Annual GFA by Typology (2026-2050)')
    bx1.legend(loc='lower left', fontsize=9); bx1.grid(True, alpha=0.3); bx1.set_xlim(2026, 2050)

    y_g = df_forecast['Ann_GFA_Growth_50th'].iloc[1:].values / 1e6
    y_ce = df_forecast['Ann_GFA_Cons_ExtraSpace_50th'].iloc[1:].values / 1e6
    y_cv = df_forecast['Ann_GFA_Cons_Vacancy_50th'].iloc[1:].values / 1e6
    y_cr = df_forecast['Ann_GFA_Cons_Replacement_50th'].iloc[1:].values / 1e6
    y_cu = df_forecast['Ann_GFA_Cons_Unconsented_50th'].iloc[1:].values / 1e6
    y_h = df_forecast['Ann_GFA_HouseSplit_Pos_50th'].iloc[1:].values / 1e6
    y_a = df_forecast['Ann_GFA_HouseSplit_Avoided_50th'].iloc[1:].values / 1e6
    colls3 = bx2.stackplot(plot_years, y_g, y_ce, y_cv, y_cr, y_h, y_a,
                           labels=DEMAND_LABELS_LEGEND, colors=DEMAND_COLORS, alpha=0.85)
    colls3[-1].set_facecolor((1, 1, 1, 0.2)); colls3[-1].set_edgecolor(HOUSESPLIT_COLOR)
    colls3[-1].set_hatch('//')
    bx2.fill_between(plot_years, 0, y_cu, facecolor='none', edgecolor=UNCONSENTED_COLOR,
                     hatch='xx', linewidth=0, label=UNCONSENTED_LABEL)
    bx2.axhline(0, color='black', lw=0.7)
    bx2.plot(plot_years, y_g + y_ce + y_cv + y_cr + y_h + y_cu, color='black', linestyle='--',
             linewidth=1.5, label='Built floor area (net)')
    bx2.set_title('Annual GFA by Demand Type (2026-2050)')
    bx2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=8); bx2.grid(True, alpha=0.3); bx2.set_xlim(2026, 2050)
    plt.tight_layout()

    # FIG 4 annual carbon
    fig4, (cx1, cx2) = plt.subplots(1, 2, figsize=(18, 6))
    cx1.stackplot(plot_years, [carbon_total_typ[n].iloc[1:] / 1e6 for n in typ_names],
                  labels=typ_names, colors=stack_colors, alpha=0.85)
    cx1.set_ylabel('Annual Carbon (kt CO2e/yr)')
    cx1.set_title('Annual Embodied Carbon by Typology (2026-2050)')
    cx1.legend(loc='lower left', fontsize=9); cx1.grid(True, alpha=0.3); cx1.set_xlim(2026, 2050)

    yc_g = carbon_growth_typ.sum(axis=1).iloc[1:].values / 1e6
    yc_ce = carbon_extra_typ.sum(axis=1).iloc[1:].values / 1e6
    yc_cv = carbon_vac_typ.sum(axis=1).iloc[1:].values / 1e6
    yc_cr = carbon_repl_typ.sum(axis=1).iloc[1:].values / 1e6
    yc_cu = carbon_unc_typ.sum(axis=1).iloc[1:].values / 1e6
    yc_h = carbon_hs_pos_typ.sum(axis=1).iloc[1:].values / 1e6
    yc_a = carbon_avoided_typ.sum(axis=1).iloc[1:].values / 1e6
    colls4 = cx2.stackplot(plot_years, yc_g, yc_ce, yc_cv, yc_cr, yc_h, yc_a,
                           labels=DEMAND_LABELS_LEGEND, colors=DEMAND_COLORS, alpha=0.85)
    colls4[-1].set_facecolor((1, 1, 1, 0.2)); colls4[-1].set_edgecolor(HOUSESPLIT_COLOR)
    colls4[-1].set_hatch('//')
    cx2.fill_between(plot_years, 0, yc_cu, facecolor='none', edgecolor=UNCONSENTED_COLOR,
                     hatch='xx', linewidth=0, label=UNCONSENTED_LABEL)
    cx2.axhline(0, color='black', lw=0.7)
    cx2.plot(plot_years, yc_g + yc_ce + yc_cv + yc_cr + yc_h + yc_cu, color='black', linestyle='--', linewidth=1.5,
             label='Actual Built Carbon')
    cx2.set_title('Annual Embodied Carbon by Demand Type (2026-2050)')
    cx2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=8); cx2.grid(True, alpha=0.3); cx2.set_xlim(2026, 2050)
    plt.tight_layout()

    # FIG 5 cumulative carbon  -- slice BEFORE accumulating
    cum_typ = (carbon_total_typ.iloc[1:] / 1e6).cumsum()
    cum_g = (carbon_growth_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values
    cum_ce = (carbon_extra_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values
    cum_cv = (carbon_vac_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values
    cum_cr = (carbon_repl_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values
    cum_cu = (carbon_unc_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values
    cum_h = (carbon_hs_pos_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values
    cum_a = (carbon_avoided_typ.sum(axis=1).iloc[1:] / 1e6).cumsum().values

    fig5, (dx1, dx2) = plt.subplots(1, 2, figsize=(18, 6))
    dx1.stackplot(plot_years, [cum_typ[n].values for n in typ_names],
                  labels=typ_names, colors=stack_colors, alpha=0.85)
    dx1.set_ylabel('Cumulative Carbon (kt CO2e)')
    dx1.set_title('Cumulative Embodied Carbon by Typology (2026-2050)')
    dx1.legend(loc='lower left', fontsize=9); dx1.grid(True, alpha=0.3); dx1.set_xlim(2026, 2050)

    colls5 = dx2.stackplot(plot_years, cum_g, cum_ce, cum_cv, cum_cr, cum_h, cum_a,
                           labels=DEMAND_LABELS_LEGEND, colors=DEMAND_COLORS, alpha=0.85)
    colls5[-1].set_facecolor((1, 1, 1, 0.2)); colls5[-1].set_edgecolor(HOUSESPLIT_COLOR)
    colls5[-1].set_hatch('//')
    dx2.fill_between(plot_years, 0, cum_cu, facecolor='none', edgecolor=UNCONSENTED_COLOR,
                     hatch='xx', linewidth=0, label=UNCONSENTED_LABEL)
    dx2.axhline(0, color='black', lw=0.7)
    dx2.plot(plot_years, cum_g + cum_ce + cum_cv + cum_cr + cum_h + cum_cu, color='black', linestyle='--',
             linewidth=1.5, label='Actual Built Carbon')
    dx2.set_title('Cumulative Embodied Carbon by Demand Type (2026-2050)')
    dx2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=8); dx2.grid(True, alpha=0.3); dx2.set_xlim(2026, 2050)
    plt.tight_layout()

    # FIG 6 market share
    plt.figure(figsize=(10, 6))
    for n in typ_names:
        plt.plot(hist_shares.index, hist_shares[n] * 100, color=TYPOLOGY_COLORS[n],
                 linewidth=2.5, label=n)
        plt.plot(forecast_years, evolving_gfa_shares[n] * 100, color=TYPOLOGY_COLORS[n],
                 linewidth=2.5, linestyle='--')
    plt.axvline(2025, color='black', linestyle=':', alpha=0.6)
    plt.ylabel('GFA Market Share (%)')
    plt.title(rf'Historical & Projected Typology Market Share ($\phi$ = {DAMPING_PHI})')
    plt.legend(); plt.grid(True, alpha=0.3); plt.xlim(1991, 2050); plt.ylim(0, 100)
    plt.tight_layout()

    # FIG 7 demographic drivers
    fig7, (ex1, ex2) = plt.subplots(1, 2, figsize=(18, 6))
    ex1.plot(years_hist, hist_S.values, color='black', linewidth=2.5, label='Historical (actual)')
    ex1.plot(forecast_years, df_forecast['PopTotal_50th'].values / households_forecast['50th'],
             color='darkorange', linestyle='--', linewidth=2.5, label=f'Projected ({HOUSEHOLD_METHOD})')
    ex1.axvline(2025, color='gray', linestyle=':', alpha=0.6)
    ex1.set_ylabel('People per Household')
    ex1.set_title('Average Household Size (1991-2050)')
    ex1.legend(); ex1.grid(True, alpha=0.3); ex1.set_xlim(1991, 2050)

    ex2.plot(years_hist, d_pop.values, color='blue', linewidth=2, label='Population Growth (hist.)')
    ex2.plot(years_hist, d_hh.values, color='darkorange', linewidth=2, label='HH Formation (hist.)')
    ex2.plot(plot_years, df_forecast['PopGrowth_50th'].values[1:], color='blue',
             linestyle='--', alpha=0.7, label='Pop Growth (proj.)')
    ex2.plot(plot_years, np.diff(households_forecast['50th']), color='darkorange',
             linestyle='--', alpha=0.7, label='HH Formation (proj.)')
    ex2.axvline(2025, color='gray', linestyle=':', alpha=0.6)
    ex2.set_ylabel('Annual Additions')
    ex2.set_title('Population Growth vs Household Formation')
    ex2.legend(); ex2.grid(True, alpha=0.3); ex2.set_xlim(1991, 2050)
    plt.tight_layout()

    # FIG 8 [FIX f / NEW g] space diagnostics
    fig8, (gx1, gx2) = plt.subplots(1, 2, figsize=(18, 6))
    gx1.plot(years_hist, blended_dwelling_size.values, color='#c0392b', linewidth=2.5,
             label='Realised new-dwelling size (GFA / consents)')
    gx1.plot(years_hist, occupied_area_per_dwelling.values, color='#2c3e50', linewidth=2.5,
             linestyle='-.', label='Occupied area per dwelling (S x OLF)')
    gx1.fill_between(years_hist, occupied_area_per_dwelling.values, blended_dwelling_size.values,
                     color='#e67e22', alpha=0.25, label='Excess space (under-utilisation)')
    gx1.set_ylabel('m2 per dwelling'); gx1.set_xlabel('Year')
    gx1.set_title('Realised vs Occupied Floor Area per New Dwelling')
    gx1.legend(loc='lower left', fontsize=9); gx1.grid(True, alpha=0.3)
    gx1.set_xlim(1991, 2025); gx1.set_ylim(0, None)

    gx2.plot(years_hist, utilisation.values * 100, color='#2980b9', linewidth=2.5)
    gx2.set_ylabel('Utilisation:  S / design capacity  (%)'); gx2.set_xlabel('Year')
    gx2.set_title('Occupancy Utilisation of New Dwellings')
    gx2.grid(True, alpha=0.3); gx2.set_xlim(1991, 2025); gx2.set_ylim(0, 100)
    gx2.axhline(100, color='black', linewidth=0.8, alpha=0.5)
    gx2.annotate('design capacity (bedrooms + 1)', xy=(1993, 101), fontsize=9, alpha=0.7)
    plt.tight_layout()


    # ==================================================================
    # MATERIAL FLOW ACCOUNTING  (median variant, 2026-2050)
    # ==================================================================
    # Annual floor area by typology x the case-study intensity of each material
    # and of soil. Soil is kept separate throughout: it is land-use change, not
    # a material, and nothing that acts on materials should act on it.
    plot_years = forecast_years[1:]
    flow_annual = pd.DataFrame(
        {m: sum(evol_typ_total[t].values * MAT_INTENSITY.loc[m, t] for t in typ_names)
         for m in MATERIALS}, index=forecast_years)
    flow_annual['SOIL'] = sum(evol_typ_total[t].values * SOIL_INTENSITY[t]
                              for t in typ_names)
    flow_annual = flow_annual.loc[plot_years]              # drop the 2025 anchor
    flow_cum = flow_annual.cumsum()

    # Carbon by demand type x material, using each demand band's own mix.
    demand_bands = {'Growth (net of consolidation)': evol_typ_growth,
                    'House-splitting': evol_typ_hs_pos,
                    'Consumption: extra space': evol_typ_extra,
                    'Consumption: vacancy': evol_typ_vac,
                    'Consumption: demolition': evol_typ_repl,
                    'Residual: RV + unconsented': evol_typ_unc}
    dem_mat = pd.DataFrame(
        {lab: [sum(df[t].iloc[1:].sum() * MAT_INTENSITY.loc[m, t] for t in typ_names)
               for m in MATERIALS] + [sum(df[t].iloc[1:].sum() * SOIL_INTENSITY[t]
                                          for t in typ_names)]
         for lab, df in demand_bands.items()}, index=MATERIALS + ['SOIL'])

    check = abs(flow_annual.sum().sum() - carbon_total_typ.iloc[1:].sum().sum())
    print("\n" + "=" * 78)
    print(" MATERIAL FLOW ACCOUNTING 2026-2050  (median)")
    print("=" * 78)
    print(f" [check] material + soil total vs typology total: "
          f"{check / 1e6:.3f} kt difference "
          f"({'OK' if check / max(flow_annual.sum().sum(), 1) < 1e-9 else 'FAIL'})")
    tbl = pd.DataFrame({'kt CO2e': flow_annual.sum() / 1e6,
                        'share %': 100 * flow_annual.sum() / flow_annual.sum().sum(),
                        'kt in 2026': flow_annual.loc[2026] / 1e6,
                        'kt in 2050': flow_annual.loc[2050] / 1e6})
    tbl = tbl.sort_values('kt CO2e', ascending=False)
    tbl.loc['TOTAL'] = [tbl['kt CO2e'].sum(), 100.0,
                        tbl['kt in 2026'].sum(), tbl['kt in 2050'].sum()]
    print(tbl.round(1).to_string())

    # Upfront (A1-A5) vs later stages. B2/B4 and C1-C4 are emitted over the
    # service life and at end of life, decades after construction; above they
    # are booked in the construction year (a static LCA convention). The split
    # lets upfront carbon be compared with annual budgets on its own.
    stage_int = (mat_scope.pivot_table(index='Stage', columns='Typology',
                                       values='kgCO2e_per_m2', aggfunc='sum')
                 .reindex(index=STAGES_IN_SCOPE, columns=typ_names).fillna(0.0))
    _soil = sum(evol_typ_total[t].values[1:].sum() * SOIL_INTENSITY[t] for t in typ_names)
    print("\n BY LIFE-CYCLE STAGE  [kt CO2e, 2026-2050]  (soil = land-use change at construction)")
    _st_tot = 0.0
    for stg in STAGES_IN_SCOPE:
        v = sum(evol_typ_total[t].values[1:].sum() * stage_int.loc[stg, t] for t in typ_names) / 1e6
        _st_tot += v
        print(f"   {stg:<10}{v:>10,.0f}")
    print(f"   {'SOIL':<10}{_soil / 1e6:>10,.0f}")
    _upfront = sum(evol_typ_total[t].values[1:].sum() * stage_int.loc[['A1-A3', 'A4-A5'], t].sum()
                   for t in typ_names) / 1e6
    print(f"   upfront (A1-A5 + soil) {_upfront + _soil / 1e6:,.0f} kt | "
          f"later stages (B2,B4, C1-C4) {_st_tot - _upfront:,.0f} kt | "
          f"[check] sum {_st_tot + _soil / 1e6:,.0f} vs {tot_carbon_median:,.0f}")

    print("\n BY DEMAND TYPE AND MATERIAL  [kt CO2e, 2026-2050]")
    dm = (dem_mat / 1e6).round(1)
    dm['TOTAL'] = dm.sum(axis=1)
    dm = dm.sort_values('TOTAL', ascending=False)
    dm.loc['TOTAL'] = dm.sum()
    print(dm.to_string())

    # --- FIG 9: material flows ---------------------------------------
    fig9, (mx1, mx2) = plt.subplots(1, 2, figsize=(18, 6))
    order = flow_annual.sum().sort_values(ascending=False).index
    pal = plt.get_cmap('tab20')(np.linspace(0, 1, len(order)))
    mx1.stackplot(plot_years, [flow_annual[m] / 1e6 for m in order],
                  labels=list(order), colors=pal, alpha=0.9)
    mx1.set_ylabel('kt CO$_2$e per year'); mx1.set_xlabel('Year')
    mx1.set_title('Annual embodied carbon by material (2026-2050)\n'
                  'soil shown separately: land-use change, not a material')
    mx1.legend(loc='upper right', fontsize=7, ncol=2); mx1.grid(True, alpha=0.3)
    mx1.set_xlim(2026, 2050)

    mx2.stackplot(plot_years, [flow_cum[m] / 1e6 for m in order],
                  labels=list(order), colors=pal, alpha=0.9)
    mx2.set_ylabel('cumulative kt CO$_2$e'); mx2.set_xlabel('Year')
    mx2.set_title('Cumulative embodied carbon by material (2026-2050)')
    mx2.legend(loc='upper left', fontsize=7, ncol=2); mx2.grid(True, alpha=0.3)
    mx2.set_xlim(2026, 2050)
    plt.tight_layout()

    # Every intermediate result is returned, so Diagnostics.py and
    # Sensitivity.py read the same run instead of re-deriving anything.
    state = dict(locals())
    if SHOW_PLOTS:
        plt.show()
    else:
        plt.close('all')
    return state


if __name__ == "__main__":
    main()

# ============================================================
# CHANGELOG v2 -> v3
# ============================================================
# [FIX c] Consumption is now  Total - Structural  in BOTH the historical
#         calibration and the forward projection. v2 used Total - Growth - HS_pos
#         historically, which differs in the 14 consolidation years and left the
#         two halves of the model on inconsistent definitions.
# [FIX d] EWMA now uses adjust=True and starts in 1992. v2's adjust=False seeded
#         the recursion on 1991 and left it holding 14.3% of the weight -- more
#         than any other year -- despite 1991 having a structurally undefined
#         growth term. A sensitivity table is printed; results are insensitive.
# [FIX e] Historical population now comes from histpopdata.xlsx (published annual
#         ERP at 31 December) instead of the hand-interpolated monthly sheet.
#         The population PROJECTION now uses the same PCHIP routine as households
#         instead of linear interpolation + ffill, which had frozen 2049-50.
# [FIX f] S x OLF renamed occupied_area_per_dwelling; it is NOT a dwelling size,
#         because OLF is normalised on design capacity (bedrooms+1) while S is
#         actual occupancy. Realised dwelling size is now measured directly from
#         consented GFA / consented dwelling counts, and utilisation is reported.
# [NEW g] Consumption is decomposed into "extra space" (dwellings built larger
#         than their occupants require) and "other" (replacement, vacancy,
#         timing, error), reported by five-year period.
# Also retained from v2: runtime truncation guard, structural identity check,
#         Fig 5 sliced before accumulating, no shared y-axes, lower-left legends,
#         House-Splitting suppressed from legends.