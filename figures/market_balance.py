"""Secondary market-balance figures (SF7).

They show a coarser classification than the demand bands, for interpretation, and the controlled lag comparison.
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
    """Annual GFA by broad category: the 17-month lag against the like-for-like zero-lag run (forward net replacement
    held at the 17-month calibration, so only the timing of building differs); the recalibrated zero-lag run as a thin
    grey context line."""
    fid = "SF7_completion_lag"
    d = D.csv("diagnostics/lag_comparison_annual.csv")
    sm = D.js("diagnostics/lag_comparison_summary.json")
    colours = dict(S.LAG_VARIANT)          # palette.toml [lag_variants]
    runs = [("lag_0_held", "Zero lag, net replacement held at the 17-month calibration", colours[0], "-", S.LW_BOLD),
            ("lag_17", "17-month lag (completion-timed)", colours[17], "--", S.LW_BOLD),
            ("lag_0", "Zero lag, recalibrated (context)", S.MUTED, ":", S.LW)]
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
        for run, label, col, ls, lw in runs:
            g = d[(d["run"] == run) & (d["category"] == category)].sort_values("year")
            if not g.empty:
                P.line(ax, g["year"], g["floor_area_Mm2"], color=col, lw=lw, ls=ls, label=label)
        if category == "market_excess":
            for run, ls in (("lag_0_held", ":"), ("lag_17", "-.")):
                g = d[(d["run"] == run) & (d["category"] == "overbuild_absorbed")].sort_values("year")
                if not g.empty:
                    P.line(ax, g["year"], g["floor_area_Mm2"], color=dict((r[0], r[2]) for r in runs)[run], lw=S.LW,
                           ls=ls)
        ax.axhline(0, color=S.INK, lw=S.LW_THIN)
        ax.set_xlim(2026, 2050)
        ax.set_ylabel("Mm² per year")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        P.panel(ax, "abcdef"[i], title)

    for ax in axes[-2:]:
        ax.set_xlabel("Year")
    handles = [Line2D([0], [0], color=col, lw=lw, ls=ls, label=label) for _, label, col, ls, lw in runs] + [
        Line2D([0], [0], color=colours[0], lw=S.LW, ls=":", label="Zero lag (held) – absorbed"),
        Line2D([0], [0], color=colours[17], lw=S.LW, ls="-.", label="17-month lag – absorbed"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02),
               frameon=False, fontsize=S.FONT_MIN)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    cum = {k: sm[k]["cumulative_categories_Mm2_2026_2050"]["net_replacement"] for k in ("lag_0_held", "lag_17", "lag_0")}
    rate = {k: 100 * sm[k]["recent_net_replacement_rate_used"] for k in ("lag_17", "lag_0")}
    a, b = sm["lag_17"]["recent_interval"]
    S.save_figure(
        fig, fid,
        note=(
            "All runs use identical source files and demographic paths. The like-for-like zero-lag run holds the "
            f"forward net replacement at the 17-month calibration ({a}-{b} rate {rate['lag_17']:.3f}%/yr), so it "
            "differs from the 17-month run only in the timing of building. The recalibrated zero-lag run (grey, "
            f"context) re-estimates net replacement from the census counts with zero-lag timing ({rate['lag_0']:.3f}%/yr "
            "with the census under-construction correction); its higher net replacement in panel c is that "
            "recalibration, not the timing of building. Cumulative net replacement 2026-2050: "
            f"{cum['lag_0_held']:.2f} Mm² (zero lag, held), {cum['lag_17']:.2f} Mm² (17 months), {cum['lag_0']:.2f} Mm² "
            "(zero lag, recalibrated). Zero lag treats a rolling 12-month consent estimate as the 2026 build proxy; "
            "the 17-month run uses complete observed consent cohorts for 2026 and 2027."
        ),
        source=["diagnostics/lag_comparison_annual.csv", "diagnostics/lag_comparison_summary.json"],
    )


FIGURES = {"SF7_completion_lag": sf7_completion_lag}
