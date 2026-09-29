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
    """One silent Boss.main() on a freshly reloaded module (no leaked globals)."""
    import importlib
    import Boss
    M = importlib.reload(Boss)
    M.SHOW_PLOTS = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


@pytest.fixture(scope='session')
def B():
    import Boss
    if not os.path.exists(Boss.FILE_FACTORS_TYPOLOGY):
        pytest.exit('Run Building_factors.py first (outputs/factors/ missing).')
    return run_boss()
