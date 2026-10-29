# CHANGELOG

Current release first. "Numbers" means the reported results in `outputs/data/`.

## model-v4.3.6: final colours

Figures only: no model, Monte Carlo or Sobol run; `outputs/data/` is byte-identical.

* **Palette** (`palette.toml`): new values for the demand bands, materials, life-cycle stages, runs, strategies,
  boundaries and zones, the Fig3b cumulative column, the one-at-a-time colours and Overbuild absorbed.
  * The zones are drawn at 0.5 opacity. Soil carbon loss is now one solid colour in the material and the stage panels
    (the same quantity).
  * redraw.py treats that pair as the same quantity (SAME_QUANTITY).
* **Black type.** Every label that was drawn in a run, strategy or boundary colour is now black ink (`style.INK`):
  * the Fig4 step tick labels;
  * the Fig5 ruler annotations;
  * the Fig6 strategy group labels;
  * the ED9 run end-labels;
  * the Fig3b "AR / AtP budget" labels.

  Lines, markers, fills and legend swatches keep their colours.
* **Visibility.** A thin white halo is added in two places:
  * Fig3b: under the 90% whisker and the AR / AtP budget lines, which cross the near-black cumulative column;
  * Fig7a, ED4, ED5: under the intermediate-case ticks on the dark high-end bars.
* **Checks.**
  * redraw.py: no warning.
  * Every palette group is at least 10 (CAM02-UCS) in all vision types, except the boundary zones, which are pale by
    design; their lightness order holds.
  * tools/palette_coverage.py: 0 colours outside the palette.
  * Captions, style.py comments and docs/PALETTE.md describe the new colours.
* **Numbers:** unchanged.

## model-v4.3.5: methods sharpening before the Stats NZ 2023-base data

Deterministic runs only (projection, boundaries, the sensitivity tables, the SF7 diagnostic, the reports, the figures).
The numbers below were printed from the outputs, not typed; old values are from model-v4.3.4.

* **Shared-parameter rule for the one-at-a-time AR base.**
  * Every one-at-a-time row that reports a LoE is classified in `boundaries.AR_BASE_RULE`. A row that changes the
    level of the present-day carbon factors or an accounting convention recomputes I_sec,base with the Monte Carlo's
    base function. Those rows are the single case study, the jackknife, soil carbon loss on all floor area and event
    timing L / n. A row that changes only future technology, siting or demand keeps the Reference base.
  * An unclassified row stops the run. The completion-rate and completion-lag rows keep the Reference base, as in the
    Monte Carlo.
  * Changed numbers:
    * Jackknife cumulative LoE of AR: 4.310 / 4.608 -> 4.442 / 4.472 (central 4.464). The row now falls below Fig7a's
      filter ("completion rate and above") and is no longer drawn there.
    * Event timing L / n: 4.4304 -> 4.4349.
  * Recomputed bases, against the Reference 1415.2 kt/yr:
    * jackknife −2.98% / +3.04%;
    * single case study −22.77% / +19.91%;
    * soil on all floor area +1.28%;
    * event timing −0.10%.
* **ED5: global impact, EF 3.1.** I_glob = 7.55E+03 kg CO2e per person x 6,895,889,018 = 5.206E+13 instead of 5.58E+13
  (Andreasi Bassi et al. 2023, Table 10). Cumulative LoE of AR 4.165 (−6.70%); AtP unchanged. The "LULUC not verified"
  limitation is replaced: 5.58E+13 equals the EF 3.0 factor, whose total includes land-use change.
* **SF7: like-for-like zero lag.**
  * A zero-lag run with the forward net replacement held at the 17-month calibration
    (`projection.NET_REPLACEMENT_HELD`, diagnostic only; `None` in every reported run). The recalibrated zero-lag run
    stays as a grey context line.
  * Cumulative net replacement 2026–2050: 8.68 Mm² (zero lag, held), 8.95 Mm² (17 months), 14.66 Mm² (zero lag,
    recalibrated).
* **Assumptions and methods text.**
  * Carbon factors and the AR base (no back-casting), the ability-to-pay sector share (Södersten, Wood & Hertwich
    2018), timber end of life (31% of C1–C4; no timber maintenance events), the GWP basis and households 2019–2023.
    Every number in these texts is computed from the data.
  * The completion-lag line of the methods draft now states the 17-month lag and 0.945.
  * A new part 5, Uncertainty analysis (`tools/uncertainty_methods.py`).
  * Version narration removed from the generated documents (METHODS_DRAFT, FIGURES.md, INDEX.md, PALETTE.md).
  * The completion rate and lag cite Greenaway-McGrevy & Jones (2023) with Jones, Greenaway-McGrevy & Crow (2025).
* **References.** `docs/REFERENCES.md` is one alphabetical list of every cited source, with the lever numbers of
  Table 1. Wallis 2014, Peduzzi 1996, Napiontek 2025, Efron & Tibshirani 1993 and Gabriel & Nothaft 1988 are
  dropped (no longer cited).
* **Leftovers.**
  * The ED4 / ED5 row notes have one source (FIGURES.md takes them from the figure code), and the numbers sit on the
    first line of each note.
  * Removed as unused:
    * the naming.py identifier maps of earlier versions (LEGACY, OLD_TERMS, *_V2_*, *_V3_2);
    * `LOCK_V3_3` / `LOCK_V3_3_1`;
    * `collect_ignore_glob`;
    * `tests/capture_v3_2_totals.py` and its two fixtures;
    * the test of the removed lever map.
  * The methods-part `main()` entry points call `tools/methods.py`.
  * `docs/LEVERS_TABLE.md` was a stale copy of `outputs/reports/LEVERS_TABLE.md` (the L5 bootstrap interval of a
    light run); it is refreshed from the outputs.
* **Data files changed:**
  * aesa/results.json, aesa/sensitivity.csv, figure_source/D18 (the AR-base rule and the EF 3.1 row);
  * sensitivity/tornado.csv, sensitivity/planetary_boundary.csv;
  * sensitivity/reference_carbon.csv (citation of the completion rate only);
  * diagnostics/lag_comparison_annual.csv and _summary.json (SF7);
  * metrics.json (the High / Very High hindcast keys of validation.json, missing from the committed copy).
* **Unchanged:** every other data file is byte-identical, including every Monte Carlo and Sobol file. The v4 lock is
  re-captured for tornado.csv and reference_carbon.csv only.
* **Figures:** Fig7, ED5 and SF7 change, and ED4 changes in its note layout only. Every other figure is
  pixel-identical.

## model-v4.3.4: cleanup towards publication; ED4/ED5 row numbers at 5 pt

* **Figures.** In ED4 and ED5 the row numbers are drawn at 5 pt (`style.FONT_MIN`), in the row labels and in the notes.
  Every other figure is pixel-identical to v4.3.3.
* **Removed.**
  * The legacy MODEL v2.1 Reference mode (`run_all.py --reference-legacy`, `PATHWAY_REFERENCE_LEGACY`, `outputs/_legacy/`).
    The "overbuild never absorbed" sensitivity row is computed as before (it sets `OVERBUILD_ABSORPTION_END = None`
    itself); `run_meta.json` no longer gets a `reference_legacy` key when it is next written.
  * Seven unused functions: `draw.fmt_kt`, `draw.boundary_lines`, `draw.stack_bars`, `draw.band_legend`,
    `style.boundary_vzones`, `levers.tl_label`, `naming.scenario_label`. `aesa.alpha_eq_s1` is kept (a test uses it).
  * The retired tests and their fixtures.
  * The one-off tools: design documents, renaming, transition audit, output manifest, number map.
  * The superseded documents: figure plans, sensitivity plan, project state, hooks, renaming map, per-version changelogs.
  * Version narration from the code comments.
* **Added.** `tools/ast_equivalence.py` proves that comment and docstring edits leave the code unchanged.
* **Numbers.** Unchanged: `outputs/data/` is byte-identical, and the v4 regression lock passes.

## model-v4.3.3: palette coverage and opacity, leaner tests, SF2b redrawn

* **Palette.** Every meaning colour and meaningful fade of the final figures is in `palette.toml`: 18 groups, including
  `[opacity]`. `tools/palette_coverage.py` finds none outside it.
* **SF2b.** Redrawn in the Fig1 layout: solid parts, negatives below zero, one straight annual line. In the 2026–27
  pipeline years the line is the component sum (author decision); the floor-area-based count differs by −51 and −801.
* **ED4 / ED5.** The row notes are numbered.
* **Tests.** Reduced to the number-protecting files plus `tests/test_figure_integrity.py`.
* **Numbers.** Unchanged.
* **Correction.** The v4.3.2 report said that this file and `CITATION.cff` had been updated for v4.3.2. They had not:
  the edit did not run and its result was not checked. v4.3.3 added the missing entry and set the version.

## model-v4.3.2: figure and palette changes

* **Palette.** The boundaries, zones, Fig3b column and one-at-a-time colours moved into `palette.toml`; the lever
  shades were retired.
* **Figures.**
  * Fig1: one annual floor-area line.
  * Fig3: no annual markers.
  * Fig7b: adds the Moderate Pathway.
  * ED4 / ED5: fewer rows shown, with row notes read from the code and the outputs.
* **Numbers.** Unchanged.

## model-v4.3.1: final figure suite, investigations, user palette

* **Palette and figures.** `palette.toml` and `redraw.py` (recolour from the committed outputs). The figure suite is
  fixed at 7 main figures, 9 Extended Data items and EDT1, and 15 Supplementary figures and ST1.
* **Investigations.** Ten investigations. Three model fixes (households, lag comparison, tornado budget) are held for
  the next model run.
* **Numbers.** Unchanged. Rows were added for the High and Very High hindcast variants.

## model-v4.3.0: clean full rerun

* **Run and figures.** A full production rerun (5,000 draws; Sobol N = 1,024, BCa 999) and the renumbered figure suite.
* **Numbers.** Carbon unchanged. The AESA base window picked up the v4.2 household bridge: every cumulative LoE of AR
  changed by about −6e-6 relative.

## model-v4.2.2 and v4.2.1: figure corrections; signed household-size band

* **v4.2.1.** The household-size band became signed (negative when households consolidate). Run totals are unchanged;
  only the band composition changed.
* **v4.2.2.** Figure fixes only.

## model-v4.2.0: households after the 2023 census

* **Households.** Households after the 2023 census are ERP / S, so the Stats NZ dwelling and household estimates are
  no longer used. Six display bands are added for the figures.
* **Numbers.** Projections 2026–2050 unchanged; the 2024–25 history changed.

## model-v4.1.0: diagnostics

* **Diagnostics.** The 2026 gap diagnostic was corrected, and the controlled completion-lag and market-balance
  analysis was added.
* **Numbers.** Model results unchanged.

## model-v4.0.0: completion lag and rate

* **Changes.** Consents become completions after 17 months, at a completion rate of 0.945, with the 2026–27 pipeline
  years observed. Also the TL1 speed limit, TL surplus pooling and household-size sensitivities.
* **Numbers changed.** Reference 19,761 kt CO₂e (v3.3: 20,615); cumulative LoE of AR 4.46 (4.63).

## Before v4.0.0

MODEL v1 to v3.3.2 built the model up step by step:
* the Reference projection, case-study carbon factors, Monte Carlo and validation;
* the planetary-boundary (AESA) layer;
* the levers, pathways and theoretical limit;
* the PAS 2080 regrouping (v3.3).

Their changelogs, locks, design documents and retired tests are in the git history and at the tag `model-v4.3.3`
(`docs/CHANGELOG_v*.md`, `docs/RENAMING.md` for the earlier vocabulary, `tests/retired/`).
