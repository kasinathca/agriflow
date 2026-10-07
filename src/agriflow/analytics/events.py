from __future__ import annotations
import numpy as np
import pandas as pd

from agriflow.analytics.weather import robust_z
from agriflow.analytics.lead_lag import market_returns
from agriflow.data.identity import ensure_market_id


def detect_market_crunches(df: pd.DataFrame, arrival_threshold: float = -1.5, price_threshold: float = 1.5) -> pd.DataFrame:
    x = ensure_market_id(df).copy().sort_values(["commodity", "market_id", "date"])
    x["arrival_z"] = x.groupby(["commodity", "market_id"])["arrivals"].transform(robust_z)
    x["price_z"] = x.groupby(["commodity", "market_id"])["modal_price"].transform(robust_z)
    out = x[(x.arrival_z <= arrival_threshold) & (x.price_z >= price_threshold)].copy()
    out["crunch_severity"] = np.sqrt(out.price_z.clip(lower=0) ** 2 + (-out.arrival_z.clip(upper=0)) ** 2)
    cols = [c for c in [
        "date", "market_id", "state", "district", "market", "commodity", "modal_price", "arrivals",
        "arrival_z", "price_z", "crunch_severity",
    ] if c in out.columns]
    return out[cols].sort_values(["crunch_severity", "price_z"], ascending=[False, False]).reset_index(drop=True)


def detect_price_shocks(df: pd.DataFrame, commodity: str, z_threshold: float = 2.0) -> pd.DataFrame:
    """Flag unusually large true daily market price returns for ripple exploration."""
    r = market_returns(df, commodity)
    if r.empty:
        return pd.DataFrame()
    r["return_z"] = r.groupby("market_id")["return"].transform(robust_z)
    r["return_pct"] = (np.exp(r["return"]) - 1) * 100
    out = r[r.return_z.abs() >= z_threshold].copy()
    return out.sort_values("return_z", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def ripple_snapshot(
    df: pd.DataFrame,
    edges: pd.DataFrame,
    commodity: str,
    leader_id: str,
    event_date: str | pd.Timestamp,
    max_horizon: int,
) -> pd.DataFrame:
    """Observed edge-aligned follower responses to a leader shock.

    For an inferred edge A→B with lag L, the follower response is B's *daily return*
    on event_date + L. This is visually faithful to the lead–lag statistic itself and
    avoids implying that a cumulative price change proves causal propagation.
    """
    if edges.empty or not leader_id or not event_date:
        return pd.DataFrame()
    r = market_returns(df, commodity)
    if r.empty:
        return pd.DataFrame()
    d0 = pd.Timestamp(event_date)
    lookup = r.set_index(["market_id", "date"])
    sub = edges[(edges.get("leader_id", edges["leader"]) == leader_id) & (edges.lag_days <= int(max_horizon))]
    rows = []
    leader_key = (leader_id, d0)
    leader_return = None
    if leader_key in lookup.index:
        lr = lookup.loc[leader_key]
        if isinstance(lr, pd.DataFrame): lr = lr.iloc[0]
        leader_return = float((np.exp(lr["return"]) - 1) * 100)
    for _, e in sub.iterrows():
        follower_id = e.get("follower_id", e["follower"])
        response_date = d0 + pd.Timedelta(days=int(e.lag_days))
        key = (follower_id, response_date)
        if key not in lookup.index:
            continue
        fr = lookup.loc[key]
        if isinstance(fr, pd.DataFrame): fr = fr.iloc[0]
        rows.append({
            "leader_id": leader_id,
            "leader": e.leader,
            "follower_id": follower_id,
            "follower": e.follower,
            "event_date": d0,
            "response_date": response_date,
            "lag_days": int(e.lag_days),
            "edge_corr": float(e["corr"]),
            "edge_q_value": float(e.q_value),
            "leader_shock_pct": leader_return,
            "follower_response_pct": float((np.exp(fr["return"]) - 1) * 100),
        })
    return pd.DataFrame(rows)
