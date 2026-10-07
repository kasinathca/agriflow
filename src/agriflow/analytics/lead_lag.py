from __future__ import annotations
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from agriflow.data.identity import ensure_market_id


def _entity_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    x = df.copy()
    if {"state", "market"}.issubset(x.columns):
        x = ensure_market_id(x)
    key = "market_id" if "market_id" in x.columns else "market"
    return x, key


def market_returns(df: pd.DataFrame, commodity: str | None = None) -> pd.DataFrame:
    x, key = _entity_frame(df)
    if commodity is not None and "commodity" in x:
        x = x[x.commodity.eq(commodity)]
    cols = list(dict.fromkeys(["date", key, "market", "modal_price"]))
    for c in ["state", "district"]:
        if c in x.columns:
            cols.append(c)
    x = x[cols].dropna(subset=["date", key, "modal_price"])
    x["date"] = pd.to_datetime(x.date)
    x = x.sort_values([key, "date"])
    x["log_price"] = np.log(x.modal_price.astype(float))
    x["prev_date"] = x.groupby(key)["date"].shift(1)
    x["return"] = x.groupby(key)["log_price"].diff()
    # Only true daily moves: do not bridge reporting gaps.
    x.loc[(x.date - x.prev_date).dt.days.ne(1), "return"] = np.nan
    if key != "market_id":
        x["market_id"] = x[key].astype(str)
    keep = ["date", "market_id", "market", "return"] + [c for c in ["state", "district"] if c in x.columns]
    return x[keep].dropna(subset=["return"])


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    if not pvalues:
        return []
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    q = ranked * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    out = np.empty_like(q)
    out[order] = q
    return out.tolist()


def infer_lead_lag_edges(
    df: pd.DataFrame,
    commodity: str,
    max_lag: int = 7,
    min_overlap: int = 35,
    min_abs_corr: float = 0.30,
    fdr_alpha: float = 0.05,
    max_markets: int = 40,
) -> pd.DataFrame:
    """Infer candidate directed price-transmission edges from daily log returns.

    Identification is pan-India safe: internal graph nodes use `market_id`, not the
    display market name. The returned `leader`/`follower` fields remain human-readable.
    """
    r = market_returns(df, commodity)
    columns = [
        "leader_id", "follower_id", "leader", "follower", "lag_days",
        "corr", "p_value", "q_value", "overlap",
    ]
    if r.empty:
        return pd.DataFrame(columns=columns)
    meta = r[["market_id", "market"]].drop_duplicates("market_id").set_index("market_id")["market"].to_dict()
    counts = r.groupby("market_id").size().sort_values(ascending=False)
    keep = counts.head(max_markets).index.tolist()
    r = r[r.market_id.isin(keep)]
    pivot = r.pivot(index="date", columns="market_id", values="return")
    candidates: list[dict] = []
    for a, b in combinations(keep, 2):
        best = None
        # Positive lag means leader return at t is paired with follower return at t+lag.
        for leader, follower in ((a, b), (b, a)):
            for lag in range(1, max_lag + 1):
                z = pd.concat([
                    pivot[leader].rename("x"),
                    pivot[follower].shift(-lag).rename("y"),
                ], axis=1).dropna()
                if len(z) < min_overlap or z.x.std() == 0 or z.y.std() == 0:
                    continue
                corr, p = pearsonr(z.x, z.y)
                cand = {
                    "leader_id": leader,
                    "follower_id": follower,
                    "leader": meta.get(leader, leader),
                    "follower": meta.get(follower, follower),
                    "lag_days": lag,
                    "corr": float(corr),
                    "p_value": float(p),
                    "overlap": len(z),
                }
                if best is None or abs(cand["corr"]) > abs(best["corr"]):
                    best = cand
        if best is not None:
            candidates.append(best)
    if not candidates:
        return pd.DataFrame(columns=columns)
    qvals = benjamini_hochberg([c["p_value"] for c in candidates])
    for c, q in zip(candidates, qvals):
        c["q_value"] = q
    out = pd.DataFrame(candidates)
    out = out[(out["corr"].abs() >= min_abs_corr) & (out["q_value"] <= fdr_alpha)]
    return out[columns].sort_values(["q_value", "corr"], ascending=[True, False]).reset_index(drop=True)
