"""Headline metrics of one full pipeline run, written to outputs/data/metrics.json.

Everything is read from what the pipeline itself produced: one silent
projection.main() (the Reference run) and the Monte Carlo CSVs in outputs/.
Keys carry the release names (naming.py; docs/RENAMING.md).
outputs/reports/RESULTS.md is generated from this file only, so no headline number is
ever copied by hand.

    python tools/metrics.py
"""
import contextlib
import io
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import layout  # noqa: E402
import naming as N  # noqa: E402

METRICS = layout.data('metrics.json', frozen=False)

# (key, label, format) in the order they appear in tables
FIELDS = [
    ('projection.floor_area_Mm2', 'Built floor area 2026-2050, Reference (Mm2)', '{:.2f}'),
    ('projection.carbon_kt', 'Embodied carbon 2026-2050, Reference (kt CO2e)', '{:,.0f}'),
    ('projection.upfront_kt', 'Upfront carbon (A1-A5 and soil carbon loss), Reference (kt CO2e)', '{:,.0f}'),
    ('projection.soil_carbon_loss_kt', 'Soil carbon loss, Reference (kt CO2e)', '{:,.0f}'),
    ('projection.carbon_excl_soil_kt', 'Embodied carbon excluding soil carbon loss, Reference (kt CO2e)', '{:,.0f}'),
    ('projection.step_2025_2026_pct', '2025 -> 2026 step in built floor area (%)', '{:+.1f}'),
    ('projection.S_2050', 'Household size 2050, Reference', '{:.3f}'),
    ('projection.retirement_village_floor_area_Mm2_out_of_scope',
     'Retirement-village floor area 2026-2050, out of scope (Mm2)', '{:.2f}'),
    ('projection.overbuild_2026_excess', '2026 overbuild: 2026 building above requirement (dwellings)', '{:+,.0f}'),
    ('projection.overbuild_2026_gap_ref', '2026 overbuild: gap_ref (building 2026 - requirement 2027)', '{:+,.0f}'),
    ('projection.overbuild_2026_net_dwellings', '2026 overbuild: net dwellings added 2026-2050', '{:+,.0f}'),
    ('mc.floor_area_p5', 'MC floor area p5 (Mm2)', '{:.2f}'),
    ('mc.floor_area_p50', 'MC floor area p50 (Mm2)', '{:.2f}'),
    ('mc.floor_area_mean', 'MC floor area mean (Mm2)', '{:.2f}'),
    ('mc.floor_area_p95', 'MC floor area p95 (Mm2)', '{:.2f}'),
    ('mc.carbon_p5', 'MC carbon p5 (kt)', '{:,.0f}'),
    ('mc.carbon_p50', 'MC carbon p50 (kt)', '{:,.0f}'),
    ('mc.carbon_mean', 'MC carbon mean (kt)', '{:,.0f}'),
    ('mc.carbon_p95', 'MC carbon p95 (kt)', '{:,.0f}'),
    ('mc.reference_percentile_floor_area', 'Reference run percentile in MC, floor area', '{:.1f}'),
    ('mc.reference_percentile_carbon', 'Reference run percentile in MC, carbon', '{:.1f}'),
    ('validation.hindcast_2006_model', 'Hindcast error, origin 2006, model method (%)', '{:+.1f}'),
    ('validation.hindcast_2013_model', 'Hindcast error, origin 2013, model method (%)', '{:+.1f}'),
    ('validation.hindcast_2018_model', 'Hindcast error, origin 2018, model method (%)', '{:+.1f}'),
    ('validation.hindcast_2006_reference', 'Hindcast error, origin 2006, Reference rule (%)', '{:+.1f}'),
    ('validation.hindcast_2013_reference', 'Hindcast error, origin 2013, Reference rule (%)', '{:+.1f}'),
    ('validation.hindcast_2018_reference', 'Hindcast error, origin 2018, Reference rule (%)', '{:+.1f}'),
    ('validation.model_consents_2026', '2026 model consent-equivalents (all categories)', '{:,.0f}'),
    ('validation.observed_to_model_2026', '2026 observed / model consents, year to date', '{:.3f}'),
]

# AESA layer (boundaries.py): read from outputs/data/aesa/results.json, kept apart from FIELDS
PB_FIELDS = [
    ('aesa.I_sec_base_kt', 'Mean annual sector emissions 2016-2025, same convention as projection (kt/yr)', '{:,.1f}'),
    ('aesa.base_year_b', 'GDP base year b (PPP coverage >= 98% of WDI population)', '{:d}'),
    ('aesa.alpha', 'alpha, Hjalsted SI Eq. S1, year b, PPP', '{:.4f}'),
    ('aesa.alpha_2017_current_usd', 'alpha 2017, current US$ (Hjalsted report 0.243)', '{:.4f}'),
    ('aesa.g_W_over_g_NZ', 'g_W / g_NZ, year b, PPP', '{:.4f}'),
    ('aesa.s_sec', 's_sec (consented value / FCE, 2016-2025)', '{:.7f}'),
    ('aesa.B_AR_2026_kt', 'Boundary AR 2026 (kt CO2e)', '{:,.1f}'),
    ('aesa.B_AR_2050_kt', 'Boundary AR 2050 (kt CO2e)', '{:,.1f}'),
    ('aesa.B_AtP_2026_kt', 'Boundary AtP 2026 (kt CO2e)', '{:,.2f}'),
    ('aesa.B_AtP_2050_kt', 'Boundary AtP 2050 (kt CO2e)', '{:,.2f}'),
    ('aesa.B_AtP_over_B_AR', 'B_AtP / B_AR (constant over time)', '{:.4f}'),
    ('aesa.cum_LoE_AR_REF', 'Cumulative LoE 2026-2050, AR, Reference', '{:.2f}'),
    ('aesa.cum_LoE_AR_REF_mc_p5', 'Cumulative LoE AR, MC p5 (Reference)', '{:.2f}'),
    ('aesa.cum_LoE_AR_REF_mc_p50', 'Cumulative LoE AR, MC p50 (Reference)', '{:.2f}'),
    ('aesa.cum_LoE_AR_REF_mc_p95', 'Cumulative LoE AR, MC p95 (Reference)', '{:.2f}'),
    ('aesa.cum_LoE_AtP_REF', 'Cumulative LoE 2026-2050, AtP, Reference', '{:.1f}'),
    ('aesa.cum_LoE_AtP_REF_mc_p5', 'Cumulative LoE AtP, MC p5 (Reference)', '{:.1f}'),
    ('aesa.cum_LoE_AtP_REF_mc_p50', 'Cumulative LoE AtP, MC p50 (Reference)', '{:.1f}'),
    ('aesa.cum_LoE_AtP_REF_mc_p95', 'Cumulative LoE AtP, MC p95 (Reference)', '{:.1f}'),
]


def aesa_metrics():
    with open(layout.data('aesa/results.json', frozen=False)) as f:
        r = json.load(f)
    c, b, mc = r['components'], r['boundaries'], r['mc']['REF']
    m = dict(I_sec_base_kt=c['I_sec_base_kg'] / 1e6, base_year_b=int(c['base_year_b']), alpha=c['alpha'],
             alpha_2017_current_usd=r['alpha_check']['NY.GDP.PCAP.CD']['alpha'],
             g_W_over_g_NZ=c['g_W_over_g_NZ'], s_sec=c['s_sec'],
             B_AR_2026_kt=b['2026']['B_AR_kt'], B_AR_2050_kt=b['2050']['B_AR_kt'],
             B_AtP_2026_kt=b['2026']['B_AtP_kt'], B_AtP_2050_kt=b['2050']['B_AtP_kt'],
             B_AtP_over_B_AR=r['B_AtP_over_B_AR']['min'],
             cum_LoE_AR_REF=r['deterministic']['REF']['LoE_AR'],
             cum_LoE_AtP_REF=r['deterministic']['REF']['LoE_AtP'],
             source_pair=r['settings']['SOURCE_PAIR'], source_pair_label=c['pair_label'],
             decarb_mode=r['settings'].get('DECARB_MODE', 'none'),
             accounting=c.get('accounting', 'whole_life_at_construction'), decarb_a45=c.get('decarb_a45', 'held'),
             I_sec_base_b_share=c.get('I_sec_base_b_share'), I_sec_base_wider_scope_kt=(
                 c['I_sec_base_wider_scope_kg'] / 1e6 if c.get('I_sec_base_wider_scope_kg') is not None else None))
    for k in ('AR', 'AtP'):
        for p in (5, 50, 95):
            m[f'cum_LoE_{k}_REF_mc_p{p}'] = mc[f'LoE_{k}_p{p}']
    m['cum_LoE_by_scenario'] = {s: dict(AR=v['LoE_AR'], AtP=v['LoE_AtP']) for s, v in r['deterministic'].items()}
    m['cum_LoE_mc'] = r['mc']
    return m


def projection_metrics(settings=None):
    """settings: optional projection module settings for this run (the module is
    reloaded first), e.g. dict(DECARB_MODE='none') for the regression test."""
    import importlib
    import projection
    if settings:
        importlib.reload(projection)
        for k, v in settings.items():
            setattr(projection, k, v)
    projection.SHOW_PLOTS = False
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            B = projection.main()
    finally:
        if settings:
            importlib.reload(projection)                     # module defaults restored
    R = B['results']['50th']
    S = B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th']
    return {
        'floor_area_Mm2': float(R['total'][1:].sum() / 1e6),
        'carbon_kt': float(B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6),
        'upfront_kt': float(B['_upfront'] + B['_soil'] / 1e6),
        'soil_carbon_loss_kt': float(B['_soil'] / 1e6),
        'carbon_excl_soil_kt': float(B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6 - B['_soil'] / 1e6),
        'step_2025_2026_pct': float(100 * (R['total'][1] / B['hist_built_gfa'].loc[2025] - 1)),
        'S_2050': float(S[-1]),
        'retirement_village_floor_area_Mm2_out_of_scope': (float(B['rv_floor_area']['projected'][1:].sum() / 1e6)
                                                           if B.get('rv_floor_area') else None),
        'overbuild_2026_excess': float(B['join_info']['50th']['e26']) if B['join_info'] else None,
        'overbuild_2026_gap_ref': float(B['join_info']['50th']['e27']) if B['join_info'] else None,
        'overbuild_2026_net_dwellings': float(B['join_info']['50th']['join'][1:].sum()) if B['join_info'] else None,
    }


def mc_metrics():
    s = pd.read_csv(layout.montecarlo('summary', 'REF', frozen=False), index_col=0)
    d = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
    m = {}
    for key, row in (('floor_area', 'floor_area_Mm2'), ('carbon', 'carbon_kt')):
        for p in (5, 50, 95):
            m[f'{key}_p{p}'] = float(s.loc[row, f'p{p}'])
        m[f'reference_percentile_{key}'] = float(100 * (d[row] < s.loc[row, 'reference']).mean())
        if 'mean' in s.columns:
            m[f'{key}_mean'] = float(s.loc[row, 'mean'])
    return m


def collect():
    m = {'projection': projection_metrics()}
    if os.path.exists(layout.montecarlo('summary', 'REF', frozen=False)):
        m['mc'] = mc_metrics()
    if os.path.exists(layout.data('aesa/results.json', frozen=False)):
        m['aesa'] = aesa_metrics()
    vfile = layout.data('baseline/validation.json', frozen=False)
    if os.path.exists(vfile):
        with open(vfile) as f:
            v = json.load(f)
        val = {f"hindcast_{r['origin']}_{r['method']}": r['error_pct'] for r in v['hindcast']}
        mm = v.get('model_method', 'constant')
        for r in v['hindcast']:
            if r['method'] == mm:
                val[f"hindcast_{r['origin']}_model"] = r['error_pct']
        val['model_consents_2026'] = v['check_2026']['model_consent_equivalent_2026']
        val['observed_to_model_2026'] = v['check_2026'].get('ratio_observed_to_model')
        m['validation'] = val
    m['run_mode'] = ('QUICK RUN, not for reporting' if os.environ.get('PATHWAY_QUICK') == '1' else 'full')
    with open(layout.writing(METRICS), 'w') as f:
        json.dump(N.keys(m), f, indent=2, sort_keys=True)
    return m


def get(m, dotted):
    for k in dotted.split('.'):
        if not isinstance(m, dict) or k not in m:
            return None
        m = m[k]
    return m


if __name__ == '__main__':
    m = collect()
    print(f'metrics -> {METRICS}')
    for key, label, f in FIELDS + PB_FIELDS:
        v = get(m, key)
        print(f'  {label:<60} {f.format(v) if v is not None else "n/a"}')
