"""MODEL v4.2 Part A (diagnostic; no adopted change): the history -> projection transition.

    python tools/transition_audit.py     # light profile, deterministic Reference runs only

A1  outputs/diagnostics/transition/audit.csv: 2016-2030 annual (and the census-interval history bands): population,
    growth, household size S, households, change in households split into population growth (dP / S_(t-1)) and
    household-size change (the rest), stock, vacancy, net replacement, the demand bands (dwellings, all categories; floor
    area in scope, Mm2), building, need and residual (building - need), each input flagged observed / consent-derived
    / projected. D45 (bands 2016-2030 on one annual axis).
A5  runs.csv: the 8 combinations HH_BRIDGE (dhe, erp_S) x START_MODE (observed, projection) x HH_SIZE_PATH
    (statsnz_2018, census_pace): building, need, residual 2024-2030; the 2026-27 residual against the observed pipeline;
    the market excess 2026-2050; Reference carbon and cumulative LoE AR (B_AR(t) is proportional to P_NZ(t), aesa.
    boundary_ar, so a run's budget is the Reference budget x its population path / the Reference path, exactly).
    history_residual.csv: the historical residual distribution (per year, dwellings and % of building, against the
    census-interval rate; per census interval, the unexplained floor-area band and % of building).

Definitions (dwellings, all categories, the model's own unit):
  building  history: completion rate x consents lagged (observed); projection: engine.requirement(E) (incl. the join)
  need      households change / (1 - v) + vacancy allowance and change + net replacement at the model's rate
            (history: the rate of the census interval containing the year; 2024-25: the Reference's 2025 rate);
            projection: the requirement without the join
  residual  building - need (projection: the join, i.e. market excess net of payback)."""
import itertools
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import engine  # noqa: E402
import layout  # noqa: E402
import validation  # noqa: E402

OUT = os.path.join(layout.OUT, 'diagnostics', 'transition')
YEARS = (2016, 2030)
COMBOS = list(itertools.product(('dhe', 'erp_S'), ('observed', 'projection'), ('statsnz_2018', 'census_pace')))


def _rate_for_year(cr, y, rate_2025):
    for _, r in cr.iterrows():
        if r['y0'] < y <= r['y1']:
            return float(r['rate'])
    return rate_2025


def annual(B, settings):
    """Rows 2016-2030 of one projection state."""
    cal, cr = B['stock_cal'], B['census_rates']
    c = float(cal['completion'])
    E = B['engine_out']['50th']
    fy = list(B['forecast_years'])
    fi = B['fwd_inputs']
    rate_2025 = float(B['demolition_rate']) + float(np.asarray(fi['rate_unc'])[0])
    pipe = B['pipe'] or {}
    built_all = c * B['hist_units_all']                      # consents lagged (df_lag), all categories
    hist_m2 = B['hist_built_gfa']
    rows = []
    for y in range(YEARS[0], YEARS[1] + 1):
        if y <= 2025:
            P, P0 = float(B['hist_pop'].loc[y]), float(B['hist_pop'].loc[y - 1])
            H, H0 = float(B['hist_hh'].loc[y]), float(B['hist_hh'].loc[y - 1])
            S0 = P0 / H0
            b = float(built_all.loc[y])
            d_h = b - float(cal['beyond'].loc[y])
            allow, change = float(cal['allow'].loc[y]), float(cal['change'].loc[y])
            net, prev = float(cal['net'].loc[y]), float(cal['prev'].loc[y])
            rep = _rate_for_year(cr, y, rate_2025) * prev
            need = d_h + allow + change + rep
            hh_src = ('census-benchmarked (DHE between censuses)' if y <= 2023 else
                      ('ERP / model S (2023 census anchor)' if settings['HH_BRIDGE'] == 'erp_S'
                       else 'DHE (consent-derived after the 2023 census)'))
            m2 = float(hist_m2.loc[y]) / 1e6
            row = dict(year=y, phase='history', population=P, population_growth=P - P0, S=P / H, households=H,
                       d_households=H - H0, d_hh_from_population=(P - P0) / S0, stock=float(cal['stock'].loc[y]),
                       vacancy=float(np.asarray(cal['v'].loc[y])), net_replacement_observed=net,
                       net_replacement_model=rep, band_households=d_h, band_vacancy=allow + change,
                       band_replacement=rep, building=b, need=need, residual=b - need, floor_area_Mm2=m2,
                       population_src='observed (ERP 31 Dec)', households_src=hh_src,
                       building_src='consent-derived (consents lagged, x completion rate)')
        else:
            i = fy.index(y)
            P, P0 = float(E['pop'][i]), float(E['pop'][i - 1])
            H, H0 = float(E['hh'][i]), float(E['hh'][i - 1])
            req = np.asarray(engine.requirement(E), float)
            b = float(req[i])
            join = float(np.asarray(E['join'])[i])
            v = float(np.broadcast_to(np.asarray(E['v'], float), (len(fy),))[i])
            rep = float(E['demol'][i] + E['unc'][i])
            obs = y in pipe.get('years', [])
            pop_src = ('observed nowcast (June qtr 2026) + projection growth' if B['pop_nowcast'] is not None
                       else 'projected (Stats NZ median)')
            row = dict(year=y, phase='projection', population=P, population_growth=P - P0, S=P / H, households=H,
                       d_households=H - H0, d_hh_from_population=(P - P0) / (P0 / H0), stock=float(E['stock'][i]),
                       vacancy=v, net_replacement_observed=np.nan, net_replacement_model=rep,
                       band_households=float(E['d_hh'][i]), band_vacancy=float(E['allow'][i] + E['change'][i]),
                       band_replacement=rep, building=b, need=b - join, residual=join,
                       floor_area_Mm2=float(E['total'][i]) / 1e6, population_src=pop_src,
                       households_src='projected (population / S path)',
                       building_src=('consent-derived (pipeline)' if obs else 'modelled'))
        row['d_hh_from_S'] = row['d_households'] - row['d_hh_from_population']
        row['residual_pct_of_building'] = 100 * row['residual'] / row['building']
        rows.append(dict(row, **settings))
    return rows


def history_residual(B):
    cal, cr = B['stock_cal'], B['census_rates']
    c = float(cal['completion'])
    yr = [y for y in B['years_hist'] if 1992 <= y <= 2023]
    b = c * B['hist_units_all']
    out = [dict(kind='year', period=str(y), residual=float(cal['net'].loc[y]) - _rate_for_year(cr, y, 0.0)
                * float(cal['prev'].loc[y]), building=float(b.loc[y])) for y in yr]
    h = pd.read_csv(layout.data('baseline/bands_history.csv', frozen=False))
    un = h[h['band'].str.contains('nexplained')]
    for _, r in un.iterrows():
        out.append(dict(kind='census_interval_floor_area', period=r['interval'], residual=r['floor_area_Mm2_per_year'],
                        building=r['observed_built_Mm2_per_year']))
    d = pd.DataFrame(out)
    d['pct_of_building'] = 100 * d['residual'] / d['building']
    return d


def run_summary(B, settings, b_ar_ref, p_ref):
    E = B['engine_out']['50th']
    fy = list(B['forecast_years'])
    req = np.asarray(engine.requirement(E), float)
    join = np.asarray(E['join'], float)
    ji = (B['join_info'] or {}).get('50th')
    pipe_obs = {}
    for y in (2026, 2027):        # observed pipeline building at the adopted lag (independent of the start mode)
        pipe_obs[y] = float(OBS_PIPE[y])
    i26, i27 = fy.index(2026), fy.index(2027)
    need = req - join
    carbon = float(B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6)
    p = np.asarray(E['pop'], float)[1:]
    loe = carbon / (float(np.sum(b_ar_ref * p / p_ref)) / 1e6)
    r = dict(settings, carbon_kt=carbon, LoE_AR=loe,
             market_excess_2026_2050=float(np.sum(ji['excess'][1:])) if ji else 0.0,
             need_2026=need[i26], need_2027=need[i27], building_2026=req[i26], building_2027=req[i27],
             residual_2026=join[i26], residual_2027=join[i27],
             pipeline_minus_need_2026=pipe_obs[2026] - need[i26], pipeline_minus_need_2027=pipe_obs[2027] - need[i27])
    r['residual_2026_27_pct'] = 100 * (r['residual_2026'] + r['residual_2027']) / (req[i26] + req[i27])
    r['pipeline_minus_need_2026_27_pct'] = 100 * (r['pipeline_minus_need_2026'] + r['pipeline_minus_need_2027']) / (
        pipe_obs[2026] + pipe_obs[2027])
    return r


def d45(audit):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from figures import style as S
    a = audit[(audit['HH_BRIDGE'] == 'dhe') & (audit['START_MODE'] == 'observed')
              & (audit['HH_SIZE_PATH'] == 'statsnz_2018')].sort_values('year')
    x = a['year'].values
    fig, ax = plt.subplots(figsize=S.figsize('double', 80))
    parts = [('band_households', 'Households (new)', S.BAND['growth'][0]),
             ('band_vacancy', 'Vacancy (allowance + change)', S.BAND['vacancy'][0]),
             ('band_replacement', 'Net replacement (model rate)', S.BAND['replacement'][0]),
             ('residual', 'Residual (building - need)', S.BAND['overbuild_2026'][0])]
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for col, lab, colr in parts:
        v = a[col].values / 1e3
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        ax.bar(x, pos, bottom=up, width=0.8, color=colr, label=lab)
        ax.bar(x, neg, bottom=dn, width=0.8, color=colr)
        up, dn = up + pos, dn + neg
    ax.plot(x, a['building'] / 1e3, 'o-', color=S.INK, lw=S.LW, ms=3, label='Building (all categories)')
    for xv, txt in ((2023.5, '2023 census'), (2025.5, 'history | projection'), (2027.5, 'pipeline end')):
        ax.axvline(xv, color=S.MUTED, lw=S.LW_THIN, ls=':')
        ax.text(xv, 0.98, ' ' + txt, transform=ax.get_xaxis_transform(), fontsize=S.FONT_MIN, color=S.MUTED, va='top')
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_ylabel('Dwellings per year (thousand)')
    ax.set_xticks(x)
    ax.tick_params(axis='x', labelsize=S.FONT_MIN)
    ax.legend(fontsize=S.FONT_MIN, loc='upper left', ncol=2, bbox_to_anchor=(0, 0.92))
    fig.tight_layout()
    path = os.path.join(OUT, 'D45_transition_bands')
    S.save(fig, path)
    plt.close(fig)
    return path + '.png'


OBS_PIPE = {}


def main():
    os.makedirs(OUT, exist_ok=True)
    B0 = validation.run_boss()
    OBS_PIPE.update(B0['pipe']['built_all'])
    a = pd.read_csv(layout.data('aesa/annual.csv', frozen=False))
    a = a[(a['scenario'] == 'REF') & (a['year'] >= 2026)].sort_values('year')
    b_ar_ref, p_ref = a['B_AR_kgCO2e'].to_numpy(float), a['P_NZ'].to_numpy(float)
    audit, runs = [], []
    for hb, sm, hp in COMBOS:
        st = dict(HH_BRIDGE=hb, START_MODE=sm, HH_SIZE_PATH=hp)
        B = validation.run_boss(**st)
        audit += annual(B, st)
        runs.append(run_summary(B, st, b_ar_ref, p_ref))
    audit = pd.DataFrame(audit)
    audit.to_csv(os.path.join(OUT, 'audit.csv'), index=False)
    h = pd.read_csv(layout.data('baseline/bands_history.csv', frozen=False))
    h.assign(phase='census_interval').to_csv(os.path.join(OUT, 'audit_census_intervals.csv'), index=False)
    pd.DataFrame(runs).to_csv(os.path.join(OUT, 'runs.csv'), index=False)
    history_residual(B0).to_csv(os.path.join(OUT, 'history_residual.csv'), index=False)
    print(d45(audit))


if __name__ == '__main__':
    main()
