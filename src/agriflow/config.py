from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    data_dir: Path = ROOT / "data"
    demo_dir: Path = ROOT / "data" / "demo"
    raw_dir: Path = ROOT / "data" / "raw"
    processed_dir: Path = ROOT / "data" / "processed"
    cache_dir: Path = ROOT / "data" / "cache"
    output_dir: Path = ROOT / "outputs"
    assets_dir: Path = ROOT / "assets"

    data_gov_api_key: str = os.getenv("DATA_GOV_API_KEY", "").strip()
    ceda_api_key: str = (os.getenv("CEDA_API_KEY", "") or os.getenv("CEDA_API_TOKEN", "")).strip()
    host: str = os.getenv("AGRIFLOW_HOST", "127.0.0.1")
    port: int = int(os.getenv("AGRIFLOW_PORT", "8050"))
    debug: bool = os.getenv("AGRIFLOW_DEBUG", "0") == "1"

    max_lag_days: int = int(os.getenv("AGRIFLOW_MAX_LAG_DAYS", "7"))
    min_overlap_days: int = int(os.getenv("AGRIFLOW_MIN_OVERLAP_DAYS", "35"))
    min_edge_corr: float = float(os.getenv("AGRIFLOW_MIN_EDGE_CORR", "0.30"))
    fdr_alpha: float = float(os.getenv("AGRIFLOW_FDR_ALPHA", "0.05"))
    max_network_markets: int = int(os.getenv("AGRIFLOW_MAX_NETWORK_MARKETS", "40"))


settings = Settings()
