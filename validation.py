"""
VALIDATION -- run by run_all.py; results in outputs/reports/validation.md and outputs/data/metrics.json
=================================================================================
Two checks, both DESCRIPTIVE. Nothing here is used to set or tune a parameter.

1. ROLLING-ORIGIN HINDCAST of dwellings built (Tashman 2000)
   Origins are census years (2006, 2013, 2018): the only points where the
   household series is independently benchmarked. For each origin O the net
   replacement rate is calibrated on the model's calibration window up to O
   only, and dwellings built over O+1 .. last census-benchmarked year are
   predicted with the historical identity:

       built_t = new households + vacancy allowance + vacancy change
                 + net replacement rate x stock_(t-1)

   using the ACTUAL households and vacancy of the test years (a conditional
   hindcast: it tests the replacement term, the one part of the identity that
   is calibrated rather than observed). Methods compared:
     constant   long-run rate over the calibration window up to O (as the model)
     recent     the rate of the last intercensal interval before O
     linked     net rate = a + b x townhouse consents / stock, OLS on the
                intercensal intervals up to O (n = 3-5 points; reported only to
                show how poorly identified it is)
   Three origins cannot support a test statistic; errors are reported as
   percentages of actual building, per origin.

2. OUT-OF-SAMPLE CHECK OF 2026 against observed consents
   Model: 2026 dwellings built (all categories: in scope + retirement
   villages), converted to 2026 consents by inverting the completion rate and
   lag: consents_2026 = (built / c - W x consents_2025) / (1 - W). Observed: all-category
   consents in the consent file for 2026 months. Year-to-date months are
   compared with the model's annual figure x the average share of annual
   consents falling in those months (2010-2025, ratio-to-annual seasonal
   shares), never annualised naively. PENDING while the consent file ends
   before 2026.

Writes outputs/reports/validation.md and outputs/data/baseline/validation.json.
"""
import contextlib
import importlib
import io
import json

import numpy as np
import pandas as pd

import projection
import engine
import layout
import naming as N

OUT_MD = layout.report('validation.md')
OUT_JSON = layout.data('baseline/validation.json')
ORIGINS = (2006, 2013, 2018)
SEASONAL_YEARS = (2010, 2025)


# Settings that remove every use of observed 2026 data (A1: consents nowcast,
# 2026 population growth), so that the 2026 check stays out of sample. The
# 2025 deviation is then carried as in the pre-A1 model.
# MODEL v4.0.0: no consent month after December 2025 and no 2026 population observation. With the completion lag
# (projection.COMPLETION_LAG_MONTHS = 17) 2026 completions are still observed (consents to July 2025), so the 2026
# overbuild is observed and 2027 follows the fading rule; with no observed projection year at all (L = 0) projection
# falls back to the carried 2025 deviation (OVERBUILD_RULE 'carried_deviation', the MODEL v3.3 definition).
NO_2026_DATA = dict(CONSENT_DATA_END='2025-12-01', NOWCAST_POPULATION=False)


def run_boss(**settings):
    """One silent projection.main() with the given settings; module defaults are
    restored afterwards."""
    M = importlib.reload(projection)
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return M.main()
    finally:
        importlib.reload(projection)


def census_intervals(B, last):
    cy = [int(y) for y in B['census'].index if B['years_hist'].min() <= y <= last]
    return [(a + 1, b) for a, b in zip(cy[:-1], cy[1:])]      # calendar years a+1..b


# VALIDATION_VACANCY (v1.2): the hindcast feeds census vacancy into the identity.
#   'consistent' (default): one empty/unoccupied share (pooled 2018 and 2023
#   private dwellings) applied to every census, removing the 2013->2018
#   empty/away definitional break; 'as_published': the published empty series
#   (reported alongside).
VALIDATION_VACANCY = 'consistent'


def consistent_share(B):
    cen = B['census']
    return float(cen.loc[[2018, 2023], 'empty'].sum() / cen.loc[[2018, 2023], 'unoccupied'].sum())


def history_bands(B):
    """Floor area built by demand band in the census intervals 1991-2023 (and 2023-2025), interval
    means in Mm2 per year, in scope (the census-interval bars of the floor-area figures). Vacancy on ONE
    definition throughout (the pooled 2018/2023 empty share of unoccupied private dwellings applied to
    every census, consistent_share). Between censuses annual detail is not identified, so each band is the
    mean over the interval's years y0+1..y1.

    MODEL v3.1.0 (A3): no band is rescaled. The bands are household formation (population growth, smaller
    households, extra space), vacancy (allowance and change), the census-measured net replacement (the rate
    of the census dwelling-count identity of the interval x the previous year's stock, as stock_identity_history;
    may be negative, e.g. 1996-2001), the retirement-village units (negative; out of scope, as in D10) and the
    unexplained building, the remainder to the observed in-scope floor area built (may be negative, e.g. 2013-2018).
    Each dwelling component is converted at the year's realised dwelling size. The bands add up to the observed
    in-scope floor area built in every interval (checked to 1e-9). The last interval (after the latest census)
    uses consent-derived households and the latest census rate carried."""
    yh = np.arange(1992, 2026)
    D = B['blended_dwelling_size'].loc[yh]
    cal = _consistent_calibration(B)
    cy, intervals = _history_intervals(B, yh)
    _, repl = _census_replacement(B, yh, cal, cy)
    built = B['hist_built_gfa'].loc[yh]
    parts = [('growth', B['hist_growth'].loc[yh] - B['hist_avoided'].loc[yh]),
             ('smaller_households', B['hist_hs_raw'].loc[yh]),
             ('extra_space', B['d_hh'].loc[yh] * (D - B['occupied_area_per_dwelling'].loc[yh])),
             ('vacancy', (cal['allow'] + cal['change']).loc[yh] * D),
             ('replacement_census', repl * D),
             ('retirement_villages', cal['rv'].loc[yh] * D)]
    parts.append(('unexplained', built - sum(v for _, v in parts)))
    rows = []
    for y0, y1 in intervals:
        mean = lambda ser: float(np.mean(np.asarray(ser.loc[y0 + 1:y1], float)))
        m = {k: mean(v) for k, v in parts}
        obs = mean(built)
        if not np.isclose(sum(m.values()), obs, rtol=1e-9, atol=1e-6):
            raise SystemExit(f'history_bands {y0}-{y1}: the bands do not add up to the observed floor area built.')
        rows += [dict(interval=f'{y0}-{y1}', year_start=y0 + 1, year_end=y1, band=N.band_data_label(k),
                      floor_area_Mm2_per_year=m[k] / 1e6, observed_built_Mm2_per_year=obs / 1e6,
                      households_from=('census' if y1 <= cy[-1] else _bridge_label())) for k in N.BANDS_HISTORY]
    return pd.DataFrame(rows)


def history_unexplained(B):
    """A3 check: the unexplained floor area of history_bands against the unexplained dwellings of
    stock_identity_history x the year's dwelling size, and the 1992-2025 unexplained sum (dwellings and % of
    the dwellings built)."""
    yh = np.arange(1992, 2026)
    D = B['blended_dwelling_size'].loc[yh]
    cal = _consistent_calibration(B)
    cy, _ = _history_intervals(B, yh)
    _, repl = _census_replacement(B, yh, cal, cy)
    built_u = B['hist_built_units'].loc[yh]
    unexpl_u = built_u - (B['d_hh'].loc[yh] + (cal['allow'] + cal['change']).loc[yh] + repl + cal['rv'].loc[yh])
    hb = history_bands(B)
    lab = N.band_data_label('unexplained')
    h = hb[hb['band'] == lab]
    n_years = (h['year_end'] - h['year_start'] + 1)
    remainder_m2 = float((h['floor_area_Mm2_per_year'] * n_years).sum() * 1e6)
    units_x_size_m2 = float((unexpl_u * D).sum())
    return dict(unexplained_dwellings_1992_2025=float(unexpl_u.sum()),
                dwellings_built_1992_2025=float(built_u.sum()),
                unexplained_share_of_built=float(unexpl_u.sum() / built_u.sum()),
                unexplained_floor_area_Mm2_remainder=remainder_m2 / 1e6,
                unexplained_dwellings_x_size_Mm2=units_x_size_m2 / 1e6,
                difference_Mm2=(remainder_m2 - units_x_size_m2) / 1e6,
                note='the floor-area remainder of history_bands and the unexplained dwellings of stock_identity_history '
                     'x the year\'s dwelling size agree to difference_Mm2 (household formation in floor area, growth + '
                     'smaller households + extra space, equals new households x the realised dwelling size)')


def _consistent_calibration(B):
    """The stock identity of the history on ONE vacancy definition (consistent_share), as D05."""
    return engine.calibrate_stock(B['years_hist'], B['hist_hh'],
                                  engine.vacancy_knots(B['census'], float(B['empty_share_measured']), consistent_share(B)),
                                  B['hist_units_all_c'], B['hist_rv_units_c'], projection.COMPLETION_RATE,
                                  projection.DEMOLITION_RATE, projection.DEMOLITION_CALIB_START, B['calib_end'])


def _history_intervals(B, yh):
    cy = [int(y) for y in B['census'].index if yh[0] - 1 <= y <= int(B['calib_end'])]
    return cy, list(zip(cy[:-1], cy[1:])) + [(cy[-1], int(yh[-1]))]


def _census_replacement(B, yh, cal, cy):
    """The census-measured net replacement rate of each year (the rate of its census interval, the
    latest carried after the latest census) and the net replacement in dwellings (rate x the previous
    year's stock of the consistent calibration)."""
    rates = B['census_rates'].set_index(['y0', 'y1'])['rate']
    rate = pd.Series(np.nan, index=yh)
    for (y0, y1), r in rates.items():
        rate.loc[(rate.index > y0) & (rate.index <= y1)] = r
    rate.loc[rate.index > cy[-1]] = rates.loc[(cy[-2], cy[-1])]          # 2024-25: the latest rate carried
    return rate, rate * cal['prev'].loc[yh]


def stock_identity_history(B):
    """Dwellings built per year in the census intervals 1991-2023 (and 2023-2025) by component
    (MODEL v1.1.0; D05c), interval means over the years y0+1..y1, in scope:

        dwellings built = new households + vacancy (allowance and change, ONE definition)
                          + net replacement (census-measured) + retirement villages (negative)
                          + unexplained building

    Net replacement is the census-measured quantity the model uses: the rate of the census
    dwelling-count identity of its interval (engine.census_interval_rates: completions,
    under-construction corrected, minus the change in census private dwellings, per stock-year;
    D07) times the previous year's stock of the consistent calibration, year by year. After the
    latest census (2024-2025, households consent-derived) the latest interval's rate is carried, as
    in the AESA history. Unexplained building is what remains: building not explained by household
    formation, vacancy and census-measured replacement (redevelopment not captured by the census
    counts, error in the household estimates, or residual); it may be negative. It equals the
    household-identity residual (cal['net']) minus the census-measured replacement."""
    yh = np.arange(1992, 2026)
    cal = _consistent_calibration(B)
    cy, intervals = _history_intervals(B, yh)
    rate, repl = _census_replacement(B, yh, cal, cy)
    parts = dict(new_households=B['d_hh'].loc[yh], vacancy=(cal['allow'] + cal['change']).loc[yh],
                 net_replacement_census=repl, retirement_villages=cal['rv'].loc[yh])
    built = B['hist_built_units'].loc[yh]
    parts['unexplained_building'] = built - sum(parts.values())
    rows = []
    for y0, y1 in intervals:
        mean = lambda ser: float(np.mean(np.asarray(ser.loc[y0 + 1:y1], float)))
        rows.append(dict(interval=f'{y0}-{y1}', year_start=y0 + 1, year_end=y1,
                         **{f'{k}_per_year': mean(v) for k, v in parts.items()},
                         dwellings_built_per_year=mean(built), net_replacement_rate=float(rate.loc[y1]),
                         household_identity_residual_per_year=mean(cal['net'].loc[yh]),
                         households_from=('census' if y1 <= cy[-1] else _bridge_label())))
    return pd.DataFrame(rows)


def household_formation_history(B):
    """New households per year in the census intervals 1991-2023 (and 2023-2025) by source (MODEL
    v1.1.0; D04c), interval means over the years y0+1..y1: from population growth (dP / S) and from
    the change in household size (the rest of the change in households). Households are census-
    benchmarked at the census years, so each interval's total is the census-anchored change
    divided by its length; 2024-2025 are consent-derived estimates with no census check."""
    yh = np.arange(1992, 2026)
    pop, hh, S = B['hist_pop'], B['hist_hh'], B['hist_S']
    pop_part = pop.diff().loc[yh] / S.loc[yh]
    d_hh = hh.diff().loc[yh]
    cy, intervals = _history_intervals(B, yh)
    rows = []
    for y0, y1 in intervals:
        n = y1 - y0
        mean = lambda ser: float(np.mean(np.asarray(ser.loc[y0 + 1:y1], float)))
        rows.append(dict(interval=f'{y0}-{y1}', year_start=y0 + 1, year_end=y1, years=n,
                         from_population_growth_per_year=mean(pop_part),
                         from_household_size_change_per_year=mean(d_hh - pop_part),
                         net_new_households_per_year=mean(d_hh),
                         households_start=float(hh.loc[y0]), households_end=float(hh.loc[y1]),
                         households_from=('census' if y1 <= cy[-1] else _bridge_label())))
    return pd.DataFrame(rows)


def hindcast(B, const_share=None):
    yh = B['years_hist']
    end = int(B['calib_end'])
    units_all = B['hist_units_all_c']                 # consents timed as completions
    c = projection.COMPLETION_RATE
    cal_full = engine.calibrate_stock(yh, B['hist_hh'], engine.vacancy_knots(B['census'], B['empty_share_measured'],
                                                                             const_share),
                                      units_all, B['hist_rv_units_c'], c, projection.DEMOLITION_RATE,
                                      projection.DEMOLITION_CALIB_START, end)
    crates = B['census_rates']
    built = c * units_all
    need = built - cal_full['net']               # households + allowance + change (observed)
    prev = cal_full['prev']
    th = B['hist_typ_units']['Townhouses']
    ivs = census_intervals(B, end)

    def rate(a, b):
        return engine.window_rate(cal_full, a, b)

    rows = []
    for O in ORIGINS:
        if O >= end:
            continue
        test = (yh > O) & (yh <= end)
        actual = float(built[test].sum())
        preds = {}
        r_const = rate(projection.DEMOLITION_CALIB_START, O)
        preds['constant'] = (r_const, (need + r_const * prev)[test])
        before = [iv for iv in ivs if iv[1] <= O]
        r_recent = rate(*before[-1])
        preds['recent'] = (r_recent, (need + r_recent * prev)[test])
        X = np.array([th.loc[a:b].sum() / prev.loc[a:b].sum() for a, b in before])
        Y = np.array([rate(a, b) for a, b in before])
        A = np.c_[np.ones(len(X)), X]
        coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
        preds['linked'] = (None, (need + (coef[0] + coef[1] * th / prev) * prev)[test])
        r_dc = engine.census_window_rate(crates, projection.NET_REPLACEMENT_WINDOW[0], O)
        preds['dwelling_count'] = (r_dc, (need + r_dc * prev)[test])
        # reference method (the Reference rule): the most recent intercensal rate before the origin,
        # fading to the long-run dwelling-count rate with a 10-year half-life from O
        r_last = float(crates[crates['y1'] <= O].iloc[-1]['rate'])
        path = pd.Series(engine.replacement_path('REF', r_dc, r_last, yh - O + 2025, 10.0), index=yh)
        preds['reference'] = (r_last, (need + path * prev)[test])
        for m, (r, ser) in preds.items():
            p = float(ser.sum())
            rows.append(dict(origin=O, test=f'{O + 1}-{end}', method=m,
                             rate_pct=None if r is None else 100 * r,
                             n_intervals=len(before) if m == 'linked' else None,
                             linked_b=float(coef[1]) if m == 'linked' else None,
                             predicted=p, actual=actual, error_pct=100 * (p / actual - 1),
                             years=[int(y) for y in yh[test]], predicted_path=[float(x) for x in ser.values],
                             actual_path=[float(x) for x in built[test].values]))
    return rows


def hindcast_stock(B):
    """(B) Census private-dwelling stock in the last census, predicted from
    each origin: stock_O + completions(O -> last) - rate x stock-years, with the
    rate calibrated on census intervals up to O only (long run from the model's
    window start, or the last interval before O). Actual completions are used,
    so this tests the replacement term of the dwelling-count identity."""
    cr = B['census_rates']
    last = int(cr['y1'].max())
    rows = []
    for O in ORIGINS:
        if O >= last:
            continue
        after = cr[cr['y0'] >= O]
        built, sy = float(after['built'].sum()), float(after['stock_years'].sum())
        actual = float(after['d_stock'].sum())
        before = cr[cr['y1'] <= O]
        for m, r in (('long run', engine.census_window_rate(cr, projection.NET_REPLACEMENT_WINDOW[0], O)),
                     ('recent interval', float(before.iloc[-1]['rate']))):
            pred = built - r * sy
            rows.append(dict(origin=O, test=f'{O}-{last}', method=m, rate_pct=100 * r,
                             predicted=pred, actual=actual, error_pct=100 * (pred / actual - 1)))
    return rows


def dhe_crosscheck(B):
    """(C) the dwelling-count identity on the Stats NZ DHE private-dwelling
    series (Table 1; bases = census counts) at 31 March of census years, and
    (D) the net replacement implied by Stats NZ's intercensal weighting after
    the 2023 base (quarterly DHE growth vs lagged consents)."""
    dq = projection.load_historical_households(projection.FILE_HOUSEHOLDS_HIST, sheet='Table 1').set_index('Date')['Households']
    years = [int(y) for y in B['census'].index if pd.Timestamp(int(y), 3, 31) in dq.index]
    stock = pd.Series({y: float(dq[pd.Timestamp(y, 3, 31)]) for y in years})
    cm = B['consents_monthly']
    r_dhe = engine.census_interval_rates(stock, cm, projection.COMPLETION_RATE, B['lag_census'], day_of_year=90)
    w0, w1 = projection.NET_REPLACEMENT_WINDOW
    out = dict(dhe_rate_long=engine.census_window_rate(r_dhe, w0, w1),
               census_rate_long=engine.census_window_rate(B['census_rates'], w0, w1),
               dhe_rates=r_dhe[['y0', 'y1', 'rate']].to_dict('records'))
    # (D) after the 2023 base: 2023-06-30 -> last quarter
    q = cm.resample('QE').sum()
    ratio = (dq.diff() / q.shift(4).reindex(dq.index)).loc['2023-09-30':]
    out['dhe_weight_mean'], out['dhe_weight_sd'] = float(ratio.mean()), float(ratio.std())
    t0, t1 = pd.Timestamp('2023-06-30'), dq.index.max()
    idx = cm.index
    tm = idx.year + (idx.dayofyear - 1 + idx.days_in_month / 2.0) / 365.25
    frac = lambda d: d.year + (d.dayofyear) / 365.25
    m = (tm > frac(t0) - B['lag_census']) & (tm <= frac(t1) - B['lag_census'])
    built = projection.COMPLETION_RATE * float(cm[m].sum())
    d_stock = float(dq[t1] - dq[t0])
    sy = float((dq[t0] + dq[t1]) / 2 * (frac(t1) - frac(t0)))
    out.update(dhe_post2023_period=f'{t0.date()}..{t1.date()}', dhe_post2023_rate=(built - d_stock) / sy)
    return out


def seasonal_shares(consents):
    return engine.seasonal_shares(consents, SEASONAL_YEARS)   # mean share of the year, by month


def _bridge_label():
    """MODEL v4.2: the household source after the last census (projection.HH_BRIDGE)."""
    return 'erp_S' if projection.HH_BRIDGE == 'erp_S' else 'consents'


def check_2026(B, consents=None, B_full=None):
    """consents: monthly all-category series (index = month); read from the
    consent file when not given. MODEL v4.0.0, with the completion lag (B['lag_months'] > 0): 2026 completions are
    observed even without 2026 data, so the out-of-sample check moves to the first year the run without 2026 data
    MODELS (its first unobserved year, 2027 at L = 17): its building (requirement + the fading excess) against the
    observed pipeline building of that year in the full-data run B_full (consents to July 2026, lagged)."""
    if int(B.get('lag_months', 0) or 0) > 0:
        pipe0 = (B['pipe'] or {}).get('years', [])
        ty = (max(pipe0) + 1) if pipe0 else 2026
        fy = list(B['forecast_years'])
        E = B['engine_out']['50th']
        i = fy.index(ty)
        model_all = float(E['dwell_in_scope'][i] + E['rv_units'][i])
        out = dict(status='pipeline', lag_months=int(B['lag_months']), data_end=B['lag_info']['consents_observed_to'],
                   pipeline_years_without_2026_data=pipe0, target_year=ty, model_built_all=model_all,
                   model_consent_equivalent_2026=None)
        fp = (B_full or {}).get('pipe') if B_full is not None else None
        if fp and ty in fp['years']:
            obs = float(fp['built_all'][ty])
            out.update(observed_pipeline_built_all=obs, ratio_observed_to_model=obs / model_all,
                       observed_from=f"consents {fp['years']} lagged {int(B_full['lag_months'])} months")
        return out
    if consents is None:
        c = projection.load_consents()
        consents = c.set_index(pd.to_datetime(c['Date']))[projection.COL_DWELLINGS_TOTAL]
    s = consents.sort_index()
    last = s.index.max()
    E = B['engine_out']['50th']
    built_all_2026 = float(E['dwell_in_scope'][1] + E['rv_units'][1])
    # completions_2026 = c x [(1 - W) consents_2026 + W consents_2025]  ->  consents_2026
    W = B['lag_w']
    cons_2025 = float(B['hist_units_all'].loc[2025])
    model_consents_2026 = (built_all_2026 / projection.COMPLETION_RATE - W * cons_2025) / (1.0 - W)
    out = dict(data_end=str(last.date()), model_built_all_2026=built_all_2026,
               model_consent_equivalent_2026=model_consents_2026)
    ytd = s.loc['2026-01-01':]
    if ytd.empty:
        out['status'] = 'pending'
        return out
    months = sorted(set(ytd.index.month))
    share = float(seasonal_shares(s).loc[months].sum())
    expected = model_consents_2026 * share
    out.update(status='observed', months=months, observed_ytd=float(ytd.sum()),
               seasonal_share=share, model_expected_ytd=expected,
               ratio_observed_to_model=float(ytd.sum() / expected))
    last12 = s.loc[last - pd.DateOffset(months=11):last]
    out.update(last12_months=f'{last12.index.min().date()}..{last.date()}', observed_last12=float(last12.sum()))
    return out


def write(rows, chk, stock_rows=None, dhe=None, rows_pub=None, vac=None):
    lines = [f'Net replacement in use: census dwelling-count identity '
             f'(window {projection.NET_REPLACEMENT_WINDOW[0]}-{projection.NET_REPLACEMENT_WINDOW[1]}).', '',
             '### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)', '',
             'Actual households and vacancy fed in; only the net-replacement term is predicted. '
             'Error = predicted / actual - 1.', '',
             (f"Vacancy definition: {VALIDATION_VACANCY} -- the pooled 2018/2023 empty share of unoccupied private "
              f"dwellings ({100 * vac['pooled_share']:.1f}%) applied to every census; the 2013 census share was "
              f"{100 * vac['share_2013']:.1f}% (published empty vacancy 2013 {100 * vac['v_2013']:.2f}% -> 2018 "
              f"{100 * vac['v_2018']:.2f}%, a definitional break). The as-published series is shown below the table."
              if vac else ''), '',
             '| origin | test years | method | rate used (%/yr) | predicted | actual | error |',
             '|---|---|---|---|---|---|---|']
    for r in rows:
        rate = (f"{r['rate_pct']:+.3f}" if r['rate_pct'] is not None
                else f"linked: b = {r['linked_b']:.2f} on {r['n_intervals']} intervals")
        lines.append(f"| {r['origin']} | {r['test']} | {r['method']} | {rate} | {r['predicted']:,.0f} | "
                     f"{r['actual']:,.0f} | {r['error_pct']:+.1f}% |")
    if rows_pub:
        lines += ['', '### (A2) Same hindcast with census vacancy as published (2013->2018 break included)', '',
                  '| origin | test years | method | predicted | actual | error |', '|---|---|---|---|---|---|']
        for r in rows_pub:
            lines.append(f"| {r['origin']} | {r['test']} | {r['method']} | {r['predicted']:,.0f} | "
                         f"{r['actual']:,.0f} | {r['error_pct']:+.1f}% |")
    if stock_rows:
        lines += ['', '### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock '
                  '(dwelling-count identity; descriptive)', '',
                  'Change in census private dwellings from the origin to 2023, predicted as completions '
                  '- rate x stock-years with the rate calibrated up to the origin.', '',
                  '| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |',
                  '|---|---|---|---|---|---|---|']
        for r in stock_rows:
            lines.append(f"| {r['origin']} | {r['test']} | {r['method']} | {r['rate_pct']:+.3f} | "
                         f"{r['predicted']:,.0f} | {r['actual']:,.0f} | {r['error_pct']:+.1f}% |")
    if dhe:
        lines += ['', '### (C, D) Cross-checks of the net replacement rate', '',
                  f"- Census dwelling counts, {projection.NET_REPLACEMENT_WINDOW[0]}-{projection.NET_REPLACEMENT_WINDOW[1]}: "
                  f"{100 * dhe['census_rate_long']:+.3f}%/yr.",
                  f"- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census "
                  f"counts): {100 * dhe['dhe_rate_long']:+.3f}%/yr.",
                  f"- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = "
                  f"{dhe['dhe_weight_mean']:.4f} x consents lagged four quarters (sd {dhe['dhe_weight_sd']:.4f}); "
                  f"with this model's completion rate and lag this implies net replacement of "
                  f"{100 * dhe['dhe_post2023_rate']:+.3f}%/yr over {dhe['dhe_post2023_period']}. This is Stats NZ's "
                  f"assumption, not an observation."]
    lines += ['', '### 2026 out-of-sample check against observed consents', '',
              'Run on the model WITHOUT any observed 2026 input (settings: '
              f"{chk.get('model_settings')}), so the check stays out of sample.", '']
    if chk['status'] == 'pipeline':
        lines.append(f"Completion lag {chk['lag_months']} months: without 2026 data the pipeline years are "
                     f"{chk['pipeline_years_without_2026_data']}; the model's {chk['target_year']} building "
                     f"{chk['model_built_all']:,.0f} (all categories)"
                     + (f" vs the observed pipeline {chk['observed_pipeline_built_all']:,.0f} "
                        f"({chk['observed_from']}); observed / model = {chk['ratio_observed_to_model']:.3f}."
                        if 'observed_pipeline_built_all' in chk else '.')
                     + ' Descriptive only: not used to set any parameter.')
    elif chk['status'] == 'pending':
        lines.append(f"PENDING: the consent file ends {chk['data_end']}. Model 2026: "
                     f"{chk['model_built_all_2026']:,.0f} dwellings built (all categories) = "
                     f"{chk['model_consent_equivalent_2026']:,.0f} consent-equivalents.")
    else:
        lines.append(f"Months observed: {chk['months']}. Observed {chk['observed_ytd']:,.0f} vs model "
                     f"{chk['model_expected_ytd']:,.0f} (annual {chk['model_consent_equivalent_2026']:,.0f} x "
                     f"seasonal share {chk['seasonal_share']:.3f}); observed / model = "
                     f"{chk['ratio_observed_to_model']:.3f}. Latest 12 months ({chk['last12_months']}): "
                     f"{chk['observed_last12']:,.0f}. Descriptive only: not used to set any parameter.")
    with open(layout.writing(OUT_MD), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(layout.writing(OUT_JSON), 'w') as f:
        json.dump(N.keys(dict(hindcast=rows, hindcast_as_published=rows_pub, vacancy_definition=vac,
                              hindcast_stock=stock_rows, net_replacement_crosscheck=dhe,
                              model_method='dwelling_count', check_2026=chk)), f, indent=2)
    print('\n'.join(lines))


def lag_hindcast(B):
    """MODEL v4.0.0 STOP check: the rolling-origin hindcast of the census dwelling-count identity (hindcast_stock) at
    the adopted completion lag and at L = 0 (MODEL v3.3 timing, the census under-construction correction on). STOP if
    the adopted lag is worse than L = 0 by the mean absolute error over the origins in BOTH rate methods (long run,
    recent interval). Writes baseline/completion_lag_hindcast.csv and .json."""
    L = int(B.get('lag_months', 0) or 0)
    if L == 0:
        return None
    rows = [dict(lag_months=L, **r) for r in hindcast_stock(B)]
    rows += [dict(lag_months=0, **r) for r in hindcast_stock(run_boss(COMPLETION_LAG_MONTHS=0))]
    df = pd.DataFrame(rows)
    mae = (df.assign(abs_error_pct=df['error_pct'].abs()).groupby(['method', 'lag_months'])['abs_error_pct']
           .mean().unstack())
    worse = {m: bool(mae.loc[m, L] > mae.loc[m, 0]) for m in mae.index}
    out = dict(adopted_lag_months=L, mean_abs_error_pct={m: {int(k): float(v) for k, v in mae.loc[m].items()}
                                                          for m in mae.index},
               adopted_worse_by_method=worse, stop=all(worse.values()),
               rule='STOP if the adopted lag has the larger mean absolute error in every rate method')
    N.columns(df).to_csv(layout.writing(layout.data('baseline/completion_lag_hindcast.csv')), index=False)
    with open(layout.writing(layout.data('baseline/completion_lag_hindcast.json')), 'w') as f:
        json.dump(N.keys(out), f, indent=1)
    if out['stop']:
        raise SystemExit(f'STOP (completion lag): the hindcast at L = {L} is worse than at L = 0: {out}')
    return out


def main():
    B = run_boss()
    uses_2026 = B['_join_mode'] == 'market_excess' or B['pop_nowcast'] is not None
    B0 = run_boss(**NO_2026_DATA) if uses_2026 else B
    chk = check_2026(B0, B_full=B)
    chk['model_settings'] = NO_2026_DATA if uses_2026 else 'as run (no 2026 data used)'
    sh = consistent_share(B)
    cen = B['census']
    vac = dict(definition=VALIDATION_VACANCY, pooled_share=sh,
               share_2013=float(cen.loc[2013, 'empty'] / cen.loc[2013, 'unoccupied']),
               v_2013=float(cen.loc[2013, 'empty'] / cen.loc[2013, 'total_private']),
               v_2018=float(cen.loc[2018, 'empty'] / cen.loc[2018, 'total_private']))
    rows_c, rows_p = hindcast(B, sh), hindcast(B, None)
    main_rows = rows_c if VALIDATION_VACANCY == 'consistent' else rows_p
    write(main_rows, chk, hindcast_stock(B), dhe_crosscheck(B), rows_pub=rows_p, vac=vac)
    lag_hindcast(B)
    history_bands(B).to_csv(layout.writing(layout.data('baseline/bands_history.csv')), index=False)
    N.columns(stock_identity_history(B)).to_csv(layout.writing(layout.data('baseline/stock_identity_history.csv')),
                                                index=False)
    N.columns(household_formation_history(B)).to_csv(
        layout.writing(layout.data('baseline/household_formation_history.csv')), index=False)
    with open(layout.writing(layout.data('baseline/history_unexplained.json')), 'w') as f:    # MODEL v3.1.0 (A3)
        json.dump(N.keys(history_unexplained(B)), f, indent=1)


if __name__ == '__main__':
    main()
