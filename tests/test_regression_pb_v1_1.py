"""The class-level decarbonisation of baseline-pb-v1.1 (then 'horup_material',
now DECARB_MODE = 'horup_class_v1_1') must reproduce that tag's outputs
exactly (tests/regression_pb_v1_1.json, read from tag baseline-PB_v1.1,
commit 5c0cfba). The deterministic run is recomputed here; the Monte Carlo,
PB and sensitivity tables are read from that mode's run directory (outputs/
while it is the adopted mode, outputs/modes/horup_class_v1_1/ otherwise),
written by run_all before the tests. In a quick run those file checks are
skipped (fewer Monte Carlo draws)."""
import json
import math
import os

import pandas as pd
import pytest

from conftest import ROOT, run_boss

MODE = 'horup_class_v1_1'
FX = json.load(open(os.path.join(ROOT, 'tests', 'regression_pb_v1_1.json')))
quick = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: fewer Monte Carlo draws')


def run_dir():
    import Boss
    return Boss.OUT_DIR if Boss.DECARB_MODE == MODE else os.path.join(ROOT, 'outputs', 'modes', MODE)


def test_deterministic_run_reproduces_v1_1():
    B = run_boss(DECARB_MODE=MODE)
    assert B['tot_carbon_median'] == FX['boss']['carbon_kt']
    assert B['_upfront'] + B['_soil'] / 1e6 == FX['boss']['upfront_kt']
    assert B['results']['50th']['total'][1:].sum() / 1e6 == FX['boss']['gfa_Mm2']
    annual = [float(v / 1e6) for v in B['carbon_total_typ'].sum(axis=1).values]
    assert annual == FX['boss']['annual_carbon_kt']


@quick
def test_boss_results_file():
    with open(os.path.join(run_dir(), 'boss_results.json')) as f:
        b = json.load(f)
    for k, v in FX['boss'].items():
        got = b['annual']['carbon_kt'] if k == 'annual_carbon_kt' else b[k]
        assert got == v, k


@quick
def test_monte_carlo_summary():
    s = pd.read_csv(os.path.join(run_dir(), 'montecarlo_summary.csv'), index_col=0)
    for k, qs in FX['mc'].items():
        for q, v in qs.items():
            assert float(s.loc[k, q]) == v, (k, q)


@quick
def test_pb_results():
    with open(os.path.join(run_dir(), 'pb_results.json')) as f:
        pb = json.load(f)
    assert pb['deterministic'] == FX['pb']['deterministic']
    assert pb['mc'] == FX['pb']['mc']
    s = pd.read_csv(os.path.join(run_dir(), 'pb_sensitivity.csv'))
    assert {r.case: [r.cum_LoE_AR, r.cum_LoE_AtP] for r in s.itertuples()} == FX['pb_sensitivity']


def test_sensitivity_table():
    p = os.path.join(run_dir(), 'sensitivity_oat.csv')
    if not os.path.exists(p):
        pytest.skip(f'{p} not written yet (run run_all.py)')
    s = pd.read_csv(p)
    got = dict(zip(s.case, s.carbon_kt))
    assert set(got) == set(FX['sensitivity_oat'])
    for k, v in FX['sensitivity_oat'].items():
        assert (math.isnan(v) and math.isnan(got[k])) or got[k] == v, k
