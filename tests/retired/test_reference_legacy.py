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

# MODEL v4.3.0. MODEL v4.2.1 made the household-size band signed and population growth gross (engine.forward,
# docs/CHANGELOG_v4_2_1.md; every total unchanged). The v2.1 bands are recovered exactly from the current ones:
#     growth_v2.1 = growth - hs_avoided,    hs_pos_v2.1 = max(0, hs_pos)
# (hs_avoided = max(0, -hs_raw) is still computed). _as_v2_1 applies this to the engine result and to df_forecast, so
# every forward year 2026-2050 is compared with the v2.1 fixture at 1e-12 as before.
# The 2025 row of the df_forecast band columns (ANCHOR_SPLIT) is not an engine result: it splits the observed 2025
# total by shares taken from the historical bands (projection.py, anchor), and the historical bands were redefined in
# MODEL v4.2 Part B (ERP/S household bridge) and v4.2.1 (signed band), so that split cannot be mapped back to v2.1.
# For 2025 the test checks the total against v2.1 (Ann_GFA_Total, 1e-12) and that the split adds up to it.
ANCHOR_SPLIT = ('Ann_GFA_Growth', 'Ann_GFA_HouseSplit_Pos', 'Ann_GFA_Consumption', 'Ann_GFA_Cons_ExtraSpace',
                'Ann_GFA_Cons_Other', 'Ann_GFA_Cons_Vacancy', 'Ann_GFA_Cons_Replacement', 'Ann_GFA_Cons_Unconsented',
                'Ann_GFA_Cons_Wave', 'Ann_GFA_Cons_RV')


def _as_v2_1(cur):
    out = dict(cur)
    for p in ('5th', '50th', '95th'):
        e = f'engine_out/{p}/'
        out[e + 'growth'] = np.asarray(cur[e + 'growth'], float) - np.asarray(cur[e + 'hs_avoided'], float)
        out[e + 'hs_pos'] = np.maximum(0.0, np.asarray(cur[e + 'hs_pos'], float))
        g, h = f'df_forecast/Ann_GFA_Growth_{p}', f'df_forecast/Ann_GFA_HouseSplit_Pos_{p}'
        out[g] = np.asarray(cur[g], float) - np.asarray(cur[f'df_forecast/Ann_GFA_HouseSplit_Avoided_{p}'], float)
        out[h] = np.maximum(0.0, np.asarray(cur[h], float))
    return out


def test_legacy_reference_reproduces_v2_1():
    with gzip.open(C.OUT, 'rt') as f:
        lock = json.load(f)
    # MODEL v4.0.0: the v2.1 completion timing and rate (the settings of run_all.py --reference-legacy)
    B = run_boss(OVERBUILD_ABSORPTION_END=None, COMPLETION_LAG_MONTHS=0, COMPLETION_RATE=0.95)
    raw = C.state_arrays(B)
    cur = _as_v2_1(raw)
    missing = sorted(set(lock['values']) - set(cur))
    assert not missing, missing[:5]
    bad = []
    for k, v in lock['values'].items():
        a, b = np.asarray(cur[k], float), np.asarray(v, float)
        if k.startswith('df_forecast/') and k.split('/')[1].rsplit('_', 1)[0] in ANCHOR_SPLIT:
            a, b = a[1:], b[1:]                  # MODEL v4.3.0: the 2025 anchor split is checked separately below
        if a.shape != b.shape:
            bad.append((k, 'shape'))
            continue
        d = np.abs(a - b) / np.maximum(np.abs(b), 1e-300)
        d[(a == 0) & (b == 0)] = 0.0
        if np.nanmax(d) > RTOL if d.size else False:
            bad.append((k, float(np.nanmax(d))))
    assert not bad, bad[:10]
    # 2025 (row 0, the observed anchor): the total equals v2.1 (checked above, Ann_GFA_Total) and its split adds up to it
    for p in ('5th', '50th', '95th'):
        f = {c: np.asarray(raw[f'df_forecast/{c}_{p}'], float)[0] for c in ANCHOR_SPLIT}   # model's own bands
        tot = np.asarray(raw[f'df_forecast/Ann_GFA_Total_{p}'], float)[0]
        assert abs(f['Ann_GFA_Growth'] + f['Ann_GFA_HouseSplit_Pos'] + f['Ann_GFA_Consumption'] - tot) <= RTOL * abs(tot)
        assert abs(f['Ann_GFA_Cons_ExtraSpace'] + f['Ann_GFA_Cons_Other'] - f['Ann_GFA_Consumption']) <= RTOL * abs(tot)
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
