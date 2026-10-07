import pandas as pd

from agriflow.analytics.geography import distance_effect_summary
from agriflow.analytics.weather import event_study


def test_qap_distance_summary_is_deterministic_and_bounded():
    rows=[]
    ids=['a','b','c','d']
    vals={('a','b'):(100,.8),('a','c'):(200,.6),('a','d'):(500,.1),('b','c'):(120,.7),('b','d'):(420,.2),('c','d'):(300,.3)}
    for (a,b),(d,c) in vals.items():
        rows.append({'market_a_id':a,'market_b_id':b,'distance_km':d,'return_corr':c})
    p=pd.DataFrame(rows)
    s1=distance_effect_summary(p,permutations=99,seed=7)
    s2=distance_effect_summary(p,permutations=99,seed=7)
    assert s1['qap_p_value']==s2['qap_p_value']
    assert 0 < s1['qap_p_value'] <= 1


def test_weather_event_study_declusters_adjacent_extremes():
    dates=pd.date_range('2024-01-01',periods=30,freq='D')
    rows=[]
    for i,d in enumerate(dates):
        z=3.0 if i in (10,11,12) else 0.0
        rows.append({'date':d,'state':'S','district':'D','market':'M','commodity':'Onion',
                     'modal_price':100+i,'arrivals':100,'rainfall_anomaly_z':z})
    es=event_study(pd.DataFrame(rows),threshold=2.0,horizons=(1,),separation_days=2)
    assert len(es)==1
