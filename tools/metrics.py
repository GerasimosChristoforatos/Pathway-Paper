"""Headline metrics of one full pipeline run, written to outputs/metrics.json.

Everything is read from what the pipeline itself produced: one silent
Boss.main() (central run) and the Monte Carlo CSVs in outputs/. CHANGELOG.md
before/after tables and outputs/RESULTS.md are generated from this file only,
so no headline number is ever copied by hand.
"""
import contextlib
import io
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS = os.path.join(ROOT, 'outputs', 'metrics.json')

# (key, label, format) in the order they appear in tables
FIELDS = [
    ('boss.GFA_Mm2', 'Built floor area 2026-2050, central run (Mm2)', '{:.2f}'),
    ('boss.carbon_kt', 'Embodied carbon 2026-2050, central run (kt CO2e)', '{:,.0f}'),
    ('boss.upfront_kt', 'Upfront carbon A1-A5 + soil, central run (kt CO2e)', '{:,.0f}'),
    ('boss.soil_kt', 'Soil carbon (land-use change), central run (kt CO2e)', '{:,.0f}'),
    ('boss.carbon_excl_soil_kt', 'Embodied carbon excluding soil, central run (kt CO2e)', '{:,.0f}'),
    ('boss.step_2025_2026_pct', '2025 -> 2026 step in built floor area (%)', '{:+.1f}'),
    ('boss.S_2050', 'Household size 2050, central run', '{:.3f}'),
    ('boss.RV_floor_area_Mm2_out_of_scope', 'Retirement-village floor area 2026-2050, out of scope (Mm2)', '{:.2f}'),
    ('boss.join_excess_2026', 'Near-term join: 2026 completions above requirement (dwellings)', '{:+,.0f}'),
    ('boss.join_excess_2027', 'Near-term join: 2027 lagged-share excess (dwellings)', '{:+,.0f}'),
    ('boss.join_net_2026_2050', 'Near-term join: net dwellings added 2026-2050', '{:+,.0f}'),
    ('mc.GFA_p5', 'MC floor area p5 (Mm2)', '{:.2f}'),
    ('mc.GFA_p50', 'MC floor area p50 (Mm2)', '{:.2f}'),
    ('mc.GFA_mean', 'MC floor area mean (Mm2)', '{:.2f}'),
    ('mc.GFA_p95', 'MC floor area p95 (Mm2)', '{:.2f}'),
    ('mc.carbon_p5', 'MC carbon p5 (kt)', '{:,.0f}'),
    ('mc.carbon_p50', 'MC carbon p50 (kt)', '{:,.0f}'),
    ('mc.carbon_mean', 'MC carbon mean (kt)', '{:,.0f}'),
    ('mc.carbon_p95', 'MC carbon p95 (kt)', '{:,.0f}'),
    ('mc.central_pct_GFA', 'Central run percentile in MC, floor area', '{:.1f}'),
    ('mc.central_pct_carbon', 'Central run percentile in MC, carbon', '{:.1f}'),
    ('validation.hindcast_2006_model', 'Hindcast error, origin 2006, model method (%)', '{:+.1f}'),
    ('validation.hindcast_2013_model', 'Hindcast error, origin 2013, model method (%)', '{:+.1f}'),
    ('validation.hindcast_2018_model', 'Hindcast error, origin 2018, model method (%)', '{:+.1f}'),
    ('validation.hindcast_2006_reference_s3_10', 'Hindcast error, origin 2006, reference S3-10 (%)', '{:+.1f}'),
    ('validation.hindcast_2013_reference_s3_10', 'Hindcast error, origin 2013, reference S3-10 (%)', '{:+.1f}'),
    ('validation.hindcast_2018_reference_s3_10', 'Hindcast error, origin 2018, reference S3-10 (%)', '{:+.1f}'),
    ('validation.model_consents_2026', '2026 model consent-equivalents (all categories)', '{:,.0f}'),
    ('validation.observed_to_model_2026', '2026 observed / model consents, year to date', '{:.3f}'),
]


def boss_metrics():
    sys.path.insert(0, ROOT)
    import Boss
    Boss.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        B = Boss.main()
    R = B['results']['50th']
    S = B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th']
    return {
        'GFA_Mm2': float(R['total'][1:].sum() / 1e6),
        'carbon_kt': float(B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6),
        'upfront_kt': float(B['_upfront'] + B['_soil'] / 1e6),
        'soil_kt': float(B['_soil'] / 1e6),
        'carbon_excl_soil_kt': float(B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6 - B['_soil'] / 1e6),
        'step_2025_2026_pct': float(100 * (R['total'][1] / B['hist_built_gfa'].loc[2025] - 1)),
        'S_2050': float(S[-1]),
        'RV_floor_area_Mm2_out_of_scope': (float(B['rv_floor_area']['projected'][1:].sum() / 1e6)
                                           if B.get('rv_floor_area') else None),
        'join_excess_2026': float(B['join_info']['50th']['e26']) if B['join_info'] else None,
        'join_excess_2027': float(B['join_info']['50th']['e27']) if B['join_info'] else None,
        'join_net_2026_2050': float(B['join_info']['50th']['join'][1:].sum()) if B['join_info'] else None,
    }


def mc_metrics(out_dir):
    s = pd.read_csv(os.path.join(out_dir, 'montecarlo_summary.csv'), index_col=0)
    d = pd.read_csv(os.path.join(out_dir, 'montecarlo_draws.csv'))
    m = {}
    for key, row in (('GFA', 'GFA_Mm2'), ('carbon', 'carbon_kt')):
        for p in (5, 50, 95):
            m[f'{key}_p{p}'] = float(s.loc[row, f'p{p}'])
        m[f'central_pct_{key}'] = float(100 * (d[row] < s.loc[row, 'central']).mean())
        if 'mean' in s.columns:
            m[f'{key}_mean'] = float(s.loc[row, 'mean'])
    return m


def collect(out_dir=None, extra=None):
    out_dir = out_dir or os.path.join(ROOT, 'outputs')
    m = {'boss': boss_metrics()}
    if os.path.exists(os.path.join(out_dir, 'montecarlo_summary.csv')):
        m['mc'] = mc_metrics(out_dir)
    vfile = os.path.join(out_dir, 'validation.json')
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
    if extra:
        m.update(extra)
    with open(METRICS, 'w') as f:
        json.dump(m, f, indent=2, sort_keys=True)
    return m


def get(m, dotted):
    for k in dotted.split('.'):
        if not isinstance(m, dict) or k not in m:
            return None
        m = m[k]
    return m


def table(before, after):
    """Markdown before/after table for the CHANGELOG."""
    lines = ['| metric | before | after | change |', '|---|---|---|---|']
    for key, label, f in FIELDS:
        b, a = get(before, key), get(after, key)
        fb = f.format(b) if b is not None else 'n/a'
        fa = f.format(a) if a is not None else 'n/a'
        if b is not None and a is not None:
            d = a - b
            ch = ('0' if abs(d) < 1e-9 else
                  f'{d:+.3g}' + (f' ({100 * d / b:+.2f}%)' if b and 'pct' not in key else ''))
        else:
            ch = ''
        lines.append(f'| {label} | {fb} | {fa} | {ch} |')
    return '\n'.join(lines)


if __name__ == '__main__':
    print(json.dumps(collect(), indent=2))
