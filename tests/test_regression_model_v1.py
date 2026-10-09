"""Numerical regression lock of MODEL v1.0.0. It replaces the byte lock of the baseline
(tests/test_baseline_lock.py and tests/baseline_manifest.json, removed in this release): the
refurbish renames files, columns and labels, so bytes change while numbers may not. Byte
reproducibility of the release outputs is re-established by tests/output_manifest_model_v1.json.

tests/regression_model_v1.json holds every number the pipeline reported at commit
ee37ef1 (pathways v3.1), captured by tests/capture_regression_model_v1.py before any
refurbish. Each captured identifier (file, row key, column; or file, JSON path) is
mapped FORWARD to its current location by the machine-readable map of the release,
naming.LEGACY (documented in docs/RENAMING.md), and every captured value must be
reproduced there to 1e-12 relative (NaN equals NaN; booleans and integers exactly).

A captured value may be absent only where naming.LEGACY.removed() says so (by-typology
reporting and exact duplicate files removed in the refurbish; each listed in the
CHANGELOG).
"""
import json
import math
import os

import pandas as pd
import pytest

from conftest import ROOT

CAPTURE = os.path.join(ROOT, 'tests', 'regression_model_v1.json')
OUT = os.path.join(ROOT, 'outputs')
REL_TOL = 1e-12

with open(CAPTURE) as _f:
    CAP = json.load(_f)


class _Identity:
    """The map before the refurbish: every identifier where it was captured."""
    @staticmethod
    def file(old):
        return old

    @staticmethod
    def column(old_file, col):
        return col

    @staticmethod
    def cell(old_file, col, value, row):
        return value

    @staticmethod
    def json_path(old_file, path):
        return path

    @staticmethod
    def removed(old_file, row=None, col=None, path=None):
        return False


try:
    import naming
    LEGACY = naming.LEGACY
except (ImportError, AttributeError):
    LEGACY = _Identity()


def _same(expected, actual):
    if isinstance(expected, str):                       # 'NaN', 'Infinity', '-Infinity'
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        return (math.isnan(actual) if expected == 'NaN' else
                actual == (math.inf if expected == 'Infinity' else -math.inf))
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    if actual is None:
        return False
    if isinstance(expected, int) and isinstance(actual, int):
        return expected == actual
    return math.isclose(float(expected), float(actual), rel_tol=REL_TOL, abs_tol=0.0)


def _py(v):
    return v.item() if hasattr(v, 'item') else v


def _row_key(vals):
    return json.dumps([None if (isinstance(v, float) and math.isnan(v)) else _py(v) for v in vals])


def _check_csv(old_file, entry):
    df = pd.read_csv(os.path.join(OUT, LEGACY.file(old_file)))
    bad, missing = [], []
    col = lambda c: LEGACY.column(old_file, c)
    if entry['kind'] == 'csv_by_row_number':
        for c, vals in entry['columns'].items():
            if col(c) not in df.columns:
                if not LEGACY.removed(old_file, col=c):
                    missing.append(c)
                continue
            got = [_py(v) for v in df[col(c)].tolist()]
            if len(got) != len(vals):
                bad.append((c, f'{len(got)} rows, captured {len(vals)}'))
                continue
            bad += [(c, i, e, a) for i, (e, a) in enumerate(zip(vals, got)) if not _same(e, a)][:5]
        return bad, missing
    keys = entry['key_columns']
    for k in keys:
        if col(k) not in df.columns:
            raise AssertionError(f'{old_file}: identifying column {k!r} ({col(k)!r}) missing in {LEGACY.file(old_file)}')
    seen, index = {}, {}
    for i, r in enumerate(df[[col(k) for k in keys]].itertuples(index=False, name=None)):
        base = _row_key(list(r))
        n = seen.get(base, 0)
        seen[base] = n + 1
        index[base if n == 0 else _row_key(list(r) + [f'#{n}'])] = i
    records = df.to_dict('records')
    for rk, vals in entry['rows'].items():
        old_cells = json.loads(rk)
        ctx = dict(zip(keys, old_cells))                   # the row's captured identifying cells
        cells = [LEGACY.cell(old_file, k, v, ctx) for k, v in zip(keys, old_cells[:len(keys)])] + old_cells[len(keys):]
        new_rk = _row_key(cells)
        if new_rk not in index:
            if not LEGACY.removed(old_file, row=old_cells):
                missing.append(rk)
            continue
        row = records[index[new_rk]]
        for c, e in vals.items():
            if col(c) not in row:
                if not LEGACY.removed(old_file, row=old_cells, col=c):
                    missing.append((rk, c))
                continue
            if not _same(e, _py(row[col(c)])):
                bad.append((rk, c, e, row[col(c)]))
    return bad, missing


def _flatten(obj, prefix=''):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f'{prefix}/{k}' if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f'{prefix}/{i}' if prefix else str(i)))
    elif isinstance(obj, (bool, int, float)) and obj is not None:
        out[prefix] = obj
    return out


def _check_json(old_file, entry):
    with open(os.path.join(OUT, LEGACY.file(old_file))) as f:
        got = _flatten(json.load(f))
    bad, missing = [], []
    for p, e in entry['values'].items():
        q = LEGACY.json_path(old_file, p)
        if q not in got:
            if not LEGACY.removed(old_file, path=p):
                missing.append(p)
            continue
        if not _same(e, got[q]):
            bad.append((p, e, got[q]))
    return bad, missing


@pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: Monte Carlo outputs differ by design')
@pytest.mark.parametrize('old_file', sorted(CAP['files']))
def test_every_captured_number_is_reproduced(old_file):
    entry = CAP['files'][old_file]
    if LEGACY.removed(old_file):
        pytest.skip(f'{old_file}: removed by design (naming.LEGACY)')
    new = os.path.join(OUT, LEGACY.file(old_file))
    assert os.path.exists(new), f'{old_file}: the current file {LEGACY.file(old_file)} does not exist'
    bad, missing = (_check_json if entry['kind'] == 'json' else _check_csv)(old_file, entry)
    assert not missing, f'{old_file}: {len(missing)} captured values absent, e.g. {missing[:5]}'
    assert not bad, f'{old_file}: {len(bad)} values differ beyond 1e-12 relative, e.g. {bad[:5]}'


def test_capture_meta():
    m = CAP['meta']
    assert m['commit'].startswith('ee37ef1') and m['n_files'] == len(CAP['files'])
