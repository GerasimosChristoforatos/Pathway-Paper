"""
PATHWAY MONTE CARLO (MODEL v2.1.0): P5 Combined (Moderate) and TL under the joint input uncertainty
=================================================================================================
Every saved Monte Carlo draw of the Reference (outputs/data/montecarlo/draws_REF.csv, 5,000 Latin
hypercube draws of population rank, dwelling-size multiplier, completion rate and the case-study
carbon-factor bootstrap) is re-run through MonteCarlo.project (unchanged outputs; full=True exposes
the draw's engine inputs) and then through the pathway layer, for P5 Combined (Moderate, full
roll-out by 2035) and TL (P5 Moderate with TL1-TL10 at full strength from 2027; released dwellings brought back
into use in proportion to each year's need, 2027-2050).
Population and household size share one draw: the household-size path is interpolated between the
Stats NZ Low, Medium and High variants at the draw's population rank (MonteCarlo.project).

  * the levers are applied identically to every draw: the same lever parameters (L1 share f, L2 target
    household-size path, L3 v*, L4 absorption, L5 d, L6 ratio r, L7 A4-A5 target path, L8 x, L9 share s and
    the adoption path), on the draw's own population, households, stock calibration, dwelling sizes and
    carbon factors (L6 and L7 act on the draw's own A1-A3 and A4-A5). The L2 target is a fixed household-size
    path; its floor (levers.l2_households: the lever never adds households) binds only in draws whose own
    household size is above the target (population ranks beyond the High variant's); counted and reported;
  * the TL targets are fixed absolute values across draws: TL2 S = the historical maximum, TL3 v = 0, TL7
    A4-A5 = 0, TL8 the lowest-soil-order factors, TL9 s = 0.89, TL10 the OLF of 19.69 m2 per person, and TL6 the
    A1-A3 per m2 of each typology at r_TL x the deterministic pooled A1-A3 (r_draw = that target / the draw's
    pooled A1-A3, capped at the Ambitious ratio so that TL6 is never weaker than Ambitious L6 in any draw; the
    cap binds in the draws with a pooled A1-A3 below the target; counted and reported); TL1, TL4 and TL5 are
    rules (f = 1; the overbuild absorbed in 2027; the surge removed and demolition -40%).

The draw's pooled A1-A3, A1-A3 reductions and A4-A5 come from MonteCarlo.carbon_bootstrap re-run with the
same seed and resampling indices and A1-A3 and A4-A5 as extra resampled columns (no new random numbers; the
draw factors are asserted identical to the saved setup). The level of exceedance of every draw uses that
draw's cumulative AR and AtP budgets (outputs/data/aesa/montecarlo_draw_budgets.csv, written by boundaries.py
from the same draws), so the Reference reproduces the AESA Monte Carlo.

Insight analyses (mcstats.py; numpy / scipy, cross-checked against statsmodels in tests/test_mcstats.py) on
the four sampled inputs: population rank (the z-score of the draw), dwelling-size multiplier, completion rate,
and the carbon-factor index. The carbon input of the Latin hypercube is a uniform selector of a bootstrap
replicate, whose order carries no meaning, so the analyses use instead the draw's carbon-factor index: the
draw's carbon per m2 of new floor area (all in-scope stages and soil, by typology and year) weighted by the
central run's floor area by typology and year 2026-2050, over the same weighted mean at the central factors.
  * SRC (standardised regression coefficients, with R^2) and PRCC (partial rank correlation coefficients) of
    floor area, carbon and the cumulative LoE AR 2026-2050 of the Reference, P5 and TL, with percentile
    bootstrap 95% intervals (1,000 resamples of the draws) -> montecarlo_importance.csv;
  * LOWESS curves (frac 2/3, 3 robustness iterations) and least-squares lines of every input-output pair
    -> montecarlo_fits.csv;
  * conditional TL: logistic regression of 1[TL LoE AR <= 1] on the standardised inputs, univariable and
    multivariable, by Firth's penalised likelihood with profile-likelihood 95% intervals (the outcome is rare and,
    the simulator being deterministic, separable, so the maximum-likelihood estimate may not exist; reported with
    the events per variable), P(TL LoE AR <= 1) by population-rank quintile (Wilson intervals) and the exceeding
    draws -> montecarlo_conditional_tl.csv and montecarlo_conditional_tl.json.

Checks that stop the run: the central draw reproduces the deterministic P5 Moderate and TL runs to
1e-9 (annual carbon, floor area and dwellings built in every year with building, and their 2026-2050
totals; zero-building years, none under the proportional reoccupation of MODEL v2.1.1, would be compared
by the model's own zero tolerances, kept as a guard); every draw's Reference carbon equals the saved draw; the
bootstrap is reproduced exactly; TL2 and TL6 never weaker than their Ambitious levers in any draw.

Writes outputs/data/pathways/montecarlo_draws.csv (per draw), montecarlo_summary.csv (percentiles,
P(LoE <= 1)), montecarlo_annual.csv (annual carbon percentiles of the Reference, P5 and TL) and the insight
files above.

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
import mcstats  # noqa: E402
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


def bootstrap_factors(su):
    """Pooled A1-A3 (kg/m2), A1-A3 reductions (kg/m2 by year) and A4-A5 (kg/m2) of every bootstrap replicate,
    with the replicates of the saved setup (MonteCarlo.carbon_bootstrap, same seed and indices)."""
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
    extras = dict(a13=pd.DataFrame({'a13': bf['A1-A3'].values}, index=bf['id']),
                  a45=pd.DataFrame({'a45': bf['A4-A5'].values}, index=bf['id']), red13=red13)
    emb, upf, _, dec, ext = MC.carbon_bootstrap(bf, typ, red if su['decarb'] else None, extras)
    if not (np.array_equal(emb, su['boot_emb']) and np.array_equal(upf, su['boot_up'])
            and (not su['decarb'] or np.array_equal(dec, su['boot_red']))):
        raise SystemExit('pathways_mc: the carbon-factor bootstrap is not reproduced (seed or data changed).')
    return ext['a13'][:, :, 0], ext['red13'], ext['a45'][:, :, 0]


def draw_context(ctx, su, d, a13, red13, a45):
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
                 red13={t: np.asarray(red13[d['kc'], j], float) for j, t in enumerate(typ)},
                 a45_2025={t: float(a45[d['kc'], j]) for j, t in enumerate(typ)})
    return c


def tl_params_for_draw(pT, params, ctx_ref, ctx_d):
    """TL6 as an absolute target: A1-A3 per m2 of each typology = r_TL x the deterministic pooled A1-A3, so the
    draw's ratio is that target over the draw's pooled A1-A3, capped at the Ambitious ratio (TL6 never weaker
    than Ambitious L6). Every other TL item is an absolute value or a rule already. Returns (params, capped
    typologies)."""
    r_amb = float(params['L6']['estimator']['ambitious']['r'])
    p = dict(pT)
    p['TL6'] = {}
    capped = []
    for t, v in pT['TL6'].items():
        r_abs = float(v['r']) * float(ctx_ref['a13_2025'][t]) / float(ctx_d['a13_2025'][t])
        if r_abs > r_amb:
            capped.append(t)
        p['TL6'][t] = dict(v, r=min(r_abs, r_amb))
    return p, capped


def runs_for_draw(ctx_d, params, pT_d):
    p5 = PW.run(ctx_d, params, LV.pathway_levers('P5', 'moderate'))
    tl = PW.run_tl(ctx_d, params, pT_d, LV.TL_COMPONENTS)
    return p5, tl


def deterministic():
    """The deterministic Reference context, lever parameters, TL parameters and the P5 Moderate and TL runs."""
    import Building_factors as BF
    B = PW.boss_state(PW.REFERENCE)
    ctx = PW.base_context(B, PW.REFERENCE, PW.boundaries())
    params = LV.resolve(B, PW.load_factors_building(), validation.projection, PW.household_size_variants(B))
    pT = LV.resolve_tl(BF.load_characteristics(), PW.load_factors_building(),
                       pd.read_csv(validation.projection.FILE_FACTORS_TYPOLOGY), B['OLF_USED'], B['hist_S'], params)
    p5, tl = runs_for_draw(ctx, params, pT)
    return ctx, params, pT, p5['E'], tl['E']


def check_central(su, ctx, params, pT, p5, tl):
    """STOP unless the central draw reproduces the deterministic P5 Moderate and TL runs to 1e-9."""
    o = MC.project(su, MC.central(su), full=True)
    cd = draw_context(ctx, su, o['draw'], None, None, None)
    r5, rt = runs_for_draw(cd, params, tl_params_for_draw(pT, params, ctx, cd)[0])
    e5, et = r5['E'], rt['E']
    worst = {}
    for name, (a, b) in (('P5', (e5, p5)), ('TL', (et, tl))):
        # years with building: relative difference of every quantity; zero-building years (none under proportional
        # reoccupation; kept as a guard: floor area <= pathways.T_ZERO_TOL_M2 in the deterministic run): both zero by the model's
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


INPUTS = ('z_pop', 'size', 'complete', 'carbon_index')
INPUT_LABELS = {'z_pop': 'Population rank (z-score)', 'size': 'Dwelling-size multiplier',
                'complete': 'Completion rate', 'carbon_index': 'Carbon-factor index'}
OUTPUTS = ('floor_area_Mm2', 'carbon_kt', 'LoE_AR')
BOOT_B = 1000
BOOT_SEED = MC.SEED + 2101                      # the insight bootstrap's own stream (the draws are not touched)
LOWESS_FRAC, LOWESS_IT, LOWESS_POINTS = 2.0 / 3.0, 3, 101


def carbon_index(o, I_c, gfa_c):
    """The draw's carbon-factor index: carbon per m2 of new floor area at the draw's factors over the same at the
    central factors, both weighted by the central run's floor area by typology and year 2026-2050."""
    I = np.broadcast_to(np.asarray(o['I'], float).reshape(len(I_c), -1), gfa_c.shape)
    return float(np.sum((gfa_c * I)[:, WINDOW]) / np.sum((gfa_c * I_c)[:, WINDOW]))


def insights(df):
    """SRC / PRCC with bootstrap intervals, LOWESS and least-squares fits, and the conditional-TL logistic
    regression (mcstats.py). Returns (importance, fits, conditional rows, conditional summary)."""
    X = df[[N.identifier(c) if c != 'carbon_index' else c for c in INPUTS]].to_numpy(float)
    imp, fits = [], []
    for r in RUNS:
        for q in OUTPUTS:
            y = df[f'{r}_{q}'].to_numpy(float)
            beta, r2 = mcstats.src(X, y)
            e_s, lo_s, hi_s = mcstats.bootstrap(lambda a, b: mcstats.src(a, b)[0], X, y, BOOT_B, BOOT_SEED)
            e_p, lo_p, hi_p = mcstats.bootstrap(mcstats.prcc, X, y, BOOT_B, BOOT_SEED)
            for i, c in enumerate(INPUTS):
                imp.append(dict(run=r, output=q, input=c, src=float(e_s[i]), src_lo=float(lo_s[i]), src_hi=float(hi_s[i]),
                                src_r2=float(r2), prcc=float(e_p[i]), prcc_lo=float(lo_p[i]), prcc_hi=float(hi_p[i]),
                                bootstrap_resamples=BOOT_B))
            for i, c in enumerate(INPUTS):
                x = X[:, i]
                grid = np.linspace(x.min(), x.max(), LOWESS_POINTS)
                _, curve = mcstats.lowess(x, y, LOWESS_FRAC, LOWESS_IT, grid)
                slope, icpt = np.polyfit(x, y, 1)
                for g, v in zip(grid, curve):
                    fits.append(dict(run=r, output=q, input=c, x=float(g), lowess=float(v),
                                     ols=float(icpt + slope * g)))
    # conditional TL: P(TL LoE AR <= 1 | inputs). The simulator is deterministic, so given all four inputs the
    # outcome is fixed and the outcome is rare (few exceedances); the maximum-likelihood logistic estimate may not
    # exist (separation). Firth's penalised likelihood (mcstats.firth) is used for every model, univariable (each
    # input alone: a genuine probability model, the other inputs being random) and multivariable; whether the
    # maximum-likelihood estimate exists and the events per variable are reported with it.
    yy = (df['TL_LoE_AR'].to_numpy(float) <= 1.0).astype(float)
    mu, sd = X.mean(axis=0), X.std(axis=0, ddof=1)
    Z = (X - mu) / sd
    events = int(min(yy.sum(), len(yy) - yy.sum()))           # the rarer outcome class
    cond = []

    def add_model(model, cols):
        try:
            mcstats.logistic(Z[:, cols], yy)
            mle, why = True, ''
        except mcstats.Separation as e:
            mle, why = False, str(e).replace('logistic: ', '')
        fr = mcstats.firth(Z[:, cols], yy)
        for i, c in enumerate(['intercept'] + [INPUTS[k] for k in cols]):
            cond.append(dict(model=model, term=c, beta=float(fr['beta'][i]), se_wald=float(fr['se'][i]),
                             ci_lo=float(fr['ci_lo'][i]), ci_hi=float(fr['ci_hi'][i]),
                             odds_ratio_per_sd=float(fr['odds_ratio'][i]), or_lo=float(fr['or_lo'][i]),
                             or_hi=float(fr['or_hi'][i]), interval=fr['interval'],
                             input_mean=None if i == 0 else float(mu[cols[i - 1]]),
                             input_sd=None if i == 0 else float(sd[cols[i - 1]]),
                             mle_exists=mle, mle_note=why, events_rarer_class=events, events_per_variable=events / len(cols),
                             mcfadden_r2=float(fr['mcfadden_r2'])))
        return fr

    for k, c in enumerate(INPUTS):
        add_model(f'univariable: {c}', [k])
    fr_all = add_model('multivariable', list(range(len(INPUTS))))
    eta = np.column_stack([np.ones(len(yy)), Z]) @ fr_all['beta']
    z = df[N.identifier('z_pop')].to_numpy(float)
    edges = np.quantile(z, np.linspace(0, 1, 6))
    quint = []
    for k in range(5):
        sel = (z >= edges[k]) & ((z <= edges[k + 1]) if k == 4 else (z < edges[k + 1]))
        kk, nn = int(yy[sel].sum()), int(sel.sum())
        lo_, hi_ = mcstats.wilson(kk, nn)
        quint.append(dict(quintile=k + 1, z_lo=float(edges[k]), z_hi=float(edges[k + 1]), n=nn, within_AR=kk,
                          p_within_AR=kk / nn, wilson_lo=lo_, wilson_hi=hi_))
    ranks = {c: pd.Series(X[:, i]).rank(pct=True).to_numpy() for i, c in enumerate(INPUTS)}
    exceed = [dict(draw=int(df['draw'].iloc[j]), TL_LoE_AR=float(df['TL_LoE_AR'].iloc[j]),
                   **{c: float(X[j, i]) for i, c in enumerate(INPUTS)},
                   **{f'{c}_percentile_rank': float(ranks[c][j]) for c in INPUTS})
              for j in np.flatnonzero(yy == 0.0)]
    k_all, n_all = int(yy.sum()), len(yy)
    summary = dict(outcome='TL cumulative LoE AR 2026-2050 <= 1', n=n_all, within_AR=k_all,
                   p_within_AR=k_all / n_all, wilson_95=list(mcstats.wilson(k_all, n_all)),
                   events_rarer_class=events, events_per_variable_multivariable=events / len(INPUTS),
                   auc_multivariable_firth=mcstats.auc(eta, yy.astype(bool)) if 0 < k_all < n_all else None,
                   by_population_quintile=quint, exceeding_draws=exceed, inputs_standardised=True,
                   method='Firth (1993) penalised-likelihood logistic regression with profile penalised-likelihood '
                          '95% intervals (Heinze & Schemper 2002), odds ratio per standard deviation of each input; '
                          'univariable models (one input; the others random) and the multivariable model; whether the '
                          'maximum-likelihood estimate exists is reported. Proportions: Wilson score intervals.',
                   caveat='the pathway model is deterministic: given all four inputs the outcome is fixed, and the '
                          'intervals describe the 5,000-draw design, not a sampling process; with fewer than 10 '
                          'events per variable (Peduzzi et al. 1996, J Clin Epidemiol 49, 1373) the multivariable '
                          'odds ratios are indicative only')
    return pd.DataFrame(imp), pd.DataFrame(fits), pd.DataFrame(cond), summary


def main():
    t0 = time.time()
    ctx, params, pT, p5_det, tl_det = deterministic()
    name, settings = MC.MC_SCENARIOS[0]
    if name != 'REF':
        raise SystemExit('pathways_mc: the first Monte Carlo scenario must be the Reference.')
    with contextlib.redirect_stdout(io.StringIO()):
        su = MC.build_setup(settings)
    central = check_central(su, ctx, params, pT, p5_det, tl_det)
    a13, red13, a45 = bootstrap_factors(su)
    oc = MC.project(su, MC.central(su), full=True)
    gfa_c = np.asarray(oc['gfa_t'], float)
    I_c = np.broadcast_to(np.asarray(oc['I'], float).reshape(len(su['typ']), -1), gfa_c.shape)
    # the L2 target against the Monte Carlo household-size variants (same Stats NZ shape, census-rebased)
    S_high_mc = np.asarray(su['S_variants'][list(MC.VARIANT_Z).index(LV.L2_MODERATE_VARIANT)], float)
    S_mod = np.asarray(params['L2']['S_target']['moderate'], float)
    l2_vs_mc = float(np.max(np.abs(S_high_mc - S_mod)))
    draws = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
    X = draws[[N.identifier(c) for c in MC.PARAMS]].to_numpy(float)
    budgets = pd.read_csv(layout.data('aesa/montecarlo_draw_budgets.csv', frozen=False))
    if len(budgets) != len(draws):
        raise SystemExit('pathways_mc: the AESA draw budgets do not match the saved draws (re-run boundaries.py).')
    years = np.asarray(ctx['years'])
    late = years >= LV.OBSERVED_YEAR + 1                     # 2027-2050: where the levers act
    S_tl = float(pT['TL2']['S'])
    r_amb = float(params['L6']['estimator']['ambitious']['r'])
    n = len(draws)
    annual = {r: np.empty((n, len(years))) for r in RUNS}
    rows = []
    for j in range(n):
        o = MC.project(su, dict(zip(MC.PARAMS, X[j])), full=True)
        cd = draw_context(ctx, su, o['draw'], a13, red13, a45)
        pT_d, capped = tl_params_for_draw(pT, params, ctx, cd)
        if any(v['r'] > r_amb for v in pT_d['TL6'].values()):
            raise SystemExit(f'STOP: draw {j}: TL6 weaker than Ambitious L6.')
        r5, rt = runs_for_draw(cd, params, pT_d)
        S_d = np.asarray(cd['pop'], float) / np.asarray(cd['hh'], float)
        b = budgets.iloc[j]
        c_ref = float(o['carbon'][WINDOW].sum()) / M6
        if abs(c_ref / b['carbon_kt_2026_2050'] - 1) > 1e-9:
            raise SystemExit(f'pathways_mc: draw {j}: the Reference carbon differs from the AESA Monte Carlo.')
        tl_built = np.asarray(PW.engine.requirement(rt['E']), float)[2:]           # 2027-2050 (index 0 is 2025)
        row = dict(draw=j, **{N.identifier(k): float(X[j, i]) for i, k in enumerate(MC.PARAMS)},
                   carbon_index=carbon_index(o, I_c, gfa_c),
                   B_AR_kt_2026_2050=float(b['B_AR_kt_2026_2050']), B_AtP_kt_2026_2050=float(b['B_AtP_kt_2026_2050']),
                   L2_floor_binds=bool(np.any(S_mod[late] < S_d[late])),
                   TL2_floor_binds=bool(np.any(S_tl < S_d[late])),
                   TL6_capped=';'.join(capped), TL_dwellings_built_min_2027_2050=float(tl_built.min()),
                   TL_reoccupied_share_of_need=float(rt['info']['reoccupation']['share']))
        for r, E in (('REF', o), ('P5', r5['E']), ('TL', rt['E'])):
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
    rules = dict(
        L2_floor_binds_draws=int(df['L2_floor_binds'].sum()), TL2_floor_binds_draws=int(df['TL2_floor_binds'].sum()),
        TL6_capped_draws={t: int(df['TL6_capped'].fillna('').str.split(';').apply(lambda x, t=t: t in x).sum())
                          for t in pT['TL6']},
        L2_target_vs_montecarlo_high_variant_max_abs_diff=l2_vs_mc, n_draws=n)
    import json
    with open(layout.writing(layout.data('pathways/montecarlo_draw_rules.json', frozen=False)), 'w') as f:
        json.dump(rules, f, indent=1)
    N.columns(df).to_csv(layout.writing(layout.data('pathways/montecarlo_draws.csv', frozen=False)), index=False)
    summary = pd.DataFrame(summ)
    summary['central_draw_max_rel_diff'] = max(central.values())
    N.columns(summary).to_csv(layout.writing(layout.data('pathways/montecarlo_summary.csv', frozen=False)), index=False)
    N.columns(pd.DataFrame(ann)).to_csv(layout.writing(layout.data('pathways/montecarlo_annual.csv', frozen=False)),
                                        index=False)
    print(summary[['run', 'quantity', 'p5', 'p50', 'p95', 'probability_LoE_at_most_1']].to_string(index=False))
    print(rules)
    print(f'pathways_mc: {n:,} draws in {time.time() - t0:.0f} s')
    run_insights()


def run_insights():
    """The insight analyses from the saved per-draw file (also: python pathways_mc.py --insights)."""
    import json
    t1 = time.time()
    df = pd.read_csv(layout.data('pathways/montecarlo_draws.csv', frozen=False))
    imp, fits, cond, cond_summary = insights(df)
    imp.to_csv(layout.writing(layout.data('pathways/montecarlo_importance.csv', frozen=False)), index=False)
    fits.to_csv(layout.writing(layout.data('pathways/montecarlo_fits.csv', frozen=False)), index=False)
    cond.to_csv(layout.writing(layout.data('pathways/montecarlo_conditional_tl.csv', frozen=False)), index=False)
    with open(layout.writing(layout.data('pathways/montecarlo_conditional_tl.json', frozen=False)), 'w') as f:
        json.dump(cond_summary, f, indent=1)
    print(imp[imp['output'] == 'LoE_AR'][['run', 'input', 'src', 'src_r2', 'prcc', 'prcc_lo', 'prcc_hi']].to_string(index=False))
    print(cond[['model', 'term', 'odds_ratio_per_sd', 'or_lo', 'or_hi', 'mle_exists', 'events_per_variable']].to_string(index=False))
    print(json.dumps({k: v for k, v in cond_summary.items() if k not in ('method',)}, indent=1))
    print(f'pathways_mc: insight analyses in {time.time() - t1:.0f} s')


if __name__ == '__main__':
    if '--insights' in sys.argv[1:]:
        run_insights()
    else:
        main()
