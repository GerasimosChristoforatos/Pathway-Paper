"""The statistics of the Monte Carlo insight analyses (mcstats.py, MODEL v2.1.0).

1. LOWESS and logistic regression reproduce statsmodels (tests/fixtures/mcstats_reference.json, written by
   tests/make_mcstats_reference.py with statsmodels on fixed synthetic data; statsmodels is not a dependency).
2. Closed-form cases: LOWESS returns an exact line on linear data; SRC equal the generating coefficients on a
   noiseless standardised linear model (R^2 = 1); PRCC is +-1 for a monotone noiseless output of one input and
   is invariant to monotone transforms; the percentile bootstrap brackets the estimate; logistic regression
   detects complete separation; the AUC of a perfect score is 1.
3. The logistic maximum is the maximum: scipy.optimize on the negative log-likelihood gives the same beta.
4. Firth's penalised likelihood: the estimate is the maximum of log L + 1/2 log|I| (independent BFGS), it is finite
   under complete separation, it is close to maximum likelihood without separation in a large sample, and every
   profile bound has the penalised-likelihood deviance chi2_1(0.95) against an independent constrained BFGS.
   (Cross-checked once against the firthlogist package, a port of R logistf: estimates agree to 1e-8; profile
   bounds agree to 1e-11 without separation; under separation one firthlogist bound fails the deviance check that
   ours passes.) The Wilson interval matches its closed form.
"""
import json
import os

import numpy as np
import pytest
from scipy import optimize

from conftest import ROOT

import mcstats as M

REF = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'mcstats_reference.json')))


def ref_data():
    from mcstats_data import data
    return data()


def test_lowess_reproduces_statsmodels():
    x, y, _, _ = ref_data()
    fit, curve = M.lowess(x, y, frac=2 / 3, it=3, xvals=np.array(REF['lowess_xvals']))
    assert np.max(np.abs(fit - np.array(REF['lowess_fit']))) < 1e-9
    assert np.max(np.abs(curve - np.array(REF['lowess_curve']))) < 1e-9


def test_logistic_reproduces_statsmodels_and_scipy():
    _, _, X, yy = ref_data()
    r = M.logistic(X, yy)
    assert np.max(np.abs(r['beta'] - np.array(REF['logit_beta']))) < 1e-8
    assert np.max(np.abs(r['se'] - np.array(REF['logit_se']))) < 1e-8
    assert abs(r['mcfadden_r2'] - REF['logit_mcfadden']) < 1e-9
    A = np.column_stack([np.ones(len(yy)), X])
    nll = lambda b: float(np.sum(np.logaddexp(0, A @ b) - yy * (A @ b)))
    o = optimize.minimize(nll, np.zeros(A.shape[1]), method='BFGS', options=dict(gtol=1e-10))
    assert np.max(np.abs(o.x - r['beta'])) < 1e-5


def test_lowess_exact_on_a_line():
    x = np.linspace(0, 10, 200)
    fit, curve = M.lowess(x, 3.0 - 0.5 * x, xvals=np.array([2.5, 7.5]))
    assert np.max(np.abs(fit - (3.0 - 0.5 * x))) < 1e-10
    assert np.max(np.abs(curve - np.array([1.75, -0.75]))) < 1e-10


def test_src_and_prcc_closed_form():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(2000, 3))
    Xs = (X - X.mean(0)) / X.std(0, ddof=1)
    beta, r2 = M.src(X, Xs @ np.array([0.6, -0.3, 0.1]))
    b_true = np.array([0.6, -0.3, 0.1]) / np.std(Xs @ np.array([0.6, -0.3, 0.1]), ddof=1)
    assert abs(r2 - 1) < 1e-12 and np.max(np.abs(beta - b_true)) < 1e-10
    p = M.prcc(X, np.exp(X[:, 0]))
    assert abs(p[0] - 1) < 1e-12
    y = X[:, 0] + 0.5 * X[:, 1] + rng.normal(size=2000)
    assert np.max(np.abs(M.prcc(X, y) - M.prcc(np.exp(X), y ** 3))) < 1e-12


def test_bootstrap_brackets_the_estimate():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(500, 2))
    y = X[:, 0] + rng.normal(size=500)
    est, lo, hi = M.bootstrap(lambda a, b: M.src(a, b)[0], X, y, B=200, seed=5)
    assert np.all(lo <= est) and np.all(est <= hi)


def test_logistic_detects_separation_and_auc():
    x = np.linspace(-1, 1, 100)[:, None]
    with pytest.raises(M.Separation):
        M.logistic(x, (x[:, 0] > 0).astype(float))
    assert M.auc(x[:, 0], x[:, 0] > 0) == 1.0


def _sep_data(n=40, seed=13):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    return X, ((X @ np.array([1.5, -1.0, 0.5]) + 0.3) > 0).astype(float)


def test_firth_is_the_penalised_maximum_and_finite_under_separation():
    X, y = _sep_data()
    with pytest.raises(M.Separation):
        M.logistic(X, y)
    r = M.firth(X, y)
    A = np.column_stack([np.ones(len(y)), X])
    o = optimize.minimize(lambda b: -M._penalised_loglik(A, y, b), np.zeros(4),
                          jac=lambda b: -M._firth_score(A, y, b)[0], method='BFGS', options=dict(gtol=1e-10))
    assert np.max(np.abs(o.x - r['beta'])) < 1e-6
    assert np.all(np.isfinite(r['beta']))


def test_firth_profile_bounds_have_the_chi2_deviance():
    """At every profile bound: the constrained fit is a stationary point of the penalised likelihood, its deviance
    is chi2_1(0.95), and no independent BFGS run from 20 random starts finds a higher constrained maximum (the
    constrained surface can be multimodal under separation, so a single local optimiser is not a check)."""
    from scipy import stats
    X, y = _sep_data()
    r = M.firth(X, y)
    A = np.column_stack([np.ones(len(y)), X])
    crit = stats.chi2.ppf(0.95, 1)
    rng = np.random.default_rng(7)
    for j in range(4):
        free = [k for k in range(4) if k != j]
        for bj in (r['ci_lo'][j], r['ci_hi'][j]):
            b0 = r['beta'].copy()
            b0[j] = bj
            bm, lm, _ = M._firth_fit(A, y, b0, np.array(free))
            assert np.max(np.abs(M._firth_score(A, y, bm)[0][free])) < 1e-6
            assert abs(2 * (r['penalised_loglik'] - lm) - crit) < 1e-8

            def f(bf, bj=bj):
                b = np.empty(4)
                b[j], b[free] = bj, bf
                v = M._penalised_loglik(A, y, b)
                return -v if np.isfinite(v) else 1e10

            def g(bf, bj=bj):
                b = np.empty(4)
                b[j], b[free] = bj, bf
                return -M._firth_score(A, y, b)[0][free]
            for _ in range(20):
                o = optimize.minimize(f, rng.normal(scale=5.0, size=3), jac=g, method='BFGS', options=dict(gtol=1e-9))
                assert -o.fun <= lm + 1e-8


def test_firth_close_to_mle_in_a_large_sample():
    _, _, X, yy = ref_data()
    assert np.max(np.abs(M.firth(X, yy)['beta'] - M.logistic(X, yy)['beta'])) < 0.02


def test_wilson_interval():
    lo, hi = M.wilson(4996, 5000)
    z = 1.959963984540054
    ph, n = 4996 / 5000, 5000
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    hw = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    assert abs(lo - (c - hw)) < 1e-12 and abs(hi - (c + hw)) < 1e-12 and hi <= 1.0
