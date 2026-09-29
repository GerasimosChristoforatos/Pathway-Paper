from stockcal import *
B = run()
yh = B['years_hist']; ua = B['hist_total_units'] + B['hist_rv_units']
built = Boss.COMPLETION_RATE * ua
cal = calibrate(B, built)
net, prev = cal['net'], cal['prev']
need = built - net                                   # = d_h + allow + change (demand before replacement)
th = B['hist_typ_units']['Townhouses']
def rate(a, b): 
    w = (yh >= a) & (yh <= b); return float(net[w].sum() / prev[w].sum())
print('net replacement rate (household identity) by census interval, and townhouse consents per 1000 stock:')
ivs = [(1992,1996),(1997,2001),(2002,2006),(2007,2013),(2014,2018),(2019,2023)]
X, Y = [], []
for a, b in ivs:
    w = (yh >= a) & (yh <= b)
    x = float(th[w].sum() / prev[w].sum()); X.append(x); Y.append(rate(a, b))
    print(f"  {a-1}-{b}: net {100*Y[-1]:+.3f}%/yr | townhouses {1000*x:.2f} per 1000 stock/yr | TH share of in-scope consents {100*th[w].sum()/B['hist_total_units'][w].sum():.1f}%")
X, Y = np.array(X), np.array(Y)
def hind(a0, b0, a1, b1, label):
    w1 = (yh >= a1) & (yh <= b1); act = built[w1].sum()
    out = []
    # (i) constant long-run rate
    r = rate(a0, b0); out.append(('constant long-run', (need + r * prev)[w1].sum()))
    # (ii) most recent census interval before the origin
    last = [iv for iv in ivs if iv[1] <= b0][-1]; r2 = rate(*last)
    out.append((f'recent interval {last[0]-1}-{last[1]}', (need + r2 * prev)[w1].sum()))
    # (iii) linked: net rate = alpha + beta * townhouses/stock, OLS on census intervals up to origin
    k = np.array([iv[1] <= b0 for iv in ivs]); A = np.c_[np.ones(k.sum()), X[k]]
    coef, *_ = np.linalg.lstsq(A, Y[k], rcond=None)
    pred_rate = coef[0] + coef[1] * th / prev
    out.append((f'linked (n={k.sum()} intervals; a={100*coef[0]:+.3f}%, b={coef[1]:.3f})', (need + pred_rate * prev)[w1].sum()))
    # oracle: actual net over test window
    print(f"\nHINDCAST {label}: calibrate {a0}-{b0}, test {a1}-{b1}; actual built {act:,.0f}")
    for lab, p in out:
        print(f"   {lab:<52} predicted {p:>9,.0f}  error {100*(p/act-1):+.1f}%")
    return coef
hind(1992, 2013, 2014, 2023, 'A')
hind(1992, 2018, 2019, 2023, 'B')
# identifiability of the linked model on all 6 intervals
A = np.c_[np.ones(6), X]; coef, res, *_ = np.linalg.lstsq(A, Y, rcond=None)
r = Y - A @ coef; s2 = (r**2).sum() / (6 - 2); cov = s2 * np.linalg.inv(A.T @ A)
lev = np.diag(A @ np.linalg.inv(A.T @ A) @ A.T)
print(f"\nlinked model on all 6 intervals: b = {coef[1]:.3f} (SE {np.sqrt(cov[1,1]):.3f}, t = {coef[1]/np.sqrt(cov[1,1]):.2f}, df=4); leverage of 2018-23 = {lev[-1]:.2f}")
k = np.arange(5); A5 = np.c_[np.ones(5), X[k]]; c5, *_ = np.linalg.lstsq(A5, Y[k], rcond=None)
print(f"   dropping 2018-23: b = {c5[1]:.3f}")
print('   interpretation: b = net dwellings removed per townhouse consented (if causal)')
