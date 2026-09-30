# CP2 note: the new central baseline, and the 2026 question

Every number here comes from a generated file:
* the baseline walk: `outputs/baseline_walk.md`;
* the 2026 decomposition: `outputs/gap_2026.md`;
* validation: `outputs/validation.md`;
* sensitivities: `outputs/sensitivity_oat.csv`.

All five changes below are behind flags. `tests/legacy_flags.py` restores
the original model, and `tests/test_engine_equivalence.py` checks that the
code still reproduces it exactly.

## 1. How each default moved the central run

| step | floor area 2026–2050 | change | why |
|---|---|---|---|
| CP1 (original numbers) | 76.71 Mm² | | |
| Item 5: household size flat after 2043 | 78.20 | +1.9% | The old tail extended the PCHIP end slope, 2.5× the last published interval. Only 0.30 of the 1.29 Mm² "consolidation" survives, and that part is inside the published knots. |
| Item 6: household size anchored on December 2023 | 77.53 | −0.9% | 2025 households are 0.888 × lagged consents. The anchor is December, not June: a six-month caveat stated at the flag. |
| Item 7: completion lag, Little's law (W = 0.507 yr) | 76.71 | −1.1% | W is time under construction only, so it is a lower bound on the lag. The 2025→2026 step softens from −22.7% to −19.1%. |
| Census 2018/2023 private dwellings only (E1) | 77.05 | +0.4% | The hard-coded counts were all dwelling types. From 2018 they include unoccupied non-private dwellings (4,860 in 2018; 4,710 in 2023). Private-only vacancy is 5.08% (2018) and 5.39% (2023). |
| Item 4: net replacement from census dwelling counts | **75.01** | −2.6% | 0.113%/yr over 1991→2023, against 0.143% from the household identity, which contains the 2013→18 empty/away break. |

**New central run:**
* 75.01 Mm²;
* 29,049 kt CO₂e;
* upfront carbon 21,377 kt;
* 2025→2026 step −19.5%;
* household size in 2050: 2.652.

Retirement villages are reported separately and are out of scope:
4.29 Mm² over 2026–2050.

**Not final:**
* The Monte Carlo still blends the long-run and 2018–23 replacement rates
  with a Uniform(0, 1) weight. Under dwelling counts that blend runs from
  0.113% to 0.360%, so the MC median (83.97) has moved away from the central
  run, which now sits at the 26.5th percentile. Item 9 (D3: scenarios S1/S2,
  inputs centred on evidence) resolves this; the MC interval should not be
  quoted until then.
* **A1 is not implemented.** The method needs your decision (§3).

**Correction to the ASSESSMENT addendum (D2 point 3).** Stats NZ's
post-2023 intercensal weight (0.889 × consents lagged four quarters) implies
about 0.000%/yr net replacement once this model's completion rate and lag are
applied consistently (`outputs/validation.md`, section D). It does **not**
corroborate about 0.09%/yr, as I wrote earlier. That arithmetic ignored the
lag timing. The weight is a Stats NZ assumption and supports no particular
rate.

The independent cross-check that remains is the identity run on the DHE
dwelling series, whose bases are census counts. It gives 0.120%/yr against
0.113%/yr from census counts.

## 2. Validation at CP2 (`outputs/validation.md`)

**Hindcast (A): dwellings built, with actual households and vacancy.**
The model's dwelling-count method errs by −15.9% (origin 2006), −18.4%
(2013) and −13.5% (2018). Every long-run calibration under-predicts. The
exceptions are the most recent interval's rate at origin 2018 (+1.8%) and
the linked townhouse model, which swings between −4.7% and +19.1%.

**Hindcast (B): the 2023 census stock.** Predicting the stock from each
origin with the dwelling-count identity over-predicts it by +12% to +19%. In
other words, net removals after each origin exceeded the rate calibrated
before it. With only three origins this is descriptive, but consistent: the
long-run rate has under-predicted recent replacement from every origin.

**2026 check.** Observed consents for January–July 2026 are 1.97 × the
model's implied 2026 consents, seasonally apportioned.

## 3. The 2026 gap (A1): evidence (`outputs/gap_2026.md`)

All in dwellings completed in 2026, all categories. Observed-implied
completions are 36,800–37,600, depending on how 2026 consents are
estimated. The model requires 27,760. The gap is +9,000 to +9,800
(32–35%).

| component | S1 | S2 |
|---|---|---|
| (ii) S2 regime | 0 | +1,674 (= +5,209 from the rate − 3,535 of the carried 2025 deviation) |
| (iii) population: actual growth 36,400 vs projected median 51,000, year ended June 2026 | −5,763 | −5,763 |
| (i) pipeline: 2026 completions from 2025 consents above the requirement | +6,483 | +5,634 |
| (iv) residual: 2026 consents above the requirement | +8,317 to +9,116 | +7,492 to +8,291 |

What the evidence says:

1. **Population does not explain the gap; it widens it.** Growth was 14,600
   below the projected median (provisional estimate), which lowers the
   requirement by about 5,800 dwellings.
2. **Most of the gap is building already in train** (the pipeline from 2025,
   +6,500) **plus 2026 consenting well above requirement** (+7,500 to
   +9,100). The model's 2026 requirement already carries +3,408 of the 2025
   deviation.
3. **If the residual were simply surplus, it would be large.** As vacancy it
   would add 0.36–0.43 percentage points in one year. For comparison,
   private vacancy rose 0.31 points over the whole of 2018–2023. As household
   formation it would lower household size by about 0.01 in one year, while
   the Stats NZ path falls about 0.003 a year.
4. **In the 2018–23 boom, excess building mostly went to redevelopment.** Of
   192,911 completions, 158,106 were net stock growth, so 34,805 were net
   removals (redevelopment). A higher vacancy rate absorbed only 6,286. Net
   replacement is pro-cyclical, and a building upswing is likely to come with
   redevelopment again.

   *Correction (after CP2):* this point first read "23,609 net removals and
   11,196 more under construction". Completions are already lagged W behind
   consents, so subtracting the change in dwellings under construction as
   well counted the pipeline twice. Net removals = completions − stock change
   = 34,805 (`outputs/gap_2026.md`). The census-interval rate (0.360%/yr) was
   always computed without that subtraction and is unaffected.

## 4. A1 options, assessed against this evidence

| option | identifiable from our data? | does early excess add to the 2026–2050 total or get offset? | fit to the evidence |
|---|---|---|---|
| (a) nowcast 2026 (and the W-share of 2027) from observed consents; projection from 2027 | Yes: observed consents, W and c; no estimated parameter | Adds, unless paired with a rule for the excess | Uses 2026 as data, so the 2026 out-of-sample check must run on a no-nowcast diagnostic |
| (b) partial adjustment of the gap (the current carried 2025 deviation is already this, ρ = 0.68) | The AR(1) is estimable (n ≈ 33, small-sample bias to state), but the gap is measured against interpolated household size | Adds; no stock consistency | Treats the excess as transient noise; the pro-cyclical removals suggest it is not |
| (c) stock-flow: excess raises vacancy, drawn down later | The drawdown rate is **not** identifiable: only two censuses are on the current empty definition | Offset within the window | 2018–23: vacancy absorbed only about a fifth of the non-pipeline excess |

**Recommendation for your decision:** (a) + (c) with an evidence-based split.
1. Nowcast 2026 completions from observed consents (7 months observed plus
   seasonal shares), and the W-share of 2027 from 2026 consents already
   issued.
2. Allocate the excess over the requirement using the 2018–23 census shares
   of non-pipeline excess: redevelopment removals (no offset; it replaces
   stock) and vacancy (raises stock; drawn down over a horizon).
3. The split is a stated assumption from one intercensal interval. The
   drawdown horizon is JUDGEMENT (for example 5 years, with 3 and 10 as
   sensitivities).
4. Keep the carried 2025 deviation (b) and "no near-term join" as reported
   sensitivities.
5. Keep a no-nowcast diagnostic run for the 2026 validation.

Rough effect, before implementation: about +1.2 Mm² of in-scope floor area in
2026–27, of which the vacancy share (about a fifth) is offset later. That
comes to roughly +1% net on the cumulative total. It will be measured
properly once implemented.

**Decision needed:**
* choose (a), (b), (c) or the combination;
* confirm or replace the split assumption and the drawdown horizon.

I implement A1 after that and then re-measure. Items 5–7 and 4 do not depend
on it.
