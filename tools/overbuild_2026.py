"""The 2026 overbuild (near-term market excess) under the adopted settings: 2026 building,
the 2026/2027 requirements, the excess and its fade, the implied vacancy, and the
redevelopment-booking sensitivity. Nothing here sets a parameter.

    python tools/overbuild_2026.py      # -> outputs/reports/overbuild_2026.md, outputs/data/baseline/overbuild_2026.json
"""
import json

import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import layout  # noqa: E402
import naming as N  # noqa: E402
import validation  # noqa: E402

OUT_MD = layout.report('overbuild_2026.md')
OUT_JSON = layout.data('baseline/overbuild_2026.json')


def main():
    B = validation.run_boss()
    import projection
    if B['_join_mode'] == 'market_excess':
        ji, nc, pipe = B['join_info']['50th'], B['nowcast'], B.get('pipe')
        E = B['engine_out']['50th']
        fy = list(B['forecast_years'])
        v_eff = 1 - E['hh'] / (E['stock'] + E['stock_join'])
        ipk = int(np.argmax(v_eff[1:])) + 1
        knots = B['stock_cal']['knots']
        rem = lambda Ex: Ex['demol'] + Ex['unc'] + Ex['join_redev']
        Er = validation.run_boss(OVERBUILD_BOOKING='redevelopment')['engine_out']['50th']
        ir = int(np.argmax(rem(Er)[1:])) + 1
        vac = dict(peak=float(v_eff[ipk]), peak_year=int(fy[ipk]), v_2050=float(v_eff[-1]), v_forward=float(E['v'][-1]),
                   census_min=float(min(knots.values())), census_max=float(max(knots.values())),
                   census_years=f'{min(knots)}-{max(knots)}')
        redev = dict(peak_removals=float(rem(Er)[ir]), peak_year=int(fy[ir]),
                     default_peak_removals=float(rem(E)[1:].max()))
        # vacancy on a consistent definition, 1986-2023: the pooled 2018/2023 empty share of
        # unoccupied private dwellings applied to every census (as validation.py)
        c, p = B['census'], B['census_18_23']
        share = sum(p[y]['empty'] for y in p) / sum(p[y]['unoccupied'] for y in p)
        v_cons = (c['unoccupied'] * share / c['total_private']).dropna()
        vac.update(consistent_share=float(share), consistent=dict((int(k), float(v)) for k, v in v_cons.items()),
                   consistent_min=float(v_cons.min()), consistent_max=float(v_cons.max()),
                   consistent_years=f'{int(v_cons.index.min())}-{int(v_cons.index.max())}')
        j = np.asarray(ji['join'])
        i28 = fy.index(2028)
        surplus_total, surplus_26_28 = float(j[1:].sum()), float(j[1:i28 + 1].sum())
        wording = N.vacancy_wording(vac['v_forward'], vac['consistent_max'], vac['consistent_min'],
                                    min(vac['consistent'], key=vac['consistent'].get), vac['v_2050'])
        ab = ji.get('absorption')
        absorbed = float(-np.asarray(ji['payback'])[1:].sum())
        end = projection.OVERBUILD_ABSORPTION_END
        limitation = (f"{wording[0].upper() + wording[1:]}. The 2026 overbuild (market excess ≈{round(float(np.sum(ji['excess'][1:])), -2):,.0f} "
                      f"dwellings over 2026-2050, of which ≈{round(float(np.sum(ji['excess'][1:i28 + 1])), -2):,.0f} in 2026-2028) "
                      + (f"is absorbed by {end} along the normalised logistic of the levers (≈{round(absorbed, -2):,.0f} "
                         f"dwellings built less; implied vacancy peaks at {100 * vac['peak']:.2f}% in {vac['peak_year']}). "
                         'Stock-flow theory of the housing market (Rosen & Smith 1983; Wheaton 1990; DiPasquale & '
                         'Wheaton 1992; Gabriel & Nothaft 2001) fixes the direction, reversion of vacancy to its '
                         'equilibrium rate, not the speed; 2035 is the common RECC adoption window of the model and the '
                         'speed is bracketed by sensitivity rows (never absorbed, by 2030, by 2045). The persistence '
                         f"rho = {ji['rho']:.2f} describes how the flow deviation fades, not the payback of the stock."
                         if end is not None else
                         'is not absorbed (the legacy Reference of MODEL v2.1), so the implied vacancy stays above the '
                         'parameter.'))
        if ab is not None and bool(np.any(ab['cap_binds'])):
            limitation += ' The payback cap binds in ' + ', '.join(str(fy[i]) for i in np.flatnonzero(ab['cap_binds'])) + '.'
        res = dict(mode='market_excess', near_mode=projection.OVERBUILD_BOOKING, gap_ref_basis=projection.OVERBUILD_GAP_REF,
                   surplus_2026_2028=surplus_26_28, limitation=limitation,
                   vacancy=vac, redevelopment_sensitivity=redev,
                   nowcast_method=(None if pipe else projection.NOWCAST_METHOD),
                   consents_2026=(pipe['consents_all'][2026] if pipe else nc['total']),
                   completion_lag_months=int(B.get('lag_months', 0) or 0), completion_rate=projection.COMPLETION_RATE,
                   pipeline_years=(list(pipe['years']) if pipe else []),
                   consents_observed_to=(B['lag_info']['consents_observed_to'] if pipe else None),
                   pipeline_consents=({int(y): pipe['consents_all'][y] for y in pipe['years']} if pipe else {}),
                   O_obs=ji.get('O_obs'), R_obs=ji.get('R_obs'), e_obs=ji.get('e_obs'), R_next=ji.get('R_next'),
                   O26=ji['O26'], R26=ji['R26'],
                   R27=ji['R27'], e26=ji['e26'], gap_ref=ji['gap_ref'], rho=ji['rho'],
                   join_2026_2050=float(ji['join'][1:].sum()), excess_2026_2050=float(np.sum(ji['excess'][1:])),
                   absorbed_2026_2050=absorbed, absorption_end=end, scenario=B['_scenario'])
        with open(layout.writing(OUT_JSON), 'w') as f:
            json.dump(N.keys(res), f, indent=2)
        if pipe:
            yrs = list(pipe['years'])
            head = [f"Completion lag {B['lag_months']} months: building in {', '.join(map(str, yrs))} = "
                    f"{projection.COMPLETION_RATE:.3f} x consents lagged {B['lag_months']} months (all categories; "
                    f"consents observed to {B['lag_info']['consents_observed_to']})."]
            head += [f"{y}: consents {pipe['consents_all'][y]:,.0f} -> building {o:,.0f}; requirement {r:,.0f} -> "
                     f"excess {e:+,.0f}." for y, o, r, e in zip(yrs, ji['O_obs'], ji['R_obs'], ji['e_obs'])]
            head += [f"gap_ref = building {yrs[-1]} - requirement {yrs[-1] + 1} ({ji['R_next']:,.0f}) = {ji['gap_ref']:+,.0f}, "
                     f"fading from {yrs[-1] + 1} at rho = {ji['rho']:.3f}."]
        else:
            head = [f"2026 consents ({projection.NOWCAST_METHOD}, observed only): {nc['total']:,.0f}; 2026 building "
                    f"= {projection.COMPLETION_RATE:.2f} x consents = {ji['O26']:,.0f} dwellings (all categories).",
                    f"Requirement 2026 {ji['R26']:,.0f} -> excess {ji['e26']:+,.0f}; requirement 2027 {ji['R27']:,.0f} "
                    f"-> gap_ref {ji['gap_ref']:+,.0f} (basis {projection.OVERBUILD_GAP_REF}), fading at rho = {ji['rho']:.2f}."]
        L = ['# The 2026 overbuild (generated by tools/overbuild_2026.py)', ''] + head + [
             f"Booked as {projection.OVERBUILD_BOOKING}: market excess {float(np.sum(ji['excess'][1:])):+,.0f}, absorbed "
             f"{-absorbed:+,.0f}, net {float(ji['join'][1:].sum()):+,.0f} dwellings over 2026-2050 (variant {B['_scenario']}; "
             f"absorbed by {end}).",
             f"Implied vacancy (1 - households / (stock + surplus still vacant)): peak {100 * vac['peak']:.2f}% in {vac['peak_year']}, "
             f"{100 * vac['v_2050']:.2f}% in 2050 (the vacancy-rate parameter: its published 2023 census value, "
             f"{100 * vac['v_forward']:.2f}%); census {vac['census_years']} "
             f"range {100 * vac['census_min']:.2f}-{100 * vac['census_max']:.2f}% (empty dwellings; before 2013 the empty share "
             f"of unoccupied is estimated, and 2013->2018 is a definitional break).",
             f"Consistent definition (pooled 2018/2023 empty share of unoccupied, {100 * share:.1f}%): "
             + ', '.join(f'{y} {100 * v:.2f}%' for y, v in vac['consistent'].items()) + '.',
             f"Sensitivity, booked as redevelopment: implied net removals peak at {redev['peak_removals']:,.0f} in "
             f"{redev['peak_year']} (default: {redev['default_peak_removals']:,.0f}).", '',
             f"Limitation: {limitation}"]
        with open(layout.writing(OUT_MD), 'w') as f:
            f.write('\n'.join(L) + '\n')
        print('\n'.join(L))
        return
    raise SystemExit("OVERBUILD_RULE is not 'market_excess': nothing to report.")

if __name__ == '__main__':
    main()
