# MODEL v3.2.0: changes and decisions (in progress)

Branch `release/model-v3.2.0`, created from `release/model-v3.0.0` (d084e09). MODEL v3.1.0 is withdrawn
(`release/model-v3.1.0`, WITHDRAWN.md): its inventory accounting expanded the scope to the existing stock. v3.2 keeps
the v3.0 cause-based accounting and ports the non-methodological fixes of v3.1.

## Ported so far (code only; no outputs regenerated)

* `bands.py` (A2 release accounting) from v3.1 without the accounting change: no soil spreading, no legacy band;
  soil carbon loss attributed to the construction year as in v3.0.
* `pathways.py` from v3.1 (A2 release flows, A4 'fast' re-occupation row) without: soil after 2050, legacy fields and
  checks, the soil kernel. Fig6 split: fixed = the 2026 cohort; later = A1-A5 + soil + in-window B2/B4 of the
  2027-2050 cohorts (y = cut in total carbon per m2).
* `projection.py`: only the A2 band pieces (fig_bands from bands.in_scope; bands_in_scope export).
* `validation.py` (A3 history split), `levers.py` (A5 check row), `naming.py` (release and history bands; no legacy,
  no soil-after component).

## STOP (MC check, light profile): A2 changes Monte Carlo draws

The pathway Monte Carlo calls pathways.run for every draw. On the light profile (1,000 draws; inputs = the v3.0 light
outputs, verified against the v3.0 lock) the v3.2 code changes pathways/montecarlo_draws.csv and the files derived
from it. Diagnosis (scratch harness, not committed):

1. Negative-gross carry (A2: an unusable amount is carried forward): in low-population draws a year's gross building is
   negative; v3.0 built nothing that year and dropped the deficit, v3.2 carries it against later building.
   TL: 20 of 1,000 draws differ (max 5.9 kt, 0.28%); TL-from2027: 150 draws (max 102 kt, 1.6%). With the carry
   replaced by the v3.0 clip, every TL / TL-from2027 draw returns to v3.0 (except 1e-11 noise in one diagnostic column).
2. Payback on gross need (A2): draw 514, P5 Ambitious (−12.8 kt). The payback cap no longer binds in 2031-2033; the
   carbon difference is entirely a pre-existing v3.0 numerical artefact: in a year with nothing built the engine
   gives floor area ±2.3e-10 m2 and a soil-share ratio of order ±1e15, hence soil of −16 kt (2031, both versions)
   and −12.8 kt (2032, v3.2) in years with no construction. Non-TL runs have no clip_soil_share guard.

Deterministic runs are unaffected (no negative gross year, no near-zero year): Reference, every L/P run and TL equal
v3.0 exactly (v3.1 equivalence test).
