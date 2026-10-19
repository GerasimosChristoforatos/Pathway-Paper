"""Run the whole pipeline headless (MODEL v3.0.0).

    python run_all.py                       # light profile (DEFAULT, temporary): outputs/_light/
    python run_all.py --profile full        # full profile: outputs/ (5,000 draws, Sobol, PDF + PNG 600 dpi)
    python run_all.py --figures-only        # redraw every figure from the data files; outputs/data must stay
                                            # byte-identical (checked: SHA-256 of every file before and after)
    python run_all.py --reference-legacy    # the MODEL v2.1 Reference (overbuild never absorbed) in outputs/_legacy/,
                                            # checked against the v2.1 fixture to 1e-12 (tests/test_reference_legacy.py)

Run profiles (runprofile.py): light = 1,000 Latin hypercube draws with their own seed, no Sobol indices, bootstrap 500,
PNG at 200 dpi with a "LIGHT RUN" footer, every output under outputs/_light/; full = 5,000 draws with the existing
seed, Sobol, bootstrap 2,000, PNG at 600 dpi under outputs/ (MODEL v3.3.1: no PDF). The deterministic results do not depend on the
profile (tests/test_profiles.py).

Order (compute, then draw): Building_factors -> projection -> Diagnostics -> Sensitivity -> MonteCarlo -> boundaries
(AESA; reads the Monte Carlo draws) -> validation -> gap_2026 -> overbuild_2026 -> scenarios -> reconciliation ->
figures_report -> pathways -> pathways_mc -> sensitivity_tables -> metrics -> results -> assumptions -> methods
(docs/LEVERS_TABLE.md, docs/METHODS_DRAFT.md) -> run_meta -> figures (python -m figures: every figure and
FIGURES.md, from the data files only) -> check_outputs -> indexes -> tests. Model scripts write CSV / JSON only.
Each step runs in its own process; its console output goes to <outputs>/logs/<step>.log.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


class StepFailed(Exception):
    pass


def interactive():
    return (hasattr(sys, 'ps1') or bool(sys.flags.interactive)
            or any(m in sys.modules for m in ('spyder_kernels', 'IPython', 'ipykernel')))


def _layout():
    import importlib
    import runprofile
    import layout
    importlib.reload(runprofile)
    return importlib.reload(layout)


TIMINGS = {}


def git_executable():
    """Find Git on PATH or in a standard GitHub Desktop installation on Windows."""
    found = shutil.which('git')
    if found:
        return found
    desktop = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'GitHubDesktop')
    try:
        candidates = [os.path.join(desktop, version, 'resources', 'app', 'git', 'cmd', 'git.exe')
                      for version in os.listdir(desktop)]
    except OSError:
        candidates = []
    candidates = [path for path in candidates if os.path.isfile(path)]
    return max(candidates, key=os.path.getmtime) if candidates else None


def git_value(*args):
    """Return a Git value when Git is available; keep the pipeline usable without it."""
    executable = git_executable()
    if not executable:
        return ''
    result = subprocess.run([executable, *args], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ''


def step(name, cmd, env):
    L = _layout()
    os.makedirs(L.LOGS, exist_ok=True)
    log_path = os.path.join(L.LOGS, f'{name}.log')
    t = time.time()
    with open(log_path, 'w') as log:
        rc = subprocess.call(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    TIMINGS[name] = round(time.time() - t, 1)
    print(f'  {name:<18} {"ok" if rc == 0 else f"FAILED (exit {rc})":<10} {TIMINGS[name]:7.1f} s')
    if rc != 0:
        raise StepFailed(f'Step "{name}" failed (exit {rc}). Read the log: {log_path}')


def tool(name):
    return os.path.join(ROOT, 'tools', f'{name}.py')


def script(name):
    return os.path.join(ROOT, f'{name}.py')


def data_hashes(data_dir):
    out = {}
    for d, _, fs in os.walk(data_dir):
        for f in fs:
            p = os.path.join(d, f)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, data_dir)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def input_hash():
    """SHA-256 over every input file under data/ (path and content), the data the model reads."""
    h = hashlib.sha256()
    base = os.path.join(ROOT, 'data')
    for d, _, fs in sorted(os.walk(base)):
        for f in sorted(fs):
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, base).encode())
            with open(p, 'rb') as fh:
                h.update(fh.read())
    return h.hexdigest()


def write_run_meta(env, mode):
    import runprofile
    L = _layout()
    git = git_value('rev-parse', 'HEAD')
    dirty = bool(git_value('status', '--porcelain', '--untracked-files=no'))
    p = runprofile.PROFILES[env['PATHWAY_PROFILE']]
    import levers
    meta = dict(profile=p['name'], mode=mode, n_draws=p['n_draws'], sobol=p['sobol'], bootstrap=p['bootstrap'],
                seeds=dict(montecarlo=p['mc_seed'], hd_bootstrap_L6=levers.HD_BOOTSTRAP_SEED,
                           hd_bootstrap_L2=levers.HD_BOOTSTRAP_SEED + 1, insight_bootstrap=p['mc_seed'] + 2101,
                           sobol=p['mc_seed'] + 2 if p['sobol'] else None),
                figures=dict(formats=list(p['formats']), dpi=p['dpi'], footer=p['footer']),
                git_hash=git, git_dirty=dirty, input_hash=input_hash(),
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%S%z'), step_seconds=dict(TIMINGS),
                reference_legacy=env.get('PATHWAY_REFERENCE_LEGACY') == '1')
    with open(L.writing(L.RUN_META), 'w') as f:
        json.dump(meta, f, indent=1)


def base_env(profile, legacy=False):
    return dict(os.environ, MPLBACKEND='Agg', PYTHONWARNINGS='ignore', PYTHONUTF8='1', PATHWAY_PROFILE=profile,
                PATHWAY_SAVE_FIGURES='0', PATHWAY_REFERENCE_LEGACY='1' if legacy else '0')


def pipeline(profile):
    env = base_env(profile)
    os.environ.update(PATHWAY_PROFILE=profile, PATHWAY_REFERENCE_LEGACY='0')
    L = _layout()
    py = sys.executable
    # a full rebuild: nothing stale survives (data, reports, every figure folder; the retired v2 folders)
    for d in (L.DATA, L.REPORTS, L.PAPER_MAIN, L.PAPER_EXTENDED, L.SUPPLEMENTARY, L.DIAGNOSTICS) + L.RETIRED:
        shutil.rmtree(d, ignore_errors=True)
    for f in (L.FIGURES_INDEX, os.path.join(L.OUT, 'INDEX.md')):
        if os.path.exists(f):
            os.remove(f)
    t0 = time.time()
    for name in ('Building_factors', 'projection', 'Diagnostics', 'Sensitivity', 'MonteCarlo', 'boundaries',
                 'validation', 'gap_2026'):
        step(name.lower(), [py, script(name)], env)
    for name, t in (('overbuild_2026', 'overbuild_2026'), ('demand_balance', 'demand_balance'),
                    ('scenarios', 'replacement_scenarios'), ('reconciliation', 'reconciliation'),
                    ('figures_report', 'figures_report')):
        step(name, [py, tool(t)], env)
    step('pathways', [py, script('pathways')], env)
    step('pathways_mc', [py, script('pathways_mc')], env)
    for t in ('sensitivity_tables', 'metrics', 'results', 'assumptions', 'methods'):
        step(t, [py, tool(t)], env)
    TIMINGS['compute_total'] = round(time.time() - t0, 1)
    write_run_meta(env, 'pipeline')
    step('figures', [py, '-m', 'figures'], env)
    step('check_outputs', [py, tool('check_outputs')], env)
    step('indexes', [py, script('indexes')], env)
    TIMINGS['total_before_tests'] = round(time.time() - t0, 1)
    write_run_meta(env, 'pipeline')
    step('tests', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests')], env)


def figures_only(profile):
    """Redraw every figure from the data files; STOP unless every file of outputs/data is byte-identical after."""
    env = base_env(profile)
    os.environ.update(PATHWAY_PROFILE=profile, PATHWAY_REFERENCE_LEGACY='0')
    L = _layout()
    before = data_hashes(L.DATA)
    for d in (L.PAPER_MAIN, L.PAPER_EXTENDED, L.SUPPLEMENTARY, L.DIAGNOSTICS):
        shutil.rmtree(d, ignore_errors=True)
    step('figures', [sys.executable, '-m', 'figures'], env)
    after = data_hashes(L.DATA)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    with open(L.writing(os.path.join(L.LOGS, 'figures_only_check.json')), 'w') as f:
        json.dump(dict(files=len(before), changed=changed), f, indent=1)
    if changed:
        raise StepFailed(f'figures-only: outputs/data changed: {changed[:10]}')
    print(f'  figures-only: {len(before)} data files byte-identical')


def reference_legacy(profile):
    """The MODEL v2.1 Reference (overbuild never absorbed): projection, Monte Carlo and AESA in outputs/_legacy/, and
    the legacy lock (tests/test_reference_legacy.py, 1e-12)."""
    env = base_env(profile, legacy=True)
    os.environ.update(PATHWAY_PROFILE=profile, PATHWAY_REFERENCE_LEGACY='1')
    py = sys.executable
    for name in ('Building_factors', 'projection', 'MonteCarlo', 'boundaries'):
        step(name.lower(), [py, script(name)], env)
    step('legacy_lock', [py, '-m', 'pytest', '-q', os.path.join(ROOT, 'tests', 'test_reference_legacy.py')], env)
    write_run_meta(env, 'reference_legacy')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    profile = 'light'
    if '--profile' in argv:
        profile = argv[argv.index('--profile') + 1]
    if profile not in ('light', 'full'):
        raise SystemExit(f'--profile {profile!r}: light | full')
    print(f'run_all ({profile} profile):')
    try:
        if '--figures-only' in argv:
            figures_only(profile)
        elif '--reference-legacy' in argv:
            reference_legacy(profile)
        else:
            pipeline(profile)
    except StepFailed as e:
        print(f'\n{e}')
        if interactive():
            return False
        sys.exit(1)
    L = _layout()
    print(f'\nDone. Figures: {L.FIGURES_INDEX}; run metadata: {L.RUN_META}')
    return True


if __name__ == '__main__':
    main()
