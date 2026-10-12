from __future__ import annotations

import json
import shutil

import pandas as pd

from agriflow.config import settings
from agriflow.visualization.figures import (
    arrivals_price_scatter,
    price_trend,
    state_map,
)

ROOT = settings.root
DEST = ROOT / "deliverables" / "final_review"


def _write_csv(frame: pd.DataFrame, relative: str) -> None:
    path = DEST / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def main() -> None:
    prices = pd.read_csv(settings.processed_dir / "market_daily.csv")
    prices["date"] = pd.to_datetime(prices["date"])
    markets = pd.read_csv(settings.processed_dir / "markets.csv")
    chunk_files = sorted((settings.raw_dir / "ceda_chunks").rglob("*.csv"))
    raw = pd.concat((pd.read_csv(path) for path in chunk_files), ignore_index=True)

    date_min = prices.date.min().date().isoformat()
    date_max = prices.date.max().date().isoformat()
    coordinate_coverage = float(
        markets[["lat", "lon"]].notna().all(axis=1).mean()
    ) if len(markets) and {"lat", "lon"}.issubset(markets.columns) else 0.0
    arrival_coverage = float(prices.arrivals.notna().mean())

    statistics = pd.DataFrame([
        ("raw_checkpoint_files", len(chunk_files)),
        ("raw_rows", len(raw)),
        ("processed_market_day_rows", len(prices)),
        ("states", prices.state.nunique()),
        ("districts", prices.district.nunique()),
        ("markets", prices.market_id.nunique()),
        ("commodities", prices.commodity.nunique()),
        ("date_min", date_min),
        ("date_max", date_max),
        ("arrival_coverage", round(arrival_coverage, 6)),
        ("coordinate_coverage", round(coordinate_coverage, 6)),
        ("weather_rows", 0),
    ], columns=["metric", "value"])
    _write_csv(statistics, "01_dataset/dataset_statistics.csv")

    state = prices.groupby(["state", "commodity"], as_index=False).agg(
        observations=("modal_price", "size"), markets=("market_id", "nunique"),
        districts=("district", "nunique"), active_days=("date", "nunique"),
        first_date=("date", "min"), last_date=("date", "max"),
        arrival_coverage=("arrivals", lambda s: s.notna().mean()),
    )
    span = (state.last_date - state.first_date).dt.days + 1
    state["reporting_density"] = state.observations / (span * state.markets.clip(lower=1))
    _write_csv(state, "01_dataset/state_coverage.csv")

    market = prices.groupby(["state", "district", "market", "market_id"], as_index=False).agg(
        observations=("modal_price", "size"), first_date=("date", "min"),
        last_date=("date", "max"), arrival_coverage=("arrivals", lambda s: s.notna().mean()),
    )
    _write_csv(market, "01_dataset/market_coverage.csv")

    monthly = prices.assign(month=prices.date.dt.to_period("M").astype(str)).groupby(
        ["month", "commodity"], as_index=False
    ).agg(observations=("modal_price", "size"), markets=("market_id", "nunique"))
    _write_csv(monthly, "01_dataset/date_coverage.csv")

    missing = pd.DataFrame([
        {"field": column, "missing_rows": int(prices[column].isna().sum()),
         "missing_pct": round(float(prices[column].isna().mean() * 100), 4)}
        for column in ["min_price", "modal_price", "max_price", "arrivals", "arrival_unit"]
    ])
    _write_csv(missing, "01_dataset/missingness_summary.csv")

    raw_keys = ["date", "state", "district", "market", "commodity", "variety", "grade"]
    processed_keys = ["date", "market_id", "commodity"]
    before_after = pd.DataFrame([
        ("rows", len(raw), len(prices)),
        ("duplicate_keys", int(raw.duplicated(raw_keys).sum()), int(prices.duplicated(processed_keys).sum())),
        ("missing_modal_price", int(raw.modal_price.isna().sum()), int(prices.modal_price.isna().sum())),
        ("missing_arrivals", int(raw.arrivals.isna().sum()), int(prices.arrivals.isna().sum())),
        ("invalid_price_order", int(((raw.min_price > raw.modal_price) | (raw.modal_price > raw.max_price)).fillna(False).sum()), int(((prices.min_price > prices.modal_price) | (prices.modal_price > prices.max_price)).fillna(False).sum())),
    ], columns=["metric", "raw", "processed"])
    _write_csv(before_after, "02_preprocessing/data_quality_before_after.csv")

    results_dir = DEST / "04_results"
    evaluation_dir = DEST / "07_evaluation"
    results_dir.mkdir(parents=True, exist_ok=True)
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    for name in ["lead_lag_onion.csv", "influence_onion.csv", "integration_onion.csv", "market_crunch_candidates.csv"]:
        shutil.copy2(settings.output_dir / name, results_dir / name)
    for name in ["coverage_audit.csv", "commodity_scope_selection.csv", "empirical_readiness.csv"]:
        shutil.copy2(settings.output_dir / name, evaluation_dir / name)

    figures_dir = DEST / "05_figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    figures = {
        "real_onion_price_trend.html": price_trend(prices, "Onion", "All India"),
        "real_onion_arrivals_price.html": arrivals_price_scatter(prices, "Onion", "All India"),
        "real_onion_india_map.html": state_map(prices, markets, "Onion", settings.cache_dir / "india_states.geojson"),
    }
    for name, figure in figures.items():
        figure.write_html(figures_dir / name, include_plotlyjs="cdn", full_html=True)

    manifest = {
        "project_version": "1.4.3",
        "generated_on": "2026-10-13",
        "release_ref": "v1.4.3",
        "data_mode": "REAL",
        "source_tiers": sorted(prices.source_tier.dropna().unique().tolist()),
        "source": "CEDA_AGMARKNET",
        "empirical_readiness_status": "READY_WITH_WARNINGS",
        "real_observation_count": len(prices),
        "real_market_count": int(prices.market_id.nunique()),
        "real_district_count": int(prices.district.nunique()),
        "real_state_count": int(prices.state.nunique()),
        "date_range": [date_min, date_max],
        "arrival_coverage": round(arrival_coverage, 6),
        "arrival_unit": "UNKNOWN",
        "coordinate_coverage": round(coordinate_coverage, 6),
        "weather_market_coverage": 0.0,
        "full_maharashtra_download_complete": False,
        "final_freeze_identifier": None,
        "important_result_files": sorted(path.name for path in results_dir.glob("*.csv")),
        "figure_files": sorted(path.name for path in figures_dir.glob("*.html")),
        "screenshot_files": sorted(path.name for path in (DEST / "06_dashboard_screenshots").glob("*.png")),
        "academic_integrity": "REAL CEDA/AGMARKNET evidence only. State breadth, coordinates, weather, full-state ingestion and final freeze remain incomplete.",
    }
    manifest_path = DEST / "manifest" / "final_review_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Updated REAL final-review evidence in {DEST}")


if __name__ == "__main__":
    main()
