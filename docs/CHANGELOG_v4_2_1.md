# MODEL v4.2.1 — signed household-size band and final main-figure fixes

Branch `release/model-v4.2.1`, from `release/model-v4.2.0`. `HH_SIZE_PATH` stays `'statsnz_2018'`.

## Model

* **Signed household-size band.** It is now `d_hh·occ − pop_growth·olf`, and is negative when households consolidate
  (`engine.forward` hs_pos; `projection` hist_hs_pos). Population growth is now gross (`pop_growth·olf`).
* **Totals unchanged.** `pathways/runs.csv` and `baseline/annual.csv` equal v4.2 (relative difference 0). Only the band
  composition changes, and the band sums still equal the totals every year (1e-9).
* **Monte Carlo.** Not rerun; the v4.0 outputs are reused.
* **Lock.** The hashes of the eight band-composition files are updated in `tests/regression_model_v4.json`.

## Figures (one 600 dpi export; data byte-identical)

* **Fig1** — the signed household-size band, drawn below zero when negative.
* **Fig2** — compact legend in panel a (two columns, inside the plot).
* **Fig3**
  * (a) adds the Moderate Pathway (orange), the Ambitious Pathway (darker orange, `style.PATHWAY_SETTING`) and the TL
    (dark green, dotted).
  * (b) adds a 50% interval to the 95% interval; the committed stack is B2/B4 at the lower bound plus C1–C4, with no
    range whisker.
* **Fig4** — the annual panel is removed; the three waterfalls are now a–c, at about 60% of the old height, in the new
  oranges.
* **Fig5** — six bands plus Re-used dwellings (TL); legend at the bottom.
* **Fig6** — the AtP annotation, the ruler values and the plane floor are removed.
* **Fig7**
  * (a) each lever alone vs the Reference, in kt;
  * (b) Shapley share (%) within each game.
  * The single-lever ED figure is deleted; the old ED8–ED11 become ED7–ED10, so there are 10 ED items again.
* **Fig8** — caption note on the flat left tail.
