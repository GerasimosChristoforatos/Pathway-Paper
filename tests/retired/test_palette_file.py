"""MODEL v4.3.1: the user palette file (palette.toml, read by figures/style.py only). MODEL v4.3.2: nine groups (the
boundaries, the zones, the Fig3b cumulative column and the one-at-a-time colours added); the lever shades retired.

* palette.toml has exactly the groups and keys of style.PALETTE_KEYS, as "#RRGGBB";
* the defaults are the colours of the v4.3.0 / v4.3.1 figures (the new keys: the fixed literals they replace);
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
# MODEL v4.3.2: the four new groups, each default the literal it replaces in figures/style.py of v4.3.1
V432 = dict(V430, boundaries=dict(acquired_rights='#D7191C', ability_to_pay='#67000D'),
            boundary_zones=dict(within_both='#41AB5D', within_ar_only='#A1D99B', exceeded='#FB6A4A'),
            cumulative=dict(fig3b_cumulative_carbon='#4D4D4D'),
            one_at_a_time=dict(low_end='#4A6192', high_end='#EB6123', single_alternative='#6E6E6E'))


def test_default_palette_is_v4_3_0():
    p = S.load_palette(S.PALETTE_DEFAULT)
    assert {g: list(k) for g, k in p.items()} == {g: list(k) for g, k in S.PALETTE_KEYS.items()}
    assert p == V432


def test_new_groups_reach_the_style_constants():
    """MODEL v4.3.2: the boundary, zone, Fig3b and one-at-a-time constants come from the palette; the zone opacities
    stay fixed (0.30 / 0.30 / 0.07); the lever shades are retired."""
    p = S.PALETTE
    assert (S.AR, S.ATP) == (p['boundaries']['acquired_rights'], p['boundaries']['ability_to_pay'])
    assert S.BOUNDARY['AR']['color'] == S.AR and S.BOUNDARY['AtP']['color'] == S.ATP
    assert {k: z['color'] for k, z in S.ZONE.items()} == {'within_both': p['boundary_zones']['within_both'],
                                                          'within_ar': p['boundary_zones']['within_ar_only'],
                                                          'exceeded': p['boundary_zones']['exceeded']}
    assert {k: z['alpha'] for k, z in S.ZONE.items()} == {'within_both': 0.30, 'within_ar': 0.30, 'exceeded': 0.07}
    assert S.CUMULATIVE_FIG3B == p['cumulative']['fig3b_cumulative_carbon']
    assert (S.TORNADO_LOW, S.TORNADO_HIGH, S.TORNADO_SINGLE) == tuple(p['one_at_a_time'][k] for k in
                                                                     ('low_end', 'high_end', 'single_alternative'))
    from figures import draw as P
    assert (P.TORNADO_LOW, P.TORNADO_HIGH, P.TORNADO_SINGLE) == (S.TORNADO_LOW, S.TORNADO_HIGH, S.TORNADO_SINGLE)
    assert not hasattr(S, 'LEVER') and 'levers' not in S.registry()


def test_no_hard_coded_boundary_or_tornado_colour():
    """MODEL v4.3.2: the hex values of the moved keys appear in no figure module except as the documented fixed
    literals of style.py that stand for other meanings (MUTED and HATCH_COLOUR #6E6E6E, the High replacement grey,
    NEUTRAL_DARK #4D4D4D, the typology and SF15 colours that share a value)."""
    import re
    moved = {v.upper() for g in ('boundaries', 'boundary_zones', 'cumulative', 'one_at_a_time')
             for v in V432[g].values()}
    figs = os.path.join(ROOT, 'figures')
    for f in sorted(os.listdir(figs)):
        if not f.endswith('.py') or f == 'style.py':
            continue
        hexes = {h.upper() for h in re.findall(r'#[0-9A-Fa-f]{6}\b', open(os.path.join(figs, f)).read())}
        assert not hexes & moved, (f, hexes & moved)
    src = open(os.path.join(figs, 'style.py')).read()
    for h in ('#D7191C', '#67000D', '#41AB5D', '#A1D99B', '#FB6A4A', '#4A6192', '#EB6123'):
        lines = [x for x in src.splitlines() if h in x.upper() and not x.lstrip().startswith('#')]
        assert all(re.match(r'\s*(RELEASE_BINDS|TYPOLOGY) =', x) for x in lines), (h, lines)


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
                      avoid=S.STRATEGY['S1'], detached=S.TYPOLOGY['Detached'],
                      moderate=S.PATHWAY_SETTING['moderate'], pathway=S.PATHWAY['pathway'],
                      tornado_high=S.TORNADO_HIGH, a1a3=S.STAGE['a1a3'][0], improve=S.STRATEGY['S3'],
                      tornado_low=S.TORNADO_LOW, tornado_single=S.TORNADO_SINGLE, muted=S.MUTED,
                      ar=S.AR, atp=S.ATP, bnd_ar=S.BOUNDARY['AR']['color'], bnd_atp=S.BOUNDARY['AtP']['color'],
                      z_both=S.ZONE['within_both']['color'], z_ar=S.ZONE['within_ar']['color'],
                      z_exc=S.ZONE['exceeded']['color'], cum=S.CUMULATIVE_FIG3B, reference=S.REFERENCE,
                      neutral_dark=S.NEUTRAL_DARK, release_binds=S.RELEASE_BINDS, scen_ref=S.SCENARIO['REF']['color'],
                      high_grey=S.SCENARIO['HIGH']['color'], hatch=S.HATCH_COLOUR)))
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


# MODEL v4.3.2: each new key changes only its own constants (several share a default value with other meanings:
# Fig3b column = Reference = NEUTRAL_DARK #4D4D4D; single alternative = MUTED = HATCH_COLOUR = High replacement
# #6E6E6E; low end = Improve = A1-A3 #4A6192; high end = Moderate #EB6123; AR = the SF15 release markers #D7191C)
NEW_KEY_CONSTANTS = {('boundaries', 'acquired_rights'): {'ar', 'bnd_ar'},
                     ('boundaries', 'ability_to_pay'): {'atp', 'bnd_atp'},
                     ('boundary_zones', 'within_both'): {'z_both'},
                     ('boundary_zones', 'within_ar_only'): {'z_ar'},
                     ('boundary_zones', 'exceeded'): {'z_exc'},
                     ('cumulative', 'fig3b_cumulative_carbon'): {'cum'},
                     ('one_at_a_time', 'low_end'): {'tornado_low'},
                     ('one_at_a_time', 'high_end'): {'tornado_high'},
                     ('one_at_a_time', 'single_alternative'): {'tornado_single'}}


@pytest.mark.parametrize('group, key', list(NEW_KEY_CONSTANTS))
def test_new_key_changes_only_its_meaning(tmp_path, group, key):
    base = _style_with(tmp_path, group, key, V432[group][key])
    s = _style_with(tmp_path, group, key, '#00FFFF')
    own = NEW_KEY_CONSTANTS[(group, key)]
    assert all(s[k] == '#00FFFF' for k in own)
    assert {k: v for k, v in s.items() if k not in own} == {k: v for k, v in base.items() if k not in own}
