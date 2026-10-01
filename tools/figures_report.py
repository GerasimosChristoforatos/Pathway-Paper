"""Report figures (v1.1.1) and FIGURES.md, generated from model runs and outputs/.

    python tools/figures_report.py

fig_reality_checks, fig_bridge, fig_scenarios, fig_conversion_chain,
fig_validation -> outputs/figures/; outputs/reality_checks.md/.json (where the
projection leaves the 1991-2025 range); FIGURES.md (one line per figure).
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
    fig, ax = plt.subplots(2, 3, figsize=(18, 10))
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
           '\nAppendix: demolition (BRANZ rate) vs residual -- only their SUM is identified by the census data')

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
            if r['method'] in ('reference_s3_10', 'constant'):
                a.plot(yy, np.cumsum(r['predicted_path']) / 1e3, lw=1.6,
                       color='#C0392B' if r['method'] == 'reference_s3_10' else '#2E86AB',
                       label=f"{'reference (S3-10)' if r['method'] == 'reference_s3_10' else 'constant rate'}, "
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
    json.dump(rc, open(os.path.join(OUT, 'reality_checks.json'), 'w'), indent=2)
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
    desc = {
        'boss_01_population': 'Population history and projection (median, 5th-95th). Look for: the 2026 level shift from observed growth.',
        'boss_02_households': 'Households; 2019-25 dotted = estimated from consents; 2023 census anchor marked. Look for: the anchored join.',
        'boss_03_cumulative_gfa': 'Cumulative floor area with the population 5th-95th band. Look for: slope change after 2026.',
        'boss_04_annual_gfa': 'Annual floor area by typology and by demand band (signed stack). Look for: the near-term excess fading.',
        'boss_05_annual_carbon': 'Annual carbon by typology and by demand band. Look for: dashed total = typology total.',
        'boss_06_cumulative_carbon': 'Cumulative carbon by typology and by demand band.',
        'boss_07_typology_share': 'Typology floor-area shares, history and projection. Look for: held shares (reference) vs trend.',
        'boss_08_demographic_drivers': 'Household size (2019-25 estimated, dotted) and population drivers.',
        'boss_09_space_diagnostics': 'Dwelling size and space per person diagnostics.',
        'boss_10_material_flows': 'Carbon by material (soil separate). Look for: dominant materials.',
        'diag_1_people_households': 'People, households, household size; anchor and estimated years marked.',
        'diag_2_household_engines': 'Household methods compared.',
        'diag_3_stock_bucket': 'Stock identity: vacancy, dwellings by component, stock, net replacement with census-interval rates and the 2013-18 definition break.',
        'diag_4_floor_area': 'Floor area by demand band, history and projection; avoided as an outline.',
        'diag_5_carbon': 'Carbon decomposition.',
        'diag_6_checks': 'History reconstruction, the 2026->2027 handover vs historical changes, the 2026 out-of-sample check, factor consistency.',
        'diag_6b_appendix_vacancy_definition': 'Appendix: why empty-only vacancy (not residents away) is used.',
        'sens_1_tornado': 'One-at-a-time sensitivities (floor area and carbon). Look for: the largest bars.',
        'sens_2_paths': 'Annual paths of the largest sensitivities.',
        'mc_1_fan': 'Reference MC fan (5-95%). Look for: the width relative to the scenario spread.',
        'mc_3_sobol': 'Sobol indices (reference). Look for: population dominance.',
        'fig_reality_checks': 'Projection vs 1991-2025 range: completions, removals, people per new dwelling, m² per new resident, household size and vacancy, dwelling size and mix. Look for: lines leaving the grey band (outputs/reality_checks.md).',
        'fig_bridge': 'Waterfall of 2026-2050 floor area by reason (low / reference / storyline); demolition and residual merged as long-run replacement (net). Look for: how much the wave and excess add.',
        'fig_bridge_appendix_split': 'Appendix: the bridge with demolition and the long-run residual split; only their sum is identified.',
        'fig_scenarios': 'Annual floor area by scenario with the reference MC band and history; cumulative floor area and carbon (upfront vs later).',
        'fig_conversion_chain': 'Indices of population growth -> households -> dwellings -> floor area -> carbon, and carbon intensity per m². Look for: where the chain diverges.',
        'fig_validation': 'Hindcast cumulative dwellings from 2006/2013/2018 under a consistent vacancy definition (dotted: vacancy as published), and the 2026 check.'}
    files = sorted(f[:-4] for f in os.listdir(FIG) if f.endswith('.png'))
    L = ['# Figures (generated by tools/figures_report.py)', '', '| figure | what it shows / what to look for |', '|---|---|']
    L += [f"| `outputs/figures/{f}.png` | {desc.get(f, '(no description)')} |" for f in files]
    open(os.path.join(ROOT, 'FIGURES.md'), 'w').write('\n'.join(L) + '\n')
    print(f'figures_report: 5 figures, {len(files)} listed in FIGURES.md')


if __name__ == '__main__':
    main()
