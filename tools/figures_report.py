"""Report figures of the projection (reality checks, floor-area bridge, net replacement rate,
variants, conversion chain, validation) and the reality checks, generated from model runs
and outputs/data/.

    python tools/figures_report.py

Figures -> outputs/diagnostics/ (style.save_figure; figure_plan.py); where the projection
leaves the 1991-2025 range -> outputs/data/baseline/reality_checks.json and
outputs/reports/reality_checks.md. The figures are indexed in outputs/diagnostics/DIAGNOSTICS.md.
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine  # noqa: E402
import layout  # noqa: E402
import naming as N  # noqa: E402
import style  # noqa: E402
import validation  # noqa: E402


def _savefig(fig, fname, note=None):
    style.save_figure(fig, fname, note=note)


# the Reference and the two replacement variants (typology shares held in all); labels: naming.SCENARIOS
SCEN = [('LOW', N.SCENARIOS['LOW'], dict(REPLACEMENT_VARIANT='LOW')),
        ('REF', N.SCENARIOS['REF'], dict(REPLACEMENT_VARIANT='REF', REPLACEMENT_HALF_LIFE=10.0)),
        ('HIGH', N.SCENARIOS['HIGH'], dict(REPLACEMENT_VARIANT='HIGH'))]
M6 = 1e6


def series(B):
    """Annual quantities, history (1991-2025) and projection (2026-2050)."""
    E, R = B['engine_out']['50th'], B['results']['50th']
    fy = np.asarray(B['forecast_years'])
    yh = np.asarray(B['years_hist'])
    c = float(B['_completion'])
    pop_f = pd.Series(E['pop'], index=fy)
    hp = B['hist_pop']
    long_rate = float(B['demolition_rate'] + B['unconsented_rate'])
    wave = (np.asarray(B['rate_path'], float) - long_rate) * E['prev']
    p = dict(
        built=pd.Series(engine.requirement(E), index=fy),
        removals_net=pd.Series(E['demol'] + E['unc'] + E['join_redev'], index=fy),
        removals_gross=pd.Series(E['demol'] + wave + E['join_redev'], index=fy),
        dpop=pop_f.diff(), gfa=pd.Series(R['total'], index=fy),
        S=pd.Series(E['S'], index=fy),
        # effective vacancy: the stock-adding near-term excess raises it above the exogenous rate
        v=pd.Series(100 * (1 - np.asarray(E['hh']) / (np.asarray(E['stock']) + np.asarray(E['stock_join']))), index=fy),
        size=pd.Series(R['total'] / np.where(E['dwell_in_scope'] == 0, np.nan, E['dwell_in_scope']), index=fy),
        dense=100 * (1 - B['evolving_gfa_shares']['Detached']),
        carbon=pd.Series(E['carbon'], index=fy), d_hh=pd.Series(E['d_hh'], index=fy),
        stock_2025=float(E['stock'][0]))
    built_h = c * B['hist_units_all_c']
    cr = B['census_rates']
    rem_h = pd.Series(np.nan, index=yh, dtype=float)
    for r in cr.itertuples():                        # census-interval net removals, annualised
        rem_h[(yh > r.y0) & (yh <= r.y1)] = (r.built - r.d_stock) / (r.y1 - r.y0)
    h = dict(built=built_h, removals_net=rem_h, dpop=hp.diff(), gfa=B['hist_built_gfa'],
             S=B['hist_S'], v=100 * B['stock_cal']['v'], size=B['hist_built_gfa'] / B['hist_built_units'],
             dense=100 * (1 - B['hist_shares']['Detached']))
    return p, h


def range_check(hist, proj, years=(2026, 2050)):
    h = hist.loc[1991:2025].replace([np.inf, -np.inf], np.nan).dropna()
    q = proj.loc[years[0]:years[1]].replace([np.inf, -np.inf], np.nan).dropna()
    lo, hi = float(h.min()), float(h.max())
    above, below = q[q > hi], q[q < lo]
    return dict(hist_min=lo, hist_max=hi, years_outside=int(len(above) + len(below)),
                max_above_pct=float(100 * (above.max() / hi - 1)) if len(above) and hi else 0.0,
                max_below_pct=float(100 * (1 - below.min() / lo)) if len(below) and lo else 0.0,
                first_outside=int(min(list(above.index) + list(below.index))) if len(above) + len(below) else None)


def scen_line(k):
    st = dict(style.SCENARIO[k])
    st.pop('label')
    return st


def main():
    import plotting as P
    S = style
    S.apply()
    runs = {}
    for k, lab, s in SCEN:
        B = validation.run_boss(**s)
        runs[k] = dict(B=B, lab=lab, p=series(B)[0])
    hist = series(runs['REF']['B'])[1]
    ref = runs['REF']
    VARS = ('LOW', 'REF', 'HIGH')

    # ---- D15 reality checks -------------------------------------------------
    rc = {}
    fig, ax = plt.subplots(3, 3, figsize=S.figsize('double', 165))
    ax = ax.ravel()
    panels = [
        ('built', ax[0], 'Dwellings completed', 'Dwellings (thousand per year)', 1e3,
         lambda p: p['built']),
        ('removals_net', ax[1], 'Implied net removals', 'Dwellings (thousand per year)', 1e3, lambda p: p['removals_net']),
        ('ppl_per_dw', ax[2], 'People per new dwelling', 'Persons per new dwelling', 1, lambda p: p['dpop'] / p['built']),
        ('m2_per_res', ax[3], 'New floor area per additional resident', 'Floor area per person (m²)', 1,
         lambda p: p['gfa'] / p['dpop']),
        ('S', ax[4], 'Household size', 'Household size (persons per household)', 1, lambda p: p['S']),
        ('size', ax[5], 'Average new-dwelling size', 'Floor area per dwelling (m²)', 1, lambda p: p['size'])]
    hist_of = dict(built=hist['built'], removals_net=hist['removals_net'], ppl_per_dw=hist['dpop'] / hist['built'],
                   m2_per_res=hist['gfa'] / hist['dpop'], S=hist['S'], size=hist['size'])

    def reality_panel(a, hs, proj, title, unit, letter):
        h = hs.loc[1991:2025].replace([np.inf, -np.inf], np.nan).dropna()
        a.axhspan(h.min(), h.max(), color=S.MUTED, alpha=0.12, lw=0, label='1991–2025 range')
        a.plot(hs.index, hs, color=S.INK, lw=S.LW, label='History')
        for k in VARS:
            y = proj[k].loc[2026:]
            a.plot(y.index, y, label=runs[k]['lab'], **scen_line(k))
        P.split(a)
        a.set_xlim(1991, 2050)
        a.set_ylabel(unit)
        a.ticklabel_format(axis='y', style='plain', useOffset=False)
        P.panel(a, letter, title)

    letters = 'abcdefgh'
    for i, (key, a, title, unit, sc, f) in enumerate(panels):
        hs = hist_of[key]
        reality_panel(a, hs / sc, {k: f(runs[k]['p']) / sc for k in VARS}, title, unit, letters[i])
        for k in VARS:
            rc.setdefault(k, {})[key] = range_check(hs, f(runs[k]['p']))
    for k in VARS:
        rc[k]['vacancy'] = range_check(hist['v'], runs[k]['p']['v'])
    reality_panel(ax[6], hist['v'], {k: runs[k]['p']['v'] for k in VARS}, 'Vacancy rate (effective)',
                  'Vacancy rate (% of private dwellings)', 'g')
    # cumulative removals as % of 2025 stock by 2050 (gross: demolition + redevelopment + 2026 overbuild)
    txt = '\n'.join(f"{runs[k]['lab']}: {100 * runs[k]['p']['removals_gross'].loc[2026:].sum() / runs[k]['p']['stock_2025']:.1f}%"
                    for k in VARS)
    ax[1].text(0.02, 0.97, 'Removals 2026–2050,\n% of the 2025 stock:\n' + txt, transform=ax[1].transAxes,
               va='top', fontsize=S.FONT_MIN, bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=1))
    _m2 = (hist['gfa'] / hist['dpop']).loc[1991:2025]
    ax[3].set_ylim(0, 300)
    ax[3].text(0.02, 0.97, f"Off scale: {int(_m2.idxmax())}, {_m2.max():,.0f} m² per person\n(near-zero population "
               "growth)", transform=ax[3].transAxes, va='top', fontsize=S.FONT_MIN)
    # the 2026 (observed) -> 2027 (model) handover against historical year-to-year changes
    a = ax[7]
    Bref = ref['B']
    chg = 100 * Bref['hist_total_gfa'].pct_change().loc[1992:2025].values
    R0 = Bref['results']['50th']['total']
    step = 100 * (R0[2] / R0[1] - 1)
    a.hist(chg, bins=14, **S.fill('#BDBDBD'))
    a.set_ylim(0, a.get_ylim()[1] * 1.45)                 # room for the legend above the bars
    a.axvline(step, color=S.ACCENT_ORANGE, lw=S.LW_BOLD, label=f'2026 → 2027 handover (observed → model): {step:+.1f}%')
    a.axvline(np.median(chg), color=S.INK, lw=S.LW, ls='--', label=f'Median year, 1992–2025: {np.median(chg):+.1f}%')
    a.set_xlabel('Change from the previous year (%)')
    a.set_ylabel('Number of years')
    a.legend(loc='upper left', fontsize=S.FONT_MIN)
    P.panel(a, 'h', 'Handover vs annual changes in floor area')
    handover = dict(step_2026_2027_pct=float(step), hist_median_pct=float(np.median(chg)),
                    hist_min_pct=float(chg.min()), hist_max_pct=float(chg.max()))
    ax[8].axis('off')
    h_, l_ = ax[0].get_legend_handles_labels()
    ax[8].legend(h_, l_, loc='center', frameon=False)
    fig.tight_layout()
    _savefig(fig, 'D15_reality_checks',
             'Projection 2026–2050 against the 1991–2025 range (grey band); a: in scope and retirement villages; the exceedances are tabulated in '
             'outputs/reports/reality_checks.md. h: the 2026 → 2027 step of the Reference (2026 observed, 2027 the '
             'first model year) against the year-to-year changes in consented floor area, 1992–2025.')
    plt.close(fig)

    # ---- D10 / D11 bridge -----------------------------------------------------
    def bridge(steps, fname, note):
        fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 88), sharey=True)
        for a, k, letter in zip(ax, VARS, 'abc'):
            R = runs[k]['B']['results']['50th']
            vals = [sum(float(np.sum(R[x][1:])) for x in keys) / M6 for keys, _, _ in steps]
            cum = 0.0
            for i, (v, (_, lab, st)) in enumerate(zip(vals, steps)):
                a.bar(i, v, bottom=cum if v >= 0 else cum + v, width=0.7, **st)
                a.text(i, cum + max(v, 0) + 0.8, f'{v:+.1f}', ha='center', fontsize=S.FONT_MIN)
                cum += v
            a.bar(len(steps), cum, color=S.INK, width=0.7)
            a.text(len(steps), cum + 0.8, f'{cum:.1f}', ha='center', fontsize=S.FONT_MIN, fontweight='bold')
            a.set_xticks(range(len(steps) + 1))
            a.set_xticklabels([l for _, l, _ in steps] + ['Total, in scope'], rotation=90, fontsize=S.FONT_MIN)
            a.grid(axis='x', visible=False)
            P.panel(a, letter, runs[k]['lab'])
        ax[0].set_ylabel('Floor area 2026–2050 (Mm²)')
        fig.tight_layout()
        _savefig(fig, fname, note)
        plt.close(fig)
    rv_style = S.fill('#BDBDBD', 'xxxx', '#7A7A7A')
    bst = lambda b: {k: v for k, v in P.band_style(b).items()}      # noqa: E731
    common = [(('growth',), N.BANDS['growth'], bst('growth')),
              (('hs_pos',), N.BANDS['smaller_households'], bst('smaller_households')),
              (('extra',), N.BANDS['extra_space'], bst('extra_space')),
              (('vac',), N.BANDS['vacancy'], bst('vacancy'))]
    tail = [(('wave',), N.BANDS['redevelopment'], bst('redevelopment')),
            (('join',), N.BANDS['overbuild_2026'], bst('overbuild_2026')),
            (('rv',), N.BAND_DETAIL['retirement_villages'], rv_style)]
    bridge(common + [(('repl', 'unc'), N.BANDS['replacement'], bst('replacement'))] + tail, 'D10_floor_area_bridge',
           'Each bar is one demand band, 2026–2050 (median population); retirement-village units are out of scope '
           'and leave the total as a negative step.')
    bridge(common + [(('repl',), N.BAND_DETAIL['replacement_demolition'], bst('replacement')),
                     (('unc',), N.BAND_DETAIL['replacement_residual'], dict(bst('replacement'), hatch='////', hatchcolor=S.HATCH_COLOUR))] + tail,
           'D11_floor_area_bridge_split',
           'Appendix: replacement split into demolition and the calibrated residual; the split assumes the BRANZ '
           'demolition rate: only their sum is identified by the census data.')

    # ---- D07 net replacement rate: census record and variant paths --------------
    Bref = ref['B']
    long_rate = float(Bref['demolition_rate'] + Bref['unconsented_rate'])
    fy = np.asarray(Bref['forecast_years'])
    fig, a = plt.subplots(figsize=S.figsize('double', 72))
    a.axvspan(2013, 2018, color=S.MUTED, alpha=0.10, lw=0, label='2013 → 2018: census empty / away definition break')
    for i, r in enumerate(Bref['census_rates'].itertuples()):
        a.hlines(100 * r.rate, r.y0, r.y1, color=S.INK, lw=S.LW_BOLD,
                 label='Census intervals (dwelling counts, under-construction corrected)' if i == 0 else None)
    for k in VARS:
        path = engine.replacement_path(k, long_rate, float(Bref['rate_recent']), fy, 10.0)
        a.plot(fy, 100 * path, label=runs[k]['lab'], **scen_line(k))
    a.axhline(100 * Bref['demolition_rate'], color=S.MUTED, ls='--', lw=S.LW,
              label=f"BRANZ demolition rate, {100 * Bref['demolition_rate']:.3f}%")
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    P.split(a)
    a.set_xlim(1986, 2050)
    a.set_ylabel("Net replacement (% of the previous year's stock per year)")
    a.legend(loc='upper left', fontsize=S.FONT_SMALL)
    _w = validation.projection.NET_REPLACEMENT_WINDOW
    _savefig(fig, 'D07_net_replacement_rate',
             f"Net replacement rate (demolition net of unconsented additions). Long run {_w[0]}–{_w[1]}: "
             f"{100 * long_rate:.3f}% per year; 2018–23: {100 * Bref['rate_recent']:.3f}% per year. Each step is one "
             f"intercensal interval; the 2018–23 step is a single interval. Negative values mean the stock grew by more "
             f"than consented new building, i.e. more dwellings appeared through conversions and unconsented additions "
             f"than were demolished.")
    plt.close(fig)

    # ---- D19 variants ------------------------------------------------------------
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 70), gridspec_kw=dict(width_ratios=[2, 1, 1]))
    a = ax[0]
    a.plot(hist['gfa'].index, hist['gfa'] / M6, color=S.INK, lw=S.LW, label='History (built)')
    mc = layout.montecarlo('annual', 'REF')
    if os.path.exists(mc):
        m = pd.read_csv(mc, index_col=0).loc[2026:]
        a.fill_between(m.index, m['floor_area_5'] / M6, m['floor_area_95'] / M6, label='Monte Carlo 5–95% (Reference)',
                       **S.MC_BAND)
    for k in VARS:
        g = runs[k]['p']['gfa'].loc[2026:]
        a.plot(g.index, g / M6, label=runs[k]['lab'], **scen_line(k))
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Floor area (Mm² per year)')
    a.legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'Annual floor area built')
    ks = list(VARS)
    a = ax[1]
    a.bar(range(len(ks)), [runs[k]['p']['gfa'].loc[2026:].sum() / M6 for k in ks],
          color=[S.SCENARIO[k]['color'] for k in ks], width=0.62)
    a.set_xticks(range(len(ks)))
    a.set_xticklabels([N.SCENARIOS[k].replace(' replacement', '\nreplacement') for k in ks], fontsize=S.FONT_MIN)
    a.set_ylabel('Floor area 2026–2050 (Mm²)')
    a.grid(axis='x', visible=False)
    P.panel(a, 'b', 'Floor area 2026–2050')
    a = ax[2]
    # MODEL v2.0.0: the totals only (maintenance is drawn as its own layer only in Fig3 and the demand-band
    # breakdowns; the component split of the Reference is Fig3, of every variant data/baseline/scenarios.json)
    tot = [float(runs[k]['B']['tot_carbon_median']) for k in ks]
    a.bar(range(len(ks)), tot, color=[S.SCENARIO[k]['color'] for k in ks], width=0.62)
    for i, v in enumerate(tot):
        a.text(i, v, P.fmt_kt(v), ha='center', va='bottom', fontsize=S.FONT_MIN)
    a.set_xticks(range(len(ks)))
    a.set_xticklabels([N.SCENARIOS[k].replace(' replacement', '\nreplacement') for k in ks], fontsize=S.FONT_MIN)
    a.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'c', 'Carbon 2026–2050')
    fig.tight_layout()
    _savefig(fig, 'D19_variants')
    plt.close(fig)

    # ---- D12 conversion chain -------------------------------------------------
    p = ref['p']
    yrs = np.arange(2027, 2051)
    chain = [('Population growth', p['dpop'], dict(color=S.INK)),
             ('Households formed', p['d_hh'], dict(color=S.ACCENT_ORANGE)),
             ('Dwellings built', p['built'], dict(color=S.MUTED, ls='--', lw=S.LW_BOLD)),
             ('Floor area', p['gfa'], dict(color=S.ACCENT_BLUE)),
             ('Carbon', p['carbon'], dict(color=S.PATHWAY['P4']))]
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 70))
    for lab, s_, st in chain:
        s_ = s_.loc[yrs]
        ax[0].plot(yrs, 100 * s_ / s_.loc[2027], label=lab, **dict(dict(lw=S.LW), **st))
    ax[0].axhline(100, color=S.INK, lw=S.LW_THIN)
    ax[0].set_xlim(yrs[0], yrs[-1])
    ax[0].set_ylabel('Index, 2027 = 100')
    ax[0].legend(loc='lower left', fontsize=S.FONT_MIN)
    P.panel(ax[0], 'a', 'Conversion chain, Reference')
    lo, hi = np.inf, -np.inf
    for k in VARS:
        ci = (runs[k]['p']['carbon'] / runs[k]['p']['gfa']).loc[2026:2050]
        ax[1].plot(ci.index, ci, label=runs[k]['lab'], **scen_line(k))
        lo, hi = min(lo, ci.min()), max(hi, ci.max())
    pad = 0.15 * max(hi - lo, 1.0)
    ax[1].set_ylim(lo - pad, hi + pad)
    ax[1].set_xlim(2026, 2050)
    ax[1].set_ylabel('Carbon intensity (kg CO₂e per m²)')
    ax[1].legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Carbon per m² of new floor area')
    fig.tight_layout()
    _savefig(fig, 'D12_conversion_chain',
             'a: 2026 is not the base year: it is observed building and carries the one-off population shortfall and '
             'the 2026 overbuild. b: decarbonisation, maintenance within 2026–2050 and the soil-bearing share; '
             'typology shares held.')
    plt.close(fig)

    # ---- D14 validation ---------------------------------------------------------
    from matplotlib.ticker import MaxNLocator
    v = json.load(open(layout.data('baseline/validation.json')))
    pub = v.get('hindcast_as_published') or []
    fig, ax = plt.subplots(1, 4, figsize=S.figsize('double', 74), gridspec_kw=dict(width_ratios=[1, 1, 1, 0.75]))
    lab_low = f"{N.SCENARIOS['LOW']} (census dwelling-count rate)"
    for a, o, letter in zip(ax[:3], (2006, 2013, 2018), 'abc'):
        rows = [r for r in v['hindcast'] if r['origin'] == o and 'years' in r]
        if not rows:
            continue
        yy = rows[0]['years']
        a.plot(yy, np.cumsum(rows[0]['actual_path']) / 1e3, color=S.INK, lw=S.LW_BOLD, label='Actual')
        err = []
        for r in rows:
            if r['method'] in ('reference', v['model_method']):
                k = 'REF' if r['method'] == 'reference' else 'LOW'
                a.plot(yy, np.cumsum(r['predicted_path']) / 1e3, label=N.SCENARIOS[k] if k == 'REF' else lab_low,
                       **dict(scen_line(k), lw=S.LW))
                err.append(f"{'Low replacement' if k == 'LOW' else 'Reference'} {r['error_pct']:+.1f}%")
        for r in pub:
            if r['origin'] == o and r['method'] == 'reference' and 'years' in r:
                a.plot(r['years'], np.cumsum(r['predicted_path']) / 1e3, lw=S.LW, ls=':', color=S.ACCENT_ORANGE,
                       label='Reference, vacancy as published')
                err.append(f"Vacancy as published {r['error_pct']:+.1f}%")
        a.text(0.97, 0.03, 'Error at the end:\n' + '\n'.join(err), transform=a.transAxes, ha='right', va='bottom',
               fontsize=S.FONT_MIN)
        a.set_ylabel('Dwellings, cumulative (thousand)')
        a.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
        P.panel(a, letter, f'Hindcast from {o}')
    fig.legend(*ax[0].get_legend_handles_labels(), loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.01),
               frameon=False)
    c = v['check_2026']
    a = ax[3]
    if c.get('status') == 'observed':
        a.bar(['Observed', 'Model'], [c['observed_ytd'], c['model_expected_ytd']], color=[S.INK, '#BDBDBD'], width=0.6)
        a.set_ylim(0, a.get_ylim()[1] * 1.15)
        a.text(0.5, 0.97, f"ratio {c['ratio_observed_to_model']:.2f}", transform=a.transAxes, ha='center', va='top',
               fontsize=S.FONT_SMALL)
    a.set_ylabel('Dwellings consented, January–July 2026')
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'd', '2026 check')
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _savefig(fig, 'D14_hindcast',
             'Rolling-origin hindcast of dwellings built (cumulative), each origin projected with the information '
             'available then; errors at the end of each window, vacancy on the consistent definition unless noted. '
             'd: consents observed January–July 2026 against the model, which uses no 2026 data.')
    plt.close(fig)

    # ---- reality-check exceedances ----------------------------------------
    with open(layout.writing(layout.data('baseline/reality_checks.json')), 'w') as f:
        json.dump(N.keys(dict(rc, handover=handover)), f, indent=2)
    names = dict(built='dwellings completed', removals_net='net removals', ppl_per_dw='people per new dwelling',
                 m2_per_res='floor area per additional resident', S='household size', size='new-dwelling size',
                 vacancy='vacancy rate (effective, %)')
    L = ['# Reality checks (generated by tools/figures_report.py)', '',
         'Projection 2026-2050 against the 1991-2025 historical range (min-max).', '',
         '| variant | quantity | historical range | years outside | first year outside | max above (%) | max below (%) |',
         '|---|---|---|---|---|---|---|']
    for k, d in rc.items():
        for q, r in d.items():
            L.append(f"| {k} | {names[q]} | {r['hist_min']:,.2f} to {r['hist_max']:,.2f} | {r['years_outside']} | "
                     f"{r['first_outside'] or '-'} | {r['max_above_pct']:.1f} | {r['max_below_pct']:.1f} |")
    with open(layout.writing(layout.report('reality_checks.md')), 'w') as f:
        f.write('\n'.join(L) + '\n')

    print('figures_report: report figures, outputs/data/baseline/reality_checks.json, outputs/reports/reality_checks.md')


if __name__ == '__main__':
    main()
