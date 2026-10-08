# PATHWAYS v1: hook inventory

Written before any pathways code (step 1). It records, for each lever, which
`engine.forward()` input (the `fwd_inputs` dict built in `Boss.main()`) or which
piece of Boss state the lever modifies, and how the identity run (every lever
off) is obtained. Line numbers refer to `Boss.py` at tag `baseline-PB_v3.1`
(commit fdc3c77). No model file is edited: pathways obtain the Boss state from
`Boss.main()` (via `validation.run_boss(**settings)`, which returns `locals()`)
and re-call `engine.forward()` with modified *copies* of `fwd_inputs`.

## Boss state read by the pathways layer

| object | where built (Boss.py) | what it is |
|---|---|---|
| `fwd_inputs` | l. 1527-1532 | every `engine.forward` argument that does not depend on the population path: `v`, `rate_demol`, `rate_unc`, `dev_2025`, `rho_dev`, `rv_share`, `shares`, `size`, `olf`, `intensity`, `intensity_upfront`, `soil`, `soil_on_replacement`, `gfa_fixed`, `events` |
| `df_forecast['PopTotal_50th']`, `df_forecast['PopGrowth_50th'].clip(lower=0)`, `households_forecast['50th']` | l. 1539-1542 | the median population and household paths (the levers never change them) |
| `join_info['50th']` (`join`, `redev`, `O26`, `rho`) | l. 1544-1550 | the near-term market excess of the reference run (`engine.market_excess`, mode `surplus`, absorption 0) |
| `v_forward` | l. 1284 | stock-wide vacancy held forward = 2023 census value (5.39%) |
| `demolition_rate`, `unconsented_rate`, `rate_path`, `unc_path` | l. 1275-1292 | BRANZ demolition rate (0.135%/yr); long-run residual = long-run net rate − demolition; scenario net replacement path; `unc_path = rate_path − demolition_rate` |
| `size_ref` | l. 1164-1165 | realised new-dwelling size per typology, mean of annual GFA / dwellings over `DWELLING_SIZE_REF` (2023-2025) |
| `OLF_USED` | l. 1167 | occupancy load factor per typology (case studies) |
| `held_shares`, `evolving_gfa_shares` | l. 1489-1508 | floor-area shares: held at the 2022-2026 consented average from 2027; 2026 row = observed (nowcast) mix |
| `MAT_STAGE`, `RED13_TOT`, `RED45_TOT`, `SOIL_INTENSITY`, `T_INT`, `U_INT` | l. 1333-1356 | stage x material x typology factors (2025); A1-A3 and A4-A5 reduction paths; soil; construction-year intensity |
| `EVENTS`, `EV_PROFILE` | l. 1364-1372 | B2/B4 event kernels per typology and the pooled event profile (committed emissions) |
| `stage_int` | l. 2244-2246 | per-typology stage totals (C1-C4 for committed end of life) |
| `COMMITTED` | l. 2274-2289 | the reference committed range, recomputed per run with `events.committed` |
| band bookkeeping | l. 1555-1575 (floor area), 1700-1745 (carbon), `export_results` l. 2439-2483 | demand bands and their carbon (replicated in `pathways.py`, identity-tested) |

**A1-A3 separability (STOP check).** With `ACCOUNTING = 'time_resolved'`,
`T_INT[t] = U_INT[t] = UPFRONT_2025[t] − RED_TOT[t]`, where
`UPFRONT_2025[t] = Σ_m MAT_STAGE['A1-A3'][m, t] + Σ_m MAT_STAGE['A4-A5'][m, t] + SOIL_INTENSITY[t]`
and `RED_TOT[t] = RED13_TOT[t] + RED45_TOT[t]`. Hence

    T_INT[t](y) = [A13_2025[t] − RED13_TOT[t](y)] + [A45_2025[t] − RED45_TOT[t](y)] + SOIL[t]

and the A1-A3 term `A13_2025[t] − RED13_TOT[t](y)` is separable exactly. Checked on
the reference run: max |T_INT − rebuilt| = 1.1e-13 kg/m² (all typologies), and
`T_INT` is identical to `U_INT`. Pooled 2025 A1-A3 (kg/m²): Detached 166.72,
Townhouses 206.75, Apartments 444.44. No STOP.

## Common conventions

* Model index 0 = 2025, 1 = 2026 (observed; `gfa_fixed = {1: observed 2026 GFA}`
  stays). Ramp weight `w(y) = clip((y − 2026) / (2035 − 2026), 0, 1)` (1/9 in
  2027, 1 from 2035; sensitivity: full by 2045). `w = 0` in 2025 and 2026, so no
  lever changes 2026.
* Near-term excess: `join = join_info['50th']['join']` and
  `join_redev = join_info['50th']['redev']` are passed unchanged to every run
  (frozen), except L2(b).

## Levers

| lever | input(s) modified | modification | identity (lever off / strength 0) |
|---|---|---|---|
| L1 new-dwelling size | `fwd_inputs['size']` (dict by typology; a scalar per typology in the baseline) | `size[t] = size_ref[t] × (1 − w(y) c_t)`, an array over years (`engine.blend` divides the share Series by it elementwise) | `c_t = 0`: `size_ref[t] × 1` (multiplication by exactly 1.0 leaves every value bit-identical) |
| L2(a) vacancy | `fwd_inputs['v']` (scalar `v_forward`) | `v(y) = v_forward + w(y)(v* − v_forward)`, an array over years (`engine.forward` broadcasts `v`) | `v* = v_forward` → the array equals `v_forward` in every year |
| L2(b) near-term absorption | `join`, `join_redev` passed to `engine.forward` | `join, ji = engine.market_excess(E_nojoin, O26, rho, '2027', 'surplus', absorption=a)` with `E_nojoin` = the baseline forward run **without** a join (same inputs as Boss l. 1543), `O26 = join_info['50th']['O26']`, `rho = rho_other` | `a = 0`: `market_excess` returns the same arrays as Boss (Boss uses absorption 0 in mode `surplus`) |
| L3 lifetime extension | `fwd_inputs['rate_demol']` (scalar), `fwd_inputs['rate_unc']` (array `unc_path`) | `rate_demol(y) = demolition_rate × (1 − w d)`; `rate_unc(y) = unconsented_rate + (unc_path(y) − unconsented_rate)(1 − w d)` (only the redevelopment-wave component `unc_path − unconsented_rate` is scaled; the long-run residual is untouched) | `d = 0`; the reference run passes the original `rate_demol` scalar and `unc_path` array |
| L4 typology mix | `fwd_inputs['shares']` (DataFrame years x typology) | attached share `a(y) = a_0 + w(y)(a* − a_0)` from 2027 with `a_0` = held Townhouses + Apartments share; the increase `Δ(y) = a(y) − a_0` is split between Townhouses and Apartments in proportion to their held shares; Detached −Δ(y). Size and OLF blend with the new shares inside `engine.forward` | `a* = a_0` → Δ = 0; the original DataFrame is passed |
| L5 best-practice materials | `fwd_inputs['intensity']` and `fwd_inputs['intensity_upfront']` (equal arrays) | `I[t](y) = T_INT[t](y) − w(y)(1 − r_t)(A13_2025[t] − RED13_TOT[t](y))`, i.e. A1-A3(y) = [1 − w(1 − r)] (A1-A3_2025 − reduction(y)); A4-A5, soil, events (`fwd_inputs['events']`), C1-C4 unchanged | `r_t = 1` → the original `T_INT` / `U_INT` objects are passed |

Run quantities recomputed per run from its own `engine.forward` result `E`
(same code paths as Boss): within-window carbon `E['carbon'][1:]`; upfront
`E['upfront'][1:]`; in-window B `E['b_t'][:, 1:]`; soil
`Σ_t soil[t] gfa_t soil_share`; floor area by typology `E['gfa_t']`; committed
after 2050 with `events.committed(gfa_t, forecast_years, profile_t,
row_factors(..., hold='2025' | '2050'))` per typology plus C1-C4 =
`Σ gfa_t[2026:] × stage_int['C1-C4', t]` (Boss l. 2274-2289); demand bands with
the Boss bookkeeping (l. 1555-1575, 1700-1745), the redevelopment wave from the
run's own `rate_unc − unconsented_rate`.

**Identity run.** `levers.apply(B, settings)` with every lever off returns
`fwd_inputs` itself (the same objects), `join`/`join_redev` from
`join_info['50th']`; `engine.forward(pop, hh, growth, join=..., join_redev=...,
**fwd_inputs)` is then the very call of Boss l. 1548-1549, so P0 reproduces the
reference central run. Tested (tests/test_pathways.py) for annual carbon,
upfront, in-window B, floor area by typology, demand bands, committed range and
cumulative LoE AR / AtP (outputs/pb_results.json), to ≤ 1e-9 relative.

**Scenarios S1 / S2** (envelope for P0 and P3 only): `validation.run_boss(
REPLACEMENT_SCENARIO='S1' | 'S2')`, the mechanism of
`tools/replacement_scenarios.py` and `PB.scenario_runs`; the levers act on each
run's own `fwd_inputs`.

**Boundaries.** `B_AR`, `B_AtP` by year for S3-10 from `outputs/pb_annual.csv`
(the levers do not change population, so the boundaries are unchanged; PB
asserts every scenario shares the population path).
