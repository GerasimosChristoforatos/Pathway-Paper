# Hook inventory of the pathway layer

> Historical record, kept unchanged in substance: it was written before any pathway code and refers to the modules and line numbers at tag `baseline-PB_v3.1`, where `Boss.py` is the module now named `projection.py` (MODEL v1.0.0, docs/RENAMING.md section 8). Lever ids are those of that version (L2a, L2b, L3 = the release L2, L3, L4).

(Written for v1 before any pathways code; updated for v2: logistic ramp, L1 on the
engine's occupied area, L2 split into L2a / L2b, L5 Harrell-Davis ratio. The hooks
themselves are unchanged.)

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
| `v_forward` | l. 1284 | the vacancy-rate parameter, held at its published 2023 census value (5.39%); implied stock vacancy rises because the 2026 overbuild is not absorbed |
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
  stays). Ramp weight: normalised logistic, `s(y) = 1 / (1 + exp(−k (y − 2030.5)))`,
  `k = ln(81)/6`, `w(y) = (s(y) − s(2026)) / (s(2035) − s(2026))` for 2026-2035, 1
  after (sensitivity ramp2045: midpoint 2035.5, end 2045). `w = 0` in 2025 and
  2026, so no lever changes 2026.
* Near-term excess: `join = join_info['50th']['join']` and
  `join_redev = join_info['50th']['redev']` are passed unchanged to every run
  (frozen), except L2b.

## Levers

| lever | input(s) modified | modification | identity (lever off / strength 0) |
|---|---|---|---|
| L1 right-sized new dwellings (P1) | `fwd_inputs['size']` (dict by typology; a scalar per typology in the baseline) | `size[t](y) = occ_t(y) + [1 − f w(y)](size_ref[t] − occ_t(y))`, `occ_t(y) = S(y) × OLF_USED[t]` with `S = pop / hh` of the median path (the engine's S and OLF); held at `size_ref[t]` where `size_ref[t] <= occ_t(y)` (never binds); an array over years (`engine.blend` divides the share Series by it elementwise) | `f = 0` → `size_ref[t]` in every year |
| L4 denser typology mix (removed in v3.1) | none: `fwd_inputs['shares']` stays at the baseline held mix in every run | evaluated in pathways_v2 (attached share `a(y) = a_0 + w(y)(a* − a_0)` on `shares`) and removed: within the embodied-carbon scope a denser mix raises A1-A3 per m2, its benefits are outside the scope | not applicable |
| L2a vacancy (P2) | `fwd_inputs['v']` (scalar `v_forward`) | `v(y) = v_forward + w(y)(v* − v_forward)`, an array over years (`engine.forward` broadcasts `v`) | `v* = v_forward` |
| L2b near-term absorption (P2) | `join`, `join_redev` passed to `engine.forward` | `join, ji = engine.market_excess(E_nojoin, O26, rho, '2027', 'surplus', absorption=a)` with `E_nojoin` = the baseline forward run **without** a join (same inputs as Boss l. 1543), `O26 = join_info['50th']['O26']`, `rho = rho_other` | `a = 0`: the same arrays as Boss |
| L3 fewer removals (P3) | `fwd_inputs['rate_demol']` (scalar), `fwd_inputs['rate_unc']` (array `unc_path`) | `rate_demol(y) = demolition_rate × (1 − w d)`; `rate_unc(y) = unconsented_rate + (unc_path(y) − unconsented_rate)(1 − w d)` (only the redevelopment-wave component is scaled; the long-run residual untouched) | `d = 0` |
| L5 best-practice materials (P4) | `fwd_inputs['intensity']` and `fwd_inputs['intensity_upfront']` (equal arrays) | `I[t](y) = T_INT[t](y) − w(y)(1 − r)(A13_2025[t] − RED13_TOT[t](y))`, the same r for every typology (r = Harrell-Davis quantile of the case-study ratios, `outputs/factors/factors_building.csv`); A4-A5, soil, events (`fwd_inputs['events']`), C1-C4 unchanged | `r = 1` |

Run quantities recomputed per run from its own `engine.forward` result `E`
(same code paths as Boss): within-window carbon `E['carbon'][1:]`; upfront
`E['upfront'][1:]`; in-window B `E['b_t'][:, 1:]`; soil
`Σ_t soil[t] gfa_t soil_share`; floor area by typology `E['gfa_t']`; committed
after 2050 with `events.committed(gfa_t, forecast_years, profile_t,
row_factors(..., hold='2025' | '2050'))` per typology plus C1-C4 =
`Σ gfa_t[2026:] × stage_int['C1-C4', t]` (Boss l. 2274-2289); demand bands with
the Boss bookkeeping (l. 1555-1575, 1700-1745), the redevelopment wave from the
run's own `rate_unc − unconsented_rate`.

**Identity run.** `levers.apply(base, params, {})` (every lever off) returns
`fwd_inputs` itself (the same objects), `join`/`join_redev` from
`join_info['50th']`; `engine.forward(pop, hh, growth, join=..., join_redev=...,
**fwd_inputs)` is then the very call of Boss l. 1548-1549, so P0 reproduces the
reference central run. Tested (tests/test_pathways.py) for annual carbon,
upfront, in-window B, floor area by typology, demand bands, committed range and
cumulative LoE AR / AtP (outputs/pb_results.json), to ≤ 1e-9 relative.

**Scenarios S1 / S2** (envelope for P0 and P5 only): `validation.run_boss(
REPLACEMENT_SCENARIO='S1' | 'S2')`, the mechanism of
`tools/replacement_scenarios.py` and `PB.scenario_runs`; the levers act on each
run's own `fwd_inputs`.

**Boundaries.** `B_AR`, `B_AtP` by year for S3-10 from `outputs/pb_annual.csv`
(the levers do not change population, so the boundaries are unchanged; PB
asserts every scenario shares the population path).

## Theoretical limit T (v3.1; `levers.apply_T`, `pathways.run_T`)

| item | input(s) modified | modification |
|---|---|---|
| T1 no idle stock | `fwd_inputs['v']`; `join`, `join_redev` | `v = 0` from 2027; `engine.market_excess(..., 'surplus', absorption=1)`; banking rule (`pathways.bank`) entered as a stock-adding join = banked built − requirement, `join_redev = 0` |
| T2 no extra space | `fwd_inputs['size']` | L1 with `f = 1`: size = S(y) × OLF (T3's OLF when T3 is active) |
| T3 minimum space per person | `fwd_inputs['olf']` | every typology at the lowest independent case-study design OLF |
| T4 best materials | `fwd_inputs['intensity']`, `fwd_inputs['intensity_upfront']` | L5 form with r per typology = its own best independent case (apartments held at 1) |
| T5 best soil, T6 urban densification | `fwd_inputs['intensity']`, `fwd_inputs['intensity_upfront']` (soil term) | I' = I − SOC_avg · share + SOC_path · share, share = the engine's soil-bearing share of the floor area built (clipped to [0, 1]; 0 in years with no new building); T5: SOC_path = SOC_low; T6: SOC_path × (1 − 0.65 w) |

All T items at w = 1 from 2027 (`levers.ramp_instant`); 2026 untouched. T-ramp: the same items on the logistic ramp.
