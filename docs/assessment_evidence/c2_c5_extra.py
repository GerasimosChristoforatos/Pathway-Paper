from stockcal import *
B = run(); fy = np.asarray(B['forecast_years'])
av = B['df_forecast']['Ann_GFA_HouseSplit_Avoided_50th'].values
print(f"consolidation 2039-2043 {av[(fy>=2039)&(fy<=2043)].sum()/1e6:.3f} | 2044-2050 {av[fy>=2044].sum()/1e6:.3f} Mm2")
# linked model identifiability under a constant empty share (2018+2023)
cen = B['census']; yh = B['years_hist']
s = float(cen.loc[[2018,2023],'empty'].sum()/cen.loc[[2018,2023],'unoccupied'].sum())
k = (s*cen['unoccupied']/cen['total_private']); k = k[k.index >= yh.min()-5]
v = pd.Series(np.interp(yh.astype(float), k.index.values.astype(float), k.values), index=yh)
ua = B['hist_total_units'] + B['hist_rv_units']
cal = calibrate(B, Boss.COMPLETION_RATE*ua, vac=v)
th = B['hist_typ_units']['Townhouses']
ivs = [(1992,1996),(1997,2001),(2002,2006),(2007,2013),(2014,2018),(2019,2023)]
X = np.array([th[(yh>=a)&(yh<=b)].sum()/cal['prev'][(yh>=a)&(yh<=b)].sum() for a,b in ivs])
Y = np.array([cal['net'][(yh>=a)&(yh<=b)].sum()/cal['prev'][(yh>=a)&(yh<=b)].sum() for a,b in ivs])
A = np.c_[np.ones(6), X]; c, *_ = np.linalg.lstsq(A, Y, rcond=None); r = Y - A@c
se = np.sqrt((r**2).sum()/4*np.linalg.inv(A.T@A)[1,1])
print(f"linked model, constant empty share: b = {c[1]:.3f} SE {se:.3f} t {c[1]/se:.2f}")
# the MC regime endpoints under this definition
w = (yh>=2019)&(yh<=2023); print(f"2019-23 net under constant share {100*cal['net'][w].sum()/cal['prev'][w].sum():.3f}% vs adopted 0.355%")
