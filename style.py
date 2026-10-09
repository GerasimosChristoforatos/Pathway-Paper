"""One style for every figure of the model (MODEL v1.0.0).

Every plotting module imports this file and nothing else for colours, line styles,
typeface, sizes and saving, so a figure cannot drift from the palette of
docs/PALETTE.md. The palette is checked for colour-vision deficiency by
tools/palette_check.py (CAM02-UCS distances under simulated deuteranomaly,
protanomaly and tritanomaly, colorspacious; Machado et al. 2009), which also writes
docs/PALETTE.md and docs/palette_preview.png.

Rules (docs/PALETTE.md):
  * demand bands are coloured by the pathway that targets them (Extra space: P1
    family; Vacancy and 2026 overbuild: P2 family; Replacement and Redevelopment: P3
    family); the untargeted bands (Population growth, Smaller households) are neutral
    greys and hatched; the P4 colour marks intensity / material effects;
  * Reference dark grey, TL near-black, TL gradual adoption light grey;
  * boundaries: acquired rights (AR) blue solid, ability to pay (AtP) orange dashed,
    never shaded as a range;
  * settings: Moderate solid line / open marker, Ambitious dashed line / filled marker;
  * one typeface (Liberation Sans, metric-compatible with Arial; bundled in fonts/ under
    the SIL Open Font License, so figures render identically on every machine);
  * print sizes: Nature Cities single column 89 mm, double column 183 mm; text 5-7 pt.

save() writes PNG (300 dpi) and, for headline figures, vector PDF, with fixed metadata
(no software version or creation date), so a re-run with the pinned environment
reproduces every figure byte for byte (tests/output_manifest_model_v1.json).
"""
import os

import matplotlib
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

# boundaries (validated pair, unchanged from the planetary-boundary layer)
AR = '#1F5FA8'
ATP = '#C2571A'
BOUNDARY = {'AR': dict(color=AR, ls='-', lw=LW_BOLD, label='Acquired rights (AR)'),
            'AtP': dict(color=ATP, ls='--', lw=LW_BOLD, label='Ability to pay (AtP)')}

# runs
REFERENCE = '#4D4D4D'
TL = '#141414'
TL_GRADUAL = '#A6A6A6'
SCENARIO = {'REF': dict(color=REFERENCE, ls='-', lw=LW_BOLD, label='Reference'),
            'LOW': dict(color='#9E9E9E', ls='--', lw=LW, label='Low replacement'),
            'HIGH': dict(color='#6E6E6E', ls=':', lw=LW, label='High replacement')}
MC_BAND = dict(color=REFERENCE, alpha=0.15, lw=0)          # Monte Carlo 5-95% band

# pathways (P1-P4 keep their hue families; P5 sky blue; see docs/PALETTE.md)
PATHWAY = {'P1': '#228833', 'P2': '#F0B400', 'P3': '#E15A97', 'P4': '#762A83', 'P5': '#56B4E9'}
SETTING = {'moderate': dict(ls='-', marker_fill='none', label='Moderate'),
           'ambitious': dict(ls='--', marker_fill='full', label='Ambitious')}

# demand bands, bottom to top: (id, colour, hatch); labels in naming.BANDS
UNTARGETED_HATCH = '....'
BAND = {'growth': ('#CCCCCC', UNTARGETED_HATCH),
        'smaller_households': ('#6E6E6E', UNTARGETED_HATCH),
        'extra_space': (PATHWAY['P1'], None),
        'vacancy': (PATHWAY['P2'], None),
        'overbuild_2026': ('#6B4C00', None),
        'replacement': (PATHWAY['P3'], None),
        'redevelopment': ('#7A1A4B', None),
        'maintenance': ('#C7A3D0', None)}
BAND_ORDER = list(BAND)

# carbon components (labels in naming.COMPONENTS)
COMPONENT = {'materials_construction': ('#762A83', None),       # A1-A5: the P4 colour
             'soil': ('#8C6D46', None),
             'maintenance': ('#C7A3D0', None),                  # B2, B4 within 2026-2050
             'committed': ('#BDBDBD', '///')}                   # after 2050, a range

# materials: the six Pride-flag stripes (author decision, baseline-pb-v2; one order in every
# figure), soil faded and hatched on top
MATERIAL = [('TIMBER', 'Timber', '#750787'), ('STEEL', 'Steel', '#004DFF'),
            ('CONCRETE (incl. reinforced)', 'Concrete', '#008026'),
            ('PLASTICS & PAINT', 'Plastics & paint', '#FFED00'),
            ('PLASTERBOARD', 'Plasterboard', '#FF8C00'), ('OTHERS', 'Others', '#E40303'),
            ('SOIL', 'Soil carbon loss', '#B5A48B')]
EDGE = dict(edgecolor='#555555', linewidth=0.3)


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


def save_figure(fig, name):
    """Save a planned figure (figure_plan.py file id, e.g. 'D22_boundaries') to its place in
    outputs/ (layout.figure): headline figures as PNG and PDF, diagnostics as PNG; the axis
    record of the figure is written first (figaudit.py)."""
    import figaudit
    import layout
    path = layout.figure(name)
    figaudit.record(fig, name)
    save(fig, path, pdf=path.startswith(layout.HEADLINE))


apply()
