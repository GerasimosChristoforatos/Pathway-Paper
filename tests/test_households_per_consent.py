"""Stats NZ's Dwelling and Household Estimates (DHE) derive households between census
bases from weighted, lagged building consents. Checked against the raw inputs (no model run): in 2019-2025 the growth of
the DHE households as published (31 December) over the previous calendar year's consents, all dwellings (retirement
villages included; data/derived/consents_monthly.csv column 'Dwellings'), is a near-constant 0.888, as documented in
projection.py (HOUSEHOLD ESTIMATES). The ratio moves away from it before 2019, where households are census-benchmarked."""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import projection as PJ  # noqa: E402


def _ratio():
    c = PJ.load_consents().set_index('Date')[PJ.COL_DWELLINGS_TOTAL].astype(float)
    cons = c.groupby(c.index.year).sum()                           # calendar-year consents, all dwellings
    h = PJ.load_historical_households(PJ.FILE_HOUSEHOLDS_HIST).set_index('Date')['Households']
    dec = h[h.index.month == 12]
    dec.index = dec.index.year                                     # households at 31 December, as published
    return dec.diff() / cons.shift(1)


def test_dhe_households_per_previous_year_consent_2019_2025():
    r = _ratio().loc[2019:2025]
    assert len(r) == 7 and r.notna().all()
    assert np.all((r > 0.884) & (r < 0.890)), r.round(4).to_dict()
    assert abs(float(r.mean()) - 0.888) < 0.002, float(r.mean())


def test_ratio_not_constant_while_census_benchmarked():
    r = _ratio().loc[2014:2018]                                    # the 2013-2018 base: benchmarked to the census
    assert float(r.max() - r.min()) > 0.05
