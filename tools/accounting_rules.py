"""The three emissions accounting rules side by side (MODEL v3.1.0, A1; inventory.py), deterministic, Reference
replacement variant, median demographics:

  * the AR base 2016-2025 (kt/yr) split into upfront A1-A5, soil and maintenance (B2, B4), and the cumulative AR
    and AtP budgets 2026-2050 (kt; AtP does not depend on the base);
  * the Reference carbon 2026-2050 split into upfront A1-A5 of the new cohorts, their soil (emitted in the window),
    their maintenance (B2, B4) and the legacy (pre-2026 activity); the soil of 2026-2050 conversions oxidised after
    2050 (committed, 'Soil, after 2050');
  * the cumulative LoE AR and AtP of the Reference, P5 Moderate, P5 Ambitious and TL;
  * the Monte Carlo share of draws with TL within AR, for the adopted rule and the instant rule (pathways_mc.py;
    'cohort_window' is deterministic only).

Every rule runs the same model (projection.main with ACCOUNTING set; boundaries.window_base on the same rule; the
pathway runs of pathways.run); nothing else changes. Writes outputs/data/sensitivity/accounting_rules.csv.

    python tools/accounting_rules.py
"""
import contextlib
import io
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import boundaries as BD  # noqa: E402
import inventory as INV  # noqa: E402
import layout  # noqa: E402
import levers as LV  # noqa: E402
import naming as N  # noqa: E402
import pathways as PW  # noqa: E402
import validation  # noqa: E402

M6 = 1e6
OUT = layout.data('sensitivity/accounting_rules.csv', frozen=False)


def budgets(B, i_base):
    """B_AR, B_AtP (kg by year, 2026-2050) and P_NZ for a base, with the AESA components of boundaries.py."""
    res = json.load(open(layout.data('aesa/results.json', frozen=False)))
    c = res['components']
    fy = np.asarray(B['forecast_years'])
    years_b = list(range(BD.T0, BD.PB_YEARS[1] + 1))
    p_w = BD.world_population(years_b)
    p_nz = pd.Series(B['df_forecast']['PopTotal_50th'].values, index=fy).loc[BD.T0:]
    comp = dict(g_W=c['g_W'], g_NZ=c['g_NZ'], alpha=c['alpha'])
    b_ar, b_atp = BD.boundaries(BD.SOURCE_PAIR, i_base, comp, c['s_sec'], p_nz, p_w)
    w = slice(*BD.PB_YEARS)
    return b_ar.loc[w].values, b_atp.loc[w].values, p_nz.loc[w].values


def rule_row(rule):
    with contextlib.redirect_stdout(io.StringIO()):
        B = validation.run_boss(ACCOUNTING=rule)
    i_base, hist = BD.window_base(B, BD.AR_BASE_WINDOW, rule=rule)
    split = BD.base_split(hist, BD.AR_BASE_WINDOW)
    b_ar, b_atp, p_nz = budgets(B, i_base)
    E = B['engine_out']['50th']
    f = slice(1, None)
    soil = float(np.sum(E['soil'][f]))
    b = float(np.sum(E['b_t'][:, f]))
    up = float(np.sum(E['upfront'][f])) - soil
    row = dict(accounting=rule, adopted=(rule == validation.projection.ACCOUNTING),
               AR_base_kt_per_yr=split['total_kg'] / M6, AR_base_upfront_kt_per_yr=split['upfront_kg'] / M6,
               AR_base_soil_kt_per_yr=split['soil_kg'] / M6, AR_base_b2b4_kt_per_yr=split['b2b4_kg'] / M6,
               AR_budget_kt_2026_2050=float(b_ar.sum()) / M6, AtP_budget_kt_2026_2050=float(b_atp.sum()) / M6,
               reference_carbon_kt=float(B['tot_carbon_median']), reference_upfront_kt=up / M6,
               reference_soil_kt=soil / M6, reference_b2b4_kt=b / M6,
               reference_legacy_kt=float(B['carbon_legacy'].iloc[f].sum().sum()) / M6,
               reference_legacy_soil_kt=float(B['carbon_legacy']['soil'].iloc[f].sum()) / M6,
               reference_legacy_b2b4_kt=float(B['carbon_legacy']['b'].iloc[f].sum()) / M6,
               soil_after_2050_kt=float(B['soil_after_2050']) / M6,
               soil_tail_coverage_base=('n/a' if rule == 'instant' else
                                        'full' if INV.tail_coverage(BD.AR_BASE_WINDOW)['covered'] else 'partial'))
    ctx = PW.base_context(B, PW.REFERENCE, (b_ar, b_atp, p_nz))
    params = PW.resolve_params(B)
    runs = {'REF': {}, 'P5_moderate': LV.pathway_levers('P5', 'moderate'),
            'P5_ambitious': LV.pathway_levers('P5', 'ambitious'), 'TL': LV.tl_levels(LV.TL_COMPONENTS)}
    for lab, lv in runs.items():
        q = PW.quick(ctx, PW.run(ctx, params, lv))
        row.update({f'{lab}_carbon_kt': q['carbon_kt'], f'{lab}_LoE_AR': q['LoE_AR'], f'{lab}_LoE_AtP': q['LoE_AtP']})
    if not np.isclose(row['REF_carbon_kt'], row['reference_carbon_kt'], rtol=1e-9):
        raise SystemExit(f'accounting_rules {rule}: the pathway Reference differs from the projection.')
    return row


def main():
    rows = [rule_row(r) for r in INV.RULES]
    dr = json.load(open(layout.data('pathways/montecarlo_draw_rules.json', frozen=False)))
    adopted = dr.get('accounting')
    for r in rows:
        r['MC_share_TL_within_AR'] = (dr['probability_TL_LoE_AR_at_most_1'] if r['accounting'] == adopted else
                                      dr['probability_TL_LoE_AR_at_most_1_instant_rule']
                                      if r['accounting'] == 'instant' else None)
    df = pd.DataFrame(rows)
    N.columns(df).to_csv(layout.writing(OUT), index=False)
    cols = ['accounting', 'AR_base_kt_per_yr', 'AR_budget_kt_2026_2050', 'reference_carbon_kt', 'reference_legacy_kt',
            'soil_after_2050_kt', 'REF_LoE_AR', 'P5_moderate_LoE_AR', 'P5_ambitious_LoE_AR', 'TL_LoE_AR',
            'MC_share_TL_within_AR']
    print(df[cols].to_string(index=False))
    print(f'accounting_rules: {OUT}')


if __name__ == '__main__':
    main()
