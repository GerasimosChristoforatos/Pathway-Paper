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
