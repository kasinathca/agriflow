from __future__ import annotations

import re
import unicodedata
import pandas as pd


def slug(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def make_market_id(state: object, district: object, market: object) -> str:
    """Stable pan-India market identifier.

    Market names are not assumed globally unique. The district component is retained
    even when blank so the ID is deterministic and auditable from source columns.
    """
    return f"{slug(state)}__{slug(district)}__{slug(market)}"


def ensure_market_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "market_id" not in out.columns:
        if "market" not in out.columns:
            return out
        if "state" in out.columns:
            district = out["district"] if "district" in out.columns else pd.Series("", index=out.index)
            out["market_id"] = [make_market_id(s, d, m) for s, d, m in zip(out["state"], district, out["market"])]
        else:
            # Compatibility for analytic fixtures lacking geography. Real ingestion
            # always carries state/district and therefore uses the pan-India ID.
            out["market_id"] = out["market"].map(slug)
    else:
        missing = out["market_id"].isna() | out["market_id"].astype(str).str.strip().eq("")
        if missing.any() and {"state", "market"}.issubset(out.columns):
            district = out["district"] if "district" in out.columns else pd.Series("", index=out.index)
            generated = [make_market_id(s, d, m) for s, d, m in zip(out["state"], district, out["market"])]
            out.loc[missing, "market_id"] = pd.Series(generated, index=out.index).loc[missing]
    return out


def market_metadata(df: pd.DataFrame) -> pd.DataFrame:
    x = ensure_market_id(df)
    cols = [c for c in ["market_id", "state", "district", "market"] if c in x.columns]
    return x[cols].drop_duplicates("market_id") if "market_id" in x.columns else x[cols].drop_duplicates()
