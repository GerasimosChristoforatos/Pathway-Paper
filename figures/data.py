"""Readers of the data files the figures draw (outputs/data/, or outputs/_light/data/ in the light profile)."""
import json

import pandas as pd

import figsource
import layout


def csv(rel, **kw):
    """outputs/data/<rel> as a DataFrame."""
    return pd.read_csv(layout.data(rel, frozen=False), **kw)


def js(rel):
    """outputs/data/<rel> (JSON)."""
    with open(layout.data(rel, frozen=False)) as f:
        return json.load(f)


def src(fid):
    """The figure source data of `fid` (figsource.read)."""
    return figsource.read(fid)
