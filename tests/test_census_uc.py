"""v1.1.1: census interval rates net of the change in dwellings under construction."""
import numpy as np

import engine
from test_identities import close


def test_uc_correction_is_delta_uc_over_stock_years(B):
    cen = B['census']
    raw = engine.census_interval_rates(cen['total_private'], B['consents_monthly'], B['_completion'], 0.0)
    cor = engine.census_interval_rates(cen['total_private'], B['consents_monthly'], B['_completion'], 0.0,
                                       uc=cen['under_construction'])
    d_uc = np.array([cen.loc[b, 'under_construction'] - cen.loc[a, 'under_construction']
                     for a, b in zip(cor['y0'], cor['y1'])])
    assert close(raw['rate'] - cor['rate'], d_uc / cor['stock_years'])
    assert cor['uc_corrected'].all()
