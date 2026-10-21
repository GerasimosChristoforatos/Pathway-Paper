"""MODEL v4.2 Part A diagnostic switches (projection.HH_BRIDGE, START_MODE, HH_SIZE_PATH 'statsnz_2018' /
'statsnz_2023'); the defaults stay MODEL v4.0.0."""
import numpy as np
import pandas as pd
import pytest

from conftest import run_boss


def test_defaults_unchanged(B):
    import projection
    assert (projection.HH_BRIDGE, projection.START_MODE, projection.HH_SIZE_PATH) == ('dhe', 'observed', 'statsnz')
    B18 = run_boss(HH_SIZE_PATH='statsnz_2018')
    assert np.array_equal(B18['engine_out']['50th']['carbon'], B['engine_out']['50th']['carbon'])


def test_erp_bridge_households_are_erp_over_the_s_path():
    import projection
    B = run_boss(HH_BRIDGE='erp_S')
    yb = [2024, 2025]
    S = projection.household_size_path(B['hist_S'], yb)        # anchored on 2023, unchanged by the bridge
    assert np.allclose(B['hist_hh'].loc[yb].values, B['hist_pop'].loc[yb].values / S, rtol=1e-12)
    assert np.isclose(B['hist_S'].loc[2023], B['hist_pop'].loc[2023] / B['hist_hh'].loc[2023], rtol=1e-15)


def test_projection_start_mode_has_no_observed_year():
    B = run_boss(START_MODE='projection')
    E = B['engine_out']['50th']
    assert B['pipe'] is None and B['pop_nowcast'] is None and B['_join_mode'] == 'none'
    assert not np.any(np.asarray(E['join'], float)) and B['lag_months'] == 17


def test_statsnz_2023_loader_stub(tmp_path):
    import projection
    rows = [(y, v, 5.2e6 + 4e4 * (y - 2023) * k, 2.0e6 + 2.2e4 * (y - 2023) * k)
            for y in (2023, 2028, 2033, 2038, 2043, 2048) for v, k in (('Medium', 1.0), ('Low', 0.8), ('High', 1.2))]
    f = tmp_path / 'hh2023.csv'
    pd.DataFrame(rows, columns=['Year', 'Variant', 'Population', 'Households']).to_csv(f, index=False)
    sh = projection.statsnz_2023_shape(str(f), 'Medium')
    for y, v, p, h in rows:
        if v == 'Medium':
            assert sh.loc[y] == pytest.approx(p / h, rel=1e-12)
    assert sh.loc[2050] == pytest.approx(sh.loc[2048], rel=1e-15)          # held after the last knot
    with pytest.raises(ValueError):
        projection.statsnz_2023_shape(None, 'Medium')
    B = run_boss(HH_SIZE_PATH='statsnz_2023', FILE_HOUSEHOLDS_PROJ_2023=str(f))
    S = B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th']
    anchor = B['hist_S'].loc[2023]
    assert S[-1] == pytest.approx(anchor * sh.loc[2050] / sh.loc[2023], rel=1e-12)
