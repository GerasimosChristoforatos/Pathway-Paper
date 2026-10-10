"""The grouped sensitivity tables (MODEL v2.0.0, docs/SENSITIVITY_PLAN.md) agree with their sources."""
import json
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'outputs', 'data')


def data(rel):
    return os.path.join(DATA, rel)


@pytest.fixture(scope='module')
def tables():
    return {k: pd.read_csv(data(f'sensitivity/{k}.csv')) for k in ('reference_carbon', 'p5_carbon', 'planetary_boundary')}


def test_reference_rows_from_sources(tables):
    t = tables['reference_carbon']
    oat = pd.read_csv(data('baseline/sensitivity_one_at_a_time.csv')).set_index('case')['carbon_kt']
    ann = pd.read_csv(data('baseline/sensitivity_annual_carbon.csv')).groupby('case')['carbon_kt'].sum()
    c0 = oat['Reference (adopted settings)']
    assert np.allclose(t['central_carbon_kt'], c0, rtol=1e-12, atol=0)
    for _, r in t.iterrows():
        src = oat[r['case']] if r['case'] in oat.index else ann[r['case']]
        assert np.isclose(r['carbon_kt'], src, rtol=1e-12, atol=0), r['case']
    # every one-at-a-time row also has its annual path, and the path sums to the table total
    for case, v in oat.items():
        if case in ann.index:
            assert np.isclose(ann[case], v, rtol=1e-9, atol=0), case


def test_reference_population_rows_are_the_engine_paths(tables):
    t = tables['reference_carbon'].set_index('case')
    with open(data('aesa/results.json')) as f:
        pp = json.load(f)['population_paths']
    for pct in ('5th', '95th'):
        row = t.loc[f'Population: Stats NZ {pct} percentile (engine path)', 'carbon_kt']
        assert np.isclose(row, pp[pct]['I_kt'], rtol=1e-9, atol=0), pct


def test_p5_central_and_rows(tables):
    t = tables['p5_carbon']
    runs = pd.read_csv(data('pathways/runs.csv'))
    c = runs[(runs['scenario'] == 'REF') & (runs['run'] == 'P5-moderate')].iloc[0]
    assert np.allclose(t['central_carbon_kt'], c['carbon_kt'], rtol=1e-12, atol=0)
    a = runs[(runs['scenario'] == 'REF') & (runs['run'] == 'P5-ambitious')].iloc[0]
    r = t[t['row'] == 'P5 Combined, Ambitious'].iloc[0]
    assert np.isclose(r['carbon_kt'], a['carbon_kt'], rtol=1e-12, atol=0)
    one = t[t['group'] == 'Ambition of one pathway']
    assert len(one) == 4
    # one pathway at Ambitious lies between P5 Moderate and P5 Ambitious
    assert (one['carbon_kt'] < c['carbon_kt']).all() and (one['carbon_kt'] > a['carbon_kt']).all()
    pop = t[t['group'] == 'Demographics'].set_index('side')
    assert pop.loc['low', 'carbon_kt'] < c['carbon_kt'] < pop.loc['high', 'carbon_kt']


def test_pb_rows_from_sources(tables):
    t = tables['planetary_boundary']
    s = pd.read_csv(data('aesa/sensitivity.csv')).set_index('case')
    assert np.allclose(t['central_LoE_AR'], s.loc['reference', 'cum_LoE_AR'], rtol=1e-12, atol=0)
    assert np.allclose(t['central_LoE_AtP'], s.loc['reference', 'cum_LoE_AtP'], rtol=1e-12, atol=0)
    for _, r in t.iterrows():
        if r['source'].startswith('data/aesa/sensitivity.csv'):
            case = r['source'].split('(')[1].rstrip(')')
            assert np.isclose(r['LoE_AR'], s.loc[case, 'cum_LoE_AR'], rtol=1e-12, atol=0)
            assert np.isclose(r['LoE_AtP'], s.loc[case, 'cum_LoE_AtP'], rtol=1e-12, atol=0)
    # the AESA technology / accounting rows (vi)-(xiii) are not in the planetary-boundary tornado
    assert not t['source'].str.contains(r'\((?:vi|vii|viii|ix|x|xi|xii|xiii)_', regex=True).any()
