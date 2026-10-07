from __future__ import annotations

"""CEDA Agri Market Data API connector.

The CEDA API is an authenticated, ID-based access layer over AGMARKNET data.
This module keeps the API-specific IDs at the boundary and emits a canonical
AgriFlow market-day schema with human-readable names.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

import pandas as pd

from agriflow.data.names import canonical_state
from agriflow.data.provenance import CURATED_OFFICIAL_DERIVED
from agriflow.data.sources.http import HttpClient, SourceError

BASE_URL = "https://api.ceda.ashoka.edu.in/v1"


@dataclass(frozen=True)
class CedaCommodity:
    commodity_id: int
    commodity_name: str


@dataclass(frozen=True)
class CedaGeography:
    census_state_id: int
    census_state_name: str
    census_district_id: int
    census_district_name: str


class CedaHistoricalSource:
    """Authenticated client for CEDA's current ``/v1/agmarknet`` API.

    Authentication is a Bearer token.  The project uses ``CEDA_API_KEY`` in its
    configuration because that is the user-facing credential label, while the
    HTTP contract still sends ``Authorization: Bearer <token>``.
    """

    def __init__(self, api_key: str, client: HttpClient | None = None):
        if not api_key:
            raise ValueError("CEDA_API_KEY is required for CEDA historical ingestion")
        self.api_key = api_key.strip()
        self.client = client or HttpClient(timeout=45, retries=4)
        self._commodities: list[dict[str, Any]] | None = None
        self._geographies: list[dict[str, Any]] | None = None
        self._market_cache: dict[tuple[int, int, int, str], list[dict[str, Any]]] = {}

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _unwrap(payload: Any) -> list[dict[str, Any]]:
        """Normalize the response envelope used by CEDA.

        Current responses are documented/observed as
        ``{"output": {"type": "success", "data": [...]}}``.  A direct
        ``{"data": [...]}`` shape is accepted defensively so minor API wrapper
        changes do not silently corrupt data.
        """
        if not isinstance(payload, dict):
            raise SourceError("Unexpected CEDA response: expected a JSON object")
        if "output" in payload:
            output = payload.get("output") or {}
            if not isinstance(output, dict):
                raise SourceError("Unexpected CEDA output envelope")
            status = str(output.get("type", "success")).lower()
            if status != "success":
                raise SourceError(f"CEDA API error: {output.get('message', 'unknown error')}")
            rows = output.get("data", [])
        else:
            rows = payload.get("data", [])
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise SourceError("Unexpected CEDA response: data is not a list")
        return [r for r in rows if isinstance(r, dict)]

    def _call(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = self.client.request_json(
            method,
            f"{BASE_URL}{path}",
            json=json,
            headers=self.headers,
        )
        return self._unwrap(payload)

    # ---------- reference/catalog endpoints ----------
    def list_commodities(self, refresh: bool = False) -> list[dict[str, Any]]:
        if refresh or self._commodities is None:
            self._commodities = self._call("GET", "/agmarknet/commodities")
        return list(self._commodities)

    def list_geographies(self, refresh: bool = False) -> list[dict[str, Any]]:
        if refresh or self._geographies is None:
            self._geographies = self._call("GET", "/agmarknet/geographies")
        return list(self._geographies)

    def list_markets(
        self,
        commodity_id: int,
        state_id: int,
        district_id: int,
        indicator: str = "price",
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        key = (int(commodity_id), int(state_id), int(district_id), indicator)
        if refresh or key not in self._market_cache:
            self._market_cache[key] = self._call(
                "POST",
                "/agmarknet/markets",
                json={
                    "commodity_id": int(commodity_id),
                    "state_id": int(state_id),
                    "district_id": int(district_id),
                    "indicator": indicator,
                },
            )
        return list(self._market_cache[key])

    # ---------- data endpoints ----------
    def fetch_prices(
        self,
        commodity_id: int,
        state_id: int,
        start_date: str,
        end_date: str,
        district_ids: Iterable[int] | None = None,
        market_ids: Iterable[int] | None = None,
    ) -> pd.DataFrame:
        body: dict[str, Any] = {
            "commodity_id": int(commodity_id),
            "state_id": int(state_id),
            "from_date": start_date,
            "to_date": end_date,
        }
        d = [int(x) for x in (district_ids or [])]
        m = [int(x) for x in (market_ids or [])]
        if d:
            body["district_id"] = d
        if m:
            body["market_id"] = m
        return pd.DataFrame(self._call("POST", "/agmarknet/prices", json=body))

    def fetch_quantities(
        self,
        commodity_id: int,
        state_id: int,
        start_date: str,
        end_date: str,
        district_ids: Iterable[int] | None = None,
        market_ids: Iterable[int] | None = None,
    ) -> pd.DataFrame:
        body: dict[str, Any] = {
            "commodity_id": int(commodity_id),
            "state_id": int(state_id),
            "from_date": start_date,
            "to_date": end_date,
        }
        d = [int(x) for x in (district_ids or [])]
        m = [int(x) for x in (market_ids or [])]
        if d:
            body["district_id"] = d
        if m:
            body["market_id"] = m
        return pd.DataFrame(self._call("POST", "/agmarknet/quantities", json=body))

    # ---------- name resolution ----------
    @staticmethod
    def _match_name(rows: list[dict[str, Any]], value: str, field: str, kind: str) -> dict[str, Any]:
        target = value.strip().casefold()
        exact = [r for r in rows if str(r.get(field, "")).strip().casefold() == target]
        if exact:
            return exact[0]
        partial = [r for r in rows if target in str(r.get(field, "")).strip().casefold()]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            sample = ", ".join(sorted({str(r.get(field, "")) for r in partial})[:8])
            raise ValueError(f"Ambiguous {kind} '{value}'. Matches include: {sample}")
        raise ValueError(f"Unknown {kind} '{value}' in the CEDA catalog")

    def resolve_commodity(self, name: str) -> dict[str, Any]:
        return self._match_name(self.list_commodities(), name, "commodity_name", "commodity")

    def resolve_state(self, name: str) -> dict[str, Any]:
        target = canonical_state(name)
        rows = self.list_geographies()
        # Geography repeats a state once per district; deduplicate before matching.
        states: dict[int, dict[str, Any]] = {}
        for r in rows:
            sid = int(r["census_state_id"])
            states.setdefault(
                sid,
                {
                    "census_state_id": sid,
                    "census_state_name": canonical_state(str(r["census_state_name"])),
                },
            )
        return self._match_name(list(states.values()), target, "census_state_name", "state")

    def districts_for_state(self, state_id: int) -> list[dict[str, Any]]:
        rows = [
            r for r in self.list_geographies()
            if int(r.get("census_state_id", -1)) == int(state_id)
        ]
        rows.sort(key=lambda r: str(r.get("census_district_name", "")))
        return rows

    # ---------- canonicalization ----------
    def canonical_market_chunk(
        self,
        commodity: dict[str, Any],
        state: dict[str, Any],
        district: dict[str, Any],
        start_date: str,
        end_date: str,
        include_quantities: bool = True,
    ) -> pd.DataFrame:
        """Fetch one district/commodity interval and emit canonical market-day rows."""
        commodity_id = int(commodity["commodity_id"])
        state_id = int(state["census_state_id"])
        district_id = int(district["census_district_id"])

        market_rows = self.list_markets(commodity_id, state_id, district_id, indicator="price")
        market_lookup = {int(r["market_id"]): str(r["market_name"]).strip() for r in market_rows}
        market_ids = sorted(market_lookup)
        if not market_ids:
            return pd.DataFrame()

        prices = self.fetch_prices(
            commodity_id,
            state_id,
            start_date,
            end_date,
            district_ids=[district_id],
            market_ids=market_ids,
        )
        if prices.empty:
            return pd.DataFrame()

        quantities = pd.DataFrame()
        if include_quantities:
            try:
                quantities = self.fetch_quantities(
                    commodity_id,
                    state_id,
                    start_date,
                    end_date,
                    district_ids=[district_id],
                    market_ids=market_ids,
                )
            except SourceError:
                # Prices remain usable when quantity access is temporarily unavailable.
                quantities = pd.DataFrame()

        prices = prices.copy()
        prices["market_id"] = pd.to_numeric(prices.get("market_id"), errors="coerce")
        prices = prices.dropna(subset=["market_id"])
        prices["market_id"] = prices["market_id"].astype(int)

        key = ["date", "commodity_id", "census_state_id", "census_district_id", "market_id"]
        if not quantities.empty and all(c in quantities.columns for c in key):
            q = quantities.copy()
            q["market_id"] = pd.to_numeric(q["market_id"], errors="coerce")
            q = q.dropna(subset=["market_id"])
            q["market_id"] = q["market_id"].astype(int)
            qty_col = "quantity" if "quantity" in q.columns else (
                "arrivals" if "arrivals" in q.columns else None
            )
            if qty_col:
                q = q[key + [qty_col]].rename(columns={qty_col: "arrivals"})
                prices = prices.merge(q, on=key, how="left")
            else:
                prices["arrivals"] = pd.NA
        else:
            prices["arrivals"] = pd.NA

        out = pd.DataFrame({
            "date": prices["date"],
            "state": canonical_state(str(state["census_state_name"])),
            "district": str(district["census_district_name"]).strip(),
            "market": prices["market_id"].map(market_lookup).fillna(
                prices["market_id"].map(lambda x: f"Market #{x}")
            ),
            "commodity": str(commodity["commodity_name"]).strip(),
            "variety": "",
            "grade": "",
            "min_price": prices.get("min_price"),
            "max_price": prices.get("max_price"),
            "modal_price": prices.get("modal_price"),
            "arrivals": prices.get("arrivals"),
            "source": "CEDA_AGMARKNET",
            "source_tier": CURATED_OFFICIAL_DERIVED,
            "data_mode": "REAL",
            "source_commodity_id": commodity_id,
            "source_state_id": state_id,
            "source_district_id": district_id,
            "source_market_id": prices["market_id"],
        })
        return out


def year_windows(start_date: str, end_date: str) -> list[tuple[str, str]]:
    """Split an inclusive date interval into calendar-year windows for resumable ingestion."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    windows: list[tuple[str, str]] = []
    cur = start
    while cur <= end:
        window_end = min(date(cur.year, 12, 31), end)
        windows.append((cur.isoformat(), window_end.isoformat()))
        cur = window_end + timedelta(days=1)
    return windows
