# New Zealand new residential floor area and embodied carbon, 2026–2050

A bottom-up, demand-driven model of the new residential floor area New Zealand builds in
2026–2050 and the embodied carbon it carries, in three layers:

* **Reference projection** (`projection.py`, `engine.py`): people → households → dwellings
  required → floor area by reason for building (demand bands) → carbon by life-cycle stage
  (materials A1–A3, construction A4–A5, maintenance B2/B4, soil carbon loss) and the emissions
  committed after 2050. The 2026 overbuild (building above the requirement) is absorbed by 2035
  on a logistic path: the market builds less until the surplus is re-occupied, and the vacancy
  rate returns to the 2023 census value (5.39%). Replacement variants, one-at-a-time
  sensitivities, Monte Carlo (Latin hypercube; Sobol indices in the full profile) and validation
  against the census record.
* **Planetary-boundary layer (AESA)** (`boundaries.py`, `aesa.py`): an absolute environmental
  sustainability assessment for climate change; the carbon 2026–2050 against the sector's
  share of a global carrying capacity under two allocation principles, acquired rights (AR) and
  ability to pay (AtP), reported side by side and never averaged.
* **Pathways** (`levers.py`, `pathways.py`): nine rule-based levers grouped by the carbon
  reduction hierarchy of PAS 2080:2023 (BSI 2023): S1 Avoid (L1 Household size, L2 Vacancy rate,
  L3 Building lifetime, L4 Extra space, L5 Occupancy density), S2 Switch (L6 Brownfield-first
  development, L7 Soil-aware planning, L8 Material carbon efficiency) and S3 Improve (L9
  Construction-stage carbon); every lever together is the Moderate / Ambitious Pathway. Each
  lever has four ambition levels after the 2050 Pathways Calculator and EUCalc: Reference
  (Level 1), Moderate (Level 2, the exact midpoint), Ambitious (Level 3, one of three documented
  sub-rules) and the theoretical limit (Level 4, TL1–TL9), all adopted on the same logistic path
  2026 → 2035. The theoretical limit (TL) is a thought experiment, not a pathway: dwellings
  released by TL1 and TL2 are re-occupied gradually at a constant share of each year's need.
  Exact Shapley attribution over strategies and over 2⁹ lever subsets, two sequential waterfalls
  (Reference → L1 … L9 = Pathway; Pathway → TL1 … TL9 = TL), the back-cast to the AR budget, a
  λ-sweep of each lever, and the pathway Monte Carlo
  with its insight statistics (`pathways_mc.py`, `mcstats.py`).

Release **MODEL v3.3.0**: the v3.2 model regrouped by PAS 2080 (strategies S1–S3 replace the
families P1–P4; deterministic totals unchanged), a Very High replacement variant and the
replacement half-life sampled in the Monte Carlo; see [docs/CHANGELOG_v3_3.md](docs/CHANGELOG_v3_3.md),
[docs/CHANGELOG_v3_2.md](docs/CHANGELOG_v3_2.md),
[docs/CHANGELOG_v3.md](docs/CHANGELOG_v3.md) and
[CHANGELOG.md](CHANGELOG.md); cite with [CITATION.cff](CITATION.cff)).

## Results

Paths are those of the full profile (`outputs/`); the light profile writes the same tree under
`outputs/_light/`.

| what | where |
|---|---|
| Every figure (paper, Extended Data, diagnostics) with its title, data sources and audit | [outputs/FIGURES.md](outputs/FIGURES.md) |
| **Paper**: Fig1–Fig8 | [outputs/paper_main/](outputs/paper_main/) |
| **Extended Data**: ED1–ED14 and the table EDT1 (lever levels by typology) | [outputs/paper_extended/](outputs/paper_extended/) |
| **Diagnostics**: calibration, validation, boundaries, pathways, Monte Carlo, sensitivity | [outputs/diagnostics/](outputs/diagnostics/) |
| Run profile, draws, seeds, git and input hashes, step timings | [outputs/run_meta.json](outputs/run_meta.json) |
| Grouped one-at-a-time sensitivity tables | [outputs/data/sensitivity/](outputs/data/sensitivity/) |
| Results summary; every assumption with its basis; validation and reconciliation reports | [outputs/reports/](outputs/reports/) |
| Methods draft and the levers table (Table 1) | [docs/METHODS_DRAFT.md](docs/METHODS_DRAFT.md), [docs/LEVERS_TABLE.md](docs/LEVERS_TABLE.md) |
| References, with their verification status | [docs/REFERENCES.md](docs/REFERENCES.md) |
| Every number (CSV, JSON) | [outputs/data/](outputs/data/) |
| Every data file, what it holds and the script that writes it | [outputs/INDEX.md](outputs/INDEX.md) |
| How the model works, script by script | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Vocabulary and the renaming map; figure plan; palette; sensitivity plan | [docs/RENAMING.md](docs/RENAMING.md) (section 11 for v3), [docs/FIGURE_PLAN_v3.md](docs/FIGURE_PLAN_v3.md), [docs/PALETTE.md](docs/PALETTE.md), [docs/SENSITIVITY_PLAN.md](docs/SENSITIVITY_PLAN.md) |

Every number in the documents and figures is read from `outputs/data/`, which the pipeline
writes; nothing is typed by hand. Results for reporting come from the full profile only.

## Running

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt               # pinned; Python 3.11
python run_all.py                             # light profile (default): outputs/_light/
python run_all.py --profile full              # full profile: outputs/ (the basis for reported results)
python run_all.py --figures-only              # redraw every figure from the data; the data must stay byte-identical
python run_all.py --reference-legacy          # the MODEL v2.1 Reference (overbuild never absorbed): outputs/_legacy/
python tests/capture_regression_model_v3.py   # (re)capture the v3 regression lock after both profiles have run
```

| profile | Monte Carlo | Sobol | bootstrap | figures | outputs |
|---|---|---|---|---|---|
| light (default) | 1,000 draws, seed 20261014 | off | 500 | PNG 200 dpi, footer "LIGHT RUN — n=1000" | `outputs/_light/` |
| full | 5,000 draws, seed 20260924 | on | 2,000 | PDF + PNG 600 dpi | `outputs/` |

The deterministic results (the Reference, every lever, pathway and TL run) do not depend on the
profile; `tests/test_profiles.py` checks this. Step timings are recorded in `run_meta.json`.

The pipeline computes first and draws last, each script in its own process with its console
output in `<outputs>/logs/<step>.log`:
`Building_factors.py` → `projection.py` → `Diagnostics.py` → `Sensitivity.py` →
`MonteCarlo.py` → `boundaries.py` (reads the Monte Carlo draws) → `validation.py` →
`gap_2026.py` → `tools/overbuild_2026.py` → `tools/replacement_scenarios.py` →
`tools/reconciliation.py` → `tools/figures_report.py` → `pathways.py` → `pathways_mc.py` →
`tools/sensitivity_tables.py` → `tools/metrics.py` → `tools/results.py` →
`tools/assumptions.py` → `tools/methods.py` → `run_meta.json` → `python -m figures` (every
figure and FIGURES.md, from the data files only) → `tools/check_outputs.py` → `indexes.py` →
the tests. The model scripts write CSV and JSON only; the `figures/` package draws. A run first
clears its data, reports and figure folders (and the retired MODEL v2.1.2 folders
`paper/`, `extended_data/`, `key_figures/`), so nothing stale survives. A failed step prints its
name and the log to read, and the run stops (exit code 1 from the command line).

### Running in Spyder

1. Open `run_all.py` and press Run (F5), or type `runfile('run_all.py', args='--profile full')`
   in the IPython console. Every path is resolved from the repository folder.
2. Each step runs in its own process; the console prints one line per step. If a step fails,
   the console names the step and the log file to open; no `SystemExit` traceback is raised.
3. To look at one figure interactively, import its module of `figures/` and call
   `FIGURES['<file id>']()` (`figure_plan.py` lists the module of every figure).
4. To run the tests on their own: `!python -m pytest -q tests` (light profile outputs; set
   `PATHWAY_PROFILE=full` for the full ones).

## Tests and reproducibility

* **Legacy lock** (`tests/test_reference_legacy.py`): with `--reference-legacy` the MODEL v2.1
  Reference is reproduced to 1e-12 relative (`tests/reference_legacy_v2_1.json.gz`).
* **v3 regression lock** (`tests/test_regression_model_v3.py`): the SHA-256 of every
  deterministic data file (identical in both profiles) and of the Monte Carlo files of each
  profile, captured by `tests/capture_regression_model_v3.py`.
* **Model rules** (`tests/test_model_v3.py`): overbuild absorption (logistic, payback cap and
  carry, excess identical in every run), Moderate the exact midpoint, TLn at least as strong as
  Ambitious, ordering Reference ≥ Moderate ≥ Ambitious ≥ TL, TL ≤ Ambitious Pathway ≤
  Moderate Pathway in every Monte Carlo draw, the L4 / L5 interaction, dwellings built ≥ 0, implied vacancy ≥ 4% outside TL, cumulative
  re-occupied ≤ cumulative released, Shapley efficiency, waterfall sums, material and stage
  carbon never negative, the data STOP conditions.
* **Figures** (`tests/test_figures_v3.py`): the model scripts do not plot; the palette registry
  has no duplicates; only the surge band is hatched; AR solid and AtP dotted with zones; the sign
  rules of time series and cumulative bars; every planned figure drawn and audited; drawing
  leaves the data byte-identical.
* **MODEL v3.3.0** (`tests/test_model_v3_3.py`): every run total equals v3.2 under the v3.2 →
  v3.3 map of run ids (`tests/fixtures/v3_2_totals.json`), Shapley efficiency of the strategy,
  lever and TL games, the two sequential waterfalls, band sums, the Fig6 markers and exact AR /
  AtP curves, the Very High trend fit, the half-life range in the Monte Carlo.
* **Profiles** (`tests/test_profiles.py`): deterministic outputs identical across profiles;
  `run_meta.json` and the light footer.
* Model tests: accounting identities, census under-construction correction, soil,
  validation, decarbonisation, time-resolved events and committed emissions, the AESA equations
  against their sources, the Harrell-Davis estimator, exact Shapley values.
* The MODEL v1–v2.1 locks are retired to `tests/retired/` (not collected): MODEL v3.0.0 changes
  the Reference on purpose; the legacy lock keeps the link to v2.1.

## Layout

| path | what |
|---|---|
| `projection.py`, `engine.py` | the Reference projection (data, calibration, projection, overbuild absorption) and the forward model (pure functions shared by the projection, Monte Carlo and pathways) |
| `Building_factors.py`, `events.py` | case-study carbon factors; time-resolved maintenance (B2, B4) and committed emissions |
| `Diagnostics.py`, `Sensitivity.py`, `MonteCarlo.py`, `validation.py`, `gap_2026.py` | diagnostics data, one-at-a-time sensitivities, Monte Carlo and Sobol indices, rolling-origin hindcast, 2026 gap |
| `aesa.py`, `boundaries.py` | planetary-boundary layer (AESA): boundaries, levels of exceedance |
| `levers.py`, `pathways.py`, `pathways_mc.py`, `mcstats.py` | the lever rule and the nine levers; pathways, TL and re-occupation, Shapley, waterfall, λ-sweep, back-cast; the pathway Monte Carlo and its insight statistics |
| `figures/` | every figure, from the data files only: `style.py` (palette registry, sizes, saving), `draw.py` (sign rules), `audit.py`, `index.py` (FIGURES.md) and one module per figure group |
| `figure_plan.py`, `layout.py`, `runprofile.py`, `figsource.py`, `naming.py` | figure registry; output layout; run profiles; figure source data; vocabulary |
| `run_all.py`, `indexes.py` | the pipeline; outputs/INDEX.md |
| `tools/` | reports (overbuild, variants, reconciliation, reality checks, metrics, results, assumptions, methods), sensitivity tables, output checks, design documents, palette check |
| `tests/` | the tests above |
| `data/` | inputs only, and the scripts that build `data/derived/` from `data/raw/` |
| `docs/` | CHANGELOG_v3, methods draft, levers table, references, renaming map, figure plan, palette, sensitivity plan, the hooks of the levers into the model |

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
