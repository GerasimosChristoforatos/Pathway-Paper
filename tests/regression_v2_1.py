"""The pathway domain of MODEL v2.1.0 and its regression lock (tests/regression_model_v2_1.json).

MODEL v2.1.0 replaces the lever set, the pathways and the theoretical limit, so every number derived from
them changes by design. Those numbers form the pathway domain:
  * every data file under data/pathways/ (runs, bands, annual series, Shapley tables, levers.json,
    theoretical_limit.json, the pathway Monte Carlo and its insight files, the sequential waterfall);
  * data/sensitivity/p5_carbon.csv (the P5 rows of the grouped sensitivity tables);
  * the P5 and TL rows of data/sensitivity/replacement_variants.csv (its Reference rows are not in the domain).
Every other number of outputs/data/ (the Reference projection, the baseline, the AESA layer and the baseline
Monte Carlo) stays locked by tests/test_regression_model_v1.py and tests/test_regression_model_v2.py to 1e-12;
those checks skip only keys in the domain, which this lock holds instead (tests/test_regression_model_v2_1.py).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_FILE = os.path.join(ROOT, 'tests', 'regression_model_v2_1.json')
DOMAIN_PREFIXES = ('data/pathways/',)
DOMAIN_FILES = ('data/sensitivity/p5_carbon.csv',)
ROWS_NOT_REFERENCE = ('data/sensitivity/replacement_variants.csv',)


def in_domain(key):
    """True for a release key (file, row key | None, column) or (file, path) of the pathway domain."""
    f = key[0]
    if f.startswith(DOMAIN_PREFIXES) or f in DOMAIN_FILES:
        return True
    if f in ROWS_NOT_REFERENCE:
        return len(key) == 3 and key[1] is not None and 'Reference' not in json.loads(key[1])
    return False


def domain_values():
    """{key: value} of every number of the pathway domain in outputs/data/."""
    sys.path.insert(0, os.path.join(ROOT, 'tests'))
    import regression_v2 as R
    out = {}
    for rel in R.data_files():
        out.update({k: v for k, v in R.values(rel).items() if in_domain(k)})
    return out


def load_lock():
    if not os.path.exists(LOCK_FILE):
        return {}, {}
    with open(LOCK_FILE) as f:
        a = json.load(f)
    return {tuple(json.loads(k)): v for k, v in a['values'].items()}, a['meta']
