"""The diagnostics of the planetary-boundary layer (AESA; figure_plan.DIAGNOSTICS['boundaries']): D18 every AESA
sensitivity row, D21 the Monte Carlo fan with the AR base window, D22 the boundaries, D23 the annual level of
exceedance, D24 the headroom, D25 / D26 annual and cumulative carbon by demand band, D27 the variants.

Drawn from the figure source data written by boundaries.py (outputs/data/figure_source/<figure id>.json) only; the
model is never run here. Every boundary is drawn with its zones and AtP dotted (style.boundary_zones /
boundary_hzones). Sign rules (figures/draw.py): D25 and D26 stack the positive bands up from zero and the negative
bands (overbuild absorbed, unconsented additions) down from zero, the net a black line.
"""
import textwrap

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import naming as N
from figures import audit as A
from figures import data as D
from figures import draw as P
from figures import style as S

VARS = ('LOW', 'REF', 'HIGH', 'VHIGH')            # MODEL v3.3.0: + Very High replacement


def _src(fid):
    return D.src(fid), [f'figure_source/{fid}.json']


def scen_line(k, **kw):
    st = dict(S.SCENARIO[k])
    st.pop('label')
    st.update(kw)
    return st


def _area_handles(bids):
    """Legend entries of bands drawn as filled areas (time series: a negative band is a filled area below zero,
    in its band colour)."""
    return [Patch(label=P.band_label(b), **dict(P.band_style(b), edgecolor='#555555', linewidth=S.LW_THIN))
            for b in bids]


def _net_handle():
    return Line2D([0], [0], color=S.INK, lw=S.LW, label='Net total')


# ---------------------------------------------------------------------------
# D18
# ---------------------------------------------------------------------------
def d18():
    """Cumulative LoE 2026-2050 of every AESA sensitivity row, AR and AtP panels (change vs the Reference)."""
    d, src = _src('D18_aesa_sensitivity')
    s, ref = d['rows'], d['reference']
    h = 24 + 4.4 * len(s)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', h))
    for a, k, colour, letter in ((ax[0], 'AR', S.AR, 'a'), (ax[1], 'AtP', S.ATP, 'b')):
        v = s[f'cum_LoE_{k}'].values - ref[f'cum_LoE_{k}']
        order = np.argsort(np.abs(v))
        a.barh(range(len(s)), v[order], color=colour, height=0.7)
        a.set_yticks(range(len(s)))
        a.set_yticklabels([textwrap.fill(s['label'].values[i], 40) for i in order], fontsize=S.FONT_MIN,
                          linespacing=1.0)
        for i, j in enumerate(order):
            a.annotate(f"{s[f'cum_LoE_{k}'].values[j]:.2f} ({s[f'{k}_vs_ref_pct'].values[j]:+.1f}%)",
                       (max(v[j], 0.0), i), xytext=(2, 0), textcoords='offset points', ha='left', va='center',
                       fontsize=S.FONT_MIN)
        a.set_xlim(min(0.0, v.min()) - 0.05 * np.ptp(np.r_[v, 0]), v.max() + 0.45 * np.ptp(np.r_[v, 0]))
        a.axvline(0, color=S.INK, lw=S.LW_THIN)
        a.set_xlabel('Change in cumulative level of exceedance vs the Reference')
        a.grid(axis='y', visible=False)
        P.panel(a, letter, f"{S.BOUNDARY[k]['label']}, 2026–2050 (Reference {ref[f'cum_LoE_{k}']:.2f})")
    fig.tight_layout()
    S.save_figure(fig, 'D18_aesa_sensitivity',
                  note='One setting changed per row; labels show the cumulative LoE of that row and its change from the '
                       'Reference. Rows that do not enter a principle (e.g. the GDP measure for AR) show no change. '
                       'Percentages are relative to carbon 2026–2050 (time-resolved accounting); fixed absolute terms '
                       'such as soil carbon loss therefore show larger percentage effects than under whole-life '
                       'accounting. The largest effects on the AR and AtP LoE, grouped: Extended Data ED4 (carbon: ED1).',
                  source=src)


# ---------------------------------------------------------------------------
# D21
# ---------------------------------------------------------------------------
def d21():
    """The Monte Carlo fan of the Reference's embodied carbon with the boundary bands, and the sector carbon of the
    AR base window as a thin line joined to the projection's 2026 median (no gap between 2025 and 2026)."""
    d, src = _src('D21_fan_and_boundaries')
    w0, w1 = (int(v) for v in d['base_window'])
    x = d['mc_years']
    hx, hy = d['history_years'], d['history_kt']
    fig, ax = plt.subplots(figsize=S.figsize('double', 80))
    ax.axvspan(w0 - 0.5, w1 + 0.5, color=S.MUTED, alpha=0.10, lw=0, label=f'AR base window {w0}–{w1}')
    ax.fill_between(x, d['I_sec_p5_kt'], d['I_sec_p95_kt'], label='Embodied carbon, Monte Carlo 5–95%', **S.MC_BAND)
    ax.plot(x, d['I_sec_p50_kt'], color=S.REFERENCE, lw=S.LW_BOLD, label='Embodied carbon, Monte Carlo median')
    # history: thin and fine, joined to the 2026 median (the step 2025 -> 2026 is drawn, not left as a gap)
    ax.plot(list(hx) + [x[0]], list(hy) + [d['I_sec_p50_kt'][0]], color=S.INK, lw=S.LW_THIN,
            label='Sector carbon in the base window, at 2025 factors (accounting as the projection)')
    S.boundary_zones(ax, x, d['B_AR_p50_kt'], d['B_AtP_p50_kt'], lines=False)
    for key in ('AR', 'AtP'):
        st = dict(S.BOUNDARY[key])
        lab = st.pop('label')
        ax.fill_between(x, d[f'B_{key}_p5_kt'], d[f'B_{key}_p95_kt'], color=st['color'], alpha=0.25, lw=0,
                        gid=A.BOUNDARY)
        ax.plot(x, d[f'B_{key}_p50_kt'], gid=A.BOUNDARY, label=f'{lab}: Monte Carlo median and 5–95%', **st)
    P.split(ax)
    ax.set_xlim(w0 - 0.5, 2050)
    ax.set_ylim(0, 1.6 * max(np.max(hy), np.max(d['I_sec_p95_kt'])))
    ax.set_ylabel('Embodied carbon (kt CO₂e per year)')
    ax.legend(loc='upper left', fontsize=S.FONT_SMALL)
    spread = 100 * float(np.max(np.abs(np.r_[d['B_AR_p95_kt'] / d['B_AR_p50_kt'] - 1,
                                              d['B_AR_p5_kt'] / d['B_AR_p50_kt'] - 1])))
    fig.tight_layout()
    S.save_figure(fig, 'D21_fan_and_boundaries',
                  note=f'Reference. AR base window {w0}–{w1} at 2025 factors, soil only on non-replacement floor area '
                       '(as the projection); the thin history line is joined to the 2026 Monte Carlo median. Boundary '
                       'bands: AR varies with the NZ population of each draw and its AR base (recomputed from the '
                       'draw\'s 2025 carbon factors), AtP with population only; AR '
                       f'5th–95th within {spread:.1f}% of the median in every year.',
                  source=src)


# ---------------------------------------------------------------------------
# D22
# ---------------------------------------------------------------------------
def d22():
    """The boundaries AR and AtP (log axis), the population modifier and the components."""
    d, src = _src('D22_boundaries')
    yb = d['years']
    t0, t1 = int(yb[0]), int(yb[-1])
    ar, atp = d['B_AR_kt'], d['B_AtP_kt']
    fig = plt.figure(figsize=S.figsize('double', 72))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.2, 1, 1.15])
    a = fig.add_subplot(gs[0])
    P.boundary_lines(a, yb, ar, atp)
    a.set_yscale('log')
    for s_ in (ar, atp):
        for i, ha, dx in ((0, 'left', 2), (-1, 'right', -2)):
            a.annotate(f'{s_[i]:,.1f}', (yb[i], s_[i]), xytext=(dx, 4), textcoords='offset points', ha=ha,
                       fontsize=S.FONT_MIN)
    a.set_xlim(t0, t1)
    a.set_ylim(atp.min() / 1.6, ar.max() * 1.6)
    P.log_ticks(a.yaxis, (20, 50, 100, 200, 500))
    a.set_ylabel('Boundary (kt CO₂e per year, log scale)')
    a.legend(loc='center right', fontsize=S.FONT_MIN)
    P.panel(a, 'a', f'Boundaries {t0}–{t1}')
    a = fig.add_subplot(gs[1])
    a.plot(yb, d['population_modifier'], color=S.INK, lw=S.LW)
    a.axhline(1, color=S.MUTED, lw=S.LW_THIN, ls=':')
    a.set_xlim(t0, t1)
    a.set_ylabel(f'Index ({t0} = 1)')
    P.panel(a, 'b', f'Population modifier\n[P_NZ(t) / P_NZ({t0})] · [P_W({t0}) / P_W(t)]')
    a = fig.add_subplot(gs[2])
    a.axis('off')
    t = a.table(cellText=d['table'], colLabels=['Component', 'Value'], loc='center', cellLoc='left',
                colWidths=[0.74, 0.30])
    t.auto_set_font_size(False)
    t.set_fontsize(S.FONT_MIN)
    t.scale(1, 1.5)
    for cell in t.get_celld().values():
        cell.set_linewidth(S.LW_THIN)
        cell.set_edgecolor('#BDBDBD')
    P.panel(a, 'c', 'Components')
    fig.tight_layout()
    S.save_figure(fig, 'D22_boundaries',
                  note=f"{d['pair_label']}. Log axis: the AtP boundary is {d['atp_pct_of_ar']:.1f}% of the AR boundary "
                       'in every year: both scale with P_NZ(t) / P_W(t) (static design), so their ratio is constant.',
                  source=src)


# ---------------------------------------------------------------------------
# D23
# ---------------------------------------------------------------------------
def d23():
    """Annual level of exceedance of AR and AtP by variant, Monte Carlo 5-95% (Reference a band, Low / High thin
    lines), log axis."""
    d, src = _src('D23_annual_loe')
    py = d['years']
    r_ = d['atp_over_ar']                       # AtP / AR, constant in every year (static design)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 74), sharey=True)
    for a, k, letter in ((ax[0], 'AR', 'a'), (ax[1], 'AtP', 'b')):
        for name in d['variants']:
            v = d['loe'][f'{name}_{k}']
            if name == 'REF':
                a.fill_between(v['mc_years'], v['p5'], v['p95'], **S.MC_BAND)
            else:
                for q in ('p5', 'p95'):
                    a.plot(v['mc_years'], v[q], **scen_line(name, lw=S.LW_THIN))
            a.plot(py, v['loe'], label=f"{N.SCENARIOS[name]} ({'band' if name == 'REF' else 'thin lines'}: "
                                       'Monte Carlo 5–95%)', **scen_line(name))
        if k == 'AR':                           # LoE AR: AR at 1, AtP at B_AtP / B_AR
            S.boundary_hzones(a, 1.0, r_)
        else:                                   # LoE AtP: AtP at 1, AR at B_AR / B_AtP
            S.boundary_hzones(a, 1.0 / r_, 1.0)
        a.set_yscale('log')
        a.set_xlim(py[0], py[-1])
        P.log_ticks(a.yaxis, (0.5, 1, 2, 5, 10, 20, 50, 100))
        P.panel(a, letter, f"Level of exceedance, {S.BOUNDARY[k]['label']}")
    ax[0].set_ylabel('Level of exceedance (annual carbon / boundary, log scale)')
    fig.legend(*ax[0].get_legend_handles_labels(), loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01),
               frameon=False, fontsize=S.FONT_SMALL)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    S.save_figure(fig, 'D23_annual_loe',
                  note=f"{d['pair_label']}. Log axis: the AtP LoE is {1 / r_:.1f} × the AR LoE in every year. Monte "
                       'Carlo bands: within-variant uncertainty (population, dwelling size, completion rate, carbon '
                       f"factors). Carbon: {d['factor_note']}.",
                  source=src)


# ---------------------------------------------------------------------------
# D24
# ---------------------------------------------------------------------------
def d24():
    """Carbon per m2, floor area and carbon per new dwelling of the Reference and the values that would fit each
    boundary (log axes)."""
    d, src = _src('D24_headroom')
    py = d['years']
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 78))
    specs = [(ax[0], 'a', 'Carbon per m² that fits each boundary', 'Carbon intensity (kg CO₂e per m², log scale)',
              'intensity', 'Carbon per m², Reference', (2, 5, 10, 20, 50, 100, 200, 500)),
             (ax[1], 'b', 'Floor area that fits each boundary', 'Floor area (Mm² per year, log scale)',
              'floor_area', 'Floor area built, Reference', (0.1, 0.2, 0.5, 1, 2, 5, 10)),
             (ax[2], 'c', 'Carbon per new dwelling', 'Carbon per new dwelling (t CO₂e, log scale)',
              'per_dwelling', 'Carbon per new dwelling, Reference', (1, 2, 5, 10, 20, 50, 100))]
    for a, letter, title, ylab, key, lab, ticks in specs:
        v = d[key]
        a.plot(py, v['reference'], label=lab, **scen_line('REF'))
        P.boundary_lines(a, py, v['fit_AR'], v['fit_AtP'], label=False)
        a.set_yscale('log')
        P.log_ticks(a.yaxis, ticks)
        a.set_xlim(py[0], py[-1])
        a.set_ylabel(ylab)
        P.panel(a, letter, title)
    h_ = [Line2D([0], [0], **scen_line('REF'))] + [Line2D([0], [0], **{k: v for k, v in S.BOUNDARY[b].items()
                                                                       if k != 'label'}) for b in ('AR', 'AtP')]
    fig.legend(h_, ['Reference', 'Fitting the AR boundary', 'Fitting the AtP boundary'], loc='lower center', ncol=3,
               bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    S.save_figure(fig, 'D24_headroom',
                  note='Reference, median population. Fitting carbon per m² = B(t) / floor area(t); fitting floor area '
                       '= B(t) / (carbon per m² of the Reference); per dwelling = B(t) / dwellings built(t), dwellings '
                       f"= floor area / blended dwelling size. Carbon: {d['factor_note']}; carbon per m² also varies "
                       f"with the mix and the soil-bearing share. {d['pair_label']}.",
                  source=src)


# ---------------------------------------------------------------------------
# D25 / D26
# ---------------------------------------------------------------------------
def _bands_vs_boundaries(fid, bands, net, ar, atp, ylabel, note, src, thousands=False):
    d = D.src(fid)
    py = d['years']
    bids = list(d['band_ids'])
    fig, ax = plt.subplots(figsize=S.figsize('double', 80))
    P.stack_series(ax, py, [(b, d[bands][b]) for b in bids], net=d[net])
    P.boundary_lines(ax, py, d[ar], d[atp])
    ax.set_xlim(py[0], py[-1])
    ax.set_ylabel(ylabel)
    if thousands:
        P.thousands(ax.yaxis)
    fig.legend(handles=_area_handles(bids) + [_net_handle()] + S.boundary_handles(), loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.01), frameon=False, handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    S.save_figure(fig, fid, note=note + d['caption'], source=src)


def d25():
    """Annual carbon by demand band (positive up, negative down from zero, net a black line) against AR and AtP."""
    fid = 'D25_annual_carbon_by_band'
    _bands_vs_boundaries(fid, 'bands_kt', 'net_kt', 'B_AR_kt', 'B_AtP_kt', 'Embodied carbon (kt CO₂e per year)',
                         'Reference, median population; positive bands stacked up from zero, negative bands (overbuild '
                         'absorbed, unconsented additions) down from zero; the black line is the net annual carbon. ',
                         [f'figure_source/{fid}.json'])


def d26():
    """Cumulative carbon by demand band from 2026 (positive up, negative down from zero, net a black line) against
    the cumulative AR and AtP budgets."""
    fid = 'D26_cumulative_carbon_by_band'
    _bands_vs_boundaries(fid, 'bands_cum_kt', 'net_cum_kt', 'B_AR_cum_kt', 'B_AtP_cum_kt',
                         'Embodied carbon, cumulative from 2026 (kt CO₂e)',
                         'Reference, median population; boundaries cumulated from 2026; positive bands stacked up from '
                         'zero, negative bands down from zero; the black line is the net cumulative carbon. ',
                         [f'figure_source/{fid}.json'], thousands=True)


# ---------------------------------------------------------------------------
# D27
# ---------------------------------------------------------------------------
def d27():
    """Annual (a) and cumulative 2026-2050 (b) carbon of the Low / Reference / High replacement variants against the
    boundaries (totals only)."""
    d, src = _src('D27_variants_vs_boundaries')
    py = d['years']
    vs = list(d['variants'])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=S.figsize('double', 80), gridspec_kw=dict(width_ratios=[2, 1]))
    a1.fill_between(d['mc_years'], d['mc_p5_kt'], d['mc_p95_kt'], label='Monte Carlo 5–95% (Reference)', **S.MC_BAND)
    for key in vs:
        a1.plot(py, d['annual_kt'][key], label=N.SCENARIOS[key], **scen_line(key))
    P.boundary_lines(a1, py, d['B_AR_kt'], d['B_AtP_kt'])
    a1.set_ylim(0, None)
    a1.set_xlim(py[0], py[-1])
    a1.set_ylabel('Embodied carbon (kt CO₂e per year)')
    a1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=S.FONT_MIN)
    P.panel(a1, 'a', 'Annual')
    # the totals only (maintenance is drawn as its own layer only in Fig3 and the band breakdowns)
    a2.bar(range(len(vs)), [d['cumulative_kt'][k] for k in vs], color=[S.SCENARIO[k]['color'] for k in vs],
           width=0.62, label='Embodied carbon 2026–2050')
    v_ar, v_atp = d['B_AR_cum_kt'], d['B_AtP_cum_kt']
    S.boundary_hzones(a2, v_ar, v_atp, label=False)
    for line, (key, v) in zip(a2.get_lines()[-2:], (('AR', v_ar), ('AtP', v_atp))):
        line.set_label(f"{S.BOUNDARY[key]['label']}: {v:,.0f} kt")
    a2.set_xticks(range(len(vs)))
    a2.set_xticklabels([N.SCENARIOS[k].replace(' replacement', '\nreplacement') for k in vs], fontsize=S.FONT_MIN)
    a2.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(a2.yaxis)
    a2.grid(axis='x', visible=False)
    a2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), fontsize=S.FONT_MIN)
    P.panel(a2, 'b', 'Cumulative 2026–2050')
    fig.tight_layout()
    S.save_figure(fig, 'D27_variants_vs_boundaries',
                  note='The boundaries are the same in every variant (same population path). ' + d['caption'],
                  source=src)


FIGURES = {'D18_aesa_sensitivity': d18, 'D21_fan_and_boundaries': d21, 'D22_boundaries': d22,
           'D23_annual_loe': d23, 'D24_headroom': d24, 'D25_annual_carbon_by_band': d25,
           'D26_cumulative_carbon_by_band': d26, 'D27_variants_vs_boundaries': d27}
