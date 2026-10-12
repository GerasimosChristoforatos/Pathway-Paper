# New Zealand new residential floor area and embodied carbon, 2026–2050

A bottom-up, demand-driven model of the new residential floor area New Zealand builds in
2026–2050 and the embodied carbon it carries, in three layers:

* **Baseline projection** (`projection.py`): people → households → dwellings required →
  floor area by reason for building (demand bands) → carbon by life-cycle stage (materials
  A1–A3, construction A4–A5, maintenance B2/B4, soil carbon loss) and the emissions committed after
  2050, with replacement variants, one-at-a-time sensitivities, Monte Carlo with Sobol indices
  and validation against the census record.
* **Planetary-boundary layer (AESA)** (`boundaries.py`, `aesa.py`): an absolute environmental
  sustainability assessment for climate change; the carbon 2026–2050 against the sector's
  share of a global carrying capacity under two allocation principles, acquired rights (AR) and
  ability to pay (AtP), reported side by side and never averaged.
* **Pathways** (`levers.py`, `pathways.py`): nine levers in four families (P1 Space per person:
  L1 Dwelling size, L2 Household occupancy; P2 Existing stock: L3 Vacancy, L4 Overbuild absorption,
  L5 Building lifetime extension; P3 Construction: L6 Material carbon, L7 Construction-stage carbon;
  P4 Land: L8 Soil-aware planning, L9 Brownfield development) and P5 Combined, at Moderate and
  Ambitious settings; only population growth is untargeted. Their Shapley attribution, the
  back-cast to the AR budget and a hyper-optimistic theoretical limit (TL = P5 Moderate with
  TL1–TL10 at full strength from 2027, each the limit of one lever; a thought experiment, not a
  pathway). The pathway Monte Carlo runs the 5,000 Reference draws through P5 and TL
  (`pathways_mc.py`) and analyses what drives them (SRC, PRCC, LOWESS, conditional TL; `mcstats.py`).
  The paper shows the Reference, P1–P5 at the Moderate setting with full roll-out by 2035, and TL;
  every other setting is Extended Data; the story in six figures is in the key figures.

Release **MODEL v2.1.1** (see [CHANGELOG.md](CHANGELOG.md); cite with [CITATION.cff](CITATION.cff)).

![Fig1. How the model works](outputs/paper/Fig1_model_schematic.png)

## Results

| what | where |
|---|---|
| **Paper**: headline findings, Fig1–Fig6 with captions, Table 1 (levers and TL assumptions) and Table 2 (results with Monte Carlo intervals) | [outputs/paper/PAPER.md](outputs/paper/PAPER.md) |
| **Extended Data**: ED1–ED13 (grouped sensitivity tornados and paths, Monte Carlo, Ambitious settings, roll-out timing, the TL attribution, single levers, Low / High replacement, Monte Carlo insights) | [outputs/extended_data/EXTENDED_DATA.md](outputs/extended_data/EXTENDED_DATA.md) |
| **Key figures**: K1–K6 (demand bands, Reference carbon, annual emissions against the boundaries, solution space, the sequential band waterfall, the schematic) | [outputs/key_figures/KEY_FIGURES.md](outputs/key_figures/KEY_FIGURES.md) |
| **Diagnostics**: every other figure, by group, with notes | [outputs/diagnostics/DIAGNOSTICS.md](outputs/diagnostics/DIAGNOSTICS.md) |
| Grouped one-at-a-time sensitivity tables (Reference carbon, P5 carbon, planetary boundary, replacement variants) | [outputs/data/sensitivity/](outputs/data/sensitivity/) |
| Results summary | [outputs/reports/RESULTS.md](outputs/reports/RESULTS.md) |
| Methods draft: baseline projection, planetary-boundary layer (AESA), pathways and the theoretical limit | [outputs/reports/METHODS_DRAFT.md](outputs/reports/METHODS_DRAFT.md) |
| The pathway levers and the theoretical-limit assumptions, with the adoption rule (full text of Table 1) | [outputs/reports/LEVERS_TABLE.md](outputs/reports/LEVERS_TABLE.md) |
| Every assumption and setting with its basis (data, literature, author decision, judgement) | [outputs/reports/ASSUMPTIONS.md](outputs/reports/ASSUMPTIONS.md) |
| Validation, reality checks, the 2026 gap and overbuild, variants, reconciliation | [outputs/reports/](outputs/reports/) |
| Every number (CSV, JSON) | [outputs/data/](outputs/data/) |
| Every output file, what it holds and the script that writes it | [outputs/INDEX.md](outputs/INDEX.md) |
| How the model works, script by script | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Vocabulary and the map from earlier names (incl. model-v1.1.0 H/D figures → Fig/ED); figure plan; sensitivity plan; palette | [docs/RENAMING.md](docs/RENAMING.md), [docs/FIGURE_PLAN.md](docs/FIGURE_PLAN.md) ([design](docs/FIGURE_PLAN_v2.md)), [docs/SENSITIVITY_PLAN.md](docs/SENSITIVITY_PLAN.md), [docs/PALETTE.md](docs/PALETTE.md) |

Every number in the documents and figures is read from `outputs/data/`, which the full run
writes; nothing is typed by hand. The outputs committed with a release are those of its full
run.

**Output layout.** `outputs/paper/` holds what goes into the paper (figures as PNG, vector PDF and a
source-data CSV of every plotted value; the two tables as Markdown and CSV; PAPER.md);
`outputs/extended_data/` the Extended Data figures in the same formats; `outputs/diagnostics/` every
other figure (PNG) with DIAGNOSTICS.md and the audit record of every figure (`_audit/`);
`outputs/data/` every number; `outputs/reports/` the generated documents. The model-v1.1.0 folder
`outputs/headline/` is retired (map: docs/RENAMING.md, section 6).

## Running

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # pinned; Python 3.11
python run_all.py                      # full run: the only basis for reported results
python run_all.py --pathways-only      # the pathway layer only (the projection is unchanged)
python run_all.py --export             # also vector PDF and source-data CSV of the paper, Extended Data and key figures (default: PNG only)
python run_all.py --quick              # development only: outputs marked "QUICK RUN, not for reporting"
```

| run mode | what it runs | time |
|---|---|---|
| full | every step below, then the tests | about 12–24 min depending on the machine (Monte Carlo and AESA most of it) |
| `--pathways-only` | `pathways.py` (the projection in memory), `pathways_mc.py`, `tools/sensitivity_tables.py`, `paper.py`, `extended_data.py`, the pathway documents, `tools/methods_draft.py`, `indexes.py`, then the pathway, pathway Monte Carlo and sensitivity-table tests, the regression locks, the release checks and the byte manifest | about 2 min (133 s on the release machine) |
| `--quick` | as the full run with 1,000 instead of 5,000 Monte Carlo draws per variant and 128 Sobol base samples, without the frozen-technology Monte Carlo and AESA steps; Monte Carlo regression checks skipped | not timed for this release |

The full run executes, each script in its own process with the non-interactive backend and
its console output in `outputs/logs/<step>.log`:
`Building_factors.py` → `projection.py` → `Diagnostics.py` → `Sensitivity.py` →
`MonteCarlo.py` → `boundaries.py` (reads the Monte Carlo draws) → `validation.py` →
`gap_2026.py` → `tools/overbuild_2026.py` → `tools/replacement_scenarios.py` →
`tools/reconciliation.py` → `tools/figures_report.py` → the frozen-technology check run
(2025 carbon factors held, whole life at construction; data in
`outputs/data/frozen_technology/`, no figures) → `pathways.py` → `pathways_mc.py` →
`tools/sensitivity_tables.py` → `tools/metrics.py` → `paper.py` → `extended_data.py` →
`tools/results.py` → `tools/assumptions.py` → `tools/pathways_methods.py` →
`tools/methods_draft.py` → `tools/check_outputs.py` → `indexes.py` → the tests, last.
A full run first clears the figures, data and reports, so nothing stale survives. A failed step
prints its name and the log to read, and the run stops (exit code 1 from the command line).

### Running in Spyder

1. Open `run_all.py` and press Run (F5), or type `runfile('run_all.py')` in the IPython
   console; for the pathway layer only, `runfile('run_all.py', args='--pathways-only')`.
   Every path is resolved from the repository folder, so the console's working directory does
   not matter.
2. Each step runs in its own process with figures saved, not shown; the console prints one
   line per step. If a step fails, the console names the step and the log file to open; no
   `SystemExit` traceback is raised and the console stays usable.
3. To look at figures interactively, run a single script instead (`projection.py`,
   `Diagnostics.py`, `MonteCarlo.py`, `boundaries.py`): each shows its figures. `paper.py` and
   `extended_data.py` always write their figures to `outputs/paper/` and `outputs/extended_data/`;
   `pathways.py` writes its diagnostics only with `PATHWAY_SAVE_FIGURES=1`, as `run_all.py`
   sets it.
4. To run the tests on their own: `!python -m pytest -q tests` in the console (or
   `python -m pytest -q tests` in a terminal), from any folder.

## Tests and reproducibility

* **Numerical regression lock** (`tests/test_regression_model_v1.py`): every one of the
  488,484 numbers the pipeline reported at commit ee37ef1 (pathways v3.1), captured in
  `tests/regression_model_v1.json`, is found at its release location through the renaming map
  (`naming.LEGACY`, docs/RENAMING.md) and reproduced to 1e-12 relative, except the values of the
  adoption-path sensitivities (full roll-out by 2030 and by 2045) that MODEL v1.1.0 changes, each
  listed with its old and new value in `tests/regression_model_v1_1.json`.
* **Coverage lock** (`tests/test_regression_model_v2.py`): every number in `outputs/data/` is
  locked: the values no earlier capture holds (the v1.1.0 data and the values MODEL v2.0.0 adds)
  are listed in `tests/regression_model_v2_additions.json` and reproduced to 1e-12, and no other
  number may appear or change.
* **Byte reproducibility** (`tests/output_manifest_model_v2.json`): the SHA-256 of every
  committed output; a re-run reproduces them (figures are written without software or date
  metadata).
* **Release checks** (`tests/test_release.py`): the new values add up to the locked numbers;
  every planned figure (paper, Extended Data, diagnostics) exists within its print width and no
  other; maintenance is drawn as its own layer only in Fig2–Fig4 and the band breakdowns D25, D26, D32 (figure audit);
  every output file is indexed once; no old term in any reader-facing text; every figure module
  uses the shared style.
* **Pathway Monte Carlo** (`tests/test_pathways_mc.py`): the central draw reproduces the
  deterministic Reference, P5 and TL runs to 1e-9; the Reference percentiles equal those of the
  AESA layer. **Sensitivity tables** (`tests/test_sensitivity_tables.py`): every row agrees with
  its source; the new runs reproduce the existing ones they overlap.
* Model tests: accounting identities, census under-construction correction, soil, the 2026
  overbuild, validation, decarbonisation, time-resolved events and committed emissions, the
  AESA equations against their sources, and the pathways (identity with the Reference,
  Harrell-Davis estimator, exact Shapley values, constraints).

## Layout

| path | what |
|---|---|
| `projection.py` | the baseline projection: data, calibration, projection, figures D01–D03, D08, D09, D13 |
| `paper.py`, `extended_data.py`, `key_figures.py` | the paper (Fig1–Fig6, Tables 1–2, PAPER.md), Extended Data (ED1–ED13, EXTENDED_DATA.md) and the key figures (K1–K6, KEY_FIGURES.md), from the data files only |
| `engine.py` | the forward model (pure functions), shared by the projection, the Monte Carlo and the pathways |
| `Building_factors.py`, `events.py` | case-study carbon factors; time-resolved maintenance (B2, B4) and committed emissions |
| `Diagnostics.py`, `Sensitivity.py`, `MonteCarlo.py`, `validation.py`, `gap_2026.py` | diagnostics, one-at-a-time sensitivities (data only), Monte Carlo and Sobol indices, rolling-origin hindcast, 2026 gap |
| `aesa.py`, `boundaries.py` | planetary-boundary layer (AESA): boundaries, levels of exceedance |
| `levers.py`, `pathways.py`, `pathways_mc.py`, `mcstats.py` | levers, pathways, attribution, back-cast, solution space, theoretical limit; the pathway Monte Carlo and its insight statistics (numpy / scipy; checked against statsmodels) |
| `indexes.py` | DIAGNOSTICS.md and outputs/INDEX.md |
| `naming.py`, `style.py`, `plotting.py`, `figaudit.py`, `layout.py`, `figure_plan.py` | vocabulary and the renaming map; palette, sizes and saving; shared drawing rules; figure audit; output layout; figure plan |
| `tools/` | reports (overbuild, variants, reconciliation, reality checks, metrics, results, assumptions, methods draft, levers table), the grouped sensitivity tables, output checks, design documents, palette check |
| `tests/` | the tests above |
| `data/` | inputs only, and the scripts that build `data/derived/` from `data/raw/` |
| `docs/` | renaming map, figure plan (and its design), sensitivity plan, palette, the hooks of the levers into the model |

## Data provenance

`data/raw/MANIFEST.csv` records the URL, SHA-256 and download date (UTC) of every file
fetched by `data/fetch_sources.py`. Large archives (`*.zip`) are not versioned; re-download
them and check them against the manifest. Inputs rebuilt from raw downloads are produced by the
scripts in `data/`, never edited by hand.

**Status key.** *Raw → script* = the model input is built by a script from the unmodified
download. *Supplied* = the workbook was supplied with the project; its provenance is only what
the file itself states, and it has not yet been rebuilt from a recorded download.

| model input | source | table / series | download date | status |
|---|---|---|---|---|
| `data/derived/consents_monthly.csv` (monthly new dwellings, floor area and value by type) | Stats NZ, *Building consents issued: July 2026*, "Download data" CSV zip, <https://www.stats.govt.nz/assets/Uploads/Building-consents-issued/Building-consents-issued-July-2026/Download-data/building-consents-issued-july-2026.zip> | file "Building consents by region (Monthly).csv"; New Zealand / New / Actual; series `BLDM.*` (Infoshare group Building consents – BLD) | 2026-09-29 | Raw → script (`data/build_consents.py`). Identical to `consentdata.xlsx` in every month 1990-04..2025-12, and to the published annual totals for years ended June and July 2026 |
| `data/consentdata.xlsx` | Stats NZ building consents (Infoshare, BLD) | [placeholder: Infoshare series IDs] | [placeholder] | Supplied; superseded by `consents_monthly.csv` and not read by the model (kept as the originally supplied record) |
| `data/histpopdata.xlsx` | Stats NZ, "Population summary figures" (estimated resident population at 31 December) | [placeholder: table ID] | [placeholder] | Supplied |
| `data/popdata.xlsx` | Stats NZ, *National population projections: 2024(base)–2078*, published 4 June 2025 (stated in the file), Table 1 | Table 1 | [placeholder] | Supplied |
| `data/Householddata.xlsx` | Stats NZ, *Family and household projections: 2018(base)–2043*, published 15 December 2021 (stated in the file) | Table 1 | [placeholder] | Supplied |
| `data/oldhouseholddata.xlsx` | Stats NZ, *Dwelling and household estimates: March 2026 quarter*, published 7 April 2026 (stated in the file) | Tables 1–2 (Infoshare group DDE) | [placeholder] | Supplied |
| `data/subnational-population-projections-2018base-2048.xlsx` | Stats NZ, *Subnational population projections: 2018(base)–2048*, published 31 March 2021 (stated in the file) | Table 1 (Table 4 is titled "update"; see `FILE_POP_SIZE_PAIR` in projection.py) | [placeholder] | Supplied |
| `data/occ-unocc-2013.xlsx` | Stats NZ, *2013 Census QuickStats about housing* | Tables 1–2 | [placeholder] | Supplied |
| `data/derived/census_dwellings.csv` (2018, 2023 census occupancy, private dwellings) | Stats NZ Aotearoa Data Explorer, `STATSNZ:CEN23_HOU_018(1.0)` "Dwelling occupancy status and dwelling type for dwellings, (RC, TALB, SA2, Health), 2013, 2018, and 2023 Censuses" (table last updated 2024-07-24), xlsx filtered to the Total – New Zealand rows; cross-check `STATSNZ:CEN23_TBT_001(1.0)` (unfiltered SDMX-CSV, last updated 2024-09-05) | occupancy status × dwelling type | downloaded by the author 2026-09-29 (see MANIFEST) | Raw → script (`data/build_census.py`); 21 cross-checks within ±3 (random rounding). Private dwellings only: the all-dwelling-type totals include unoccupied non-private dwellings, counted from 2018 |
| `data/derived/population_quarterly.csv` (quarterly ERP, total of both sexes, 1991Q1-2026Q2; the 2026 population nowcast, `projection.NOWCAST_POPULATION`) | Stats NZ Infoshare, Population Estimates - DPE, "Estimated Resident Population (Mean Quarter Ended) by Sex (1991+) (Qrtly-Mar/Jun/Sep/Dec)" | series DPE059AA (total); table last updated 18 August 2026 | exported by the author 2026-09-30 (see `data/raw/MANIFEST.csv`) | Raw → script (`data/build_population_quarterly.py`). MEAN-quarter values (average over the quarter), dated at the quarter's centre; not point estimates at quarter end. Convention: history = 31 December ERP; projection growth = years ended June applied to calendar years; 2026 nowcast = June quarter 2026 minus June quarter 2025 |
| `data/building_data.xlsx` | 16 New Zealand case-study LCAs: Christoforatos G, Pickering K (2025), "Embodied impacts of residential stocks; multi-level assessment of materials, buildings, typologies and functional units to support policymaking towards sustainable housing", *Smart and Sustainable Built Environment* (ahead of print), <https://doi.org/10.1108/SASBE-06-2025-0304> (source and benchmarking). Soil sheet: 58.77 kg CO₂e/m² footprint, area-weighted over the 10 soil orders of Auckland land zoned for urbanisation to ~2050: Christoforatos G, Pickering K, Schipper LA (2026), *Journal of Environmental Management* 415, 130603, <https://doi.org/10.1016/j.jenvman.2026.130603> | sheets 1–3 | n/a | Supplied |

**Planetary-boundary layer (AESA; boundaries.py) inputs.**

| model input | source | table / series | download date | status |
|---|---|---|---|---|
| `data/derived/nz_gdp_quarterly.csv` (GDP and final consumption expenditure, quarterly, NZD million, nominal) | Stats NZ Infoshare, *GDP(E), Nominal, Actual, Total (Qrtly-Mar/Jun/Sep/Dec)*, last updated 19 March 2026 (stated in the file) | table SNE022AA; file `data/raw/GDP_Data.xlsx` | supplied by the author 2026-10-04 (see MANIFEST) | Raw → script (`data/build_gdp.py`) |
| `data/derived/wpp2024_population_median.csv` (World and New Zealand, 1 July, persons) | United Nations, DESA, Population Division (2024), *World Population Prospects 2024*, Probabilistic Population Projections, <https://population.un.org/wpp/> | file PPP/POPTOT (POP/DB/WPP/Rev.2024/PPP/POPTOT), sheet "Median"; `data/raw/UN_PPP2024_Output_PopTot.xlsx` | supplied by the author 2026-10-04 | Raw → script (`data/build_wpp.py`) |
| `data/derived/wdi_economies.csv`, `wdi_world_aggregate.csv` (population, GDP per capita PPP constant 2021 int-$ and current US$, by economy; WLD aggregate for coverage only) | World Bank, *World Development Indicators*, bulk CSV, release "Last Updated Date 2026-07-13" (stated in the files) | SP.POP.TOTL, NY.GDP.PCAP.PP.KD, NY.GDP.PCAP.CD; `data/raw/API_*_DS2_en_csv_v2_*.zip`; aggregates dropped with each archive's Metadata_Country file | supplied by the author 2026-10-04 | Raw → script (`data/build_wdi.py`) |
| `data/raw/Absolute_Analysis.xlsm` | the author's earlier-manuscript AESA workbook (under review) | sheets 1.Acquired Rights, 2.Equalitarian, 6, 7 | supplied 2026-10-04 | Supplied; **local only (git-ignored)**; read only by reproduction tests, which skip without it |
| `data/derived/lca_events.csv` (replacement and repaint event counts and building lifespan per item line; time-resolved maintenance B2/B4) | LCAQuick v3.6 root tables of the 16 case studies (Christoforatos & Pickering 2025); built by `data/build_lca_events.py`, which matches every line to the item table (16 lines without B2/B4 excluded: `data/derived/lca_excluded_lines.csv`) | file `data/raw/Analytical_LCA_Results_Database.xlsx`, one sheet per building | supplied 2026-10-07 | Supplied |
| `data/derived/material_items.csv` (case-study A1–A3 etc. by building and EPD item; `projection.DECARB_MODE = 'horup_item'`) | the 16 case-study LCAs of Christoforatos & Pickering (2025) (as `data/building_data.xlsx`) at item resolution; built by `data/build_material_items.py`, which checks it against `building_data.xlsx` | file `data/raw/epd-level_materials.xlsx`, sheet "ROOOOOT" | supplied 2026-10-05 | Supplied |
| `data/derived/horup2025_table_s4.csv` (relative GWP of material production 2025/2030/2040/2050; `projection.DECARB_MODE`) | Horup et al. (2025), *Sci. Total Environ.* 966, 178780, supplementary material mmc1.xlsx, <https://doi.org/10.1016/j.scitotenv.2025.178780> | sheet "Table S4" (average of 9 premise scenarios relative to ecoinvent 3.9.1), column C; checked against column E | supplied by the author 2026-10-05 (SHA-256 in MANIFEST) | Raw → script (`data/build_horup.py`); the workbook is kept in `refs/` (not versioned) |
| SOS, I_glob (constants in `boundaries.py`) | Bjørn & Hauschild (2015), *Int J Life Cycle Assess* 20:1005-1018, Table 1 and ESM1/ESM2 | see the source check in `outputs/reports/METHODS_DRAFT.md` (part 2) | n/a | Literature |

The reference papers behind the planetary-boundary layer (Bjørn & Hauschild 2015 with ESM1/ESM2;
Sala et al. 2020 and corrigendum; Hjalsted et al. 2021 with SI; Horup et al. 2025; Andreasi Bassi
et al. 2023; Clausen et al. 2025; the EC-JRC table of ILCD normalisation factors; the author's
manuscript) are kept in `refs/`, which is git-ignored: the papers are copyrighted and are not
distributed. The same folder holds Resch et al. 2021 (A4–A5 path, timing of replacement
emissions) and Habert et al. 2020 (time-resolved accounting of embodied emissions).

**Documentation cited:** Stats NZ DataInfo+, "Dwelling occupancy status (information about this
variable and its quality)", 2018 Census,
<https://datainfoplus.stats.govt.nz/Item/nz.govt.stats/9b4c0bf9-2b8c-4b54-aa6d-fa51e07bd4d5>.
The page is saved as `data/raw/datainfo_dwelling_occupancy_status.html` and was accessed on
2026-09-29. It states:
* "Dwelling occupancy status did not receive a quality rating in 2018";
* "the change in the proportion of unoccupied residents away versus unoccupied empty indicates a
  break in the time series";
* "the use of administrative data to provide evidence that a dwelling with no 2018 Census
  response was usually occupied may have contributed to the increase in 'Unoccupied - residents
  away' dwellings for 2018".

Note: `data/raw/national_population_estimates_june_2026.html` is the release text behind the
interim 2026 population figure used before the quarterly ERP series; it is kept with its
MANIFEST entry but no longer read.

Earlier versions and their outputs are preserved at their git tags (CHANGELOG.md).
