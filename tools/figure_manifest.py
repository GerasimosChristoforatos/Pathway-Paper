"""MODEL v4.3.0: outputs/figure_manifest.csv, one row per figure of figure_plan.py (main, Extended Data,
Supplementary): final id, file (relative to the profile's output folder), section, source script, source data files
and a one-line caption stub (the figure_plan title). Run after the figures are drawn (run_all.py)."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figure_plan as FP  # noqa: E402
import layout  # noqa: E402
import runprofile  # noqa: E402

SECTIONS = (('Main', FP.PAPER_MAIN), ('ED', FP.PAPER_EXTENDED), ('Supp', FP.SUPPLEMENTARY))


def rows():
    full = runprofile.name() == 'full'
    out = []
    for section, items in SECTIONS:
        for h in items:
            if h['file'] in FP.FULL_ONLY and not full:
                continue
            path = layout.figure(h['file']) + '.png'
            if not os.path.exists(path):
                raise SystemExit(f'figure_manifest: {h["file"]} is planned but not drawn ({path})')
            out.append(dict(id=h['id'], file=os.path.relpath(path, layout.OUT).replace(os.sep, '/'),
                            section=section, source_script=h['module'].replace('.', '/') + '.py',
                            source_data='; '.join(f'data/{s}' for s in h['source']), caption_stub=h['title']))
    return out


def main():
    path = layout.writing(os.path.join(layout.OUT, 'figure_manifest.csv'))
    rs = rows()
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rs[0]))
        w.writeheader()
        w.writerows(rs)
    print(f'figure_manifest: {len(rs)} figures -> {os.path.relpath(path, layout.OUT)}')


if __name__ == '__main__':
    main()
