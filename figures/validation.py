"""Validation and report diagnostics (draw only): D07_net_replacement_rate, D10_floor_area_bridge,
D11_floor_area_bridge_split, D12_conversion_chain, D14_hindcast, D15_reality_checks, D19_variants.

Each figure reads its figure source data (outputs/data/figure_source/<file id>.json, written by
tools/figures_report.py) and nothing else; nothing is recomputed here.

Sign rules (figures/draw.py): the floor-area bridges (D10, D11) are waterfalls of cumulative values: a positive band
a filled step up from the running total, a negative band (Overbuild absorbed, Unconsented additions, retirement
villages, or any band negative in a run) an unfilled, unhatched segment outlined in its band colour hanging down
from the running total (the top of the positive stack), so the last step ends at the net total, drawn as the
black 'Total, in scope' bar. Only the surge band (Recent replacement surge) is hatched.
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
    a.set_ylabel(f"Dwellings completed, {c['target_year']}" if pipeline_mode else
                 'Dwellings consented, January–July 2026')
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'd', f"{c['target_year']} check" if pipeline_mode else '2026 check')
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
                          'consents observed January–July 2026 against the model, which uses no 2026 data.'),
                  source=['figure_source/D14_hindcast.json', 'baseline/validation.json'])


# ---------------------------------------------------------------------------
# SF8 (D15) reality checks
# ---------------------------------------------------------------------------
def sf8_reality_checks():
    fid = 'SF8_reality_checks'
    d = D.src('D15_reality_checks')
    labels = d['labels']
    fig, ax = plt.subplots(3, 3, figsize=S.figsize('double', 165))
    ax = ax.ravel()
    for i, key in enumerate(d['order']):
        p = d['panels'][key]
        a = ax[i]
        lo, hi = p['range_1991_2025']
        a.axhspan(lo, hi, color=S.MUTED, alpha=S.FIXED_FADES['history_range_span'], lw=0, label='1991–2025 range')
        hs = p['history']
        if key == 'removals_net':                     # census-interval rates: a step function, not interpolated
            a.plot(hs.index, hs, color=S.INK, lw=S.LW, label='History')
        else:
            P.line(a, hs.index, hs, color=S.INK, lw=S.LW, label='History')
        for k in VARS:
            y = p['projection'][k]
            P.line(a, y.index, y, label=labels[k], **_scen_line(k))
        P.split(a)
        a.set_xlim(1991, 2050)
        a.set_ylabel(p['ylabel'])
        a.ticklabel_format(axis='y', style='plain', useOffset=False)
        P.panel(a, 'abcdefg'[i], p['title'])
    rem = d['removals_pct_of_2025_stock']
    txt = '\n'.join(f"{labels[k]}: {rem[k]:.1f}%" for k in VARS)
    ax[1].text(0.02, 0.97, 'Removals 2026–2050,\n% of the 2025 stock:\n' + txt, transform=ax[1].transAxes,
               va='top', fontsize=S.FONT_MIN, bbox=dict(facecolor='white', alpha=S.FIXED_FADES['label_box'], edgecolor='none', pad=1))
    m = d['m2_per_res_max']
    ax[3].set_ylim(0, 300)
    ax[3].text(0.02, 0.97, f"Off scale: {int(m['year'])}, {m['value']:,.0f} m² per person\n(near-zero population "
               "growth)", transform=ax[3].transAxes, va='top', fontsize=S.FONT_MIN,
               bbox=dict(facecolor='white', alpha=S.FIXED_FADES['label_box'], edgecolor='none', pad=1))
    a = ax[7]
    chg = np.asarray(d['handover_changes_pct'], float)
    h = d['handover']
    counts, _, _ = a.hist(chg, bins=14, **S.fill(S.VALIDATION['handover_history']))
    a.set_ylim(0, a.get_ylim()[1] * 1.45)                 # room for the legend above the bars
    ytop = 1.1 * float(np.max(counts))                    # the two markers stop below the legend
    a.vlines(h['step_pct'], 0, ytop, color=S.VALIDATION['handover_step'], lw=S.LW_BOLD,
             label=f"{h['last_observed_year']} → {h['first_model_year']} handover (observed → model): "
                   + P.minus(f"{h['step_pct']:+.1f}%"))
    a.vlines(h['hist_median_pct'], 0, ytop, color=S.INK, lw=S.LW, linestyles='--',
             label="Median year, 1992–2025: " + P.minus(f"{h['hist_median_pct']:+.1f}%"))
    a.set_xlabel('Change from the previous year (%)')
    a.set_ylabel('Number of years')
    a.legend(loc='upper left', fontsize=S.FONT_MIN)
    P.panel(a, 'h', 'Handover vs annual changes in floor area')
    ax[8].axis('off')
    h_, l_ = ax[0].get_legend_handles_labels()
    ax[8].legend(h_, l_, loc='center', frameon=False)
    fig.tight_layout()
    S.save_figure(fig, fid,
                  note='Projection 2026–2050 against the 1991–2025 range (grey band); a: in scope and retirement '
                       'villages; the exceedances are tabulated in outputs/reports/reality_checks.md. h: the 2026 → '
                       '2027 step of the Reference (2026 observed, 2027 the first model year) against the '
                       'year-to-year changes in consented floor area, 1992–2025.',
                  source=['figure_source/D15_reality_checks.json'])


FIGURES = {'SF6_hindcast': sf6_hindcast, 'SF8_reality_checks': sf8_reality_checks}
