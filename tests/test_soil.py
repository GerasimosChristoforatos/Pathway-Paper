"""Item 8: soil loss only on floor area built on newly converted land."""
import numpy as np

from test_identities import close


def test_soil_zero_on_net_replacement(B):
    import Boss
    if Boss.SOIL_ON_REPLACEMENT:
        return
    E = B['engine_out']['50th']
    D = E['D']
    repl = np.clip(E['demol'] + E['unc'] + E['join_redev'], 0, None) * (1 - B['rv_share']) * D
    assert close(E['soil_free_gfa'], repl)
    soil_t = sum(E['gfa_t'][j] * B['SOIL_INTENSITY'][t] for j, t in enumerate(E['typ']))
    expect = soil_t * (1 - repl / E['total'])
    # soil in the engine's carbon = carbon - materials
    mat = sum(E['gfa_t'][j] * (B['T_BASELINE_2025'][t] - B['SOIL_INTENSITY'][t]) for j, t in enumerate(E['typ']))
    assert close((E['carbon'] - mat)[1:], expect[1:])
    # the reported soil line equals it (2026-2050)
    assert abs(B['_soil'] - expect[1:].sum()) < 1e-6 * expect[1:].sum()
