# Evidence for ASSESSMENT.md

These scripts produce every number in `ASSESSMENT.md`. They **read** the model
and do not modify it. Alternatives are applied by setting a module flag, or
wrapping a module-level function, on a freshly reloaded `Boss`. Where a change
sits inside a closure of `Boss.main()`, `stockcal.py` provides an offline
replica of the stock calibration and forward equation. The replica reproduces
Boss at the adopted settings and at completion 0.92 to the printed precision,
and `stockcal.py` prints that check when run directly.

Run from the repository root after `Building_factors.py`:

```
python docs/assessment_evidence/c1_engine_equivalence.py
python docs/assessment_evidence/c2_household_size_tail.py
python docs/assessment_evidence/c2_c5_extra.py
python docs/assessment_evidence/c3_dhe_anchor.py
python docs/assessment_evidence/c4_completion_lag.py
python docs/assessment_evidence/c5_hindcast.py
python docs/assessment_evidence/c5_c7_vacancy_break.py
python docs/assessment_evidence/c5_dwelling_count_identity.py
python docs/assessment_evidence/c6_c8_soil_factors.py
python docs/assessment_evidence/c7_small_sample_se.py
python docs/assessment_evidence/c7_mc_median_attribution.py   # ~10 min (11 x 10,000 MC draws)
python docs/assessment_evidence/c8_c9_checks.py
```

The saved outputs of the run used for `ASSESSMENT.md` are in `output/`.
Environment: Python 3.11.15, numpy 2.4.6, pandas 3.0.6, scipy 1.17.1,
matplotlib 3.11.2, openpyxl 3.1.5.
