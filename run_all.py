"""Run the whole pipeline headless, save every figure, and collect the metrics.

    python run_all.py                   # full run: the only basis for reported results and tags
    python run_all.py --pathways-only   # the pathway layer only (the projection is unchanged):
                                        # pathways.py (projection.main() in memory), the pathway
                                        # tests and the numerical regression lock, then the pathway
                                        # documents; only the pathway figures are replaced
    python run_all.py --quick           # development: Monte Carlo with fewer draws, no
                                        # frozen-technology Monte Carlo or AESA step, regression
                                        # checks of the Monte Carlo skipped; every output and figure
                                        # marked "QUICK RUN, not for reporting"
    python run_all.py --no-mc           # skip the Monte Carlo (development only; the MC metrics are
                                        # carried over from the last full run and marked stale)

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
pathways -> metrics -> tests (incl. the v1.2.1 regression test, which reads the
frozen-technology data, and the regression lock of MODEL v1.0.0, which reads every data file)
-> results -> assumptions -> baseline_draft -> pb_methods -> pathways_docs -> check_outputs.
Each script runs in its own process, with the non-interactive matplotlib backend and
PATHWAY_SAVE_FIGURES=1, so every figure is written (outputs/headline/, outputs/diagnostics/;
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


def pipeline(skip_mc, quick=False):
    py = sys.executable
    q = {'PATHWAY_QUICK': '1'} if quick else {'PATHWAY_QUICK': '0'}

    def run(name, cmd, **extra):
        step(name, cmd, dict(q, **extra))

    # every figure (and its audit record, figaudit.py) is written by this run
    for d in (layout.HEADLINE, layout.DIAGNOSTICS, layout.FIGURE_AUDIT):
        shutil.rmtree(d, ignore_errors=True)
    run('building_factors', [py, os.path.join(ROOT, 'Building_factors.py')])
    run('projection', [py, os.path.join(ROOT, 'projection.py')])
    run('diagnostics', [py, os.path.join(ROOT, 'Diagnostics.py')])
    run('sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')])
    if not skip_mc:
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
    if not (skip_mc or quick):
        run('frozen_montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')], **fz)
    run('frozen_scenarios', [py, tool('replacement_scenarios')], **fz)
    if not (skip_mc or quick):
        run('frozen_boundaries', [py, os.path.join(ROOT, 'boundaries.py')], **fz)
    # PATHWAYS v2 (levers, pathways, attribution, AESA gap): after PB and after figures_report
    # (which rewrites FIGURES.md; pathways.py appends its own section), before the tests
    run('pathways', [py, os.path.join(ROOT, 'pathways.py')])
    # metrics.json is a data file (locked by tests/test_regression_model_v1.py): written before the tests
    run('metrics', [py, tool('metrics')] + (['--mc-stale'] if skip_mc else []))
    run('tests', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests')])
    run('results', [py, tool('results')])
    run('assumptions', [py, tool('assumptions')])
    run('baseline_draft', [py, tool('baseline_draft')])
    run('pb_methods', [py, tool('pb_methods')])
    run('pathways_docs', [py, tool('pathways_methods'), '--sections'])
    run('check_outputs', [py, tool('check_outputs')])


def pathways_only():
    """Pathways-only run mode: the projection is unchanged (every number locked by
    tests/test_regression_model_v1.py), so only the pathway layer runs. projection.main() is
    called in memory by pathways.py; no projection output is written; pathways.py overwrites
    only the pathway figures."""
    py = sys.executable
    env = {'PATHWAY_QUICK': '0'}
    step('pathways', [py, os.path.join(ROOT, 'pathways.py')], env)
    step('tests_pathways', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests', 'test_pathways.py'),
                            os.path.join(ROOT, 'tests', 'test_regression_model_v1.py')], env)
    step('pathways_docs', [py, tool('pathways_methods'), '--sections'], env)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    print('run_all:')
    try:
        if '--pathways-only' in argv:
            pathways_only()
        else:
            pipeline(skip_mc='--no-mc' in argv, quick='--quick' in argv)
    except StepFailed as e:
        print(f'\n{e}')
        if interactive():
            return False
        sys.exit(1)
    if '--pathways-only' in argv:
        print(f'\nDone (pathways only; projection unchanged). Data: {layout.data("pathways", frozen=False)} '
              f'(log of each step in {LOGS})')
    else:
        print(f'\nDone. Figures of the paper: {os.path.join(layout.HEADLINE, "HEADLINE.md")}; metrics: '
              f'{layout.data("metrics.json", frozen=False)} (log of each step in {LOGS})')
    if '--quick' in argv:
        print('QUICK RUN, not for reporting: re-run without --quick before reporting or tagging.')
    return True


if __name__ == '__main__':
    main()
