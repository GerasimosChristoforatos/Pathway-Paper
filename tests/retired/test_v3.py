"""baseline-pb-v3: time-resolved B2/B4 (replacement and repaint events), committed
post-2050 emissions, A4-A5 decarbonisation. Checks: the event table reproduces the
supplied tables; events per line equal the counts and add up to the line B2/B4;
within-window + committed (2025 factors) = whole-life total; the
whole-life-at-construction accounting with A4-A5 held reproduces baseline-pb-v2
and 'none' the frozen anchor (tests/regression_pb_v2.json, tag baseline-PB_v2);
soil unchanged; the A4-A5 path is Resch et al.'s e^(-0.01 (t - 2025)); every figure
file is planned (figure_plan.py); no figure shows carbon before 2026 except the AR base
window of D21 (at 2025 factors)."""
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT, run_boss

import Building_factors as BF  # noqa: E402

FX = json.load(open(os.path.join(ROOT, 'tests', 'regression_pb_v2.json')))
EV = pd.read_csv(BF.FILE_EVENTS).fillna({'event_type': '', 'event_path': ''})
ITEMS = pd.read_csv(BF.FILE_ITEMS)
WHOLE_LIFE = dict(ACCOUNTING='whole_life_at_construction', DECARB_A45='held')


@pytest.fixture(scope='module')
def tr_frozen():
    return run_boss(DECARB_MODE='none', DECARB_A45='held')


def test_event_lines_reproduce_the_item_table():
    """B2/B4 of the matched workbook lines equals the item table for every building x
    class x item; the other stages too, except the one T_1 aluminium line (10 kg A1-A3,
    excluded with the 15 site-works / unlabelled lines)."""
    st = ['A1-A3', 'A4-A5', 'B2,B4', 'C1-C4']
    a = EV.groupby(['id', 'class', 'item'])[st].sum()
    b = ITEMS.set_index(['id', 'class', 'item'])[st].groupby(level=[0, 1, 2]).sum()
    j = b.join(a, rsuffix='_ev', how='outer').fillna(0.0)
    assert np.allclose(j['B2,B4'], j['B2,B4_ev'], rtol=0, atol=1e-6)
    off = j[(np.abs(j[st].values - j[[f'{s}_ev' for s in st]].values) > 1e-6).any(axis=1)]
    assert len(off) == 1 and off.index[0][0] == 'T_1' and off.index[0][1] == 'ALUMINIUM'
    excl = pd.read_csv(os.path.join(ROOT, 'data', 'derived', 'lca_excluded_lines.csv'))
    assert len(excl) == 16 and (excl['B2,B4'] == 0).all()


def test_events_per_line_equal_the_counts():
    rep = EV['event_type'] == 'replacement'
    rpt = EV['event_type'] == 'repaint'
    assert (EV.loc[rep, 'n_events'] == EV.loc[rep, 'n_replacements']).all()
    assert (EV.loc[rpt, 'n_events'] == EV.loc[rpt, 'n_repaints']).all()
    assert ((EV['B2,B4'] > 0) == (EV['n_events'] > 0)).all()
    assert (EV.loc[EV['class'] == 'PAINT', 'event_type'].isin(['repaint', ''])).all()


@pytest.mark.parametrize('timing', list(BF.EVENT_TIMINGS))
def test_events_add_up_to_line_b(timing):
    r = BF.event_rows(timing)
    tot = r.groupby('id')['kg'].sum()
    ref = EV[EV['n_events'] > 0].groupby('id')['B2,B4'].sum()
    assert np.allclose(tot.reindex(ref.index).values, ref.values, rtol=1e-12)
    assert r['Age'].between(1, 50).all()
    pooled = pd.read_csv(BF.OUT_EVENTS)
    mf = pd.read_csv(BF.OUT_MATERIAL)
    bfac = mf[mf.Stage == 'B2,B4'].groupby('Typology')['kgCO2e_per_m2'].sum()
    p = pooled[pooled.Timing == timing].groupby('Typology')['kg_per_m2'].sum()
    assert np.allclose(p.reindex(bfac.index).values, bfac.values, rtol=1e-12)


def test_event_timing_first_event():
    """One replacement in a 50-year life: year 25 (L / (n + 1)); six repaints: L / 7."""
    r = BF.event_rows('n+1')
    one = EV[(EV['event_type'] == 'replacement') & (EV['n_events'] == 1)]
    assert len(one) > 0
    single = r[r['id'].isin(one['id']) & (r['Age'] == 25)]
    assert not single.empty                                  # 50 / 2 = 25, integer
    paint = EV[EV['class'] == 'PAINT'].iloc[0]
    rp = r[(r['id'] == paint['id']) & (r['Material'] == 'PLASTICS & PAINT')]
    assert {7, 8} <= set(rp['Age'])                          # 50 / 7 = 7.14: split 0.86 / 0.14


def test_whole_life_with_a45_held_reproduces_v2():
    B = run_boss(**WHOLE_LIFE)
    a = FX['adopted']
    assert B['tot_carbon_median'] == a['carbon_kt']
    assert B['_upfront'] + B['_soil'] / 1e6 == a['upfront_kt']
    assert [float(v / 1e6) for v in B['carbon_total_typ'].sum(axis=1).values] == a['annual_carbon_kt']


def test_none_reproduces_the_frozen_anchor():
    B = run_boss(DECARB_MODE='none', **WHOLE_LIFE)
    f = FX['frozen']
    assert B['tot_carbon_median'] == f['carbon_kt']
    assert [float(v / 1e6) for v in B['carbon_total_typ'].sum(axis=1).values] == f['annual_carbon_kt']


def test_within_window_plus_committed_equals_whole_life(tr_frozen):
    """At 2025 factors: upfront + in-window B + committed B (upper) + C1-C4 = whole life."""
    whole = FX['frozen']['carbon_kt']
    c = tr_frozen['COMMITTED']
    up = tr_frozen['_upfront'] + tr_frozen['_soil'] / 1e6
    assert up + c['B_inwindow_kt'] + c['B_upper_kt'] + c['C_kt'] == pytest.approx(whole, rel=1e-12)
    assert c['B_upper_kt'] == c['B_lower_kt']                    # nothing to decarbonise


def test_soil_unchanged(tr_frozen):
    B = run_boss(**WHOLE_LIFE)
    T = run_boss()
    assert B['_soil'] == T['_soil'] == tr_frozen['_soil']
    assert np.array_equal(B['flow_annual']['SOIL'].values, T['flow_annual']['SOIL'].values)


def test_a45_generic_path():
    y = np.arange(2025, 2051)
    assert np.allclose(BF.generic_path(y), np.exp(-0.01 * (y - 2025)), rtol=0, atol=1e-15)
    assert BF.generic_path([2050])[0] == pytest.approx(0.7788, abs=1e-4)


def test_committed_range_ordered():
    c = run_boss()['COMMITTED']
    assert c['B_lower_kt'] < c['B_upper_kt'] and c['lower_kt'] < c['upper_kt']
    assert c['C_kt'] > 0 and c['B_inwindow_kt'] > 0


def test_every_figure_is_planned():
    """Every figure file in outputs/paper/, outputs/extended_data/ and outputs/diagnostics/ is a figure of figure_plan.py
    (tools/check_outputs.py also refuses to finish otherwise)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import check_outputs
    assert not check_outputs.unplanned_figures()


CARBON_AXIS = re.compile(r'CO₂|CO2|carbon|LoE|exceedance|\bkt\b|\bMt\b', re.I)


def test_no_historical_carbon_in_figures():
    """No figure shows carbon before the projection (from 2026), except the Monte Carlo fan
    with the boundaries (D21) and Fig4 (a), which show the AR base window at 2025 factors (figaudit records,
    written when each figure is saved)."""
    import boundaries
    import layout
    audit = layout.FIGURE_AUDIT
    files = {os.path.splitext(f)[0] for base in (layout.PAPER, layout.EXTENDED_DATA, layout.DIAGNOSTICS)
             for _, _, fs in os.walk(base) for f in fs if f.endswith('.png')}
    recs = {f[:-5]: json.load(open(os.path.join(audit, f))) for f in os.listdir(audit) if f.endswith('.json')}
    assert files and files <= set(recs), sorted(files - set(recs))         # every saved figure audited
    # MODEL v2.1.2: Fig4 (a) shows the same AR base window history as D21 (a thin line joined to the projection)
    allowed = {'D21_fan_and_boundaries': boundaries.AR_BASE_WINDOW[0],
               'Fig4_reference_boundaries': boundaries.AR_BASE_WINDOW[0]}
    bad = []
    for name in files:
        for ax in recs[name]['axes']:
            if ax['year_min'] is None or not CARBON_AXIS.search(ax['ylabel'] + ' ' + ax['title']):
                continue
            if ax['year_min'] < allowed.get(name, 2026):
                bad.append((name, ax['title'][:50], ax['ylabel'][:40], ax['year_min']))
    assert not bad, bad
