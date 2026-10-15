"""
DRAW: drawing helpers shared by every figure (MODEL v3.0.0, figures/ package)
=============================================================================
figures/style.py holds the colours, sizes and saving, naming.py the labels; this module draws with them, so every
figure stacks bands, materials and boundaries the same way. The figures read data files only (outputs/data/).

Sign rules (MODEL v3.0.0; the data keep the sign of every band, the figures never flip it):
  * time series (stack_series): positive bands stacked up from zero, negative bands stacked down from zero, in the
    fixed band order; the net is a black line (up - |down| = net, checked to 1e-9);
  * cumulative bars (bars_cumulative): positive bands stacked; each negative band (Overbuild absorbed, Released
    dwellings (TL), Unconsented additions, and any band negative in a run) an unfilled, unhatched segment outlined in
    its band colour, hanging down from the top of the positive stack; the bar ends at the net total, marked by a net
    tick (checked to 1e-9); one legend entry per band;
  * material and stage values are never negative (nonnegative() raises: STOP);
  * the two allocation principles (AR, AtP) are lines, never a shaded range and never averaged; tagged as
    boundaries for the figure audit (figures/audit.py).
"""
import numpy as np
import matplotlib
from matplotlib.patches import Patch

import naming as N
from figures import style as S

HISTORY_SPLIT = 2025.5             # vertical divider between history (to 2025) and projection (2026 on)
NET_RTOL = 1e-9


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
    """A short italic note under the figure (the full caption is in DIAGNOSTICS.md / PAPER.md / EXTENDED_DATA.md)."""
    fig.text(0.5, y, text, ha='center', va='top', fontsize=S.FONT_SMALL, style='italic', color=S.MUTED, wrap=True)


# ---------------------------------------------------------------------------
# boundaries
# ---------------------------------------------------------------------------
def boundary_lines(ax, x, ar, atp, label=True, **kw):
    """The two allocation principles as thin lines (never averaged) with the boundary zones of style.py
    (below AtP darker green, between AtP and AR light green, above AR light red: style.boundary_zones)."""
    if ar is not None and atp is not None:
        S.boundary_zones(ax, x, ar, atp, lines=False)
    from figures import audit as figaudit
    for key, y in (('AR', ar), ('AtP', atp)):
        if y is None:
            continue
        st = dict(S.BOUNDARY[key])
        lab = st.pop('label')
        st.update(kw)
        ax.plot(x, y, gid=figaudit.BOUNDARY, label=lab if label else None, zorder=3, **st)


# ---------------------------------------------------------------------------
# demand bands
# ---------------------------------------------------------------------------
def band_label(bid):
    if bid in ('unexplained_building', 'unexplained'):
        return N.BAND_DETAIL['unexplained']
    return (N.BANDS.get(bid) or N.BAND_DETAIL[bid]) + (' (untargeted)' if bid in N.UNTARGETED else '')


def band_style(bid):
    """Seamless style of one demand band (style.fill: edge = face, hatch in its own colour). History-only ids
    (MODEL v3.1.0, style.HISTORY_BAND): 'replacement_census', 'retirement_villages', 'unexplained'."""
    if bid in ('unexplained_building', 'unexplained'):
        return S.fill(S.UNEXPLAINED[0])
    if bid not in S.BAND and bid in S.HISTORY_BAND:
        return S.fill(*S.HISTORY_BAND[bid])
    key = bid if bid in S.BAND else 'replacement'
    colour, hatch = S.BAND[key]
    return S.fill(colour, hatch, S.BAND_HATCHCOLOR.get(key))


def band_id(label):
    """The band id of a band label of the data files (naming.band_data_label)."""
    ids = {N.band_data_label(b): b for b in list(N.BANDS) + list(N.BAND_DETAIL)}
    return ids[label]


def steps(edges, values):
    """Step coordinates of interval values: x = [e0, e1, e1, e2, ...], y duplicated, for fill_between / plot."""
    x, y = [], []
    for (a, b), v in zip(zip(edges[:-1], edges[1:]), values):
        x += [a, b]
        y += [v, v]
    return np.asarray(x, float), np.asarray(y, float)


NEG_GID = 'negative_band'           # a negative band area of a time series (figure audit)
NEG_BAR_GID = 'negative_bar'        # a negative band segment of a cumulative bar: unfilled, outlined (figure audit)
NET_GID = 'net_total'               # the net tick of a bar / the net line of a time series (figure audit)


class SignError(SystemExit):
    pass


def nonnegative(name, *series):
    """STOP if a material or stage series is negative (MODEL v3.0.0: never drawn, never clipped)."""
    lo = min(float(np.nanmin(np.asarray(v, float))) for v in series)
    if lo < -1e-9:
        raise SignError(f'STOP: negative {name} value ({lo:g}); material and stage values are never negative.')


def _check_net(up, dn, net, what):
    if net is None:
        return
    net = np.asarray(net, float)
    tot = up + dn
    scale = np.maximum(np.abs(net), np.maximum(np.abs(up), 1.0))
    err = float(np.max(np.abs(tot - net) / scale))
    if err > NET_RTOL:
        raise SignError(f'STOP: {what}: the drawn stack does not end at the net total (max rel. diff {err:.2e}).')


def stack_series(ax, x, parts, net=None, net_line=True, net_label='Net total', **kw):
    """Time series by band: positive values stacked up from zero, negative values stacked down from zero (fixed
    order), the net a black line. parts: [(band id, values)]; net: the run's total to check against (1e-9).
    Returns (up, down) with down <= 0."""
    x = np.asarray(x, float)
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for bid, v in parts:
        v = np.asarray(v, float)
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        if np.any(pos > 0):
            ax.fill_between(x, up, up + pos, gid='band_area', **dict(band_style(bid), **kw))
        if np.any(neg < 0):
            ax.fill_between(x, dn + neg, dn, gid=NEG_GID, **dict(band_style(bid), **kw))
        up, dn = up + pos, dn + neg
    _check_net(up, dn, net, 'stack_series')
    if net_line and np.any(dn < 0):
        ax.plot(x, up + dn, color=S.INK, lw=S.LW, gid=NET_GID, label=net_label, zorder=6)
    if np.any(dn < 0):
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    else:
        for c in ax.collections:
            c.sticky_edges.y.append(0.0)
    return up, dn


def negative_bar_style(bid):
    colour = (S.BAND[bid][0] if bid in S.BAND else S.HISTORY_BAND[bid][0] if bid in S.HISTORY_BAND
              else S.BAND['replacement'][0])
    return dict(facecolor='none', edgecolor=colour, linewidth=S.LW_OUTLINE, hatch=None)


def bars_cumulative(ax, x, parts, width, net=None, tick=True, styles=None):
    """Cumulative bars by band: positive values stacked from zero; each negative value an unfilled, unhatched
    segment outlined in its band colour, hanging down from the top of the positive stack (in the fixed band
    order), so the bar ends at the net total, marked by a short tick. parts: [(band id, values)]; styles: optional
    {band id: patch style} for the positive segments. Returns (up, down, end)."""
    x = np.atleast_1d(np.asarray(x, float))
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for bid, v in parts:
        pos = np.clip(np.broadcast_to(np.asarray(v, float), x.shape), 0, None)
        st = (styles or {}).get(bid, band_style(bid))
        if np.any(pos > 0):
            ax.bar(x, pos, bottom=up, width=width, gid='band_segment', **st)
        up = up + pos
    top = up.copy()
    for bid, v in parts:
        neg = np.clip(np.broadcast_to(np.asarray(v, float), x.shape), None, 0)
        if np.any(neg < 0):
            ax.bar(x, -neg, bottom=top + neg, width=width, gid=NEG_BAR_GID, **negative_bar_style(bid))
        top, dn = top + neg, dn + neg
    _check_net(up, dn, net, 'bars_cumulative')
    if tick:
        for xi, t, d in zip(x, top, dn):
            if d < 0:
                ax.plot([xi - 0.36 * width, xi + 0.36 * width], [t, t], color=S.INK, lw=S.LW_BOLD,
                        solid_capstyle='butt', zorder=5, gid=NET_GID)
    if np.any(top < 0):
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    return up, dn, top


def band_handles(bids, negative=None, outline=True):
    """One legend entry per band; in bar figures (outline True) a negative band (style.NEGATIVE_BANDS, or the ids in
    `negative`) as an outline; in time-series figures (outline False) every band filled."""
    neg = (set(S.NEGATIVE_BANDS) | set(negative or ())) if outline else set()
    out = []
    for b in bids:
        if b in neg:
            out.append(Patch(label=band_label(b), **negative_bar_style(b)))
        else:
            out.append(Patch(label=band_label(b), **dict(band_style(b), edgecolor='#555555', linewidth=S.LW_THIN)))
    return out


def band_legend(fig, bids, loc='lower center', ncol=4, y=-0.02, extra=(), negative=None, outline=True):
    fig.legend(handles=band_handles(bids, negative, outline) + list(extra), loc=loc, ncol=ncol, bbox_to_anchor=(0.5, y),
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
        return S.fill(colour, S.SOIL['hatch'], S.SOIL['hatchcolor'], alpha * S.SOIL['alpha'])
    return S.fill(colour, alpha=alpha)


def stack_materials(ax, years, frame, scale=1.0, alpha=1.0):
    """Areas of carbon by material in style.MATERIAL order (bottom to top), soil on top.
    Each material includes its maintenance within 2026-2050. Returns legend handles,
    top first."""
    unknown = set(frame.columns) - {c for c, _, _ in S.MATERIAL}
    if unknown:
        raise ValueError(f'No colour for {sorted(unknown)} in style.MATERIAL.')
    years = np.asarray(years)
    bottom, handles = np.zeros(len(years)), []
    present = [(c, l_, col) for c, l_, col in S.MATERIAL if c in frame.columns]   # the legacy only where it exists
    for code, lab, colour in present:                      # legacy (if any) the base, SOIL the top layer
        v = np.asarray(frame[code], float) / scale
        handles.append(ax.fill_between(years, bottom, bottom + v, label=lab, **material_patch(code, colour, alpha)))
        bottom = bottom + v
    zero_floor(ax, *[frame[code] for code, _, _ in present])
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
