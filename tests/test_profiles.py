"""Run profiles (MODEL v3.0.0): the deterministic results are identical in the light and full profiles.

  * in process: the lever parameters resolved under both profiles agree in every field except the bootstrap
    intervals (whose replicate count is the profile's);
  * on the outputs: when both outputs/_light/data and outputs/data exist, every deterministic data file is identical
    (tests/regression_v3.py: bytes, JSON without the profile fields)."""
import os

import pytest

import regression_v3 as R

LIGHT = os.path.join(R.ROOT, 'outputs', '_light', 'data')
FULL = os.path.join(R.ROOT, 'outputs', 'data')


def test_profile_settings():
    import runprofile
    L, F = runprofile.PROFILES['light'], runprofile.PROFILES['full']
    assert (L['n_draws'], L['sobol'], L['bootstrap'], L['dpi'], L['formats']) == (1000, False, 500, 200, ('png',))
    assert (F['n_draws'], F['sobol'], F['bootstrap'], F['dpi'], F['formats']) == (5000, True, 2000, 600, ('pdf', 'png'))
    assert F['mc_seed'] == 20260924 and L['mc_seed'] != F['mc_seed'] and L['out_subdir'] == '_light'


def test_lever_parameters_do_not_depend_on_the_profile():
    import pathways as PW
    import levers as LV
    import validation
    import Building_factors as BF
    import pandas as pd
    B = PW.boss_state(PW.REFERENCE)
    args = (B, PW.load_factors_building(), BF.load_characteristics(),
            pd.read_csv(validation.projection.FILE_FACTORS_TYPOLOGY), validation.projection,
            PW.household_size_variants(B))
    a, b = LV.resolve(*args, 500), LV.resolve(*args, 2000)
    assert R._strip(a) == R._strip(b)


@pytest.mark.skipif(not (os.path.isdir(LIGHT) and os.path.isdir(FULL)
                         and all(os.path.exists(os.path.join(FULL, r)) for r in R.DETERMINISTIC_FILES)),
                    reason='both the light and the full outputs are needed')
@pytest.mark.parametrize('rel', R.DETERMINISTIC_FILES)
def test_deterministic_outputs_identical_across_profiles(rel):
    assert R.digest(LIGHT, rel) == R.digest(FULL, rel), rel
