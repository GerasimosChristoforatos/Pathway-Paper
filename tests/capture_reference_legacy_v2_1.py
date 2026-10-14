"""Capture the v2.1 Reference projection state (in memory, projection.main()) BEFORE any MODEL v3.0.0 change,
for the legacy lock (tests/test_reference_legacy.py): `--reference-legacy` (PATHWAY_REFERENCE_LEGACY=1, the overbuild
never absorbed) must reproduce every array below to 1e-12 relative.

Stored: every numeric column of df_forecast; every array of the engine result of each population percentile
(5th, 50th, 95th); the annual carbon by typology; the near-term join of each percentile.
Run once, at model-v2.1.2 (95cd074):  python tests/capture_reference_legacy_v2_1.py
"""
import contextlib
import gzip
import io
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
OUT = os.path.join(ROOT, 'tests', 'reference_legacy_v2_1.json.gz')


def state_arrays(B):
    out = {}
    df = B['df_forecast']
    for c in df.columns:
        if np.issubdtype(df[c].dtype, np.number):
            out[f'df_forecast/{c}'] = [float(x) for x in df[c].values]
    for col, E in B['engine_out'].items():
        for k, v in E.items():
            a = np.asarray(v)
            if a.dtype.kind in 'fi' and a.size:
                out[f'engine_out/{col}/{k}'] = [float(x) for x in a.ravel()]
    out['carbon_total_typ'] = [float(x) for x in np.asarray(B['carbon_total_typ'].values).ravel()]
    for col, ji in B['join_info'].items():
        out[f'join_info/{col}/join'] = [float(x) for x in np.asarray(ji['join'])]
    return out


if __name__ == '__main__':
    import projection
    projection.SHOW_PLOTS = False
    with contextlib.redirect_stdout(io.StringIO()):
        B = projection.main()
    vals = state_arrays(B)
    import subprocess
    head = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    with gzip.open(OUT, 'wt') as f:
        json.dump(dict(meta=dict(commit=head, n_arrays=len(vals)), values=vals), f)
    print(f'{len(vals)} arrays -> {OUT}')
