"""
DIAGNOSTICS -- sanity checks for Boss.py, past and future together
==================================================================
Four figures and one appendix. Everything is read from ONE run of Boss.py, so
the two scripts can never disagree. Projections are annual; the history of the
demand decomposition (diag_3, diag_4) is one bar per census interval, because
between censuses households and vacancy are interpolated and annual detail is
not identified.

  2  The two household engines    people arriving vs homes emptying out
  3  The stock bucket             vacancy, dwellings by component, stock
  4  Floor area                   by typology, by demand type, mix, dwelling size
  5  Embodied carbon              by typology, by material, cumulative, factors
  3b Appendix                     which vacancy definition is plausible

Historical carbon is ESTIMATED by applying the 2025 case-study factors to past
floor area; it is shown for continuity, not as a measured series. The
accounting identities and factor sums are checked in tests/test_identities.py.
Figures are plotted, not saved (run_all.py sets PATHWAY_SAVE_FIGURES=1 to write
PNGs to outputs/figures/).
"""

import importlib
import io
import os
import contextlib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

import Boss as M
import engine
import validation
# Interactive consoles (Spyder, IPython, Jupyter) keep an imported module alive
# between runs, so an edited Boss.py would otherwise be ignored. Always reload.
M = importlib.reload(M)

SAVE_FIGURES = os.environ.get('PATHWAY_SAVE_FIGURES') == '1'   # run_all.py sets this
FIG_DIR = os.path.join(M.OUT_DIR, 'figures')

plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'legend.fontsize': 7.5,
                     'axes.grid': True, 'grid.alpha': 0.3})


# ---------------------------------------------------------------------------
# One silent run of Boss, with a version check
# ---------------------------------------------------------------------------
_BOSS_CACHE = None


def boss_locals():
    """Run Boss.main() silently once per run and return its internal variables."""
    global _BOSS_CACHE
    if _BOSS_CACHE is not None:
        return _BOSS_CACHE
    M.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        grab = M.main()
    if not isinstance(grab, dict):
        raise RuntimeError(f"{M.__file__}: main() returned no state; use the latest Boss.py.")
    need = ('stock_fwd', 'stock_cal', 'census', 'unconsented_rate', 'flow_annual', 'hist_rv_units',
            'hh_response', 'MAT_INTENSITY', 'fig_bands')
    miss = [k for k in need if k not in grab]
    miss += [f"results['{k}']" for k in ('vac', 'repl', 'unc', 'rv')
             if k not in grab.get('results', {}).get('50th', {})]
    if miss:
        raise RuntimeError(
            f"\nThe Boss.py being run is OLDER than this Diagnostics.py.\n"
            f"  file used: {M.__file__}\n  missing:   {', '.join(miss)}\n"
            f"Use the latest Boss.py. In Spyder, restart the kernel once.")
    _BOSS_CACHE = grab
    return grab


B = boss_locals()

# ---------------------------------------------------------------------------
# Shared quantities
# ---------------------------------------------------------------------------
TYP = list(B['typ_names'])
TC = M.TYPOLOGY_COLORS
BF = M.COMPLETION_RATE                         # consents -> built (x the completion lag, see Boss)
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
D_h = B['blended_dwelling_size']               # realised m2 per dwelling
D_f = B['future_dwelling_size'].values
S_f = DF['PopTotal_50th'].values / B['households_forecast']['50th']

C = dict(growth='#3498db', split='#e67e22', extra='#8e44ad', vac='#95a5a6',
         vchg='#f1c40f', repl=M.REPL_COLOR, wave=M.WAVE_COLOR, rv=M.RV_COLOR, join=M.JOIN_COLOR, built='black')

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
HIST_NOTE = (f'History: one bar per census interval (interval means; vacancy on one definition, pooled '
             f'2018/23 empty share {100 * POOLED_SHARE:.1f}% of unoccupied); between censuses annual detail is not '
             f'identified. Faint bar: {CENSUS_Y[-1] + 1}-{YH[-1]}, households consent-derived. '
             f'Projection annual, hatched.')


def split(ax):
    ax.axvline(2025.5, color='grey', ls=':', lw=1)


def mark_anchor(ax):
    """The 2025 row is the observed anchor and the projection starts in 2026:
    the step there is deliberate, not a model artefact."""
    ax.axvline(2025.5, color='grey', lw=0.8, ls=':')
    ax.text(2025.7, 0.97, '2025 observed anchor ->\nprojection (deliberate join)', transform=ax.get_xaxis_transform(),
            fontsize=7, va='top', color='grey')


def tidy(ax, title, ylabel, xlim=(1991, 2050)):
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if xlim:
        ax.set_xlim(*xlim)
    split(ax)


def signed_bars(ax, years, parts, projected=False):
    """Stack positive parts upward and negative parts downward from zero."""
    up = np.zeros(len(years))
    dn = np.zeros(len(years))
    for lab, vals, col in parts:
        v = np.asarray(vals, dtype=float)
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        kw = dict(color=col, width=0.85, alpha=0.5 if projected else 0.95,
                  hatch='//' if projected else None, edgecolor='white', linewidth=0)
        ax.bar(years, pos, bottom=up, label=None if projected else lab, **kw)
        ax.bar(years, neg, bottom=dn, **kw)
        up += pos
        dn += neg
    ax.axhline(0, color='black', lw=0.7)


def interval_means(parts):
    """parts: [(label, annual Series over YH, colour)] -> per census interval, the mean of
    each part over the years y0+1..y1: [(y0, y1, [(label, mean, colour)])]."""
    return [(y0, y1, [(lab, float(np.mean(np.asarray(ser.loc[y0 + 1:y1], float))), col) for lab, ser, col in parts])
            for y0, y1 in INTERVALS]


def interval_bars(ax, groups, scale=1.0):
    """One stacked bar per census interval, spanning its years (signed: a negative mean
    is drawn below zero). The interval after the latest census is faint."""
    for i, (y0, y1, parts) in enumerate(groups):
        up = dn = 0.0
        faint = y0 == CENSUS_Y[-1]
        for lab, m, col in parts:
            m = m / scale
            kw = dict(width=y1 - y0, align='edge', color=col, alpha=0.35 if faint else 0.95,
                      edgecolor='white', linewidth=0.6, label=lab if i == 0 else None)
            if m >= 0:
                ax.bar(y0 + 0.5, m, bottom=up, **kw)
                up += m
            else:
                ax.bar(y0 + 0.5, m, bottom=dn, **kw)
                dn += m
    ax.axhline(0, color='black', lw=0.7)


def finish(fig, name, note=None):
    if note:
        fig.tight_layout(rect=(0, 0.035, 1, 1))
        fig.text(0.5, 0.008, note, ha='center', fontsize=8, style='italic')
    else:
        fig.tight_layout()
    if SAVE_FIGURES:
        os.makedirs(FIG_DIR, exist_ok=True)
        fig.savefig(os.path.join(FIG_DIR, name), dpi=130, bbox_inches='tight')


# =============================================================================
# FIGURE 2 -- the two household engines
# =============================================================================
fig, ax = plt.subplots(1, 3, figsize=(20, 5.5), gridspec_kw={'width_ratios': [1, 1, 1.7]})
fig.suptitle('2. Where new households come from. Caveat: between censuses, households are consent-derived; '
             'the relationship is partly mechanical', fontsize=12)

a = ax[0]
dP, dS = HR['dP_hist'], HR['dS_hist']
lr = stats.linregress(dP, dS)
a.scatter(dP / 1e3, dS, color='#7f8c8d', s=26, zorder=3,
          label=f"{HR['years_fit'][0]}-{HR['years_fit'][-1]} (census-benchmarked)")
xx = np.linspace(dP.min(), dP.max(), 50)
a.plot(xx / 1e3, lr.intercept + lr.slope * xx, color='black', lw=1.3,
       label=f'r = {lr.rvalue:+.2f}, p = {lr.pvalue:.0e}')
late = [y for y in YH if y > HR['years_fit'][-1]]
dP_l, dS_l = pop_h.diff().loc[late], S_h.diff().loc[late]
a.scatter(dP_l / 1e3, dS_l, facecolor='none', edgecolor='#c0392b', s=60, zorder=4,
          label=f'{late[0]}-{late[-1] % 100:02d}: consent-derived, no census check')
for y, off in ((2024, (6, 5)), (2025, (-30, -12))):
    a.annotate(str(y), (dP_l[y] / 1e3, dS_l[y]), xytext=off, textcoords='offset points')
a.axhline(0, color='black', lw=0.7)
a.set_title('Household size vs arrivals (between censuses households are consent-derived;\n'
            'the relationship is partly mechanical: housing supply meets migration)')
a.set_xlabel('population growth that year (thousand)')
a.set_ylabel('change in household size')
a.legend(fontsize=7)

a = ax[1]
cons_all = (B['hist_total_units'] + B['hist_rv_units']).shift(1)
ratio = (B['hist_hh_dhe'].diff() / cons_all).loc[YH]
bases = [1991, 1996, 2001, 2006, 2013, 2018]
a.bar(YH, ratio, color=['#c0392b' if y > 2018 else '#7f8c8d' for y in YH], width=0.8)
for y in bases:
    a.axvline(y + 0.5, color='black', lw=0.6, ls=':')
a.set_title('Stats NZ household growth / previous-year consents\n'
            'flat within each census period; 0.888 every year since 2019 (consent-derived)')
a.set_ylabel('ratio'); a.set_xlim(1991, 2026)

a = ax[2]
pop_part_h = pop_h.diff().loc[YH] / S_h.loc[YH]
size_part_h = hh_h.diff().loc[YH] - pop_part_h
pop_part_f = DF['PopGrowth_50th'].values[1:] / S_f[1:]
size_part_f = R['d_hh'][1:] - pop_part_f
parts_h = [('from people arriving', pop_part_h, C['growth']),
           ('from household size changing', size_part_h, C['split'])]
parts_f = [('', pop_part_f, C['growth']), ('', size_part_f, C['split'])]
signed_bars(a, YH, [(l, v / 1e3, c) for l, v, c in parts_h])
signed_bars(a, PF, [(l, v / 1e3, c) for l, v, c in parts_f], projected=True)
a.plot(YH, hh_h.diff().loc[YH] / 1e3, color='black', lw=1.5, label='new households (net)')
a.plot(PF, R['d_hh'][1:] / 1e3, color='black', lw=1.5, ls='--')
tidy(a, 'New households per year, split by engine (hatched = projected; 2019-25 consent-derived)',
     'thousand per year')
a.legend(loc='upper right')
finish(fig, 'diag_2_household_engines.png')

# =============================================================================
# FIGURE 3 -- the stock bucket
# =============================================================================
fig = plt.figure(figsize=(14, 9))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15])
fig.suptitle('3. The stock bucket: built (in scope) = households + vacancy + net replacement'
             ' - retirement villages', fontsize=12)

cen = B['census']
SC = B['stock_cal']
knots = SC['knots']
a = fig.add_subplot(gs[0, 0])
a.plot(SC['v'].index, 100 * SC['v'], color='#2c3e50', lw=2, label='published empty (model; forward held at 2023)')
a.plot(SCc['v'].index, 100 * SCc['v'], color='#16a085', lw=1.5, ls='-.',
       label='one definition: pooled 2018/23 empty share (history bars below)')
_v_imp = 1 - E50['hh'] / (E50['stock'] + E50['stock_join'])     # held rate + unabsorbed surplus / stock
a.plot(FY, np.full(len(FY), 100 * B['v_forward']), color='#2c3e50', lw=1.2, ls=':', label='held (latest census)')
a.plot(FY, 100 * _v_imp, color='#2c3e50', lw=2, ls='--', label='implied: held + near-term surplus / stock')
meas = cen['empty'].notna()
for y, v in knots.items():
    filled = bool(meas.get(y, False))
    a.scatter(y, 100 * v, s=45, zorder=5, color='#c0392b' if filled else 'white', edgecolor='#c0392b')
    a.scatter(y, 100 * cen.loc[y, 'unoccupied'] / cen.loc[y, 'total_private'], marker='x',
              color='#95a5a6', s=40)
a.scatter([], [], color='#c0392b', label='census empty (published)')
a.scatter([], [], color='white', edgecolor='#c0392b', label='census empty (2013 split applied)')
a.scatter([], [], marker='x', color='#95a5a6', label='all unoccupied (rejected)')
a.axvspan(2013, 2018, color='#f1c40f', alpha=0.12, label='2013->2018 empty/away definition break')
tidy(a, 'Vacancy: empty homes only', '% of private dwellings', xlim=(1985, 2050))
a.set_ylim(0, None)
a.legend(loc='lower left', fontsize=6.5)

a = fig.add_subplot(gs[0, 1])
a.plot(SC['stock'].index, SC['stock'] / M6, color='#2c3e50', lw=2, label='dwelling stock')
M.plot_hist_estimated(a, hh_h, M6, color='#e67e22', label='households', k=B['hh_rebase_k'])
a.plot(FY, (SF['stock'] + SF['stock_join']) / M6, color='#2c3e50', lw=2, ls='--',
       label='stock projected (incl. near-term surplus)')
a.plot(FY, B['households_forecast']['50th'] / M6, color='#e67e22', lw=2, ls='--')
tidy(a, 'Stock = households / (1 - vacancy) + near-term surplus', 'million')
a.legend(fontsize=6.5)

a = fig.add_subplot(gs[1, :])
hist_parts = [('new households', B['d_hh'].loc[YH], C['split']),
              ('vacancy allowance + change', (SCc['allow'] + SCc['change']).loc[YH], C['vac']),
              ('net replacement (demolition net of unconsented additions)', SCc['net'].loc[YH], C['repl']),
              ('retirement-village units (out of scope)', SCc['rv'].loc[YH], C['rv'])]
interval_bars(a, interval_means(hist_parts), 1e3)
_wave_u = (np.asarray(B['rate_path'], float) - (B['demolition_rate'] + B['unconsented_rate'])) * E50['prev']
fut_parts = [('', R['d_hh'][1:], C['split']), ('', SF['allow'][1:], C['vac']),
             ('', (SF['demol'] + SF['uncons'] - _wave_u)[1:], C['repl']), ('', _wave_u[1:], C['wave']),
             ('', SF['rv'][1:], C['rv']), ('', SF['join'][1:], C['join'])]
signed_bars(a, PF, [(l, v / 1e3, c) for l, v, c in fut_parts], projected=True)
for _lab, _arr, _col in (('replacement: recent redevelopment wave (fading)', _wave_u, C['wave']),
                         ('near-term market excess', SF['join'], C['join'])):
    if np.any(np.asarray(_arr)[1:] != 0):              # legend swatch in the projected style
        a.fill_between([], [], color=_col, alpha=0.5, hatch='//', edgecolor='white', label=_lab)
built_h = B['hist_built_units'].loc[YH]          # in-scope dwellings built (lagged completions)
built_f = R['total'][1:] / D_f[1:]
a.plot(YH, built_h / 1e3, color='black', lw=1.4, label='dwellings built, in scope (observed, annual)')
a.plot(PF, built_f / 1e3, color='black', lw=1.6, ls='--')
tidy(a, 'Dwellings per year (history: net replacement is the household-identity residual; the model\'s '
        'rate comes from census dwelling counts, fig_replacement_rate)', 'thousand dwellings')
a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=4, fontsize=7)
finish(fig, 'diag_3_stock_bucket.png', HIST_NOTE)

# =============================================================================
# FIGURE 4 -- floor area
# =============================================================================
fig, ax = plt.subplots(2, 2, figsize=(14, 9))
fig.suptitle('4. Floor area built, 1992-2050 (history converted to built: consents x '
             f"{BF:.2f}, completion lag W = {B['lag_w']:.2f} yr)", fontsize=12)

a = ax[0, 0]
typ_h = B['hist_built_typ_gfa'].loc[YH]
typ_f = B['evol_typ_total'].loc[PF]
a.stackplot(YH, [typ_h[t] / M6 for t in TYP], colors=[TC[t] for t in TYP], labels=TYP, alpha=0.95)
a.stackplot(PF, [typ_f[t] / M6 for t in TYP], colors=[TC[t] for t in TYP], alpha=0.5)
tidy(a, 'By typology (observed annual history)', 'Mm² per year')
a.legend(loc='upper left')

a = ax[0, 1]
Dh = D_h.loc[YH]
hs_raw = B['hist_hs_raw'].loc[YH]
hist_dem = [('growth (net of consolidation)', B['hist_growth'].loc[YH] - B['hist_avoided'].loc[YH], C['growth']),
            ('house-splitting', hs_raw.clip(lower=0), C['split']),
            ('extra space per dwelling', B['d_hh'].loc[YH] * (Dh - B['occupied_area_per_dwelling'].loc[YH]),
             C['extra']),
            ('vacancy allowance + change', (SCc['allow'] + SCc['change']).loc[YH] * Dh, C['vac']),
            ('replacement (net of unconsented additions)', SCc['net'].loc[YH] * Dh, C['repl'])]
_rv_h = SCc['rv'].loc[YH] * Dh
# in scope, as in the projection: every band x (1 - RV share) = in-scope total / bands before RV
groups = []
for y0, y1, parts in interval_means(hist_dem + [('', _rv_h, C['rv'])]):
    f = sum(m for _, m, _ in parts) / sum(m for _, m, _ in parts[:-1])
    groups.append((y0, y1, [(l, m * f, c) for l, m, c in parts[:-1]]))
interval_bars(a, groups, M6)
bands, total = B['fig_bands']['gfa']                 # in scope, already in Mm2
signed_bars(a, PF, [('', v, c) for _, v, c in bands], projected=True)
for _lab, _col in ((M.WAVE_LABEL, C['wave']), ('near-term market excess', C['join'])):
    a.fill_between([], [], color=_col, alpha=0.5, hatch='//', edgecolor='white', label=_lab)
a.plot(YH, B['hist_built_gfa'].loc[YH] / M6, color='black', lw=1.4, label='built, in scope (observed, annual)')
a.plot(PF, total, color='black', lw=1.6, ls='--')
tidy(a, 'By demand type, in scope (excl. retirement villages)', 'Mm² per year')
a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3)

a = ax[1, 0]
sh_h, sh_f = B['hist_shares'], B['evolving_gfa_shares']
for t in TYP:
    a.plot(sh_h.index, 100 * sh_h[t], color=TC[t], lw=2, label=t)
    a.plot(FY, 100 * sh_f[t], color=TC[t], lw=2, ls='--')
tidy(a, ('Typology mix: held at 2022–26 average (reference)' if B['mix_used'] == 'held'
         else 'Typology mix: damped trend from 2012'), '% of floor area')
a.set_ylim(0, 100)
a.legend()

a = ax[1, 1]
ds_h = B['hist_dwelling_size']
for t in TYP:
    a.plot(ds_h.index, ds_h[t], color=TC[t], lw=1.8, label=t)
    a.plot(FY, np.full(len(FY), B['size_ref'][t]), color=TC[t], lw=1.8, ls='--')
a.plot(D_h.index, D_h, color='black', lw=2, label='blended')
a.plot(FY, D_f, color='black', lw=2, ls='--')
tidy(a, 'Dwelling size: held at 2023-25 per typology\n(blended falls only because the mix shifts)',
     'm² per dwelling')
a.legend(ncol=2)
finish(fig, 'diag_4_floor_area.png',
       HIST_NOTE + f" Excludes retirement-village units ({100 * B['rv_share']:.1f}% of new dwellings).")

# =============================================================================
# FIGURE 5 -- embodied carbon
# =============================================================================
MI, SI, TB = B['MAT_INTENSITY'], B['SOIL_INTENSITY'], B['T_BASELINE_2025']
mats = list(MI.index)
STYLE = {col: (lab, colour) for col, lab, colour in M.MATERIAL_STYLE}
fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
fig.suptitle('5. Embodied carbon (A1-A5, B2, B4, C1-C4 + soil). History estimated with '
             '2025 case-study factors', fontsize=12)

a = ax[0, 0]
car_h = pd.DataFrame({t: typ_h[t] * TB[t] for t in TYP})
car_f = B['carbon_total_typ'].loc[PF]
a.stackplot(YH, [car_h[t] / M6 for t in TYP], colors=[TC[t] for t in TYP], labels=TYP, alpha=0.95)
a.stackplot(PF, [car_f[t] / M6 for t in TYP], colors=[TC[t] for t in TYP], alpha=0.5)
tidy(a, 'Annual carbon by typology', 'kt CO₂e per year')
a.legend(loc='upper left')

a = ax[0, 1]
mat_h = pd.DataFrame({m: sum(typ_h[t] * MI.loc[m, t] for t in TYP) for m in mats})
mat_h['SOIL'] = sum(typ_h[t] * SI[t] for t in TYP)
handles = M.stack_materials(a, YH, mat_h, M6, alpha=0.95)
M.stack_materials(a, PF, B['flow_annual'], M6, alpha=0.5)
tidy(a, 'Annual carbon by material (soil = land-use change)', 'kt CO₂e per year')
a.legend(handles=handles, loc='upper left', ncol=2)

a = ax[1, 0]
fc = B['flow_cum']
a.legend(handles=M.stack_materials(a, fc.index, fc, M6), loc='upper left', ncol=2)
tidy(a, f'Cumulative carbon 2026-2050: {fc.iloc[-1].sum() / M6:,.0f} kt', 'kt CO₂e',
     xlim=(2026, 2050))

a = ax[1, 1]
bottom = np.zeros(len(TYP))
handles = []
for col, lab, colour in M.MATERIAL_STYLE:
    v = np.array([SI[t] for t in TYP]) if col == 'SOIL' else MI.loc[col, TYP].values
    handles.append(a.bar(TYP, v, bottom=bottom, color=colour, label=lab,
                         alpha=M.SOIL_ALPHA if col == 'SOIL' else 1.0, **M.EDGE))
    bottom += v
for k, t in enumerate(TYP):
    a.text(k, TB[t] + 8, f'{TB[t]:.0f}', ha='center', fontweight='bold')
a.set_title('Case-study intensity (16 buildings), constant over time')
a.set_ylabel('kg CO₂e per m²')
a.legend(handles=handles[::-1], loc='upper left', fontsize=7)
finish(fig, 'diag_5_carbon.png')

# =============================================================================
# APPENDIX (3b) -- which vacancy definition is plausible
# =============================================================================
fig, a = plt.subplots(figsize=(7, 5))
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
bars = a.bar(['empty homes only\n(used)', "incl. 'residents away'\n(rejected)"],
             [unc_emp, unc_all], color=['#16a085', '#e74c3c'])
for bb, v in zip(bars, [unc_emp, unc_all]):
    a.text(bb.get_x() + bb.get_width() / 2, v / 2, f'{v:,.0f}/yr\n({100 * v / nb:+.0f}% of building)',
           ha='center', va='center', fontsize=9, color='white', fontweight='bold')
a.axhline(0, color='black', lw=0.7)
a.set_title(f"Which vacancy definition is plausible?\nunconsented additions each one requires, 1992-{B['calib_end']} "
            f"(assumes the BRANZ demolition rate)")
a.set_ylabel('dwellings per year')
finish(fig, 'diag_3b_appendix_vacancy_definition.png')

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
print("=" * 70)
if SAVE_FIGURES:
    print(f"Saved diag_2 ... diag_5 and diag_3b in {FIG_DIR}/.")

plt.show()
