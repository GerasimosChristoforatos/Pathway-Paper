"""MODEL v3.2.0 regression lock (tests/regression_model_v3_2.json; captured by tests/capture_regression_model_v3.py).
The MODEL v3.0.0 lock (tests/regression_model_v3.json) is kept: its link to v3.2 is tests/test_model_v3_2.py
(every run total equal; the Reference Monte Carlo hashes unchanged).

DETERMINISTIC: the SHA-256 of every deterministic data file (the Reference, every lever / pathway / TL run, the Shapley
values and subsets, the waterfalls, the lambda-sweep, the logs). These files are identical in the light and the full
profile (tests/test_profiles.py), so one lock serves both. JSON files that also carry profile-dependent fields (the run
mode, the bootstrap intervals) are locked after those fields are removed (canonical_json).
MONTE CARLO: per profile, the SHA-256 of the Monte Carlo draw files (the Reference and the pathway Monte Carlo)."""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, 'tests', 'regression_model_v3_2.json')
DETERMINISTIC_FILES = (
    'baseline/projection.json', 'baseline/annual.csv', 'baseline/bands_annual.csv', 'baseline/annual_by_stage.csv',
    'baseline/annual_by_material.csv', 'baseline/overbuild_absorption_log.csv', 'baseline/sensitivity_one_at_a_time.csv',
    'baseline/sensitivity_annual_carbon.csv', 'aesa/annual.csv',
    'pathways/runs.csv', 'pathways/annual.csv', 'pathways/bands.csv', 'pathways/bands_annual.csv', 'pathways/shapley.csv',
    'pathways/shapley_subsets.csv', 'pathways/waterfall.csv', 'pathways/lambda_sweep.csv', 'pathways/lever_annual.csv',
    'pathways/reoccupation_log.csv', 'pathways/solution_space.csv', 'pathways/ordering_checks.json',
    'pathways/theoretical_limit.json', 'pathways/backcast.json', 'pathways/levers.json',
    'sensitivity/reference_carbon.csv', 'sensitivity/pathway_carbon.csv', 'sensitivity/replacement_variants.csv',
    'sensitivity/tornado.csv', 'baseline/bands_history.csv', 'baseline/history_unexplained.json')
MC_FILES = ('montecarlo/draws_REF.csv', 'montecarlo/summary_REF.csv', 'pathways/montecarlo_draws.csv',
            'pathways/montecarlo_summary.csv')
PROFILE_KEYS = ('run_mode', 'ci_lo', 'ci_hi', 'bootstrap')


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in PROFILE_KEYS}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def canonical_json(path):
    with open(path) as f:
        return json.dumps(_strip(json.load(f)), sort_keys=True).encode()


def digest(data_dir, rel):
    p = os.path.join(data_dir, rel)
    b = canonical_json(p) if rel.endswith('.json') else open(p, 'rb').read()
    return hashlib.sha256(b).hexdigest()
