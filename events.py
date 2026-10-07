"""
Time-resolved replacement and repaint emissions (B2, B4) of new construction.

The case-study B2/B4 of every event line is split into events in time
(Building_factors.event_rows: per-event impact = line B / n, at k L / (n + 1)
years after construction, sensitivity k L / n), pooled per typology with the
weights of the carbon factors (outputs/factors/factors_events.csv), and kept by
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
    """Pooled events by typology (outputs/factors/factors_events.csv)."""
    d = pd.read_csv(path or BF.OUT_EVENTS)
    d = d[d['Timing'] == timing].drop(columns='Timing')
    if d.empty:
        raise ValueError(f"No events for timing '{timing}' (run Building_factors.py).")
    return d


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
