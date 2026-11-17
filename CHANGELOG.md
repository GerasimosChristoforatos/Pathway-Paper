# CHANGELOG

Current release first. "Numbers" means the reported results in `outputs/data/`.

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

### 1. End of life (C1-C4) in the committed range
**Rule** (`Building_factors.C14_HELD_CLASSES`, Methods). The split is by material chemistry, not by a ratio
threshold.
* **Held at 2025 in both bounds:** the classes whose end of life is dominated by the release of their own material
  carbon at disposal (TIMBER, PLASTERBOARD, PLASTICS, PAINT, SIP).
* **The energy part:** all other classes (demolition, processing, transport). That includes CONCRETE: its weighted
  C1-C4 / A1-A3 of 0.12-0.13 reflects the low A1-A3 of unreinforced low-strength in-situ concrete (the 17.5-20 MPa
  items: 0.131-0.136). It is not material carbon, because concrete releases none at disposal.
  * Upper bound: 2025 factors.
  * Lower bound: the generic construction-stage factor e^(-0.01 (t - 2025)) (Resch et al. 2021) at 2050, held after
    it (x 0.779).
* The v4.7.2 rule held all C1-C4 at 2025.
* The B2/B4 events keep their own C1-C4 share at 2025 factors (in the window and after it). Changing it would move
  the 2026-2050 results.

**Code.**
* `Building_factors.class_factors`: pools the A1-A3, C1-C4 and D factors per class, the same way as the typology
  factors. It writes `factors/factors_material_class.csv` and STOPs unless the classes pool back to the typology
  factors.
* `events.c14_split` and `events.c14_committed`: the split and the committed C1-C4.
* `projection.COMMITTED` and `pathways.committed()`: new keys `C_upper_kt`, `C_lower_kt`, `C_held_kt` and
  `C_held_share`, with upper = B_upper + C_upper and lower = B_lower + C_lower.
* `pathways_mc`: committed lower and upper per draw for the Moderate and Ambitious Pathways and the TL as well, plus
  their summary rows.

**Fig. 3b** keeps the lower bound. The note gives the C1-C4 range and the held share.

**Whole life and reconciliation.** The whole-life row is unchanged: whole life at construction, at 2025 C1-C4. It
reconciles with the committed upper bound (identity holds, `outputs/reports/reconciliation.md`). The reconciliation
now has separate C1-C4 upper and lower rows, and two new identities:
* 2025 factors: committed C1-C4 upper = lower;
* decarbonised: committed C1-C4 upper unchanged.

**Class table** (`outputs/reports/reconciliation.md`). Items: the case-study items. Weighted: the pooled class factors,
weighted by the Reference 2026-2050 cohort floor area by typology.

| class | end of life | C1-C4 / A1-A3, items | weighted | D / A1-A3, items | weighted |
|---|---|---|---|---|---|
| STEEL | energy | 0.038 | 0.026 | -0.369 | -0.368 |
| REINFORCED CONCRETE | energy | 0.066 | 0.078 | -0.043 | -0.038 |
| CONCRETE | energy | 0.094 | 0.122 | -0.012 | -0.006 |
| OTHERS | energy | 0.023 | 0.067 | -0.001 | -0.003 |
| PLASTERBOARD | held | 0.792 | 0.872 | 0.000 | 0.000 |
| GLASS | energy | 0.007 | 0.008 | 0.000 | 0.000 |
| ALUMINIUM | energy | 0.023 | 0.023 | -0.643 | -0.640 |
| PLASTICS | held | 0.283 | 0.144 | -0.005 | -0.014 |
| TIMBER | held | 2.153 | 1.530 | -0.460 | -0.343 |
| PAINT | held | 0.018 | 0.019 | -0.009 | -0.008 |
| FIBRE CEMENT | energy | 0.029 | 0.030 | -0.048 | -0.047 |
| GLASS WOOL | energy | 0.009 | 0.009 | -0.050 | -0.050 |
| BRICKS | energy | 0.050 | 0.050 | -0.050 | -0.050 |
| SIP | held | 0.000 | 0.000 | 0.000 | 0.000 |
| PLASTER | energy | 0.032 | 0.032 | 0.000 | 0.000 |
| all classes | | 0.112 | 0.279 | -0.181 | -0.192 |

**Held share of committed C1-C4:**
* items: 57.2%;
* Reference cohorts: 86.3%;
* Moderate: 86.3%; Ambitious: 86.3%; TL: 86.4%.

**Committed after 2050, deterministic (kt CO2e):**

| run | lower, v4.7.2 -> v4.8.0 | change | upper (unchanged) | C1-C4 lower-upper |
|---|---|---|---|---|
| Reference | 9,727.8 -> 9,554.5 | -1.8% | 10,662.0 | 5,528.6-5,701.9 |
| Moderate Pathway | 7,373.6 -> 7,242.1 | -1.8% | 8,080.7 | 4,199-4,330 |
| Ambitious Pathway | 5,462.3 -> 5,364.7 | -1.8% | 5,985.1 | 3,118-3,216 |
| Theoretical Limit | 1,832.2 -> 1,798.8 | -1.8% | 2,002.2 | 1,076-1,109 |

**Committed after 2050, Monte Carlo p5-p50-p95 (kt CO2e):**
* REF lower: 8,160-9,726-11,519 -> 8,014-9,553-11,314.
* REF upper: unchanged, 8,944-10,660-12,624.
* New, per pathway:
  * Moderate: lower 6,017-7,243-8,675, upper 6,713-8,082-9,679;
  * Ambitious: lower 4,380-5,365-6,536, upper 4,886-5,985-7,291;
  * TL: lower 804-1,801-3,027, upper 892-2,005-3,373.

**Texts.** Every "C1-C4 held at 2025" text is updated, now qualified as in-window: Methods, ASSUMPTIONS, RESULTS
(new table "Committed after 2050 by run"), the Fig. 3 caption, `boundaries.factor_note` and the register.

New limitation: "The end of life of carbon-bearing materials (86% of committed C1-C4) is held at 2025; landfill-gas
capture or diversion of timber and plasterboard would lower it."

### 1b. Module D (carbon only)
* **New ED4 row**, one-sided: "Module D credit, booked at construction (not netted)". It is the D of the 2026-2050
  cohorts at 2025 factors (the largest credit).
* **Result:** 21,584 kt vs 25,503 kt, **-15.4%**. D / A1-A3 by class is in the table above.
* **Carbon only.** No LoE, no Fig. 7a row, no ED5 row. A consistent LoE would need Module D in the historical sector
  base as well.
* **Guard.** `tools/sensitivity_tables.CARBON_ONLY_ROWS` records this. Such a row needs no AR-base rule, and the code
  and the tests stop if it ever enters the LoE tornado.
* **Methods:** "Module D is excluded (EN 15978) and shown as a carbon-only sensitivity (Extended Data Fig. 4)."

### 2. ED / SF reallocation (`figure_plan.py`; `ed_number_map.csv`, `sf_number_map.csv`)
* **Extended Data:** ED1-ED5 unchanged; ED6 Sobol; ED7 lever alone; ED8 roll-out timing; ED9 stock & vacancy.
* **Extended Data Table 1** = LEVERS_TABLE.md, retitled from "Supplementary Table 5". The Table 1 note now reads
  "Values and sources in Extended Data Table 1".
* **Supplementary:** the SFs are renumbered so the MC input distributions sit next to MC convergence, and the reality
  checks next to the hindcast.

| v4.7.2 | v4.8.0 |
|---|---|
| ED6 MC input distributions | SF11 |
| ED7 Sobol | ED6 |
| ED8 lever alone | ED7 |
| ED9 roll-out timing | ED8 |
| ED10 reality checks | SF6 |
| SF2 stock & vacancy | ED9 |
| SF3 census replacement rates | SF2 |
| SF4 dwelling size | SF3 |
| SF5 overbuild absorption | SF4 |
| SF6 hindcast | SF5 |
| SF11 MC convergence | SF12 |
| SF12 pathway MC | SF13 |
| SF13 conditional TL | SF14 |
| SF14 TL dwellings | SF15 |
| SF1, SF7-SF10 | unchanged |

Cross-references updated in: the README, ARCHITECTURE, FIGURES.md, palette.toml / docs/PALETTE.md, the reports, the
tests and the figure modules.

### 3. Figures
* **Panel letters "a)":** `style.PANEL_SUFFIX = ')'`. The letter now sits a fixed 6 pt left of the axes
  (`draw.PANEL_LABEL_GAP_PT`) instead of 2% of the axes width, so it clears the title on narrow panels (ED9c).
* **Fig. 3:**
  * zone labels "Within both budgets" / "Within AR budget";
  * legend in the upper right of panel a;
  * Fig. 3b uses the new committed keys.
* **Fig. 4a:** "Acquired-rights budget" / "Ability-to-pay budget" placed above the lines.
* **Fig. 6:** labels L6 "Brownfield development" and L9 "Construction stage carbon"; tighter left margin.
* **Fig. 7a:** "Household size (Stats NZ B)"; tighter margin.
* **ED4:**
  * the Module D row;
  * `NOTES_TOP` 0.30 -> 0.33, because the 25 row notes did not fit below the axes and ED4_H is already at the
    247 mm page maximum.
* **ED9a:** compact legend (5 columns, short labels, key in the note).

### Notes
* **EDT1:** the per-typology lever values (`EDT1_levels_by_typology`) are filed as part of Extended Data Table 1.
* **CITATION:** 4.8.0.

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

### 1. Code-vs-text contradictions (the code is the truth; text fixed)
* **Re-occupation pool** (`tools/pathways_methods.py`, the `pathways.py` module docstring step 4, `reoccupation()`, the
  `REOCCUPATION_YEARS` comment, ARCHITECTURE).
  * The Reference, the Pathways and every non-TL run have no pool: the starting surplus and the 2026-27 overbuild
    are absorbed on the logistic by 2035, and a vacancy-rate fall is used in its year.
  * TL-family runs pool R = R1 + R2 + the positive overbuild + the starting surplus.
  * The window is first = observed_end + 1 = 2028 (not 2027).
  * TL numbers: R1 = 0; R2 = 117,834; overbuild pooled 33,984; starting surplus 18,966; R = 170,785.
    G+ (2028-2050) = 315,033 (G+ over 2027-2050 would be 353,692); s = 0.542.
  * R1 = 0 because, at the TL1 rate limit, households never fall in absolute terms. In the instant TL (no rate
    limit) R1 = 78,964: households fall from 2.026 M to 1.947 M in 2027.
* **Household size after 2048** (assumption table): the Stats NZ shape through 2048, then the 2043-2048 secant slope
  continued linearly to 2050. The zero-slope and PCHIP tails are ED4 rows [4] and [5].
* **Very High replacement:** two negative interval rates, 1996-2001 (-0.105%/yr) and 2001-2006 (-0.039%/yr), not one
  (D07).
* **L6 basis:** "the Reference of this run: replacement (soil-free) floor area / total floor area built, ratio of
  sums 2026-2050" (0.088). The test docstring is fixed too.

### 2. Documentation sweep
* **Stale terms:** fixed where they described the current model; the hits left are justified in the PR.
  * README: L9 and TL1 are exceptions to the common logistic.
  * The ARCHITECTURE pool text.
  * Methods figure paths now point to `outputs/FIGURES.md`.
  * "authors contacted" removed (Hjalsted α).
* **Acknowledged limitations:** one generated list (`baseline_draft.acknowledged_limitations`, in METHODS_DRAFT and
  ASSUMPTIONS) holding exactly the eleven acknowledged limitations, the TL one new and data-driven. The other items
  stay as "method notes" without duplicates.
* **Manuscript numbering** (`figure_plan.MANUSCRIPT_IDS`), in the `outputs/FIGURES.md` header and the README:
  * EDT1 -> Supplementary Table 5;
  * ST1 -> Supplementary Table 4;
  * LEVERS_TABLE_MAIN -> Table 1.

### 3. Main-paper Table 1
* `outputs/reports/LEVERS_TABLE_MAIN.md` / `.csv`, from the `TABLE1_MAIN` dict in `tools/pathways_methods.py`.
  Eleven structural facts are checked against `levers.json`; the writer stops on a mismatch.
* `LEVERS_TABLE.md` is retitled Supplementary Table 5.

### 4. References, availability, case-study data
* **`docs/REFERENCES.md`:** rewritten with the checked entries.
  * Benini et al. 2015 deleted; Laurent et al. 2013 Table 4 (pp. 10-11) is now the cited source of I_glob.
  * PAS 2080 cited in full, with the methods sentence on L3 under Avoid.
  * Kockat et al. 2019 replaces EUCalc 2020; US EPA 2012 (was 2014); Stats NZ projections 2025.
  * Christoforatos & Pickering 2026 everywhere (MANIFEST and CITATION included).
  * `grep "[verify"` over docs/, outputs/reports/, *.py and tools/: empty.
* **Wording fixes:**
  * The L9 sources no longer claim more than they state: s 5Q is an economy-wide target, used for the end year only;
    Oslo requires emission-free site machinery, not zero A4-A5.
  * Resch et al. 2021 title corrected in `levers.SOURCES`.
  * Napiontek et al. 2025 dropped from `levers.SOURCES`: it supported no value and is not in REFERENCES.
* **Availability:** `outputs/reports/AVAILABILITY.md` (`tools/availability.py`) and the README carry the data and code
  availability statements (Zenodo DOI placeholder) and a third-party data table.
* **Licence:** `LICENSE` (MIT) added, and `license: MIT` set in CITATION.cff, to match the stated code licence.
* **Case-study data:** `data/raw/Analytical_LCA_Results_Database.xlsx` (the author's LCAQuick root tables) is removed
  from the tree (git rm + .gitignore; no history rewrite).
  * `data/build_lca_events.py` stops with a clear message without it.
  * The MANIFEST rows are reworded.
  * No test needed it (skip count unchanged at 0).

### Follow-up (same PR)
* **Table 1, L3:**
  * Ambitious: "40% fewer demolitions and rebuilds (national scenario)".
  * TL: "No demolition and no rebuild wave".
  * Both now cover the recent-surge component that L3 also removes.
* **The four-level rule:** Ambitious is "a documented frontier: a value achieved in New Zealand or elsewhere, an
  official projection, a peer-reviewed scenario or a documented requirement, and is cited". The same wording is in
  the Table 1 note, the Methods / Supplementary Table 5 header and the `levers.LEVEL_RULE` comment; the L1 rule now
  reads "official projection".
* **s 5Q (checked by the author):** the 2025 Amendment Act changes only s 5Q(1)(b)(ii) and (3) and adds s 5QA; the
  net-zero target of s 5Q(1)(a) is unchanged.
  * Cited as "Climate Change Response Act 2002, s 5Q (as amended 2025)".
  * The 2025 Act is added to `docs/REFERENCES.md`.
  * `levers.json` gets the new L9 anchor and sources strings (text only; lock entry updated).

### 5. Figures (redraw only)
* **Fig2:** legend +0.5 pt and every other text +0.5 pt, except the panel d column labels (they collide at +0.5 pt).
* **Fig3b:** no Monte Carlo median mark or legend entry (median in the note).
* **Fig5:** AtP out of the legend (kept on the strip); 3 x 3 grid with AR below the Theoretical Limit; centred on the
  square plot.
* **Fig6, Fig7a:** legends +0.5 pt.
* **Fig7b:** the 50% line's legend entry merged into its two-line label.
* **ED / SF:** legends and annotations at least 6 pt (`style.raise_small_text`).
  * The ED4 / ED5 row notes keep their measured layout.
  * Layout fixes: ED3b headroom, SF1a label wrapped, SF10 x room, SF14a legend placed upper right.
  * Font audit (smallest text per figure) in the PR; nothing below 5 pt.

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

### v4.6.0 -> v4.7.0

| quantity | v4.6.0 | v4.7.0 |
|---|---|---|
| Reference: carbon 2026-2050 (kt CO2e) / LoE AR / LoE AtP | 25,502.8 / 5.761 / 22.91 | 25,502.8 / 5.761 / 22.91 (unchanged) |
| Moderate Pathway | 17,971.4 / 4.060 / 16.15 | 17,236.1 / 3.894 / 15.49 |
| Ambitious Pathway | 12,542.0 / 2.833 / 11.27 | 11,459.2 / 2.589 / 10.30 |
| Theoretical Limit | 4,079.1 / 0.921 / 3.67 | 4,079.1 / 0.921 / 3.67 (unchanged) |
| TL, TL1 age-standardised (new sensitivity) | - | 5,946.4 / 1.343 / 5.34 |
| P(LoE AR <= 1), pathway Monte Carlo (5,000 draws): Reference / Moderate / Ambitious / TL / TL from 2027 | 0.0% / 0.0% / 0.0% / 64.0% / 98.9% | 0.0% / 0.0% / 0.0% / 64.0% / 98.9% |
| P(LoE AR <= 1), TL1 age-standardised | - | 0.06% (3 of 5,000) |
| TL threshold population 2050 (P = 50%) | 6.715 M (95% CI 6.713-6.718) | 6.715 M (95% CI 6.713-6.718) |
| Shapley top 3, Ambitious (kt) | L5 2,531; L1 2,193; L8 1,749 | L1 3,611; L5 2,434; L8 1,682 |
| Shapley top 3, TL (kt) | L1 6,639; L4 3,346; L2 2,883 | unchanged |
| L1 alone, Moderate / Ambitious (kt) | 24,010.9 / 22,563.4 | 23,058.5 / 20,731.1 |
| L9 alone, Moderate / Ambitious / TL (kt) | 24,701.3 / 23,899.8 / 22,668.6 | 24,689.4 / 23,876.0 / 22,668.6 |
| Committed after 2050 (lower bound), central and Monte Carlo 90% interval (kt) | 9,728 (8,160-11,519) | 9,728 (8,160-11,519) (unchanged) |

The Reference, the Theoretical Limit, the Reference Monte Carlo and Sobol indices are unchanged to the last digit; the
Moderate and Ambitious Pathways change through L1 and L9 only.

### Stage 1: cleanup (outputs identical)

Proof: the deterministic steps re-run after the cleanup; every file of `outputs/data` byte-identical except the nine
removed replacement-variant Monte Carlo files and four files that differ only by the dropped variant entries
(`aesa/montecarlo_annual.csv`, `aesa/results.json`, `metrics.json`, `figure_source/D23_annual_loe.json`; every REF
entry identical). The regression lock (`tests/regression_model_v4.json`) unchanged and passing. Tests 265 -> 252
collected, all passed, 0 skipped. Code and docs outside `outputs/`: 59 files, +658 / -2,789 lines.

* Removed code paths: the 'dhe' household bridge and the 'projection' start mode (households after 2023 = population /
  household size always); the two-point completion lag (Little's law; `lag_census` = lag in years); `PATHWAY_FROZEN`
  (its settings are now plain settings); every QUICK_RUN / `--quick` reference; the 2018-base household path (loaders,
  settings, branches); the L1 `on` and TL surplus-pooling switches (always on). `projection.py` 2,431 -> 2,274 lines.
  The four month-name helpers merged into `naming.month_year`.
* Removed data (sizes in bytes): `data/Householddata.xlsx` (123,198), `data/subnational-population-projections-2018base-
  2048.xlsx` (150,914), `data/consentdata.xlsx` (54,725), `data/raw/building-consents-issued-july-2026.xlsx` (184,881),
  with their MANIFEST rows and the NZ_pop.xlsx row (the July 2026 zip row kept for provenance).
* Removed tests and fixtures: the two duplicated tests; the MODEL v2 / v3.3 reproduction tests with
  `tests/regression_pb_v2.json` (2,186 B) and `tests/v3_3_runs_fixture.json` (14,509 B); the ten tests classified (c)
  (including `test_households_per_consent.py`, `test_validation.py`). One extra: `test_model_v4_2
  bridge_reaches_2026_2050` compared the 'erp_S' and 'dhe' bridges and cannot exist without the second.
* Replacement Monte Carlo (Low / High / Very High variants) dropped: variants, nine output files (~3.1 MB), run steps,
  the Methods table and tests. Replacement uncertainty is reported by ED3 (the four variants through every run) and the
  one-at-a-time rows (Replacement Low-Very High; half-life 5-15 yr).
* Docs: `docs/METHODS_DRAFT.md` and `docs/LEVERS_TABLE.md` deleted (generated copies are in `outputs/reports/`; links
  fixed); ARCHITECTURE rewritten (918 -> 498 lines); `docs/palette_preview.png` 2,617,166 -> 325,556 B; README in its
  final form (question, headline results generated from `outputs/data/metrics.json`, how to run: full / light /
  figures-only / redraw, tests, provenance, data freeze, citation); `tests/README.md` updated.

### Stage 2: pathway method consistency

* One rule for the levels (Methods Table 1 header, `outputs/reports/LEVERS_TABLE.md` "Rule" column, `levers.LEVEL_RULE`):
  Reference = current practice held; Moderate = the midpoint; Ambitious = the documented frontier; TL = the logical
  bound (zero vacancy, zero space beyond the occupied area, no demolition, 100% brownfield, zero A4-A5), otherwise the
  best observed (TL1 household size; the lowest-carbon NZ case study). TL A4-A5 = 0 is labelled a theoretical bound
  (construction waste cannot reach zero; LCAQuick does not split A4-A5). Exceptions stated: TL1 reaches its level in
  2037.5 (rate limit); L9 phased once (below).
* L1 Ambitious = the Stats NZ Medium B household projection (living-arrangement propensities change; DataInfo+
  POPPR_FHH, propensity B), rebased on the observed 2023 household size with the same 2048 secant tail; in the pathway
  Monte Carlo the draw's own Low / Medium / High B path. Replaces the High - Medium gap. Moderate = the midpoint. 2050:
  Reference 2.4635, Moderate 2.5275, Ambitious 2.5916 (v4.6.0 Ambitious 2.5420). B >= A in every year (checked; STOP
  otherwise). The ED4 row "Living arrangements: propensities change" asks "what if B happens anyway"; L1 Ambitious asks
  "what if policy delivers it" (same path, both stated).
* TL1 unchanged (2.79, 1991; the same rate limit). Methods and the SF13 note: held regardless of age structure; with the
  2050 population this requires about 11.7% fewer households per person than in 2023 at every age.
* New sensitivity "TL1 age-standardised" (`household_headship.py`, `tests/test_household_headship.py`): headship rates by
  age group (0-14, 15-39, 40-64, 65+) from POPPR_FHH_008 / POPPR_FHH_010, calibrated on 2023; TL1 at the lower of the 2023
  and Medium B rates by age group, scaling the Reference household size. Above L1 Ambitious in 2026-2039 and floored at
  it (TL never weaker than Ambitious) in 2040-2050. Row TL-TL1-age-standardised in runs, theoretical_limit.json, metrics
  and README; the SF13 note; the Methods; P(LoE AR <= 1) from the pathway Monte Carlo.
* L9 Ambitious phased once: anchored on the Reference 2026 factor, linear to zero in 2050 (v4.6.0 applied the roll-out
  twice). Effective A4-A5 factor, Reference / Ambitious v4.6.0 / v4.7.0: 2027 0.980 / 0.978 / 0.949; 2030 0.951 / 0.890 /
  0.825; 2035 0.905 / 0.600 / 0.619; 2040 0.861 / 0.400 / 0.413; 2050 0.779 / 0 / 0. TL unchanged.
* Re-checked: Reference = lever off in every TL and Shapley run; midpoints; phase exceptions (`ordering_checks.json`).

### Stage 3: run, lock, tests

* Full run, then light run; lock re-captured (18 of 34 deterministic files changed, all under `pathways/` plus
  `baseline/projection.json` settings keys, `baseline/gap_2026.json`, D09; the Reference baseline annual / bands,
  sensitivity Reference and tornado, AESA annual files unchanged). Tests: 258 passed, 0 skipped (the two AESA-workbook
  skips of earlier releases were removed with their tests in Stage 1).
* Every main, Extended Data and Supplementary figure inspected.

### Deviations and audit items not implemented

* The audit's "the 2023-rate path reproduces Stats NZ Medium A within 0.02" does not hold: max |difference| 0.0225
  (Medium, 2033), 0.024 (Low), 0.021 (High), from the four broad age groups (sex-specific rates give the same). The test
  uses 0.025 (documented); the model uses the ratio to the 2023-rate path, so this aggregation bias cancels.
* README provenance rows for histpopdata, popdata, oldhouseholddata and occ-unocc: MANIFEST holds no rows for them; the
  README states what the files themselves record ("not recorded in MANIFEST").
* Not implemented (not in the v4.7.0 brief): the 20-year AR-base Monte Carlo table; renaming `regression_model_v3` ->
  `v4`; moving two figure tests out of `test_events.py`; renaming `test_fig6_*`.

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
