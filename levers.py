"""
LEVERS: pure functions, lever -> modified engine.forward inputs
===============================================================
Each lever changes one or two inputs of engine.forward (the `fwd_inputs` dict
built in projection.main(); docs/HOOKS.md) and nothing else. No function
reads module globals of projection, no file is written and no argument is modified:
every function returns new objects (or, for a lever that is off, the input
object itself, so that the identity run is the reference call of projection.main()).

Years: model index 0 = 2025, 1 = 2026 (observed; no lever touches it). A lever
at full strength moves a quantity from its baseline b to its target x as
b + w(y) (x - b), with the adoption path (normalised logistic ramp)

    s(y) = 1 / (1 + exp(-k (y - m))),  k = ln(81) / 6,  m = 2030.5
    w(y) = (s(y) - s(2026)) / (s(2035) - s(2026))  for 2026 <= y <= 2035;  w = 1 after 2035

(10% -> 90% of s within 6 years; full roll-out by 2035 following RECC, Pauliuk et al. 2024;
sensitivities 'by2030': m = 2028.5, end 2030, and 'by2045': m = 2035.5, end 2045; same k).
Typology shares stay at the baseline (held) mix in every run: a denser typology mix was
evaluated in pathways_v2 and removed (DENSER_MIX_V2_NOTE).

Levers (settings Moderate and Ambitious; naming.LEVERS) and pathways (naming.PATHWAYS):
  P1 Right-sized dwellings   L1 Dwelling size    size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)),
                                                 occ_t(y) = S(y) OLF_t (the engine's occupied area): a share f of
                                                 the extra-space margin removed; full strength in 2035, f constant
  P2 Occupied stock          L2 Vacancy rate     stock-wide vacancy v(y) = v0 + w (v* - v0)
                             L3 Overbuild        the 2026 overbuild absorbed at rate a (engine.market_excess)
                                absorption
  P3 Retained stock          L4 Building         demolition x (1 - w d); redevelopment x (1 - w d)
                                retention
  P4 Low-carbon materials    L5 Material carbon  A1-A3_t(y) = [1 - w (1 - r)] (A1-A3_t,2025 - reduction_t(y)),
                                                 r = Harrell-Davis quantile of the case-study ratios
  P5 Combined                every lever
Resolved values (incl. the L5 estimator): outputs/pathways/levers.json.
"""
import math

import numpy as np
import pandas as pd

import engine
import naming as N

LEVERS = tuple(N.LEVERS)                          # ('L1', 'L2', 'L3', 'L4', 'L5')
SETTINGS = tuple(N.SETTINGS)                      # ('moderate', 'ambitious')
SETTING_NAMES = dict(N.SETTINGS)
LEVER_NAMES = dict(N.LEVERS)
PATHWAYS = dict(N.PATHWAY_LEVERS)                 # P1-P4 -> their levers; P5 = every lever
PATHWAY_NAMES = dict(N.PATHWAYS)
LEVER_PATHWAY = {L: P for P, ls in PATHWAYS.items() for L in ls}
# demand band(s) each lever targets (naming.BANDS; LEVERS_TABLE.md)
BAND_TARGET = {
    'L1': 'Extra space (and the dwelling size of every band except Population growth)',
    'L2': 'Vacancy (including the change in the vacancy rate)',
    'L3': '2026 overbuild',
    'L4': 'Replacement and Redevelopment',
    'L5': 'None: carbon per m2 (A1-A3) of every band'}
LEVER_PARAMETER = {'L1': 'size (engine.forward), per typology and year',
                   'L2': 'v (stock-wide vacancy rate)', 'L3': 'join, join_redev (engine.market_excess absorption)',
                   'L4': 'rate_demol, rate_unc (redevelopment component)',
                   'L5': 'intensity, intensity_upfront (A1-A3 term only)'}

OBSERVED_YEAR = 2026            # last observed year: w = 0 up to and including it
RAMP_END = 2035                 # full strength from this year (adopted: by2035)
RAMP_MID = 2030.5
RAMP_K = math.log(81.0) / 6.0   # s rises from 0.1 to 0.9 within 6 years
ADOPTION_ADOPTED = 'by2035'
ADOPTION_BY2045 = dict(name='by2045', mid=2035.5, end=2045)    # sensitivity (P5 only); same k
ADOPTION_BY2030 = dict(name='by2030', mid=2028.5, end=2030)    # sensitivity (P5 only); same k
ADOPTION_SENSITIVITIES = (ADOPTION_BY2030, ADOPTION_BY2045)
RAMP_BASIS = ('full roll-out by 2035 following RECC (Pauliuk et al. 2024, J. Ind. Ecol. 28, 1699: circular-economy '
              'strategies fully implemented by 2035)')
ATTACHED = ('Townhouses', 'Apartments')
DETACHED = 'Detached'

# ---------------------------------------------------------------------------
# PARAMETERS (author decisions, PATHWAYS v2; sources in SOURCES)
# ---------------------------------------------------------------------------
# L1: share f of the space above the occupied area (S x OLF) removed from new dwellings.
L1_F = {'moderate': 0.25, 'ambitious': 0.50}
L1_REPORT_YEARS = (2035, 2050)
L1_BENCHMARKS = {'Pellan2024': -0.065, 'Pauliuk2024_LEMD_EU_UK': 31.2 / 37.7 - 1.0}
# L2: stock-wide vacancy target v*; Moderate = midpoint of the 1986-2023 census range on a
#     consistent definition (4.0-5.4%), Ambitious = its minimum.
L2_V_STAR = {'moderate': 0.047, 'ambitious': 0.040}
L2_VACANCY_FLOOR = 0.040        # implied vacancy must never fall below this (check)
# L3: the 2026 overbuild absorbed (the existing baseline payback sensitivities)
L3_ABSORPTION = {'moderate': 0.10, 'ambitious': 0.20}
# L4: reduction d of removals (Pellan et al. 2024: demolition 150,000 -> 90,000 a year = -40%)
L4_D = {'moderate': 0.20, 'ambitious': 0.40}
# Denser typology mix (numbered L4 in pathways_v2): evaluated in pathways_v2 and removed. Values
# from tag pathways_v2, outputs/pathways/pathways_runs.csv and shapley_levers.csv (Reference;
# checked in tests/test_pathways.py). Setting keys in the release names (central = Moderate,
# stretch = Ambitious; P0 = the Reference).
DENSER_MIX_V2_NOTE = dict(
    text=('A denser typology mix (lever L4 of pathways_v2) was evaluated in pathways_v2 and removed: within the '
          'embodied-carbon scope a denser mix raises A1-A3 per m2 (attached typologies carry more per m2), while its '
          'benefits (infrastructure, operational energy, land) are outside the scope.'),
    tag='pathways_v2', attached_share={'baseline': 0.3940321454268726, 'moderate': 0.4139242880995848,
                                       'ambitious': 0.5540321454268726},
    carbon_kt={'REF': 21577.50362382947, 'moderate': 21493.26802626376, 'ambitious': 20944.022039096093},
    carbon_vs_reference_pct={'moderate': -0.3903862051617746, 'ambitious': -2.935842791534893},
    floor_area_Mm2={'REF': 89.56525459310168, 'moderate': 88.84679781127117, 'ambitious': 84.1634942040968},
    carbon_per_m2_kg={'REF': 240.9137753457731, 'moderate': 241.9138174447195, 'ambitious': 248.84924559223688},
    shapley_share_of_reference_minus_P5={'moderate': 0.016744, 'ambitious': 0.058045})
# L5: target ratio r = Harrell-Davis quantile at q of the scale-free case ratios
#     x_i = A1-A3_i / pooled A1-A3 of the case's typology (independent detached and townhouse cases)
L5_Q = {'moderate': 0.25, 'ambitious': 0.15}
L5_SAMPLE_TYPOLOGIES = ('Detached', 'Townhouses')
L5_MIN_CASES = 10
L5_BOOTSTRAP_B = 10_000
L5_BOOTSTRAP_SEED = 20261008
L5_CI = 0.95

SOURCES = {
    'Pellan2024': 'Pellan M, et al. (2024) Building and Environment 256, 111505 (Table 2)',
    'Pauliuk2024': 'Pauliuk S, et al. (2024) Journal of Industrial Ecology 28, 1699 (LEMD EU_UK: 37.7 -> 31.2 m2/cap)',
    'Napiontek2025': 'Napiontek et al. (2025) Resources, Conservation and Recycling 215, 108117',
    'Horup2025': 'Horup LH, et al. (2025) Science of the Total Environment 966, 178780 (Fig. 6)',
    'ChristoforatosPickering2025': 'Christoforatos G, Pickering K (2025) Smart and Sustainable Built '
                                   'Environment, doi:10.1108/SASBE-06-2025-0304 (16 NZ case studies)',
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
    """The adopted adoption path (name None or 'by2035') or a sensitivity ('by2030', 'by2045')."""
    if name is None or name == ADOPTION_ADOPTED:
        return ramp(years)
    for r in ADOPTION_SENSITIVITIES:
        if name == r['name']:
            return ramp(years, mid=r['mid'], end=r['end'])
    raise ValueError(f'Unknown adoption path {name!r}.')


# ============================================================
# L5 ESTIMATOR: Harrell-Davis quantile, bootstrap interval
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


def hd_bootstrap(x, q, B=L5_BOOTSTRAP_B, seed=L5_BOOTSTRAP_SEED, ci=L5_CI):
    """Nonparametric bootstrap of the cases (resampled with replacement, B times, fixed seed);
    percentile interval (Efron & Tibshirani 1993). Returns (lo, hi, draws)."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    w = hd_weights(len(x), q)
    draws = np.sort(x[idx], axis=1) @ w
    lo, hi = np.percentile(draws, [100 * (1 - ci) / 2, 100 * (1 + ci) / 2])
    return float(lo), float(hi), draws


def case_ratios(fb, typologies=L5_SAMPLE_TYPOLOGIES):
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
# TARGETS FROM DATA (resolved once per projection state)
# ============================================================
def attached_share(shares):
    return sum(shares[t] for t in ATTACHED)


def household_size(B):
    """S(y) = population / households of the median path (the engine's S)."""
    return np.asarray(B['df_forecast']['PopTotal_50th'].values, float) / np.asarray(B['households_forecast']['50th'], float)


def resolve(B, factors_building, settings):
    """Every lever's parameters at Moderate and Ambitious, with the targets computed from the data
    in the projection state B (projection.main() locals), the projection module settings (`settings`: the projection
    module, for DWELLING_SIZE_REF, COL_TYPOLOGIES and OVERBUILD_GAP_REF) and the case-study
    table. Returns a dict (written to outputs/pathways/levers.json)."""
    typ = list(B['typ_names'])
    years = np.asarray(B['forecast_years'])
    w = ramp(years)
    # L1
    size_ref = {t: float(B['size_ref'][t]) for t in typ}
    olf = {t: float(B['OLF_USED'][t]) for t in typ}
    S = household_size(B)
    implied = {}
    held = []
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
              implied=implied, held=held, benchmarks_pct={k: 100 * v for k, v in L1_BENCHMARKS.items()})
    # L2 / L3
    v0 = float(B['v_forward'])
    c, p = B['census'], B['census_18_23']
    share = sum(p[y]['empty'] for y in p) / sum(p[y]['unoccupied'] for y in p)
    v_cons = (c['unoccupied'] * share / c['total_private']).dropna()
    L2 = dict(v0=v0, v_star=dict(L2_V_STAR), floor=L2_VACANCY_FLOOR,
               census_consistent={int(k): float(v) for k, v in v_cons.items()},
               census_consistent_min=float(v_cons.min()), census_consistent_max=float(v_cons.max()),
              census_consistent_min_year=int(v_cons.idxmin()), census_consistent_max_year=int(v_cons.idxmax()),
              consistent_empty_share=float(share),
               census_consistent_midpoint=float((v_cons.min() + v_cons.max()) / 2.0))
    L3 = dict(absorption=dict(L3_ABSORPTION), O26=float(B['join_info']['50th']['O26']),
               rho=float(B['rho_other']), gap_ref=str(settings.OVERBUILD_GAP_REF))
    # L4
    L4 = dict(d=dict(L4_D), demolition_rate=float(B['demolition_rate']),
              long_run_residual=float(B['unconsented_rate']),
              long_run_net=float(B['demolition_rate'] + B['unconsented_rate']))
    # typology shares: the baseline (held) mix in every run (denser mix removed; DENSER_MIX_V2_NOTE)
    held_sh = B['held_shares']
    denser = dict(removed=True, note=DENSER_MIX_V2_NOTE, baseline_shares={t: float(held_sh[t]) for t in typ})
    # L5
    cases, pooled = case_ratios(factors_building)
    x = cases['ratio'].values
    from scipy.stats.mstats import hdquantiles
    est = {}
    for s in SETTINGS:
        q = L5_Q[s]
        r = hd_quantile(x, q)
        lo, hi, _ = hd_bootstrap(x, q)
        est[s] = dict(q=q, r=r, ci_lo=lo, ci_hi=hi, scipy_hdquantiles=float(np.asarray(hdquantiles(x, prob=[q]))[0]),
                      weights=[float(v) for v in hd_weights(len(x), q)])
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    L5 = dict(n=int(len(x)), sample_typologies=list(L5_SAMPLE_TYPOLOGIES), min_cases=L5_MIN_CASES,
              cases=cases.to_dict(orient='records'), pooled_a13=pooled, a13_2025_pooled=a13,
              pooled_check_max_abs=float(max(abs(pooled[t] - a13[t]) for t in pooled)),
              estimator=est, r={s: {t: est[s]['r'] for t in typ} for s in SETTINGS},
              r_apartments_held={s: {t: (1.0 if t == 'Apartments' else est[s]['r']) for t in typ} for s in SETTINGS},
              bootstrap=dict(B=L5_BOOTSTRAP_B, seed=L5_BOOTSTRAP_SEED, ci=L5_CI, method='percentile'))
    return dict(adoption=dict(form='normalised logistic', k=RAMP_K, mid=RAMP_MID, start=OBSERVED_YEAR, end=RAMP_END,
                              adopted=ADOPTION_ADOPTED, basis=RAMP_BASIS, w={int(y): float(v) for y, v in zip(years, w)},
                              sensitivity=dict(ADOPTION_BY2045),
                              sensitivities=[dict(r) for r in ADOPTION_SENSITIVITIES],
                              w_sensitivity={int(y): float(v) for y, v in zip(years, ramp_named(years, 'by2045'))},
                              w_sensitivity_2030={int(y): float(v) for y, v in zip(years, ramp_named(years, 'by2030'))}),
                L1=L1, denser_mix_pathways_v2=denser, L2=L2, L3=L3, L4=L4, L5=L5)


def stop_checks(p):
    """STOP conditions of the lever parameters (raises SystemExit)."""
    if p['L5']['n'] < L5_MIN_CASES:
        raise SystemExit(f"STOP (L5): {p['L5']['n']} independent cases < {L5_MIN_CASES}.")
    for s in SETTINGS:
        if p['L5']['estimator'][s]['r'] >= 1.0:
            raise SystemExit(f"STOP (L5): Harrell-Davis r = {p['L5']['estimator'][s]['r']:.4f} >= 1 ({s}).")


# ============================================================
# LEVER FUNCTIONS (each returns new inputs; strength 0 = baseline values)
# ============================================================
def l1_size(size_ref, olf, S, f, w):
    """L1: size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)), occ_t = S(y) OLF_t.
    Where size_ref_t <= occ_t(y) the typology / year is held at size_ref_t (rule). Returns
    (size {typology: array}, held {typology: bool array})."""
    S = np.asarray(S, float)
    size, held = {}, {}
    for t in size_ref:
        occ = S * float(olf[t])
        ref = float(size_ref[t])
        h = ref <= occ
        size[t] = np.where(h, ref, occ + (1.0 - float(f) * w) * (ref - occ))
        held[t] = h
    return size, held


def l2_vacancy(v0, v_star, w):
    """L2: stock-wide vacancy v(y) = v0 + w(y) (v* - v0)."""
    return float(v0) + w * (float(v_star) - float(v0))


def l3_join(E_nojoin, O26, rho, gap_ref, absorption):
    """L3: the 2026 overbuild (near-term market excess) with the surplus absorbed at rate `absorption`
    (engine.market_excess, mode 'surplus'), from the baseline forward run WITHOUT a join
    and the same observed 2026 building, rho and gap reference. Returns (join, redev)."""
    join, ji = engine.market_excess(E_nojoin, O26, rho, gap_ref, 'surplus', absorption)
    return join, ji['redev']


def l4_rates(rate_demol, rate_unc, long_run_residual, d, w):
    """L4: demolition rate x (1 - w d); the redevelopment component of the residual
    path (rate_unc - long-run residual) x (1 - w d); the long-run residual untouched."""
    f = 1.0 - w * float(d)
    return float(rate_demol) * f, float(long_run_residual) + (np.asarray(rate_unc, float) - long_run_residual) * f


def l5_intensity(intensity, a13_2025, red13, r, w):
    """L5: intensity_t(y) - w(y) (1 - r_t) (A1-A3_t,2025 - red13_t(y)): only the A1-A3 term is
    scaled, so A1-A3(y) = [1 - w (1 - r)] (A1-A3_2025 - reduction(y)) and decarbonisation
    still applies on top; A4-A5 and soil unchanged."""
    return {t: np.asarray(intensity[t], float) - w * (1.0 - float(r[t])) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in intensity}


def a13_path(a13_2025, red13, r, w):
    """A1-A3 intensity (kg/m2) by typology and year under L5 (r = 1: the baseline path)."""
    return {t: (1.0 - w * (1.0 - float(r[t]))) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in a13_2025}


def apply(base, params, active, ramp_name=None, E_nojoin=None, l5_apartments_held=False):
    """Modified engine.forward inputs for the levers in `active` ({lever: 'moderate' | 'ambitious'}).

    base: dict with fwd_inputs, years, pop, hh, size_ref, olf, v0, rate_demol, rate_unc,
    long_run_residual, held_shares, a13_2025, red13, join, join_redev, O26, rho, gap_ref
    (pathways.base_context). A lever not in `active` leaves its inputs as the very objects of
    the reference run. Returns (inputs, join, join_redev, info)."""
    unknown = set(active) - set(LEVERS)
    if unknown or not set(active.values()) <= set(SETTINGS):
        raise ValueError(f'Unknown lever or setting in {active}.')
    fi = dict(base['fwd_inputs'])                         # same objects; replaced below if a lever is on
    w = ramp_named(base['years'], ramp_name)
    join, redev = base['join'], base['join_redev']
    info = dict(w=w, l1_held=None)
    if 'L1' in active:
        S = np.asarray(base['pop'], float) / np.asarray(base['hh'], float)
        fi['size'], info['l1_held'] = l1_size(base['size_ref'], base['olf'], S, params['L1']['f'][active['L1']], w)
    if 'L2' in active:
        fi['v'] = l2_vacancy(base['v0'], params['L2']['v_star'][active['L2']], w)
    if 'L3' in active:
        if E_nojoin is None:
            raise ValueError('L3 needs the baseline forward run without a join (E_nojoin).')
        join, redev = l3_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'],
                              params['L3']['absorption'][active['L3']])
    if 'L4' in active:
        fi['rate_demol'], fi['rate_unc'] = l4_rates(base['rate_demol'], base['rate_unc'],
                                                    base['long_run_residual'], params['L4']['d'][active['L4']], w)
    r = {t: 1.0 for t in base['a13_2025']}
    if 'L5' in active:
        r = params['L5']['r_apartments_held' if l5_apartments_held else 'r'][active['L5']]
        fi['intensity'] = l5_intensity(base['fwd_inputs']['intensity'], base['a13_2025'], base['red13'], r, w)
        fi['intensity_upfront'] = l5_intensity(base['fwd_inputs']['intensity_upfront'], base['a13_2025'],
                                               base['red13'], r, w)
    info['a13'] = a13_path(base['a13_2025'], base['red13'], r, w)
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


# ============================================================
# REGISTER (ASSUMPTIONS.md "Pathways" section), LEVERS_TABLE.md and the methods draft
# ============================================================
OMITTED = [
    ('Occupancy / household size', 'household size is a demographic input of the baseline (Stats NZ household '
     'projections, projection.HH_SIZE_VARIANT) and sets the number of households, not a construction choice; a lever on it '
     'needs a behavioural or policy model of household formation that the model does not have (Population growth and '
     'Smaller households are untargeted by design, as in Pellan et al. 2024)'),
    ('Brownfield soil', 'the soil factor is one area-weighted value for Auckland land zoned for urbanisation '
     '(Christoforatos, Pickering & Schipper 2026) and soil carbon loss is already zero on the replacement bands; no '
     'national brownfield share is in the inputs to parameterise a shift (TL6 Urban infill bounds it in the '
     'theoretical limit)'),
    ('Lightweighting', 'the case studies give A1-A3 per m2 by material and item, not structural mass by design '
     'alternative; a mass reduction cannot be separated from the material choice already covered by L5'),
    ('Bio-based archetypes', 'no typology has a bio-based archetype among the 16 case studies, and the model\'s '
     'biogenic-carbon convention (timber C1-C4 excludes biogenic CO2) would need extending; overlaps L5'),
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
    """Table 1 of the paper, lever rows: item, pathway, demand band targeted, how it works (model
    terms), assumption, Moderate, Ambitious, source with full citation, tag."""
    L1, L2, L3, L4, L5 = p['L1'], p['L2'], p['L3'], p['L4'], p['L5']
    e = L5['estimator']
    return [
        dict(item='L1 ' + LEVER_NAMES['L1'], pathway='P1 ' + PATHWAY_NAMES['P1'], band=BAND_TARGET['L1'],
             how='size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)), occ_t = S(y) x OLF_t (engine `size`): a '
                 'share f of the extra-space margin (new-dwelling size - occupied area) is removed; full strength in '
                 '2035, f constant to 2050, so sizes then follow S(y)',
             assumption='new dwellings keep the occupied area S x OLF of the engine; only the space above it shrinks',
             moderate=f"f = {L1['f']['moderate']:.2f}; 2050: {_l1_text(p, 'moderate', 2050)}",
             ambitious=f"f = {L1['f']['ambitious']:.2f}; 2050: {_l1_text(p, 'ambitious', 2050)}",
             source='DECISION (author): f; benchmarks Pellan M, et al. (2024) Building and Environment 256, 111505, '
                    'Table 2 (individual dwellings 107 -> 100 m2, -6.5%); Pauliuk S, et al. (2024) Journal of '
                    'Industrial Ecology 28, 1699 (LEMD EU_UK 37.7 -> 31.2 m2/cap, -17%)', tag='DECISION'),
        dict(item='L2 ' + LEVER_NAMES['L2'], pathway='P2 ' + PATHWAY_NAMES['P2'], band=BAND_TARGET['L2'],
             how='v(y) = v0 + w(y)(v* - v0) (engine `v`); while v falls the vacancy-change term of the stock identity '
                 'releases existing dwellings once',
             assumption=f"consistent definition: the pooled 2018/2023 empty share of unoccupied dwellings "
                        f"({100 * L2['consistent_empty_share']:.1f}%) applied to every census; 4.0% is the lowest NZ "
                        f"vacancy rate on that definition in 1986-2023 ({L2['census_consistent_min_year']}: "
                        f"{pct(L2['census_consistent_min'], 2)})",
             moderate=f"{pct(L2['v0'], 2)} -> {pct(L2['v_star']['moderate'])} (midpoint of the 1986-2023 range "
                      f"{pct(L2['census_consistent_min'], 2)} ({L2['census_consistent_min_year']}) - "
                      f"{pct(L2['census_consistent_max'], 2)} ({L2['census_consistent_max_year']}))",
             ambitious=f"-> {pct(L2['v_star']['ambitious'])} (range minimum)",
             source='DATA: Stats NZ censuses 1986-2023 (data/derived/census_dwellings.csv, data/occ-unocc-2013.xlsx)',
             tag='DATA'),
        dict(item='L3 ' + LEVER_NAMES['L3'], pathway='P2 ' + PATHWAY_NAMES['P2'], band=BAND_TARGET['L3'],
             how='engine.market_excess(..., surplus, absorption a): a share a of the remaining 2026 overbuild is '
                 'absorbed each year (`join`)',
             assumption='the 2026 observed building stays; later building is lower by the absorbed overbuild',
             moderate=f"a = {L3['absorption']['moderate']:.2f} a year",
             ambitious=f"a = {L3['absorption']['ambitious']:.2f} a year",
             source='DECISION (author): the baseline payback sensitivities', tag='DECISION'),
        dict(item='L4 ' + LEVER_NAMES['L4'], pathway='P3 ' + PATHWAY_NAMES['P3'], band=BAND_TARGET['L4'],
             how='demolition x (1 - w d); redevelopment component of the residual x (1 - w d) (`rate_demol`, '
                 '`rate_unc`); the long-run residual untouched',
             assumption='renovation carbon of the kept stock not modelled (upper bound; Napiontek et al. 2025, '
                        'Resources, Conservation and Recycling 215, 108117)',
             moderate=f"d = {pct(L4['d']['moderate'], 0)}", ambitious=f"d = {pct(L4['d']['ambitious'], 0)}",
             source='LITERATURE: Pellan M, et al. (2024) Building and Environment 256, 111505 (demolition 150,000 -> '
                    '90,000 a year, -40%); Pauliuk S, et al. (2024) Journal of Industrial Ecology 28, 1699 (lifetime '
                    'extension up to +90%)', tag='LITERATURE'),
        dict(item='L5 ' + LEVER_NAMES['L5'], pathway='P4 ' + PATHWAY_NAMES['P4'], band=BAND_TARGET['L5'],
             how='A1-A3(y) = [1 - w(y)(1 - r)] (A1-A3_2025 - decarbonisation reduction(y)) (`intensity`, A1-A3 term '
                 'only); r = Harrell-Davis quantile of the case ratios A1-A3_i / pooled typology A1-A3',
             assumption='the same r for all typologies (apartments held as a sensitivity); decarbonisation on top; '
                        'A4-A5, B events, C1-C4 and soil unchanged',
             moderate=f"q = {e['moderate']['q']:.2f}: r = {e['moderate']['r']:.3f} (95% CI "
                      f"{e['moderate']['ci_lo']:.3f}-{e['moderate']['ci_hi']:.3f}), n = {L5['n']}",
             ambitious=f"q = {e['ambitious']['q']:.2f}: r = {e['ambitious']['r']:.3f} ({e['ambitious']['ci_lo']:.3f}-"
                       f"{e['ambitious']['ci_hi']:.3f})",
             source='DATA: Christoforatos G, Pickering K (2025) Smart and Sustainable Built Environment, '
                    'doi:10.1108/SASBE-06-2025-0304; Harrell FE, Davis CE (1982) Biometrika 69, 635-640; top-15% '
                    'convention of Commission Delegated Regulation (EU) 2021/2139, Annex I s. 7.7', tag='DATA / LITERATURE'),
    ]


def tl_table(t):
    """Table 1, theoretical-limit rows (from outputs/pathways/theoretical_limit.json)."""
    r = t['resolved']
    TL3, TL4, TL5 = r['TL3'], r['TL4'], r['TL5']
    ind = t['indicators']['TL']
    size50 = by_year(ind['new_dwelling_size_m2']['Detached'], 2050)
    return [
        dict(item='TL1 ' + TL_NAMES['TL1'], pathway='TL (replaces P2)', band=BAND_TARGET['L2'] + '; ' + BAND_TARGET['L3'],
             how='v = 0 from 2027 (`v`); the 2026 overbuild absorbed in full; banking rule: built_t = max(0, raw_t - '
                 'bank_(t-1)), unused release carried forward; stock-adding join = built - requirement',
             assumption='every vacant dwelling usable where needed, reallocated from 1 January 2027', value='v = 0; absorption 1',
             source='DECISION (author): theoretical limit of L2 / L3', tag='DECISION'),
        dict(item='TL2 ' + TL_NAMES['TL2'], pathway='TL (replaces P1)', band=BAND_TARGET['L1'],
             how='L1 with f = 1: size = occupied area S(t) x OLF (TL3\'s OLF) (`size`)',
             assumption='no space above the occupied area', value=f'f = 1 (2050 size {size50:.1f} m2 with TL3)',
             source='DECISION (author): theoretical limit of L1', tag='DECISION'),
        dict(item='TL3 ' + TL_NAMES['TL3'], pathway='TL', band='Occupied area of every band (population growth and '
                                                                'extra space)',
             how='OLF of every new building = the lowest design OLF (floor area / design occupants) of the independent '
                 'case studies (`olf`, all typologies)',
             assumption='an apartment-block occupancy applied to every typology',
             value=f"{TL3['olf']:.2f} m2/person ({TL3['building']}); replaces "
                   + ', '.join(f'{k} {v:.2f}' for k, v in TL3['replaces'].items()),
             source='DATA: Christoforatos G, Pickering K (2025) Smart and Sustainable Built Environment, '
                    'doi:10.1108/SASBE-06-2025-0304 (data/building_data.xlsx; duplicate '
                    + ', '.join(TL3['excluded_duplicates']) + ' excluded)', tag='DATA'),
        dict(item='TL4 ' + TL_NAMES['TL4'], pathway='TL (replaces P4)', band=BAND_TARGET['L5'],
             how='each typology\'s A1-A3 per m2 at its own best independent case, on top of decarbonisation (as L5)',
             assumption='the best observed design of each typology built everywhere',
             value=', '.join(f"{k} r = {v['r']:.3f}" + (f" ({v['building']})" if v['building'] else ' (held: one independent case)')
                             for k, v in TL4.items()),
             source='DATA: case studies (outputs/factors/factors_building.csv, 2025 factors)', tag='DATA'),
        dict(item='TL5 ' + TL_NAMES['TL5'], pathway='TL', band='Soil carbon loss of the non-replacement floor area',
             how='soil factor at the lowest soil order (SOC_low), applied exactly through the soil-bearing share',
             assumption='the lowest of 10 soil orders under every new footprint',
             value=', '.join(f"{k} {v['soc_low']:.1f} (vs {v['soc_avg']:.1f})" for k, v in TL5.items()) + ' kg CO2e/m2',
             source='DATA: Christoforatos G, Pickering K, Schipper LA (2026) Journal of Environmental Management 415, '
                    '130603 (the existing lower-bound sensitivity)', tag='DATA'),
        dict(item='TL6 ' + TL_NAMES['TL6'], pathway='TL', band='Soil carbon loss of the non-replacement floor area',
             how=f'a share s of each year\'s non-replacement new floor area 2027-2050 is on previously developed land '
                 f'(zero soil carbon loss); the rest carries the TL5 factor: soil factor x (1 - s) on the soil-bearing '
                 f'floor area',
             assumption='; '.join(TL6_ASSUMPTIONS),
             value=f's = {TL6_COMPONENTS[0]} x {TL6_COMPONENTS[1]} = {TL6_COMPONENTS[0] * TL6_COMPONENTS[1]:.3f}, '
                   f'rounded {TL6_SHARE}',
             source='DATA: ' + TL6_SOURCE + ' (Auckland monitoring); DECISION (author): national application',
             tag='DATA + DECISION'),
    ]


def register(p):
    """(setting, value, basis) rows for the resolved parameters p (resolve() / levers.json)."""
    note = DENSER_MIX_V2_NOTE
    rows = [
        ('Pathways', 'P1 Right-sized dwellings (L1 Dwelling size), P2 Occupied stock (L2 Vacancy rate + L3 Overbuild '
         'absorption), P3 Retained stock (L4 Building retention), P4 Low-carbon materials (L5 Material carbon), '
         'P5 Combined (every lever); settings Moderate and Ambitious; Reference projection, with the Low and High '
         'replacement variants for the Reference and P5; Population growth and Smaller households untargeted by '
         'design', 'DECISION (author)'),
        ('Adoption path', f"normalised logistic s(y) = 1 / (1 + exp(-k (y - {p['adoption']['mid']}))), k = ln(81)/6 = "
         f"{p['adoption']['k']:.4f}; w = (s(y) - s(2026)) / (s(2035) - s(2026)), 1 after 2035, 0 up to 2026 (full "
         "roll-out by 2035, adopted); sensitivities (P5): full roll-out by 2030 (midpoint 2028.5) and by 2045 "
         "(midpoint 2035.5), same k",
         'LITERATURE: ' + RAMP_BASIS + '; DECISION (author): the logistic form'),
        ('Typology mix', 'baseline (held) shares in every run; ' + note['text'] + ' pathways_v2 (Reference): '
         f"Moderate / Ambitious carbon {note['carbon_vs_reference_pct']['moderate']:+.2f}% / "
         f"{note['carbon_vs_reference_pct']['ambitious']:+.2f}% vs the Reference, carbon per m2 "
         f"{note['carbon_per_m2_kg']['REF']:.1f} -> {note['carbon_per_m2_kg']['moderate']:.1f} / "
         f"{note['carbon_per_m2_kg']['ambitious']:.1f} kg; lever Shapley share "
         f"{100 * note['shapley_share_of_reference_minus_P5']['moderate']:.1f}% / "
         f"{100 * note['shapley_share_of_reference_minus_P5']['ambitious']:.1f}%",
         'DECISION (author); DATA: tag pathways_v2'),
        ('2026 overbuild under the levers', 'held at the Reference path (dwellings) in every run except L3; the '
         'overbuild is the observed 2026 pipeline, not demand', 'DECISION (author)'),
        ('Vacancy check', f"implied vacancy 1 - hh / (stock + stock_join) >= {pct(p['L2']['floor'])} in every year of "
         "every run", 'DECISION (author)'),
        ('Attribution', 'Shapley values (Shapley 1953; Albrecht, Francois & Schoors 2002, Energy Policy 30, 727) over '
         'the 16 pathway subsets (main) and the 32 lever subsets (SI), exact rational arithmetic, on cumulative carbon '
         'and cumulative LoE AR; demand bands give the attribution by band exactly', 'LITERATURE; DECISION (author)'),
        ('Back-cast', 'uniform factor k on the floor area of every 2027-2050 cohort of P5 and the Reference (2026 '
         'fixed), brentq for cumulative LoE AR = 1; AtP: minimum LoE at k = 0', 'DECISION (author)'),
        ('Solution space', 'uniform cuts of 2027-2050 floor area and of non-soil carbon per m2 of the 2027-2050 '
         'cohorts, 0-100% in 5% steps, applied to the Reference', 'LITERATURE: Horup et al. 2025, Sci. Total Environ. '
         '966, 178780, Fig. 6 (form); DECISION (author)'),
    ]
    for r in lever_table(p):
        rows.append((r['item'], f"Moderate: {r['moderate']}; Ambitious: {r['ambitious']}; how: {r['how']}; "
                     f"band: {r['band']}; assumption: {r['assumption']}", f"{r['tag']}: {r['source']}"))
    rows += [(f'Omitted: {a}', 'not modelled', f'DECISION (author): {b}') for a, b in OMITTED]
    return rows


# ============================================================
# THEORETICAL LIMIT TL (PATHWAYS v3): a thought experiment, not a pathway
# ============================================================
# TL = P5 Ambitious with six overrides, all at full strength from 2027 (w = 1 in 2027-2050,
# no adoption path; 2026 observed and untouched). It combines the best observed attributes of
# different buildings and is a theoretical potential (theoretical > technical >
# realisable), not a feasible pathway.
#   TL1 No vacancy          v = 0 from 2027; the 2026 overbuild absorbed in full (absorption 1);
#                           banking rule (pathways.bank): dwellings built never negative, unused
#                           release carried forward and used before any new building
#   TL2 No extra space      L1 with f = 1: new-dwelling size = occupied area S(t) x OLF (TL3's OLF)
#   TL3 Minimum space per   OLF of all new buildings = the lowest design OLF among the independent
#       person              case studies
#   TL4 Best-practice       r per typology = its own best independent case (A1-A3 / pooled);
#       materials           apartments held at r = 1 (one independent case)
#   TL5 Lowest-carbon soils soil factor at the lowest soil order (SOC_low) for every typology
#   TL6 Urban infill        a share TL6_SHARE of the non-replacement floor area on developed land (zero soil)
TL_COMPONENTS = ('TL1', 'TL2', 'TL3', 'TL4', 'TL5', 'TL6')
TL_NAMES = {k: N.TL[k] for k in TL_COMPONENTS}
TL_DISCLAIMER = ('TL is a hyper-optimistic theoretical limit; a thought experiment, not a pathway: all assumptions at '
                 'full strength from 1 January 2027, combining best observed attributes of different buildings and '
                 'places; not a proposal or a feasible pathway (potentials hierarchy: theoretical > technical > '
                 'realisable).')
TL_BAU_NOTE = ('BAU decarbonisation applies in TL as in every run (A1-A3 item paths of Horup et al. 2025, A4-A5 '
               'e^(-0.01 (t - 2025)); the lift held at 2025 as in the Reference).')
# TL6 urban infill: share of each year's non-replacement new floor area 2027-2050 on previously
# developed land (zero soil carbon loss). Auckland Council (2021), Auckland Plan 2050 Development
# Strategy Monitoring Report, December 2021: in 2020/21, 82% of dwelling consents were in the existing
# urban area, of which 79% occurred through intensification; 0.82 x 0.79 = 0.648, rounded 0.65.
TL6_SHARE = 0.65
TL6_COMPONENTS = (0.82, 0.79)
TL6_SOURCE = ('Auckland Council (2021). Auckland Plan 2050 Development Strategy Monitoring Report, December 2021: in '
              '2020/21, 82% of dwelling consents were in the existing urban area, of which 79% occurred through '
              'intensification')
TL6_ASSUMPTIONS = (
    "(i) Auckland's observed share applied nationally (demonstrated-limit logic, as TL3 / TL4)",
    '(ii) a dwelling-count share applied to floor area',
    '(iii) intensification on developed land seals no additional soil (upper bound: some infill builds over garden soil)',
    '(iv) replacement floor area keeps its existing zero-soil treatment',
    "(v) the soil factor on the remaining share is TL5's lowest soil order")
TL_BASE_SETTING = 'ambitious'
TL_FROM2027 = 'from2027'           # adoption: full strength from 2027 (TL and its Shapley subsets)
TL_GRADUAL = 'by2035'              # TL, gradual adoption (SI): the adopted logistic path of the pathways


def ramp_from2027(years, start=OBSERVED_YEAR):
    """w = 1 from the first year after the observed year (2027), 0 up to and including 2026."""
    return (np.asarray(years, float) > start).astype(float)


def resolve_tl(chars, factors_building, factors_typology, olf_used):
    """TL parameters from the case-study data. chars: per-building characteristics
    (Building_factors.load_characteristics: Total GFA, OLF, Occupants); factors_building:
    outputs/factors/factors_building.csv (A1-A3 per m2 at 2025 factors, duplicate_of);
    factors_typology: outputs/factors/factors_typology.csv (SOC_avg, SOC_low);
    olf_used: the Reference OLF per typology (projection.OLF_USED, the pooled 'OLF_m2_per_person')."""
    fb = factors_building.set_index('id')
    independent = [i for i in fb.index if str(fb.loc[i, 'duplicate_of']) in ('', 'nan')]
    c = chars.loc[independent]
    occ_check = float((c['Total GFA'] / c['Occupants'] - c['OLF']).abs().max()) if 'Occupants' in c else None
    olf_bld = c['OLF'].astype(float)
    best = str(olf_bld.idxmin())
    TL3 = dict(building=best, typology=str(fb.loc[best, 'Typology']), olf=float(olf_bld.min()),
               per_building={str(i): float(v) for i, v in olf_bld.sort_values().items()},
               gfa_over_occupants_max_abs_diff=occ_check, excluded_duplicates=[i for i in fb.index if i not in independent],
               replaces={t: float(v) for t, v in olf_used.items()})
    TL4 = {}
    for t in factors_typology['Typology']:
        g = fb[fb['Typology'] == t]
        pooled = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        ind = g.loc[[i for i in g.index if i in independent]]
        ratios = (ind['A1-A3'] / pooled).sort_values()
        held = len(ind) < 2
        TL4[t] = dict(n_independent=int(len(ind)), pooled_a13=pooled, held=held,
                      building=None if held else str(ratios.index[0]),
                      a13=None if held else float(ind.loc[ratios.index[0], 'A1-A3']),
                      r=1.0 if held else float(ratios.iloc[0]),
                      ratios={str(i): float(v) for i, v in ratios.items()})
    ft = factors_typology.set_index('Typology')
    TL5 = {t: dict(soc_avg=float(ft.loc[t, 'SOC_avg']), soc_low=float(ft.loc[t, 'SOC_low'])) for t in ft.index}
    return dict(TL3=TL3, TL4=TL4, TL5=TL5, disclaimer=TL_DISCLAIMER, base_setting=TL_BASE_SETTING,
                start_year=OBSERVED_YEAR + 1)


def apply_tl(base, params, pT, comps, adoption=TL_FROM2027, E_nojoin=None):
    """Inputs of a TL-family run: P5 Ambitious with the overrides in `comps` (subset of TL1..TL6).
    adoption 'from2027' (w = 1 from 2027; TL and its Shapley subsets) or 'by2035' (the adopted
    logistic path; TL gradual adoption, SI). Returns (inputs, join_absorbed, join_redev, info);
    the banking rule and the soil path are applied by pathways.run_tl."""
    unknown = set(comps) - set(TL_COMPONENTS)
    if unknown:
        raise ValueError(f'Unknown TL component(s) {unknown}.')
    s = TL_BASE_SETTING
    years = base['years']
    w = ramp_from2027(years) if adoption == TL_FROM2027 else ramp_named(years, adoption)
    fi = dict(base['fwd_inputs'])
    typ = list(base['a13_2025'])
    S = np.asarray(base['pop'], float) / np.asarray(base['hh'], float)
    # TL3: OLF of every new building = the lowest independent design OLF
    if 'TL3' in comps:
        olf_y = {t: float(base['olf'][t]) + w * (pT['TL3']['olf'] - float(base['olf'][t])) for t in typ}
        fi['olf'] = olf_y
    else:
        olf_y = {t: np.full(len(years), float(base['olf'][t])) for t in typ}
    # L1 / TL2: size = occ + [1 - f w](size_ref - occ), occ = S x OLF (TL3's OLF if active)
    f = 1.0 if 'TL2' in comps else params['L1']['f'][s]
    size, held = {}, {}
    for t in typ:
        occ = S * olf_y[t]
        ref = float(base['size_ref'][t])
        held[t] = ref <= occ
        size[t] = np.where(held[t], ref, occ + (1.0 - f * w) * (ref - occ))
    fi['size'] = size
    # typology shares: the baseline (held) mix (denser mix removed)
    # L2 / L3, or TL1 (v = 0, absorption 1)
    fi['v'] = l2_vacancy(base['v0'], 0.0 if 'TL1' in comps else params['L2']['v_star'][s], w)
    if E_nojoin is None:
        raise ValueError('apply_tl needs the Reference forward run without a join (E_nojoin).')
    join, redev = l3_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'],
                          1.0 if 'TL1' in comps else params['L3']['absorption'][s])
    # L4 (unchanged, Ambitious)
    fi['rate_demol'], fi['rate_unc'] = l4_rates(base['rate_demol'], base['rate_unc'], base['long_run_residual'],
                                                params['L4']['d'][s], w)
    # L5 / TL4
    r = {t: pT['TL4'][t]['r'] for t in typ} if 'TL4' in comps else params['L5']['r'][s]
    fi['intensity'] = l5_intensity(base['fwd_inputs']['intensity'], base['a13_2025'], base['red13'], r, w)
    fi['intensity_upfront'] = l5_intensity(base['fwd_inputs']['intensity_upfront'], base['a13_2025'], base['red13'], r, w)
    # TL5 / TL6: soil path (applied exactly by pathways.run_tl through the soil-bearing share).
    # TL5: the lowest soil order; TL6: a share s of the non-replacement floor area is on developed land
    # (zero soil), so the soil factor on the soil-bearing floor area is scaled by (1 - s w).
    soil_path = None
    if 'TL5' in comps or 'TL6' in comps:
        soil_path = {}
        for t in typ:
            base_s = pT['TL5'][t]['soc_avg']
            sp = base_s + w * (pT['TL5'][t]['soc_low'] - base_s) if 'TL5' in comps else np.full(len(years), base_s)
            soil_path[t] = sp * (1.0 - TL6_SHARE * w) if 'TL6' in comps else sp
    info = dict(w=w, l1_held=held, a13=a13_path(base['a13_2025'], base['red13'], r, w), soil_path=soil_path,
                olf_path=olf_y, occupied=None, comps=tuple(c for c in TL_COMPONENTS if c in comps))
    return fi, join, redev, info


def tl_label(comps, adoption=TL_FROM2027):
    """'TL' for all six, 'P5-ambitious-from2027' for none, else e.g. 'TL[TL1+TL3]'; '-gradual' for the
    adopted logistic path (TL gradual adoption)."""
    c = [x for x in TL_COMPONENTS if x in comps]
    name = 'TL' if len(c) == len(TL_COMPONENTS) else ('P5-ambitious-from2027' if not c else f"TL[{'+'.join(c)}]")
    return name + ('' if adoption == TL_FROM2027 else '-gradual')


def register_tl(t):
    """(setting, value, basis) rows of the theoretical limit TL, from outputs/pathways/theoretical_limit.json."""
    rows = [('Theoretical limit TL', TL_DISCLAIMER + ' TL = P5 Ambitious with TL1-TL6 at full strength from 2027 '
             '(no adoption path); 2026 untouched; sensitivity: the adopted logistic adoption path (TL, gradual '
             'adoption, SI). ' + TL_BAU_NOTE, 'DECISION (author)')]
    for r in tl_table(t):
        rows.append((r['item'], f"{r['value']}; how: {r['how']}; assumption: {r['assumption']}", f"{r['tag']}: {r['source']}"))
    return rows
