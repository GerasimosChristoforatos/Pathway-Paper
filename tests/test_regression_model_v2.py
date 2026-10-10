"""Regression lock of MODEL v2.0.0: every number of outputs/data/ is locked.

tests/test_regression_model_v1.py keeps every value captured at ee37ef1 (and the model-v1.0.0
additions) to 1e-12, with the MODEL v1.1.0 changes of the adoption-path sensitivities. Here:
every number of every data file is either one of those values or a listed addition of
tests/regression_model_v2_additions.json (tests/capture_regression_model_v2.py, append-only),
which must be reproduced to 1e-12. A number neither lock holds fails the test: nothing can
change or appear unrecorded. Removing a figure never removes its data.
"""
import os

import pytest

import regression_v2 as R

pytestmark = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: Monte Carlo outputs differ')
ADD, META = R.load_additions()


@pytest.fixture(scope='module')
def unc():
    return R.uncovered()


def test_every_number_of_the_data_files_is_locked(unc):
    unlisted = sorted(set(unc) - set(ADD), key=R.keystr)
    assert not unlisted, f'{len(unlisted)} numbers locked by neither the v1 lock nor the v2 additions, e.g. {unlisted[:5]}'


def test_every_v2_addition_is_reproduced(unc):
    gone = [k for k in ADD if k not in unc]
    bad = [(k, ADD[k], unc[k]) for k in ADD if k in unc and not R.same(ADD[k], unc[k])]
    assert not gone, f'{len(gone)} listed additions are no longer in the data files (or are now v1-locked), e.g. {gone[:5]}'
    assert not bad, f'{len(bad)} additions differ beyond 1e-12, e.g. {bad[:5]}'


def test_additions_meta():
    assert META and META['n_values'] == len(ADD) and sum(b['n_values'] for b in META['batches']) == len(ADD)
