"""Figure audit: when a figure is saved, record for every axes its labels and the
range of calendar years its data cover, every text of the figure and its note
(outputs/figure_audit/<name>.json). The tests read these records to check that no
figure shows carbon outside the projection, except the AR base window
(tests/test_v3.py), and that no figure uses an old name (tests/test_release.py);
DIAGNOSTICS.md takes the notes from them.

Data covered: lines, filled areas (fill_between, stackplot) and bars (at their
centre). Not data: vertical marker lines (axvline) and artists tagged
gid=BOUNDARY (the AR / AtP boundaries, defined from t0 = 2025, not emissions). An x
value counts as a calendar year when it lies in YEAR_RANGE.
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
AUDIT_DIR = layout.FIGURE_AUDIT


def _years(ax):
    xs = []
    for a in ax.get_children():
        if not a.get_visible() or a.get_gid() == BOUNDARY:
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


def record(fig, name, note=None):
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
        json.dump(dict(figure=os.path.splitext(os.path.basename(name))[0], producer=producer(), axes=axes,
                       texts=texts(fig), note=note), f, indent=1)
