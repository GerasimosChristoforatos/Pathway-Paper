# CHANGELOG

## pathways-v1

PATHWAYS v1: five levers on new residential construction, their bundles, an
order-free attribution, and the gap to the climate-change boundaries. A layer on
top of baseline-pb-v3.1; no model file changes (engine.py, Boss.py, events.py,
aesa.py, PB.py, MonteCarlo.py, Building_factors.py and the existing tests are
untouched). New: `levers.py`, `pathways.py`, `tools/pathways_methods.py`,
`tests/test_pathways.py`, `outputs/pathways/` (HOOKS.md, pathways_runs.csv,
pathways_annual.csv, pathways_bands.csv, shapley.csv, shapley_subsets.csv,
backcast.json, solution_space.csv, levers.json, PATHWAYS_METHODS_DRAFT.md),
figures pw_1-pw_6.

**Regression locks.** With every lever off the run reproduces the reference
central run (annual carbon, upfront, in-window B, floor area by typology, demand
bands, committed range, cumulative LoE AR 4.85 / AtP 19.4; maximum relative
difference 4.4e-16); each lever at zero strength is the baseline; every baseline
output is byte-identical to tag baseline-PB_v3.1 (tests/test_pathways.py and
`git diff --stat baseline-PB_v3.1 -- outputs/`: changes only under
outputs/pathways/).

**Levers** (Moderate / Ambitious; ramp 1/9 in 2027, full from 2035; 2026 observed
and unchanged; near-term excess frozen except under L2):

* L1 new-dwelling size: -6.5% all typologies (Pellan et al. 2024) / the 1991-1995
  realised size (detached -4.74%; townhouses and apartments held: their 1991-95
  sizes exceed today's, so A is weaker than M).
* L2 existing stock: vacancy 5.39% -> 4.7% / 4.0% (1986-2023 consistent census
  range 4.01-5.38%) and near-term surplus absorbed at 0.10 / 0.20 a year.
* L3 lifetime extension: demolition and the redevelopment wave -20% / -40%
  (Pellan et al. 2024; Pauliuk et al. 2024); renovation carbon not modelled.
* L4 typology mix: attached floor-area share 39.4% -> 41.4% (peak 2023) / 55.4%
  (+16 points, Pellan et al. 2024).
* L5 best-practice materials: A1-A3 x r on top of decarbonisation, r detached
  0.829 / 0.530, townhouses 0.915 / 0.880, apartments held.

**Results** (S3-10, 2026-2050; committed after 2050 as a range):

| run | floor area (Mm2) | carbon (kt) | committed (kt) | LoE AR | LoE AtP | carbon vs P0 |
|---|---|---|---|---|---|---|
| P0 | 89.57 | 21,578 | 8,208-8,969 | 4.85 | 19.4 | +0.0% |
| P1-M / P1-A (Avoid) | 76.90 / 73.92 | 18,584 / 17,881 | 7,047-7,700 / 6,786-7,416 | 4.18 / 4.02 | 16.7 / 16.1 | -13.9% / -17.1% |
| P2-M / P2-A (Shift + Improve) | 88.85 / 84.14 | 20,218 / 18,468 | 8,137-8,880 / 7,674-8,296 | 4.54 / 4.15 | 18.2 / 16.6 | -6.3% / -14.4% |
| P3-M / P3-A (all five) | 76.29 / 69.78 | 17,428 / 15,365 | 6,987-7,624 / 6,375-6,893 | 3.92 / 3.45 | 15.7 / 13.8 | -19.2% / -28.8% |

Shapley shares of P0 - P3 (carbon, M / A): L1 23% / 4%, L2 35% / 35%, L3 12% / 16%,
L4 2% / 4%, L5 29% / 41%. Back-cast: cumulative LoE AR = 1 needs 2027-2050
construction cut by 78.3% from P3-A (k = 0.2173; 83.4% of P0's 2027-2050 floor
area), or by 85.0% from P0; AtP is not attainable within the window (2026 alone
gives a cumulative LoE AtP of 1.28).

**Tests**: 101 passed, 2 skipped (the reproduction tests that need the git-ignored
author workbook; full run). **Run time**: full run 1,280 s on 4 cores (pathways
step 16 s), `--quick` 526 s; pinned environment (requirements.txt), in which the
unchanged baseline run also reproduces every tracked output of baseline-PB_v3.1
byte for byte.

## baseline-pb-v3.1

Figure and label clean-up only. No model result, method or test baseline changes:
metrics.json, every Monte Carlo, PB, scenario and reconciliation output and
RESULTS.md are byte-identical to baseline-pb-v3. sensitivity_oat.csv differs only
in the relabelled rows below and the removed "Accounting: whole life at
construction" row (an accounting convention, not a parameter; it stays in
pb_sensitivity.csv and pb_4_sensitivity_SI: carbon / LoE AtP +41.8%, LoE AR +1.5%).

* **Material figures** (boss_10, diag_5): replacements & repaints within 2026-2050
  merged into their material colour (no separate lighter / hatched layer or legend
  entry; totals unchanged); soil on top, hatched, as before.
* **mc_1_fan / mc_1_fan_pb**: the replacements & repaints band and its legend entry
  removed; carbon axes start at 2026 (mc_1_fan_pb: at the 2016 AR base window); the
  floor-area panel keeps its history.
* **Tornados** (sens_1, pb_4, main text): the 5 parameters with the largest absolute
  effect (sens_1: on carbon; pb_4: on AR or AtP), with both ends of paired
  parameters shown (population 5th / 95th, Low / High replacement, single case
  study lowest / highest, soil order Raw / Organic, AR base windows, ...).
  Captions and figure notes add: "Percentages are relative to within-window carbon
  (2026-2050); fixed absolute terms such as soil carbon therefore show larger
  percentage effects than under whole-life accounting."
* **Labels** (sens_1, sens_1_SI, sens_2, sensitivity_oat.csv; the PB labels had no
  version tags), old -> new:
  - "Stats NZ 5th / 95th percentile (level)" -> "Population: Stats NZ 5th / 95th percentile"
  - "Stats NZ Low / High projection variant (S)" -> "Household size: Stats NZ Low / High variant"
  - "S after 2043: flat (kink at 2043)" -> "Household size after 2043: flat (kink at 2043)"
  - "S after 2043: secant-slope taper (v1.2)" -> "Household size after 2043: secant-slope taper"
  - "S after 2043: taper from the PCHIP end slope" -> "Household size after 2043: taper from the PCHIP end slope"
  - "Booked as redevelopment, stock-neutral (v1.1)" -> "Booked as redevelopment, stock-neutral"
  - "Soil: lowest / highest soil order (Raw / Organic)" -> "Soil carbon: lowest / highest soil order (Raw / Organic)"
  tests/test_regression_v1_2_1.py maps the old labels to the new (values unchanged).
* **Cosmetic fixes**: boss_10 panel titles no longer overlap; diag_5 suptitle
  shortened; mc_1_fan carbon title on two lines; mc_1_fan_pb legend no longer covers
  the base-window line, stale caption reference to mc_1_fan history removed; pb_5
  axis starts at 2026 (no empty 2025 column); pb_6 caption no longer overlaps the
  tick labels, boundary labels now drawn (were clipped), duplicated legend wording
  removed; fig_scenarios_pb bar legend moved below the panel (was covering the AtP
  label); pb_3 caption wrapped (the figure was 4,300 px wide); pb_4 labels wrapped
  with a subtitle; sens_1 note spacing; fig_conversion_chain subtitle and caption
  updated (intensity also reflects A4-A5 decarbonisation and in-window replacements
  & repaints).
* **Tests**: 87 passed (full run); new: top-5 parameter selection, whole-life row
  only in the PB sensitivities. **Run time**: full run 1,037 s on 4 cores (v3: 880 s;
  same steps minus one Sensitivity case, so the difference is machine load).

## baseline-pb-v3

Time-resolved replacement and repaint emissions (B2, B4), committed post-2050
emissions, and A4-A5 decarbonisation. Unchanged: demographics, floor area, the
three scenarios (Low S1 / Reference S3-10 / High S2), the AESA framework (AR,
Horup et al. 2025 Eq. 1; AtP, Hjalsted et al. 2021 Eqs. 5-6 with α; carrying-capacity
pair A), the A1-A3 item-level mapping, soil (never decarbonised).

**Regression locks.** With `ACCOUNTING = 'whole_life_at_construction'` and
`DECARB_A45 = 'held'` the model reproduces baseline-pb-v2 exactly (carbon, upfront,
annual carbon; `tests/test_v3.py` against `tests/regression_pb_v2.json`), and with
`DECARB_MODE = 'none'` the frozen anchor; the frozen-technology PB run
(`outputs/frozen/pb_results.json`) equals baseline-PB_v2 in every deterministic and
MC cumulative LoE and in the AR base.

**Results** (deterministic; MC p5-p95 in brackets):

| 2026-2050 | v2 (whole life at construction) | v3 (time-resolved, reported) |
|---|---|---|
| Reference carbon (kt) | 31,013 (upfront 21,592) | 21,578 within the window = upfront 21,174 + replacements & repaints 403; committed after 2050 8,208-8,969 |
| Low (S1) carbon (kt) | 29,083 (upfront 20,327) | 20,311 = 19,938 + 373; committed 7,630-8,338 |
| High (S2) carbon (kt) | 33,799 (upfront 23,412) | 23,361 = 22,937 + 424; committed 9,069-9,911 |
| Ī_sec,base 2016-2025 (kt/yr) | 1,987.5 | 1,423.0 (same accounting rule as the projection; at 2025 factors) |
| Reference cumulative LoE AR | 4.99 [4.00-5.92] | 4.85 [3.90-5.75] |
| Reference cumulative LoE AtP | 27.9 [22.1-33.2] | 19.4 [15.5-23.1] |
| Low / High LoE AR | 4.68 / 5.44 | 4.56 / 5.25 |
| Low / High LoE AtP | 26.1 / 30.4 | 18.2 / 21.0 |

AR changes little because the AR base follows the same accounting rule as the
projection (both lose the post-window stages); AtP falls by the share of
whole-life carbon now committed after 2050, since its boundary does not depend
on the sector's history. Committed emissions equal 44.7-48.9 years of the 2050
AR boundary (Reference). Reconciliation with v2 (outputs/reconciliation.md): at
2025 factors upfront + in-window B + committed B + C1-C4 = 33,625.2 kt = the v2
frozen whole-life total exactly; decarbonised, v2 31,013.0 - A4-A5 of
construction 417.2 - in-window B decarbonisation 49.3 = 30,546.5 (committed upper
bound).

* **Event table** (`data/build_lca_events.py` -> `data/derived/lca_events.csv`):
  event counts and building lifespan from the supplied LCAQuick root tables
  (`data/raw/Analytical_LCA_Results_Database.xlsx`, MANIFEST); stage totals stay
  those of `building_data.xlsx` and the item table. 1,287 of 1,303 lines matched;
  16 excluded, none with B2/B4 (12 sand / granular-fill site works, 3 unlabelled
  incl. the A_1 row of ≈408 t A1-A3, one T_1 aluminium line 10 kg off the item
  table). Some sheet summary blocks do not equal their own line sums; line data
  used. Colorsteel: one replacement at L/(n+1) with the full line B; ZinaCore: 3
  repaints of B/3 on the paint path (author decisions).
* **Timing**: event k at k L/(n+1) (sensitivity k L/n); per-event components
  A1-A3 : A4-A5 : C1-C4 in the line's initial proportions; pooled per typology.
* **Accounting** (`ACCOUNTING`): `time_resolved` adopted; `whole_life_at_construction`
  is a sensitivity. Committed emissions: upper at 2025 factors, lower with the
  2050 factors held; C1-C4 at 2025.
* **A4-A5** (`DECARB_A45`): e^(-0.01 (t - 2025)) after Resch, Andresen, Cherubini &
  Brattebø (2021) Table 1; held and item paths are sensitivities.
* **AR base** on the projection's rule, at 2025 factors, for the adopted window and
  the base-window rows; replacements & repaints are 0.25% of the base. Wider
  scope (events of all cohorts since 1992 in base and projection): base 1,574.8
  kt/yr, LoE AR +10.6%, AtP +22.4%.
* **New sensitivity rows** (sensitivity_oat.csv, pb_sensitivity.csv, full
  tornados `_SI`, top-5 regenerated): A4-A5 held (+2.0%), A4-A5 item paths
  (-1.2%), event timing L/n (-0.8%), whole life at construction (carbon +41.8%;
  LoE AR +1.5%, AtP +41.8%), wider scope, AtP with α = 1 "as computed in
  Hjalsted et al.'s SI tables" (AtP -57.8%; limitation: the authors have been
  contacted). The proxies-held and NZ-electricity-held rows stay as ordinary rows.
* **Figures**: no historical carbon in any figure except the AR base window of
  mc_1_fan_pb ("at 2025 factors"); historical_demand_carbon removed; in-window B
  as a band (carbon figures) or lighter and hatched (material figures); new
  pb_6_committed. `figaudit.py` records each figure's year range;
  `tests/test_v3.py` checks it and FIGURES.md against the files. run_all clears
  outputs/figures at the start.
* **Removed** (results preserved at tags baseline-PB_v1.2 and baseline-PB_v2): the
  class-level decarbonisation mode `horup_class_v1_1` (v2 Reference under whole
  life at construction: carbon 31,400 kt, upfront 21,979, LoE AR 5.05 / AtP
  28.2), the stored comparison runs (outputs/modes/, DECARB_MODES.md,
  decarb_modes.json), `run_all.py --compare-modes`, `tools/decarb_modes.py`, the
  lift-at-steel-profile case, `tests/test_regression_pb_v1_1.py`; the unused
  `MIX_MODE = 'storyline'` option; a half-implemented `Boss.B_SCOPE` switch (the
  wider scope remains a PB sensitivity row).
* **Documents**: register rows and limitations for the accounting, events,
  excluded lines, A4-A5 path, committed bounds, history at 2025 factors; Habert et
  al. (2020, Section 5.1, p. 442) cited for time-resolved accounting; the Resch et
  al. author list corrected (Resch, Andresen, Cherubini, Brattebø). "Jones et al.
  2024" (completion rate) remains flagged "citation to verify" (TODO in Boss.py).
  `tools/check_outputs.py` searches all stale terms; `tools/reconciliation.py` new.
* **Tests**: 86 passed (full run). **Run time**: full run 880 s on 4 cores
  (including the frozen-technology check run); `--quick` 348 s.

## baseline-pb-v2

Clean-up, scenario simplification and figure improvements. The AESA framework,
the decarbonisation mapping, the carbon factors, soil and the demographic method
are unchanged.

**Results**: Low (S1) and Reference (S3-10) are unchanged: every Monte Carlo file
of S1 and S3-10 (draws, annual, summaries, Sobol) is byte-identical to
baseline-PB_v1.2, and the deterministic totals and PB results of S1 and S3-10 are
equal (tests/test_v2.py against tests/regression_pb_v1_2_low_ref.json). Only the
third scenario changes, because its MC/PB "S2" is now High (shares held) instead
of the storyline:

| High (S2), 2026-2050 | v1.2 "S2" (storyline: S2 + damped mix trend) | v2 High (S2, shares held) |
|---|---|---|
| Floor area (Mm², deterministic) | 90.81 | 98.74 (= v1.2 "S2-held") |
| Carbon / upfront (kt, deterministic) | 31,548 / 22,255 | 33,799 / 23,412 |
| MC floor area p5 / p50 / p95 (Mm²) | 71.27 / 90.11 / 110.13 | 77.36 / 97.96 / 119.86 |
| MC carbon p5 / p50 / p95 (kt) | 24,526 / 31,279 / 38,652 | 26,339 / 33,468 / 41,374 |
| MC upfront p5 / p50 / p95 (kt) | 17,357 / 22,077 / 27,238 | 18,247 / 23,219 / 28,689 |
| Cumulative LoE_AR (deterministic; MC p5 / p50 / p95) | 5.07; 4.12 / 5.03 / 5.98 | 5.44; 4.42 / 5.40 / 6.39 |
| Cumulative LoE_AtP (deterministic; MC p5 / p50 / p95) | 28.3; 22.78 / 28.05 / 33.58 | 30.4; 24.41 / 30.05 / 35.98 |

* **Three scenarios only** (all with typology shares held): Low (S1), Reference
  (S3-10), High (S2). `Boss.MIX_MODE = 'held'`; the storyline (S2 + damped mix
  trend) and the "S3-10 with the damped mix trend" sensitivity are removed from
  the scenario table, Monte Carlo, Sobol, Sensitivity, PB, figures, metrics and
  documents; the trend code path stays behind `MIX_MODE` (not run or reported;
  ASSUMPTIONS). One naming scheme everywhere. S3-5 and S3-15 stay as half-life
  sensitivities. tools/check_outputs.py (last run_all step) and tests/test_v2.py
  check that no generated output mentions the storyline (the stored
  `--compare-modes` run in outputs/modes/ predates v2: note in DECARB_MODES.md).
* **Regression references updated deliberately** (tests/test_regression_v1_2_1.py):
  the v1.2.1 storyline rows (scenarios S2, S3-10-trend, S2-noUC; sensitivity rows
  "Storyline ..." and "S3-10 with the damped mix trend") are removed; v1.2.1
  "S2-held" is compared under its new key S2 (unchanged values); the frozen High
  MC summary and the S2-noUC row (High without the census UC correction), which
  had no v1.2.1 reference, are pinned in tests/regression_v2_high.json from this
  version's full run.
* **Near-term surplus not absorbed** (author decision after review): the
  persistence rho = 0.52 is a flow persistence (lag-1 autocorrelation of the
  annual departure of building from the calibrated stock identity), already used
  to fade the excess, not a stock payback rate, and the eight census vacancy
  observations do not identify a mean-reversion rate. Limitation added
  (ASSUMPTIONS, BASELINE_DRAFT, near_term_join.md): ≈27,500 dwellings over
  2026-2050 (≈24,600 in 2026-2028); implied vacancy 5.4% -> ≈6.4%, about 1
  percentage point above the 1986-2023 range on a consistent definition
  (4.0-5.4%). diag_3 shades that range and labels the implied vacancy.
* **AR base window**: adopted 2016-2025 (Ī_sec,base 1,987.5 kt/yr). Sensitivity
  rows 2006-2025 (20 yr; 1,651.8 kt/yr; cumulative LoE_AR 6.00, +20.3%) and
  1992-2025 (full consistent history; 1,559.9 kt/yr; 6.36, +27.4%); AtP
  unaffected. The history is consistent with the projection scope from 1992
  (limitations in the PB register). Non-adopted MC band with the 20-year base
  (per-draw base from the saved draws, no new random numbers): cumulative LoE_AR
  p5 / p50 / p95 4.81 / 5.96 / 7.13 (Reference), 4.46 / 5.59 / 6.74 (Low),
  5.30 / 6.49 / 7.70 (High); pb_results.json `mc_base_20yr`.
* **Historical analogue of the near-term excess** (diag_3): per census interval
  (1991-2023; 1986-91 not covered), building beyond the structural requirement
  = vacancy change + (net replacement - long-run replacement), on the consistent
  vacancy definition used by the diag_3 history: -0.2k, +2.1k, -1.6k, +0.8k,
  -5.4k and +6.3k dwellings per year. On that definition the 2013-18 value is
  not driven by the vacancy definition break (vacancy change -2.7k over the
  interval); it reflects net replacement below the long-run rate in the
  household identity.
* **Figures**: material stacks in the six Pride-stripe colours (one order in every
  figure; Timber violet ... Others red), soil faded and hatched on top
  (Boss.material_patch); main-text tornados with the 5 largest effects
  (sens_1_tornado, pb_4_sensitivity) and full versions *_SI; sens_2 gains a
  cumulative-carbon panel and the Stats NZ population 5th / 95th paths, and a
  note on the household-size convergence after 2041 (projections end in 2043);
  pb_5 shows the history 1992-2025 by demand type per census interval (2025
  factors) and the boundaries from 2025; the shading between the AR and AtP
  boundaries is removed from every _pb figure; diag_2 and fig_conversion_chain
  titles corrected.
* **Tests**: 86 pass (storyline absent, scenario names, Low / Reference
  unchanged, tornado top-5 selection, Pride colour order, soil top layer, plus
  the existing suite).
* **Run time**: default full run 925 s on 4 cores (915 s up to the tests step,
  which first failed on the S2-noUC reference above and was re-run after the
  fixture was added, plus 10 s for the report steps).

## baseline-pb-v1.2

**Adopted carbon factors change** (author approval): item-level material
decarbonisation, `DECARB_MODE = 'horup_item'`. The class-level mode of
baseline-pb-v1.1 is kept as `'horup_class_v1_1'` (renamed from
`'horup_material'`; reproduces the baseline-PB_v1.1 outputs exactly) and
`'none'` as the frozen-technology reference (reproduces v1.2.1 / baseline v2).
Floor area, the history, the AR base and the boundaries are unchanged.

| 2026-2050, reference S3-10 | `'none'` | `'horup_class_v1_1'` (v1.1) | `'horup_item'` (adopted) |
|---|---|---|---|
| Embodied carbon (kt CO₂e) | 33,625 | 31,400 | 31,013 |
| Upfront, A1-A5 + soil (kt) | 24,204 | 21,979 | 21,592 |
| MC carbon p5 / p50 / p95 (kt) | 25,743 / 33,268 / 41,644 | 24,119 / 31,095 / 38,863 | 23,833 / 30,715 / 38,391 |
| Cumulative LoE_AR (MC p5 / p50 / p95) | 5.41 (4.33 / 5.37 / 6.42) | 5.05 (4.05 / 5.02 / 5.99) | 4.99 (4.00 / 4.95 / 5.92) |
| Cumulative LoE_AtP (MC p5 / p50 / p95) | 30.2 (24.0 / 29.9 / 36.1) | 28.2 (22.4 / 27.9 / 33.6) | 27.9 (22.1 / 27.6 / 33.2) |
| A1-A3 by 2050 (Detached / Townhouses / Apartments) | 0 | −20.9 / −21.2 / −25.2% | −25.0 / −24.8 / −28.9% |
| Whole factor incl. soil by 2050 | 0 | −9.7 / −11.2 / −18.2% | −11.7 / −13.0 / −20.9% |

Values from `outputs/DECARB_MODES.md` (comparison run 2026-10-05 20:04 UTC at
commit 3bcd7aa). The `'none'` MC LoE bands use the per-draw AR base of v1.1;
with the base fixed they equal baseline-pb-v1.

* **Item table**: `data/raw/epd-level_materials.xlsx` (supplied; MANIFEST) ->
  `data/build_material_items.py` -> `data/derived/material_items.csv`: names
  stripped of leading/trailing whitespace (5 item names, 34 rows), rows of the
  same building x class x item summed; reproduces `building_data.xlsx` for every
  building x class x stage (max relative difference 4.4e-16).
* **Mapping**: `data/material_item_map.csv`, 160 items, each to one S4 row or
  held: 115 direct, 16 by Horup et al. p. 6 (other cementitious and wood-based
  products), 28 proxy (plastics and paint -> EPS; SIP -> EPS; plasterboard ->
  clay brick), 1 held (lift). Share of 2025 A1-A3 direct / p. 6 / proxy / held:
  Detached 74.9 / 6.2 / 18.9 / 0.0%, Townhouses 82.2 / 4.9 / 13.0 / 0.0%,
  Apartments 90.0 / 0.9 / 5.0 / 4.1%. Decisions, the Horup p. 6 quote, the
  NZ low-carbon-electricity criterion and caveat in ASSUMPTIONS.md.
* **Decarbonisation sensitivities of `'horup_item'`** (deterministic; carbon and
  both cumulative LoE change by the same %): proxies held at 2025 +0.3%; NZ-made
  electricity-intensive items held at 2025 +1.7%; lift at steel profile −0.1%;
  class-level mapping of v1.1 +1.2%; frozen technology +8.4%.
* **Run modes**: the default full run keeps `'none'` (frozen-technology check
  run incl. PB; regression) and the frozen-technology sensitivity row
  (sensitivity_oat, pb_sensitivity, pb_4). `python run_all.py --compare-modes`
  runs the class-level mode in full into `outputs/modes/horup_class_v1_1/` and
  the item-level decarbonisation sensitivities (`tools/decarb_modes.py`),
  writing `outputs/DECARB_MODES.md` / `decarb_modes.json` stamped with UTC time
  and commit. RESULTS, BASELINE_DRAFT and PB_METHODS_DRAFT read the stored
  result, state its date and commit, and flag it as stale when the adopted-mode
  carbon differs from the current run.
* **Tests** (78 pass in the comparison run; 74 + 4 skipped in a default run
  without stored class-level outputs): item mapping complete and one-to-one,
  workbook reproduction, class totals at 2025, independent recomputation of the
  pooled reductions, soil / other stages / history unchanged, sensitivity
  cases, `tests/test_regression_pb_v1_1.py` (class-level mode equals the
  baseline-PB_v1.1 outputs exactly), v1.2.1 regression (`'none'`) unchanged.
* **Figures**: every carbon figure of the adopted run is regenerated with the
  item-level factors (boss_05/06/10, diag_5, sens_1, mc_*, fig_scenarios,
  pb_*); floor-area figures are unchanged. pb_4 and sens_1 carry the
  frozen-technology row only; the other decarbonisation sensitivities are in
  DECARB_MODES.md. Captions of sens_1 and pb_4 updated; pb_4 height scales with
  its rows.
* **Run time**: default full run 956 s wall clock on 4 cores; with
  `--compare-modes` 1,448 s.

## baseline-pb-v1.1

**Adopted carbon factors change**: materials are decarbonised (author decision),
so headline carbon and levels of exceedance differ from baseline-pb-v1, which is
now the frozen-technology sensitivity. Floor area, the history, the AR base and
the boundaries are unchanged.

| 2026-2050, reference S3-10 | frozen technology (`'none'`) | adopted (`'horup_material'`) |
|---|---|---|
| Floor area (Mm²) | 89.57 | 89.57 |
| Embodied carbon (kt CO₂e) | 33,625 | 31,400 (−6.6%) |
| Upfront, A1-A5 + soil (kt) | 24,204 | 21,979 |
| MC carbon p5 / p50 / p95 (kt) | 25,743 / 33,268 / 41,644 | 24,119 / 31,095 / 38,863 |
| Cumulative LoE_AR (MC p5-p95) | 5.41 (4.29-6.46) | 5.05 (4.05-5.99) |
| Cumulative LoE_AtP (MC p5-p95) | 30.2 (24.0-36.1) | 28.2 (22.4-33.6) |

* **Material decarbonisation** (`Boss.DECARB_MODE = 'horup_material'`): the
  A1-A3 factor of each case-study material class follows the relative GWP path
  of its counterpart in Horup et al. (2025), Sci. Total Environ. 966, 178780, SI
  Table S4 (average of 9 premise scenarios, relative to 2025; linear between
  2025, 2030, 2040, 2050). Concrete and reinforced concrete -> concrete
  structure; STEEL -> reinforcing steel (steel profile is a sensitivity);
  timber -> construction wood; aluminium, bricks, glass, glass wool -> their S4
  rows; the rest held at 2025. A4-A5, B2, B4, C1-C4, soil and the 1991-2025
  history (the acquired-rights base) always at 2025 factors. Built by
  `data/build_horup.py` and `Building_factors.py`; carried through
  `engine.forward` (per-year intensities), Boss, scenarios, Sensitivity, the
  Monte Carlo (the bootstrap resamples the reduction with the same cases;
  random stream unchanged) and PB. Decisions and limitations in ASSUMPTIONS.md.
* **Frozen-technology check**: `run_all.py` runs Boss, Sensitivity, MonteCarlo
  and the scenario table with `DECARB_MODE = 'none'` into `outputs/frozen/`;
  `tests/test_regression_v1_2_1.py` compares it with v1.2.1 (all files
  byte-identical to baseline-pb-v1).
* **PB Monte Carlo**: the AR base Ī_sec,base is recomputed per draw from the
  draw's 2025 carbon factors on the observed history (5th-95th 1,862-2,116
  kt/yr). Cumulative LoE_AR, S3-10: 4.01 / 5.00 / 6.02 with the base fixed,
  4.05 / 5.02 / 5.99 per draw (p5 / p50 / p95); AtP unchanged. The fixed-base
  bands stay in `pb_results.json` (`mc_base_fixed`).
* **Quick mode** (`run_all.py --quick`, development only): 1,000 Monte Carlo draws
  per scenario (128 Sobol base samples), no frozen-technology Monte Carlo, MC
  regression checks skipped; `metrics.json` (`run_mode`), the generated
  documents and every figure are marked "QUICK RUN, not for reporting". Checked
  against the full run: every cumulative carbon and LoE percentile (p5, p50,
  p95; S3-10, S1, S2) within 0.84%.
* **Figures**: stacked panels are anchored at y = 0 (`Boss.zero_floor()`, which
  checks that every series is >= 0): boss_04, boss_05, boss_05_annual_carbon_pb,
  boss_06, boss_06_cumulative_carbon_pb, boss_10, diag_5, pb_5. Labels and units
  harmonised (CO₂e, m², persons/households); captions state the carbon-factor
  basis; pb_4 gains the frozen-technology and steel-profile rows.
* **Audit fixes**: regression test pinned to `'none'`; `test_soil` uses the
  run's own intensity; ASSUMPTIONS.md no longer lists run-time display switches;
  three unused Boss settings removed; RESULTS/PB methods state the factor
  basis; B_AtP rounding aligned; Hjalsted α limitation added; README run time.
  Open: the completion-rate citation (Jones et al. 2024) is to be supplied.
* **Environment**: the full pipeline of this version under Python 3.12.3 with
  the same pinned packages gives byte-identical outputs (all 57 versioned output
  files) and pixel-identical figures (35) to Python 3.11. Full run 769-770 s on
  4 cores; quick run about 6 minutes; 63 tests pass.

## baseline-pb-v1

A planetary-boundary (AESA, climate change) layer on top of baseline v2.
**The baseline is unchanged**: `tests/test_regression_v1_2_1.py` passes and
every existing key of `outputs/metrics.json` keeps its value; the new metrics
are under the key `pb`.

* **New:** `aesa.py` (pure functions: Horup et al. 2025 Eq. 1; Hjalsted et
  al. 2021 Eqs. 5-6 and SI S1; levels of exceedance), `PB.py` (data, scenario
  and Monte Carlo runs, sensitivities, figures `boss_05/06_*_pb`,
  `fig_scenarios_pb`, `mc_1_fan_pb`, `pb_1`-`pb_5`), `tools/pb_methods.py`
  (`outputs/PB_METHODS_DRAFT.md`), `tests/test_pb.py`.
* **Data:** `data/build_gdp.py`, `build_wpp.py`, `build_wdi.py` build
  `data/derived/` from supplied raw files (Stats NZ GDP(E) SNE022AA; UN WPP
  2024 probabilistic median; World Bank WDI), recorded in MANIFEST.csv.
  `refs/` (papers) and the earlier-manuscript workbook are git-ignored.
* **Changed outside the new files:** `run_all.py` (step `pb` after the Monte
  Carlo, `pb_methods` at the end), `tools/metrics.py` (key `pb`),
  `tools/results.py`, `tools/assumptions.py`, `tools/baseline_draft.py`,
  `tools/figures_report.py` (PB sections and figure entries), README,
  ARCHITECTURE, `.gitignore`. `Boss.py`, `engine.py` and `MonteCarlo.py` are
  not modified.

## Baseline v2

v2 = cleaned v1.2.1. Full development history (every intermediate version,
option, note, equivalence proof and before/after metrics table) at the git tag
`baseline-v1.2.1` (commit a83cf03).

**Results are unchanged.** `tests/test_regression_v1_2_1.py` checks the central
run, the totals of all ten scenarios, the four Monte Carlo summaries and the
sensitivity table against v1.2.1 to 1e-9 (relative). Monte Carlo draws, fans
and Sobol indices are byte-identical. The one sensitivity row removed (the
v1.0.2 three-channel join) is excluded from that comparison.

What changed:

* **Code.** Options that were not used by the adopted run or by a row of the
  sensitivity table were removed: the three-channel near-term join, the
  population-nowcast alternatives, the per-person/per-household consumption
  bases, the household-identity sources of net replacement, the legacy consent
  and census sources, earlier household-size methods and tails, the
  migration-response size path, the full-input Monte Carlo, and related flags.
  Kept: completion lag, payback and gap-vs-2026 variants of the near-term rule,
  household-size tail alternatives, all scenarios, carbon-factor and soil
  bounds.
* **Documents.** Earlier-iteration notes, reviews, equivalence proofs, step
  reports and assessment evidence were removed (they remain at the tag).
  README, ARCHITECTURE.md, FIGURES.md and this file were rewritten;
  ASSUMPTIONS.md, RESULTS.md and BASELINE_DRAFT.md are regenerated.
* **Running.** `run_all.py` resolves paths from the repository folder, runs
  the tests after the outputs they check, and in Spyder/IPython reports a failed
  step and its log instead of raising `SystemExit`.
* **Figures.** Households and household size distinguish census-benchmarked,
  census-scaled and consent-derived years and project from the 2023 census
  point; demand-band figures show in-scope bands only (no negative or avoided
  bands); fixed material palette; census-interval history in diag_3/diag_4;
  new fig_replacement_rate; diag_1 and diag_6 removed (identities remain as
  tests; the handover panel moved to fig_reality_checks). See FIGURES.md.

Environment: `requirements.txt` (Python 3.11.15). Seeds fixed.
