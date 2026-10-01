# CHANGELOG

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
