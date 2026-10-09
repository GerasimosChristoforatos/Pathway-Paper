"""Material decarbonisation paths: Horup et al. (2025) SI Table S4, relative to
2025, linear between the S4 years (the item-level mapping is tested in
test_decarb_item.py)."""
import pandas as pd
import pytest

import Building_factors as BF

S4 = pd.read_csv(BF.FILE_HORUP)


def test_s4_paths_match_the_table():
    """Relative path = C(t)/C(2025) at Horup's years; linear in between."""
    p = BF.decarb_paths()
    for m, g in S4.groupby('material'):
        g = g.set_index('year')
        for y in BF.DECARB_KNOTS:
            assert p.loc[y, m] == pytest.approx(g.loc[y, 'premise_rel_ecoinvent'] / g.loc[2025, 'premise_rel_ecoinvent'],
                                                rel=1e-12)
        assert p.loc[2027, m] == pytest.approx(0.6 * p.loc[2025, m] + 0.4 * p.loc[2030, m], rel=1e-12)
        assert p.loc[2045, m] == pytest.approx(0.5 * p.loc[2040, m] + 0.5 * p.loc[2050, m], rel=1e-12)
