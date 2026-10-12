from __future__ import annotations

from pathlib import Path
import pandas as pd

from agriflow.config import settings
from agriflow.data.demo import generate_demo
from agriflow.data.processing import normalize_prices, aggregate_market_daily
from agriflow.data.identity import ensure_market_id


class DataRepository:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or settings.data_dir
        self.processed_dir = self.base_dir / "processed"
        self.demo_dir = self.base_dir / "demo"

    def ensure_demo(self) -> None:
        required = [
            self.demo_dir / "demo_market_daily.csv",
            self.demo_dir / "demo_weather_daily.csv",
            self.demo_dir / "demo_markets.csv",
        ]
        if not all(p.exists() for p in required):
            generate_demo(self.demo_dir)

    def load_prices(self) -> pd.DataFrame:
        real = self.processed_dir / "market_daily.csv"
        if real.exists():
            df = normalize_prices(pd.read_csv(real))
            return aggregate_market_daily(df)
        self.ensure_demo()
        return aggregate_market_daily(normalize_prices(pd.read_csv(self.demo_dir / "demo_market_daily.csv")))

    def load_weather(self) -> pd.DataFrame:
        real = self.processed_dir / "weather_daily.csv"
        if real.exists():
            p = real
        elif self.data_mode() == "REAL":
            return pd.DataFrame(columns=[
                "date", "market_id", "state", "district", "market",
                "rainfall_mm", "temperature_c", "data_mode", "source",
            ])
        else:
            p = self.demo_dir / "demo_weather_daily.csv"
        if not p.exists():
            self.ensure_demo()
        df = pd.read_csv(p)
        df["date"] = pd.to_datetime(df["date"])
        return ensure_market_id(df)

    def load_markets(self) -> pd.DataFrame:
        real = self.processed_dir / "markets.csv"
        if real.exists():
            p = real
        elif self.data_mode() == "REAL":
            return pd.DataFrame(columns=[
                "market_id", "state", "district", "market", "lat", "lon",
                "data_mode", "source",
            ])
        else:
            p = self.demo_dir / "demo_markets.csv"
        if not p.exists():
            self.ensure_demo()
        return ensure_market_id(pd.read_csv(p))

    def data_mode(self) -> str:
        real = self.processed_dir / "market_daily.csv"
        if not real.exists():
            return "DEMO"
        try:
            modes = set(pd.read_csv(real, usecols=["data_mode"], nrows=5000)["data_mode"].astype(str).str.upper())
            return "DEMO" if modes and modes <= {"DEMO"} else "REAL"
        except Exception:
            return "REAL"
