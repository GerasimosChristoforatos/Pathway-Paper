"""One style for every figure of the model (MODEL v3.0.0: moved into the figures/ package).

Every module of figures/ imports this file and nothing else for colours, line styles,
typeface, sizes and saving, so a figure cannot drift from the palette of
docs/PALETTE.md. The palette is checked for colour-vision deficiency by
tools/palette_check.py (CAM02-UCS distances under simulated deuteranomaly,
protanomaly and tritanomaly, colorspacious; Machado et al. 2009), which also writes
docs/PALETTE.md and docs/palette_preview.png.

Rules (docs/PALETTE.md, MODEL v2.1.2):
  * demand bands are coloured by the lever that targets them (hue families after Francis Bacon, Head VI);
    the only untargeted band, Population growth, a solid deep green-blue; negative bands drawn down from the top of
    the positive stack (net-total convention; MODEL v3.0.0: figures/draw.py, see below);
  * Reference dark grey, the Moderate / Ambitious Pathway vermilion, TL a deep forest green (a larger circle on point plots);
  * boundaries: acquired rights (AR) a thin red line, ability to pay (AtP) a thin dark-red dotted line, light zones
    below AtP, between AtP and AR and above AR;
  * settings: Moderate solid line / filled marker, Ambitious dashed line / hollow marker;
  * one typeface (Liberation Sans, metric-compatible with Arial; bundled in fonts/ under
    the SIL Open Font License, so figures render identically on every machine);
  * print sizes: Nature Cities single column 89 mm, double column 183 mm; text 5-7 pt.

MODEL v3.0.0: save() writes the formats of the run profile (runprofile.py: light PNG at 200 dpi with a small grey
footer "LIGHT RUN — n=1000"; full PNG at 600 dpi; PDF retired in MODEL v3.3.1) with fixed metadata (no software version or creation
date), so a re-run with the pinned environment reproduces every figure byte for byte. Negative bands keep their
sign in the data: in time series they are stacked down from zero (positives up from zero, the net a black line);
in cumulative bars each negative band is an unfilled, unhatched segment outlined in its band colour hanging from the
top of the positive stack, so the bar ends at the net total (figures/draw.py). Only the surge band is hatched.
registry() lists every colour of every group; tests/test_figures_v3.py requires no duplicate (colour, hatch) within a
group.
"""
import os
import re
import tomllib

import matplotlib
import numpy as np
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, 'fonts')
for _f in ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf', 'LiberationSans-Italic.ttf'):
    font_manager.fontManager.addfont(os.path.join(FONT_DIR, _f))
# MODEL v4.2.2: Arial where installed; otherwise the bundled metric-compatible Liberation Sans
FONT = 'Arial' if any(f.name == 'Arial' for f in font_manager.fontManager.ttflist) else 'Liberation Sans'

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
import runprofile  # noqa: E402

DPI = int(os.environ.get('PATHWAY_DPI') or runprofile.get('dpi'))   # light 200, full 600; MODEL v4.3.1: redraw.py --dpi

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
# MODEL v4.3.1: the user palette (palette.toml at the repository root; another file through the environment variable
# PATHWAY_PALETTE, as redraw.py --palette sets it). This module is the only reader, and every figure takes these
# colours from the constants below. Each key colours one meaning only: nothing else is derived from it (the
# typologies, variants, sub-bands and neutrals are fixed literals). MODEL v4.3.2: nine groups; the planetary
# boundaries, their zones (alpha fixed here), the Fig3b cumulative column and the one-at-a-time (tornado) colours
# moved from fixed literals into the file; the lever shades L1-L9 retired.
# ---------------------------------------------------------------------------
PALETTE_KEYS = {
    'demand_bands': ('population_growth', 'household_size_change', 'extra_space', 'vacancy', 'net_replacement',
                     'market_balance', 'maintenance'),
    'materials': ('timber', 'steel', 'concrete', 'plastics_paint', 'plasterboard', 'others', 'soil_carbon_loss'),
    'life_cycle_stages': ('a1_a3', 'a4_a5', 'soil_carbon_loss', 'maintenance', 'committed_b2_b4', 'committed_c1_c4'),
    'runs': ('reference', 'moderate', 'ambitious', 'theoretical_limit'),
    'strategies': ('avoid', 'switch', 'improve'),
    'boundaries': ('acquired_rights', 'ability_to_pay'),
    'boundary_zones': ('within_both', 'within_ar_only', 'exceeded'),
    'cumulative': ('fig3b_cumulative_carbon',),
    'one_at_a_time': ('low_end', 'high_end', 'single_alternative')}
PALETTE_DEFAULT = os.path.join(ROOT, 'palette.toml')
_HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')


class PaletteError(ValueError):
    pass


def load_palette(path):
    """{group: {key: '#RRGGBB'}} from a palette file. Every group and key of PALETTE_KEYS must be present, with a
    six-digit hex value; unknown groups or keys are an error too (a misspelt key would otherwise be ignored)."""
    with open(path, 'rb') as f:
        raw = tomllib.load(f)
    errors = [f'unknown group [{g}]' for g in raw if g not in PALETTE_KEYS]
    out = {}
    for g, keys in PALETTE_KEYS.items():
        sec = raw.get(g)
        if not isinstance(sec, dict):
            errors.append(f'missing group [{g}]')
            continue
        errors += [f'[{g}] unknown key {k!r}' for k in sec if k not in keys]
        for k in keys:
            v = sec.get(k)
            if v is None:
                errors.append(f'[{g}] missing key {k!r}')
            elif not isinstance(v, str) or not _HEX.match(v):
                errors.append(f'[{g}] {k} = {v!r} is not a "#RRGGBB" hex colour')
        out[g] = {k: sec[k].upper() for k in keys if isinstance(sec.get(k), str) and _HEX.match(sec[k])}
    if errors:
        raise PaletteError(f'{path}: ' + '; '.join(errors))
    return out


PALETTE_PATH = os.environ.get('PATHWAY_PALETTE') or PALETTE_DEFAULT
PALETTE = load_palette(PALETTE_PATH)
_DB, _MAT, _ST, _RUN, _SG, _BD, _ZN, _CUM, _OAT = (PALETTE[g] for g in PALETTE_KEYS)

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
# MODEL v4.3.2: the colours from palette.toml [boundaries] and [boundary_zones]; line styles, widths and the zone
# opacities (ZONE_ALPHA) stay fixed here. redraw.py and tools/palette_check.py warn when the zones, composited on white
# at these opacities, lose the lightness order within both < within AR only < exceeded (CAM02-UCS J').
AR = _BD['acquired_rights']
ATP = _BD['ability_to_pay']
LW_BOUNDARY = 0.9
# MODEL v2.1.2: AtP dotted; the zones much lighter (on white: within both J' 90, within AR only 95, exceeded 99;
# the lightness order still holds under every simulated deficiency; tools/palette_check.py)
ATP_LS = (0, (1, 1.3))                          # dotted ·····
BOUNDARY = {'AR': dict(color=AR, ls='-', lw=LW_BOUNDARY, label='Acquired rights (AR)'),
            'AtP': dict(color=ATP, ls=ATP_LS, lw=LW_BOUNDARY, label='Ability to pay (AtP)')}
ZONE_ALPHA = {'within_both': 0.30, 'within_ar': 0.30, 'exceeded': 0.07}      # fixed (not in palette.toml)
ZONE = {'within_both': dict(color=_ZN['within_both'], alpha=ZONE_ALPHA['within_both'],
                            label='Within both budgets (below AtP)'),
        'within_ar': dict(color=_ZN['within_ar_only'], alpha=ZONE_ALPHA['within_ar'],
                          label='Within AR only (between AtP and AR)'),
        'exceeded': dict(color=_ZN['exceeded'], alpha=ZONE_ALPHA['exceeded'], label='Boundary exceeded (above AR)')}
# MODEL v3.3.1: the exceeded zone slightly more red (alpha 0.035 -> 0.07; same hue, still the lightest zone:
# tools/palette_check.py)
ZONE_GID = 'boundary_zone'
# two accent colours for lines that are not boundaries (household formation, floor area in the diagnostics): the
# boundary pair of model-v2.0.0, kept so those diagnostics are unchanged
ACCENT_ORANGE = '#C2571A'
ACCENT_BLUE = '#1F5FA8'

# runs (palette.toml [runs])
REFERENCE = _RUN['reference']
NEUTRAL_DARK = '#4D4D4D'          # MODEL v4.3.1: a dark neutral grey (not the Reference): ED6 histograms, SF15 bars
# MODEL v4.3.2: the Fig3b 2026-2050 cumulative column and its legend patch, palette.toml [cumulative] (was REFERENCE)
CUMULATIVE_FIG3B = _CUM['fig3b_cumulative_carbon']
# MODEL v4.3.2: the 'release constraint binds' markers of SF15 (not a boundary; were S.AR): a fixed literal
RELEASE_BINDS = '#D7191C'
# MODEL v2.1.2: TL a deep forest green, far darker than the zones; at CAM02-UCS J' 25 it is >= 10 from AR, AtP,
# the Reference, the Pathways, every lever, Population growth and the zones under every simulated deficiency (a mid green
# at the lightness of AR merges with it under deuteranomaly / protanomaly)
TL = _RUN['theoretical_limit']
TL_MARKER = dict(marker='o', ms=8)             # TL on point plots: a larger circle (no star)
SCENARIO = {'REF': dict(color=REFERENCE, ls='-', lw=LW_BOLD, label='Reference'),    # the Reference run itself
            'LOW': dict(color='#B5B5B5', ls='--', lw=LW, label='Low replacement'),
            'HIGH': dict(color='#6E6E6E', ls=':', lw=LW, label='High replacement'),
            # MODEL v3.3.0: Very High replacement (trend continues), the darkest grey, dash-dot
            'VHIGH': dict(color='#1F1F1F', ls='-.', lw=LW, label='Very High replacement (trend continues)')}
MC_BAND = dict(color=REFERENCE, alpha=0.15, lw=0)          # Monte Carlo 5-95% band

# MODEL v2.1.1 palette, inspired by Francis Bacon, Head VI (1949): hue families (golds / ochres, mauves, blues,
# browns); the Pathways vermilion and TL a deep forest green, outside every family; Reference grey. Lightness and
# chroma chosen by maximising the minimum CAM02-UCS distance of every group shown together under every simulated
# deficiency (tools/palette_check.py; docs/PALETTE.md). The strategies reuse the former pathway colours: S1 Avoid the
# ochre of the space-per-person family, S2 Switch the land brown, S3 Improve the construction blue; the deep mauve
# P2_ANCHOR stays the 2026 overbuild band. MODEL v4.3.2: the lever shades L1-L9 (style.LEVER) are retired; a lever is
# drawn in its strategy colour (palette.toml [strategies]) and told apart by marker (LEVER_MARKER).
LEVER_MARKER = ('o', 's', '^', 'D', 'v')          # the k-th lever within its strategy (SF10 lambda sweep)
SURGE_FACE = '#E1D2DD'                  # the Recent replacement surge face (the former L3 shade): fixed
P2_ANCHOR = '#683861'                   # the detailed band '2026 overbuild' (SF2c, SF5): fixed
# MODEL v4.3.0: the typology colours; MODEL v4.3.1: fixed literals (were aliases of the L4 / L8 / L2 lever shades)
TYPOLOGY = {'Detached': '#DFA538', 'Townhouses': '#4A6192', 'Apartments': '#AA7C9D'}
# MODEL v4.3.1: palette.toml [strategies] (were aliases of the L4 / L7 / L8 lever shades)
STRATEGY = {'S1': _SG['avoid'], 'S2': _SG['switch'], 'S3': _SG['improve']}
# MODEL v4.2.1: the Moderate / Ambitious Pathway (orange, darker orange); MODEL v4.3.1: palette.toml [runs]
PATHWAY_SETTING = {'moderate': _RUN['moderate'], 'ambitious': _RUN['ambitious']}
PATHWAY = dict(STRATEGY, pathway=PATHWAY_SETTING['moderate'])     # 'pathway': the Moderate Pathway (Fig5, ED3)
# MODEL v2.1.2: Moderate filled marker, Ambitious hollow (the solution-space convention, used everywhere)
SETTING = {'moderate': dict(ls='-', marker_fill='full', label='Moderate'),
           'ambitious': dict(ls='--', marker_fill='none', label='Ambitious')}

# demand bands, bottom to top: (colour, hatch), coloured by the lever that targets them; labels in naming.BANDS.
# Population growth (untargeted) the deep green-blue hue, solid, clearly lighter since MODEL v2.1.2 (J' 47, was 11);
# Historical replacement a darker lilac with a slightly bluer hue (MODEL v2.1.2) than the Recent replacement surge,
# which keeps the L3 face with a fine, light hatch (both replacement bands are targeted by L3)
# MODEL v4.3.1: the seven display bands of the figures (bands.DISPLAY) take palette.toml [demand_bands]; the detailed
# sub-bands drawn on their own in SF2c / SF5 (2026 overbuild, overbuild absorbed, demolition replacement, unconsented
# additions, surge, ...) keep fixed literals. growth, household size, extra space, vacancy and maintenance are both a
# detailed and a display band and follow the palette.
UNTARGETED_HATCH = None
GROWTH = _DB['population_growth']
REPLACEMENT = '#D0BBDC'                 # the detailed band 'replacement' (demolition replacement, SF2c): fixed
HATCH_LIGHT = '#FFFFFF'                 # the fine hatch of the surge band: drawn in a light colour on its light face
DISPLAY_BAND = {'growth': _DB['population_growth'], 'smaller_households': _DB['household_size_change'],
                'extra_space': _DB['extra_space'], 'vacancy': _DB['vacancy'],
                'net_replacement': _DB['net_replacement'], 'market_balance': _DB['market_balance'],
                'maintenance': _DB['maintenance']}
BAND = {'growth': (GROWTH, None),
        'smaller_households': (DISPLAY_BAND['smaller_households'], None),
        'extra_space': (DISPLAY_BAND['extra_space'], None),
        'vacancy': (DISPLAY_BAND['vacancy'], None),
        'overbuild_2026': (P2_ANCHOR, None),
        'overbuild_absorbed': ('#8D5D93', None),      # negative: outline only (P2 mauve family)
        'replacement': (REPLACEMENT, None),
        'unconsented': ('#BA9AC1', None),             # negative: outline only (replacement lilac family, darker)
        'redevelopment': (SURGE_FACE, '\\\\\\\\'),     # fine hatch, drawn light (BAND_HATCHCOLOR); the only hatch
        'released_tl': ('#95C283', None),             # negative: outline only (TL green family); SF17 re-occupation
        # MODEL v3.2.0 (A2, from v3.1.0): 'Vacancy released' (negative, outline; the L2 vacancy family, darker).
        # MODEL v4.3.1: 'Surplus kept vacant (2050)' removed (TL only, never drawn in a final figure)
        'vacancy_released': ('#481870', None),
        'maintenance': (DISPLAY_BAND['maintenance'], None)}
BAND_ORDER = list(BAND)
NEGATIVE_BANDS = ('overbuild_absorbed', 'unconsented', 'vacancy_released', 'released_tl')
BAND_HATCHCOLOR = {'redevelopment': HATCH_LIGHT}


def band_colour(bid):
    """MODEL v4.3.1: the colour of a band id (display band, detailed band or history band), one rule for faces,
    outlines of negative parts and legend swatches."""
    if bid in DISPLAY_BAND:
        return DISPLAY_BAND[bid]
    if bid in BAND:
        return BAND[bid][0]
    if bid in HISTORY_BAND:
        return HISTORY_BAND[bid][0]
    raise KeyError(f'band_colour: unknown band {bid!r}')
LW_OUTLINE = 0.9                        # the outline of a negative band segment in a cumulative bar

# life-cycle stages (Fig2c, Fig2d; labels in naming.STAGES), stacked A1-A3, A4-A5, soil, maintenance; MODEL v4.3.1:
# palette.toml [life_cycle_stages] (were aliases of the L8 / L9 / L7 lever shades and the maintenance band)
STAGE = {'a1a3': (_ST['a1_a3'], None), 'a4a5': (_ST['a4_a5'], None), 'soil': (_ST['soil_carbon_loss'], None),
         'maintenance': (_ST['maintenance'], None)}
# carbon components of Fig3b (committed after 2050): B2/B4 and C1-C4, palette.toml [life_cycle_stages]
COMPONENT = {'materials_construction': STAGE['a1a3'], 'soil': STAGE['soil'],
             'maintenance': (_ST['committed_b2_b4'], None),     # committed after 2050: B2, B4
             'committed': (_ST['committed_c1_c4'], None)}       # committed after 2050: C1-C4

# unexplained building of the history (Fig2, D05c, K1): a faded reddish face, no hatch (MODEL v2.1.2; face, hatch,
# hatch colour); may be negative
UNEXPLAINED = ('#C6A3A4', None, None)
# MODEL v3.2.0 (A3, from v3.1.0): the history bands of Fig1 (census intervals): household formation and vacancy as the projection
# bands, the census-measured net replacement the replacement face, the retirement-village units a neutral outline
# (negative, out of scope) and the unexplained building its faded reddish face
HISTORY_BAND = {'growth': BAND['growth'], 'smaller_households': BAND['smaller_households'],
                'extra_space': BAND['extra_space'], 'vacancy': BAND['vacancy'],
                'replacement_census': (DISPLAY_BAND['net_replacement'], None),   # the census net replacement
                'retirement_villages': ('#4E463E', None),
                'unexplained': (UNEXPLAINED[0], None)}
# the untargeted band (Fig4): the population-growth grey, hatched
UNTARGETED_GROUP = (BAND['growth'][0], UNTARGETED_HATCH)      # solid since MODEL v2.1.1

# materials: the six Pride-flag stripes (author decision, baseline-pb-v2; one order in every
# figure), soil faded and hatched on top
MATERIAL = [('TIMBER', 'Timber', _MAT['timber']), ('STEEL', 'Steel', _MAT['steel']),
            ('CONCRETE (incl. reinforced)', 'Concrete', _MAT['concrete']),
            ('PLASTICS & PAINT', 'Plastics & paint', _MAT['plastics_paint']),
            ('PLASTERBOARD', 'Plasterboard', _MAT['plasterboard']), ('OTHERS', 'Others', _MAT['others']),
            ('SOIL', 'Soil carbon loss', _MAT['soil_carbon_loss'])]     # MODEL v4.3.1: palette.toml [materials]
SOIL = dict(alpha=0.5, hatch=None, hatchcolor=None)          # MODEL v3.0.0: only the surge band is hatched

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
# MODEL v4.3.1: the tornado colours, fixed literals (were aliases of the Improve blue and the Moderate orange);
# MODEL v4.3.2: palette.toml [one_at_a_time] (Fig7a, ED4, ED5: every draw.tornado)
TORNADO_LOW, TORNADO_HIGH, TORNADO_SINGLE = _OAT['low_end'], _OAT['high_end'], _OAT['single_alternative']
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


def _thousands_label(v, _pos=None):
    s = f'{v:,.0f}' if float(v).is_integer() else f'{v:,g}'
    return s.replace('-', '\u2212')                    # the typographic minus, as matplotlib's default formatter


def thousands_ticks(fig):
    """MODEL v4.3.1 (suite rule): thousands separators on every linear axis whose ticks reach 1,000, on every figure at
    save time. Left alone: log axes and axes with their own formatter (only matplotlib's default ScalarFormatter is
    replaced), year axes (every tick between 1800 and 2100) and axes whose ticks all stay below 1,000."""
    from matplotlib.ticker import FuncFormatter, ScalarFormatter
    for ax in fig.axes:
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            if axis.get_scale() != 'linear' or type(axis.get_major_formatter()) is not ScalarFormatter:
                continue
            lo, hi = min(lim), max(lim)
            locs = [v for v in axis.get_majorticklocs() if lo - 1e-9 <= v <= hi + 1e-9]
            if not locs or max(abs(v) for v in locs) < 1000:
                continue
            if all(1800 <= v <= 2100 and float(v).is_integer() for v in locs):
                continue
            axis.set_major_formatter(FuncFormatter(_thousands_label))


def save(fig, path):
    """Write the PNG of the run profile (light: 200 dpi; full: 600 dpi; MODEL v3.3.1: no PDF), no software / date
    metadata, then close the figure. In the light profile every figure carries a small grey footer
    'LIGHT RUN — n=1000'."""
    import matplotlib.pyplot as plt
    os.makedirs(os.path.dirname(path), exist_ok=True)
    thousands_ticks(fig)                                # MODEL v4.3.1: suite rule (thousands separators)
    footer = runprofile.get('footer')
    if footer:
        fig.text(0.995, 0.002, footer, ha='right', va='bottom', color='#9A9A9A', fontsize=FONT_MIN)
    for fmt in runprofile.get('formats'):
        if fmt != 'png':                         # MODEL v3.3.1: figures are PNG only
            raise ValueError(f'save: unsupported figure format {fmt!r} (PNG only)')
        fig.savefig(path + '.png', dpi=DPI, metadata={'Software': None})
    plt.close(fig)


def save_figure(fig, name, note=None, source=None):
    """Save a planned figure (figure_plan.py file id, e.g. 'D22_boundaries') to its place in outputs/
    (layout.figure). The audit record (axes, year ranges, every text, the note, boundary and band styling) is
    written first (figures/audit.py). note: run-specific caption text for FIGURES.md; source: the data files the
    figure reads (relative to outputs/data/)."""
    import layout
    from figures import audit
    path = layout.figure(name)
    audit.record(fig, name, note=note, source=source)
    save(fig, path)


def registry():
    """Every colour group of the palette: {group: {element: (colour, hatch)}} (tests/test_palette.py: no duplicate
    (colour, hatch) within a group)."""
    return {
        'bands': {b: (c.upper(), h) for b, (c, h) in BAND.items()},
        'runs': {'REF': (REFERENCE.upper(), None), **{k: (v.upper(), None) for k, v in PATHWAY.items()},
                 'TL': (TL.upper(), None), 'LOW': (SCENARIO['LOW']['color'].upper(), None),
                 'HIGH': (SCENARIO['HIGH']['color'].upper(), None),
                 'VHIGH': (SCENARIO['VHIGH']['color'].upper(), None)},
        'stages': {k: (c.upper(), h) for k, (c, h) in STAGE.items()},
        'history_bands': {k: (c.upper(), h) for k, (c, h) in HISTORY_BAND.items()},
        'components': {k: (c.upper(), h) for k, (c, h) in COMPONENT.items()},
        'materials': {code: (c.upper(), None) for code, _, c in MATERIAL},
        'boundaries': {'AR': (AR.upper(), None), 'AtP': (ATP.upper(), None)},
        'zones': {k: (z['color'].upper(), None) for k, z in ZONE.items()},
    }


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
    from figures import audit as figaudit
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
    from figures import audit as figaudit

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
    from figures import audit as figaudit

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
    from figures import audit as figaudit
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
