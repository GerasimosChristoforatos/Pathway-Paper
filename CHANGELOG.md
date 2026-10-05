# CHANGELOG

## baseline-pb-v1.2 (in progress; default mode unchanged, tag not yet proposed)

**New, not adopted**: item-level material decarbonisation (`DECARB_MODE =
'horup_item'`). The adopted mode is still the v1.1 class-level mapping, renamed
`'horup_class_v1_1'`; all its model outputs are identical to baseline-PB_v1.1
(every versioned result CSV in outputs/ and outputs/frozen/ byte-identical; the
JSON files differ only in the mode name; the factor tables in outputs/factors/
carry the renamed class variants with unchanged values plus the item variants).

| 2026-2050, reference S3-10 | `'none'` | `'horup_class_v1_1'` (adopted) | `'horup_item'` |
|---|---|---|---|
| Embodied carbon (kt CO₂e) | 33,625 | 31,400 | 31,013 |
| Upfront, A1-A5 + soil (kt) | 24,204 | 21,979 | 21,592 |
| MC carbon p5 / p50 / p95 (kt) | 25,743 / 33,268 / 41,644 | 24,119 / 31,095 / 38,863 | 23,833 / 30,715 / 38,391 |
| Cumulative LoE_AR (MC p5-p95) | 5.41 (4.33-6.42) | 5.05 (4.05-5.99) | 4.99 (4.00-5.92) |
| Cumulative LoE_AtP (MC p5-p95) | 30.2 (24.0-36.1) | 28.2 (22.4-33.6) | 27.9 (22.1-33.2) |
| A1-A3 by 2050 (Detached / Townhouses / Apartments) | 0 | −20.9 / −21.2 / −25.2% | −25.0 / −24.8 / −28.9% |
| Whole factor incl. soil by 2050 | 0 | −9.7 / −11.2 / −18.2% | −11.7 / −13.0 / −20.9% |

Values from `outputs/DECARB_MODES.md` (full run). The `'none'` MC LoE bands use
the per-draw AR base of v1.1; with the base fixed they equal baseline-pb-v1.

* **Item table**: `data/raw/epd-level_materials.xlsx` (supplied; MANIFEST) ->
  `data/build_material_items.py` -> `data/derived/material_items.csv`: names
  stripped of leading/trailing whitespace (5 item names, 34 rows), rows of the
  same building x class x item summed; reproduces `building_data.xlsx` for every
  building x class x stage (max relative difference 4.4e-16).
* **Mapping**: `data/material_item_map.csv`, 160 items, each to one S4 row or
  held: 115 direct, 16 by Horup et al. p. 6 (other cementitious and wood-based
  products), 28 proxy (plastics and paint -> EPS; SIP -> EPS; plasterboard ->
  clay brick), 1 held (lift). Share of 2025 A1-A3 direct / p. 6 / proxy / held:
  Detached 74.9 / 6.2 / 18.9 / 0.0%, Townhouses 82.2 / 4.9 / 13.0 / 0.0%,
  Apartments 90.0 / 0.9 / 5.0 / 4.1%. Decisions in ASSUMPTIONS.md.
* **Sensitivities of `'horup_item'`** (deterministic carbon / cumulative LoE):
  proxies held at 2025 +0.3%; NZ-made electricity-intensive items held at 2025
  +1.7%; lift at steel profile −0.1%; class-level mapping of v1.1 +1.2%; frozen
  technology +8.4%. In `sensitivity_oat.csv` and `pb_sensitivity.csv` / pb_4 of
  the item-level run (`outputs/modes/horup_item/`).
* **Pipeline**: `run_all.py` runs every non-adopted mode in full into
  `outputs/modes/<mode>/` (`PATHWAY_DECARB_MODE`) and PB in the frozen run;
  `tools/decarb_modes.py` writes `outputs/DECARB_MODES.md`. RESULTS,
  BASELINE_DRAFT and PB_METHODS_DRAFT report the modes; ASSUMPTIONS documents
  both mappings.
* **Tests** (78 pass): item mapping complete and one-to-one, workbook
  reproduction, class totals at 2025, independent recomputation of the pooled
  reductions, soil / other stages / history unchanged, sensitivity cases, and
  `tests/test_regression_pb_v1_1.py` (class-level mode equals the
  baseline-PB_v1.1 outputs exactly); the v1.2.1 regression ('none') unchanged.
* **Figures**: no adopted-run figure changes (the adopted mode is unchanged);
  captions of sens_1 and pb_4 name the decarbonisation rows; pb_4 height scales
  with the number of rows (unchanged for the adopted mode).
* **Run time**: full run 1,420 s (sum of step times) on 4 cores.

## baseline-pb-v1.1

**Adopted carbon factors change**: materials are decarbonised (author decision),
so headline carbon and levels of exceedance differ from baseline-pb-v1, which is
now the frozen-technology sensitivity. Floor area, the history, the AR base and
the boundaries are unchanged.

| 2026-2050, reference S3-10 | frozen technology (`'none'`) | adopted (`'horup_material'`) |
|---|---|---|
| Floor area (Mm²) | 89.57 | 89.57 |
| Embodied carbon (kt CO₂e) | 33,625 | 31,400 (−6.6%) |
| Upfront, A1-A5 + soil (kt) | 24,204 | 21,979 |
| MC carbon p5 / p50 / p95 (kt) | 25,743 / 33,268 / 41,644 | 24,119 / 31,095 / 38,863 |
| Cumulative LoE_AR (MC p5-p95) | 5.41 (4.29-6.46) | 5.05 (4.05-5.99) |
| Cumulative LoE_AtP (MC p5-p95) | 30.2 (24.0-36.1) | 28.2 (22.4-33.6) |

* **Material decarbonisation** (`Boss.DECARB_MODE = 'horup_material'`): the
  A1-A3 factor of each case-study material class follows the relative GWP path
  of its counterpart in Horup et al. (2025), Sci. Total Environ. 966, 178780, SI
  Table S4 (average of 9 premise scenarios, relative to 2025; linear between
  2025, 2030, 2040, 2050). Concrete and reinforced concrete -> concrete
  structure; STEEL -> reinforcing steel (steel profile is a sensitivity);
  timber -> construction wood; aluminium, bricks, glass, glass wool -> their S4
  rows; the rest held at 2025. A4-A5, B2, B4, C1-C4, soil and the 1991-2025
  history (the acquired-rights base) always at 2025 factors. Built by
  `data/build_horup.py` and `Building_factors.py`; carried through
  `engine.forward` (per-year intensities), Boss, scenarios, Sensitivity, the
  Monte Carlo (the bootstrap resamples the reduction with the same cases;
  random stream unchanged) and PB. Decisions and limitations in ASSUMPTIONS.md.
* **Frozen-technology check**: `run_all.py` runs Boss, Sensitivity, MonteCarlo
  and the scenario table with `DECARB_MODE = 'none'` into `outputs/frozen/`;
  `tests/test_regression_v1_2_1.py` compares it with v1.2.1 (all files
  byte-identical to baseline-pb-v1).
* **PB Monte Carlo**: the AR base Ī_sec,base is recomputed per draw from the
  draw's 2025 carbon factors on the observed history (5th-95th 1,862-2,116
  kt/yr). Cumulative LoE_AR, S3-10: 4.01 / 5.00 / 6.02 with the base fixed,
  4.05 / 5.02 / 5.99 per draw (p5 / p50 / p95); AtP unchanged. The fixed-base
  bands stay in `pb_results.json` (`mc_base_fixed`).
* **Quick mode** (`run_all.py --quick`, development only): 1,000 Monte Carlo draws
  per scenario (128 Sobol base samples), no frozen-technology Monte Carlo, MC
  regression checks skipped; `metrics.json` (`run_mode`), the generated
  documents and every figure are marked "QUICK RUN, not for reporting". Checked
  against the full run: every cumulative carbon and LoE percentile (p5, p50,
  p95; S3-10, S1, S2) within 0.84%.
* **Figures**: stacked panels are anchored at y = 0 (`Boss.zero_floor()`, which
  checks that every series is >= 0): boss_04, boss_05, boss_05_annual_carbon_pb,
  boss_06, boss_06_cumulative_carbon_pb, boss_10, diag_5, pb_5. Labels and units
  harmonised (CO₂e, m², persons/households); captions state the carbon-factor
  basis; pb_4 gains the frozen-technology and steel-profile rows.
* **Audit fixes**: regression test pinned to `'none'`; `test_soil` uses the
  run's own intensity; ASSUMPTIONS.md no longer lists run-time display switches;
  three unused Boss settings removed; RESULTS/PB methods state the factor
  basis; B_AtP rounding aligned; Hjalsted α limitation added; README run time.
  Open: the completion-rate citation (Jones et al. 2024) is to be supplied.
* **Environment**: the full pipeline of this version under Python 3.12.3 with
  the same pinned packages gives byte-identical outputs (all 57 versioned output
  files) and pixel-identical figures (35) to Python 3.11. Full run 769-770 s on
  4 cores; quick run about 6 minutes; 63 tests pass.

## baseline-pb-v1

A planetary-boundary (AESA, climate change) layer on top of baseline v2.
**The baseline is unchanged**: `tests/test_regression_v1_2_1.py` passes and
every existing key of `outputs/metrics.json` keeps its value; the new metrics
are under the key `pb`.

* **New:** `aesa.py` (pure functions: Horup et al. 2025 Eq. 1; Hjalsted et
  al. 2021 Eqs. 5-6 and SI S1; levels of exceedance), `PB.py` (data, scenario
  and Monte Carlo runs, sensitivities, figures `boss_05/06_*_pb`,
  `fig_scenarios_pb`, `mc_1_fan_pb`, `pb_1`-`pb_5`), `tools/pb_methods.py`
  (`outputs/PB_METHODS_DRAFT.md`), `tests/test_pb.py`.
* **Data:** `data/build_gdp.py`, `build_wpp.py`, `build_wdi.py` build
  `data/derived/` from supplied raw files (Stats NZ GDP(E) SNE022AA; UN WPP
  2024 probabilistic median; World Bank WDI), recorded in MANIFEST.csv.
  `refs/` (papers) and the earlier-manuscript workbook are git-ignored.
* **Changed outside the new files:** `run_all.py` (step `pb` after the Monte
  Carlo, `pb_methods` at the end), `tools/metrics.py` (key `pb`),
  `tools/results.py`, `tools/assumptions.py`, `tools/baseline_draft.py`,
  `tools/figures_report.py` (PB sections and figure entries), README,
  ARCHITECTURE, `.gitignore`. `Boss.py`, `engine.py` and `MonteCarlo.py` are
  not modified.

## Baseline v2

v2 = cleaned v1.2.1. Full development history (every intermediate version,
option, note, equivalence proof and before/after metrics table) at the git tag
`baseline-v1.2.1` (commit a83cf03).

**Results are unchanged.** `tests/test_regression_v1_2_1.py` checks the central
run, the totals of all ten scenarios, the four Monte Carlo summaries and the
sensitivity table against v1.2.1 to 1e-9 (relative). Monte Carlo draws, fans
and Sobol indices are byte-identical. The one sensitivity row removed (the
v1.0.2 three-channel join) is excluded from that comparison.

What changed:

* **Code.** Options that were not used by the adopted run or by a row of the
  sensitivity table were removed: the three-channel near-term join, the
  population-nowcast alternatives, the per-person/per-household consumption
  bases, the household-identity sources of net replacement, the legacy consent
  and census sources, earlier household-size methods and tails, the
  migration-response size path, the full-input Monte Carlo, and related flags.
  Kept: completion lag, payback and gap-vs-2026 variants of the near-term rule,
  household-size tail alternatives, all scenarios, carbon-factor and soil
  bounds.
* **Documents.** Earlier-iteration notes, reviews, equivalence proofs, step
  reports and assessment evidence were removed (they remain at the tag).
  README, ARCHITECTURE.md, FIGURES.md and this file were rewritten;
  ASSUMPTIONS.md, RESULTS.md and BASELINE_DRAFT.md are regenerated.
* **Running.** `run_all.py` resolves paths from the repository folder, runs
  the tests after the outputs they check, and in Spyder/IPython reports a failed
  step and its log instead of raising `SystemExit`.
* **Figures.** Households and household size distinguish census-benchmarked,
  census-scaled and consent-derived years and project from the 2023 census
  point; demand-band figures show in-scope bands only (no negative or avoided
  bands); fixed material palette; census-interval history in diag_3/diag_4;
  new fig_replacement_rate; diag_1 and diag_6 removed (identities remain as
  tests; the handover panel moved to fig_reality_checks). See FIGURES.md.

Environment: `requirements.txt` (Python 3.11.15). Seeds fixed.
