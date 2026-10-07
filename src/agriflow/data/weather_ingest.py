from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from agriflow.data.identity import ensure_market_id
from agriflow.data.sources.nasa_power import NasaPowerSource
from agriflow.data.sources.ceda import year_windows


def power_cell(lat: float, lon: float) -> tuple[float, float]:
    """Coarsen requests to approximately POWER meteorological source resolution.

    NASA POWER documents meteorological products at ~0.5° × 0.625°. The point API
    maps requested coordinates to source cells; this quantization prevents redundant
    requests for nearby mandis while retaining the exact market coordinates separately.
    """
    return round(round(float(lat) / 0.5) * 0.5, 4), round(round(float(lon) / 0.625) * 0.625, 4)


@dataclass(frozen=True)
class PowerJob:
    cell_lat: float
    cell_lon: float
    start_date: str
    end_date: str

    @property
    def key(self) -> str:
        return f"{self.cell_lat:+07.3f}_{self.cell_lon:+08.3f}_{self.start_date}_{self.end_date}"


class PowerHistoricalIngestor:
    def __init__(self, source: NasaPowerSource, raw_dir: Path, processed_dir: Path):
        self.source = source
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.chunk_dir = raw_dir / "power_chunks"
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

    def prepare_market_cells(self, markets: pd.DataFrame) -> tuple[pd.DataFrame, Path]:
        x = ensure_market_id(markets).dropna(subset=["lat", "lon"]).copy()
        if x.empty:
            raise RuntimeError("No markets with usable latitude/longitude coordinates are available")
        cells = x.apply(lambda r: power_cell(float(r.lat), float(r.lon)), axis=1)
        x["power_cell_lat"] = [c[0] for c in cells]
        x["power_cell_lon"] = [c[1] for c in cells]
        cols = [
            c for c in ["market_id", "state", "district", "market", "lat", "lon", "coordinate_quality",
                        "coordinate_source", "power_cell_lat", "power_cell_lon"] if c in x.columns
        ]
        mapping = x[cols].drop_duplicates("market_id").sort_values(["power_cell_lat", "power_cell_lon", "market_id"])
        path = self.processed_dir / "power_market_cells.csv"
        mapping.to_csv(path, index=False)
        return mapping, path

    def plan(self, markets: pd.DataFrame, start_date: str, end_date: str) -> list[PowerJob]:
        mapping, _ = self.prepare_market_cells(markets)
        windows = year_windows(start_date, end_date)
        unique_cells = mapping[["power_cell_lat", "power_cell_lon"]].drop_duplicates()
        return [
            PowerJob(float(r.power_cell_lat), float(r.power_cell_lon), a, b)
            for _, r in unique_cells.iterrows()
            for a, b in windows
        ]

    def _paths(self, job: PowerJob) -> tuple[Path, Path]:
        stem = job.key.replace("+", "p").replace("-", "m")
        return self.chunk_dir / f"{stem}.csv", self.chunk_dir / f"{stem}.meta.json"

    def run(self, jobs: list[PowerJob], force: bool = False, fail_fast: bool = False) -> dict:
        counters = {"planned": len(jobs), "fetched": 0, "cached": 0, "failed": 0, "rows": 0}
        errors: list[dict] = []
        for job in jobs:
            csv_path, meta_path = self._paths(job)
            if csv_path.exists() and meta_path.exists() and not force:
                counters["cached"] += 1
                continue
            try:
                frame = self.source.fetch_daily(job.cell_lat, job.cell_lon, job.start_date, job.end_date)
                frame["power_cell_lat"] = job.cell_lat
                frame["power_cell_lon"] = job.cell_lon
                frame.to_csv(csv_path, index=False)
                meta_path.write_text(json.dumps({
                    "job": asdict(job),
                    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                    "row_count": int(len(frame)),
                    "source": "NASA_POWER",
                    "note": "POWER meteorology is gridded; cell coordinates are analysis locations, not station observations.",
                }, indent=2), encoding="utf-8")
                counters["fetched"] += 1
                counters["rows"] += int(len(frame))
            except Exception as exc:
                counters["failed"] += 1
                errors.append({"job": asdict(job), "error": f"{type(exc).__name__}: {exc}"})
                if fail_fast:
                    raise
        summary = {**counters, "completed_at_utc": datetime.now(timezone.utc).isoformat(), "errors": errors}
        (self.chunk_dir / "_last_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if errors:
            with (self.chunk_dir / "_errors.jsonl").open("a", encoding="utf-8") as fh:
                for row in errors:
                    fh.write(json.dumps({"recorded_at_utc": datetime.now(timezone.utc).isoformat(), **row}) + "\n")
        return summary

    def rebuild_processed(self, markets: pd.DataFrame) -> tuple[pd.DataFrame, Path]:
        mapping, _ = self.prepare_market_cells(markets)
        frames = []
        for path in sorted(self.chunk_dir.glob("*.csv")):
            try:
                f = pd.read_csv(path)
            except pd.errors.EmptyDataError:
                continue
            if not f.empty:
                frames.append(f)
        if not frames:
            raise RuntimeError("No NASA POWER weather chunks are available to rebuild weather_daily.csv")
        weather = pd.concat(frames, ignore_index=True)
        weather["date"] = pd.to_datetime(weather["date"])
        weather = weather.drop_duplicates(["date", "power_cell_lat", "power_cell_lon"], keep="last")
        out = mapping.merge(weather, on=["power_cell_lat", "power_cell_lon"], how="inner", suffixes=("", "_weather"))
        out["source"] = "NASA_POWER"
        out["data_mode"] = "REAL"
        keep = [
            "date", "market_id", "state", "district", "market", "lat", "lon",
            "power_cell_lat", "power_cell_lon", "rainfall_mm", "temperature_c",
            "temperature_max_c", "temperature_min_c", "source", "data_mode",
        ]
        out = out[[c for c in keep if c in out.columns]].sort_values(["market_id", "date"]).reset_index(drop=True)
        target = self.processed_dir / "weather_daily.csv"
        out.to_csv(target, index=False)
        return out, target
