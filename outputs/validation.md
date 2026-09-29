Net replacement source in use: `dwelling_count` (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.024 | 391,522 | 455,109 | -14.0% |
| 2006 | 2007-2023 | recent | -0.082 | 358,418 | 455,109 | -21.2% |
| 2006 | 2007-2023 | linked | linked: b = 2.45 on 3 intervals | 473,242 | 455,109 | +4.0% |
| 2006 | 2007-2023 | dwelling_count | -0.004 | 382,629 | 455,109 | -15.9% |
| 2013 | 2014-2023 | constant | +0.029 | 272,162 | 333,208 | -18.3% |
| 2013 | 2014-2023 | recent | +0.038 | 273,820 | 333,208 | -17.8% |
| 2013 | 2014-2023 | linked | linked: b = 0.77 on 4 intervals | 317,475 | 333,208 | -4.7% |
| 2013 | 2014-2023 | dwelling_count | +0.028 | 271,931 | 333,208 | -18.4% |
| 2018 | 2019-2023 | constant | +0.101 | 177,353 | 200,146 | -11.4% |
| 2018 | 2019-2023 | recent | +0.369 | 203,669 | 200,146 | +1.8% |
| 2018 | 2019-2023 | linked | linked: b = 1.15 on 5 intervals | 238,447 | 200,146 | +19.1% |
| 2018 | 2019-2023 | dwelling_count | +0.057 | 173,029 | 200,146 | -13.5% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.004 | 444,082 | 383,046 | +15.9% |
| 2006 | 2006-2023 | recent interval | +0.027 | 434,623 | 383,046 | +13.5% |
| 2013 | 2013-2023 | long run | +0.028 | 310,942 | 266,661 | +16.6% |
| 2013 | 2013-2023 | recent interval | +0.087 | 299,905 | 266,661 | +12.5% |
| 2018 | 2018-2023 | long run | +0.057 | 187,443 | 158,106 | +18.6% |
| 2018 | 2018-2023 | recent interval | +0.163 | 177,125 | 158,106 | +12.0% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.113%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.120%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.000%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Months observed: [1, 2, 3, 4, 5, 6, 7]. Observed 23,916 vs model 12,133 (annual 21,618 x seasonal share 0.561); observed / model = 1.971. Latest 12 months (2025-08-01..2026-07-01): 40,908. Descriptive only: not used to set any parameter.
