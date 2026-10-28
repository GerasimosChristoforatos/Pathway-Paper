# MODEL v4.3.2

Branch `release/model-v4.3.2`, from `main` at `c7a474d` (v4.3.1 merged).

**Scope.** Figure and palette changes only. **No model run.** `run_all.py`, `MonteCarlo.py`, `Sensitivity.py`,
`pathways_mc.py` and the Sobol analysis were not run. Every figure was drawn from the committed full-profile outputs
with `python redraw.py` (previews) and `python redraw.py --final` (release, 600 dpi). No change needed recomputed
data.

* **Files changed.**
  * Code: `figures/`, `figure_plan.py`, `palette.toml`, `redraw.py`, `tools/palette_check.py`.
  * Tests: `tests/test_palette_file.py`, new `tests/test_figures_v4_3_2.py`.
  * Docs: `docs/PALETTE.md`, `docs/palette_preview.png`, this file, `CHANGELOG.md`, `CITATION.cff`, `README.md`.
  * `naming.py` is unchanged.
* **`outputs/data/` is unchanged.** `git diff --stat -- outputs/data` is empty.
* **Other outputs.** These changed:
  * The seven redrawn PNGs (below).
  * `outputs/FIGURES.md`.
  * `outputs/palette_swatches.png`.
  * The audit records in `outputs/diagnostics/_audit/`:
    * Fig1, Fig3, Fig7, ED4, ED5, ED8 and SF10 have new content.
    * Fig4, Fig6, ED9, SF1, SF6, SF7, SF9 and SF12 change only their `producer` field. It was `pytest` in v4.3.1 and
      is `redraw.py` now. Their PNGs are pixel-identical.
* **No reported number changes.**

Order of work: Step 1 (palette, checked on its own) → Step 2 (figures) → Step 3 (checks, release).

---

## Step 1: palette

### New groups in `palette.toml`

The default of each key is the exact literal it replaces in `figures/style.py` of v4.3.1.

| group | key | default | colours |
|---|---|---|---|
| `[boundaries]` | `acquired_rights` | `#D7191C` | `style.AR`, `style.BOUNDARY['AR']` |
| | `ability_to_pay` | `#67000D` | `style.ATP`, `style.BOUNDARY['AtP']` |
| `[boundary_zones]` | `within_both` | `#41AB5D` | `style.ZONE['within_both']` |
| | `within_ar_only` | `#A1D99B` | `style.ZONE['within_ar']` |
| | `exceeded` | `#FB6A4A` | `style.ZONE['exceeded']` |
| `[cumulative]` | `fig3b_cumulative_carbon` | `#4D4D4D` | `style.CUMULATIVE_FIG3B`: the Fig3b 2026–2050 column and its legend patch (was `REFERENCE`) |
| `[one_at_a_time]` | `low_end` | `#4A6192` | `style.TORNADO_LOW` |
| | `high_end` | `#EB6123` | `style.TORNADO_HIGH` |
| | `single_alternative` | `#6E6E6E` | `style.TORNADO_SINGLE` |

* **Fixed in `style.py`.** The zone opacities stay fixed in `style.ZONE_ALPHA` (0.30 / 0.30 / 0.07). The comment of
  `[boundary_zones]` in `palette.toml` says so.
* **`PALETTE_KEYS`.** It has nine groups. `load_palette` stays strict: every group and key is required, and unknown
  groups or keys are errors.
* **`palette.toml` header.** The new items are removed from the "fixed in figures/style.py" list.

### Hard-coded colours found (grep of `figures/`, `tools/`, `*.py`)

* **The hex values of the new keys.** They appeared only in `figures/style.py`. They were the literals of `AR`,
  `ATP`, `ZONE` and `TORNADO_*`, and the alias `TORNADO_SINGLE = MUTED`. No figure module had a boundary, zone,
  tornado or Fig3b colour of its own.
* **Indirect uses that took the boundary or Reference colour for another meaning.** Two were changed:
  * `figures/paper_main.fig3`: the Fig3b column and its legend patch used `S.REFERENCE`. They now use
    `S.CUMULATIVE_FIG3B`.
  * `figures/pathways.sf15_tl_dwellings`: the "release constraint binds" markers used `S.AR`, which is not a boundary
    meaning. They now use the fixed literal `S.RELEASE_BINDS` (`#D7191C`, the same value). The AR key therefore no
    longer recolours SF15.
* **Every boundary, zone and tornado drawing now takes its colour from `style`.** The places are:
  * `style.boundary_zones`, `boundary_hzones`, `boundary_vzones`, `boundary_field`, `zone_handles` and
    `boundary_handles`.
  * `draw.py` (the boundary lines and `draw.tornado` / `tornado_legend`).
  * `paper_main` (Fig3, Fig5, Fig7, and Fig7a through `draw.TORNADO_*`).
  * `paper_extended` (ED9, and SF14, whose AR line is drawn only in its no-threshold branch).
  * `sensitivity` (ED4, ED5).
* **A test guards this.** `tests/test_palette_file.py::test_no_hard_coded_boundary_or_tornado_colour` fails if a
  figure module writes one of these hex values.

### Lever shades retired

* **`style.LEVER` is removed.** Its only remaining uses were:
  * the λ sweep (`paper_extended.sf3`, drawn as **SF10_lambda_sweep**; the prompt called it "SF3", after the
    function name);
  * the surge-band face (`BAND['redevelopment']`, now the fixed literal `style.SURGE_FACE = '#E1D2DD'`);
  * the registry;
  * `tools/palette_check.py`.
* **SF10.** Each lever is drawn in its strategy colour (`palette.toml [strategies]`). Within a strategy, levers are
  told apart by marker: `o`, `s`, `^`, `D`, `v` (`style.LEVER_MARKER`). The legend has one column per strategy,
  headed by the strategy name, listing the lever ids and names. The TL point of each lever uses the same marker with
  a TL-green edge.

### `redraw.py` and `tools/palette_check.py`

* **`SHARED`.** New entries: `'Fig3 (runs, boundaries, zones, cumulative)'` and `'Fig7a/ED4/ED5 (one at a time)'`.
* **Zones in the comparisons.** Zones are compared as they show on white, at their fixed opacities
  (`palette_check.palette_as_shown`). Zone-against-zone pairs are excluded from the closeness warning: the zones are
  pale by design and are covered by the order check below.
* **Same quantity.** The Fig3b column and `runs.reference` are declared the same quantity (the Reference's
  cumulative carbon), so their shared default is not a clash.
* **Zone lightness order (new warning).**
  * The check is `palette_check.zone_lightness_order`, the property documented in `style.py`.
  * Each zone is composited on white at its fixed opacity.
  * The CAM02-UCS J' must fall in the order within both < within AR only < exceeded, under normal vision and
    simulated deuteranomaly, protanomaly and tritanomaly.
  * Each zone's maximum over the vision types must lie below the next zone's minimum.
  * With the default palette it holds: J' 90 / 95 / 98 in normal vision.
* **Colour-vision report.** It covers every group of two or more keys, so the new groups are included. Single-key
  groups have no pair.
* **`tools/palette_check.py`.** It has groups 'Fig3 (runs, boundaries, zones on white, cumulative column)' and 'One
  at a time (Fig7a, ED4, ED5)'. The lever groups are replaced by the strategies. `docs/PALETTE.md` and
  `docs/palette_preview.png` were regenerated (preview at 200 dpi, as before).
  * The committed `PALETTE.md` predated v4.3.0: it had old group names and the removed "Surplus kept vacant" band. The
    regeneration therefore changes more lines than this release's own edits.

### Regression check (before Step 2)

`python redraw.py --dpi 600 --out <scratch>` with the default palette was compared array by array with the committed
v4.3.1 PNGs.

* **Before any change.** All 31 of 31 figures were pixel-identical in the pinned environment (Python 3.11.17,
  `requirements.txt`).
* **After Step 1.** 30 of 31 were pixel-identical. The only difference was SF10, the planned lever → strategy
  recolour (319,711 pixels differ).

---

## Step 2: figures

### Fig1

* **Annual line.** One continuous line of the floor area built (in scope), annual 1992–2050, in INK:
  * history 1992–2025 from `baseline/annual.csv`, source 'history';
  * projection 2026–2050 (pipeline years included), source 'projection';
  * drawn at year centres with straight segments and no markers.
* **Net lines removed.** The line replaces the net line of the projection and the per-year net lines of the
  pipeline columns (`_stack_bar(..., net_line=False)`).
* **Census-interval means.** They stay as short caps on the history columns, in MUTED and thinner (`LW_THIN`).
* **Check.** Before drawing, the figure asserts that the mean of the annual history over each census interval equals
  `observed_built_Mm2_per_year` (rtol 1e-9); otherwise it stops. All seven intervals agree to ≤ 2.2e-16 relative.
* **Labels.** The legend inside reads 'Floor area built, annual (in scope)' (line) and 'Census-interval mean' (cap).
  The history label reads "History (columns: census-interval means)". The caption (`figure_plan`) and the note are
  updated.

### Fig3

* **Markers removed.** The annual-value markers (`MK`) on the Monte Carlo median and on the three runs are gone. The
  PCHIP curves and the pipeline break are kept.
* **Note.** Changed from "between annual values (dots)" to "through the annual values".
* **Column colour.** The 2026–2050 column is in `[cumulative] fig3b_cumulative_carbon`. The 50% box is unchanged.
* **Other figures.** No other figure draws annual markers on PCHIP lines. Every `draw.line` call is without a
  marker. SF4b marks only each typology's minimum year, a single point, not annual values.

### Fig7b

* **Moderate Pathway added.** It uses `pathway_moderate_LoE_AR` from `pathways/montecarlo_draws.csv`, on the same
  paired draws. Colour `S.PATHWAY_SETTING['moderate']`, diamond marker, drawn below the Ambitious Pathway and TL
  (zorder 1.5 < 2 < 3).
* **Legend.** 'Moderate Pathway: P(LoE of AR ≤ 1) = 0.0% (0 of 5,000)'.
* **Wilson values** (from the committed draws; consistent with the v4.3.0 headline table):

  | run | P(LoE of AR ≤ 1) | Wilson 95% |
  |---|---|---|
  | Reference | 0.0000 | 0.0000–0.0008 |
  | Moderate Pathway | 0.0000 | 0.0000–0.0008 |
  | Ambitious Pathway | 0.0002 | 0.0000–0.0011 |
  | Theoretical Limit | 0.4988 | 0.4849–0.5127 |

* **Title.** "Reference, the Pathways and the Theoretical Limit vs the 2050 population". The existing y headroom was
  enough for the legend. The caption is updated.

### ED4

* **Rows not shown** (`sensitivity.REF_NOT_SHOWN`; display only, the data file keeps them; change of cumulative
  carbon from `change_pct`):

  | row | change |
  |---|---|
  | Household size after 2043: flat | +0.0047% |
  | 2026 overbuild gap vs the 2026 requirement | +0.0034% |
  | No census under-construction correction | 0.0000% |
  | Event timing L / n | −0.7560% |

  * **Flat.** It is practically the Reference: the Reference is also held constant after 2043 and differs only by the
    zero slope imposed at 2043.
  * **Accounting group.** It is now empty and is not drawn (`draw.tornado_rows` only emits a header for a group with
    rows; tested).
  * **Note.** The "not shown" sentence lists the version-history rows and these four, each with its change.
* **Row notes.** Described under "Row notes" below.

### ED5

* **Rows not shown** (`sensitivity.PB_DROPPED`; display only):
  * 'α = 1 (Hjalsted et al. SI tables)';
  * 'NZ population: raw Stats NZ 2024-base median'.
* **Unmapped rows still stop the figure.** This is tested with an injected row.

### Row notes (ED4 and ED5)

* **Placement and size.**
  * A compact block under each figure, titled "What each row changes compared with the Reference".
  * FONT_MIN (5 pt), two columns, balanced by line count with rows kept whole.
  * One line per shown row, in display order: "<row label>: <alternative> instead of <Reference setting>".
  * ED4 is now 240 mm high (was 175) and ED5 152 mm (was 110), both within `style.MAX_HEIGHT` (247 mm). The figure
    stops if the block does not fit.
* **Sources.** Every value is read from code or outputs, never typed:
  * `projection.py`, `Building_factors.py`, `boundaries.py`;
  * `Sensitivity.CASES` / `DECARB_CASES`, the settings each row runs;
  * `baseline/projection.json` and `overbuild_2026.json`;
  * `aesa/results.json`;
  * the `case` and `basis` columns.
* **Cross-checks (STOP on a mismatch).**
  * Where the outputs record a setting, it must equal the code. Checked: completion rate, half-life, scenario,
    booking, lag, absorption end, A4–A5 path, event timing, SOURCE_PAIR, AR_BASE_WINDOW, GDP measures, FCE-share
    convention, s_sec window and population source.
  * Every row label must name the value its case runs.
  * The AR base-window rows must equal `boundaries.AR_BASE_WINDOW_SENS / _20 / _FULL`.
  * A test sets `projection.COMPLETION_RATE` to 0.9 and checks that the figure stops.
* **Captions.** The same lines are copied into `figure_plan.ED4_ROW_NOTES` / `ED5_ROW_NOTES` and into the ED4 / ED5
  captions. `figures/index.py` now prints Extended Data and Supplementary captions when present, so the notes reach
  `FIGURES.md`. A test checks that the copy equals the generated text.

**Label/code disagreements found while writing the notes** (none between a row label and the setting it runs):

1. **Redevelopment booking.** The expected wording for "2026 overbuild booked as stock-neutral redevelopment" was "the
   2026–27 building above need replaces existing dwellings". In the code (`engine.market_excess`, mode
   'redevelopment') the whole market excess is booked as redevelopment. That is the observed 2026–2027 excess *and*
   its continuation gap × ρ^(t − 2027) from 2028 (ρ = 0.43). The note says so: "the 2026 overbuild (building above
   need in 2026–2027 and its continuation, fading at ρ = 0.43) …".
2. **Reference population source in ED5.** The expected wording was "the adjusted Stats NZ median". In the code the
   Reference uses `boundaries.POP_NZ_SOURCE = 'model'`: the model's own path, the Stats NZ 2024-base median from the
   observed 2025 level with the observed 2026 growth (`NOWCAST_POPULATION`). The note uses that wording.
3. **Sector-share row.** The row varies the FCE share of GDP inside s_sec: the ratio of the summed quarters
   2016–2025 against the mean of the 40 quarterly ratios (`boundaries.sector_share_components`). It is not the sector
   share itself; the note says so.
4. **Draft caption corrected before release.** It had said that the four hidden ED4 rows were each within 0.01% of
   the Reference. Event timing L / n is −0.76%. The caption now makes no such claim, and the note quotes each row's
   change from the data.

### ED8

* **Squares removed.** The strategy-colour squares (`Rectangle` patches) beside the panel titles are gone. The titles
  ("L1 Household size", …) now start at the panel's left edge.
* **Colours.** The line colours are the `[runs]` keys. No lever-specific colour remains (tested).

---

## Step 3: checks

### Palette probe

Each new key was set in turn to a probe colour (200 dpi, compared with the default-palette redraw), then all at once:

| key | figures that change |
|---|---|
| `boundaries.acquired_rights` | Fig3, Fig4, Fig5, Fig7, ED3, ED9 |
| `boundaries.ability_to_pay` | Fig3, Fig4, Fig5, ED3, ED9 |
| `boundary_zones.within_both` | Fig3, Fig4, Fig5, ED3, ED9 |
| `boundary_zones.within_ar_only` | Fig3, Fig4, Fig5, ED3, ED9 |
| `boundary_zones.exceeded` | Fig3, Fig4, Fig5, ED3, ED9 |
| `cumulative.fig3b_cumulative_carbon` | Fig3 |
| `one_at_a_time.low_end` / `high_end` / `single_alternative` | Fig7, ED4, ED5 |
| every new key at once | Fig3, Fig4, Fig5, Fig7, ED3, ED4, ED5, ED9 |

* **AtP and Fig7.** AtP does not change Fig7: Fig7b draws only the AR line at LoE = 1.
* **SF14.** No key changes it, because its AR line belongs to the no-threshold branch, which the committed data do
  not take.
* **Zone warning.** The probe `within_ar_only = #0050FF` (darker than within both on white) raised the new
  zone-lightness warning, as intended.

### Tests and tools

* **Fast tests.** `PATHWAY_PROFILE=full pytest tests/test_palette_file.py tests/test_figures_v3.py
  tests/test_figures_v3_3_1.py tests/test_figures_v3_3_2.py tests/test_figure_text_rules.py
  tests/test_figures_v4_3_2.py`: **56 passed**. The full suite was not run: this release is figures only, and the
  model and data tests are unaffected (`outputs/data/` is unchanged).
  * `tests/test_palette_file.py` (16 tests). It covers:
    * the nine groups and their defaults;
    * the new constants;
    * no hard-coded moved colour in `figures/`;
    * `LEVER` retired;
    * each new key changing only its own constants. Several share a default with other meanings: the Fig3b column,
      `REFERENCE` and `NEUTRAL_DARK` are all `#4D4D4D`; the single alternative, `MUTED`, `HATCH_COLOUR` and High
      replacement are all `#6E6E6E`.
  * `tests/test_figures_v4_3_2.py` (10 tests). It covers:
    * the Fig1 identity and its single line;
    * Fig3 without markers;
    * the Fig7b Moderate Pathway;
    * the ED4 / ED5 drop lists and notes;
    * the STOP on a code/output mismatch;
    * ED8 without squares;
    * the SF10 colours and markers;
    * the zone-order check.
* **`tools/check_figure_text.py`.** 31 figures, 0 with findings.
* **`tools/check_outputs.py`.** Passes.

### Release render

* **Render.** `python redraw.py --final` (600 dpi) wrote the release PNGs and `FIGURES.md`. Against the committed
  v4.3.1 PNGs exactly seven differ, all by design: Fig1, Fig3, Fig7, ED4, ED5, ED8 and SF10.
* **Visual check of each changed figure.** No clipping, the notes at 5 pt or larger, legends clear of the data:
  * **Fig1.** The line passes over the history columns, and the caps are visible where a column has negative bands.
  * **ED4 / ED5.** The notes sit below the x labels in two columns.
  * **SF10.** Two TL points coincide closely (L6 Switch and L9 Improve, both circles near 17,650 kt). They differ in
    colour.

### Colour-vision finding (not changed; for the colourist)

* **Fig3 under protanomaly.** The new Fig3 group puts the Ambitious Pathway (`#A8400C`) and AR (`#D7191C`) only 3.7
  apart in CAM02-UCS under simulated protanomaly. The threshold is 10.
* **Status.** Both colours predate this release. One is a line and one is a boundary, and both are labelled in the
  legend. A palette decision is left to the final palette.
