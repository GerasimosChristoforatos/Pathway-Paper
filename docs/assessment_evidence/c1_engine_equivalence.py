"""C1: does MonteCarlo.project() agree with Boss.main() away from the central point?

Only settings that BOTH engines can express are compared. All MC evaluations
are done BEFORE any Boss re-run: MonteCarlo.project() calls Boss's
calibrate_stock closure, which reads Boss module globals at call time, so a
preceding Boss run with a changed setting would leak into the MC result.
"""
import contextlib
import io

from common import np, run
import MonteCarlo as MC

with contextlib.redirect_stdout(io.StringIO()):
    su = MC.build_setup()
cen = MC.central(su)
k_occ = su['k_range'][0]


def mc(**kw):
    p = dict(cen)
    p.update(kw)
    o = MC.project(su, p)
    return o['gfa'][1:].sum() / 1e6, o['carbon'][1:].sum() / 1e6, o['S'][-1]


def boss(pct='50th', **kw):
    B = run(**kw)
    R = B['results'][pct]['total']
    mix = sum(B['evolving_gfa_shares'][t].values * B['T_BASELINE_2025'][t] for t in B['typ_names'])
    S = B['df_forecast'][f'PopTotal_{pct}'].values / B['households_forecast'][pct]
    return R[1:].sum() / 1e6, float((R[1:] * mix[1:]).sum()) / 1e6, S[-1]


specs = [
    ('central', {}, ('50th', {})),
    ('complete 0.92 | COMPLETION_RATE 0.92', dict(complete=0.92), ('50th', dict(COMPLETION_RATE=0.92))),
    ('complete 0.96 | COMPLETION_RATE 0.96', dict(complete=0.96), ('50th', dict(COMPLETION_RATE=0.96))),
    ('phi 0.5 | DAMPING_PHI 0.5', dict(phi=0.5), ('50th', dict(DAMPING_PHI=0.5))),
    ('phi 0.95 | DAMPING_PHI 0.95', dict(phi=0.95), ('50th', dict(DAMPING_PHI=0.95))),
    ('k(occupied) | HH_CENSUS_REBASE occupied', dict(hh_rebase=k_occ), ('50th', dict(HH_CENSUS_REBASE='occupied'))),
    ('z -1.645 | 5th pct + Low S variant', dict(z_pop=MC.Z_KNOTS[0]), ('5th', dict(HH_SIZE_VARIANT='Low'))),
    ('z +1.645 | 95th pct + High S variant', dict(z_pop=MC.Z_KNOTS[-1]), ('95th', dict(HH_SIZE_VARIANT='High'))),
    ('regime 1 | DEMOLITION_CALIB_START 2019', dict(regime=1.0), ('50th', dict(DEMOLITION_CALIB_START=2019))),
    ('k 1.0 | HH_CENSUS_REBASE None', dict(hh_rebase=1.0), ('50th', dict(HH_CENSUS_REBASE=None))),
]
mc_vals = [mc(**m) for _, m, _ in specs]          # before any Boss re-run
print(f"{'MC setting | Boss setting':<44}{'MC GFA':>8}{'Boss':>8}{'diff':>9}{'MC kt':>9}{'Boss kt':>9}{'S2050 MC/Boss':>15}")
for (lab, _, (pct, kw)), m in zip(specs, mc_vals):
    b = boss(pct, **kw)
    print(f"{lab:<44}{m[0]:>8.2f}{b[0]:>8.2f}{100 * (m[0] / b[0] - 1):>+8.2f}%{m[1]:>9,.0f}{b[1]:>9,.0f}"
          f"{m[2]:>8.3f}/{b[2]:.3f}")

B = run()
B19 = run(DEMOLITION_CALIB_START=2019)
print(f"\nrho_other: Boss 1992-2023 window {B['rho_other']:.3f}; Boss 2019-2023 window (n=5) {B19['rho_other']:.3f}; "
      f"MC always uses the 1992-2023 window")
print(f"other_dev_2025: adopted {B['other_dev_2025']:+,.0f}; DEMOLITION_CALIB_START=2019 {B19['other_dev_2025']:+,.0f}")
occ = B['results']['50th']['occ_per_dw']
D = B['future_dwelling_size'].values
print(f"MC assumes total = dwellings x D; this requires D >= occupied area. Min margin on the median path "
      f"{float((D - occ)[1:].min()):.1f} m2 (occupied/D <= {float((occ / D)[1:].max()):.2f}); "
      f"a size multiplier below {float((occ / D)[1:].max()):.2f} would break it")
print("\nMC inputs with NO Boss counterpart: vacancy drift to a 2050 target, dwelling-size multiplier, "
      "ALR slope offsets, z between knots (variant interpolation), pre_share and rv_share as free inputs, carbon bootstrap")
