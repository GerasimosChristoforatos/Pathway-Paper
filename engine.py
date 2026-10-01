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
  replacement_path  net replacement by year under scenario S1 / S2 / S3
  seasonal_shares   mean share of the calendar-year total, by month
  nowcast_year      calendar-year consents from the observed months (A1)
  requirement       dwellings built (all categories) in a forward() result
  market_excess     near-term market excess from observed 2026 building
  mix_shares        damped additive-log-ratio typology mix
  blend             dwelling-weighted blend of a per-typology quantity
  forward           households -> dwellings built -> floor area -> carbon

Notation (all per year, 2025..2050 forward; index 0 is 2025):
  hh     households                      d_hh   new households (floored at 0)
  v      vacancy rate (empty/private)    stock  dwellings = hh / (1 - v)
  D      blended realised dwelling size  occ    occupied area per dwelling = S x OLF
"""
import numpy as np
import pandas as pd


# ============================================================
# HISTORY: STOCK CALIBRATION
# ============================================================
def vacancy_knots(census, pre_share, const_share=None):
    """Vacancy at each census: empty / (occupied + unoccupied private).
    Before 2013 only 'unoccupied' is published; its empty part is taken as
    pre_share x unoccupied. With const_share, EVERY census uses
    const_share x unoccupied (one empty/away split throughout, which removes
    the 2013 -> 2018 classification break, N1)."""
    if const_share is not None:
        empty = census['unoccupied'] * const_share
    else:
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


CENSUS_DAY_OF_YEAR = 64          # census nights fell on 4-7 March, 1986-2023; 5 March used


def census_interval_rates(stock, consents, completion, lag_w, day_of_year=CENSUS_DAY_OF_YEAR, uc=None):
    """Net replacement from census DWELLING counts, per intercensal interval
    (no household data, no empty/away split):

        rate = [dwellings completed - change in census private dwellings] / stock-years

    stock    : census private dwellings (occupied + unoccupied), by census year
    consents : monthly consents, all categories (index = first of month)
    Dwellings completed in (census_0, census_1] = completion x consents whose
    mid-month falls in (census_0 - W, census_1 - W]: the same two-point lag as
    the model's completions series, in continuous time. Intervals without full
    consent coverage are skipped.
    uc : census dwellings under construction (private), by census year. When
    given, dwellings completed = completion x consents - change in UC: the census
    stock excludes dwellings under construction, so consents still in progress
    at census night are not yet built. Use only with lag_w = 0 (a lag already
    removes the pipeline). Intervals with a missing UC count are not corrected
    (uc_corrected = False)."""
    years = sorted(int(y) for y in stock.index)
    t = {y: y + day_of_year / 365.25 for y in years}
    idx = consents.index
    tm = idx.year + (idx.dayofyear - 1 + idx.days_in_month / 2.0) / 365.25
    rows = []
    for y0, y1 in zip(years[:-1], years[1:]):
        lo, hi = t[y0] - lag_w, t[y1] - lag_w
        if tm.min() > lo:
            continue
        m = (tm > lo) & (tm <= hi)
        built = completion * float(consents[m].sum())
        d_uc = (float(uc[y1] - uc[y0]) if uc is not None and y0 in uc.index and y1 in uc.index
                and np.isfinite(uc[y0]) and np.isfinite(uc[y1]) else np.nan)
        if np.isfinite(d_uc):
            built -= d_uc
        d_stock = float(stock[y1] - stock[y0])
        stock_years = float((stock[y0] + stock[y1]) / 2.0 * (t[y1] - t[y0]))
        rows.append(dict(y0=y0, y1=y1, built=built, d_stock=d_stock, stock_years=stock_years,
                         d_uc=d_uc, uc_corrected=bool(np.isfinite(d_uc)),
                         rate=(built - d_stock) / stock_years))
    return pd.DataFrame(rows)


def census_window_rate(rates, start, end):
    """Ratio of sums over the intervals from census year start to census year
    end. The stock changes telescope, so only the endpoint counts enter the
    numerator."""
    w = rates[(rates['y0'] >= start) & (rates['y1'] <= end)]
    if w.empty:
        raise ValueError(f'No census intervals within {start}-{end}.')
    return float((w['built'] - w['d_stock']).sum() / w['stock_years'].sum())


def replacement_path(scenario, rate_long, rate_recent, years, half_life=10.0):
    """Net replacement rate by year (index 0 = 2025).
      'S1': the long-run rate throughout;
      'S2': the recent (2018-2023) rate throughout;
      'S3': the recent rate fading to the long-run rate with the given
            half-life: long + (recent - long) x 0.5^((t - 2025) / half_life)."""
    years = np.asarray(years)
    if scenario == 'S1':
        return np.full(len(years), float(rate_long))
    if scenario == 'S2':
        return np.full(len(years), float(rate_recent))
    if scenario == 'S3':
        return rate_long + (rate_recent - rate_long) * 0.5 ** ((years - 2025) / float(half_life))
    raise ValueError(f"Unknown replacement scenario '{scenario}'.")


def seasonal_shares(consents, years):
    """Mean share of the calendar-year total falling in each month, over the
    complete calendar years years[0]..years[1] (fixed multiplicative seasonal
    factors, normalised to the year)."""
    m = consents.loc[f'{years[0]}-01-01':f'{years[1]}-12-31']
    by = m.groupby([m.index.year, m.index.month]).sum().unstack()
    return (by.div(by.sum(axis=1), axis=0)).mean()


def nowcast_year(consents, year, method, seasonal_years):
    """Calendar-year consents for a year observed only in part. consents:
    monthly series (index = first of month). The observed months are taken
    from the data; the unobserved months are estimated by:
      'seasonal_share'   ratio-to-annual estimator with fixed seasonal factors:
                         observed / (sum of the observed months' mean shares)
                         x (sum of the missing months' mean shares);
      'same_period_ratio' the same months of the previous year x the ratio of
                         the observed months to the same months a year earlier;
      'last_12_months'   the latest 12 observed months stand in for the year."""
    s = consents.sort_index()
    obs = s.loc[f'{year}-01-01':f'{year}-12-31']
    months = sorted(int(m) for m in obs.index.month)
    if months != list(range(1, len(months) + 1)):
        raise ValueError(f'{year}: observed months {months} are not a run from January.')
    missing = [m for m in range(1, 13) if m not in months]
    ytd = float(obs.sum())
    if not missing:
        est = 0.0
    elif method == 'seasonal_share':
        sh = seasonal_shares(s, seasonal_years)
        est = ytd / float(sh.loc[months].sum()) * float(sh.loc[missing].sum())
    elif method == 'same_period_ratio':
        prev = s.loc[f'{year - 1}-01-01':f'{year - 1}-12-31']
        same = float(prev[prev.index.month.isin(months)].sum())
        est = float(prev[prev.index.month.isin(missing)].sum()) * ytd / same
    elif method == 'last_12_months':
        last = s.index.max()
        est = float(s.loc[last - pd.DateOffset(months=11):last].sum()) - ytd
    else:
        raise ValueError(f"Unknown nowcast method '{method}'.")
    return dict(year=year, method=method, months_observed=months, observed=ytd,
                estimated_missing=est, total=ytd + est)


def requirement(E):
    """Dwellings built, all categories (incl. retirement villages), in a
    forward() result: new households (floored as in forward) + vacancy
    allowance + vacancy change + demolition + residual (+ join, if any)."""
    return np.maximum(E['d_hh'], 0.0) + E['allow'] + E['change'] + E['demol'] + E['unc'] + E['join']


def market_excess(E, building_2026, rho, gap_ref='2027', mode='redevelopment', absorption=0.0):
    """Near-term market excess (v1.1 rule). E: forward() result WITHOUT a join
    (index 0 = 2025, 1 = 2026). building_2026: observed dwellings built in 2026
    (all categories).
      excess_2026 = building_2026 - requirement_2026
      gap_ref     = building_2026 - requirement_2027  (gap_ref='2027'; '2026' = sensitivity)
      excess_t    = gap_ref x rho^(t - 2026), t >= 2027
    mode 'redevelopment' (default): the excess is stock-neutral extra replacement
      of existing stock (returned as redev = join; no soil, no absorption, no payback);
    mode 'surplus': the excess adds to the stock; each later year a share
      `absorption` of the remaining surplus is absorbed by building less
      (payback); absorption = 0 leaves the surplus permanent.
    Returns (join, info)."""
    R = requirement(E)
    n = len(R)
    k = np.arange(n)
    gap = float(building_2026 - (R[2] if gap_ref == '2027' else R[1]))
    excess = np.zeros(n)
    excess[1] = building_2026 - R[1]
    excess[2:] = gap * rho ** (k[2:] - 1)
    info = dict(O26=float(building_2026), R26=float(R[1]), R27=float(R[2]), e26=float(excess[1]),
                e27=gap, gap_ref=gap, rho=float(rho), mode=mode, excess=excess)
    if mode == 'redevelopment':
        return excess.copy(), dict(info, redev=excess.copy(), surplus=np.zeros(n), payback=np.zeros(n))
    if mode != 'surplus':
        raise ValueError(f"Unknown near-term mode '{mode}'.")
    join, pay, U, left = excess.copy(), np.zeros(n), np.zeros(n), 0.0
    for i in range(1, n):
        pay[i] = absorption * left if i >= 2 else 0.0
        join[i] = excess[i] - pay[i]
        left = left - pay[i] + excess[i]
        U[i] = left
    return join, dict(info, redev=np.zeros(n), surplus=U, payback=-pay)


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
            shares, size, olf, intensity, intensity_upfront, join=None, join_redev=None,
            soil=None, soil_on_replacement=True, gfa_fixed=None):
    """One forward path, 2025..2050 (index 0 = 2025, a model value; callers that
    anchor 2025 on observations overwrite it).

    pop, hh, pop_growth, v : arrays over the years (v may vary by year)
    rate_demol, rate_unc   : demolition and residual, shares of last year's stock
                             (rate_unc may be an array by year: scenario S3)
    join                   : optional array of dwellings built above the requirement
                             (near-term market excess), added before the RV split
    join_redev             : the part of join that replaces extra removals
                             (redevelopment); the rest adds to the stock
                             (stock_join). The extra stock does not enter the
                             demolition / residual base (a second-order effect).
    dev_2025, rho_dev      : 2025 deviation, fading as rho^(t-2025), booked to the residual
    rv_share               : retirement-village share of ALL dwellings built (out of scope)
    shares                 : DataFrame years x typology (floor-area shares)
    size, olf, intensity, intensity_upfront : dicts by typology
    soil                   : dict by typology, the soil part of intensity and
                             intensity_upfront (kg/m2). None = soil on all floor
                             area. Otherwise soil applies to the share
                             soil_share of each year's floor area (item 8):
        soil_share = 1 - soil-free floor area / total, where the soil-free
        floor area is the in-scope net replacement (demolition + residual +
        redevelopment channel, x (1 - rv_share) x D; land already settled) when
        soil_on_replacement is False.
    gfa_fixed              : optional {index: floor area} fixing the in-scope floor area of
                             a year to an observation (the 2026 nowcast from consented
                             GFA); the difference is booked to consumption and reported
                             as gfa_adj. Dwelling counts (the stock) are not changed.

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
    olf_f = blend(shares, olf, typ).values
    occ = S * olf_f
    d_raw = np.insert(np.diff(hh), 0, 0)
    d_hh = np.maximum(d_raw, 0.0)                   # household decline -> vacancy, not negative building

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
    join = np.zeros(len(hh)) if join is None else np.asarray(join, float)
    join_redev = np.zeros(len(hh)) if join_redev is None else np.asarray(join_redev, float)
    units = units + join
    stock_join = np.cumsum(join - join_redev)        # dwellings added to the stock by the join
    rv = -rv_share * (np.maximum(d_hh, 0.0) + units)
    units_in_scope = units + rv

    c_gross = extra + units_in_scope * D
    total = growth + hs_pos + c_gross
    gfa_adj = np.zeros(len(hh))
    for i, g in (gfa_fixed or {}).items():
        gfa_adj[i] = float(g) - total[i]
    c_gross, total = c_gross + gfa_adj, total + gfa_adj

    gfa_t = shares.values.T * total                  # (typology, years)
    I = np.array([intensity[t] for t in typ])
    U = np.array([intensity_upfront[t] for t in typ])
    if soil is None:
        soil_share, soil_free = np.ones(len(hh)), np.zeros(len(hh))
        carbon_t, upfront_t = I[:, None] * gfa_t, U[:, None] * gfa_t
    else:
        s = np.array([soil[t] for t in typ])
        soil_free = (np.zeros(len(hh)) if soil_on_replacement else
                     np.clip(demol + unc + join_redev, 0.0, None) * (1.0 - rv_share) * D)
        soil_share = (1.0 - np.divide(soil_free, total, out=np.zeros(len(hh)),
                                                         where=total != 0))
        carbon_t = (I - s)[:, None] * gfa_t + (s[:, None] * gfa_t) * soil_share
        upfront_t = (U - s)[:, None] * gfa_t + (s[:, None] * gfa_t) * soil_share
    return dict(
        years=shares.index.values, typ=typ, pop=pop, hh=hh, S=S, d_hh=d_hh, d_hh_raw=d_raw,
        D=D, olf=olf_f, occ=occ, structural=structural, growth_gross=g_gross, growth=growth,
        hs_pos=hs_pos, hs_avoided=hs_avoided, extra=extra, extra_clip=extra_clip,
        c_gross=c_gross, total=total,
        v=np.array(v), stock=stock, prev=prev, allow=allow, change=change, demol=demol,
        unc=unc, dev=dev, join=join, join_redev=join_redev, stock_join=stock_join, rv=rv, dwell_in_scope=total / D, rv_units=-rv,
        gfa_t=gfa_t, carbon_t=carbon_t, carbon=carbon_t.sum(axis=0), upfront=upfront_t.sum(axis=0),
        soil_share=soil_share, soil_free_gfa=soil_free, gfa_adj=gfa_adj)
