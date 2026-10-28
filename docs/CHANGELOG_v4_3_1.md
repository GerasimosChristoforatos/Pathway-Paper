# MODEL v4.3.1

Branch `release/model-v4.3.1`, from `release/model-v4.3.0`.

**Scope.** Final figure fixes, ten investigations and a user palette file. The deterministic model, the Monte Carlo
and the Sobol analysis were **not** rerun: every figure is redrawn from the committed outputs (`redraw.py --final`,
600 dpi). There was one cheap deterministic recompute, the SF6 hindcast (`validation.py`). It **adds** rows for the
High and Very High replacement variants to `baseline/validation.json`, `reports/validation.md` and
`figure_source/D14_hindcast.json`; every existing row is unchanged. No reported number changes. The model-changing
fixes found by the investigations are **held for the final clean run** (section "Held for the final run"). That run
comes after the colourist's palette and the Stats NZ 2023-base swap.

Order of work: A (palette) → B (investigations) → C (figure changes) → D (render, report).

---

## A. User palette file and the redraw-only workflow

### A1, A2: `palette.toml`, read only by `figures/style.py`

There are five groups. Their defaults are the colours of v4.3.0:

* `[demand_bands]`: population_growth, household_size_change, extra_space, vacancy, net_replacement, market_balance,
  maintenance;
* `[materials]`: timber, steel, concrete, plastics_paint, plasterboard, others, soil_carbon_loss;
* `[life_cycle_stages]`: a1_a3, a4_a5, soil_carbon_loss, maintenance, committed_b2_b4, committed_c1_c4;
* `[runs]`: reference, moderate, ambitious, theoretical_limit;
* `[strategies]`: avoid, switch, improve.

How the file is read:

* `style.load_palette` reads it with `tomllib`.
* A missing group, a missing or extra key, or a value that is not `#RRGGBB` raises `PaletteError`, naming the key.
* The `PATHWAY_PALETTE` environment variable points `style.py` at another file.
* No other module reads the file. Every figure takes its colours from `style.py`
  (`tests/test_palette_file.py`, 5 tests).

### A3: decoupling (the aliases broken)

In v4.3.0 several colour roles were the same object as a lever shade, so recolouring one recoloured the others. Each
role now has its own palette key or its own literal. The aliases broken were:

| role | was an alias of | now |
|---|---|---|
| bands smaller_households / extra_space / vacancy | lever L1 / L4 / L2 | `[demand_bands]` |
| stages a1_a3 / a4_a5 / soil carbon loss (also `COMPONENT`) | lever L8 / L9 / L7 | `[life_cycle_stages]` |
| strategies avoid / switch / improve | lever L4 / L7 / L8 | `[strategies]` |
| typology detached / townhouse / apartment | lever L4 / L8 / L2 | literals in `style.TYPOLOGY` |
| tornado low / high | L8 (Improve blue) / `PATHWAY['pathway']` (Moderate orange) | literals `TORNADO_LOW`, `TORNADO_HIGH` |
| display band net_replacement / market_balance | `BAND['replacement']` / `BAND['overbuild_2026']` | `[demand_bands]` |
| `COMPONENT` maintenance | `BAND` maintenance | `[life_cycle_stages]` maintenance |
| `PATHWAY['pathway']` | a duplicate literal | `[runs]` moderate |
| `SCENARIO['REF']` | — | follows `[runs]` reference |

Uses of `REFERENCE` that do not represent the Reference run now use the new `NEUTRAL_DARK` (#4D4D4D, the same value):
the ED6 histogram and the bars of the TL-dwellings figure (SF15).

Proof of decoupling: each of the 31 keys was set in turn to a probe colour (#00FFFF), and only the figures that draw
that meaning changed. Two examples:

* `extra_space` changes Fig1, Fig2 and SF4 only.
* `avoid` changes only the strategy figures; the tornado (ED4) is unaffected.

### A4: `released_tl` and `surplus_vacant`

* **`released_tl`.** It is not drawn as a band in any final figure. Its colour is still used in SF15 (the re-occupied
  outline and the pool line), so it is kept, and it stays outside the user file.
* **`surplus_vacant`.** It is drawn nowhere. Its style entry was removed; the data band is unchanged.

### A5: `redraw.py`

```
python redraw.py [--palette FILE] [--only ID ...] [--dpi N] [--out DIR] [--final]
```

* **Defaults.** 200 dpi into `outputs/_palette_preview/<palette stem>/` (git-ignored).
* **`--final`.** Writes the release folders at the profile dpi (600). It also writes `FIGURES.md` and the
  Supplementary and Extended Data tables.
* **Swatch sheet.** Every run writes one (`palette_swatches.png`).
* **Validation.** The file is validated before anything is drawn.
* **Closeness warnings.** A warning names two keys that are drawn in the same figure and closer than CAM02-UCS ΔE 10
  (the `tools/palette_check.py` method). Keys that stand for the same quantity, such as maintenance as a band and as a
  stage, are exempt.
* **CVD report.** For each group, the closest pair under normal vision and under simulated deuteranomaly, protanomaly
  and tritanomaly (Machado et al. 2009, severity 100, `colorspacious`).

### A6: proof

* **(i) Default palette.** With the default palette, all 34 v4.3.0 PNGs redraw **pixel-identical** at 600 dpi. This
  was checked before part C, which changes figures by design.
* **(ii) Fresh clone.**
  * Setup: a fresh clone from GitHub with a new virtual environment (Python 3.13, `requirements.txt`).
  * Result: `redraw.py` worked and all 34 PNGs were pixel-identical.
  * Timings: clone 16 s; virtual environment 70 s; preview (200 dpi) 17.4 s; `--final` (600 dpi) 26.4 s.

### A7

The README section "Recolour the figures locally" describes the workflow.

---

## B. Investigations (no model result changed)

| | question | finding | verdict |
|---|---|---|---|
| B1 | Household size dips in 2021–22, then rises in 2023 | S used: 2019 2.7453, 2020 2.7340, 2021 2.6943, 2022 2.6624, 2023 2.6859. The published Stats NZ DHE has the same shape (2.7338 → 2.6251 → 2.6387); the ×0.8244 rescale dampens it rather than causing it. ERP growth was 54.3k, 4.0k and 35.3k in 2020–22, then 142.4k in 2023, while DHE households are consent-driven (24–36k per year). The deviation from census interpolation is about +0.02 to −0.033. | Artefact of the DHE estimation method; no change now. **Held:** replace with the Stats NZ 2023-base households. |
| B2 | SF1b points for 2024/25 | In v4.2.2 these were DHE consent-derived ΔS (−0.0144, −0.0143), written by v4.0.0. Since the v4.2 ERP / S bridge (data regenerated in v4.3.0) they are the model's own household-size path (−0.00312, −0.00259), not observations. | Relabelled: "the model's household-size path (households = ERP / S), not observed". |
| B3 | SF7c: why does net replacement differ between lags? | Replacement is recalibrated with each run's completion timing. 2018–23 interval built: 187,263 at zero lag (with the census under-construction correction) against 174,876 at 17 months. Recent rate 0.301 against 0.173 %/yr; long-run unconsented −0.042 against −0.076 %/yr. Cumulative net replacement 2026–2050: 14.66 against 8.95 Mm². | Not like-for-like in replacement; caption added. **Held:** a zero-lag run with replacement held at the adopted calibration. |
| B4 | Is household size uncertain in the Monte Carlo? | Yes. S interpolates the Stats NZ Low / Medium / High household-size variants with the same z as population (comonotone). In the one-at-a-time rows (Fig7a, ED4) and the SF1a band, S is held at Medium. | Monte Carlo input renamed "Population and household size". |
| B5 | Tornado: is the budget recomputed per row? | No for the non-population rows: they use the fixed Reference AR budget (`tools/sensitivity_tables.py` ~401–413). The Monte Carlo recomputes I_base per draw (`boundaries.py` ~385). An approximate recomputation with the jackknife factors (upfront ratio 0.969 / 1.032) gives a LoE of 4.45–4.46 for those rows instead of 4.31–4.61. | Inconsistent. **Held:** recompute I_base for factor rows (exact, time-resolved base) in the final run. |
| B6 | PRCC: high PRCC with a low Sobol share | The PRCC is correct (ranks of all inputs, OLS residuals with intercept; percentile bootstrap, B = 2,000). Interval widths are 0.0026–0.057, smaller than the dots. SRC² ≈ Sobol S1: half-life 0.0026 against 0.0026; carbon 0.042 against 0.037; size 0.106 against 0.109. A high PRCC with a small variance share is expected: the partial correlation is computed after population and household size have removed about 99% of the variance. | No bug. |
| B7 | Households per consent | Ratio 0.885–0.889 (December basis; all dwellings including retirement villages). | Test added (`tests/test_households_per_consent.py`: 0.884–0.890 for 2019–2025, mean 0.888 ± 0.002; the 2014–2018 range is wider than 0.05). The SF1 panel (c) is dropped. |
| B8 | SF6 hindcast variants without look-ahead | All four variants can be defined from data before each origin. Low: dwelling count. Reference: as adopted. High: the last intercensal rate held. Very High: the OLS trend of the census intervals before the origin (n = 3, 4, 5). End errors are in the table below. | SF6 shows the four variants; the as-published line is removed. |
| B9 | Zero-building years in the pathway Monte Carlo | Re-evaluating the saved draws reproduces the stored outputs exactly (2.2e-16). Draws with at least one zero-building year: Ambitious 299 / 5,000 (2031: 244; 2032: 299; 2033: 157 …), Moderate 26, TL 244 (every year from 2028), TL from 2027: 332. All are low-population draws: Ambitious zero draws have z ≤ −1.44 (mean −1.98), and their other inputs are typical. | Explained by low population; no change. |
| B10 | SF2a vacancy definitions | The Reference history is census empty / total private dwellings. Before 2013 it is unoccupied × the 2013 measured empty share, and it is linear between censuses. The projection is held at the 2023 value (5.39%). | Legend labels rewritten to say which line the Reference uses. |

B8 hindcast, error at the end (% of actual cumulative dwellings):

| origin | Low | Reference | High | Very High |
|---|---:|---:|---:|---:|
| 2006 | −3.9 | −4.2 | −4.5 | −15.1 |
| 2013 | +5.4 | +10.6 | +13.0 | +14.0 |
| 2018 | −10.5 | −11.4 | −11.5 | −7.3 |

The household-size variant is now named by direction. The Stats NZ Low variant gives smaller households (S in 2050:
Low 2.6105, Medium 2.6701, High 2.7222). Its LoE of 4.82 sits at the low end of the input, in blue. The colours
already followed direction; only the label changed: "Household size (smaller–larger households)".

## Held for the final run (model-changing; not applied here)

1. **B1.** Households after 2018 from the Stats NZ 2023-base series instead of the rescaled DHE.
2. **B3.** A controlled zero-lag run (SF7) with replacement held at the adopted calibration, so that the lag comparison
   is like-for-like.
3. **B5.** Recompute the AR budget base I_base for each factor row of the one-at-a-time tornado (Fig7a, ED4). Use the
   exact time-resolved base, as the Monte Carlo already does.

---

## C. Figure changes

### Intervals and settings

* **90% intervals everywhere (5th–95th percentile).** Fig3b moves from 2.5–97.5 to 5–95 (`FIG3_INTERVAL`).
  * The interval equals the stored `montecarlo/summary_REF.csv` p5 / p95 to 1e-12 (test).
  * Legend: "90% interval (5th–95th percentile)", "50% interval (25th–75th percentile)".
* **Settings convention.** Moderate is filled and Ambitious is hollow.
  * Fig6 (Moderate above, Ambitious below each lever).
  * Fig5: the Ambitious points and ruler marker are in the Ambitious run colour; the legend has four columns.

### Labels

* **Fig2a.** "Household-size change", in full.
* **Fig7b.** "Theoretical Limit" (from `naming.TL`).
* **ED4 / Fig7a.** "Household size (smaller–larger households)".
* **ED6, ED7, SF9.** "Population and household size".

### Extended Data

* **ED8 Shapley attribution.** No longer rendered; the Shapley values are in Fig6.
* **Renumbering.** ED9 → ED8 (lever annual) and ED10 → ED9 (roll-out timing), recorded in
  `outputs/data/ed_number_map.csv`.
* **ED2a.** The legend sits below the panel and includes the negative-outline entry ("From household-size change,
  negative … outline").
* **ED3a.** The Ambitious Pathway is drawn in all four replacement variants, with a legend entry.

### Supplementary

* **SF9 (budget construction) → Supplementary Table ST1.**
  * Files: `supplementary/boundaries/ST1_budget_construction.md` and `.csv`.
  * Content: components with units, budgets in 2025 and 2050, the population modifier; three significant figures and
    no e-notation.
* **No longer rendered.** SF11 (pathway sensitivity).
* **Panels dropped.**
  * SF1c (households per consent, B7).
  * SF2b (stock). SF2 is relabelled a (vacancy) / b (components) / c (vacancy definition).
  * SF4b (utilisation).
* **SF5b.** "Never absorbed" has its own line style (dash-dot).
* **SF6.** The four hindcast variants, as in B8. The in-panel error box is at the top left (the empty corner) and uses
  short variant names.
* **SF7.** The note explains the replacement recalibration (B3).
* **SF9 (PRCC, was SF10).** The x-limits are ±1.05, so the markers at about 1 are no longer clipped.
* **Renumbering.** SF10, SF12–SF17 → SF9–SF15, recorded in `outputs/data/sf_number_map.csv` (status per item: same
  number / renumbered / no longer rendered / figure → table).

### Suite-wide text rules

These are checked on every drawn figure by `tools/check_figure_text.py` (`tests/test_figure_text_rules.py`).

* **Year ranges** use the en dash: "2026–2050".
* **Thousands separators** on numbers ≥ 1,000.
  * `style.thousands_ticks` applies them at save time.
  * It replaces only matplotlib's default formatter, on linear axes.
  * Year axes are left alone.
* **The typographic minus** is used for negative numbers, in tick labels (`draw.thousands`) and in number labels drawn
  as text (`draw.minus`): SF2 interval and bar labels, SF6 errors, SF8 handover.
* The final check finds no issues in all 31 figures.

### Captions and registry

* **Fig4.** The caption follows the figure. Panels a–c are the three waterfalls; the annual panel was removed in
  v4.2.1, and the caption still described it.
* **`figure_plan`.**
  * `PB_FIGURES` updated (ED9 roll-out timing; ST1 has no axes).
  * New: `SUPPLEMENTARY_TABLES`, `SF_NUMBER_MAP` and `TABLE_MODULES`.
  * A `RETIRED` entry for v4.3.1.
* **Other files.**
  * `tools/figure_manifest.py` lists the tables (EDT1, ST1).
  * `indexes.py` registers `sf_number_map.csv`, ST1 and `palette_swatches.png`.
  * The README figure table is current.

### Deleted (superseded by renumbered files or no longer rendered)

* **Extended Data.** `paper_extended/ED8_shapley_attribution.png`, `ED9_lever_annual.png`, `ED10_rollout_timing.png`.
* **Supplementary.**
  * `supplementary/boundaries/SF9_budget_construction.png`
  * `supplementary/sensitivity/SF10_prcc.png`, `SF11_pathway_sensitivity.png`, `SF12_lambda_sweep.png`,
    `SF13_hd_estimators.png`
  * `supplementary/montecarlo/SF14_mc_convergence.png`, `SF15_pathway_mc.png`, `SF16_conditional_tl.png`
  * `supplementary/pathways/SF17_tl_dwellings.png`
* **Audit records.** The 12 matching `diagnostics/_audit/*.json`.
* **Plotting code.** `paper_extended.ed_shapley` (with `SHAPLEY_GAMES`, `shapley_attribution`). From
  `figures/sensitivity.py`: the SF11 code (`_lever_row`, `PATHWAY_ROWS`, `_pathway_label`, `sf11`).

---

## D. Final set and checks

* **Main.** Fig1–Fig7.
* **Extended Data.** ED1–ED9 and the table EDT1.
* **Supplementary.** SF1–SF15 and the table ST1.
* `outputs/figure_manifest.csv` has 33 rows: 31 figures and 2 tables.

How the release was checked:

* **Rendering.** All figures were drawn with `redraw.py --final` (600 dpi). Every PNG was checked visually.
* **Overlaps fixed.**
  * ED2a legend.
  * Fig5 legend.
  * SF6 error box.
  * SF9 clipped markers.
  * Hyphen-minus labels in SF2, SF6 and SF8.
* **Outputs check.** `tools/check_outputs.py` passes.
* **Indexes.** `indexes.py` passes, with every output registered.
* **Tests.** `PATHWAY_PROFILE=full pytest tests`: 255 passed, 2 skipped.
