from __future__ import annotations
import numpy as np
import pandas as pd

from agriflow.data.identity import ensure_market_id


def robust_z(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    med = s.median()
    mad = (s - med).abs().median()
    if pd.isna(mad) or mad == 0:
        sd = s.std(ddof=0)
        return (s - med) / sd if sd and not pd.isna(sd) else pd.Series(np.zeros(len(s)), index=s.index)
    return 0.67448975 * (s - med) / mad


def weather_anomalies(weather: pd.DataFrame) -> pd.DataFrame:
    """Compute within-location, within-calendar-month robust anomalies.

    This controls broad seasonality without pretending NASA POWER values are local
    station observations. Multi-year history is preferred; the anomaly sample count is
    retained so short climatologies can be identified in outputs.
    """
    w = ensure_market_id(weather)
    w["date"] = pd.to_datetime(w.date)
    w["month"] = w.date.dt.month
    group_cols = ["market_id"] if "market_id" in w.columns else (["market"] if "market" in w.columns else ["state"])
    base_cols = group_cols + ["month"]
    if "rainfall_mm" in w:
        w["rainfall_anomaly_z"] = w.groupby(base_cols, dropna=False)["rainfall_mm"].transform(robust_z)
    if "temperature_c" in w:
        w["temperature_anomaly_z"] = w.groupby(base_cols, dropna=False)["temperature_c"].transform(robust_z)
    w["climatology_n"] = w.groupby(base_cols, dropna=False)["date"].transform("size")
    return w.drop(columns="month")


def join_market_weather(prices: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    p = ensure_market_id(prices)
    w = weather_anomalies(weather)
    p["date"] = pd.to_datetime(p.date)
    w["date"] = pd.to_datetime(w.date)
    keys = ["date", "market"]
    if "market_id" in p.columns and "market_id" in w.columns:
        overlap = len(set(p.market_id.dropna()) & set(w.market_id.dropna()))
        denom = max(1, min(p.market_id.nunique(), w.market_id.nunique()))
        if overlap / denom >= 0.5:
            keys = ["date", "market_id"]
        else:
            # Compatibility fallback only when display names are globally unique in both
            # frames; never collapse duplicate market names in real pan-India panels.
            p_unique = p.groupby("market").market_id.nunique().max() <= 1
            w_unique = w.groupby("market").market_id.nunique().max() <= 1
            if not (p_unique and w_unique):
                keys = ["date", "market_id"]
    cols = keys + [c for c in [
        "rainfall_mm", "temperature_c", "temperature_max_c", "temperature_min_c",
        "rainfall_anomaly_z", "temperature_anomaly_z", "climatology_n",
    ] if c in w.columns]
    return p.merge(w[cols].drop_duplicates(keys), on=keys, how="left")


def _decluster_events(events: pd.DataFrame, key: str, weather_col: str, separation_days: int) -> pd.DataFrame:
    chosen = []
    for _, g in events.sort_values([key, "date"]).groupby(key):
        cluster = []
        prev = None
        for idx, row in g.iterrows():
            if prev is None or (row.date - prev).days <= separation_days:
                cluster.append(idx)
            else:
                chosen.append(g.loc[cluster, weather_col].abs().idxmax())
                cluster = [idx]
            prev = row.date
        if cluster:
            chosen.append(g.loc[cluster, weather_col].abs().idxmax())
    return events.loc[chosen].sort_values([key, "date"]) if chosen else events.iloc[0:0]


def event_study(
    joined: pd.DataFrame,
    weather_col: str = "rainfall_anomaly_z",
    threshold: float = 2.0,
    horizons: tuple[int, ...] = (1, 3, 7, 14),
    separation_days: int = 2,
    observation_tolerance_days: int = 2,
) -> pd.DataFrame:
    """Descriptive weather-event response study with declustered extreme events.

    Responses are measured against the latest observed market record immediately before
    the event. A future response may use the first reporting date up to `tolerance` days
    after the target horizon, preventing an arbitrary missing market day from discarding
    an otherwise usable event. Results are associations, not causal estimates.
    """
    x = ensure_market_id(joined).copy()
    if weather_col not in x.columns or x.empty:
        return pd.DataFrame()
    x["date"] = pd.to_datetime(x.date)
    x = x.sort_values(["market_id", "date"])
    events = x[x[weather_col].abs() >= threshold].copy()
    if events.empty:
        return pd.DataFrame()
    events = _decluster_events(events, "market_id", weather_col, separation_days)
    rows = []
    groups = {k: g.set_index("date").sort_index() for k, g in x.groupby("market_id")}
    for _, e in events.iterrows():
        g = groups[e.market_id]
        before = g[g.index < e.date].tail(1)
        if before.empty:
            continue
        b = before.iloc[0]
        base_date = before.index[-1]
        for h in horizons:
            target = pd.Timestamp(e.date) + pd.Timedelta(days=h)
            future = g[(g.index >= target) & (g.index <= target + pd.Timedelta(days=observation_tolerance_days))].head(1)
            if future.empty:
                continue
            f = future.iloc[0]
            rows.append({
                "market_id": e.market_id,
                "market": e.get("market", e.market_id),
                "state": e.get("state", ""),
                "commodity": e.get("commodity", ""),
                "event_date": e.date,
                "baseline_date": base_date,
                "response_date": future.index[0],
                "horizon_days": h,
                "weather_z": float(e[weather_col]),
                "event_sign": "positive" if float(e[weather_col]) > 0 else "negative",
                "price_change_pct": (float(f.modal_price) / float(b.modal_price) - 1) * 100 if b.modal_price else np.nan,
                "arrival_change_pct": (float(f.arrivals) / float(b.arrivals) - 1) * 100 if pd.notna(b.get("arrivals")) and b.arrivals else np.nan,
            })
    return pd.DataFrame(rows)


def event_study_summary(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["event_sign", "horizon_days", "n", "median_price_change_pct", "median_arrival_change_pct"])
    return events.groupby(["event_sign", "horizon_days"], as_index=False).agg(
        n=("price_change_pct", "count"),
        median_price_change_pct=("price_change_pct", "median"),
        median_arrival_change_pct=("arrival_change_pct", "median"),
    )
