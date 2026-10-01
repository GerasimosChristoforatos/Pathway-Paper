Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.043 | 397,185 | 460,544 | -13.8% |
| 2006 | 2007-2023 | recent | -0.049 | 368,553 | 460,544 | -20.0% |
| 2006 | 2007-2023 | linked | linked: b = 2.54 on 3 intervals | 481,694 | 460,544 | +4.6% |
| 2006 | 2007-2023 | dwelling_count | -0.010 | 380,933 | 460,544 | -17.3% |
| 2006 | 2007-2023 | reference_s3_10 | +0.018 | 385,742 | 460,544 | -16.2% |
| 2013 | 2014-2023 | constant | +0.034 | 273,162 | 340,888 | -19.9% |
| 2013 | 2014-2023 | recent | +0.019 | 270,314 | 340,888 | -20.7% |
| 2013 | 2014-2023 | linked | linked: b = 0.96 on 4 intervals | 330,310 | 340,888 | -3.1% |
| 2013 | 2014-2023 | dwelling_count | +0.024 | 271,249 | 340,888 | -20.4% |
| 2013 | 2014-2023 | reference_s3_10 | +0.087 | 279,469 | 340,888 | -18.0% |
| 2018 | 2019-2023 | constant | +0.118 | 179,025 | 202,189 | -11.5% |
| 2018 | 2019-2023 | recent | +0.430 | 209,681 | 202,189 | +3.7% |
| 2018 | 2019-2023 | linked | linked: b = 1.39 on 5 intervals | 253,530 | 202,189 | +25.4% |
| 2018 | 2019-2023 | dwelling_count | +0.053 | 172,638 | 202,189 | -14.6% |
| 2018 | 2019-2023 | reference_s3_10 | +0.158 | 181,047 | 202,189 | -10.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.010 | 440,630 | 383,046 | +15.0% |
| 2006 | 2006-2023 | recent interval | +0.018 | 432,197 | 383,046 | +12.8% |
| 2013 | 2013-2023 | long run | +0.024 | 306,523 | 266,661 | +14.9% |
| 2013 | 2013-2023 | recent interval | +0.087 | 294,848 | 266,661 | +10.6% |
| 2018 | 2018-2023 | long run | +0.053 | 183,230 | 158,106 | +15.9% |
| 2018 | 2018-2023 | recent interval | +0.158 | 173,055 | 158,106 | +9.5% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.101%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.141%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of -0.001%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 17,389 (annual 30,983 x seasonal share 0.561); observed / model = 1.375. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.
