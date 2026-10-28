"""Palette coverage of the final figures: does every meaning colour and every meaningful fade come from
palette.toml?

Every final figure (main, Extended Data, Supplementary; not the diagnostics) is drawn in process from the committed
outputs, with a probe palette in which every colour key is a distinct vivid hex and every [opacity] key a distinct
probe value. Just before a figure would be saved, every visible artist is read: lines (line, marker face and edge),
patches (face, edge, hatch), collections (faces, edges) and texts. Each colour is then
  * a palette colour (one of the probe hexes: the key it stands for is reported),
  * a neutral (style.NEUTRALS: ink, muted grey, grid, white, black, legend outlines, neutral greys; fixed by design),
  * or NOT FROM THE PALETTE: reported per figure with the artist that draws it.
Every alpha that is not 1 is either a probe opacity (an [opacity] key) or a fixed context fade (style.FIXED_FADES:
definition-break spans, interval spans, rugs, label boxes); anything else is reported. Nothing is saved; the probe
palette is written to a temporary file. This is a tool run by hand, not a test.

    python tools/palette_coverage.py              # exit 1 if any colour or fade is not covered
    python tools/palette_coverage.py --inventory  # also list every colour and alpha found per figure
"""
import argparse
import colorsys
import importlib
import os
import sys
import tempfile
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def probe_palette(default_path, out_path):
    """A copy of the palette file with every colour key a distinct vivid hex and every opacity a distinct value.
    Returns ({hex: 'group.key'}, {alpha: 'opacity.key'})."""
    import tomllib
    with open(default_path, 'rb') as f:
        raw = tomllib.load(f)
    keys = [(g, k) for g, sec in raw.items() if g != 'opacity' for k in sec]
    hexes, used = {}, set()
    n = len(keys)
    for i, (g, k) in enumerate(keys):              # golden-angle hues at three saturation / value levels
        h = (i * 0.618033988749895) % 1.0
        s, v = (1.0, 0.85), (0.75, 0.95)
        r, gg, b = colorsys.hsv_to_rgb(h, s[i % 2], v[(i // 2) % 2])
        hx = '#{:02X}{:02X}{:02X}'.format(round(255 * r), round(255 * gg), round(255 * b))
        while hx in used:
            hx = '#{:02X}{:02X}{:02X}'.format(round(255 * r), round(255 * gg), (round(255 * b) + 7) % 256)
        used.add(hx)
        hexes[(g, k)] = hx
    alphas = {k: round(0.211 + 0.0137 * j, 4) for j, k in enumerate(raw.get('opacity', {}))}
    lines = []
    for g, sec in raw.items():
        lines.append(f'[{g}]')
        for k in sec:
            lines.append(f'{k} = "{hexes[(g, k)]}"' if g != 'opacity' else f'{k} = {alphas[k]}')
        lines.append('')
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines))
    assert len(set(hexes.values())) == n
    return {h: f'{g}.{k}' for (g, k), h in hexes.items()}, {a: f'opacity.{k}' for k, a in alphas.items()}


def _hex(c):
    from matplotlib.colors import to_rgba
    r, g, b, a = to_rgba(c)
    return '#{:02X}{:02X}{:02X}'.format(round(255 * r), round(255 * g), round(255 * b)), a


def _desc(a):
    lab = a.get_label() if hasattr(a, 'get_label') else ''
    lab = '' if not lab or lab.startswith('_') else lab[:60]
    gid = a.get_gid() or ''
    ax_ = getattr(a, 'axes', None)
    ax = ax_.get_title(loc='left')[:20] if hasattr(ax_, 'get_title') else ''
    return f"{type(a).__name__}{'[' + gid + ']' if gid else ''}{' ' + repr(lab) if lab else ''}" \
           f"{' in ' + repr(ax) if ax else ''}"


def artist_colours(fig):
    """[(hex, alpha, artist description, role)] of every visible artist of a figure."""
    from matplotlib.collections import Collection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.text import Text
    out = []

    def add(c, a, role, alpha=None):
        if c is None:
            return
        if isinstance(c, str) and c.lower() == 'none':
            return
        h, ca = _hex(c)
        if ca == 0:
            return
        al = alpha if alpha is not None else ca
        out.append((h, None if al is None else round(float(al), 4), _desc(a), role))

    for a in fig.findobj():
        if not a.get_visible() or a is fig.patch:
            continue
        ax_ = getattr(a, 'axes', None)
        if not hasattr(ax_, 'patch') or a is ax_.patch:     # the figure itself, axes backgrounds
            continue
        al = a.get_alpha() if hasattr(a, 'get_alpha') else None
        if isinstance(a, Line2D):
            if a.get_linestyle() not in ('None', '', ' ', 'none') and a.get_linewidth() > 0:
                add(a.get_color(), a, 'line', al)
            if a.get_marker() not in (None, 'None', '', ' ', 'none'):
                from matplotlib.markers import MarkerStyle
                if MarkerStyle(a.get_marker()).is_filled():        # '|', '_', 'x' have no face
                    add(a.get_markerfacecolor(), a, 'marker face', al)
                add(a.get_markeredgecolor(), a, 'marker edge', al)
        elif isinstance(a, Patch):
            if a.get_fill():
                add(a.get_facecolor(), a, 'face', al)
            if a.get_linewidth() > 0:
                add(a.get_edgecolor(), a, 'edge', al)
            if a.get_hatch():
                add(a.get_hatchcolor() if hasattr(a, 'get_hatchcolor') else a._hatch_color, a, 'hatch', al)
        elif isinstance(a, Collection):
            for c in a.get_facecolors():
                add(tuple(c), a, 'face', al)
            lw = a.get_linewidths()
            if len(lw) and max(lw) > 0:
                for c in a.get_edgecolors():
                    add(tuple(c), a, 'edge', al)
        elif isinstance(a, Text):
            if a.get_text().strip():
                add(a.get_color(), a, 'text', al)
                bb = a.get_bbox_patch()                          # a label box (not a child artist)
                if bb is not None and bb.get_visible() and bb.get_fill():
                    add(bb.get_facecolor(), bb, 'label box face', bb.get_alpha())
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--inventory', action='store_true', help='list every colour and alpha found per figure')
    a = p.parse_args(argv)
    tmp = tempfile.mkdtemp(prefix='palette_coverage_')
    probe = os.path.join(tmp, 'probe.toml')
    hexes, alphas = probe_palette(os.path.join(ROOT, 'palette.toml'), probe)
    os.environ.update(PATHWAY_PROFILE='full', PATHWAY_PALETTE=probe, PATHWAY_DPI='50', MPLBACKEND='Agg',
                      PATHWAY_FIG_OUT=tmp)
    import matplotlib.pyplot as plt
    from figures import style as S
    import figure_plan as FP
    neutrals = {h.upper() for h in S.NEUTRALS.values()}
    # the fixed fades are probed too: every figure reads style.FIXED_FADES when it draws, so a distinct probe value
    # per fade shows which artist uses which, and a bare literal alpha in a figure module cannot pass unnoticed
    fixed_fades = {}
    for j, k in enumerate(S.FIXED_FADES):
        S.FIXED_FADES[k] = round(0.5013 + 0.0071 * j, 4)
        fixed_fades[S.FIXED_FADES[k]] = f'fixed fade {k}'
    found = {}

    def fake_save(fig, name, note=None, source=None):
        found[name] = artist_colours(fig)
        plt.close(fig)
    S.save_figure = fake_save
    for g, f, m in FP.all_figures(profile_full=True):
        importlib.import_module(m).FIGURES[f]()
    bad = 0
    used = defaultdict(set)
    for fid, cols in found.items():
        miss_c, miss_a, inv = defaultdict(set), defaultdict(set), defaultdict(set)
        for h, al, desc, role in cols:
            if h in hexes:
                used[hexes[h]].add(fid.split('_')[0])
                kind = hexes[h]
            elif h in neutrals:
                kind = 'neutral'
            else:
                kind = 'NOT FROM THE PALETTE'
                miss_c[h].add(f'{role} of {desc}')
            if al is not None and al != 1.0:
                if al in alphas:
                    used[alphas[al]].add(fid.split('_')[0])
                    akind = alphas[al]
                elif al in fixed_fades:
                    akind = fixed_fades[al]
                    used[akind].add(fid.split('_')[0])
                else:
                    akind = 'FADE NOT FROM THE PALETTE'
                    miss_a[al].add(f'{role} of {desc} ({h})')
                inv[f'alpha {al} ({akind})'].add(f'{role} of {desc}')
            inv[f'{h} ({kind})'].add(f'{role} of {desc}')
        if a.inventory:
            print(f'\n== {fid}')
            for k in sorted(inv):
                print(f'  {k}: ' + '; '.join(sorted(inv[k]))[:400])
        for h, w in sorted(miss_c.items()):
            bad += 1
            print(f'{fid}: colour {h} not from the palette: ' + '; '.join(sorted(w))[:400])
        for al, w in sorted(miss_a.items()):
            bad += 1
            print(f'{fid}: alpha {al} not from the palette: ' + '; '.join(sorted(w))[:400])
    unused = [k for k in list(hexes.values()) + list(alphas.values()) + list(fixed_fades.values()) if k not in used]
    print(f'\npalette_coverage: {len(found)} final figures; {len(hexes)} colour keys and {len(alphas)} opacity keys '
          f'probed; {bad} colour / fade finding(s) not from the palette.')
    if unused:
        print('keys drawn in no final figure: ' + ', '.join(unused))
    print('figures per key: ' + '; '.join(f"{k}: {', '.join(sorted(v))}" for k, v in sorted(used.items())))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
