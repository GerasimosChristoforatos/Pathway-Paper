# CHANGELOG

Current release first. "Numbers" means the reported results in `outputs/data/`.

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
