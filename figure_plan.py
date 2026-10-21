"""The figures of MODEL v3.0.0: one registry, read by layout.figure (where a figure is written), the figures/ package
(what draws it), indexes.py (outputs/FIGURES.md) and the tests.

    outputs/paper_main/       Fig1-Fig8 (PAPER_MAIN)
    outputs/paper_extended/   the Extended Data ED1-ED10 (PAPER_EXTENDED) and the per-typology level table
    outputs/supplementary/    further figures (SUPPLEMENTARY; MODEL v3.3.1: at most ten Extended Data items)
    outputs/diagnostics/<group>/  calibration, validation, boundaries, pathways, montecarlo, sensitivity (DIAGNOSTICS)

Every figure is drawn by a module of figures/ from the data files of outputs/data/ only (compute / draw
separation); `module` names it, `source` lists the data files it reads (relative to outputs/data/).
Figures are PNG only (runprofile.py: 600 dpi full, 200 dpi light; MODEL v3.3.1). Figure ids of MODEL v2.1 that are not carried forward are listed in
RETIRED with the reason (docs/FIGURE_PLAN_v3.md).
"""
PAPER_MAIN = [
    dict(id='Fig1', file='Fig1_floor_area', width='double', module='figures.paper_main',
         title='Floor area: history and projection by demand band',
         caption='Floor area built per year by demand band: history as census-interval means (columns), the Reference '
                 'projection annually from 2026 (2026 observed). Positive bands stacked up from zero, negative bands '
                 '(overbuild absorbed, unconsented additions) down from zero; the black line is the floor area built '
                 '(in scope). 2026 overbuild: observed 2026 building above need, fading from 2027 and absorbed by 2035.',
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
                 '95% interval (2.5th-97.5th percentile of the cumulative carbon) and the AR and AtP budgets, and the '
                 'committed emissions after 2050: C1-C4 and B2/B4 after 2050, the latter a range (lower = 2050 factors '
                 'held, upper = 2025 factors).',
         source=['aesa/annual.csv', 'montecarlo/annual_REF.csv', 'montecarlo/draws_REF.csv', 'baseline/projection.json']),
    dict(id='Fig4', file='Fig4_pathways', width='double', module='figures.paper_main',
         title='The Pathways: annual carbon and the sequential waterfalls',
         caption='(a) Annual carbon 2026-2050 of the Reference, the Moderate and Ambitious Pathway, the Theoretical Limit '
                 'and the PAS 2080 strategies S1-S3 (thin; Moderate solid, Ambitious dotted) against AR and AtP. (b-d) '
                 'Sequential waterfalls of cumulative carbon 2026-2050 from the Reference, levers added in PAS 2080 '
                 'order: (b) L1 ... L9 at Moderate -> Moderate Pathway; (c) at Ambitious -> Ambitious Pathway; (d) TL1 '
                 '... TL9 cumulative -> Theoretical Limit. Each step is one bar coloured by strategy with its net change; '
                 'order-free Shapley values in Fig7; split by demand band in ED6.',
         source=['pathways/annual.csv', 'pathways/waterfall.csv', 'pathways/waterfall_tl_from_reference.csv']),
    dict(id='Fig5', file='Fig5_reduction_by_demand', width='double', module='figures.paper_main',
         title='What the reduction consists of',
         caption='Reduction of cumulative carbon 2026-2050 against the Reference for the Moderate Pathway, the Ambitious '
                 'Pathway and the Theoretical Limit, by demand band (Reference - run, per band); column height = total '
                 'reduction. Negative band reductions (outlined, hanging down from the top of the positive stack): the '
                 'credits from re-used dwellings (overbuild absorbed, unconsented additions) shrink when new dwellings '
                 'are smaller, because each re-used dwelling is valued at the new-dwelling size it displaces.',
         source=['pathways/bands.csv', 'pathways/runs.csv']),
    dict(id='Fig6', file='Fig6_solution_space', width='double', module='figures.paper_main',
         title='The solution space',
         caption='Cumulative level of exceedance of AR over uniform cuts of 2027-2050 floor area (x) and of carbon per m2 '
                 '(y) (after Horup et al. 2025), axes -5% to 100%, with S1-S3 (Moderate filled, Ambitious hollow), the '
                 'Moderate / Ambitious Pathway and the Theoretical Limit; analytic LoE AR contours and the exact AR line. '
                 'Right: the LoE AR ruler (log) with the Reference, the Pathways, TL, AR = 1, the plane floor (the 2026 '
                 'observed cohort alone) and AtP.',
         source=['pathways/solution_space.csv', 'pathways/backcast.json', 'pathways/runs.csv']),
    dict(id='Fig7', file='Fig7_shapley_levers', width='double', module='figures.paper_main',
         title='What each lever removes',
         caption='Shapley values within each combined game (Reference -> Moderate Pathway, -> Ambitious Pathway, -> TL; '
                 'exact, 512 subsets) on cumulative carbon 2026-2050: rows grouped by PAS 2080 strategy (S1 Avoid, S2 '
                 'Switch, S3 Improve) in the lever order and coloured by strategy; hollow bar Moderate, filled bar '
                 'Ambitious, large deep-green dot TL. The TL dots are Shapley values within the TL game (all nine '
                 'levers at their limit), so they include each lever\'s interactions at the limit; L5 (occupancy '
                 'density) interacts with L4 (extra space): both act on the floor area per dwelling.',
         source=['pathways/shapley.csv']),
    dict(id='Fig8', file='Fig8_uncertainty', width='double', module='figures.paper_main',
         title='Uncertainty',
         caption='(a) One-at-a-time ranges of the Reference cumulative LoE AR 2026-2050, each input at its low and high '
                 'end per its definition (population rows move the budgets with the path; AR base-window rows move the '
                 'AR budget only); not additive, not a joint interval. (b) Theoretical Limit: cumulative LoE AR against '
                 'the 2050 New Zealand population across the Monte Carlo draws, LoE = 1, and the population at which '
                 'P(LoE AR <= 1) = 50% (Firth logistic; bootstrap 95% CI).',
         source=['sensitivity/tornado.csv', 'sensitivity/planetary_boundary.csv', 'pathways/montecarlo_draws.csv',
                 'pathways/montecarlo_conditional_tl.json', 'baseline/scenarios.json', 'aesa/results.json']),
]

PAPER_EXTENDED = [
    dict(id='ED1', file='ED1_population_households_floor_area', module='figures.paper_extended',
         title='Population, households and floor area: history and projection (Monte Carlo 5th-95th)',
         source=['figure_source/projection_paths.json', 'figure_source/D02_households.json']),
    dict(id='ED2', file='ED2_census_replacement_rates', module='figures.paper_extended',
         title='Net replacement rates from census dwelling counts and the four variants',
         source=['baseline/stock_identity_history.csv', 'figure_source/D07_net_replacement_rate.json']),
    dict(id='ED3', file='ED3_household_formation_size', module='figures.paper_extended',
         title='Household formation and household size', source=['baseline/household_formation_history.csv',
                                                                 'figure_source/D03_household_size.json']),
    dict(id='ED4', file='ED4_overbuild_absorption', module='figures.paper_extended',
         title='Overbuild absorption: the Reference path and its timing sensitivity',
         source=['baseline/overbuild_absorption_log.csv', 'baseline/sensitivity_annual_carbon.csv']),
    dict(id='ED5', file='ED5_pathways_annual', module='figures.paper_extended',
         title='Pathways against the boundaries (annual)',
         source=['pathways/annual.csv', 'pathways/runs.csv']),
    dict(id='ED6', file='ED6_waterfalls_by_demand_band', module='figures.paper_extended',
         title='Sequential waterfalls by demand band, Moderate and Ambitious (PAS 2080 order)',
         source=['pathways/waterfall.csv']),
    dict(id='ED7', file='ED7_single_levers', module='figures.paper_extended',
         title='Single-lever runs at Moderate, Ambitious and TL', source=['pathways/runs.csv']),
    dict(id='ED8', file='ED8_tl_shapley_indicators', module='figures.paper_extended',
         title='TL: Shapley values from the Moderate Pathway and human-terms indicators',
         source=['pathways/shapley.csv', 'pathways/theoretical_limit.json']),
    dict(id='ED9', file='ED9_replacement_variants', module='figures.paper_extended',
         title='Low, High and Very High replacement: the Reference, the Pathways and TL',
         source=['sensitivity/replacement_variants.csv', 'pathways/annual.csv']),
    dict(id='ED10', file='ED10_rollout_timing', module='figures.paper_extended',
         title='Roll-out timing (the Pathways by 2030, 2035, 2045)', source=['pathways/annual.csv', 'pathways/runs.csv']),
    # MODEL v4.2: the detailed demand bands behind the six display bands (eleven ED items: one over the Nature Cities
    # cap of ten; the author chooses which to move to the supplementary set)
    dict(id='ED11', file='ED11_detailed_demand_bands', module='figures.paper_extended',
         title='Detailed demand bands: floor area (Fig1) and Reference carbon (Fig2a)',
         source=['baseline/bands_history.csv', 'baseline/bands_annual.csv', 'baseline/annual.csv',
                 'baseline/annual_by_stage.csv', 'baseline/overbuild_2026.json', 'bands_display_map.csv']),
]

# MODEL v3.3.1: Extended Data beyond the ten allowed (Nature Cities) -> outputs/supplementary/
SUPPLEMENTARY = [
    dict(id='SF1', file='SF1_model_schematic', module='figures.paper_main',
         title='The model: conversion chain, levers by PAS 2080 strategy, ambition ladder (Fig1 in MODEL v3.3.1)',
         source=['pathways/levers.json']),
    dict(id='SF2', file='SF2_mc_scatter_population', module='figures.paper_extended',
         title='Monte Carlo: LoE against the population rank', source=['pathways/montecarlo_draws.csv']),
    dict(id='SF3', file='SF3_conditional_tl', module='figures.paper_extended',
         title='When does TL stay within AR? By population quintile and the population threshold',
         source=['pathways/montecarlo_conditional_tl.csv', 'pathways/montecarlo_conditional_tl.json']),
    dict(id='SF4', file='SF4_lambda_sweep', module='figures.paper_extended',
         title='Lambda-sweep of each lever (Reference 0, Moderate 0.5, Ambitious 1) and the TL point',
         source=['pathways/lambda_sweep.csv']),
    dict(id='SF5', file='SF5_hd_estimators', module='figures.paper_extended',
         title='Harrell-Davis estimators of L5 and L8 with bootstrap intervals', source=['pathways/levers.json']),
    dict(id='SF6', file='SF6_consent_sizes', module='figures.paper_extended',
         title='L4: mean consented new-dwelling size by typology, 1990-2025, with the minima',
         source=['pathways/levers.json']),
]
# tables of the Extended Data (Markdown + CSV, outputs/paper_extended/)
EXTENDED_TABLES = [dict(id='EDT1', file='EDT1_levels_by_typology', title='Lever levels by typology: Moderate, '
                        'Ambitious and TL', source=['pathways/levers.json'])]

_d = lambda file, title, module, source: dict(file=file, title=title, module=module, source=source)
DIAGNOSTICS = {
    'calibration': [
        _d('D01_population', 'Population, history and projection (median, 5th-95th)', 'figures.calibration',
           ['figure_source/D01_population.json']),
        _d('D02_households', 'Households: census-benchmarked history and projection', 'figures.calibration',
           ['figure_source/D02_households.json']),
        _d('D03_household_size', 'Household size and population vs household growth', 'figures.calibration',
           ['figure_source/D03_household_size.json']),
        _d('D04_household_formation', 'Household size vs arrivals; households per consent; new households by source',
           'figures.calibration', ['figure_source/D04_household_formation.json']),
        _d('D05_stock_and_vacancy', 'Vacancy, stock and dwellings per year by component', 'figures.calibration',
           ['figure_source/D05_stock_and_vacancy.json']),
        _d('D06_vacancy_definition', 'Why empty-only vacancy is used (appendix)', 'figures.calibration',
           ['figure_source/D06_vacancy_definition.json']),
        _d('D07_net_replacement_rate', 'Net replacement rate: census intervals and the four variants (Reference to 2075)',
           'figures.validation', ['figure_source/D07_net_replacement_rate.json']),
        _d('D08_dwelling_space', 'Realised vs occupied floor area per new dwelling; occupancy utilisation',
           'figures.calibration', ['figure_source/D08_dwelling_space.json']),
        _d('D09_cumulative_floor_area', 'Cumulative floor area 1991-2050 with the population 5th-95th band',
           'figures.calibration', ['figure_source/D09_cumulative_floor_area.json']),
        _d('D35_overbuild_absorption', 'The 2026 overbuild in the Reference: excess, surplus, payback, implied vacancy',
           'figures.calibration', ['baseline/overbuild_absorption_log.csv']),
    ],
    'validation': [
        _d('D10_floor_area_bridge', 'Floor area 2026-2050 by demand band, Low / Reference / High / Very High (waterfall)',
           'figures.validation', ['figure_source/D10_floor_area_bridge.json']),
        _d('D12_conversion_chain', 'Population -> households -> dwellings -> floor area -> carbon (indices)',
           'figures.validation', ['figure_source/D12_conversion_chain.json']),
        _d('D13_carbon_by_material', 'Embodied carbon by material, annual and cumulative', 'figures.calibration',
           ['figure_source/D13_carbon_by_material.json']),
        _d('D14_hindcast', 'Rolling-origin hindcast of dwellings built and the 2026 out-of-sample check',
           'figures.validation', ['figure_source/D14_hindcast.json', 'baseline/validation.json']),
        _d('D15_reality_checks', 'Projection vs the 1991-2025 range and the observed -> model handover',
           'figures.validation', ['figure_source/D15_reality_checks.json']),
        _d('D43_historical_market_balance', 'Historical and projected floor area: demand, net replacement and unallocated balance',
           'figures.market_balance', ['diagnostics/market_balance_history_projection.csv']),
        _d('D44_completion_lag_comparison', 'Annual floor area by broad demand group: zero- and 17-month completion lag',
           'figures.market_balance', ['diagnostics/lag_comparison_annual.csv']),
    ],
    'boundaries': [
        _d('D18_aesa_sensitivity', 'All AESA sensitivity rows: cumulative LoE AR and AtP', 'figures.boundaries',
           ['figure_source/D18_aesa_sensitivity.json']),
        _d('D21_fan_and_boundaries', 'Monte Carlo fan of carbon, the AR base window and the boundary bands',
           'figures.boundaries', ['figure_source/D21_fan_and_boundaries.json']),
        _d('D22_boundaries', 'Boundaries AR and AtP 2025-2050, population modifier, components', 'figures.boundaries',
           ['figure_source/D22_boundaries.json']),
        _d('D23_annual_loe', 'Annual level of exceedance by variant with Monte Carlo bands', 'figures.boundaries',
           ['figure_source/D23_annual_loe.json']),
        _d('D24_headroom', 'Intensity, floor area and carbon per dwelling that would fit each boundary',
           'figures.boundaries', ['figure_source/D24_headroom.json']),
        _d('D25_annual_carbon_by_band', 'Annual carbon by demand band against the boundaries', 'figures.boundaries',
           ['figure_source/D25_annual_carbon_by_band.json']),
        _d('D26_cumulative_carbon_by_band', 'Cumulative carbon by demand band against the cumulative boundaries',
           'figures.boundaries', ['figure_source/D26_cumulative_carbon_by_band.json']),
        _d('D27_variants_vs_boundaries', 'Annual and cumulative carbon by variant against the boundaries',
           'figures.boundaries', ['figure_source/D27_variants_vs_boundaries.json']),
    ],
    'pathways': [
        _d('D28_pathways_annual', 'Annual carbon of the Reference, S1-S3, the Pathways and TL against the boundaries',
           'figures.pathways', ['pathways/annual.csv', 'aesa/annual.csv']),
        _d('D29_ramps', 'The adoption path and each lever\'s native parameter at Moderate, Ambitious and TL',
           'figures.pathways', ['pathways/levers.json']),
        _d('D31_lever_annual', 'Annual carbon of each lever alone at Moderate, Ambitious and TL', 'figures.pathways',
           ['pathways/lever_annual.csv']),
        _d('D32_tl_staircase', 'Reference -> Pathways -> TL: cumulative LoE and the human terms', 'figures.pathways',
           ['pathways/runs.csv', 'pathways/theoretical_limit.json']),
        _d('D33_ordering_checks', 'Ordering Reference >= Moderate >= Ambitious >= TL: carbon of each single-lever run',
           'figures.pathways', ['pathways/ordering_checks.json', 'pathways/lever_annual.csv']),
        _d('D34_tl_dwellings', 'TL: need, release, re-occupation and dwellings built per year (log)', 'figures.pathways',
           ['pathways/reoccupation_log.csv']),
        _d('D36_pathway_bands', 'Cumulative carbon by demand band of every pathway and TL', 'figures.pathways',
           ['pathways/bands.csv']),
    ],
    'montecarlo': [
        _d('D20_sobol', 'Sobol indices of the Reference (full profile only)', 'figures.montecarlo',
           ['montecarlo/sobol_REF.csv']),
        _d('D37_mc_convergence', 'Monte Carlo convergence of the 2026-2050 percentiles', 'figures.montecarlo',
           ['montecarlo/convergence_REF.csv']),
        _d('D38_mc_input_distributions', 'Monte Carlo input distributions (sample and quantiles; the resulting A1-A3 '
           'factors by typology)', 'figures.montecarlo',
           ['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv', 'montecarlo/carbon_factors_REF.csv']),
        _d('D39_pathway_mc', 'Pathway Monte Carlo: Reference, Moderate / Ambitious Pathway, TL', 'figures.montecarlo',
           ['pathways/montecarlo_summary.csv', 'pathways/montecarlo_annual.csv']),
    ],
    'sensitivity': [
        _d('D16_one_at_a_time', 'Every one-at-a-time row of the Reference carbon', 'figures.sensitivity',
           ['sensitivity/reference_carbon.csv']),
        _d('D17_sensitivity_paths', 'Annual carbon of every sensitivity row', 'figures.sensitivity',
           ['baseline/sensitivity_annual_carbon.csv']),
        _d('D19_variants', 'Annual and cumulative floor area and carbon by projection variant', 'figures.validation',
           ['figure_source/D19_variants.json', 'montecarlo/annual_REF.csv']),
        _d('D40_src_prcc', 'Monte Carlo SRC and PRCC with bootstrap intervals', 'figures.sensitivity',
           ['pathways/montecarlo_importance.csv']),
        _d('D41_pathway_sensitivity', 'Moderate Pathway: one-at-a-time rows', 'figures.sensitivity',
           ['sensitivity/pathway_carbon.csv']),
        _d('D42_pb_sensitivity', 'Planetary-boundary rows: cumulative LoE AR and AtP', 'figures.sensitivity',
           ['sensitivity/planetary_boundary.csv']),
    ],
}
# figures drawn only in the full profile (their data exist only there)
FULL_ONLY = ('D20_sobol',)

# Maintenance (B2, B4) drawn as its own layer: only in the band and stage breakdowns
MAINTENANCE_ALLOWED = ('Fig2_reference_carbon', 'Fig3_reference_boundaries', 'Fig5_reduction_by_demand',
                       'ED6_waterfalls_by_demand_band',
                       'D25_annual_carbon_by_band', 'D26_cumulative_carbon_by_band', 'D32_tl_staircase',
                       'D36_pathway_bands')
# every figure with a planetary boundary on its axes (zones required; AtP dotted)
PB_FIGURES = ('Fig3_reference_boundaries', 'Fig4_pathways', 'Fig6_solution_space',
              'ED5_pathways_annual', 'ED6_waterfalls_by_demand_band', 'ED9_replacement_variants', 'ED10_rollout_timing',
              'D21_fan_and_boundaries', 'D22_boundaries', 'D23_annual_loe',
              'D24_headroom', 'D25_annual_carbon_by_band', 'D26_cumulative_carbon_by_band',
              'D27_variants_vs_boundaries', 'D28_pathways_annual')

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
}


def all_figures(profile_full=True):
    """[(group, file id, module)] of every figure (diagnostics of FULL_ONLY only in the full profile)."""
    out = [('paper_main', h['file'], h['module']) for h in PAPER_MAIN]
    out += [('paper_extended', h['file'], h['module']) for h in PAPER_EXTENDED]
    out += [('supplementary', h['file'], h['module']) for h in SUPPLEMENTARY]
    for g, rows in DIAGNOSTICS.items():
        out += [(g, r['file'], r['module']) for r in rows if profile_full or r['file'] not in FULL_ONLY]
    return out
