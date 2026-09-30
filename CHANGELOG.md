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

## Completion lag from Little's law (item 7, C4, N5)

New flag COMPLETION_LAG, default 'littles_law': dwellings completed in year t = c x [(1 - W) consents_t + W consents_(t-1)], W estimated at run time as the mean over censuses 1986-2023 of dwellings under construction / all dwellings consented in the 12 months to March of the census year (Little 1961): 0.45, 0.46, 0.49, 0.47, 0.53, 0.56, 0.51, 0.58 -> W = 0.508 yr. The same completions series feeds the stock calibration, the 2025 deviation, the 2025 observed anchor (so the step), history plots, validation and the MC. Limitations stated at the flag: W is time under construction only (a lower bound on consent-to-completion), steady-state assumption, kernel shape assumed. Boss's old build-duration printout (0.78 yr in 2023: March stock over a calendar-year flow) is replaced. Net replacement calibrates to 0.137%/yr (was 0.154%); 2025 deviation +4,411 (was +5,494), persistence 0.68. Sensitivities: no lag (original) 77.53 Mm2; W = 0.99 74.94 Mm2. The dwelling-count census check still uses the June-year convention; item 4 rebuilds it on the same W. The 2026 check now inverts the lag: the model's 2026 completions imply 21,888 consents in 2026 against observed Jan-Jul consents 1.95 x that (seasonally apportioned).

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 77.53 | 76.71 | -0.814 (-1.05%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 30,025 | 29,709 | -316 (-1.05%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 22,096 | 21,863 | -233 (-1.06%) |
| 2025 -> 2026 step in built floor area (%) | -22.7 | -19.1 | +3.59 |
| Household size 2050, central run | 2.651 | 2.651 | 0 |
| MC floor area p5 (Mm2) | 59.47 | 58.26 | -1.21 (-2.04%) |
| MC floor area p50 (Mm2) | 81.31 | 80.03 | -1.28 (-1.57%) |
| MC floor area p95 (Mm2) | 106.28 | 104.96 | -1.32 (-1.25%) |
| MC carbon p5 (kt) | 22,983 | 22,552 | -431 (-1.87%) |
| MC carbon p50 (kt) | 31,409 | 30,920 | -489 (-1.56%) |
| MC carbon p95 (kt) | 41,487 | 40,937 | -549 (-1.32%) |
| Central run percentile in MC, floor area | 39.5 | 40.7 | +1.21 |
| Central run percentile in MC, carbon | 40.0 | 40.9 | +0.97 |
| Hindcast error, origin 2006, model method (%) | -13.0 | -13.2 | -0.207 (+1.59%) |
| Hindcast error, origin 2013, model method (%) | -18.9 | -17.3 | +1.57 (-8.34%) |
| Hindcast error, origin 2018, model method (%) | -12.0 | -11.9 | +0.0619 (-0.52%) |
| 2026 model consent-equivalents (all categories) | 29,522 | 21,888 | -7.63e+03 (-25.86%) |
| 2026 observed / model consents, year to date | 1.443 | 1.947 | +0.503 (+34.88%) |

Validation (outputs/validation.md):

### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 394,956 | 455,099 | -13.2% |
| 2006 | 2007-2023 | recent | -0.082 | 361,815 | 455,099 | -20.5% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 476,526 | 455,099 | +4.7% |
| 2013 | 2014-2023 | constant | +0.029 | 275,606 | 333,193 | -17.3% |
| 2013 | 2014-2023 | recent | +0.038 | 277,274 | 333,193 | -16.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 320,857 | 333,193 | -3.7% |
| 2018 | 2019-2023 | constant | +0.092 | 176,284 | 200,142 | -11.9% |
| 2018 | 2019-2023 | recent | +0.328 | 199,502 | 200,142 | -0.3% |
| 2018 | 2019-2023 | linked | linked: b = 1.09 on 5 intervals | 234,623 | 200,142 | +17.2% |

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,285 (annual 21,888 x seasonal share 0.561); observed / model = 1.947. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Census 2018/2023 occupancy built by script, private dwellings only (E1)

data/build_census.py builds data/derived/census_dwellings.csv from Aotearoa Data Explorer CEN23_HOU_018 (occupancy status x dwelling type), cross-checked against CEN23_TBT_001 (all-type totals identical) and, for 2013, against the QuickStats file used for 1981-2013 (identical within random rounding, +/-3). Finding: the hard-coded CENSUS_LATER values were ALL dwelling types, i.e. they included the unoccupied non-private dwellings Stats NZ counts from 2018 (4,860 in 2018, 4,710 in 2023), while 1981-2013 are private only. New flag CENSUS_SOURCE = 'hou018_private' (default) | 'hardcoded' (original). Private-only vacancy: 2018 5.08% (was 5.26%), 2023 5.39% (was 5.53%, held forward). Private residents-away enters the census rebase: k = 0.824 (was 0.826). Private under-construction: W = 0.507. The household-identity net replacement rate rises to 0.143%/yr (the 2013->2018 fall in 'empty' is now larger, which strengthens N1). The Boss comment claiming unoccupied dwellings are private by definition is corrected.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.71 | 77.05 | +0.338 (+0.44%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,709 | 29,840 | +131 (+0.44%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,863 | 21,959 | +96.3 (+0.44%) |
| 2025 -> 2026 step in built floor area (%) | -19.1 | -18.9 | +0.183 |
| Household size 2050, central run | 2.651 | 2.652 | +0.000362 (+0.01%) |
| MC floor area p5 (Mm2) | 58.26 | 58.32 | +0.0651 (+0.11%) |
| MC floor area p50 (Mm2) | 80.03 | 80.15 | +0.116 (+0.14%) |
| MC floor area p95 (Mm2) | 104.96 | 104.96 | +0.00204 (+0.00%) |
| MC carbon p5 (kt) | 22,552 | 22,580 | +27.6 (+0.12%) |
| MC carbon p50 (kt) | 30,920 | 30,995 | +75.6 (+0.24%) |
| MC carbon p95 (kt) | 40,937 | 40,935 | -2.78 (-0.01%) |
| Central run percentile in MC, floor area | 40.7 | 41.3 | +0.54 |
| Central run percentile in MC, carbon | 40.9 | 41.7 | +0.74 |
| Hindcast error, origin 2006, model method (%) | -13.2 | -14.0 | -0.756 (+5.72%) |
| Hindcast error, origin 2013, model method (%) | -17.3 | -18.3 | -1.04 (+6.00%) |
| Hindcast error, origin 2018, model method (%) | -11.9 | -11.4 | +0.532 (-4.46%) |
| 2026 model consent-equivalents (all categories) | 21,888 | 22,059 | +171 (+0.78%) |
| 2026 observed / model consents, year to date | 1.947 | 1.932 | -0.0151 (-0.77%) |

Validation (outputs/validation.md):

### Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,380 (annual 22,059 x seasonal share 0.561); observed / model = 1.932. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Net replacement calibrated from census dwelling counts (item 4, D2, N1)

New flag NET_REPLACEMENT_SOURCE, default 'dwelling_count': the long-run net replacement rate comes from the census dwelling-count identity over 1991->2023 (completions - change in census private dwellings, per stock-year; engine.census_interval_rates), which uses neither household estimates nor the census empty/away split that breaks in 2018. Completions use the model's lag W in continuous time (mid-month consents in (census - W, next census - W]), replacing the June-year convention of the old printout; census nights taken as 5 March (all fell on 4-7 March). Rate 0.113%/yr (household identity as published: 0.143%). By interval (dwelling counts / household identity): 1991-96 +0.063/+0.219, 1996-01 -0.100/-0.043, 2001-06 +0.027/-0.082, 2006-13 +0.087/+0.038, 2013-18 +0.163/+0.369, 2018-23 +0.360/+0.333 %/yr: only 2018-23 is elevated in the dwelling counts. Cross-checks (outputs/validation.md): identity on the DHE dwelling series 0.120%/yr; Stats NZ's post-2023 intercensal weight (0.889 x consents lagged 4 quarters) implies ~0.000%/yr with this model's completion rate and lag (an assumption of Stats NZ, not an observation; this corrects the rougher ~0.09% reading in the ASSESSMENT addendum). Sensitivities: household identity (original) 77.05, constant empty share 72.91, dwelling counts 2013-2023 85.20, 2018-2023 (S2) 91.54 Mm2. Validation adds hindcast (B), the 2023 census stock predicted from each origin (dwelling-count identity): +12% to +19% (net removals after each origin exceeded the rate calibrated before it), and the dwelling-count method in hindcast (A). The MC still blends the long-run and 2018-23 rates with a Uniform(0,1) weight; with dwelling counts the blend spans 0.113-0.360%, which raises the MC median while the central run falls, so the central run is now at the 26.5th percentile. Per D3 that blend becomes scenarios S1/S2 in item 9.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 77.05 | 75.01 | -2.04 (-2.65%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,840 | 29,049 | -791 (-2.65%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,959 | 21,377 | -583 (-2.65%) |
| 2025 -> 2026 step in built floor area (%) | -18.9 | -19.5 | -0.599 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| MC floor area p5 (Mm2) | 58.32 | 61.70 | +3.38 (+5.79%) |
| MC floor area p50 (Mm2) | 80.15 | 83.97 | +3.82 (+4.76%) |
| MC floor area p95 (Mm2) | 104.96 | 108.84 | +3.88 (+3.70%) |
| MC carbon p5 (kt) | 22,580 | 23,864 | +1.28e+03 (+5.69%) |
| MC carbon p50 (kt) | 30,995 | 32,434 | +1.44e+03 (+4.64%) |
| MC carbon p95 (kt) | 40,935 | 42,436 | +1.5e+03 (+3.67%) |
| Central run percentile in MC, floor area | 41.3 | 26.5 | -14.8 |
| Central run percentile in MC, carbon | 41.7 | 27.1 | -14.5 |
| Hindcast error, origin 2006, model method (%) | n/a | -15.9 |  |
| Hindcast error, origin 2013, model method (%) | n/a | -18.4 |  |
| Hindcast error, origin 2018, model method (%) | n/a | -13.5 |  |
| 2026 model consent-equivalents (all categories) | 22,059 | 21,618 | -441 (-2.00%) |
| 2026 observed / model consents, year to date | 1.932 | 1.971 | +0.0394 (+2.04%) |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Retirement-village floor area reported as its own series, out of scope (A4)

Stats NZ publishes retirement-village floor area consented; data/build_consents.py already extracts it. Boss now reports RV floor area: history on the built basis, and a projection = projected RV units x RV floor area per unit over DWELLING_SIZE_REF (124.2 m2/unit, 2023-2025) = 4.29 Mm2 built 2026-2050 (the in-scope total is 75.01 Mm2). New flag RV_FLOOR_AREA_IN_SCOPE = False; True raises NotImplementedError until an RV carbon factor is chosen (no case study exists, so any factor would be judgement). In-scope floor area and carbon unchanged.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 75.01 | 75.01 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,049 | 29,049 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,377 | 21,377 | 0 |
| 2025 -> 2026 step in built floor area (%) | -19.5 | -19.5 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | n/a | 4.29 |  |
| MC floor area p5 (Mm2) | 61.70 | 61.70 | 0 |
| MC floor area p50 (Mm2) | 83.97 | 83.97 | 0 |
| MC floor area p95 (Mm2) | 108.84 | 108.84 | 0 |
| MC carbon p5 (kt) | 23,864 | 23,864 | 0 |
| MC carbon p50 (kt) | 32,434 | 32,434 | 0 |
| MC carbon p95 (kt) | 42,436 | 42,436 | 0 |
| Central run percentile in MC, floor area | 26.5 | 26.5 | 0 |
| Central run percentile in MC, carbon | 27.1 | 27.1 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## 2026 gap decomposition (A1 evidence) and baseline walk

gap_2026.py (run by run_all.py) decomposes observed-implied 2026 completions against the model's 2026 requirement into S2 regime, population (actual vs projected growth, year ended June 2026, from the saved Stats NZ release, provisional), pipeline from 2025 and residual, and reports where the 2018-23 excess building went (census counts). tools/baseline_walk.py generates outputs/baseline_walk.md from the committed metrics at each step. Evidence only: no model change.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 75.01 | 75.01 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,049 | 29,049 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,377 | 21,377 | 0 |
| 2025 -> 2026 step in built floor area (%) | -19.5 | -19.5 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.29 | 4.29 | 0 |
| MC floor area p5 (Mm2) | 61.70 | 61.70 | 0 |
| MC floor area p50 (Mm2) | 83.97 | 83.97 | 0 |
| MC floor area p95 (Mm2) | 108.84 | 108.84 | 0 |
| MC carbon p5 (kt) | 23,864 | 23,864 | 0 |
| MC carbon p50 (kt) | 32,434 | 32,434 | 0 |
| MC carbon p95 (kt) | 42,436 | 42,436 | 0 |
| Central run percentile in MC, floor area | 26.5 | 26.5 | 0 |
| Central run percentile in MC, carbon | 27.1 | 27.1 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## A1 and item-2 machinery behind flags; defaults unchanged

New flags, all set to reproduce the previous run exactly (every headline metric below is unchanged): REPLACEMENT_SCENARIO ('S1' default; 'S2' = the 2018-2023 census-interval rate persists; 'S3' = it fades to the long-run rate with half-life S3_HALF_LIFE; engine.replacement_path), NEAR_TERM_JOIN ('carried_deviation' default = the original; 'nowcast' = A1(a)+(c); 'none'), NOWCAST_METHOD, NOWCAST_POPULATION (False), EXCESS_CHANNELS, VACANCY_DRAWDOWN_YEARS, HOUSEHOLD_CHANNEL, CHANNEL_POP_DATE. New pure engine functions: seasonal_shares, nowcast_year, excess_channels, join_channels, nowcast_join, requirement; engine.forward takes an optional join (and its redevelopment part) and reports the join-adjusted stock. New population-nowcast input built by script from the raw Stats NZ release (data/build_population_nowcast.py; interim, provisional). validation.py and gap_2026.py now run the 2026 check and gap decomposition on the model WITHOUT observed-2026 inputs (validation.NO_2026_DATA). Sensitivity.py: the S2 row now uses REPLACEMENT_SCENARIO='S2' (identical result to the former window row, 91.54 Mm2); new rows for S3 half-lives and for every A1 setting (they show no change while the join is off). MonteCarlo: scenario path and per-draw join (interim treatment of the regime weight until item 9). Tests: tests/test_near_term_join.py (identities of the nowcast join, channel conservation, nowcast estimators on synthetic seasonality, scenario paths); legacy flags extended; equivalence tests pass.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 75.01 | 75.01 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,049 | 29,049 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,377 | 21,377 | 0 |
| 2025 -> 2026 step in built floor area (%) | -19.5 | -19.5 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.29 | 4.29 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | n/a | n/a |  |
| Near-term join: 2027 lagged-share excess (dwellings) | n/a | n/a |  |
| Near-term join: net dwellings added 2026-2050 | n/a | n/a |  |
| MC floor area p5 (Mm2) | 61.70 | 61.70 | 0 |
| MC floor area p50 (Mm2) | 83.97 | 83.97 | 0 |
| MC floor area p95 (Mm2) | 108.84 | 108.84 | 0 |
| MC carbon p5 (kt) | 23,864 | 23,864 | 0 |
| MC carbon p50 (kt) | 32,434 | 32,434 | 0 |
| MC carbon p95 (kt) | 42,436 | 42,436 | 0 |
| Central run percentile in MC, floor area | 26.5 | 26.5 | 0 |
| Central run percentile in MC, carbon | 27.1 | 27.1 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: as run (no 2026 data used)), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Correct the 2018-2023 boom decomposition in gap_2026 (evidence only)

gap_2026.boom_2018_2023 subtracted the change in dwellings under construction from completions that are already lagged W behind consents, which counts the pipeline twice. Net removals 2018-2023 = completions - change in census private dwellings = 34,805 (was reported as 23,609 plus 11,196 more under construction). Evidence report only: no model code changed, so only gap_2026.py was re-run; the model metrics below are those of the previous full run and are unchanged. The census-interval net replacement rate never included that subtraction. docs/CP2_NOTE.md point 4 corrected.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 75.01 | 75.01 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,049 | 29,049 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,377 | 21,377 | 0 |
| 2025 -> 2026 step in built floor area (%) | -19.5 | -19.5 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.29 | 4.29 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | n/a | n/a |  |
| Near-term join: 2027 lagged-share excess (dwellings) | n/a | n/a |  |
| Near-term join: net dwellings added 2026-2050 | n/a | n/a |  |
| MC floor area p5 (Mm2) | 61.70 | 61.70 | 0 |
| MC floor area p50 (Mm2) | 83.97 | 83.97 | 0 |
| MC floor area p95 (Mm2) | 108.84 | 108.84 | 0 |
| MC carbon p5 (kt) | 23,864 | 23,864 | 0 |
| MC carbon p50 (kt) | 32,434 | 32,434 | 0 |
| MC carbon p95 (kt) | 42,436 | 42,436 | 0 |
| Central run percentile in MC, floor area | 26.5 | 26.5 | 0 |
| Central run percentile in MC, carbon | 27.1 | 27.1 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: as run (no 2026 data used)), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## A1(a), part 1: observed 2026 population growth (NOWCAST_POPULATION = True)

The 2026 population growth is the OBSERVED growth over the year ended June 2026 (Stats NZ, National population estimates at 30 June 2026, provisional: +36,400) instead of the 2024-base projection median for that year (+51,000). Later years keep the projection's growth, so every percentile path's level is shifted by -14,600 from 2026 on. The model's existing convention applies year-ended-June growth to calendar years (half-year offset); the nowcast inherits it. Input built by script from the raw release page (interim; the quarterly ERP from Infoshare DPE is to replace it). The whole shortfall lands on 2026, which deepens the 2025->2026 step; the consent nowcast (next commit) replaces 2026 building with observed data. The 2026 validation check runs on the model without observed-2026 inputs and is unchanged. Sensitivity row: 'Projected 2026 growth (no population nowcast)'.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 75.01 | 74.24 | -0.776 (-1.03%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,049 | 28,751 | -298 (-1.03%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,377 | 21,160 | -217 (-1.02%) |
| 2025 -> 2026 step in built floor area (%) | -19.5 | -36.2 | -16.7 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.29 | 4.25 | -0.0418 (-0.98%) |
| Near-term join: 2026 completions above requirement (dwellings) | n/a | n/a |  |
| Near-term join: 2027 lagged-share excess (dwellings) | n/a | n/a |  |
| Near-term join: net dwellings added 2026-2050 | n/a | n/a |  |
| MC floor area p5 (Mm2) | 61.70 | 60.95 | -0.75 (-1.21%) |
| MC floor area p50 (Mm2) | 83.97 | 83.17 | -0.801 (-0.95%) |
| MC floor area p95 (Mm2) | 108.84 | 107.98 | -0.862 (-0.79%) |
| MC carbon p5 (kt) | 23,864 | 23,578 | -286 (-1.20%) |
| MC carbon p50 (kt) | 32,434 | 32,131 | -303 (-0.94%) |
| MC carbon p95 (kt) | 42,436 | 42,112 | -324 (-0.76%) |
| Central run percentile in MC, floor area | 26.5 | 26.6 | +0.04 |
| Central run percentile in MC, carbon | 27.1 | 27.2 | +0.01 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## A1(a)+(c), part 2: nowcast 2026-27 from observed consents; excess split into three channels (NEAR_TERM_JOIN = 'nowcast')

2026 completions (all categories) are taken from observed consents, c x [(1 - W) C2026 + W C2025]. C2026 = January-July 2026 observed + August-December estimated by a ratio-to-annual estimator with fixed seasonal factors (mean monthly share of the calendar year over 2010-2025; engine.nowcast_year). Alternatives are sensitivities: same-period ratio on 2025, and the latest 12 months. The W share of 2027 completions comes from the 2026 consents; 2027 consents are taken at the requirement net of the 2026 drawdown. The building above the model's requirement (2026 and the 2027 lagged share) is split into three channels measured on ONE census interval (2018-2023) against the active replacement scenario (engine.excess_channels): redevelopment (permanent), vacancy (drawn down linearly over 5 years; 3 and 10 are sensitivities) and faster household formation. The household channel is included because census household size (ERP at census night / occupied + away) fell faster than the Stats NZ shape over 2018-2023. It is permanent by JUDGEMENT; reverting is a sensitivity. The 2025 deviation is no longer carried (the observed pipeline replaces it); 'carried_deviation' and 'none' are sensitivities. The extra stock from the vacancy and household channels does not enter the demolition base (second order: a few dwellings a year). The 2026 validation check and the gap decomposition still run on the model without observed-2026 inputs. New band 'Near-term join' in the demand-type tables and figures; identity tests extended to the join-adjusted stock.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 74.24 | 76.00 | +1.76 (+2.38%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 28,751 | 29,427 | +676 (+2.35%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,160 | 21,650 | +491 (+2.32%) |
| 2025 -> 2026 step in built floor area (%) | -36.2 | +9.0 | +45.2 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.25 | 4.34 | +0.0933 (+2.20%) |
| Near-term join: 2026 completions above requirement (dwellings) | n/a | +19,007 |  |
| Near-term join: 2027 lagged-share excess (dwellings) | n/a | +7,939 |  |
| Near-term join: net dwellings added 2026-2050 | n/a | +24,016 |  |
| MC floor area p5 (Mm2) | 60.95 | 64.18 | +3.23 (+5.30%) |
| MC floor area p50 (Mm2) | 83.17 | 85.31 | +2.14 (+2.57%) |
| MC floor area p95 (Mm2) | 107.98 | 109.03 | +1.05 (+0.97%) |
| MC carbon p5 (kt) | 23,578 | 24,729 | +1.15e+03 (+4.88%) |
| MC carbon p50 (kt) | 32,131 | 32,958 | +827 (+2.57%) |
| MC carbon p95 (kt) | 42,112 | 42,533 | +421 (+1.00%) |
| Central run percentile in MC, floor area | 26.6 | 24.4 | -2.16 |
| Central run percentile in MC, carbon | 27.2 | 25.1 | -2.02 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Reporting only: A1 evidence file, item-2 scenario comparison, CP2b note

New generated outputs, no model change (metrics identical): outputs/near_term_join.md (nowcast methods, household-size test and channel levels under both population dates, the join by channel) from tools/near_term_join.py; outputs/replacement_scenarios.md (S1, S3 half-lives 5/10/15, S2: totals, implied removals, comparison with the 2026 excess, reported and not fitted, and the census record) from tools/replacement_scenarios.py. Both run in run_all.py. Baseline walk extended to the A1 commits. docs/CP2B_NOTE.md asks for the scenario decision.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.00 | 76.00 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,427 | 29,427 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,650 | 21,650 | 0 |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.34 | 4.34 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | +19,007 | +19,007 | 0 |
| Near-term join: 2027 lagged-share excess (dwellings) | +7,939 | +7,939 | 0 |
| Near-term join: net dwellings added 2026-2050 | +24,016 | +24,016 | 0 |
| MC floor area p5 (Mm2) | 64.18 | 64.18 | 0 |
| MC floor area p50 (Mm2) | 85.31 | 85.31 | 0 |
| MC floor area p95 (Mm2) | 109.03 | 109.03 | 0 |
| MC carbon p5 (kt) | 24,729 | 24,729 | 0 |
| MC carbon p50 (kt) | 32,958 | 32,958 | 0 |
| MC carbon p95 (kt) | 42,533 | 42,533 | 0 |
| Central run percentile in MC, floor area | 24.4 | 24.4 | 0 |
| Central run percentile in MC, carbon | 25.1 | 25.1 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 21,618 | 0 |
| 2026 observed / model consents, year to date | 1.971 | 1.971 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Item 2 decision: S3 (half-life 10 yr) is the reference path; S1 and S2 are the bounds

REPLACEMENT_SCENARIO = 'S3', S3_HALF_LIFE = 10 (author's decision after docs/CP2B_NOTE.md). S1 (long-run rate) and S2 (2018-2023 rate persists) are reported as lower and upper bounds, and half-lives 5 and 15 alongside (outputs/replacement_scenarios.md, Sensitivity.py). The half-life is JUDGEMENT; it is not identifiable from the census record. The household-identity sensitivity rows have no census-interval rate and are run as S1 (labelled). The 2026 out-of-sample check runs on the reference model without observed-2026 inputs, so its ratio changes with the scenario; gap_2026 remains stated on S1 and S2. The MC still uses the interim regime weight (item 9 pending); its interval is not quoted.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 76.00 | 83.01 | +7.01 (+9.22%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 29,427 | 32,142 | +2.71e+03 (+9.23%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 21,650 | 23,648 | +2e+03 (+9.23%) |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.34 | 4.74 | +0.401 (+9.24%) |
| Near-term join: 2026 completions above requirement (dwellings) | +19,007 | +14,147 | -4.86e+03 (-25.57%) |
| Near-term join: 2027 lagged-share excess (dwellings) | +7,939 | +5,679 | -2.26e+03 (-28.46%) |
| Near-term join: net dwellings added 2026-2050 | +24,016 | +16,149 | -7.87e+03 (-32.76%) |
| MC floor area p5 (Mm2) | 64.18 | 68.14 | +3.96 (+6.17%) |
| MC floor area p50 (Mm2) | 85.31 | 88.68 | +3.37 (+3.95%) |
| MC floor area p95 (Mm2) | 109.03 | 111.81 | +2.78 (+2.55%) |
| MC carbon p5 (kt) | 24,729 | 26,282 | +1.55e+03 (+6.28%) |
| MC carbon p50 (kt) | 32,958 | 34,309 | +1.35e+03 (+4.10%) |
| MC carbon p95 (kt) | 42,533 | 43,630 | +1.1e+03 (+2.58%) |
| Central run percentile in MC, floor area | 24.4 | 33.5 | +9.11 |
| Central run percentile in MC, carbon | 25.1 | 34.3 | +9.17 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 21,618 | 24,446 | +2.83e+03 (+13.08%) |
| 2026 observed / model consents, year to date | 1.971 | 1.743 | -0.228 (-11.57%) |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Item 1: quarterly ERP (Infoshare DPE059AA) for the 2026 population nowcast and the household test

Built by script from the raw Infoshare export (data/build_population_quarterly.py; moved to data/raw/, MANIFEST entry). The series is MEAN-QUARTER ERP (the average over the quarter), not point estimates at quarter end. 2026 growth = June quarter 2026 minus June quarter 2025 = 35,400 (the provisional 30 June release, 36,400, is now a sensitivity). Population convention stated in Boss.py and the README: history = 31 December ERP; projection growth = years ended June applied to calendar years; nowcast = the latest four-quarter change, applied the same way. Household test: population = March-quarter value (author's decision; it is the January-March mean, not a 31 March point value, which the export does not contain); census-night interpolation between quarter centres and mid-year are sensitivities. New catch-up sensitivity: the 2026 shortfall made up linearly over 5 years instead of a permanent level shift (POP_NOWCAST_CATCHUP_YEARS). Test added: the shift equals observed minus projected growth and the catch-up level rejoins the projection.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 83.01 | 83.01 | -0.00158 (-0.00%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 32,142 | 32,141 | -0.612 (-0.00%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 23,648 | 23,648 | -0.451 (-0.00%) |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.74 | 4.74 | -9.1e-05 (-0.00%) |
| Near-term join: 2026 completions above requirement (dwellings) | +14,147 | +14,542 | +395 (+2.79%) |
| Near-term join: 2027 lagged-share excess (dwellings) | +5,679 | +5,681 | +2.18 (+0.04%) |
| Near-term join: net dwellings added 2026-2050 | +16,149 | +16,555 | +407 (+2.52%) |
| MC floor area p5 (Mm2) | 68.14 | 68.15 | +0.00134 (+0.00%) |
| MC floor area p50 (Mm2) | 88.68 | 88.67 | -0.00189 (-0.00%) |
| MC floor area p95 (Mm2) | 111.81 | 111.80 | -0.0101 (-0.01%) |
| MC carbon p5 (kt) | 26,282 | 26,282 | +0.484 (+0.00%) |
| MC carbon p50 (kt) | 34,309 | 34,307 | -1.61 (-0.00%) |
| MC carbon p95 (kt) | 43,630 | 43,626 | -4.04 (-0.01%) |
| Central run percentile in MC, floor area | 33.5 | 33.5 | 0 |
| Central run percentile in MC, carbon | 34.3 | 34.3 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 24,446 | 24,446 | 0 |
| 2026 observed / model consents, year to date | 1.743 | 1.743 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Item 2 (CP3 order): household channel reverts by default at the estimated household-size persistence

HOUSEHOLD_CHANNEL = 'reverting' (author's decision). The extra households from the 2026-27 excess dissolve geometrically: a share rho remains after each year, with rho = the model's estimated persistence of household-size deviations (lag-1 autocorrelation of the residuals of the regression of the annual change in S on population growth, 1992-2023). Caveat stated in Boss.py: rho is estimated on CHANGES in household size; its use as the reversion rate of a LEVEL deviation is an assumption, not an estimate. Sensitivities: 'permanent' (the previous default) and 'reverting_linear' (over the vacancy drawdown horizon). Under the reference scenario the redevelopment share is zero, so the join is now almost entirely timing: net dwellings added 2026-2050 are close to zero. The MC uses the same rho (the sampled one when the household-size response is on). Tests: geometric reversion identity.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 83.01 | 80.94 | -2.07 (-2.49%) |
| Embodied carbon 2026-2050, central run (kt CO2e) | 32,141 | 31,342 | -799 (-2.49%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 23,648 | 23,062 | -586 (-2.48%) |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.74 | 4.62 | -0.116 (-2.44%) |
| Near-term join: 2026 completions above requirement (dwellings) | +14,542 | +14,542 | 0 |
| Near-term join: 2027 lagged-share excess (dwellings) | +5,681 | +7,639 | +1.96e+03 (+34.45%) |
| Near-term join: net dwellings added 2026-2050 | +16,555 | +2 | -1.66e+04 (-99.99%) |
| MC floor area p5 (Mm2) | 68.15 | 65.23 | -2.91 (-4.27%) |
| MC floor area p50 (Mm2) | 88.67 | 86.79 | -1.89 (-2.13%) |
| MC floor area p95 (Mm2) | 111.80 | 111.08 | -0.721 (-0.64%) |
| MC carbon p5 (kt) | 26,282 | 25,197 | -1.08e+03 (-4.13%) |
| MC carbon p50 (kt) | 34,307 | 33,552 | -755 (-2.20%) |
| MC carbon p95 (kt) | 43,626 | 43,307 | -319 (-0.73%) |
| Central run percentile in MC, floor area | 33.5 | 33.8 | +0.3 |
| Central run percentile in MC, carbon | 34.3 | 34.5 | +0.21 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 24,446 | 24,446 | 0 |
| 2026 observed / model consents, year to date | 1.743 | 1.743 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Item 8: no soil loss on net-replacement floor area; greenfield share and soil-order weights as marked placeholders

Soil organic carbon loss is land-use change, so it arises only on land converted to settlement (IPCC 2006 Guidelines, Vol. 4, ch. 8, Settlements). SOIL_ON_REPLACEMENT = False: soil is zero on the in-scope net-replacement floor area (demolition replacement + calibrated residual + the redevelopment channel of the near-term join, after the RV share). engine.forward separates the soil part of the intensities and applies it to the soil-bearing share of each year's floor area. Every report (demand bands, material flows, stages, upfront, Sensitivity carbon-factor rows, MC) uses the same share, and the identity tests confirm the bands and flows add up. GREENFIELD_SHARE g = 1.0 is a marked PLACEHOLDER: it keeps the original treatment of the remaining floor area, and no evidence-based value exists yet (E5). g = 0.5 and 0 are shown only as bracketing. Development-weighted soil-order shares: a hook reads data/placeholders/soil_order_shares_development.csv (expected columns, no values; E6). While it is empty the national area-weighted case-study factor is used. Original treatment kept as a sensitivity and in the legacy flags. Test: tests/test_soil.py.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 80.94 | 80.94 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 31,342 | 30,729 | -613 (-1.96%) |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 23,062 | 22,448 | -613 (-2.66%) |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.62 | 4.62 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | +14,542 | +14,542 | 0 |
| Near-term join: 2027 lagged-share excess (dwellings) | +7,639 | +7,639 | 0 |
| Near-term join: net dwellings added 2026-2050 | +2 | +2 | 0 |
| MC floor area p5 (Mm2) | 65.23 | 65.23 | 0 |
| MC floor area p50 (Mm2) | 86.79 | 86.79 | 0 |
| MC floor area p95 (Mm2) | 111.08 | 111.08 | 0 |
| MC carbon p5 (kt) | 25,197 | 24,556 | -642 (-2.55%) |
| MC carbon p50 (kt) | 33,552 | 32,813 | -739 (-2.20%) |
| MC carbon p95 (kt) | 43,307 | 42,520 | -787 (-1.82%) |
| Central run percentile in MC, floor area | 33.8 | 33.8 | 0 |
| Central run percentile in MC, carbon | 34.5 | 35.0 | +0.54 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 24,446 | 24,446 | 0 |
| 2026 observed / model consents, year to date | 1.743 | 1.743 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Item 9: Monte Carlo within each net-replacement scenario (S3-10 reference, S1, S2); inputs centred on the deterministic values

Net replacement is no longer sampled: the Uniform(0, 1) regime weight is removed. The MC is run separately within S3 (half-life 10, fixed, not sampled; the reference, whose files keep the plain names and carry the Sobol indices and figures), S1 and S2 (montecarlo_*_<scenario>.csv). All scenarios use the same seed (common random numbers). Centring (D3): the deterministic run uses the median of every sampled input. The completion rate (0.92-0.96 around 0.95), the household rebase factor and the RV share had asymmetric ranges about Boss's value, so they now use two-piece (split) distributions with their median at that value (two-piece family, Wallis 2014): uniform halves for the completion rate, triangular halves for the other two. Vacancy is on the 2018/2023 empty definition only (N1), symmetric about 2023 with half-width equal to the 2018-2023 difference (JUDGEMENT width). phi keeps its symmetric triangle about 0.80 (JUDGEMENT); what it means is reported as a new output, the 2050 townhouse share. Summaries report the mean and the median with the 90% interval, plus the percentile of the deterministic run. The legacy equivalence test still covers the old regime path (drawn in the test).

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 80.94 | 80.94 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 30,729 | 30,729 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 22,448 | 22,448 | 0 |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.62 | 4.62 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | +14,542 | +14,542 | 0 |
| Near-term join: 2027 lagged-share excess (dwellings) | +7,639 | +7,639 | 0 |
| Near-term join: net dwellings added 2026-2050 | +2 | +2 | 0 |
| MC floor area p5 (Mm2) | 65.23 | 59.47 | -5.76 (-8.83%) |
| MC floor area p50 (Mm2) | 86.79 | 79.74 | -7.05 (-8.12%) |
| MC floor area mean (Mm2) | n/a | 80.28 |  |
| MC floor area p95 (Mm2) | 111.08 | 102.86 | -8.22 (-7.40%) |
| MC carbon p5 (kt) | 24,556 | 22,414 | -2.14e+03 (-8.72%) |
| MC carbon p50 (kt) | 32,813 | 30,294 | -2.52e+03 (-7.68%) |
| MC carbon mean (kt) | n/a | 30,498 |  |
| MC carbon p95 (kt) | 42,520 | 39,392 | -3.13e+03 (-7.36%) |
| Central run percentile in MC, floor area | 33.8 | 53.7 | +19.9 |
| Central run percentile in MC, carbon | 35.0 | 53.6 | +18.5 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 24,446 | 24,446 | 0 |
| 2026 observed / model consents, year to date | 1.743 | 1.743 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Baseline v1.0: soil final, carbon-factor sources, hygiene, generated ASSUMPTIONS.md and RESULTS.md

The headline numbers are unchanged from CP3; this full run is the single run for v1.0. Soil: zero on the replacement bands, applied to all other floor area; the greenfield-share and soil-order placeholders are deleted; the 58.77 kg CO2e/m2 footprint factor (area-weighted over the 10 soil orders of Auckland land zoned for urbanisation to about 2050) is cited to Christoforatos, Pickering & Schipper 2026 (J. Environ. Manage. 415, 130603). Carbon is now reported with and without soil. Case-study source and benchmarking cited to Christoforatos & Pickering 2025 (SASBE). Building_factors: the non-running reconciliation block and its docstring claim, the gfa_weighted option and the pooling switch are deleted, with factor outputs byte-identical; the apartment single-case flag is kept. Stale comments and dead labels removed. ASSUMPTIONS.md (from the settings) and outputs/RESULTS.md (from metrics) are generated by run_all. BASELINE_DRAFT: the 2026 gap as a finding, the soil method and sources, and the updated limitations.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 80.94 | 80.94 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 30,729 | 30,729 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 22,448 | 22,448 | 0 |
| Soil carbon (land-use change), central run (kt CO2e) | n/a | 2,452 |  |
| Embodied carbon excluding soil, central run (kt CO2e) | n/a | 28,277 |  |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.62 | 4.62 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | +14,542 | +14,542 | 0 |
| Near-term join: 2027 lagged-share excess (dwellings) | +7,639 | +7,639 | 0 |
| Near-term join: net dwellings added 2026-2050 | +2 | +2 | 0 |
| MC floor area p5 (Mm2) | 59.47 | 59.47 | 0 |
| MC floor area p50 (Mm2) | 79.74 | 79.74 | 0 |
| MC floor area mean (Mm2) | 80.28 | 80.28 | 0 |
| MC floor area p95 (Mm2) | 102.86 | 102.86 | 0 |
| MC carbon p5 (kt) | 22,414 | 22,414 | 0 |
| MC carbon p50 (kt) | 30,294 | 30,294 | 0 |
| MC carbon mean (kt) | 30,498 | 30,498 | 0 |
| MC carbon p95 (kt) | 39,392 | 39,392 | 0 |
| Central run percentile in MC, floor area | 53.7 | 53.7 | 0 |
| Central run percentile in MC, carbon | 53.6 | 53.6 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| 2026 model consent-equivalents (all categories) | 24,446 | 24,446 | 0 |
| 2026 observed / model consents, year to date | 1.743 | 1.743 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.

## Baseline v1.0.1

Headline numbers unchanged. The calibrated residual band is split into the long-run residual and the redevelopment wave (scenario minus long-run net replacement, no soil); the split is carried through bands, carbon, figures and the draft. Draft: sentence on why the joint MC interval is narrower than the population-only range (z coupling to the Low/High household-size variants); upfront carbon stated as the quantity comparable with a 2026-2050 budget; 2026 finding and decomposition on the reference path S3-10, with S1 as a footnote; limitations add N4 and the transfer of the Auckland soil factor nationally; phi basis 'JUDGEMENT: ≈4 years of trend applied by 2050'; completion-rate citation marked 'to verify'; the rho = 0.9 deviation case relabelled as rejected (DHE artefact). Gap decomposition adds S3-10 and uses the adopted DPE population series (35,400). Hindcast adds the reference method (latest intercensal rate fading to the long-run rate, 10-year half-life) at origins 2006, 2013 and 2018.

| metric | before | after | change |
|---|---|---|---|
| Built floor area 2026-2050, central run (Mm2) | 80.94 | 80.94 | 0 |
| Embodied carbon 2026-2050, central run (kt CO2e) | 30,729 | 30,729 | 0 |
| Upfront carbon A1-A5 + soil, central run (kt CO2e) | 22,448 | 22,448 | 0 |
| Soil carbon (land-use change), central run (kt CO2e) | 2,452 | 2,452 | 0 |
| Embodied carbon excluding soil, central run (kt CO2e) | 28,277 | 28,277 | 0 |
| 2025 -> 2026 step in built floor area (%) | +9.0 | +9.0 | 0 |
| Household size 2050, central run | 2.652 | 2.652 | 0 |
| Retirement-village floor area 2026-2050, out of scope (Mm2) | 4.62 | 4.62 | 0 |
| Near-term join: 2026 completions above requirement (dwellings) | +14,542 | +14,542 | 0 |
| Near-term join: 2027 lagged-share excess (dwellings) | +7,639 | +7,639 | 0 |
| Near-term join: net dwellings added 2026-2050 | +2 | +2 | 0 |
| MC floor area p5 (Mm2) | 59.47 | 59.47 | 0 |
| MC floor area p50 (Mm2) | 79.74 | 79.74 | 0 |
| MC floor area mean (Mm2) | 80.28 | 80.28 | 0 |
| MC floor area p95 (Mm2) | 102.86 | 102.86 | 0 |
| MC carbon p5 (kt) | 22,414 | 22,414 | 0 |
| MC carbon p50 (kt) | 30,294 | 30,294 | 0 |
| MC carbon mean (kt) | 30,498 | 30,498 | 0 |
| MC carbon p95 (kt) | 39,392 | 39,392 | 0 |
| Central run percentile in MC, floor area | 53.7 | 53.7 | 0 |
| Central run percentile in MC, carbon | 53.6 | 53.6 | 0 |
| Hindcast error, origin 2006, model method (%) | -15.9 | -15.9 | 0 |
| Hindcast error, origin 2013, model method (%) | -18.4 | -18.4 | 0 |
| Hindcast error, origin 2018, model method (%) | -13.5 | -13.5 | 0 |
| Hindcast error, origin 2006, reference S3-10 (%) | n/a | -14.7 |  |
| Hindcast error, origin 2013, reference S3-10 (%) | n/a | -16.1 |  |
| Hindcast error, origin 2018, reference S3-10 (%) | n/a | -9.3 |  |
| 2026 model consent-equivalents (all categories) | 24,446 | 24,446 | 0 |
| 2026 observed / model consents, year to date | 1.743 | 1.743 | 0 |

Validation (outputs/validation.md):

Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2006 | 2007-2023 | reference_s3_10 | +0.027 | 388,023 | 455,109 | -14.7% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2013 | 2014-2023 | reference_s3_10 | +0.087 | 279,702 | 333,208 | -16.1% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |
| 2018 | 2019-2023 | reference_s3_10 | +0.163 | 181,556 | 200,146 | -9.3% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 13,720 (annual 24,446 x seasonal share 0.561); observed / model = 1.743. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.
