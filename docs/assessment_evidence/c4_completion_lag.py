from stockcal import *
B = run()
cen = B['census']
c = pd.read_excel(Boss.FILE_CONSENTS, sheet_name=Boss.CONSENT_SHEET); c['Date'] = pd.to_datetime(c['Date'])
ua = B['hist_total_units'] + B['hist_rv_units']
print("Little's law W = L / lambda  (L = dwellings under construction on census night, March)")
for y in [1991, 1996, 2001, 2006, 2013, 2018, 2023]:
    L = cen.loc[y, 'under_construction']
    m = (c.Date >= pd.Timestamp(y - 1, 4, 1)) & (c.Date < pd.Timestamp(y, 4, 1))
    lam_mar = c.loc[m, 'Dwellings'].sum() if m.any() else np.nan
    print(f"  {y}: L {L:>7,.0f} | W vs 3-typology cal-year consents {L/B['hist_total_units'].get(y,np.nan):.2f} (as in Boss) | "
          f"vs all-dwelling cal-year {L/ua.get(y,np.nan):.2f} | vs all-dwelling yr to March {L/lam_mar:.2f}")
T = totals(B)
g_obs25 = B['hist_total_gfa'].loc[2025] * Boss.COMPLETION_RATE
print(f"\nadopted (no lag): rate_net {100*(Boss.DEMOLITION_RATE+B['unconsented_rate']):.3f}% | GFA {T['GFA']:.2f} | kt {T['carbon']:,.0f} | step {T['step']:+.1f}%")
for w in (0.25, 0.5, 0.78):
    built = Boss.COMPLETION_RATE * ((1 - w) * ua + w * ua.shift(1))
    cal = calibrate(B, built)
    g = forward_gfa(B, cal['rate_net'], cal['dev'], cal['rho'])
    # 2025 comparison value on the same lagged basis (floor area)
    gh = B['hist_total_gfa']
    g25 = Boss.COMPLETION_RATE * ((1 - w) * gh.loc[2025] + w * gh.loc[2024])
    print(f"lag weight w={w:.2f}: rate_net {100*cal['rate_net']:.3f}% dev {cal['dev']:+,.0f} rho {cal['rho']:.2f} -> GFA {g[1:].sum()/1e6:.2f} "
          f"({100*(g[1:].sum()/1e6/T['GFA']-1):+.1f}%) | kt {carbon_of(B,g)[1:].sum()/1e6:,.0f} | built-2025 {g25/1e6:.3f} vs {g_obs25/1e6:.3f} Mm2 | "
          f"step {100*(g[1]/g25-1):+.1f}%")
print('\nconsents (all dwellings) 2019-2025:', ua.loc[2019:2025].astype(int).to_dict())
print('3-typology GFA 2023-2025 (Mm2):', (B['hist_total_gfa'].loc[2023:2025]/1e6).round(3).to_dict())
