"""
DIAGNOSTICS -- sanity checks for Boss.py, past and future together
==================================================================
Six figures. Every time-series panel runs 1992-2050: history solid, projection
lighter or dashed, a dotted line at 2025. Everything is read from ONE run of
Boss.py, so the two scripts can never disagree.

  1  People and households       population, households, household size, flows
  2  The two household engines    people arriving vs homes emptying out
  3  The stock bucket             vacancy, demolition, unconsented additions
  4  Floor area                   by typology, by demand type, mix, dwelling size
  5  Embodied carbon              by typology, by material, cumulative, factors
  6  Checks                       reconciliation, the 2025->2026 join, rejections

Historical carbon is ESTIMATED by applying the 2025 case-study factors to past
floor area; it is shown for continuity, not as a measured series.
Figures are plotted, not saved (set SAVE_FIGURES = True to write PNGs).
"""

import importlib
import io
import contextlib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

import Boss as M
# Interactive consoles (Spyder, IPython, Jupyter) keep an imported module alive
# between runs, so an edited Boss.py would otherwise be ignored. Always reload.
M = importlib.reload(M)

SAVE_FIGURES = False

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
    need = ('stock_fwd', 'stock_cal', 'census', 'unconsented_rate', 'flow_annual',
            'hh_response', 'MAT_INTENSITY')
    miss = [k for k in need if k not in grab]
    miss += [f"results['{k}']" for k in ('vac', 'repl', 'unc')
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
BF = M.COMPLETION_RATE                         # consents -> built
YH = np.arange(1992, 2026)                     # history with defined flows
FY = np.asarray(B['forecast_years'])
PF = FY[1:]                                    # projected years (2025 is the anchor)
M6 = 1e6
R = B['results']['50th']
SC = B['stock_cal']
SF = B['stock_fwd']['50th']
HR = B['hh_response']
DF = B['df_forecast']

pop_h, hh_h, S_h = B['hist_pop'], B['hist_hh'], B['hist_S']
D_h = B['blended_dwelling_size']               # realised m2 per dwelling
D_f = B['future_dwelling_size'].values
S_f = DF['PopTotal_50th'].values / B['households_forecast']['50th']

C = dict(growth='#3498db', split='#e67e22', extra='#8e44ad', vac='#95a5a6',
         vchg='#f1c40f', demol='#34495e', unc='#16a085', built='black')


def split(ax):
    ax.axvline(2025.5, color='grey', ls=':', lw=1)


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


def finish(fig, name):
    fig.tight_layout()
    if SAVE_FIGURES:
        fig.savefig(name, dpi=130, bbox_inches='tight')


# =============================================================================
# FIGURE 1 -- people and households
# =============================================================================
fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
fig.suptitle('1. People and households, 1991-2050', fontsize=12)

a = ax[0, 0]
a.plot(pop_h.index, pop_h / M6, color='black', lw=2, label='observed')
a.plot(FY, DF['PopTotal_50th'] / M6, color='#2980b9', lw=2, ls='--', label='median projection')
a.fill_between(FY, DF['PopTotal_5th'] / M6, DF['PopTotal_95th'] / M6, color='#2980b9',
               alpha=0.15, label='5th-95th percentile')
tidy(a, 'Population', 'million people')
a.legend()

a = ax[0, 1]
hf = B['households_forecast']
a.plot(hh_h.index, hh_h / M6, color='black', lw=2, label='observed')
a.plot(FY, hf['50th'] / M6, color='#e67e22', lw=2, ls='--', label='median projection')
a.fill_between(FY, hf['5th'] / M6, hf['95th'] / M6, color='#e67e22', alpha=0.15,
               label='5th-95th percentile')
tidy(a, 'Households = population / household size', 'million households')
a.legend()

a = ax[1, 0]
a.plot(S_h.index, S_h, color='black', lw=2, label='observed')
a.plot(FY, HR['S_snz'], color='#95a5a6', lw=2, ls='--',
       label=f"Stats NZ path alone -> {HR['S_snz'][-1]:.3f}")
a.plot(FY, S_f, color='#c0392b', lw=2.5, label=f'model -> {S_f[-1]:.3f}')
a.text(0.02, 0.04, f"2025 fall: {HR['b'] * (HR['dP_obs_2025'] - HR['dP_ref'][0]):+.4f} from low "
       f"migration (ends),\n{HR['e_2025']:+.4f} unexplained (fades at {HR['rho']:.2f}/yr)",
       transform=a.transAxes, fontsize=8, va='bottom',
       bbox=dict(facecolor='white', alpha=0.85, edgecolor='#cccccc'))
tidy(a, 'Household size: Stats NZ long run, 2025 momentum fading', 'people per household')
a.legend(loc='upper right')

a = ax[1, 1]
a.plot(YH, pop_h.diff().loc[YH] / 1e3, color='#2980b9', lw=1.8, label='population growth')
a.plot(YH, hh_h.diff().loc[YH] / 1e3, color='#e67e22', lw=1.8, label='new households')
a.plot(PF, DF['PopGrowth_50th'].values[1:] / 1e3, color='#2980b9', lw=1.8, ls='--')
a.plot(PF, R['d_hh'][1:] / 1e3, color='#e67e22', lw=1.8, ls='--')
tidy(a, 'Annual flows', 'thousand per year')
a.legend()
finish(fig, 'diag_1_people_households.png')

# =============================================================================
# FIGURE 2 -- the two household engines
# =============================================================================
fig, ax = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw={'width_ratios': [1, 1.7]})
fig.suptitle('2. Where new households come from: people arriving, or homes emptying out',
             fontsize=12)

a = ax[0]
dP, dS = HR['dP_hist'], HR['dS_hist']
lr = stats.linregress(dP, dS)
a.scatter(dP / 1e3, dS, color='#7f8c8d', s=26, zorder=3)
xx = np.linspace(dP.min(), dP.max(), 50)
a.plot(xx / 1e3, lr.intercept + lr.slope * xx, color='black', lw=1.3,
       label=f'r = {lr.rvalue:+.2f}, p = {lr.pvalue:.0e}')
yrs_fit = list(HR['years_fit'])
for y, c in [(2023, '#27ae60'), (2024, '#e67e22'), (2025, '#c0392b')]:
    k = yrs_fit.index(y)
    a.scatter(dP[k] / 1e3, dS[k], color=c, s=85, edgecolor='black', zorder=4)
    a.annotate(str(y), (dP[k] / 1e3, dS[k]), xytext=(6, 5), textcoords='offset points',
               fontweight='bold')
a.axhline(0, color='black', lw=0.7)
a.set_title('The engines take turns\nfew arrivals: homes empty out  |  many: homes fill up')
a.set_xlabel('people arriving that year (thousand)')
a.set_ylabel('change in household size')
a.legend()

a = ax[1]
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
tidy(a, 'New households per year, split by engine (hatched = projected)', 'thousand per year')
a.legend(loc='upper right')
finish(fig, 'diag_2_household_engines.png')

# =============================================================================
# FIGURE 3 -- the stock bucket
# =============================================================================
fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
fig.suptitle('3. The stock bucket: built = households + vacancy + demolitions - residual (RV + unconsented)',
             fontsize=12)

cen = B['census']
knots = SC['knots']
a = ax[0, 0]
a.plot(SC['v'].index, 100 * SC['v'], color='#2c3e50', lw=2, label='vacancy used')
a.plot(FY, np.full(len(FY), 100 * B['v_forward']), color='#2c3e50', lw=2, ls='--')
meas = cen['empty'].notna()
for y, v in knots.items():
    filled = bool(meas.get(y, False))
    a.scatter(y, 100 * v, s=45, zorder=5, color='#c0392b' if filled else 'white',
              edgecolor='#c0392b')
    a.scatter(y, 100 * cen.loc[y, 'unoccupied'] / cen.loc[y, 'total_private'], marker='x',
              color='#95a5a6', s=40)
a.scatter([], [], color='#c0392b', label='census empty (measured)')
a.scatter([], [], color='white', edgecolor='#c0392b', label='census empty (2013 split applied)')
a.scatter([], [], marker='x', color='#95a5a6', label='all unoccupied (rejected)')
tidy(a, 'Vacancy: empty homes only', '% of private dwellings', xlim=(1985, 2050))
a.set_ylim(0, None)
a.legend(loc='lower left')

a = ax[0, 1]
hist_parts = [('new households', B['d_hh'].loc[YH], C['split']),
              ('vacancy allowance', SC['allow'].loc[YH], C['vac']),
              ('vacancy change', SC['change'].loc[YH], C['vchg']),
              ('demolitions replaced', SC['demol'].loc[YH], C['demol']),
              ('residual (RV units + unconsented)', SC['uncons'].loc[YH], C['unc'])]
fut_parts = [('', R['d_hh'][1:], C['split']), ('', SF['allow'][1:], C['vac']),
             ('', np.zeros(len(PF)), C['vchg']), ('', SF['demol'][1:], C['demol']),
             ('', SF['uncons'][1:], C['unc'])]
signed_bars(a, YH, [(l, v / 1e3, c) for l, v, c in hist_parts])
signed_bars(a, PF, [(l, v / 1e3, c) for l, v, c in fut_parts], projected=True)
built_h = BF * B['hist_total_units'].loc[YH]
built_f = R['total'][1:] / D_f[1:]
a.plot(YH, built_h / 1e3, color='black', lw=1.6, label='dwellings built')
a.plot(PF, built_f / 1e3, color='black', lw=1.6, ls='--')
tidy(a, 'Dwellings per year (hatched = projected)', 'thousand dwellings')
a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3)

a = ax[1, 0]
a.plot(SC['stock'].index, SC['stock'] / M6, color='#2c3e50', lw=2, label='dwelling stock')
a.plot(hh_h.index, hh_h / M6, color='#e67e22', lw=2, label='households')
a.plot(FY, SF['stock'] / M6, color='#2c3e50', lw=2, ls='--')
a.plot(FY, B['households_forecast']['50th'] / M6, color='#e67e22', lw=2, ls='--')
tidy(a, 'Stock = households / (1 - vacancy)', 'million')
a.legend()

a = ax[1, 1]
prev_h = SC['stock'].shift(1).loc[YH]
net_h = 100 * SC['net'].loc[YH] / prev_h
a.bar(YH, net_h, color=np.where(net_h < 0, C['unc'], C['demol']), width=0.85)
prev_f = np.concatenate([[SF['stock'][0]], SF['stock'][:-1]])[1:]
a.plot(PF, 100 * (SF['demol'][1:] + SF['uncons'][1:]) / prev_f, color='black', lw=1.8,
       ls='--', label='net, projected')
a.axhline(100 * B['demolition_rate'], color=C['demol'], ls='--', lw=1.2,
          label=f"demolition {100 * B['demolition_rate']:.3f}% (BRANZ, fixed)")
a.axhline(100 * B['unconsented_rate'], color=C['unc'], ls='--', lw=1.2,
          label=f"residual: RV units + unconsented {100 * B['unconsented_rate']:+.3f}% (calibrated)")
a.axhline(0, color='black', lw=0.7)
tidy(a, 'Net turnover = demolition - unconsented additions\n'
        'single years noisy: vacancy known only at censuses', '% of stock per year')
a.legend(loc='lower left')
finish(fig, 'diag_3_stock_bucket.png')

# =============================================================================
# FIGURE 4 -- floor area
# =============================================================================
fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
fig.suptitle('4. Floor area built, 1992-2050 (history converted to built: consents x '
             f'{BF:.2f})', fontsize=12)

a = ax[0, 0]
typ_h = B['hist_typ_gfa'].loc[YH] * BF
typ_f = B['evol_typ_total'].loc[PF]
a.stackplot(YH, [typ_h[t] / M6 for t in TYP], colors=[TC[t] for t in TYP], labels=TYP, alpha=0.95)
a.stackplot(PF, [typ_f[t] / M6 for t in TYP], colors=[TC[t] for t in TYP], alpha=0.5)
tidy(a, 'By typology', 'million m² per year')
a.legend(loc='upper left')

a = ax[0, 1]
Dh = D_h.loc[YH]
hs_raw = B['hist_hs_raw'].loc[YH]
hist_dem = [('growth (net of consolidation)', B['hist_growth'].loc[YH] - B['hist_avoided'].loc[YH], C['growth']),
            ('house-splitting', hs_raw.clip(lower=0), C['split']),
            ('extra space per dwelling', B['d_hh'].loc[YH] * (Dh - B['occupied_area_per_dwelling'].loc[YH]), C['extra']),
            ('vacancy allowance', SC['allow'].loc[YH] * Dh, C['vac']),
            ('vacancy change', SC['change'].loc[YH] * Dh, C['vchg']),
            ('demolition replacement', SC['demol'].loc[YH] * Dh, C['demol']),
            ('residual (RV units + unconsented)', SC['uncons'].loc[YH] * Dh, C['unc'])]
fut_dem = [('', R['growth'][1:], C['growth']), ('', R['hs_pos'][1:], C['split']),
           ('', R['extra'][1:], C['extra']), ('', R['vac'][1:], C['vac']),
           ('', np.zeros(len(PF)), C['vchg']), ('', R['repl'][1:], C['demol']),
           ('', R['unc'][1:], C['unc'])]
signed_bars(a, YH, [(l, np.asarray(v) / M6, c) for l, v, c in hist_dem])
signed_bars(a, PF, [(l, v / M6, c) for l, v, c in fut_dem], projected=True)
a.plot(YH, B['hist_total_gfa'].loc[YH] * BF / M6, color='black', lw=1.6, label='built (net)')
a.plot(PF, R['total'][1:] / M6, color='black', lw=1.6, ls='--')
tidy(a, 'By demand type (hatched = projected)', 'million m² per year')
a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3)

a = ax[1, 0]
sh_h, sh_f = B['hist_shares'], B['evolving_gfa_shares']
for t in TYP:
    a.plot(sh_h.index, 100 * sh_h[t], color=TC[t], lw=2, label=t)
    a.plot(FY, 100 * sh_f[t], color=TC[t], lw=2, ls='--')
tidy(a, 'Typology mix: damped trend from 2012', '% of floor area')
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
finish(fig, 'diag_4_floor_area.png')

# =============================================================================
# FIGURE 5 -- embodied carbon
# =============================================================================
MI, SI, TB = B['MAT_INTENSITY'], B['SOIL_INTENSITY'], B['T_BASELINE_2025']
mats = list(MI.index)
MC = dict(zip(mats + ['SOIL'], plt.get_cmap('tab10')(np.linspace(0, 1, len(mats) + 1))))
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
fa = B['flow_annual']
order = list(fa.sum().sort_values(ascending=False).index)
a.stackplot(YH, [mat_h[m] / M6 for m in order], colors=[MC[m] for m in order],
            labels=order, alpha=0.95)
a.stackplot(PF, [fa[m] / M6 for m in order], colors=[MC[m] for m in order], alpha=0.5)
tidy(a, 'Annual carbon by material (soil = land-use change)', 'kt CO₂e per year')
a.legend(loc='upper left', ncol=2)

a = ax[1, 0]
fc = B['flow_cum']
a.stackplot(fc.index, [fc[m] / M6 for m in order], colors=[MC[m] for m in order],
            labels=order, alpha=0.9)
tidy(a, f'Cumulative carbon 2026-2050: {fc.iloc[-1].sum() / M6:,.0f} kt', 'kt CO₂e',
     xlim=(2026, 2050))
a.legend(loc='upper left', ncol=2)

a = ax[1, 1]
bottom = np.zeros(len(TYP))
for m in mats:
    v = MI.loc[m, TYP].values
    a.bar(TYP, v, bottom=bottom, color=MC[m], label=m)
    bottom += v
a.bar(TYP, [SI[t] for t in TYP], bottom=bottom, color=MC['SOIL'], hatch='//',
      edgecolor='white', label='SOIL')
for k, t in enumerate(TYP):
    a.text(k, TB[t] + 8, f'{TB[t]:.0f}', ha='center', fontweight='bold')
a.set_title('Case-study intensity (16 buildings), constant over time')
a.set_ylabel('kg CO₂e per m²')
a.legend(loc='upper left', fontsize=7)
finish(fig, 'diag_5_carbon.png')

# =============================================================================
# FIGURE 6 -- checks
# =============================================================================
fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
fig.suptitle('6. Checks', fontsize=12)

a = ax[0, 0]
recon = sum(np.asarray(v, dtype=float) for _, v, _ in hist_dem)
obs = (B['hist_total_gfa'].loc[YH] * BF).values
a.plot(YH, obs / M6, color='black', lw=2.5, label='observed (built)')
a.plot(YH, recon / M6, color='#e74c3c', ls='', marker='o', ms=4, label='sum of demand parts')
a.set_title(f'History reproduced by the decomposition\n'
            f'max |difference| = {np.abs(recon - obs).max():.1e} m²')
a.set_ylabel('million m² per year')
a.legend()

a = ax[0, 1]
chg = 100 * B['hist_total_gfa'].pct_change().loc[YH].values
step = 100 * (R['total'][1] / (B['hist_total_gfa'].loc[2025] * BF) - 1)
a.hist(chg, bins=14, color='#bdc3c7', edgecolor='white')
a.axvline(step, color='#c0392b', lw=2.5, label=f'2025->2026 in the model: {step:+.1f}%')
a.axvline(np.median(chg), color='black', lw=1, ls='--', label=f'median year: {np.median(chg):+.1f}%')
a.set_title('Is the 2025->2026 join normal?\nhistorical year-to-year changes, 1992-2025')
a.set_xlabel('% change from previous year')
a.set_ylabel('number of years')
a.legend()

a = ax[1, 0]
cen_all = (cen['unoccupied'] / cen['total_private']).to_dict()
v_all = pd.Series(np.interp(B['years_hist'].astype(float), list(cen_all), list(cen_all.values())),
                  index=B['years_hist'])
prev_all = (hh_h / (1 - v_all)).shift(1)
net_all = (BF * B['hist_total_units'] - B['d_hh'] - B['d_hh'] * v_all / (1 - v_all)
           - hh_h.shift(1) * (1 / (1 - v_all)).diff())
unc_all = (net_all - B['demolition_rate'] * prev_all).loc[YH].mean()
unc_emp = SC['uncons'].loc[YH].mean()
nb = built_h.mean()
bars = a.bar(['empty homes only\n(used)', "incl. 'residents away'\n(rejected)"],
             [unc_emp, unc_all], color=[C['unc'], '#e74c3c'])
for bb, v in zip(bars, [unc_emp, unc_all]):
    a.text(bb.get_x() + bb.get_width() / 2, v / 2, f'{v:,.0f}/yr\n({100 * v / nb:+.0f}% of building)',
           ha='center', va='center', fontsize=9, color='white', fontweight='bold')
a.axhline(0, color='black', lw=0.7)
a.set_title("Which vacancy definition is plausible?\nunconsented additions each one requires, 1992-2025")
a.set_ylabel('dwellings per year')

a = ax[1, 1]
tot_mat = MI[TYP].sum() + pd.Series(SI)[TYP]
x = np.arange(len(TYP))
a.bar(x - 0.2, tot_mat.values, 0.4, color='#34495e', label='materials + soil')
a.bar(x + 0.2, [TB[t] for t in TYP], 0.4, color='#e67e22', label='intensity used')
a.set_xticks(x)
a.set_xticklabels(TYP)
dev = max(abs(tot_mat[t] - TB[t]) for t in TYP)
a.set_title(f'Carbon factors add up (internal consistency of the CSVs only)\n'
            f'max |difference| = {dev:.3f} kg/m²')
a.set_ylabel('kg CO₂e per m²')
a.legend()
finish(fig, 'diag_6_checks.png')

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
print("=" * 70)
print(f" Built floor area 2026-2050: {R['total'][1:].sum() / M6:.2f} million m2")
print(f" Embodied carbon  2026-2050: {B['carbon_total_typ'].iloc[1:].sum().sum() / M6:,.1f} kt CO2e")
print(f" 2025 -> 2026 step: {step:+.1f}%  (median historical year {np.median(chg):+.1f}%)")
print(f" History reconstruction: max |difference| {np.abs(recon - obs).max():.1e} m2")
print(f" Household size 2050: {S_f[-1]:.3f} | vacancy {100 * B['v_forward']:.2f}% | "
      f"demolition {100 * B['demolition_rate']:.3f}% | unconsented {100 * B['unconsented_rate']:+.3f}%")
print("=" * 70)
if SAVE_FIGURES:
    print("Saved diag_1 ... diag_6 beside the script.")

plt.show()