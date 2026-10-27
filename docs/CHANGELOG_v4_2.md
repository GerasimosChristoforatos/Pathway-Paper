# MODEL v4.2 — Part A (diagnostic; nothing adopted)

Branch `release/model-v4.2.0`, from `release/model-v4.0.0`. The v4.1 diagnostic commits are cherry-picked: gap_2026
fix, `tools/demand_balance.py`, `figures/market_balance.py`.

## Switches (`projection.py`)

Each new switch defaults to the MODEL v4.0.0 behaviour, so the Reference is unchanged (tested).

* **`HH_BRIDGE`** — `'dhe'` (default) or `'erp_S'`. With `'erp_S'`, households from 2024 are the 31 December ERP
  divided by the model's S path, anchored on the 2023 census.
* **`START_MODE`** — `'observed'` (default) or `'projection'`. `'projection'` uses:
  * the Stats NZ population median from 2026, with no nowcast;
  * no pipeline, no market excess and no carried deviation;
  * the 17-month lag in the history only.
* **`HH_SIZE_PATH`** — the requested `HH_PATH`. The existing switch is extended rather than renamed:
  * `'statsnz_2018'` is an alias of `'statsnz'`;
  * `'census_pace'` is the existing sensitivity;
  * `'statsnz_2023'` is a loader stub for the Stats NZ 2023-base family and household projections. It reads
    `FILE_HOUSEHOLDS_PROJ_2023` (CSV columns: Year, Variant, Population, Households), is anchored on the 2023 census,
    and applies no DHE rebase factor. It is tested only on a synthetic file; the real file is not in `data/`.

## Outputs

`tools/transition_audit.py` writes to `outputs/_light/diagnostics/transition/`:

* `audit.csv` — A1, 2016–2030 annual;
* `audit_census_intervals.csv`;
* `runs.csv` — A5, the 8 runs;
* `history_residual.csv`;
* `D45_transition_bands.png`.

## Definitions

* **Need** — new households / (1 − v) + vacancy allowance and change + net replacement at the model rate. In history
  years the rate is that of the census interval containing the year.
* **Residual** — building − need.
* **Historical per-year residual** — measured against the census-interval rate. It therefore shows within-interval
  timing, and sums to about zero over each interval.

## Tests

`tests/test_model_v4_2.py`: 4 passed. `tests/test_demand_balance.py`: 2 passed, 1 skipped.

# MODEL v4.2 — Part B (adopted)

## Changes

* **B1. Bridge adopted.** `HH_BRIDGE = 'erp_S'`: households from 2024 are ERP / S(t), so Stats NZ DHE is not used
  after the 2023 census. `START_MODE` stays `'observed'`; `HH_SIZE_PATH` stays `'statsnz'` (= `'statsnz_2018'`).
* **2026–2050 unchanged.**
  * Reference, Moderate / Ambitious Pathway and TL totals equal v4.0 to ≤ 2.2e-16; `pathways/runs.csv` is identical
    to v4.0 (relative difference 0).
  * Only history files changed: bands_history, history_unexplained, stock_identity, household_formation, gap_2026,
    reality_checks and the D02 / D03 / D08 / D15 / projection_paths figure sources.
  * Lock: the hashes of bands_history.csv and history_unexplained.json are updated in
    `tests/regression_model_v4.json`.
* **Monte Carlo.** Not rerun: the v4.0 full-profile outputs are reused unchanged.
* **B2. Six display bands.** Defined in `bands.DISPLAY`, written to `outputs/data/bands_display_map.csv`; for figures
  only. Tested: the six-band sums equal the detailed-band sums every year (1e-9).
* **B3. Figures.**
  * Fig1: six bands; 2024–25 decomposed with the ERP / S households (the 2023–2025 interval column).
  * Fig2: panels a and d by the six bands.
  * Fig5: the six bands, plus Re-used dwellings (TL).
  * New ED11: the detailed-band Fig1 and Fig2a. This makes 11 ED items, one over the Nature Cities cap of 10, so
    `test_figures_v3_3_1::test_display_item_limits` will fail until one item moves to the supplementary set.

## Fixes carried from v4.1

* D43 read a column its own pivot drops; it now reads the `total_built` category.
* `test_demand_balance` now expects the ERP / S basis for 2023–2025.
