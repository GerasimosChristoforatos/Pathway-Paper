"""Capture the MODEL v3.0.0 run totals for the v3.0 equality test (tests/test_model_v3_2.py):
    python tests/capture_v3_0_totals.py
Source: outputs/data/pathways/runs.csv at the v3.0.0 full-profile commit (d084e09; deterministic, identical in both
profiles), read with git show so that the fixture is reproducible from the repository history."""
import io
import json
import os
import subprocess

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMIT = 'd084e09'
OUT = os.path.join(ROOT, 'tests', 'fixtures', 'v3_0_totals.json')
COLS = ('run', 'scenario', 'setting', 'levers', 'adoption', 'floor_area_Mm2', 'carbon_kt', 'B_AR_kt', 'B_AtP_kt',
        'LoE_AR', 'LoE_AtP')

if __name__ == '__main__':
    src = subprocess.run(['git', 'show', f'{COMMIT}:outputs/data/pathways/runs.csv'], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    df = pd.read_csv(io.StringIO(src))[list(COLS)]
    with open(OUT, 'w') as f:
        json.dump(dict(meta=dict(commit=COMMIT, source='outputs/data/pathways/runs.csv', n_runs=len(df)),
                       runs=df.to_dict(orient='records')), f, indent=1)
    print(f'{len(df)} runs -> {OUT}')
