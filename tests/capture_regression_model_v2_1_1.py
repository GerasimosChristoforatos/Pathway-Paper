"""MODEL v2.1.1: record every key of the pathway domain that changed since the MODEL v2.1.0 lock
(tests/regression_model_v2_1.json) in tests/regression_model_v2_1_1.json, with its old and new value or hash.

    python tests/capture_regression_model_v2_1_1.py "<label>"     # after the full run of the release

MODEL v2.1.1 changes the theoretical limit only (TL gradual reoccupation): if any changed, added or removed key
is not a TL key (regression_v2_1.is_tl_key), nothing is written and the script stops (exit 1).
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
    base = R21.load_base_lock()
    cur = R21.compact_values()
    changed = {k: dict(old=base[k], new=cur[k]) for k in base if k in cur and not R21.same_compact(k, base[k], cur[k])}
    added = {k: cur[k] for k in cur if k not in base}
    removed = {k: base[k] for k in base if k not in cur}
    non_tl = [k for k in list(changed) + list(added) + list(removed) if not R21.is_tl_key(k)]
    if non_tl:
        print('\n'.join(map(str, non_tl[:30])))
        raise SystemExit(f'STOP: {len(non_tl)} keys outside the theoretical limit changed (nothing written).')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R21.ROOT, text=True).strip()
    key = lambda k: json.dumps(list(k))
    out = dict(meta=dict(
        purpose='MODEL v2.1.1: the keys of the pathway domain that changed since tests/regression_model_v2_1.json '
                '(TL gradual reoccupation; theoretical limit only)', label=label, code_commit=commit,
        n_changed=len(changed), n_added=len(added), n_removed=len(removed),
        files=sorted({k[0] for k in list(changed) + list(added) + list(removed)}),
        captured_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')),
        changed={key(k): v for k, v in sorted(changed.items(), key=lambda kv: key(kv[0]))},
        added={key(k): v for k, v in sorted(added.items(), key=lambda kv: key(kv[0]))},
        removed={key(k): v for k, v in sorted(removed.items(), key=lambda kv: key(kv[0]))})
    with open(R21.CHANGES_FILE, 'w') as f:
        json.dump(out, f, indent=0)
        f.write('\n')
    print(f'regression v2.1.1: {len(changed)} changed, {len(added)} added, {len(removed)} removed (all TL) -> '
          f'{os.path.relpath(R21.CHANGES_FILE, R21.ROOT)}')


if __name__ == '__main__':
    main()
