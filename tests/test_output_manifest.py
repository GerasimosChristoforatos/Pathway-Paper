"""Byte reproducibility of the release outputs (MODEL v1.1.0).

tests/output_manifest_model_v1_1.json holds the SHA-256 of every file the release run wrote
under outputs/ (tools/output_manifest.py; console logs excluded). Run after
`python run_all.py` (or `--pathways-only`, which rewrites the pathway outputs), this test
checks that the run reproduced every one of them byte for byte and wrote no other file.

Byte identity is expected only in the environment that wrote the manifest (its 'environment'
block: Python, numpy, pandas, scipy, matplotlib, FreeType, machine): floating-point results and
font rasterisation may differ in the last bits elsewhere. In any other environment the test is
skipped with the reason; the numerical lock (tests/test_regression_model_v1.py, every number to
1e-12 relative) applies everywhere. Quick runs write different Monte Carlo outputs and are
never compared.
"""
import json
import os
import sys

import pytest

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import output_manifest as OM  # noqa: E402

MANIFEST = OM.TARGET
pytestmark = [
    pytest.mark.skipif(not os.path.exists(MANIFEST), reason='no release manifest yet (tools/output_manifest.py)'),
    pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: outputs differ by design'),
]


def _manifest():
    with open(MANIFEST) as f:
        return json.load(f)


def test_environment_matches_the_manifest():
    """Not an assertion on the model: it records why the byte test below is skipped elsewhere."""
    want, have = _manifest()['meta']['environment'], OM.environment()
    diff = {k: (want[k], have.get(k)) for k in want if want[k] != have.get(k)}
    if diff:
        pytest.skip(f'environment differs from the release run {diff}: byte identity not expected')


def test_every_output_is_reproduced_byte_for_byte():
    man = _manifest()
    want, have = man['meta']['environment'], OM.environment()
    if want != have:
        pytest.skip('environment differs from the release run: byte identity not expected')
    files = OM.output_files()
    missing = sorted(set(man['files']) - set(files))
    extra = sorted(set(files) - set(man['files']))
    changed = sorted(f for f in set(files) & set(man['files'])
                     if OM.sha256(os.path.join(OM.layout.OUT, f)) != man['files'][f])
    assert not (missing or extra or changed), (f'missing {missing[:20]}; not in the manifest {extra[:20]}; '
                                               f'bytes differ {changed[:40]} ({len(changed)} files)')
