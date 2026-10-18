# MODEL v4.0.0

Branch `release/model-v4.0.0`, from `release/model-v3.3.2`.

**Status.** The STOP on TL zero-building Monte Carlo draws (below) was reported, and the author decided to
**accept and report** them as the definitional TL outcome. One full run (Monte Carlo + Sobol), one `--figures-only`
export (600 dpi PNG; the data were byte-identical afterwards) and the test suite, run once (235 passed, 2 skipped:
both need the local AESA workbook). The lock is `tests/regression_model_v4.json` (light and full).

## Headline (full profile; v3.3 in brackets)

| run | carbon kt | LoE AR | LoE AtP |
|---|---|---|---|
| Reference | 19,761 (20,615) | 4.46 (4.63) | 17.76 |
| Moderate Pathway | 14,302 | 3.23 (3.39) | 12.85 |
| Ambitious Pathway | 10,267 | 2.32 (2.45) | 9.23 |
| TL | 4,423 | 0.999 (0.98) | 3.97 |

* Monte Carlo (n = 5,000): TL within AR in 49.9% of draws (v3.3: 55.2%).
* Population threshold: 6.614 M (95% CI 6.611–6.616 M).
* TL zero-building draws: 244 of 5,000 (4.9%; v3.3.2: 2,750, 55%). All of them have R > G+ and a 2050 population
  ≤ 6.161 M.

## Timings

| step | time |
|---|---|
| full run | 40.5 min (pathway Monte Carlo 23.7 min) |
| figures-only, 600 dpi | 1.7 min |
| tests | 1.3 min |

## Decisions

### §1 Consent-to-completion lag (`projection.COMPLETION_LAG_MONTHS = 17`)

* **Rule.** Completions in month m = c × consents in month m − L, aggregated to calendar years
  (`projection.lagged_consents`).
* **Same lag everywhere consents become dwellings:**
  * the stock identity and the history;
  * the census-interval rates: consents lagged L/12 yr before each census date (`lag_census`). The census
    under-construction correction applies only at a zero lag;
  * the dwelling-size, typology-mix and retirement-village windows;
  * historical floor area and the AR / AtP base;
  * the projection start.
* **L = 0 reproduces MODEL v3.3 exactly.**
* **Typology months before April 1990.** The consent file's typology columns start in April 1990. Earlier months are
  split by the April 1990 – March 1991 typology ratios of all dwellings. They enter only the 1991 completions (67.8% of
  them at L = 17), which are used only in the cumulative floor area from 1991.
* **Pipeline years.** These are the projection years whose twelve lagged months are all observed: 2026 and 2027 at
  L = 17 (consents observed to July 2026).
  * Their building is observed in every run: c × lagged consents, all categories, with their floor area fixed.
  * Excess = pipeline − requirement for 2026–27. From 2028 the excess is gap_ref × ρ^(t−2027), with
    gap_ref = building 2027 − requirement 2028 (`engine.market_excess`, generalised to n observed years).
  * In lever runs the excess of a pipeline year is the observed building minus the run's own need, so building equals
    the observation in every run (asserted in `pathways.run`).
* **Absorption window.** It now starts at the last observed year (`OVERBUILD_ABSORPTION_START = None` → 2027), so
  w = 0 through 2027. Starting at 2026 would pay back part of the overbuild within the observed 2027.
* **Re-occupation and use window.** It starts at the first unobserved year (2028). Releases of 2027 enter at 2028.
* **The lever adoption window is unchanged (from 2026), as instructed.** Levers therefore act at w(2027) = 0.039 in
  2027. Building and floor area in 2027 stay observed, but an intensity lever (L8, L9, L7) changes the carbon of
  2027's floor area by that weight. This is a stated limitation.
* **ρ.** 0.434, re-estimated on the lagged history (MODEL v3.3: 0.518).
* **Hindcast** (`validation.lag_hindcast`; rolling-origin census dwelling-count identity, 3 origins). Mean absolute
  error:

  | rate method | L = 0 | L = 17 |
  |---|---|---|
  | long run | 15.2% | 8.2% |
  | recent interval | 10.8% | 9.1% |

  L = 17 is not worse, so there is no STOP. The check is now part of `validation.py`.
* **'No 2026 data'.** It truncates consents at December 2025 and uses the projected 2026 population. Under the lag,
  2026 is still observed, so the out-of-sample check moves to 2027 (`validation.check_2026`, status 'pipeline').
* **Retired row.** The Little's-law sensitivity row (two-point W) cannot be combined with the monthly lag.
* **Census interval rates.** With the lag, two interval rates are negative (1996–2001 and 2001–2006); MODEL v3.3 had
  one. The Very High replacement text now reads this from the data.

### §2 Completion rate

* **Central value.** 0.945, the midpoint of the milestones of Jones, Greenaway-McGrevy & Crow (2025, footnote 12):
  * 93% of 2018–19 consents had a final inspection (the lower bound);
  * more than 95% of 2018–21 consents had a first inspection (the upper bound).
* **Monte Carlo.** Uniform(0.93, 0.96), replacing the two-piece distribution (0.92, 0.95, 0.96).
* **Band edge.** The article gives the upper milestone only as '>95%'. The edge 0.96 is a stated judgement.
* **Limitation.** The evidence is Auckland's, applied nationally.
* **Effect vs 0.95.** The Reference is 0.71% higher at 0.95: 19,900.8 kt vs 19,761.4 kt.
* **Legacy.** The legacy MODEL v2.1 Reference (`--reference-legacy`) keeps L = 0 and 0.95.

### §3 TL1 speed limit (`levers.TL1_SPEED_LIMIT`)

* **Rate.** r = the fastest |ΔS| per year between consecutive censuses 1991–2023, on census-benchmarked households:
  0.01176 per year, in **1996–2001**. The brief expected about 0.012 in 2018–23; that interval's rate is 0.00921.
* **Path.** S_TL(t) = max(min(S_ref(2026) + r (t − 2026), 2.7905), S_ref + w × gap), so TL1 is never weaker than
  Ambitious.
* **Level reached.** S_ref(2026) = 2.6779, so the level is reached in 2035.6.
* **Scope.** It applies in TL, the TL steps, the TL Shapley subsets and the Monte Carlo, where it starts from the
  draw's own S(2026). The instant-TL row keeps its definition.

### §4 TL surplus pooling (`pathways.TL_SURPLUS_POOLING`)

* **Pool.** In TL-family runs the positive Reference market excess enters the re-occupation pool, together with the
  TL1 and TL2 releases. The pipeline years' excess enters at 2028; the fading excess enters in its own year.
* **Rule.** Constant share of positive need, availability constraint, carry-forward.
* **Negative excess.** An under-build is made good along the Reference logistic.
* **Bookkeeping.**
  * The re-occupied overbuild is booked in 'Overbuild absorbed'.
  * Its part of the pool unused in 2050 is booked in 'Overbuild absorbed' and, with the opposite sign, in 'Surplus
    kept vacant (2050)' (`flows['ob_remainder']`).
* **Unchanged.** Non-TL runs; the instant-TL and greedy rows are kept.

### §5 Household-size sensitivities

* **New setting.** `HH_SIZE_PATH = 'census_pace'`: S continues linearly from 2023 at the 2018–23 census pace,
  (S_2023 − S_2018) / 5.
* **New table.** `sensitivity/household_size.csv`: the Reference, the Moderate / Ambitious Pathway and TL under the
  Low / High variants and the census pace. These runs use the central lever parameters, applied to each variant's own
  household size.
* **Where else.** The rows are also in the Reference sensitivity table, the Pathway table and the tornado.

### §6 Figures

* **Fig1.**
  * census-interval history to 2023;
  * 2024–25 observed totals (grey, 'Observed (consent-based; household estimates not independent)');
  * 2026–27 pipeline columns split into the need bands plus 'Building above modelled need (pipeline)' (hatched);
  * annual projection from 2028;
  * caption note: lag, sources, pipeline years and the population nowcast.
* **Fig8a.**
  * new rows: completion rate 0.93–0.96; completion lag 15–19 months, with a tick at 0 months; household-size census
    pace; No 2026 data;
  * single-case rows are drawn in the muted grey;
  * the figure is 96 mm high (was 88 mm).
* **Other figure changes, needed to run.**
  * D40: the percentile-bootstrap intervals are drawn as they are (lo to hi). For TL with completion rate as the
    input, the PRCC point estimate (0.878) lies just above the upper end of its interval (0.877). That can happen with
    a percentile interval when the bootstrap distribution is skewed near |PRCC| = 1.
  * D14 (d) and the D15 handover use the last observed year.
  * D34 shows the pool inflow.

## TL zero-building years in Monte Carlo draws (STOP reported; accepted and reported, author's decision)

* **Deterministic runs.** None of the 1,033 TL-family runs (TL, steps, Shapley subsets, instant TL, every scenario)
  has a zero-building year; the minimum is 4,343 dwellings a year. The greedy row TL-reoccupation-fast builds nothing
  in years its pool covers, by its definition (a sensitivity).
* **Monte Carlo, light, n = 1,000.** 48 TL draws (4.8%) have years with no building. MODEL v3.3.2 (full, n = 5,000)
  had 2,750 of 5,000 (55%), so §3–4 removed most of them.
* **Cause, identical in all 48.** The pool R exceeds the whole positive need of 2028–2050 (R > G+):
  * R is 186k–223k: the TL2 vacancy-rate fall to 0% (about 114k), the pooled overbuild, and the household-size
    release;
  * G+ is 63k–185k.
  * The constant-share rule then gives s = 1: every year's need is met from vacant dwellings and nothing is built.
* **Where they fall.** These are the lowest-population draws: P_NZ(2050) ≤ 6.145 M, the bottom 5.2% of draws. Their
  TL LoE AR is at most 0.64.
* **Read.** This follows from the definitional limit (0% vacancy plus re-occupation of the overbuild) meeting a low
  population path. It is not a bookkeeping error: the stock identity, band sums and availability constraint all hold.
  Any rule that forces building in these draws would be a new, unsourced assumption.

## Tests

* **New (`tests/test_model_v4.py`).**
  * Equivalence: L = 0, completion rate 0.95, speed limit off and pooling off reproduce the v3.3 Reference projection
    and all 55 deterministic v3.3 pathway runs (floor area, carbon, dwellings, committed; 1e-9). **Passes.**
  * The lag at L = 0 equals the calendar-year sums.
  * Pipeline years for L = 0 / 15 / 17 / 19, and the observed building.
  * Completion-rate band and median.
  * The TL1 path.
  * Building ≥ 0, and > 0 in every TL-family run (the greedy row excluded and reported).
  * The household-size table.
* **Legacy v2.1 lock.** Run with the v2.1 completion timing.
* **Retired (figure-only release checks of v3.3.x).**
  * `test_figures_v3_3_1::test_deterministic_files_equal_v3_3` and `test_montecarlo_files_equal_v3_3`;
  * `test_figures_v3_3_2::test_data_byte_identical_to_v3_3_1`;
  * `test_model_v3_3::test_equal_to_v3_2_under_the_map` (now covered through the v3.3 equivalence).
* **Lock.** `tests/regression_model_v4.json`: 34 deterministic files, plus the Monte Carlo files of the light and full
  profiles.
