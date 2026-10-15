# MODEL v3.3.0: changes and decisions

Branch `release/model-v3.3.0`, created from `release/model-v3.2.0` (b5a8c62). Three changes: the levers regrouped by
the carbon reduction hierarchy of PAS 2080:2023 (BSI 2023) with strategy runs S1-S3 replacing the families P1-P4; a
Very High replacement variant; the replacement half-life sampled in the Monte Carlo. Figures Fig5, Fig6, Fig8 and D07
are revised. Numbers are full profile unless stated; deterministic numbers are identical in both profiles (checked by
`tests/capture_regression_model_v3.py`).

## Summary

* **Equality with v3.2**: under the v3.2 -> v3.3 map of run ids, the Reference, every lever run, the Moderate and
  Ambitious Pathway (v3.2 P5), the adoption-timing variants, the LOW / HIGH variants and TL (45 runs; floor area,
  carbon, LoE AR, LoE AtP, B_AR, B_AtP) equal the v3.2 outputs. The worst relative difference is 0 (bit-identical),
  against the 1e-9 condition (`tests/test_model_v3_3.py`; fixture `tests/fixtures/v3_2_totals.json` from b5a8c62). The
  P1-P4 runs (8 runs) have no v3.3 counterpart.
* **STOP conditions**: none triggered. Shapley efficiency holds to 1e-9 in every game (strategy, lever, TL), the bands
  add up to the totals in every run and year (1e-9), and the waterfall steps add up to their totals.
* **Monte Carlo**: adding the half-life as an LHS dimension changes every draw. The Reference Monte Carlo (REF, LOW,
  HIGH, VHIGH), the AESA draws, Sobol and the pathway Monte Carlo were re-run, once, in the full profile.

## 1. PAS 2080 strategies (Avoid - Switch - Improve)

**Classification rule (Methods).** PAS 2080:2023 Clause 4.3 orders interventions by their potential to reduce whole
life carbon:

* **Avoid**: the need for new floor area is removed. These levers change how much is built.
* **Switch**: the same floor area is delivered with a lower-carbon solution: a different site, soil or material
  choice.
* **Improve**: the delivery of the chosen solution is made more efficient. This covers construction-stage processes.

Each lever is assigned by the quantity it changes in the engine (`levers.py` docstring, `tools/pathways_methods.py`).
Lever settings (Moderate / Ambitious / TL values, sub-rules, anchors) are unchanged.

| v3.0-v3.2 | v3.3.0 | strategy |
|---|---|---|
| L3 Household size | L1 | S1 Avoid |
| L4 Vacancy rate | L2 | S1 Avoid |
| L5 Building lifetime | L3 | S1 Avoid |
| L1 Extra space | L4 | S1 Avoid |
| L2 Occupancy density | L5 | S1 Avoid |
| L9 Brownfield-first development | L6 | S2 Switch |
| L8 Soil-aware planning | L7 | S2 Switch |
| L6 Material carbon efficiency | L8 | S2 Switch |
| L7 Construction-stage carbon | L9 | S3 Improve |

TLn follows Ln (same TL values). The complete map, including runs, games, MC keys, columns and file names, is in
`docs/RENAMING.md` §12, generated from `naming.py` by `tools/renaming_v3_3.py`.

**How the renumbering was implemented.** A token permutation (old -> new, `naming.LEVER_V3_2`) was applied to the
active code; `levers.inputs` applies the levers in the same computation order as before, which is why every total is
bit-identical. Run ids:

* `S1-moderate` ... `S3-ambitious` are new;
* `pathway-moderate` / `pathway-ambitious` (v3.2 `P5-*`);
* `pathway-<setting>-by2030` / `-by2045`;
* `TL` (unchanged).

Games: `strategies_moderate` / `strategies_ambitious` (8 subsets each), `levers_*` (renumbered players) and
`tl_from_moderate_pathway`.

**Colours.** The strategy colours reuse existing palette entries, with no new palette work:

* S1 = the L4 (extra space) colour;
* S2 = the L7 (soil) colour;
* S3 = the L8 (materials) colour;
* the Pathway = `#EB6123`.

| run | carbon 2026-2050 (kt) | vs Reference | LoE AR |
|---|---|---|---|
| S1 Avoid, Moderate | 16,875.0 | -18.14% | 3.791 |
| S2 Switch, Moderate | 19,036.0 | -7.66% | 4.277 |
| S3 Improve, Moderate | 19,974.4 | -3.11% | 4.488 |
| S1 Avoid, Ambitious | 13,650.9 | -33.78% | 3.067 |
| S2 Switch, Ambitious | 17,540.4 | -14.91% | 3.941 |
| S3 Improve, Ambitious | 19,333.9 | -6.21% | 4.344 |
| Moderate Pathway | 15,073.4 | -26.88% | 3.386 |
| Ambitious Pathway | 10,920.4 | -47.03% | 2.453 |
| Theoretical Limit | 4,357.7 | -78.86% | 0.979 |

Strategy Shapley values (carbon reduction from the Reference, kt; share):

| strategy | Moderate | Ambitious |
|---|---|---|
| S1 Avoid | 3,531.0 (63.7%) | 6,151.5 (63.5%) |
| S2 Switch | 1,435.4 (25.9%) | 2,505.0 (25.8%) |
| S3 Improve | 575.1 (10.4%) | 1,037.9 (10.7%) |

**Sequential waterfalls** (Fig5 a/b, ED7). The waterfalls run in PAS 2080 order:

* (a) Reference -> L1 ... L9 (= Pathway);
* (b) Moderate Pathway -> TL1 ... TL9 (= TL).

Totals are unchanged, but the order differs from v3.2, so individual step values differ. Diagnostics are in
`pathways/sequential_vs_shapley.csv`. The sequential step minus the Shapley value, and the levers where it is most
negative and most positive:

| setting | steps compared | max abs gap (kt) | most negative | most positive |
|---|---|---|---|---|
| Moderate | levers L1-L9 | 94.3 | L8 (-94.3) | L1 (+87.4) |
| Ambitious | levers L1-L9 | 339.3 | L8 (-339.3) | L1 (+312.6) |
| Moderate | TL steps from the Pathway | 892.0 | TL8 (-626.4) | TL1 (+892.0) |

In every case the gaps sum to 0 within 3e-13 kt. Early demand-side steps take more in a sequence than their
order-free share, and later intensity steps take less. The Ambitious TL steps start from the Ambitious Pathway, which
has no Shapley game, so their Shapley column is empty.

**Fig8** is grouped and coloured by strategy.

**Fig6**:

* markers for S1-S3 (Moderate filled, Ambitious hollow), the two Pathways and TL;
* the exact AR curve, and the exact AtP curve (dark-red dotted, deep-green fill beyond it);
* the y-axis extended to the smallest multiple of 10% that shows the AtP curve, which is 110% here;
* above 100% a hatched region labelled "net-negative carbon per m² (carbon-storing construction)".

The AtP curve is y(x) = 1 - k/(1 - x), with k = (B_AtP - C_2026) / C_ref,2027-2050. Because C_2026 = 1,420.8 kt
exceeds B_AtP = 1,113.0 kt, the curve lies above y = 100% for every x (101.6% at x = 0). Annotation: "2026 (observed)
alone emits 1,421 kt = 1.28 × the 2026–2050 AtP budget".

## 2. Replacement

**(a) Half-life in the Monte Carlo.**

* Deterministic value: 10 yr, unchanged.
* Monte Carlo: U(5, 15) yr (median 10). It acts in the Reference replacement path only.
* It is included in SRC / PRCC, Sobol, D38 and D40.

**(b) Very High variant (VHIGH)**: "trend continues".

* Method: weighted least squares of the six census-interval net replacement rates 1991-2023 (seven censuses). The
  regressor is the mean of each interval's model years (y0+1 .. y1), and the weight is the interval length.
* Fit: rate = -0.221894 + 1.1097e-4 × year, i.e. 0.294% in 2026 and 0.560% in 2050.
* The fit is stored in `baseline/projection.json` (`replacement_trend`) and recomputed in the tests from the stored
  rates.
* In the Monte Carlo the trend is refitted in each draw from that draw's census rates (completion rate).
* VHIGH runs wherever LOW / HIGH run:
  * deterministic runs;
  * the Monte Carlo band;
  * D07, D10 and D23;
  * the sensitivity tables;
  * the tornado (one-sided row "Replacement: Very High (trend continues; one-sided)", low = central);
  * Methods.

| VHIGH | floor area (Mm²) | carbon (kt) | LoE AR | LoE AtP |
|---|---|---|---|---|
| Reference variant | 104.68 | 24,237.8 | 5.445 | 21.78 |
| Moderate Pathway | 82.93 | 17,579.2 | 3.949 | 15.79 |
| Ambitious Pathway | 64.58 | 12,286.1 | 2.760 | 11.04 |
| TL | 24.69 | 4,437.9 | 0.997 | 3.99 |

VHIGH Monte Carlo (carbon, 5th-95th): 18,548-30,344 kt (median 24,054). For comparison, HIGH: 16,891-28,315 kt; REF:
15,180-26,255 kt.

**(c) Methods text** (`tools/release_methods.py`):

* The half-life is not identifiable from the census record.
* Functional form: the mean excess of net replacement over the long-run rate, 2026-2050, is 0.097 pp with the 10-yr
  half-life and 0.102 pp for a linear path to the long-run rate in 2050. Both are computed from `scenarios.json`. The
  brief quoted 0.105 vs 0.100 pp; those values were not reproduced and the computed ones are reported.
* Why Very High is not adopted:
  * six interval rates (the brief's "7 points" are the seven censuses);
  * one rate is negative (1996-2001);
  * the 2013-2018 census definition break;
  * an unbounded extrapolation of a policy-driven wave.
* An "Auckland Unitary Plan" attribution drafted during development was removed as unsupported.

**D07**: the Reference is extended (dotted) to 2075, with the annotation "asymptote: long-run rate 0.10%; 2050 value
0.138%". The brief gave 0.137%; the computed value 0.100548 + 0.211662 × 0.5^2.5 = 0.1379% is used. The VHIGH line is
added.

## 3. Monte Carlo changes from sampling the half-life (v3.2 -> v3.3; 5,000 pathway draws)

| run | carbon 5th-95th (kt) v3.2 | v3.3 | LoE AR 5th-95th v3.2 | v3.3 |
|---|---|---|---|---|
| Reference | 15,220-26,216 | 15,180-26,255 | 3.557-5.669 | 3.570-5.648 |
| Moderate Pathway | 10,997-19,324 | 10,982-19,343 | 2.578-4.170 | 2.584-4.153 |
| Ambitious Pathway | 7,836-14,182 | 7,818-14,173 | 1.830-3.055 | 1.843-3.049 |
| TL | 2,507-6,504 | 2,483-6,488 | 0.589-1.399 | 0.590-1.388 |

* P(TL within AR) is 0.551 in v3.2 (Wilson 0.537-0.565) and 0.552 in v3.3 (Wilson 0.538-0.566).
* Importance of the half-life (carbon): it ranks 5th of 5 inputs by |SRC| in the Reference (SRC 0.089, PRCC 0.41),
  the Moderate Pathway (SRC 0.085) and TL (SRC 0.016). In the Sobol indices of the Reference it is also 5th of 5:
  S1 0.008 (95% CI 0.001-0.016), ST 0.008.
* The changes in the bands come from the extra dimension (all draws are new), not from a change in the model.

## Tests and lock

* `tests/test_model_v3_3.py` (new):
  * equality with v3.2 under the map;
  * strategy partition;
  * strategy runs present and P runs absent;
  * Shapley efficiency against run totals (strategy, lever, TL games);
  * the two waterfalls and their agreement with `sequential_vs_shapley.csv`;
  * band sums (projection, pathway runs, history) and no rescaling;
  * built >= 0;
  * the zero-year guard;
  * Fig6 markers on the analytic plane, the exact AR / AtP curves (LoE = level, 1e-9) and the y-limit rule;
  * the Very High fit;
  * the half-life range.
* `tests/test_model_v3_2.py` is retired to `tests/retired/` (it uses the v3.0-v3.2 run names); its model-rule tests
  continue in `test_model_v3_3.py`.
* `tests/test_model_v3.py`: MC columns `pathway_*` and the waterfall check (the L9 step equals the Pathway).
* `tests/test_aesa.py`: the AESA Monte Carlo variant set includes VHIGH.
* Lock: `tests/regression_model_v3_3.json`. It covers 31 deterministic files, adding
  `pathways/sequential_vs_shapley.csv` and `sensitivity/pathway_carbon.csv` (formerly `p5_carbon.csv`), plus the
  Monte Carlo hashes for the light and full profiles. The v3.0 and v3.2 locks are kept for the record.
* Figures-only exports: the 103 full-profile data files are byte-identical after `--figures-only`.

The test run happened inside `run_all.py --profile full`: 176 passed, 37 skipped (the lock tests, before the lock was
captured) and 1 failed. The failure was the AESA variant set, an expectation made stale by adding VHIGH, not a model
failure. The suite was run once more after that expectation was fixed and the lock was captured; see the PR.

## Timings (full profile)

| step | time |
|---|---|
| `run_all.py --profile full` (total, including tests 50 s) | 1,814 s |
| Reference Monte Carlo (4 variants) | 247 s |
| boundaries / AESA | 320 s |
| pathway Monte Carlo | 994 s |
| figures | 98 s |
| `--figures-only`, full quality | 93 s |
| `--figures-only`, light | 44 s |

## Reference

BSI (2023) PAS 2080:2023 Carbon management in buildings and infrastructure. British Standards Institution, London
[verify] (`docs/REFERENCES.md`).
