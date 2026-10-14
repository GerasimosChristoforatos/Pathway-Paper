"""The figures of MODEL v3.0.0: one registry, read by layout.figure (where a figure is written), the figures/ package
(what draws it), indexes.py (outputs/FIGURES.md) and the tests.

    outputs/paper_main/       Fig1-Fig8 (PAPER_MAIN)
    outputs/paper_extended/   the Extended Data (PAPER_EXTENDED) and the per-typology level table
    outputs/diagnostics/<group>/  calibration, validation, boundaries, pathways, montecarlo, sensitivity (DIAGNOSTICS)

Every figure is drawn by a module of figures/ from the data files of outputs/data/ only (compute / draw
separation); `module` names it, `source` lists the data files it reads (relative to outputs/data/).
Formats follow the run profile (runprofile.py). Figure ids of MODEL v2.1 that are not carried forward are listed in
RETIRED with the reason (docs/FIGURE_PLAN_v3.md).
"""
PAPER_MAIN = [
    dict(id='Fig1', file='Fig1_floor_area', width='double', module='figures.paper_main',
         title='Floor area: history and projection by demand band',
         caption='Floor area built per year, history (census intervals) and the Reference projection 2026-2050, by '
                 'demand band: positive bands stacked up from zero, negative bands (overbuild absorbed, unconsented '
                 'additions) down from zero, the net a black line.',
         source=['baseline/bands_history.csv', 'baseline/bands_annual.csv', 'baseline/annual.csv']),
    dict(id='Fig2', file='Fig2_reference_carbon', width='double', module='figures.paper_main',
         title='Embodied carbon of the Reference',
         caption='Annual embodied carbon of the Reference 2026-2050 by (a) demand band, (b) material and (c) life-cycle '
                 'stage; materials and stages are never negative.',
         source=['baseline/bands_annual.csv', 'baseline/annual_by_material.csv', 'baseline/annual_by_stage.csv']),
    dict(id='Fig3', file='Fig3_reference_boundaries', width='double', module='figures.paper_main',
         title='The Reference against the planetary boundaries',
         caption='(a) Annual carbon, Monte Carlo median with 50% and 90% bands, against the acquired-rights (AR) and '
                 'ability-to-pay (AtP) boundaries and their zones; (b) cumulative carbon 2026-2050 with the committed '
                 'range after 2050 as a hollow segment on top, the AR and AtP budgets as ticks, and three thin 100% '
                 'share bars by demand band, material and stage.',
         source=['aesa/annual.csv', 'montecarlo/annual_REF.csv', 'baseline/projection.json',
                 'baseline/bands_annual.csv', 'baseline/annual_by_material.csv', 'baseline/annual_by_stage.csv']),
    dict(id='Fig4', file='Fig4_pathways_annual', width='double', module='figures.paper_main',
         title='Pathways against the boundaries',
         caption='Annual carbon of the Reference, P1-P5 and TL against AR and AtP: Moderate solid bold, Ambitious the '
                 'same colour thin dotted.',
         source=['pathways/annual.csv', 'aesa/annual.csv']),
    dict(id='Fig5', file='Fig5_waterfall', width='double', module='figures.paper_main',
         title='From the Reference to the theoretical limit',
         caption='Cumulative carbon 2026-2050 by demand band along the sequential path Reference -> P1 ... P4 (= P5 '
                 'Moderate) -> TL1 ... TL9 (= TL); negative bands outlined, hanging from the top of the positive stack; '
                 'each bar ends at its net total.',
         source=['pathways/waterfall.csv']),
    dict(id='Fig6', file='Fig6_solution_space', width='double', module='figures.paper_main',
         title='The solution space',
         caption='Cumulative level of exceedance of AR and AtP over uniform cuts of 2027-2050 floor area and of carbon '
                 'per m2 (after Horup et al. 2025), with P1-P5 (Moderate filled, Ambitious hollow) and TL.',
         source=['pathways/solution_space.csv', 'pathways/backcast.json']),
    dict(id='Fig7', file='Fig7_tornado', width='double', module='figures.paper_main',
         title='What moves the Reference',
         caption='One-at-a-time ranges of eight inputs, the overbuild absorption timing among them: (a) cumulative '
                 'carbon 2026-2050, (b) cumulative LoE AR and AtP. Not additive, not a joint interval.',
         source=['sensitivity/tornado.csv']),
    dict(id='Fig8', file='Fig8_shapley_levers', width='double', module='figures.paper_main',
         title='What each lever removes',
         caption='Exact Shapley value of each lever (512 subsets) on cumulative carbon 2026-2050, from the Reference: '
                 'hollow bar Moderate, filled bar Ambitious, large deep-green dot TL; sorted by Ambitious.',
         source=['pathways/shapley.csv']),
]

PAPER_EXTENDED = [
    dict(id='ED1', file='ED1_census_replacement_rates', module='figures.paper_extended',
         title='Net replacement rates from census dwelling counts', source=['baseline/stock_identity_history.csv',
                                                                            'figure_source/D07_net_replacement_rate.json']),
    dict(id='ED2', file='ED2_household_formation_size', module='figures.paper_extended',
         title='Household formation and household size', source=['baseline/household_formation_history.csv',
                                                                 'figure_source/D03_household_size.json']),
    dict(id='ED3', file='ED3_cumulative_households_population_floor_area', module='figures.paper_extended',
         title='Cumulative households, population and floor area', source=['figure_source/projection_paths.json']),
    dict(id='ED4', file='ED4_mc_scatter_population', module='figures.paper_extended',
         title='Monte Carlo: LoE against the population rank', source=['pathways/montecarlo_draws.csv']),
    dict(id='ED5', file='ED5_conditional_tl', module='figures.paper_extended',
         title='When does TL stay within AR? (Firth logistic regression)',
         source=['pathways/montecarlo_conditional_tl.csv', 'pathways/montecarlo_conditional_tl.json']),
    dict(id='ED6', file='ED6_single_levers', module='figures.paper_extended',
         title='Single-lever runs at Moderate, Ambitious and TL', source=['pathways/runs.csv']),
    dict(id='ED7', file='ED7_waterfall_ambitious', module='figures.paper_extended',
         title='Waterfall at Ambitious', source=['pathways/waterfall.csv']),
    dict(id='ED8', file='ED8_tl_shapley_indicators', module='figures.paper_extended',
         title='TL: Shapley values from P5 Moderate and human-terms indicators',
         source=['pathways/shapley.csv', 'pathways/theoretical_limit.json']),
    dict(id='ED9', file='ED9_rollout_timing', module='figures.paper_extended',
         title='Roll-out timing (P5 by 2030, 2035, 2045)', source=['pathways/annual.csv', 'pathways/runs.csv']),
    dict(id='ED10', file='ED10_lambda_sweep', module='figures.paper_extended',
         title='Lambda-sweep of each lever (Reference 0, Moderate 0.5, Ambitious 1) and the TL point',
         source=['pathways/lambda_sweep.csv']),
    dict(id='ED11', file='ED11_hd_estimators', module='figures.paper_extended',
         title='Harrell-Davis estimators of L2 and L6 with bootstrap intervals', source=['pathways/levers.json']),
    dict(id='ED12', file='ED12_consent_sizes', module='figures.paper_extended',
         title='L1: mean consented new-dwelling size by typology, 1990-2025, with the minima',
         source=['pathways/levers.json']),
    dict(id='ED13', file='ED13_replacement_variants', module='figures.paper_extended',
         title='Low and High replacement: the Reference, P5 and TL', source=['sensitivity/replacement_variants.csv',
                                                                             'pathways/annual.csv']),
    dict(id='ED14', file='ED14_overbuild_absorption', module='figures.paper_extended',
         title='Overbuild absorption: the Reference path and its timing sensitivity',
         source=['baseline/overbuild_absorption_log.csv', 'baseline/sensitivity_annual_carbon.csv']),
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
        _d('D07_net_replacement_rate', 'Net replacement rate: census intervals and the three variants',
           'figures.validation', ['figure_source/D07_net_replacement_rate.json']),
        _d('D08_dwelling_space', 'Realised vs occupied floor area per new dwelling; occupancy utilisation',
           'figures.calibration', ['figure_source/D08_dwelling_space.json']),
        _d('D09_cumulative_floor_area', 'Cumulative floor area 1991-2050 with the population 5th-95th band',
           'figures.calibration', ['figure_source/D09_cumulative_floor_area.json']),
        _d('D35_overbuild_absorption', 'The 2026 overbuild in the Reference: excess, surplus, payback, implied vacancy',
           'figures.calibration', ['baseline/overbuild_absorption_log.csv']),
    ],
    'validation': [
        _d('D10_floor_area_bridge', 'Floor area 2026-2050 by demand band, Low / Reference / High (waterfall)',
           'figures.validation', ['figure_source/D10_floor_area_bridge.json']),
        _d('D12_conversion_chain', 'Population -> households -> dwellings -> floor area -> carbon (indices)',
           'figures.validation', ['figure_source/D12_conversion_chain.json']),
        _d('D13_carbon_by_material', 'Embodied carbon by material, annual and cumulative', 'figures.calibration',
           ['figure_source/D13_carbon_by_material.json']),
        _d('D14_hindcast', 'Rolling-origin hindcast of dwellings built and the 2026 out-of-sample check',
           'figures.validation', ['figure_source/D14_hindcast.json', 'baseline/validation.json']),
        _d('D15_reality_checks', 'Projection vs the 1991-2025 range and the 2026 -> 2027 handover',
           'figures.validation', ['figure_source/D15_reality_checks.json']),
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
        _d('D28_pathways_annual', 'Annual carbon of the Reference, P1-P5 and TL against the boundaries',
           'figures.pathways', ['pathways/annual.csv', 'aesa/annual.csv']),
        _d('D29_ramps', 'The adoption path and each lever\'s native parameter at Moderate, Ambitious and TL',
           'figures.pathways', ['pathways/levers.json']),
        _d('D31_lever_annual', 'Annual carbon of each lever alone at Moderate, Ambitious and TL', 'figures.pathways',
           ['pathways/lever_annual.csv']),
        _d('D32_tl_staircase', 'Reference -> P5 -> TL: cumulative LoE and the human terms', 'figures.pathways',
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
        _d('D38_mc_input_distributions', 'Monte Carlo input distributions (sample and quantiles)', 'figures.montecarlo',
           ['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv']),
        _d('D39_pathway_mc', 'Pathway Monte Carlo: Reference, P5 Moderate / Ambitious, TL', 'figures.montecarlo',
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
        _d('D41_p5_sensitivity', 'P5 Moderate: one-at-a-time rows', 'figures.sensitivity', ['sensitivity/p5_carbon.csv']),
        _d('D42_pb_sensitivity', 'Planetary-boundary rows: cumulative LoE AR and AtP', 'figures.sensitivity',
           ['sensitivity/planetary_boundary.csv']),
    ],
}
# figures drawn only in the full profile (their data exist only there)
FULL_ONLY = ('D20_sobol',)

# Maintenance (B2, B4) drawn as its own layer: only in the band and stage breakdowns
MAINTENANCE_ALLOWED = ('Fig2_reference_carbon', 'Fig3_reference_boundaries', 'Fig5_waterfall', 'ED7_waterfall_ambitious',
                       'D25_annual_carbon_by_band', 'D26_cumulative_carbon_by_band', 'D32_tl_staircase',
                       'D36_pathway_bands')
# every figure with a planetary boundary on its axes (zones required; AtP dotted)
PB_FIGURES = ('Fig3_reference_boundaries', 'Fig4_pathways_annual', 'Fig5_waterfall', 'Fig6_solution_space',
              'ED7_waterfall_ambitious', 'ED9_rollout_timing',
              'ED13_replacement_variants', 'D21_fan_and_boundaries', 'D22_boundaries', 'D23_annual_loe',
              'D24_headroom', 'D25_annual_carbon_by_band', 'D26_cumulative_carbon_by_band',
              'D27_variants_vs_boundaries', 'D28_pathways_annual')

RETIRED = {
    'outputs/paper/ (Fig1-Fig6 of MODEL v2.1.2)': 'outputs/paper_main/ Fig1-Fig8 (new set)',
    'outputs/extended_data/ (ED1-ED13)': 'outputs/paper_extended/ ED1-ED14',
    'outputs/key_figures/ (K1-K6)': 'retired: their content is in Fig1-Fig8',
    'D30_l6_estimator': 'ED11 (L2 and L6 estimators)',
    'D11_floor_area_bridge_split': 'D10 (MODEL v3.0.0 splits demolition replacement and unconsented additions in '
                                   'every band set, so the appendix bridge equals D10)',
    'Fig1_model_schematic': 'retired (schematic; the levers are in Table 1)',
}


def all_figures(profile_full=True):
    """[(group, file id, module)] of every figure (diagnostics of FULL_ONLY only in the full profile)."""
    out = [('paper_main', h['file'], h['module']) for h in PAPER_MAIN]
    out += [('paper_extended', h['file'], h['module']) for h in PAPER_EXTENDED]
    for g, rows in DIAGNOSTICS.items():
        out += [(g, r['file'], r['module']) for r in rows if profile_full or r['file'] not in FULL_ONLY]
    return out
