"""The figures of one registry, read by layout.figure (where a figure is written), the figures/ package
(what draws it), indexes.py (outputs/FIGURES.md) and the tests.

    outputs/paper_main/       Fig1-Fig7 (PAPER_MAIN)
    outputs/paper_extended/   the Extended Data ED1-ED9 (PAPER_EXTENDED) and the per-typology level table EDT1
    outputs/supplementary/    the Supplementary figures SF1-SF15 and table ST1 (SUPPLEMENTARY; at most ten Extended
                              Data items)
    outputs/diagnostics/      the figure audit records (DIAGNOSTICS is empty)

Every figure is drawn by a module of figures/ from the data files of outputs/data/ only (compute / draw
separation); `module` names it, `source` lists the data files it reads (relative to outputs/data/).
Figures are PNG only (runprofile.py: 600 dpi full, 200 dpi light).
"""
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
         # the caption follows the figure (a-c; the annual pathways are in Fig3a)
         caption='Sequential waterfalls of cumulative carbon 2026-2050 from the Reference, levers added in PAS 2080 '
                 'order: (a) L1 ... L9 at Moderate -> Moderate Pathway; (b) at Ambitious -> Ambitious Pathway; (c) TL1 '
                 '... TL9 cumulative -> Theoretical Limit. Each step is one bar coloured by strategy with its net change; '
                 'AR (solid) and AtP (dotted) budgets with their zones; order-free Shapley values in Fig6.',
         source=['pathways/annual.csv', 'pathways/waterfall.csv', 'pathways/waterfall_tl_from_reference.csv']),
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
    # nine items in this order (outputs/data/ed_number_map.csv, ED_NUMBER_MAP below)
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
                 'maintenance event timing L / n, and the rows that compare with superseded settings (their changes are in the note). '
                 'What each row changes compared with the Reference (numbered as the row labels): ',
         row_notes='ED4',
         source=['sensitivity/reference_carbon.csv']),
    dict(id='ED5', file='ED5_boundary_sensitivity', module='figures.sensitivity',
         title='Boundary definitions and allocation: cumulative LoE of AR and of AtP',
         caption='One-at-a-time ranges of the Reference cumulative level of exceedance 2026-2050 of (a) acquired '
                 'rights (AR) and (b) ability to pay (AtP): boundary definitions (carrying capacity, global impact, AR '
                 'base window), allocation, population and replacement. Not shown (kept in the data file): α = 1 (Hjalsted et al. SI tables) and the raw Stats '
                 'NZ 2024-base median population. What each row changes compared with the Reference (numbered as the row labels): ',
         row_notes='ED5',
         source=['sensitivity/planetary_boundary.csv', 'aesa/results.json']),
    dict(id='ED6', file='ED6_mc_input_distributions', module='figures.montecarlo',
         title='Monte Carlo input distributions',
         source=['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv',
                 'montecarlo/carbon_factors_REF.csv', 'pathways/montecarlo_draws.csv']),
    dict(id='ED7', file='ED7_sobol', module='figures.montecarlo',
         title='Sobol indices of the Reference: embodied carbon and floor area 2026-2050',
         source=['montecarlo/sobol_REF.csv']),
    # ED8 Shapley attribution dropped (it duplicated Fig6a / Fig6b); ED9, ED10 -> ED8, ED9
    dict(id='ED8', file='ED8_lever_annual', module='figures.pathways',
         title='Each lever alone: annual embodied carbon at Moderate, Ambitious and the Theoretical Limit',
         source=['pathways/lever_annual.csv', 'pathways/annual.csv']),
    dict(id='ED9', file='ED9_rollout_timing', module='figures.paper_extended',
         title='Roll-out timing (the Pathways by 2030, 2035, 2045): annual and cumulative carbon',
         source=['pathways/annual.csv', 'pathways/runs.csv']),
]

# Extended Data numbering, MODEL v4.3.0 -> the current numbering (old id, old file, new id, new file); new id None:
# not rendered. Written to outputs/data/ed_number_map.csv.
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
    pathways.py with the deterministic outputs (with the Supplementary map, write_sf_number_map)."""
    return _write_number_map('ed_number_map.csv', ED_NUMBER_MAP)


def write_sf_number_map():
    """outputs/data/sf_number_map.csv from SF_NUMBER_MAP (Supplementary Figures and Tables)."""
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

# Extended Data beyond the ten allowed (Nature Cities) -> outputs/supplementary/
# the Supplementary Figures, one continuous series in reading order (calibration -> validation -> the
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
         title='Annual floor area by demand group: 17-month and like-for-like zero completion lag',
         source=['diagnostics/lag_comparison_annual.csv', 'diagnostics/lag_comparison_summary.json']),
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
# Supplementary Tables (Markdown + CSV, outputs/supplementary/<folder>/)
SUPPLEMENTARY_TABLES = [dict(id='ST1', file='ST1_budget_construction', folder='boundaries', module='figures.boundaries',
                             title='The AR and AtP budgets: components, the budgets in 2025 and 2050 and the 2050 '
                                   'population modifier', source=['aesa/results.json',
                                                                           'figure_source/D22_boundaries.json'])]
# Supplementary numbering, MODEL v4.3.0 -> the current numbering (old id, old file, new id, new file)
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
# no separate diagnostic figures; every figure is a main, Extended Data or Supplementary figure
DIAGNOSTICS = {}
# figures drawn only in the full profile (their data exist only there)
FULL_ONLY = ('ED7_sobol',)

# Maintenance (B2, B4) drawn as its own layer: only in the band and stage breakdowns
MAINTENANCE_ALLOWED = ('Fig2_reference_carbon', 'Fig3_reference_boundaries')
# every figure with a planetary boundary on its axes (zones required; AtP dotted)
# (ED10 -> ED9; SF9 budget construction is the Supplementary Table ST1, no axes)
PB_FIGURES = ('Fig3_reference_boundaries', 'Fig4_pathways', 'Fig5_solution_space',
              'ED3_replacement_variants', 'ED9_rollout_timing')

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
