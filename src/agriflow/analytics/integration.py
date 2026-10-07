from __future__ import annotations
from itertools import combinations
import numpy as np
import pandas as pd

from agriflow.analytics.lead_lag import market_returns
from agriflow.data.identity import ensure_market_id


def market_integration_pairs(df: pd.DataFrame, commodity: str, edges: pd.DataFrame | None = None, min_overlap: int = 35) -> pd.DataFrame:
    x = df[df.commodity.eq(commodity)].copy()
    if x.empty:
        return pd.DataFrame()
    x = ensure_market_id(x)
    x["date"] = pd.to_datetime(x.date)
    meta = x[["market_id", "market", "state", "district"]].drop_duplicates("market_id").set_index("market_id")
    price = x.pivot_table(index="date", columns="market_id", values="modal_price", aggfunc="median")
    ret = market_returns(x, commodity).pivot(index="date", columns="market_id", values="return")
    strength = {}
    if edges is not None and not edges.empty:
        for _, e in edges.iterrows():
            a = e.get("leader_id", e["leader"])
            b = e.get("follower_id", e["follower"])
            key = tuple(sorted((a, b)))
            strength[key] = max(strength.get(key, 0.0), abs(float(e["corr"])))
    rows = []
    for a, b in combinations(price.columns, 2):
        shared = price[[a, b]].dropna()
        rr = ret[[a, b]].dropna() if a in ret.columns and b in ret.columns else pd.DataFrame()
        if len(shared) < min_overlap or len(rr) < min_overlap:
            continue
        corr = float(rr[a].corr(rr[b]))
        gap = float(np.median(np.abs(np.log(shared[a] / shared[b]))))
        denom = max(1, min(price[a].notna().sum(), price[b].notna().sum()))
        overlap = min(1.0, len(shared) / denom)
        similarity = float(np.clip((corr + 1) / 2, 0, 1))
        gap_score = float(np.exp(-gap / 0.25))
        trans = float(strength.get(tuple(sorted((a, b))), 0.0))
        score = 0.40 * similarity + 0.30 * gap_score + 0.20 * overlap + 0.10 * trans
        ma, mb = meta.loc[a], meta.loc[b]
        rows.append({
            "market_a_id": a,
            "market_b_id": b,
            "market_a": ma.market,
            "market_b": mb.market,
            "state_a": ma.state,
            "state_b": mb.state,
            "return_corr": corr,
            "median_abs_log_price_gap": gap,
            "shared_date_fraction": overlap,
            "transmission_strength": trans,
            "integration_score": score,
        })
    return pd.DataFrame(rows).sort_values("integration_score", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
