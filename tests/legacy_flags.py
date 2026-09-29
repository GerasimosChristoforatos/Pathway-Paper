"""Flag values that reproduce the code as it was before Step 2 changed any
default. The equivalence tests apply these to the NEW code and require it to
reproduce the frozen legacy copies exactly, so every earlier behaviour stays
available. Each Step 2 change that alters a default adds its flag here."""
LEGACY_FLAGS = {
    'S_TAIL': 'pchip_end_slope',          # item 5
    'S_ANCHOR_YEAR': 2025,                 # item 6
    'COMPLETION_LAG': 0,                   # item 7
    'CENSUS_SOURCE': 'hardcoded',          # census private-dwelling correction
}
