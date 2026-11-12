"""The age-standardised household size (household_headship.py): the 2023-rate path reproduces the Stats NZ Medium A
household size within 0.025 at every knot (largest deviation 0.022, 2033: the four broad age groups); the more-shared alternative is never below
it; the calibration reproduces the 2023 households exactly."""
import numpy as np
import pytest


@pytest.mark.parametrize('variant', ['Low', 'Medium', 'High'])
def test_2023_rates_reproduce_statsnz_propensity_a(variant):
    import household_headship as H
    t = H.paths(variant)
    assert np.all(np.abs(t['S_2023'] - t['S_statsnz_A']) < H.CHECK_TOL), t[['S_2023', 'S_statsnz_A']]
    assert np.all(t['S_min_2023_or_B'] >= t['S_2023'] - 1e-12)
    assert t.loc[2023, 'ratio_min_2023_or_B'] == pytest.approx(1.0, abs=1e-12)


def test_calibration_reproduces_2023_households():
    import household_headship as H
    p, h = H.load()
    f, g = H.calibration(p, h)
    P = H._people(p, 'Medium A', 2023)
    hh = float((H.headship(P, f, g) * P[H.LAT['tot']]).sum())
    assert hh == pytest.approx(H._households(h, 'Medium A', 2023, 'Total households'), rel=2e-3)
