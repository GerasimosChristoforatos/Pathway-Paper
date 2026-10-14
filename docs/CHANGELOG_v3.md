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
  22.6 min; v2.1.2 figures-only about 10 min; v3 light figures 38 s for 61 figures). Full-profile timings are in
  `outputs/run_meta.json`.

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
