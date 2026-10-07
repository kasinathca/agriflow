from __future__ import annotations

"""Resumable historical ingestion for the CEDA AGMARKNET API."""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Iterable

import pandas as pd

from agriflow.data.processing import normalize_prices, aggregate_market_daily
from agriflow.data.sources.ceda import CedaHistoricalSource, year_windows


def slug(value: str) -> str:
    x = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return x.strip("_") or "unknown"


@dataclass(frozen=True)
class CedaJob:
    commodity_id: int
    commodity_name: str
    state_id: int
    state_name: str
    district_id: int
    district_name: str
    start_date: str
    end_date: str

    @property
    def key(self) -> str:
        return (
            f"{slug(self.commodity_name)}/{slug(self.state_name)}/"
            f"{self.district_id}_{slug(self.district_name)}_{self.start_date}_{self.end_date}"
        )


class CedaHistoricalIngestor:
    """Fetch CEDA in small cached jobs and rebuild a reproducible processed panel.

    One job = one commodity × district × calendar-year interval.  Completed jobs
    are checkpointed, so a national multi-year run can be safely interrupted and
    resumed without repeating successful API calls.
    """

    def __init__(self, source: CedaHistoricalSource, raw_dir: Path, processed_dir: Path):
        self.source = source
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.chunk_dir = raw_dir / "ceda_chunks"
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def cache_catalogs(self) -> tuple[Path, Path]:
        commodities = pd.DataFrame(self.source.list_commodities())
        geographies = pd.DataFrame(self.source.list_geographies())
        cp = self.raw_dir / "ceda_catalog_commodities.csv"
        gp = self.raw_dir / "ceda_catalog_geographies.csv"
        commodities.to_csv(cp, index=False)
        geographies.to_csv(gp, index=False)
        return cp, gp

    def _selected_commodities(self, names: Iterable[str]) -> list[dict]:
        unique: dict[int, dict] = {}
        for name in names:
            row = self.source.resolve_commodity(name)
            unique[int(row["commodity_id"])] = row
        return list(unique.values())

    def _selected_states(self, names: Iterable[str] | None) -> list[dict]:
        if names:
            unique: dict[int, dict] = {}
            for name in names:
                row = self.source.resolve_state(name)
                unique[int(row["census_state_id"])] = row
            return sorted(unique.values(), key=lambda r: str(r["census_state_name"]))

        # All states represented by at least one geography row.
        unique = {}
        for r in self.source.list_geographies():
            sid = int(r["census_state_id"])
            unique.setdefault(
                sid,
                {
                    "census_state_id": sid,
                    "census_state_name": str(r["census_state_name"]).strip(),
                },
            )
        return sorted(unique.values(), key=lambda r: str(r["census_state_name"]))

    def plan(
        self,
        commodities: Iterable[str],
        start_date: str,
        end_date: str,
        states: Iterable[str] | None = None,
        district_limit: int | None = None,
    ) -> list[CedaJob]:
        commodity_rows = self._selected_commodities(commodities)
        state_rows = self._selected_states(states)
        windows = year_windows(start_date, end_date)
        jobs: list[CedaJob] = []
        for commodity in commodity_rows:
            for state in state_rows:
                districts = self.source.districts_for_state(int(state["census_state_id"]))
                if district_limit:
                    districts = districts[:district_limit]
                for district in districts:
                    for a, b in windows:
                        jobs.append(CedaJob(
                            commodity_id=int(commodity["commodity_id"]),
                            commodity_name=str(commodity["commodity_name"]),
                            state_id=int(state["census_state_id"]),
                            state_name=str(state["census_state_name"]),
                            district_id=int(district["census_district_id"]),
                            district_name=str(district["census_district_name"]),
                            start_date=a,
                            end_date=b,
                        ))
        return jobs

    def _job_paths(self, job: CedaJob) -> tuple[Path, Path]:
        base = self.chunk_dir / slug(job.commodity_name) / slug(job.state_name)
        base.mkdir(parents=True, exist_ok=True)
        stem = f"{job.district_id}_{slug(job.district_name)}_{job.start_date}_{job.end_date}"
        return base / f"{stem}.csv", base / f"{stem}.meta.json"

    def run(
        self,
        jobs: list[CedaJob],
        *,
        include_quantities: bool = True,
        force: bool = False,
        fail_fast: bool = False,
    ) -> dict:
        counters = {"planned": len(jobs), "fetched": 0, "cached": 0, "empty": 0, "failed": 0, "rows": 0}
        errors: list[dict] = []

        commodities = {int(r["commodity_id"]): r for r in self.source.list_commodities()}
        geographies = self.source.list_geographies()
        states: dict[int, dict] = {}
        districts: dict[tuple[int, int], dict] = {}
        for r in geographies:
            sid = int(r["census_state_id"]); did = int(r["census_district_id"])
            states.setdefault(sid, {"census_state_id": sid, "census_state_name": r["census_state_name"]})
            districts[(sid, did)] = r

        for i, job in enumerate(jobs, start=1):
            csv_path, meta_path = self._job_paths(job)
            if meta_path.exists() and csv_path.exists() and not force:
                counters["cached"] += 1
                continue
            try:
                frame = self.source.canonical_market_chunk(
                    commodities[job.commodity_id],
                    states[job.state_id],
                    districts[(job.state_id, job.district_id)],
                    job.start_date,
                    job.end_date,
                    include_quantities=include_quantities,
                )
                if frame.empty:
                    frame = pd.DataFrame(columns=[
                        "date","state","district","market","commodity","variety","grade",
                        "min_price","max_price","modal_price","arrivals","source","data_mode",
                        "source_commodity_id","source_state_id","source_district_id","source_market_id",
                    ])
                    counters["empty"] += 1
                frame.to_csv(csv_path, index=False)
                metadata = {
                    "job": asdict(job),
                    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                    "row_count": int(len(frame)),
                    "include_quantities": include_quantities,
                    "source": "CEDA_AGMARKNET",
                }
                meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                counters["fetched"] += 1
                counters["rows"] += int(len(frame))
            except Exception as exc:  # retained in an explicit error ledger
                counters["failed"] += 1
                errors.append({"job": asdict(job), "error": f"{type(exc).__name__}: {exc}"})
                if fail_fast:
                    raise

        summary = {
            **counters,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "errors": errors,
        }
        (self.chunk_dir / "_last_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if errors:
            with (self.chunk_dir / "_errors.jsonl").open("a", encoding="utf-8") as fh:
                for row in errors:
                    fh.write(json.dumps({"recorded_at_utc": datetime.now(timezone.utc).isoformat(), **row}) + "\n")
        return summary

    def rebuild_processed(self) -> tuple[pd.DataFrame, Path]:
        files = sorted(p for p in self.chunk_dir.rglob("*.csv") if p.is_file())
        frames: list[pd.DataFrame] = []
        for path in files:
            try:
                f = pd.read_csv(path)
            except pd.errors.EmptyDataError:
                continue
            if not f.empty:
                frames.append(f)
        if not frames:
            raise RuntimeError("No non-empty CEDA chunk files are available to rebuild the panel")
        raw = pd.concat(frames, ignore_index=True)
        normalized = normalize_prices(raw)
        daily = aggregate_market_daily(normalized)
        out = self.processed_dir / "market_daily.csv"
        daily.to_csv(out, index=False)
        return daily, out
