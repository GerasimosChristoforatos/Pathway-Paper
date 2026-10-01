"""Totals and year-to-year steps from the run outputs (generated; no typed numbers).

    python tools/step_report.py [label]   # appends a row to outputs/step_report.csv
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')


def row(label):
    b = json.load(open(os.path.join(OUT, 'boss_results.json')))
    g = pd.Series(b['annual']['gfa_Mm2'], index=b['annual']['years'])
    a = pd.read_csv(os.path.join(OUT, 'montecarlo_annual.csv'), index_col=0)
    ch = 100 * (g.loc[2026:2050] / g.loc[2026:2050].shift(1) - 1)
    big = ch.abs().idxmax()
    import re
    log = open(os.path.join(OUT, 'logs', 'montecarlo.log')).read() if os.path.exists(os.path.join(OUT, 'logs', 'montecarlo.log')) else ''
    rt = re.findall(r'\(([\d,]+) s\)', log)
    return dict(label=label, GFA_Mm2=b['gfa_Mm2'], carbon_kt=b['carbon_kt'], upfront_kt=b['upfront_kt'],
                step_2027_28_pct=100 * (g[2028] / g[2027] - 1), step_2043_44_pct=100 * (g[2044] / g[2043] - 1),
                mc_p5_2028_Mm2=float(a.loc[2028, 'gfa_5']) / 1e6,
                largest_step=f'{big - 1}->{big}', largest_step_pct=float(ch[big]),
                mc_runtime_s=float(rt[-1].replace(',', '')) if rt else None)


if __name__ == '__main__':
    r = row(sys.argv[1] if len(sys.argv) > 1 else 'run')
    p = os.path.join(OUT, 'step_report.csv')
    d = pd.concat([pd.read_csv(p), pd.DataFrame([r])]) if os.path.exists(p) else pd.DataFrame([r])
    d.to_csv(p, index=False)
    print(pd.DataFrame([r]).round(3).to_string(index=False))
