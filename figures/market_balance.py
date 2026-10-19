"""Secondary market-balance figures for MODEL v4.1.0.

The existing demand-band figures remain unchanged. These figures show a
coarser classification for interpretation and the controlled lag comparison.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from figures import data as D
from figures import draw as P
from figures import style as S


def _src(fid):
    if fid == "D43_historical_market_balance":
        return ["diagnostics/market_balance_history_projection.csv"]
    return ["diagnostics/lag_comparison_annual.csv"]


def d43():
    """Historical and projected floor area by the secondary market-balance groups."""
    fid = "D43_historical_market_balance"
    d = D.csv("diagnostics/market_balance_history_projection.csv")
    hist = d[d["period_type"] == "history"].copy()
    proj = d[d["period_type"] == "projection"].copy()

    history_wide = hist.pivot(index=["period", "year_mid", "year_start", "year_end"],
                              columns="category", values="floor_area_Mm2_per_year").reset_index()
    projection_wide = proj.pivot(index=["period", "year_mid", "year_start", "year_end"],
                                 columns="category", values="floor_area_Mm2_per_year").reset_index()
    history_wide = history_wide.sort_values("year_mid")
    projection_wide = projection_wide.sort_values("year_mid")

    categories = [
        "population_growth", "household_size_change", "net_replacement", "other",
        "market_excess", "overbuild_absorbed"
    ]
    labels = {
        "population_growth": "Population growth",
        "household_size_change": "Household-size change",
        "net_replacement": "Net replacement",
        "other": "Other / unallocated",
        "market_excess": "Gross market excess",
        "overbuild_absorbed": "Overbuild absorbed",
    }
    colours = {
        "population_growth": S.BAND["growth"][0],
        "household_size_change": S.BAND["smaller_households"][0],
        "net_replacement": S.BAND["replacement"][0],
        "other": S.UNEXPLAINED[0],
        "market_excess": S.BAND["overbuild_2026"][0],
        "overbuild_absorbed": S.BAND["overbuild_absorbed"][0],
    }

    fig, ax = plt.subplots(figsize=S.figsize("double", 88))
    for frame, is_history in ((history_wide, True), (projection_wide, False)):
        x = frame["year_mid"].to_numpy(float)
        if is_history:
            width = (frame["year_end"] - frame["year_start"] + 1).to_numpy(float) * 0.86
        else:
            width = np.full(len(frame), 0.82)
        positive_bottom = np.zeros(len(frame))
        negative_bottom = np.zeros(len(frame))
        for category in categories:
            values = frame[category].to_numpy(float) if category in frame else np.full(len(frame), np.nan)
            values = np.nan_to_num(values, nan=0.0)
            pos = np.maximum(values, 0.0)
            neg = np.minimum(values, 0.0)
            # Historical market excess and payback are NA in the source data.
            # They are drawn as no segment only for visual stacking.
            ax.bar(x, pos, width=width, bottom=positive_bottom, color=colours[category],
                   edgecolor=colours[category], linewidth=S.LW_THIN, align="center")
            ax.bar(x, neg, width=width, bottom=negative_bottom, color="white",
                   edgecolor=colours[category], linewidth=S.LW_OUTLINE, align="center")
            positive_bottom += pos
            negative_bottom += neg

        total = frame["total_built_Mm2_per_year"].to_numpy(float)
        ax.plot(x, total, color=S.INK, lw=S.LW_BOLD, marker="o" if is_history else None,
                ms=3 if is_history else 0, zorder=5)

    ax.axvline(2025.5, color=S.MUTED, lw=S.LW, ls=":")
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_xlim(1990.5, 2050.5)
    ax.set_ylabel("Floor area (Mm² per year)")
    ax.set_xlabel("Historical census intervals (bars show interval means) and annual projection")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
    ax.grid(axis="x", visible=False)

    handles = [
        Patch(facecolor=colours[k], edgecolor=colours[k], label=labels[k])
        for k in categories[:4]
    ]
    handles += [
        Patch(facecolor=colours["market_excess"], edgecolor=colours["market_excess"],
              label=labels["market_excess"]),
        Patch(facecolor="white", edgecolor=colours["overbuild_absorbed"],
              label=labels["overbuild_absorbed"]),
        Line2D([0], [0], color=S.INK, lw=S.LW_BOLD, label="Total floor area built"),
    ]
    fig.legend(handles=handles, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               frameon=False, fontsize=S.FONT_MIN)
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    S.save_figure(
        fig, fid,
        note=(
            "History separates population growth, household-size change and census-measured net replacement. "
            "Other / unallocated combines extra space, vacancy, retirement-village adjustment and unexplained "
            "building; it may contain historical excess supply but is not a measured overbuild series. The "
            "2023–2025 household bridge is consent-derived. From 2026, gross market excess and its payback are "
            "shown separately on the 17-month completion-timed Reference."
        ),
        source=_src(fid),
    )


def d44():
    """Annual GFA by broad category under a controlled zero- versus 17-month lag comparison."""
    fid = "D44_completion_lag_comparison"
    d = D.csv("diagnostics/lag_comparison_annual.csv")
    labels = {0: "Zero lag (consent-timed proxy)", 17: "17-month lag (completion-timed)"}
    colours = {0: S.ACCENT_ORANGE, 17: S.ACCENT_BLUE}
    panels = [
        ("population_growth", "Population growth"),
        ("household_size_change", "Household-size change"),
        ("net_replacement", "Net replacement"),
        ("other", "Other demand / balance"),
        ("market_excess", "Gross excess and payback"),
        ("total_built", "Total floor area built"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=S.figsize("double", 100), sharex=True)
    axes = axes.ravel()
    for i, (category, title) in enumerate(panels):
        ax = axes[i]
        for lag in (0, 17):
            g = d[(d["lag_months"] == lag) & (d["category"] == category)].sort_values("year")
            if not g.empty:
                ax.plot(g["year"], g["floor_area_Mm2"], color=colours[lag], lw=S.LW_BOLD,
                        ls="-" if lag == 0 else "--", label=labels[lag])
        if category == "market_excess":
            for lag in (0, 17):
                g = d[(d["lag_months"] == lag) & (d["category"] == "overbuild_absorbed")].sort_values("year")
                if not g.empty:
                    ax.plot(g["year"], g["floor_area_Mm2"], color=colours[lag], lw=S.LW,
                            ls=":" if lag == 0 else "-.", label=labels[lag] + " – absorbed")
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
        ax.set_xlim(2026, 2050)
        ax.set_ylabel("Mm² per year")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        P.panel(ax, "abcdef"[i], title)

    for ax in axes[-2:]:
        ax.set_xlabel("Year")
    handles = [
        Line2D([0], [0], color=colours[0], lw=S.LW_BOLD, label=labels[0]),
        Line2D([0], [0], color=colours[17], lw=S.LW_BOLD, ls="--", label=labels[17]),
        Line2D([0], [0], color=colours[0], lw=S.LW, ls=":", label="Zero lag – absorbed"),
        Line2D([0], [0], color=colours[17], lw=S.LW, ls="-.", label="17-month lag – absorbed"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02),
               frameon=False, fontsize=S.FONT_MIN)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    S.save_figure(
        fig, fid,
        note=(
            "Both runs use identical source files and demographic paths; only the monthly consent-to-completion "
            "lag changes. Zero lag treats a rolling 12-month consent estimate as the 2026 build proxy; it is not "
            "a count of completed calendar-2026 homes. The 17-month run uses complete observed consent cohorts "
            "for 2026 and 2027. Lag-specific historical completion timing and replacement calibration are "
            "recomputed consistently."
        ),
        source=_src(fid),
    )


FIGURES = {
    "D43_historical_market_balance": d43,
    "D44_completion_lag_comparison": d44,
}
