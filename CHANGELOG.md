# CHANGELOG

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
