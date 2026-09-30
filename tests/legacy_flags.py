"""Flag values that reproduce the code as it was before Step 2 changed any
default. The equivalence tests apply these to the NEW code and require it to
reproduce the frozen legacy copies exactly, so every earlier behaviour stays
available. Each Step 2 change that alters a default adds its flag here."""
LEGACY_FLAGS = {
    'S_TAIL': 'pchip_end_slope',          # item 5
    'S_ANCHOR_YEAR': 2025,                 # item 6
    'COMPLETION_LAG': 0,                   # item 7
    'CENSUS_SOURCE': 'hardcoded',          # census private-dwelling correction
    'NET_REPLACEMENT_SOURCE': 'household_identity',   # item 4
    'NOWCAST_POPULATION': False,           # A1(a): observed 2026 population growth
    'NEAR_TERM_JOIN': 'carried_deviation',  # A1(a)+(c): nowcast 2026-27, three channels
    'REPLACEMENT_SCENARIO': 'S1',          # item 2 of the CP2 decisions
    'HOUSEHOLD_CHANNEL': 'permanent',      # CP3 order, item 2 (inactive without the nowcast join)
    'SOIL_ON_REPLACEMENT': True,           # item 8
    'MIX_MODE': 'trend',                   # v1.0.2 storylines
}
