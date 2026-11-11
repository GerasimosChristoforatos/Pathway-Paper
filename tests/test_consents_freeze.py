"""MODEL v4.6.0 data freeze: data/derived/consents_monthly.csv is rebuilt exactly from the unmodified Infoshare export
in data/raw (data/build_consents.py read_infoshare), the export matches its MANIFEST checksum, and the 1965-04..2026-07
months carry no Stats NZ revision against the earlier (July 2026 release) file."""
import csv
import hashlib
import importlib.util
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw', 'BLD468601_20261111_075751_49.csv')


def _bc():
    spec = importlib.util.spec_from_file_location('build_consents', os.path.join(ROOT, 'data', 'build_consents.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_raw_export_matches_manifest():
    rows = {r['file']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'raw', 'MANIFEST.csv')))}
    with open(RAW, 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == rows[os.path.basename(RAW)]['sha256']


def test_derived_consents_rebuilt_exactly_from_raw():
    bc = _bc()
    wide, _ = bc.read_infoshare(RAW)
    out = bc.to_model_layout(wide)
    got = pd.read_csv(os.path.join(ROOT, 'data', 'derived', 'consents_monthly.csv'), index_col='Date', parse_dates=True)
    assert list(got.columns) == list(out.columns)
    assert got.index.min() == pd.Timestamp('1965-04-01') and got.index.max() == pd.Timestamp('2026-09-01')
    pd.testing.assert_frame_equal(got, out, check_freq=False, check_names=False)


def test_no_revisions_against_the_july_2026_release():
    rev = pd.read_csv(os.path.join(ROOT, 'data', 'derived', 'consents_revisions.csv'))
    assert list(rev.columns) == ['month', 'column', 'old', 'new', 'rel'] and len(rev) == 0
