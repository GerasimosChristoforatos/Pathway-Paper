"""Baseline lock (PATHWAYS v2): every file tracked under outputs/ at tag baseline-PB_v3.1,
outside outputs/pathways/, is byte-identical to the tag (SHA-256 in
tests/baseline_manifest.json, built from the tag's blobs). The baseline is frozen: the
pathway layer reads it and never rewrites it.

A quick run (run_all.py --quick) rewrites the Monte Carlo outputs with fewer draws by
design, so the lock is skipped there (PATHWAY_QUICK=1); run_all.py --pathways-only and
the full run assert it."""
import hashlib
import json
import os

import pytest

from conftest import ROOT

MANIFEST = json.load(open(os.path.join(ROOT, 'tests', 'baseline_manifest.json')))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def test_manifest_scope():
    files = MANIFEST['files']
    assert MANIFEST['tag'] == 'baseline-PB_v3.1' and len(files) == 65
    assert not any(p.startswith('outputs/pathways/') for p in files)


@pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: Monte Carlo outputs differ by design')
def test_baseline_outputs_match_the_tag():
    missing = [p for p in MANIFEST['files'] if not os.path.exists(os.path.join(ROOT, p))]
    changed = [p for p, h in MANIFEST['files'].items() if p not in missing and sha256(os.path.join(ROOT, p)) != h]
    assert not missing and not changed, dict(missing=missing, changed=changed)
