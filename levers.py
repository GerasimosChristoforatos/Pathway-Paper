"""
PATHWAYS v2 LEVERS: pure functions, lever -> modified engine.forward inputs
===========================================================================
Each lever changes one or two inputs of engine.forward (the `fwd_inputs` dict
built in Boss.main(); outputs/pathways/HOOKS.md) and nothing else. No function
reads module globals of Boss, no file is written and no argument is modified:
every function returns new objects (or, for a lever that is off, the input
object itself, so that the identity run is the reference call of Boss.main()).

Years: model index 0 = 2025, 1 = 2026 (observed; no lever touches it). A lever
at full strength moves a quantity from its baseline b to its target x as
b + w(y) (x - b), with the normalised logistic ramp

    s(y) = 1 / (1 + exp(-k (y - m))),  k = ln(81) / 6,  m = 2030.5
    w(y) = (s(y) - s(2026)) / (s(2035) - s(2026))  for 2026 <= y <= 2035;  w = 1 after 2035

(10% -> 90% of s within 6 years; sensitivity 'ramp2045': m = 2035.5, end 2045).

Levers (settings 'central' and 'stretch') and pathways:
  P1 Right-size space        L1  size_t(y) = occ_t(y) + [1 - f w(y)] (size_ref_t - occ_t(y)),
                                 occ_t(y) = S(y) OLF_t (the engine's occupied area)
                             L4  attached floor-area share a0 + w (a* - a0)
  P2 Occupy the existing     L2a stock-wide vacancy v(y) = v0 + w (v* - v0)
     stock                   L2b near-term surplus absorbed at rate a (engine.market_excess)
  P3 Keep and reuse          L3  demolition x (1 - w d); redevelopment wave x (1 - w d)
  P4 Build better            L5  A1-A3_t(y) = [1 - w (1 - r)] (A1-A3_t,2025 - reduction_t(y)),
                                 r = Harrell-Davis quantile of the case-study ratios
  P5 All                     every lever
Resolved values (incl. the L5 estimator): outputs/pathways/levers.json.
"""
import math

import numpy as np
import pandas as pd

import engine

LEVERS = ('L1', 'L4', 'L2a', 'L2b', 'L3', 'L5')
SETTINGS = ('central', 'stretch')
SETTING_NAMES = {'central': 'central', 'stretch': 'stretch'}
LEVER_NAMES = {'L1': 'Right-sized new dwellings', 'L4': 'Denser typology mix', 'L2a': 'Lower vacancy',
               'L2b': 'Near-term surplus absorbed', 'L3': 'Fewer removals', 'L5': 'Best-practice materials'}
PATHWAYS = {'P1': ('L1', 'L4'), 'P2': ('L2a', 'L2b'), 'P3': ('L3',), 'P4': ('L5',)}
PATHWAY_NAMES = {'P0': 'Baseline (S3-10)', 'P1': 'Right-size space', 'P2': 'Occupy the existing stock',
                 'P3': 'Keep and reuse', 'P4': 'Build better', 'P5': 'All pathways'}
LEVER_PATHWAY = {L: P for P, ls in PATHWAYS.items() for L in ls}
# demand band(s) each lever targets (bands as Boss.export_results; LEVERS_TABLE.md)
BAND_TARGET = {
    'L1': 'Extra space per dwelling (and the dwelling size of every non-growth band)',
    'L4': 'Extra space per dwelling and dwelling size via the mix; the attached OLF also lowers the growth band',
    'L2a': 'Vacancy allowance (incl. the vacancy change)',
    'L2b': 'Near-term market excess',
    'L3': 'Replacement: long-run background (demolition) + recent redevelopment wave',
    'L5': 'None: carbon per m2 (A1-A3) of every band'}
LEVER_PARAMETER = {'L1': 'size (engine.forward), per typology and year', 'L4': 'shares (floor-area shares)',
                   'L2a': 'v (stock-wide vacancy rate)', 'L2b': 'join, join_redev (engine.market_excess absorption)',
                   'L3': 'rate_demol, rate_unc (redevelopment-wave component)',
                   'L5': 'intensity, intensity_upfront (A1-A3 term only)'}

OBSERVED_YEAR = 2026            # last observed year: w = 0 up to and including it
RAMP_END = 2035                 # full strength from this year (adopted)
RAMP_MID = 2030.5
RAMP_K = math.log(81.0) / 6.0   # s rises from 0.1 to 0.9 within 6 years
RAMP_SENS = dict(name='ramp2045', mid=2035.5, end=2045)    # sensitivity (P5 only); same k
ATTACHED = ('Townhouses', 'Apartments')
DETACHED = 'Detached'

# ---------------------------------------------------------------------------
# PARAMETERS (author decisions, PATHWAYS v2; sources in SOURCES)
# ---------------------------------------------------------------------------
# L1: share f of the space above the occupied area (S x OLF) removed from new dwellings.
L1_F = {'central': 0.25, 'stretch': 0.50}
L1_REPORT_YEARS = (2035, 2050)
L1_BENCHMARKS = {'Pellan2024': -0.065, 'Pauliuk2024_LEMD_EU_UK': 31.2 / 37.7 - 1.0}
# L2a: stock-wide vacancy target v*; central = midpoint of the 1986-2023 census range on a
#      consistent definition (4.0-5.4%), stretch = its minimum.
L2A_V_STAR = {'central': 0.047, 'stretch': 0.040}
# L2b: near-term surplus absorbed (the existing baseline payback sensitivities)
L2B_ABSORPTION = {'central': 0.10, 'stretch': 0.20}
L2_VACANCY_FLOOR = 0.040        # implied vacancy must never fall below this (check)
# L3: reduction d of removals (Pellan et al. 2024: demolition 150,000 -> 90,000 a year = -40%)
L3_D = {'central': 0.20, 'stretch': 0.40}
# L4: attached (townhouses + apartments) floor-area share target; central = observed peak
#     annual share 1991-2026 (consents), stretch = baseline share + 16 points (Pellan et al. 2024)
L4_PEAK_WINDOW = (1991, 2026)
L4_STRETCH_INCREMENT = 0.16
# L5: target ratio r = Harrell-Davis quantile at q of the scale-free case ratios
#     x_i = A1-A3_i / pooled A1-A3 of the case's typology (independent detached and townhouse cases)
L5_Q = {'central': 0.25, 'stretch': 0.15}
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
    """The adopted ramp (name None) or the 'ramp2045' sensitivity."""
    if name is None:
        return ramp(years)
    if name != RAMP_SENS['name']:
        raise ValueError(f'Unknown ramp {name!r}.')
    return ramp(years, mid=RAMP_SENS['mid'], end=RAMP_SENS['end'])


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
# TARGETS FROM DATA (resolved once per Boss state)
# ============================================================
def attached_share(shares):
    return sum(shares[t] for t in ATTACHED)


def household_size(B):
    """S(y) = population / households of the median path (the engine's S)."""
    return np.asarray(B['df_forecast']['PopTotal_50th'].values, float) / np.asarray(B['households_forecast']['50th'], float)


def resolve(B, factors_building, settings):
    """Every lever's parameters at central and stretch, with the targets computed from the data
    in the Boss state B (Boss.main() locals), the Boss module settings (`settings`: the Boss
    module, for DWELLING_SIZE_REF, COL_TYPOLOGIES and NEAR_TERM_GAP_REF) and the case-study
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
    # L2a / L2b
    v0 = float(B['v_forward'])
    c, p = B['census'], B['census_18_23']
    share = sum(p[y]['empty'] for y in p) / sum(p[y]['unoccupied'] for y in p)
    v_cons = (c['unoccupied'] * share / c['total_private']).dropna()
    L2a = dict(v0=v0, v_star=dict(L2A_V_STAR), floor=L2_VACANCY_FLOOR,
               census_consistent={int(k): float(v) for k, v in v_cons.items()},
               census_consistent_min=float(v_cons.min()), census_consistent_max=float(v_cons.max()),
               census_consistent_midpoint=float((v_cons.min() + v_cons.max()) / 2.0))
    L2b = dict(absorption=dict(L2B_ABSORPTION), O26=float(B['join_info']['50th']['O26']),
               rho=float(B['rho_other']), gap_ref=str(settings.NEAR_TERM_GAP_REF))
    # L3
    L3 = dict(d=dict(L3_D), demolition_rate=float(B['demolition_rate']),
              long_run_residual=float(B['unconsented_rate']),
              long_run_net=float(B['demolition_rate'] + B['unconsented_rate']))
    # L4: observed annual attached floor-area shares; 1991-2025 calendar years (Boss hist_shares),
    # 2026 = the model's observed 2026 mix (the latest 12 months, the 2026 row of evolving_gfa_shares)
    hs = B['hist_shares']
    att = {int(y): float(attached_share(hs.loc[y])) for y in hs.index if L4_PEAK_WINDOW[0] <= y <= L4_PEAK_WINDOW[1]}
    att[2026] = float(attached_share(B['evolving_gfa_shares'].loc[2026]))
    dc = B['df_consents']
    m26 = dc[dc['Year'] == 2026]
    col = settings.COL_TYPOLOGIES
    ytd = float(sum(m26[col[t]].sum() for t in ATTACHED) / sum(m26[col[t]].sum() for t in typ)) if len(m26) else None
    peak_year = max(att, key=att.get)
    held_sh = B['held_shares']
    a0 = float(attached_share(held_sh))
    L4 = dict(baseline_shares={t: float(held_sh[t]) for t in typ}, baseline_attached=a0, attached_by_year=att,
              attached_2026_calendar_ytd=ytd, peak_year=int(peak_year),
              target={'central': float(att[peak_year]), 'stretch': a0 + L4_STRETCH_INCREMENT},
              increment_stretch=L4_STRETCH_INCREMENT)
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
    return dict(ramp=dict(form='normalised logistic', k=RAMP_K, mid=RAMP_MID, start=OBSERVED_YEAR, end=RAMP_END,
                          w={int(y): float(v) for y, v in zip(years, w)}, sensitivity=dict(RAMP_SENS),
                          w_sensitivity={int(y): float(v) for y, v in zip(years, ramp_named(years, RAMP_SENS['name']))}),
                L1=L1, L4=L4, L2a=L2a, L2b=L2b, L3=L3, L5=L5)


def stop_checks(p):
    """STOP conditions of the lever parameters (raises SystemExit)."""
    if p['L5']['n'] < L5_MIN_CASES:
        raise SystemExit(f"STOP (L5): {p['L5']['n']} independent cases < {L5_MIN_CASES}.")
    for s in SETTINGS:
        if p['L5']['estimator'][s]['r'] >= 1.0:
            raise SystemExit(f"STOP (L5): Harrell-Davis r = {p['L5']['estimator'][s]['r']:.4f} >= 1 ({s}).")
    if p['L4']['target']['central'] >= p['L4']['target']['stretch']:
        raise SystemExit('STOP (L4): central target >= stretch target.')


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
    """L2a: stock-wide vacancy v(y) = v0 + w(y) (v* - v0)."""
    return float(v0) + w * (float(v_star) - float(v0))


def l2_join(E_nojoin, O26, rho, gap_ref, absorption):
    """L2b: the near-term market excess with the surplus absorbed at rate `absorption`
    (engine.market_excess, mode 'surplus'), from the baseline forward run WITHOUT a join
    and the same observed 2026 building, rho and gap reference. Returns (join, redev)."""
    join, ji = engine.market_excess(E_nojoin, O26, rho, gap_ref, 'surplus', absorption)
    return join, ji['redev']


def l3_rates(rate_demol, rate_unc, long_run_residual, d, w):
    """L3: demolition rate x (1 - w d); the redevelopment-wave component of the residual
    path (rate_unc - long-run residual) x (1 - w d); the long-run residual untouched."""
    f = 1.0 - w * float(d)
    return float(rate_demol) * f, float(long_run_residual) + (np.asarray(rate_unc, float) - long_run_residual) * f


def l4_shares(shares, baseline, target, w):
    """L4: attached share a0 + w (a* - a0) (w = 0 up to 2026); the increase split between
    townhouses and apartments in proportion to their baseline shares, detached reduced by
    the same amount."""
    a0 = attached_share(baseline)
    delta = w * (float(target) - a0)
    out = shares.copy()
    for t in ATTACHED:
        out[t] = shares[t].values + delta * (baseline[t] / a0)
    out[DETACHED] = shares[DETACHED].values - delta
    if (out.values < 0).any():
        raise ValueError('L4: a typology share falls below zero.')
    return out


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
    """Modified engine.forward inputs for the levers in `active` ({lever: 'central' | 'stretch'}).

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
    if 'L4' in active:
        fi['shares'] = l4_shares(base['fwd_inputs']['shares'], base['held_shares'],
                                 params['L4']['target'][active['L4']], w)
    if 'L2a' in active:
        fi['v'] = l2_vacancy(base['v0'], params['L2a']['v_star'][active['L2a']], w)
    if 'L2b' in active:
        if E_nojoin is None:
            raise ValueError('L2b needs the baseline forward run without a join (E_nojoin).')
        join, redev = l2_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'],
                              params['L2b']['absorption'][active['L2b']])
    if 'L3' in active:
        fi['rate_demol'], fi['rate_unc'] = l3_rates(base['rate_demol'], base['rate_unc'],
                                                    base['long_run_residual'], params['L3']['d'][active['L3']], w)
    r = {t: 1.0 for t in base['a13_2025']}
    if 'L5' in active:
        r = params['L5']['r_apartments_held' if l5_apartments_held else 'r'][active['L5']]
        fi['intensity'] = l5_intensity(base['fwd_inputs']['intensity'], base['a13_2025'], base['red13'], r, w)
        fi['intensity_upfront'] = l5_intensity(base['fwd_inputs']['intensity_upfront'], base['a13_2025'],
                                               base['red13'], r, w)
    info['a13'] = a13_path(base['a13_2025'], base['red13'], r, w)
    return fi, join, redev, info


def pathway_levers(pathway, setting):
    """{lever: setting} of a pathway ('P0'..'P5')."""
    if pathway == 'P0':
        return {}
    levers = LEVERS if pathway == 'P5' else PATHWAYS[pathway]
    return {L: setting for L in levers}


def label(active):
    """'P0' for no lever; otherwise e.g. 'L1:central+L4:central'."""
    return '+'.join(f'{k}:{active[k]}' for k in LEVERS if k in active) or 'P0'


# ============================================================
# REGISTER (ASSUMPTIONS.md "Pathways" section), LEVERS_TABLE.md and the methods draft
# ============================================================
OMITTED = [
    ('Occupancy / household size', 'household size is a demographic input of the baseline (Stats NZ household '
     'projections, Boss.HH_SIZE_VARIANT) and sets the number of households, not a construction choice; a lever on it '
     'needs a behavioural or policy model of household formation that v2 does not have (growth and house-splitting '
     'are untargeted by design, as in Pellan et al. 2024)'),
    ('Brownfield soil', 'the soil factor is one area-weighted value for Auckland land zoned for urbanisation '
     '(Christoforatos, Pickering & Schipper 2026) and soil is already zero on the replacement bands; no national '
     'brownfield share is in the inputs to parameterise a shift'),
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
    """Table 1 of the paper: one row per lever (pathway, band targeted, model parameter, central,
    stretch, basis with full citation, key assumption, tag)."""
    L1, L4, L2a, L2b, L3, L5 = p['L1'], p['L4'], p['L2a'], p['L2b'], p['L3'], p['L5']
    e = L5['estimator']
    return [
        dict(lever='L1 ' + LEVER_NAMES['L1'], pathway='P1 ' + PATHWAY_NAMES['P1'], band=BAND_TARGET['L1'],
             parameter=LEVER_PARAMETER['L1'],
             central=f"f = {L1['f']['central']:.2f} of the space above S x OLF removed; 2050: {_l1_text(p, 'central', 2050)}",
             stretch=f"f = {L1['f']['stretch']:.2f}; 2050: {_l1_text(p, 'stretch', 2050)}",
             basis='DECISION (author): f; benchmarks Pellan et al. (2024) Build. Environ. 256, 111505, Table 2 '
                   '(individual dwellings 107 -> 100 m2, -6.5%); Pauliuk et al. (2024) J. Ind. Ecol. 28, 1699 '
                   '(LEMD EU_UK 37.7 -> 31.2 m2/cap, -17%)',
             assumption='new dwellings keep the occupied area S x OLF of the engine; only the space above it shrinks',
             tag='DECISION'),
        dict(lever='L4 ' + LEVER_NAMES['L4'], pathway='P1 ' + PATHWAY_NAMES['P1'], band=BAND_TARGET['L4'],
             parameter=LEVER_PARAMETER['L4'],
             central=f"attached share {pct(L4['baseline_attached'])} -> {pct(L4['target']['central'])} (observed peak, {L4['peak_year']})",
             stretch=f"-> {pct(L4['target']['stretch'])} (+16 points)",
             basis='DATA: Stats NZ building consents 1991-2026 (central); LITERATURE: Pellan et al. (2024) Build. '
                   'Environ. 256, 111505 (collective 59% -> 75%) (stretch)',
             assumption='per-typology size, OLF and carbon factors unchanged; increase split by the held townhouse / apartment shares',
             tag='DATA / LITERATURE'),
        dict(lever='L2a ' + LEVER_NAMES['L2a'], pathway='P2 ' + PATHWAY_NAMES['P2'], band=BAND_TARGET['L2a'],
             parameter=LEVER_PARAMETER['L2a'],
             central=f"{pct(L2a['v0'], 2)} -> {pct(L2a['v_star']['central'])} (midpoint of the 1986-2023 range)",
             stretch=f"-> {pct(L2a['v_star']['stretch'])} (range minimum)",
             basis=f"DATA: Stats NZ censuses 1986-2023 on one empty/unoccupied share, {pct(L2a['census_consistent_min'], 2)}-"
                   f"{pct(L2a['census_consistent_max'], 2)}",
             assumption='vacancy falls through the stock identity (existing dwellings released once while the rate falls)',
             tag='DATA'),
        dict(lever='L2b ' + LEVER_NAMES['L2b'], pathway='P2 ' + PATHWAY_NAMES['P2'], band=BAND_TARGET['L2b'],
             parameter=LEVER_PARAMETER['L2b'],
             central=f"absorption {L2b['absorption']['central']:.2f} of the remaining surplus a year",
             stretch=f"{L2b['absorption']['stretch']:.2f} a year",
             basis='DECISION (author): the baseline payback sensitivities (engine.market_excess, mode surplus)',
             assumption='the 2026 observed building stays; later building is lower by the absorbed surplus',
             tag='DECISION'),
        dict(lever='L3 ' + LEVER_NAMES['L3'], pathway='P3 ' + PATHWAY_NAMES['P3'], band=BAND_TARGET['L3'],
             parameter=LEVER_PARAMETER['L3'],
             central=f"removals -{pct(L3['d']['central'], 0)} (demolition {pct(L3['demolition_rate'], 3)}/yr and the redevelopment wave)",
             stretch=f"-{pct(L3['d']['stretch'], 0)}",
             basis='LITERATURE: Pellan et al. (2024) (demolition 150,000 -> 90,000 a year, -40%); Pauliuk et al. (2024) '
                   'J. Ind. Ecol. 28, 1699 (lifetime extension up to +90%)',
             assumption='renovation carbon of the kept stock not modelled (upper bound; Napiontek et al. 2025, RCR 215, 108117); '
                        'long-run residual untouched',
             tag='LITERATURE'),
        dict(lever='L5 ' + LEVER_NAMES['L5'], pathway='P4 ' + PATHWAY_NAMES['P4'], band=BAND_TARGET['L5'],
             parameter=LEVER_PARAMETER['L5'],
             central=f"r = {e['central']['r']:.3f} (95% CI {e['central']['ci_lo']:.3f}-{e['central']['ci_hi']:.3f}), "
                     f"Harrell-Davis q = {e['central']['q']:.2f}, n = {L5['n']}",
             stretch=f"r = {e['stretch']['r']:.3f} ({e['stretch']['ci_lo']:.3f}-{e['stretch']['ci_hi']:.3f}), q = {e['stretch']['q']:.2f}",
             basis='DATA: 16 NZ case studies, Christoforatos & Pickering (2025) SASBE, doi:10.1108/SASBE-06-2025-0304 '
                   '(independent detached and townhouse cases); Harrell & Davis (1982) Biometrika 69, 635; top-15% '
                   'convention of Commission Delegated Regulation (EU) 2021/2139, Annex I s. 7.7',
             assumption='the same r for all three typologies (apartments held as a sensitivity); A1-A3 only, on top of '
                        'decarbonisation; A4-A5, B events, C1-C4 and soil unchanged',
             tag='DATA / LITERATURE'),
    ]


def register(p):
    """(setting, value, basis) rows for the resolved parameters p (resolve() / levers.json)."""
    rows = [
        ('Pathways', 'P1 Right-size space (L1 + L4), P2 Occupy the existing stock (L2a + L2b), P3 Keep and reuse '
         '(L3), P4 Build better (L5), P5 all; settings central and stretch; reference scenario S3-10, envelope S1 / S2 '
         'for P0 and P5; growth and house-splitting untargeted by design', 'DECISION (author)'),
        ('Ramp', f"normalised logistic s(y) = 1 / (1 + exp(-k (y - {p['ramp']['mid']}))), k = ln(81)/6 = "
         f"{p['ramp']['k']:.4f}; w = (s(y) - s(2026)) / (s(2035) - s(2026)), 1 after 2035, 0 up to 2026; sensitivity "
         f"ramp2045 (P5): midpoint {p['ramp']['sensitivity']['mid']}, end {p['ramp']['sensitivity']['end']}, same k",
         'DECISION (author)'),
        ('Near-term excess under the levers', 'frozen at the baseline path (dwellings) in every run except L2b; the '
         'excess is the observed 2026 pipeline, not demand', 'DECISION (author)'),
        ('L2 check', f"implied vacancy 1 - hh / (stock + stock_join) >= {pct(p['L2a']['floor'])} in every year of every run",
         'DECISION (author)'),
        ('Attribution', 'Shapley values (Shapley 1953; Albrecht, Francois & Schoors 2002, Energy Policy 30, 727) over '
         'the 16 pathway subsets (main) and the 64 lever subsets (SI), exact rational arithmetic, on cumulative carbon '
         'and cumulative LoE AR; demand bands give the attribution by band exactly', 'LITERATURE; DECISION (author)'),
        ('Back-cast', 'uniform factor k on the floor area of every 2027-2050 cohort of P5 and P0 (2026 fixed), brentq '
         'for cumulative LoE AR = 1; AtP: minimum LoE at k = 0', 'DECISION (author)'),
        ('Solution space', 'uniform cuts of 2027-2050 floor area and of non-soil carbon per m2 of the 2027-2050 '
         'cohorts, 0-100% in 5% steps, applied to P0', 'LITERATURE: Horup et al. 2025, Sci. Total Environ. 966, '
         '178780, Fig. 6 (form); DECISION (author)'),
    ]
    for r in lever_table(p):
        rows.append((r['lever'], f"central: {r['central']}; stretch: {r['stretch']}; parameter: {r['parameter']}; "
                     f"band: {r['band']}; assumption: {r['assumption']}", f"{r['tag']}: {r['basis']}"))
    rows += [(f'Omitted in v2: {a}', 'not modelled', f'DECISION (author): {b}') for a, b in OMITTED]
    return rows


# ============================================================
# THEORETICAL LIMIT T (PATHWAYS v3): a thought experiment, not a proposal
# ============================================================
# T = P5-stretch with five overrides, all at full strength from 2027 (w = 1 in 2027-2050,
# no ramp; 2026 observed and untouched). It combines the best observed attributes of
# different buildings and is a theoretical potential (theoretical > technical >
# realisable), not a feasible pathway.
#   T1 No idle stock       v = 0 from 2027; near-term surplus absorbed in full (absorption 1);
#                          banking rule (pathways.bank): dwellings built never negative, unused
#                          release carried forward and used before any new building
#   T2 No extra space      L1 with f = 1: new-dwelling size = occupied area S(t) x OLF (T3's OLF)
#   T3 Minimum space       OLF of all new buildings = the lowest design OLF among the independent
#                          case studies
#   T4 Best materials      r per typology = its own best independent case (A1-A3 / pooled);
#                          apartments held at r = 1 (one independent case)
#   T5 Best soil           soil factor at the lowest soil order (SOC_low) for every typology
T_COMPONENTS = ('T1', 'T2', 'T3', 'T4', 'T5')
T_NAMES = {'T1': 'No idle stock', 'T2': 'No extra space', 'T3': 'Minimum space per person',
           'T4': 'Best materials', 'T5': 'Best soil'}
T_DISCLAIMER = ('T is a theoretical limit (thought experiment) combining the best observed attributes of different '
                'buildings; it is not a proposal or a feasible pathway (potentials hierarchy: theoretical > technical > '
                'realisable).')
T_BASE_SETTING = 'stretch'
T_INSTANT = 'instant'


def ramp_instant(years, start=OBSERVED_YEAR):
    """w = 1 from the first year after the observed year (2027), 0 up to and including 2026."""
    return (np.asarray(years, float) > start).astype(float)


def resolve_T(chars, factors_building, factors_typology, olf_used):
    """T parameters from the case-study data. chars: per-building characteristics
    (Building_factors.load_characteristics: Total GFA, OLF, Occupants); factors_building:
    outputs/factors/factors_building.csv (A1-A3 per m2 at 2025 factors, duplicate_of);
    factors_typology: outputs/factors/factors_typology.csv (SOC_avg, SOC_low);
    olf_used: the baseline OLF per typology (Boss.OLF_USED, the pooled 'OLF_m2_per_person')."""
    fb = factors_building.set_index('id')
    independent = [i for i in fb.index if str(fb.loc[i, 'duplicate_of']) in ('', 'nan')]
    c = chars.loc[independent]
    occ_check = float((c['Total GFA'] / c['Occupants'] - c['OLF']).abs().max()) if 'Occupants' in c else None
    olf_bld = c['OLF'].astype(float)
    best = str(olf_bld.idxmin())
    T3 = dict(building=best, typology=str(fb.loc[best, 'Typology']), olf=float(olf_bld.min()),
              per_building={str(i): float(v) for i, v in olf_bld.sort_values().items()},
              gfa_over_occupants_max_abs_diff=occ_check, excluded_duplicates=[i for i in fb.index if i not in independent],
              replaces={t: float(v) for t, v in olf_used.items()})
    T4 = {}
    for t in factors_typology['Typology']:
        g = fb[fb['Typology'] == t]
        pooled = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        ind = g.loc[[i for i in g.index if i in independent]]
        ratios = (ind['A1-A3'] / pooled).sort_values()
        held = len(ind) < 2
        T4[t] = dict(n_independent=int(len(ind)), pooled_a13=pooled, held=held,
                     building=None if held else str(ratios.index[0]),
                     a13=None if held else float(ind.loc[ratios.index[0], 'A1-A3']),
                     r=1.0 if held else float(ratios.iloc[0]),
                     ratios={str(i): float(v) for i, v in ratios.items()})
    ft = factors_typology.set_index('Typology')
    T5 = {t: dict(soc_avg=float(ft.loc[t, 'SOC_avg']), soc_low=float(ft.loc[t, 'SOC_low'])) for t in ft.index}
    return dict(T3=T3, T4=T4, T5=T5, disclaimer=T_DISCLAIMER, base_setting=T_BASE_SETTING,
                start_year=OBSERVED_YEAR + 1)


def apply_T(base, params, pT, comps, ramp_name=T_INSTANT, E_nojoin=None):
    """Inputs of a T-family run: P5-stretch with the overrides in `comps` (subset of T1..T5).
    ramp_name 'instant' (w = 1 from 2027; T and its Shapley subsets) or None (the v2 logistic
    ramp; T-ramp sensitivity). Returns (inputs, join_absorbed, join_redev, info); the banking
    rule and the soil path are applied by pathways.run_T."""
    unknown = set(comps) - set(T_COMPONENTS)
    if unknown:
        raise ValueError(f'Unknown T component(s) {unknown}.')
    s = T_BASE_SETTING
    years = base['years']
    w = ramp_instant(years) if ramp_name == T_INSTANT else ramp_named(years, ramp_name)
    fi = dict(base['fwd_inputs'])
    typ = list(base['a13_2025'])
    S = np.asarray(base['pop'], float) / np.asarray(base['hh'], float)
    # T3: OLF of every new building = the lowest independent design OLF
    if 'T3' in comps:
        olf_y = {t: float(base['olf'][t]) + w * (pT['T3']['olf'] - float(base['olf'][t])) for t in typ}
        fi['olf'] = olf_y
    else:
        olf_y = {t: np.full(len(years), float(base['olf'][t])) for t in typ}
    # L1 / T2: size = occ + [1 - f w](size_ref - occ), occ = S x OLF (T3's OLF if active)
    f = 1.0 if 'T2' in comps else params['L1']['f'][s]
    size, held = {}, {}
    for t in typ:
        occ = S * olf_y[t]
        ref = float(base['size_ref'][t])
        held[t] = ref <= occ
        size[t] = np.where(held[t], ref, occ + (1.0 - f * w) * (ref - occ))
    fi['size'] = size
    # L4 (unchanged, stretch)
    fi['shares'] = l4_shares(base['fwd_inputs']['shares'], base['held_shares'], params['L4']['target'][s], w)
    # L2a / L2b, or T1 (v = 0, absorption 1)
    fi['v'] = l2_vacancy(base['v0'], 0.0 if 'T1' in comps else params['L2a']['v_star'][s], w)
    if E_nojoin is None:
        raise ValueError('apply_T needs the baseline forward run without a join (E_nojoin).')
    join, redev = l2_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'],
                          1.0 if 'T1' in comps else params['L2b']['absorption'][s])
    # L3 (unchanged, stretch)
    fi['rate_demol'], fi['rate_unc'] = l3_rates(base['rate_demol'], base['rate_unc'], base['long_run_residual'],
                                                params['L3']['d'][s], w)
    # L5 / T4
    r = {t: pT['T4'][t]['r'] for t in typ} if 'T4' in comps else params['L5']['r'][s]
    fi['intensity'] = l5_intensity(base['fwd_inputs']['intensity'], base['a13_2025'], base['red13'], r, w)
    fi['intensity_upfront'] = l5_intensity(base['fwd_inputs']['intensity_upfront'], base['a13_2025'], base['red13'], r, w)
    # T5: soil path (applied exactly by pathways.run_T through the soil-bearing share)
    soil_path = ({t: pT['T5'][t]['soc_avg'] + w * (pT['T5'][t]['soc_low'] - pT['T5'][t]['soc_avg'])
                  for t in typ} if 'T5' in comps else None)
    info = dict(w=w, l1_held=held, a13=a13_path(base['a13_2025'], base['red13'], r, w), soil_path=soil_path,
                olf_path=olf_y, occupied=None, comps=tuple(c for c in T_COMPONENTS if c in comps))
    return fi, join, redev, info


def t_label(comps, ramp_name=T_INSTANT):
    """'T' for all five, 'P5-stretch-instant' for none, else e.g. 'T[T1+T3]'; '-ramp' for the logistic ramp."""
    c = [x for x in T_COMPONENTS if x in comps]
    name = 'T' if len(c) == 5 else ('P5-stretch-instant' if not c else f"T[{'+'.join(c)}]")
    return name + ('' if ramp_name == T_INSTANT else '-ramp')
