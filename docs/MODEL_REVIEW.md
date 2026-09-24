# Model review: NZ residential floor area and embodied carbon, 2026–2050

Scripts reviewed: `Building_factors.py`, `Boss.py`, `Diagnostics.py`, run on the
data in `data/` (commit `f137955`). Every number below comes from those runs
unless marked otherwise. Changes made during the review are listed in
section 4. Round 2 (retirement villages, Monte Carlo) updated sections 1.4,
3.2, 3.5 and 3.7. Round 3 (Stats NZ household-estimate methodology) rewrote
3.5 and added 3.9. All numbers are from the final code.

---

## 1. How the model works

### 1.1 Carbon factors (`Building_factors.py`)

1. Reads LCA results for 16 NZ case-study buildings: absolute kg CO2e by
   material × EN 15978 module (A1–A3, A4–A5, B2/B4, C1–C4, D).
2. Divides by gross floor area to get kg CO2e/m² per building.
3. Pools buildings into three typologies (Detached, Townhouses, Apartments).
   Buildings are averaged within a sub-type first, then sub-types are averaged
   with equal weight, so the six single-storey detached cases don't outweigh
   the four two-storey ones.
4. Soil organic carbon loss is handled as land-use change, not as a material:
   `SOC per m² GFA = L_w / FSI`, where L_w is the area-weighted soil carbon loss
   per m² of footprint (58.8 kg/m²) and FSI is GFA / footprint. Denser
   typologies therefore lose less soil per m² of floor.
5. Module D is reported separately and never added to the totals.

Result, in-scope materials + soil, kg CO2e/m²: Detached 358, Townhouses 393,
Apartments 615.

### 1.2 Floor area (`Boss.py`)

The core identity (built-dwelling basis):

```
dwellings built = new households
                + vacancy allowance   (ΔHH · v/(1−v))
                + vacancy change      (HH(t−1) · Δ[1/(1−v)])
                + demolitions         (0.135 % of stock, BRANZ SR214)
                + calibrated residual (census-benchmarked, 1992–2023)
                − retirement-village units (out of carbon scope)
in-scope floor area = in-scope dwellings built × realised dwelling size
                      (by typology, 2023–25)
```

Retirement-village (RV) units are counted in the stock identity, because they
house private households, and they are reported. They are excluded from floor
area and carbon, because the consent floor-area data and the case-study LCAs
do not cover them. From 2026 they are 5.64% of all dwellings built (the
2016–2025 ratio of sums).

- **Population:** Stats NZ 2024-base stochastic projection, anchored on the
  observed 31 Dec 2025 ERP.
- **Historical households:** the Stats NZ DHE series, with the post-2018
  increments rebased on the 2023 census (× 0.826; see 3.9).
- **Household size S:** the shape of the Stats NZ 2018-base Medium household
  projection divided by the matched-vintage population, rebased on 2025
  (S = 2.657). The earlier carry-forward of 2025's "unexplained" fall is now
  a sensitivity only (3.5).
- **Households** = Population / S. Declines are floored at zero.
- **Vacancy:** census empty-dwelling share (excluding "residents away"),
  interpolated between censuses and held at the 2023 value (5.53 %) from then on.
- **Calibrated residual:** the gap in the stock identity beyond the BRANZ
  demolition rate, over the census-benchmarked years 1992–2023: +0.019 %/yr
  of stock. A negative value means unconsented additions; a positive value
  means losses above the BRANZ rate.
- **Typology mix:** additive-log-ratio trend fitted from 2012 onward,
  geometrically damped (φ = 0.8).
- **Demand bands** (growth, house-splitting, extra space, vacancy,
  replacement, residual): an accounting split of the same total.
  Note: the occupancy load factor (OLF) from the case studies moves floor
  area *between* bands but does not change the total.

### 1.3 Carbon

Floor area by typology × the constant 2025 case-study intensity. No
decarbonisation or learning is applied, which is stated as a design choice
("current practice" baseline). All modules (A–C) are booked in the year of
construction.

### 1.4 Headline (2026–2050, final code)

| | central run | Monte Carlo median | 90 % interval (5th–95th) |
|---|---|---|---|
| Built floor area, in scope | 76.7 Mm² | 80.7 Mm² | 60.0–104.6 Mm² |
| Embodied carbon (A1–C4 + soil) | 29,708 kt | 31,191 kt | 23,168–40,888 kt |
| Upfront carbon (A1–A5 + soil) | 21,862 kt | 23,004 kt | 17,098–30,017 kt |
| Retirement-village units built (not in carbon) | 35,321 | 39,052 | 27,495–54,466 |
| Households, 2050 | 2.51 M | 2.53 M | 2.40–2.66 M |
| Household size, 2050 | 2.641 | 2.624 | 2.563–2.679 |

The Monte Carlo median is 5 % above the central run. The reason is that
several inputs are one-sided relative to the central choice:
- replacement regime: the central run uses the long-run rate, while the
  Monte Carlo also allows the higher 2019–23 rate (3.9);
- vacancy: the measured census range reaches 8.1 % (2013), against 5.5 %
  in 2023;
- dwelling size: the lognormal multiplier is skewed upward;
- household rebase: the central k is near the low end of its range.

Report both numbers and say why they differ.

The central run gives a 2025→2026 step of −22 %. Built dwellings drop from
33,400 (observed 2025) to about 25,700. Census-consistent household
formation (~21,000/yr) is well below 2021–25 building. The step disappears
only if the 2019–23 replacement regime continues (3.9). Discuss it in the
paper rather than smoothing it away.

---

## 2. Comparison with the literature

| Aspect | This model | Typical approach in the literature | Assessment |
|---|---|---|---|
| Demand driver | Households (Pop / S), with explicit vacancy | Stock-driven MFA: population × floor area per capita → stock; inflow = Δstock + outflow (Müller 2006; Bergsdal et al. 2007; Sartori et al. 2008; Sandberg et al. 2016) | Household-based demand is a legitimate variant, and closer to housing-need practice. It explains formation-driven demand better than per-capita floor area. Explain in the paper why you chose it over the stock-driven MFA standard. |
| Outflow / demolition | Fixed 0.135 %/yr of stock | Lifetime (survival) distributions by cohort, e.g. Weibull or normal (Müller 2006; Sartori et al. 2008; Pauliuk & Müller 2014) | Acceptable over 25 years for a relatively young stock, but it isn't identified separately from the residual (see 3.4). Reviewers from the MFA community will ask why there are no survival curves. |
| Floor space per person | Dwelling size held per typology; "extra space" band made explicit | Floor area per capita as a key lever (Hertwich et al. 2019; Zhong et al. 2021; Arehart et al. 2021) | A strength: the extra-space band maps directly onto the sufficiency / material-efficiency lever. |
| Embodied intensity | 16 NZ case studies (15 independent), pooled by typology | Archetype LCAs or benchmark databases; large variability across studies (Simonen et al. 2017; De Wolf et al. 2017; Röck et al. 2020) | NZ-specific data is a strength. The small sample and n = 1 for apartments are a weakness (see 3.3). |
| Life-cycle timing | All modules booked at construction | Static LCA does this. Dynamic LCA separates timing (Levasseur et al. 2010). Budget studies usually use upfront carbon (Röck et al. 2020; Chandrakumar et al. 2020) | Now reported split into upfront and later stages. Use upfront carbon when comparing with annual or sectoral budgets. |
| Soil carbon | L_w / FSI, applied to all new floor area | Rarely included in building-stock carbon studies | A novel contribution. It assumes every new dwelling is greenfield and that disturbance equals the footprint (see 3.6). |
| Population uncertainty | Stats NZ stochastic percentiles | Percentile paths or scenario variants. Percentiles are not additive (Lee & Tuljapurkar 1994; Stats NZ footnote) | Was wrong; now fixed (3.1). |
| Other uncertainty | One setting per assumption; stock-term sensitivities printed | Monte Carlo propagation and global sensitivity analysis (Saltelli et al. 2008) | Was the main gap; now addressed by MonteCarlo.py (3.7). |
| Trend methods | ALR compositional trend with damping; Theil–Sen / Mann–Kendall; moving-block bootstrap | Aitchison (1986); Gardner & McKenzie (1985); Künsch (1989) | Appropriate choices. φ is set, not estimated (3.7). |

---

## 3. Robustness assessment

Severity: **High** = changes a headline number or would likely be caught at
review. **Medium** = needs disclosure or a sensitivity check. **Low** = cosmetic
or documentation.

### 3.1 [High, fixed] Population percentile paths were not percentiles

`Boss.py` added up the annual-growth 5th and 95th percentiles year by year.
Stats NZ's table footnote says percentiles are non-additive except the median.
Adding them assumes a 1-in-20 low (or high) year every year for 25 years.

| 2048 population | 5th | 50th | 95th |
|---|---|---|---|
| Published (Stats NZ) | 6.04 M | 6.53 M | 7.01 M |
| Model before fix | 5.27 M | 6.54 M | 7.81 M |
| Model after fix | 6.10 M | 6.54 M | 6.98 M |

The old floor-area band was 8.9–152 Mm², and the 5th percentile had
households falling in 13 of 25 years. It is now 51.3–103.3 Mm². The median
is unchanged. The remaining small offsets come from rebasing on the observed
Dec-2025 ERP.

### 3.2 [High, resolved] Retirement villages were hidden in the "unconsented additions" residual

The consent file's `Dwellings` column includes retirement-village (RV) units;
the three typology columns do not. RV residents are counted in the private
household series. Leaving RV units out of "built" had pushed them into the
residual: they made up 54 % of it over 1992–2025 and 75 % over 2016–2025.

**How it is handled now (your decision):**
- **Stock and demography:** RV units are counted as built dwellings in the
  identity. The residual becomes genuinely unconsented additions: −948
  dwellings/yr, or −0.056 % of stock, down from −2,059/yr (−0.121 %). RV
  history is reported:

  | period | consented/yr | share of all new dwellings |
  |---|---|---|
  | 1992–2005 | 509 | 2.1 % |
  | 2006–2015 | 1,138 | 5.7 % |
  | 2016–2025 | 2,126 | 5.6 % |

  From 2026, RV units are 5.64 % of all dwellings built, reported every year
  and cumulatively (35,658 units in the central run).
- **Carbon and floor area:** out of scope. Households housed in RV units are
  a negative band ("Housed in RV units (out of scope)"), valued at in-scope
  dwelling size so the reader can see how much housing need they meet. RV
  carbon is not estimated, because there is no RV floor area or LCA.
- **Effect:** in-scope floor area goes from 76.94 to 77.56 Mm² (+0.8 %),
  because the forward RV share is now explicit instead of the lower 1992–2025
  average hidden in the old residual.
- **Disclosure for the paper:** the 85+ population grows faster than the
  total in the Stats NZ projection, so a constant RV share may understate
  future RV building. The inputs have no historical age series to calibrate
  against, so this is disclosed rather than modelled. The Monte Carlo samples
  the share over its observed 2011–2025 range (4.1–8.2 %).

### 3.3 [High, flagged] The apartment carbon factor rests on one building

A_2 equals A_1 × 1.000073 in all 52 material × stage cells, so it is the same
design at a slightly different GFA. The next-closest pair of cases differs by
29 %. Apartments are 4 % of projected floor area, so the effect on the
headline is small. But any typology comparison ("apartments are 1.7× detached
per m²") is a one-building result. `n_independent` is now written, and the
paper should say so. Across all typologies, carbon varies from −20 % to +20 %
depending on which single case study is used (Sensitivity.py). The jackknife
range of the pooled factors is −4.5 % to +3.8 %.

### 3.4 [Medium, reported] Demolition and residual are not separately identified

Calibration trades them one-for-one: at demolition rates of 0.10 % and
0.30 % the total is identical. Only their net (+12.75 Mm², 4,936 kt in the
final central run) is identified by the data. The split (10.5 Mm² of
demolition replacement plus 2.3 Mm² of residual) depends entirely on the
BRANZ 2001–06 demolition rate.
Present the net as the result and the split as illustrative. The demand
table now prints the net line.

### 3.5 [High, resolved] Household size: the 2025 "deviation" was a product of how Stats NZ estimates households

What Stats NZ's DHE note says, and what I checked in the data:
- The household series is built from census-year **bases** (1991, 1996,
  2001, 2006, 2013, 2018). Each base is derived from the estimated resident
  population × living-arrangement type rates.
- Between and after bases (Table 2, footnote 1): *"Estimates for reference
  dates after each base are derived using weighted and lagged building
  consents."*
- 2019–2025: household growth = 0.887–0.889 × the previous year's consents,
  every year (correlation 1.000). There is no 2023 household base yet.
- 1992–2018: within each census period, household growth is a constant
  fraction of dwelling growth (e.g. 0.73 in 1996–2000, 0.84 in 2006–12), and
  the fraction resets at each base.

Consequences:
1. **The 2024–25 fall in S is an artefact.** Households kept rising at
   0.888 × lagged consents while population growth slowed. The fall is not
   observed behaviour, so carrying it forward (`e_2025`) projected a
   measurement artefact. It is now **off by default**. Carrying it is a
   sensitivity: +2.5 % (ρ estimated) and +10.0 % (ρ = 0.9).
2. **The migration–household-size correlation** (r ≈ +0.6–0.7) is, between
   censuses, consent-driven households meeting migration-driven population.
   It describes housing supply against arrivals, not household behaviour, and
   should not be presented as a behavioural finding ("the engines take
   turns"). It is still fitted and reported as a diagnostic: b = 3.95e-7,
   HAC t = 4.7, over 1992–2023.
3. **The Low/High projection variants** now move the total by +9.6 % /
   −7.6 % (they were +17.7 % / −15.3 % when the artefact was carried). The
   variants share one living-arrangement assumption and differ in fertility,
   mortality and migration. In the Monte Carlo, S follows the population rank.

What I did **not** do: drop 2024–25. They stay as the starting point, now
census-consistent (3.9).

### 3.6 [Medium] Carbon-factor assumptions to state explicitly

- Soil loss assumes all new floor area is greenfield and that disturbance
  equals the building footprint. Infill and brownfield development (a large
  share of townhouses and apartments) lose little soil carbon. Driveways and
  earthworks disturb more than the footprint. Neither effect is quantified.
  Across soil orders the effect ranges from −5.3 % to +22.5 %; Organic is an
  extreme bound.
- The B and C modules depend on the reference study period and service-life
  assumptions in the case-study LCAs. State them, and use upfront carbon for
  comparisons with budgets.
- The 2025 factors are also applied to 1992–2025 floor area in Diagnostics
  Figure 5. That is labelled "estimated", which is correct; keep the label in
  any published figure.

### 3.7 [Medium, resolved] Joint uncertainty and global sensitivity (`MonteCarlo.py`)

**Engine.** The Monte Carlo re-evaluates the forward projection with Boss's
own functions: the household-size path, stock calibration, mix and size
blend. Before sampling, it checks itself against `Boss.main()` at the central
values; the maximum relative difference over 2026–2050 is 3.8e-15.

**Inputs.** Twelve inputs are sampled jointly. The distributions and their
justification are in the script's docstring. In short:
- population rank z: published 5/25/50/75/95th level percentiles, with the
  Stats NZ Low/Medium/High household size tied to the same rank;
- household rebase k: triangular(0.785, 0.826, 1.0), from census occupied
  dwellings only, through occupied + away, to the DHE as published; the
  stock is recalibrated for each draw;
- replacement regime: a uniform weight between the 1992–2023 and 2019–23
  net replacement rates;
- b and ρ: sampled only when the 2025 carry-forward is switched on (a
  sensitivity);
- mix damping φ: triangular(0.62, 0.80, 0.98), the conventional
  damped-trend width;
- ALR mix slopes: HAC standard errors;
- dwelling size: lognormal, σ = 0.068;
- completion rate: uniform(0.92, 0.96);
- pre-2013 empty share: ±0.05;
- vacancy: triangular over the measured censuses;
- RV share: triangular over 2011–2025;
- carbon factors: stratified bootstrap of the case studies.

Demolition rate is not sampled (it cannot move the total). Soil order is not
sampled; the extremes remain a bounding scenario.

**Method.** 10,000 Latin hypercube draws (McKay et al. 1979) give the
percentiles in 1.4. Sobol indices come from 14,336 evaluations with the
Saltelli/Jansen estimators in `scipy.stats.sobol_indices` (Saltelli et al.
2010), with 95 % bootstrap confidence intervals.

**Total-order Sobol indices, cumulative carbon** (share of variance, including interactions):

| input | ST | 95 % CI |
|---|---|---|
| population rank (with household size) | 0.58 | 0.54–0.64 |
| dwelling size | 0.17 | 0.16–0.20 |
| household census rebase k | 0.08 | 0.08–0.10 |
| carbon factors (bootstrap) | 0.06 | 0.05–0.06 |
| replacement regime | 0.05 | 0.04–0.05 |
| vacancy target | 0.03 | 0.02–0.03 |
| mix damping φ | 0.03 | 0.02–0.03 |
| completion rate | 0.01 | 0.01–0.01 |
| RV share, pre-2013 share, mix slopes | ≤ 0.003 each | |

**Reading.** Population (with household size tied to it) dominates. Future
dwelling size comes next, then how households are benchmarked to the census.
The earlier large role of ρ (0.21) is gone because the artefact is no longer
carried. The case-study carbon factors explain about 6 %. That is because the bootstrap measures uncertainty in the *mean*
intensity; one building versus another differs much more (±20 % in the
one-at-a-time table).

**Caveats to state in the paper.**
- Population paths are comonotone across years: one draw keeps one rank
  throughout.
- Mapping the Low/High Stats NZ variants to the 5th/95th percentiles is an
  assumption.
- The inputs are treated as independent.
- A bootstrap of 4–6 buildings per sub-type understates variance slightly.
- The apartment spread is borrowed from the other sub-types (between-building
  log-SD 0.203), because only one independent apartment case exists.

One-at-a-time results (`Sensitivity.py`, `data/sensitivity_oat.csv`) are
kept as a complement: they show the direction of each effect.

### 3.8 [Low] Other points

- Timing: projected annual growth is for years ending 30 June, applied from
  a 31 December 2025 base. That is a half-year offset. State it.
- The same typology shares apply to every demand band. For example,
  demolition replacement is assumed to have the same mix as growth.
- Damping φ = 0.8 is set by hand rather than estimated. Cite Gardner &
  McKenzie (1985) and report the sensitivity.
- Checks that are fine: the typology GFA columns sum to the total exactly;
  history is reproduced by the decomposition to 2e-9 m²; the material, soil
  and typology carbon totals agree; and Building_factors reproduces the
  committed CSVs exactly.

### 3.9 [High, resolved] Households rebased on the 2023 census; stock calibrated where households are census-benchmarked

**Evidence.** Stats NZ rebased the dwelling series on the 2023 census (June
2023: 2,025,100 vs a census count of 2,018,781), but not the household
series. Between 2018 and 2023 the published households grew 1.099×. Census
households grew 1.082× counting occupied dwellings plus residents away, or
1.078× counting occupied dwellings only. So June 2023 is 31–38k households
(1.6–2.0 %) above the census.

**Fix (mirrors Stats NZ's own benchmarking).** All household increments after
30 June 2018 are scaled by one factor, k = 0.826, so that June 2023 matches
census growth (occupied + away, the closer match to Stats NZ's base
definition). The same k is applied to 2024–25.
- 2025 households: 2,011,726 (published 2,057,500).
- S in 2025: 2.657 (published 2.598).
- Assumption: the census undercount adjustments are proportionally equal in
  2018 and 2023. The Monte Carlo spans k from 0.785 (occupied only) to 1.0
  (the DHE as published).

**Calibration window.** The stock residual is calibrated only on
census-benchmarked years: 1992–2023 with the rebase, or 1992–2018 without
it. After the last base, the identity would only recover Stats NZ's 0.888
weight.

**Independent check, from census dwelling counts only (no household data).**
Net replacement = dwellings built − change in census private dwellings, as
% of stock per year:

| interval | net replacement | net of change in dwellings under construction |
|---|---|---|
| 1991–96 | +0.068 % | +0.056 % |
| 1996–01 | −0.103 % | −0.083 % |
| 2001–06 | +0.017 % | −0.041 % |
| 2006–13 | +0.098 % | +0.130 % |
| 2013–18 | +0.078 % | +0.008 % |
| **2018–23** | **+0.334 %** | **+0.218 %** |

Replacement roughly doubled to tripled in 2018–23. That fits the
redevelopment of existing sites in the intensification era. The household
identity shows the same: +0.154 %/yr over 1992–2023 but +0.355 %/yr in
2019–23. **Whether that regime continues is the largest structural choice
left.** Continuing it fully gives +18.3 % (Sensitivity.py). The central run
uses the long-run window. The Monte Carlo samples a uniform weight between
the two (Sobol ST ≈ 0.05). Demolition-consent data, if you can get it,
would pin this down better than any modelling choice.

**Effect on the central run:** 77.6 → 76.7 Mm², 30,028 → 29,708 kt. This is
the net of three changes:
- the rebase, with S starting higher: −;
- the 2025 carry removed: −;
- the 1992–2023 window, which includes the recent replacement: +.

---

## 4. Changes made

| File | Change | Effect on median |
|---|---|---|
| Boss.py | Population 5th/95th paths built from published level percentiles (old method kept as `POP_PERCENTILE_METHOD='cumulated_growth'`) | none |
| Boss.py | RV-unit breakdown of the residual printed; residual relabelled; net demolition + residual line added | none |
| Boss.py | Newey–West HAC SE for b | none |
| Boss.py | Carbon by life-cycle stage (upfront vs later) | none |
| Boss.py | 2025 anchor row by typology on the built basis (plots only) | none |
| Boss.py | OLF comment corrected to match the code; `main()` returns state; `SHOW_PLOTS` | none |
| Building_factors.py | Duplicate-case detection; `n_independent`; building and jackknife ranges; soil low/high exclude the aggregate row; hard-coded 1.006223 replaced by a named constant | none (existing columns identical) |
| Diagnostics.py | Uses `Boss.main()`'s return value instead of rewriting and exec-ing Boss's source; labels | none |
| Sensitivity.py | New one-at-a-time sensitivity runner | n/a |
| Boss.py | Retirement villages counted in the stock identity, projected as a share, reported, excluded from floor area and carbon (`RV_IN_STOCK`) | 76.94 → 77.56 Mm² |
| Boss.py | Household-size path moved to shared functions (`statsnz_size_shape`, `respond_household_size`, `newey_west_cov`) | none (output byte-identical) |
| Building_factors.py | Writes `factors_building.csv` for the bootstrap | none |
| MonteCarlo.py | New joint uncertainty (LHS) and Sobol analysis, validated against Boss | n/a |
| Boss.py | Households rebased on 2023 census (`HH_CENSUS_REBASE`); stock calibrated on census-benchmarked years (`STOCK_CALIB_END`); 2025 household-size carry off by default (`HH_SIZE_RESPONSE`); census dwelling-count check printed; residual relabelled | 77.56 → 76.71 Mm² |
| MonteCarlo.py | Adds `hh_rebase` and `regime` inputs; b and ρ sampled only when the carry is on | n/a |
| Diagnostics.py | Figure 2 shows the DHE evidence (household growth / lagged consents) and separates census-benchmarked years; households and S panels show the published series next to the rebased one | none |

## 5. Decisions left to you

1. **Replacement regime (3.9):** is the 2019–23 redevelopment rate expected
   to continue? The central run uses the long run and the Monte Carlo spans
   both. If you have a view based on policy, you could state it. Local
   demolition data would help most.
2. **Household rebase measure:** occupied + away (adopted) or occupied only.
   The difference is small (+1.5 %).
3. **Monte Carlo distributions:** they are stated assumptions; review the
   `MonteCarlo.py` docstring. The vacancy upper bound (8.1 %) is still the
   one most worth a second look.
4. **Demolition and residual:** whether to present them only as a net
   figure (3.4).

---

## References

Check every reference against the original before citing. I have listed only
works I am confident exist, but please confirm the details (volume, pages).
References already cited in the code (BRANZ SR214; Jones, Greenaway-McGrevy
& Crow 2024; Napiontek et al. 2025) are yours and were not checked.

- Aitchison, J. (1986). *The Statistical Analysis of Compositional Data*. Chapman & Hall.
- Arehart, J. H., Pomponi, F., D'Amico, B., & Srubar, W. V. (2021). A new estimate of building floor space in North America. *Environmental Science & Technology*, 55.
- Bergsdal, H., Brattebø, H., Bohne, R. A., & Müller, D. B. (2007). Dynamic material flow analysis for Norway's dwelling stock. *Building Research & Information*, 35(5).
- Chandrakumar, C., McLaren, S. J., Dowdell, D., & Jaques, R. (2020). A science-based approach to setting climate targets for buildings: the case of a New Zealand detached house. *Building and Environment*, 169.
- De Wolf, C., Pomponi, F., & Moncaster, A. (2017). Measuring embodied carbon dioxide equivalent of buildings: a review and critique of current industry practice. *Energy and Buildings*, 140.
- Gardner, E. S., & McKenzie, E. (1985). Forecasting trends in time series. *Management Science*, 31(10).
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts.
- Hertwich, E. G., et al. (2019). Material efficiency strategies to reducing greenhouse gas emissions associated with buildings, vehicles, and electronics — a review. *Environmental Research Letters*, 14.
- Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *Annals of Statistics*, 17(3).
- Lee, R. D., & Tuljapurkar, S. (1994). Stochastic population forecasts for the United States: beyond high, medium, and low. *Journal of the American Statistical Association*, 89(428).
- Levasseur, A., Lesage, P., Margni, M., Deschênes, L., & Samson, R. (2010). Considering time in LCA: dynamic LCA and its application to global warming impact assessments. *Environmental Science & Technology*, 44(8).
- McKay, M. D., Beckman, R. J., & Conover, W. J. (1979). A comparison of three methods for selecting values of input variables in the analysis of output from a computer code. *Technometrics*, 21(2).
- Müller, D. B. (2006). Stock dynamics for forecasting material flows — case study for housing in The Netherlands. *Ecological Economics*, 59(1).
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3).
- Pauliuk, S., & Müller, D. B. (2014). The role of in-use stocks in the social metabolism and in climate change mitigation. *Global Environmental Change*, 24.
- Röck, M., et al. (2020). Embodied GHG emissions of buildings — the hidden challenge for effective climate change mitigation. *Applied Energy*, 258.
- Saltelli, A., Annoni, P., Azzini, I., Campolongo, F., Ratto, M., & Tarantola, S. (2010). Variance based sensitivity analysis of model output: design and estimator for the total sensitivity index. *Computer Physics Communications*, 181(2).
- Saltelli, A., et al. (2008). *Global Sensitivity Analysis: The Primer*. Wiley.
- Sandberg, N. H., et al. (2016). Dynamic building stock modelling: application to 11 European countries to support the energy efficiency and retrofit ambitions of the EU. *Energy and Buildings*, 132.
- Sartori, I., Bergsdal, H., Müller, D. B., & Brattebø, H. (2008). Towards modelling of construction, renovation and demolition activities: Norway's dwelling stock, 1900–2100. *Building Research & Information*, 36(5).
- Simonen, K., Rodriguez, B. X., & De Wolf, C. (2017). Benchmarking the embodied carbon of buildings. *Technology | Architecture + Design*, 1(2).
- Stats NZ (2025). National population projections: 2024(base)–2078, Table 1 notes (non-additivity of percentiles).
- Zhong, X., et al. (2021). Global greenhouse gas emissions from residential and commercial building materials and mitigation strategies to 2060. *Nature Communications*, 12.
