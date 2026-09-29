"""
ENGINE -- the forward model shared by Boss.py and MonteCarlo.py
===============================================================
Pure functions. Every input is an argument; nothing is read from module
globals or files; no argument is modified. Boss.py builds the inputs from the
data and its settings, MonteCarlo.py builds them from one draw of its
uncertain inputs, and both call these same functions. There is therefore one
engine, and a change here reaches both scripts at once.

  vacancy_knots     census vacancy (empty / private dwellings) at each census
  calibrate_stock   historical stock identity -> calibrated net replacement
  window_rate       net replacement (demolition + residual) over a year window
  deviation_2025    2025 departure from the calibrated identity, and its persistence
  mix_shares        damped additive-log-ratio typology mix
  blend             dwelling-weighted blend of a per-typology quantity
  forward           households -> dwellings built -> floor area -> carbon

Notation (all per year, 2025..2050 forward; index 0 is 2025):
  hh     households                      d_hh   new households (floored at 0 if asked)
  v      vacancy rate (empty/private)    stock  dwellings = hh / (1 - v)
  D      blended realised dwelling size  occ    occupied area per dwelling = S x OLF
"""
import numpy as np
import pandas as pd


# ============================================================
# HISTORY: STOCK CALIBRATION
# ============================================================
def vacancy_knots(census, pre_share):
    """Vacancy at each census: empty / (occupied + unoccupied private).
    Before 2013 only 'unoccupied' is published; its empty part is taken as
    pre_share x unoccupied."""
    empty = census['empty'].fillna(census['unoccupied'] * pre_share)
    return (empty / census['total_private']).to_dict()


def calibrate_stock(years, hh, knots, units_all, rv_units, completion, demol_rate,
                    window_start, window_end):
    """Historical stock identity, per calendar year:

        built (all kinds) = new households + vacancy allowance + vacancy change
                            + demolitions + residual

    built = completion x consents (all categories, incl. retirement villages).
    Vacancy is interpolated linearly between census years (flat outside).
    Demolition is a fixed rate of the previous year's stock; the residual is
    what is left. Its rate is calibrated as a ratio of sums over
    [window_start, window_end]."""
    years = np.asarray(years)
    v = pd.Series(np.interp(years.astype(float), list(knots), list(knots.values())), index=years)
    inv = 1.0 / (1.0 - v)
    d_h = hh.diff().fillna(0)
    stock = hh / (1.0 - v)
    allow = d_h * v / (1.0 - v)
    change = hh.shift(1) * inv.diff()
    rv_built = completion * rv_units
    beyond = completion * units_all - d_h           # built beyond household formation
    net = beyond - allow - change                   # = demolitions + residual
    prev = stock.shift(1)
    demolition = demol_rate * prev
    uncons = net - demolition
    w = (years >= window_start) & (years <= window_end)
    rate_unc = float(uncons[w].sum() / prev[w].sum())
    return dict(knots=knots, v=v, stock=stock, allow=allow, change=change, beyond=beyond,
                net=net, demol=demolition, uncons=uncons, rv=-rv_built, rate_unc=rate_unc,
                prev=prev, completion=completion, demol_rate=demol_rate)


def window_rate(cal, start, end):
    """Net replacement (demolition + residual) as a share of stock, ratio of
    sums over the calendar years start..end."""
    return float(cal['net'].loc[start:end].sum() / cal['prev'].loc[start:end].sum())


def deviation_2025(cal, built_all_2025, d_hh_2025, rate_net, years, window_start, window_end):
    """How far 2025's building beyond household formation departs from the
    calibrated identity, and the lag-1 autocorrelation (clipped to [0, 0.95])
    of the historical net series over the calibration window."""
    years = np.asarray(years)
    other_2025 = float(built_all_2025 - d_hh_2025)
    model_2025 = float(cal['allow'].loc[2025] + cal['change'].loc[2025]
                       + rate_net * cal['stock'].shift(1).loc[2025])
    net = cal['net'][(years >= window_start) & (years <= window_end)].values
    rho = float(np.clip(np.corrcoef(net[:-1], net[1:])[0, 1], 0.0, 0.95))
    return dict(dev=other_2025 - model_2025, rho=rho, other_2025=other_2025, model_2025=model_2025)


# ============================================================
# FORWARD
# ============================================================
def mix_shares(alr_2025, slopes, phi, years, typ_names, ref='Detached'):
    """Additive-log-ratio trend, geometrically damped from 2025:
        alr(t) = alr(2025) + slope x phi (1 - phi^(t-2025)) / (1 - phi).
    Shares stay positive and sum to one. Returns DataFrame (years x typology)."""
    years = np.asarray(years)
    other = [n for n in typ_names if n != ref]
    ahead = (years - 2025).clip(min=0)
    damp = phi * (1 - phi ** ahead) / (1 - phi)
    alr_f = {n: alr_2025[n] + slopes[n] * damp for n in other}
    denom = 1 + sum(np.exp(alr_f[n]) for n in other)
    out = {ref: 1 / denom}
    for n in other:
        out[n] = np.exp(alr_f[n]) / denom
    return pd.DataFrame(out, index=years)[list(typ_names)]


def blend(shares, per_unit, typ_names):
    """Harmonic mean weighted by floor-area share. This equals the mean
    weighted by the underlying units (dwellings or persons), so blended x units
    == sum over typologies exactly."""
    inv = pd.Series(0.0, index=shares.index)
    for name in typ_names:
        inv += shares[name] / per_unit[name]
    return 1.0 / inv


def forward(pop, hh, pop_growth, v, rate_demol, rate_unc, dev_2025, rho_dev, rv_share,
            shares, size, olf, intensity, intensity_upfront, floor_decline=True,
            olf_per_resident=False, consumption_override=None):
    """One forward path, 2025..2050 (index 0 = 2025, a model value; callers that
    anchor 2025 on observations overwrite it).

    pop, hh, pop_growth, v : arrays over the years (v may vary by year)
    rate_demol, rate_unc   : demolition and residual, shares of last year's stock
    dev_2025, rho_dev      : 2025 deviation, fading as rho^(t-2025), booked to the residual
    rv_share               : retirement-village share of ALL dwellings built (out of scope)
    shares                 : DataFrame years x typology (floor-area shares)
    size, olf, intensity, intensity_upfront : dicts by typology
    consumption_override   : for the legacy per-person/per-household bases only:
                             gross consumption computed elsewhere from
                             (extra space, floored new households, population).

    Floor area built (in scope) = structural + gross consumption, where
        structural  = d_hh x occupied area per dwelling
        consumption = extra space + (vacancy allowance + vacancy change
                      + demolition + residual + RV) x D.
    While D >= occupied area this equals in-scope dwellings built x D."""
    typ = list(shares.columns)
    pop = np.asarray(pop, float)
    hh = np.asarray(hh, float)
    v = np.broadcast_to(np.asarray(v, float), hh.shape)
    D = blend(shares, size, typ).values
    S = pop / hh
    olf_f = D / S if olf_per_resident else blend(shares, olf, typ).values
    occ = S * olf_f
    d_raw = np.insert(np.diff(hh), 0, 0)
    d_hh = np.maximum(d_raw, 0.0) if floor_decline else d_raw

    # demand split (bookkeeping): growth, house-splitting, consolidation
    g_gross = np.asarray(pop_growth, float) * olf_f
    structural = d_hh * occ
    hs_raw = structural - g_gross
    hs_pos = np.maximum(0, hs_raw)
    hs_avoided = np.abs(np.minimum(0, hs_raw))
    growth = g_gross - hs_avoided
    extra = np.clip(d_hh * (D - occ), 0, None)
    # > 0 only where the realised dwelling size falls below the occupied area:
    # there floor area exceeds dwellings built x D by this amount.
    extra_clip = extra - d_hh * (D - occ)

    # dwellings built beyond household formation (stock identity, forward)
    hh_prev = np.concatenate([[hh[0]], hh[:-1]])
    v_prev = np.concatenate([[v[0]], v[:-1]])
    prev = hh_prev / (1.0 - v_prev)                  # last year's stock
    stock = hh / (1.0 - v)
    allow = np.maximum(d_hh, 0.0) * v / (1.0 - v)
    change = hh_prev * (1.0 / (1.0 - v) - 1.0 / (1.0 - v_prev))
    demol = rate_demol * prev
    unc = rate_unc * prev
    dev = dev_2025 * rho_dev ** np.arange(len(hh))
    dev[0] = 0.0
    units = allow + change + demol + unc
    units, unc = units + dev, unc + dev
    rv = -rv_share * (np.maximum(d_hh, 0.0) + units)
    units_in_scope = units + rv

    if consumption_override is None:
        c_gross = extra + units_in_scope * D
    else:
        c_gross = np.asarray(consumption_override(extra, d_hh), float)
    total = growth + hs_pos + c_gross

    gfa_t = shares.values.T * total                  # (typology, years)
    I = np.array([intensity[t] for t in typ])
    U = np.array([intensity_upfront[t] for t in typ])
    return dict(
        years=shares.index.values, typ=typ, pop=pop, hh=hh, S=S, d_hh=d_hh, d_hh_raw=d_raw,
        D=D, olf=olf_f, occ=occ, structural=structural, growth_gross=g_gross, growth=growth,
        hs_pos=hs_pos, hs_avoided=hs_avoided, extra=extra, extra_clip=extra_clip,
        c_gross=c_gross, total=total,
        v=np.array(v), stock=stock, prev=prev, allow=allow, change=change, demol=demol,
        unc=unc, dev=dev, rv=rv, dwell_in_scope=total / D, rv_units=-rv,
        gfa_t=gfa_t, carbon_t=I[:, None] * gfa_t, carbon=(I[:, None] * gfa_t).sum(axis=0),
        upfront=(U[:, None] * gfa_t).sum(axis=0))
