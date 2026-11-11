# Audit for MODEL v4.7 (report only)

Branch `audit/v4.7` off `main` (`d217ae0`, v4.6.0 merged). The audit changed no code, data, outputs or tests. It ran
only reading and one in-memory deterministic TL re-run; no full profile, Monte Carlo or Sobol run. Every count below
comes from `git grep` / `git ls-files` on that commit. Repository: 165 versioned files outside `outputs/`, 11.6 MB.

---

## Part A: cleanup inventory

### A1. Code and data kept only for superseded versions

| # | path | what it is / why it exists | evidence of (non-)use | action | risk | saved |
|---|---|---|---|---|---|---|
| 1 | `projection.py`: `HH_SIZE_PATH = 'statsnz_2018'` branch: `load_national_pop_projection`, `extract_household_projection_block`, the 2018 branches of `statsnz_size_shape` / `household_size_path`, `FILE_HOUSEHOLDS_PROJ_2018`, `FILE_POP_SIZE_PAIR_2018`, `HOUSEHOLD_SHEET_PROJ_2018`, `POP_SIZE_PAIR_SHEET_2018` | household size of MODEL v2.1-v4.3.7 (2018-base); kept in v4.4 so that the old anchors could be reproduced | set only in `tests/test_events.py` (LEGACY) and `tests/test_model_v4.py` (V33); no reported run uses it | delete together with A1-3 and A1-4 | none for outputs (lock-provable); loses the old-version reproduction | ~85 lines |
| 2 | `data/Householddata.xlsx` (123 KB), `data/subnational-population-projections-2018base-2048.xlsx` (151 KB) | 2018-base family and household projections and the 2018-base population used to pair them | read only by the branch in A1-1 | delete with A1-1 | none | 274 KB |
| 3 | `tests/test_events.py::test_whole_life_with_a45_held_reproduces_v2`, `::test_none_reproduces_the_frozen_anchor`, the `LEGACY` dict, `tests/regression_pb_v2.json` | reproduce the baseline-PB_v2 anchors (whole life at construction, 2018-base, no lag, rate 0.95, never-absorbed overbuild) | pins numbers of v2.1; needs A1-1, `CONSENT_DATA_END='2026-07-01'`, `S_TAIL='hermite_clamped'`, `STARTING_SURPLUS='none'` | delete (git tag `baseline-PB_v2` keeps the anchor) | loses a back-compatibility guard; the current accounting is guarded by `test_within_window_plus_committed_equals_whole_life` and the lock | ~25 lines + 2.2 KB |
| 4 | `tests/test_model_v4.py::test_v33_reference_projection_reproduced`, `::test_v33_pathway_runs_reproduced`, `V33`, `v33_flags`, `tests/v3_3_runs_fixture.json` | every MODEL v3.3.2 run reproduced to 1e-9 under the v3.3 settings | pins v3.3; needs A1-1 and the switches `TL1_SPEED_LIMIT`, `TL_SURPLUS_POOLING` | delete (tag `model-v3.3.2` keeps it) | as A1-3 | ~45 lines + 14.5 KB |
| 5 | `levers.TL1_SPEED_LIMIT`, `pathways.TL_SURPLUS_POOLING` | on/off switches added so v3.3 could be reproduced | only `True` is ever used; `False` only in `v33_flags` (A1-4) | fold into constants (remove the off branches) after A1-4 | none (lock) | ~15 lines |
| 6 | `projection.COMPLETION_LAG = 0` (two-point W) and the `lag_w` argument carried through `engine.census_interval_rates`, `MonteCarlo`, `gap_2026`, `validation`, `export_figure_sources` | completion timing before MODEL v4.0 (replaced by `COMPLETION_LAG_MONTHS`) | always 0; a guard refuses combining it with the monthly lag; `lag_w` is 0 in every run | delete the two-point W path (keep `lag_w=0` as a literal or drop the term) | low; touches engine signatures; lock proves identity | ~40 lines |
| 7 | `FROZEN_RUN` (`PATHWAY_FROZEN=1`): `layout.frozen_run` and the frozen path helpers, the conditional defaults of `DECARB_MODE` / `DECARB_A45` / `ACCOUNTING` in `projection.py` | separate frozen-technology run of v2.x | not a `run_all` step; the frozen-technology row is now an explicit settings row (`Sensitivity.FROZEN_CASE`, `boundaries`) | delete the env switch; keep `ACCOUNTING`/`DECARB_*` as plain settings | none (lock) | ~30 lines |
| 8 | `data/consentdata.xlsx` (55 KB) | the consent workbook supplied before v4.0 | README: "superseded … not read by the model"; only a docstring mention in `data/build_consents.py` | delete, or keep as supplied record (decision D4) | none for outputs | 55 KB |
| 9 | `data/raw/building-consents-issued-july-2026.xlsx` (185 KB) | July 2026 release workbook (provenance of v4.0-v4.5) | read by no script; the July zip (actual source of v4.0-v4.5) is not versioned; v4.6 proved the BLD468601 export identical for 1965-04..2026-07 | delete with its MANIFEST row, or keep (decision D4) | provenance of earlier tags only | 185 KB |
| 10 | `tests/regression_v3.py`, `tests/capture_regression_model_v3.py` | helpers of the current **v4** lock, named after v3 | used | keep; rename `*_v4` (cosmetic) | none | 0 |

### A2. Tests (166 test functions; 265 with parameters)

(a) protects reported numbers or data integrity; (b) protects a figure / data identity; (c) pins an old version, a
switch no reported output uses, or a cosmetic detail.

| file | n | a | b | c | the (c) tests and notes |
|---|---|---|---|---|---|
| test_aesa | 13 | 11 | 0 | 2 | `test_manuscript_ar_boundaries_2025_2029`, `test_manuscript_ssec_constants_match_workbook` (always skipped: need the local `Absolute_Analysis.xlsm`) |
| test_census_uc, test_committed_mc, test_consents_freeze, test_decarb, test_soil | 7 | 7 | 0 | 0 | |
| test_decarb_item | 10 | 10 | 0 | 0 | `test_mc_bootstrap_stream_unchanged` duplicates the lock (keep: fails earlier, clearer message) |
| test_demand_balance | 3 | 0 | 3 | 0 | diagnostic report only; the third skips when its file is absent |
| test_events | 12 | 8 | 2 | 2 | (c) A1-3; (b) `test_every_figure_is_planned`, `test_no_historical_carbon_in_figures` belong in test_figure_integrity |
| test_figure_integrity | 19 | 0 | 19 | 0 | |
| test_households_per_consent | 2 | 0 | 0 | 2 | documents why the DHE bridge was rejected (`HH_BRIDGE='dhe'`, not used) |
| test_identities | 22 | 20 | 2 | 0 | |
| test_mcstats | 10 | 10 | 0 | 0 | statistical correctness against statsmodels / scipy |
| test_model_v3 | 17 | 15 | 2 | 0 | `test_material_and_stage_values_nonnegative` duplicates test_figure_integrity's |
| test_model_v3_3 | 15 | 13 | 2 | 0 | `test_shapley_efficiency_against_run_totals` overlaps `test_model_v3.test_shapley_efficiency`; `test_fig6_*` now test Fig5 (names stale) |
| test_model_v4 | 10 | 8 | 0 | 2 | (c) A1-4 |
| test_model_v4_2 | 10 | 8 | 1 | 1 | `test_projection_start_mode_has_no_observed_year` (`START_MODE='projection'`, a diagnostic switch) |
| test_overbuild_2026, test_profiles, test_regression_model_v3, test_sensitivity_rules | 15 | 15 | 0 | 0 | |
| test_validation | 1 | 0 | 0 | 1 | `test_check_2026_pending_and_seasonal`: the zero-lag 2026 check, never reported (SF6d uses the pipeline check) |
| **total** | **166** | **125** | **31** | **10** | |

Proposed: remove the 10 (c) tests together with what they alone keep alive (A1, A3), merge the two duplicates, move
the two figure tests out of test_events, rename `test_fig6_*` → `test_fig5_*`.

### A3. Pipeline steps, tools and settings that no reported output uses

| item | evidence | action | risk | saved |
|---|---|---|---|---|
| `projection.HH_BRIDGE` (`'dhe'` branch) | only `'erp_S'` is used; `'dhe'` appears in no run or row | delete branch and switch | none (lock) | ~15 lines |
| `projection.START_MODE` (`'projection'`) | only `'observed'`; `'projection'` only in the (c) test | delete branch, switch and test | none (lock) | ~15 lines |
| `tools/assumptions.RUNTIME_ONLY` lists `QUICK_RUN` | no such setting exists | drop the name | none | 1 line |
| `tools/baseline_draft.py` `run_mode` banner ("run_all.py --quick") | `run_all.py` has no `--quick` (profiles only) | delete the banner | none | 3 lines |
| `tools/ast_equivalence.py`, `tools/check_figure_text.py` | not in `run_all`; referenced only in README / ARCHITECTURE | keep as developer tools, list them under "developer tools" | none | 0 |
| Monte Carlo LOW / HIGH / VHIGH variants (`montecarlo/*_LOW|HIGH|VHIGH.csv`) | read only by `boundaries.mc_runs` for the per-variant AESA Monte Carlo table in the Methods; ~3/4 of the `montecarlo` step and much of `boundaries` (612 s) | keep if the per-variant MC table is reported; else run the Monte Carlo for REF only (decision D5) | changes reported tables | ~10 min per full run |
| `pb_methods`: "Monte Carlo with a 20-year AR base (not adopted)" | a not-adopted variant re-reported in the Methods | cut from the Methods (keep in data) | none | ~15 lines |
| `OBSERVED_FILL` (Fig1), `highlights.release_binds` (SF14), the zero-lag branches of SF6d / `check_2026` | drawn only when their condition occurs; not in the current outputs | keep (guarded, cheap) | none | 0 |

### A4. Redundant code (output-identical, provable by the lock)

| item | now | proposal | saved |
|---|---|---|---|
| month names | 4 implementations: `paper_main._month`, `baseline_draft._month_name`, a literal month list in `figures/sensitivity.py`, an inline `calendar` call in `figures/validation.py` | one `naming.month_year(iso)` | ~15 lines |
| docs copies | `docs/METHODS_DRAFT.md`, `docs/LEVERS_TABLE.md` are byte copies of `outputs/reports/` (written by `tools/methods.py`) | keep `docs/` only (or only `outputs/reports/`), one writer | 113 KB duplicate |
| Shapley efficiency | tested twice (A2) | keep one | ~15 lines |
| legacy branches A1-1, A1-5…7, A3 | see above | remove | ~200 lines in total |

### A5. Documentation

| doc | role for a reviewer | finding | proposal |
|---|---|---|---|
| README.md (219 lines) | question, headline results, how to run, provenance | good; provenance table still has `[placeholder]` for 6 supplied files (A6) | keep; fill the placeholders |
| ARCHITECTURE.md (918 lines, 62 KB) | model chain, equations | header says "MODEL v4.3.4"; much overlaps METHODS_DRAFT; §11 "Run modes" and parts of §4.8/§10 carry version history | cut to the model chain and equations (~400 lines); history goes to CHANGELOG |
| docs/METHODS_DRAFT.md (680 lines, generated) | methods, assumption register, limitations | the reviewer-facing text; includes not-adopted variants (A3) | keep; trim not-adopted tables |
| docs/LEVERS_TABLE.md | Table 1 | fine | keep |
| docs/REFERENCES.md | references | fine | keep |
| docs/PALETTE.md + `docs/palette_preview.png` (2.6 MB) | figure styling | not needed by a reviewer; the PNG is the largest file in the repo | keep PALETTE.md; regenerate the preview at 100 dpi or drop it |
| CHANGELOG.md (15 releases, 39 KB) | history | fine as history; the place for removed version notes | keep |
| outputs/reports/*.md (11 files) | generated reports | RESULTS.md, ASSUMPTIONS.md, METHODS_DRAFT.md are the reviewer set; gap_2026, overbuild_2026, market_balance, reconciliation, scenarios, reality_checks, validation are diagnostics | keep generated; index them as "diagnostic reports" |

**Final doc set:** README (question, results, run, provenance, data freeze) → ARCHITECTURE (chain + equations) →
METHODS_DRAFT (generated) → LEVERS_TABLE → REFERENCES → CHANGELOG / CITATION; diagnostics under `outputs/reports/`.

### A6. Data provenance

| file | MANIFEST | used | build script | gap |
|---|---|---|---|---|
| `data/raw/*` (20 versioned) | yes, every one | all except A1-9 and `national_population_estimates_june_2026.html` (release text, cited in README) | n/a | none |
| MANIFEST rows without a versioned file | `Absolute_Analysis.xlsm` (local only, documented), `Horup_2025_SI_mmc1.xlsx` (in `refs/`, not versioned; `build_horup.py` handles its absence), `building-consents-issued-july-2026.zip` (not versioned) | | | **`NZ_pop.xlsx`: a MANIFEST row, no file, no code** → delete the row |
| `data/derived/*` (13) | n/a | yes | every one has a `data/build_*.py` | none |
| `data/histpopdata.xlsx`, `data/popdata.xlsx`, `data/occ-unocc-2013.xlsx`, `data/oldhouseholddata.xlsx` | no (except popdata) | yes (projection, MonteCarlo, build_census) | none (supplied) | README rows say "[placeholder]" for table ID / download date: **fill or re-download** |
| `data/material_item_map.csv` | no | yes (5 modules, tested) | none (curated by the author) | document as an author-curated mapping in README |
| `data/building_data.xlsx` | yes | yes | n/a | none |

### A7. Ranked list

**Safe cuts (output-identical; the regression lock proves them):**
1. Dead switches and branches: `HH_BRIDGE` 'dhe', `START_MODE` 'projection', `COMPLETION_LAG` / `lag_w`, `FROZEN_RUN`, `QUICK_RUN`, the `--quick` banner (~105 lines).
2. One month-name helper; remove the duplicate tests; rename `test_fig6_*`, `regression_v3` → v4.
3. One copy of METHODS_DRAFT / LEVERS_TABLE; delete the `NZ_pop.xlsx` MANIFEST row; fill the README placeholders; ARCHITECTURE header.

**Cuts needing a decision:**
4. The 2018-base path and its data and the v2 / v3.3 reproduction tests and fixtures (A1-1…5; ~170 lines, 291 KB) — decision D3.
5. `consentdata.xlsx`, the July 2026 raw workbook (240 KB) — D4.
6. The LOW / HIGH / VHIGH Monte Carlo and the 20-year-base MC table — D5.
7. ARCHITECTURE cut to ~400 lines; the 2.6 MB palette preview — D6.
8. The 2 manuscript AESA tests that only run on the author's machine — D3.

**Keep:** the regression lock, every (a) and (b) test, all `data/raw` sources with MANIFEST rows, the generated reports,
the developer tools.

---

## Part B: methodological review of the pathways

### B1. The levers (cumulative carbon 2026-2050; Reference 25,503 kt)

| lever | definition | Reference | Moderate | Ambitious | TL | source of Ambitious / TL | phase-in | Shapley Amb. / TL (kt) | TL flag |
|---|---|---|---|---|---|---|---|---|---|
| L1 Household size | S path (households = population / S) | S 2050 2.4635 (Medium A) | 2.5027 | 2.5420 (Medium A + Stats NZ High − Medium gap) | S = 2.7905 (1991), at the fastest inter-census change 0.0118/yr (1996-2001) | Amb.: Stats NZ 2023-base High A (see B4-1); TL: model history maximum | logistic 2026→2035; TL reaches 2.79 in 2037.5 | 2,193 / 6,639 | **yes**: not age-standardised (B2) |
| L2 Vacancy | stock vacancy v | 5.39% (2023 census) | 4.70% | 4.01% (1996 census minimum, one definition) | v = 0 | observed minimum / definitional zero | logistic → 2035 | 1,196 / 2,883 | **yes**: zero frictional vacancy is not physically possible |
| L3 Building lifetime | cut in demolition and the recent surge, d | 0 | 0.20 | 0.40 (Pellan et al. 2024, −40% demolition) | no demolition, no surge | European scenario study / definitional | logistic → 2035 | 771 / 1,477 | **yes**: no building reaches end of life in 25 years |
| L4 Extra space | share f of the margin above occupied area | 0 | half of Ambitious | Detached 0.412, Townhouses 0.095, Apartments 0.110 (smallest NZ consent sizes 1990 / 1998) | f = 1 (size = occupied area) | observed NZ minimum / definitional | logistic → 2035 | 1,708 / 3,346 | **yes**: no circulation or non-occupied space |
| L5 Occupancy density | design density ratio r | 1 | 0.910 | 0.819 (HD q0.15, n = 16, 95% CI 0.732-0.960) | best single case per typology (Detached 0.710) | case studies | logistic → 2035 | 2,531 / 1,905 | mild: one case (n = 1) |
| L6 Brownfield-first | share of new floor area on previously developed land s | 0.088 (current run) | 0.339 | 0.59 (England 2018-21, DLUHC 2022) | s = 1 | peer country / definitional | logistic → 2035 | 1,304 / 1,219 | **yes**: highest observed is 0.89 (London) |
| L7 Soil-aware planning | cut in soil carbon loss per m² x | 0 | 0.073 | 0.146 (Christoforatos, Pickering & Schipper 2026) | lowest soil order everywhere (−54%) | authors' own study / physical floor | logistic → 2035 | 273 / 538 | mild: spatial feasibility of putting all growth on the lowest-SOC soils |
| L8 Material carbon | A1-A3 ratio r | 1 | 0.914 | 0.827 (HD q0.15, n = 14, 95% CI 0.607-0.950) | best single case (Detached 0.530) | case studies | logistic → 2035 | 1,749 / 2,053 | **yes**: Detached TL is one outlier case (SD_2) |
| L9 Construction stage | A4-A5 factor path | Resch 1%/yr (0.779 in 2050) | 0.389 in 2050 | linear to 0 in 2050 (Zero Carbon Act s. 5Q; Oslo 2025) | A4-A5 = 0 | legislated target / definitional | target linear to 2050 × logistic ramp; TL zero by 2035 | 1,235 / 1,366 | **yes**: A5 includes site waste (assumed eliminated) |
| **sum** | | | 7,531 | 12,961 (= 25,503 − 12,542) | 21,424 (= 25,503 − 4,079) | | | | |

### B2. TL1 diagnostic: age-standardised household size

**Data.** The repo has living arrangements by age (0-14, 15-39, 40-64, 65+) only for the 2023 base year and the
2028-2048 projections (POPPR_FHH_008). No historical census propensities by age are present: the 2018-base workbook
has households by type only, and CEN23_* are totals. So the 2023 propensities are used, as instructed. The Stats NZ
Medium B projection, whose propensities are modelled on the 2001-2023 censuses, is shown as a second bound; it is a
projection, not an observation.

**Method** (`scratchpad/audit/tl1_headship.py`, not in the repo):
1. Headship rate by age:
   h_a = one-person + f·(couple partners/2 + two-parent partners/2 + one-parent parents) + g·other.
2. f = 0.9452 and g = 0.1803 are calibrated so the 2023 rates give the Stats NZ 2023 family and other-multi-person
   households; one-person people equal one-person households exactly.
3. S(y) = Σ people_a(y) / Σ h_a · people_a(y), on the Medium A age structure.

**Validation:** with 2023 propensities this gives 2.7409 / 2.6762 / 2.6101 / 2.5672 / 2.5461 / 2.5253 for 2023-2048,
against the Stats NZ Medium A values 2.7409 / 2.6885 / 2.6325 / 2.5840 / 2.5479 / 2.5236 (within 0.02).

| alternative TL1 level | 2048 S (method) | 2050 S on the model's rebased path | TL carbon (kt) | TL LoE AR |
|---|---|---|---|---|
| current: 1991 maximum | — | 2.7905 | 4,079 | 0.921 |
| highest observed propensity of living with others (2023, the only observed year) | 2.5253 | 2.4635 (= Reference) → TL rule floors it at Ambitious, 2.5420 | 6,714 (+2,635) | **1.517** |
| lower headship of 2023 or Stats NZ Medium B, by age group | 2.6313 | 2.5669 | 6,129 (+2,050) | **1.385** |

How the TL rows were computed:
- **Re-run:** quick, deterministic and in memory: `pathways.run` with every lever at TL, the same speed limit, and
  `params['L1']['tl']` replaced by the path. Nothing was written.
- **Check:** the unmodified run reproduces the reported TL exactly (4,079.1 kt, 0.9215).
- **What the current TL1 implies:** S 2.79 in 2050 needs about 11.7% fewer households per person than 2023, at every
  age. No observed age-specific propensity in the repo supports that.
- **What drives the 1991 value:** a younger age structure. Applied to the 2050 population, the 2023 propensities give
  2.46.
- **Effect on the headline:** with an age-standardised TL1, TL no longer meets AR (LoE AR 1.38-1.52). The finding that
  "TL is within the AR budget in 64% of draws" rests on TL1.

### B3. Internal consistency

| check | result |
|---|---|
| Moderate = midpoint of Reference and Ambitious | holds in every lever's native parameter: L1 and L9 per year; L4 / L5 / L8 per typology; L2 4.70 = (5.39 + 4.01)/2; L6 0.339 = (0.088 + 0.59)/2 (`test_moderate_is_the_exact_midpoint`). Not a midpoint in carbon (L1, L5 are nonlinear); expected, stated in Table 1 |
| phase-ins end 2035 | every level uses the same logistic w (2026 → 2035). Exceptions: L9 Ambitious target is itself linear to 2050 (full only in 2050; so L9 is phased twice); TL1 under the speed limit reaches 2.79 in 2037.5; instant-TL (from 2027) and by2030 / by2045 are labelled sensitivities |
| TL steps and Shapley subsets use the Reference rules | yes: every run is `pathways.run(ctx, …)` on the Reference context (`boss_state('REF')`): the same household-size tail (pchip_secant), starting surplus (carry), A propensities, 17-month lag. Two TL attributions exist (`levers_tl` from the Reference; `tl_from_moderate_pathway`), reported in different places |
| levers defined before v4.4 vs 2023-base households | L1 gap recomputed from the 2023-base variants (v4.5: every year); L4 occ_ref uses the current S(2035); L6 s_ref recomputed (0.0881; its label "the v3 Reference" is stale text); **TL1 = 2.7905 (1991 history) and its speed (1996-2001) were defined before v4.4 and were not revisited against the 2023-base age structure** (B2) |

### B4. Rough or hard-to-defend points

| # | point | why | suggested fix |
|---|---|---|---|
| 1 | L1 Ambitious = Stats NZ High − Medium gap | within one propensity the 2023-base variants differ only through their population projections (v4.4 finding), so the "gap" is an age-structure effect of a larger, younger population, not behaviour; it also clashes with the pairing (95th population ↔ High A) | anchor Ambitious on living-arrangement propensities (e.g. Medium B, or the age-standardised headship rates) |
| 2 | TL1 = 1991 household size | not age-standardised; B2 shows it needs 11.7% fewer households per person at every age than 2023 | an age-standardised TL1 (needs census living arrangements by age, 1991-2018 — data request), or report TL with and without TL1 |
| 3 | TL2 v = 0, TL3 no demolition, TL4 size = occupied area, TL6 s = 1, TL9 A4-A5 = 0 | definitional zeros beyond physical or observed evidence; the TL is called a thought experiment, but its LoE (0.92) is read against AR | use bounded TLs (frictional vacancy ~2-3%; London 0.89; best observed) or label each TL "definitional" in Table 1 |
| 4 | L5 / L8 TL = best single case | n = 1; the L8 Detached TL (0.530) is one outlier case | use the minimum of the bootstrap distribution's lower CI or a trimmed minimum |
| 5 | L9 double phase-in | logistic w × linear-to-2050 target: Ambitious reaches zero only in 2050 while every other lever is full by 2035 | phase L9 with the target alone, or state the exception in Table 1 |
| 6 | L3 Ambitious from Pellan et al. 2024 | European scenario study, not NZ evidence | cite NZ demolition evidence or label as a peer value |
| 7 | L7 Ambitious from the authors' own paper | single study, self-citation | add an independent source or label as "authors' estimate" |
| 8 | TL re-occupation machinery (pool, constant share, release constraint, surplus pooling, instant TL) | complex for a thought experiment; hard to explain | simplify to "released dwellings re-occupied up to need" and move the detail to the SI |
| 9 | two TL attributions (from the Reference and from the Moderate Pathway) | reader may compare the wrong one | keep one in the main text |
| 10 | L5 / L8 HD q0.15 with n = 14-16 | wide intervals (0.73-0.96, 0.61-0.95) | report the interval in the main lever table (it is in Table 1) and run the Ambitious Pathway at both CI ends |

---

## Decisions needed

1. **TL1:** keep the 1991 level, replace it with an age-standardised level (2023 propensities: TL LoE AR 1.52; lower
   of 2023 / Medium B: 1.38), or request the census living-arrangement tables by age (1991-2018) and derive the
   highest observed propensity by age.
2. **L1 Ambitious anchor:** keep the High − Medium gap, or move it to a propensity-based anchor (Medium B).
3. **Old-version reproduction:** remove the 2018-base path, its data, the v2 / v3.3 anchor tests and fixtures, the two
   manuscript AESA tests (A1, A2; ~170 lines, 291 KB), relying on the git tags.
4. **Superseded consent files:** delete `data/consentdata.xlsx` and `data/raw/building-consents-issued-july-2026.xlsx`,
   or keep them as provenance of earlier tags.
5. **Monte Carlo scope:** keep the LOW / HIGH / VHIGH Monte Carlo and the 20-year-base MC table in the Methods, or run
   the Monte Carlo for the Reference only.
6. **Docs:** cut ARCHITECTURE to the model chain (~400 lines) and drop or shrink the 2.6 MB palette preview.
7. **TL levels beyond evidence** (TL2, TL3, TL4, TL6, TL8, TL9): keep as definitional limits with a flag in Table 1,
   or bound them by observed values.
8. **L9 phase-in:** keep the double phase-in (logistic × linear to 2050) or align it with the 2035 rule.
