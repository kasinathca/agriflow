import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def small_prices():
    dates=pd.date_range('2024-01-01',periods=80,freq='D')
    rows=[]
    rng=np.random.default_rng(42)
    for market,state,lat,lon in [('A','State 1',20,75),('B','State 1',21,76),('C','State 2',25,80)]:
        price=2000.0
        for i,d in enumerate(dates):
            price*=np.exp(rng.normal(0,0.01))
            arr=100+rng.normal(0,10)
            rows.append({'date':d,'state':state,'district':'D','market':market,'commodity':'Onion','variety':'General','grade':'FAQ','min_price':price-100,'max_price':price+100,'modal_price':price,'arrivals':max(1,arr),'source':'TEST','data_mode':'DEMO'})
    return pd.DataFrame(rows)
