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


def pytest_configure(config):
    """The tests read the outputs of the active profile (PATHWAY_PROFILE, light by default). A fresh clone holds the
    committed full outputs only: stop with a clear message instead of a collection error."""
    import layout
    import runprofile
    if not os.path.exists(os.path.join(layout.FACTORS, 'factors_a13_decarb.csv')):
        pytest.exit(f'No outputs of the {runprofile.name()} profile ({os.path.relpath(layout.DATA, ROOT)} missing). '
                    'Run `python run_all.py --profile light` first, or test the committed full outputs with '
                    '`PATHWAY_PROFILE=full python -m pytest tests`.', returncode=4)


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

