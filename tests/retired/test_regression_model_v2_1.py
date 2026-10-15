"""Regression lock of the pathway domain (tests/regression_v2_1.py): MODEL v2.1.0 and its MODEL v2.1.1 changes.

1. Every number of the pathway domain is locked and reproduced: the value-by-value part to 1e-12, the large files
   by their SHA-256 per row group and column (per draw for the Monte Carlo) and summary statistics.
2. Only the theoretical limit changed in MODEL v2.1.1: every key listed in tests/regression_model_v2_1_1.json is a
   TL key, so every lever, P1-P5 and Reference key of the domain is reproduced from the v2.1.0 lock unchanged.
3. The compact form detects what the value-by-value lock detected: a change of 1e-12 relative in any one value
   changes its column hash and, in the per-draw file, that draw's hash.
4. The domain is the documented one.
"""
import json
import os

import numpy as np
import pytest

import regression_v2 as R
import regression_v2_1 as R21

pytestmark = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: Monte Carlo outputs differ')
LOCK, META = R21.load_lock()
CHANGES = R21.load_changes()


@pytest.fixture(scope='module')
def cur():
    return R21.compact_values()


def test_every_domain_number_is_locked_and_reproduced(cur):
    assert LOCK, 'tests/regression_model_v2_1.json missing (tests/capture_regression_model_v2_1.py)'
    new = sorted(set(cur) - set(LOCK), key=str)
    gone = sorted(set(LOCK) - set(cur), key=str)
    bad = [(k, LOCK[k], cur[k]) for k in LOCK if k in cur and not R21.same_compact(k, LOCK[k], cur[k])]
    assert not new, f'{len(new)} domain values not locked, e.g. {new[:5]}'
    assert not gone, f'{len(gone)} locked domain values absent, e.g. {gone[:5]}'
    assert not bad, f'{len(bad)} domain values differ, e.g. {bad[:5]}'


def test_only_the_theoretical_limit_changed_in_v2_1_1():
    assert CHANGES, 'tests/regression_model_v2_1_1.json missing (tests/capture_regression_model_v2_1_1.py)'
    keys = list(CHANGES['changed']) + list(CHANGES['added']) + list(CHANGES['removed'])
    ok = lambda k: R21.is_tl_key(k) or R21.is_tl_derived(k)
    assert keys and all(ok(k) for k in keys), [k for k in keys if not ok(k)][:10]
    m = CHANGES['meta']
    assert (m['n_changed'], m['n_added'], m['n_removed']) == (len(CHANGES['changed']), len(CHANGES['added']),
                                                              len(CHANGES['removed']))
    # the lever, pathway and Reference runs are untouched: none of their keys is listed
    for k in keys:
        assert not any(str(x).startswith(('P1-', 'P2-', 'P3-', 'P4-', 'L1-', 'L9-', 'REF')) for x in k[1:2]), k


def test_tl_derived_keys_change_only_through_the_theoretical_limit():
    """The invariants behind regression_v2_1.TL_DERIVED, on the current outputs."""
    import json
    import pandas as pd
    import layout
    d = lambda rel: layout.data(rel, frozen=False)
    keys = [json.loads(k) if isinstance(k, str) and k.startswith('[') else k
            for k in list(CHANGES['changed']) + list(CHANGES['added']) + list(CHANGES['removed'])]
    derived = [k for k in keys if R21.is_tl_derived(tuple(k)) and not R21.is_tl_key(tuple(k))]
    assert derived, 'no TL-derived key recorded'
    # the waterfall step 'by2030' is the unchanged pathway run P5-moderate-by2030
    w = pd.read_csv(d('pathways/waterfall_sequential.csv'))
    r = pd.read_csv(d('pathways/runs.csv'))
    p30 = r[(r['run'] == 'P5-moderate-by2030') & (r['scenario'] == 'REF')].iloc[0]
    st = w[w['step_id'] == 'by2030']
    assert len(st) and abs(st['total_carbon_kt'].iloc[0] / p30['carbon_kt'] - 1) < 1e-12
    assert abs(st['carbon_kt'].sum() / p30['carbon_kt'] - 1) < 1e-9
    # annual.csv: the added rows are the instant TL sensitivity's
    a = pd.read_csv(d('pathways/annual.csv'))
    base_rows = R21.load_base_lock()[('data/pathways/annual.csv', '#n_rows')]
    assert len(a) - base_rows == (a['run'] == 'TL-from2027').sum() == 25
    # the pooled central-draw diagnostic stays at floating-point level
    s = pd.read_csv(d('pathways/montecarlo_summary.csv'))
    assert (s['central_draw_max_rel_diff'] < 1e-9).all()


def test_is_tl_key():
    assert R21.is_tl_key(('data/pathways/runs.csv', '["TL", "REF", "TL", "P5-moderate+TL1"]', 'carbon_kt'))
    assert R21.is_tl_key(('data/pathways/montecarlo_draws.csv', '#group', 'all', 'TL_LoE_AR', 'sha256'))
    assert R21.is_tl_key(('data/pathways/montecarlo_draws.csv', '#rows', 'TL', 7))
    assert not R21.is_tl_key(('data/pathways/runs.csv', '["P5-moderate", "REF", "moderate"]', 'carbon_kt'))
    assert not R21.is_tl_key(('data/pathways/montecarlo_draws.csv', '#group', 'all', 'P5_LoE_AR', 'sha256'))
    assert not R21.is_tl_key(('data/pathways/levers.json', 'L2/S_target/moderate/3'))


def test_compact_form_detects_a_1e_12_change():
    rng = np.random.default_rng(3)
    for x in np.concatenate([rng.lognormal(0, 6, 2000), -rng.lognormal(0, 6, 200), [1.0, 9.999999999999, 1e-300]]):
        y = x * (1 + 1e-12)
        if y != x:
            assert R21.canonical(x) != R21.canonical(y), (x, y)
    a = [R21.canonical(v) for v in (1.0, 2.0, 3.0)]
    b = [R21.canonical(v) for v in (1.0, 2.0 * (1 + 1e-12), 3.0)]
    assert R21._sha(a) != R21._sha(b)
    assert R21.canonical(-0.0) == '0' and R21.canonical(float('nan')) == 'nan' and R21.canonical(True) == 'True'


def test_the_domain_is_the_documented_one():
    dom = R21.domain_values()
    files = {k[0] for k in dom}
    assert all(f.startswith('data/pathways/') or f in ('data/sensitivity/p5_carbon.csv',
                                                       'data/sensitivity/replacement_variants.csv') for f in files)
    rv = [k for k in dom if k[0] == 'data/sensitivity/replacement_variants.csv']
    assert rv and all('Reference' not in json.loads(k[1]) for k in rv)
    for k in R.values('data/sensitivity/replacement_variants.csv'):
        if 'Reference' in json.loads(k[1]):
            assert not R21.in_domain(k)
    assert set(R21.HASHED_FILES) <= files


def test_lock_meta():
    assert META['files'] == sorted({k[0] for k in LOCK if not (len(k) > 1 and str(k[1]).startswith('#'))}
                                   | set(R21.HASHED_FILES))
    assert os.path.getsize(R21.LOCK_FILE) < 4e6
