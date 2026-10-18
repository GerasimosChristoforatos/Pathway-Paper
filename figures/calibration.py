"""Calibration diagnostics (outputs/diagnostics/calibration/; figure_plan.DIAGNOSTICS['calibration'] and D13).

Drawn from data files only (compute / draw separation, MODEL v3.0.0): the figure source written by projection.py
(D01-D03, D08, D09, D13; export_figure_sources) and Diagnostics.py (D04-D06), and baseline/overbuild_absorption_log.csv
(D35). Sign rules of figures/draw.py: bars with a negative component are drawn with bars_cumulative (negative parts
unfilled, outlined in the component colour, hanging from the top of the positive stack; net tick); materials are
never negative (nonnegative: STOP); only the surge band (redevelopment) is hatched.
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S

M6 = 1e6


def _src(fid):
    return [f'figure_source/{fid}.json']


def _ref():
    r = dict(S.SCENARIO['REF'])
    r.pop('label')
    return r


def _band(ax, x, lo, hi, label):
    ax.fill_between(x, lo, hi, label=label, **S.MC_BAND)


# ---------------------------------------------------------------------------
# D01-D03: population and households
# ---------------------------------------------------------------------------
def d01():
    fid = 'D01_population'
    d = D.src(fid)
    yh, fy = d['years_hist'], d['forecast_years']
    fig, ax = plt.subplots(figsize=S.figsize('double', 62))
    ax.plot(yh, d['population_hist'].values / M6, color=S.INK,
            label='History (estimated resident population, 31 December)')
    _band(ax, fy, d['population_5th'] / M6, d['population_95th'] / M6, 'Population 5th–95th percentile')
    ax.plot(fy, d['population_50th'] / M6, label='Reference projection (median)', **_ref())
    P.split(ax)
    ax.set_xlim(yh[0], fy[-1])
    ax.set_ylabel('Population (million)')
    ax.legend(loc='upper left')
    S.save_figure(fig, fid, source=_src(fid))


def d02():
    fid = 'D02_households'
    d = D.src(fid)
    yh, fy, anchor, k = d['years_hist'], d['forecast_years'], int(d['S_ANCHOR_YEAR']), d['hh_rebase_k']
    fig, ax = plt.subplots(figsize=S.figsize('double', 66))
    dhe = d['households_dhe_published']
    ax.plot(dhe.index, dhe.values / M6, color=S.MUTED, lw=S.LW_THIN, label='Stats NZ household estimates as published')
    P.history_estimated(ax, d['households_hist'], anchor, M6, label='History (31 Dec)', k=k)
    _band(ax, fy, d['households_5th'] / M6, d['households_95th'] / M6,
          '5th–95th population percentile (household size fixed)')
    ax.plot(d['projection_years'], d['projection_households'] / M6,
            label='Projection: population / household size, median', **_ref())
    P.split(ax)
    ax.set_xlim(yh[0], fy[-1])
    ax.set_ylabel('Households (million)')
    ax.legend(loc='upper left', fontsize=S.FONT_SMALL)
    S.save_figure(fig, fid, note=f'Projection from the {anchor} census point; 2019–23 Stats NZ estimates scaled to the '
                                 f'{anchor} census (×{k:.3f}).', source=_src(fid))


def d03():
    fid = 'D03_household_size'
    d = D.src(fid)
    yh, fy, anchor = d['years_hist'], d['forecast_years'], int(d['S_ANCHOR_YEAR'])
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 70))
    P.history_estimated(a, d['household_size_hist'], anchor, 1.0, label='History', k=d['hh_rebase_k'])
    a.plot(d['projection_years'], d['projection_household_size'],
           label=f'Projection (Stats NZ shape from the {anchor} census point)', **_ref())
    P.split(a)
    a.set_xlim(yh[0], fy[-1])
    a.set_ylabel('Household size (persons per household)')
    a.legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'Household size')
    pyr = fy[1:]
    dp, dh = d['population_growth_hist'], d['household_formation_hist']
    b.plot(yh[1:], dp.values[1:] / 1e3, color=S.INK, label='Population growth, history')   # 1991: no flow
    b.plot(yh[1:], dh.values[1:] / 1e3, color=S.ACCENT_ORANGE, label='Household formation, history')
    b.plot(pyr, d['population_growth_50th'][1:] / 1e3, color=S.INK, ls='--', label='Population growth, projection')
    b.plot(pyr, d['household_formation_50th'][1:] / 1e3, color=S.ACCENT_ORANGE, ls='--',
           label='Household formation, projection')
    P.split(b)
    b.set_xlim(yh[0], fy[-1])
    b.set_ylabel('Persons or households per year (thousand)')
    b.legend(loc='upper left', fontsize=S.FONT_MIN)
    P.panel(b, 'b', 'Population growth and household formation')
    fig.tight_layout()
    S.save_figure(fig, fid, source=_src(fid))


# ---------------------------------------------------------------------------
# stacked bars by component (D04c, D05c)
# ---------------------------------------------------------------------------
UNEXPLAINED = S.UNEXPLAINED                    # unexplained building: faded red, no hatch (face, hatch, hatch colour)
RV = ('#8C8C8C', None)                         # retirement villages: out of scope, grey (v3: no hatch; always
#                                                negative, so an outline: darker than the v2.1.2 #BDBDBD face)
# component id: (label, colour, hatch); colours by band (style.BAND), labels in the release vocabulary (naming)
COMP = {'new_households': ('New households', '#B0B0B0', None),
        'vacancy': ('Vacancy (allowance and change)',) + S.BAND['vacancy'],
        'replacement': (N.BANDS['replacement'],) + S.BAND['replacement'],
        'unconsented': (N.BANDS['unconsented'],) + S.BAND['unconsented'],
        'redevelopment': (N.BANDS['redevelopment'],) + S.BAND['redevelopment'],
        'retirement_villages': (N.BAND_DETAIL['retirement_villages'],) + RV,
        'overbuild_2026': (N.BANDS['overbuild_2026'],) + S.BAND['overbuild_2026'],
        'overbuild_absorbed': (N.BANDS['overbuild_absorbed'],) + S.BAND['overbuild_absorbed'],
        # history only (D05c): census-measured net replacement, and what the components leave unexplained
        'net_replacement_census': ('Net replacement, history (census dwelling counts; parts not separable)',)
        + S.BAND['replacement'],
        'unexplained_building': ('Unexplained building', UNEXPLAINED[0], UNEXPLAINED[1]),
        'growth': ('From population growth',) + S.BAND['growth'],
        'smaller_households': ('From household-size change',) + S.BAND['smaller_households']}
EDGE = {'unexplained_building': UNEXPLAINED[2], **S.BAND_HATCHCOLOR}    # hatch colours (style.fill)


def _fill(cid, alpha=1.0):
    return S.fill(COMP[cid][1], COMP[cid][2], EDGE.get(cid), alpha)


def comp_bars(ax, x, parts, width, alpha=1.0):
    """P.bars_cumulative with the component colours: positive parts filled (faded by alpha), each negative part an
    unfilled segment outlined in its component colour hanging from the top of the positive stack, net tick.
    draw.negative_bar_style knows only the band colours, so the outlines of the components that are not demand
    bands (new households, retirement villages, census net replacement, unexplained building) are recoloured here."""
    x = np.atleast_1d(np.asarray(x, float))
    parts = [(cid, np.broadcast_to(np.asarray(v, float), x.shape)) for cid, v in parts]
    n0 = len(ax.patches)
    P.bars_cumulative(ax, x, parts, width, styles={cid: _fill(cid, alpha) for cid, _ in parts})
    neg = [p for p in ax.patches[n0:] if p.get_gid() == P.NEG_BAR_GID]
    order = [cid for cid, v in parts if np.any(v < 0)]
    if len(neg) != len(order) * len(x):
        raise SystemExit('comp_bars: unexpected number of negative segments.')
    for i, p in enumerate(neg):
        p.set_edgecolor(COMP[order[i // len(x)]][1])
        p.set_alpha(max(alpha, 0.6))


def comp_handles(ids, negative=()):
    out = []
    for c in ids:
        if c in negative:
            out.append(Patch(label=COMP[c][0], facecolor='none', edgecolor=COMP[c][1], linewidth=S.LW_OUTLINE))
        else:
            out.append(Patch(label=COMP[c][0], **dict(_fill(c), edgecolor='#555555', linewidth=S.LW_THIN)))
    return out


def sign_handles():
    return [Patch(facecolor='none', edgecolor=S.MUTED, linewidth=S.LW_OUTLINE,
                  label='Negative part: outline in its colour, hanging from the top of the stack'),
            Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label='Net total of a bar with a negative part')]


# ---------------------------------------------------------------------------
# D04 household formation
# ---------------------------------------------------------------------------
def d04():
    fid = 'D04_household_formation'
    d = D.src(fid)
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 78), gridspec_kw={'width_ratios': [1, 1, 1.5]})
    a = ax[0]
    dP, dS, yf, fit = d['dP_fit'], d['dS_fit'], d['years_fit'], d['fit']
    a.scatter(dP / 1e3, dS, color=S.MUTED, s=10, zorder=3, label=f'{int(yf[0])}–{int(yf[-1])} (census-benchmarked)')
    xx = np.linspace(dP.min(), dP.max(), 50)
    a.plot(xx / 1e3, fit['intercept'] + fit['slope'] * xx, color=S.INK, lw=S.LW,
           label=f"r = {fit['r']:+.2f}, p = {fit['p']:.0e}")
    dP_l, dS_l = d['dP_late'], d['dS_late']
    late = [int(y) for y in d['late_years']]
    a.scatter(dP_l.values / 1e3, dS_l.values, facecolor='none', edgecolor=S.ACCENT_ORANGE, s=22, zorder=4,
              lw=S.LW_THIN, label=f'{late[0]}–{late[-1] % 100:02d}: consent-derived, no census check')
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
    yh, ratio = d['ratio_years'], d['households_per_consent']
    a.bar(yh, ratio.values, color=[S.ACCENT_ORANGE if y > 2018 else S.MUTED for y in yh], width=0.8)
    for y in d['census_bases']:
        a.axvline(y + 0.5, color=S.INK, lw=S.LW_THIN, ls=':')
    a.set_ylabel('Households per consent')
    a.set_xlim(1991, 2026)
    a.set_ylim(0, 1.45)
    P.panel(a, 'b', 'Household growth per consent')
    a.legend(handles=[Patch(color=S.MUTED, label='census-benchmarked'),
                      Patch(color=S.ACCENT_ORANGE, label='2019 on: consent-derived')], loc='upper left', ncol=2,
             fontsize=S.FONT_MIN)

    a = ax[2]
    # history: one column per census interval (interval means; households census-anchored at both ends), the
    # consent-derived interval faint (v3: no hatch); projection annual, a gentle fade
    H = d['formation_history']
    gap = 0.5
    first = int(str(H['interval'].iloc[0])[:4])
    for r in H.itertuples():
        y0, y1 = int(str(r.interval)[:4]), int(r.year_end)
        est = r.households_from != 'census'
        comp_bars(a, [(y0 + y1) / 2 + 0.5], [('growth', r.from_population_growth_per_year / 1e3),
                                             ('smaller_households', r.from_household_size_change_per_year / 1e3)],
                  width=(y1 - y0) - gap, alpha=0.5 if est else 1.0)
        a.hlines(r.net_new_households_per_year / 1e3, y0 + 0.5 + gap / 2, y1 + 0.5 - gap / 2, color=S.INK, lw=S.LW,
                 ls=':' if est else '-', label='Net new households' if y0 == first else None)
    PF = d['projection_years']
    comp_bars(a, PF, [('growth', d['from_population_growth'] / 1e3),
                      ('smaller_households', d['from_household_size_change'] / 1e3)], width=0.82, alpha=0.75)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.plot(PF, d['net_new_households'] / 1e3, color=S.INK, lw=S.LW, ls='--')
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylabel('Households (thousand per year)')
    ys, ye = int(H['year_start'].iloc[-1]), int(H['year_end'].iloc[-1])
    a.legend(handles=comp_handles(['growth', 'smaller_households'])
             + [Patch(label=f'{ys}–{ye % 100:02d}: consent-derived estimates, no census check (faint)',
                      **dict(_fill('growth', 0.5), edgecolor='#555555', linewidth=S.LW_THIN))]
             + a.get_legend_handles_labels()[0] + sign_handles(), loc='upper left', fontsize=S.FONT_MIN)
    _y0, _y1 = a.get_ylim()
    a.set_ylim(_y0, _y1 + 0.62 * (_y1 - _y0))            # room for the legend above the columns
    P.panel(a, 'c', 'New households per year, by source')
    fig.tight_layout()
    S.save_figure(fig, fid, source=_src(fid), note=(
        'Between censuses households are consent-derived, so the relationship in a is partly mechanical (housing '
        f"supply meets migration). b: households per previous-year consent vary before 2019 and are {d['R19']} from "
        '2019: these years are estimated from consents and are not independent evidence. c: history one column per '
        'census interval (interval means; households census-anchored at both ends), stacked from population growth '
        f'and from household-size change; {ys}–{ye} faint (consent-derived estimates, no census check); projection '
        'annual, faded, from 2026; the line is the net of the two parts. A negative part (household-size change, '
        'where households grow larger) is drawn as an outlined segment hanging from the top of the stack, so each '
        'column ends at its net total (short tick).'))


# ---------------------------------------------------------------------------
# D05 stock and vacancy
# ---------------------------------------------------------------------------
HIST_IDS = ('new_households', 'vacancy', 'net_replacement_census', 'retirement_villages', 'unexplained_building')
FUT_IDS = ('new_households', 'vacancy', 'replacement', 'unconsented', 'redevelopment', 'retirement_villages',
           'overbuild_2026', 'overbuild_absorbed')


def d05():
    fid = 'D05_stock_and_vacancy'
    d = D.src(fid)
    FY, PF, YH = d['forecast_years'], d['projection_years'], d['years_hist_flows']
    census_y = [int(y) for y in d['census_years']]
    fig = plt.figure(figsize=S.figsize('double', 185))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.1], hspace=0.66, wspace=0.22)

    a = fig.add_subplot(gs[0, 0])
    vc = d['vacancy_consistent_knots']
    lo, hi = float(vc.min()), float(vc.max())
    a.axhspan(100 * lo, 100 * hi, color=S.BAND['vacancy'][0], alpha=0.12, lw=0,
              label=f'Census {int(vc.index.min())}–{int(vc.index.max())} range, one definition '
                    f'({100 * lo:.1f}–{100 * hi:.1f}%)')
    a.axvspan(2013, 2018, color=S.MUTED, alpha=0.10, lw=0, label='2013 → 2018 empty / away definition break')
    vp, vcm = d['vacancy_published_model'], d['vacancy_consistent_model']
    a.plot(vp.index, 100 * vp.values, color=S.INK, lw=S.LW, label='Published empty share (model)')
    a.plot(vcm.index, 100 * vcm.values, color=S.BAND['vacancy'][0], lw=S.LW, ls='-.',
           label='One definition: pooled 2018/2023 empty share')
    vf = d['vacancy_forward']
    a.plot(FY, np.full(len(FY), 100 * vf), color=S.INK, lw=S.LW_THIN, ls=':',
           label=f'Held at its published 2023 census value ({100 * vf:.2f}%)')
    a.plot(FY, 100 * d['vacancy_implied'], color=S.INK, lw=S.LW, ls='--',
           label='Implied: held rate + unabsorbed 2026 overbuild / stock')
    K = d['census_knots']
    for y, r in K.iterrows():
        filled = bool(r['measured'])
        a.scatter(y, 100 * r['vacancy'], s=12, zorder=5, color=S.ACCENT_ORANGE if filled else 'white',
                  edgecolor=S.ACCENT_ORANGE, lw=S.LW_THIN)
        a.scatter(y, 100 * r['all_unoccupied'], marker='x', color=S.MUTED, s=12, lw=S.LW_THIN)
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
    st = d['stock_hist']
    a.plot(st.index, st.values / M6, color=S.INK, lw=S.LW, label='Dwelling stock')
    P.history_estimated(a, d['households_hist'], int(d['S_ANCHOR_YEAR']), M6, color=S.ACCENT_ORANGE,
                        label='Households', k=d['hh_rebase_k'])
    a.plot(FY, d['stock_projection'] / M6, color=S.INK, lw=S.LW, ls='--',
           label='Stock, projection (incl. the unabsorbed 2026 overbuild)')
    a.plot(FY, d['households_projection'] / M6, color=S.ACCENT_ORANGE, lw=S.LW, ls='--',
           label='Households, projection')
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylabel('Dwellings or households (million)')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, ncol=1)
    P.panel(a, 'b', 'Stock = households / (1 − vacancy) + 2026 overbuild')

    a = fig.add_subplot(gs[1, :])
    SIH = d['stock_identity_history']
    for r in SIH.itertuples():                      # one bar per census interval; the latest (consents) faint
        y0, y1 = int(str(r.interval)[:4]), int(r.year_end)
        comp_bars(a, [y0 + 0.5 + (y1 - y0) / 2], [(c, getattr(r, f'{c}_per_year') / 1e3) for c in HIST_IDS],
                  width=y1 - y0, alpha=0.4 if y0 == census_y[-1] else 1.0)
    fut = d['projection_components']
    comp_bars(a, PF, [(c, fut[c] / 1e3) for c in FUT_IDS], width=0.82, alpha=0.55)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    for r in SIH.itertuples():                      # the unexplained building of each interval, labelled at
        m = r.unexplained_building_per_year / 1e3   # the end of the stack it extends (top if positive)
        vals = [getattr(r, f'{c}_per_year') / 1e3 for c in HIST_IDS]
        y = sum(v for v in vals if v > 0) if m >= 0 else sum(vals)        # negative: at the net total
        a.annotate(f'unexpl. {m:+.1f}k', ((int(str(r.interval)[:4]) + int(r.year_end)) / 2 + 0.5, y),
                   xytext=(0, 2 if m >= 0 else -2), textcoords='offset points', ha='center',
                   va='bottom' if m >= 0 else 'top', fontsize=S.FONT_MIN, color='#595959', zorder=7)
    a.text(1991.6, 0.02, '1986–91 not covered (calibration starts 1991)', transform=a.get_xaxis_transform(),
           fontsize=S.FONT_MIN, color=S.MUTED)
    a.plot(YH, d['dwellings_built_hist'].values / 1e3, color=S.INK, lw=S.LW,
           label='Dwellings built, in scope (observed, annual)')
    a.plot(PF, d['dwellings_built_projection'] / 1e3, color=S.INK, lw=S.LW, ls='--',
           label='Dwellings built, in scope (projection)')
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylabel('Dwellings (thousand per year)')
    _y0, _y1 = a.get_ylim()
    a.set_ylim(_y0 - 0.06 * (_y1 - _y0), _y1)          # room for the labels of the negative interval means
    P.panel(a, 'c', 'Dwellings per year by component')
    a.legend(handles=comp_handles(['new_households', 'vacancy', 'net_replacement_census', 'replacement',
                                   'redevelopment', 'overbuild_2026', 'unexplained_building'])
             + comp_handles(['unconsented', 'retirement_villages', 'overbuild_absorbed'],
                            negative=('unconsented', 'retirement_villages', 'overbuild_absorbed'))
             + a.get_legend_handles_labels()[0] + sign_handles(),
             loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=3, fontsize=S.FONT_MIN)
    V = d['vacancy_wording']
    hist_note = (f'History: one bar per census interval (interval means; vacancy on one definition, the pooled '
                 f"2018/2023 empty share, {100 * d['pooled_share']:.1f}% of unoccupied dwellings); between censuses "
                 f'annual detail is not identified. Faint bar: {census_y[-1] + 1}–{int(YH[-1])}, households '
                 'consent-derived. Projection annual, lighter.')
    S.save_figure(fig, fid, source=_src(fid), note=(
        f'a: {V[0].upper() + V[1:]}. c: {hist_note} History: net replacement is census-measured, the '
        'rate of the census dwelling-count identity of each interval (D07; under-construction corrected) x the '
        f"previous year's stock, the quantity the model uses ({census_y[-1] + 1}–{int(YH[-1])}: the latest rate "
        'carried). Projection: demolition replacement, unconsented additions (negative), the recent replacement '
        'surge, retirement villages (negative), the 2026 overbuild and the overbuild absorbed '
        '(negative payback). Negative parts are outlined, hanging from the top of the positive stack; each bar ends '
        'at its net total (tick). Unexplained building (faded red, labelled per interval in thousand dwellings per '
        'year): building not explained by household formation, vacancy and census-measured replacement: '
        'redevelopment not captured by the census counts, error in the household estimates, or residual; it may be '
        'negative.'))


# ---------------------------------------------------------------------------
# D06 vacancy definition
# ---------------------------------------------------------------------------
def d06():
    fid = 'D06_vacancy_definition'
    d = D.src(fid)
    fig, a = plt.subplots(figsize=S.figsize('single', 66))
    vals = [d['unconsented_empty_only'], d['unconsented_including_away']]
    nb = d['mean_dwellings_built']
    bb_ = a.bar(['Empty homes only\n(used)', "Including 'residents away'\n(rejected)"], vals,
                color=[S.BAND['vacancy'][0], S.MUTED], width=0.6)
    for bb, v in zip(bb_, vals):
        a.text(bb.get_x() + bb.get_width() / 2, v / 2, f'{v:,.0f} per year\n({100 * v / nb:+.0f}% of building)',
               ha='center', va='center', fontsize=S.FONT_SMALL, color='white', fontweight='bold')
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.set_ylabel(f"Unconsented additions required, 1992–{int(d['calib_end'])}\n(dwellings per year)")
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    fig.tight_layout()
    S.save_figure(fig, fid, source=_src(fid), note=(
        'The unconsented additions each vacancy definition requires to close the stock identity, assuming the BRANZ '
        'demolition rate; counting residents-away dwellings as vacant requires implausibly many.'))


# ---------------------------------------------------------------------------
# D08, D09: dwelling space, cumulative floor area
# ---------------------------------------------------------------------------
def d08():
    fid = 'D08_dwelling_space'
    d = D.src(fid)
    yh = d['years_hist']
    real, occ, util = (d[k].values for k in ('realised_dwelling_size', 'occupied_area_per_dwelling', 'utilisation'))
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 66))
    a.plot(yh, real, color=S.INK, label='Realised new-dwelling size (floor area / consents)')
    a.plot(yh, occ, color=S.MUTED, ls='-.', label='Occupied area per dwelling (household size × occupant load factor)')
    a.fill_between(yh, occ, real, color=S.BAND['extra_space'][0], alpha=0.25, lw=0,
                   label='Space above occupancy (under-utilisation)')
    a.set_xlim(yh[0], yh[-1])
    a.set_ylim(0, None)
    a.set_ylabel('Floor area per dwelling (m²)')
    a.legend(loc='lower left', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'New dwellings: realised and occupied floor area')
    b.plot(yh, 100 * util, color=S.INK)
    b.axhline(100, color=S.MUTED, lw=S.LW_THIN)
    b.text(yh[0] + 1, 101, 'design capacity (bedrooms + 1)', fontsize=S.FONT_SMALL, color=S.MUTED, va='bottom')
    b.set_xlim(yh[0], yh[-1])
    b.set_ylim(0, 110)
    b.set_ylabel('Occupancy utilisation: household size / design capacity (%)')
    P.panel(b, 'b', 'Occupancy utilisation of new dwellings')
    fig.tight_layout()
    S.save_figure(fig, fid, source=_src(fid))


def d09():
    fid = 'D09_cumulative_floor_area'
    d = D.src(fid)
    yh, fy = d['years_hist'], d['forecast_years']
    fig, ax = plt.subplots(figsize=S.figsize('double', 66))
    ax.plot(yh, d['cumulative_floor_area_hist'].values / M6, color=S.INK,
            label=(f"History (completions = consents lagged {int(d['lag_months'])} months × {d['built_factor']:.3f})"
                   if int(d.get('lag_months', 0) or 0) else
                   f"History (consents timed as completions × {d['built_factor']:.2f}, completion lag weight "
                   f"{d['lag_w']:.2f})"))
    _band(ax, fy, d['cumulative_floor_area_5th'] / M6, d['cumulative_floor_area_95th'] / M6,
          'Population 5th–95th percentile (other inputs at the Reference)')
    ax.plot(d['projection_years'], d['cumulative_floor_area_50th'] / M6, label='Reference projection', **_ref())
    P.split(ax)
    ax.set_xlim(yh[0], fy[-1])
    ax.set_ylim(0, None)
    ax.set_ylabel('Floor area, cumulative from 1991 (Mm²)')
    ax.legend(loc='upper left')
    S.save_figure(fig, fid, source=_src(fid))


# ---------------------------------------------------------------------------
# D13 carbon by material
# ---------------------------------------------------------------------------
def d13():
    fid = 'D13_carbon_by_material'
    d = D.src(fid)
    py = d['years']
    fa, fc = d['carbon_annual'], d['carbon_cumulative']
    P.nonnegative('material carbon', fa.values, fc.values)
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    handles = P.stack_materials(a, py, fa, 1e6)
    P.stack_materials(b, py, fc, 1e6)
    for ax_, letter, title, ylab in ((a, 'a', 'Annual', 'Embodied carbon (kt CO₂e per year)'),
                                    (b, 'b', 'Cumulative from 2026', 'Embodied carbon, cumulative from 2026 (kt CO₂e)')):
        ax_.set_xlim(py[0], py[-1])
        ax_.set_ylabel(ylab)
        P.thousands(ax_.yaxis)
        P.panel(ax_, letter, title)
    fig.legend(handles=handles, loc='lower center', ncol=len(handles), bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    acc = ('construction (A1–A5 and soil) plus maintenance (B2, B4) within 2026–2050' if d['time_resolved'] else
           'whole life booked at construction')
    S.save_figure(fig, fid, note=f'Reference, {acc}; each material includes its maintenance.', source=_src(fid))


# ---------------------------------------------------------------------------
# D35 overbuild absorption (new in MODEL v3.0.0)
# ---------------------------------------------------------------------------
def d35():
    fid = 'D35_overbuild_absorption'
    rel = 'baseline/overbuild_absorption_log.csv'
    L = D.csv(rel)
    y = L['year'].to_numpy(int)
    exc, paid = L['excess_dwellings'].to_numpy(float), L['payback_paid'].to_numpy(float)
    w, U = L['absorption_weight'].to_numpy(float), L['surplus_vacant'].to_numpy(float)
    fig = plt.figure(figsize=S.figsize('double', 92))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.6, 1], hspace=0.12, wspace=0.28)
    a = fig.add_subplot(gs[0, 0])
    a2 = fig.add_subplot(gs[1, 0], sharex=a)
    b = fig.add_subplot(gs[:, 1])
    # a: dwellings per year: market 2026 overbuild up, payback paid (negative) outlined hanging from the top of the overbuild
    P.bars_cumulative(a, y, [('overbuild_2026', exc / 1e3), ('overbuild_absorbed', -paid / 1e3)], width=0.8,
                      net=(exc - paid) / 1e3)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    _lo, _hi = min(0.0, float(np.min(exc - paid)) / 1e3), float(np.max(exc)) / 1e3
    a.set_ylim(_lo - 0.08 * (_hi - _lo), _hi + 0.08 * (_hi - _lo))
    a.set_ylabel('Dwellings per year (thousand)')
    a.tick_params(labelbottom=False)
    a.legend(handles=[Patch(label='2026 overbuild (building above the requirement)',
                            **dict(P.band_style('overbuild_2026'), edgecolor='#555555', linewidth=S.LW_THIN)),
                      Patch(label='Payback paid (overbuild absorbed, negative)', **P.negative_bar_style('overbuild_absorbed')),
                      Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label='Net (2026 overbuild − payback)')],
             loc='upper right', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'The 2026 overbuild, its payback and the surplus still vacant')
    # a (lower): surplus still vacant U and the absorption weight w
    a2.plot(y, U / 1e3, color=S.BAND['overbuild_2026'][0], lw=S.LW, label='Surplus still vacant U (thousand dwellings)')
    a2.set_ylabel('U (thousand dwellings)')
    a2.set_ylim(0, None)
    w_ax = a2.twinx()
    w_ax.plot(y, w, color=S.INK, lw=S.LW_THIN, ls='--', label='Absorption weight w (right axis)')
    w_ax.set_ylim(0, 1.05)
    w_ax.set_ylabel('w')
    w_ax.grid(False)
    w_ax.spines['right'].set_visible(True)
    a2.legend(handles=a2.get_legend_handles_labels()[0] + w_ax.get_legend_handles_labels()[0], loc='center right',
              fontsize=S.FONT_MIN)
    a2.set_xlim(y[0] - 0.6, y[-1] + 0.6)
    # b: implied vacancy against the vacancy parameter
    vp = L['vacancy_parameter'].to_numpy(float)
    b.plot(y, 100 * L['implied_vacancy'].to_numpy(float), color=S.INK, lw=S.LW, ls='--',
           label='Implied vacancy 1 − households / (stock + U)')
    b.plot(y, 100 * vp, color=S.BAND['vacancy'][0], lw=S.LW,
           label=f'Vacancy parameter ({100 * vp[-1]:.2f}%, the published 2023 census value)')
    b.set_xlim(2025, 2050)
    b.set_ylabel('Vacancy rate (% of private dwellings)')
    b.legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel(b, 'b', 'Implied vacancy and the vacancy parameter')
    done = y[np.argmax(w >= 1 - 1e-9)] if np.any(w >= 1 - 1e-9) else None
    S.save_figure(fig, fid, source=[rel], note=(
        'Reference, median population path (engine.absorb_overbuild). a: the 2026 overbuild, building above the '
        'requirement (positive), and the payback paid by building less (negative, outlined, hanging from the '
        'top of the overbuild; tick = net); below, the surplus still vacant U and the absorption weight w. '
        + (f'The overbuild is absorbed by {done} along the logistic (w = 1); ' if done is not None else
           'The absorption weight does not reach 1 within 2050; ')
        + 'once absorbed, the remaining 2026 overbuild is paid back in the same year (net 0, the ticks on the zero '
        'line). b: the unabsorbed surplus raises implied vacancy temporarily, which returns to the vacancy parameter once '
        'it is absorbed. The speed of absorption is bracketed by sensitivity (never absorbed, absorbed by 2030, '
        'by 2045).'))


FIGURES = {'D01_population': d01, 'D02_households': d02, 'D03_household_size': d03,
           'D04_household_formation': d04, 'D05_stock_and_vacancy': d05, 'D06_vacancy_definition': d06,
           'D08_dwelling_space': d08, 'D09_cumulative_floor_area': d09, 'D13_carbon_by_material': d13,
           'D35_overbuild_absorption': d35}
