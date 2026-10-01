"""
Residential GFA & Embodied Carbon Projection, New Zealand 2026-2050
====================================================================
Bottom-up demographic model of new residential floor area and its embodied
carbon (A1-A5, B2, B4, C1-C4, plus soil carbon loss) by typology, demand type
and material.

    total floor area = new dwellings required x realised dwelling size
    new dwellings    = new households + vacancy allowance + replacement

All input data are read from DATA_DIR; everything written goes to OUT_DIR.
Case-study carbon and occupancy factors come from Building_factors.py (run it
first; it writes them to outputs/factors/). Figures are plotted, never saved.
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from scipy import stats

import engine

# ============================================================
# CONFIGURATION
# ============================================================
# Paths are anchored on this file's folder (the repository root), so every
# script and test works from any working directory (e.g. Spyder).
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, 'data')          # inputs only
OUT_DIR = os.path.join(ROOT_DIR, 'outputs')        # everything the scripts write
FACTORS_DIR = os.path.join(OUT_DIR, 'factors')     # written by Building_factors.py
VERBOSE = False     # True also prints historical diagnostics (occupancy, calibration)
SHOW_PLOTS = True   # False: build nothing on screen (used by Diagnostics / Sensitivity)
# Save every figure as PNG to FIG_DIR. Only when Boss.py is run as a script with
# PATHWAY_SAVE_FIGURES=1 (run_all.py), so re-runs from other scripts never overwrite them.
SAVE_FIGURES = False
FIG_DIR = os.path.join(OUT_DIR, 'figures')
BOSS_FIGURE_NAMES = ['boss_01_population', 'boss_02_households', 'boss_03_cumulative_gfa',
                     'boss_04_annual_gfa', 'boss_05_annual_carbon', 'boss_06_cumulative_carbon',
                     'boss_07_typology_share', 'boss_08_demographic_drivers',
                     'boss_09_space_diagnostics', 'boss_10_material_flows']
# Monthly building consents: data/derived/consents_monthly.csv, built by
# data/build_consents.py from the raw Stats NZ release download (provenance in
# data/raw/MANIFEST.csv).
FILE_CONSENTS_DERIVED = os.path.join(DATA_DIR, 'derived', 'consents_monthly.csv')
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

HOUSEHOLD_SHEET_HIST = 'Table 2'
HOUSEHOLD_SHEET_PROJ = 'Table 1'
HOUSEHOLD_VARIANT_MAP = {'5th': 'Low', '50th': 'Medium', '95th': 'High'}

# ---------------------------------------------------------------------------
# HOUSEHOLD SIZE -- how future households are obtained
# ---------------------------------------------------------------------------
# All three Stats NZ household variants (Low B / Medium B / High B) use the SAME
# 'B' living-arrangement assumption and differ only in fertility, mortality and
# migration. Pairing the 5th-percentile population with the Low B households
# would count low population on BOTH sides of S = Pop / HH, so household size
# is taken from ONE living-arrangement assumption and applied to every
# population percentile:
#     S_StatsNZ(knot) = Pop(knot) / HH_MediumB(knot)
# from a population projection of (near-)matching vintage and the 2018-base
# household projection, at their shared published knots (see S_TAIL for the
# interpolation), applied as a SHAPE rebased on observed household size in
# S_ANCHOR_YEAR:
#     S(t)            = S_observed(anchor) x S_StatsNZ(t) / S_StatsNZ(anchor)
#     Households_p(t) = Pop_2024base_p(t) / S(t)
# VINTAGE: see FILE_POP_SIZE_PAIR for which release is paired and why. Both
# series are at 30 June; only the rebased shape is used, so the half-year offset
# and any level difference do not enter the result.
HH_SIZE_VARIANT = 'Medium'   # 'Low' | 'Medium' | 'High' -- sensitivity on S only

# S_TAIL: household size between and after the published knots (last knot 2043).
#   'hermite_clamped' (ADOPTED, v1.2.1): one cubic Hermite through every
#       published knot (PCHIP derivatives at the interior knots, zero slope
#       imposed at 2043), held constant after 2043.
#   Sensitivities (Sensitivity.py): 'flat' (PCHIP, held after 2043; a kink at
#       2043), 'taper' (PCHIP; the slope tapers linearly to zero over
#       S_TAPER_YEARS from the PCHIP end derivative), 'taper_secant' (v1.2: the
#       2038-43 interval linear at its secant slope, then tapering from it).
# N4 (the Low/High variants pair stochastic population percentiles with
# deterministic household variants) and the total vs private-household
# population question remain OPEN until the living-arrangement table (E2) is
# obtained; see ASSUMPTIONS.md.
S_TAIL = 'hermite_clamped'
S_TAPER_YEARS = 5

# S_ANCHOR_YEAR: the observed household size the Stats NZ shape is rebased on.
#   2023 (ADOPTED, item 6): the last year in which households are benchmarked
#       to a census (the k-rebase makes June 2023 match census growth); the
#       Stats NZ shape then carries S from 2023 through 2025 and on.
#       CAVEAT: the model's annual series is at 31 December, so the anchor is
#       December 2023, six months after the June 2023 benchmark; those six
#       months of household growth are consent-derived (0.888 x lagged
#       consents x k). A June anchor would need a June population; the ERP is
#       used at 31 December throughout, so this half-year compromise stands.
#   Not 2025: 2024-25 households are 0.888 x lagged consents, so the 2025
#       value carries the same DHE artefact that the model does not carry
#       forward as e_2025 (see HOUSEHOLD SIZE AND MIGRATION).
# When Stats NZ rebases DHE households on the 2023 census (planned after the
# 2023-base family and household projections, late 2026; F3), this and the
# k-rebase are to be replaced through one input switch.
S_ANCHOR_YEAR = 2023

# ---------------------------------------------------------------------------
# HOUSEHOLD ESTIMATES: HOW STATS NZ BUILDS THEM, AND WHAT THAT ALLOWS
# ---------------------------------------------------------------------------
# Stats NZ Dwelling and Household Estimates (DHE), Table 2 footnote 1: the
# household series has census-year BASES (1991, 1996, 2001, 2006, 2013, 2018),
# each derived from the estimated resident population and living-arrangement
# type rates. "Estimates for reference dates after each base are derived using
# weighted and lagged building consents." Checked against the data:
#   2019-2025: household growth = 0.887-0.889 x the previous year's consents,
#              every year (correlation 1.000). There is no 2023 household base
#              yet; the dwelling series (Table 1) HAS been rebased on 2023.
#   1992-2018: within each intercensal period household growth is a constant
#              fraction of dwelling growth (e.g. 0.73 in 1996-2000, 0.84 in
#              2006-2012), reset at each census base.
# Consequences:
#   (i)  Between censuses, annual household change carries no information
#        independent of consents. Only census-to-census change does.
#   (ii) The June 2023 estimate is 31-38k (1.6-2.0%) above the growth the 2018
#        and 2023 censuses imply, because it has not been rebased.
#   (iii) The 2024-25 fall in household size is consents (x 0.888, lagged a
#        year) outrunning slowing population growth: an artefact of the
#        estimation method, not observed behaviour.
#
# CENSUS REBASE OF HOUSEHOLDS: households are rebased on the 2023 census the
#   way Stats NZ benchmarks each base. All increments after 30 June 2018 are
#   scaled by one factor k, so that June 2023 grows over June 2018 by the census
#   ratio (the intercensal SHAPE stays consent-driven, as in Stats NZ's own
#   series); 2024-25 keep the same k. Census households = occupied private
#   dwellings + dwellings whose residents were away (Stats NZ's bases add
#   households temporarily absent), k = 0.826. Only the 2018->2023 RATIO is
#   used, so the level adjustments (undercount, households overseas) are assumed
#   proportionally equal in both censuses. This is an assumption: 2018 census
#   coverage was poorer than usual.
HH_REBASE_BASE, HH_REBASE_CENSUS = '2018-06-30', '2023-06-30'

# The stock identity is calibrated only where households are census-benchmarked
# (to the 2023 census; calib_end in main()); beyond it the identity would compare
# consents with 0.888 x lagged consents and just recover Stats NZ's weight.

# ---------------------------------------------------------------------------
# HOUSEHOLD SIZE AND MIGRATION (diagnostic only)
# ---------------------------------------------------------------------------
# Annual household size S = population / households co-moves with migration
# (r ~ +0.6). Given (i) above, between censuses this is how consent-driven
# households meet migration-driven population, i.e. housing SUPPLY against
# arrivals. It is not evidence of how households behave, and must not be
# presented as a behavioural finding. The regression (dS on population growth
# with a time trend, HAC standard errors) is fitted over the census-benchmarked
# years and reported (diag_2); the part of 2025's fall in S it does not explain
# (e_2025) is a product of the estimation method (iii) and is not carried.
# rho_other: the persistence of departures from the calibrated stock identity
# (lag-1 autocorrelation of its residual; engine.deviation_2025). The near-term
# market excess fades at it.

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
# COL_DWELLINGS_TOTAL: the all-category dwellings column. It is never the
# dwelling-size denominator (an all-category count divided into three-typology
# floor area would understate dwelling size by roughly the retirement-village
# share); all-category minus the three typologies = retirement-village units.
COL_DWELLINGS_TOTAL = 'Dwellings'

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
# Retirement-village units are their own band (see RETIREMENT VILLAGES below).
# Calibrated residual of the stock identity beyond the fixed BRANZ demolition rate:
# negative = unconsented additions, positive = losses above that rate.
UNCONSENTED_LABEL = 'Calibrated residual (unconsented additions if < 0; losses beyond BRANZ rate if > 0)'
RV_LABEL = 'Housed in retirement villages (out of carbon scope)'
RV_COLOR = '#b8a0d0'
UNCONSENTED_COLOR = '#16a085'
JOIN_LABEL = 'Near-term market excess (2026 observed building above requirement, fading at rho)'
JOIN_COLOR = '#c0392b'
WAVE_LABEL = 'Redevelopment wave: net replacement above the long-run rate (scenario)'
WAVE_COLOR = '#d35400'

TREND_WINDOW_START = 2012
DAMPING_PHI = 0.8
# MIX_MODE (v1.0.2, author's decision): coherent storylines.
#   'storyline' (ADOPTED): S1 and S3 hold the typology floor-area shares at their
#       MIX_HELD_WINDOW average; S2 ('intensification continues') keeps the
#       damped ALR trend above.
#   'held' / 'trend': force one mix whatever the scenario (sensitivities: S3-10
#       with the trend = the v1.0 mix; S2 with shares held = the maximum
#       floor-area case, since held shares keep more detached floor area).
#   Held shares = ratio of sums of consented floor area over the window (floor-
#   area weighted), with 2026 = the observed months (January-July).
MIX_MODE = 'storyline'
MIX_HELD_WINDOW = (2022, 2026)
# 2026 in-scope floor area (market-excess rule): the observed consented GFA by
#   typology, c x [(1 - W) GFA_2026 + W GFA_2025], with the observed 2026 mix;
#   dwelling counts (the stock) follow the dwelling consents.

# First year with a defined household-formation flow (1991 has no prior year
# in the window); start of the household-size diagnostic regression.
CALIB_START_YEAR = 1992

# ---------------------------------------------------------------------------
# CONSUMPTION: THE STOCK BASIS
# ---------------------------------------------------------------------------
# Floor area beyond household formation is the dwellings built beyond
# formation, decomposed with census vacancy data into named terms:
#   extra space       = new households x (realised dwelling size - occupied area)
#   vacancy allowance = new households x v / (1 - v)
#   vacancy change    = households(t-1) x [1/(1-v(t)) - 1/(1-v(t-1))]
#   replacement       = net replacement rate x stock(t-1)
# converted to floor area at realised dwelling size (engine.forward). Vacancy v
# is measured (census tables below); forward it is held at its latest census
# value. Identity: total floor area = (new households + allowance + change +
# replacement) x realised dwelling size.

# ---------------------------------------------------------------------------
# CENSUS DWELLING OCCUPANCY  (private dwellings only)
# ---------------------------------------------------------------------------
# Vacancy = EMPTY private dwellings / (occupied + unoccupied PRIVATE dwellings).
# Up to 2013 Stats NZ counted only private dwellings as unoccupied. From 2018 it
# also counts UNOCCUPIED NON-PRIVATE dwellings (camping grounds, marae, ...; 4,860
# in 2018, 4,710 in 2023; DataInfo+ 'Dwelling occupancy status'), so the 2018
# and 2023 counts must be taken for private dwellings only.
# 'Residents away' are NOT vacant: those households exist and are already in
# the household series. Counting them fails the replacement check below.
#
# 1981-2013: FILE_CENSUS_2013, Stats NZ 2013 Census QuickStats about housing.
#   Table 1 gives occupied private dwellings, unoccupied and under construction
#   for every census 1981-2013; Table 2 gives the 2013 empty / residents-away
#   split. Before 2013 only total unoccupied is published, so the 2013 empty
#   share (76.2%) is applied to earlier years -- the one assumption here, with
#   a sensitivity band. 2013 is measured.
# 2018, 2023: private dwellings only, from Aotearoa Data Explorer CEN23_HOU_018
#   (occupancy status x dwelling type), built by data/build_census.py into
#   data/derived/census_dwellings.csv and cross-checked there against
#   CEN23_TBT_001 and, for 2013, against the QuickStats file above (identical
#   within random rounding).
# The empty / residents-away split itself breaks between 2013 and 2018
# (N1; DataInfo+: 'did not receive a quality rating in 2018', 'a break in the
# time series').
# Only the RATIO is used: census counts and the household estimates series
# differ in level (census undercount), exactly as for household size.
FILE_CENSUS_2013 = os.path.join(DATA_DIR, 'occ-unocc-2013.xlsx')
FILE_CENSUS_DERIVED = os.path.join(DATA_DIR, 'derived', 'census_dwellings.csv')
PRE2013_EMPTY_SHARE_BAND = 0.05    # +/- on the empty share applied before 2013
DEMOLITION_CALIB_START = 1992      # calibration window for the unconsented-additions rate

# NET REPLACEMENT RATE (demolition + residual, share of last year's stock):
#   the census DWELLING-count identity, per intercensal interval: [completions -
#   change in census private dwellings] / stock-years
#   (engine.census_interval_rates), ratio of sums over NET_REPLACEMENT_WINDOW
#   (census years). Uses neither the household estimates nor the census
#   empty/away split, which breaks between 2013 and 2018 (N1). Completions use
#   the model's lag W in continuous time. Over 1991->2023 the stock changes
#   telescope, so only the 1991 and 2023 counts enter the numerator (2018 only
#   weights the denominator). The household identity (stock_cal) is still
#   calibrated and printed for comparison.
NET_REPLACEMENT_WINDOW = (1991, 2023)
# CENSUS_UC_CORRECTION (v1.1.1, default True): in the dwelling-count identity,
#   dwellings completed over a census interval = 0.95 x consents - the change in
#   census private dwellings UNDER CONSTRUCTION (census stock excludes them; with
#   no completion lag, consents still in progress at census night would else be
#   read as demolition). Applied only when COMPLETION_LAG is 0 (a lag already
#   removes the pipeline; correcting twice would double count). UC counts:
#   1986-2013 census Table 1 (occ-unocc-2013.xlsx), 2018/2023 CEN23_HOU_018
#   (private). False = no correction (sensitivity).
CENSUS_UC_CORRECTION = True    # census years; (2013, 2023) is a sensitivity

# REPLACEMENT_SCENARIO (net replacement path, on the census dwelling-count rates):
#   'S1': the long-run rate (NET_REPLACEMENT_WINDOW) throughout;
#   'S2': the 2018-2023 census-interval rate persists;
#   'S3': the 2018-2023 rate fades to the long-run rate with half-life
#         S3_HALF_LIFE years (5, 10, 15 assessed).
# Author's decision: S1 and S2 are the lower and
# upper bounds; S3 with a 10-year half-life is the labelled reference path
# (JUDGEMENT: the half-life is not identifiable), with 5 and 15 years reported.
REPLACEMENT_SCENARIO = 'S3'
S3_HALF_LIFE = 10.0
RECENT_INTERVAL = (2018, 2023)

# ---------------------------------------------------------------------------
# NEAR-TERM MARKET EXCESS
# ---------------------------------------------------------------------------
# NEAR_TERM_JOIN:
#   'carried_deviation': no observed 2026 data; 2025's deviation fades at rho
#       (used only by the 2026 out-of-sample check, validation.NO_2026_DATA).
# v1.1 default: 'market_excess' -- ONE rule on top of any replacement scenario:
#   2026 building = observed (NOWCAST_METHOD). Its excess over the 2026
#   requirement is the 'near-term market excess'. From 2027 the building
#   continues above the requirement by gap_ref x rho^(t-2026), with gap_ref =
#   building_2026 - requirement_2027 (the 2027 requirement, because the 2026 one
#   is depressed by the one-off 2026 population shortfall) and rho = rho_other
#   (the estimated persistence of departures from the calibrated identity).
#   NEAR_TERM_MODE 'surplus' with absorption 0 (default): the excess is
#   STOCK-ADDING -- extra dwellings join the stock as vacancy that is never
#   absorbed; soil applies; removals stay on the scenario path. Implied vacancy
#   = 1 - households / (stock + cumulative excess). Sensitivities: 'redevelopment'
#   (stock-neutral), payback (NEAR_TERM_ABSORPTION 0.20 / 0.10), and
#   NEAR_TERM_GAP_REF = '2026'.
NEAR_TERM_JOIN = 'market_excess'
NEAR_TERM_GAP_REF = '2027'
NEAR_TERM_MODE = 'surplus'
NEAR_TERM_ABSORPTION = 0.0
# NOWCAST_METHOD: 'last_12_months' -- 2026 = the latest 12 OBSERVED months
#   (August 2025 - July 2026), no seasonal estimation. It is the year to July
#   2026, not calendar 2026: replace it with calendar 2026 when published.
NOWCAST_METHOD = 'last_12_months'
NOWCAST_SEASONAL_YEARS = (2010, 2025)
# NOWCAST_POPULATION: 2026 population growth is OBSERVED: the latest
#   four-quarter change of the Stats NZ mean-quarter ERP (Infoshare DPE059AA),
#   June quarter 2026 minus June quarter 2025, in place of the projection
#   median; later years keep the projection's growth, so the level shift is
#   permanent. POPULATION CONVENTION: history = ERP at 31 December; projection
#   growth = years ended June applied to calendar years (half-year offset).
NOWCAST_POPULATION = True
FILE_POP_QUARTERLY = os.path.join(DATA_DIR, 'derived', 'population_quarterly.csv')
# ---------------------------------------------------------------------------
# SOIL CARBON (item 8)
# ---------------------------------------------------------------------------
# Soil organic carbon loss is land-use change: a new building footprint seals
# the soil under it; a rebuilt footprint sits on soil already sealed (IPCC 2006
# Guidelines, Vol. 4, ch. 8: settlements remaining settlements). So soil loss
# applies to ALL non-replacement floor area and is ZERO on the replacement bands
# (demolition replacement + calibrated residual + the redevelopment channel of
# the near-term join).
# Factor: 58.77 kg CO2e per m2 of footprint, the area-weighted average over the
# 10 soil orders of the land zoned for urbanisation to about 2050 in Auckland
# (divided by each typology's floor space index), from
#   Christoforatos G, Pickering K, Schipper LA (2026). Integrating soil organic carbon loss into bu
#   ilding life cycle assessment and urban planning: implications for urban sustainability practice. Journal of Environmental Management 415, 130603. https://doi.org/10.1016/j.jenvman.2026.130603
# The Raw / Organic soil-order extremes are the bounding sensitivity.
# SOIL_ON_REPLACEMENT = True restores the original (soil on all floor area).
SOIL_ON_REPLACEMENT = False

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
# ---------------------------------------------------------------------------
# RETIREMENT VILLAGES -- in the stock and demographic analysis, out of carbon scope
# ---------------------------------------------------------------------------
# Retirement-village (RV) units are private dwellings: their residents are
# counted in the household series, and they are built with new-dwelling
# consents. The consent file's 'Dwellings' column includes them; the three
# typology columns (and therefore all floor area) do not. RV units are
# therefore:
#   STOCK / DEMOGRAPHY: counted as built dwellings in the stock identity, so
#     they are not mistaken for unconsented additions (they were 54% of the
#     calibrated residual over 1992-2025 when left out), and reported forward.
#   CARBON / FLOOR AREA: out of scope. There is no RV floor area or case-study
#     LCA. Households housed in RV units are removed from in-scope demand and
#     shown as their own (negative) band, valued at in-scope dwelling size, so
#     the reader sees how much housing need they meet. Their carbon is NOT
#     estimated.
# Forward, RV units are a fixed SHARE of all dwellings built (RV + in-scope),
# the ratio of sums over RV_SHARE_REF. The annual share has been 4-8% since
# 2011 with no trend; before 2008 it was 1-4%. The population aged 85+ grows
# faster than the total in the Stats NZ projection, so a constant share may
# understate future RV building; this is disclosed, not modelled (there is no
# historical age series in the inputs to calibrate against).
RV_SHARE_REF = (2016, 2025)
# RV floor area (A4). Stats NZ publishes retirement-village floor area
# consented (building type 'Retirement village units'), extracted by
# data/build_consents.py. It is reported as its own series: history (built
# basis, lagged like everything else) and a projection = projected RV units x
# RV floor area per unit over DWELLING_SIZE_REF. It stays OUT of the in-scope
# floor area and carbon: bringing it in needs a carbon factor for RV buildings,
# for which no case study exists (any factor would be judgement).
COL_RV_GFA = 'GFA - GFA/RetirementVillage'

COMPLETION_RATE = 0.95
COMPLETION_RATE_BAND = (0.92, 0.96)

# COMPLETION_LAG: consents are not built in the calendar year they are issued.
#   'littles_law' (ADOPTED, item 7): dwellings completed in year t =
#       COMPLETION_RATE x [(1 - W) x consents_t + W x consents_(t-1)],
#       a two-point distributed lag whose mean lag W (years) is estimated at
#       run time by Little's law (Little 1961), W = L / lambda, at each census
#       with 12 months of consent data before it (1986-2023 with the Stats NZ
#       release series): L = dwellings under construction on census night (March),
#       lambda = all dwellings consented in the 12 months to March of the census
#       year (the census is in early March, so the window runs to the end of
#       the census month). W is the mean over those censuses.
#       LIMITATIONS: (i) W measures time UNDER CONSTRUCTION only; dwellings
#       consented but not started are not counted, so the consent-to-completion
#       lag is at least W (a lower bound); (ii) Little's law assumes a steady
#       state, which 2023 (falling consents) violates, hence the mean over
#       censuses; (iii) only the mean is identified: the two-point kernel shape
#       (even consents within the year, one fixed duration) is an assumption.
#       1991, the first model year, uses unlagged consents (no prior model year).
#   0, or a number in [0, 1): a fixed W; 0 is the original behaviour.
# The same completions series is used everywhere consents become 'built':
# stock calibration, the 2025 deviation, the 2025 observed anchor (and so the
# 2025 -> 2026 step), history plots and the Monte Carlo.
# v1.1 default: 0 (no lag): calibration, history and the 2026 anchor use
#   same-year consents x COMPLETION_RATE. 'littles_law' is a sensitivity.
COMPLETION_LAG = 0
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
FILE_FACTORS_MATERIAL = os.path.join(FACTORS_DIR, 'factors_material.csv')
FILE_FACTORS_TYPOLOGY = os.path.join(FACTORS_DIR, 'factors_typology.csv')
FILE_FACTORS_BUILDING = os.path.join(FACTORS_DIR, 'factors_building.csv')
STAGES_IN_SCOPE = ['A1-A3', 'A4-A5', 'B2,B4', 'C1-C4']   # Module D excluded

# Carbon intensity is held CONSTANT at its case-study value for the whole
# projection. No learning rate, no decarbonisation: this build reports what
# current construction practice implies, and nothing is assumed about future
# material supply.


# ============================================================
# LOADERS
# ============================================================

def load_consents():
    """Monthly consents (data/derived/consents_monthly.csv) with a datetime 'Date' column."""
    df = pd.read_csv(FILE_CONSENTS_DERIVED)
    df['Date'] = pd.to_datetime(df['Date'])
    return df


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


def census_later():
    """2018 and 2023 census private-dwelling counts (data/derived/census_dwellings.csv)."""
    d = pd.read_csv(FILE_CENSUS_DERIVED)
    d = d[d['type'] == 'private'].set_index('year')
    return {int(y): dict(occupied_private=float(d.loc[y, 'occupied']), unoccupied=float(d.loc[y, 'unoccupied']),
                         empty=float(d.loc[y, 'empty']), away=float(d.loc[y, 'away']),
                         under_construction=float(d.loc[y, 'under_construction']))
            for y in (2018, 2023)}


def load_census_occupancy(later, path=None):
    """Census private-dwelling occupancy, one row per census year.
    Reads Tables 1 and 2 of the 2013 QuickStats workbook, then appends the
    later censuses. Columns: occupied_private, unoccupied, empty (NaN where not
    published), away, under_construction, total_private."""
    path = path or FILE_CENSUS_2013
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
# HOUSEHOLD SIZE (shared by main() and MonteCarlo.py)
# ============================================================

def extend_tail(S_knots, S_ann, mode):
    """Replace the values after the last knot according to S_TAIL (see there)."""
    yrs_k, s_k = S_knots['Year'].values, S_knots['S'].values
    last = int(yrs_k[-1])
    if mode == 'hermite_clamped':
        # v1.2.1: ONE cubic Hermite through every published knot, PCHIP derivatives at the
        # interior knots, zero derivative clamped at the last knot; held constant after it.
        from scipy.interpolate import CubicHermiteSpline
        x = yrs_k.astype(float)
        d = PchipInterpolator(x, s_k).derivative()(x)
        d[-1] = 0.0
        h = CubicHermiteSpline(x, s_k, d)
        out = S_ann.copy()
        inside = (out.index >= x[0]) & (out.index <= last)
        out[inside] = h(out.index[inside].astype(float))
        out[out.index > last] = float(s_k[-1])
        return out
    if mode in ('taper', 'taper_secant'):
        # slope tapers linearly to zero over S_TAPER_YEARS: S(K+t) = S(K) + s0 (t - t^2 / (2T)),
        # constant after K+T. With s0 = the PCHIP end derivative this is C1-continuous at K
        # ('taper'); 'taper_secant' starts from the 2038-43 secant slope instead (not C1).
        s0 = (float(PchipInterpolator(yrs_k.astype(float), s_k).derivative()(last)) if mode == 'taper'
              else (s_k[-1] - s_k[-2]) / (yrs_k[-1] - yrs_k[-2]))
        T = float(S_TAPER_YEARS)
        out = S_ann.copy()
        if mode == 'taper_secant':
            # v1.2: the last published interval (2038->2043) is linear at its secant slope, so the
            # taper after 2043 continues it smoothly (no kink at 2043; the PCHIP segment meets the
            # line at 2038 instead)
            k0 = int(yrs_k[-2])
            seg = (out.index >= k0) & (out.index <= last)
            out[seg] = s_k[-2] + s0 * (out.index[seg] - k0)
        t = np.clip(out.index.values - last, 0.0, T)
        after = out.index > last
        out[after] = float(S_ann.loc[last]) + s0 * (t[after] - t[after] ** 2 / (2 * T))
        return out
    if mode != 'flat':
        raise ValueError(f"Unknown S_TAIL '{mode}'.")
    out = S_ann.copy()
    out[out.index > last] = float(S_ann.loc[last])
    return out


def statsnz_size_shape(variant, forecast_years, tail):
    """[Route A] Stats NZ household size S = Pop / HH at the shared knots of the
    matched-vintage population and household projections for one variant,
    PCHIP-interpolated to annual values; after the last knot, see S_TAIL.
    Returns (S_knots, S_ann, pop_ref), where pop_ref is that variant's annual
    population (to read the growth it assumed)."""
    pop_k = load_national_pop_projection(variant=variant).set_index('Year')['Population']
    hh_k = extract_household_projection_block(FILE_HOUSEHOLDS_PROJ,
                                              variant_label=variant).set_index('Year')['Households']
    common = sorted(set(pop_k.index) & set(hh_k.index))
    S_knots = pd.DataFrame({'Year': common, 'S': [pop_k[y] / hh_k[y] for y in common]})
    S_ann = smooth_interpolate_and_extend(S_knots, 'S', np.arange(min(common), 2051)).set_index('Year')['S']
    S_ann = extend_tail(S_knots, S_ann, tail)
    pk = pop_k.reset_index().rename(columns={'index': 'Year'})
    pop_ref = smooth_interpolate_and_extend(pk, 'Population',
                                            np.arange(int(pk['Year'].min()), 2051)).set_index('Year')['Population']
    return S_knots, S_ann, pop_ref


def household_size(S_ann, pop_ref, hist_S, hist_pop, forecast_years, b, anchor_year):
    """Household size rebased on the observed value in anchor_year (S_matched):
        S(t) = S_obs(anchor) x S_StatsNZ(t) / S_StatsNZ(anchor).
    Diagnostic only: 2025's departure from the Stats NZ trend not explained by
    b x (observed - assumed population growth), e_2025 (not carried)."""
    S_statsnz = S_ann.reindex(forecast_years).values
    S_matched = float(hist_S.loc[anchor_year]) * S_statsnz / float(S_ann.loc[anchor_year])
    dP_ref = pop_ref.diff().reindex(forecast_years).values
    dS_snz_2025 = float(S_matched[0] * (S_ann.loc[2025] - S_ann.loc[2024]) / S_ann.loc[2025])
    dS_obs_2025 = float(hist_S.loc[2025] - hist_S.loc[2024])
    dP_obs_2025 = float(hist_pop.loc[2025] - hist_pop.loc[2024])
    e_2025 = dS_obs_2025 - (dS_snz_2025 + b * (dP_obs_2025 - dP_ref[0]))
    return dict(S_matched=S_matched, e_2025=e_2025, dS_snz_2025=dS_snz_2025,
                dS_obs_2025=dS_obs_2025, dP_obs_2025=dP_obs_2025, dP_ref=dP_ref)


def household_rebase_factor(hh_q, later):
    """k: the factor on DHE household increments after the 2018 base that makes
    June 2023 grow over June 2018 by the census ratio of occupied + residents-away
    private dwellings (see CENSUS REBASE OF HOUSEHOLDS)."""
    cols = ('occupied_private', 'away')
    c18 = sum(later[2018][c] for c in cols)
    c23 = sum(later[2023][c] for c in cols)
    h = hh_q.set_index('Date')['Households']
    h0, h1 = float(h[pd.Timestamp(HH_REBASE_BASE)]), float(h[pd.Timestamp(HH_REBASE_CENSUS)])
    return (h0 * c23 / c18 - h0) / (h1 - h0)


def rebase_households(hh_q, k, base=HH_REBASE_BASE):
    """Scale every household increment after the 2018 base by k (quarterly)."""
    out = hh_q.copy()
    h0 = float(out.loc[out['Date'] == pd.Timestamp(base), 'Households'].iloc[0])
    after = out['Date'] > pd.Timestamp(base)
    out.loc[after, 'Households'] = h0 + k * (out.loc[after, 'Households'] - h0)
    return out


def annual_households(hh_q):
    """Last quarter of each calendar year (31 December)."""
    last = hh_q.loc[hh_q.groupby(hh_q['Date'].dt.year)['Date'].idxmax()]
    return last.set_index(last['Date'].dt.year.rename('Year'))['Households']


def newey_west_cov(X, resid, lag=None):
    """Newey-West (1987) HAC covariance of OLS coefficients, Bartlett kernel,
    default lag floor(4 (n/100)^(2/9)), small-sample factor n / (n - k)."""
    n, k = X.shape
    lag = int(np.floor(4 * (n / 100) ** (2 / 9))) if lag is None else lag
    Xe = X * resid[:, None]
    S = Xe.T @ Xe
    for l in range(1, lag + 1):
        G = Xe[l:].T @ Xe[:-l]
        S += (1 - l / (lag + 1)) * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X)
    return XtXi @ S @ XtXi * n / (n - k), lag


# ============================================================
# CORE HELPERS
# ============================================================

def fit_evolving_mix(hist_shares, shares_2025, forecast_years, phi, trend_window_start,
                     typ_names, ref_typology='Detached'):
    """Additive log-ratio (ALR) trend with geometric damping. Shares stay positive
    and sum to one by construction."""
    alr_2025, slope = mix_trend(hist_shares, shares_2025, trend_window_start, typ_names, ref_typology)
    return engine.mix_shares(alr_2025, slope, phi, forecast_years, typ_names, ref_typology)


def mix_trend(hist_shares, shares_2025, trend_window_start, typ_names, ref_typology='Detached'):
    """2025 log-ratios and OLS slopes of log(share / reference share) over the
    trend window, for every non-reference typology."""
    other = [n for n in typ_names if n != ref_typology]
    window = hist_shares.loc[hist_shares.index >= trend_window_start]
    alr_hist = {n: np.log(window[n] / window[ref_typology]) for n in other}
    slope = {n: np.polyfit(window.index.values, alr_hist[n].values, 1)[0] for n in other}
    alr_2025 = {n: np.log(shares_2025[n] / shares_2025[ref_typology]) for n in other}
    return alr_2025, slope


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
    return engine.blend(shares, per_unit_dict, typ_names)


# ============================================================
# MAIN
# ============================================================

def save_open_figures(names, fig_dir, dpi=130):
    """Write every open figure, in creation order, as fig_dir/<name>.png."""
    nums = plt.get_fignums()
    if len(nums) != len(names):
        raise RuntimeError(f"{len(nums)} figures open but {len(names)} names given.")
    os.makedirs(fig_dir, exist_ok=True)
    for n, name in zip(nums, names):
        plt.figure(n).savefig(os.path.join(fig_dir, name + '.png'), dpi=dpi, bbox_inches='tight')


def main():
    print("\n" + "=" * 78)
    print(" NZ RESIDENTIAL FLOOR AREA & EMBODIED CARBON, 2026-2050")
    print(" demand split: growth / house-splitting / consumption (stock basis)")
    print("=" * 78)

    typ_names = list(COL_TYPOLOGIES.keys())
    # Settings used by the stock calibration, bound here once so that the
    # returned calibrate_stock() never reads the (mutable) module globals.
    _completion, _demol_rate, _calib_start = COMPLETION_RATE, DEMOLITION_RATE, DEMOLITION_CALIB_START
    _nr_window = tuple(NET_REPLACEMENT_WINDOW)
    _scenario, _join_mode = REPLACEMENT_SCENARIO, NEAR_TERM_JOIN
    if _join_mode not in ('market_excess', 'carried_deviation'):
        raise ValueError(f"Unknown NEAR_TERM_JOIN '{_join_mode}'.")

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
    MAT_INTENSITY_STAGE = (mat_scope[mat_scope['Stage'].isin(['A1-A3', 'A4-A5'])]
                           .groupby('Typology')['kgCO2e_per_m2'].sum().to_dict())   # upfront materials
    # kg CO2e per m2 GFA, by typology and material (materials only; soil added
    # separately as its own line so that it is never treated as a material).
    MAT_INTENSITY = (mat_scope.pivot_table(index='Material', columns='Typology',
                                           values='kgCO2e_per_m2', aggfunc='sum')
                     .reindex(index=MATERIALS, columns=typ_names).fillna(0.0))
    SOIL_INTENSITY = {t: float(typ_fac.loc[t, 'SOC_avg']) for t in typ_names}
    OLF_NET_BIM = {t: float(typ_fac.loc[t, 'OLF_m2_per_person']) for t in typ_names}
    DESIGN_OCCUPANTS = {t: float(typ_fac.loc[t, 'design_occupants']) for t in typ_names}
    T_BASELINE_2025 = {t: float(typ_fac.loc[t, 'total_with_SOC']) for t in typ_names}
    UPFRONT_2025 = {t: float(MAT_INTENSITY_STAGE.get(t, 0.0)) + SOIL_INTENSITY[t] for t in typ_names}

    # ------------------------------------------------------------------
    # 1. CONSENTS: floor area AND dwelling counts
    # ------------------------------------------------------------------
    df_consents = load_consents()
    df_consents['Year'] = pd.to_datetime(df_consents['Date']).dt.year

    hist_typ_gfa = df_consents.groupby('Year')[list(COL_TYPOLOGIES.values())].sum()
    hist_typ_gfa.columns = typ_names
    hist_typ_gfa = hist_typ_gfa.loc[1991:2025]

    hist_typ_units = df_consents.groupby('Year')[list(COL_CONSENT_COUNTS.values())].sum()
    hist_typ_units.columns = typ_names
    hist_typ_units = hist_typ_units.loc[1991:2025]

    hist_total_gfa = df_consents.groupby('Year')[COL_GFA].sum().loc[1991:2025]

    # ---- dwelling-count denominator: the three typologies ----------
    typ_sum = hist_typ_units.sum(axis=1)
    ext = df_consents.groupby('Year')[COL_DWELLINGS_TOTAL].sum().reindex(typ_sum.index)
    ratio = (ext / typ_sum).loc[2015:2025].mean()
    gap = (ext - typ_sum).loc[2015:2025].mean()
    # The all-category column includes retirement village units, which the floor
    # area columns exclude, so it is never the denominator.
    print(f"[check] scope: 3 typologies; the all-category dwelling column is "
          f"{100 * (ratio - 1):.1f}% higher ({gap:,.0f}/yr, retirement villages) "
          f"-> not used as denominator")

    hist_total_units = typ_sum
    # Retirement-village units consented = all-category dwellings - 3 typologies.
    hist_rv_units = (ext - typ_sum).clip(lower=0)
    _rw = slice(*RV_SHARE_REF)
    rv_share = float(hist_rv_units.loc[_rw].sum()
                     / (hist_total_units.loc[_rw].sum() + hist_rv_units.loc[_rw].sum()))
    hist_rv_share = hist_rv_units / (hist_total_units + hist_rv_units)

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

    hh_raw_dhe = load_historical_households(FILE_HOUSEHOLDS_HIST)     # as published
    census_18_23 = census_later()
    hh_rebase_k = household_rebase_factor(hh_raw_dhe, census_18_23)
    hh_raw = rebase_households(hh_raw_dhe, hh_rebase_k)
    hh_annual = annual_households(hh_raw)
    calib_end = 2023                     # last census-benchmarked household year
    hist_hh_dhe = annual_households(hh_raw_dhe).reindex(years_hist)
    hist_hh = hh_annual.reindex(years_hist)
    if hist_hh.isna().any():
        raise ValueError("Household series has gaps over 1991-2025.")

    hist_S = hist_pop / hist_hh
    print(f"[check] households: DHE series rebased on the 2023 census (occupied + away); "
          f"post-2018 increments x {hh_rebase_k:.3f} -> 2025 households "
          f"{hist_hh.loc[2025]:,.0f} (published {hist_hh_dhe.loc[2025]:,.0f}), "
          f"S 2025 {hist_S.loc[2025]:.3f} (published {hist_pop.loc[2025] / hist_hh_dhe.loc[2025]:.3f})")
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
    OLF_GROSS = {t: size_ref[t] / DESIGN_OCCUPANTS[t] for t in typ_names}   # comparison only
    OLF_USED = dict(OLF_NET_BIM)

    if VERBOSE:   # case-study vs consented occupancy; see Diagnostics D
        print("\n OCCUPANCY LOAD FACTOR -- case studies (in use) vs consented dwellings")
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

    # ------------------------------------------------------------------
    # STOCK, VACANCY AND REPLACEMENT  (census-based)
    # ------------------------------------------------------------------
    census = load_census_occupancy(later=census_18_23)
    measured = census['empty'].notna()
    empty_share_measured = float(census.loc[measured, 'empty'].iloc[0]
                                 / census.loc[measured, 'unoccupied'].iloc[0])
    census = census[census.index >= years_hist.min() - 5]     # relevant window only

    hist_units_all = hist_total_units + hist_rv_units       # all dwellings consented

    # ---- completion lag (see COMPLETION_LAG) --------------------------------
    # Little's law at each census: under construction / all dwellings consented
    # in the 12 months to March of the census year.
    _m = df_consents.set_index('Date')[COL_DWELLINGS_TOTAL]
    build_duration = {}
    for yr in census.index:
        _win = _m.loc[pd.Timestamp(yr - 1, 4, 1):pd.Timestamp(yr, 3, 1)]
        if len(_win) == 12:
            build_duration[int(yr)] = float(census.loc[yr, 'under_construction'] / _win.sum())
    if COMPLETION_LAG == 'littles_law':
        lag_w = float(np.mean(list(build_duration.values())))
    else:
        lag_w = float(COMPLETION_LAG)
    if not 0.0 <= lag_w < 1.0:
        raise ValueError(f'Completion lag W = {lag_w} outside [0, 1).')

    def completed(series):
        """Consents timed as completions: (1 - W) x this year + W x last year.
        The first year has no full prior year in the data and stays unlagged."""
        return ((1.0 - lag_w) * series + lag_w * series.shift(1)).fillna(series)

    hist_units_all_c = completed(hist_units_all)              # all categories
    hist_rv_units_c = completed(hist_rv_units)
    hist_total_units_c = completed(hist_total_units)          # in scope
    hist_gfa_c = completed(hist_total_gfa)
    hist_typ_gfa_c = hist_typ_gfa.apply(completed)

    def calibrate_stock(pre_share, completion=None, demol=None, hh=None):
        """The historical stock identity (engine.calibrate_stock) with this
        run's data and settings. In-scope built = d_hh + allow + change + demol
        + uncons + rv (rv < 0)."""
        return engine.calibrate_stock(years_hist, hist_hh if hh is None else hh,
                                      engine.vacancy_knots(census, pre_share),
                                      hist_units_all_c, hist_rv_units_c,
                                      _completion if completion is None else completion,
                                      _demol_rate if demol is None else demol,
                                      _calib_start, calib_end)

    stock_cal = calibrate_stock(empty_share_measured)
    demolition_rate = DEMOLITION_RATE                  # fixed (BRANZ SR214)
    # census dwelling-count identity (always computed; reported, and the default source)
    consents_monthly = df_consents.set_index('Date')[COL_DWELLINGS_TOTAL].astype(float)
    census_uc = (census['under_construction'] if CENSUS_UC_CORRECTION and lag_w == 0 else None)
    census_rates = engine.census_interval_rates(census['total_private'], consents_monthly, _completion, lag_w,
                                                uc=census_uc)

    # long-run residual beyond the BRANZ demolition rate (census dwelling counts)
    unconsented_rate = engine.census_window_rate(census_rates, *_nr_window) - demolition_rate
    v_forward = float(stock_cal['knots'][max(stock_cal['knots'])])   # latest census, held

    # 2025's departure from the calibrated identity, and its persistence. Carried
    # forward fading at rho, booked to the residual (see engine.forward).
    # net replacement path forward (REPLACEMENT_SCENARIO); unconsented_rate stays the long-run value
    rate_recent = engine.census_window_rate(census_rates, *RECENT_INTERVAL)
    rate_path = engine.replacement_path(_scenario, demolition_rate + unconsented_rate, rate_recent,
                                        np.arange(2025, 2051), S3_HALF_LIFE)
    unc_path = rate_path - demolition_rate
    _dv = engine.deviation_2025(stock_cal, _completion * hist_units_all_c.loc[2025], d_hh.loc[2025],
                                float(rate_path[0]), years_hist, _calib_start, calib_end)
    other_2025, other_model_2025 = _dv['other_2025'], _dv['model_2025']
    rho_other, other_dev_2025 = _dv['rho'], _dv['dev']

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

    # 5th / 95th: the published LEVEL spread about the median (knots run past 2050,
    # so no extrapolation); see POPULATION PERCENTILES
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
    pop_nowcast = None
    if NOWCAST_POPULATION:
        _q = pd.read_csv(FILE_POP_QUARTERLY).set_index(['year', 'quarter'])['total']
        if (2026, 2) not in _q.index:
            raise ValueError(f'{FILE_POP_QUARTERLY} has no June quarter 2026.')
        _g_obs, _status = float(_q[(2026, 2)] - _q[(2025, 2)]), 'DPE059AA, June qtr 2026 vs 2025, mean-quarter'
        _i26 = int(np.where(forecast_years == 2026)[0][0])
        _shift = _g_obs - float(df_forecast.loc[_i26, 'PopGrowth_50th'])
        _adj = np.full(len(forecast_years), _shift)          # permanent level shift from 2026
        _adj[:_i26] = 0.0
        for pct in ['5th', '50th', '95th']:
            df_forecast[f'PopTotal_{pct}'] += _adj
            df_forecast[f'PopGrowth_{pct}'] += np.diff(np.insert(_adj, 0, 0.0))
        pop_nowcast = dict(observed_growth=_g_obs, shift=_shift, status=_status)
        print(f"[nowcast] 2026 population growth: observed {pop_nowcast['observed_growth']:,.0f} "
              f"(year ended June 2026, {pop_nowcast['status']}) vs projection median "
              f"{pop_nowcast['observed_growth'] - _shift:,.0f}; levels from 2026 shifted by {_shift:+,.0f}")
    print(f"[check] population percentiles (published levels), 2048: "
          + " | ".join(f"{p} {df_forecast.loc[forecast_years == 2048, f'PopTotal_{p}'].iloc[0] / 1e6:.2f} M"
                       for p in ['5th', '50th', '95th']))

    if VERBOSE: print(f"[FIX e] population projection: {len(pop_growth_block)} published knots "
          f"-> PCHIP to 2050 (was linear interpolate + ffill, which froze 2049-50)")

    # ------------------------------------------------------------------
    # 7. HOUSEHOLD PROJECTION
    # ------------------------------------------------------------------
    # household size: the Stats NZ shape, rebased on the census anchor year
    S_knots, _S_ann, _pref = statsnz_size_shape(HH_SIZE_VARIANT, forecast_years, tail=S_TAIL)
    S_matched = household_size(_S_ann, _pref, hist_S, hist_pop, forecast_years, 0.0,
                               anchor_year=S_ANCHOR_YEAR)['S_matched']
    # ---- household size and migration: diagnostic regression (not applied) ----
    # Fitted only where households are census-benchmarked (see above).
    _yr = years_hist[(years_hist >= CALIB_START_YEAR) & (years_hist <= calib_end)]
    _dS = hist_S.diff().loc[_yr].values
    _dP = hist_pop.diff().loc[_yr].values
    _X = np.c_[np.ones(len(_yr)), _dP, _yr - _yr.mean()]
    _beta, *_ = np.linalg.lstsq(_X, _dS, rcond=None)
    b_resp = float(_beta[1])
    _res = _dS - _X @ _beta
    rho = float(np.clip(np.corrcoef(_res[:-1], _res[1:])[0, 1], 0.0, 0.95))
    _r2 = 1 - (_res ** 2).sum() / ((_dS - _dS.mean()) ** 2).sum()
    # The residuals are autocorrelated (that is what rho measures), so the
    # ordinary OLS standard error of b is invalid: Newey-West HAC instead.
    _n, _k = _X.shape
    _cov_hac, _L = newey_west_cov(_X, _res)
    _se_hac = float(np.sqrt(_cov_hac[1, 1]))
    _se_ols = float(np.sqrt((_res ** 2).sum() / (_n - _k) * np.linalg.inv(_X.T @ _X)[1, 1]))
    # Migration explains part of 2025's fall (b x the migration shortfall); the
    # unexplained remainder e_2025 is a DHE estimation artefact and is not carried.
    _hr = household_size(_S_ann, _pref, hist_S, hist_pop, forecast_years, b_resp, anchor_year=S_ANCHOR_YEAR)
    hh_response = dict(b=b_resp, se_hac=_se_hac, se_ols=_se_ols, hac_lag=_L, rho=rho, r2=_r2,
                       e_2025=_hr['e_2025'], dS_obs_2025=_hr['dS_obs_2025'], dS_snz_2025=_hr['dS_snz_2025'],
                       dP_obs_2025=_hr['dP_obs_2025'], dP_ref=_hr['dP_ref'], dS_hist=_dS, dP_hist=_dP,
                       years_fit=_yr, n_fit=_n)
    households_forecast = {pct: df_forecast[f'PopTotal_{pct}'].values / S_matched
                           for pct in ['5th', '50th', '95th']}

    print(f"\n[Route A] household size from {FILE_POP_SIZE_PAIR} / {FILE_HOUSEHOLDS_PROJ} "
          f"({HH_SIZE_VARIANT})")
    print("   knot   " + "  ".join(f"{int(y)}" for y in S_knots['Year']))
    print("   S      " + "  ".join(f"{v:.3f}" for v in S_knots['S']))
    h = hh_response
    print(f"   [diagnostic, {h['years_fit'][0]}-{h['years_fit'][-1]}] dS on population growth: "
          f"b = {h['b']:.2e} per person (r2 {h['r2']:.2f}), residual persistence rho = {h['rho']:.2f}/yr")
    print(f"   between censuses households follow lagged consents, so b measures supply vs "
          f"arrivals, not behaviour")
    print(f"   b standard error: OLS {h['se_ols']:.2e} | Newey-West HAC (lag {h['hac_lag']}) "
          f"{h['se_hac']:.2e} -> t = {h['b'] / h['se_hac']:.1f}")
    print(f"   2025: observed dS {h['dS_obs_2025']:+.4f} vs trend {h['dS_snz_2025']:+.4f} at "
          f"{h['dP_obs_2025']:,.0f} people (Stats NZ assumed {h['dP_ref'][0]:,.0f}) "
          f"-> deviation {h['e_2025']:+.4f}")
    _mig = h['b'] * (h['dP_obs_2025'] - h['dP_ref'][0])
    print(f"   of 2025's fall: {_mig:+.4f} from low migration (ends as migration recovers), "
          f"{h['e_2025']:+.4f} unexplained -> not carried (a DHE estimation artefact)")
    print(f"   dwellings beyond formation: 2025 deviation {other_dev_2025:+,.0f}, "
          f"persistence {rho_other:.2f}/yr")
    print(f"   household size 2050: {S_matched[-1]:.3f}")
    print(f"   rebased on observed {S_ANCHOR_YEAR} (S = {hist_S.loc[S_ANCHOR_YEAR]:.3f}; observed 2025 S = {hist_S.loc[2025]:.3f}): "
          f"2030 {S_matched[5]:.3f} | 2040 {S_matched[15]:.3f} | 2050 {S_matched[-1]:.3f}")

    # ------------------------------------------------------------------
    # 8. FORWARD MIX, OLF AND DWELLING SIZE
    # ------------------------------------------------------------------
    evolving_gfa_shares = fit_evolving_mix(hist_shares, shares_2025, forecast_years,
                                           DAMPING_PHI, TREND_WINDOW_START, typ_names)
    if MIX_MODE not in ('storyline', 'held', 'trend'):
        raise ValueError(f"Unknown MIX_MODE '{MIX_MODE}'.")
    mix_used = MIX_MODE if MIX_MODE != 'storyline' else ('trend' if _scenario == 'S2' else 'held')
    _typ_cols = [COL_TYPOLOGIES[n] for n in typ_names]
    _w = df_consents[(df_consents['Year'] >= MIX_HELD_WINDOW[0]) & (df_consents['Year'] <= MIX_HELD_WINDOW[1])]
    held_shares = (_w[_typ_cols].sum() / _w[_typ_cols].sum().sum()).set_axis(typ_names)
    if mix_used == 'held':
        evolving_gfa_shares.loc[forecast_years > 2025, :] = held_shares.values
    # 2026 floor area from observed consented GFA by typology
    gfa_nowcast = None
    if _join_mode == 'market_excess':
        _gm = df_consents.set_index(pd.to_datetime(df_consents['Date']))
        _g26 = {n: engine.nowcast_year(_gm[COL_TYPOLOGIES[n]].astype(float), 2026, NOWCAST_METHOD,
                                       NOWCAST_SEASONAL_YEARS)['total'] for n in typ_names}
        _built = {n: _completion * ((1.0 - lag_w) * _g26[n] + lag_w * float(hist_typ_gfa.loc[2025, n]))
                  for n in typ_names}
        gfa_nowcast = dict(by_typology=_built, total=float(sum(_built.values())), consented_2026=_g26)
        evolving_gfa_shares.loc[2026, :] = [_built[n] / gfa_nowcast['total'] for n in typ_names]
    future_blended_olf_bim = blend_per_gfa_share(evolving_gfa_shares, OLF_NET_BIM, typ_names)

    # [FIX f] realised dwelling size held at its recent observed level per
    # typology (parallel to holding OLF constant); the blended value still moves
    # because the typology mix moves.
    future_dwelling_size = blend_per_gfa_share(evolving_gfa_shares, size_ref, typ_names)
    future_blended_olf = blend_per_gfa_share(evolving_gfa_shares, OLF_USED, typ_names)

    # ------------------------------------------------------------------
    # 9. FORWARD DEMAND
    # ------------------------------------------------------------------
    floor_report, growth_check, identity_report, stock_fwd = {}, {}, {}, {}
    results = {}
    # Under the stock basis the model reports BUILT floor area, so the observed
    # 2025 consents are converted with the completion rate.
    real_2025_total = float(hist_gfa_c.loc[2025]) * COMPLETION_RATE

    # Everything that does not depend on the population path (engine.forward).
    fwd_inputs = dict(v=v_forward, rate_demol=demolition_rate, rate_unc=unc_path,
                      dev_2025=(other_dev_2025 if _join_mode == 'carried_deviation' else 0.0),
                      rho_dev=rho_other, rv_share=rv_share,
                      shares=evolving_gfa_shares, size=size_ref, olf=OLF_USED,
                      intensity=T_BASELINE_2025, intensity_upfront=UPFRONT_2025,
                      soil=SOIL_INTENSITY, soil_on_replacement=SOIL_ON_REPLACEMENT,
                      gfa_fixed=({1: gfa_nowcast['total']} if gfa_nowcast else None))
    # NEAR-TERM MARKET EXCESS: 2026 building from observed consents (NOWCAST_METHOD)
    nowcast, join_info = None, {}
    if _join_mode == 'market_excess':
        nowcast = engine.nowcast_year(consents_monthly, 2026, NOWCAST_METHOD, NOWCAST_SEASONAL_YEARS)
    engine_out = {}
    for col in ['5th', '50th', '95th']:
        pop_total = df_forecast[f'PopTotal_{col}'].values
        pop_growth = df_forecast[f'PopGrowth_{col}'].clip(lower=0).values
        hh_arr = households_forecast[col]
        E = engine.forward(pop_total, hh_arr, pop_growth, **fwd_inputs)
        if _join_mode == 'market_excess':
            _b26 = _completion * ((1.0 - lag_w) * float(nowcast['total']) + lag_w * float(hist_units_all.loc[2025]))
            join, ji = engine.market_excess(E, _b26, rho_other, NEAR_TERM_GAP_REF, NEAR_TERM_MODE,
                                            NEAR_TERM_ABSORPTION)
            E = engine.forward(pop_total, hh_arr, pop_growth, join=join, join_redev=ji['redev'],
                               **fwd_inputs)
            join_info[col] = dict(ji, join=join)
        engine_out[col] = E

        occ_per_dw_f, d_hh_f, d_hh_raw = E['occ'], E['d_hh'], E['d_hh_raw']
        floor_report[col] = {'years': int((d_hh_raw[1:] < 0).sum()),
                             'area': float((np.minimum(d_hh_raw, 0) * occ_per_dw_f)[1:].sum())}
        # copies: the 2025 entries are overwritten with the observed anchor below
        g_gross, structural = E['growth_gross'].copy(), E['structural'].copy()
        hs_pos, hs_avoided = E['hs_pos'].copy(), E['hs_avoided'].copy()
        g_demand = E['growth'].copy()             # growth net of consolidation (>= 0)
        extra_space, c_gross = E['extra'].copy(), E['c_gross'].copy()
        _D = E['D']
        stock_fwd[col] = dict(allow=E['allow'] + E['change'], demol=E['demol'], uncons=E['unc'],
                              rv=E['rv'], repl=E['demol'] + E['unc'], stock=E['stock'],
                              join=E['join'], join_redev=E['join_redev'], stock_join=E['stock_join'])
        vac_gfa = (E['allow'] + E['change']) * _D   # vacancy allowance (+ change), m2
        repl_gfa = E['demol'] * _D                 # demolition replacement, m2
        # net replacement above the long-run rate (scenario - long run): the
        # 'redevelopment wave'; the rest is the long-run residual (incl. any
        # carried 2025 deviation)
        wave_gfa = (np.asarray(rate_path, float) - (demolition_rate + unconsented_rate)) * E['prev'] * _D
        unc_gfa = E['unc'] * _D - wave_gfa         # long-run residual, m2
        rv_gfa = E['rv'] * _D                      # housed in RV units, m2 (<0)
        join_gfa = E['join'] * _D + E['gfa_adj']   # near-term join (A1), m2; 2026 = observed GFA
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
        # 2025 is the observed anchor: split its 'other' in the 2026 proportions
        # (the near-term join starts in 2026; it has no 2025 share).
        join_gfa = join_gfa.copy()
        join_gfa[0] = 0.0
        _t1 = vac_gfa[1] + repl_gfa[1] + unc_gfa[1] + wave_gfa[1] + rv_gfa[1]
        _t1 = _t1 if abs(_t1) > 1e-9 else 1.0
        for _arr in (vac_gfa, repl_gfa, unc_gfa, wave_gfa, rv_gfa):
            _arr[0] = other_cons[0] * _arr[1] / _t1

        total = g_demand + hs_pos + c_gross
        identity_report[col] = float(
            np.abs(total[1:] - (structural + c_gross)[1:]).max()
            / max(np.abs((structural + c_gross)[1:]).mean(), 1e-9))

        results[col] = dict(total=total, growth=g_demand, growth_gross=g_gross,
                            hs_pos=hs_pos, hs_avoided=hs_avoided, c_gross=c_gross,
                            extra=extra_space, other=other_cons, vac=vac_gfa, repl=repl_gfa, unc=unc_gfa, wave=wave_gfa, rv=rv_gfa,
                            join=join_gfa,
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
        df_forecast[f'Ann_GFA_Cons_Wave_{col}'] = wave_gfa
        df_forecast[f'Ann_GFA_Cons_RV_{col}'] = rv_gfa
        df_forecast[f'Ann_GFA_Cons_Join_{col}'] = join_gfa

    # ---- retirement-village floor area: reported, out of scope (A4) ----
    rv_floor_area, rv_size_ref = None, float('nan')
    if COL_RV_GFA in df_consents.columns:
        _rvg = df_consents.groupby('Year')[COL_RV_GFA].sum().loc[1991:2025]
        _rw = slice(*DWELLING_SIZE_REF)
        rv_size_ref = float(_rvg.loc[_rw].sum() / hist_rv_units.loc[_rw].sum())
        rv_floor_area = dict(history_built=completed(_rvg) * COMPLETION_RATE,
                             projected=-stock_fwd['50th']['rv'] * rv_size_ref)

    # Projections are BUILT floor area, so history is put on the same basis
    # (consents x completion rate) wherever the two are joined.
    built_factor = COMPLETION_RATE
    # Built history on the same basis as the projection (completions, x completion rate)
    hist_built_gfa = hist_gfa_c * built_factor
    hist_built_typ_gfa = hist_typ_gfa_c * built_factor
    hist_built_units = hist_total_units_c * built_factor     # in-scope dwellings built
    hist_cum = hist_built_gfa.cumsum()
    gfa_2025_cum = float(hist_cum.loc[2025])
    for col in ['5th', '50th', '95th']:
        fwd = df_forecast[f'Ann_GFA_Total_{col}'].cumsum() - df_forecast[f'Ann_GFA_Total_{col}'].iloc[0]
        df_forecast[f'Cum_GFA_Total_{col}'] = gfa_2025_cum + fwd

    print(f"\n[replacement] scenario {_scenario}"
          + (f" (half-life {S3_HALF_LIFE:g} yr)" if _scenario == 'S3' else '')
          + f": net replacement {100 * rate_path[1]:.3f}%/yr in 2026, {100 * rate_path[-1]:.3f}%/yr in 2050 "
          f"(long run {100 * (demolition_rate + unconsented_rate):.3f}%, "
          f"{RECENT_INTERVAL[0]}-{RECENT_INTERVAL[1]} {100 * rate_recent:.3f}%)")
    if _join_mode == 'market_excess':
        ji = join_info['50th']
        print(f"[near-term market excess] 2026 building {ji['O26']:,.0f} (0.95 x consents, {NOWCAST_METHOD}) vs "
              f"requirement {ji['R26']:,.0f} -> excess {ji['e26']:+,.0f}; gap_ref ({NEAR_TERM_GAP_REF}) "
              f"{ji['gap_ref']:+,.0f}, rho {ji['rho']:.2f}; {NEAR_TERM_MODE}: "
              f"{ji['join'][1:].sum():+,.0f} dwellings 2026-2050")

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
    evol_typ_wave = split_typ(df_forecast['Ann_GFA_Cons_Wave_50th'].values)
    evol_typ_rv = split_typ(df_forecast['Ann_GFA_Cons_RV_50th'].values)
    evol_typ_join = split_typ(df_forecast['Ann_GFA_Cons_Join_50th'].values)   # 0 in 2025
    evol_typ_total = pd.DataFrame(engine_out['50th']['gfa_t'].T, index=forecast_years,
                                  columns=typ_names)

    # The 2025 row is the observed anchor. It is put on the same BUILT basis as
    # the projection (consents x completion rate), as the national total is.
    for n in typ_names:
        evol_typ_total.loc[2025, n] = hist_typ_gfa_c.loc[2025, n] * built_factor
        evol_typ_growth.loc[2025, n] = hist_typ_gfa_c.loc[2025, n] * built_factor * anchor['growth']
        evol_typ_hs_pos.loc[2025, n] = hist_typ_gfa_c.loc[2025, n] * built_factor * anchor['housesplit']
        evol_typ_avoided.loc[2025, n] = 0.0
        evol_typ_cons.loc[2025, n] = hist_typ_gfa_c.loc[2025, n] * built_factor * anchor['consumption']
        evol_typ_extra.loc[2025, n] = hist_typ_gfa_c.loc[2025, n] * built_factor * anchor['consumption'] * anchor_extra_share
        evol_typ_other.loc[2025, n] = hist_typ_gfa_c.loc[2025, n] * built_factor * anchor['consumption'] * (1 - anchor_extra_share)
        _o1 = float(df_forecast['Ann_GFA_Cons_Other_50th'].iloc[1]
                    - df_forecast['Ann_GFA_Cons_Join_50th'].iloc[1]) or 1.0
        for _ev, _c in ((evol_typ_vac, 'Vacancy'), (evol_typ_repl, 'Replacement'),
                        (evol_typ_unc, 'Unconsented'), (evol_typ_wave, 'Wave'), (evol_typ_rv, 'RV')):
            _ev.loc[2025, n] = (evol_typ_other.loc[2025, n]
                                * float(df_forecast[f'Ann_GFA_Cons_{_c}_50th'].iloc[1]) / _o1)

    # Constant over time: materials plus soil, no decarbonisation assumed.
    intensity = pd.DataFrame({n: np.full(len(forecast_years), T_BASELINE_2025[n])
                              for n in typ_names}, index=forecast_years)

    # Soil (item 8): the share of each band's floor area that bears soil loss.
    # Bands on new footprints: 1. Net replacement (demolition, residual): 0 unless
    # SOIL_ON_REPLACEMENT. Near-term join: its non-redevelopment part. RV
    # (a proportional share of every dwelling built): the non-replacement
    # share of gross building. The bands then add up to the engine's total.
    # 2025 is the observed anchor: soil on all its floor area, as before.
    _E50 = engine_out['50th']
    _soil_df = pd.DataFrame({n: np.full(len(forecast_years), SOIL_INTENSITY[n]) for n in typ_names},
                            index=forecast_years)
    _mat_df = intensity - _soil_df
    _one = np.ones(len(forecast_years))
    if SOIL_ON_REPLACEMENT:
        f_new = f_repl = f_join = f_rv = _one.copy()
    else:
        _repl_u = np.clip(_E50['demol'] + _E50['unc'] + _E50['join_redev'], 0.0, None)
        _gross_u = np.maximum(_E50['d_hh'], 0.0) + _E50['allow'] + _E50['change'] + _E50['demol'] \
            + _E50['unc'] + _E50['join']
        f_new, f_repl = _one.copy(), 0.0 * _one
        # join band floor area = join x D + gfa_adj (2026 observed GFA); its soil-bearing part
        # is the non-redevelopment dwellings plus the observed-GFA adjustment
        _jg = _E50['join'] * _E50['D'] + _E50['gfa_adj']
        f_join = np.divide((_E50['join'] - _E50['join_redev']) * _E50['D'] + _E50['gfa_adj'], _jg,
                           out=_one.copy(), where=_jg != 0)
        f_rv = (1.0 - np.divide(_repl_u, _gross_u, out=np.zeros_like(_one), where=_gross_u != 0))
    soil_frac = np.asarray(_E50['soil_share'], float).copy()
    for _f in (f_new, f_repl, f_join, f_rv, soil_frac):
        _f[0] = 1.0

    def band_carbon(evol, frac):
        return evol * _mat_df + evol.mul(frac, axis=0) * _soil_df

    carbon_growth_typ = band_carbon(evol_typ_growth, f_new)
    carbon_hs_pos_typ = band_carbon(evol_typ_hs_pos, f_new)
    carbon_avoided_typ = band_carbon(evol_typ_avoided, f_new)
    carbon_extra_typ = band_carbon(evol_typ_extra, f_new)
    carbon_vac_typ = band_carbon(evol_typ_vac, f_new)
    carbon_repl_typ = band_carbon(evol_typ_repl, f_repl)
    carbon_unc_typ = band_carbon(evol_typ_unc, f_repl)
    carbon_wave_typ = band_carbon(evol_typ_wave, f_repl)     # replacement: no soil
    carbon_rv_typ = band_carbon(evol_typ_rv, f_rv)   # in-scope carbon NOT incurred; RV carbon out of scope
    carbon_join_typ = band_carbon(evol_typ_join, f_join)
    carbon_other_typ = (carbon_vac_typ + carbon_repl_typ + carbon_unc_typ + carbon_wave_typ + carbon_rv_typ
                        + carbon_join_typ)
    carbon_cons_typ = carbon_extra_typ + carbon_other_typ
    soil_fracs = {'Growth (net of consolidation)': f_new, 'House-splitting': f_new,
                  'Consumption: extra space': f_new, 'Consumption: vacancy': f_new,
                  'Consumption: demolition': f_repl, 'Calibrated stock residual': f_repl,
                  'Redevelopment wave': f_repl,
                  'Housed in RV units (out of scope)': f_rv, 'Near-term market excess': f_join}
    carbon_total_typ = pd.DataFrame(engine_out['50th']['carbon_t'].T, index=forecast_years,
                                    columns=typ_names)
    carbon_total_typ.loc[2025] = evol_typ_total.loc[2025] * intensity.loc[2025]   # observed anchor

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
                     f"floored to 0 (-> vacancy)")
        print(f"     {c:<5} {'OK  ' if ok else 'FAIL'}  {floor_txt}")
    print(" [2] Structural identity  total == structural + c_gross")
    _band = {c: results[c]['total'][1:].sum() / 1e6 for c in ['5th', '50th', '95th']}
    for c in ['5th', '50th', '95th']:
        print(f"     {c:<5} {'OK  ' if identity_report[c] < 1e-6 else 'FAIL'}  "
              f"max relative deviation = {identity_report[c]:.2e}")
    print(f" [3] Population-only band (household size, mix, dwelling size and carbon\n"
          f"     factors held fixed), total GFA 2026-2050 (Mm2): "
          f"5th {_band['5th']:.2f} | 50th {_band['50th']:.2f} | 95th {_band['95th']:.2f}")

    # ------------------------------------------------------------------
    # STOCK, VACANCY AND REPLACEMENT
    # ------------------------------------------------------------------
    sc = stock_cal
    wcal = (years_hist >= DEMOLITION_CALIB_START) & (years_hist <= calib_end)
    print("\n" + "=" * 78)
    print(" STOCK, VACANCY, DEMOLITION AND UNCONSENTED ADDITIONS  (built basis)")
    print("=" * 78)
    print("   vacancy (empty / private dwellings): " +
          " | ".join(f"{y} {100*v:.2f}%" for y, v in sc['knots'].items()) +
          f"  -> held at {100*v_forward:.2f}% forward")
    print(f"   build duration W, Little's law (under construction / all consents in the 12 months to March): " +
          " | ".join(f"{y} {d:.2f}" for y, d in build_duration.items()) +
          f" -> completion lag W used = {lag_w:.3f} yr ({COMPLETION_LAG})")
    nb_hist = hist_built_units[wcal].mean()
    print(f"\n   The stock bucket, {DEMOLITION_CALIB_START}-{calib_end} mean per year (census-benchmarked; dwellings):")
    print(f"     {'new households':<46}{d_hh[wcal].mean():>9,.0f}")
    print(f"     {'+ vacancy allowance':<46}{sc['allow'][wcal].mean():>9,.0f}")
    print(f"     {'+ vacancy change':<46}{sc['change'][wcal].mean():>9,.0f}")
    print(f"     {f'+ demolitions replaced ({100*DEMOLITION_RATE:.3f}% of stock, fixed)':<46}"
          f"{sc['demol'][wcal].mean():>9,.0f}")
    print(f"     {'+ calibrated residual (see note)':<46}{sc['uncons'][wcal].mean():>9,.0f}")
    print(f"     {'- retirement-village units built (out of scope)':<46}{sc['rv'][wcal].mean():>9,.0f}")
    print(f"     {'= dwellings built (in scope)':<46}{nb_hist:>9,.0f}")
    print(f"     {f'/ completion rate {COMPLETION_RATE:.2f}, lag W {lag_w:.3f} = consents':<46}"
          f"{hist_total_units_c[wcal].mean():>9,.0f}  (observed, timed as completions)")
    print(f"   calibrated residual = {100*unconsented_rate:+.3f}% of stock per year "
          f"(< 0: unconsented additions; > 0: losses beyond the BRANZ demolition rate) "
          f"({100*sc['uncons'][wcal].mean()/nb_hist:+.1f}% of building)")
    neg = int((sc['net'][wcal] < 0).sum())
    print(f"   single years where demolition < unconsented additions: {neg}/{int(wcal.sum())} "
          f"(vacancy interpolated between censuses; only the long-run rate is used)")
    # Plausibility check: what would 'residents away counted as vacant' require?
    _all = (census['unoccupied'] / census['total_private']).to_dict()
    _v = pd.Series(np.interp(years_hist.astype(float), list(_all), list(_all.values())),
                   index=years_hist)
    _prev = (hist_hh / (1 - _v)).shift(1)
    _net_all = (COMPLETION_RATE * hist_units_all_c - d_hh - d_hh * _v / (1 - _v)
                - hist_hh.shift(1) * (1 / (1 - _v)).diff())
    _unc_all = (_net_all - DEMOLITION_RATE * _prev)[wcal].mean()
    print(f"   [check] counting 'residents away' as vacant would need unconsented additions of "
          f"{_unc_all:,.0f}/yr ({100*_unc_all/nb_hist:+.0f}% of building) vs "
          f"{sc['uncons'][wcal].mean():,.0f} -> rejected as implausible")
    # ---- net replacement by source (census dwelling counts vs household identity) ----
    print(f"\n   Net replacement (demolition + residual), % of stock/yr, by census interval "
          f"(completions lagged W = {lag_w:.3f} yr):")
    for r in census_rates.itertuples():
        _w = (years_hist > r.y0) & (years_hist <= r.y1) & sc['prev'].notna().values
        _hh = (float(sc['net'][_w].sum() / sc['prev'][_w].sum())) if _w.any() else float('nan')
        print(f"     {r.y0}-{r.y1}: dwelling counts {100 * r.rate:+.3f}% | household identity {100 * _hh:+.3f}%")
    print(f"     long run {_nr_window[0]}-{_nr_window[1]}: dwelling counts "
          f"{100 * engine.census_window_rate(census_rates, *_nr_window):+.3f}% | household identity "
          f"{DEMOLITION_CALIB_START}-{calib_end} {100 * (DEMOLITION_RATE + sc['rate_unc']):+.3f}%")
    print(f"     IN USE (dwelling counts): {100 * (DEMOLITION_RATE + unconsented_rate):+.3f}%/yr")

    # ---- retirement villages: in the stock, out of carbon scope ----
    print(f"\n   RETIREMENT VILLAGES (counted in the stock; out of floor-area and carbon scope)")
    print(f"     consented RV units = all-category dwellings - three typologies")
    for a_, b_ in [(1992, 2005), (2006, 2015), (2016, 2025)]:
        print(f"     {a_}-{b_}: {hist_rv_units.loc[a_:b_].mean():6,.0f} consented/yr "
              f"({100 * hist_rv_share.loc[a_:b_].mean():.1f}% of all new dwellings)")
    print(f"     forward share of all dwellings built: {100 * rv_share:.2f}% "
          f"(ratio of sums {RV_SHARE_REF[0]}-{RV_SHARE_REF[1]}; annual range since 2011 "
          f"{100 * hist_rv_share.loc[2011:].min():.1f}-{100 * hist_rv_share.loc[2011:].max():.1f}%)")
    _sf = stock_fwd['50th']
    _nb = (results['50th']['total'][1:] / future_dwelling_size.values[1:]).mean()
    print(f"\n   Forward 2026-2050, median, dwellings per year:")
    for lab, v_ in [('new households', results['50th']['d_hh'][1:].mean()),
                    ('+ vacancy allowance', _sf['allow'][1:].mean()),
                    ('+ demolitions replaced', _sf['demol'][1:].mean()),
                    ('+ calibrated residual', _sf['uncons'][1:].mean()),
                    ('- retirement-village units', _sf['rv'][1:].mean()),
                    ('= dwellings built (in scope)', _nb)]:
        print(f"     {lab:<30}{v_:>9,.0f}{'' if lab.startswith('=') else f'{100*v_/_nb:>8.1f}%'}")
    _rv_tot = -_sf['rv'][1:].sum()
    print(f"     retirement-village units built 2026-2050: {_rv_tot:,.0f} "
          f"(median; carbon not estimated, out of scope)")
    if rv_floor_area is not None:
        print(f"     retirement-village FLOOR AREA (Stats NZ consents; out of scope): "
              f"{rv_size_ref:.1f} m2/unit ({DWELLING_SIZE_REF[0]}-{DWELLING_SIZE_REF[1]}) -> "
              f"{rv_floor_area['projected'][1:].sum() / 1e6:.2f} Mm2 built 2026-2050 "
              f"(in-scope total {results['50th']['total'][1:].sum() / 1e6:.2f} Mm2); "
              f"history 2016-2025 {rv_floor_area['history_built'].loc[2016:2025].sum() / 1e6:.2f} Mm2 built")

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
             ('Calibrated stock residual (long run)', evol_typ_unc, carbon_unc_typ),
             ('Redevelopment wave (scenario - long run)', evol_typ_wave, carbon_wave_typ),
             ('Housed in RV units (out of scope)', evol_typ_rv, carbon_rv_typ),
             ('Near-term market excess', evol_typ_join, carbon_join_typ)]
    rows = [(lab, g.iloc[1:].sum().sum() / 1e6, c.iloc[1:].sum().sum() / 1e6) for lab, g, c in bands]
    tg = sum(r[1] for r in rows); tc = sum(r[2] for r in rows)
    print("\n BY DEMAND TYPE, 2026-2050 (median)")
    print(f"   {'':<34}{'floor area':>12}{'share':>8}{'carbon':>12}")
    print(f"   {'':<34}{'(Mm2)':>12}{'':>8}{'(kt CO2e)':>12}")
    for lab, g, c in rows:
        print(f"   {lab:<34}{g:>12.2f}{100 * g / tg:>7.1f}%{c:>12,.0f}")
    print(f"   {'TOTAL BUILT':<34}{tg:>12.2f}{100.0:>7.1f}%{tc:>12,.0f}")
    # Demolition and the residual trade one-for-one in calibration (only their
    # sum is identified by the stock identity), so report the sum too.
    _net_g = rows[4][1] + rows[5][1] + rows[6][1]
    _net_c = rows[4][2] + rows[5][2] + rows[6][2]
    print(f"   {'(demolition + residual: identified net)':<34}{_net_g:>12.2f}"
          f"{100 * _net_g / tg:>7.1f}%{_net_c:>12,.0f}")
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
    plot_hist_estimated(plt.gca(), hist_hh, 1e6, label='Historical (31 Dec)')
    plt.plot(forecast_years, households_forecast['50th'] / 1e6, color='darkorange', linestyle='--',
             label='Projected Median')
    plt.fill_between(forecast_years, households_forecast['5th'] / 1e6, households_forecast['95th'] / 1e6,
                     color='darkorange', alpha=0.2,
                     label='5th-95th population percentile (household size fixed)')
    plt.axvline(2025, color='black', linestyle=':', alpha=0.6)
    plt.ylabel('Households (millions)'); plt.title('New Zealand Households (1991-2050)')
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()

    # FIG 2 cumulative GFA
    plt.figure(figsize=(13, 7))
    plt.plot(years_hist, hist_cum.values, color='black', linewidth=3, label=f'Historical (consents x {built_factor:.2f}, lagged W={lag_w:.2f} = built)')
    plt.plot(df_forecast['Year'], df_forecast['Cum_GFA_Total_50th'], color='darkred',
             linewidth=2.5, label='Projected Total GFA (Median)')
    plt.fill_between(df_forecast['Year'], df_forecast['Cum_GFA_Total_5th'],
                     df_forecast['Cum_GFA_Total_95th'], color='darkred', alpha=0.2,
                     label='Population 5th-95th percentile (other inputs fixed)')
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v / 1e6:,.0f}'))
    plt.ylabel('Cumulative new GFA (Mm²)')
    plt.title('Cumulative New Residential GFA Projection')
    plt.legend(loc='upper left'); plt.grid(True, alpha=0.3)
    plt.xlim(1991, 2050); plt.tight_layout()

    # Demand bands for figs 3-5 (annual, 2026-2050): one list, so the figures
    # and the identity test use the same numbers.
    def _band_list(get, scale):
        spec = [('Growth demand (net of consolidation)', 'growth', DEMAND_COLORS[0]),
                ('House-splitting demand', 'hs_pos', HOUSESPLIT_COLOR),
                ('Consumption: extra space per dwelling', 'extra', DEMAND_COLORS[1]),
                ('Consumption: vacancy allowance', 'vac', DEMAND_COLORS[2]),
                ('Consumption: replacement of demolished stock', 'repl', DEMAND_COLORS[3]),
                (UNCONSENTED_LABEL, 'unc', UNCONSENTED_COLOR),
                (WAVE_LABEL, 'wave', WAVE_COLOR),
                (JOIN_LABEL, 'join', JOIN_COLOR),
                (RV_LABEL, 'rv', RV_COLOR)]
        return [(lab, get(k) / scale, col) for lab, k, col in spec]
    _gfa_cols = dict(growth='Growth', hs_pos='HouseSplit_Pos', extra='Cons_ExtraSpace', vac='Cons_Vacancy',
                     repl='Cons_Replacement', unc='Cons_Unconsented', wave='Cons_Wave', join='Cons_Join',
                     rv='Cons_RV')
    _carb = dict(growth=carbon_growth_typ, hs_pos=carbon_hs_pos_typ, extra=carbon_extra_typ, vac=carbon_vac_typ,
                 repl=carbon_repl_typ, unc=carbon_unc_typ, wave=carbon_wave_typ, join=carbon_join_typ,
                 rv=carbon_rv_typ)
    fig_bands = {
        'gfa': (_band_list(lambda k: df_forecast[f'Ann_GFA_{_gfa_cols[k]}_50th'].values[1:], 1e6),
                df_forecast['Ann_GFA_HouseSplit_Avoided_50th'].values[1:] / 1e6),
        'carbon': (_band_list(lambda k: _carb[k].sum(axis=1).values[1:], 1e6),
                   carbon_avoided_typ.sum(axis=1).values[1:] / 1e6)}

    # FIG 3 annual GFA
    fig3, (bx1, bx2) = plt.subplots(1, 2, figsize=(18, 6))
    bx1.stackplot(plot_years, [evol_typ_total[n].iloc[1:] / 1e6 for n in typ_names],
                  labels=typ_names, colors=stack_colors, alpha=0.85)
    bx1.set_ylabel('Annual new GFA (Mm²/yr)')
    bx1.set_title('Annual GFA by Typology (2026-2050)')
    bx1.legend(loc='lower left', fontsize=9); bx1.grid(True, alpha=0.3); bx1.set_xlim(2026, 2050)

    plot_demand_bands(bx2, plot_years, fig_bands['gfa'][0], fig_bands['gfa'][1])
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

    plot_demand_bands(cx2, plot_years, fig_bands['carbon'][0], fig_bands['carbon'][1])
    cx2.set_ylabel('Annual Carbon (kt CO2e/yr)')
    cx2.set_title('Annual Embodied Carbon by Demand Type (2026-2050)')
    cx2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=8); cx2.grid(True, alpha=0.3); cx2.set_xlim(2026, 2050)
    plt.tight_layout()

    # FIG 5 cumulative carbon  -- slice BEFORE accumulating
    cum_typ = (carbon_total_typ.iloc[1:] / 1e6).cumsum()
    fig5, (dx1, dx2) = plt.subplots(1, 2, figsize=(18, 6))
    dx1.stackplot(plot_years, [cum_typ[n].values for n in typ_names],
                  labels=typ_names, colors=stack_colors, alpha=0.85)
    dx1.set_ylabel('Cumulative Carbon (kt CO2e)')
    dx1.set_title('Cumulative Embodied Carbon by Typology (2026-2050)')
    dx1.legend(loc='lower left', fontsize=9); dx1.grid(True, alpha=0.3); dx1.set_xlim(2026, 2050)

    plot_demand_bands(dx2, plot_years, [(l, np.cumsum(v), c) for l, v, c in fig_bands['carbon'][0]],
                      np.cumsum(fig_bands['carbon'][1]))
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
    plot_hist_estimated(ex1, hist_S, 1.0, label='Historical (census-benchmarked)', lw=2.5)
    ex1.plot(forecast_years, df_forecast['PopTotal_50th'].values / households_forecast['50th'],
             color='darkorange', linestyle='--', linewidth=2.5, label='Projected (Stats NZ shape, census-rebased)')
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
    flow_annual['SOIL'] = sum(evol_typ_total[t].values * SOIL_INTENSITY[t] * soil_frac
                              for t in typ_names)
    flow_annual = flow_annual.loc[plot_years]              # drop the 2025 anchor
    flow_cum = flow_annual.cumsum()

    # Carbon by demand type x material, using each demand band's own mix.
    demand_bands = {'Growth (net of consolidation)': evol_typ_growth,
                    'House-splitting': evol_typ_hs_pos,
                    'Consumption: extra space': evol_typ_extra,
                    'Consumption: vacancy': evol_typ_vac,
                    'Consumption: demolition': evol_typ_repl,
                    'Calibrated stock residual': evol_typ_unc,
                    'Redevelopment wave': evol_typ_wave,
                    'Housed in RV units (out of scope)': evol_typ_rv,
                    'Near-term market excess': evol_typ_join}
    dem_mat = pd.DataFrame(
        {lab: [sum(df[t].iloc[1:].sum() * MAT_INTENSITY.loc[m, t] for t in typ_names)
               for m in MATERIALS] + [sum((df[t].values * soil_fracs[lab])[1:].sum() * SOIL_INTENSITY[t]
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
    _soil = sum((evol_typ_total[t].values * soil_frac)[1:].sum() * SOIL_INTENSITY[t] for t in typ_names)
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
    if SAVE_FIGURES:
        save_open_figures(BOSS_FIGURE_NAMES, FIG_DIR)
    state = dict(locals())
    if SHOW_PLOTS:
        plt.show()
    else:
        plt.close('all')
    return state


def plot_hist_estimated(ax, series, scale=1.0, color='black', label='Historical', lw=2.0,
                        census_last=2018, anchor=None):
    """Households / household size history: census-benchmarked years solid,
    2019-2025 dotted ("estimated from consents, not a census count"), the
    census anchor year marked, and the join annotated."""
    anchor = S_ANCHOR_YEAR if anchor is None else anchor
    s = series.dropna() / scale
    ax.plot(s.loc[:census_last].index, s.loc[:census_last].values, color=color, lw=lw, label=label)
    tail = s.loc[census_last:]
    ax.plot(tail.index, tail.values, color=color, lw=lw, ls=':',
            label=f'{census_last + 1}-{int(s.index.max())} estimated from consents (not a census count)')
    if anchor in s.index:
        ax.plot([anchor], [s.loc[anchor]], 'o', color=color, ms=6, label=f'{anchor} census anchor')
        ax.annotate(f'projection anchored on {anchor} census;\n{anchor + 1}-{int(s.index.max())} estimates not used',
                    xy=(anchor, s.loc[anchor]), xytext=(10, -28), textcoords='offset points', fontsize=7,
                    color='grey', arrowprops=dict(arrowstyle='-', color='grey', lw=0.6))
    ax.ticklabel_format(axis='y', style='plain', useOffset=False)


def plot_demand_bands(ax, years, bands, avoided=None):
    """Signed stack: the positive part of each band stacked upward from zero,
    the negative part (RV, a negative join) downward from zero. 'Avoided'
    (consolidation) is drawn as an outline above the total, not stacked. The
    dashed line is the signed sum of the bands, which equals the typology total
    (tests/test_identities.py). Returns that sum."""
    years = np.asarray(years)
    up, dn = np.zeros(len(years)), np.zeros(len(years))
    for lab, v, col in bands:
        v = np.asarray(v, float)
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        if np.any(pos > 0):
            ax.fill_between(years, up, up + pos, color=col, alpha=0.85, lw=0, label=lab)
        if np.any(neg < 0):
            ax.fill_between(years, dn + neg, dn, color=col, alpha=0.45, lw=0, hatch='..',
                            label=None if np.any(pos > 0) else lab)
        up, dn = up + pos, dn + neg
    total = sum(np.asarray(v, float) for _, v, _ in bands)
    if avoided is not None and np.any(np.asarray(avoided) > 0):
        ax.fill_between(years, total, total + np.asarray(avoided, float), facecolor='none',
                        edgecolor=HOUSESPLIT_COLOR, hatch='//', lw=0.8,
                        label='Avoided floor area (consolidation; not built, not stacked)')
    ax.plot(years, total, color='black', linestyle='--', linewidth=1.5, label='Total built (net) = typology total')
    ax.axhline(0, color='black', lw=0.7)
    return total


def export_results(B, path):
    """Write the central run's report tables to JSON (read by tools/baseline_draft.py;
    every number in the draft report comes from here or another generated file)."""
    import json
    f = slice(1, None)
    tot = lambda df: float(df.iloc[f].sum().sum())
    bands = [('Growth (net of consolidation)', 'evol_typ_growth', 'carbon_growth_typ'),
             ('House-splitting', 'evol_typ_hs_pos', 'carbon_hs_pos_typ'),
             ('Extra space per dwelling', 'evol_typ_extra', 'carbon_extra_typ'),
             ('Vacancy allowance', 'evol_typ_vac', 'carbon_vac_typ'),
             ('Demolition replacement', 'evol_typ_repl', 'carbon_repl_typ'),
             ('Calibrated stock residual (long run)', 'evol_typ_unc', 'carbon_unc_typ'),
             ('Redevelopment wave (scenario - long run)', 'evol_typ_wave', 'carbon_wave_typ'),
             ('Near-term market excess', 'evol_typ_join', 'carbon_join_typ'),
             ('Housed in RV units (out of scope)', 'evol_typ_rv', 'carbon_rv_typ')]
    typ = list(B['typ_names'])
    et, ct = B['evol_typ_total'], B['carbon_total_typ']
    shares = B['evolving_gfa_shares']
    stages = {s: float(sum(et[t].values[f].sum() * B['stage_int'].loc[s, t] for t in typ) / 1e6)
              for s in B['stage_int'].index}
    R = B['results']
    out = dict(
        settings=dict(scenario=B['_scenario'], s3_half_life=S3_HALF_LIFE, near_term_join=B['_join_mode'],
                      nowcast_method=NOWCAST_METHOD, near_term_mode=NEAR_TERM_MODE,
                      completion_rate=COMPLETION_RATE, lag_w=float(B['lag_w']), phi=DAMPING_PHI),
        gfa_Mm2=float(R['50th']['total'][f].sum() / 1e6), carbon_kt=float(B['tot_carbon_median']),
        upfront_kt=float(B['_upfront'] + B['_soil'] / 1e6), soil_kt=float(B['_soil'] / 1e6),
        stages_kt=stages,
        pop_band_gfa_Mm2={p: float(R[p]['total'][f].sum() / 1e6) for p in ('5th', '50th', '95th')},
        demand_bands=[dict(band=lab, gfa_Mm2=tot(B[g]) / 1e6, carbon_kt=tot(B[c]) / 1e6)
                      for lab, g, c in bands],
        typology={t: dict(gfa_Mm2=float(et[t].values[f].sum() / 1e6), carbon_kt=float(ct[t].values[f].sum() / 1e6),
                          share_2025=float(shares[t].iloc[0]), share_2050=float(shares[t].iloc[-1]))
                  for t in typ},
        material_kt={m: float(v / 1e6) for m, v in B['flow_annual'].sum().items()},
        annual=dict(years=[int(y) for y in B['forecast_years']],
                    gfa_Mm2=[float(v / 1e6) for v in R['50th']['total']],
                    carbon_kt=[float(v / 1e6) for v in ct.sum(axis=1).values]),
        S_2050=float(B['df_forecast']['PopTotal_50th'].values[-1] / B['households_forecast']['50th'][-1]))
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=2)


if __name__ == "__main__":
    SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'
    export_results(main(), os.path.join(OUT_DIR, 'boss_results.json'))
