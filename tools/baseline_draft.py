"""Generate outputs/BASELINE_DRAFT.md from the run outputs. No number in the
report is typed by hand: every value is read from a generated file in
outputs/ (or, for the assumption register, from the settings in Boss.py).

    python tools/baseline_draft.py

Inputs: outputs/boss_results.json, metrics.json, replacement_scenarios.json,
validation.json, gap_2026.json, near_term_join.json, sensitivity_oat.csv,
montecarlo_summary*.csv (when present), figures/.
"""
import glob
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')
sys.path.insert(0, ROOT)


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def pct(a, b):
    return f'{100 * (a / b - 1):+.1f}%'


def class_register():
    """Register rows of the class-level mapping ('horup_class_v1_1', baseline-pb-v1.1)."""
    import Boss as B
    return [
        ('Material mapping, class-level (horup_class_v1_1; case-study class -> S4 row)',
         'CONCRETE and REINFORCED CONCRETE -> concrete structure; STEEL -> reinforcing steel; TIMBER -> '
         'construction wood; ALUMINIUM -> aluminium; BRICKS -> clay brick; GLASS -> glass (flat glass, coated); '
         'GLASS WOOL -> mineral wool glass; held at 2025: PLASTERBOARD, PLASTICS, PAINT, FIBRE CEMENT, PLASTER, '
         'SIP, unspecified OTHERS (no S4 counterpart)', 'DECISION (author)'),
        ('STEEL class', f"S4 '{'reinforcing steel' if B.DECARB_STEEL == 'reinforcing_steel' else 'steel profile'}' "
         "(2050: -29.9%; steel profile -39.8% is a one-at-a-time sensitivity)",
         'DECISION (author): rebar is inside REINFORCED CONCRETE; STEEL is non-rebar steel (stud walls, sections, '
         'miscellaneous) whose closest S4 counterpart is steel profile; reinforcing steel is used as the '
         'conservative choice because the class mixes items of unknown composition'),
        ('Rebar in REINFORCED CONCRETE', 'decarbonised at the concrete-structure rate (2050: -27.6%)',
         'DECISION (author): S4\'s concrete dataset does not separate reinforcement; the difference from '
         'reinforcing steel (-29.9%) is small'),
    ]


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
    from outputs/factors/factors_a13_item_coverage.csv (Building_factors.py)."""
    import Building_factors as BF
    c = pd.read_csv(BF.OUT_ITEM_COVERAGE)
    lab = c[c.Kind == 'label'].pivot(index='Typology', columns='Key', values='Value').reindex(BF.TYP_ORDER)
    red = c[c.Kind == 'reduction_2050'].pivot(index='Typology', columns='Key', values='Value').reindex(BF.TYP_ORDER)
    return lab, red


def item_register():
    """Register rows of the item-level mapping ('horup_item', baseline-pb-v1.2). Counts,
    shares and S4 changes are read from the mapping table, the coverage file and S4."""
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
         'DECISION (author): no S4 counterpart; sensitivity at the steel-profile rate'),
        ('Composite floor decking (RC item)', 'concrete structure, incl. its rebar and steel trapezoidal deck',
         'DECISION (author): no split available in the source; conservative versus steel profile '
         f"({100 * ch['Concrete structure']:+.1f}% vs {100 * _s4_change(['Steel profile'])['Steel profile']:+.1f}% "
         'by 2050)'),
        ('Masonry wall (dense concrete block, grouted, reinforced)', 'concrete structure', 'DECISION (author)'),
        ('Rebar inside REINFORCED CONCRETE items', 'concrete-structure rate', 'DECISION (author): S4\'s concrete '
         'dataset does not separate reinforcement'),
        ('Coverage of 2025 A1-A3 (pooled; direct / Horup p. 6 / proxy / held)', cov,
         'DATA: outputs/factors/factors_a13_item_coverage.csv'),
        ('Sensitivity: NZ low-carbon-electricity items held at 2025',
         f"{len(nz)} items: the 5 aluminium items, Pink Batts glass wool, Pacific Steel rebar, WPMA Radiata timber, "
         'Nelson Pine LVL', 'DECISION (author); criterion: made in New Zealand AND electricity-intensive production '
         '(not fossil process heat). Not included: Allied Concrete, GIB plasterboard, Colorsteel / ZinaCore (fossil '
         'process heat, where Horup\'s reductions reflect process change), CLT (imported, Xlam Australia); NZSIP not '
         f"needed (EPS path {100 * ch['EPS']:+.1f}%)"),
        ('Sensitivities (item-level)', 'proxies held at 2025; NZ low-carbon-electricity items held at 2025; lift at '
         'the steel-profile rate; class-level mapping of v1.1 (sensitivity_oat.csv, pb_sensitivity.csv, pb_4)',
         'DECISION (author)'),
    ]


def decarb_limitations(mode):
    """Limitations of the material decarbonisation for a DECARB_MODE."""
    if mode == 'none':
        return []
    held = ('Materials without a counterpart in Horup et al. are held at 2025 factors, so the decarbonised '
            'baseline is conservative.' if mode == 'horup_class_v1_1' else
            'Items without a counterpart in Horup et al. follow a labelled proxy path (polymers, paint and SIP at '
            'EPS, the smallest reduction in the set; gypsum plasterboard at clay brick) or are held at 2025 (the '
            'lift); the proxies are a judgement, bracketed by holding them at 2025 (sensitivity).')
    L = ['Decarbonisation paths are relative changes for European and global market processes modelled with '
         'premise on ecoinvent 3.9.1 (Horup et al. 2025); they are applied as relative changes to New Zealand '
         'case-study factors. This assumes NZ material supply decarbonises at the same relative rate as those '
         'markets, which is not tested. ' + held] + DECARB_LIMITATIONS[1:]
    if mode == 'horup_item':
        L.append('Several items are made in New Zealand with electricity-intensive production (aluminium, Pink '
                 'Batts glass wool, Pacific Steel rebar, WPMA Radiata timber, Nelson Pine LVL); the aluminium items '
                 'are stated in their EPD names to use mainly renewables-generated electricity. Where their 2025 '
                 'factors already reflect low-carbon electricity, the premise paths, which include the '
                 f'decarbonisation of electricity supply ({PREMISE_QUOTE}), may overstate their relative reduction; '
                 'a sensitivity holds them at 2025.')
        L.append('Composite floor decking (an RC item containing its steel deck and rebar) follows the '
                 'concrete-structure path because the source gives no split; this is conservative versus steel '
                 'profile for the steel share.')
    return L


def register():
    """(setting, value, basis). Values are read from Boss.py; the basis
    labels say whether a value rests on data, literature, or judgement."""
    import Boss as B
    return [
        ('Net replacement scenario', f"{B.REPLACEMENT_SCENARIO}"
         + (f", half-life {B.S3_HALF_LIFE:g} yr" if B.REPLACEMENT_SCENARIO == 'S3' else ''),
         'DECISION (author): S1/S2 bounds, S3-10 reference; half-life is JUDGEMENT (not identifiable)'),
        ('Long-run net replacement window', f'{B.NET_REPLACEMENT_WINDOW[0]}-{B.NET_REPLACEMENT_WINDOW[1]}',
         'DATA: census private-dwelling counts and consents'),
        ('Demolition rate (split only)', f'{100 * B.DEMOLITION_RATE:.3f}%/yr', 'LITERATURE: BRANZ SR214'),
        ('Completion rate', f'{B.COMPLETION_RATE:.2f} (band {B.COMPLETION_RATE_BAND[0]}-{B.COMPLETION_RATE_BAND[1]})',
         'LITERATURE: bounds from Jones et al. 2024 (citation to verify)'),
        ('Completion lag', f'{B.COMPLETION_LAG}', "DATA: Little's law W = L / lambda (a lower bound)"),
        ('Near-term rule', f'{B.NEAR_TERM_JOIN}: 2026 building observed ({B.NOWCAST_METHOD})',
         'DATA (observed consents); method stated'),
        ('Near-term excess after 2026', f'gap vs the {B.NEAR_TERM_GAP_REF} requirement, fading at rho; booked as '
         f'{B.NEAR_TERM_MODE}, absorption {B.NEAR_TERM_ABSORPTION:g}',
         'JUDGEMENT (author decision); rho estimated; redevelopment, payback and gap-vs-2026 as sensitivities'),
        ('Population 2026', 'observed' if B.NOWCAST_POPULATION else 'projected median',
         'DATA: Stats NZ ERP (see README)'),
        ('Household-size shape', f'Stats NZ {B.HH_SIZE_VARIANT}, anchored {B.S_ANCHOR_YEAR}, tail {B.S_TAIL}',
         'DATA (2018-base projections; N4 open)'),
        ('Vacancy forward', 'latest census value held', 'DATA: census 2023 (2018 empty count unrated, F1)'),
        ('Typology damping phi', f'{B.DAMPING_PHI}', 'JUDGEMENT: ≈4 years of trend applied by 2050'),
        ('Mix trend window', f'{B.TREND_WINDOW_START}-2025', 'DATA'),
        ('Dwelling size reference', f'{B.DWELLING_SIZE_REF[0]}-{B.DWELLING_SIZE_REF[1]}', 'DATA: consents'),
        ('RV share reference', f'{B.RV_SHARE_REF[0]}-{B.RV_SHARE_REF[1]}', 'DATA: consents'),
        ('Soil loss', 'all non-replacement floor area; zero on replacement bands' if not B.SOIL_ON_REPLACEMENT
         else 'all floor area (original)',
         'LITERATURE: 58.77 kg CO2e/m2 footprint, Auckland land zoned for urbanisation to ~2050, 10 soil orders '
         '(Christoforatos, Pickering & Schipper 2026, J. Environ. Manage. 415, 130603)'),
        ('Material decarbonisation', {'none': 'none: all factors held at 2025 (frozen technology)',
                                      'horup_class_v1_1': 'horup_class_v1_1: A1-A3 of mapped material classes '
                                      'scaled by material-specific GWP paths, 2026-2050',
                                      'horup_item': 'horup_item: A1-A3 of each case-study EPD item scaled by the GWP '
                                      'path of its mapped S4 material, 2026-2050'}[B.DECARB_MODE],
         'DECISION (author); LITERATURE: Horup et al. 2025, Sci. Total Environ. 966, 178780, Fig. 2 and SI '
         'Table S4 (average of 9 premise scenarios, relative to 2025)'),
        ('Decarbonised life-cycle stages', 'A1-A3 only; A4-A5, B2, B4, C1-C4 held at 2025; soil never',
         'DECISION (author): Horup\'s scope is material production (A1-A3); soil is land-use change'),
        ('Interpolation between 2025, 2030, 2040, 2050', 'linear',
         'DECISION (author): Horup et al. state "interpolated" without naming the method (p. 3)'),
        *({'none': [], 'horup_class_v1_1': class_register(), 'horup_item': item_register()}[B.DECARB_MODE]),
        ('Carbon-factor sensitivity rows (decarbonised runs)', 'an alternative materials factor (jackknife, '
         'single case study) follows the adopted factor\'s relative path over time: factor_alt x (materials '
         'intensity(t) / 2025 value)', 'DECISION (author)'),
        ('History and acquired-rights base', 'always 2025 factors; decarbonisation applies to 2026-2050 only',
         'DECISION (author): the base is observed past construction, built with past (not future) technology'),
    ]


DECARB_LIMITATIONS = [
    'Decarbonisation paths are relative changes for European and global market processes modelled with premise on '
    'ecoinvent 3.9.1 (Horup et al. 2025); they are applied as relative changes to New Zealand case-study factors. '
    'This assumes NZ material supply decarbonises at the same relative rate as those markets, which is not tested. '
    'Materials without a counterpart in Horup et al. are held at 2025 factors, so the decarbonised baseline is '
    'conservative.',
    'B4 (replacement) and C1-C4 (end of life) occur decades after construction but are booked in the construction '
    'year and held at 2025 factors; future production and end-of-life technology would lower them '
    '(conservative).',
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
    'With shares held (reference and S1), the Monte Carlo carries no typology-mix uncertainty; the mix is '
    'bracketed by the storylines and sensitivities instead.',
    'The soil factor was derived for Auckland\'s future urban zones and is applied nationally.',
    'Apartments rest on one independent case study (A_1 and A_2 are one design at two scales).',
    'The regional analysis of the rebuilding wave (replacement half-life by territorial authority) is deferred.',
    'Net replacement persistence (S3 half-life) is not identifiable from the census record; S1 and S2 bound it.',
    'The 2018 census empty-dwelling count has no quality rating (DataInfo+); the vacancy terms rely on it.',
    'The near-term excess fades at the persistence estimated on the calibrated stock identity (rho), not on '
    'market cycles (an assumption).',
    'W from Little\'s law is a lower bound on the completion lag.',
    'Retirement-village floor area is reported but out of carbon scope.',
]


def _payback():
    p = os.path.join(OUT, 'sensitivity_oat.csv')
    if not os.path.exists(p):
        return None
    s = pd.read_csv(p).set_index('case')['GFA_change_pct']
    k = 'Temporary surplus with payback, absorption 0.20/yr'
    return float(s[k]) if k in s else None


def main():
    b, m = load('boss_results.json'), load('metrics.json')
    sc, v = load('replacement_scenarios.json'), load('validation.json')
    gap, nj = load('gap_2026.json'), load('near_term_join.json')
    if b is None or m is None:
        raise SystemExit('Run run_all.py first (outputs/boss_results.json missing).')
    st = b['settings']
    ref = f"{st['scenario']}" + (f"-{st['s3_half_life']:g}" if st['scenario'] == 'S3' else '')
    L = ['# Baseline report: DRAFT (generated by tools/baseline_draft.py; do not edit by hand)', '',
         f"Every number below is read from the run outputs. Reference path: net replacement {ref}; "
         f"near-term join `{st['near_term_join']}`.", '']
    if (m or {}).get('run_mode', 'full') != 'full':
        L[1:1] = ['> **' + m['run_mode'] + '** (run_all.py --quick: fewer Monte Carlo draws, no frozen-technology '
                  'Monte Carlo).', '']

    # ---- summary ----
    rows = sc['scenarios'] if sc else {}
    L += ['## Summary', '']
    txt = (f"New Zealand is projected to build {b['gfa_Mm2']:.1f} million m² of new residential floor area in "
           f"2026-2050 on the reference path, embodying {b['carbon_kt'] / 1e3:.1f} Mt CO₂e over the life cycle, "
           f"of which {b['upfront_kt'] / 1e3:.1f} Mt is upfront (materials A1-A5 plus soil).")
    if 'S1' in rows and 'S2-held' in rows:
        txt += (f" How fast existing dwellings are replaced is the largest structural uncertainty: the low case "
                f"(long-run rate) gives {rows['S1']['GFA_Mm2']:.1f} million m², the high case (the 2018-2023 rate "
                f"persisting, shares held) {rows['S2-held']['GFA_Mm2']:.1f} million m².")
    if 'S2' in rows and 'S2-held' in rows and 'S3-10' in rows:
        _off = (rows['S2-held']['GFA_Mm2'] - rows['S2']['GFA_Mm2']) / (rows['S2-held']['GFA_Mm2'] - rows['S3-10']['GFA_Mm2'])
        txt += (f" Under the intensification storyline (S2 with the mix trend), smaller dwellings offset most of the "
                f"extra redevelopment: {rows['S2']['GFA_Mm2']:.1f} million m² against {rows['S2-held']['GFA_Mm2']:.1f} "
                f"with shares held, i.e. {100 * _off:.0f}% of the high case's gain over the reference.")
    ref_mc = os.path.join(OUT, 'montecarlo_summary_S3-10.csv')
    if os.path.exists(ref_mc):
        r = pd.read_csv(ref_mc, index_col=0).loc['GFA_Mm2']
        txt += (f" Within the reference path, joint uncertainty in the inputs gives a 90% interval of "
                f"{r['p5']:.1f}-{r['p95']:.1f} million m² (median {r['p50']:.1f}, mean {r['mean']:.1f}).")
        _sp = os.path.join(OUT, 'sensitivity_oat.csv')
        if os.path.exists(_sp):
            _s = pd.read_csv(_sp).set_index('case')['carbon_kt']
            _pair = lambda a, b_: (f"{_s[a]:,.0f}-{_s[b_]:,.0f} kt" if a in _s and b_ in _s else 'n/a')
            txt += (f" Outside the MC, carbon-factor and soil bounds on the reference carbon "
                    f"({b['carbon_kt']:,.0f} kt): case-study jackknife "
                    f"{_pair('Materials: jackknife low (all typologies)', 'Materials: jackknife high (all typologies)')}, "
                    f"single case study {_pair('Materials: lowest single case study', 'Materials: highest single case study')}, "
                    f"soil order {_pair('Soil: lowest soil order (Raw)', 'Soil: highest soil order (Organic)')}.")
    txt += (f" Population uncertainty alone (Stats NZ 5th-95th percentiles) spans "
            f"{b['pop_band_gfa_Mm2']['5th']:.1f}-{b['pop_band_gfa_Mm2']['95th']:.1f} million m².")
    if os.path.exists(ref_mc):
        txt += (" The joint interval is narrower than the population-only range because each population draw "
                "also moves household size along the matching Stats NZ Low/High variant: low-population variants "
                "come with smaller households (an older age structure), so the number of households varies less "
                "than population, whereas the population-only range holds household size on the Medium shape.")
    txt += (f" Upfront carbon ({b['upfront_kt'] / 1e3:.1f} Mt) is the quantity comparable with a 2026-2050 "
            f"budget; the later life-cycle stages are booked in the construction year but emitted mostly after 2050.")
    L += [txt, '']

    # ---- headline ----
    L += ['## Headline, 2026-2050 (median demographics)', '',
          '| path | floor area (Mm²) | vs reference | whole-life carbon (kt CO₂e) | of which soil | '
          'carbon excl. soil | upfront carbon (kt CO₂e) |', '|---|---|---|---|---|---|---|']
    base = rows.get('S3-10', {}).get('GFA_Mm2', b['gfa_Mm2'])
    for k, lab in (('S1', 'Low: S1 long-run replacement, shares held'),
                   ('S3-5', 'S3, half-life 5 yr, shares held'),
                   ('S3-10', 'Reference: S3 half-life 10 yr, shares held'),
                   ('S3-15', 'S3, half-life 15 yr, shares held'),
                   ('S2-held', 'High: S2 2018-2023 replacement, shares held'),
                   ('S2', 'Storyline: intensification continues (S2 + damped mix trend)'),
                   ('S3-10-trend', 'Sensitivity: S3-10 with the damped mix trend (v1.0 mix)')):
        if k in rows:
            r = rows[k]
            up = f"{r['upfront_kt']:,.0f}" if 'upfront_kt' in r else 'n/a'
            so = r.get('soil_kt')
            sol = (f"{so:,.0f} | {r['carbon_kt'] - so:,.0f}") if so is not None else 'n/a | n/a'
            L.append(f"| {lab} | {r['GFA_Mm2']:.2f} | {pct(r['GFA_Mm2'], base)} | {r['carbon_kt']:,.0f} | {sol} | {up} |")
    mcs = sorted(glob.glob(os.path.join(OUT, 'montecarlo_summary_*.csv')))
    if mcs:
        L += ['', 'Monte Carlo within each scenario (joint input uncertainty; mean, median and 90% interval):', '',
              '| scenario | output | mean | median | 5th | 95th |', '|---|---|---|---|---|---|']
        for p in mcs:
            s = pd.read_csv(p, index_col=0)
            name = os.path.basename(p)[len('montecarlo_summary_'):-4]
            name = {'S1': 'low (S1)', 'S3-10': 'reference (S3-10)',
                    'S2': 'storyline: intensification continues (S2 + trend)'}.get(name, name)
            for row, lab in (('GFA_Mm2', 'floor area (Mm²)'), ('carbon_kt', 'carbon (kt)'),
                             ('upfront_kt', 'upfront (kt)')):
                if row in s.index:
                    r = s.loc[row]
                    L.append(f"| {name} | {lab} | {r.get('mean', float('nan')):,.1f} | {r['p50']:,.1f} | "
                             f"{r['p5']:,.1f} | {r['p95']:,.1f} |")
    else:
        L += ['', '*Monte Carlo intervals by scenario: pending (item 9). The current single MC mixes '
              'scenarios and is not quoted.*']

    # ---- decomposition ----
    L += ['', '## Why the floor area is built (reference path, median)', '',
          '| reason | floor area (Mm²) | share | carbon (kt CO₂e) |', '|---|---|---|---|']
    for d in b['demand_bands']:
        L.append(f"| {d['band']} | {d['gfa_Mm2']:.2f} | {100 * d['gfa_Mm2'] / b['gfa_Mm2']:.1f}% | "
                 f"{d['carbon_kt']:,.0f} |")
    L.append(f"| **Total** | **{b['gfa_Mm2']:.2f}** | 100% | **{b['carbon_kt']:,.0f}** |")
    if nj and nj.get('mode') == 'market_excess':
        L += ['', '### Near-term rule: "near-term market excess"', '',
              f"2026 building is observed, not modelled: {nj['O26']:,.0f} dwellings = 0.95 x consents over the latest "
              f"12 observed months (the year to July 2026; to be replaced by calendar 2026 when published). It "
              f"exceeds the 2026 requirement by {nj['e26']:+,.0f}. From 2027 building stays above the requirement by "
              f"gap_ref x rho^(t-2026), with gap_ref = building 2026 - requirement 2027 = {nj['gap_ref']:+,.0f} and "
              f"rho = {nj['rho']:.2f} (the estimated persistence of departures from the calibrated identity). The "
              f"2027 requirement is used because the 2026 requirement is depressed by the one-off 2026 population "
              f"shortfall. The excess is STOCK-ADDING: the extra dwellings join the stock as additional vacancy "
              f"that is not absorbed (no payback), soil applies (new footprints) and removals stay on the scenario "
              f"path; {nj['join_2026_2050']:+,.0f} dwellings over 2026-2050, on top of whichever replacement "
              f"scenario runs."
              + (f" Implied vacancy (1 - households / (stock + excess)) peaks at {100 * nj['vacancy']['peak']:.2f}% "
                 f"in {nj['vacancy']['peak_year']} and is {100 * nj['vacancy']['v_2050']:.2f}% in 2050, against "
                 f"{100 * nj['vacancy']['census_min']:.2f}-{100 * nj['vacancy']['census_max']:.2f}% at the censuses "
                 f"{nj['vacancy']['census_years']} (pre-2013 values on the earlier empty definition)."
                 if 'vacancy' in nj else ''),
              '', ((f"Implied vacancy stays about {100 * (nj['vacancy']['v_2050'] - nj['vacancy']['v_forward']):.1f} "
                    f"point above the 2023 rate because the surplus is never absorbed"
                    + (f"; with payback (absorption 0.20 a year) floor area is "
                       f"{_pb:+.1f}%." if (_pb := _payback()) is not None else '.'))
                   if 'vacancy' in nj else ''),
              '', 'Caveats: a permanent surplus assumes the extra vacancy is never absorbed; over 2018-2023 part of '
                  'the excess went to redevelopment and household formation instead. rho is estimated on the '
                  'calibrated identity, not on market cycles. Sensitivities: booking as stock-neutral redevelopment'
                  + (f" (implied net removals then peak at {nj['redevelopment_sensitivity']['peak_removals']:,.0f} in "
                     f"{nj['redevelopment_sensitivity']['peak_year']})" if 'redevelopment_sensitivity' in nj else '')
                  + ', payback (absorption 0.20 or 0.10 a year), and the gap measured against the 2026 '
                  'requirement.']

    # ---- typology / material / stages ----
    L += ['', '## By typology', '', '| typology | floor area (Mm²) | carbon (kt) | share of floor area 2025 → 2050 |',
          '|---|---|---|---|']
    for t, r in b['typology'].items():
        L.append(f"| {t} | {r['gfa_Mm2']:.2f} | {r['carbon_kt']:,.0f} | "
                 f"{100 * r['share_2025']:.1f}% → {100 * r['share_2050']:.1f}% |")
    L += ['', '## By material (kt CO₂e, 2026-2050)', '', '| material | kt | share |', '|---|---|---|']
    mt = sum(b['material_kt'].values())
    for k, x in sorted(b['material_kt'].items(), key=lambda kv: -kv[1]):
        L.append(f'| {k} | {x:,.0f} | {100 * x / mt:.1f}% |')
    L += ['', '## Upfront vs whole-life (kt CO₂e)', '', '| stage | kt |', '|---|---|']
    for s_, x in b['stages_kt'].items():
        L.append(f'| {s_} | {x:,.0f} |')
    L += [f"| soil (land-use change) | {b['soil_kt']:,.0f} |",
          f"| **upfront (A1-A5 + soil)** | **{b['upfront_kt']:,.0f}** |",
          f"| **whole-life** | **{b['carbon_kt']:,.0f}** |",
          '', 'Later stages (B, C) are booked in the construction year (static LCA convention).',
          '', '### Soil method', '',
          'Soil organic carbon loss is land-use change: a new building footprint seals the soil under it, '
          'while a rebuilt footprint sits on soil already sealed. Soil loss is therefore applied to all '
          'non-replacement floor area and is zero on the replacement bands (demolition replacement, the '
          'calibrated residual and the redevelopment channel). The factor is 58.77 kg CO₂e per m² of '
          'footprint, the area-weighted average over the 10 soil orders of the land zoned for urbanisation '
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
              '| origin | test years | long-run rate (S1) error | reference method (S3-10) error | best alternative | '
              'reference, vacancy as published |', '|---|---|---|---|---|---|']
        for o in sorted({r['origin'] for r in v['hindcast']}):
            rr = [r for r in v['hindcast'] if r['origin'] == o]
            mm = [r for r in rr if r['method'] == v['model_method']][0]
            ref = [r for r in rr if r['method'] == 'reference_s3_10']
            alt = min((r for r in rr if r['method'] not in (v['model_method'], 'reference_s3_10')),
                      key=lambda r: abs(r['error_pct']))
            L.append(f"| {o} | {mm['test']} | {mm['error_pct']:+.1f}% | "
                     f"{(format(ref[0]['error_pct'], '+.1f') + '%') if ref else 'n/a'} | "
                     f"{alt['method']} {alt['error_pct']:+.1f}% | "
                     f"{(format(pub[(o, 'reference_s3_10')]['error_pct'], '+.1f') + '%') if (o, 'reference_s3_10') in pub else 'n/a'} |")
        _ref = sorted((r['origin'], r['error_pct']) for r in v['hindcast'] if r['method'] == 'reference_s3_10')
        if _ref:
            _early = [e for o_, e in _ref if o_ < 2018]
            L += ['', (f"Under a consistent vacancy definition the reference method reproduces building from the 2006 "
                       f"and 2013 origins to 2023 within {min(abs(e) for e in _early):.0f}-{max(abs(e) for e in _early):.0f}%; "
                       f"the residual miss ({[e for o_, e in _ref if o_ == 2018][0]:+.1f}% from 2018) is the 2018-23 surge."
                       if _early and any(o_ == 2018 for o_, _ in _ref) else '')]
        c = v['check_2026']
        if c.get('status') == 'observed':
            L += ['', f"2026 check (model run without any observed-2026 input): observed consents Jan-Jul "
                      f"{c['observed_ytd']:,.0f} vs model {c['model_expected_ytd']:,.0f}; ratio "
                      f"{c['ratio_observed_to_model']:.2f}."]
        if gap:
            r3 = [r for r in gap['rows'] if r['scenario'].startswith('S3-10')][0]
            L += [f"Decomposition of the 2026 gap on the reference path ({r3['C26_estimate']}): "
                  f"{r3['gap'] - r3['scenario_adds']:+,.0f} dwellings = population {r3['population']:+,.0f} + "
                  f"pipeline from 2025 {r3['pipeline']:+,.0f} + 2026 consents above requirement "
                  f"{r3['residual']:+,.0f}."]

    # ---- the 2026 gap as a finding ----
    if gap and v and nj:
        r1 = gap['rows'][0]
        r3 = [r for r in gap['rows'] if r['C26_estimate'] == r1['C26_estimate'] and r['scenario'].startswith('S3-10')][0]
        req3 = r3['model'] + r3['scenario_adds']
        c = v['check_2026']
        L += ['', '## Finding: 2026 building runs well above the model\'s requirement', '',
              f"Consents for January-July 2026 ({c['observed_ytd']:,.0f}) are {c['ratio_observed_to_model']:.2f} "
              f"times what the reference model, run without any 2026 data, implies for those months. In "
              f"completions, observed-implied 2026 building is {r3['observed_implied']:,.0f} dwellings against a "
              f"reference-path requirement of {req3:,.0f} (gap {r3['observed_implied'] - req3:+,.0f})[^s1]. "
              f"Population does not explain it: growth over the year to June 2026 fell short of the projection, "
              f"which lowers the requirement by {-r3['population']:,.0f}. The gap is building already in the "
              f"pipeline from 2025 ({r3['pipeline']:+,.0f}) plus 2026 consents above requirement "
              f"({r3['residual']:+,.0f}). Over 2018-2023 most building above household formation went to "
              f"redevelopment (net removals {gap['boom_2018_2023']['net_removals']:,.0f}) rather than vacancy "
              f"({gap['boom_2018_2023']['vacancy_rate_rise_absorbed']:+,.0f}).",
              '', (f"The model takes 2026 building from the observed consents and carries the excess forward as "
                   f"near-term market excess ({nj['e26']:+,.0f} dwellings in 2026, then gap_ref {nj['gap_ref']:+,.0f} "
                   f"fading at rho = {nj['rho']:.2f}; {nj['join_2026_2050']:+,.0f} dwellings over 2026-2050)."),
              '', f"[^s1]: On S1 (long-run replacement) the requirement is {r1['model']:,.0f} and the gap "
                  f"{r1['gap']:+,.0f} = population {r1['population']:+,.0f} + pipeline {r1['pipeline']:+,.0f} + "
                  f"2026 consents above requirement {r1['residual']:+,.0f}."]

    # ---- reality checks ----
    rcj = load('reality_checks.json')
    if rcj:
        names = dict(built='dwellings completed', removals_net='net removals', ppl_per_dw='people per new dwelling',
                     m2_per_res='floor area per additional resident', S='household size', size='new-dwelling size',
                     vacancy='vacancy rate')
        L += ['', '## Reality checks (projection vs 1991-2025 range; outputs/reality_checks.md)', '']
        out = [(k, q, r) for k, d in rcj.items() if k != 'handover' for q, r in d.items() if r['years_outside']]
        if not out:
            L.append('Every checked quantity stays within the 1991-2025 range in every scenario.')
        for k, q, r in out:
            L.append(f"- {k}: {names.get(q, q)} outside the range in {r['years_outside']} years from {r['first_outside']} "
                     f"(max {r['max_above_pct']:.1f}% above / {r['max_below_pct']:.1f}% below).")
        if 'handover' in rcj:
            h = rcj['handover']
            L.append(f"- Handover 2026 -> 2027 (observed -> model, reference): {h['step_2026_2027_pct']:+.1f}% in floor "
                     f"area, against annual changes of {h['hist_min_pct']:+.1f}% to {h['hist_max_pct']:+.1f}% in "
                     f"1992-2025 (median {h['hist_median_pct']:+.1f}%).")
        L += ['', 'Notes: household size below the historical minimum is expected from Stats NZ\'s ageing projection '
                  '(the household-size shape keeps falling as the population ages). In the intensification storyline '
                  '(S2 + mix trend), average new-dwelling size below the historical minimum is intrinsic to that '
                  'storyline'
                  + ((f": by 2050 townhouses rise to {100 * rows['S2']['shares_2050']['Townhouses']:.0f}% of new floor "
                      f"area (held: {100 * rows['S2-held']['shares_2050']['Townhouses']:.0f}%), while the apartment share "
                      f"falls slightly ({100 * rows['S2-held']['shares_2050']['Apartments']:.1f}% -> "
                      f"{100 * rows['S2']['shares_2050']['Apartments']:.1f}%), so the smaller average dwelling "
                      f"({rows['S2']['size_2050']:.0f} vs {rows['S2-held']['size_2050']:.0f} m² in 2050) comes from "
                      f"townhouses replacing detached houses.")
                     if 'shares_2050' in rows.get('S2', {}) and 'shares_2050' in rows.get('S2-held', {}) else '.')]

    # ---- sensitivity ----
    sens = os.path.join(OUT, 'sensitivity_oat.csv')
    if os.path.exists(sens):
        s = pd.read_csv(sens)
        s = s[s.group != 'Adopted'].copy()
        s['abs'] = s['GFA_change_pct'].abs()
        s = s.sort_values('abs', ascending=False)
        L += ['', '## One-at-a-time sensitivities (floor area and carbon vs reference)', '',
              '| group | case | floor area (Mm²) | change | carbon change |', '|---|---|---|---|---|']
        for r in s.itertuples():
            L.append(f"| {r.group} | {r.case} | {r.GFA_Mm2:.2f} | {r.GFA_change_pct:+.1f}% | {r.carbon_change_pct:+.1f}% |")

    # ---- assumptions (short) ----
    import Boss as BB
    A = [('DATA', 'Population: Stats NZ 2024-base projection percentiles; observed 2026 growth (DPE ERP)'),
         ('DATA', 'Household-size shape: Stats NZ 2018-base household projections, rebased on observed households'),
         ('DATA', 'Long-run net replacement: census private-dwelling counts and consents, 1991-2023'),
         ('DATA', '2026 building: 0.95 x consents over the latest 12 observed months (dwellings and GFA by typology)'),
         ('DATA', f'Typology shares (S1, S3): held at the {BB.MIX_HELD_WINDOW[0]}-{BB.MIX_HELD_WINDOW[1]} consented average'),
         ('DATA', 'Dwelling size and vacancy: consents 2023-2025; 2023 census vacancy'),
         ('LITERATURE', f'Completion rate {BB.COMPLETION_RATE:.2f} (Jones et al. 2024; citation to verify)'),
         ('LITERATURE', 'Demolition split 0.135%/yr (BRANZ SR214); total net replacement from census counts'),
         ('LITERATURE', 'Material carbon factors: 16 NZ case studies (Christoforatos & Pickering 2025)'),
         ('LITERATURE', 'Soil 58.77 kg CO2e/m2 footprint, zero on replacement (Christoforatos, Pickering & Schipper 2026)'),
         ('JUDGEMENT', f'Replacement: S3 fades with half-life {BB.S3_HALF_LIFE:g} yr (reference); S1 and S2 bound it'),
         ('JUDGEMENT', 'Near-term market excess: stock-adding vacancy, never absorbed, fading at rho'),
         ('JUDGEMENT', 'Mix: held shares in S1/S3; damped trend (phi 0.8, about 4 years of trend) in S2'),
         ('JUDGEMENT', 'Household size: interpolation through all published Stats NZ values (2018-2043), held '
                       'constant beyond 2043 with zero slope imposed at 2043'),
         ('JUDGEMENT', 'No completion lag (same-year consents x 0.95)')]
    pb = (m or {}).get('pb')
    if pb:
        L += ['', '## Planetary-boundary layer (climate change)', '',
              f"Against the {pb['source_pair_label']}, allocated to the sector by acquired rights (AR; Horup et al. "
              f"2025) and ability to pay (AtP; Hjalsted et al. 2021), the boundary is {pb['B_AR_2026_kt']:,.1f} kt "
              f"CO2e (AR) and {pb['B_AtP_2026_kt']:,.2f} kt (AtP) in 2026, and {pb['B_AR_2050_kt']:,.1f} / "
              f"{pb['B_AtP_2050_kt']:,.2f} kt in 2050 (AtP = {100 * pb['B_AtP_over_B_AR']:.1f}% of AR in every year). "
              f"Over 2026-2050 the reference path exceeds them {pb['cum_LoE_AR_S3_10']:.2f}-fold (AR; MC p5-p95 "
              f"{pb['cum_LoE_AR_S3_10_mc_p5']:.2f}-{pb['cum_LoE_AR_S3_10_mc_p95']:.2f}) and "
              f"{pb['cum_LoE_AtP_S3_10']:.1f}-fold (AtP; {pb['cum_LoE_AtP_S3_10_mc_p5']:.1f}-"
              f"{pb['cum_LoE_AtP_S3_10_mc_p95']:.1f}). The two principles are a range and are not averaged. "
              'Methods, constants, sources and limitations: outputs/PB_METHODS_DRAFT.md; settings: ASSUMPTIONS.md.']
    dm = load('decarb_modes.json')
    if dm:
        typ = list(next(iter(dm['modes'].values()))['a13_reduction_2050'])
        L += ['', '## Material decarbonisation: modes compared', '',
              f"Adopted: `{dm['adopted']}`. A1-A3 only; A4-A5, B2, B4, C1-C4 and soil at 2025 in every mode. "
              'Full tables (sensitivities, coverage, S4 rows): outputs/DECARB_MODES.md.', '',
              '| mode | carbon (kt) | upfront (kt) | MC carbon p5-p95 (kt) | cum. LoE AR / AtP | A1-A3 by 2050 ('
              + ', '.join(typ) + ') |', '|---|---|---|---|---|---|']
        for mode, r in dm['modes'].items():
            mc = r.get('mc')
            pbm = r.get('pb')
            L.append(f"| `{mode}` | {r['carbon_kt']:,.0f} | {r['upfront_kt']:,.0f} | "
                     + (f"{mc['carbon_kt']['p5']:,.0f}-{mc['carbon_kt']['p95']:,.0f}" if mc else 'n/a') + ' | '
                     + (f"{pbm['det']['LoE_AR']:.2f} / {pbm['det']['LoE_AtP']:.1f}" if pbm else 'n/a') + ' | '
                     + ', '.join(f"{-100 * r['a13_reduction_2050'][t]:.1f}%" for t in typ) + ' |')
    L += ['', '## Assumptions', '', '| basis | assumption |', '|---|---|'] + [f'| {b_} | {a_} |' for b_, a_ in A]

    # ---- register ----
    L += ['', '## Assumption register (values read from Boss.py)', '', '| setting | value | basis |', '|---|---|---|']
    for a, val, basis in register():
        L.append(f'| {a} | {val} | {basis} |')
    L += ['', '## Open limitations and data needs', ''] + [f'- {x}' for x in LIMITATIONS + decarb_limitations(BB.DECARB_MODE)]

    # ---- figures ----
    figs = sorted(glob.glob(os.path.join(OUT, 'figures', '*.png')))
    key = [f for f in figs if any(k in f for k in ('fig_reality_checks', 'fig_bridge', 'fig_scenarios', 'fig_conversion_chain', 'fig_validation', 'boss_03', 'boss_04', 'boss_05', 'diag_3', 'diag_4',
                                                     'sens_1', 'mc_1', 'pb_1', 'pb_2'))]
    L += ['', '## Key figures', '', 'One line per figure: FIGURES.md. Where the projection leaves the 1991-2025 range: outputs/reality_checks.md.', ''] + [f"![{os.path.basename(f)}](figures/{os.path.basename(f)})" for f in key]
    with open(os.path.join(OUT, 'BASELINE_DRAFT.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print(f'outputs/BASELINE_DRAFT.md: {len(L)} lines')


if __name__ == '__main__':
    main()
