from __future__ import annotations

"""Defensible commodity-basket selection from observed reporting coverage."""

from dataclasses import dataclass, asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd

from agriflow.analytics.coverage import coverage_audit


@dataclass(frozen=True)
class SelectionPolicy:
    target_count: int = 10
    min_states: int = 8
    min_markets: int = 40
    min_observations: int = 2000
    min_median_state_density: float = 0.08
    min_arrival_availability: float = 0.20
    min_span_days: int = 365


def commodity_scope_table(prices: pd.DataFrame, policy: SelectionPolicy = SelectionPolicy()) -> pd.DataFrame:
    """Rank commodities using explicit, auditable coverage criteria.

    Scores are relative *within the supplied dataset*, so the raw component
    columns must always accompany the score in reports.
    """
    audit = coverage_audit(prices)
    if audit.empty:
        return pd.DataFrame(columns=[
            "commodity","states","state_coverage_ratio","markets","observations","span_days",
            "median_state_density","arrival_availability","coverage_score","eligible","recommended",
        ])

    total_states = max(int(prices["state"].nunique()), 1)
    rows = []
    for commodity, a in audit.groupby("commodity", sort=True):
        sub = prices[prices["commodity"].eq(commodity)]
        first = pd.to_datetime(sub["date"]).min()
        last = pd.to_datetime(sub["date"]).max()
        span_days = int((last - first).days + 1) if pd.notna(first) and pd.notna(last) else 0
        rows.append({
            "commodity": commodity,
            "states": int(a["state"].nunique()),
            "state_coverage_ratio": float(a["state"].nunique() / total_states),
            "markets": int(a["markets"].sum()),
            "observations": int(a["observations"].sum()),
            "span_days": span_days,
            "median_state_density": float(a["reporting_density"].median()),
            "arrival_availability": float(
                sub["arrivals"].notna().mean() if "arrivals" in sub.columns and len(sub) else 0.0
            ),
        })
    out = pd.DataFrame(rows)

    # Saturating/relative transforms keep a single very large commodity from
    # dominating the score while still rewarding broad coverage.
    out["_states"] = out["state_coverage_ratio"].clip(0, 1)
    out["_markets"] = np.log1p(out["markets"]) / max(np.log1p(out["markets"].max()), 1)
    out["_obs"] = np.log1p(out["observations"]) / max(np.log1p(out["observations"].max()), 1)
    out["_span"] = (out["span_days"] / max(policy.min_span_days * 3, 1)).clip(upper=1)
    out["_density"] = out["median_state_density"].clip(0, 1)
    out["_arrivals"] = out["arrival_availability"].clip(0, 1)
    out["coverage_score"] = (
        0.30 * out["_states"]
        + 0.18 * out["_markets"]
        + 0.16 * out["_obs"]
        + 0.12 * out["_span"]
        + 0.14 * out["_density"]
        + 0.10 * out["_arrivals"]
    )
    out["eligible"] = (
        (out["states"] >= policy.min_states)
        & (out["markets"] >= policy.min_markets)
        & (out["observations"] >= policy.min_observations)
        & (out["median_state_density"] >= policy.min_median_state_density)
        & (out["arrival_availability"] >= policy.min_arrival_availability)
        & (out["span_days"] >= policy.min_span_days)
    )
    out = out.sort_values(["eligible", "coverage_score", "states", "observations"], ascending=[False, False, False, False]).reset_index(drop=True)
    out["recommended"] = False
    eligible_idx = out.index[out["eligible"]][: policy.target_count]
    out.loc[eligible_idx, "recommended"] = True
    return out.drop(columns=["_states","_markets","_obs","_span","_density","_arrivals"])


def write_selection_report(
    prices: pd.DataFrame,
    output_dir: Path,
    policy: SelectionPolicy = SelectionPolicy(),
) -> tuple[pd.DataFrame, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    table = commodity_scope_table(prices, policy)
    csv_path = output_dir / "commodity_scope_selection.csv"
    json_path = output_dir / "commodity_scope_selection.json"
    table.to_csv(csv_path, index=False)
    recommended = table.loc[table["recommended"], "commodity"].tolist()
    payload = {
        "policy": asdict(policy),
        "observed_states_in_input": int(prices["state"].nunique()) if len(prices) else 0,
        "recommended_commodities": recommended,
        "note": (
            "Recommendations are coverage-driven candidates, not a claim that these commodities "
            "represent all Indian agriculture. Review commodity relevance before the empirical freeze."
        ),
        "rows": table.to_dict("records"),
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return table, csv_path, json_path
