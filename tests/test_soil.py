"""Item 8: soil loss only on floor area built on newly converted land."""
import numpy as np

import inventory as INV

from test_identities import close


def test_soil_zero_on_net_replacement(B):
    import projection
    if projection.SOIL_ON_REPLACEMENT:
        return
    E = B['engine_out']['50th']
    D = E['D']
    repl = np.clip(E['demol'] + E['unc'] + E['join_redev'], 0, None) * (1 - B['rv_share']) * D
    assert close(E['soil_free_gfa'], repl)
    soil_t = sum(E['gfa_t'][j] * B['SOIL_INTENSITY'][t] for j, t in enumerate(E['typ']))
    expect = soil_t * (1 - repl / E['total'])
    # soil lost at conversion (MODEL v3.1.0: emitted in the window by the ACCOUNTING rule, inventory.spread)
    assert close(E['soil_conv'][1:], expect[1:])
    # soil in the carbon of the new cohorts = carbon_new - construction-year materials - in-window events
    mat = sum(E['gfa_t'][j] * (np.asarray(B['T_INT'][t]) - B['SOIL_INTENSITY'][t]) for j, t in enumerate(E['typ']))   # 2025 or decarbonised
    emitted = expect if E['soil_spread'] is None else INV.spread(expect, int(E['soil_spread']))[0]
    assert close((E['carbon_new'] - mat - E['b_t'].sum(axis=0))[1:], emitted[1:])
    # the reported soil line equals the emitted soil 2026-2050; conversions = emitted + after 2050
    assert abs(B['_soil'] - emitted[1:].sum()) < 1e-6 * emitted[1:].sum()
    if E['soil_spread'] is not None:
        assert abs(emitted[1:].sum() + E['soil_after'] - expect[1:].sum()) < 1e-9 * expect[1:].sum()
