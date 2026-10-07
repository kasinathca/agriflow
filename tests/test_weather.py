import numpy as np
import pandas as pd
from agriflow.analytics.weather import weather_anomalies, join_market_weather, event_study
from agriflow.analytics.events import detect_market_crunches


def test_weather_join_and_anomaly(small_prices):
    dates=pd.date_range('2024-01-01',periods=80,freq='D')
    rows=[]
    for market in ['A','B','C']:
        for i,d in enumerate(dates):
            rows.append({'date':d,'market':market,'state':'State 1','rainfall_mm':50 if i==40 else 2+(i%5),'temperature_c':25+(i%7)})
    w=pd.DataFrame(rows)
    wa=weather_anomalies(w)
    assert 'rainfall_anomaly_z' in wa
    joined=join_market_weather(small_prices,w)
    assert joined.rainfall_mm.notna().all()
    es=event_study(joined,threshold=1.0,horizons=(1,))
    assert isinstance(es,pd.DataFrame)


def test_crunch_detection():
    dates=pd.date_range('2024-01-01',periods=40)
    rows=[]
    for i,d in enumerate(dates):
        rows.append({'date':d,'state':'S','market':'M','commodity':'Onion','modal_price':5000 if i==20 else 2000+i,'arrivals':5 if i==20 else 100+i%5})
    e=detect_market_crunches(pd.DataFrame(rows),arrival_threshold=-1.5,price_threshold=1.5)
    assert not e.empty
    assert pd.Timestamp(e.iloc[0].date)==dates[20]
