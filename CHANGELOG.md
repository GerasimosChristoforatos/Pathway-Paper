# CHANGELOG

One entry per commit that can change a number. Each entry is written by
`tools/changelog.py` after a full `python run_all.py`: 'before' is
`outputs/metrics.json` as committed at the previous commit, 'after' is the
fresh run. Environment: `requirements.txt` (Python 3.11.15). Seeds fixed.

MC = Monte Carlo (10,000 Latin hypercube draws). "Central run percentile" =
share of MC draws below the deterministic central run.

## Baseline (commit e1f98ff, code as supplied; reproduced in Step 0)

| metric | value |
|---|---|
| Built floor area 2026-2050, central run (Mm2)  |  76.71 |
| Embodied carbon 2026-2050, central run (kt CO2e)  |  29,708 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e)  |  21,862 |
| 2025 -> 2026 step in built floor area (%)  |  -22.1 |
| Household size 2050, central run  |  2.641 |
| MC floor area p5 (Mm2)  |  59.98 |
| MC floor area p50 (Mm2)  |  80.66 |
| MC floor area p95 (Mm2)  |  104.57 |
| MC carbon p5 (kt)  |  23,168 |
| MC carbon p50 (kt)  |  31,191 |
| MC carbon p95 (kt)  |  40,888 |
| Central run percentile in MC, floor area  |  38.5 |
| Central run percentile in MC, carbon  |  39.0 |

## Pinned environment (0143f22)

`requirements.txt` added. No code change; no number changes.

## Derived outputs moved from data/ to outputs/ (c94d8e5, D4)

Paths only. factors, sensitivity and MC summary/draws regenerated
byte-identically; all metrics unchanged (table identical to baseline).
`montecarlo_annual.csv` regenerated (the committed copy predated the
25th/75th columns). Sobol point estimates identical; bootstrap CIs differ
because they were still unseeded.

## run_all.py, figure saving and metrics tooling (item 1)

Adds run_all.py (headless; every figure to outputs/figures/, logs to outputs/logs/), tools/metrics.py (outputs/metrics.json) and tools/changelog.py. Figure saving is controlled by PATHWAY_SAVE_FIGURES, off by default, so interactive behaviour is unchanged; Boss saves only when run as a script. No model change.

First metrics file, so 'before' is empty; the values equal the Baseline table above.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | n/a | 76.71 |  |
| Embodied carbon 2026-2050, central run (kt CO2e) | n/a | 29,708 |  |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | n/a | 21,862 |  |
| 2025 -> 2026 step in built floor area (%) | n/a | -22.1 |  |
| Household size 2050, central run | n/a | 2.641 |  |
| MC floor area p5 (Mm2) | n/a | 59.98 |  |
| MC floor area p50 (Mm2) | n/a | 80.66 |  |
| MC floor area p95 (Mm2) | n/a | 104.57 |  |
| MC carbon p5 (kt) | n/a | 23,168 |  |
| MC carbon p50 (kt) | n/a | 31,191 |  |
| MC carbon p95 (kt) | n/a | 40,888 |  |
| Central run percentile in MC, floor area | n/a | 38.5 |  |
| Central run percentile in MC, carbon | n/a | 39.0 |  |
