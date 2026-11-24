# model-v5.0.0 report: L1 at TL from age-specific headship

Branch `release/model-v5.0.0` from main a8add58. One full run (PATHWAY_PROFILE=full, 5,000 draws, Sobol). No tag or
release. All numbers below are read from the committed outputs (`outputs/data/`); "v4.10.2" values come from the
saved v4.10.2 full outputs.

**Headline.** Under the age-specific rule the Theoretical Limit no longer stays within the acquired-rights budget:
TL LoE AR 0.944 → 1.347, P(LoE AR ≤ 1) 60.92% → 0.04% (2 of 5,000 draws). The Reference, Moderate and Ambitious
Pathways, S1–S3 and every non-TL Monte Carlo, Sobol, one-at-a-time and AESA output are unchanged.

## 1. Headship

### Data and mapping
* Stats NZ Census living arrangements: CEN23_FHH_036 (role in family nucleus × age, 2013/2018/2023), CEN23_FHH_018,
  CEN23_FHH_041 (household composition; stated family and other multi-person households), CEN13_FHH_026 / 030 / 031
  (2013 cross-checks; the 2013 targets agree with CEN13_FHH_026 within 0.5%); ERP by age DPE058AA (back-check).
  Unmodified copies in `data/raw/census_living_arrangements/` and `data/raw/DPE058AA.csv`, MANIFEST rows with SHA-256;
  derived tables from `data/build_census_headship.py`.
* Roles → headship: person alone = 1; couple without children and couple-parent = f/2 each; sole parent = f; other
  person not in a family nucleus (incl. persons in households of under-15s only) = g; child in a family nucleus = 0
  (children stay a separate category, as in POPPR_FHH_008). Unknown roles and unidentifiable households are
  allocated proportionally (stated basis).
* Census coding changes (methods note in `METHODS_DRAFT.md`, limitations): census family coding changed in 2018 (new
  methodology) and 2023 (administrative data added people to families). Unknown roles are 3.1% of people in 2013,
  0.6% in 2018 and 1.2% in 2023; unidentifiable households 2.6% / 3.9% / 4.1%. Each census is calibrated to its own
  stated households (f_c, g_c per census), and the TL takes each age group's lowest rate, which may come from
  different census years.

### Calibration and gates (all pass)

| census | f | g | one-person people / households | unknown roles (people) | unidentifiable (households) |
|---|---|---|---|---|---|
| 2013 | 0.9517 | 0.2208 | 1.0000 | 3.1% | 2.6% |
| 2018 | 0.9506 | 0.2118 | 1.0000 | 0.6% | 3.9% |
| 2023 | 0.9450 | 0.2126 | 1.0000 | 1.2% | 4.1% |

Plausibility: 0 < f ≤ 1, 0 < g < 1, f within ±5% of f_2013 (2023: −0.7%). Common basis (each source's rates
divided by its own all-ages rate, 2023 census vs POPPR): 15–39 −0.13%, 40–64 −1.13%, 65+ +1.51% (gate 2%).
People per household: census 2.684 (stated basis), POPPR 2.741. Share differences against POPPR are within 1.6
points below 65; at 65+ couples +2.77 and other −4.28 points.

### Headship rates h_a (households per person)

| age group | census 2013 | census 2018 | census 2023 | B-adjusted 2030 | B-adjusted 2040 | B-adjusted 2050 |
|---|---|---|---|---|---|---|
| 15–39 | 0.3408 | 0.3232 | 0.3219 | 0.3053 | 0.2955 | 0.2953 |
| 40–64 | 0.5471 | 0.5375 | 0.5313 | 0.5262 | 0.5204 | 0.5172 |
| 65+ | 0.6275 | 0.6080 | 0.6023 | 0.5972 | 0.5904 | 0.5862 |

(0–14: census 2013 / 2018 / 2023 = 0.00003 / 0.0026 / 0.0001; TL rate 0.00003 from 2013.)
Adult headship fell in every age group from 2013 to 2023, so 2023 is the census minimum of every adult group; the
one-person share fell at every age 15+. **TL source:** B-adjusted propensity sets the TL rate of every adult group in
every year 2028–2050 (h^B,adj = h^census_2023 × h^B(y) / h^proj_2023); the census minimum sets it in 2023.
Per-year detail: `outputs/data/pathways/headship_by_census.csv`, SF16.

### Back-check (ratio form, ERP age shares, census-minimum TL rates)

| census | implied S_c/S_2023 | observed S_c/S_2023 | implied hpp rel. 2023 | observed hpp rel. 2023 |
|---|---|---|---|---|
| 1991 | 1.1168 | 1.0389 | 0.8954 | 0.9625 |
| 1996 | 1.1038 | 1.0385 | 0.9059 | 0.9629 |
| 2001 | 1.0772 | 1.0166 | 0.9284 | 0.9836 |
| 2006 | 1.0489 | 1.0035 | 0.9534 | 0.9965 |

Implied ≥ observed at every census, so "best observed since 1991" holds and no "matched to census year X" row is
needed.

### Household size S (Reference age structure, POPPR Medium A)

| year | Reference S_ref | TL ratio | S_ref × ratio | **S^TL (adopted)** | v4.10 path | L1 Ambitious |
|---|---|---|---|---|---|---|
| 2030 | 2.6125 | 1.0214 | 2.6685 | **2.6685** | 2.7026 | 2.6593 |
| 2035 | 2.5595 | 1.0330 | 2.6440 | **2.6440** | 2.7614 | 2.6329 |
| 2040 | 2.5166 | 1.0374 | 2.6107 | **2.6113** | 2.7905 | 2.6113 |
| 2050 | 2.4635 | 1.0420 | 2.5669 | **2.5916** | 2.7905 | 2.5916 |

* Speed limit (1.18% a year, 1996–2001 interval) binds in 2026–2027 (`tl_speed.binds_until` = 2027); the v4.10
  path would have reached its level in 2037.5.
* **The Ambitious floor binds in 2040–2050:** the age-specific TL level (S_ref × ratio) is lower than L1 Ambitious
  from 2040, so L1 at TL = L1 Ambitious in those years. S in 2050: Reference 2.4635, L1 Ambitious 2.5916, L1 at TL
  2.5916 (v4.10: 2.7905).
* L1 Ambitious is defined as a share of the gap to the v4.10 level (national 1991 household size, 2.7905), which is
  now above the TL level. The identity gate requires Ambitious unchanged, so this was not altered. **Author
  decision needed:** whether L1 Moderate/Ambitious should keep the v4.10 gap reference (kept here) or be re-anchored
  to the new TL. Re-anchoring would change the Pathways.
* L1 at TL alone vs L1 Ambitious alone: 20,653.1 vs 20,731.1 kt (L1 at TL 78.0 kt lower). Annual carbon of L1 at TL
  is up to 124 kt above L1 Ambitious in 2031–2040 (`ordering_checks.json`, an annual reversal; the cumulative
  ordering holds): the TL path rises above Ambitious early and converges down to it by 2040, so its year-on-year
  household increments are larger in those years.

## 2. TL results, v4.10.2 → v5.0.0

| quantity | v4.10.2 | v5.0.0 | source |
|---|---|---|---|
| TL carbon 2026–2050 (kt) | 4,177.0 | 5,962.7 | pathways/runs.csv |
| TL LoE AR / AtP, 2026–2050 | 0.944 / 3.753 | 1.347 / 5.358 | pathways/runs.csv |
| TL LoE AR / AtP, 2028–2050 | 0.420 / 1.671 | 0.858 / 3.411 | loe_2028_2050.csv; metrics.json |
| P(TL LoE AR ≤ 1), Wilson 95% | 60.92% (59.56–62.26%) | 0.04% (0.01–0.15%; 2 of 5,000) | pathways/montecarlo_summary.csv, montecarlo_draws.csv |
| TL LoE AR, MC p5 / p50 / p95 | 0.616 / 0.945 / 1.287 | 1.196 / 1.350 / 1.537 | pathways/montecarlo_summary.csv |
| P(LoE AR ≤ 1), TL from 2027 | 98.58% | 79.78% | pathways/montecarlo_summary.csv |
| Population threshold (P = 50%) | 6.693 M | not estimable (2 of 5,000 draws within AR, fewer than 10) | pathways/montecarlo_conditional_tl.json |
| Committed after 2050, TL (kt) | 1,750.6–2,240.8 | 2,752.3–3,532.1 | pathways/runs.csv |
| Re-occupation pool: R1 / R2 / R_overbuild / R | 0 / 90,337 / 52,944 / 143,281 | 0 / 91,552 / 52,944 / 144,496 | pathways/theoretical_limit.json |
| Re-occupation share of need | 0.4496 | 0.2876 | pathways/theoretical_limit.json |
| Single-lever sum vs combined, TL (kt) | 44,635.5 vs 21,325.8 (overlap 52.22%) | 38,143.1 vs 19,540.1 (48.77%) | metrics.json |
| Avoid / Switch / Improve, levers at TL (Shapley) | 71.3% / 17.0% / 11.7% | 63.7% / 21.6% / 14.7% | pathways/shapley.csv |
| Fig. 5 TL position: demand / intensity reduction | 81.8% / 33.0% | 69.0% / 36.9% | pathways/backcast.json |
| Years TL ≤ AR budget (annual) | 2030–2050 | 2033–2050 | pathways/annual.csv |
| Years TL ≤ AtP budget (annual) | 2035–2037, 2050 | none | pathways/annual.csv |

Shapley shares at TL (carbon, `pathways/shapley.csv`):

| lever | levers at TL v4.10.2 | v5.0.0 | TL from the Moderate Pathway v4.10.2 | v5.0.0 |
|---|---|---|---|---|
| L1 | 30.23% | 14.52% | 32.61% | 11.77% |
| L2 | 9.66% | 10.12% | 10.11% | 10.25% |
| L3 | 6.68% | 7.35% | 7.53% | 8.76% |
| L4 | 15.71% | 20.35% | 15.46% | 22.10% |
| L5 | 8.96% | 11.35% | 6.86% | 9.50% |
| L6 | 4.68% | 5.93% | 3.61% | 4.92% |
| L7 | 2.92% | 3.63% | 2.47% | 3.34% |
| L8 | 9.44% | 12.04% | 8.71% | 12.12% |
| L9 | 3.86% | 4.96% | 3.76% | 5.27% |
| L10 | 7.85% | 9.75% | 8.90% | 11.97% |

Shapley efficiency holds in every game and metric (sum of values = v(∅) − v(N), largest difference 3.6e-12 kt).
Bands sum to the run totals (maximum relative difference 5.2e-16).

### Re-occupation pool predicate (user decision, option 1)
The pool applies only in runs that release dwellings (cumulative releases R > 0 by 2050). L1 at TL releases none
under the age-specific rule. Changed (light, deterministic): 512 Shapley configurations (256 per TL game: L1 at TL
without L2 at TL), by −129 to −497 kt (median −350 kt); L1 at TL alone 20,787.0 → 20,653.1 kt; TL-from-Moderate
{L1 at TL} 15,567.6 → 15,269.0 kt; TL unchanged at 5,962.7 kt (L2 at TL releases). Shapley at TL from the
predicate alone: L1 13.89 → 14.52%, L2 10.89 → 10.12% (levers at TL); L1 10.07 → 11.77%, L2 12.14 → 10.25% (TL from
the Moderate Pathway); other levers ≤ 0.12 points.

### Population threshold (user decision: minimum-events rule)
With 2 draws within AR the logistic MLE does not exist (separation); a Firth estimate (5.60 M, inside the sampled
range 5.47–7.70 M) would rest on 2 events and 276 of 2,000 bootstrap resamples would contain neither. Rule adopted:
not estimable when fewer than 10 draws fall in the rarer outcome class (10 events per variable; Peduzzi et al.
1996). No curve and no vertical line in Fig. 7b / SF13; the LoE distribution against the 2050 population is shown.
`pathways/montecarlo_conditional_tl.json` records `within_AR` = 2 and `min_events` = 10.

## 3. Old TL as a sensitivity
Row "L1 at TL: national 1991 household size regardless of age (v4.10)" (run `TL-L1-national-1991`, MC
`TL_L1_national_1991`) reproduces the v4.10.2 TL exactly: 4,177.0 kt, LoE AR 0.944, AtP 3.753, P(LoE AR ≤ 1) =
60.92%. The age-standardised row is removed. (Its v4.10.2 values, 5,963 kt and P 0.04%, are close to the new TL:
both rules let age structure, not the national 1991 level, set the limit.)

## 4. Identity gate (v4.10.2 full outputs → v5.0.0 full outputs)
* 110 files in common: 77 byte-identical, 33 differ; 2 new (`loe_2028_2050.csv`, `pathways/headship_by_census.csv`).
* Every differing row traced to the TL family: runs L1-tl, TL, TL-from2027, TL-reoccupation-fast, TL LOW/HIGH/VHIGH,
  the v4.10 / age-standardised sensitivity runs; Shapley games `levers_tl` and `tl_from_moderate_pathway`; waterfall
  steps TL1–TL10; `lever_annual` L1 tl; `lambda_sweep` L1 tl; TL rows of `sensitivity/household_size.csv`,
  `pathway_carbon.csv`, `replacement_variants.csv`; TL Monte Carlo (draws, summary, annual, importance, fits,
  conditional, draw rules); TL markers and TL1 entries of `backcast.json`, `ordering_checks.json`, `levers.json`,
  `theoretical_limit.json`, `metrics.json`.
* New rows or keys only: `sensitivity/planetary_boundary.csv` (two ED7 rows), `aesa/results.json`
  (`one_at_a_time_ar_base/window_2028_2050`), the number-map files.
* One non-TL column moves: `central_draw_max_rel_diff` in `pathways/montecarlo_summary.csv` (a maximum over all
  runs, TL included): 2.2877e-14 → 2.2832e-14.
* Reference, Moderate, Ambitious, S1–S3 and their Monte Carlo, Sobol (ED9), one-at-a-time and AESA outputs:
  identical. Reference 25,502.8 kt (5.761 / 22.914); Moderate 17,209.3 (3.888 / 15.463); Ambitious 11,470.5 (2.591 /
  10.306).

## 5. Checks
* Lever audit (`outputs/reports/lever_audit.md`): all 9 checks pass (check 7 now on actual releases).
* `check_outputs`: pass. Figures: all drawn.
* Tests: 269 passed in the light and the full profile after re-capturing `tests/regression_lock.json`.
* Clean clone: see the PR description (fresh clone, Python 3.11 venv, `pip install -r requirements.txt`, pytest,
  light run, `git status`).
* CLAUDE.md and `.claude/`: absent from main and the branch. No Co-Authored-By / Claude-Session / "Generated with"
  lines in `git log origin/main -20` or in the PR's commits; all commits authored and committed as Gerras.
* Note: the release-metadata commit (54b3384) had removed 163 output files, because it was made while the
  interrupted full run had cleared `outputs/`. The full-run commit restores them; the tracked outputs now equal
  main's set apart from the planned renumbering (checked file by file).

## 6. ED7 new rows (Reference)

| row | LoE AR | LoE AtP | change AR / AtP vs central | source |
|---|---|---|---|---|
| 2028–2050 only (pipeline years excluded) | 5.631 | 22.395 | −2.26% / −2.26% | loe_2028_2050.csv |
| Whole-life accounting (committed emissions at construction) | 5.859 | 32.542 | +1.69% / +42.01% | aesa/sensitivity.csv (xii_whole_life) |

`outputs/data/loe_2028_2050.csv` (2028–2050, LoE AR / AtP): Reference 5.631 / 22.395; Moderate 3.602 / 14.326;
Ambitious 2.199 / 8.746; TL 0.858 / 3.411.

## 7. Number maps

Extended Data (`outputs/data/ed_number_map.csv`):

| new | old |
|---|---|
| ED1 | ED1 |
| ED2 | ED2 |
| ED3 dwelling size | SF4 + new OLF panel c |
| ED4 stock vacancy | ED3 panels a, b |
| ED5 replacement variants | SF3a (panel a) + ED7 |
| ED6 roll-out timing | ED4 |
| ED7 boundary sensitivity | ED5 + 2 rows |
| ED8 one-at-a-time | ED6 |
| ED9 Sobol | ED9 |
| EDT1 | EDT1 (+ L3, L10 footnotes) |

Supplementary (`outputs/data/sf_number_map.csv`): SF1, SF2 same; SF3 vacancy definition ← old ED3c; SF4 ← SF5;
SF5 ← SF6; SF6 ← SF7; SF7 ← SF8; SF8 lever annual ← old ED8; SF9–SF15 same; SF16 headship by census (new).
Supplementary tables ST1–ST12 keep their numbers (`st_number_map.csv`). **Assumption to check:** SF16 is placed
last; its position in the SI citation order is not known here.

## 8. Manuscript numbers that change (old → new, source file)

| place | old | new | source |
|---|---|---|---|
| Abstract: TL LoE AR / P / AtP | 0.94 / 61% / 3.7 | 1.35 / 0.04% / 5.4 | pathways/runs.csv; montecarlo_summary.csv |
| Results TL paragraph: TL carbon, LoE AR / AtP | 4,177 kt; 0.94 / 3.75 | 5,963 kt; 1.35 / 5.36 | pathways/runs.csv |
| Results: P(TL within AR), Wilson | 60.9% (59.6–62.3%) | 0.04% (0.01–0.15%) | montecarlo_summary.csv |
| Results: "Avoid alone 92%, 5.8 → 1.32" | 92.3% of the TL reduction; LoE AR 5.76 → 1.315 | 84.2%; 5.76 → 2.04 | pathways/shapley_subsets.csv (levers_tl, L1+…+L5) |
| Shapley TL shares | see table in §2 | see table in §2 | pathways/shapley.csv |
| Avoid / Switch / Improve at TL | 71.3 / 17.0 / 11.7% | 63.7 / 21.6 / 14.7% | pathways/shapley.csv |
| Fig. 5 TL reductions (demand / intensity) | 82% / 33% | 69% / 37% | pathways/backcast.json |
| Fig. 7b threshold | 6.69 M | not estimable (2 of 5,000 draws within AR) | montecarlo_conditional_tl.json |
| Discussion "11.7%": if it is the TL fall in households per person (2050 population vs 2023 rates) | 11.7% (national 1991 household size) | 4.0% (age-specific headship) | pathways/levers.json (tl_households_per_person_fall); METHODS_DRAFT.md limitations |
| Discussion "11.7%": if it is the Improve share of the TL reduction | 11.7% | 14.7% | pathways/shapley.csv |
| 2028–2050 TL LoE AR / AtP | 0.42 / 1.7 | 0.86 / 3.4 | loe_2028_2050.csv |
| Committed after 2050, TL | 1,751–2,241 kt | 2,752–3,532 kt | pathways/runs.csv |
| Single-lever sum vs combined, TL | 44,636 vs 21,326 kt (52.2%) | 38,143 vs 19,540 kt (48.8%) | metrics.json |
| L1 at TL alone | 14,161 kt | 20,653 kt | pathways/runs.csv |
| Methods TL paragraph: L1 at TL rule and S^TL | national 1991 household size 2.7905, speed limit | age-specific headship, ratio method, speed limit 2026–2027, Ambitious floor 2040–2050, S^TL 2050 = 2.5916 | METHODS_DRAFT.md; pathways/levers.json |
| SI Notes 10–12 TL numbers | as the rows above | as the rows above | METHODS_DRAFT.md (regenerated) |

Both old values of the Discussion sentence were 11.7%; which one the sentence uses is not visible from the
repository, so both are listed.

Note on "1.32": the v4.10.2 outputs give LoE AR 1.3148 for the Avoid-only subset at TL, which rounds to 1.31, not
1.32. Please check the manuscript's source for that number.

## 9. Open items for the author
1. **L1 Ambitious anchoring** (§1): Ambitious refers to the v4.10 level, which is now above the TL; the floor binds
   in 2040–2050.
2. **Headline change:** the TL is no longer within AR in nearly any draw; the abstract and Discussion framing that
   rests on "61%" needs rewriting, not only renumbering.
3. **ED legends** were written by Claude from the figure contents; please review them.
4. **OECD licence wording:** the OECD terms page could not be fetched from this environment (www.oecd.org not
   allowed); the wording "the OECD terms and conditions" is kept and is unverified.
5. **Horup et al. GMST labels:** Table S1 gives about 1.6–1.8 °C (RCP2.6) and 1.0–1.4 °C (RCP1.9); the EDT1 L10
   footnote uses the supplied "≈ 2 °C / ≈ 1.5 °C" text verbatim.
6. **SF16 position** in the SI order (§7).
7. This report is hand-written at the requested path; `run_all.py` rebuilds `outputs/reports/` from scratch, so a
   later full run deletes it (restore with `git checkout -- outputs/reports/v5_0_0_report.md`).
8. Repository housekeeping from earlier work: the old tags still need the command block (run from a Codespace); the
   branch `tmp/attribution-test` still exists on GitHub.
