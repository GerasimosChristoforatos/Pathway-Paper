# MODEL v4.2.2 — figure corrections

Branch `release/model-v4.2.2`, from `release/model-v4.2.1`, which is kept as it was. Figures only, with the data
byte-identical.

* **Fig2** — the panel a legend sits tighter to the stack (ylim headroom ×1.16).
* **Fig6** — both axes are clipped at 90% (`FIG6_LIM = (-0.05, 0.90)`); the layout is tightened, with the legend below.
  The test in `test_figures_v3_3_2` is updated to the new square.
* **Fig8a** — restores Completion rate and every row above it. The previous version kept the wrong half.
* **Fig5** — unchanged; see the note below.

## Note on Fig5

Each column is the reduction vs the Reference, band by band: Reference band − run band, cumulative 2026–2050.

* **Re-used dwellings (TL).** This band is 0 in the Reference and negative in the TL run. Its reduction is
  0 − (negative) > 0, so it correctly stands above zero: re-use cuts carbon.
* **Market balance.** It sits below zero because the TL run books less overbuild-absorption credit than the
  Reference. Its re-used dwellings are valued at the smaller TL new-dwelling size, and the pooled overbuild is
  re-occupied rather than paid back.
* v4.2.2 styling: the history's RV exclusion is now spread pro rata across the display bands (bands.allocate_rv), so no RV segment appears in Fig1, Fig2 or Fig5 (the detailed RV band is kept in data and ED10). Fig5 caption added, and Market balance is its only negative segment. Arial font where installed (Liberation Sans fallback). Strategies renamed 'Avoid / Switch / Improve Strategies'. Fig1-Fig8 sizes, fonts and legends restyled; Fig6 axes now end at 85%.
* Final figure tweaks: Fig2 two-line legend inside panel a, panel d y-axis on the left; Fig3 panel a y max 1,650, panel b legend upper left and tighter; Fig4 panel c headroom for the TL1 label; Fig6 legend 3×3 without the zone and ruler entries, cropped at the ruler labels; Fig7 legend Moderate / Ambitious / Theoretical limit; Fig8 panel a two-line tick labels centred. Figures-only export (600 dpi); data byte-identical.

## Fig5 replaced by the model schematic

Figures only: no model or Monte Carlo rerun. One `--figures-only` export (600 dpi PNG); the data were byte-identical
afterwards (`outputs/logs/figures_only_check.json`: changed = []).

* **Placement.** Extended Data already holds ten items (ED1–ED10), so the former Fig5 (reduction by demand band) moved
  to **Supplementary as SF7** (`SF7_reduction_by_demand`, same drawing code and data). The rest of the Extended Data
  is unchanged. SF1 (the older schematic) is kept as it was.
* **Files.**
  * new `figures/fig5_schematic.py`, drawing `Fig5_model_schematic`;
  * `figure_plan.py`: Fig5 entry, SF7 entry, `MAINTENANCE_ALLOWED` and `RETIRED` updated;
  * `figures/paper_main.py`: the old fig5 now saves as SF7;
  * `tests/test_figures_v3_3_2.py`: main-figure list;
  * outputs: the new Fig5 and SF7 PNGs and their audits; the old Fig5 PNG and audit removed; FIGURES.md and INDEX.md
    regenerated (INDEX.md was out of date and now also lists the files added since v4.2).
* **Design.** It follows the author's layout script (schem3). Colours come only from `style.py`: display-band
  colours, strategy colours for the chip edges, Reference / Pathway / TL colours for the ladder, and AR for the
  budget box. Fonts are 5–8 pt. The PNG was checked visually: no text overlaps.
* **Band widths (b).** Reference cumulative floor area 2026–2050, in scope (`baseline/bands_annual.csv` summed through
  `bands_display_map.csv`), in Mm²:

  | band | Mm² |
  |---|---|
  | Population growth | 40.588 |
  | Household-size change | 1.885 |
  | Extra space | 26.359 |
  | Vacancy | 3.919 |
  | Net replacement | 8.948 |
  | Market balance | −0.169 |

  * Market balance nets to about zero (2026 overbuild +4.545, overbuild absorbed −4.713). It is drawn at a fixed
    5 mm width and labelled "net −0.2 Mm² (not to scale)".
  * The other five bands share the remaining width in proportion. Each band's value is printed on the figure.
* **Lever → band mapping (c).** This comes from the model output, not from the draft layout. Each lever goes under the
  display band whose in-scope floor area its single-lever Ambitious run reduces most (`pathways/bands.csv`,
  Reference − run). A dashed connector marks a further band with ≥ 20% of that lever's floor-area reduction. The
  script asserts that this mapping matches the chip layout and fails otherwise. Floor-area reductions, Mm²:

  | lever | primary band | further band |
  |---|---|---|
  | L1 | Household-size change 2.87 | Extra space 2.43 |
  | L2 | Vacancy 5.20 | — |
  | L3 | Net replacement 4.73 | — |
  | L4 | Extra space 6.75 | — |
  | L5 | Population growth 5.88 | Extra space 3.78 |

  * **L5 differs from the draft**, which placed it under Extra space. L5 scales the occupied floor area per person
    (OLF), and the population-growth band is population growth × OLF (`engine.forward`). L5 therefore reduces that
    band most. The population itself stays exogenous ("driver (exogenous)").
  * L6–L9 change no floor area; the script asserts a zero floor-area change in their runs. They sit under the
    separate carbon-intensity bar.
* **Tests.** 34 of 35 figure tests pass. `test_figures_v3::test_audit_sign_and_boundary_rules` fails on
  `ED10_detailed_demand_bands` (maintenance is drawn but ED10 is not in `MAINTENANCE_ALLOWED`). It fails identically
  on the previous commit, so it predates this change, and it is left for the author to decide.

## Figure revisions (figures only; Fig5 schematic dropped)

Figures only. The figures were redrawn from the existing outputs with one `--figures-only` export (600 dpi PNG); the
deterministic model and the Monte Carlo were not rerun. The data were byte-identical afterwards
(`outputs/logs/figures_only_check.json`: changed = []). Each changed PNG was checked visually: no overlaps.

* **Fig5 schematic dropped.**
  * `figures/fig5_schematic.py`, its PNG and its audit record are deleted, and its `figure_plan` entry is removed.
  * Fig5 is vacant; no other figure or reference is renumbered.
  * The reduction by demand band stays in Supplementary (SF7).
  * `tests/test_figures_v3_3_1::test_display_item_limits` now expects Fig1–Fig4 and Fig6–Fig8;
    `tests/test_figures_v3_3_2` expects the same main list.
* **Fig2.**
  * The in-panel legends are removed. One legend row now sits below panels a–d, each block under its own panel:
    demand bands and the carbon line under a (2 columns), materials under b (2 columns), life-cycle stages under c
    (1 column).
  * Entries, order and colours are unchanged.
  * The figure is now 108 mm high (was 82 mm), and panel a's top headroom drops from ×1.16 to ×1.04.
* **Fig3.** The panel a y-axis maximum is 1,580 (was 1,650).
* **Fig4.**
  * Panel titles are the pathway name only (Moderate Pathway, Ambitious Pathway, Theoretical Limit).
  * The legend title "Waterfall steps" is removed.
  * "Improve Strategies" becomes "Improve Strategy".
* **Fig6.**
  * Every text is scaled ×1.45 (was ×1.25): ticks, axis labels, legend, contour labels and ruler annotations.
  * The ruler annotations are on two lines, centre-aligned, with label spacing raised to fit them.
  * Axis titles: x "Sufficiency: Floor area reduction (%)", y "Efficiency: Carbon reduction per m² (%)". The
    definitions (2027–2050, vs the Reference, A1–A5 + soil + B2/B4) remain in the figure_plan caption.
  * Legend: "Moderate / Ambitious Pathway" becomes "Pathways", and "Improve Strategy" is singular.
* **Fig7.**
  * Lever labels are on two lines (split at the space nearest the middle), centre-aligned.
  * The strategy annotations are centre-aligned and read "Improve Strategy".
  * The legend font is 6 pt (was 5.5 pt).
* **Label scope.** The singular label is a figure-level map (`paper_main.STRATEGY_LABEL`); `naming.STRATEGIES` and the
  data labels are unchanged. ED5 shares the same legend map, so its legend now also reads "Improve Strategy".
* **Fig8.** Unchanged.
* **Tests.** 27 of 28 figure tests pass. The remaining failure is the pre-existing ED10 maintenance rule recorded above,
  unchanged.
