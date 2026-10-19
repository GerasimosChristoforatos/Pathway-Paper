"""Separate market-balance and completion-lag diagnostics for MODEL v4.1.0.

This module does not alter the demand bands used by the pathway model. It
creates a second, coarser interpretation layer and a controlled comparison
between zero- and 17-month consent-to-completion timing.

Run after validation.py has written baseline/bands_history.csv:
    python tools/demand_balance.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

# Scripts in tools/ are launched as separate processes by run_all.py. Add the
# repository root explicitly so root-level modules (layout, projection, etc.)
# resolve the same way they do in sibling tools.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import layout  # noqa: E402
import naming as N  # noqa: E402
import projection  # noqa: E402
import validation  # noqa: E402


BROAD_GROUPS = {
    "population_growth": ("growth",),
    "household_size_change": ("smaller_households",),
    "net_replacement": ("replacement", "redevelopment", "unconsented"),
    "other": ("extra_space", "vacancy", "vacancy_released", "released_tl", "surplus_vacant"),
    "market_excess": ("overbuild_2026",),
    "overbuild_absorbed": ("overbuild_absorbed",),
}
GROUP_LABELS = {
    "population_growth": "Population growth",
    "household_size_change": "Household-size change",
    "net_replacement": "Net replacement",
    "other": "Other demand / balance",
    "market_excess": "Gross market excess",
    "overbuild_absorbed": "Overbuild absorbed",
    "underlying_requirement": "Underlying requirement",
    "net_market_effect": "Net market-excess effect",
    "total_built": "Total floor area built",
}


def projection_components(B, lag_months):
    """Aggregate the annual floor-area bands without changing their accounting.

    The six broad components must reproduce the Reference floor area exactly:
    underlying requirement + gross market excess + payback.
    """
    years = np.asarray(B["forecast_years"], dtype=int)[1:]
    bands = B["fig_bands"]["gfa"][0]
    raw = {band_id: np.asarray(values, dtype=float)
           for _label, values, band_id in bands}
    required = {band for group in BROAD_GROUPS.values() for band in group}
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"Projection is missing demand-band IDs: {missing}")

    grouped = {
        category: sum((raw[band] for band in band_ids), start=np.zeros(len(years)))
        for category, band_ids in BROAD_GROUPS.items()
    }
    total = np.asarray(B["results"]["50th"]["total"][1:], dtype=float) / 1e6
    requirement = sum(
        (grouped[key] for key in ("population_growth", "household_size_change", "net_replacement", "other")),
        start=np.zeros(len(years))
    )
    net_market = grouped["market_excess"] + grouped["overbuild_absorbed"]
    reconstructed = requirement + net_market
    if not np.allclose(reconstructed, total, rtol=1e-9, atol=1e-8):
        error = float(np.max(np.abs(reconstructed - total)))
        raise RuntimeError(
            f"L={lag_months}: broad demand groups do not reconcile to total GFA; "
            f"maximum difference {error:.6g} Mm2"
        )

    annual_rows = []
    for category, values in grouped.items():
        for year, value in zip(years, values):
            annual_rows.append(dict(
                lag_months=int(lag_months),
                timing="consent-timed proxy" if lag_months == 0 else "completion-timed",
                year=int(year), category=category, floor_area_Mm2=float(value)
            ))
    derived = {
        "underlying_requirement": requirement,
        "net_market_effect": net_market,
        "total_built": total,
    }
    for category, values in derived.items():
        for year, value in zip(years, values):
            annual_rows.append(dict(
                lag_months=int(lag_months),
                timing="consent-timed proxy" if lag_months == 0 else "completion-timed",
                year=int(year), category=category, floor_area_Mm2=float(value)
            ))

    return pd.DataFrame(annual_rows), grouped, {
        "years": years,
        "total": total,
        "requirement": requirement,
        "net_market_effect": net_market,
        "raw": raw,
    }


def historical_market_balance(history):
    """Create a second, coarse historical classification.

    Population growth, household-size change and net replacement remain
    separate. Other demand / balance contains extra space, vacancy, the
    retirement-village adjustment and the unexplained residual. Historical
    overbuilding is not independently identified and is therefore NA, not zero.
    """
    labels = {
        "growth": N.band_data_label("growth"),
        "smaller_households": N.band_data_label("smaller_households"),
        "extra_space": N.band_data_label("extra_space"),
        "vacancy": N.band_data_label("vacancy"),
        "replacement_census": N.band_data_label("replacement_census"),
        "retirement_villages": N.band_data_label("retirement_villages"),
        "unexplained": N.band_data_label("unexplained"),
    }
    missing = sorted(set(labels.values()) - set(history["band"].unique()))
    if missing:
        raise ValueError(f"Historical bands are missing expected labels: {missing}")

    rows = []
    group_cols = ["interval", "year_start", "year_end", "households_from"]
    for (interval, year_start, year_end, households_from), group in history.groupby(group_cols, sort=False):
        values = group.set_index("band")["floor_area_Mm2_per_year"].astype(float).to_dict()
        broad = {
            "population_growth": values[labels["growth"]],
            "household_size_change": values[labels["smaller_households"]],
            "net_replacement": values[labels["replacement_census"]],
            "other": sum(values[labels[key]] for key in
                         ("extra_space", "vacancy", "retirement_villages", "unexplained")),
        }
        total = float(group["observed_built_Mm2_per_year"].iloc[0])
        if not np.isclose(sum(broad.values()), total, rtol=1e-9, atol=1e-8):
            raise RuntimeError(f"Historical broad groups do not reconcile in {interval}.")

        basis = (
            "Census-benchmarked household counts"
            if households_from == "census"
            else "Consent-derived household estimates; not independent of consents"
        )
        common = dict(
            period_type="history", period=str(interval), year_start=int(year_start),
            year_end=int(year_end), year_mid=(int(year_start) + int(year_end)) / 2.0,
            total_built_Mm2_per_year=total, data_basis=basis,
            historical_overbuild_identified=False,
        )
        for category, value in broad.items():
            rows.append(dict(**common, category=category, floor_area_Mm2_per_year=float(value)))
        # No historical overbuild series is directly observed in the available
        # census/consent reconciliation; keep these entries missing, not zero.
        for category in ("market_excess", "overbuild_absorbed"):
            rows.append(dict(**common, category=category, floor_area_Mm2_per_year=np.nan))
        rows.append(dict(**common, category="total_built", floor_area_Mm2_per_year=total))
    return pd.DataFrame(rows)


def forecast_market_balance(comparison, lag_months=17):
    """Create the coarse forecast classification using the completion-timed run."""
    selected = comparison[comparison["lag_months"] == int(lag_months)]
    rows = []
    for year, group in selected.groupby("year", sort=True):
        values = group.set_index("category")["floor_area_Mm2"].astype(float).to_dict()
        basis = (
            "Observed completion pipeline (consents lagged 17 months)"
            if int(year) in (2026, 2027)
            else "Modelled annual projection"
        )
        common = dict(
            period_type="projection", period=str(int(year)), year_start=int(year),
            year_end=int(year), year_mid=float(year),
            total_built_Mm2_per_year=float(values["total_built"]), data_basis=basis,
            historical_overbuild_identified=np.nan,
        )
        for category in (
            "population_growth", "household_size_change", "net_replacement", "other",
            "market_excess", "overbuild_absorbed", "total_built"
        ):
            rows.append(dict(**common, category=category,
                             floor_area_Mm2_per_year=float(values[category])))
    return pd.DataFrame(rows)


def _zero_lag_consent_period(B):
    dates = pd.to_datetime(B["df_consents"]["Date"])
    last = dates.max()
    first = last - pd.DateOffset(months=11)
    return f"{first:%b %Y}–{last:%b %Y}"


def _lagged_consent_period(year, lag_months):
    first = pd.Timestamp(int(year), 1, 1) - pd.DateOffset(months=int(lag_months))
    last = pd.Timestamp(int(year), 12, 1) - pd.DateOffset(months=int(lag_months))
    return f"{first:%b %Y}–{last:%b %Y}"


def run_summary(B, lag_months, grouped):
    join = B["join_info"]["50th"]
    pipe = B.get("pipe") or {}
    cohort_rows = []
    if int(lag_months) == 0:
        years = [2026]
        periods = [_zero_lag_consent_period(B)]
        consents = [float(join["O_obs"][0] / B["_completion"])]
    else:
        years = [int(year) for year in pipe.get("years", [])]
        periods = [_lagged_consent_period(year, lag_months) for year in years]
        consents = [float(pipe["consents_all"][year]) for year in years]

    for i, (year, period, consent_total) in enumerate(zip(years, periods, consents)):
        cohort_rows.append(dict(
            completion_or_proxy_year=int(year),
            consent_period=period,
            all_category_consents=consent_total,
            building_equivalent_dwellings=float(join["O_obs"][i]),
            pre_pipeline_requirement_dwellings=float(join["R_obs"][i]),
            gross_excess_dwellings=float(join["e_obs"][i]),
        ))

    cumulative = {category: float(np.sum(values)) for category, values in grouped.items()}
    cumulative["underlying_requirement"] = float(sum(
        cumulative[key] for key in
        ("population_growth", "household_size_change", "net_replacement", "other")
    ))
    cumulative["net_market_effect"] = (
        cumulative["market_excess"] + cumulative["overbuild_absorbed"]
    )
    cumulative["total_built"] = (
        cumulative["underlying_requirement"] + cumulative["net_market_effect"]
    )

    return dict(
        lag_months=int(lag_months),
        timing=("Consent-timed proxy (zero lag)" if int(lag_months) == 0
                else "Completion-timed pipeline (17-month lag)"),
        completion_rate=float(B["_completion"]),
        observed_to=str(B["lag_info"].get("consents_observed_to")),
        pipeline_years=[int(y) for y in pipe.get("years", [])],
        observed_cohorts=cohort_rows,
        gross_market_excess_dwellings_2026_2050=float(np.sum(join["excess"][1:])),
        payback_dwellings_2026_2050=float(-np.sum(join["payback"][1:])),
        cumulative_categories_Mm2_2026_2050=cumulative,
    )


def main():
    # The only imposed change between runs is consent-to-completion lag.
    # Demographic projections, household-size paths, and all other settings
    # must be identical for this to be a controlled timing comparison.
    B0 = validation.run_boss(COMPLETION_LAG_MONTHS=0)
    B17 = validation.run_boss(COMPLETION_LAG_MONTHS=17)

    for key, atol in (("PopTotal_50th", 1e-8),):
        a = np.asarray(B0["df_forecast"][key], dtype=float)
        b = np.asarray(B17["df_forecast"][key], dtype=float)
        if not np.allclose(a, b, rtol=0, atol=atol):
            raise RuntimeError(f"Controlled lag comparison failed: {key} differs.")
    for name, a, b, atol in (
        ("household-size path", B0["S_matched"], B17["S_matched"], 1e-10),
        ("household path", B0["households_forecast"]["50th"],
         B17["households_forecast"]["50th"], 1e-8),
    ):
        if not np.allclose(np.asarray(a, float), np.asarray(b, float), rtol=0, atol=atol):
            raise RuntimeError(f"Controlled lag comparison failed: {name} differs.")

    d0, groups0, _ = projection_components(B0, 0)
    d17, groups17, _ = projection_components(B17, 17)
    comparison = pd.concat([d0, d17], ignore_index=True)

    hist_raw = pd.read_csv(layout.data("baseline/bands_history.csv"))
    historical = historical_market_balance(hist_raw)
    forecast = forecast_market_balance(comparison, 17)
    market_balance = pd.concat([historical, forecast], ignore_index=True)

    summaries = {
        "comparison_basis": (
            "Controlled comparison: same source files, population path, household-size path, "
            "completion rate and remaining defaults; only completion lag differs. "
            "Historical completion timing and stock/replacement calibration are recalculated consistently."
        ),
        "same_population_path": True,
        "same_household_size_path": True,
        "same_household_path": True,
        "lag_0": run_summary(B0, 0, groups0),
        "lag_17": run_summary(B17, 17, groups17),
        "historical_classification": {
            "population_growth": "Population growth",
            "household_size_change": "Smaller households",
            "net_replacement": "Census-measured net replacement",
            "other": (
                "Extra space + vacancy + retirement-village adjustment + unexplained building"
            ),
            "market_excess": "Not separately identified in historical data",
            "overbuild_absorbed": "Not separately identified in historical data",
            "warning": (
                "Historical other/unallocated may contain excess supply, but it also includes "
                "unexplained residual and omitted or mismeasured components; it is not a measured "
                "historical overbuild series."
            ),
        },
        "forecast_classification": {
            "population_growth": "Population growth",
            "household_size_change": "Smaller households",
            "net_replacement": (
                "Demolition replacement + recent replacement wave + unconsented additions"
            ),
            "other": "Extra space + vacancy and any released-vacancy terms",
            "market_excess": "Gross market excess before payback",
            "overbuild_absorbed": "Negative floor area corresponding to the modelled payback",
        },
        "population_household_note": (
            "Household-size settings are unchanged. The next Stats NZ 2023-base family and "
            "household projection release should be assessed as a separate input update."
        ),
        "time_resolution_note": (
            "Monthly consents are shifted month by month for completion timing. Demographic demand "
            "remains annual; quarterly population and stock series are not interpolated into "
            "pseudo-monthly observations."
        ),
    }

    comparison_path = layout.writing(layout.data("diagnostics/lag_comparison_annual.csv"))
    balance_path = layout.writing(layout.data("diagnostics/market_balance_history_projection.csv"))
    summary_path = layout.writing(layout.data("diagnostics/lag_comparison_summary.json"))
    report_path = layout.writing(layout.report("market_balance.md"))

    comparison.to_csv(comparison_path, index=False)
    market_balance.to_csv(balance_path, index=False)
    with open(summary_path, "w") as f:
        json.dump(summaries, f, indent=2)

    labels = [
        ("population_growth", "Population growth"),
        ("household_size_change", "Household-size change"),
        ("net_replacement", "Net replacement"),
        ("other", "Other demand / balance"),
        ("market_excess", "Gross market excess"),
        ("overbuild_absorbed", "Overbuild absorbed"),
    ]
    lines = [
        "# Demand balance and completion-lag comparison",
        "",
        "This is a separate diagnostic. It does not change the detailed demand bands, pathway levers, or carbon accounting.",
        "",
        "## Controlled zero- versus 17-month lag comparison",
        "",
        summaries["comparison_basis"],
        "",
        "| Cumulative floor area, 2026–2050 (Mm2) | Zero lag | 17-month lag |",
        "|---|---:|---:|",
    ]
    for category, label in labels:
        a = summaries["lag_0"]["cumulative_categories_Mm2_2026_2050"][category]
        b = summaries["lag_17"]["cumulative_categories_Mm2_2026_2050"][category]
        lines.append(f"| {label} | {a:.2f} | {b:.2f} |")
    lines.append(
        f"| **Total built** | **{summaries['lag_0']['cumulative_categories_Mm2_2026_2050']['total_built']:.2f}** "
        f"| **{summaries['lag_17']['cumulative_categories_Mm2_2026_2050']['total_built']:.2f}** |"
    )
    lines += ["", "### Observed consent periods", ""]
    z = summaries["lag_0"]["observed_cohorts"][0]
    lines.append(
        f"- Zero lag: {z['consent_period']} is a rolling 12-month consent proxy used for 2026, "
        "not observed completed dwellings in calendar 2026."
    )
    for cohort in summaries["lag_17"]["observed_cohorts"]:
        lines.append(
            f"- 17-month lag: completion cohort {cohort['completion_or_proxy_year']} uses "
            f"{cohort['consent_period']} consents; this is a complete 12-month observed cohort."
        )
    lines += [
        "",
        "The lagged run therefore has two complete observed completion cohorts (2026 and 2027). "
        "The zero-lag run has one rolling 12-month estimate assigned to 2026. These are not "
        "equivalent observations of actual completed dwellings.",
        "",
        "The lag also changes the historical timing of building and therefore the calibrated "
        "replacement rate, stock residual and near-term excess. Those dependent quantities are "
        "recomputed consistently rather than frozen. The comparison isolates the lag setting, "
        "not only the timing of the same fixed excess series.",
        "",
        "## Separate historical and projected classification",
        "",
        "The historical view retains three components separately: population growth, household-size "
        "change, and census-measured net replacement. Other demand / balance combines extra space, "
        "vacancy, retirement-village adjustment and unexplained building.",
        "",
        "**Historical overbuilding is not separately identified by the available data.** It may be "
        "one contributor to the historical remainder, but the remainder also contains measurement "
        "error and omitted or mismeasured stock changes. The model therefore records historical "
        "market excess as missing, not zero, and does not rename the residual as overbuilding.",
        "",
        "The 2023–2025 household estimate bridge is flagged as consent-derived, so it is not "
        "independent evidence of household formation.",
        "",
        "For the projection, population growth, household-size change and net replacement remain "
        "separate. Extra space and vacancy are grouped as other demand / balance. Gross market "
        "excess and overbuild absorption remain explicit separate terms. The original detailed "
        "bands are unchanged and remain the inputs to the pathways.",
        "",
        "## Time resolution",
        "",
        "Consents are monthly and are shifted month by month by the completion lag. Demographic "
        "demand remains annual. Quarterly population and dwelling or household estimates are not "
        "interpolated into pseudo-monthly observations: that would impose an unobserved within-quarter "
        "pattern rather than add information. A quarterly demand engine would require its own "
        "stock-flow calibration and validation and is not introduced here.",
        "",
        "Household-size settings are deliberately unchanged pending the Stats NZ 2023-base family "
        "and household projection release. The new national household projection, its census anchor, "
        "and the household-estimate series should be reconciled together before replacing the current "
        "2018-base projection shape.",
        "",
        "Full annual values are in diagnostics/lag_comparison_annual.csv; the historical and forecast "
        "coarse classification is in diagnostics/market_balance_history_projection.csv; the "
        "machine-readable cohort comparison is in diagnostics/lag_comparison_summary.json.",
    ]
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Demand-balance diagnostics written: {report_path}")


if __name__ == "__main__":
    main()
