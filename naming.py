"""One vocabulary for the model (MODEL v1.0.0): every name a reader sees, and the map from
the names of commit ee37ef1 (pathways v3.1) to the release names.

* The vocabulary (SCENARIOS, PATHWAYS, SETTINGS, LEVERS, TL, ADOPTION, BANDS,
  COMPONENTS, METRICS) is the only source of reader-facing labels: figures, tables, data
  files and generated documents take their labels from here. Internal code uses the short
  IDs (REF, LOW, HIGH; P1-P5; L1-L5; TL, TL1-TL6; band and component ids).
* LEGACY maps every identifier of the captured outputs (tests/regression_model_v1.json)
  to its release location: file, CSV column, identifying cell, JSON path. It is used by
  tests/test_regression_model_v1.py, which requires every captured number to be
  reproduced at its mapped location, and by tools/renaming_doc.py, which writes the
  complete old -> new table, docs/RENAMING.md. One map serves both, so the documented
  renaming is exactly the one the test enforces.
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
}
SCENARIO_LEGACY = {'S3-10': 'REF', 'S1': 'LOW', 'S2': 'HIGH', 'S3-5': 'REF_HL5', 'S3-15': 'REF_HL15',
                   'S1-noUC': 'LOW_NOUC', 'S3-10-noUC': 'REF_NOUC', 'S2-noUC': 'HIGH_NOUC'}
FROZEN = 'Frozen technology (2025 carbon factors held; check run)'

PATHWAYS = {'P1': 'Right-sized dwellings', 'P2': 'Occupied stock', 'P3': 'Retained stock',
            'P4': 'Low-carbon materials', 'P5': 'Combined'}
SETTINGS = {'moderate': 'Moderate', 'ambitious': 'Ambitious'}
SETTING_LEGACY = {'central': 'moderate', 'stretch': 'ambitious'}

# Levers (renumbered): new id -> label; LEVER_LEGACY: v3.1 id -> new id
LEVERS = {'L1': 'Dwelling size', 'L2': 'Vacancy rate', 'L3': 'Overbuild absorption',
          'L4': 'Building retention', 'L5': 'Material carbon'}
LEVER_LEGACY = {'L1': 'L1', 'L2a': 'L2', 'L2b': 'L3', 'L3': 'L4', 'L5': 'L5'}
PATHWAY_LEVERS = {'P1': ('L1',), 'P2': ('L2', 'L3'), 'P3': ('L4',), 'P4': ('L5',)}
# The denser-typology-mix lever of pathways_v2 (numbered L4 in that version) was removed in
# v3.1; it is never given a lever number in the release, because L4 is now Building retention.
DENSER_MIX = 'denser typology mix (lever of pathways_v2, removed in pathways_v3.1)'

TL = {'TL': 'Theoretical limit', 'TL1': 'No vacancy', 'TL2': 'No extra space', 'TL3': 'Minimum space per person',
      'TL4': 'Best-practice materials', 'TL5': 'Lowest-carbon soils', 'TL6': 'Urban infill'}
TL_LEGACY = {'T': 'TL', 'T1': 'TL1', 'T2': 'TL2', 'T3': 'TL3', 'T4': 'TL4', 'T5': 'TL5', 'T6': 'TL6'}
TL_CAPTION = 'hyper-optimistic theoretical limit; a thought experiment, not a pathway'
TL_GRADUAL = 'TL, gradual adoption (SI)'

# adoption paths of the levers (v3.1 'ramp' names)
ADOPTION = {'by2035': 'full roll-out by 2035 (adopted)', 'by2030': 'full roll-out by 2030 (sensitivity)',
            'by2045': 'full roll-out by 2045 (sensitivity)', 'from2027': 'full strength from 2027'}
ADOPTION_LEGACY = {'ramp2035': 'by2035', 'ramp2030': 'by2030', 'ramp2045': 'by2045', 'instant': 'from2027'}

# Demand bands (why floor area is built), bottom to top. Retirement villages are a
# bookkeeping row (out of scope), never a band in figures.
BANDS = {'growth': 'Population growth',
         'smaller_households': 'Smaller households',
         'extra_space': 'Extra space',
         'vacancy': 'Vacancy',
         'overbuild_2026': '2026 overbuild',
         'replacement': 'Replacement',
         'redevelopment': 'Redevelopment',
         'maintenance': 'Maintenance (B2, B4), 2026–2050'}
BAND_DETAIL = {'replacement_demolition': 'Replacement: demolition (BRANZ rate)',
               'replacement_residual': 'Replacement: net unconsented additions (calibrated residual)',
               'retirement_villages': 'Retirement villages (out of scope)',
               # history (census intervals): the net replacement observed in the dwelling counts holds the
               # long-run rate and any redevelopment; the two are not separable before the projection
               'replacement_history': 'Replacement and redevelopment (history; not separable)'}
BANDS_HISTORY = ('growth', 'smaller_households', 'extra_space', 'vacancy', 'replacement_history')
BAND_DEFINITIONS = {
    'growth': 'population growth at the occupied area per person, net of consolidation (untargeted)',
    'smaller_households': 'additional households from falling household size (untargeted)',
    'extra_space': 'new-dwelling size above the occupied area (household size x floor area per design occupant)',
    'vacancy': 'the vacancy allowance on new households and the change in the vacancy rate',
    'overbuild_2026': 'observed 2026 building above the requirement, fading at the persistence rho; never absorbed',
    'replacement': 'long-run net replacement: demolition net of unconsented additions (the census identifies only '
                   'their sum)',
    'redevelopment': 'the recent redevelopment wave: net replacement above the long-run rate, fading',
    'maintenance': 'replacement and repaint events (B2, B4) of the new buildings within 2026–2050 (carbon only)',
}
UNTARGETED = ('growth', 'smaller_households')

COMPONENTS = {'materials_construction': 'Materials and construction (A1–A5)',
              'soil': 'Soil carbon loss',
              'maintenance': 'Maintenance (B2, B4), 2026–2050',
              'committed': 'Committed after 2050 (later B2/B4 and C1–C4)'}
UPFRONT = 'Upfront (A1–A5 and soil carbon loss)'

METRICS = {'AR': 'Acquired rights (AR)', 'AtP': 'Ability to pay (AtP)', 'LoE': 'Level of exceedance (LoE)',
           'cumulative_LoE': 'Cumulative level of exceedance, 2026–2050'}

# The one wording of the vacancy assumption (author decision, MODEL v1.0.0), filled from the data by
# vacancy_wording(): the parameter is the published 2023 census value; on the consistent 1986-2023
# definition (pooled 2018/2023 empty share of unoccupied dwellings) 2023 is the series maximum.
VACANCY_WORDING = ('the vacancy-rate parameter is held at its published 2023 census value ({v0:.2f}%; on the '
                   'consistent definition 2023 is the series maximum, {vmax:.2f}%, minimum {vmin:.2f}% in {ymin}); '
                   'implied stock vacancy rises to ≈{v2050:.1f}% because the 2026 overbuild is not absorbed')


def vacancy_wording(v0, vmax, vmin, ymin, v2050):
    """The release wording of the vacancy assumption (fractions in, percent out)."""
    return VACANCY_WORDING.format(v0=100 * v0, vmax=100 * vmax, vmin=100 * vmin, ymin=ymin, v2050=100 * v2050)


def scenario_label(code):
    return SCENARIOS[code]


def run_label(run, scenario='REF'):
    """Reader-facing label of a pathway-layer run id (release ids: REF/LOW/HIGH, P1-moderate,
    L2-ambitious, P5-moderate-by2030, P4-moderate-apartments-held, TL, TL-gradual)."""
    if run in SCENARIOS:
        return SCENARIOS[run]
    if run == 'TL':
        return f"TL {TL['TL']}"
    if run == 'TL-gradual':
        return TL_GRADUAL
    parts = run.split('-')
    head, setting = parts[0], parts[1] if len(parts) > 1 else None
    name = f'{head} {PATHWAYS.get(head) or LEVERS.get(head)}'
    out = name + (f', {SETTINGS[setting]}' if setting else '')
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
BANDS_WITH_RETIREMENT_VILLAGES = ('growth', 'smaller_households', 'extra_space', 'vacancy',
                                  'replacement_demolition', 'replacement_residual', 'redevelopment',
                                  'overbuild_2026', 'retirement_villages')
BANDS_IN_SCOPE = ('growth', 'smaller_households', 'extra_space', 'vacancy', 'replacement', 'redevelopment',
                  'overbuild_2026', 'maintenance')
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
# columns() or keys(), which apply identifier() (the generic rules of docs/RENAMING.md), so
# one function names every output and the regression test checks the same map. Vocabulary
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
# LEGACY MAP (ee37ef1 -> release)
# ============================================================
_SCEN_FILE = {'S3-10': 'REF', 'S1': 'LOW', 'S2': 'HIGH'}


def _file(old):
    """outputs/<old> -> outputs/<new> (paths relative to outputs/)."""
    frozen = old.startswith('frozen/')
    o = old[len('frozen/'):] if frozen else old
    base = 'data/frozen_technology/' if frozen else 'data/'
    m = re.fullmatch(r'montecarlo_(summary|draws|annual|sobol)(?:_(S3-10|S1|S2))?\.csv', o)
    if m:
        return f"{base}montecarlo/{m.group(1)}_{_SCEN_FILE.get(m.group(2), 'REF')}.csv"
    simple = {'boss_results.json': 'baseline/projection.json', 'metrics.json': 'metrics.json',
              'replacement_scenarios.json': 'baseline/scenarios.json', 'validation.json': 'baseline/validation.json',
              'gap_2026.json': 'baseline/gap_2026.json', 'near_term_join.json': 'baseline/overbuild_2026.json',
              'reality_checks.json': 'baseline/reality_checks.json',
              'reconciliation.json': 'baseline/reconciliation.json',
              'sensitivity_oat.csv': 'baseline/sensitivity_one_at_a_time.csv',
              'pb_annual.csv': 'aesa/annual.csv', 'pb_mc_annual.csv': 'aesa/montecarlo_annual.csv',
              'pb_sensitivity.csv': 'aesa/sensitivity.csv', 'pb_results.json': 'aesa/results.json',
              'pathways/pathways_runs.csv': 'pathways/runs.csv',
              'pathways/pathways_annual.csv': 'pathways/annual.csv',
              'pathways/pathways_bands.csv': 'pathways/bands.csv',
              'pathways/shapley_pathways.csv': 'pathways/shapley_pathways.csv',
              'pathways/shapley_levers.csv': 'pathways/shapley_levers.csv',
              'pathways/shapley_subsets.csv': 'pathways/shapley_subsets.csv',
              'pathways/shapley_T.csv': 'pathways/shapley_theoretical_limit.csv',
              'pathways/shapley_T_subsets.csv': 'pathways/shapley_theoretical_limit_subsets.csv',
              'pathways/backcast.json': 'pathways/backcast.json',
              'pathways/solution_space.csv': 'pathways/solution_space.csv',
              'pathways/levers.json': 'pathways/levers.json',
              'pathways/t_limit.json': 'pathways/theoretical_limit.json'}
    if o in simple:
        return base + simple[o]
    if o.startswith('factors/'):
        return base + o
    raise KeyError(f'No release location for outputs/{old}')


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


def identifier(name):
    """Release name of a v3.1 column name or JSON key (generic rules)."""
    out = str(name)
    for pat, rep in _ID_RULES:
        out = re.sub(pat, rep, out)
    return out


def _lever_token(t):
    m = re.fullmatch(r'(L1|L2a|L2b|L3|L5)', t)
    return LEVER_LEGACY[t] if m else t


def run_id(old, scenario=None):
    """v3.1 pathway-layer run id -> release run id. P0 is the projection without
    interventions of its scenario (REF / LOW / HIGH)."""
    if old == 'P0':
        return _SCEN_FILE.get(scenario, 'REF') if scenario else 'REF'
    if old == 'T':
        return 'TL'
    if old == 'T-ramp':
        return 'TL-gradual'
    if old == 'none':
        return 'none'
    m = re.fullmatch(r'(P[1-5]|L1|L2a|L2b|L3|L5)-(central|stretch)(?:-(ramp2030|ramp2045|aptheld|instant))?', old)
    if not m:
        raise KeyError(f'Unknown run id {old!r}')
    head = _lever_token(m.group(1))
    out = f'{head}-{SETTING_LEGACY[m.group(2)]}'
    tail = m.group(3)
    if tail in ('ramp2030', 'ramp2045'):
        out += '-' + ADOPTION_LEGACY[tail]
    elif tail == 'aptheld':
        out += '-apartments-held'
    elif tail == 'instant':
        out += '-from2027'
    return out


def lever_set(old):
    """v3.1 'levers' cell (e.g. 'L2a:central+L2b:central', 'P5-stretch+T1+...+T6', 'P0')."""
    if old == 'P0':
        return 'none'
    out = []
    for part in old.split('+'):
        if ':' in part:
            lev, s = part.split(':')
            out.append(f'{LEVER_LEGACY[lev]}:{SETTING_LEGACY[s]}')
        elif part in TL_LEGACY:
            out.append(TL_LEGACY[part])
        else:
            out.append(run_id(part))
    return '+'.join(out)


def subset_label(old):
    """Shapley subset labels: 'P1+P3', 'L2a', 'T[T1+T3]', 'P5-stretch-instant', 'none'."""
    if old == 'none':
        return 'none'
    if old == 'P5-stretch-instant':
        return 'P5-ambitious-from2027'
    if old == 'T':
        return 'TL'
    m = re.fullmatch(r'T\[(.*)\]', old)
    if m:
        return 'TL[' + '+'.join(TL_LEGACY[t] for t in m.group(1).split('+')) + ']'
    return '+'.join(_lever_token(t) for t in old.split('+'))


_BAND_LEGACY = {
    # boss_results definition (with the retirement-village row) and Boss reporting labels
    'Growth (net of consolidation)': BANDS['growth'],
    'House-splitting': BANDS['smaller_households'],
    'Extra space per dwelling': BANDS['extra_space'],
    'Vacancy allowance': BANDS['vacancy'],
    'Demolition replacement': BAND_DETAIL['replacement_demolition'],
    'Calibrated stock residual (long run)': BAND_DETAIL['replacement_residual'],
    'Redevelopment wave (scenario - long run)': BANDS['redevelopment'],
    'Near-term market excess': BANDS['overbuild_2026'],
    'Housed in RV units (out of scope)': BAND_DETAIL['retirement_villages'],
    # in-scope figure definition
    'Growth demand (net of consolidation)': BANDS['growth'],
    'House-splitting demand': BANDS['smaller_households'],
    'Consumption: extra space per dwelling': BANDS['extra_space'],
    'Consumption: vacancy allowance': BANDS['vacancy'],
    'Replacement: long-run background (net of unconsented additions)': BANDS['replacement'],
    'Replacement: recent redevelopment wave (fading)': BANDS['redevelopment'],
    'Near-term market excess (2026 observed building above requirement, fading at rho)': BANDS['overbuild_2026'],
    'Replacements & repaints, within 2026-2050': BANDS['maintenance'],
}
BAND_DEFINITION_LEGACY = {'boss_results': 'with_retirement_villages', 'in_scope_figure': 'in_scope'}


def band_label(old):
    return _BAND_LEGACY[old]


# Cell maps for identifying CSV columns, per v3.1 file (paths relative to outputs/; the
# frozen-technology copies use the same maps). A value is mapped with the row's other
# identifying cells available (P0 needs its scenario).
def _cell(old_file, col, value, row):
    f = old_file[len('frozen/'):] if old_file.startswith('frozen/') else old_file
    if value is None:
        return None
    if col == 'scenario' and f in ('pb_annual.csv', 'pb_mc_annual.csv', 'pathways/pathways_runs.csv',
                                    'pathways/pathways_annual.csv', 'pathways/pathways_bands.csv'):
        return SCENARIO_LEGACY.get(value, value)                    # 'history' stays
    if f.startswith('pathways/'):
        if col == 'run':
            return run_id(value, row.get('scenario'))
        if col == 'setting':
            return {'central': 'moderate', 'stretch': 'ambitious', 'T': 'TL'}[value]
        if col == 'ramp':
            return ADOPTION_LEGACY[value]
        if col == 'levers':
            return lever_set(value)
        if col == 'band':
            return _ascii(band_label(value))
        if col == 'definition':
            return BAND_DEFINITION_LEGACY[value]
        if col == 'level':
            return {'T': 'TL'}.get(value, value)
        if col == 'player':
            return {'instant start': 'from2027'}.get(value, TL_LEGACY.get(value, _lever_token(value)))
        if col == 'name':
            return _ascii(_player_name(value))
        if col == 'subset':
            return subset_label(value)
    if (f.startswith('montecarlo_summary') and col == 'Unnamed: 0') or (f.startswith('montecarlo_sobol')
                                                                        and col == 'output'):
        return identifier(value)                    # output names, as the draws columns
    if f == 'sensitivity_oat.csv' and col in ('group', 'case'):
        return _ascii(_sens_label(value))
    if f == 'pb_sensitivity.csv' and col == 'label':
        return _ascii(_pb_sens_label(value))
    return value


_PLAYER_NAMES = {
    # pathways (v3.1 names) and levers
    'Right-size space': PATHWAYS['P1'], 'Occupy the existing stock': PATHWAYS['P2'], 'Keep and reuse': PATHWAYS['P3'],
    'Build better': PATHWAYS['P4'], 'Right-sized new dwellings': LEVERS['L1'], 'Lower vacancy': LEVERS['L2'],
    'Near-term surplus absorbed': LEVERS['L3'], 'Fewer removals': LEVERS['L4'],
    'Best-practice materials': LEVERS['L5'],
    # theoretical limit
    'No idle stock': TL['TL1'], 'No extra space': TL['TL2'], 'Minimum space per person': TL['TL3'],
    'Best materials': TL['TL4'], 'Best soil': TL['TL5'], 'Urban densification': TL['TL6'],
    'P5-stretch: ramp -> instant start': 'P5 Ambitious: adoption path -> full strength from 2027',
    'instant start': ADOPTION['from2027'],
    'P5-stretch ramped -> P5-stretch instant (separate line, not a Shapley player)':
        'P5 Ambitious: adoption path -> full strength from 2027 (separate line, not a Shapley player)',
}


def _player_name(old):
    return _PLAYER_NAMES.get(old, old)


def _sens_label(old):
    """sensitivity_oat.csv group / case labels (only the scenario names change)."""
    rep = [('Low (S1): long-run rate, shares held', 'Low replacement: long-run rate'),
           ('High (S2): 2018-2023 rate persists, shares held', 'High replacement: 2018-2023 rate persists'),
           ('S3: half-life 5 yr', 'Reference, replacement half-life 5 yr'),
           ('S3: half-life 15 yr', 'Reference, replacement half-life 15 yr'),
           ('Replacement scenario', 'Replacement variant'),
           ('Near-term: how the excess is booked', '2026 overbuild: how it is booked'),
           ('Near-term: rule variant', '2026 overbuild: rule variant'),
           ('Adopted settings', 'Reference (adopted settings)'), ('Adopted', 'Reference')]
    for a, b in rep:
        if old == a:
            return b
    return old


def _pb_sens_label(old):
    return old.replace('Reference: pair A', 'Reference: carrying-capacity pair A')


# JSON: per-file key maps (exact keys), then the generic identifier rules.
_JSON_KEY_MAPS = {
    '*': {},
    # committed/<variant> holds the in-window maintenance twice: Boss's B_inwindow_kt and the
    # layer's own sum of the annual series (equal to rounding); both kept, named apart
    'pb_results.json': dict(SCENARIO_LEGACY, b_inwindow_kt='maintenance_kt_sum_of_annual'),
    'metrics.json': dict(SCENARIO_LEGACY, boss='projection', pb='aesa'),
    'gap_2026.json': {'S2_rate_effect': 'HIGH_rate_effect', 'S2_deviation_effect': 'HIGH_deviation_effect',
                      'model_requirement_2026_S2': 'model_requirement_2026_HIGH'},
    'replacement_scenarios.json': dict(SCENARIO_LEGACY),
    'reality_checks.json': dict(SCENARIO_LEGACY),
    'pathways/backcast.json': {'P0': 'REF', 'P5-central': 'P5-moderate', 'P5-stretch': 'P5-ambitious'},
    'pathways/t_limit.json': {'T': 'TL', 'T-ramp': 'TL-gradual', 't6': 'tl6',
                              **{k: v for k, v in TL_LEGACY.items() if k != 'T'}},
    'pathways/levers.json': {'L2a': 'L2', 'L2b': 'L3', 'L3': 'L4', 'L4': 'denser_mix_pathways_v2',
                             'central': 'moderate', 'stretch': 'ambitious', 'P0': 'REF', 'ramp': 'adoption',
                             'end_of_ramp_step_P2-central': 'end_of_ramp_step_P2-moderate',
                             'end_of_ramp_step_P2-stretch': 'end_of_ramp_step_P2-ambitious',
                             'S3-10 LoE_AR': 'REF LoE_AR', 'S3-10 LoE_AtP': 'REF LoE_AtP',
                             'S1 LoE_AR': 'LOW LoE_AR', 'S1 LoE_AtP': 'LOW LoE_AtP',
                             'S2 LoE_AR': 'HIGH LoE_AR', 'S2 LoE_AtP': 'HIGH LoE_AtP',
                             'S3-10 carbon vs pb_results': 'REF carbon vs aesa results',
                             'S1 carbon vs pb_results': 'LOW carbon vs aesa results',
                             'S2 carbon vs pb_results': 'HIGH carbon vs aesa results'},
}


def _json_key(old_file, key):
    f = old_file[len('frozen/'):] if old_file.startswith('frozen/') else old_file
    m = _JSON_KEY_MAPS.get(f, {})
    if key in m:
        return m[key]
    if f == 'pathways/levers.json' and key.startswith('band '):     # 'band <label> <quantity>'
        for lab in sorted(_BAND_LEGACY, key=len, reverse=True):
            if key.startswith(f'band {lab} '):
                return f'band {_ascii(band_label(lab))} {identifier(key[len(lab) + 6:])}'
    return identifier(key)


def _json_path(old_file, path):
    return '/'.join(_json_key(old_file, k) for k in path.split('/'))


def _column(old_file, col):
    f = old_file[len('frozen/'):] if old_file.startswith('frozen/') else old_file
    if f.startswith('montecarlo_sobol') or f.startswith('factors/'):
        return col                                  # Sobol S1 / ST; model input tables keep their names
    if f.startswith('montecarlo_summary') and col == 'Unnamed: 0':
        return 'output'                             # the index column (one row per output)
    if f.startswith('montecarlo_annual') and col == 'Unnamed: 0':
        return 'year'                               # the index column
    if f.startswith('pathways/') and col == 'ramp':
        return 'adoption'                           # the adoption path of the levers (by2035, ...)
    if f.startswith('montecarlo_summary') and col == 'central':
        return 'reference'                          # the deterministic Reference run
    return identifier(col)


# By-typology reporting removed in the release (typology stays internal to the model);
# each identifier is listed in the CHANGELOG.
_TYP = ('Detached', 'Townhouses', 'Apartments')


def _removed(old_file, row=None, col=None, path=None):
    f = old_file[len('frozen/'):] if old_file.startswith('frozen/') else old_file
    if row is None and col is None and path is None:
        return False                                # no whole file is removed
    if col is not None and re.fullmatch(r'gfa_(Detached|Townhouses|Apartments)_Mm2', col):
        return True
    if col in ('attached_share_2050', 'townhouse_share_2050'):
        return True
    if path is not None:
        parts = path.split('/')
        if f == 'boss_results.json' and parts[0] == 'typology':
            return True
        if f == 'replacement_scenarios.json' and 'shares_2050' in parts:
            return True
        if any(re.fullmatch(r'gfa_(Detached|Townhouses|Apartments)_Mm2', p) for p in parts):
            return True
        if parts[-1] in ('attached_share_2050',):
            return True
        if f.startswith('montecarlo_summary') and False:
            return True
    if row is not None and f.startswith('montecarlo_summary') and row and row[0] == 'townhouse_share_2050':
        return True
    if row is not None and f == 'montecarlo_sobol.csv' and row and row[0] == 'townhouse_share_2050':
        return True
    return False


# Stages of the refurbish already applied to the outputs. Each commit of the release states
# what it has applied, so the regression test holds at every commit:
#   'labels'   vocabulary, columns, identifying cells and JSON keys renamed (commit 3)
#   'layout'   outputs/data/, outputs/headline/, outputs/diagnostics/, outputs/reports/ (commit 4)
#   'removals' by-typology reporting removed (commit 7)
APPLIED = {'labels', 'layout'}


class _Legacy:
    """naming.LEGACY: v3.1 identifier -> release identifier, for the stages in APPLIED."""
    @staticmethod
    def file(old):
        return _file(old) if 'layout' in APPLIED else old

    @staticmethod
    def column(old_file, col):
        return _column(old_file, col) if 'labels' in APPLIED else col

    @staticmethod
    def cell(old_file, col, value, row):
        return _cell(old_file, col, value, row) if 'labels' in APPLIED else value

    @staticmethod
    def json_path(old_file, path):
        return _json_path(old_file, path) if 'labels' in APPLIED else path

    @staticmethod
    def removed(old_file, row=None, col=None, path=None):
        return _removed(old_file, row, col, path) if 'removals' in APPLIED else False


class _Release(_Legacy):
    """The full release map (all stages), for docs/RENAMING.md."""
    file = staticmethod(_file)
    column = staticmethod(_column)
    cell = staticmethod(_cell)
    json_path = staticmethod(_json_path)
    removed = staticmethod(_removed)


LEGACY = _Legacy()
RELEASE = _Release()
