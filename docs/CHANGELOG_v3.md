# MODEL v3.0.0: changes and decisions

Branch `release/model-v3.0.0`, created from `release/model-v2.1.2` (95cd074). Older branches are untouched. This file
records every change and every decision taken while building the release; where the specification left a choice
open, the choice and its reason are given here. Numbers quoted are deterministic (identical in both run profiles)
unless marked "Monte Carlo"; every number is read from `outputs/data/` and can be traced there.

## Summary

* The **Reference absorbs the 2026 overbuild by 2035** on a logistic path (it was never absorbed in v2.1). Reference
  floor area 2026–2050 85.90 Mm² (v2.1: 89.57), embodied carbon 20,615 kt CO₂e (v2.1: 21,578), cumulative level of
  exceedance AR 4.631, AtP 18.52.
* **Nine rule-based levers** with four ambition levels (Reference / Moderate / Ambitious / theoretical limit, after
  the 2050 Pathways Calculator and EUCalc), renumbered and regrouped into P1–P4; P5 combines them.
* **TL1–TL9** adopted on the same logistic, with gradual re-occupation of the dwellings released by TL3 and TL4.
* **Run profiles** light / full; compute and drawing separated (`figures/` package); new output architecture
  (`paper_main/`, `paper_extended/`, `diagnostics/<group>/`, `FIGURES.md`, `run_meta.json`).
* **STOP conditions**: none triggered (details in the checks section).

## §0 Run profiles

| | light (default) | full |
|---|---|---|
| Monte Carlo | 1,000 Latin hypercube draws, seed 20261014 | 5,000 draws, seed 20260924 (the existing seed) |
| Sobol indices | off | on |
| bootstrap (L2 / L6 intervals, SRC / PRCC intervals) | 500 | 2,000 |
| figures | PNG 200 dpi, footer "LIGHT RUN — n=1000" | vector PDF + PNG 600 dpi |
| outputs | `outputs/_light/` | `outputs/` |

Decisions:

* **The light profile has its own seed** (20261014), as specified, so its draws are not a prefix of the full draws.
  Its Monte Carlo results are a development check, never a reported number.
* **The bootstrap replicate count follows the profile.** It changes only the *intervals* of the Harrell-Davis
  estimates (L2, L6) and of the SRC / PRCC importance; the point estimates, and therefore every deterministic run,
  do not depend on it. The carbon-factor bootstrap that defines the Monte Carlo input distribution is part of the
  Monte Carlo itself and follows its draws.
* **Profile equality** (`tests/test_profiles.py`): the lever parameters resolved under both profiles agree in every
  field except the bootstrap intervals, and the deterministic data files are identical between the two profiles'
  outputs.
* **Shapley values are exact** over all 2⁹ = 512 subsets per game, with a run cache keyed by the lever setting
  (`levers.key`), so a subset shared by several games (and by the pathways, the λ-sweep and the waterfalls) is run
  once. Pathway step: about 15 s for 2,137 runs.
* **`metrics.json`** reports the profile in `run_mode` ("light profile, not for reporting" or "full"; it read the
  retired `--quick` flag before).
* **`run_meta.json`** records profile, mode, draws, Sobol, bootstrap, every seed, figure formats, git hash and dirty
  flag, a SHA-256 of the inputs, timestamp and the seconds of every step.
* **Light / legacy outputs are not versioned** (`.gitignore`): they are reproducible working copies; the committed
  outputs are those of the full profile.
* **Timings** (same machine): light pipeline 4 min 53 s including the tests and every figure (v2.1.2 full run about
  22.6 min; v2.1.2 figures-only about 10 min; v3 light figures 38 s for the 61 light-profile figures). Full profile: 975.7 s
  (16.3 min) before the tests (compute 885.2 s, of which the pathway Monte Carlo 378.3 s, AESA 229.2 s and the
  Reference Monte Carlo 182.7 s; figures 88.9 s at 600 dpi PDF + PNG); tests about 40 s (`outputs/run_meta.json`).

## §1 The Reference absorbs the 2026 overbuild by 2035

* **Rule.** The surplus of the 2026 overbuild, C(t) (cumulative market excess), is reduced along the normalised
  logistic weight w(t), 0 in 2026 and 1 from 2035 (midpoint 2030.5, k = ln 81 / 6, the adoption path of the levers):
  target surplus U(t) = C(t) (1 − w(t)); payback target = U(t−1) + excess(t) − U(t). The payback is capped at
  max(gross building, 0) of the year and the shortfall carried to the next years (`engine.absorb_overbuild`).
  Log: `baseline/overbuild_absorption_log.csv` (excess, cumulative excess, weight, targets, paid, carried, cap
  binding, surplus vacant, built, implied vacancy).
* **Result.** Excess 27,479 dwellings (2026–2050), absorbed in full by 2035 (the residual excess after 2035, at
  most 14 dwellings a year, is paid in the year it arises). The cap never binds. Implied vacancy 6.13% (2026), peak
  6.33% (2028), 5.39% from 2035.
* **The excess is computed once and held fixed in every run.** The market excess of the Reference is passed to every
  lever, pathway and TL run (`market_excess(..., excess=...)`); the maximum absolute difference of the excess between
  runs is 0.0 (`pathways/levers.json`, `identity_checks`). For the record, v2.1.2 also gave 0.0 (checked on a worktree
  at 95cd074).
* **Vacancy is frozen at 5.39%** (the 2023 census value, one definition) as the forward parameter.
* **New band "Overbuild absorbed"** (negative). "Replacement" is split into "Demolition replacement" (BRANZ rate) and
  "Unconsented additions" (negative: the calibrated residual of the census identity). This split makes the appendix
  bridge D11 identical to D10, so D11 is retired.
* **`--reference-legacy`** (`PATHWAY_REFERENCE_LEGACY=1`) reproduces the v2.1 Reference; the fixture
  `tests/reference_legacy_v2_1.json.gz` was captured at 95cd074 and the lock passes with a worst difference of 0
  (tolerance 1e-12 relative). **Scope decision:** the legacy switch covers the Reference (projection, Monte Carlo,
  AESA), not the v2.1 pathways, whose lever rule MODEL v3.0.0 replaces.
* **Sensitivity rows** (`Sensitivity.py`; Fig7 tornado, D16, D17): absorption never (the v2.1 Reference), by 2030,
  by 2045; booked as redevelopment (stock-neutral); vacancy parameter = the 1986–2023 census mean (one definition);
  half-life 5 / 15 years of the surge; Low / High replacement. The absorption-timing rows move Reference carbon
  by −0.15% (by 2030) and +0.25% (by 2045).
* **Theory fixes the direction, not the speed.** The stock-flow models of the housing market (Rosen & Smith 1983;
  Wheaton 1990; DiPasquale & Wheaton 1992; Gabriel & Nothaft 2001) imply that vacancy above its natural rate reverts
  through reduced construction; they do not fix the speed for New Zealand. 2035 is the common adoption window of the
  model; the speed is bracketed by the sensitivity rows. References with verification status: `docs/REFERENCES.md`
  (DiPasquale & Wheaton issue number and Gabriel & Nothaft year are marked [verify]).

## §2 The lever rule

* Levels 1–4 after DECC (2010), DESNZ (2023) and EUCalc D2.5: Reference = Level 1, Moderate = Level 2, Ambitious =
  Level 3, TL = Level 4.
* **Ambitious sub-rules** (first applicable): A, a case-study distribution → Harrell-Davis q0.15 (the top-15%
  convention of the EU Taxonomy) with a percentile bootstrap interval; B, an NZ record without a structural trend →
  the best value ever observed; C, otherwise a published reference value (official projection > legislated target >
  peer-reviewed scenario > peer-country value).
* **Moderate is the exact midpoint** of the native parameter (λ = 0.5; per year for the path levers L3 and L7);
  tested to 1 ulp. **TLn ≥ Ambitious** for every lever, asserted (`levers.tl_strength`).
* **Adoption:** every level, TL included, on the logistic 2026 → 2035. **λ-sweep** of each lever (ED10).

## §3 The nine levers

| lever | sub-rule | anchor (Ambitious unless stated) |
|---|---|---|
| L1 Dwelling size | B | consent-size minima 1990–2025: Detached 148.8 m² (1990), Townhouses 105.8 m² (1990), Apartments 91.0 m² (1998); f_amb = 0.372 / 0.097 / 0.162 |
| L2 Design density | A | r = 0.8194 (HD q0.15 of the 16 case-study OLF ratios; bootstrap CI about 0.73–0.96), Moderate 0.9097 |
| L3 Household size | C | Stats NZ High − Medium gap (held after 2043): 2050 Reference 2.6518, Moderate 2.6725, Ambitious 2.6933 |
| L4 Vacancy | B | 1996 census minimum, one definition: Ambitious 4.013%, Moderate 4.700% |
| L5 Building lifetime | C | demolition and the surge × (1 − 0.40) |
| L6 Material carbon | A | r = 0.8270 (HD q0.15; CI 0.607–0.950), Moderate 0.9135 |
| L7 Construction-stage carbon | C | A4–A5 linear to zero by 2050 |
| L8 Soil-aware planning | C | soil carbon loss per m² × (1 − 0.146) |
| L9 Brownfield development | C | s = 0.59 (England 2018–21); s_ref = 0.1792 (v3 Reference), Moderate 0.3846 |

Decisions:

* **L1 full-strength year.** The occupied reference area is taken at 2035, occ_ref = S(2035) × OLF, the year the
  lever reaches full strength, so that the Ambitious size at full strength equals the recorded minimum.
* **L1 / L2 interaction.** L2 scales OLF and dwelling size; L1 then removes its share of the L2-scaled extra-space
  margin (tested).
* **L2 sample check.** n = 16 with all three typologies (STOP condition).
* **L9 at λ = 0** is the lever off (the Reference). A constant s = s_ref would not be neutral: it would act in the
  years whose own replacement share is below s_ref. This is recorded in `levers.json`.
* The v2.1 lever "Overbuild absorption" is removed: absorption is now Reference behaviour. The map from v2.1 lever ids
  to v3: `docs/RENAMING.md`, section 11.

## §4 Theoretical limit and re-occupation

* TL = every lever at Level 4, adopted by 2035. TL1 No extra space; TL2 Densest design; TL3 Historical maximum
  household size (target max(2.7905, S + gap)); TL4 No vacancy; TL5 No demolition; TL6 Best-practice materials;
  TL7 Zero-emission construction; TL8 Lowest-carbon soils; TL9 All brownfield.
* **One run order for every run:** gross → overbuild payback → re-occupation → built.
* **Re-occupation:** the dwellings released by TL3 (R3) and TL4 (R4) meet a constant share s of each year's need;
  a year whose share exceeds the cumulative release builds the shortfall, and s is recomputed over the remaining
  years. Log: `pathways/reoccupation_log.csv`; `surplus_vacant_2050` in `runs.csv`.
* TL: R3 = 0, R4 = 117,044, G+ = 354,466, s = 0.330; the release binds in 2027; need is non-positive (no building)
  in 2031–2032. TL carbon 4,358 kt (LoE AR 0.979, AtP 3.92; −78.9%).
* **R3 = 0 under the logistic TL.** TL3 raises household size, so households fall only in a year where the rise in
  household size outpaces population growth. On the logistic path this never happens (the smallest yearly change in
  households in the TL run is +2,565), so all release comes from TL4. Under the instant TL the 2027 step does release
  households (R3 = 62,085).
* **Attribution of re-occupation is proportional to R3 : R4** (`reoccupied_tl3`, `reoccupied_tl4` in the log).
* **Waterfall:** Reference → P1 … P4 (= P5) → TL1 … TL9 (= TL), by band, at Moderate (Fig5) and Ambitious (ED7).
  The **instant TL** (every limit from 1 January 2027) is a sensitivity row only: 3,020 kt, LoE AR 0.679 (R3 62,085,
  R4 114,399, s 0.454).
* **Shapley games:** pathways (16 subsets) and levers (512) at Moderate and Ambitious; the nine levers at TL from the
  Reference (Fig8); TL1–TL9 from P5 Moderate (ED8).
* **Ordering:** no parameter violation; reversals of *annual* carbon between levels are reported, not STOPs, because
  the rule orders the parameters and the cumulative totals (L3 Ambitious ≥ TL in 2039–2043, at most 64 kt a year;
  L4 in 2031). Cumulative ordering holds for every lever.

## §5 Compute / draw separation and drawing rules

* Model scripts (`projection.py`, `Diagnostics.py`, `boundaries.py`, `MonteCarlo.py`, `pathways.py`,
  `pathways_mc.py`, `tools/figures_report.py`, `engine.py`, `levers.py`) write CSV / JSON only. Arrays a figure needs
  that are not otherwise exported go to `outputs/data/figure_source/` (`figsource.py`).
* `figures/` package: `style.py` (moved from the root; palette registry), `draw.py` (sign rules), `audit.py`
  (moved), `data.py`, `index.py` (FIGURES.md), `__main__.py`, one module per group. `paper.py`, `extended_data.py`,
  `key_figures.py` and `plotting.py` are deleted.
* `--figures-only` redraws from the data and stops unless every data file is byte-identical (SHA-256).
* Sign rules: time series stacked up and down from zero with a net line; cumulative bars with negative bands as
  outlined, unfilled segments hanging from the top of the positive stack, ending at the net with a tick. Material and
  stage values are never negative (STOP). Only the surge band is hatched. AR solid, AtP dotted, with zones.
* **Palette re-tuning.** The new bands and L2 needed colours. The colours were searched to pass the CVD check
  (`tools/palette_check.py`): L2 `#944E02`, Overbuild absorbed `#8D5D93`, Unconsented additions `#BA9AC1`, Released
  dwellings (TL) `#95C283`, maintenance `#9E9E9E`. The Low scenario grey and the D05 new-households grey were changed
  (`#B5B5B5`, `#B0B0B0`) so that the maintenance grey is unique, which removed a false positive of the maintenance
  audit. Every group reaches the threshold of 10 except the documented boundary-zones exception.

## §6 Outputs

* `outputs/paper_main/` Fig1–Fig8; `outputs/paper_extended/` ED1–ED14 and EDT1; `outputs/diagnostics/{calibration,
  validation, boundaries, pathways, montecarlo, sensitivity}`; `outputs/FIGURES.md` generated from
  `figure_plan.py` and the audit. `outputs/paper/`, `outputs/extended_data/` and `outputs/key_figures/` are deleted.
* **Retired figures:** the schematic Fig1 (the levers are in Table 1); K1–K6 (their content is in Fig1–Fig8); D11
  (identical to D10 after the replacement split); D30 (now ED11). D20 Sobol is drawn in the full profile only.
* **The frozen-technology check run is dropped** from the pipeline: it was a v2-era check run (a second pass of the
  whole Reference at 2025 factors, data only) that no v3 figure or table reads. The frozen-technology case remains a
  one-at-a-time sensitivity row ("Frozen technology: 2025 factors held").

## §7 Tests and documents

* New: `test_reference_legacy.py` (legacy lock), `test_model_v3.py` (model rules and STOP conditions),
  `test_figures_v3.py` (compute / draw separation, palette, sign rules, audit, figures-only), `test_profiles.py`,
  `test_regression_model_v3.py` (deterministic hashes identical in both profiles; Monte Carlo hashes per profile;
  captured by `tests/capture_regression_model_v3.py`). `test_identities.py` updated for the new bands.
* **Retired** to `tests/retired/` (not collected): the v1, v2, v2.1 and v1.2.1 locks, the data-unchanged and byte
  manifest tests, and the v2-era pathway, Monte Carlo, release, release-map, sensitivity-table and palette tests.
  Reason: MODEL v3.0.0 changes the Reference and the lever rule on purpose, so the earlier locks cannot hold. The
  link to v2.1 is kept by the legacy lock; their v3 counterparts are the tests above.
* **Restored** (they test components MODEL v3.0.0 does not change): the AESA equations against their sources
  (`test_aesa.py`, from `test_pb.py`) and the time-resolved B2/B4 events and committed emissions (`test_events.py`,
  from the baseline-pb-v3 `test_v3.py`). The two captured anchors of baseline-PB_v2 are checked on the MODEL v2.1
  Reference (`OVERBUILD_ABSORPTION_END = None`, itself locked by the legacy lock); the identity "in-window + committed
  = whole life at 2025 factors" now runs on the v3 Reference; the historical-carbon figure check uses the v3 folders
  and exempts D29, whose panels plot dimensionless lever parameters (the L7 A4–A5 factor path is anchored at
  2025 = 1).
* Documents: this file, `RENAMING.md` (section 11), `PALETTE.md`, `METHODS_DRAFT.md`, `REFERENCES.md`,
  `FIGURE_PLAN_v3.md`, `LEVERS_TABLE.md`, `PROJECT_STATE_v3.md`; README and ARCHITECTURE updated.

## Fixes found by the full-profile run

* `indexes.py` walked the whole of `outputs/` and so listed the git-ignored `outputs/_light/` mirror as unindexed
  files; the mirrors (`_light`, `_legacy`) are now excluded.
* The figure audit (`figures/audit.py`) took any x value between 1900 and 2100 as a calendar year, so the Monte
  Carlo convergence diagnostic D37 (x = number of draws, up to 5,000) was flagged by the historical-carbon check.
  An x-axis whose label names another quantity is no longer read as years. Only figures were affected: the figures
  were redrawn with `--figures-only`, which confirmed every data file byte-identical (98 files, full; 97, light).
  `outputs/run_meta.json` keeps the timings of the pipeline run.

## Checks (STOP conditions)

| condition | result |
|---|---|
| legacy lock | passes (worst difference 0) |
| material / stage values negative | none |
| ordering violated | none (annual reversals reported above) |
| Shapley efficiency error > 1e-9 | none |
| L2 sample ≠ 16 or typology missing | n = 16, three typologies |
| f_t outside [0, 1] | none |
| High < Medium (household size) | none |
| cumulative re-occupied > released | none |
| built_t < 0 | none |
| TLn weaker than Ambitious | none |
| excess differs between runs | 0.0 |

---

# MODEL v3.1.0: changes and decisions

Branch `release/model-v3.1.0`, created from `release/model-v3.0.0`. Minimal, targeted changes: inventory emissions
accounting (A1), one release-accounting convention (A2), the history split (A3), two report-only rows (A4, A5) and the
figure fixes (B1–B3). Numbers are from the full profile (deterministic numbers are identical in both profiles).

## A1 Emissions accounting (`inventory.py`; `ACCOUNTING`)

* `ACCOUNTING` ∈ {`inventory` (default), `instant`, `cohort_window`} in `projection.py`; environment override
  `PATHWAY_ACCOUNTING`. The v3.0 constant of the same name (the life-cycle timing: in-window / whole life) is
  **renamed `LIFE_CYCLE_TIMING`**; the whole-life sensitivity row (xii) now runs `LIFE_CYCLE_TIMING = whole_life`
  on the instant rule, as in v3.0.
* Scope: residential construction since `B_SCOPE_START = 1992` on both sides (base and projection). Soil carbon of
  converted land is emitted linearly over `SOIL_OXIDATION_YEARS = 20` years from the conversion year (IPCC 2006,
  Vol. 4, Ch. 2, default transition period; NZ GHG Inventory land-use change convention [verify]).
* **inventory**, AR base 2016–2025: upfront A1–A5 of the window's construction + soil tails of 1997+ conversions
  emitted in the window + B2/B4 of every cohort since 1992 occurring in the window. Projection 2026–2050: upfront +
  in-window soil of 2026–2050 conversions + the tails of 2007–2025 conversions over 2026–2044 + the B2/B4 of the
  1992–2025 cohorts (on each run's decarbonisation paths). The pre-2026 part is the band **Legacy (pre-2026
  activity)** (soil and B2/B4 kept separately in the data: `carbon_legacy`, `legacy_soil_kt`, `legacy_b2b4_kt`);
  the soil of 2026–2050 conversions oxidised after 2050 is the committed component **Soil, after 2050**.
* **instant** reproduces MODEL v3.0.0 (soil at conversion, B2/B4 of each window's own cohorts). It is used by the
  legacy lock (`PATHWAY_REFERENCE_LEGACY` now also forces `instant`) and the A2 equivalence test.
* **cohort_window** (20-year oxidation, own cohorts only, on both sides) is deterministic only and **rejected**:
  a 10-year base window and a 25-year projection capture different shares of slow-release emissions.
* Base-window sensitivity rows use the same rule as the adopted base, with a `soil_tail_coverage` column (`full` /
  `partial` where tails reach before 1992). The adopted 2016 window needs conversions from 1997: covered (no STOP).
* Monte Carlo: AR and AtP are recomputed per draw on the rule (`mc_runs(..., rule)`); the legacy soil is fixed
  (observed history; soil factors are not drawn); the legacy B2/B4 follows each draw's bootstrap of the case-study
  event profiles (`INV.legacy_b` per building, `boot_legacy_b`), on the central history, as the per-draw AR base
  does. The per-draw TL is also evaluated on the instant rule against `B_AR_instant` to report its share.
* `engine.forward(..., soil_spread=None, legacy=None)` reproduces v3.0 bit for bit with both None (the summation
  order of the v3.0 carbon total is kept; a 1-ulp difference found during development was fixed this way).

| (full profile) | inventory | instant | cohort_window |
|---|---|---|---|
| AR base (kt/yr): total / upfront / soil / B2B4 | 1558.0 / 1226.8 / 175.8 / 155.4 | 1423.0 / 1226.8 / 192.6 / 3.5 | 1285.4 / 1226.8 / 55.1 / 3.5 |
| AR budget 2026–2050 (kt) | 4873.6 | 4451.0 | 4020.9 |
| AtP budget 2026–2050 (kt) | 1113.0 | 1113.0 | 1113.0 |
| Reference carbon (kt) | 26142.7 | 20614.9 | 19590.5 |
| of which upfront / soil / B2B4 / legacy | 17340.5 / 1875.0 / 375.1 / 6552.2 (soil 1709.0 + B 4843.2) | 17340.5 / 2899.3 / 375.1 / 0 | 17340.5 / 1875.0 / 375.1 / 0 |
| Soil, after 2050 (kt, committed) | 1024.4 | 0 | 1024.4 |
| LoE AR: REF / P5 Mod / P5 Amb / TL | 5.364 / 4.321 / 3.529 / 2.239 | 4.631 / 3.386 / 2.453 / 0.979 | 4.872 / 3.608 / 2.648 / 1.084 |
| LoE AtP: REF / TL | 23.49 / 9.80 | 18.52 / 3.92 | 17.60 / 3.92 |
| MC share of draws with TL within AR | 0.000 | 0.551 | n/a (deterministic only) |

Written by `tools/accounting_rules.py` to `outputs/data/sensitivity/accounting_rules.csv` (a new `run_all` step after
`sensitivity_tables`). Under the adopted rule the legacy alone is 1.34 × the AR budget, so no 2026–2050 pathway can
reach LoE AR ≤ 1 (Fig6).

## A2 One release-accounting convention (`bands.py`; `pathways.run`)

* Positive bands are always gross need; each release is its own negative band (Overbuild absorbed, Unconsented
  additions, **Vacancy released** (new), Released dwellings (TL)); no netting, no rescaling. Retirement-village units
  are removed from each band by the exact factor (1 − RV share); the 2026 observed-GFA adjustment sits on the
  overbuild band. (v3.0 rescaled bands to fit; removed.)
* An amount that cannot be used in a year (gross need minus releases < 0) is carried forward; whatever remains in 2050
  is booked against its release band and as **Surplus kept vacant (2050)**, so the bands sum to the floor area and
  carbon totals every year (checked to 1e-9; `bands.check`). The negative-gross residual (census identity) is carried
  the same way.
* TL-family runs (TL, TL waterfall steps, every TL Shapley subset): the re-occupation pool holds every dwelling
  release in the run. Non-TL runs: vacancy releases are used in-year, capped at the year's gross need, the rest
  carried. The gross vacancy band is never negative (STOP if it were); years where households fall are logged
  (`households_fall_years`).
* Soil-bearing indicator per band follows `soil_on_replacement` (with the sensitivity setting `True`, replacement
  bands bear soil; a check failure on that row during development was fixed this way); the brownfield factor phi
  makes the bands carry exactly the engine's soil.
* **Equivalence** (`PATHWAY_ACCOUNTING=instant` against the v3.0 light snapshot): every Reference, lever (L1–L9),
  pathway (P1–P5) and TL total identical (52 runs, max difference 0.0). What changes, as intended (TL pool now holds
  the vacancy release in every TL-family subset):
  * TL waterfall steps (kt): Moderate TL1 +92.1, TL2 +95.8, TL3 +97.2; Ambitious TL1 +199.9, TL2 +201.5, TL3 +185.9;
    TL4–TL9 and TL unchanged.
  * TL1–TL9 Shapley values from P5 Moderate (carbon, kt): TL1 −13.5, TL2 −10.7, TL3 −7.5, TL4 +76.5, TL5 −4.0,
    TL6 −12.7, TL7 −8.1, TL8 −8.8, TL9 −11.3 (sum 0, efficiency holds). LoE values change proportionally.
    Moderate/Ambitious P- and L-games unchanged.

## A3 History split (`validation.history_bands`)

* The residual of the history is split into **net replacement (census)** (interval rate of the census identity ×
  previous stock × dwelling size; may be negative), **retirement villages** (negative, out of scope) and
  **unexplained building** (the remainder to the observed floor area). Bands sum to the observed floor area in every
  year (1e-9); no rescaling. `history_replacement_split` (v3.0) is retired and its CSV removed.
* Unexplained building 1992–2025: **−4,345 dwellings (−0.52 % of 828,537 built)**; floor-area remainder and the
  stock-identity dwellings × size agree to 1.4e-15 Mm² (`baseline/history_unexplained.json`).

## A4 / A5 report-only rows

* A4 `TL-reoccupation-fast` (re-occupation as fast as demand allows, `reoccupation(rule='fast')`): 10,624.8 kt,
  LoE AR 2.180 (TL 10,909.8 kt, 2.239); zero-building years 2029–2038.
* A5 r_L6 with A_1 (n = 15): r = 0.841 (bootstrap CI 0.619–0.955) vs adopted 0.827 (n = 14); check only.

## B Figures (`--figures-only`; data byte-identical)

* Fig5/ED7: true sequential waterfall Reference → P1..P4 → P5 → TL1..TL9 → TL; reductions filled downward,
  increases outlined upward, Δ kt labels; legacy as the base of the end bars; AR/AtP lines and zones.
* Fig6: single panel, analytic LoE_AR(x, y) = [C_2026 + C_legacy + C_ref,2027–50 (1−x)(1−y)] / B_AR
  (`fig6_loe`); AR solid red, AtP dotted; zones; contour labels in LoE AR; markers at the effective coordinates,
  clip_on=False; marker test at 1e-9. The figure audit records markers outside the plotted boundary
  (`boundary_outside`) instead of failing.
* ED5b: population threshold (univariate logistic, bootstrap CI). Under the adopted rule no draw reaches TL within AR
  (no events), so ED5b shows a note and the LoE-vs-population scatter; the instant-rule threshold, 6.651 M
  (CI 6.648–6.654 M; Firth, separation), is reported in the note. ED5a uses categorical Q1–Q5.
* Fig1: A3 split, legend only for bands present. Fig2/Fig3/Fig4/D25: legacy band in neutral grey (registered in
  `figures/style.py`, distinct from maintenance). Fig3: "Soil, after 2050" segment. Fig8 caption as specified.
  D37 distinct styles; D38 shows the resulting A1–A3 factors per typology (`montecarlo/carbon_factors_REF.csv`,
  written by `pathways_mc.py --carbon-factors`); D40 readable labels; D07 "BRANZ demolition (component of the
  long-run rate)"; D29 L3 caption; ED11 footnote on A_1 with the A5 value; ED8c caption.
* Palette: the new colours were set by a coordinate-ascent search maximising the minimum CAM02-UCS distance under
  every simulated deficiency within each figure group (`tools/palette_check.py` groups, plus the waterfall end bars
  Reference / P5 / TL), each colour constrained to its hue family, then a local refinement of the two colours that
  limited the minimum: Vacancy released `#481870` (dark mauve, the vacancy family), Surplus kept vacant (2050)
  `#D1E6C1` (pale), Legacy `#858277` (neutral warm grey, distinct from Maintenance `#9E9E9E`), Soil after 2050
  `#C9B49A`, Retirement villages (history) `#4E463E`. Every group now meets the distance threshold of 10 except the
  boundary zones (pale by design, unchanged since v2.1.2; `docs/PALETTE.md`).
* Fig3b: the band bar no longer normalises the gross positive bands to the total (that was an implicit rescaling,
  against A2): the bands are drawn at their size and the release bands hang down as outlines to the total
  (`draw.bars_cumulative`), so legacy has the same height in the band, material and stage bars.
* `--figures-only` (full and light): every data file byte-identical (100 files full, 99 light).

## C Documents

* `METHODS_DRAFT.md` part 4 (`tools/accounting_methods.py`): A1 (inventory default and why; scope; instant and
  cohort_window as sensitivities; why cohort_window is rejected), A2, A3, the replacement wording and the
  completion-rate two-piece uniform rationale.
* `REFERENCES.md`: emissions-accounting section; DiPasquale & Wheaton (1992), Gabriel & Nothaft (2001, distinct from
  1988), IPCC 2006 Vol. 4 Ch. 2, NZ GHG Inventory, Jones, Greenaway-McGrevy & Crow (2024), Wallis (2014).
  Crossref was not reachable from the build environment, so entries not verified against a DOI are marked [verify].

## Other code changes

* `naming.py`: new bands/components/stages (`vacancy_released`, `surplus_vacant`, `legacy`, `soil_after`),
  `BANDS_IN_SCOPE`, `BANDS_HISTORY`. `export_results` adds `bands_in_scope`, `legacy_kt`, `soil_after_2050_kt`.
* `pathways.linear_split` / `scaled_carbon`: the fixed part is the 2026 cohort + legacy (Fig6 analytic plane).
* `pathways` checks: legacy identical across all runs (STOP; `legacy_max_rel_diff_between_runs`).
* Development fixes: Firth guard for zero events (`population_threshold`, `estimable`), retired-key fixes in
  `pb_methods` and validation, legacy colour and stage in Fig2/D13.
* Timings (full compute, s): total 1316.8; montecarlo 156.8, boundaries 279.2, pathways 15.2, pathways_mc 781.4,
  accounting_rules 9.6.

## Tests (v3.1)

* New `tests/test_model_v3_1.py`: A2 equivalence (every one of the 52 v3.0 runs recomputed in process on ACCOUNTING
  'instant': floor area, carbon, LoE AR, LoE AtP and B_AR equal to 1e-9; fixture `tests/fixtures/v3_0_totals.json`,
  captured from `outputs/data/pathways/runs.csv` at the v3.0.0 commit d084e09 by `tests/capture_v3_0_totals.py`);
  legacy identical in every run; band sums (projection, every pathway run, history) to 1e-9; gross vacancy band >= 0,
  release bands <= 0, surplus only in 2050; Fig6 analytic LoE at every marker = the run's LoE AR (1e-9); soil
  kernel conservation; the accounting-rules table.
* v3.1 lock `tests/regression_model_v3_1.json` (30 deterministic files, adds the history bands and the unexplained
  sum; Monte Carlo hashes for both profiles); the v3.0 lock file is kept for the record.
* Updated for the v3.1 accounting (each difference checked first, never loosened):
  * the legacy v2.1 lock runs with `ACCOUNTING = 'instant'`, as `run_all.py --reference-legacy` does (it passes);
  * three carbon identities (stages + soil, demand bands by material, in-scope figure bands) add the legacy term: their
    gap was exactly the legacy, 6,552.19 kt;
  * the B-timing identities of `test_events.py` (within window + committed = whole life; soil unchanged) run on the
    instant rule they describe; new `test_inventory_soil_conserved`: inventory soil in the window + soil after 2050 =
    instant soil (1e-12), upfront unchanged;
  * `test_aesa.py`: the AR base on the projection's rule (`boundaries.window_base`);
  * `test_soil.py`: conversions and emitted soil separately (`soil_conv`, `inventory.spread`);
  * `test_figures_v3.py`: `vacancy_released` among the negative bands; a boundary outside the plotted range may be
    stated instead of drawn (Fig6, `boundary_outside`).
* Result: 202 passed, 2 skipped (the local-only AESA workbook), in both profiles. A first pass, run once, showed the
  six stale tests above; nothing in the model was changed to pass them.

## Checks (STOP conditions, v3.1)

| condition | result |
|---|---|
| legacy v2.1 lock (instant) | passes (1e-12) |
| A2 equivalence (every L/P/Reference/TL total, instant vs v3.0) | passes (max difference 0.0) |
| history coverage for the default rule | full (2016 window needs 1997+) |
| legacy band differs between runs | no |
| material / stage values negative | none |
| ordering / Shapley efficiency | holds |
| built ≥ 0 / band sums | holds (tests) |
