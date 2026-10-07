# New Zealand new residential floor area and embodied carbon, 2026–2050

A bottom-up projection of new residential floor area and its embodied carbon
by typology, reason for building and material. How the model works:
[ARCHITECTURE.md](ARCHITECTURE.md). Every setting and its basis:
[ASSUMPTIONS.md](ASSUMPTIONS.md). Headline results: [RESULTS.md](RESULTS.md) and
`outputs/BASELINE_DRAFT.md`. Figures: [FIGURES.md](FIGURES.md). Release notes:
[CHANGELOG.md](CHANGELOG.md).

This is baseline-pb-v3: replacements and repaints (B2, B4) resolved in time,
committed post-2050 emissions, and A4–A5 decarbonisation (see CHANGELOG.md).
With whole life at construction, A4–A5 held, it reproduces baseline-pb-v2
exactly (`tests/test_v3.py`), and with frozen technology v1.2.1
(`tests/test_regression_v1_2_1.py`). Options and documents removed in earlier
releases are preserved at the git tags `baseline-v1.2.1`, `baseline-PB_v1.2` and
`baseline-PB_v2`.

## Running

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # pinned; Python 3.11
python run_all.py                      # full run; the only basis for reported results and tags
python run_all.py --quick              # development only: every output marked "QUICK RUN, not for reporting"
```

Measured for baseline-pb-v3 on a 4-core machine: the default full run takes 880 s
(about 15 minutes, including the frozen-technology check run), `--quick` 348 s
(about 6 minutes). `--quick` uses 1,000 instead of 5,000 Monte Carlo draws per
scenario and 128 Sobol base samples, skips the frozen-technology Monte Carlo and
the Monte Carlo regression checks, and marks `metrics.json`, the generated
documents and every figure as a quick run.

`run_all.py` runs, in order:
* `Building_factors.py`, then `Boss.py` (central run);
* `Diagnostics.py`, `Sensitivity.py` and `MonteCarlo.py`;
* `PB.py`, the planetary-boundary layer (climate change; acquired rights and
  ability to pay), which reads the model outputs and the Monte Carlo draws;
* the validation harness (`validation.py`), `gap_2026.py` and the report tools
  (`tools/`: near-term rule, scenarios, reconciliation of the accounting, report
  figures);
* a frozen-technology check run (`DECARB_MODE = 'none'`, A4–A5 held, whole life
  at construction: Boss, Sensitivity, MonteCarlo, the scenario table and PB,
  written to `outputs/frozen/`, figures not saved);
* the tests (`tests/`, including the v1.2.1 regression test, which compares the
  frozen-technology run with v1.2.1);
* metrics, `RESULTS.md`, `ASSUMPTIONS.md`, `outputs/BASELINE_DRAFT.md` and
  `outputs/PB_METHODS_DRAFT.md`.

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

**Planetary-boundary layer (PB.py) inputs.**

| model input | source | table / series | download date | status |
|---|---|---|---|---|
| `data/derived/nz_gdp_quarterly.csv` (GDP and final consumption expenditure, quarterly, NZD million, nominal) | Stats NZ Infoshare, *GDP(E), Nominal, Actual, Total (Qrtly-Mar/Jun/Sep/Dec)*, last updated 19 March 2026 (stated in the file) | table SNE022AA; file `data/raw/GDP_Data.xlsx` | supplied by the author 2026-10-04 (see MANIFEST) | Raw → script (`data/build_gdp.py`) |
| `data/derived/wpp2024_population_median.csv` (World and New Zealand, 1 July, persons) | United Nations, DESA, Population Division (2024), *World Population Prospects 2024*, Probabilistic Population Projections, <https://population.un.org/wpp/> | file PPP/POPTOT (POP/DB/WPP/Rev.2024/PPP/POPTOT), sheet "Median"; `data/raw/UN_PPP2024_Output_PopTot.xlsx` | supplied by the author 2026-10-04 | Raw → script (`data/build_wpp.py`) |
| `data/derived/wdi_economies.csv`, `wdi_world_aggregate.csv` (population, GDP per capita PPP constant 2021 int-$ and current US$, by economy; WLD aggregate for coverage only) | World Bank, *World Development Indicators*, bulk CSV, release "Last Updated Date 2026-07-13" (stated in the files) | SP.POP.TOTL, NY.GDP.PCAP.PP.KD, NY.GDP.PCAP.CD; `data/raw/API_*_DS2_en_csv_v2_*.zip`; aggregates dropped with each archive's Metadata_Country file | supplied by the author 2026-10-04 | Raw → script (`data/build_wdi.py`) |
| `data/raw/Absolute_Analysis.xlsm` | the author's earlier-manuscript AESA workbook (under review) | sheets 1.Acquired Rights, 2.Equalitarian, 6, 7 | supplied 2026-10-04 | Supplied; **local only (git-ignored)**; read only by reproduction tests, which skip without it |
| `data/derived/lca_events.csv` (replacement / repaint event counts and building lifespan per item line; time-resolved B2/B4) | LCAQuick v3.6 root tables of the 16 case studies (Christoforatos & Pickering 2025); built by `data/build_lca_events.py`, which matches every line to the item table (16 lines without B2/B4 excluded: `data/derived/lca_excluded_lines.csv`) | file `data/raw/Analytical_LCA_Results_Database.xlsx`, one sheet per building | supplied 2026-10-07 | Supplied |
| `data/derived/material_items.csv` (case-study A1–A3 etc. by building and EPD item; `Boss.DECARB_MODE = 'horup_item'`) | the 16 case-study LCAs of Christoforatos & Pickering (2025) (as `data/building_data.xlsx`) at item resolution; built by `data/build_material_items.py`, which checks it against `building_data.xlsx` | file `data/raw/epd-level_materials.xlsx`, sheet "ROOOOOT" | supplied 2026-10-05 | Supplied |
| `data/derived/horup2025_table_s4.csv` (relative GWP of material production 2025/2030/2040/2050; `Boss.DECARB_MODE`) | Horup et al. (2025), *Sci. Total Environ.* 966, 178780, supplementary material mmc1.xlsx, <https://doi.org/10.1016/j.scitotenv.2025.178780> | sheet "Table S4" (average of 9 premise scenarios relative to ecoinvent 3.9.1), column C; checked against column E | supplied by the author 2026-10-05 (SHA-256 in MANIFEST) | Raw → script (`data/build_horup.py`); the workbook is kept in `refs/` (not versioned) |
| SOS, I_glob (constants in `PB.py`) | Bjørn & Hauschild (2015), *Int J Life Cycle Assess* 20:1005-1018, Table 1 and ESM1/ESM2 | see the source check in `outputs/PB_METHODS_DRAFT.md` | n/a | Literature |

The reference papers behind the PB layer (Bjørn & Hauschild 2015 with ESM1/ESM2; Sala et al. 2020 and
corrigendum; Hjalsted et al. 2021 with SI; Horup et al. 2025; Andreasi Bassi et al. 2023; Clausen et
al. 2025; the EC-JRC table of ILCD normalisation factors; the author's manuscript) are kept in `refs/`,
which is git-ignored: the papers are copyrighted and are not distributed. The same folder holds
Resch et al. 2021 (A4–A5 path, timing of replacement emissions) and Habert et al. 2020
(time-resolved accounting of embodied emissions).

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
| `Building_factors.py` | case-study carbon factors and pooled replacement / repaint events → `outputs/factors/` |
| `events.py` | time-resolved B2/B4: event factors, kernels, committed post-2050 emissions |
| `Diagnostics.py` | diagnostic figures `diag_2`-`diag_5`, appendix `diag_3b` |
| `Sensitivity.py` | one-at-a-time sensitivities (`outputs/sensitivity_oat.csv`, `sens_1`, `sens_2`) |
| `MonteCarlo.py` | joint parametric uncertainty within S3-10, S1 and S2; Sobol indices (reference) |
| `aesa.py`, `PB.py` | planetary-boundary layer: boundaries, levels of exceedance, figures `*_pb`, `pb_1`-`pb_6` |
| `validation.py`, `gap_2026.py` | rolling-origin hindcast, 2026 out-of-sample check, 2026 gap decomposition |
| `tools/` | near-term rule and scenario reports, reconciliation of the accounting, report figures and FIGURES.md, metrics, RESULTS.md, ASSUMPTIONS.md, BASELINE_DRAFT.md, PB_METHODS_DRAFT.md |
| `tests/` | accounting identities, census UC correction, soil, near-term rule, validation, events and committed emissions (`test_v3.py`), and the regression tests against v1.2.1 (`regression_v1_2_1.json`) and baseline-pb-v2 (`regression_pb_v2.json`) |
| `data/` | inputs and the scripts that build `data/derived/` from `data/raw/` |

Note: `data/raw/national_population_estimates_june_2026.html` is the release
text behind the interim 2026 population figure used before the quarterly ERP
series; it is kept with its MANIFEST entry but no longer read.
