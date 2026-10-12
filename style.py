"""One style for every figure of the model (MODEL v1.0.0; layout of MODEL v2.0.0).

Every plotting module imports this file and nothing else for colours, line styles,
typeface, sizes and saving, so a figure cannot drift from the palette of
docs/PALETTE.md. The palette is checked for colour-vision deficiency by
tools/palette_check.py (CAM02-UCS distances under simulated deuteranomaly,
protanomaly and tritanomaly, colorspacious; Machado et al. 2009), which also writes
docs/PALETTE.md and docs/palette_preview.png.

Rules (docs/PALETTE.md, MODEL v2.1.2):
  * demand bands are coloured by the lever that targets them (four pathway families after Francis Bacon, Head VI);
    the only untargeted band, Population growth, a solid deep green-blue; negative bands drawn down from the top of
    the positive stack (net-total convention, plotting.signed_stack);
  * Reference dark grey, P5 vermilion, TL a deep forest green (a larger circle on point plots);
  * boundaries: acquired rights (AR) a thin red line, ability to pay (AtP) a thin dark-red dotted line, light zones
    below AtP, between AtP and AR and above AR;
  * settings: Moderate solid line / filled marker, Ambitious dashed line / hollow marker;
  * one typeface (Liberation Sans, metric-compatible with Arial; bundled in fonts/ under
    the SIL Open Font License, so figures render identically on every machine);
  * print sizes: Nature Cities single column 89 mm, double column 183 mm; text 5-7 pt.

save() writes PNG (300 dpi) and, for the paper and Extended Data figures, vector PDF, with fixed metadata
(no software version or creation date), so a re-run with the pinned environment
reproduces every figure byte for byte (tests/output_manifest_model_v2.json).
"""
import os

import matplotlib
import numpy as np
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ROOT, 'fonts')
for _f in ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf', 'LiberationSans-Italic.ttf'):
    font_manager.fontManager.addfont(os.path.join(FONT_DIR, _f))
FONT = 'Liberation Sans'

# ---------------------------------------------------------------------------
# Sizes (Nature Cities: 89 mm single column, 183 mm double column; text 5-7 pt)
# ---------------------------------------------------------------------------
MM = 1 / 25.4                                   # inches per mm
WIDTH = {'single': 89 * MM, 'double': 183 * MM}
MAX_HEIGHT = 247 * MM                           # full page depth
FONT_SIZE = 7.0                                 # body text, tick labels
FONT_SMALL = 6.0                                # legends, annotations
FONT_MIN = 5.0                                  # never smaller (Nature: 5 pt minimum)
LW = 1.0                                        # data lines, pt
LW_THIN = 0.5                                   # grid, edges, reference lines
LW_BOLD = 1.5                                   # the Reference / emphasised line
DPI = 300

RC = {
    'font.family': 'sans-serif', 'font.sans-serif': [FONT], 'font.size': FONT_SIZE,
    'axes.titlesize': FONT_SIZE, 'axes.labelsize': FONT_SIZE, 'axes.titleweight': 'bold',
    'axes.linewidth': LW_THIN, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'grid.linewidth': LW_THIN * 0.6, 'grid.color': '#E0E0E0', 'axes.axisbelow': True,
    'xtick.labelsize': FONT_SMALL, 'ytick.labelsize': FONT_SMALL, 'xtick.major.width': LW_THIN,
    'ytick.major.width': LW_THIN, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
    'legend.fontsize': FONT_SMALL, 'legend.frameon': False, 'legend.handlelength': 1.6,
    'lines.linewidth': LW, 'patch.linewidth': LW_THIN, 'hatch.linewidth': LW_THIN,
    'figure.dpi': 100, 'savefig.dpi': DPI, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02,
    'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
    'axes.formatter.use_mathtext': True, 'mathtext.default': 'regular',
}

# ---------------------------------------------------------------------------
# Colours (hex; checked by tools/palette_check.py)
# ---------------------------------------------------------------------------
INK = '#1A1A1A'                                 # text, axes
MUTED = '#6E6E6E'                               # secondary text, leader lines

# boundaries (MODEL v2.1.0 styling, implemented once here: boundary_zones / boundary_hzones): AR a thin red line,
# AtP a thin dark-red line (dashed, so the two principles stay apart under colour-vision deficiency); the area
# below AtP darker green (within both budgets), between AtP and AR light green (within AR only), above AR light
# red at low opacity (boundary exceeded); the same on annual and cumulative axes. The three zones (as seen on
# white) fall strictly in lightness under every simulated deficiency (darker green < light green < palest red;
# CAM02-UCS J' 77 / 90 / 97 at least / at most), so they never depend on hue alone; AR '#D7191C' keeps >= 10 from
# every run colour under every deficiency (tools/palette_check.py; docs/PALETTE.md)
AR = '#D7191C'
ATP = '#67000D'
LW_BOUNDARY = 0.9
# MODEL v2.1.2: AtP dotted; the zones much lighter (on white: within both J' 90, within AR only 95, exceeded 99;
# the lightness order still holds under every simulated deficiency; tools/palette_check.py)
ATP_LS = (0, (1, 1.3))                          # dotted ·····
BOUNDARY = {'AR': dict(color=AR, ls='-', lw=LW_BOUNDARY, label='Acquired rights (AR)'),
            'AtP': dict(color=ATP, ls=ATP_LS, lw=LW_BOUNDARY, label='Ability to pay (AtP)')}
ZONE = {'within_both': dict(color='#41AB5D', alpha=0.30, label='Within both budgets (below AtP)'),
        'within_ar': dict(color='#A1D99B', alpha=0.30, label='Within AR only (between AtP and AR)'),
        'exceeded': dict(color='#FB6A4A', alpha=0.035, label='Boundary exceeded (above AR)')}
ZONE_GID = 'boundary_zone'
# two accent colours for lines that are not boundaries (household formation, floor area in the diagnostics): the
# boundary pair of model-v2.0.0, kept so those diagnostics are unchanged
ACCENT_ORANGE = '#C2571A'
ACCENT_BLUE = '#1F5FA8'

# runs
REFERENCE = '#4D4D4D'
# MODEL v2.1.2: TL a deep forest green, far darker than the zones; at CAM02-UCS J' 25 it is >= 10 from AR, AtP,
# the Reference, P5, every lever, Population growth and the zones under every simulated deficiency (a mid green
# at the lightness of AR merges with it under deuteranomaly / protanomaly)
TL = '#13412B'
TL_MARKER = dict(marker='o', ms=8)             # TL on point plots: a larger circle (no star)
SCENARIO = {'REF': dict(color=REFERENCE, ls='-', lw=LW_BOLD, label='Reference'),
            'LOW': dict(color='#9E9E9E', ls='--', lw=LW, label='Low replacement'),
            'HIGH': dict(color='#6E6E6E', ls=':', lw=LW, label='High replacement')}
MC_BAND = dict(color=REFERENCE, alpha=0.15, lw=0)          # Monte Carlo 5-95% band

# MODEL v2.1.1 palette, inspired by Francis Bacon, Head VI (1949): four pathway families, each lever a shade within
# its family. P1 Space per person golds / ochres (L1 deep ochre, L2 light gold), P2 Existing stock mauves (L4
# 2026 overbuild deep mauve, L3 vacancy rose-lilac, lighter; L5 replacement lighter still), P3 Construction blues
# (L6 dark, L7 light), P4 Land browns (L8 dark brown, L9 light tan); P5 vermilion and TL cyan, outside every family;
# Reference grey. The hue families are fixed; lightness and chroma were chosen by maximising the minimum CAM02-UCS
# distance of every group shown together under every simulated deficiency, with each slot's tone kept (lightness
# bounds: overbuild < vacancy < replacement; browns and the near-black growth keep a visible hue); every group
# >= 10 (tools/palette_check.py; docs/PALETTE.md). Where a group failed, the lightness of one colour moved within
# its hue family (L7 lighter and TL lighter so TL stays apart from L7 under protanomaly; committed lighter than
# maintenance; the unexplained-building face lighter than Historical replacement)
LEVER = {'L1': '#DFA538', 'L2': '#F4D168', 'L3': '#AA7C9D', 'L4': '#683861', 'L5': '#E1D2DD',
         'L6': '#4A6192', 'L7': '#ABD3FA', 'L8': '#8D6545', 'L9': '#C7B395'}
PATHWAY = {'P1': LEVER['L1'], 'P2': LEVER['L4'], 'P3': LEVER['L6'], 'P4': LEVER['L8'], 'P5': '#EB6123'}
# MODEL v2.1.2: Moderate filled marker, Ambitious hollow (the solution-space convention, used everywhere)
SETTING = {'moderate': dict(ls='-', marker_fill='full', label='Moderate'),
           'ambitious': dict(ls='--', marker_fill='none', label='Ambitious')}

# demand bands, bottom to top: (colour, hatch), coloured by the lever that targets them; labels in naming.BANDS.
# Population growth (untargeted) the deep green-blue hue, solid, clearly lighter since MODEL v2.1.2 (J' 47, was 11);
# Historical replacement a darker lilac with a slightly bluer hue (MODEL v2.1.2) than the Recent replacement surge,
# which keeps the L5 face with a fine, light hatch (both replacement bands are targeted by L5)
UNTARGETED_HATCH = None
GROWTH = '#586E71'
REPLACEMENT = '#D0BBDC'
HATCH_LIGHT = '#FFFFFF'                 # the fine hatch of the surge band: drawn in a light colour on its light face
BAND = {'growth': (GROWTH, None),
        'smaller_households': (LEVER['L2'], None),
        'extra_space': (LEVER['L1'], None),
        'vacancy': (LEVER['L3'], None),
        'overbuild_2026': (LEVER['L4'], None),
        'replacement': (REPLACEMENT, None),
        'redevelopment': (LEVER['L5'], '\\\\\\\\'),     # fine hatch, drawn light (BAND_HATCHCOLOR)
        'maintenance': ('#AAAAAA', None)}      # neutral (MODEL v2.1.1)
BAND_ORDER = list(BAND)
BAND_HATCHCOLOR = {'redevelopment': HATCH_LIGHT}

# carbon components (labels in naming.COMPONENTS)
COMPONENT = {'materials_construction': (LEVER['L6'], None),     # A1-A3: P3 dark blue
             'soil': (LEVER['L8'], None),                       # P4 brown
             'maintenance': (BAND['maintenance'][0], None),     # B2, B4 within 2026-2050
             'committed': ('#D0D0D0', '///')}                   # after 2050, a range; lighter than maintenance

# life-cycle stages (Fig3a; labels in naming.STAGES): A1-A3 the L6 shade, A4-A5 the L7 shade, soil the L8
# shade, maintenance its band colour; stacked A1-A3, A4-A5, soil, maintenance (A4-A5 and maintenance not adjacent)
STAGE = {'a1a3': COMPONENT['materials_construction'], 'a4a5': (LEVER['L7'], None), 'soil': COMPONENT['soil'],
         'maintenance': COMPONENT['maintenance']}

# unexplained building of the history (Fig2, D05c, K1): a faded reddish face, no hatch (MODEL v2.1.2; face, hatch,
# hatch colour); may be negative
UNEXPLAINED = ('#C6A3A4', None, None)
# the untargeted band (Fig4): the population-growth grey, hatched
UNTARGETED_GROUP = (BAND['growth'][0], UNTARGETED_HATCH)      # solid since MODEL v2.1.1

# materials: the six Pride-flag stripes (author decision, baseline-pb-v2; one order in every
# figure), soil faded and hatched on top
MATERIAL = [('TIMBER', 'Timber', '#750787'), ('STEEL', 'Steel', '#004DFF'),
            ('CONCRETE (incl. reinforced)', 'Concrete', '#008026'),
            ('PLASTICS & PAINT', 'Plastics & paint', '#FFED00'),
            ('PLASTERBOARD', 'Plasterboard', '#FF8C00'), ('OTHERS', 'Others', '#E40303'),
            ('SOIL', 'Soil carbon loss', '#B5A48B')]
SOIL = dict(alpha=0.5, hatch='///', hatchcolor='#8C7B66')         # the soil layer of a material stack

# stacked bars and areas (MODEL v2.1.1): no white borders between segments. Every segment's edge is its own face
# colour at LW_SEAM (it covers the antialiasing seam between adjacent segments without drawing a line); hatches are
# drawn in an explicit thin hatch colour (matplotlib hatchcolor), never in the edge colour
LW_SEAM = 0.3
HATCH_COLOUR = '#6E6E6E'


def fill(face, hatch=None, hatchcolor=None, alpha=1.0):
    """Patch style of one stacked segment: edge = face at LW_SEAM; a hatch in hatchcolor (default HATCH_COLOUR)."""
    d = dict(facecolor=face, edgecolor=face, linewidth=LW_SEAM, alpha=alpha)
    if hatch:
        d.update(hatch=hatch, hatchcolor=hatchcolor or HATCH_COLOUR)
    return d

# categorical groups in the diagnostics (sensitivity groups, the cases of D17): the Okabe-Ito
# palette (Okabe & Ito 2008, Color Universal Design), distinguishable under the common colour-vision
# deficiencies; one colour per group, always with a label
QUALITATIVE = ['#000000', '#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7']

# sequential ramp for continuous fields (the solution-space LoE, H10): light to dark blue, lightness
# strictly decreasing (tools/palette_check.py), so the order survives greyscale and colour-vision
# deficiency
SEQUENTIAL = ['#EAF2FB', '#C6DBF2', '#9EC5F4', '#6DA7EC', '#3987E5', '#256ABF', '#184F95', '#0D366B']


def apply():
    """Set the rcParams of the release style (call once per process before plotting)."""
    matplotlib.rcParams.update(RC)


def figsize(width='double', height_mm=100.0):
    """(width, height) in inches for a print width ('single' 89 mm or 'double' 183 mm)."""
    return WIDTH[width], height_mm * MM


QUICK_TEXT = 'QUICK RUN, not for reporting (run_all.py --quick: fewer Monte Carlo draws)'


def quick_run():
    return os.environ.get('PATHWAY_QUICK') == '1'


def save(fig, path, pdf=False):
    """Write path + '.png' (DPI, no software / date metadata) and, with pdf, path + '.pdf'
    (vector, fonts embedded as TrueType, no producer / dates), then close the figure.
    Fixed metadata make re-runs byte-identical. In a quick run (PATHWAY_QUICK=1) every figure
    carries a red footer 'QUICK RUN, not for reporting'."""
    import matplotlib.pyplot as plt
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if quick_run():
        fig.text(0.5, 0.0, QUICK_TEXT, ha='center', va='top', color='white', fontsize=FONT_SIZE,
                 fontweight='bold', bbox=dict(facecolor='#C0392B', edgecolor='none', pad=2))
    fig.savefig(path + '.png', dpi=DPI, metadata={'Software': None})
    if pdf:
        fig.savefig(path + '.pdf', metadata={'Creator': None, 'Producer': None, 'CreationDate': None})
    plt.close(fig)


def export_run():
    """True with run_all.py --export (PATHWAY_EXPORT=1): the paper and Extended Data figures are also written as
    vector PDF with their source-data CSV (Nature source data, at acceptance). Default: PNG only."""
    return os.environ.get('PATHWAY_EXPORT') == '1'


def save_figure(fig, name, note=None):
    """Save a planned figure (figure_plan.py file id, e.g. 'D22_boundaries') to its place in
    outputs/ (layout.figure): PNG; with --export also a vector PDF of the paper and Extended Data figures. The
    audit record of the figure (axes, year ranges, every text, the note, maintenance and boundary styling) is
    written first (figaudit.py). note: run-specific caption text for DIAGNOSTICS.md (numbers of this run)."""
    import figaudit
    import layout
    path = layout.figure(name)
    figaudit.record(fig, name, note=note)
    save(fig, path, pdf=layout.vector(path) and export_run())


# ---------------------------------------------------------------------------
# Planetary-boundary styling (every figure with boundaries: paper, Extended Data, diagnostics, key figures)
# ---------------------------------------------------------------------------
_ZONE_TOP = 1e15                   # the 'exceeded' zone extends far above any axis (clipped by the axes)


def _keep_limits(ax, draw):
    """Draw the zones without changing the data limits (autoscaling follows the data, not the zones)."""
    saved = ax.dataLim.frozen()
    ignore = ax.ignore_existing_data_limits
    draw()
    ax.dataLim.set(saved)
    ax.ignore_existing_data_limits = ignore


def boundary_zones(ax, x, ar, atp, lines=True, label=True):
    """Annual (or cumulative-by-year) boundaries: the zones below AtP (darker green), between AtP and AR (light
    green) and above AR (light red, low opacity), and the two thin boundary lines. Zones start just above zero
    (a positive floor, so log axes work) and are tagged ZONE_GID for the figure audit; lines are tagged as
    boundaries (figaudit.BOUNDARY)."""
    import figaudit
    x = np.asarray(x, float)
    ar, atp = np.asarray(ar, float), np.asarray(atp, float)
    floor = 1e-6 * float(np.nanmin(atp))

    def draw():
        for lo, hi, key in ((np.full(len(x), floor), atp, 'within_both'), (atp, ar, 'within_ar'),
                            (ar, np.full(len(x), _ZONE_TOP), 'exceeded')):
            z = dict(ZONE[key])
            z.pop('label')
            ax.fill_between(x, lo, hi, lw=0, zorder=0, gid=ZONE_GID, **z)
    _keep_limits(ax, draw)
    if lines:
        for key, y in (('AR', ar), ('AtP', atp)):
            st = dict(BOUNDARY[key])
            lab = st.pop('label')
            ax.plot(x, y, gid=figaudit.BOUNDARY, label=lab if label else None, zorder=3, **st)


def boundary_hzones(ax, ar, atp, lines=True, label=True, xspan=None):
    """Cumulative budgets on a bar axis (one value each): horizontal zones over the whole axes width (or xspan
    in data units) and the two thin budget lines."""
    import figaudit

    def draw():
        for lo, hi, key in ((1e-6 * atp, atp, 'within_both'), (atp, ar, 'within_ar'), (ar, _ZONE_TOP, 'exceeded')):
            z = dict(ZONE[key])
            z.pop('label')
            if xspan is None:
                ax.axhspan(lo, hi, lw=0, zorder=0, gid=ZONE_GID, **z)
            else:
                ax.fill_between(list(xspan), [lo, lo], [hi, hi], lw=0, zorder=0, gid=ZONE_GID, **z)
    _keep_limits(ax, draw)
    if lines:
        for key, v in (('AR', ar), ('AtP', atp)):
            st = dict(BOUNDARY[key])
            lab = st.pop('label')
            if xspan is None:
                ax.axhline(v, gid=figaudit.BOUNDARY, label=lab if label else None, zorder=3, **st)
            else:
                ax.plot(list(xspan), [v, v], gid=figaudit.BOUNDARY, label=lab if label else None, zorder=3, **st)


def zone_handles():
    """Legend handles of the three boundary zones."""
    from matplotlib.patches import Patch
    return [Patch(facecolor=z['color'], alpha=z['alpha'], edgecolor='none', label=z['label']) for z in ZONE.values()]


def boundary_handles():
    """Legend handles of the two boundary lines."""
    from matplotlib.lines import Line2D
    return [Line2D([0], [0], **{k: v for k, v in BOUNDARY[b].items()}) for b in ('AR', 'AtP')]


def boundary_vzones(ax, ar, atp, lines=True, label=True):
    """Budgets on an x axis (e.g. a cumulative level of exceedance: AR at 1, AtP at its AR equivalent): vertical
    zones and lines."""
    import figaudit

    def draw():
        for lo, hi, key in ((1e-6 * atp, atp, 'within_both'), (atp, ar, 'within_ar'), (ar, _ZONE_TOP, 'exceeded')):
            z = dict(ZONE[key])
            z.pop('label')
            ax.axvspan(lo, hi, lw=0, zorder=0, gid=ZONE_GID, **z)
    _keep_limits(ax, draw)
    if lines:
        for key, v in (('AR', ar), ('AtP', atp)):
            st = dict(BOUNDARY[key])
            lab = st.pop('label')
            ax.axvline(v, gid=figaudit.BOUNDARY, label=lab if label else None, zorder=3, **st)


def boundary_field(ax, X, Y, Z, ar, atp, lines=True):
    """A field of cumulative carbon (Z, in any unit where the budgets are ar and atp, e.g. LoE AR: ar = 1,
    atp = B_AtP / B_AR) on a plane: the three zones as filled regions and the two budgets as contour lines
    (the solution space). Only the levels inside the range of Z are drawn."""
    import figaudit
    zmin, zmax = float(np.nanmin(Z)), float(np.nanmax(Z))
    edges = [min(zmin, atp) - 1.0, atp, ar, max(zmax, ar) + 1.0]
    keys = ('within_both', 'within_ar', 'exceeded')
    for (lo, hi), key in zip(zip(edges[:-1], edges[1:]), keys):
        if hi <= zmin or lo >= zmax:
            continue
        cf = ax.contourf(X, Y, Z, levels=[lo, hi], colors=[ZONE[key]['color']], alpha=ZONE[key]['alpha'],
                         zorder=0)
        cf.set_gid(ZONE_GID)
    out = {}
    if lines:
        for key, v in (('AR', ar), ('AtP', atp)):
            if zmin < v < zmax:
                st = BOUNDARY[key]
                cs = ax.contour(X, Y, Z, levels=[v], colors=[st['color']], linewidths=[st['lw']],
                                linestyles=[st['ls']], zorder=3)
                cs.set_gid(figaudit.BOUNDARY)
                out[key] = cs
    return out


apply()
