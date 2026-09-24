# Model review: NZ residential floor area and embodied carbon, 2026–2050

Scripts reviewed: `Building_factors.py`, `Boss.py`, `Diagnostics.py`, run on the
data in `data/` (commit `f137955`). Every number below comes from those runs
unless marked otherwise. Changes made during the review are in commits
`b579eb4` and `e4b7732`. Section 4 lists them.

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
                + residual            (calibrated, negative)
floor area      = dwellings built × realised dwelling size (by typology, 2023–25)
```

- **Population:** Stats NZ 2024-base stochastic projection, anchored on the
  observed 31 Dec 2025 ERP.
- **Household size S:** the shape of the Stats NZ 2018-base Medium household
  projection divided by the matched-vintage population, rebased on the observed
  2025 S. Added to it is the part of 2025's unusually large fall in S that
  low migration doesn't explain (`e_2025`), fading at the residual
  autocorrelation ρ = 0.76.
- **Households** = Population / S. Declines are floored at zero.
- **Vacancy:** census empty-dwelling share (excluding "residents away"),
  interpolated between censuses and held at the 2023 value (5.53 %) from then on.
- **Residual:** the long-run gap in the stock identity over 1992–2025,
  expressed as a share of stock (−0.121 %/yr).
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

### 1.4 Headline (median, 2026–2050, after the fixes in section 4)

| | value |
|---|---|
| Built floor area | 76.9 Mm² |
| Embodied carbon (A1–C4 + soil) | 29,789 kt CO2e |
| of which upfront (A1–A5 + soil) | 21,915 kt |
| of which later stages (B2/B4, C1–C4) | 7,874 kt |
| Population-only band (5th–95th) | 51.3–103.3 Mm², 19,840–39,973 kt |

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
| Other uncertainty | One setting per assumption; stock-term sensitivities printed | Monte Carlo propagation and global sensitivity analysis (Saltelli et al. 2008) | Main gap. Sensitivity.py is a first step (3.7). |
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

### 3.2 [High, flagged] The "unconsented additions" residual is partly retirement-village units

The consent file's `Dwellings` column includes retirement-village (RV) units;
the three typology columns do not. RV residents are counted in the private
household series, so leaving RV units out of "built" pushes them into the
residual.

| period | residual (dwellings/yr) | RV units built (× 0.95) |
|---|---|---|
| 1992–2005 | −1,905 | 483 |
| 2006–2015 | −1,629 | 1,081 |
| 2016–2025 | −2,703 | 2,020 |
| 1992–2025 | −2,059 | 1,111 (54 %) |

Consequences:

- It is wrong to call the band "met without new building". These units are
  built, and they embody carbon outside the model's scope. Labels are now
  corrected, and a `[check]` prints this breakdown.
- The in-scope total stays internally consistent, but only if RV units keep
  the same share of the stock as in 1992–2025. The RV share of new dwellings
  rose from about 2 % to about 5.6 %, and an ageing population points
  upward. A stock-proportional residual calibrated on the whole window may
  therefore under-state future out-of-scope building.
- The part that is really unconsented is about −948/yr (−0.056 % of stock).

**Decision needed (yours):**
- Option (a): count RV units as built in the calibration, then project an
  explicit RV share and report it as out of scope. There is no RV floor area
  in the file, so RV carbon would need an assumed size.
- Option (b): keep the current approach and state this limitation in the
  paper.

(a) is the more defensible.

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
0.30 % the total is identical. Only their net (+1.25 Mm², 484 kt) is
identified by the data. The split (10.9 Mm² of demolition replacement against
−9.6 Mm² of residual) depends entirely on the BRANZ 2001–06 demolition rate.
Present the net as the result and the split as illustrative. The demand
table now prints the net line.

### 3.5 [Medium] Household size: a single year carries a lot of weight

- `e_2025` is one year's unexplained residual, carried forward. Removing it
  changes the total by −7.3 %; using ρ = 0.9 instead of 0.76 changes it by
  +12.6 %. The value of 2025 may be revised by Stats NZ.
- b is statistically robust to autocorrelation: Newey–West HAC SE 7.6e-8,
  t = 5.2 (OLS SE 6.4e-8; Durbin–Watson 0.49). This is now printed.
- **Circularity risk (please verify):** Stats NZ's Dwelling and Household
  Estimates, to my understanding, are rolled forward between censuses from
  building consents. If so, historical households are partly built from the
  same consents the model is calibrated against. That would (i) make parts
  of the stock identity close to tautological, and (ii) make S = Pop / HH
  correlate with migration mechanically: population jumps with migration
  while consent-driven households move slowly. The "engines take turns"
  result (r = +0.64) could then be partly a measurement artefact rather than
  behaviour. Check the DHE methodology note. If it is confirmed, the paper
  should discuss it and ideally test the relationship on census years only.
- The Stats NZ living-arrangement variant (Low / High) moves the total by
  +18.8 % / −16.2 %. This is the largest structural sensitivity, and it is not
  in the reported band.

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

### 3.7 [Medium] Uncertainty is not jointly propagated

One-at-a-time results, change in the median total (`data/sensitivity_oat.csv`):

| assumption | ΔGFA | ΔCarbon |
|---|---|---|
| Population 5th / 95th | −33.4 % / +34.2 % | same |
| S variant Low / High | +18.8 % / −16.2 % | +18.7 % / −16.2 % |
| ρ = 0.9 / no e_2025 | +12.6 % / −7.3 % | same |
| Mix damping φ 0.5 / 0.95 | +5.7 % / −7.6 % | +4.9 % / −6.8 % |
| Dwelling-size window 2016–25 | +4.5 % | +4.5 % |
| Completion rate 0.92 / 0.96 | −4.7 % / +1.6 % | same |
| Soil order Raw / Organic | 0 | −5.3 % / +22.5 % |
| Single-case materials low / high | 0 | −20.1 % / +20.4 % |

**Recommended:** a Monte Carlo run over these inputs, with distributions you
can justify, and a variance-based global sensitivity analysis (Sobol indices;
Saltelli et al. 2008). This would replace a population-only band. It needs
your judgement on the input distributions, so I have not added it.

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

## 5. Decisions left to you

1. Retirement villages: option (a) or (b) in 3.2.
2. Whether to keep carrying `e_2025` forward, or to show it as a scenario.
3. Whether to verify the DHE circularity (3.5), and how to handle it if it is
   confirmed.
4. Input distributions for a joint Monte Carlo analysis.
5. Whether to present demolition and residual only as a net figure.

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
- Hertwich, E. G., et al. (2019). Material efficiency strategies to reducing greenhouse gas emissions associated with buildings, vehicles, and electronics — a review. *Environmental Research Letters*, 14.
- Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *Annals of Statistics*, 17(3).
- Lee, R. D., & Tuljapurkar, S. (1994). Stochastic population forecasts for the United States: beyond high, medium, and low. *Journal of the American Statistical Association*, 89(428).
- Levasseur, A., Lesage, P., Margni, M., Deschênes, L., & Samson, R. (2010). Considering time in LCA: dynamic LCA and its application to global warming impact assessments. *Environmental Science & Technology*, 44(8).
- Müller, D. B. (2006). Stock dynamics for forecasting material flows — case study for housing in The Netherlands. *Ecological Economics*, 59(1).
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3).
- Pauliuk, S., & Müller, D. B. (2014). The role of in-use stocks in the social metabolism and in climate change mitigation. *Global Environmental Change*, 24.
- Röck, M., et al. (2020). Embodied GHG emissions of buildings — the hidden challenge for effective climate change mitigation. *Applied Energy*, 258.
- Saltelli, A., et al. (2008). *Global Sensitivity Analysis: The Primer*. Wiley.
- Sandberg, N. H., et al. (2016). Dynamic building stock modelling: application to 11 European countries to support the energy efficiency and retrofit ambitions of the EU. *Energy and Buildings*, 132.
- Sartori, I., Bergsdal, H., Müller, D. B., & Brattebø, H. (2008). Towards modelling of construction, renovation and demolition activities: Norway's dwelling stock, 1900–2100. *Building Research & Information*, 36(5).
- Simonen, K., Rodriguez, B. X., & De Wolf, C. (2017). Benchmarking the embodied carbon of buildings. *Technology | Architecture + Design*, 1(2).
- Stats NZ (2025). National population projections: 2024(base)–2078, Table 1 notes (non-additivity of percentiles).
- Zhong, X., et al. (2021). Global greenhouse gas emissions from residential and commercial building materials and mitigation strategies to 2060. *Nature Communications*, 12.
