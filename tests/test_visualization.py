import json

import pandas as pd
import pytest

from agriflow.data.names import canonical_state
from agriflow.visualization.figures import (
    detect_geo_state_property,
    prepare_state_geojson,
    state_map,
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


def test_malformed_geojson_falls_back_without_crashing(tmp_path):
    path=tmp_path/"states.geojson"
    path.write_text('{"type":"FeatureCollection","features":[]}',encoding="utf-8")
    prices=pd.DataFrame([{
        "state":"Maharashtra","market":"Lasalgaon","commodity":"Onion","modal_price":1200,
    }])
    markets=pd.DataFrame([{"state":"Maharashtra","lat":20.0,"lon":74.0}])
    figure=state_map(prices,markets,"Onion",path)
    assert figure.data[0].type=="scattergeo"
