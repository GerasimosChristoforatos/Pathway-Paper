"""C8 / C9: Building_factors checks, stale comment numbers, pooling switch."""
import contextlib
import importlib
import io
import tempfile
import time
from pathlib import Path

from common import REPO, np, pd, run

# ---- C8: the documented reconciliation needs a GWP column -----------------
chars = pd.read_excel(REPO / 'data' / 'building_data.xlsx', sheet_name='2')
print('building_data.xlsx sheet 2 columns:', list(chars.columns),
      '-> GWP present' if 'GWP' in chars.columns else '-> no GWP column: the reconciliation block never runs')
s3 = pd.read_excel(REPO / 'data' / 'building_data.xlsx', sheet_name='3')
print(f'soil orders in sheet 3: {len(s3) - 1} (+ aggregate row):', list(s3.iloc[:-1, 0]))

# ---- C8/C9: pooling scheme switch -----------------------------------------
import Building_factors as BF  # noqa: E402
tmp = Path(tempfile.mkdtemp())
for scheme in ('equal_subtypes', 'equal_buildings', 'gfa_weighted'):
    BF = importlib.reload(BF)
    BF.WEIGHT_SCHEME = scheme            # what a caller would naturally do
    BF.OUT_MATERIAL, BF.OUT_TYPOLOGY, BF.OUT_BUILDING = (str(tmp / n) for n in ('m.csv', 't.csv', 'b.csv'))
    with contextlib.redirect_stdout(io.StringIO()):
        BF.main()
    via_attr = pd.read_csv(tmp / 't.csv').set_index('Typology')['total_with_SOC'].round(1).to_dict()
    BF = importlib.reload(BF)
    BF.pool.__defaults__ = (scheme,)     # the default is bound at definition time
    BF.OUT_MATERIAL, BF.OUT_TYPOLOGY, BF.OUT_BUILDING = (str(tmp / n) for n in ('m.csv', 't.csv', 'b.csv'))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            BF.main()
        real = pd.read_csv(tmp / 't.csv').set_index('Typology')['total_with_SOC'].round(1).to_dict()
    except Exception as e:  # noqa: BLE001
        real = f'CRASH: {type(e).__name__}: {e}'
    print(f'{scheme:<16} set via WEIGHT_SCHEME: {via_attr}\n{"":<16} actually applied:      {real}')

# ---- C9: numbers quoted in Boss.py comments vs what the code now produces --
for basis, quoted in (('per_capita', '101.98'), ('per_household', '61.77'),
                      ('extra_space_plus_other', '52-63 (62.8)')):
    B = run(CONSUMPTION_BASIS=basis)
    print(f'CONSUMPTION_BASIS={basis:<24} comment says {quoted:>12} Mm2; code gives '
          f"{B['results']['50th']['total'][1:].sum() / 1e6:.2f}")
B = run()
print(f"FILE_POP_SIZE_PAIR comment: S(2050) 2.582, GFA 80.31 Mm2; code gives S(2050) "
      f"{(B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th'])[-1]:.3f}, "
      f"GFA {B['results']['50th']['total'][1:].sum() / 1e6:.2f}")
print('update-vintage file referenced in the comment present in data/:',
      (REPO / 'data' / 'subnational-population-projections-2018base-2048-update.xlsx').exists())
g, c = B['gfa_growth_typ'].sum(), B['gfa_cons_typ'].sum()
print(f'summary table: growth {g:.2f} + consumption {c:.2f} = {g + c:.2f} vs total {B["tot_built"]:.2f} '
      f'(house-splitting {B["gfa_hs_typ"].sum():.2f} not shown)')
print(f"Boss [4] band 'completion 92%' (linearised) vs a full re-run: see Boss printout 73.05 vs "
      f"{run(COMPLETION_RATE=0.92)['results']['50th']['total'][1:].sum() / 1e6:.2f} Mm2")
t = time.time()
rng = np.random.default_rng(42)
o = np.arange(34.)
for _ in range(20000):
    st = rng.integers(0, 31, size=9)
    np.concatenate([o[i:i + 4] for i in st])[:34].mean()
print(f"unused 20,000-draw 'other' bootstrap: {time.time() - t:.2f} s per Boss run")
