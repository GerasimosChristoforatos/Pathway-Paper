"""Figure audit: when a figure is saved, record for every axes its labels and the
range of calendar years its data cover, every text of the figure and its note
(outputs/diagnostics/_audit/<name>.json). The tests read these records to check that no
figure shows carbon outside the projection, except the AR base window
(tests/test_v3.py), and that no figure uses an old name (tests/test_release.py);
DIAGNOSTICS.md takes the notes from them.

Data covered: lines, filled areas (fill_between, stackplot) and bars (at their
centre). Not data: vertical marker lines (axvline) and artists tagged
gid=BOUNDARY (the AR / AtP boundaries, defined from t0 = 2025, not emissions). An x
value counts as a calendar year when it lies in YEAR_RANGE.

Boundaries (MODEL v2.1.0): every record says whether the figure draws a planetary boundary (an artist tagged
BOUNDARY) and the boundary zones of style.py (tagged ZONE); tests/test_release.py requires the zones wherever a
boundary is drawn.

Maintenance (MODEL v2.0.0): every record says whether the figure draws maintenance (B2, B4) as
its own layer or line ('maintenance_drawn'): a data artist (bar, filled area, line) on a data axes
in the maintenance colour of style.py, or a legend entry naming maintenance. The schematic (axes
switched off) carries no data. tests/test_release.py allows it only in the figures of
figure_plan.MAINTENANCE_ALLOWED.
"""
import json
import os

import layout

import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

YEAR_RANGE = (1900, 2200)
BOUNDARY = 'boundary'
BOUNDARY_OUTSIDE = 'boundary_outside'      # MODEL v3.1.0: a budget level outside the plotted range, stated
ZONE = 'boundary_zone'             # style.ZONE_GID: the boundary zones (MODEL v2.1.0 styling)
AUDIT_DIR = layout.FIGURE_AUDIT


def _years(ax):
    """Year range of the x data of an axes, or (None, None) when the x-axis is not calendar years: x values in
    YEAR_RANGE count as years unless the x-axis label names another quantity (year axes carry no label or a label
    with 'year'; e.g. D37 plots the number of Monte Carlo draws, 100-5,000)."""
    xl = ax.get_xlabel().strip().lower()
    if xl and 'year' not in xl:
        return (None, None)
    xs = []
    for a in ax.get_children():
        if not a.get_visible() or a.get_gid() in (BOUNDARY, ZONE):
            continue
        if isinstance(a, Line2D):
            x = np.asarray(a.get_xdata(), float).ravel()
            if x.size and np.ptp(x) > 0:                     # not a vertical marker line
                xs.append(x)
        elif isinstance(a, PolyCollection):
            xs += [p.vertices[:, 0] for p in a.get_paths()]
        elif isinstance(a, Rectangle) and a is not ax.patch and a.get_height() != 0:
            xs.append(np.array([a.get_x() + a.get_width() / 2], float))
    x = np.concatenate(xs) if xs else np.array([])
    x = x[np.isfinite(x) & (x >= YEAR_RANGE[0]) & (x <= YEAR_RANGE[1])]
    return (float(x.min()), float(x.max())) if x.size else (None, None)


def _hex(c):
    from matplotlib.colors import to_hex
    try:
        a = np.asarray(c, float)
        if a.ndim == 2:
            return {to_hex(x[:3]).upper() for x in a if x[3] > 0}
        return {to_hex(a[:3]).upper()} if a.size >= 3 and (a.size == 3 or a[3] > 0) else set()
    except (TypeError, ValueError):
        return {to_hex(c).upper()} if c not in (None, 'none') else set()


def maintenance_drawn(fig):
    """[where] maintenance is drawn as its own layer or line: data artists in the maintenance colour
    (style.BAND / style.COMPONENT) on axes that are switched on, and legend entries naming it."""
    from figures import style
    colour = {style.BAND['maintenance'][0].upper(), style.COMPONENT['maintenance'][0].upper()}
    out = []
    for k, ax in enumerate(fig.get_axes()):
        if not ax.axison:
            continue
        for a in ax.get_children():
            if not a.get_visible() or a is ax.patch:
                continue
            if isinstance(a, Rectangle):
                c = _hex(a.get_facecolor())
            elif isinstance(a, PolyCollection):
                c = _hex(a.get_facecolor())
            elif isinstance(a, Line2D):
                c = _hex(a.get_color())
            else:
                continue
            if c & colour:
                out.append(f'axes {k}: {type(a).__name__} in the maintenance colour')
                break
    legends = [ax.get_legend() for ax in fig.get_axes() if ax.get_legend()] + list(fig.legends)
    for lg in legends:
        for t in lg.get_texts():
            if 'maintenance' in t.get_text().lower():
                out.append(f'legend: {t.get_text()}')
    return out


def texts(fig):
    """Every visible text of a figure: titles, labels, tick labels, legend entries, annotations
    (tests/test_release.py checks them against the old names of docs/RENAMING.md)."""
    from matplotlib.text import Text
    fig.canvas.draw_idle()
    out = []
    for t in fig.findobj(Text):
        s = t.get_text()
        if t.get_visible() and s.strip():
            out.append(s)
    return sorted(set(out))


def producer():
    """The script that draws the figure (the process's main script, relative to the repository)."""
    import sys
    main = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0].endswith('.py') else None
    return os.path.relpath(main, layout.ROOT).replace(os.sep, '/') if main else None


def white_edges(fig):
    """Filled segments (bars, stacked areas) drawn with a white edge on a non-white face: a white border between
    stacked segments (MODEL v2.1.1: none allowed; style.fill draws the edge in the face colour)."""
    from matplotlib.colors import to_rgba_array
    n = 0
    for ax in fig.get_axes():
        for a in list(ax.patches) + list(ax.collections):
            if a.get_gid() == ZONE or not hasattr(a, 'get_edgecolor') or not hasattr(a, 'get_facecolor'):
                continue
            lw = np.atleast_1d(a.get_linewidth())
            ec, fc = to_rgba_array(a.get_edgecolor()), to_rgba_array(a.get_facecolor())
            if not len(ec) or not len(fc) or float(np.max(lw)) <= 0:
                continue
            white_e = (ec[:, :3] > 0.98).all(axis=1) & (ec[:, 3] > 0)
            white_f = (fc[:, :3] > 0.98).all(axis=1)
            if white_e.any() and not white_f.all():
                n += 1
    return n


def _dash_kind(line):
    """'solid', 'dotted' (every on-segment at most 1.5 x the line width) or 'dashed', from the line's dash pattern."""
    ls = line.get_linestyle()
    if ls in ('-', 'solid', 'None', ' ', ''):
        return 'solid'
    _, seq = getattr(line, '_unscaled_dash_pattern', (0, None))
    if not seq:
        return 'dotted' if ls in (':', 'dotted') else 'dashed'
    return 'dotted' if max(seq[0::2]) <= 1.5 else 'dashed'


def styling(fig):
    """MODEL v2.1.2 styling facts: the line style of every AtP boundary line (dotted required), the negative band
    segments and net-total ticks (net-total convention: plotting.signed_stack / signed_areas), negative-height
    band rectangles (the old convention, drawn down from zero; none allowed) and whether the TL colour is used."""
    from figures import style as S
    from matplotlib.colors import to_hex
    atp, neg, ticks, down, tl, old = [], 0, 0, 0, False, set()
    tlhex = S.TL.upper()
    retired = {'#0DB2C7', '#00ACC1', '#102A2E'}       # TL and Population growth of model-v2.1.1
    from matplotlib.collections import Collection
    from matplotlib.patches import Patch
    for ax in fig.get_axes():
        for a in ax.get_children():
            g = a.get_gid()
            if g == BOUNDARY and isinstance(a, Line2D) and to_hex(a.get_color()).upper() == S.ATP.upper():
                atp.append(_dash_kind(a))
            if g == 'negative_band':
                neg += 1
            elif g == 'net_total':
                ticks += 1
            elif g == 'band_segment' and isinstance(a, Rectangle) and a.get_height() < 0:
                down += 1
            if not isinstance(a, (Line2D, Collection, Patch)):
                continue
            for attr in ('get_color', 'get_facecolor', 'get_markerfacecolor', 'get_edgecolor'):
                try:
                    cols = _hex(getattr(a, attr)())
                except (AttributeError, TypeError, ValueError):
                    continue
                tl = tl or tlhex in cols
                old |= cols & retired
    return dict(atp_linestyles=sorted(set(atp)), negative_band_segments=neg, net_total_ticks=ticks,
                band_rectangles_below_zero=down, tl_colour_used=tl, retired_colours=sorted(old))


def negatives(fig):
    """MODEL v3.0.0 sign rules: the negative band segments of cumulative bars (gid NEG_BAR) must be unfilled and
    unhatched; returns (count, count filled or hatched) and the net-total ticks / lines drawn."""
    n, bad = 0, 0
    for ax in fig.get_axes():
        for a in ax.get_children():
            if a.get_gid() == 'negative_bar':
                n += 1
                fc = np.atleast_2d(np.asarray(a.get_facecolor(), float))
                if (fc[:, 3] > 0).any() or (hasattr(a, 'get_hatch') and a.get_hatch()):
                    bad += 1
    return dict(negative_bar_segments=n, negative_bar_segments_filled=bad)


def record(fig, name, note=None, source=None):
    """Write the audit record of a figure about to be saved under name (no extension): per
    axes its title, labels and the year range of its data; the figure's texts; the note
    (run-specific caption text, used by DIAGNOSTICS.md)."""
    os.makedirs(AUDIT_DIR, exist_ok=True)
    axes = []
    for ax in fig.get_axes():
        y0, y1 = _years(ax)
        axes.append(dict(title=ax.get_title(loc='left') or ax.get_title(), xlabel=ax.get_xlabel(),
                         ylabel=ax.get_ylabel(), year_min=y0, year_max=y1))
    with open(os.path.join(AUDIT_DIR, os.path.splitext(os.path.basename(name))[0] + '.json'), 'w') as f:
        md = maintenance_drawn(fig)
        gids = {a.get_gid() for ax in fig.get_axes() for a in ax.get_children()}
        json.dump(dict(figure=os.path.splitext(os.path.basename(name))[0], producer=producer(), axes=axes,
                       texts=texts(fig), note=note, maintenance_drawn=bool(md), maintenance_where=md,
                       boundary_drawn=BOUNDARY in gids, boundary_outside=BOUNDARY_OUTSIDE in gids,
                       boundary_zones=ZONE in gids,
                       white_segment_edges=white_edges(fig), source=source, **styling(fig), **negatives(fig)),
                  f, indent=1)
