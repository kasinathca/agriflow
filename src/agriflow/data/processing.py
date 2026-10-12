from __future__ import annotations

import numpy as np
import pandas as pd

from agriflow.data.identity import ensure_market_id
from agriflow.data.names import canonical_state
from agriflow.data.provenance import infer_source_tier

PRICE_COLUMNS = [
    "date", "state", "district", "market", "commodity", "variety", "grade",
    "min_price", "max_price", "modal_price", "arrivals", "arrival_unit",
    "source", "source_tier", "data_mode"
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
    if "arrival_unit" not in out:
        out["arrival_unit"] = "UNKNOWN"
    out["arrival_unit"] = (
        out["arrival_unit"].fillna("").astype(str).str.strip().replace("", "UNKNOWN")
    )
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
    """One comparable daily record per market/commodity.

    Prices use medians across variety/grade rows. Repeated identical arrival
    quantities are counted once because source APIs commonly attach a market-day
    total to every price row. Distinct quantities are summed only when their unit
    label is consistent; mixed/unknown unit combinations are left unavailable.
    """
    df = ensure_market_id(df)
    if "arrival_unit" not in df:
        df["arrival_unit"] = "UNKNOWN"
    df["arrival_unit"] = (
        df["arrival_unit"].fillna("").astype(str).str.strip().replace("", "UNKNOWN")
    )
    gcols = ["date", "state", "district", "market", "market_id", "commodity", "data_mode"]
    agg = df.groupby(gcols, as_index=False).agg(
        modal_price=("modal_price", "median"),
        min_price=("min_price", "median"),
        max_price=("max_price", "median"),
        varieties=("variety", "nunique"),
        source=("source", lambda s: ",".join(sorted({x for x in s if x}))),
        source_tier=("source_tier", lambda s: ",".join(sorted({x for x in s if x})))
    )
    arrival_rows = []
    for key, group in df.groupby(gcols, sort=False, dropna=False):
        units = sorted(set(group["arrival_unit"]))
        values = group["arrivals"].dropna()
        if len(units) > 1:
            total = np.nan
            unit = "MIXED:" + "|".join(units)
        elif values.empty:
            total = np.nan
            unit = units[0] if units else "UNKNOWN"
        elif values.nunique() == 1:
            total = float(values.iloc[0])
            unit = units[0] if units else "UNKNOWN"
        else:
            total = float(values.sum())
            unit = units[0] if units else "UNKNOWN"
        arrival_rows.append(dict(zip(gcols, key), arrivals=total, arrival_unit=unit))
    agg = agg.merge(pd.DataFrame(arrival_rows), on=gcols, how="left")
    return agg.sort_values(["commodity", "market_id", "date"]).reset_index(drop=True)


def merge_market_daily(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    """Append compatible market-day panels with deterministic authority-aware deduplication."""
    if existing.empty:
        return incoming.copy().reset_index(drop=True)
    if incoming.empty:
        return existing.copy().reset_index(drop=True)
    combined = pd.concat(
        [existing.assign(_incoming=0), incoming.assign(_incoming=1)],
        ignore_index=True,
        sort=False,
    )
    combined = ensure_market_id(combined)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    tier_rank = {
        "DEMO": 0,
        "UNKNOWN": 1,
        "USER_SUPPLIED": 2,
        "SECONDARY_MIRROR": 3,
        "CURATED_OFFICIAL_DERIVED": 4,
        "PRIMARY_OFFICIAL": 5,
    }
    tiers = combined["source_tier"] if "source_tier" in combined else pd.Series("", index=combined.index)
    combined["_authority"] = tiers.fillna("").astype(str).map(
        lambda value: max((tier_rank.get(part.strip(), 1) for part in value.split(",")), default=1)
    )
    keys = ["date", "market_id", "commodity"]
    combined = combined.sort_values(keys + ["_authority", "_incoming"], kind="stable")
    combined = combined.drop_duplicates(keys, keep="last")
    return combined.drop(columns=["_incoming", "_authority"]).sort_values(keys).reset_index(drop=True)


def quality_summary(df: pd.DataFrame) -> dict[str, float | int]:
    total = len(df)
    invalid_order = int(((df.min_price > df.modal_price) | (df.modal_price > df.max_price)).fillna(False).sum()) if total else 0
    dup_cols = [c for c in ["date", "market", "commodity", "variety", "grade"] if c in df.columns]
    return {
        "rows": total,
        "states": int(df.state.nunique()) if total and "state" in df else 0,
        "markets": int(df.market_id.nunique() if "market_id" in df else df.market.nunique()) if total and "market" in df else 0,
        "commodities": int(df.commodity.nunique()) if total and "commodity" in df else 0,
        "missing_arrivals_pct": round(float(df.arrivals.isna().mean() * 100), 2) if total and "arrivals" in df else 0.0,
        "invalid_price_order_rows": invalid_order,
        "duplicate_key_rows": int(df.duplicated(dup_cols).sum()) if total and dup_cols else 0,
        "source_tiers": ",".join(sorted({
            t for value in df.get("source_tier", pd.Series(dtype=str)).fillna("").astype(str)
            for t in value.split(",") if t
        })) if total else "",
    }
