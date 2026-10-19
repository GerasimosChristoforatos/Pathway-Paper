# Demand balance and completion-lag comparison

This is a separate diagnostic. It does not change the detailed demand bands, pathway levers, or carbon accounting.

## Controlled zero- versus 17-month lag comparison

Controlled comparison: same source files, population path, household-size path, completion rate and remaining defaults; only completion lag differs. Historical completion timing and stock/replacement calibration are recalculated consistently.

| Cumulative floor area, 2026–2050 (Mm2) | Zero lag | 17-month lag |
|---|---:|---:|
| Population growth | 40.47 | 40.31 |
| Household-size change | 2.18 | 2.17 |
| Net replacement | 14.66 | 8.95 |
| Other demand / balance | 27.88 | 30.28 |
| Gross market excess | 3.64 | 4.54 |
| Overbuild absorbed | -3.66 | -4.71 |
| **Total built** | **85.17** | **81.53** |

### Observed consent periods

- Zero lag: Aug 2025–Jul 2026 is a rolling 12-month consent proxy used for 2026, not observed completed dwellings in calendar 2026.
- 17-month lag: completion cohort 2026 uses Aug 2024–Jul 2025 consents; this is a complete 12-month observed cohort.
- 17-month lag: completion cohort 2027 uses Aug 2025–Jul 2026 consents; this is a complete 12-month observed cohort.

The lagged run therefore has two complete observed completion cohorts (2026 and 2027). The zero-lag run has one rolling 12-month estimate assigned to 2026. These are not equivalent observations of actual completed dwellings.

The lag also changes the historical timing of building and therefore the calibrated replacement rate, stock residual and near-term excess. Those dependent quantities are recomputed consistently rather than frozen. The comparison isolates the lag setting, not only the timing of the same fixed excess series.

## Separate historical and projected classification

The historical view retains three components separately: population growth, household-size change, and census-measured net replacement. Other demand / balance combines extra space, vacancy, retirement-village adjustment and unexplained building.

**Historical overbuilding is not separately identified by the available data.** It may be one contributor to the historical remainder, but the remainder also contains measurement error and omitted or mismeasured stock changes. The model therefore records historical market excess as missing, not zero, and does not rename the residual as overbuilding.

The 2023–2025 household estimate bridge is flagged as consent-derived, so it is not independent evidence of household formation.

For the projection, population growth, household-size change and net replacement remain separate. Extra space and vacancy are grouped as other demand / balance. Gross market excess and overbuild absorption remain explicit separate terms. The original detailed bands are unchanged and remain the inputs to the pathways.

## Time resolution

Consents are monthly and are shifted month by month by the completion lag. Demographic demand remains annual. Quarterly population and dwelling or household estimates are not interpolated into pseudo-monthly observations: that would impose an unobserved within-quarter pattern rather than add information. A quarterly demand engine would require its own stock-flow calibration and validation and is not introduced here.

Household-size settings are deliberately unchanged pending the Stats NZ 2023-base family and household projection release. The new national household projection, its census anchor, and the household-estimate series should be reconciled together before replacing the current 2018-base projection shape.

Full annual values are in diagnostics/lag_comparison_annual.csv; the historical and forecast coarse classification is in diagnostics/market_balance_history_projection.csv; the machine-readable cohort comparison is in diagnostics/lag_comparison_summary.json.
