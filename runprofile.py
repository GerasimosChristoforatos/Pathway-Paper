"""Run profiles (MODEL v3.0.0): run_all.py --profile {light,full}; environment PATHWAY_PROFILE.

    light (DEFAULT, temporary)  Monte Carlo 1,000 Latin-hypercube draws (its own fixed seed), Sobol indices off,
                                bootstrap 500 replicates; figures PNG at 200 dpi with a grey footer
                                "LIGHT RUN - n=1000"; every output under outputs/_light/ (a mirror of the outputs/
                                tree), so the full outputs are never overwritten.
    full                        Monte Carlo 5,000 Latin-hypercube draws (the existing design and seed), Sobol on,
                                bootstrap 2,000 replicates; figures PDF + PNG at 600 dpi; outputs under outputs/.

Only the stochastic layer differs. The deterministic results (the Reference, every lever / pathway / TL run, the
Shapley values, the waterfalls) do not depend on the profile (tests/test_profiles.py). The bootstrap setting
applies to the percentile intervals of the Harrell-Davis estimators (levers.hd_estimate) and of the Monte Carlo
SRC / PRCC importance (pathways_mc); the carbon-factor bootstrap that defines the Monte Carlo input distribution
(MonteCarlo.N_BOOT) is part of the Monte Carlo design and is the same in both profiles.
"""
import os

DEFAULT = 'light'
PROFILES = {
    'light': dict(name='light', n_draws=1000, mc_seed=20261014, sobol=False, bootstrap=500, dpi=200,
                  formats=('png',), out_subdir='_light', footer='LIGHT RUN – n=1000'),
    'full': dict(name='full', n_draws=5000, mc_seed=20260924, sobol=True, bootstrap=2000, dpi=600,
                 formats=('pdf', 'png'), out_subdir='', footer=None),
}


def name():
    p = os.environ.get('PATHWAY_PROFILE', DEFAULT)
    if p not in PROFILES:
        raise ValueError(f'Unknown run profile {p!r} (light | full).')
    return p


def get(key=None):
    p = PROFILES[name()]
    return p if key is None else p[key]
