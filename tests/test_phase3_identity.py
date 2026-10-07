import pandas as pd

from agriflow.data.processing import normalize_prices
from agriflow.analytics.lead_lag import market_returns


def test_same_market_name_in_two_states_gets_distinct_ids():
    df=pd.DataFrame([
        {'date':'2024-01-01','state':'State A','district':'D1','market':'Central Market','commodity':'Onion','modal_price':1000},
        {'date':'2024-01-01','state':'State B','district':'D2','market':'Central Market','commodity':'Onion','modal_price':1100},
    ])
    out=normalize_prices(df)
    assert out.market_id.nunique()==2


def test_returns_keep_duplicate_display_names_separate():
    rows=[]
    for state,district,base in [('State A','D1',1000),('State B','D2',1200)]:
        for i,d in enumerate(pd.date_range('2024-01-01',periods=4)):
            rows.append({'date':d,'state':state,'district':district,'market':'Central Market','commodity':'Onion','modal_price':base+i*10})
    r=market_returns(pd.DataFrame(rows),'Onion')
    assert r.market_id.nunique()==2
