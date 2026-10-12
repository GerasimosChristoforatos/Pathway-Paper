"""
LEVERS: pure functions, lever -> modified engine.forward inputs (MODEL v2.1.0: the final lever set)
==================================================================================================
Each lever changes one or two inputs of engine.forward (the `fwd_inputs` dict built in
projection.main(), and the households path; docs/HOOKS.md) and nothing else. No function reads
module globals of projection, no file is written and no argument is modified: every function
returns new objects (or, for a lever that is off, the input object itself, so that the identity run
is the reference call of projection.main()).

Years: model index 0 = 2025, 1 = 2026 (observed; no lever touches it). A lever at full strength
moves a quantity from its baseline b to its target x as b + w(y) (x - b), with the adoption path
(normalised logistic ramp)

    s(y) = 1 / (1 + exp(-k (y - m))),  w(y) = (s(y) - s(2026)) / (s(E) - s(2026))  for 2026 <= y <= E;
    w = 1 after E,  with  W = E - 2026,  m = 2026 + W/2,  k = ln(81) / (2W/3)

one rule for every window (adoption_window): 10% -> 90% of s within the middle two-thirds of the
window. Adopted E = 2035 (full roll-out by 2035 following RECC, Pauliuk et al. 2024); sensitivities
'by2030' and 'by2045'. The business-as-usual decarbonisation (A1-A3 item paths of Horup et al. 2025,
A4-A5 e^(-0.01 (t - 2025))) applies in every run. Typology shares stay at the Reference (held) mix.

Levers (settings Moderate and Ambitious; naming.LEVERS) and pathways (naming.PATHWAYS):
  P1 Space per person   L1 Dwelling size          size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)),
                                                  occ_t = S(y) OLF_t; never below occ_t
                        L2 Household occupancy    S(y) = S_ref(y) + w(y) (S_target(y) - S_ref(y)); households
                                                  = population / S
  P2 Existing stock     L3 Vacancy                stock-wide vacancy v(y) = v0 + w (v* - v0)
                        L4 Overbuild absorption   the 2026 overbuild absorbed at rate a (engine.market_excess)
                        L5 Building lifetime      demolition and the recent-surge component x (1 - w d)
                           extension
  P3 Construction       L6 Material carbon        A1-A3_t(y) = [1 - w (1 - r)] (A1-A3_t,2025 - reduction_t(y))
                        L7 Construction-stage     A4-A5 factor(y) = ref(y) + w(y) (target(y) - ref(y)),
                           carbon                 ref(y) = e^(-0.01 (y - 2025))
  P4 Land               L8 Soil-aware planning    soil carbon loss per m2 of footprint x (1 - w x)
                        L9 Brownfield development target share s of all new floor area on previously developed
                                                  land: soil-free floor area += w max(0, s total - replacement)
  P5 Combined           every lever
Only population growth is untargeted. Resolved values: outputs/data/pathways/levers.json.
"""
import math

import numpy as np
import pandas as pd

import engine
import naming as N

LEVERS = tuple(N.LEVERS)                          # ('L1', ..., 'L9')
SETTINGS = tuple(N.SETTINGS)                      # ('moderate', 'ambitious')
SETTING_NAMES = dict(N.SETTINGS)
LEVER_NAMES = dict(N.LEVERS)
PATHWAYS = dict(N.PATHWAY_LEVERS)                 # P1-P4 -> their levers; P5 = every lever
PATHWAY_NAMES = dict(N.PATHWAYS)
LEVER_PATHWAY = {L: P for P, ls in PATHWAYS.items() for L in ls}
# demand band(s) each lever targets (naming.BANDS; LEVERS_TABLE.md)
BAND_TARGET = {
    'L1': 'Extra space (and the dwelling size of every band except Population growth)',
    'L2': 'Smaller households (and the number of households of every band)',
    'L3': 'Vacancy (including the change in the vacancy rate)',
    'L4': '2026 overbuild',
    'L5': f"{N.BANDS['replacement']} and {N.BANDS['redevelopment']}",
    'L6': 'None: carbon per m2 (A1-A3) of every band',
    'L7': 'None: carbon per m2 (A4-A5) of every band',
    'L8': 'None: soil carbon loss per m2 of every soil-bearing band',
    'L9': 'None: the soil-bearing share of every band'}
LEVER_PARAMETER = {'L1': 'size (engine.forward), per typology and year', 'L2': 'hh (households = population / S)',
                   'L3': 'v (stock-wide vacancy rate)', 'L4': 'join, join_redev (engine.market_excess absorption)',
                   'L5': 'rate_demol, rate_unc (recent-surge component)',
                   'L6': 'intensity, intensity_upfront (A1-A3 term only)',
                   'L7': 'intensity, intensity_upfront (A4-A5 term only)',
                   'L8': 'soil (factor by year) and the soil term of intensity, intensity_upfront',
                   'L9': 'brownfield_share, brownfield_w (soil-free floor area)'}

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
assert RAMP_MID == 2030.5 and RAMP_K == math.log(81.0) / 6.0    # the adopted path of model-v1.0.0, bit for bit
ADOPTION_ADOPTED = 'by2035'
ADOPTION_BY2045 = adoption_window(2045)    # sensitivity (P5 only): midpoint 2035.5, k = ln(81) / (38/3)
ADOPTION_BY2030 = adoption_window(2030)    # sensitivity (P5 only): midpoint 2028, k = ln(81) / (8/3)
ADOPTION_SENSITIVITIES = (ADOPTION_BY2030, ADOPTION_BY2045)
RAMP_BASIS = ('full roll-out by 2035 following RECC (Pauliuk et al. 2024, J. Ind. Ecol. 28, 1699: circular-economy '
              'strategies fully implemented by 2035)')
ATTACHED = ('Townhouses', 'Apartments')
DETACHED = 'Detached'

# ---------------------------------------------------------------------------
# PARAMETERS (author decisions, MODEL v2.1.0; sources in SOURCES)
# ---------------------------------------------------------------------------
# L1: share f of the space above the occupied area (S x OLF) removed from new dwellings
L1_F = {'moderate': 0.25, 'ambitious': 0.50}
L1_REPORT_YEARS = (2035, 2050)
L1_BENCHMARKS = {'Pellan2024': -0.065, 'Pauliuk2024_LEMD_EU_UK': 31.2 / 37.7 - 1.0}
# L2: household size target. Moderate: the Stats NZ household-size variant with the largest household size,
#     identified by its S path (projection.HH_SIZE_VARIANT run; resolve() checks it is the largest);
#     Ambitious: S held at the highest value of that variant's path (author decision, MODEL v2.1.0)
L2_VARIANTS = ('Low', 'Medium', 'High')
L2_MODERATE_VARIANT = 'High'
# L3: stock-wide vacancy target v*; Moderate = midpoint of the 1986-2023 census range on a consistent
#     definition, Ambitious = its minimum (1996)
L3_V_STAR = {'moderate': 0.047, 'ambitious': 0.040}
L3_VACANCY_FLOOR = 0.040        # implied vacancy must never fall below this (check)
# L4: the 2026 overbuild absorbed (the absorption sensitivities of the projection, OVERBUILD_ABSORPTION)
L4_ABSORPTION = {'moderate': 0.10, 'ambitious': 0.20}
# L5: reduction d of demolition and of the recent replacement surge (Pellan et al. 2024: 150,000 -> 90,000)
L5_D = {'moderate': 0.20, 'ambitious': 0.40}
# L6: target ratio r = Harrell-Davis quantile at q of the scale-free case ratios
#     x_i = A1-A3_i / pooled A1-A3 of the case's typology (independent detached and townhouse cases)
L6_Q = {'moderate': 0.25, 'ambitious': 0.15}
L6_SAMPLE_TYPOLOGIES = ('Detached', 'Townhouses')
L6_MIN_CASES = 10
L6_BOOTSTRAP_B = 10_000
L6_BOOTSTRAP_SEED = 20261008
L6_CI = 0.95
# L7: A4-A5 factor relative to 2025; reference e^(-0.01 (y - 2025)) (Resch et al. 2021, the adopted path)
L7_REF_RATE = 0.01
L7_TARGET = {'moderate': 'halving by 2050: e^(-(ln 2 / 25)(y - 2025))', 'ambitious': 'linear to zero in 2050: 1 - (y - 2025) / 25'}
# L8: reduction x of soil carbon loss per m2 of footprint (Christoforatos, Pickering & Schipper 2026: SOC-aware
#     allocation of the same developed area, 14.6% less SOC loss than business as usual; Moderate half of it)
L8_X = {'moderate': 0.073, 'ambitious': 0.146}
L8_PUBLISHED_REDUCTION = 0.146
# L9: target share s of ALL new floor area on previously developed land (UK DLUHC 2022: England 2018-21 average
#     59%; North East, the lowest English region, 41%; London, the highest, 89%)
L9_S = {'moderate': 0.41, 'ambitious': 0.59}
L9_ENGLAND = dict(england_2020_21=0.66, england_3yr=0.59, north_east=0.41, london=0.89)
# The denser typology mix (lever of pathways_v2, removed in pathways_v3.1; never numbered in the release)
DENSER_MIX_V2_NOTE = dict(
    text=(f'The {N.DENSER_MIX} was not carried forward: within the embodied-carbon scope a denser mix raises '
          'A1-A3 per m2 (attached typologies carry more per m2), while its benefits (infrastructure, operational '
          'energy, land) are outside the scope.'),
    tag='pathways_v2', attached_share={'baseline': 0.3940321454268726, 'moderate': 0.4139242880995848,
                                       'ambitious': 0.5540321454268726},
    carbon_kt={'REF': 21577.50362382947, 'moderate': 21493.26802626376, 'ambitious': 20944.022039096093},
    carbon_vs_reference_pct={'moderate': -0.3903862051617746, 'ambitious': -2.935842791534893},
    floor_area_Mm2={'REF': 89.56525459310168, 'moderate': 88.84679781127117, 'ambitious': 84.1634942040968},
    carbon_per_m2_kg={'REF': 240.9137753457731, 'moderate': 241.9138174447195, 'ambitious': 248.84924559223688},
    shapley_share_of_reference_minus_P5={'moderate': 0.016744, 'ambitious': 0.058045})

SOURCES = {
    'Pellan2024': 'Pellan M, et al. (2024) Building and Environment 256, 111505 (Table 2)',
    'Pauliuk2024': 'Pauliuk S, et al. (2024) Journal of Industrial Ecology 28, 1699 (LEMD EU_UK: 37.7 -> 31.2 m2/cap)',
    'Napiontek2025': 'Napiontek et al. (2025) Resources, Conservation and Recycling 215, 108117',
    'Horup2025': 'Horup LH, et al. (2025) Science of the Total Environment 966, 178780 (Fig. 6)',
    'Resch2021': 'Resch E, et al. (2021) Impact of urban density and building height on energy use in cities '
                 '(A4-A5 e^(-0.01 (t - 2025)), the adopted path of the model)',
    'ChristoforatosPickering2025': 'Christoforatos G, Pickering K (2025) Smart and Sustainable Built '
                                   'Environment, doi:10.1108/SASBE-06-2025-0304 (16 NZ case studies)',
    'ChristoforatosPickeringSchipper2026': 'Christoforatos G, Pickering K, Schipper LA (2026) Integrating soil '
                                           'organic carbon loss into building life cycle assessment and urban '
                                           'planning. Journal of Environmental Management 415, 130603, '
                                           'doi:10.1016/j.jenvman.2026.130603 (SOC-aware scenario: same developed '
                                           'area, inverse-SOC allocation, 14.6% less SOC loss than BAU)',
    'StatsNZHousehold': 'Stats NZ (2021) Family and household projections: 2018(base)-2043, Low / Medium / High '
                        'household-size variants (data/Householddata.xlsx)',
    'CoLiving': '[to complete: co-living / shared-housing embodied-carbon literature; no reference in refs/]',
    'ZeroCarbonAct2019': 'Climate Change Response (Zero Carbon) Amendment Act 2019 (NZ), s. 5Q: net zero emissions '
                         'of long-lived greenhouse gases by 2050',
    'Oslo2025': 'City of Oslo (2025) Climate and environmental requirements for the City of Oslo\'s construction '
                'sites (emission-free construction sites)',
    'DLUHC2022': 'UK Department for Levelling Up, Housing and Communities (2022) Land use change statistics in '
                 'England: new residential addresses 2020 to 2021 (66% on previously developed land in 2020-21; 59% '
                 'three-year average; regions 41% North East - 89% London)',
    'HarrellDavis1982': 'Harrell FE, Davis CE (1982) A new distribution-free quantile estimator. Biometrika 69(3), 635-640',
    'EUTaxonomy2021': 'Commission Delegated Regulation (EU) 2021/2139 (Climate Delegated Act), Annex I, Section 7.7 '
                      '(top 15% of the national or regional building stock)',
    'EfronTibshirani1993': 'Efron B, Tibshirani RJ (1993) An Introduction to the Bootstrap. Chapman & Hall (percentile interval)',
    'Shapley1953': 'Shapley LS (1953) A value for n-person games. In: Kuhn HW, Tucker AW (eds) Contributions to the '
                   'Theory of Games II. Annals of Mathematics Studies 28, 307-317',
    'Albrecht2002': 'Albrecht J, Francois D, Schoors K (2002) A Shapley decomposition of carbon emissions without '
                    'residuals. Energy Policy 30, 727-736',
    'StatsNZCensus': 'Stats NZ census dwelling counts 1986-2023 (data/derived/census_dwellings.csv, occ-unocc-2013.xlsx)',
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


def ramp_named(years, name=None):
    """The adopted adoption path (name None or 'by2035'), a sensitivity ('by2030', 'by2045') or full
    strength from 2027 ('from2027', the theoretical-limit family)."""
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
# L6 ESTIMATOR: Harrell-Davis quantile, bootstrap interval
# ============================================================
def hd_weights(n, q):
    """Harrell & Davis (1982): W_i = I_{i/n}(a, b) - I_{(i-1)/n}(a, b), a = q (n + 1),
    b = (1 - q)(n + 1), I the regularised incomplete beta function."""
    from scipy.special import betainc
    a, b = q * (n + 1), (1.0 - q) * (n + 1)
    grid = np.arange(n + 1) / n
    cdf = betainc(a, b, grid)
    return np.diff(cdf)


def hd_quantile(x, q):
    """Harrell-Davis estimate of the q-quantile: Beta-weighted sum of the order statistics."""
    xs = np.sort(np.asarray(x, float))
    return float(hd_weights(len(xs), q) @ xs)


def hd_bootstrap(x, q, B=L6_BOOTSTRAP_B, seed=L6_BOOTSTRAP_SEED, ci=L6_CI):
    """Nonparametric bootstrap of the cases (resampled with replacement, B times, fixed seed);
    percentile interval (Efron & Tibshirani 1993). Returns (lo, hi, draws)."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    w = hd_weights(len(x), q)
    draws = np.sort(x[idx], axis=1) @ w
    lo, hi = np.percentile(draws, [100 * (1 - ci) / 2, 100 * (1 + ci) / 2])
    return float(lo), float(hi), draws


def case_ratios(fb, typologies=L6_SAMPLE_TYPOLOGIES):
    """x_i = A1-A3_i / pooled A1-A3 of its typology (2025 factors, factors_building.csv),
    independent cases only (empty duplicate_of). Pooling as Building_factors.pool: equal
    weight per sub-type, then per building (over every case of the typology, as the model)."""
    rows = []
    pooled = {}
    for t in typologies:
        g = fb[fb['Typology'] == t]
        pooled[t] = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        for _, r in g[g['duplicate_of'].fillna('') == ''].iterrows():
            rows.append(dict(id=r['id'], typology=t, subtype=r['Subtype'], a13=float(r['A1-A3']),
                             ratio=float(r['A1-A3']) / pooled[t]))
    return pd.DataFrame(rows).sort_values('ratio').reset_index(drop=True), pooled


# ============================================================
# L7 PATHS (A4-A5 factor relative to 2025)
# ============================================================
def a45_reference(years):
    """The adopted A4-A5 factor e^(-0.01 (y - 2025)) (Building_factors.generic_path, DECARB_A45 'resch')."""
    t = np.asarray(years, float)
    return np.exp(-L7_REF_RATE * np.clip(t - 2025.0, 0.0, None))


def a45_target(years, setting):
    """L7 targets: Moderate e^(-(ln 2 / 25)(y - 2025)) (half the 2025 factor in 2050); Ambitious
    1 - (y - 2025) / 25 (zero in 2050); TL7 ('zero'): 0."""
    t = np.clip(np.asarray(years, float) - 2025.0, 0.0, None)
    if setting == 'moderate':
        return np.exp(-(math.log(2.0) / 25.0) * t)
    if setting == 'ambitious':
        return np.clip(1.0 - t / 25.0, 0.0, None)
    if setting == 'zero':
        return np.zeros(len(t))
    raise ValueError(setting)


# ============================================================
# TARGETS FROM DATA (resolved once per projection state)
# ============================================================
def household_size(B):
    """S(y) = population / households of the median path (the engine's S)."""
    return np.asarray(B['df_forecast']['PopTotal_50th'].values, float) / np.asarray(B['households_forecast']['50th'], float)


def resolve(B, factors_building, settings, S_variants):
    """Every lever's parameters at Moderate and Ambitious, with the targets computed from the data in the
    projection state B (projection.main() locals), the projection module settings (`settings`: the projection
    module) and the case-study table. S_variants: {variant: S path} of the Stats NZ household-size variants
    (projection runs with HH_SIZE_VARIANT changed, same population). Returns a dict (levers.json)."""
    typ = list(B['typ_names'])
    years = np.asarray(B['forecast_years'])
    w = ramp(years)
    S = household_size(B)
    # L2 first (L1's occupied area follows S)
    if not all(np.array_equal(np.asarray(B['df_forecast']['PopTotal_50th']), np.asarray(p['pop'])) for p in S_variants.values()):
        raise SystemExit('STOP (L2): the household-size variants do not share the Reference population path.')
    largest = max(S_variants, key=lambda v: float(np.mean(S_variants[v]['S'][2:])))
    dominates = all(np.all(S_variants[largest]['S'][2:] >= S_variants[v]['S'][2:]) for v in S_variants)
    if largest != L2_MODERATE_VARIANT or not dominates:
        raise SystemExit(f'STOP (L2): the largest household-size variant by its S path is {largest!r} '
                         f'(dominates every year: {dominates}), not {L2_MODERATE_VARIANT!r}.')
    S_mod = np.asarray(S_variants[largest]['S'], float)
    i_max = int(np.argmax(S_mod[2:])) + 2
    S_amb_level = float(S_mod[i_max])
    S_target = {'moderate': S_mod, 'ambitious': np.full(len(years), S_amb_level)}
    S_path = {s: S + w * (S_target[s] - S) for s in SETTINGS}
    if np.any(S_path['ambitious'] < S_path['moderate']):
        bad = [int(y) for y, a, m in zip(years, S_path['ambitious'], S_path['moderate']) if a < m]
        raise SystemExit(f'STOP (L2): Ambitious household size below Moderate in {bad}.')
    # the floor of l2_households (S >= S_ref) must not bind in the deterministic runs
    if np.any(S_target['moderate'][1:] < S[1:]):
        bad = [int(y) for y, t_, r_ in zip(years[1:], S_target['moderate'][1:], S[1:]) if t_ < r_]
        raise SystemExit(f'STOP (L2): the Moderate household-size target is below the Reference in {bad}.')
    hS = B['hist_S'].dropna()
    L2 = dict(variant_moderate=largest, variant_S={v: {int(y): float(x) for y, x in zip(years, S_variants[v]['S'])}
                                                   for v in S_variants},
              ambitious_level=S_amb_level, ambitious_level_year=int(years[i_max]),
              S_ref={int(y): float(x) for y, x in zip(years, S)},
              S={s: {int(y): float(x) for y, x in zip(years, S_path[s])} for s in SETTINGS},
              S_target={s: [float(x) for x in S_target[s]] for s in SETTINGS},
              S_2023=float(hS.loc[2023]), history_max=float(hS.max()), history_max_year=int(hS.idxmax()),
              ambitious_ge_moderate_every_year=True, moderate_ge_reference_every_year=True)
    # L1
    size_ref = {t: float(B['size_ref'][t]) for t in typ}
    olf = {t: float(B['OLF_USED'][t]) for t in typ}
    implied, held = {}, []
    for s in SETTINGS:
        sz, hd = l1_size(size_ref, olf, S, L1_F[s], w)
        implied[s] = {}
        for t in typ:
            implied[s][t] = {int(y): dict(size_m2=float(sz[t][i]), occupied_m2=float(S[i] * olf[t]),
                                          cut_pct=float(100 * (sz[t][i] / size_ref[t] - 1)),
                                          size_per_occupant_m2=float(sz[t][i] / S[i]))
                             for i, y in enumerate(years) if y in L1_REPORT_YEARS}
            held += [dict(setting=s, typology=t, year=int(years[i])) for i in np.where(hd[t])[0]]
    L1 = dict(f=dict(L1_F), size_ref=size_ref, size_ref_window=list(settings.DWELLING_SIZE_REF), olf=olf,
              S={int(y): float(S[i]) for i, y in enumerate(years) if y in (2025, 2026) + L1_REPORT_YEARS},
              implied=implied, held=held, benchmarks_pct={k: 100 * v for k, v in L1_BENCHMARKS.items()},
              note='alone (L1 without L2); with L2 the occupied area follows the L2 household size')
    # L3 / L4
    v0 = float(B['v_forward'])
    c, p = B['census'], B['census_18_23']
    share = sum(p[y]['empty'] for y in p) / sum(p[y]['unoccupied'] for y in p)
    v_cons = (c['unoccupied'] * share / c['total_private']).dropna()
    L3 = dict(v0=v0, v_star=dict(L3_V_STAR), floor=L3_VACANCY_FLOOR,
              census_consistent={int(k): float(v) for k, v in v_cons.items()},
              census_consistent_min=float(v_cons.min()), census_consistent_max=float(v_cons.max()),
              census_consistent_min_year=int(v_cons.idxmin()), census_consistent_max_year=int(v_cons.idxmax()),
              consistent_empty_share=float(share), census_consistent_midpoint=float((v_cons.min() + v_cons.max()) / 2.0))
    L4 = dict(absorption=dict(L4_ABSORPTION), O26=float(B['join_info']['50th']['O26']),
              rho=float(B['rho_other']), gap_ref=str(settings.OVERBUILD_GAP_REF))
    L5 = dict(d=dict(L5_D), demolition_rate=float(B['demolition_rate']),
              long_run_residual=float(B['unconsented_rate']),
              long_run_net=float(B['demolition_rate'] + B['unconsented_rate']))
    held_sh = B['held_shares']
    denser = dict(removed=True, note=DENSER_MIX_V2_NOTE, baseline_shares={t: float(held_sh[t]) for t in typ})
    # L6
    cases, pooled = case_ratios(factors_building)
    x = cases['ratio'].values
    from scipy.stats.mstats import hdquantiles
    est = {}
    for s in SETTINGS:
        q = L6_Q[s]
        r = hd_quantile(x, q)
        lo, hi, _ = hd_bootstrap(x, q)
        est[s] = dict(q=q, r=r, ci_lo=lo, ci_hi=hi, scipy_hdquantiles=float(np.asarray(hdquantiles(x, prob=[q]))[0]),
                      weights=[float(v) for v in hd_weights(len(x), q)])
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    L6 = dict(n=int(len(x)), sample_typologies=list(L6_SAMPLE_TYPOLOGIES), min_cases=L6_MIN_CASES,
              cases=cases.to_dict(orient='records'), pooled_a13=pooled, a13_2025_pooled=a13,
              pooled_check_max_abs=float(max(abs(pooled[t] - a13[t]) for t in pooled)),
              estimator=est, r={s: {t: est[s]['r'] for t in typ} for s in SETTINGS},
              r_apartments_held={s: {t: (1.0 if t == 'Apartments' else est[s]['r']) for t in typ} for s in SETTINGS},
              bootstrap=dict(B=L6_BOOTSTRAP_B, seed=L6_BOOTSTRAP_SEED, ci=L6_CI, method='percentile'))
    # L7
    a45 = {t: float(B['MAT_STAGE']['A4-A5'][t].sum()) for t in typ}
    ref45 = a45_reference(years)
    red45 = {t: np.asarray(B['RED45_TOT'][t], float) for t in typ}
    chk = max(float(np.max(np.abs(a45[t] * (1.0 - ref45) - red45[t]))) for t in typ)
    if chk > 1e-9:
        raise SystemExit(f'L7: the model A4-A5 path is not a45_2025 x e^(-0.01 (y - 2025)) (max abs diff {chk:.2e}).')
    L7 = dict(a45_2025=a45, reference_factor={int(y): float(v) for y, v in zip(years, ref45)},
              target=dict(L7_TARGET), target_factor={s: {int(y): float(v) for y, v in zip(years, a45_target(years, s))}
                                                      for s in SETTINGS},
              factor={s: {int(y): float(v) for y, v in zip(years, ref45 + w * (a45_target(years, s) - ref45))}
                      for s in SETTINGS}, reference_check_max_abs=chk,
              assumption='A5 treated as energy: site waste assumed eliminated (upper bound)')
    # L8 / L9
    soil = {t: float(B['SOIL_INTENSITY'][t]) for t in typ}
    L8 = dict(x=dict(L8_X), published_reduction=L8_PUBLISHED_REDUCTION, soil_factor_2025=soil,
              factor={s: {t: soil[t] * (1.0 - L8_X[s]) for t in typ} for s in SETTINGS})
    E0 = B['engine_out']['50th']
    implied_bf = np.divide(E0['soil_free_gfa'], E0['total'], out=np.zeros(len(years)), where=E0['total'] != 0)
    L9 = dict(s=dict(L9_S), england=dict(L9_ENGLAND),
              reference_implied_share={int(y): float(v) for y, v in zip(years, implied_bf) if y >= 2026},
              reference_implied_share_mean_2026_2050=float(np.sum(E0['soil_free_gfa'][1:]) / np.sum(E0['total'][1:])),
              note='no national NZ statistic of new residential floor area on previously developed land exists; England '
                   'is the international benchmark')
    return dict(adoption=dict(form='normalised logistic', k=RAMP_K, mid=RAMP_MID, start=OBSERVED_YEAR, end=RAMP_END,
                              adopted=ADOPTION_ADOPTED, basis=RAMP_BASIS, w={int(y): float(v) for y, v in zip(years, w)},
                              sensitivities=[dict(r) for r in ADOPTION_SENSITIVITIES],
                              w_sensitivity={int(y): float(v) for y, v in zip(years, ramp_named(years, 'by2045'))},
                              w_sensitivity_2030={int(y): float(v) for y, v in zip(years, ramp_named(years, 'by2030'))}),
                L1=L1, L2=L2, L3=L3, L4=L4, L5=L5, L6=L6, L7=L7, L8=L8, L9=L9, denser_mix_pathways_v2=denser)


def stop_checks(p):
    """STOP conditions of the lever parameters (raises SystemExit)."""
    if p['L6']['n'] < L6_MIN_CASES:
        raise SystemExit(f"STOP (L6): {p['L6']['n']} independent cases < {L6_MIN_CASES}.")
    for s in SETTINGS:
        if p['L6']['estimator'][s]['r'] >= 1.0:
            raise SystemExit(f"STOP (L6): Harrell-Davis r = {p['L6']['estimator'][s]['r']:.4f} >= 1 ({s}).")
    if not p['L2']['ambitious_ge_moderate_every_year']:
        raise SystemExit('STOP (L2): Ambitious household size below Moderate.')


# ============================================================
# LEVER FUNCTIONS (each returns new inputs; strength 0 = baseline values)
# ============================================================
def l1_size(size_ref, olf, S, f, w):
    """L1: size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)), occ_t = S(y) OLF_t (OLF_t may be a
    path). Where size_ref_t <= occ_t(y) the typology / year is held at size_ref_t (never below the occupied
    area). Returns (size {typology: array}, held {typology: bool array})."""
    S = np.asarray(S, float)
    size, held = {}, {}
    for t in size_ref:
        occ = S * np.asarray(olf[t], float)
        ref = float(size_ref[t])
        h = ref <= occ
        size[t] = np.where(h, ref, occ + (1.0 - float(f) * w) * (ref - occ))
        held[t] = h
    return size, held


def l2_households(pop, hh, S_target, w):
    """L2: S(y) = max(S_ref(y), S_ref(y) + w(y) (S_target(y) - S_ref(y))), S_ref = pop / hh; households = pop / S,
    computed as hh x S_ref / S so that w = 0 returns hh exactly. The floor at S_ref means the lever never adds
    households: in the deterministic runs the target is at or above S_ref in every year (asserted by resolve(), so
    the floor never binds there); it binds only in Monte Carlo draws whose own household size is above the fixed
    target (population ranks above the High variant's, pathways_mc.py). Returns (hh, S)."""
    hh = np.asarray(hh, float)
    S_ref = np.asarray(pop, float) / hh
    S = np.maximum(S_ref, S_ref + w * (np.asarray(S_target, float) - S_ref))
    return hh * (S_ref / S), S


def l3_vacancy(v0, v_star, w):
    """L3: stock-wide vacancy v(y) = v0 + w(y) (v* - v0)."""
    return float(v0) + w * (float(v_star) - float(v0))


def l4_join(E_nojoin, O26, rho, gap_ref, absorption):
    """L4: the 2026 overbuild with the surplus absorbed at rate `absorption` (engine.market_excess, mode
    'surplus'), from the Reference forward run WITHOUT a join and the same observed 2026 building, rho and gap
    reference. Returns (join, redev)."""
    join, ji = engine.market_excess(E_nojoin, O26, rho, gap_ref, 'surplus', absorption)
    return join, ji['redev']


def l5_rates(rate_demol, rate_unc, long_run_residual, d_demolition, w, d_surge=None):
    """L5: demolition rate x (1 - w d); the recent-surge component of the residual path (rate_unc - long-run
    residual) x (1 - w d_surge) (d_surge = d unless given; TL5: 1, the surge removed); the long-run residual
    untouched."""
    d_surge = d_demolition if d_surge is None else d_surge
    return (float(rate_demol) * (1.0 - w * float(d_demolition)),
            float(long_run_residual) + (np.asarray(rate_unc, float) - long_run_residual) * (1.0 - w * float(d_surge)))


def l6_intensity(intensity, a13_2025, red13, r, w):
    """L6: intensity_t(y) - w(y) (1 - r_t) (A1-A3_t,2025 - red13_t(y)): only the A1-A3 term is scaled, so
    A1-A3(y) = [1 - w (1 - r)] (A1-A3_2025 - reduction(y)) and decarbonisation still applies on top."""
    return {t: np.asarray(intensity[t], float) - w * (1.0 - float(r[t])) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in intensity}


def a13_path(a13_2025, red13, r, w):
    """A1-A3 intensity (kg/m2) by typology and year under L6 (r = 1: the baseline path)."""
    return {t: (1.0 - w * (1.0 - float(r[t]))) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in a13_2025}


def l7_delta(a45_2025, years, target, w):
    """L7: change of the A4-A5 intensity (kg/m2) by typology and year: a45_2025 x w (target - ref), ref =
    e^(-0.01 (y - 2025)), so the A4-A5 factor becomes ref + w (target - ref)."""
    ref = a45_reference(years)
    return {t: float(a45_2025[t]) * w * (np.asarray(target, float) - ref) for t in a45_2025}


def a45_path(a45_2025, years, target=None, w=None):
    """A4-A5 intensity (kg/m2) by typology and year (target None: the reference path)."""
    ref = a45_reference(years)
    f = ref if target is None else ref + w * (np.asarray(target, float) - ref)
    return {t: float(a45_2025[t]) * f for t in a45_2025}


def _add(d, delta):
    return {t: np.asarray(d[t], float) + np.asarray(delta[t], float) for t in d}


def apply(base, params, active, ramp_name=None, E_nojoin=None, l6_apartments_held=False):
    """Modified engine.forward inputs and households for the levers in `active` ({lever: 'moderate' |
    'ambitious'}).

    base: pathways.base_context. A lever not in `active` leaves its inputs as the very objects of the
    reference run. Returns (inputs, join, join_redev, info); info['hh'] is the households path."""
    unknown = set(active) - set(LEVERS)
    if unknown or not set(active.values()) <= set(SETTINGS):
        raise ValueError(f'Unknown lever or setting in {active}.')
    fi = dict(base['fwd_inputs'])                         # same objects; replaced below if a lever is on
    years = base['years']
    w = ramp_named(years, ramp_name)
    join, redev = base['join'], base['join_redev']
    hh = base['hh']
    info = dict(w=w, l1_held=None)
    if 'L2' in active:
        hh, _ = l2_households(base['pop'], base['hh'], params['L2']['S_target'][active['L2']], w)
    if 'L1' in active:
        S = np.asarray(base['pop'], float) / np.asarray(hh, float)
        fi['size'], info['l1_held'] = l1_size(base['size_ref'], base['olf'], S, params['L1']['f'][active['L1']], w)
    if 'L3' in active:
        fi['v'] = l3_vacancy(base['v0'], params['L3']['v_star'][active['L3']], w)
    if 'L4' in active:
        if E_nojoin is None:
            raise ValueError('L4 needs the Reference forward run without a join (E_nojoin).')
        join, redev = l4_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'],
                              params['L4']['absorption'][active['L4']])
    if 'L5' in active:
        fi['rate_demol'], fi['rate_unc'] = l5_rates(base['rate_demol'], base['rate_unc'], base['long_run_residual'],
                                                    params['L5']['d'][active['L5']], w)
    r = {t: 1.0 for t in base['a13_2025']}
    if 'L6' in active:
        r = params['L6']['r_apartments_held' if l6_apartments_held else 'r'][active['L6']]
        for key in ('intensity', 'intensity_upfront'):
            fi[key] = l6_intensity(fi[key], base['a13_2025'], base['red13'], r, w)
    target45 = None
    if 'L7' in active:
        target45 = a45_target(years, active['L7'])
        d45 = l7_delta(base['a45_2025'], years, target45, w)
        for key in ('intensity', 'intensity_upfront'):
            fi[key] = _add(fi[key], d45)
    soil_path = None
    if 'L8' in active:
        x = params['L8']['x'][active['L8']]
        soil_path = {t: float(base['soil'][t]) * (1.0 - w * x) for t in base['typ']}
        ds = {t: soil_path[t] - float(base['soil'][t]) for t in base['typ']}
        for key in ('intensity', 'intensity_upfront'):
            fi[key] = _add(fi[key], ds)
        fi['soil'] = soil_path
    if 'L9' in active:
        fi['brownfield_share'] = np.full(len(years), float(params['L9']['s'][active['L9']]))
        fi['brownfield_w'] = w
    info.update(hh=hh, a13=a13_path(base['a13_2025'], base['red13'], r, w),
                a45=a45_path(base['a45_2025'], years, target45, w), soil_path=soil_path)
    return fi, join, redev, info


def pathway_levers(pathway, setting):
    """{lever: setting} of a pathway ('P1'..'P5'; a projection variant id such as 'REF': no lever)."""
    if pathway in N.SCENARIOS:
        return {}
    levers = LEVERS if pathway == 'P5' else PATHWAYS[pathway]
    return {L: setting for L in levers}


def label(active):
    """'none' for no lever; otherwise e.g. 'L1:moderate+L4:moderate'."""
    return '+'.join(f'{k}:{active[k]}' for k in LEVERS if k in active) or 'none'


def tagged(r):
    """The basis column of a lever row: its tag and source, the tag written once."""
    return r['source'] if r['source'].startswith(r['tag']) else f"{r['tag']}: {r['source']}"


# ============================================================
# REGISTER (ASSUMPTIONS.md "Pathways" section), LEVERS_TABLE.md and the methods draft
# ============================================================
OMITTED = [
    ('Lightweighting', 'the case studies give A1-A3 per m2 by material and item, not structural mass by design '
     'alternative; a mass reduction cannot be separated from the material choice already covered by L6'),
    ('Bio-based archetypes', 'no typology has a bio-based archetype among the 16 case studies, and the model\'s '
     'biogenic-carbon convention (timber C1-C4 excludes biogenic CO2) would need extending; overlaps L6'),
    ('Renovation carbon of retained buildings', 'not modelled: L5 is an upper bound of the effect of building '
     'lifetime extension (Napiontek et al. 2025)'),
]


def pct(x, nd=1):
    return f'{100 * x:.{nd}f}%'


def by_year(d, year):
    """d[year] whether the keys are int (in memory) or str (after the JSON round trip)."""
    return d[year] if year in d else d[str(year)]


def _l1_text(p, s, year):
    im = p['L1']['implied'][s]
    return ', '.join(f"{t} {by_year(im[t], year)['size_m2']:.1f} m2 ({by_year(im[t], year)['cut_pct']:+.1f}%)" for t in im)


def lever_table(p):
    """Table 1 of the paper, lever rows: item, pathway, demand band targeted, how it works (exact model
    definition), assumption, Moderate, Ambitious, source with full citation, tag."""
    L1, L2, L3, L4, L5, L6, L7, L8, L9 = (p[f'L{k}'] for k in range(1, 10))
    e = L6['estimator']
    pw = lambda L: f"{LEVER_PATHWAY[L]} {PATHWAY_NAMES[LEVER_PATHWAY[L]]}"
    s50 = lambda s: by_year(L2['S'][s], 2050)
    return [
        dict(item='L1 ' + LEVER_NAMES['L1'], pathway=pw('L1'), band=BAND_TARGET['L1'],
             how='size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)), occ_t = S(y) x OLF_t (engine `size`); '
                 'never below occ_t; a share f of the extra-space margin removed, full strength in 2035',
             assumption='new dwellings keep the occupied area S x OLF; only the space above it shrinks',
             moderate=f"f = {L1['f']['moderate']:.2f}; 2050 (alone): {_l1_text(p, 'moderate', 2050)}",
             ambitious=f"f = {L1['f']['ambitious']:.2f}; 2050 (alone): {_l1_text(p, 'ambitious', 2050)}",
             source='DECISION (author): f; benchmarks Pellan M, et al. (2024) Building and Environment 256, 111505, '
                    'Table 2 (individual dwellings 107 -> 100 m2, -6.5%); Pauliuk S, et al. (2024) Journal of '
                    'Industrial Ecology 28, 1699 (LEMD EU_UK 37.7 -> 31.2 m2/cap, -17%)', tag='DECISION'),
        dict(item='L2 ' + LEVER_NAMES['L2'], pathway=pw('L2'), band=BAND_TARGET['L2'],
             how='S(y) = S_ref(y) + w(y) (S_target(y) - S_ref(y)); households = population / S (engine `hh`); the '
                 'occupied area S x OLF follows',
             assumption='households form at the larger size (co-living, shared and multigenerational living); '
                        'population unchanged',
             moderate=f"S_target = Stats NZ {L2['variant_moderate']} household-size variant (the largest S path); "
                      f"S 2050 = {s50('moderate'):.3f} (Reference {by_year(L2['S_ref'], 2050):.3f})",
             ambitious=f"S held at {L2['ambitious_level']:.4f} (the highest value of the {L2['variant_moderate']} "
                       f"variant, {L2['ambitious_level_year']}) through the adoption path; >= Moderate every year",
             source='DATA: ' + SOURCES['StatsNZHousehold'] + '; LITERATURE: ' + SOURCES['CoLiving'] +
                    '; DECISION (author): the Ambitious level', tag='DATA + DECISION'),
        dict(item='L3 ' + LEVER_NAMES['L3'], pathway=pw('L3'), band=BAND_TARGET['L3'],
             how='v(y) = v0 + w(y)(v* - v0) (engine `v`); while v falls the vacancy-change term of the stock identity '
                 'releases existing dwellings once',
             assumption=f"consistent definition: the pooled 2018/2023 empty share of unoccupied dwellings "
                        f"({100 * L3['consistent_empty_share']:.1f}%) applied to every census; absorbs the unabsorbed "
                        f"post-2018 excess vacancy (2023 is the series maximum, {pct(L3['census_consistent_max'], 2)})",
             moderate=f"{pct(L3['v0'], 2)} -> {pct(L3['v_star']['moderate'])} (midpoint of the consistent 1986-2023 range "
                      f"{pct(L3['census_consistent_min'], 2)} ({L3['census_consistent_min_year']}) - "
                      f"{pct(L3['census_consistent_max'], 2)} ({L3['census_consistent_max_year']}))",
             ambitious=f"-> {pct(L3['v_star']['ambitious'])} (the {L3['census_consistent_min_year']} minimum)",
             source='DATA: ' + SOURCES['StatsNZCensus'], tag='DATA'),
        dict(item='L4 ' + LEVER_NAMES['L4'], pathway=pw('L4'), band=BAND_TARGET['L4'],
             how='engine.market_excess(..., surplus, absorption a): a share a of the remaining 2026 overbuild is '
                 'absorbed each year (`join`)',
             assumption='the 2026 observed building stays; later building is lower by the absorbed overbuild',
             moderate=f"a = {L4['absorption']['moderate']:.2f} a year", ambitious=f"a = {L4['absorption']['ambitious']:.2f} a year",
             source='DECISION (author): the absorption sensitivities of the 2026 overbuild in the projection '
                    '(projection.OVERBUILD_ABSORPTION 0.10 / 0.20)', tag='DECISION'),
        dict(item='L5 ' + LEVER_NAMES['L5'], pathway=pw('L5'), band=BAND_TARGET['L5'],
             how='demolition x (1 - w d); recent-surge component of the residual x (1 - w d) (`rate_demol`, '
                 '`rate_unc`); the long-run residual untouched',
             assumption='renovation carbon of the kept stock not modelled (upper bound; Napiontek et al. 2025, '
                        'Resources, Conservation and Recycling 215, 108117)',
             moderate=f"d = {pct(L5['d']['moderate'], 0)}", ambitious=f"d = {pct(L5['d']['ambitious'], 0)}",
             source='LITERATURE: Pellan M, et al. (2024) Building and Environment 256, 111505 (demolition 150,000 -> '
                    '90,000 a year, -40%)', tag='LITERATURE'),
        dict(item='L6 ' + LEVER_NAMES['L6'], pathway=pw('L6'), band=BAND_TARGET['L6'],
             how='A1-A3(y) = [1 - w(y)(1 - r)] (A1-A3_2025 - decarbonisation reduction(y)) (`intensity`, A1-A3 term '
                 'only); r = Harrell-Davis quantile of the case ratios A1-A3_i / pooled typology A1-A3',
             assumption='the same pooled r for all three typologies (apartments held as a sensitivity); decarbonisation '
                        'on top; B events, C1-C4 and soil unchanged',
             moderate=f"q = {e['moderate']['q']:.2f}: r = {e['moderate']['r']:.3f} (95% CI "
                      f"{e['moderate']['ci_lo']:.3f}-{e['moderate']['ci_hi']:.3f}), n = {L6['n']}",
             ambitious=f"q = {e['ambitious']['q']:.2f}: r = {e['ambitious']['r']:.3f} ({e['ambitious']['ci_lo']:.3f}-"
                       f"{e['ambitious']['ci_hi']:.3f})",
             source='DATA: Christoforatos G, Pickering K (2025) Smart and Sustainable Built Environment, '
                    'doi:10.1108/SASBE-06-2025-0304; Harrell FE, Davis CE (1982) Biometrika 69, 635-640; top-15% '
                    'convention of Commission Delegated Regulation (EU) 2021/2139, Annex I s. 7.7', tag='DATA / LITERATURE'),
        dict(item='L7 ' + LEVER_NAMES['L7'], pathway=pw('L7'), band=BAND_TARGET['L7'],
             how='A4-A5 factor(y) = ref(y) + w(y) (target(y) - ref(y)), ref(y) = e^(-0.01 (y - 2025)) (the adopted path); '
                 'A4-A5(y) = A4-A5_2025 x factor(y) (`intensity`, A4-A5 term only)',
             assumption=L7['assumption'] + '; B events unchanged',
             moderate=f"target e^(-(ln 2 / 25)(y - 2025)): -50% by 2050 (factor 2050 {by_year(L7['factor']['moderate'], 2050):.3f})",
             ambitious=f"target 1 - (y - 2025) / 25: zero by 2050 (factor 2050 {by_year(L7['factor']['ambitious'], 2050):.3f})",
             source='LITERATURE: ' + SOURCES['ZeroCarbonAct2019'] + '; ' + SOURCES['Oslo2025'], tag='LITERATURE'),
        dict(item='L8 ' + LEVER_NAMES['L8'], pathway=pw('L8'), band=BAND_TARGET['L8'],
             how='soil carbon loss per m2 of footprint on the non-replacement floor area x (1 - w(y) x) (engine `soil` '
                 'by year and the soil term of `intensity`)',
             assumption='the published SOC-aware allocation (same developed area, inverse-SOC siting) applies to the '
                        'national soil factor; the same BAU soil factor as the model',
             moderate=f"x = {L8['x']['moderate']:.3f} (half the published reduction)",
             ambitious=f"x = {L8['x']['ambitious']:.3f} (the published SOC-aware scenario)",
             source='LITERATURE: ' + SOURCES['ChristoforatosPickeringSchipper2026'], tag='LITERATURE'),
        dict(item='L9 ' + LEVER_NAMES['L9'], pathway=pw('L9'), band=BAND_TARGET['L9'],
             how='target share s of ALL new floor area on previously developed land (zero soil carbon loss): soil-free '
                 'floor area = replacement + w(y) max(0, s x total - replacement) (engine `brownfield_share`), taken from '
                 'the soil-bearing floor area; never below the replacement share (no double counting)',
             assumption=f"the Reference's implied share (replacement floor area / total) is "
                        f"{100 * L9['reference_implied_share_mean_2026_2050']:.1f}% over 2026-2050; {L9['note']}",
             moderate=f"s = {L9['s']['moderate']:.2f} (North East England, the lowest English region)",
             ambitious=f"s = {L9['s']['ambitious']:.2f} (England, three-year average)",
             source='DATA: ' + SOURCES['DLUHC2022'], tag='DATA'),
    ]


def register(p):
    """(setting, value, basis) rows for the resolved parameters p (resolve() / levers.json)."""
    note = DENSER_MIX_V2_NOTE
    rows = [
        ('Pathways', 'P1 Space per person (L1 Dwelling size + L2 Household occupancy), P2 Existing stock (L3 Vacancy + '
         'L4 Overbuild absorption + L5 Building lifetime extension), P3 Construction (L6 Material carbon + L7 '
         'Construction-stage carbon), P4 Land (L8 Soil-aware planning + L9 Brownfield development), P5 Combined (every '
         'lever); settings Moderate (headline) and Ambitious (sensitivity); Reference projection, with the Low and High '
         'replacement variants for the Reference and P5; only Population growth is untargeted', 'DECISION (author)'),
        ('Adoption path', f"normalised logistic s(y) = 1 / (1 + exp(-k (y - {p['adoption']['mid']}))), k = ln(81)/6 = "
         f"{p['adoption']['k']:.4f}; w = (s(y) - s(2026)) / (s(2035) - s(2026)), 1 after 2035, 0 up to 2026 (full "
         "roll-out by 2035, adopted); one rule for every window 2026 -> E (W = E - 2026): midpoint 2026 + W/2, "
         "k = ln(81) / (2W/3); sensitivities (P5): full roll-out by 2030 (midpoint "
         f"{ADOPTION_BY2030['mid']:g}, k = {ADOPTION_BY2030['k']:.4f}) and by 2045 (midpoint {ADOPTION_BY2045['mid']:g}, "
         f"k = {ADOPTION_BY2045['k']:.4f})", 'LITERATURE: ' + RAMP_BASIS + '; DECISION (author): the logistic form'),
        ('Business-as-usual decarbonisation', 'applies in every run (A1-A3 item paths of Horup et al. 2025; A4-A5 '
         'e^(-0.01 (t - 2025)), the reference path of L7)', 'LITERATURE'),
        ('Typology mix', 'Reference (held) shares in every run; ' + note['text'] + ' Values from git tag pathways_v2 '
         f"(Reference): Moderate / Ambitious carbon {note['carbon_vs_reference_pct']['moderate']:+.2f}% / "
         f"{note['carbon_vs_reference_pct']['ambitious']:+.2f}% vs the Reference", 'DECISION (author); DATA: git tag pathways_v2'),
        ('2026 overbuild under the levers', 'held at the Reference path (dwellings) in every run except L4; the '
         'overbuild is the observed 2026 pipeline, not demand', 'DECISION (author)'),
        ('Vacancy check', f"implied vacancy 1 - hh / physical stock >= {pct(p['L3']['floor'])} in every year of every "
         'pathway run', 'DECISION (author)'),
        ('Attribution', 'Shapley values (Shapley 1953; Albrecht, Francois & Schoors 2002, Energy Policy 30, 727) over '
         'the 16 pathway subsets (main) and the 512 lever subsets (SI), exact rational arithmetic, on cumulative carbon '
         'and cumulative LoE AR; demand bands give the attribution by band exactly', 'LITERATURE; DECISION (author)'),
        ('Back-cast', 'uniform factor k on the floor area of every 2027-2050 cohort of P5 and the Reference (2026 '
         'fixed), brentq for cumulative LoE AR = 1; AtP: minimum LoE at k = 0', 'DECISION (author)'),
        ('Solution space', 'uniform cuts of 2027-2050 floor area and of non-soil carbon per m2 of the 2027-2050 '
         'cohorts, 0-100% in 5% steps, applied to the Reference', 'LITERATURE: Horup et al. 2025, Sci. Total Environ. '
         '966, 178780, Fig. 6 (form); DECISION (author)'),
    ]
    for r in lever_table(p):
        rows.append((r['item'], f"Moderate: {r['moderate']}; Ambitious: {r['ambitious']}; how: {r['how']}; "
                     f"band: {r['band']}; assumption: {r['assumption']}", tagged(r)))
    rows += [(f'Omitted: {a}', 'not modelled', f'DECISION (author): {b}') for a, b in OMITTED]
    return rows


# ============================================================
# THEORETICAL LIMIT TL (MODEL v2.1.0): a thought experiment, not a pathway
# ============================================================
# TL = P5 Moderate with TL1-TL10, every lever and every TL item at full strength from 1 January 2027 (no
# adoption path; 2026 observed and untouched). TLn is the limit of Ln; TL10 (minimum space per person) has no
# lever counterpart. Every TL item is at least as strong as the Ambitious setting of its lever (tl_strength).
TL_REOCCUPATION = 'reoccupation'          # MODEL v2.1.1: separate line of the TL attribution
TL_BASE_LABEL = 'P5-moderate-from2027-reoccupied'   # the TL base: P5 Moderate from 2027, reoccupation
TL_COMPONENTS = tuple(f'TL{k}' for k in range(1, 11))
TL_NAMES = {k: N.TL[k] for k in TL_COMPONENTS}
TL_BASE_SETTING = 'moderate'
TL_FROM2027 = 'from2027'           # adoption: full strength from 2027 (TL and its Shapley subsets)
TL_DISCLAIMER = ('TL is a hyper-optimistic theoretical limit; a thought experiment, not a pathway: all assumptions at '
                 'full strength from 1 January 2027, combining best observed attributes of different buildings and '
                 'places; not a proposal or a feasible pathway (potentials hierarchy: theoretical > technical > '
                 'realisable); a thought experiment combining instant limits; its early years rely on re-occupying all vacant dwellings and a return to 1991 household size.')
TL_REOCCUPATION_NOTE = ("In 2027 households re-form at the 1991 household size, so almost no new households form that year; released dwellings are brought back into use in proportion to each year's need; 2026 observed.")
TL_BAU_NOTE = ('The adopted decarbonisation applies in TL as in every run (A1-A3 item paths of Horup et al. 2025; A4-A5 '
               'e^(-0.01 (t - 2025)) until TL7 sets A4-A5 to zero).')
TL5_SURGE_REMOVED = 1.0            # TL5: the recent replacement surge removed entirely (as the Low variant)
TL9_S = 0.89                       # TL9: London, the highest English region (DLUHC 2022)


def resolve_tl(chars, factors_building, factors_typology, olf_used, hist_S, params):
    """TL parameters from the data. chars: per-building characteristics (Building_factors.load_characteristics);
    factors_building: outputs/data/factors/factors_building.csv (A1-A3 per m2 at 2025 factors, duplicate_of);
    factors_typology: outputs/data/factors/factors_typology.csv (SOC_avg, SOC_low); olf_used: the Reference OLF
    per typology; hist_S: the model's household-size history (projection.hist_S); params: resolve()."""
    fb = factors_building.set_index('id')
    independent = [i for i in fb.index if str(fb.loc[i, 'duplicate_of']) in ('', 'nan')]
    c = chars.loc[independent]
    occ_check = float((c['Total GFA'] / c['Occupants'] - c['OLF']).abs().max()) if 'Occupants' in c else None
    olf_bld = c['OLF'].astype(float)
    best = str(olf_bld.idxmin())
    TL10 = dict(building=best, typology=str(fb.loc[best, 'Typology']), olf=float(olf_bld.min()),
                per_building={str(i): float(v) for i, v in olf_bld.sort_values().items()},
                gfa_over_occupants_max_abs_diff=occ_check, excluded_duplicates=[i for i in fb.index if i not in independent],
                replaces={t: float(v) for t, v in olf_used.items()})
    r_amb = float(params['L6']['estimator']['ambitious']['r'])
    TL6 = {}
    for t in factors_typology['Typology']:
        g = fb[fb['Typology'] == t]
        pooled = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        ind = g.loc[[i for i in g.index if i in independent]]
        ratios = (ind['A1-A3'] / pooled).sort_values()
        evidence = len(ind) >= 2
        own = float(ratios.iloc[0]) if evidence else None
        r = min(own, r_amb) if evidence else r_amb
        TL6[t] = dict(n_independent=int(len(ind)), pooled_a13=pooled, own_best=own,
                      own_best_building=str(ratios.index[0]) if evidence else None, r_ambitious=r_amb, r=r,
                      rule='min(own best independent case, r_Ambitious)' if evidence else
                           'r_Ambitious (one independent case: no own best case)',
                      exceeds_ambitious=bool(r < r_amb), ratios={str(i): float(v) for i, v in ratios.items()})
    ft = factors_typology.set_index('Typology')
    TL8 = {t: dict(soc_avg=float(ft.loc[t, 'SOC_avg']), soc_low=float(ft.loc[t, 'SOC_low'])) for t in ft.index}
    hS = hist_S.dropna()
    TL2 = dict(S=float(hS.max()), year=int(hS.idxmax()), history_first_year=int(hS.index.min()),
               history_last_year=int(hS.index.max()))
    return dict(TL1=dict(f=1.0), TL2=TL2, TL3=dict(v=0.0), TL4=dict(absorption=1.0),
                TL5=dict(d_demolition=float(params['L5']['d']['ambitious']), d_surge=TL5_SURGE_REMOVED),
                TL6=TL6, TL7=dict(a45_factor=0.0), TL8=TL8, TL9=dict(s=TL9_S), TL10=TL10,
                disclaimer=TL_DISCLAIMER, base_setting=TL_BASE_SETTING, start_year=OBSERVED_YEAR + 1)


def tl_strength(params, pT, years):
    """Every TL item against the Ambitious setting of its lever: [(item, TL value, Ambitious value, ok)]. TL must
    be at least as strong in every year and typology (asserted by pathways.compute_tl)."""
    w = ramp(years)
    amb_S = np.asarray(params['L2']['S_target']['ambitious'], float)
    amb45 = a45_target(years, 'ambitious')
    rows = [('TL1', 'f = 1', f"f = {params['L1']['f']['ambitious']}", 1.0 >= params['L1']['f']['ambitious']),
            ('TL2', f"S = {pT['TL2']['S']:.4f}", f"S target {amb_S.max():.4f}", bool(np.all(pT['TL2']['S'] >= amb_S))),
            ('TL3', 'v = 0', f"v* = {params['L3']['v_star']['ambitious']}", 0.0 <= params['L3']['v_star']['ambitious']),
            ('TL4', 'a = 1', f"a = {params['L4']['absorption']['ambitious']}", 1.0 >= params['L4']['absorption']['ambitious']),
            ('TL5', f"demolition d = {pT['TL5']['d_demolition']}, surge removed (d = 1)",
             f"d = {params['L5']['d']['ambitious']} (both)",
             pT['TL5']['d_demolition'] >= params['L5']['d']['ambitious'] and pT['TL5']['d_surge'] >= params['L5']['d']['ambitious']),
            ('TL6', ', '.join(f"{t} r = {v['r']:.3f}" for t, v in pT['TL6'].items()),
             f"r = {params['L6']['estimator']['ambitious']['r']:.3f}",
             all(v['r'] <= params['L6']['estimator']['ambitious']['r'] for v in pT['TL6'].values())),
            ('TL7', 'A4-A5 = 0 from 2027', 'linear to zero in 2050', bool(np.all(0.0 <= amb45))),
            ('TL8', ', '.join(f"{t} {v['soc_low']:.2f}" for t, v in pT['TL8'].items()),
             ', '.join(f"{t} {v * 1.0:.2f}" for t, v in params['L8']['factor']['ambitious'].items()),
             all(pT['TL8'][t]['soc_low'] <= params['L8']['factor']['ambitious'][t] for t in pT['TL8'])),
            ('TL9', f"s = {pT['TL9']['s']}", f"s = {params['L9']['s']['ambitious']}", pT['TL9']['s'] >= params['L9']['s']['ambitious']),
            ('TL10', f"OLF {pT['TL10']['olf']:.2f} m2/person", 'no lever (Reference OLF per typology)',
             all(pT['TL10']['olf'] <= v for v in pT['TL10']['replaces'].values()))]
    del w
    return rows


def apply_tl(base, params, pT, comps, E_nojoin=None):
    """Inputs of a TL-family run: P5 Moderate with the TL items in `comps` (subset of TL1..TL10), every lever and
    item at full strength from 2027 (w = 1 in 2027-2050). TLn overrides Ln. Returns (inputs, join_absorbed,
    join_redev, info); the reoccupation of released dwellings is applied by pathways.run_tl."""
    unknown = set(comps) - set(TL_COMPONENTS)
    if unknown:
        raise ValueError(f'Unknown TL component(s) {unknown}.')
    s = TL_BASE_SETTING
    years = base['years']
    w = ramp_from2027(years)
    typ = list(base['typ'])
    fi = dict(base['fwd_inputs'])
    # L2 / TL2: household size (TL2: the historical maximum from 2027)
    S_target = np.full(len(years), pT['TL2']['S']) if 'TL2' in comps else params['L2']['S_target'][s]
    hh, S = l2_households(base['pop'], base['hh'], S_target, w)
    # TL10: OLF of every new building = the lowest independent design OLF
    if 'TL10' in comps:
        olf_y = {t: float(base['olf'][t]) + w * (pT['TL10']['olf'] - float(base['olf'][t])) for t in typ}
        fi['olf'] = olf_y
    else:
        olf_y = {t: np.full(len(years), float(base['olf'][t])) for t in typ}
    # L1 / TL1: size = occ + [1 - f w](size_ref - occ), occ = S x OLF
    f = 1.0 if 'TL1' in comps else params['L1']['f'][s]
    fi['size'], held = l1_size(base['size_ref'], olf_y, S, f, w)
    # L3 / TL3 and L4 / TL4
    fi['v'] = l3_vacancy(base['v0'], 0.0 if 'TL3' in comps else params['L3']['v_star'][s], w)
    if E_nojoin is None:
        raise ValueError('apply_tl needs the Reference forward run without a join (E_nojoin).')
    join, redev = l4_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'],
                          1.0 if 'TL4' in comps else params['L4']['absorption'][s])
    # L5 / TL5
    if 'TL5' in comps:
        fi['rate_demol'], fi['rate_unc'] = l5_rates(base['rate_demol'], base['rate_unc'], base['long_run_residual'],
                                                    pT['TL5']['d_demolition'], w, pT['TL5']['d_surge'])
    else:
        fi['rate_demol'], fi['rate_unc'] = l5_rates(base['rate_demol'], base['rate_unc'], base['long_run_residual'],
                                                    params['L5']['d'][s], w)
    # L6 / TL6
    r = {t: pT['TL6'][t]['r'] for t in typ} if 'TL6' in comps else params['L6']['r'][s]
    for key in ('intensity', 'intensity_upfront'):
        fi[key] = l6_intensity(fi[key], base['a13_2025'], base['red13'], r, w)
    # L7 / TL7
    target45 = a45_target(years, 'zero' if 'TL7' in comps else s)
    d45 = l7_delta(base['a45_2025'], years, target45, w)
    for key in ('intensity', 'intensity_upfront'):
        fi[key] = _add(fi[key], d45)
    # L8 / TL8: soil factor by year (TL8: the lowest soil order)
    if 'TL8' in comps:
        soil_path = {t: float(base['soil'][t]) + w * (pT['TL8'][t]['soc_low'] - float(base['soil'][t])) for t in typ}
    else:
        soil_path = {t: float(base['soil'][t]) * (1.0 - w * params['L8']['x'][s]) for t in typ}
    ds = {t: soil_path[t] - float(base['soil'][t]) for t in typ}
    for key in ('intensity', 'intensity_upfront'):
        fi[key] = _add(fi[key], ds)
    fi['soil'] = soil_path
    # L9 / TL9
    fi['brownfield_share'] = np.full(len(years), pT['TL9']['s'] if 'TL9' in comps else float(params['L9']['s'][s]))
    fi['brownfield_w'] = w
    fi['clip_soil_share'] = True
    info = dict(w=w, l1_held=held, hh=hh, S=S, a13=a13_path(base['a13_2025'], base['red13'], r, w),
                a45=a45_path(base['a45_2025'], years, target45, w), soil_path=soil_path, olf_path=olf_y,
                comps=tuple(c for c in TL_COMPONENTS if c in comps))
    return fi, join, redev, info


def tl_label(comps, components=TL_COMPONENTS):
    """'TL' for every component, TL_BASE_LABEL for none (P5 Moderate from 2027 with reoccupation), else e.g.
    'TL[TL1+TL3]'."""
    c = [x for x in components if x in comps]
    return 'TL' if len(c) == len(components) else (TL_BASE_LABEL if not c else f"TL[{'+'.join(c)}]")


def tl_table(t):
    """Table 1, theoretical-limit rows (from outputs/data/pathways/theoretical_limit.json): limit of, value, vs
    Ambitious."""
    r = t['resolved']
    st = {row[0]: row for row in t['strength']}
    mk = lambda k, how, value, source, tag, band: dict(
        item=f'{k} {TL_NAMES[k]}', pathway=f"limit of {N.TL_LIMIT_OF[k]} {LEVER_NAMES[N.TL_LIMIT_OF[k]]}"
        if N.TL_LIMIT_OF[k] else 'no lever counterpart', band=band, how=how, assumption=f"vs Ambitious: {st[k][2]}",
        value=value, source=source, tag=tag)
    TL6, TL8, TL10 = r['TL6'], r['TL8'], r['TL10']
    return [
        mk('TL1', 'L1 with f = 1: new-dwelling size = occupied area S x OLF', 'f = 1', 'DECISION (author): limit of L1',
           'DECISION', BAND_TARGET['L1']),
        mk('TL2', 'S = the highest household size in the model history from 2027; households = population / S; '
                  'household decline releases dwellings, reoccupied in proportion to each year\'s need',
           f"S = {r['TL2']['S']:.4f} ({r['TL2']['year']}; history {r['TL2']['history_first_year']}-"
           f"{r['TL2']['history_last_year']})", 'DATA: Stats NZ population and household estimates (projection history)',
           'DATA', BAND_TARGET['L2']),
        mk('TL3', 'v = 0 from 2027; the released dwellings reoccupied in proportion to need: built_t = gross_t (1 - R/G)',
           'v = 0', 'DECISION (author): limit of L3', 'DECISION', BAND_TARGET['L3']),
        mk('TL4', 'the 2026 overbuild absorbed in full in 2027 (absorption 1)', 'a = 1', 'DECISION (author): limit of L4',
           'DECISION', BAND_TARGET['L4']),
        mk('TL5', 'demolition x (1 - 0.40); the recent replacement surge removed (replacement at the long-run 1991-2023 '
                  'rate, as the Low variant)', 'd = 0.40 (demolition); surge removed', 'LITERATURE: Pellan2024; DATA: the '
           'long-run census rate', 'LITERATURE + DATA', BAND_TARGET['L5']),
        mk('TL6', 'r per typology = min(own best independent case, r_Ambitious); exceeds Ambitious only where case-study '
                  'evidence exists (detached)', ', '.join(f"{k} r = {v['r']:.3f}" + (f" ({v['own_best_building']})"
                                                                                 if v['exceeds_ambitious'] else ' (= r_Ambitious)')
                                                         for k, v in TL6.items()),
           'DATA: case studies (outputs/data/factors/factors_building.csv, 2025 factors)', 'DATA', BAND_TARGET['L6']),
        mk('TL7', 'A4-A5 = 0 from 2027 (emission-free construction sites, zero-carbon transport)', 'A4-A5 factor 0',
           'LITERATURE: ' + SOURCES['Oslo2025'], 'LITERATURE', BAND_TARGET['L7']),
        mk('TL8', 'soil factor at the lowest soil order (SOC_low) for every typology',
           ', '.join(f"{k} {v['soc_low']:.1f} (vs {v['soc_avg']:.1f})" for k, v in TL8.items()) + ' kg CO2e/m2',
           'DATA: ' + SOURCES['ChristoforatosPickeringSchipper2026'], 'DATA', BAND_TARGET['L8']),
        mk('TL9', 'L9 with s = 0.89', f"s = {r['TL9']['s']:.2f} (London)", 'DATA: ' + SOURCES['DLUHC2022'], 'DATA',
           BAND_TARGET['L9']),
        mk('TL10', 'OLF of every new building = the lowest design OLF of the independent case studies (`olf`)',
           f"{TL10['olf']:.2f} m2/person ({TL10['building']}); replaces "
           + ', '.join(f'{k} {v:.2f}' for k, v in TL10['replaces'].items()),
           'DATA: Christoforatos G, Pickering K (2025) Smart and Sustainable Built Environment, '
           'doi:10.1108/SASBE-06-2025-0304', 'DATA', 'Occupied area of every band'),
    ]


def register_tl(t):
    """(setting, value, basis) rows of the theoretical limit TL, from outputs/data/pathways/theoretical_limit.json."""
    rows = [('Theoretical limit TL', TL_DISCLAIMER + ' TL = P5 Combined (Moderate) with TL1-TL10, every lever and item '
             'at full strength from 1 January 2027 (no adoption path); 2026 untouched; every TL item at least as '
             'strong as the Ambitious setting of its lever (asserted). ' + TL_BAU_NOTE, 'DECISION (author)')]
    for r in tl_table(t):
        rows.append((r['item'], f"{r['value']}; how: {r['how']}; {r['assumption']}", tagged(r)))
    return rows
