Net replacement in use: census dwelling-count identity (window 1991-2023).

### (A) Rolling-origin hindcast of dwellings built (descriptive; 3 origins)

Actual households and vacancy fed in; only the net-replacement term is predicted. Error = predicted / actual - 1.

Vacancy definition: consistent -- the pooled 2018/2023 empty share of unoccupied private dwellings (49.2%) applied to every census; the 2013 census share was 76.2% (published empty vacancy 2013 8.09% -> 2018 5.08%, a definitional break). The as-published series is shown below the table.

| origin | test years | method | rate used (%/yr) | predicted | actual | error |
|---|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | +0.039 | 442,676 | 438,386 | +1.0% |
| 2006 | 2007-2023 | recent | -0.116 | 394,985 | 438,386 | -9.9% |
| 2006 | 2007-2023 | linked | linked: b = 1.91 on 3 intervals | 459,136 | 438,386 | +4.7% |
| 2006 | 2007-2023 | dwelling_count | -0.030 | 421,494 | 438,386 | -3.9% |
| 2006 | 2007-2023 | reference | -0.039 | 419,979 | 438,386 | -4.2% |
| 2013 | 2014-2023 | constant | +0.077 | 335,678 | 311,633 | +7.7% |
| 2013 | 2014-2023 | recent | +0.146 | 348,753 | 311,633 | +11.9% |
| 2013 | 2014-2023 | linked | linked: b = 0.32 on 4 intervals | 344,773 | 311,633 | +10.6% |
| 2013 | 2014-2023 | dwelling_count | +0.038 | 328,404 | 311,633 | +5.4% |
| 2013 | 2014-2023 | reference | +0.164 | 344,750 | 311,633 | +10.6% |
| 2018 | 2019-2023 | constant | -0.016 | 165,729 | 190,590 | -13.0% |
| 2018 | 2019-2023 | recent | -0.363 | 131,694 | 190,590 | -30.9% |
| 2018 | 2019-2023 | linked | linked: b = 0.82 on 5 intervals | 196,149 | 190,590 | +2.9% |
| 2018 | 2019-2023 | dwelling_count | +0.033 | 170,563 | 190,590 | -10.5% |
| 2018 | 2019-2023 | reference | +0.013 | 168,956 | 190,590 | -11.4% |

### (A2) Same hindcast with census vacancy as published (2013->2018 break included)

| origin | test years | method | predicted | actual | error |
|---|---|---|---|---|---|
| 2006 | 2007-2023 | constant | 381,233 | 438,386 | -13.0% |
| 2006 | 2007-2023 | recent | 334,129 | 438,386 | -23.8% |
| 2006 | 2007-2023 | linked | 402,719 | 438,386 | -8.1% |
| 2006 | 2007-2023 | dwelling_count | 374,614 | 438,386 | -14.5% |
| 2006 | 2007-2023 | reference | 373,067 | 438,386 | -14.9% |
| 2013 | 2014-2023 | constant | 270,772 | 311,633 | -13.1% |
| 2013 | 2014-2023 | recent | 281,395 | 311,633 | -9.7% |
| 2013 | 2014-2023 | linked | 288,236 | 311,633 | -7.5% |
| 2013 | 2014-2023 | dwelling_count | 273,906 | 311,633 | -12.1% |
| 2013 | 2014-2023 | reference | 290,429 | 311,633 | -6.8% |
| 2018 | 2019-2023 | constant | 174,090 | 190,590 | -8.7% |
| 2018 | 2019-2023 | recent | 190,849 | 190,590 | +0.1% |
| 2018 | 2019-2023 | linked | 183,375 | 190,590 | -3.8% |
| 2018 | 2019-2023 | dwelling_count | 170,715 | 190,590 | -10.4% |
| 2018 | 2019-2023 | reference | 169,109 | 190,590 | -11.3% |

### (B) Rolling-origin hindcast of the 2023 census private-dwelling stock (dwelling-count identity; descriptive)

Change in census private dwellings from the origin to 2023, predicted as completions - rate x stock-years with the rate calibrated up to the origin.

| origin | interval | rate | rate used (%/yr) | predicted change | actual change | error |
|---|---|---|---|---|---|---|
| 2006 | 2006-2023 | long run | -0.030 | 429,436 | 383,046 | +12.1% |
| 2006 | 2006-2023 | recent interval | -0.039 | 432,150 | 383,046 | +12.8% |
| 2013 | 2013-2023 | long run | +0.038 | 277,428 | 266,661 | +4.0% |
| 2013 | 2013-2023 | recent interval | +0.164 | 253,960 | 266,661 | -4.8% |
| 2018 | 2018-2023 | long run | +0.033 | 171,688 | 158,106 | +8.6% |
| 2018 | 2018-2023 | recent interval | +0.013 | 173,633 | 158,106 | +9.8% |

### (C, D) Cross-checks of the net replacement rate

- Census dwelling counts, 1991-2023: +0.059%/yr.
- Same identity on the Stats NZ DHE private-dwelling series at 31 March (bases = census counts): +0.064%/yr.
- Stats NZ's intercensal weighting after the 2023 base: DHE dwelling growth = 0.8888 x consents lagged four quarters (sd 0.0047); with this model's completion rate and lag this implies net replacement of +0.235%/yr over 2023-06-30..2026-03-31. This is Stats NZ's assumption, not an observation.

### 2026 out-of-sample check against observed consents

Run on the model WITHOUT any observed 2026 input (settings: {'CONSENT_DATA_END': '2025-12-01', 'NOWCAST_POPULATION': False}), so the check stays out of sample.

Completion lag 17 months: without 2026 data the pipeline years are [2026]; the model's 2027 building 28,386 (all categories) vs the observed pipeline 38,658 (consents [2026, 2027] lagged 17 months); observed / model = 1.362. Descriptive only: not used to set any parameter.
