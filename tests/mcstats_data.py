"""Fixed synthetic data of tests/test_mcstats.py and tests/make_mcstats_reference.py."""
import numpy as np


def data():
    rng = np.random.default_rng(20261012)
    n = 600
    x = rng.normal(size=n)
    y = np.sin(x) + 0.3 * rng.standard_t(3, size=n)
    X = rng.normal(size=(n, 4))
    eta = 0.5 + X @ np.array([1.0, -0.5, 0.2, 0.0])
    yy = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    return x, y, X, yy
