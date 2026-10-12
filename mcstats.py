"""
Statistics of the Monte Carlo insight analyses (MODEL v2.1.0), in numpy / scipy only
====================================================================================
The environment has no statsmodels; each method is implemented from its published definition and
checked in tests/test_mcstats.py against closed-form cases and against an independent optimiser.

  lowess(x, y)          Cleveland (1979) J. Am. Stat. Assoc. 74, 829: robust locally weighted linear
                        regression; span frac of the points, tricube distance weights, `it` robustness
                        iterations with bisquare weights on the residuals scaled by 6 x median |residual|.
                        The fit at every data point uses its k = ceil(frac n) nearest neighbours in x;
                        the curve at evaluation points uses the final robustness weights.
  src(X, y)             standardised regression coefficients: ordinary least squares of the standardised
                        output on the standardised inputs, with the coefficient of determination R^2
                        (Saltelli et al. 2008, Global Sensitivity Analysis: The Primer, s. 1.2.5; SRC are
                        a valid measure of importance when R^2 is high, conventionally >= 0.7).
  prcc(X, y)            partial rank correlation coefficients (Marino et al. 2008, J. Theor. Biol. 254, 178):
                        inputs and output rank-transformed; for each input the Pearson correlation of the
                        residuals of its ranks and of the output ranks, each regressed (with intercept) on
                        the ranks of the other inputs.
  bootstrap(stat, ...)  percentile bootstrap (Efron & Tibshirani 1993, ch. 13) of a statistic over the
                        draws, resampled with replacement, fixed seed.
  logistic(X, y)        maximum-likelihood logistic regression by Newton-Raphson (iteratively reweighted
                        least squares), standard errors from the inverse observed information, Wald 95%
                        intervals, odds ratios exp(beta); McFadden's pseudo-R^2; quasi-complete separation
                        is detected (non-convergence or fitted probabilities at 0 or 1) and raised.
  firth(X, y)           Firth (1993) Biometrika 80, 27 penalised-likelihood logistic regression, the standard
                        remedy when the maximum-likelihood estimate does not exist because of separation
                        (Heinze & Schemper 2002, Stat. Med. 21, 2409): log L*(b) = log L(b) + 1/2 log|I(b)|,
                        maximised by Newton-Raphson on the modified score with step halving; 95% intervals by
                        the profile penalised likelihood (2 [log L*(b_hat) - max log L*(b | b_j)] = chi2_1(0.95)),
                        as Heinze & Schemper recommend (Wald intervals are unreliable under separation).
  wilson(k, n)          Wilson (1927) score interval of a binomial proportion.
"""
import math

import numpy as np
from scipy import special, stats

Z975 = float(stats.norm.ppf(0.975))


# ---------------------------------------------------------------------------
# LOWESS
# ---------------------------------------------------------------------------
def _tricube(u):
    u = np.clip(np.abs(u), 0.0, 1.0)
    return (1.0 - u ** 3) ** 3


def _bisquare(u):
    u = np.clip(np.abs(u), 0.0, 1.0)
    return (1.0 - u ** 2) ** 2


def _local_fit(xs, ys, rw, x0, k):
    """Weighted linear fit at x0 over the k nearest neighbours of x0 in the sorted xs (contiguous window)."""
    n = len(xs)
    i = int(np.searchsorted(xs, x0))
    lo, hi = max(0, i - k), min(n, i + k)            # the k nearest lie within [i - k, i + k)
    cand = np.abs(xs[lo:hi] - x0)
    h = np.partition(cand, k - 1)[k - 1] if len(cand) >= k else cand.max()
    if h <= 0.0:                                     # all neighbours tied at x0
        sel = cand <= 0.0
        wsum = rw[lo:hi][sel].sum()
        return float(np.sum(rw[lo:hi][sel] * ys[lo:hi][sel]) / wsum) if wsum > 0 else float(ys[lo:hi][sel].mean())
    w = _tricube(cand / (h * (1.0 + 1e-12))) * rw[lo:hi]   # the k-th neighbour gets weight ~0 (Cleveland 1979)
    xw, yw = xs[lo:hi], ys[lo:hi]
    sw = w.sum()
    if sw <= 0.0:
        return float(np.mean(yw))
    xm, ym = np.sum(w * xw) / sw, np.sum(w * yw) / sw
    sxx = np.sum(w * (xw - xm) ** 2)
    if sxx <= 1e-300 * max(1.0, abs(xm)):
        return float(ym)
    b = np.sum(w * (xw - xm) * (yw - ym)) / sxx
    return float(ym + b * (x0 - xm))


def lowess(x, y, frac=2.0 / 3.0, it=3, xvals=None):
    """Robust LOWESS (Cleveland 1979). Returns (fitted values at x, in the input order; curve at xvals or None)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 3:
        raise ValueError('lowess needs at least 3 points')
    order = np.argsort(x, kind='mergesort')
    xs, ys = x[order], y[order]
    k = min(n, max(2, int(math.ceil(frac * n))))
    rw = np.ones(n)
    fit = np.empty(n)
    for step in range(it + 1):
        for j in range(n):
            fit[j] = _local_fit(xs, ys, rw, xs[j], k)
        if step == it:
            break
        e = ys - fit
        s = np.median(np.abs(e))
        if s <= 0.0:
            break
        rw = _bisquare(e / (6.0 * s))
    out = np.empty(n)
    out[order] = fit
    curve = None if xvals is None else np.array([_local_fit(xs, ys, rw, float(v), k) for v in np.asarray(xvals, float)])
    return out, curve


# ---------------------------------------------------------------------------
# SRC and PRCC
# ---------------------------------------------------------------------------
def _standardise(a):
    a = np.asarray(a, float)
    sd = a.std(axis=0, ddof=1)
    if np.any(sd <= 0):
        raise ValueError('a variable has zero variance')
    return (a - a.mean(axis=0)) / sd


def src(X, y):
    """Standardised regression coefficients and R^2 of the linear regression of y on X."""
    Xs, ys = _standardise(X), _standardise(np.asarray(y, float)[:, None])[:, 0]
    beta, *_ = np.linalg.lstsq(Xs, ys, rcond=None)
    resid = ys - Xs @ beta
    r2 = 1.0 - float(resid @ resid) / float(ys @ ys)
    return beta, r2


def _residual(A, b):
    A1 = np.column_stack([np.ones(len(b)), A])
    coef, *_ = np.linalg.lstsq(A1, b, rcond=None)
    return b - A1 @ coef


def prcc(X, y):
    """Partial rank correlation coefficient of each column of X with y."""
    R = np.column_stack([stats.rankdata(c) for c in np.asarray(X, float).T])
    ry = stats.rankdata(np.asarray(y, float))
    p = R.shape[1]
    out = np.empty(p)
    for i in range(p):
        others = np.delete(R, i, axis=1)
        ex, ey = _residual(others, R[:, i]), _residual(others, ry)
        out[i] = float(np.corrcoef(ex, ey)[0, 1])
    return out


def bootstrap(stat, X, y, B=1000, seed=0, level=0.95):
    """Percentile bootstrap of stat(X, y) -> array over the rows (draws). Returns (estimate, lower, upper)."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    est = np.asarray(stat(X, y), float)
    rng = np.random.default_rng(seed)
    n = len(y)
    reps = np.empty((B, est.size))
    for b in range(B):
        idx = rng.integers(0, n, n)
        reps[b] = np.asarray(stat(X[idx], y[idx]), float).ravel()
    a = (1.0 - level) / 2.0
    return est, np.percentile(reps, 100 * a, axis=0), np.percentile(reps, 100 * (1 - a), axis=0)


# ---------------------------------------------------------------------------
# Logistic regression
# ---------------------------------------------------------------------------
class Separation(ValueError):
    """Quasi-complete separation: the maximum-likelihood estimate does not exist."""


def logistic(X, y, max_iter=100, tol=1e-10):
    """Logistic regression of the 0/1 outcome y on X (an intercept is added). Returns a dict with beta, se,
    Wald 95% intervals, odds ratios with intervals, log-likelihoods, McFadden pseudo-R^2 and iterations."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    if not set(np.unique(y)) <= {0.0, 1.0}:
        raise ValueError('logistic: y must be 0/1')
    if y.min() == y.max():
        raise Separation('logistic: the outcome has a single class')
    A = np.column_stack([np.ones(len(y)), X])
    beta = np.zeros(A.shape[1])
    beta[0] = math.log(y.mean() / (1 - y.mean()))
    for it in range(1, max_iter + 1):
        eta = A @ beta
        p = special.expit(eta)
        W = p * (1 - p)
        g = A.T @ (y - p)
        H = (A * W[:, None]).T @ A
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError as e:
            raise Separation(f'logistic: singular information matrix at iteration {it} (separation?)') from e
        beta = beta + step
        if not np.all(np.isfinite(beta)) or np.max(np.abs(beta)) > 50:
            raise Separation(f'logistic: coefficients diverge at iteration {it} (separation)')
        if np.max(np.abs(step)) < tol:
            break
    else:
        raise Separation(f'logistic: no convergence in {max_iter} iterations (separation?)')
    eta = A @ beta
    p = special.expit(eta)
    if np.any(p < 1e-12) or np.any(p > 1 - 1e-12):
        raise Separation('logistic: fitted probabilities at 0 or 1 (quasi-complete separation)')
    H = (A * (p * (1 - p))[:, None]).T @ A
    cov = np.linalg.inv(H)
    se = np.sqrt(np.diag(cov))
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    p0 = y.mean()
    ll0 = float(len(y) * (p0 * math.log(p0) + (1 - p0) * math.log(1 - p0)))
    lo, hi = beta - Z975 * se, beta + Z975 * se
    return dict(beta=beta, se=se, ci_lo=lo, ci_hi=hi, odds_ratio=np.exp(beta), or_lo=np.exp(lo), or_hi=np.exp(hi),
                z=beta / se, p_value=2 * stats.norm.sf(np.abs(beta / se)), loglik=ll, loglik_null=ll0,
                mcfadden_r2=1.0 - ll / ll0, iterations=it, n=int(len(y)), events=int(y.sum()), cov=cov)


def auc(score, y):
    """Area under the ROC curve (Mann-Whitney U / (n1 n0)), ties counted one half."""
    y = np.asarray(y, bool)
    r = stats.rankdata(np.asarray(score, float))
    n1, n0 = int(y.sum()), int((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def _penalised_loglik(A, y, beta):
    eta = A @ beta
    ll = float(np.sum(y * eta - np.logaddexp(0.0, eta)))
    p = special.expit(eta)
    W = p * (1 - p)
    sign, logdet = np.linalg.slogdet((A * W[:, None]).T @ A)
    return ll + 0.5 * logdet if sign > 0 else -np.inf


def _firth_score(A, y, beta):
    """Firth's modified score: the exact gradient of the penalised log-likelihood (Firth 1993, eq. 2), and the
    Fisher information."""
    p = special.expit(A @ beta)
    W = p * (1 - p)
    I = (A * W[:, None]).T @ A
    h = W * np.einsum('ij,jk,ik->i', A, np.linalg.inv(I), A)    # leverages of the weighted hat matrix
    return A.T @ (y - p + h * (0.5 - p)), I


GRAD_TOL = 1e-7


def _firth_fit(A, y, beta0, free, max_iter=200, tol=1e-10):
    """Maximise the penalised log-likelihood over the coordinates in `free` (the others held at beta0): Newton-
    Raphson with the Fisher information and step halving; where step halving stalls, BFGS on the exact gradient
    from that point. Accepted only with the free gradient below GRAD_TOL (ValueError otherwise)."""
    from scipy.optimize import minimize
    beta = beta0.copy()
    lstar = _penalised_loglik(A, y, beta)
    it = 0
    for it in range(1, max_iter + 1):
        U, I = _firth_score(A, y, beta)
        step = np.zeros_like(beta)
        step[free] = np.linalg.solve(I[np.ix_(free, free)], U[free])
        t, moved = 1.0, False
        while t >= 1e-8:                                        # step halving: the penalised likelihood must rise
            cand = beta + t * step
            lc = _penalised_loglik(A, y, cand)
            if lc >= lstar - 1e-12:
                moved = True
                break
            t /= 2.0
        if not moved:
            break                                               # Newton stalled: hand over to BFGS
        beta, lstar = cand, lc
        if np.max(np.abs(t * step)) < tol:
            break
    U, _ = _firth_score(A, y, beta)
    if np.max(np.abs(U[free])) > GRAD_TOL:
        def f(bf):
            b = beta.copy()
            b[free] = bf
            v = _penalised_loglik(A, y, b)
            return np.inf if not np.isfinite(v) else -v

        def g(bf):
            b = beta.copy()
            b[free] = bf
            return -_firth_score(A, y, b)[0][free]
        o = minimize(f, beta[free], jac=g, method='BFGS', options=dict(gtol=GRAD_TOL / 10, maxiter=10000))
        beta = beta.copy()
        beta[free] = o.x
        lstar = _penalised_loglik(A, y, beta)
        U, _ = _firth_score(A, y, beta)
        if np.max(np.abs(U[free])) > GRAD_TOL:
            raise ValueError(f'firth: no convergence (gradient {np.max(np.abs(U[free])):.1e})')
    return beta, lstar, it


def firth(X, y, level=0.95):
    """Firth penalised-likelihood logistic regression of the 0/1 outcome y on X (intercept added), with profile
    penalised-likelihood intervals. Returns a dict as logistic() (ci_* and or_* from the profile)."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    A = np.column_stack([np.ones(len(y)), X])
    k = A.shape[1]
    allc = np.arange(k)
    beta, lstar, it = _firth_fit(A, y, np.zeros(k), allc)
    p = special.expit(A @ beta)
    se = np.sqrt(np.diag(np.linalg.inv((A * (p * (1 - p))[:, None]).T @ A)))
    crit = float(stats.chi2.ppf(level, 1))

    def dev(j, bj):
        b0 = beta.copy()
        b0[j] = bj
        try:
            _, l_j, _ = _firth_fit(A, y, b0, np.delete(allc, j))
        except (np.linalg.LinAlgError, ValueError):
            # the information matrix is singular at b_j (fitted probabilities at 0 or 1): log|I| = -inf, so the
            # penalised likelihood is -inf there and b_j lies outside any finite profile interval
            return np.inf
        return 2.0 * (lstar - l_j) - crit

    from scipy.optimize import brentq
    lo, hi = np.empty(k), np.empty(k)
    for j in range(k):
        for sgn, out in ((-1.0, lo), (1.0, hi)):
            d0 = max(se[j], 1e-3) / 2.0                      # walk outwards in half-SE steps until the crossing
            inner, b = beta[j], beta[j] + sgn * d0
            while dev(j, b) < 0.0:
                inner, b = b, b + sgn * d0
                if abs(b - beta[j]) > 200 * max(se[j], 1e-3):
                    raise ValueError('firth: profile interval not bracketed')
            out[j] = brentq(lambda v: min(dev(j, v), 1e6), min(inner, b), max(inner, b), xtol=1e-10)
            # guard against a local constrained maximum (the surface can be multimodal under separation): refit
            # the bound from other starts; a higher maximum there would move the bound, so it stops the run
            b0 = beta.copy()
            b0[j] = out[j]
            free = np.delete(allc, j)
            _, l_ref, _ = _firth_fit(A, y, b0, free)
            for start in (np.zeros(k), 0.5 * beta, -beta):
                s0 = start.copy()
                s0[j] = out[j]
                try:
                    _, l_alt, _ = _firth_fit(A, y, s0, free)
                except (np.linalg.LinAlgError, ValueError):
                    continue
                if l_alt > l_ref + 1e-8:
                    raise ValueError(f'firth: a higher constrained maximum at the profile bound of coefficient {j}')
    eta = A @ beta
    ll = float(np.sum(y * eta - np.logaddexp(0.0, eta)))
    p0 = y.mean()
    ll0 = float(len(y) * (p0 * math.log(p0) + (1 - p0) * math.log(1 - p0)))
    return dict(beta=beta, se=se, ci_lo=lo, ci_hi=hi, odds_ratio=np.exp(beta), or_lo=np.exp(lo), or_hi=np.exp(hi),
                penalised_loglik=lstar, loglik=ll, loglik_null=ll0, mcfadden_r2=1.0 - ll / ll0, iterations=it,
                n=int(len(y)), events=int(y.sum()), interval='profile penalised likelihood')


def wilson(k, n, level=0.95):
    """Wilson score interval of the proportion k / n."""
    if n == 0:
        return float('nan'), float('nan')
    z = float(stats.norm.ppf(0.5 + level / 2))
    ph = k / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    hw = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - hw, c + hw
