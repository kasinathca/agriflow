from __future__ import annotations

import pandas as pd
from agriflow.data.sources.http import HttpClient, SourceError

URL = "https://mausam.imd.gov.in/api/statewise_rainfall_api.php"


class ImdRainfallReference:
    """Current/reference state rainfall from IMD's documented statewise rainfall API."""

    def __init__(self, client: HttpClient | None = None):
        self.client = client or HttpClient()

    def fetch(self, state_id: str | None = None) -> pd.DataFrame:
        params = {"id": state_id} if state_id else None
        raw = self.client.request_json("GET", URL, params=params)
        if isinstance(raw, dict):
            for key in ("data", "records", "result"):
                if isinstance(raw.get(key), list):
                    raw = raw[key]
                    break
        if not isinstance(raw, list):
            raise SourceError("Unexpected IMD rainfall response schema")
        return pd.DataFrame(raw)
