"""
ENGINE -- the forward model shared by projection.py and MonteCarlo.py
===============================================================
Pure functions. Every input is an argument; nothing is read from module
globals or files; no argument is modified. projection.py builds the inputs from the
data and its settings, MonteCarlo.py builds them from one draw of its
uncertain inputs, and both call these same functions. There is therefore one
engine, and a change here reaches both scripts at once.

  vacancy_knots     census vacancy (empty / private dwellings) at each census
  calibrate_stock   historical stock identity -> calibrated net replacement
  window_rate       net replacement (demolition + residual) over a year window
  deviation_2025    2025 departure from the calibrated identity, and its persistence
  replacement_path  net replacement by year: LOW / HIGH / REF (the projection variants)
  seasonal_shares   mean share of the calendar-year total, by month
  nowcast_year      calendar-year consents from the observed months (A1)
  requirement       dwellings built (all categories) in a forward() result
  market_excess     the 2026 overbuild from observed 2026 building
  logistic_weights  normalised logistic weights of a window (adoption; overbuild absorption)
  absorb_overbuild  logistic absorption of the 2026 overbuild, capped at the year's building
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


def replacement_trend(rates, start, end):
    """MODEL v3.3.0 (Very High replacement): the weighted least-squares linear trend of the census-interval net
    replacement rates with start <= y0 and y1 <= end: rate_i = (built_i - d_stock_i) / stock_years_i, placed at the mean
    of the interval's model years y0+1 .. y1 (the interval convention of the history bands), weighted by the interval
    length y1 - y0. Returns dict(a, b, n, x, rate, weight): rate(t) = a + b t."""
    w = rates[(rates['y0'] >= start) & (rates['y1'] <= end)]
    if len(w) < 2:
        raise ValueError(f'replacement_trend: fewer than two census intervals within {start}-{end}.')
    y = ((w['built'] - w['d_stock']) / w['stock_years']).to_numpy(float)
    x = ((w['y0'] + 1 + w['y1']) / 2.0).to_numpy(float)
    wt = (w['y1'] - w['y0']).to_numpy(float)
    X = np.column_stack([np.ones(len(x)), x])
    a, b = np.linalg.solve(X.T @ (wt[:, None] * X), X.T @ (wt * y))
    return dict(a=float(a), b=float(b), n=int(len(w)), x=x.tolist(), rate=y.tolist(), weight=wt.tolist())


def replacement_path(scenario, rate_long, rate_recent, years, half_life=10.0, trend=None):
    """Net replacement rate by year (index 0 = 2025), by projection variant:
      'LOW':   the long-run rate throughout (Low replacement);
      'HIGH':  the recent (2018-2023) rate throughout (High replacement);
      'VHIGH': the weighted linear trend of the census-interval rates continues (Very High replacement, MODEL v3.3.0;
               trend = replacement_trend(...)): a + b t;
      'REF':   the recent rate fading to the long-run rate with the given
               half-life: long + (recent - long) x 0.5^((t - 2025) / half_life)
               (the Reference; the half-life is sampled U(5, 15) yr in the Monte Carlo)."""
    years = np.asarray(years)
    if scenario == 'LOW':
        return np.full(len(years), float(rate_long))
    if scenario == 'HIGH':
        return np.full(len(years), float(rate_recent))
    if scenario == 'VHIGH':
        if trend is None:
            raise ValueError("replacement_path: 'VHIGH' needs the census trend (replacement_trend).")
        return trend['a'] + trend['b'] * years.astype(float)
    if scenario == 'REF':
        return rate_long + (rate_recent - rate_long) * 0.5 ** ((years - 2025) / float(half_life))
    raise ValueError(f"Unknown replacement variant '{scenario}'.")


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


SOIL_ZERO_TOL_M2 = 1e-3          # floor area treated as zero (theoretical limit, banked zero-building years)
# MODEL v3.2.0 zero-year guard (every run): built floor area below this is floating-point noise of a year in which
# nothing is built (e.g. +-2.3e-10 m2); that year's floor area, soil share and soil carbon are set to 0. Without it
# the soil share 1 - soil_free / total is a ratio of noise (order +-1e15) and the soil carbon of a year with no
# construction is non-zero (MODEL v3.0 defect, found in Monte Carlo draws; docs/CHANGELOG_v3_2.md).
BUILT_ZERO_TOL_M2 = 1e-6


def requirement(E):
    """Dwellings built, all categories (incl. retirement villages), in a
    forward() result: new households (floored as in forward) + vacancy
    allowance + vacancy change + demolition + residual (+ join, if any)."""
    return np.maximum(E['d_hh'], 0.0) + E['allow'] + E['change'] + E['demol'] + E['unc'] + E['join']


def logistic_weights(years, start, end):
    """Normalised logistic of a window start -> end (W = end - start): midpoint start + W/2, speed
    k = ln(81) / (2W/3) (10% -> 90% within the middle two-thirds of the window), rescaled so that
    w(start) = 0 and w(end) = 1; 0 up to start, 1 from end. The adoption rule of the levers
    (levers.adoption_window) and of the overbuild absorption of the Reference (MODEL v3.0.0)."""
    y = np.asarray(years, float)
    W = float(end - start)
    mid, k = start + W / 2.0, np.log(81.0) / (2.0 * W / 3.0)
    s = lambda t: 1.0 / (1.0 + np.exp(-k * (np.asarray(t, float) - mid)))
    w = (s(y) - s(start)) / (s(end) - s(start))
    return np.where(y <= start, 0.0, np.where(y >= end, 1.0, w))


def absorb_overbuild(excess, w, need):
    """Logistic absorption of the 2026 overbuild (MODEL v3.0.0). excess: the market excess by year (index 0 =
    2025: 0); w: absorption weights (logistic_weights, 0 in 2026, 1 from the absorption year); need: the run's
    dwellings built WITHOUT any join (requirement of a forward() run with join = 0), all categories.

        C_t = sum of excess up to t          (cumulative overbuild)
        U*_t = C_t (1 - w_t)                 (surplus still vacant on the target path)
        payback*_t = (C_t - U*_t) - (C_(t-1) - U*_(t-1)) = C_t w_t - C_(t-1) w_(t-1)
        gross_t = need_t + excess_t          (dwellings built before the payback)
        paid_t = min(payback*_t + carry_(t-1), max(gross_t, 0))   where payback*_t + carry_(t-1) > 0
        carry_t = payback*_t + carry_(t-1) - paid_t
        join_t = excess_t - paid_t           (built_t = gross_t - paid_t >= 0)
        U_t = C_t - sum of paid up to t      (surplus vacant: the stock-adding join, engine stock_join)

    A negative payback (C falling: the excess below zero, an under-build made good) is paid in full. Returns
    (join, info) with the arrays of the absorption log and the years where the cap binds."""
    excess = np.asarray(excess, float)
    w = np.asarray(w, float)
    need = np.asarray(need, float)
    n = len(excess)
    C = np.cumsum(excess)
    U_target = C * (1.0 - w)
    pay_target = np.diff(np.r_[0.0, C * w])
    gross = need + excess
    paid, carry = np.zeros(n), np.zeros(n)
    binds = np.zeros(n, bool)
    c = 0.0
    for i in range(n):
        want = pay_target[i] + c
        if want > 0.0:
            cap = max(gross[i], 0.0)
            paid[i] = min(want, cap)
            binds[i] = want > cap
        else:
            paid[i] = want
        c = want - paid[i]
        carry[i] = c
    join = excess - paid
    U = C - np.cumsum(paid)
    return join, dict(excess=excess, w=w, C=C, U_target=U_target, payback_target=pay_target, need=need,
                      gross=gross, paid=paid, carry=carry, cap_binds=binds, U=U, built=gross - paid)


def market_excess(E, building_2026, rho, gap_ref='2027', mode='redevelopment', absorption=0.0, absorb_w=None,
                  excess=None):
    """Near-term market excess (v1.1 rule; MODEL v4.0.0: n observed years). E: forward() result WITHOUT a join
    (index 0 = 2025, 1 = 2026). building_2026: observed dwellings built (all categories) in the first projection
    year, or a sequence over the n observed (pipeline) years 2026 .. 2025 + n (MODEL v4.0.0: completions from consents
    already issued, projection.COMPLETION_LAG_MONTHS):
      excess_t    = building_t - requirement_t,          t = 2026 .. 2025 + n (observed)
      gap_ref     = building_last - requirement_(last+1) (gap_ref='2027': the requirement of the year after the last
                    observed year; '2026' = sensitivity: of the last observed year)
      excess_t    = gap_ref x rho^(t - last),             t > last
    n = 1 is the v1.1-v3.3 rule exactly (gap_ref = building_2026 - requirement_2027, rho^(t - 2026)).
    mode 'redevelopment': the excess is stock-neutral extra replacement
      of existing stock (returned as redev = join; no soil, no absorption, no payback);
    mode 'surplus': the excess adds to the stock;
      absorb_w None (MODEL v2.1 and the legacy Reference): each later year a share
        `absorption` of the remaining surplus is absorbed by building less (payback);
        absorption = 0 leaves the surplus permanent;
      absorb_w given (MODEL v3.0.0 Reference): logistic absorption (absorb_overbuild),
        the surplus absorbed along the weights absorb_w, capped at the run's own building.
    excess: optional fixed excess series (MODEL v3.0.0: the Reference's, held in every run of
      the levers); None computes it from E.
    Returns (join, info)."""
    R = requirement(E)
    n = len(R)
    k = np.arange(n)
    b_obs = np.atleast_1d(np.asarray(building_2026, float))
    m = len(b_obs)
    gap = float(b_obs[-1] - (R[m + 1] if gap_ref == '2027' else R[m]))
    if excess is None:
        excess = np.zeros(n)
        excess[1:m + 1] = b_obs - R[1:m + 1]
        excess[m + 1:] = gap * rho ** (k[m + 1:] - m)
    else:
        excess = np.asarray(excess, float).copy()
    info = dict(O26=float(b_obs[0]), R26=float(R[1]), R27=float(R[2]), e26=float(excess[1]),
                e27=gap, gap_ref=gap, rho=float(rho), mode=mode, excess=excess,
                n_observed=m, O_obs=[float(x) for x in b_obs], R_obs=[float(x) for x in R[1:m + 1]],
                e_obs=[float(x) for x in excess[1:m + 1]], R_next=float(R[m + 1]))
    if mode == 'redevelopment':
        return excess.copy(), dict(info, redev=excess.copy(), surplus=np.zeros(n), payback=np.zeros(n))
    if mode != 'surplus':
        raise ValueError(f"Unknown near-term mode '{mode}'.")
    if absorb_w is not None:
        join, ab = absorb_overbuild(excess, absorb_w, R)
        return join, dict(info, redev=np.zeros(n), surplus=ab['U'], payback=-ab['paid'], absorption=ab)
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
            soil=None, soil_on_replacement=True, gfa_fixed=None, events=None,
            brownfield_share=None, brownfield_w=None, clip_soil_share=False):
    """One forward path, 2025..2050 (index 0 = 2025, a model value; callers that
    anchor 2025 on observations overwrite it).

    pop, hh, pop_growth, v : arrays over the years (v may vary by year)
    rate_demol, rate_unc   : demolition and residual, shares of last year's stock
                             (rate_unc may be an array by year: the Reference variant)
    join                   : optional array of dwellings built above the requirement
                             (the 2026 overbuild), added before the RV split
    join_redev             : the part of join that replaces extra removals
                             (redevelopment); the rest adds to the stock
                             (stock_join). The extra stock does not enter the
                             demolition / residual base (a second-order effect).
    dev_2025, rho_dev      : 2025 deviation, fading as rho^(t-2025), booked to the residual
    rv_share               : retirement-village share of ALL dwellings built (out of scope)
    shares                 : DataFrame years x typology (floor-area shares)
    size, olf              : dicts by typology
    intensity, intensity_upfront : dicts by typology, each a scalar (constant over
                             time) or an array over the years (kg CO2e/m2, incl. soil)
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
    events                 : optional {typology: K (years x years)}: replacement and
                             repaint emissions, kg/m2 of the cohort built in year i
                             occurring in year j (events.kernel); b_t = gfa_t @ K is
                             added to carbon_t (time-resolved accounting).
    MODEL v2.1.0 (pathway levers; every default reproduces the earlier result bit for bit):
    soil[t] may be an array over the years (L7 soil-aware planning, TL7 lowest-carbon soils).
    brownfield_share, brownfield_w : optional arrays over the years (L6 brownfield development):
                             target share s of ALL new floor area on previously developed land
                             and its adoption weight w; the soil-free floor area becomes
                             soil_free + w max(0, s total - soil_free), so the replacement floor
                             area (already soil-free) is never counted twice.
    clip_soil_share        : True (theoretical limit, banked zero-building years): the soil-bearing
                             share is clipped to [0, 1] and set to 0 where nothing is built.

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

    # nothing built (zero-year guard, MODEL v3.2.0). A negative total occurs only in the requirement pass of
    # pathways.run (join = 0, the floor area unused there); a built path is >= 0 in dwellings (checked in pathways)
    zero_built = total < BUILT_ZERO_TOL_M2
    total = np.where(zero_built, 0.0, total)
    gfa_t = shares.values.T * total                  # (typology, years)
    # intensities: one value per typology (constant), or one per typology and
    # year (materials decarbonised, projection.DECARB_MODE); both broadcast to (typ, years)
    I = np.array([np.broadcast_to(np.asarray(intensity[t], float), (len(hh),)) for t in typ])
    U = np.array([np.broadcast_to(np.asarray(intensity_upfront[t], float), (len(hh),)) for t in typ])
    if soil is None:
        soil_share, soil_free = np.ones(len(hh)), np.zeros(len(hh))
        carbon_t, upfront_t = I * gfa_t, U * gfa_t
    else:
        if any(np.ndim(soil[t]) for t in typ):        # soil factor by year (MODEL v2.1.0 levers)
            sY = np.array([np.broadcast_to(np.asarray(soil[t], float), (len(hh),)) for t in typ])
        else:
            sY = np.array([soil[t] for t in typ])[:, None]
        soil_free = (np.zeros(len(hh)) if soil_on_replacement else
                     np.clip(demol + unc + join_redev, 0.0, None) * (1.0 - rv_share) * D)
        soil_free_repl = soil_free
        if brownfield_share is not None:
            soil_free = soil_free + np.asarray(brownfield_w, float) * np.maximum(
                0.0, np.asarray(brownfield_share, float) * total - soil_free)
        soil_share = (1.0 - np.divide(soil_free, total, out=np.zeros(len(hh)),
                                                         where=total != 0))
        # MODEL v3.2.0: the soil-bearing share is a share: clipped to [0, 1] in every run, and 0 in a zero year
        soil_share = np.where(zero_built, 0.0, np.clip(soil_share, 0.0, 1.0))
        if clip_soil_share:
            soil_share = np.where(total <= SOIL_ZERO_TOL_M2, 0.0, soil_share)
        carbon_t = (I - sY) * gfa_t + (sY * gfa_t) * soil_share
        upfront_t = (U - sY) * gfa_t + (sY * gfa_t) * soil_share
    b_t = np.zeros_like(gfa_t)
    if events is not None:                           # time-resolved B2/B4 of the new cohorts
        b_t = np.array([gfa_t[k] @ events[t] for k, t in enumerate(typ)])
        carbon_t = carbon_t + b_t
    return dict(
        years=shares.index.values, typ=typ, pop=pop, hh=hh, S=S, d_hh=d_hh, d_hh_raw=d_raw,
        D=D, olf=olf_f, occ=occ, structural=structural, growth_gross=g_gross, growth=growth,
        hs_pos=hs_pos, hs_avoided=hs_avoided, extra=extra, extra_clip=extra_clip,
        c_gross=c_gross, total=total,
        v=np.array(v), stock=stock, prev=prev, allow=allow, change=change, demol=demol,
        unc=unc, dev=dev, join=join, join_redev=join_redev, stock_join=stock_join, rv=rv, dwell_in_scope=total / D, rv_units=-rv,
        gfa_t=gfa_t, carbon_t=carbon_t, carbon=carbon_t.sum(axis=0), upfront=upfront_t.sum(axis=0), b_t=b_t,
        soil_share=soil_share, soil_free_gfa=soil_free, gfa_adj=gfa_adj,
        soil_free_replacement_gfa=(soil_free_repl if soil is not None else np.zeros(len(hh))),
        soil=((sY * gfa_t) * soil_share).sum(axis=0) if soil is not None else None)
