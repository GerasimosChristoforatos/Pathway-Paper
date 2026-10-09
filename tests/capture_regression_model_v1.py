"""Capture every reported number of the model into tests/regression_model_v1.json
(MODEL v1.0.0 release, step 1: numerical regression lock taken BEFORE the refurbish).

Run once, on commit ee37ef1 (pathways v3.1), after a full `python run_all.py` and a
`python run_all.py --pathways-only`:

    python tests/capture_regression_model_v1.py

What is captured: every numeric (and boolean) value of every CSV and JSON file the
pipeline writes under outputs/ (baseline, factors, frozen-technology check run, Monte
Carlo, sensitivity, planetary-boundary layer, pathways and theoretical limit T,
metrics.json). Not captured: the figure audit records (outputs/figures/_audit/, year
ranges of plotted data) and the generated Markdown documents, whose numbers are
formatted copies of the captured files.

Stable identifiers. Every value is keyed by
    file (path under outputs/ at capture time) -> row key -> column      (CSV)
    file -> slash-joined path of dict keys and list indices              (JSON)
where the CSV row key is the tuple of the row's identifying columns: every text or
boolean column plus the year / age index columns (an ordinal is appended where those
do not identify a row uniquely; files without identifying columns are keyed by row
number, e.g. the Monte Carlo draws, whose order is the draw order). These are the
names at capture time; tests/test_regression_model_v1.py translates the renamed
outputs back to them through the machine-readable map of docs/RENAMING.md
(naming.py), so labels and file names may change while every number is compared.

Additions (MODEL v1.0.0): values the release reports that no v3.1 output held (the annual
component split, the annual and census-interval demand bands, the annual series of the
projection variants, the population paths of the AESA layer, the TL marker of the solution
space). They are NEW values, not changes: after the release run,

    python tests/capture_regression_model_v1.py --additions

writes them to the 'additions' section of the same file, flagged with the commit and run
they come from; the v3.1 capture ('meta', 'files') is not touched.
"""
import datetime
import glob
import hashlib
import json
import math
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')
TARGET = os.path.join(ROOT, 'tests', 'regression_model_v1.json')
KEY_INT_COLUMNS = ('year', 'Year', 'Age')          # integer columns that identify a row
SKIP_DIRS = (os.path.join('figures', ''), os.path.join('logs', ''))


def number(v):
    """JSON-safe value: floats keep full precision (repr round trip); NaN -> 'NaN'."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    v = float(v)
    return 'NaN' if math.isnan(v) else ('Infinity' if v == math.inf else ('-Infinity' if v == -math.inf else v))


def key_columns(df):
    cols = []
    for i, c in enumerate(df.columns):
        dt = df[c].dtype
        if c in KEY_INT_COLUMNS or (i == 0 and str(c).startswith('Unnamed')):
            cols.append(c)
        elif dt == object or str(dt) in ('bool', 'string', 'str') or pd.api.types.is_string_dtype(dt):
            cols.append(c)
    return cols


def row_key(vals):
    return json.dumps([None if (isinstance(v, float) and math.isnan(v)) else
                       (v.item() if hasattr(v, 'item') else v) for v in vals])


def capture_csv(path):
    df = pd.read_csv(path)
    keys = key_columns(df)
    values = [c for c in df.columns if c not in keys]
    rows = {}
    if keys:
        seen = {}
        vals = df[values].to_dict('records')
        for i, k in enumerate(df[keys].itertuples(index=False, name=None)):   # dtypes kept per column
            k = list(k)
            base = row_key(k)
            n = seen.get(base, 0)
            seen[base] = n + 1
            rk = base if n == 0 else row_key(k + [f'#{n}'])
            rows[rk] = {c: number(v) for c, v in vals[i].items() if pd.api.types.is_number(v) or isinstance(v, bool)}
        dup = sum(1 for v in seen.values() if v > 1)
        return dict(kind='csv', key_columns=keys, value_columns=values, n_rows=len(df), duplicate_keys=dup, rows=rows)
    cols = {c: [number(v) for v in df[c].tolist()] for c in values}
    return dict(kind='csv_by_row_number', value_columns=values, n_rows=len(df), columns=cols)


def flatten(obj, prefix=''):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f'{prefix}/{k}' if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f'{prefix}/{i}' if prefix else str(i)))
    elif isinstance(obj, (bool, int, float)) and obj is not None:
        out[prefix] = number(obj)
    return out


def capture_json(path):
    with open(path) as f:
        obj = json.load(f)
    vals = flatten(obj)
    return dict(kind='json', n_values=len(vals), values=vals)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def files():
    out = []
    for ext in ('csv', 'json'):
        for p in glob.glob(os.path.join(OUT, '**', f'*.{ext}'), recursive=True):
            rel = os.path.relpath(p, OUT)
            if not rel.startswith(SKIP_DIRS):
                out.append(rel)
    return sorted(out)


def main():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    cap = dict(meta=dict(
        purpose='MODEL v1.0.0 numerical regression lock (step 1), captured before the refurbish',
        commit=commit, captured_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        python=sys.version.split()[0], pandas=pd.__version__,
        runs='python run_all.py (full) then python run_all.py --pathways-only',
        tolerance='relative 1e-12 (math.isclose, abs_tol 0); NaN equals NaN; booleans and integers exact',
        not_captured='outputs/figures/_audit (plot year ranges), outputs/logs, generated Markdown documents'),
        files={})
    n = 0
    for rel in files():
        p = os.path.join(OUT, rel)
        entry = capture_csv(p) if rel.endswith('.csv') else capture_json(p)
        entry['sha256_at_capture'] = sha256(p)
        cap['files'][rel] = entry
        if entry['kind'] == 'csv':
            n += sum(len(r) for r in entry['rows'].values())
        elif entry['kind'] == 'csv_by_row_number':
            n += sum(len(c) for c in entry['columns'].values())
        else:
            n += entry['n_values']
    cap['meta']['n_files'] = len(cap['files'])
    cap['meta']['n_values'] = n
    with open(TARGET, 'w') as f:
        json.dump(cap, f, indent=0, sort_keys=False)
    print(f'regression capture: {n:,} values from {len(cap["files"])} files -> {os.path.relpath(TARGET, ROOT)} '
          f'({os.path.getsize(TARGET) / 1e6:.1f} MB)')


# the release locations (outputs/...) of the additions: a whole file (None) or JSON key prefixes
ADDITIONS = {'data/baseline/annual.csv': None, 'data/baseline/bands_annual.csv': None,
             'data/baseline/bands_history.csv': None, 'data/baseline/variants_annual.csv': None,
             'data/frozen_technology/baseline/variants_annual.csv': None,
             'data/aesa/results.json': ('population_paths',),
             'data/frozen_technology/aesa/results.json': ('population_paths',),
             'data/pathways/theoretical_limit.json': ('solution_space_marker',)}


def additions():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with open(TARGET) as f:
        cap = json.load(f)
    add = dict(meta=dict(
        purpose='MODEL v1.0.0: values that no v3.1 output held (additions, not changes)',
        commit=commit, captured_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        runs='python run_all.py (full) then python run_all.py --pathways-only, release layout (layout.py)',
        tolerance=cap['meta']['tolerance']), files={})
    n = 0
    for rel, prefixes in ADDITIONS.items():
        p = os.path.join(OUT, rel)
        entry = capture_csv(p) if rel.endswith('.csv') else capture_json(p)
        if prefixes:
            entry['values'] = {k: v for k, v in entry['values'].items() if k.split('/')[0] in prefixes}
            entry['n_values'] = len(entry['values'])
        add['files'][rel] = entry
        n += (sum(len(r) for r in entry['rows'].values()) if entry['kind'] == 'csv' else
              sum(len(c) for c in entry['columns'].values()) if entry['kind'] == 'csv_by_row_number' else
              entry['n_values'])
    add['meta']['n_files'], add['meta']['n_values'] = len(add['files']), n
    cap['additions'] = add
    with open(TARGET, 'w') as f:
        json.dump(cap, f, indent=0, sort_keys=False)
    print(f'regression additions: {n:,} values from {len(add["files"])} files -> {os.path.relpath(TARGET, ROOT)}')


if __name__ == '__main__':
    if '--additions' in sys.argv:
        additions()
    else:
        main()
