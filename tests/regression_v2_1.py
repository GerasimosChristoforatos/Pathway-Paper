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

Compact form (MODEL v2.1.1). The five large files of the domain (HASHED_FILES: the per-draw pathway Monte Carlo,
the annual series, the LOWESS fits and the two Shapley subset tables; 155,000 of the 163,000 values) are not stored
value by value. For each of them the lock holds, per row group (the value of the `run` column where there is one)
and column: the SHA-256 of the column's values written at 13 significant digits (canonical()), and the count,
sum, minimum and maximum (compared at 1e-12 relative). The per-draw file also holds one SHA-256 per draw and
column group (inputs, REF, P5, TL), so a change is located to the draw. At 13 significant digits the decimal
spacing is at most 1e-12 relative, so any value that moves by 1e-12 relative or more changes its text and so the
hash (tested): the detection power is at least that of the value-by-value lock at 1e-12 (stricter below it, which
the deterministic, byte-reproduced run allows), and the summary statistics give the size of a change. Every other file of the domain is held value by value.

MODEL v2.1.1 changes the theoretical limit only (TL adopted by 2030 with constant-share re-occupation); tests/regression_model_v2_1_1.json lists
every key that changed (old and new value or hash), and tests/test_regression_model_v2_1.py requires every one of
them to be a TL key (is_tl_key) and every other key to be unchanged.
"""
import hashlib
import math
import re
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


CHANGES_FILE = os.path.join(ROOT, 'tests', 'regression_model_v2_1_1.json')
HASHED_FILES = ('data/pathways/montecarlo_draws.csv', 'data/pathways/annual.csv', 'data/pathways/montecarlo_fits.csv',
                'data/pathways/shapley_subsets.csv', 'data/pathways/shapley_theoretical_limit_subsets.csv')
PER_DRAW = 'data/pathways/montecarlo_draws.csv'
STAT_TOL = 1e-12
# files whose every number belongs to the theoretical limit
TL_FILES = ('data/pathways/theoretical_limit.json', 'data/pathways/shapley_theoretical_limit.csv',
            'data/pathways/shapley_theoretical_limit_subsets.csv', 'data/pathways/montecarlo_conditional_tl.csv',
            'data/pathways/montecarlo_conditional_tl.json')
_TL = re.compile(r'(^|[^A-Za-z0-9])TL|from2027|reoccup')


def canonical(v):
    """A cell as text at 13 significant digits (booleans and text as they are; NaN as 'nan'; -0 as 0)."""
    if isinstance(v, (bool,)) or type(v).__name__ == 'bool_':
        return str(bool(v))
    if isinstance(v, str):
        return v
    x = float(v)
    if math.isnan(x):
        return 'nan'
    t = format(x, '.13g')
    return '0' if t == '-0' else t


def _sha(strings):
    return hashlib.sha256('\n'.join(strings).encode('utf-8')).hexdigest()


def draw_group(col):
    """Column group of the per-draw file: the run a column belongs to (REF, P5, TL) or the draw's inputs."""
    head = col.split('_')[0]
    if head in ('REF', 'P5'):
        return head
    return 'TL' if col.startswith('TL') else 'inputs'


def hashed_entry(rel):
    """The compact lock entry of a large domain file (see the module docstring)."""
    import pandas as pd
    df = pd.read_csv(os.path.join(ROOT, 'outputs', rel))
    groups = {None: df} if 'run' not in df.columns else {str(g): d for g, d in df.groupby('run', sort=False)}
    out = {'n_rows': int(len(df)), 'columns': list(df.columns), 'groups': {}}
    for g, d in groups.items():
        cols = {}
        for c in d.columns:
            vals = d[c].tolist()
            e = {'sha256': _sha(canonical(v) for v in vals), 'n': len(vals)}
            num = pd.to_numeric(d[c], errors='coerce') if d[c].dtype != bool else None
            if num is not None and num.notna().any() and d[c].dtype != object:
                x = num.dropna()
                e.update(sum=float(x.sum()), min=float(x.min()), max=float(x.max()))
            cols[c] = e
        out['groups']['all' if g is None else g] = cols
    if rel == PER_DRAW:
        cg = {}
        for c in df.columns:
            if c == 'draw':
                continue
            cg.setdefault(draw_group(c), []).append(c)
        out['rows'] = {g: [_sha([canonical(v) for v in r]) for r in df[cs].itertuples(index=False, name=None)]
                       for g, cs in cg.items()}
        out['row_groups'] = cg
    return out


def hashed_entries():
    return {rel: hashed_entry(rel) for rel in HASHED_FILES}


def flat_hashed(entries):
    """{key: value} of the compact entries: (file, '#group', group, column, field) and (file, '#rows', group, i)."""
    out = {}
    for rel, e in entries.items():
        out[(rel, '#n_rows')] = e['n_rows']
        for g, cols in e['groups'].items():
            for c, st in cols.items():
                for k, v in st.items():
                    out[(rel, '#group', g, c, k)] = v
        for g, hs in e.get('rows', {}).items():
            for i, h in enumerate(hs):
                out[(rel, '#rows', g, i)] = h
    return out


def compact_values():
    """{key: value}: every value of the domain outside the hashed files, and the flattened compact entries."""
    vals = {k: v for k, v in domain_values().items() if k[0] not in HASHED_FILES}
    vals.update(flat_hashed(hashed_entries()))
    return vals


def same_compact(key, a, b):
    """Equality of two lock values: hashes and counts exactly, summary statistics at 1e-12 relative, every other
    value as tests/regression_v2.same."""
    sys.path.insert(0, os.path.join(ROOT, 'tests'))
    import regression_v2 as R
    if len(key) == 5 and key[1] == '#group' and key[4] in ('sum', 'min', 'max'):
        return math.isclose(float(a), float(b), rel_tol=STAT_TOL, abs_tol=1e-9)
    if len(key) >= 2 and isinstance(key[1], str) and key[1].startswith('#'):
        return a == b
    return R.same(a, b)


def is_tl_key(key):
    """True for a key of the theoretical limit (a TL run, item, subset, column or file, or the full-strength-from-2027
    base of the TL attribution)."""
    if key[0] in TL_FILES:
        return True
    return any(_TL.search(str(x)) for x in key[1:] if x is not None)


def load_lock():
    """{key: value} of tests/regression_model_v2_1.json with MODEL v2.1.1's changes applied, and its meta."""
    if not os.path.exists(LOCK_FILE):
        return {}, {}
    with open(LOCK_FILE) as f:
        a = json.load(f)
    lock = {tuple(json.loads(k)): v for k, v in a['values'].items()}
    lock.update(flat_hashed(a.get('hashed', {})))
    ch = load_changes()
    for k, d in ch.get('changed', {}).items():
        lock[k] = d['new']
    for k, v in ch.get('added', {}).items():
        lock[k] = v
    for k in ch.get('removed', {}):
        lock.pop(k, None)
    return lock, a['meta']


def load_base_lock():
    """The lock as captured (without MODEL v2.1.1's changes), flattened."""
    with open(LOCK_FILE) as f:
        a = json.load(f)
    lock = {tuple(json.loads(k)): v for k, v in a['values'].items()}
    lock.update(flat_hashed(a.get('hashed', {})))
    return lock


def load_changes():
    if not os.path.exists(CHANGES_FILE):
        return {}
    with open(CHANGES_FILE) as f:
        a = json.load(f)
    un = lambda d: {tuple(json.loads(k)): v for k, v in d.items()}
    return dict(meta=a['meta'], changed=un(a['changed']), added=un(a['added']), removed=un(a['removed']))
