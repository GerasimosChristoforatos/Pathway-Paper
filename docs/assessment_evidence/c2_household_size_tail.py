from common import *
from scipy.interpolate import PchipInterpolator
B = run()
Sk = B['S_knots']; print(Sk.to_string(index=False))
fy = np.asarray(B['forecast_years'])
S = B['df_forecast']['PopTotal_50th'].values / B['households_forecast']['50th']
print('annual S (model):', ' '.join(f"{y}:{s:.4f}" for y, s in zip(fy, S) if y in (2025,2030,2035,2038,2040,2043,2045,2050)))
print('min S year:', fy[np.argmin(S)], f"{S.min():.4f}")
f = PchipInterpolator(Sk['Year'].values.astype(float), Sk['S'].values)
print(f"PCHIP end slope at 2043 (per yr): {float(f.derivative()(2043.0)):+.5f}; last-interval slope {(Sk.S.iloc[-1]-Sk.S.iloc[-2])/5:+.5f}; mean 2018-43 slope {(Sk.S.iloc[-1]-Sk.S.iloc[0])/25:+.5f}")
# rounding of households to the nearest thousand
pop = Boss.load_national_pop_projection(variant='Medium').set_index('Year')['Population']
hh = Boss.extract_household_projection_block(Boss.FILE_HOUSEHOLDS_PROJ, variant_label='Medium').set_index('Year')['Households']
for y in Sk.Year:
    lo, hi = pop[y] / (hh[y] + 500), pop[y] / (hh[y] - 500)
    print(f"  {y}: HH {hh[y]:,.0f} (published to nearest 1000) -> S in [{lo:.4f}, {hi:.4f}], half-width {0.5*(hi-lo):.4f}")
d = Sk.S.iloc[-1] - Sk.S.iloc[-2]
print(f"2038->2043 change {d:+.4f}; max change attributable to rounding of the two knots: +/-{(pop[2038]/(hh[2038]-500)-pop[2038]/(hh[2038]+500))/2 + (pop[2043]/(hh[2043]-500)-pop[2043]/(hh[2043]+500))/2:.4f}")
# consolidation (avoided) by year
av = B['df_forecast']['Ann_GFA_HouseSplit_Avoided_50th'].values
yrs = fy[av > 0]; print('years with consolidation savings:', yrs.min() if len(yrs) else None, '-', yrs.max() if len(yrs) else None,
      f" total {av[1:].sum()/1e6:.3f} Mm2; 2039-2050 {av[(fy>=2039)].sum()/1e6:.3f}")
# age structure (medium, 2018-base update, Table 4)
t4 = pd.read_excel(Boss.FILE_POP_SIZE_PAIR, sheet_name='Table 4', header=None)
i = t4.index[t4[0].astype(str).str.startswith('New Zealand')][0]
ag = t4.iloc[i:i+11, 1:7].astype(float); ag.columns = ['Year','0-14','15-39','40-64','65+','Total']
ag['65+ share %'] = 100*ag['65+']/ag['Total']; ag['0-14 share %'] = 100*ag['0-14']/ag['Total']
print(ag.round(2).to_string(index=False))

def tail(mode):
    def patch(M):
        orig = M.statsnz_size_shape
        def f2(variant, forecast_years):
            S_knots, S_ann, pop_ref = orig(variant, forecast_years)
            last = int(S_knots.Year.max())
            yrs = S_ann.index.values
            if mode == 'flat':
                slope = 0.0
            elif mode == 'mean_slope':
                slope = (S_knots.S.iloc[-1] - S_knots.S.iloc[0]) / (S_knots.Year.iloc[-1] - S_knots.Year.iloc[0])
            S_new = S_ann.copy()
            S_new[yrs > last] = S_ann.loc[last] + slope * (yrs[yrs > last] - last)
            return S_knots, S_new, pop_ref
        M.statsnz_size_shape = f2
    return patch
for mode in ('flat', 'mean_slope'):
    print(f"{mode:<11}", fmt(totals(run(patch=tail(mode)))))
print(f"{'adopted':<11}", fmt(totals(B)))
