import contextlib
import io
import os
import sys

import matplotlib
import pytest

matplotlib.use('Agg')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def run_boss(**settings):
    """One silent projection.main() on a freshly reloaded module (no leaked globals)."""
    import importlib
    import projection
    M = importlib.reload(projection)
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


@pytest.fixture(scope='session')
def B():
    import projection
    if not os.path.exists(projection.FILE_FACTORS_TYPOLOGY):
        pytest.exit('Run Building_factors.py first (outputs/data/factors/ missing).')
    return run_boss()


# MODEL v3.0.0: the tests of the v2 lever set, figures and data locks are kept for the record in tests/retired/
# (their locks describe MODEL v2.1; the legacy Reference is locked by tests/test_reference_legacy.py)
collect_ignore_glob = ['retired/*']
