"""
PATHWAY MONTE CARLO (MODEL v2.0.0): P5 Combined (Moderate) and TL under the joint input uncertainty
=================================================================================================
Every saved Monte Carlo draw of the Reference (outputs/data/montecarlo/draws_REF.csv, 5,000 Latin
hypercube draws of population rank, dwelling-size multiplier, completion rate and the case-study
carbon-factor bootstrap) is re-run through MonteCarlo.project (unchanged outputs; full=True exposes
the draw's engine inputs) and then through the pathway layer, for P5 Combined (Moderate, full
roll-out by 2035) and TL (P5 Moderate with TL1-TL7 at full strength from 2027):

  * the levers are applied identically to every draw: the same lever parameters (L1 share f, L2 v*,
    L3 absorption, L4 d, L5 ratio r and the adoption path), on the draw's own population, households,
    stock calibration, dwelling sizes and carbon factors;
  * TL3-TL6 are absolute targets, fixed across draws: the OLF of TL3 (19.69 m2 per person), the
    best-case A1-A3 per m2 of each typology of TL4 (r_draw = target / the draw's pooled A1-A3), the
    lowest-soil-order factors of TL5 and the 65% infill share of TL6; TL1, TL2 and TL7 are rules
    (v = 0 and the overbuild absorbed; size = occupied area; L4 at d = 0.40).

The draw's pooled A1-A3 and its A1-A3 reductions come from MonteCarlo.carbon_bootstrap re-run with the
same seed and resampling indices and A1-A3 as an extra resampled column (no new random numbers; the
draw factors are asserted identical to the saved setup). The level of exceedance of every draw uses
that draw's cumulative AR and AtP budgets (outputs/data/aesa/montecarlo_draw_budgets.csv, written by
boundaries.py from the same draws), so the Reference reproduces the AESA Monte Carlo.

Checks that stop the run: the central draw reproduces the deterministic P5 Moderate and TL runs to
1e-9 (annual carbon, floor area and dwellings built in every year with building, and their 2026-2050
totals; in TL's zero-building years both runs are zero by the model's own tolerances, the carbon there
being floating-point noise of order 1e-8 kg); every draw's Reference carbon equals the saved draw; the
bootstrap is reproduced exactly.

Writes outputs/data/pathways/montecarlo_draws.csv (per draw), montecarlo_summary.csv (percentiles,
P(LoE <= 1)) and montecarlo_annual.csv (annual carbon percentiles of the Reference, P5 and TL).

    python pathways_mc.py          (run_all.py runs it after pathways.py)
"""
import contextlib
import io
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import layout  # noqa: E402
import levers as LV  # noqa: E402
import MonteCarlo as MC  # noqa: E402
import naming as N  # noqa: E402
import pathways as PW  # noqa: E402
import validation  # noqa: E402

M6 = 1e6
PCT = (5, 25, 50, 75, 95)
CENTRAL_TOL = 1e-9
RUNS = ('REF', 'P5', 'TL')
WINDOW = slice(1, None)                          # 2026-2050 (index 0 = 2025)


def bootstrap_a13(su):
    """Pooled A1-A3 (kg/m2) and A1-A3 reductions (kg/m2 by year) of every bootstrap replicate, with the
    replicates of the saved setup (MonteCarlo.carbon_bootstrap, same seed and indices)."""
    projection = MC.projection
    typ, fy = su['typ'], su['fy']
    bf = pd.read_csv(projection.FILE_FACTORS_BUILDING)
    red13 = pd.DataFrame(0.0, index=bf['id'], columns=list(fy))
    B = su['B']
    if B['DECARB13'] is not None:
        variant = projection.BF.decarb_variant(projection.DECARB_MODE, projection.DECARB_ITEM_CASE)
        r = pd.read_csv(projection.FILE_FACTORS_DECARB_BLD)
        red13 = red13 + (r[r['Variant'] == variant]
                         .pivot(index='id', columns='Year', values='A13_reduction_kgCO2e_per_m2')
                         .reindex(index=bf['id'], columns=list(fy)))
    red = red13.copy()
    if projection.DECARB_A45 == 'resch':
        g = projection.BF.generic_path(fy)
        red = red + pd.DataFrame(np.outer(bf['A4-A5'].values, 1.0 - g), index=bf['id'], columns=list(fy))
    extras = dict(a13=pd.DataFrame({'a13': bf['A1-A3'].values}, index=bf['id']), red13=red13)
    emb, upf, _, dec, ext = MC.carbon_bootstrap(bf, typ, red if su['decarb'] else None, extras)
    if not (np.array_equal(emb, su['boot_emb']) and np.array_equal(upf, su['boot_up'])
            and (not su['decarb'] or np.array_equal(dec, su['boot_red']))):
        raise SystemExit('pathways_mc: the carbon-factor bootstrap is not reproduced (seed or data changed).')
    return ext['a13'][:, :, 0], ext['red13']


def draw_context(ctx, su, d, a13, red13):
    """The pathway context of one draw: the deterministic Reference context with the draw's inputs."""
    typ = su['typ']
    fi = dict(d['fwd_inputs'])
    ji = d['join_info']
    c = dict(ctx)
    c.update(pop=d['pop'], hh=d['hh'], growth=d['growth'], fwd_inputs=fi,
             size_ref={t: float(fi['size'][t]) for t in typ}, olf=dict(fi['olf']), v0=float(fi['v']),
             rate_demol=float(fi['rate_demol']), rate_unc=np.asarray(fi['rate_unc'], float),
             long_run_residual=float(d['unc_long']), join=d['join'], join_redev=ji['redev'], O26=float(ji['O26']),
             rho=float(d['rho']), E_nojoin=d['E_nojoin'], soil=dict(fi['soil']), events=fi['events'])
    if d['kc'] is not None:
        c.update(a13_2025={t: float(a13[d['kc'], j]) for j, t in enumerate(typ)},
                 red13={t: np.asarray(red13[d['kc'], j], float) for j, t in enumerate(typ)})
    return c


def tl_params_for_draw(pT, ctx_ref, ctx_d):
    """TL4 as an absolute target: the best-case A1-A3 per m2 of each typology is fixed, so the draw's ratio
    is that target over the draw's pooled A1-A3. TL3 (OLF), TL5 (soil factors) and TL6 are absolute already."""
    p = dict(pT)
    p['TL4'] = {t: dict(v, r=float(v['r']) * float(ctx_ref['a13_2025'][t]) / float(ctx_d['a13_2025'][t]))
                for t, v in pT['TL4'].items()}
    return p


def runs_for_draw(ctx_d, params, pT_d):
    p5 = PW.run(ctx_d, params, LV.pathway_levers('P5', 'moderate'))
    tl = PW.run_tl(ctx_d, params, pT_d, LV.TL_COMPONENTS_V2, LV.TL_FROM2027, LV.TL_BASE_SETTING_V2)
    return p5['E'], tl['E']


def deterministic():
    """The deterministic Reference context, lever parameters, TL parameters and the P5 Moderate and TL runs."""
    import Building_factors as BF
    B = PW.boss_state(PW.REFERENCE)
    ctx = PW.base_context(B, PW.REFERENCE, PW.boundaries())
    params = LV.resolve(B, PW.load_factors_building(), validation.projection)
    pT = LV.resolve_tl(BF.load_characteristics(), PW.load_factors_building(),
                       pd.read_csv(validation.projection.FILE_FACTORS_TYPOLOGY), B['OLF_USED'])
    p5, tl = runs_for_draw(ctx, params, pT)
    return ctx, params, pT, p5, tl


def check_central(su, ctx, params, pT, p5, tl):
    """STOP unless the central draw reproduces the deterministic P5 Moderate and TL runs to 1e-9."""
    o = MC.project(su, MC.central(su), full=True)
    cd = draw_context(ctx, su, o['draw'], None, None)
    e5, et = runs_for_draw(cd, params, tl_params_for_draw(pT, ctx, cd))
    worst = {}
    for name, (a, b) in (('P5', (e5, p5)), ('TL', (et, tl))):
        # years with building: relative difference of every quantity; zero-building years (TL banking rule,
        # floor area <= pathways.T_ZERO_TOL_M2 in the deterministic run): both runs must be zero by the model's
        # own definition (floor area and dwellings below its zero tolerances; carbon there is floating-point
        # noise of order 1e-8 kg and is compared through the 2026-2050 total); 2026-2050 totals relative.
        built = np.asarray(b['total'], float)[WINDOW] > PW.T_ZERO_TOL_M2
        zero = ~built
        if zero.any() and not ((np.asarray(a['total'], float)[WINDOW][zero] <= PW.T_ZERO_TOL_M2).all()
                               and (np.abs(np.asarray(a['dwell_in_scope'], float)[WINDOW][zero])
                                    <= PW.T_ZERO_TOL_DWELLINGS).all()):
            worst[f'{name} zero-building years'] = np.inf
        for k in ('carbon', 'total', 'dwell_in_scope'):
            x, y = np.asarray(a[k], float)[WINDOW], np.asarray(b[k], float)[WINDOW]
            worst[f'{name} {k}'] = float((np.abs(x - y)[built] / np.abs(y[built])).max())
            worst[f'{name} {k} 2026-2050'] = float(abs(x.sum() / y.sum() - 1.0))
    w = max(worst.values())
    print(f'[check] pathway MC central draw vs the deterministic P5 Moderate and TL runs: max relative difference '
          f'{w:.1e} ({"OK" if w < CENTRAL_TOL else "FAIL"})')
    if w >= CENTRAL_TOL:
        raise SystemExit(f'STOP: the pathway Monte Carlo central draw does not reproduce the deterministic runs {worst}.')
    return worst


def main():
    t0 = time.time()
    ctx, params, pT, p5_det, tl_det = deterministic()
    name, settings = MC.MC_SCENARIOS[0]
    if name != 'REF':
        raise SystemExit('pathways_mc: the first Monte Carlo scenario must be the Reference.')
    with contextlib.redirect_stdout(io.StringIO()):
        su = MC.build_setup(settings)
    central = check_central(su, ctx, params, pT, p5_det, tl_det)
    a13, red13 = bootstrap_a13(su)
    draws = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
    X = draws[[N.identifier(c) for c in MC.PARAMS]].to_numpy(float)
    budgets = pd.read_csv(layout.data('aesa/montecarlo_draw_budgets.csv', frozen=False))
    if len(budgets) != len(draws):
        raise SystemExit('pathways_mc: the AESA draw budgets do not match the saved draws (re-run boundaries.py).')
    years = np.asarray(ctx['years'])
    n = len(draws)
    annual = {r: np.empty((n, len(years))) for r in RUNS}
    rows = []
    for j in range(n):
        o = MC.project(su, dict(zip(MC.PARAMS, X[j])), full=True)
        cd = draw_context(ctx, su, o['draw'], a13, red13)
        e5, et = runs_for_draw(cd, params, tl_params_for_draw(pT, ctx, cd))
        b = budgets.iloc[j]
        c_ref = float(o['carbon'][WINDOW].sum()) / M6
        if abs(c_ref / b['carbon_kt_2026_2050'] - 1) > 1e-9:
            raise SystemExit(f'pathways_mc: draw {j}: the Reference carbon differs from the AESA Monte Carlo.')
        row = dict(draw=j, **{N.identifier(k): float(X[j, i]) for i, k in enumerate(MC.PARAMS)},
                   B_AR_kt_2026_2050=float(b['B_AR_kt_2026_2050']), B_AtP_kt_2026_2050=float(b['B_AtP_kt_2026_2050']))
        for r, E in (('REF', o), ('P5', e5), ('TL', et)):
            carbon = np.asarray(E['carbon'], float)
            annual[r][j] = carbon
            c = float(carbon[WINDOW].sum()) / M6
            row.update({f'{r}_carbon_kt': c, f'{r}_floor_area_Mm2': float(np.asarray(E['gfa'] if r == 'REF'
                                                                                    else E['total'])[WINDOW].sum()) / M6,
                        f'{r}_LoE_AR': c / row['B_AR_kt_2026_2050'], f'{r}_LoE_AtP': c / row['B_AtP_kt_2026_2050']})
        rows.append(row)
        if (j + 1) % 1000 == 0:
            print(f'  {j + 1:,} draws ({time.time() - t0:.0f} s)')
    df = pd.DataFrame(rows)
    summ = []
    for r in RUNS:
        for q in ('carbon_kt', 'floor_area_Mm2', 'LoE_AR', 'LoE_AtP'):
            v = df[f'{r}_{q}'].to_numpy()
            e = dict(run=r, quantity=q, mean=float(v.mean()), **{f'p{p}': float(np.percentile(v, p)) for p in PCT})
            if q.startswith('LoE'):
                e['probability_LoE_at_most_1'] = float(np.mean(v <= 1.0))
            summ.append(e)
    ann = []
    for r in RUNS:
        for i, y in enumerate(years):
            if y < 2026:
                continue
            ann.append(dict(run=r, year=int(y), **{f'carbon_kt_p{p}': float(np.percentile(annual[r][:, i], p) / M6)
                                                   for p in PCT},
                            carbon_kt_mean=float(annual[r][:, i].mean() / M6)))
    N.columns(df).to_csv(layout.writing(layout.data('pathways/montecarlo_draws.csv', frozen=False)), index=False)
    summary = pd.DataFrame(summ)
    summary['central_draw_max_rel_diff'] = max(central.values())
    N.columns(summary).to_csv(layout.writing(layout.data('pathways/montecarlo_summary.csv', frozen=False)), index=False)
    N.columns(pd.DataFrame(ann)).to_csv(layout.writing(layout.data('pathways/montecarlo_annual.csv', frozen=False)),
                                        index=False)
    print(summary[['run', 'quantity', 'p5', 'p50', 'p95', 'probability_LoE_at_most_1']].to_string(index=False))
    print(f'pathways_mc: {n:,} draws in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
