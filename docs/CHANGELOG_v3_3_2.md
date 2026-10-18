# MODEL v3.3.2: final main-figure layout

Branch `release/model-v3.3.2`, from `release/model-v3.3.1`.

* **Figure code only.** No model, deterministic or Monte Carlo step was re-run.
* **Data byte-identical.** Every data file is unchanged: 103 files in the light profile and 104 in the full profile
  are byte-identical after `--figures-only`. Every file of the v3.3.1 lock keeps its hash
  (`tests/test_figures_v3_3_2.py`, `tests/test_regression_model_v3.py`).
* **Figures.** PNG only, current palette. Previews at 200 dpi (light); one final export at 600 dpi (full).

## Main figures (outputs/paper_main/)

| v3.3.2 | from v3.3.1 | change |
|---|---|---|
| Fig1 Floor area by demand | Fig2 | The column gap is halved (10% → 5% of each interval's width). The same gap now separates the last history column from the projection. The dotted 2025/26 line and the labels stay. |
| Fig2 Reference carbon | Fig3 | See below. |
| Fig3 Reference vs boundaries | Fig4 | See below. |
| Fig4 Pathways | Fig5 + ED5 | See below. |
| Fig5 Reduction by demand | new | See below. |
| Fig6 Solution space | Fig6 | See below. |
| Fig7 Shapley by lever | Fig7 | Unchanged. |
| Fig8 Uncertainty | Fig8 | Panel (a) unchanged. Panel (b): the secondary axis and the logistic curve are removed. It keeps the draws, LoE = 1, the threshold line labelled with its CI, and "TL within AR in 55% of draws" (0.552, full profile). |

**Fig2 Reference carbon.** Panels a–c keep the shared y-axis.

* The demand legend is inside panel a, in two columns, above the data. The y-axis is extended upward, and its ticks
  are shown only over the data range.
* New panel (d): cumulative 2026–2050 as three attached columns, by demand | by material | by stage, all of the same
  total (20,615 kt). It has its own y-axis in kt, thin white separators and column labels below.
* The demand column follows the existing sign rule (`draw.bars_cumulative`): positive bands are stacked, and negative
  bands are outlined and hang down to the total tick. Its top therefore reaches the gross positive stack, and the net
  equals the total. A dotted line marks the common total.

**Fig3 Reference vs boundaries.** Panel b:

* A 95% interval whisker sits on the cumulative column. It spans the 2.5th–97.5th percentile of the Monte Carlo
  cumulative carbon: 14,353–27,415 kt in the full profile.
* These percentiles were not stored, so the figure computes them from the per-draw totals
  (`montecarlo/draws_REF.csv`) with the model's percentile method (`numpy.percentile`, linear). The same computation
  reproduces the stored 5th/95th percentiles exactly (tested).
* The committed column is C1–C4 plus B2/B4 at its lower bound (2050 factors held), stacked, with a range whisker up to
  the upper bound (2025 factors).
* All numbers are removed from the panel. The budget lines keep the text labels "AR budget" and "AtP budget", since
  the three-entry legend does not name them.
* The legend inside the panel has the three requested entries.

**Fig4 Pathways.**

* (a) Full-width annual carbon:
  * the Reference in black (`style.INK`);
  * the Moderate and Ambitious Pathway in bold, Moderate solid and Ambitious dotted;
  * the Theoretical Limit in deep green, bold;
  * S1–S3 as thin lines in the strategy colours, Moderate solid and Ambitious dotted;
  * AR/AtP lines and zones, with the legend inside.
* (b–d) The three waterfalls of v3.3.1, unchanged; the strategy key now sits inside panel d.
* ED5 (pathways annual) is kept unchanged in the Extended Data. It now duplicates Fig4a, and the author may drop it.

**Fig5 Reduction by demand (new).**

* Three columns: the Moderate Pathway, the Ambitious Pathway and the Theoretical Limit. Column height is the total
  reduction against the Reference, with the value on top: 5,542, 9,694 and 16,257 kt.
* Each column is stacked by demand band, as Reference − run for each in-scope band (`pathways/bands.csv`). The bands
  of each run add up to its carbon.
* Negative band reductions are outlined segments hanging down from the top of the positive stack to the total tick,
  per the existing rule:
  * Overbuild absorbed: −132 / −249 / −481 kt;
  * Unconsented additions: −109 / −199 / −331 kt.
* Caption note: the credits from re-used dwellings shrink when new dwellings are smaller, because each re-used
  dwelling is valued at the new-dwelling size it displaces.
* The TL band "Released dwellings (TL)" is a positive reduction (+1,256 kt): the Reference has no such release, so it
  is drawn filled.

**Fig6 Solution space.**

* Both axes run from −5% to 100%. The >100% strips and both AtP branches are removed. The AtP contour lies above the
  plotted square (101.6% at x = 0), because the plane floor C_2026/B_AR = 0.319 exceeds AtP = 0.250.
* A slim LoE AR ruler at the right edge uses a log scale, which reads better: the values span 0.25–4.6, a factor of
  about 18. It shows the zones and marks:
  * the Reference (4.63);
  * the Moderate Pathway (3.39) and the Ambitious Pathway (2.45);
  * the Theoretical Limit (0.98);
  * AR = 1;
  * the plane floor (0.32, "2026 observed");
  * AtP (0.25).
* Kept: the annotation, the markers, the contours, the AR line, and the marker test.
* The contour labels now sit where each contour crosses the diagonal x = y, computed analytically from
  (1 − x)² = k. Labels whose crossing falls outside the square are omitted.

## Supplementary

The schematic (Fig1 of v3.3.1) is now **SF1** (`outputs/supplementary/SF1_model_schematic.png`). The other
supplementary figures shift to SF2–SF6: MC scatter, conditional TL, lambda sweep, Harrell-Davis estimators, consent
sizes.

## Tests (`tests/test_figures_v3_3_2.py`)

* The data are byte-identical to the v3.3.1 lock (deterministic files, and the Monte Carlo files of the profile).
* Fig5 column totals equal Reference − run, and the band reductions sum to them (1e-9).
* The Fig3 interval is computed from the draws and reproduces the stored 5th/95th percentiles.
* Fig6: the markers lie on the analytic plane (1e-9), the square is −5% to 100%, and the AR line is exact.
* The schematic is SF1, and the main-figure order is as listed above.
* v3.3.1 tests were adapted: the AtP branches are still checked against the contour equation on the v3.3.1 square
  (they are no longer drawn); the net-positive-step note is read from Fig4.

## Timings

| step | time |
|---|---|
| `run_all.py --figures-only`, light (200 dpi previews) | 34 s |
| `run_all.py --figures-only`, full (600 dpi PNG; the one final export) | 57 s |
| Test suite, run once on the full profile (257 passed; 2 skipped, both needing the local AESA workbook) | 41 s |

No model or Monte Carlo step was run.
