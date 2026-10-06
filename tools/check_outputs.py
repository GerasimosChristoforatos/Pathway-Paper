"""Final check of the generated outputs (run_all.py, last step): the storyline
scenario of v1.0.2-v1.2 (S2 + damped mix trend) must not appear in any
generated output or document of the adopted and frozen runs. The stored
--compare-modes run (outputs/modes/, DECARB_MODES.md, decarb_modes.json)
predates baseline-pb-v2 and is excluded; DECARB_MODES.md carries a note.

    python tools/check_outputs.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')
STORYLINE = re.compile(r'storyline|S2-held|S3-10-trend|damped mix trend|intensification continues', re.I)
EXCLUDED = ('DECARB_MODES.md', 'decarb_modes.json')
# written by run_all after the tests step (checked here, not by tests/test_v2.py)
AFTER_TESTS = ('metrics.json', 'RESULTS.md', 'BASELINE_DRAFT.md', 'PB_METHODS_DRAFT.md', 'ASSUMPTIONS.md')


def generated_files(include_docs=True):
    files = [p for d in (OUT, os.path.join(OUT, 'frozen')) for ext in ('*.md', '*.json', '*.csv')
             for p in glob.glob(os.path.join(d, ext))]
    files += [os.path.join(ROOT, f) for f in ('ASSUMPTIONS.md', 'FIGURES.md', 'README.md')]
    files = [p for p in files if os.path.basename(p) not in EXCLUDED]
    if os.environ.get('PATHWAY_QUICK') == '1':      # quick runs do not re-run the frozen PB step
        files = [p for p in files if not (os.path.dirname(p).endswith('frozen')
                                          and os.path.basename(p).startswith('pb_'))]
    if not include_docs:
        files = [p for p in files if os.path.basename(p) not in AFTER_TESTS]
    return files


def storyline_hits(include_docs=True):
    hits = {}
    for p in generated_files(include_docs):
        with open(p, encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if STORYLINE.search(line):
                    hits.setdefault(os.path.relpath(p, ROOT), []).append(i)
    return hits


def main():
    hits = storyline_hits()
    if hits:
        print(f'check_outputs: storyline found in {hits}')
        sys.exit(1)
    print(f'check_outputs: no storyline in {len(generated_files())} generated files')


if __name__ == '__main__':
    main()
