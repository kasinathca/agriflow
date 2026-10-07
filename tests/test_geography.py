from agriflow.analytics.geography import haversine_km, distance_similarity, distance_effect_summary
import pandas as pd


def test_haversine_reasonable():
    d=haversine_km(19.076,72.8777,18.5204,73.8567)
    assert 110 < d < 140


def test_distance_similarity(small_prices):
    markets=pd.DataFrame([{'market':'A','lat':20,'lon':75},{'market':'B','lat':21,'lon':76},{'market':'C','lat':25,'lon':80}])
    p=distance_similarity(small_prices,markets,'Onion',min_overlap=30)
    assert len(p)==3
    s=distance_effect_summary(p)
    assert s['pairs']==3
