"""Reconciliation of the time-resolved accounting with whole life at construction
(the Reference, median demographics), written to outputs/data/baseline/reconciliation.json
and outputs/reports/reconciliation.md.

At 2025 factors (DECARB_MODE 'none', A4-A5 held) the identity is exact:
    whole life at construction, 2025 factors
        = upfront (materials and construction A1-A5 + soil carbon loss) + maintenance (B2, B4) 2026-2050
          + committed B2/B4 (after 2050) + committed C1-C4.
With decarbonisation (adopted: item A1-A3 paths, A4-A5 'resch'):
    whole life at construction, adopted A1-A3 paths with A4-A5 held
        - A4-A5 decarbonisation of construction
        - decarbonisation of the maintenance 2026-2050
        = upfront + maintenance 2026-2050 + committed B2/B4 (upper, 2025 factors) + committed C1-C4,
the lower committed bound holding the 2050 factors after 2050. Every term is computed
by projection.main(); the identities are asserted.

    python tools/reconciliation.py
"""
import contextlib
import importlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import layout  # noqa: E402
import naming as N  # noqa: E402
TOL = 1e-9                                         # relative


def run(**settings):
    import projection
    M = importlib.reload(projection)
    M.SHOW_PLOTS = False
    M.SAVE_FIGURES = False
    for k, v in settings.items():
        assert hasattr(M, k), k
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        return M.main()


def split(B):
    c = B['COMMITTED']
    return dict(upfront_kt=float(B['_upfront'] + B['_soil'] / 1e6), b_inwindow_kt=float(c['B_inwindow_kt']),
                b_committed_upper_kt=float(c['B_upper_kt']), b_committed_lower_kt=float(c['B_lower_kt']),
                c_committed_upper_kt=float(c['C_upper_kt']), c_committed_lower_kt=float(c['C_lower_kt']),
                c_held_share=float(c['C_held_share']), within_window_kt=float(B['tot_carbon_median']))


def class_table(B):
    """C1-C4 / A1-A3 and D / A1-A3 by item class: the case-study items (sum over the 16 case studies) and the
    pooled class factors weighted by the Reference 2026-2050 cohort floor area (the C1-C4 split of the committed
    range and the Module D row; Building_factors.class_factors)."""
    import pandas as pd
    import Building_factors as BF
    it = pd.read_csv(os.path.join(ROOT, 'data', 'derived', 'material_items.csv'))
    g = it.groupby('class')[['A1-A3', 'C1-C4', 'D']].sum()
    cls = pd.read_csv(BF.OUT_CLASS).pivot_table(index=['Class', 'Typology'], columns='Stage', values='kgCO2e_per_m2')
    w = B['evol_typ_total'].loc[2026:2050].sum()                      # m2 by typology, the Reference cohorts
    wt = cls.mul(w, level='Typology', axis=0).groupby('Class').sum()
    held = list(BF.C14_HELD_CLASSES)
    rows = []
    for c in g.sort_values('A1-A3', ascending=False).index:
        r = lambda a, b: f'{a / b:.3f}' if b else '-'
        rows.append(f"| {c} | {'held (carbon-bearing)' if c in held else 'energy part'} | "
                    f"{r(g.loc[c, 'C1-C4'], g.loc[c, 'A1-A3'])} | {r(wt.loc[c, 'C1-C4'], wt.loc[c, 'A1-A3'])} | "
                    f"{r(g.loc[c, 'D'], g.loc[c, 'A1-A3'])} | {r(wt.loc[c, 'D'], wt.loc[c, 'A1-A3'])} |")
    tot_i, tot_w = g.sum(), wt.sum()
    share_i = g.loc[held, 'C1-C4'].sum() / tot_i['C1-C4']
    share_w = wt.loc[[c for c in held if c in wt.index], 'C1-C4'].sum() / tot_w['C1-C4']
    return (['## End of life (C1-C4) and Module D by item class', '',
             'C1-C4 is split by material chemistry (Building_factors.C14_HELD_CLASSES), not by a ratio threshold: the '
             'carbon-bearing classes are held at 2025 in both bounds of the committed range; the energy part of the '
             'others takes the generic construction-stage factor of 2050 in the lower bound. Items: sums over the '
             'case-study items (data/derived/material_items.csv); weighted: the pooled class factors (as the typology '
             'factors) weighted by the Reference 2026-2050 cohort floor area by typology. CONCRETE (weighted 0.12-0.13) '
             'is in the energy part: the low A1-A3 of unreinforced low-strength in-situ concrete, not material carbon.',
             '', '| class | end of life | C1-C4 / A1-A3, items | C1-C4 / A1-A3, weighted | D / A1-A3, items | '
             'D / A1-A3, weighted |', '|---|---|---|---|---|---|'] + rows +
            [f"| all classes | | {tot_i['C1-C4'] / tot_i['A1-A3']:.3f} | {tot_w['C1-C4'] / tot_w['A1-A3']:.3f} | "
             f"{tot_i['D'] / tot_i['A1-A3']:.3f} | {tot_w['D'] / tot_w['A1-A3']:.3f} |", '',
             f'Share of C1-C4 in the carbon-bearing (held) classes: items {100 * share_i:.1f}%, Reference cohorts '
             f'{100 * share_w:.1f}%.'])


def close(a, b):
    return abs(a - b) <= TOL * abs(b)


def main():
    wl, tr = dict(ACCOUNTING='whole_life_at_construction'), dict(ACCOUNTING='time_resolved')
    frozen = dict(DECARB_MODE='none', DECARB_A45='held')
    adopted = dict(DECARB_MODE='horup_item', DECARB_A45='resch')
    wl_frozen = float(run(**wl, **frozen)['tot_carbon_median'])
    wl_a45_held = float(run(**wl, DECARB_MODE='horup_item', DECARB_A45='held')['tot_carbon_median'])
    wl_adopted = float(run(**wl, **adopted)['tot_carbon_median'])
    s0, s1 = split(run(**tr, **frozen)), split(run(**tr, **adopted))

    sum0 = s0['upfront_kt'] + s0['b_inwindow_kt'] + s0['b_committed_upper_kt'] + s0['c_committed_upper_kt']
    a45 = wl_a45_held - wl_adopted                  # A4-A5 decarbonisation of construction
    b_dec = s0['b_inwindow_kt'] - s1['b_inwindow_kt']   # decarbonisation of the maintenance 2026-2050
    sum1u = s1['upfront_kt'] + s1['b_inwindow_kt'] + s1['b_committed_upper_kt'] + s1['c_committed_upper_kt']
    sum1l = s1['upfront_kt'] + s1['b_inwindow_kt'] + s1['b_committed_lower_kt'] + s1['c_committed_lower_kt']
    checks = {
        '2025 factors: split sums to the whole-life total at 2025 factors': close(sum0, wl_frozen),
        '2025 factors: committed B upper = lower': close(s0['b_committed_upper_kt'], s0['b_committed_lower_kt']),
        '2025 factors: committed C1-C4 upper = lower': close(s0['c_committed_upper_kt'], s0['c_committed_lower_kt']),
        'decarbonised: committed C1-C4 upper (2025 factors) unchanged': close(s1['c_committed_upper_kt'],
                                                                             s0['c_committed_upper_kt']),
        'decarbonised: committed B upper (2025 factors) unchanged': close(s1['b_committed_upper_kt'],
                                                                         s0['b_committed_upper_kt']),
        'decarbonised: whole life (A4-A5 held) - A4-A5 decarbonisation - maintenance decarbonisation = split (upper)':
            close(wl_a45_held - a45 - b_dec, sum1u),
    }
    out = dict(scenario='REF', whole_life_2025_factors_kt=wl_frozen, whole_life_a45_held_kt=wl_a45_held,
               whole_life_adopted_a45_resch_kt=wl_adopted, frozen_2025_factors=s0, adopted=s1,
               a45_construction_decarbonisation_kt=a45, b_inwindow_decarbonisation_kt=b_dec,
               sum_2025_factors_kt=sum0, sum_adopted_upper_kt=sum1u, sum_adopted_lower_kt=sum1l, checks=checks)
    with open(layout.writing(layout.data('baseline/reconciliation.json')), 'w') as f:
        json.dump(N.keys(out), f, indent=2)
    L = ['# Reconciliation: time-resolved vs whole life at construction (generated by tools/reconciliation.py)', '',
         'The Reference, median demographics, kt CO2e. Upfront = materials and construction (A1-A5) of 2026-2050 '
         'construction + soil carbon loss.',
         '', '| term | 2025 factors (none, A4-A5 held) | decarbonised (adopted) |', '|---|---|---|',
         f"| upfront (A1-A5 and soil carbon loss), 2026-2050 | {s0['upfront_kt']:,.1f} | {s1['upfront_kt']:,.1f} |",
         f"| maintenance (B2, B4), 2026-2050 | {s0['b_inwindow_kt']:,.1f} | {s1['b_inwindow_kt']:,.1f} |",
         f"| **carbon 2026-2050 (reported total)** | **{s0['within_window_kt']:,.1f}** | "
         f"**{s1['within_window_kt']:,.1f}** |",
         f"| committed B2/B4 after 2050 (upper: 2025 factors) | {s0['b_committed_upper_kt']:,.1f} | "
         f"{s1['b_committed_upper_kt']:,.1f} |",
         f"| committed B2/B4 after 2050 (lower: 2050 factors held) | {s0['b_committed_lower_kt']:,.1f} | "
         f"{s1['b_committed_lower_kt']:,.1f} |",
         f"| committed C1-C4 (upper: 2025 factors) | {s0['c_committed_upper_kt']:,.1f} | "
         f"{s1['c_committed_upper_kt']:,.1f} |",
         f"| committed C1-C4 (lower: carbon-bearing classes at 2025, energy part at the 2050 generic factor) | "
         f"{s0['c_committed_lower_kt']:,.1f} | {s1['c_committed_lower_kt']:,.1f} |",
         f"| sum, committed upper | {sum0:,.1f} | {sum1u:,.1f} |",
         f"| sum, committed lower | {sum0:,.1f} | {sum1l:,.1f} |",
         f"| whole life at construction (A4-A5 held) | {wl_frozen:,.1f} | {wl_a45_held:,.1f} |",
         f"| less A4-A5 decarbonisation of construction (Resch et al. 2021) | - | {-a45:,.1f} |",
         f"| less decarbonisation of maintenance within 2026-2050 | - | {-b_dec:,.1f} |",
         f"| = sum, committed upper | {wl_frozen:,.1f} | {wl_a45_held - a45 - b_dec:,.1f} |", '',
         '| identity | holds (relative tolerance 1e-9) |', '|---|---|']
    L += [f'| {k} | {"yes" if v else "NO"} |' for k, v in checks.items()]
    L += [''] + class_table(run(**tr, **adopted))
    with open(layout.writing(layout.report('reconciliation.md')), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    if not all(checks.values()):
        raise SystemExit('Reconciliation identity failed: ' + ', '.join(k for k, v in checks.items() if not v))


if __name__ == '__main__':
    main()
