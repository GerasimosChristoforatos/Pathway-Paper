"""
Time-resolved replacement and repaint emissions (B2, B4) of new construction.

The case-study B2/B4 of every event line is split into events in time
(Building_factors.event_rows: per-event impact = line B / n, at k L / (n + 1)
years after construction, sensitivity k L / n), pooled per typology with the
weights of the carbon factors (outputs/data/factors/factors_events.csv), and kept by
stage component of the event (A1-A3 : A4-A5 : C1-C4, in proportion to the line's
initial stages), material group and decarbonisation path.

At the calendar year y of an event, each component follows its own factor
(author decisions, ASSUMPTIONS):
  A1-A3  the item's Horup et al. (2025) S4 path (paint and recoating: EPS proxy),
         with the same item-level rules and sensitivities as initial construction;
  A4-A5  the generic path e^(-0.01 (y - 2025)) of Resch et al. (2021) Table 1
         (DECARB_A45 'resch'), held at 2025 ('held') or the item's S4 path ('item');
  C1-C4  held at 2025 (no source for end-of-life decarbonisation).
Factors are defined to 2050. Events after 2050 are committed emissions, reported
as a range: upper = 2025 factors throughout; lower = the 2050 factors held
constant after 2050 (no extrapolation beyond 2050).

kernel(): K[i, j] = kg CO2e per m2 of the cohort built in years[i] that occurs in
years[j] (within the window); engine.forward adds gfa_t @ K to the carbon of year j.
"""
import numpy as np
import pandas as pd

import Building_factors as BF

COMPONENTS = BF.EVENT_COMPONENTS
LAST_FACTOR_YEAR = BF.DECARB_YEARS[-1]                 # 2050


def load_profile(timing='n+1', path=None):
    """Pooled events by typology (outputs/data/factors/factors_events.csv)."""
    d = pd.read_csv(path or BF.OUT_EVENTS)
    d = d[d['Timing'] == timing].drop(columns='Timing')
    if d.empty:
        raise ValueError(f"No events for timing '{timing}' (run Building_factors.py).")
    return d


def c14_split(path=None):
    """End-of-life (C1-C4) factors per typology (kg CO2e per m2 at 2025), split by material chemistry
    (Building_factors.C14_HELD_CLASSES): {'held': {typology: kg/m2}, 'energy': {typology: kg/m2}}, from the pooled
    item-class factors (outputs/data/factors/factors_material_class.csv)."""
    cls = pd.read_csv(path or BF.OUT_CLASS)
    c = cls[cls['Stage'] == 'C1-C4']
    held = c[c['Class'].isin(BF.C14_HELD_CLASSES)].groupby('Typology')['kgCO2e_per_m2'].sum()
    tot = c.groupby('Typology')['kgCO2e_per_m2'].sum()
    return dict(held={t: float(held.get(t, 0.0)) for t in tot.index},
                energy={t: float(tot[t] - held.get(t, 0.0)) for t in tot.index})


def c14_committed(gfa_cohorts, held, energy, hold='2050', a45='resch'):
    """Committed end of life (kg) of cohorts of floor area gfa_cohorts (m2; all of it after 2050): the held part
    (material carbon released at disposal) at 2025 factors in both bounds; the energy part at 2025 factors (hold='2025',
    upper bound) or at the generic construction-stage path e^(-0.01 (t - 2025)) at LAST_FACTOR_YEAR, held after it
    (hold='2050', lower bound; the rule of row_factors). The energy part follows the A4-A5 path, so with
    a45 = 'held' (A4-A5 not decarbonised; the 2025-factor runs) it is held as well. Returns (total, held part, energy
    part)."""
    if hold not in ('2025', '2050'):
        raise ValueError(f"c14_committed: hold {hold!r} (one of '2025', '2050').")
    f = 1.0 if (hold == '2025' or a45 == 'held') else float(BF.generic_path([LAST_FACTOR_YEAR])[0])
    a = float(np.sum(gfa_cohorts))
    return a * (held + f * energy), a * held, a * f * energy


def row_factors(prof, years, decarb_mode, item_case='central', a45='resch', hold='2050'):
    """Factor of each profile row in each calendar year (rows x years). Years after
    LAST_FACTOR_YEAR take the LAST_FACTOR_YEAR factor (hold='2050', lower bound of
    committed emissions) or 1 (hold='2025', upper bound)."""
    years = np.asarray(years)
    yy = np.minimum(years, LAST_FACTOR_YEAR)
    paths = BF.decarb_paths()
    gen = BF.generic_path(yy)
    out = np.ones((len(prof), len(years)))

    def item_path(s4, label, nz):
        if decarb_mode == 'none':
            return None
        if s4 == BF.ITEM_HELD:
            s4 = None
        if (item_case == 'proxies_held' and label == 'proxy') or (item_case == 'nz_elec_held' and nz == 'yes'):
            s4 = None
        return None if s4 is None else paths.loc[yy, s4].values

    for k, r in enumerate(prof.itertuples(index=False)):
        if r.Component == 'A1-A3' or (r.Component == 'A4-A5' and a45 == 'item'):
            f = item_path(r.S4, r.label, r.nz)
            if f is not None:
                out[k] = f
        elif r.Component == 'A4-A5' and a45 == 'resch':
            out[k] = gen
        elif r.Component == 'A4-A5' and a45 != 'held':
            raise ValueError(f"Unknown DECARB_A45 '{a45}'.")
    if hold == '2025':
        out[:, years > LAST_FACTOR_YEAR] = 1.0
    return out


def kernel(prof_t, years, factors, by_material=False):
    """K[i, j]: kg/m2 of the cohort built in years[i] occurring in years[j] (j > i,
    cohorts from years[1] on; the first year is the observed anchor). prof_t: the
    rows of one typology; factors: row_factors(prof_t, years, ...). With
    by_material, a dict {material: K}."""
    years = np.asarray(years)
    n = len(years)
    age = prof_t['Age'].to_numpy(int)
    kg = prof_t['kg_per_m2'].to_numpy(float)
    mats = prof_t['Material'].to_numpy()
    out = {}
    for m in (sorted(set(mats)) if by_material else [None]):
        sel = np.ones(len(prof_t), bool) if m is None else mats == m
        K = np.zeros((n, n))
        for i in range(1, n):
            for j in range(i + 1, n):
                hit = sel & (age == years[j] - years[i])
                if hit.any():
                    K[i, j] = float((kg[hit] * factors[hit, j]).sum())
        out[m] = K
    return out if by_material else out[None]


def component_kernels(prof_t, years, factors, component='A1-A3'):
    """(K of the rows of `component`, K of the other rows) of one typology's profile (kernel()); their sum is the
    kernel of all rows. Used by lever L10 (MODEL v4.9.0), which scales the A1-A3 component of the in-window events."""
    a = (prof_t['Component'] == component).to_numpy()
    return (kernel(prof_t[a].reset_index(drop=True), years, factors[a]),
            kernel(prof_t[~a].reset_index(drop=True), years, factors[~a]))


def committed(gfa, years, prof_t, factors_after, end_year=None):
    """Events after the window of the cohorts built in years[1:]: kg per cohort sum.
    gfa: floor area by cohort (array over years); factors_after: row_factors over the
    calendar years (years[-1] + 1 .. end_year). Returns total kg."""
    years = np.asarray(years)
    end_year = end_year or int(years[-1] + prof_t['Age'].max())
    after = np.arange(years[-1] + 1, end_year + 1)
    age = prof_t['Age'].to_numpy(int)
    kg = prof_t['kg_per_m2'].to_numpy(float)
    tot = 0.0
    for i in range(1, len(years)):
        for j, y in enumerate(after):
            hit = age == y - years[i]
            if hit.any():
                tot += gfa[i] * float((kg[hit] * factors_after[hit, j]).sum())
    return tot


def age_profile(prof_t, max_age=None):
    """Events at 2025 factors by age (kg/m2), all components."""
    a = prof_t.groupby('Age')['kg_per_m2'].sum()
    return a.reindex(range(0, int(max_age or a.index.max()) + 1), fill_value=0.0)
