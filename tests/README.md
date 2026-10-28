# Tests (MODEL v4.3.3)

`python -m pytest tests` runs every file below on the outputs of the active profile (`PATHWAY_PROFILE=full` for
`outputs/`; light by default). No test runs the Monte Carlo or the Sobol analysis; several run the deterministic
projection in process (`conftest.run_boss`). `tests/retired/` is never collected (`conftest.collect_ignore_glob`).

## What each file protects

| file | protects |
|---|---|
| `test_regression_model_v3.py` | **the v4 regression lock** (`tests/regression_model_v4.json`): the SHA-256 of every deterministic data file and of the Monte Carlo draw files of the active profile. Any change to a reported number fails here. |
| `test_identities.py` | the accounting identities of the projection: typology and band sums, the stock identity, material + soil = carbon, stages + soil = total, the band stack is the total, the census-interval histories. |
| `test_model_v3.py` | the model rules and STOP conditions: overbuild absorption (logistic, payback cap and carry), the lever rule (Moderate the exact midpoint, TL at least as strong as Ambitious), the ordering Reference ≥ Moderate ≥ Ambitious ≥ TL, re-occupation, Shapley efficiency, waterfall sums. |
| `test_model_v3_3.py` | the PAS 2080 restructure (strategies partition the levers), the Very High replacement variant, the replacement half-life sampled in the Monte Carlo. |
| `test_model_v4.py` | the 17-month completion lag, the completion rate 0.945, the TL1 speed limit, TL surplus pooling, the household-size sensitivities; equivalence with MODEL v3.3 when they are switched off. |
| `test_model_v4_2.py` | the MODEL v4.2 diagnostic switches (household bridge, start mode, household-size path) keep the defaults. |
| `test_aesa.py` | the AESA equations and constants (acquired rights, ability to pay, level of exceedance); the reproduction of the author's workbook is skipped when `data/raw/Absolute_Analysis.xlsm` (local only) is absent. |
| `test_decarb.py`, `test_decarb_item.py` | material decarbonisation: the Horup et al. (2025) S4 paths, the item mapping, the 2025 class totals kept, the sensitivity cases, the Monte Carlo bootstrap stream unchanged. |
| `test_events.py` | time-resolved maintenance (B2/B4 events) and the committed emissions after 2050. |
| `test_census_uc.py` | the census under-construction correction of the interval rates. |
| `test_soil.py` | soil carbon loss only on floor area on newly converted land. |
| `test_overbuild_2026.py` | the near-term market excess, the 2026 nowcast and the replacement scenarios (synthetic inputs). |
| `test_validation.py` | the 2026 out-of-sample check (synthetic consents). |
| `test_demand_balance.py` | the demand-balance diagnostics. |
| `test_households_per_consent.py` | the Stats NZ household estimates grow by 0.888 × the previous year's consents (2019–2025), from the raw inputs. |
| `test_mcstats.py` | the Monte Carlo insight statistics against statsmodels fixtures and closed-form cases. |
| `test_profiles.py` | the deterministic results are identical in the light and full profiles (the file comparisons skip unless both `outputs/_light/` and `outputs/` exist). |
| `test_figure_integrity.py` | the figure tests that check drawn values against the data: the model scripts do not plot; drawing leaves `outputs/data/` byte-identical; every planned figure is drawn and audited; the sign rules (cumulative bars end at their net, stacked series up + down = net, materials and stages never negative); the Fig4 waterfalls and Fig5 reductions add up to the run totals; the TL steps; Fig3b's interval from the draws; Fig1's annual line against the census-interval means; the ED4 / ED5 notes stop when the code and the outputs disagree; the palette file rejects a missing or unknown key, a bad hex and an opacity outside [0, 1]; SF2b: up + down = net for every column and year, and the census-interval means of the annual line = the column nets. |

## Retired in MODEL v4.3.3 (`tests/retired/`)

`test_palette_file.py`, `test_figure_text_rules.py`, `test_figures_v3.py`, `test_figures_v3_3_1.py`,
`test_figures_v3_3_2.py` and `test_figures_v4_3_2.py`: their tests of drawn values against the data live on, unchanged,
in `test_figure_integrity.py`; the rest checked styling (colours, labels, layout), which the tools below check by hand.
`test_reference_legacy.py` locked the superseded MODEL v2.1 Reference (`run_all.py --reference-legacy` no longer runs
it); the v4 regression lock covers the current model.

## Run by hand (not tests)

* `python tools/check_figure_text.py` — the text rules of the figure suite (en-dash year ranges, thousands separators,
  the typographic minus) on every drawn figure.
* `python tools/palette_check.py` — the colour-vision check of the palette (CAM02-UCS under simulated deficiencies) and
  the zone lightness order; writes `docs/PALETTE.md` and `docs/palette_preview.png`.
* `python tools/palette_coverage.py` — redraws every final figure with a probe palette and reports any colour or fade
  that does not come from `palette.toml` (or the declared neutrals and context fades of `figures/style.py`).
