"""The figure plan of MODEL v2.1.0 (docs/FIGURE_PLAN_v2.md, amended by the v2.1.0 entries): one entry per figure of the release,
with its title, panels, data source, draft caption and the earlier figures it replaces.

    outputs/paper/           Fig1-Fig6 (PAPER) and Tables 1-2, PAPER.md            paper.py
    outputs/extended_data/   ED1-ED10 (EXTENDED_DATA), EXTENDED_DATA.md             extended_data.py
    outputs/key_figures/     K1-K6 (KEY_FIGURES), KEY_FIGURES.md                     key_figures.py
    outputs/diagnostics/     every other figure, by group (DIAGNOSTICS), DIAGNOSTICS.md

Figures are written as PNG (300 dpi); with run_all.py --export (PATHWAY_EXPORT=1) the paper, Extended Data and
key figures also get a vector PDF and a source-data CSV. Every planetary-boundary figure (PB_FIGURES) uses the
boundary styling of style.py (thin AR and AtP lines; zones below AtP, between AtP and AR, above AR).

tools/design_docs.py writes docs/FIGURE_PLAN.md and the figure tables of docs/RENAMING.md from it;
the figure audit (tests/test_release.py) requires every planned file to exist and every file in
outputs/ to be indexed. Captions are drafts: numbers in braces are filled from the data files when
the figure is drawn, never typed by hand.
"""
PAPER_GROUP = 'paper'
ED_GROUP = 'extended_data'
TL_NOTE = 'TL: hyper-optimistic theoretical limit; a thought experiment, not a pathway.'

# ---------------------------------------------------------------------------
# Paper figures (outputs/paper/): PNG 300 dpi + vector PDF + source-data CSV
# ---------------------------------------------------------------------------
PAPER = [
    dict(id='Fig1', file='Fig1_model_schematic', width='double', title='How the model works',
         panels='one panel: population -> households -> dwellings required -> floor area -> embodied carbon -> '
                'level of exceedance against the AESA boundaries (AR, AtP); the demand bands branch off the dwellings '
                'step, each lever (L1-L9) attached to the band or quantity it acts on; P1-P4 group the levers, P5 '
                'combines them; TL1-TL10 at the end of the same arrows; the untargeted band (population growth) '
                'marked',
         source='naming.py, levers.py (structure only; no numbers)',
         caption='Model structure. A bottom-up chain converts population and household projections into '
                 'dwellings required, floor area by reason for building (demand bands) and embodied carbon, '
                 'which is compared with two allocations of a global carrying capacity (acquired rights, AR; '
                 'ability to pay, AtP). Pathway levers act on the band or quantity they target; only population '
                 'growth is untargeted by design.',
         v1=['H1'], legacy=[]),
    dict(id='Fig2', file='Fig2_demand_bands', width='double', title='Why floor area is built',
         panels='(a) floor area by demand band: history one column per census interval with the census-measured net '
                'replacement and the unexplained building (hatched, neutral; may be negative), Reference projection '
                'annual 2026-2050; (b) the Reference bands as embodied carbon per year, maintenance (B2, B4) as its '
                'own layer',
         source='data/baseline/bands_history.csv, data/baseline/bands_history_replacement_split.csv, '
                'data/baseline/bands_annual.csv',
         caption='Floor area and carbon by reason for building. Bands sum to the in-scope total. Only population '
                 'growth is untargeted; smaller households, extra space, vacancy, the 2026 overbuild, historical '
                 'replacement and the recent replacement surge are the bands the pathways act on.',
         v1=['H3'], legacy=['diag_4_floor_area', 'boss_04_annual_gfa']),
    dict(id='Fig3', file='Fig3_reference_carbon', width='double', title='Embodied carbon of the Reference',
         panels='(a) annual carbon 2026-2050 by life-cycle stage (A1-A3, A4-A5, maintenance B2/B4, soil carbon loss); '
                '(b) the same carbon by material, soil carbon loss on top; (c) cumulative carbon 2026-2050 and the '
                'emissions committed after 2050 (lower-upper, hatched), second axis in years of the 2050 AR boundary',
         source='data/baseline/annual_by_stage.csv, data/baseline/annual_by_material.csv, data/aesa/results.json',
         caption='Embodied carbon of new residential construction in the Reference. Materials (A1-A3), construction '
                 '(A4-A5) and soil carbon loss are counted in the construction year, maintenance (B2, B4) in the year '
                 'it occurs within 2026-2050; later events and end of life are committed after 2050 (c, hatched).',
         v1=['H4', 'H6'], legacy=['boss_05_annual_carbon', 'boss_06_cumulative_carbon', 'boss_10_material_flows',
                                  'diag_5_carbon', 'pb_6_committed']),
    dict(id='Fig4', file='Fig4_pathways_bands', width='double', title='What each pathway removes, by demand band',
         panels='(a) floor area and (b) carbon 2026-2050 by demand band for the Reference, P1-P5 and TL; untargeted '
                'band (population growth) at the bottom; maintenance its own layer in (b); change vs the Reference '
                'on each bar; cumulative AR and AtP budgets as lines with the boundary zones in (b)',
         source='data/pathways/bands.csv, data/pathways/runs.csv',
         caption='Pathways by demand band (each pathway at its Moderate setting, full roll-out by 2035). Each pathway '
                 'acts on the bands it targets; P3 and P4 lower carbon per m2 of every band. ' + TL_NOTE,
         v1=['H7'], legacy=['pw_1_bands_by_pathway']),
    dict(id='Fig5', file='Fig5_boundaries_attribution', width='double',
         title='Emissions against the boundaries, and what closes the gap',
         panels='(a) annual emissions of the Reference, P5 and TL against the annual AR and AtP boundaries (log axis), '
                'Monte Carlo 5-95% bands, TL zero-building years shaded; (b) Shapley waterfall of the cumulative LoE '
                'AR (AtP on the right axis): Reference -> P1-P4 -> P5 -> full strength from 2027 -> TL1-TL10 -> TL, '
                'budgets as lines with the boundary zones, Monte Carlo whiskers, committed after 2050 as hatched companion bars, TL residual '
                'in dwellings and people',
         source='data/pathways/annual.csv, data/pathways/montecarlo_annual.csv, data/aesa/montecarlo_annual.csv, '
                'data/pathways/shapley_pathways.csv, data/pathways/shapley_theoretical_limit.csv, '
                'data/pathways/montecarlo_summary.csv, data/pathways/runs.csv, data/pathways/theoretical_limit.json',
         caption='Absolute sustainability of the Reference, P5 Combined and the theoretical limit. ' + TL_NOTE,
         v1=['H5', 'H8', 'H9'], legacy=['pb_2_loe', 'boss_05_annual_carbon_pb', 'fig_scenarios_pb', 'pw_4_annual_SI',
                                        'pw_10_T_annual_SI', 'pw_2_shapley_waterfall', 'pw_8_staircase']),
    dict(id='Fig6', file='Fig6_solution_space', width='single', title='Solution space: demand and intensity',
         panels='cumulative LoE AR over uniform cuts of 2027-2050 floor area (x) and of non-soil carbon per m2 (y), '
                '0-100%, in the three boundary zones with the AR and AtP budget contours; P1-P5 and TL at their effective '
                'coordinates',
         source='data/pathways/solution_space.csv, data/pathways/backcast.json, data/pathways/theoretical_limit.json',
         caption='Solution space (after Horup et al. 2025, Fig. 6). Markers sit at each run\'s effective reductions '
                 'of 2027-2050 floor area and non-soil carbon per m2; L8, L9, TL8 and TL9 also lower soil carbon, which '
                 'the plane does not show.',
         v1=['H10'], legacy=['pw_3_solution_space']),
]

TABLES = [
    dict(id='Table1', file='Table1_levers', title='Levers and the theoretical-limit assumptions',
         source='data/pathways/levers.json, data/pathways/theoretical_limit.json (outputs/reports/LEVERS_TABLE.md)'),
    dict(id='Table2', file='Table2_results', title='Results 2026-2050: the Reference, P1-P5 and TL',
         source='data/pathways/runs.csv, data/pathways/montecarlo_summary.csv'),
]

# ---------------------------------------------------------------------------
# Extended Data (outputs/extended_data/): PNG 300 dpi + vector PDF + source-data CSV
# ---------------------------------------------------------------------------
ONE_AT_A_TIME = 'One-at-a-time ranges are not additive and are not a joint interval.'
EXTENDED_DATA = [
    dict(id='ED1', file='ED1_reference_carbon_tornado', width='double',
         title='What moves the Reference carbon 2026-2050', source='data/sensitivity/reference_carbon.csv',
         caption='One-at-a-time sensitivity of the Reference carbon 2026-2050, grouped by the type of change; '
                 'population rows from the exact engine paths. ' + ONE_AT_A_TIME,
         v1=['H11', 'D16'], legacy=['sens_1_tornado', 'sens_1_tornado_SI']),
    dict(id='ED2', file='ED2_p5_carbon_tornado', width='double', title='What moves P5 carbon 2026-2050',
         source='data/sensitivity/p5_carbon.csv',
         caption='Sensitivity of P5 Combined (Moderate, full roll-out by 2035) to the pathway design, the roll-out '
                 'timing, the replacement scenario and the population path. ' + ONE_AT_A_TIME, v1=[], legacy=[]),
    dict(id='ED3', file='ED3_sensitivity_paths', width='double', title='Sensitivity paths of the Reference carbon',
         source='data/baseline/sensitivity_annual_carbon.csv, data/sensitivity/reference_carbon.csv',
         caption='Annual carbon 2026-2050 of every one-at-a-time row, one panel per group; the Reference in black.',
         v1=['D17'], legacy=['sens_2_paths']),
    dict(id='ED4', file='ED4_boundary_tornado', width='double',
         title='What moves the cumulative level of exceedance', source='data/sensitivity/planetary_boundary.csv',
         caption='One-at-a-time sensitivity of the cumulative level of exceedance of the Reference, AR and AtP side by '
                 'side. ' + ONE_AT_A_TIME, v1=['H11'], legacy=['pb_4_sensitivity']),
    dict(id='ED5', file='ED5_monte_carlo', width='double', title='Monte Carlo of the Reference, P5 and TL',
         source='data/montecarlo/annual_REF.csv, data/montecarlo/summary_REF.csv, data/pathways/montecarlo_draws.csv, '
                'data/pathways/montecarlo_summary.csv',
         caption='Joint parametric uncertainty (Latin hypercube, 5,000 draws of the Reference; each draw also run '
                 'through P5 and TL).', v1=['H2'], legacy=['mc_1_fan']),
    dict(id='ED6', file='ED6_ambitious_settings', width='double', title='Ambitious settings',
         source='data/pathways/runs.csv', caption='P1-P5 at the Ambitious setting against the Moderate setting.',
         v1=[], legacy=[]),
    dict(id='ED7', file='ED7_rollout_timing', width='double', title='Roll-out timing',
         source='data/pathways/annual.csv, data/pathways/runs.csv, levers.py (adoption paths)',
         caption='P5 Combined with full roll-out by 2030, 2035 (adopted) and 2045.', v1=['D29'],
         legacy=['pw_5_envelope_SI']),
    dict(id='ED8', file='ED8_theoretical_limit', width='double', title='The theoretical limit: attribution and indicators',
         source='data/pathways/shapley_theoretical_limit.csv, data/pathways/theoretical_limit.json, '
                'data/pathways/annual.csv',
         caption='Order-free attribution of P5 Combined (Moderate) to TL over TL1-TL10 (1,024 subsets), and the TL '
                 'indicators. ' + TL_NOTE,
         v1=['D33'], legacy=['pw_9_T_shapley_SI']),
    dict(id='ED9', file='ED9_single_levers', width='double', title='Single levers',
         source='data/pathways/runs.csv, data/pathways/shapley_levers.csv',
         caption='Each lever alone at the Moderate and Ambitious settings, and the lever attribution of P5 (Moderate).',
         v1=['D31'], legacy=['pw_7_shapley_levers_SI']),
    dict(id='ED10', file='ED10_replacement_variants', width='double', title='Low and High replacement',
         source='data/sensitivity/replacement_variants.csv',
         caption='The Reference, P5 Combined (Moderate) and TL under the Low, Reference and High replacement variants.',
         v1=['D29', 'D27'], legacy=[]),
    # MODEL v2.1.0: what the joint uncertainty says (the saved Reference draws through P5 and TL)
    dict(id='ED11', file='ED11_mc_scatter', width='double', title='Monte Carlo inputs against outputs',
         source='data/pathways/montecarlo_draws.csv, data/montecarlo/draws_REF.csv',
         caption='Scatter matrix of the four sampled inputs (population rank, which also sets household size; '
                 'dwelling-size multiplier; completion rate; carbon-factor index) against floor area, carbon and the '
                 'cumulative LoE AR 2026-2050 of the Reference, P5 Combined (Moderate) and TL, with ordinary '
                 'least-squares and LOWESS fits.', v1=[], legacy=[]),
    dict(id='ED12', file='ED12_mc_importance', width='double', title='What drives the joint uncertainty',
         source='data/pathways/montecarlo_importance.csv, data/montecarlo/sobol_REF.csv',
         caption='Standardised regression coefficients (SRC) and partial rank correlation coefficients (PRCC) of the '
                 'cumulative LoE AR with percentile-bootstrap 95% intervals, for the Reference, P5 Combined '
                 '(Moderate) and TL, beside the Sobol indices of the Reference carbon.', v1=[], legacy=[]),
    dict(id='ED13', file='ED13_conditional_tl', width='double', title='When does the theoretical limit stay within AR?',
         source='data/pathways/montecarlo_draws.csv, data/pathways/montecarlo_conditional_tl.csv',
         caption='TL cumulative LoE AR against the population rank of each draw, coloured by the carbon-factor index, '
                 'with LoE AR = 1; logistic regression of P(TL LoE AR <= 1) on the sampled inputs (odds ratios '
                 'with 95% intervals). ' + TL_NOTE, v1=[], legacy=[]),
]

# ---------------------------------------------------------------------------
# Key figures (outputs/key_figures/, MODEL v2.1.0): the story in six figures, KEY_FIGURES.md
# ---------------------------------------------------------------------------
KEY_GROUP = 'key_figures'
KEY_FIGURES = [
    dict(id='K1', file='K1_demand_bands', width='double', title='Why floor area is built',
         source='data/baseline/bands_history.csv, data/baseline/bands_annual.csv',
         caption='Floor area by demand band: history per census interval and the Reference projection 2026-2050.'),
    dict(id='K2', file='K2_reference_carbon', width='double', title='Embodied carbon of the Reference',
         source='data/baseline/annual_by_stage.csv, data/baseline/annual_by_material.csv, data/baseline/bands_annual.csv, '
                'data/pathways/runs.csv',
         caption='Reference carbon 2026-2050 by life-cycle stage, by material and by demand band, and the emissions '
                 'committed after 2050.'),
    dict(id='K3', file='K3_annual_emissions', width='double', title='Annual emissions against the boundaries',
         source='data/pathways/annual.csv, data/aesa/montecarlo_annual.csv, data/pathways/theoretical_limit.json',
         caption='Annual embodied carbon of the Reference (Monte Carlo 5-95% band), P1-P5 (Moderate) and TL against '
                 'the AR and AtP boundaries; TL zero-building years shaded. ' + TL_NOTE),
    dict(id='K4', file='K4_solution_space', width='single', title='Solution space',
         source='data/pathways/solution_space.csv, data/pathways/backcast.json, data/pathways/theoretical_limit.json',
         caption='Cumulative LoE AR over uniform cuts of 2027-2050 floor area and non-soil carbon per m2, in the '
                 'boundary zones; P1-P5 (Moderate) and TL at their effective coordinates.'),
    dict(id='K5', file='K5_band_waterfall', width='double', title='From the Reference to the theoretical limit',
         source='data/pathways/waterfall_sequential.csv',
         caption='Sequential waterfall of carbon 2026-2050, each step segmented by its exact demand-band deltas: '
                 'Reference -> P1 -> P2 -> P3 -> P4 (= P5 Combined, Moderate) -> TL1 ... TL10 (= TL), against the '
                 'cumulative budgets. Sequential steps depend on the order; the order-free Shapley values are in '
                 'Table 2, ED8 and ED9. ' + TL_NOTE),
    dict(id='K6', file='K6_schematic', width='double', title='Levers, pathways and the theoretical limit',
         source='naming.py, levers.py (structure only; no numbers)',
         caption='The nine levers (L1-L9) by the demand band or quantity they target, grouped into P1-P4 and combined '
                 'in P5; TL1-TL10 at the end of the same arrows.'),
]

# Every planetary-boundary figure (emissions or levels of exceedance against the AR / AtP budgets): drawn with the
# boundary styling of style.py (the figure audit checks the AR / AtP lines and the zones; tests/test_release.py).
# Figures of changes in the level of exceedance (tornados D18, ED4) have no boundary on their axis.
PB_FIGURES = ('Fig4_pathways_bands', 'Fig5_boundaries_attribution', 'Fig6_solution_space',
              'ED5_monte_carlo', 'ED6_ambitious_settings', 'ED7_rollout_timing', 'ED10_replacement_variants',
              'ED11_mc_scatter', 'ED13_conditional_tl', 'D21_fan_and_boundaries', 'D22_boundaries', 'D23_annual_loe', 'D24_headroom',
              'D25_annual_carbon_by_band', 'D26_cumulative_carbon_by_band', 'D27_variants_vs_boundaries',
              'D28_pathways_annual', 'D32_tl_staircase', 'D34_tl_dwellings', 'K3_annual_emissions',
              'K4_solution_space', 'K5_band_waterfall')

# model-v1.1.0 figure -> MODEL v2.0.0 location (docs/RENAMING.md, section MODEL v2.0.0)
V1_MAP = {
    'H1': 'Fig1', 'H2': 'ED5 (a)', 'H3': 'Fig2 (a)', 'H4': 'Fig3 (a, b)', 'H5': 'Fig5 (a) (with P5, TL and their Monte '
    'Carlo bands)', 'H6': 'Fig3 (c)', 'H7': 'Fig4 (Moderate; Ambitious in ED6)', 'H8': 'Fig5 (a)',
    'H9': 'Fig5 (b) (Moderate; TL1-TL10 relative to P5 Moderate)', 'H10': 'Fig6', 'H11': 'ED1 (carbon) and ED4 (LoE)',
    'D16': 'ED1', 'D17': 'ED3', 'D29': 'ED7, ED10', 'D31': 'ED9', 'D33': 'ED8',
    'outputs/headline/ (HEADLINE.md)': 'outputs/paper/ (PAPER.md) and outputs/extended_data/ (EXTENDED_DATA.md)',
}
# model-v1.1.0 diagnostics superseded by Extended Data (their data stay in outputs/data/)
SUPERSEDED = {'D16_one_at_a_time': 'ED1', 'D17_sensitivity_paths': 'ED3', 'D29_adoption_and_variants': 'ED7, ED10',
              'D31_shapley_levers': 'ED9', 'D33_tl_shapley': 'ED8'}

# Maintenance (B2, B4) is drawn as its own layer only in Fig3 and in the demand-band breakdowns (Fig2 and Fig4
# carbon panels, D25, D26, and D32 c, the carbon by demand band of Reference / P5 Ambitious / TL, which the design
# document did not list); elsewhere it is in the totals (figaudit.maintenance_drawn; tests/test_release.py)
MAINTENANCE_ALLOWED = ('Fig2_demand_bands', 'Fig3_reference_carbon', 'Fig4_pathways_bands', 'D25_annual_carbon_by_band',
                       'D26_cumulative_carbon_by_band', 'D32_tl_staircase',
                       # MODEL v2.1.0 key figures: the Reference carbon by stage and band (K2), the band waterfall (K5)
                       'K2_reference_carbon', 'K5_band_waterfall')

# ---------------------------------------------------------------------------
# Diagnostics (outputs/diagnostics/<group>/): PNG 300 dpi
# ---------------------------------------------------------------------------
DIAGNOSTICS = {
    'data_calibration': [
        ('D01_population', 'Population, history and projection (median, 5th-95th)', ['boss_01_population']),
        ('D02_households', 'Households: census-benchmarked history and projection', ['boss_02_households']),
        ('D03_household_size', 'Household size and population vs household growth', ['boss_08_demographic_drivers']),
        ('D04_household_formation', 'Household size vs arrivals; households per consent (2019 on consent-derived); new '
         'households by source: history one column per census interval (population growth, household-size change; '
         '2024-25 hatched, no census check), projection annual',
         ['diag_2_household_engines']),
        ('D05_stock_and_vacancy', 'Vacancy (definitions, consistent 1986-2023 range, implied vacancy), stock, '
         'dwellings per year by component (history per census interval with census-measured net replacement and '
         'unexplained building; projection annual)', ['diag_3_stock_bucket']),
        ('D06_vacancy_definition', 'Why empty-only vacancy is used (appendix)', ['diag_3b_appendix_vacancy_definition']),
        ('D07_net_replacement_rate', 'Net replacement rate: census intervals and the three variants',
         ['fig_replacement_rate']),
        ('D08_dwelling_space', 'Realised vs occupied floor area per new dwelling; occupancy utilisation',
         ['boss_09_space_diagnostics']),
        ('D09_cumulative_floor_area', 'Cumulative floor area 1991-2050 with the population 5th-95th band',
         ['boss_03_cumulative_gfa']),
        ('D10_floor_area_bridge', 'Floor area 2026-2050 by demand band, Low / Reference / High (waterfall)',
         ['fig_bridge']),
        ('D11_floor_area_bridge_split', 'The bridge with replacement split into demolition and net unconsented '
         'additions (appendix; the split assumes the BRANZ rate)', ['fig_bridge_appendix_split']),
        ('D12_conversion_chain', 'Population -> households -> dwellings -> floor area -> carbon (indices); '
         'carbon intensity of new floor area by variant', ['fig_conversion_chain']),
        ('D13_carbon_by_material', 'Embodied carbon by material, annual and cumulative', ['boss_10_material_flows']),
    ],
    'validation': [
        ('D14_hindcast', 'Rolling-origin hindcast of dwellings built and the 2026 out-of-sample check',
         ['fig_validation']),
        ('D15_reality_checks', 'Projection vs the 1991-2025 range and the 2026 -> 2027 handover',
         ['fig_reality_checks']),
    ],
    'sensitivity': [
        ('D18_aesa_sensitivity', 'All AESA sensitivity rows: cumulative LoE AR and AtP', ['pb_4_sensitivity_SI']),
        ('D19_variants', 'Annual and cumulative floor area and carbon by projection variant', ['fig_scenarios']),
    ],
    'monte_carlo': [
        ('D20_sobol', 'Sobol indices (Reference): what drives the joint uncertainty', ['mc_3_sobol']),
        ('D21_fan_and_boundaries', 'Monte Carlo fan of carbon, the AR base window and the boundary bands',
         ['mc_1_fan_pb']),
    ],
    'planetary_boundary': [
        ('D22_boundaries', 'Boundaries AR and AtP 2025-2050, population modifier, components', ['pb_1_boundaries']),
        ('D23_annual_loe', 'Annual level of exceedance by variant with Monte Carlo bands', ['pb_2_loe']),
        ('D24_headroom', 'Intensity, floor area and carbon per dwelling that would fit each boundary',
         ['pb_3_headroom']),
        ('D25_annual_carbon_by_band', 'Annual carbon by demand band against the boundaries',
         ['pb_5_demand_vs_boundary']),
        ('D26_cumulative_carbon_by_band', 'Cumulative carbon by demand band against the cumulative boundaries',
         ['boss_06_cumulative_carbon_pb']),
        ('D27_variants_vs_boundaries', 'Annual and cumulative carbon by variant against the boundaries',
         ['fig_scenarios_pb']),
    ],
    'pathways_si': [
        ('D28_pathways_annual', 'Annual carbon of the Reference and P1-P5 against the boundaries', ['pw_4_annual_SI']),
        ('D30_l6_estimator', 'L6 material carbon: Harrell-Davis estimator of the case-study ratios',
         ['pw_6_L5_estimator_SI']),
        ('D32_tl_staircase', 'Reference -> P5 -> TL: cumulative LoE and the human terms (size, space per '
         'person, dwellings built)', ['pw_8_staircase']),
        ('D34_tl_dwellings', 'TL: dwellings built per year (banking rule) and annual carbon', ['pw_10_T_annual_SI']),
    ],
}

# v3.1 figures that are not carried into the release, with the reason (CHANGELOG)
REMOVED = {
    'boss_04_annual_gfa': 'superseded by Fig2 (bands, history and projection); its typology panel is by-typology '
                          'reporting',
    'boss_05_annual_carbon': 'superseded by Fig3 (stages, materials) and D25 (carbon by band); typology panel removed',
    'boss_05_annual_carbon_pb': 'duplicate of D25 with a typology panel',
    'boss_06_cumulative_carbon': 'duplicate of D26 without the boundaries; typology panel removed',
    'boss_07_typology_share': 'by-typology reporting (typology shares are held; internal to the model)',
    'diag_4_floor_area': 'demand-band panel superseded by Fig2; typology, mix and per-typology size panels are '
                         'by-typology reporting',
    'diag_5_carbon': 'material panels duplicate D13; typology panels are by-typology reporting',
    'mc_1_fan': 'superseded by the Monte Carlo bands of ED5 (floor area and carbon)',
    'sens_1_tornado': 'superseded by ED1 (grouped tornado of the Reference carbon) and ED4 (levels of exceedance)',
    'pb_4_sensitivity': 'superseded by ED4; all rows in D18',
}


def all_release_files():
    """[(group, file id)] of every planned figure."""
    out = [(PAPER_GROUP, h['file']) for h in PAPER] + [(ED_GROUP, h['file']) for h in EXTENDED_DATA]
    out += [(KEY_GROUP, h['file']) for h in KEY_FIGURES]
    out += [(g, f) for g, rows in DIAGNOSTICS.items() for f, _, _ in rows]
    return out


def legacy_map():
    """v3.1 figure name -> [(group, release file id)] or [('removed', reason)]."""
    m = {}
    for grp, items in ((PAPER_GROUP, PAPER), (ED_GROUP, EXTENDED_DATA)):
        for h in items:
            for old in h['legacy']:
                m.setdefault(old, []).append((grp, h['file']))
    for g, rows in DIAGNOSTICS.items():
        for f, _, olds in rows:
            for old in olds:
                m.setdefault(old, []).append((g, f))
    for old, why in REMOVED.items():
        m.setdefault(old, []).append(('removed', why))
    return m
