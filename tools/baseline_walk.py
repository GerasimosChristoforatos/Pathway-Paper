"""Walk of the central baseline through the Step 2 commits, generated from the
committed outputs/metrics.json at each commit (never typed by hand).

    python tools/baseline_walk.py > outputs/baseline_walk.md
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import ROOT, get  # noqa: E402

STEPS = [  # (commit, label) in order; the first is the CP1 state (= original numbers)
    ('4721a25', 'CP1 (original model, infrastructure only)'),
    ('4d8326c', 'item 5: household size flat after 2043'),
    ('34a2f3e', 'item 6: household size anchored on 2023'),
    ('2213ba1', "item 7: completion lag (Little's law)"),
    ('dcb182c', 'census 2018/2023 private dwellings only (E1)'),
    ('6221b95', 'item 4: net replacement from census dwelling counts'),
    ('e1b3fbf', 'A1(a): observed 2026 population growth'),
    ('0ab938f', 'A1(a)+(c): nowcast 2026-27 consents, three-channel join'),
    ('a9c46fa', 'item 2 decision: S3 half-life 10 as reference'),
    ('14188c3', 'quarterly ERP for the population nowcast and household test'),
    ('71a864e', 'household channel reverts at rho'),
    ('0a366fd', 'item 8: no soil loss on net replacement'),
    ('5867f5e', 'item 9: MC within each scenario, centred inputs'),
]
COLS = [('boss.GFA_Mm2', 'floor area Mm2', '{:.2f}'), ('boss.carbon_kt', 'carbon kt', '{:,.0f}'),
        ('boss.upfront_kt', 'upfront kt', '{:,.0f}'), ('boss.step_2025_2026_pct', 'step 2025-26', '{:+.1f}%'),
        ('boss.S_2050', 'S 2050', '{:.3f}'), ('mc.GFA_p50', 'MC p50 Mm2', '{:.2f}'),
        ('mc.central_pct_GFA', 'central pct', '{:.1f}'),
        ('validation.observed_to_model_2026', '2026 obs/model', '{:.2f}')]


def at(commit):
    return json.loads(subprocess.check_output(['git', 'show', f'{commit}:outputs/metrics.json'], cwd=ROOT))


def main():
    print('| step | ' + ' | '.join(c[1] for c in COLS) + ' | change in floor area |')
    print('|---|' + '---|' * (len(COLS) + 1))
    prev = None
    for commit, lab in STEPS:
        m = at(commit)
        vals = [(f.format(get(m, k)) if get(m, k) is not None else 'n/a') for k, _, f in COLS]
        g = get(m, 'boss.GFA_Mm2')
        d = '' if prev is None else f'{g - prev:+.2f} ({100 * (g / prev - 1):+.1f}%)'
        print(f'| {lab} (`{commit}`) | ' + ' | '.join(vals) + f' | {d} |')
        prev = g


if __name__ == '__main__':
    main()
