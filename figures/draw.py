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

import bands as BANDS_MOD
import naming as N
from figures import style as S

HISTORY_SPLIT = 2025.5             # vertical divider between history (to 2025) and projection (2026 on)
NET_RTOL = 1e-9


# ---------------------------------------------------------------------------
# MODEL v4.3.0: shape-preserving interpolation of annual series (display only; the data are unchanged)
# ---------------------------------------------------------------------------
PCHIP_PER_YEAR = 12                # points per year on the fine grid


def pchip_grid(x, breaks=()):
    """The fine grid: PCHIP_PER_YEAR points per year within each segment, the segment ends shared. breaks: x values
    at which a segment ends and the next starts (no interpolation across them)."""
    x = np.asarray(x, float)
    segs = _segments(x, breaks)
    out = []
    for lo, hi in segs:
        n = int(round((x[hi - 1] - x[lo]) * PCHIP_PER_YEAR)) + 1
        out.append(np.linspace(x[lo], x[hi - 1], max(n, 2)))
    return out


def _segments(x, breaks):
    """[(start, stop)] index ranges; a break b ends one segment at the last x <= b and starts the next there (the
    shared knot keeps the line continuous; the derivative is not carried across)."""
    cuts = [0]
    for b in sorted(breaks):
        k = int(np.searchsorted(x, b, side='right'))
        if 0 < k < len(x):
            cuts.append(k - 1)
    cuts.append(len(x) - 1)
    return [(cuts[i], cuts[i + 1] + 1) for i in range(len(cuts) - 1) if cuts[i + 1] > cuts[i]]


def pchip(x, y, breaks=()):
    """(xf, yf): monotone shape-preserving piecewise cubic Hermite interpolation (scipy PchipInterpolator) through
    every annual value, interpolated separately within each segment (breaks). Two-point segments are linear (PCHIP
    with two knots). The curve passes through every (x, y) and does not overshoot between neighbouring values."""
    from scipy.interpolate import PchipInterpolator
    x, y = np.asarray(x, float), np.asarray(y, float)
    xs, ys = [], []
    for (lo, hi), xf in zip(_segments(x, breaks), pchip_grid(x, breaks)):
        yf = PchipInterpolator(x[lo:hi], y[lo:hi])(xf)
        if xs:                                        # the shared knot once
            xf, yf = xf[1:], yf[1:]
        xs.append(xf)
        ys.append(yf)
    xf, yf = np.concatenate(xs), np.concatenate(ys)
    on = np.isin(xf, x)
    assert np.allclose(yf[on], y[np.searchsorted(x, xf[on])], rtol=1e-12, atol=1e-12)   # through every value
    return xf, yf


def pipeline_breaks():
    """The break between the observed pipeline years (consents already issued; baseline/overbuild_2026.json) and the
    modelled years: annual projection lines are not interpolated across it."""
    from figures import data as D
    return [float(max(D.js('baseline/overbuild_2026.json')['pipeline_years']))]


def pchip_band(x, lo, mid, hi, breaks=(), name='band'):
    """(xf, lo_f, hi_f, method): the band's lower and upper edges interpolated separately; on the fine grid
    lo <= mid <= hi is checked (mid interpolated the same way). If it fails anywhere the band falls back to linear
    interpolation (which keeps the ordering, since it holds at every annual value) and the fallback is logged."""
    xf, lof = pchip(x, lo, breaks)
    _, hif = pchip(x, hi, breaks)
    _, midf = pchip(x, mid, breaks)
    tol = 1e-9 * max(1.0, float(np.nanmax(np.abs(hi))))
    if np.all(lof <= midf + tol) and np.all(midf <= hif + tol):
        return xf, lof, hif, 'pchip'
    print(f'pchip_band: {name}: lower <= central <= upper fails on the fine grid; linear interpolation used')
    return xf, np.interp(xf, x, lo), np.interp(xf, x, hi), 'linear'


# ---------------------------------------------------------------------------
# MODEL v4.3.0: tick labels of horizontal bars (shared by every bar / tornado figure)
# ---------------------------------------------------------------------------
def two_lines(text):
    """A label split at the space nearest its middle (one line if it has no space or is already split)."""
    if '\n' in text:
        return text
    sp = [i for i, ch in enumerate(text) if ch == ' ']
    if not sp:
        return text
    i = min(sp, key=lambda k: abs(k - len(text) / 2))
    return text[:i] + '\n' + text[i + 1:]


def centre_ticklabels(fig, ax):
    """y tick labels centred (every line) on one vertical axis at the centre of the widest label, keeping the
    existing gap between the widest label and the axis: ha = 'center' and the tick pad raised by half the widest
    label's width (points). Call after the labels and fonts are final and before the layout is fixed."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    labels = [t for t in ax.get_yticklabels() if t.get_text()]
    if not labels:
        return
    w = max(t.get_window_extent(r).width for t in labels) * 72.0 / fig.dpi
    pad = ax.yaxis.get_major_ticks()[0].get_pad()
    ax.tick_params(axis='y', pad=pad + w / 2)
    for t in ax.get_yticklabels():
        t.set_horizontalalignment('center')
        t.set_multialignment('center')


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
DISPLAY_STYLE_OF = {'net_replacement': 'replacement', 'market_balance': 'overbuild_2026'}


def display_frame(t):
    """MODEL v4.2: a year x detailed-band frame summed into the six display bands (bands.DISPLAY), in display order."""
    g = t.T.groupby(lambda b: BANDS_MOD.DISPLAY[b]).sum().T
    return g[[d for d in BANDS_MOD.DISPLAY_ORDER if d in g.columns]]


def band_label(bid):
    if bid in ('net_replacement', 'market_balance'):              # MODEL v4.2 display bands
        return BANDS_MOD.DISPLAY_LABEL[bid]
    if bid in ('unexplained_building', 'unexplained'):
        return N.BAND_DETAIL['unexplained']
    return (N.BANDS.get(bid) or N.BAND_DETAIL[bid]) + (' (untargeted)' if bid in N.UNTARGETED else '')


def band_style(bid):
    """Seamless style of one demand band (style.fill: edge = face, hatch in its own colour). History-only ids
    (MODEL v3.1.0, style.HISTORY_BAND): 'replacement_census', 'retirement_villages', 'unexplained'."""
    if bid in ('unexplained_building', 'unexplained'):
        return S.fill(S.UNEXPLAINED[0])
    if bid in DISPLAY_STYLE_OF:                                   # MODEL v4.2 display bands: an existing band colour
        bid = DISPLAY_STYLE_OF[bid]
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


def stack_bars(ax, x, parts, width, net=None):
    """MODEL v4.2.1: bars by band, positive values stacked up from zero and negative values stacked down from zero
    (fixed order), each segment filled in its band style; net: the totals to check against (1e-9). Returns (up, down)."""
    x = np.atleast_1d(np.asarray(x, float))
    up, dn = np.zeros(len(x)), np.zeros(len(x))
    for bid, v in parts:
        v = np.broadcast_to(np.asarray(v, float), x.shape)
        pos, neg = np.clip(v, 0, None), np.clip(v, None, 0)
        if np.any(pos > 0):
            ax.bar(x, pos, bottom=up, width=width, gid='band_segment', **band_style(bid))
        if np.any(neg < 0):
            ax.bar(x, neg, bottom=dn, width=width, gid=NEG_GID, **band_style(bid))
        up, dn = up + pos, dn + neg
    _check_net(up, dn, net, 'stack_bars')
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
    present = [(c, l_, col) for c, l_, col in S.MATERIAL if c in frame.columns]   # only the materials present
    for code, lab, colour in present:                      # SOIL the top layer
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


# ---------------------------------------------------------------------------
# MODEL v4.3.0: paired tornado grouped by category (ED4, ED5; the Fig7a colour rule)
# ---------------------------------------------------------------------------
TORNADO_LOW, TORNADO_HIGH, TORNADO_SINGLE = S.LEVER['L8'], S.PATHWAY['pathway'], S.MUTED   # as Fig7a
NO_EFFECT_RTOL = 1e-4             # |change| below 0.01% of the central value: marked 'no effect'


def tornado_rows(groups, rows, central):
    """Display order: groups in the given order, rows sorted by their span within a group (largest first).
    rows: [dict(id, group, low=None, high=None, single=None, ticks={})]. Returns [(kind, item)] top to bottom,
    kind 'header' (item = group name) or 'row'."""
    out = []
    span = lambda r: max(abs(v - central) for v in (r.get('low'), r.get('high'), r.get('single')) if v is not None)
    for g in groups:
        rs = sorted([r for r in rows if r['group'] == g], key=span, reverse=True)
        if rs:
            out.append(('header', g))
            out += [('row', r) for r in rs]
    return out


def tornado(ax, order, central, label, height=0.62, header_fs=None, headers=True):
    """Draw a paired tornado on ax from tornado_rows() output: one row per input, its low end (blue) and high end
    (orange) on the same row, a single alternative case grey, intermediate cases as ticks with their name; a row
    whose every case is within NO_EFFECT_RTOL of the central value is marked 'no effect'; bold group headers with a
    separator line above each group. y tick labels: label(row id). Returns the row y positions."""
    n = len(order)
    ys, labels = [], []
    for k, (kind, item) in enumerate(order):
        y = n - 1 - k
        if kind == 'header':
            if headers:                               # a panel sharing the rows of another shows none
                ax.text(0.005, y, item, transform=ax.get_yaxis_transform(), ha='left', va='center', zorder=6,
                        fontsize=header_fs or S.FONT_SMALL, fontweight='bold', color=S.INK,
                        bbox=dict(facecolor='white', edgecolor='none', pad=0.6))
            if k:
                ax.axhline(y + 0.5, color=S.MUTED, lw=S.LW_THIN * 0.7)
            continue
        r = item
        vals = [v for v in (r.get('low'), r.get('high'), r.get('single')) if v is not None]
        if all(abs(v - central) <= NO_EFFECT_RTOL * abs(central) for v in vals):
            ax.text(central, y, '  no effect', ha='left', va='center', fontsize=S.FONT_MIN, color=S.MUTED,
                    style='italic')
        else:
            if r.get('single') is not None:
                ax.barh(y, r['single'] - central, left=central, height=height, **S.fill(TORNADO_SINGLE))
            for key, col in (('low', TORNADO_LOW), ('high', TORNADO_HIGH)):
                if r.get(key) is not None:
                    ax.barh(y, r[key] - central, left=central, height=height, **S.fill(col))
            for name, v in r.get('ticks', {}).items():
                ax.plot([v, v], [y - height / 2, y + height / 2], color=S.INK, lw=S.LW_THIN)
                ax.text(v, y + height / 2 + 0.02, name, ha='center', va='bottom', fontsize=S.FONT_MIN, color=S.INK)
        ys.append(y)
        labels.append(label(r['id']))
    ax.axvline(central, color=S.INK, lw=S.LW_THIN)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.set_ylim(-0.7, n - 0.3)
    ax.grid(axis='y', visible=False)
    return ys


def tornado_legend(single=True):
    """The Fig7a legend handles: input at its low end, at its high end, single alternative case."""
    h = [Patch(label='Input at low end', **S.fill(TORNADO_LOW)), Patch(label='Input at high end', **S.fill(TORNADO_HIGH))]
    if single:
        h.append(Patch(label='Single alternative case', **S.fill(TORNADO_SINGLE)))
    return h
