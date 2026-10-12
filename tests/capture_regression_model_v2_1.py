"""MODEL v2.1.0: lock every number of the pathway domain (tests/regression_v2_1.py) of the release run.

    python tests/capture_regression_model_v2_1.py "<label>"     # after the full run of the release

Writes tests/regression_model_v2_1.json (compact form, tests/regression_v2_1.py). Run once per release of the
pathway layer: the v1 and v2 locks keep
every number outside the domain unchanged to 1e-12, and tests/test_regression_model_v2_1.py then requires every
locked domain value to be reproduced and no domain value to appear unlocked.
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regression_v2_1 as R21  # noqa: E402


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'unlabelled'
    hashed = R21.hashed_entries()
    vals = {k: v for k, v in R21.domain_values().items() if k[0] not in R21.HASHED_FILES}
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R21.ROOT, text=True).strip()
    out = dict(meta=dict(
        purpose='MODEL v2.1.0: every number of the pathway domain (tests/regression_v2_1.py), which the lever, '
                'pathway and theoretical-limit rebuild changes by design; compact form since MODEL v2.1.1 (the large '
                'files as SHA-256 per row group and column, per draw for the Monte Carlo, with summary statistics)',
        hashed_files=list(R21.HASHED_FILES),
        tolerance='relative 1e-12; NaN equals NaN; booleans and integers exact',
        keys='JSON list: [file, row key or null, column] for CSV; [file, path] for JSON',
        label=label, code_commit=commit, n_values=len(vals), files=sorted({k[0] for k in vals} | set(hashed)),
        captured_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')),
        values={json.dumps(list(k)): v for k, v in sorted(vals.items(), key=lambda kv: json.dumps(list(kv[0])))},
        hashed=hashed)
    with open(R21.LOCK_FILE, 'w') as f:
        json.dump(out, f, indent=0)
        f.write('\n')
    print(f'regression v2.1: {len(vals)} values and {len(hashed)} hashed files in {len(out["meta"]["files"])} files -> '
          f'{os.path.relpath(R21.LOCK_FILE, R21.ROOT)}')


if __name__ == '__main__':
    main()
