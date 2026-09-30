from stockcal import *
B = run(); cen = B['census']
c = pd.read_excel(Boss.FILE_CONSENTS, sheet_name=Boss.CONSENT_SHEET); d = pd.to_datetime(c['Date'])
fy_ = np.where(d.dt.month >= 7, d.dt.year + 1, d.dt.year); cons = c.groupby(fy_)['Dwellings'].sum()
cy = [y for y in cen.index if y >= 1991]
num = {'all': 0, 'to2018': 0, 'pipe_all': 0}; den = {'all': 0, 'to2018': 0}
for y0, y1 in zip(cy[:-1], cy[1:]):
    b = Boss.COMPLETION_RATE * cons.loc[y0:y1 - 1].sum()
    dd = cen.loc[y1, 'total_private'] - cen.loc[y0, 'total_private']
    dp = cen.loc[y1, 'under_construction'] - cen.loc[y0, 'under_construction']
    st = (cen.loc[y0, 'total_private'] + cen.loc[y1, 'total_private']) / 2 * (y1 - y0)
    num['all'] += b - dd; den['all'] += st; num['pipe_all'] += b - dp - dd
    if y1 <= 2018: num['to2018'] += b - dd; den['to2018'] += st
r_all, r18, rp = num['all']/den['all'], num['to2018']/den['to2018'], num['pipe_all']/den['all']
print(f"dwelling-count identity: 1991-2023 {100*r_all:+.3f}%/yr | net of pipeline {100*rp:+.3f}% | 1991-2018 {100*r18:+.3f}% | household identity (Boss) {100*(Boss.DEMOLITION_RATE+B['unconsented_rate']):+.3f}%")
ua = B['hist_total_units'] + B['hist_rv_units']; built = Boss.COMPLETION_RATE * ua
cal = calibrate(B, built); T = totals(B)
for lab, r in [('dwelling-count 1991-2023', r_all), ('dwelling-count net of pipeline', rp)]:
    dev = float(built.loc[2025] - B['d_hh'].loc[2025] - cal['allow'].loc[2025] - cal['change'].loc[2025] - r*cal['prev'].loc[2025])
    g = forward_gfa(B, r, dev, cal['rho'])
    print(f"  forward with {lab}: rate {100*r:.3f}% dev {dev:+,.0f} -> GFA {g[1:].sum()/1e6:.2f} ({100*(g[1:].sum()/1e6/T['GFA']-1):+.1f}%) | kt {carbon_of(B,g)[1:].sum()/1e6:,.0f}")
