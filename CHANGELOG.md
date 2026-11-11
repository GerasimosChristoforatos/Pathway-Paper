# CHANGELOG

Current release first. "Numbers" means the reported results in `outputs/data/`.

## model-v4.4.0: Stats NZ 2023-base household projections, starting surplus, AR base with completion

One full run (`run_all.py --profile full`), then the light profile. Every number below is read from the outputs of
v4.3.7 (5ae8bf5) and of this run.

* **Household size: Stats NZ 2023-base family and household projections.**
  * Inputs: POPPR_FHH_008 (people in households) and POPPR_FHH_010 (households), 2023(base)-2048, Low / Medium /
    High x propensity A / B, in `data/raw/` (MANIFEST rows).
  * `data/build_households_2023.py` writes `data/derived/households_proj_2023base.csv`, with
    S = people in households / households. The published AHS is not used. A STOP fires unless
    FHH + OPH + OMH = HH within 100.
  * Knots, Medium A: 2.741, 2.689, 2.633, 2.584, 2.548, 2.524 (2023-2048). Medium B ends at 2.648.
  * The Reference uses Medium A (`HH_PROPENSITY = 'A'`), rebased on the observed 2023 household size (2.686).
    This holds the share of the population outside private dwellings at its 2023 level.
  * S 2048 / 2049 / 2050 = 2.473 / 2.473 / 2.473: zero slope imposed at 2048, held after it.
  * N4 resolved. The 5th / 95th population paths take Low A / High A (`HH_SIZE_PAIRED`). The Monte Carlo pairs them
    through one z, as before.
  * Rows:
    * The S-only "Stats NZ High / Low variant" row is removed; its variation is now part of the population row.
    * New row "Living arrangements: propensities change (Stats NZ B)" (Medium B): Reference -18.1%.
    * The tail rows now act "after 2048". The secant and end-slope tapers move carbon by +1.04% and +0.78%, above the
      0.1% rule, so they stay shown. The flat row (-0.008%) stays in the not-shown list.
  * The 2018-base files and loader are no longer used by any reported run. They are kept only as
    `HH_SIZE_PATH = 'statsnz_2018'`, with which tests/test_events.py and tests/test_model_v4.py reproduce the
    anchors of earlier versions.
* **F2: households 2019-2023.** `data/raw` holds no Stats NZ household estimates rebased on the 2023 census: the
  March 2026 quarter release still has its last household base at 2018. The census-pinned rescaling (k = 0.824) is
  kept and nothing was fetched.
* **F1: starting surplus (rule fixed in advance).**
  * Stock-identity residual, 1992-2023 census intervals: time-weighted mean -463 and SD 3,038 dwellings a year.
  * 2024-2025: 9,020 a year, above mean + 2 SD (5,614), so the surplus is carried.
  * Starting surplus: (9,020 + 463) x 2 = 18,966 vacant dwellings at 1 January 2026. It is absorbed with the
    overbuild by 2035, in every run and Monte Carlo draw, recomputed from each run's own completion rate and lag.
    TL runs pool it for re-occupation.
  * Rows: no starting surplus +2.71%; minus 2 SD (6,812 dwellings) +1.73%.
  * The decision does not depend on the SD definition: with the unweighted SD (3,437), mean + 2 SD = 6,412.
* **F5: the AR base co-varies with the completion rate and lag.**
  * Each Monte Carlo draw rebuilds its 2016-2025 history at its own completion rate
    (`boundaries.history_at_completion`).
  * The completion-rate and completion-lag rows recompute the base from their own runs (class 'recompute'). The
    Monte Carlo base at 0.93 equals the base of the 0.93 run to 1e-12.
* **F6:** the Fig7a note states that the carbon-factor (jackknife) row falls below the row filter: LoE AR
  5.660-5.697 against carbon -3.4% / +3.2%, because the AR base co-varies with the factors.
* **Old -> new** (v4.3.7 -> v4.4.0):

  | quantity | v4.3.7 | v4.4.0 | change |
  |---|---|---|---|
  | Reference cumulative carbon 2026-2050 (kt CO2e) | 19,761 | 25,176 | +27.4% |
  | Reference floor area 2026-2050 (Mm2) | 81.53 | 103.94 | +27.5% |
  | Household size 2050 | 2.652 | 2.473 | -6.7% |
  | Demand band carbon (kt): population growth | 9,776 | 9,776 | 0.0% |
  | household-size change | 487 | 3,421 | x7.0 |
  | extra space | 6,364 | 9,070 | +42.5% |
  | vacancy | 947 | 1,268 | +33.9% |
  | net replacement | 1,804 | 1,870 | +3.7% |
  | market balance (incl. the starting-surplus payback) | 24 | -668 | |
  | (maintenance) | 359 | 438 | +22.0% |
  | Reference LoE AR / AtP | 4.464 / 17.76 | 5.687 / 22.62 | +27.4% |
  | Moderate Pathway carbon (kt) / LoE AR / AtP | 14,302 / 3.231 / 12.85 | 17,818 / 4.025 / 16.01 | +24.6% |
  | Ambitious Pathway carbon (kt) / LoE AR / AtP | 10,267 / 2.319 / 9.22 | 12,486 / 2.821 / 11.22 | +21.6% |
  | Theoretical Limit carbon (kt) / LoE AR / AtP | 4,423 / 0.999 / 3.97 | 4,079 / 0.921 / 3.67 | -7.8% |
  | P(LoE AR <= 1): Reference / Moderate / Ambitious / TL | 0 / 0 / 0.0002 / 0.499 | 0 / 0 / 0 / 0.640 | |
  | TL threshold 2050 population, P = 50% (M) | 6.614 | 6.715 | +1.5% |
  | Sobol total indices, carbon (top 3) | z_pop 0.846, size 0.108, carbon 0.044 | z_pop 0.670, size 0.234, carbon 0.089 | |

  * TL falls while the Reference rises. With the starting surplus at zero, TL would be 4,279 kt (LoE AR 0.967), so
    199 kt of the 344 kt fall is the surplus pooled for re-occupation. The rest comes with the 2023-base household
    path; it is not decomposed further here.
* **Figures:**
  * Fig5 axes to 90% (the TL marker had moved outside) and contour labels clear of the markers.
  * ED3 and ED9 legends moved below the panels.
  * ED4 at 247 mm.
  * SF2 legend and note name the starting surplus.
* **Checks.**
  * Full test suite (full profile): 259 passed, 2 skipped (the local AESA workbook).
  * Regression lock re-captured: 33 of 34 deterministic files and all Monte Carlo files changed; the light and full
    deterministic files are identical.

## model-v4.3.7: Inter, ED10 reality checks, one net-replacement band

Figures only: no model, Monte Carlo or Sobol run. Every figure is redrawn from the committed outputs (`redraw.py`).
In `outputs/data/` only the two number maps change (`ed_number_map.csv`, `sf_number_map.csv`); the other 111 files are
byte-identical.

* **Typeface: Inter** (SIL OFL 1.1). Regular, Italic, Bold and Bold Italic are taken from the rsms/inter 4.1 release
  into `fonts/`, with the licence and a note in `fonts/README.txt`. `style.FONT = 'Inter'`, with Liberation Sans as
  the fallback. Sizes are unchanged, and every character drawn in the figures is in Inter.
  * Layout fixes, each placed from measured text extents:
    * Fig1: the History label sits 3 pt clear of the divider.
    * Fig2: the panel a and b legends no longer touch.
    * Fig4c: the legend has a white box, so the gridline no longer crosses it.
    * Fig5: the legend sits at least 4 pt below the x-label.
    * Fig7b: the 50% line stops 3 pt below the legend.
    * SF2b: the bottom note sits 3 pt off the spine and clear of the divider.
  * ED4 / ED5 row notes: wrapped by rendered width and stacked at the measured line pitch. The numbers are
    right-aligned in the width of the widest number. Inter's taller lines had made the fixed 2.15 mm pitch overlap.
  * One-at-a-time intermediate tick names (e.g. "High") get a white halo and sit clear of the bar.
* **Boundary zones.** The "Boundary exceeded" fill is no longer drawn anywhere; nothing is filled above AR. Removed:
  the key in `palette.toml` (`[boundary_zones]`, `[opacity]`), in `style.ZONE` and in the palette checks. The zone
  lightness check now compares the two zones (within both < within AR only), and it holds.
* **Colours.**
  * Fig2 stages: A1–A3 `#672327`, A4–A5 `#EFBF9F`.
  * ED7: total effect `#4D4D4D`, first-order `#B3B3B3`.
* **ED6.**
  * New x-label "A1–A3 materials factor (kg CO₂e per m², 2025)".
  * New note on A1–A3 against whole embodied carbon and on the single apartment case study. Its numbers are read
    from `factors_typology.csv` / `factors_building.csv`: 610, 444 and the median 434 kg/m².
* **SF2b: one Net replacement band.**
  * The projection's demolition replacement, recent surge and unconsented additions are drawn as one band, Net
    replacement, in the history's colour and with one legend entry.
  * The band is checked per year against the sum of its three parts; a mismatch STOPs.
  * The note states that the projection's split is not identified from data. Its rates are read from the outputs:
    demolition 0.135%/yr; residual −0.076%/yr.
  * `[components] replacement_surge` and `unconsented_additions` are removed; no figure used them.
* **SF8 moved to Extended Data as ED10, "Reality checks".**
  * Panel b is titled "Implied net removals (net replacement rate × stock)". Its note explains Low / High /
    Reference / Very High, and its removals box uses the short names so it covers no data (checked; STOP otherwise).
  * Panel h (the handover step) is replaced by "Floor area built (consented, in scope)":
    * history: `annual.csv`, 1991–2025;
    * projection: `variants_annual.csv`;
    * the handover statistic moves into the note (from D15): 2027 → 2028, −18.2%, against −39.8% to +27.8%.
  * Every history line is straight segments between annual values (no PCHIP), and a drawn line that is not its
    source data STOPs (maximum difference 0).
* **Renumbering.** SF9–SF15 become SF8–SF14. Both number maps record the change: SF8 → ED10 in `ed_number_map.csv`;
  SF10 → SF8, SF12–SF17 → SF9–SF14 (v4.3.0 numbers) in `sf_number_map.csv`. Extended Data: ED1–ED10 (at most 10).
* **Checks.**
  * `redraw.py`: 0 palette warnings.
  * `tools/palette_coverage.py`: 0 colours outside the palette.
  * `tests/test_figure_integrity.py`: 32 passed, including new tests for the merged band and the ED10 history lines.
  * Full suite: 221 passed, 36 skipped.
* **Numbers:** unchanged.

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
