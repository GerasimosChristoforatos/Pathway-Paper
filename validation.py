"""
VALIDATION -- run by run_all.py after every change; results logged in CHANGELOG.md
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

Writes outputs/validation.md and outputs/validation.json.
"""
import contextlib
import importlib
import io
import json
import os

import numpy as np
import pandas as pd

import Boss
import engine

OUT_MD = os.path.join(Boss.OUT_DIR, 'validation.md')
OUT_JSON = os.path.join(Boss.OUT_DIR, 'validation.json')
ORIGINS = (2006, 2013, 2018)
SEASONAL_YEARS = (2010, 2025)


# Settings that remove every use of observed 2026 data (A1: consents nowcast,
# 2026 population growth), so that the 2026 check stays out of sample. The
# 2025 deviation is then carried as in the pre-A1 model.
NO_2026_DATA = dict(NEAR_TERM_JOIN='carried_deviation', NOWCAST_POPULATION=False)


def run_boss(**settings):
    """One silent Boss.main() with the given settings; module defaults are
    restored afterwards."""
    M = importlib.reload(Boss)
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return M.main()
    finally:
        importlib.reload(Boss)


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


def hindcast(B, const_share=None):
    yh = B['years_hist']
    end = int(B['calib_end'])
    units_all = B['hist_units_all_c']                 # consents timed as completions
    c = Boss.COMPLETION_RATE
    cal_full = engine.calibrate_stock(yh, B['hist_hh'], engine.vacancy_knots(B['census'], B['empty_share_measured'],
                                                                             const_share),
                                      units_all, B['hist_rv_units_c'], c, Boss.DEMOLITION_RATE,
                                      Boss.DEMOLITION_CALIB_START, end)
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
        r_const = rate(Boss.DEMOLITION_CALIB_START, O)
        preds['constant'] = (r_const, (need + r_const * prev)[test])
        before = [iv for iv in ivs if iv[1] <= O]
        r_recent = rate(*before[-1])
        preds['recent'] = (r_recent, (need + r_recent * prev)[test])
        X = np.array([th.loc[a:b].sum() / prev.loc[a:b].sum() for a, b in before])
        Y = np.array([rate(a, b) for a, b in before])
        A = np.c_[np.ones(len(X)), X]
        coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
        preds['linked'] = (None, (need + (coef[0] + coef[1] * th / prev) * prev)[test])
        r_dc = engine.census_window_rate(crates, Boss.NET_REPLACEMENT_WINDOW[0], O)
        preds['dwelling_count'] = (r_dc, (need + r_dc * prev)[test])
        # reference method (S3): the most recent intercensal rate before the origin,
        # fading to the long-run dwelling-count rate with a 10-year half-life from O
        r_last = float(crates[crates['y1'] <= O].iloc[-1]['rate'])
        path = pd.Series(engine.replacement_path('S3', r_dc, r_last, yh - O + 2025, 10.0), index=yh)
        preds['reference_s3_10'] = (r_last, (need + path * prev)[test])
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
        for m, r in (('long run', engine.census_window_rate(cr, Boss.NET_REPLACEMENT_WINDOW[0], O)),
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
    dq = Boss.load_historical_households(Boss.FILE_HOUSEHOLDS_HIST, sheet='Table 1').set_index('Date')['Households']
    years = [int(y) for y in B['census'].index if pd.Timestamp(int(y), 3, 31) in dq.index]
    stock = pd.Series({y: float(dq[pd.Timestamp(y, 3, 31)]) for y in years})
    cm = B['consents_monthly']
    r_dhe = engine.census_interval_rates(stock, cm, Boss.COMPLETION_RATE, B['lag_w'], day_of_year=90)
    w0, w1 = Boss.NET_REPLACEMENT_WINDOW
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
    m = (tm > frac(t0) - B['lag_w']) & (tm <= frac(t1) - B['lag_w'])
    built = Boss.COMPLETION_RATE * float(cm[m].sum())
    d_stock = float(dq[t1] - dq[t0])
    sy = float((dq[t0] + dq[t1]) / 2 * (frac(t1) - frac(t0)))
    out.update(dhe_post2023_period=f'{t0.date()}..{t1.date()}', dhe_post2023_rate=(built - d_stock) / sy)
    return out


def seasonal_shares(consents):
    return engine.seasonal_shares(consents, SEASONAL_YEARS)   # mean share of the year, by month


def check_2026(B, consents=None):
    """consents: monthly all-category series (index = month); read from the
    consent file when not given."""
    if consents is None:
        c = Boss.load_consents()
        consents = c.set_index(pd.to_datetime(c['Date']))[Boss.COL_DWELLINGS_TOTAL]
    s = consents.sort_index()
    last = s.index.max()
    E = B['engine_out']['50th']
    built_all_2026 = float(E['dwell_in_scope'][1] + E['rv_units'][1])
    # completions_2026 = c x [(1 - W) consents_2026 + W consents_2025]  ->  consents_2026
    W = B['lag_w']
    cons_2025 = float(B['hist_units_all'].loc[2025])
    model_consents_2026 = (built_all_2026 / Boss.COMPLETION_RATE - W * cons_2025) / (1.0 - W)
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
             f'(window {Boss.NET_REPLACEMENT_WINDOW[0]}-{Boss.NET_REPLACEMENT_WINDOW[1]}).', '',
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
                  f"- Census dwelling counts, {Boss.NET_REPLACEMENT_WINDOW[0]}-{Boss.NET_REPLACEMENT_WINDOW[1]}: "
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
    if chk['status'] == 'pending':
        lines.append(f"PENDING: the consent file ends {chk['data_end']}. Model 2026: "
                     f"{chk['model_built_all_2026']:,.0f} dwellings built (all categories) = "
                     f"{chk['model_consent_equivalent_2026']:,.0f} consent-equivalents.")
    else:
        lines.append(f"Months observed: {chk['months']}. Observed {chk['observed_ytd']:,.0f} vs model "
                     f"{chk['model_expected_ytd']:,.0f} (annual {chk['model_consent_equivalent_2026']:,.0f} x "
                     f"seasonal share {chk['seasonal_share']:.3f}); observed / model = "
                     f"{chk['ratio_observed_to_model']:.3f}. Latest 12 months ({chk['last12_months']}): "
                     f"{chk['observed_last12']:,.0f}. Descriptive only: not used to set any parameter.")
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(OUT_JSON, 'w') as f:
        json.dump(dict(hindcast=rows, hindcast_as_published=rows_pub, vacancy_definition=vac,
                       hindcast_stock=stock_rows, net_replacement_crosscheck=dhe,
                       model_method='dwelling_count', check_2026=chk), f, indent=2)
    print('\n'.join(lines))


def main():
    B = run_boss()
    uses_2026 = B['_join_mode'] == 'market_excess' or B['pop_nowcast'] is not None
    B0 = run_boss(**NO_2026_DATA) if uses_2026 else B
    chk = check_2026(B0)
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


if __name__ == '__main__':
    main()
