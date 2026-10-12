import json

import pandas as pd
import pytest

from agriflow.data.names import canonical_state
from agriflow.visualization.figures import (
    detect_geo_state_property,
    network_figure,
    prepare_state_geojson,
    state_map,
    weather_price_figure,
)


def _geo(property_name="shapeName", state="Mahārāshtra"):
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {property_name: state},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[72, 18], [80, 18], [80, 22], [72, 22], [72, 18]]],
            },
        }],
    }


def test_state_property_detection_and_diacritic_canonicalization():
    geo=_geo()
    assert detect_geo_state_property(geo,{"Maharashtra"})=="shapeName"
    prepared,_=prepare_state_geojson(geo,{"Maharashtra"})
    assert prepared["features"][0]["properties"]["AGRIFLOW_STATE"]=="Maharashtra"
    ring=prepared["features"][0]["geometry"]["coordinates"][0]
    area=sum(
        ring[i][0]*ring[(i+1)%len(ring)][1]-ring[(i+1)%len(ring)][0]*ring[i][1]
        for i in range(len(ring))
    )/2
    assert area < 0
    assert canonical_state("TAMIL NĀDU")=="Tamil Nadu"


def test_missing_state_and_unsupported_geojson_are_rejected():
    with pytest.raises(ValueError,match="do not match"):
        prepare_state_geojson(_geo(),{"Kerala"})
    with pytest.raises(ValueError,match="supported"):
        detect_geo_state_property(_geo("province"),{"Maharashtra"})
    with pytest.raises(ValueError,match="no features"):
        detect_geo_state_property({"type":"FeatureCollection","features":[]})


def test_successful_choropleth_construction(tmp_path):
    path=tmp_path/"states.geojson"
    path.write_text(json.dumps(_geo()),encoding="utf-8")
    prices=pd.DataFrame([{
        "state":"Maharashtra","market":"Lasalgaon","commodity":"Onion","modal_price":1200,
    }])
    figure=state_map(prices,pd.DataFrame(),"Onion",path)
    assert figure.data[0].type=="choropleth"
    assert figure.data[0].featureidkey=="properties.AGRIFLOW_STATE"
    assert list(figure.data[0].locations)==["Maharashtra"]
    assert figure.layout.geo.projection.scale==3.7
    assert figure.layout.geo.fitbounds is None


def test_choropleth_locations_follow_all_matched_states(tmp_path):
    geo = _geo()
    geo["features"].append(_geo(state="Karnātaka")["features"][0])
    path=tmp_path/"states.geojson"
    path.write_text(json.dumps(geo),encoding="utf-8")
    prices=pd.DataFrame([
        {"state":"Maharashtra","market":"Lasalgaon","commodity":"Onion","modal_price":1200},
        {"state":"Karnataka","market":"Bengaluru","commodity":"Onion","modal_price":1400},
    ])
    figure=state_map(prices,pd.DataFrame(),"Onion",path)
    assert set(figure.data[0].locations)=={"Maharashtra","Karnataka"}


def test_state_without_selected_commodity_does_not_crash(tmp_path):
    path=tmp_path/"states.geojson"
    path.write_text(json.dumps(_geo()),encoding="utf-8")
    prices=pd.DataFrame([{
        "state":"Maharashtra","market":"Lasalgaon","commodity":"Tomato","modal_price":1200,
    }])
    figure=state_map(prices,pd.DataFrame(),"Onion",path)
    assert "No state values" in figure.layout.annotations[0].text


def test_malformed_geojson_falls_back_without_crashing(tmp_path):
    path=tmp_path/"states.geojson"
    path.write_text('{"type":"FeatureCollection","features":[]}',encoding="utf-8")
    prices=pd.DataFrame([{
        "state":"Maharashtra","market":"Lasalgaon","commodity":"Onion","modal_price":1200,
    }])
    markets=pd.DataFrame([{"state":"Maharashtra","lat":20.0,"lon":74.0}])
    figure=state_map(prices,markets,"Onion",path)
    assert figure.data[0].type=="scattergeo"


def test_real_auxiliary_gaps_render_explicit_unavailable_figures():
    prices=pd.DataFrame([{
        "date":pd.Timestamp("2024-01-01"),"market_id":"m1","market":"Market 1",
        "commodity":"Onion","modal_price":1200,
    }])
    weather=weather_price_figure(prices,"m1","Onion")
    assert "REAL weather observations are unavailable" in weather.layout.annotations[0].text

    edges=pd.DataFrame([{
        "leader_id":"m1","follower_id":"m2","leader":"Market 1","follower":"Market 2",
        "lag_days":1,"corr":0.5,"q_value":0.01,
    }])
    scores=pd.DataFrame([{
        "market_id":"m1","market":"Market 1","influence_score":1.0,"outbound_edges":1,
    }])
    markets=pd.DataFrame(columns=["market_id","state","district","market","lat","lon"])
    network=network_figure(edges,markets,scores)
    assert "coordinates are unavailable" in network.layout.annotations[0].text
