"""L1 at TL from census headship (household_headship.py): the calibration gates, the common-basis check, the TL
rates never above any census rate or the propensity-B rate, the ratio path, the one-person identity, and the POPPR 2023
rates against the Stats NZ Medium A household size (within 0.025 at every knot: the four broad age groups)."""
import numpy as np
import pytest


@pytest.mark.parametrize('variant', ['Low', 'Medium', 'High'])
def test_projection_rates_reproduce_statsnz_propensity_a(variant):
    import household_headship as H
    t = H.projection_check(variant)
    assert np.all(np.abs(t['S_2023'] - t['S_statsnz_A']) < H.CHECK_TOL), t


def test_calibration_gates_and_one_person_identity():
    import household_headship as H
    cal = H.census_calibration()
    f13 = cal[2013]['f']
    for c, v in cal.items():
        assert 0.0 < v['f'] <= 1.0 and 0.0 < v['g'] < 1.0 and abs(v['f'] / f13 - 1.0) <= H.F_BAND, (c, v)
        assert abs(v['one_person_ratio'] - 1.0) <= H.ONE_PERSON_TOL, c
    P, T = H.census_people(), H.census_targets()
    for c in H.CENSUSES:            # the calibration reproduces each census's own stated households
        hh = float((H.census_headship(P[c], cal[c]['f'], cal[c]['g']) * P[c]['stated']).sum())
        assert hh == pytest.approx(T.loc[c, 'stated'], rel=1e-3), c


def test_common_basis_within_tolerance():
    import household_headship as H
    n = H.common_basis_check()['normalised']
    assert (n.loc[['15-39', '40-64', '65+'], 'diff'].abs() <= H.COMMON_BASIS_TOL).all()


@pytest.mark.parametrize('variant', ['Low', 'Medium', 'High'])
def test_tl_rates_and_ratio(variant):
    import household_headship as H
    R, src, hb = H.tl_rates(variant)
    cmin = H.census_rates().min(axis=1)
    for y in R.columns:
        assert (R[y] <= cmin + 1e-15).all() and (R[y] <= hb[y] + 1e-15).all()
    t = H.tl_paths(variant)
    assert (t['ratio'] >= 1.0 - 1e-12).all() and (t['S_TL'] >= t['S_2023'] - 1e-12).all()
    r = H.tl_ratio_path(np.arange(2020, 2051), variant)
    assert (r[:4] == 1.0).all() and r[-1] == pytest.approx(t['ratio'].iloc[-1], rel=1e-12)   # 1 up to 2023
