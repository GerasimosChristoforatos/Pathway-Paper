"""Regression lock of MODEL v2.1.0 (tests/regression_v2_1.py).

1. Every number of the pathway domain is locked: the set of domain keys in outputs/data/ equals the set in
   tests/regression_model_v2_1.json, and every value is reproduced to 1e-12.
2. Only the pathway domain changed: the v1 and v2 locks (tests/test_regression_model_v1.py,
   tests/test_regression_model_v2.py) still hold every other number to 1e-12; here, the domain is checked to be
   exactly the documented one (pathway data, the P5 sensitivity table and the non-Reference rows of the
   replacement variants), and no Reference row is in it.
"""
import json
import os

import pytest

import regression_v2 as R
import regression_v2_1 as R21

pytestmark = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: Monte Carlo outputs differ')
LOCK, META = R21.load_lock()


@pytest.fixture(scope='module')
def dom():
    return R21.domain_values()


def test_every_domain_number_is_locked_and_reproduced(dom):
    assert LOCK, 'tests/regression_model_v2_1.json missing (tests/capture_regression_model_v2_1.py)'
    new = sorted(set(dom) - set(LOCK), key=R.keystr)
    gone = sorted(set(LOCK) - set(dom), key=R.keystr)
    bad = [(k, LOCK[k], dom[k]) for k in LOCK if k in dom and not R.same(LOCK[k], dom[k])]
    assert not new, f'{len(new)} domain values not locked, e.g. {new[:5]}'
    assert not gone, f'{len(gone)} locked domain values absent, e.g. {gone[:5]}'
    assert not bad, f'{len(bad)} domain values differ beyond 1e-12, e.g. {bad[:5]}'


def test_the_domain_is_the_documented_one(dom):
    files = {k[0] for k in dom}
    assert all(f.startswith('data/pathways/') or f in ('data/sensitivity/p5_carbon.csv',
                                                       'data/sensitivity/replacement_variants.csv') for f in files)
    rv = [k for k in dom if k[0] == 'data/sensitivity/replacement_variants.csv']
    assert rv and all('Reference' not in json.loads(k[1]) for k in rv)
    for k in R.values('data/sensitivity/replacement_variants.csv'):
        if 'Reference' in json.loads(k[1]):
            assert not R21.in_domain(k)


def test_lock_meta():
    assert META['n_values'] == len(LOCK) and META['files'] == sorted({k[0] for k in LOCK})
