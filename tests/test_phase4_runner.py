from pathlib import Path

import numpy as np
import pandas as pd

from agriflow.research.freeze import ReadinessPolicy, freeze_scope
from agriflow.research.runner import analyze_frozen_scope


def test_frozen_runner_writes_results_and_manifest(tmp_path: Path):
    rng=np.random.default_rng(9)
    rows=[]
    markets=[
        {"state":"S","district":"D1","market":"Leader","market_id":"s__d1__leader","lat":20.0,"lon":77.0,"coordinate_quality":"reviewed_exact"},
        {"state":"S","district":"D2","market":"Follower","market_id":"s__d2__follower","lat":21.0,"lon":78.0,"coordinate_quality":"reviewed_exact"},
    ]
    for year in (2023,2024):
        dates=pd.date_range(f"{year}-01-01",periods=70,freq="D")
        lr=np.r_[0,rng.normal(0,.02,69)]
        fr=np.r_[0,0,lr[:-2]] + rng.normal(0,.001,70)
        lp=1000*np.exp(np.cumsum(lr)); fp=900*np.exp(np.cumsum(fr))
        for d,a,b in zip(dates,lp,fp):
            for district,market,mid,price in [("D1","Leader","s__d1__leader",a),("D2","Follower","s__d2__follower",b)]:
                rows.append({"date":d,"state":"S","district":district,"market":market,"market_id":mid,"commodity":"Onion","modal_price":price,"min_price":price*.9,"max_price":price*1.1,"arrivals":100,"source":"TEST_REAL","source_tier":"PRIMARY_OFFICIAL","data_mode":"REAL"})
    prices=pd.DataFrame(rows)
    policy=ReadinessPolicy(min_span_days=1,min_states=1,min_markets=2,min_observations=50,min_arrival_availability=.5,min_coordinate_coverage=1,min_weather_market_coverage=0)
    freeze,_=freeze_scope(prices,pd.DataFrame(markets),pd.DataFrame(),["Onion"],"2023-01-01","2024-03-31",tmp_path,policy=policy)
    results,summary=analyze_frozen_scope(freeze,max_lag_days=4,min_overlap_days=20,min_edge_corr=.5,fdr_alpha=.05,max_network_markets=10)
    assert (results/"results_manifest.json").exists()
    assert (results/"edge_stability_onion.csv").exists()
    assert (results/"leader_stability_onion.csv").exists()
    assert summary["commodities"]["Onion"]["lead_lag_edges"] >= 1
