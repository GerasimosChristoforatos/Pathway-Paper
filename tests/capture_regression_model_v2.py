"""MODEL v2.0.0: lock every number of outputs/data/ that the v1 lock does not hold
(tests/regression_model_v2_additions.json; tests/regression_v2.py, tests/test_regression_model_v2.py).

    python tests/capture_regression_model_v2.py "<label>"     # after a full run

Append-only: values already in the file must be reproduced to 1e-12 (otherwise nothing is written,
exit 1), and every value of outputs/data/ that neither the v1 lock nor the file holds is added under
<label> (the step and commit that produced it). An addition is a NEW value, never a change: the v1
lock (tests/test_regression_model_v1.py) still requires every earlier value unchanged.
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regression_v2 as R  # noqa: E402


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'unlabelled'
    old, meta = R.load_additions()
    unc = R.uncovered()
    stale = [k for k in old if k not in unc]
    changed = [k for k in old if k in unc and not R.same(old[k], unc[k])]
    if stale or changed:
        print(f'gone: {stale[:10]}\nchanged: {[(k, old[k], unc[k]) for k in changed[:10]]}')
        raise SystemExit(f'{len(stale)} locked additions are gone and {len(changed)} changed: STOP (nothing written).')
    new = {k: v for k, v in unc.items() if k not in old}
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip()
    batches = (meta or {}).get('batches', [])
    if new:
        files = sorted({k[0] for k in new})
        batches.append(dict(label=label, code_commit=commit, n_values=len(new), files=files,
                            captured_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')))
    allv = {**old, **new}
    out = dict(meta=dict(
        purpose='MODEL v2.0.0: every number of outputs/data/ that tests/regression_model_v1.json (with '
                'regression_model_v1_1.json) does not hold; additions, not changes',
        tolerance='relative 1e-12; NaN equals NaN; booleans and integers exact',
        keys='JSON list: [file, row key (JSON of the identifying cells) or null for a whole column, column] '
             'for CSV; [file, path] for JSON',
        n_values=len(allv), batches=batches),
        values={R.keystr(k): v for k, v in sorted(allv.items(), key=lambda kv: R.keystr(kv[0]))})
    with open(R.ADDITIONS_FILE, 'w') as f:
        json.dump(out, f, indent=0)
        f.write('\n')
    print(f'regression v2 additions: {len(new)} new, {len(allv)} in total -> {os.path.relpath(R.ADDITIONS_FILE, R.ROOT)}')


if __name__ == '__main__':
    main()
