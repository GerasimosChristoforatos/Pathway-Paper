"""MODEL v4.3.1: the user palette file (palette.toml, read by figures/style.py only).

* palette.toml has exactly the five groups and keys of style.PALETTE_KEYS, as "#RRGGBB";
* the defaults are the colours of the v4.3.0 figures;
* style.load_palette rejects a missing key, an unknown key and a value that is not "#RRGGBB";
* decoupling: a palette that changes one key changes only the style constants of that meaning (checked in a fresh
  process for a key whose default hex is shared with other meanings)."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from figures import style as S  # noqa: E402

V430 = {'demand_bands': dict(population_growth='#586E71', household_size_change='#F4D168', extra_space='#DFA538',
                             vacancy='#AA7C9D', net_replacement='#D0BBDC', market_balance='#683861',
                             maintenance='#9E9E9E'),
        'materials': dict(timber='#750787', steel='#004DFF', concrete='#008026', plastics_paint='#FFED00',
                          plasterboard='#FF8C00', others='#E40303', soil_carbon_loss='#B5A48B'),
        'life_cycle_stages': dict(a1_a3='#4A6192', a4_a5='#ABD3FA', soil_carbon_loss='#8D6545', maintenance='#9E9E9E',
                                  committed_b2_b4='#9E9E9E', committed_c1_c4='#D0D0D0'),
        'runs': dict(reference='#4D4D4D', moderate='#EB6123', ambitious='#A8400C', theoretical_limit='#13412B'),
        'strategies': dict(avoid='#DFA538', switch='#8D6545', improve='#4A6192')}


def test_default_palette_is_v4_3_0():
    p = S.load_palette(S.PALETTE_DEFAULT)
    assert {g: list(k) for g, k in p.items()} == {g: list(k) for g, k in S.PALETTE_KEYS.items()}
    assert p == V430


@pytest.mark.parametrize('bad, msg', [('extra_space     = "#DFA538"', 'missing key'),
                                      ('extra_space = "#DFA5"', 'not a "#RRGGBB"'),
                                      ('extra_space = "#DFA538"\nextra_spaces = "#000000"', 'unknown key')])
def test_load_palette_rejects(tmp_path, bad, msg):
    src = open(S.PALETTE_DEFAULT).read()
    line = next(x for x in src.splitlines() if x.startswith('extra_space'))
    txt = src.replace(line, '' if msg == 'missing key' else bad)
    f = tmp_path / 'p.toml'
    f.write_text(txt)
    with pytest.raises(S.PaletteError, match=msg):
        S.load_palette(str(f))


PROBE = """
import json, os, sys
sys.path.insert(0, {root!r})
from figures import style as S
print(json.dumps(dict(extra_space=S.DISPLAY_BAND['extra_space'], band_extra=S.BAND['extra_space'][0],
                      avoid=S.STRATEGY['S1'], detached=S.TYPOLOGY['Detached'], lever_L4=S.LEVER['L4'],
                      moderate=S.PATHWAY_SETTING['moderate'], pathway=S.PATHWAY['pathway'],
                      tornado_high=S.TORNADO_HIGH, a1a3=S.STAGE['a1a3'][0], improve=S.STRATEGY['S3'],
                      tornado_low=S.TORNADO_LOW)))
"""


def _style_with(tmp_path, group, key, value):
    src, out, cur = open(S.PALETTE_DEFAULT).read().splitlines(), [], None
    for line in src:
        if line.startswith('['):
            cur = line.split(']')[0][1:]
        if cur == group and line.split('=')[0].strip() == key:
            line = f'{key} = "{value}"'
        out.append(line)
    f = tmp_path / f'{group}_{key}.toml'
    f.write_text('\n'.join(out) + '\n')
    env = dict(os.environ, PATHWAY_PALETTE=str(f), MPLBACKEND='Agg')
    r = subprocess.run([sys.executable, '-c', PROBE.format(root=ROOT)], env=env, capture_output=True, text=True,
                       check=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_one_key_changes_only_its_meaning(tmp_path):
    base = _style_with(tmp_path, 'strategies', 'avoid', V430['strategies']['avoid'])
    probe = '#00FFFF'
    s = _style_with(tmp_path, 'strategies', 'avoid', probe)          # shares #DFA538 with Extra space, L4, Detached
    assert s['avoid'] == probe
    assert {k: v for k, v in s.items() if k != 'avoid'} == {k: v for k, v in base.items() if k != 'avoid'}
    e = _style_with(tmp_path, 'demand_bands', 'extra_space', probe)
    assert e['extra_space'] == e['band_extra'] == probe
    assert {k: v for k, v in e.items() if k not in ('extra_space', 'band_extra')} == \
           {k: v for k, v in base.items() if k not in ('extra_space', 'band_extra')}
    m = _style_with(tmp_path, 'runs', 'moderate', probe)              # the tornado high end no longer follows it
    assert m['moderate'] == m['pathway'] == probe and m['tornado_high'] == base['tornado_high']
    i = _style_with(tmp_path, 'strategies', 'improve', probe)        # nor the A1-A3 stage or the tornado low end
    assert i['improve'] == probe and i['a1a3'] == base['a1a3'] and i['tornado_low'] == base['tornado_low']
