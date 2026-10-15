"""Validation and report diagnostics (MODEL v3.0.0, draw only): D07_net_replacement_rate, D10_floor_area_bridge,
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

VARS = ('LOW', 'REF', 'HIGH')
RV_OUTLINE = '#7A7A7A'          # retirement villages (out of scope; not a demand band): grey outline


def _src(fid):
    return [f'figure_source/{fid}.json']


def _scen_line(k):
    st = dict(S.SCENARIO[k])
    st.pop('label')
    return st


# ---------------------------------------------------------------------------
# D07 net replacement rate
# ---------------------------------------------------------------------------
def d07():
    fid = 'D07_net_replacement_rate'
    d = D.src(fid)
    fy = d['years']
    fig, a = plt.subplots(figsize=S.figsize('double', 72))
    a.axvspan(2013, 2018, color=S.MUTED, alpha=0.10, lw=0, label='2013 → 2018: census empty / away definition break')
    c = d['census']
    for i, (y0, y1, r) in enumerate(zip(c['y0'], c['y1'], c['rate'])):
        a.hlines(100 * r, y0, y1, color=S.INK, lw=S.LW_BOLD,
                 label='Census intervals (dwelling counts, under-construction corrected)' if i == 0 else None)
    for k in VARS:
        a.plot(fy, 100 * np.asarray(d['paths'][k]), label=d['labels'][k], **_scen_line(k))
    a.axhline(100 * d['demolition_rate'], color=S.MUTED, ls='--', lw=S.LW,
              label=f"BRANZ demolition (component of the long-run rate), {100 * d['demolition_rate']:.3f}%")
    a.axhline(0, color=S.INK, lw=S.LW_THIN)
    P.split(a)
    a.set_xlim(1986, 2050)
    a.set_ylabel("Net replacement (% of the previous year's stock per year)")
    a.legend(loc='upper left', fontsize=S.FONT_SMALL)
    w = [int(x) for x in d['window']]
    S.save_figure(fig, fid,
                  note=f"Net replacement rate (demolition net of unconsented additions). Long run {w[0]}–{w[1]}: "
                       f"{100 * d['long_rate']:.3f}% per year; 2018–23: {100 * d['rate_recent']:.3f}% per year. Each "
                       f"step is one intercensal interval; the 2018–23 step is a single interval. Negative values "
                       f"mean the stock grew by more than consented new building, i.e. more dwellings appeared "
                       f"through conversions and unconsented additions than were demolished.",
                  source=_src(fid))


# ---------------------------------------------------------------------------
# D10 / D11 floor-area bridge (waterfall)
# ---------------------------------------------------------------------------
def _bridge_label(b, split):
    if b == 'retirement_villages':
        return N.BAND_DETAIL['retirement_villages']
    if split and b == 'replacement':
        return N.BANDS['replacement'] + ' (BRANZ rate)'
    if split and b == 'unconsented':
        return N.BANDS['unconsented'] + ' (calibrated residual)'
    return N.BANDS[b]


def _neg_style(b):
    if b == 'retirement_villages':
        return dict(facecolor='none', edgecolor=RV_OUTLINE, linewidth=S.LW_OUTLINE, hatch=None)
    return P.negative_bar_style(b)


def _bridge(fid, note, split):
    d = D.src(fid)
    bands = list(d['bands'])
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 96), sharey=True)
    pad = 0.8
    for a, k, letter in zip(ax, VARS, 'abc'):
        b = d['bridge'][k]
        cum = 0.0
        for i, bid in enumerate(bands):
            v = float(b['values'][bid])
            if v >= 0:
                a.bar(i, v, bottom=cum, width=0.7, gid='band_segment', **P.band_style(bid))
            else:                     # negative: unfilled outline hanging from the running total
                a.bar(i, -v, bottom=cum + v, width=0.7, gid=P.NEG_BAR_GID, **_neg_style(bid))
            a.text(i, cum + max(v, 0) + pad, f'{v:+.1f}', ha='center', fontsize=S.FONT_MIN)
            cum += v
        net = float(b['total_in_scope'])
        if abs(cum - net) > 1e-9 * max(abs(net), 1.0):
            raise P.SignError(f'STOP: {fid} {k}: the bridge does not end at the in-scope total ({cum} vs {net}).')
        n = len(bands)
        a.bar(n, net, color=S.INK, width=0.7, gid=P.NET_GID)
        a.text(n, net + pad, f'{net:.1f}', ha='center', fontsize=S.FONT_MIN, fontweight='bold')
        if split:
            s = float(b['values']['replacement']) + float(b['values']['unconsented'])
            a.text(0.86, 0.30, f'Demolition + unconsented\n= {s:+.1f} (identified)', transform=a.transAxes,
                   ha='right', va='center', fontsize=S.FONT_MIN)
        a.set_xticks(range(n + 1))
        a.set_xticklabels([_bridge_label(x, split) for x in bands] + ['Total, in scope'], rotation=90,
                          fontsize=S.FONT_MIN)
        a.grid(axis='x', visible=False)
        a.set_ylim(0, None)
        P.panel(a, letter, d['labels'][k])
    top = max(max(np.cumsum([float(d['bridge'][k]['values'][x]) for x in bands]).max(),
                  float(d['bridge'][k]['total_in_scope'])) for k in VARS)
    ax[0].set_ylim(0, top * 1.08 + pad)
    ax[0].set_ylabel('Floor area 2026–2050 (Mm²)')
    fig.tight_layout()
    S.save_figure(fig, fid, note=note, source=_src(fid))


def d10():
    _bridge('D10_floor_area_bridge',
            'Each bar is one demand band, 2026–2050 (median population); the 2026 overbuild (market excess) and the '
            'overbuild absorbed are separate bands; negative bands (overbuild absorbed, unconsented additions, '
            'retirement villages) are outlined, hanging from the running total. Retirement-village units are out of '
            'scope and leave the total as a negative step.', split=False)


def d11():
    _bridge('D11_floor_area_bridge_split',
            'Appendix: demolition replacement and unconsented additions as in D10, here labelled by their source: '
            'the split assumes the BRANZ demolition rate; only their sum (the net replacement, annotated) is '
            'identified by the census data.', split=True)


# ---------------------------------------------------------------------------
# D12 conversion chain
# ---------------------------------------------------------------------------
def d12():
    fid = 'D12_conversion_chain'
    d = D.src(fid)
    yrs = [int(y) for y in d['years']]
    chain = [('Population growth', 'dpop', dict(color=S.INK)),
             ('Households formed', 'd_hh', dict(color=S.ACCENT_ORANGE)),
             ('Dwellings built', 'built', dict(color=S.MUTED, ls='--', lw=S.LW_BOLD)),
             ('Floor area', 'gfa', dict(color=S.ACCENT_BLUE)),
             ('Carbon', 'carbon', dict(color=S.PATHWAY['P4']))]
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 70))
    for lab, key, st in chain:
        s_ = d['chain'][key].loc[yrs]
        ax[0].plot(yrs, 100 * s_ / s_.loc[2027], label=lab, **dict(dict(lw=S.LW), **st))
    ax[0].axhline(100, color=S.INK, lw=S.LW_THIN)
    ax[0].set_xlim(yrs[0], yrs[-1])
    ax[0].set_ylabel('Index, 2027 = 100')
    ax[0].legend(loc='lower left', fontsize=S.FONT_MIN)
    P.panel(ax[0], 'a', 'Conversion chain, Reference')
    lo, hi = np.inf, -np.inf
    for k in VARS:
        ci = d['intensity'][k]
        ax[1].plot(ci.index, ci, label=d['labels'][k], **_scen_line(k))
        lo, hi = min(lo, ci.min()), max(hi, ci.max())
    pad = 0.15 * max(hi - lo, 1.0)
    ax[1].set_ylim(lo - pad, hi + pad)
    ax[1].set_xlim(2026, 2050)
    ax[1].set_ylabel('Carbon intensity (kg CO₂e per m²)')
    ax[1].legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel(ax[1], 'b', 'Carbon per m² of new floor area')
    fig.tight_layout()
    S.save_figure(fig, fid,
                  note='a: 2026 is not the base year: it is observed building and carries the one-off population '
                       'shortfall and the 2026 overbuild. b: decarbonisation, maintenance within 2026–2050 and the '
                       'soil-bearing share; typology shares held.',
                  source=_src(fid))


# ---------------------------------------------------------------------------
# D14 hindcast
# ---------------------------------------------------------------------------
def d14():
    fid = 'D14_hindcast'
    v = D.src(fid)
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
                       **dict(_scen_line(k), lw=S.LW))
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
    S.save_figure(fig, fid,
                  note='Rolling-origin hindcast of dwellings built (cumulative), each origin projected with the '
                       'information available then; errors at the end of each window, vacancy on the consistent '
                       'definition unless noted. d: consents observed January–July 2026 against the model, which '
                       'uses no 2026 data.',
                  source=_src(fid))


# ---------------------------------------------------------------------------
# D15 reality checks
# ---------------------------------------------------------------------------
def d15():
    fid = 'D15_reality_checks'
    d = D.src(fid)
    labels = d['labels']
    fig, ax = plt.subplots(3, 3, figsize=S.figsize('double', 165))
    ax = ax.ravel()
    for i, key in enumerate(d['order']):
        p = d['panels'][key]
        a = ax[i]
        lo, hi = p['range_1991_2025']
        a.axhspan(lo, hi, color=S.MUTED, alpha=0.12, lw=0, label='1991–2025 range')
        hs = p['history']
        a.plot(hs.index, hs, color=S.INK, lw=S.LW, label='History')
        for k in VARS:
            y = p['projection'][k]
            a.plot(y.index, y, label=labels[k], **_scen_line(k))
        P.split(a)
        a.set_xlim(1991, 2050)
        a.set_ylabel(p['ylabel'])
        a.ticklabel_format(axis='y', style='plain', useOffset=False)
        P.panel(a, 'abcdefg'[i], p['title'])
    rem = d['removals_pct_of_2025_stock']
    txt = '\n'.join(f"{labels[k]}: {rem[k]:.1f}%" for k in VARS)
    ax[1].text(0.02, 0.97, 'Removals 2026–2050,\n% of the 2025 stock:\n' + txt, transform=ax[1].transAxes,
               va='top', fontsize=S.FONT_MIN, bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=1))
    m = d['m2_per_res_max']
    ax[3].set_ylim(0, 300)
    ax[3].text(0.02, 0.97, f"Off scale: {int(m['year'])}, {m['value']:,.0f} m² per person\n(near-zero population "
               "growth)", transform=ax[3].transAxes, va='top', fontsize=S.FONT_MIN,
               bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=1))
    a = ax[7]
    chg = np.asarray(d['handover_changes_pct'], float)
    h = d['handover']
    counts, _, _ = a.hist(chg, bins=14, **S.fill('#BDBDBD'))
    a.set_ylim(0, a.get_ylim()[1] * 1.45)                 # room for the legend above the bars
    ytop = 1.1 * float(np.max(counts))                    # the two markers stop below the legend
    a.vlines(h['step_2026_2027_pct'], 0, ytop, color=S.ACCENT_ORANGE, lw=S.LW_BOLD,
             label=f"2026 → 2027 handover (observed → model): {h['step_2026_2027_pct']:+.1f}%")
    a.vlines(h['hist_median_pct'], 0, ytop, color=S.INK, lw=S.LW, linestyles='--',
             label=f"Median year, 1992–2025: {h['hist_median_pct']:+.1f}%")
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
                  source=_src(fid))


# ---------------------------------------------------------------------------
# D19 variants
# ---------------------------------------------------------------------------
def d19():
    fid = 'D19_variants'
    d = D.src(fid)
    labels = d['labels']
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 70), gridspec_kw=dict(width_ratios=[2, 1, 1]))
    a = ax[0]
    hg = d['history_gfa']
    a.plot(hg.index, hg, color=S.INK, lw=S.LW, label='History (built)')
    mc = d.get('mc_band')
    if mc:
        a.fill_between(mc['lo'].index, mc['lo'], mc['hi'], label='Monte Carlo 5–95% (Reference)', **S.MC_BAND)
    for k in VARS:
        g = d['gfa'][k]
        a.plot(g.index, g, label=labels[k], **_scen_line(k))
    P.split(a)
    a.set_xlim(1991, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Floor area (Mm² per year)')
    a.legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel(a, 'a', 'Annual floor area built')
    ks = list(VARS)
    ticklabels = [N.SCENARIOS[k].replace(' replacement', '\nreplacement') for k in ks]
    a = ax[1]
    a.bar(range(len(ks)), [d['gfa_cumulative'][k] for k in ks], color=[S.SCENARIO[k]['color'] for k in ks],
          width=0.62)
    a.set_xticks(range(len(ks)))
    a.set_xticklabels(ticklabels, fontsize=S.FONT_MIN)
    a.set_ylabel('Floor area 2026–2050 (Mm²)')
    a.grid(axis='x', visible=False)
    P.panel(a, 'b', 'Floor area 2026–2050')
    a = ax[2]
    # the totals only (maintenance is drawn as its own layer only in the band and stage breakdowns)
    tot = [float(d['carbon_cumulative_kt'][k]) for k in ks]
    a.bar(range(len(ks)), tot, color=[S.SCENARIO[k]['color'] for k in ks], width=0.62)
    for i, v in enumerate(tot):
        a.text(i, v, P.fmt_kt(v), ha='center', va='bottom', fontsize=S.FONT_MIN)
    a.set_xticks(range(len(ks)))
    a.set_xticklabels(ticklabels, fontsize=S.FONT_MIN)
    a.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(a.yaxis)
    a.grid(axis='x', visible=False)
    P.panel(a, 'c', 'Carbon 2026–2050')
    fig.tight_layout()
    S.save_figure(fig, fid, source=_src(fid))


FIGURES = {'D07_net_replacement_rate': d07, 'D10_floor_area_bridge': d10,
           'D12_conversion_chain': d12, 'D14_hindcast': d14, 'D15_reality_checks': d15, 'D19_variants': d19}
