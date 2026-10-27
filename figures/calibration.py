"""Calibration figures (MODEL v4.3.0: Supplementary SF1, SF2, SF4; outputs/supplementary/calibration/).

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
        'net_replacement_census': ('Net replacement, history (census dwelling counts; parts not separable)',
                                   S.DISPLAY_BAND['net_replacement'], None),      # MODEL v4.3.1: palette key
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
# SF1 (MODEL v4.3.0; D02 + D04 a, b): households
# ---------------------------------------------------------------------------
def sf1_households():
    """(a) households: Stats NZ estimates as published, the census-benchmarked history, the 2019-23 estimates scaled to
    the 2023 census, the projection (population / household size) with the 5th-95th population percentile; (b) change
    in household size against population growth (census-benchmarked years, the consent-derived 2024-25 marked);
    (c) households per consent by year (census-benchmarked; consent-derived from 2019)."""
    d2 = D.src('D02_households')
    d4 = D.src('D04_household_formation')
    yh, fy, anchor, k = d2['years_hist'], d2['forecast_years'], int(d2['S_ANCHOR_YEAR']), d2['hh_rebase_k']
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 100), gridspec_kw={'width_ratios': [1.3, 1, 1]})
    a = ax[0]
    dhe = d2['households_dhe_published']
    P.line(a, dhe.index, dhe.values / M6, color=S.MUTED, lw=S.LW_THIN, label='Stats NZ household estimates as published')
    P.history_estimated(a, d2['households_hist'], anchor, M6, label='History (31 Dec)', k=k)
    lo, hi = d2['households_5th'] / M6, d2['households_95th'] / M6
    xf, lof, hif, _ = P.pchip_band(fy, lo, (lo + hi) / 2, hi, P.series_breaks(), name='SF1a households 5-95')
    a.fill_between(xf, lof, hif, label='5th–95th population percentile (household size fixed)', **S.MC_BAND)
    P.line(a, d2['projection_years'], d2['projection_households'] / M6,
           label='Projection: population / household size, median', **_ref())
    P.split(a)
    a.set_xlim(yh[0], fy[-1])
    a.set_ylabel('Households (million)')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), fontsize=S.FONT_MIN, ncol=1, frameon=False)
    P.panel(a, 'a', 'Households')
    a = ax[1]
    dP, dS, yf, fit = d4['dP_fit'], d4['dS_fit'], d4['years_fit'], d4['fit']
    a.scatter(dP / 1e3, dS, color=S.MUTED, s=10, zorder=3, label=f'{int(yf[0])}–{int(yf[-1])} (census-benchmarked)')
    xx = np.linspace(dP.min(), dP.max(), 50)
    a.plot(xx / 1e3, fit['intercept'] + fit['slope'] * xx, color=S.INK, lw=S.LW,
           label=f"r = {fit['r']:+.2f}, p = {fit['p']:.0e}")
    dP_l, dS_l = d4['dP_late'], d4['dS_late']
    late = [int(y) for y in d4['late_years']]
    marks = ('o', 's', 'D', '^')
    assert len(late) <= len(marks), late
    for y, mk in zip(late, marks):        # MODEL v4.3.0: one hollow marker per year, named in the legend (no in-plot text)
        a.scatter([dP_l[y] / 1e3], [dS_l[y]], facecolor='none', edgecolor=S.ACCENT_ORANGE, s=22, zorder=4,
                  marker=mk, lw=S.LW_THIN, label=f'{y}: consent-derived, no census check')
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.set_xlabel('Population growth (thousand per year)')
    a.set_ylabel('Change in household size (persons per household)')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.14), fontsize=S.FONT_MIN, frameon=False)
    P.panel(a, 'b', 'Household size vs population growth')

    a = ax[2]
    yh, ratio = d4['ratio_years'], d4['households_per_consent']
    a.bar(yh, ratio.values, color=[S.ACCENT_ORANGE if y > 2018 else S.MUTED for y in yh], width=0.8)
    for y in d4['census_bases']:
        a.axvline(y + 0.5, color=S.INK, lw=S.LW_THIN, ls=':')
    a.set_ylabel('Households per consent')
    a.set_xlim(1991, 2026)
    a.set_ylim(0, 1.75)                                                # room for the legend
    P.panel(a, 'c', 'Households per consent')
    a.legend(handles=[Patch(color=S.MUTED, label='census-benchmarked'),
                      Patch(color=S.ACCENT_ORANGE, label='2019 on: consent-derived')], loc='upper left', ncol=2,
             fontsize=S.FONT_MIN, framealpha=1, facecolor='white', edgecolor='none')   # over the census lines

    fig.tight_layout()
    S.save_figure(fig, 'SF1_households', source=['figure_source/D02_households.json',
                                                 'figure_source/D04_household_formation.json'], note=(
        f'a: projection from the {anchor} census point; 2019–23 Stats NZ estimates scaled to the {anchor} census '
        f'(×{k:.3f}). b, c: between censuses households are consent-derived, so the relationship in b is partly '
        'mechanical (housing supply meets migration) and the 2019 on ratios in c are estimated from consents, not '
        'independent evidence.'))


# ---------------------------------------------------------------------------
# SF2 (MODEL v4.3.0; D05 + D06 as panel d): stock and vacancy
# ---------------------------------------------------------------------------
HIST_IDS = ('new_households', 'vacancy', 'net_replacement_census', 'retirement_villages', 'unexplained_building')
FUT_IDS = ('new_households', 'vacancy', 'replacement', 'unconsented', 'redevelopment', 'retirement_villages',
           'overbuild_2026', 'overbuild_absorbed')


def sf2_stock_vacancy():
    fid = 'SF2_stock_vacancy'
    d = D.src('D05_stock_and_vacancy')
    d6 = D.src('D06_vacancy_definition')
    FY, PF, YH = d['forecast_years'], d['projection_years'], d['years_hist_flows']
    census_y = [int(y) for y in d['census_years']]
    fig = plt.figure(figsize=S.figsize('double', 185))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.1], width_ratios=[1, 1, 1, 0.85], hspace=0.66, wspace=0.75)

    a = fig.add_subplot(gs[0, :2])
    vc = d['vacancy_consistent_knots']
    lo, hi = float(vc.min()), float(vc.max())
    a.axhspan(100 * lo, 100 * hi, color=S.BAND['vacancy'][0], alpha=0.12, lw=0,
              label=f'Census {int(vc.index.min())}–{int(vc.index.max())} range, one definition '
                    f'({100 * lo:.1f}–{100 * hi:.1f}%)')
    a.axvspan(2013, 2018, color=S.MUTED, alpha=0.10, lw=0, label='2013 → 2018 empty / away definition break')
    vp, vcm = d['vacancy_published_model'], d['vacancy_consistent_model']
    P.line(a, vp.index, 100 * vp.values, color=S.INK, lw=S.LW, label='Published empty share (model)')
    P.line(a, vcm.index, 100 * vcm.values, color=S.BAND['vacancy'][0], lw=S.LW, ls='-.',
           label='One definition: pooled 2018/2023 empty share')
    vf = d['vacancy_forward']
    a.plot(FY, np.full(len(FY), 100 * vf), color=S.INK, lw=S.LW_THIN, ls=':',
           label=f'Held at its published 2023 census value ({100 * vf:.2f}%)')
    P.line(a, FY, 100 * d['vacancy_implied'], color=S.INK, lw=S.LW, ls='--',
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

    a = fig.add_subplot(gs[0, 2:])
    st = d['stock_hist']
    P.line(a, st.index, st.values / M6, color=S.INK, lw=S.LW, label='Dwelling stock')
    P.history_estimated(a, d['households_hist'], int(d['S_ANCHOR_YEAR']), M6, color=S.ACCENT_ORANGE,
                        label='Households', k=d['hh_rebase_k'])
    P.line(a, FY, d['stock_projection'] / M6, color=S.INK, lw=S.LW, ls='--',
           label='Stock, projection (incl. the unabsorbed 2026 overbuild)')
    P.line(a, FY, d['households_projection'] / M6, color=S.ACCENT_ORANGE, lw=S.LW, ls='--',
           label='Households, projection')
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylabel('Dwellings or households (million)')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, ncol=1)
    P.panel(a, 'b', 'Stock = households / (1 − vacancy) + 2026 overbuild')

    # (d) MODEL v4.3.0 (D06): the unconsented additions each vacancy definition requires
    a = fig.add_subplot(gs[1, 3])
    vals = [d6['unconsented_empty_only'], d6['unconsented_including_away']]
    nb = d6['mean_dwellings_built']
    bb_ = a.bar([0, 1], vals, color=[S.BAND['vacancy'][0], S.MUTED], width=0.6)
    a.set_ylim(min(vals) * 1.25, 0)
    for bb, v in zip(bb_, vals):
        a.text(bb.get_x() + bb.get_width() / 2, v, f'{v:,.0f}\n({100 * v / nb:+.0f}%)', ha='center', va='top',
               fontsize=S.FONT_MIN, color=S.INK)
    a.set_xticks([0, 1])
    a.set_xticklabels(['Empty\nonly\n(used)', "With 'away'\n(rejected)"], fontsize=S.FONT_MIN)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.set_ylabel(f"Unconsented additions required\n1992–{int(d6['calib_end'])} (per year)", fontsize=S.FONT_SMALL)
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'd', 'Vacancy definition')

    a = fig.add_subplot(gs[1, :3])
    SIH = d['stock_identity_history']
    for r in SIH.itertuples():                      # one bar per census interval; the latest (consents) faint
        y0, y1 = int(str(r.interval)[:4]), int(r.year_end)
        comp_bars(a, [y0 + 0.5 + (y1 - y0) / 2], [(c, getattr(r, f'{c}_per_year') / 1e3) for c in HIST_IDS],
                  width=y1 - y0, alpha=0.4 if y0 == census_y[-1] else 1.0)
    fut = d['projection_components']
    comp_bars(a, PF, [(c, fut[c] / 1e3) for c in FUT_IDS], width=0.82, alpha=0.55)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    # MODEL v4.3.0: the unexplained building of each interval as one row of values at the top of the panel (thousand
    # dwellings per year), above every bar, so no label sits on a bar
    for r in SIH.itertuples():
        m = r.unexplained_building_per_year / 1e3
        a.text((int(str(r.interval)[:4]) + int(r.year_end)) / 2 + 0.5, 0.965, f'{m:+.1f}',
               transform=a.get_xaxis_transform(), ha='center', va='top', fontsize=S.FONT_MIN, color='#595959')
    a.text(1991.6, 0.02, '1986–91 not covered (calibration starts 1991)', transform=a.get_xaxis_transform(),
           fontsize=S.FONT_MIN, color=S.MUTED)
    P.line(a, YH, d['dwellings_built_hist'].values / 1e3, color=S.INK, lw=S.LW,
           label='Dwellings built, in scope (observed, annual)')
    P.line(a, PF, d['dwellings_built_projection'] / 1e3, color=S.INK, lw=S.LW, ls='--',
           label='Dwellings built, in scope (projection)')
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylabel('Dwellings (thousand per year)')
    _y0, _y1 = a.get_ylim()
    a.set_ylim(_y0 - 0.06 * (_y1 - _y0), _y1 + 0.08 * (_y1 - _y0))   # room for the row of unexplained values
    P.panel(a, 'c', 'Dwellings per year by component (top row: unexplained building, thousand per year)')
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
    S.save_figure(fig, fid, source=['figure_source/D05_stock_and_vacancy.json',
                                    'figure_source/D06_vacancy_definition.json'], note=(
        f'a: {V[0].upper() + V[1:]}. d: the unconsented additions each vacancy definition requires to close the stock '
        'identity (BRANZ demolition rate); counting residents-away dwellings as vacant requires implausibly many. '
        f'c: {hist_note} History: net replacement is census-measured, the '
        'rate of the census dwelling-count identity of each interval (SF3; under-construction corrected) x the '
        f"previous year's stock, the quantity the model uses ({census_y[-1] + 1}–{int(YH[-1])}: the latest rate "
        'carried). Projection: demolition replacement, unconsented additions (negative), the recent replacement '
        'surge, retirement villages (negative), the 2026 overbuild and the overbuild absorbed '
        '(negative payback). Negative parts are outlined, hanging from the top of the positive stack; each bar ends '
        'at its net total (tick). Unexplained building (faded red; its value per interval in the row at the top, '
        'thousand dwellings per year): building not explained by household formation, vacancy and census-measured replacement: '
        'redevelopment not captured by the census counts, error in the household estimates, or residual; it may be '
        'negative.'))


# ---------------------------------------------------------------------------
# SF4 (MODEL v4.3.0; D08 + the consent sizes of the former SF6): new-dwelling size
# ---------------------------------------------------------------------------
def sf4_dwelling_size():
    """(a) realised and occupied floor area per new dwelling; (b) occupancy utilisation of new dwellings; (c) mean
    consented new-dwelling size by typology 1990-2025 with the minima (L4) and the Reference size."""
    d = D.src('D08_dwelling_space')
    p = D.js('pathways/levers.json')['L4']
    yh = d['years_hist']
    real, occ, util = (d[k].values for k in ('realised_dwelling_size', 'occupied_area_per_dwelling', 'utilisation'))
    fig, (a, b, c) = plt.subplots(1, 3, figsize=S.figsize('double', 72))
    P.line(a, yh, real, color=S.INK, label='Realised new-dwelling size (floor area / consents)')
    P.line(a, yh, occ, color=S.MUTED, ls='-.', label='Occupied area per dwelling (household size × occupant load factor)')
    xf, rf = P.pchip(np.asarray(yh, float), np.asarray(real, float))
    _, of = P.pchip(np.asarray(yh, float), np.asarray(occ, float))
    a.fill_between(xf, of, rf, color=S.BAND['extra_space'][0], alpha=0.25, lw=0,
                   label='Space above occupancy (under-utilisation)')
    a.set_xlim(yh[0], yh[-1])
    a.set_ylim(0, None)
    a.set_ylabel('Floor area per dwelling (m²)')
    a.legend(loc='lower left', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'Realised and occupied floor area')
    P.line(b, yh, 100 * util, color=S.INK)
    b.axhline(100, color=S.MUTED, lw=S.LW_THIN)
    b.text(yh[0] + 1, 101, 'design capacity (bedrooms + 1)', fontsize=S.FONT_MIN, color=S.MUTED, va='bottom')
    b.set_xlim(yh[0], yh[-1])
    b.set_ylim(0, 110)
    b.set_ylabel('Household size / design capacity (%)')
    P.panel(b, 'b', 'Occupancy utilisation')
    for t, ser in p['consent_size_series'].items():
        yrs = sorted(int(y) for y in ser)
        m = p['minima'][t]
        P.line(c, yrs, [ser[str(y)] for y in yrs], color=S.TYPOLOGY[t],
               label=f"{t} (min {m['size_min']:.0f} m², {m['year']})")
        c.plot([m['year']], [m['size_min']], 'o', color=S.TYPOLOGY[t], ms=4)
        c.axhline(p['size_ref'][t], color=S.TYPOLOGY[t], lw=S.LW_THIN, ls=':')
    c.set_ylabel('Mean consented new-dwelling size (m²)')
    c.legend(fontsize=S.FONT_MIN, loc='upper center', ncol=1, frameon=False)
    c.set_ylim(78, 275)
    P.panel(c, 'c', 'Consented size by typology')
    fig.tight_layout()
    S.save_figure(fig, 'SF4_dwelling_size', source=['figure_source/D08_dwelling_space.json', 'pathways/levers.json'],
                  note='c: dotted, the Reference size (2023-2025 mean); dots, the smallest annual mean (the L4 minima). '
                       '1990 is the first year of the series and a recession year.')


FIGURES = {'SF1_households': sf1_households, 'SF2_stock_vacancy': sf2_stock_vacancy,
           'SF4_dwelling_size': sf4_dwelling_size}
