from __future__ import annotations

import pandas as pd

from agriflow.data.sources.http import HttpClient, SourceError

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


class NasaPowerSource:
    def __init__(self, client: HttpClient | None = None):
        self.client = client or HttpClient(timeout=60)

    def fetch_daily(self, lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
        params = {
            "parameters": "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN",
            "community": "AG",
            "longitude": round(float(lon), 4),
            "latitude": round(float(lat), 4),
            "start": start_date.replace("-", ""),
            "end": end_date.replace("-", ""),
            "format": "JSON",
            "time-standard": "LST",
        }
        raw = self.client.request_json("GET", BASE_URL, params=params)
        params_data = raw.get("properties", {}).get("parameter", {}) if isinstance(raw, dict) else {}
        if not params_data:
            raise SourceError("Unexpected NASA POWER response schema")
        keys = sorted(set().union(*(v.keys() for v in params_data.values())))
        rows = []
        for k in keys:
            rows.append({
                "date": pd.to_datetime(k, format="%Y%m%d"),
                "rainfall_mm": params_data.get("PRECTOTCORR", {}).get(k),
                "temperature_c": params_data.get("T2M", {}).get(k),
                "temperature_max_c": params_data.get("T2M_MAX", {}).get(k),
                "temperature_min_c": params_data.get("T2M_MIN", {}).get(k),
                "lat": lat,
                "lon": lon,
                "source": "NASA_POWER",
                "data_mode": "REAL",
            })
        df = pd.DataFrame(rows)
        for col in ["rainfall_mm", "temperature_c", "temperature_max_c", "temperature_min_c"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(-999, pd.NA)
        return df
