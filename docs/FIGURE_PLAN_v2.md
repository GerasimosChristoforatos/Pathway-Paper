# Figure plan, MODEL v2.0.0 (design for approval)

Paper-ready structure: six paper figures and two tables (`outputs/paper/`), ten Extended Data
figures (`outputs/extended_data/`), every other figure as a diagnostic (`outputs/diagnostics/`).
No adopted number changes; new values (TL Shapley relative to P5 Moderate with TL7, the pathway
Monte Carlo, grouped sensitivity tables, the exact-engine population rows) are additions, locked by
`tests/regression_model_v2_additions.json`. Removing a figure never removes its data.

## 1. Storyline and naming

| item | in the paper | sensitivity only (Extended Data, diagnostics, data) |
|---|---|---|
| projection | **Reference** (no interventions) | Low replacement, High replacement, half-life 5/15 yr |
| pathways | **P1 Right-sized dwellings, P2 Occupied stock, P3 Retained stock, P4 Low-carbon materials, P5 Combined**, at the Moderate setting, named without a setting suffix | the Ambitious setting of every pathway and lever |
| adoption | **full roll-out by 2035** (basis: RECC, Pauliuk et al. 2024, J. Ind. Ecol. 28, 1699: full implementation by 2035) | full roll-out by 2030 and by 2045 |
| theoretical limit | **TL** (TL1–TL7 at full strength from 2027; a thought experiment, not a pathway) | TL, gradual adoption |

**TL relative to P5 Moderate.** TL is unchanged (asserted to 1e-12): with TL1–TL6 active, every
Ambitious lever setting of today's base (P5 Ambitious) is overridden (TL1 replaces L2/L3, TL2 and TL3
replace L1, TL4 replaces L5) except L4. The only Ambitious element left is therefore named as a
seventh TL assumption: **TL7 Building retention at −40% (the Ambitious level of L4, d = 0.40)**.
TL = P5 Moderate + TL1–TL7 is then the same computation. The TL Shapley attribution becomes TL1–TL7
relative to P5 Moderate at full strength from 2027 (128 subsets, exact rational arithmetic,
efficiency exact), with the instant-start effect (P5 Moderate: adoption path → full strength from
2027) as a separate line.

**Naming in the paper.** "P1 Right-sized dwellings" … "P5 Combined" mean the Moderate setting by
2035. Labels with a setting or a window (e.g. "P5 Combined, Ambitious", "full roll-out by 2030")
appear only in Extended Data and diagnostics. Data files keep their run ids (`P5-moderate`, …).

**Maintenance as a layer.** Maintenance (B2, B4) is drawn as its own layer only in Fig3 and in
demand-band breakdowns (Fig2 and Fig4 carbon panels, D25/D26). Everywhere else it is included in
the totals but not drawn separately. It is removed as a separate layer or line from D27 (the
maintenance layers of the annual and cumulative panels) and D23 (the "Reference without maintenance"
line); no other figure draws it. Every figure's audit record lists whether
maintenance is drawn; a test allows that only in Fig3, Fig2, Fig4, D25 and D26.

## 2. Paper figures (`outputs/paper/`)

Each figure is a PNG (300 dpi), a vector PDF and a source-data CSV (panel, series, x, value, unit),
at Nature widths (89 mm single, 183 mm double column). `PAPER.md` holds the headline findings (one
sentence each, with numbers and data files) and every figure with its caption. Colours, sizes and
fonts come from `style.py`, labels from `naming.py`; the palette is colour-vision checked
(`docs/PALETTE.md`).

### Fig1. Model schematic (183 mm; was H1)

Mock: a left-to-right chain of boxes: population → households → dwellings required → floor area →
embodied carbon → AESA boundaries (AR, AtP). The demand bands branch off "dwellings required" (bottom to
top: population growth, smaller households, extra space, vacancy, 2026 overbuild, historical
replacement, recent replacement surge). Each lever is a tag attached to the band or quantity it acts
on (L1 extra space; L2 vacancy; L3 2026 overbuild; L4 historical replacement and the recent surge;
L5 carbon per m²). The pathways P1–P5 group the levers and TL1–TL7 sit at the end of the same
arrows; the untargeted bands are marked. Source data: the structure only (naming.py, levers.py).

### Fig2. Why floor area is built (183 mm; was H3, with the D05c history)

Mock: (a) floor area by demand band, Mm² per year: the history as one column per census interval
(1991–96 … 2018–23, 2024–25 faint), the Reference projection annual 2026–2050; bands stacked and
summing to the total; no separate total line. History bands as in v1.1: the census-measured net
replacement (D07 rate × previous year's stock) and the hatched neutral **unexplained building** band
(building not explained by household formation, vacancy and census-measured replacement), which may
be negative. (b) The same Reference bands as embodied carbon per year, with maintenance (B2, B4) as
its own layer (a demand-band breakdown). Source data: `data/baseline/bands_history.csv`,
`stock_identity_history.csv`, `bands_annual.csv`.

### Fig3. Embodied carbon of the Reference (183 mm; was H4 and H6)

Mock: (a) annual carbon 2026–2050 by life-cycle stage: materials A1–A3, construction A4–A5,
maintenance B2/B4, soil carbon loss, stacked. (b) The same carbon by material (concrete, steel,
timber, plastics & paint, plasterboard, others, soil carbon loss on top). (c) Companion panel:
cumulative carbon 2026–2050 next to the emissions committed after 2050 (lower and upper bound,
hatched), with a second axis in years of the 2050 AR boundary (45–49 years). Source data:
`data/baseline/annual.csv`, `projection.json`, `data/aesa/results.json`.

### Fig4. Pathways by demand band (183 mm; was H7)

Mock: two panels, floor area 2026–2050 (Mm²) and carbon 2026–2050 (kt CO₂e), one stacked bar each
for the Reference, P1, P2, P3, P4, P5 and TL (Moderate, by 2035). Untargeted bands (population growth,
smaller households) grouped into one neutral segment at the bottom; the targeted bands above. The
carbon panel draws maintenance as its own layer (a band breakdown). The percentage change vs the
Reference is labelled on each bar; the cumulative AR and AtP budgets are short reference lines on the
carbon panel. Source data: `data/pathways/bands.csv`, `runs.csv`.

### Fig5. Emissions against the boundaries and the attribution (183 mm, two rows)

(a) Annual emissions 2026–2050 of the Reference, P5 and TL against the annual AR and AtP boundaries
(log axis as now). Each run has a Monte Carlo 5–95% band: the Reference from the existing draws, P5
and TL from the pathway Monte Carlo (§3b of the release spec; new data). TL's zero-building years
(2027–2031, banking rule) are shaded and labelled "no new construction: vacant stock absorbed". The
true values are drawn: zero, not clipped; on the log axis the line drops to the axis floor and the
label says so.

(b) Order-free Shapley waterfall, cumulative LoE AR (left axis) with the AtP equivalent (right axis):
Reference → P1, P2, P3, P4 (Shapley values over the four Moderate pathways, summing exactly to
Reference − P5) → P5 → instant start (separate line) → TL1 … TL7 (Shapley values relative to P5
Moderate, full strength from 2027) → TL. The cumulative AR and AtP budgets are horizontal lines.
Monte Carlo 5–95% whiskers on the Reference, P5 and TL bars. The emissions committed after 2050 are
hatched companion bars next to the Reference, P5 and TL (lower–upper bound). The TL residual above
the AR budget is annotated in dwellings not built (2027–2050) and people housed in existing
dwellings. Source data: `shapley_pathways.csv`, `shapley_theoretical_limit.csv` (new TL1–TL7
version), `pathways_montecarlo_*.csv` (new), `theoretical_limit.json`.

### Fig6. Solution space (89 mm; was H10)

Mock: cumulative LoE AR over uniform cuts of 2027–2050 floor area (x) and of non-soil carbon per m²
(y), 0–100%, with the LoE = 1 contour (and the LoE AtP = 1 contour where reachable). Markers for
P1–P5 (Moderate) and TL at their effective coordinates (TL's soil effects are not on the plane, as
the caption says). Source data: `solution_space.csv`, `backcast.json`, `theoretical_limit.json`.

### Tables (`outputs/paper/`, Markdown and CSV)

* **Table 1. Levers and the theoretical-limit assumptions**: today's LEVERS_TABLE, Moderate column
  first, plus TL7.
* **Table 2. Results**: Reference, P1–P5, TL. Columns: floor area 2026–2050, carbon 2026–2050,
  committed after 2050, cumulative LoE AR and AtP, change vs the Reference. Monte Carlo 5–95% for the
  Reference, P5 and TL; P(LoE AR ≤ 1) for TL.

## 3. Extended Data (`outputs/extended_data/`, ED1–ED10)

Same format as the paper figures (183 mm unless noted); `EXTENDED_DATA.md` holds the captions. Rows
and groups are in docs/SENSITIVITY_PLAN.md.

| ED | content | replaces |
|---|---|---|
| ED1 | One-at-a-time tornado of Reference carbon 2026–2050, grouped (Demographics; Housing stock & calibration; Replacement scenario; Carbon factors & technology; Accounting); population rows from the exact engine paths | D16, H11 (carbon part) |
| ED2 | Tornado of P5 carbon 2026–2050 (pathway design): each of P1–P4 at Ambitious with the others Moderate, P5 Ambitious, roll-out 2030 / 2045, Low/High replacement, population 5th/95th (exact engine path); TL gradual adoption as a separate marker | new |
| ED3 | Sensitivity paths: annual carbon 2026–2050, one panel per ED1 group, every row of the group, the Reference in black | D17 |
| ED4 | Planetary-boundary tornado, cumulative LoE AR and AtP side by side, grouped (Carrying capacity; Base window; Economic measures; Population source; Replacement scenario) | H11 (LoE part) |
| ED5 | Monte Carlo of the Reference: (a) floor area and (b) carbon per year, 5–95% and 25–75% bands, median, deterministic Reference; (c) cumulative distributions of cumulative carbon and of cumulative LoE AR for the Reference, P5 and TL, with P(LoE AR ≤ 1) for TL | H2, part of D21 |
| ED6 | Ambitious settings: P1–P5 Ambitious vs Moderate, carbon 2026–2050 and LoE AR | part of H7, H8, H9 |
| ED7 | Roll-out timing: P5 (Moderate and Ambitious) by 2030 / 2035 / 2045, annual carbon and cumulative LoE AR; the three adoption paths w(y) as an inset | D29 (adoption part) |
| ED8 | TL: Shapley attribution TL1–TL7 relative to P5 Moderate (instant start separate) and the TL indicators (new-dwelling size, space per person, dwellings built per year with the banking rule, soil factor) | D33, part of D32 |
| ED9 | Single-lever results: each of L1–L5 alone at Moderate and Ambitious, carbon 2026–2050 and LoE AR vs the Reference; the lever Shapley values for P5 Moderate | D31 |
| ED10 | Low and High replacement: the Reference, P5 and TL under the three replacement variants, carbon 2026–2050 and LoE AR | D29 (variant part), D27 (variant totals) |

## 4. Diagnostics (`outputs/diagnostics/`)

Every other figure stays, as now, with `DIAGNOSTICS.md`: D01–D15, D18, D19, D20–D28, D30, D32, D34.
D16, D17, D29, D31 and D33 are superseded by Extended Data (their data stay in `outputs/data/`).
D23 and D27 lose their maintenance line and layers.

## 5. Old → new (RENAMING.md gains a section)

| model-v1.1.0 | MODEL v2.0.0 |
|---|---|
| H1 | Fig1 |
| H2 | ED5 (a) |
| H3 | Fig2 (a) |
| H4 | Fig3 (a, b) |
| H5 | Fig5 (a) (with P5, TL and their Monte Carlo bands) |
| H6 | Fig3 (c) |
| H7 | Fig4 (Moderate; Ambitious in ED6) |
| H8 | Fig5 (a) |
| H9 | Fig5 (b) (Moderate; TL1–TL7 relative to P5 Moderate) |
| H10 | Fig6 |
| H11 | ED1 (carbon) and ED4 (LoE) |
| D16 / D17 | ED1 / ED3 |
| D29 | ED7, ED10 |
| D31 | ED9 |
| D33 | ED8 |
| outputs/headline/ (HEADLINE.md) | outputs/paper/ (PAPER.md) and outputs/extended_data/ (EXTENDED_DATA.md) |

## 6. New values (additions)

* TL Shapley TL1–TL7 relative to P5 Moderate (128 subsets) and the instant-start line;
  `TL7` in the TL definition and indicators. Today's TL1–TL6 attribution relative to P5 Ambitious
  stays in its data file (locked).
* Pathway Monte Carlo: the 5,000 saved Reference draws re-run through the pathway layer for P5
  (Moderate) and TL. Levers applied identically to each draw; TL3–TL6 targets fixed absolute values
  (OLF 19.69 m² per person; best-case A1–A3 per m² per typology; lowest-soil-order factors; 65%).
  Output: cumulative carbon and LoE AR/AtP per draw, percentiles, annual percentiles, P(LoE AR ≤ 1).
  The central draw must reproduce the deterministic P5 and TL runs to 1e-9 (otherwise STOP).
* Grouped sensitivity tables (Reference carbon, P5 carbon, planetary boundary), with the new rows:
  P1–P4 each at Ambitious within P5, and the population 5th/95th rows from the exact engine path.
* The tables of Fig/ED source data and Table 2.
