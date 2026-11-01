"""Output layout of the model: where every file the pipeline writes goes.

    outputs/                  full profile (run_all.py --profile full); outputs/_light/ mirrors this tree for the
                              light profile (the default)
      paper_main/             Fig1-Fig7 of the paper (figure_plan.PAPER_MAIN)
      paper_extended/         Extended Data ED1-ED10 and the table EDT1 (figure_plan.PAPER_EXTENDED)
      supplementary/<folder>/ Supplementary Figures SF1-SF14 and the table ST1 (figure_plan.SUPPLEMENTARY)
      diagnostics/_audit/     the record of every drawn figure (figures/audit.py; read by the tests)
      FIGURES.md              the index of every figure (indexes / figures/index.py, from figure_plan.py)
      run_meta.json           profile, draws, seeds, git hash, input hash, timestamp, step timings
      data/                   every number the model reports, as CSV and JSON, in the release names of naming.py:
                              baseline/, montecarlo/, aesa/, pathways/, sensitivity/, factors/, figure_source/
                              (the arrays the figures draw that are not otherwise exported), metrics.json
      reports/                generated documents (RESULTS, ASSUMPTIONS, methods draft, levers table, validation)
      logs/                   console output of each run_all.py step (not versioned)

Every module takes its paths from here, so the layout is defined once. RETIRED lists output folders of earlier
releases that run_all.py deletes. The frozen-technology helpers serve the PATHWAY_FROZEN=1 setting, which the
pipeline does not run.
"""
import os

import runprofile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_FULL = os.path.join(ROOT, 'outputs')
# run profiles (runprofile.py): the light profile writes a mirror of the tree under outputs/_light/,
# so a light run never overwrites the outputs of a full run
OUT = os.path.join(OUT_FULL, runprofile.get('out_subdir')) if runprofile.get('out_subdir') else OUT_FULL
DATA = os.path.join(OUT, 'data')
REPORTS = os.path.join(OUT, 'reports')
# figure folders: paper_main/ (Fig1-Fig7), paper_extended/ (the Extended Data), supplementary/ by group, diagnostics/
# (the audit records), FIGURES.md
# PATHWAY_FIG_OUT (set by redraw.py for palette previews) moves the figure folders and the figure audit
# elsewhere; the data are still read from DATA. Unset (the pipeline), the figures go to OUT as before.
FIG_OUT = os.environ.get('PATHWAY_FIG_OUT') or OUT
PAPER_MAIN = os.path.join(FIG_OUT, 'paper_main')
PAPER_EXTENDED = os.path.join(FIG_OUT, 'paper_extended')
SUPPLEMENTARY = os.path.join(FIG_OUT, 'supplementary')   # the Supplementary figures and tables
DIAGNOSTICS = os.path.join(FIG_OUT, 'diagnostics')
DIAGNOSTIC_GROUPS = ('calibration', 'validation', 'boundaries', 'pathways', 'montecarlo', 'sensitivity')
FIGURES_INDEX = os.path.join(OUT, 'FIGURES.md')
RUN_META = os.path.join(OUT, 'run_meta.json')
FIGURE_AUDIT = os.path.join(DIAGNOSTICS, '_audit')
LOGS = os.path.join(OUT, 'logs')
FACTORS = os.path.join(DATA, 'factors')          # written by Building_factors.py (inputs of every run)
FROZEN = 'frozen_technology'                     # data/ sub-folder and reports/ file prefix of the check run
# output folders of earlier releases (deleted by run_all.py): outputs/paper, outputs/extended_data, outputs/key_figures
RETIRED = tuple(os.path.join(OUT, d) for d in ('paper', 'extended_data', 'key_figures'))


def frozen_run():
    """True in the frozen-technology setting (PATHWAY_FROZEN=1)."""
    return os.environ.get('PATHWAY_FROZEN') == '1'


def _under(base, rel, frozen):
    frozen = frozen_run() if frozen is None else frozen
    return os.path.join(base, FROZEN, rel) if frozen else os.path.join(base, rel)


def data(rel, frozen=None):
    """outputs/data/<rel>; outputs/data/frozen_technology/<rel> in the frozen-technology run."""
    return _under(DATA, rel, frozen)


def report(rel, frozen=None):
    """outputs/reports/<rel>; outputs/reports/frozen_technology_<rel> in the frozen-technology run."""
    frozen = frozen_run() if frozen is None else frozen
    return os.path.join(REPORTS, f'{FROZEN}_{rel}' if frozen else rel)


def montecarlo(kind, variant, frozen=None):
    """outputs/data/montecarlo/<kind>_<variant>.csv; kind: summary, draws, annual, sobol."""
    return data(f'montecarlo/{kind}_{variant}.csv', frozen)


def writing(path):
    """path, with its folder created (for every writer)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def figure(name):
    """The folder of a figure (no extension), from its id in figure_plan.py: outputs/paper_main/<file>,
    outputs/paper_extended/<file>, outputs/supplementary/<file> or outputs/diagnostics/<group>/<file>."""
    import figure_plan as FP
    for base, items in ((PAPER_MAIN, FP.PAPER_MAIN), (PAPER_EXTENDED, FP.PAPER_EXTENDED),
                        (SUPPLEMENTARY, FP.SUPPLEMENTARY)):
        for h in items:
            if h['file'] == name:                     # supplementary figures in their folder
                return os.path.join(base, h.get('folder', ''), name)
    for g, rows in FP.DIAGNOSTICS.items():
        if name in (r['file'] for r in rows):
            return os.path.join(DIAGNOSTICS, g, name)
    raise KeyError(f'{name!r} is not a figure of figure_plan.py')
