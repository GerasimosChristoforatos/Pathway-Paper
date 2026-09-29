"""Append one entry to CHANGELOG.md: the before/after metrics table.

    python tools/changelog.py "<title>" "<one-paragraph description>"

'before' is outputs/metrics.json as committed at HEAD (the state before the
change); 'after' is outputs/metrics.json as just written by run_all.py. Run it
after a FULL run_all.py and before committing the change.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import METRICS, ROOT, table  # noqa: E402

CHANGELOG = os.path.join(ROOT, 'CHANGELOG.md')


def main(title, description, validation=None):
    rel = os.path.relpath(METRICS, ROOT)
    try:
        before = json.loads(subprocess.check_output(['git', 'show', f'HEAD:{rel}'], cwd=ROOT, stderr=subprocess.DEVNULL))
    except subprocess.CalledProcessError:
        before = {}
    with open(METRICS) as f:
        after = json.load(f)
    entry = [f'\n## {title}\n', description.strip() + '\n', table(before, after) + '\n']
    vfile = os.path.join(ROOT, 'outputs', 'validation.md')
    if os.path.exists(vfile):
        with open(vfile) as f:
            entry.append('Validation (outputs/validation.md):\n\n' + f.read().strip() + '\n')
    with open(CHANGELOG, 'a') as f:
        f.write('\n'.join(entry))
    print('\n'.join(entry))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
