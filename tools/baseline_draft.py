"""The baseline-projection part of the methods draft: methods and results of the Reference
projection and its variants (Low replacement, High replacement, replacement half-life 5 / 15 yr),
the demand bands, the 2026 overbuild, carbon 2026-2050 (materials and construction A1-A5, soil
carbon loss, maintenance B2/B4) and committed after 2050, validation, reality checks,
sensitivities and the assumption register.

    python tools/baseline_draft.py      # writes outputs/reports/METHODS_DRAFT.md (all three parts)

lines() returns the Markdown of this part without a document title (section headings at '##');
tools/methods_draft.py merges it with the AESA and pathways parts into
outputs/reports/METHODS_DRAFT.md, the one methods document of the release.

Results are read from the generated files in outputs/data/ and settings from projection.py;
reader-facing labels follow naming.py (docs/RENAMING.md). Method constants quoted in the text
(e.g. the 0.95 completion rate, the 58.77 kg CO2e/m2 soil factor) are typed and must agree with
projection.py.

Inputs (outputs/data/): baseline/projection.json, metrics.json, baseline/scenarios.json,
baseline/validation.json, baseline/gap_2026.json, baseline/overbuild_2026.json,
baseline/reality_checks.json, baseline/reconciliation.json, baseline/sensitivity_one_at_a_time.csv,
aesa/results.json, factors/factors_a13_item_coverage.csv, montecarlo/summary_<variant>.csv
(LOW, REF, HIGH; when present).
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layout  # noqa: E402
import naming as N  # noqa: E402

SENSITIVITY = layout.data('baseline/sensitivity_one_at_a_time.csv', frozen=False)


def load(name):
    """A JSON file of outputs/data/ (relative path), or None if it does not exist."""
    p = layout.data(name, frozen=False)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def pct(a, b):
    return f'{100 * (a / b - 1):+.1f}%'


def _cap(s):
    return s[0].upper() + s[1:]


def vacancy_sentence(nj):
    """The release wording of the vacancy assumption (naming.vacancy_wording), filled from
    outputs/data/baseline/overbuild_2026.json (key 'vacancy'); None if the file or a field is missing."""
    v = (nj or {}).get('vacancy') or {}
    if not {'v_forward', 'consistent_max', 'consistent_min', 'consistent', 'v_2050'} <= set(v):
        return None
    c = v['consistent']
    if str(max(c, key=c.get)) != '2023':          # the wording names 2023 as the series maximum (as D05)
        raise SystemExit('The consistent vacancy series no longer peaks in 2023; revise naming.VACANCY_WORDING.')
    return N.vacancy_wording(v['v_forward'], v['consistent_max'], v['consistent_min'], min(c, key=c.get),
                             v['v_2050'])


def _s4_change(rows):
    """{S4 row: relative change by 2050}, from data/derived/horup2025_table_s4.csv."""
    import Building_factors as BF
    d = pd.read_csv(BF.FILE_HORUP)
    d = d[d.year == 2050].set_index('material')['rel_to_2025']
    return {r: float(d[r] - 1) for r in rows}


SEC31_QUOTE = ('"Tendencies for concrete, wood and clay products are generally similar for other cementitious, '
               'wood-based and clay products, whereas the extended analysis shows that for other metals, glass and '
               'insulation products the results and tendencies observed are less homogenous." (Horup et al. 2025, '
               'Sci. Total Environ. 966, 178780, p. 6)')
PREMISE_QUOTE = ('"The Premise software accounts for future changes in several critical sectors (supply of '
                 'conventional and alternative fuels, electricity, cement and steel production and freight and '
                 'passenger road transportation), and includes implementation of technologies such as carbon capture '
                 'and storage in steel and cement production" (Horup et al. 2025, p. 5)')


def item_coverage():
    """{typology: {label: share of 2025 A1-A3}} and {typology: {case: A1-A3 reduction by 2050}}
    from outputs/data/factors/factors_a13_item_coverage.csv (Building_factors.py); the case-study
    factors are per typology inside the model."""
    import Building_factors as BF
    c = pd.read_csv(BF.OUT_ITEM_COVERAGE)
    lab = c[c.Kind == 'label'].pivot(index='Typology', columns='Key', values='Value').reindex(BF.TYP_ORDER)
    red = c[c.Kind == 'reduction_2050'].pivot(index='Typology', columns='Key', values='Value').reindex(BF.TYP_ORDER)
    return lab, red


def item_register():
    """Register rows of the item-level mapping ('horup_item'). Counts, shares and S4 changes
    are read from the mapping table, the coverage file and S4."""
    import Building_factors as BF
    mp = pd.read_csv(BF.FILE_ITEM_MAP)
    n = mp['label'].value_counts()
    ch = _s4_change(sorted(set(mp['s4_row']) - {BF.ITEM_HELD}))
    lab, _ = item_coverage()
    cov = '; '.join(f"{t} {100 * r.get('direct', 0):.1f} / {100 * r.get('sec31', 0):.1f} / "
                    f"{100 * r.get('proxy', 0):.1f} / {100 * r.get('held', 0):.1f}%" for t, r in lab.iterrows())
    nz = mp[mp['nz_low_carbon_electricity'] == 'yes']
    return [
        ('Item table (horup_item)', f"{len(mp)} case-study class x EPD items (data/derived/material_items.csv, built by "
         'data/build_material_items.py from the supplied data/raw/epd-level_materials.xlsx); item and class names '
         'stripped of leading/trailing whitespace (5 item names, 34 source rows); rows of the same building, class '
         'and item summed; reproduces data/building_data.xlsx sheet 1 for every building x class x stage',
         'DATA: Christoforatos & Pickering 2025 case studies at item resolution'),
        ('Material mapping, item-level (horup_item; EPD item -> S4 row)',
         f"data/material_item_map.csv: each item to exactly one S4 row or held, with its basis; {n.get('direct', 0)} "
         f"direct, {n.get('sec31', 0)} by Horup p. 6, {n.get('proxy', 0)} proxy, {n.get('held', 0)} held. Pooled per "
         'building, then per typology, as the classes; the 2025 totals are the class totals',
         'DECISION (author); per-item basis in the table'),
        ('Item mapping: direct', 'in-situ concrete and concrete roof tiles, all REINFORCED CONCRETE items (incl. rebar) '
         '-> concrete structure; AAC block -> lightweight concrete; steel sections (UB, UC, WC, PFC, SHS, RHS), '
         'sheet / decking, purlins, studs, ZinaCore, Colorsteel -> steel profile; Pacific Steel rebar -> reinforcing '
         'steel; sawn / framing / flooring timber, weatherboards, glulam, LVL, I-joists -> construction wood; CLT -> '
         'CLT; plywood -> plywood; glass and IGUs (incl. the argon-fill items in OTHERS) -> glass; glass wool -> '
         'mineral wool glass; bricks -> clay brick; aluminium -> aluminium; ceramic tiles and sanitary ware -> '
         'ceramic tile; EPS and XPS -> EPS', 'DECISION (author)'),
        ('Item mapping: Horup p. 6 (label sec31)', 'particleboard (TIMBER and OTHERS), MDF doors, hardwood floor -> '
         'construction wood; fibre cement (all), "Plaster, cement" (PLASTER and the item in PLASTERBOARD) -> '
         'cement mortar', f'LITERATURE: {SEC31_QUOTE}'),
        ('Item mapping: proxies (label proxy)', 'plastics without an S4 row (carpets PA6.6 and wool blend, PE '
         'membranes, PVC membrane / floor sheets / frames, EPDM, polyester insulation) and paint -> EPS; SIP -> EPS '
         f"(the smaller 2050 reduction of construction wood, {100 * ch['Construction wood']:+.1f}%, and EPS, "
         f"{100 * ch['EPS']:+.1f}%); gypsum plasterboard -> clay brick ({100 * ch['Clay brick']:+.1f}%)",
         'DECISION (author): no S4 counterpart. The EPS-based proxies (polymers, paint, SIP) carry the smallest '
         f"reduction in the set ({100 * ch['EPS']:+.1f}% by 2050), so they are conservative"),
        ('Item mapping: held at 2025 (label held)', 'lift (OTIS Gen2, apartments)',
         'DECISION (author): no S4 counterpart; its share of 2025 A1-A3 is in the coverage row'),
        ('Composite floor decking (RC item)', 'concrete structure, incl. its rebar and steel trapezoidal deck',
         'DECISION (author): no split available in the source; conservative versus steel profile '
         f"({100 * ch['Concrete structure']:+.1f}% vs {100 * _s4_change(['Steel profile'])['Steel profile']:+.1f}% "
         'by 2050)'),
        ('Masonry wall (dense concrete block, grouted, reinforced)', 'concrete structure', 'DECISION (author)'),
        ('Rebar inside REINFORCED CONCRETE items', 'concrete-structure rate', 'DECISION (author): S4\'s concrete '
         'dataset does not separate reinforcement'),
        ('Coverage of 2025 A1-A3 of the case-study factors (pooled per typology inside the model; direct / '
         'Horup p. 6 / proxy / held)', cov, 'DATA: outputs/data/factors/factors_a13_item_coverage.csv (model input; '
         'not a result by typology)'),
        ('Sensitivity: NZ low-carbon-electricity items held at 2025',
         f"{len(nz)} items: the 5 aluminium items, Pink Batts glass wool, Pacific Steel rebar, WPMA Radiata timber, "
         'Nelson Pine LVL', 'DECISION (author); criterion: made in New Zealand AND electricity-intensive production '
         '(not fossil process heat). Not included: Allied Concrete, GIB plasterboard, Colorsteel / ZinaCore (fossil '
         'process heat, where Horup\'s reductions reflect process change), CLT (imported, Xlam Australia); NZSIP not '
         f"needed (EPS path {100 * ch['EPS']:+.1f}%)"),
        ('Sensitivities (item-level)', 'proxies held at 2025; NZ low-carbon-electricity items held at 2025; frozen '
         'technology (no decarbonisation, A4-A5 held); all in the default run '
         '(outputs/data/baseline/sensitivity_one_at_a_time.csv, outputs/data/aesa/sensitivity.csv; figures ED1, ED4 and '
         'D18). An earlier class-level mapping and its comparison runs were removed (history: CHANGELOG.md)',
         'DECISION (author)'),
    ]


def overbuild_limitations():
    """The 2026 overbuild limitation, from outputs/data/baseline/overbuild_2026.json (tools/overbuild_2026.py)."""
    nj = load('baseline/overbuild_2026.json')
    return [nj['limitation']] if nj and 'limitation' in nj else []


def decarb_limitations(mode):
    """Limitations of the material decarbonisation for a DECARB_MODE."""
    if mode == 'none':
        return []
    return DECARB_LIMITATIONS + [
        'Several items are made in New Zealand with electricity-intensive production (aluminium, Pink '
        'Batts glass wool, Pacific Steel rebar, WPMA Radiata timber, Nelson Pine LVL); the aluminium items '
        'are stated in their EPD names to use mainly renewables-generated electricity. Where their 2025 '
        'factors already reflect low-carbon electricity, the premise paths, which include the '
        f'decarbonisation of electricity supply ({PREMISE_QUOTE}), may overstate their relative reduction; '
        'a sensitivity holds them at 2025.',
        'Composite floor decking (an RC item containing its steel deck and rebar) follows the '
        'concrete-structure path because the source gives no split; this is conservative versus steel '
        'profile for the steel share.']


def timing_register():
    """Register rows of the time-resolved accounting: maintenance events (B2, B4), A4-A5 path,
    committed after 2050 and the data notes of the event table. Counts from the files."""
    import projection as B
    import Building_factors as BF
    ev = pd.read_csv(BF.FILE_EVENTS).fillna({'event_type': '', 'event_path': ''})
    ex = pd.read_csv(os.path.join(ROOT, 'data', 'derived', 'lca_excluded_lines.csv'))
    ne = ev[ev['n_events'] > 0]
    nrep = int((ne['event_type'] == 'replacement').sum())
    nrp = int((ne['event_type'] == 'repaint').sum())
    site = int(ex['reason'].str.startswith('site works').sum())
    unl = ex[ex['reason'].str.startswith('unlabelled')]
    a1 = unl[unl['id'] == 'A_1']['A1-A3'].sum() / 1e3
    g = BF.generic_path([2050])[0]
    return [
        ('Accounting of later life-cycle stages (LIFE_CYCLE_TIMING)',
         {'time_resolved': 'time_resolved: materials and construction (A1-A5) and soil carbon loss in the '
                           'construction year; maintenance (B2, B4: replacement and repaint events) in the calendar '
                           'year it occurs, 2026-2050; events after 2050 and all C1-C4 of the 2026-2050 cohorts '
                           'reported as committed after 2050 (range below), not added to the 2026-2050 total',
          'whole_life_at_construction': 'whole_life_at_construction: all stages A1-C4 booked in the construction '
                                        'year (the static convention of earlier versions of the model)'}[B.LIFE_CYCLE_TIMING],
         'DECISION (author); LITERATURE: Habert et al. 2020, Buildings and Cities 1, 429-452, Section 5.1 (p. '
         '442): embodied emissions "occur mainly in the first year of the building life time and (approximately '
         '30 years later) when deep renovation are done", and spreading them over the building life '
         '"underestimates the peak of emissions which will happen before 2050"; time-explicit inventories of '
         'building replacements: Resch, Andresen, Cherubini & Brattebø 2021, Building and Environment 187, 107399, '
         'Section 2.2. Whole life at construction is a sensitivity'),
        ('Event table (B2, B4)', f"{len(ev)} case-study lines matched to the item table (data/derived/lca_events.csv, "
         'built by data/build_lca_events.py from data/raw/Analytical_LCA_Results_Database.xlsx, LCAQuick root '
         f"tables): number of replacement and repaint events (maintenance, B2 and B4) and building lifespan ({', '.join(str(int(v)) for v in sorted(ev['lifespan'].unique()))} "
         f"yr) per line; {len(ne)} lines carry events ({nrep} replacement, {nrp} repaint lines). Stage totals stay "
         'those of data/building_data.xlsx and the item table (the stage totals of earlier versions of the model '
         'are reproduced)',
         'DATA: Christoforatos & Pickering 2025 case studies, LCAQuick root tables'),
        ('Lines not used from the event workbook', f"{len(ex)} lines, none with B2/B4 (data/derived/"
         f"lca_excluded_lines.csv): {site} sand / granular-fill lines (site works, outside the case-study scope); "
         f"{len(unl)} unlabelled lines, including the A_1 unlabelled row ({a1:,.0f} t A1-A3; excluded, as in "
         'earlier versions of the model and the sheet summary); one T_1 aluminium line whose A1-A3 differs from '
         'the item table by 10 kg (item table kept). Several sheet summary blocks do not equal their own line '
         'sums; line-level data are used', 'DECISION (author)'),
        ('Events per line', 'per-event impact = line B2/B4 / n; split into A1-A3 : A4-A5 : C1-C4 in proportion to '
         "the line's initial stages; pooled per typology inside the model with the weights of the carbon factors "
         '(outputs/data/factors/factors_events.csv)', 'DECISION (author)'),
        ('Event timing (EVENT_TIMING)', f"'{B.EVENT_TIMING}': {BF.EVENT_TIMINGS[B.EVENT_TIMING]}; a fractional "
         'year is split linearly between the two adjacent years',
         'DECISION (author): LCAQuick derives n = ceil(L / RSL) - 1, so the service life lies in [L / (n + 1), '
         'L / n); L / (n + 1) is its lower end (earliest events), L / n the sensitivity'),
        ('Colorsteel lines (1 replacement + 1 repaint in the source)', 'one replacement event at L / (n + 1) '
         'carrying the full line B2/B4, on the item\'s steel-profile path', 'DECISION (author): the repaint '
         'would fall in the same year (L / 2), so a separate repaint event would change only the decarbonisation '
         'path of about 2.5% of these lines\' B2/B4'),
        ('ZinaCore lines', '3 repaint events of B2/B4 / 3 each at L / (m + 1) spacing, on the paint path (EPS '
         'proxy)', 'DECISION (author): the emission is recoating, not new steel'),
        ('Event decarbonisation paths', 'A1-A3: replacements on the item\'s own S4 path (same item rules and '
         'sensitivities as construction); repaints and recoating on the paint path (EPS proxy). A4-A5: the A4-A5 '
         'path below. C1-C4: held at 2025', 'DECISION (author); no source for end-of-life decarbonisation'),
        ('A4-A5 decarbonisation (DECARB_A45)',
         {'resch': f"resch: e^(-0.01 (t - 2025)), {100 * (g - 1):+.1f}% by 2050, for construction A4-A5 and the "
                   'A4-A5 share of events',
          'held': 'held: A4-A5 at 2025', 'item': "item: each item's S4 path"}[B.DECARB_A45],
         'LITERATURE: Resch et al. 2021, Table 1 (p. 4): production e^(-0.01 y), "a ~1% yearly improvement", '
         'half-life 69 years; the exponential form of the source is used (0.99^25 would give -22.2%). Resch et al. '
         'apply 2%/yr to transport; A4-A5 also contains installation and wastage, so the 1% production rate is '
         'used for the combined stage (conservative for transport). Resch et al. count y from the construction '
         'year for future (B, C) emissions; here y counts calendar years from 2025 (adaptation). Sensitivities: '
         'held at 2025; item S4 paths'),
        ('Committed after 2050 (later B2/B4 and C1-C4)', 'upper: events after 2050 at 2025 factors; lower: the 2050 '
         'factors held after 2050 (no extrapolation beyond the last source year); C1-C4 at 2025 in both. Expressed '
         'in years of the 2050 AR boundary', 'DECISION (author): the source paths end in 2050'),
        ('Emissions accounting rule (ACCOUNTING, MODEL v3.1.0)',
         f"'{B.ACCOUNTING}': " + {
             'inventory': ('every window (the AR base 2016-2025 and the projection 2026-2050) counts all emissions '
                           f'occurring in it from residential construction since {B.B_SCOPE_START}: A1-A5 of its own '
                           f'construction, soil oxidised linearly over {B.SOIL_OXIDATION_YEARS} years after conversion '
                           '(incl. the tails of earlier conversions) and B2/B4 of every cohort since '
                           f'{B.B_SCOPE_START}; the emissions of pre-2026 activity in 2026-2050 are the legacy band '
                           '(identical in every run); the oxidation after 2050 of 2026-2050 conversions is committed '
                           "('Soil, after 2050'); pre-1992 stock out of scope on both sides"),
             'instant': 'soil at conversion; B2/B4 of each window\'s own cohorts (MODEL v3.0.0)',
             'cohort_window': 'soil oxidised over 20 years, each window\'s own cohorts only (both sides)'}[B.ACCOUNTING]
         + "; the other two rules are sensitivities ('cohort_window' rejected: the 10-yr base and the 25-yr "
           'projection windows capture different shares of slow-release emissions)',
         'DECISION (author); LITERATURE: IPCC (2006) Guidelines Vol. 4 Ch. 2 (default transition period of soil '
         'carbon stock change after land-use conversion, D = 20 yr); the AR share is taken against global annual '
         'emissions, so the sector is measured as an annual emissions flow in both the base and the projection'),
    ]


TIMING_LIMITATIONS = [
    'Event timing is deterministic (n events evenly spaced in the building life). Resch et al. (2021, Section 2.2 '
    'and Fig. 4) model replacement years as probability-distributed; the L / n sensitivity brackets the timing '
    'within the service-life range implied by the counts, but not early or late failures.',
    'A4-A5 follows a generic technological-progress factor (Resch et al. 2021, Table 1) because it cannot be '
    'separated by material process; Horup et al. (2025, Fig. 2A, pp. 5-6) show that generic factors oversimplify '
    'material-specific trends, and Resch et al. state that "the decay functions should not be interpreted as '
    'predictions" (p. 4). Sensitivities: held at 2025 and the item S4 paths.',
    'Emissions committed after 2050 (later B2/B4 and C1-C4) are a range bounded by two conventions (2025 factors; '
    'the 2050 factors held), not a projection: the source paths end in 2050 and C1-C4 has no decarbonisation source.',
    'The repaint composition differs from the first coat but cannot be separated in the source file; repaints '
    'take the line\'s initial stage split (negligible: the paint path is the EPS proxy).',
    'Completion rate 0.95: "Jones et al. 2024" is a citation to verify (TODO: confirm the reference before '
    'submission).',
]


def register():
    """(setting, value, basis). Values are read from projection.py (the vacancy wording from
    outputs/data/baseline/overbuild_2026.json); the basis labels say whether a value rests on
    data, literature, or judgement."""
    import projection as B
    vs = vacancy_sentence(load('baseline/overbuild_2026.json'))
    return [
        ('Net replacement variant', f"{N.SCENARIOS[B.REPLACEMENT_VARIANT]}"
         + (f", replacement half-life {B.REPLACEMENT_HALF_LIFE:g} yr" if B.REPLACEMENT_VARIANT == 'REF' else ''),
         'DECISION (author): Low replacement and High replacement bound the Reference; the half-life is JUDGEMENT '
         '(not identifiable)'),
        ('Long-run net replacement window', f'{B.NET_REPLACEMENT_WINDOW[0]}-{B.NET_REPLACEMENT_WINDOW[1]}',
         'DATA: census private-dwelling counts and consents'),
        ('Demolition rate (split only)', f'{100 * B.DEMOLITION_RATE:.3f}%/yr', 'LITERATURE: BRANZ SR214'),
        ('Completion rate', f'{B.COMPLETION_RATE:.2f} (band {B.COMPLETION_RATE_BAND[0]}-{B.COMPLETION_RATE_BAND[1]})',
         'LITERATURE: bounds from Jones et al. 2024 (citation to verify)'),
        ('Completion lag', f'{B.COMPLETION_LAG}', "DATA: Little's law W = L / lambda (a lower bound)"),
        ('2026 overbuild rule', f'{B.OVERBUILD_RULE}: 2026 building observed ({B.NOWCAST_METHOD})',
         'DATA (observed consents); method stated'),
        ('2026 overbuild from 2027', f'gap vs the {B.OVERBUILD_GAP_REF} requirement, fading at rho; booked as '
         f'{B.OVERBUILD_BOOKING}, absorbed by {B.OVERBUILD_ABSORPTION_END} (normalised logistic from '
         f'{B.OVERBUILD_ABSORPTION_START})',
         'THEORY: reversion to the equilibrium vacancy (Rosen & Smith 1983; Wheaton 1990; DiPasquale & Wheaton '
         '1992; Gabriel & Nothaft 2001) fixes the direction, not the speed; 2035 the common RECC window; never / by '
         '2030 / by 2045, redevelopment booking and gap-vs-2026 as sensitivities'),
        ('Population 2026', 'observed' if B.NOWCAST_POPULATION else 'projected median',
         'DATA: Stats NZ ERP (see README)'),
        ('Household-size shape', f'Stats NZ {B.HH_SIZE_VARIANT}, anchored {B.S_ANCHOR_YEAR}, tail {B.S_TAIL}',
         'DATA (2018-base projections; N4 open)'),
        ('Vacancy-rate parameter', _cap(vs) if vs else 'The vacancy-rate parameter is held at its published 2023 '
         'census value (outputs/data/baseline/overbuild_2026.json missing: series values not shown)',
         'DATA: census 2023 (2018 empty count unrated, F1)'),
        ('Typology mix', f"shares held at the {B.MIX_HELD_WINDOW[0]}-{B.MIX_HELD_WINDOW[1]} consented average in "
         'every variant (2026: the observed consented mix)', 'DECISION (author): internal to the model (it weights '
         'the case-study factors) and not reported; a change of mix is a pathway question for later work'),
        ('Dwelling size reference', f'{B.DWELLING_SIZE_REF[0]}-{B.DWELLING_SIZE_REF[1]}', 'DATA: consents'),
        ('Retirement-village share reference', f'{B.RV_SHARE_REF[0]}-{B.RV_SHARE_REF[1]}', 'DATA: consents'),
        ('Soil carbon loss', f"all floor area except the {N.BANDS['replacement']} and {N.BANDS['redevelopment']} bands; zero on those bands"
         if not B.SOIL_ON_REPLACEMENT else 'all floor area (original)',
         'LITERATURE: 58.77 kg CO2e/m2 footprint, Auckland land zoned for urbanisation to ~2050, 10 soil orders '
         '(Christoforatos, Pickering & Schipper 2026, J. Environ. Manage. 415, 130603)'),
        ('Material decarbonisation', {'none': 'none: all factors held at 2025 (frozen technology)',
                                      'horup_item': 'horup_item: A1-A3 of each case-study EPD item scaled by the GWP '
                                      'path of its mapped S4 material, 2026-2050'}[B.DECARB_MODE],
         'DECISION (author); LITERATURE: Horup et al. 2025, Sci. Total Environ. 966, 178780, Fig. 2 and SI '
         'Table S4 (average of 9 premise scenarios, relative to 2025)'),
        ('Decarbonised life-cycle stages', 'A1-A3 item paths (construction and events); A4-A5 as below; C1-C4 '
         'held at 2025; soil carbon loss never', 'DECISION (author): Horup\'s scope is material production '
         '(A1-A3); soil carbon loss is not material production'),
        ('Interpolation between 2025, 2030, 2040, 2050', 'linear',
         'DECISION (author): Horup et al. state "interpolated" without naming the method (p. 3)'),
        *({'none': [], 'horup_item': item_register()}[B.DECARB_MODE]),
        *timing_register(),
        ('Carbon-factor sensitivity rows (decarbonised runs)', 'an alternative materials factor (jackknife, '
         'single case study) follows the adopted factor\'s relative path over time: factor_alt x (materials '
         'intensity(t) / 2025 value)', 'DECISION (author)'),
        ('History and acquired-rights base', 'always 2025 factors ("at 2025 factors"); decarbonisation applies '
         'to 2026-2050 only; the base follows the projection\'s accounting rule (materials and construction '
         '(A1-A5) and soil carbon loss of the construction in the period, plus the maintenance (B2, B4) events in '
         'the period of the cohorts built in it). Historical carbon appears only for the AR base window (figure '
         'D21) and the base-window rows',
         'DECISION (author): no historical factor series exists for the case studies (limitation)'),
    ]


DECARB_LIMITATIONS = [
    'Decarbonisation paths are relative changes for European and global market processes modelled with premise on '
    'ecoinvent 3.9.1 (Horup et al. 2025); they are applied as relative changes to New Zealand case-study factors. '
    'This assumes NZ material supply decarbonises at the same relative rate as those markets, which is not tested.',
    'Items without a counterpart in Horup et al. follow a labelled proxy path (polymers, paint and SIP at EPS, the '
    'smallest reduction in the set; gypsum plasterboard at clay brick) or are held at 2025 (the lift); the proxies '
    'are a judgement, bracketed by holding them at 2025 (sensitivity).',
    'C1-C4 (end of life) is held at 2025 factors (no source for end-of-life decarbonisation); future end-of-life '
    'technology would lower the committed emissions (conservative).',
    'Horup et al. (2025) SI Table S4 gives the average of the 9 premise scenarios only; the scenario range is shown '
    'graphically in their Fig. 2, so no low/high decarbonisation path is implemented.',
]


LIMITATIONS = [
    'No national demolition data: demolition of detached buildings up to three storeys is consent-exempt, so '
    'the implied replacement rates cannot be tested against a count.',
    'N4 (open): the Low/High household-size variants (deterministic) are paired with stochastic population '
    'percentiles through one draw z, and the total vs private-household population question is unresolved '
    'until the living-arrangement table (E2); the household projections are 2018-base, with Stats NZ\'s '
    '2023-base release (late 2026) to be adopted in a later version.',
    'Timber end of life (C1-C4) excludes biogenic CO2 (confirmed by the author). Whether it includes landfill '
    'methane is TO CONFIRM from Christoforatos & Pickering 2025 (author check).',
    'With the typology mix held in every variant (internal to the model: it weights the case-study factors), '
    'neither the variants nor the Monte Carlo carry typology-mix uncertainty; a change of mix is a pathway '
    'question for later work, not a baseline uncertainty.',
    'The soil factor was derived for Auckland\'s future urban zones and is applied nationally.',
    'The case-study carbon factor for apartments rests on one independent case study (A_1 and A_2 are one design '
    'at two scales).',
    'The regional analysis of the recent replacement surge (replacement half-life by territorial authority) is deferred.',
    'Net replacement persistence (the replacement half-life of the Reference) is not identifiable from the census '
    'record; Low replacement and High replacement bound it.',
    'The 2018 census empty-dwelling count has no quality rating (DataInfo+); the vacancy terms rely on it.',
    'The 2026 overbuild fades at the persistence estimated on the calibrated stock identity (rho), not on '
    'market cycles (an assumption).',
    'W from Little\'s law is a lower bound on the completion lag.',
    'Retirement-village floor area is reported but out of carbon scope.',
]


def _payback():
    p = SENSITIVITY
    if not os.path.exists(p):
        return None
    s = pd.read_csv(p).set_index('case')['floor_area_change_pct']
    k = 'Overbuild never absorbed (MODEL v2.1 Reference)'
    return float(s[k]) if k in s else None


def lines():
    """The Markdown lines of the baseline-projection part, without the document title and its
    'generated by' note; section headings at '##' (tools/methods_draft.py demotes them by one level)."""
    b, m = load('baseline/projection.json'), load('metrics.json')
    sc, v = load('baseline/scenarios.json'), load('baseline/validation.json')
    gap, nj = load('baseline/gap_2026.json'), load('baseline/overbuild_2026.json')
    if b is None or m is None:
        raise SystemExit('Run run_all.py first (outputs/data/baseline/projection.json or outputs/data/metrics.json '
                         'missing).')
    st = b['settings']
    run = N.SCENARIOS[st['scenario']] + (f" (net replacement half-life {st['replacement_half_life']:g} yr)"
                                         if st['scenario'] == 'REF' else '')
    L = [f"Every result below is read from the run outputs (outputs/data/; settings from projection.py). Adopted "
         f"run: {run}; 2026 overbuild rule `{st['overbuild_rule']}`.", '']
    if (m or {}).get('run_mode', 'full') != 'full':
        L[0:0] = ['> **' + m['run_mode'] + '** (run_all.py --quick: fewer Monte Carlo draws, no frozen-technology '
                  'Monte Carlo).', '']

    # ---- summary ----
    rows = sc['scenarios'] if sc else {}
    L += ['## Summary', '']
    tr = b.get('accounting') == 'time_resolved'
    cm = b.get('committed') or {}
    if tr:
        txt = (f"New Zealand is projected to build {b['floor_area_Mm2']:.1f} million m² of new residential floor area in "
               f"2026-2050 in the Reference. In 2026-2050 this emits {b['carbon_kt'] / 1e3:.1f} Mt CO₂e: "
               f"{b['upfront_kt'] / 1e3:.1f} Mt from materials and construction (A1-A5) and soil carbon loss, counted "
               f"in the construction year, and {b['maintenance_kt']:,.0f} kt of maintenance (B2, B4), 2026-2050. A "
               f"further {cm['lower_kt'] / 1e3:.1f}-{cm['upper_kt'] / 1e3:.1f} Mt is committed after 2050 (later "
               f"B2/B4 and C1-C4; outputs/reports/reconciliation.md).")
    else:
        txt = (f"New Zealand is projected to build {b['floor_area_Mm2']:.1f} million m² of new residential floor area in "
               f"2026-2050 in the Reference, embodying {b['carbon_kt'] / 1e3:.1f} Mt CO₂e over the life cycle, "
               f"of which {b['upfront_kt'] / 1e3:.1f} Mt is materials and construction (A1-A5) and soil carbon loss.")
    if 'LOW' in rows and 'HIGH' in rows:
        txt += (f" How fast existing dwellings are replaced is the largest structural uncertainty: "
                f"{N.SCENARIOS['LOW']} (the long-run rate throughout) gives {rows['LOW']['floor_area_Mm2']:.1f} "
                f"million m², {N.SCENARIOS['HIGH']} (the 2018-2023 rate persisting) "
                f"{rows['HIGH']['floor_area_Mm2']:.1f} million m².")
    ref_mc = layout.montecarlo('summary', 'REF', frozen=False)
    if os.path.exists(ref_mc):
        r = pd.read_csv(ref_mc, index_col=0).loc['floor_area_Mm2']
        txt += (f" Within the Reference, joint uncertainty in the inputs gives a 90% interval of "
                f"{r['p5']:.1f}-{r['p95']:.1f} million m² (median {r['p50']:.1f}, mean {r['mean']:.1f}).")
        _sp = SENSITIVITY
        if os.path.exists(_sp):
            _s = pd.read_csv(_sp).set_index('case')['carbon_kt']
            _pair = lambda a, b_: (f"{_s[a]:,.0f}-{_s[b_]:,.0f} kt" if a in _s and b_ in _s else 'n/a')
            txt += (f" Outside the Monte Carlo, carbon-factor and soil bounds on the Reference carbon "
                    f"({b['carbon_kt']:,.0f} kt): case-study jackknife "
                    f"{_pair('Materials: jackknife low (all typologies)', 'Materials: jackknife high (all typologies)')}, "
                    f"single case study {_pair('Materials: lowest single case study', 'Materials: highest single case study')}, "
                    f"soil order {_pair('Soil carbon: lowest soil order (Raw)', 'Soil carbon: highest soil order (Organic)')}.")
    txt += (f" Population uncertainty alone (Stats NZ 5th-95th percentiles) spans "
            f"{b['population_band_floor_area_Mm2']['5th']:.1f}-{b['population_band_floor_area_Mm2']['95th']:.1f} million m².")
    if os.path.exists(ref_mc):
        txt += (" The joint interval is narrower than the population-only range because each population draw "
                "also moves household size along the matching Stats NZ Low/High variant: low-population variants "
                "come with smaller households (an older age structure), so the number of households varies less "
                "than population, whereas the population-only range holds household size on the Medium shape.")
    if not tr:
        txt += (f" Materials and construction (A1-A5) and soil carbon loss ({b['upfront_kt'] / 1e3:.1f} Mt) are the "
                f"quantity comparable with a 2026-2050 budget; the later life-cycle stages are booked in the "
                f"construction year but emitted mostly after 2050.")
    L += [txt, '']

    # ---- headline ----
    L += ['## Headline, 2026-2050 (median demographics)', '',
          '| variant | floor area (Mm²) | vs Reference | ' + ('carbon 2026-2050' if tr else 'whole-life carbon')
          + ' (kt CO₂e) | of which soil carbon loss | carbon excl. soil carbon loss | materials and construction '
          '(A1-A5) + soil carbon loss (kt CO₂e) |', '|---|---|---|---|---|---|---|']
    base = rows.get('REF', {}).get('floor_area_Mm2', b['floor_area_Mm2'])
    for k in ('LOW', 'REF_HL5', 'REF', 'REF_HL15', 'HIGH'):
        lab = N.SCENARIOS[k]
        if k in rows:
            r = rows[k]
            up = f"{r['upfront_kt']:,.0f}" if 'upfront_kt' in r else 'n/a'
            so = r.get('soil_carbon_loss_kt')
            sol = (f"{so:,.0f} | {r['carbon_kt'] - so:,.0f}") if so is not None else 'n/a | n/a'
            L.append(f"| {lab} | {r['floor_area_Mm2']:.2f} | {pct(r['floor_area_Mm2'], base)} | {r['carbon_kt']:,.0f} | {sol} | {up} |")
    mcs = [layout.montecarlo('summary', k, frozen=False) for k in ('LOW', 'REF', 'HIGH')]
    mcs = [p for p in mcs if os.path.exists(p)]
    if mcs:
        L += ['', 'Monte Carlo within each variant (joint input uncertainty; mean, median and 90% interval):', '',
              '| variant | output | mean | median | 5th | 95th |', '|---|---|---|---|---|---|']
        for p in mcs:
            s = pd.read_csv(p, index_col=0)
            name = N.SCENARIOS[os.path.basename(p)[len('summary_'):-4]]
            for row, lab in (('floor_area_Mm2', 'floor area (Mm²)'),
                             ('carbon_kt', 'carbon 2026-2050 (kt)' if tr else 'whole-life carbon (kt)'),
                             ('upfront_kt', 'materials and construction (A1-A5) + soil carbon loss (kt)')):
                if row in s.index:
                    r = s.loc[row]
                    L.append(f"| {name} | {lab} | {r.get('mean', float('nan')):,.1f} | {r['p50']:,.1f} | "
                             f"{r['p5']:,.1f} | {r['p95']:,.1f} |")
    else:
        L += ['', '*Monte Carlo summaries not found (outputs/data/montecarlo/summary_<variant>.csv): run '
              'run_all.py.*']

    # ---- decomposition ----
    L += ['', '## Why the floor area is built (Reference, median demographics)', '',
          '| demand band | floor area (Mm²) | share | carbon (kt CO₂e) |', '|---|---|---|---|']
    for d in b['demand_bands']:
        L.append(f"| {d['band']} | {d['floor_area_Mm2']:.2f} | {100 * d['floor_area_Mm2'] / b['floor_area_Mm2']:.1f}% | "
                 f"{d['carbon_kt']:,.0f} |")
    L.append(f"| **Total** | **{b['floor_area_Mm2']:.2f}** | 100% | **{b['carbon_kt']:,.0f}** |")
    if nj and nj.get('mode') == 'market_excess':
        vs = vacancy_sentence(nj)
        L += ['', '### The 2026 overbuild rule', '',
              f"2026 building is observed, not modelled: {nj['O26']:,.0f} dwellings = 0.95 x consents over the latest "
              f"12 observed months (the year to July 2026; to be replaced by calendar 2026 when published). It "
              f"exceeds the 2026 requirement by {nj['e26']:+,.0f}. From 2027 building stays above the requirement by "
              f"gap_ref x rho^(t-2026), with gap_ref = building 2026 - requirement 2027 = {nj['gap_ref']:+,.0f} and "
              f"rho = {nj['rho']:.2f} (the estimated persistence of departures from the calibrated identity). The "
              f"2027 requirement is used because the 2026 requirement is depressed by the one-off 2026 population "
              f"shortfall. The 2026 overbuild is STOCK-ADDING: the extra dwellings join the stock as additional vacant "
              f"dwellings, soil carbon loss applies (new footprints) and removals stay on the path of the replacement "
              f"variant. The surplus is absorbed by {nj.get('absorption_end')}: the remaining surplus U(t) = C(t) "
              f"(1 - w(t)), C the cumulative excess and w the normalised logistic of the levers (w(2026) = 0, "
              f"w >= 2035 = 1), and the absorbed part is built less (payback, capped at the year's building, any "
              f"shortfall carried). Market excess {nj.get('excess_2026_2050', 0.0):+,.0f} and absorbed "
              f"{-nj.get('absorbed_2026_2050', 0.0):+,.0f} dwellings over 2026-2050 "
              f"(net {nj['overbuild_2026_dwellings_2026_2050']:+,.0f}), on top of whichever replacement variant runs. "
              f"Stock-flow theory of the housing market (Rosen & Smith 1983; Wheaton 1990; DiPasquale & Wheaton 1992; "
              f"Gabriel & Nothaft 2001) fixes the direction of the adjustment, the reversion of vacancy to its "
              f"equilibrium rate, but not its speed: 2035 is the common RECC adoption window of the model and the "
              f"speed is bracketed by sensitivity rows (never absorbed, by 2030, by 2045)."
              + (f" Implied stock vacancy (1 - households / (stock + cumulative 2026 overbuild)) peaks at "
                 f"{100 * nj['vacancy']['peak']:.2f}% "
                 f"in {nj['vacancy']['peak_year']} and is {100 * nj['vacancy']['v_2050']:.2f}% in 2050, against "
                 f"{100 * nj['vacancy']['census_min']:.2f}-{100 * nj['vacancy']['census_max']:.2f}% at the censuses "
                 f"{nj['vacancy']['census_years']} (pre-2013 values on the earlier empty definition)."
                 if 'vacancy' in nj else ''),
              '', ((f"{_cap(vs)}. In 2050 implied stock vacancy is "
                    f"{100 * (nj['vacancy']['v_2050'] - nj['vacancy']['v_forward']):.1f} percentage point above the "
                    f"2023 rate"
                    + (f"; never absorbed (the MODEL v2.1 Reference) floor area would be "
                       f"{_pb:+.1f}%." if (_pb := _payback()) is not None else '.'))
                   if vs else ''),
              '', 'Caveats: the absorption speed is not identified by the eight census vacancy observations; over '
                  '2018-2023 part of the excess building went to redevelopment and household formation instead. rho '
                  'is estimated on the calibrated identity, not on market cycles. Sensitivities: booking as '
                  'stock-neutral redevelopment'
                  + (f" (implied net removals then peak at {nj['redevelopment_sensitivity']['peak_removals']:,.0f} in "
                     f"{nj['redevelopment_sensitivity']['peak_year']})" if 'redevelopment_sensitivity' in nj else '')
                  + ', absorption never, by 2030 or by 2045, and the gap measured against the 2026 '
                  'requirement.']

    # ---- material / stages (no by-typology reporting: typology is internal to the model) ----
    L += ['', '## By material (kt CO₂e, 2026-2050)', '', '| material | kt | share |', '|---|---|---|']
    mt = sum(b['material_kt'].values())
    for k, x in sorted(b['material_kt'].items(), key=lambda kv: -kv[1]):
        L.append(f'| {k} | {x:,.0f} | {100 * x / mt:.1f}% |')
    if tr:
        L += ['', '## Carbon 2026-2050 and committed after 2050 (kt CO₂e)', '', '| term | kt |', '|---|---|']
        L += [f'| {s_} | {b["stages_kt"][s_]:,.0f} |' for s_ in ('A1-A3', 'A4-A5')]
        L += [f"| soil carbon loss | {b['soil_carbon_loss_kt']:,.0f} |",
              f"| **materials and construction (A1-A5) + soil carbon loss** | **{b['upfront_kt']:,.0f}** |",
              f"| maintenance (B2, B4), 2026-2050 | {b['maintenance_kt']:,.0f} |",
              f"| **carbon 2026-2050** | **{b['carbon_kt']:,.0f}** |",
              f"| committed B2, B4 after 2050 (lower: 2050 factors held / upper: 2025 factors) | "
              f"{cm['B_lower_kt']:,.0f} / {cm['B_upper_kt']:,.0f} |",
              f"| committed C1-C4 (2025 factors) | {cm['C_kt']:,.0f} |",
              f"| **committed after 2050 (later B2/B4 and C1-C4)** | **{cm['lower_kt']:,.0f}-{cm['upper_kt']:,.0f}** |",
              '', 'Time-resolved accounting: materials and construction (A1-A5) and soil carbon loss in the '
                  'construction year, maintenance (B2, B4) in the year it occurs. Emissions committed after 2050 are '
                  'reported as a range and are not added to the 2026-2050 total. Reconciliation with whole life at '
                  'construction (the static convention): outputs/reports/reconciliation.md.']
        rc = load('baseline/reconciliation.json')
        if rc:
            f0, f1 = rc['frozen_2025_factors'], rc['adopted']
            L += ['', '| term (Reference, kt CO₂e) | 2025 factors | decarbonised |', '|---|---|---|',
                  f"| materials and construction (A1-A5) + soil carbon loss, 2026-2050 | {f0['upfront_kt']:,.0f} | "
                  f"{f1['upfront_kt']:,.0f} |",
                  f"| maintenance (B2, B4), 2026-2050 | {f0['maintenance_kt']:,.0f} | {f1['maintenance_kt']:,.0f} |",
                  f"| committed after 2050: B2, B4 (upper) | {f0['b_committed_upper_kt']:,.0f} | "
                  f"{f1['b_committed_upper_kt']:,.0f} |",
                  f"| committed after 2050: C1-C4 | {f0['c_committed_kt']:,.0f} | {f1['c_committed_kt']:,.0f} |",
                  f"| sum | {rc['sum_2025_factors_kt']:,.0f} | {rc['sum_adopted_upper_kt']:,.0f} |",
                  f"| whole life at construction, A4-A5 held (static convention) | "
                  f"{rc['whole_life_2025_factors_kt']:,.0f} | {rc['whole_life_a45_held_kt']:,.0f} |",
                  f"| difference: A4-A5 of construction + maintenance (B2, B4) 2026-2050, decarbonised | 0 | "
                  f"{-rc['a45_construction_decarbonisation_kt'] - rc['maintenance_decarbonisation_kt']:,.0f} |"]
    else:
        L += ['', '## Materials and construction, soil carbon loss and whole life (kt CO₂e)', '', '| stage | kt |',
              '|---|---|']
        for s_, x in b['stages_kt'].items():
            L.append(f'| {s_} | {x:,.0f} |')
        L += [f"| soil carbon loss | {b['soil_carbon_loss_kt']:,.0f} |",
              f"| **materials and construction (A1-A5) + soil carbon loss** | **{b['upfront_kt']:,.0f}** |",
              f"| **whole-life** | **{b['carbon_kt']:,.0f}** |",
              '', 'Later stages (B, C) are booked in the construction year (static LCA convention).']
    L += [
          '', '### Soil method', '',
          'Soil carbon loss is the loss of soil organic carbon when land is built on (land-use change): a new '
          'building footprint seals the soil under it, while a rebuilt footprint sits on soil already sealed. '
          f"Soil carbon loss is therefore applied to all floor area except the {N.BANDS['replacement']} band (demolition, "
          f"net of unconsented additions) and the {N.BANDS['redevelopment']} band, where it is zero. "
          'The factor is 58.77 kg CO₂e per m² '
          'of footprint, the area-weighted average over the 10 soil orders of the land zoned for urbanisation '
          'to about 2050 in Auckland, divided by each typology\'s floor space index (Christoforatos, '
          'Pickering & Schipper 2026, Journal of Environmental Management 415, 130603, '
          'https://doi.org/10.1016/j.jenvman.2026.130603). The Raw and Organic soil-order extremes are the '
          'bounding sensitivity. Carbon factors for materials come from 16 New Zealand case studies '
          '(Christoforatos & Pickering 2025, Smart and Sustainable Built Environment, '
          'https://doi.org/10.1108/SASBE-06-2025-0304).']

    # ---- validation ----
    if v:
        vd = v.get('vacancy_definition') or {}
        pub = {(r['origin'], r['method']): r for r in (v.get('hindcast_as_published') or [])}
        L += ['', '## Validation', '', 'Rolling-origin hindcast of dwellings built (actual households and vacancy '
              'fed in; the net-replacement term predicted). Vacancy on a consistent definition'
              + (f" (the pooled 2018/2023 empty share, {100 * vd['pooled_share']:.1f}% of unoccupied, at every census; "
                 f"the 2013 census share was {100 * vd['share_2013']:.1f}%, and published empty vacancy falls "
                 f"{100 * vd['v_2013']:.2f}% -> {100 * vd['v_2018']:.2f}% across the 2013->2018 definitional break)"
                 if vd else '') + '; vacancy as published in the last column.', '',
              '| origin | test years | long-run rate (Low replacement rule) error | Reference rule error | '
              'best alternative | Reference rule, vacancy as published |', '|---|---|---|---|---|---|']
        for o in sorted({r['origin'] for r in v['hindcast']}):
            rr = [r for r in v['hindcast'] if r['origin'] == o]
            mm = [r for r in rr if r['method'] == v['model_method']][0]
            ref = [r for r in rr if r['method'] == 'reference']
            alt = min((r for r in rr if r['method'] not in (v['model_method'], 'reference')),
                      key=lambda r: abs(r['error_pct']))
            L.append(f"| {o} | {mm['test']} | {mm['error_pct']:+.1f}% | "
                     f"{(format(ref[0]['error_pct'], '+.1f') + '%') if ref else 'n/a'} | "
                     f"{alt['method']} {alt['error_pct']:+.1f}% | "
                     f"{(format(pub[(o, 'reference')]['error_pct'], '+.1f') + '%') if (o, 'reference') in pub else 'n/a'} |")
        _ref = sorted((r['origin'], r['error_pct']) for r in v['hindcast'] if r['method'] == 'reference')
        if _ref:
            _early = [e for o_, e in _ref if o_ < 2018]
            L += ['', (f"Under a consistent vacancy definition the Reference rule reproduces building from the 2006 "
                       f"and 2013 origins to 2023 within {min(abs(e) for e in _early):.0f}-{max(abs(e) for e in _early):.0f}%; "
                       f"the residual miss ({[e for o_, e in _ref if o_ == 2018][0]:+.1f}% from 2018) is the 2018-23 surge."
                       if _early and any(o_ == 2018 for o_, _ in _ref) else '')]
        c = v['check_2026']
        if c.get('status') == 'observed':
            L += ['', f"2026 check (model run without any observed-2026 input): observed consents Jan-Jul "
                      f"{c['observed_ytd']:,.0f} vs model {c['model_expected_ytd']:,.0f}; ratio "
                      f"{c['ratio_observed_to_model']:.2f}."]
        if gap:
            r3 = [r for r in gap['rows'] if r['scenario'].startswith(N.SCENARIOS['REF'])][0]
            L += [f"Decomposition of the 2026 gap in the Reference ({r3['C26_estimate']}): "
                  f"{r3['gap'] - r3['scenario_adds']:+,.0f} dwellings = population {r3['population']:+,.0f} + "
                  f"pipeline from 2025 {r3['pipeline']:+,.0f} + 2026 consents above requirement "
                  f"{r3['residual']:+,.0f}."]

    # ---- the 2026 gap as a finding ----
    if gap and v and nj:
        r1 = gap['rows'][0]
        r3 = [r for r in gap['rows'] if r['C26_estimate'] == r1['C26_estimate']
              and r['scenario'].startswith(N.SCENARIOS['REF'])][0]
        req3 = r3['model'] + r3['scenario_adds']
        c = v['check_2026']
        L += ['', '## Finding: 2026 building runs well above the model\'s requirement', '',
              f"Consents for January-July 2026 ({c['observed_ytd']:,.0f}) are {c['ratio_observed_to_model']:.2f} "
              f"times what the Reference, run without any 2026 data, implies for those months. In "
              f"completions, observed-implied 2026 building is {r3['observed_implied']:,.0f} dwellings against a "
              f"Reference requirement of {req3:,.0f} (gap {r3['observed_implied'] - req3:+,.0f})[^low]. "
              f"Population does not explain it: population growth over the year to June 2026 fell short of the "
              f"projection, which lowers the requirement by {-r3['population']:,.0f}. The gap is building already "
              f"in the pipeline from 2025 ({r3['pipeline']:+,.0f}) plus 2026 consents above requirement "
              f"({r3['residual']:+,.0f}). Over 2018-2023 most building above household formation went to "
              f"redevelopment (net removals {gap['boom_2018_2023']['net_removals']:,.0f}) rather than vacancy "
              f"({gap['boom_2018_2023']['vacancy_rate_rise_absorbed']:+,.0f}).",
              '', (f"The model takes 2026 building from the observed consents and carries the excess forward as "
                   f"the 2026 overbuild ({nj['e26']:+,.0f} dwellings in 2026, then gap_ref {nj['gap_ref']:+,.0f} "
                   f"fading at rho = {nj['rho']:.2f}; market excess {nj.get('excess_2026_2050', 0.0):+,.0f} dwellings over "
                   f"2026-2050, absorbed by {nj.get('absorption_end')}, net {nj['overbuild_2026_dwellings_2026_2050']:+,.0f})."),
              '', f"[^low]: In {r1['scenario']} the requirement is {r1['model']:,.0f} and the gap "
                  f"{r1['gap']:+,.0f} = population {r1['population']:+,.0f} + pipeline {r1['pipeline']:+,.0f} + "
                  f"2026 consents above requirement {r1['residual']:+,.0f}."]

    # ---- reality checks ----
    rcj = load('baseline/reality_checks.json')
    if rcj:
        names = dict(built='dwellings completed', removals_net='net removals', ppl_per_dw='people per new dwelling',
                     m2_per_res='floor area per additional resident', S='household size', size='new-dwelling size',
                     vacancy='vacancy rate')
        L += ['', '## Reality checks (projection vs the 1991-2025 range; outputs/reports/reality_checks.md)', '']
        out = [(k, q, r) for k, d in rcj.items() if k != 'handover' for q, r in d.items() if r['years_outside']]
        if not out:
            L.append('Every checked quantity stays within the 1991-2025 range in every variant.')
        for k, q, r in out:
            L.append(f"- {N.SCENARIOS.get(k, k)}: {names.get(q, q)} outside the range in {r['years_outside']} years "
                     f"from {r['first_outside']} (max {r['max_above_pct']:.1f}% above / {r['max_below_pct']:.1f}% "
                     f"below).")
        if 'handover' in rcj:
            h = rcj['handover']
            L.append(f"- Handover 2026 -> 2027 (observed -> model, Reference): {h['step_2026_2027_pct']:+.1f}% in floor "
                     f"area, against annual changes of {h['hist_min_pct']:+.1f}% to {h['hist_max_pct']:+.1f}% in "
                     f"1992-2025 (median {h['hist_median_pct']:+.1f}%).")
        L += ['', 'Notes: household size below the historical minimum is expected from Stats NZ\'s ageing projection '
                  '(the household-size shape keeps falling as the population ages).']

    # ---- sensitivity ----
    sens = SENSITIVITY
    if os.path.exists(sens):
        s = pd.read_csv(sens)
        s = s[s.group != 'Reference'].copy()
        s['abs'] = s['floor_area_change_pct'].abs()
        s = s.sort_values('abs', ascending=False)
        L += ['', '## One-at-a-time sensitivities (floor area and carbon vs the Reference)', '',
              '| group | case | floor area (Mm²) | change | carbon change |', '|---|---|---|---|---|']
        for r in s.itertuples():
            L.append(f"| {r.group} | {r.case} | {r.floor_area_Mm2:.2f} | {r.floor_area_change_pct:+.1f}% | {r.carbon_change_pct:+.1f}% |")

    # ---- assumptions (short) ----
    import projection as BB
    A = [('DATA', 'Population: Stats NZ 2024-base projection percentiles; observed 2026 growth (DPE ERP)'),
         ('DATA', 'Household-size shape: Stats NZ 2018-base household projections, rebased on observed households'),
         ('DATA', 'Long-run net replacement: census private-dwelling counts and consents, 1991-2023'),
         ('DATA', '2026 building: 0.95 x consents over the latest 12 observed months (dwellings and floor area; the '
                  'observed 2026 typology mix weights the case-study factors inside the model)'),
         ('DATA', f'Typology mix (internal to the model): the {BB.MIX_HELD_WINDOW[0]}-{BB.MIX_HELD_WINDOW[1]} '
                  'consented average'),
         ('DATA', 'Dwelling size: consents 2023-2025; vacancy-rate parameter: the published 2023 census value'),
         ('LITERATURE', f'Completion rate {BB.COMPLETION_RATE:.2f} (Jones et al. 2024; citation to verify)'),
         ('LITERATURE', 'Demolition split 0.135%/yr (BRANZ SR214); total net replacement from census counts'),
         ('LITERATURE', 'Material carbon factors: 16 NZ case studies (Christoforatos & Pickering 2025)'),
         ('LITERATURE', f"Soil carbon loss 58.77 kg CO2e/m2 footprint, zero on the {N.BANDS['replacement']} and {N.BANDS['redevelopment']} bands "
                        '(Christoforatos, Pickering & Schipper 2026)'),
         ('JUDGEMENT', f'Net replacement: in the Reference it fades from the 2018-2023 rate to the long-run '
                       f'rate with half-life {BB.REPLACEMENT_HALF_LIFE:g} yr; Low replacement and High replacement '
                       'bound it'),
         ('JUDGEMENT', '2026 overbuild: stock-adding (vacant dwellings), fading at rho, absorbed by 2035 (logistic; '
                       'theory fixes the direction, not the speed; never / 2030 / 2045 as sensitivities)'),
         ('DECISION', 'Typology mix held in every variant (Low replacement, Reference, High replacement); internal to '
                      'the model (it weights the case-study factors) and not reported'),
         ('JUDGEMENT', 'Household size: interpolation through all published Stats NZ values (2018-2043), held '
                       'constant beyond 2043 with zero slope imposed at 2043'),
         ('JUDGEMENT', 'No completion lag (same-year consents x 0.95)')]
    pb = (m or {}).get('aesa')
    if pb:
        L += ['', '## Planetary-boundary layer (AESA): climate change', '',
              f"Against the {pb['source_pair_label']}, allocated to the sector by acquired rights (AR; Horup et al. "
              f"2025) and ability to pay (AtP; Hjalsted et al. 2021), the boundary is {pb['B_AR_2026_kt']:,.1f} kt "
              f"CO2e (AR) and {pb['B_AtP_2026_kt']:,.2f} kt (AtP) in 2026, and {pb['B_AR_2050_kt']:,.1f} / "
              f"{pb['B_AtP_2050_kt']:,.2f} kt in 2050 (AtP = {100 * pb['B_AtP_over_B_AR']:.1f}% of AR in every year). "
              f"Over 2026-2050 the Reference exceeds them {pb['cum_LoE_AR_REF']:.2f}-fold (AR; Monte Carlo p5-p95 "
              f"{pb['cum_LoE_AR_REF_mc_p5']:.2f}-{pb['cum_LoE_AR_REF_mc_p95']:.2f}) and "
              f"{pb['cum_LoE_AtP_REF']:.1f}-fold (AtP; {pb['cum_LoE_AtP_REF_mc_p5']:.1f}-"
              f"{pb['cum_LoE_AtP_REF_mc_p95']:.1f}). The two principles are a range and are not averaged. "
              'Methods, constants, sources and limitations: the AESA section of outputs/reports/METHODS_DRAFT.md; '
              'settings: outputs/reports/ASSUMPTIONS.md.']
        pr = load('aesa/results.json') or {}
        cr = (pr.get('committed') or {}).get('REF')
        if cr:
            L[-1] += (f" The emissions committed after 2050 (later B2/B4 and C1-C4) by the 2026-2050 cohorts "
                      f"({cr['lower_kt']:,.0f}-{cr['upper_kt']:,.0f} kt) equal {cr['years_of_B_AR_2050_lower']:.0f}-"
                      f"{cr['years_of_B_AR_2050_upper']:.0f} years of the 2050 AR boundary; they fall after 2050 and "
                      'are not part of the cumulative LoE 2026-2050.')
    L += ['', '## Assumptions', '', '| basis | assumption |', '|---|---|'] + [f'| {b_} | {a_} |' for b_, a_ in A]

    # ---- register ----
    L += ['', '## Assumption register (values read from projection.py)', '', '| setting | value | basis |',
          '|---|---|---|']
    for a, val, basis in register():
        L.append(f'| {a} | {val} | {basis} |')
    L += ['', '## Open limitations and data needs', ''] + [
        f'- {x}' for x in LIMITATIONS + overbuild_limitations() + decarb_limitations(BB.DECARB_MODE)
        + TIMING_LIMITATIONS]

    L += ['', '## Figures', '', 'The figures of the paper: outputs/paper/PAPER.md; Extended Data: outputs/extended_data/EXTENDED_DATA.md; '
          'every other figure: '
          'outputs/diagnostics/DIAGNOSTICS.md. Where the projection leaves the 1991-2025 range: '
          'outputs/reports/reality_checks.md.']
    return L


def main():
    """The methods draft is one document: tools/methods_draft.py writes it with this part."""
    import methods_draft
    methods_draft.main()


if __name__ == '__main__':
    main()
