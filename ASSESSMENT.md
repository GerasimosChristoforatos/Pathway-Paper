# Critical assessment of the previous review (claims C1–C9)

**Status: Step 1 only. No model code has been changed.** This document
verifies or refutes each claim with numbers from the code and data. It then
judges whether each proposed fix is sound, estimates its effect on the
headline results, and lists what the review got wrong or missed. It ends with
a proposed order for Step 2 and the external data that would be needed.

Every number here can be reproduced. The scripts are in
`docs/assessment_evidence/` and their saved outputs in
`docs/assessment_evidence/output/`. The scripts read the model; they do not
modify it. Each alternative is applied by setting a module flag, or wrapping a
module-level function, on a freshly reloaded `Boss`.

Effects are computed in one of two ways, and each is labelled:
* **full run**: a complete `Boss.main()` re-run;
* **replica**: an offline copy of Boss's stock calibration and forward
  equation (`stockcal.py`). It reproduces Boss to the printed precision:
  76.713 vs 76.713 Mm² adopted, and 73.204 vs 73.204 Mm² at completion 0.92.
  It is used where the change sits inside a closure that cannot be patched
  from outside.

All effects are **one at a time**. They are not additive.

---

## 0. Step 0: reproduction

Environment: Python 3.11.15, numpy 2.4.6, pandas 3.0.6, scipy 1.17.1,
matplotlib 3.11.2, openpyxl 3.1.5. Headless, `MPLBACKEND=Agg`.

| quantity | reference | reproduced |
|---|---|---|
| Boss floor area 2026–2050 | 76.71 Mm² | **76.71** |
| Boss carbon 2026–2050 | 29,708 kt | **29,708** |
| MC median floor area | ≈ 80.66 Mm² | **80.662** |
| MC median carbon | ≈ 31,191 kt | **31,191** |
| central run's percentile in the MC | ≈ 39th | **38.5** (floor area), **39.0** (carbon) |
| 2025→2026 step | ≈ −22.1% | **−22.1%** |

The other outputs:
* `factors_*.csv` and `sensitivity_oat.csv` are byte-identical to the
  committed files.
* `montecarlo_summary.csv` and `montecarlo_draws.csv` are byte-identical.
* `montecarlo_annual.csv`: the committed file is **stale**. It predates the
  25th/75th columns the current script writes. The common columns are
  identical.
* `montecarlo_sobol.csv`: the point estimates are identical, but the bootstrap
  confidence bounds differ (up to 33% relative on one bound). `res.bootstrap()`
  is called without a seed, so the Sobol **CIs are not reproducible** (see N3).

The working tree was restored to HEAD after the reproduction runs.

---

## Summary

| claim | verdict | proposed fix | effect on headline (one at a time) |
|---|---|---|---|
| C1 two engines | **Confirmed, and worse than stated** | Sound; a stronger version is recommended | none at the centre; −1.8% at k = 1; untestable for 7 of 12 inputs |
| C2 household-size tail | **Confirmed, with corrections** | Sound as sensitivities; a better method exists | flat tail +1.9%; mean slope +4.6% |
| C3 DHE consistency | **Confirmed** | Sound | 2023 anchor −0.85%; drop 2025 deviation −0.9% (step becomes −29.7%) |
| C4 completion lag | **Confirmed; the review's 0.78 yr is an artefact** | Sound, but it cannot remove the step | −0.5% to −2.2%; step −18% to −20% |
| C5 replacement–mix coherence | **Hindcast confirmed (−18.9%), but misattributed** | (A) acceptable as scenarios; (B) not identifiable | depends on N1 |
| C6 soil | **Confirmed** | Sound | −1.6% (all greenfield) to −9.8% (no soil) on carbon |
| C7 MC distributions | **Confirmed; one reason is wrong** | Sound | MC median shifts: regime +4.3, vacancy +2.7, k −3.7, completion −1.5 Mm² |
| C8 Building_factors | **Confirmed, plus two more defects** | Sound | none (checks) |
| C9 hygiene | **Confirmed, plus more** | Sound | none, except one inconsistent printed number |
| **N1 (missed)** | **census vacancy definition breaks in 2018** | see §N1 | **−5.5% to −9.3%** floor area and carbon |

**The largest issue is one the review did not raise (N1).** The split of
unoccupied dwellings into "empty" and "residents away" changes from 76%/24%
in the 2013 census to 50%/50% in 2018 and 2023, while the total unoccupied
rate stays flat. The model uses "empty" as vacancy, so the series has a break.

This break alone explains the review's 19% hindcast failure (C5). It inflates
the long-run replacement rate from about 0.09% to 0.154% of stock per year,
and it is the real reason the MC vacancy range reaches 8.1% (C7). Two
independent routes that do not depend on the split both give about
0.09%/yr:
* the census dwelling-count identity, which uses no household data;
* the household identity with a constant empty share.

---

## C1: Two engines

### (a) Verification

**Claim confirmed.** `MonteCarlo.validate()` compares the engine with
`Boss.main()` only at `central(su)`. There, regime = 0, the vacancy target
equals the 2023 value (no drift), size = 1, z = 0 (no population spread;
Medium variant) and the slope offsets are 0.

`c1_engine_equivalence.py` compares the engines at every off-centre point
Boss can also express:

| MC setting \| Boss setting | MC Mm² | Boss Mm² | difference |
|---|---|---|---|
| completion 0.92 / 0.96 | 73.20 / 77.88 | 73.20 / 77.88 | 0.00% |
| φ 0.5 / 0.95 | 81.21 / 70.64 | 81.21 / 70.64 | 0.00% |
| k(occupied) \| `HH_CENSUS_REBASE='occupied'` | 77.85 | 77.85 | 0.00% |
| z = −1.645 \| 5th pct + Low S | 59.80 | 59.80 | 0.00% |
| z = +1.645 \| 95th pct + High S | 94.79 | 94.79 | 0.00% |
| regime = 1 \| `DEMOLITION_CALIB_START=2019` | 90.90 | 90.75 | **+0.17%** |
| k = 1 \| `HH_CENSUS_REBASE=None` | 72.65 | 73.96 | **−1.78%** |

So the engines agree exactly wherever both can express a setting, with two
exceptions:
* **regime = 1.** Boss re-estimates the persistence ρ over the calibration
  window, which here is 2019–2023 (n = 5, ρ = 0.07). The MC keeps the
  1992–2023 value (ρ = 0.50). Neither engine is wrong; they are different
  models.
* **k = 1.** The MC calibrates the stock to 2023 on consent-derived
  households; Boss forbids this combination (see C7).

### (d) What the review missed

1. **Seven of the 12 MC inputs have no Boss counterpart at all:** vacancy
   drift, the dwelling-size multiplier, the two slope offsets, pre-2013 share
   and RV share as free inputs, and the carbon bootstrap. z has a counterpart
   only at three points. Equivalence on "≥200 random draws" is therefore
   impossible until Boss can express every MC input. The review's fix quietly
   presupposes the unification it proposes.
2. **The MC engine reads mutable Boss module globals at call time.**
   `project()` calls `B['calibrate_stock']`, a closure inside `Boss.main()`
   that looks up `DEMOLITION_CALIB_START`, `COMPLETION_RATE` and
   `DEMOLITION_RATE` when it is called. Any code that changes a Boss setting
   before the MC runs silently changes the MC. I hit this while building the
   comparison: a leaked `DEMOLITION_CALIB_START=2019` produced a spurious
   +22.8% "discrepancy" at z = −1.645. That was an artefact of the test
   harness, not of the model, but the same leak is possible in any interactive
   session (e.g. Spyder, which the code comments mention).
3. The MC assumes total = dwellings × D, i.e. the clip in
   `extra_space = max(dHH × (D − occupied area), 0)` never binds. On the
   median path, occupied area / D ≤ 0.69. A size multiplier below 0.69 would
   break the equivalence. The lognormal puts about 1e-7 probability there, so
   this is irrelevant in practice, but a unified function should assert it
   rather than assume it.
4. `validate()` checks floor area, carbon and RV units, but not upfront
   carbon, households or S, which are also MC outputs. They agree
   (upfront 21,861.68 kt in both), but this is not tested.

### (b) Is the proposed fix sound?

**Yes.** One pure forward function, with the two old engines retired only
after equivalence on random draws, is standard code verification. It follows
Oberkampf & Roy (2010, ch. 2 and 5) and is what the software literature calls
a characterization or "golden master" test of legacy code (Feathers 2004).

**Recommended strengthening:**
* **Boss itself** should become a thin wrapper around the pure function. Then
  there is one engine by construction, not two engines kept in step.
* The pure function should take **every** input explicitly (no module
  globals). It should return floor area, carbon, upfront carbon, RV units,
  households and S.
* Equivalence should be proved in two layers:
  1. old `Boss.main()` against the new function, on random draws of the
     settings Boss can express (completion, φ, k, window, variant, percentile,
     trend window, size reference);
  2. old `MonteCarlo.project()` against the new function, on ≥200 random
     draws of all 12 MC inputs.

  Tolerance 1e-9 relative, as now.
* The MC-only features (vacancy drift, size multiplier, slope offsets) have
  no independent reference. They need identity tests instead, e.g. "Δstock =
  built − net replacement" and "shares sum to 1".

### (c) Effect

None on the central run. On the MC, the one real divergence is the k = 1
region, analysed under C7.

---

## C2: Household-size tail

### (a) Verification

**Confirmed, with two corrections.**

* The knots (Medium): 2018 2.7301, 2023 2.7045, 2028 2.6912, 2033 2.6737,
  2038 2.6662, 2043 2.6701. The last published knot is 2043.
* S (rebased) is 2.6251 in 2040 and 2.6406 in 2050, as the review says.
* All consolidation savings (1.295 Mm²) fall in 2039–2050, as the review says.

**Correction 1: the extension is not the 2038→2043 slope.** The code
extrapolates PCHIP's *one-sided end derivative*, estimated as
(f(2043) − f(2042.5)) / 0.5. That derivative is **+0.00191/yr**, 2.5× the
2038→2043 secant slope (+0.00077/yr). The mean 2018–2043 slope is
−0.00240/yr. So the extension amplifies the uptick, rather than just
continuing it.

**Correction 2: part of the effect is in the published data, not the
extrapolation.** Of the 1.295 Mm² of consolidation, 0.300 Mm² falls in
2039–2043, which lies inside the knots. Only 0.994 Mm² comes from the
2044–2050 extension. The uptick is larger than rounding can explain:
* households are published to the nearest 1,000, so each knot's S is uncertain
  by about ±0.0006;
* the 2038→2043 change is +0.0039, against a maximum rounding effect of
  ±0.0012.

**Total vs private-household population.** This cannot be tested with the
inputs in the repository. `Householddata.xlsx` gives households only; the
paired population is the total resident population, which includes people in
non-private dwellings such as aged care. The data needed are in NZ.Stat
"National family and household projections, population by living arrangement
type, age, and sex, 2018(base)–2043". The workbook's own contents page lists
this table.

What the inputs do show (Table 4 of the subnational file, Medium) is
consistent with an ageing explanation, but does not prove it. The 65+ share
rises 1.46 points in 2033–38, then only 0.52 in 2038–43 and 0.48 in
2043–48. So the downward pressure of ageing on S weakens just when the uptick
appears. The growth of the 85+ population into aged care would push the
total-population S up at the same time. The two effects cannot be separated
without the private-household population.

### (d) Missed by the review

**The "Low"/"High" size variants mix two kinds of projection.** In
`subnational-population-projections-2018base-2048.xlsx`, footnote 7 says the
national High/Medium/Low rows are the **95th/50th/5th percentiles of the
2020-base stochastic** national projection. The household file's High B /
Low B are **deterministic** variants: fixed fertility, mortality and migration
assumptions. So `statsnz_size_shape('Low')` divides a stochastic percentile by
a deterministic variant. That is not a coherent "low" household size.

This affects `HH_SIZE_VARIANT` (+9.6% / −7.6% in Sensitivity) and the MC's
z-coupling of S. The Medium/50th pairing is the least affected, because the
median of the stochastic projection and the medium deterministic variant are
built to be close. Their closeness is not verified here.

### (b) Is the proposed fix sound?

**As sensitivities, yes.**

* **Holding S flat after 2043** (zero-order hold) is the conventional neutral
  extrapolation when no information exists beyond the horizon.
* **The mean 2018–2043 slope** is less defensible. It continues a decline that
  Stats NZ's own projection says flattens out; it is the opposite bound, not a
  neutral one.
* A third option is more defensible than either: **extrapolate the
  2038→2043 secant** instead of the PCHIP end derivative. This removes the
  amplification (correction 1) without discarding Stats NZ's last interval.

**Better alternative (standard method).** Stats NZ projects households with
living-arrangement-type propensities by age and sex, applied to a projected
population (see the "data and methods" note cited in the workbook). The
standard way to extend beyond 2043 is to:
1. hold the 2043 propensities constant;
2. apply them to the **2024-base** population projection by age and sex to
   2050.

This is the headship- or propensity-rate method. It also repairs the vintage
mismatch: the 2018-base shape currently rides on a 2024-base population.

It needs age-by-sex propensities (the NZ.Stat table above) and the 2024-base
age–sex projection. If Stats NZ has since released 2023-base household
projections, they supersede all of this. I could not check this; please
verify.

### (c) Effect (full run)

| tail after 2043 | floor area | carbon | S 2050 | consolidation |
|---|---|---|---|---|
| adopted (PCHIP end derivative) | 76.71 | 29,708 | 2.641 | 1.29 Mm² |
| flat | 78.20 (+1.9%) | 30,284 (+1.9%) | 2.628 | 0.30 Mm² |
| mean 2018–43 slope | 80.24 (+4.6%) | 31,079 (+4.6%) | 2.612 | 0.30 Mm² |

The step is unchanged at −22.1%, because the tail starts in 2044.

---

## C3: DHE consistency

### (a) Verification

**Confirmed.** In the published DHE, household growth ÷ previous-year
all-dwelling consents is 0.8850–0.8889 every year from 2019 to 2025.
(The code comment says "0.887–0.889"; 2020 is 0.8850.) Before 2018 the ratio
is 1.06–1.17 (2014–2018), which shows the base-dependent reset.

Two things carry the 2024–25 consent-derived artefact forward:

* **S is anchored on 2025.** S_2025 = 2.6567 on the rebased series.
* **`other_dev_2025` is purely a function of consents.** It is +5,494
  dwellings = 0.95 × consents₂₀₂₅ − ΔHH₂₀₂₅ − model. Since ΔHH₂₀₂₅ =
  k × 0.887 × consents₂₀₂₄, this is exactly the kind of quantity the code
  rejects as an artefact for household size (`HH_SIZE_RESPONSE = False`).
  Carried at ρ = 0.505, it adds 5,599 dwellings over 2026–2050. The review's
  claim holds.

### (b) Is the proposed fix sound?

**Yes, as two flagged options.**

* **Anchoring S on 2023** follows the benchmarking principle the code already
  applies to households. Use the last census-benchmarked value, then Stats NZ's
  shape: S₂₀₂₅ = S₂₀₂₃ × S_StatsNZ(2025) / S_StatsNZ(2023) = 2.6798, against
  2.6567 observed-anchored.
  * **Caveat:** the "2023" value is December 2023. June 2023 is the census
    benchmark, and the extra six months are consent-driven. June-based
    anchoring would need a June population. The ERP is used at 31 December,
    so this is a half-year compromise that should be stated.
* **Dropping `other_dev_2025`** is consistent with rejecting `e_2025`. But it
  **worsens the 2026 step to −29.7%**, because the deviation is what currently
  softens that step. This is a trade-off, not a free improvement: the step is
  a real feature of the demand model (see C4).

**Missed by the review:** check whether Stats NZ has since rebased the DHE
household series on the 2023 census. The code says "there is no 2023
household base yet". If a rebased series now exists, it replaces the whole
k-rebase construction, and should be used in preference to any in-house
rebasing.

### (c) Effect (full run and replica)

| option | floor area | carbon | step 2025→26 | S 2050 |
|---|---|---|---|---|
| adopted | 76.71 | 29,708 | −22.1% | 2.641 |
| S anchored on 2023 (full run) | 76.06 (−0.85%) | 29,454 | −22.7% | 2.664 |
| drop `other_dev_2025` (replica) | 75.99 (−0.94%) | 29,431 | −29.7% | 2.641 |

---

## C4: Completion lag

### (a) Verification

**Confirmed.** Consents in calendar year t count as built in t, both in the
stock identity (`calibrate_stock`) and in the 2025 anchor. The census
cross-check does lag: it uses June-year consents for y0 … y1−1 against March
censuses.

**The review's "0.5–0.78 yr" repeats an artefact in Boss's printout.** The
build duration is Little's law, W = L / λ (Little 1961), with:
* L = dwellings under construction on census night (March);
* λ = consents in that calendar year, counting only the three typologies,
  without RV units.

In 2023 consents were falling fast (49.5k in 2022 → 37.2k in 2023), so
dividing a March stock by the flow of the following nine months inflates W.
With λ = all dwellings consented in the 12 months **to the census month**:

| census | 1991 | 1996 | 2001 | 2006 | 2013 | 2018 | 2023 |
|---|---|---|---|---|---|---|---|
| W, Boss printout | 0.55 | 0.46 | 0.45 | 0.54 | 0.49 | 0.52 | **0.78** |
| W, 12 months to March | 0.46 | 0.49 | 0.47 | 0.53 | 0.56 | 0.51 | **0.58** |

The mean construction duration is therefore about 0.5 yr, stable over three
decades.

**Missed by the review:** W is the time spent **under construction**, not the
consent-to-completion lag. Consented-but-not-started dwellings are not in the
census count. W is therefore a lower bound on the lag the model needs. The
consent-to-start delay is not observable from these inputs.

### (b) Is the proposed fix sound?

**Yes, in principle.** A distributed lag applied identically to the historical
identity and to the anchor is the standard treatment (Koyck 1954; Almon 1965).
With a mean lag W < 1 yr and consents spread evenly through the year, the
simplest kernel is two-point:

  built_t = c × [(1 − W) × consents_t + W × consents_{t−1}].

**Limitations to state:**
* Only the mean is identified (by Little's law). The kernel shape is an
  assumption.
* The consent-to-start delay makes the true mean larger.
* Proper identification needs **completion data**, e.g. code-compliance
  certificates. Greenaway-McGrevy & Jones (2023), already cited in the code,
  use such data; whether their series can be obtained is for you to check.

**What the lag can and cannot do.** In the forward years the model projects
completions directly, so the lag affects the projection only through:
* the calibration;
* the 2025 comparison value;
* the carried 2025 deviation.

**It cannot remove the step.** The step comes from demand: census-consistent
household formation of about 21,000/yr against 2021–25 building. A short-run
supply constraint (completions in 2026 are largely fixed by consents already
issued) is a different model: a stock-flow model in which excess completions
raise vacancy. That would be a structural change, not a lag.

**A cheaper and more direct check:** Stats NZ publishes monthly consents with
about a one-month lag, so 2026 year-to-date consents should now exist. They
would show whether 2026 is tracking the model's step.

### (c) Effect (replica)

| lag weight W | net replacement | 2025 deviation | floor area | carbon | step |
|---|---|---|---|---|---|
| none (adopted) | 0.154% | +5,494 | 76.71 | 29,708 | −22.1% |
| 0.25 | 0.146% | +4,960 | 76.31 (−0.5%) | 29,551 | −20.1% |
| 0.50 | 0.137% | +4,427 | 75.90 (−1.1%) | 29,394 | −18.5% |
| 0.78 | 0.127% | +3,830 | 75.03 (−2.2%) | 29,055 | −17.9% |

---

## C5: Replacement–mix coherence

### (a) Verification

**The hindcast number is confirmed. Its interpretation is not.**
`c5_hindcast.py` fits the model on 1992–2013 and feeds in actual households
and vacancy. The constant long-run rate under-predicts dwellings built in
2014–2023 by **18.9%** (276,609 vs 340,888).

The review reads this as an intensification or redevelopment regime linked to
townhouses. The interval-by-interval data say otherwise:

| census interval | net replacement, household identity (as coded) | net replacement, dwelling counts only | townhouses per 1000 stock/yr |
|---|---|---|---|
| 1991–96 | +0.256% | +0.068% | 3.05 |
| 1996–01 | −0.058% | −0.103% | 2.28 |
| 2001–06 | −0.049% | +0.017% | 1.78 |
| 2006–13 | +0.019% | +0.098% | 0.87 |
| **2013–18** | **+0.389%** | **+0.078%** | 2.40 |
| 2018–23 | +0.355% | +0.334% | 7.50 |

* The household identity puts the jump in **2013–18**, when townhouse building
  was modest. The household-free dwelling-count identity puts it only in
  **2018–23**.
* The 2013–18 spike in the household identity is produced by the vacancy
  series falling from 8.09% to 5.26% between the 2013 and 2018 censuses: a
  definitional break (N1), not fewer empty homes.
* With a constant empty share, the same hindcast errs by only **+0.9%**
  (2013 share) or **−0.1%** (2018/23 share).

**The 19% failure is therefore almost entirely the vacancy break.** The
2018–23 rise, by contrast, is real and robust to the definition: +0.351%
(constant share), +0.355% (as coded), +0.334% (dwelling counts).

### (b) Are the proposed fixes sound?

**(B) Structural link** (net replacement = base + demolitions per infill
townhouse × townhouses): **not identifiable from these data.**
* On all six census intervals, b = 0.54 (SE 0.35, t = 1.54, df = 4).
* The 2018–23 interval has leverage 0.92, so the fit is one observation.
* Re-fitting without it gives b = 1.34. As a forecast rule it fails its own
  test: calibrated to 2018, it over-predicts 2019–23 by **+23.5%**.
* Under a constant empty share: b = 0.55, t = 1.88.
* It also assumes a causal direction (infill causes demolition) that
  aggregate data cannot establish. Evidence would have to come from
  parcel-level redevelopment data (demolition consents matched to new-dwelling
  consents on the same site).

**Recommendation: do not implement (B).** At most, report it descriptively
with the identifiability numbers above.

**(A) Coherent scenario pairing:** acceptable, but better done as explicit
scenarios than as one shared random variable.
* Driving the regime and φ from one latent variable assumes perfect rank
  dependence, which nothing in the data supports.
* Once inputs are dependent, standard Sobol indices no longer decompose
  variance cleanly. It would need grouped indices (Jacques et al. 2006) or
  Shapley effects (Owen 2014; Song et al. 2016). A rank correlation induced
  by Iman–Conover (1982) is the standard way to impose partial dependence,
  but its coefficient would itself be unsupported.
* Because "does the 2018–23 regime persist?" is a **structural** question
  with one data point, the conventional treatment is to report **scenarios**
  (e.g. long-run / recent-regime storylines, each with its own consistent φ)
  and run the MC *within* each scenario (Morgan & Henrion 1990, ch. 6 on
  model/structural uncertainty). A Uniform(0, 1) mixing weight turns
  ignorance into a probability; that is the current approach, and it moves the
  MC median by +4.3 Mm² (C7).

**Formal hindcast.** The review's request is sound. The standard form is a
**rolling-origin evaluation** (Tashman 2000) with origins at census years.
Only three origins exist (2006, 2013, 2018). The errors are therefore
descriptive, not a test, and should be reported as such.

The results so far:

| method | origin 2013, test 2014–23 | origin 2018, test 2019–23 |
|---|---|---|
| constant long-run rate | −18.9% | −12.0% |
| most recent intercensal rate | −19.7% (2006–13 rate) | +1.7% (2013–18 rate) |
| linked townhouse model | −2.1% (n = 4 intervals) | +23.5% (n = 5) |

The "recent rate" success at origin 2018 is itself contaminated: the 2013–18
rate it uses is the artefact.

### (c) Effect

The regime question is real, but narrower than the review suggests:
* a single elevated interval (2018–23, about 0.33–0.35%/yr);
* against a long-run rate of about 0.09%/yr once N1 is corrected (not
  0.154%).

Full persistence of the recent regime gives +18.3% under the current
calibration (Sensitivity). Measured from the corrected long-run base, the gap
would be larger.

---

## C6: Soil carbon

### (a) Verification

**Confirmed.**
* `T_BASELINE_2025 = embodied materials + SOC_avg` is applied to every m²,
  including the demolition-replacement and residual bands.
* Soil is 2,903 kt (9.8% of 29,708).
* Of that, **482.5 kt** sits on the replacement bands (demolition 395.7,
  residual 86.8); the remaining 2,420.8 kt is on all other bands.

The weighting could not be checked. Sheet 3 of `building_data.xlsx` holds only
the per-order values and the aggregate (58.77). The area weights are not in
the repository.

### (d) Missed by the review

1. **Only 10 soil orders are listed.** The New Zealand Soil Classification
   has 15 orders (Hewitt 2010). Anthropic, Pallic, Podzol, Pumice and
   Semiarid are absent, and Pallic, Podzol and Pumice are extensive. Whether
   they were dropped, merged or re-normalised decides what "area-weighted"
   means. Please check the source of the 58.77 figure.
2. **The disturbance boundary is the building footprint only**
   (L_w / FSI). Greenfield subdivision strips topsoil across roads, sections
   and earthworks, not only under buildings. For greenfield land, L_w / FSI is
   therefore likely an *under*-estimate per dwelling; for infill, an
   *over*-estimate. The review's greenfield share addresses the second effect
   but not the first.
3. **Timing.** IPCC Tier 1 methods spread a soil-carbon stock change over a
   default 20-year transition (IPCC 2006, Vol. 4, ch. 2). The model books it
   all at construction. For cumulative 2026–2050 totals, this front-loads
   emissions from late-period conversions. It is a convention to state, not an
   error.
4. A_2 duplicates A_1's footprint as well (identical FSI, 10.660677), so the
   apartment soil factor also rests on one case (it is only 5.5 kg/m²).

### (b) Is the proposed fix sound?

**Yes.** Zero soil on the replacement bands follows the land-use-change
accounting logic of the IPCC Guidelines (Vol. 4, ch. 8, Settlements):
conversion emissions arise only on land converted *to* settlements, not on
settlements remaining settlements. For the rest:
* a greenfield share g, with an explicitly stated distribution, is the right
  structure;
* development-weighted soil-order shares from Land Cover Database change ×
  S-map are the right data.

Note that S-map does not yet cover all of New Zealand. For unmapped areas the
Fundamental Soil Layers are the usual fallback. Please check this for your
development areas.

The code would use **clearly marked placeholders** for g and the shares (no
invented values). One design choice for you: whether the vacancy-allowance and
extra-space bands count as "new land" (share g) or whether g applies uniformly
to all non-replacement floor area.

### (c) Effect (from the band split; exact because soil is linear)

With soil zeroed on replacement and g applied to the remaining 2,420.8 kt:

| g (greenfield share) | 0 | 0.25 | 0.50 | 0.75 | 1.0 |
|---|---|---|---|---|---|
| total carbon (kt) | 26,805 | 27,410 | 28,015 | 28,620 | 29,225 |
| change | −9.8% | −7.7% | −5.7% | −3.7% | −1.6% |

This is before any change to the soil-order weighting, which could move soil
in either direction (the Raw-to-Organic range is −5.3% to +22.5%).

---

## C7: Monte Carlo input distributions

### (a) Verification

**All five sub-claims are confirmed.** The attribution below re-runs the same
10,000-draw Latin hypercube with **one** input fixed at its adopted value
(`c7_mc_median_attribution.py`).

| input | adopted | distribution median / mean | MC median with this input fixed | shift in MC median caused by the input |
|---|---|---|---|---|
| regime | 0 | 0.5 / 0.5 | 76.39 | **+4.27** |
| vacancy target | 5.53% | 6.19% / 6.29% | 77.93 | **+2.74** |
| φ | 0.80 | 0.80 / 0.80 | 81.18 | −0.52 (curvature, not centring) |
| RV share | 5.64% | 5.88% / 5.95% | 80.99 | −0.33 |
| completion | 0.95 | 0.94 / 0.94 | 82.14 | **−1.48** |
| k (census rebase) | 0.826 | 0.863 / 0.870 | 84.38 | **−3.71** |
| z, slopes, size, pre-share | centred | – | ±0.1 | ≈0 |

The MC median (80.66) sits 3.95 Mm² above the central run (76.71). The shifts
are not additive, because the median is non-linear.

**Population is centred correctly.** With only z sampled, the MC median is
76.71, equal to the central run. The gap therefore comes entirely from the
non-population inputs.

Findings per sub-claim:
* **regime U(0, 1) vs adopted 0:** confirmed; the largest single cause (+4.3).
* **vacancy upper bound:** confirmed that 8.09% (2013) is the maximum; the
  review's **reason is wrong**. Canterbury's 2013 empty rate was 9.82%, and
  excluding Canterbury the national rate is 7.82%. The earthquake therefore
  explains 0.27 of the 2.56–2.83-point gap to 2018/2023. The rest is the
  empty/away definitional break (N1). On one consistent definition, 2013, 2018
  and 2023 fall within 0.29 points of each other with the 2018/23 empty share
  (5.27 / 5.25 / 5.54%), or within 0.45 points with the 2013 share
  (8.09 / 8.05 / 8.50%).
* **completion mean 0.94 vs 0.95:** confirmed (−1.5).
* **k upper bound 1 with calibration to 2023:** confirmed. At k = 1 the MC
  gives 72.65 against Boss's legitimate `HH_CENSUS_REBASE=None` (calibrated to
  2018) 73.96, i.e. −1.8% at that end. k's asymmetric range pulls the MC
  median **down** by 3.7.
* **φ:** confirmed. The docstring cites [0.80, 0.98] but samples a
  triangular(0.62, 0.80, 0.98): the same width, re-centred on 0.80. Half of
  all draws are below the lower end of the cited range.
* **annual bands:** confirmed. `np.percentile(fan, p, axis=0)` gives marginal
  quantiles per year, and the figure labels them simply "5th–95th percentile".

### (d) Missed or got wrong

1. **The existing `docs/MODEL_REVIEW.md` §1.4 gets a direction wrong.** It
   lists "household rebase: the central k is near the low end of its range"
   as a reason the MC median is **above** the central run. The attribution
   shows the k range pulls the median **down** by 3.7. It is the regime,
   vacancy and (net) other inputs that push it up.
2. **The φ range is borrowed from a different setting.** Hyndman &
   Athanasopoulos's 0.80–0.98 is the range to which φ is *restricted when it is
   estimated* in exponential-smoothing models. Here φ is not estimated, and it
   damps a compositional trend. What φ actually controls is how many years of
   slope are applied by 2050: 1.6 years at φ = 0.62, 4.0 at 0.80, 19.4 at 0.98.
   **A better approach:** elicit the uncertainty on an interpretable
   observable, the 2050 townhouse share (O'Hagan et al. 2006), and derive φ
   from it.
3. **Small-sample HAC.** The mix slopes use Newey–West standard errors with
   n = 14 and lag 2. The AR(1) effective sample sizes are about 6
   (townhouses, r₁ = +0.40) and about 3 (apartments, r₁ = +0.64). HAC
   estimators are unreliable at this size (Kiefer & Vogelsang 2005). The
   AR(1)-inflated standard errors are 13% and 49% larger than the HAC ones.
   **Immaterial here:** both slope inputs have total Sobol index ≤ 0.001.
   State the limitation rather than engineer around it.
4. **Sobol bootstrap CIs are unseeded** (N3).
5. **Soil is not sampled.** The soil-order extremes are treated as a bounding
   scenario. That is defensible, but the MC interval then excludes a known
   uncertainty of −5% to +22% on carbon. This must be stated next to the
   interval.
6. **The dwelling-size σ measures history, not the future.** σ = 0.068 is the
   RMS log deviation of 2016–2025 sizes from the 2023–25 level. Detached size
   fell from 208.7 to 178.2 m² over 2016–2025, so σ mostly measures that
   one-way historical trend. It is then applied symmetrically in log space.
   Acceptable as a stated assumption, but it is not an estimate of forecast
   uncertainty.
7. **The carbon bootstrap understates variance.** With 4–6 cases per sub-type,
   the bootstrap variance of a mean is biased low by the factor (n − 1)/n
   (about 13% on the SE for n = 4; Efron & Tibshirani 1993). It also assumes
   the case studies are a random sample of NZ construction, which
   `Building_factors.py` itself says they are not.

### (b) Is the proposed fix sound?

**Yes. The table of every input is necessary.** On the choice between
"centre on the adopted value" and "declare the MC median the baseline", the
metrology standard for Monte Carlo propagation (JCGM 101:2008, "GUM
Supplement 1") takes the estimate of the output from the propagated
distribution, not from the model at best-estimate inputs. Both options are
defensible if stated. What is not defensible is the current situation: the
two differ by 5% for reasons nobody chose deliberately.

**My recommendation:**
1. Fix the distributions on evidence first (N1 changes the vacancy input;
   the regime becomes scenarios per C5).
2. Then make the adopted central value the **median** of each input
   distribution.
3. Report the MC median and interval as the result, and the deterministic run
   as "all inputs at their medians".

The remaining difference is then pure non-linearity (Jensen's inequality) and
small.

### (c) Effect

The MC median would move from 80.66 towards the central run, by about 4 Mm²
if all inputs are centred. The width of the interval is dominated by
population (ST 0.62) and is largely unaffected.

---

## C8: Building_factors

### (a) Verification

**Confirmed.**
* Sheet 2 has the columns `ID, Total GFA, OLF, Footprint, Occupants`. There is
  no `GWP` column, so the block "reconciliation against the published
  per-building intensities" (lines 184–195) never runs. Yet the module
  docstring (lines 34–37) says it "prints at runtime".
* A_2 = A_1 × 1.000073 in every material and stage cell, and its footprint is
  scaled too (identical FSI). `n_independent` for apartments is 1, so the
  jackknife range for apartments is zero width (609.73–609.77).

### (d) Missed by the review

1. **The pooling-scheme switch does not work from outside, and one scheme
   crashes.**
   * `pool(..., scheme=WEIGHT_SCHEME)` binds the default when the function is
     defined. Setting `Building_factors.WEIGHT_SCHEME` before `main()` has no
     effect.
   * Forced properly, `equal_buildings` works (detached 360.5 vs 357.9,
     +0.7%).
   * `gfa_weighted` raises `KeyError: 'GFA'`: `chars` has `GFA_used`, not
     `GFA`.
   * The docstring's "all three agree within ~1%" cannot have been produced
     by the current code.
2. The per-building soil column for SD_4 is exactly L_w (FSI = 1.000). That is
   fine, but it shows that the single-storey soil factor is essentially L_w
   itself. Any error in the soil weighting (C6) passes straight through to the
   largest typology.

### (b) Is the proposed fix sound?

**Yes.** "Fail loudly" is standard defensive practice. Better still: **supply
the published per-building intensities**, with their source, so that the
check actually runs. If they are unavailable, delete the claim from the
docstring. Flagging single-case typologies in every output (CSV column, and a
note in the figures and the summary) is right. Apartments are 3.26 Mm² (4.2%)
of floor area and 2,006 kt (6.8%) of carbon, so ±20% on the apartment factor
is ±400 kt (±1.35%).

### (c) Effect

None on the numbers.

---

## C9: Hygiene

### (a) Verification

**All confirmed** (`c8_c9_checks.py`):

* **Stale numbers in comments.** Current code gives:
  * `per_capita` 124.24 (comment 101.98);
  * `per_household` 92.64 (comment 61.77);
  * `extra_space_plus_other` 84.74 (comment "52–63", "62.8");
  * the `FILE_POP_SIZE_PAIR` comment's S(2050) 2.582 and 80.31 Mm², against
    2.641 and 76.71 now.

  The "update"-vintage file that comment compares against is **not in
  `data/`**, so that sensitivity cannot be reproduced.
* **Unused work every run.** The 20,000-draw bootstrap for
  `extra_space_plus_other` runs every time: 0.25 s, about 8% of a Boss run.
  Clutter rather than cost.
* **Two options labelled ADOPTED:** `extra_space_plus_other` (line 294) and
  `stock_vacancy` (line 309).
* **The summary table does not add up.** Growth 41.88 + consumption 32.54 =
  74.42 ≠ 76.71; house-splitting (2.29) is not shown.
* **Hard-coded census counts:** `CENSUS_LATER` (2018, 2023) has no table ID or
  download date. Given N1, these specific numbers now matter and must be
  verified against source.
* **`locals()` as the API:** `state = dict(locals())`.
* **No README, no environment file, no run-all script.**

### (d) Missed by the review

1. **Two printed numbers for the same case.** Boss's "[4] completion rate 92%"
   line is a linearisation (73.05 Mm²); Sensitivity's full re-run gives 73.20.
   Both appear in outputs.
2. The committed `data/montecarlo_annual.csv` is stale (see Step 0).
3. Sobol CIs are unseeded (N3).
4. `Diagnostics.py` runs at import (no `main()` guard). `MonteCarlo.PARAMS` is
   fixed at import from Boss flags, so a later flag change is ignored.
5. Boss's docstring refers to `building_factors.py` (lowercase). The file is
   `Building_factors.py`, which matters on case-sensitive file systems.

### (b) Is the proposed fix sound?

**Yes.** This is standard reproducible-research practice (Sandve et al. 2013):
* pinned environment;
* one command that regenerates every figure and table;
* provenance for every input;
* no numbers in comments that the code does not produce.

**One addition:** stale numbers are best prevented structurally. Have the
run write a results file, and quote that in the paper, rather than hand-copying
numbers into comments.

### (c) Effect

None, except removing the inconsistent 73.05.

---

## Issues the review missed

### N1: The census vacancy series has a definitional break (highest impact)

**Evidence** (`c5_c7_vacancy_break.py`):

| census | unoccupied / all private | empty share of unoccupied | "empty" vacancy used |
|---|---|---|---|
| 2006 | 9.77% | (2013 share applied) | 7.44% |
| 2013 | 10.61% | **76.2%** | 8.09% |
| 2018 | 10.56% | **49.8%** | 5.26% |
| 2023 | 11.15% | **49.6%** | 5.53% |

The total unoccupied rate is flat between 2013 and 2018, but the empty share
falls by 26 points. A behavioural shift of that size in five years is not
plausible. A change in how unoccupied dwellings were classified is the likely
explanation. The 2018 census relied heavily on administrative data, but you
should confirm the cause from Stats NZ's 2018/2023 data-quality notes for
dwelling occupancy status before writing it into the paper.

**Consequences in the model:**
* Vacancy is interpolated from 8.09% down to 5.26% over 2014–2018. The
  "vacancy change" term therefore tells the identity that 55,739
  dwellings were absorbed from vacancy. That shows up as net replacement of
  +0.389%/yr in 2013–18, which the household-free dwelling-count identity
  does not see (+0.078%).
* The long-run calibrated rate (0.154%) includes that artefact.
* The same break is why the MC vacancy range reaches 8.09% (C7) and why the
  hindcast fails (C5).

**Two independent routes that avoid the split agree:**

| calibration of net replacement | rate 1992–2023 | floor area | carbon |
|---|---|---|---|
| adopted (empty, broken series) | 0.154% | 76.71 | 29,708 |
| household identity, constant empty share 49.7% (2018/23) | 0.089% | 71.90 (−6.3%) | 27,843 |
| household identity, constant empty share 76.2% (2013) | 0.028% | 69.61 (−9.3%) | 26,955 |
| **dwelling-count identity** (no household data, no split) | **0.094%** | **72.49 (−5.5%)** | 28,072 |
| dwelling-count, net of pipeline change | 0.061% | 70.10 (−8.6%) | 27,147 |

The 76.2% row also raises forward vacancy to 8.50%, which is why it moves
the most.

**Recommended method.** Calibrate the long-run net replacement from the
**census dwelling-count identity** (Δ census private dwellings vs dwellings
built, census to census). It depends on neither the household estimates nor
the empty/away split. Keep the household identity as the cross-check (the
roles are currently reversed). Keep forward vacancy on the 2018/2023
definition (5.53%), since that is the definition the 2023 households are
benchmarked on. Add a flagged sensitivity with the constant-share household
identity.

**Caveats:**
* The dwelling-count identity depends on the 2018 census dwelling count, a
  census with known coverage problems.
* It uses June-year consents against March censuses.

### N2: The MC engine depends on mutable Boss module globals (C1, point 2)

### N3: Sobol bootstrap confidence intervals are not reproducible

`res.bootstrap(confidence_level=0.95, n_resamples=999)` is called without an
`rng`. The fix is a one-line seed.

### N4: The "Low/High" household-size variants mix stochastic percentiles with deterministic variants (C2)

### N5: The 2023 build duration of 0.78 yr is a timing artefact (C4)

### N6: Soil table covers 10 of 15 soil orders; soil disturbance limited to the footprint (C6)

### N7: `Building_factors` pooling switch is ignored when set from outside, and `gfa_weighted` crashes (C8)

### N8: `docs/MODEL_REVIEW.md` §1.4 attributes the MC–central gap partly to the wrong input (C7)

---

## Proposed Step 2 plan (for your approval)

Rules as you set them:
* one change per commit;
* every new behaviour behind a flag, with the old behaviour kept as a
  sensitivity;
* after each change, a full pipeline re-run and a CHANGELOG before/after table;
* seeds fixed;
* no parameter tuned to reach a target.

The order puts no-change infrastructure first, so that every later change is
implemented **once**, in one engine, and measured by one script.

| # | change | flag / default | claims |
|---|---|---|---|
| 1 | `requirements.txt` (pinned), `run_all.py` (headless, saves all figures to `figures/`), CHANGELOG with baseline row; seed the Sobol bootstrap | none; numbers unchanged except Sobol CIs | C9, N3 |
| 2 | Tests for identities: stock identity closes; bands sum to total; material + soil = typology; shares sum to 1; history reconstructed | none | C9 |
| 3 | One pure forward function taking all inputs explicitly; Boss and MC both call it; equivalence proved on ≥200 random draws against the **old** engines before the MC engine is deleted; `validate()` extended to upfront, households, S | none; must reproduce 76.71 / 80.66 exactly | C1, N2 |
| 4 | Net-replacement calibration source: `'household_identity'` (old) \| `'dwelling_count'` \| `'household_constant_empty_share'` | **your choice of default** | N1, C5, C7 |
| 5 | S tail after last knot: `'pchip_end_slope'` (old) \| `'secant'` \| `'flat'` \| `'mean_slope'` | your choice | C2 |
| 6 | S anchor year: 2025 (old) \| 2023; `CARRY_2025_STOCK_DEVIATION` True (old) \| False | your choice | C3 |
| 7 | Completion lag: `COMPLETION_LAG_WEIGHT` 0 (old) \| W from Little's law (12 months to March); Boss's build-duration printout corrected | your choice | C4, N5 |
| 8 | Soil: zero on replacement bands; `GREENFIELD_SHARE` = **placeholder, clearly marked**; hook to read `data/soil_order_shares_development.csv` (placeholder file with the expected columns, no values) | old behaviour default until you supply data | C6, N6 |
| 9 | MC inputs: table of every input (adopted, distribution, source, rationale); vacancy on one definition; φ elicited on the 2050 townhouse share or restricted and justified; completion and k centred or justified; regime as **scenarios** with the MC inside each; bands labelled marginal | your choice on centring vs "MC median = baseline" | C7, C5 |
| 10 | Hindcast module: rolling origins 2006/2013/2018 for constant, recent and linked rates, reported descriptively | none (report) | C5 |
| 11 | Building_factors: loud failure when a documented check cannot run; `n_independent` and a single-case flag carried into outputs; pooling switch fixed (`gfa_weighted` repaired) | none on the central run | C8, N7 |
| 12 | Hygiene: stale comments removed or regenerated; one ADOPTED label; summary table shows house-splitting; census counts moved to a sourced CSV; `locals()` replaced by an explicit result object; `Diagnostics` `main()` guard; `[4]` linearised lines replaced by re-runs or labelled; README with provenance; MODEL_REVIEW §1.4 corrected | none | C9, N8 |

**Decisions I need from you before starting:**
1. Approve, reorder or drop items.
2. For item 4 (N1): which calibration should become the default, or keep the
   old default and report the others as sensitivities until the Stats NZ
   classification question is answered?
3. For item 9: centre the MC inputs on the adopted values, or declare the MC
   median the headline? And scenarios vs a probabilistic regime weight?
4. Should regenerated outputs keep living in `data/` (mixed with inputs), or
   move to `outputs/`?

## External data that would be needed (none will be fabricated)

| # | what | where from | for |
|---|---|---|---|
| E1 | 2018 and 2023 census dwelling occupancy counts (occupied, empty, residents away, under construction), table IDs and download dates, plus Stats NZ's data-quality notes on how "empty" vs "residents away" was classified | Stats NZ census tables / Aotearoa Data Explorer; 2018 and 2023 Census data-quality documentation | N1, C9 (verifies `CENSUS_LATER`) |
| E2 | Population by living-arrangement type (private households vs non-private dwellings), by age and sex, 2018(base)–2043 | NZ.Stat: "National family and household projections, population by living arrangement type, age, and sex, 2018(base)-2043" (named on the workbook's Contents sheet) | C2 |
| E3 | Whether Stats NZ has published (i) DHE households rebased on the 2023 census and/or (ii) 2023-base household projections | Stats NZ release calendar | C2, C3 |
| E4 | 2024-base national population projection by age and sex to 2050 (if the propensity-rate extension is wanted) | Stats NZ | C2 |
| E5 | Development-weighted soil-order shares (your GIS: LCDB change × S-map/FSL) and the provenance of the current 58.77 average | your analysis; Manaaki Whenua | C6 |
| E6 | A greenfield share of new floor area (or new dwellings), with its source and uncertainty | to be identified: e.g. LCDB urban-expansion area against consents; council capacity reports | C6 |
| E7 | A consent-to-completion lag distribution (code-compliance-certificate data) | e.g. data behind Greenaway-McGrevy & Jones (2023), or Stats NZ if published | C4 |
| E8 | 2026 year-to-date monthly consents | Stats NZ building consents | C4 (observed check on the step) |
| E9 | Published per-building intensities for the 16 case studies, with source | the case-study publications | C8 |
| E10 | The "-update" 2018-base subnational population file, if that sensitivity is to be kept | Stats NZ | C9 |
| E11 | (optional) Demolition consents, national or for the main councils | councils / BRANZ | C5, N1 |

---

## References

I have included only works I am confident exist. Please check the details
(volume, pages, edition) before citing, as the previous review also advised.
References already cited in the code (BRANZ SR214; Jones, Greenaway-McGrevy
& Crow 2024; Greenaway-McGrevy & Jones 2023; Napiontek et al. 2025) were not
re-checked.

- Almon, S. (1965). The distributed lag between capital appropriations and expenditures. *Econometrica*, 33(1), 178–196.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- Feathers, M. (2004). *Working Effectively with Legacy Code*. Prentice Hall.
- Hewitt, A. E. (2010). *New Zealand Soil Classification* (3rd ed.). Landcare Research Science Series 1. Manaaki Whenua Press.
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts.
- Iman, R. L., & Conover, W. J. (1982). A distribution-free approach to inducing rank correlation among input variables. *Communications in Statistics – Simulation and Computation*, 11(3), 311–334.
- IPCC (2006). *2006 IPCC Guidelines for National Greenhouse Gas Inventories*, Vol. 4: Agriculture, Forestry and Other Land Use (ch. 2 generic methods; ch. 8 Settlements). IGES.
- Jacques, J., Lavergne, C., & Devictor, N. (2006). Sensitivity analysis in presence of model uncertainty and correlated inputs. *Reliability Engineering & System Safety*, 91(10–11), 1126–1134.
- JCGM 101:2008. *Evaluation of measurement data – Supplement 1 to the "Guide to the expression of uncertainty in measurement" – Propagation of distributions using a Monte Carlo method*. BIPM.
- Kiefer, N. M., & Vogelsang, T. J. (2005). A new asymptotic theory for heteroskedasticity-autocorrelation robust tests. *Econometric Theory*, 21(6), 1130–1164.
- Koyck, L. M. (1954). *Distributed Lags and Investment Analysis*. North-Holland.
- Little, J. D. C. (1961). A proof for the queuing formula: L = λW. *Operations Research*, 9(3), 383–387.
- Morgan, M. G., & Henrion, M. (1990). *Uncertainty: A Guide to Dealing with Uncertainty in Quantitative Risk and Policy Analysis*. Cambridge University Press.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708.
- Oberkampf, W. L., & Roy, C. J. (2010). *Verification and Validation in Scientific Computing*. Cambridge University Press.
- O'Hagan, A., Buck, C. E., Daneshkhah, A., Eiser, J. R., Garthwaite, P. H., Jenkinson, D. J., Oakley, J. E., & Rakow, T. (2006). *Uncertain Judgements: Eliciting Experts' Probabilities*. Wiley.
- Owen, A. B. (2014). Sobol' indices and Shapley value. *SIAM/ASA Journal on Uncertainty Quantification*, 2(1), 245–251.
- Saltelli, A., Annoni, P., Azzini, I., Campolongo, F., Ratto, M., & Tarantola, S. (2010). Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index. *Computer Physics Communications*, 181(2), 259–270.
- Sandve, G. K., Nekrutenko, A., Taylor, J., & Hovig, E. (2013). Ten simple rules for reproducible computational research. *PLoS Computational Biology*, 9(10), e1003285.
- Song, E., Nelson, B. L., & Staum, J. (2016). Shapley effects for global sensitivity analysis: theory and computation. *SIAM/ASA Journal on Uncertainty Quantification*, 4(1), 1060–1083.
- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: an analysis and review. *International Journal of Forecasting*, 16(4), 437–450.

---

# Addendum (round 2): assessment of F1–F3, D1–D4, A1–A6

Network note: every Stats NZ host (`www.`, `datainfoplus.`, `explore.data.`,
`infoshare.`, `api.data.`, `nzdotstat.stats.govt.nz`) and the mirrors
(`scoop.co.nz`, `figure.nz`) are blocked by this environment's egress policy.
The facts below were checked against search-engine excerpts of the cited
pages and against Stats NZ files already in `data/`. They were **not** checked
against the pages themselves.

**F1 (cause of N1): consistent with the evidence, but only partly verified.**
The search excerpt of the DataInfo+ page for "Dwelling occupancy status"
says two things:
* administrative data used to show that non-responding dwellings were usually
  occupied "may have contributed to the occupancy classifications";
* "the change in the proportion of unoccupied residents away versus
  unoccupied empty indicates a break in the time series", while national
  occupied/unoccupied proportions are "consistent with expectations".

That matches the data: the empty share was 76.2% in 2013, 49.8% in 2018 and
49.6% in 2023, with a flat total. It also shows that 2018 and 2023 are on the
same basis. The statement "received no quality rating" was **not visible in
the excerpt**; please confirm the wording before it is quoted. The docs will
cite the URL, marked "accessed via search excerpt, <date>" until confirmed.

**F2 (2026 consents): confirmed in substance.**
* The excerpt of the release gives 40,908 new dwellings consented in the year
  ended July 2026 (+21% on 33,879).
* Our `consentdata.xlsx` reproduces the 33,879 for the year ended July 2025
  exactly. This shows our `Dwellings` column is the published headline series,
  RV units included.
* Boss's 2026 is 26,673 in-scope built = 28,266 all-category built = 29,754
  consent-equivalents: 27.3% below the year ended July 2026.
* The N1 correction lowers it slightly. The replacement term falls by about
  1,300, but the carried 2025 deviation rises by about 1,260 × 0.5, which
  partly offsets it. The exact figure is to come at item 4.
* The June-2026 figure of 40,581 was not in any excerpt; please confirm it.
* Download instructions are in the table at the end of this addendum.
  Please also send the release's month and date.

**F3 (2023-base household projections, late 2026): confirmed in substance.**
The excerpt of "Dwelling and household estimates: March 2026 quarter" says:
* household estimates will be rebased after the 2023-base family and household
  projections, which are planned for late 2026;
* dwelling estimates are already on a 2023 base;
* that release revised 2018–2025 dwelling and household estimates to remove
  dwellings under construction.

Our `oldhouseholddata.xlsx` **is** that release (Contents: "March 2026
quarter", published 7 April 2026), so the revision is already in the inputs.
Agreed: the household-size source and the k-rebase will sit behind one input
switch (`HOUSEHOLD_SOURCE`).

**D1 (order): agree.** One dependency to note:
* A1's gap and its decay depend on the S anchor (item 6) and the completion
  lag (item 7).
* Because A1's quantities are computed at run time, the CP2 state is the same
  whatever the order; only the per-commit attribution in the CHANGELOG
  changes.
* I will follow your order and say so in the CP2 note.

**D2 (dwelling-count identity as default): agree.** Evidence and caveats:
1. **The 1991–2023 ratio of sums is already almost independent of 2018.** The
   interval changes telescope: Σ(built − ΔD) = Σ built − (D₂₀₂₃ − D₁₉₉₁).
   The 2018 count enters only through the stock-year weights in the
   denominator, and 2013–2023 behaves the same way. The two "2018-free"
   variants will be reported, but expect them to be close to the default.
2. **Census totals are consistent with the DHE bases, but the split is not
   verified.** The DHE private-dwelling series (Table 1, footnote: "base = the
   census count of occupied private dwellings plus unoccupied dwellings")
   agrees with the census totals to within 0.12% for 1991–2018 and 0.23% for
   2023. For 1991–2013 the DHE figure at 31 March is 1,300–2,000 **above**
   the census; for 2018 it is 2,219 and for 2023 4,581 **below**. That change
   of sign is unexplained. A 6,000-dwelling error in 2023 would move the
   1991–2023 rate by about ±0.012 percentage points.

   **The empty/away split and the under-construction counts in
   `CENSUS_LATER` cannot be verified from anything in the repository.** Per
   D2, I stop before item 4 until E1 is supplied or the Stats NZ hosts are
   allowed.
3. **[CORRECTED at CP2, see docs/CP2_NOTE.md: with the model's completion rate and lag applied consistently, the weight implies about 0.000%/yr and corroborates no particular rate.]** ~~The DHE intercensal weight corroborates about 0.09%/yr, not 0.154%.~~
   * After the 2023 base, DHE quarterly dwelling growth = **0.8897 ×
     consents lagged four quarters** (sd 0.004, 2023Q3–2025Q4). It is a Stats
     NZ assumption, not an observation. The workbook gives no published factor
     (the DataInfo+ DHE page may; it is blocked).
   * Our identity implies net additions per consent ≈ 0.95 − (rate × stock) /
     consents. At about 35,000 consents and a 2.0 M stock, that is ≈ 0.896 at
     0.094% and ≈ 0.862 at 0.154%.
   * Stats NZ's weight is therefore consistent with the dwelling-count
     calibration. This is corroboration, not proof: completion is folded into
     their weight.
   * The weights implied by the revised intercensal series are 0.75–0.78 in
     2018–23 and about 0.83 in 2013–18. The first is consistent with the
     2018–23 redevelopment regime.
4. **Lag consistency.** The dwelling-count identity currently pairs June-year
   consents with March censuses, an implicit lag of about 0.75 yr. When
   item 7 introduces W, the identity must use the same W: monthly consents in
   (census date − W, next census date − W]. Otherwise the default and the
   cross-check would use different lags.

**D3 (Monte Carlo): agree, with one correction and two notes.**
* **Correction:** JCGM 101:2008 takes the **expectation (mean)** of the Monte
  Carlo output as the estimate, with a probabilistically symmetric or shortest
  coverage interval. A median headline is defensible for skewed outputs, but it
  is our choice, not JCGM 101's. The docs will say "propagation of
  distributions per JCGM 101; the median is reported as the headline because
  the output is skewed; the mean is also reported".
* **Vacancy:** on the 2018/2023 definition there are **two** observations
  (5.26%, 5.53%). Any distribution around them is judgement and will be
  labelled so.
* **The carbon-bootstrap input** has no meaningful "median". The deterministic
  run uses the pooled central factors.
* **φ mapping** (proposal, to be shown at CP3): the 2050 townhouse share is a
  monotone function of φ given the fitted slopes, so a range elicited on the
  share inverts uniquely to φ. The range will be labelled JUDGEMENT.

**D4 (outputs/): agree.** `factors_*.csv` are also derived, so they move to
`outputs/factors/`, and Boss will read them from there. `run_all` enforces
the order.

**Other defaults: agree**, with two notes:
1. W from Little's law (≈0.5 yr; census mean 0.51 over 12 months to March)
   measures **construction duration only**, so it is a lower bound on the
   consent-to-completion lag. This will be stated.
2. The flat S tail and the 2023 anchor will be replaced by the F3 switch once
   Stats NZ publishes.

**A1 (near-term join): preliminary view; the full analysis comes at item A1.**
Evidence from the 2018–23 boom, from census counts only: 190,328 dwellings
built (0.95 × consents, June years). They went to:

| where | dwellings |
|---|---|
| net stock growth | 157,962 |
| more dwellings under construction | 11,181 |
| **net removals (redevelopment)** | **21,185** |
| higher vacancy (empty rate +0.27 points) | only 5,518 |
| households (occupied + away) grew by | 144,135 |

So the boom's excess went mainly into redevelopment and the pipeline, not into
vacancy: **net replacement is pro-cyclical**. This matters for the options:
* **(a) Nowcast.** Identifiable from observed consents, W and the completion
  rate. Excess 2026 building **adds** to the 2026–2050 total unless offset. It
  **uses up** the 2026 out-of-sample check (A2), so A2 must run on a
  no-nowcast diagnostic run and, once the model uses 2026, on months after the
  data cut-off.
* **(b) Partial adjustment.** The persistence of the gap between building and
  requirement from modelled, census-consistent households (pop / S, with S
  interpolated between censuses) is statistically estimable: AR(1), n ≈ 33,
  with small-sample bias to state. But it has no stock consistency. The excess
  simply **adds** to the total, and the estimated persistence mixes supply
  dynamics with the redevelopment regime.
* **(c) Stock-flow vacancy buffer.** Preserves the identity, and the excess is
  largely **offset** within the window. But the drawdown rate is not
  identifiable from two comparable censuses, and the 2018–23 evidence says
  excess building went mostly to removals, not vacancy. A pure vacancy buffer
  would misrepresent the mechanism.
* **Likely recommendation, to be confirmed with numbers at A1:** (a) for 2026
  with a (c)-type stock-consistent treatment, in which the excess is split
  between vacancy and replacement in the 2018–23 proportions (a stated
  assumption), plus (b) as a sensitivity.

**A2: agree.** The 2026 check needs the extended consent file. Until then it
reports "pending data".

**A3, A6: agree.** Both will be generated by `run_all`.

**A4 (RV floor area): open.** Our consent file has no RV floor area: its
`GFA - GFA` equals the sum of the three typologies exactly. Whether Stats NZ
publishes RV floor area could not be checked (blocked). See the table below.

**A5 (E2): agree it is high priority.** The table is named on the Contents
sheet of `Householddata.xlsx`. See the table below for what to download. N4
will not proceed without it.

## Data to download (named items)

| item | where | what to select | notes |
|---|---|---|---|
| **A5 / E2** | NZ.Stat, or its replacement Aotearoa Data Explorer (explore.data.stats.govt.nz) if NZ.Stat has been retired; I could not check which | "National family and household projections, population by living arrangement type, age, and sex, 2018(base)-2043". Projection: Low B, Medium B, High B (other variants too, if offered). All living-arrangement categories, **including any category for people not in private households / in non-private dwellings**. Age: total **and** five-year groups. Sex: total. Years: all (2018–2043) | The key test: if the table's all-category total equals the national population projection at the same knots, it covers the whole population and the non-private share can be read off. If it is smaller, the difference is the non-private population. Please include the table's footnotes. |
| **A4** | Stats NZ Infoshare, "Building Consents Issued – BLD", or the monthly "Building consents issued" release tables | Any table of **new dwellings by building type with floor area**. Check whether "retirement village units" appears with a floor-area measure | Please send the table name/ID. |
| **F2** | Stats NZ building consents, latest monthly release | The same series as `consentdata.xlsx`: monthly counts, floor area and value by type, plus the all-dwellings total, to the latest month | Please keep the same column layout, or send the table IDs. |
| **E1** | Stats NZ | 2018 and 2023 census private dwellings by occupancy status: occupied, unoccupied–empty, unoccupied–residents away, under construction | Needed before item 4. |
