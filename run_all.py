"""Run the whole pipeline headless, save every figure, and collect the metrics.

    python run_all.py                   # full run: the only basis for reported results and tags
    python run_all.py --pathways-only   # the pathway layer only (the projection is unchanged):
                                        # pathways.py (projection.main() in memory), the pathway Monte
                                        # Carlo, the grouped sensitivity tables, the paper and Extended
                                        # Data figures, the pathway documents and the indexes, then the
                                        # pathway tests, the numerical regression lock, the
                                        # release checks and the byte manifest; only the pathway
                                        # figures are replaced
    python run_all.py --figures-only    # MODEL v2.1.2: redraw every figure, no data may change (byte-checked)
    python run_all.py --export          # also the vector PDF and source-data CSV of every paper, Extended Data
                                        # and key figure (PATHWAY_EXPORT=1); combinable with the modes above
                                        # (default: PNG only)
    python run_all.py --quick           # development: Monte Carlo with fewer draws, no
                                        # frozen-technology Monte Carlo or AESA step, regression
                                        # checks of the Monte Carlo skipped; every output and figure
                                        # marked "QUICK RUN, not for reporting"

In Spyder (or any IPython console): open run_all.py and Run (F5), or
    runfile('run_all.py')                        # full run
    runfile('run_all.py', args='--pathways-only')
Paths are resolved from this file's folder, so the working directory does not
matter. A failed step prints its name and the log to read, and the run stops
there; from the command line the exit code is non-zero, in an interactive
console no SystemExit is raised.

Order: Building_factors -> projection -> Diagnostics -> Sensitivity -> MonteCarlo ->
boundaries (AESA layer; reads the Monte Carlo draws) -> validation -> gap_2026 ->
overbuild_2026 -> scenarios -> reconciliation -> figures_report -> frozen-technology check
(projection, Sensitivity, MonteCarlo, scenarios, boundaries with DECARB_MODE 'none', A4-A5
held, whole life at construction; data in outputs/data/frozen_technology/, no figures) ->
pathways -> pathways_mc (the saved Reference draws through P5 and TL) -> sensitivity_tables (grouped
one-at-a-time tables) -> metrics -> paper (Fig1-Fig6, Tables 1-2, PAPER.md) -> extended_data (ED1-ED13,
EXTENDED_DATA.md) -> key_figures (K1-K6, KEY_FIGURES.md), all from the data files -> results ->
assumptions -> pathways_docs (LEVERS_TABLE.md) -> methods_draft (METHODS_DRAFT.md) -> check_outputs -> indexes
(DIAGNOSTICS.md, outputs/INDEX.md) -> tests, last (incl. the v1.2.1 regression test, which reads
the frozen-technology data, the regression lock of MODEL v1.0.0, which reads every data file, and
the release checks of figures and indexes).
Each script runs in its own process, with the non-interactive matplotlib backend and
PATHWAY_SAVE_FIGURES=1, so every figure is written (outputs/paper/, outputs/extended_data/, outputs/diagnostics/;
layout.py) and nothing is shown. Console output of each step goes to outputs/logs/<step>.log.
"""
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import layout  # noqa: E402

LOGS = layout.LOGS


class StepFailed(Exception):
    pass


def interactive():
    """True inside Spyder, IPython or Jupyter, or python -i."""
    return (hasattr(sys, 'ps1') or bool(sys.flags.interactive)
            or any(m in sys.modules for m in ('spyder_kernels', 'IPython', 'ipykernel')))


def step(name, cmd, env_extra=None):
    os.makedirs(LOGS, exist_ok=True)
    env = dict(os.environ, MPLBACKEND='Agg', PATHWAY_SAVE_FIGURES='1', PYTHONWARNINGS='ignore')
    env.update(env_extra or {})                      # a step's own settings override the defaults
    log_path = os.path.join(LOGS, f'{name}.log')
    t = time.time()
    with open(log_path, 'w') as log:
        rc = subprocess.call(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(f'  {name:<18} {"ok" if rc == 0 else f"FAILED (exit {rc})":<10} {time.time() - t:6.1f} s')
    if rc != 0:
        raise StepFailed(f'Step "{name}" failed (exit {rc}). Read the log: {log_path}')


def tool(name):
    return os.path.join(ROOT, 'tools', f'{name}.py')


def export_env(export):
    return {'PATHWAY_EXPORT': '1' if export else '0'}


def pipeline(quick=False, export=False):
    py = sys.executable
    q = dict({'PATHWAY_QUICK': '1'} if quick else {'PATHWAY_QUICK': '0'}, **export_env(export))

    def run(name, cmd, **extra):
        step(name, cmd, dict(q, **extra))

    # every figure (and its audit record, figaudit.py) is written by this run; a full run also
    # rewrites every data file and report, so nothing stale survives (outputs/INDEX.md, the tests).
    # A quick run keeps the data: it does not re-run the frozen-technology Monte Carlo and AESA.
    for d in (layout.PAPER, layout.EXTENDED_DATA, layout.KEY_FIGURES, layout.DIAGNOSTICS, layout.FIGURE_AUDIT) + (
            () if quick else (layout.DATA, layout.REPORTS)):
        shutil.rmtree(d, ignore_errors=True)
    run('building_factors', [py, os.path.join(ROOT, 'Building_factors.py')])
    run('projection', [py, os.path.join(ROOT, 'projection.py')])
    run('diagnostics', [py, os.path.join(ROOT, 'Diagnostics.py')])
    run('sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')])
    run('montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')])
    run('boundaries', [py, os.path.join(ROOT, 'boundaries.py')])
    run('validation', [py, os.path.join(ROOT, 'validation.py')])
    run('gap_2026', [py, os.path.join(ROOT, 'gap_2026.py')])
    run('overbuild_2026', [py, tool('overbuild_2026')])
    run('scenarios', [py, tool('replacement_scenarios')])
    run('reconciliation', [py, tool('reconciliation')])
    run('figures_report', [py, tool('figures_report')])
    # frozen-technology check run (DECARB_MODE 'none', outputs/data/frozen_technology/): the
    # v1.2.1 regression test compares it with v1.2.1; figures are not saved
    fz = dict(PATHWAY_FROZEN='1', PATHWAY_SAVE_FIGURES='0')
    run('frozen_projection', [py, os.path.join(ROOT, 'projection.py')], **fz)
    run('frozen_sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')], **fz)
    if not quick:
        run('frozen_montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')], **fz)
    run('frozen_scenarios', [py, tool('replacement_scenarios')], **fz)
    if not quick:
        run('frozen_boundaries', [py, os.path.join(ROOT, 'boundaries.py')], **fz)
    # the pathway layer (levers, pathways, attribution, AESA gap): after the AESA layer, whose
    # boundaries it reads
    run('pathways', [py, os.path.join(ROOT, 'pathways.py')])
    # the pathway Monte Carlo: the saved Reference draws through P5 (Moderate) and TL (reads the draw budgets
    # written by boundaries.py)
    run('pathways_mc', [py, os.path.join(ROOT, 'pathways_mc.py')])
    # the grouped one-at-a-time sensitivity tables (Reference carbon, P5 carbon, planetary boundary):
    # existing rows from the data files; the rows MODEL v2.0.0 adds computed on the engine path
    run('sensitivity_tables', [py, tool('sensitivity_tables')])
    # metrics.json is a data file (locked by tests/test_regression_model_v1.py): written before the tests
    run('metrics', [py, tool('metrics')])
    # the figures and tables of the paper (PAPER.md) and Extended Data (EXTENDED_DATA.md), from the data files only
    run('paper', [py, os.path.join(ROOT, 'paper.py')])
    run('extended_data', [py, os.path.join(ROOT, 'extended_data.py')])
    run('key_figures', [py, os.path.join(ROOT, 'key_figures.py')])
    run('results', [py, tool('results')])
    run('assumptions', [py, tool('assumptions')])
    run('pathways_docs', [py, tool('pathways_methods'), '--sections'])
    run('methods_draft', [py, tool('methods_draft')])
    run('check_outputs', [py, tool('check_outputs')])
    # DIAGNOSTICS.md and outputs/INDEX.md, once every output is written; then the tests, last, on
    # the complete output set (figure audit, index, regression lock)
    run('indexes', [py, os.path.join(ROOT, 'indexes.py')])
    run('tests', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests')])


def figures_only(export=False):
    """Figures-only run mode (MODEL v2.1.2): no data may change. The model scripts that draw diagnostics in-process
    (projection, Diagnostics, MonteCarlo, boundaries, figures_report, pathways) are re-run with figures saved; the
    pathway Monte Carlo, the frozen-technology check and the sensitivity tables are not run; the paper, Extended Data
    and key figures are drawn from the data files; nothing is deleted first. The last step requires every file of
    outputs/data/ to be byte-identical to tests/data_snapshot_model_v2_1_1.json (tests/test_data_unchanged.py) and
    stops otherwise."""
    py = sys.executable
    env = dict({'PATHWAY_QUICK': '0'}, **export_env(export))
    step('projection', [py, os.path.join(ROOT, 'projection.py')], env)
    step('diagnostics', [py, os.path.join(ROOT, 'Diagnostics.py')], env)
    step('montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')], env)
    step('boundaries', [py, os.path.join(ROOT, 'boundaries.py')], env)
    step('figures_report', [py, tool('figures_report')], env)
    step('pathways', [py, os.path.join(ROOT, 'pathways.py')], env)
    step('data_unchanged', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests', 'test_data_unchanged.py')], env)
    step('paper', [py, os.path.join(ROOT, 'paper.py')], env)
    step('extended_data', [py, os.path.join(ROOT, 'extended_data.py')], env)
    step('key_figures', [py, os.path.join(ROOT, 'key_figures.py')], env)
    step('pathways_docs', [py, tool('pathways_methods'), '--sections'], env)
    step('methods_draft', [py, tool('methods_draft')], env)
    step('indexes', [py, os.path.join(ROOT, 'indexes.py')], env)
    step('data_unchanged_final', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests', 'test_data_unchanged.py')], env)


def pathways_only(export=False):
    """Pathways-only run mode: the projection is unchanged (every number locked by
    tests/test_regression_model_v1.py), so only the pathway layer runs. projection.main() is
    called in memory by pathways.py; no projection output is written; pathways.py overwrites
    only the pathway diagnostics, paper.py and extended_data.py rewrite outputs/paper/ and
    outputs/extended_data/ from the data files."""
    py = sys.executable
    env = dict({'PATHWAY_QUICK': '0'}, **export_env(export))
    step('pathways', [py, os.path.join(ROOT, 'pathways.py')], env)
    step('pathways_mc', [py, os.path.join(ROOT, 'pathways_mc.py')], env)
    step('sensitivity_tables', [py, tool('sensitivity_tables')], env)
    step('paper', [py, os.path.join(ROOT, 'paper.py')], env)
    step('extended_data', [py, os.path.join(ROOT, 'extended_data.py')], env)
    step('key_figures', [py, os.path.join(ROOT, 'key_figures.py')], env)
    step('pathways_docs', [py, tool('pathways_methods'), '--sections'], env)
    step('methods_draft', [py, tool('methods_draft')], env)
    step('indexes', [py, os.path.join(ROOT, 'indexes.py')], env)
    step('tests_pathways', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests', 'test_pathways.py'),
                            os.path.join(ROOT, 'tests', 'test_regression_model_v1.py'),
                            os.path.join(ROOT, 'tests', 'test_regression_model_v2.py'),
                            os.path.join(ROOT, 'tests', 'test_regression_model_v2_1.py'),
                            os.path.join(ROOT, 'tests', 'test_mcstats.py'),
                            os.path.join(ROOT, 'tests', 'test_pathways_mc.py'),
                            os.path.join(ROOT, 'tests', 'test_sensitivity_tables.py'),
                            os.path.join(ROOT, 'tests', 'test_release.py'),
                            os.path.join(ROOT, 'tests', 'test_output_manifest.py')], env)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    print('run_all:')
    try:
        if '--figures-only' in argv:
            figures_only(export='--export' in argv)
        elif '--pathways-only' in argv:
            pathways_only(export='--export' in argv)
        else:
            pipeline(quick='--quick' in argv, export='--export' in argv)
    except StepFailed as e:
        print(f'\n{e}')
        if interactive():
            return False
        sys.exit(1)
    if '--pathways-only' in argv:
        print(f'\nDone (pathways only; projection unchanged). Data: {layout.data("pathways", frozen=False)} '
              f'(log of each step in {LOGS})')
    else:
        print(f'\nDone. Figures of the paper: {os.path.join(layout.PAPER, "PAPER.md")}; Extended Data: '
              f'{os.path.join(layout.EXTENDED_DATA, "EXTENDED_DATA.md")}; metrics: '
              f'{layout.data("metrics.json", frozen=False)} (log of each step in {LOGS})')
    if '--quick' in argv:
        print('QUICK RUN, not for reporting: re-run without --quick before reporting or tagging.')
    return True


if __name__ == '__main__':
    main()
