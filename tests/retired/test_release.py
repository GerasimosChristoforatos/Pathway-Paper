"""Release checks of MODEL v1.0.0.

1. The values the release adds (annual component split, annual and census-interval demand
   bands, the annual series of the projection variants, the population paths of the AESA
   layer) agree with the numbers locked by tests/test_regression_model_v1.py: the annual
   components add up exactly to the captured annual carbon, the bands to the captured band
   totals, the variants to the captured variant totals.
2. The paper and Extended Data (MODEL v2.0.0): every figure of figure_plan.PAPER and EXTENDED_DATA
   exists as PNG, PDF and source data (CSV) within its print width; PAPER.md and EXTENDED_DATA.md show
   every one with a filled caption; Table 2 carries the Monte Carlo intervals and P(LoE <= 1) of TL
   under AR and AtP; outputs/headline/ is retired.
3. Figure audit and indexes: every planned figure exists and no other (the superseded diagnostics
   are not drawn); maintenance is drawn as its own layer only in figure_plan.MAINTENANCE_ALLOWED;
   every output file is indexed once; DIAGNOSTICS.md shows every diagnostic with its script.
4. Vocabulary and style: no reader-facing text of the release (generated reports, PAPER.md, EXTENDED_DATA.md,
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


def test_stage_and_material_split_add_up_to_the_annual_carbon():
    """MODEL v2.0.0 (Fig3): the annual stage and material splits of the Reference add up to the locked annual
    carbon; the stage totals equal the A1-A3 / A4-A5 totals of the pathway layer (runs.csv, Reference)."""
    an = pd.read_csv(data('baseline/annual.csv'))
    p = an[an['source'] == 'projection'].set_index('year')
    st = pd.read_csv(data('baseline/annual_by_stage.csv')).set_index('year')
    parts = st['a1a3_kt'] + st['a4a5_kt'] + st['maintenance_kt'] + st['soil_carbon_loss_kt']
    assert np.allclose(parts, p['carbon_kt'], rtol=1e-9, atol=0)
    assert np.allclose(st['a1a3_kt'] + st['a4a5_kt'], p['materials_construction_kt'], rtol=1e-9, atol=0)
    assert np.allclose(st['maintenance_kt'], p['maintenance_kt'], rtol=1e-12, atol=0)
    r = pd.read_csv(data('pathways/runs.csv'))
    r = r[(r['scenario'] == 'REF') & (r['run'] == 'REF')].iloc[0]
    assert math.isclose(st['a1a3_kt'].sum(), r['a1a3_kt'], rel_tol=1e-9)
    assert math.isclose(st['a4a5_kt'].sum(), r['a4a5_kt'], rel_tol=1e-9)
    m = pd.read_csv(data('baseline/annual_by_material.csv')).groupby('year')['carbon_kt'].sum()
    assert np.allclose(m.loc[p.index], p['carbon_kt'], rtol=1e-9, atol=0)


def test_history_replacement_split_adds_up_to_the_band():
    sp = pd.read_csv(data('baseline/bands_history_replacement_split.csv')).set_index('interval')
    h = pd.read_csv(data('baseline/bands_history.csv'))
    band = h[h['band'] == N.band_data_label('replacement_history')].set_index('interval')['floor_area_Mm2_per_year']
    assert list(sp.index) == list(band.index)
    assert np.allclose(sp['net_replacement_census_Mm2_per_year'] + sp['unexplained_building_Mm2_per_year'], band,
                       rtol=1e-9, atol=1e-12)
    assert np.allclose(sp['net_replacement_band_Mm2_per_year'], band, rtol=0, atol=0)


def test_population_paths_reproduce_the_reference():
    r = json.load(open(data('aesa/results.json')))
    pp, d = r['population_paths'], r['deterministic']['REF']
    for k in ('LoE_AR', 'LoE_AtP', 'I_kt'):
        assert pp['50th'][k] == pytest.approx(d[k], rel=1e-12), k
    assert pp['5th']['I_kt'] < d['I_kt'] < pp['95th']['I_kt']
    assert pp['5th']['B_AR_kt'] < pp['50th']['B_AR_kt'] < pp['95th']['B_AR_kt']


# ---- 2. paper and Extended Data ------------------------------------------------------------------
VECTOR = ([(L.PAPER, h) for h in FP.PAPER] + [(L.EXTENDED_DATA, h) for h in FP.EXTENDED_DATA]
          + [(L.KEY_FIGURES, h) for h in FP.KEY_FIGURES])


def export_run():
    """MODEL v2.1.0: PNG only by default; run_all.py --export (PATHWAY_EXPORT=1) also writes the vector PDF and the
    source-data CSV of every paper, Extended Data and key figure."""
    return os.environ.get('PATHWAY_EXPORT') == '1'


@pytest.mark.parametrize('base,h', VECTOR, ids=[h['id'] for _, h in VECTOR])
def test_paper_and_extended_data_figure_files(base, h):
    p = os.path.join(base, f"{h['file']}.png")
    assert os.path.exists(p) and os.path.getsize(p) > 0, p
    for ext in ('pdf', 'csv'):
        p = os.path.join(base, f"{h['file']}.{ext}")
        assert os.path.exists(p) == export_run(), p
    if export_run():
        src = pd.read_csv(os.path.join(base, f"{h['file']}.csv"))
        assert list(src.columns) == ['panel', 'series', 'x', 'value', 'unit'] and len(src) > 0


def _md_check(md, items):
    import re
    for h in items:
        assert f"![{h['id']}]({h['file']}.png)" in md, h['id']
    assert not re.search(r'\{[a-z_0-9]+(:[^}]*)?\}', md), 'unfilled caption placeholder'


def test_paper_md_shows_every_figure_the_findings_and_the_tables():
    md = open(os.path.join(L.PAPER, 'PAPER.md'), encoding='utf-8').read()
    _md_check(md, FP.PAPER)
    findings = md.split('## Findings')[1].split('## Figures')[0]
    n = sum(1 for line in findings.splitlines() if line[:2].rstrip('.').isdigit())
    assert 6 <= n <= 8, n
    assert '### Table 1.' in md and '### Table 2.' in md
    for t in FP.TABLES:
        for ext in ('md', 'csv'):
            assert os.path.exists(os.path.join(L.PAPER, f"{t['file']}.{ext}")), t['file']


def test_table2_reports_the_monte_carlo_and_both_probabilities_for_tl():
    t = pd.read_csv(os.path.join(L.PAPER, 'Table2_results.csv')).set_index('run_id')
    assert list(t.index) == ['REF', 'P1-moderate', 'P2-moderate', 'P3-moderate', 'P4-moderate', 'P5-moderate', 'TL']
    for run in ('REF', 'P5-moderate', 'TL'):
        assert t.loc[run, 'carbon_kt_mc_p5'] < t.loc[run, 'carbon_kt'] < t.loc[run, 'carbon_kt_mc_p95']
    s = pd.read_csv(data('pathways/montecarlo_summary.csv')).set_index(['run', 'quantity'])
    for run, k in (('P5-moderate', 'P5'), ('TL', 'TL')):
        for key in ('AR', 'AtP'):
            assert t.loc[run, f'P_LoE_{key}_at_most_1'] == s.loc[(k, f'LoE_{key}'), 'probability_LoE_at_most_1']
    runs = pd.read_csv(data('pathways/runs.csv'))
    runs = runs[runs['scenario'] == 'REF'].set_index('run')
    for run in t.index:
        assert t.loc[run, 'carbon_kt'] == runs.loc[run, 'carbon_kt']


def test_extended_data_md_shows_every_figure():
    _md_check(open(os.path.join(L.EXTENDED_DATA, 'EXTENDED_DATA.md'), encoding='utf-8').read(), FP.EXTENDED_DATA)


def test_key_figures_md_shows_every_figure():
    _md_check(open(os.path.join(L.KEY_FIGURES, 'KEY_FIGURES.md'), encoding='utf-8').read(), FP.KEY_FIGURES)


def test_headline_folder_retired():
    assert not os.path.exists(os.path.join(L.OUT, 'headline'))
    assert not os.path.exists(os.path.join(ROOT, 'headline.py'))


# ---- 3. figure audit and indexes --------------------------------------------------------------
def planned_figures():
    out = {h['file']: os.path.join(base, h['file']) for base, h in VECTOR}
    out.update({f: os.path.join(L.DIAGNOSTICS, g, f) for g, rows in FP.DIAGNOSTICS.items() for f, _, _ in rows})
    return out


def test_every_planned_figure_exists_and_no_other():
    """Every figure of the figure plan exists (paper and Extended Data: PNG and PDF; diagnostics: PNG) with
    its audit record, and no figure outside the plan is written."""
    plan = planned_figures()
    for fid, base in plan.items():
        exts = ('png', 'pdf') if fid.startswith(('Fig', 'ED', 'K')) and export_run() else ('png',)
        for ext in exts:
            assert os.path.exists(f'{base}.{ext}'), f'{fid}.{ext}'
        assert os.path.exists(os.path.join(L.FIGURE_AUDIT, f'{fid}.json')), fid
    written = {os.path.splitext(f)[0] for base in (L.PAPER, L.EXTENDED_DATA, L.KEY_FIGURES, L.DIAGNOSTICS)
               for _, _, fs in os.walk(base) for f in fs if f.endswith('.png')}
    assert written == set(plan), sorted(written ^ set(plan))
    assert not set(FP.SUPERSEDED) & written
    audits = {os.path.splitext(f)[0] for f in os.listdir(L.FIGURE_AUDIT)}
    assert audits == set(plan), sorted(audits ^ set(plan))


def test_maintenance_drawn_only_where_allowed():
    """Maintenance (B2, B4) is drawn as its own layer or line only in Fig2, Fig3, Fig4, D25 and D26
    (figaudit.maintenance_drawn: data artists in the maintenance colour, legend entries naming it)."""
    drawn = set()
    for f in os.listdir(L.FIGURE_AUDIT):
        rec = json.load(open(os.path.join(L.FIGURE_AUDIT, f)))
        assert 'maintenance_drawn' in rec, f
        if rec['maintenance_drawn']:
            drawn.add(rec['figure'])
    assert drawn == set(FP.MAINTENANCE_ALLOWED), sorted(drawn ^ set(FP.MAINTENANCE_ALLOWED))


def test_boundary_styling_in_every_planetary_boundary_figure():
    """MODEL v2.1.0: every planetary-boundary figure (figure_plan.PB_FIGURES) draws the AR / AtP lines and the zones of
    style.py (figaudit: boundary_drawn, boundary_zones), and no other figure draws a boundary."""
    drawn, zoned = set(), set()
    for f in os.listdir(L.FIGURE_AUDIT):
        rec = json.load(open(os.path.join(L.FIGURE_AUDIT, f)))
        if rec.get('boundary_drawn'):
            drawn.add(rec['figure'])
        if rec.get('boundary_zones'):
            zoned.add(rec['figure'])
    pb = set(FP.PB_FIGURES)
    assert zoned == pb, sorted(zoned ^ pb)
    assert drawn == pb, sorted(drawn ^ pb)


def test_every_output_file_is_indexed_once():
    """outputs/INDEX.md covers every file the run wrote (indexes.FILES), each by exactly one entry,
    and no entry of the registry is stale."""
    import indexes
    files = indexes.output_files()
    assert 'INDEX.md' in files
    bad = {f: len(indexes.entry(f)) for f in files if len(indexes.entry(f)) != 1}
    assert not bad, bad
    stale = [e[0] for e in indexes.FILES if not any(indexes.fnmatch.fnmatch(f, e[0]) for f in files)]
    if not export_run():                       # PDFs and source data exist only after run_all.py --export
        stale = [e for e in stale if not e.endswith(('.pdf', '.csv')) or not e.split('/')[0] in
                 ('paper', 'extended_data', 'key_figures')]
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


def test_paper_and_extended_data_figures_print_within_their_width():
    from PIL import Image
    import style as S
    for base, h in VECTOR:
        with Image.open(os.path.join(base, f"{h['file']}.png")) as im:
            assert im.size[0] / S.DPI * 25.4 <= {'single': 89.0, 'double': 183.0}[h['width']] + 1e-6, h['file']


# ---- 4. vocabulary and style -------------------------------------------------------------------
def _reader_texts():
    """(file relative to outputs/, line number, text) of every reader-facing text of the run."""
    md = [os.path.join(d, f) for d, _, fs in os.walk(L.REPORTS) for f in fs if f.endswith('.md')]
    md += [os.path.join(L.PAPER, 'PAPER.md'), os.path.join(L.EXTENDED_DATA, 'EXTENDED_DATA.md'),
           os.path.join(L.KEY_FIGURES, 'KEY_FIGURES.md'),
           os.path.join(L.PAPER, 'Table1_levers.md'), os.path.join(L.PAPER, 'Table2_results.md'),
           os.path.join(L.DIAGNOSTICS, 'DIAGNOSTICS.md'),
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


FIGURE_MODULES = ('paper.py', 'extended_data.py', 'key_figures.py', 'projection.py', 'Diagnostics.py', 'MonteCarlo.py',
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
