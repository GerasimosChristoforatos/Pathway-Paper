"""MODEL v4.6.0: committed after-2050 emissions per Reference Monte Carlo draw (pathways_mc.py): every draw satisfies
the identities of pathways.committed (total = B2/B4 + C1-C4 at each bound; the lower bound below the upper), and the
deterministic central value lies inside the 5th-95th percentile range of the draws."""
import json

import numpy as np
import pandas as pd


def test_committed_per_draw_identities_and_central():
    import layout
    d = pd.read_csv(layout.data('pathways/montecarlo_draws.csv'))
    s = pd.read_csv(layout.data('pathways/montecarlo_summary.csv'))
    with open(layout.data('baseline/projection.json')) as f:
        com = json.load(f)['committed']
    lo, up = d['REF_committed_lower_kt'], d['REF_committed_upper_kt']
    np.testing.assert_allclose(lo, d['REF_committed_b2b4_lower_kt'] + d['REF_committed_c1c4_kt'], rtol=1e-12)
    np.testing.assert_allclose(up, d['REF_committed_b2b4_upper_kt'] + d['REF_committed_c1c4_kt'], rtol=1e-12)
    assert (lo <= up).all() and (lo > 0).all()
    q = s[s['run'] == 'REF'].set_index('quantity')
    for col, key in (('committed_lower_kt', 'lower_kt'), ('committed_upper_kt', 'upper_kt'),
                     ('committed_c1c4_kt', 'C_kt')):
        r = q.loc[col]
        assert r['p5'] <= r['p25'] <= r['p50'] <= r['p75'] <= r['p95']
        assert r['p5'] < com[key] < r['p95']
        assert np.isclose(r['p50'], np.percentile(d[f'REF_{col}'], 50))
