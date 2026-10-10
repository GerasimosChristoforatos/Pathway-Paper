"""Byte manifest of the release outputs (MODEL v2.0.0): tests/output_manifest_model_v2.json
(the manifests of model-v1.0.0 and model-v1.1.0 are kept at their releases: tag model-v1.0.0, and
tests/output_manifest_model_v1_1.json at the merge commit 4ad57f3 of main).

    python tools/output_manifest.py          # after the release run (python run_all.py)

Records the SHA-256 of every file under outputs/ (except the git-ignored console logs,
outputs/logs/) together with the environment that wrote them. tests/test_output_manifest.py
checks that a re-run reproduces every file byte for byte. Byte identity is expected only in
the same environment (Python, numpy, pandas, scipy, matplotlib, FreeType and machine
architecture: floating-point and font rasterisation can differ elsewhere); the test is skipped,
with the reason, in any other environment, where the numerical lock
(tests/test_regression_model_v1.py and tests/test_regression_model_v2.py, every number to 1e-12
relative) still applies.

Written once per release, from the outputs the release commits; never by run_all.py.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import layout  # noqa: E402

TARGET = os.path.join(ROOT, 'tests', 'output_manifest_model_v2.json')
EXCLUDED = ('logs',)                               # console logs: git-ignored, not part of the release


def environment():
    """The software and machine that determine the bytes of the outputs."""
    import matplotlib
    import matplotlib.ft2font
    import numpy
    import pandas
    import scipy
    return dict(python=platform.python_version(), numpy=numpy.__version__, pandas=pandas.__version__,
                scipy=scipy.__version__, matplotlib=matplotlib.__version__,
                freetype=matplotlib.ft2font.__freetype_version__, machine=platform.machine(),
                system=platform.system())


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def output_files():
    """Every release output file, as a path relative to outputs/ with '/' separators."""
    out = []
    for d, _, files in os.walk(layout.OUT):
        rel = os.path.relpath(d, layout.OUT)
        if rel.split(os.sep)[0] in EXCLUDED:
            continue
        out += [os.path.normpath(os.path.join(rel, f)).replace(os.sep, '/') for f in files]
    return sorted(out)


def main():
    if os.environ.get('PATHWAY_QUICK') == '1':
        raise SystemExit('output_manifest: a quick run is never a release run.')
    with open(layout.data('metrics.json', frozen=False)) as f:
        mode = json.load(f).get('run_mode')
    if mode != 'full':
        raise SystemExit(f'output_manifest: the outputs are from a {mode!r} run; run python run_all.py first.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    files = {rel: sha256(os.path.join(layout.OUT, rel)) for rel in output_files()}
    man = dict(meta=dict(purpose='MODEL v1.1.0: SHA-256 of every release output (tests/test_output_manifest.py)',
                         code_commit=commit, run='python run_all.py (full)', environment=environment(),
                         n_files=len(files)),
               files=files)
    with open(TARGET, 'w') as f:
        json.dump(man, f, indent=1, sort_keys=False)
        f.write('\n')
    print(f'output_manifest: {len(files)} files -> {os.path.relpath(TARGET, ROOT)}')


if __name__ == '__main__':
    main()
