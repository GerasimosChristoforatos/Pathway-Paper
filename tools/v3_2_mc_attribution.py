"""Attribution of the pathway Monte Carlo changes, MODEL v3.2.0 against v3.0.0 (audit tool; not part of the pipeline).

For every draw whose 2026-2050 carbon differs from v3.0 in any of the four pathway Monte Carlo runs (P5 Moderate,
P5 Ambitious, TL, TL-from2027), the draw is recomputed with the v3.2 pathways code on the v3.0 engine (git show of
release/model-v3.0.0:engine.py), i.e. with the release accounting (B) but without the zero-year soil guard (C):
    delta_B = B-only - v3.0     (carry-forward of unusable releases; payback on gross need)
    delta_C = v3.2 - B-only     (zero-year guard and the [0, 1] clip of the soil-bearing share)
plus, per run, the zero-built years 2027-2050 of the v3.2 run, the building years whose B-only soil share lies outside
[0, 1], and the v3.0-engine soil carbon booked in the zero-built years.
The v3.0 draws are read from the v3.0.0 full-profile commit (d084e09). Full profile only.

    PATHWAY_PROFILE=full python tools/v3_2_mc_attribution.py      -> docs/v3_2_mc_attribution.csv
"""
import contextlib, io, os, subprocess, sys, types
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine
import pathways_mc as PM, naming as N, layout
import MonteCarlo as MC
import runprofile
if runprofile.name() != 'full':
    raise SystemExit('v3_2_mc_attribution: full profile only (the v3.0 draws are those of the full-profile commit).')
OUT = os.path.join(ROOT, 'docs', 'v3_2_mc_attribution.csv')
old = pd.read_csv(io.StringIO(subprocess.run(['git', 'show', 'd084e09:outputs/data/pathways/montecarlo_draws.csv'],
                                             cwd=ROOT, capture_output=True, text=True, check=True).stdout))
new = pd.read_csv(layout.data('pathways/montecarlo_draws.csv', frozen=False))
RUNS = {'P5': 'P5', 'P5A': 'P5A', 'TL': 'TL', PM.INSTANT: 'TL_from2027'}
cols = {k: f'{v}_carbon_kt' for k, v in RUNS.items()}
diff = np.zeros(len(new), bool)
for c in cols.values():
    diff |= (new[c] - old[c]).abs().to_numpy() > 1e-9 * old[c].abs().to_numpy()
idx = np.flatnonzero(diff)
src = subprocess.run(['git', 'show', 'origin/release/model-v3.0.0:engine.py'], cwd=ROOT, capture_output=True,
                     text=True, check=True).stdout
eng30 = types.ModuleType('engine30')
exec(compile(src, 'engine30', 'exec'), eng30.__dict__)
ctx, params, det = PM.deterministic()
with contextlib.redirect_stdout(io.StringIO()):
    su = MC.build_setup(MC.MC_SCENARIOS[0][1])
a13, red13, a45 = PM.bootstrap_factors(su)
draws = pd.read_csv(layout.montecarlo('draws', 'REF', frozen=False))
X = draws[[N.identifier(c) for c in MC.PARAMS]].to_numpy(float)
rows = []
f32 = engine.forward
for j in idx:
    o = MC.project(su, dict(zip(MC.PARAMS, X[j])), full=True)
    cd = PM.draw_context(ctx, su, o['draw'], a13, red13, a45)
    engine.forward = eng30.forward
    try:
        rb = PM.runs_for_draw(cd, params)
    finally:
        engine.forward = f32
    r2 = PM.runs_for_draw(cd, params)
    for k, lab in RUNS.items():
        cb = float(np.asarray(rb[k]['E']['carbon'], float)[PM.WINDOW].sum()) / PM.M6
        c0, c2 = float(old.loc[j, cols[k]]), float(new.loc[j, cols[k]])
        Eb, E2 = rb[k]['E'], r2[k]['E']
        w = slice(2, None)
        zero = np.asarray(E2['total'], float)[w] == 0.0
        sb = np.asarray(Eb['soil_share'], float)[w]
        clip = (~zero) & ((sb < 0.0) | (sb > 1.0))
        rows.append(dict(draw=int(j), run=lab, v3_0=c0, b_only=cb, v3_2=c2, delta_total=c2 - c0,
                         delta_B=cb - c0, delta_C=c2 - cb, zero_built_years=int(zero.sum()),
                         soil_share_clipped_years=int(clip.sum()),
                         v3_0_soil_in_zero_years_kt=float(np.asarray(Eb['soil'], float)[w][zero].sum()) / PM.M6))
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
tol = lambda s, ref: s.abs() > 1e-9 * ref.abs()
for lab, g in df.groupby('run'):
    t, b, c = tol(g.delta_total, g.v3_0), tol(g.delta_B, g.v3_0), tol(g.delta_C, g.v3_0)
    print(f"{lab}: changed {int(t.sum())} (max |d| {g.delta_total.abs().max():.3f} kt); B {int(b.sum())} "
          f"(max {g.delta_B.abs().max():.3f}); C {int(c.sum())} (max {g.delta_C.abs().max():.3f}); "
          f"C draws {sorted(g.draw[c].tolist())}; of which with zero-built years {int((c & (g.zero_built_years > 0)).sum())}, "
          f"with clipped soil share in a building year {int((c & (g.soil_share_clipped_years > 0)).sum())}")
