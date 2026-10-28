"""Secondary market-balance figures for MODEL v4.1.0.

The existing demand-band figures remain unchanged. These figures show a
coarser classification for interpretation and the controlled lag comparison.
"""
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from figures import data as D
from figures import draw as P
from figures import style as S


def _src(fid):
    if fid == "D43_historical_market_balance":
        return ["diagnostics/market_balance_history_projection.csv"]
    return ["diagnostics/lag_comparison_annual.csv"]


def sf7_completion_lag():
    """Annual GFA by broad category under a controlled zero- versus 17-month lag comparison."""
    fid = "SF7_completion_lag"
    d = D.csv("diagnostics/lag_comparison_annual.csv")
    labels = {0: "Zero lag (consent-timed proxy)", 17: "17-month lag (completion-timed)"}
    colours = dict(S.LAG_VARIANT)          # MODEL v4.3.3: palette.toml [lag_variants]
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
                P.line(ax, g["year"], g["floor_area_Mm2"], color=colours[lag], lw=S.LW_BOLD,
                        ls="-" if lag == 0 else "--", label=labels[lag])
        if category == "market_excess":
            for lag in (0, 17):
                g = d[(d["lag_months"] == lag) & (d["category"] == "overbuild_absorbed")].sort_values("year")
                if not g.empty:
                    P.line(ax, g["year"], g["floor_area_Mm2"], color=colours[lag], lw=S.LW,
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
            "recomputed consistently, so panel c is not like-for-like in replacement: the net replacement rate is "
            "re-estimated from the census dwelling counts with each run's completion timing (2018-2023 interval: "
            "0.301%/yr at zero lag, with the census under-construction correction, against 0.173%/yr at 17 months), "
            "and the difference in c is that recalibration, not the timing of building itself (MODEL v4.3.1, "
            "investigation B3)."
        ),
        source=["diagnostics/lag_comparison_annual.csv"],
    )


FIGURES = {"SF7_completion_lag": sf7_completion_lag}
