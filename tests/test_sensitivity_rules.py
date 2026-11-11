"""The rules of the one-at-a-time sensitivities and the SF7 comparison:

  * every row that reports a level of exceedance is classified in boundaries.AR_BASE_RULE;
  * a 'reference_base' row of the Fig7a tornado uses the Reference AR budget (to the rounding of the CSV);
  * a 'recompute' row's I_sec,base is the Monte Carlo base function (boundaries.base_with_factors) at the row's factors,
    and the central factors of boundaries.reference_factors are those of the Monte Carlo set-up;
  * the global-impact sensitivity (EF 3.1) scales the cumulative LoE of AR by I_glob(A) / I_glob(EF 3.1) and leaves AtP;
  * the like-for-like zero-lag run of SF7 uses the adopted (17-month) net replacement calibration.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

import layout
from conftest import ROOT, run_boss  # noqa: F401


def _data(rel):
    return layout.data(rel)


def _js(rel):
    with open(_data(rel)) as f:
        return json.load(f)


@pytest.fixture(scope='module')
def BD():
    import boundaries
    return boundaries


def test_every_loe_row_is_classified(BD):
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sensitivity_tables as T
    keys = [row for _, row in T.TORNADO]
    keys += [c for c in pd.read_csv(_data('aesa/sensitivity.csv'))['case'] if c != 'reference']
    keys += [case for *_, case, _ in T.PB_ROWS]
    pc = pd.read_csv(_data('sensitivity/pathway_carbon.csv'))
    keys += [g if g in BD.AR_BASE_RULE else r for g, r in zip(pc['group'], pc['row'])]
    keys += list(pd.read_csv(_data('sensitivity/household_size.csv'))['row'].unique())
    keys += [r[1] for r in T.REF_ROWS]
    missing = sorted({k for k in keys if k not in BD.AR_BASE_RULE})
    assert not missing, f'unclassified one-at-a-time rows: {missing}'
    assert {r for r, _ in BD.AR_BASE_RULE.values()} == {BD.RECOMPUTE, BD.REFERENCE_BASE}
    with pytest.raises(SystemExit):
        BD.ar_base_rule('a row that does not exist')


def test_reference_base_rows_use_the_reference_budget(BD):
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sensitivity_tables as T
    a = pd.read_csv(_data('aesa/annual.csv'))
    a = a[(a['scenario'] == 'REF') & (a['year'] >= 2026)]
    bar = a['B_AR_kgCO2e'].sum() / 1e6
    t = pd.read_csv(_data('sensitivity/tornado.csv'))
    rows = dict(T.TORNADO)
    n = 0
    for x in t.itertuples():
        rule = BD.ar_base_rule(rows[x.input])[0]
        if rule == BD.REFERENCE_BASE and not x.input.startswith('Population'):
            # the Reference budget (to 1e-14: carbon_kt is read back from the CSV, one rounding unit)
            assert x.carbon_kt / x.LoE_AR == pytest.approx(bar, rel=1e-14, abs=0), x.input
            n += 1
        elif rule == BD.RECOMPUTE and x.case != 'central':    # a one-sided row's low end is the Reference
            assert x.carbon_kt / x.LoE_AR != pytest.approx(bar, rel=1e-6), x.input
    assert n > 0


def test_recompute_rows_use_the_monte_carlo_base_function(BD, B):
    import projection
    typ = list(B['typ_names'])
    i_base, hist = BD.window_base(B, BD.AR_BASE_WINDOW)
    up, age = BD.reference_factors(B, typ)
    assert BD.base_with_factors(hist, typ, up, BD.AR_BASE_WINDOW, age) == pytest.approx(i_base, rel=1e-12)
    oat = _js('aesa/results.json')['one_at_a_time_ar_base']
    tf = pd.read_csv(projection.FILE_FACTORS_TYPOLOGY).set_index('Typology').loc[typ]
    emb0 = tf['embodied_materials'].values
    cols = {'Case studies: jackknife low / high': ('emb_jackknife_min', 'emb_jackknife_max'),
            'Single case study: lowest / highest': ('emb_building_min', 'emb_building_max')}
    for row, (lo, hi) in cols.items():
        assert oat[row]['rule'] == BD.RECOMPUTE
        for side, col in (('low', lo), ('high', hi)):
            k = tf[col].values / emb0
            want = BD.base_with_factors(hist, typ, up * k, BD.AR_BASE_WINDOW, age * k[:, None])
            assert oat[row]['sides'][side]['I_sec_base_kg'] == pytest.approx(want, rel=1e-12)
    soil = hist['I_soil_on_all_kg'] - hist['I_sec_kg'] + hist['soil_kg']
    want = BD.base_with_factors(hist.assign(soil_kg=soil), typ, up, BD.AR_BASE_WINDOW, age)
    got = oat['Soil carbon loss on all floor area, including replacement']['sides']['single']['I_sec_base_kg']
    assert got == pytest.approx(want, rel=1e-12)
    Bn = run_boss(EVENT_TIMING='n')
    want = BD.base_with_factors(hist, typ, up, BD.AR_BASE_WINDOW, BD.reference_factors(Bn, typ)[1])
    assert oat['Event timing L / n']['sides']['single']['I_sec_base_kg'] == pytest.approx(want, rel=1e-12)


def test_reference_factors_are_the_monte_carlo_central_factors(BD, B):
    import MonteCarlo as MC
    su = MC.build_setup(dict(MC.MC_SCENARIOS)['REF'])
    up, age = BD.reference_factors(B, list(B['typ_names']))
    assert np.array_equal(up, su['up_central'])
    assert np.array_equal(age, su['age_central'])


def test_global_impact_ef31_scales_ar_only(BD):
    s = pd.read_csv(_data('aesa/sensitivity.csv')).set_index('case')
    pa, pe = BD.SOURCE_PAIRS[BD.SOURCE_PAIR], BD.SOURCE_PAIRS['EF31']
    assert pe['i_glob'] == BD.I_GLOB_EF31_PER_PERSON * BD.I_GLOB_EF31_POPULATION
    assert pe['sos'] == pa['sos']
    ratio = s.loc['i_glob_ef31', 'cum_LoE_AR'] / s.loc['reference', 'cum_LoE_AR']
    assert ratio == pytest.approx(pe['i_glob'] / pa['i_glob'], rel=1e-12)
    assert s.loc['i_glob_ef31', 'cum_LoE_AtP'] == s.loc['reference', 'cum_LoE_AtP']


def test_sf7_like_for_like_run_uses_the_adopted_calibration():
    import projection
    assert projection.NET_REPLACEMENT_HELD is None                   # never set in a reported run
    B17 = run_boss(COMPLETION_LAG_MONTHS=17)
    B0h = run_boss(COMPLETION_LAG_MONTHS=0, NET_REPLACEMENT_HELD=B17['census_rates'])
    B0 = run_boss(COMPLETION_LAG_MONTHS=0)
    assert np.array_equal(B0h['fwd_inputs']['rate_unc'], B17['fwd_inputs']['rate_unc'])
    assert not np.allclose(B0['fwd_inputs']['rate_unc'], B17['fwd_inputs']['rate_unc'])
    s = _js('diagnostics/lag_comparison_summary.json')
    assert s['lag_0_held']['net_replacement_held'] and not s['lag_0']['net_replacement_held']
    assert s['lag_0_held']['recent_net_replacement_rate_used'] == s['lag_17']['recent_net_replacement_rate_used']
    d = pd.read_csv(_data('diagnostics/lag_comparison_annual.csv'))
    assert set(d['run']) == {'lag_0', 'lag_0_held', 'lag_17'}
