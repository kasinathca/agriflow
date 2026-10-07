from __future__ import annotations
import pandas as pd

from agriflow.data.identity import ensure_market_id


def coverage_audit(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["state","commodity","observations","markets","active_days","first_date","last_date","reporting_density","arrival_availability"])
    x = ensure_market_id(df)
    x["date"] = pd.to_datetime(x["date"])
    grp = x.groupby(["state", "commodity"])
    out = grp.agg(
        observations=("modal_price", "size"),
        markets=("market_id", "nunique"),
        active_days=("date", "nunique"),
        first_date=("date", "min"),
        last_date=("date", "max"),
        arrival_nonmissing=("arrivals", lambda s: s.notna().sum()),
    ).reset_index()
    span = (out["last_date"] - out["first_date"]).dt.days.add(1).clip(lower=1)
    possible_market_days = (span * out["markets"].clip(lower=1)).clip(lower=1)
    out["reporting_density"] = (out["observations"] / possible_market_days).clip(upper=1)
    out["arrival_availability"] = out["arrival_nonmissing"] / out["observations"].clip(lower=1)
    return out.drop(columns="arrival_nonmissing").sort_values(["state", "commodity"]).reset_index(drop=True)


def commodity_coverage_score(audit: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame(columns=["commodity","states","markets","observations","density","arrival_availability","coverage_score"])
    c = audit.groupby("commodity", as_index=False).agg(
        states=("state", "nunique"),
        markets=("markets", "sum"),
        observations=("observations", "sum"),
        density=("reporting_density", "mean"),
        arrival_availability=("arrival_availability", "mean"),
    )
    for col in ["states", "markets", "observations"]:
        mx = c[col].max() or 1
        c[f"_{col}"] = c[col] / mx
    c["coverage_score"] = (
        0.35*c["_states"] + 0.20*c["_markets"] + 0.20*c["_observations"] +
        0.15*c["density"] + 0.10*c["arrival_availability"]
    )
    return c.drop(columns=["_states","_markets","_observations"]).sort_values("coverage_score", ascending=False)
