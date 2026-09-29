from common import *
B = run()
dm = B['dem_mat'] / 1e6
soil = dm.loc['SOIL']; tot = dm.sum()
print('SOIL carbon by demand band, 2026-2050 (kt):'); print(soil.round(1).to_string())
print(f"total soil {soil.sum():,.1f} kt = {100*soil.sum()/tot.sum():.1f}% of {tot.sum():,.0f}")
repl = soil['Consumption: demolition'] + soil['Calibrated stock residual']
rest = soil.sum() - repl
print(f"replacement bands (demolition + residual): {repl:,.1f} kt; remainder {rest:,.1f} kt")
C = tot.sum()
for g in (0.0, 0.25, 0.5, 0.75, 1.0):
    print(f"  greenfield share g={g:.2f}: soil {g*rest:,.0f} kt -> total {C - soil.sum() + g*rest:,.0f} kt ({100*((C - soil.sum() + g*rest)/C-1):+.1f}%)")
tf = pd.read_csv(Boss.FILE_FACTORS_TYPOLOGY).set_index('Typology')
print(tf[['n_buildings','n_independent','embodied_materials','emb_building_min','emb_building_max','emb_jackknife_min','emb_jackknife_max','SOC_avg','FSI']].round(2).to_string())
gfa_t = B['evol_typ_total'].iloc[1:].sum()/1e6
print('floor area by typology 2026-2050 (Mm2):', gfa_t.round(2).to_dict(), ' carbon (kt):', (B['carbon_total_typ'].iloc[1:].sum()/1e6).round(0).to_dict())
bf = pd.read_csv('data/factors_building.csv'); print(bf[['id','Subtype','GFA','FSI','SOC_avg','duplicate_of']].to_string(index=False))
