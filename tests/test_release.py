"""Release checks of MODEL v1.0.0.

1. The values the release adds (annual component split, annual and census-interval demand
   bands, the annual series of the projection variants, the population paths of the AESA
   layer) agree with the numbers locked by tests/test_regression_model_v1.py: the H4
   components add up exactly to the captured annual carbon, the bands to the captured band
   totals, the variants to the captured variant totals.
2. The headline set: every figure of figure_plan.HEADLINE exists as PNG, PDF and source data
   (CSV), and HEADLINE.md shows every one with a filled caption.
"""
import json
import math
import os

import numpy as np
import pandas as pd
import pytest

from conftest import ROOT

import figure_plan as FP
import layout as L
import naming as N

CAP = json.load(open(os.path.join(ROOT, 'tests', 'regression_model_v1.json')))
quick = pytest.mark.skipif(os.environ.get('PATHWAY_QUICK') == '1', reason='quick run: Monte Carlo outputs differ')


def data(rel):
    return L.data(rel, frozen=False)


def captured(old_file, path):
    return CAP['files'][old_file]['values'][path]


# ---- 1. additions agree with the locked numbers ------------------------------------------------
def test_h4_components_add_up_to_the_captured_annual_carbon():
    """carbon = materials and construction + soil carbon loss + maintenance in every year, and the
    annual carbon is the captured one (boss_results.json annual/carbon_kt at ee37ef1)."""
    an = pd.read_csv(data('baseline/annual.csv'))
    p = an[an['source'] == 'projection'].reset_index(drop=True)
    comp = p['materials_construction_kt'] + p['soil_carbon_loss_kt'] + p['maintenance_kt']
    assert np.allclose(comp, p['carbon_kt'], rtol=1e-12, atol=0)
    years = [captured('boss_results.json', f'annual/years/{i}') for i in range(26)]
    cap = {y: captured('boss_results.json', f'annual/carbon_kt/{i}') for i, y in enumerate(years)}
    assert list(p['year']) == years[1:]
    assert np.allclose(p['carbon_kt'], [cap[y] for y in p['year']], rtol=1e-12, atol=0)
    assert math.isclose(p['soil_carbon_loss_kt'].sum(), captured('boss_results.json', 'soil_kt'), rel_tol=1e-12)
    assert math.isclose(p['maintenance_kt'].sum(), captured('boss_results.json', 'b_inwindow_kt'), rel_tol=1e-12)
    assert math.isclose((p['materials_construction_kt'] + p['soil_carbon_loss_kt']).sum(),
                        captured('boss_results.json', 'upfront_kt'), rel_tol=1e-12)
    hist = an[an['source'] == 'history']
    assert hist['carbon_kt'].isna().all()                     # no historical carbon


def test_annual_bands_add_up_to_the_band_totals():
    """The annual in-scope bands of the Reference add up, over 2026-2050, to the in-scope band totals of
    the Reference run in data/pathways/bands.csv (locked) and, in every year, to the annual totals."""
    ba = pd.read_csv(data('baseline/bands_annual.csv'))
    bd = pd.read_csv(data('pathways/bands.csv'))
    bd = bd[(bd['run'] == 'REF') & (bd['scenario'] == 'REF') & (bd['definition'] == 'in_scope')].set_index('band')
    tot = ba.groupby('band')[['floor_area_Mm2', 'carbon_kt']].sum()
    assert list(dict.fromkeys(ba['band'])) == [N.band_data_label(b) for b in N.BANDS_IN_SCOPE]
    for b in tot.index:
        for c in ('floor_area_Mm2', 'carbon_kt'):
            assert tot.loc[b, c] == pytest.approx(bd.loc[b, c], rel=1e-9, abs=1e-9), (b, c)
    an = pd.read_csv(data('baseline/annual.csv'))
    p = an[an['source'] == 'projection'].set_index('year')
    by_year = ba.groupby('year')[['floor_area_Mm2', 'carbon_kt']].sum()
    assert np.allclose(by_year['floor_area_Mm2'], p['floor_area_Mm2'], rtol=1e-12, atol=0)
    assert np.allclose(by_year['carbon_kt'], p['carbon_kt'], rtol=1e-12, atol=0)


def test_variant_annual_series_add_up_to_the_variant_totals():
    va = pd.read_csv(data('baseline/variants_annual.csv'))
    sc = json.load(open(data('baseline/scenarios.json')))['scenarios']
    for k, g in va.groupby('variant'):
        assert g['floor_area_Mm2'].sum() == pytest.approx(sc[k]['floor_area_Mm2'], rel=1e-12), k
        assert g['carbon_kt'].sum() == pytest.approx(sc[k]['carbon_kt'], rel=1e-12), k
    assert set(va['variant']) == set(sc)
    an = pd.read_csv(data('baseline/annual.csv'))
    p = an[an['source'] == 'projection']
    r = va[va['variant'] == 'REF']
    assert np.allclose(r['floor_area_Mm2'].values, p['floor_area_Mm2'].values, rtol=1e-12, atol=0)


def test_history_bands_by_census_interval():
    h = pd.read_csv(data('baseline/bands_history.csv'))
    assert list(dict.fromkeys(h['band'])) == [N.band_data_label(b) for b in N.BANDS_HISTORY]
    first = h.groupby('interval', sort=False).first()
    assert list(first['year_start']) == sorted(first['year_start'])
    assert (first['year_end'] >= first['year_start']).all()
    assert h['floor_area_Mm2_per_year'].notna().all()


def test_population_paths_reproduce_the_reference():
    r = json.load(open(data('aesa/results.json')))
    pp, d = r['population_paths'], r['deterministic']['REF']
    for k in ('LoE_AR', 'LoE_AtP', 'I_kt'):
        assert pp['50th'][k] == pytest.approx(d[k], rel=1e-12), k
    assert pp['5th']['I_kt'] < d['I_kt'] < pp['95th']['I_kt']
    assert pp['5th']['B_AR_kt'] < pp['50th']['B_AR_kt'] < pp['95th']['B_AR_kt']


# ---- 2. headline set ---------------------------------------------------------------------------
@pytest.mark.parametrize('h', FP.HEADLINE, ids=[h['id'] for h in FP.HEADLINE])
def test_headline_figure_files(h):
    for ext in ('png', 'pdf', 'csv'):
        p = os.path.join(L.HEADLINE, f"{h['file']}.{ext}")
        assert os.path.exists(p) and os.path.getsize(p) > 0, p
    src = pd.read_csv(os.path.join(L.HEADLINE, f"{h['file']}.csv"))
    assert list(src.columns) == ['panel', 'series', 'x', 'value', 'unit'] and len(src) > 0


def test_headline_md_shows_every_figure_with_a_filled_caption():
    md = open(os.path.join(L.HEADLINE, 'HEADLINE.md'), encoding='utf-8').read()
    for h in FP.HEADLINE:
        assert f"![{h['id']}]({h['file']}.png)" in md, h['id']
    import re
    assert not re.search(r'\{[a-z_0-9]+(:[^}]*)?\}', md), 'unfilled caption placeholder'
    findings = md.split('## Findings')[1].split('## Figures')[0]
    n = sum(1 for line in findings.splitlines() if line[:2].rstrip('.').isdigit())
    assert 6 <= n <= 8, n
