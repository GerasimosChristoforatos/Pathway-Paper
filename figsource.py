"""Figure source data (MODEL v3.0.0 compute / draw separation): the model scripts write, for every diagnostic that
needs more than the published data tables, the exact arrays the figure draws, as JSON under
outputs/data/figure_source/<figure id>.json; the figures/ package reads them (read()) and never recomputes the model.

Encoding (to_jsonable / from_jsonable, lossless for float64 via repr round trip in json): numpy arrays -> lists;
pandas Series -> {"__series__": {"index": [...], "values": [...], "name": ...}}; pandas DataFrame ->
{"__frame__": {"index": [...], "columns": [...], "data": {column: [...]}}}; numpy scalars -> Python scalars;
non-finite floats -> null.
"""
import json
import math

import numpy as np
import pandas as pd

import layout

DIR = 'figure_source'


def _scalar(v):
    if isinstance(v, (np.floating,)):
        v = float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def to_jsonable(o):
    if isinstance(o, pd.DataFrame):
        return {'__frame__': dict(index=[to_jsonable(i) for i in o.index], columns=[str(c) for c in o.columns],
                                  data={str(c): [to_jsonable(v) for v in o[c].tolist()] for c in o.columns})}
    if isinstance(o, pd.Series):
        return {'__series__': dict(index=[to_jsonable(i) for i in o.index], values=[to_jsonable(v) for v in o.tolist()],
                                   name=None if o.name is None else str(o.name))}
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [to_jsonable(v) for v in o.tolist()]
    return _scalar(o)


def _num(v):
    return np.nan if v is None else v


def from_jsonable(o):
    if isinstance(o, dict):
        if '__frame__' in o:
            f = o['__frame__']
            df = pd.DataFrame({c: [(_num(v) if not isinstance(v, str) else v) for v in f['data'][c]] for c in f['columns']},
                              index=f['index'])
            return df
        if '__series__' in o:
            s = o['__series__']
            return pd.Series([_num(v) if not isinstance(v, str) else v for v in s['values']], index=s['index'], name=s['name'])
        return {k: from_jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        if o and all(isinstance(v, (int, float)) or v is None for v in o):
            return np.array([_num(v) for v in o], float)
        return [from_jsonable(v) for v in o]
    return o


def path(fid):
    return layout.data(f'{DIR}/{fid}.json', frozen=False)


def write(fid, **data):
    """Write the source data of figure `fid` (keyword arrays / series / frames / scalars / dicts)."""
    with open(layout.writing(path(fid)), 'w') as f:
        json.dump(to_jsonable(data), f, indent=0, sort_keys=True)


def read(fid):
    """The source data of figure `fid`: a dict of numpy arrays, pandas objects, scalars and dicts."""
    with open(path(fid)) as f:
        return from_jsonable(json.load(f))
