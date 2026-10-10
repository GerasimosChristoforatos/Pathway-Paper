# Sensitivity plan, MODEL v2.0.0 (design for approval)

One-at-a-time rows, grouped by the type of change. Each row has its group, its low/high setting (or
its single setting) and its basis. Every row exists today in `outputs/data/` unless marked **new**.
New rows are computed once and locked as additions (tests/regression_model_v2_additions.json); no
existing row changes. One-at-a-time ranges are not additive and are not a joint interval (stated in
every caption). The grouped tables are written to `outputs/data/sensitivity/` (new):
`reference_carbon.csv`, `p5_carbon.csv` and `planetary_boundary.csv`, with group, row, low, high,
value(s) and change vs the central case.

## 1. Reference carbon 2026–2050 (ED1 tornado; ED3 paths)

Central: the Reference, 21,578 kt CO₂e. Source of the rows: `data/baseline/sensitivity_one_at_a_time.csv`
(Sensitivity.py) unless stated.

| group | row (low / high) | basis |
|---|---|---|
| Demographics | Population, Stats NZ 5th / 95th percentile paths | Stats NZ 2024-base stochastic projection (DATA); **new**: carbon from the exact engine path (`data/aesa/results.json` population_paths, carbon 2026–2050). Today's approximate row (Reference carbon per m² × the path's floor area) stays in its data file. |
| Demographics | Household size, Stats NZ Low / High variant | Stats NZ household projections (DATA) |
| Demographics | Household size after 2043: flat; secant-slope taper; taper from the PCHIP end slope (three single rows) | JUDGEMENT on the post-2043 tail (the Stats NZ series ends in 2043) |
| Housing stock & calibration | Completion rate 0.92 / 0.96 | Jones et al. 2024 bounds (LITERATURE; citation to verify, as flagged) |
| Housing stock & calibration | Completion lag on (Little's law) | DATA (build duration from consents and dwellings under construction) |
| Housing stock & calibration | No census under-construction correction | DATA (census UC counts) |
| Housing stock & calibration | Dwelling-size window 2016–2025 (vs 2023–2025) | DATA (consents) |
| Housing stock & calibration | 2026 overbuild: payback at absorption 0.10 / 0.20 a year; booked as stock-neutral redevelopment; gap vs the 2026 requirement (single rows) | DECISION (author) on the booking of observed 2026 building |
| Housing stock & calibration | Vacancy definition | not a carbon row today. The definition test (empty-only vs including residents away) is D06, a calibration check whose rejected definition needs implausible unconsented additions. Not added. |
| Replacement scenario | Low / High replacement | DATA (1991–2023 long-run rate; 2018–2023 rate persists) |
| Replacement scenario | Replacement half-life 5 / 15 yr | JUDGEMENT (the half-life is not identifiable from the census record) |
| Carbon factors & technology | Single case study: lowest / highest materials factor | 16 NZ case studies (Christoforatos & Pickering 2025) |
| Carbon factors & technology | Jackknife low / high (all typologies) | the same case studies, leave-one-out |
| Carbon factors & technology | Frozen technology (2025 factors held) | DECISION: the no-decarbonisation bound |
| Carbon factors & technology | Decarbonisation mapping: proxy-mapped items held; NZ-made electricity-intensive items held (single rows) | Horup et al. 2025 S4 mapping cases (LITERATURE, DECISION) |
| Carbon factors & technology | Soil order: lowest (Raw) / highest (Organic) | Christoforatos, Pickering & Schipper 2026 (LITERATURE) |
| Carbon factors & technology | A4–A5 held at 2025 / on each item's own Horup path | Resch et al. 2021 vs Horup et al. 2025 (LITERATURE) |
| Carbon factors & technology | Soil carbon loss on all floor area, including replacement | DECISION (the adopted rule: no soil loss on rebuilt footprints) |
| Accounting | Event timing L / n (vs L / (n + 1)) | DECISION on maintenance timing |
| Accounting | Scope: maintenance of every cohort since 1992 in base and projection | an AESA row (it changes the AR base as well), so it appears in §3 and in D18, not as a carbon row. |

ED3 (paths): one panel per group, annual carbon 2026–2050 of every row of the group (population
rows from the exact engine paths), the Reference in black.

## 2. P5 carbon 2026–2050, pathway design (ED2 tornado)

Central: P5 Combined (Moderate, by 2035), 17,560 kt CO₂e. Rows:

| group | row | source |
|---|---|---|
| Ambition of one pathway | P1 at Ambitious, P2–P4 Moderate | **new** run |
| Ambition of one pathway | P2 at Ambitious, the others Moderate | **new** run |
| Ambition of one pathway | P3 at Ambitious, the others Moderate | **new** run |
| Ambition of one pathway | P4 at Ambitious, the others Moderate | **new** run |
| Ambition of all | P5 Ambitious | `data/pathways/runs.csv` |
| Roll-out timing | full roll-out by 2030 / by 2045 | `runs.csv` (window rule of v1.1) |
| Replacement scenario | P5 under Low / High replacement | `runs.csv` |
| Demographics | P5 under the population 5th / 95th paths, exact engine path (the boundaries move with the path for the LoE) | **new** runs |
| Separate marker (not a bar) | TL, gradual adoption | `theoretical_limit.json` (TL-gradual) |

Each row also reports the cumulative LoE AR and AtP (the table carries them; the tornado shows
carbon).

## 3. Planetary boundary: cumulative LoE AR and AtP (ED4 tornado)

Central: the Reference, LoE AR 4.85, AtP 19.4. Two tornados side by side (AR, AtP) with the same rows.

| group | row | source |
|---|---|---|
| Carrying capacity | SOS / I_glob pair C: 1 W/m² planetary boundary (vs pair A, 2 °C) | `data/aesa/sensitivity.csv` (i) |
| Base window | AR base window 2021–2025 (5 yr, as Horup); 2006–2025 (20 yr); 1992–2025 (full consistent history) | (iii) |
| Economic measures | GDP per capita in current US$ (vs PPP constant 2021) | (ii) |
| Economic measures | α = 1 (as computed in Hjalsted et al.'s SI tables) | (xiv) |
| Economic measures | s_sec with the FCE share as a ratio of sums | (v) |
| Population source | NZ population: raw Stats NZ 2024-base median; WPP 2024 median for New Zealand | (iv) |
| Population source | Population 5th / 95th paths (carbon and boundaries moving together) | `data/aesa/results.json` population_paths |
| Replacement scenario | Low / High replacement; half-life 5 / 15 yr | `data/aesa/results.json` cum_LoE_by_scenario |

The technology and accounting rows of the AESA table, (vi)–(xiii), change the carbon and are shown
as carbon in ED1. They stay in `data/aesa/sensitivity.csv` and in the diagnostic D18, which keeps
every AESA row. The (xiii) wider scope and (xii) whole-life rows change the AR base as well, so they
appear only there.

## 4. Sensitivity paths (ED3)

As §1: annual carbon per group, one panel per group, the Reference in black.

## 5. Not in the tornados (reported elsewhere)

* Monte Carlo (joint parametric uncertainty within the Reference): ED5 and Fig5 bands.
* Sobol indices: diagnostic D20.
* Ambitious settings, roll-out timing, single levers, Low/High replacement for the Reference, P5 and
  TL: ED6, ED7, ED9 and ED10 as whole-run comparisons (they are designs, not parameter uncertainty).
