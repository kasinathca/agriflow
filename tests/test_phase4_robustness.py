import numpy as np
import pandas as pd

from agriflow.analytics.robustness import yearly_edge_stability, yearly_leader_stability


def _price_from_returns(start, returns):
    vals=[start]
    for r in returns[1:]:
        vals.append(vals[-1]*np.exp(r))
    return np.array(vals)


def test_yearly_edge_stability_recovers_persistent_two_day_direction():
    rng=np.random.default_rng(17)
    rows=[]
    for year in (2023,2024):
        dates=pd.date_range(f"{year}-01-01",periods=100,freq="D")
        lead_ret=np.r_[0,rng.normal(0,.02,99)]
        follow_ret=np.r_[0,0,lead_ret[:-2]] + rng.normal(0,.001,100)
        p1=_price_from_returns(1000,lead_ret)
        p2=_price_from_returns(900,follow_ret)
        for d,a,b in zip(dates,p1,p2):
            rows += [
                {"date":d,"state":"S","district":"D1","market":"Leader","market_id":"s__d1__leader","commodity":"Onion","modal_price":a},
                {"date":d,"state":"S","district":"D2","market":"Follower","market_id":"s__d2__follower","commodity":"Onion","modal_price":b},
            ]
    yearly,stable=yearly_edge_stability(pd.DataFrame(rows),"Onion",max_lag=4,min_overlap=30,min_abs_corr=.5,fdr_alpha=.05,max_markets=10)
    hit=stable[(stable.leader_id=="s__d1__leader") & (stable.follower_id=="s__d2__follower")]
    assert len(hit)==1
    assert hit.iloc[0].years_supported==2
    assert hit.iloc[0].persistence_ratio==1
    annual,leaders=yearly_leader_stability(yearly)
    assert not annual.empty and not leaders.empty
    assert leaders.iloc[0].market=="Leader"
