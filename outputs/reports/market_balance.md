# Demand balance and completion-lag comparison

This is a separate diagnostic. It does not change the detailed demand bands, pathway levers, or carbon accounting.

## Controlled zero- versus 17-month lag comparison

Controlled comparison: same source files, population path, household-size path, completion rate and remaining defaults; only completion lag differs. lag_0 recalculates the historical completion timing and the stock and replacement calibration with zero lag; lag_0_held is the like-for-like run: zero lag with the forward net replacement held at the 17-month calibration (projection.NET_REPLACEMENT_HELD), so only the timing of building differs from lag_17.

| Cumulative floor area, 2026–2050 (Mm2) | Zero lag, net replacement held at the 17-month calibration | Zero lag, recalibrated | 17-month lag |
|---|---:|---:|---:|
| Population growth | 40.76 | 40.76 | 40.59 |
| Household-size change | 14.00 | 14.00 | 13.94 |
| Net replacement | 9.01 | 15.22 | 9.29 |
| Other demand / balance | 39.67 | 39.67 | 42.87 |
| Gross market excess | 2.50 | 1.80 | 2.02 |
| Overbuild absorbed | -3.34 | -2.64 | -4.78 |
| **Total built** | 102.60 | 108.81 | 103.94 |

### Observed consent periods

- Zero lag: Aug 2025–Jul 2026 is a rolling 12-month consent proxy used for 2026, not observed completed dwellings in calendar 2026.
- 17-month lag: completion cohort 2026 uses Aug 2024–Jul 2025 consents; this is a complete 12-month observed cohort.
- 17-month lag: completion cohort 2027 uses Aug 2025–Jul 2026 consents; this is a complete 12-month observed cohort.

The lagged run therefore has two complete observed completion cohorts (2026 and 2027). The zero-lag run has one rolling 12-month estimate assigned to 2026. These are not equivalent observations of actual completed dwellings.

The lag also changes the historical timing of building and therefore the calibrated replacement rate, stock residual and near-term excess. In the recalibrated zero-lag run those dependent quantities are recomputed consistently; in the like-for-like zero-lag run the forward net replacement is held at the 17-month calibration (the 2018-2023 rate 0.173%/yr instead of the zero-lag 0.301%/yr), so the difference to the 17-month run is the timing of building alone.

## Separate historical and projected classification

The historical view retains three components separately: population growth, household-size change, and census-measured net replacement. Other demand / balance combines extra space, vacancy, retirement-village adjustment and unexplained building.

**Historical overbuilding is not separately identified by the available data.** It may be one contributor to the historical remainder, but the remainder also contains measurement error and omitted or mismeasured stock changes. The model therefore records historical market excess as missing, not zero, and does not rename the residual as overbuilding.

The 2023–2025 household estimate bridge is flagged as consent-derived, so it is not independent evidence of household formation.

For the projection, population growth, household-size change and net replacement remain separate. Extra space and vacancy are grouped as other demand / balance. Gross market excess and overbuild absorption remain explicit separate terms. The original detailed bands are unchanged and remain the inputs to the pathways.

## Time resolution

Consents are monthly and are shifted month by month by the completion lag. Demographic demand remains annual. Quarterly population and dwelling or household estimates are not interpolated into pseudo-monthly observations: that would impose an unobserved within-quarter pattern rather than add information. A quarterly demand engine would require its own stock-flow calibration and validation and is not introduced here.

Household size follows the Stats NZ 2023-base family and household projections (Medium A), rebased on the 2023 census; the household estimates of 2019-2025 are still the census-pinned rescaling of the latest Stats NZ release (last household base 2018) and the ERP / S bridge.

Full annual values are in diagnostics/lag_comparison_annual.csv; the historical and forecast coarse classification is in diagnostics/market_balance_history_projection.csv; the machine-readable cohort comparison is in diagnostics/lag_comparison_summary.json.
