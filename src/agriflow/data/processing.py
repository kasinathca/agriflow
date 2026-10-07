from __future__ import annotations

import numpy as np
import pandas as pd

from agriflow.data.names import canonical_state
from agriflow.data.identity import ensure_market_id
from agriflow.data.provenance import infer_source_tier

PRICE_COLUMNS = [
    "date", "state", "district", "market", "commodity", "variety", "grade",
    "min_price", "max_price", "modal_price", "arrivals", "source", "source_tier", "data_mode"
]


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {"arrival_date": "date", "arrival_quantity": "arrivals"}
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
    for col in ["state", "district", "market", "commodity", "variety", "grade", "source", "source_tier", "data_mode"]:
        if col not in out:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str).str.strip()
        if col == "state":
            out[col] = out[col].map(canonical_state)
    missing_tier = out["source_tier"].eq("")
    if missing_tier.any():
        out.loc[missing_tier, "source_tier"] = [
            infer_source_tier(src, mode)
            for src, mode in zip(out.loc[missing_tier, "source"], out.loc[missing_tier, "data_mode"])
        ]
    raw_dates = out["date"].astype(str).str.strip()
    slash = raw_dates.str.contains("/", regex=False)
    parsed = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
    parsed.loc[slash] = pd.to_datetime(raw_dates.loc[slash], errors="coerce", dayfirst=True)
    parsed.loc[~slash] = pd.to_datetime(raw_dates.loc[~slash], errors="coerce")
    out["date"] = parsed
    for col in ["min_price", "max_price", "modal_price", "arrivals"]:
        if col not in out:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["date", "state", "market", "commodity", "modal_price"])
    out = out[(out["modal_price"] > 0) & (out["modal_price"] < 1_000_000)]
    if "min_price" in out and "max_price" in out:
        invalid_order = (
            out["min_price"].notna() & out["max_price"].notna()
            & ((out["min_price"] > out["modal_price"]) | (out["modal_price"] > out["max_price"]))
        )
        out.loc[invalid_order, ["min_price", "max_price"]] = np.nan
    out["arrivals"] = out["arrivals"].where(out["arrivals"] >= 0)
    out = out.drop_duplicates(subset=["date", "state", "district", "market", "commodity", "variety", "grade"], keep="last")
    out = ensure_market_id(out)
    return out.sort_values(["commodity", "market_id", "date"]).reset_index(drop=True)


def aggregate_market_daily(df: pd.DataFrame) -> pd.DataFrame:
    """One comparable daily record per market/commodity using medians across variety/grade."""
    df = ensure_market_id(df)
    gcols = ["date", "state", "district", "market", "market_id", "commodity", "data_mode"]
    agg = df.groupby(gcols, as_index=False).agg(
        modal_price=("modal_price", "median"),
        min_price=("min_price", "median"),
        max_price=("max_price", "median"),
        arrivals=("arrivals", "sum"),
        varieties=("variety", "nunique"),
        source=("source", lambda s: ",".join(sorted(set(x for x in s if x)))),
        source_tier=("source_tier", lambda s: ",".join(sorted(set(x for x in s if x))))
    )
    return agg.sort_values(["commodity", "market_id", "date"]).reset_index(drop=True)


def quality_summary(df: pd.DataFrame) -> dict[str, float | int]:
    total = len(df)
    invalid_order = int(((df.min_price > df.modal_price) | (df.modal_price > df.max_price)).fillna(False).sum()) if total else 0
    dup_cols = [c for c in ["date", "market", "commodity", "variety", "grade"] if c in df.columns]
    return {
        "rows": total,
        "states": int(df.state.nunique()) if total and "state" in df else 0,
        "markets": int((df.market_id.nunique() if "market_id" in df else df.market.nunique())) if total and "market" in df else 0,
        "commodities": int(df.commodity.nunique()) if total and "commodity" in df else 0,
        "missing_arrivals_pct": round(float(df.arrivals.isna().mean() * 100), 2) if total and "arrivals" in df else 0.0,
        "invalid_price_order_rows": invalid_order,
        "duplicate_key_rows": int(df.duplicated(dup_cols).sum()) if total and dup_cols else 0,
        "source_tiers": ",".join(sorted(set(
            t for value in df.get("source_tier", pd.Series(dtype=str)).fillna("").astype(str)
            for t in value.split(",") if t
        ))) if total else "",
    }
