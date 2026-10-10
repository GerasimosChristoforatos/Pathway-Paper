"""
EXTENDED DATA FIGURES (MODEL v2.0.0): ED1-ED10, EXTENDED_DATA.md
===============================================================
Every figure is drawn from the data files of outputs/data/ only (as paper.py, whose helpers it uses:
source data, saving, labels): the grouped sensitivity tables (outputs/data/sensitivity/,
tools/sensitivity_tables.py; docs/SENSITIVITY_PLAN.md), the Monte Carlo of the Reference and the
pathway Monte Carlo, and the pathway runs at the settings the paper does not show (Ambitious,
roll-out by 2030 / 2045, single levers, Low / High replacement).

For each figure this writes, in outputs/extended_data/: ED<n>_<name>.png / .pdf (183 mm) and .csv (every
plotted value: panel, series, x, value, unit), and EXTENDED_DATA.md with every figure and its caption.

    python extended_data.py      (run_all.py runs it after paper.py)
"""
import math
import os
import sys
import textwrap

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import layout as L  # noqa: E402
import naming as N  # noqa: E402
import paper as PP  # noqa: E402
import plotting as P  # noqa: E402
import style as S  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

PLAN = {h['id']: h for h in FP.EXTENDED_DATA}
REF = PP.REF
read_csv, read_json, check = PP.read_csv, PP.read_json, PP.check
REF_GROUPS = ('Demographics', 'Housing stock & calibration', 'Replacement scenario', 'Carbon factors & technology',
              'Accounting')
P5_GROUPS = ('Ambition of one pathway', 'Ambition of all', 'Roll-out timing', 'Replacement scenario', 'Demographics')
PB_GROUPS = ('Carrying capacity', 'Base window', 'Economic measures', 'Population source', 'Replacement scenario')


def source(fid):
    return PP.Source(fid, L.EXTENDED_DATA)


def save(fig, fid, src):
    PP.save(fig, fid, src, 'double')


# line colours of the sensitivity paths (ED3): Okabe-Ito without black (the Reference) and yellow (low contrast
# on white); more rows than colours cycle through the line styles
LINE_COLOURS = [c for c in S.QUALITATIVE if c not in ('#000000', '#F0E442')]


def group_colours(groups):
    """Okabe-Ito colours (style.QUALITATIVE) for the groups, without black (the central line) and the yellow
    (not legible as heading text on white)."""
    cols = [c for c in S.QUALITATIVE if c not in ('#000000', '#F0E442')]
    return {g: cols[k % len(cols)] for k, g in enumerate(groups)}


# ============================================================
# Tornado (ED1, ED2, ED4)
# ============================================================
def tornado(ax, t, value, central, groups, src, panel, unit, fmt, wrap=46):
    """One horizontal bar per row from the central value, rows grouped (group order as given, rows of a group
    in the table's order; the two sides of a paired row on one line), group colour; every value labelled."""
    cols = group_colours(groups)
    y, ticks, labels = 0.0, [], []
    for g in groups:
        rows = t[t['group'] == g]
        if rows.empty:
            continue
        ax.text(0.0, y + 0.15, g, transform=ax.get_yaxis_transform(), ha='right', va='bottom',
                fontsize=S.FONT_SMALL, fontweight='bold', color=cols[g])
        y -= 0.85
        for lab, rr in rows.groupby('row', sort=False):
            vals = [float(v) for v in rr[value]]
            same_side = len(vals) == 2 and (min(vals) - central) * (max(vals) - central) > 0
            # the bar farther from the central value first, so both ends stay visible when they lie on one side
            for _, r in sorted(rr.iterrows(), key=lambda kv: -abs(float(kv[1][value]) - central)):
                v = float(r[value])
                ax.barh(y, v - central, left=central, height=0.62, color=cols[g], edgecolor='white', lw=S.LW_THIN,
                        alpha=0.55 if r['side'] == 'low' else 1.0)
                if not same_side:
                    ax.text(v, y, f' {fmt(v)} ', va='center', ha='left' if v >= central else 'right',
                            fontsize=S.FONT_MIN)
                src.add(panel, f"{g}: {lab} ({r['side']})", 'value', v, unit)
            if same_side:
                far = max(vals, key=lambda v: abs(v - central))
                txt = ' / '.join(fmt(float(v)) for v in rr[value])         # in the order of the row label
                ax.text(far, y, f' {txt} ', va='center', ha='left' if far >= central else 'right', fontsize=S.FONT_MIN)
            ticks.append(y)
            labels.append(textwrap.fill(lab, wrap))
            y -= 1.0
        y -= 0.35
    ax.axvline(central, color=S.INK, lw=S.LW)
    src.add(panel, 'central', 'value', central, unit)
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=S.FONT_MIN, linespacing=1.0)
    ax.set_ylim(y + 0.4, 0.9)
    ax.grid(axis='y', visible=False)
    lo, hi = t[value].min(), t[value].max()
    pad = 0.16 * (max(hi, central) - min(lo, central))
    ax.set_xlim(min(lo, central) - pad, max(hi, central) + pad)
    return len(ticks)


def side_legend():
    return [Patch(facecolor=S.MUTED, alpha=0.55, label='low end of a pair'),
            Patch(facecolor=S.MUTED, label='high end, or a single row')]


def ed1():
    h = PLAN['ED1']
    fid = h['file']
    src = source(fid)
    t = read_csv('sensitivity/reference_carbon.csv')
    c0 = float(t['central_carbon_kt'].iloc[0])
    n = t['row'].nunique()
    fig, ax = plt.subplots(figsize=S.figsize('double', 30 + 4.4 * n))
    tornado(ax, t, 'carbon_kt', c0, REF_GROUPS, src, 'a', 'kt CO2e 2026-2050', lambda v: f'{v:,.0f}', wrap=58)
    ax.set_xlabel(f'Embodied carbon 2026–2050, Reference (kt CO₂e; central {c0:,.0f})')
    P.thousands(ax.xaxis)
    fig.legend(handles=side_legend(), loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.005), frameon=False)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    save(fig, fid, src)
    big = t.assign(eff=(t['change_pct']).abs()).sort_values('eff', ascending=False).head(4)
    cap = (h['caption'] + f" Central: the Reference, {c0:,.0f} kt CO₂e. The largest effects: "
           + '; '.join(f"{r['case']} {r['change_pct']:+.0f}%" for _, r in big.iterrows()) + '. The population rows are '
           'the projection run on the Stats NZ 5th / 95th percentile paths (exact engine path; the one-at-a-time '
           'approximation, carbon per m² of the Reference times the path\'s floor area, stays in '
           'data/baseline/sensitivity_one_at_a_time.csv). The vacancy definition is a calibration check (D06), the '
           'scope of maintenance an AESA row (ED4, D18). Every row with its basis: data/sensitivity/reference_carbon.csv.')
    return dict(caption=cap)


def ed2():
    h = PLAN['ED2']
    fid = h['file']
    src = source(fid)
    t = read_csv('sensitivity/p5_carbon.csv')
    c0 = float(t['central_carbon_kt'].iloc[0])
    bars = t[t['side'] != 'marker']
    mk = t[t['side'] == 'marker'].iloc[0]
    fig, ax = plt.subplots(figsize=S.figsize('double', 30 + 4.6 * bars['row'].nunique()))
    tornado(ax, bars, 'carbon_kt', c0, P5_GROUPS, src, 'a', 'kt CO2e 2026-2050', lambda v: f'{v:,.0f}', wrap=58)
    ax.set_xlabel(f'Embodied carbon 2026–2050, P5 Combined (kt CO₂e; central: Moderate, full roll-out by 2035, {c0:,.0f})')
    P.thousands(ax.xaxis)
    ax.annotate(f"← {mk['row']}: {mk['carbon_kt']:,.0f} kt ({mk['change_pct']:+.0f}%; LoE AR {mk['LoE_AR']:.2f}), "
                'off the axis', xy=(ax.get_xlim()[0], ax.get_ylim()[0] - 0.55), xycoords='data', va='center',
                fontsize=S.FONT_SMALL, color=S.TL, annotation_clip=False)
    ax.set_ylim(ax.get_ylim()[0] - 1.1, ax.get_ylim()[1])                # a row of its own for the marker
    src.add('a', f"marker: {mk['row']}", 'value', mk['carbon_kt'], 'kt CO2e 2026-2050')
    for _, r in t.iterrows():
        src.add('table', f"{r['group']}: {r['row']} ({r['side']})", 'LoE AR', r['LoE_AR'], 'cumulative LoE AR')
        src.add('table', f"{r['group']}: {r['row']} ({r['side']})", 'LoE AtP', r['LoE_AtP'], 'cumulative LoE AtP')
    fig.legend(handles=side_legend(), loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.005), frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, fid, src)
    pop = t[t['group'] == 'Demographics'].set_index('side')
    cap = (h['caption'] + f" Central: P5 Combined (Moderate, full roll-out by 2035), {c0:,.0f} kt CO₂e (LoE AR "
           f"{t['central_LoE_AR'].iloc[0]:.2f}). P1–P4 at Ambitious: one pathway at its Ambitious setting with the others "
           f"at Moderate (new runs). Population 5th / 95th: P5 on the projection's own percentile run (exact engine "
           f"path), LoE AR {pop.loc['low', 'LoE_AR']:.2f}–{pop.loc['high', 'LoE_AR']:.2f} with the budgets of each path. "
           'TL, gradual adoption is a separate marker (off the axis, annotated). The levels of exceedance of every row: '
           'data/sensitivity/p5_carbon.csv.')
    return dict(caption=cap)


def ed4():
    h = PLAN['ED4']
    fid = h['file']
    src = source(fid)
    t = read_csv('sensitivity/planetary_boundary.csv')
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 30 + 4.6 * t['row'].nunique()), sharey=True)
    tornado(a, t, 'LoE_AR', float(t['central_LoE_AR'].iloc[0]), PB_GROUPS, src, 'a', 'cumulative LoE AR',
            lambda v: f'{v:.2f}', wrap=44)
    tornado(b, t, 'LoE_AtP', float(t['central_LoE_AtP'].iloc[0]), PB_GROUPS, src, 'b', 'cumulative LoE AtP',
            lambda v: f'{v:.1f}', wrap=44)
    for t_ in b.texts[:]:
        if t_.get_transform() == b.get_yaxis_transform():
            t_.remove()                                         # group headings once (left panel)
    a.set_xlabel(f"Cumulative LoE 2026–2050, AR\n(Reference {t['central_LoE_AR'].iloc[0]:.2f})")
    b.set_xlabel(f"Cumulative LoE 2026–2050, AtP\n(Reference {t['central_LoE_AtP'].iloc[0]:.1f})")
    P.panel_label(a, 'a')
    P.panel_label(b, 'b')
    fig.legend(handles=side_legend(), loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.005), frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, fid, src)
    cap = (h['caption'] + ' Rows: the carrying capacity (pair C, 1 W/m², vs pair A, 2 °C), the AR base window, the '
           'economic measures of the AtP allocation, the population source and path, and the replacement variants. '
           'Model-input rows other than population and replacement change the carbon only (ED1); the technology and '
           'accounting rows of the AESA table, (vi)–(xiii), stay in data/aesa/sensitivity.csv and D18. Every row with its '
           'basis: data/sensitivity/planetary_boundary.csv.')
    return dict(caption=cap)


# ============================================================
# ED3  Sensitivity paths
# ============================================================
def ed3():
    h = PLAN['ED3']
    fid = h['file']
    src = source(fid)
    t = read_csv('sensitivity/reference_carbon.csv')
    an = read_csv('baseline/sensitivity_annual_carbon.csv')
    ref = an[an['case'] == 'Reference (adopted settings)'].set_index('year')['carbon_kt']
    fig, axes = plt.subplots(2, 3, figsize=S.figsize('double', 228), gridspec_kw=dict(height_ratios=[1, 1.15]))
    axes = axes.ravel()
    for k, g in enumerate(REF_GROUPS):
        ax = axes[k]
        cases = list(dict.fromkeys(t[t['group'] == g]['case']))
        for j, c in enumerate(cases):
            d = an[an['case'] == c].set_index('year')['carbon_kt']
            check(math.isclose(d.sum(), float(t[t['case'] == c]['carbon_kt'].iloc[0]), rel_tol=1e-9),
                  f'ED3: the path of {c} does not add up to its table value')
            ax.plot(d.index, d.values, color=LINE_COLOURS[j % len(LINE_COLOURS)], lw=S.LW_THIN * 1.6,
                    ls=('-', '--', ':', '-.')[(j // len(LINE_COLOURS)) % 4], label=textwrap.fill(c, 46))
            src.add(g, c, d.index, d.values, 'kt CO2e per year')
        ax.plot(ref.index, ref.values, color=S.INK, lw=S.LW_BOLD, label='Reference')
        src.add(g, 'Reference', ref.index, ref.values, 'kt CO2e per year')
        ax.set_xlim(2026, 2050)
        ax.set_ylim(0, None)
        ax.set_ylabel('kt CO₂e per year')
        P.thousands(ax.yaxis)
        P.panel(ax, 'abcde'[k], g)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=S.FONT_MIN, handlelength=2.2,
                  labelspacing=0.25, ncol=1)
    axes[-1].set_axis_off()
    fig.tight_layout(h_pad=0.6)
    save(fig, fid, src)
    return dict(caption=h['caption'] + ' Population rows: the exact engine paths. Every path adds up to its value in '
                'ED1 (checked).')


# ============================================================
# ED5  Monte Carlo
# ============================================================
def ecdf(x):
    x = np.sort(np.asarray(x, float))
    return x, np.arange(1, len(x) + 1) / len(x)


def ed5():
    h = PLAN['ED5']
    fid = h['file']
    src = source(fid)
    mc = read_csv(L.montecarlo('annual', REF, frozen=False), index_col=0)
    ms = read_csv(L.montecarlo('summary', REF, frozen=False), index_col=0)
    an = read_csv('baseline/annual.csv')
    an = an[an['source'] == 'projection'].set_index('year')
    dr = read_csv('pathways/montecarlo_draws.csv')
    mcs = PP.mc_summary()
    r = PP.runs_ref()
    fig, axes = plt.subplots(2, 2, figsize=S.figsize('double', 130))
    yrs = [y for y in mc.index if y >= PP.WINDOW[0]]
    for ax, q, col, unit, letter, ylab in ((axes[0, 0], 'floor_area', 'floor_area_Mm2', 'Mm2 per year', 'a',
                                            'Floor area (Mm² per year)'),
                                           (axes[0, 1], 'carbon', 'carbon_kt', 'kt CO2e per year', 'b',
                                            'Embodied carbon (kt CO₂e per year)')):
        f = (lambda s: s / PP.M6)
        ax.fill_between(yrs, f(mc.loc[yrs, f'{q}_5']), f(mc.loc[yrs, f'{q}_95']), color=S.REFERENCE, alpha=0.14, lw=0,
                        label='Monte Carlo 5–95%')
        ax.fill_between(yrs, f(mc.loc[yrs, f'{q}_25']), f(mc.loc[yrs, f'{q}_75']), color=S.REFERENCE, alpha=0.28, lw=0,
                        label='Monte Carlo 25–75%')
        ax.plot(yrs, f(mc.loc[yrs, f'{q}_50']), color=S.REFERENCE, lw=S.LW, ls='--', label='Monte Carlo median')
        ax.plot(yrs, an.loc[yrs, col], color=S.INK, lw=S.LW_BOLD, label='Reference (deterministic)')
        for p_ in ('5', '25', '50', '75', '95'):
            src.add(letter, f'Monte Carlo {p_}%', yrs, f(mc.loc[yrs, f'{q}_{p_}']).values, unit)
        src.add(letter, 'Reference', yrs, an.loc[yrs, col].values, unit)
        ax.set_xlim(yrs[0], yrs[-1])
        ax.set_ylim(0, None)
        ax.set_ylabel(ylab)
        if q == 'carbon':
            P.thousands(ax.yaxis)
        ax.legend(loc='upper right', fontsize=S.FONT_MIN)
        P.panel_label(ax, letter)
    runs = (('REF', REF, 'Reference'), ('P5', 'P5-moderate', 'P5 Combined'), ('TL', 'TL', 'TL Theoretical limit'))
    for ax, q, letter, xlab in ((axes[1, 0], 'carbon_kt', 'c', 'Cumulative embodied carbon 2026–2050 (kt CO₂e)'),
                                (axes[1, 1], 'LoE_AR', 'd', N.METRICS['cumulative_LoE'] + ', AR')):
        for k, run, lab in runs:
            x, yv = ecdf(dr[f'{k}_{q}'])
            ax.plot(x, yv, color=PP.colour(run), lw=S.LW, label=lab)
            ax.axvline(float(r.loc[run, q]), color=PP.colour(run), lw=S.LW_THIN, ls=':')
            src.add(letter, f'{lab}, percentiles 5/25/50/75/95', ['p5', 'p25', 'p50', 'p75', 'p95'],
                    [mcs.loc[(k, q), c] for c in ('p5', 'p25', 'p50', 'p75', 'p95')], 'kt CO2e' if q == 'carbon_kt'
                    else 'cumulative LoE AR')
            src.add(letter, f'{lab}, deterministic', 'value', float(r.loc[run, q]),
                    'kt CO2e' if q == 'carbon_kt' else 'cumulative LoE AR')
        ax.set_ylim(0, 1)
        ax.set_ylabel('Share of draws at or below')
        ax.set_xlabel(xlab)
        P.panel_label(ax, letter)
    axes[1, 0].xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    d = axes[1, 1]
    d.axvline(1.0, color=S.AR, lw=S.LW_BOLD)
    p_ar = float(mcs.loc[('TL', 'LoE_AR'), 'probability_LoE_at_most_1'])
    p_atp = float(mcs.loc[('TL', 'LoE_AtP'), 'probability_LoE_at_most_1'])
    d.plot([1.0], [p_ar], marker='o', ms=4, color=S.TL)
    d.annotate(f'TL: P(LoE AR ≤ 1) = {100 * p_ar:.1f}%\n(P(LoE AtP ≤ 1) = {100 * p_atp:.1f}%)', xy=(1.0, p_ar),
               xytext=(1.5, 0.30), fontsize=S.FONT_SMALL, arrowprops=dict(arrowstyle='-', color=S.MUTED, lw=S.LW_THIN))
    src.add('d', 'TL, P(LoE AR <= 1)', 'probability', p_ar, 'share of draws')
    src.add('d', 'TL, P(LoE AtP <= 1)', 'probability', p_atp, 'share of draws')
    d.legend(handles=d.get_legend_handles_labels()[0] + [Line2D([0], [0], color=S.AR, lw=S.LW_BOLD, label='LoE AR = 1'),
                                                         Line2D([0], [0], color=S.MUTED, lw=S.LW_THIN, ls=':',
                                                                label='deterministic run')],
             loc='lower right', fontsize=S.FONT_MIN)
    fig.tight_layout()
    save(fig, fid, src)
    n = len(dr)
    cap = (h['caption'] + f" (a, b) The Reference: Monte Carlo 5–95% and 25–75% bands, median (dashed) and the "
           f"deterministic Reference; cumulative floor area 2026–2050 {ms.loc['floor_area_Mm2', 'p5']:.1f}–"
           f"{ms.loc['floor_area_Mm2', 'p95']:.1f} Mm², carbon {ms.loc['carbon_kt', 'p5']:,.0f}–{ms.loc['carbon_kt', 'p95']:,.0f} "
           f"kt (5–95%). (c, d) Cumulative distributions over the {n:,} draws of the Reference, P5 and TL (each draw "
           'run through the pathway layer with the levers applied identically and the TL targets at their absolute '
           'values; the AR and AtP budgets of each draw follow its population path and its case-study factors). '
           f"TL: P(LoE AR ≤ 1) = {100 * p_ar:.1f}%, P(LoE AtP ≤ 1) = {100 * p_atp:.1f}%. The central draw reproduces the "
           'deterministic runs (asserted to 1e-9).')
    return dict(caption=cap)


# ============================================================
# ED6  Ambitious settings
# ============================================================
def setting_dots(ax, r, rows, value, src, panel, unit, fmt):
    for i, (pw, lab) in enumerate(rows):
        m_, a_ = float(r.loc[f'{pw}-moderate', value]), float(r.loc[f'{pw}-ambitious', value])
        col = S.PATHWAY.get(pw) or S.PATHWAY[N_P(pw)]
        ax.plot([m_, a_], [i, i], color=col, lw=S.LW)
        ax.plot(m_, i, marker='o', mfc='white', mec=col, mew=S.LW, ms=5, lw=0)
        ax.plot(a_, i, marker='o', mfc=col, mec=col, ms=5, lw=0)
        ax.text(min(m_, a_), i - 0.16, f'{fmt(a_)} | {fmt(m_)}', ha='left', va='bottom', fontsize=S.FONT_MIN)
        src.add(panel, f'{lab}, Moderate', 'value', m_, unit)
        src.add(panel, f'{lab}, Ambitious', 'value', a_, unit)
    ax.axvline(float(r.loc[REF, value]), color=S.REFERENCE, lw=S.LW_BOLD)
    src.add(panel, 'Reference', 'value', float(r.loc[REF, value]), unit)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([lab for _, lab in rows])
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.grid(axis='y', visible=False)


def N_P(lever):
    """The pathway of a lever (its colour)."""
    return [p for p, ls in N.PATHWAY_LEVERS.items() if lever in ls][0] if lever in sum(N.PATHWAY_LEVERS.values(), ()) \
        else 'P5'


def setting_legend(fig):
    fig.legend(handles=[Line2D([0], [0], marker='o', mfc='white', mec=S.INK, lw=0, ms=5, label='Moderate (open)'),
                        Line2D([0], [0], marker='o', mfc=S.INK, mec=S.INK, lw=0, ms=5, label='Ambitious (filled)'),
                        Line2D([0], [0], color=S.REFERENCE, lw=S.LW_BOLD, label='Reference')],
               loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.005), frameon=False)


def ed6():
    h = PLAN['ED6']
    fid = h['file']
    src = source(fid)
    r = PP.runs_ref()
    rows = [(p, f'{p} {N.PATHWAYS[p]}') for p in PP.PATHWAY_IDS]
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 72), sharey=True)
    setting_dots(a, r, rows, 'carbon_kt', src, 'a', 'kt CO2e 2026-2050', lambda v: f'{v:,.0f}')
    setting_dots(b, r, rows, 'LoE_AR', src, 'b', 'cumulative LoE AR', lambda v: f'{v:.2f}')
    a.set_xlabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(a.xaxis)
    b.set_xlabel(N.METRICS['cumulative_LoE'] + ', AR')
    k = PP.budget_ratio(r)
    sec = b.secondary_xaxis('top', functions=(lambda v: v * k, lambda v: v / k))
    sec.set_xlabel('Cumulative level of exceedance, AtP')
    P.panel_label(a, 'a')
    P.panel_label(b, 'b')
    setting_legend(fig)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, fid, src)
    cap = (h['caption'] + f" P5 Combined: {r.loc['P5-moderate', 'carbon_kt']:,.0f} kt (Moderate) and "
           f"{r.loc['P5-ambitious', 'carbon_kt']:,.0f} kt (Ambitious), LoE AR {r.loc['P5-moderate', 'LoE_AR']:.2f} and "
           f"{r.loc['P5-ambitious', 'LoE_AR']:.2f}. Labels: Ambitious | Moderate. Both settings with full roll-out by "
           '2035; the settings of every lever: Table 1.')
    return dict(caption=cap)


# ============================================================
# ED7  Roll-out timing
# ============================================================
def ed7():
    import levers as LV
    h = PLAN['ED7']
    fid = h['file']
    src = source(fid)
    r = PP.runs_ref()
    an = read_csv('pathways/annual.csv')
    an = an[an['scenario'] == REF]
    windows = (('by2030', '-by2030'), ('by2035', ''), ('by2045', '-by2045'))
    ls = {'by2030': ':', 'by2035': '-', 'by2045': '-.'}
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 78), gridspec_kw=dict(width_ratios=[1.6, 1]))
    d0 = an[an['run'] == REF]
    a.plot(d0['year'], d0['carbon_kt'], color=S.REFERENCE, lw=S.LW_BOLD, label='Reference')
    src.add('a', 'Reference', d0['year'], d0['carbon_kt'], 'kt CO2e per year')
    for setting in ('moderate', 'ambitious'):
        for w, suf in windows:
            run = f'P5-{setting}{suf}'
            d = an[an['run'] == run]
            a.plot(d['year'], d['carbon_kt'], color=S.PATHWAY['P5'], ls=ls[w],
                    lw=S.LW if setting == 'moderate' else S.LW_THIN * 1.6, alpha=1.0 if setting == 'moderate' else 0.6,
                    label=f"P5, {N.SETTINGS[setting]}, {N.ADOPTION[w]}")
            src.add('a', N.run_label(run), d['year'], d['carbon_kt'], 'kt CO2e per year')
    a.set_xlim(2026, 2050)
    a.set_ylim(0, None)
    a.set_ylabel('Embodied carbon (kt CO₂e per year)')
    P.thousands(a.yaxis)
    a.legend(loc='upper right', fontsize=S.FONT_MIN)
    P.panel_label(a, 'a')
    ins = a.inset_axes([0.60, 0.07, 0.37, 0.21])
    yy = np.arange(2026, 2051)
    for w, _ in windows:
        wv = LV.ramp_named(yy, w)
        ins.plot(yy, wv, color=S.INK, ls=ls[w], lw=S.LW_THIN * 1.6)
        src.add('a (inset)', f'adoption path w(y), {N.ADOPTION[w]}', yy, wv, 'share of full strength')
    ins.set_xlim(2026, 2050)
    ins.set_ylim(0, 1.05)
    ins.set_title('adoption path w(y)', fontsize=S.FONT_MIN, fontweight='normal', pad=2)
    ins.tick_params(labelsize=S.FONT_MIN)
    for i, (w, suf) in enumerate(windows):
        for setting, mfc in (('moderate', 'white'), ('ambitious', S.PATHWAY['P5'])):
            v = float(r.loc[f'P5-{setting}{suf}', 'LoE_AR'])
            b.plot(v, i, marker='o', mfc=mfc, mec=S.PATHWAY['P5'], mew=S.LW, ms=5, lw=0)
            b.text(v, i - 0.18, f'{v:.2f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
            src.add('b', f"P5, {N.SETTINGS[setting]}, {N.ADOPTION[w]}", 'value', v, 'cumulative LoE AR')
    b.axvline(float(r.loc[REF, 'LoE_AR']), color=S.REFERENCE, lw=S.LW_BOLD)
    b.set_yticks(range(3))
    b.set_yticklabels([N.ADOPTION[w] for w, _ in windows])
    b.set_ylim(2.6, -0.6)
    b.set_xlabel(N.METRICS['cumulative_LoE'] + ', AR')
    b.grid(axis='y', visible=False)
    P.panel_label(b, 'b')
    setting_legend(fig)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, fid, src)
    cap = (h['caption'] + ' One rule for every adoption window 2026 → E: a normalised logistic path, 10–90% of adoption '
           f"within the middle two-thirds of the window (inset). Cumulative LoE AR of P5 (Moderate): "
           f"{r.loc['P5-moderate-by2030', 'LoE_AR']:.2f} (by 2030), {r.loc['P5-moderate', 'LoE_AR']:.2f} (by 2035) and "
           f"{r.loc['P5-moderate-by2045', 'LoE_AR']:.2f} (by 2045).")
    return dict(caption=cap)


# ============================================================
# ED8  TL: attribution and indicators
# ============================================================
def ed8():
    import pathways as PW
    h = PLAN['ED8']
    fid = h['file']
    src = source(fid)
    st = read_csv('pathways/shapley_theoretical_limit_moderate.csv')
    tl = read_json('pathways/theoretical_limit.json')
    an = read_csv('pathways/annual.csv')
    an = an[an['scenario'] == REF]
    ind = tl['indicators']['TL']
    fig, axes = plt.subplots(2, 2, figsize=S.figsize('double', 128))
    a = axes[0, 0]
    players = [f'TL{k}' for k in range(1, 8)] + ['from2027']
    lab = {p: (f'{p} {N.TL[p]}' if p != 'from2027' else N.ADOPTION['from2027'].capitalize()) for p in players}
    car = st[st['metric'] == 'carbon_kt'].set_index('player')['reduction']
    loe = st[st['metric'] == 'LoE_AR'].set_index('player')['reduction']
    share = st[st['metric'] == 'carbon_kt'].set_index('player')['share_of_P5_moderate_from2027_minus_TL']
    for i, p in enumerate(players):
        a.barh(i, loe[p], color='#7A7A7A' if p != 'from2027' else S.TL_GRADUAL, height=0.66, edgecolor='white')
        txt = f"{loe[p]:.2f} ({car[p]:,.0f} kt" + (f', {100 * share[p]:.0f}%)' if p != 'from2027' else ')')
        a.text(loe[p], i, ' ' + txt, va='center', fontsize=S.FONT_MIN)
        src.add('a', lab[p], 'LoE AR', loe[p], 'cumulative LoE AR')
        src.add('a', lab[p], 'carbon', car[p], 'kt CO2e 2026-2050')
    a.set_yticks(range(len(players)))
    a.set_yticklabels([textwrap.fill(lab[p], 30) for p in players], fontsize=S.FONT_MIN, linespacing=1.0)
    a.set_ylim(len(players) - 0.4, -0.6)
    a.set_xlim(0, loe.max() * 1.55)
    a.set_xlabel('Reduction of the cumulative LoE AR')
    a.grid(axis='y', visible=False)
    P.panel(a, 'a', 'Shapley values relative to P5 at full strength from 2027')
    yrs = np.arange(2026, 2051)
    ref = an[an['run'] == REF].set_index('year')
    tla = an[an['run'] == 'TL'].set_index('year')
    b = axes[0, 1]
    size_tl = [ind['mean_new_dwelling_size_m2_by_year'][str(y)] for y in yrs]
    b.plot(yrs, ref.loc[yrs, 'dwelling_size_m2'], color=S.REFERENCE, lw=S.LW_BOLD, label='Reference')
    b.plot(yrs, size_tl, color=S.TL, lw=S.LW, label='TL')
    src.add('b', 'Reference: new-dwelling size', yrs, ref.loc[yrs, 'dwelling_size_m2'].values, 'm2 per dwelling')
    src.add('b', 'TL: new-dwelling size', yrs, size_tl, 'm2 per dwelling')
    m2p = [ind['m2_per_person_new_dwellings'][str(y)] for y in yrs]
    b.plot(yrs, m2p, color=S.TL, lw=S.LW, ls='--', label='TL: floor area per person in new dwellings')
    src.add('b', 'TL: floor area per person in new dwellings', yrs, m2p, 'm2 per person')
    b.set_xlim(2026, 2050)
    b.set_ylim(0, None)
    b.set_ylabel('m² per dwelling; m² per person')
    b.legend(loc='center right', fontsize=S.FONT_MIN)
    P.panel(b, 'b', 'New-dwelling size and space per person')
    c = axes[1, 0]
    dw_tl = [ind['dwellings_built_in_scope'][str(y)] for y in yrs]
    check(np.allclose(dw_tl, tla.loc[yrs, 'dwellings_built'].values, rtol=1e-9, atol=1e-6),
          'ED8: TL dwellings built differ between the indicators and annual.csv')
    c.bar(yrs, ref.loc[yrs, 'dwellings_built'] / 1e3, width=0.8, color=S.REFERENCE, alpha=0.35, label='Reference')
    c.bar(yrs, np.asarray(dw_tl) / 1e3, width=0.5, color=S.TL, label='TL (banking rule)')
    src.add('c', 'Reference: dwellings built', yrs, ref.loc[yrs, 'dwellings_built'].values, 'dwellings per year')
    src.add('c', 'TL: dwellings built', yrs, dw_tl, 'dwellings per year')
    c.set_xlim(2025.4, 2050.6)
    c.set_ylabel('Dwellings built (thousand per year)')
    c.legend(loc='upper right', fontsize=S.FONT_MIN)
    c.grid(axis='x', visible=False)
    P.panel(c, 'c', 'Dwellings built (in scope)')
    d = axes[1, 1]
    for run, col, lw in ((REF, S.REFERENCE, S.LW_BOLD), ('TL', S.TL, S.LW)):
        x = an[an['run'] == run].set_index('year').loc[yrs]
        with np.errstate(invalid='ignore', divide='ignore'):
            # nothing built (below the model's zero tolerance, pathways.T_ZERO_TOL_M2): the ratio is not defined
            v = np.where(x['floor_area_Mm2'] * PP.M6 > PW.T_ZERO_TOL_M2, x['soil_carbon_loss_kt'] / x['floor_area_Mm2'],
                         np.nan)
        d.plot(yrs, v, color=col, lw=lw, label=PP.label(run), marker='o' if run == 'TL' else None, ms=2)
        src.add('d', f'{PP.label(run)}: soil carbon loss per m2 built', yrs, v, 'kg CO2e per m2 (NaN: nothing built)')
    d.set_xlim(2026, 2050)
    d.set_ylim(0, None)
    d.set_ylabel('Soil carbon loss per m² built (kg CO₂e/m²)')
    d.legend(loc='center right', fontsize=S.FONT_MIN)
    P.panel(d, 'd', 'Soil carbon loss per m² built (TL5, TL6)')
    fig.tight_layout()
    save(fig, fid, src)
    z = ind['zero_building_years']
    cap = (h['caption'] + ' (a) Shapley values (exact, 128 subsets) of TL1–TL7 relative to P5 Combined (Moderate) at full '
           'strength from 2027, in cumulative LoE AR (carbon and share of that run − TL in brackets); they add up exactly '
           'to that difference. The effect of full strength from 2027 (P5 on the adoption path → from 2027) is a separate '
           'line, not a Shapley player. The earlier attribution of TL1–TL6 relative to P5 Ambitious stays in '
           'data/pathways/shapley_theoretical_limit.csv. (b) New-dwelling size and floor area per person (TL3: '
           f"{ind['m2_per_person_new_dwellings']['2030']:.2f} m² per person). (c) Dwellings built: TL builds nothing in "
           f"{min(z)}–{max(z)} (banking rule: the vacant stock released by TL1 absorbs the requirement). (d) Soil carbon "
           'loss per m² of floor area built (soil carbon loss / floor area, annual data; not defined in years with no '
           'building).')
    return dict(caption=cap)


# ============================================================
# ED9  Single levers
# ============================================================
def ed9():
    h = PLAN['ED9']
    fid = h['file']
    src = source(fid)
    r = PP.runs_ref()
    sl = read_csv('pathways/shapley_levers.csv')
    sl = sl[(sl['setting'] == 'moderate') & (sl['metric'] == 'carbon_kt')].set_index('player')
    rows = [(f'L{k}', f"L{k} {N.LEVERS[f'L{k}']}") for k in range(1, 6)]
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 72))
    setting_dots(a, r, rows, 'carbon_kt', src, 'a', 'kt CO2e 2026-2050', lambda v: f'{v:,.0f}')
    a.set_xlabel('Embodied carbon 2026–2050, one lever alone (kt CO₂e)')
    P.thousands(a.xaxis)
    P.panel_label(a, 'a')
    tot = float(r.loc[REF, 'carbon_kt'] - r.loc['P5-moderate', 'carbon_kt'])
    check(math.isclose(sl['reduction'].sum(), tot, rel_tol=1e-12), 'ED9: the lever Shapley values do not add up')
    for i, (lv, lab) in enumerate(rows):
        v = float(sl.loc[lv, 'reduction'])
        b.barh(i, v, color=S.PATHWAY[N_P(lv)], height=0.62, edgecolor='white')
        b.text(v, i, f" {v:,.0f} kt ({100 * sl.loc[lv, 'share_of_reference_minus_P5']:.0f}%)", va='center',
               fontsize=S.FONT_MIN)
        src.add('b', lab, 'Shapley value', v, 'kt CO2e 2026-2050')
    b.set_yticks(range(len(rows)))
    b.set_yticklabels([lab for _, lab in rows])
    b.set_ylim(len(rows) - 0.4, -0.6)
    b.set_xlim(0, sl['reduction'].max() * 1.45)
    b.set_xlabel(f'Shapley value of Reference − P5 (Moderate; total {tot:,.0f} kt CO₂e)')
    P.thousands(b.xaxis)
    b.grid(axis='y', visible=False)
    P.panel_label(b, 'b')
    setting_legend(fig)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, fid, src)
    cap = (h['caption'] + ' (a) Each lever alone on the Reference, Moderate (open) and Ambitious (filled), full roll-out '
           'by 2035; the cumulative LoE AR of every run: data/pathways/runs.csv. (b) Order-free (Shapley) attribution of '
           'Reference − P5 Combined (Moderate) to the five levers (exact; adds up to the difference).')
    return dict(caption=cap)


# ============================================================
# ED10  Low and High replacement
# ============================================================
def ed10():
    h = PLAN['ED10']
    fid = h['file']
    src = source(fid)
    t = read_csv('sensitivity/replacement_variants.csv')
    scen = ('LOW', 'REF', 'HIGH')
    runs = (('Reference', 'Reference'), ('P5-moderate', 'P5 Combined'), ('TL', 'TL Theoretical limit'))
    fig, (a, b) = plt.subplots(1, 2, figsize=S.figsize('double', 74))
    w = 0.26
    for ax, col, unit, letter, fmt in ((a, 'carbon_kt', 'kt CO2e 2026-2050', 'a', lambda v: f'{v:,.0f}'),
                                       (b, 'LoE_AR', 'cumulative LoE AR', 'b', lambda v: f'{v:.2f}')):
        for i, (run, lab) in enumerate(runs):
            for j, sc in enumerate(scen):
                v = float(t[(t['scenario'] == sc) & (t['run'] == run)][col].iloc[0])
                st = S.SCENARIO[sc]
                ax.bar(i + (j - 1) * w, v, width=w * 0.92, color=PP.colour('TL' if run == 'TL' else
                                                                          (REF if run == 'Reference' else run)),
                       alpha={'LOW': 0.45, 'REF': 1.0, 'HIGH': 0.75}[sc],
                       hatch={'LOW': None, 'REF': None, 'HIGH': '///'}[sc], edgecolor='white', lw=S.LW_THIN)
                ax.text(i + (j - 1) * w, v, fmt(v), ha='center', va='bottom', fontsize=S.FONT_MIN, rotation=90)
                src.add(letter, f'{lab}, {st["label"]}', sc, v, unit)
        ax.set_xticks(range(len(runs)))
        ax.set_xticklabels([lab for _, lab in runs])
        ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
        ax.grid(axis='x', visible=False)
        P.panel_label(ax, letter)
    a.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(a.yaxis)
    b.set_ylabel(N.METRICS['cumulative_LoE'] + ', AR')
    b.axhline(1.0, color=S.AR, lw=S.LW)
    fig.legend(handles=[Patch(facecolor=S.MUTED, alpha=0.45, label=N.SCENARIOS['LOW'] + ' (left)'),
                        Patch(facecolor=S.MUTED, label=N.SCENARIOS['REF'] + ' replacement (middle)'),
                        Patch(facecolor=S.MUTED, alpha=0.75, hatch='///', edgecolor='white',
                              label=N.SCENARIOS['HIGH'] + ' (right)'),
                        Line2D([0], [0], color=S.AR, lw=S.LW, label='LoE AR = 1')],
               loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.005), frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, fid, src)
    tlr = t[t['run'] == 'TL'].set_index('scenario')
    cap = (h['caption'] + ' Low replacement: the 1991–2023 long-run net replacement rate throughout; High: the 2018–2023 '
           'census-interval rate persists. Every run is computed with the pathway engine; all but TL under Low and High '
           'replacement reproduce data/pathways/runs.csv to 1e-12, and TL under Low and High is new (TL7 then cuts that '
           f"variant's replacement rates by 40%). TL: LoE AR {tlr.loc['LOW', 'LoE_AR']:.2f} (Low), "
           f"{tlr.loc['REF', 'LoE_AR']:.2f} (Reference) and {tlr.loc['HIGH', 'LoE_AR']:.2f} (High).")
    return dict(caption=cap)


# ============================================================
# EXTENDED_DATA.md
# ============================================================
def md_path():
    return L.writing(os.path.join(L.EXTENDED_DATA, 'EXTENDED_DATA.md'))


def write_md(rr):
    lines = ['# Extended Data', '',
             '_Generated by extended_data.py from outputs/data/ (do not edit by hand). Figures: 183 mm wide, PNG 300 dpi '
             'and vector PDF; the source data of every figure in the CSV of the same name. The figures of the paper: '
             '../paper/PAPER.md; rows and groups of the sensitivity figures: docs/SENSITIVITY_PLAN.md._', '']
    if PP.quick_run():
        lines += ['> **QUICK RUN, not for reporting** (run_all.py --quick: fewer Monte Carlo draws).', '']
    for h in FP.EXTENDED_DATA:
        f = h['file']
        lines += [f"## {h['id']}. {N.typeset(h['title'])}", '', f'![{h["id"]}]({f}.png)', '',
                  f"**{h['id']}.** {N.typeset(rr[h['id']]['caption'])}", '',
                  f"Files: [{f}.png]({f}.png), [{f}.pdf]({f}.pdf), source data [{f}.csv]({f}.csv). "
                  f"Data (outputs/): {h['source']}.", '']
    with open(md_path(), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


FIGURES = dict(ED1=ed1, ED2=ed2, ED3=ed3, ED4=ed4, ED5=ed5, ED6=ed6, ED7=ed7, ED8=ed8, ED9=ed9, ED10=ed10)


def main(only=None):
    rr = {}
    for k, fn in FIGURES.items():
        if only and k not in only:
            continue
        rr[k] = fn()
        print(f'extended_data: {k} {PLAN[k]["file"]}')
    if not only:
        write_md(rr)
        print(f'extended_data: {os.path.relpath(md_path(), ROOT)}')
    return rr


if __name__ == '__main__':
    main([a for a in sys.argv[1:] if a.startswith('ED')] or None)
