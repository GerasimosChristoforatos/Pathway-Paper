"""
New residential floor area and embodied carbon, New Zealand 2026-2050
=====================================================================
Bottom-up demographic model of new residential floor area and its embodied
carbon (A1-A5, B2, B4, C1-C4, plus soil carbon loss) by demand band and
material (typology is internal: it weights the case-study factors).

    total floor area = new dwellings required x realised dwelling size
    new dwellings    = new households + vacancy allowance + replacement

All input data are read from DATA_DIR; every output path comes from layout.py.
Case-study carbon and occupancy factors come from Building_factors.py (run it
first; it writes them to outputs/data/factors/). MODEL v3.0.0 (compute / draw separation): this module draws
nothing; run as a script it writes, with export_figure_sources(B), the exact arrays of D01-D03, D08, D09, D13 and
the Extended Data paths (figure_source/projection_paths.json); figures/calibration.py draws them.
"""

import os
import re
import pandas as pd
import numpy as np
from scipy.interpolate import PchipInterpolator

import engine
import events as EV
import bands as BANDS
import layout
import naming as N
import figsource
import Building_factors as BF

# ============================================================
# CONFIGURATION
# ============================================================
# Paths are anchored on this file's folder (the repository root), so every
# script and test works from any working directory (e.g. Spyder).
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, 'data')          # inputs only
# Frozen-technology check run (run_all.py steps 'frozen_*', env PATHWAY_FROZEN=1):
# DECARB_MODE 'none', A4-A5 held, whole life at construction (the regression anchor:
# it reproduces v1.2.1 / baseline v2); its data go to outputs/data/frozen_technology/
# (layout.py: every path of the pipeline).
FROZEN_RUN = layout.frozen_run()
FACTORS_DIR = layout.FACTORS     # written by Building_factors.py
# MODEL v3.0.0: projection.py draws nothing (figures/calibration.py draws D01-D03, D08, D09, D13 from the figure
# source written by export_figure_sources). SHOW_PLOTS and SAVE_FIGURES are kept as inert attributes only, because
# other scripts and the tests still set them (Diagnostics, Sensitivity, validation, tools, tests/conftest.py).
SHOW_PLOTS = False
SAVE_FIGURES = False
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
# HH_SIZE_PATH (MODEL v4.0.0): 'statsnz' (ADOPTED: the Stats NZ 2018-base household projection shape, rebased on the
#   2023 census as above; to be replaced by the 2023-base household projections when published) or 'census_pace'
#   (sensitivity: household size continues LINEARLY from the 2023 anchor at the 2018-2023 census-interval pace,
#   (S_2023 - S_2018) / 5 per year, census-benchmarked households; HH_SIZE_PACE_WINDOW).
HH_SIZE_PATH = 'statsnz'
HH_SIZE_PACE_WINDOW = (2018, 2023)

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
#   households temporarily absent); k = 0.824 (printed at run time). Only the 2018->2023 RATIO is
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
# Reader-facing labels: naming.py (docs/RENAMING.md); the figures are drawn by the figures/ package from the
# figure source written by export_figure_sources(), never from here.

# Typology mix (author's decision, baseline-pb-v2): the typology floor-area shares are held at
#   their MIX_HELD_WINDOW average (ratio of sums of consented floor area over the window, 2026 =
#   the observed months, January-July) in every variant. The typology mix is internal to the model
#   (it weights the case-study factors) and is not reported. The damped log-ratio trend of v1.0.2-
#   v1.2 was never run in a reported result and is removed (MODEL v1.0.0; tag baseline-PB_v1.2).
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
# is measured (census tables below); forward the vacancy-rate parameter is held at its
# published 2023 census value (naming.VACANCY_WORDING: implied stock vacancy still rises,
# because the 2026 overbuild is not absorbed). Identity: total floor area = (new households + allowance + change +
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

# REPLACEMENT_VARIANT (net replacement path, on the census dwelling-count rates):
#   'REF':  the Reference: the 2018-2023 rate fades to the long-run rate with
#           half-life REPLACEMENT_HALF_LIFE years (10; 5 and 15 are sensitivity variants);
#   'LOW':  Low replacement: the long-run rate (NET_REPLACEMENT_WINDOW) throughout;
#   'HIGH': High replacement: the 2018-2023 census-interval rate persists;
#   'VHIGH': Very High replacement (trend continues; MODEL v3.3.0): the weighted (by interval length) linear OLS
#           trend of the census-interval rates 1991-2023 extrapolated 2026-2050 (engine.replacement_trend).
# Author's decision: Low and High bound the Reference (JUDGEMENT: the half-life is
# not identifiable from the census record; it is sampled U(5, 15) yr in the Monte Carlo, MODEL v3.3.0). Very High is
# a sensitivity variant, not the Reference: six interval rates (seven censuses), one negative, a definition break in
# 2013-2018 and the unbounded extrapolation of a policy-driven wave.
REPLACEMENT_VARIANT = 'REF'
REPLACEMENT_HALF_LIFE = 10.0
RECENT_INTERVAL = (2018, 2023)

# ---------------------------------------------------------------------------
# NEAR-TERM MARKET EXCESS
# ---------------------------------------------------------------------------
# OVERBUILD_RULE:
#   'carried_deviation': no observed 2026 data; 2025's deviation fades at rho
#       (used only by the 2026 out-of-sample check, validation.NO_2026_DATA).
# v1.1 default: 'market_excess' -- ONE rule on top of any replacement scenario:
#   2026 building = observed (NOWCAST_METHOD). Its excess over the 2026
#   requirement is the 'near-term market excess'. From 2027 the building
#   continues above the requirement by gap_ref x rho^(t-2026), with gap_ref =
#   building_2026 - requirement_2027 (the 2027 requirement, because the 2026 one
#   is depressed by the one-off 2026 population shortfall) and rho = rho_other
#   (the estimated persistence of departures from the calibrated identity).
#   OVERBUILD_BOOKING 'surplus' with absorption 0 (default): the excess is
#   STOCK-ADDING -- extra dwellings join the stock as vacancy that is never
#   absorbed; soil applies; removals stay on the scenario path. Implied vacancy
#   = 1 - households / (stock + cumulative excess). Sensitivities: 'redevelopment'
#   (stock-neutral), payback (OVERBUILD_ABSORPTION 0.20 / 0.10), and
#   OVERBUILD_GAP_REF = '2026'.
#   MODEL v3.0.0 (Reference): the surplus is ABSORBED by OVERBUILD_ABSORPTION_END along the
#   normalised logistic of the levers (engine.logistic_weights, 2026 -> 2035: w(2026) = 0,
#   w >= 2035 = 1): remaining surplus U(t) = C(t) (1 - w(t)), C the cumulative excess; the
#   absorbed part is built less (payback, capped at the year's building, shortfall carried;
#   engine.absorb_overbuild). Implied vacancy 1 - hh / (stock + U) returns to the vacancy
#   parameter by 2035. Theory (stock-flow models of the housing market: Rosen & Smith 1983;
#   Wheaton 1990; DiPasquale & Wheaton 1992; Gabriel & Nothaft 2001) fixes the DIRECTION
#   (reversion of vacancy to its equilibrium rate), not the speed; 2035 is the common RECC
#   adoption window of the model; the speed is bracketed by sensitivity rows (never absorbed =
#   MODEL v2.1; by 2030; by 2045). OVERBUILD_ABSORPTION_END None = never absorbed with
#   OVERBUILD_ABSORPTION the constant share (MODEL v2.1; run_all.py --reference-legacy).
OVERBUILD_RULE = 'market_excess'
OVERBUILD_GAP_REF = '2027'
OVERBUILD_BOOKING = 'surplus'
OVERBUILD_ABSORPTION = 0.0
REFERENCE_LEGACY = os.environ.get('PATHWAY_REFERENCE_LEGACY') == '1'
# VACANCY_PARAMETER: 'census_2023' (adopted; the published 2023 census value, 5.39%) or 'consistent_mean'
#   (sensitivity: the mean of the 1986-2023 censuses on one definition)
VACANCY_PARAMETER = 'census_2023'
OVERBUILD_ABSORPTION_START = 2026
OVERBUILD_ABSORPTION_END = None if REFERENCE_LEGACY else 2035
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
# COMPLETION_RATE (MODEL v4.0.0): 0.945, the midpoint of the published completion milestones of Jones,
#   Greenaway-McGrevy & Crow (2025, Policy Quarterly 21(1), 63-68, footnote 12; Auckland consents): 93% of 2018-2019
#   consents had a final inspection by July 2024 (a lower bound: counted late, some completed dwellings are never
#   inspected within the window) and more than 95% of 2018-2021 consents had a first inspection (construction
#   started; an upper bound on eventual completion). The article gives the upper milestone only as '>95%', with no
#   point value: the band edge 0.96 is a stated judgement (the upper edge of the MODEL v3.3 band), not a published
#   number. The Monte Carlo draws the rate uniform on COMPLETION_RATE_BAND = (0.93, 0.96); no shape inside the band
#   is identified, hence uniform. LIMITATION: the evidence is Auckland's, applied nationally. MODEL v3.3 used 0.95 (the
#   authors' own assumption) with the two-piece band (0.92, 0.95, 0.96). The legacy Reference (REFERENCE_LEGACY,
#   MODEL v2.1) keeps 0.95.
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

COMPLETION_RATE = 0.95 if REFERENCE_LEGACY else 0.945
COMPLETION_RATE_BAND = (0.93, 0.96)

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
# COMPLETION_LAG_MONTHS (MODEL v4.0.0, adopted 17): consent-to-completion lag in months. Completions(month m) =
#   COMPLETION_RATE x consents(month m - L), aggregated to calendar years; the SAME lag everywhere consents become
#   'built': the history (stock identity, census-interval net replacement, the dwelling-size and typology-mix
#   windows, historical floor area, the AR / AtP base) and the projection start. L = 17 is the midpoint of the median
#   time to dwelling completion of 1.27-1.53 yr (15.2-18.4 months) in Auckland as of July 2024 (Jones,
#   Greenaway-McGrevy & Crow 2025, Policy Quarterly 21(1), 63-68, citing Greenaway-McGrevy & Jones 2023); consistent
#   with the Stats NZ Experimental building indicators (dwelling-weighted median days from consent to final inspection
#   455 for December 2020 quarter consents, March 2022 quarter release, Table 1; 533 for September 2022 quarter
#   consents, December 2023 quarter release, Table 1). Projection years whose 12 lagged months are all observed are
#   PIPELINE years (L = 17, consents to July 2026: 2026 and 2027): their building is observed, not modelled (the
#   market excess over the requirement, engine.market_excess with n observed years; their floor area fixed in every
#   run). 0 reproduces MODEL v3.3 (same-calendar-year consents; 2026 from the last-12-months nowcast). Not combined
#   with COMPLETION_LAG (the two-point W) != 0. The legacy Reference (REFERENCE_LEGACY, MODEL v2.1) keeps 0.
COMPLETION_LAG_MONTHS = 0 if REFERENCE_LEGACY else 17
# CONSENT_DATA_END (MODEL v4.0.0): None = every observed month; 'YYYY-MM-01' truncates the monthly consents (the
#   'No 2026 data' check, validation.NO_2026_DATA, adapted to the lag).
CONSENT_DATA_END = None
DEMOLITION_RATE = 0.00135


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

FILE_FACTORS_DECARB = os.path.join(FACTORS_DIR, 'factors_a13_decarb.csv')
FILE_FACTORS_DECARB_BLD = os.path.join(FACTORS_DIR, 'factors_building_a13_reduction.csv')

# MATERIAL DECARBONISATION OF A1-A3 (author decision; adopted: 'horup_item').
# 'none': A1-A3 held at its 2025 case-study value (frozen technology; the regression
# anchor and a sensitivity).
# 'horup_item': the material-specific GWP paths of Horup et al. (2025), Sci. Total
# Environ. 966, 178780, Fig. 2 and SI Table S4 (average of 9 premise scenarios,
# relative to 2025, linear between 2025/2030/2040/2050), applied to each EPD item of
# the case studies, mapped one-to-one to an S4 row (direct, Horup p. 6, or proxy) or
# held, by data/material_item_map.csv. Mapping and values: Building_factors.py and
# outputs/data/factors/factors_a13_decarb.csv. The history (and so the acquired-rights
# base of boundaries.py) always uses 2025 factors. (The class-level mapping of v1.1 is
# preserved at tags baseline-PB_v1.2 / baseline-PB_v2.)
DECARB_MODE = 'none' if FROZEN_RUN else 'horup_item'   # see Building_factors.DECARB_MODES
DECARB_ITEM_CASE = 'central'        # 'horup_item' only: 'central' or a sensitivity in Building_factors.ITEM_CASES
# A4-A5 (not separable by material process): 'resch' (adopted) = generic technological
# progress e^(-0.01 (t - 2025)), Resch et al. (2021) Table 1 (Building_factors.generic_path);
# sensitivities 'held' (2025 factors) and 'item' (each item's own S4 path).
DECARB_A45 = 'held' if FROZEN_RUN else 'resch'
# ACCOUNTING (author decision, baseline-pb-v3):
#   'time_resolved' (adopted): each year's construction is booked with its upfront
#       carbon (A1-A5 + soil); replacements and repaints (B2, B4) are booked in the
#       calendar year they occur (events.py; EVENT_TIMING), within 2026-2050 for the
#       buildings built from 2026; later events and all end of life (C1-C4) are
#       committed emissions after 2050, reported separately as a range.
#   'whole_life_at_construction': every stage booked in the construction year (v1-v2);
#       with DECARB_A45 'held' it reproduces baseline-pb-v2 exactly (regression).
ACCOUNTING = 'whole_life_at_construction' if FROZEN_RUN else 'time_resolved'
EVENT_TIMING = 'n+1'       # event k at k L / (n + 1); 'n': k L / n (sensitivity)
# Scope of B events (author decision): those of the buildings built in the window
#   only (projection: from 2026; AR base: from the base window's first year). The
#   wider scope, which adds the events of every cohort built since B_SCOPE_START
#   (upkeep of the post-1992 stock) in base and projection alike, is a PB
#   sensitivity row (boundaries.legacy_events, boundaries.window_base(scope='since_1992')).
B_SCOPE_START = 1992


def load_decarb_a45(mode, a45, typ_names, materials, years):
    """A4-A5 reduction versus 2025 (kg CO2e/m2) by material and typology, by year,
    or None ('held'). a45: 2025 A4-A5 factors (materials x typology). 'resch':
    generic e^(-0.01 (t - 2025)); 'item': each item's own S4 path
    (Building_factors.OUT_A45_ITEM)."""
    if mode == 'held':
        return None
    if mode == 'resch':
        g = BF.generic_path(years)
        return {m: {t: a45.loc[m, t] * (1.0 - g) for t in typ_names} for m in materials}
    if mode != 'item':
        raise ValueError(f"Unknown DECARB_A45 '{mode}'.")
    d = pd.read_csv(BF.OUT_A45_ITEM).set_index(['Material', 'Typology', 'Year'])['A45_kgCO2e_per_m2'].sort_index()
    out = {}
    for m in materials:
        out[m] = {}
        for t in typ_names:
            v = d.loc[(m, t)].reindex(years).values
            out[m][t] = v[0] - v
    return out


def load_decarb(mode, item_case, typ_names, materials, years):
    """A1-A3 reduction versus 2025 (kg CO2e/m2) by material and typology, one
    value per year in years (0 in 2025): {material: {typology: array}}, or None
    for mode 'none'. From Building_factors.py (factors_a13_decarb.csv)."""
    variant = BF.decarb_variant(mode, item_case)
    if variant is None:
        return None
    d = pd.read_csv(FILE_FACTORS_DECARB)
    d = d[d['Variant'] == variant].set_index(['Material', 'Typology', 'Year'])['A13_kgCO2e_per_m2'].sort_index()
    if d.empty:
        raise ValueError(f"{FILE_FACTORS_DECARB}: no rows for variant '{variant}' (run Building_factors.py).")
    out = {}
    for m in materials:
        out[m] = {}
        for t in typ_names:
            v = d.loc[(m, t)].reindex(years).values
            if np.isnan(v).any():
                raise ValueError(f'{FILE_FACTORS_DECARB}: missing years for {m} / {t}.')
            out[m][t] = v[0] - v                     # reduction versus 2025 (2025 = first year)
    return out


# ============================================================
# LOADERS
# ============================================================

def load_consents():
    """Monthly consents (data/derived/consents_monthly.csv) with a datetime 'Date' column; truncated at
    CONSENT_DATA_END when set (MODEL v4.0.0)."""
    df = pd.read_csv(FILE_CONSENTS_DERIVED)
    df['Date'] = pd.to_datetime(df['Date'])
    if CONSENT_DATA_END is not None:
        df = df[df['Date'] <= pd.Timestamp(CONSENT_DATA_END)].reset_index(drop=True)
    return df


def lagged_consents(df, lag_months, typ_cols, total_col):
    """MODEL v4.0.0: the monthly consents timed as completions, consents(m - L) booked in month m (the 'Date' shifted
    forward by L months), with 'Year' the completion year. The typology and retirement-village columns start in
    April 1990; months before their first observation that a lag reaches (L = 17: August 1989 - March 1990, all in
    1991 completions) are imputed from the all-category dwelling count (from 1965) x each column's ratio to it over
    the first 12 observed months (the composition of consents in April 1990 - March 1991, floor area per dwelling
    included). Returns (frame, info: imputed months and the imputed share of each affected completion year)."""
    out = df.copy()
    first = out.loc[out[typ_cols[0]].notna(), 'Date'].min()
    win = out[(out['Date'] >= first) & (out['Date'] < first + pd.DateOffset(months=12))]
    ratio = {c: float(win[c].sum() / win[total_col].sum()) for c in typ_cols}
    gap = out['Date'] < first
    for c in typ_cols:
        out.loc[gap, c] = out.loc[gap, total_col] * ratio[c]
    out['Date'] = out['Date'] + pd.DateOffset(months=int(lag_months))
    out['Year'] = out['Date'].dt.year
    out['_imputed'] = gap.values
    info = dict(lag_months=int(lag_months), first_typology_month=str(first.date()), composition_window=(
        str(first.date()), str((first + pd.DateOffset(months=11)).date())), ratio=ratio)
    share = {}
    model = out['_imputed'] & (out['Year'] >= 1991)                  # model years only (the history starts in 1991)
    for y, g in out[model].groupby('Year'):
        tot = out.loc[out['Year'] == y, total_col].sum()
        share[int(y)] = float(g[total_col].sum() / tot)
    info['imputed_months_by_completion_year'] = {int(y): [str((d - pd.DateOffset(months=int(lag_months))).date())
                                                           for d in g['Date']]
                                                 for y, g in out[model].groupby('Year')}
    info['imputed_share_of_completions'] = share
    return out.drop(columns='_imputed'), info


def pipeline_years(df, lag_months, first_year=2026):
    """MODEL v4.0.0: the projection years (from first_year, contiguous) whose 12 lagged months are all observed:
    December of the year minus L months is at or before the last observed consent month."""
    last = pd.Timestamp(df['Date'].max())
    out, y = [], first_year
    while pd.Timestamp(y, 12, 1) - pd.DateOffset(months=int(lag_months)) <= last and lag_months > 0:
        out.append(y)
        y += 1
    return out


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
    _scenario, _join_mode = REPLACEMENT_VARIANT, OVERBUILD_RULE
    if _join_mode not in ('market_excess', 'carried_deviation'):
        raise ValueError(f"Unknown OVERBUILD_RULE '{_join_mode}'.")

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
    T_BASELINE_2025 = {t: float(typ_fac.loc[t, 'total_with_SOC']) for t in typ_names}
    UPFRONT_2025 = {t: float(MAT_INTENSITY_STAGE.get(t, 0.0)) + SOIL_INTENSITY[t] for t in typ_names}

    # ------------------------------------------------------------------
    # 1. CONSENTS: floor area AND dwelling counts
    # ------------------------------------------------------------------
    df_consents = load_consents()
    df_consents['Year'] = pd.to_datetime(df_consents['Date']).dt.year
    # MODEL v4.0.0: consents timed as completions L months later (COMPLETION_LAG_MONTHS); every annual consent
    # series of the model is taken from this frame (L = 0: the calendar-year consents of MODEL v3.3, unchanged)
    lag_months = int(COMPLETION_LAG_MONTHS or 0)
    if lag_months and COMPLETION_LAG not in (0, 0.0):
        raise ValueError('COMPLETION_LAG_MONTHS and COMPLETION_LAG (two-point W) cannot be combined.')
    _lag_cols = (list(COL_TYPOLOGIES.values()) + list(COL_CONSENT_COUNTS.values()) + [COL_GFA]
                 + ([COL_RV_GFA] if COL_RV_GFA in df_consents.columns else []))
    df_lag, lag_info = lagged_consents(df_consents, lag_months, _lag_cols, COL_DWELLINGS_TOTAL)
    pipeline = pipeline_years(df_consents, lag_months)
    lag_info.update(pipeline_years=pipeline, consents_observed_to=str(df_consents['Date'].max().date()))
    if _join_mode == 'market_excess' and not pipeline and not (df_consents['Date'].dt.year >= 2026).any():
        _join_mode = 'carried_deviation'     # no observed projection year at all (validation.NO_2026_DATA, L = 0)

    hist_typ_gfa = df_lag.groupby('Year')[list(COL_TYPOLOGIES.values())].sum()
    hist_typ_gfa.columns = typ_names
    hist_typ_gfa = hist_typ_gfa.loc[1991:2025]

    hist_typ_units = df_lag.groupby('Year')[list(COL_CONSENT_COUNTS.values())].sum()
    hist_typ_units.columns = typ_names
    hist_typ_units = hist_typ_units.loc[1991:2025]

    hist_total_gfa = df_lag.groupby('Year')[COL_GFA].sum().loc[1991:2025]

    # ---- dwelling-count denominator: the three typologies ----------
    typ_sum = hist_typ_units.sum(axis=1)
    ext = df_lag.groupby('Year')[COL_DWELLINGS_TOTAL].sum().reindex(typ_sum.index)
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
    OLF_USED = dict(OLF_NET_BIM)

    blended_olf_bim = blend_per_gfa_share(hist_shares, OLF_NET_BIM, typ_names)
    blended_dwelling_size = hist_total_gfa / hist_total_units

    # Floor area per resident, MEASURED: realised dwelling size / actual occupancy.
    area_per_resident = blended_dwelling_size / hist_S

    blended_olf = blend_per_gfa_share(hist_shares, OLF_USED, typ_names)

    occupied_area_per_dwelling = hist_S * blended_olf
    # Utilisation is always measured against the BIM DESIGN benchmark: how much
    # floor area we build per resident, versus how much the design allows for.
    utilisation = blended_olf_bim / area_per_resident

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
    # MODEL v4.0.0: the lag of the census dwelling-count identity in years (continuous time, monthly resolution):
    # the two-point W (0 when the monthly lag is on) + L / 12; the annual series are already lagged (df_lag)
    lag_census = lag_w + lag_months / 12.0

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
    census_uc = (census['under_construction'] if CENSUS_UC_CORRECTION and lag_census == 0 else None)
    census_rates = engine.census_interval_rates(census['total_private'], consents_monthly, _completion, lag_census,
                                                uc=census_uc)

    # long-run residual beyond the BRANZ demolition rate (census dwelling counts)
    unconsented_rate = engine.census_window_rate(census_rates, *_nr_window) - demolition_rate
    v_forward = float(stock_cal['knots'][max(stock_cal['knots'])])   # vacancy-rate parameter: its published 2023 census value
    # MODEL v3.0.0 sensitivity: the long-run mean of the census vacancy on one definition (the pooled 2018/2023 empty
    # share of unoccupied private dwellings applied to every census, 1986-2023)
    _cs = float(census.loc[[2018, 2023], 'empty'].sum() / census.loc[[2018, 2023], 'unoccupied'].sum())
    vacancy_consistent = (census['unoccupied'] * _cs / census['total_private']).dropna()
    vacancy_consistent_mean = float(vacancy_consistent.mean())
    if VACANCY_PARAMETER == 'consistent_mean':
        v_forward = vacancy_consistent_mean
    elif VACANCY_PARAMETER != 'census_2023':
        raise ValueError(f"Unknown VACANCY_PARAMETER '{VACANCY_PARAMETER}'.")

    # 2025's departure from the calibrated identity, and its persistence. Carried
    # forward fading at rho, booked to the residual (see engine.forward).
    # net replacement path forward (REPLACEMENT_VARIANT); unconsented_rate stays the long-run value
    rate_recent = engine.census_window_rate(census_rates, *RECENT_INTERVAL)
    replacement_trend = engine.replacement_trend(census_rates, *_nr_window)   # MODEL v3.3.0 (Very High; reported)
    rate_path = engine.replacement_path(_scenario, demolition_rate + unconsented_rate, rate_recent,
                                        np.arange(2025, 2051), REPLACEMENT_HALF_LIFE, trend=replacement_trend)
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

    # ---- material decarbonisation of A1-A3 (DECARB_MODE) ----
    # T_INT / U_INT: whole-life and upfront intensity incl. soil, by typology; scalars
    # (2025 factors held) for 'none', arrays over forecast_years otherwise.
    if ACCOUNTING not in ('time_resolved', 'whole_life_at_construction'):
        raise ValueError(f"Unknown ACCOUNTING '{ACCOUNTING}'.")
    TIME_RESOLVED = ACCOUNTING == 'time_resolved'
    MAT_STAGE = {stg: (mat_scope[mat_scope['Stage'] == stg]
                       .pivot_table(index='Material', columns='Typology', values='kgCO2e_per_m2', aggfunc='sum')
                       .reindex(index=MATERIALS, columns=typ_names).fillna(0.0)) for stg in STAGES_IN_SCOPE}
    DECARB13 = load_decarb(DECARB_MODE, DECARB_ITEM_CASE, typ_names, MATERIALS, forecast_years)
    DECARB45 = load_decarb_a45(DECARB_A45, MAT_STAGE['A4-A5'], typ_names, MATERIALS, forecast_years)
    if DECARB13 is None and DECARB45 is None:
        DECARB = None
    else:
        _z = np.zeros(len(forecast_years))
        DECARB = {m: {t: (DECARB13[m][t] if DECARB13 else _z) + (DECARB45[m][t] if DECARB45 else _z)
                      for t in typ_names} for m in MATERIALS}
    RED13_TOT = {t: (sum(DECARB13[m][t] for m in MATERIALS) if DECARB13 else 0.0) for t in typ_names}
    RED45_TOT = {t: (sum(DECARB45[m][t] for m in MATERIALS) if DECARB45 else 0.0) for t in typ_names}
    # the construction-year intensity: whole life (v1-v2) or upfront only (time-resolved)
    BASE_INT = UPFRONT_2025 if TIME_RESOLVED else T_BASELINE_2025
    MAT_BASE = (MAT_STAGE['A1-A3'] + MAT_STAGE['A4-A5']) if TIME_RESOLVED else MAT_INTENSITY
    if DECARB is None:
        RED_TOT = None
        T_INT, U_INT = BASE_INT, UPFRONT_2025
    else:
        RED_TOT = {t: sum(DECARB[m][t] for m in MATERIALS) for t in typ_names}
        T_INT = {t: BASE_INT[t] - RED_TOT[t] for t in typ_names}
        U_INT = {t: UPFRONT_2025[t] - RED_TOT[t] for t in typ_names}

    def mat_int(m, t):
        """Material m's construction-year intensity for typology t (kg/m2; whole life, or
        A1-A5 only when time-resolved): scalar, or by year."""
        return MAT_BASE.loc[m, t] if DECARB is None else MAT_BASE.loc[m, t] - DECARB[m][t]

    # replacement and repaint events (time-resolved B2, B4): kernels by typology
    EVENTS, EVENTS_MAT, EV_PROFILE = None, None, None
    if TIME_RESOLVED:
        EV_PROFILE = EV.load_profile(EVENT_TIMING)
        EVENTS, EVENTS_MAT = {}, {}
        for t in typ_names:
            _p = EV_PROFILE[EV_PROFILE['Typology'] == t].reset_index(drop=True)
            _f = EV.row_factors(_p, forecast_years, DECARB_MODE, DECARB_ITEM_CASE, DECARB_A45)
            EVENTS[t] = EV.kernel(_p, forecast_years, _f)
            EVENTS_MAT[t] = EV.kernel(_p, forecast_years, _f, by_material=True)
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
    print("[check] population percentiles (published levels), 2048: "
          + " | ".join(f"{p} {df_forecast.loc[forecast_years == 2048, f'PopTotal_{p}'].iloc[0] / 1e6:.2f} M"
                       for p in ['5th', '50th', '95th']))

    # ------------------------------------------------------------------
    # 7. HOUSEHOLD PROJECTION
    # ------------------------------------------------------------------
    # household size: the Stats NZ shape, rebased on the census anchor year
    S_knots, _S_ann, _pref = statsnz_size_shape(HH_SIZE_VARIANT, forecast_years, tail=S_TAIL)
    S_matched = household_size(_S_ann, _pref, hist_S, hist_pop, forecast_years, 0.0,
                               anchor_year=S_ANCHOR_YEAR)['S_matched']
    # the same shape from the anchor year to 2025 (figures draw the projection from the anchor point)
    S_bridge = (float(hist_S.loc[S_ANCHOR_YEAR]) * _S_ann.loc[S_ANCHOR_YEAR:2025]
                / float(_S_ann.loc[S_ANCHOR_YEAR]))
    if HH_SIZE_PATH == 'census_pace':
        _p0, _p1 = HH_SIZE_PACE_WINDOW
        if _p1 != S_ANCHOR_YEAR:
            raise ValueError('HH_SIZE_PATH census_pace: the pace window must end at S_ANCHOR_YEAR.')
        _pace = float(hist_S.loc[_p1] - hist_S.loc[_p0]) / (_p1 - _p0)
        S_matched = float(hist_S.loc[S_ANCHOR_YEAR]) + _pace * (np.asarray(forecast_years, float) - S_ANCHOR_YEAR)
        S_bridge = pd.Series(float(hist_S.loc[S_ANCHOR_YEAR]) + _pace * (S_bridge.index.values - S_ANCHOR_YEAR),
                             index=S_bridge.index)
    elif HH_SIZE_PATH != 'statsnz':
        raise ValueError(f"Unknown HH_SIZE_PATH '{HH_SIZE_PATH}'.")
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
    print("   between censuses households follow lagged consents, so b measures supply vs "
          "arrivals, not behaviour")
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
    # typology shares: 2025 observed, 2026 the observed consented mix (below), then held at the
    # MIX_HELD_WINDOW average
    _typ_cols = [COL_TYPOLOGIES[n] for n in typ_names]
    _w = df_lag[(df_lag['Year'] >= MIX_HELD_WINDOW[0]) & (df_lag['Year'] <= MIX_HELD_WINDOW[1])]
    held_shares = (_w[_typ_cols].sum() / _w[_typ_cols].sum().sum()).set_axis(typ_names)
    evolving_gfa_shares = pd.DataFrame([shares_2025[list(typ_names)].values] * len(forecast_years),
                                       index=forecast_years, columns=list(typ_names))
    evolving_gfa_shares.loc[forecast_years > 2025, :] = held_shares.values
    # 2026 floor area from observed consented GFA by typology
    gfa_nowcast = None
    pipe = None                    # MODEL v4.0.0: observed (pipeline) years, their building and floor area
    if _join_mode == 'market_excess' and pipeline:
        _ly = df_lag.groupby('Year')
        _pa = _ly[COL_DWELLINGS_TOTAL].sum()
        _pg = _ly[[COL_TYPOLOGIES[n] for n in typ_names]].sum()
        pipe = dict(years=list(pipeline),
                    consents_all={y: float(_pa.loc[y]) for y in pipeline},                     # all categories
                    built_all={y: _completion * float(_pa.loc[y]) for y in pipeline},
                    gfa_by_typology={y: {n: _completion * float(_pg.loc[y, COL_TYPOLOGIES[n]]) for n in typ_names}
                                     for y in pipeline})
        pipe['gfa_total'] = {y: float(sum(pipe['gfa_by_typology'][y].values())) for y in pipeline}
        for y in pipeline:
            evolving_gfa_shares.loc[y, :] = [pipe['gfa_by_typology'][y][n] / pipe['gfa_total'][y] for n in typ_names]
        gfa_nowcast = dict(by_typology=pipe['gfa_by_typology'][pipeline[0]], total=pipe['gfa_total'][pipeline[0]],
                           consented_2026=None, pipeline=True)
    elif _join_mode == 'market_excess':
        _gm = df_consents.set_index(pd.to_datetime(df_consents['Date']))
        _g26 = {n: engine.nowcast_year(_gm[COL_TYPOLOGIES[n]].astype(float), 2026, NOWCAST_METHOD,
                                       NOWCAST_SEASONAL_YEARS)['total'] for n in typ_names}
        _built = {n: _completion * ((1.0 - lag_w) * _g26[n] + lag_w * float(hist_typ_gfa.loc[2025, n]))
                  for n in typ_names}
        gfa_nowcast = dict(by_typology=_built, total=float(sum(_built.values())), consented_2026=_g26)
        evolving_gfa_shares.loc[2026, :] = [_built[n] / gfa_nowcast['total'] for n in typ_names]
    # the observed floor area fixed in every run: the pipeline years (MODEL v4.0.0) or the 2026 nowcast
    gfa_fixed = ({y - 2025: pipe['gfa_total'][y] for y in pipe['years']} if pipe else
                 ({1: gfa_nowcast['total']} if gfa_nowcast else None))
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
                      intensity=T_INT, intensity_upfront=U_INT,
                      soil=SOIL_INTENSITY, soil_on_replacement=SOIL_ON_REPLACEMENT,
                      gfa_fixed=gfa_fixed, events=EVENTS)
    # NEAR-TERM MARKET EXCESS: 2026 building from observed consents (NOWCAST_METHOD)
    nowcast, join_info = None, {}
    if _join_mode == 'market_excess' and not pipe:
        nowcast = engine.nowcast_year(consents_monthly, 2026, NOWCAST_METHOD, NOWCAST_SEASONAL_YEARS)
    engine_out = {}
    for col in ['5th', '50th', '95th']:
        pop_total = df_forecast[f'PopTotal_{col}'].values
        pop_growth = df_forecast[f'PopGrowth_{col}'].clip(lower=0).values
        hh_arr = households_forecast[col]
        E = engine.forward(pop_total, hh_arr, pop_growth, **fwd_inputs)
        if _join_mode == 'market_excess':
            _b26 = ([pipe['built_all'][y] for y in pipe['years']] if pipe else
                    _completion * ((1.0 - lag_w) * float(nowcast['total']) + lag_w * float(hist_units_all.loc[2025])))
            _aw = (None if OVERBUILD_ABSORPTION_END is None or OVERBUILD_BOOKING != 'surplus' else
                   engine.logistic_weights(forecast_years, OVERBUILD_ABSORPTION_START, OVERBUILD_ABSORPTION_END))
            join, ji = engine.market_excess(E, _b26, rho_other, OVERBUILD_GAP_REF, OVERBUILD_BOOKING,
                                            OVERBUILD_ABSORPTION, absorb_w=_aw)
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
        # MODEL v3.0.0: the join = market excess - overbuild absorbed (payback, <= 0); two bands
        _pay = np.asarray(join_info[col]['payback'], float) if col in join_info else np.zeros(len(_D))
        join_gfa = (E['join'] - _pay) * _D + E['gfa_adj']   # 2026 overbuild (market excess), m2; 2026 = observed GFA
        absorbed_gfa = _pay * _D                   # overbuild absorbed (payback), m2 (<= 0)
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
        absorbed_gfa[0] = 0.0
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
                            join=join_gfa, absorbed=absorbed_gfa,
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
        df_forecast[f'Ann_GFA_Cons_Absorbed_{col}'] = absorbed_gfa

    # ---- retirement-village floor area: reported, out of scope (A4) ----
    rv_floor_area, rv_size_ref = None, float('nan')
    if COL_RV_GFA in df_consents.columns:
        _rvg = df_lag.groupby('Year')[COL_RV_GFA].sum().loc[1991:2025]
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

    print(f"\n[replacement] variant {_scenario}"
          + (f" (half-life {REPLACEMENT_HALF_LIFE:g} yr)" if _scenario == 'REF' else '')
          + f": net replacement {100 * rate_path[1]:.3f}%/yr in 2026, {100 * rate_path[-1]:.3f}%/yr in 2050 "
          f"(long run {100 * (demolition_rate + unconsented_rate):.3f}%, "
          f"{RECENT_INTERVAL[0]}-{RECENT_INTERVAL[1]} {100 * rate_recent:.3f}%)")
    if _join_mode == 'market_excess':
        ji = join_info['50th']
        _src = (f"pipeline {pipe['years']} (consents lagged {lag_months} months)" if pipe else NOWCAST_METHOD)
        print(f"[near-term market excess] observed building {[round(x) for x in ji['O_obs']]} ({_completion:g} x "
              f"consents, {_src}) vs requirement {[round(x) for x in ji['R_obs']]} -> excess "
              f"{[round(x) for x in ji['e_obs']]}; gap_ref ({OVERBUILD_GAP_REF}) "
              f"{ji['gap_ref']:+,.0f}, rho {ji['rho']:.2f}; {OVERBUILD_BOOKING}: "
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
    evol_typ_absorbed = split_typ(df_forecast['Ann_GFA_Cons_Absorbed_50th'].values)   # 0 in 2025, 2026
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
                    - df_forecast['Ann_GFA_Cons_Join_50th'].iloc[1]
                    - df_forecast['Ann_GFA_Cons_Absorbed_50th'].iloc[1]) or 1.0
        for _ev, _c in ((evol_typ_vac, 'Vacancy'), (evol_typ_repl, 'Replacement'),
                        (evol_typ_unc, 'Unconsented'), (evol_typ_wave, 'Wave'), (evol_typ_rv, 'RV')):
            _ev.loc[2025, n] = (evol_typ_other.loc[2025, n]
                                * float(df_forecast[f'Ann_GFA_Cons_{_c}_50th'].iloc[1]) / _o1)

    # Materials plus soil: constant at 2025 (DECARB_MODE 'none') or with A1-A3 decarbonised by year.
    intensity = pd.DataFrame({n: (np.full(len(forecast_years), BASE_INT[n]) if DECARB is None
                                  else T_INT[n]) for n in typ_names}, index=forecast_years)

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
    carbon_absorbed_typ = band_carbon(evol_typ_absorbed, f_join)   # building avoided: as soil-bearing as the excess
    carbon_other_typ = (carbon_vac_typ + carbon_repl_typ + carbon_unc_typ + carbon_wave_typ + carbon_rv_typ
                        + carbon_join_typ + carbon_absorbed_typ)
    carbon_cons_typ = carbon_extra_typ + carbon_other_typ
    soil_fracs = {'Growth (net of consolidation)': f_new, 'House-splitting': f_new,
                  'Consumption: extra space': f_new, 'Consumption: vacancy': f_new,
                  'Consumption: demolition': f_repl, 'Calibrated stock residual': f_repl,
                  'Redevelopment wave': f_repl,
                  'Housed in RV units (out of scope)': f_rv, 'Near-term market excess': f_join,
                  'Overbuild absorbed': f_join}
    # replacements and repaints within the window (time-resolved; zero otherwise)
    carbon_bev_typ = pd.DataFrame(engine_out['50th']['b_t'].T, index=forecast_years, columns=typ_names)
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
          f"  -> vacancy-rate parameter held at its published 2023 census value, {100*v_forward:.2f}%")
    print("   build duration W, Little's law (under construction / all consents in the 12 months to March): " +
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
    print("\n   RETIREMENT VILLAGES (counted in the stock; out of floor-area and carbon scope)")
    print("     consented RV units = all-category dwellings - three typologies")
    for a_, b_ in [(1992, 2005), (2006, 2015), (2016, 2025)]:
        print(f"     {a_}-{b_}: {hist_rv_units.loc[a_:b_].mean():6,.0f} consented/yr "
              f"({100 * hist_rv_share.loc[a_:b_].mean():.1f}% of all new dwellings)")
    print(f"     forward share of all dwellings built: {100 * rv_share:.2f}% "
          f"(ratio of sums {RV_SHARE_REF[0]}-{RV_SHARE_REF[1]}; annual range since 2011 "
          f"{100 * hist_rv_share.loc[2011:].min():.1f}-{100 * hist_rv_share.loc[2011:].max():.1f}%)")
    _sf = stock_fwd['50th']
    _nb = (results['50th']['total'][1:] / future_dwelling_size.values[1:]).mean()
    print("\n   Forward 2026-2050, median, dwellings per year:")
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

    # ==================================================================
    # DASHBOARD
    # ==================================================================
    # console summary (totals; the typology mix is internal and not reported)
    tot_built = float(evol_typ_total.iloc[1:].sum().sum() / 1e6)
    tot_avoided_gfa = df_forecast['Ann_GFA_HouseSplit_Avoided_50th'].iloc[1:].sum() / 1e6
    tot_avoided_c = carbon_avoided_typ.iloc[1:].sum().sum() / 1e6
    print("\n" + "=" * 80)
    print(" PROJECTION SUMMARY 2026-2050 (median population)")
    print("=" * 80)
    print(f"   floor area {tot_built:.2f} Mm2 | carbon {carbon_total_typ.iloc[1:].sum().sum() / 1e6:,.1f} kt CO2e")
    print(f"   smaller households avoided by consolidation (not built): {tot_avoided_gfa:.2f} Mm2, "
          f"{tot_avoided_c:,.0f} kt CO2e ({100 * tot_avoided_gfa / tot_built:.1f}% of the floor area built)")
    # ---- by demand band (definition with retirement villages; naming.BANDS_WITH_RETIREMENT_VILLAGES) ----
    _src = dict(growth=(evol_typ_growth, carbon_growth_typ), hs_pos=(evol_typ_hs_pos, carbon_hs_pos_typ),
                extra=(evol_typ_extra, carbon_extra_typ), vac=(evol_typ_vac, carbon_vac_typ),
                repl=(evol_typ_repl, carbon_repl_typ), unc=(evol_typ_unc, carbon_unc_typ),
                wave=(evol_typ_wave, carbon_wave_typ), join=(evol_typ_join, carbon_join_typ),
                absorbed=(evol_typ_absorbed, carbon_absorbed_typ), rv=(evol_typ_rv, carbon_rv_typ))
    rows = [(N.band_data_label(b), _src[k][0].iloc[1:].sum().sum() / 1e6, _src[k][1].iloc[1:].sum().sum() / 1e6)
            for b, k in zip(N.BANDS_WITH_RETIREMENT_VILLAGES, _src)]
    tg = sum(r[1] for r in rows)
    tc = sum(r[2] for r in rows)
    print("\n BY DEMAND BAND, 2026-2050 (median)")
    print(f"   {'':<58}{'floor area':>12}{'share':>8}{'carbon':>12}")
    print(f"   {'':<58}{'(Mm2)':>12}{'':>8}{'(kt CO2e)':>12}")
    for lab, g, c in rows:
        print(f"   {lab:<58}{g:>12.2f}{100 * g / tg:>7.1f}%{c:>12,.0f}")
    print(f"   {'Total built':<58}{tg:>12.2f}{100.0:>7.1f}%{tc:>12,.0f}")
    print(f"   {f'(consented equivalent, /{COMPLETION_RATE:.2f})':<58}{tg / COMPLETION_RATE:>12.2f}")
    print("=" * 80 + "\n")

    # Demand bands (annual, 2026-2050; Fig1, Fig2, the band exports, D25/D26): bands.in_scope, the same band
    # accounting as every pathway run (MODEL v3.2.0, release accounting A2 from v3.1.0: gross positive bands, release
    # bands, retirement villages removed by their exact share, no rescaling, maintenance a carbon-only band);
    # [(label, values, band id)]; the bands add up to the typology total every year (bands.check, 1e-9).
    _ji50 = join_info.get('50th')
    _exc50 = (np.asarray(_ji50['excess'], float) if _ji50 is not None and _ji50.get('mode') == 'surplus'
              else np.asarray(_E50['join'], float))
    _paid50 = (-np.asarray(_ji50['payback'], float) if _ji50 is not None and _ji50.get('mode') == 'surplus'
               else np.zeros(len(forecast_years)))
    _gross50 = engine.requirement(_E50)
    if np.any(_gross50[2:] < -1e-9):
        raise SystemExit('projection: negative gross building in the Reference (no carry-forward rule here).')
    band_set = BANDS.in_scope(_E50, fwd_inputs, _exc50, _paid50, BANDS.no_flows(len(forecast_years)),
                              float(unconsented_rate), typ_names)
    fig_bands = {
        'gfa': ([(N.band_data_label(b), band_set[b][0][1:] / 1e6, b) for b in BANDS.IN_SCOPE],
                evol_typ_total.sum(axis=1).values[1:] / 1e6),
        'carbon': ([(N.band_data_label(b), band_set[b][1][1:] / 1e6, b) for b in BANDS.IN_SCOPE],
                   carbon_total_typ.sum(axis=1).values[1:] / 1e6)}

    # ==================================================================
    # MATERIAL FLOW ACCOUNTING  (median variant, 2026-2050)
    # ==================================================================
    # Annual floor area by typology x the case-study intensity of each material
    # and of soil. Soil is kept separate throughout: it is land-use change, not
    # a material, and nothing that acts on materials should act on it.
    plot_years = forecast_years[1:]
    flow_annual = pd.DataFrame(
        {m: sum(evol_typ_total[t].values * mat_int(m, t) for t in typ_names)
         for m in MATERIALS}, index=forecast_years)
    # in-window replacements and repaints by material (time-resolved; zero otherwise)
    flow_annual_b = pd.DataFrame(
        {m: (sum(evol_typ_total[t].values @ EVENTS_MAT[t][m] for t in typ_names if m in EVENTS_MAT[t])
             if EVENTS_MAT else 0.0) for m in MATERIALS}, index=forecast_years).astype(float)
    flow_annual = flow_annual + flow_annual_b
    flow_annual['SOIL'] = sum(evol_typ_total[t].values * SOIL_INTENSITY[t] * soil_frac
                              for t in typ_names)
    flow_annual = flow_annual.loc[plot_years]              # drop the 2025 anchor
    flow_annual_b = flow_annual_b.loc[plot_years]
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
                    'Near-term market excess': evol_typ_join,
                    'Overbuild absorbed': evol_typ_absorbed}
    dem_mat = pd.DataFrame(
        {lab: [sum((df[t].iloc[1:].sum() * MAT_BASE.loc[m, t]) if DECARB is None
                   else wsum(df[t].values, mat_int(m, t)) for t in typ_names)
               for m in MATERIALS] + [sum((df[t].values * soil_fracs[lab])[1:].sum() * SOIL_INTENSITY[t]
                                          for t in typ_names)]
         for lab, df in demand_bands.items()}, index=MATERIALS + ['SOIL'])
    if TIME_RESOLVED:
        dem_mat[N.band_data_label('maintenance')] = list(flow_annual_b.sum().reindex(MATERIALS).values) + [0.0]

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
    # by stage and typology: 2025 factor, or by year (A1-A3 decarbonised; DECARB_MODE)
    # (A1-A3 and A4-A5 decarbonised; DECARB_MODE, DECARB_A45). Time-resolved: B2,B4 and
    # C1-C4 are not booked at construction (B2,B4 in-window events are added below)
    _red = {'A1-A3': RED13_TOT, 'A4-A5': RED45_TOT}
    stage_path = {stg: {t: (0.0 if (TIME_RESOLVED and stg in ('B2,B4', 'C1-C4')) else
                            stage_int.loc[stg, t] if (DECARB is None or stg not in _red)
                            else stage_int.loc[stg, t] - _red[stg][t]) for t in typ_names}
                  for stg in STAGES_IN_SCOPE}
    _soil = sum((evol_typ_total[t].values * soil_frac)[1:].sum() * SOIL_INTENSITY[t] for t in typ_names)
    print("\n BY LIFE-CYCLE STAGE  [kt CO2e, 2026-2050]  (soil = land-use change at construction)")
    _st_tot = 0.0
    _b_inwin = float(carbon_bev_typ.iloc[1:].sum().sum())
    for stg in STAGES_IN_SCOPE:
        v = sum(wsum(evol_typ_total[t].values, stage_path[stg][t]) for t in typ_names) / 1e6
        if stg == 'B2,B4' and TIME_RESOLVED:
            v = _b_inwin / 1e6
        _st_tot += v
        print(f"   {stg:<10}{v:>10,.0f}")
    print(f"   {'SOIL':<10}{_soil / 1e6:>10,.0f}")
    _upfront = (sum(evol_typ_total[t].values[1:].sum() * stage_int.loc[['A1-A3', 'A4-A5'], t].sum()
                    for t in typ_names) / 1e6 if DECARB is None else
                sum(wsum(evol_typ_total[t].values, stage_path['A1-A3'][t] + stage_path['A4-A5'][t])
                    for t in typ_names) / 1e6)
    print(f"   upfront (A1-A5 + soil) {_upfront + _soil / 1e6:,.0f} kt | "
          f"later stages (B2,B4, C1-C4) {_st_tot - _upfront:,.0f} kt | "
          f"[check] sum {_st_tot + _soil / 1e6:,.0f} vs {tot_carbon_median:,.0f}")

    # committed after 2050 (time-resolved): the 2026-2050 cohorts' later replacements and
    # repaints, and all their end of life (C1-C4, held at 2025). Range: upper = 2025
    # factors throughout; lower = 2050 factors held after 2050 (no extrapolation).
    COMMITTED = None
    if TIME_RESOLVED:
        _after = np.arange(forecast_years[-1] + 1, forecast_years[-1] + int(EV_PROFILE['Age'].max()) + 1)
        _b = {'upper': 0.0, 'lower': 0.0}
        for t in typ_names:
            _p = EV_PROFILE[EV_PROFILE['Typology'] == t].reset_index(drop=True)
            for k, hold in (('upper', '2025'), ('lower', '2050')):
                _f = EV.row_factors(_p, _after, DECARB_MODE, DECARB_ITEM_CASE, DECARB_A45, hold=hold)
                _b[k] += EV.committed(evol_typ_total[t].values, forecast_years, _p, _f)
        _c = sum(evol_typ_total[t].values[1:].sum() * stage_int.loc['C1-C4', t] for t in typ_names)
        COMMITTED = dict(B_upper_kt=_b['upper'] / 1e6, B_lower_kt=_b['lower'] / 1e6, C_kt=_c / 1e6,
                         upper_kt=(_b['upper'] + _c) / 1e6, lower_kt=(_b['lower'] + _c) / 1e6,
                         B_inwindow_kt=_b_inwin / 1e6)
        print(f"   in-window replacements & repaints {_b_inwin / 1e6:,.0f} kt | committed after 2050: "
              f"B {_b['lower'] / 1e6:,.0f}-{_b['upper'] / 1e6:,.0f} kt + C1-C4 {_c / 1e6:,.0f} kt (2025 factors)")

    print("\n BY DEMAND TYPE AND MATERIAL  [kt CO2e, 2026-2050]")
    dm = (dem_mat / 1e6).round(1)
    dm['TOTAL'] = dm.sum(axis=1)
    dm = dm.sort_values('TOTAL', ascending=False)
    dm.loc['TOTAL'] = dm.sum()
    print(dm.to_string())

    # Every intermediate result is returned, so Diagnostics.py and
    # Sensitivity.py read the same run instead of re-deriving anything; the figure source is
    # written from it (export_figure_sources(), script run only), never from inside the computation.
    state = dict(locals())
    return state


def wsum(values, k):
    """Sum over 2026-2050 (index 1 on) of values x k, where k is one factor
    (constant: the original expression, unchanged to the last bit) or one factor
    per year (decarbonised materials)."""
    if np.ndim(k) == 0:
        return values[1:].sum() * k
    return (np.asarray(values)[1:] * np.asarray(k)[1:]).sum()


def export_results(B, path):
    """Write the central run's report tables to JSON (read by tools/baseline_draft.py;
    every number in the draft report comes from here or another generated file)."""
    import json
    f = slice(1, None)
    tot = lambda df: float(df.iloc[f].sum().sum())
    # demand bands, definition 'with_retirement_villages' (naming.BANDS_WITH_RETIREMENT_VILLAGES)
    keys = ('growth', 'hs_pos', 'extra', 'vac', 'repl', 'unc', 'wave', 'join', 'absorbed', 'rv')
    bands = [(N.band_data_label(b), f'evol_typ_{k}', f'carbon_{k}_typ')
             for b, k in zip(N.BANDS_WITH_RETIREMENT_VILLAGES, keys)]
    typ = list(B['typ_names'])
    et, ct = B['evol_typ_total'], B['carbon_total_typ']
    stages = {s: float(sum(wsum(et[t].values, B['stage_path'][s][t]) for t in typ) / 1e6)
              for s in B['stage_int'].index}
    R = B['results']
    out = dict(
        settings=dict(scenario=B['_scenario'], replacement_half_life=REPLACEMENT_HALF_LIFE, overbuild_rule=B['_join_mode'],
                      nowcast_method=NOWCAST_METHOD, overbuild_booking=OVERBUILD_BOOKING,
                      completion_rate=COMPLETION_RATE, lag_w=float(B['lag_w'])),
        gfa_Mm2=float(R['50th']['total'][f].sum() / 1e6), carbon_kt=float(B['tot_carbon_median']),
        upfront_kt=float(B['_upfront'] + B['_soil'] / 1e6), soil_kt=float(B['_soil'] / 1e6),
        stages_kt=stages,
        pop_band_gfa_Mm2={p: float(R[p]['total'][f].sum() / 1e6) for p in ('5th', '50th', '95th')},
        demand_bands=[dict(band=lab, gfa_Mm2=tot(B[g]) / 1e6, carbon_kt=tot(B[c]) / 1e6)
                      for lab, g, c in bands],
        material_kt={m: float(v / 1e6) for m, v in B['flow_annual'].sum().items()},
        replacement_trend=dict(B['replacement_trend'], window=list(B['_nr_window']),
                               rate_2026=float(B['replacement_trend']['a'] + B['replacement_trend']['b'] * 2026),
                               rate_2050=float(B['replacement_trend']['a'] + B['replacement_trend']['b'] * 2050),
                               method='weighted least squares of the census-interval net replacement rates on the mean '
                                      'of each interval\'s model years (y0+1 .. y1), weights = interval length; '
                                      'Very High replacement = a + b year (MODEL v3.3.0)'),
        bands_in_scope=[dict(band=lab, gfa_Mm2=float(np.sum(gv)), carbon_kt=float(np.sum(cv)))
                        for (lab, gv, _), (_, cv, _) in zip(B['fig_bands']['gfa'][0], B['fig_bands']['carbon'][0])],
        accounting=ACCOUNTING, decarb_a45=DECARB_A45, event_timing=EVENT_TIMING,
        **({'b_inwindow_kt': B['COMMITTED']['B_inwindow_kt'], 'committed': B['COMMITTED']}
           if B['COMMITTED'] else {}),
        annual=dict(years=[int(y) for y in B['forecast_years']],
                    gfa_Mm2=[float(v / 1e6) for v in R['50th']['total']],
                    carbon_kt=[float(v / 1e6) for v in ct.sum(axis=1).values]),
        S_2050=float(B['df_forecast']['PopTotal_50th'].values[-1] / B['households_forecast']['50th'][-1]))
    with open(path, 'w') as fh:
        json.dump(N.keys(out), fh, indent=2)


def export_annual(B, path_annual, path_bands):
    """Annual series of the Reference (MODEL v1.0.0 additions; release names of naming.py).

    path_annual: one row per year, history (in-scope floor area built, 1991-2025) and the
    Reference (2026-2050; 2025 is the observed anchor): floor area and embodied carbon, the
    carbon split into materials and construction (A1-A5, excluding soil), soil carbon loss and
    maintenance (B2, B4 within 2026-2050). The three components add up to the annual carbon
    of the engine (carbon = upfront + maintenance; upfront = materials and construction + soil
    carbon loss, the soil term computed exactly as the engine applies it: soil factor x floor
    area x soil-bearing share). No historical carbon (the model has no historical factors).

    path_bands: the in-scope demand bands of the Reference by year 2026-2050 (floor area and
    carbon; retirement villages removed from every band in proportion, maintenance a carbon band),
    the bands of the projection figures (fig_bands) under the labels of naming.BANDS_IN_SCOPE."""
    E = B['engine_out']['50th']
    fy = np.asarray(B['forecast_years'])
    typ = list(B['typ_names'])
    soil = (np.array([B['SOIL_INTENSITY'][t] for t in typ])[:, None] * E['gfa_t']).sum(axis=0) * E['soil_share']
    maint = E['b_t'].sum(axis=0)
    if not np.allclose(E['upfront'] + maint, E['carbon'], rtol=1e-12, atol=0):
        raise SystemExit('export_annual: upfront + maintenance does not reproduce the annual carbon.')
    if not np.allclose(E['carbon'][1:], B['carbon_total_typ'].sum(axis=1).values[1:], rtol=1e-12, atol=0):
        raise SystemExit('export_annual: engine carbon differs from the reported annual carbon.')
    hist = B['hist_built_gfa']
    rows = [dict(year=int(y), source='history', floor_area_Mm2=float(v) / 1e6) for y, v in hist.items() if y <= fy[0]]
    for i, y in enumerate(fy):
        if i == 0:
            continue                                   # 2025: the observed anchor (history row)
        rows.append(dict(year=int(y), source='projection', floor_area_Mm2=float(B['results']['50th']['total'][i]) / 1e6,
                         carbon_kt=float(E['carbon'][i]) / 1e6,
                         materials_construction_kt=float(E['upfront'][i] - soil[i]) / 1e6,
                         soil_carbon_loss_kt=float(soil[i]) / 1e6, maintenance_kt=float(maint[i]) / 1e6))
    N.columns(pd.DataFrame(rows)).to_csv(path_annual, index=False)
    (g_bands, _), (c_bands, _) = B['fig_bands']['gfa'], B['fig_bands']['carbon']
    if len(g_bands) != len(N.BANDS_IN_SCOPE) or len(c_bands) != len(N.BANDS_IN_SCOPE):
        raise SystemExit('export_annual: the projection bands do not match naming.BANDS_IN_SCOPE.')
    out = [dict(year=int(y), band=N.band_data_label(b), floor_area_Mm2=float(g[i]), carbon_kt=float(c[i]))
           for i, y in enumerate(fy[1:])
           for b, (_, g, _), (_, c, _) in zip(N.BANDS_IN_SCOPE, g_bands, c_bands)]
    pd.DataFrame(out).to_csv(path_bands, index=False)


def export_absorption_log(B, path):
    """MODEL v3.0.0: the overbuild absorption of the Reference by year (median population path; engine.absorb_overbuild):
    market excess, cumulative excess C, absorption weight w, target surplus U* = C (1 - w), target payback, the
    year's building before the payback (gross), the payback paid (capped at max(gross, 0)), the carried shortfall,
    the surplus still vacant U, dwellings built, and the implied vacancy 1 - hh / (stock + U) against the vacancy
    parameter. Written whatever the absorption setting (never absorbed: w = 0, payback 0)."""
    ji = B['join_info']['50th']
    E = B['engine_out']['50th']
    fy = np.asarray(B['forecast_years'])
    n = len(fy)
    ab = ji.get('absorption')
    if ab is None:                                     # MODEL v2.1 rule (constant share; never absorbed by default)
        C = np.cumsum(ji['excess'])
        ab = dict(excess=ji['excess'], C=C, w=np.zeros(n), U_target=np.asarray(ji['surplus'], float),
                  payback_target=-np.asarray(ji['payback'], float), need=engine.requirement(E) - E['join'],
                  gross=engine.requirement(E) - E['join'] + ji['excess'], paid=-np.asarray(ji['payback'], float),
                  carry=np.zeros(n), cap_binds=np.zeros(n, bool), U=np.asarray(ji['surplus'], float))
        ab['built'] = ab['gross'] - ab['paid']
    stock = np.asarray(E['stock'], float)
    v_par = np.broadcast_to(np.asarray(E['v'], float), (n,))
    rows = []
    for i, y in enumerate(fy):
        rows.append(dict(year=int(y), excess_dwellings=float(ab['excess'][i]), cumulative_excess=float(ab['C'][i]),
                         absorption_weight=float(ab['w'][i]), surplus_target=float(ab['U_target'][i]),
                         payback_target=float(ab['payback_target'][i]), building_before_payback=float(ab['gross'][i]),
                         payback_paid=float(ab['paid'][i]), payback_carried=float(ab['carry'][i]),
                         cap_binds=bool(ab['cap_binds'][i]), surplus_vacant=float(ab['U'][i]),
                         dwellings_built=float(engine.requirement(E)[i]),
                         implied_vacancy=float(1.0 - E['hh'][i] / (stock[i] + E['stock_join'][i])),
                         vacancy_parameter=float(v_par[i])))
    df = pd.DataFrame(rows)
    if not np.allclose(df['surplus_vacant'].values, np.asarray(E['stock_join'], float), rtol=1e-12, atol=1e-6):
        raise SystemExit('export_absorption_log: the surplus U differs from the engine stock_join.')
    df.to_csv(path, index=False)
    return df


def export_stage_material(B, path_stage, path_material):
    """Annual carbon of the Reference 2026-2050 by life-cycle stage and by material (MODEL v2.0.0
    additions, Fig3). No new computation: the stage split is the one main() prints (floor area by
    typology x the stage factor path of each typology), the material split is flow_annual (D13);
    both are checked against the engine's annual carbon (export_annual), so the parts add up to
    the totals of data/baseline/annual.csv.

    path_stage: year, A1-A3, A4-A5 (decarbonised factor paths), maintenance (B2, B4 in-window
    events) and soil carbon loss (kt). path_material: year, material (the six material groups and
    soil carbon loss), carbon (kt); each material includes its in-window maintenance."""
    if not B['TIME_RESOLVED']:
        raise SystemExit('export_stage_material: written for the time-resolved accounting.')
    E = B['engine_out']['50th']
    fy = np.asarray(B['forecast_years'])
    typ = list(B['typ_names'])
    ev, sp = B['evol_typ_total'], B['stage_path']

    def stage(stg):
        out = np.zeros(len(fy))
        for t in typ:
            k = sp[stg][t]
            out += np.asarray(ev[t].values, float) * (np.asarray(k, float) if np.ndim(k) else float(k))
        return out

    a13, a45 = stage('A1-A3'), stage('A4-A5')
    soil = (np.array([B['SOIL_INTENSITY'][t] for t in typ])[:, None] * E['gfa_t']).sum(axis=0) * E['soil_share']
    maint = E['b_t'].sum(axis=0)
    if not np.allclose((a13 + a45 + soil)[1:], E['upfront'][1:], rtol=1e-9, atol=0):
        raise SystemExit('export_stage_material: A1-A3 + A4-A5 + soil does not reproduce the upfront carbon.')
    rows = [dict(year=int(y), a1a3_kt=a13[i] / 1e6, a4a5_kt=a45[i] / 1e6, maintenance_kt=maint[i] / 1e6,
                 soil_carbon_loss_kt=soil[i] / 1e6, carbon_kt=float(E['carbon'][i]) / 1e6)
            for i, y in enumerate(fy) if i > 0]
    pd.DataFrame(rows).to_csv(path_stage, index=False)
    fa = B['flow_annual']
    if not np.allclose(fa.sum(axis=1).values, np.asarray(E['carbon'], float)[1:], rtol=1e-9, atol=0):
        raise SystemExit('export_stage_material: the materials do not add up to the annual carbon.')
    pd.DataFrame([dict(year=int(y), material=m, carbon_kt=float(fa.loc[y, m]) / 1e6)
                  for y in fa.index for m in fa.columns]).to_csv(path_material, index=False)


def export_figure_sources(B):
    """MODEL v3.0.0 compute / draw separation: write the exact arrays of D01-D03, D08, D09 and D13 (drawn by
    figures/calibration.py) and of the Extended Data paths (projection_paths, ED3) as figure source JSON
    (figsource.write, outputs/data/figure_source/<id>.json). Units are the model's (persons, households, m2,
    kg CO2e); the figures only rescale for display. Called by the script run only (main() writes nothing)."""
    yh, fy = np.asarray(B['years_hist'], int), np.asarray(B['forecast_years'], int)
    df = B['df_forecast']
    hf = {p: np.asarray(B['households_forecast'][p], float) for p in ('5th', '50th', '95th')}
    pop = {p: df[f'PopTotal_{p}'].to_numpy(float) for p in ('5th', '50th', '95th')}
    sb = B['S_bridge']
    yb = np.r_[sb.index.values.astype(int), fy[1:]]               # the projection drawn from the anchor census point
    common = dict(years_hist=yh, forecast_years=fy, S_ANCHOR_YEAR=int(S_ANCHOR_YEAR),
                  hh_rebase_k=float(B['hh_rebase_k']))
    figsource.write('D01_population', years_hist=yh, forecast_years=fy, population_hist=B['hist_pop'],
                    population_5th=pop['5th'], population_50th=pop['50th'], population_95th=pop['95th'])
    figsource.write('D02_households', **common, households_hist=B['hist_hh'],
                    households_dhe_published=B['hist_hh_dhe'].loc[2018:],
                    households_5th=hf['5th'], households_50th=hf['50th'], households_95th=hf['95th'],
                    projection_years=yb,
                    projection_households=np.r_[(B['hist_pop'].loc[sb.index] / sb).values, hf['50th'][1:]])
    figsource.write('D03_household_size', **common, household_size_hist=B['hist_S'], projection_years=yb,
                    projection_household_size=np.r_[sb.values, (pop['50th'] / hf['50th'])[1:]],
                    population_growth_hist=B['d_pop'], household_formation_hist=B['d_hh'],
                    population_growth_50th=df['PopGrowth_50th'].to_numpy(float),
                    household_formation_50th=np.r_[np.nan, np.diff(hf['50th'])])
    figsource.write('D08_dwelling_space', years_hist=yh, realised_dwelling_size=B['blended_dwelling_size'],
                    occupied_area_per_dwelling=B['occupied_area_per_dwelling'], utilisation=B['utilisation'])
    figsource.write('D09_cumulative_floor_area', years_hist=yh, forecast_years=fy, cumulative_floor_area_hist=B['hist_cum'],
                    built_factor=float(B['built_factor']), lag_w=float(B['lag_w']),
                    cumulative_floor_area_5th=df['Cum_GFA_Total_5th'].to_numpy(float),
                    cumulative_floor_area_50th=df['Cum_GFA_Total_50th'].to_numpy(float),
                    cumulative_floor_area_95th=df['Cum_GFA_Total_95th'].to_numpy(float),
                    projection_years=df['Year'].to_numpy(int))
    figsource.write('D13_carbon_by_material', years=fy[1:], carbon_annual=B['flow_annual'],
                    carbon_cumulative=B['flow_cum'], time_resolved=bool(B['TIME_RESOLVED']), unit='kg CO2e')
    num = {c: df[c].to_numpy() for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    figsource.write('projection_paths', years_hist=yh, forecast_years=fy, S_ANCHOR_YEAR=int(S_ANCHOR_YEAR),
                    population_hist=B['hist_pop'], households_hist=B['hist_hh'], household_size_hist=B['hist_S'],
                    floor_area_built_hist=B['hist_built_gfa'], cumulative_floor_area_hist=B['hist_cum'],
                    households_5th=hf['5th'], households_50th=hf['50th'], households_95th=hf['95th'],
                    df_forecast=num,
                    units=dict(population='persons', households='households', household_size='persons per household',
                               floor_area='m2 (floor area built per year; cumulative from 1991)'))


if __name__ == "__main__":
    _B = main()
    export_results(_B, layout.writing(layout.data('baseline/projection.json')))
    if not FROZEN_RUN:                 # the frozen check run (whole life at construction) is an anchor only
        export_annual(_B, layout.writing(layout.data('baseline/annual.csv')),
                      layout.writing(layout.data('baseline/bands_annual.csv')))
        export_stage_material(_B, layout.writing(layout.data('baseline/annual_by_stage.csv')),
                              layout.writing(layout.data('baseline/annual_by_material.csv')))
        export_absorption_log(_B, layout.writing(layout.data('baseline/overbuild_absorption_log.csv')))
        export_figure_sources(_B)
