"""Writes tests/fixtures/mcstats_reference.json: reference values of LOWESS and logistic regression computed
with statsmodels (not a dependency of the model) on fixed synthetic data, for tests/test_mcstats.py. Run once
in an environment with statsmodels:  python tests/make_mcstats_reference.py"""
import json
import os

import numpy as np
import statsmodels
import statsmodels.api as sm
from statsmodels.nonparametric.smoothers_lowess import lowess

HERE = os.path.dirname(os.path.abspath(__file__))

from mcstats_data import data  # noqa: E402


if __name__ == '__main__':
    x, y, X, yy = data()
    xv = np.linspace(x.min(), x.max(), 21)
    f = sm.Logit(yy, sm.add_constant(X)).fit(disp=0, tol=1e-12)
    out = dict(statsmodels=statsmodels.__version__, seed=20261012,
               lowess_fit=lowess(y, x, frac=2 / 3, it=3, delta=0.0, return_sorted=False).tolist(),
               lowess_xvals=xv.tolist(), lowess_curve=lowess(y, x, frac=2 / 3, it=3, delta=0.0, xvals=xv).tolist(),
               logit_beta=f.params.tolist(), logit_se=f.bse.tolist(), logit_mcfadden=float(f.prsquared))
    os.makedirs(os.path.join(HERE, 'fixtures'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'fixtures', 'mcstats_reference.json'), 'w'), indent=1)
