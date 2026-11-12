"""Methods draft, part 5: the uncertainty analysis (MonteCarlo.py, boundaries.mc_runs, pathways_mc.py, mcstats.py).
Every number is read from the settings of those modules (runprofile.py, MonteCarlo.py, projection.py) or from the
outputs (montecarlo/, aesa/results.json, pathways/montecarlo_*); nothing is typed by hand.

lines() returns the Markdown of this part without its title (section headings at '##'); tools/methods.py merges it,
one heading level down, into outputs/reports/METHODS_DRAFT.md.
"""
import importlib.metadata
import inspect
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layout  # noqa: E402
import naming as N  # noqa: E402


def data(rel):
    return layout.data(rel)


def js(rel):
    with open(data(rel)) as f:
        return json.load(f)


def lines():
    import MonteCarlo as MC
    import pathways_mc as PMC
    import projection
    import runprofile
    src = inspect.getsource(MC)
    m = re.search(r'bootstrap\(confidence_level=([0-9.]+), n_resamples=(\d+)\)', src)
    if not m:
        raise SystemExit('uncertainty_methods: the Sobol bootstrap call of MonteCarlo.py has changed; rewrite the text.')
    cl, n_res = float(m.group(1)), int(m.group(2))
    w = re.search(r"hist_dwelling_size'\]\[t\]\.loc\[(\d{4}):(\d{4})\]", src)
    if not w:
        raise SystemExit('uncertainty_methods: the dwelling-size window of MonteCarlo.py has changed; rewrite the text.')
    knots = ', '.join(f'{p}th' for p in MC.PCT_COLS)
    full, light = runprofile.PROFILES['full'], runprofile.PROFILES['light']
    draws = pd.read_csv(layout.montecarlo('draws', 'REF'))
    q = pd.read_csv(data('montecarlo/input_distributions_REF.csv')).set_index('input')
    sob = pd.read_csv(data('montecarlo/sobol_REF.csv')) if runprofile.get('sobol') else None   # full profile only
    imp = pd.read_csv(data('pathways/montecarlo_importance.csv'))
    ct = js('pathways/montecarlo_conditional_tl.json')
    r = js('aesa/results.json')
    d = len(MC.PARAMS)
    z95 = float(MC.Z_KNOTS[-1])
    size_sigma = float(np.log(q.loc['size', 'q95']) / z95)
    band = projection.COMPLETION_RATE_BAND
    hl = MC.HALF_LIFE_RANGE

    def pct(k, fmt):
        return ' / '.join(format(q.loc[k, c], fmt) for c in ('q05', 'q50', 'q95'))
    rows = [
        ('z_pop (population and household size)', 'standard normal; one rank in every year (comonotone)',
         f'Stats NZ 2024-base stochastic population projection: the published level spread at the {knots} '
         'percentiles, linear in z; household size by the same z through the Stats NZ 2023-base Low / Medium / '
         f'High {MC.projection.HH_PROPENSITY} household projections placed at z = {MC.VARIANT_Z["Low"]:.3f} / 0 / '
         f'{MC.VARIANT_Z["High"]:.3f}',
         pct('z_pop', '.2f')),
        ('size (dwelling size)', f'lognormal multiplier, σ = {size_sigma:.4f}',
         f'RMS log deviation of annual typology dwelling sizes {w.group(1)}-{w.group(2)} from the adopted reference', pct('size', '.3f')),
        ('complete (completion rate)', f'uniform({band[0]:g}, {band[1]:g})',
         'completion milestones of Auckland consents (Greenaway-McGrevy & Jones 2023; Jones, Greenaway-McGrevy & Crow '
         '2025); the stock calibration, the census replacement rates, the 2024-2025 starting surplus and the '
         'acquired-rights base are redone in each draw', pct('complete', '.3f')),
        ('carbon (case-study carbon factors)', f'uniform index into {MC.N_BOOT:,} bootstrap replicates',
         'stratified bootstrap of the case studies within sub-type (duplicates removed, re-pooled as Building_factors); '
         'the apartments (one independent case) take a mean-preserving lognormal multiplier with the pooled '
         'between-building log-SD of the other sub-types', pct('carbon', '.2f')),
        ('half_life (replacement half-life)', f'uniform({hl[0]:g}, {hl[1]:g}) yr',
         'not identifiable from the census record; the Reference variant only', pct('half_life', '.1f')),
    ]
    L = [f'Joint uncertainty is propagated by Latin hypercube sampling (McKay, Beckman & Conover 1979): '
         f"{full['n_draws']:,} draws in the full profile (seed {full['mc_seed']}) and {light['n_draws']:,} in the light "
         f"profile (seed {light['mc_seed']}) of the {d} inputs below, for the Reference "
         'only (replacement-level uncertainty is reported by the variants of ED3 and the one-at-a-time rows). '
         'The reported results are those of the full profile '
         f'({len(draws):,} draws in montecarlo/draws_REF.csv). Each draw runs the same forward functions as the '
         'deterministic projection (engine.py), which uses the median of every sampled input; the central draw is '
         'checked against the projection to 1e-9.', '',
         '| input | distribution | basis | 5th / 50th / 95th percentile of the draws |', '|---|---|---|---|']
    L += [f'| {a} | {b} | {c} | {e} |' for a, b, c, e in rows]
    L += ['', 'Population and household size share one draw because, within one living-arrangement propensity, the '
          'Stats NZ 2023-base Low / Medium / High household projections differ only through their population '
          'projections (the 5th / 50th / 95th percentiles of the stochastic population projection), so the household '
          'size moves with the population percentile (N4, resolved). Not sampled: the living-arrangement propensity '
          '(A, held at 2023; B, the change modelled on the 2001-2023 censuses, is a one-at-a-time row), the net replacement level (the Reference only; its half-life is sampled; '
          'the variants are reported deterministically in ED3 and the one-at-a-time rows), the typology mix, the census rebase of households, the pre-2013 empty '
          'share, the future vacancy and the retirement-village share (total Sobol indices about zero in a '
          'full-input run), the demolition rate (it trades one-for-one with the calibrated residual), the observed '
          'consents and population (data) and the soil order (a bounding scenario, not a probability).', '']
    rb = r['mc']['REF']
    L += [f'In every draw the acquired-rights base Ī_sec,base is recomputed from that draw\'s carbon-factor replicate '
          'on the 2016-2025 built floor area at that draw\'s completion rate (boundaries.mc_runs, '
          'boundaries.history_at_completion, boundaries.base_with_factors): the carbon factors and the completion rate '
          'are shared parameters of the base and the projection and are sampled once (the shared-parameter rule of '
          'Part 2). Each draw also recomputes the 2024-2025 stock-identity residual and its starting surplus at its own '
          'completion rate. '
          f"Ī_sec,base over the draws: {rb['I_sec_base_kt_p5']:,.1f} / {rb['I_sec_base_kt_p50']:,.1f} / "
          f"{rb['I_sec_base_kt_p95']:,.1f} kt/yr (5th / 50th / 95th percentile).", '']
    if sob is None:                                    # the light profile computes no Sobol indices
        top = 'not computed in this (light) profile run; see the full-profile outputs'
    else:
        sc = sob[sob['output'] == 'carbon_kt'].sort_values('ST', ascending=False)
        top = ', '.join(f"{N.MC_INPUT.get(x.input, x.input)} {x.ST:.2f} ({x.ST_lo:.2f}-{x.ST_hi:.2f})"
                        for x in sc.head(3).itertuples())
    L += [f'**Variance-based sensitivity.** First-order and total Sobol indices of the Reference (full profile): base '
          f'sample N = {MC.N_SOBOL:,} ({MC.N_SOBOL * (d + 2):,} model evaluations), the estimators of Saltelli et al. '
          f"(2010) and Jansen (1999) as implemented in scipy.stats.sobol_indices (scipy "
          f"{importlib.metadata.version('scipy')}), with BCa {100 * cl:g}% intervals from {n_res:,} bootstrap resamples "
          f'(Efron 1987). Total indices of cumulative carbon 2026-2050: {top}. Population and household size are '
          'one grouped input (one z, perfectly dependent): their indices are grouped Sobol indices (Jacques, Lavergne '
          '& Devictor 2006).', '']
    B = int(imp['bootstrap_resamples'].iloc[0])
    L += [f'**Pathway Monte Carlo** (pathways_mc.py). The Reference, the Moderate and Ambitious Pathways and the '
          'Theoretical Limit are run on the same draws (paired), so their differences are draw by draw. The importance '
          'of each input for floor area, carbon and the cumulative LoE of AR is given by standardised regression '
          f'coefficients and partial rank correlation coefficients (Marino et al. 2008) with percentile bootstrap '
          f'intervals ({B:,} resamples).', '']
    ps = pd.read_csv(data('pathways/montecarlo_summary.csv'))
    cq = ps[(ps['run'] == 'REF') & (ps['quantity'] == 'committed_lower_kt')]
    com = js('baseline/projection.json')['committed']
    if len(cq) != 1:
        raise SystemExit('uncertainty_methods: no committed_lower_kt row in pathways/montecarlo_summary.csv.')
    cq = cq.iloc[0]
    L += [f"**Committed after 2050.** For every Reference draw the committed emissions (the later B2/B4 events of the "
          f"2026-2050 cohorts and their C1-C4) are computed with pathways.committed on that draw's floor area by "
          f"typology; the repair and end-of-life factors are held at their central values, so the range comes from "
          f"the floor-area uncertainty (population, household size, dwelling size, completion rate). At the lower "
          f"decarbonisation bound (2050 factors held for the later events): central {com['lower_kt']:,.0f} kt, median "
          f"{cq['p50']:,.0f} kt, 50% interval {cq['p25']:,.0f}-{cq['p75']:,.0f}, 90% interval {cq['p5']:,.0f}-"
          f"{cq['p95']:,.0f} kt (pathways/montecarlo_summary.csv; per draw in pathways/montecarlo_draws.csv).", '']
    th = ct['population_threshold']['adopted']
    L += [f"The share of draws in which TL stays within the AR budget is {100 * ct['p_within_AR']:.1f}% "
          f"({ct['within_AR']:,} of {ct['n']:,}; Wilson 95% interval {100 * ct['wilson_95'][0]:.1f}-"
          f"{100 * ct['wilson_95'][1]:.1f}%, Wilson 1927). The 2050 population at which P(TL LoE AR ≤ 1) = 50% is "
          f"{th['threshold_P_NZ_2050'] / 1e6:.2f} million (95% interval {th['ci95'][0] / 1e6:.2f}-"
          f"{th['ci95'][1] / 1e6:.2f}), from a univariate logistic regression on the draw's 2050 population fitted by "
          "Firth's penalised likelihood where the maximum-likelihood estimate does not exist (Firth 1993; Heinze & "
          f"Schemper 2002), with a percentile bootstrap of {th['bootstrap_resamples']:,} resamples (seed "
          f'{PMC.BOOT_SEED} in the full profile).']
    return L
