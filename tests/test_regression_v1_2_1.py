"""Baseline v2 must reproduce every headline number of v1.2.1 (commit a83cf03)
to 1e-9 relative, with carbon factors held at 2025 (DECARB_MODE 'none', frozen
technology; the adopted run decarbonises materials). Central-run metrics and the
four scenario totals are recomputed here under 'none'; the Monte Carlo
summaries, the scenario table and the sensitivity table are read from
outputs/frozen/, written by run_all's frozen-technology steps before the tests.
In a quick run (run_all.py --quick) those file checks are skipped.

Deliberate changes since v1.2.1 (baseline-pb-v2, CHANGELOG): the storyline
scenario (S2 + damped mix trend) and the 'S3-10 with the damped mix trend'
rows are removed; the High scenario 'S2-held' is now 'S2' (shares held), so
its v1.2.1 values are compared under the new key; the Monte Carlo summary of
S2 and the scenario row S2-noUC are now High (and High without the census
UC correction), whose v1.2.1-era references did not exist: they are compared
with tests/regression_v2_high.json (from the baseline-pb-v2 full run)."""
import json
import os
import sys

import pandas as pd
import pytest

from conftest import ROOT

REL = 1e-9
FROZEN = dict(DECARB_MODE='none', ACCOUNTING='whole_life_at_construction', DECARB_A45='held')   # the anchor
FROZEN_DIR = os.path.join(ROOT, 'outputs', 'frozen')
quick = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1',
                           reason='quick run: no frozen-technology Monte Carlo (not for reporting)')
FX = json.load(open(os.path.join(ROOT, 'tests', 'regression_v1_2_1.json')))
REMOVED_SENSITIVITY_ROWS = {'Three-channel join (v1.0.2)',      # dropped with the three-channel join
                            'Storyline: intensification continues (S2 + mix trend)',   # baseline-pb-v2
                            'S3-10 with the damped mix trend'}                         # baseline-pb-v2
# baseline-pb-v2: storyline removed, High renamed (v1.2.1 key -> current key)
REMOVED_SCENARIOS = {'S2', 'S3-10-trend', 'S2-noUC'}            # the v1.2.1 storyline rows
FX['scenarios'] = {('S2' if k == 'S2-held' else k): v for k, v in FX['scenarios'].items()
                   if k not in REMOVED_SCENARIOS}
# baseline-pb-v3.1: row labels made version-free and explicit (CHANGELOG); values unchanged
RENAMED_SENSITIVITY_ROWS = {
    'Stats NZ 5th percentile (level)': 'Population: Stats NZ 5th percentile',
    'Stats NZ 95th percentile (level)': 'Population: Stats NZ 95th percentile',
    'Stats NZ Low projection variant (S)': 'Household size: Stats NZ Low variant',
    'Stats NZ High projection variant (S)': 'Household size: Stats NZ High variant',
    'S after 2043: flat (kink at 2043)': 'Household size after 2043: flat (kink at 2043)',
    'S after 2043: secant-slope taper (v1.2)': 'Household size after 2043: secant-slope taper',
    'S after 2043: taper from the PCHIP end slope': 'Household size after 2043: taper from the PCHIP end slope',
    'Booked as redevelopment, stock-neutral (v1.1)': 'Booked as redevelopment, stock-neutral',
    'Soil: lowest soil order (Raw)': 'Soil carbon: lowest soil order (Raw)',
    'Soil: highest soil order (Organic)': 'Soil carbon: highest soil order (Organic)'}
FX['sensitivity'] = {RENAMED_SENSITIVITY_ROWS.get(k, k): v for k, v in FX['sensitivity'].items()}
HIGH = json.load(open(os.path.join(ROOT, 'tests', 'regression_v2_high.json')))   # baseline-pb-v2 references
FX['mc']['montecarlo_summary_S2.csv'] = HIGH['montecarlo_summary_S2.csv']
FX['scenarios'].update(HIGH['scenarios'])


def same(a, b):
    return abs(a - b) <= REL * max(abs(b), 1e-12)


def test_central_run_metrics():
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import metrics
    m = metrics.boss_metrics(FROZEN)
    bad = {k: (m[k], v) for k, v in FX['boss'].items() if v is not None and not same(m[k], v)}
    assert not bad, bad


@pytest.mark.parametrize('key', ['S1', 'S3-10', 'S2'])
def test_scenario_totals_recomputed(key):
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import replacement_scenarios as RS
    settings = dict((k, s) for k, _, s in RS.SCENARIOS)[key]
    r, _ = RS.one(dict(settings, **FROZEN))
    bad = {f: (r[f], v) for f, v in FX['scenarios'][key].items() if not same(r[f], v)}
    assert not bad, bad


@quick
def test_scenario_table_file():
    sc = json.load(open(os.path.join(FROZEN_DIR, 'replacement_scenarios.json')))['scenarios']
    bad = {(k, f): (sc[k][f], v) for k, d in FX['scenarios'].items() for f, v in d.items() if not same(sc[k][f], v)}
    assert not bad, bad


@quick
def test_monte_carlo_summaries():
    bad = {}
    for name, rows in FX['mc'].items():
        s = pd.read_csv(os.path.join(FROZEN_DIR, name), index_col=0)
        for i, cols in rows.items():
            for c, v in cols.items():
                if not same(float(s.loc[i, c]), v):
                    bad[(name, i, c)] = (float(s.loc[i, c]), v)
    assert not bad, bad


@quick
def test_sensitivity_table():
    s = pd.read_csv(os.path.join(FROZEN_DIR, 'sensitivity_oat.csv')).set_index('case')
    missing = set(FX['sensitivity']) - set(s.index) - REMOVED_SENSITIVITY_ROWS
    extra = set(s.index) - set(FX['sensitivity'])
    assert not missing and not extra, (missing, extra)
    bad = {c: (float(s.loc[c, 'GFA_Mm2']), float(s.loc[c, 'carbon_kt']), v) for c, v in FX['sensitivity'].items()
           if c in s.index and not (same(float(s.loc[c, 'GFA_Mm2']), v[0]) and same(float(s.loc[c, 'carbon_kt']), v[1]))}
    assert not bad, bad
