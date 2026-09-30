# Engine equivalence proof at CP2: current code with tests/legacy_flags.py vs frozen original (200 Boss draws)

Unified engine vs frozen pre-unification code (tests/legacy/). Tolerance 1e-09 x the largest absolute value of each series.

## MonteCarlo.project, default mode: 301 draws, largest relative difference 7.16e-15

| output | largest relative difference |
|---|---|
| S | 0.00e+00 |
| carbon | 7.16e-15 |
| gfa | 5.29e-15 |
| hh | 0.00e+00 |
| rv_units | 3.50e-16 |
| upfront | 5.98e-15 |

Draws in which the extra-space floor binds in at least one year (new = legacy + that term, verified above): 1.

## MonteCarlo.project, 2025 deviation carried (b, rho sampled): 101 draws, largest relative difference 5.52e-15

| output | largest relative difference |
|---|---|
| S | 0.00e+00 |
| carbon | 5.52e-15 |
| gfa | 4.64e-15 |
| hh | 0.00e+00 |
| rv_units | 3.47e-16 |
| upfront | 4.84e-15 |

Draws in which the extra-space floor binds in at least one year (new = legacy + that term, verified above): 0.

## Boss.main, random settings: 200 draws, largest relative difference 0.00e+00

| output | largest relative difference |
|---|---|
| carbon_total_typ | 0.00e+00 |
| dem_mat | 0.00e+00 |
| df_forecast | 0.00e+00 |
| evol_typ_growth | 0.00e+00 |
| evol_typ_repl | 0.00e+00 |
| evol_typ_rv | 0.00e+00 |
| evol_typ_total | 0.00e+00 |
| evol_typ_unc | 0.00e+00 |
| evol_typ_vac | 0.00e+00 |
| evolving_gfa_shares | 0.00e+00 |
| flow_annual | 0.00e+00 |
| households | 0.00e+00 |
| other_dev_2025 | 0.00e+00 |
| results.c_gross | 0.00e+00 |
| results.d_hh | 0.00e+00 |
| results.extra | 0.00e+00 |
| results.growth | 0.00e+00 |
| results.growth_gross | 0.00e+00 |
| results.hs_avoided | 0.00e+00 |
| results.hs_pos | 0.00e+00 |
| results.occ_per_dw | 0.00e+00 |
| results.other | 0.00e+00 |
| results.repl | 0.00e+00 |
| results.rv | 0.00e+00 |
| results.structural | 0.00e+00 |
| results.total | 0.00e+00 |
| results.unc | 0.00e+00 |
| results.vac | 0.00e+00 |
| rho_other | 0.00e+00 |
| stock_fwd.allow | 0.00e+00 |
| stock_fwd.demol | 0.00e+00 |
| stock_fwd.repl | 0.00e+00 |
| stock_fwd.rv | 0.00e+00 |
| stock_fwd.stock | 0.00e+00 |
| stock_fwd.uncons | 0.00e+00 |
| tot_carbon_median | 0.00e+00 |
| unconsented_rate | 0.00e+00 |
| v_forward | 0.00e+00 |

Consumption bases drawn: {'stock_vacancy': 136, 'extra_space_plus_other': 19, 'per_capita': 21, 'per_household': 24}.
