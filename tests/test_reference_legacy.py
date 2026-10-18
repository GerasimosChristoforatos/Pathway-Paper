"""Legacy lock (MODEL v3.0.0): with the overbuild never absorbed (projection.OVERBUILD_ABSORPTION_END = None, the
setting of run_all.py --reference-legacy), the Reference projection reproduces MODEL v2.1 to 1e-12 relative: every
numeric column of df_forecast, every array of the engine result of each population percentile, the annual carbon by
typology and the near-term join (fixture tests/reference_legacy_v2_1.json.gz, captured at model-v2.1.2, 95cd074, before
any v3 change, by tests/capture_reference_legacy_v2_1.py). The v3 Reference differs from it only through the
absorption (tested in tests/test_model_v3.py)."""
import gzip
import json
import os
import sys

import numpy as np

from conftest import ROOT, run_boss

sys.path.insert(0, os.path.join(ROOT, 'tests'))
import capture_reference_legacy_v2_1 as C  # noqa: E402

RTOL = 1e-12


def test_legacy_reference_reproduces_v2_1():
    with gzip.open(C.OUT, 'rt') as f:
        lock = json.load(f)
    # MODEL v4.0.0: the v2.1 completion timing and rate (the settings of run_all.py --reference-legacy)
    B = run_boss(OVERBUILD_ABSORPTION_END=None, COMPLETION_LAG_MONTHS=0, COMPLETION_RATE=0.95)
    cur = C.state_arrays(B)
    missing = sorted(set(lock['values']) - set(cur))
    assert not missing, missing[:5]
    bad = []
    for k, v in lock['values'].items():
        a, b = np.asarray(cur[k], float), np.asarray(v, float)
        if a.shape != b.shape:
            bad.append((k, 'shape'))
            continue
        d = np.abs(a - b) / np.maximum(np.abs(b), 1e-300)
        d[(a == 0) & (b == 0)] = 0.0
        if np.nanmax(d) > RTOL if d.size else False:
            bad.append((k, float(np.nanmax(d))))
    assert not bad, bad[:10]
    assert lock['meta']['n_arrays'] == len(lock['values']) >= 150


def test_legacy_switch_is_the_environment_flag():
    import importlib
    os.environ['PATHWAY_REFERENCE_LEGACY'] = '1'
    try:
        import projection
        M = importlib.reload(projection)
        assert M.OVERBUILD_ABSORPTION_END is None and M.REFERENCE_LEGACY
        assert M.COMPLETION_LAG_MONTHS == 0 and M.COMPLETION_RATE == 0.95
    finally:
        os.environ['PATHWAY_REFERENCE_LEGACY'] = '0'
        importlib.reload(projection)
