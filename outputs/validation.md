Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.043 | 397,185 | 460,544 | -13.8% |
| 2006 | 2007-2023 | recent | -0.049 | 368,553 | 460,544 | -20.0% |
| 2006 | 2007-2023 | linked | linked: b = 2.54 on 3 intervals | 481,694 | 460,544 | +4.6% |
| 2006 | 2007-2023 | dwelling_count | +0.009 | 386,590 | 460,544 | -16.1% |
| 2006 | 2007-2023 | reference_s3_10 | +0.076 | 398,303 | 460,544 | -13.5% |
| 2013 | 2014-2023 | constant | +0.034 | 273,162 | 340,888 | -19.9% |
| 2013 | 2014-2023 | recent | +0.019 | 270,314 | 340,888 | -20.7% |
| 2013 | 2014-2023 | linked | linked: b = 0.96 on 4 intervals | 330,310 | 340,888 | -3.1% |
| 2013 | 2014-2023 | dwelling_count | +0.025 | 271,333 | 340,888 | -20.4% |
| 2013 | 2014-2023 | reference_s3_10 | +0.055 | 275,263 | 340,888 | -19.3% |
| 2018 | 2019-2023 | constant | +0.118 | 179,025 | 202,189 | -11.5% |
| 2018 | 2019-2023 | recent | +0.430 | 209,681 | 202,189 | +3.7% |
| 2018 | 2019-2023 | linked | linked: b = 1.39 on 5 intervals | 253,530 | 202,189 | +25.4% |
| 2018 | 2019-2023 | dwelling_count | +0.067 | 174,104 | 202,189 | -13.9% |
| 2018 | 2019-2023 | reference_s3_10 | +0.227 | 186,837 | 202,189 | -7.6% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | +0.009 | 448,708 | 383,046 | +17.1% |
| 2006 | 2006-2023 | recent interval | +0.076 | 428,167 | 383,046 | +11.8% |
| 2013 | 2013-2023 | long run | +0.025 | 323,851 | 266,661 | +21.4% |
| 2013 | 2013-2023 | recent interval | +0.055 | 318,271 | 266,661 | +19.4% |
| 2018 | 2018-2023 | long run | +0.067 | 192,982 | 158,106 | +22.1% |
| 2018 | 2018-2023 | recent interval | +0.227 | 177,575 | 158,106 | +12.3% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.134%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.141%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of -0.001%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'NEAR_TERM_JOIN': 'carried_deviation', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 18,017 (annual 32,103 x seasonal share 0.561); observed / model = 1.327. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.
