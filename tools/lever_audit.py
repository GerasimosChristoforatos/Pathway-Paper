"""Lever consistency audit (MODEL v4.9.0): outputs/reports/lever_audit.md. STOPs (exit 1) on any failed check.

For every lever L1-L10, on its native parameter (levers.native) and on its effect alone (single-lever runs of the
Reference, pathways.run):
  1. monotone levels in every year 2026-2050 and every typology: Reference >= Moderate >= Ambitious >= TL in carbon per
     unit (the native parameter in its carbon direction, and the quantity the run applies);
  2. Moderate is exactly the midpoint of Reference and Ambitious in the native parameter, every year, every lever;
  3. the same level is the same parameter across pathways (Moderate / Ambitious Pathway = every lever at that level,
     TL = every lever at TL), and every lever follows the common adoption window except the stated exceptions (L9 and
     L10 on their own paths; the TL1 speed limit);
  4. each lever alone is monotone in cumulative carbon 2026-2050: Reference >= Moderate >= Ambitious >= TL;
  5. no double counting: each lever changes only its own engine inputs and stage (L1-L5 floor area; L6, L7 soil;
     L8, L10 the A1-A3 term; L9 the A4-A5 term), checked on the inputs and on the stage totals;
  6. levers.tl_strength (TL at least as strong as Ambitious), TL8 by year and TL10 included.

    python tools/lever_audit.py          (run_all.py runs it after pathways)
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import layout  # noqa: E402
import levers as LV  # noqa: E402
import naming as N  # noqa: E402
import pathways as PW  # noqa: E402

OUT = layout.report('lever_audit.md')
LEVELS = ('reference', 'moderate', 'ambitious', 'tl')
TOL = 1e-12
# carbon direction of each native parameter: +1 = a larger value means more carbon (Reference largest), -1 = a larger
# value means less carbon (L1 household size S, L6 brownfield share s, L4 share f, L3 reduction d)
DIRECTION = {'L1': -1, 'L2': +1, 'L3': -1, 'L4': -1, 'L5': +1, 'L6': -1, 'L7': +1, 'L8': +1, 'L9': +1, 'L10': +1}
# engine inputs each lever may change (levers.inputs); every other input must be the Reference object
OWN_INPUTS = {'L1': set(), 'L2': {'v'}, 'L3': {'rate_demol', 'rate_unc'}, 'L4': {'size'}, 'L5': {'olf', 'size'},
              'L6': {'brownfield_share', 'brownfield_w'}, 'L7': {'soil', 'intensity', 'intensity_upfront'},
              'L8': {'intensity', 'intensity_upfront'}, 'L9': {'intensity', 'intensity_upfront'},
              'L10': {'intensity', 'intensity_upfront', 'events'}}
FLOOR_AREA_LEVERS = ('L1', 'L2', 'L3', 'L4', 'L5')
OWN_WINDOW = ('L9', 'L10')            # stated exceptions: own path, no logistic adoption weight


def flat(x):
    """A native parameter as {key: array over years} (scalars and per-typology values broadcast)."""
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if isinstance(v, dict):
                out.update({f'{k}.{k2}': np.atleast_1d(np.asarray(v2, float)) for k2, v2 in v.items()})
            else:
                out[str(k)] = np.atleast_1d(np.asarray(v, float))
        return out
    return {'all': np.atleast_1d(np.asarray(x, float))}


def applied(L, R, ref_soil, years):
    """The quantity a single-lever run applies (pathways.ordering's), in its carbon direction (larger = more carbon)."""
    fi, info, E = R['inputs'], R['info'], R['E']
    bt = lambda a: np.broadcast_to(np.asarray(a, float), (len(years),))
    typ = list(R['inputs']['olf'])
    if L == 'L1':
        return {'households': np.asarray(info['hh'], float)}
    if L == 'L2':
        return {'v': bt(fi['v'])}
    if L == 'L3':
        return {'demolition': bt(fi['rate_demol']), 'residual': bt(fi['rate_unc'])}
    if L == 'L4':
        return {t: bt(fi['size'][t]) for t in typ}
    if L == 'L5':
        return {t: bt(fi['olf'][t]) for t in typ}
    if L == 'L6':
        return {'soil_share': np.asarray(E['soil_share'], float)}
    if L == 'L7':
        return {t: bt(fi.get('soil', ref_soil)[t]) for t in typ}
    if L in ('L8', 'L10'):
        return {t: bt(info['a13'][t]) for t in typ}
    if L == 'L9':
        return {t: bt(info['a45'][t]) for t in typ}
    raise ValueError(L)


def stages(ctx, R):
    st = PW.stage_arrays(ctx, R)
    f = slice(1, None)
    return dict(gfa_Mm2=float(R['E']['gfa_t'][:, f].sum()) / 1e6, a13_kt=st['a13'][f].sum() / 1e6,
                a45_kt=st['a45'][f].sum() / 1e6, soil_kt=st['soil'][f].sum() / 1e6,
                maintenance_kt=st['maintenance'][f].sum() / 1e6, carbon_kt=float(R['E']['carbon'][f].sum()) / 1e6)


def same(a, b):
    if a is b:
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    try:
        return bool(np.array_equal(np.asarray(a, float), np.asarray(b, float)))
    except (TypeError, ValueError):
        return a == b


def main():
    B = PW.boss_state(PW.REFERENCE)
    ctx = PW.base_context(B, PW.REFERENCE, PW.boundaries())
    p = PW.resolve_params(B)
    years = np.asarray(ctx['years'])
    yr = years >= PW.WINDOW[0]
    cache = {}

    def get(levels, ramp=None):
        k = LV.key(levels, ramp)
        if k not in cache:
            cache[k] = PW.run(ctx, p, levels, ramp)
        return cache[k]

    R0 = get({})
    S0 = stages(ctx, R0)
    fails = []
    L = ['# Lever consistency audit (generated by tools/lever_audit.py; MODEL v4.9.0)', '',
         'The Reference projection, median demographics. Every check covers the ten levers; a failed check is a STOP '
         '(run_all.py stops). Tolerance 1e-12 (relative where stated).', '']

    # ---- 1. monotone levels ----
    L += ['## 1. Monotone levels in every year 2026-2050 and every typology', '',
          'Native parameter (levers.native) in its carbon direction, and the quantity each single-lever run applies '
          '(after the adoption weight). Reference >= Moderate >= Ambitious >= TL in carbon per unit.', '',
          '| lever | direction of the native parameter | native: years failing | applied: years failing |',
          '|---|---|---|---|']
    for lv in LV.LEVERS:
        nat = {s: flat(LV.native(p, lv, s, years)) for s in LEVELS}
        bad_n = set()
        for a, b in zip(LEVELS[:-1], LEVELS[1:]):
            for k in nat[a]:
                x = DIRECTION[lv] * np.broadcast_to(nat[a][k], years.shape)
                y = DIRECTION[lv] * np.broadcast_to(nat[b][k], years.shape)
                bad_n |= {int(v) for v in years[yr][(y > x + TOL * np.maximum(np.abs(x), 1.0))[yr]]}
        app = {s: applied(lv, get({} if s == 'reference' else {lv: s}), ctx['soil'], years) for s in LEVELS}
        bad_a = set()
        for a, b in zip(LEVELS[:-1], LEVELS[1:]):
            for k in app[a]:
                x, y = app[a][k], app[b][k]
                tol = 1e-12 if lv == 'L6' else PW.ORDER_RTOL * np.abs(x) + 1e-15
                bad_a |= {int(v) for v in years[yr][(y > x + tol)[yr]]}
        d = {+1: 'larger = more carbon', -1: 'larger = less carbon'}[DIRECTION[lv]]
        L.append(f"| {lv} {N.LEVERS[lv]} | {d} | {sorted(bad_n) or 'none'} | {sorted(bad_a) or 'none'} |")
        if bad_n or bad_a:
            fails.append(f'1 {lv}: native {sorted(bad_n)}, applied {sorted(bad_a)}')

    # ---- 2. Moderate = midpoint ----
    L += ['', '## 2. Moderate is the midpoint of Reference and Ambitious in the native parameter', '',
          '| lever | max abs (Moderate - (Reference + Ambitious) / 2) | rule |', '|---|---|---|']
    rule2 = {'L1': 'per year: S_ref + gap / 2 (the path midpoint)', 'L8': 'per year and typology: (1 + r(y)) / 2',
             'L9': 'per year: the midpoint of the Reference and Ambitious A4-A5 factor paths (lambda = 0.5)',
             'L10': 'per year and typology: (1 + m_Amb(y)) / 2'}
    for lv in LV.LEVERS:
        n = {s: flat(LV.native(p, lv, s, years)) for s in ('reference', 'moderate', 'ambitious')}
        dev = max(float(np.max(np.abs(n['moderate'][k] - (n['reference'][k] + n['ambitious'][k]) / 2.0))) for k in n['moderate'])
        L.append(f"| {lv} | {dev:.1e} | {rule2.get(lv, 'scalar (or per typology) midpoint')} |")
        if dev > 1e-12:
            fails.append(f'2 {lv}: Moderate is not the midpoint ({dev:.2e})')

    # ---- 3. same level, same parameter; common adoption window ----
    L += ['', '## 3. The same level means the same parameter across runs; the common adoption window', '']
    defs = {'Moderate Pathway': (LV.pathway_levers(LV.PATHWAY, 'moderate'), {x: 'moderate' for x in LV.LEVERS}),
            'Ambitious Pathway': (LV.pathway_levers(LV.PATHWAY, 'ambitious'), {x: 'ambitious' for x in LV.LEVERS}),
            'Theoretical Limit': (LV.tl_levels(LV.TL_COMPONENTS), {x: 'tl' for x in LV.LEVERS})}
    L += ['| run | levers and levels | as expected |', '|---|---|---|']
    for k, (got, exp) in defs.items():
        ok = got == exp
        L.append(f"| {k} | {LV.label(got)} | {'yes' if ok else 'NO'} |")
        if not ok:
            fails.append(f'3 {k}: {LV.label(got)}')
    L += ['', 'Adoption window: each lever at Ambitious under the adopted window (by 2035) and under by 2045; a lever on '
          'the common window changes with it, L9 and L10 (own paths) do not.', '',
          '| lever | applied quantity differs between by 2035 and by 2045 | expected |', '|---|---|---|']
    for lv in LV.LEVERS:
        a = applied(lv, get({lv: 'ambitious'}), ctx['soil'], years)
        b = applied(lv, get({lv: 'ambitious'}, 'by2045'), ctx['soil'], years)
        differs = any(not np.array_equal(a[k], b[k]) for k in a)
        exp = lv not in OWN_WINDOW
        L.append(f"| {lv} | {'yes' if differs else 'no'} | {'yes' if exp else 'no (own path)'} |")
        if differs != exp:
            fails.append(f'3 {lv}: adoption window {"followed" if differs else "not followed"}')
    L += ['', 'Stated exceptions: L9 and L10 follow their own paths (no logistic weight); TL1 under the speed limit '
          '(levers.tl1_path); the instant TL sensitivity (full strength from 2027).']

    # ---- 4. each lever alone monotone in cumulative carbon ----
    L += ['', '## 4. Each lever alone: cumulative carbon 2026-2050 (kt CO2e)', '',
          '| lever | Reference | Moderate | Ambitious | TL | Reference >= Moderate >= Ambitious >= TL |',
          '|---|---|---|---|---|---|']
    alone = {}
    for lv in LV.LEVERS:
        c = {s: stages(ctx, get({} if s == 'reference' else {lv: s}))['carbon_kt'] for s in LEVELS}
        alone[lv] = c
        ok = all(c[b] <= c[a] * (1 + 1e-12) for a, b in zip(LEVELS[:-1], LEVELS[1:]))
        L.append(f"| {lv} | {c['reference']:,.1f} | {c['moderate']:,.1f} | {c['ambitious']:,.1f} | {c['tl']:,.1f} | "
                 f"{'yes' if ok else 'NO'} |")
        if not ok:
            fails.append(f'4 {lv}: ' + ', '.join(f'{s} {c[s]:.1f}' for s in LEVELS))
    # diagnostic: the TL-family release accounting alone (any lever at 'tl' pools the starting surplus and the
    # overbuild into re-occupation, pathways.run), measured with a lever whose TL equals its Reference
    p0 = dict(p, L10=dict(p['L10'], tl={t: {y: 1.0 for y in v} for t, v in p['L10']['tl'].items()}))
    Rn = PW.run(ctx, p0, {'L10': 'tl'})
    Sn = stages(ctx, Rn)
    L += ['', f"Diagnostic: the TL-family release accounting alone (a run with one lever at 'tl' whose TL parameter is "
              f"its Reference value): cumulative carbon {Sn['carbon_kt']:,.1f} kt, {Sn['carbon_kt'] - S0['carbon_kt']:+,.1f} kt "
              f"on the Reference; floor area {Sn['gfa_Mm2']:.3f} Mm2 ({Sn['gfa_Mm2'] - S0['gfa_Mm2']:+.3f}). Any lever "
              "at 'tl' carries this effect on top of its parameter."]

    # ---- 5. no double counting ----
    L += ['', '## 5. Each lever changes only its own inputs and stage (Ambitious, alone)', '',
          'Changed engine inputs (levers.inputs) against the Reference run, and the change of each stage total '
          '2026-2050 (kt; floor area Mm2).', '',
          '| lever | inputs changed | allowed | floor area | A1-A3 | A4-A5 | soil | maintenance (B2, B4) | own stage only |',
          '|---|---|---|---|---|---|---|---|---|']
    keys = ('gfa_Mm2', 'a13_kt', 'a45_kt', 'soil_kt', 'maintenance_kt')
    expect = {lv: {'gfa_Mm2'} for lv in FLOOR_AREA_LEVERS}
    expect.update(L6={'soil_kt'}, L7={'soil_kt'}, L8={'a13_kt'}, L9={'a45_kt'}, L10={'a13_kt', 'maintenance_kt'})
    for lv in LV.LEVERS:
        R = get({lv: 'ambitious'})
        changed = {k for k in set(R['inputs']) | set(R0['inputs'])
                   if k not in R0['inputs'] or k not in R['inputs'] or not same(R['inputs'][k], R0['inputs'][k])}
        S = stages(ctx, R)
        dS = {k: S[k] - S0[k] for k in keys}
        moved = {k for k in keys if abs(dS[k]) > 1e-9 * max(abs(S0[k]), 1.0)}
        if lv in FLOOR_AREA_LEVERS:                     # a floor-area lever moves every stage through the floor area;
            per_m2_same = all(np.array_equal(np.asarray(R['info'][q][t], float), np.asarray(R0['info'][q][t], float))
                              for q in ('a13', 'a45') for t in ctx['typ'])  # its carbon per m2 must not move
            stage_ok = 'gfa_Mm2' in moved and per_m2_same and not (changed & {'intensity', 'intensity_upfront', 'soil', 'events'})
        else:
            stage_ok = moved == expect[lv]
        ok_in = changed <= OWN_INPUTS[lv]
        L.append(f"| {lv} | {', '.join(sorted(changed)) or '-'} | {', '.join(sorted(OWN_INPUTS[lv])) or '(households)'} | "
                 + ' | '.join(f'{dS[k]:+,.3f}' if k == 'gfa_Mm2' else f'{dS[k]:+,.1f}' for k in keys)
                 + f" | {'yes' if (ok_in and stage_ok) else 'NO'} |")
        if not (ok_in and stage_ok):
            fails.append(f'5 {lv}: inputs {sorted(changed)}, stages moved {sorted(moved)}')
    # exact term checks: the intensity change equals the lever's own term
    exact = []
    for lv, term in (('L8', 'a13'), ('L10', 'a13'), ('L9', 'a45')):
        R = get({lv: 'ambitious'})
        dev = max(float(np.max(np.abs((np.asarray(R['inputs']['intensity'][t], float)
                                       - np.asarray(R0['inputs']['intensity'][t], float))
                                      - (np.asarray(R['info'][term][t], float) - np.asarray(R0['info'][term][t], float)))))
                  for t in ctx['typ'])
        exact.append((lv, term, dev))
        if dev > 1e-9:
            fails.append(f'5 {lv}: the intensity change is not its {term} term ({dev:.2e})')
    R = get({'L10': 'ambitious'})
    m = R['info']['m10']
    dev_ev = max(float(np.max(np.abs(np.asarray(R['inputs']['events'][t]) - np.asarray(R0['inputs']['events'][t])
                                     - np.asarray(ctx['events_a13'][t]) * (m[t] - 1.0)[None, :]))) for t in ctx['typ'])
    if dev_ev > 1e-12:
        fails.append(f'5 L10: the event change is not the A1-A3 kernel x (m - 1) ({dev_ev:.2e})')
    R8 = get({'L8': 'ambitious', 'L10': 'ambitious'})
    r8 = {t: 1.0 - R8['info']['w'] * (1.0 - np.asarray(R8['info']['r6'][t], float)) for t in ctx['typ']}
    dev_mul = max(float(np.max(np.abs(np.asarray(R8['info']['a13'][t])
                                      - r8[t] * R8['info']['m10'][t] * (ctx['a13_2025'][t] - np.asarray(ctx['red13'][t])))))
                  for t in ctx['typ'])
    if dev_mul > 1e-9:
        fails.append(f'5 L8 x L10: A1-A3 is not r8 x m10 x the decarbonised path ({dev_mul:.2e})')
    L += ['', 'Exact terms (max abs difference, kg/m2): ' + '; '.join(f'{lv} intensity change - {t} change {d:.1e}'
                                                                   for lv, t, d in exact)
          + f'; L10 event change - A1-A3 kernel x (m - 1) {dev_ev:.1e}; L8 + L10: A1-A3 - r8 x m10 x (A1-A3_2025 - '
            f'red13) {dev_mul:.1e}.',
          '', 'L10 moves maintenance by design: it scales the A1-A3 component of the in-window replacement and repaint '
              'events (calendar-year production). L8 does not: it is a design choice of the new building.']

    # ---- 6. tl_strength ----
    L += ['', '## 6. TL at least as strong as Ambitious (levers.tl_strength)', '', '| item | TL | Ambitious | ok |',
          '|---|---|---|---|']
    for r in p['tl_strength']:
        L.append(f"| {r['item']} | {r['tl']} | {r['ambitious']} | {'yes' if r['ok'] else 'NO'} |")
        if not r['ok']:
            fails.append(f"6 {r['item']}")
    items = {r['item'] for r in p['tl_strength']}
    if items != set(LV.TL_COMPONENTS):
        fails.append(f'6 tl_strength covers {sorted(items)}')

    L += ['', '## Result', '', 'ALL CHECKS PASS.' if not fails else 'FAILED (STOP):', '']
    L += [f'- {f}' for f in fails]
    with open(layout.writing(OUT), 'w') as f:
        f.write('\n'.join(L) + '\n')
    print(f'lever_audit: {OUT}: ' + ('all checks pass' if not fails else f'{len(fails)} failed: ' + '; '.join(fails)))
    if fails:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
