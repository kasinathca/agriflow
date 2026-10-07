from __future__ import annotations

"""Temporal robustness diagnostics for inferred market leadership."""

import numpy as np
import pandas as pd

from agriflow.analytics.lead_lag import infer_lead_lag_edges
from agriflow.analytics.network import influence_scores


def yearly_edge_stability(
    df: pd.DataFrame,
    commodity: str,
    *,
    max_lag: int = 7,
    min_overlap: int = 35,
    min_abs_corr: float = 0.30,
    fdr_alpha: float = 0.05,
    max_markets: int = 40,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Re-estimate the network independently by calendar year.

    The aggregate persistence ratio is descriptive: it is the fraction of evaluable
    years in which the same directed edge passed the full edge-selection criteria.
    """
    x = df[df["commodity"].eq(commodity)].copy()
    if x.empty:
        return pd.DataFrame(), pd.DataFrame()
    x["date"] = pd.to_datetime(x["date"])
    yearly: list[pd.DataFrame] = []
    evaluated_years: list[int] = []
    for year, y in x.groupby(x["date"].dt.year):
        # A year is considered evaluable only if at least two markets have enough
        # observations to meet the overlap criterion in principle.
        counts = y.groupby("market_id" if "market_id" in y else "market").size()
        if int((counts >= min_overlap + 1).sum()) < 2:
            continue
        evaluated_years.append(int(year))
        e = infer_lead_lag_edges(
            y, commodity, max_lag, min_overlap, min_abs_corr, fdr_alpha, max_markets
        )
        if not e.empty:
            e = e.copy()
            e["year"] = int(year)
            yearly.append(e)
    all_yearly = pd.concat(yearly, ignore_index=True) if yearly else pd.DataFrame(columns=[
        "leader_id","follower_id","leader","follower","lag_days","corr","p_value","q_value","overlap","year"
    ])
    cols = [
        "leader_id","follower_id","leader","follower","years_evaluated","years_supported",
        "persistence_ratio","median_corr","median_abs_corr","median_lag_days","median_overlap"
    ]
    if all_yearly.empty:
        return all_yearly, pd.DataFrame(columns=cols)
    total = len(evaluated_years)
    agg = all_yearly.groupby(["leader_id","follower_id","leader","follower"], as_index=False).agg(
        years_supported=("year","nunique"),
        median_corr=("corr","median"),
        median_abs_corr=("corr",lambda s: float(np.median(np.abs(s)))),
        median_lag_days=("lag_days","median"),
        median_overlap=("overlap","median"),
    )
    agg["years_evaluated"] = total
    agg["persistence_ratio"] = agg["years_supported"] / max(total, 1)
    agg = agg[cols].sort_values(["persistence_ratio","median_abs_corr"], ascending=[False,False]).reset_index(drop=True)
    return all_yearly, agg


def yearly_leader_stability(
    yearly_edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarise year-by-year source-oriented influence ranks."""
    cols = ["year","market_id","market","influence_score","rank","outbound_edges"]
    if yearly_edges.empty:
        return pd.DataFrame(columns=cols), pd.DataFrame(columns=[
            "market_id","market","years_present","mean_rank","median_rank","mean_influence","median_influence","top3_years"
        ])
    frames=[]
    for year,e in yearly_edges.groupby("year"):
        s=influence_scores(e)
        if s.empty:
            continue
        s=s.copy(); s["year"]=int(year); s["rank"]=np.arange(1,len(s)+1)
        frames.append(s[["year","market_id","market","influence_score","rank","outbound_edges"]])
    annual=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=cols)
    if annual.empty:
        return annual, pd.DataFrame(columns=[
            "market_id","market","years_present","mean_rank","median_rank","mean_influence","median_influence","top3_years"
        ])
    summary=annual.groupby(["market_id","market"],as_index=False).agg(
        years_present=("year","nunique"),
        mean_rank=("rank","mean"),
        median_rank=("rank","median"),
        mean_influence=("influence_score","mean"),
        median_influence=("influence_score","median"),
        top3_years=("rank",lambda s:int((s<=3).sum())),
    )
    return annual, summary.sort_values(["top3_years","mean_rank","mean_influence"],ascending=[False,True,False]).reset_index(drop=True)
