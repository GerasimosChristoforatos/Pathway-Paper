# Architecture: how the model works (baseline-pb-v3)

This document is for a reviewer who knows statistics or modelling but not this
code or New Zealand housing data. It describes what each script reads, what it
calculates and in what order, and what it writes. Headline numbers are not
repeated here: they are generated into [RESULTS.md](RESULTS.md),
`outputs/metrics.json` and `outputs/BASELINE_DRAFT.md`. Every setting, with its
basis (data, literature, author decision, judgement), is in
[ASSUMPTIONS.md](ASSUMPTIONS.md). Parameter values quoted below are the adopted
settings in `Boss.py`.

---

## 1. What the model answers

How much new residential floor area New Zealand will build from 2026 to 2050,
and how much embodied carbon that floor area carries, split by building type
(detached, townhouses, apartments), by reason for building (household growth,
vacancy, replacement, ...) and by material and life-cycle stage.

The model is bottom-up and demand-driven: people → households → dwellings
required → floor area → carbon. Construction capacity, prices and policy are not
modelled. Carbon intensities are the 2025 case-study values; with
`DECARB_MODE = 'horup_item'` (adopted) the A1–A3 part of each case-study EPD
item follows the material-specific GWP paths of Horup et al. (2025) from 2026,
and A4–A5 a generic 1%/yr path after Resch et al. (2021) (section 4.9); with
`'none'` and `DECARB_A45 = 'held'` every factor is held at 2025 (frozen
technology). With `ACCOUNTING = 'time_resolved'` (adopted) upfront emissions are
counted in the construction year and replacements and repaints (B2, B4) in the
year they occur; later events and end of life are committed emissions after
2050, reported as a range (section 4.10).

---

## 2. Scripts and data flow

```mermaid
flowchart LR
    subgraph inputs["data/ (inputs; data/derived built by scripts from data/raw)"]
        BD[building_data.xlsx<br/>16 case-study LCAs]
        EV[derived/lca_events.csv<br/>replacement / repaint counts]
        CM[derived/consents_monthly.csv<br/>monthly building consents]
        HP[histpopdata.xlsx / derived/population_quarterly.csv<br/>population]
        OH[oldhouseholddata.xlsx<br/>household estimates]
        PP[popdata.xlsx<br/>population projection 2024-base]
        HH[Householddata.xlsx + subnational 2018-base<br/>household size shape]
        CE[occ-unocc-2013.xlsx + derived/census_dwellings.csv<br/>census occupancy]
    end
    BF[Building_factors.py] --> F[(outputs/factors/*.csv)]
    BD & EV --> BF
    EVP[events.py<br/>event kernels, committed] --- BOSS
    F --> BOSS[Boss.py<br/>central run]
    ENG[engine.py<br/>pure forward model] --- BOSS
    ENG --- MC
    CM & HP & OH & PP & HH & CE --> BOSS
    BOSS -->|main returns its state| DIAG[Diagnostics.py]
    BOSS -->|re-run, one setting changed| SENS[Sensitivity.py]
    BOSS -->|data + settings copied once| MC[MonteCarlo.py]
    BOSS --> VAL[validation.py, gap_2026.py, tools/]
```

`python run_all.py` runs everything in a fixed order (see README), each script
in its own process, and writes to `outputs/`. **One engine:** the forward model
is in `engine.py` (stock calibration, census dwelling-count rates, replacement
path, near-term market excess, typology mix, forward projection). These are pure
functions; `Boss.py` and `MonteCarlo.py` both call them. `Boss.main()` returns a
dictionary of all its local variables, which the other scripts read.

---

## 3. `Building_factors.py`: carbon per square metre

1. Each case study's absolute emissions (by material and EN 15978 stage) are
   divided by its gross floor area (GFA).
2. Materials are grouped into six lines: concrete, steel, timber, plastics &
   paint, plasterboard, others.
3. Buildings are pooled into three typologies: equal weight within sub-type,
   then equal weight across sub-types. A_2 duplicates A_1 (scaled by
   1.000073), so apartments have one independent case.
4. Soil carbon is land-use change, not a material: soil loss per m² of floor =
   soil loss per m² of footprint (58.77 kg CO₂e/m², area-weighted over the soil
   orders of Auckland land zoned for urbanisation) / floor space index.
5. Stage D is written out but never added. Stages in scope: A1–A3, A4–A5,
   B2/B4, C1–C4.
6. Replacement and repaint events (`event_rows`): each line of
   `data/derived/lca_events.csv` (counts and lifespan from the LCAQuick root
   tables; stage totals from `building_data.xlsx` and the item table) is split
   into n events of line B2/B4 / n at k L / (n + 1) years (sensitivity k L / n;
   a fractional year split linearly), each divided into A1–A3 : A4–A5 : C1–C4
   in proportion to the line's initial stages and carrying its decarbonisation
   path (replacements: the item's S4 row; repaints and recoating: the paint
   path). Pooled per typology like the factors; the pooled events add up to the
   B2/B4 factor of each typology (tested).

Outputs: `factors_material.csv`, `factors_typology.csv`, `factors_building.csv`,
`factors_events.csv`, `factors_building_events.csv`, `factors_a45_item.csv`.

---

## 4. `Boss.py`: the central projection

### 4.1 Consents (history 1991–2025)

Monthly consents are summed to calendar years: floor area and dwellings by
typology, and an all-category dwelling count. Retirement-village (RV) units =
all-category − three typologies. RV units are dwellings in the stock but carry
no floor area or carbon (no RV case study); forward they are a constant share
of all dwellings built (ratio of sums 2016–2025, 5.6%). RV floor area is
reported separately, out of scope. Realised dwelling size = floor area /
dwellings, held per typology at its 2023–2025 average.

Dwellings built = 0.95 × consents (completion rate; Jones et al. 2024 bounds
0.92–0.96). No completion lag in the adopted run (Little's-law lag is a
sensitivity).

### 4.2 Population and households (history)

Population: estimated resident population at 31 December. Households: Stats NZ
Dwelling and Household Estimates (DHE) at 31 December. After the 2018 base the
DHE series is 0.888 × lagged consents, so increments after June 2018 are
scaled by one factor k = 0.824, chosen so that June 2023 grows over June 2018
by the census ratio of occupied + residents-away private dwellings. 2024–25
household values are consent-derived and not used as evidence (the household
size anchor is 2023).

### 4.3 Net replacement: the census dwelling-count identity

For each intercensal interval: net replacement = (completions − change in
census private dwellings) / stock-years, with completions corrected for the
change in dwellings under construction on census night. This uses neither the
household estimates nor the empty/away split (which breaks between 2013 and
2018). Long run (ratio of sums 1991–2023): 0.101% of stock per year; the
2018–2023 interval: 0.312%. A fixed BRANZ demolition rate (0.135%/yr) splits
the net rate into demolition and a residual (net unconsented additions); only
their sum is identified.

The household stock identity (built = new households + vacancy allowance +
vacancy change + net replacement) is still calibrated and printed for
comparison, and is used by the hindcast with one vacancy definition throughout
(the pooled 2018/2023 empty share).

### 4.4 Replacement scenarios

`engine.replacement_path`, three scenarios, all with typology shares held:
**Low (S1)** long-run rate throughout; **Reference (S3-10)** the 2018–2023 rate
fading to the long-run rate with a 10-year half-life (5 and 15 years as
sensitivities); **High (S2)** the 2018–2023 rate persists. The half-life is not
identifiable from the census record.

### 4.5 Population projection

Stats NZ 2024-base stochastic projection: the median path is observed 2025 plus
the published median growth (PCHIP between knots); the 5th/95th paths add the
published spread of the *level* about the median, shifted to zero in 2025.
2026 growth is observed (mean-quarter ERP, June quarter 2026 − June quarter
2025); later growth is the projection's, so the level shift is permanent.

### 4.6 Household size

`S_StatsNZ = population / households` at the shared knots of the 2018-base
subnational population and household projections (2018–2043). Interpolation:
one cubic Hermite through every knot (PCHIP derivatives at interior knots, zero
slope at 2043), held constant after 2043. Applied as a shape rebased on the
observed 2023 value; households = population / S for every population path.
Household decline is floored at zero (it becomes vacancy).

### 4.7 Typology mix

Floor-area shares are held at their 2022–2026 consented average in every
scenario (`MIX_MODE = 'held'`); 2026 uses the observed consented mix. The damped
additive-log-ratio trend (fitted on 2012–2025, φ = 0.8; `MIX_MODE = 'trend'`, or
`'storyline'` for S2 only, as in v1.0.2–v1.2) stays in the code but is not run or
reported: the typology mix is a pathway lever for the next paper.

### 4.8 Forward requirement and the near-term market excess

```
dwellings built (all categories) = new households + vacancy allowance (v held at the 2023 census)
                                   + net replacement (scenario rate × last year's stock)
                                   + near-term market excess
in-scope dwellings              = dwellings built × (1 − RV share)
floor area                      = in-scope dwellings × blended dwelling size
```

2026 building is observed: 0.95 × consents over the latest 12 observed months
(the year to July 2026). Its excess over the 2026 requirement is booked in
2026; from 2027 building stays above the requirement by gap_ref × ρ^(t−2026),
with gap_ref = building 2026 − requirement 2027 and ρ the estimated persistence
of departures from the calibrated identity. The excess is stock-adding (extra
vacancy, never absorbed); redevelopment booking, payback and the gap against
the 2026 requirement are sensitivities. 2026 floor area is fixed to the
observed consented GFA.

The floor area is reported in demand bands (bookkeeping; they add up to the
total): growth (net of consolidation), house-splitting, extra space per
dwelling, vacancy allowance, long-run background replacement (demolition net of
unconsented additions), the recent redevelopment wave (scenario − long run),
and the near-term market excess. In the figures RV units are removed from every
band in proportion (each band × (1 − RV share)), so all bands are in scope and
sum exactly to the typology total (tested).

### 4.9 Carbon

Floor area by typology × intensity, by band, material, soil and stage. Upfront
= A1–A5 + soil. Soil applies only to floor area on new footprints: zero on the
replacement bands (land already settled).

**Material decarbonisation** (`DECARB_MODE`). `'none'`: every A1–A3 factor held
at its 2025 value. `'horup_item'` (adopted from baseline-pb-v1.2): the A1–A3
factor of each EPD item of the case studies (`data/derived/material_items.csv`,
built by `data/build_material_items.py` from the supplied item table and
checked against `building_data.xlsx`) is multiplied, year by year, by the
relative GWP path of its counterpart in Horup et al. (2025) SI Table S4 (average
of 9 premise scenarios, relative to 2025; linear between 2025, 2030, 2040 and
2050), mapped one-to-one by `data/material_item_map.csv` (direct; by Horup et
al. p. 6 for other cementitious and wood-based products; a labelled proxy; or
held, the lift); summed per building and class, then pooled, so the 2025 totals
are the class totals. `DECARB_ITEM_CASE` selects its sensitivities (proxies
held; NZ-made electricity-intensive items held). **A4–A5** (`DECARB_A45`):
`'resch'` (adopted) e^(−0.01 (t − 2025)) after Resch et al. (2021) Table 1;
`'held'` and `'item'` (each item's S4 path) are sensitivities. C1–C4 and soil
stay at 2025. The history (1991–2025) always uses 2025 factors. The Monte Carlo
bootstraps the same reductions per case study with the same resampled cases.
Coverage by mapping basis: `outputs/factors/factors_a13_item_coverage.csv`.

### 4.10 Accounting of the later stages (`ACCOUNTING`)

`'time_resolved'` (adopted): the construction year carries the upfront
emissions; `events.py` builds per typology a kernel K[i, j] (kg/m² of the
cohort built in year i occurring in year j, each event component at its own
factor in year j) and `engine.forward` adds gfa @ K to the carbon of year j.
Events after 2050 and all C1–C4 of the 2026–2050 cohorts are committed
emissions (`COMMITTED`): upper bound at 2025 factors, lower bound with the 2050
factors held (no extrapolation beyond the last source year). At 2025 factors,
upfront + in-window B + committed B + C1–C4 equals the whole-life total exactly
(tested; `tools/reconciliation.py`). `'whole_life_at_construction'` books every
stage in the construction year (baseline-pb-v2; with A4–A5 held it reproduces
v2 exactly, tested) and is a sensitivity.

---

## 5. `Diagnostics.py`

Runs `Boss.main()` once: household engines and the DHE/consent relationship
(diag_2), the stock bucket (diag_3), floor area (diag_4), carbon of the
projection (diag_5; no historical carbon) and
the vacancy-definition appendix (diag_3b). The history of the demand
decomposition is one bar per census interval (interval means, one vacancy
definition): between censuses annual detail is not identified. Accounting
identities and factor sums are checked in `tests/test_identities.py`.

## 6. `Sensitivity.py`

Re-runs `Boss.main()` with one setting changed per row: replacement scenarios
and half-lives, mix, household-size variants and tails, dwelling-size window,
completion rate and lag, census under-construction correction, near-term
booking and gap reference, soil on replacement, and the decarbonisation and
accounting rows (`Sensitivity.DECARB_CASES`: frozen technology, proxies held, NZ
low-carbon-electricity items held, A4–A5 held, A4–A5 on the item paths, event
timing L / n, whole life at construction). Population rows reuse Boss's 5th/95th paths;
carbon-factor and soil-order rows re-weight the central floor area. Writes `outputs/sensitivity_oat.csv`, `sens_1`, `sens_2`. One-at-a-time
ranges are not additive.

## 7. `MonteCarlo.py`

Within each scenario (S3-10 reference, S1, S2): 5,000 Latin hypercube draws of
population rank z (moving population between the published percentile levels
and household size between Stats NZ Low/Medium/High with the same z), a
dwelling-size multiplier, the completion rate (two-piece uniform with median
0.95) and a stratified bootstrap of the carbon factors. Each draw runs the same
`engine.py` chain; the central draw is checked against `Boss.main()` to 1e-9.
With decarbonised materials (`DECARB_MODE`), the bootstrap also resamples each
case study's reduction by year, its event kernel and its event age profile with
the same resampled cases and multipliers, so the random stream and every
2025-factor draw are unchanged.
Sobol first-order and total indices (reference scenario, 1,024 × 6
evaluations). This is within-scenario parametric uncertainty only; scenario,
mix, carbon-factor and soil bounds are reported separately (sens_1).

## 8. Validation, reports and run modes

**Frozen-technology check.** The adopted run decarbonises materials and
resolves events in time. `run_all.py` also runs Boss, Sensitivity, MonteCarlo,
the scenario table and PB with `DECARB_MODE = 'none'`, `DECARB_A45 = 'held'` and
`ACCOUNTING = 'whole_life_at_construction'` (environment `PATHWAY_FROZEN=1`)
into `outputs/frozen/`; the v1.2.1 regression test compares that run, and its
own recomputation of the central run and scenario totals, with v1.2.1 to 1e-9,
and `tests/test_v3.py` checks the whole-life accounting against baseline-pb-v2
(`tests/regression_pb_v2.json`). The class-level decarbonisation mode and the
`--compare-modes` comparison were removed in baseline-pb-v3 (CHANGELOG; results
preserved at tags baseline-PB_v1.2 and baseline-PB_v2).

**Quick mode** (`run_all.py --quick`, development only): 1,000 Monte Carlo draws
per scenario, 128 Sobol base samples, no frozen-technology Monte Carlo, Monte
Carlo regression checks skipped; `metrics.json` (`run_mode`), the generated
documents and every figure are marked "QUICK RUN, not for reporting".



`validation.py`: rolling-origin hindcast of dwellings built from 2006, 2013 and
2018 (consistent vacancy definition), and the 2026 out-of-sample check (model
run without any 2026 data vs observed consents). `gap_2026.py`: decomposition of
the 2026 gap. `tools/`: near-term rule and scenario reports, report figures,
metrics, RESULTS.md, ASSUMPTIONS.md and BASELINE_DRAFT.md.
`tests/test_regression_v1_2_1.py` checks every headline number against v1.2.1.

## 9. `PB.py`: planetary-boundary layer (AESA, climate change)

A layer on top of the model outputs; nothing in the model changes. Equations
are pure functions in `aesa.py`; `PB.py` assembles data, runs and figures.

```mermaid
flowchart LR
    BOSS[Boss.main via validation.run_boss<br/>central + every scenario row] --> H[history 1992-2025<br/>projection soil convention]
    BOSS --> I[I_sec 2026-2050<br/>by scenario]
    MCD[outputs/montecarlo_draws_*.csv] --> MCR[MonteCarlo.project re-run<br/>per draw, asserted vs saved]
    WPP[derived/wpp2024_population_median.csv] --> PW[P_W]
    WDI[derived/wdi_economies.csv] --> A[alpha, g_W, g_NZ, year b]
    GDP[derived/nz_gdp_quarterly.csv + consents] --> S[s_sec]
    H --> BAR[B_AR, Horup Eq. 1]
    PW --> BAR & BATP[B_AtP, Hjalsted Eqs. 5-6]
    A --> BATP
    S --> BATP
    BAR & BATP & I & MCR --> OUT[(pb_annual / pb_mc_annual /<br/>pb_sensitivity .csv, pb_results.json, figures)]
```

1. **History (at 2025 factors).** Sector emissions 1992-2025 = built floor
   area by typology x the 2025 case-study factors, with soil only on the
   non-replacement floor area, as in `engine.forward`: net replacement in year
   y = census-interval rate x last year's stock x (1 - RV share) x dwelling
   size (2024-25: the 2018-23 rate carried). The base follows the projection's
   accounting rule (`PB.window_base`): upfront of the window's construction
   plus the events within the window of cohorts built in it. The mean
   2016-2025 is Ī_sec,base. Historical carbon is used only for the AR base and
   the base-window sensitivity rows; no figure shows it outside the base window.
2. **Acquired rights.** B_AR(t) = SOS (Ī_sec,base / I_glob) x population
   modifier relative to t0 = 2025 (NZ: model path; world: WPP 2024 median,
   dated 31 December as the mean of 1 July t and t+1).
3. **Ability to pay.** α, g_W and g_NZ in base year b (latest year with ≥ 98%
   WDI population coverage of PPP GDP per capita), over the covered economies;
   s_sec = consented residential value / final consumption expenditure
   2016-2025. B_AtP(t) = SOS / P_W(t) x g_W/g_NZ x α x P_NZ(t) x s_sec.
4. **Scenarios.** Every deterministic scenario of
   `tools/replacement_scenarios.py` is re-run (full Boss run); they share the
   population path, so the boundaries are the same and only I_sec differs.
5. **Monte Carlo.** Each saved draw of S3-10, S1 and S2 is re-run through
   `MonteCarlo.project()` from its saved parameters (MonteCarlo.py unchanged);
   the run stops unless every draw reproduces its saved outputs to 1e-9. The
   boundaries are recomputed from each draw's NZ population path, and the AR
   base Ī_sec,base from the draw's case-study carbon factors (2025 technology)
   on the observed history, so factor uncertainty enters base and projection
   alike.
6. **Sensitivities** of cumulative LoE (reference scenario): source pair,
   GDP measure, AR base window, NZ population source, s_sec definition, the
   decarbonisation and accounting rows, the wider B scope (events of all
   cohorts since 1992 in base and projection) and α = 1.
7. **Committed emissions** per scenario, in years of the 2050 AR boundary
   (`pb_results.json` "committed", pb_6).

Settings, sources and limitations: top of `PB.py` and ASSUMPTIONS.md; methods
as implemented: `outputs/PB_METHODS_DRAFT.md`.

---

## 10. Pathways (PATHWAYS v2: `levers.py`, `pathways.py`)

A layer on top of the frozen baseline, like PB: nothing in the model changes and no
baseline output is rewritten. `tests/test_baseline_lock.py` checks the SHA-256 of
the 65 files tracked under `outputs/` at tag baseline-PB_v3.1
(`tests/baseline_manifest.json`). `pathways.py` obtains the Boss state from
`validation.run_boss()` (`Boss.main()` returns its locals, in memory only) and
re-calls `engine.forward()` with copies of `fwd_inputs` modified by the pure
functions of `levers.py`. Which input each lever changes:
`outputs/pathways/HOOKS.md`.

```mermaid
flowchart LR
    BOSS[Boss.main via validation.run_boss<br/>S3-10; S1, S2 for the envelope] --> CTX[fwd_inputs, S, OLF, join,<br/>events, committed factors]
    FB[outputs/factors/factors_building.csv] --> L5[L5: Harrell-Davis quantile<br/>+ bootstrap]
    LEV[levers.py<br/>L1, L4 / L2a, L2b / L3 / L5<br/>logistic ramp 2026-2035] --> RUN
    L5 --> LEV
    CTX --> RUN[engine.forward per run<br/>P0, levers, P1-P5, 16 + 64 subsets]
    PBA[outputs/pb_annual.csv<br/>B_AR, B_AtP S3-10] --> GAP
    RUN --> GAP[bands, cumulative LoE, committed,<br/>Shapley, back-cast, solution space]
    GAP --> OUTP[(outputs/pathways/*.csv, *.json,<br/>LEVERS_TABLE.md, PATHWAYS_METHODS_DRAFT.md, pw_1-pw_7)]
```

1. **Pathways and levers** (settings central and stretch; normalised logistic ramp,
   w = 0 in 2026, 1 from 2035; sensitivity ramp2045): P1 Right-size space = L1
   right-sized new dwellings (`size` per typology and year: the space above the
   engine's occupied area S x OLF cut by f) + L4 denser mix (`shares`); P2 Occupy
   the existing stock = L2a vacancy path (`v`) + L2b absorption of the near-term
   surplus (`join` from `engine.market_excess(..., 'surplus', absorption)`); P3
   Keep and reuse = L3 fewer removals (`rate_demol`, `rate_unc`); P4 Build better =
   L5 best-practice A1-A3 ratio (`intensity`, `intensity_upfront`), r = the
   Harrell-Davis quantile of the case-study ratios with a bootstrap interval; P5
   all. Resolved values: `outputs/pathways/levers.json`; Table 1:
   `outputs/pathways/LEVERS_TABLE.md`.
2. **Identity.** With every lever off the call is the reference call of Boss, and
   P0 reproduces the central run (annual carbon, upfront, in-window B, floor area
   by typology, demand bands, committed range, cumulative LoE) to 1e-9; each lever
   at zero strength is the baseline (`tests/test_pathways.py`). The near-term
   excess is frozen except under L2b; 2026 is never changed.
3. **Per run**: within-window carbon, upfront, B, soil, A1-A3, A4-A5, floor area
   by typology and by demand band (with the delta vs P0, exact), committed after
   2050 (`events.committed`, the run's floor area), dwellings, mean size, existing
   dwellings released, implied vacancy, and cumulative LoE against the S3-10
   budgets of `outputs/pb_annual.csv`. Checks that stop the run: identity, sizes
   below the occupied area, implied vacancy below 4.0%, negative dwellings, fewer
   than 10 L5 cases or r >= 1.
4. **Attribution**: Shapley values over the 16 pathway subsets (main) and the 64
   lever subsets (SI), exact rational arithmetic (they sum to P0 - P5 exactly).
5. **Gap**: back-cast of P5 (central, stretch) and P0 (uniform factor k on every
   2027-2050 cohort, `scipy.optimize.brentq` for cumulative LoE AR = 1; AtP
   minimum at k = 0) and the demand x intensity solution space on P0 (Horup et
   al. 2025, Fig. 6 style).

**Run mode.** `python run_all.py --pathways-only` (about 40 s) runs `pathways.py`,
then `pytest tests/test_pathways.py tests/test_baseline_lock.py`, then
`tools/pathways_methods.py --sections` (methods draft, LEVERS_TABLE, and the
Pathways sections of ASSUMPTIONS.md and FIGURES.md, each replacing only its own
section). It does not clear `outputs/figures/` (only `pw_*` files are replaced)
and stamps nothing as quick. The full pipeline runs the same `pathways` step
after the frozen-technology check (after `figures_report`, which rewrites
FIGURES.md) and before the tests, and `pathways_docs` after `pb_methods`.
`tools/figures_report.py` run on its own while `pw_*` figures exist stops with
"unlisted": run `run_all.py`, which clears the figures first. Methods as
implemented: `outputs/pathways/PATHWAYS_METHODS_DRAFT.md`.

---

## 11. Glossary

| term | meaning |
|---|---|
| GFA | gross floor area, m² |
| DHE | Stats NZ Dwelling and Household Estimates |
| ERP | estimated resident population |
| S | average household size = population / households |
| v | vacancy rate = empty private dwellings / all private dwellings |
| RV | retirement-village unit |
| UC | dwellings under construction on census night |
| OLF | occupancy load factor = floor area per design occupant |
| FSI | floor space index = GFA / building footprint |
| ALR | additive log-ratio transform for shares that sum to one |
| φ | damping factor of the mix trend |
| ρ | persistence of departures from the calibrated stock identity |
| PCHIP | piecewise cubic Hermite interpolation, a shape-preserving spline |
| EN 15978 stages | A1–A3 product, A4–A5 construction, B2/B4 maintenance/replacement, C1–C4 end of life, D beyond the life cycle |
| upfront carbon | A1–A5 + soil loss |
| AESA | absolute environmental sustainability assessment |
| SOS | safe operating space: the global carrying capacity for climate change (kg CO₂-eq/yr) |
| AR / AtP | acquired rights / ability to pay (allocation principles) |
| LoE | level of exceedance = impact / boundary (> 1: exceeded) |
| s_sec | the sector's share of final consumption expenditure (upscaling, Hjalsted Eq. 6) |
