# MODEL v4.1.0

Branch `release/model-v4.1.0`, based on `release/model-v4.0.0`.

## Scope

This is a deliberately narrow diagnostic correction. The demand projection, completion lag, completion rate, population nowcast, overbuild absorption rule, pathways, and LCA inputs are unchanged.

## 2026 population and completion-period audit

The 2026 completion pipeline and the population input are both annual quantities, but they refer to different 12-month windows:

- **Completions in calendar 2026:** at the adopted 17-month consent-to-completion lag, these are the consents issued from August 2024 to July 2025, shifted month by month into January–December 2026. All 12 consent months are observed in the v4.0.0 input.
- **Population growth used for 2026:** the current nowcast is the change in Stats NZ's mean-quarter ERP between June quarter 2025 and June quarter 2026 (35,400 people). This is a full 12-month June-to-June measure, not population growth over only January–June 2026. It is used as a proxy for the calendar-year population increment because the projection is indexed by calendar year.

The windows are offset by six months. The population input therefore is not an exact observation of December-to-December 2026 growth, and a different second-half growth pace could make the proxy too high or too low. However, it is incorrect to describe the current model as comparing a full year of completions with only six months of population growth: it applies a 12-month population-growth observation. The timing difference alone does not explain the full 2026 excess.

A more explicit calendar-year nowcast could use the observed national ERP at 30 June 2026 and a consistent 30 June 2027 projection to estimate 31 December 2026, then compare this with the model's 31 December 2025 ERP anchor. Before adopting that method, the official point-in-time ERP series, the mean-quarter DPE series, projection vintage, and household series must be reconciled. No such unverified splice is introduced in v4.1.0.

The August 2026 consent release is not added to the projection input in this branch: it does not complete a full 2028 consent cohort at a 17-month lag and therefore does not create another fully observed pipeline year. It should be added to the source data in the next routine input refresh, but it should not be treated as a complete 2028 completion observation.

## Corrected 2026 gap diagnostic

`gap_2026.requirement_2026()` previously read `dwell_in_scope + rv_units` from the final joined engine output. That output already contains the observed pipeline join and has floor area fixed to observed consented GFA; it is not the underlying demand requirement.

The diagnostic now reads `join_info['50th']['R26']`, the exact requirement recorded by `engine.market_excess()` during the unjoined forward pass. The output identifies this explicitly as the pre-pipeline requirement and labels the population input as a 12-month June-to-June measure.

Expected reconciliation under the v4.0.0 committed outputs:

- 2026 observed pipeline building: approximately 32,016 dwellings.
- 2026 requirement before applying the population nowcast: approximately 25,470 dwellings.
- June-to-June population nowcast effect relative to the projection median: approximately -6,157 dwelling-equivalents.
- Requirement after that population adjustment: approximately 19,313 dwellings.
- Pipeline excess: approximately 12,702 dwellings.

These are diagnostic values; the full model run regenerates them from source inputs. The corrected diagnostic should reconcile with `outputs/reports/overbuild_2026.md`.

## Tests

Added a regression test that checks the 2026 gap diagnostic returns the stored pre-pipeline `R26` and that subtracting the pipeline join from the final requirement recovers the same value.

The GitHub-side change is not a substitute for running the repository's full light/full pipeline and test suite locally. Regenerate outputs and the regression lock only after those runs pass.


## Controlled completion-lag and market-balance analysis

Added a separate diagnostic run after the baseline overbuild report. It runs the Reference twice, with a zero-month and a 17-month consent-to-completion lag. The same source files, population path, household-size path, completion rate, and remaining model defaults are retained; the diagnostic checks that the population and household paths are identical. Historical completion timing and the stock / replacement calibration are recalculated under each lag, because those are consequences of the timing assumption rather than independent settings.

The comparison is reported in floor area by a broad, secondary classification:

- Population growth.
- Household-size change.
- Net replacement (demolition replacement + recent replacement wave + unconsented additions).
- Other demand / balance (extra space + vacancy and related release terms).
- Gross market excess.
- Overbuild absorbed.

These are aggregates of the existing detailed bands. No original band, pathway lever, carbon calculation, or pathway assumption is changed.

### Interpretation of zero lag

Zero lag is labelled a consent-timed proxy, not observed completed construction. At the current data cut it uses the latest rolling 12 months of consent data as its 2026 consent estimate. The 17-month run instead has complete observed 12-month consent cohorts shifted into completion years 2026 and 2027. The two methods are therefore not interchangeable observations; the comparison is a timing-method sensitivity.

### Historical classification

Historical intervals retain population growth, household-size change, and census-measured net replacement as separate components. The remainder groups extra space, vacancy, retirement-village adjustment and unexplained building. The historical residual can contain excess supply, but it also includes omitted or mismeasured components. There is no independent historical overbuild measure in the available annual data, so the historical market-excess and absorption entries are missing rather than set to zero or inferred from the residual.

The 2023–2025 household-estimate interval is flagged as consent-derived, not independent evidence of household formation. The current household-size projection remains unchanged pending the Stats NZ 2023-base family and household projection release. Once published, the projection, census anchor and consent-derived household-estimate bridge should be reconciled together before changing this input.

### Time resolution

Consents continue to be handled monthly and shifted month by month by the completion lag. Demographic demand remains annual. Quarterly population and dwelling / household estimates are not interpolated into pseudo-monthly observations: that would impose an unobserved within-quarter pattern. A quarterly demand engine is a separate methodological development requiring stock-flow calibration and validation; it is not part of this release.

### New outputs

- D43: historical and projected market-balance classification.
- D44: annual GFA comparison by broad demand group under zero and 17-month lag.
- outputs/data/diagnostics/lag_comparison_annual.csv
- outputs/data/diagnostics/market_balance_history_projection.csv
- outputs/data/diagnostics/lag_comparison_summary.json
- outputs/reports/market_balance.md

