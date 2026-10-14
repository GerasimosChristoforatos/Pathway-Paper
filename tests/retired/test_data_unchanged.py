"""MODEL v2.1.2 is a figures-only release: every file of outputs/data/ must stay byte-identical to model-v2.1.1
(tests/data_snapshot_model_v2_1_1.json, SHA-256 of each file, frozen before any change). run_all.py --figures-only
runs this test after the model scripts that draw figures and again at the end, and stops if a file changed.
A later release that changes the model re-freezes the snapshot (or retires this test) on purpose.
"""
import hashlib
import json
import os

from conftest import ROOT

SNAPSHOT = os.path.join(ROOT, 'tests', 'data_snapshot_model_v2_1_1.json')
DATA = os.path.join(ROOT, 'outputs', 'data')


def _sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_every_data_file_is_byte_identical_to_model_v2_1_1():
    snap = json.load(open(SNAPSHOT))['files']
    now = {os.path.relpath(os.path.join(d, f), DATA): _sha(os.path.join(d, f))
           for d, _, fs in os.walk(DATA) for f in fs}
    missing = sorted(set(snap) - set(now))
    extra = sorted(set(now) - set(snap))
    changed = sorted(k for k in set(snap) & set(now) if snap[k] != now[k])
    assert not (missing or extra or changed), f'missing {missing}; new {extra}; changed {changed}'
    assert len(snap) == 88
