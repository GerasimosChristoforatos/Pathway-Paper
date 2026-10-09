"""
PLOTTING: drawing helpers shared by every figure (MODEL v1.0.0)
==============================================================
style.py holds the colours, sizes and saving, naming.py the labels; this module draws
with them, so the headline figures (headline.py) and the diagnostics (projection.py,
Diagnostics.py, tools/figures_report.py, Sensitivity.py, MonteCarlo.py, boundaries.py,
pathways.py) stack bands, materials and boundaries the same way.

Rules kept here (docs/FIGURE_PLAN.md):
  * demand bands are stacked and sum to the total: no separate total line is drawn;
  * negative parts are drawn below zero, never clipped (zero_floor raises if a series
    that must be non-negative is not);
  * the two allocation principles (AR, AtP) are lines, never a shaded range and never
    averaged; they are tagged as boundaries for the figure audit (figaudit.py).
"""
import numpy as np
import matplotlib
from matplotlib.patches import Patch

import naming as N
import style as S

HISTORY_SPLIT = 2025.5             # vertical divider between history (to 2025) and projection (2026 on)


# ---------------------------------------------------------------------------
# panels and axes
# ---------------------------------------------------------------------------
def panel_label(ax, letter, x=-0.02, y=1.02):
    """Bold panel letter at the top left, outside the axes."""
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=S.FONT_SIZE + 1, fontweight='bold', va='bottom',
            ha='right')


def panel(ax, letter, title=None):
    """Panel letter and, for the diagnostics, a short panel title next to it."""
    panel_label(ax, letter)
    if title:
        ax.set_title(title, loc='left', fontsize=S.FONT_SIZE, fontweight='normal', pad=4)


def split(ax, x=HISTORY_SPLIT):
    """History | projection divider (not data: axvline is ignored by the figure audit)."""
    ax.axvline(x, color=S.MUTED, lw=S.LW_THIN, ls=':')


def fmt_kt(v):
    return f'{v:,.0f}'


def thousands(axis):
    axis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))


def log_ticks(axis, ticks):
    """Plain-number ticks on a log axis (1, 2, 5, 10 ... rather than 10^0, 10^1)."""
    lo, hi = axis.get_view_interval()
    axis.set_major_locator(matplotlib.ticker.FixedLocator([t for t in ticks if lo <= t <= hi]))
    axis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,g}'))
    axis.set_minor_locator(matplotlib.ticker.NullLocator())


def note(fig, text, y=0.0):
    """A short italic note under the figure (the full caption is in DIAGNOSTICS.md / HEADLINE.md)."""
    fig.text(0.5, y, text, ha='center', va='top', fontsize=S.FONT_SMALL, style='italic', color=S.MUTED, wrap=True)


# ---------------------------------------------------------------------------
# boundaries
# ---------------------------------------------------------------------------
def boundary_lines(ax, x, ar, atp, label=True, **kw):
    """The two allocation principles as lines (never shaded as a range, never averaged)."""
    import figaudit
    for key, y in (('AR', ar), ('AtP', atp)):
        if y is None:
            continue
        st = dict(S.BOUNDARY[key])
        lab = st.pop('label')
        st.update(kw)
        ax.plot(x, y, gid=figaudit.BOUNDARY, label=lab if label else None, **st)


def boundary_hline(ax, key, value, label=None, **kw):
    """A cumulative budget (one value) as a horizontal boundary line."""
    import figaudit
    st = dict(S.BOUNDARY[key])
    lab = st.pop('label')
    st.update(kw)
    ax.axhline(value, gid=figaudit.BOUNDARY, label=lab if label is None else label, **st)


# ---------------------------------------------------------------------------
# demand bands
# ---------------------------------------------------------------------------
def band_label(bid):
    return (N.BANDS.get(bid) or N.BAND_DETAIL[bid]) + (' (untargeted)' if bid in N.UNTARGETED else '')


def band_style(bid):
    colour, hatch = S.BAND[bid if bid in S.BAND else 'replacement']
    return dict(facecolor=colour, hatch=hatch, edgecolor='white', linewidth=S.LW_THIN)


def signed_stack(ax, x, parts, width, **kw):
    """Bars: stack positive parts upwards and negative parts downwards from zero.
    parts: [(band id, values)]. Returns the tops (up, down)."""
    x = np.atleast_1d(np.asarray(x, float))
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for bid, v in parts:
        v = np.atleast_1d(np.asarray(v, float))
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        st = dict(band_style(bid), **kw)
        ax.bar(x, pos, bottom=up, width=width, **st)
        ax.bar(x, neg, bottom=dn, width=width, **st)
        up, dn = up + pos, dn + neg
    return up, dn


def signed_areas(ax, x, parts, **kw):
    """Areas: the same signed stack as signed_stack, as filled areas over a year axis.
    parts: [(band id, values)]. No total line: the stack is the total. Returns (up, down)."""
    x = np.asarray(x, float)
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for bid, v in parts:
        v = np.asarray(v, float)
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        st = dict(band_style(bid), lw=0, **kw)
        st.pop('linewidth')
        if np.any(pos > 0):
            ax.fill_between(x, up, up + pos, **st)
        if np.any(neg < 0):
            ax.fill_between(x, dn + neg, dn, **st)
        up, dn = up + pos, dn + neg
    if np.any(dn < 0):
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    else:
        for c in ax.collections:
            c.sticky_edges.y.append(0.0)
    return up, dn


def band_handles(bids):
    return [Patch(label=band_label(b), **dict(band_style(b), edgecolor='#555555')) for b in bids]


def band_legend(fig, bids, loc='lower center', ncol=4, y=-0.02, extra=()):
    fig.legend(handles=band_handles(bids) + list(extra), loc=loc, ncol=ncol, bbox_to_anchor=(0.5, y),
               frameon=False, handlelength=1.4, columnspacing=1.2)


# ---------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------
def zero_floor(ax, *series):
    """Anchor the y axis at 0 for panels of non-negative quantities. Checks that every
    plotted series is >= 0 (raises otherwise: a negative value must be reported, never
    clipped) and adds a sticky edge at 0 to the panel's filled areas, so autoscaling keeps
    its top margin but no margin below zero."""
    lo = min(float(np.nanmin(np.asarray(s, float))) for s in series)
    if lo < 0:
        raise ValueError(f'zero_floor: a plotted series is negative (min {lo:g}); not clipped.')
    for c in ax.collections:
        c.sticky_edges.y.append(0.0)


def material_patch(code, colour, alpha=1.0):
    """Patch style of one material layer (style.MATERIAL): soil faded and hatched."""
    if code == 'SOIL':
        return dict(facecolor=colour, alpha=alpha * S.SOIL['alpha'], hatch=S.SOIL['hatch'],
                    edgecolor=S.SOIL['edgecolor'], linewidth=S.LW_THIN)
    return dict(facecolor=colour, alpha=alpha, **S.EDGE)


def stack_materials(ax, years, frame, scale=1.0, alpha=1.0):
    """Areas of carbon by material in style.MATERIAL order (bottom to top), soil on top.
    Each material includes its maintenance within 2026-2050. Returns legend handles,
    top first."""
    unknown = set(frame.columns) - {c for c, _, _ in S.MATERIAL}
    if unknown:
        raise ValueError(f'No colour for {sorted(unknown)} in style.MATERIAL.')
    years = np.asarray(years)
    bottom, handles = np.zeros(len(years)), []
    for code, lab, colour in S.MATERIAL:                    # SOIL is the last entry: the top layer
        v = np.asarray(frame[code], float) / scale
        handles.append(ax.fill_between(years, bottom, bottom + v, label=lab, **material_patch(code, colour, alpha)))
        bottom = bottom + v
    zero_floor(ax, *[frame[code] for code, _, _ in S.MATERIAL])
    return handles[::-1]


# ---------------------------------------------------------------------------
# history with its census benchmarks
# ---------------------------------------------------------------------------
def history_estimated(ax, series, anchor, scale=1.0, color=S.INK, label='History', lw=S.LW, k=None,
                      census_last=2018):
    """Households / household size history: census-benchmarked to census_last (solid);
    census_last+1..anchor Stats NZ estimates scaled to the anchor census by k (dotted);
    after the anchor consent-derived estimates, not used (faint dashed); the anchor census
    point marked."""
    s = series.dropna() / scale
    last = int(s.index.max())
    ax.plot(s.loc[:census_last].index, s.loc[:census_last].values, color=color, lw=lw,
            label=f'{label}: census-benchmarked to {census_last}')
    mid = s.loc[census_last:anchor]
    ax.plot(mid.index, mid.values, color=color, lw=lw, ls=':',
            label=f'{census_last + 1}–{anchor % 100:02d}: Stats NZ estimates scaled to the {anchor} census'
                  + (f' (×{k:.3f})' if k is not None else ''))
    tail = s.loc[anchor:]
    ax.plot(tail.index, tail.values, color=color, lw=lw * 0.7, ls='--', alpha=0.35,
            label=f'{anchor + 1}–{last % 100:02d}: consent-derived estimates, not used')
    if anchor in s.index:
        ax.plot([anchor], [s.loc[anchor]], 'o', color=color, ms=3, label=f'{anchor} census')
    ax.ticklabel_format(axis='y', style='plain', useOffset=False)
