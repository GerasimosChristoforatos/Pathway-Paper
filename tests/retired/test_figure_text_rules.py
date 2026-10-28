"""MODEL v4.3.1: every final figure follows the text rules of the suite (tools/check_figure_text.py): year ranges with
an en dash, thousands separators on every value of 1,000 or more. Draws every figure in a separate process into a
temporary folder (about 30 s)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import check_figure_text as C  # noqa: E402


def test_rules_detect_what_they_should():
    assert C.findings_of(['Cumulative carbon 2026-2050'])
    assert C.findings_of(['1400'])
    assert not C.findings_of(['Cumulative carbon 2026–2050', '1,400', '2030', '−1,200', '0.945'])


def test_every_figure_follows_the_text_rules(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'check_figure_text.py'), str(tmp_path)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
