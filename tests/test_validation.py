"""The 2026 out-of-sample check, on SYNTHETIC monthly consents (test only;
nothing here enters data/ or the model)."""
import numpy as np
import pandas as pd

import validation


def test_check_2026_pending_and_seasonal(B):
    idx = pd.date_range('2010-01-01', '2025-12-01', freq='MS')
    season = np.tile(np.arange(1, 13), len(idx) // 12)            # month m has weight m
    s = pd.Series(season * 100.0, index=idx)
    chk = validation.check_2026(B, s)
    assert chk['status'] == 'pending'
    # add Jan-Mar 2026 exactly at the model's annual rate x the seasonal share
    annual = chk['model_consent_equivalent_2026']
    share = np.arange(1, 13) / 78.0
    extra = pd.Series(annual * share[:3], index=pd.date_range('2026-01-01', periods=3, freq='MS'))
    chk = validation.check_2026(B, pd.concat([s, extra]))
    assert chk['status'] == 'observed' and chk['months'] == [1, 2, 3]
    assert abs(chk['seasonal_share'] - share[:3].sum()) < 1e-12
    assert abs(chk['ratio_observed_to_model'] - 1.0) < 1e-12
