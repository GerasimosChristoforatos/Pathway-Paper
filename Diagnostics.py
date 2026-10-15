"""
DIAGNOSTICS -- sanity checks of projection.py, past and future together
======================================================================
Three diagnostics (outputs/diagnostics/calibration/, docs/FIGURE_PLAN_v3.md), read
from ONE run of projection.py, so the two scripts can never disagree:

  D04  household formation      people arriving vs household size changing
  D05  stock and vacancy        vacancy, stock, dwellings per year by component
  D06  vacancy definition       why empty homes only (appendix)

Projections are annual; the history of the stock identity (D05c) is one bar per census
interval, because between censuses households and vacancy are interpolated and annual
detail is not identified. The accounting identities are checked in
tests/test_identities.py. MODEL v3.0.0 (compute / draw separation): this script computes only and writes the
exact arrays of D04-D06 as figure source (figsource.write, outputs/data/figure_source/<id>.json);
figures/calibration.py draws them (python -m figures D04_household_formation ...).
"""

import importlib
import io
import contextlib

import numpy as np
import pandas as pd
from scipy import stats

import projection as M
import engine
import figsource
import naming as N
import validation
# Interactive consoles (Spyder, IPython, Jupyter) keep an imported module alive
# between runs, so an edited projection.py would otherwise be ignored. Always reload.
M = importlib.reload(M)


# ---------------------------------------------------------------------------
# One silent run of projection, with a version check
# ---------------------------------------------------------------------------
_PROJECTION_CACHE = None


def projection_state():
    """Run projection.main() silently once per run and return its internal variables."""
    global _PROJECTION_CACHE
    if _PROJECTION_CACHE is not None:
        return _PROJECTION_CACHE
    M.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        grab = M.main()
    if not isinstance(grab, dict):
        raise RuntimeError(f"{M.__file__}: main() returned no state; use the latest projection.py.")
    need = ('stock_fwd', 'stock_cal', 'census', 'unconsented_rate', 'flow_annual', 'hist_rv_units',
            'hh_response', 'fig_bands')
    miss = [k for k in need if k not in grab]
    miss += [f"results['{k}']" for k in ('vac', 'repl', 'unc', 'rv')
             if k not in grab.get('results', {}).get('50th', {})]
    if miss:
        raise RuntimeError(
            f"\nThe projection.py being run is OLDER than this Diagnostics.py.\n"
            f"  file used: {M.__file__}\n  missing:   {', '.join(miss)}\n"
            f"Use the latest projection.py. In Spyder, restart the kernel once.")
    _PROJECTION_CACHE = grab
    return grab


B = projection_state()

# ---------------------------------------------------------------------------
# Shared quantities
# ---------------------------------------------------------------------------
BF = M.COMPLETION_RATE                         # consents -> built (x the completion lag, see projection)
YH = np.arange(1992, 2026)                     # history with defined flows
FY = np.asarray(B['forecast_years'])
PF = FY[1:]                                    # projected years (2025 is the anchor)
M6 = 1e6
R = B['results']['50th']
SF = B['stock_fwd']['50th']
HR = B['hh_response']
DF = B['df_forecast']
E50 = B['engine_out']['50th']

pop_h, hh_h, S_h = B['hist_pop'], B['hist_hh'], B['hist_S']
D_f = B['future_dwelling_size'].values
S_f = DF['PopTotal_50th'].values / B['households_forecast']['50th']

# History of the stock identity on ONE vacancy definition throughout (the pooled
# 2018/2023 private empty share applied to every census, validation.consistent_share):
# the published empty / residents-away split breaks between 2013 and 2018 (N1).
POOLED_SHARE = validation.consistent_share(B)
SCc = engine.calibrate_stock(B['years_hist'], hh_h,
                             engine.vacancy_knots(B['census'], float(B['empty_share_measured']), POOLED_SHARE),
                             B['hist_units_all_c'], B['hist_rv_units_c'], M.COMPLETION_RATE, M.DEMOLITION_RATE,
                             M.DEMOLITION_CALIB_START, B['calib_end'])
CENSUS_Y = [int(y) for y in B['census'].index if YH[0] - 1 <= y <= int(B['calib_end'])]
INTERVALS = list(zip(CENSUS_Y[:-1], CENSUS_Y[1:])) + [(CENSUS_Y[-1], int(YH[-1]))]


# =============================================================================
# D04 -- household formation: people arriving vs household size changing
# =============================================================================
# a: change in household size against population growth (census-benchmarked years) and the later years
dP, dS = HR['dP_hist'], HR['dS_hist']
lr = stats.linregress(dP, dS)
late = [y for y in YH if y > HR['years_fit'][-1]]
dP_l, dS_l = pop_h.diff().loc[late], S_h.diff().loc[late]
# b: households per previous-year consent (all consents, retirement villages included)
cons_all = (B['hist_total_units'] + B['hist_rv_units']).shift(1)
ratio = (B['hist_hh_dhe'].diff() / cons_all).loc[YH]
BASES = [1991, 1996, 2001, 2006, 2013, 2018]
_r19 = ratio.loc[2019:]
R19 = (f'{_r19.min():.3f}–{_r19.max():.3f}' if _r19.max() - _r19.min() >= 5e-4 else f'flat at {_r19.iloc[0]:.3f}')
# c: history one column per census interval (validation.household_formation_history); projection annual
HFH = validation.household_formation_history(B)
pop_part_f = DF['PopGrowth_50th'].values[1:] / S_f[1:]
size_part_f = R['d_hh'][1:] - pop_part_f
figsource.write('D04_household_formation',
                years_fit=np.asarray(HR['years_fit'], int), dP_fit=np.asarray(dP, float), dS_fit=np.asarray(dS, float),
                fit=dict(slope=float(lr.slope), intercept=float(lr.intercept), r=float(lr.rvalue), p=float(lr.pvalue)),
                late_years=np.asarray(late, int), dP_late=dP_l, dS_late=dS_l,
                ratio_years=YH, households_per_consent=ratio, census_bases=BASES, R19=R19,
                formation_history=HFH, projection_years=PF, from_population_growth=np.asarray(pop_part_f, float),
                from_household_size_change=np.asarray(size_part_f, float),
                net_new_households=np.asarray(R['d_hh'][1:], float))

# =============================================================================
# D05 -- the stock: built (in scope) = households + vacancy + net replacement - retirement villages
# =============================================================================
cen = B['census']
SC = B['stock_cal']
knots = SC['knots']
_vc = SCc['knots']                                # census vacancy, one (consistent) definition
_v_imp = 1 - E50['hh'] / (E50['stock'] + E50['stock_join'])     # held rate + unabsorbed surplus / stock
meas = cen['empty'].notna()
KNOTS = pd.DataFrame({'vacancy': [float(v) for v in knots.values()],
                      'measured': [bool(meas.get(y, False)) for y in knots],
                      'all_unoccupied': [float(cen.loc[y, 'unoccupied'] / cen.loc[y, 'total_private']) for y in knots]},
                     index=[int(y) for y in knots])
# history: census-measured net replacement (the rate of D07 x the previous year's stock) and the
# building the components leave unexplained (validation.stock_identity_history; it may be negative)
SIH = validation.stock_identity_history(B)
# projection by component (MODEL v3.0.0 bands): the long-run net replacement split into demolition replacement
# (demolition rate x stock) and unconsented additions (calibrated rate x stock, negative); the surge above the
# long-run rate (redevelopment); the 2026 overbuild split into the market excess and the payback of its absorption
# (negative): join = excess - payback paid (engine.absorb_overbuild)
_wave_u = (np.asarray(B['rate_path'], float) - (B['demolition_rate'] + B['unconsented_rate'])) * E50['prev']
_ab = B['join_info']['50th'].get('absorption')
if _ab is None:
    _excess, _paid = np.asarray(SF['join'], float), np.zeros(len(FY))
else:
    _excess, _paid = np.asarray(_ab['excess'], float), np.asarray(_ab['paid'], float)
if not np.allclose(_excess - _paid, np.asarray(SF['join'], float), rtol=1e-12, atol=1e-6):
    raise SystemExit('D05: the market excess less the payback paid does not reproduce the stock join.')
_unc_u = np.asarray(SF['uncons'], float) - _wave_u
FUT_PARTS = {'new_households': np.asarray(R['d_hh'], float), 'vacancy': np.asarray(SF['allow'], float),
             'replacement': np.asarray(SF['demol'], float), 'unconsented': _unc_u, 'redevelopment': _wave_u,
             'retirement_villages': np.asarray(SF['rv'], float), 'overbuild_2026': _excess,
             'overbuild_absorbed': -_paid}
_old = (np.asarray(R['d_hh']) + np.asarray(SF['allow']) + np.asarray(SF['demol']) + np.asarray(SF['uncons'])
        + np.asarray(SF['rv']) + np.asarray(SF['join']))
if not np.allclose(sum(FUT_PARTS.values()), _old, rtol=1e-12, atol=1e-6):
    raise SystemExit('D05: the projected components do not add up to the stock identity.')
built_h = B['hist_built_units'].loc[YH]          # in-scope dwellings built (lagged completions)
built_f = R['total'][1:] / D_f[1:]
if max(_vc, key=_vc.get) != 2023:                 # the wording names 2023 as the series maximum
    raise SystemExit('D05: the consistent vacancy series no longer peaks in 2023; revise naming.VACANCY_WORDING.')
VACANCY = N.vacancy_wording(B['v_forward'], max(_vc.values()), min(_vc.values()), min(_vc, key=_vc.get), _v_imp[-1])
figsource.write('D05_stock_and_vacancy',
                forecast_years=FY, projection_years=PF, years_hist_flows=YH, S_ANCHOR_YEAR=int(M.S_ANCHOR_YEAR),
                hh_rebase_k=float(B['hh_rebase_k']), pooled_share=POOLED_SHARE, census_years=CENSUS_Y,
                vacancy_consistent_knots=pd.Series({int(k): float(v) for k, v in _vc.items()}),
                vacancy_published_model=SC['v'], vacancy_consistent_model=SCc['v'],
                vacancy_forward=float(B['v_forward']), vacancy_implied=np.asarray(_v_imp, float),
                census_knots=KNOTS, stock_hist=SC['stock'], households_hist=hh_h,
                stock_projection=np.asarray(SF['stock'] + SF['stock_join'], float),
                households_projection=np.asarray(B['households_forecast']['50th'], float),
                stock_identity_history=SIH,
                projection_components={k: v[1:] for k, v in FUT_PARTS.items()},
                dwellings_built_hist=built_h, dwellings_built_projection=np.asarray(built_f, float),
                vacancy_wording=VACANCY)

# =============================================================================
# D06 (appendix) -- which vacancy definition is plausible
# =============================================================================
cen_all = (cen['unoccupied'] / cen['total_private']).to_dict()
v_all = pd.Series(np.interp(B['years_hist'].astype(float), list(cen_all), list(cen_all.values())),
                  index=B['years_hist'])
prev_all = (hh_h / (1 - v_all)).shift(1)
net_all = (BF * B['hist_units_all_c'] - B['d_hh'] - B['d_hh'] * v_all / (1 - v_all)
           - hh_h.shift(1) * (1 / (1 - v_all)).diff())
YC = np.arange(1992, B['calib_end'] + 1)            # census-benchmarked calibration window
unc_all = (net_all - B['demolition_rate'] * prev_all).loc[YC].mean()
unc_emp = SC['uncons'].loc[YC].mean()
nb = built_h.mean()
figsource.write('D06_vacancy_definition', calib_end=int(B['calib_end']), unconsented_empty_only=float(unc_emp),
                unconsented_including_away=float(unc_all), mean_dwellings_built=float(nb))

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
print("=" * 70)
print(f" Built floor area 2026-2050: {R['total'][1:].sum() / M6:.2f} million m2")
print(f" Embodied carbon  2026-2050: {B['carbon_total'].iloc[1:].sum() / M6:,.1f} kt CO2e")
print(f" Household size 2050: {S_f[-1]:.3f} | vacancy {100 * B['v_forward']:.2f}% | "
      f"net replacement (long run) {100 * (B['demolition_rate'] + B['unconsented_rate']):.3f}%")
print(f" History bars: census intervals {', '.join(f'{a}-{b}' for a, b in INTERVALS)}; "
      f"pooled empty share {100 * POOLED_SHARE:.1f}%")
print(f" Vacancy: {VACANCY}")
print("=" * 70)
print("Wrote the figure source of D04-D06 (outputs/data/figure_source/; drawn by figures/calibration.py).")
