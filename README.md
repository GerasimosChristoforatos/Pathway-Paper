# New Zealand new residential floor area and embodied carbon, 2026–2050

A bottom-up projection of new residential floor area and its embodied carbon
by typology, reason for building and material. How the model works:
[ARCHITECTURE.md](ARCHITECTURE.md). Every setting and its basis:
[ASSUMPTIONS.md](ASSUMPTIONS.md). Headline results: [RESULTS.md](RESULTS.md) and
`outputs/BASELINE_DRAFT.md`. Figures: [FIGURES.md](FIGURES.md). Release notes:
[CHANGELOG.md](CHANGELOG.md).

This is baseline v2: a cleaned release of v1.2.1 with identical results
(checked by `tests/test_regression_v1_2_1.py`). The full development history,
including every option and document removed here, is at the git tag
`baseline-v1.2.1`.

## Running

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # pinned; Python 3.11
python run_all.py                      # about 5 minutes
```

`run_all.py` runs, in order:
* `Building_factors.py`, then `Boss.py` (central run);
* `Diagnostics.py`, `Sensitivity.py` and `MonteCarlo.py`;
* the validation harness (`validation.py`), `gap_2026.py` and the report tools
  (`tools/`: near-term rule, scenarios, report figures);
* the tests (`tests/`, including the v1.2.1 regression test, which reads the
  outputs written above);
* metrics, `RESULTS.md`, `ASSUMPTIONS.md` and `outputs/BASELINE_DRAFT.md`.

A failed step prints its name and the log to read (`outputs/logs/<step>.log`)
and the run stops; from the command line the exit code is 1.

It writes everything to `outputs/`. Figures go to `outputs/figures/` and logs to
`outputs/logs/`; both folders are regenerated on every run and are not
versioned. The headline numbers are in `outputs/metrics.json`.

`data/` holds inputs only. Inputs rebuilt from raw downloads are produced by
the scripts in `data/`, never edited by hand.

## Running in Spyder

1. Open `run_all.py` and press Run (F5), or type `runfile('run_all.py')` in the
   console. Every path is resolved from the repository folder, so the console's
   working directory does not matter.
2. Each step runs in its own process with figures saved, not shown; the console
   prints one line per step. If a step fails, the console shows which step and
   the log file to open; no `SystemExit` traceback is raised and the console
   stays usable.
3. To look at figures interactively, run a single script instead (`Boss.py`,
   `Diagnostics.py`, `Sensitivity.py`, `MonteCarlo.py`): each shows its figures
   and reloads `Boss` on every run, so edits are picked up without restarting
   the kernel.
4. To run the tests on their own: `!python -m pytest -q tests` in the console
   (or `python -m pytest -q tests` in a terminal), from any folder.

## Data provenance

`data/raw/MANIFEST.csv` records the URL, SHA-256 and download date (UTC) of
every file fetched by `data/fetch_sources.py`. Large archives (`*.zip`) are not
versioned; re-download them and check them against the manifest.

**Status key.** *Raw → script* = the model input is built by a script from the
unmodified download. *Supplied* = the workbook was supplied with the project;
its provenance is only what the file itself states, and it has not yet been
rebuilt from a recorded download.

| model input | source | table / series | download date | status |
|---|---|---|---|---|
| `data/derived/consents_monthly.csv` (monthly new dwellings, floor area and value by type) | Stats NZ, *Building consents issued: July 2026*, "Download data" CSV zip, <https://www.stats.govt.nz/assets/Uploads/Building-consents-issued/Building-consents-issued-July-2026/Download-data/building-consents-issued-july-2026.zip> | file "Building consents by region (Monthly).csv"; New Zealand / New / Actual; series `BLDM.*` (Infoshare group Building consents – BLD) | 2026-09-29 | Raw → script (`data/build_consents.py`). Identical to `consentdata.xlsx` in every month 1990-04..2025-12, and to the published annual totals for years ended June and July 2026 |
| `data/consentdata.xlsx` | Stats NZ building consents (Infoshare, BLD) | [placeholder: Infoshare series IDs] | [placeholder] | Supplied; superseded by `consents_monthly.csv` and not read by the model (kept as the originally supplied record) |
| `data/histpopdata.xlsx` | Stats NZ, "Population summary figures" (estimated resident population at 31 December) | [placeholder: table ID] | [placeholder] | Supplied |
| `data/popdata.xlsx` | Stats NZ, *National population projections: 2024(base)–2078*, published 4 June 2025 (stated in the file), Table 1 | Table 1 | [placeholder] | Supplied |
| `data/Householddata.xlsx` | Stats NZ, *Family and household projections: 2018(base)–2043*, published 15 December 2021 (stated in the file) | Table 1 | [placeholder] | Supplied |
| `data/oldhouseholddata.xlsx` | Stats NZ, *Dwelling and household estimates: March 2026 quarter*, published 7 April 2026 (stated in the file) | Tables 1–2 (Infoshare group DDE) | [placeholder] | Supplied |
| `data/subnational-population-projections-2018base-2048.xlsx` | Stats NZ, *Subnational population projections: 2018(base)–2048*, published 31 March 2021 (stated in the file) | Table 1 (Table 4 is titled "update"; see `FILE_POP_SIZE_PAIR` in Boss.py) | [placeholder] | Supplied |
| `data/occ-unocc-2013.xlsx` | Stats NZ, *2013 Census QuickStats about housing* | Tables 1–2 | [placeholder] | Supplied |
| `data/derived/census_dwellings.csv` (2018, 2023 census occupancy, private dwellings) | Stats NZ Aotearoa Data Explorer, `STATSNZ:CEN23_HOU_018(1.0)` "Dwelling occupancy status and dwelling type for dwellings, (RC, TALB, SA2, Health), 2013, 2018, and 2023 Censuses" (table last updated 2024-07-24), xlsx filtered to the Total – New Zealand rows; cross-check `STATSNZ:CEN23_TBT_001(1.0)` (unfiltered SDMX-CSV, last updated 2024-09-05) | occupancy status × dwelling type | downloaded by the author 2026-09-29 (see MANIFEST) | Raw → script (`data/build_census.py`); 21 cross-checks within ±3 (random rounding). Private dwellings only: the all-dwelling-type totals include unoccupied non-private dwellings, counted from 2018 |
| `data/derived/population_quarterly.csv` (quarterly ERP, total of both sexes, 1991Q1-2026Q2; the 2026 population nowcast, `Boss.NOWCAST_POPULATION`) | Stats NZ Infoshare, Population Estimates - DPE, "Estimated Resident Population (Mean Quarter Ended) by Sex (1991+) (Qrtly-Mar/Jun/Sep/Dec)" | series DPE059AA (total); table last updated 18 August 2026 | exported by the author 2026-09-30 (see `data/raw/MANIFEST.csv`) | Raw → script (`data/build_population_quarterly.py`). MEAN-quarter values (average over the quarter), dated at the quarter's centre; not point estimates at quarter end. Convention: history = 31 December ERP; projection growth = years ended June applied to calendar years; 2026 nowcast = June quarter 2026 minus June quarter 2025 |
| `data/building_data.xlsx` | 16 New Zealand case-study LCAs: Christoforatos G, Pickering K (2025), "Embodied impacts of residential stocks; multi-level assessment of materials, buildings, typologies and functional units to support policymaking towards sustainable housing", *Smart and Sustainable Built Environment* (ahead of print), <https://doi.org/10.1108/SASBE-06-2025-0304> (source and benchmarking). Soil sheet: 58.77 kg CO₂e/m² footprint, area-weighted over the 10 soil orders of Auckland land zoned for urbanisation to ~2050: Christoforatos G, Pickering K, Schipper LA (2026), *Journal of Environmental Management* 415, 130603, <https://doi.org/10.1016/j.jenvman.2026.130603> | sheets 1–3 | n/a | Supplied |

**Documentation cited:** Stats NZ DataInfo+, "Dwelling occupancy status
(information about this variable and its quality)", 2018 Census,
<https://datainfoplus.stats.govt.nz/Item/nz.govt.stats/9b4c0bf9-2b8c-4b54-aa6d-fa51e07bd4d5>.
The page is saved as `data/raw/datainfo_dwelling_occupancy_status.html` and
was accessed on 2026-09-29. It states:
* "Dwelling occupancy status did not receive a quality rating in 2018";
* "the change in the proportion of unoccupied residents away versus
  unoccupied empty indicates a break in the time series";
* "the use of administrative data to provide evidence that a dwelling with no
  2018 Census response was usually occupied may have contributed to the
  increase in 'Unoccupied - residents away' dwellings for 2018".

## Layout

| path | what |
|---|---|
| `engine.py` | the forward model (pure functions), shared by Boss and MonteCarlo |
| `Boss.py` | central run: data, calibration, projection, reporting, figures `boss_01`-`boss_10` |
| `Building_factors.py` | case-study carbon factors → `outputs/factors/` |
| `Diagnostics.py` | diagnostic figures `diag_2`-`diag_5`, appendix `diag_3b` |
| `Sensitivity.py` | one-at-a-time sensitivities (`outputs/sensitivity_oat.csv`, `sens_1`, `sens_2`) |
| `MonteCarlo.py` | joint parametric uncertainty within S3-10, S1 and S2; Sobol indices (reference) |
| `validation.py`, `gap_2026.py` | rolling-origin hindcast, 2026 out-of-sample check, 2026 gap decomposition |
| `tools/` | near-term rule and scenario reports, report figures and FIGURES.md, metrics, RESULTS.md, ASSUMPTIONS.md, BASELINE_DRAFT.md |
| `tests/` | accounting identities, census UC correction, soil, near-term rule, validation, and the v1.2.1 regression test (`regression_v1_2_1.json`) |
| `data/` | inputs and the scripts that build `data/derived/` from `data/raw/` |

Note: `data/raw/national_population_estimates_june_2026.html` is the release
text behind the interim 2026 population figure used before the quarterly ERP
series; it is kept with its MANIFEST entry but no longer read.
