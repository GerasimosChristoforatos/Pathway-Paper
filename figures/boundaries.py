"""The diagnostics of the planetary-boundary layer (AESA; figure_plan.DIAGNOSTICS['boundaries']): D18 every AESA
sensitivity row, D21 the Monte Carlo fan with the AR base window, D22 the boundaries, D23 the annual level of
exceedance, D24 the headroom, D25 / D26 annual and cumulative carbon by demand band, D27 the variants.

Drawn from the figure source data written by boundaries.py (outputs/data/figure_source/<figure id>.json) only; the
model is never run here. Every boundary is drawn with its zones and AtP dotted (style.boundary_zones /
boundary_hzones). Sign rules (figures/draw.py): D25 and D26 stack the positive bands up from zero and the negative
bands (overbuild absorbed, unconsented additions) down from zero, the net a black line.
"""

import matplotlib.pyplot as plt

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


# ---------------------------------------------------------------------------
# D22
# ---------------------------------------------------------------------------
def sf9_budget_construction():
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
    P.line(a, yb, d['population_modifier'], color=S.INK, lw=S.LW)
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
    S.save_figure(fig, 'SF9_budget_construction',
                  note=f"{d['pair_label']}. Log axis: the AtP boundary is {d['atp_pct_of_ar']:.1f}% of the AR boundary "
                       'in every year: both scale with P_NZ(t) / P_W(t) (static design), so their ratio is constant.',
                  source=src)


FIGURES = {'SF9_budget_construction': sf9_budget_construction}
