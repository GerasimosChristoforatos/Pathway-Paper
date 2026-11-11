"""Sensitivity figures (ED4, ED5, SF8), from the data files only.

ED4 and ED5 carry row notes under the axes (row_notes_ed4 / row_notes_ed5): one line per shown row,
saying only what changes compared with the Reference. Every value is read from the model code (projection.py,
Building_factors.py, boundaries.py, Sensitivity.py: the settings each row changes) and the committed outputs
(baseline/projection.json and overbuild_2026.json settings, aesa/results.json settings, the case and basis columns);
where a setting is recorded in the outputs it must equal the code, and a row label must agree with the setting it
names, or the figure stops."""
import re

import numpy as np
import matplotlib.pyplot as plt

import naming as N
from figures import data as D
from figures import draw as P
from figures import style as S


# ---------------------------------------------------------------------------
# SF8 (data D40): partial rank correlation of each Monte Carlo input
# ---------------------------------------------------------------------------
MC_IMPORTANCE_INPUT = {'carbon_index': 'carbon'}          # importance-table input id -> naming.MC_INPUT id
MC_RUNS = (('REF', N.SCENARIOS['REF'], S.REFERENCE), ('pathway_moderate', N.PATHWAY_RUNS['pathway-moderate'],
                                                      S.PATHWAY_SETTING['moderate']), ('TL', N.TL['TL'], S.TL))


def sf8_prcc():
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
        a.set_xlim(-1.05, 1.05)                     # room for the markers at ±1 (were clipped)
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
    S.save_figure(fig, 'SF8_prcc', note=f"Bootstrap resamples: {int(imp['bootstrap_resamples'].iloc[0])}; SRC and R² "
                                         'in the data file.', source=['pathways/montecarlo_importance.csv'])


# ---------------------------------------------------------------------------
# ED4 (one at a time, carbon) and ED5 (boundary definitions, LoE): paired tornados
# ---------------------------------------------------------------------------
# data row (sensitivity/reference_carbon.csv: row, side) -> (input id of naming.INPUT_LABEL, role); role 'low' / 'high'
# = the input at its low / high end, 'single' = one alternative case, ('tick', name) = an intermediate case. The rows that only compare with superseded
# model settings (REF_DROPPED: the MODEL v3.3 completion rate and lag, the MODEL v2.1 never-absorbed overbuild) are
# not shown; the note under ED4 names them with their values.
REF_ROWS = {
    ('Population: Stats NZ 5th / 95th percentile', 'low'): ('population', 'low'),
    ('Population: Stats NZ 5th / 95th percentile', 'high'): ('population', 'high'),
    ('Living arrangements: propensities change (Stats NZ B)', 'single'): ('hh_propensity', 'single'),
    ('Household size: 2018-2023 census pace', 'single'): ('hh_pace', 'single'),
    ('After 2048: held flat (zero slope)', 'single'): ('hh_after2048_flat', 'single'),
    ('After 2048: PCHIP end slope', 'single'): ('hh_after2048_endslope', 'single'),
    ('Completion rate 0.93 / 0.96', 'low'): ('completion_rate', 'low'),
    ('Completion rate 0.93 / 0.96', 'high'): ('completion_rate', 'high'),
    ('Completion lag 15 / 19 months', 'low'): ('completion_lag', 'low'),
    ('Completion lag 15 / 19 months', 'high'): ('completion_lag', 'high'),
    ('No 2026 data', 'single'): ('no_2026', 'single'),
    ('No census under-construction correction', 'single'): ('uc_correction', 'single'),
    ('Dwelling-size window 2016-2025', 'single'): ('size_window', 'single'),
    ('No starting surplus', 'single'): ('start_surplus_none', 'single'),
    ('Starting surplus minus 2 SD', 'single'): ('start_surplus_m2sd', 'single'),
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
# rows kept in the data file but not shown in ED4 (display only), with the reason given in the note; the change of
# each row (data: change_pct) is quoted in the figure note.
REF_NOT_SHOWN = {'2026 overbuild gap vs the 2026 requirement': 'the overbuild gap measured against the 2026 '
                                                               'requirement',
                 'No census under-construction correction': 'no census under-construction correction',
                 'Event timing L / n': 'maintenance event timing L / n'}
GROUP_RENAME = {'Replacement scenario': 'Replacement'}


def ref_not_shown(r):
    """{row: reason} of the ED4 rows kept in the data file but not shown (REF_NOT_SHOWN)."""
    return dict(REF_NOT_SHOWN)
# rows kept in the data file but not shown in ED5 (display only); any other unmapped row still stops
PB_DROPPED = {'α = 1 (Hjalsted et al. SI tables)': 'α = 1 (Hjalsted et al. SI tables)',
              'NZ population: raw Stats NZ 2024-base median': 'the raw Stats NZ 2024-base median population'}
# sensitivity/planetary_boundary.csv rows -> (input id, role, group); the AR base-window rows are one row (shortest
# window = low end, longest = high end, the others ticks), as in Fig7a
PB_ROWS = {
    ('SOS / I_glob pair C: 1 W/m² planetary boundary', 'single'): ('carrying_capacity', 'single', 'Carrying capacity'),
    ('Global impact: EF 3.1', 'single'): ('global_impact_ef31', 'single', 'Global impact'),
    ('GDP per capita in current US$', 'single'): ('gdp_current', 'single', 'Economic allocation'),
    ('s_sec with the FCE share as a ratio of sums', 'single'): ('sector_share', 'single', 'Economic allocation'),
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


# ---------------------------------------------------------------------------
# row notes of ED4 and ED5 (what each shown row changes compared with the Reference)
# ---------------------------------------------------------------------------
NOTE_LINESPACING = 1.2           # line spacing of the notes (matplotlib linespacing; the pitch is measured, not assumed)
NOTE_GUTTER_MM = 3.0              # clear space between the right end of a note column and the next column
# WDI series and s_sec conventions as named in boundaries.py (a code the text does not know stops the figure)
WDI_MEASURE = {'NY.GDP.PCAP.PP.KD': 'GDP per capita at purchasing-power parity, constant 2021 international $',
               'NY.GDP.PCAP.CD': 'GDP per capita in current US$'}
FCE_SHARE = {'mean_of_ratios': 'the mean of the {n} quarterly FCE/GDP ratios {a}–{b}',
             'ratio_of_sums': 'the ratio of the summed FCE to the summed GDP of the {n} quarters {a}–{b}'}


def _stop(fig, msg):
    raise SystemExit(f'STOP: {fig}: {msg}')


def _model():
    """The model modules whose settings the notes quote (imported here only: the notes, never the drawing)."""
    import Building_factors as BF
    import Sensitivity as SE
    import boundaries as BD
    import projection as PR
    cases = {lab: kw for _, lab, kw in SE.CASES + SE.DECARB_CASES[PR.DECARB_MODE]}
    return PR, BF, BD, cases


def _case(cases, label, fig):
    if label not in cases:
        _stop(fig, f'the data case {label!r} is not a case of Sensitivity.py')
    return cases[label]


def _same(fig, what, code, out):
    if code != out and not (isinstance(code, (tuple, list)) and list(code) == list(out)):
        _stop(fig, f'{what}: the code says {code!r}, the committed outputs {out!r}')


def _mentions(fig, row, *vals):
    for v in vals:
        if str(v) not in row:
            _stop(fig, f'the row label {row!r} does not name the setting value {v!r} it runs')


def _yrs(a, b):
    return f'{a}–{b}'


def row_notes_ed4(r):
    """{input id: note} for every row of ED4 (sensitivity/reference_carbon.csv as r), from the code and outputs."""
    F = 'ED4 notes'
    PR, BF, BD, cases = _model()
    pj = D.js('baseline/projection.json')
    ob = D.js('baseline/overbuild_2026.json')
    _same(F, 'completion rate', PR.COMPLETION_RATE, pj['settings']['completion_rate'])
    _same(F, 'completion rate', PR.COMPLETION_RATE, ob['completion_rate'])
    _same(F, 'replacement half-life', PR.REPLACEMENT_HALF_LIFE, pj['settings']['replacement_half_life'])
    _same(F, 'replacement scenario', PR.REPLACEMENT_VARIANT, pj['settings']['scenario'])
    _same(F, 'overbuild booking', PR.OVERBUILD_BOOKING, pj['settings']['overbuild_booking'])
    _same(F, 'completion lag (months)', PR.COMPLETION_LAG_MONTHS, ob['completion_lag_months'])
    _same(F, 'overbuild absorbed by', PR.OVERBUILD_ABSORPTION_END, ob['absorption_end'])
    _same(F, 'A4-A5 path', PR.DECARB_A45, pj['decarb_a45'])
    _same(F, 'event timing', PR.EVENT_TIMING, pj['event_timing'])
    if (PR.HH_SIZE_PATH, PR.S_TAIL, PR.VACANCY_PARAMETER, PR.DECARB_MODE, PR.DECARB_ITEM_CASE, PR.SOIL_ON_REPLACEMENT,
            PR.NOWCAST_POPULATION, PR.CENSUS_UC_CORRECTION) != ('statsnz_2023', 'pchip_secant', 'census_2023',
                                                                'horup_item', 'central', False, True, True):
        _stop(F, 'a Reference setting the notes describe has changed in projection.py; rewrite the notes')
    case = {(x['row'], x['side']): x['case'] for _, x in r.iterrows()}
    basis = {(x['row'], x['side']): x['basis'] for _, x in r.iterrows()}

    def kw(row, side):
        return _case(cases, case[(row, side)], F)
    n = {}
    if PR.HH_PROPENSITY != 'A' or PR.HH_SIZE_VARIANT != 'Medium':
        _stop(F, 'the Reference household projection is not Medium A; rewrite the notes')
    _same(F, 'propensity row', kw('Living arrangements: propensities change (Stats NZ B)', 'single'),
          dict(HH_PROPENSITY='B'))
    n['hh_propensity'] = ('Stats NZ Medium B household projection (living-arrangement propensities change, modelled on '
                          'the 2001–2023 censuses) instead of Medium A (propensities held at 2023)')
    k = kw('Household size: 2018-2023 census pace', 'single')
    _same(F, 'census-pace path', k, dict(HH_SIZE_PATH='census_pace'))
    a, b = PR.HH_SIZE_PACE_WINDOW
    _mentions(F, 'Household size: 2018-2023 census pace', f'{a}-{b}')
    n['hh_pace'] = (f'household size continues linearly from {PR.S_ANCHOR_YEAR} at the {_yrs(a, b)} census-interval '
                    f'pace instead of the Stats NZ household-size path rebased on {PR.S_ANCHOR_YEAR}')
    if PR.S_TAIL != 'pchip_secant':
        _stop(F, 'the household-size tail of the Reference has changed; rewrite the tail notes')
    ref_tail = ('instead of the 2043–2048 secant slope at 2048, continued linearly in 2049–2050')
    _same(F, 'flat tail', kw('After 2048: held flat (zero slope)', 'single'), dict(S_TAIL='hermite_clamped'))
    _same(F, 'PCHIP end slope', kw('After 2048: PCHIP end slope', 'single'), dict(S_TAIL='pchip_endslope'))
    n['hh_after2048_flat'] = f'a zero slope imposed at 2048 and household size held constant after it {ref_tail}'
    n['hh_after2048_endslope'] = (f'the shape-preserving (PCHIP) end derivative at 2048, continued linearly, '
                                  f'{ref_tail}')
    if PR.HH_SIZE_PAIRED != {'5th': 'Low', '50th': None, '95th': 'High'}:
        _stop(F, 'the population / household-size pairing has changed; rewrite the population note')
    n['population'] = (f'Stats NZ 2024-base stochastic projection, 5th / 95th percentile path instead of the median, '
                       f'with the household size of the Stats NZ Low / High {PR.HH_PROPENSITY} household projection '
                       f'(the same percentiles)')
    v = [kw('Completion rate 0.93 / 0.96', s)['COMPLETION_RATE'] for s in ('low', 'high')]
    _mentions(F, 'Completion rate 0.93 / 0.96', *(f'{x:g}' for x in v))
    n['completion_rate'] = (f'{v[0]:g} / {v[1]:g} of consented dwellings completed instead of '
                            f'{PR.COMPLETION_RATE:g}')
    w = kw('Dwelling-size window 2016-2025', 'single')['DWELLING_SIZE_REF']
    _mentions(F, 'Dwelling-size window 2016-2025', f'{w[0]}-{w[1]}')
    n['size_window'] = (f'new-dwelling size held at its {_yrs(*w)} mean per typology instead of the '
                        f'{_yrs(*PR.DWELLING_SIZE_REF)} mean')
    e = [kw('2026 overbuild absorbed by 2030 / by 2045', s)['OVERBUILD_ABSORPTION_END'] for s in ('low', 'high')]
    _mentions(F, '2026 overbuild absorbed by 2030 / by 2045', *e)
    n['overbuild_timing'] = (f'the starting surplus and the 2026 overbuild absorbed by {e[0]} / {e[1]} instead of '
                             f'{PR.OVERBUILD_ABSORPTION_END}')
    ss = pj['starting_surplus']
    _same(F, 'starting surplus', PR.STARTING_SURPLUS, ss['mode'])
    if ss['mode'] != 'carry' or not ss['rule_carry']:
        _stop(F, 'the starting-surplus rule or setting has changed; rewrite the notes')
    _same(F, 'no-surplus row', kw('No starting surplus', 'single'), dict(STARTING_SURPLUS='none'))
    _same(F, 'minus-2-SD row', kw('Starting surplus minus 2 SD', 'single'), dict(STARTING_SURPLUS='carry_minus_2sd'))
    ya = ss['after_years']
    k_iv = list(ss['intervals'])
    y0, y1 = int(k_iv[0].split('-')[0]) + 1, int(k_iv[-1].split('-')[1])       # the residual years of the intervals
    n['start_surplus_none'] = (f"no starting surplus instead of {ss['dwellings_carry']:,.0f} vacant dwellings at the "
                               f"start of 2026, absorbed by {ss['absorbed_by']}: (the {_yrs(ya[0], ya[-1])} building "
                               f"beyond the stock identity, {ss['r_after']:,.0f} dwellings a year, minus the {_yrs(y0, y1)} "
                               f"census-interval mean, {P.minus(format(ss['m'], ',.0f'))}) × {len(ya)} years; carried "
                               f"because it exceeds the mean + {ss['sd_multiple']:g} SD (SD {ss['s']:,.0f})")
    n['start_surplus_m2sd'] = (f"a starting surplus of {ss['dwellings_carry_minus_2sd']:,.0f} dwellings (only the "
                               f"excess above the mean + {ss['sd_multiple']:g} SD) instead of "
                               f"{ss['dwellings_carry']:,.0f}")
    _same(F, 'vacancy parameter', kw('Vacancy parameter: 1986-2023 census mean (one definition)', 'single'),
          dict(VACANCY_PARAMETER='consistent_mean'))
    vy = ob['vacancy']['consistent_years']
    _mentions(F, 'Vacancy parameter: 1986-2023 census mean (one definition)', vy)
    n['vacancy_mean'] = (f"the mean of the {vy.replace('-', '–')} censuses on one definition instead of "
                         f"the 2023 census value ({100 * ob['vacancy']['v_forward']:.2f}%)")
    _same(F, 'overbuild booking row', kw('2026 overbuild booked as stock-neutral redevelopment', 'single'),
          dict(OVERBUILD_BOOKING='redevelopment'))
    pipe = [int(y) for y in ob['pipeline_years']]
    n['overbuild_redev'] = (f'the 2026 overbuild (building above need in {_yrs(pipe[0], pipe[-1])} and its '
                            f"continuation, fading at ρ = {ob['rho']:.2f}) replaces existing dwellings instead of "
                            'adding to the stock: no surplus, so no absorption payback and no soil carbon loss on it')
    g = [kw('Completion lag 15 / 19 months', s)['COMPLETION_LAG_MONTHS'] for s in ('low', 'high')]
    _mentions(F, 'Completion lag 15 / 19 months', *g)
    n['completion_lag'] = f'consents lagged {g[0]} / {g[1]} months instead of {PR.COMPLETION_LAG_MONTHS}'
    k = kw('No 2026 data', 'single')
    _same(F, 'no-2026 row', k, dict(CONSENT_DATA_END='2025-12-01', NOWCAST_POPULATION=False))
    obs = ob['consents_observed_to']
    month = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
             'November', 'December']
    n['no_2026'] = (f'consents to December 2025 and the projected 2026 population instead of consents to '
                    f'{month[int(obs[5:7]) - 1]} {obs[:4]} and the observed 2026 population growth')
    # replacement: the variants of engine.replacement_path, named by the case and basis columns
    low = case[('Low / High replacement', 'low')]
    high = case[('Low / High replacement', 'high')]
    vh = case[('Very High replacement (trend continues)', 'single')]
    for lab, var in ((low, 'LOW'), (high, 'HIGH'), (vh, 'VHIGH')):
        _same(F, f'replacement row {lab!r}', _case(cases, lab, F), dict(REPLACEMENT_VARIANT=var))
    lr = re.search(r'(\d{4})-(\d{4}) long-run rate', basis[('Low / High replacement', 'low')])
    rr = re.search(r'(\d{4})-(\d{4}) rate persists', high)
    tr = re.search(r'(\d{4})-(\d{4}) census trend continues', vh)
    if not (lr and rr and tr):
        _stop(F, 'the replacement case / basis texts no longer name their periods')
    n['replacement'] = (f'Low: the {_yrs(*lr.groups())} long-run net rate throughout; High (tick): the '
                        f'{_yrs(*rr.groups())} rate persists; Very High: the {_yrs(*tr.groups())} census-interval '
                        f'trend continues; instead of the {_yrs(*rr.groups())} rate fading to the long-run rate with a '
                        f'{PR.REPLACEMENT_HALF_LIFE:g}-year half-life')
    h = [kw('Replacement half-life 5 / 15 yr', s)['REPLACEMENT_HALF_LIFE'] for s in ('low', 'high')]
    _mentions(F, 'Replacement half-life 5 / 15 yr', *(f'{x:g}' for x in h))
    n['half_life'] = f'{h[0]:g} / {h[1]:g} years instead of {PR.REPLACEMENT_HALF_LIFE:g}'
    n['soil_order'] = ('the soil carbon loss of the lowest (Raw) / highest (Organic) soil order on every new footprint '
                       'instead of the area-weighted mean over the soil orders of the Auckland land zoned for '
                       'urbanisation')
    n['single_case'] = ('the materials factor of the lowest / highest single case study of each typology instead of '
                        'the pooled typology factor')
    n['jackknife'] = ('the lowest / highest pooled materials factor when each case study is left out in turn, instead '
                      'of the pooled factor (a spread, not a confidence interval)')
    a45 = f'{100 * BF.A45_DECAY:g}% per year'
    _same(F, 'frozen technology row', kw('Frozen technology (2025 factors held)', 'single'),
          dict(DECARB_MODE='none', DECARB_A45='held'))
    n['frozen'] = (f'every factor held at 2025 instead of A1–A3 on the item paths of Horup et al. (2025) and A4–A5 '
                   f'falling {a45}')
    _same(F, 'NZ-made row', kw('Decarbonisation: NZ-made electricity-intensive items held', 'single'),
          dict(DECARB_ITEM_CASE='nz_elec_held'))
    n['nz_made_held'] = ('items made in New Zealand with electricity-intensive production held at 2025 instead of '
                         'following their Horup et al. (2025) path')
    _same(F, 'proxy row', kw('Decarbonisation: proxy-mapped items held', 'single'),
          dict(DECARB_ITEM_CASE='proxies_held'))
    n['proxy_held'] = 'items mapped to a proxy material held at 2025 instead of following the proxy\'s path'
    row = "A4-A5 on each item's own path / held at 2025"
    _same(F, 'A4-A5 rows', [kw(row, s)['DECARB_A45'] for s in ('low', 'high')], ['item', 'held'])
    n['a4a5'] = (f"A4–A5 on each item's own Horup et al. (2025) path / held at 2025 instead of the generic {a45} "
                 'decline (Resch et al. 2021)')
    _same(F, 'soil row', kw('Soil carbon loss on all floor area, including replacement', 'single'),
          dict(SOIL_ON_REPLACEMENT=True))
    n['soil_all'] = 'soil carbon loss also on replacement floor area instead of none on rebuilt footprints'
    return n


def row_notes_ed5(r):
    """{input id: note} for every row of ED5 (sensitivity/planetary_boundary.csv as r), from the code and outputs."""
    F = 'ED5 notes'
    PR, BF, BD, cases = _model()
    st = D.js('aesa/results.json')['settings']
    for k in ('SOURCE_PAIR', 'AR_BASE_WINDOW', 'GDP_MEASURE', 'GDP_MEASURE_SENS', 'SSEC_FCE_SHARE', 'SSEC_WINDOW',
              'POP_NZ_SOURCE'):
        _same(F, k, getattr(BD, k), st[k])
    if BD.POP_NZ_SOURCE != 'model' or not PR.NOWCAST_POPULATION:
        _stop(F, 'the Reference population source of the notes has changed; rewrite the notes')
    for code in (BD.GDP_MEASURE, BD.GDP_MEASURE_SENS):
        if code not in WDI_MEASURE:
            _stop(F, f'no text for the WDI series {code}')
    alt_fce = [k for k in FCE_SHARE if k != BD.SSEC_FCE_SHARE]
    if BD.SSEC_FCE_SHARE not in FCE_SHARE or len(alt_fce) != 1:
        _stop(F, f'no text for the FCE-share convention {BD.SSEC_FCE_SHARE!r}')
    rows = set(r['row'])
    pa, pc = BD.SOURCE_PAIRS[BD.SOURCE_PAIR], BD.SOURCE_PAIRS['C']
    row_cc = [x for x in rows if x.startswith('SOS / I_glob pair')]
    if len(row_cc) != 1 or 'pair C' not in row_cc[0] or pc['label'].split(' (')[0] not in row_cc[0]:
        _stop(F, f'the carrying-capacity row {row_cc} does not match boundaries.SOURCE_PAIRS')
    pe = BD.SOURCE_PAIRS['EF31']
    if pe['sos'] != pa['sos'] or pe['i_glob'] != BD.I_GLOB_EF31_PER_PERSON * BD.I_GLOB_EF31_POPULATION:
        _stop(F, 'the EF 3.1 row is not the Reference SOS with the EF 3.1 global impact')
    if pc['i_glob'] != pa['i_glob']:
        _stop(F, 'the two source pairs differ in I_glob; the note says only the SOS changes')

    def sci(v):
        m, e = f'{v:.2e}'.split('e')
        return f"{float(m):.2f} × 10{str(int(e)).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))}"
    n = {}
    n['carrying_capacity'] = (f"{pc['label']}, safe operating space {sci(pc['sos'])} kg CO₂e per year, instead of the "
                              f"{pa['label']}, {sci(pa['sos'])} (the same global impact); both budgets move")
    n['global_impact_ef31'] = (f'global impact (I_glob) from the EF 3.1 normalisation factor (Andreasi Bassi et al. '
                               f'2023, Table 10; {sci(BD.I_GLOB_EF31_PER_PERSON)} kg CO₂e per person, 2010) instead of '
                               f"{sci(pa['i_glob'])} (Bjørn & Hauschild 2015; equal to the EF 3.0 factor, "
                               f'{sci(BD.I_GLOB_EF30_PER_PERSON)} per person). The '
                               f"{100 * (1 - pe['i_glob'] / pa['i_glob']):.1f}% difference is mainly the lower "
                               'characterisation factor of methane in EF 3.1. Acquired rights only')
    bw = sorted((int(a), int(b)) for a, b in r.loc[r['group'] == 'Base window', 'row'].str.extract(
        r'(\d{4})-(\d{4})').values)
    want = sorted([tuple(BD.AR_BASE_WINDOW_SENS), tuple(BD.AR_BASE_WINDOW_20), tuple(BD.AR_BASE_WINDOW_FULL)])
    _same(F, 'AR base windows', bw, want)
    bw = sorted(bw, key=lambda t: t[1] - t[0])
    a0, b0 = BD.AR_BASE_WINDOW
    n[N.AR_WINDOW_LABEL.format(short=bw[0][1] - bw[0][0] + 1, long=bw[-1][1] - bw[-1][0] + 1)] = ('mean sector emissions over ' + ' / '.join(f'{b - a + 1}' for a, b in bw) + ' years ('
                      + ', '.join(_yrs(a, b) for a, b in bw) + f') instead of {b0 - a0 + 1} years ({_yrs(a0, b0)}); '
                      'AR only')
    gdp_row = [x for x in rows if x.startswith('GDP per capita')]
    if len(gdp_row) != 1 or gdp_row[0] != WDI_MEASURE[BD.GDP_MEASURE_SENS]:
        _stop(F, f'the GDP row {gdp_row} and boundaries.GDP_MEASURE_SENS ({BD.GDP_MEASURE_SENS}) disagree')
    n['gdp_current'] = (f'{WDI_MEASURE[BD.GDP_MEASURE_SENS]} instead of {WDI_MEASURE[BD.GDP_MEASURE]} (World Bank '
                        'WDI); AtP only')
    ss_row = [x for x in rows if x.startswith('s_sec with the FCE share')]
    if len(ss_row) != 1 or not ss_row[0].endswith(alt_fce[0].replace('_', ' ')):
        _stop(F, f'the sector-share row {ss_row} and boundaries.SSEC_FCE_SHARE ({BD.SSEC_FCE_SHARE}) disagree')
    a1, b1 = BD.SSEC_WINDOW
    q = 4 * (b1 - a1 + 1)
    n['sector_share'] = ('FCE share of GDP in the sector share: ' + FCE_SHARE[alt_fce[0]].format(n=q, a=a1, b=b1)
                         + ' instead of ' + FCE_SHARE[BD.SSEC_FCE_SHARE].format(n=q, a=a1, b=b1) + '; AtP only')
    n['pop_source_wpp'] = ('UN WPP 2024 median for New Zealand instead of the model\'s population path (the Stats NZ '
                           '2024-base median from the observed 2025 level, with the observed 2026 growth); budgets '
                           'only')
    n['population'] = ('Stats NZ 2024-base 5th / 95th percentile path instead of the median; carbon and both budgets '
                       'move together')
    n['replacement'] = 'as in Extended Data Fig. 4 (carbon only; the budgets are unchanged)'
    n['half_life'] = 'as in Extended Data Fig. 4 (carbon only)'
    return n


def tag(n):
    """A row number as drawn: '[n]' (the end of the row label, the start of its note; captions and FIGURES.md)."""
    return f'[{n}]'


def note_lines(order, notes, label, fig):
    """[(number, row id, note)] for every shown row of a tornado order, numbered 1, 2, ... top to bottom
    (display order); every shown row has a note."""
    out = []
    for kind, item in order:
        if kind != 'row':
            continue
        rid = item['id']
        if rid not in notes:
            _stop(fig, f'no row note for {rid!r}')
        out.append((len(out) + 1, rid, notes[rid]))
    return out


def caption_lines(numbered):
    """'[1] <note>.' per numbered row (the text of the captions, FIGURES.md and the audit note)."""
    return [f'{tag(n)} {t}.' for n, _, t in numbered]


def numbered_label(numbered):
    """The y tick label of a row, ending with its number ' [n]' (rows without a note: the label alone)."""
    num = {rid: n for n, rid, _ in numbered}
    return lambda rid: _input_label(rid).replace('$', r'\$') + (f' {tag(num[rid])}' if rid in num else '')


NOTE_TEXT_SIZE = S.FONT_MIN + 0.5      # the row notes (pt)
NOTE_NUMBER_GAP_MM = 1.0         # the note text starts this far right of the widest '[n]' (measured)


def note_metrics(fig):
    """(line pitch in inches, a function giving the rendered width of a string in inches) of the note text (FONT_MIN,
    the figure font) as matplotlib lays it out: the pitch is the height a second line adds to a one-line text, so the
    notes are spaced exactly as the lines inside a note, whatever the typeface."""
    r = fig.canvas.get_renderer()
    probe = dict(fontsize=NOTE_TEXT_SIZE, linespacing=NOTE_LINESPACING)
    h = []
    for s in ('Ag', 'Ag\nAg'):
        t = fig.text(0, 0, s, **probe)
        h.append(t.get_window_extent(r).height)
        t.remove()
    tw = fig.text(0, 0, '', **probe)

    def width_in(s):
        tw.set_text(s.replace('$', r'\$'))                  # measured as drawn (a literal dollar, not mathtext)
        return tw.get_window_extent(r).width / fig.dpi
    return (h[1] - h[0]) / fig.dpi, width_in, tw


def wrap_measured(text, width_in, avail_in):
    """Greedy word wrap of text so that every line's rendered width is at most avail_in (inches); a single word wider
    than the column stops the figure (it would be clipped)."""
    lines, cur = [], ''
    for word in text.split():
        cand = f'{cur} {word}' if cur else word
        if width_in(cand) <= avail_in:
            cur = cand
            continue
        if not cur:
            raise SystemExit(f'STOP: a row-note word is wider than its column: {word!r}')
        lines.append(cur)
        cur = word
        if width_in(cur) > avail_in:
            raise SystemExit(f'STOP: a row-note word is wider than its column: {word!r}')
    if cur:
        lines.append(cur)
    return lines


def draw_notes(fig, numbered, title, top_frac, ncol=2):
    """The row notes as a compact list below the axes, '[1] ...', '[2] ...' (the numbers those of the y labels), the
    note text indented past the widest '[n]'; ncol columns filled top to bottom, a note never split. Each note is wrapped by its rendered width (the column width less the indent and a gutter) and
    the notes are stacked at the measured line pitch, so no note overlaps the next. Returns the height used (mm)."""
    if ncol != 2:
        raise ValueError('draw_notes: two columns')
    pitch_in, width_in, tw = note_metrics(fig)
    W = fig.get_figwidth()
    num_in = max(width_in(tag(n)) for n, _, _ in numbered)          # the '[n]' are right-aligned in this width
    indent_in = num_in + NOTE_NUMBER_GAP_MM * S.MM
    avail = (0.5 - 0.01) * W - indent_in - NOTE_GUTTER_MM * S.MM
    wrapped = [[x.replace('$', r'\$') for x in wrap_measured(f'{t}.', width_in, avail)]   # a literal dollar
               for _, _, t in numbered]
    tw.remove()
    n_ = [len(w) for w in wrapped]                        # the split (rows kept whole) with the shortest longer column
    k = min(range(len(n_) + 1), key=lambda j: (max(sum(n_[:j]), sum(n_[j:])), j))
    rows = max(sum(n_[:k]), sum(n_[k:]))
    line = pitch_in / fig.get_figheight()
    fig.text(0.01, top_frac, title, ha='left', va='top', fontsize=NOTE_TEXT_SIZE, fontweight='bold', color=S.INK)
    for c, items in enumerate((list(zip(numbered, wrapped))[:k], list(zip(numbered, wrapped))[k:])):
        x0, y = 0.01 + c / ncol, top_frac - line
        for (n, _, _), w in items:
            fig.text(x0 + num_in / W, y, tag(n), ha='right', va='top', fontsize=NOTE_TEXT_SIZE, color=S.INK)
            fig.text(x0 + indent_in / W, y, '\n'.join(w),
                     ha='left', va='top', fontsize=NOTE_TEXT_SIZE, color=S.INK, linespacing=NOTE_LINESPACING)
            y -= len(w) * line
    return (rows + 1) * pitch_in / S.MM


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


ED4_H = 247                       # mm, with the row notes below the axes; at most style.MAX_HEIGHT
ED5_H = 165                       # mm
NOTES_TOP = 0.30                 # the notes block occupies the figure below this fraction of its height (ED4)
NOTES_TOP_ED5 = 0.22


def ed4_rows():
    """(data, Reference carbon, display order, row-note lines) of ED4 (shared with the caption test)."""
    r = D.csv('sensitivity/reference_carbon.csv')
    c0 = float(r['central_carbon_kt'].iloc[0])
    items, unmapped = [], []
    hidden = ref_not_shown(r)
    for _, x in r.iterrows():
        if x['row'] in REF_DROPPED or x['row'] in hidden:
            continue
        key = (x['row'], x['side'])
        if key not in REF_ROWS:
            unmapped.append(key)
            continue
        rid, role = REF_ROWS[key]
        items.append((rid, role, GROUP_RENAME.get(x['group'], x['group']), float(x['carbon_kt'])))
    if unmapped:
        raise SystemExit(f'STOP: ED4: rows without a display name: {unmapped}')
    missing = [k for k in REF_NOT_SHOWN if k not in set(r['row'])]
    if missing:
        raise SystemExit(f'STOP: ED4: rows listed as not shown are not in the data: {missing}')
    rows = _collect(items)
    order = P.tornado_rows(N.SENSITIVITY_GROUPS, rows, c0)
    return r, c0, order, note_lines(order, row_notes_ed4(r), _input_label, 'ED4')



def ed4_one_at_a_time():
    """ED4 (data D16): every one-at-a-time row of the Reference on the cumulative embodied carbon
    2026-2050 (kt CO2e) as a paired tornado grouped by category (sensitivity/reference_carbon.csv). the
    rows of REF_NOT_SHOWN dropped from the display; the row notes below the axes."""
    r, c0, order, numbered = ed4_rows()
    lines = caption_lines(numbered)
    fig, ax = plt.subplots(figsize=S.figsize('double', ED4_H))
    P.tornado(ax, order, c0, numbered_label(numbered))
    ax.tick_params(axis='y', labelsize=S.FONT_SMALL)
    ax.text(c0, 1.0, f' Reference {c0:,.0f} kt', transform=ax.get_xaxis_transform(), ha='left', va='bottom',
            fontsize=S.FONT_SMALL, color=S.INK)
    ax.set_xlabel('Cumulative embodied carbon 2026–2050 (kt CO₂e)')
    P.thousands(ax.xaxis)
    ax.legend(handles=P.tornado_legend(), loc='lower right', fontsize=S.FONT_SMALL, frameon=False)
    P.centre_ticklabels(fig, ax)
    notes_mm = draw_notes(fig, numbered, 'What each row changes compared with the Reference', NOTES_TOP)
    fig.tight_layout(rect=(0, NOTES_TOP + 0.01, 1, 1))
    if notes_mm * S.MM / fig.get_figheight() > NOTES_TOP:
        raise SystemExit(f'STOP: ED4: the row notes ({notes_mm:.0f} mm) do not fit below the axes; raise ED4_H')
    S.save_figure(fig, 'ED4_one_at_a_time',
                  note=f'Reference {c0:,.0f} kt. One at a time: not additive, not a joint interval. "No effect": every '
                       f'case within {100 * P.NO_EFFECT_RTOL:.2f}% of the Reference. Not shown: the superseded-setting '
                       'rows (completion rate 0.95 and lag 0 months of MODEL v3.3; the never-absorbed overbuild of '
                       'MODEL v2.1) and ' + '; '.join(f"{t} ({float(r.loc[r['row'] == k, 'change_pct'].iloc[0]):+.4f}%)"
                                                     for k, t in ref_not_shown(r).items()) + ' (in the data file). Row notes: '
                       + ' '.join(lines), source=['sensitivity/reference_carbon.csv'])


def ed5_rows():
    """(data, settings, {quantity: Reference value}, {quantity: display order}, row-note lines) of ED5 (shared with the caption test). The row notes follow the order of panel a (the rows are shared)."""
    r = D.csv('sensitivity/planetary_boundary.csv')
    st = D.js('aesa/results.json')['settings']
    c = {'LoE_AR': float(r['central_LoE_AR'].iloc[0]), 'LoE_AtP': float(r['central_LoE_AtP'].iloc[0])}
    bw = r[r['group'] == 'Base window'].copy()
    bw['n'] = bw['row'].str.extract(r'(\d{4})-(\d{4})').astype(int).pipe(lambda t: t[1] - t[0] + 1)
    bw = bw.sort_values('n')
    ar_id = N.AR_WINDOW_LABEL.format(short=int(bw['n'].iloc[0]), long=int(bw['n'].iloc[-1]))
    missing = [k for k in PB_DROPPED if k not in set(r['row'])]
    if missing:
        raise SystemExit(f'STOP: ED5: rows listed as not shown are not in the data: {missing}')
    orders = {}
    for q in ('LoE_AR', 'LoE_AtP'):
        items, unmapped = [], []
        for _, x in r.iterrows():
            if x['group'] == 'Base window' or x['row'] in PB_DROPPED:
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
        orders[q] = P.tornado_rows(N.BOUNDARY_SENSITIVITY_GROUPS, _collect(items), c[q])
    shared = [[(k, i if k == 'header' else i['id']) for k, i in orders[q]] for q in orders]
    if shared[0] != shared[1]:                        # the panels share their y labels and numbers
        raise SystemExit('STOP: ED5: panels a and b order their rows differently; the shared y labels would be wrong.')
    return r, st, c, orders, note_lines(orders['LoE_AR'], row_notes_ed5(r), _input_label, 'ED5')


def ed5_boundary_sensitivity():
    """ED5 (data D42): the boundary-definition and AESA rows on the cumulative LoE of AR (a) and of AtP
    (b), paired tornados with shared y labels (sensitivity/planetary_boundary.csv). the rows of
    PB_DROPPED dropped from the display; the row notes below the axes."""
    r, st, c, orders, numbered = ed5_rows()
    lines = caption_lines(numbered)
    fig, ax = plt.subplots(1, 2, figsize=S.figsize('double', ED5_H), sharey=True)
    for a, q, xl, letter in ((ax[0], 'LoE_AR', N.LOE_AR, 'a'), (ax[1], 'LoE_AtP', N.LOE_ATP, 'b')):
        P.tornado(a, orders[q], c[q], numbered_label(numbered), headers=(q == 'LoE_AR'))
        a.text(c[q], 1.0, f' Reference {c[q]:.2f}', transform=a.get_xaxis_transform(), ha='left', va='bottom',
               fontsize=S.FONT_SMALL, color=S.INK)
        a.set_xlabel(f'{xl} 2026–2050')
        P.panel(a, letter, '')
    ax[0].tick_params(axis='y', labelsize=S.FONT_SMALL)
    ax[1].legend(handles=P.tornado_legend(), loc='lower right', fontsize=S.FONT_SMALL, frameon=False)
    P.centre_ticklabels(fig, ax[0])
    notes_mm = draw_notes(fig, numbered, 'What each row changes compared with the Reference', NOTES_TOP_ED5)
    fig.tight_layout(rect=(0, NOTES_TOP_ED5 + 0.01, 1, 1))
    if notes_mm * S.MM / fig.get_figheight() > NOTES_TOP_ED5:
        raise SystemExit(f'STOP: ED5: the row notes ({notes_mm:.0f} mm) do not fit below the axes; raise ED5_H')
    S.save_figure(fig, 'ED5_boundary_sensitivity',
                  note=f"Reference cumulative LoE of AR {c['LoE_AR']:.2f}, of AtP {c['LoE_AtP']:.2f}; AR base window "
                       f"central {st['AR_BASE_WINDOW'][0]}-{st['AR_BASE_WINDOW'][1]}. 'No effect': within "
                       f'{100 * P.NO_EFFECT_RTOL:.2f}% of the Reference (the economic-allocation rows move AtP only, '
                       'the AR base window moves AR only). Not shown: ' + '; '.join(PB_DROPPED.values())
                       + ' (in the data file). Row notes: ' + ' '.join(lines),
                  source=['sensitivity/planetary_boundary.csv', 'aesa/results.json'])


def row_note_caption(fid):
    """The row notes of ED4 or ED5 as caption text ('[1] <note>. [2] ...'), from the same list the figure draws (the
    captions of FIGURES.md take them from here)."""
    numbered = {'ED4': lambda: ed4_rows()[3], 'ED5': lambda: ed5_rows()[4]}[fid]()
    return ' '.join(caption_lines(numbered))


FIGURES = {'ED4_one_at_a_time': ed4_one_at_a_time, 'ED5_boundary_sensitivity': ed5_boundary_sensitivity,
           'SF8_prcc': sf8_prcc}
