from __future__ import annotations

"""Analysis runner for a frozen AgriFlow empirical snapshot."""

from datetime import datetime, timezone
from pathlib import Path
import json
import re

import pandas as pd

from agriflow.analytics.coverage import coverage_audit
from agriflow.analytics.events import detect_market_crunches
from agriflow.analytics.geography import distance_similarity, distance_effect_summary
from agriflow.analytics.integration import market_integration_pairs
from agriflow.analytics.lead_lag import infer_lead_lag_edges
from agriflow.analytics.network import influence_scores
from agriflow.analytics.robustness import yearly_edge_stability, yearly_leader_stability
from agriflow.analytics.supply_price import supply_price_stats
from agriflow.analytics.weather import join_market_weather, event_study, event_study_summary
from agriflow.research.freeze import verify_freeze, sha256_file


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _read_optional(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def analyze_frozen_scope(
    freeze_dir: Path,
    *,
    max_lag_days: int = 7,
    min_overlap_days: int = 35,
    min_edge_corr: float = 0.30,
    fdr_alpha: float = 0.05,
    max_network_markets: int = 40,
) -> tuple[Path, dict]:
    freeze_dir = Path(freeze_dir)
    verification = verify_freeze(freeze_dir)
    if not verification["ok"]:
        raise ValueError("Freeze integrity verification failed: " + "; ".join(verification["errors"]))

    prices = pd.read_csv(freeze_dir / "market_daily.csv")
    prices["date"] = pd.to_datetime(prices["date"])
    markets = _read_optional(freeze_dir / "markets.csv")
    weather = _read_optional(freeze_dir / "weather_daily.csv")
    if not weather.empty:
        weather["date"] = pd.to_datetime(weather["date"])

    results = freeze_dir / "results"
    results.mkdir(exist_ok=True)
    coverage_audit(prices).to_csv(results / "coverage_audit.csv", index=False)
    detect_market_crunches(prices).to_csv(results / "market_crunch_candidates.csv", index=False)

    run_summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_dir": freeze_dir.name,
        "commodities": {},
        "analysis_settings": {
            "max_lag_days": max_lag_days,
            "min_overlap_days": min_overlap_days,
            "min_edge_corr": min_edge_corr,
            "fdr_alpha": fdr_alpha,
            "max_network_markets": max_network_markets,
        },
        "interpretation_guardrail": (
            "Lead-lag, weather-event and integration results are statistical/descriptive associations. "
            "They do not establish causal market control or causal weather effects."
        ),
    }

    for commodity in sorted(prices["commodity"].dropna().astype(str).unique()):
        key = _slug(commodity)
        c = prices[prices["commodity"].eq(commodity)].copy()
        edges = infer_lead_lag_edges(
            prices, commodity, max_lag_days, min_overlap_days,
            min_edge_corr, fdr_alpha, max_network_markets,
        )
        scores = influence_scores(edges)
        integ = market_integration_pairs(prices, commodity, edges, min_overlap_days)
        edges.to_csv(results / f"lead_lag_{key}.csv", index=False)
        scores.to_csv(results / f"influence_{key}.csv", index=False)
        integ.to_csv(results / f"integration_{key}.csv", index=False)

        yearly_edges, edge_stability = yearly_edge_stability(
            prices, commodity, max_lag=max_lag_days, min_overlap=min_overlap_days,
            min_abs_corr=min_edge_corr, fdr_alpha=fdr_alpha, max_markets=max_network_markets,
        )
        annual_leaders, leader_stability = yearly_leader_stability(yearly_edges)
        yearly_edges.to_csv(results / f"lead_lag_yearly_{key}.csv", index=False)
        edge_stability.to_csv(results / f"edge_stability_{key}.csv", index=False)
        annual_leaders.to_csv(results / f"leader_yearly_{key}.csv", index=False)
        leader_stability.to_csv(results / f"leader_stability_{key}.csv", index=False)

        dist_summary = {"pairs": 0, "spearman_rho": None, "p_value": None, "qap_p_value": None}
        if not markets.empty:
            pairs = distance_similarity(prices, markets, commodity, min_overlap_days)
            pairs.to_csv(results / f"distance_pairs_{key}.csv", index=False)
            dist_summary = distance_effect_summary(pairs)
            (results / f"distance_summary_{key}.json").write_text(
                json.dumps(dist_summary, indent=2, default=str), encoding="utf-8"
            )

        weather_summary_rows = 0
        weather_event_count = 0
        if not weather.empty:
            try:
                joined = join_market_weather(c, weather)
                events = event_study(joined)
                summary = event_study_summary(events)
                events.to_csv(results / f"weather_events_{key}.csv", index=False)
                summary.to_csv(results / f"weather_event_summary_{key}.csv", index=False)
                weather_event_count = int(len(events))
                weather_summary_rows = int(len(summary))
            except Exception as exc:
                (results / f"weather_events_{key}.error.txt").write_text(str(exc), encoding="utf-8")

        supply = supply_price_stats(c)
        top = scores.iloc[0].to_dict() if len(scores) else None
        stable = leader_stability.iloc[0].to_dict() if len(leader_stability) else None
        run_summary["commodities"][commodity] = {
            "observations": int(len(c)),
            "states": int(c["state"].nunique()),
            "markets": int(c["market_id"].nunique() if "market_id" in c else c["market"].nunique()),
            "lead_lag_edges": int(len(edges)),
            "top_full_period_price_leader": top,
            "top_temporally_stable_leader": stable,
            "evaluable_years": int(edge_stability["years_evaluated"].max()) if len(edge_stability) else 0,
            "persistent_edges_ge_50pct": int((edge_stability["persistence_ratio"] >= 0.5).sum()) if len(edge_stability) else 0,
            "distance_effect": dist_summary,
            "weather_event_rows": weather_event_count,
            "weather_summary_rows": weather_summary_rows,
            "supply_price_association": supply,
        }

    summary_path = results / "empirical_run_summary.json"
    summary_path.write_text(json.dumps(run_summary, indent=2, default=str), encoding="utf-8")

    # A concise, machine-generated research notebook aid. It deliberately avoids
    # causal language so it can be inspected before any sentence is copied into a paper.
    lines = [
        "# AgriFlow Frozen-Run Summary",
        "",
        f"Generated: {run_summary['generated_at_utc']}",
        "",
        "> Interpretation guardrail: statistical leadership is not causal/commercial control; weather-event results are descriptive associations.",
        "",
    ]
    for commodity, s in run_summary["commodities"].items():
        lines += [f"## {commodity}", ""]
        lines.append(f"- Panel: {s['observations']:,} observations, {s['markets']} markets, {s['states']} states/UTs.")
        lines.append(f"- Significant lead-lag edges under configured FDR/effect-size gates: {s['lead_lag_edges']}.")
        top = s.get("top_full_period_price_leader")
        if top:
            lines.append(f"- Highest full-period source-oriented influence score: {top.get('market')} ({float(top.get('influence_score', 0)):.3f}).")
        stable = s.get("top_temporally_stable_leader")
        if stable:
            lines.append(f"- Highest temporal-stability ranking: {stable.get('market')} (top-3 in {int(stable.get('top3_years', 0))} evaluable years).")
        d=s.get("distance_effect") or {}
        if d.get("spearman_rho") is not None:
            lines.append(f"- Distance effect: Spearman ρ={float(d['spearman_rho']):.3f}; QAP-style p={float(d['qap_p_value']):.4g} across {int(d['pairs'])} pairs.")
        lines.append(f"- Declustered weather-event observations: {s['weather_event_rows']}.")
        lines.append("")
    report = results / "RESULTS_SUMMARY.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    artifact_files = sorted(p for p in results.iterdir() if p.is_file())
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_manifest_sha256": sha256_file(freeze_dir / "freeze_manifest.json"),
        "files": {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size} for p in artifact_files},
    }
    (results / "results_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return results, run_summary
