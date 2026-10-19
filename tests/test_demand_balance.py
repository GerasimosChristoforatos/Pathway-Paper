import json
import os

import numpy as np
import pandas as pd
import pytest

import layout
from tools.demand_balance import historical_market_balance, projection_components


def test_broad_projection_groups_reconcile_to_floor_area(B):
    assert int(B["lag_months"]) == 17
    comparison, groups, derived = projection_components(B, 17)

    reconstructed = (
        groups["population_growth"]
        + groups["household_size_change"]
        + groups["net_replacement"]
        + groups["other"]
        + groups["market_excess"]
        + groups["overbuild_absorbed"]
    )
    np.testing.assert_allclose(reconstructed, derived["total"], rtol=1e-9, atol=1e-8)
    assert set(comparison["category"]) >= {
        "population_growth", "household_size_change", "net_replacement",
        "other", "market_excess", "overbuild_absorbed", "total_built"
    }


def test_historical_balance_is_not_mislabelled_as_overbuild():
    history = pd.read_csv(layout.data("baseline/bands_history.csv"))
    classified = historical_market_balance(history)

    for period, group in classified.groupby("period"):
        broad = group[group["category"].isin(
            ["population_growth", "household_size_change", "net_replacement", "other"]
        )]["floor_area_Mm2_per_year"].sum()
        total = float(group.loc[group["category"] == "total_built",
                                "floor_area_Mm2_per_year"].iloc[0])
        assert broad == pytest.approx(total, rel=1e-9, abs=1e-8)
        assert group.loc[group["category"] == "market_excess",
                         "floor_area_Mm2_per_year"].isna().all()
        assert group.loc[group["category"] == "overbuild_absorbed",
                         "floor_area_Mm2_per_year"].isna().all()

    bridge = classified[classified["period"] == "2023-2025"]
    assert bridge["data_basis"].str.contains("Consent-derived").all()


def test_completed_lag_comparison_was_generated_and_is_controlled():
    path = layout.data("diagnostics/lag_comparison_summary.json")
    if not os.path.exists(path):
        pytest.skip("Run the demand_balance step in run_all.py first.")
    with open(path) as f:
        summary = json.load(f)

    assert summary["same_population_path"]
    assert summary["same_household_size_path"]
    assert summary["same_household_path"]
    assert summary["lag_0"]["lag_months"] == 0
    assert summary["lag_17"]["lag_months"] == 17
    assert summary["lag_17"]["pipeline_years"] == [2026, 2027]
    assert len(summary["lag_17"]["observed_cohorts"]) == 2
    assert len(summary["lag_0"]["observed_cohorts"]) == 1
