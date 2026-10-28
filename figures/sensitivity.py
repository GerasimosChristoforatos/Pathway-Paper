"""Sensitivity figures (MODEL v4.3.1: ED4, ED5, SF9; SF11 of v4.3.0 dropped), from the data files only."""
import numpy as np
import matplotlib.pyplot as plt

import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S


# ---------------------------------------------------------------------------
# SF9 (SF10 of v4.3.0, D40): partial rank correlation of each Monte Carlo input
# ---------------------------------------------------------------------------
MC_IMPORTANCE_INPUT = {'carbon_index': 'carbon'}          # importance-table input id -> naming.MC_INPUT id
MC_RUNS = (('REF', N.SCENARIOS['REF'], S.REFERENCE), ('pathway_moderate', N.PATHWAY_RUNS['pathway-moderate'],
                                                      S.PATHWAY_SETTING['moderate']), ('TL', N.TL['TL'], S.TL))


def sf9_prcc():
    """PRCC of each Monte Carlo input (naming.MC_INPUT) with its 95% bootstrap interval, for the Reference, the
    Moderate Pathway and TL, on cumulative floor area, carbon and LoE of AR 2026-2050 (pathways/montecarlo_importance
    .csv). The percentile interval is drawn as it is (lo to hi): it need not contain the point estimate when the
    bootstrap distribution is skewed near |PRCC| = 1."""
    imp = D.csv('pathways/montecarlo_importance.csv')
    fig, ax = plt.subplots(1, 3, figsize=S.figsize('double', 72), sharey=True)
    inputs = list(dict.fromkeys(imp['input']))
    y = np.arange(len(inputs))
    have = [r for r in MC_RUNS if r[0] in set(imp['run'])]
    for a, out, letter, title in zip(ax, ('floor_area_Mm2', 'carbon_kt', 'LoE_AR'), 'abc',
                                     ('Floor area, cumulative', 'Embodied carbon, cumulative', N.LOE_AR)):
        for j, (run, lab, col) in enumerate(have):
            t = imp[(imp['run'] == run) & (imp['output'] == out)].set_index('input').loc[inputs]
            off = (j - (len(have) - 1) / 2) * 0.22
            a.hlines(y + off, t['prcc_lo'], t['prcc_hi'], color=col, lw=S.LW_THIN)
            a.plot(t['prcc'], y + off, 'o', ms=3, color=col, label=lab)
        a.axvline(0, color=S.INK, lw=S.LW_THIN)
        a.set_xlim(-1.05, 1.05)                     # MODEL v4.3.1: room for the markers at ±1 (were clipped)
        a.set_xticks([-1, -0.5, 0, 0.5, 1])
        a.set_xlabel('PRCC (95% bootstrap interval)', fontsize=S.FONT_SMALL)
        a.grid(axis='y', visible=False)
        P.panel(a, letter, title)
    ax[0].set_yticks(y)
    ax[0].set_yticklabels([N.MC_INPUT[MC_IMPORTANCE_INPUT.get(i, i)] for i in inputs], fontsize=S.FONT_SMALL)
    fig.legend(*ax[0].get_legend_handles_labels(), loc='lower center', ncol=len(have), frameon=False,
               fontsize=S.FONT_SMALL, bbox_to_anchor=(0.5, 0.0))
    P.centre_ticklabels(fig, ax[0])
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    S.save_figure(fig, 'SF9_prcc', note=f"Bootstrap resamples: {int(imp['bootstrap_resamples'].iloc[0])}; SRC and R² "
                                         'in the data file.', source=['pathways/montecarlo_importance.csv'])


# ---------------------------------------------------------------------------
# MODEL v4.3.0: ED4 (one at a time, carbon) and ED5 (boundary definitions, LoE): paired tornados
# ---------------------------------------------------------------------------
# data row (sensitivity/reference_carbon.csv: row, side) -> (input id of naming.INPUT_LABEL, role); role 'low' / 'high'
# = the input at its low / high end (the Fig7a rule: the Stats NZ Low household-size variant is the input's low end),
# 'single' = one alternative case, ('tick', name) = an intermediate case. Version-history rows (MODEL v3.3 completion
# rate and lag, MODEL v2.1 never-absorbed overbuild) are dropped.
REF_ROWS = {
    ('Population: Stats NZ 5th / 95th percentile', 'low'): ('population', 'low'),
    ('Population: Stats NZ 5th / 95th percentile', 'high'): ('population', 'high'),
    ('Household size: Stats NZ High / Low variant', 'high'): ('hh_variant', 'low'),
    ('Household size: Stats NZ High / Low variant', 'low'): ('hh_variant', 'high'),
    ('Household size: 2018-2023 census pace', 'single'): ('hh_pace', 'single'),
    ('Household size after 2043: flat', 'single'): ('hh_after2043_flat', 'single'),
    ('Household size after 2043: secant-slope taper', 'single'): ('hh_after2043_secant', 'single'),
    ('Household size after 2043: taper from the PCHIP end slope', 'single'): ('hh_after2043_endslope', 'single'),
    ('Completion rate 0.93 / 0.96', 'low'): ('completion_rate', 'low'),
    ('Completion rate 0.93 / 0.96', 'high'): ('completion_rate', 'high'),
    ('Completion lag 15 / 19 months', 'low'): ('completion_lag', 'low'),
    ('Completion lag 15 / 19 months', 'high'): ('completion_lag', 'high'),
    ('No 2026 data', 'single'): ('no_2026', 'single'),
    ('No census under-construction correction', 'single'): ('uc_correction', 'single'),
    ('Dwelling-size window 2016-2025', 'single'): ('size_window', 'single'),
    ('2026 overbuild absorbed by 2030 / by 2045', 'low'): ('overbuild_timing', 'low'),
    ('2026 overbuild absorbed by 2030 / by 2045', 'high'): ('overbuild_timing', 'high'),
    ('Vacancy parameter: 1986-2023 census mean (one definition)', 'single'): ('vacancy_mean', 'single'),
    ('2026 overbuild booked as stock-neutral redevelopment', 'single'): ('overbuild_redev', 'single'),
    ('2026 overbuild gap vs the 2026 requirement', 'single'): ('overbuild_gap', 'single'),
    ('Low / High replacement', 'low'): ('replacement', 'low'),
    ('Low / High replacement', 'high'): ('replacement', ('tick', 'High')),
    ('Very High replacement (trend continues)', 'single'): ('replacement', 'high'),
    ('Replacement half-life 5 / 15 yr', 'low'): ('half_life', 'low'),
    ('Replacement half-life 5 / 15 yr', 'high'): ('half_life', 'high'),
    ('Single case study: lowest / highest', 'low'): ('single_case', 'low'),
    ('Single case study: lowest / highest', 'high'): ('single_case', 'high'),
    ('Case studies: jackknife low / high', 'low'): ('jackknife', 'low'),
    ('Case studies: jackknife low / high', 'high'): ('jackknife', 'high'),
    ('Frozen technology (2025 factors held)', 'single'): ('frozen', 'single'),
    ('Decarbonisation: proxy-mapped items held', 'single'): ('proxy_held', 'single'),
    ('Decarbonisation: NZ-made electricity-intensive items held', 'single'): ('nz_made_held', 'single'),
    ('Soil order: lowest (Raw) / highest (Organic)', 'low'): ('soil_order', 'low'),
    ('Soil order: lowest (Raw) / highest (Organic)', 'high'): ('soil_order', 'high'),
    ("A4-A5 on each item's own path / held at 2025", 'low'): ('a4a5', 'low'),
    ("A4-A5 on each item's own path / held at 2025", 'high'): ('a4a5', 'high'),
    ('Soil carbon loss on all floor area, including replacement', 'single'): ('soil_all', 'single'),
    ('Event timing L / n', 'single'): ('event_timing', 'single'),
}
REF_DROPPED = ('Completion rate 0.95 (MODEL v3.3)', 'Completion lag 0 months (MODEL v3.3)',
               '2026 overbuild never absorbed (MODEL v2.1 Reference)')
GROUP_RENAME = {'Replacement scenario': 'Replacement'}
# sensitivity/planetary_boundary.csv rows -> (input id, role, group); the AR base-window rows are one row (shortest
# window = low end, longest = high end, the others ticks), as in Fig7a
PB_ROWS = {
    ('SOS / I_glob pair C: 1 W/m² planetary boundary', 'single'): ('carrying_capacity', 'single', 'Carrying capacity'),
    ('GDP per capita in current US$', 'single'): ('gdp_current', 'single', 'Economic allocation'),
    ('α = 1 (Hjalsted et al. SI tables)', 'single'): ('alpha_1', 'single', 'Economic allocation'),
    ('s_sec with the FCE share as a ratio of sums', 'single'): ('sector_share', 'single', 'Economic allocation'),
    ('NZ population: raw Stats NZ 2024-base median', 'single'): ('pop_source_raw', 'single', 'Population'),
    ('NZ population: WPP 2024 median', 'single'): ('pop_source_wpp', 'single', 'Population'),
    ('Population: Stats NZ 5th / 95th percentile (carbon and boundaries together)', 'low'): ('population', 'low',
                                                                                             'Population'),
    ('Population: Stats NZ 5th / 95th percentile (carbon and boundaries together)', 'high'): ('population', 'high',
                                                                                              'Population'),
    ('Low / High replacement', 'low'): ('replacement', 'low', 'Replacement'),
    ('Low / High replacement', 'high'): ('replacement', ('tick', 'High'), 'Replacement'),
    ('Very High replacement (trend continues)', 'single'): ('replacement', 'high', 'Replacement'),
    ('Replacement half-life 5 / 15 yr', 'low'): ('half_life', 'low', 'Replacement'),
    ('Replacement half-life 5 / 15 yr', 'high'): ('half_life', 'high', 'Replacement'),
}


def _collect(items):
    """[(id, role, group, value)] -> [row dict] (one per id)."""
    out = {}
    for rid, role, group, v in items:
        r = out.setdefault(rid, dict(id=rid, group=group, ticks={}))
        if isinstance(role, tuple):
            r['ticks'][role[1]] = v
        else:
            r[role] = v
    return list(out.values())


def _input_label(rid):
    return N.INPUT_LABEL.get(rid, rid)


def ed4_one_at_a_time():
    """MODEL v4.3.0 (ED4, from D16): every one-at-a-time row of the Reference on the cumulative embodied carbon
    2026-2050 (kt CO2e) as a paired tornado grouped by category (sensitivity/reference_carbon.csv)."""
    r = D.csv('sensitivity/reference_carbon.csv')
    c0 = float(r['central_carbon_kt'].iloc[0])
    items, unmapped = [], []
    for _, x in r.iterrows():
        if x['row'] in REF_DROPPED:
            continue
        key = (x['row'], x['side'])
        if key not in REF_ROWS:
            unmapped.append(key)
            continue
        rid, role = REF_ROWS[key]
        items.append((rid, role, GROUP_RENAME.get(x['group'], x['group']), float(x['carbon_kt'])))
    if unmapped:
        raise SystemExit(f'STOP: ED4: rows without a display name: {unmapped}')
    rows = _collect(items)
    order = P.tornado_rows(N.SENSITIVITY_GROUPS, rows, c0)
    fig, ax = plt.subplots(figsize=S.figsize('double', 175))
    P.tornado(ax, order, c0, _input_label)
    ax.tick_params(axis='y', labelsize=S.FONT_MIN + 0.5)
    ax.text(c0, 1.0, f' Reference {c0:,.0f} kt', transform=ax.get_xaxis_transform(), ha='left', va='bottom',
            fontsize=S.FONT_SMALL, color=S.INK)
    ax.set_xlabel('Cumulative embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(ax.xaxis)
    ax.legend(handles=P.tornado_legend(), loc='lower right', fontsize=S.FONT_SMALL, frameon=False)
    P.centre_ticklabels(fig, ax)
    fig.tight_layout()
    S.save_figure(fig, 'ED4_one_at_a_time',
                  note=f'Reference {c0:,.0f} kt. One at a time: not additive, not a joint interval. "No effect": every '
                       f'case within {100 * P.NO_EFFECT_RTOL:.2f}% of the Reference. Version-history rows (completion '
                       'rate 0.95 and lag 0 months of MODEL v3.3; the never-absorbed overbuild of MODEL v2.1) are not '
                       'shown.', source=['sensitivity/reference_carbon.csv'])


def ed5_boundary_sensitivity():
    """MODEL v4.3.0 (ED5, from D42): the boundary-definition and AESA rows on the cumulative LoE of AR (a) and of AtP
    (b), paired tornados with shared y labels (sensitivity/planetary_boundary.csv)."""
    r = D.csv('sensitivity/planetary_boundary.csv')
    st = D.js('aesa/results.json')['settings']
    c = {'LoE_AR': float(r['central_LoE_AR'].iloc[0]), 'LoE_AtP': float(r['central_LoE_AtP'].iloc[0])}
    bw = r[r['group'] == 'Base window'].copy()
    bw['n'] = bw['row'].str.extract(r'(\d{4})-(\d{4})').astype(int).pipe(lambda t: t[1] - t[0] + 1)
    bw = bw.sort_values('n')
    ar_id = N.AR_WINDOW_LABEL.format(short=int(bw['n'].iloc[0]), long=int(bw['n'].iloc[-1]))
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', 110), sharey=True)
    for a, q, xl, letter in ((ax[0], 'LoE_AR', N.LOE_AR, 'a'), (ax[1], 'LoE_AtP', N.LOE_ATP, 'b')):
        items, unmapped = [], []
        for _, x in r.iterrows():
            if x['group'] == 'Base window':
                continue
            key = (x['row'], x['side'])
            if key not in PB_ROWS:
                unmapped.append(key)
                continue
            rid, role, g = PB_ROWS[key]
            items.append((rid, role, g, float(x[q])))
        if unmapped:
            raise SystemExit(f'STOP: ED5: rows without a display name: {unmapped}')
        for k, (_, x) in enumerate(bw.iterrows()):
            role = 'low' if k == 0 else ('high' if k == len(bw) - 1 else ('tick', f"{int(x['n'])} yr"))
            items.append((ar_id, role, 'AR base window', float(x[q])))
        rows = _collect(items)
        order = P.tornado_rows(N.BOUNDARY_SENSITIVITY_GROUPS, rows, c[q])
        P.tornado(a, order, c[q], _input_label, headers=(q == 'LoE_AR'))
        a.text(c[q], 1.0, f' Reference {c[q]:.2f}', transform=a.get_xaxis_transform(), ha='left', va='bottom',
               fontsize=S.FONT_SMALL, color=S.INK)
        a.set_xlabel(f'{xl} 2026–2050')
        P.panel(a, letter, '')
    ax[0].tick_params(axis='y', labelsize=S.FONT_MIN + 0.5)
    ax[1].legend(handles=P.tornado_legend(), loc='lower right', fontsize=S.FONT_SMALL, frameon=False)
    P.centre_ticklabels(fig, ax[0])
    fig.tight_layout()
    S.save_figure(fig, 'ED5_boundary_sensitivity',
                  note=f"Reference cumulative LoE of AR {c['LoE_AR']:.2f}, of AtP {c['LoE_AtP']:.2f}; AR base window "
                       f"central {st['AR_BASE_WINDOW'][0]}-{st['AR_BASE_WINDOW'][1]}. 'No effect': within "
                       f'{100 * P.NO_EFFECT_RTOL:.2f}% of the Reference (the economic-allocation rows move AtP only, '
                       'the AR base window moves AR only).', source=['sensitivity/planetary_boundary.csv',
                                                                     'aesa/results.json'])


FIGURES = {'ED4_one_at_a_time': ed4_one_at_a_time, 'ED5_boundary_sensitivity': ed5_boundary_sensitivity,
           'SF9_prcc': sf9_prcc}   # MODEL v4.3.1: SF11 dropped
