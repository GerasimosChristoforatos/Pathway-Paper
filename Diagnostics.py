"""
DIAGNOSTICS -- sanity checks of projection.py, past and future together
======================================================================
Three diagnostics (outputs/diagnostics/data_calibration/, docs/FIGURE_PLAN.md), read
from ONE run of projection.py, so the two scripts can never disagree:

  D04  household formation      people arriving vs household size changing
  D05  stock and vacancy        vacancy, stock, dwellings per year by component
  D06  vacancy definition       why empty homes only (appendix)

Projections are annual; the history of the stock identity (D05c) is one bar per census
interval, because between censuses households and vacancy are interpolated and annual
detail is not identified. The accounting identities are checked in
tests/test_identities.py. Figures are drawn on screen (Spyder) and saved only when
run_all.py sets PATHWAY_SAVE_FIGURES=1.
"""

import importlib
import io
import os
import contextlib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

import projection as M
import engine
import naming as N
import plotting as P
import style as S
import validation
# Interactive consoles (Spyder, IPython, Jupyter) keep an imported module alive
# between runs, so an edited projection.py would otherwise be ignored. Always reload.
M = importlib.reload(M)

SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'   # run_all.py sets this
S.apply()


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

# components of the stock identity: (label, colour, hatch), labels in the release vocabulary
RV = ('#BDBDBD', 'xxxx')                       # retirement villages: out of scope, grey cross-hatch
UNEXPLAINED = S.UNEXPLAINED                    # unexplained building: neutral, hatched (face, hatch, hatch colour)
COMP = {'new_households': ('New households', '#9E9E9E', None),
        'vacancy': ('Vacancy (allowance and change)',) + S.BAND['vacancy'],
        'replacement': (N.BANDS['replacement'],) + S.BAND['replacement'],
        'redevelopment': (N.BANDS['redevelopment'],) + S.BAND['redevelopment'],
        'retirement_villages': (N.BAND_DETAIL['retirement_villages'],) + RV,
        'overbuild_2026': (N.BANDS['overbuild_2026'],) + S.BAND['overbuild_2026'],
        # history only (D05c): census-measured net replacement, and what the components leave unexplained
        'net_replacement_census': ('Net replacement, history (census dwelling counts; parts not separable)',) + S.BAND['replacement'],
        'unexplained_building': ('Unexplained building', UNEXPLAINED[0], UNEXPLAINED[1])}
EDGE = {'unexplained_building': UNEXPLAINED[2], **S.BAND_HATCHCOLOR}    # hatch colours (style.fill)

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
HIST_NOTE = (f'History: one bar per census interval (interval means; vacancy on one definition, the pooled '
             f'2018/2023 empty share, {100 * POOLED_SHARE:.1f}% of unoccupied dwellings); between censuses annual '
             f'detail is not identified. Faint bar: {CENSUS_Y[-1] + 1}–{YH[-1]}, households consent-derived. '
             f'Projection annual, lighter.')


def bars(ax, years, parts, projected=False):
    """Signed stacked bars, positive parts up and negative parts down from zero.
    parts: [(component id, values)]; projected years lighter."""
    up = np.zeros(len(years))
    dn = np.zeros(len(years))
    for cid, vals in parts:
        _, colour, hatch = COMP[cid]
        v = np.asarray(vals, dtype=float)
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        kw = dict(S.fill(colour, hatch, EDGE.get(cid), 0.55 if projected else 1.0), width=0.82)
        ax.bar(years, pos, bottom=up, **kw)
        ax.bar(years, neg, bottom=dn, **kw)
        up += pos
        dn += neg
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)


def interval_bars(ax, groups, scale=1.0):
    """One stacked bar per census interval, spanning its years (signed: a negative mean is drawn
    below zero). The interval after the latest census is faint."""
    for y0, y1, parts in groups:
        up = dn = 0.0
        faint = y0 == CENSUS_Y[-1]
        for cid, m in parts:
            _, colour, hatch = COMP[cid]
            m = m / scale
            kw = dict(S.fill(colour, hatch, EDGE.get(cid), 0.4 if faint else 1.0), width=y1 - y0, align='edge')
            if m >= 0:
                ax.bar(y0 + 0.5, m, bottom=up, **kw)
                up += m
            else:
                ax.bar(y0 + 0.5, m, bottom=dn, **kw)
                dn += m
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)


def comp_handles(ids):
    return [Patch(label=COMP[c][0], **dict(S.fill(COMP[c][1], COMP[c][2], EDGE.get(c)), edgecolor='#555555',
                                           linewidth=S.LW_THIN)) for c in ids]


def finish(fig, fid, note=None):
    if SAVE_FIGURES:
        S.save_figure(fig, fid, note=note)


# =============================================================================
# D04 -- household formation: people arriving vs household size changing
# =============================================================================
fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 72), gridspec_kw={'width_ratios': [1, 1, 1.5]})

a = ax[0]
dP, dS = HR['dP_hist'], HR['dS_hist']
lr = stats.linregress(dP, dS)
a.scatter(dP / 1e3, dS, color=S.MUTED, s=10, zorder=3,
          label=f"{HR['years_fit'][0]}–{HR['years_fit'][-1]} (census-benchmarked)")
xx = np.linspace(dP.min(), dP.max(), 50)
a.plot(xx / 1e3, lr.intercept + lr.slope * xx, color=S.INK, lw=S.LW,
       label=f'r = {lr.rvalue:+.2f}, p = {lr.pvalue:.0e}')
late = [y for y in YH if y > HR['years_fit'][-1]]
dP_l, dS_l = pop_h.diff().loc[late], S_h.diff().loc[late]
a.scatter(dP_l / 1e3, dS_l, facecolor='none', edgecolor=S.ACCENT_ORANGE, s=22, zorder=4, lw=S.LW_THIN,
          label=f'{late[0]}–{late[-1] % 100:02d}: consent-derived, no census check')
for y in (2024, 2025):                          # label the left point to the left, the right one to the right
    left = dP_l[y] <= dP_l[[2024, 2025]].min()
    a.annotate(str(y), (dP_l[y] / 1e3, dS_l[y]), xytext=(-4 if left else 4, 4), textcoords='offset points',
               ha='right' if left else 'left', fontsize=S.FONT_MIN, color=S.ACCENT_ORANGE)
a.axhline(0, color=S.INK, lw=S.LW_THIN)
a.set_xlabel('Population growth (thousand per year)')
a.set_ylabel('Change in household size (persons per household)')
a.legend(loc='upper left', fontsize=S.FONT_MIN)
P.panel(a, 'a', 'Household size vs arrivals')

a = ax[1]
cons_all = (B['hist_total_units'] + B['hist_rv_units']).shift(1)
ratio = (B['hist_hh_dhe'].diff() / cons_all).loc[YH]
bases = [1991, 1996, 2001, 2006, 2013, 2018]
a.bar(YH, ratio, color=[S.ACCENT_ORANGE if y > 2018 else S.MUTED for y in YH], width=0.8)
for y in bases:
    a.axvline(y + 0.5, color=S.INK, lw=S.LW_THIN, ls=':')
_r19 = ratio.loc[2019:]
a.set_ylabel('Households per consent')
a.set_xlim(1991, 2026)
a.set_ylim(0, 1.45)
P.panel(a, 'b', 'Household growth per consent')
a.legend(handles=[Patch(color=S.MUTED, label='census-benchmarked'),
                  Patch(color=S.ACCENT_ORANGE, label='2019 on: consent-derived')], loc='upper left', ncol=2,
         fontsize=S.FONT_MIN)
R19 = (f'{_r19.min():.3f}–{_r19.max():.3f}' if _r19.max() - _r19.min() >= 5e-4 else f'flat at {_r19.iloc[0]:.3f}')

a = ax[2]
# history: one column per census interval (interval means; households census-anchored at both ends),
# 2024-25 hatched (consent-derived estimates, no census check); projection annual, lighter
HFH = validation.household_formation_history(B)
for r in HFH.itertuples():
    y0, y1 = int(r.interval[:4]), int(r.year_end)
    est = r.households_from != 'census'
    up = dn = 0.0
    for bid, m in (('growth', r.from_population_growth_per_year), ('smaller_households',
                                                                    r.from_household_size_change_per_year)):
        m = m / 1e3
        st = dict(P.band_style(bid), width=y1 - y0, align='edge')
        if est:
            st.update(hatch='////', alpha=0.5)
        if m >= 0:
            a.bar(y0 + 0.5, m, bottom=up, **st)
            up += m
        else:
            a.bar(y0 + 0.5, m, bottom=dn, **st)
            dn += m
    a.hlines(r.net_new_households_per_year / 1e3, y0 + 0.5, y1 + 0.5, color=S.INK, lw=S.LW,
             ls=':' if est else '-', label='Net new households' if y0 == int(HFH['interval'].iloc[0][:4]) else None)
pop_part_f = DF['PopGrowth_50th'].values[1:] / S_f[1:]
size_part_f = R['d_hh'][1:] - pop_part_f
up, dn = np.zeros(len(PF)), np.zeros(len(PF))
for bid, v in zip(('growth', 'smaller_households'), (pop_part_f, size_part_f)):
    v = np.asarray(v, float) / 1e3
    st = dict(P.band_style(bid), alpha=0.55, linewidth=0)   # many thin bars: no outline
    pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
    a.bar(PF, pos, bottom=up, width=0.82, **st)
    a.bar(PF, neg, bottom=dn, width=0.82, **st)
    up, dn = up + pos, dn + neg
a.axhline(0, color=S.INK, lw=S.LW_THIN)
a.plot(PF, R['d_hh'][1:] / 1e3, color=S.INK, lw=S.LW, ls='--')
P.split(a)
a.set_xlim(1991, 2050)
a.set_ylabel('Households (thousand per year)')
a.legend(handles=[Patch(label='From population growth', **dict(P.band_style('growth'), edgecolor='#555555')),
                  Patch(label='From household-size change', **dict(P.band_style('smaller_households'),
                                                                     edgecolor='#555555')),
                  Patch(facecolor='white', edgecolor='#555555', hatch='////',
                        label=f"{HFH['year_start'].iloc[-1]}–{HFH['year_end'].iloc[-1] % 100:02d}: consent-derived "
                              'estimates, no census check')]
         + a.get_legend_handles_labels()[0], loc='upper left', fontsize=S.FONT_MIN)
_y0, _y1 = a.get_ylim()
a.set_ylim(_y0, _y1 + 0.42 * (_y1 - _y0))            # room for the legend above the columns
P.panel(a, 'c', 'New households per year, by source')
fig.tight_layout()
finish(fig, 'D04_household_formation',
       'Between censuses households are consent-derived, so the relationship in a is partly mechanical (housing '
       f'supply meets migration). b: households per previous-year consent vary before 2019 and are {R19} from 2019: '
       'these years are estimated from consents and are not independent evidence. c: history one column per census '
       'interval (interval means; households census-anchored at both ends), stacked from population growth and from '
       f"household-size change; {HFH['year_start'].iloc[-1]}–{HFH['year_end'].iloc[-1]} hatched (consent-derived "
       'estimates, no census check); projection annual and lighter, from 2026; the line is the net of the two parts.')

# =============================================================================
# D05 -- the stock: built (in scope) = households + vacancy + net replacement - retirement villages
# =============================================================================
fig = plt.figure(figsize=S.figsize('double', 175))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.1], hspace=0.62, wspace=0.22)

cen = B['census']
SC = B['stock_cal']
knots = SC['knots']
a = fig.add_subplot(gs[0, 0])
_vc = SCc['knots']                                # census vacancy, one (consistent) definition
a.axhspan(100 * min(_vc.values()), 100 * max(_vc.values()), color=S.BAND['vacancy'][0], alpha=0.12, lw=0,
          label=f'Census {min(_vc)}–{max(_vc)} range, one definition '
                f'({100 * min(_vc.values()):.1f}–{100 * max(_vc.values()):.1f}%)')
a.axvspan(2013, 2018, color=S.MUTED, alpha=0.10, lw=0, label='2013 → 2018 empty / away definition break')
a.plot(SC['v'].index, 100 * SC['v'], color=S.INK, lw=S.LW, label='Published empty share (model)')
a.plot(SCc['v'].index, 100 * SCc['v'], color=S.BAND['vacancy'][0], lw=S.LW, ls='-.',
       label='One definition: pooled 2018/2023 empty share')
_v_imp = 1 - E50['hh'] / (E50['stock'] + E50['stock_join'])     # held rate + unabsorbed surplus / stock
a.plot(FY, np.full(len(FY), 100 * B['v_forward']), color=S.INK, lw=S.LW_THIN, ls=':',
       label=f"Held at its published 2023 census value ({100 * B['v_forward']:.2f}%)")
a.plot(FY, 100 * _v_imp, color=S.INK, lw=S.LW, ls='--',
       label='Implied: held rate + unabsorbed 2026 overbuild / stock')
meas = cen['empty'].notna()
for y, v in knots.items():
    filled = bool(meas.get(y, False))
    a.scatter(y, 100 * v, s=12, zorder=5, color=S.ACCENT_ORANGE if filled else 'white', edgecolor=S.ACCENT_ORANGE, lw=S.LW_THIN)
    a.scatter(y, 100 * cen.loc[y, 'unoccupied'] / cen.loc[y, 'total_private'], marker='x', color=S.MUTED, s=12,
              lw=S.LW_THIN)
a.scatter([], [], color=S.ACCENT_ORANGE, s=12, label='Census empty (published)')
a.scatter([], [], color='white', edgecolor=S.ACCENT_ORANGE, s=12, label='Census empty (2013 split applied)')
a.scatter([], [], marker='x', color=S.MUTED, s=12, label='All unoccupied (rejected)')
P.split(a)
a.set_xlim(1985, 2050)
a.set_ylim(0, None)
a.set_ylabel('Vacancy rate (% of private dwellings)')
a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, ncol=2)
P.panel(a, 'a', 'Vacancy: empty homes only')

a = fig.add_subplot(gs[0, 1])
a.plot(SC['stock'].index, SC['stock'] / M6, color=S.INK, lw=S.LW, label='Dwelling stock')
P.history_estimated(a, hh_h, M.S_ANCHOR_YEAR, M6, color=S.ACCENT_ORANGE, label='Households', k=B['hh_rebase_k'])
a.plot(FY, (SF['stock'] + SF['stock_join']) / M6, color=S.INK, lw=S.LW, ls='--',
       label='Stock, projection (incl. the unabsorbed 2026 overbuild)')
a.plot(FY, B['households_forecast']['50th'] / M6, color=S.ACCENT_ORANGE, lw=S.LW, ls='--', label='Households, projection')
P.split(a)
a.set_xlim(1991, 2050)
a.set_ylabel('Dwellings or households (million)')
a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, ncol=1)
P.panel(a, 'b', 'Stock = households / (1 − vacancy) + 2026 overbuild')

a = fig.add_subplot(gs[1, :])
# history: census-measured net replacement (the rate of D07 x the previous year's stock) and the
# building the components leave unexplained (validation.stock_identity_history; it may be negative)
SIH = validation.stock_identity_history(B)
HIST_IDS = ('new_households', 'vacancy', 'net_replacement_census', 'retirement_villages', 'unexplained_building')
interval_bars(a, [(int(r.interval[:4]), int(r.year_end), [(c, getattr(r, f'{c}_per_year')) for c in HIST_IDS])
                  for r in SIH.itertuples()], 1e3)
_wave_u = (np.asarray(B['rate_path'], float) - (B['demolition_rate'] + B['unconsented_rate'])) * E50['prev']
fut_parts = [('new_households', R['d_hh'][1:]), ('vacancy', SF['allow'][1:]),
             ('replacement', (SF['demol'] + SF['uncons'] - _wave_u)[1:]), ('redevelopment', _wave_u[1:]),
             ('retirement_villages', SF['rv'][1:]), ('overbuild_2026', SF['join'][1:])]
bars(a, PF, [(c, np.asarray(v) / 1e3) for c, v in fut_parts], projected=True)
# the per-interval "building beyond household formation" annotation of model-v1.0.0 is not drawn:
# its parts (vacancy change, replacement above the long-run rate) are now drawn as bands, and what
# the components leave over is the unexplained band
for r in SIH.itertuples():                          # the unexplained building of each interval, labelled at
    m = r.unexplained_building_per_year / 1e3       # the end of the stack it extends (top if positive)
    vals = [getattr(r, f'{c}_per_year') / 1e3 for c in HIST_IDS]
    y = sum(v for v in vals if v > 0) if m >= 0 else sum(v for v in vals if v < 0)
    a.annotate(f'unexpl. {m:+.1f}k', ((int(r.interval[:4]) + int(r.year_end)) / 2 + 0.5, y),
               xytext=(0, 2 if m >= 0 else -2), textcoords='offset points', ha='center',
               va='bottom' if m >= 0 else 'top', fontsize=S.FONT_MIN, color='#595959', zorder=7)
a.text(1991.6, 0.02, '1986–91 not covered (calibration starts 1991)', transform=a.get_xaxis_transform(),
       fontsize=S.FONT_MIN, color=S.MUTED)
built_h = B['hist_built_units'].loc[YH]          # in-scope dwellings built (lagged completions)
built_f = R['total'][1:] / D_f[1:]
a.plot(YH, built_h / 1e3, color=S.INK, lw=S.LW, label='Dwellings built, in scope (observed, annual)')
a.plot(PF, built_f / 1e3, color=S.INK, lw=S.LW, ls='--', label='Dwellings built, in scope (projection)')
P.split(a)
a.set_xlim(1991, 2050)
a.set_ylabel('Dwellings (thousand per year)')
_y0, _y1 = a.get_ylim()
a.set_ylim(_y0 - 0.06 * (_y1 - _y0), _y1)          # room for the labels of the negative interval means
P.panel(a, 'c', 'Dwellings per year by component')
a.legend(handles=comp_handles(['new_households', 'vacancy', 'net_replacement_census', 'replacement', 'redevelopment',
                               'retirement_villages', 'overbuild_2026', 'unexplained_building'])
         + a.get_legend_handles_labels()[0],
         loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=3, fontsize=S.FONT_MIN)
if max(_vc, key=_vc.get) != 2023:                 # the wording names 2023 as the series maximum
    raise SystemExit('D05: the consistent vacancy series no longer peaks in 2023; revise naming.VACANCY_WORDING.')
VACANCY = N.vacancy_wording(B['v_forward'], max(_vc.values()), min(_vc.values()), min(_vc, key=_vc.get), _v_imp[-1])
finish(fig, 'D05_stock_and_vacancy',
       f'a: {VACANCY[0].upper() + VACANCY[1:]}. c: {HIST_NOTE} History: net replacement is census-measured, the '
       'rate of the census dwelling-count identity of each interval (D07; under-construction corrected) x the '
       f'previous year\'s stock, the quantity the model uses ({CENSUS_Y[-1] + 1}–{YH[-1]}: the latest rate carried). '
       'Unexplained building (hatched grey, labelled per interval in thousand dwellings per year): building not '
       'explained by household formation, vacancy and census-measured replacement: redevelopment not captured by '
       'the census counts, error in the household estimates, or residual; it may be negative.')

# =============================================================================
# D06 (appendix) -- which vacancy definition is plausible
# =============================================================================
fig, a = plt.subplots(figsize=S.figsize('single', 66))
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
bb_ = a.bar(['Empty homes only\n(used)', "Including 'residents away'\n(rejected)"], [unc_emp, unc_all],
            color=[S.BAND['vacancy'][0], S.MUTED], width=0.6)
for bb, v in zip(bb_, [unc_emp, unc_all]):
    a.text(bb.get_x() + bb.get_width() / 2, v / 2, f'{v:,.0f} per year\n({100 * v / nb:+.0f}% of building)',
           ha='center', va='center', fontsize=S.FONT_SMALL, color='white', fontweight='bold')
a.axhline(0, color=S.INK, lw=S.LW_THIN)
a.set_ylabel(f"Unconsented additions required, 1992–{B['calib_end']}\n(dwellings per year)")
P.thousands(a.yaxis)
a.grid(axis='x', visible=False)
fig.tight_layout()
finish(fig, 'D06_vacancy_definition',
       'The unconsented additions each vacancy definition requires to close the stock identity, assuming the BRANZ '
       'demolition rate; counting residents-away dwellings as vacant requires implausibly many.')

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
print("=" * 70)
print(f" Built floor area 2026-2050: {R['total'][1:].sum() / M6:.2f} million m2")
print(f" Embodied carbon  2026-2050: {B['carbon_total_typ'].iloc[1:].sum().sum() / M6:,.1f} kt CO2e")
print(f" Household size 2050: {S_f[-1]:.3f} | vacancy {100 * B['v_forward']:.2f}% | "
      f"net replacement (long run) {100 * (B['demolition_rate'] + B['unconsented_rate']):.3f}%")
print(f" History bars: census intervals {', '.join(f'{a}-{b}' for a, b in INTERVALS)}; "
      f"pooled empty share {100 * POOLED_SHARE:.1f}%")
print(f" Vacancy: {VACANCY}")
print("=" * 70)
if SAVE_FIGURES:
    print("Saved D04-D06 in outputs/diagnostics/data_calibration/.")
else:
    plt.show()
