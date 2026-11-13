"""Validation and report diagnostics (draw only): D07_net_replacement_rate, D10_floor_area_bridge,
D11_floor_area_bridge_split, D12_conversion_chain, D14_hindcast, D15_reality_checks, D19_variants.

Each figure reads its figure source data (outputs/data/figure_source/<file id>.json, written by
tools/figures_report.py); ED10 panel h also reads baseline/annual.csv and baseline/variants_annual.csv. Nothing is
recomputed here.

Sign rules (figures/draw.py): the floor-area bridges (D10, D11) are waterfalls of cumulative values: a positive band
a filled step up from the running total, a negative band (Overbuild absorbed, Unconsented additions, retirement
villages, or any band negative in a run) an unfilled, unhatched segment outlined in its band colour hanging down
from the running total (the top of the positive stack), so the last step ends at the net total, drawn as the
black 'Total, in scope' bar. No band is hatched.
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S

VARS = ('LOW', 'REF', 'HIGH', 'VHIGH')            # + Very High replacement


def _src(fid):
    return [f'figure_source/{fid}.json']


def _scen_line(k):
    st = dict(S.SCENARIO[k])
    st.pop('label')
    return st


# ---------------------------------------------------------------------------
# D14 hindcast
# ---------------------------------------------------------------------------
# the replacement variant (style.SCENARIO key) of each hindcast method (validation.hindcast)
HINDCAST_VARIANTS = (('LOW', 'dwelling_count'), ('REF', 'reference'), ('HIGH', 'high'), ('VHIGH', 'very_high'))
# the short names of the in-panel error box; the legend carries the full names (naming.SCENARIOS)
HINDCAST_SHORT = {'LOW': 'Low', 'REF': 'Reference', 'HIGH': 'High', 'VHIGH': 'Very High'}


def sf6_hindcast():
    fid = 'SF6_hindcast'
    v = D.src('D14_hindcast')
    fig, ax = plt.subplots(1, 4, figsize=S.figsize('double', 74), gridspec_kw=dict(width_ratios=[1, 1, 1, 0.75]))
    # Actual and the four replacement variants (ED3 styles), each defined from the census intervals
    # before the origin only (validation.hindcast)
    for a, o, letter in zip(ax[:3], (2006, 2013, 2018), 'abc'):
        rows = {r['method']: r for r in v['hindcast'] if r['origin'] == o and 'years' in r}
        if not rows:
            continue
        yy = rows[v['model_method']]['years']
        P.line(a, yy, np.cumsum(rows[v['model_method']]['actual_path']) / 1e3, color=S.INK, lw=S.LW_BOLD,
               label='Actual')
        err = []
        for k, m in HINDCAST_VARIANTS:
            r = rows[m]
            P.line(a, yy, np.cumsum(r['predicted_path']) / 1e3, label=N.SCENARIOS[k], **dict(_scen_line(k), lw=S.LW))
            err.append(f"{HINDCAST_SHORT[k]} {P.minus(format(r['error_pct'], '+.1f'))}%")
        # top left, the empty corner of a cumulative path (bottom right overlapped the curves)
        a.text(0.03, 0.97, 'Error at the end:\n' + '\n'.join(err), transform=a.transAxes, ha='left', va='top',
               fontsize=S.FONT_MIN)
        a.set_ylabel('Dwellings, cumulative (thousand)')
        a.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
        P.panel(a, letter, f'Hindcast from {o}')
    fig.legend(*ax[0].get_legend_handles_labels(), loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.01),
               frameon=False)
    c = v['check_2026']
    a = ax[3]
    pipeline_mode = c.get('status') == 'pipeline'
    if c.get('status') == 'observed':
        a.bar(['Observed', 'Model'], [c['observed_ytd'], c['model_expected_ytd']], color=[S.INK, S.VALIDATION['model_check']], width=0.6)
    elif pipeline_mode and 'observed_pipeline_built_all' in c:      # completion lag
        a.bar(['Observed\n(pipeline)', 'Model'], [c['observed_pipeline_built_all'], c['model_built_all']],
              color=[S.INK, S.VALIDATION['model_check']], width=0.6)
    if 'ratio_observed_to_model' in c:
        a.set_ylim(0, a.get_ylim()[1] * 1.15)
        a.text(0.5, 0.97, f"ratio {c['ratio_observed_to_model']:.2f}", transform=a.transAxes, ha='center', va='top',
               fontsize=S.FONT_SMALL)
    ytd_months = (f"January–{N.month_year(c['data_end'])}" if c.get('data_end') else 'the observed 2026 months')
    a.set_ylabel(f"Dwellings completed, {c['target_year']}" if pipeline_mode else
                 f'Dwellings consented, {ytd_months}')
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'd', 'Pipeline-year check' if pipeline_mode else 'Year-to-date check')   # the year: the y label
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    S.save_figure(fig, fid,
                  note='Rolling-origin hindcast of dwellings built (cumulative), each origin projected with the '
                       'information available then; errors at the end of each window, vacancy on the consistent '
                       'definition. The four replacement variants use only the census intervals ending at or before '
                       'the origin: Low the long-run dwelling-count rate, Reference the last intercensal rate fading '
                       'to it (10-year half-life), High the last rate held, Very High the weighted linear trend of the '
                       'interval rates (3, 4 and 5 intervals at the 2006, 2013 and 2018 origins). d: '
                       + ('building of the first year the run without 2026 data models, observed in the pipeline '
                          '(consents lagged), against that run.' if pipeline_mode else
                          f'consents observed {ytd_months} against the model, which uses no 2026 data.'),
                  source=['figure_source/D14_hindcast.json', 'baseline/validation.json'])


# ---------------------------------------------------------------------------
# ED10 (D15) reality checks
# ---------------------------------------------------------------------------
HISTORY_ATOL = 1e-12          # every drawn history vertex equals its source value (observed data are not smoothed)


def _history_line(a, x, y):
    """Observed history: straight segments between annual values (no PCHIP), checked against the source."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(y)
    ln, = a.plot(x[ok], y[ok], color=S.INK, lw=S.LW, label='History')
    dx, dy = (np.asarray(v, float) for v in ln.get_data())
    err = float(np.max(np.abs(dy - y[ok]))) if len(dy) else 0.0
    if len(dx) != int(ok.sum()) or err > HISTORY_ATOL:
        raise SystemExit(f'STOP: ED10: a drawn history line differs from its source data ({err:.3g}).')
    return err


def ed10_reality_checks():
    """ED10 (data D15, baseline/annual.csv, baseline/variants_annual.csv): the projection of each replacement variant
    against the 1991-2025 range (grey band) for eight quantities. History: straight segments between annual values
    (observed data are not smoothed); census-interval rates (b) are constant within each interval. Projections: PCHIP
    display interpolation as every projection line. The largest difference between a drawn history and its source is
    returned in the note (it must be 0)."""
    fid = 'ED10_reality_checks'
    d = D.src('D15_reality_checks')
    labels = d['labels']
    fig, ax = plt.subplots(3, 3, figsize=S.figsize('double', 165))
    ax = ax.ravel()
    titles = {'removals_net': 'Implied net removals', 'vacancy': 'Effective vacancy rate'}   # D15 titles otherwise
    errs = {}
    for i, key in enumerate(d['order']):
        p = d['panels'][key]
        a = ax[i]
        lo, hi = p['range_1991_2025']
        a.axhspan(lo, hi, color=S.MUTED, alpha=S.FIXED_FADES['history_range_span'], lw=0, label='1991–2025 range')
        hs = p['history']
        errs[key] = _history_line(a, hs.index, hs.values)
        for k in VARS:
            y = p['projection'][k]
            P.line(a, y.index, y, label=labels[k], **_scen_line(k))
        P.split(a)
        a.set_xlim(1991, 2050)
        a.set_ylabel(p['ylabel'])
        a.ticklabel_format(axis='y', style='plain', useOffset=False)
        P.panel(a, 'abcdefg'[i], titles.get(key, p['title']))
    rem = d['removals_pct_of_2025_stock']
    txt = '\n'.join(f"{HINDCAST_SHORT[k]}: {rem[k]:.1f}%" for k in VARS)   # short names; the legend has the full ones
    tb = ax[1].text(0.02, 0.97, 'Removals 2026–2050,\n% of the 2025 stock:\n' + txt, transform=ax[1].transAxes,
                    va='top', fontsize=S.FONT_MIN,
                    bbox=dict(facecolor='white', alpha=S.FIXED_FADES['label_box'], edgecolor='none', pad=1))
    m = d['m2_per_res_max']
    ax[3].set_ylim(0, 300)
    ax[3].text(0.02, 0.97, f"Off scale: {int(m['year'])}, {m['value']:,.0f} m² per person\n(near-zero population "
               "growth)", transform=ax[3].transAxes, va='top', fontsize=S.FONT_MIN,
               bbox=dict(facecolor='white', alpha=S.FIXED_FADES['label_box'], edgecolor='none', pad=1))
    # h: floor area built (consented, in scope): history baseline/annual.csv, projection baseline/variants_annual.csv
    a = ax[7]
    an = D.csv('baseline/annual.csv')
    fh = an[an['source'] == 'history'].set_index('year')['floor_area_Mm2'].loc[1991:2025]
    va = D.csv('baseline/variants_annual.csv')
    a.axhspan(float(fh.min()), float(fh.max()), color=S.MUTED, alpha=S.FIXED_FADES['history_range_span'], lw=0)
    errs['floor_area'] = _history_line(a, fh.index, fh.values)
    ref = an[an['source'] != 'history'].set_index('year')['floor_area_Mm2']
    for k in VARS:
        y = va[va['variant'] == k].set_index('year')['floor_area_Mm2']
        if k == 'REF' and not np.allclose(y.values, ref.reindex(y.index).values, rtol=1e-12, atol=0):
            raise SystemExit('STOP: ED10: the Reference of variants_annual.csv differs from annual.csv.')
        P.line(a, y.index, y, label=labels[k], **_scen_line(k))
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Floor area (Mm² per year)')
    P.panel(a, 'h', 'Floor area built')
    ax[8].axis('off')
    h_, l_ = ax[0].get_legend_handles_labels()
    ax[8].legend(h_, l_, loc='center', frameon=False)
    fig.tight_layout()
    fig.canvas.draw()                                     # the panel b text box must cover no drawn line
    bb = tb.get_bbox_patch().get_window_extent().transformed(ax[1].transData.inverted())
    hb = d['panels'][d['order'][1]]['history']
    if not (bb.x1 < P.HISTORY_SPLIT and bb.y0 > float(np.nanmax(hb.values))):
        raise SystemExit(f'STOP: ED10 b: the removals text box (x {bb.x0:.1f}-{bb.x1:.1f}, y {bb.y0:.2f}-{bb.y1:.2f}) '
                         'covers drawn data')
    h = d['handover']
    S.save_figure(fig, fid,
                  note='Projection 2026–2050 against the 1991–2025 range (grey band); b: implied net removals = net '
                       'replacement rate × stock; h: consented floor area, in scope; a: in scope and retirement '
                       'villages; the exceedances are tabulated in outputs/reports/reality_checks.md. b: Low and High '
                       'hold a constant rate (Low: the 1991–2023 long-run rate; High: the 2018–2023 rate); removals '
                       'rise because the stock grows. The Reference rate fades from the 2018–2023 rate to the long-run '
                       'rate (half-life 10 yr); Very High continues the census trend. History lines: straight segments '
                       'between annual values (not smoothed; largest difference from the source data '
                       f'{max(errs.values()):.1g}); b: census-interval rates, constant within each interval. Handover: '
                       f"the {h['last_observed_year']} → {h['first_model_year']} step of the Reference floor area "
                       f"({h['last_observed_year']} observed, {h['first_model_year']} the first model year) is "
                       + P.minus(f"{h['step_pct']:+.1f}%") + ', against year-to-year changes of '
                       + P.minus(f"{h['hist_min_pct']:+.1f}%") + ' to ' + P.minus(f"{h['hist_max_pct']:+.1f}%")
                       + ' (median ' + P.minus(f"{h['hist_median_pct']:+.1f}%") + ') in consented floor area, '
                       '1992–2025.',
                  source=['figure_source/D15_reality_checks.json', 'baseline/annual.csv', 'baseline/variants_annual.csv'])


FIGURES = {'SF6_hindcast': sf6_hindcast, 'ED10_reality_checks': ed10_reality_checks}
