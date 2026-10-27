# MODEL v4.3.0

Branch `release/model-v4.3.0`, from `release/model-v4.2.2`.

This file has two parts. **Part A** (below, first) is the first v4.3.0 pass: a figures-only update from stored outputs.
**Part B** (at the end) is the **clean release** before the Stats NZ 2023-base swap. It renumbers the figure suite again
(Part A's interim ED numbers are superseded by `outputs/data/ed_number_map.csv`), deletes the plotting code of every
figure outside the main / Extended Data / Supplementary sets, and reruns the whole pipeline at production size.

# Part A: figures-only update (no rerun)

**Scope.** Figures only; no model change. No Monte Carlo was run and the deterministic model was not rerun: every
figure was redrawn from the stored outputs with one `--figures-only` export (600 dpi PNG). The data were
byte-identical afterwards (`outputs/logs/figures_only_check.json`: changed = []).

**Added data file.** `outputs/data/ed_number_map.csv`, the Extended Data numbering. It was written from
`figure_plan.ED_NUMBER_MAP` by `tools/ed_number_map.py` before the export, and `pathways.py` now writes it with the
deterministic outputs.

Each changed PNG was checked visually: no overlaps. Figure tests: 35 of 35 pass. The ED10 maintenance-rule failure
reported in v4.2.2 is gone because ED10 is no longer rendered.

## Fig3 (main): shape-preserving interpolation (display only)

* **Caption note.** "Lines are shape-preserving (PCHIP) interpolation between annual values."
* **Method.** Every annual series of panel a is drawn with `scipy.interpolate.PchipInterpolator`, at 12 points per
  year (`draw.pchip`). This applies to:
  * the Monte Carlo median and the 50% and 90% band edges;
  * the Moderate and Ambitious Pathway and TL;
  * the AR and AtP lines and their zones.
* **Properties.** The curve passes through every annual value (asserted) and does not overshoot between neighbouring
  values.
* **Not used.** No moving average, LOWESS or ordinary cubic spline.
* **Stacked areas.** Panel a has none, so the per-component rule did not apply.
* **Bands.** The lower and upper edges are interpolated separately. On the fine grid the check lower ≤ median ≤ upper
  passed for both bands, so the linear fallback (`draw.pchip_band`) was not used; it is recorded in the figure note.
* **Segments.**
  * Fig3 has no history. The observed pipeline years (2026–2027, from consents already issued) and the modelled years
    (2028 on) are interpolated as separate segments that share the 2027 knot, so the observed → modelled join is not
    smoothed.
  * The 2026–27 segment has two points, so it is linear.
  * The budget lines are one segment.
* **Markers.** Small dots (1.4 pt) mark the annual values of the median and the three runs.
* **Unchanged.** The y-axis maximum stays at 1,540, and panel b is unchanged.

## Fig8b (main): Reference, Ambitious Pathway and TL on the paired draws

* **Data.** The stored Monte Carlo draws (`pathways/montecarlo_draws.csv`, n = 5,000). The Reference, Ambitious and TL
  LoE AR come from the same draw, so they share the same 2050 population.
* **Markers.**
  * Reference: grey square.
  * Ambitious Pathway: dark orange triangle.
  * TL: forest green circle, drawn last, larger and darker.
* **Axes and lines.** The y-axis is on a log scale with plain-number ticks. The AR line stays at LoE = 1. The TL
  threshold line (Firth logistic P(LoE AR ≤ 1) = 50%: 6.614 M, bootstrap 95% CI 6.611–6.616 M) keeps its label and
  stops below the legend.
* **P(LoE AR ≤ 1).** Proportion of draws, with the Wilson 95% interval (`mcstats.wilson`):

  | run | draws ≤ 1 | P(LoE AR ≤ 1) | Wilson 95% |
  |---|---|---|---|
  | Reference | 0 of 5,000 | 0.00% | 0.00–0.08% |
  | Ambitious Pathway | 1 of 5,000 | 0.02% | 0.00–0.11% |
  | Theoretical Limit | 2,494 of 5,000 | 49.88% | 48.49–51.27% |

  The TL value equals the stored `montecarlo_conditional_tl.json` value (asserted).
* **Unchanged.** Panel a.

## Extended Data

* **No longer rendered.** ED5 (pathways annual), ED6 (waterfalls by demand band), ED7 (TL Shapley and indicators) and
  ED10 (detailed demand bands).
  * They are removed from `figure_plan.PAPER_EXTENDED`, and their PNGs and audit records are removed from outputs.
  * Their code is kept in `figures/paper_extended.py`.
* **New ED5: Shapley attribution (order-independent)** (`ED5_shapley_attribution`), in ED7's place.
  * One row per lever L1–L9, in PAS 2080 order, grouped Avoid / Switch / Improve.
  * Three bars per row: Moderate (hollow, strategy colour), Ambitious (filled, strategy colour) and TL (TL green).
  * A total row, with the values labelled in Mt and as % of the Reference.
  * Bottom axis: Mt CO₂e. Top axis: % of the Reference cumulative carbon 2026–2050 (19,761 kt).
  * Data: the stored exact Shapley values, 2^9 coalitions per game (`pathways/shapley.csv`, games `levers_moderate`,
    `levers_ambitious`, `levers_tl`). Nothing was recomputed.
  * The title says "Shapley attribution (order-independent)", to set it apart from the sequential waterfalls of Fig4.
* **Shapley sum check.** The lever sum is compared with Reference − pathway cumulative; the tolerance is 0.1% and the
  figure stops if it is exceeded:

  | game | Σ levers (kt) | Reference − pathway (kt) | relative difference |
  |---|---|---|---|
  | Moderate Pathway | 5,459.650 | 5,459.650 | 1.7e-16 |
  | Ambitious Pathway | 9,494.443 | 9,494.443 | 0 |
  | Theoretical Limit | 15,338.501 | 15,338.501 | 0 |

  As shares of the Reference cumulative carbon: 5.5 Mt (28%), 9.5 Mt (48%) and 15.3 Mt (78%).
* **ED7 roll-out timing (was ED9).** Panels a and b are unchanged. New panel c shows the cumulative carbon 2026–2050 as
  the running sum, for Moderate and Ambitious under the three roll-out variants, in the same colour and line styles as
  a and b. The Reference cumulative is a grey line. Units are kt CO₂e. The 2050 end values equal `runs.csv`
  (asserted), in kt:

  | variant | Moderate | Ambitious |
  |---|---|---|
  | by 2030 | 13,737 | 9,350 |
  | by 2035 (adopted) | 14,302 | 10,267 |
  | by 2045 | 15,395 | 12,091 |

  Reference: 19,761 kt.
* **Old → new map** (`outputs/data/ed_number_map.csv`):

  | old | new |
  |---|---|
  | ED1–ED4 | ED1–ED4 (unchanged) |
  | ED5 pathways annual | not rendered |
  | ED6 waterfalls by demand band | not rendered |
  | ED7 TL Shapley and indicators | not rendered |
  | ED8 replacement variants | ED6 |
  | ED9 roll-out timing | ED7 |
  | ED10 detailed demand bands | not rendered |
  | — | ED5 Shapley attribution (new) |

* **References updated.**
  * The Fig4 caption now says "Shapley values in Fig7 and, per lever and pathway, in ED5" (was "split by demand band
    in ED6").
  * `figure_plan` module docstring (ED1–ED7), `PB_FIGURES`, `MAINTENANCE_ALLOWED`, `RETIRED`, and the `pathways.py`
    docstring.
* **Main figures.** Not renumbered.

## Files

`figures/draw.py` (`pchip`, `pchip_grid`, `pchip_band`), `figures/paper_main.py` (Fig3, Fig8),
`figures/paper_extended.py` (ED5 new, ED6 and ED7 renamed, ED7 panel c), `figure_plan.py`, `pathways.py` (writes the
map), `indexes.py`, `tools/ed_number_map.py`; outputs: PNGs, audit records, FIGURES.md, INDEX.md and
`data/ed_number_map.csv`.

# Part B: clean release (full rerun)

Branch `release/model-v4.3.0`. This is the last release on the Stats NZ 2018-base inputs before the 2023-base swap.
There is no model change: the compute code is the v4.2.2 code. The figure suite is renumbered and restyled to one set of
rules, the plotting code of every figure outside the paper sets is deleted, and every output is regenerated at
production size with the fixed seeds.

## Run

* **Pipeline.** `python run_all.py --profile full` from a wiped output tree, on commit `7a47703` (compute code
  unchanged since). The run stopped at the `indexes` step on a path pattern for the new Supplementary sub-folders. That
  step was fixed (`indexes.py`) and run by hand. No compute step was repeated.
* **Profile and seeds** (`outputs/run_meta.json`):
  * Monte Carlo: 5,000 Latin hypercube draws, seed 20260924.
  * PRCC / SRC: bootstrap 2,000 resamples.
  * Sobol indices (Reference): `scipy.stats.sobol_indices` (scipy 1.17.1; Saltelli 2010 first-order and Jansen total
    estimators). Base sample N = 1,024, so 1,024 × (5 + 2) = 7,168 model evaluations, seed 20260926. 95% confidence
    intervals by bias-corrected and accelerated (BCa) bootstrap, 999 resamples (`SobolResult.bootstrap`, which calls
    `scipy.stats.bootstrap(method='BCa')`). The global numpy generator is seeded at 20260927 because that call takes no
    generator.
* **Runtime (full profile).** 26 min 24 s from the first step to the figures, manifest and indexes, single process. The
  largest steps were:

  | step | seconds |
  |---|---|
  | pathways_mc | 887.4 |
  | boundaries (AESA) | 293.7 |
  | montecarlo | 229.2 |
  | sensitivity | 40.9 |
  | figures | 40.4 |

* **Other profiles.** The light profile (1,000 draws, used by the profile-equality tests) and `--reference-legacy` (the
  v2.1 Reference lock) were also rerun. Light: 7 min 33 s. Legacy: 9 min 10 s (its lock step failed first; see "Tests").
* **Final figures.** The visual check led to the figure-code fixes listed under "Rules sweep". They were exported once
  with `python run_all.py --profile full --figures-only` (600 dpi PNG). The data were byte-identical afterwards
  (`outputs/logs/figures_only_check.json`: 112 files, changed = []).

## Headline numbers (full profile)

| run | cumulative carbon 2026–2050 (kt CO₂e) | cumulative LoE of AR | cumulative LoE of AtP | P(LoE of AR ≤ 1), draws | Wilson 95% |
|---|---|---|---|---|---|
| Reference | 19,761.4 | 4.4642 | 17.756 | 0.00% (0 of 5,000) | 0.00–0.08% |
| Moderate Pathway | 14,301.7 | 3.2308 | 12.850 | 0.00% (0 of 5,000) | 0.00–0.08% |
| Ambitious Pathway | 10,266.9 | 2.3193 | 9.225 | 0.02% (1 of 5,000) | 0.00–0.11% |
| Theoretical Limit | 4,422.9 | 0.9992 | 3.974 | 49.88% (2,494 of 5,000) | 48.49–51.27% |

* **TL threshold.** The 2050 population at which P(LoE of AR ≤ 1) = 50% for the Theoretical Limit (Firth logistic) is
  6.614 M, bootstrap 95% CI 6.611–6.616 M. This is unchanged from v4.2.2.
* **Reference Monte Carlo.** The median is 19,708.8 kt and the 5th–95th percentile is 14,575–25,503 kt. The
  deterministic Reference sits at the 50.9th percentile.

## Changes against the v4.2.2 outputs

Every data file was compared with the stored v4.2.2 outputs (numeric relative difference per column / key).

* **Unchanged.** Floor area and carbon are bit-identical for every run, scenario and Monte Carlo draw.
* **AR base-window change.** One input changed: the AESA sector-emissions history for 2025. It was 1.169028e9 kg CO₂e
  and is now 1.169113e9 kg (+7.3e-5).
  * **Effect.** The 2016–2025 base-window mean Ī_sec,base went from 1,415,156,813.62 kg to 1,415,165,294.93 kg per year
    (+8,481 kg, +5.99e-6). Every AR boundary therefore rises by 5.99e-6, and every cumulative LoE of AR falls by about
    6e-6. LoE of AtP does not depend on the base window and is unchanged.
  * **Cause.** v4.2 Part B adopted the ERP/S household bridge, which changes the 2024–25 history. The deterministic
    pipeline was rerun then, but the AESA step (`boundaries.py`) and the Monte Carlo were not ("Monte Carlo. Not rerun"
    in `CHANGELOG_v4_2.md`; v4.2.1 likewise). The stored AESA outputs were therefore one history revision behind the
    model. The full rerun brings them into line.
* **No headline number changed by more than 1%.** The largest change in any number above is 6.7e-6 relative.
* **Relative differences above 1% (all on near-zero values or on files no figure reads):**
  * `pathways/montecarlo_importance.csv`, `src_hi` of the carbon index on LoE of AR (Reference): −0.0039557 to
    −0.0039542. The absolute change is 1.5e-6, on a near-zero coefficient.
  * `pathways/runs.csv`, `remaining_reduction_AR`: the largest absolute change is 8.7e-6 (TL from 2027: −0.448318 to
    −0.448327). The 0.7% relative maximum is on a value close to zero.
  * `aesa/sensitivity.csv`, `AR_vs_ref_pct`: 24.82732% to 24.82779% (row "AR base window 1992–2025"), and smaller.
  * `figure_source/D04_household_formation.json`, `D05_stock_and_vacancy.json`: the 2024–25 history under the ERP/S
    bridge (the same v4.2 Part B cause).
  * `figure_source/D25_annual_carbon_by_band.json`, `D26_cumulative_carbon_by_band.json`: the household-size band is now
    the signed v4.2.1 band (minimum −19.5 kt per year in 2041). These files had not been regenerated since v4.2.1.
  * D04, D05, D25 and D26 are no longer drawn by any figure (see "Deleted").
* **Text-label changes in data.**
  * `pathways/shapley.csv` `name`: 'Avoid' / 'Switch' / 'Improve' became 'Avoid Strategies' / 'Switch Strategies' /
    'Improve Strategy' (`naming.STRATEGIES`). Every reader was checked: figures, tests and tables use the strategy key,
    not the label.
  * `bands_display_map.csv` `display_label`: 'Market balance'.
* **Regression lock.** `tests/regression_model_v4.json` was recaptured with `tests/capture_regression_model_v3.py`
  (deterministic hashes from the light profile, which equal the full-profile hashes; Monte Carlo hashes per profile).

## Figure suite

Every figure is listed, with its file, script, data and caption stub, in `outputs/figure_manifest.csv` (new;
`tools/figure_manifest.py`, a pipeline step after `check_outputs`).

### Main (paper_main/): Fig1–Fig7

Fig1–Fig5 keep their content. Fig6 → Fig5 (solution space), Fig7 → Fig6 (lever attribution), Fig8 → Fig7
(uncertainty). The Fig3 y-axis maximum stays at 1,540.

### Extended Data (paper_extended/): ED1–ED10

The old → new map is in `outputs/data/ed_number_map.csv`.

| new | content | from |
|---|---|---|
| ED1 | Population, households, floor area | v4.2.2 ED1 |
| ED2 | Household formation and size | v4.2.2 ED3 |
| ED3 | Replacement variants | v4.2.2 ED8 |
| ED4 | Reference one-at-a-time sensitivity: paired tornado with group headers | diagnostic D16 |
| ED5 | Planetary-boundary sensitivity: (a) LoE of AR, (b) LoE of AtP | diagnostic D42 |
| ED6 | Monte Carlo input distributions | diagnostic D38 |
| ED7 | Sobol indices (first-order and total, BCa 95%) | diagnostic D20 |
| ED8 | Shapley attribution (order-independent) | Part A |
| ED9 | Each lever alone, annual (3 × 3) | diagnostic D31 |
| ED10 | Roll-out timing, with the cumulative panel c | v4.2.2 ED9 |

v4.2.2 ED2 and ED4 moved to the Supplementary set (SF3, SF5). v4.2.2 ED5, ED6, ED7 and ED10 are not rendered.

### Supplementary (supplementary/&lt;topic&gt;/): SF1–SF17

The list approved before the run, plus D22 and D34.

| SF | folder | content | from |
|---|---|---|---|
| SF1 | calibration | Households; household size vs population growth; households per consent | D02 + D04 a, b |
| SF2 | calibration | Vacancy, stock, dwellings per year by component, vacancy definition | D05 + D06 (panel d) |
| SF3 | calibration | Census replacement rates and variants | v4.2.2 ED2 |
| SF4 | calibration | Realised and occupied floor area, utilisation, consented size by typology | D08 + v4.2.2 SF6 |
| SF5 | calibration | 2026 overbuild absorption | v4.2.2 ED4 (D35 dropped as its duplicate) |
| SF6 | validation | Rolling-origin hindcast and the 2027 check | D14 |
| SF7 | validation | Zero vs 17-month completion lag | D44 |
| SF8 | validation | Reality checks against the 1991–2025 range | D15 |
| SF9 | boundaries | Budget construction (AR, AtP, population modifier, components) | D22 |
| SF10 | sensitivity | PRCC with bootstrap intervals | D40 |
| SF11 | sensitivity | Moderate Pathway one-at-a-time | D41 |
| SF12 | sensitivity | λ sweep | v4.2.2 SF4 |
| SF13 | sensitivity | L5 / L8 estimators | v4.2.2 SF5 |
| SF14 | montecarlo | Monte Carlo convergence | D37 |
| SF15 | montecarlo | Pathway Monte Carlo bands | D39 |
| SF16 | montecarlo | Conditional Theoretical Limit | v4.2.2 SF3 |
| SF17 | pathways | Theoretical Limit: need, release, re-occupation | D34 |

D22 is placed as a methods item before the sensitivity figures (new `boundaries/` folder). D34 comes last, in
`pathways/`. Numbering is continuous.

## Rules sweep (every figure)

* **One source for labels.** Every label comes from `naming.py`: run, pathway, strategy, lever and input labels
  (`INPUT_LABEL`, `SENSITIVITY_GROUPS`, `BOUNDARY_SENSITIVITY_GROUPS`, `MC_INPUT`, `LOE_AR`, `LOE_ATP`). Strategies are
  "Avoid Strategies", "Switch Strategies" and "Improve Strategy". No internal code names appear in any figure.
  * SF9 panel c shows the AESA components under plain-English labels (`figures/boundaries.PLAIN_COMPONENTS`). Each row's
    stored symbol is asserted before relabelling. The data file keeps the `aesa.py` notation.
  * SF9 panel c is a table filling its panel, below the title. Panel b is titled "Population modifier: New Zealand share of world population, relative to 2025" instead of
    the formula.
* **Colours by meaning.**
  * Tornado: input at the low end blue, high end orange, single alternative case grey (`draw.TORNADO_*`).
  * Run colours throughout. ED10 now draws the Ambitious Pathway in its own darker orange in panels b and c (it was the
    Moderate orange), and its legend shows the roll-out styles in grey.
  * The ED1 projection line uses the Reference colour.
  * The SF13 typology colours are explained in its legend (`style.TYPOLOGY`).
* **Units.** kt CO₂e throughout. ED8 changed from Mt to kt; its total labels read e.g. "5,460 kt (28%)". Every
  level-of-exceedance axis or label reads "Cumulative LoE of AR" or "Cumulative LoE of AtP" (`naming.LOE_AR`,
  `naming.LOE_ATP`).
* **PCHIP display interpolation for annual lines.** `scipy.interpolate.PchipInterpolator`, 12 points per year
  (`draw.line`, `draw.pchip`).
  * The curve passes through every annual value and does not overshoot between neighbours.
  * Segments are split at the history → projection join (2025 | 2026) and at the observed-pipeline → modelled join
    (2027), so neither join is smoothed.
  * Stacked areas: each component is interpolated separately and then stacked (`draw.smooth_parts`), so the stack
    still adds up on the fine grid.
  * Bands: both edges are interpolated, and lower ≤ median ≤ upper is checked on the fine grid. A linear fallback is
    logged if the check fails; none was logged in this run (`outputs/logs/figures.log`).
  * Not used for census-interval steps, step functions (SF8 removals history), bars, histograms or scatter.
* **Labels.** Tornado and bar labels are on two lines, centred on the widest label (`draw.two_lines`,
  `draw.centre_ticklabels`): ED4, ED5, ED8, SF11, Fig6. ED3 panel b no longer rotates its labels.
* **Legends and text.**
  * Fig6 legend: "Theoretical Limit" (was "Theoretical limit").
  * ED3 legend: the Reference run and the "Reference replacement" variant are named apart.
  * SF1 b: the 2024 and 2025 points have their own hollow markers, named in the legend (no in-plot labels over the
    scatter).
  * SF1 c: the legend has a white background over the census lines.
  * SF14: one legend below both panels, and thousands separators.
* **Output.** PNG only at 600 dpi. Panel letters are consistent across the suite. Every PNG of the final export (7 main,
  10 ED, 17 Supplementary) was checked visually for overlaps.
* **Population in physical units (ED6).** The population panel shows the 2050 New Zealand population of each draw, in
  millions (`pathways/montecarlo_draws.csv` `P_NZ_2050`). The figure checks that the Reference and pathway Monte Carlo
  draws are the same on every input column (to 1e-12, the CSV round-off).
* **Shapley sum check (ED8).** Σ levers = Reference − pathway, within 0.1% (the figure stops otherwise). The relative
  differences are 1.7e-16 (Moderate), 0 (Ambitious) and 0 (TL).

## Deleted (step 4; each removal grepped for readers first)

No computation, data table or function used by a test was deleted. `paper_main.reduction_by_band` and `REDUCTION_RUNS`
are kept because a test uses them. The diagnostics data files (`outputs/data/figure_source/D*.json`) are still written.

* **Plotting code deleted (no successor figure).**
  * `figures/paper_main.py`:
    * the SF1 model schematic (`sf1_schematic`, `_box`, `_arrow` and its step constants);
    * the SF7 reduction-by-demand figure (old `fig5`);
    * `RUN_COLOUR`, `PATHWAY_LABEL`.
  * `figures/paper_extended.py`:
    * `ed5` (pathways annual), `ed6` and `_waterfall_panel` (waterfalls by demand band), `ed8` (TL Shapley and
      indicators), `ed11` (detailed demand bands);
    * `sf1` (Monte Carlo scatter vs population, now in Fig7b);
    * `sf5` (consent sizes, merged into SF4 c);
    * `LEVEL_STYLE`, `WATERFALL_NOTE`.
  * `figures/calibration.py`: `d01`, `d03`, `d09`, `d13`, `d35`.
  * `figures/validation.py`: `d07`, `d10`, `d11`, `d12`, `d19`, `_bridge`, `_bridge_label`, `_neg_style`.
  * `figures/market_balance.py`: `d43`.
  * `figures/boundaries.py`: `d18`, `d21`, `d23`, `d24`, `d25`, `d26`, `d27`, `_area_handles`, `_bands_vs_boundaries`,
    `_net_handle`, `scen_line`, `VARS`.
  * `figures/pathways.py`: `d28`, `d29`, `d32`, `d33`, `d36`, `_ref_annual`.
  * `figures/sensitivity.py`: `d17`, `_rows`.
  * `figures/montecarlo.py`: `INPUT_LABELS` (moved to `naming.MC_INPUT`).
  * `tests/test_figures_v3_3_2.py`: `test_schematic_is_supplementary`, replaced by `test_figure_set_v4_3_0`.
* **Plotting code renamed into its new figure.**
  * `d02` + `d04` → `sf1_households`; `d05` + `d06` → `sf2_stock_vacancy`; `d08` → `sf4_dwelling_size`.
  * `d14` → `sf6_hindcast`; `d15` → `sf8_reality_checks`; `d44` → `sf7_completion_lag`; `d22` →
    `sf9_budget_construction`.
  * `d16` → `ed4_one_at_a_time`; `d42` / `d41` → `ed5_boundary_sensitivity` / `sf11_pathway_sensitivity`; `d40` →
    `sf10_prcc`.
  * `d20` / `d37` / `d38` / `d39` → `ed7_sobol` / `sf14_mc_convergence` / `ed6_mc_input_distributions` /
    `sf15_pathway_mc`.
  * `d31` / `d34` → `ed9_lever_annual` / `sf17_tl_dwellings`.
  * Main: `fig6*` → `fig5*`, `fig7` → `fig6`, `fig8` → `fig7`. `_two_lines` and `_centre_ticklabels` moved to
    `figures/draw.py` as `two_lines` and `centre_ticklabels`.
* **Outputs deleted.** The PNG and audit record of each of the following:
  * Every diagnostic: D01–D10, D12–D29, D31–D44 (`outputs/diagnostics/<group>/`, 42 PNGs). `figure_plan.DIAGNOSTICS`
    is now empty.
  * Superseded files:
    * `paper_main/Fig6_solution_space`, `Fig7_shapley_levers`, `Fig8_uncertainty`;
    * `paper_extended/ED2_census_replacement_rates`, `ED3_household_formation_size`, `ED4_overbuild_absorption`,
      `ED5_shapley_attribution`, `ED6_replacement_variants`, `ED7_rollout_timing` (Part A names);
    * `supplementary/SF1_model_schematic`, `SF2_mc_scatter_population`, `SF3_conditional_tl`, `SF4_lambda_sweep`,
      `SF5_hd_estimators`, `SF6_consent_sizes`, `SF7_reduction_by_demand`.
  * Figures that continue appear under their new numbers and folders (tables above).
  * `figure_plan.RETIRED` records the whole old → new map; it is printed in `outputs/FIGURES.md`.

## Tests

* **`tests/test_identities.py`: two tests updated to the v4.2.1 signed household-size band.** Both had failed since
  v4.2.1 (commit `79f42df`). They run the model in process, so the failure did not depend on stored outputs.
  * `test_history_reconstructed_by_demand_bands` used the pre-v4.2.1 decomposition (household-size band clipped at 0).
    It now uses the band the model draws, `hist_hs_pos`. This is valid under both definitions: before v4.2.1 the
    clipped part was credited back through `hist_avoided`, and since v4.2.1 `hist_avoided` = 0. The identity holds to
    3.7e-16.
  * `test_figure_bands_in_scope_sum_to_total` required the household-size band to be ≥ 0. It now allows either sign for
    `naming.SIGNED_BANDS = ('smaller_households',)`, a constant added to record the v4.2.1 definition. The
    sum-to-total checks are unchanged.
* **`tests/test_reference_legacy.py`: the v2.1 legacy lock, mapped to the v2.1 band definitions.** This test had also
  failed since v4.2.1. 143 of 179 locked arrays matched to 1e-12, including:
  * every total, the carbon by typology and the near-term join;
  * the engine's `c_gross`, `structural` and `d_hh`.

  The other 36 were band compositions that v4.2.1 redefined. The test now converts the current bands back to v2.1
  exactly: growth_v2.1 = growth − `hs_avoided`, household-size_v2.1 = max(0, household-size).
  * **2026–2050.** After this conversion every forward year equals the v2.1 fixture to a relative difference of 0, for
    the engine result and `df_forecast` at the 5th, 50th and 95th population percentiles.
  * **2025 (row 0 of the `df_forecast` band columns).** This row is not an engine result. It splits the observed 2025
    total by shares from the historical bands, which were redefined in v4.2 Part B and v4.2.1, so it cannot be mapped
    back. For 2025 the test checks the total against v2.1 (1e-12) and that the model's split adds up to it.
  * **For confirmation.** Excluding the 2025 split shares from the v2.1 comparison is a judgement call, so it is listed
    here for review. The v2.1 fixture itself is unchanged.
* **Results.** 246 passed, 2 skipped, on both the full and the light profile (65.7 s and 61.7 s). The two skipped tests are the cross-check against the AESA workbook `Absolute_Analysis.xlsm`, which is kept local only.

## Files

* Code: `figures/` (every module), `figure_plan.py`, `naming.py`, `layout.py`, `pathways.py`, `run_all.py`,
  `indexes.py`, `tools/figure_manifest.py` (new), `tools/ed_number_map.py`.
* Tests: `tests/test_figures_v3.py`, `test_figures_v3_3_1.py`, `test_figures_v3_3_2.py`, `test_events.py`,
  `test_model_v3_3.py`, `test_identities.py`, `test_reference_legacy.py`, `regression_model_v4.json`.
* Outputs: every file under `outputs/` (data, PNGs, audit records, `FIGURES.md`, `INDEX.md`, `figure_manifest.csv`,
  `run_meta.json`), and `docs/LEVERS_TABLE.md`, `docs/METHODS_DRAFT.md` (regenerated by the pipeline).
