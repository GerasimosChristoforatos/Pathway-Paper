# Project state: MODEL v3.2.0 (update)

Branch `release/model-v3.2.0` (from `release/model-v3.0.0`; proposed tag `model-v3.2.0`, not yet tagged). MODEL v3.1.0
is withdrawn. Decisions: [CHANGELOG_v3_2.md](CHANGELOG_v3_2.md). Every v3.0 headline below still holds: the
Reference, every lever and pathway run and TL are unchanged (to 3.4e-16), and so are the Reference Monte Carlo and the
AESA draws. What changes: the band composition (release accounting, A2), the TL waterfall steps TL1-TL3 and the TL
Shapley values from P5 Moderate, the history split (A3), Fig6 (y = cut in total carbon per m2), and the pathway Monte
Carlo draws with a negative-gross year (carry-forward) or a non-physical soil share (zero-year guard): P(TL LoE AR <= 1)
stays 0.551, the 5th-95th percentiles of P5 Moderate, P5 Ambitious and TL are unchanged. New rows: TL with
re-occupation as fast as demand allows (4,073 kt, LoE AR 0.915) and r_L6 with A_1 (0.841, report only).

---

# Project state: MODEL v3.0.0

Status at the end of the v3.0.0 build (branch `release/model-v3.0.0`; proposed tag `model-v3.0.0`, not yet tagged).
Every number below is read from the full-profile outputs (`outputs/data/`); deterministic numbers are identical in
the light profile (`tests/test_profiles.py`). Decisions and their reasons: [CHANGELOG_v3.md](CHANGELOG_v3.md).

## What the model now says

**Reference (2026–2050).** Floor area 85.90 Mm², embodied carbon 20,615 kt CO₂e, cumulative level of exceedance
(LoE) 4.63 against acquired rights (AR) and 18.52 against ability to pay (AtP). The 2026 overbuild (27,479 dwellings
of market excess) is absorbed by 2035; implied vacancy 6.13% in 2026, peak 6.33% in 2028, 5.39% from 2035; the
payback cap never binds. The v2.1 Reference (overbuild never absorbed): 89.57 Mm², 21,578 kt. Monte Carlo (5,000
draws): carbon median 20,432 kt (90% interval 15,220–26,216), LoE AR median 4.60 (3.56–5.67).

**Pathways** (carbon 2026–2050, change vs the Reference):

| | Moderate | Ambitious |
|---|---|---|
| P1 Space per person | 17,958 kt (−12.9%) | 15,556 kt (−24.5%) |
| P2 Existing stock | 19,400 kt (−5.9%) | 18,202 kt (−11.7%) |
| P3 Construction | 19,077 kt (−7.5%) | 17,540 kt (−14.9%) |
| P4 Land | 19,933 kt (−3.3%) | 19,335 kt (−6.2%) |
| P5 Combined | 15,073 kt (−26.9%; LoE AR 3.39) | 10,920 kt (−47.0%; LoE AR 2.45) |

**Theoretical limit** (a thought experiment, not a pathway): 4,358 kt (−78.9%), LoE AR 0.98, AtP 3.92. Monte Carlo:
P(LoE AR ≤ 1) = 0.551; TL ≤ P5 Ambitious ≤ P5 Moderate in every draw. Instant TL (sensitivity row): 3,020 kt, LoE AR
0.68, P(LoE AR ≤ 1) = 0.979. No pathway, P5 Ambitious included, reaches the AR budget in any draw; AtP is not
reached by TL in any draw.

**Lever anchors:**

| lever | Ambitious anchor | Moderate |
|---|---|---|
| L1 | consent-size minima Detached 148.8 m² (1990), Townhouses 105.8 m² (1990), Apartments 91.0 m² (1998) | midpoint of f |
| L2 | r = 0.819 (95% bootstrap CI 0.732–0.960, B = 2,000) | 0.910 |
| L3 | household size 2050: 2.693 (Reference 2.652) | 2.673 |
| L4 | vacancy 4.013% | 4.700% |
| L6 | r = 0.827 (CI 0.607–0.950) | 0.914 |
| L9 | brownfield share 0.59 (s_ref 0.179) | 0.385 |

**Re-occupation (TL):** release from TL4 only (R3 = 0, R4 = 117,044 of G+ = 354,466; s = 0.330); release binds in
2027; no building needed in 2031–2032.

## What is built and tested

* Run profiles light / full; compute and drawing separated; Fig1–Fig8, ED1–ED14 + EDT1 and 40 diagnostics (62 figures; D20 in the
  full profile only), indexed in `outputs/FIGURES.md`.
* Tests: 189 passed in both profiles (2 skipped: they need the local-only manuscript workbook). Locks: the v2.1
  Reference (legacy, 1e-12), v3 deterministic hashes (28 files, identical in both profiles), Monte Carlo hashes per
  profile. No STOP condition triggered.

## Open items for the author

1. **References to verify** before submission (`REFERENCES.md`, items marked [verify]): DiPasquale & Wheaton (1992)
   issue number; Gabriel & Nothaft (2001 vs 1999) year, volume and pages; the DOIs of Wheaton (1990) and Rosen &
   Smith (1983); the DECC / DESNZ / EUCalc document titles and URLs; US EPA (2014) edition; Resch et al. (2021) full
   citation.
2. **Absorption speed.** 2035 is a modelling choice (the model's common adoption window); theory fixes the direction
   only. The sensitivity rows bracket it (by 2030: −0.15% Reference carbon; by 2045: +0.25%).
3. **Annual-carbon reversals** between levels (L3 Ambitious above TL in 2039–2043 by at most 64 kt a year; L4 in
   2031) are reported, not STOPs; the parameters and the cumulative totals are ordered. Decide whether the paper
   mentions them.
4. **Figures** are near-final but have not had an author review at print size.
5. **Tag** `model-v3.0.0` after review and merge.
