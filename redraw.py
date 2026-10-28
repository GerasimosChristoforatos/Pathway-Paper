"""Redraw the figures from the committed outputs only, with a palette file (MODEL v4.3.1; v4.3.2: nine groups).

No model, no Monte Carlo: every figure reads outputs/data/ (the full-profile results in the repository) and is drawn
by the figures/ package exactly as in the pipeline. Only the colours of palette.toml change.

    python redraw.py                                   # every figure, palette.toml, 200 dpi preview
    python redraw.py --palette my_colours.toml         # another palette file
    python redraw.py --only main                       # main | extended | supplementary | figure ids (Fig2 ED4 ...)
    python redraw.py --dpi 600 --out somewhere/        # resolution and output folder of a preview
    python redraw.py --final                           # the release figures: outputs/ at 600 dpi (+ FIGURES.md)

Previews go to outputs/_palette_preview/<palette file stem>/ (paper_main/, paper_extended/, supplementary/<topic>/),
so the release PNGs are never overwritten unless --final is given. Each run also writes palette_swatches.png (the
palette groups) to the same folder.

On loading, the palette is validated (every group and key present, "#RRGGBB" values; style.load_palette). Then:
  * a warning (not an error) for two keys that share a figure and are identical or very close: the demand bands,
    materials and life-cycle stages (all in Fig2), the runs and strategies (Fig4-Fig6), the runs, boundaries, zones
    and cumulative column of Fig3, and the one-at-a-time colours (Fig7a, ED4, ED5). "Very close" is a CAM02-UCS
    distance below 10 in normal vision, the convention of tools/palette_check.py. The zones are compared as they show
    on white, at their fixed opacities, with every other key of the figure; they are pale by design (data are drawn
    over them), so zone against zone is checked by their lightness order instead (next item);
  * a warning if the three zones, composited on white, lose the lightness order within both < within AR only <
    exceeded (CAM02-UCS J') in normal vision or under any simulated deficiency (MODEL v4.3.2);
  * the colour-vision report of tools/palette_check.py for every group of two or more keys: per group and vision
    type (normal,
    simulated deuteranomaly, protanomaly and tritanomaly at full severity; Machado et al. 2009, colorspacious), the
    closest pair and its CAM02-UCS distance, flagged below 10.
"""
import argparse
import importlib
import itertools
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

GROUP_OF_SECTION = {'main': 'paper_main', 'extended': 'paper_extended', 'supplementary': 'supplementary'}
# palette keys drawn in one figure: closeness warnings are checked across them (group: keys; None = every key)
SHARED = {'Fig2 (demand bands, materials, life-cycle stages)': {
              'demand_bands': None, 'materials': None,
              'life_cycle_stages': ('a1_a3', 'a4_a5', 'soil_carbon_loss', 'maintenance')},   # committed_*: Fig3b only
          'Fig4-Fig6 (runs, strategies)': {'runs': None, 'strategies': None},
          # MODEL v4.3.2
          'Fig3 (runs, boundaries, zones, cumulative)': {'runs': None, 'boundaries': None, 'boundary_zones': None,
                                                         'cumulative': None},
          'Fig7a/ED4/ED5 (one at a time)': {'one_at_a_time': None}}
# pairs of keys that denote the same quantity (identical by design, not a clash): maintenance B2/B4 as a demand band
# and as a stage, and before / after 2050; MODEL v4.3.2: the Fig3b column is the Reference's cumulative carbon
_MAINT = (('demand_bands', 'maintenance'), ('life_cycle_stages', 'maintenance'), ('life_cycle_stages', 'committed_b2_b4'))
SAME_QUANTITY = {frozenset(p) for p in itertools.combinations(_MAINT, 2)} | {
    frozenset({('runs', 'reference'), ('cumulative', 'fig3b_cumulative_carbon')})}
CLOSE = 10.0                     # CAM02-UCS distance (tools/palette_check.THRESHOLD)


def parse(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--palette', default=os.path.join(ROOT, 'palette.toml'))
    p.add_argument('--only', nargs='+', default=None, help='main | extended | supplementary | figure ids')
    p.add_argument('--dpi', type=int, default=None, help='default 200 (preview); 600 with --final')
    p.add_argument('--out', default=None, help='default outputs/_palette_preview/<palette stem>/')
    p.add_argument('--final', action='store_true', help='write the release figures (outputs/, 600 dpi)')
    a = p.parse_args(argv)
    if a.final and a.out:
        p.error('--final writes the release folders; do not combine it with --out')
    if a.final and a.dpi not in (None, 600):
        p.error('--final is always 600 dpi')
    a.palette = os.path.abspath(a.palette)
    a.dpi = a.dpi or (600 if a.final else 200)
    stem = os.path.splitext(os.path.basename(a.palette))[0]
    a.out = None if a.final else os.path.abspath(a.out or os.path.join(ROOT, 'outputs', '_palette_preview', stem))
    return a


def check_palette(S):
    """Closeness warnings and the colour-vision report; returns the number of warnings."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import palette_check as PC
    pal = S.PALETTE
    shown = PC.palette_as_shown(S)                  # MODEL v4.3.2: the zones as they show on white
    nwarn = 0
    for fig, groups in SHARED.items():
        keys = [(g, k) for g, ks in groups.items() for k in (ks or pal[g])]
        for a, b in itertools.combinations(keys, 2):
            if frozenset({a, b}) in SAME_QUANTITY or a[0] == b[0] == 'boundary_zones':
                continue                            # zone against zone: the lightness-order check below
            ca, cb = shown[a[0]][a[1]], shown[b[0]][b[1]]
            d = float(((PC.jab(ca, 'normal') - PC.jab(cb, 'normal')) ** 2).sum() ** 0.5)
            if ca == cb or d < CLOSE:
                nwarn += 1
                what = 'identical' if ca == cb else f'very close (CAM02-UCS {d:.1f} < {CLOSE:g})'
                print(f'  WARNING {fig}: {a[0]}.{a[1]} {ca} and {b[0]}.{b[1]} {cb} are {what}')
    ok, J = PC.zone_lightness_order(S)
    if not ok:
        nwarn += 1
        print('  WARNING boundary zones: on white they no longer fall in lightness within both < within AR only < '
              "exceeded under every vision type (CAM02-UCS J' normal / deuteranomaly / protanomaly / tritanomaly: "
              + '; '.join(f"{k} " + ' / '.join(f'{x:.1f}' for x in v) for k, v in J.items()) + ')')
    print('\nColour-vision report (tools/palette_check.py method): closest pair per group, CAM02-UCS distance '
          '(same-quantity pairs excluded; the zones as shown on white)')
    for g, cols in shown.items():
        if len(cols) < 2:
            continue
        pairs = [(x, y) for x, y in itertools.combinations(cols, 2) if frozenset({(g, x), (g, y)}) not in SAME_QUANTITY]
        cells = []
        for v in PC.VISION:
            d, x, y = min((float(((PC.jab(cols[x], v) - PC.jab(cols[y], v)) ** 2).sum() ** 0.5), x, y) for x, y in pairs)
            cells.append(f"{v} {d:.1f}{' (<10)' if d < PC.THRESHOLD else ''} ({x} / {y})")
        print(f'  [{g}] ' + '; '.join(cells))
    return nwarn


def swatches(S, path):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    groups = list(S.PALETTE.items())
    rows = max(len(v) for _, v in groups)
    fig, ax = plt.subplots(figsize=(2.3 * len(groups), 0.32 * rows + 0.7))
    for i, (g, cols) in enumerate(groups):
        ax.text(i * 2.3, rows + 0.3, g, fontsize=8, fontweight='bold', va='bottom')
        for j, (k, c) in enumerate(cols.items()):
            y = rows - 1 - j
            ax.add_patch(Rectangle((i * 2.3, y), 0.45, 0.8, facecolor=c, edgecolor='#555555', lw=0.4))
            ax.text(i * 2.3 + 0.55, y + 0.4, f'{k}\n{c}', fontsize=6, va='center', linespacing=1.0)
    ax.set_xlim(-0.1, 2.3 * len(groups))
    ax.set_ylim(-0.2, rows + 0.9)
    ax.axis('off')
    fig.savefig(path, dpi=200, bbox_inches='tight', metadata={'Software': None})
    plt.close(fig)


def main(argv=None):
    a = parse(sys.argv[1:] if argv is None else argv)
    os.environ.update(PATHWAY_PROFILE='full', PATHWAY_PALETTE=a.palette, PATHWAY_DPI=str(a.dpi), MPLBACKEND='Agg',
                      PATHWAY_REFERENCE_LEGACY='0')
    if a.out:
        os.environ['PATHWAY_FIG_OUT'] = a.out
    else:
        os.environ.pop('PATHWAY_FIG_OUT', None)
    t0 = time.time()
    try:
        from figures import style as S              # validates the palette (style.load_palette)
    except Exception as e:
        if type(e).__name__ == 'PaletteError':
            raise SystemExit(f'palette: {e}')
        raise
    import figure_plan as FP
    import layout
    print(f'palette {a.palette}; {a.dpi} dpi; figures -> {layout.FIG_OUT}; data <- {layout.DATA}')
    if not os.path.isdir(layout.DATA):
        raise SystemExit(f'redraw: no data folder {layout.DATA} (the committed full-profile outputs)')
    nwarn = check_palette(S)
    todo = FP.all_figures(profile_full=True)
    if a.only:
        sec = {GROUP_OF_SECTION[o] for o in a.only if o in GROUP_OF_SECTION}
        ids = {o for o in a.only if o not in GROUP_OF_SECTION}
        known = {f for _, f, _ in todo}
        bad = [i for i in ids if i not in known and not any(f.startswith(i + '_') for f in known)]
        if bad:
            raise SystemExit(f'--only: unknown figure id(s) {bad}')
        todo = [(g, f, m) for g, f, m in todo if g in sec or f in ids or any(f.startswith(i + '_') for i in ids)]
    failed = []
    for g, f, m in todo:
        try:
            importlib.import_module(m).FIGURES[f]()
        except SystemExit:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            failed.append((f, repr(e)))
    if not a.only:                                   # the tables (Extended Data, Supplementary)
        for m in FP.TABLE_MODULES:
            for t in importlib.import_module(m).TABLES.values():
                t()
    if a.final and not a.only:
        from figures import index
        index.write()
    os.makedirs(layout.FIG_OUT, exist_ok=True)
    swatches(S, os.path.join(layout.FIG_OUT, 'palette_swatches.png'))
    print(f'\nredraw: {len(todo) - len(failed)} of {len(todo)} figures in {time.time() - t0:.1f} s -> {layout.FIG_OUT}'
          f' ({nwarn} palette warning{"s" if nwarn != 1 else ""})')
    if failed:
        raise SystemExit('redraw failed: ' + '; '.join(f'{f} ({e})' for f, e in failed))


if __name__ == '__main__':
    main()
