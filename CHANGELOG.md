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

## Validation harness: rolling-origin hindcast and 2026 check (item 10, A2)

validation.py runs after every change (run_all.py) and writes outputs/validation.md/json. (1) Rolling-origin hindcast at census origins 2006/2013/2018 (Tashman 2000): the net-replacement rate is calibrated up to the origin only; dwellings built to 2023 are predicted with actual households and vacancy (a conditional hindcast of the one calibrated term); methods constant / most recent intercensal rate / linked townhouse model. Three origins support no test statistic, so the errors are descriptive. (2) 2026 out-of-sample check against observed all-category consents, year-to-date months compared via 2010-2025 seasonal shares; PENDING until the consent file reaches 2026. Not used to set any parameter. No model change; the hindcast reproduces ASSESSMENT.md C5 exactly.

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
| Hindcast error, origin 2006, model method (%) | n/a | -13.0 |  |
| Hindcast error, origin 2013, model method (%) | n/a | -18.9 |  |
| Hindcast error, origin 2018, model method (%) | n/a | -12.0 |  |
| 2026 model consent-equivalents (all categories) | n/a | 29,754 |  |
| 2026 observed / model consents, year to date | n/a | n/a |  |

Validation (outputs/validation.md):

### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.043 | 400,634 | 460,544 | -13.0% |
| 2006 | 2007-2023 | recent | -0.049 | 371,979 | 460,544 | -19.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.54 on 3 intervals | 484,994 | 460,544 | +5.3% |
| 2013 | 2014-2023 | constant | +0.034 | 276,609 | 340,888 | -18.9% |
| 2013 | 2014-2023 | recent | +0.019 | 273,758 | 340,888 | -19.7% |
| 2013 | 2014-2023 | linked | linked: b = 0.96 on 4 intervals | 333,710 | 340,888 | -2.1% |
| 2018 | 2019-2023 | constant | +0.109 | 177,962 | 202,189 | -12.0% |
| 2018 | 2019-2023 | recent | +0.389 | 205,531 | 202,189 | +1.7% |
| 2018 | 2019-2023 | linked | linked: b = 1.34 on 5 intervals | 249,717 | 202,189 | +23.5% |

### 2026 out-of-sample check against observed consents

PENDING: the consent file ends 2025-12-01. Model 2026: 28,266 dwellings built (all categories) = 29,754 consent-equivalents.

## Consents built by script from the raw Stats NZ release (data provenance)

data/fetch_sources.py downloads 'Building consents issued: July 2026' (Stats NZ) into data/raw/ and records URL, SHA-256 and date in data/raw/MANIFEST.csv; data/build_consents.py extracts New Zealand / New / Actual series (number, floor area, value) for houses, townhouses-flats-units, apartments, retirement-village units and all dwelling units into data/derived/consents_monthly.csv. It reproduces data/consentdata.xlsx exactly in all 13 columns for every month 1990-04..2025-12, and the published totals 40,581 (year ended June 2026) and 40,908 (year ended July 2026). Boss reads it by default (CONSENT_SOURCE = 'statsnz_release'; 'legacy_xlsx' keeps the original file). Model outputs unchanged (1991-2025 identical). The 2026 out-of-sample check is now observed: Jan-Jul 2026 consents are 1.432 x the model's 2026 consent-equivalent apportioned by 2010-2025 seasonal shares. Descriptive only; not used to set any parameter. The DataInfo+ page cited for F1/N1 is saved in data/raw/ with its SHA-256.

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
| Hindcast error, origin 2006, model method (%) | -13.0 | -13.0 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.9 | -18.9 | 0 |
| Hindcast error, origin 2018, model method (%) | -12.0 | -12.0 | 0 |
| 2026 model consent-equivalents (all categories) | 29,754 | 29,754 | 0 |
| 2026 observed / model consents, year to date | n/a | 1.432 |  |

Validation (outputs/validation.md):

### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.043 | 400,634 | 460,544 | -13.0% |
| 2006 | 2007-2023 | recent | -0.049 | 371,979 | 460,544 | -19.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.54 on 3 intervals | 484,994 | 460,544 | +5.3% |
| 2013 | 2014-2023 | constant | +0.034 | 276,609 | 340,888 | -18.9% |
| 2013 | 2014-2023 | recent | +0.019 | 273,758 | 340,888 | -19.7% |
| 2013 | 2014-2023 | linked | linked: b = 0.96 on 4 intervals | 333,710 | 340,888 | -2.1% |
| 2018 | 2019-2023 | constant | +0.109 | 177,962 | 202,189 | -12.0% |
| 2018 | 2019-2023 | recent | +0.389 | 205,531 | 202,189 | +1.7% |
| 2018 | 2019-2023 | linked | linked: b = 1.34 on 5 intervals | 249,717 | 202,189 | +23.5% |

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 16,699 (annual 29,754 x seasonal share 0.561); observed / model = 1.432. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Household size held flat after the last published knot (item 5, C2)

New flag S_TAIL, default 'flat': household size after 2043 is held at its 2043 value (zero-order hold) instead of continuing the PCHIP end derivative, which is 2.5x the published 2038->2043 slope. Applied identically in Boss and in every MC variant path. The original ('pchip_end_slope'), the 2038-43 secant and the mean 2018-43 slope are reported in Sensitivity.py (77.54 / 80.24 / 76.71 Mm2). Consolidation savings fall from 1.29 to 0.30 Mm2 (those left are inside the published knots, 2039-2043). N4 and the private-household population question remain open (E2 deferred). Legacy behaviour: tests/legacy_flags.py; equivalence with the frozen code still exact.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.71 | 78.20 | +1.49 (+1.94%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,708 | 30,284 | +576 (+1.94%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,862 | 22,287 | +425 (+1.95%) |
| 2025 -> 2026 step in built floor area (%) | -22.1 | -22.1 | 0 |
| Household size 2050, central run | 2.641 | 2.628 | -0.0121 (-0.46%) |
| MC floor area p5 (Mm2) | 59.98 | 59.99 | +0.0108 (+0.02%) |
| MC floor area p50 (Mm2) | 80.66 | 82.14 | +1.47 (+1.83%) |
| MC floor area p95 (Mm2) | 104.57 | 107.39 | +2.83 (+2.70%) |
| MC carbon p5 (kt) | 23,168 | 23,200 | +32.3 (+0.14%) |
| MC carbon p50 (kt) | 31,191 | 31,730 | +539 (+1.73%) |
| MC carbon p95 (kt) | 40,888 | 41,899 | +1.01e+03 (+2.47%) |
| Central run percentile in MC, floor area | 38.5 | 39.3 | +0.72 |
| Central run percentile in MC, carbon | 39.0 | 39.7 | +0.66 |
| Hindcast error, origin 2006, model method (%) | -13.0 | -13.0 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.9 | -18.9 | 0 |
| Hindcast error, origin 2018, model method (%) | -12.0 | -12.0 | 0 |
| 2026 model consent-equivalents (all categories) | 29,754 | 29,754 | 0 |
| 2026 observed / model consents, year to date | 1.432 | 1.432 | 0 |

Validation (outputs/validation.md):

### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.043 | 400,634 | 460,544 | -13.0% |
| 2006 | 2007-2023 | recent | -0.049 | 371,979 | 460,544 | -19.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.54 on 3 intervals | 484,994 | 460,544 | +5.3% |
| 2013 | 2014-2023 | constant | +0.034 | 276,609 | 340,888 | -18.9% |
| 2013 | 2014-2023 | recent | +0.019 | 273,758 | 340,888 | -19.7% |
| 2013 | 2014-2023 | linked | linked: b = 0.96 on 4 intervals | 333,710 | 340,888 | -2.1% |
| 2018 | 2019-2023 | constant | +0.109 | 177,962 | 202,189 | -12.0% |
| 2018 | 2019-2023 | recent | +0.389 | 205,531 | 202,189 | +1.7% |
| 2018 | 2019-2023 | linked | linked: b = 1.34 on 5 intervals | 249,717 | 202,189 | +23.5% |

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 16,699 (annual 29,754 x seasonal share 0.561); observed / model = 1.432. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Household size anchored on the census-benchmarked year 2023 (item 6, C3)

New flag S_ANCHOR_YEAR, default 2023: the Stats NZ household-size shape is rebased on observed S in December 2023 (the last census-benchmarked year) and carried through 2025 by the Stats NZ shape, instead of on 2025, whose households are 0.888 x lagged consents (the same DHE artefact the model already refuses to carry as e_2025). S in 2025 becomes 2.680 (observed-anchored 2.657). Caveat stated in Boss.py: the anchor is 31 December 2023, six months after the June census benchmark, and those six months are consent-derived. The 2025 anchor is a Sensitivity.py row. The 2025 stock deviation (other_dev_2025) is unchanged here; per D1 its treatment is A1.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 78.20 | 77.53 | -0.67 (-0.86%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 30,284 | 30,025 | -259 (-0.86%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 22,287 | 22,096 | -191 (-0.86%) |
| 2025 -> 2026 step in built floor area (%) | -22.1 | -22.7 | -0.608 |
| Household size 2050, central run | 2.628 | 2.651 | +0.0229 (+0.87%) |
| MC floor area p5 (Mm2) | 59.99 | 59.47 | -0.517 (-0.86%) |
| MC floor area p50 (Mm2) | 82.14 | 81.31 | -0.824 (-1.00%) |
| MC floor area p95 (Mm2) | 107.39 | 106.28 | -1.11 (-1.04%) |
| MC carbon p5 (kt) | 23,200 | 22,983 | -217 (-0.94%) |
| MC carbon p50 (kt) | 31,730 | 31,409 | -322 (-1.01%) |
| MC carbon p95 (kt) | 41,899 | 41,487 | -413 (-0.99%) |
| Central run percentile in MC, floor area | 39.3 | 39.5 | +0.27 |
| Central run percentile in MC, carbon | 39.7 | 40.0 | +0.29 |
| Hindcast error, origin 2006, model method (%) | -13.0 | -13.0 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.9 | -18.9 | 0 |
| Hindcast error, origin 2018, model method (%) | -12.0 | -12.0 | 0 |
| 2026 model consent-equivalents (all categories) | 29,754 | 29,522 | -232 (-0.78%) |
| 2026 observed / model consents, year to date | 1.432 | 1.443 | +0.0113 (+0.79%) |

Validation (outputs/validation.md):

### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.043 | 400,634 | 460,544 | -13.0% |
| 2006 | 2007-2023 | recent | -0.049 | 371,979 | 460,544 | -19.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.54 on 3 intervals | 484,994 | 460,544 | +5.3% |
| 2013 | 2014-2023 | constant | +0.034 | 276,609 | 340,888 | -18.9% |
| 2013 | 2014-2023 | recent | +0.019 | 273,758 | 340,888 | -19.7% |
| 2013 | 2014-2023 | linked | linked: b = 0.96 on 4 intervals | 333,710 | 340,888 | -2.1% |
| 2018 | 2019-2023 | constant | +0.109 | 177,962 | 202,189 | -12.0% |
| 2018 | 2019-2023 | recent | +0.389 | 205,531 | 202,189 | +1.7% |
| 2018 | 2019-2023 | linked | linked: b = 1.34 on 5 intervals | 249,717 | 202,189 | +23.5% |

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 16,569 (annual 29,522 x seasonal share 0.561); observed / model = 1.443. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.
