"""Attribute the gap between the MC median and the central run: re-run the
same Latin hypercube with ONE input fixed at its adopted (central) value."""
from common import *
import contextlib, io
from scipy.stats import qmc
import MonteCarlo as MC
with contextlib.redirect_stdout(io.StringIO()):
    su = MC.build_setup()
dists = MC.distributions(su); cen = MC.central(su); P = MC.PARAMS
N = MC.N_UNCERTAINTY
lhs = qmc.LatinHypercube(d=len(P), seed=MC.SEED).random(N)
X = np.array([dists[k].ppf(lhs[:, i]) for i, k in enumerate(P)])
def mc_run(fix=None):
    Y = np.empty((2, N))
    for j in range(N):
        p = dict(zip(P, X[:, j]))
        if fix: p[fix] = cen[fix]
        o = MC.project(su, p); Y[0, j] = o['gfa'][1:].sum()/1e6; Y[1, j] = o['carbon'][1:].sum()/1e6
    return Y
base = mc_run(); c0 = MC.summarise(MC.project(su, cen))
print(f"all sampled: median GFA {np.median(base[0]):.2f} carbon {np.median(base[1]):,.0f}; central {c0[0]:.2f} / {c0[1]:,.0f}; central pct {100*(base[0]<c0[0]).mean():.1f}")
print(f"{'input fixed at adopted':<14}{'adopted':>10}{'dist median':>12}{'dist mean':>11}{'MC med GFA':>11}{'shift':>8}{'central pct':>12}")
for k in P:
    if k == 'carbon':
        Y = base.copy(); adopted = 'central'
        continue
    Y = mc_run(k)
    print(f"{k:<14}{cen[k]:>10.4g}{dists[k].median():>12.4g}{dists[k].mean():>11.4g}{np.median(Y[0]):>11.2f}{np.median(Y[0])-np.median(base[0]):>+8.2f}{100*(Y[0]<c0[0]).mean():>12.1f}")
# all non-population inputs fixed at adopted: does the MC median coincide with the central run?
Y = np.empty(N)
for j in range(N):
    p = dict(cen); p['z_pop'] = X[0, j]; Y[j] = MC.project(su, p)['gfa'][1:].sum()/1e6
print(f"only z_pop sampled: median {np.median(Y):.2f} (central {c0[0]:.2f})")
