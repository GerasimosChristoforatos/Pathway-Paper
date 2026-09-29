"""Run the whole pipeline headless, save every figure, and collect the metrics.

    python run_all.py            # full run (about 5 minutes)
    python run_all.py --no-mc    # skip the Monte Carlo (development only; the
                                 # MC metrics are then carried over from the
                                 # last full run and marked stale)

Order: Building_factors -> Boss -> Diagnostics -> Sensitivity -> MonteCarlo
-> tests -> validation -> gap_2026 (A1 evidence) -> metrics. Each script runs in its own process, with
the non-interactive matplotlib backend and PATHWAY_SAVE_FIGURES=1, so
every figure is written to outputs/figures/ and nothing is shown. Console
output of each step goes to outputs/logs/<step>.log. The run stops at the
first failing step.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(ROOT, 'outputs', 'logs')


def step(name, cmd):
    os.makedirs(LOGS, exist_ok=True)
    env = dict(os.environ, MPLBACKEND='Agg', PATHWAY_SAVE_FIGURES='1', PYTHONWARNINGS='ignore')
    t = time.time()
    with open(os.path.join(LOGS, f'{name}.log'), 'w') as log:
        rc = subprocess.call(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(f'  {name:<18} {"ok" if rc == 0 else f"FAILED (exit {rc})":<10} {time.time() - t:6.1f} s')
    if rc != 0:
        sys.exit(f'Step {name} failed: see outputs/logs/{name}.log')


def main():
    py = sys.executable
    skip_mc = '--no-mc' in sys.argv
    print('run_all:')
    step('building_factors', [py, 'Building_factors.py'])
    step('boss', [py, 'Boss.py'])
    step('diagnostics', [py, 'Diagnostics.py'])
    step('sensitivity', [py, 'Sensitivity.py'])
    if not skip_mc:
        step('montecarlo', [py, 'MonteCarlo.py'])
    if os.path.isdir(os.path.join(ROOT, 'tests')):
        step('tests', [py, '-m', 'pytest', '-q', 'tests'])
    if os.path.exists(os.path.join(ROOT, 'validation.py')):
        step('validation', [py, 'validation.py'])
    if os.path.exists(os.path.join(ROOT, 'gap_2026.py')):
        step('gap_2026', [py, 'gap_2026.py'])
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    os.environ['MPLBACKEND'] = 'Agg'
    import metrics
    m = metrics.collect(extra={'mc_stale': True} if skip_mc else None)
    print('metrics -> outputs/metrics.json')
    for key, label, f in metrics.FIELDS:
        v = metrics.get(m, key)
        print(f'  {label:<55} {f.format(v) if v is not None else "n/a"}')


if __name__ == '__main__':
    main()
