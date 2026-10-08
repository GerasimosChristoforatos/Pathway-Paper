"""baseline-pb-v2 clean-up: three replacement scenarios only (Low (S1), Reference
(S3-10), High (S2), typology shares held), Low and Reference unchanged from
baseline-pb-v1.2 under the v2 accounting (tests/regression_pb_v1_2_low_ref.json, tag
baseline-PB_v1.2),
main-text tornados with the top-5 effects, Pride colours for the six material
classes in one order, soil always the top layer."""
import json
import os
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from conftest import ROOT, run_boss  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'tools'))

OUT = os.path.join(ROOT, 'outputs')
FX = json.load(open(os.path.join(ROOT, 'tests', 'regression_pb_v1_2_low_ref.json')))
NAMES = {'S1': 'Low (S1)', 'S3-10': 'Reference (S3-10)', 'S2': 'High (S2)'}
PRIDE = ['#750787', '#004DFF', '#008026', '#FFED00', '#FF8C00', '#E40303']   # bottom -> top of the stack


def test_stale_terms_absent_from_outputs():
    """Outputs written before the tests step; the documents written after it
    (metrics, RESULTS, drafts, ASSUMPTIONS) are checked by tools/check_outputs.py,
    the last step of run_all.py."""
    import check_outputs
    hits = check_outputs.storyline_hits(include_docs=False)
    assert not hits, hits


def test_mix_held_in_every_scenario():
    import Boss
    import MonteCarlo as MC
    import replacement_scenarios as RS
    assert Boss.MIX_MODE == 'held'
    assert [k for k, _ in MC.MC_SCENARIOS] == ['S3-10', 'S1', 'S2']
    assert not any('MIX_MODE' in s for _, s in MC.MC_SCENARIOS)
    assert not any('MIX_MODE' in s for _, _, s in RS.SCENARIOS)
    assert run_boss(REPLACEMENT_SCENARIO='S2')['mix_used'] == 'held'


def test_scenario_names_consistent():
    import figures_report as FR
    import replacement_scenarios as RS
    assert [(k, lab) for k, lab, *_ in FR.SCEN] == list(NAMES.items())
    labels = {k: lab for k, lab, _ in RS.SCENARIOS}
    for k, name in NAMES.items():
        assert labels[k].startswith(name), (k, labels[k])
    sc = json.load(open(os.path.join(OUT, 'replacement_scenarios.json')))['scenarios']
    for k, name in NAMES.items():
        assert sc[k]['label'].startswith(name)


def test_low_and_reference_deterministic_unchanged():
    """Under the v2 accounting (whole life at construction, A4-A5 held), Low and
    Reference reproduce baseline-pb-v1.2 exactly. (Their Monte Carlo and PB outputs
    change deliberately in baseline-pb-v3: time-resolved accounting, CHANGELOG.)"""
    import replacement_scenarios as RS
    settings = {k: s for k, _, s in RS.SCENARIOS}
    for k, ref in FX['scenarios'].items():
        r, _ = RS.one(dict(settings[k], ACCOUNTING='whole_life_at_construction', DECARB_A45='held'))
        for f, v in ref.items():
            assert r[f] == v, (k, f, r[f], v)


def test_tornado_top5_parameters():
    """Main-text tornados: all rows of the 5 parameters with the largest absolute effect
    (sens_1: on carbon; pb_4: on AR or AtP), both ends of a paired parameter shown."""
    import PB
    import Sensitivity as S
    d = pd.DataFrame(dict(case=['a_lo', 'a_hi', 'b', 'c', 'd', 'e', 'f', 'g_lo', 'g_hi'], group='Stock',
                          GFA_change_pct=[0, 0, 0, 0, 0, 0, 50, 0, 0],
                          carbon_change_pct=[-1, 9, 8, 7, 6, 2, 0.1, 5, -0.5]))
    par = {'a_lo': 'a', 'a_hi': 'a', 'g_lo': 'g', 'g_hi': 'g'}
    top = S.top_parameters(d, 5, parameter=par)
    assert S.TOP_N == 5 and set(top.case) == {'a_lo', 'a_hi', 'b', 'c', 'd', 'g_lo', 'g_hi'}   # f: floor area only
    assert list(top.case) == list(top.sort_values('order').case)
    p = pd.DataFrame(dict(case=['iii_base_window', 'iii_base_window_20', 'iii_base_window_full', 'i_source_pair',
                                'ii_gdp_measure', 'v_ssec', 'vi_frozen', 'xiv_alpha_1', 'vii_proxies_held'],
                          AR_vs_ref_pct=[-2, 20, 22, 88, 0, 0, 14, 0, 0.4],
                          AtP_vs_ref_pct=[0, 0, 0, 88, 207, 0.2, 14, -58, 0.4]))
    assert PB.TOP_N == 5
    assert set(PB.top_rows(p, 5).case) == {'iii_base_window', 'iii_base_window_20', 'iii_base_window_full',
                                          'i_source_pair', 'ii_gdp_measure', 'vi_frozen', 'xiv_alpha_1'}
    assert 'xii_whole_life' in PB.MAIN_EXCLUDED


def test_whole_life_row_only_in_pb_sensitivity():
    import Sensitivity as S
    assert not any('whole life' in lab.lower() for _, lab, _ in S.CASES + S.DECARB_CASES['horup_item'])
    oat = pd.read_csv(os.path.join(OUT, 'sensitivity_oat.csv'))
    assert not oat['case'].str.contains('whole life', case=False).any()
    pb = pd.read_csv(os.path.join(OUT, 'pb_sensitivity.csv'))
    assert (pb['case'] == 'xii_whole_life').sum() == 1


def test_pride_colours_in_one_order():
    import Boss
    style = Boss.MATERIAL_STYLE
    assert [c for _, _, c in style[:-1]] == PRIDE
    assert [col for col, _, _ in style] == ['TIMBER', 'STEEL', 'CONCRETE (incl. reinforced)', 'PLASTICS & PAINT',
                                            'PLASTERBOARD', 'OTHERS', 'SOIL']
    # every per-material figure draws through Boss.stack_materials / Boss.material_patch
    for f in ('Diagnostics.py', 'Boss.py', 'PB.py', os.path.join('tools', 'figures_report.py')):
        src = open(os.path.join(ROOT, f), encoding='utf-8').read()
        assert not re.search(r"'#8B5A2B'|'#8E9296'|'#2EE62E'", src), f      # the pre-v2 material colours


def test_soil_is_the_top_layer():
    import Boss
    frame = pd.DataFrame({col: np.full(3, 1.0) for col, _, _ in Boss.MATERIAL_STYLE})
    fig, ax = plt.subplots()
    handles = Boss.stack_materials(ax, [2026, 2027, 2028], frame)
    assert handles[0].get_label() == 'Soil (land-use change)'            # legend: top first
    polys = ax.collections
    assert polys[-1].get_label() == 'Soil (land-use change)' and polys[-1].get_hatch()
    tops = [p.get_paths()[0].vertices[:, 1].max() for p in polys]
    assert tops == sorted(tops) and tops[-1] == len(Boss.MATERIAL_STYLE)
    colours = [matplotlib.colors.to_hex(p.get_facecolor()[0][:3]).upper() for p in polys[:-1]]
    assert colours == PRIDE
    plt.close(fig)
