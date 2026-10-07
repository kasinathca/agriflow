from __future__ import annotations
from itertools import combinations
import math
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from agriflow.analytics.lead_lag import market_returns
from agriflow.data.identity import ensure_market_id


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_similarity(df: pd.DataFrame, markets: pd.DataFrame, commodity: str, min_overlap: int = 35) -> pd.DataFrame:
    r = market_returns(df, commodity)
    if r.empty:
        return pd.DataFrame()
    pivot = r.pivot(index="date", columns="market_id", values="return")
    m = ensure_market_id(markets).dropna(subset=["lat", "lon"]).copy()
    coords = m.drop_duplicates("market_id").set_index("market_id")
    names = [mid for mid in pivot.columns if mid in coords.index]
    if not names and "market" in m.columns and m.market.nunique() == len(m.drop_duplicates("market")):
        # Compatibility for coordinate fixtures that only provide display market names.
        # Real project market tables carry the pan-India market_id directly.
        price_meta = r[["market_id", "market"]].drop_duplicates("market_id")
        by_name = m.drop_duplicates("market").set_index("market")
        rows=[]
        for _, mr in price_meta.iterrows():
            if mr.market in by_name.index:
                row=by_name.loc[mr.market].to_dict(); row["market_id"]=mr.market_id; row["market"]=mr.market
                rows.append(row)
        if rows:
            coords=pd.DataFrame(rows).set_index("market_id")
            names=[mid for mid in pivot.columns if mid in coords.index]
    rows = []
    for a, b in combinations(names, 2):
        z = pivot[[a, b]].dropna()
        if len(z) < min_overlap:
            continue
        corr = z[a].corr(z[b])
        ca, cb = coords.loc[a], coords.loc[b]
        dist = haversine_km(float(ca.lat), float(ca.lon), float(cb.lat), float(cb.lon))
        rows.append({
            "market_a_id": a,
            "market_b_id": b,
            "market_a": ca.get("market", a),
            "market_b": cb.get("market", b),
            "state_a": ca.get("state", ""),
            "state_b": cb.get("state", ""),
            "distance_km": dist,
            "return_corr": corr,
            "overlap": len(z),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    bins = [0, 100, 250, 500, 1000, np.inf]
    labels = ["0–100", "100–250", "250–500", "500–1000", ">1000"]
    out["distance_bin"] = pd.cut(out.distance_km, bins=bins, labels=labels, right=False)
    return out


def _qap_permutation_p(pairs: pd.DataFrame, observed: float, permutations: int, seed: int) -> float | None:
    """QAP-style label permutation for pairwise matrix association.

    Market-pair rows are not independent, so a conventional correlation p-value is
    optimistic. Relabelling one matrix preserves its internal pair dependence and gives
    a more defensible exploratory significance check.
    """
    if pairs.empty or permutations <= 0 or pd.isna(observed):
        return None
    ids = sorted(set(pairs.market_a_id) | set(pairs.market_b_id))
    corr = {tuple(sorted((r.market_a_id, r.market_b_id))): float(r.return_corr) for _, r in pairs.iterrows()}
    dist = {tuple(sorted((r.market_a_id, r.market_b_id))): float(r.distance_km) for _, r in pairs.iterrows()}
    base_pairs = list(dist)
    rng = np.random.default_rng(seed)
    extreme = 0
    valid = 0
    for _ in range(permutations):
        shuffled = ids.copy()
        rng.shuffle(shuffled)
        mapping = dict(zip(ids, shuffled))
        xs, ys = [], []
        for a, b in base_pairs:
            mapped = tuple(sorted((mapping[a], mapping[b])))
            if mapped in corr:
                xs.append(dist[(a, b)])
                ys.append(corr[mapped])
        if len(xs) < 3:
            continue
        rho = spearmanr(xs, ys, nan_policy="omit").statistic
        if pd.notna(rho):
            valid += 1
            if abs(float(rho)) >= abs(observed):
                extreme += 1
    return (extreme + 1) / (valid + 1) if valid else None


def distance_effect_summary(
    pairs: pd.DataFrame,
    permutations: int = 499,
    seed: int = 240124,
) -> dict[str, float | int | None]:
    if pairs.empty or len(pairs) < 3:
        return {"pairs": len(pairs), "spearman_rho": None, "p_value": None, "qap_p_value": None}
    rho, p = spearmanr(pairs.distance_km, pairs.return_corr, nan_policy="omit")
    rho = float(rho)
    return {
        "pairs": len(pairs),
        "spearman_rho": rho,
        "p_value": float(p),
        "qap_p_value": _qap_permutation_p(pairs, rho, permutations, seed),
    }
