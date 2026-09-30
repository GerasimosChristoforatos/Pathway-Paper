from common import *
from scipy import stats
B = run()
hs = B['hist_shares']; win = hs.loc[hs.index >= Boss.TREND_WINDOW_START]
yrs = win.index.values.astype(float); n = len(yrs); X = np.c_[np.ones(n), yrs]
print(f"ALR mix trend window {int(yrs[0])}-{int(yrs[-1])}: n = {n}; Newey-West lag = {int(np.floor(4*(n/100)**(2/9)))}")
for t in ['Townhouses', 'Apartments']:
    y = np.log(win[t] / win['Detached']).values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ beta
    se_ols = np.sqrt((e**2).sum()/(n-2) * np.linalg.inv(X.T@X)[1,1])
    cov, L = Boss.newey_west_cov(X, e); se_hac = np.sqrt(cov[1,1])
    r1 = np.corrcoef(e[:-1], e[1:])[0,1]
    neff = n * (1 - r1) / (1 + r1)
    se_ar1 = se_ols * np.sqrt((1 + r1) / (1 - r1)) if r1 > 0 else se_ols
    print(f"  {t:<11} slope {beta[1]:+.4f}/yr | SE OLS {se_ols:.4f} | NW-HAC {se_hac:.4f} | AR(1)-inflated {se_ar1:.4f} "
          f"(r1 = {r1:+.2f}, n_eff ~ {neff:.1f}) | t_crit(df=12) {stats.t.ppf(.975, 12):.2f}")
    print(f"     share 2025 {100*B['shares_2025'][t]:.1f}% -> 2050 {100*B['evolving_gfa_shares'][t].iloc[-1]:.1f}%")
for phi in (0.62, 0.8, 0.98):
    print(f"  phi {phi}: cumulative slopes applied by 2050 = {phi*(1-phi**25)/(1-phi):.2f}; asymptote {phi/(1-phi):.1f}")
# household-size regression (diagnostic) small-n note
hr = B['hh_response']; print(f"dS on dP regression: n = {hr['n_fit']}, HAC lag {hr['hac_lag']}, b/SE_hac = {hr['b']/hr['se_hac']:.1f}")
# size sigma in the MC
print('dwelling size by typology 2016-2025 (m2):'); print(B['hist_dwelling_size'].loc[2016:2025].round(1).to_string())
print('size_ref', {k: round(v,1) for k,v in B['size_ref'].items()})
