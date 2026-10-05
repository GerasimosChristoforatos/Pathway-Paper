"""Run the whole pipeline headless, save every figure, and collect the metrics.

    python run_all.py            # full run: the only
                                 # basis for reported results and tags
    python run_all.py --quick    # development: Monte Carlo with fewer draws, no
                                 # frozen-technology Monte Carlo, MC regression
                                 # checks skipped; every output marked
                                 # "QUICK RUN, not for reporting"
    python run_all.py --compare-modes   # also run the other decarbonisation modes
                                 # in full and the item-level decarbonisation
                                 # sensitivities (outputs/modes/,
                                 # outputs/DECARB_MODES.md, stamped with date and
                                 # commit); the documents read the stored result
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
-> PB (planetary-boundary layer; reads the Monte Carlo draws) -> validation
-> gap_2026 -> near_term_join -> scenarios -> figures_report -> frozen
technology check (Boss, Sensitivity, MonteCarlo, scenarios, PB with DECARB_MODE
'none', written to outputs/frozen/, figures not saved) -> [--compare-modes:
comparison runs of the other decarbonisation modes (Boss, Sensitivity,
MonteCarlo, PB; outputs/modes/<mode>/, figures not saved)] -> tests (incl. the
v1.2.1 regression test, which reads outputs/frozen/) -> metrics ->
[--compare-modes: decarb_modes] -> results ->
assumptions -> baseline_draft -> pb_methods (-> quick_stamp, quick runs). Each script
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


def comparison_modes():
    """Decarbonisation modes other than 'none' (outputs/frozen/) and the adopted one."""
    sys.path.insert(0, ROOT)
    import Boss
    import Building_factors as BF
    return [m for m in BF.DECARB_MODES if m not in ('none', Boss.DECARB_MODE)]


def pipeline(skip_mc, quick=False, compare=False):
    py = sys.executable
    q = {'PATHWAY_QUICK': '1'} if quick else {'PATHWAY_QUICK': '0'}

    def run(name, cmd, **extra):
        step(name, cmd, dict(q, **extra))

    run('building_factors', [py, os.path.join(ROOT, 'Building_factors.py')])
    run('boss', [py, os.path.join(ROOT, 'Boss.py')])
    run('diagnostics', [py, os.path.join(ROOT, 'Diagnostics.py')])
    run('sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')])
    if not skip_mc:
        run('montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')])
    run('pb', [py, os.path.join(ROOT, 'PB.py')])
    run('validation', [py, os.path.join(ROOT, 'validation.py')])
    run('gap_2026', [py, os.path.join(ROOT, 'gap_2026.py')])
    run('near_term_join', [py, tool('near_term_join')])
    run('scenarios', [py, tool('replacement_scenarios')])
    run('figures_report', [py, tool('figures_report')])
    # frozen-technology check run (DECARB_MODE 'none', outputs/frozen/): the
    # v1.2.1 regression test compares it with v1.2.1; figures are not saved
    fz = dict(PATHWAY_FROZEN='1', PATHWAY_SAVE_FIGURES='0')
    run('frozen_boss', [py, os.path.join(ROOT, 'Boss.py')], **fz)
    run('frozen_sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')], **fz)
    if not (skip_mc or quick):
        run('frozen_montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')], **fz)
    run('frozen_scenarios', [py, tool('replacement_scenarios')], **fz)
    if not (skip_mc or quick):
        run('frozen_pb', [py, os.path.join(ROOT, 'PB.py')], **fz)
    # optional (--compare-modes): full runs of the other decarbonisation modes
    # into outputs/modes/<mode>/ and the comparison with the item-level
    # sensitivities (tools/decarb_modes.py -> outputs/DECARB_MODES.md, stamped
    # with date and commit); the documents read the stored result
    if compare:
        for mode in comparison_modes():
            md = dict(PATHWAY_DECARB_MODE=mode, PATHWAY_SAVE_FIGURES='0')
            run(f'mode_{mode}_boss', [py, os.path.join(ROOT, 'Boss.py')], **md)
            run(f'mode_{mode}_sensitivity', [py, os.path.join(ROOT, 'Sensitivity.py')], **md)
            if not skip_mc:
                run(f'mode_{mode}_montecarlo', [py, os.path.join(ROOT, 'MonteCarlo.py')], **md)
                run(f'mode_{mode}_pb', [py, os.path.join(ROOT, 'PB.py')], **md)
    run('tests', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests')])
    run('metrics', [py, tool('metrics')] + (['--mc-stale'] if skip_mc else []))
    if compare:
        run('decarb_modes', [py, tool('decarb_modes')])
    run('results', [py, tool('results')])
    run('assumptions', [py, tool('assumptions')])
    run('baseline_draft', [py, tool('baseline_draft')])
    run('pb_methods', [py, tool('pb_methods')])
    if quick:
        run('quick_stamp', [py, tool('quick_stamp')])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    print('run_all:')
    try:
        pipeline(skip_mc='--no-mc' in argv, quick='--quick' in argv, compare='--compare-modes' in argv)
    except StepFailed as e:
        print(f'\n{e}')
        if interactive():
            return False
        sys.exit(1)
    print(f'\nDone. Metrics: {os.path.join(ROOT, "outputs", "metrics.json")} '
          f'(log of each step in {LOGS})')
    if '--quick' in argv:
        print('QUICK RUN, not for reporting: re-run without --quick before reporting or tagging.')
    return True


if __name__ == '__main__':
    main()
