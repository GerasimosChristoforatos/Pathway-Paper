"""Draw every figure of figure_plan.py (or the ids given), then write outputs/FIGURES.md (figures/index.py)."""
import importlib
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import matplotlib  # noqa: E402

matplotlib.use('Agg')
import figure_plan as FP  # noqa: E402
import runprofile  # noqa: E402


def main(ids=None):
    full = runprofile.name() == 'full'
    todo = [(g, f, m) for g, f, m in FP.all_figures(profile_full=full) if not ids or f in ids]
    mods = {}
    t0 = time.time()
    failed = []
    for g, f, m in todo:
        mod = mods.setdefault(m, importlib.import_module(m))
        if f not in mod.FIGURES:
            failed.append((f, f'not drawn by {m}'))
            continue
        try:
            mod.FIGURES[f]()
        except SystemExit:
            raise
        except Exception as e:                       # report every failing figure, then stop
            import traceback
            traceback.print_exc()
            failed.append((f, repr(e)))
    if not ids:                                       # the tables of the Extended Data
        from figures import paper_extended
        for f in paper_extended.TABLES.values():
            f()
    from figures import index
    index.write()
    print(f'figures: {len(todo) - len(failed)} of {len(todo)} drawn in {time.time() - t0:.0f} s')
    if failed:
        raise SystemExit('figures failed: ' + '; '.join(f'{f} ({e})' for f, e in failed))


if __name__ == '__main__':
    main(sys.argv[1:] or None)
