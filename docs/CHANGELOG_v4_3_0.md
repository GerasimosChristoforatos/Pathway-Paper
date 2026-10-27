# MODEL v4.3.0

Branch `release/model-v4.3.0`, from `release/model-v4.2.2`.

**Scope.** Figures only; no model change. No Monte Carlo was run and the deterministic model was not rerun: every
figure was redrawn from the stored outputs with one `--figures-only` export (600 dpi PNG). The data were
byte-identical afterwards (`outputs/logs/figures_only_check.json`: changed = []).

**Added data file.** `outputs/data/ed_number_map.csv`, the Extended Data numbering. It was written from
`figure_plan.ED_NUMBER_MAP` by `tools/ed_number_map.py` before the export, and `pathways.py` now writes it with the
deterministic outputs.

Each changed PNG was checked visually: no overlaps. Figure tests: 35 of 35 pass. The ED10 maintenance-rule failure
reported in v4.2.2 is gone because ED10 is no longer rendered.

## Fig3 (main): shape-preserving interpolation (display only)

* **Caption note.** "Lines are shape-preserving (PCHIP) interpolation between annual values."
* **Method.** Every annual series of panel a is drawn with `scipy.interpolate.PchipInterpolator`, at 12 points per
  year (`draw.pchip`). This applies to:
  * the Monte Carlo median and the 50% and 90% band edges;
  * the Moderate and Ambitious Pathway and TL;
  * the AR and AtP lines and their zones.
* **Properties.** The curve passes through every annual value (asserted) and does not overshoot between neighbouring
  values.
* **Not used.** No moving average, LOWESS or ordinary cubic spline.
* **Stacked areas.** Panel a has none, so the per-component rule did not apply.
* **Bands.** The lower and upper edges are interpolated separately. On the fine grid the check lower ≤ median ≤ upper
  passed for both bands, so the linear fallback (`draw.pchip_band`) was not used; it is recorded in the figure note.
* **Segments.**
  * Fig3 has no history. The observed pipeline years (2026–2027, from consents already issued) and the modelled years
    (2028 on) are interpolated as separate segments that share the 2027 knot, so the observed → modelled join is not
    smoothed.
  * The 2026–27 segment has two points, so it is linear.
  * The budget lines are one segment.
* **Markers.** Small dots (1.4 pt) mark the annual values of the median and the three runs.
* **Unchanged.** The y-axis maximum stays at 1,540, and panel b is unchanged.

## Fig8b (main): Reference, Ambitious Pathway and TL on the paired draws

* **Data.** The stored Monte Carlo draws (`pathways/montecarlo_draws.csv`, n = 5,000). The Reference, Ambitious and TL
  LoE AR come from the same draw, so they share the same 2050 population.
* **Markers.**
  * Reference: grey square.
  * Ambitious Pathway: dark orange triangle.
  * TL: forest green circle, drawn last, larger and darker.
* **Axes and lines.** The y-axis is on a log scale with plain-number ticks. The AR line stays at LoE = 1. The TL
  threshold line (Firth logistic P(LoE AR ≤ 1) = 50%: 6.614 M, bootstrap 95% CI 6.611–6.616 M) keeps its label and
  stops below the legend.
* **P(LoE AR ≤ 1).** Proportion of draws, with the Wilson 95% interval (`mcstats.wilson`):

  | run | draws ≤ 1 | P(LoE AR ≤ 1) | Wilson 95% |
  |---|---|---|---|
  | Reference | 0 of 5,000 | 0.00% | 0.00–0.08% |
  | Ambitious Pathway | 1 of 5,000 | 0.02% | 0.00–0.11% |
  | Theoretical Limit | 2,494 of 5,000 | 49.88% | 48.49–51.27% |

  The TL value equals the stored `montecarlo_conditional_tl.json` value (asserted).
* **Unchanged.** Panel a.

## Extended Data

* **No longer rendered.** ED5 (pathways annual), ED6 (waterfalls by demand band), ED7 (TL Shapley and indicators) and
  ED10 (detailed demand bands).
  * They are removed from `figure_plan.PAPER_EXTENDED`, and their PNGs and audit records are removed from outputs.
  * Their code is kept in `figures/paper_extended.py`.
* **New ED5: Shapley attribution (order-independent)** (`ED5_shapley_attribution`), in ED7's place.
  * One row per lever L1–L9, in PAS 2080 order, grouped Avoid / Switch / Improve.
  * Three bars per row: Moderate (hollow, strategy colour), Ambitious (filled, strategy colour) and TL (TL green).
  * A total row, with the values labelled in Mt and as % of the Reference.
  * Bottom axis: Mt CO₂e. Top axis: % of the Reference cumulative carbon 2026–2050 (19,761 kt).
  * Data: the stored exact Shapley values, 2^9 coalitions per game (`pathways/shapley.csv`, games `levers_moderate`,
    `levers_ambitious`, `levers_tl`). Nothing was recomputed.
  * The title says "Shapley attribution (order-independent)", to set it apart from the sequential waterfalls of Fig4.
* **Shapley sum check.** The lever sum is compared with Reference − pathway cumulative; the tolerance is 0.1% and the
  figure stops if it is exceeded:

  | game | Σ levers (kt) | Reference − pathway (kt) | relative difference |
  |---|---|---|---|
  | Moderate Pathway | 5,459.650 | 5,459.650 | 1.7e-16 |
  | Ambitious Pathway | 9,494.443 | 9,494.443 | 0 |
  | Theoretical Limit | 15,338.501 | 15,338.501 | 0 |

  As shares of the Reference cumulative carbon: 5.5 Mt (28%), 9.5 Mt (48%) and 15.3 Mt (78%).
* **ED7 roll-out timing (was ED9).** Panels a and b are unchanged. New panel c shows the cumulative carbon 2026–2050 as
  the running sum, for Moderate and Ambitious under the three roll-out variants, in the same colour and line styles as
  a and b. The Reference cumulative is a grey line. Units are kt CO₂e. The 2050 end values equal `runs.csv`
  (asserted), in kt:

  | variant | Moderate | Ambitious |
  |---|---|---|
  | by 2030 | 13,737 | 9,350 |
  | by 2035 (adopted) | 14,302 | 10,267 |
  | by 2045 | 15,395 | 12,091 |

  Reference: 19,761 kt.
* **Old → new map** (`outputs/data/ed_number_map.csv`):

  | old | new |
  |---|---|
  | ED1–ED4 | ED1–ED4 (unchanged) |
  | ED5 pathways annual | not rendered |
  | ED6 waterfalls by demand band | not rendered |
  | ED7 TL Shapley and indicators | not rendered |
  | ED8 replacement variants | ED6 |
  | ED9 roll-out timing | ED7 |
  | ED10 detailed demand bands | not rendered |
  | — | ED5 Shapley attribution (new) |

* **References updated.**
  * The Fig4 caption now says "Shapley values in Fig7 and, per lever and pathway, in ED5" (was "split by demand band
    in ED6").
  * `figure_plan` module docstring (ED1–ED7), `PB_FIGURES`, `MAINTENANCE_ALLOWED`, `RETIRED`, and the `pathways.py`
    docstring.
* **Main figures.** Not renumbered.

## Files

`figures/draw.py` (`pchip`, `pchip_grid`, `pchip_band`), `figures/paper_main.py` (Fig3, Fig8),
`figures/paper_extended.py` (ED5 new, ED6 and ED7 renamed, ED7 panel c), `figure_plan.py`, `pathways.py` (writes the
map), `indexes.py`, `tools/ed_number_map.py`; outputs: PNGs, audit records, FIGURES.md, INDEX.md and
`data/ed_number_map.csv`.
