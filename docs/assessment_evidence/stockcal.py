"""Offline replica of Boss's calibrate_stock + forward 'other' terms, so that the
built-dwelling series can be replaced (e.g. by a distributed lag). Checked
against Boss before use."""
from common import *

def calibrate(B, built_all, completion=None, window=(None, None), vac=None, hh=None):
    """built_all: dwellings BUILT (all categories, incl. RV) per calendar year."""
    yh = B['years_hist']; hh = B['hist_hh'] if hh is None else hh
    v = B['stock_cal']['v'] if vac is None else vac
    d_h = hh.diff().fillna(0); inv = 1 / (1 - v)
    stock = hh * inv; allow = d_h * v * inv; change = hh.shift(1) * inv.diff()
    net = built_all - d_h - allow - change; prev = stock.shift(1)
    a = window[0] or Boss.DEMOLITION_CALIB_START; b = window[1] or B['calib_end']
    w = (yh >= a) & (yh <= b)
    rate_net = float(net[w].sum() / prev[w].sum())
    _n = net[(yh >= Boss.DEMOLITION_CALIB_START) & (yh <= B['calib_end'])].values
    rho = float(np.clip(np.corrcoef(_n[:-1], _n[1:])[0, 1], 0, 0.95))
    other_2025 = float(built_all.loc[2025] - d_h.loc[2025])
    model_2025 = float(allow.loc[2025] + change.loc[2025] + rate_net * prev.loc[2025])
    return dict(rate_net=rate_net, rho=rho, dev=other_2025 - model_2025, net=net, prev=prev,
                allow=allow, change=change, stock=stock, v=v)

def forward_gfa(B, rate_net, dev, rho, rv_share=None):
    """Median-path in-scope built GFA 2025..2050 (index 0 = 2025, not used)."""
    fy = np.asarray(B['forecast_years']); hh = B['households_forecast']['50th']
    v = B['v_forward']; rv = B['rv_share'] if rv_share is None else rv_share
    d = np.maximum(np.insert(np.diff(hh), 0, 0), 0)
    prev = np.concatenate([[hh[0]], hh[:-1]]) / (1 - v)
    units = d * v / (1 - v) + rate_net * prev
    dv = dev * rho ** np.arange(len(fy)); dv[0] = 0
    dwell = (d + units + dv) * (1 - rv)
    return dwell * B['future_dwelling_size'].values

def carbon_of(B, gfa):
    mix = sum(B['evolving_gfa_shares'][t].values * B['T_BASELINE_2025'][t] for t in B['typ_names'])
    return gfa * mix

if __name__ == '__main__':
    B = run()
    ua = B['hist_total_units'] + B['hist_rv_units']
    for c in (0.95, 0.92):
        cal = calibrate(B, c * ua)
        g = forward_gfa(B, cal['rate_net'], cal['dev'], cal['rho'])
        print(f"completion {c}: rate_net {100*cal['rate_net']:.4f}% dev {cal['dev']:,.0f} rho {cal['rho']:.3f} -> GFA {g[1:].sum()/1e6:.3f}, carbon {carbon_of(B,g)[1:].sum()/1e6:,.1f}")
    print('Boss: rate', 100*(Boss.DEMOLITION_RATE + B['unconsented_rate']), 'dev', B['other_dev_2025'], 'GFA', B['results']['50th']['total'][1:].sum()/1e6)
