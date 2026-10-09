"""The release map naming.RELEASE (docs/RENAMING.md) is complete and one-to-one: every
identifier captured at ee37ef1 (tests/regression_model_v1.json) has a release location,
and no two captured identifiers of one file land on the same release identifier unless
they carry the same value (exact duplicate files merged, e.g. montecarlo_summary.csv and
montecarlo_summary_S3-10.csv)."""
import json
import os
from collections import defaultdict

from conftest import ROOT

import naming as N

with open(os.path.join(ROOT, 'tests', 'regression_model_v1.json')) as _f:
    CAP = json.load(_f)
R = N.RELEASE


def test_every_file_has_a_release_location_and_merged_files_are_identical():
    by_new = defaultdict(list)
    for f, e in CAP['files'].items():
        by_new[R.file(f)].append(e['sha256_at_capture'])
    merged = {k: v for k, v in by_new.items() if len(v) > 1}
    assert all(len(set(v)) == 1 for v in merged.values()), merged
    assert len(merged) == 6            # the plain-named Monte Carlo copies of the Reference (and frozen)


def test_csv_identifiers_one_to_one():
    for f, e in CAP['files'].items():
        if e['kind'] == 'json':
            continue
        keys = e.get('key_columns', [])
        cols = [R.column(f, c) for c in keys + e['value_columns']]
        assert len(set(cols)) == len(cols), (f, cols)
        if e['kind'] != 'csv':
            continue
        seen = {}
        for rk in e['rows']:
            cells = json.loads(rk)
            ctx = dict(zip(keys, cells))
            new = tuple(R.cell(f, k, v, ctx) for k, v in zip(keys, cells)) + tuple(cells[len(keys):])
            assert new not in seen, (f, rk, seen.get(new))
            seen[new] = rk


def test_json_paths_one_to_one():
    for f, e in CAP['files'].items():
        if e['kind'] != 'json':
            continue
        seen = {}
        for p in e['values']:
            if R.removed(f, path=p):
                continue
            q = R.json_path(f, p)
            assert q not in seen, (f, p, seen.get(q))
            seen[q] = p


def test_removals_are_by_typology_only():
    """Everything the release removes is by-typology reporting (CHANGELOG)."""
    typ = ('Detached', 'Townhouses', 'Apartments', 'typology', 'townhouse', 'attached', 'shares_2050')
    for f, e in CAP['files'].items():
        if e['kind'] == 'json':
            gone = [p for p in e['values'] if R.removed(f, path=p)]
            assert all(any(t in p for t in typ) for p in gone), (f, gone[:5])
        else:
            cols = e['value_columns']
            gone = [c for c in cols if R.removed(f, col=c)]
            assert all(any(t in c for t in typ) for c in gone), (f, gone)
