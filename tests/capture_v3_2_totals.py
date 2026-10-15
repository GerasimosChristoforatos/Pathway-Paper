"""Capture the MODEL v3.2.0 run totals for the v3.3 equality test (tests/test_model_v3_3.py):
    python tests/capture_v3_2_totals.py
Source: outputs/data/pathways/runs.csv at the v3.2.0 commit (b5a8c62; deterministic, identical in both profiles), read
with git show so that the fixture is reproducible from the repository history. Each run is stored under its v3.2 id and
the id it has in MODEL v3.3.0 (naming.LEVER_V3_2: Ln-<setting> -> its new lever number; P5-<...> -> pathway-<...>).
The P1-P4 runs have no v3.3 counterpart (replaced by the strategy runs S1-S3) and are kept with run_v3_3 = null."""
import io
import json
import os
import re
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import naming as N  # noqa: E402

COMMIT = 'b5a8c62'
OUT = os.path.join(ROOT, 'tests', 'fixtures', 'v3_2_totals.json')
COLS = ('run', 'scenario', 'setting', 'levers', 'adoption', 'floor_area_Mm2', 'carbon_kt', 'B_AR_kt', 'B_AtP_kt',
        'LoE_AR', 'LoE_AtP')


def v3_3_id(run):
    m = re.match(r'^L([1-9])-(.*)$', run)
    if m:
        return f"{N.LEVER_V3_2['L' + m.group(1)]}-{m.group(2)}"
    if run.startswith('P5-'):
        return N.PATHWAY + '-' + run[3:]
    if re.match(r'^P[1-4]-', run):
        return None
    return run


if __name__ == '__main__':
    src = subprocess.run(['git', 'show', f'{COMMIT}:outputs/data/pathways/runs.csv'], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    df = pd.read_csv(io.StringIO(src))[list(COLS)]
    rows = df.to_dict(orient='records')
    for r in rows:
        r['run_v3_3'] = v3_3_id(r['run'])
    with open(OUT, 'w') as f:
        json.dump(dict(meta=dict(commit=COMMIT, source='outputs/data/pathways/runs.csv', n_runs=len(df),
                                 n_mapped=sum(r['run_v3_3'] is not None for r in rows)), runs=rows), f, indent=1)
    print(f'{len(df)} runs -> {OUT}')
