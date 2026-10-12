"""Output layout of the model (MODEL v2.0.0): where every file the pipeline writes goes.

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

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'outputs')
DATA = os.path.join(OUT, 'data')
REPORTS = os.path.join(OUT, 'reports')
PAPER = os.path.join(OUT, 'paper')
EXTENDED_DATA = os.path.join(OUT, 'extended_data')
KEY_FIGURES = os.path.join(OUT, 'key_figures')
DIAGNOSTICS = os.path.join(OUT, 'diagnostics')
FIGURE_AUDIT = os.path.join(DIAGNOSTICS, '_audit')
LOGS = os.path.join(OUT, 'logs')
FACTORS = os.path.join(DATA, 'factors')          # written by Building_factors.py (inputs of every run)
FROZEN = 'frozen_technology'                     # data/ sub-folder and reports/ file prefix of the check run


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
    """outputs/paper/<file>, outputs/extended_data/<file> or outputs/diagnostics/<group>/<file> (no
    extension) of a figure, from its file id in figure_plan.py (e.g. 'Fig5_boundaries_attribution',
    'ED1_reference_carbon_tornado', 'D22_boundaries')."""
    import figure_plan as FP
    for base, items in ((PAPER, FP.PAPER), (EXTENDED_DATA, FP.EXTENDED_DATA), (KEY_FIGURES, FP.KEY_FIGURES)):
        if name in (h['file'] for h in items):
            return os.path.join(base, name)
    for g, rows in FP.DIAGNOSTICS.items():
        if name in (f for f, _, _ in rows):
            return os.path.join(DIAGNOSTICS, g, name)
    raise KeyError(f'{name!r} is not a figure of figure_plan.py')


def vector(path):
    """True for a figure of the paper, Extended Data or the key figures (vector PDF with run_all.py --export)."""
    return any(path.startswith(b + os.sep) for b in (PAPER, EXTENDED_DATA, KEY_FIGURES))
