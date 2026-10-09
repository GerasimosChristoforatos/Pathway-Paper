"""Output layout of the model (MODEL v1.0.0): where every file the pipeline writes goes.

    outputs/
      headline/       the figures of the paper (H1-H11: PNG 300 dpi and vector PDF), their
                      tables and HEADLINE.md (findings, every figure with its caption)
      diagnostics/    every other figure, by group (D01-D34: PNG 300 dpi) and DIAGNOSTICS.md
      data/           every number the model reports, as CSV and JSON, in the release names of
                      naming.py: baseline/ (the Reference projection and its checks), montecarlo/,
                      aesa/ (boundaries and levels of exceedance), pathways/, factors/ (case-study
                      factors), frozen_technology/ (the check run at 2025 factors), metrics.json
      reports/        generated documents: RESULTS, ASSUMPTIONS, the methods draft, the levers
                      table, the validation and reality-check reports
      figure_audit/   the axis record of every figure (figaudit.py; read by the tests)
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
HEADLINE = os.path.join(OUT, 'headline')
DIAGNOSTICS = os.path.join(OUT, 'diagnostics')
FIGURE_AUDIT = os.path.join(OUT, 'figure_audit')
LOGS = os.path.join(OUT, 'logs')
FACTORS = os.path.join(DATA, 'factors')          # written by Building_factors.py (inputs of every run)
FROZEN = 'frozen_technology'                     # sub-folder of data/ and reports/ of the check run


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
    """outputs/reports/<rel>; outputs/reports/frozen_technology/<rel> in the frozen-technology run."""
    return _under(REPORTS, rel, frozen)


def montecarlo(kind, variant, frozen=None):
    """outputs/data/montecarlo/<kind>_<variant>.csv; kind: summary, draws, annual, sobol."""
    return data(f'montecarlo/{kind}_{variant}.csv', frozen)


def writing(path):
    """path, with its folder created (for every writer)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def figure(name):
    """outputs/headline/<file> or outputs/diagnostics/<group>/<file> (no extension) of a figure,
    from its file id in figure_plan.py (e.g. 'H5_boundaries', 'D22_boundaries')."""
    import figure_plan as FP
    for h in FP.HEADLINE:
        if h['file'] == name:
            return os.path.join(HEADLINE, name)
    for g, rows in FP.DIAGNOSTICS.items():
        if name in (f for f, _, _ in rows):
            return os.path.join(DIAGNOSTICS, g, name)
    raise KeyError(f'{name!r} is not a figure of figure_plan.py')
