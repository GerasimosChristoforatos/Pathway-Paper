"""The figure plan of MODEL v1.0.0: one entry per figure of the release (headline set in
outputs/headline/, diagnostics in outputs/diagnostics/<group>/), with its title, panels,
data source, draft caption and the v3.1 figures it replaces. tools/design_docs.py writes
docs/FIGURE_PLAN.md and the figure table of docs/RENAMING.md from it; the figure audit
test (tests/test_release.py) requires every planned file to exist and every file in
outputs/ to be indexed.

Captions are drafts: numbers in braces are filled from the data files when the figure is
drawn, never typed by hand.
"""
H = 'headline'

# ---------------------------------------------------------------------------
# Headline set (outputs/headline/): PNG 300 dpi + vector PDF, double column (183 mm)
# ---------------------------------------------------------------------------
HEADLINE = [
    dict(id='H1', file='H1_model_schematic', title='How the model works',
         panels='one panel: people -> households -> dwellings -> floor area -> embodied carbon -> AESA '
                'boundaries (AR, AtP); the demand bands branch off the dwellings step, each pathway lever '
                '(L1-L5) is attached to the band or quantity it acts on (L1 extra space; L2 vacancy, L3 2026 '
                'overbuild; L4 historical replacement and the recent replacement surge; L5 carbon per m2); TL1-TL6 shown as the limits of '
                'the same arrows; untargeted bands (population growth, smaller households) marked',
         source='naming.py, levers.py (structure only; no numbers)',
         caption='Model structure. A bottom-up chain converts population and household projections into '
                 'dwellings required, floor area by reason for building (demand bands) and embodied carbon, '
                 'which is compared with two allocations of a global carrying capacity (acquired rights, AR; '
                 'ability to pay, AtP). Pathway levers act on the band or quantity they target; population growth '
                 'and smaller households are untargeted by design.',
         legacy=[]),
    dict(id='H2', file='H2_floor_area', title='New residential floor area, 1991-2050',
         panels='(a) annual floor area built: history 1991-2025 (consents x completion rate), Reference '
                'projection 2026-2050 with the Monte Carlo 5-95% band, Low and High replacement variants; '
                '(b) cumulative floor area 2026-2050 by variant (bar) with the Monte Carlo 5-95% whisker on the '
                'Reference',
         source='data/baseline/annual.csv, data/baseline/variants_annual.csv, data/baseline/scenarios.json, '
                'data/montecarlo/annual_REF.csv, data/montecarlo/summary_REF.csv',
         caption='New residential floor area. History is consented floor area converted to built floor area; '
                 'the Reference projection builds {gfa_ref:.1f} million m2 in 2026-2050 (Monte Carlo 90% '
                 'interval {gfa_p5:.1f}-{gfa_p95:.1f}); Low and High replacement bracket the replacement '
                 'assumption ({gfa_low:.1f} and {gfa_high:.1f}).',
         legacy=['boss_03_cumulative_gfa', 'fig_scenarios', 'mc_1_fan']),
    dict(id='H3', file='H3_demand_bands', title='Why floor area is built',
         panels='annual floor area by demand band: history as one bar per census interval (interval means, '
                'one vacancy definition), Reference projection annual 2026-2050; bands stacked (they sum to '
                'the total; no separate total line); untargeted bands grey and hatched; retirement villages '
                'removed in proportion (out of scope, noted)',
         source='data/baseline/bands_annual.csv (Reference, 2026-2050), data/baseline/bands_history.csv (census '
                'intervals)',
         caption='Floor area by reason for building. Bands sum to the in-scope total. Population growth and '
                 'smaller households are untargeted; extra space, vacancy, the 2026 overbuild, historical replacement '
                 'and the recent replacement surge are the bands the pathways act on.',
         legacy=['diag_4_floor_area', 'boss_04_annual_gfa', 'fig_bridge']),
    dict(id='H4', file='H4_carbon_components', title='Embodied carbon 2026-2050 by component',
         panels='(a) annual embodied carbon of the Reference by component (materials and construction A1-A5, '
                'soil carbon loss, maintenance B2/B4 within 2026-2050), stacked, with the Monte Carlo 5-95% band '
                'of the total; (b) cumulative 2026-2050 by material (Pride-stripe order) with committed after '
                '2050 as a hatched companion range',
         source='data/baseline/annual.csv (components), data/baseline/projection.json (materials, committed), '
                'data/montecarlo/annual_REF.csv',
         caption='Embodied carbon of new residential construction. Materials and construction (A1-A5) and soil '
                 'carbon loss are counted in the construction year, maintenance (B2, B4) in the year it occurs '
                 'within 2026-2050; later events and end of life are committed after 2050 (b, hatched).',
         legacy=['boss_05_annual_carbon', 'boss_06_cumulative_carbon', 'boss_10_material_flows',
                 'diag_5_carbon']),
    dict(id='H5', file='H5_boundaries', title='Reference emissions against the AR and AtP boundaries',
         panels='(a) annual embodied carbon of the Reference (Monte Carlo band) against the annual AR and AtP '
                'boundaries; (b) cumulative level of exceedance 2026-2050, AR and AtP shown side by side as a '
                'range of principles (never averaged), for Low, Reference and High with Monte Carlo 5-95% '
                'whiskers',
         source='data/aesa/annual.csv, data/aesa/montecarlo_annual.csv, data/aesa/results.json',
         caption='Absolute sustainability. Over 2026-2050 the Reference exceeds the acquired-rights boundary '
                 '{loe_ar:.2f}-fold and the ability-to-pay boundary {loe_atp:.1f}-fold; the two allocation '
                 'principles are reported side by side and never averaged.',
         legacy=['pb_2_loe', 'boss_05_annual_carbon_pb', 'fig_scenarios_pb']),
    dict(id='H6', file='H6_committed', title='Lock-in: emissions committed after 2050',
         panels='cumulative carbon within 2026-2050 (materials and construction, soil, maintenance) and the '
                'emissions committed after 2050 (later B2/B4 and C1-C4, lower-upper range, hatched) for Low, '
                'Reference and High, in kt and in years of the 2050 AR boundary; cumulative AR and AtP budgets '
                'as lines',
         source='data/aesa/results.json (committed, budgets), data/baseline/scenarios.json',
         caption='Lock-in. The 2026-2050 cohorts commit {com_lo:,.0f}-{com_hi:,.0f} kt after 2050 (Reference), '
                 'equal to {yrs_lo:.0f}-{yrs_hi:.0f} years of the 2050 acquired-rights boundary.',
         legacy=['pb_6_committed']),
    dict(id='H7', file='H7_pathways_bands', title='What each pathway removes, by demand band',
         panels='(a) floor area and (b) carbon 2026-2050 by demand band for the Reference, P1-P5 (Moderate '
                'bars, Ambitious whiskers on the total) and TL; untargeted bands grey and hatched at the bottom',
         source='data/pathways/bands.csv, data/pathways/runs.csv',
         caption='Pathways by demand band. Each pathway acts on the bands it targets; P4 lowers carbon per m2 '
                 'of every band. TL: ' + 'hyper-optimistic theoretical limit; a thought experiment, not a pathway.',
         legacy=['pw_1_bands_by_pathway']),
    dict(id='H8', file='H8_annual_emissions', title='Annual emissions 2026-2050 against the boundaries',
         panels='one panel: Reference, P5 Moderate (solid), P5 Ambitious (dashed), TL (near-black) and TL '
                'gradual adoption (light) against the annual AR and AtP boundaries',
         source='data/pathways/annual.csv',
         caption='Annual embodied carbon of the combined pathways and the theoretical limit against the annual '
                 'boundaries. TL: hyper-optimistic theoretical limit; a thought experiment, not a pathway.',
         legacy=['pw_4_annual_SI', 'pw_10_T_annual_SI']),
    dict(id='H9', file='H9_waterfall', title='From the Reference to P5 Ambitious and TL',
         panels='order-free (Shapley) waterfall of cumulative carbon 2026-2050: Reference -> P1-P4 '
                '(Ambitious; Moderate shown as markers) -> P5 Ambitious -> full strength from 2027 -> TL1-TL6 -> '
                'TL, against the cumulative AR and AtP budgets; committed after 2050 as hatched companion bars '
                'for Reference, P5 Ambitious and TL; the TL residual to LoE AR = 1 annotated in dwellings not '
                'built and residents housed in existing dwellings',
         source='data/pathways/shapley_pathways.csv, data/pathways/shapley_theoretical_limit.csv, '
                'data/pathways/runs.csv, data/pathways/theoretical_limit.json',
         caption='Order-free attribution (Shapley values, exact). Even the theoretical limit exceeds the '
                 'acquired-rights budget: closing the residual means {dw:,.0f} dwellings not built in 2027-2050 '
                 '({res:,.0f} residents housed in existing dwellings). TL: hyper-optimistic theoretical limit; '
                 'a thought experiment, not a pathway.',
         legacy=['pw_2_shapley_waterfall', 'pw_8_staircase', 'pw_9_T_shapley_SI']),
    dict(id='H10', file='H10_solution_space', title='Solution space: demand and intensity',
         panels='cumulative LoE AR over uniform cuts of 2027-2050 floor area (demand) and of non-soil carbon '
                'per m2 (intensity) applied to the Reference: (a) the whole plane with the LoE = 1 contour and '
                '2, 3, 5, 10 contours, P1-P5 (Moderate open, Ambitious filled) and TL at their effective '
                'coordinates, back-cast points; (b) zoom on the P1-P5 markers',
         source='data/pathways/solution_space.csv, data/pathways/backcast.json, data/pathways/theoretical_limit.json '
                '(TL marker)',
         caption='Solution space (after Horup et al. 2025, Fig. 6). Markers sit at each run\'s effective '
                 'reductions of 2027-2050 floor area and non-soil carbon per m2; TL also lowers soil carbon '
                 '(TL5, TL6), which the plane does not show.',
         legacy=['pw_3_solution_space']),
    dict(id='H11', file='H11_sensitivity', title='What moves the cumulative level of exceedance',
         panels='tornado of the cumulative LoE AR 2026-2050 (Reference), the largest parameters with both '
                'ends of paired parameters: model-input rows (boundaries as adopted, as the AESA sensitivity rows) '
                'and AESA-method rows on one axis; the population rows move carbon and boundaries together',
         source='data/baseline/sensitivity_one_at_a_time.csv, data/aesa/sensitivity.csv, data/aesa/results.json '
                '(population paths)',
         caption='One-at-a-time sensitivities of the cumulative acquired-rights level of exceedance; bars are '
                 'not additive and not a joint interval.',
         legacy=['sens_1_tornado', 'pb_4_sensitivity']),
]

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
        ('D16_one_at_a_time', 'All one-at-a-time sensitivities: floor area and carbon', ['sens_1_tornado_SI']),
        ('D17_sensitivity_paths', 'Annual paths of the largest one-at-a-time sensitivities', ['sens_2_paths']),
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
        ('D29_adoption_and_variants', 'P5 under Low / Reference / High replacement and the adoption paths '
         '(full by 2030, 2035, 2045)', ['pw_5_envelope_SI']),
        ('D30_l5_estimator', 'L5 material carbon: Harrell-Davis estimator of the case-study ratios',
         ['pw_6_L5_estimator_SI']),
        ('D31_shapley_levers', 'Shapley attribution of Reference - P5 to the five levers', ['pw_7_shapley_levers_SI']),
        ('D32_tl_staircase', 'Reference -> P5 -> TL: cumulative LoE and the human terms (size, space per '
         'person, dwellings built)', ['pw_8_staircase']),
        ('D33_tl_shapley', 'Shapley attribution of P5 Ambitious (full strength from 2027) - TL to TL1-TL6',
         ['pw_9_T_shapley_SI']),
        ('D34_tl_dwellings', 'TL: dwellings built per year (banking rule) and annual carbon', ['pw_10_T_annual_SI']),
    ],
}

# v3.1 figures that are not carried into the release, with the reason (CHANGELOG)
REMOVED = {
    'boss_04_annual_gfa': 'superseded by H3 (bands, history and projection); its typology panel is by-typology '
                          'reporting',
    'boss_05_annual_carbon': 'superseded by H4 (components) and D25 (carbon by band); typology panel removed',
    'boss_05_annual_carbon_pb': 'duplicate of D25 with a typology panel',
    'boss_06_cumulative_carbon': 'duplicate of D26 without the boundaries; typology panel removed',
    'boss_07_typology_share': 'by-typology reporting (typology shares are held; internal to the model)',
    'diag_4_floor_area': 'demand-band panel superseded by H3; typology, mix and per-typology size panels are '
                         'by-typology reporting',
    'diag_5_carbon': 'material panels duplicate D13; typology panels are by-typology reporting',
    'mc_1_fan': 'superseded by the Monte Carlo bands of H2 (floor area) and H4 (carbon)',
    'sens_1_tornado': 'superseded by H11 (top parameters on the cumulative LoE AR); all rows in D16',
    'pb_4_sensitivity': 'superseded by H11; all rows in D18',
}


def all_release_files():
    """[(group, file id)] of every planned figure."""
    out = [(H, h['file']) for h in HEADLINE]
    out += [(g, f) for g, rows in DIAGNOSTICS.items() for f, _, _ in rows]
    return out


def legacy_map():
    """v3.1 figure name -> (group, release file id) or ('removed', reason)."""
    m = {}
    for h in HEADLINE:
        for old in h['legacy']:
            m.setdefault(old, []).append((H, h['file']))
    for g, rows in DIAGNOSTICS.items():
        for f, _, olds in rows:
            for old in olds:
                m.setdefault(old, []).append((g, f))
    for old, why in REMOVED.items():
        m.setdefault(old, []).append(('removed', why))
    return m
