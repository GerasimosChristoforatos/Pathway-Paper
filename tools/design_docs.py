"""Design documents of the MODEL v1.0.0 release, generated from the code that enforces them:

  docs/RENAMING.md     the complete old -> new map: vocabulary (naming.py), every file,
                       column, identifying cell and JSON key of the outputs captured at
                       ee37ef1 (tests/regression_model_v1.json, mapped with naming.LEGACY,
                       the map the regression test uses), figures (figure_plan.py), axis
                       labels and legend terms, code settings
  docs/FIGURE_PLAN.md  the headline and diagnostics figure sets (figure_plan.py)

    python tools/design_docs.py
"""
import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import naming as N  # noqa: E402

DOCS = os.path.join(ROOT, 'docs')
CAPTURE = os.path.join(ROOT, 'tests', 'regression_model_v1.json')


def table(head, rows):
    L = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    L += ['| ' + ' | '.join(str(c).replace('|', '\\|') for c in r) + ' |' for r in rows]
    return L


def code(s):
    return f'`{s}`'


# ---------------------------------------------------------------------------
# hand-curated parts of the map (reader-facing text that is not an identifier)
# ---------------------------------------------------------------------------
TERMS = [
    ('within-window, within the window, in-window', '2026–2050 (e.g. "carbon 2026–2050", "maintenance (B2, B4), 2026–2050")'),
    ('S3-10, reference S3-10, central run, P0, baseline (as a run)', 'Reference'),
    ('S1, Low (S1)', 'Low replacement'),
    ('S2, High (S2)', 'High replacement'),
    ('S3-5, S3-15', 'Reference, replacement half-life 5 yr / 15 yr'),
    ('-noUC', ', no census under-construction correction'),
    ('central / stretch', 'Moderate / Ambitious'),
    ('ramp, logistic ramp, ramp2035 / ramp2030 / ramp2045', 'adoption path; full roll-out by 2035 (adopted) / by 2030 / by 2045'),
    ('instant start, T at full strength from 2027', 'full strength from 2027'),
    ('near-term market excess, near-term join, near-term surplus', '2026 overbuild'),
    ('house-splitting', 'smaller households'),
    ('growth (net of consolidation), growth demand', 'population growth'),
    ('extra space per dwelling, consumption: extra space', 'extra space'),
    ('vacancy allowance, consumption: vacancy', 'vacancy'),
    ('demolition replacement + calibrated stock residual; long-run background replacement', 'replacement (net of unconsented additions)'),
    ('redevelopment wave', 'redevelopment'),
    ('replacements & repaints (B2, B4) within 2026-2050', 'maintenance (B2, B4), 2026–2050'),
    ('upfront (A1-A5 + soil)', 'materials and construction (A1–A5) + soil carbon loss (both named); "upfront" kept only as the defined sum in data files'),
    ('soil (land-use change)', 'soil carbon loss'),
    ('committed post-2050 emissions', 'committed after 2050 (later B2/B4 and C1–C4)'),
    ('PB layer, planetary-boundary layer', 'planetary-boundary layer (AESA); data and file prefix "aesa"'),
    ('T, theoretical limit T, T-ramp', 'TL Theoretical limit; TL, gradual adoption (SI)'),
    ('L4 (denser typology mix, pathways_v2)', N.DENSER_MIX + ' (never numbered: L4 is Building retention)'),
    ('version tags in labels (v1.1, v1.2, baseline-pb-v3, PATHWAYS v2, v3, v3.1)', 'none in any label, caption or generated document (history: CHANGELOG and git tags)'),
    ('typology (Detached, Townhouses, Apartments) in reporting', 'not reported; typology stays internal to the model (factors and lever parameters in data/)'),
]

SETTINGS = [
    ('Boss.py (module)', 'projection.py (git mv; history kept)'),
    ('PB.py (module)', 'boundaries.py (git mv; history kept); outputs data/aesa/*, figures D22-D27, H5, H6'),
    ('Boss.REPLACEMENT_SCENARIO = S1 / S2 / S3', 'projection.REPLACEMENT_VARIANT = LOW / HIGH / REF (REF = the fading path)'),
    ('Boss.S3_HALF_LIFE', 'projection.REPLACEMENT_HALF_LIFE'),
    ('Boss.NEAR_TERM_JOIN (market_excess, carried_deviation)', 'projection.OVERBUILD_RULE (same values)'),
    ('Boss.NEAR_TERM_MODE (surplus, redevelopment)', 'projection.OVERBUILD_BOOKING (same values)'),
    ('Boss.NEAR_TERM_ABSORPTION', 'projection.OVERBUILD_ABSORPTION'),
    ('Boss.NEAR_TERM_GAP_REF', 'projection.OVERBUILD_GAP_REF'),
    ('Boss.MIX_MODE, TREND_WINDOW_START, DAMPING_PHI, fit_evolving_mix, mix_trend, engine.mix_shares', 'removed (the damped typology-mix trend was never run or reported; MIX_HELD_WINDOW kept)'),
    ('Boss colour and label constants (DEMAND_COLORS, REPL_*, JOIN_*, WAVE_*, EVENTS_*, RV_COLOR, TYPOLOGY_COLORS, MATERIAL_STYLE, SOIL_*)', 'style.py (colours) and naming.py (labels)'),
    ('MonteCarlo.MC_SCENARIOS keys S3-10 / S1 / S2', 'REF / LOW / HIGH'),
    ('engine.replacement_path codes S1 / S2 / S3', 'LOW / HIGH / REF'),
    ('validation hindcast method reference_s3_10', 'reference'),
    ('pathways run_T, compute_T, checks_T, write_T, t_indicators', 'run_tl, compute_tl, checks_tl, write_tl, tl_indicators'),
    ('levers.LEVERS (L1, L2a, L2b, L3, L5)', 'L1, L2, L3, L4, L5'),
    ('levers.L2A_V_STAR, L2B_ABSORPTION, L3_D', 'L2_V_STAR, L3_ABSORPTION, L4_D'),
    ('levers.L4_V2_NOTE', 'levers.DENSER_MIX_V2_NOTE'),
    ('levers.SETTINGS (central, stretch)', 'moderate, ambitious'),
    ('levers.RAMP_SENS, RAMP_SENS_2030, ramp names', 'ADOPTION_SENSITIVITIES; by2030, by2045 (adopted by2035; TL from2027)'),
    ('levers.T_COMPONENTS, T_NAMES, T_DISCLAIMER, T6_*, T_*', 'TL_COMPONENTS, TL_NAMES, TL_DISCLAIMER, TL6_*, TL_*'),
    ('levers.resolve_T, apply_T, t_label, t_table, register_T, ramp_instant', 'resolve_tl, apply_tl, tl_label, tl_table, register_tl, ramp_from2027'),
    ('other module names (levers.py, pathways.py, engine.py, aesa.py, MonteCarlo.py, Sensitivity.py, ...)', 'unchanged; documents name them by role'),
]

# Identifiers the approved map did not cover, added while applying it (step 3 of the release);
# every one is in sections 3-5 above, which are enumerated from the map itself.
EXTENSIONS = [
    ('gap_2026.json: S2_rate_effect, S2_deviation_effect, model_requirement_2026_S2', 'HIGH_rate_effect, HIGH_deviation_effect, model_requirement_2026_HIGH'),
    ('metrics.json sections boss, pb', 'projection, aesa'),
    ('metrics.json validation/hindcast_<origin>_reference_s3_10 (and the hindcast method id)', 'hindcast_<origin>_reference'),
    ('projection.json settings/s3_half_life', 'settings/replacement_half_life'),
    ('levers.json ramp (section), end_of_ramp_step_P2-central / -stretch, P0_carbon_step_kt, step_relative_to_P0_kt', 'adoption, end_of_ramp_step_P2-moderate / -ambitious, reference_carbon_step_kt, step_relative_to_reference_kt'),
    ('pathways CSV column ramp (values ramp2035 / ramp2030 / ramp2045 / instant)', 'adoption (by2035 / by2030 / by2045 / from2027)'),
    ('t_limit.json definition/t6; indicators near_term_surplus_absorbed_dwellings', 'definition/tl6; overbuild_2026_absorbed_dwellings'),
    ('replacement_scenarios.json join_net', 'overbuild_2026_net_dwellings'),
    ('RV_units, RV_floor_area_Mm2_out_of_scope', 'retirement_village_units, retirement_village_floor_area_Mm2_out_of_scope'),
    ('shapley_T_subsets.csv subset T', 'TL'),
    ('shapley_T.csv name of the separate line (P5-stretch ramped -> P5-stretch instant ...)', 'P5 Ambitious: adoption path -> full strength from 2027 (separate line, not a Shapley player)'),
    ('montecarlo_summary*.csv index column (unnamed) and its output names (GFA_Mm2, RV_units, ...)', 'output; floor_area_Mm2, retirement_village_units, ...'),
    ('montecarlo_annual*.csv index column (unnamed)', 'year'),
    ('montecarlo_sobol.csv output names', 'as the draws columns (floor_area_Mm2, retirement_village_units, ...)'),
]

LEGEND_TERMS = [
    ('Historical (ERP, 31 Dec)', 'History (estimated resident population, 31 December)'),
    ('Projected Median', 'Reference projection (median)'),
    ('Uncertainty (5th/95th)', 'Population 5th-95th percentile'),
    ('Projected Total GFA (Median)', 'Reference projection'),
    ('Population 5th-95th percentile (other inputs fixed)', 'Population 5th-95th percentile (other inputs at the Reference)'),
    ('reference MC 5-95%', 'Monte Carlo 5-95% (Reference)'),
    ('Boss central run', 'Reference (deterministic)'),
    ('Monte Carlo median', 'Monte Carlo median'),
    ('Total built, in scope', 'removed (bands sum to the total)'),
    ('boundary, acquired rights (AR) / B_AR (acquired rights)', 'Acquired rights (AR)'),
    ('boundary, ability to pay (AtP) / B_AtP (ability to pay)', 'Ability to pay (AtP)'),
    ('LoE = 1 (boundary)', 'LoE = 1'),
    ('Reference without in-window replacements & repaints', 'Reference without maintenance (B2, B4)'),
    ('within 2026-2050: upfront at construction', 'Materials and construction (A1–A5) + soil carbon loss, 2026–2050'),
    ('within 2026-2050: replacements & repaints', 'Maintenance (B2, B4), 2026–2050'),
    ('committed after 2050 (later replacements & repaints + end of life), lower bound', 'Committed after 2050, lower bound (2050 factors held)'),
    ('committed after 2050, range to the upper bound (2025 factors)', 'Committed after 2050, range to the upper bound (2025 factors)'),
    ('P0 / P0 baseline', 'Reference'),
    ('P5-central / P5-stretch', 'P5 Combined, Moderate / Ambitious'),
    ('T theoretical limit / T (limit) / T-ramp', 'TL Theoretical limit / TL, gradual adoption'),
    ('central (open) / stretch (filled)', 'Moderate (open) / Ambitious (filled)'),
    ('full by 2030 / 2035 (adopted) / 2045', 'full roll-out by 2030 / by 2035 (adopted) / by 2045'),
    ('Soil (land-use change)', 'Soil carbon loss'),
    ('history (built)', 'History (built)'),
    ('Detached / Townhouses / Apartments', 'removed (by-typology reporting)'),
]


def _vacancy():
    for p in ('outputs/data/baseline/overbuild_2026.json', 'outputs/near_term_join.json'):
        path = os.path.join(ROOT, p)
        if os.path.exists(path):
            with open(path) as f:
                v = json.load(f)['vacancy']
            ymin = min(v['consistent'], key=v['consistent'].get)
            return N.vacancy_wording(v['v_forward'], v['consistent_max'], v['consistent_min'], ymin, v['v_2050']) + '.'
    raise FileNotFoundError('overbuild report')


def _vocabulary():
    L = ['## 1. Vocabulary', '',
         'Reader-facing labels (figures, tables, captions, documents) come only from `naming.py`. Code may use '
         'the short IDs; data files use the IDs with ASCII hyphens (no en dash) so that every tool reads them.', '']
    L += ['### Projection and variants', '']
    inv = {v: k for k, v in N.SCENARIO_LEGACY.items()}
    L += table(['code ID', 'release label', 'v3.1 names', 'definition'],
               [[code(k), v, f"{code(inv.get(k, '-'))}" + (' (also run P0, "central run", "reference S3-10")' if k == 'REF' else ''),
                 N.SCENARIO_DEFINITIONS.get(k, 'sensitivity variant')] for k, v in N.SCENARIOS.items()])
    L += ['', f'Frozen-technology check run: "{N.FROZEN}" (data/frozen_technology/).', '',
          'In the pathway tables the run without interventions takes the ID of its variant: REF (was P0 under '
          'S3-10), LOW (P0 under S1), HIGH (P0 under S2). "P0" is not used in any reader-facing text.', '',
          '### Pathways, settings, levers', '']
    old_p = {'P1': 'Right-size space', 'P2': 'Occupy the existing stock', 'P3': 'Keep and reuse', 'P4': 'Build better',
             'P5': 'All pathways'}
    L += table(['ID', 'release label', 'v3.1 label', 'levers'],
               [[k, v, old_p[k], ', '.join(f'{l} {N.LEVERS[l]}' for l in N.PATHWAY_LEVERS.get(k, ())) or 'all five']
                for k, v in N.PATHWAYS.items()])
    L += ['']
    L += table(['setting ID', 'release label', 'v3.1'], [[code(k), v, code(o)] for o, k in N.SETTING_LEGACY.items()
                                                         for v in [N.SETTINGS[k]]])
    L += ['']
    old_l = {'L1': 'Right-sized new dwellings', 'L2a': 'Lower vacancy', 'L2b': 'Near-term surplus absorbed',
             'L3': 'Fewer removals', 'L5': 'Best-practice materials'}
    L += table(['release ID', 'release label', 'v3.1 ID', 'v3.1 label', 'pathway'],
               [[n, N.LEVERS[n], o, old_l[o], next(p for p, ls in N.PATHWAY_LEVERS.items() if n in ls)]
                for o, n in N.LEVER_LEGACY.items()])
    L += ['', f'Removed in v3.1: the {N.DENSER_MIX}. It is never referred to as "L4" in the release.', '',
          '### Theoretical limit', '']
    old_t = {'T': 'T theoretical limit', 'T1': 'No idle stock', 'T2': 'No extra space', 'T3': 'Minimum space per person',
             'T4': 'Best materials', 'T5': 'Best soil', 'T6': 'Urban densification'}
    L += table(['release ID', 'release label', 'v3.1'], [[n, N.TL[n], f'{o} {old_t[o]}' if o != 'T' else old_t[o]]
                                                         for o, n in N.TL_LEGACY.items()])
    L += ['', f'TL caption wording: "{N.TL_CAPTION}". T-ramp -> "{N.TL_GRADUAL}" (run ID `TL-gradual`).', '',
          '### Adoption paths of the levers', '']
    L += table(['release ID', 'label', 'v3.1'], [[code(n), N.ADOPTION[n], code(o)] for o, n in N.ADOPTION_LEGACY.items()])
    L += ['', '### Demand bands (bottom to top)', '']
    leg = {}
    for o, n in N._BAND_LEGACY.items():
        leg.setdefault(n, []).append(o)
    L += table(['ID', 'release label', 'v3.1 labels', 'definition'],
               [[code(k), v, '; '.join(f'"{x}"' for x in leg.get(v, [])), N.BAND_DEFINITIONS.get(k, '')]
                for k, v in N.BANDS.items()]
               + [[code(k), v, '; '.join(f'"{x}"' for x in leg.get(v, [])), 'sub-row of Replacement in data tables'
                   if k.startswith('replacement') else 'bookkeeping row, out of scope; not a band in figures']
                  for k, v in N.BAND_DETAIL.items()])
    L += ['', '### Carbon components, boundaries and metrics', '']
    L += table(['ID', 'release label'], [[code(k), v] for k, v in N.COMPONENTS.items()]
               + [[code('upfront'), N.UPFRONT]] + [[code(k), v] for k, v in N.METRICS.items()])
    L += ['', '### Terms', '']
    L += table(['v3.1 term', 'release term'], TERMS)
    L += ['', '### Vacancy wording (one sentence everywhere)', '', '> ' + _vacancy(), '',
          'Values are read from the overbuild report (outputs/near_term_join.json at ee37ef1; '
          'data/baseline/overbuild_2026.json in the release): the held rate is the published 2023 empty-dwelling '
          'share; on the consistent definition (the pooled 2018/2023 empty share applied to every census) 2023 is '
          'the highest census and 1996 the lowest. Every document, caption and code comment that implies that '
          'vacancy itself stays at the census level is reworded to this sentence.']
    return L


def _identifiers(cap):
    L = ['', '## 2. Files', '', 'Every CSV and JSON output captured at ee37ef1 (paths under `outputs/`).', '']
    rows = [[code(f), code(N.RELEASE.file(f))] for f in cap['files']]
    L += table(['v3.1 file', 'release file'], rows)
    other = [('outputs/RESULTS.md', 'outputs/reports/RESULTS.md'),
             ('ASSUMPTIONS.md (root)', 'outputs/reports/ASSUMPTIONS.md'),
             ('outputs/BASELINE_DRAFT.md, outputs/PB_METHODS_DRAFT.md, outputs/pathways/PATHWAYS_METHODS_DRAFT.md',
              'outputs/reports/METHODS_DRAFT.md (sections: baseline projection, AESA, pathways and TL)'),
             ('outputs/pathways/LEVERS_TABLE.md', 'outputs/reports/LEVERS_TABLE.md'),
             ('outputs/validation.md, reality_checks.md, gap_2026.md, near_term_join.md, replacement_scenarios.md, '
              'reconciliation.md', 'outputs/reports/ (validation.md, reality_checks.md, gap_2026.md, overbuild_2026.md, '
              'scenarios.md, reconciliation.md)'),
             ('outputs/frozen/replacement_scenarios.md', 'outputs/reports/frozen_technology_scenarios.md'),
             ('FIGURES.md (root)', 'outputs/headline/HEADLINE.md and outputs/diagnostics/DIAGNOSTICS.md'),
             ('outputs/pathways/HOOKS.md', 'docs/HOOKS.md'),
             ('outputs/figures/*.png (not versioned)', 'outputs/headline/*.png|pdf, outputs/diagnostics/<group>/*.png (versioned)'),
             ('outputs/figures/_audit/*.json', 'outputs/diagnostics/_audit/*.json (year-range audit records)'),
             ('outputs/logs/', 'outputs/logs/ (not versioned)')]
    L += ['', 'Documents and folders:', ''] + table(['v3.1', 'release'], other)
    # columns
    L += ['', '## 3. Columns', '', 'Columns whose name changes (generic rules of `naming.identifier`; Sobol '
          'columns S1/ST and the model-input factor tables keep their names). "removed" = by-typology reporting.', '']
    rows = []
    for f, e in cap['files'].items():
        if e['kind'] == 'json':
            continue
        cols = (e['key_columns'] + e['value_columns']) if e['kind'] == 'csv' else e['value_columns']
        for c in cols:
            new = N.RELEASE.column(f, c)
            rem = N.RELEASE.removed(f, col=c) if e['kind'] != 'csv' or c in e['value_columns'] else False
            if rem:
                rows.append([code(f), code(c), 'removed'])
            elif new != c:
                rows.append([code(f), code(c), code(new)])
    L += table(['v3.1 file', 'v3.1 column', 'release column'], rows)
    # cells
    L += ['', '## 4. Identifying cells', '', 'Distinct values of identifying (text) columns that change.', '']
    rows = []
    for f, e in cap['files'].items():
        if e['kind'] != 'csv':
            continue
        keys = e['key_columns']
        seen = OrderedDict()
        for rk in e['rows']:
            cells = json.loads(rk)
            ctx = dict(zip(keys, cells))
            for k, v in zip(keys, cells):
                if isinstance(v, str):
                    new = N.RELEASE.cell(f, k, v, ctx)
                    if new != v:
                        seen[(k, v, new)] = None
        for (k, v, new) in seen:
            rows.append([code(f), code(k), v, new])
    L += table(['v3.1 file', 'column', 'v3.1 value', 'release value'], rows)
    # JSON
    L += ['', '## 5. JSON keys', '', 'Distinct keys that change, per file (paths are joined by "/"; list indices '
          'unchanged).', '']
    rows, removed = [], {}
    for f, e in cap['files'].items():
        if e['kind'] != 'json':
            continue
        seen = OrderedDict()
        for p in e['values']:
            if N.RELEASE.removed(f, path=p):
                removed.setdefault(f, set()).add(p.split('/')[0] + ('/...' if '/' in p else ''))
                continue
            for k in p.split('/'):
                new = N.RELEASE.json_path(f, k)
                if new != k:
                    seen[(k, new)] = None
        for (k, new) in seen:
            rows.append([code(f), code(k), code(new)])
    L += table(['v3.1 file', 'v3.1 key', 'release key'], rows)
    if removed:
        L += ['', 'Removed JSON values (by-typology reporting):', '']
        L += [f'* `{f}`: ' + ', '.join(sorted(v)) for f, v in removed.items()]
    return L


def _figures():
    L = ['', '## 6. Figures', '', 'Every v3.1 figure, its release figure(s) or the reason it is not carried. Plan: '
         '[FIGURE_PLAN.md](FIGURE_PLAN.md).', '']
    rows = []
    for old, targets in sorted(FP.legacy_map().items()):
        rows.append([code(old), '; '.join((f'removed: {t[1]}' if t[0] == 'removed' else f'{t[0]}/{t[1]}')
                                          for t in targets)])
    L += table(['v3.1 figure', 'release'], rows)
    return L


def _labels():
    L = ['', '## 7. Axis labels and legend entries', '',
         'Axis labels follow one pattern: quantity (unit), e.g. "Floor area (Mm² per year)", "Embodied carbon '
         '(kt CO₂e per year)", "Cumulative level of exceedance, 2026–2050". Every v3.1 axis label of the figure '
         'audit records and its release form:', '']
    L += table(['v3.1 axis label', 'release axis label'], AXIS_LABELS)
    L += ['', 'Legend entries (term level; legends are composed from the vocabulary above):', '']
    L += table(['v3.1 legend entry', 'release legend entry'], LEGEND_TERMS)
    L += ['', '## 8. Code settings that surface in documents', '',
          'Module renames approved with the design documents: Boss.py -> projection.py and PB.py -> boundaries.py '
          '(git mv, so the history of each file is kept); imports, run_all.py, the Spyder instructions, the '
          'documents and the tests use the new names.', '']
    L += table(['v3.1', 'release'], SETTINGS)
    L += ['', '## 9. Extensions made while applying the map', '',
          'Identifiers of the captured outputs that the approved map left in the v3.1 vocabulary, mapped while '
          'the renaming was applied (MODEL v1.0.0, step 3) by the same rules (naming.py); sections 3-5 above list '
          'them with every other identifier. Kept on purpose: the Sobol index notation S1 / ST of '
          'montecarlo_sobol.csv, the case-study ids (A_1, T_1, ...) and the input tables of data/factors/ '
          '(model inputs keep their source names), and setting names echoed from module constants (e.g. '
          'PB_YEARS in the AESA settings block).', '']
    L += table(['v3.1 identifier', 'release identifier'], EXTENSIONS)
    return L


AXIS_LABELS = [
    ('Population (persons)', 'Population (million)'),
    ('Households (millions)', 'Households (million)'),
    ('People per Household / persons per household', 'Household size (persons per household)'),
    ('Per year (persons; households)', 'Persons or households per year (thousand)'),
    ('Cumulative new GFA (Mm²)', 'Floor area, cumulative (Mm²)'),
    ('Annual new GFA (Mm²/yr) / Mm² per year', 'Floor area (Mm² per year)'),
    ('Mm² / Mm² (2026-2050)', 'Floor area 2026–2050 (Mm²)'),
    ('Mm² per year (log)', 'Floor area (Mm² per year, log scale)'),
    ('Annual carbon (kt CO₂e per year) / kt CO₂e per year / kt CO$_2$e per year', 'Embodied carbon (kt CO₂e per year)'),
    ('Cumulative carbon (kt CO₂e) / cumulative kt CO$_2$e / kt CO₂e, cumulative from 2026', 'Embodied carbon, cumulative from 2026 (kt CO₂e)'),
    ('kt CO₂e / kt CO₂e, 2026-2050', 'Embodied carbon 2026–2050 (kt CO₂e)'),
    ('kt CO₂e per year (log scale)', 'Boundary (kt CO₂e per year, log scale)'),
    ('LoE = annual carbon / boundary (log scale)', 'Level of exceedance (annual carbon / boundary, log scale)'),
    ('change in cumulative LoE vs reference (…)', 'Change in cumulative level of exceedance vs the Reference'),
    ('cumulative level of exceedance 2026-2050 (log)', 'Cumulative level of exceedance, 2026–2050 (log scale)'),
    ('% change from the adopted settings', 'Change vs the Reference (%)'),
    ('% difference from adopted, each year', 'Difference vs the Reference, each year (%)'),
    ('% of private dwellings / vacancy (% of private dwellings)', 'Vacancy rate (% of private dwellings)'),
    ("% of last year's stock per year", "Net replacement (% of the previous year's stock per year)"),
    ('% of floor area / GFA Market Share (%) / townhouses + apartments, % of floor area', 'removed (by-typology reporting)'),
    ('m² per dwelling', 'Floor area per dwelling (m²)'),
    ('m² per person', 'Floor area per person (m²)'),
    ('kg CO₂e per m² / kg CO₂e per m² of new floor area (log)', 'Carbon intensity (kg CO₂e per m², log scale where stated)'),
    ('t CO₂e per new dwelling (log)', 'Carbon per new dwelling (t CO₂e, log scale)'),
    ('Utilisation: S / design capacity (%)', 'Occupancy utilisation: household size / design capacity (%)'),
    ('thousand dwellings / dwellings per year / thousand per year', 'Dwellings (thousand per year)'),
    ('dwellings consented', 'Dwellings consented'),
    ('households per consent', 'Households per consent'),
    ('population growth that year (thousand)', 'Population growth (thousand per year)'),
    ('change in household size', 'Change in household size (persons per household)'),
    ('index, 2025 = 1', 'Index (2025 = 1)'),
    ('% change from previous year / number of years', 'Change from the previous year (%) / Number of years'),
    ('share of output variance', 'Share of output variance'),
    ('Year / year', 'Year (only where the axis is not obviously calendar years)'),
    ('million / thousand / persons', 'quantity named with its unit (e.g. "Dwellings (million)")'),
]


def renaming():
    with open(CAPTURE) as f:
        cap = json.load(f)
    L = ['# Renaming map (generated by tools/design_docs.py; do not edit by hand)', '',
         'The complete map from the names of commit ee37ef1 (pathways v3.1) to the MODEL v1.0.0 names. Sections '
         '2-5 are enumerated from every identifier of the captured outputs (tests/regression_model_v1.json) through '
         '`naming.LEGACY`, the same map tests/test_regression_model_v1.py uses to find every captured number in the '
         'release outputs; nothing in them is typed by hand.', '',
         '**Principle.** Every term is academically proper, describes its content and is concise; one vocabulary '
         'everywhere. Internal code may use short IDs; everything a reader sees uses the labels below.', '']
    L += _vocabulary() + _identifiers(cap) + _figures() + _labels()
    return L


def figure_plan():
    L = ['# Figure plan (generated by tools/design_docs.py from figure_plan.py; do not edit by hand)', '',
         'Two sets. **Headline** (`outputs/headline/`): the figures of the paper, double column (183 mm), PNG '
         '300 dpi and vector PDF, with `HEADLINE.md` (findings and every figure with its caption). '
         '**Diagnostics** (`outputs/diagnostics/<group>/`): every other figure, PNG 300 dpi, indexed in '
         '`DIAGNOSTICS.md`. All figures use `style.py` (docs/PALETTE.md) and the vocabulary of `naming.py` '
         '(docs/RENAMING.md). Caption numbers are read from the data files when the figure is drawn.', '',
         '## Headline set', '']
    for h in FP.HEADLINE:
        L += [f"### {h['id']}. {h['title']}", '', f"* File: `outputs/headline/{h['file']}.png` / `.pdf`",
              f"* Panels: {h['panels']}", f"* Data: {h['source']}", f"* Draft caption: {h['caption']}",
              f"* Replaces (v3.1): {', '.join(h['legacy']) or 'new'}", '']
    L += ['### Decisions (approved with the design documents)', '',
          '* **H11, population rows: option A.** The one-at-a-time rows that change only the numerator of the LoE '
          '(every model-input row except population) convert exactly: cumulative LoE AR = Reference LoE x carbon / '
          'Reference carbon, because the boundaries depend on the population path only. The population 5th / 95th '
          'rows change the AR boundary as well (population modifier of Horup et al. 2025, Eq. 1): their LoE is '
          'computed with the existing boundary function (aesa.boundary_ar, aesa.boundary_atp) on each population '
          'path, with the exact engine carbon of that path. Two new values, flagged as additions (not changes) in '
          'the regression file and the CHANGELOG.',
          '* **H10, TL marker: yes.** TL is placed at its effective coordinates (2027-2050 floor area and non-soil '
          'carbon per m2 of the TL run vs the Reference): two derived coordinates, computed exactly from the TL run, '
          'with the caveat in the caption that TL5 and TL6 lower soil carbon, which the plane does not show.',
          '* **H4, annual components: yes.** The annual split into materials and construction (A1-A5), soil carbon '
          'loss and maintenance is exported as a new table (outputs/headline/H4_carbon_components.csv); it is an '
          'exact decomposition of the captured annual carbon (tested to sum to it exactly).',
          '* **Added headline content.** No figure beyond H1-H11; the material breakdown joins H4 as panel (b) '
          'because it is the policy-relevant split of the same carbon, and the TL human-terms staircase stays in '
          'the diagnostics (D32) because H9 carries its residual.',
          '* **Palette and figure plan:** approved as proposed (docs/PALETTE.md).', '']
    L += ['## Diagnostics set', '']
    for g, rows in FP.DIAGNOSTICS.items():
        L += [f'### {g}', '']
        L += table(['file', 'content', 'replaces (v3.1)'],
                   [[f'`outputs/diagnostics/{g}/{f}.png`', t, ', '.join(o)] for f, t, o in rows])
        L += ['']
    L += ['## Not carried into the release', '']
    L += table(['v3.1 figure', 'reason'], [[code(k), v] for k, v in FP.REMOVED.items()])
    return L


def main():
    os.makedirs(DOCS, exist_ok=True)
    for name, fn in (('RENAMING.md', renaming), ('FIGURE_PLAN.md', figure_plan)):
        L = fn()
        with open(os.path.join(DOCS, name), 'w', encoding='utf-8') as f:
            f.write('\n'.join(L) + '\n')
        print(f'design_docs: docs/{name} ({len(L)} lines)')


if __name__ == '__main__':
    main()
