# Tests

`python -m pytest tests` runs every file below on the outputs of the active profile (`PATHWAY_PROFILE=full` for
`outputs/`; light by default). No test runs the Monte Carlo or the Sobol analysis; several run the deterministic
projection in process (`conftest.run_boss`).

## What each file protects

| file | protects |
|---|---|
| `test_regression_model.py` | **the regression lock** (`tests/regression_lock.json`): the SHA-256 of every deterministic data file and of the Monte Carlo draw files of the active profile. Any change to a reported number fails here. |
| `test_identities.py` | the accounting identities of the projection: typology and band sums, the stock identity, material + soil = carbon, stages + soil = total, the band stack is the total, the census-interval histories. |
| `test_pathway_rules.py` | the model rules and STOP conditions: overbuild absorption (logistic, payback cap and carry), the lever rule (Moderate the exact midpoint, TL at least as strong as Ambitious), the ordering Reference ≥ Moderate ≥ Ambitious ≥ TL, re-occupation, Shapley efficiency, waterfall sums. |
| `test_strategies_bands.py` | the PAS 2080 strategies partition the levers in order, the band sums of every run, the solution-space markers on the analytic plane, the Very High replacement variant, the replacement half-life sampled in the Monte Carlo. |
| `test_completion_lag.py` | the 17-month completion lag, the completion rate 0.945, the L1 at TL speed limit, the household-size sensitivities, the AR base at the completion rate. |
| `test_household_settings.py` | the adopted household settings (households after 2023 = ERP / the household-size path; the Stats NZ 2023-base path, rebased and paired), the six display bands, the starting surplus. |
| `test_aesa.py` | the AESA equations and constants (acquired rights, ability to pay, level of exceedance); the constants from the raw files. |
| `test_decarb.py`, `test_decarb_item.py` | material decarbonisation: the Horup et al. (2025) S4 paths, the item mapping, the 2025 class totals kept, the sensitivity cases, the Monte Carlo bootstrap stream unchanged. |
| `test_events.py` | time-resolved maintenance (B2/B4 events) and the committed emissions after 2050. |
| `test_census_uc.py` | the census under-construction correction of the interval rates. |
| `test_soil.py` | soil carbon loss only on floor area on newly converted land. |
| `test_overbuild_2026.py` | the near-term market excess, the 2026 nowcast and the replacement scenarios (synthetic inputs). |
| `test_demand_balance.py` | the demand-balance diagnostics. |
| `test_consents_freeze.py` | the consent data freeze: the derived file is rebuilt exactly from the raw Infoshare export, the MANIFEST checksum, no revisions. |
| `test_committed_mc.py` | committed emissions per Monte Carlo draw: the identities and the central value inside the 5th-95th range. |
| `test_mcstats.py` | the Monte Carlo insight statistics against statsmodels fixtures and closed-form cases. |
| `test_profiles.py` | the deterministic results are identical in the light and full profiles (the file comparisons skip unless both `outputs/_light/` and `outputs/` exist). |
| `test_sensitivity_rules.py` | the shared-parameter rule: every one-at-a-time row that reports a LoE is classified (`boundaries.AR_BASE_RULE`); a `reference_base` row of the tornado uses the Reference AR budget; a `recompute` row's I_sec,base is the Monte Carlo base function at the row's factors, and the central factors are the Monte Carlo's; the EF 3.1 global-impact row scales LoE AR by the I_glob ratio and leaves AtP; the like-for-like zero-lag run of SF2 uses the 17-month net replacement calibration. |
| `test_figure_integrity.py` | the figure tests that check drawn values against the data: the model scripts do not plot; drawing leaves `outputs/data/` byte-identical; every planned figure is drawn and audited; the sign rules (cumulative bars end at their net, stacked series up + down = net, materials and stages never negative); the Fig4 waterfalls add up to the run totals; the TL steps; Fig3b's interval from the draws; Fig1's annual line against the census-interval means; the ED6 / ED5 notes stop when the code and the outputs disagree; the palette file rejects a missing or unknown key, a bad hex and an opacity outside [0, 1]; ED3b: up + down = net for every column and year, and the census-interval means of the annual line = the column nets. |

## Fixtures and capture scripts

| file | used by |
|---|---|
| `regression_lock.json`, `regression.py` | the regression lock (`regression.py` reads and compares it); written by `capture_regression_lock.py` after a light and a full run |
| `fixtures/mcstats_reference.json` | `test_mcstats.py` (written by `make_mcstats_reference.py`) |
| `mcstats_data.py` | the fixed synthetic data of `test_mcstats.py` and `make_mcstats_reference.py` |
| `conftest.py` | `run_boss` (one silent in-process projection) and the shared fixtures |

Every test writes only to temporary folders (`tmp_path`, or `PATHWAY_FIG_OUT` for the figure redraw), so the committed
outputs and `git status` are unchanged by a test run.

## Run by hand (not tests)

* `python tools/check_figure_text.py` — the text rules of the figure suite (en-dash year ranges, thousands separators,
  the typographic minus) on every drawn figure.
* `python tools/palette_check.py` — the colour-vision check of the palette (CAM02-UCS under simulated deficiencies) and
  the zone lightness order; writes `docs/PALETTE.md` and `docs/palette_preview.png`.
* `python tools/palette_coverage.py` — redraws every final figure with a probe palette and reports any colour or fade
  that does not come from `palette.toml` (or the declared neutrals and context fades of `figures/style.py`).
