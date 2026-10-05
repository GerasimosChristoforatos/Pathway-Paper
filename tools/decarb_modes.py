"""Compare the material-decarbonisation modes (Boss.DECARB_MODE) and run the
item-level decarbonisation sensitivities. Writes outputs/DECARB_MODES.md and
outputs/decarb_modes.json, stamped with the run time and the git commit.
No number is typed by hand.

    python run_all.py --compare-modes     # the optional step that runs this

Not part of the default full run: the generated documents read the stored
result and state its date and commit (provenance_note), and flag it as stale
when the adopted-mode carbon no longer matches the current run (stale()).

Per mode, the outputs of its own pipeline run: the adopted mode in outputs/,
'none' in outputs/frozen/ (frozen-technology check run, default full run), any
other mode in outputs/modes/<mode>/ (run_all.py --compare-modes):
boss_results.json (deterministic reference path, S3-10),
montecarlo_summary.csv (MC p5/p50/p95), pb_results.json (cumulative LoE
2026-2050; deterministic and MC). The implied reductions by 2050 per typology
come from a Boss run of each mode (checked against that mode's
boss_results.json). Item-level sensitivities (ITEM_SENS): a Boss run per case;
cumulative LoE against the reference boundaries in the item-level run's
pb_annual.csv, as PB.py does (equal to PB's own computation to the last bit
but one: the boundary passes through a CSV). Class-level sensitivities: its
run's sensitivity_oat.csv and pb_sensitivity.csv.
"""
import contextlib
import datetime
import importlib
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, 'outputs')
LABEL = {'none': 'frozen technology (2025 factors)',
         'horup_class_v1_1': 'class-level mapping (baseline-pb-v1.1)',
         'horup_item': 'item-level mapping (v1.2)'}


# item-level sensitivities: (case, label, DECARB_MODE, other Boss settings); the first is the reference
ITEM_SENS = [
    ('reference', 'Item-level mapping (horup_item)', 'horup_item', {}),
    ('frozen', 'Frozen technology: 2025 factors held (no decarbonisation)', 'none', {}),
    ('proxies_held', 'Proxy-mapped items held at 2025', 'horup_item', dict(DECARB_ITEM_CASE='proxies_held')),
    ('nz_elec_held', 'NZ-made, electricity-intensive items held at 2025', 'horup_item',
     dict(DECARB_ITEM_CASE='nz_elec_held')),
    ('lift_steel_profile', 'Lift at the steel-profile rate (Horup SI Table S4)', 'horup_item',
     dict(DECARB_ITEM_CASE='elevator_steel_profile')),
    ('class_v1_1', 'Class-level mapping of baseline-pb-v1.1', 'horup_class_v1_1', {}),
]


def provenance():
    """When and from which code this comparison was run: UTC time, git commit,
    whether tracked files outside outputs/ had uncommitted changes, run mode."""
    def git(*a):
        try:
            return subprocess.check_output(['git', *a], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
        except (OSError, subprocess.CalledProcessError):
            return ''
    dirty = git('status', '--porcelain', '--untracked-files=no', '--', '.', ':(exclude)outputs')
    return dict(run_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                commit=git('rev-parse', '--short', 'HEAD') or 'unknown', code_uncommitted_changes=bool(dirty),
                run_mode='quick' if os.environ.get('PATHWAY_QUICK') == '1' else 'full',
                command='python run_all.py --compare-modes')


def provenance_note(res):
    """One line naming the stored comparison's run: for the generated documents."""
    p = res.get('provenance', {})
    return (f"comparison run {p.get('run_utc', '?')} at commit {p.get('commit', '?')}"
            + (' with uncommitted code changes' if p.get('code_uncommitted_changes') else '')
            + (' (QUICK RUN, not for reporting)' if p.get('run_mode') == 'quick' else '')
            + f" (`{p.get('command', 'python run_all.py --compare-modes')}`)")


def stale(res, out=OUT):
    """True when the stored comparison's adopted-mode carbon differs from the
    current run's (outputs/boss_results.json), or the adopted mode changed."""
    import Boss
    b = read_json(out, 'boss_results.json')
    a = res['modes'].get(res['adopted'], {})
    return (res['adopted'] != Boss.DECARB_MODE or b is None
            or not np.isclose(b['carbon_kt'], a.get('carbon_kt', np.nan), rtol=1e-9))


def load_stored():
    """The stored comparison (outputs/decarb_modes.json) or None."""
    return read_json(OUT, 'decarb_modes.json')


def mode_dir(mode, adopted):
    if mode == adopted:
        return OUT
    if mode == 'none':
        return os.path.join(OUT, 'frozen')
    return os.path.join(OUT, 'modes', mode)


def read_json(d, name):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def boss_run(mode, **settings):
    import Boss
    M = importlib.reload(Boss)
    M.SHOW_PLOTS = False
    M.DECARB_MODE = mode
    for k, v in settings.items():
        if not hasattr(M, k):
            raise AttributeError(f"Boss has no setting '{k}'.")
        setattr(M, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        B = M.main()
    importlib.reload(Boss)
    return B


def main():
    import Boss
    import Building_factors as BF
    adopted = Boss.DECARB_MODE
    fy = None
    mf = pd.read_csv(Boss.FILE_FACTORS_MATERIAL)
    a13_2025 = mf[mf.Stage == 'A1-A3'].groupby('Typology')['kgCO2e_per_m2'].sum()
    res = dict(adopted=adopted, provenance=provenance(), modes={})
    for mode in BF.DECARB_MODES:
        d = mode_dir(mode, adopted)
        B = boss_run(mode)
        typ = B['typ_names']
        fy = list(B['forecast_years'])
        i50 = fy.index(2050)
        whole = {t: float(1 - np.asarray(B['T_INT'][t] if np.ndim(B['T_INT'][t]) else
                                         np.full(len(fy), B['T_INT'][t]))[i50] /
                          float(np.asarray(B['T_BASELINE_2025'][t]))) for t in typ}
        a13 = {t: (0.0 if B['RED_TOT'] is None else float(B['RED_TOT'][t][i50] / a13_2025[t])) for t in typ}
        r = dict(label=LABEL[mode], dir=os.path.relpath(d, ROOT),
                 carbon_kt=float(B['tot_carbon_median']), upfront_kt=float(B['_upfront'] + B['_soil'] / 1e6),
                 a13_reduction_2050=a13, whole_factor_reduction_2050=whole)
        bj = read_json(d, 'boss_results.json')
        if bj is not None:
            if not (np.isclose(bj['carbon_kt'], r['carbon_kt'], rtol=1e-9)
                    and np.isclose(bj['upfront_kt'], r['upfront_kt'], rtol=1e-9)):
                raise ValueError(f"{d}/boss_results.json carbon {bj['carbon_kt']} differs from a fresh {mode} run "
                                 f"{r['carbon_kt']}: re-run the pipeline.")
        else:
            r['missing'] = ['boss_results.json']
        p = os.path.join(d, 'montecarlo_summary.csv')
        if os.path.exists(p):
            s = pd.read_csv(p, index_col=0)
            r['mc'] = {k: {q: float(s.loc[k, q]) for q in ('p5', 'p50', 'p95')} for k in ('carbon_kt', 'upfront_kt')}
        pj = read_json(d, 'pb_results.json')
        if pj is not None:
            r['pb'] = dict(det=pj['deterministic']['S3-10'], mc=pj['mc'].get('S3-10'))
        res['modes'][mode] = r

    # sensitivities (deterministic, one at a time). Item-level: computed here,
    # carbon from a Boss run per case and cumulative LoE 2026-2050 against the
    # reference (S3-10) boundaries of the item-level run's pb_annual.csv, as in
    # PB.py (boundaries unchanged, I_sec re-run). Class-level: read from its own
    # run directory (sensitivity_oat.csv, pb_sensitivity.csv).
    import PB
    res['sensitivity'] = {}
    d_item = mode_dir('horup_item', adopted)
    pa = os.path.join(d_item, 'pb_annual.csv')
    if os.path.exists(pa):
        ann = pd.read_csv(pa)
        ann = ann[ann.scenario == 'S3-10'].set_index('year')
        b_ar, b_atp = ann['B_AR_kgCO2e'], ann['B_AtP_kgCO2e']
        rows = []
        for case, label, mode, kw in ITEM_SENS:
            B = boss_run(mode, **kw)
            I = pd.Series(B['carbon_total_typ'].sum(axis=1).values, index=np.asarray(B['forecast_years']))
            rows.append(dict(case=case, label=label, carbon_kt=float(B['tot_carbon_median']),
                             cum_LoE_AR=float(PB.cum(I, b_ar)), cum_LoE_AtP=float(PB.cum(I, b_atp))))
        ref = rows[0]
        for r in rows:
            r['carbon_change_pct'] = 100 * (r['carbon_kt'] / ref['carbon_kt'] - 1)
            r['AR_vs_ref_pct'] = 100 * (r['cum_LoE_AR'] / ref['cum_LoE_AR'] - 1)
            r['AtP_vs_ref_pct'] = 100 * (r['cum_LoE_AtP'] / ref['cum_LoE_AtP'] - 1)
        res['sensitivity']['horup_item'] = dict(
            oat=[dict(case=r['label'], carbon_kt=r['carbon_kt'], carbon_change_pct=r['carbon_change_pct']) for r in rows],
            pb=[{k: r[k] for k in ('case', 'label', 'cum_LoE_AR', 'cum_LoE_AtP', 'AR_vs_ref_pct', 'AtP_vs_ref_pct')}
                for r in rows])
    d = mode_dir('horup_class_v1_1', adopted)
    p, q = os.path.join(d, 'sensitivity_oat.csv'), os.path.join(d, 'pb_sensitivity.csv')
    if os.path.exists(p) and os.path.exists(q):
        s = pd.read_csv(p)
        s = s[(s.group == 'Adopted') | s.case.str.contains('Decarbonisation|Frozen technology')]
        ps = pd.read_csv(q)
        ps = ps[ps.case.isin(['reference']) | ps.case.str.match(r'^(vi|vii)_')]
        res['sensitivity']['horup_class_v1_1'] = dict(
            oat=s[['case', 'carbon_kt', 'carbon_change_pct']].to_dict(orient='records'),
            pb=ps[['case', 'label', 'cum_LoE_AR', 'cum_LoE_AtP', 'AR_vs_ref_pct', 'AtP_vs_ref_pct']]
            .to_dict(orient='records'))

    cov = pd.read_csv(BF.OUT_ITEM_COVERAGE)
    res['coverage'] = {k: g.pivot(index='Key', columns='Typology', values='Value').to_dict()
                       for k, g in cov.groupby('Kind')}
    s4 = pd.read_csv(BF.FILE_HORUP)
    used = sorted(set(pd.read_csv(BF.FILE_ITEM_MAP)['s4_row']) - {BF.ITEM_HELD})
    res['s4_rows'] = {m: {int(r.year): dict(rel_to_2025=float(r.rel_to_2025), cell=r.cell)
                          for r in s4[s4.material == m].itertuples()} for m in used}
    with open(os.path.join(OUT, 'decarb_modes.json'), 'w') as f:
        json.dump(res, f, indent=2)
    write_md(res, typ)
    print(f'outputs/DECARB_MODES.md, outputs/decarb_modes.json (adopted: {adopted})')


def write_md(res, typ):
    L = ['# Material decarbonisation: modes compared (generated by tools/decarb_modes.py; do not edit by hand)', '',
         f"Stored result: {provenance_note(res)}.", '',
         f"Adopted mode: `{res['adopted']}`. Reference path S3-10, 2026-2050. Each mode is a full pipeline run "
         '(own directory). A1-A3 only is decarbonised; A4-A5, B2, B4, C1-C4 and soil stay at 2025 in every mode.', '',
         '## Results by mode', '',
         '| mode | carbon (kt) | upfront (kt) | MC carbon p5 / p50 / p95 (kt) | cum. LoE AR | cum. LoE AtP | '
         'MC LoE AR p5 / p50 / p95 | MC LoE AtP p5 / p50 / p95 |', '|---|---|---|---|---|---|---|---|']
    for mode, r in res['modes'].items():
        mc = r.get('mc')
        mcs = f"{mc['carbon_kt']['p5']:,.0f} / {mc['carbon_kt']['p50']:,.0f} / {mc['carbon_kt']['p95']:,.0f}" \
            if mc else 'n/a (no MC run)'
        pb = r.get('pb')
        if pb:
            det, pm = pb['det'], pb['mc']
            ar, atp = f"{det['LoE_AR']:.2f}", f"{det['LoE_AtP']:.1f}"
            mar = f"{pm['LoE_AR_p5']:.2f} / {pm['LoE_AR_p50']:.2f} / {pm['LoE_AR_p95']:.2f}" if pm else 'n/a'
            matp = f"{pm['LoE_AtP_p5']:.1f} / {pm['LoE_AtP_p50']:.1f} / {pm['LoE_AtP_p95']:.1f}" if pm else 'n/a'
        else:
            ar = atp = mar = matp = 'n/a (no PB run)'
        L.append(f"| `{mode}`: {r['label']} | {r['carbon_kt']:,.0f} | {r['upfront_kt']:,.0f} | {mcs} | {ar} | {atp} | "
                 f"{mar} | {matp} |")
    L += ['', '## Implied reduction by 2050 versus 2025, per typology', '',
          '| mode | ' + ' | '.join(f'{t} A1-A3' for t in typ) + ' | ' + ' | '.join(f'{t} whole factor' for t in typ)
          + ' |', '|---|' + '---|' * (2 * len(typ))]
    for mode, r in res['modes'].items():
        L.append(f'| `{mode}` | ' + ' | '.join(f"{-100 * r['a13_reduction_2050'][t]:.1f}%" for t in typ) + ' | '
                 + ' | '.join(f"{-100 * r['whole_factor_reduction_2050'][t]:.1f}%" for t in typ) + ' |')
    L += ['', 'Whole factor = all in-scope stages plus soil carbon loss (kg CO2e/m2 GFA) of new floor area.']
    for mode, s in res['sensitivity'].items():
        L += ['', f'## Sensitivities of `{mode}` (deterministic, one at a time)', '',
              '| case | carbon (kt) | change |', '|---|---|---|']
        L += [f"| {x['case']} | {x['carbon_kt']:,.0f} | {x['carbon_change_pct']:+.1f}% |" for x in s['oat']]
        L += ['', '| PB case | cum. LoE AR | cum. LoE AtP | change |', '|---|---|---|---|']
        L += [f"| {x['label']} | {x['cum_LoE_AR']:.2f} | {x['cum_LoE_AtP']:.1f} | {x['AR_vs_ref_pct']:+.1f}% |"
              for x in s['pb']]
    c = res['coverage']
    L += ['', '## Item-level mapping: share of 2025 A1-A3 by basis (pooled per typology)', '',
          '| basis | ' + ' | '.join(typ) + ' |', '|---|' + '---|' * len(typ)]
    for k in ('direct', 'sec31', 'proxy', 'held'):
        L.append(f'| {k} | ' + ' | '.join(f"{100 * c['label'][t].get(k, 0.0):.1f}%" for t in typ) + ' |')
    L += ['', '| S4 row | ' + ' | '.join(typ) + ' |', '|---|' + '---|' * len(typ)]
    rows = sorted(c['s4_row'][typ[0]], key=lambda k: -sum(c['s4_row'][t][k] for t in typ))
    for k in rows:
        L.append(f'| {k} | ' + ' | '.join(f"{100 * c['s4_row'][t][k]:.1f}%" for t in typ) + ' |')
    L += ['', '## Horup et al. (2025) SI Table S4 rows used (relative to 2025; sheet "Table S4", column C)', '',
          '| S4 row | cells | 2030 | 2040 | 2050 | change by 2050 |', '|---|---|---|---|---|---|']
    for m, v in sorted(res['s4_rows'].items()):
        cells = f"{v[2025]['cell']}:{v[2050]['cell']}"
        L.append(f"| {m} | {cells} | {v[2030]['rel_to_2025']:.4f} | {v[2040]['rel_to_2025']:.4f} | "
                 f"{v[2050]['rel_to_2025']:.4f} | {100 * (v[2050]['rel_to_2025'] - 1):+.1f}% |")
    with open(os.path.join(OUT, 'DECARB_MODES.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
