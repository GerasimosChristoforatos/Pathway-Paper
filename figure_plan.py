"""The figures of one registry, read by layout.figure (where a figure is written), the figures/ package
(what draws it), indexes.py (outputs/FIGURES.md) and the tests.

    outputs/paper_main/       Fig1-Fig7 (PAPER_MAIN)
    outputs/paper_extended/   the Extended Data ED1-ED9 (PAPER_EXTENDED) and the per-typology level table EDT1 (Extended Data Table 1)
    outputs/supplementary/    the Supplementary figures SF1-SF16 and table ST8 (SUPPLEMENTARY; at most ten Extended
                              Data items)
    outputs/diagnostics/      the figure audit records (DIAGNOSTICS is empty)

Every figure is drawn by a module of figures/ from the data files of outputs/data/ only (compute / draw
separation); `module` names it, `source` lists the data files it reads (relative to outputs/data/).
Figures are PNG only (runprofile.py: 600 dpi full, 200 dpi light).
"""
# caption sentence filled from the data when FIGURES.md is written (render_caption): no value typed here
SURPLUS_TOKEN = '<<surplus_absorption>>'


def render_caption(cap):
    """A caption with its data tokens filled: the absorption window (baseline/overbuild_2026.json) and the ED8 row
    'absorbed by 2030 / by 2045' (sensitivity/reference_carbon.csv)."""
    if not cap or SURPLUS_TOKEN not in cap:
        return cap
    import json
    import pandas as pd
    import layout
    ob = json.load(open(layout.data('baseline/overbuild_2026.json')))
    a, b = int(max(ob['pipeline_years'])) + 1, int(ob['absorption_end'])
    r = pd.read_csv(layout.data('sensitivity/reference_carbon.csv'))
    r = r[r['row'] == '2026 overbuild absorbed by 2030 / by 2045'].set_index('side')['change_pct']
    sentence = (f'Building runs below need in {a}-{b} while the 2024-{str(a - 1)[-2:]} surplus is absorbed (absorption '
                f"by 2030 or 2045 changes cumulative carbon by {r['low']:+.1f}%/{r['high']:+.1f}%, Extended Data Fig. 8).")
    return cap.replace(SURPLUS_TOKEN, sentence.replace('-0.', '−0.').replace('+-', '−'))


PAPER_MAIN = [
    dict(id='Fig1', file='Fig1_floor_area', width='double', module='figures.paper_main',
         title='Floor area: history and projection by demand band',
         caption='Floor area built per year by demand band: history as census-interval means (columns), the Reference '
                 'projection annually from 2026 (2026 observed). Positive bands stacked up from zero, negative bands '
                 '(the starting surplus and the overbuild absorbed, unconsented additions) down from zero. The black line is the floor area built '
                 '(in scope), annual 1992-2050 (history from consents, projection from 2026); the grey caps on the '
                 'history columns are the census-interval means. 2026 overbuild: observed 2026 building above need, fading from 2027; '
                 'it is absorbed by 2035 together with the starting surplus (the 2024-25 building beyond the stock identity, carried into 2026). '
                 + SURPLUS_TOKEN,
         source=['baseline/bands_history.csv', 'baseline/bands_annual.csv', 'baseline/annual.csv',
                 'baseline/overbuild_2026.json']),
    dict(id='Fig2', file='Fig2_reference_carbon', width='double', module='figures.paper_main',
         title='Embodied carbon of the Reference',
         caption='Annual embodied carbon of the Reference 2026-2050 by (a) demand type (the demand bands), (b) material and (c) life-cycle '
                 'stage; (d) cumulative 2026-2050 as three attached columns of the same total by demand band, material '
                 'and stage (negative demand bands solid below zero; the net total a black marker). Materials and stages are never '
                 'negative.',
         source=['baseline/bands_annual.csv', 'baseline/annual_by_material.csv', 'baseline/annual_by_stage.csv']),
    dict(id='Fig3', file='Fig3_reference_boundaries', width='double', module='figures.paper_main',
         title='The Reference against the planetary boundaries',
         caption='(a) Annual carbon, Monte Carlo median with 50% and 90% bands, against the acquired-rights (AR) and '
                 'ability-to-pay (AtP) boundaries and their zones; (b) cumulative carbon 2026-2050 with its Monte Carlo '
                 '90% interval (5th-95th percentile of the cumulative carbon) and 50% interval (25th-75th), the AR and '
                 'AtP budgets, and the '
                 'committed emissions after 2050: C1-C4 and B2/B4 after 2050, each a range (lower = 2050 factors '
                 'held, the carbon-bearing materials of C1-C4 at 2025 in both bounds; upper = 2025 factors), drawn at '
                 'the lower bound. ' + SURPLUS_TOKEN,
         source=['aesa/annual.csv', 'montecarlo/annual_REF.csv', 'montecarlo/draws_REF.csv', 'baseline/projection.json']),
    dict(id='Fig4', file='Fig4_pathways', width='double', module='figures.paper_main',
         title='The Pathways: the sequential waterfalls',
         # the caption follows the figure (a-c; the annual pathways are in Fig3a)
         caption='Sequential waterfalls of cumulative carbon 2026-2050 from the Reference, levers added in PAS 2080 '
                 'order: (a) L1 ... L10 at Moderate -> Moderate Pathway; (b) at Ambitious -> Ambitious Pathway; (c) L1 at '
                 'TL ... L10 at TL cumulative -> Theoretical Limit. Each step is one bar coloured by strategy with its net change; '
                 'AR (solid) and AtP (dotted) budgets with their zones; order-free Shapley values in Fig6.',
         source=['pathways/annual.csv', 'pathways/waterfall.csv', 'pathways/waterfall_tl_from_reference.csv']),
    dict(id='Fig5', file='Fig5_solution_space', width='double', module='figures.paper_main',
         title='The solution space',
         caption='Cumulative level of exceedance of AR over uniform cuts of 2027-2050 floor area (x) and of carbon per m2 '
                 '(y) (after Horup et al. 2025), with S1-S3 (Moderate filled, Ambitious hollow), the '
                 'Moderate / Ambitious Pathway and the Theoretical Limit; analytic LoE AR contours and the exact AR line. '
                 'Right: the cumulative LoE AR ruler (log) with the Reference, the Pathways, TL, AR = 1 and AtP; the same '
                 'marker size per run in the plane, the ruler and the legend.',
         source=['pathways/solution_space.csv', 'pathways/backcast.json', 'pathways/runs.csv']),
    dict(id='Fig6', file='Fig6_shapley_levers', width='double', module='figures.paper_main',
         title='What each lever removes',
         caption='Shapley values within each combined game (Reference -> Moderate Pathway, -> Ambitious Pathway, -> TL; '
                 'exact, 1,024 subsets) on cumulative carbon 2026-2050: rows grouped by PAS 2080 strategy (S1 Avoid, S2 '
                 'Switch, S3 Improve: L9 construction-stage carbon and L10 production decarbonisation) in the lever order '
                 'and coloured by strategy; filled bar Moderate, hollow bar '
                 'Ambitious, large dot TL. The TL dots are Shapley values within the TL game (all ten '
                 'levers at their limit), so they include each lever\'s interactions at the limit; L5 (occupancy '
                 'density) interacts with L4 (extra space): both act on the floor area per dwelling.',
         source=['pathways/shapley.csv']),
    dict(id='Fig7', file='Fig7_uncertainty', width='double', module='figures.paper_main',
         title='Uncertainty',
         caption='(a) One-at-a-time ranges of the Reference cumulative LoE AR 2026-2050, each input at its low and high '
                 'end per its definition (population rows move the budgets with the path; AR base-window rows move the '
                 'AR budget only); rows are shown from the completion-rate range up, without the completion-rate and '
                 'no-2026-data rows (both in Extended Data Fig. 8; the rows with a smaller range are named, with '
                 'their ranges, in the note); not additive, not a joint interval. (b) The Reference, the Moderate and Ambitious '
                 'Pathways and the Theoretical Limit: cumulative LoE AR against the 2050 New Zealand population on the '
                 'same paired Monte Carlo draws, P(LoE AR <= 1) of each with its Wilson 95% interval, LoE = 1, and the '
                 'population at which the Theoretical Limit has P(LoE AR <= 1) = 50% (Firth logistic; bootstrap 95% CI).',
         source=['sensitivity/tornado.csv', 'sensitivity/planetary_boundary.csv', 'pathways/montecarlo_draws.csv',
                 'pathways/annual.csv',
                 'pathways/montecarlo_conditional_tl.json', 'baseline/scenarios.json', 'aesa/results.json']),
]

PAPER_EXTENDED = [
    # nine figures in this order, with Extended Data Table 1 (EDT1) the tenth item (Nature: at most ten)
    dict(id='ED1', file='ED1_population_households_floor_area', module='figures.paper_extended',
         title='Population, households and floor area: history and projection',
         caption='Population (a), households (b) and cumulative floor area built (c): history (black) and the Reference '
                 'projection (dark red line). The shaded band is the range of the Stats NZ population projection '
                 'between its 5th and 95th percentile paths run through the model; it is not a Monte Carlo interval. '
                 'Households after the 2023 Census are population divided by the household-size path. The household '
                 'history is rebased on the 2023 Census (occupied and residents-away private dwellings): the Stats NZ '
                 'household increments after 2018 are scaled by one factor so that June 2023 matches the census.',
         source=['figure_source/projection_paths.json', 'figure_source/D02_households.json']),
    dict(id='ED2', file='ED2_household_formation_size', module='figures.paper_extended',
         title='Household formation and household size',
         caption='(a) Household formation by census interval, split into population growth and the change in household '
                 'size. (b) Household size: history, the Reference (Stats NZ 2023-base, living arrangements of 2023 '
                 'held), L1 Ambitious (Stats NZ propensity B, living arrangements keep changing as in 2001-2023) and '
                 'L1 at the Theoretical Limit, returning to the 1991 maximum of 2.79 no faster than the fastest change '
                 'between censuses (reached in mid-2037). The paths are '
                 'rebased on the observed 2023 household size.',
         source=['baseline/household_formation_history.csv', 'figure_source/D03_household_size.json',
                 'figure_source/D04_household_formation.json', 'pathways/levers.json', 'pathways/annual.csv']),
    dict(id='ED3', file='ED3_dwelling_size', module='figures.calibration',
         title='Dwelling size and occupied area',
         caption='(a) Realised floor area per new dwelling (floor area consented per dwelling consented) and the occupied '
                 'area per dwelling (household size times the occupied floor area per person); the gap is space above '
                 'occupancy. (b) Mean consented new-dwelling size by typology, 1990-2025, with the smallest annual mean '
                 '(dot, the L4 minimum) and the Reference size held at its 2023-2025 mean (dotted). (c) Occupied floor '
                 'area per person (OLF) by typology: design floor area per design occupant, with design occupants = '
                 'bedrooms + 1, from the New Zealand case studies; the number of case studies is printed on each bar.',
         source=['figure_source/D08_dwelling_space.json', 'pathways/levers.json']),
    dict(id='ED4', file='ED4_stock_vacancy', module='figures.calibration',
         title='Vacancy and dwellings per year by component',
         caption='(a) Vacancy rate of empty private dwellings: census values (filled; open where the 2013 split is '
                 'estimated), the series on one consistent definition, the rate held at its 2023 value in the '
                 'projection, and the implied rate including the surplus still to be absorbed. (b) Dwellings per year '
                 'by component: census intervals as interval means (columns), the pipeline years 2026-2027 as annual '
                 'columns and the projection as stacked areas; positive components are stacked up and negative ones '
                 'down from zero, and the line is the dwellings built in scope. The row at the top gives the market '
                 'balance of each census interval (thousand dwellings per year). 1986-1991 is not covered (the '
                 'calibration starts in 1991). In the last column (after the 2023 Census) households are population divided by '
                 'the household size of the model, not census-benchmarked.',
         source=['figure_source/D05_stock_and_vacancy.json', 'baseline/scenarios.json', 'baseline/projection.json']),
    dict(id='ED5', file='ED5_replacement_variants', module='figures.paper_extended',
         title='Net replacement: census-interval rates and the Low, High and Very High variants',
         caption='(a) Net replacement (demolition minus unconsented additions) as a share of the stock: census-interval '
                 'rates from dwelling counts (bars) and the four projection variants (lines), with the BRANZ demolition '
                 'rate and the long-run net rate 1991-2023. (b) Annual embodied carbon of the Reference, the Moderate '
                 'and Ambitious Pathways and the Theoretical Limit under each variant (line style), against the AR and '
                 'AtP budgets. (c) Cumulative level of exceedance of AR 2026-2050 by run and variant; LoE = 1 is the '
                 'AR budget.',
         source=['baseline/stock_identity_history.csv', 'figure_source/D07_net_replacement_rate.json',
                 'sensitivity/replacement_variants.csv', 'pathways/annual.csv']),
    dict(id='ED6', file='ED6_rollout_timing', module='figures.paper_extended',
         title='Roll-out timing: annual and cumulative carbon of the Pathways',
         caption='Annual embodied carbon of the Moderate (a) and Ambitious (b) Pathways with every lever fully adopted '
                 'by 2030, 2035 (adopted) or 2045 on the normalised logistic, and (c) their cumulative carbon '
                 '2026-2050 against the Reference (grey). Only the adoption window changes; the lever levels are the '
                 'same.',
         source=['pathways/annual.csv', 'pathways/runs.csv']),
    dict(id='ED7', file='ED7_boundary_sensitivity', module='figures.sensitivity',
         title='Boundary definitions and allocation: cumulative LoE of AR and of AtP',
         caption='One-at-a-time ranges of the Reference cumulative level of exceedance 2026-2050 of (a) acquired '
                 'rights (AR) and (b) ability to pay (AtP): boundary definitions (carrying capacity, global impact, AR '
                 'base window), allocation, population, replacement, the summation window (2028-2050 only: carbon and '
                 'budget both summed over 2028-2050, the pipeline years excluded; the AR base unchanged) and whole-life '
                 'accounting (committed emissions after 2050 counted at construction, the AR base recomputed on the '
                 'same convention). Each input is shown at its low (pale blue) and high (dark blue) end, a single '
                 'alternative case in grey; the ranges are not additive. Not shown (kept in the data file): α = 1 '
                 '(Hjalsted et al. SI tables) and the raw Stats NZ 2024-base median population. What each row changes '
                 'compared with the Reference: ',
         row_notes='ED7',
         source=['sensitivity/planetary_boundary.csv', 'aesa/results.json', 'loe_2028_2050.csv']),
    dict(id='ED8', file='ED8_one_at_a_time', module='figures.sensitivity',
         title='One at a time: cumulative embodied carbon 2026-2050 of the Reference and of the Theoretical Limit',
         caption='(a) One-at-a-time ranges of the Reference cumulative embodied carbon 2026-2050, grouped by category; '
                 'each input at its low (pale blue) and high (dark blue) end, a single alternative case grey, '
                 'intermediate cases as ticks; the ranges are not additive and are not a joint interval. Not shown '
                 '(kept in the data file): the overbuild gap against the same-year requirement, no census '
                 'under-construction correction, the maintenance event timing L / n, and the rows that compare with '
                 'superseded settings. (b) The Theoretical Limit under two L10 sensitivities, every other lever at TL, '
                 'against the central Theoretical Limit (vertical line): the near-zero factor of cement (125/850) on '
                 'every material class without a documented near-zero definition, steel keeping its own (an upper '
                 'bound on L10, not a documented scenario: no documented near-zero definition exists outside steel and '
                 'cement), and the near-zero share of cement and steel production 100% by 2050 instead of 93%; values '
                 'and P(cumulative LoE of AR ≤ 1) over the Monte Carlo draws in Supplementary Table 12. What each row '
                 'of (a) changes compared with the Reference: ',
         row_notes='ED8',
         source=['sensitivity/reference_carbon.csv', 'sensitivity/tl_sensitivity.csv']),
    dict(id='ED9', file='ED9_sobol', module='figures.montecarlo',
         title='Sobol indices of the Reference: embodied carbon and floor area 2026-2050',
         caption='First-order and total-effect Sobol indices of the Reference cumulative embodied carbon and floor area '
                 '2026-2050 for the sampled inputs (population rank, dwelling-size multiplier, completion rate and the '
                 'case-study carbon-factor bootstrap), from the full-profile Monte Carlo; bars are the estimates, '
                 'whiskers their bootstrap intervals.',
         source=['montecarlo/sobol_REF.csv']),
]

def _write_number_map(name, rows):
    import csv
    import layout
    path = layout.writing(layout.data(name))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['old_id', 'old_file', 'new_id', 'new_file', 'status'])
        for oid, ofile, nid, nfile in rows:
            st = ('added' if oid == 'new' else 'from the diagnostics' if oid.startswith('D') else
                  'no longer rendered' if nid is None else 'moved to Extended Data' if nid.startswith('ED') and oid.startswith('SF') else
                  'moved to Supplementary' if nid.startswith('SF') and
                  oid.startswith('ED') else 'figure -> table' if nid.startswith('ST') else
                  'same number' if (oid, ofile) == (nid, nfile) else 'renumbered')
            w.writerow(['' if oid == 'new' else oid, ofile or '', nid or '', nfile or '', st])
    return path

# Extended Data beyond the ten allowed (Nature Cities) -> outputs/supplementary/
# the Supplementary Figures, one continuous series in reading order (calibration -> validation -> the
# boundary method -> sensitivity -> Monte Carlo -> the TL dwellings); 'folder' only organises outputs/supplementary/
SUPPLEMENTARY = [
    dict(id='SF1', file='SF1_households', folder='calibration', module='figures.calibration',
         title='Households: the published and census-benchmarked series, and household size against population growth',
         source=['figure_source/D02_households.json', 'figure_source/D04_household_formation.json']),
    dict(id='SF2', file='SF2_completion_lag', folder='validation', module='figures.market_balance',
         title='Annual floor area by demand group: 17-month and like-for-like zero completion lag',
         source=['diagnostics/lag_comparison_annual.csv', 'diagnostics/lag_comparison_summary.json']),
    dict(id='SF3', file='SF3_vacancy_definition', folder='calibration', module='figures.calibration',
         title='Vacancy definition: unconsented additions each definition requires',
         source=['figure_source/D06_vacancy_definition.json']),
    dict(id='SF4', file='SF4_overbuild_absorption', folder='calibration', module='figures.paper_extended',
         title='The starting surplus and the 2026 overbuild: absorption in the Reference and its timing sensitivity',
         source=['baseline/overbuild_absorption_log.csv', 'baseline/sensitivity_annual_carbon.csv']),
    dict(id='SF5', file='SF5_hindcast', folder='validation', module='figures.validation',
         title='Rolling-origin hindcast of dwellings built and the 2027 out-of-sample check',
         source=['figure_source/D14_hindcast.json', 'baseline/validation.json']),
    dict(id='SF6', file='SF6_reality_checks', folder='validation', module='figures.validation',
         title='Reality checks: the projection against the 1991-2025 range',
         source=['figure_source/D15_reality_checks.json', 'baseline/annual.csv', 'baseline/variants_annual.csv']),
    dict(id='SF7', file='SF7_lambda_sweep', folder='sensitivity', module='figures.paper_extended',
         title='Each lever from the Reference to Ambitious (lambda sweep) and its Theoretical Limit',
         source=['pathways/lambda_sweep.csv']),
    dict(id='SF8', file='SF8_lever_annual', folder='pathways', module='figures.pathways',
         title='Each lever alone: annual embodied carbon at Moderate, Ambitious and the Theoretical Limit',
         source=['pathways/lever_annual.csv', 'pathways/annual.csv']),
    dict(id='SF9', file='SF9_hd_estimators', folder='sensitivity', module='figures.paper_extended',
         title='Harrell-Davis estimators of L5 and L8 with bootstrap intervals', source=['pathways/levers.json']),
    dict(id='SF10', file='SF10_tl_dwellings', folder='pathways', module='figures.pathways',
         title='The Theoretical Limit: need, released dwellings, re-occupation and dwellings built per year',
         source=['pathways/reoccupation_log.csv']),
    dict(id='SF11', file='SF11_mc_input_distributions', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo input distributions',
         source=['montecarlo/draws_REF.csv', 'montecarlo/input_distributions_REF.csv',
                 'montecarlo/carbon_factors_REF.csv', 'pathways/montecarlo_draws.csv', 'factors/factors_typology.csv',
                 'factors/factors_building.csv']),
    dict(id='SF12', file='SF12_pathway_mc', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo: annual carbon of the Reference, the Pathways and TL (median, 5th-95th)',
         source=['pathways/montecarlo_annual.csv', 'pathways/montecarlo_summary.csv']),
    dict(id='SF13', file='SF13_conditional_tl', folder='montecarlo', module='figures.paper_extended',
         title='When does TL stay within AR? By population quintile and the population threshold',
         source=['pathways/montecarlo_conditional_tl.csv', 'pathways/montecarlo_conditional_tl.json',
                 'pathways/theoretical_limit.json', 'pathways/montecarlo_summary.csv', 'pathways/levers.json']),
    dict(id='SF14', file='SF14_prcc', folder='sensitivity', module='figures.sensitivity',
         title='Monte Carlo sensitivity: partial rank correlation of each input, Reference, Moderate Pathway and TL',
         source=['pathways/montecarlo_importance.csv']),
    dict(id='SF15', file='SF15_mc_convergence', folder='montecarlo', module='figures.montecarlo',
         title='Monte Carlo convergence of the 2026-2050 percentiles', source=['montecarlo/convergence_REF.csv']),
    dict(id='SF16', file='SF16_headship_by_census', folder='pathways', module='figures.pathways',
         title='Household formation (headship) by age group across censuses and the by-age limit (sensitivity)',
         source=['pathways/levers.json']),
]
# Supplementary Tables (Markdown + CSV, outputs/supplementary/<folder>/)
# Repository numbers = manuscript numbers (from MODEL v4.10.1): Extended Data figures numbered by first citation in the
# manuscript, Supplementary figures and tables by first citation in the SI (after the Methods). Table 1 (main paper) is
# outputs/reports/LEVERS_TABLE_MAIN.md (tools/pathways_methods.py); Extended Data Table 1 is LEVERS_TABLE.md with its
# per-typology values (paper_extended/EDT1_levels_by_typology).
NUMBERING_NOTE = ('Repository numbers = manuscript numbers; the renumbering of each version is in '
                  'data/ed_number_map.csv, data/sf_number_map.csv and data/st_number_map.csv.')


def manuscript_map_lines():
    """The numbering note (a list of lines)."""
    return [NUMBERING_NOTE]


SUPPLEMENTARY_TABLES = [dict(id='ST8', file='ST8_budget_construction', folder='boundaries', module='figures.boundaries',
                             title='The AR and AtP budgets: components, the budgets in 2025 and 2050 and the 2050 '
                                   'population modifier', source=['aesa/results.json',
                                                                           'figure_source/D22_boundaries.json'])]
TABLE_MODULES = ('figures.paper_extended', 'figures.boundaries')      # the modules that write tables (TABLES)
# tables of the Extended Data (Markdown + CSV, outputs/paper_extended/)
EXTENDED_TABLES = [dict(id='EDT1', file='EDT1_levels_by_typology', title='Lever levels by typology: Moderate, '
                        'Ambitious and TL', source=['pathways/levers.json'])]

# no separate diagnostic figures; every figure is a main, Extended Data or Supplementary figure
DIAGNOSTICS = {}
# figures drawn only in the full profile (their data exist only there)
FULL_ONLY = ('ED9_sobol',)

# Maintenance (B2, B4) drawn as its own layer: only in the band and stage breakdowns
MAINTENANCE_ALLOWED = ('Fig2_reference_carbon', 'Fig3_reference_boundaries')
# every figure with a planetary boundary on its axes (zones required; AtP dotted)
# (budget construction is the Supplementary Table ST8, no axes)
PB_FIGURES = ('Fig3_reference_boundaries', 'Fig4_pathways', 'Fig5_solution_space',
              'ED7_replacement_variants', 'ED4_rollout_timing')

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


# ============================================================
# NUMBER MAPS: the single source of the renumbering v4.10.2 -> v5.0.0 (manuscript order); the
# maps below and outputs/data/{ed,sf,st}_number_map.csv are derived from it and from the lists above. Earlier maps
# (v4.3.0 -> v4.10.0) are in the git history and the CHANGELOG.
# ============================================================
# the renumbering v4.10.2 -> v5.0.0 (new id -> old id: figures merged, split or moved between Extended Data and the
# Supplementary figures); ED5 merges SF3 (panel a) and ED7, ED4 is ED3 panels a-b (panel c is SF3), SF16 is new
RENUMBER = {'ED3': 'SF4', 'ED4': 'ED3', 'ED5': 'ED7', 'ED6': 'ED4', 'ED7': 'ED5', 'ED8': 'ED6',
            'SF3': 'ED3', 'SF4': 'SF5', 'SF5': 'SF6', 'SF6': 'SF7', 'SF7': 'SF8', 'SF8': 'ED8', 'SF16': 'new'}
MERGED = {'ED5': 'SF3'}      # a second source of a merged item (SF3 panel a -> ED5 panel a)
_PREVIOUS = dict(RENUMBER)
# The Supplementary Tables of the SI (numbered by first citation in the SI); 'file' the repository table, if any
SI_TABLES = [
    ('ST1', 'data sources', None, 'SI text table (README Data availability; outputs/reports/AVAILABILITY.md)'),
    ('ST2', 'assumption register', None, 'outputs/reports/ASSUMPTIONS.md'),
    ('ST3', 'net replacement variants', None, 'outputs/data/sensitivity/replacement_variants.csv'),
    ('ST4', 'demand bands of the Reference 2026-2050', None, 'outputs/data/baseline/bands_annual.csv'),
    ('ST5', 'hindcast errors', None, 'outputs/data/baseline/validation.json'),
    ('ST6', 'item mapping to the decarbonisation paths', None, 'data/material_item_map.csv'),
    ('ST7', 'embodied carbon by term, 2025 vs decarbonised factors', None,
     'outputs/reports/reconciliation.md and METHODS_DRAFT.md'),
    ('ST8', 'budget construction', 'ST8_budget_construction', 'outputs/supplementary/boundaries/ST8_budget_construction'),
    ('ST9', 'deterministic AESA sensitivities', None, 'outputs/data/sensitivity/planetary_boundary.csv'),
    ('ST10', 'strategies, Pathways and TL runs (with the 2028-2050 LoE)', None,
     'outputs/data/pathways/runs.csv and outputs/data/loe_2028_2050.csv'),
    ('ST11', 'Monte Carlo inputs', None, 'SI text table'),
    ('ST12', 'Theoretical Limit sensitivities (deterministic and Monte Carlo)', None,
     'outputs/data/sensitivity/tl_sensitivity.csv'),
    ('ST13', 'limitations register', None, 'SI text table'),
]
# v4.10.2 -> v5.0.0: the limitations register moves from ST12 to ST13; ST12 (TL sensitivities) is new
ST_PREVIOUS = {'ST12': 'new', 'ST13': 'ST12'}


# old files where the old id plus the new suffix is not the old file name (a split panel, a merged source)
OLD_FILE = {'SF3': 'ED3_stock_vacancy (panel c)', 'ED5:SF3': 'SF3_census_replacement_rates (as panel a)'}


def _map_rows(items):
    """(old id, old file, new id, new file) of each item, the old id from RENUMBER (same id when not renumbered), and
    one more row for the second source of a merged item (MERGED)."""
    rows = []
    for h in items:
        old = _PREVIOUS.get(h['id'], h['id'])
        ofile = None if old == 'new' else OLD_FILE.get(h['id'], old + h['file'][len(h['id']):])
        rows.append((old, ofile, h['id'], h['file']))
        if h['id'] in MERGED:
            o2 = MERGED[h['id']]
            rows.append((o2, OLD_FILE[f"{h['id']}:{o2}"], h['id'], h['file']))
    key = lambda r: ('~' if r[0] == 'new' else r[0].rstrip('0123456789'), int(r[0].lstrip('EDTSF') or 0) if r[0] != 'new' else 0)
    return sorted(rows, key=key)


def write_ed_number_map():
    """outputs/data/ed_number_map.csv (v4.10.2 -> v5.0.0; old id, old file, new id, new file, status). Written by
    pathways.py with the deterministic outputs (with write_sf_number_map and write_st_number_map)."""
    return _write_number_map('ed_number_map.csv', _map_rows(PAPER_EXTENDED + EXTENDED_TABLES))


def write_sf_number_map():
    """outputs/data/sf_number_map.csv (v4.10.2 -> v5.0.0, Supplementary Figures)."""
    return _write_number_map('sf_number_map.csv', _map_rows(SUPPLEMENTARY))


def write_st_number_map():
    """outputs/data/st_number_map.csv (v4.10.2 -> v5.0.0, Supplementary Tables of the SI): every SI table with its
    content and repository source, and its v4.10.2 number where it changed (ST_PREVIOUS: the limitations register
    moves from ST12 to ST13; ST12 is new)."""
    import csv
    import layout
    path = layout.writing(layout.data('st_number_map.csv'))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['old_id', 'old_file', 'new_id', 'new_file', 'status', 'content', 'repository_source'])
        for nid, content, nfile, src in SI_TABLES:
            old = ST_PREVIOUS.get(nid)
            w.writerow(['' if old in (None, 'new') else old,
                        (old + nfile[len(nid):]) if (old not in (None, 'new') and nfile) else '', nid, nfile or '',
                        'added' if old == 'new' else 'renumbered' if old else 'same number', content, src])
    return path

