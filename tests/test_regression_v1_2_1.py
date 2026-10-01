"""Baseline v2 must reproduce every headline number of v1.2.1 (commit a83cf03)
to 1e-9 relative: central-run metrics and the four scenario totals are
recomputed here; the Monte Carlo summaries, the scenario table and the
sensitivity table are read from outputs/ (run_all writes them before tests)."""
import json
import os
import sys

import pandas as pd
import pytest

from conftest import ROOT

REL = 1e-9
FX = json.load(open(os.path.join(ROOT, 'tests', 'regression_v1_2_1.json')))
REMOVED_SENSITIVITY_ROWS = {'Three-channel join (v1.0.2)'}      # dropped with the three-channel join


def same(a, b):
    return abs(a - b) <= REL * max(abs(b), 1e-12)


def test_central_run_metrics():
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import metrics
    m = metrics.boss_metrics()
    bad = {k: (m[k], v) for k, v in FX['boss'].items() if v is not None and not same(m[k], v)}
    assert not bad, bad


@pytest.mark.parametrize('key', ['S1', 'S3-10', 'S2', 'S2-held'])
def test_scenario_totals_recomputed(key):
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import replacement_scenarios as RS
    settings = dict((k, s) for k, _, s in RS.SCENARIOS)[key]
    r, _ = RS.one(settings)
    bad = {f: (r[f], v) for f, v in FX['scenarios'][key].items() if not same(r[f], v)}
    assert not bad, bad


def test_scenario_table_file():
    sc = json.load(open(os.path.join(ROOT, 'outputs', 'replacement_scenarios.json')))['scenarios']
    bad = {(k, f): (sc[k][f], v) for k, d in FX['scenarios'].items() for f, v in d.items() if not same(sc[k][f], v)}
    assert not bad, bad


def test_monte_carlo_summaries():
    bad = {}
    for name, rows in FX['mc'].items():
        s = pd.read_csv(os.path.join(ROOT, 'outputs', name), index_col=0)
        for i, cols in rows.items():
            for c, v in cols.items():
                if not same(float(s.loc[i, c]), v):
                    bad[(name, i, c)] = (float(s.loc[i, c]), v)
    assert not bad, bad


def test_sensitivity_table():
    s = pd.read_csv(os.path.join(ROOT, 'outputs', 'sensitivity_oat.csv')).set_index('case')
    missing = set(FX['sensitivity']) - set(s.index) - REMOVED_SENSITIVITY_ROWS
    extra = set(s.index) - set(FX['sensitivity'])
    assert not missing and not extra, (missing, extra)
    bad = {c: (float(s.loc[c, 'GFA_Mm2']), float(s.loc[c, 'carbon_kt']), v) for c, v in FX['sensitivity'].items()
           if c in s.index and not (same(float(s.loc[c, 'GFA_Mm2']), v[0]) and same(float(s.loc[c, 'carbon_kt']), v[1]))}
    assert not bad, bad
