"""baseline-pb-v2 clean-up: three replacement scenarios only (Low (S1), Reference
(S3-10), High (S2), typology shares held), Low and Reference unchanged from
baseline-pb-v1.2 under the v2 accounting (tests/regression_pb_v1_2_low_ref.json, tag
baseline-PB_v1.2),
the largest parameters shown with both ends (H11 since MODEL v1.0.0), Pride colours for the six
material classes in one order, soil always the top layer."""
import json
import os
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from conftest import ROOT, run_boss  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'tools'))

import layout  # noqa: E402
FX = json.load(open(os.path.join(ROOT, 'tests', 'regression_pb_v1_2_low_ref.json')))
import naming as N  # noqa: E402

NAMES = {k: N.SCENARIOS[k] for k in ('LOW', 'REF', 'HIGH')}
PRIDE = ['#750787', '#004DFF', '#008026', '#FFED00', '#FF8C00', '#E40303']   # bottom -> top of the stack


def test_stale_terms_absent_from_outputs():
    """Every data file and report (the tests run last in run_all.py; tools/check_outputs.py
    applies the same check during the run)."""
    import check_outputs
    hits = check_outputs.storyline_hits()
    assert not hits, hits


def test_mix_held_in_every_scenario():
    import projection
    import MonteCarlo as MC
    import replacement_scenarios as RS
    assert not hasattr(projection, 'MIX_MODE')                      # the mix is held; no trend code path
    assert [k for k, _ in MC.MC_SCENARIOS] == ['REF', 'LOW', 'HIGH']
    assert not any('MIX_MODE' in s for _, s in MC.MC_SCENARIOS)
    assert not any('MIX_MODE' in s for _, _, s in RS.SCENARIOS)
    sh = run_boss(REPLACEMENT_VARIANT='HIGH')['evolving_gfa_shares']
    assert (sh.loc[2027:].nunique() == 1).all()                       # held after the observed 2026


def test_scenario_names_consistent():
    import figures_report as FR
    import replacement_scenarios as RS
    assert [(k, lab) for k, lab, *_ in FR.SCEN] == list(NAMES.items())
    labels = {k: lab for k, lab, _ in RS.SCENARIOS}
    for k, name in NAMES.items():
        assert labels[k].startswith(name), (k, labels[k])
    sc = json.load(open(layout.data('baseline/scenarios.json', frozen=False)))['scenarios']
    for k, name in NAMES.items():
        assert sc[k]['label'].startswith(name)


def test_low_and_reference_deterministic_unchanged():
    """Under the v2 accounting (whole life at construction, A4-A5 held), Low and
    Reference reproduce baseline-pb-v1.2 exactly. (Their Monte Carlo and PB outputs
    change deliberately in baseline-pb-v3: time-resolved accounting, CHANGELOG.)"""
    import replacement_scenarios as RS
    settings = {k: s for k, _, s in RS.SCENARIOS}
    for k, ref in FX['scenarios'].items():                  # fixture keys: v1.2 scenario ids (S1, S3-10)
        r, _ = RS.one(dict(settings[N.SCENARIO_LEGACY[k]], ACCOUNTING='whole_life_at_construction',
                           DECARB_A45='held'))
        for f, v in ref.items():
            assert r[f] == v, (k, f, r[f], v)


def test_top_parameters_keep_both_ends_of_a_parameter():
    """H11 (headline.py) shows all rows of the parameters with the largest absolute effect, both ends
    of a paired parameter together (Sensitivity.top_parameters); the accounting-convention row
    (whole life) and the reference are not drawn."""
    import headline
    import Sensitivity as S
    d = pd.DataFrame(dict(case=['a_lo', 'a_hi', 'b', 'c', 'd', 'e', 'f', 'g_lo', 'g_hi'], group='Stock',
                          GFA_change_pct=[0, 0, 0, 0, 0, 0, 50, 0, 0],
                          carbon_change_pct=[-1, 9, 8, 7, 6, 2, 0.1, 5, -0.5]))
    par = {'a_lo': 'a', 'a_hi': 'a', 'g_lo': 'g', 'g_hi': 'g'}
    top = S.top_parameters(d, 5, parameter=par)
    assert set(top.case) == {'a_lo', 'a_hi', 'b', 'c', 'd', 'g_lo', 'g_hi'}   # f: floor area only
    assert list(top.case) == list(top.sort_values('order').case)
    assert 'xii_whole_life' in headline.AESA_NOT_DRAWN and 'reference' in headline.AESA_NOT_DRAWN


def test_whole_life_row_only_in_pb_sensitivity():
    import Sensitivity as S
    assert not any('whole life' in lab.lower() for _, lab, _ in S.CASES + S.DECARB_CASES['horup_item'])
    oat = pd.read_csv(layout.data('baseline/sensitivity_one_at_a_time.csv', frozen=False))
    assert not oat['case'].str.contains('whole life', case=False).any()
    pb = pd.read_csv(layout.data('aesa/sensitivity.csv', frozen=False))
    assert (pb['case'] == 'xii_whole_life').sum() == 1


def test_pride_colours_in_one_order():
    import style
    assert [c for _, _, c in style.MATERIAL[:-1]] == PRIDE
    assert [col for col, _, _ in style.MATERIAL] == ['TIMBER', 'STEEL', 'CONCRETE (incl. reinforced)', 'PLASTICS & PAINT',
                                                     'PLASTERBOARD', 'OTHERS', 'SOIL']
    # every per-material figure draws through plotting.stack_materials / plotting.material_patch
    for f in ('Diagnostics.py', 'projection.py', 'boundaries.py', 'headline.py', 'plotting.py',
              os.path.join('tools', 'figures_report.py')):
        src = open(os.path.join(ROOT, f), encoding='utf-8').read()
        assert not re.search(r"'#8B5A2B'|'#8E9296'|'#2EE62E'", src), f      # the pre-v2 material colours


def test_soil_is_the_top_layer():
    import plotting
    import style
    frame = pd.DataFrame({col: np.full(3, 1.0) for col, _, _ in style.MATERIAL})
    fig, ax = plt.subplots()
    handles = plotting.stack_materials(ax, [2026, 2027, 2028], frame)
    soil = [lab for code, lab, _ in style.MATERIAL if code == 'SOIL'][0]
    assert handles[0].get_label() == soil                                   # legend: top first
    polys = ax.collections
    assert polys[-1].get_label() == soil and polys[-1].get_hatch()
    tops = [p.get_paths()[0].vertices[:, 1].max() for p in polys]
    assert tops == sorted(tops) and tops[-1] == len(style.MATERIAL)
    colours = [matplotlib.colors.to_hex(p.get_facecolor()[0][:3]).upper() for p in polys[:-1]]
    assert colours == PRIDE
    plt.close(fig)
