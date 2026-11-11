"""Calibration figures (Supplementary SF1, SF2, SF4; outputs/supplementary/calibration/).

Drawn from data files only (compute / draw separation): the figure source written by projection.py
(D01-D03, D08, D09, D13; export_figure_sources) and Diagnostics.py (D04-D06), and baseline/overbuild_absorption_log.csv
(D35). SF2b in the Fig1 layout: positive components stacked up from zero and negative components
stacked down from zero, every part a solid fill (no outlines, hatching or fades), checked against its net.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
# components of SF2b (D05)
# ---------------------------------------------------------------------------
# component id -> (label, colour). A component that IS a demand band takes the [demand_bands] key
# (vacancy; net replacement in the history and demolition replacement in the projection; the 2026 overbuild = market
# balance); the others palette.toml [components]. Every part is a solid fill: no hatch (the surge too), no fade.
COMP = {'new_households': ('New households', S.NEW_HOUSEHOLDS),
        'vacancy': ('Vacancy (allowance and change)', S.BAND['vacancy'][0]),
        # net replacement: one band, the same quantity and colour in the history (census-measured) and the
        # projection (demolition replacement + recent surge + unconsented additions, merged; Fig1)
        'net_replacement_census': ('Net replacement', S.DISPLAY_BAND['net_replacement']),
        'net_replacement': ('Net replacement', S.DISPLAY_BAND['net_replacement']),
        'retirement_villages': (N.BAND_DETAIL['retirement_villages'], S.RETIREMENT_VILLAGES),
        'overbuild_2026': (N.BANDS['overbuild_2026'], S.BAND['overbuild_2026'][0]),
        # the absorption pays back the F1 starting surplus (2024-2025) and the 2026 overbuild
        'overbuild_absorbed': ('Surplus absorbed (2024–25 surplus + 2026 overbuild)', S.BAND['overbuild_absorbed'][0]),
        'unexplained_building': ('Unexplained building', S.UNEXPLAINED[0]),
        # the unexplained building of the years after the last census is the F1 starting surplus carried into 2026:
        # the same face, a light hatch
        'surplus_2425': ('2024–25 surplus (carried into 2026)', S.UNEXPLAINED[0])}
COMP_STYLE = {c: S.fill(col) for c, (_, col) in COMP.items()}           # solid, edge = face at LW_SEAM
COMP_STYLE['surplus_2425'] = S.fill(S.UNEXPLAINED[0], '////', S.HATCH_COLOUR)


# ---------------------------------------------------------------------------
# SF1 (D02 + D04 a, b): households
# ---------------------------------------------------------------------------
def sf1_households():
    """(a) households: Stats NZ estimates as published, the census-benchmarked history, the 2019-23 estimates scaled to
    the 2023 census, the projection (population / household size) with the 5th-95th population percentile; (b) change
    in household size against population growth (census-benchmarked years; 2024-25 marked: households
    there are ERP / the model's household-size path, so their change in household size is the model's path,
    not an observation). panel (c), households per consent, dropped (tests/test_households_per_consent.py:
    the Stats NZ estimates grow by 0.888 x the previous year's consents in 2019-2025)."""
    d2 = D.src('D02_households')
    d4 = D.src('D04_household_formation')
    yh, fy, anchor, k = d2['years_hist'], d2['forecast_years'], int(d2['S_ANCHOR_YEAR']), d2['hh_rebase_k']
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 100), gridspec_kw={'width_ratios': [1.3, 1]})
    a = ax[0]
    dhe = d2['households_dhe_published']
    # history: straight segments between the annual values (observed data, not smoothed); after the 2023 census the
    # households are population / the model's household size, drawn as the projection line from the census point
    a.plot(dhe.index, dhe.values / M6, color=S.MUTED, lw=S.LW_THIN,
           label='Stats NZ household estimates as published (2018 Census base)')
    P.history_estimated(a, d2['households_hist'], anchor, M6, label='History (31 Dec)', k=k, straight=True,
                        tail=False)
    lo, hi = d2['households_5th'] / M6, d2['households_95th'] / M6
    xf, lof, hif, _ = P.pchip_band(fy, lo, (lo + hi) / 2, hi, P.series_breaks(), name='SF1a households 5-95')
    a.fill_between(xf, lof, hif, label='5th–95th population percentile with Low A – High A household size '
                                       '(household size moves with population)', **S.MC_BAND)
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
    for y, mk in zip(late, marks):        # one hollow marker per year, named in the legend (no in-plot text)
        a.scatter([dP_l[y] / 1e3], [dS_l[y]], facecolor='none', edgecolor=S.MODEL_PATH_YEARS, s=22, zorder=4,
                  marker=mk, lw=S.LW_THIN, label=f"{y}: the model's household-size path (households = ERP / S), "
                                                   'not observed')
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.set_xlabel('Population growth (thousand per year)')
    a.set_ylabel('Change in household size (persons per household)')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.14), fontsize=S.FONT_MIN, frameon=False)
    P.panel(a, 'b', 'Household size vs population growth')

    fig.tight_layout()
    S.save_figure(fig, 'SF1_households', source=['figure_source/D02_households.json',
                                                 'figure_source/D04_household_formation.json'], note=(
        f'a: projection from the {anchor} census point; 2019–23 Stats NZ estimates scaled to the {anchor} census '
        f'(×{k:.3f}); 2024–2025: households = population / household size (model), on the projection line. The band: '
        'the 5th / 95th population percentile paths with the Stats NZ Low A / High A household size (households '
        'computed per path). b: between censuses households are consent-derived, so the relationship is partly '
        'mechanical (housing supply meets migration); 2024-25 are the model household-size path (ERP / S), not '
        'observations.'))


# ---------------------------------------------------------------------------
# SF2 (D05 + D06 as panel d): stock and vacancy
# ---------------------------------------------------------------------------
HIST_IDS = ('new_households', 'vacancy', 'net_replacement_census', 'retirement_villages', 'unexplained_building')
FUT_IDS = ('new_households', 'vacancy', 'net_replacement', 'retirement_villages', 'overbuild_2026', 'overbuild_absorbed')
NET_REPLACEMENT_PARTS = ('replacement', 'redevelopment', 'unconsented')   # merged into 'net_replacement' (D05 parts)
SF2B_LEGEND = ('new_households', 'vacancy', 'net_replacement_census', 'net_replacement', 'overbuild_2026',
               'unexplained_building', 'retirement_villages', 'overbuild_absorbed')
SF2B_RTOL = 1e-9


def sf2b_columns():
    """The SF2b columns and line from the committed figure source (D05), in the Fig1 layout (the same gap
    rule, paper_main.FIG1_GAP): one column per census interval, the pipeline years as annual columns, the projection
    from the year after as annual areas. Each column / year carries its signed parts, its net (the sum of the parts),
    and up / down (the positive and negative sums). The line is the annual dwellings built (in scope), observed
    1992-2025 then the projection. Checks (STOP): the interval mean of the annual line equals the column net of every
    census interval (rtol 1e-9); the line equals the net of every projection year after the pipeline (rtol 1e-9).
    The pipeline years (author decision): the line is the sum of the components, the stock-identity
    count (observed all-category building less the modelled retirement-village share), the dwellings that join the
    stock. D05's dwellings_built_projection there is the in-scope floor area / the dwelling size held at its
    2023-2025 mean, which differs because the pipeline floor area is observed while the size is held; the difference
    is returned ('pipeline_floor_count') and quoted in the note."""
    from figures.paper_main import FIG1_GAP
    d = D.src('D05_stock_and_vacancy')
    pipe = [int(y) for y in D.js('baseline/overbuild_2026.json')['pipeline_years']]
    SIH = d['stock_identity_history']
    line_h = d['dwellings_built_hist']
    PF = np.asarray(d['projection_years'], int)
    pc = d['projection_components']
    fut = {c: np.asarray(pc[c], float) for c in FUT_IDS if c != 'net_replacement'}
    # the projection's net replacement as one band: demolition replacement + recent surge + unconsented additions
    parts = np.vstack([np.asarray(pc[c], float) for c in NET_REPLACEMENT_PARTS])
    fut['net_replacement'] = parts.sum(axis=0)
    for k in range(parts.shape[1]):                   # per year: the merged band is the sum of its three parts
        s = sum(float(pc[c][k]) for c in NET_REPLACEMENT_PARTS)
        if not np.isclose(fut['net_replacement'][k], s, rtol=1e-12, atol=1e-9):
            raise SystemExit(f'STOP: SF2b: the merged net replacement of {int(PF[k])} ({fut["net_replacement"][k]!r}) '
                             f'differs from the sum of its parts ({s!r}).')
    known = set(FUT_IDS) | set(NET_REPLACEMENT_PARTS)
    if set(pc) - known:
        raise SystemExit(f'STOP: SF2b: projection components not drawn: {sorted(set(pc) - known)}')
    line_f = pd.Series(np.asarray(d['dwellings_built_projection'], float), index=PF)
    hist = []
    for r in SIH.itertuples():
        y0, y1 = int(r.year_start), int(r.year_end)
        a_, b_ = y0 - 0.5, y1 + 0.5
        w = b_ - a_
        parts = {c: float(getattr(r, f'{c}_per_year')) for c in HIST_IDS}
        net = float(sum(parts.values()))
        mean = float(line_h.loc[y0:y1].mean())
        if not np.isclose(mean, net, rtol=SF2B_RTOL, atol=0.0):
            raise SystemExit(f'STOP: SF2b: the mean of the annual dwellings built {y0}-{y1} ({mean!r}) differs from '
                             f'the column net ({net!r}).')
        hist.append(dict(x=(a_ + FIG1_GAP / 2 * w, b_ - FIG1_GAP / 2 * w), centre=(y0 + y1) / 2, years=(y0, y1),
                         parts=parts, net=net, line_mean=mean, up=sum(v for v in parts.values() if v > 0),
                         down=sum(v for v in parts.values() if v < 0)))
    g = FIG1_GAP / 2
    annual = []
    floor_count = {}
    for k, y in enumerate(PF):
        parts = {c: float(fut[c][k]) for c in FUT_IDS}
        net = float(sum(parts.values()))
        if int(y) in pipe:                            # the stock-identity count (see the docstring)
            floor_count[int(y)] = float(line_f.loc[y])
            line_f.loc[y] = net
        annual.append(dict(year=int(y), parts=parts, net=net, line=float(line_f.loc[y]),
                           up=sum(v for v in parts.values() if v > 0), down=sum(v for v in parts.values() if v < 0)))
    bad = [(c['year'], c['line'], c['net']) for c in annual
           if not np.isclose(c['line'], c['net'], rtol=SF2B_RTOL, atol=0.0)]
    if bad:
        raise SystemExit('STOP: SF2b: the dwellings built differ from the sum of the components in '
                         + '; '.join(f'{y} (line {l_:,.1f}, components {n:,.1f})' for y, l_, n in bad))
    present = {c for col in hist + annual for c, v in col['parts'].items() if abs(v) > 1e-9}
    years_line = np.concatenate([line_h.index.values, PF]).astype(float)
    if not np.array_equal(years_line, np.arange(years_line[0], years_line[-1] + 1)):
        raise SystemExit('STOP: SF2b: the annual dwellings built are not one continuous series of years.')
    return dict(history=hist, pipeline=pipe, annual=annual, present=present, gap=g, pipeline_floor_count=floor_count,
                line=(years_line, np.concatenate([line_h.values, line_f.values]).astype(float)),
                xlim=(hist[0]['x'][0], float(PF[-1]) + 0.5))


def _yrs(a_, b_):
    return f'{a_}–{b_}'


def sf2b_draw(a, b):
    """Draw the SF2b columns, areas, caps and line (values in thousand dwellings per year)."""
    k = 1e3
    for j, c in enumerate(b['history']):            # census intervals: one column each
        x = list(c['x'])
        st = (dict(COMP_STYLE, unexplained_building=COMP_STYLE['surplus_2425']) if j == len(b['history']) - 1
              else COMP_STYLE)                       # after the last census: the carried surplus, hatched
        P.stack_series(a, x, [(cid, np.full(2, c['parts'][cid] / k)) for cid in HIST_IDS], net=np.full(2, c['net'] / k),
                       net_line=False, styles=st)
        a.plot(x, [c['net'] / k] * 2, color=S.MUTED, lw=S.LW_THIN, gid='census_interval_mean', zorder=6)
    g = b['gap']
    pipe = set(b['pipeline'])
    for c in b['annual']:                           # the pipeline years: annual columns
        if c['year'] in pipe:
            x = [c['year'] - 0.5 + g, c['year'] + 0.5 - g]
            P.stack_series(a, x, [(cid, np.full(2, c['parts'][cid] / k)) for cid in FUT_IDS],
                           net=np.full(2, c['net'] / k), net_line=False, styles=COMP_STYLE)
    fut = [c for c in b['annual'] if c['year'] not in pipe]      # the projection: annual areas, each year its width
    yrs = np.array([c['year'] for c in fut], float)
    xs = np.concatenate([[yrs[0] - 0.5 + g], yrs, [yrs[-1] + 0.5]])
    ext = lambda v: np.concatenate([[v[0]], v, [v[-1]]])
    P.stack_series(a, xs, [(cid, ext(np.array([c['parts'][cid] for c in fut]) / k)) for cid in FUT_IDS],
                   net=ext(np.array([c['net'] for c in fut]) / k), net_line=False, styles=COMP_STYLE)
    ly, lv = b['line']                              # straight segments between year centres, no markers
    a.plot(ly, lv / k, color=S.INK, lw=S.LW, gid=P.NET_GID, zorder=7)


def sf2_stock_vacancy():
    fid = 'SF2_stock_vacancy'
    d = D.src('D05_stock_and_vacancy')
    d6 = D.src('D06_vacancy_definition')
    FY, PF, YH = d['forecast_years'], d['projection_years'], d['years_hist_flows']
    census_y = [int(y) for y in d['census_years']]
    fig = plt.figure(figsize=S.figsize('double', 185))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.1], width_ratios=[1, 1, 1, 0.85], hspace=0.66, wspace=0.75)

    a = fig.add_subplot(gs[0, :])                   # the stock panel (b) dropped; vacancy the full width
    vc = d['vacancy_consistent_knots']
    lo, hi = float(vc.min()), float(vc.max())
    a.axhspan(100 * lo, 100 * hi, color=S.BAND['vacancy'][0], alpha=S.FIXED_FADES['census_range_span'], lw=0,
              label=f'Census {int(vc.index.min())}–{int(vc.index.max())} range, one definition '
                    f'({100 * lo:.1f}–{100 * hi:.1f}%)')
    a.axvspan(2013, 2018, color=S.MUTED, alpha=S.FIXED_FADES['definition_break_span'], lw=0, label='2013 → 2018 empty / away definition break')
    vp, vcm = d['vacancy_published_model'], d['vacancy_consistent_model']
    # the labels say which series the Reference uses (engine.vacancy_knots; projection.v_forward)
    P.line(a, vp.index, 100 * vp.values, color=S.INK, lw=S.LW,
           label='Reference, history: census empty / private dwellings (before 2013: unoccupied × the 2013 empty '
                 'share), linear between censuses')
    P.line(a, vcm.index, 100 * vcm.values, color=S.BAND['vacancy'][0], lw=S.LW, ls='-.',
           label='Sensitivity, not used by the Reference: one definition, pooled 2018/2023 empty share')
    vf = d['vacancy_forward']
    a.plot(FY, np.full(len(FY), 100 * vf), color=S.INK, lw=S.LW_THIN, ls=':',
           label=f'Reference, projection: held at the 2023 census value ({100 * vf:.2f}%)')
    P.line(a, FY, 100 * d['vacancy_implied'], color=S.INK, lw=S.LW, ls='--',
           label='Reference, projection: implied by the held rate + the unabsorbed starting surplus and 2026 '
                 'overbuild / stock')
    K = d['census_knots']
    for y, r in K.iterrows():
        filled = bool(r['measured'])
        a.scatter(y, 100 * r['vacancy'], s=12, zorder=5, color=S.CENSUS_EMPTY if filled else 'white',
                  edgecolor=S.CENSUS_EMPTY, lw=S.LW_THIN)
        a.scatter(y, 100 * r['all_unoccupied'], marker='x', color=S.MUTED, s=12, lw=S.LW_THIN)
    a.scatter([], [], color=S.CENSUS_EMPTY, s=12, label='Census empty (published)')
    a.scatter([], [], color='white', edgecolor=S.CENSUS_EMPTY, s=12, label='Census empty (2013 split applied)')
    a.scatter([], [], marker='x', color=S.MUTED, s=12, label='All unoccupied (rejected)')
    P.split(a)
    a.set_xlim(1985, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Vacancy rate (% of private dwellings)')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, ncol=2)
    P.panel(a, 'a', 'Vacancy: empty homes only')

    # (c; data D06): the unconsented additions each vacancy definition requires
    a = fig.add_subplot(gs[1, 3])
    vals = [d6['unconsented_empty_only'], d6['unconsented_including_away']]
    nb = d6['mean_dwellings_built']
    bb_ = a.bar([0, 1], vals, color=[S.BAND['vacancy'][0], S.MUTED], width=0.6)
    a.set_ylim(min(vals) * 1.25, 0)
    for bb, v in zip(bb_, vals):
        a.text(bb.get_x() + bb.get_width() / 2, v, P.minus(f'{v:,.0f}\n({100 * v / nb:+.0f}%)'), ha='center', va='top',
               fontsize=S.FONT_MIN, color=S.INK)
    a.set_xticks([0, 1])
    a.set_xticklabels(['Empty\nonly\n(used)', "With 'away'\n(rejected)"], fontsize=S.FONT_MIN)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    a.set_ylabel(f"Unconsented additions required\n1992–{int(d6['calib_end'])} (per year)", fontsize=S.FONT_SMALL)
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'c', 'Vacancy definition')                # d -> c

    a = fig.add_subplot(gs[1, :3])
    b = sf2b_columns()
    sf2b_draw(a, b)
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    # the unexplained building of each interval as one row of values at the top of the panel (thousand
    # dwellings per year), above every column, so no label sits on a column
    for c in b['history']:
        m = c['parts']['unexplained_building'] / 1e3
        a.text(c['centre'], 0.965, P.minus(f'{m:+.1f}'), transform=a.get_xaxis_transform(), ha='center', va='top',
               fontsize=S.FONT_MIN, color=S.NEUTRALS['note_text'])
    # the latest interval (households from the model, not census-benchmarked) labelled, not faded
    last = b['history'][-1]
    ss = D.js('baseline/projection.json')['starting_surplus']    # F1 starting surplus
    if not np.isclose(last['parts']['unexplained_building'], ss['r_after'], rtol=1e-9):
        raise SystemExit(f"STOP: SF2b: the {_yrs(*last['years'])} unexplained building "
                         f"({last['parts']['unexplained_building']:,.1f}) is not the F1 residual ({ss['r_after']:,.1f}).")
    a.text(last['centre'], last['up'] / 1e3, '†', ha='center', va='bottom', fontsize=S.FONT_SMALL, color=S.INK)
    a.annotate(f"1986–91 not covered (calibration starts 1991)\n† {_yrs(*last['years'])}: households = population /\n"
               'household size (model), not census-benchmarked', (0, 0.02), xycoords='axes fraction', xytext=(3, 0),
               textcoords='offset points', fontsize=S.FONT_MIN, color=S.MUTED)      # 3 pt clear of the spine
    P.split(a)
    a.set_xlim(b['xlim'])
    a.set_ylabel('Dwellings (thousand per year)')
    _y0, _y1 = a.get_ylim()
    a.set_ylim(_y0 - 0.06 * (_y1 - _y0), _y1 + 0.10 * (_y1 - _y0))   # room for the row of unexplained values
    P.panel(a, 'b', 'Dwellings per year by component (top row: unexplained building, thousand per year)')
    shown = [c for c in SF2B_LEGEND if c in b['present']]
    shown.insert(shown.index('unexplained_building') + 1, 'surplus_2425')
    seen, handles = set(), []
    for c in shown:                                   # one entry per label (net replacement: history and projection)
        if COMP[c][0] in seen:
            continue
        seen.add(COMP[c][0])
        handles.append(Patch(label=COMP[c][0], **dict(COMP_STYLE[c], linewidth=S.LW_SEAM)))
    handles += [Line2D([0], [0], color=S.INK, lw=S.LW, label='Dwellings built, in scope (annual)'),
                Line2D([0], [0], color=S.MUTED, lw=S.LW_THIN, label='Census-interval mean')]
    a.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=3, fontsize=S.FONT_MIN)
    V = d['vacancy_wording']
    sm = D.js('baseline/scenarios.json')['meta']              # the projection's replacement rates (%/yr)
    hist_note = (f'History: one column per census interval (interval means; vacancy on one definition, the pooled '
                 f"2018/2023 empty share, {100 * d['pooled_share']:.1f}% of unoccupied dwellings); between censuses "
                 f'annual detail is not identified. The {census_y[-1] + 1}–{int(YH[-1])} column (marked †): households '
                 'are population / household size (model), not census-benchmarked; its unexplained building '
                 f"({ss['r_after']:,.0f} dwellings a year) is the F1 residual, carried into 2026 as the starting surplus "
                 f"({ss['dwellings']:,.0f} dwellings, hatched). Pipeline years {', '.join(str(y) for y in b['pipeline'])}: annual columns; "
                 f"projection from {b['pipeline'][-1] + 1}: annual stacked areas. In the pipeline years the line is the "
                 'sum of the components (the stock-identity count: observed building less the modelled '
                 'retirement-village share); the in-scope floor area divided by the dwelling size held at its '
                 '2023–2025 mean gives ' + '; '.join(
                     f"{y}: {v:,.0f} ({P.minus(format(v - c['net'], '+,.0f'))})" for y, v in
                     b['pipeline_floor_count'].items() for c in b['annual'] if c['year'] == y)
                 + ' (the pipeline floor area is observed, the dwelling size held).')
    S.save_figure(fig, fid, source=['figure_source/D05_stock_and_vacancy.json',
                                    'figure_source/D06_vacancy_definition.json', 'baseline/scenarios.json', 'baseline/projection.json'], note=(
        f'a: {V[0].upper() + V[1:]}. c: the unconsented additions each vacancy definition requires to close the stock '
        'identity (BRANZ demolition rate); counting residents-away dwellings as vacant requires implausibly many. '
        f'b: {hist_note} History: net replacement is census-measured, the '
        'rate of the census dwelling-count identity of each interval (SF3; under-construction corrected) x the '
        f"previous year's stock, the quantity the model uses ({census_y[-1] + 1}–{int(YH[-1])}: the latest rate "
        'carried). Projection: net replacement, retirement villages (negative), the 2026 overbuild and the overbuild '
        f"absorbed (negative payback of the 2026 overbuild and of the starting surplus: {ss['dwellings']:,.0f} vacant "
        f"dwellings at the start of 2026, the {ss['after_years'][0]}–{ss['after_years'][-1]} unexplained building "
        f"above the census-interval mean x {len(ss['after_years'])} years, absorbed by {ss['absorbed_by']}). "
        'Net replacement = demolition − unconsented additions (+ the recent surge in the '
        'Reference); the census measures only the net. The projection\'s split (demolition at the BRANZ rate, '
        f"{sm['demolition_rate_pct']:.3f}%/yr; the calibrated residual as unconsented additions, "
        f"{P.minus(format(sm['residual_long_pct'], '.3f'))}%/yr; the surge) is not identified from data and is not "
        'drawn. Positive parts are stacked up from zero and negative parts down from zero, all solid (no '
        'outlines, hatching or fades); up + down = the net of every column and year (checked). The line is the '
        'annual dwellings built (in scope), straight between annual values; the grey caps are its census-interval '
        'means (equal to the column nets, checked). Unexplained building (its value per interval in the row at the top, '
        'thousand dwellings per year): building not explained by household formation, vacancy and census-measured replacement: '
        'redevelopment not captured by the census counts, error in the household estimates, or residual; it may be '
        'negative.'))


# ---------------------------------------------------------------------------
# SF4 (D08 + the consent sizes of the former SF6): new-dwelling size
# ---------------------------------------------------------------------------
def sf4_dwelling_size():
    """(a) realised and occupied floor area per new dwelling; (b) mean consented new-dwelling size by typology 1990-2025
    with the minima (L4) and the Reference size. the occupancy-utilisation panel (b before) dropped."""
    d = D.src('D08_dwelling_space')
    p = D.js('pathways/levers.json')['L4']
    yh = d['years_hist']
    real, occ = (d[k].values for k in ('realised_dwelling_size', 'occupied_area_per_dwelling'))
    fig, (a, c) = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    P.line(a, yh, real, color=S.INK, label='Realised new-dwelling size (floor area / consents)')
    P.line(a, yh, occ, color=S.MUTED, ls='-.', label='Occupied area per dwelling (household size × occupant load factor)')
    xf, rf = P.pchip(np.asarray(yh, float), np.asarray(real, float))
    _, of = P.pchip(np.asarray(yh, float), np.asarray(occ, float))
    a.fill_between(xf, of, rf, color=S.BAND['extra_space'][0], alpha=S.OPACITY['space_above_occupancy'], lw=0,
                   label='Space above occupancy (under-utilisation)')
    a.set_xlim(yh[0], yh[-1])
    a.set_ylim(0, None)
    a.set_ylabel('Floor area per dwelling (m²)')
    a.legend(loc='lower left', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'Realised and occupied floor area')
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
    P.panel(c, 'b', 'Consented size by typology')
    fig.tight_layout()
    S.save_figure(fig, 'SF4_dwelling_size', source=['figure_source/D08_dwelling_space.json', 'pathways/levers.json'],
                  note='b: dotted, the Reference size (2023-2025 mean); dots, the smallest annual mean (the L4 minima). '
                       '1990 is the first year of the series and a recession year.')


FIGURES = {'SF1_households': sf1_households, 'SF2_stock_vacancy': sf2_stock_vacancy,
           'SF4_dwelling_size': sf4_dwelling_size}
