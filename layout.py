"""Output layout of the model (MODEL v3.0.0): where every file the pipeline writes goes.

    outputs/
      paper/          the figures of the paper (Fig1-Fig6: PNG 300 dpi, vector PDF and source-data
                      CSV), Tables 1-2 (Markdown and CSV) and PAPER.md (headline findings, every
                      figure with its caption)
      extended_data/  the Extended Data figures (ED1-ED10, same formats) and EXTENDED_DATA.md
      key_figures/    K1-K6 (MODEL v2.1.0): the story in six figures, KEY_FIGURES.md
      diagnostics/    every other figure, by group (PNG 300 dpi), DIAGNOSTICS.md, and
                      _audit/: the record of every figure (figaudit.py; read by the tests)
      data/           every number the model reports, as CSV and JSON, in the release names of
                      naming.py: baseline/ (the Reference projection and its checks), montecarlo/,
                      aesa/ (boundaries and levels of exceedance), pathways/, factors/ (case-study
                      factors), frozen_technology/ (the check run at 2025 factors), metrics.json
      reports/        generated documents: RESULTS, ASSUMPTIONS, the methods draft, the levers
                      table, the validation and reality-check reports (frozen-technology run:
                      frozen_technology_<name>.md)
      logs/           console output of each run_all.py step (not versioned)

Every module takes its paths from here, so the layout is defined once. The data file names
are those of naming._file (docs/RENAMING.md, section 2); tests/test_release.py checks that
the two agree and that every file in outputs/ is indexed.
"""
import os

import runprofile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_FULL = os.path.join(ROOT, 'outputs')
# MODEL v3.0.0 run profiles (runprofile.py): the light profile writes a mirror of the tree under outputs/_light/,
# so a light run never overwrites the outputs of a full run
OUT = os.path.join(OUT_FULL, runprofile.get('out_subdir')) if runprofile.get('out_subdir') else OUT_FULL
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
