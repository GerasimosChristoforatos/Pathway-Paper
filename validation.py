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


def run_boss():
    Boss.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        return Boss.main()


def census_intervals(B, last):
    cy = [int(y) for y in B['census'].index if B['years_hist'].min() <= y <= last]
    return [(a + 1, b) for a, b in zip(cy[:-1], cy[1:])]      # calendar years a+1..b


def hindcast(B):
    yh = B['years_hist']
    end = int(B['calib_end'])
    units_all = B['hist_units_all_c']                 # consents timed as completions
    c = Boss.COMPLETION_RATE
    cal_full = engine.calibrate_stock(yh, B['hist_hh'], engine.vacancy_knots(B['census'], B['empty_share_measured']),
                                      units_all, B['hist_rv_units_c'], c, Boss.DEMOLITION_RATE,
                                      Boss.DEMOLITION_CALIB_START, end)
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
        preds['constant'] = (r_const, float((need + r_const * prev)[test].sum()))
        before = [iv for iv in ivs if iv[1] <= O]
        r_recent = rate(*before[-1])
        preds['recent'] = (r_recent, float((need + r_recent * prev)[test].sum()))
        X = np.array([th.loc[a:b].sum() / prev.loc[a:b].sum() for a, b in before])
        Y = np.array([rate(a, b) for a, b in before])
        A = np.c_[np.ones(len(X)), X]
        coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
        preds['linked'] = (None, float((need + (coef[0] + coef[1] * th / prev) * prev)[test].sum()))
        for m, (r, p) in preds.items():
            rows.append(dict(origin=O, test=f'{O + 1}-{end}', method=m,
                             rate_pct=None if r is None else 100 * r,
                             n_intervals=len(before) if m == 'linked' else None,
                             linked_b=float(coef[1]) if m == 'linked' else None,
                             predicted=p, actual=actual, error_pct=100 * (p / actual - 1)))
    return rows


def seasonal_shares(consents):
    m = consents.loc[f'{SEASONAL_YEARS[0]}-01-01':f'{SEASONAL_YEARS[1]}-12-31']
    by = m.groupby([m.index.year, m.index.month]).sum().unstack()
    return (by.div(by.sum(axis=1), axis=0)).mean()          # mean share of the year, by month


def check_2026(B, consents=None):
    """consents: monthly all-category series (index = month); read from the
    consent file when not given."""
    if consents is None:
        c = Boss.load_consents(Boss.CONSENT_SOURCE)
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


def write(rows, chk):
    lines = ['### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)', '',
             'Actual households and vacancy fed in; only the net-replacement term is predicted. '
             'Error = predicted / actual - 1.', '',
             '| origin | test years | method | rate used (%/yr) | predicted | actual | error |',
             '|---|---|---|---|---|---|---|']
    for r in rows:
        rate = (f"{r['rate_pct']:+.3f}" if r['rate_pct'] is not None
                else f"linked: b = {r['linked_b']:.2f} on {r['n_intervals']} intervals")
        lines.append(f"| {r['origin']} | {r['test']} | {r['method']} | {rate} | {r['predicted']:,.0f} | "
                     f"{r['actual']:,.0f} | {r['error_pct']:+.1f}% |")
    lines += ['', '### 2026 out-of-sample check against observed consents', '']
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
        json.dump(dict(hindcast=rows, check_2026=chk), f, indent=2)
    print('\n'.join(lines))


def main():
    B = run_boss()
    write(hindcast(B), check_2026(B))


if __name__ == '__main__':
    main()
