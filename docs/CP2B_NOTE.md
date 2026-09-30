# CP2b note: A1 implemented, and the replacement scenarios (decision needed)

Every number here is quoted from a generated file:
* `outputs/near_term_join.md` (A1 evidence and result);
* `outputs/replacement_scenarios.md` (item 2);
* `outputs/gap_2026.md` and `outputs/validation.md` (2026 evidence, run on the
  model without observed-2026 inputs);
* `outputs/sensitivity_oat.csv`;
* `CHANGELOG.md` (before/after tables).

Commits: machinery behind flags (no change), the gap_2026 correction,
population nowcast, then the consent nowcast with three channels.

## 1. A1 as implemented

**(a) Nowcast.**
* 2026 consents = January–July observed (23,916) plus August–December by a
  ratio-to-annual estimator with fixed seasonal factors: the mean share of
  the calendar year in each month over 2010–2025. That gives 42,613 in all.
* The alternatives are reported as sensitivities:
  * same-period ratio on 2025: 44,621 (+0.29% on the total);
  * the latest 12 months: 40,908 (−0.25%).
* A model-based forecast (SARIMA or ETS) would be the other standard choice.
  It is not implemented: statsmodels is not in the environment, and with five
  months to forecast I do not expect it to move the total beyond the spread
  above. I have not tested this.
* 2026 completions = c[(1 − W)C26 + W C25] = 37,596, against the model's
  requirement of 18,589.
* The W share of 2027 gives a further +7,939. The assumption behind that
  figure: 2027 consents run at the requirement, net of the 2026 drawdown.
* Population: observed growth over the year ended June 2026 was 36,400
  (provisional), against a projection median of 51,000.
  * Under the join this changes only how the 2026 excess is allocated. The
    total moves by 0.13% (sensitivity row).

**(c) Three channels, measured on ONE interval (2018→2023) against the active
scenario.**
* **Household test.** Census household size is ERP at census night divided
  by (occupied + away). It fell 2.37%, against 0.94% for the Stats NZ shape,
  so the channel is included.
  * With one interval no standard error can be formed. This is a comparison
    of point values, not a statistical test.
  * 2013→18 census household size rose. So the effect looks cyclical, but it
    is permanent by default (JUDGEMENT); reverting is a sensitivity (−2.05%).
* **Channel levels.**
  * Redevelopment: 23,913.
  * Vacancy: 6,286.
  * Households: 27,600, or 20,421 if the population is dated mid-year rather
    than at census night.
  * Shares (census night): 0.414 / 0.109 / 0.478.
  * **The household level is sensitive to the population date**, because
    growth was fast early in 2023. The effect on the total is small (−0.06%),
    but the measurement should use the 31 March ERP (see §4).
* **Median-path join, 2026–2050.** Redevelopment +11,148; vacancy +2,930
  (drawn down −2,930 over 5 years); households +12,867; net +24,016
  dwellings.
* **Result:** 76.00 Mm²; 29,427 kt. The 2025→2026 step is +9.0%, now set by
  observed consents.
* **Sensitivities (floor area):**

| setting | change |
|---|---|
| all to redevelopment | +0.45% |
| all to vacancy | −3.95% |
| equal shares | −0.95% |
| drawdown over 3 years | +0.02% |
| drawdown over 10 years | −0.01% |
| carried deviation (original) | −2.32% |
| no join | −4.11% |

**Caveats (stated in the code and the CHANGELOG):**
* The 2018 empty count has no quality rating (F1). The vacancy channel rests
  on it.
* The Stats NZ shape is 2018-base (N4).
* The extra stock from the vacancy and household channels does not enter the
  demolition base. This is second order: at most about 0.1% of roughly
  16,000 dwellings a year.
* Negative excess would be treated symmetrically.

**The 2026 check stays out of sample.** `validation.py` and `gap_2026.py` run
the model with `NO_2026_DATA` (carried deviation, projected population). The
observed/model ratio is 1.971, unchanged.

**Correction.** In the CP2 note, 2018–23 net removals are 34,805, not 23,609.
The change in dwellings under construction had been subtracted on top of the
lag. Fixed in a separate commit.

## 2. Item 2: S1, S2 and S3 (`outputs/replacement_scenarios.md`)

| scenario | floor area 2026–50 | vs S1 | net removals/yr (mean) | cumulative, % of 2025 stock | share of S1's 2026 excess covered |
|---|---|---|---|---|---|
| S1: long run 0.113% | 76.00 | — | 2,671 | 3.2% | 0% |
| S3, half-life 5 years | 79.54 | +4.7% | 4,113 | 4.9% | 24% |
| S3, half-life 10 years | 83.01 | +9.2% | 5,276 | 6.3% | 26% |
| S3, half-life 15 years | 85.17 | +12.1% | 5,995 | 7.1% | 26% |
| S2: 2018–23 rate 0.360% | 92.81 | +22.1% | 8,534 | 10.1% | 27% |

**Implied gross demolitions.** Assuming the long-run residual (net
unconsented additions, −0.022%/yr) persists, gross demolitions are about 530
a year above net removals: S1 3,202; S2 9,066.

**Plausibility.**
* **Census record.** The intercensal rate has risen at every interval since
  2001: +0.027 → +0.087 → +0.163 → +0.360%/yr, or 423 → 1,470 → 2,940 →
  6,961 net removals a year.
  * S2 holds the record interval for 25 years. That means 10% of today's
    stock removed.
  * S1 assumes a return to below the 2013–18 rate from 2026.
* **Hindcast.** The long-run rate under-predicted building from every origin
  (−13.5% to −18.4%), so S1 has a documented low bias.
  * The "recent interval" method did well from 2018 (+1.8%) but badly from
    2006 (−21%) and 2013 (−18%). Recency alone has not been reliable either.
* **The 2026 data do not discriminate between S2 and S3.** S3 starts at the
  2018–23 rate by construction, and the 2026 rates differ only between 0.328
  and 0.360%. All scenarios cover only 24–27% of S1's 2026 excess. Most of
  the excess is channel building whichever scenario holds.
* **The persistence (half-life) is not identifiable** from a single elevated
  interval. The sample is too small for any estimation method.
* **No independent count of demolitions is in our data.** Gross demolitions
  at 0.38%/yr (S2) would be almost three times BRANZ SR214's 0.135%. A
  national demolition count would test this directly (§4).
* **Channel shares under S2/S3** are 0 / 0.185 / 0.815. The household channel
  then carries most of the excess permanently, which puts more weight on the
  household-channel judgement.

**Recommendation (your decision):**
* Present **S1 and S2 as the bracketing bounds**, with no data-identified
  central case.
* Use **S3 with a 10-year half-life as the labelled reference path**
  (JUDGEMENT) for the decompositions, figures and the MC, with 5 and 15
  years reported.
* Reasons:
  1. S1 is biased low in the hindcast, and the rate has risen for four
     intervals.
  2. S2 extrapolates one record interval for 25 years.
  3. A decaying path is the standard mean-reverting form, but its speed is
     judgement.
* If you prefer a single evidence-only central case, S1 is the only one that
  uses no judgement parameter, but its downward bias should then be stated as
  a limitation.

## 3. Next steps

After your decision:
* item 8: soil set to zero on replacement bands, with placeholders marked
  for E5/E6;
* item 9: the MC run within each scenario, replacing the interim regime
  weight. The MC central run currently sits at the 24.4th percentile, which
  is why the MC interval should not be quoted yet.

Then stop at CP3.

## 4. External data requested

1. **Quarterly ERP.** Infoshare (infoshare.stats.govt.nz) → Browse →
   Population → *Population Estimates – DPE* → the quarterly estimated
   resident population series (Mar/Jun/Sep/Dec), total New Zealand, both
   sexes, all ages; export CSV from 1991. Please confirm the exact table
   title on the page; I have not been able to open Infoshare from here.
   * It replaces the provisional release figure for 2026.
   * It gives the 31 March 2018 and 2023 ERP for the household test.
   * Alternative: allow `infoshare.stats.govt.nz`. Its download is a form
     workflow, so a manual CSV export is more reliable.
2. **A national count of dwelling demolitions** (optional, for item 2
   plausibility), if you know of a source, for example council demolition
   consents. I do not know of a Stats NZ national series and will not
   assume one exists.
