import pandas as pd

from agriflow.data.manual_import import canonicalize_mandi_export
from agriflow.data.processing import normalize_prices, aggregate_market_daily
from agriflow.data.provenance import (
    CURATED_OFFICIAL_DERIVED,
    PRIMARY_OFFICIAL,
    USER_SUPPLIED,
    infer_source_tier,
)
from agriflow.research.freeze import ReadinessPolicy, empirical_readiness


def test_source_tier_inference_is_conservative():
    assert infer_source_tier("DATA_GOV_IN_AGMARKNET", "REAL") == PRIMARY_OFFICIAL
    assert infer_source_tier("CEDA_AGMARKNET", "REAL") == CURATED_OFFICIAL_DERIVED
    assert infer_source_tier("USER_IMPORT", "REAL") == USER_SUPPLIED
    assert infer_source_tier("anything", "DEMO") == "DEMO"


def test_manual_ceda_mapping_accepts_portal_style_columns_and_metadata():
    raw=pd.DataFrame({
        "Date":["01/02/2024"],
        "Min Price (Rs/q)":[1000],
        "Max Price (Rs/q)":[1400],
        "Modal Price (Rs/q)":[1200],
        "Arrival Qty":[55],
    })
    out=canonicalize_mandi_export(
        raw,state="Maharashtra",district="Nashik",market="Lasalgaon",commodity="Onion"
    )
    assert out.iloc[0]["market"]=="Lasalgaon"
    assert out.iloc[0]["modal_price"]==1200
    assert out.iloc[0]["arrivals"]==55


def test_processing_preserves_source_tier_after_daily_aggregation():
    raw=pd.DataFrame({
        "date":["2024-01-01"],"state":["Maharashtra"],"district":["Nashik"],
        "market":["Lasalgaon"],"commodity":["Onion"],"modal_price":[1200],
        "min_price":[1000],"max_price":[1400],"arrivals":[50],
        "source":["CEDA_PORTAL_EXPORT"],"data_mode":["REAL"],
    })
    daily=aggregate_market_daily(normalize_prices(raw))
    assert daily.iloc[0]["source_tier"]==CURATED_OFFICIAL_DERIVED


def test_secondary_or_user_source_is_blocked_from_paper_readiness():
    dates=pd.date_range("2024-01-01",periods=10)
    prices=pd.DataFrame({
        "date":dates,"state":"Maharashtra","district":"Nashik","market":"Lasalgaon",
        "market_id":"maharashtra__nashik__lasalgaon","commodity":"Onion",
        "modal_price":1200,"min_price":1000,"max_price":1400,"arrivals":50,
        "source":"USER_IMPORT","source_tier":"USER_SUPPLIED","data_mode":"REAL",
    })
    policy=ReadinessPolicy(min_span_days=1,min_states=1,min_markets=1,min_observations=1,
        min_arrival_availability=0,min_coordinate_coverage=0,min_weather_market_coverage=0)
    r=empirical_readiness(prices,pd.DataFrame(),pd.DataFrame(),["Onion"],"2024-01-01","2024-01-10",policy)
    assert r["status"]=="BLOCKED"
    gate={g["gate"]:g for g in r["gates"]}["paper_acceptable_source_tier"]
    assert gate["status"]=="FAIL"


def test_generic_import_cli_cannot_self_promote_to_official():
    import pytest
    from agriflow.cli import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args([
            "import-prices", "arbitrary.csv", "--source-tier", PRIMARY_OFFICIAL
        ])


def test_dedicated_official_import_routes_are_separate_commands():
    from agriflow.cli import build_parser, cmd_import_ceda_csv, cmd_import_data_gov_csv

    ceda=build_parser().parse_args(["import-ceda-csv", "ceda.csv", "--commodity", "Onion"])
    ogd=build_parser().parse_args(["import-data-gov-csv", "ogd.csv"])
    assert ceda.func is cmd_import_ceda_csv
    assert ogd.func is cmd_import_data_gov_csv
