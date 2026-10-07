from pathlib import Path

import pandas as pd
import pytest

from agriflow.research.freeze import ReadinessPolicy, empirical_readiness, freeze_scope, verify_freeze


def _frames(mode="REAL"):
    dates=pd.date_range("2023-01-01",periods=120,freq="D")
    rows=[]
    markets=[]
    weather=[]
    for i,(state,district,market,lat,lon) in enumerate([
        ("A","D1","M1",20.0,77.0),("A","D2","M2",20.5,77.5),("B","D3","M3",21.0,78.0)
    ]):
        mid=f"{state.lower()}__{district.lower()}__{market.lower()}"
        markets.append({"state":state,"district":district,"market":market,"market_id":mid,"lat":lat,"lon":lon,"coordinate_quality":"reviewed_exact"})
        for j,d in enumerate(dates):
            rows.append({"date":d,"state":state,"district":district,"market":market,"market_id":mid,"commodity":"Onion","modal_price":1000+i*50+j,"min_price":900,"max_price":1200,"arrivals":100+j%5,"source":"TEST_SOURCE","source_tier":"PRIMARY_OFFICIAL","data_mode":mode})
            weather.append({"date":d,"state":state,"district":district,"market":market,"market_id":mid,"rainfall_mm":j%7,"temperature_c":28.0})
    return pd.DataFrame(rows),pd.DataFrame(markets),pd.DataFrame(weather)


def test_readiness_real_scope_can_pass_with_explicit_small_policy():
    p,m,w=_frames("REAL")
    policy=ReadinessPolicy(min_span_days=100,min_states=2,min_markets=3,min_observations=300,min_arrival_availability=.9,min_coordinate_coverage=1,min_weather_market_coverage=1)
    r=empirical_readiness(p,m,w,["Onion"],"2023-01-01","2023-04-30",policy)
    assert r["status"]=="READY"
    assert r["summary"]["data_modes"]==["REAL"]


def test_freeze_blocks_demo_without_testing_override(tmp_path: Path):
    p,m,w=_frames("DEMO")
    with pytest.raises(ValueError,match="real_data_only"):
        freeze_scope(p,m,w,["Onion"],"2023-01-01","2023-04-30",tmp_path)


def test_freeze_hash_verification_detects_tamper(tmp_path: Path):
    p,m,w=_frames("DEMO")
    path,_=freeze_scope(p,m,w,["Onion"],"2023-01-01","2023-04-30",tmp_path,allow_demo_for_testing=True)
    assert verify_freeze(path)["ok"]
    with (path/"market_daily.csv").open("a",encoding="utf-8") as fh:
        fh.write("tamper\n")
    result=verify_freeze(path)
    assert not result["ok"]
    assert any("checksum mismatch" in e for e in result["errors"])
