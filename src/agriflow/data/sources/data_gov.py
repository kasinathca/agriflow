from __future__ import annotations

from typing import Iterator
import pandas as pd

from agriflow.data.sources.http import HttpClient, SourceError

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


class DataGovMandiSource:
    """Official data.gov.in AGMARKNET daily resource connector."""

    def __init__(self, api_key: str, client: HttpClient | None = None):
        if not api_key:
            raise ValueError("DATA_GOV_API_KEY is required for real data.gov.in ingestion")
        self.api_key = api_key
        self.client = client or HttpClient()

    def fetch_page(self, offset: int = 0, limit: int = 1000, **filters: str) -> dict:
        params: dict[str, str | int] = {
            "api-key": self.api_key,
            "format": "json",
            "offset": offset,
            "limit": min(limit, 1000),
        }
        for field, value in filters.items():
            if value:
                # Current resource uses state.keyword on some deployments; plain state is also seen.
                key = "state.keyword" if field == "state" else field
                params[f"filters[{key}]"] = value
        data = self.client.request_json("GET", BASE_URL, params=params)
        if not isinstance(data, dict) or "records" not in data:
            raise SourceError("Unexpected data.gov.in response schema")
        return data

    def iter_records(self, max_records: int = 5000, page_size: int = 1000, **filters: str) -> Iterator[dict]:
        offset = 0
        while offset < max_records:
            data = self.fetch_page(offset=offset, limit=min(page_size, max_records - offset), **filters)
            rows = data.get("records", [])
            if not rows:
                break
            yield from rows
            offset += len(rows)
            if len(rows) < min(page_size, max_records - offset + len(rows)):
                break

    def fetch_dataframe(self, max_records: int = 5000, **filters: str) -> pd.DataFrame:
        return pd.DataFrame(list(self.iter_records(max_records=max_records, **filters)))
