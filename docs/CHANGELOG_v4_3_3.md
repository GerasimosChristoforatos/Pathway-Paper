# MODEL v4.3.3

Branch `release/model-v4.3.3`, from `main` at `b8582b9` (v4.3.2 merged).

**Scope.** This release covers palette coverage and opacity, a leaner test suite, the ED4 / ED5 row numbers and a
redrawn SF2b.

* **No model run.** `run_all.py`, `MonteCarlo.py`, `Sensitivity.py`, `pathways_mc.py` and the Sobol analysis were not
  run.
* **Figures.** Every figure was drawn from the committed full-profile outputs with `redraw.py`.
* **Data.** `git diff --stat -- outputs/data` is empty. No reported number changes.
* **Fig7.** The orange is left as it is: Moderate = the one-at-a-time high end (known, accepted).

---

## Step 1: palette coverage and opacity (no visual change)

### Inventory

`tools/palette_coverage.py` (new, run by hand) gives the inventory.

* **Method.** It draws every final figure in process: 31 figures, main, Extended Data and Supplementary, not the
  diagnostics. It reads the colour and alpha of every visible artist: line, marker face and edge, patch face, edge and
  hatch, collection faces and edges, text and label boxes.
* **First run.** With the v4.3.2 palette it found 81 colour or fade findings that did not come from `palette.toml`.
  Each was classified as follows.

| class | what | where it is now |
|---|---|---|
| neutral (fixed) | ink `#1A1A1A`, muted grey `#6E6E6E`, grid `#E0E0E0`, white, black, legend outlines `#555555`, note text `#595959`, the dark neutral grey `#4D4D4D` of histograms and bars that are not a run (ED6, SF15), the legend swatch `#E6E6E6` of the Fig3b 50% box | `style.NEUTRALS` |
| meaning colour | the SF2b parts that are not demand bands: new households `#B0B0B0`, surge `#E1D2DD`, unconsented additions `#BA9AC1`, retirement villages `#8C8C8C`, overbuild absorbed `#8D5D93` (also SF5), unexplained building `#C6A3A4` | `[components]` |
| meaning colour | the SF2b parts that are demand bands: vacancy, net replacement `#D0BBDC` (history, census) and demolition replacement `#D0BBDC` (projection; also SF3), 2026 overbuild `#683861` (also the SF5 lines) | the existing `[demand_bands]` keys (vacancy, net_replacement, market_balance); same values, so no pixel changes |
| meaning colour | released dwellings and the pool line `#95C283` (SF15) | `[components] released_tl` |
| meaning colour | typologies `#DFA538` / `#4A6192` / `#AA7C9D` (ED6, SF4b, SF11) | `[typologies]` |
| meaning colour | Low / High / Very High replacement `#B5B5B5` / `#6E6E6E` / `#1F1F1F` (ED3, SF3, SF6, SF8) | `[replacement_variants]` |
| meaning colour | Sobol total / first-order `#0072B2` / `#56B4E9` (ED7; were Okabe-Ito entries) | `[sensitivity_indices]` |
| meaning colour | census empty points `#C2571A` (SF2a); observed totals without a band split `#BDBDBD` (Fig1; none in the committed data) | `[census_markers]` |
| meaning colour | zero lag / 17-month lag `#C2571A` / `#1F5FA8` (SF7) | `[lag_variants]` |
| meaning colour | the SF6 2027-check model bar, the SF8h history histogram (`#BDBDBD`), the SF8h handover step (`#C2571A`) | `[validation]` |
| meaning colour | SF1b 2024–25 markers (the model's household-size path) `#C2571A`; SF15 "release constraint binds" `#D7191C` | `[highlights]` |
| meaningful fade | zones 0.30 / 0.30 / 0.07; Fig3a Monte Carlo 90% / 50% bands 0.12 / 0.25; single 5–95% bands 0.15 (`style.MC_BAND`, SF13); Fig3a pathway lines 0.8; soil carbon loss 0.5; Fig7b points 0.18 / 0.18 / 0.20 / 0.30; ED6 typology histograms 0.55; SF4a space above occupancy 0.25; ED9c Reference cumulative line 0.55 | `[opacity]` |
| context fade (fixed) | SF2a definition-break span 0.10 and census range span 0.12; SF8 range spans 0.12; SF11 bootstrap span 0.15; SF14 threshold-CI span 0.12 and rugs 0.4; SF1 "estimates not used" line 0.35; neutral histograms 0.6 and bars 0.5; Fig3b 50% box 0.55; label boxes 0.85; Fig7b legend markers 0.9 | `style.FIXED_FADES`, listed in the `palette.toml` header |

* **ED9 roll-out variants.** These are drawn as line styles in the run colours, and their legend swatches are muted
  grey, so they have no colour group. `[rollout_variants]` was not created.
* **Accent colours.** `ACCENT_ORANGE` carried four meanings: census empty points, SF1b markers, SF7 zero lag and the
  SF8 handover. Each now has its own key with the same default.
* **Vacancy released.** `vacancy_released` is drawn in no final figure and has no key.
* **SF14b scatter.** The SF14b fallback scatter (drawn only when no population threshold is estimable, so not with the
  committed data) now takes `scatter_tl` (0.30; it was a literal 0.35).

### Final palette groups (18; 60 colour keys, 15 opacity keys)

`demand_bands`, `materials`, `life_cycle_stages`, `runs`, `strategies`, `boundaries`, `boundary_zones`, `cumulative`,
`one_at_a_time`, plus, new in this release:

* `components`: new_households, replacement_surge, unconsented_additions, retirement_villages, overbuild_absorbed,
  unexplained_building, released_tl;
* `typologies`: detached, townhouses, apartments;
* `replacement_variants`: low, high, very_high;
* `sensitivity_indices`: total_effect, first_order_effect;
* `census_markers`: census_empty, observed_total;
* `lag_variants`: zero_lag, lag_17_months;
* `validation`: model_check, handover_history, handover_step;
* `highlights`: model_path_years, release_binds;
* `opacity`: zone_within_both, zone_within_ar_only, zone_exceeded, mc_band_90, mc_band_50, mc_band, pathway_lines,
  soil_carbon_loss, scatter_reference, scatter_moderate, scatter_ambitious, scatter_tl, typology_histograms,
  space_above_occupancy, rollout_reference_cumulative.

### Code and documentation changes

* **`style.load_palette`.** Strict, as before: every group and key is required.
  * `[opacity]` values must be numbers in [0, 1]; booleans and strings are rejected.
* **Figure code.** Every alpha now comes from `style.OPACITY` or `style.FIXED_FADES`, and every colour from a palette
  constant or `style.NEUTRALS`.
* **`redraw.py`.**
  * `SHARED` gains SF2b (components and the demand-band parts), replacement variants with the Reference, typologies,
    Sobol, lag variants, and SF15.
  * The colour-vision report compares only keys that share a figure. The `census_markers`, `validation` and
    `highlights` keys each sit in a different figure. `released_tl` is compared in the SF15 group.
  * The swatch sheet lists the opacities.
* **`tools/palette_check.py`.**
  * New colour groups.
  * The zone composites and the zone-lightness warning use the `[opacity]` zone values.
  * `docs/PALETTE.md` regenerated.
* **`palette.toml` header.** It states what the file holds, what stays fixed and why.

### Coverage proof

`python tools/palette_coverage.py` uses a probe palette in which every colour key is a distinct vivid hex. Every
opacity key and every fixed fade also gets a distinct probe value, so a bare alpha literal cannot pass. Result:

* 31 final figures, 60 colour keys, 15 opacity keys: **0 colour or fade findings not from the palette** (exit 0);
* drawn in no final figure: `census_markers.observed_total` (Fig1 has no observed-only years in the committed data).

### Regression check

`redraw.py --dpi 600` with the default palette, compared array by array with the committed v4.3.2 PNGs:
**31 of 31 pixel-identical**.

---

## Step 2: figures

### SF2b (`figures/calibration.sf2_stock_vacancy`, panel b)

* **Layout (Fig1).** One column per census interval. The pipeline years 2026–2027 are annual columns. From 2028 the
  projection is annual stacked areas. The gap rule is Fig1's (`paper_main.FIG1_GAP`); the code is
  `draw.stack_series` with per-part styles.
* **Parts.** Positive parts are stacked up from zero and negative parts down from zero. Every part is a solid,
  full-opacity fill: no outlines, no hatching, no alpha.
  * Removed: the hanging-outline rule (`comp_bars`, `comp_handles`, `sign_handles`), the surge hatch, the faded
    projection (0.55) and the faded last interval (0.4).
  * The 2024–25 column is marked "†", with the footnote "† 2024–2025: households consent-derived (not
    census-benchmarked)".
* **Line.** One annual line of dwellings built (in scope), observed 1992–2025 then the projection. It is drawn at year
  centres with straight segments (no PCHIP), no markers, in INK. The census-interval means are thin MUTED caps.
* **Checks (STOP).**
  * Up + down = net for every column and year (`draw._check_net`).
  * The census-interval means of the annual line equal the column nets (rtol 1e-9; all seven intervals agree).
  * The line equals the net in every projection year.
* **Pipeline years: a finding, and an author decision.**
  * **The gap.** In 2026–2027 the stacked parts are the stock-identity count: observed all-category building less the
    modelled retirement-village share, 30,096 and 36,340. D05's `dwellings_built_projection` is the in-scope floor area
    divided by the dwelling size held at its 2023–2025 mean: 30,045 and 35,540. The difference is −51 and −801. The
    cause is that the pipeline floor area is observed while the dwelling size is held.
  * **Earlier release.** v4.3.2 drew this gap without saying so.
  * **Decision.** The check stopped, and the author chose that in the pipeline years the line is the component sum.
    The note quotes the floor-area-based counts and differences, read from the data. No data are recomputed. A fix of
    the D05 export can follow in the next model run.
* **Unchanged.** The row of unexplained-building values at the top is kept.
* **Legend.** It lists the parts present: net replacement in the history and demolition replacement in the projection
  share one key and one entry. It adds the two line entries. The "negative part: outline" and "net total" entries are
  removed.
* **Note.** Rewritten: negative parts below zero, no fades, the line straight between annual values.
* **Audit.** The SF2 audit record shows 20 negative areas below zero, 0 filled negative bars and 0 rectangles below
  zero. The sign rule of `figures/audit.py` already accepts filled negative areas below zero: it flags only filled
  `negative_bar` rectangles, the outline convention of `bars_cumulative`, and band rectangles below zero. It was not
  changed.

**Component colours.** These are the requested defaults with the lightness adjusted for colour vision. A part that is
a demand band takes its `[demand_bands]` key.

* **Problem.** The requested defaults (`#7D9396`, `#8F6BB0`, `#4E8FB8`, `#B8B8B8`, `#C27BA0`, `#D98B5F`) left SF2b
  pairs below CAM02-UCS 10. The worst were vacancy / overbuild absorbed (1.5 under protanomaly) and new households /
  vacancy (2.9 under deuteranomaly).
* **Method.**
  * Only the CAM02-UCS lightness J' of the newer colours changed; hue and chroma (a′, b′) are kept, and the demand-band
    keys are fixed.
  * The search was coordinate line searches over J' (1-unit grid, in gamut), with 12 random restarts.
  * Objective: the smallest pairwise distance over normal vision and the three deficiencies, capped at 10, then the
    smallest total |ΔJ'|.
* **Result.** Every SF2b pair is ≥ 10.0 under every vision type. The total |ΔJ'| is 42, the same for every restart that
  reached the target.

| key | requested | adopted | ΔJ' |
|---|---|---|---|
| new_households | `#7D9396` | `#97AEB1` | +10 |
| replacement_surge | `#8F6BB0` | `#8A66AB` | −2 |
| unconsented_additions | `#4E8FB8` | `#5C9CC5` | +5 |
| retirement_villages | `#B8B8B8` | `#DCDCDC` | +12 |
| overbuild_absorbed | `#C27BA0` | `#9E5B7F` | −13 |
| unexplained_building | `#D98B5F` | `#D98B5F` | 0 |

* **SF5.** It changes with `overbuild_absorbed`.
* **SF1 and SF15.** SF1 renders unchanged (it draws no components). SF15 keeps `released_tl` (`#95C283`).
* **`docs/PALETTE.md`.** Its legacy groups 'Demand bands (Fig1, Fig2, …)' and 'History bands (Fig1)' now report pairs
  below 10: population growth / overbuild absorbed, and extra space / unexplained building. These pairs share no final
  figure. Fig1 draws the six display bands, where both parts sit inside market balance, and SF2b draws new households,
  not population growth. SF2b's own group passes.

**Final figures that still draw negative parts as outlines** (reported, not changed):

* **ED2a.** 7 outlined household-size-change segments.
* **SF5.** 26 outlined payback bars.
* **Fig2d.** It uses the outline rule of `draw.bars_cumulative`, but no cumulative band is negative in the committed
  data.

### ED4 and ED5: row numbers

* **Labels.** Each row with a note carries a superscript number, top to bottom, on the last line of its y tick label.
  ED5 uses one numbering for the y labels shared by both panels. `ed5_rows` now STOPs if the two panels order their
  rows differently.
* **Notes.** The note is a numbered list, "¹ <explanation>", in the same order. The explanation text is unchanged.
  `figure_plan.ED4_ROW_NOTES` / `ED5_ROW_NOTES` and the captions (and so `FIGURES.md`) carry the same list in Unicode
  superscripts.
* **Rendering.**
  * The bundled Liberation Sans has the superscript digits one to nine but no superscript zero (U+2070), which ¹⁰ and
    ²⁰ need.
  * A DejaVu Sans fallback for that glyph alone was tried and mismatched visibly.
  * The figures therefore draw the numbers with matplotlib mathtext (`$^{n}$`, the same font). Its superscripts are
    0.7 × the label size: about 3.9 pt on the 5.5 pt tick labels and 3.5 pt in the 5 pt notes. All other text stays at
    5 pt or more.
  * A literal "$" in a label (ED5 "current US$") is escaped.
* **Sizes.** ED4 is 223 mm high as saved and ED5 136 mm, both within `style.MAX_HEIGHT` (247 mm).

---

## Step 3: tests

* **Kept.** These protect the numbers: test_aesa, test_census_uc, test_decarb, test_decarb_item, test_demand_balance,
  test_events, test_households_per_consent, test_identities, test_mcstats, test_model_v3, test_model_v3_3,
  test_model_v4, test_model_v4_2, test_overbuild_2026, test_profiles, test_regression_model_v3 (the v4 lock), test_soil
  and test_validation.
* **New: `tests/test_figure_integrity.py`.** It holds, unchanged:
  * test_model_scripts_do_not_plot, test_bars_cumulative_end_at_net, test_stack_series_up_minus_down_is_net;
  * test_material_and_stage_values_never_negative, test_figures_leave_the_data_byte_identical,
    test_every_planned_figure_is_drawn_and_audited;
  * test_fig5_waterfall_panels_sum_to_totals, test_tl_steps_from_the_reference, test_fig5_net_positive_steps_reported;
  * test_fig5_column_totals_are_reference_minus_run, test_fig3_interval_from_the_draws;
  * test_fig1_annual_line_matches_census_interval_means, test_notes_stop_when_code_and_outputs_disagree,
    test_load_palette_rejects.

  It also adds:
  * `test_sf2b_up_plus_down_is_net`: every column and year, including a drawn column whose parts do not add up, which
    must stop;
  * `test_sf2b_line_means_equal_column_nets`;
  * `test_load_palette_rejects_opacity`: 1.2, −0.1, true, "0.5".
* **Retired to `tests/retired/`.** test_palette_file.py, test_figure_text_rules.py, test_figures_v3.py,
  test_figures_v3_3_1.py, test_figures_v3_3_2.py, test_figures_v4_3_2.py and test_reference_legacy.py.
  * Because test_reference_legacy.py is retired, `run_all.py --reference-legacy` no longer runs a `legacy_lock` step.
    The file can be run by hand from `tests/retired/`.
* **`tests/README.md`.** It says what each kept file protects, and that `tools/check_figure_text.py`,
  `tools/palette_check.py` and `tools/palette_coverage.py` are run by hand.
* **A regression found and fixed.** The first run of the kept suite failed in
  `test_identities::test_band_stack_is_the_total` with a KeyError for `surplus_vacant`. The new `styles` option of
  `draw.stack_series` looked up a part's style even when the part is all zero; it is now looked up only when drawn,
  as before. The same test passes on `main`.
* **Counts.**

| | collected | result | time |
|---|---|---|---|
| before (v4.3.2) | 278 | (v4.3.1 run: 255 passed, 2 skipped, with both profiles present) | |
| after (v4.3.3) | 250 | **214 passed, 36 skipped**, `PATHWAY_PROFILE=full` | 75 s |

  The 36 skipped tests are 2 AESA reproductions (the local-only workbook is absent) and 34 profile comparisons
  (`outputs/_light/` is not in this clone). No Monte Carlo or Sobol run is needed. `test_decarb_item` builds the seeded
  carbon-factor bootstrap setup, which runs no draws.

---

## Step 4: release

* **Render.** `python redraw.py --final` (600 dpi, `FIGURES.md`). `tools/figure_manifest.py` was rerun:
  `figure_manifest.csv` is unchanged.
* **Changed PNGs against v4.3.2.** Exactly four: SF2, SF5, ED4 and ED5. The other 27 are pixel-identical.
* **Visual check.**
  * SF2 and SF5.
  * ED4 and ED5: the superscripts render.
  * ED6 (typologies), ED7 (Sobol) and SF7 (lag variants).
  * The unchanged figures of the other new groups (ED3, SF1, SF6, SF8, SF15, Fig7) are pixel-identical to v4.3.2.
  * No clipping; legends are clear of the data.
* **`outputs/data`.** `git diff --stat -- outputs/data` is empty.

## Correction to the v4.3.2 release record

The v4.3.2 report said that `CHANGELOG.md` gained a v4.3.2 entry and that `CITATION.cff` was set to 4.3.2. Neither edit
was made: the command that would have made them did not run, and its result was not checked. Both files were
unchanged since MODEL v3.0.0. This release adds the missing v4.3.2 entry next to the v4.3.3 entry in `CHANGELOG.md`
and sets `CITATION.cff` to 4.3.3. `docs/CHANGELOG_v4_3_2.md` itself was committed with v4.3.2.
