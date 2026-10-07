from __future__ import annotations

import json
from pathlib import Path
import time
import pandas as pd

from agriflow.data.identity import ensure_market_id
from agriflow.data.sources.http import HttpClient, SourceError

NIC_STATE_QUERY = (
    "https://mapservice.gov.in/gismapservice/rest/services/"
    "BharatMapService/Admin_Boundary_District/MapServer/0/query"
)
GEObOUNDARIES_META = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


class GeographySource:
    def __init__(self, client: HttpClient | None = None):
        self.client = client or HttpClient(timeout=30, retries=2)

    def _write_geojson(self, data: dict, target: Path, metadata: dict) -> Path:
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            raise SourceError("Boundary provider returned an unexpected GeoJSON schema")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding="utf-8")
        target.with_suffix(".source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return target

    def download_state_geojson(self, target: Path, provider: str = "auto") -> Path:
        """Cache a state-level India vector boundary with explicit provenance.

        `auto` first attempts the NIC/BharatMaps endpoint because it is an Indian
        government reference, but BharatMaps access policies can require institutional
        authorization. It then falls back to geoBoundaries gbOpen ADM1, an openly
        licensed CC-BY 4.0 research boundary suitable for reproducible academic demos.
        """
        errors = []
        if provider in {"auto", "nic"}:
            try:
                params = {
                    "where": "1=1",
                    "outFields": "STNAME,STCODE11,State_LGD",
                    "returnGeometry": "true",
                    "f": "geojson",
                    "outSR": "4326",
                }
                data = self.client.request_json("GET", NIC_STATE_QUERY, params=params)
                return self._write_geojson(data, target, {
                    "provider": "NIC BharatMaps",
                    "url": NIC_STATE_QUERY,
                    "retrieved_for": "AgriFlow state-level visualization",
                    "access_note": "BharatMaps production GIS services may require authorized institutional access; this cached response was only used if the endpoint returned GeoJSON.",
                })
            except Exception as exc:
                errors.append(f"NIC: {exc}")
                if provider == "nic":
                    raise
        if provider in {"auto", "geoboundaries"}:
            try:
                meta = self.client.request_json("GET", GEObOUNDARIES_META)
                url = meta.get("simplifiedGeometryGeoJSON") or meta.get("gjDownloadURL")
                if not url:
                    raise SourceError("geoBoundaries metadata did not expose a GeoJSON URL")
                data = self.client.request_json("GET", url)
                return self._write_geojson(data, target, {
                    "provider": "geoBoundaries gbOpen",
                    "metadata_url": GEObOUNDARIES_META,
                    "download_url": url,
                    "boundary_id": meta.get("boundaryID"),
                    "boundary_year": meta.get("boundaryYearRepresented"),
                    "boundary_source": meta.get("boundarySource"),
                    "license": "CC BY 4.0 (gbOpen); attribution required",
                })
            except Exception as exc:
                errors.append(f"geoBoundaries: {exc}")
                if provider == "geoboundaries":
                    raise
        raise SourceError("Unable to retrieve an India ADM1 GeoJSON. " + " | ".join(errors))

    def geocode_markets(
        self,
        markets: pd.DataFrame,
        delay_s: float = 1.1,
        *,
        max_requests: int = 50,
    ) -> pd.DataFrame:
        """Small, one-time Nominatim geocoding helper with explicit safeguards.

        The public OSMF Nominatim service discourages bulk geocoding and requires
        caching plus <=1 request/second. AgriFlow therefore caps this helper to a small
        one-time batch. Pan-India runs should import a reviewed coordinate table or use
        a self-hosted/approved geocoder instead.
        """
        x = ensure_market_id(markets)
        max_requests = min(max(int(max_requests), 1), 50)
        delay_s = max(float(delay_s), 1.05)
        rows = []
        requests_used = 0
        for _, row in x.iterrows():
            base = row.to_dict()
            if pd.notna(base.get("lat")) and pd.notna(base.get("lon")):
                rows.append(base)
                continue
            lat = lon = None
            quality = "unresolved"
            source = ""
            queries = [
                (f"{row['market']}, {row.get('district','')}, {row['state']}, India", "nominatim_market"),
                (f"{row.get('district','')}, {row['state']}, India", "nominatim_district_centroid"),
            ]
            for query, label in queries:
                if requests_used >= max_requests:
                    break
                try:
                    data = self.client.request_json(
                        "GET",
                        NOMINATIM,
                        params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "in"},
                        headers={"User-Agent": "AgriFlow-Academic-Project/1.2 (student research; cached one-time geocoding)"},
                    )
                    requests_used += 1
                    if data:
                        lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                        quality = label
                        source = "OpenStreetMap Nominatim"
                        break
                except Exception:
                    requests_used += 1
                finally:
                    time.sleep(max(1.05, delay_s))
            rows.append({**base, "lat": lat, "lon": lon, "coordinate_quality": quality, "coordinate_source": source})
        return pd.DataFrame(rows)
