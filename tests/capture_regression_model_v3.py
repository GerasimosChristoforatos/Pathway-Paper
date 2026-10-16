"""Capture the MODEL v3.3.1 regression lock (tests/regression_model_v3_3_1.json) from the outputs of a light and (if present) a full run:
    python tests/capture_regression_model_v3.py
The deterministic hashes are taken from the light outputs and must equal the full ones (else it stops)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regression_v3 as R  # noqa: E402

DIRS = {'light': os.path.join(R.ROOT, 'outputs', '_light', 'data'), 'full': os.path.join(R.ROOT, 'outputs', 'data')}

if __name__ == '__main__':
    det = {rel: R.digest(DIRS['light'], rel) for rel in R.DETERMINISTIC_FILES}
    mc = {}
    for prof, d in DIRS.items():
        if all(os.path.exists(os.path.join(d, rel)) for rel in R.MC_FILES):
            mc[prof] = {rel: R.digest(d, rel) for rel in R.MC_FILES}
            if prof == 'full':
                diff = [rel for rel in R.DETERMINISTIC_FILES if R.digest(d, rel) != det[rel]]
                if diff:
                    raise SystemExit(f'STOP: deterministic files differ between the light and full profiles: {diff}')
    head = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    with open(R.LOCK, 'w') as f:
        json.dump(dict(meta=dict(commit=head, profiles=sorted(mc)), deterministic=det, montecarlo=mc), f, indent=1)
    print(f'{len(det)} deterministic files, Monte Carlo profiles {sorted(mc)} -> {R.LOCK}')
