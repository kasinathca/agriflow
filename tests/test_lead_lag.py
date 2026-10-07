import numpy as np
import pandas as pd
from agriflow.analytics.lead_lag import infer_lead_lag_edges, benjamini_hochberg


def test_bh_monotonic_in_original_order_values_bounded():
    q=benjamini_hochberg([0.01,0.04,0.03,0.20])
    assert len(q)==4
    assert all(0<=x<=1 for x in q)
    assert q[0] <= q[3]


def test_known_two_day_leader_direction():
    rng=np.random.default_rng(123)
    dates=pd.date_range('2024-01-01',periods=180,freq='D')
    r_a=rng.normal(0,0.025,len(dates))
    r_b=np.zeros(len(dates)); r_b[2:]=0.92*r_a[:-2]+rng.normal(0,0.003,len(dates)-2)
    p_a=2000*np.exp(np.cumsum(r_a));p_b=2100*np.exp(np.cumsum(r_b))
    rows=[]
    for market,prices in [('Leader',p_a),('Follower',p_b)]:
        for d,p in zip(dates,prices):
            rows.append({'date':d,'market':market,'commodity':'Onion','modal_price':p})
    df=pd.DataFrame(rows)
    edges=infer_lead_lag_edges(df,'Onion',max_lag=5,min_overlap=80,min_abs_corr=.5,fdr_alpha=.05,max_markets=10)
    assert len(edges)==1
    e=edges.iloc[0]
    assert e.leader=='Leader' and e.follower=='Follower'
    assert int(e.lag_days)==2
    assert e["corr"]>.8
