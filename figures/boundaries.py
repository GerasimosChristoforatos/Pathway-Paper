"""Supplementary Table ST1 (data D22): how the
planetary-boundary budgets AR and AtP are built. The components with their units, the two budgets in 2025 and 2050 and
the 2050 population modifier, as Markdown and CSV in outputs/supplementary/boundaries/.

Read from the data files only (aesa/results.json: the components as numbers; figure_source/D22_boundaries.json: the
budgets and the population modifier by year); the model is never run here. Definitions: aesa.py (module docstring),
Horup et al. 2025 Eq. 1 (acquired rights), Hjalsted et al. 2021 Eqs. 5-6 and SI Eq. S1 (ability to pay).
"""
import os

import figure_plan as FP
import layout
from figures import data as D

ST1 = next(t for t in FP.SUPPLEMENTARY_TABLES if t['id'] == 'ST1')


def _sig(v, n=3):
    """v to n significant figures, thousands separators, never e-notation."""
    if v == 0:
        return '0'
    from math import floor, log10
    d = max(n - 1 - int(floor(log10(abs(v)))), 0)
    return f'{round(v, d):,.{d}f}'


def st1_rows():
    """[(quantity, value, unit, note)] of ST1."""
    r = D.js('aesa/results.json')
    c, st = r['components'], r['settings']
    d = D.src('D22_boundaries')
    yb = [int(y) for y in d['years']]
    i0, i1 = yb.index(int(st['T0'])), yb.index(2050)
    ar, atp, pm = d['B_AR_kt'], d['B_AtP_kt'], d['population_modifier']
    w0, w1 = st['AR_BASE_WINDOW']
    s0, s1 = st['SSEC_WINDOW']
    gdp = ('purchasing-power-parity constant 2021 international $ per person'
           if st['GDP_MEASURE'] == 'NY.GDP.PCAP.PP.KD' else st['GDP_MEASURE'])
    ratio = r['B_AtP_over_B_AR']
    return [
        ('Global safe operating space, climate', _sig(c['SOS_kg'] / 1e12), 'Gt CO₂e per year', c['pair_label']),
        ('Global annual emissions, same source', _sig(c['I_glob_kg'] / 1e12), 'Gt CO₂e per year', c['pair_label']),
        (f'Sector emissions, mean {w0}–{w1} (acquired-rights base)', _sig(c['I_sec_base_kg'] / 1e6), 'kt CO₂e per year',
         'new residential construction in New Zealand'),
        ('Ability-to-pay scaling factor α', _sig(c['alpha']), '–', f"base year {c['base_year_b']}"),
        ('World GDP per person', _sig(c['g_W']), gdp, f"World Development Indicators {st['GDP_MEASURE']}, "
                                                      f"{c['base_year_b']}"),
        ('New Zealand GDP per person', _sig(c['g_NZ']), gdp, f"{st['GDP_MEASURE']}, {c['base_year_b']}"),
        ('World / New Zealand GDP per person', _sig(c['g_W_over_g_NZ']), '–', ''),
        ('Sector share of New Zealand final consumption expenditure', _sig(100 * c['s_sec']), '%',
         f'mean of the annual shares {s0}–{s1}'),
        (f"Acquired-rights budget, {yb[i0]}", _sig(ar[i0]), 'kt CO₂e per year', ''),
        ("Acquired-rights budget, 2050", _sig(ar[i1]), 'kt CO₂e per year', ''),
        (f"Ability-to-pay budget, {yb[i0]}", _sig(atp[i0]), 'kt CO₂e per year', ''),
        ("Ability-to-pay budget, 2050", _sig(atp[i1]), 'kt CO₂e per year', ''),
        ('Ability-to-pay / acquired-rights budget', _sig(ratio['min']), '–',
         'the same in every year: both budgets scale with the population modifier'),
        ('Population modifier, 2050', _sig(pm[i1], 4), f'{yb[i0]} = 1',
         f"New Zealand share of world population relative to {yb[i0]}")]


def st1_budget_construction():
    rows = st1_rows()
    base = os.path.join(layout.SUPPLEMENTARY, ST1['folder'], ST1['file'])
    os.makedirs(os.path.dirname(base), exist_ok=True)
    head = ('Quantity', 'Value', 'Unit', 'Note')
    md = [f"# {ST1['id']} {ST1['title']}", '', '| ' + ' | '.join(head) + ' |', '|---|---:|---|---|']
    md += ['| ' + ' | '.join(r) + ' |' for r in rows]
    md += ['', 'Three significant figures (four for the population modifier). Sources: '
           + ', '.join(f'`data/{s}`' for s in ST1['source']) + '.']
    with open(base + '.md', 'w') as f:
        f.write('\n'.join(md) + '\n')
    import csv
    with open(base + '.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)
    return base


FIGURES = {}
TABLES = {'ST1_budget_construction': st1_budget_construction}
