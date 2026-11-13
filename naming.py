"""One vocabulary for the model: every name a reader sees, and the release identifiers of the data files.

* The vocabulary (SCENARIOS, STRATEGIES, SETTINGS, LEVERS, TL, ADOPTION, BANDS,
  COMPONENTS, METRICS) is the only source of reader-facing labels: figures, tables, data
  files and generated documents take their labels from here. Internal code uses the short
  IDs (REF, LOW, HIGH, VHIGH; S1-S3; pathway-moderate / pathway-ambitious; L1-L9; TL, TL1-TL9; band and
  component ids).
* identifier() gives every CSV column and JSON key its release name (columns(), keys()).
"""
import re

# ============================================================
# VOCABULARY
# ============================================================
PERIOD = '2026–2050'

# Projection and its variants. The Reference is the adopted projection with no
# interventions (S3-10 in the baseline layers, P0 in the pathway layers: one run).
SCENARIOS = {
    'REF': 'Reference',
    'LOW': 'Low replacement',
    'HIGH': 'High replacement',
    'VHIGH': 'Very High replacement (trend continues)',
    'REF_HL5': 'Reference, replacement half-life 5 yr',
    'REF_HL15': 'Reference, replacement half-life 15 yr',
    'LOW_NOUC': 'Low replacement, no census under-construction correction',
    'REF_NOUC': 'Reference, no census under-construction correction',
    'HIGH_NOUC': 'High replacement, no census under-construction correction',
}
SCENARIO_DEFINITIONS = {
    'REF': 'the adopted projection with no interventions: net replacement fades from the 2018–2023 census-interval '
           'rate to the 1991–2023 long-run rate with a 10-year half-life',
    'LOW': 'sensitivity variant of the Reference: the 1991–2023 long-run net replacement rate throughout',
    'HIGH': 'sensitivity variant of the Reference: the 2018–2023 census-interval rate persists',
    'VHIGH': 'sensitivity variant of the Reference (MODEL v3.3.0): the weighted linear trend of the census-interval '
             'net replacement rates 1991–2023 continues (OLS weighted by interval length, extrapolated 2026–2050)',
}
SCENARIO_LEGACY = {'S3-10': 'REF', 'S1': 'LOW', 'S2': 'HIGH', 'S3-5': 'REF_HL5', 'S3-15': 'REF_HL15',
                   'S1-noUC': 'LOW_NOUC', 'S3-10-noUC': 'REF_NOUC', 'S2-noUC': 'HIGH_NOUC'}

# nine rule-based levers grouped by the PAS 2080:2023 carbon reduction hierarchy (BSI 2023, Clause 4.3,
# Fig. 5: Avoid - Switch - Improve). Avoid = levers that reduce the floor area needed to house the population, system
# level (number of dwellings) before asset level (floor area per dwelling); Switch = alternative site and materials
# for the floor area that is built (carbon per m2); Improve = construction efficiencies. Order within a strategy
# follows the decision sequence (system before asset; site before materials). Ambition levels follow the 2050
# Pathways Calculator (DECC 2010; DESNZ 2023) and EUCalc (D2.5, 2020): Reference = Level 1, Moderate = Level 2,
# Ambitious = Level 3, theoretical limit = Level 4. Every lever at a setting = the Moderate / Ambitious Pathway.
STRATEGIES = {'S1': 'Avoid Strategies', 'S2': 'Switch Strategies', 'S3': 'Improve Strategy'}   # S3 has one lever
STRATEGY_LEVERS = {'S1': ('L1', 'L2', 'L3', 'L4', 'L5'), 'S2': ('L6', 'L7', 'L8'), 'S3': ('L9',)}
LEVER_STRATEGY = {L: S for S, ls in STRATEGY_LEVERS.items() for L in ls}
PATHWAY = 'pathway'                                   # run id prefix of the Moderate / Ambitious Pathway (every lever)
PATHWAY_RUNS = {'pathway-moderate': 'Moderate Pathway', 'pathway-ambitious': 'Ambitious Pathway'}
PAS2080 = ('BSI (2023) PAS 2080:2023 Carbon management in buildings and infrastructure. British Standards '
           'Institution, London; Clause 4.3 and Figure 5 (carbon reduction hierarchy: Avoid - Switch - Improve)')
SETTINGS = {'moderate': 'Moderate', 'ambitious': 'Ambitious'}
LEVELS = {'reference': 'Reference (Level 1)', 'moderate': 'Moderate (Level 2)', 'ambitious': 'Ambitious (Level 3)',
          'tl': 'Theoretical limit (Level 4)'}

LEVERS = {'L1': 'Household size', 'L2': 'Vacancy rate', 'L3': 'Building lifetime', 'L4': 'Extra space',
          'L5': 'Occupancy density', 'L6': 'Brownfield-first development', 'L7': 'Soil-aware planning',
          'L8': 'Material carbon efficiency', 'L9': 'Construction-stage carbon'}
# The rule sub-rule each lever's Ambitious level follows (METHODS_DRAFT.md): A case-study distribution (Harrell-Davis
# q0.15), B best value ever observed in NZ, C published reference value
LEVER_SUBRULE = {'L1': 'C', 'L2': 'B', 'L3': 'C', 'L4': 'B', 'L5': 'A', 'L6': 'C', 'L7': 'C', 'L8': 'A', 'L9': 'C'}
# The denser-typology-mix lever of pathways_v2 (numbered L4 in that version) was removed in
# v3.1; it is never given a lever number in the release.
DENSER_MIX = 'denser typology mix (lever of pathways_v2, removed in pathways_v3.1)'

# Theoretical limit: TLn is Level 4 of Ln
TL = {'TL': 'Theoretical Limit', 'TL1': 'Historical maximum household size', 'TL2': 'No vacancy',
      'TL3': 'No demolition', 'TL4': 'No extra space', 'TL5': 'Densest design', 'TL6': 'All brownfield',
      'TL7': 'Lowest-carbon soils', 'TL8': 'Best-practice materials', 'TL9': 'Zero-emission construction'}
TL_LIMIT_OF = {f'TL{k}': f'L{k}' for k in range(1, 10)}
TL_CAPTION = 'hyper-optimistic theoretical limit; a thought experiment, not a pathway'

# adoption paths of the levers (ADOPTION_LEGACY: the earlier 'ramp' names)
ADOPTION = {'by2035': 'full roll-out by 2035 (adopted)', 'by2030': 'full roll-out by 2030 (sensitivity)',
            'by2045': 'full roll-out by 2045 (sensitivity)', 'from2027': 'full strength from 2027'}
# TL is adopted on the same 2026 -> 2035 logistic as every level; its instant variant (every limit
# from 1 January 2027) is one sensitivity row
TL_INSTANT = 'TL, all limits from 1 January 2027 (instant)'
TL_REOCCUPATION_LINE = 'released dwellings re-occupied at a constant share of each year\'s need'


def tl_caption(share):
    """The TL caption with the constant share s of each year's need (share 0-1)."""
    return ('TL: every lever at Level 4, adopted by 2035; dwellings released by TL3 (household size) and TL4 (zero '
            f'vacancy) are re-occupied gradually, meeting a constant share (~{100 * share:.0f}%) of each year\'s '
            'need; 2026 observed.')

# Demand bands (why floor area is built), bottom to top. Retirement villages are a
# bookkeeping row (out of scope), never a band in figures.
BANDS = {'growth': 'Population growth',
         'smaller_households': 'Smaller households',
         'extra_space': 'Extra space',
         'vacancy': 'Vacancy',
         'overbuild_2026': '2026 overbuild',
         'overbuild_absorbed': 'Overbuild absorbed',
         'replacement': 'Demolition replacement',
         'unconsented': 'Unconsented additions',
         'redevelopment': 'Recent replacement surge',
         'released_tl': 'Released dwellings (TL)',
         'vacancy_released': 'Vacancy released',
         'surplus_vacant': 'Surplus kept vacant (2050)',
         'maintenance': 'Maintenance (B2, B4), 2026–2050'}
# bands whose values are negative by construction (drawn as outlined segments hanging from the
# top of the positive stack; the data keep the sign); 'Vacancy released': bands.py
NEGATIVE_BANDS = ('overbuild_absorbed', 'unconsented', 'vacancy_released', 'released_tl')
# the household-size band is signed, d_hh x occupied area - population growth x OLF: positive when households
# dilute, negative when they consolidate
SIGNED_BANDS = ('smaller_households',)
BAND_DETAIL = {'replacement_demolition': 'Historical replacement: demolition (BRANZ rate)',
               'replacement_residual': 'Historical replacement: net unconsented additions (calibrated residual)',
               'retirement_villages': 'Retirement villages (out of scope)',
               # history (census intervals): the net replacement observed in the dwelling counts holds the
               # long-run rate and any surge above it; the two are not separable before the projection
               'replacement_history': 'Net replacement (history; historical replacement and recent surge not '
                                      'separable)'}
BAND_DETAIL['replacement_census'] = 'Net replacement (census)'
BAND_DETAIL['unexplained'] = 'Unexplained building'
# the history's residual band is split into the census-measured net replacement (may be negative),
# the retirement-village units (negative, out of scope) and the unexplained remainder (may be negative); the bands add
# up to the observed in-scope floor area built in every census interval
BANDS_HISTORY = ('growth', 'smaller_households', 'extra_space', 'vacancy', 'replacement_census', 'retirement_villages',
                 'unexplained')
NEGATIVE_BANDS_HISTORY = ('retirement_villages',)       # negative by construction; census replacement and the
                                                        # unexplained remainder may be negative in an interval
BAND_DEFINITIONS = {
    'growth': 'population growth at the occupied area per person, net of consolidation (untargeted)',
    'smaller_households': 'additional households from falling household size (targeted by L1 Household size, S1 Avoid)',
    'extra_space': 'new-dwelling size above the occupied area (household size x floor area per design occupant)',
    'vacancy': 'the vacancy allowance on new households and the change in the vacancy rate',
    'overbuild_2026': 'observed 2026 building above the requirement, continuing above it in 2027-2050 at the '
                      'persistence rho (the market excess)',
    'overbuild_absorbed': 'the starting surplus (2024-2025, carried into 2026) and the cumulative overbuild absorbed '
                          'by building less, logistic 2026 -> 2035 (negative; MODEL v3.0.0 Reference, the starting '
                          'surplus from MODEL v4.4)',
    'replacement': 'demolition replacement at the fixed BRANZ SR214 rate (0.135% of the stock a year)',
    'unconsented': 'unconsented additions: the calibrated long-run residual of the census dwelling-count identity '
                   '(negative: dwellings that appear without a new-dwelling consent)',
    'released_tl': 'existing dwellings released by TL3 (household size) and TL4 (zero vacancy) and re-occupied '
                   '(negative; theoretical limit only)',
    'redevelopment': 'the scenario rate above that long-run rate: the 2018–2023 knock-down-and-rebuild wave, fading '
                     'in the Reference',
    'maintenance': 'replacement and repaint events (B2, B4) of the new buildings within 2026–2050 (carbon only)',
    'vacancy_released': 'existing dwellings released by a fall in the vacancy rate (a run without any lever at its '
                        'theoretical limit), used in the year they occur up to the gross need, the rest carried '
                        '(negative; MODEL v3.1.0/v3.2.0)',
    'surplus_vacant': 'released dwellings still unusable in 2050, kept vacant (booked in 2050 against the release '
                      'bands, so the bands add up to the total every year)',
}
UNTARGETED = ('growth',)          # smaller households are targeted by L1 Household size (S1 Avoid)

COMPONENTS = {'materials_construction': 'Materials and construction (A1–A5)',
              'soil': 'Soil carbon loss',
              'maintenance': 'Maintenance (B2, B4), 2026–2050',
              'committed': 'Committed after 2050 (later B2/B4 and C1–C4)'}
UPFRONT = 'Upfront (A1–A5 and soil carbon loss)'
# life-cycle stages of the carbon (Fig3a)
STAGES = {'a1a3': 'Materials (A1–A3)', 'a4a5': 'Construction (A4–A5)',
          'maintenance': 'Maintenance (B2, B4)',
          'soil': 'Soil carbon loss'}
UNTARGETED_GROUP = 'Untargeted: population growth'
UNEXPLAINED = 'Unexplained building (history; may be negative)'
REPLACEMENT_CENSUS = 'Net replacement, census-measured (history)'

METRICS = {'AR': 'Acquired rights (AR)', 'AtP': 'Ability to pay (AtP)', 'LoE': 'Level of exceedance (LoE)',
           'cumulative_LoE': 'Cumulative level of exceedance, 2026–2050'}

# The one wording of the vacancy assumption (author decision), filled from the data by
# vacancy_wording(): the parameter is the published 2023 census value; on the consistent 1986-2023
# definition (pooled 2018/2023 empty share of unoccupied dwellings) 2023 is the series maximum.
VACANCY_WORDING = ('the vacancy-rate parameter is held at its published 2023 census value ({v0:.2f}%; on the '
                   'consistent definition 2023 is the series maximum, {vmax:.2f}%, minimum {vmin:.2f}% in {ymin}); '
                   'the starting surplus and the 2026 overbuild raise implied stock vacancy temporarily and are '
                   'absorbed by 2035, so implied '
                   'vacancy returns to the parameter ({v2050:.2f}% in 2050)')


def vacancy_wording(v0, vmax, vmin, ymin, v2050):
    """The release wording of the vacancy assumption (fractions in, percent out)."""
    return VACANCY_WORDING.format(v0=100 * v0, vmax=100 * vmax, vmin=100 * vmin, ymin=ymin, v2050=100 * v2050)


# display names of the sensitivity inputs, one source for the Fig7a tornado, ED4 (one at a time, carbon),
# ED5 (boundary definitions, LoE), ED6 (Monte Carlo inputs) and ED7 (Sobol). Two lines where long (centred on one
# axis by figures.draw.centre_ticklabels). The same input carries the same label everywhere.
INPUT_LABEL = {
    'population': 'Population\n(5th–95th pct.)',
    'hh_propensity': 'Living arrangements: propensities\nchange (Stats NZ B)',
    'hh_pace': 'Household size\n(2018–23 pace)',
    'hh_after2048_flat': 'After 2048: held flat\n(zero slope)',
    'hh_after2048_endslope': 'After 2048:\nPCHIP end slope',
    'completion_rate': 'Completion rate\n(0.93–0.96)',
    'uc_correction': 'Census under-construction\ncorrection removed',
    'size_window': 'Dwelling-size reference\nwindow 2016–2025',
    'start_surplus_none': 'No starting surplus\n(2024–25 excess not carried)',
    'start_surplus_m2sd': 'Starting surplus\nminus 2 SD',
    'overbuild_timing': 'Surplus absorbed\n(by 2030–by 2045)',
    'vacancy_mean': 'Vacancy rate: 1986–2023\ncensus mean',
    'overbuild_redev': '2026 overbuild booked as\nstock-neutral redevelopment',
    'overbuild_gap': '2026 overbuild measured\nagainst the 2026 need',
    'completion_lag': 'Completion lag\n(15–19 months)',
    'no_2026': 'No 2026 data\n(consents to Dec 2025)',
    'replacement': 'Replacement\n(Low–Very High)',
    'half_life': 'Replacement half-life\n(5–15 yr)',
    'single_case': 'Single case study\n(lowest–highest)',
    'jackknife': 'Carbon factors\n(jackknife)',
    'frozen': 'Frozen technology\n(2025 factors held)',
    'proxy_held': 'Proxy-mapped items\nheld at 2025 factors',
    'nz_made_held': 'NZ-made electricity-intensive\nitems held at 2025 factors',
    'soil_order': 'Soil order\n(Raw–Organic)',
    'a4a5': 'A4–A5 decarbonisation\n(own path–held at 2025)',
    'soil_all': 'Soil carbon loss on all\nfloor area, incl. replacement',
    'event_timing': 'B2/B4 event spacing\n(L/n, not L/(n+1))',
    'carrying_capacity': 'Carrying capacity:\n1 W/m² boundary (not 2 °C)',
    'global_impact_ef31': 'Global impact:\nEF 3.1',
    'gdp_current': 'Economic allocation measure:\nGDP per capita, current US$',
    'alpha_1': 'Allocation exponent\nα = 1',
    'sector_share': 'Sector share: ratio of sums\n(not mean of ratios)',
    'pop_source_raw': 'Population source: Stats NZ\n2024-base median, unadjusted',
    'pop_source_wpp': 'Population source:\nUN WPP 2024 median',
    'rollout': 'Full roll-out\n(by 2030–by 2045)',
    'all_ambitious': 'Every lever at Ambitious\n(Ambitious Pathway)',
    'all_tl': 'Every lever at its limit\n(Theoretical Limit)',
}
AR_WINDOW_LABEL = 'AR base window\n({short}–{long} yr)'
# ED4 / ED5 group headers (in this order)
SENSITIVITY_GROUPS = ('Demographics', 'Housing stock & calibration', 'Completion lag', 'Replacement',
                      'Carbon factors & technology', 'Accounting')
BOUNDARY_SENSITIVITY_GROUPS = ('Carrying capacity', 'Global impact', 'AR base window', 'Economic allocation', 'Population', 'Replacement')
# Monte Carlo inputs (ED6 panel titles, ED7 rows): the same input names as the tornado rows, without their ranges
MC_INPUT = {'z_pop': 'Population and household size',     # MODEL v4.3.1 (B4): one z draws both (Stats NZ variants)
            'size': 'Dwelling size', 'complete': 'Completion rate', 'carbon': 'Carbon factors',
            'half_life': 'Replacement half-life'}
LOE_AR = 'Cumulative LoE of AR'
TL_AGE_STANDARDISED = 'Theoretical Limit, TL1 age-standardised (sensitivity)'   # pathways.TL_AGE_STANDARDISED
LOE_ATP = 'Cumulative LoE of AtP'

def run_label(run, scenario='REF'):
    """Reader-facing label of a pathway-layer run id (release ids: REF/LOW/HIGH/VHIGH, S1-moderate,
    L2-ambitious, pathway-moderate, pathway-moderate-by2030, TL)."""
    if run in SCENARIOS:
        return SCENARIOS[run]
    if run == 'TL':
        return TL['TL']
    if run == 'TL-from2027':
        return TL_INSTANT
    if run == 'TL-TL1-age-standardised':
        return TL_AGE_STANDARDISED
    parts = run.split('-')
    head, setting = parts[0], parts[1] if len(parts) > 1 else None
    if head == PATHWAY:
        out = PATHWAY_RUNS[f'{PATHWAY}-{setting}']
    else:
        out = f'{head} {STRATEGIES.get(head) or LEVERS.get(head)}' + (f', {SETTINGS[setting]}' if setting else '')
    rest = '-'.join(parts[2:])
    if rest in ('by2030', 'by2045'):
        out += f', {ADOPTION[rest]}'
    elif rest == 'apartments-held':
        out += ', apartments held'
    return out


# Demand bands as the data files list them. 'with_retirement_villages' (projection.json,
# bands.csv): every band of the projection's bookkeeping, replacement split into demolition
# and net unconsented additions, and the retirement-village row (negative: households housed
# in retirement villages, out of scope). 'in_scope' (bands.csv, the band figures): retirement
# villages removed from every band in proportion, replacement one band, maintenance a carbon band.
# '2026 overbuild' split into the market excess (positive) and 'Overbuild absorbed' (negative);
# in scope, 'Historical replacement' split into 'Demolition replacement' and 'Unconsented additions' (negative);
# the theoretical-limit runs add 'Released dwellings (TL)' (negative; *_TL lists).
BANDS_WITH_RETIREMENT_VILLAGES = ('growth', 'smaller_households', 'extra_space', 'vacancy',
                                  'replacement_demolition', 'replacement_residual', 'redevelopment',
                                  'overbuild_2026', 'overbuild_absorbed', 'retirement_villages')
# one in-scope band list for every run (bands.IN_SCOPE; release bands zero where a run has no release)
BANDS_IN_SCOPE = ('growth', 'smaller_households', 'extra_space', 'vacancy', 'overbuild_2026', 'replacement',
                  'redevelopment', 'overbuild_absorbed', 'unconsented', 'vacancy_released', 'released_tl',
                  'surplus_vacant', 'maintenance')
BANDS_WITH_RETIREMENT_VILLAGES_TL = BANDS_WITH_RETIREMENT_VILLAGES[:-1] + ('released_tl', 'retirement_villages')
BANDS_IN_SCOPE_TL = BANDS_IN_SCOPE
BAND_DEFINITION_IDS = ('with_retirement_villages', 'in_scope')


def band_data_label(band_id):
    """The label of a band in the data files (ASCII: en dash -> hyphen)."""
    return _ascii({**BANDS, **BAND_DETAIL}[band_id])


def _ascii(s):
    """Data files keep ASCII identifiers: en dash -> hyphen."""
    return s.replace('\u2013', '-')


# ============================================================
# EXPORT: release identifiers at write time
# ============================================================
# The model code names quantities with short tokens (gfa, soil_kt, b_inwindow, ...); the
# files carry the release names. Every CSV and JSON file of the model is written through
# columns() or keys(), which apply identifier() (the generic rules _ID_RULES), so one function
# names every output. Vocabulary
# identifiers (scenario, pathway, lever, setting, band and TL ids) are the release ids in
# the code itself.
def columns(df):
    """df with the release column names (identifier on every column; collisions refused)."""
    new = [identifier(c) if isinstance(c, str) else c for c in df.columns]
    if len(set(new)) != len(new):
        raise ValueError(f'naming.columns: two columns map to one release name: {list(df.columns)}')
    return df.set_axis(new, axis=1)


def keys(obj):
    """obj with the release JSON keys (identifier on every string key, recursively; collisions
    refused). Lists and tuples become lists, as json.dump writes them."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nk = identifier(k) if isinstance(k, str) else k
            if nk in out:
                raise ValueError(f'naming.keys: two keys map to {nk!r}')
            out[nk] = keys(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [keys(v) for v in obj]
    return obj


# ============================================================
# RELEASE IDENTIFIERS
# ============================================================
# --- identifiers inside files -------------------------------------------------
# Whole-identifier substitutions for column names and JSON keys (applied in order; each a
# regular expression on '_'-separated tokens). Equation symbols of the AESA (I_sec, B_AR,
# B_AtP, SOS, I_glob, alpha, g_W, g_NZ, s_sec, LoE) are kept: they are the published
# notation of Horup et al. (2025) and Hjalsted et al. (2021).
_ID_RULES = [
    (r'(?<![A-Za-z])(?:gfa|GFA)(?![A-Za-z])', 'floor_area'),
    (r'_vs_P0(?=_|$)', '_vs_reference'),
    (r'^P0_', 'reference_'),
    (r'share_of_P0_minus_P5', 'share_of_reference_minus_P5'),
    (r'share_of_P5s_instant_minus_T', 'share_of_P5_ambitious_from2027_minus_TL'),
    (r'equivalent_cut_vs_P0_', 'equivalent_cut_vs_reference_'),
    (r'(?<![A-Za-z])[bB]_inwindow', 'maintenance'),
    (r'b_share_inwindow', 'maintenance_share'),
    (r'near_term_join', 'overbuild_2026'),
    (r'(?<![A-Za-z])join_excess_2026', 'overbuild_2026_excess'),
    (r'(?<![A-Za-z])join_excess_2027', 'overbuild_2026_gap_ref'),
    (r'(?<![A-Za-z])join_net_2026_2050', 'overbuild_2026_net_dwellings'),
    (r'(?<![A-Za-z])join_2026_2050', 'overbuild_2026_dwellings_2026_2050'),
    (r'_S3_10(?=_|$)', '_REF'),
    (r'(?<![A-Za-z0-9_])soil_kt', 'soil_carbon_loss_kt'),
    (r'(?<![A-Za-z0-9_])a13_kt', 'a1a3_kt'),
    (r'(?<![A-Za-z0-9_])a45_kt', 'a4a5_kt'),
    (r'committed_B_', 'committed_b2b4_'),
    (r'committed_C_', 'committed_c1c4_'),
    (r'^within_window_kt$', 'carbon_2026_2050_kt'),
    (r'^pop_band_', 'population_band_'),
    (r'^s3_half_life$', 'replacement_half_life'),
    (r'(?<![A-Za-z0-9])reference_s3_10(?![A-Za-z0-9])', 'reference'),      # hindcast method (validation)
    (r'_to_P0(?=_|$)', '_to_reference'),
    (r'near_term_surplus_absorbed', 'overbuild_2026_absorbed'),
    (r'^join_net$', 'overbuild_2026_net_dwellings'),
    (r'(?<![A-Za-z])RV_(?=units|floor_area)', 'retirement_village_'),
    # Monte Carlo: 'central' is the deterministic Reference run (metrics.json, montecarlo_summary)
    (r'^central_pct_(GFA|floor_area|carbon)$', r'reference_percentile_\1'),
    (r'^central_pct$', 'reference_percentile'),
]



def month_year(iso, missing=None):
    """'2026-09-01' -> 'September 2026' (the one month formatter of the figures and reports). A missing date returns
    `missing` when given, else stops."""
    import calendar
    if not iso:
        if missing is None:
            raise SystemExit('naming.month_year: no date.')
        return missing
    return f'{calendar.month_name[int(str(iso)[5:7])]} {str(iso)[:4]}'

def identifier(name):
    """Release name of a v3.1 column name or JSON key (generic rules)."""
    out = str(name)
    for pat, rep in _ID_RULES:
        out = re.sub(pat, rep, out)
    return out


def typeset(text):
    """Print typography for reader-facing text built from ASCII sources (figure_plan.py, data labels):
    ranges with an en dash (1991-2050, 8,208-8,969, A1-A5, C1-C4), m² and CO₂e. Data files keep
    ASCII hyphens."""
    import re
    text = re.sub(r'(?<=\d)-(?=\d)', '–', text)
    text = re.sub(r'\b(\d+(?:st|nd|rd|th))-(\d+(?:st|nd|rd|th))\b', r'\1–\2', text)      # 5th-95th
    text = re.sub(r'\b([A-D]\d)-([A-D]\d)\b', r'\1–\2', text)
    text = re.sub(r'\bm2\b', 'm²', text)
    return re.sub(r'\bCO2e\b', 'CO₂e', text)
