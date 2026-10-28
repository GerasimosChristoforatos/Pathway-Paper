"""The figures of MODEL v3.0.0: one registry, read by layout.figure (where a figure is written), the figures/ package
(what draws it), indexes.py (outputs/FIGURES.md) and the tests.

    outputs/paper_main/       Fig1-Fig7 (PAPER_MAIN; MODEL v4.3.0)
    outputs/paper_extended/   the Extended Data ED1-ED7 (PAPER_EXTENDED; MODEL v4.3.0) and the per-typology level table
    outputs/supplementary/    further figures (SUPPLEMENTARY; MODEL v3.3.1: at most ten Extended Data items)
    outputs/diagnostics/<group>/  calibration, validation, boundaries, pathways, montecarlo, sensitivity (DIAGNOSTICS)

Every figure is drawn by a module of figures/ from the data files of outputs/data/ only (compute / draw
separation); `module` names it, `source` lists the data files it reads (relative to outputs/data/).
Figures are PNG only (runprofile.py: 600 dpi full, 200 dpi light; MODEL v3.3.1). Figure ids of MODEL v2.1 that are not carried forward are listed in
RETIRED with the reason (docs/FIGURE_PLAN_v3.md).
"""
# MODEL v4.3.2: the row notes of ED4 and ED5 as figures/sensitivity.py writes them under the axes (read from the model
# code and the committed outputs); copied here so they reach the captions and FIGURES.md, and checked equal to the
# generated text by tests/test_figures_v4_3_2.py
ED4_ROW_NOTES = (
    'Household size (2018–23 pace): household size continues linearly from 2023 at the 2018–2023 '
    'census-interval pace instead of the Stats NZ household-size path rebased on 2023.',
    'Population (5th–95th pct.): Stats NZ 2024-base stochastic projection, 5th / 95th percentile path '
    'instead of the median.',
    'Household size (smaller–larger households): Stats NZ Low / High household-size variant (smaller / '
    'larger households) instead of the Medium variant.',
    'Household size after 2043: end-slope taper: from the shape-preserving (PCHIP) end slope at 2043 the '
    'slope tapers to zero over 5 years, instead of a zero slope imposed at 2043 and household size held '
    'constant after 2043.',
    'Household size after 2043: secant-slope taper: the last published interval (2038–2043) linear at its'
    ' secant slope, the slope then tapering to zero over 5 years, instead of a zero slope imposed at 2043'
    ' and household size held constant after 2043.',
    '2026 overbuild booked as stock-neutral redevelopment: the 2026 overbuild (building above need in '
    '2026–2027 and its continuation, fading at ρ = 0.43) replaces existing dwellings instead of adding to'
    ' the stock: no surplus, so no absorption payback and no soil carbon loss on it.',
    'Dwelling-size reference window 2016–2025: new-dwelling size held at its 2016–2025 mean per typology '
    'instead of the 2023–2025 mean.',
    'Completion rate (0.93–0.96): 0.93 / 0.96 of consented dwellings completed instead of 0.945.',
    'Vacancy rate: 1986–2023 census mean: the mean of the 1986–2023 censuses on one definition instead of'
    ' the 2023 census value (5.39%).',
    'Overbuild absorbed (by 2030–by 2045): the 2026 overbuild absorbed by 2030 / 2045 instead of 2035.',
    'Completion lag (15–19 months): consents lagged 15 / 19 months instead of 17.',
    'No 2026 data (consents to Dec 2025): consents to December 2025 and the projected 2026 population '
    'instead of consents to July 2026 and the observed 2026 population growth.',
    'Replacement (Low–Very High): Low: the 1991–2023 long-run net rate throughout; High (tick): the '
    '2018–2023 rate persists; Very High: the 1991–2023 census-interval trend continues; instead of the '
    '2018–2023 rate fading to the long-run rate with a 10-year half-life.',
    'Replacement half-life (5–15 yr): 5 / 15 years instead of 10.',
    'Soil order (Raw–Organic): the soil carbon loss of the lowest (Raw) / highest (Organic) soil order on'
    ' every new footprint instead of the area-weighted mean over the soil orders of the Auckland land '
    'zoned for urbanisation.',
    'Single case study (lowest–highest): the materials factor of the lowest / highest single case study '
    'of each typology instead of the pooled typology factor.',
    'Frozen technology (2025 factors held): every factor held at 2025 instead of A1–A3 on the item paths '
    'of Horup et al. (2025) and A4–A5 falling 1% per year.',
    'Carbon factors (jackknife): the lowest / highest pooled materials factor when each case study is '
    'left out in turn, instead of the pooled factor (a spread, not a confidence interval).',
    'NZ-made electricity-intensive items held at 2025 factors: items made in New Zealand with '
    'electricity-intensive production held at 2025 instead of following their Horup et al. (2025) path.',
    "A4–A5 decarbonisation (own path–held at 2025): A4–A5 on each item's own Horup et al. (2025) path / "
    'held at 2025 instead of the generic 1% per year decline (Resch et al. 2021).',
    'Soil carbon loss on all floor area, incl. replacement: soil carbon loss also on replacement floor '
    'area instead of none on rebuilt footprints.',
    'Proxy-mapped items held at 2025 factors: items mapped to a proxy material held at 2025 instead of '
    "following the proxy's path.",
)
ED5_ROW_NOTES = (
    'Carrying capacity: 1 W/m² boundary (not 2 °C): 1 W/m² planetary boundary (Bjørn & Hauschild 2015), '
    'safe operating space 3.61 × 10¹² kg CO₂e per year, instead of the 2 °C carrying capacity (Bjørn & '
    'Hauschild 2015), 6.81 × 10¹² (the same global impact); both budgets move.',
    'AR base window (5–34 yr): mean sector emissions over 5 / 20 / 34 years (2021–2025, 2006–2025, '
    '1992–2025) instead of 10 years (2016–2025); AR only.',
    'Economic allocation measure: GDP per capita, current US$: GDP per capita in current US$ instead of '
    'GDP per capita at purchasing-power parity, constant 2021 international $ (World Bank WDI); AtP only.',
    'Sector share: ratio of sums (not mean of ratios): FCE share of GDP in the sector share: the ratio of'
    ' the summed FCE to the summed GDP of the 40 quarters 2016–2025 instead of the mean of the 40 '
    'quarterly FCE/GDP ratios 2016–2025; AtP only.',
    'Population (5th–95th pct.): Stats NZ 2024-base 5th / 95th percentile path instead of the median; '
    'carbon and both budgets move together.',
    "Population source: UN WPP 2024 median: UN WPP 2024 median for New Zealand instead of the model's "
    'population path (the Stats NZ 2024-base median from the observed 2025 level, with the observed 2026 '
    'growth); budgets only.',
    'Replacement (Low–Very High): as in Extended Data Fig. 4 (carbon only; the budgets are unchanged).',
    'Replacement half-life (5–15 yr): as in Extended Data Fig. 4 (carbon only).',
)

PAPER_MAIN = [
    dict(id='Fig1', file='Fig1_floor_area', width='double', module='figures.paper_main',
         title='Floor area: history and projection by demand band',
         caption='Floor area built per year by demand band: history as census-interval means (columns), the Reference '
                 'projection annually from 2026 (2026 observed). Positive bands stacked up from zero, negative bands '
                 '(overbuild absorbed, unconsented additions) down from zero. The black line is the floor area built '
                 '(in scope), annual 1992-2050 (history from consents, projection from 2026); the grey caps on the '
                 'history columns are the census-interval means. 2026 overbuild: observed 2026 building above need, fading from 2027 and absorbed by 2035.',
         source=['baseline/bands_history.csv', 'baseline/bands_annual.csv', 'baseline/annual.csv',
                 'baseline/overbuild_2026.json']),
    dict(id='Fig2', file='Fig2_reference_carbon', width='double', module='figures.paper_main',
         title='Embodied carbon of the Reference',
         caption='Annual embodied carbon of the Reference 2026-2050 by (a) demand band, (b) material and (c) life-cycle '
                 'stage; (d) cumulative 2026-2050 as three attached columns of the same total by demand band, material '
                 'and stage (negative demand bands outlined, hanging down to the total). Materials and stages are never '
                 'negative.',
         source=['baseline/bands_annual.csv', 'baseline/annual_by_material.csv', 'baseline/annual_by_stage.csv']),
    dict(id='Fig3', file='Fig3_reference_boundaries', width='double', module='figures.paper_main',
         title='The Reference against the planetary boundaries',
         caption='(a) Annual carbon, Monte Carlo median with 50% and 90% bands, against the acquired-rights (AR) and '
                 'ability-to-pay (AtP) boundaries and their zones; (b) cumulative carbon 2026-2050 with its Monte Carlo '
                 '90% interval (5th-95th percentile of the cumulative carbon) and 50% interval (25th-75th), the AR and '
                 'AtP budgets, and the '
                 'committed emissions after 2050: C1-C4 and B2/B4 after 2050, the latter a range (lower = 2050 factors '
                 'held, upper = 2025 factors).',
         source=['aesa/annual.csv', 'montecarlo/annual_REF.csv', 'montecarlo/draws_REF.csv', 'baseline/projection.json']),
    dict(id='Fig4', file='Fig4_pathways', width='double', module='figures.paper_main',
         title='The Pathways: the sequential waterfalls',
         # MODEL v4.3.1: the caption follows the figure (a-c since MODEL v4.2.1; the annual pathways are in Fig3a)
         caption='Sequential waterfalls of cumulative carbon 2026-2050 from the Reference, levers added in PAS 2080 '
                 'order: (a) L1 ... L9 at Moderate -> Moderate Pathway; (b) at Ambitious -> Ambitious Pathway; (c) TL1 '
                 '... TL9 cumulative -> Theoretical Limit. Each step is one bar coloured by strategy with its net change; '
                 'AR (solid) and AtP (dotted) budgets with their zones; order-free Shapley values in Fig6.',
         source=['pathways/annual.csv', 'pathways/waterfall.csv', 'pathways/waterfall_tl_from_reference.csv']),
    # MODEL v4.3.0: Fig6, Fig7, Fig8 renumbered Fig5, Fig6, Fig7 (Fig5 was vacant since MODEL v4.2.2)
    dict(id='Fig5', file='Fig5_solution_space', width='double', module='figures.paper_main',
         title='The solution space',
         caption='Cumulative level of exceedance of AR over uniform cuts of 2027-2050 floor area (x) and of carbon per m2 '
                 '(y) (after Horup et al. 2025), axes -5% to 100%, with S1-S3 (Moderate filled, Ambitious hollow), the '
                 'Moderate / Ambitious Pathway and the Theoretical Limit; analytic LoE AR contours and the exact AR line. '
                 'Right: the LoE AR ruler (log) with the Reference, the Pathways, TL, AR = 1, the plane floor (the 2026 '
                 'observed cohort alone) and AtP.',
         source=['pathways/solution_space.csv', 'pathways/backcast.json', 'pathways/runs.csv']),
    dict(id='Fig6', file='Fig6_shapley_levers', width='double', module='figures.paper_main',
         title='What each lever removes',
         caption='Shapley values within each combined game (Reference -> Moderate Pathway, -> Ambitious Pathway, -> TL; '
                 'exact, 512 subsets) on cumulative carbon 2026-2050: rows grouped by PAS 2080 strategy (S1 Avoid, S2 '
                 'Switch, S3 Improve) in the lever order and coloured by strategy; filled bar Moderate, hollow bar '
                 'Ambitious, large deep-green dot TL. The TL dots are Shapley values within the TL game (all nine '
                 'levers at their limit), so they include each lever\'s interactions at the limit; L5 (occupancy '
                 'density) interacts with L4 (extra space): both act on the floor area per dwelling.',
         source=['pathways/shapley.csv']),
    dict(id='Fig7', file='Fig7_uncertainty', width='double', module='figures.paper_main',
         title='Uncertainty',
         caption='(a) One-at-a-time ranges of the Reference cumulative LoE AR 2026-2050, each input at its low and high '
                 'end per its definition (population rows move the budgets with the path; AR base-window rows move the '
                 'AR budget only); not additive, not a joint interval. (b) The Reference, the Moderate and Ambitious '
                 'Pathways and the Theoretical Limit: cumulative LoE AR against the 2050 New Zealand population on the '
                 'same paired Monte Carlo draws, P(LoE AR <= 1) of each with its Wilson 95% interval, LoE = 1, and the '
                 'population at which the Theoretical Limit has P(LoE AR <= 1) = 50% (Firth logistic; bootstrap 95% CI).',
         source=['sensitivity/tornado.csv', 'sensitivity/planetary_boundary.csv', 'pathways/montecarlo_draws.csv',
                 'pathways/montecarlo_conditional_tl.json', 'baseline/scenarios.json', 'aesa/results.json']),
]

PAPER_EXTENDED = [
    # MODEL v4.3.1: nine items in this order (outputs/data/ed_number_map.csv, ED_NUMBER_MAP below)
    dict(id='ED1', file='ED1_population_households_floor_area', module='figures.paper_extended',
         title='Population, households and floor area: history and projection (Monte Carlo 5th-95th)',
         source=['figure_source/projection_paths.json', 'figure_source/D02_households.json']),
    dict(id='ED2', file='ED2_household_formation_size', module='figures.paper_extended',
         title='Household formation and household size', source=['baseline/household_formation_history.csv',
                                                                 'figure_source/D03_household_size.json']),
    dict(id='ED3', file='ED3_replacement_variants', module='figures.paper_extended',
         title='Low, High and Very High replacement: the Reference, the Pathways and TL',
         source=['sensitivity/replacement_variants.csv', 'pathways/annual.csv']),
    dict(id='ED4', file='ED4_one_at_a_time', module='figures.sensitivity',
         title='One at a time: cumulative embodied carbon 2026-2050 of the Reference',
         caption='One-at-a-time ranges of the Reference cumulative embodied carbon 2026-2050, grouped by category; each '
                 'input at its low (blue) and high (orange) end, a single alternative case grey, intermediate cases as '
                 'ticks; not additive, not a joint interval. Not shown (kept in the data file): household size held '
                 'flat after 2043 (the Reference is also held constant after 2043, with a zero slope imposed at 2043), '
                 'the overbuild gap against the 2026 requirement, no census under-construction correction, the '
                 'maintenance event timing L / n, and the version-history rows (their changes are in the note). '
                 'What each row changes compared with the Reference: ' + ' '.join(ED4_ROW_NOTES),
         source=['sensitivity/reference_carbon.csv']),
    dict(id='ED5', file='ED5_boundary_sensitivity', module='figures.sensitivity',
         title='Boundary definitions and allocation: cumulative LoE of AR and of AtP',
         caption='One-at-a-time ranges of the Reference cumulative level of exceedance 2026-2050 of (a) acquired '
                 'rights (AR) and (b) ability to pay (AtP): boundary definitions, allocation, population and '
                 'replacement. Not shown (kept in the data file): α = 1 (Hjalsted et al. SI tables) and the raw Stats '
                 'NZ 2024-base median population. What each row changes compared with the Reference: '
                 + ' '.join(ED5_ROW_NOTES),
         source=['sensitivity/planetary_boundary.csv', 'aesa/results.json']),
    dict(id='ED6', file='ED6_mc_input_distributions', module='figures.montecarlo',
         title='Monte Carlo input distributions',
         source=['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv',
                 'montecarlo/carbon_factors_REF.csv', 'pathways/montecarlo_draws.csv']),
    dict(id='ED7', file='ED7_sobol', module='figures.montecarlo',
         title='Sobol indices of the Reference: embodied carbon and floor area 2026-2050',
         source=['montecarlo/sobol_REF.csv']),
    # MODEL v4.3.1: ED8 Shapley attribution dropped (it duplicated Fig6a / Fig6b); ED9, ED10 -> ED8, ED9
    dict(id='ED8', file='ED8_lever_annual', module='figures.pathways',
         title='Each lever alone: annual embodied carbon at Moderate, Ambitious and the Theoretical Limit',
         source=['pathways/lever_annual.csv', 'pathways/annual.csv']),
    dict(id='ED9', file='ED9_rollout_timing', module='figures.paper_extended',
         title='Roll-out timing (the Pathways by 2030, 2035, 2045): annual and cumulative carbon',
         source=['pathways/annual.csv', 'pathways/runs.csv']),
]

# MODEL v4.3.1: Extended Data numbering, MODEL v4.3.0 (the last release) -> MODEL v4.3.1 (old id, old file, new id, new
# file); new id None: no longer rendered. The v4.2.2 -> v4.3.0 map is in docs/CHANGELOG_v4_3_0.md.
ED_NUMBER_MAP = [('ED1', 'ED1_population_households_floor_area', 'ED1', 'ED1_population_households_floor_area'),
                 ('ED2', 'ED2_household_formation_size', 'ED2', 'ED2_household_formation_size'),
                 ('ED3', 'ED3_replacement_variants', 'ED3', 'ED3_replacement_variants'),
                 ('ED4', 'ED4_one_at_a_time', 'ED4', 'ED4_one_at_a_time'),
                 ('ED5', 'ED5_boundary_sensitivity', 'ED5', 'ED5_boundary_sensitivity'),
                 ('ED6', 'ED6_mc_input_distributions', 'ED6', 'ED6_mc_input_distributions'),
                 ('ED7', 'ED7_sobol', 'ED7', 'ED7_sobol'),
                 ('ED8', 'ED8_shapley_attribution', None, None),
                 ('ED9', 'ED9_lever_annual', 'ED8', 'ED8_lever_annual'),
                 ('ED10', 'ED10_rollout_timing', 'ED9', 'ED9_rollout_timing')]


def write_ed_number_map():
    """outputs/data/ed_number_map.csv from ED_NUMBER_MAP (old id, old file, new id, new file, status). Written by
    pathways.py with the deterministic outputs and by tools/ed_number_map.py (MODEL v4.3.0; v4.3.1: with the
    Supplementary map, write_sf_number_map)."""
    return _write_number_map('ed_number_map.csv', ED_NUMBER_MAP)


def write_sf_number_map():
    """MODEL v4.3.1: outputs/data/sf_number_map.csv from SF_NUMBER_MAP (Supplementary Figures and Tables)."""
    return _write_number_map('sf_number_map.csv', SF_NUMBER_MAP)


def _write_number_map(name, rows):
    import csv
    import layout
    path = layout.writing(layout.data(name, frozen=False))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['old_id', 'old_file', 'new_id', 'new_file', 'status'])
        for oid, ofile, nid, nfile in rows:
            st = ('added' if oid == 'new' else 'from the diagnostics' if oid.startswith('D') else
                  'no longer rendered' if nid is None else 'moved to Supplementary' if nid.startswith('SF') and
                  oid.startswith('ED') else 'figure -> table' if nid.startswith('ST') else
                  'same number' if (oid, ofile) == (nid, nfile) else 'renumbered')
            w.writerow(['' if oid == 'new' else oid, ofile or '', nid or '', nfile or '', st])
    return path

# MODEL v3.3.1: Extended Data beyond the ten allowed (Nature Cities) -> outputs/supplementary/
# MODEL v4.3.0: the Supplementary Figures, one continuous series in reading order (calibration -> validation -> the
# boundary method -> sensitivity -> Monte Carlo -> the TL dwellings); 'folder' only organises outputs/supplementary/
SUPPLEMENTARY = [
    dict(id='SF1', file='SF1_households', folder='calibration', module='figures.calibration',
         title='Households: the published and census-benchmarked series, and household size against arrivals',
         source=['figure_source/D02_households.json',
                                                 'figure_source/D04_household_formation.json']),
    dict(id='SF2', file='SF2_stock_vacancy', folder='calibration', module='figures.calibration',
         title='Vacancy, dwellings per year by component and the vacancy definition',
         source=['figure_source/D05_stock_and_vacancy.json', 'figure_source/D06_vacancy_definition.json']),
    dict(id='SF3', file='SF3_census_replacement_rates', folder='calibration', module='figures.paper_extended',
         title='Net replacement rates from census dwelling counts and the four variants',
         source=['baseline/stock_identity_history.csv', 'figure_source/D07_net_replacement_rate.json']),
    dict(id='SF4', file='SF4_dwelling_size', folder='calibration', module='figures.calibration',
         title='New-dwelling size: realised and occupied floor area, and consented size by typology',
         source=['figure_source/D08_dwelling_space.json', 'pathways/levers.json']),
    dict(id='SF5', file='SF5_overbuild_absorption', folder='calibration', module='figures.paper_extended',
         title='The 2026 overbuild: absorption in the Reference and its timing sensitivity',
         source=['baseline/overbuild_absorption_log.csv', 'baseline/sensitivity_annual_carbon.csv']),
    dict(id='SF6', file='SF6_hindcast', folder='validation', module='figures.validation',
         title='Rolling-origin hindcast of dwellings built and the 2027 out-of-sample check',
         source=['figure_source/D14_hindcast.json', 'baseline/validation.json']),
    dict(id='SF7', file='SF7_completion_lag', folder='validation', module='figures.market_balance',
         title='Annual floor area by demand group: zero- and 17-month completion lag',
         source=['diagnostics/lag_comparison_annual.csv']),
    dict(id='SF8', file='SF8_reality_checks', folder='validation', module='figures.validation',
         title='The projection against the 1991-2025 range and the observed -> model handover',
         source=['figure_source/D15_reality_checks.json']),
    dict(id='SF9', file='SF9_prcc', folder='sensitivity', module='figures.sensitivity',
         title='Monte Carlo sensitivity: partial rank correlation of each input, Reference, Moderate Pathway and TL',
         source=['pathways/montecarlo_importance.csv']),
    dict(id='SF10', file='SF10_lambda_sweep', folder='sensitivity', module='figures.paper_extended',
         title='Each lever from the Reference to Ambitious (lambda sweep) and its Theoretical Limit',
         source=['pathways/lambda_sweep.csv']),
    dict(id='SF11', file='SF11_hd_estimators', folder='sensitivity', module='figures.paper_extended',
         title='Harrell-Davis estimators of L5 and L8 with bootstrap intervals', source=['pathways/levers.json']),
    dict(id='SF12', file='SF12_mc_convergence', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo convergence of the 2026-2050 percentiles', source=['montecarlo/convergence_REF.csv']),
    dict(id='SF13', file='SF13_pathway_mc', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo: annual carbon of the Reference, the Pathways and TL (median, 5th-95th)',
         source=['pathways/montecarlo_annual.csv', 'pathways/montecarlo_summary.csv']),
    dict(id='SF14', file='SF14_conditional_tl', folder='montecarlo', module='figures.paper_extended',
         title='When does TL stay within AR? By population quintile and the population threshold',
         source=['pathways/montecarlo_conditional_tl.csv', 'pathways/montecarlo_conditional_tl.json']),
    dict(id='SF15', file='SF15_tl_dwellings', folder='pathways', module='figures.pathways',
         title='The Theoretical Limit: need, released dwellings, re-occupation and dwellings built per year',
         source=['pathways/reoccupation_log.csv']),
]
# MODEL v4.3.1: Supplementary Tables (Markdown + CSV, outputs/supplementary/<folder>/)
SUPPLEMENTARY_TABLES = [dict(id='ST1', file='ST1_budget_construction', folder='boundaries', module='figures.boundaries',
                             title='The AR and AtP budgets: components, the budgets in 2025 and 2050 and the 2050 '
                                   'population modifier', source=['aesa/results.json',
                                                                           'figure_source/D22_boundaries.json'])]
# MODEL v4.3.1: Supplementary numbering, MODEL v4.3.0 -> MODEL v4.3.1 (old id, old file, new id, new file)
SF_NUMBER_MAP = ([(f'SF{i}', h, f'SF{i}', h) for i, h in enumerate(
    ['SF1_households', 'SF2_stock_vacancy', 'SF3_census_replacement_rates', 'SF4_dwelling_size',
     'SF5_overbuild_absorption', 'SF6_hindcast', 'SF7_completion_lag', 'SF8_reality_checks'], start=1)]
                 + [('SF9', 'SF9_budget_construction', 'ST1', 'ST1_budget_construction'),
                    ('SF10', 'SF10_prcc', 'SF9', 'SF9_prcc'),
                    ('SF11', 'SF11_pathway_sensitivity', None, None),
                    ('SF12', 'SF12_lambda_sweep', 'SF10', 'SF10_lambda_sweep'),
                    ('SF13', 'SF13_hd_estimators', 'SF11', 'SF11_hd_estimators'),
                    ('SF14', 'SF14_mc_convergence', 'SF12', 'SF12_mc_convergence'),
                    ('SF15', 'SF15_pathway_mc', 'SF13', 'SF13_pathway_mc'),
                    ('SF16', 'SF16_conditional_tl', 'SF14', 'SF14_conditional_tl'),
                    ('SF17', 'SF17_tl_dwellings', 'SF15', 'SF15_tl_dwellings')])
TABLE_MODULES = ('figures.paper_extended', 'figures.boundaries')      # the modules that write tables (TABLES)
# tables of the Extended Data (Markdown + CSV, outputs/paper_extended/)
EXTENDED_TABLES = [dict(id='EDT1', file='EDT1_levels_by_typology', title='Lever levels by typology: Moderate, '
                        'Ambitious and TL', source=['pathways/levers.json'])]

_d = lambda file, title, module, source: dict(file=file, title=title, module=module, source=source)
# MODEL v4.3.0: no separate diagnostic figures; every figure is a main, Extended Data or Supplementary figure
DIAGNOSTICS = {}
# figures drawn only in the full profile (their data exist only there)
FULL_ONLY = ('ED7_sobol',)

# Maintenance (B2, B4) drawn as its own layer: only in the band and stage breakdowns
MAINTENANCE_ALLOWED = ('Fig2_reference_carbon', 'Fig3_reference_boundaries')
# every figure with a planetary boundary on its axes (zones required; AtP dotted)
# (MODEL v4.3.1: ED10 -> ED9; SF9 budget construction is the Supplementary Table ST1, no axes)
PB_FIGURES = ('Fig3_reference_boundaries', 'Fig4_pathways', 'Fig5_solution_space',
              'ED3_replacement_variants', 'ED9_rollout_timing')

RETIRED = {
    'outputs/paper/ (Fig1-Fig6 of MODEL v2.1.2)': 'outputs/paper_main/ Fig1-Fig8 (new set)',
    'outputs/extended_data/ (ED1-ED13)': 'outputs/paper_extended/ ED1-ED14',
    'outputs/key_figures/ (K1-K6)': 'retired: their content is in Fig1-Fig8',
    'D30_l6_estimator': 'ED11 (L5 and L8 estimators)',
    'D11_floor_area_bridge_split': 'D10 (MODEL v3.0.0 splits demolition replacement and unconsented additions in '
                                   'every band set, so the appendix bridge equals D10)',
    'MODEL v3.3.1 renumbering': 'Fig1-Fig3 -> Fig2-Fig4 (Fig1 the new model schematic); Fig4 pathways annual -> ED5; '
                                'Fig7 tornado -> Fig8a; Fig8 Shapley -> Fig7; ED5 conditional TL -> Fig8b and SF2; '
                                'ED7 Ambitious waterfall -> ED6 (Moderate and Ambitious by demand band); '
                                'ED1, ED2, ED14, ED6, ED13, ED9 -> ED2, ED3, ED4, ED7, ED9, ED10; '
                                'ED4, ED10, ED11, ED12 -> SF1, SF3, SF4, SF5 (outputs/supplementary/)',
    'ED3_cumulative_households_population_floor_area': 'ED1 (population, households, floor area; 3 x 1)',
    'PDF output': 'retired in MODEL v3.3.1: figures are PNG only (600 dpi full, 200 dpi light)',
    'MODEL v3.3.2 renumbering': 'Fig2-Fig4 -> Fig1-Fig3; Fig5 waterfalls -> Fig4 (b-d) with the annual pathways (a); '
                                'Fig5 reduction by demand band (new); Fig1 schematic -> SF1 (SF1-SF5 -> SF2-SF6)',
    'MODEL v4.2.2 Fig5': 'Fig5 reduction by demand band -> SF7 (Extended Data full at ten items); the Fig5 model '
                         'schematic was added and then dropped; Fig5 is vacant, no other figure renumbered',
    'MODEL v4.3.0 Extended Data': 'v4.2.2 ED5 pathways annual, ED6 waterfalls by demand band, ED7 TL Shapley and '
                                  'indicators, ED10 detailed demand bands no longer rendered (their plotting code was '
                                  'deleted in the clean release); the full old -> new map is '
                                  'outputs/data/ed_number_map.csv',
    'MODEL v4.3.0 clean release': 'main Fig6-Fig8 -> Fig5-Fig7; Extended Data ED1-ED10 as ed_number_map.csv; '
                                  'Supplementary SF1-SF17 in topic folders (calibration, validation, boundaries, '
                                  'sensitivity, montecarlo, pathways); the diagnostics set D01-D44 is no longer drawn '
                                  '(its data files are still written): D02+D04 -> SF1, D05+D06 -> SF2, D07 -> SF3 (with '
                                  'v4.2.2 ED2), D08 + v4.2.2 SF6 -> SF4, D35 (a duplicate of v4.2.2 ED4) -> SF5, D14 -> SF6, '
                                  'D44 -> SF7, D15 -> SF8, D22 -> SF9, D40 -> SF10, D41 -> SF11, D37 -> SF14, '
                                  'D39 -> SF15, D34 -> SF17, D16 -> ED4, D42 -> ED5, D38 -> ED6, D20 -> ED7, '
                                  'D31 -> ED9; v4.2.2 SF3, SF4, SF5 -> SF16, SF12, SF13; v4.2.2 SF1 model schematic, '
                                  'SF2 Monte Carlo scatter (in Fig7b) and SF7 reduction by demand band, and D01, D03, '
                                  'D09, D10, D12, D13, D17, D18, D19, D21, D23-D29, D32, D33, D36, D43 deleted '
                                  '(docs/CHANGELOG_v4_3_0.md)',
    'MODEL v4.3.1 renumbering': 'ED8 Shapley attribution no longer rendered (the Shapley values are in Fig6); ED9, ED10 '
                                '-> ED8, ED9 (ed_number_map.csv). SF9 budget construction -> Supplementary Table ST1; '
                                'SF11 pathway sensitivity no longer rendered; SF10, SF12-SF17 -> SF9-SF15 '
                                '(sf_number_map.csv); panels dropped: SF1c, SF2b, SF4b (docs/CHANGELOG_v4_3_1.md)',
}


def all_figures(profile_full=True):
    """[(group, file id, module)] of every figure (FULL_ONLY figures only in the full profile: their data exist only
    there)."""
    keep = lambda f: profile_full or f not in FULL_ONLY
    out = [('paper_main', h['file'], h['module']) for h in PAPER_MAIN if keep(h['file'])]
    out += [('paper_extended', h['file'], h['module']) for h in PAPER_EXTENDED if keep(h['file'])]
    out += [('supplementary', h['file'], h['module']) for h in SUPPLEMENTARY if keep(h['file'])]
    for g, rows in DIAGNOSTICS.items():
        out += [(g, r['file'], r['module']) for r in rows if profile_full or r['file'] not in FULL_ONLY]
    return out
