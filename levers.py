"""
LEVERS: pure functions, lever level -> modified engine.forward inputs (MODEL v3.0.0: nine rule-based levers)
=============================================================================================================
Each lever changes one or two inputs of engine.forward (the `fwd_inputs` dict built in projection.main(), and the
households path; docs/HOOKS.md) and nothing else. No function reads module globals of projection, no file is
written and no argument is modified: every function returns new objects (or, for a lever that is off, the input
object itself, so that the identity run is the reference call of projection.main()).

AMBITION LEVELS (the 2050 Pathways Calculator, DECC 2010 and DESNZ 2023; EUCalc D2.5, 2020)
  Reference  = Level 1   the lever's native parameter at its Reference value (the lever is off)
  Moderate   = Level 2   the exact midpoint between Reference and Ambitious in the native parameter (per year for the
                         path levers L1 and L9)
  Ambitious  = Level 3   the best value already achieved, by the first applicable sub-rule:
                 A  a case-study distribution exists -> Harrell-Davis q0.15 of the pooled scale-free case ratios
                    (the top-15% convention of the EU Taxonomy, Delegated Regulation 2021/2139, Annex I s. 7.7),
                    with a percentile bootstrap interval;
                 B  an NZ record with no structural trend exists -> the best value ever observed in NZ;
                 C  otherwise -> a published reference value (official projection > legislated target >
                    peer-reviewed scenario > peer-country value)
  TL         = Level 4   the definitional zero / full where one exists, else the best single observation; every TLn
                         is asserted at least as strong as Ambitious (tl_strength)
Levels between Reference and Ambitious are indexed by lambda in [0, 1] (the native parameter
x(lambda) = x_ref + lambda (x_amb - x_ref)); Moderate is lambda = 0.5 exactly (the lambda-sweep of the Extended Data).

ADOPTION. Every level, TL included, moves from the Reference along the normalised logistic 2026 -> 2035 (midpoint
2030.5, k = ln(81) / 6; RECC full roll-out by 2035, Pauliuk et al. 2024): x(y) = x_ref + w(y) (x_level - x_ref).
Sensitivities: by 2030, by 2045 (the Pathways) and the instant TL (full strength from 2027). Years: model index 0 = 2025,
1 = 2026 (observed; no lever touches it).

LEVERS (MODEL v3.3.0: grouped by the PAS 2080:2023 hierarchy, naming.STRATEGY_LEVERS; sub-rule naming.LEVER_SUBRULE;
settings unchanged from MODEL v3.0.0, only grouping, numbering, names and order changed: naming.LEVER_V3_2)
  S1 Avoid    L1 Household size [C]    S = S_ref + gap, gap = Stats NZ High - Medium household size (held at its 2043
                                       value after 2043)
              L2 Vacancy rate [B]      vacancy parameter -> the 1996 census minimum (one definition)
              L3 Building lifetime [C] demolition and the recent-surge component x (1 - d), d = 0.40
              L4 Extra space [B]       share f of the extra-space margin (size - occupied area) removed, applied
                                       after L5; f_amb,t = (size_ref - size_min) / (size_ref - occ_ref), size_min = the
                                       smallest annual mean consented size 1990-2025
              L5 Occupancy density [A] every typology's OLF and dwelling size x r, r = HD q0.15 of the 16 case-study
                                       ratios OLF_i / typology median
  S2 Switch   L6 Brownfield-first development [C] share s of new floor area on previously developed land, 0.59
              L7 Soil-aware planning [C] soil carbon loss per m2 x (1 - x), x = 0.146
              L8 Material carbon efficiency [A] A1-A3 x r, r = HD q0.15 of the case ratios A1-A3_i / pooled
  S3 Improve  L9 Construction-stage carbon [C]  A4-A5 linear to zero by 2050
  Moderate / Ambitious Pathway: every lever at that setting.
Resolved values: outputs/data/pathways/levers.json.
"""
import math

import numpy as np
import pandas as pd

import naming as N

LEVERS = tuple(N.LEVERS)                          # ('L1', ..., 'L9'), in the PAS 2080 order
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
    'L7': 'None: soil carbon loss per m2 of every soil-bearing band',
    'L6': 'None: the soil-bearing share of every band'}
LEVER_PARAMETER = {'L4': 'f, share of the extra-space margin removed (engine `size`), per typology',
                   'L5': 'r, design density ratio (engine `olf` and `size`), per typology',
                   'L1': 'S, household size path (households = population / S)',
                   'L2': 'v, vacancy-rate parameter (engine `v`)',
                   'L3': 'd, reduction of demolition and of the recent-surge component (`rate_demol`, `rate_unc`)',
                   'L8': 'r, A1-A3 ratio (`intensity`, A1-A3 term only), per typology',
                   'L9': 'A4-A5 factor path relative to 2025 (`intensity`, A4-A5 term only)',
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
HD_BOOTSTRAP_SEED = 20261008      # L8 (as MODEL v2.1); L5 uses seed + 1
L4_CONSENT_YEARS = (1990, 2025)
L4_FULL_STRENGTH_YEAR = 2035      # occ_ref = S_ref(2035) x OLF_t: the size at full strength equals size_min
L4_REPORT_YEARS = (2035, 2050)
L5_N_CASES = 16
L5_TYPOLOGIES = ('Detached', 'Townhouses', 'Apartments')
L1_VARIANTS = ('Low', 'Medium', 'High')
L1_REFERENCE_VARIANT = 'Medium'
L1_AMBITIOUS_VARIANT = 'High'
L1_GAP_HELD_AFTER = 2043          # the last published Stats NZ knot
L2_VACANCY_FLOOR = 0.040          # implied vacancy must never fall below this in a non-TL run (check)
L3_D_AMBITIOUS = 0.40             # Pellan et al. 2024: demolition 150,000 -> 90,000 a year
L8_SAMPLE_TYPOLOGIES = ('Detached', 'Townhouses')
L8_MIN_CASES = 10
L9_REF_RATE = 0.01
L9_ZERO_YEAR = 2050
L7_X_AMBITIOUS = 0.146            # Christoforatos, Pickering & Schipper 2026 (SOC-aware allocation)
L6_S_AMBITIOUS = 0.59             # DLUHC 2022: England, three-year average 2018-21
L6_CONTEXT = dict(us_epa_2014_infill=0.21, england_2020_21=0.66, england_3yr=0.59, north_east=0.41, london=0.89)

SOURCES = {
    'DECC2010': 'DECC (2010) 2050 Pathways Analysis. Department of Energy and Climate Change, London (ambition levels 1-4)',
    'DESNZ2023': 'DESNZ (2023) 2050 Calculator (MacKay Carbon Calculator), user guide and methodology. Department for '
                 'Energy Security and Net Zero, London (levels 1-4)',
    'EUCalc2020': 'EUCalc (2020) D2.5: Ambition levels and the lever logic of the European Calculator. EUCalc project, '
                  'Horizon 2020 grant 730459',
    'EUTaxonomy2021': 'Commission Delegated Regulation (EU) 2021/2139 (Climate Delegated Act), Annex I, Section 7.7 '
                      '(top 15% of the national or regional building stock)',
    'HarrellDavis1982': 'Harrell FE, Davis CE (1982) A new distribution-free quantile estimator. Biometrika 69(3), 635-640',
    'EfronTibshirani1993': 'Efron B, Tibshirani RJ (1993) An Introduction to the Bootstrap. Chapman & Hall (percentile interval)',
    'StatsNZConsents': 'Stats NZ building consents by typology, floor area and number (data/derived/consents_monthly.csv)',
    'ChristoforatosPickering2025': 'Christoforatos G, Pickering K (2025) Smart and Sustainable Built '
                                   'Environment, doi:10.1108/SASBE-06-2025-0304 (16 NZ case studies)',
    'StatsNZHousehold': 'Stats NZ (2021) Family and household projections: 2018(base)-2043, Low / Medium / High '
                        'variants (data/Householddata.xlsx)',
    'StatsNZCensus': 'Stats NZ census dwelling counts 1986-2023 (data/derived/census_dwellings.csv, occ-unocc-2013.xlsx)',
    'Pellan2024': 'Pellan M, et al. (2024) Building and Environment 256, 111505 (Table 2: demolition 150,000 -> 90,000 '
                  'a year)',
    'Napiontek2025': 'Napiontek et al. (2025) Resources, Conservation and Recycling 215, 108117',
    'Horup2025': 'Horup LH, et al. (2025) Science of the Total Environment 966, 178780 (Fig. 6)',
    'Resch2021': 'Resch E, et al. (2021) Impact of urban density and building height on energy use in cities '
                 '(A4-A5 e^(-0.01 (t - 2025)), the adopted path of the model)',
    'ZeroCarbonAct2019': 'Climate Change Response (Zero Carbon) Amendment Act 2019 (NZ), s. 5Q: net zero emissions '
                         'of long-lived greenhouse gases by 2050',
    'Oslo2025': 'City of Oslo (2025) Climate and environmental requirements for the City of Oslo\'s construction '
                'sites (emission-free construction sites)',
    'ChristoforatosPickeringSchipper2026': 'Christoforatos G, Pickering K, Schipper LA (2026) Integrating soil '
                                           'organic carbon loss into building life cycle assessment and urban '
                                           'planning. Journal of Environmental Management 415, 130603, '
                                           'doi:10.1016/j.jenvman.2026.130603 (SOC-aware scenario: same developed '
                                           'area, inverse-SOC allocation, 14.6% less SOC loss than BAU)',
    'DLUHC2022': 'UK Department for Levelling Up, Housing and Communities (2022) Land use change statistics in '
                 'England: new residential addresses 2020 to 2021 (66% on previously developed land in 2020-21; 59% '
                 'three-year average; regions 41% North East - 89% London)',
    'USEPA2014': 'US EPA (2014) Residential Construction Trends in America\'s Metropolitan Regions, 2012 edition '
                 '(infill share of new residential construction, about 21% nationally)',
    'Pauliuk2024': 'Pauliuk S, et al. (2024) Journal of Industrial Ecology 28, 1699',
    'Shapley1953': 'Shapley LS (1953) A value for n-person games. In: Kuhn HW, Tucker AW (eds) Contributions to the '
                   'Theory of Games II. Annals of Mathematics Studies 28, 307-317',
    'Albrecht2002': 'Albrecht J, Francois D, Schoors K (2002) A Shapley decomposition of carbon emissions without '
                    'residuals. Energy Policy 30, 727-736',
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


def a45_ambitious(years):
    """L9 Ambitious: linear to zero in 2050, 1 - (y - 2025) / 25 (Zero Carbon Act s. 5Q; Oslo 2025)."""
    t = np.clip(np.asarray(years, float) - 2025.0, 0.0, None)
    return np.clip(1.0 - t / (L9_ZERO_YEAR - 2025.0), 0.0, None)


def a45_target(years, lam):
    """L9 target factor path at level lambda (per-year interpolation; 0.5 = Moderate = the per-year midpoint);
    lam 'tl': zero."""
    if lam == 'tl':
        return np.zeros(len(np.asarray(years)))
    ref = a45_reference(years)
    return ref + float(lam) * (a45_ambitious(years) - ref)


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
    S_med = np.asarray(S_variants[L1_REFERENCE_VARIANT]['S'], float)
    S_high = np.asarray(S_variants[L1_AMBITIOUS_VARIANT]['S'], float)
    if not np.allclose(S_med, S, rtol=1e-12, atol=0):
        raise SystemExit('STOP (L1): the Reference household size is not the Medium variant.')
    held = years > L1_GAP_HELD_AFTER
    gap_raw = S_high - S_med
    if np.any(gap_raw[~held] < 0):
        bad = [int(y) for y, g in zip(years[~held], gap_raw[~held]) if g < 0]
        raise SystemExit(f'STOP (L1): High household size below Medium in {bad}.')
    gap = np.where(held, gap_raw[int(np.where(years == L1_GAP_HELD_AFTER)[0][0])], gap_raw)
    if np.any(S_high < S_med):
        bad = [int(y) for y, h, m in zip(years, S_high, S_med) if h < m]
        raise SystemExit(f'STOP (L1): High household size below Medium in {bad}.')
    hS = B['hist_S'].dropna()
    S_tl = float(hS.max())
    S_amb = S + gap
    out['L1'] = dict(subrule='C', variants={v: yy(S_variants[v]['S']) for v in S_variants}, gap=yy(gap),
                     gap_held_after=L1_GAP_HELD_AFTER, S_ref=yy(S),
                     S={'reference': yy(S), 'moderate': yy(S + gap / 2.0), 'ambitious': yy(S_amb)},
                     tl=S_tl, tl_year=int(hS.idxmax()), high_ge_medium_every_year=True,
                     anchor=f'Stats NZ High - Medium household size gap (2050: +{gap[-1]:.4f})')

    # ---- L2 Vacancy [B] ----
    v0 = float(B['v_forward'])
    vc = B['vacancy_consistent']
    v_min, y_min = float(vc.min()), int(vc.idxmin())
    out['L2'] = dict(subrule='B', v={'reference': v0, 'moderate': (v0 + v_min) / 2.0, 'ambitious': v_min}, tl=0.0,
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
    cases6, pooled6 = case_ratios(factors_building)
    est6 = hd_estimate(cases6['ratio'].values, HD_Q, bootstrap_B, HD_BOOTSTRAP_SEED)
    r6 = est6['r']
    if len(cases6) < L8_MIN_CASES or r6 >= 1.0:
        raise SystemExit(f'STOP (L8): n = {len(cases6)}, r = {r6:.4f}.')
    fb = factors_building.set_index('id')
    tl6 = {}
    for t in typ:
        g = fb[fb['Typology'] == t]
        pooled = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        ind = g[g['duplicate_of'].fillna('') == '']
        ratios = (ind['A1-A3'] / pooled).sort_values()
        evidence = len(ind) >= 2
        own = float(ratios.iloc[0]) if evidence else None
        tl6[t] = dict(n_independent=int(len(ind)), pooled_a13=pooled, own_best=own,
                      own_best_case=str(ratios.index[0]) if evidence else None, r=min(own, r6) if evidence else r6,
                      rule='min(own best independent case, r_Ambitious)' if evidence else
                           'r_Ambitious (one independent case)')
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    out['L8'] = dict(subrule='A', n=int(len(cases6)), sample_typologies=list(L8_SAMPLE_TYPOLOGIES),
                     cases=cases6.to_dict(orient='records'), pooled_a13=pooled6, a13_2025_pooled=a13,
                     estimator=est6, r={'reference': 1.0, 'moderate': (1.0 + r6) / 2.0, 'ambitious': r6},
                     tl={t: v['r'] for t, v in tl6.items()}, tl_detail=tl6,
                     anchor=f'HD q0.15 of the {len(cases6)} case ratios = {r6:.4f}')
    # MODEL v3.1.0 (A5): check row, report only: the estimator with the apartment case A_1 included (n = 15). A_1 is the
    # one independent apartment case (A_2 is its duplicate_of), so its ratio to the apartment pooled value is ~1 by
    # construction and carries no information on the spread; the adopted sample (n = 14) stays.
    cases15, _ = case_ratios(factors_building, L8_SAMPLE_TYPOLOGIES + ('Apartments',))
    est15 = hd_estimate(cases15['ratio'].values, HD_Q, bootstrap_B, HD_BOOTSTRAP_SEED)
    out['L8']['check_with_A_1'] = dict(n=int(len(cases15)), r=float(est15['r']), ci_lo=est15.get('ci_lo'),
                                       ci_hi=est15.get('ci_hi'), adopted_n=int(len(cases6)), adopted_r=float(r6),
                                       A_1_ratio=float(cases15.loc[cases15['id'] == 'A_1', 'ratio'].iloc[0]),
                                       note='report only; the adopted estimate keeps n = 14 (Detached, Townhouses)')

    # ---- L9 Construction-stage carbon [C] ----
    a45 = {t: float(B['MAT_STAGE']['A4-A5'][t].sum()) for t in typ}
    ref45 = a45_reference(years)
    red45 = {t: np.asarray(B['RED45_TOT'][t], float) for t in typ}
    chk = max(float(np.max(np.abs(a45[t] * (1.0 - ref45) - red45[t]))) for t in typ)
    if chk > 1e-9:
        raise SystemExit(f'L9: the model A4-A5 path is not a45_2025 x e^(-0.01 (y - 2025)) (max abs diff {chk:.2e}).')
    out['L9'] = dict(subrule='C', a45_2025=a45, target={lv: yy(a45_target(years, LAMBDA[lv])) for lv in LAMBDA},
                     tl=0.0, reference_check_max_abs=chk,
                     anchor='A4-A5 linear to zero by 2050 (Zero Carbon Act s. 5Q; Oslo 2025)',
                     assumption='A5 treated as energy: site waste assumed eliminated (upper bound)')

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
                                     'ambitious': L6_S_AMBITIOUS}, tl=1.0, s_ref_basis='the v3 Reference: replacement '
                     '(soil-free) floor area / total, ratio of sums 2026-2050', context=dict(L6_CONTEXT),
                     anchor='59% of new floor area on previously developed land (England 2018-21, DLUHC 2022)',
                     note='lambda = 0 is the lever off (the Reference); a constant s = s_ref would act in the years whose '
                          'own replacement share is below s_ref')
    out['tl_strength'] = tl_strength(out, years)
    return out


def tl_strength(p, years):
    """Every TLn against the Ambitious level of Ln (at least as strong in every typology and year)."""
    yrs = [int(y) for y in years]
    amb3 = np.array([by_year(p['L1']['S']['ambitious'], y) for y in yrs])
    soil = p['L7']['soil_factor_2025']
    return [
        dict(item='TL4', tl='f = 1', ambitious=str({t: round(v, 4) for t, v in p['L4']['f']['ambitious'].items()}),
             ok=all(1.0 >= v for v in p['L4']['f']['ambitious'].values())),
        dict(item='TL5', tl=str({t: round(v, 4) for t, v in p['L5']['tl'].items()}),
             ambitious=f"r = {p['L5']['r']['ambitious']:.4f}",
             ok=all(v <= p['L5']['r']['ambitious'] for v in p['L5']['tl'].values())),
        dict(item='TL1', tl=f"S = {p['L1']['tl']:.4f}", ambitious=f'S_amb max {amb3.max():.4f}',
             ok=bool(np.all(p['L1']['tl'] >= amb3))),
        dict(item='TL2', tl='v = 0', ambitious=f"v = {p['L2']['v']['ambitious']:.4f}", ok=0.0 <= p['L2']['v']['ambitious']),
        dict(item='TL3', tl='d = 1 (demolition and surge)', ambitious=f"d = {p['L3']['d']['ambitious']}",
             ok=min(p['L3']['tl'].values()) >= p['L3']['d']['ambitious']),
        dict(item='TL8', tl=str({t: round(v, 4) for t, v in p['L8']['tl'].items()}),
             ambitious=f"r = {p['L8']['r']['ambitious']:.4f}",
             ok=all(v <= p['L8']['r']['ambitious'] for v in p['L8']['tl'].values())),
        dict(item='TL9', tl='A4-A5 = 0', ambitious='linear to zero in 2050', ok=bool(np.all(a45_ambitious(years) >= 0.0))),
        dict(item='TL7', tl=str({t: round(v, 2) for t, v in p['L7']['tl'].items()}),
             ambitious=f"x = {p['L7']['x']['ambitious']}",
             ok=all(p['L7']['tl'][t] <= soil[t] * (1 - p['L7']['x']['ambitious']) for t in soil)),
        dict(item='TL6', tl='s = 1', ambitious=f"s = {p['L6']['s']['ambitious']}", ok=1.0 >= p['L6']['s']['ambitious'])]


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


def native(p, lever, level, years):
    """The native parameter of `lever` at `level` (by typology for L4, L5, L8, L7; by year for L1, L9; scalars
    otherwise). Moderate is the exact midpoint of Reference and Ambitious (lambda = 0.5)."""
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
        return np.full(len(years), p['L1']['tl']) if tl else S + lam * gap
    if lever == 'L2':
        return p['L2']['tl'] if tl else interp(p['L2']['v']['reference'], p['L2']['v']['ambitious'])
    if lever == 'L3':
        return dict(p['L3']['tl']) if tl else dict(d_demolition=lam * p['L3']['d']['ambitious'],
                                                    d_surge=lam * p['L3']['d']['ambitious'])
    if lever == 'L8':
        return dict(p['L8']['tl']) if tl else {t: interp(1.0, p['L8']['r']['ambitious']) for t in p['L8']['tl']}
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
    """L8: intensity_t(y) - w(y) (1 - r_t) (A1-A3_t,2025 - red13_t(y)): only the A1-A3 term is scaled, so
    A1-A3(y) = [1 - w (1 - r)] (A1-A3_2025 - reduction(y)) and decarbonisation still applies on top."""
    return {t: np.asarray(intensity[t], float) - w * (1.0 - float(r[t])) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in intensity}


def a13_path(a13_2025, red13, r, w):
    """A1-A3 intensity (kg/m2) by typology and year under L8 (r = 1: the baseline path)."""
    return {t: (1.0 - w * (1.0 - float(r[t]))) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in a13_2025}


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
    info = dict(w=w, l4_held=None, levels=dict(lv), tl=tuple(L for L in LEVERS if lv.get(L) == 'tl'))
    # L1 household size (the draw's own Reference S plus the published gap; TL1: the historical maximum)
    if 'L1' in lv:
        gap = np.array([by_year(p['L1']['gap'], int(y)) for y in years])
        if lv['L1'] == 'tl':                          # never weaker than Ambitious (a Monte Carlo draw's own S)
            target = np.maximum(p['L1']['tl'], S + gap)
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
        r6 = native(p, 'L8', lv['L8'], years)
        for k in ('intensity', 'intensity_upfront'):
            fi[k] = l8_intensity(fi[k], base['a13_2025'], base['red13'], r6, w)
    # L9 construction-stage carbon
    target45 = None
    if 'L9' in lv:
        target45 = native(p, 'L9', lv['L9'], years)
        d45 = l9_delta(base['a45_2025'], years, target45, w)
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
    if info['tl']:
        fi['clip_soil_share'] = True                  # zero-building years possible in TL-family runs
    info.update(hh=hh, S=S, r6=r6, a13=a13_path(base['a13_2025'], base['red13'], r6, w),
                a45=a45_path(base['a45_2025'], years, target45, w), soil_path=soil_path)
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
# THEORETICAL LIMIT TL (MODEL v3.0.0): Level 4 of every lever -- a thought experiment, not a pathway
# ============================================================
TL_COMPONENTS = tuple(f'TL{k}' for k in range(1, 10))
TL_NAMES = {k: N.TL[k] for k in TL_COMPONENTS}
TL_LEVER = {f'TL{k}': f'L{k}' for k in range(1, 10)}
TL_RELEASE_ITEMS = ('TL1', 'TL2')       # their released dwellings are re-occupied (pathways.reoccupation)
TL_INSTANT_LABEL = 'TL-from2027'
TL_DISCLAIMER = ('TL is a hyper-optimistic theoretical limit; a thought experiment, not a pathway: every lever at '
                 'Level 4 (the definitional zero or full, or the best single observation), adopted by 2035, combining '
                 'best observed attributes of different buildings and places; not a proposal or a feasible pathway '
                 '(potentials hierarchy: theoretical > technical > realisable).')
TL_BAU_NOTE = ('The adopted decarbonisation applies in TL as in every run (A1-A3 item paths of Horup et al. 2025; A4-A5 '
               'e^(-0.01 (t - 2025)) until TL9 sets A4-A5 to zero).')
tl_caption = N.tl_caption


def tl_levels(comps, base_setting='moderate'):
    """{lever: level} of a TL-family run: the levers of comps (TL1..TL9) at 'tl', the others at base_setting
    ('moderate': the Moderate Pathway, the base of the TL waterfall and of its Shapley game; 'ambitious': the
    Ambitious Pathway;
    'reference': the base of the per-lever TL Shapley game of Fig8)."""
    out = {} if base_setting == 'reference' else {L: base_setting for L in LEVERS}
    out.update({TL_LEVER[c]: 'tl' for c in comps})
    return out


def tl_label(comps, base_setting='moderate'):
    c = [x for x in TL_COMPONENTS if x in comps]
    base = {'moderate': f'{PATHWAY}-moderate', 'ambitious': f'{PATHWAY}-ambitious', 'reference': 'REF'}[base_setting]
    return 'TL' if len(c) == len(TL_COMPONENTS) else (base if not c else f"{base}+{'+'.join(c)}")


OMITTED = [
    ('Lightweighting', 'the case studies give A1-A3 per m2 by material and item, not structural mass by design '
     'alternative; a mass reduction cannot be separated from the material choice already covered by L8'),
    ('Bio-based archetypes', 'no typology has a bio-based archetype among the 16 case studies, and the model\'s '
     'biogenic-carbon convention (timber C1-C4 excludes biogenic CO2) would need extending; overlaps L8'),
    ('Renovation carbon of retained buildings', 'not modelled: L3 is an upper bound of the effect of building '
     'lifetime extension (Napiontek et al. 2025)'),
]


def pct(x, nd=1):
    return f'{100 * x:.{nd}f}%'


def lever_table(p):
    """Table 1 of the paper: one row per lever with its sub-rule and anchor, and the native parameter at Moderate,
    Ambitious and TL (LEVERS_TABLE.md)."""
    rows = []
    t3 = lambda d: ', '.join(f'{k} {v:.3f}' for k, v in d.items())
    for L in LEVERS:
        q = p[L]
        if L == 'L4':
            mod, amb, tl = 'f = ' + t3(q['f']['moderate']), 'f = ' + t3(q['f']['ambitious']), 'f = 1 (size = occupied area)'
        elif L in ('L5', 'L8'):
            e = q['estimator']
            mod = f"r = {q['r']['moderate']:.4f}"
            amb = f"r = {q['r']['ambitious']:.4f} (95% CI {e['ci_lo']:.3f}-{e['ci_hi']:.3f}, n = {q['n']})"
            tl = 'r = ' + t3(q['tl'])
        elif L == 'L1':
            mod = f"S 2050 = {by_year(q['S']['moderate'], 2050):.4f}"
            amb = f"S 2050 = {by_year(q['S']['ambitious'], 2050):.4f} (Reference {by_year(q['S_ref'], 2050):.4f})"
            tl = f"S = {q['tl']:.4f} ({q['tl_year']})"
        elif L == 'L2':
            mod, amb, tl = pct(q['v']['moderate'], 2), pct(q['v']['ambitious'], 2), 'v = 0'
        elif L == 'L3':
            mod, amb, tl = f"d = {q['d']['moderate']:.2f}", f"d = {q['d']['ambitious']:.2f}", 'no demolition, no surge'
        elif L == 'L9':
            mod = f"factor 2050 = {by_year(q['target']['moderate'], 2050):.3f}"
            amb, tl = 'factor 2050 = 0 (linear from 2025)', 'A4-A5 = 0'
        elif L == 'L7':
            mod, amb = f"x = {q['x']['moderate']:.3f}", f"x = {q['x']['ambitious']:.3f}"
            tl = ', '.join(f'{t} {v:.1f}' for t, v in q['tl'].items()) + ' kg CO2e/m2 (lowest soil order)'
        else:
            mod = f"s = {q['s']['moderate']:.3f} (s_ref {q['s']['reference']:.3f})"
            amb, tl = f"s = {q['s']['ambitious']:.2f}", 's = 1'
        rows.append(dict(item=f'{L} {LEVER_NAMES[L]}', strategy=f'{LEVER_STRATEGY[L]} {STRATEGY_NAMES[LEVER_STRATEGY[L]]}',
                         subrule=q['subrule'], anchor=q['anchor'], parameter=LEVER_PARAMETER[L], band=BAND_TARGET[L],
                         moderate=mod, ambitious=amb, tl=tl))
    return rows
