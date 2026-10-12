"""
KEY FIGURES (MODEL v2.1.0): K1-K6 and KEY_FIGURES.md
====================================================
The story of the model in six figures, drawn from the data files of outputs/data/ only (as paper.py, whose
panel functions, labels and saving it reuses, so a key figure can never disagree with the paper):

  K1  why floor area is built: demand bands, history per census interval and the Reference projection
  K2  the Reference carbon by life-cycle stage, by material and by demand band, and the emissions committed
      after 2050
  K3  annual emissions of the Reference (Monte Carlo 5-95% band), P1-P5 (Moderate) and TL against the AR and AtP
      boundaries, TL zero-building years shaded
  K4  the solution space (as Fig6)
  K5  the sequential waterfall Reference -> P1 -> P2 -> P3 -> P4 (= P5) -> full strength from 2027 -> TL1 ... TL10
      (= TL), each step segmented by its exact demand-band deltas, against the cumulative budgets
  K6  the schematic of levers, pathways and the theoretical limit (as Fig1)

Every planetary-boundary figure uses the boundary styling of style.py. Written to outputs/key_figures/ as PNG
(with run_all.py --export also PDF and source-data CSV).

    python key_figures.py      (run_all.py runs it after extended_data.py)
"""
import os
import sys
import textwrap

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import figure_plan as FP  # noqa: E402
import layout as L  # noqa: E402
import naming as N  # noqa: E402
import paper as PP  # noqa: E402
import plotting as P  # noqa: E402
import style as S  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

PLAN = {h['id']: h for h in FP.KEY_FIGURES}
REF = PP.REF
read_csv, read_json, check = PP.read_csv, PP.read_json, PP.check


def source(fid):
    return PP.Source(fid, L.KEY_FIGURES)


def save(fig, h, src):
    PP.save(fig, h['file'], src, h['width'])


def k1():
    h = PLAN['K1']
    src = source(h['file'])
    fig, a = plt.subplots(figsize=S.figsize('double', 92))
    ba = PP.bands_history_panel(a, src, letter='a')
    handles = P.band_handles([b for b in N.BANDS_IN_SCOPE if b != 'maintenance'])
    handles.append(Patch(label=N.UNEXPLAINED, **dict(PP.unexplained_style())))
    fig.legend(handles=handles, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.01), frameon=False,
               handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    save(fig, h, src)
    tot = ba.groupby('band')['floor_area_Mm2'].sum()
    share = tot[N.band_data_label('growth')] / tot.sum()
    return dict(caption=h['caption'] + f" Population growth, the only untargeted band, is {100 * share:.0f}% of the "
                f"{tot.sum():.1f} million m² built in 2026–2050. History: interval means between censuses; the hatched "
                'band is the building that household formation, vacancy and census-measured replacement leave '
                'unexplained.')


def k2():
    h = PLAN['K2']
    src = source(h['file'])
    fig = plt.figure(figsize=S.figsize('double', 150))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], hspace=0.55, wspace=0.35, left=0.08, right=0.92, bottom=0.17,
                          top=0.96)
    a, b, c, d = (fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2))
    PP.stage_panel(a, src, letter='a')
    PP.committed_panel(b, src, letter='b')
    PP.material_panel(c, src, letter='c')
    PP.bands_carbon_panel(d, src, letter='d')
    P.band_legend(fig, list(N.BANDS_IN_SCOPE), ncol=4, y=-0.005)
    save(fig, h, src)
    st = read_csv('baseline/annual_by_stage.csv')
    res = read_json('aesa/results.json')['committed'][REF]
    tot = float(sum(st[c_].sum() for _, c_ in PP.STAGE_COLS))
    return dict(caption=h['caption'] + f" (a) By stage and (b) cumulative: {tot:,.0f} kt CO₂e in 2026–2050 and a further "
                f"{res['lower_kt']:,.0f}–{res['upper_kt']:,.0f} kt committed after 2050 (hatched; not part of the level "
                'of exceedance). (c) By material, soil carbon loss on top. (d) By demand band, maintenance its own layer.')


def k3():
    h = PLAN['K3']
    src = source(h['file'])
    an = read_csv('pathways/annual.csv')
    an = an[an['scenario'] == REF]
    mca = read_csv('pathways/montecarlo_annual.csv')
    zero = PP.zero_building_years(an)
    yrs = list(range(PP.WINDOW[0], PP.WINDOW[1] + 1))
    fig, ax = plt.subplots(figsize=S.figsize('double', 100))
    d0 = an[an['run'] == REF].set_index('year').loc[yrs]
    P.boundary_lines(ax, yrs, d0['B_AR_kt'].values, d0['B_AtP_kt'].values)
    ax.axvspan(zero[0] - 0.5, zero[-1] + 0.5, facecolor='none', edgecolor=S.MUTED, hatch='////', lw=0, zorder=1)
    m = mca[mca['run'] == 'REF'].set_index('year').loc[yrs]
    ax.fill_between(yrs, m['carbon_kt_p5'], m['carbon_kt_p95'], color=S.REFERENCE, alpha=0.18, lw=0, zorder=2,
                    label='Reference, Monte Carlo 5–95%')
    src.add('a', 'Reference, Monte Carlo 5%', yrs, m['carbon_kt_p5'].values, 'kt CO2e per year')
    src.add('a', 'Reference, Monte Carlo 95%', yrs, m['carbon_kt_p95'].values, 'kt CO2e per year')
    for run in PP.STORY:
        d = an[an['run'] == run].set_index('year').loc[yrs]
        lw = S.LW_BOLD if run in (REF, 'P5-moderate', 'TL') else S.LW
        ax.plot(yrs, d['carbon_kt'], color=PP.colour(run), lw=lw, label=PP.label(run), zorder=4)
        src.add('a', PP.label(run), yrs, d['carbon_kt'].values, 'kt CO2e per year')
    src.add('a', N.METRICS['AR'] + ' boundary', yrs, d0['B_AR_kt'].values, 'kt CO2e per year')
    src.add('a', N.METRICS['AtP'] + ' boundary', yrs, d0['B_AtP_kt'].values, 'kt CO2e per year')
    src.add('a', 'TL zero-building years', zero, np.zeros(len(zero)), 'dwellings built')
    ax.set_yscale('log', nonpositive='clip')
    ax.set_ylim(20, 3000)
    ax.set_xlim(PP.WINDOW[0] - 0.5, PP.WINDOW[1] + 0.5)
    P.log_ticks(ax.yaxis, (20, 50, 100, 200, 500, 1000, 2000))
    ax.set_ylabel('Embodied carbon (kt CO₂e per year, log scale)')
    ax.text((zero[0] + zero[-1]) / 2, 22, f'TL builds nothing {zero[0]}–{zero[-1]}\n(released dwellings used)',
            ha='center', va='bottom', fontsize=S.FONT_SMALL, color=S.INK,
            bbox=dict(facecolor='white', edgecolor='none', pad=1.0, alpha=0.9), zorder=5)
    hd, _ = ax.get_legend_handles_labels()
    hd += S.zone_handles() + [Patch(facecolor='none', edgecolor=S.MUTED, hatch='////', label='TL zero-building years')]
    fig.legend(handles=hd, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.01), frameon=False, fontsize=S.FONT_SMALL)
    fig.tight_layout(rect=(0, 0.2, 1, 1))
    save(fig, h, src)
    return dict(caption=h['caption'] + ' Log scale; the TL line sits at the axis floor in its zero-building years (its '
                'value is zero). Shading: below AtP (darker green), between AtP and AR (light green), above AR (light '
                'red, boundary exceeded).')


def k4():
    h = PLAN['K4']
    return dict(caption=PP.fig6(h, L.KEY_FIGURES)['caption'])          # fig6 builds the caption on h['caption']


def k5():
    h = PLAN['K5']
    src = source(h['file'])
    w = read_csv('pathways/waterfall_sequential.csv')
    steps = w.drop_duplicates('step').sort_values('step')
    bands = list(w['band'].drop_duplicates())
    bid = {N.band_data_label(b): b for b in N.BANDS_IN_SCOPE}
    fig, ax = plt.subplots(figsize=S.figsize('double', 120))
    bar_ar, bar_atp = float(steps['B_AR_kt'].iloc[0]), float(steps['B_AtP_kt'].iloc[0])
    S.boundary_hzones(ax, bar_ar, bar_atp, label=False)
    width = 0.7
    labels = []
    totals_at = {'REF', 'P4', N_TL_LAST}
    xs = []
    x = 0
    prev_total = None                                   # set by the Reference step (the first)
    for _, srow in steps.iterrows():
        sid = srow['step_id']
        d = w[w['step'] == srow['step']].set_index('band')
        if sid == 'REF':
            P.signed_stack(ax, [x], [(bid[b], float(d.loc[b, 'carbon_kt'])) for b in bands], width=width)
            labels.append(N.SCENARIOS['REF'])
        else:
            cur = float(prev_total)
            for b in bands:
                dv = float(d.loc[b, 'delta_carbon_kt'])
                if dv == 0.0:
                    continue
                ax.bar(x, -dv, bottom=cur, width=width, **P.band_style(bid[b]))
                cur -= dv
                src.add('steps', f'{sid}: {N.BANDS[bid[b]]}', 'reduction', dv, 'kt CO2e 2026-2050')
            check(abs(cur - float(srow['total_carbon_kt'])) <= 1e-6 * max(1.0, cur),
                  f'K5: the band deltas of step {sid} do not reach its total')
            ax.plot([x - 1 + width / 2, x - width / 2], [prev_total, prev_total], color=S.MUTED, lw=S.LW_THIN)
            labels.append(textwrap.fill(srow['label'], 26))
        tot = float(srow['total_carbon_kt'])
        src.add('totals', srow['label'], 'carbon', tot, 'kt CO2e 2026-2050')
        if sid in totals_at:
            ax.text(x, tot, f'{tot:,.0f}\nLoE AR {srow["LoE_AR"]:.2f}', ha='center', va='bottom', fontsize=S.FONT_MIN)
        prev_total = tot
        xs.append(x)
        x += 1
    ax.axhline(0, color=S.INK, lw=S.LW_THIN)
    ax.set_ylim(0, float(steps['total_carbon_kt'].max()) * 1.09)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=90, fontsize=S.FONT_MIN, linespacing=1.0)
    ax.set_xlim(-0.6, xs[-1] + 0.6)
    ax.set_ylabel('Embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(ax.yaxis)
    ax.grid(axis='x', visible=False)
    P.band_legend(fig, list(N.BANDS_IN_SCOPE), ncol=4, y=-0.005,
                  extra=[Line2D([0], [0], **{k: v for k, v in S.BOUNDARY[b].items()}) for b in ('AR', 'AtP')])
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    save(fig, h, src)
    r = steps.set_index('step_id')
    return dict(caption=h['caption'] + f" Reference {r.loc['REF', 'total_carbon_kt']:,.0f} kt (LoE AR "
                f"{r.loc['REF', 'LoE_AR']:.2f}), P5 {r.loc['P4', 'total_carbon_kt']:,.0f} kt ({r.loc['P4', 'LoE_AR']:.2f}), "
                f"TL {r.loc[N_TL_LAST, 'total_carbon_kt']:,.0f} kt ({r.loc[N_TL_LAST, 'LoE_AR']:.2f}); cumulative AR "
                f"budget {bar_ar:,.0f} kt, AtP {bar_atp:,.0f} kt. A segment above its step's start marks a band that grows at "
                'that step (a lever shifts building between bands). In the TL steps the 2026-overbuild band also carries '
                'the banking adjustment (dwellings released by vacancy, larger households and the absorbed overbuild); in '
                'zero-building years every band is zero except the maintenance of the cohorts already built.')


def k6():
    h = PLAN['K6']
    PP.fig1(h, L.KEY_FIGURES)
    return dict(caption=h['caption'] + ' Arrows: the demand band or carbon quantity each lever acts on; colours: the '
                'pathway family (lever shades in the other figures). ' + N.TL_CAPTION.capitalize() + '.')


N_TL_LAST = 'TL10'
FIGURES = dict(K1=k1, K2=k2, K3=k3, K4=k4, K5=k5, K6=k6)


def write_md(rr):
    lines = ['# Key figures', '',
             '_Generated by key_figures.py from outputs/data/ (do not edit by hand): the story of the model in six '
             'figures. PNG 300 dpi; with run_all.py --export also vector PDF and source data. The paper figures: '
             '../paper/PAPER.md; Extended Data: ../extended_data/EXTENDED_DATA.md._', '']
    if PP.quick_run():
        lines += ['> **QUICK RUN, not for reporting** (run_all.py --quick: fewer Monte Carlo draws).', '']
    for h in FP.KEY_FIGURES:
        f = h['file']
        lines += [f"## {h['id']}. {N.typeset(h['title'])}", '', f'![{h["id"]}]({f}.png)', '',
                  f"**{h['id']}.** {N.typeset(rr[h['id']]['caption'])}", '',
                  f"Files: [{f}.png]({f}.png)" + (f", [{f}.pdf]({f}.pdf), source data [{f}.csv]({f}.csv)"
                                                    if S.export_run() else ' (PDF and source data: run_all.py --export)')
                  + f". Data (outputs/): {h['source']}.", '']
    with open(L.writing(os.path.join(L.KEY_FIGURES, 'KEY_FIGURES.md')), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


def main(only=None):
    rr = {}
    for k, fn in FIGURES.items():
        if only and k not in only:
            continue
        rr[k] = fn()
        print(f'key_figures: {k} {PLAN[k]["file"]}')
    if not only:
        write_md(rr)
        print('key_figures: outputs/key_figures/KEY_FIGURES.md')
    return rr


if __name__ == '__main__':
    main([a for a in sys.argv[1:] if a.startswith('K')] or None)
