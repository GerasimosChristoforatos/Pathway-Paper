"""
LEVERS: pure functions, lever level -> modified engine.forward inputs (ten rule-based levers)
=============================================================================================================
Each lever changes one or two inputs of engine.forward (the `fwd_inputs` dict built in projection.main(), and the
households path; LEVER_PARAMETER) and nothing else. No function reads module globals of projection, no file is
written and no argument is modified: every function returns new objects (or, for a lever that is off, the input
object itself, so that the identity run is the reference call of projection.main()).

AMBITION LEVELS (the 2050 Pathways Calculator, DECC 2010 and DESNZ 2023; EUCalc D2.5, Kockat et al. 2019)
  Reference  = Level 1   the lever's native parameter at its Reference value (the lever is off)
  Moderate   = Level 2   the exact midpoint between Reference and Ambitious in the native parameter (per year for the
                         path levers L1, L8, L9 and L10)
  Ambitious  = Level 3   the best value already achieved, by the first applicable sub-rule:
                 A  a case-study distribution exists -> Harrell-Davis q0.15 of the pooled scale-free case ratios
                    (the top-15% convention of the EU Taxonomy, Delegated Regulation 2021/2139, Annex I s. 7.7),
                    with a percentile bootstrap interval;
                 B  an NZ record with no structural trend exists -> the best value ever observed in NZ;
                 C  otherwise -> a published reference value (official projection > legislated target >
                    peer-reviewed scenario > peer-country value)
  TL         = Level 4   the Theoretical Limit (TL_RULE): the best value observed, internationally where a comparable
                         measure exists, otherwise in New Zealand, or a documented scenario bound; a logical bound
                         only where physically attainable by choice or design; every lever at TL is asserted at
                         least as strong as Ambitious (tl_strength)
Levels between Reference and Ambitious are indexed by lambda in [0, 1] (the native parameter
x(lambda) = x_ref + lambda (x_amb - x_ref)); Moderate is lambda = 0.5 exactly (the lambda-sweep of the Extended Data).

ADOPTION. Every level, TL included, moves from the Reference along the normalised logistic 2026 -> 2035 (midpoint
2030.5, k = ln(81) / 6; RECC full roll-out by 2035, Pauliuk et al. 2024): x(y) = x_ref + w(y) (x_level - x_ref).
Stated exceptions: L10 follows its own scenario path (no logistic weight), and L1 at TL is limited to the fastest
observed census-interval change of household size (tl_speed).
Sensitivities: by 2030, by 2045 (the Pathways) and the instant TL (full strength from 2027). Years: model index 0 = 2025,
1 = 2026 (observed; no lever touches it).

LEVERS (grouped by the PAS 2080:2023 hierarchy, naming.STRATEGY_LEVERS; sub-rule naming.LEVER_SUBRULE)
  S1 Avoid    L1 Household size [C]    S = S_ref + gap, gap = Stats NZ Medium B - Medium A household size (the
                                       propensity-B path: living arrangements change as modelled on the 2001-2023
                                       censuses; both rebased on the observed 2023 S, the same post-2048 tail)
              L2 Vacancy rate [B]      vacancy parameter -> the 1996 census minimum (one definition)
              L3 Building lifetime [C] demolition and the recent-surge component x (1 - d), d = 0.40
              L4 Extra space [B]       share f of the extra-space margin (size - occupied area) removed, applied
                                       after L5; f_amb,t = (size_ref - size_min) / (size_ref - occ_ref), size_min = the
                                       smallest annual mean consented size 1990-2025
              L5 Occupancy density [A] every typology's OLF and dwelling size x r, r = HD q0.15 of the 16 case-study
                                       ratios OLF_i / typology median
  S2 Switch   L6 Brownfield-first development [C] share s of new floor area on previously developed land, 0.59
              L7 Soil-aware planning [C] soil carbon loss per m2 x (1 - x), x = 0.146
              L8 Material carbon efficiency [A] A1-A3 x r(y), r(y) = HD q0.15 of the case ratios
                                       x_i(y) = (A1-A3_i,2025 - red13_i(y)) / pooled(y): each case on its own
                                       decarbonisation path, every year
  S3 Improve  L9 Construction-stage carbon [C]  A4-A5 split into transport, site energy and waste (L9_SHARES);
                                       Ambitious: site energy -85%, transport and waste as the Reference
              L10 Production decarbonisation [C] A1-A3 x m(y), m = the lower envelope of the 9 prospective backgrounds
                                       of Horup et al. (2025) Table S3 relative to their average, by archetype
                                       (A1-A3_t(y) = r8_t(y) x [A13_2025,t - red13_t(y)] x m10_t(y))
  Moderate / Ambitious Pathway: every lever at that setting.
Resolved values: outputs/data/pathways/levers.json.
"""
import math

import numpy as np
import pandas as pd

import naming as N

LEVERS = tuple(N.LEVERS)                          # ('L1', ..., 'L10'), in the PAS 2080 order
SETTINGS = tuple(N.SETTINGS)                      # ('moderate', 'ambitious')
LEVELS = ('reference', 'moderate', 'ambitious', 'tl')
LAMBDA = {'reference': 0.0, 'moderate': 0.5, 'ambitious': 1.0}
SETTING_NAMES = dict(N.SETTINGS)
LEVER_NAMES = dict(N.LEVERS)
STRATEGIES = dict(N.STRATEGY_LEVERS)              # S1 Avoid, S2 Switch, S3 Improve -> their levers
STRATEGY_NAMES = dict(N.STRATEGIES)
LEVER_STRATEGY = dict(N.LEVER_STRATEGY)
PATHWAY = N.PATHWAY                               # the Moderate / Ambitious Pathway: every lever
SUBRULE = dict(N.LEVER_SUBRULE)
SUBRULE_TEXT = {'A': 'A: case-study distribution, Harrell-Davis q0.15 of the pooled scale-free case ratios',
                'B': 'B: best value ever observed in NZ (no structural trend)',
                'C': 'C: published reference value (official projection > legislated target > peer-reviewed '
                     'scenario > peer-country value)'}
# demand band(s) each lever targets (naming.BANDS; LEVERS_TABLE.md)
BAND_TARGET = {
    'L4': 'Extra space (and the dwelling size of every band except Population growth)',
    'L5': 'Every band: occupied area per person (OLF) and dwelling size of every typology',
    'L1': 'Smaller households (and the number of households of every band)',
    'L2': 'Vacancy (including the change in the vacancy rate)',
    'L3': f"{N.BANDS['replacement']} and {N.BANDS['redevelopment']}",
    'L8': 'None: carbon per m2 (A1-A3) of every band',
    'L9': 'None: carbon per m2 (A4-A5) of every band',
    'L10': 'None: carbon per m2 (A1-A3) of every band',
    'L7': 'None: soil carbon loss per m2 of every soil-bearing band',
    'L6': 'None: the soil-bearing share of every band'}
LEVER_PARAMETER = {'L4': 'f, share of the extra-space margin removed (engine `size`), per typology',
                   'L5': 'r, design density ratio (engine `olf` and `size`), per typology',
                   'L1': 'S, household size path (households = population / S)',
                   'L2': 'v, vacancy-rate parameter (engine `v`)',
                   'L3': 'd, reduction of demolition and of the recent-surge component (`rate_demol`, `rate_unc`)',
                   'L8': 'r, A1-A3 ratio by year (`intensity`, A1-A3 term only), per typology',
                   'L9': 'A4-A5 factor path relative to 2025 (`intensity`, A4-A5 term only)',
                   'L10': 'm, A1-A3 production multiplier by year vs the Horup nine-scenario average (`intensity`, '
                          'A1-A3 term only), per typology',
                   'L7': 'x, reduction of soil carbon loss per m2 (engine `soil`)',
                   'L6': 's, share of new floor area on previously developed land (`brownfield_share`)'}

OBSERVED_YEAR = 2026            # last observed year: w = 0 up to and including it


def adoption_window(end, name=None, start=OBSERVED_YEAR):
    """The adoption path of a window start -> end (W = end - start years), one rule for every
    window: normalised logistic with midpoint start + W/2 and speed k = ln(81) / (2W/3), so that
    s rises from 10% to 90% within the middle two-thirds of the window; w(start) = 0, w(end) = 1,
    w = 1 after end (ramp())."""
    W = end - start
    return dict(name=name or f'by{end}', mid=start + W / 2.0, end=end, k=math.log(81.0) / (2.0 * W / 3.0))


ADOPTED_WINDOW = adoption_window(2035)
RAMP_END = ADOPTED_WINDOW['end']    # full strength from this year (adopted: by2035)
RAMP_MID = ADOPTED_WINDOW['mid']    # 2030.5
RAMP_K = ADOPTED_WINDOW['k']        # ln(81) / 6: s rises from 0.1 to 0.9 within 6 years
assert RAMP_MID == 2030.5 and RAMP_K == math.log(81.0) / 6.0
ADOPTION_ADOPTED = 'by2035'
ADOPTION_BY2045 = adoption_window(2045)    # sensitivity (the Pathways): midpoint 2035.5, k = ln(81) / (38/3)
ADOPTION_BY2030 = adoption_window(2030)    # sensitivity (the Pathways): midpoint 2028, k = ln(81) / (8/3)
ADOPTION_SENSITIVITIES = (ADOPTION_BY2030, ADOPTION_BY2045)
RAMP_BASIS = ('full roll-out by 2035 following RECC (Pauliuk et al. 2024, J. Ind. Ecol. 28, 1699: circular-economy '
              'strategies fully implemented by 2035)')

# ---------------------------------------------------------------------------
# PARAMETERS (rule anchors; resolve() computes the data-based ones)
# ---------------------------------------------------------------------------
HD_Q = 0.15                       # sub-rule A: top 15% (EU Taxonomy 2021/2139, Annex I s. 7.7)
HD_CI = 0.95
HD_BOOTSTRAP_SEED = 20261008      # L8; L5 uses seed + 1
L4_CONSENT_YEARS = (1990, 2025)
L4_FULL_STRENGTH_YEAR = 2035      # occ_ref = S_ref(2035) x OLF_t: the size at full strength equals size_min
L5_N_CASES = 16
L5_TYPOLOGIES = ('Detached', 'Townhouses', 'Apartments')
# L1: the Ambitious household size is the Stats NZ propensity-B path (living-arrangement propensities
# change, modelled on the 2001-2023 censuses; Stats NZ DataInfo+, POPPR_FHH), the Reference the propensity-A path
# (propensities held at 2023), both Medium, rebased on the observed 2023 S with the same post-2048 tail
# (projection.S_TAIL). Within one propensity the Low / Medium / High variants differ only through their population
# projections (age structure), so the earlier High - Medium gap was not a behavioural lever.
L1_VARIANTS = ('A', 'B')                 # HH_PROPENSITY of the Reference and of the Ambitious path (Medium variant)
L1_REFERENCE_VARIANT = 'A'
L1_AMBITIOUS_VARIANT = 'B'
L1_PROPENSITY_SOURCE = ('Stats NZ, National family and household projections: 2023(base)-2048, propensity B '
                        '(living-arrangement type propensities change, based on modelling of 2001-2023 Census data); '
                        'DataInfo+ POPPR_FHH')
# TL1 speed limit: the TL household size cannot rise faster than the fastest change observed between
# consecutive censuses 1991-2023 (census-benchmarked households): S_TL(t) = min(S_ref(2026) + r (t - 2026), TL1
# level), and never below the Ambitious path (S_ref + w gap). The other TL items keep the logistic window; the instant
# TL row (TL_FROM2027) keeps its definition (the level from 2027).
TL1_SPEED_CENSUS_WINDOW = (1991, 2023)
TL1_SPEED_START = OBSERVED_YEAR
L1_TL_VARIANT = 'Medium'          # the population variant of the deterministic L1 at TL ratio path
L2_VACANCY_FLOOR = 0.040          # implied vacancy must never fall below this in a non-TL run (check)
L3_D_AMBITIOUS = 0.40             # Pellan et al. 2024: demolition 150,000 -> 90,000 a year
L8_SAMPLE_TYPOLOGIES = ('Detached', 'Townhouses')
L8_MIN_CASES = 10
L9_REF_RATE = 0.01
# L9: A4-A5 split into transport (A4), site energy and site waste by the medians of Kanafani et al.
# (2023) Sustainability 15(14), 10992 (61 Danish construction sites, kg CO2e per m2 per year): A4 0.28; site energy =
# electricity 0.19 + heat 0.12 + fuel 0.08; waste 0.49 (the main A5 contributor, as Hasselsteen et al. 2025 J. Clean.
# Prod. 521, 146243). The medians do not add, so the shares are the medians normalised. Reference: every part -1%/yr
# (Resch et al. 2021; the total unchanged). Ambitious: site energy -85% (City of Oslo Climate Agency 2025, Barriers and
# key success factors for zero emission construction in Oslo, v0.1: "roughly 85 percent of work at municipal
# construction sites" with zero-emission machinery in 2024), A4 and waste as the Reference; Moderate the midpoint; at
# TL A4 and site energy zero (electric machinery and freight exist), waste as the Reference (its material carbon
# belongs to L8 / L10). Every level on the common 2026-2035 logistic adoption (no own path).
L9_MEDIANS = {'transport (A4)': ('transport', 0.28), 'site electricity': ('site_energy', 0.19),
              'site heat': ('site_energy', 0.12), 'site fuel': ('site_energy', 0.08), 'site waste': ('waste', 0.49)}
L9_PARTS = ('transport', 'site_energy', 'waste')
L9_SHARES = {q: sum(v for g, v in L9_MEDIANS.values() if g == q) / sum(v for _, v in L9_MEDIANS.values())
             for q in L9_PARTS}
L9_SITE_ENERGY_CUT_AMBITIOUS = 0.85
L9_CUT = {'ambitious': {'transport': 0.0, 'site_energy': L9_SITE_ENERGY_CUT_AMBITIOUS, 'waste': 0.0},
          'tl': {'transport': 1.0, 'site_energy': 1.0, 'waste': 0.0}}
# One rule for the Theoretical Limit, written once here, in METHODS_DRAFT and the Extended Data Table 1
TL_RULE = ('Theoretical Limit = the best value observed, internationally where a comparable measure exists, otherwise '
           'in New Zealand, or a documented scenario bound; a logical bound only where physically attainable by choice '
           'or design.')
# L2 at TL: OECD (2024) Affordable Housing Database HM1.1, Figure HM1.1.2 panel B, Switzerland 2022
FILE_OECD_VACANCY = 'data/derived/oecd_hm112_vacancy.csv'
L2_TL_COUNTRY = 'Switzerland'
L2_TL_NOTE = ('At the Theoretical Limit every non-market empty dwelling (holiday homes, dwellings held empty) is '
              'occupied, a choice, and only frictional market vacancy remains, at the lowest nationwide rate in the OECD '
              'cross-country table: Switzerland 1.31% (2022): 61,496 empty dwellings on 1 June 2022, a share of the '
              'total dwelling stock including single-family homes (Swiss Federal Statistical Office, empty dwellings '
              'survey; admin.ch media release https://www.admin.ch/gov/en/start/documentation/media-releases.msg-id-'
              '90300.html). Sweden (0.25%, 2021) is excluded: its '
              'national count (6,794 vacant units in a 4.6 M stock; OECD \'Vacant\' sheet) cannot be an all-tenure '
              'market count. One vintage (OECD 2024 table) is used for all countries; national releases after it are '
              'not.')
# L6 at TL: DCLG (2010) Land use change statistics England, provisional estimates for 2009: "80% of
# dwellings (including conversions) were built on previously developed land, unchanged from 2008" (England's peak)
L6_S_TL = 0.80
L8_REPORT_YEARS = (2025, 2030, 2040, 2050)
# L10 Production decarbonisation: the same materials and quantities made with lower-carbon production.
# Source: Horup et al. (2025) Table S3, GWP per m2 of the Danish archetypes 2025-2050, average / minimum / maximum over
# the 9 prospective backgrounds of Table S1 (SSP1/2/5 x no climate policy / RCP2.6 / RCP1.9), extracted by
# data/build_horup.py. m10_Amb,t(y) = [MIN_a(y) / MIN_a(2025)] / [AVG_a(y) / AVG_a(2025)]: the extra decarbonisation of
# the lower envelope over the nine-scenario average, which the Reference already follows (the S4 item paths). Author
# decision: archetype a = 'Single family houses' for Detached and Townhouses, 'Multi dwellings' for Apartments; the
# extra decarbonisation is spread evenly across materials (Horup report the envelope by archetype only). L10 at TL
# adds near-zero emissions cement and steel to this envelope (below). No logistic ramp: the scenario path is the
# timing; m = 1 up to the observed year 2026.
FILE_L10 = 'data/derived/horup2025_table_s3_archetypes.csv'
L10_ARCHETYPE = {'Detached': 'Single family houses', 'Townhouses': 'Single family houses',
                 'Apartments': 'Multi dwellings'}
L10_EVIDENCE = 'documented scenario: lower envelope of 9 prospective backgrounds (Horup et al. 2025, Table S3)'
L10_REPORT_YEARS = (2030, 2040, 2050)
L7_X_AMBITIOUS = 0.146            # Christoforatos, Pickering & Schipper 2026 (SOC-aware allocation)
L6_S_AMBITIOUS = 0.59             # DLUHC 2022: England, three-year average 2018-21
L6_CONTEXT = dict(us_epa_2014_infill=0.21, england_2020_21=0.66, england_3yr=0.59, north_east=0.41, london=0.89)

SOURCES = {
    'DECC2010': 'DECC (2010) 2050 Pathways Analysis. Department of Energy and Climate Change, London, July 2010 '
                '(ambition levels 1-4)',
    'DESNZ2023': 'DESNZ (2023) How to build a 2050 Calculator (guide). Department for Energy Security and Net Zero, '
                 'London (levels 1-4)',
    'Kockat2019': 'Kockat J, Wallerand AS, Jankovic I, Wang X (2019) Identification of levers and levels for the building '
                  'stock. EUCalc Deliverable D2.5 (updated July 2019), Horizon 2020 grant 730459 (Table 2: Levels 1-4)',
    'EUTaxonomy2021': 'Commission Delegated Regulation (EU) 2021/2139 (Climate Delegated Act), Annex I, Section 7.7 '
                      '(top 15% of the national or regional building stock)',
    'HarrellDavis1982': 'Harrell FE, Davis CE (1982) A new distribution-free quantile estimator. Biometrika 69(3), 635-640',
    'EfronTibshirani1993': 'Efron B, Tibshirani RJ (1993) An Introduction to the Bootstrap. Chapman & Hall (percentile interval)',
    'StatsNZConsents': 'Stats NZ building consents by typology, floor area and number (data/derived/consents_monthly.csv)',
    'ChristoforatosPickering2026': 'Christoforatos G, Pickering K (2026) Embodied impacts of residential stocks. '
                                   'Smart and Sustainable Built Environment, advance online publication, '
                                   'doi:10.1108/SASBE-06-2025-0304 (16 NZ case studies)',
    'StatsNZHousehold': 'Stats NZ, National family and household projections: 2023(base)-2048, Low / Medium / High '
                        'A (POPPR_FHH_008, POPPR_FHH_010; DataInfo+ https://datainfoplus.stats.govt.nz/item/nz.govt.'
                        'stats/e7475c01-9e55-491d-a8fe-74efa8fba757; accessed 2026-11-11; '
                        'data/derived/households_proj_2023base.csv)',
    'StatsNZCensus': 'Stats NZ census dwelling counts 1986-2023 (data/derived/census_dwellings.csv, occ-unocc-2013.xlsx)',
    'Pellan2024': 'Pellan M, Almeida D, Louerat M, Habert G (2024) From limit values to carbon budgets: assessing '
                  'comprehensive building stock decarbonisation strategies. Building and Environment 256, 111505 '
                  '(Table 2: demolition 150,000 -> 90,000 a year)',
    'Horup2025': 'Horup L, Bruhn S, Hoxha E, Birgisdottir H, Secher AQ, Ohms P, Hauschild M (2025) Absolute '
                 'sustainability assessment of the Danish building sector through prospective LCA. Science of the '
                 'Total Environment 966, 178780 (Fig. 6; supplementary Tables S1, S3 and S4)',
    'Resch2021': 'Resch E, Andresen I, Cherubini F, Brattebo H (2021) Estimating dynamic climate change effects of '
                 'material use in buildings - timing, uncertainty, and emission sources. Building and Environment 187, '
                 '107399 (Table 1: A4-A5 e^(-0.01 (t - 2025)), the adopted path of the model)',
    'CCRA2002': 'Climate Change Response Act 2002 (NZ), s 5Q (as amended 2025): the 2050 target, net zero for all '
                'greenhouse gases other than biogenic methane by 2050 (s 5Q(1)(a), unchanged by the Climate Change '
                'Response (2050 Target and Other Matters) Amendment Act 2025); an economy-wide target, used for the '
                'end year 2050 only',
    'Oslo2025': 'City of Oslo (2025) Revised standard climate and environmental requirements for City of Oslo '
                'construction sites. City Government Proposition 1014/25 (emission-free site machinery from 2027; '
                'emission-free construction aimed for by 2030; it does not require total A4-A5 to reach zero)',
    'ChristoforatosPickeringSchipper2026': 'Christoforatos G, Pickering K, Schipper LA (2026) Integrating soil '
                                           'organic carbon loss into building life cycle assessment and urban '
                                           'planning. Journal of Environmental Management 415, 130603, '
                                           'doi:10.1016/j.jenvman.2026.130603 (SOC-aware scenario: same developed '
                                           'area, inverse-SOC allocation, 14.6% less SOC loss than BAU)',
    'DLUHC2022': 'UK Department for Levelling Up, Housing and Communities (2022) Land use change statistics in '
                 'England: new residential addresses 2020 to 2021 (66% on previously developed land in 2020-21; 59% '
                 'three-year average; regions 41% North East - 89% London)',
    'USEPA2012': 'US EPA (2012) Residential Construction Trends in America\'s Metropolitan Regions, 2012 edition '
                 '(infill share of new residential construction, about 21% nationally)',
    'Pauliuk2024': 'Pauliuk S, Carrer F, Heeren N, Hertwich EG (2024) Scenario analysis of supply- and demand-side '
                   'solutions for circular economy and climate change mitigation in the global building sector. '
                   'Journal of Industrial Ecology 28(6), 1699-1715',
    'Shapley1953': 'Shapley LS (1953) A value for n-person games. In: Kuhn HW, Tucker AW (eds) Contributions to the '
                   'Theory of Games II. Annals of Mathematics Studies 28, 307-317',
    'Albrecht2002': 'Albrecht J, Francois D, Schoors K (2002) A Shapley decomposition of carbon emissions without '
                    'residuals. Energy Policy 30(9), 727-736',
}


# ============================================================
# RAMP
# ============================================================
def ramp(years, mid=RAMP_MID, end=RAMP_END, start=OBSERVED_YEAR, k=RAMP_K):
    """Normalised logistic: w(start) = 0, w(end) = 1, monotone; 0 before start, 1 after end."""
    y = np.asarray(years, float)
    s = lambda t: 1.0 / (1.0 + np.exp(-k * (np.asarray(t, float) - mid)))
    w = (s(y) - s(start)) / (s(end) - s(start))
    return np.where(y <= start, 0.0, np.where(y >= end, 1.0, w))


TL_FROM2027 = 'from2027'           # adoption: full strength from 2027 (the instant TL sensitivity)


def ramp_named(years, name=None):
    """The adopted adoption path (name None or 'by2035'), a sensitivity ('by2030', 'by2045') or full
    strength from 2027 ('from2027', the instant sensitivity of the theoretical limit)."""
    if name is None or name == ADOPTION_ADOPTED:
        return ramp(years)
    if name == TL_FROM2027:
        return ramp_from2027(years)
    for r in ADOPTION_SENSITIVITIES:
        if name == r['name']:
            return ramp(years, mid=r['mid'], end=r['end'], k=r['k'])
    raise ValueError(f'Unknown adoption path {name!r}.')


def ramp_from2027(years, start=OBSERVED_YEAR):
    """w = 1 from the first year after the observed year (2027), 0 up to and including 2026."""
    return (np.asarray(years, float) > start).astype(float)


# ============================================================
# SUB-RULE A ESTIMATOR: Harrell-Davis quantile, bootstrap interval
# ============================================================
def hd_weights(n, q):
    """Harrell & Davis (1982): W_i = I_{i/n}(a, b) - I_{(i-1)/n}(a, b), a = q (n + 1),
    b = (1 - q)(n + 1), I the regularised incomplete beta function."""
    from scipy.special import betainc
    a, b = q * (n + 1), (1.0 - q) * (n + 1)
    grid = np.arange(n + 1) / n
    return np.diff(betainc(a, b, grid))


def hd_quantile(x, q):
    """Harrell-Davis estimate of the q-quantile: Beta-weighted sum of the order statistics."""
    xs = np.sort(np.asarray(x, float))
    return float(hd_weights(len(xs), q) @ xs)


def hd_bootstrap(x, q, B, seed, ci=HD_CI):
    """Nonparametric bootstrap of the cases (resampled with replacement, B times, fixed seed);
    percentile interval (Efron & Tibshirani 1993). Returns (lo, hi, draws)."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    draws = np.sort(x[idx], axis=1) @ hd_weights(len(x), q)
    lo, hi = np.percentile(draws, [100 * (1 - ci) / 2, 100 * (1 + ci) / 2])
    return float(lo), float(hi), draws


def hd_estimate(x, q, B, seed):
    """Sub-rule A: r = HD q-quantile, its bootstrap interval, scipy's hdquantiles as a cross-check and the weights."""
    from scipy.stats.mstats import hdquantiles
    r = hd_quantile(x, q)
    lo, hi, _ = hd_bootstrap(x, q, B, seed)
    return dict(q=q, r=r, ci_lo=lo, ci_hi=hi, n=int(len(x)),
                scipy_hdquantiles=float(np.asarray(hdquantiles(np.asarray(x, float), prob=[q]))[0]),
                weights=[float(v) for v in hd_weights(len(x), q)],
                bootstrap=dict(B=int(B), seed=int(seed), ci=HD_CI, method='percentile'))


def case_ratios(fb, typologies=L8_SAMPLE_TYPOLOGIES):
    """L8 sample: x_i = A1-A3_i / pooled A1-A3 of its typology (2025 factors, factors_building.csv),
    independent cases only (empty duplicate_of). Pooling as Building_factors.pool: equal
    weight per sub-type, then per building (over every case of the typology, as the model)."""
    rows, pooled = [], {}
    for t in typologies:
        g = fb[fb['Typology'] == t]
        pooled[t] = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        for _, r in g[g['duplicate_of'].fillna('') == ''].iterrows():
            rows.append(dict(id=r['id'], typology=t, subtype=r['Subtype'], a13=float(r['A1-A3']),
                             ratio=float(r['A1-A3']) / pooled[t]))
    return pd.DataFrame(rows).sort_values('ratio').reset_index(drop=True), pooled


def case_paths(fb, red, typologies=L8_SAMPLE_TYPOLOGIES):
    """L8 by year: x_i(y) = (A1-A3_i,2025 - red13_i(y)) / pooled(y), each case on its own
    decarbonisation path, pooled(y) pooled as case_ratios (equal weight per sub-type, every case of the typology).
    red: A1-A3 reduction per case (rows = id) and year (columns; factors_building_a13_reduction.csv). Returns
    ({year: DataFrame of the independent cases (id, typology, ratio)}, {typology: {year: pooled}})."""
    out, pooled = {}, {t: {} for t in typologies}
    for y in red.columns:
        rows = []
        for t in typologies:
            g = fb[fb['Typology'] == t].assign(path=lambda d: d['A1-A3'].values - red.loc[d['id'], y].values)
            pooled[t][int(y)] = float(g.groupby('Subtype')['path'].mean().mean())
            for _, r in g[g['duplicate_of'].fillna('') == ''].iterrows():
                rows.append(dict(id=r['id'], typology=t, subtype=r['Subtype'], ratio=float(r['path']) / pooled[t][int(y)]))
        out[int(y)] = pd.DataFrame(rows)
    return out, pooled


def case_reductions(settings, fb, years):
    """Per-case A1-A3 reduction (kg/m2) by year of the projection's decarbonisation setting (zeros for 'none')."""
    import Building_factors as BF
    red = pd.DataFrame(0.0, index=fb['id'], columns=[int(y) for y in years])
    variant = BF.decarb_variant(settings.DECARB_MODE, settings.DECARB_ITEM_CASE)
    if variant is not None:
        r = pd.read_csv(settings.FILE_FACTORS_DECARB_BLD)
        red = red + (r[r['Variant'] == variant].pivot(index='id', columns='Year', values='A13_reduction_kgCO2e_per_m2')
                     .reindex(index=fb['id'], columns=[int(y) for y in years]))
    if red.isna().any().any():
        raise SystemExit('STOP (L8): a case or year lacks its A1-A3 reduction.')
    return red


def l10_paths(years, path=None):
    """L10: Horup et al. (2025) Table S3 archetype paths relative to their own 2025 value, by archetype
    and statistic (avg | min | max), as arrays over `years` (2025-2050 required); and the source cells."""
    import os
    d = pd.read_csv(path or os.path.join(os.path.dirname(os.path.abspath(__file__)), FILE_L10), comment='#')
    years = [int(y) for y in years]
    out, cells = {}, {}
    for (a, st), g in d.groupby(['archetype', 'stat']):
        g = g.set_index('year')
        missing = sorted(set(years) - set(g.index))
        if missing:
            raise SystemExit(f'STOP (L10): Table S3 lacks years {missing} for {a} {st}.')
        out[(a, st)] = g.loc[years, 'rel_to_2025'].to_numpy(float)
        cells[(a, st)] = {int(y): str(c) for y, c in g['cell'].items()}
    return out, cells


def l10_multiplier(years, stat='min', path=None):
    """{typology: m(y)} = [stat_a(y) / stat_a(2025)] / [AVG_a(y) / AVG_a(2025)] with the archetype a of the typology
    (L10_ARCHETYPE); stat 'min' = L10 Ambitious (= TL10), 'max' = the no-climate-policy sensitivity (ED6)."""
    rel, _ = l10_paths(years, path)
    return {t: rel[(a, stat)] / rel[(a, 'avg')] for t, a in L10_ARCHETYPE.items()}


# Item-level production chain: for every case-study item i, A13_i(y) = A13_i,2025 x p_i(y) x q_i(y),
# p_i the Horup S4 path of the item (unmapped items held), q_i the L10 multiplier at the run's level:
# q_i = m_a(y) x c_k(y), m_a the archetype multiplier (uniform over a case's items: Horup et al. report the envelope by
# archetype only) and c_k a factor of the item's class k (1 unless the class is in L10_TL_CLASSES and L10 is at TL).
# Items aggregate to case studies (per m2) and typologies by the same pooling (Building_factors.pool). Pooling is
# linear and m_a is uniform within a typology, so the typology A1-A3 is exactly m_a(y) x C_t(y) x the decarbonised
# path, C_t(y) = 1 - sum_k P_tk(y) (1 - c_k(y)) / P_t(y) with P_tk the pooled class paths
# (factors_a13_class_paths.csv); the same chain gives the A1-A3 component of the in-window events (class kernels)
# and of the committed lower bound. With every c_k = 1 the correction terms are exact zeros (l10_chain).
# L10 at TL: near-zero emissions cement and steel (IEA 2022, Definitions for near-zero and low-emissions
# steel and cement, and underlying emissions measurement methodologies, p. 17: 125 kg CO2-eq/t cement at 100% clinker,
# 400 kg CO2-eq/t crude steel at 100% iron), relative to the BAT reference values of IEA (2022) Achieving Net Zero
# Heavy Industry Sectors in G7 Members (cited ibid. p. 22-23, footnote 8: 850 kg CO2-eq/t cement at 100% clinker,
# 2,945 kg CO2-eq/t crude steel, BF-BOF with 100% iron). The near-zero share s(y) of production: 0 (2022), 0.08
# (2030), 0.27 (2035), 0.93 (2050), linear between the milestones, 0 through the observed 2026 (IEA 2023, Net Zero
# Roadmap: A Global Pathway to Keep the 1.5 °C Goal in Reach, 2023 update, Cement: near-zero emission clinker
# production share 0% / 8% / 27% / 93% in 2022 / 2030 / 2035 / 2050; verified; steel takes the same s, a stated
# assumption). q_i = m_a(y) x [(1 - s(y)) + s(y) k], whatever the item's S4
# mapping. Classes: cement-based CONCRETE, REINFORCED CONCRETE, FIBRE CEMENT and PLASTER (cement plaster), STEEL, and
# the OTIS elevator (OTHERS, apartments A_1 / A_2; Building_factors.ELEVATOR_CLASS), an assembled product dominated by
# steel: the whole item treated as steel at TL (an upper bound of the reduction; author decision).
L10_K_CEMENT = 125.0 / 850.0
L10_K_STEEL = 400.0 / 2945.0
L10_S_MILESTONES = {2022: 0.0, 2030: 0.08, 2035: 0.27, 2050: 0.93}
L10_S_SOURCE = ('IEA (2023) Net Zero Roadmap: A Global Pathway to Keep the 1.5 °C Goal in Reach, 2023 update, Cement: '
                'near-zero emission clinker production share (verified)')
L10_S_TEXT = ', '.join(f'{100 * v:.0f}% in {k}' for k, v in L10_S_MILESTONES.items() if v > 0)
L10_S_TEXT = ' and '.join(L10_S_TEXT.rsplit(', ', 1))      # '8% in 2030, 27% in 2035 and 93% in 2050'
L10_ELEVATOR_CLASS = 'ELEVATOR (assembled, steel-dominated)'
L10_ELEVATOR_NOTE = ('assembled product dominated by steel; whole item treated as steel at TL (upper bound of the '
                     'reduction; ~2.4% of A1-A3, apartments only)')
L10_TL_CLASSES = {'CONCRETE': L10_K_CEMENT, 'REINFORCED CONCRETE': L10_K_CEMENT, 'FIBRE CEMENT': L10_K_CEMENT,
                  'PLASTER': L10_K_CEMENT, 'STEEL': L10_K_STEEL, L10_ELEVATOR_CLASS: L10_K_STEEL}
# every production class reviewed for cement- or steel-dominance (a class not listed stops the run)
L10_CLASS_REVIEW = {
    'CONCRETE': 'cement-based', 'REINFORCED CONCRETE': 'cement-based (steel reinforcement included in the item)',
    'FIBRE CEMENT': 'cement-based', 'PLASTER': 'cement-based (the only item is "Plaster, cement")', 'STEEL': 'steel',
    L10_ELEVATOR_CLASS: 'steel (' + L10_ELEVATOR_NOTE + ')',
    'OTHERS': 'neither (after the elevator: MDF doors, ceramic tiles and sanitary ware, particleboard, glazing)',
    'BRICKS': 'neither (clay brick)', 'TIMBER': 'neither', 'PLASTICS': 'neither', 'ALUMINIUM': 'neither (aluminium)',
    'PLASTERBOARD': 'neither (gypsum)', 'SIP': 'neither (timber-foam panel)', 'GLASS': 'neither',
    'GLASS WOOL': 'neither', 'PAINT': 'neither'}


def l10_near_zero_share(years):
    """s(y): the near-zero share of cement and steel production, linear between L10_S_MILESTONES, 0 through 2026."""
    y = np.asarray(years, float)
    k = sorted(L10_S_MILESTONES)
    s = np.interp(y, k, [L10_S_MILESTONES[x] for x in k])
    return np.where(y <= OBSERVED_YEAR, 0.0, s)


def l10_class_factor(level, years):
    """{item class: c_k(y)} at an L10 level: c_k = (1 - s(y)) + s(y) k at TL for L10_TL_CLASSES, none otherwise."""
    if level != 'tl' or not L10_TL_CLASSES:
        return {}
    s = l10_near_zero_share(years)
    return {k: (1.0 - s) + s * kk for k, kk in L10_TL_CLASSES.items()}


def l10_chain(base, m_eff, cls_eff, typ):
    """The item-level chain aggregated per typology: q_t(y) = m_t(y) x C_t(y) (construction A1-A3) and, per class with
    a factor, (m_t(y) (c_k(y) - 1)) the multiplier of its pooled path / event kernel. cls_eff {class: c_k(y)} (empty:
    C_t = 1 exactly). Returns (q, corr): q {typology: array}; corr {typology: {class: array}}."""
    q, corr = {}, {}
    for t in typ:
        m = np.asarray(m_eff[t], float)
        if not cls_eff:
            q[t], corr[t] = m, {}
            continue
        P = float(base['a13_2025'][t]) - np.asarray(base['red13'][t], float)
        d = sum(np.asarray(base['a13_class'][t][k], float) * (1.0 - c) for k, c in cls_eff.items())
        q[t] = m * (1.0 - d / P)
        corr[t] = {k: m * (c - 1.0) for k, c in cls_eff.items()}
    return q, corr


def l10_weight(years):
    """L10 is applied without the logistic adoption weight (the scenario path is the timing, as L9): 1 after the
    observed year 2026, 0 up to it (m = 1 in 2025-2026)."""
    return (np.asarray(years, float) > OBSERVED_YEAR).astype(float)


def design_ratios(chars, fb):
    """L5 sample: x_i = design floor area per occupant (OLF_i = total GFA / design occupants) / the median OLF of the
    case's typology, every one of the 16 case studies (A_2 included: a distinct design, 4,078 vs 3,721 m2 for the
    same 189 occupants)."""
    c = chars[['Total GFA', 'Occupants', 'OLF']].join(fb.set_index('id')[['Typology', 'Subtype']], how='inner')
    med = c.groupby('Typology')['OLF'].median()
    c = c.assign(median_olf=c['Typology'].map(med), ratio=c['OLF'] / c['Typology'].map(med))
    c.index.name = 'id'
    return c.reset_index().sort_values('ratio').reset_index(drop=True), med


# ============================================================
# L9 PATHS (A4-A5 factor relative to 2025)
# ============================================================
def a45_reference(years):
    """The adopted A4-A5 factor e^(-0.01 (y - 2025)) (Building_factors.generic_path, DECARB_A45 'resch')."""
    t = np.asarray(years, float)
    return np.exp(-L9_REF_RATE * np.clip(t - 2025.0, 0.0, None))


def l9_cut(lam):
    """{part: cut at full strength} of L9 at level lambda (0..1) or 'tl': lambda x the Ambitious cuts (Moderate = the
    midpoint), or the TL cuts."""
    if lam == 'tl':
        return dict(L9_CUT['tl'])
    return {q: float(lam) * c for q, c in L9_CUT['ambitious'].items()}


def a45_target(years, lam):
    """L9 target A4-A5 factor path at full strength (before the adoption weight), relative to 2025:
    ref(y) x (1 - sum_part share x cut), ref = e^(-0.01 (y - 2025))."""
    ref = a45_reference(years)
    cut = l9_cut(lam)
    return ref * (1.0 - sum(L9_SHARES[q] * cut[q] for q in L9_PARTS))


def l9_parts(a45_2025, years, lam, w):
    """{typology: {part: A4-A5 kg/m2 by year}}: a45_2025 x share x ref(y) x (1 - w(y) cut) (lam None: the Reference)."""
    ref = a45_reference(years)
    cut = l9_cut(0.0 if lam is None else lam)
    return {t: {q: float(a45_2025[t]) * L9_SHARES[q] * ref * (1.0 - np.asarray(w, float) * cut[q]) for q in L9_PARTS}
            for t in a45_2025}


# ============================================================
# RESOLVE: every lever's levels from the data (once per projection state)
# ============================================================
def household_size(B):
    """S(y) = population / households of the median path (the engine's S)."""
    return np.asarray(B['df_forecast']['PopTotal_50th'].values, float) / np.asarray(B['households_forecast']['50th'], float)


def consent_size_minima(B, settings, years=L4_CONSENT_YEARS):
    """L4 sub-rule B: annual mean new-dwelling size (consented floor area / consents) by typology, years[0]-years[1];
    the minimum and its year."""
    d = B['df_consents']
    d = d[(d['Year'] >= years[0]) & (d['Year'] <= years[1])]
    out = {}
    for t, col in settings.COL_TYPOLOGIES.items():
        g = d.groupby('Year')[[col, settings.COL_CONSENT_COUNTS[t]]].sum()
        s = g[col] / g[settings.COL_CONSENT_COUNTS[t]]
        out[t] = dict(size_min=float(s.min()), year=int(s.idxmin()), series={int(y): float(v) for y, v in s.items()})
    return out


def resolve(B, factors_building, chars, factors_typology, settings, S_variants, bootstrap_B):
    """Every lever's levels (Reference, Moderate, Ambitious, TL) from the data in the projection state B
    (projection.main() locals), the projection module (`settings`), the case-study tables and the Stats NZ
    household-size variants (S_variants: {variant: dict(S, pop)}, projection runs with HH_SIZE_VARIANT changed).
    bootstrap_B: bootstrap replicates of the sub-rule A intervals (run profile). Returns a dict (levers.json)."""
    typ = list(B['typ_names'])
    years = np.asarray(B['forecast_years'])
    w = ramp(years)
    S = household_size(B)
    olf = {t: float(B['OLF_USED'][t]) for t in typ}
    size_ref = {t: float(B['size_ref'][t]) for t in typ}
    yy = lambda a: {int(y): float(v) for y, v in zip(years, a)}
    out = dict(adoption=dict(form='normalised logistic', k=RAMP_K, mid=RAMP_MID, start=OBSERVED_YEAR, end=RAMP_END,
                             adopted=ADOPTION_ADOPTED, basis=RAMP_BASIS, w=yy(w),
                             sensitivities=[dict(r) for r in ADOPTION_SENSITIVITIES]),
               levels=dict(N.LEVELS), lambda_=dict(LAMBDA), subrule=dict(SUBRULE))

    # ---- L5 Design density [A] (first: L4 acts on the margin after L5) ----
    cases2, med2 = design_ratios(chars, factors_building)
    present = sorted(set(cases2['Typology']))
    if len(cases2) != L5_N_CASES or set(present) != set(L5_TYPOLOGIES):
        raise SystemExit(f'STOP (L5): design-density sample n = {len(cases2)} (expected {L5_N_CASES}), typologies '
                         f'{present} (expected {list(L5_TYPOLOGIES)}).')
    est2 = hd_estimate(cases2['ratio'].values, HD_Q, bootstrap_B, HD_BOOTSTRAP_SEED + 1)
    r2 = est2['r']
    tl2 = {}
    for t in typ:
        g = cases2[cases2['Typology'] == t]
        own = float(g['ratio'].min())
        tl2[t] = dict(own_densest=own, own_densest_case=str(g.loc[g['ratio'].idxmin(), 'id']), r=min(own, r2),
                      exceeds_ambitious=bool(own < r2))
    out['L5'] = dict(subrule='A', n=int(len(cases2)), typologies=present, median_olf={k: float(v) for k, v in med2.items()},
                     cases=cases2[['id', 'Typology', 'Subtype', 'Total GFA', 'Occupants', 'OLF', 'median_olf', 'ratio']]
                     .to_dict(orient='records'), estimator=est2,
                     r={'reference': 1.0, 'moderate': (1.0 + r2) / 2.0, 'ambitious': r2},
                     tl={t: v['r'] for t, v in tl2.items()}, tl_detail=tl2, olf_reference=olf,
                     anchor=f'HD q0.15 of the 16 case-study design ratios = {r2:.4f}')

    # ---- L4 Dwelling size [B] ----
    mins = consent_size_minima(B, settings)
    i35 = int(np.where(years == L4_FULL_STRENGTH_YEAR)[0][0])
    occ_ref = {t: float(S[i35] * olf[t]) for t in typ}
    f_amb = {t: (size_ref[t] - mins[t]['size_min']) / (size_ref[t] - occ_ref[t]) for t in typ}
    bad = {t: v for t, v in f_amb.items() if not 0.0 <= v <= 1.0}
    if bad:
        raise SystemExit(f'STOP (L4): f_t outside [0, 1]: {bad}')
    out['L4'] = dict(subrule='B', size_ref=size_ref, size_ref_window=list(settings.DWELLING_SIZE_REF),
                     consent_years=list(L4_CONSENT_YEARS), minima={t: {k: v for k, v in m.items() if k != 'series'}
                                                                  for t, m in mins.items()},
                     consent_size_series={t: m['series'] for t, m in mins.items()},
                     occ_ref=occ_ref, occ_ref_year=L4_FULL_STRENGTH_YEAR, S_ref_occ_year=float(S[i35]), olf=olf,
                     f={'reference': {t: 0.0 for t in typ}, 'moderate': {t: f_amb[t] / 2.0 for t in typ},
                        'ambitious': f_amb}, tl={t: 1.0 for t in typ},
                     anchor=', '.join(f"{t} {mins[t]['size_min']:.1f} m2 ({mins[t]['year']})" for t in typ),
                     note='1990 is the first year of the consent series and a recession year')

    # ---- L1 Household size [C] ----
    if not all(np.array_equal(np.asarray(B['df_forecast']['PopTotal_50th']), np.asarray(p['pop'])) for p in S_variants.values()):
        raise SystemExit('STOP (L1): the household-size variants do not share the Reference population path.')
    S_a = np.asarray(S_variants[L1_REFERENCE_VARIANT]['S'], float)
    S_b = np.asarray(S_variants[L1_AMBITIOUS_VARIANT]['S'], float)
    if not np.allclose(S_a, S, rtol=1e-12, atol=0):
        raise SystemExit('STOP (L1): the Reference household size is not the Medium A path.')
    gap = S_b - S_a                          # every year: each path on its own post-2048 tail (projection.S_TAIL)
    if np.any(gap < -1e-12):
        bad = [int(y) for y, g in zip(years, gap) if g < -1e-12]
        raise SystemExit(f'STOP (L1): the propensity-B household size is below the A path in {bad}.')
    gap = np.maximum(gap, 0.0)                # exact zeros where the two rebased paths coincide (2023-2025)
    hS = B['hist_S'].dropna()
    S_amb = S + gap
    # L1 at TL: the lowest observed census headship of each age group, or propensity B where lower, on the projected
    # age structure (household_headship.py), as a ratio to the 2023 census rates; the speed limit applies below
    import household_headship as HH
    tl_ratio = HH.tl_ratio_path(years, L1_TL_VARIANT)
    S_tl = S * tl_ratio
    S_v410 = float(hS.max())                  # the v4.10 setting (sensitivity): the national 1991 household size
    out['L1'] = dict(subrule='C', variants={v: yy(S_variants[v]['S']) for v in S_variants}, gap=yy(gap),
                     tail=settings.S_TAIL, S_ref=yy(S),
                     S={'reference': yy(S), 'moderate': yy(S + gap / 2.0), 'ambitious': yy(S_amb)},
                     tl=yy(S_tl), tl_ratio=yy(tl_ratio), tl_variant=L1_TL_VARIANT,
                     tl_v410=S_v410, tl_v410_year=int(hS.idxmax()),
                     b_ge_a_every_year=True, source=L1_PROPENSITY_SOURCE,
                     # the fall in households per person at every age against the 2023 census rates, 2050
                     tl_households_per_person_fall=float(1.0 - 1.0 / tl_ratio[-1]),
                     tl_v410_households_per_person_fall=float(1.0 - S[-1] / S_v410),
                     headship=headship_evidence(HH, hS),
                     anchor=f'Stats NZ Medium B household size, rebased on 2023 (2050: S = {S_amb[-1]:.4f}, '
                            f'+{gap[-1]:.4f} on the Reference)')
    # TL1 speed limit: the fastest |dS| per year between consecutive censuses (census-benchmarked households)
    cy = [int(y) for y in B['census'].index
          if TL1_SPEED_CENSUS_WINDOW[0] <= int(y) <= TL1_SPEED_CENSUS_WINDOW[1] and int(y) in hS.index]
    intervals = [dict(y0=a, y1=b, S0=float(hS.loc[a]), S1=float(hS.loc[b]),
                      rate=abs(float(hS.loc[b] - hS.loc[a])) / (b - a)) for a, b in zip(cy[:-1], cy[1:])]
    fastest = max(intervals, key=lambda r: r['rate'])
    i0 = int(np.where(years == TL1_SPEED_START)[0][0])
    path = tl1_path(S, gap, w, years, S_tl, fastest['rate'])
    fast = float(S[i0]) + fastest['rate'] * (years - TL1_SPEED_START)
    binds = [int(y) for y, f_, l_, p_ in zip(years, fast, S_tl, path)
             if y >= TL1_SPEED_START and f_ < l_ - 1e-12 and abs(p_ - f_) < 1e-12]
    v410_reached = TL1_SPEED_START + (S_v410 - float(S[i0])) / fastest['rate']
    out['L1']['tl_speed'] = dict(rate=fastest['rate'], interval=[fastest['y0'], fastest['y1']], start=TL1_SPEED_START,
                                 S_start=float(S[i0]), binding_years=binds,
                                 binds_until=(max(binds) if binds else None),
                                 v410_level_reached=float(v410_reached),
                                 census_years=cy, intervals=intervals, path=yy(path),
                                 v410_path=yy(tl1_path(S, gap, w, years, S_v410, fastest['rate'])),
                                 basis='fastest change of household size between consecutive censuses 1991-2023')

    # ---- L2 Vacancy [B] ----
    v0 = float(B['v_forward'])
    vc = B['vacancy_consistent']
    v_min, y_min = float(vc.min()), int(vc.idxmin())
    import os
    oe = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), FILE_OECD_VACANCY), comment='#')
    sw = oe[oe['country'] == L2_TL_COUNTRY].iloc[0]
    v_tl = float(sw['vacant_incl_seasonal_pct']) / 100.0
    if not 0.0 < v_tl < v_min:
        raise SystemExit(f'STOP (L2): the TL vacancy {v_tl:.4f} is not below the Ambitious {v_min:.4f}.')
    out['L2'] = dict(subrule='B', v={'reference': v0, 'moderate': (v0 + v_min) / 2.0, 'ambitious': v_min}, tl=v_tl,
                     tl_source=dict(file=FILE_OECD_VACANCY, workbook='OECD (2024) Affordable Housing Database, HM1.1',
                                    sheet='HM1.1.2', cell=str(sw['cell_panel_b']), panel='B (vacant dwellings and '
                                    'seasonal/holiday homes)', country=L2_TL_COUNTRY, year=int(sw['year']),
                                    value_pct=float(sw['vacant_incl_seasonal_pct'])),
                     tl_note=L2_TL_NOTE,
                     census_consistent={int(k): float(v) for k, v in vc.items()}, census_consistent_min_year=y_min,
                     census_consistent_2023=float(vc.loc[2023]), floor=L2_VACANCY_FLOOR,
                     anchor=f'{100 * v_min:.2f}% ({y_min} census minimum, one definition)',
                     note=f'Reference = the published 2023 census value {100 * v0:.2f}%; on the consistent definition '
                          f'2023 is {100 * float(vc.loc[2023]):.2f}%')

    # ---- L3 Building lifetime [C] ----
    out['L3'] = dict(subrule='C', d={'reference': 0.0, 'moderate': L3_D_AMBITIOUS / 2.0, 'ambitious': L3_D_AMBITIOUS},
                     tl=dict(d_demolition=1.0, d_surge=1.0), demolition_rate=float(B['demolition_rate']),
                     long_run_residual=float(B['unconsented_rate']),
                     anchor='-40% demolition (Pellan et al. 2024)',
                     tl_note='zero demolition, no redevelopment wave; unconsented additions kept at the long-run rate')

    # ---- L8 Material carbon [A] ----
    # the Ambitious r is the HD q0.15 of the case ratios in every year, each case on its own decarbonisation path
    # (scaling the pooled path by the 2025 r instead would decarbonise the best cases at the pooled mix's
    # rate); the bootstrap interval is computed at 2025 only (estimator)
    cases6, pooled6 = case_ratios(factors_building)
    est6 = hd_estimate(cases6['ratio'].values, HD_Q, bootstrap_B, HD_BOOTSTRAP_SEED)
    if len(cases6) < L8_MIN_CASES or est6['r'] >= 1.0:
        raise SystemExit(f'STOP (L8): n = {len(cases6)}, r = {est6["r"]:.4f}.')
    red_case = case_reductions(settings, factors_building, years)
    by_y, pooled_y = case_paths(factors_building, red_case)
    by_y_all, _ = case_paths(factors_building, red_case, typologies=tuple(typ))
    if not math.isclose(hd_quantile(by_y[int(years[0])]['ratio'].values, HD_Q), est6['r'], rel_tol=1e-12):
        raise SystemExit('STOP (L8): the 2025 per-year estimate differs from the bootstrap estimator.')
    r_amb = np.array([hd_quantile(by_y[int(y)]['ratio'].values, HD_Q) for y in years])
    if np.any(r_amb >= 1.0):
        raise SystemExit(f'STOP (L8): r(y) >= 1 in {[int(y) for y, v in zip(years, r_amb) if v >= 1.0]}.')
    tl6, tl_y = {}, {}
    fb = factors_building.set_index('id')
    for t in typ:
        g = fb[fb['Typology'] == t]
        ind = g[g['duplicate_of'].fillna('') == '']
        evidence = len(ind) >= 2
        sel = {int(y): by_y_all[int(y)][by_y_all[int(y)]['typology'] == t] for y in years}
        own = np.array([float(sel[int(y)]['ratio'].min()) for y in years])
        best_case = [str(sel[int(y)].sort_values('ratio')['id'].iloc[0]) for y in years]
        tl_y[t] = np.minimum(own, r_amb) if evidence else r_amb.copy()
        tl6[t] = dict(n_independent=int(len(ind)), pooled_a13=pooled6.get(t, float(g.groupby('Subtype')['A1-A3'].mean().mean())),
                      own_best_2025=float(own[0]) if evidence else None,
                      own_best_case=sorted(set(best_case)) if evidence else None,
                      own_best=yy(own) if evidence else None, r_2025=float(tl_y[t][0]),
                      rule='min(own best independent case, r_Ambitious) in every year' if evidence else
                           'r_Ambitious (one independent case)')
    # the model's typology A1-A3 path against the case table's pooled path (report only: the ratio is scale-free)
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    model_path = {t: a13[t] - np.asarray(B['RED13_TOT'][t], float) for t in typ}
    pool_vs_model = {t: float(np.max(np.abs(np.array([pooled_y[t][int(y)] for y in years]) / model_path[t] - 1.0)))
                     for t in pooled_y}
    out['L8'] = dict(subrule='A', n=int(len(cases6)), sample_typologies=list(L8_SAMPLE_TYPOLOGIES),
                     cases=cases6.to_dict(orient='records'), pooled_a13=pooled6, a13_2025_pooled=a13,
                     estimator=est6,
                     r={'reference': yy(np.ones(len(years))), 'moderate': yy((1.0 + r_amb) / 2.0), 'ambitious': yy(r_amb)},
                     r_2025={'reference': 1.0, 'moderate': (1.0 + float(r_amb[0])) / 2.0, 'ambitious': float(r_amb[0])},
                     r_report={int(y): float(r_amb[list(years).index(y)]) for y in L8_REPORT_YEARS},
                     tl={t: yy(v) for t, v in tl_y.items()}, tl_2025={t: float(v[0]) for t, v in tl_y.items()},
                     tl_report={t: {int(y): float(v[list(years).index(y)]) for y in L8_REPORT_YEARS} for t, v in tl_y.items()},
                     tl_detail=tl6, by_year_basis='each case on its own decarbonisation path (factors_building_a13_'
                     'reduction.csv, the projection\'s DECARB setting); bootstrap interval at 2025 only',
                     pooled_vs_model_max_rel=pool_vs_model,
                     anchor=f'HD q0.15 of the {len(cases6)} case ratios = {r_amb[0]:.4f} (2025), {r_amb[-1]:.4f} (2050)')
    # check row, report only: the estimator with the apartment case A_1 included (n = 15). A_1 is the
    # one independent apartment case (A_2 is its duplicate_of), so its ratio to the apartment pooled value is ~1 by
    # construction and carries no information on the spread; the adopted sample (n = 14) stays. Per year as L8.
    cases15, _ = case_ratios(factors_building, L8_SAMPLE_TYPOLOGIES + ('Apartments',))
    est15 = hd_estimate(cases15['ratio'].values, HD_Q, bootstrap_B, HD_BOOTSTRAP_SEED)
    by15, _ = case_paths(factors_building, red_case, L8_SAMPLE_TYPOLOGIES + ('Apartments',))
    out['L8']['check_with_A_1'] = dict(n=int(len(cases15)), r=float(est15['r']), ci_lo=est15.get('ci_lo'),
                                       ci_hi=est15.get('ci_hi'), adopted_n=int(len(cases6)), adopted_r=float(r_amb[0]),
                                       r_report={int(y): hd_quantile(by15[int(y)]['ratio'].values, HD_Q)
                                                 for y in L8_REPORT_YEARS},
                                       A_1_ratio=float(cases15.loc[cases15['id'] == 'A_1', 'ratio'].iloc[0]),
                                       note='report only; the adopted estimate keeps n = 14 (Detached, Townhouses)')
    # L8 on the case paths of the run's L10 level: the archetype multiplier m is uniform over the
    # sample (Detached and Townhouses share the single-family archetype) and cancels exactly in the ratios, so the
    # ratios differ only where the L10 class factors act (L10 at TL): x_i(y) = [path_i(y) - sum_k P_ik(y) (1 - c_k(y))]
    # / the same pooled
    cf = l10_class_factor('tl', years)
    if cf:
        import Building_factors as BF
        cp = pd.read_csv(BF.OUT_A13_CLASS_BLD)
        variant = BF.decarb_variant(settings.DECARB_MODE, settings.DECARB_ITEM_CASE)
        cp = cp[cp['Variant'] == (variant or 'horup_item')]
        w10 = l10_weight(years)
        red_tl = pd.DataFrame(0.0, index=factors_building['id'], columns=[int(y) for y in years])
        for k, c in cf.items():
            g = cp[cp['Class'] == k].pivot(index='id', columns='Year', values='A13_kgCO2e_per_m2')
            g = (g.reindex(index=factors_building['id'], columns=[int(y) for y in years]) if variant else
                 pd.DataFrame(np.repeat(g.reindex(index=factors_building['id'])[int(years[0])].to_numpy()[:, None],
                                        len(years), axis=1), index=factors_building['id'], columns=[int(y) for y in years]))
            red_tl = red_tl + g.fillna(0.0) * (w10 * (1.0 - c))[None, :]
        by_t, _ = case_paths(factors_building, red_case + red_tl)
        by_t_all, _ = case_paths(factors_building, red_case + red_tl, typologies=tuple(typ))
        r_tl = np.array([hd_quantile(by_t[int(y)]['ratio'].values, HD_Q) for y in years])
        tl_t = {}
        for t in typ:
            ind = factors_building[(factors_building['Typology'] == t) & (factors_building['duplicate_of'].fillna('') == '')]
            own = np.array([float(by_t_all[int(y)][by_t_all[int(y)]['typology'] == t]['ratio'].min()) for y in years])
            tl_t[t] = np.minimum(own, r_tl) if len(ind) >= 2 else r_tl.copy()
        out['L8']['at_l10_tl'] = dict(
            r={'reference': yy(np.ones(len(years))), 'moderate': yy((1.0 + r_tl) / 2.0), 'ambitious': yy(r_tl)},
            tl={t: yy(v) for t, v in tl_t.items()},
            r_report={int(y): float(r_tl[list(years).index(y)]) for y in L8_REPORT_YEARS},
            basis='the case paths with the L10 class factors at TL (near-zero cement and steel)')

    # ---- L9 Construction-stage carbon [C] ----
    a45 = {t: float(B['MAT_STAGE']['A4-A5'][t].sum()) for t in typ}
    ref45 = a45_reference(years)
    red45 = {t: np.asarray(B['RED45_TOT'][t], float) for t in typ}
    chk = max(float(np.max(np.abs(a45[t] * (1.0 - ref45) - red45[t]))) for t in typ)
    if chk > 1e-9:
        raise SystemExit(f'L9: the model A4-A5 path is not a45_2025 x e^(-0.01 (y - 2025)) (max abs diff {chk:.2e}).')
    out['L9'] = dict(subrule='C', a45_2025=a45, target={lv: yy(a45_target(years, LAMBDA[lv])) for lv in LAMBDA},
                     tl=yy(a45_target(years, 'tl')), reference_check_max_abs=chk,
                     medians_kg_per_m2_yr={k: v for k, (_, v) in L9_MEDIANS.items()},
                     shares=dict(L9_SHARES), cut={lv: l9_cut(LAMBDA[lv]) for lv in LAMBDA} | {'tl': l9_cut('tl')},
                     anchor='site energy -85% (zero-emission site machinery, City of Oslo Climate Agency 2025); A4-A5 split by the '
                            'medians of Kanafani et al. (2023)',
                     caveat='Oslo\'s definition covers machinery inside the site fence (scope 1); applying it to all '
                            'site energy assumes the electricity and heat used on site are decarbonised too',
                     tl_note='A4 and site energy zero (physically attainable: electric machinery and freight exist); '
                             'site waste persists, its material carbon belongs to L8 / L10')

    # ---- L10 Production decarbonisation [C] ----
    if [int(y) for y in years] != list(range(2025, 2051)):
        raise SystemExit('STOP (L10): the projection years are not 2025-2050 (Table S3 is by year 2025-2050).')
    rel, cells = l10_paths(years)
    m_amb = l10_multiplier(years, 'min')
    m_max = l10_multiplier(years, 'max')
    bad = {t: [int(y) for y, v in zip(years, m) if not 0.0 < v <= 1.0 + 1e-12] for t, m in m_amb.items()}
    if any(bad.values()) or any(abs(m[0] - 1.0) > 1e-12 for m in m_amb.values()):
        raise SystemExit(f'STOP (L10): m_Amb outside (0, 1] or m(2025) != 1: {bad}.')
    out['L10'] = dict(subrule='C', archetype=dict(L10_ARCHETYPE), evidence=L10_EVIDENCE,
                      m={'reference': {t: yy(np.ones(len(years))) for t in typ},
                         'moderate': {t: yy((1.0 + m_amb[t]) / 2.0) for t in typ},
                         'ambitious': {t: yy(m_amb[t]) for t in typ}},
                      tl={t: yy(m_amb[t]) for t in typ}, no_policy_max={t: yy(m_max[t]) for t in typ},
                      report={lv: {t: {int(y): float(v[list(years).index(y)]) for y in L10_REPORT_YEARS}
                                   for t, v in m_.items()}
                              for lv, m_ in (('moderate', {t: (1.0 + m_amb[t]) / 2.0 for t in typ}),
                                             ('ambitious', m_amb), ('tl', m_amb), ('no_policy_max', m_max))},
                      table_s3_rel={f'{a} {st}': yy(v) for (a, st), v in rel.items()},
                      cells={f'{a} {st}': {'2025': c[2025], '2050': c[2050]} for (a, st), c in cells.items()},
                      weight='none (scenario path is the timing): m = 1 in 2025-2026, the path from 2027',
                      anchor=L10_EVIDENCE + '; m(2050) = MIN / AVG relative to 2025: '
                             + ', '.join(f'{t} {m_amb[t][-1]:.3f}' for t in typ),
                      archetype_note='author decision: Single family houses for Detached and Townhouses, Multi '
                                     'dwellings for Apartments; the extra decarbonisation is spread evenly across '
                                     'materials (the envelope is reported by archetype only)',
                      tl_note='L10 at TL: the Ambitious envelope m(y) x [(1 - s(y)) + s(y) k] on the cement-based and '
                              'steel classes (near-zero emissions cement and steel), m(y) on every other class',
                      tl_classes={k: dict(k=v, review=L10_CLASS_REVIEW[k]) for k, v in L10_TL_CLASSES.items()},
                      class_review=dict(L10_CLASS_REVIEW), elevator_note=L10_ELEVATOR_NOTE,
                      k=dict(cement=L10_K_CEMENT, steel=L10_K_STEEL,
                             source='IEA (2022) Definitions for near-zero and low-emissions steel and cement, and '
                                    'underlying emissions measurement methodologies: thresholds p. 17 (125 kg CO2-eq/t '
                                    'cement, 100% clinker; 400 kg CO2-eq/t crude steel, 100% iron); BAT reference values '
                                    'p. 22-23 footnote 8, citing IEA (2022) Achieving Net Zero Heavy Industry Sectors in '
                                    'G7 Members (850 kg CO2-eq/t cement; 2,945 kg CO2-eq/t crude steel)'),
                      near_zero_share=dict(milestones={str(k): v for k, v in L10_S_MILESTONES.items()},
                                           path=yy(l10_near_zero_share(years)),
                                           source=L10_S_SOURCE + '; steel takes the same s (assumption)'))

    # ---- L7 Soil-aware planning [C] ----
    soil = {t: float(B['SOIL_INTENSITY'][t]) for t in typ}
    ft = factors_typology.set_index('Typology')
    tl8 = {t: dict(soc_avg=float(ft.loc[t, 'SOC_avg']), soc_low=float(ft.loc[t, 'SOC_low'])) for t in typ}
    out['L7'] = dict(subrule='C', x={'reference': 0.0, 'moderate': L7_X_AMBITIOUS / 2.0, 'ambitious': L7_X_AMBITIOUS},
                     soil_factor_2025=soil, tl={t: v['soc_low'] for t, v in tl8.items()}, tl_detail=tl8,
                     tl_x={t: 1.0 - tl8[t]['soc_low'] / soil[t] for t in typ},
                     anchor='-14.6% soil carbon loss (SOC-aware allocation; Christoforatos, Pickering & Schipper 2026)')

    # ---- L6 Brownfield development [C] ----
    E0 = B['engine_out']['50th']
    s_ref = float(np.sum(E0['soil_free_gfa'][1:]) / np.sum(E0['total'][1:]))
    out['L6'] = dict(subrule='C', s={'reference': s_ref, 'moderate': (s_ref + L6_S_AMBITIOUS) / 2.0,
                                     'ambitious': L6_S_AMBITIOUS}, tl=L6_S_TL, s_ref_basis='the Reference of this run: '
                     'replacement (soil-free) floor area / total floor area built, ratio of sums 2026-2050', context=dict(L6_CONTEXT),
                     anchor='59% of new floor area on previously developed land (England 2018-21, DLUHC 2022)',
                     note='lambda = 0 is the lever off (the Reference); a constant s = s_ref would act in the years whose '
                          'own replacement share is below s_ref',
                     tl_source='DCLG (2010) Land use change statistics England, provisional estimates for 2009: 80% of '
                               'dwellings (including conversions) built on previously developed land, unchanged from 2008 '
                               '(England\'s peak share)')
    out['tl_strength'] = tl_strength(out, years)
    return out


def tl_strength(p, years):
    """Every TLn against the Ambitious level of Ln (at least as strong in every typology and year)."""
    yrs = [int(y) for y in years]
    soil = p['L7']['soil_factor_2025']
    return [
        dict(item='TL4', tl='f = 1', ambitious=str({t: round(v, 4) for t, v in p['L4']['f']['ambitious'].items()}),
             ok=all(1.0 >= v for v in p['L4']['f']['ambitious'].values())),
        dict(item='TL5', tl=str({t: round(v, 4) for t, v in p['L5']['tl'].items()}),
             ambitious=f"r = {p['L5']['r']['ambitious']:.4f}",
             ok=all(v <= p['L5']['r']['ambitious'] for v in p['L5']['tl'].values())),
        dict(item='TL1', tl=f"S 2050 = {by_year(p['L1']['tl_speed']['path'], 2050):.4f} (age-specific headship)",
             ambitious=f"S 2050 = {by_year(p['L1']['S']['ambitious'], 2050):.4f}",
             # against Ambitious on the adoption window, S_ref + w gap (the bound tl1_path applies)
             ok=all(by_year(p['L1']['tl_speed']['path'], y) >= by_year(p['L1']['S_ref'], y)
                    + by_year(p['adoption']['w'], y) * by_year(p['L1']['gap'], y) - 1e-12
                    for y in yrs if y >= TL1_SPEED_START)),
        dict(item='TL2', tl=f"v = {p['L2']['tl']:.4f}", ambitious=f"v = {p['L2']['v']['ambitious']:.4f}",
             ok=p['L2']['tl'] <= p['L2']['v']['ambitious']),
        dict(item='TL3', tl='d = 1 (demolition and surge)', ambitious=f"d = {p['L3']['d']['ambitious']}",
             ok=min(p['L3']['tl'].values()) >= p['L3']['d']['ambitious']),
        dict(item='TL8', tl='by year: ' + str({t: round(v, 4) for t, v in p['L8']['tl_2025'].items()}) + ' (2025)',
             ambitious=f"r(y), {p['L8']['r_2025']['ambitious']:.4f} (2025)",
             ok=all(by_year(p['L8']['tl'][t], y) <= by_year(p['L8']['r']['ambitious'], y) + 1e-15
                    for t in p['L8']['tl'] for y in yrs)),
        dict(item='TL9', tl='A4 and site energy zero, waste as the Reference', ambitious='site energy -85%',
             ok=all(by_year(p['L9']['tl'], y) <= by_year(p['L9']['target']['ambitious'], y) + 1e-15 for y in yrs)),
        dict(item='TL10', tl='Ambitious envelope x near-zero cement and steel (class factors <= 1)',
             ambitious='m(2050) ' + ', '.join(f"{t} {by_year(v, 2050):.3f}" for t, v in p['L10']['m']['ambitious'].items()),
             ok=all(by_year(p['L10']['tl'][t], y) <= by_year(p['L10']['m']['ambitious'][t], y) + 1e-15
                    for t in p['L10']['tl'] for y in yrs)),
        dict(item='TL7', tl=str({t: round(v, 2) for t, v in p['L7']['tl'].items()}),
             ambitious=f"x = {p['L7']['x']['ambitious']}",
             ok=all(p['L7']['tl'][t] <= soil[t] * (1 - p['L7']['x']['ambitious']) for t in soil)),
        dict(item='TL6', tl=f"s = {p['L6']['tl']:.2f}", ambitious=f"s = {p['L6']['s']['ambitious']}",
             ok=p['L6']['tl'] >= p['L6']['s']['ambitious'])]


def stop_checks(p):
    """STOP conditions of the lever parameters (raises SystemExit; resolve() raises the data ones)."""
    weak = [r for r in p['tl_strength'] if not r['ok']]
    if weak:
        raise SystemExit(f'STOP: TL weaker than Ambitious: {weak}')


def by_year(d, year):
    """d[year] whether the keys are int (in memory) or str (after the JSON round trip)."""
    return d[year] if year in d else d[str(year)]


# ============================================================
# NATIVE PARAMETERS AT A LEVEL
# ============================================================
def lam_of(level):
    """lambda of a level: a float in [0, 1], 'moderate' (0.5), 'ambitious' (1), 'reference' (0); 'tl' stays 'tl'."""
    if isinstance(level, str):
        return 'tl' if level == 'tl' else LAMBDA[level]
    lam = float(level)
    if not 0.0 <= lam <= 1.0:
        raise ValueError(f'lambda {lam} outside [0, 1].')
    return lam


def native(p, lever, level, years, l10_tl=False):
    """The native parameter of `lever` at `level` (by typology for L4, L5, L7; by year for L1, L9; by typology and
    year for L8, L10; scalars otherwise). Moderate is the exact midpoint of Reference and Ambitious (lambda = 0.5)."""
    lam = lam_of(level)
    tl = lam == 'tl'
    interp = lambda ref, amb: ref + lam * (amb - ref)
    if lever == 'L4':
        return dict(p['L4']['tl']) if tl else {t: lam * v for t, v in p['L4']['f']['ambitious'].items()}
    if lever == 'L5':
        return dict(p['L5']['tl']) if tl else {t: interp(1.0, p['L5']['r']['ambitious']) for t in p['L5']['tl']}
    if lever == 'L1':
        S = np.array([by_year(p['L1']['S_ref'], int(y)) for y in years])
        gap = np.array([by_year(p['L1']['gap'], int(y)) for y in years])
        return tl1_level(p, years) if tl else S + lam * gap
    if lever == 'L2':
        return p['L2']['tl'] if tl else interp(p['L2']['v']['reference'], p['L2']['v']['ambitious'])
    if lever == 'L3':
        return dict(p['L3']['tl']) if tl else dict(d_demolition=lam * p['L3']['d']['ambitious'],
                                                    d_surge=lam * p['L3']['d']['ambitious'])
    if lever == 'L8':
        q = p['L8']['at_l10_tl'] if (l10_tl and 'at_l10_tl' in p['L8']) else p['L8']
        if tl:
            return {t: np.array([by_year(v, int(y)) for y in years]) for t, v in q['tl'].items()}
        amb = np.array([by_year(q['r']['ambitious'], int(y)) for y in years])
        return {t: interp(1.0, amb) for t in q['tl']}
    if lever == 'L10':
        src = p['L10']['tl'] if tl else p['L10']['m']['ambitious']
        m = {t: np.array([by_year(v, int(y)) for y in years]) for t, v in src.items()}
        return m if tl else {t: interp(1.0, v) for t, v in m.items()}
    if lever == 'L9':
        return a45_target(years, lam)
    if lever == 'L7':
        soil = p['L7']['soil_factor_2025']
        return dict(p['L7']['tl']) if tl else {t: soil[t] * (1.0 - lam * p['L7']['x']['ambitious']) for t in soil}
    if lever == 'L6':
        return p['L6']['tl'] if tl else interp(p['L6']['s']['reference'], p['L6']['s']['ambitious'])
    raise ValueError(lever)


# ============================================================
# LEVER FUNCTIONS (each returns new inputs)
# ============================================================
def l4_size(size_base, olf_y, S, f, w):
    """L4: size_t(y) = occ_t(y) + [1 - f_t w(y)] (size_base_t(y) - occ_t(y)), occ_t = S(y) OLF_t(y), with the size and
    OLF after L5 (size_base = size_ref x the L5 factor). Where size_base <= occ the typology / year is held at
    size_base (never below the occupied area). Returns (size {typology: array}, held {typology: bool array})."""
    S = np.asarray(S, float)
    size, held = {}, {}
    for t in size_base:
        occ = S * np.asarray(olf_y[t], float)
        ref = np.broadcast_to(np.asarray(size_base[t], float), S.shape)
        h = ref <= occ
        size[t] = np.where(h, ref, occ + (1.0 - float(f[t]) * w) * (ref - occ))
        held[t] = h
    return size, held


def tl1_level(p, years):
    """The L1 at TL household-size level by model year: p['L1']['tl'] as a by-year dict (the resolved path), an array
    (a Monte Carlo draw's own path) or a number (the v4.10 sensitivity, held)."""
    v = p['L1']['tl']
    if isinstance(v, dict):
        return np.array([by_year(v, int(y)) for y in years], float)
    v = np.asarray(v, float)
    return np.full(len(years), float(v)) if v.ndim == 0 else v


def headship_evidence(HH, hist_S):
    """The census headship evidence of L1 at TL for levers.json (household_headship.py): calibration, rates by census,
    TL rates and their sources by knot, the common-basis check, the back-check, the share comparison."""
    cal = HH.census_calibration()
    rates = HH.census_rates()
    R, src, hb = HH.tl_rates(L1_TL_VARIANT)
    cb = HH.common_basis_check()
    bc, more, scale = HH.back_check(hist_S)
    w1, fell = HH.one_person_direction()
    paths = {v: HH.tl_paths(v) for v in ('Low', 'Medium', 'High')}
    tbl = lambda df: {str(c): {str(i): float(df.loc[i, c]) for i in df.index} for c in df.columns}
    return dict(calibration={str(c): v for c, v in cal.items()}, rates=tbl(rates),
                tl_rates=tbl(R), tl_source={str(c): {str(i): str(src.loc[i, c]) for i in src.index} for c in src.columns},
                b_adjusted=tbl(hb), common_basis=dict(normalised=tbl(cb['normalised']),
                                                       people_per_household=cb['people_per_household'],
                                                       f_projection=cb['f_projection'], g_projection=cb['g_projection']),
                share_diff_pp=tbl(cb['share_diff_pp']),
                back_check=dict(table=tbl(bc.drop(columns=['more_shared']).astype(float)),
                                more_shared_year=more, matching_scale=scale,
                                best_observed_since_1991=more is None),
                one_person_share_fell_every_age_15plus=fell,
                paths={v: tbl(t) for v, t in paths.items()},
                direction={a: ('fell' if rates.loc[a, 2023] < rates.loc[a, 2013] else 'rose')
                           for a in rates.index if a != '0-14'})


def tl1_path(S_ref, gap, w, years, level, rate, start=TL1_SPEED_START):
    """TL1 under the speed limit: max(min(S_ref(start) + rate (t - start), level), S_ref + w gap) from `start`; the
    Reference before it. S_ref is the run's own Reference household size (a Monte Carlo draw's)."""
    years = np.asarray(years, float)
    S_ref = np.asarray(S_ref, float)
    i0 = int(np.where(years == start)[0][0])
    fast = np.minimum(S_ref[i0] + rate * (years - start), level)
    return np.where(years >= start, np.maximum(fast, S_ref + w * np.asarray(gap, float)), S_ref)


def l1_households(hh, S_ref, S_target, w):
    """L1: S(y) = S_ref(y) + w(y) (S_target(y) - S_ref(y)); households = hh x S_ref / S (w = 0 returns hh exactly)."""
    hh = np.asarray(hh, float)
    S_ref = np.asarray(S_ref, float)
    S = S_ref + w * (np.asarray(S_target, float) - S_ref)
    return hh * (S_ref / S), S


def l2_vacancy(v0, v_level, w):
    """L2: stock-wide vacancy v(y) = v0 + w(y) (v_level - v0)."""
    return v0 + w * (v_level - v0)


def l3_rates(rate_demol, rate_unc, long_run_residual, d_demolition, w, d_surge=None):
    """L3: demolition rate x (1 - w d); the recent-surge component of the residual path (rate_unc - long-run
    residual) x (1 - w d_surge); the long-run residual (unconsented additions) untouched."""
    d_surge = d_demolition if d_surge is None else d_surge
    return (float(rate_demol) * (1.0 - w * float(d_demolition)),
            float(long_run_residual) + (np.asarray(rate_unc, float) - long_run_residual) * (1.0 - w * float(d_surge)))


def l8_intensity(intensity, a13_2025, red13, r, w):
    """L8: intensity_t(y) - w(y) (1 - r_t(y)) (A1-A3_t,2025 - red13_t(y)): only the A1-A3 term is scaled, so
    A1-A3(y) = [1 - w (1 - r(y))] (A1-A3_2025 - reduction(y)) and decarbonisation still applies on top (r scalar or by
    year)."""
    return {t: np.asarray(intensity[t], float)
            - w * (1.0 - np.asarray(r[t], float)) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in intensity}


def l10_intensity(intensity, a13_2025, red13, r8_eff, m_eff):
    """L10: intensity_t(y) - (1 - m_t(y)) x r8_eff_t(y) (A1-A3_t,2025 - red13_t(y)): the A1-A3 term after L8
    (r8_eff = 1 - w (1 - r8); 1 without L8) times the production multiplier m (m_eff with its own weight)."""
    return {t: np.asarray(intensity[t], float) - (1.0 - np.asarray(m_eff[t], float)) * np.asarray(r8_eff[t], float)
            * (float(a13_2025[t]) - np.asarray(red13[t], float)) for t in intensity}


def l10_events(events, events_a13, m_eff):
    """L10 on the in-window replacement and repaint events: the A1-A3 component of the kernel (events_a13) times m(j)
    of the calendar year j of the event; the A4-A5 and C1-C4 components unchanged."""
    return {t: np.asarray(events[t], float) + np.asarray(events_a13[t], float)
            * (np.asarray(m_eff[t], float) - 1.0)[None, :] for t in events}


def a13_path(a13_2025, red13, r, w, m=None):
    """A1-A3 intensity (kg/m2) by typology and year under L8 (r = 1: the baseline path) and L10 (m None: 1)."""
    return {t: (1.0 - w * (1.0 - np.asarray(r[t], float))) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            * (1.0 if m is None else np.asarray(m[t], float)) for t in a13_2025}


def l9_delta(a45_2025, years, target, w):
    """L9: change of the A4-A5 intensity (kg/m2): a45_2025 x w (target - ref), ref = e^(-0.01 (y - 2025))."""
    ref = a45_reference(years)
    return {t: float(a45_2025[t]) * w * (np.asarray(target, float) - ref) for t in a45_2025}


def a45_path(a45_2025, years, target=None, w=None):
    """A4-A5 intensity (kg/m2) by typology and year (target None: the reference path)."""
    ref = a45_reference(years)
    f = ref if target is None else ref + w * (np.asarray(target, float) - ref)
    return {t: float(a45_2025[t]) * f for t in a45_2025}


def _add(d, delta):
    return {t: np.asarray(d[t], float) + np.asarray(delta[t], float) for t in d}


def active(levels):
    """{lever: lambda | 'tl'} of the levers that are on (lambda > 0 or 'tl')."""
    out = {}
    for L, x in levels.items():
        lam = lam_of(x)
        if lam == 'tl' or lam > 0.0:
            out[L] = lam
    return out


def inputs(base, p, levels, ramp_name=None):
    """engine.forward inputs and households for the levers in `levels` ({lever: 'moderate' | 'ambitious' | 'tl' |
    lambda}); a lever not in `levels` (or at lambda 0) keeps the very objects of the Reference run.
    base: pathways.base_context (Reference inputs of one projection state or Monte Carlo draw). Returns (fi, info);
    info['hh'] the households, info['tl'] the levers at Level 4 (re-occupation of the TL1 / TL2 releases)."""
    unknown = set(levels) - set(LEVERS)
    if unknown:
        raise ValueError(f'Unknown lever(s) {unknown}.')
    lv = active(levels)
    fi = dict(base['fwd_inputs'])
    years = base['years']
    typ = list(base['typ'])
    w = ramp_named(years, ramp_name)
    hh, S = base['hh'], np.asarray(base['pop'], float) / np.asarray(base['hh'], float)
    info = dict(w=w, l4_held=None, levels=dict(lv), tl=tuple(L for L in LEVERS if lv.get(L) == 'tl'),
                releases=releases_dwellings(levels))
    # L1 household size (the Reference S plus the gap to the propensity-B path, the draw's own gap in the pathway Monte
    # Carlo; L1 at TL: the age-specific headship path, a Monte Carlo draw's own)
    if 'L1' in lv:
        gap = np.array([by_year(p['L1']['gap'], int(y)) for y in years])
        if lv['L1'] == 'tl' and ramp_name != TL_FROM2027:
            # the speed limit replaces the window (the path is the target, at full weight)
            target = tl1_path(S, gap, w, years, tl1_level(p, years), p['L1']['tl_speed']['rate'])
            hh, S = l1_households(base['hh'], S, target, np.ones(len(years)))
        else:
            if lv['L1'] == 'tl':                      # never weaker than Ambitious (a Monte Carlo draw's own S)
                target = np.maximum(tl1_level(p, years), S + gap)
            else:
                target = S + lv['L1'] * gap
            hh, S = l1_households(base['hh'], S, target, w)
    # L5 design density: OLF and dwelling size x k2(y), k2 = 1 - w (1 - r_t)
    k2 = None
    if 'L5' in lv:
        r2 = native(p, 'L5', lv['L5'], years)
        k2 = {t: 1.0 - w * (1.0 - float(r2[t])) for t in typ}
        fi['olf'] = {t: float(base['olf'][t]) * k2[t] for t in typ}
        fi['size'] = {t: np.asarray(base['size_ref'][t], float) * k2[t] for t in typ}
    # L4 dwelling size: a share f of the extra-space margin after L5
    if 'L4' in lv:
        olf_y = fi['olf'] if k2 is not None else {t: np.full(len(years), float(base['olf'][t])) for t in typ}
        size_b = fi['size'] if k2 is not None else {t: np.broadcast_to(np.asarray(base['size_ref'][t], float),
                                                                       (len(years),)) for t in typ}
        fi['size'], info['l4_held'] = l4_size(size_b, olf_y, S, native(p, 'L4', lv['L4'], years), w)
    # L2 vacancy
    if 'L2' in lv:
        fi['v'] = l2_vacancy(base['v0'], native(p, 'L2', lv['L2'], years), w)
    # L3 building lifetime
    if 'L3' in lv:
        d = native(p, 'L3', lv['L3'], years)
        fi['rate_demol'], fi['rate_unc'] = l3_rates(base['rate_demol'], base['rate_unc'], base['long_run_residual'],
                                                    d['d_demolition'], w, d['d_surge'])
    # L8 material carbon
    r6 = {t: 1.0 for t in typ}
    if 'L8' in lv:
        r6 = native(p, 'L8', lv['L8'], years, l10_tl=lv.get('L10') == 'tl')   # L8 on the L10 level's case paths
        for k in ('intensity', 'intensity_upfront'):
            fi[k] = l8_intensity(fi[k], base['a13_2025'], base['red13'], r6, w)
    # L10 production decarbonisation: the A1-A3 term after L8 x m(y) (no logistic weight: the scenario path is the
    # timing; m = 1 up to 2026), on construction and on the A1-A3 component of the in-window events
    m10, q10, prod2050 = None, None, None
    if 'L10' in lv:
        w10 = l10_weight(years)
        m10 = {t: 1.0 - w10 * (1.0 - v) for t, v in native(p, 'L10', lv['L10'], years).items()}
        cls_eff = {k: 1.0 - w10 * (1.0 - c) for k, c in l10_class_factor(lv['L10'], years).items()}
        q10, corr = l10_chain(base, m10, cls_eff, typ)
        r8_eff = {t: 1.0 - w * (1.0 - np.asarray(r6[t], float)) for t in typ}
        for k in ('intensity', 'intensity_upfront'):
            fi[k] = l10_intensity(fi[k], base['a13_2025'], base['red13'], r8_eff, q10)
        if fi.get('events') is not None:
            if base.get('events_a13') is None:
                raise SystemExit('L10: the context has no A1-A3 event kernel (events_a13).')
            fi['events'] = l10_events(fi['events'], base['events_a13'], m10)
            for t in typ:                             # the class factors on the class kernels (exact zeros at c = 1)
                for k, f in corr[t].items():
                    fi['events'][t] = fi['events'][t] + np.asarray(base['events_a13_class'][t][k], float) * f[None, :]
        prod2050 = dict(m={t: float(v[-1]) for t, v in m10.items()}, c={k: float(c[-1]) for k, c in cls_eff.items()})
    # L9 construction-stage carbon
    target45 = None
    w9 = w
    if 'L9' in lv:
        target45 = native(p, 'L9', lv['L9'], years)
        d45 = l9_delta(base['a45_2025'], years, target45, w9)   # the common adoption window
        for k in ('intensity', 'intensity_upfront'):
            fi[k] = _add(fi[k], d45)
    # L7 soil-aware planning: soil factor by year
    soil_path = None
    if 'L7' in lv:
        lev = native(p, 'L7', lv['L7'], years)
        soil_path = {t: float(base['soil'][t]) + w * (float(lev[t]) - float(base['soil'][t])) for t in typ}
        ds = {t: soil_path[t] - float(base['soil'][t]) for t in typ}
        for k in ('intensity', 'intensity_upfront'):
            fi[k] = _add(fi[k], ds)
        fi['soil'] = soil_path
    # L6 brownfield development
    if 'L6' in lv:
        fi['brownfield_share'] = np.full(len(years), float(native(p, 'L6', lv['L6'], years)))
        fi['brownfield_w'] = w
    if releases_dwellings(levels):
        fi['clip_soil_share'] = True                  # zero-building years possible in runs that release dwellings
    info.update(hh=hh, S=S, r6=r6, m10=m10, q10=q10, prod2050=prod2050,
                a13=a13_path(base['a13_2025'], base['red13'], r6, w, q10),
                a45=a45_path(base['a45_2025'], years, target45, w9), soil_path=soil_path,
                a45_parts=l9_parts(base['a45_2025'], years, lv.get('L9'), w9))
    return fi, info


def pathway_levers(pathway, setting):
    """{lever: setting} of a strategy ('S1'..'S3') or of the Pathway (PATHWAY: every lever); a projection variant id
    such as 'REF': no lever."""
    if pathway in N.SCENARIOS:
        return {}
    levers = LEVERS if pathway == PATHWAY else STRATEGIES[pathway]
    return {L: setting for L in levers}


def label(levels):
    """'none' for no lever; otherwise e.g. 'L4:moderate+L2:tl' (lambda levels as 'L5:0.3')."""
    fmt = lambda x: x if isinstance(x, str) else f'{float(x):g}'
    return '+'.join(f'{k}:{fmt(levels[k])}' for k in LEVERS if k in levels) or 'none'


def key(levels, ramp_name=None):
    """Cache key of a lever setting (a run is a pure function of it): the active (lever, lambda | 'tl') and the ramp."""
    lv = active(levels)
    return tuple((L, lv[L]) for L in LEVERS if L in lv), ramp_name or ADOPTION_ADOPTED


# ============================================================
# THEORETICAL LIMIT TL: Level 4 of every lever -- a thought experiment, not a pathway
# ============================================================
TL_COMPONENTS = tuple(f'TL{k}' for k in range(1, 11))
TL_NAMES = {k: N.TL[k] for k in TL_COMPONENTS}
TL_LEVER = {f'TL{k}': f'L{k}' for k in range(1, 11)}
TL_RELEASE_ITEMS = ('TL1', 'TL2')       # their released dwellings are re-occupied (pathways.reoccupation)


def releases_dwellings(levels):
    """True if and only if the run releases dwellings: TL1 or TL2 (TL_RELEASE_ITEMS) at 'tl'. The one
    predicate that chooses the re-occupation pool accounting (pathways.run), the zero-building soil clip and the
    checks of release runs; a run that releases nothing (the Reference, the Pathways, any other lever at TL) absorbs
    the starting surplus and the overbuild along the logistic to 2035. Choosing the pool for any lever at 'tl' would
    shift the timing of building (+84.6 kt with an otherwise neutral TL item; lever_audit.md check 7)."""
    return any(lam_of(levels[TL_LEVER[c]]) == 'tl' for c in TL_RELEASE_ITEMS if TL_LEVER[c] in levels)
TL_INSTANT_LABEL = 'TL-from2027'
TL_DISCLAIMER = ('TL is the Theoretical Limit, a thought experiment, not a pathway: every lever at Level 4 ('
                 + TL_RULE.split(' = ', 1)[1].rstrip('.') + '), adopted by 2035 (L10 on its own scenario path, L1 at '
                 'the census speed limit), combining best observed attributes of different '
                 'buildings and places; not a proposal or a feasible pathway (potentials hierarchy: theoretical > '
                 'technical > realisable).')
TL_BAU_NOTE = ('The adopted decarbonisation applies in TL as in every run (A1-A3 item paths of Horup et al. 2025; A4-A5 '
               'e^(-0.01 (t - 2025)); L9 at TL sets transport and site energy to zero).')


def tl_levels(comps, base_setting='moderate'):
    """{lever: level} of a TL-family run: the levers of comps (TL1..TL10) at 'tl', the others at base_setting
    ('moderate': the Moderate Pathway, the base of the TL waterfall and of its Shapley game; 'ambitious': the
    Ambitious Pathway;
    'reference': the base of the per-lever TL Shapley game of Fig6 and of the Fig5c waterfall)."""
    out = {} if base_setting == 'reference' else {L: base_setting for L in LEVERS}
    out.update({TL_LEVER[c]: 'tl' for c in comps})
    return out




def pct(x, nd=1):
    return f'{100 * x:.{nd}f}%'


# The level rule (Table 1 'rule' column): Reference = current practice held (2023 / 2025);
# Moderate = the exact midpoint of Reference and Ambitious; Ambitious = a documented frontier (a value achieved in New
# Zealand or elsewhere, an official projection, a peer-reviewed scenario or a documented requirement, cited); TL = the logical bound where the lever has one, otherwise the best value observed.
LEVEL_RULE = {
    'L1': ('2023 living arrangements held (Stats NZ propensity A)', 'official projection: Stats NZ propensity B',
           'best observed: the lowest census headship of each age group (2013-2023), or propensity B where lower, '
           'on the projected age structure'),
    'L2': ('2023 census vacancy', 'achieved in NZ: the 1996 census minimum',
           'best observed internationally: lowest nationwide rate in the OECD table, Switzerland 1.31% (2022)'),
    'L3': ('current demolition and surge', 'peer-reviewed scenario: -40% demolition (Pellan et al. 2024)',
           'logical bound: no demolition'),
    'L4': ('2023-2025 dwelling sizes', 'achieved in NZ: the smallest annual mean consented size',
           'logical bound: zero space beyond the occupied area'),
    'L5': ('case-study typology medians', 'achieved: the top-15% case-study design density (HD q0.15)',
           'best observed: the densest case-study design'),
    'L6': ('the Reference share on previously developed land', 'achieved abroad: England 2018-21 (DLUHC 2022)',
           'best observed internationally: England\'s peak share, 80% (2008-2009; DCLG 2010)'),
    'L7': ('area-weighted soil orders', 'peer-reviewed scenario: SOC-aware allocation (-14.6%)',
           'logical bound: the lowest soil order'),
    'L8': ('pooled case-study A1-A3', 'achieved: the top-15% case-study A1-A3 (HD q0.15)',
           'best observed: the lowest-carbon NZ case study'),
    'L9': ('business-as-usual A4-A5, every part -1%/yr (Resch et al. 2021)',
           'achieved: zero-emission site machinery, site energy -85% (City of Oslo Climate Agency 2025)',
           'physically attainable: zero-emission transport and site energy; site waste as the Reference'),
    'L10': ('the Horup et al. (2025) nine-scenario average production paths (S4 item paths)',
            'documented scenario: the lowest of the 9 prospective backgrounds by year (Horup et al. 2025, Table S3)',
            'documented scenario bound: the Ambitious envelope with near-zero emissions cement and steel (IEA 2022 '
            'definitions; near-zero share ' + L10_S_TEXT + ')')}


def lever_table(p):
    """Table 1 of the paper: one row per lever with its sub-rule and anchor, and the native parameter at Moderate,
    Ambitious and TL (LEVERS_TABLE.md)."""
    rows = []
    t3 = lambda d: ', '.join(f'{k} {v:.3f}' for k, v in d.items())
    for L in LEVERS:
        q = p[L]
        if L == 'L4':
            mod, amb, tl = 'f = ' + t3(q['f']['moderate']), 'f = ' + t3(q['f']['ambitious']), 'f = 1 (size = occupied area)'
        elif L == 'L8':
            e = q['estimator']
            rr = q['r']['ambitious']
            mod = 'r(y): ' + ', '.join(f"{y} {(1 + by_year(rr, y)) / 2:.4f}" for y in L8_REPORT_YEARS)
            amb = ('r(y): ' + ', '.join(f"{y} {by_year(rr, y):.4f}" for y in L8_REPORT_YEARS)
                   + f" (2025: 95% CI {e['ci_lo']:.3f}-{e['ci_hi']:.3f}, n = {q['n']})")
            tl = '; '.join(f"{t} " + ', '.join(f"{y} {by_year(v, y):.3f}" for y in (2025, 2050))
                           for t, v in q['tl'].items())
        elif L == 'L10':
            rep_ = q['report']
            fmt = lambda d: '; '.join(f"{t} " + ', '.join(f"{y} {by_year(v, y):.3f}" for y in L10_REPORT_YEARS)
                                      for t, v in d.items())
            mod, amb = 'm(y): ' + fmt(rep_['moderate']), 'm(y): ' + fmt(rep_['ambitious'])
            tl = (f"m(y) as Ambitious x [(1 - s) + s k] on cement-based classes (k = {L10_K_CEMENT:.3f}: CONCRETE, "
                  f"REINFORCED CONCRETE, FIBRE CEMENT, PLASTER) and steel (k = {L10_K_STEEL:.3f}: STEEL and the "
                  f"elevator, {L10_ELEVATOR_NOTE}); s = " + ', '.join(f'{k} {v:.2f}' for k, v in L10_S_MILESTONES.items())
                  + ' (linear; 0 through 2026)')
        elif L == 'L5':
            e = q['estimator']
            mod = f"r = {q['r']['moderate']:.4f}"
            amb = f"r = {q['r']['ambitious']:.4f} (95% CI {e['ci_lo']:.3f}-{e['ci_hi']:.3f}, n = {q['n']})"
            tl = 'r = ' + t3(q['tl'])
        elif L == 'L1':
            mod = f"S 2050 = {by_year(q['S']['moderate'], 2050):.4f}"
            amb = f"S 2050 = {by_year(q['S']['ambitious'], 2050):.4f} (Reference {by_year(q['S_ref'], 2050):.4f})"
            tl = (f"S 2050 = {by_year(q['tl_speed']['path'], 2050):.4f} (lowest observed headship by age group, or "
                  f"propensity B where lower; speed-limited)")
        elif L == 'L2':
            src = q['tl_source']
            mod, amb = pct(q['v']['moderate'], 2), pct(q['v']['ambitious'], 2)
            tl = (f"{pct(q['tl'], 2)} ({src['country']} {src['year']}: 61,496 empty dwellings on 1 June 2022, share of "
                  f"the total stock incl. single-family homes; OECD HM1.1, sheet {src['sheet']}, cell {src['cell']}, "
                  f"panel B)")
        elif L == 'L3':
            mod, amb, tl = f"d = {q['d']['moderate']:.2f}", f"d = {q['d']['ambitious']:.2f}", 'no demolition, no surge'
        elif L == 'L9':
            sh = q['shares']
            parts = (f"transport / site energy / waste = {sh['transport']:.2f} / {sh['site_energy']:.2f} / "
                     f"{sh['waste']:.2f} of A4-A5, each -1%/yr")
            mod = f"site energy -{100 * q['cut']['moderate']['site_energy']:.1f}%; " + parts
            amb = f"site energy -{100 * q['cut']['ambitious']['site_energy']:.0f}%; " + parts
            tl = 'transport and site energy zero, waste as the Reference; ' + parts
        elif L == 'L7':
            mod, amb = f"x = {q['x']['moderate']:.3f}", f"x = {q['x']['ambitious']:.3f}"
            tl = ', '.join(f'{t} {v:.1f}' for t, v in q['tl'].items()) + ' kg CO2e/m2 (lowest soil order)'
        else:
            mod = f"s = {q['s']['moderate']:.3f} (s_ref {q['s']['reference']:.3f})"
            amb, tl = f"s = {q['s']['ambitious']:.2f}", f"s = {q['tl']:.2f} (England 2009, DCLG 2010)"
        rows.append(dict(item=f'{L} {LEVER_NAMES[L]}', strategy=f'{LEVER_STRATEGY[L]} {STRATEGY_NAMES[LEVER_STRATEGY[L]]}',
                         subrule=q['subrule'], anchor=q['anchor'], parameter=LEVER_PARAMETER[L], band=BAND_TARGET[L],
                         moderate=mod, ambitious=amb, tl=tl,
                         rule='Reference: {}; Ambitious: {}; TL: {}'.format(*LEVEL_RULE[L])))
    empty = [(r['item'], k) for r in rows for k, v in r.items() if not str(v).strip()]
    if empty:
        raise SystemExit(f'STOP: Extended Data Table 1 has empty cells: {empty}')
    return rows
