"""Coverage of the regression lock (MODEL v2.0.0): every number in outputs/data/ must be locked.

A number of a data file is locked when one of these checks finds it at its release location and
compares it to 1e-12 relative:
  * tests/regression_model_v1.json, 'files' (the ee37ef1 capture, mapped by naming.LEGACY) and
    'additions' (model-v1.0.0), with the MODEL v1.1.0 changes of tests/regression_model_v1_1.json;
  * tests/regression_model_v2_additions.json: every value no earlier version held (the v1.1.0
    data that no file captured, and the values MODEL v2.0.0 adds).
The keys are the release keys the checks record in test_regression_model_v1.COVER:
  CSV with identifying columns   (file, row key, column), row key as the capture's row_key of the
                                 identifying cells (text / boolean columns and year, Year, Age)
  CSV without (by row number)    (file, None, column): the whole column
  JSON                           (file, slash-joined path)
"""
import json
import math
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, ROOT)
import capture_regression_model_v1 as C  # noqa: E402
import test_regression_model_v1 as T  # noqa: E402

OUT = os.path.join(ROOT, 'outputs')
DATA = os.path.join(OUT, 'data')
ADDITIONS_FILE = os.path.join(ROOT, 'tests', 'regression_model_v2_additions.json')


def data_files():
    out = []
    for d, _, fs in os.walk(DATA):
        out += [os.path.relpath(os.path.join(d, f), OUT).replace(os.sep, '/') for f in fs
                if f.endswith(('.csv', '.json'))]
    return sorted(out)


def values(rel):
    """{key: value} of every number (and boolean) of a data file, keys as in the module docstring;
    a column of a CSV without identifying columns is one key whose value is the list."""
    p = os.path.join(OUT, rel)
    if rel.endswith('.json'):
        with open(p) as f:
            return {(rel, k): v for k, v in C.flatten(json.load(f)).items()}
    e = C.capture_csv(p)
    if e['kind'] == 'csv_by_row_number':
        return {(rel, None, c): v for c, v in e['columns'].items()}
    return {(rel, rk, c): v for rk, cols in e['rows'].items() for c, v in cols.items()}


def covered_by_v1():
    """Run every check of tests/test_regression_model_v1.py and return the release keys they cover
    (the checks assert nothing here: test_regression_model_v1.py does)."""
    T.COVER.clear()
    for f, entry in T.CAP['files'].items():
        if T.LEGACY.removed(f) or not os.path.exists(os.path.join(OUT, T.LEGACY.file(f))):
            continue
        (T._check_json if entry['kind'] == 'json' else T._check_csv)(f, entry)
    saved = T.LEGACY
    T.LEGACY = T._Release()
    try:
        for f, entry in T.CAP.get('additions', {}).get('files', {}).items():
            if os.path.exists(os.path.join(OUT, f)):
                (T._check_json if entry['kind'] == 'json' else T._check_csv)(f, entry)
    finally:
        T.LEGACY = saved
    return set(T.COVER)


def keystr(key):
    """A key as a JSON string (the regression file's dictionary key)."""
    return json.dumps(list(key))


def unkey(s):
    k = json.loads(s)
    return tuple(k)


def load_additions():
    if not os.path.exists(ADDITIONS_FILE):
        return {}, {}
    with open(ADDITIONS_FILE) as f:
        a = json.load(f)
    return {unkey(k): v for k, v in a['values'].items()}, a['meta']


def same(expected, actual):
    if isinstance(expected, list) or isinstance(actual, list):
        return (isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual)
                and all(same(e, a) for e, a in zip(expected, actual)))
    if isinstance(expected, str) or isinstance(actual, str):          # 'NaN', 'Infinity'
        return expected == actual
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    if isinstance(expected, int) and isinstance(actual, int):
        return expected == actual
    return math.isclose(float(expected), float(actual), rel_tol=1e-12, abs_tol=0.0)


def uncovered(cover=None):
    """{key: value} of every number of outputs/data/ that no v1 check covers."""
    cover = covered_by_v1() if cover is None else cover
    out = {}
    for rel in data_files():
        out.update({k: v for k, v in values(rel).items() if k not in cover})
    return out


if __name__ == '__main__':
    u = uncovered()
    by = pd.Series([k[0] for k in u]).value_counts()
    print(f'{len(u)} values not covered by the v1 lock:')
    print(by.to_string())
