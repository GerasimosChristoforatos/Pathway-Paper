"""Mark every figure of a quick run (run_all.py --quick) as not for reporting:
a red footer band reading 'QUICK RUN, not for reporting' is added to the
bottom of each PNG in outputs/figures/. Runs only in quick mode; a full run
regenerates every figure without it.

    python tools/quick_stamp.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'outputs', 'figures')
TEXT = 'QUICK RUN, not for reporting (run_all.py --quick: fewer Monte Carlo draws)'


def stamp(path):
    im = Image.open(path).convert('RGB')
    h = max(28, im.height // 30)
    out = Image.new('RGB', (im.width, im.height + h), 'white')
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.rectangle([0, im.height, im.width, im.height + h], fill=(192, 57, 43))
    font = ImageFont.load_default(size=int(h * 0.6))
    d.text((10, im.height + h * 0.18), TEXT, fill='white', font=font)
    out.save(path)


def main():
    if os.environ.get('PATHWAY_QUICK') != '1':
        raise SystemExit('quick_stamp: not a quick run (PATHWAY_QUICK != 1); nothing stamped.')
    files = sorted(f for f in os.listdir(FIG) if f.endswith('.png'))
    for f in files:
        stamp(os.path.join(FIG, f))
    print(f'quick_stamp: {len(files)} figures marked "QUICK RUN, not for reporting"')


if __name__ == '__main__':
    main()
