from stockcal import *
B = run()
cen = B['census']; yh = B['years_hist']
print('census unoccupied split:')
for y in cen.index:
    r = cen.loc[y]
    es = r['empty'] / r['unoccupied'] if np.isfinite(r['empty']) else np.nan
    print(f"  {y}: unoccupied/total {100*r['unoccupied']/r['total_private']:.2f}% | empty share of unoccupied "
          f"{'' if np.isnan(es) else f'{100*es:.1f}%'} | empty rate used {100*B['stock_cal']['knots'].get(y, np.nan):.2f}%")
# Canterbury 2013
t2 = pd.read_excel(Boss.FILE_CENSUS_2013, sheet_name='Table 2', header=None)
row = lambda s: t2[t2[0].astype(str).str.strip().str.lower() == s].iloc[0]
nz, ca = row('total new zealand'), row('canterbury region')
tot = lambda r: float(r[1]) + float(r[6])
print(f"2013 empty rate NZ {100*float(nz[5])/tot(nz):.2f}% | Canterbury {100*float(ca[5])/tot(ca):.2f}% | NZ excl. Canterbury "
      f"{100*(float(nz[5])-float(ca[5]))/(tot(nz)-tot(ca)):.2f}%")
ua = B['hist_total_units'] + B['hist_rv_units']; built = Boss.COMPLETION_RATE * ua
def vac_path(share):
    k = (share * cen['unoccupied'] / cen['total_private'])
    k = k[k.index >= yh.min() - 5]
    return pd.Series(np.interp(yh.astype(float), k.index.values.astype(float), k.values), index=yh), float(k.iloc[-1])
T = totals(B)
cases = [('adopted: measured empty (2013 split pre-2013)', B['stock_cal']['v'], B['v_forward'])]
s13 = float(cen.loc[2013, 'empty'] / cen.loc[2013, 'unoccupied'])
s1823 = float(cen.loc[[2018, 2023], 'empty'].sum() / cen.loc[[2018, 2023], 'unoccupied'].sum())
for lab, s in [(f'constant empty share {100*s13:.1f}% (2013) all censuses', s13),
               (f'constant empty share {100*s1823:.1f}% (2018+2023) all censuses', s1823)]:
    cases.append((lab, *vac_path(s)))
ivs = [(1992,1996),(1997,2001),(2002,2006),(2007,2013),(2014,2018),(2019,2023)]
for lab, v, vf in cases:
    cal = calibrate(B, built, vac=v)
    rs = [float(cal['net'][(yh>=a)&(yh<=b)].sum()/cal['prev'][(yh>=a)&(yh<=b)].sum()) for a,b in ivs]
    fyv = B['v_forward']
    # forward with this definition's latest-census vacancy
    hh = B['households_forecast']['50th']; d = np.maximum(np.insert(np.diff(hh),0,0),0)
    prev = np.concatenate([[hh[0]], hh[:-1]])/(1-vf); dv = cal['dev']*cal['rho']**np.arange(len(hh)); dv[0]=0
    g = (d + d*vf/(1-vf) + cal['rate_net']*prev + dv)*(1-B['rv_share'])*B['future_dwelling_size'].values
    w = (yh>=2014)&(yh<=2023); r0 = float(cal['net'][(yh>=1992)&(yh<=2013)].sum()/cal['prev'][(yh>=1992)&(yh<=2013)].sum())
    hc = (built - cal['net'] + r0*cal['prev'])[w].sum()/built[w].sum()-1
    print(f"\n{lab}\n   net by interval: " + ' | '.join(f"{a-1}-{b} {100*r:+.3f}%" for (a,b),r in zip(ivs, rs)) +
          f"\n   rate 1992-2023 {100*cal['rate_net']:.3f}% | v_forward {100*vf:.2f}% | dev {cal['dev']:+,.0f} | GFA {g[1:].sum()/1e6:.2f} "
          f"({100*(g[1:].sum()/1e6/T['GFA']-1):+.1f}%) | kt {carbon_of(B,g)[1:].sum()/1e6:,.0f} | hindcast 2014-23 (cal. 1992-2013) {100*hc:+.1f}%")
print('\n(dwelling-count identity, no households: 1991-96 +0.068 | 96-01 -0.103 | 01-06 +0.017 | 06-13 +0.098 | 13-18 +0.078 | 18-23 +0.334 %/yr)')
