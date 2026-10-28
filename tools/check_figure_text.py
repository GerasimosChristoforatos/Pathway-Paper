"""The text rules of the figure suite, checked on the drawn figures. Every final figure is drawn (into a
scratch folder, at low resolution, from the committed data) and, just before it is saved, every visible text is read:
titles, axis labels, legends, annotations and tick labels (after style.thousands_ticks). Exit 1 on a finding:

  * a year range written with a hyphen ("2026-2050"): the suite writes "2026–2050" (en dash);
  * a number of 1,000 or more without a thousands separator (four-digit values from 1800 to 2100 are taken as years);
  * a negative number written with the hyphen-minus ("-0.3"): the suite writes the typographic minus ("−0.3").

    python tools/check_figure_text.py [OUTDIR]
"""
import importlib
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAR_RANGE = re.compile(r'(?<![\d.,])((?:18|19|20)\d\d)\s?-\s?((?:18|19|20)?\d\d)(?![\d%])')
BIG = re.compile(r'(?<![\d.,−\-])(\d{4,})(?![\d,])')
HYPHEN_MINUS = re.compile(r'(?<![\w.])-(?=\d)')            # "-0.3", "(-3%)"; not "1e-06" or "A1-A3"


def findings_of(texts):
    out = set()
    for s in texts:
        flat = s.replace('\n', ' ')
        if YEAR_RANGE.search(s):
            out.add(('year range with a hyphen', flat))
        for m in BIG.finditer(s):
            if len(m.group(1)) == 4 and 1800 <= int(m.group(1)) <= 2100:
                continue
            out.add(('no thousands separator', flat))
        if HYPHEN_MINUS.search(s):
            out.add(('hyphen-minus for a negative number', flat))
    return out


def main(outdir=None):
    os.environ.update(PATHWAY_PROFILE='full', MPLBACKEND='Agg', PATHWAY_DPI='50',
                      PATHWAY_FIG_OUT=outdir or tempfile.mkdtemp(prefix='figtext_'))
    sys.path.insert(0, ROOT)
    from matplotlib.text import Text
    from figures import style as S
    import figure_plan as FP
    found, save = {}, S.save

    def checking_save(fig, path):
        S.thousands_ticks(fig)
        fig.canvas.draw()
        texts = [t.get_text() for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]
        f = findings_of(texts)
        if f:
            found[os.path.basename(path)] = f
        save(fig, path)

    S.save = checking_save
    n = 0
    for _, fid, mod in FP.all_figures():
        importlib.import_module(mod).FIGURES[fid]()
        n += 1
    for k in sorted(found):
        for kind, s in sorted(found[k]):
            print(f'{k}: {kind}: {s[:100]}')
    print(f'check_figure_text: {n} figures, {len(found)} with findings')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
