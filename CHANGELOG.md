# CHANGELOG

Current release first. "Numbers" means the reported results in `outputs/data/`.

## model-v5.0.0: L1 at TL from age-specific headship (final model version)

**Numbers.** Only the TL family changes: L1 at TL, the TL runs (and their LOW / HIGH / VHIGH, from-2027 and fast
re-occupation variants), the games and summaries that contain them, and the TL Monte Carlo. The Reference, the
Moderate and Ambitious Pathways, S1-S3, every other lever and every Reference Monte Carlo, Sobol, one-at-a-time and
AESA value are unchanged to the printed digit (identity gate against the v4.10.2 full outputs: every differing file
traced to TL-family rows or new rows; the one non-TL column that moves is `central_draw_max_rel_diff` of
`pathways/montecarlo_summary.csv`, a maximum over all runs including TL, 2.2877e-14 -> 2.2832e-14).

| full profile | v4.10.2 | v5.0.0 |
|---|---|---|
| TL carbon 2026-2050 (kt); LoE AR / AtP | 4,177.0; 0.944 / 3.753 | 5,962.7; 1.347 / 5.358 |
| P(LoE AR <= 1), TL (Monte Carlo, Wilson 95%) | 60.92% (59.56-62.26%) | 0.04% (0.01-0.15%; 2 of 5,000 draws) |
| TL: 2050 population at which P = 50% | 6.693 M | not estimable (fewer than 10 draws within AR) |
| Committed after 2050, TL (kt) | 1,750.6-2,240.8 | 2,752.3-3,532.1 |
| L1 at TL alone (kt) | 14,160.7 | 20,653.1 |
| LoE 2028-2050, TL (AR / AtP) | 0.420 / 1.671 | 0.858 / 3.411 |
| Single-lever overlap, TL | 52.22% (44,635.5 vs 21,325.8 kt) | 48.77% (38,143.1 vs 19,540.1 kt) |
| Shapley share of L1, levers at TL | 30.23% | 14.52% |
| Avoid / Switch / Improve, levers at TL | 71.3% / 17.0% / 11.7% | 63.7% / 21.6% / 14.7% |
| Fig. 5 TL position (demand / intensity reduction) | 81.8% / 33.0% | 69.0% / 36.9% |
| Re-occupation share of need, TL | 0.4496 | 0.2876 |

The v4.10 setting (national 1991 household size regardless of age) is kept as a sensitivity row and reproduces the
v4.10.2 TL exactly (4,177.0 kt; P = 60.92%).

### L1 at TL from age-specific headship
* Data: Stats NZ 2013, 2018 and 2023 Census living arrangements (CEN23_FHH_036, CEN23_FHH_018, CEN23_FHH_041;
  CEN13_FHH_026, CEN13_FHH_030, CEN13_FHH_031) and the estimated resident population by age (DPE058AA), unmodified
  in `data/raw/census_living_arrangements/` and `data/raw/DPE058AA.csv` (MANIFEST rows with SHA-256);
  `data/build_census_headship.py` writes the derived tables.
* Headship by age group (0-14, 15-39, 40-64, 65+) per census, with households per family unit f_c and per person in
  other living arrangements g_c calibrated so that each census reproduces its own stated family and other
  multi-person households (stated basis, CEN23_FHH_041; unknowns allocated proportionally). Children stay a separate
  category with zero headship. Gates (STOP on failure): 0 < f <= 1, 0 < g < 1, f within 5% of f_2013; common-basis
  normalised rates within 2% of POPPR (15-39, 40-64, 65+); one-person people = one-person households.
* The TL rate of each age group is the lower of its census minimum and the Stats NZ propensity-B rate of that year;
  B enters as a ratio to its own 2023 base. S^TL = S_ref x (household size at TL rates / at 2023 rates) on the
  projected age structure (ratio method), with the speed limit of v4.10 and never below L1 Ambitious. In the
  Reference the speed limit binds in 2026-2027 and the Ambitious floor in 2040-2050 (S^TL 2050 = 2.5916 = L1
  Ambitious).
* Used everywhere L1 at TL enters: TL, Shapley games, waterfalls, Monte Carlo (per-draw ratio), instant TL, pool.
* Sensitivity: "L1 at TL: national 1991 household size regardless of age (v4.10)" replaces the age-standardised row.
* Back-check: the implied household size at the TL rates is at or above the observed one at every census 1991-2006
  (ratio form, ERP age shares), so "best observed since 1991" holds.

### Re-occupation pool on actual releases
* The pool now applies only in runs that release dwellings (cumulative releases R > 0 by 2050), not in every run
  with L1 or L2 at TL: pool predicate now on actual releases; L1 at TL releases none under the age-specific rule.
  Changed runs: 512 Shapley configurations (L1 at TL without L2 at TL), L1 at TL alone and the TL-from-Moderate
  {L1 at TL} subset; TL itself is unaffected by the predicate (L2 at TL releases).

### Population threshold
* Not extrapolated: outside the sampled population range it is reported as not reached.
* Not estimable when fewer than 10 draws fall in the rarer outcome class (10 events per variable; Peduzzi et al.
  1996); no curve is fitted and no line drawn (Fig. 7b, SF13). The Firth fit of the threshold and its bootstrap use
  the point estimate only (`mcstats.firth(..., intervals=False)`).

### Figures and tables
* Absorption shading removed. Extended Data renumbered (ED3 = old SF4 + OLF panel; ED4 = old ED3 a-b; ED5 = old
  SF3a + ED7; ED6 = old ED4; ED7 = old ED5 + two rows; ED8 = old ED6); old ED3c and ED8 move to the Supplementary
  figures (SF3, SF8); SF16 headship by census added. Maps: `outputs/data/ed_number_map.csv`, `sf_number_map.csv`,
  `st_number_map.csv`.
* ED7 rows "2028-2050 only (pipeline years excluded)" and "Whole-life accounting (committed emissions at
  construction)"; `outputs/data/loe_2028_2050.csv`. Full legends for every Extended Data figure; EDT1 footnotes for L3
  and L10.

### Release
* Version 5.0.0 in CITATION.cff, `.zenodo.json`, README and run_meta; the paper-DOI placeholder removed.

## model-v4.10.2: data freeze, IEA 2035 milestone, clean code and docs, publication metadata

The release candidate for model-v5.0.0.

**Numbers.** Only L10 at TL, the TL runs and the games and summaries that contain them change, through the IEA 2035
milestone (Step B). The Reference, the Moderate and Ambitious Pathways, every other lever and every Reference Monte
Carlo value are unchanged to the printed digit.

| full profile | v4.10.1 | v4.10.2 |
|---|---|---|
| Reference carbon 2026–2050 (kt); LoE AR / AtP | 25,502.8; 5.761 / 22.914 | unchanged |
| Moderate Pathway | 17,209.3; 3.888 / 15.463 | unchanged |
| Ambitious Pathway | 11,470.5; 2.591 / 10.306 | unchanged |
| TL | 4,171.3; 0.942 / 3.748 | 4,177.0; 0.944 / 3.753 |
| P(LoE AR ≤ 1), TL (Monte Carlo) | 61.14% | 60.92% |
| TL: 2050 population at which P = 50% | 6.694 M | 6.693 M |
| Committed after 2050, TL (kt) | 1,750.6–2,240.8 | unchanged (s(2050) unchanged) |
| L10 at TL alone (kt) | 21,712.8 | 21,778.1 |
| LoE 2028–2050, TL (AR / AtP) | 0.419 / 1.665 | 0.420 / 1.671 |
| Single-lever overlap, TL | 52.28% (44,700.8 vs 21,331.5 kt) | 52.22% (44,635.5 vs 21,325.8 kt) |
| Shapley share of L10, levers at TL | 7.98% | 7.85% |
| Shapley share of L10 at TL, TL from the Moderate Pathway | 9.06% | 8.90% |

The Moderate and Ambitious overlap (14.90%, 27.84%) and the 2028–2050 LoE of the Reference and the Pathways are
unchanged.

### Step A: clean code, tests and documentation (numbers byte-identical)
* Gate A: every file of `outputs/data/` byte-identical to v4.10.1 except text-only fields: the sensitivity row
  labels "Completion rate 0.95", "Completion lag 0 months (same calendar year)", "Overbuild never absorbed" and
  "2026 overbuild never absorbed" (without their version notes) and "Gap measured against the same-year requirement"
  (it read "...the 2026 requirement", wrong at the 17-month lag: the variant uses the requirement of the last observed
  year, 2027); the TL waterfall step labels ("+ L1 at TL: ..."); the TL disclaimer and notes of
  `pathways/theoretical_limit.json`; basis texts of `sensitivity/reference_carbon.csv` and `pathway_carbon.csv`; one
  data-basis label of `diagnostics/market_balance_history_projection.csv`; three keys of
  `aesa/results.json/one_at_a_time_ar_base` renamed with the rows (values identical).
* Removed: unused constants and functions in 13 modules, the release-zip reader of `data/build_consents.py` (no zip
  source exists), `figures/paper_main.reduction_by_band` (drawn by no figure) and the 2026-based overbuild sentence of
  the methods draft (no reported run uses it). Version history in comments is replaced by present-tense statements.
* The overbuild gap label: building 2027 − requirement 2028 (`tools/metrics.py`).
* User-facing names "Lx at TL" (assumption register, waterfall labels, SF10 legend, INDEX.md). The TL disclaimer
  states the TL rule.
* Tests: the regression lock is `tests/test_regression_model.py` (`tests/regression_lock.json`); the version-named
  test files are renamed by topic; the figure-redraw test draws into a temporary folder, so `git status` stays clean
  after `pytest` in both profiles. 263 tests (one removed with `reduction_by_band`, one added for the freeze).
* README in six sections; ARCHITECTURE is the module map and data flow; the OECD vacancy data are listed with the
  third-party data.
* `.zenodo.json` (software, 4.10.2, ORCID, affiliation, MIT; the paper DOI a placeholder), `LICENSE-DATA` (CC BY 4.0
  for `outputs/` and `data/derived/`), CITATION.cff 4.10.2 with ORCID and affiliation.

### Step B: data freeze and the IEA 2035 milestone
* `L10_S_MILESTONES = {2022: 0, 2030: 0.08, 2035: 0.27, 2050: 0.93}`: IEA (2023) Net Zero Roadmap, 2023 update,
  Cement, near-zero emission clinker production share (verified). The 2035 value lies below the former straight line
  2030–2050 (0.2925), so s(y) is lower in 2031–2049 and L10 at TL reduces slightly less.
* One data-freeze sentence, generated from the data files, in METHODS and README: data frozen on 22 November 2026;
  consents to September 2026; population estimates to the June 2026 quarter; Stats NZ 2023-base household
  projections; Dwelling and household estimates to the March 2026 quarter on the 2018 Census base (limitation kept).

**Checks:** full run 30 min 53 s; 263 tests pass in both profiles; palette coverage 0 findings; figure integrity,
`check_outputs` and `lever_audit.md` (all checks) pass; the regression lock re-captured from both profiles.

## model-v4.10.1: manuscript numbering

**Numbers unchanged.** No model run was made.

Every file under `outputs/data/` is byte-identical to v4.10.0, except these:
* the number maps `ed_number_map.csv` and `sf_number_map.csv` (v4.10.0 → v4.10.1) and the new `st_number_map.csv`;
* `metrics.json`: the two new metric blocks only; everything else is identical;
* `pathways/levers.json`: two text fields only, `L2/tl_note` and `L9/anchor` (§4). The same keys and every value are
  identical.

Figures changed only in their file names, and in one in-figure text: the ED5 row notes now read "as in Extended Data
Fig. 6" (they read "Fig. 4"). Every other PNG is byte-identical to its v4.10.0 file.

**Checks:**
* Tests: 263 passed in both profiles.
* Palette coverage: 0 findings. Figure integrity and `check_outputs` pass.
* `lever_audit.md`: all checks pass.
* The regression lock was re-captured. It changed in `pathways/levers.json` (the two text fields) and its commit
  stamp only; the lock covers data files, not figure names.

Step-by-step notes of this release: the git history of CHANGELOG.md.

## model-v4.10.0: material-level chain, final lever set (L2/L6/L9/L10 re-anchored), single TL rule (full run)

**Runs and checks**
- One full run (`run_all.py --profile full`), then `--profile light`; regression lock re-captured.
- Tests: 263 passed in both profiles.
- Palette coverage: 0 findings. Figure integrity and `check_outputs` pass.
- `lever_audit.md`: all nine checks pass.
- No "TLn" id remains in Methods, the tables, FIGURES.md or the audit; they read "Lx at TL".

**The Reference is unchanged.** These files are byte-identical to v4.9.0:
- `baseline/projection.json`, `baseline/annual.csv`;
- `aesa/annual.csv`, `montecarlo/draws_REF.csv`;
- `sensitivity/reference_carbon.csv`, `baseline/sensitivity_one_at_a_time.csv`.

Step-by-step notes of this release: the git history of CHANGELOG.md.

## model-v4.9.0: L10 Production decarbonisation, L8 on own paths, lever audit (full run)

**One full run** (`run_all.py --profile full`), then `--profile light`, and the lock re-captured
(`tests/capture_regression_model_v3.py`).

Checks:
* Tests: 262 passed in both profiles.
* Palette coverage: 0 findings.
* Figure integrity passes; `check_outputs` passes.
* `outputs/reports/lever_audit.md`: all seven checks pass. `run_all.py` now runs the audit after pathways and stops
  on a failure.

**The Reference is unchanged except for the new Extended Data Fig. 4 (ED4) row.**
* Byte-identical: `baseline/projection.json`, `baseline/annual.csv`, `aesa/annual.csv`, `montecarlo/draws_REF.csv`.
* The Reference Monte Carlo summary and committed emissions are unchanged.
* The 42 existing rows of `sensitivity/reference_carbon.csv` are identical (max difference 0.0).

Step-by-step notes of this release: the git history of CHANGELOG.md.

## model-v4.8.0: end-of-life decarbonisation in the committed range, ED/SF reallocation, figure tidy (full run)

**One full run** (`run_all.py --profile full`), then `--profile light`, the lock re-captured
(`tests/capture_regression_model_v3.py`). Tests: 258 passed in both profiles. Palette coverage: 0 findings. Figure
integrity passes. `check_outputs`: no stale terms.

**The 2026-2050 window is unchanged.** Checked against the v4.7.2 outputs:
* `pathways/runs.csv`: all 62 non-committed columns identical; new columns `committed_c1c4_upper_kt`,
  `committed_c1c4_lower_kt` and `committed_c1c4_held_share`.
* `pathways/montecarlo_draws.csv`: all 54 non-committed columns identical.
* `pathways/montecarlo_summary.csv`: the 24 window rows identical (NaN = NaN).
* `sensitivity/reference_carbon.csv`: all 41 existing rows identical; one row added (Module D, below).
* Byte-identical: `pathways/annual.csv`, the bands, Shapley, `baseline/annual`, `aesa/annual`, `montecarlo/draws_REF`.

Only committed quantities changed. The committed upper bound differs by 1.8e-12 kt, from the summation order.

Lock entries changed (9 files; all of them committed quantities, new keys or the Module D row):
* `baseline/projection.json`;
* `baseline/sensitivity_one_at_a_time.csv` and `baseline/sensitivity_annual_carbon.csv` (the Module D case);
* `pathways/runs.csv` and `pathways/levers.json` (the identity check `committed_c1c4_kt` -> `_upper_kt` / `_lower_kt`);
* `pathways/montecarlo_draws.csv` and `pathways/montecarlo_summary.csv`;
* `sensitivity/reference_carbon.csv`;
* `sensitivity/replacement_variants.csv` (`committed_lower_kt` only).

Step-by-step notes of this release: the git history of CHANGELOG.md.

## model-v4.7.2: documentation consistent with the locked method, references checked, main-paper lever table, figure tidy (no model run)

**No model, Monte Carlo or Sobol run; the methodology is locked.** Reports and figures were regenerated from the
v4.7.1 outputs (`tools/methods.py`, `tools/assumptions.py`, `tools/sensitivity_tables.py`, `redraw.py --final`).

**Numbers unchanged.** Every number in `outputs/data/` is identical. Two files differ only in text fields, reported here:
* `pathways/levers.json`: the L6 `s_ref_basis`, the L9 `anchor` and the `sources` dict. The new strings come from the
  code; the file was patched in place and checked equal to the old one in every other field. It is written only by a
  full `pathways.py` run.
* `sensitivity/reference_carbon.csv`: the citation year in the "basis" column of two rows (Christoforatos &
  Pickering 2025 -> 2026), rewritten by `tools/sensitivity_tables.py`.

Their two entries in `tests/regression_model_v4.json` are updated; no other lock entry changed. Tests: 258 passed,
0 skipped. Palette coverage and figure integrity pass.

Step-by-step notes of this release: the git history of CHANGELOG.md.

## model-v4.7.1: panel titles, Fig5 / Fig7 tidy, ED2b paths, Supplementary pass (cosmetics; no model run)

No model, Monte Carlo or Sobol run: every figure was redrawn from the committed v4.7.0 outputs (`redraw.py --final`).
**Numbers unchanged:** SHA-256 of all 115 files under `outputs/data/` and `outputs/reports/`, before and after, are
identical. Tests: 258 passed (`tests/test_figure_integrity.py` 32 passed); palette coverage: 0 findings. Font: Inter
(no font file added).

* **Panel-title rule** (all figures): a single-panel figure has no title; a multi-panel figure has a bold letter and one
  short sentence-case title per panel, with no colon, no "the" and no numbers. Values move to labels (Fig7a "Reference
  5.76" at the top of the reference line, as in ED4 / ED5) or to the note. Kept as panel identity: the lever ids (L1-L9),
  and the hindcast origin years of SF6 a-c. `figures/draw.panel(..., above_label=True)` lifts a title and its letter
  clear of a reference-line label (Fig7, ED5).
* **Fig5:** the "Cumulative LoE of AR" title above the side strip is removed. One marker size per run in the plane, the
  strip and the legend (the strip sizes): Theoretical Limit 6 (was 8 in the plane and the legend), Pathways 5 (was 6.5
  in the plane), levers 5, Reference 4; Ambitious hollow everywhere.
* **Fig7a:** the Completion rate and No 2026 data rows are removed (both stay in ED4 [9] and [14]; the note names them);
  the other rows are unchanged and keep their order.
* **Fig7b note:** a new sentence on the Theoretical Limit floor at low population, read from the draws and checked in
  code (STOP otherwise). In 434 draws (every draw below 6.03 M, none above 6.25 M), TL builds nothing after 2027:
  the floor area equals the 2026-27 pipeline, 9.48 Mm², and the reoccupation share is 1. The LoE AR flattens at
  median 0.61 (0.58-0.65); the carbon is independent of population (r = -0.02) and follows the carbon factors
  (r = 0.985).
* **ED2b:** two paths added, read from the outputs already written (`pathways/levers.json`, `pathways/annual.csv`; no
  figure-source change):
  * Stats NZ Medium B (L1 Ambitious), in palette `ambitious`;
  * the TL run's household size, Theoretical Limit (TL1), in palette `theoretical_limit`, rising at the rate limit
    to 2.79 at mid-2037 and held from 2038.

  The Reference is relabelled "Reference (Stats NZ Medium A)"; a caption line is added.
* **ED4 / ED5:** every Fig7a row and the two rows removed from it are present with their notes:
  * Living arrangements ED4 [1]; Population ED4 [2]; Household size ED4 [3]; Completion rate ED4 [9];
  * Completion lag ED4 [13]; No 2026 data ED4 [14]; Replacement ED4 [15]; Replacement half-life ED4 [16];
  * Soil order ED4 [17]; AR base window ED5 [3].

  No row was missing.
* **Supplementary pass:**
  * SF2b's top-row explanation moved to the note; SF2c y label "(dwellings per year)".
  * SF10: n and B moved to the note.
  * SF12: legend in two columns above the bands; the note uses the run names.
  * SF14b: y label added; SF14 note added.
  * SF8 titles made consistent ("Cumulative …").
  * ED6 x label "Half-life (years)".
  * ED10 b / g / h shortened, with their qualifiers moved to the note.
* **Captions:**
  * Fig5: the ruler has no plane floor; the stale axis range is removed.
  * Fig7: the row rule.
  * ED1 title: the band is the Stats NZ population 5th-95th percentile, not the Monte Carlo.
  * SF1 title: "population growth", not "arrivals".
  * Fig2: (a) demand type.
  * Fig7 note: run names.
  * The ED2 and Fig7 data sources are listed.
* **Other:** `naming.TL_AGE_STANDARDISED` added (`run_label` of the age-standardised TL run).

## model-v4.7.0: publication cleanup, one rule for the pathway levels, TL1 age-standardised sensitivity

The cleanup implements the decisions in the v4.7 audit (draft PR 29, closed without merging; README does not link to it).
After the cleanup, one full run (`run_all.py --profile full`) and then the light run. Every number below is read from
the v4.6.0 outputs (main after PR 28) and from this run.

Step-by-step notes of this release: the git history of CHANGELOG.md.

## model-v4.6.0: data freeze (consents to September 2026), committed emissions in the Monte Carlo, figure simplifications

One full run (`run_all.py --profile full`), then the light profile. Every number below is read from the outputs of
v4.5.0 (main after PR 27) and of this run.

* **Data freeze: consents to September 2026.**
  * `data/raw/BLD468601_20261111_075751_49.csv` (Stats NZ Infoshare, "Building consents by region (Monthly)", New
    Zealand, New, Actual; 1965M04-2026M09; "Last updated 03 November 2026") copied unmodified; MANIFEST row (sha256
    fefc9a63..., 2026-11-11).
  * `data/build_consents.py`: new reader `read_infoshare` for the wide Infoshare layout (six header rows, ".." =
    missing; the July 2026 zip reader `extract` kept for provenance); docstring names the new source. Same columns as
    before (Dwellings = Dwelling units, New, Number; Detached = Houses).
  * Revisions: every cell 1965-04..2026-07 equals the v4.5.0 file exactly (0 revised cells;
    `data/derived/consents_revisions.csv`, empty; the STOP at >1% before 2024 did not fire). The derived file gains
    two rows (2026-08, 2026-09). `tests/test_consents_freeze.py` rebuilds the derived file from the raw export and
    checks the MANIFEST checksum.
  * Pipeline unchanged (2026-2027 observed completions, 17-month lag). Where August-September 2026 enter:
    * Reference, pathways, Monte Carlo: nowhere. At L = 17 the 2027 completions are consents August 2025 - July 2026,
      already observed; the typology-mix window (2022-2026, lagged) and the 2026 nowcast (used only at L = 0) do not
      reach the new months; 2028 is modelled. Every Reference, pathway, TL and Monte Carlo number is unchanged to the
      last digit.
    * "No 2026 data" row: unchanged (it truncates the consents at December 2025); its note now reads "instead of
      consents to September 2026" (read from the data).
    * Completion lag 15 months: 2027 becomes a pipeline year (October 2025 - September 2026 all observed), 25,883 ->
      25,850 kt (+1.49% -> +1.36% vs the Reference).
    * Completion lag 0 months (MODEL v3.3, not shown): the 2026 nowcast is now the year to September 2026, 26,541.1 ->
      26,540.7 kt.
    * The MODEL v2.1-v3.3 reproduction tests pin `CONSENT_DATA_END = '2026-07-01'` (the data of those versions; no
      revisions since).
  * Freeze recorded in README ("Data freeze") and the Methods ("Data freeze and scope", read from the data files):
    consents to September 2026, population estimates to the June 2026 quarter, household projections 2023-base
    (released 11 November 2026).
  * Scope sentence (Methods): new dwellings only; alterations (no floor area published) outside scope, "about 12% of
    residential consent value in 2025 (Stats NZ BLD468601, 2025)" (stated, not computed: the supplied export holds the
    New series only); both budgets use the same new-build scope.
  * Hard-coded "July 2026" texts made data-driven (SF6d label at L = 0, the baseline draft) or corrected (comments in
    projection.py, validation.py, ARCHITECTURE.md).
* **Committed after-2050 emissions in the Monte Carlo.** For every Reference draw (5,000), `pathways.committed(ctx,
  gfa_t)` on that draw's floor area by typology, central repair and end-of-life factors; written per draw to
  `pathways/montecarlo_draws.csv` (REF_committed_*), summarised in `pathways/montecarlo_summary.csv`. STOP unless the
  central draw reproduces `baseline/projection.json` (max relative difference 0). Lower bound (the Fig3b column):
  central 9,728 kt; median 9,726; 50% interval 9,069-10,456; 90% interval 8,160-11,519 kt. Upper bound: central
  10,662, median 10,660, 90% 8,944-12,624 kt. C1-C4: central 5,702, 90% 4,785-6,753 kt. Fig3b note and the
  uncertainty Methods say the range comes from the floor-area uncertainty only. `tests/test_committed_mc.py`.
* **Old -> new** (v4.5.0 -> v4.6.0):

  | quantity | v4.5.0 | v4.6.0 | change |
  |---|---|---|---|
  | Reference cumulative carbon 2026-2050 (kt CO2e) | 25,503 | 25,503 | 0.0% |
  | Reference floor area 2026-2050 (Mm2) | 105.44 | 105.44 | 0.0% |
  | Household size 2050 | 2.464 | 2.464 | 0.0% |
  | Demand band carbon (kt): population growth | 9,776 | 9,776 | 0.0% |
  | household-size change | 3,597 | 3,597 | 0.0% |
  | extra space | 9,203 | 9,203 | 0.0% |
  | vacancy | 1,286 | 1,286 | 0.0% |
  | net replacement | 1,870 | 1,870 | 0.0% |
  | market balance (incl. the starting-surplus payback) | -668 | -668 | 0.0% |
  | (maintenance) | 438 | 438 | 0.0% |
  | Reference LoE AR / AtP | 5.761 / 22.91 | 5.761 / 22.91 | 0.0% |
  | Moderate Pathway carbon (kt) / LoE AR / AtP | 17,971 / 4.060 / 16.15 | 17,971 / 4.060 / 16.15 | 0.0% |
  | Ambitious Pathway carbon (kt) / LoE AR / AtP | 12,542 / 2.833 / 11.27 | 12,542 / 2.833 / 11.27 | 0.0% |
  | Theoretical Limit carbon (kt) / LoE AR / AtP | 4,079 / 0.921 / 3.67 | 4,079 / 0.921 / 3.67 | 0.0% |
  | P(LoE AR <= 1): Reference / Moderate / Ambitious / TL | 0 / 0 / 0 / 0.640 | 0 / 0 / 0 / 0.640 | |
  | TL threshold 2050 population, P = 50% (M) | 6.715 | 6.715 | 0.0% |
  | Sobol total indices, carbon (top 3) | z_pop 0.639, size 0.256, carbon 0.097 | unchanged | |
  | Committed after 2050, lower bound (kt), central | 9,728 | 9,728 | 0.0% |
  | Committed after 2050, lower bound, Monte Carlo 90% interval (kt) | not computed | 8,160-11,519 | new |

* **Figures.**
  * Fig3b: the 2026-2050 column filled in the Reference colour, no hatch; the Monte Carlo intervals as capped error
    bars (50% bold ink, thicker line and caps; 90% muted grey, thinner, longer caps; both at opacity 0.7, the new
    palette key `[opacity] fig3b_interval_bars`), the median a short tick; the committed column keeps its two hatches,
    denser (x and dots, 0.6 pt, legend swatches the same), with the same capped bars from the per-draw committed
    emissions; legend updated; the y top raised until the legend clears the bars (data-driven).
  * Fig7a: the parenthesised part of every y label one font step smaller (5.5 pt vs 6.6 pt after the panel's 1.1
    scaling; >= 5 pt checked) on the same baseline (`draw.stacked_ticklabels`); the completion-lag row back to 15-19
    months (no 0-month case; zero lag stays the SF7 counterfactual).
  * ED2a: the projection drawn like the history: stacked "From population growth" and "From household-size change"
    (annual areas from the D04 figure source, STOP unless they sum to the projected formation), negative parts solid
    below zero (no outlines, also in the history columns), the median line kept. ED2b: history as straight segments.
  * ED4 / ED5: the superscript machinery removed; each explained row label ends with "[n]", the notes are a list
    "[1] ...", "[2] ..." (same text). In figures/sensitivity.py 60 lines removed and 18 added (net -42):
    `SUPERSCRIPT`, `sup`, `SUP_GAP`, `SUP_DIGIT`, `label_numbers`, `ROW_LABEL_SIZE` and the bold 5-pt numbers gone;
    `tag(n)` added.
  * SF2: one "Market balance" band (palette `demand_bands.market_balance`) for the history stock-identity residual
    (was "Unexplained building"), the 2024-25 surplus, the 2026-27 overbuild and the absorption; the requested note;
    the top-row values kept (now labelled market balance). STOP check against Fig1's market-balance band
    (`bands_display_map.csv`, retirement villages excluded as SF2 draws them separately): the same sign in all 32
    intervals and years, and Fig1 = SF2 dwellings x in-scope floor area per dwelling in every projection year after
    the pipeline (rtol 1e-9). Passed.
  * Palette keys no longer drawn removed (palette_coverage): `[cumulative] fig3b_cumulative_carbon` (the group),
    `[components] unexplained_building`, `[validation] handover_history / handover_step`, and the fixed fades
    `interval_box`, `estimate_not_used_line` (with the unused `tail` path of `draw.history_estimated`). Kept, drawn
    only when their condition occurs: `census_markers.observed_total`, `highlights.release_binds`. palette_coverage: 0
    findings outside the palette; docs/PALETTE.md regenerated.
  * Also corrected (stale since v4.5.0): the Fig2 caption and the palette rules text still described negative
    cumulative bands as outlined.
* **Checks.**
  * Full test suite (full profile): 263 passed, 2 skipped (the local AESA workbook).
  * Regression lock re-captured: 4 deterministic files changed (baseline/sensitivity_one_at_a_time.csv,
    baseline/sensitivity_annual_carbon.csv, sensitivity/reference_carbon.csv, sensitivity/tornado.csv: the lag rows
    above) and 2 Monte Carlo files per profile (pathways/montecarlo_draws.csv, montecarlo_summary.csv: the committed
    columns); the light and full deterministic files are identical.
  * Every main figure, ED1-ED10 and SF1-SF14 looked at.

## model-v4.5.0: household-size tail, F2 limitation, figure revisions

One full run (`run_all.py --profile full`), then the light profile. Every number below is read from the outputs of
v4.4.0 (main after PR 26) and of this run. How the run went, in order:
the compute steps of the full run completed; its figures step stopped (ED4: the row notes, 73 mm, did not fit), so the
ED4 notes block was enlarged (30% of the figure height) and the figures redrawn from the data (`--figures-only`, 113
data files byte-identical). Looking at the figures then showed a 2049 step in the L1 Moderate / Ambitious paths (below);
after that fix the steps from `pathways` onward (pathways, pathways_mc, sensitivity_tables, metrics, results,
assumptions, methods) were re-run on the same code, and the figures, check_outputs, figure_manifest and indexes after
them. No step before `pathways` imports `levers.py`, so the earlier outputs are unaffected by the fix.

* **Household-size tail (all variants and runs).**
  * Rule: Hermite interpolation through the five-yearly Stats NZ knots with PCHIP (Fritsch-Carlson) derivatives at the
    interior knots; the end derivative at 2048 is the 2043-2048 secant slope; S is continued linearly at that slope in
    2049-2050 (`projection.S_TAIL = 'pchip_secant'`). The same rule for A / B, Low / Medium / High, the Reference, the
    pathways, TL and every Monte Carlo draw. MODEL v4.4 imposed a zero slope at 2048 and held S flat after it.
  * Medium A and the Reference annual carbon, 2043-2050:

    | year | S v4.4.0 | S v4.5.0 | carbon kt v4.4.0 | carbon kt v4.5.0 |
    |---|---|---|---|---|
    | 2043 | 2.4968 | 2.4968 | 965.5 | 965.5 |
    | 2044 | 2.4907 | 2.4915 | 960.4 | 934.7 |
    | 2045 | 2.4843 | 2.4866 | 959.4 | 907.4 |
    | 2046 | 2.4787 | 2.4821 | 926.7 | 886.7 |
    | 2047 | 2.4746 | 2.4776 | 868.4 | 880.1 |
    | 2048 | 2.4730 | 2.4730 | 777.9 | 881.4 |
    | 2049 | 2.4730 | 2.4683 | 714.4 | 878.3 |
    | 2050 | 2.4730 | 2.4635 | 703.7 | 869.4 |

    The zero end slope bent the 2043-2048 decline forward (faster in 2044-2046, then flat), so 2044-2046 carbon falls
    and 2047-2050 carbon rises; net +327 kt over 2026-2050.
  * ED4 rows (both shown, above the 0.1% rule): "After 2048: held flat (zero slope)" 25,176 kt (-1.28%; equal to the
    v4.4.0 Reference to 1e-9, which confirms the change is confined to the tail); "After 2048: PCHIP end slope"
    25,423 kt (-0.31%). The secant / end-slope "taper" rows of v4.4 are removed (`S_TAPER_YEARS` removed).
  * L1 (found on figure review): v4.4 held the High - Medium gap at its 2048 value (`L1_GAP_HELD_AFTER`), so in
    2049-2050 S_Ambitious = S_Medium + gap fell at the Medium slope (-0.0047 a year) instead of the High variant's own
    tail (-0.0020), a step of +0.40 Mm2 in the Ambitious L1 floor area in 2049. Under the flat tail the hold changed
    nothing. The gap is now taken in every year (each variant on its own tail; High >= Medium asserted in every year);
    `L1_GAP_HELD_AFTER` removed. TL is unaffected (TL1 holds S at the 1991 maximum).
* **F2 limitation (text).** The 2019-2023 household estimates remain on the 2018 Census base; Stats NZ has not rebased
  them. k is kept; with the census endpoints fixed, only the timing of household growth within 2019-2023 depends on it
  (`tools/baseline_draft.py`).
* **Extra space (text).** One sentence in the release methods: extra space grows with smaller households, because it is
  new households x (dwelling size - occupied area) (`tools/release_methods.py`). Extra-space carbon +133 kt (+1.5%).
* **ED7 / methods (text).** Population and household size are one grouped input (one z, perfectly dependent); their
  Sobol indices are grouped Sobol indices (Jacques, Lavergne & Devictor 2006, Reliab. Eng. Syst. Saf. 91,
  doi:10.1016/j.ress.2005.11.047; added to docs/REFERENCES.md).
* **Monte Carlo committed emissions: not added.** No existing function computes them per draw: `pathways.committed`
  uses the central event profiles and the C1-C4 factors, so per-draw committed emissions would need new modelling
  (bootstrapped event profiles and C1-C4 factors per draw). Fig3b states that the committed column has no Monte Carlo
  interval.
* **Old -> new** (v4.4.0 -> v4.5.0):

  | quantity | v4.4.0 | v4.5.0 | change |
  |---|---|---|---|
  | Reference cumulative carbon 2026-2050 (kt CO2e) | 25,176 | 25,503 | +1.3% |
  | Reference floor area 2026-2050 (Mm2) | 103.94 | 105.44 | +1.4% |
  | Household size 2050 | 2.473 | 2.464 | -0.4% |
  | Demand band carbon (kt): population growth | 9,776 | 9,776 | 0.0% |
  | household-size change | 3,421 | 3,597 | +5.2% |
  | extra space | 9,070 | 9,203 | +1.5% |
  | vacancy | 1,268 | 1,286 | +1.4% |
  | net replacement | 1,870 | 1,870 | -0.0% |
  | market balance (incl. the starting-surplus payback) | -668 | -668 | 0.0% |
  | (maintenance) | 438 | 438 | 0.0% |
  | Reference LoE AR / AtP | 5.687 / 22.62 | 5.761 / 22.91 | +1.3% |
  | Moderate Pathway carbon (kt) / LoE AR / AtP | 17,818 / 4.025 / 16.01 | 17,971 / 4.060 / 16.15 | +0.9% |
  | Ambitious Pathway carbon (kt) / LoE AR / AtP | 12,486 / 2.821 / 11.22 | 12,542 / 2.833 / 11.27 | +0.4% |
  | Theoretical Limit carbon (kt) / LoE AR / AtP | 4,079 / 0.921 / 3.67 | 4,079 / 0.921 / 3.67 | 0.0% |
  | P(LoE AR <= 1): Reference / Moderate / Ambitious / TL | 0 / 0 / 0 / 0.640 | 0 / 0 / 0 / 0.640 | |
  | TL threshold 2050 population, P = 50% (M) | 6.715 | 6.715 | 0.0% |
  | Sobol total indices, carbon (top 3) | z_pop 0.670, size 0.234, carbon 0.089 | z_pop 0.639, size 0.256, carbon 0.097 | |

  * TL, its Monte Carlo probability and the population threshold are unchanged to every digit: TL1 holds household size
    at the 1991 maximum (2.79), independent of the Reference path.
  * Sobol: the z_pop 95% interval (0.588-0.691) contains the v4.4.0 value.
* **Figures.**
  * Fig2d: no outline boxes; the negative market balance is a solid segment below zero; the net total is a black
    marker.
  * Fig3a: y top set from the data: 1,700 kt raised in 100 kt steps until the legend clears the 50% band and the
    pathway lines in its x-range; the result is 1,800 kt (at 1,700 the legend overlapped the 50% band).
  * Fig3b: the 2026-2050 column has a white fill and a faint hatch; the 90% / 50% intervals are the greys of the fans;
    the committed column is two hatched segments (B2/B4 cross-hatch, C1-C4 dots), no grey fills; the note says the
    committed column has no Monte Carlo interval. In both panels the 50% legend swatch overlays the 90% and 50% fills
    at their palette opacities, as drawn (Fig3a's swatch showed the 50% opacity alone; Fig3b's used a composite alpha
    not in the palette, flagged by tools/palette_coverage.py; now 0 findings).
  * Fig5: contours only at LoE 1-5; the AR line carries the label "LoE of AR 1"; the 1.25 / 1.5 / 2.5 contours removed.
  * Fig7a: bar height 0.6; the completion-lag row runs from 0 months (MODEL v3.3 case, the low end) to 19 months, with
    15 months as a tick and "0 mo" labelled at the bar end; tick labels have a white halo so the Reference line does not
    cross them. Fig7b title "Monte Carlo draws vs 2050 population".
  * ED3: legend one font step larger, extended under panel b.
  * ED4 / ED5: row-number superscripts at FONT_MIN (>= 5 pt), bold, smaller than the row labels (FONT_MIN + 1); the same
    numbers in the notes, whose text is FONT_MIN + 0.5. ED4 notes block 30% of the figure height; ED5 at 165 mm.
  * SF1: legend "Stats NZ household estimates as published (2018 Census base)"; the band is Low A - High A (checked
    against `HH_SIZE_PAIRED` and relabelled); 2024-2025 households are the model path (population / household size),
    drawn as the start of the projection line and named in the note, so their separate legend entry is dropped;
    history lines as straight segments.
  * SF2: the 2024-25 unexplained building is labelled "2024-25 surplus (carried into 2026)" (hatched; a STOP checks it
    equals the F1 residual, 9,020 a year, the +9.0 above the column); "Surplus absorbed (2024-25 surplus + 2026
    overbuild)"; the dagger note reads "2024-2025: households = population / household size (model), not
    census-benchmarked".
  * SF5: payback bars solid; the note says "Surplus still vacant" starts with the 18,966 starting surplus (a STOP checks
    U(2025) equals it).
  * SF14: "Need after the surplus payback"; the "Release constraint binds" entry is drawn only when a marker is.
* **Label audit** (2018-base wording, overbuild-only wording, consent-derived 2024-25, "held after 2043/2048"):
  Fig1 caption and note (starting surplus absorbed); SF5 title, curve label and note; `naming.VACANCY_WORDING` and the
  `overbuild_absorbed` band description; the ED4 / Fig7a row "Surplus absorbed (by 2030-by 2045)" and its note; SF1
  labels and note; SF2 labels, note and dagger; SF14 labels; the L1 text of the methods (gap in every year). ED10 and
  the other SFs: no hits, no change.
* **Checks.**
  * Full test suite (full profile): 259 passed, 2 skipped (the local AESA workbook).
  * Regression lock re-captured: 31 of 34 deterministic files changed (unchanged: the three history-only files,
    bands_history, history_unexplained, completion_lag_hindcast) and all 4 Monte Carlo files in both profiles; the light
    and full deterministic files are identical.

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
