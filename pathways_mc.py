"""
PATHWAY MONTE CARLO (MODEL v3.0.0): P5 Combined (Moderate, Ambitious) and TL under the joint input uncertainty
================================================================================================================
Every saved Monte Carlo draw of the Reference (outputs/data/montecarlo/draws_REF.csv: the Latin hypercube draws of
population rank, dwelling-size multiplier, completion rate and the case-study carbon-factor bootstrap; 5,000 in
the full profile, 1,000 in the light one) is re-run through MonteCarlo.project (full=True exposes the draw's
engine inputs) and then through the pathway layer (pathways.run, the same function as the deterministic runs):
P5 Moderate, P5 Ambitious, TL and the instant TL (sensitivity; summary only).

  * every lever level is applied to the draw's own inputs as in the deterministic runs: the ratios (L2 design
    density, L6 material carbon) to the draw's own OLF, dwelling sizes and A1-A3; L3 adds the published Stats NZ
    High - Medium gap to the draw's own household size; L4 moves the vacancy parameter to the same Ambitious
    value; the overbuild excess is the draw's own Reference excess (MonteCarlo.project), held fixed in the draw's
    lever runs and absorbed on the Reference weights;
  * TL3 (the historical maximum household size) is taken as max(2.7905, the draw's Ambitious path) so that TL3 is
    never weaker than Ambitious in a draw (counted); every other TLn is a ratio or an absolute zero / full.

The level of exceedance of every draw uses that draw's cumulative AR and AtP budgets
(outputs/data/aesa/montecarlo_draw_budgets.csv, boundaries.py, the same draws).

Insight analyses (mcstats.py) on the four sampled inputs (population rank, dwelling-size multiplier, completion
rate, carbon-factor index): SRC and PRCC with percentile bootstrap intervals (runprofile bootstrap replicates),
LOWESS and least-squares fits, and the conditional TL (Firth logistic regression of 1[TL LoE AR <= 1]).

STOP: the central draw must reproduce the deterministic P5 Moderate, P5 Ambitious, TL and instant TL runs to
1e-9; every draw's Reference carbon equals the saved draw; the bootstrap is reproduced exactly; in every draw
TL <= P5 Ambitious <= P5 Moderate (cumulative carbon), dwellings built >= 0, and the cumulative re-occupied
never exceeds the cumulative released.

Writes outputs/data/pathways/montecarlo_draws.csv (per draw), montecarlo_summary.csv, montecarlo_annual.csv,
montecarlo_draw_rules.json and the insight files.

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
import runprofile  # noqa: E402

M6 = 1e6
PCT = (5, 25, 50, 75, 95)
CENTRAL_TOL = 1e-9
RUNS = ('REF', 'P5', 'TL')                       # the insight analyses (P5 = P5 Moderate)
INSTANT = 'TL_from2027'                          # the instant TL sensitivity (summary and annual percentiles only)
SUMMARY_RUNS = ('REF', 'P5', 'P5A', 'TL', INSTANT)     # P5A = P5 Ambitious
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


def write_carbon_factors(su, a13):
    """MODEL v3.2.0 (from v3.1.0) (D38): the resulting pooled A1-A3 factor of each Reference draw by typology (kg CO2e/m2, 2025
    technology), from the saved draws' carbon-factor parameter and the saved setup's bootstrap replicates
    (MonteCarlo.carbon_bootstrap, same seed and indices; nothing is resampled). Writes
    outputs/data/montecarlo/carbon_factors_REF.csv."""
    draws = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
    u = draws[N.identifier('carbon')].to_numpy(float)
    kc = np.minimum((u * MC.N_BOOT).astype(int), MC.N_BOOT - 1)
    rows = [dict(draw=int(j), typology=t, a1a3_kg_per_m2=float(a13[kc[j], i]))
            for j in range(len(draws)) for i, t in enumerate(su['typ'])]
    pd.DataFrame(rows).to_csv(layout.writing(layout.data('montecarlo/carbon_factors_REF.csv', frozen=False)), index=False)


def draw_context(ctx, su, d, a13, red13, a45):
    """The pathway context of one draw: the deterministic Reference context with the draw's inputs."""
    typ = su['typ']
    fi = dict(d['fwd_inputs'])
    ji = d['join_info']
    c = dict(ctx)
    c.update(pop=d['pop'], hh=d['hh'], growth=d['growth'], fwd_inputs=fi,
             size_ref={t: float(fi['size'][t]) for t in typ}, olf=dict(fi['olf']), v0=float(fi['v']),
             rate_demol=float(fi['rate_demol']), rate_unc=np.asarray(fi['rate_unc'], float),
             long_run_residual=float(d['unc_long']), excess=np.asarray(ji['excess'], float).copy(),
             join_reference=np.asarray(d['join'], float), soil=dict(fi['soil']), events=fi['events'])
    if d['kc'] is not None:
        c.update(a13_2025={t: float(a13[d['kc'], j]) for j, t in enumerate(typ)},
                 red13={t: np.asarray(red13[d['kc'], j], float) for j, t in enumerate(typ)},
                 a45_2025={t: float(a45[d['kc'], j]) for j, t in enumerate(typ)})
    return c


def runs_for_draw(ctx_d, params):
    TL = LV.tl_levels(LV.TL_COMPONENTS)
    return dict(P5=PW.run(ctx_d, params, LV.pathway_levers('P5', 'moderate')),
                P5A=PW.run(ctx_d, params, LV.pathway_levers('P5', 'ambitious')),
                TL=PW.run(ctx_d, params, TL), **{INSTANT: PW.run(ctx_d, params, TL, LV.TL_FROM2027)})


def deterministic():
    """The deterministic Reference context, lever parameters and the P5 Moderate / Ambitious, TL and instant TL runs."""
    B = PW.boss_state(PW.REFERENCE)
    ctx = PW.base_context(B, PW.REFERENCE, PW.boundaries())
    params = PW.resolve_params(B)
    return ctx, params, {k: R['E'] for k, R in runs_for_draw(ctx, params).items()}


def check_central(su, ctx, params, det):
    """STOP unless the central draw reproduces the deterministic P5 Moderate / Ambitious, TL and instant TL runs to 1e-9."""
    o = MC.project(su, MC.central(su), full=True)
    cd = draw_context(ctx, su, o['draw'], None, None, None)
    runs = runs_for_draw(cd, params)
    worst = {}
    for name, R in runs.items():
        a, b = R['E'], det[name]
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
    print(f'[check] pathway MC central draw vs the deterministic runs: max relative difference {w:.1e} '
          f'({"OK" if w < CENTRAL_TOL else "FAIL"})')
    if w >= CENTRAL_TOL:
        raise SystemExit(f'STOP: the pathway Monte Carlo central draw does not reproduce the deterministic runs {worst}.')
    return worst


INPUTS = ('z_pop', 'size', 'complete', 'carbon_index')
INPUT_LABELS = {'z_pop': 'Population rank (z-score)', 'size': 'Dwelling-size multiplier',
                'complete': 'Completion rate', 'carbon_index': 'Carbon-factor index'}
OUTPUTS = ('floor_area_Mm2', 'carbon_kt', 'LoE_AR')
BOOT_B = runprofile.get('bootstrap')
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
    estimable = 0.0 < yy.sum() < len(yy)                      # MODEL v3.2.0 (from v3.1.0): a single outcome class -> no model

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

    if estimable:
        for k, c in enumerate(INPUTS):
            add_model(f'univariable: {c}', [k])
        fr_all = add_model('multivariable', list(range(len(INPUTS))))
        eta = np.column_stack([np.ones(len(yy)), Z]) @ fr_all['beta']
    else:
        eta = None
        cond.append(dict(model='not estimable', term='', mle_exists=False, events_rarer_class=events,
                         mle_note=('no draw has TL within AR' if yy.sum() == 0 else 'every draw has TL within AR')
                         + ': the logistic models are not estimable (single outcome class)'))
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
                   auc_multivariable_firth=mcstats.auc(eta, yy.astype(bool)) if estimable else None,
                   models_estimable=bool(estimable),
                   population_threshold={'adopted': population_threshold(df, 'TL_LoE_AR')},
                   by_population_quintile=quint, exceeding_draws=exceed, inputs_standardised=True,
                   method='Firth (1993) penalised-likelihood logistic regression with profile penalised-likelihood '
                          '95% intervals (Heinze & Schemper 2002), odds ratio per standard deviation of each input; '
                          'univariable models (one input; the others random) and the multivariable model; whether the '
                          'maximum-likelihood estimate exists is reported. Proportions: Wilson score intervals.',
                   caveat='the pathway model is deterministic: given all four inputs the outcome is fixed, and the '
                          'intervals describe the Monte Carlo design, not a sampling process; with fewer than 10 '
                          'events per variable (Peduzzi et al. 1996, J Clin Epidemiol 49, 1373) the multivariable '
                          'odds ratios are indicative only')
    return pd.DataFrame(imp), pd.DataFrame(fits), pd.DataFrame(cond), summary


THRESHOLD_POINTS = 101


def population_threshold(df, col):
    """MODEL v3.2.0 (from v3.1.0) (ED5b): the 2050 New Zealand population at which P(TL LoE AR <= 1) = 50%, from a univariate
    logistic regression of the outcome on the draw's 2050 population (maximum likelihood; Firth's penalised
    likelihood where the MLE does not exist), with a percentile bootstrap 95% interval (resampled draws; the
    insight bootstrap's stream). If no draw (or every draw) has TL within AR the threshold is not estimable and that
    is reported instead."""
    x = df['P_NZ_2050'].to_numpy(float)
    y = (df[col].to_numpy(float) <= 1.0).astype(float)
    k, n = int(y.sum()), len(y)
    base = dict(outcome=f'{col} <= 1', n=n, within_AR=k, p_within_AR=k / n)
    if k == 0 or k == n:
        return dict(base, estimable=False, note=('no draw has TL within AR' if k == 0 else
                                                 'every draw has TL within AR') + ': no population threshold exists in '
                    'the sampled range; the LoE distribution against the 2050 population is shown instead')
    mu, sd = float(x.mean()), float(x.std(ddof=1))

    def fit(xx, yy):
        z = ((xx - mu) / sd)[:, None]
        try:
            b = mcstats.logistic(z, yy)['beta']
            how = 'maximum likelihood'
        except mcstats.Separation:
            b = mcstats.firth(z, yy)['beta']
            how = 'Firth penalised likelihood (MLE does not exist)'
        return b, how

    b, how = fit(x, y)
    thr = mu + sd * (-b[0] / b[1])
    rng = np.random.default_rng(BOOT_SEED + 7)
    boots, skipped = [], 0
    for _ in range(BOOT_B):
        i = rng.integers(0, n, n)
        if y[i].min() == y[i].max():
            skipped += 1
            continue
        bb, _ = fit(x[i], y[i])
        boots.append(mu + sd * (-bb[0] / bb[1]))
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
    grid = np.linspace(x.min(), x.max(), THRESHOLD_POINTS)
    p = 1.0 / (1.0 + np.exp(-(b[0] + b[1] * (grid - mu) / sd)))
    return dict(base, estimable=True, method=how, beta_per_sd=[float(v) for v in b], population_mean=mu,
                population_sd=sd, threshold_P_NZ_2050=float(thr), ci95=[float(lo), float(hi)],
                bootstrap_resamples=BOOT_B, bootstrap_single_class_skipped=skipped,
                curve=dict(P_NZ_2050=[float(v) for v in grid], probability=[float(v) for v in p]),
                direction=('P(within AR) falls as the 2050 population rises' if b[1] < 0 else
                           'P(within AR) rises with the 2050 population'))


def reoccupation_counts(df):
    """How often the release constraint binds over the draws, the share s, the draws where R > G+ (the surplus left
    vacant in 2050), for TL and the instant TL."""
    pc = lambda v: {f'p{p}': float(np.percentile(v, p)) for p in (0, 5, 25, 50, 75, 95, 100)}
    out = dict(rule='constant share s = min(R, G+) / G+ of each year\'s need after the overbuild payback; re-occupied '
                    'never ahead of the cumulative release (shortfall built, share recomputed from the remaining pool); '
                    'R = TL3 + TL4 releases (pathways.reoccupation)')
    for lab_ in ('TL', INSTANT):
        sur = df[f'{lab_}_surplus_vacant_2050']
        exceed = df[f'{lab_}_released_R'] > df[f'{lab_}_need_G_plus']
        npn = df[f'{lab_}_nonpositive_need_years'] > 0
        out[lab_] = dict(
            share_percentiles=pc(df[f'{lab_}_reoccupation_share']),
            R3_percentiles=pc(df[f'{lab_}_released_R3']), R4_percentiles=pc(df[f'{lab_}_released_R4']),
            draws_R_exceeds_G_plus=int(exceed.sum()),
            surplus_vacant_2050_where_R_exceeds_G_plus=pc(sur[exceed]) if exceed.any() else None,
            draws_with_nonpositive_need_year=int(npn.sum()),
            draws_release_constraint_binds=int((df[f'{lab_}_release_constraint_binding_years'] > 0).sum()),
            release_constraint_binding_years_percentiles=pc(df[f'{lab_}_release_constraint_binding_years']),
            draws_with_a_zero_building_year=int((df[f'{lab_}_dwellings_built_min_2027_2050']
                                                 <= PW.T_ZERO_TOL_DWELLINGS).sum()),
            dwellings_built_min_2027_2050_percentiles=pc(df[f'{lab_}_dwellings_built_min_2027_2050']))
    return out


def main():
    t0 = time.time()
    ctx, params, det = deterministic()
    name, settings = MC.MC_SCENARIOS[0]
    if name != 'REF':
        raise SystemExit('pathways_mc: the first Monte Carlo scenario must be the Reference.')
    with contextlib.redirect_stdout(io.StringIO()):
        su = MC.build_setup(settings)
    central = check_central(su, ctx, params, det)
    a13, red13, a45 = bootstrap_factors(su)
    write_carbon_factors(su, a13)
    oc = MC.project(su, MC.central(su), full=True)
    gfa_c = np.asarray(oc['gfa_t'], float)
    I_c = np.broadcast_to(np.asarray(oc['I'], float).reshape(len(su['typ']), -1), gfa_c.shape)
    draws = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
    X = draws[[N.identifier(c) for c in MC.PARAMS]].to_numpy(float)
    budgets = pd.read_csv(layout.data('aesa/montecarlo_draw_budgets.csv', frozen=False))
    if len(budgets) != len(draws):
        raise SystemExit('pathways_mc: the AESA draw budgets do not match the saved draws (re-run boundaries.py).')
    years = np.asarray(ctx['years'])
    late = years >= LV.OBSERVED_YEAR + 1
    gap = np.array([LV.by_year(params['L3']['gap'], int(y)) for y in years])
    n = len(draws)
    annual = {r: np.empty((n, len(years))) for r in SUMMARY_RUNS}
    rows, stops = [], []
    for j in range(n):
        o = MC.project(su, dict(zip(MC.PARAMS, X[j])), full=True)
        cd = draw_context(ctx, su, o['draw'], a13, red13, a45)
        runs = runs_for_draw(cd, params)
        S_d = np.asarray(cd['pop'], float) / np.asarray(cd['hh'], float)
        b = budgets.iloc[j]
        c_ref = float(o['carbon'][WINDOW].sum()) / M6
        if abs(c_ref / b['carbon_kt_2026_2050'] - 1) > 1e-9:
            raise SystemExit(f'pathways_mc: draw {j}: the Reference carbon differs from the AESA Monte Carlo.')
        reo = {}
        for lab_ in ('TL', INSTANT):
            ro = runs[lab_]['info']['reoccupation']
            built = np.asarray(PW.engine.requirement(runs[lab_]['E']), float)
            if (built[1:] < -PW.T_ZERO_TOL_DWELLINGS).any():
                stops.append(f'draw {j} {lab_}: built_t < 0')
            rel = ro['released_tl3'] + ro['released_tl4']
            if (np.cumsum(ro['reoccupied']) > np.cumsum(rel) + PW.REOCCUPATION_TOL * max(ro['R'], 1.0)).any():
                stops.append(f'draw {j} {lab_}: cumulative re-occupied > released')
            reo.update({f'{lab_}_reoccupation_share': ro['share'], f'{lab_}_released_R': ro['R'],
                        f'{lab_}_released_R3': ro['R3'], f'{lab_}_released_R4': ro['R4'],
                        f'{lab_}_need_G_plus': ro['G_plus'], f'{lab_}_surplus_vacant_2050': ro['surplus_vacant_2050'],
                        f'{lab_}_nonpositive_need_years': len(ro['nonpositive_need_years']),
                        f'{lab_}_release_constraint_binding_years': int(ro['release_binds'].sum()),
                        f'{lab_}_dwellings_built_min_2027_2050': float(built[2:].min())})
        row = dict(draw=j, **{N.identifier(k): float(X[j, i]) for i, k in enumerate(MC.PARAMS)},
                   P_NZ_2050=float(np.asarray(cd['pop'], float)[-1]),
                   carbon_index=carbon_index(o, I_c, gfa_c),
                   B_AR_kt_2026_2050=float(b['B_AR_kt_2026_2050']), B_AtP_kt_2026_2050=float(b['B_AtP_kt_2026_2050']),
                   TL3_draw_max_binds=bool(np.any((S_d + gap)[late] > params['L3']['tl'])),
                   overbuild_cap_binding_years=int(runs['P5']['info']['payback_cap_binds'].sum()),
                   **reo)
        for r, E in [('REF', o)] + [(k, R['E']) for k, R in runs.items()]:
            carbon = np.asarray(E['carbon'], float)
            annual[r][j] = carbon
            c = float(carbon[WINDOW].sum()) / M6
            row.update({f'{r}_carbon_kt': c, f'{r}_floor_area_Mm2': float(np.asarray(E['gfa'] if r == 'REF'
                                                                                    else E['total'])[WINDOW].sum()) / M6,
                        f'{r}_LoE_AR': c / row['B_AR_kt_2026_2050'], f'{r}_LoE_AtP': c / row['B_AtP_kt_2026_2050']})
        if not row['TL_carbon_kt'] <= row['P5A_carbon_kt'] * (1 + 1e-12) <= row['P5_carbon_kt'] * (1 + 1e-12):
            stops.append(f'draw {j}: TL <= P5 Ambitious <= P5 Moderate violated')
        rows.append(row)
        if (j + 1) % 1000 == 0:
            print(f'  {j + 1:,} draws ({time.time() - t0:.0f} s)')
    if stops:
        raise SystemExit('STOP (pathway Monte Carlo):\n  ' + '\n  '.join(stops[:20]))
    df = pd.DataFrame(rows)
    summ = []
    for r in SUMMARY_RUNS:
        for q in ('carbon_kt', 'floor_area_Mm2', 'LoE_AR', 'LoE_AtP'):
            v = df[f'{r}_{q}'].to_numpy()
            e = dict(run=r, quantity=q, mean=float(v.mean()), **{f'p{p}': float(np.percentile(v, p)) for p in PCT})
            if q.startswith('LoE'):
                e['probability_LoE_at_most_1'] = float(np.mean(v <= 1.0))
            summ.append(e)
    ann = []
    for r in SUMMARY_RUNS:
        for i, y in enumerate(years):
            if y < 2026:
                continue
            ann.append(dict(run=r, year=int(y), **{f'carbon_kt_p{p}': float(np.percentile(annual[r][:, i], p) / M6)
                                                   for p in PCT},
                            carbon_kt_mean=float(annual[r][:, i].mean() / M6)))
    rules = dict(TL3_draw_max_binds_draws=int(df['TL3_draw_max_binds'].sum()), n_draws=n,
                 probability_TL_LoE_AR_at_most_1=float(np.mean(df['TL_LoE_AR'] <= 1.0)),
                 overbuild_cap_binds_draws_P5=int((df['overbuild_cap_binding_years'] > 0).sum()),
                 tl_le_p5_every_draw=True, reoccupation=reoccupation_counts(df))
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
    print(cond.reindex(columns=['model', 'term', 'odds_ratio_per_sd', 'or_lo', 'or_hi', 'mle_exists',
                                'events_per_variable']).to_string(index=False))
    print(json.dumps({k: v for k, v in cond_summary.items() if k not in ('method',)}, indent=1))
    print(f'pathways_mc: insight analyses in {time.time() - t1:.0f} s')


def carbon_factors_only():
    """python pathways_mc.py --carbon-factors: write montecarlo/carbon_factors_REF.csv from the saved draws only."""
    name, settings = MC.MC_SCENARIOS[0]
    with contextlib.redirect_stdout(io.StringIO()):
        su = MC.build_setup(settings)
    write_carbon_factors(su, bootstrap_factors(su)[0])


if __name__ == '__main__':
    if '--insights' in sys.argv[1:]:
        run_insights()
    elif '--carbon-factors' in sys.argv[1:]:
        carbon_factors_only()
    else:
        main()
