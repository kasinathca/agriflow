from __future__ import annotations

import pandas as pd

from agriflow.data.repository import DataRepository


def _real_prices(path):
    pd.DataFrame([{
        "date": "2024-01-01", "state": "Maharashtra", "district": "Nashik",
        "market": "Lasalgaon", "commodity": "Onion", "variety": "General",
        "grade": "FAQ", "min_price": 900, "max_price": 1100,
        "modal_price": 1000, "arrivals": 10, "arrival_unit": "UNKNOWN",
        "source": "CEDA_AGMARKNET", "source_tier": "CURATED_OFFICIAL_DERIVED",
        "data_mode": "REAL",
    }]).to_csv(path / "processed" / "market_daily.csv", index=False)


def test_real_prices_never_fall_back_to_demo_auxiliary_data(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    _real_prices(tmp_path)
    repo = DataRepository(tmp_path)
    weather = repo.load_weather()
    markets = repo.load_markets()

    assert weather.empty
    assert markets.empty
    assert {"date", "market_id", "rainfall_mm"}.issubset(weather.columns)
    assert {"market_id", "lat", "lon"}.issubset(markets.columns)
