# MODEL v3.2.0: changes and decisions

Branch `release/model-v3.2.0`, created from `release/model-v3.0.0` (d084e09). MODEL v3.1.0 is **withdrawn**
(`release/model-v3.1.0`, `WITHDRAWN.md`): its accounting change (inventory default) expanded the scope to the existing
stock. v3.2 keeps the v3.0 cause-based accounting and carries the non-methodological fixes of v3.1, ported from the
v3.1 implementations (`git diff release/model-v3.0.0 release/model-v3.1.0`, applied selectively) with every trace of
the accounting change removed. Numbers are full profile unless stated; deterministic numbers are identical in both
profiles (`tests/capture_regression_model_v3.py` checks it).

## Summary

* **Equality with v3.0**: the Reference, every lever (L1-L9) and pathway (P1-P5) run and TL (52 runs; floor area,
  carbon, LoE AR, LoE AtP, B_AR, B_AtP) equal the v3.0 outputs: worst relative difference 3.4e-16 (TL carbon and LoE
  in the last binary digit), against the 1e-9 condition.
* **Monte Carlo**: the Reference Monte Carlo, the AESA draws (budgets and annual) and the Sobol indices are not
  re-run; their v3.0 files are unchanged (byte-identical; checked on the light profile by a full re-run of those
  steps, and on the full profile through the per-draw check of pathways_mc.py, which re-projects every Reference draw
  through the v3.2 engine and stops if its carbon differs from the AESA draw by more than 1e-9). Only the pathway
  Monte Carlo (`pathways_mc.py`, 5,000 draws) was re-run, once.
* **STOP conditions**: none triggered (details at the end).

## What was ported (and what not)

Ported:

* **A2 release accounting** (`bands.py`, `pathways.run`): gross positive bands; separate negative bands ('Vacancy
  released', 'Released dwellings (TL)', 'Overbuild absorbed', 'Unconsented additions') and 'Surplus kept vacant (2050)';
  no netting or rescaling (retirement villages removed by the exact factor 1 - RV share); in every TL-family run (TL,
  the TL waterfall steps, every TL Shapley subset) the re-occupation pool holds every release present in that run.
* **A3 history split** (`validation.history_bands`, `history_unexplained`): 'Net replacement (census)', 'Retirement
  villages (out of scope)', 'Unexplained building'; the bands add up to the observed floor area built (1e-9).
  `history_replacement_split` and its CSV are retired.
* **A4** sensitivity row 'TL-reoccupation-fast' (re-occupation as fast as demand allows; deterministic only).
* **A5** check row r_L6 with A_1 (n = 15; report only; `levers.json` L6.check_with_A_1).
* **Figures B1-B3**: Fig5/ED7 true sequential waterfall; Fig6 single panel with analytic contours; ED5b population
  threshold; Fig1 history split; Fig3b band bar without rescaling; Fig8 caption; D37, D38 (the resulting A1-A3 factors,
  `montecarlo/carbon_factors_REF.csv`, written by pathways_mc.py from the saved draws and bootstrap replicates; nothing
  resampled), D40, D07, D29, ED11, ED8c; the final palette (Vacancy released `#481870`, Surplus kept vacant `#D1E6C1`,
  Retirement villages `#4E463E`; every group meets the CVD distance threshold of 10 except the boundary zones, pale by
  design; `docs/PALETTE.md`).
* **Docs**: the Reference replacement wording, the completion-rate two-piece rationale, the reference corrections
  (DiPasquale & Wheaton 1992; Gabriel & Nothaft 2001, distinct from 1988; Jones et al. 2024 [verify]); methods part 4
  (`tools/release_methods.py`).

Not ported: the `ACCOUNTING` setting and all its code (`inventory.py`, `cohort_window`, soil spreading, legacy soil and
B, the 'Legacy (pre-2026 activity)' band, 'Soil, after 2050', `accounting_rules.csv`, the related tests, figures and
methods text), the v3.1 engine changes, the v3.1 Monte Carlo changes (per-draw legacy B, the instant-rule share).

Adapted to the v3.0 accounting:

* **Fig6**: LoE_AR(x, y) = [C_2026 + C_ref,2027-2050 (1 - x)(1 - y)] / B_AR with C_2026 = 1,420.8 kt (the 2026
  cohort's emissions in the window), C_ref,2027-2050 = 19,194.1 kt (every emission in the window of the 2027-2050
  cohorts: A1-A5, soil carbon loss, in-window B2/B4) and B_AR = 4,451.0 kt; y = cut in 2027-2050 total carbon per m2
  (v3.0: non-soil carbon only). Each run at its effective coordinates; the analytic value at every marker equals the
  run's LoE AR (test, 1e-9). The AR line lies on the plane; the AtP line (LoE AR = 0.25) lies below its lowest point
  (0.32 at a 100% cut), stated on the figure.
* **Fig5/ED7**: no legacy segment. **Fig3**: committed column as in v3.0 (B after 2050 + C1-C4 range).
* **Methods**: the attribution principle of the (unchanged) v3.0 rule and the system boundary (part 4), citing
  Davis & Socolow (2014) [verify].

## B: release accounting in the pathway runs (as ported)

Two rules of A2 change pathway Monte Carlo draws (not any deterministic run):

* **Carry-forward of unusable releases.** When releases in the requirement exceed the gross need in a year (a
  negative gross year; low-population draws), nothing is built and the unusable dwellings are carried forward against
  the next years' building. v3.0 built nothing in that year and dropped the deficit, as if the released dwellings
  vanished. Rationale: released dwellings remain physically available later; carrying them is the same treatment as
  the TL re-occupation pool, which re-occupies released dwellings over the following years subject to availability.
  Dwellings still unusable in 2050 are kept vacant ('Surplus kept vacant (2050)').
* **Payback on gross need.** The overbuild payback is taken on the gross need (the requirement with the vacancy
  release added back) instead of the net requirement, so the release is not netted against the payback cap.

## C: zero-year soil guard (a v3.0 defect)

`engine.forward` (every run): built floor area below `BUILT_ZERO_TOL_M2` = 1e-6 m2 is set to 0 with its soil-bearing
share and soil carbon; the soil-bearing share is clipped to [0, 1] in every run (TL runs already clipped it). In
v3.0, in a year where nothing is built the floor area was floating-point noise (e.g. ±2.3e-10 m2) and the share
1 - soil-free / total a ratio of noise (order ±1e15), so the soil carbon of a year without construction was non-zero
(e.g. -16.0 kt in 2031 of draw 514, light). In years that do build, the share fell below 0 where the soil-free
replacement floor area exceeded the total built, booking a soil credit (negative soil carbon) on land that was never
converted. Every deterministic run is unaffected (equality above); the Reference Monte Carlo and the AESA draws are
unaffected (above). A negative floor area occurs only in the requirement pass of pathways.run (join = 0; its floor area
is not used) and is set to 0 there too; built dwellings are checked >= 0 separately.

## Pathway Monte Carlo: changed draws (full profile, 5,000 draws)

Attribution by `tools/v3_2_mc_attribution.py` (every changed draw recomputed with the v3.2 pathways code on the v3.0
engine: B alone; C = the rest); per-draw table `docs/v3_2_mc_attribution.csv`.

| run | draws changed | max abs change (kt) | by B | by C | C draws with a zero-built year / with a clipped share in a building year |
|---|---|---|---|---|---|
| P5 Moderate | 6 | 23.0 | 0 | 6 | 0 / 6 |
| P5 Ambitious | 109 | 43.5 | 3 | 109 | 13 / 109 |
| TL | 156 | 7.6 | 156 | 0 | — |
| TL-from2027 | 742 | 96.4 | 742 | 0 | — |

C always raises carbon (115 of 115 changed run-draws; it removes the non-physical soil credits); the largest soil
removed from zero-built years is 26.2 kt. C draws, P5 Moderate: 1800, 1836, 2426, 2448, 3755, 4960; P5 Ambitious: the
109 draws listed in the CSV (delta_C != 0).

Headline statistics (v3.0 → v3.2): P(TL LoE AR <= 1) 0.551 → 0.551 (Wilson 0.537-0.565). The 5th-95th percentiles
of P5 Moderate (carbon 10,997-19,324 kt, LoE AR 2.58-4.17), P5 Ambitious (7,836-14,182 kt, 1.83-3.05) and TL
(2,507-6,504 kt, 0.59-1.40) are unchanged; the means move by +0.008 kt (P5 Moderate), +0.199 kt (P5 Ambitious) and
-0.065 kt (TL). TL-from2027: p95 4,364.8 → 4,343.7 kt, P(LoE AR <= 1) 0.9788 → 0.9808.

ED5b population threshold (TL within AR at 50%): 6.651 M in 2050 (95% bootstrap CI 6.647-6.654 M; Firth penalised
likelihood, the MLE does not exist: P(within AR) falls from about 1 to about 0 within a narrow band of the 2050
population, so the interval is narrow by construction of the model, not by sampling precision).

## Deterministic changes (A2, A3; all files in the v3.2 lock)

* TL waterfall steps (kt): Moderate TL1 +92.1, TL2 +95.8, TL3 +97.2; Ambitious TL1 +199.9, TL2 +201.5, TL3 +185.9;
  TL4-TL9, P5 and TL unchanged.
* TL1-TL9 Shapley values from P5 Moderate (carbon, kt): TL1 -13.5, TL2 -10.7, TL3 -7.5, TL4 +76.5, TL5 -4.0,
  TL6 -12.7, TL7 -8.1, TL8 -8.8, TL9 -11.3 (the changes sum to 0 within 1.5e-12 kt; efficiency is checked exactly in pathways.py); LoE values proportionally. The Moderate and
  Ambitious P- and L-games are unchanged.
* A3: unexplained building 1992-2025 = -4,345 dwellings (-0.52% of the 828,537 built); floor-area remainder and the
  stock-identity dwellings x size agree to 1.4e-15 Mm2.
* A4: TL-reoccupation-fast 4,072.6 kt, LoE AR 0.915, AtP 3.66 (TL 4,357.7 kt, 0.979); zero-building years
  2029-2038 (TL: 2031-2032).
* A5: r_L6 with A_1 (n = 15) 0.841 (bootstrap CI 0.619-0.955) vs adopted 0.827 (n = 14).

## Runs and timings (full profile)

Re-run: projection 2 s, validation 3 s, boundaries 216 s (for the band figure sources D25/D26; every AESA file came
out byte-identical), pathways 16 s, pathways_mc 821 s (once), sensitivity_tables 10 s, metrics/results/assumptions/
methods 5 s; total 1,073 s. Figures: a 200 dpi preview pass on the light outputs (40 s), then `--figures-only` once at
full quality (PDF + PNG 600 dpi, 89 s); every data file byte-identical before and after drawing. Not re-run:
Building_factors, Diagnostics, Sensitivity (Sobol), MonteCarlo, gap_2026 and the report tools (their outputs are
unchanged: light check). `outputs/run_meta.json` keeps the v3.0 pipeline timings; the reruns above are recorded here.

Regenerated figures whose image changed: Fig1, Fig2, Fig3, Fig5, Fig6; ED4, ED5, ED7, ED8; D07, D25, D26, D36, D37,
D38, D39, D40 (captions of Fig8, ED8c, ED11, D29 in FIGURES.md).

## Tests

* `tests/test_model_v3_2.py`: equality with v3.0 on every run (1e-9); Reference MC and AESA hashes unchanged from the
  v3.0 lock; band sums (projection, every pathway run, history); no rescaling (in-scope band = gross x (1 - RV share));
  vacancy band >= 0, release bands <= 0, surplus only in 2050; Fig6 marker test (1e-9); the zero-year guard; A4, A5.
* v3.2 lock `tests/regression_model_v3_2.json` (30 deterministic files incl. the history bands and the unexplained
  sum; pathway Monte Carlo hashes per profile); the v3.0 lock file is kept.
* `tests/test_figures_v3.py`: 'Vacancy released' among the negative bands; a boundary stated outside the plotted range
  is accepted (Fig6 AtP).
* Result, one pass: 202 passed, 2 skipped (the local-only AESA workbook) in both profiles.

## Checks (STOP conditions)

| condition | result |
|---|---|
| any L/P/Reference/TL total or LoE differs from v3.0 (1e-9) | no (worst 3.4e-16) |
| C changes a deterministic total | no |
| C changes the Reference MC or AESA draws | no |
| band sums fail | no (projection, pathways, history; 1e-9) |
| Shapley efficiency > 1e-9 | no (checked in pathways.py) |
| built >= 0 | yes (every run and draw) |
