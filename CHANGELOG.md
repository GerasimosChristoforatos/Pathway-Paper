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

## Seed the Sobol bootstrap (item 1, N3)

MonteCarlo seeds numpy's global generator (SEED + 3) immediately before SobolResult.bootstrap(), which accepts no rng in scipy 1.17. Sobol confidence intervals are now reproducible: montecarlo_sobol.csv is byte-identical across two independent runs. Point estimates and all headline metrics unchanged.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.71 | 76.71 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,708 | 29,708 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,862 | 21,862 | 0 |
| 2025 -> 2026 step in built floor area (%) | -22.1 | -22.1 | 0 |
| Household size 2050, central run | 2.641 | 2.641 | 0 |
| MC floor area p5 (Mm2) | 59.98 | 59.98 | 0 |
| MC floor area p50 (Mm2) | 80.66 | 80.66 | 0 |
| MC floor area p95 (Mm2) | 104.57 | 104.57 | 0 |
| MC carbon p5 (kt) | 23,168 | 23,168 | 0 |
| MC carbon p50 (kt) | 31,191 | 31,191 | 0 |
| MC carbon p95 (kt) | 40,888 | 40,888 | 0 |
| Central run percentile in MC, floor area | 38.5 | 38.5 | 0 |
| Central run percentile in MC, carbon | 39.0 | 39.0 | 0 |

## Identity tests (item 2)

tests/test_identities.py: 23 accounting identities checked to 1e-9 x the largest value (history: typology sum, share sums, dwelling-weighted size blend, stock identity every year, history reconstructed by the demand bands; forward: bands sum to total, structural identity, stock identity, RV share, typology split, for all three population paths; carbon: materials + soil, stages + soil, bands; determinism with no leaked module state). Mutation check: a +100 m2, +1 dwelling or +1 t error is detected. run_all.py runs them after the MC. No model change.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.71 | 76.71 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,708 | 29,708 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,862 | 21,862 | 0 |
| 2025 -> 2026 step in built floor area (%) | -22.1 | -22.1 | 0 |
| Household size 2050, central run | 2.641 | 2.641 | 0 |
| MC floor area p5 (Mm2) | 59.98 | 59.98 | 0 |
| MC floor area p50 (Mm2) | 80.66 | 80.66 | 0 |
| MC floor area p95 (Mm2) | 104.57 | 104.57 | 0 |
| MC carbon p5 (kt) | 23,168 | 23,168 | 0 |
| MC carbon p50 (kt) | 31,191 | 31,191 | 0 |
| MC carbon p95 (kt) | 40,888 | 40,888 | 0 |
| Central run percentile in MC, floor area | 38.5 | 38.5 | 0 |
| Central run percentile in MC, carbon | 39.0 | 39.0 | 0 |

## Single pure engine shared by Boss and MonteCarlo (item 3, C1, N2)

The forward model moves to engine.py as pure functions (stock calibration, 2025 deviation, damped mix, size blend, forward projection to carbon). Boss.main() and MonteCarlo.project() both call it. Boss binds its calibration settings once at the start of main(); MonteCarlo copies everything it needs from Boss once in build_setup(), so no draw reads mutable Boss module globals (N2). validate() now checks floor area, carbon, upfront carbon, RV units, households and S.

Equivalence against frozen copies of the pre-unification code (tests/legacy/, commit a25fbff), outputs/equivalence_proof_item3.md: Boss.main() on 200 random draws of its own settings (all four consumption bases, both percentile methods, floor on/off, per-resident OLF, variants, response mode): every band, stock term, household path and carbon table bit-identical (difference 0.0). MonteCarlo.project() on 301 random draws of all 12 inputs (half from the input distributions, half from widened ranges) and 101 draws in response mode: largest relative difference 7.2e-15.

One deliberate difference: the old MC engine computed floor area as in-scope dwellings x realised size; Boss (and now both) adds extra space floored at zero. They differ only where realised size falls below occupied area. That happened in 1 of the 301 widened test draws (verified: new = legacy + that term) and in none of the 10,000 real MC draws. MC outputs differ from the previous commit by at most 1.5e-12 relative (floating-point order; Boss's polyfit slopes replace the MC's own lstsq slopes).

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.71 | 76.71 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,708 | 29,708 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,862 | 21,862 | 0 |
| 2025 -> 2026 step in built floor area (%) | -22.1 | -22.1 | 0 |
| Household size 2050, central run | 2.641 | 2.641 | 0 |
| MC floor area p5 (Mm2) | 59.98 | 59.98 | 0 |
| MC floor area p50 (Mm2) | 80.66 | 80.66 | 0 |
| MC floor area p95 (Mm2) | 104.57 | 104.57 | 0 |
| MC carbon p5 (kt) | 23,168 | 23,168 | 0 |
| MC carbon p50 (kt) | 31,191 | 31,191 | 0 |
| MC carbon p95 (kt) | 40,888 | 40,888 | 0 |
| Central run percentile in MC, floor area | 38.5 | 38.5 | 0 |
| Central run percentile in MC, carbon | 39.0 | 39.0 | 0 |
