# model-v5.0.0 report (final state)

Branch `release/model-v5.0.0`. One complete full run (PATHWAY_PROFILE=full, 5,000 draws, Sobol), 24 min 13 s. No
tag or release; no pull request edited. "v4.10.2" values come from the saved v4.10.2 full outputs.

## 1. Theoretical Limit definitions (final)

* TL rule (`levers.TL_RULE`): the most extreme value of each lever physically attainable while the housing system
  keeps functioning: a bound the system itself defines where one exists (L3 no demolition; L4 no space beyond the
  occupied area; L7 the lowest soil order; L9 zero site energy and transport), otherwise the best value observed (L1,
  L2, L5, L6, L8) or the most stringent documented scenario (L10); behavioural change is limited to the fastest
  observed rate (the L1 speed limit).
* L1 at TL = the national 1991 household size (2.7905), the census speed limit (0.0118 a year, 1996-2001; level
  reached in 2037.5), never below Ambitious. L1 Ambitious is S_ref + (B - A) and Moderate the midpoint (levers.py,
  unchanged). (Correction of the earlier report: Ambitious is not anchored to 2.7905.)
* `tl_households_per_person_fall` (levers.json L1; formerly `tl_v410_households_per_person_fall`) = **11.7%**: the
  1991 size held with the 2050 population needs 11.7% fewer households per person at every age than the 2023 census
  rates. Methods sentence (METHODS_DRAFT.md): "L1 at TL lies beyond any census at the age level: it requires 11.7%
  fewer households per person at every age than in 2023, more shared living than observed in any census since 1991
  (back-check, SI)." Back-check: observed households per person at given ages relative to the 2023 rates were 1.075
  (1991), 1.063 (1996), 1.060 (2001), 1.045 (2006), and the 2013 and 2018 adult rates were above 2023's.
* L2 at TL = Switzerland 1.31% (2022), recorded as the frictional-vacancy proxy; Sweden (OECD 0.25%) excluded, with
  the reason given by the author (Statistics Sweden counts only rental flats in multi-dwelling buildings vacant for
  immediate letting, over the whole stock; 0.8% of rental dwellings in 2021, 1.3% in 2024).
* L6 at TL = 80% (England), L10 at TL unchanged. Steel follows the IEA cement near-zero share path (8 / 27 / 93% in
  2030 / 2035 / 2050) as a stated assumption (METHODS_DRAFT.md and the EDT1 L10 footnote).
* EDT1 L10 footnote: Horup et al. (2025) Table S1 ("Scenarios represented in the background system (using IAM model:
  REMIND)"), column "GMST increase by 2100": RCP2.6 about 1.6-1.8 °C (SSP1 ~1.7, SSP2 1.6-1.8, SSP5 ~1.7), RCP1.9
  about 1.0-1.4 °C (SSP1 ~1.3, SSP2 1.2-1.4, SSP5 ~1.0), no climate policy 2.3-4.5 °C. The table gives no baseline
  period beyond "by 2100".
* Pool predicate (actual releases) and population-threshold rule (not estimable with fewer than 10 draws in the rarer
  class): kept.

## 2. L1 by-age sensitivity (Supplementary only)

| run | carbon 2026-2050 (kt) | LoE AR | LoE AtP | P(LoE AR <= 1), Wilson 95% |
|---|---|---|---|---|
| TL (central) | 4,177.0 | 0.944 | 3.753 | 60.92% (59.56-62.26%) |
| TL, L1 at TL from the lowest observed census headship by age | 5,962.7 | 1.347 | 5.358 | 0.04% (0.01-0.15%) |

The by-age rule needs 4.0% fewer households per person in 2050. It appears only in Supplementary Table 12, its Monte
Carlo row, the SF13 note and SF16 (headship by census); not in any Extended Data figure or table.

## 3. New L10 sensitivities (TL; every other lever at TL)

| row | carbon (kt) | change vs TL | LoE AR | LoE AtP | P(LoE AR <= 1), Wilson 95% |
|---|---|---|---|---|---|
| Theoretical Limit (central) | 4,177.0 | - | 0.944 | 3.753 | 60.92% (59.56-62.26%) |
| L10: near-zero factor on all material classes | 3,907.3 | -6.46% | 0.883 | 3.511 | 74.66% (73.44-75.85%) |
| L10: near-zero share 100% by 2050 | 4,159.5 | -0.42% | 0.940 | 3.737 | 61.78% (60.42-63.12%) |

* Check against the author's values (3,907 kt, 0.883; 4,159 kt, 0.940): both within 1 kt. Row (a) reproduces 3,907
  only when steel and the steel-dominated elevator keep their own documented factor (400/2,945 = 0.136) and every
  other class takes the cement factor 125/850 = 0.147; with the cement factor on steel too it is 3,909.0 kt. The
  adopted reading is the first (steel keeps its stricter documented factor). L8 at TL is recomputed on the variant's
  case paths, as for the central L10 at TL (without that, 3,896.5 kt).
* Placement: **ED8 panel b** (cumulative carbon on its own axis, centred on the TL; the two rows as bars from the TL
  line). Rows in ED7 would have stretched its LoE axes, which are centred on the Reference (5.76), and mixed a TL block
  into the boundary-definition rows.
* Supplementary Table 12 (`outputs/data/sensitivity/tl_sensitivity.csv`, new): these rows, the by-age row, the instant
  TL and fast re-occupation.

## 4. Identity gate (v4.10.2 -> v5.0.0, full outputs)

* Reference, Moderate, Ambitious, S1-S3 and all their Monte Carlo, Sobol, one-at-a-time and AESA outputs:
  identical. TL: 4,177.0 kt, LoE AR 0.944 / AtP 3.753, P 60.92%, committed 1,750.6-2,240.8 kt, 2028-2050 LoE
  0.420 / 1.671, Fig. 5 position 81.8% / 33.0%, pool share 0.4496: identical. `montecarlo_draws.csv`: every common
  column identical; Monte Carlo summaries and annual percentiles identical.
* (i) Pool predicate: L1 at TL alone 14,160.7 -> 14,006.5 kt (`runs.csv`, `annual.csv`, `bands*.csv`,
  `lever_annual.csv`, `lambda_sweep.csv` L1 tl row, `ordering_checks.json`); 512 Shapley subsets (256 in `levers_tl`,
  256 in `tl_from_moderate_pathway`: exactly those with L1 at TL and not L2 at TL), -153 to -536 kt (median -369);
  the TL1 and TL2 steps of the waterfalls; the TL Shapley values and `sequential_vs_shapley.csv` TL rows;
  `metrics.json` single-lever sum at TL (44,635.5 -> 44,789.7 kt; overlap 52.22 -> 52.39%);
  `theoretical_limit.json` count of runs using the pool (1,548 -> 1,035).
* (ii) New rows and renumbering: runs TL-L1-by-age, TL-L10-all-classes, TL-L10-share-100 (and their Monte Carlo
  columns and summaries), replacing TL-TL1-age-standardised; `sensitivity/tl_sensitivity.csv`, `loe_2028_2050.csv`,
  `pathways/headship_by_census.csv`; the two ED7 rows (`planetary_boundary.csv`, `aesa/results.json`); levers.json
  keys `L1/by_age`, `L8/at_l10_tl_variants`; `theoretical_limit.json` `tl1` (replaces `tl1_age_standardised`);
  number maps.
* (iii) Population threshold: 6.693 M (95% CI 6.690-6.695 M); `montecarlo_conditional_tl.json` identical.
* Other differences: text only (`levers.json` L2 note; `theoretical_limit.json` disclaimer with the TL rule), and
  `central_draw_max_rel_diff` of `montecarlo_summary.csv`, a maximum over all runs (2.2877e-14 -> 2.2832e-14).

## 5. Shapley shares at TL (carbon)

| lever | levers at TL v4.10.2 | v5.0.0 | TL from the Moderate Pathway v4.10.2 | v5.0.0 |
|---|---|---|---|---|
| L1 | 30.23% | 30.85% | 32.61% | 34.13% |
| L2 | 9.66% | 8.91% | 10.11% | 8.46% |
| L3 | 6.68% | 6.68% | 7.53% | 7.48% |
| L4 | 15.71% | 15.72% | 15.46% | 15.46% |
| L5 | 8.96% | 8.97% | 6.86% | 6.86% |
| L6 | 4.68% | 4.70% | 3.61% | 3.62% |
| L7 | 2.92% | 2.93% | 2.47% | 2.47% |
| L8 | 9.44% | 9.45% | 8.71% | 8.72% |
| L9 | 3.86% | 3.87% | 3.76% | 3.78% |
| L10 | 7.85% | 7.92% | 8.90% | 9.03% |
| Avoid / Switch / Improve | 71.25 / 17.04 / 11.71% | 71.13 / 17.07 / 11.79% | 72.56 / 14.78 / 12.66% | 72.39 / 14.80 / 12.80% |

Efficiency holds in every game and metric (largest |sum - (v(0) - v(N))| 3.6e-12 kt); bands sum to the run totals
(6.5e-16 relative).

## 6. Checks

* Lever audit: all 9 checks pass. `check_outputs`: pass. Every figure drawn.
* Tests: 271 pass in the light and the full profile after re-capturing `tests/regression_lock.json` (two added: the
  L10 sensitivities, the EDT1 footnote milestones).
* Clean clone (commit e663d32; new Python 3.11 venv): `pip install -r requirements.txt` 19 s; `PATHWAY_PROFILE=full
  pytest` 237 passed, 34 skipped (the light-vs-full comparisons, which need light outputs) in 52 s; `python run_all.py`
  (light) completed in 6 min 50 s, then 271 passed; `git status` clean.

## 7. Number maps

Extended Data (`outputs/data/ed_number_map.csv`):

| new | old |
|---|---|
| ED1 | ED1 |
| ED2 | ED2 |
| ED3 dwelling size | SF4 + OLF panel c |
| ED4 stock vacancy | ED3 panels a, b |
| ED5 replacement variants | SF3a (panel a) + ED7 |
| ED6 roll-out timing | ED4 |
| ED7 boundary sensitivity | ED5 + 2 rows |
| ED8 one at a time | ED6 + panel b (TL L10 sensitivities) |
| ED9 Sobol | ED9 |
| EDT1 | EDT1 (+ L3, L10 footnotes) |

Supplementary figures (`sf_number_map.csv`): SF1, SF2 same; SF3 vacancy definition <- old ED3c; SF4 <- SF5; SF5 <-
SF6; SF6 <- SF7; SF7 <- SF8; SF8 lever annual <- old ED8; SF9-SF15 same; SF16 headship by census (new).
Supplementary tables (`st_number_map.csv`): ST1-ST11 unchanged; ST12 Theoretical Limit sensitivities (new); ST13 limitations register (was ST12).

## 8. Manuscript number map (v4.10.2 -> v5.0.0)

| place | v4.10.2 | v5.0.0 | source |
|---|---|---|---|
| Abstract: TL LoE AR / P / AtP | 0.94 / 61% / 3.7 | unchanged | pathways/runs.csv; montecarlo_summary.csv |
| Results TL paragraph; Avoid alone (92.3%, LoE AR 5.76 -> 1.31) | | unchanged | pathways/shapley_subsets.csv |
| Fig. 5 TL reductions (82% / 33%); Fig. 7b threshold (6.69 M) | | unchanged | backcast.json; montecarlo_conditional_tl.json |
| 2028-2050 TL LoE (0.42 / 1.7); committed after 2050, TL | | unchanged | loe_2028_2050.csv; runs.csv |
| Discussion 11.7% (households per person at TL) | 11.7% | unchanged | levers.json L1 tl_households_per_person_fall |
| Shapley share of L1, levers at TL | 30.2% | 30.9% | pathways/shapley.csv |
| Shapley share of L2, levers at TL | 9.7% | 8.9% | pathways/shapley.csv |
| Shapley share of TL1 / TL2, TL from the Moderate Pathway | 32.6% / 10.1% | 34.1% / 8.5% | pathways/shapley.csv |
| Avoid / Switch / Improve at TL (if the Discussion "11.7%" is the Improve share) | 71.2 / 17.0 / 11.7% | 71.1 / 17.1 / 11.8% | pathways/shapley.csv |
| L1 at TL alone | 14,161 kt | 14,006 kt | pathways/runs.csv |
| Single-lever sum vs combined, TL | 44,636 vs 21,326 kt (52.2%) | 44,790 vs 21,326 kt (52.4%) | metrics.json |
| Methods TL rule | best value observed; logical bound where attainable | the author's TL rule (section 1) | levers.TL_RULE |
| Methods L1 at TL caveat | - | 11.7% sentence (section 1) | METHODS_DRAFT.md |
| New: TL L10 sensitivities (ED8 b, ST12) | - | 3,907 kt / 0.883 / 74.7%; 4,160 kt / 0.940 / 61.8% | sensitivity/tl_sensitivity.csv |
| New: TL with L1 by age (ST12) | - | 5,963 kt / 1.35 / 0.04% | sensitivity/tl_sensitivity.csv |
| ED numbering in text | see section 7 | | ed_number_map.csv |

## 9. Repository cleanup

Tracked: 378 files (code 30 modules, `figures/` 16, `tools/` 22, `data/` 13 builders + raw 29 + derived 19, `tests/`
28, `docs/` 4, `fonts/` 10, `outputs/` about 205).

| path | purpose |
|---|---|
| `run_all.py`, `runprofile.py`, `layout.py`, `indexes.py` | pipeline, run profiles, output paths, the output registry |
| `projection.py`, `engine.py`, `events.py`, `Building_factors.py`, `bands.py`, `gap_2026.py`, `household_headship.py` | stock, floor area, carbon, events, demand bands, the L1 caveat and by-age sensitivity |
| `boundaries.py`, `aesa.py` | AESA budgets and LoE |
| `levers.py`, `pathways.py` | levers, pathways, Shapley, TL |
| `MonteCarlo.py`, `pathways_mc.py`, `mcstats.py`, `Sensitivity.py`, `validation.py`, `Diagnostics.py` | uncertainty, statistics, validation, diagnostics |
| `naming.py`, `figure_plan.py`, `figsource.py`, `palette.toml`, `redraw.py` | names, figure registry, figure sources, palette, redraw with a palette |
| `figures/` | every figure from the data |
| `tools/` | tables, reports, checks (lever audit, outputs check, palette checks, figure text) |
| `data/` | raw inputs with MANIFEST, builders, derived inputs |
| `tests/` | tests and the regression lock |
| `docs/` | DATA.md (provenance), REFERENCES.md, PALETTE.md and its preview |
| `fonts/` | Inter and Liberation Sans with their OFL licences |
| `outputs/` | full-profile results, figures, reports |
| `README.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CITATION.cff`, `.zenodo.json`, `LICENSE`, `LICENSE-DATA`, `requirements.txt`, `.gitignore` | documentation, citation, licences, environment |

Removed: `tools/ast_equivalence.py` (one-off check that a refactoring left the code unchanged; not part of reproducing
the paper); unused functions `figures/draw.absorption_window` (shading removed), `figures/paper_extended.LV_by_year`,
`figures/style.registry`, `household_headship.households_per_person_fall`; a redundant `if True:` block in
`Building_factors.py`; the drawn notes of ED1, ED4, ED7 and ED8 and their helpers; the age-standardised sensitivity.
README provenance tables moved to `docs/DATA.md` (one copy); CHANGELOG entries v4.7.0-v4.10.1 condensed to their
summaries (1,557 -> about 830 lines; the step notes stay in the git history).

Kept but unsure (not removed):
* `data/raw/census_living_arrangements/CEN13_FHH_030.csv`, `CEN13_FHH_031.csv`: supplied with MANIFEST provenance,
  listed in the data tables, but read by no code.
* Palette tooling (`redraw.py`, `tools/palette_check.py`, `tools/palette_coverage.py`, `docs/PALETTE.md`,
  `docs/palette_preview.png`): supports the colour-vision statement of the figures; not needed to reproduce numbers.
* `tools/check_figure_text.py`: a figure-text check run by hand.
* `data/raw/national_population_estimates_june_2026.html`: release text kept with its MANIFEST row, not read.
* `fonts/LiberationSans-*`: fallback font used by `figures/style.py`.

## 10. README (as written)

See `README.md` (109 lines): what the model does and the paper ([PAPER TITLE], no DOI); the model in six steps;
headline results (generated block); repository structure; how to reproduce (requirements, light vs full, run time,
tests); data and licences (data freeze, provenance in docs/DATA.md, MIT / CC BY 4.0 / third-party terms); how to cite
(CITATION.cff; Zenodo DOI at release); contact (name, affiliation, ORCID; the issue tracker).

## 11. AI-attribution check

A case-insensitive search of every tracked file and file name for tool and vendor names and for attribution phrases: no hit other than the standard Python `.gitignore` template line about the Abstra framework. The assistant configuration file and folder are absent. Commits on the branch
are authored and committed as Gerras, with no trailers. Two merge commits on main (960dd56 and 6c96d51, 1 October 2026,
"Merge pull request #1 / #3") carry the name of their source branch, which names a coding tool; changing them would
need a history rewrite and force-push of main, which was not done.

## 12. Open items for the author

1. The two old merge-commit messages on main (section 11), if they should go: a history rewrite of main by the owner.
2. Verify the new reference entry Peduzzi et al. (1996) in docs/REFERENCES.md; add entries for Sacchi et al. (2023)
   (cited through Horup et al. Table S1) and Statistics Sweden (the Sweden exclusion), whose details were not
   checked here.
3. The Sweden figures (SCB 0.8% in 2021, 1.3% in 2024) are as supplied; not verified here.
4. OECD licence wording "the OECD terms and conditions": unverified (the OECD site is not reachable from this
   environment).
5. ED legends were drafted from the figure contents: review the wording.
6. SF16 position in the SI order (ST12/ST13 now follow the SI's first-citation order).
7. `outputs/reports/v5_0_0_report.md` is hand-written; `run_all.py` rebuilds `outputs/reports/`, so a later full run
   deletes it (`git checkout -- outputs/reports/v5_0_0_report.md`).
8. Zenodo DOI and paper title placeholders ([ZENODO-DOI] in AVAILABILITY.md, [PAPER TITLE] in README) until release.
9. Old tags still need the command block; the branch `tmp/attribution-test` still exists on GitHub.

## 13. Text sync with the manuscript and SI

Numbers: identity gate against the committed v5.0.0 outputs: 111 of 113 data files byte-identical; the two others
differ in text only (`pathways/theoretical_limit.json` definition note; `st_number_map.csv`). Every model value is
unchanged: Reference 25,503 kt (5.761 / 22.914); Moderate 17,209; Ambitious 11,471; TL 4,177.0 kt (0.944 / 3.753;
P 60.92%, Wilson 59.56-62.26%); instant TL 3,034; fast re-occupation 3,460; TL by age 5,963 (1.347); L10 rows 3,907.3
and 4,159.5; Shapley L1 at TL 30.85%; threshold 6.693 M.

1. Supplementary Tables: ST12 = Theoretical Limit sensitivities, ST13 = limitations register (was ST12)
   (`figure_plan.SI_TABLES`, `ST_PREVIOUS`; `st_number_map.csv` statuses "added" / "renumbered"; the ED8 legend,
   `indexes.py`, `tools/sensitivity_tables.py`, CHANGELOG, this report).
2. Wording: ED2 legend (L1 at TL returning to the 1991 maximum of 2.79, reached in mid-2037); SF16 title and note
   ("the by-age limit (sensitivity)"); `theoretical_limit.json` definition note ("L7 at TL applies to the floor area
   still built on new land under L6 at TL (80%)", from `levers.L6_S_TL`); METHODS_DRAFT.md demand-band and
   run-order paragraphs and the TL-constraints paragraph: the pool only in runs that actually release dwellings
   (`tools/release_methods.py`, `tools/pathways_methods.py`); CITATION.cff abstract with the TL rule.
3. Data: `CEN13_FHH_030.csv`, `CEN13_FHH_031.csv` (read by no code; `data/build_census_headship.py` uses only
   CEN13_FHH_026) and `national_population_estimates_june_2026.html` (not read, not cited) removed with their MANIFEST
   rows and mentions (docs/DATA.md, `tools/availability.py`).
4. References: Sacchi et al. corrected from 2023 to 2022 (*Renewable and Sustainable Energy Reviews* 160, 112311) in
   `levers.py` (EDT1 L10 footnote) and added to docs/REFERENCES.md (Horup et al. Table S1 prints "Sacchi et al., 2023");
   Statistics Sweden added; the Swiss FSO entry dated 2022; IEA (2023) already listed; docs/DATA.md has a table of the
   parameter values taken from publications (IEA 2023 and 2022, Swiss FSO, Statistics Sweden, DCLG).
5. Numbering: files and `sf_number_map.csv` / `ed_number_map.csv` match SF1-SF16, ED1-ED9 and EDT1. Fixed
   cross-references: "SF1-SF15" ranges (`figure_plan.py`, `indexes.py`, `layout.py`); "Extended Data Fig. 5" for the
   AESA row not shown (now Fig. 7; `boundaries.py`); "Extended Data Fig. 8 row 1" and "rows 4 and 5" replaced by the
   row names (ED8 has no row numbers; `figures/paper_extended.py`, `tools/baseline_draft.py`).
6. Paper-title placeholder "[paper title]": README.md (line 3), CITATION.cff (message), AVAILABILITY.md (code
   availability statement; `tools/availability.PAPER_TITLE`).
7. Stale-wording grep ("100% brownfield", "age-standardised", Sweden, "tl_v410", "TL-TL1-age-standardised", "4,171",
   "3,455", "5,951", "61.1%", "21,331"): the only remaining hits are the CHANGELOG entries of earlier versions (they
   describe those versions), the OECD source row and the exclusion note for Sweden (`data/build_oecd_vacancy.py`,
   `data/derived/oecd_hm112_vacancy.csv`, `levers.L2_TL_NOTE`), numeric coincidences inside data rows, and this
   report's history sections.

