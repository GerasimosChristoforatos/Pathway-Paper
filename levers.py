"""
PATHWAYS v1 LEVERS: pure functions, lever -> modified engine.forward inputs
===========================================================================
Each lever changes one or two inputs of engine.forward (the `fwd_inputs` dict
built in Boss.main(); outputs/pathways/HOOKS.md) and nothing else. No function
reads module globals of Boss, no file is written and no argument is modified:
every function returns new objects (or, for a lever that is off, the input
object itself, so that the identity run is the reference call of Boss.main()).

Years: model index 0 = 2025, 1 = 2026 (observed; no lever touches it).
Ramp weight  w(y) = clip((y - 2026) / (RAMP_FULL - 2026), 0, 1): 1/9 in 2027,
full from 2035 (sensitivity: full by 2045). A lever at full strength x moves a
quantity from its baseline b to its target x as  b + w(y) (x - b).

  L1  new-dwelling size (Avoid)       size_t(y)  = size_ref_t (1 - w c_t)
  L2  use the existing stock (Avoid)  v(y) = v0 + w (v* - v0); near-term surplus
                                      absorbed at rate a (engine.market_excess)
  L3  lifetime extension (Avoid)      demolition x (1 - w d); redevelopment wave
                                      component of the residual x (1 - w d)
  L4  typology mix (Shift)            attached floor-area share a0 + w (a* - a0)
  L5  best-practice materials         A1-A3_t(y) = [1 - w (1 - r_t)] x
      (Improve)                       (A1-A3_t,2025 - decarbonisation reduction_t(y))

Settings: Moderate (M) and Ambitious (A); sources in PARAMETERS and
outputs/pathways/levers.json (resolved values, including the targets computed
from data: 1991-95 dwelling sizes, the peak attached share, case-study ratios).
"""
import math

import numpy as np
import pandas as pd

import engine

LEVERS = ('L1', 'L2', 'L3', 'L4', 'L5')
SETTINGS = ('M', 'A')
LEVER_NAMES = {'L1': 'New-dwelling size', 'L2': 'Use the existing stock', 'L3': 'Lifetime extension',
               'L4': 'Typology mix', 'L5': 'Best-practice materials'}
LEVER_GROUP = {'L1': 'Avoid', 'L2': 'Avoid', 'L3': 'Avoid', 'L4': 'Shift', 'L5': 'Improve'}
BUNDLES = {'P1': ('L1', 'L2', 'L3'), 'P2': ('L4', 'L5'), 'P3': LEVERS}
BUNDLE_NAMES = {'P0': 'Baseline (reference S3-10)', 'P1': 'Avoid (L1+L2+L3)',
                'P2': 'Shift + Improve (L4+L5)', 'P3': 'All five levers'}

OBSERVED_YEAR = 2026            # last observed year: w = 0 up to and including it
RAMP_FULL = 2035                # full strength from this year (adopted)
RAMP_FULL_SENS = 2045           # sensitivity (P3 only)
ATTACHED = ('Townhouses', 'Apartments')
DETACHED = 'Detached'

# ---------------------------------------------------------------------------
# PARAMETERS (author decisions, PATHWAYS v1; sources in SOURCES)
# ---------------------------------------------------------------------------
# L1: M = Pellan et al. (2024) Table 2, individual dwellings 107 -> 100 m2
#     (1 - 100/107 = 6.54%, used as 6.5% for every typology); A = the 1991-1995
#     mean realised new-dwelling size per typology (consents; resolved by data).
L1_C_M = 0.065
L1_SIZE_WINDOW_A = (1991, 1995)
# L2: stock-wide vacancy target v*; M = midpoint of the 1986-2023 census range on a
#     consistent definition (4.0-5.4%), A = its minimum; near-term surplus absorbed
#     at the existing baseline sensitivities (0.10 / 0.20 a year).
L2_V_STAR = {'M': 0.047, 'A': 0.040}
L2_ABSORPTION = {'M': 0.10, 'A': 0.20}
L2_VACANCY_FLOOR = 0.040        # implied vacancy must never fall below this (check)
# L3: reduction d of removals; M 20%, A 40% (Pellan et al. 2024: demolition
#     150,000 -> 90,000 a year = -40%; Pauliuk et al. 2024: lifetime extension up to +90%).
L3_D = {'M': 0.20, 'A': 0.40}
# L4: attached (townhouses + apartments) floor-area share target; M = observed peak
#     annual share 1991-2026 (consents), A = baseline share + 16 points (Pellan et al.
#     2024: collective 59% -> 75%).
L4_PEAK_WINDOW_M = (1991, 2026)
L4_A_INCREMENT = 0.16
# L5: best-practice A1-A3 per m2 relative to the pooled typology factor; M = mean of the
#     lowest ceil(n/3) independent case studies, A = the single lowest; apartments held
#     (one independent case study).
L5_HELD = ('Apartments',)

SOURCES = {
    'Pellan2024': 'Pellan M, et al. (2024) Building and Environment 256, 111505 (Table 2)',
    'Pauliuk2024': 'Pauliuk S, et al. (2024) Journal of Industrial Ecology 28, 1699',
    'Napiontek2025': 'Napiontek et al. (2025) Resources, Conservation and Recycling 215, 108117',
    'Horup2025': 'Horup LH, et al. (2025) Science of the Total Environment 966, 178780 (Fig. 6)',
    'ChristoforatosPickering2025': 'Christoforatos G, Pickering K (2025) Smart and Sustainable Built '
                                   'Environment, doi:10.1108/SASBE-06-2025-0304 (16 NZ case studies)',
}


def ramp(years, full=RAMP_FULL, start=OBSERVED_YEAR):
    """w(y) = clip((y - start) / (full - start), 0, 1)."""
    years = np.asarray(years, float)
    return np.clip((years - start) / float(full - start), 0.0, 1.0)


# ============================================================
# TARGETS FROM DATA (resolved once per Boss state)
# ============================================================
def size_window_mean(hist_typ_gfa, hist_typ_units, window):
    """Mean of the annual realised new-dwelling size (consented GFA / dwellings) per
    typology over the inclusive window: the definition of Boss.DWELLING_SIZE_REF."""
    s = hist_typ_gfa / hist_typ_units
    return {t: float(s[t].loc[window[0]:window[1]].mean()) for t in s.columns}


def l1_cuts(size_ref, size_target):
    """c_t = 1 - target / size_ref, held at 0 where the target is not smaller."""
    return {t: (1.0 - size_target[t] / size_ref[t]) if size_target[t] < size_ref[t] else 0.0
            for t in size_ref}


def attached_share(shares):
    return sum(shares[t] for t in ATTACHED)


def case_study_ratios(fb, typologies):
    """L5 ratio r_t per typology from the case-study table (factors_building.csv: kg/m2 at
    2025 factors). Independent cases only (rows with an empty duplicate_of). Pooled
    typology value as Building_factors.pool (equal weight per sub-type, then per
    building). M target = mean of the lowest ceil(n/3) independent cases; A = the
    lowest. Held typologies (one independent case) get r = 1."""
    out = {}
    for t in typologies:
        g = fb[fb['Typology'] == t]
        ind = g[g['duplicate_of'].fillna('') == ''].sort_values('A1-A3')
        pooled = float(g.groupby('Subtype')['A1-A3'].mean().mean())
        n = len(ind)
        k = int(math.ceil(n / 3.0))
        rec = dict(n_cases=int(len(g)), n_independent=int(n), pooled_a13=pooled,
                   cases=dict(zip(ind['id'], [float(v) for v in ind['A1-A3']])))
        if t in L5_HELD or n < 2:
            rec.update(held=True, k_M=0, target_M=pooled, target_A=pooled, r={'M': 1.0, 'A': 1.0},
                       cases_M=[], case_A=None)
        else:
            tm = float(ind['A1-A3'].iloc[:k].mean())
            ta = float(ind['A1-A3'].iloc[0])
            rec.update(held=False, k_M=k, target_M=tm, target_A=ta, r={'M': tm / pooled, 'A': ta / pooled},
                       cases_M=list(ind['id'].iloc[:k]), case_A=str(ind['id'].iloc[0]))
        out[t] = rec
    return out


def resolve(B, factors_building, settings):
    """Every lever's parameters at M and A, with the targets computed from the data in
    the Boss state B (Boss.main() locals), the Boss module settings used by that run
    (`settings`: the Boss module, for DWELLING_SIZE_REF, COL_TYPOLOGIES and
    NEAR_TERM_GAP_REF) and the case-study table. Returns a dict (written to
    outputs/pathways/levers.json)."""
    typ = list(B['typ_names'])
    size_ref = {t: float(B['size_ref'][t]) for t in typ}
    # L1
    s9195 = size_window_mean(B['hist_typ_gfa'], B['hist_typ_units'], L1_SIZE_WINDOW_A)
    cA = l1_cuts(size_ref, s9195)
    L1 = dict(size_ref=size_ref, size_ref_window=list(settings.DWELLING_SIZE_REF),
              size_1991_1995=s9195,
              c={'M': {t: L1_C_M for t in typ}, 'A': cA},
              held_A=[t for t in typ if cA[t] == 0.0],
              target_size={'M': {t: size_ref[t] * (1 - L1_C_M) for t in typ},
                           'A': {t: size_ref[t] * (1 - cA[t]) for t in typ}})
    # L2
    v0 = float(B['v_forward'])
    c, p = B['census'], B['census_18_23']
    share = sum(p[y]['empty'] for y in p) / sum(p[y]['unoccupied'] for y in p)
    v_cons = (c['unoccupied'] * share / c['total_private']).dropna()
    L2 = dict(v0=v0, v_star=dict(L2_V_STAR), absorption=dict(L2_ABSORPTION), floor=L2_VACANCY_FLOOR,
              census_consistent={int(k): float(v) for k, v in v_cons.items()},
              census_consistent_min=float(v_cons.min()), census_consistent_max=float(v_cons.max()),
              census_consistent_midpoint=float((v_cons.min() + v_cons.max()) / 2.0),
              O26=float(B['join_info']['50th']['O26']), rho=float(B['rho_other']),
              gap_ref=str(settings.NEAR_TERM_GAP_REF))
    # L3
    L3 = dict(d=dict(L3_D), demolition_rate=float(B['demolition_rate']),
              long_run_residual=float(B['unconsented_rate']),
              long_run_net=float(B['demolition_rate'] + B['unconsented_rate']))
    # L4: observed annual attached floor-area shares; 1991-2025 calendar years (Boss
    # hist_shares) and 2026 = the model's observed 2026 mix (the latest 12 months, as the
    # 2026 row of evolving_gfa_shares); the calendar Jan-Jul 2026 share is recorded too.
    hs = B['hist_shares']
    att_hist = {int(y): float(attached_share(hs.loc[y])) for y in hs.index
                if L4_PEAK_WINDOW_M[0] <= y <= L4_PEAK_WINDOW_M[1]}
    att_2026 = float(attached_share(B['evolving_gfa_shares'].loc[2026]))
    att_hist[2026] = att_2026
    dc = B['df_consents']
    m26 = dc[dc['Year'] == 2026]
    col = settings.COL_TYPOLOGIES
    ytd = None
    if len(m26):
        tot = float(sum(m26[col[t]].sum() for t in typ))
        ytd = float(sum(m26[col[t]].sum() for t in ATTACHED) / tot)
    peak_year = max(att_hist, key=att_hist.get)
    held = B['held_shares']
    a0 = float(attached_share(held))
    L4 = dict(baseline_shares={t: float(held[t]) for t in typ}, baseline_attached=a0,
              attached_by_year=att_hist, attached_2026_calendar_ytd=ytd,
              peak_year=int(peak_year), target={'M': float(att_hist[peak_year]), 'A': a0 + L4_A_INCREMENT},
              increment_A=L4_A_INCREMENT)
    # L5
    rat = case_study_ratios(factors_building, typ)
    a13 = {t: float(B['MAT_STAGE']['A1-A3'][t].sum()) for t in typ}
    L5 = dict(cases=rat, r={s: {t: rat[t]['r'][s] for t in typ} for s in SETTINGS}, a13_2025_pooled=a13,
              pooled_check_max_abs=float(max(abs(rat[t]['pooled_a13'] - a13[t]) for t in typ)))
    return dict(ramp=dict(observed_year=OBSERVED_YEAR, full=RAMP_FULL, full_sensitivity=RAMP_FULL_SENS),
                L1=L1, L2=L2, L3=L3, L4=L4, L5=L5)


# ============================================================
# LEVER FUNCTIONS (each returns new inputs; strength 0 = baseline values)
# ============================================================
def l1_size(size_ref, c, w):
    """L1: size_t(y) = size_ref_t x (1 - w(y) c_t), an array over the years."""
    return {t: float(size_ref[t]) * (1.0 - w * float(c[t])) for t in size_ref}


def l2_vacancy(v0, v_star, w):
    """L2(a): stock-wide vacancy v(y) = v0 + w(y) (v* - v0)."""
    return float(v0) + w * (float(v_star) - float(v0))


def l2_join(E_nojoin, O26, rho, gap_ref, absorption):
    """L2(b): the near-term market excess with the surplus absorbed at rate `absorption`
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
    """L4: attached share a0 + w (a* - a0) from 2027 (w = 0 before); the increase split
    between townhouses and apartments in proportion to their baseline shares, detached
    reduced by the same amount. Rows with w = 0 (2025, 2026) are returned unchanged."""
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
    """L5: intensity_t(y) - w(y) (1 - r_t) (A1-A3_t,2025 - red13_t(y)): only the A1-A3 term
    is scaled, so A1-A3(y) = [1 - w (1 - r)] (A1-A3_2025 - reduction(y)) and the
    decarbonisation still applies on top; A4-A5 and soil unchanged."""
    return {t: np.asarray(intensity[t], float) - w * (1.0 - float(r[t])) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in intensity}


def a13_path(a13_2025, red13, r, w):
    """A1-A3 intensity (kg/m2) by typology and year under L5 (r = 1: the baseline path)."""
    return {t: (1.0 - w * (1.0 - float(r[t]))) * (float(a13_2025[t]) - np.asarray(red13[t], float))
            for t in a13_2025}


def apply(base, params, active, ramp_full=RAMP_FULL, E_nojoin=None):
    """Modified engine.forward inputs for the levers in `active` ({lever: 'M' | 'A'}).

    base: dict with fwd_inputs, years, size_ref, v0, rate_demol, rate_unc,
    long_run_residual, held_shares, a13_2025, red13, join, join_redev, O26, rho, gap_ref
    (pathways.base_context). A lever not in `active` leaves its inputs as the very
    objects of the reference run. Returns (inputs, join, join_redev, info)."""
    unknown = set(active) - set(LEVERS)
    if unknown or not set(active.values()) <= set(SETTINGS):
        raise ValueError(f'Unknown lever or setting in {active}.')
    fi = dict(base['fwd_inputs'])                         # same objects; replaced below if a lever is on
    w = ramp(base['years'], ramp_full)
    join, redev = base['join'], base['join_redev']
    info = dict(w=w)
    if 'L1' in active:
        fi['size'] = l1_size(base['size_ref'], params['L1']['c'][active['L1']], w)
    if 'L2' in active:
        s = active['L2']
        fi['v'] = l2_vacancy(base['v0'], params['L2']['v_star'][s], w)
        if E_nojoin is None:
            raise ValueError('L2 needs the baseline forward run without a join (E_nojoin).')
        join, redev = l2_join(E_nojoin, base['O26'], base['rho'], base['gap_ref'], params['L2']['absorption'][s])
    if 'L3' in active:
        fi['rate_demol'], fi['rate_unc'] = l3_rates(base['rate_demol'], base['rate_unc'],
                                                    base['long_run_residual'], params['L3']['d'][active['L3']], w)
    if 'L4' in active:
        fi['shares'] = l4_shares(base['fwd_inputs']['shares'], base['held_shares'],
                                 params['L4']['target'][active['L4']], w)
    r = {t: 1.0 for t in base['a13_2025']}
    if 'L5' in active:
        r = params['L5']['r'][active['L5']]
        fi['intensity'] = l5_intensity(base['fwd_inputs']['intensity'], base['a13_2025'], base['red13'], r, w)
        fi['intensity_upfront'] = l5_intensity(base['fwd_inputs']['intensity_upfront'], base['a13_2025'],
                                               base['red13'], r, w)
    info['a13'] = a13_path(base['a13_2025'], base['red13'], r, w)
    return fi, join, redev, info


def label(active):
    """'P0' for no lever; otherwise e.g. 'L1:M+L3:M'."""
    return '+'.join(f'{k}:{active[k]}' for k in LEVERS if k in active) or 'P0'


# ============================================================
# REGISTER (ASSUMPTIONS.md "Pathways" section and the methods draft)
# ============================================================
OMITTED = [
    ('Occupancy / household size', 'household size is a demographic input of the baseline (Stats NZ household '
     'projections, Boss.HH_SIZE_VARIANT) and sets the number of households, not a construction choice; a lever on it '
     'needs a behavioural or policy model of household formation that v1 does not have'),
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


def register(p):
    """(setting, value, basis) rows for the resolved parameters p (resolve() / levers.json)."""
    L1, L2, L3, L4, L5 = p['L1'], p['L2'], p['L3'], p['L4'], p['L5']
    typ = list(L1['size_ref'])
    sz = lambda d: ', '.join(f'{t} {d[t]:.1f}' for t in typ)
    cA = ', '.join(f"{t} {pct(L1['c']['A'][t])}" + (' (held)' if t in L1['held_A'] else '') for t in typ)
    rr = lambda s: ', '.join(f"{t} {L5['r'][s][t]:.3f}" for t in typ)
    return [
        ('Pathway levers, settings', 'L1 size, L2 existing stock, L3 lifetime (Avoid); L4 typology mix (Shift); L5 '
         'best-practice materials (Improve); each at Moderate (M) and Ambitious (A); reference scenario S3-10, '
         'envelope S1 / S2 for P0 and P3', 'DECISION (author)'),
        ('Ramp', f"w(y) = clip((y - {p['ramp']['observed_year']}) / ({p['ramp']['full']} - "
         f"{p['ramp']['observed_year']}), 0, 1): 1/9 in 2027, full from {p['ramp']['full']}; sensitivity full by "
         f"{p['ramp']['full_sensitivity']} (P3); 2026 observed and never changed", 'DECISION (author)'),
        ('Near-term excess under the levers', 'frozen at the baseline path (dwellings) in every run except L2; the '
         'excess is the observed 2026 pipeline, not demand', 'DECISION (author)'),
        ('L1 size, M', f"size_ref x (1 - w x 6.5%) for every typology; size_ref {L1['size_ref_window'][0]}-"
         f"{L1['size_ref_window'][1]} (m2): {sz(L1['size_ref'])}; target {sz(L1['target_size']['M'])}",
         'LITERATURE: Pellan et al. 2024, Build. Environ. 256, 111505, Table 2 (individual 107 -> 100 m2)'),
        ('L1 size, A', f"1991-1995 mean realised size (m2): {sz(L1['size_1991_1995'])}; cut {cA}",
         'DATA: Stats NZ consents (data/derived/consents_monthly.csv), definition of DWELLING_SIZE_REF; a typology '
         'whose 1991-95 size is not smaller is held (DECISION)'),
        ('L2 vacancy', f"v(y) = {pct(L2['v0'], 2)} + w (v* - {pct(L2['v0'], 2)}); v* M {pct(L2['v_star']['M'])}, "
         f"A {pct(L2['v_star']['A'])}; consistent census range 1986-2023 {pct(L2['census_consistent_min'], 2)}-"
         f"{pct(L2['census_consistent_max'], 2)} (midpoint {pct(L2['census_consistent_midpoint'], 2)})",
         'DATA: census 1986-2023 on one empty/unoccupied share (tools/near_term_join.py); M midpoint, A minimum '
         '(DECISION, rounded to 0.1 point)'),
        ('L2 near-term absorption', f"engine.market_excess(..., 'surplus', absorption) with M {L2['absorption']['M']:.2f}, "
         f"A {L2['absorption']['A']:.2f} a year, from the baseline run without a join (O26 {L2['O26']:,.0f}, rho "
         f"{L2['rho']:.3f}, gap vs {L2['gap_ref']})", 'DECISION (author): the existing baseline payback sensitivities'),
        ('L2 check', f"implied vacancy 1 - hh / (stock + stock_join) >= {pct(L2['floor'])} in every year of every run",
         'DECISION (author)'),
        ('L3 lifetime extension', f"demolition {pct(L3['demolition_rate'], 3)}/yr x (1 - w d) and the redevelopment "
         f"wave (residual path - long-run residual {pct(L3['long_run_residual'], 4)}) x (1 - w d); d M "
         f"{pct(L3['d']['M'], 0)}, A {pct(L3['d']['A'], 0)}; renovation carbon not modelled (upper bound)",
         'LITERATURE: Pellan et al. 2024 (demolition 150,000 -> 90,000/yr, -40%); Pauliuk et al. 2024, J. Ind. Ecol. '
         '28, 1699 (lifetime extension up to +90%); Napiontek et al. 2025, RCR 215, 108117 (renovation)'),
        ('L4 typology mix', f"attached (townhouses + apartments) floor-area share {pct(L4['baseline_attached'])} -> "
         f"M {pct(L4['target']['M'])} (observed peak, {L4['peak_year']}), A {pct(L4['target']['A'])} (+16 points); "
         'increase split in proportion to the held townhouse / apartment shares; size and OLF blend with the shares',
         'DATA: consents 1991-2026 (M); LITERATURE: Pellan et al. 2024 (collective 59% -> 75%) (A)'),
        ('L5 best-practice materials', f"A1-A3 x [1 - w (1 - r)] on top of decarbonisation; r M: {rr('M')}; r A: {rr('A')}; "
         'M = mean of the lowest ceil(n/3) independent case studies (detached 4 of 10, townhouses 2 of 4), A = the '
         'lowest; apartments held (one independent case); A4-A5, B2/B4 events, C1-C4 and soil unchanged',
         'DATA: case studies (Christoforatos & Pickering 2025; outputs/factors/factors_building.csv, 2025 factors); '
         'DECISION (author): the ceil(n/3) rule'),
        ('Attribution', 'Shapley values over all 2^5 lever subsets (exact rational arithmetic) on cumulative carbon '
         'and cumulative LoE AR; fixed-order waterfall L1 -> L5 for the main figure', 'DECISION (author)'),
        ('Back-cast', 'uniform factor k on the floor area of every 2027-2050 cohort of P3-A (2026 fixed), brentq for '
         'cumulative LoE AR = 1; AtP: minimum LoE at k = 0', 'DECISION (author)'),
        ('Solution space', 'uniform cuts of 2027-2050 floor area and of non-soil carbon per m2 of the 2027-2050 '
         'cohorts, 0-100% in 5% steps, applied to P0', 'LITERATURE: Horup et al. 2025, Sci. Total Environ. 966, '
         '178780, Fig. 6 (form); DECISION (author)'),
    ] + [(f'Omitted in v1: {a}', 'not modelled', f'DECISION (author): {b}') for a, b in OMITTED]
