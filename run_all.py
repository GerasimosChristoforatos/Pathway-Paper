"""Run the whole pipeline headless, save every figure, and collect the metrics.

    python run_all.py            # full run (about 5 minutes)
    python run_all.py --no-mc    # skip the Monte Carlo (development only; the
                                 # MC metrics are then carried over from the
                                 # last full run and marked stale)

In Spyder (or any IPython console): open run_all.py and Run (F5), or
    runfile('run_all.py')
Paths are resolved from this file's folder, so the working directory does not
matter. A failed step prints its name and the log to read, and the run stops
there; from the command line the exit code is non-zero, in an interactive
console no SystemExit is raised.

Order: Building_factors -> Boss -> Diagnostics -> Sensitivity -> MonteCarlo
-> validation -> gap_2026 -> near_term_join -> scenarios -> figures_report
-> tests (incl. the v1.2.1 regression test, which reads the outputs written
above) -> metrics -> results -> assumptions -> baseline_draft. Each script
runs in its own process, with the non-interactive matplotlib backend and
PATHWAY_SAVE_FIGURES=1, so every figure is written to outputs/figures/ and
nothing is shown. Console output of each step goes to outputs/logs/<step>.log.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(ROOT, 'outputs', 'logs')


class StepFailed(Exception):
    pass


def interactive():
    """True inside Spyder, IPython or Jupyter, or python -i."""
    return (hasattr(sys, 'ps1') or bool(sys.flags.interactive)
            or any(m in sys.modules for m in ('spyder_kernels', 'IPython', 'ipykernel')))


def step(name, cmd):
    os.makedirs(LOGS, exist_ok=True)
    env = dict(os.environ, MPLBACKEND='Agg', PATHWAY_SAVE_FIGURES='1', PYTHONWARNINGS='ignore')
    log_path = os.path.join(LOGS, f'{name}.log')
    t = time.time()
    with open(log_path, 'w') as log:
        rc = subprocess.call(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(f'  {name:<18} {"ok" if rc == 0 else f"FAILED (exit {rc})":<10} {time.time() - t:6.1f} s')
    if rc != 0:
        raise StepFailed(f'Step "{name}" failed (exit {rc}). Read the log: {log_path}')


def tool(name):
    return os.path.join(ROOT, 'tools', f'{name}.py')


def pipeline(skip_mc):
    py = sys.executable
    step('building_factors', [py, os.path.join(ROOT, 'Building_factors.py')])
    step('boss', [py, os.path.join(ROOT, 'Boss.py')])
    step('diagnostics', [py, os.path.join(ROOT, 'Diagnostics.py')])
    step('sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')])
    if not skip_mc:
        step('montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')])
    step('validation', [py, os.path.join(ROOT, 'validation.py')])
    step('gap_2026', [py, os.path.join(ROOT, 'gap_2026.py')])
    step('near_term_join', [py, tool('near_term_join')])
    step('scenarios', [py, tool('replacement_scenarios')])
    step('figures_report', [py, tool('figures_report')])
    step('tests', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests')])
    step('metrics', [py, tool('metrics')] + (['--mc-stale'] if skip_mc else []))
    step('results', [py, tool('results')])
    step('assumptions', [py, tool('assumptions')])
    step('baseline_draft', [py, tool('baseline_draft')])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    print('run_all:')
    try:
        pipeline(skip_mc='--no-mc' in argv)
    except StepFailed as e:
        print(f'\n{e}')
        if interactive():
            return False
        sys.exit(1)
    print(f'\nDone. Metrics: {os.path.join(ROOT, "outputs", "metrics.json")} '
          f'(log of each step in {LOGS})')
    return True


if __name__ == '__main__':
    main()
