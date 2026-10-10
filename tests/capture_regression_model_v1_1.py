"""MODEL v1.1.0: the values of the regression lock that the adoption-window rule changes
(tests/regression_model_v1_1.json).

    python tests/capture_regression_model_v1_1.py      # after the v1.1.0 run

MODEL v1.1.0 applies one rule to every adoption window 2026 -> E (levers.adoption_window:
midpoint 2026 + W/2, k = ln(81) / (2W/3)). For E = 2035 (adopted) it is the earlier path bit for
bit; the sensitivities 'full roll-out by 2030' and 'by 2045' change. This script compares the
current outputs with every value of tests/regression_model_v1.json (the ee37ef1 capture and the
model-v1.0.0 additions) through the same map and comparison as tests/test_regression_model_v1.py,
and writes every value that differs beyond 1e-12 relative, with its old and new value. It refuses
to write (exit 1) if any differing value is not produced by the two adoption sensitivities:
a row of the pathway outputs whose adoption path is by2030 / by2045 (ramp2030 / ramp2045 at
ee37ef1), or a key of levers.json that holds those paths (ramp/sensitivity..., ramp/sensitivities...,
ramp/w_sensitivity...). tests/test_regression_model_v1.py then requires the listed values to
equal their new value and every other value its captured one.
"""
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import test_regression_model_v1 as T  # noqa: E402

TARGET = os.path.join(ROOT, 'tests', 'regression_model_v1_1.json')
SENSITIVITY_TOKENS = ('ramp2030', 'ramp2045', 'by2030', 'by2045')
LEVERS_PATHS = ('ramp/sensitivit', 'ramp/w_sensitivity', 'adoption/sensitivit', 'adoption/w_sensitivity')


def key_of(kind, item):
    """(key, old, new) of one item of T._check_csv / T._check_json's 'bad' list."""
    if kind == 'json':
        p, e, a = item
        return p, e, a
    rk, c, e, a = item
    return json.dumps([json.loads(rk), c]), e, a


def allowed(old_file, kind, key):
    if kind == 'json':
        return old_file.endswith('levers.json') and key.startswith(LEVERS_PATHS)
    return any(t in key for t in SENSITIVITY_TOKENS)


def collect():
    changed, refused = {}, []
    sources = [('files', f, e) for f, e in T.CAP['files'].items()]
    sources += [('additions', f, e) for f, e in T.CAP.get('additions', {}).get('files', {}).items()]
    for section, f, entry in sources:
        if entry['kind'] == 'csv_by_row_number':
            kind = 'csv_by_row_number'
        else:
            kind = 'json' if entry['kind'] == 'json' else 'csv'
        saved = T.LEGACY
        if section == 'additions':
            T.LEGACY = T._Release()
        try:
            if section == 'files' and T.LEGACY.removed(f):
                continue
            bad, missing = (T._check_json if kind == 'json' else T._check_csv)(f, entry)
        finally:
            T.LEGACY = saved
        if missing:
            refused.append((section, f, 'missing', missing[:5]))
        for item in bad:
            if kind == 'csv_by_row_number':
                refused.append((section, f, 'row-number file', item))
                continue
            k, old, new = key_of(kind, item)
            if not allowed(f, kind, k):
                refused.append((section, f, k, old, new))
                continue
            changed.setdefault(f'{section}:{f}', []).append(dict(key=k, old=old, new=T._py(new)))
    return changed, refused


def main():
    changed, refused = collect()
    if refused:
        for r in refused[:40]:
            print('NOT an adoption-sensitivity value:', r)
        raise SystemExit(f'{len(refused)} values outside the adoption sensitivities changed: STOP (nothing written).')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    n = sum(len(v) for v in changed.values())
    out = dict(meta=dict(
        purpose='MODEL v1.1.0: values of tests/regression_model_v1.json changed by the adoption-window rule '
                '(full roll-out by 2030 and by 2045 only); every other value unchanged to 1e-12',
        rule='levers.adoption_window: midpoint 2026 + W/2, k = ln(81) / (2W/3), W = E - 2026; adopted E = 2035 '
             'unchanged bit for bit',
        code_commit=commit, captured_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        n_values=n, keys='CSV: [captured row key, column]; JSON: captured path; sections "files" (ee37ef1) and '
                         '"additions" (model-v1.0.0)'),
        changed=changed)
    with open(TARGET, 'w') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(f'regression v1.1: {n} changed values in {len(changed)} files -> {os.path.relpath(TARGET, ROOT)}')
    for f, v in changed.items():
        print(f'  {f}: {len(v)}')


if __name__ == '__main__':
    main()
