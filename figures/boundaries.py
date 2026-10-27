"""Supplementary SF9 (MODEL v4.3.0; the D22 diagnostic before): how the planetary-boundary budgets AR and AtP are
built: the two boundaries, the population modifier and the components.

Drawn from the figure source data written by boundaries.py (outputs/data/figure_source/D22_boundaries.json) only; the
model is never run here. The other AESA diagnostics (D18, D21, D23-D27) are no longer drawn (MODEL v4.3.0); their data
files are still written.
"""

import re

import matplotlib.pyplot as plt

from figures import data as D
from figures import draw as P
from figures import style as S


def _src(fid):
    return D.src(fid), [f'figure_source/{fid}.json']


# MODEL v4.3.0 (suite rule: plain English, no internal symbols in a figure): the D22 component rows are stored with the
# aesa.py notation; each is shown under a plain-English label (definitions: aesa.py module docstring, Horup et al. 2025
# Eq. 1, Hjalsted et al. 2021 Eqs. 5-6 and S1). The symbol a row must start with is asserted, so a reordered table stops.
PLAIN_COMPONENTS = (('SOS', 'Global safe operating space,\nclimate (kg CO₂e per year)'),
                    ('I_glob', 'Global annual emissions, same\nsource (kg CO₂e per year)'),
                    ('Ī_sec,base', 'Sector emissions, mean\n{window} (kt CO₂e per year)'),
                    ('α', 'Ability-to-pay scaling factor\n(base year {b}, PPP)'),
                    ('g_W / g_NZ', 'World / New Zealand\nGDP per person'),
                    ('s_sec', 'Sector share of New Zealand\nfinal consumption expenditure'),
                    ('B_AtP / B_AR', 'AtP / AR boundary ratio\n(every year)'))


def _plain_table(rows):
    assert len(rows) == len(PLAIN_COMPONENTS), rows
    out = []
    for (label, value), (sym, plain) in zip(rows, PLAIN_COMPONENTS):
        assert label.startswith(sym), (label, sym)
        w = re.search(r'(\d{4}–\d{4})', label)
        b = re.search(r'b = (\d{4})', label)
        out.append([plain.format(window=w.group(1) if w else '', b=b.group(1) if b else ''), value])
    return out


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
    P.panel(a, 'b', f'Population modifier: New Zealand share of\nworld population, relative to {t0}')
    a = fig.add_subplot(gs[2])
    a.axis('off')
    t = a.table(cellText=_plain_table(d['table']), colLabels=['Component', 'Value'], cellLoc='left',
                colWidths=[0.72, 0.28], bbox=[0, 0, 1, 1])     # MODEL v4.3.0: the table fills the panel, below its title
    t.auto_set_font_size(False)
    t.set_fontsize(S.FONT_MIN)
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
