"""MODEL v3.2.0 regression lock: every deterministic data file reproduced byte for byte (JSON without its profile
fields), and the Monte Carlo draw files of the active profile (tests/regression_v3.py)."""
import json
import os

import pytest

import layout
import runprofile
import regression_v3 as R

LOCK = json.load(open(R.LOCK)) if os.path.exists(R.LOCK) else None


@pytest.mark.skipif(LOCK is None, reason='tests/regression_model_v3_3.json not captured yet')
@pytest.mark.parametrize('rel', R.DETERMINISTIC_FILES)
def test_deterministic_file_locked(rel):
    assert R.digest(layout.DATA, rel) == LOCK['deterministic'][rel], rel


@pytest.mark.skipif(LOCK is None, reason='tests/regression_model_v3_3.json not captured yet')
@pytest.mark.parametrize('rel', R.MC_FILES)
def test_montecarlo_hash_locked(rel):
    prof = runprofile.name()
    if prof not in LOCK['montecarlo']:
        pytest.skip(f'no Monte Carlo lock for the {prof} profile')
    assert R.digest(layout.DATA, rel) == LOCK['montecarlo'][prof][rel], rel
