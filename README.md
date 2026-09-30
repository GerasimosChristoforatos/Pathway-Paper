# New Zealand new residential floor area and embodied carbon, 2026–2050

A bottom-up projection of new residential floor area and its embodied carbon
by typology, reason for building and material. How the model works:
[ARCHITECTURE.md](ARCHITECTURE.md). Critical assessment and open issues:
[ASSESSMENT.md](ASSESSMENT.md). Every change and its effect on the results:
[CHANGELOG.md](CHANGELOG.md).

## Running

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # pinned; Python 3.11
python run_all.py                      # about 5 minutes
```

`run_all.py` runs, in order:
* `Building_factors.py`, then `Boss.py` (central run);
* `Diagnostics.py`, `Sensitivity.py` and `MonteCarlo.py`;
* the tests (`tests/`) and the validation harness (`validation.py`).

It writes everything to `outputs/`. Figures go to `outputs/figures/` and logs to
`outputs/logs/`; both folders are regenerated on every run and are not
versioned. The headline numbers are in `outputs/metrics.json`.

`data/` holds inputs only. Inputs rebuilt from raw downloads are produced by
the scripts in `data/`, never edited by hand.

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
| `data/derived/consents_monthly.csv` (monthly new dwellings, floor area and value by type; default via `Boss.CONSENT_SOURCE`) | Stats NZ, *Building consents issued: July 2026*, "Download data" CSV zip, <https://www.stats.govt.nz/assets/Uploads/Building-consents-issued/Building-consents-issued-July-2026/Download-data/building-consents-issued-july-2026.zip> | file "Building consents by region (Monthly).csv"; New Zealand / New / Actual; series `BLDM.*` (Infoshare group Building consents – BLD) | 2026-09-29 | Raw → script (`data/build_consents.py`). Identical to `consentdata.xlsx` in every month 1990-04..2025-12, and to the published annual totals for years ended June and July 2026 |
| `data/consentdata.xlsx` (`CONSENT_SOURCE='legacy_xlsx'`) | Stats NZ building consents (Infoshare, BLD) | [placeholder: Infoshare series IDs] | [placeholder] | Supplied; kept for reproducing the original runs |
| `data/histpopdata.xlsx` | Stats NZ, "Population summary figures" (estimated resident population at 31 December) | [placeholder: table ID] | [placeholder] | Supplied |
| `data/popdata.xlsx` | Stats NZ, *National population projections: 2024(base)–2078*, published 4 June 2025 (stated in the file), Table 1 | Table 1 | [placeholder] | Supplied |
| `data/Householddata.xlsx` | Stats NZ, *Family and household projections: 2018(base)–2043*, published 15 December 2021 (stated in the file) | Table 1 | [placeholder] | Supplied |
| `data/oldhouseholddata.xlsx` | Stats NZ, *Dwelling and household estimates: March 2026 quarter*, published 7 April 2026 (stated in the file) | Tables 1–2 (Infoshare group DDE) | [placeholder] | Supplied |
| `data/subnational-population-projections-2018base-2048.xlsx` | Stats NZ, *Subnational population projections: 2018(base)–2048*, published 31 March 2021 (stated in the file) | Table 1 (Table 4 is titled "update"; see ASSESSMENT.md) | [placeholder] | Supplied |
| `data/occ-unocc-2013.xlsx` | Stats NZ, *2013 Census QuickStats about housing* | Tables 1–2 | [placeholder] | Supplied |
| `data/derived/census_dwellings.csv` (2018, 2023 census occupancy, private dwellings; default via `Boss.CENSUS_SOURCE`) | Stats NZ Aotearoa Data Explorer, `STATSNZ:CEN23_HOU_018(1.0)` "Dwelling occupancy status and dwelling type for dwellings, (RC, TALB, SA2, Health), 2013, 2018, and 2023 Censuses" (table last updated 2024-07-24), xlsx filtered to the Total – New Zealand rows; cross-check `STATSNZ:CEN23_TBT_001(1.0)` (unfiltered SDMX-CSV, last updated 2024-09-05) | occupancy status × dwelling type | downloaded by the author 2026-09-29 (see MANIFEST) | Raw → script (`data/build_census.py`); 21 cross-checks within ±3 (random rounding). The original hard-coded `CENSUS_LATER` equals the ALL-dwelling-type totals (it included unoccupied non-private dwellings, counted from 2018); kept as `CENSUS_SOURCE='hardcoded'` |
| `data/derived/population_nowcast.csv` (observed population growth, year ended June 2026; A1, `Boss.NOWCAST_POPULATION`) | Stats NZ, *National population estimates: At 30 June 2026* (information release, provisional), <https://www.stats.govt.nz/information-releases/national-population-estimates-at-30-june-2026/> | release text: ERP at 30 June 2026 and growth over the year ended June 2026 | 2026-09-29 (see `data/raw/MANIFEST.csv`) | Raw → script (`data/build_population_nowcast.py`). INTERIM: provisional headline figures. To be replaced by the quarterly ERP series from Infoshare (Population → Population Estimates – DPE), which would also give the 31 March ERP for the census-date household-size test |
| `data/derived/population_quarterly.csv` (quarterly ERP, total of both sexes, 1991Q1-2026Q2; A1 default via `Boss.POP_NOWCAST_SOURCE` and `Boss.CHANNEL_POP_DATE`) | Stats NZ Infoshare, Population Estimates - DPE, "Estimated Resident Population (Mean Quarter Ended) by Sex (1991+) (Qrtly-Mar/Jun/Sep/Dec)" | series DPE059AA (total); table last updated 18 August 2026 | exported by the author 2026-09-30 (see `data/raw/MANIFEST.csv`) | Raw → script (`data/build_population_quarterly.py`). MEAN-quarter values (average over the quarter), dated at the quarter's centre; not point estimates at quarter end. Convention: history = 31 December ERP; projection growth = years ended June applied to calendar years; 2026 nowcast = June quarter 2026 minus June quarter 2025 |
| `data/building_data.xlsx` | 16 New Zealand case-study LCAs (the authors' compilation) | sheets 1–3 | n/a | Supplied; the source studies and the soil-order weights behind the 58.77 kg/m² average are to be cited [placeholder] |

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
| `Boss.py` | central run: data, calibration, projection, reporting |
| `Building_factors.py` | case-study carbon factors → `outputs/factors/` |
| `Diagnostics.py`, `Sensitivity.py`, `MonteCarlo.py` | figures, one-at-a-time sensitivities, joint uncertainty and Sobol indices |
| `validation.py` | rolling-origin hindcast and 2026 out-of-sample check |
| `tests/` | identity tests; engine equivalence against frozen legacy code (`tests/legacy/`, `tests/legacy_flags.py`) |
| `tools/` | metrics and CHANGELOG generation |
| `docs/assessment_evidence/` | scripts behind every number in ASSESSMENT.md, as of Step 1 |
