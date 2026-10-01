"""Report figures and FIGURES.md, generated from model runs and outputs/.

    python tools/figures_report.py

fig_reality_checks, fig_bridge (+ appendix split), fig_replacement_rate,
fig_scenarios, fig_conversion_chain, fig_validation -> outputs/figures/;
outputs/reality_checks.md/.json (where the projection leaves the 1991-2025
range); FIGURES.md (one line per figure, paper candidates / supplementary).
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import engine  # noqa: E402
import validation  # noqa: E402

OUT = os.path.join(ROOT, 'outputs')
FIG = os.path.join(OUT, 'figures')
SCEN = [('S1', 'low (S1)', dict(REPLACEMENT_SCENARIO='S1'), '#2E86AB'),
        ('S3-10', 'reference (S3-10)', dict(REPLACEMENT_SCENARIO='S3', S3_HALF_LIFE=10.0), '#C0392B'),
        ('S2', 'storyline: intensification continues (S2 + trend)', dict(REPLACEMENT_SCENARIO='S2'), '#27AE60'),
        ('S2-held', 'high (S2, shares held)', dict(REPLACEMENT_SCENARIO='S2', MIX_MODE='held'), '#8E44AD')]
M6 = 1e6


def series(B):
    """Annual quantities, history (1991-2025) and projection (2026-2050)."""
    E, R = B['engine_out']['50th'], B['results']['50th']
    fy = np.asarray(B['forecast_years'])
    yh = np.asarray(B['years_hist'])
    c = float(B['_completion'])
    pop_f = pd.Series(E['pop'], index=fy)
    hp = B['hist_pop']
    long_rate = float(B['demolition_rate'] + B['unconsented_rate'])
    wave = (np.asarray(B['rate_path'], float) - long_rate) * E['prev']
    p = dict(
        built=pd.Series(engine.requirement(E), index=fy),
        removals_net=pd.Series(E['demol'] + E['unc'] + E['join_redev'], index=fy),
        removals_gross=pd.Series(E['demol'] + wave + E['join_redev'], index=fy),
        dpop=pop_f.diff(), gfa=pd.Series(R['total'], index=fy),
        S=pd.Series(E['S'], index=fy),
        # effective vacancy: the stock-adding near-term excess raises it above the exogenous rate
        v=pd.Series(100 * (1 - np.asarray(E['hh']) / (np.asarray(E['stock']) + np.asarray(E['stock_join']))), index=fy),
        size=pd.Series(R['total'] / np.where(E['dwell_in_scope'] == 0, np.nan, E['dwell_in_scope']), index=fy),
        dense=100 * (1 - B['evolving_gfa_shares']['Detached']),
        carbon=pd.Series(E['carbon'], index=fy), d_hh=pd.Series(E['d_hh'], index=fy),
        stock_2025=float(E['stock'][0]))
    built_h = c * B['hist_units_all_c']
    cr = B['census_rates']
    rem_h = pd.Series(np.nan, index=yh, dtype=float)
    for r in cr.itertuples():                        # census-interval net removals, annualised
        rem_h[(yh > r.y0) & (yh <= r.y1)] = (r.built - r.d_stock) / (r.y1 - r.y0)
    h = dict(built=built_h, removals_net=rem_h, dpop=hp.diff(), gfa=B['hist_built_gfa'],
             S=B['hist_S'], v=100 * B['stock_cal']['v'], size=B['hist_built_gfa'] / B['hist_built_units'],
             dense=100 * (1 - B['hist_shares']['Detached']))
    return p, h


def range_check(hist, proj, years=(2026, 2050)):
    h = hist.loc[1991:2025].replace([np.inf, -np.inf], np.nan).dropna()
    q = proj.loc[years[0]:years[1]].replace([np.inf, -np.inf], np.nan).dropna()
    lo, hi = float(h.min()), float(h.max())
    above, below = q[q > hi], q[q < lo]
    return dict(hist_min=lo, hist_max=hi, years_outside=int(len(above) + len(below)),
                max_above_pct=float(100 * (above.max() / hi - 1)) if len(above) and hi else 0.0,
                max_below_pct=float(100 * (1 - below.min() / lo)) if len(below) and lo else 0.0,
                first_outside=int(min(list(above.index) + list(below.index))) if len(above) + len(below) else None)


def shade(ax, hist):
    h = hist.loc[1991:2025].replace([np.inf, -np.inf], np.nan).dropna()
    ax.axhspan(h.min(), h.max(), color='grey', alpha=0.12, label='1991-2025 range')
    ax.axvline(2025.5, color='grey', lw=0.7, ls=':')


def main():
    os.makedirs(FIG, exist_ok=True)
    runs = {}
    for k, lab, s, col in SCEN:
        B = validation.run_boss(**s)
        runs[k] = dict(B=B, lab=lab, col=col, p=series(B)[0])
    hist = series(runs['S3-10']['B'])[1]
    ref = runs['S3-10']

    # ---- 5. reality checks -------------------------------------------------
    rc = {}
    fig, ax = plt.subplots(2, 4, figsize=(24, 10))
    fig.suptitle('Reality checks: projection vs 1991-2025 history (grey band = historical min-max)', fontsize=13)
    panels = [
        ('built', ax[0, 0], 'Dwellings completed per year (in scope + RV)', 'thousand dwellings', 1e3,
         lambda p: p['built']),
        ('removals_net', ax[0, 1], 'Implied net removals per year\n(demolition + residual + wave + near-term excess)',
         'thousand dwellings', 1e3, lambda p: p['removals_net']),
        ('ppl_per_dw', ax[0, 2], 'People per new dwelling (population growth / dwellings built)', 'persons', 1,
         lambda p: p['dpop'] / p['built']),
        ('m2_per_res', ax[1, 0], 'New floor area per additional resident', 'm² per person', 1,
         lambda p: p['gfa'] / p['dpop']),
        ('S', ax[1, 1], 'Household size (left) and vacancy rate (right, dashed)', 'persons per household', 1,
         lambda p: p['S']),
        ('size', ax[1, 2], 'Average new-dwelling size (left) and non-detached share of floor area (right, dashed)',
         'm² per dwelling', 1, lambda p: p['size'])]
    hist_of = dict(built=hist['built'], removals_net=hist['removals_net'], ppl_per_dw=hist['dpop'] / hist['built'],
                   m2_per_res=hist['gfa'] / hist['dpop'], S=hist['S'], size=hist['size'])
    for key, a, title, unit, sc, f in panels:
        hs = hist_of[key]
        shade(a, hs / sc)
        a.plot(hs.index, hs / sc, color='black', lw=1.8, label='history')
        for k in ('S1', 'S3-10', 'S2'):
            r = runs[k]
            y = f(r['p']).loc[2026:]
            a.plot(y.index, y / sc, color=r['col'], lw=2 if k == 'S3-10' else 1.3, label=r['lab'])
            rc.setdefault(k, {})[key] = range_check(hs, f(r['p']))
        a.set_title(title, fontsize=10); a.set_ylabel(unit); a.grid(alpha=0.3); a.set_xlim(1991, 2050)
        a.ticklabel_format(axis='y', style='plain', useOffset=False)
    for k in ('S1', 'S3-10', 'S2'):
        rc[k]['vacancy'] = range_check(hist['v'], runs[k]['p']['v'])
    # cumulative removals as % of 2025 stock by 2050 (gross: demolition + wave + near-term excess)
    txt = '\n'.join(f"{runs[k]['lab']}: {100 * runs[k]['p']['removals_gross'].loc[2026:].sum() / runs[k]['p']['stock_2025']:.1f}%"
                    for k in ('S1', 'S3-10', 'S2'))
    ax[0, 1].text(0.02, 0.97, 'Cumulative removals 2026-50\n(% of 2025 stock):\n' + txt, transform=ax[0, 1].transAxes,
                  va='top', fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='#ccc'))
    t = ax[1, 1].twinx()
    t.plot(hist['v'].index, hist['v'], color='black', ls='--', lw=1)
    for k in ('S1', 'S3-10', 'S2'):
        vv = runs[k]['p']['v'].loc[2026:]
        t.plot(vv.index, vv, color=runs[k]['col'], ls='--', lw=1)
    t.set_ylabel('vacancy (% of private dwellings)')
    t2 = ax[1, 2].twinx()
    t2.plot(hist['dense'].index, hist['dense'], color='black', ls='--', lw=1)
    for k in ('S1', 'S3-10', 'S2'):
        d = runs[k]['p']['dense'].loc[2026:]
        t2.plot(d.index, d, color=runs[k]['col'], ls='--', lw=1)
    t2.set_ylabel('townhouses + apartments, % of floor area')
    ax[0, 0].legend(fontsize=8, loc='upper left')
    _m2 = (hist['gfa'] / hist['dpop']).loc[1991:2025]
    ax[1, 0].set_ylim(0, 300)
    ax[1, 0].text(0.02, 0.97, f"off-scale: {int(_m2.idxmax())} = {_m2.max():,.0f} m²/person (near-zero population growth)",
                  transform=ax[1, 0].transAxes, va='top', fontsize=8)
    # the 2026 (observed) -> 2027 (model) handover against historical year-to-year changes
    a = ax[0, 3]
    Bref = ref['B']
    chg = 100 * Bref['hist_total_gfa'].pct_change().loc[1992:2025].values
    R0 = Bref['results']['50th']['total']
    step = 100 * (R0[2] / R0[1] - 1)
    a.hist(chg, bins=14, color='#bdc3c7', edgecolor='white')
    a.axvline(step, color='#C0392B', lw=2.5, label=f'2026->2027 handover (observed -> model): {step:+.1f}%')
    a.axvline(np.median(chg), color='black', lw=1, ls='--', label=f'median year 1992-2025: {np.median(chg):+.1f}%')
    a.set_title('Handover 2026 -> 2027 (reference) vs annual changes\nin consented floor area, 1992-2025', fontsize=10)
    a.set_xlabel('% change from previous year'); a.set_ylabel('number of years'); a.grid(alpha=0.3)
    a.legend(fontsize=8)
    handover = dict(step_2026_2027_pct=float(step), hist_median_pct=float(np.median(chg)),
                          hist_min_pct=float(chg.min()), hist_max_pct=float(chg.max()))
    ax[1, 3].axis('off')
    plt.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_reality_checks.png'), dpi=130); plt.close(fig)

    # ---- 6. bridge ---------------------------------------------------------
    def bridge(steps, fname, note):
        fig, ax = plt.subplots(1, 3, figsize=(19, 6), sharey=True)
        fig.suptitle('Bridge: 2026-2050 floor area by reason for building (Mm²)' + note, fontsize=12)
        for a, k in zip(ax, ('S1', 'S3-10', 'S2')):
            R = runs[k]['B']['results']['50th']
            vals = [sum(float(np.sum(R[x][1:])) for x in keys) / M6 for keys, _ in steps]
            cum = 0.0
            for i, (v, (_, lab)) in enumerate(zip(vals, steps)):
                a.bar(i, v, bottom=cum if v >= 0 else cum + v, color='#2E86AB' if v >= 0 else '#C0392B')
                a.text(i, cum + max(v, 0) + 0.5, f'{v:+.1f}', ha='center', fontsize=7.5)
                cum += v
            a.bar(len(steps), cum, color='black')
            a.text(len(steps), cum + 0.5, f'{cum:.1f}', ha='center', fontsize=8, fontweight='bold')
            a.set_xticks(range(len(steps) + 1))
            a.set_xticklabels([l for _, l in steps] + ['Total'], rotation=60, ha='right', fontsize=8)
            a.set_title(runs[k]['lab']); a.grid(alpha=0.3, axis='y')
        ax[0].set_ylabel('Mm² (2026-2050)')
        plt.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=130); plt.close(fig)
    common = [(('growth',), 'Growth'), (('hs_pos',), 'House-splitting'), (('extra',), 'Extra space'),
              (('vac',), 'Vacancy')]
    tail = [(('wave',), 'Redevelopment wave'), (('join',), 'Near-term excess'), (('rv',), 'RV (out of scope)')]
    bridge(common + [(('repl', 'unc'), 'Long-run replacement (net)')] + tail, 'fig_bridge.png', '')
    bridge(common + [(('repl',), 'Demolition replacement'), (('unc',), 'Long-run residual')] + tail,
           'fig_bridge_appendix_split.png',
           '\nAppendix: split assumes the BRANZ demolition rate -- only the SUM is identified by the census data')

    # ---- replacement rate: census record and scenario paths ----------------
    Bref = ref['B']
    long_rate = float(Bref['demolition_rate'] + Bref['unconsented_rate'])
    fy = np.asarray(Bref['forecast_years'])
    fig, a = plt.subplots(figsize=(11, 5.5))
    for i, r in enumerate(Bref['census_rates'].itertuples()):
        a.hlines(100 * r.rate, r.y0, r.y1, color='black', lw=2.5,
                 label='census intervals (dwelling counts, UC-corrected)' if i == 0 else None)
    for k, scen, hl in (('S1', 'S1', 10.0), ('S3-10', 'S3', 10.0), ('S2', 'S2', 10.0)):
        path = engine.replacement_path(scen, long_rate, float(Bref['rate_recent']), fy, hl)
        a.plot(fy, 100 * path, color=runs[k]['col'], lw=2 if k == 'S3-10' else 1.5, label=runs[k]['lab'])
    a.axhline(100 * Bref['demolition_rate'], color='#7f8c8d', ls='--', lw=1.3,
              label=f"BRANZ demolition rate {100 * Bref['demolition_rate']:.3f}%")
    a.axhline(0, color='black', lw=0.6)
    a.axvspan(2013, 2018, color='#f1c40f', alpha=0.15, label='2013->2018: census empty/away definition break')
    a.axvline(2025.5, color='grey', lw=0.7, ls=':')
    a.set_xlim(1986, 2050); a.grid(alpha=0.3)
    a.set_ylabel('% of last year\'s stock per year')
    a.set_title('Net replacement rate (demolition net of unconsented additions): census record and scenario paths')
    a.legend(fontsize=8, loc='upper left')
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    _w = validation.Boss.NET_REPLACEMENT_WINDOW
    fig.text(0.5, 0.01, f"Long run {_w[0]}-{_w[1]}: "
             f"{100 * long_rate:.3f}%/yr; 2018-23: {100 * Bref['rate_recent']:.3f}%/yr. Each step is one intercensal "
             f"interval; the 2018-23 step is a single interval.", ha='center', fontsize=8.5, style='italic')
    fig.savefig(os.path.join(FIG, 'fig_replacement_rate.png'), dpi=130); plt.close(fig)

    # ---- 7. scenarios ------------------------------------------------------
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.5), gridspec_kw=dict(width_ratios=[2, 1, 1]))
    a = ax[0]
    a.plot(hist['gfa'].index, hist['gfa'] / M6, color='black', lw=1.8, label='history (built)')
    mc = os.path.join(OUT, 'montecarlo_annual.csv')
    if os.path.exists(mc):
        m = pd.read_csv(mc, index_col=0).loc[2026:]
        a.fill_between(m.index, m['gfa_5'] / M6, m['gfa_95'] / M6, color=ref['col'], alpha=0.15,
                       label='reference MC 5-95%')
    for k, r in runs.items():
        g = r['p']['gfa'].loc[2026:]
        a.plot(g.index, g / M6, color=r['col'], lw=2 if k == 'S3-10' else 1.3, label=r['lab'])
    a.set_title('Annual floor area built'); a.set_ylabel('Mm² per year'); a.grid(alpha=0.3); a.legend(fontsize=8)
    ks = list(runs)
    a = ax[1]
    a.bar(range(len(ks)), [runs[k]['p']['gfa'].loc[2026:].sum() / M6 for k in ks], color=[runs[k]['col'] for k in ks])
    short = {'S1': 'low', 'S3-10': 'reference', 'S2': 'storyline', 'S2-held': 'high'}
    a.set_xticks(range(len(ks))); a.set_xticklabels([short[k] for k in ks]); a.set_title('Cumulative floor area 2026-2050')
    a.set_ylabel('Mm²'); a.grid(alpha=0.3, axis='y')
    a = ax[2]
    up = [float(runs[k]['B']['_upfront'] + runs[k]['B']['_soil'] / M6) for k in ks]
    tot = [float(runs[k]['B']['tot_carbon_median']) for k in ks]
    a.bar(range(len(ks)), up, color='#34495E', label='upfront (A1-A5 + soil)')
    a.bar(range(len(ks)), np.subtract(tot, up), bottom=up, color='#BDC3C7', label='later stages (B, C)')
    a.set_xticks(range(len(ks))); a.set_xticklabels([short[k] for k in ks]); a.set_title('Cumulative carbon 2026-2050')
    a.set_ylabel('kt CO₂e'); a.legend(fontsize=8); a.grid(alpha=0.3, axis='y')
    plt.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_scenarios.png'), dpi=130); plt.close(fig)

    # ---- 8. conversion chain -----------------------------------------------
    p = ref['p']
    yrs = np.arange(2027, 2051)
    chain = [('population growth', p['dpop'], '-'), ('households formed', p['d_hh'], '-'),
             ('dwellings built', p['built'], '--'), ('floor area', p['gfa'], '-'), ('carbon', p['carbon'], '-')]
    fig, ax = plt.subplots(1, 2, figsize=(16, 5.5))
    for lab, s_, ls in chain:
        s_ = s_.loc[yrs]
        ax[0].plot(yrs, 100 * s_ / s_.loc[2027], lw=2.2 if ls == '--' else 1.8, ls=ls, label=lab)
    ax[0].axhline(100, color='black', lw=0.6)
    ax[0].set_title('Conversion chain, reference path (index, 2027 = 100)'); ax[0].legend(); ax[0].grid(alpha=0.3)
    ax[0].text(0.02, 0.03, '2026 is not used as the base: it is observed building and carries the one-off\n'
               'population shortfall and the near-term market excess.', transform=ax[0].transAxes, fontsize=8)
    lo, hi = np.inf, -np.inf
    for k in ('S3-10', 'S2', 'S2-held'):
        ci = (runs[k]['p']['carbon'] / runs[k]['p']['gfa']).loc[2026:2050]
        ax[1].plot(ci.index, ci, color=runs[k]['col'], lw=2, label=runs[k]['lab'])
        lo, hi = min(lo, ci.min()), max(hi, ci.max())
    pad = 0.15 * max(hi - lo, 1.0)
    ax[1].set_ylim(lo - pad, hi + pad)
    ax[1].set_title('Average carbon intensity of new floor area (typology mix effect only)')
    ax[1].set_ylabel('kg CO₂e per m²'); ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8)
    plt.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_conversion_chain.png'), dpi=130); plt.close(fig)

    # ---- 9. validation -----------------------------------------------------
    from matplotlib.ticker import MaxNLocator
    v = json.load(open(os.path.join(OUT, 'validation.json')))
    pub = v.get('hindcast_as_published') or []
    fig, ax = plt.subplots(1, 4, figsize=(20, 4.8))
    for a, o in zip(ax[:3], (2006, 2013, 2018)):
        rows = [r for r in v['hindcast'] if r['origin'] == o and 'years' in r]
        if not rows:
            continue
        yy = rows[0]['years']
        a.plot(yy, np.cumsum(rows[0]['actual_path']) / 1e3, color='black', lw=2, label='actual')
        for r in rows:
            if r['method'] in ('reference_s3_10', v['model_method']):
                a.plot(yy, np.cumsum(r['predicted_path']) / 1e3, lw=1.6,
                       color='#C0392B' if r['method'] == 'reference_s3_10' else '#2E86AB',
                       label=f"{'reference (S3-10)' if r['method'] == 'reference_s3_10' else 'S1 (census dwelling-count rate)'}, "
                             f"consistent vacancy {r['error_pct']:+.1f}%")
        for r in pub:
            if r['origin'] == o and r['method'] == 'reference_s3_10' and 'years' in r:
                a.plot(r['years'], np.cumsum(r['predicted_path']) / 1e3, lw=1.2, ls=':', color='#C0392B',
                       label=f"reference, vacancy as published {r['error_pct']:+.1f}%")
        a.set_title(f'Hindcast from origin {o}: cumulative dwellings'); a.set_ylabel('thousand')
        a.xaxis.set_major_locator(MaxNLocator(integer=True))
        a.legend(fontsize=7.5); a.grid(alpha=0.3)
    c = v['check_2026']
    a = ax[3]
    if c.get('status') == 'observed':
        a.bar(['observed\nJan-Jul 2026', 'model\n(no 2026 data)'], [c['observed_ytd'], c['model_expected_ytd']],
              color=['black', '#95A5A6'])
        a.set_title(f"2026 check: ratio {c['ratio_observed_to_model']:.2f}")
    a.set_ylabel('dwellings consented'); a.grid(alpha=0.3, axis='y')
    plt.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_validation.png'), dpi=130); plt.close(fig)

    # ---- reality-check exceedances ----------------------------------------
    json.dump(dict(rc, handover=handover), open(os.path.join(OUT, 'reality_checks.json'), 'w'), indent=2)
    names = dict(built='dwellings completed', removals_net='net removals', ppl_per_dw='people per new dwelling',
                 m2_per_res='floor area per additional resident', S='household size', size='new-dwelling size',
                 vacancy='vacancy rate (effective, %)')
    L = ['# Reality checks (generated by tools/figures_report.py)', '',
         'Projection 2026-2050 against the 1991-2025 historical range (min-max).', '',
         '| scenario | quantity | historical range | years outside | first year outside | max above (%) | max below (%) |',
         '|---|---|---|---|---|---|---|']
    for k, d in rc.items():
        for q, r in d.items():
            L.append(f"| {k} | {names[q]} | {r['hist_min']:,.2f} to {r['hist_max']:,.2f} | {r['years_outside']} | "
                     f"{r['first_outside'] or '-'} | {r['max_above_pct']:.1f} | {r['max_below_pct']:.1f} |")
    open(os.path.join(OUT, 'reality_checks.md'), 'w').write('\n'.join(L) + '\n')

    # ---- FIGURES.md ---------------------------------------------------------
    paper = {
        'boss_03_cumulative_gfa': 'Cumulative built floor area, history and projection, with the population 5th-95th band.',
        'boss_04_annual_gfa': 'Annual floor area by typology and by demand type (in scope; RV units excluded by scaling).',
        'boss_05_annual_carbon': 'Annual embodied carbon by typology and by demand type (in scope).',
        'boss_10_material_flows': 'Carbon by material, annual and cumulative; soil (land-use change) on top.',
        'fig_bridge': 'Waterfall of 2026-2050 floor area by reason for building: low (S1) / reference (S3-10) / storyline (S2).',
        'fig_replacement_rate': 'Net replacement rate: census intervals (steps), S1 / S3-10 / S2 paths, BRANZ demolition rate.',
        'fig_scenarios': 'Annual floor area by scenario with the reference MC band; cumulative floor area and carbon.',
        'fig_reality_checks': 'Projection vs the 1991-2025 range (outputs/reality_checks.md) and the 2026->2027 handover.',
        'fig_validation': 'Hindcast of cumulative dwellings from 2006/2013/2018 (consistent vacancy) and the 2026 check.',
        'mc_1_fan': 'Within-scenario Monte Carlo fan (reference), history from 1991.',
        'sens_1_tornado': 'One-at-a-time sensitivities: scenarios, mix, household size, stock, near-term rule, carbon/soil bounds.'}
    supp = {
        'boss_01_population': 'Population history and projection (median, 5th-95th); the 2026 level shift from observed growth.',
        'boss_02_households': 'Households: census-benchmarked to 2018, 2019-23 scaled to the 2023 census, projection from 2023.',
        'boss_06_cumulative_carbon': 'Cumulative carbon by typology and by demand type (in scope).',
        'boss_07_typology_share': 'Typology floor-area shares, history and projection (held vs trend).',
        'boss_08_demographic_drivers': 'Household size (same history treatment as boss_02) and population vs household growth.',
        'boss_09_space_diagnostics': 'Realised vs occupied floor area per new dwelling; occupancy utilisation.',
        'diag_2_household_engines': 'Household size vs arrivals (partly mechanical between censuses); DHE/consent ratio; engines.',
        'diag_3_stock_bucket': 'Vacancy definitions, stock, and dwellings per year (history by census interval).',
        'diag_3b_appendix_vacancy_definition': 'Appendix: why empty-only vacancy (not residents away) is used.',
        'diag_4_floor_area': 'Floor area by typology and demand type (history by census interval), mix, dwelling size.',
        'diag_5_carbon': 'Carbon by typology and material (history estimated with 2025 factors); case-study intensities.',
        'fig_bridge_appendix_split': 'Appendix: the bridge with demolition and residual split (split assumes the BRANZ rate).',
        'fig_conversion_chain': 'Indices population -> households -> dwellings -> floor area -> carbon; intensity per m².',
        'mc_3_sobol': 'Sobol indices (reference): within-scenario parametric uncertainty only.',
        'sens_2_paths': 'Annual paths of the largest one-at-a-time sensitivities.'}
    files = sorted(f[:-4] for f in os.listdir(FIG) if f.endswith('.png'))
    unlisted = [f for f in files if f not in paper and f not in supp]
    missing = [f for f in list(paper) + list(supp) if f not in files]
    if unlisted or missing:
        raise SystemExit(f'FIGURES.md out of date: unlisted {unlisted}, missing {missing}')
    L = ['# Figures (generated by tools/figures_report.py)', '', 'All in `outputs/figures/`.', '',
         '## Paper candidates', '']
    L += [f'- `{f}.png`: {d}' for f, d in paper.items()]
    L += ['', '## Supplementary', '']
    L += [f'- `{f}.png`: {d}' for f, d in supp.items()]
    open(os.path.join(ROOT, 'FIGURES.md'), 'w').write('\n'.join(L) + '\n')
    print(f'figures_report: {len(files)} figures listed in FIGURES.md ({len(paper)} paper, {len(supp)} supplementary)')


if __name__ == '__main__':
    main()
