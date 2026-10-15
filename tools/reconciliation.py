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
by projection.main(); the identities are asserted. These identities concern the life-cycle timing of the new
cohorts and are stated with ACCOUNTING 'instant' (soil at conversion). MODEL v3.1.0 adds the identity of the
adopted ACCOUNTING 'inventory':
    carbon 2026-2050 (inventory) = carbon 2026-2050 (instant) - soil of 2026-2050 conversions oxidised after 2050
                                   + legacy (soil tails of 2007-2025 conversions, B2/B4 of the 1992-2025 cohorts).

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
                c_committed_kt=float(c['C_kt']), within_window_kt=float(B['tot_carbon_median']))


def close(a, b):
    return abs(a - b) <= TOL * abs(b)


def main():
    wl = dict(LIFE_CYCLE_TIMING='whole_life_at_construction', ACCOUNTING='instant')
    tr = dict(LIFE_CYCLE_TIMING='time_resolved', ACCOUNTING='instant')
    frozen = dict(DECARB_MODE='none', DECARB_A45='held')
    adopted = dict(DECARB_MODE='horup_item', DECARB_A45='resch')
    wl_frozen = float(run(**wl, **frozen)['tot_carbon_median'])
    wl_a45_held = float(run(**wl, DECARB_MODE='horup_item', DECARB_A45='held')['tot_carbon_median'])
    wl_adopted = float(run(**wl, **adopted)['tot_carbon_median'])
    s0, s1 = split(run(**tr, **frozen)), split(run(**tr, **adopted))
    Binv = run(LIFE_CYCLE_TIMING='time_resolved', ACCOUNTING='inventory', **adopted)
    inv = dict(within_window_kt=float(Binv['tot_carbon_median']), soil_after_2050_kt=float(Binv['soil_after_2050'] / 1e6),
               legacy_kt=float(Binv['carbon_legacy'].iloc[1:].sum().sum() / 1e6),
               legacy_soil_kt=float(Binv['carbon_legacy']['soil'].iloc[1:].sum() / 1e6),
               legacy_b2b4_kt=float(Binv['carbon_legacy']['b'].iloc[1:].sum() / 1e6))

    sum0 = s0['upfront_kt'] + s0['b_inwindow_kt'] + s0['b_committed_upper_kt'] + s0['c_committed_kt']
    a45 = wl_a45_held - wl_adopted                  # A4-A5 decarbonisation of construction
    b_dec = s0['b_inwindow_kt'] - s1['b_inwindow_kt']   # decarbonisation of the maintenance 2026-2050
    sum1u = s1['upfront_kt'] + s1['b_inwindow_kt'] + s1['b_committed_upper_kt'] + s1['c_committed_kt']
    sum1l = s1['upfront_kt'] + s1['b_inwindow_kt'] + s1['b_committed_lower_kt'] + s1['c_committed_kt']
    checks = {
        '2025 factors: split sums to the whole-life total at 2025 factors': close(sum0, wl_frozen),
        '2025 factors: committed B upper = lower': close(s0['b_committed_upper_kt'], s0['b_committed_lower_kt']),
        'decarbonised: committed C1-C4 unchanged (held at 2025)': close(s1['c_committed_kt'], s0['c_committed_kt']),
        'decarbonised: committed B upper (2025 factors) unchanged': close(s1['b_committed_upper_kt'],
                                                                         s0['b_committed_upper_kt']),
        'decarbonised: whole life (A4-A5 held) - A4-A5 decarbonisation - maintenance decarbonisation = split (upper)':
            close(wl_a45_held - a45 - b_dec, sum1u),
        'inventory = instant - soil oxidised after 2050 + legacy':
            close(inv['within_window_kt'], s1['within_window_kt'] - inv['soil_after_2050_kt'] + inv['legacy_kt']),
    }
    out = dict(scenario='REF', whole_life_2025_factors_kt=wl_frozen, whole_life_a45_held_kt=wl_a45_held,
               whole_life_adopted_a45_resch_kt=wl_adopted, frozen_2025_factors=s0, adopted=s1,
               a45_construction_decarbonisation_kt=a45, b_inwindow_decarbonisation_kt=b_dec,
               sum_2025_factors_kt=sum0, sum_adopted_upper_kt=sum1u, sum_adopted_lower_kt=sum1l, inventory=inv,
               checks=checks)
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
         f"| committed C1-C4 (2025 factors) | {s0['c_committed_kt']:,.1f} | {s1['c_committed_kt']:,.1f} |",
         f"| sum, committed upper | {sum0:,.1f} | {sum1u:,.1f} |",
         f"| sum, committed lower | {sum0:,.1f} | {sum1l:,.1f} |",
         f"| whole life at construction (A4-A5 held) | {wl_frozen:,.1f} | {wl_a45_held:,.1f} |",
         f"| less A4-A5 decarbonisation of construction (Resch et al. 2021) | - | {-a45:,.1f} |",
         f"| less decarbonisation of maintenance within 2026-2050 | - | {-b_dec:,.1f} |",
         f"| = sum, committed upper | {wl_frozen:,.1f} | {wl_a45_held - a45 - b_dec:,.1f} |", '',
         '**Adopted accounting (ACCOUNTING inventory), decarbonised:**', '',
         '| term | kt CO2e |', '|---|---|',
         f"| carbon 2026-2050, instant (above) | {s1['within_window_kt']:,.1f} |",
         f"| less soil of 2026-2050 conversions oxidised after 2050 (committed 'Soil, after 2050') | "
         f"{-inv['soil_after_2050_kt']:,.1f} |",
         f"| plus legacy: soil tails of 2007-2025 conversions | {inv['legacy_soil_kt']:,.1f} |",
         f"| plus legacy: B2/B4 of the 1992-2025 cohorts | {inv['legacy_b2b4_kt']:,.1f} |",
         f"| **= carbon 2026-2050, inventory (reported total)** | **{inv['within_window_kt']:,.1f}** |", '',
         '| identity | holds (relative tolerance 1e-9) |', '|---|---|']
    L += [f'| {k} | {"yes" if v else "NO"} |' for k, v in checks.items()]
    with open(layout.writing(layout.report('reconciliation.md')), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    if not all(checks.values()):
        raise SystemExit('Reconciliation identity failed: ' + ', '.join(k for k, v in checks.items() if not v))


if __name__ == '__main__':
    main()
