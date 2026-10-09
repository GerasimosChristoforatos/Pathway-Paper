"""Release checks of MODEL v1.0.0.

1. The values the release adds (annual component split, annual and census-interval demand
   bands, the annual series of the projection variants, the population paths of the AESA
   layer) agree with the numbers locked by tests/test_regression_model_v1.py: the H4
   components add up exactly to the captured annual carbon, the bands to the captured band
   totals, the variants to the captured variant totals.
2. The headline set: every figure of figure_plan.HEADLINE exists as PNG, PDF and source data
   (CSV), and HEADLINE.md shows every one with a filled caption.
3. Figure audit and indexes: every planned figure exists and no other; every output file is
   indexed once; DIAGNOSTICS.md shows every diagnostic with the script that draws it.
4. Vocabulary and style: no reader-facing text of the release (generated reports, HEADLINE.md,
   DIAGNOSTICS.md, INDEX.md, the texts of every figure) uses a term of the earlier versions
   (naming.OLD_TERMS, docs/RENAMING.md); every module that draws a figure imports style.py and
   plotting.py, and only style.save_figure writes figure files.
"""
import ast
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


# ---- 3. figure audit and indexes --------------------------------------------------------------
def planned_figures():
    out = {h['file']: os.path.join(L.HEADLINE, h['file']) for h in FP.HEADLINE}
    out.update({f: os.path.join(L.DIAGNOSTICS, g, f) for g, rows in FP.DIAGNOSTICS.items() for f, _, _ in rows})
    return out


def test_every_planned_figure_exists_and_no_other():
    """Every figure of docs/FIGURE_PLAN.md exists (headline: PNG and PDF; diagnostics: PNG) with
    its audit record, and no figure outside the plan is written."""
    plan = planned_figures()
    for fid, base in plan.items():
        exts = ('png', 'pdf') if fid.startswith('H') else ('png',)
        for ext in exts:
            assert os.path.exists(f'{base}.{ext}'), f'{fid}.{ext}'
        assert os.path.exists(os.path.join(L.FIGURE_AUDIT, f'{fid}.json')), fid
    written = {os.path.splitext(f)[0] for base in (L.HEADLINE, L.DIAGNOSTICS) for _, _, fs in os.walk(base)
               for f in fs if f.endswith('.png')}
    assert written == set(plan), sorted(written ^ set(plan))


def test_every_output_file_is_indexed_once():
    """outputs/INDEX.md covers every file the run wrote (indexes.FILES), each by exactly one entry,
    and no entry of the registry is stale."""
    import indexes
    files = indexes.output_files()
    assert 'INDEX.md' in files
    bad = {f: len(indexes.entry(f)) for f in files if len(indexes.entry(f)) != 1}
    assert not bad, bad
    stale = [e[0] for e in indexes.FILES if not any(indexes.fnmatch.fnmatch(f, e[0]) for f in files)]
    assert not stale, stale
    md = open(os.path.join(L.OUT, 'INDEX.md'), encoding='utf-8').read()
    assert 'NOT INDEXED' not in md
    for f in files:
        assert f'`{f}`' in md, f


def test_diagnostics_md_shows_every_diagnostic_with_its_script():
    md = open(os.path.join(L.DIAGNOSTICS, 'DIAGNOSTICS.md'), encoding='utf-8').read()
    for g, rows in FP.DIAGNOSTICS.items():
        for fid, _, _ in rows:
            assert f'({g}/{fid}.png)' in md, fid
            rec = json.load(open(os.path.join(L.FIGURE_AUDIT, f'{fid}.json')))
            assert rec['producer'] and rec['producer'].endswith('.py'), fid
            assert f"drawn by `{rec['producer']}`" in md, fid


def test_headline_figures_print_within_183_mm():
    from PIL import Image
    import style as S
    for h in FP.HEADLINE:
        with Image.open(os.path.join(L.HEADLINE, f"{h['file']}.png")) as im:
            assert im.size[0] / S.DPI * 25.4 <= 183.0 + 1e-6, h['file']


# ---- 4. vocabulary and style -------------------------------------------------------------------
def _reader_texts():
    """(file relative to outputs/, line number, text) of every reader-facing text of the run."""
    md = [os.path.join(d, f) for d, _, fs in os.walk(L.REPORTS) for f in fs if f.endswith('.md')]
    md += [os.path.join(L.HEADLINE, 'HEADLINE.md'), os.path.join(L.DIAGNOSTICS, 'DIAGNOSTICS.md'),
           os.path.join(L.OUT, 'INDEX.md')]
    for p in sorted(md):
        with open(p, encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                yield os.path.relpath(p, L.OUT), i, line
    for f in sorted(os.listdir(L.FIGURE_AUDIT)):
        rec = json.load(open(os.path.join(L.FIGURE_AUDIT, f)))
        for i, t in enumerate(rec.get('texts', []) + [rec.get('note') or ''], 1):
            yield os.path.relpath(os.path.join(L.FIGURE_AUDIT, f), L.OUT), i, t


def test_no_old_vocabulary_in_reader_facing_texts():
    import re
    rules = [(re.compile(p), new) for p, new in N.OLD_TERMS]
    hits = [f'{f}:{i}: {m.group(0)!r} -> {new}' for f, i, line in _reader_texts() for rx, new in rules
            for m in rx.finditer(line)]
    assert not hits, '\n'.join(hits[:50])


FIGURE_MODULES = ('headline.py', 'projection.py', 'Diagnostics.py', 'Sensitivity.py', 'MonteCarlo.py',
                  'boundaries.py', 'pathways.py', 'tools/figures_report.py')


def _imports(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_every_figure_module_imports_style_and_plotting():
    """Every module that draws a figure (FIGURE_MODULES and every producer in the figure audit
    records) imports style.py and plotting.py; no module but style.py calls savefig."""
    producers = {json.load(open(os.path.join(L.FIGURE_AUDIT, f))).get('producer')
                 for f in os.listdir(L.FIGURE_AUDIT)}
    assert producers <= set(FIGURE_MODULES), producers - set(FIGURE_MODULES)
    for m in FIGURE_MODULES:
        tree = ast.parse(open(os.path.join(ROOT, m), encoding='utf-8').read())
        assert {'style', 'plotting'} <= _imports(tree), m
    py = [os.path.join(d, f) for d, ds, fs in os.walk(ROOT) for f in fs if f.endswith('.py')
          and not any(x in d for x in ('.venv', '.git', 'site-packages'))]
    for p in py:
        if os.path.relpath(p, ROOT) == 'style.py':
            continue
        tree = ast.parse(open(p, encoding='utf-8').read())
        calls = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'savefig']
        assert not calls, f'{os.path.relpath(p, ROOT)}: savefig at lines {calls} (use style.save_figure)'
