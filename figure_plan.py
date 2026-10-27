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
                 'order-free Shapley values in Fig6 and, per lever and pathway, in ED8.',
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
                 'Switch, S3 Improve) in the lever order and coloured by strategy; hollow bar Moderate, filled bar '
                 'Ambitious, large deep-green dot TL. The TL dots are Shapley values within the TL game (all nine '
                 'levers at their limit), so they include each lever\'s interactions at the limit; L5 (occupancy '
                 'density) interacts with L4 (extra space): both act on the floor area per dwelling.',
         source=['pathways/shapley.csv']),
    dict(id='Fig7', file='Fig7_uncertainty', width='double', module='figures.paper_main',
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
    # MODEL v4.3.0: exactly ten items in this order (outputs/data/ed_number_map.csv, ED_NUMBER_MAP below)
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
         source=['sensitivity/reference_carbon.csv']),
    dict(id='ED5', file='ED5_boundary_sensitivity', module='figures.sensitivity',
         title='Boundary definitions and allocation: cumulative LoE of AR and of AtP',
         source=['sensitivity/planetary_boundary.csv', 'aesa/results.json']),
    dict(id='ED6', file='ED6_mc_input_distributions', module='figures.montecarlo',
         title='Monte Carlo input distributions',
         source=['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv',
                 'montecarlo/carbon_factors_REF.csv', 'pathways/montecarlo_draws.csv']),
    dict(id='ED7', file='ED7_sobol', module='figures.montecarlo',
         title='Sobol indices of the Reference: embodied carbon and floor area 2026-2050',
         source=['montecarlo/sobol_REF.csv']),
    dict(id='ED8', file='ED8_shapley_attribution', module='figures.paper_extended',
         title='Shapley attribution (order-independent): reduction of cumulative embodied carbon 2026-2050 by lever, '
               'Moderate and Ambitious Pathway and TL',
         source=['pathways/shapley.csv', 'pathways/runs.csv']),
    dict(id='ED9', file='ED9_lever_annual', module='figures.pathways',
         title='Each lever alone: annual embodied carbon at Moderate, Ambitious and the Theoretical Limit',
         source=['pathways/lever_annual.csv', 'pathways/annual.csv']),
    dict(id='ED10', file='ED10_rollout_timing', module='figures.paper_extended',
         title='Roll-out timing (the Pathways by 2030, 2035, 2045): annual and cumulative carbon',
         source=['pathways/annual.csv', 'pathways/runs.csv']),
]

# MODEL v4.3.0: Extended Data numbering, MODEL v4.2.2 (the last release) -> MODEL v4.3.0 (old id, old file, new id, new
# file); new id None: no longer rendered; a new id SFn: moved to the Supplementary Figures; old id 'new' or a
# diagnostic id (Dxx): added to the Extended Data. Supersedes the interim v4.3.0 numbering of commit 402dc33.
ED_NUMBER_MAP = [('ED1', 'ED1_population_households_floor_area', 'ED1', 'ED1_population_households_floor_area'),
                 ('ED2', 'ED2_census_replacement_rates', 'SF3', 'SF3_census_replacement_rates'),
                 ('ED3', 'ED3_household_formation_size', 'ED2', 'ED2_household_formation_size'),
                 ('ED4', 'ED4_overbuild_absorption', 'SF5', 'SF5_overbuild_absorption'),
                 ('ED5', 'ED5_pathways_annual', None, None),
                 ('ED6', 'ED6_waterfalls_by_demand_band', None, None),
                 ('ED7', 'ED7_tl_shapley_indicators', None, None),
                 ('ED8', 'ED8_replacement_variants', 'ED3', 'ED3_replacement_variants'),
                 ('ED9', 'ED9_rollout_timing', 'ED10', 'ED10_rollout_timing'),
                 ('ED10', 'ED10_detailed_demand_bands', None, None),
                 ('D16', 'D16_one_at_a_time', 'ED4', 'ED4_one_at_a_time'),
                 ('D42', 'D42_pb_sensitivity', 'ED5', 'ED5_boundary_sensitivity'),
                 ('D38', 'D38_mc_input_distributions', 'ED6', 'ED6_mc_input_distributions'),
                 ('D20', 'D20_sobol', 'ED7', 'ED7_sobol'),
                 ('new', None, 'ED8', 'ED8_shapley_attribution'),
                 ('D31', 'D31_lever_annual', 'ED9', 'ED9_lever_annual')]


def write_ed_number_map():
    """MODEL v4.3.0: outputs/data/ed_number_map.csv from ED_NUMBER_MAP (old id, old file, new id, new file; empty =
    not rendered / newly added). Written by pathways.py with the deterministic outputs and by tools/ed_number_map.py."""
    import csv
    import layout
    path = layout.writing(layout.data('ed_number_map.csv', frozen=False))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['old_id', 'old_file', 'new_id', 'new_file', 'status'])
        for oid, ofile, nid, nfile in ED_NUMBER_MAP:
            st = ('added' if oid == 'new' else 'from the diagnostics' if oid.startswith('D') else
                  'no longer rendered' if nid is None else 'moved to Supplementary' if nid.startswith('SF') else
                  'unchanged' if oid == nid else 'renumbered')
            w.writerow(['' if oid == 'new' else oid, ofile or '', nid or '', nfile or '', st])
    return path

# MODEL v3.3.1: Extended Data beyond the ten allowed (Nature Cities) -> outputs/supplementary/
# MODEL v4.3.0: the Supplementary Figures, one continuous series in reading order (calibration -> validation -> the
# boundary method -> sensitivity -> Monte Carlo -> the TL dwellings); 'folder' only organises outputs/supplementary/
SUPPLEMENTARY = [
    dict(id='SF1', file='SF1_households', folder='calibration', module='figures.calibration',
         title='Households: the published and census-benchmarked series, household size against arrivals and '
               'households per consent', source=['figure_source/D02_households.json',
                                                 'figure_source/D04_household_formation.json']),
    dict(id='SF2', file='SF2_stock_vacancy', folder='calibration', module='figures.calibration',
         title='Vacancy, the stock identity, dwellings per year by component and the vacancy definition',
         source=['figure_source/D05_stock_and_vacancy.json', 'figure_source/D06_vacancy_definition.json']),
    dict(id='SF3', file='SF3_census_replacement_rates', folder='calibration', module='figures.paper_extended',
         title='Net replacement rates from census dwelling counts and the four variants',
         source=['baseline/stock_identity_history.csv', 'figure_source/D07_net_replacement_rate.json']),
    dict(id='SF4', file='SF4_dwelling_size', folder='calibration', module='figures.calibration',
         title='New-dwelling size: realised and occupied floor area, occupancy utilisation and consented size by '
               'typology', source=['figure_source/D08_dwelling_space.json', 'pathways/levers.json']),
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
    dict(id='SF9', file='SF9_budget_construction', folder='boundaries', module='figures.boundaries',
         title='The AR and AtP budgets 2026-2050: population modifier and components',
         source=['figure_source/D22_boundaries.json']),
    dict(id='SF10', file='SF10_prcc', folder='sensitivity', module='figures.sensitivity',
         title='Monte Carlo sensitivity: partial rank correlation of each input, Reference, Moderate Pathway and TL',
         source=['pathways/montecarlo_importance.csv']),
    dict(id='SF11', file='SF11_pathway_sensitivity', folder='sensitivity', module='figures.sensitivity',
         title='One at a time: cumulative embodied carbon 2026-2050 of the Moderate Pathway',
         source=['sensitivity/pathway_carbon.csv']),
    dict(id='SF12', file='SF12_lambda_sweep', folder='sensitivity', module='figures.paper_extended',
         title='Each lever from the Reference to Ambitious (lambda sweep) and its Theoretical Limit',
         source=['pathways/lambda_sweep.csv']),
    dict(id='SF13', file='SF13_hd_estimators', folder='sensitivity', module='figures.paper_extended',
         title='Harrell-Davis estimators of L5 and L8 with bootstrap intervals', source=['pathways/levers.json']),
    dict(id='SF14', file='SF14_mc_convergence', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo convergence of the 2026-2050 percentiles', source=['montecarlo/convergence_REF.csv']),
    dict(id='SF15', file='SF15_pathway_mc', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo: annual carbon of the Reference, the Pathways and TL (median, 5th-95th)',
         source=['pathways/montecarlo_annual.csv', 'pathways/montecarlo_summary.csv']),
    dict(id='SF16', file='SF16_conditional_tl', folder='montecarlo', module='figures.paper_extended',
         title='When does TL stay within AR? By population quintile and the population threshold',
         source=['pathways/montecarlo_conditional_tl.csv', 'pathways/montecarlo_conditional_tl.json']),
    dict(id='SF17', file='SF17_tl_dwellings', folder='pathways', module='figures.pathways',
         title='The Theoretical Limit: need, released dwellings, re-occupation and dwellings built per year',
         source=['pathways/reoccupation_log.csv']),
]
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
PB_FIGURES = ('Fig3_reference_boundaries', 'Fig4_pathways', 'Fig5_solution_space',
              'ED3_replacement_variants', 'ED10_rollout_timing', 'SF9_budget_construction')

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
