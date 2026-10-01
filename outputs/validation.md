Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

Vacancy definition: consistent -- the pooled 2018/2023 empty share of unoccupied private dwellings (49.2%) applied to every census; the 2013 census share was 76.2% (published empty vacancy 2013 8.09% -> 2018 5.08%, a definitional break). The as-published series is shown below the table.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.092 | 458,783 | 460,544 | -0.4% |
| 2006 | 2007-2023 | recent | -0.003 | 429,806 | 460,544 | -6.7% |
| 2006 | 2007-2023 | linked | linked: b = 1.67 on 3 intervals | 513,426 | 460,544 | +11.5% |
| 2006 | 2007-2023 | dwelling_count | -0.010 | 427,708 | 460,544 | -7.1% |
| 2006 | 2007-2023 | reference_s3_10 | +0.018 | 432,419 | 460,544 | -6.1% |
| 2013 | 2014-2023 | constant | +0.090 | 338,113 | 340,888 | -0.8% |
| 2013 | 2014-2023 | recent | +0.086 | 337,443 | 340,888 | -1.0% |
| 2013 | 2014-2023 | linked | linked: b = 0.59 on 4 intervals | 372,681 | 340,888 | +9.3% |
| 2013 | 2014-2023 | dwelling_count | +0.024 | 325,771 | 340,888 | -4.4% |
| 2013 | 2014-2023 | reference_s3_10 | +0.087 | 333,902 | 340,888 | -2.0% |
| 2018 | 2019-2023 | constant | +0.035 | 170,792 | 202,189 | -15.5% |
| 2018 | 2019-2023 | recent | -0.168 | 150,872 | 202,189 | -25.4% |
| 2018 | 2019-2023 | linked | linked: b = 0.26 on 5 intervals | 185,079 | 202,189 | -8.5% |
| 2018 | 2019-2023 | dwelling_count | +0.053 | 172,485 | 202,189 | -14.7% |
| 2018 | 2019-2023 | reference_s3_10 | +0.158 | 180,895 | 202,189 | -10.5% |

### (A2) Same hindcast with census vacancy as published (2013->2018 break included)

| origin | test years | method | predicted | actual | error |
|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | 397,185 | 460,544 | -13.8% |
| 2006 | 2007-2023 | recent | 368,553 | 460,544 | -20.0% |
| 2006 | 2007-2023 | linked | 481,694 | 460,544 | +4.6% |
| 2006 | 2007-2023 | dwelling_count | 380,933 | 460,544 | -17.3% |
| 2006 | 2007-2023 | reference_s3_10 | 385,742 | 460,544 | -16.2% |
| 2013 | 2014-2023 | constant | 273,162 | 340,888 | -19.9% |
| 2013 | 2014-2023 | recent | 270,314 | 340,888 | -20.7% |
| 2013 | 2014-2023 | linked | 330,310 | 340,888 | -3.1% |
| 2013 | 2014-2023 | dwelling_count | 271,249 | 340,888 | -20.4% |
| 2013 | 2014-2023 | reference_s3_10 | 279,469 | 340,888 | -18.0% |
| 2018 | 2019-2023 | constant | 179,025 | 202,189 | -11.5% |
| 2018 | 2019-2023 | recent | 209,681 | 202,189 | +3.7% |
| 2018 | 2019-2023 | linked | 253,530 | 202,189 | +25.4% |
| 2018 | 2019-2023 | dwelling_count | 172,638 | 202,189 | -14.6% |
| 2018 | 2019-2023 | reference_s3_10 | 181,047 | 202,189 | -10.5% |

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
