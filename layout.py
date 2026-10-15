"""Output layout of the model (MODEL v3.0.0): where every file the pipeline writes goes.

    outputs/                  full profile (run_all.py --profile full); outputs/_light/ mirrors this tree for the
                              light profile (the default) and outputs/_legacy/ for --reference-legacy
      paper_main/             Fig1-Fig8 of the paper (figure_plan.PAPER_MAIN)
      paper_extended/         Extended Data ED1-ED14 and the table EDT1 (figure_plan.PAPER_EXTENDED)
      diagnostics/<group>/    calibration, validation, boundaries, pathways, montecarlo, sensitivity; _audit/: the
                              record of every drawn figure (figures/audit.py; read by the tests)
      FIGURES.md              the index of every figure (indexes / figures/index.py, from figure_plan.py)
      run_meta.json           profile, draws, seeds, git hash, input hash, timestamp, step timings
      data/                   every number the model reports, as CSV and JSON, in the release names of naming.py:
                              baseline/, montecarlo/, aesa/, pathways/, sensitivity/, factors/, figure_source/
                              (the arrays the figures draw that are not otherwise exported), metrics.json
      reports/                generated documents (RESULTS, ASSUMPTIONS, methods draft, levers table, validation)
      logs/                   console output of each run_all.py step (not versioned)

Every module takes its paths from here, so the layout is defined once. The folders of MODEL v2.1.2 (outputs/paper,
outputs/extended_data, outputs/key_figures) are RETIRED and deleted by run_all.py. The frozen-technology helpers
below are kept for the data layout of earlier releases; MODEL v3.0.0 does not run the frozen-technology check
(docs/CHANGELOG_v3.md).
"""
import os

import runprofile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_FULL = os.path.join(ROOT, 'outputs')
# MODEL v3.0.0 run profiles (runprofile.py): the light profile writes a mirror of the tree under outputs/_light/,
# so a light run never overwrites the outputs of a full run
OUT = os.path.join(OUT_FULL, runprofile.get('out_subdir')) if runprofile.get('out_subdir') else OUT_FULL
# run_all.py --reference-legacy (PATHWAY_REFERENCE_LEGACY=1): the Reference of MODEL v2.1 (overbuild never absorbed),
# written under outputs/_legacy/ so it never mixes with the v3 outputs
LEGACY = os.environ.get('PATHWAY_REFERENCE_LEGACY') == '1'
if LEGACY:
    OUT = os.path.join(OUT_FULL, '_legacy')
DATA = os.path.join(OUT, 'data')
REPORTS = os.path.join(OUT, 'reports')
# MODEL v3.0.0 output architecture: paper_main/ (Fig1-Fig8), paper_extended/ (the Extended Data), diagnostics/
# by group (calibration, validation, boundaries, pathways, montecarlo, sensitivity), FIGURES.md
PAPER_MAIN = os.path.join(OUT, 'paper_main')
PAPER_EXTENDED = os.path.join(OUT, 'paper_extended')
DIAGNOSTICS = os.path.join(OUT, 'diagnostics')
DIAGNOSTIC_GROUPS = ('calibration', 'validation', 'boundaries', 'pathways', 'montecarlo', 'sensitivity')
FIGURES_INDEX = os.path.join(OUT, 'FIGURES.md')
RUN_META = os.path.join(OUT, 'run_meta.json')
FIGURE_AUDIT = os.path.join(DIAGNOSTICS, '_audit')
LOGS = os.path.join(OUT, 'logs')
FACTORS = os.path.join(DATA, 'factors')          # written by Building_factors.py (inputs of every run)
FROZEN = 'frozen_technology'                     # data/ sub-folder and reports/ file prefix of the check run
# retired in MODEL v3.0.0 (deleted by run_all.py): outputs/paper, outputs/extended_data, outputs/key_figures
RETIRED = tuple(os.path.join(OUT, d) for d in ('paper', 'extended_data', 'key_figures'))


def frozen_run():
    """True in the frozen-technology check run (run_all.py steps 'frozen_*', PATHWAY_FROZEN=1)."""
    return os.environ.get('PATHWAY_FROZEN') == '1'


def _under(base, rel, frozen):
    frozen = frozen_run() if frozen is None else frozen
    return os.path.join(base, FROZEN, rel) if frozen else os.path.join(base, rel)


def data(rel, frozen=None):
    """outputs/data/<rel>; outputs/data/frozen_technology/<rel> in the frozen-technology run."""
    return _under(DATA, rel, frozen)


def report(rel, frozen=None):
    """outputs/reports/<rel>; outputs/reports/frozen_technology_<rel> in the frozen-technology run
    (docs/RENAMING.md section 2)."""
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
    outputs/paper_extended/<file> or outputs/diagnostics/<group>/<file>."""
    import figure_plan as FP
    for base, items in ((PAPER_MAIN, FP.PAPER_MAIN), (PAPER_EXTENDED, FP.PAPER_EXTENDED)):
        if name in (h['file'] for h in items):
            return os.path.join(base, name)
    for g, rows in FP.DIAGNOSTICS.items():
        if name in (r['file'] for r in rows):
            return os.path.join(DIAGNOSTICS, g, name)
    raise KeyError(f'{name!r} is not a figure of figure_plan.py')
