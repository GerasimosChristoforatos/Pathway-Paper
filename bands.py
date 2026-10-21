"""
DEMAND BANDS (MODEL v3.2.0; release accounting from v3.1.0, A2): one band accounting for the projection (Reference and its variants) and every lever,
pathway and theoretical-limit run (pathways.py), so that the figures and tables of both read the same numbers.

Release-accounting convention (A2):
  * positive bands are always GROSS need: population growth, smaller households, extra space, vacancy (the gross
    allowance: allowance on new households + any vacancy-rate rise), the 2026 overbuild, demolition replacement and
    the recent replacement surge;
  * every release is its own negative band, booked in the year it is used: 'Overbuild absorbed' (payback),
    'Unconsented additions' (the calibrated residual of the census identity), 'Vacancy released' (a vacancy-rate fall
    in a run without any lever at its theoretical limit, applied in the year it occurs, capped at the year's gross
    need, the rest carried) and 'Released dwellings (TL)' (the re-occupation pool of a theoretical-limit-family run);
    no release is netted inside a positive band and no band is rescaled to fit a floor or a cap;
  * an amount still unusable in 2050 is booked in 2050 in its release band and, with the opposite sign, as
    'Surplus kept vacant (2050)', so the bands add up to the total in every year;
  * carbon-only band: 'Maintenance (B2, B4)' of the new cohorts within the window.
  * MODEL v4.0.0 (TL surplus pooling, pathways.TL_SURPLUS_POOLING): in a theoretical-limit-family run the re-occupied
    Reference overbuild is booked in 'Overbuild absorbed' (paid), its part of the pool still unused in 2050 in
    'Overbuild absorbed' and, with the opposite sign, in 'Surplus kept vacant (2050)' (flows['ob_remainder']).

In-scope bands: retirement-village (RV) units are a constant share of every dwelling built (engine.forward), so each
band's in-scope floor area is its gross floor area x (1 - RV share), exactly; the observed-GFA adjustment of 2026
(gfa_adj) is in-scope floor area of the 2026 overbuild band. Soil: a band bears soil unless it is soil-free
replacement (demolition, the surge and the residual, and the redevelopment part of the join, in a year whose net
replacement is positive; engine.forward), scaled by the brownfield factor phi = soil share / soil share of the
replacement rule (L6); soil carbon loss is attributed to the construction year (MODEL v3.0 accounting). The bands then reproduce the engine's floor area and carbon in every year (checked to 1e-9).
"""
import numpy as np

# band ids (naming.BANDS) in stacking order of the in-scope definition
IN_SCOPE = ('growth', 'smaller_households', 'extra_space', 'vacancy', 'overbuild_2026', 'replacement',
            'redevelopment', 'overbuild_absorbed', 'unconsented', 'vacancy_released', 'released_tl',
            'surplus_vacant', 'maintenance')
FLOOR_AREA_BANDS = IN_SCOPE[:-1]                     # maintenance carries carbon only
IDENTITY_RTOL = 1e-9
# MODEL v4.2: six display bands (aggregation for figures only; the detailed bands are unchanged in data and pathways):
# detailed band id (projection and history) -> display id. 'released_tl' (Re-used dwellings (TL)) and the carbon-only
# 'maintenance' stay separate.
DISPLAY = {'growth': 'growth', 'smaller_households': 'smaller_households', 'extra_space': 'extra_space',
           'vacancy': 'vacancy', 'vacancy_released': 'vacancy',
           'replacement': 'net_replacement', 'redevelopment': 'net_replacement', 'unconsented': 'net_replacement',
           'replacement_census': 'net_replacement',
           'unexplained': 'market_balance', 'retirement_villages': 'market_balance', 'overbuild_2026': 'market_balance',
           'overbuild_absorbed': 'market_balance', 'surplus_vacant': 'market_balance',
           'released_tl': 'released_tl', 'maintenance': 'maintenance'}
DISPLAY_ORDER = ('growth', 'smaller_households', 'extra_space', 'vacancy', 'net_replacement', 'market_balance',
                 'released_tl', 'maintenance')
DISPLAY_LABEL = {'growth': 'Population growth', 'smaller_households': 'Household-size change',
                 'extra_space': 'Extra space', 'vacancy': 'Vacancy', 'net_replacement': 'Net replacement',
                 'market_balance': 'Market balance (excess, residual and scope adjustments)',
                 'released_tl': 'Re-used dwellings (TL)', 'maintenance': 'Maintenance (B2, B4)'}


def display_map():
    """The detailed -> display band map as rows (outputs/data/bands_display_map.csv)."""
    return [dict(band_id=b, display_id=d, display_label=DISPLAY_LABEL[d]) for b, d in DISPLAY.items()]
_TOL_M2 = 1e-6


def no_flows(n):
    """The release flows of a run without any release (the Reference): every array zero."""
    z = np.zeros(n)
    return dict(rel_v=z, used_v=z, reocc=z, negclip=z, neg_used=z, vac_carry_end=0.0, pool_remainder=0.0,
                ob_remainder=0.0, neg_carry_end=0.0)


def arrays(E, fi, excess, paid, flows, long_run_residual):
    """Gross band floor area (m2, with retirement villages, before the RV share is removed; index over the model
    years) and the soil-bearing indicator of each band. excess, paid: the 2026 overbuild and its payback (dwellings,
    paid >= 0); flows: the release flows of the run (no_flows(), or pathways.run's info['flows'])."""
    D = np.asarray(E['D'], float)
    n = len(D)
    wave = (np.asarray(fi['rate_unc'], float) - long_run_residual) * np.asarray(E['prev'], float) * D
    rem = np.zeros(n)
    rem[-1] = 1.0                                       # the 2050 booking of what is still unusable
    g = dict(growth=np.asarray(E['growth'], float), smaller_households=np.asarray(E['hs_pos'], float),
             extra_space=np.asarray(E['extra'], float),
             vacancy=(E['allow'] + E['change'] + flows['rel_v']) * D,
             overbuild_2026=np.asarray(excess, float) * D,
             replacement=E['demol'] * D, redevelopment=wave,
             overbuild_absorbed=-(np.asarray(paid, float) + rem * flows.get('ob_remainder', 0.0)) * D,
             unconsented=(E['unc'] + flows['negclip'] - flows['neg_used'] - rem * flows['neg_carry_end']) * D - wave,
             vacancy_released=-(flows['used_v'] + rem * flows['vac_carry_end']) * D,
             released_tl=-(flows['reocc'] + rem * flows['pool_remainder']) * D,
             surplus_vacant=rem * (flows['vac_carry_end'] + flows['pool_remainder'] + flows.get('ob_remainder', 0.0)
                                   + flows['neg_carry_end']) * D)
    if np.any(g['vacancy'][1:] < -1e-6):               # gross allowance: never negative (A2)
        raise SystemExit('bands: negative gross vacancy allowance.')
    net = np.asarray(E['demol'], float) + np.asarray(E['unc'], float) + np.asarray(E['join_redev'], float)
    # replacement soil-free where net replacement is positive (engine.forward); none when soil is on all floor area
    free = np.zeros(n) if fi.get('soil_on_replacement') else (net >= 0.0).astype(float)
    one = np.ones(n)
    bear = {k: one for k in g}
    for k in ('replacement', 'redevelopment', 'unconsented'):
        bear[k] = 1.0 - free
    jr = np.asarray(E['join_redev'], float) * D
    bear['overbuild_2026'] = np.divide(g['overbuild_2026'] - free * jr, g['overbuild_2026'],
                                       out=one.copy(), where=g['overbuild_2026'] != 0)
    return g, bear


def _factors(E, fi, gi, bear, typ):
    """(materials kg per m2 of the year's mix, soil kg per m2, phi): phi scales the soil of every soil-bearing band so
    that the bands carry exactly the engine's soil (brownfield share L6, clipped soil share of TL zero years)."""
    total = np.asarray(E['total'], float)
    shares, soil = fi['shares'], fi['soil']
    sY = {t: np.broadcast_to(np.asarray(soil[t], float), total.shape) for t in typ}
    mat = {t: np.broadcast_to(np.asarray(fi['intensity'][t], float), total.shape) - sY[t] for t in typ}
    bearing = sum(gi[k] * bear[k] for k in gi)
    soil_share = np.asarray(E['soil_share'], float)
    phi = np.divide(soil_share * total, bearing, out=np.zeros_like(total), where=np.abs(bearing) > _TOL_M2)
    if np.any((np.abs(bearing) <= _TOL_M2) & (np.abs(soil_share * total) > _TOL_M2)):
        raise SystemExit('bands: soil on floor area that no band bears.')
    return (sum(shares[t].values * mat[t] for t in typ), sum(shares[t].values * sY[t] for t in typ), phi)


def _carbon(area, bear, mat_m2, soil_m2, phi):
    return area * mat_m2 + area * bear * phi * soil_m2


def with_retirement_villages(E, fi, excess, paid, flows, long_run_residual, typ):
    """Bands with the retirement-village units as their own negative band: every other band at its gross floor area
    (before the RV share), the RV band = - RV share x their sum; the totals equal in_scope()."""
    g, bear = arrays(E, fi, excess, paid, flows, long_run_residual)
    rv_share = float(fi['rv_share'])
    gi = {k: v * (1.0 - rv_share) for k, v in g.items()}
    adj = np.asarray(E['gfa_adj'], float)
    gi['overbuild_2026'] = gi['overbuild_2026'] + adj
    mat_m2, soil_m2, phi = _factors(E, fi, gi, bear, typ)
    out = {}
    for k in FLOOR_AREA_BANDS:
        area = g[k] + (adj if k == 'overbuild_2026' else 0.0)
        out[k] = (area, _carbon(area, bear[k], mat_m2, soil_m2, phi))
    rv_g = -rv_share * sum(g[k] for k in FLOOR_AREA_BANDS)
    rv_c = -rv_share * sum(_carbon(g[k], bear[k], mat_m2, soil_m2, phi) for k in FLOOR_AREA_BANDS)
    out['retirement_villages'] = (rv_g, rv_c)
    out['maintenance'] = (np.zeros_like(rv_g), np.asarray(E['b_t'], float).sum(axis=0))
    check(out, E)
    return out


def in_scope(E, fi, excess, paid, flows, long_run_residual, typ):
    """In-scope bands: {band id: (floor area m2, carbon kg)} over the model years (index 0 = 2025 is not a band year;
    callers use [1:]). Raises unless the bands reproduce E['total'] and E['carbon'] in every year 2026-2050."""
    g, bear = arrays(E, fi, excess, paid, flows, long_run_residual)
    total = np.asarray(E['total'], float)
    rv_share = float(fi['rv_share'])
    gi = {k: v * (1.0 - rv_share) for k, v in g.items()}
    gi['overbuild_2026'] = gi['overbuild_2026'] + np.asarray(E['gfa_adj'], float)
    mat_m2, soil_m2, phi = _factors(E, fi, gi, bear, typ)
    out = {k: (gi[k], _carbon(gi[k], bear[k], mat_m2, soil_m2, phi)) for k in FLOOR_AREA_BANDS}
    out['maintenance'] = (np.zeros_like(total), np.asarray(E['b_t'], float).sum(axis=0))
    check(out, E)
    return out


def check(out, E, rtol=IDENTITY_RTOL):
    """The bands add up to the engine's floor area and carbon in every year 2026-2050."""
    f = slice(1, None)
    sg = sum(v[0] for v in out.values())[f]
    sc = sum(v[1] for v in out.values())[f]
    tg, tc = np.asarray(E['total'], float)[f], np.asarray(E['carbon'], float)[f]
    if not np.allclose(sg, tg, rtol=rtol, atol=_TOL_M2 * 10):
        raise SystemExit(f'bands: floor area bands differ from the total by {np.max(np.abs(sg - tg)):.3g} m2.')
    if not np.allclose(sc, tc, rtol=rtol, atol=1.0):
        raise SystemExit(f'bands: carbon bands differ from the total by {np.max(np.abs(sc - tc)):.3g} kg.')
