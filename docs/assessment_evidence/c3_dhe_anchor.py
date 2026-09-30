from common import *
B = run()
units_all = B['hist_total_units'] + B['hist_rv_units']
dhe = B['hist_hh_dhe']
r = (dhe.diff() / units_all.shift(1)).loc[2014:2025]
print('DHE household growth / previous-year consents (all dwellings):'); print(r.round(4).to_string())
# rebased series: same ratio times k
print('k =', round(B['hh_rebase_k'], 4))
print('hist_S 2018..2025:', B['hist_S'].loc[2018:2025].round(4).to_dict())
fy = np.asarray(B['forecast_years'])
# other_dev_2025 and its forward contribution
dev = B['other_dev_2025'] * B['rho_other'] ** np.arange(len(fy)); dev[0] = 0
D = B['future_dwelling_size'].values
mix = sum(B['evolving_gfa_shares'][t].values * B['T_BASELINE_2025'][t] for t in B['typ_names'])
dgfa = dev * (1 - B['rv_share']) * D
print(f"other_dev_2025 {B['other_dev_2025']:+,.0f} dwellings, rho {B['rho_other']:.3f}; forward dwellings {dev[1:].sum():,.0f}; "
      f"GFA {dgfa[1:].sum()/1e6:.3f} Mm2; carbon {(dgfa*mix)[1:].sum()/1e6:,.0f} kt; 2026 share of built {100*dgfa[1]/B['results']['50th']['total'][1]:.1f}%")
t = totals(B)
print(f"without other_dev_2025: GFA {t['GFA']-dgfa[1:].sum()/1e6:.2f} | carbon {t['carbon']-(dgfa*mix)[1:].sum()/1e6:,.0f} | 2026 step "
      f"{100*((B['results']['50th']['total'][1]-dgfa[1])/(B['hist_total_gfa'].loc[2025]*B['built_factor'])-1):+.1f}%")
# decomposition of other_2025
c = Boss.COMPLETION_RATE
print('2025: built all', c*units_all.loc[2025], ' d_hh', B['d_hh'].loc[2025], ' model other', B['other_model_2025'])
# S anchored on 2023 (census-benchmarked) with the Stats NZ shape 2023->2025->forward
S_ann = B['_S_ann']
S23 = B['hist_S'].loc[2023]
S25_alt = S23 * S_ann.loc[2025] / S_ann.loc[2023]
print(f"S_2023 (rebased, Dec) {S23:.4f}; Stats NZ shape 2023->2025 x{S_ann.loc[2025]/S_ann.loc[2023]:.5f} -> S_2025 {S25_alt:.4f} vs observed-anchor {B['hist_S'].loc[2025]:.4f}")
def anchor2023(M):
    orig = M.respond_household_size
    def f(S_ann, pop_ref, hist_S, hist_pop, fyears, b, rho):
        out = orig(S_ann, pop_ref, hist_S, hist_pop, fyears, b, rho)
        out['S_matched'] = float(hist_S.loc[2023]) * S_ann.reindex(fyears).values / float(S_ann.loc[2023])
        return out
    M.respond_household_size = f
B2 = run(patch=anchor2023)
print('anchor S on 2023:', fmt(totals(B2)))
hf = B2['households_forecast']['50th']
print(f"   implied 2025 households {hf[0]:,.0f} vs series {B['hist_hh'].loc[2025]:,.0f}; d_hh 2026 {hf[1]-hf[0]:,.0f} vs {B['results']['50th']['d_hh'][1]:,.0f}")
print('adopted:        ', fmt(totals(B)))
