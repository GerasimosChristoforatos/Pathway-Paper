# MODEL v3.3.1: final figure layout

Branch `release/model-v3.3.1`, from `main` after PR #15 (MODEL v3.3.0) was merged. This release changes figure code
only. The one exception is item 5: the deterministic steps Reference → TL1 … TL9, added cumulatively from the
Reference, are written to `pathways/waterfall_tl_from_reference.csv`. There is no Monte Carlo re-run. All figures are
PNG only (600 dpi in the full profile, 200 dpi in the light profile), and every PDF output has been removed.

## Equality with v3.3.0

* `pathways.py` was re-run in both profiles (17-23 s each). Every existing data file is byte-identical before and
  after (103 files in each profile, hashed with SHA-256). The only new file is `waterfall_tl_from_reference.csv`,
  which is identical in the two profiles.
* `tests/test_figures_v3_3_1.py` checks every file of the v3.3.0 lock (`tests/regression_model_v3_3.json`): the 31
  deterministic files and the Monte Carlo files of the active profile. They all keep their v3.3.0 hashes, so every
  deterministic total is unchanged.
* The new lock is `tests/regression_model_v3_3_1.json`: 32 deterministic files plus the Monte Carlo hashes.
* Check of the new steps: the TL step totals equal the prefix subsets {L1}, {L1, L2}, … of the existing levers_tl
  Shapley game exactly (relative difference 0), and the last step equals the TL run. The bands of each step add up to
  its total (1e-9).

## Display items

| MODEL v3.3.0 | MODEL v3.3.1 |
|---|---|
| (new) | **Fig1** Model schematic |
| Fig1 Floor area | **Fig2** Floor area by demand band |
| Fig2 Reference carbon | **Fig3** Reference carbon |
| Fig3 Reference vs boundaries | **Fig4** Reference vs boundaries |
| Fig5 Waterfalls (by demand band) | **Fig5** Three net waterfalls from the Reference |
| Fig6 Solution space | **Fig6** Solution space (axes -5% to 110%) |
| Fig8 Shapley by lever | **Fig7** Shapley by lever |
| Fig7 Tornado + ED5 conditional TL | **Fig8** Uncertainty: (a) tornado, (b) TL against the 2050 population |
| ED3 Cumulative population / households / floor area (1 × 3) | **ED1** Population, households, floor area (3 × 1) |
| ED1 Census replacement rates | ED2 |
| ED2 Household formation and size | ED3 |
| ED14 Overbuild absorption | ED4 |
| Fig4 Pathways annual | **ED5** |
| Fig5 / ED7 waterfalls by demand band | **ED6** (Moderate and Ambitious; 2 × 2) |
| ED6 Single levers | ED7 |
| ED8 TL Shapley and indicators | ED8 |
| ED13 Replacement variants | ED9 |
| ED9 Roll-out timing | ED10 |
| ED4 MC scatter vs population rank | **SF1** (`outputs/supplementary/`) |
| ED5 Conditional TL (quintiles, threshold) | **SF2** (its threshold panel is also Fig8b) |
| ED10 Lambda sweep | SF3 |
| ED11 Harrell-Davis estimators | SF4 |
| ED12 Consent sizes | SF5 |

ED items are capped at 10 (Nature Cities). The supplementary set was chosen as the items least needed to read the
main results: the rank scatter (SF1) and the quintile view (SF2) duplicate Fig8b; the lambda sweep (SF3) duplicates
the Moderate/Ambitious midpoint rule; SF4 and SF5 document lever estimators that Table 1 summarises. This choice is
for the author to confirm.

## Items and decisions

1. **Fig1 schematic.** Built from matplotlib boxes and arrows.
   * Top row: the conversion chain, ending in the "compared with planetary boundaries (AR, AtP)" box. That box is
     dashed and red-edged because it is a comparison, not a conversion step.
   * Below: three strategy bands. Each lever sits under the step it acts on: L6 and L7 under "site / soil", L8 under
     "materials", L9 under "A4–A5".
   * Right: the four-rung ambition ladder.
   * Footer: the adoption window, read from `pathways/levers.json` (full by 2035).
   * Lever names come from `naming.LEVERS`.
2. **Fig2.**
   * Census-interval columns are separated by 10% of each interval's width (5% on each side). There is no gap at the
     history | projection join.
   * Each projection year is drawn over its own width (2025.5-2050.5), so history and projection meet at the dotted
     line at 2025.5.
   * New labels: "History (census-interval means)", "Projection (annual; 2026 observed)", "Population growth",
     "Floor area built (in scope)". Only bands present are shown.
   * The run note (FIGURES.md) carries the caption sentence with ρ read from `baseline/overbuild_2026.json`:
     ρ = 0.518, which displays as 0.52, absorbed by 2035.
3. **Fig3.** Only bands present appear in the legend; "Released dwellings (TL)" and "Surplus kept vacant (2050)" are
   dropped. New labels: "Carbon (in scope)" and "Maintenance (B2, B4)".
4. **Fig4.**
   * The legend lists only the lines and the two budget zones; "Boundary exceeded" is removed.
   * The exceeded fill is now slightly redder: opacity 0.035 → 0.07, same hue. This is set once in `style.ZONE`, so
     every boundary figure stays consistent. `tools/palette_check.py` confirms the lightness order still holds under
     every simulated vision type (J′ 89.6 < 95.1 < 97.8).
   * The committed column is a separate bar next to the 2026–2050 bar, by stage only, labelled on the bar:
     * C1–C4: 4,687 kt (2025 factors);
     * B2/B4 after 2050: 3,197 kt (lower, 2050 factors held, solid) to 3,929 kt (upper, 2025 factors; the hollow
       part).
   * The budget ticks are labelled on the axis; there is no legend.
5. **Fig5.**
   * Three panels, all starting from the Reference, with levers added in PAS 2080 lever order:
     * (a) L1 … L9 at Moderate → Moderate Pathway;
     * (b) L1 … L9 at Ambitious → Ambitious Pathway;
     * (c) TL1 … TL9 cumulative → Theoretical Limit.
   * Each step is one solid bar in its strategy's colour, with its net value on top. There are no outlines and no
     new-total ticks.
   * **No step is net positive in any panel**; the figure note states "Net-positive steps: none", and a test checks
     this.
   * Steps (kt):
     * (a) Moderate: −696, −667, −539, −661, −1,176, −492, −96, −703, −510;
     * (b) Ambitious: −1,382, −1,315, −1,066, −1,206, −1,995, −758, −102, −1,076, −795;
     * (c) TL from the Reference: −4,614, −4,418, −2,567, −1,964, −1,001, −530, −8, −680, −475.
   * The demand-split waterfalls, with the existing outline rule, are now ED6.
6. **Fig6.**
   * Both axes run from -5% to 110%.
   * Light, sparse hatching marks y > 100% "carbon-negative buildings" and x > 100% "negative construction".
   * Both branches of the AtP contour are drawn exactly, from (1 − x)(1 − y) = (B_AtP − C_2026) / C_ref,2027–50 =
     −0.01605. One branch has x < 1 and y > 1 (101.6% at x = 0); the other has y < 1 and x > 1 (101.6% at y = 0). A
     test checks every point of both branches against the contour equation (1e-9).
   * New annotation: "AtP requires negative construction or carbon-negative buildings".
   * **Departure from the brief: the negative strips.** The zones, including the strips x < 0 and y < 0, are
     coloured from the analytic LoE field. The strips therefore show the exceeded fill wherever the field exceeds AR,
     which is most of each strip. Two small parts of the strips (x < 0 above the AR line, about y > 84%, and the
     mirror part of y < 0) are within AR on the plane. They are shown as within AR, not painted as exceeded, because
     painting them would contradict the AR line drawn through them.
7. **Fig7.** Unchanged. The caption now explains the TL dots: they are Shapley values within the TL game, so they
   include interactions at the limit, and L5 interacts with L4 because both act on floor area per dwelling.
8. **Fig8.**
   * **(a) Tornado, on the cumulative LoE AR.** Carbon would not work as the axis, because the AR base-window rows
     move only the budget, not the carbon.
     * The two colours (input at low end in blue, at high end in vermilion) follow the input, not the outcome. For
       example, the low household-size variant gives the higher LoE.
     * Each row is labelled with its input and its range as defined in the data:
       * Population: Stats NZ 5th–95th percentile.
       * Household size: Stats NZ low–high variant.
       * Replacement: Low (0.10%) – Very High (trend); the High variant is marked as a tick.
       * Replacement half-life: 5–15 yr.
       * Completion rate: 0.92–0.96.
       * Carbon factors: **case-study jackknife** low–high. The brief said "bootstrap 5th–95th", but the tornado row is
         the jackknife; the bootstrap defines the Monte Carlo input distribution, not this row.
       * Soil order: lowest (Raw) – highest (Organic).
       * Overbuild absorption: by 2030 – by 2045.
       * AR base window: 5–34 yr (central 2016–2025); the 20-yr window is marked as a tick. These values come from
         `sensitivity/planetary_boundary.csv`.
     * **Not included: "Dwelling size (MC 5th–95th)".** No one-at-a-time dwelling-size row exists in the sensitivity
       tables, and adding one requires a new sensitivity run, which is outside a figure-only release. No AtP
       base-window row exists either; the AtP budget does not depend on the AR base window.
     * The LoE panel of the old Fig7 is dropped; its values remain in `sensitivity/tornado.csv` and D42.
   * **(b)** TL cumulative LoE AR against the 2050 NZ population across the 5,000 draws (light points), with:
     * the Firth logistic P(LoE AR ≤ 1) on the right axis;
     * the 50% threshold with its bootstrap 95% CI;
     * the text "TL within AR in X% of draws", where X is read from `montecarlo_conditional_tl.json` (55% in the full
       profile).
9. **ED1** (3 × 1): history in black, projection in dark red, with a band.
   * **Departure from the brief: the band.** It is the **Stats NZ population 5th–95th percentile paths** run through
     the model (the ED3 data), not a Monte Carlo band. The outputs hold no Monte Carlo percentiles of population,
     households or cumulative floor area (`montecarlo/annual_REF.csv` holds annual floor area built and carbon only).
     The band is labelled accordingly.
   * The dark red reuses the AtP hex; no boundary is drawn in ED1.
   * The households panel states the rebasing: "History rebased on the 2023 census (occupied + residents-away private
     dwellings): Stats NZ household increments after 2018 × 0.824".

## PNG only

* `runprofile` full formats changed from ('pdf', 'png') to ('png',).
* `style.save` refuses any format other than PNG.
* `tools/check_outputs.py` fails if any PDF is present.
* The 62 PDFs previously tracked under `outputs/` are deleted.
* `test_no_pdf_written_png_only` checks the profile's output tree.

## Tests (`tests/test_figures_v3_3_1.py`)

The new tests cover:

* equality with the v3.3.0 lock (deterministic files and Monte Carlo files);
* the Fig5 panels: the steps add up from the Reference to each end total, and each end equals its run (1e-12);
* the TL steps against the levers_tl prefix subsets, and their band sums;
* the reporting of net-positive steps;
* the Fig6 markers, and both AtP branches plus the AR line against the contour equation (1e-9);
* no PDF anywhere;
* the display-item limits (at most 8 main and 10 ED items).

Existing tests were updated for the new ids: `test_figures_v3`, `test_events`, `test_profiles`, and the Fig6 axis
rule in `test_model_v3_3`.

## Timings

See the run report in the PR / session.
