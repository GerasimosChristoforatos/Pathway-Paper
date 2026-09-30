"""Shared helpers for the ASSESSMENT.md evidence scripts.

Nothing here modifies model code. Every alternative is applied by setting a
module attribute, or by wrapping a module-level function, on a freshly
reloaded copy of Boss. Run each script from any directory, e.g.
    python docs/assessment_evidence/c2_household_size_tail.py
"""
import contextlib
import importlib
import io
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)
sys.path.insert(0, str(REPO))
import matplotlib  # noqa: E402
matplotlib.use('Agg')
import Boss  # noqa: E402


def run(patch=None, **settings):
    """One silent Boss.main() with module settings changed; returns its state."""
    M = importlib.reload(Boss)
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    if patch:
        patch(M)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


def totals(B):
    g = B['results']['50th']['total'][1:].sum() / 1e6
    c = B['carbon_total_typ'].iloc[1:].sum().sum() / 1e6
    step = 100 * (B['results']['50th']['total'][1]
                  / (B['hist_total_gfa'].loc[2025] * B['built_factor']) - 1)
    S = B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th']
    up = B['_upfront'] + B['_soil'] / 1e6
    return dict(GFA=g, carbon=c, upfront=up, step=step, S2050=S[-1],
                consol=B['df_forecast']['Ann_GFA_HouseSplit_Avoided_50th'].iloc[1:].sum() / 1e6)


def fmt(d):
    return (f"GFA {d['GFA']:.2f} Mm2 | carbon {d['carbon']:,.0f} kt | upfront {d['upfront']:,.0f} kt | "
            f"step {d['step']:+.1f}% | S2050 {d['S2050']:.3f} | consolidation {d['consol']:.2f} Mm2")
