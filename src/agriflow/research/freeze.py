from __future__ import annotations

"""Empirical-scope freezing, readiness auditing and integrity verification.

The final paper should never depend on whatever happens to be in data/processed at
presentation time.  This module snapshots the exact inputs used for one empirical
run, records provenance and SHA-256 hashes, and verifies the snapshot later.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
from typing import Iterable

import pandas as pd

from agriflow.data.identity import ensure_market_id
from agriflow.data.provenance import infer_source_tier, split_tiers, tiers_are_paper_acceptable


def _slug(value: str) -> str:
    x = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return x.strip("_") or "run"


def sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class ReadinessPolicy:
    min_span_days: int = 365
    min_states: int = 3
    min_markets: int = 8
    min_observations: int = 500
    min_arrival_availability: float = 0.20
    min_coordinate_coverage: float = 0.70
    min_weather_market_coverage: float = 0.60


def _bool_gate(name: str, passed: bool, value, threshold, severity: str, detail: str) -> dict:
    return {
        "gate": name,
        "status": "PASS" if passed else severity,
        "value": value,
        "threshold": threshold,
        "detail": detail,
    }


def empirical_readiness(
    prices: pd.DataFrame,
    markets: pd.DataFrame | None,
    weather: pd.DataFrame | None,
    commodities: Iterable[str],
    start_date: str,
    end_date: str,
    policy: ReadinessPolicy = ReadinessPolicy(),
) -> dict:
    """Audit whether a selected empirical scope is suitable for paper-grade analysis.

    Hard gates (FAIL) protect academic integrity.  Coverage gaps that can legitimately
    remain in an empirical study are WARN gates and must be disclosed rather than hidden.
    """
    wanted = [str(c).strip() for c in commodities if str(c).strip()]
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    x = ensure_market_id(prices.copy())
    x["date"] = pd.to_datetime(x["date"])
    x = x[x["commodity"].isin(wanted) & x["date"].between(start, end)].copy()

    modes = sorted(set(x.get("data_mode", pd.Series(dtype=str)).fillna("").astype(str).str.upper()))
    sources = sorted(set(s for s in x.get("source", pd.Series(dtype=str)).fillna("").astype(str) if s))
    if "source_tier" not in x.columns:
        x["source_tier"] = [infer_source_tier(src, mode) for src, mode in zip(
            x.get("source", pd.Series("", index=x.index)).fillna(""),
            x.get("data_mode", pd.Series("", index=x.index)).fillna(""),
        )]
    source_tiers = sorted(split_tiers(x["source_tier"].fillna("").astype(str)))
    states = int(x["state"].nunique()) if not x.empty else 0
    markets_n = int(x["market_id"].nunique()) if not x.empty else 0
    observations = int(len(x))
    span = int((x["date"].max() - x["date"].min()).days + 1) if not x.empty else 0
    arrival_avail = float(x["arrivals"].notna().mean()) if not x.empty and "arrivals" in x else 0.0

    coord_cov = 0.0
    coordinate_quality_counts: dict[str, int] = {}
    if markets is not None and not markets.empty and markets_n:
        m = ensure_market_id(markets.copy())
        m = m[m["market_id"].isin(set(x["market_id"]))].drop_duplicates("market_id")
        coord_cov = float(m[["lat", "lon"]].notna().all(axis=1).mean()) if len(m) else 0.0
        if "coordinate_quality" in m:
            coordinate_quality_counts = {
                str(k): int(v) for k, v in m["coordinate_quality"].fillna("unknown").value_counts().items()
            }

    weather_cov = 0.0
    if weather is not None and not weather.empty and markets_n:
        w = ensure_market_id(weather.copy())
        w["date"] = pd.to_datetime(w["date"])
        w = w[w["market_id"].isin(set(x["market_id"])) & w["date"].between(start, end)]
        weather_cov = float(w["market_id"].nunique() / markets_n) if markets_n else 0.0

    gates = [
        _bool_gate("real_data_only", bool(modes) and modes == ["REAL"], modes, "['REAL']", "FAIL", "Final empirical runs must contain no DEMO observations."),
        _bool_gate("nonempty_selected_scope", observations > 0, observations, "> 0", "FAIL", "The selected commodity/date scope must contain observations."),
        _bool_gate("source_provenance_present", bool(sources), len(sources), ">= 1 source", "FAIL", "At least one non-empty source label is required."),
        _bool_gate("paper_acceptable_source_tier", tiers_are_paper_acceptable(source_tiers), source_tiers, "PRIMARY_OFFICIAL or CURATED_OFFICIAL_DERIVED only", "FAIL", "Final-paper freezes reject secondary mirrors, unverified user imports and unknown provenance even when observations are REAL."),
        _bool_gate("temporal_span", span >= policy.min_span_days, span, policy.min_span_days, "WARN", "Short spans weaken seasonality and temporal-network interpretation."),
        _bool_gate("state_breadth", states >= policy.min_states, states, policy.min_states, "WARN", "A pilot can be narrower, but national claims require broader state coverage."),
        _bool_gate("market_breadth", markets_n >= policy.min_markets, markets_n, policy.min_markets, "WARN", "Network inference needs multiple sufficiently observed markets."),
        _bool_gate("observation_volume", observations >= policy.min_observations, observations, policy.min_observations, "WARN", "Very small panels are unsuitable for stable national inference."),
        _bool_gate("arrival_availability", arrival_avail >= policy.min_arrival_availability, round(arrival_avail, 4), policy.min_arrival_availability, "WARN", "Arrival-based crunch and supply analyses depend on non-missing arrivals."),
        _bool_gate("coordinate_coverage", coord_cov >= policy.min_coordinate_coverage, round(coord_cov, 4), policy.min_coordinate_coverage, "WARN", "Spatial/network maps and distance analysis require reviewed coordinates."),
        _bool_gate("weather_market_coverage", weather_cov >= policy.min_weather_market_coverage, round(weather_cov, 4), policy.min_weather_market_coverage, "WARN", "Weather-event analysis should not silently represent only a small market subset."),
    ]
    fail_count = sum(g["status"] == "FAIL" for g in gates)
    warn_count = sum(g["status"] == "WARN" for g in gates)
    status = "BLOCKED" if fail_count else ("READY_WITH_WARNINGS" if warn_count else "READY")
    return {
        "status": status,
        "scope": {
            "commodities": wanted,
            "start_date": str(start.date()),
            "end_date": str(end.date()),
        },
        "summary": {
            "observations": observations,
            "states": states,
            "markets": markets_n,
            "span_days": span,
            "arrival_availability": round(arrival_avail, 6),
            "coordinate_coverage": round(coord_cov, 6),
            "weather_market_coverage": round(weather_cov, 6),
            "data_modes": modes,
            "sources": sources,
            "source_tiers": source_tiers,
            "coordinate_quality_counts": coordinate_quality_counts,
        },
        "policy": asdict(policy),
        "gates": gates,
    }


def freeze_scope(
    prices: pd.DataFrame,
    markets: pd.DataFrame | None,
    weather: pd.DataFrame | None,
    commodities: Iterable[str],
    start_date: str,
    end_date: str,
    freeze_root: Path,
    *,
    label: str | None = None,
    allow_demo_for_testing: bool = False,
    policy: ReadinessPolicy = ReadinessPolicy(),
    provenance_files: Iterable[Path] | None = None,
) -> tuple[Path, dict]:
    """Write an immutable-style snapshot directory and integrity manifest."""
    readiness = empirical_readiness(prices, markets, weather, commodities, start_date, end_date, policy)
    if readiness["status"] == "BLOCKED" and not allow_demo_for_testing:
        reasons = [g["gate"] for g in readiness["gates"] if g["status"] == "FAIL"]
        raise ValueError("Empirical freeze blocked by hard gate(s): " + ", ".join(reasons))

    wanted = readiness["scope"]["commodities"]
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    p = ensure_market_id(prices.copy())
    p["date"] = pd.to_datetime(p["date"])
    p = p[p["commodity"].isin(wanted) & p["date"].between(start, end)].copy()
    if p.empty:
        raise ValueError("Selected freeze scope contains no observations")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = _slug(label or "_".join(wanted[:3]))[:48]
    out = freeze_root / f"{stamp}_{tag}"
    if out.exists():
        raise FileExistsError(f"Freeze directory already exists: {out}")
    out.mkdir(parents=True, exist_ok=False)

    p_path = out / "market_daily.csv"
    p.to_csv(p_path, index=False)
    used_ids = set(p["market_id"])

    files = {"market_daily.csv": p_path}
    if markets is not None and not markets.empty:
        m = ensure_market_id(markets.copy())
        m = m[m["market_id"].isin(used_ids)].drop_duplicates("market_id")
        m_path = out / "markets.csv"
        m.to_csv(m_path, index=False)
        files["markets.csv"] = m_path
    if weather is not None and not weather.empty:
        w = ensure_market_id(weather.copy())
        w["date"] = pd.to_datetime(w["date"])
        w = w[w["market_id"].isin(used_ids) & w["date"].between(start, end)].copy()
        if not w.empty:
            w_path = out / "weather_daily.csv"
            w.to_csv(w_path, index=False)
            files["weather_daily.csv"] = w_path

    readiness_path = out / "readiness.json"
    readiness_path.write_text(json.dumps(readiness, indent=2, default=str), encoding="utf-8")
    files["readiness.json"] = readiness_path

    provenance_dir = out / "provenance"
    for source_path in provenance_files or []:
        source_path = Path(source_path)
        if not source_path.exists() or not source_path.is_file():
            continue
        provenance_dir.mkdir(exist_ok=True)
        dest = provenance_dir / source_path.name
        # Avoid silent collisions if two provenance files have the same basename.
        if dest.exists():
            dest = provenance_dir / f"{_slug(source_path.parent.name)}__{source_path.name}"
        shutil.copy2(source_path, dest)
        files[str(dest.relative_to(out)).replace("\\", "/")] = dest

    manifest = {
        "schema_version": "1.0",
        "project": "AgriFlow",
        "freeze_created_at_utc": datetime.now(timezone.utc).isoformat(),
        "label": label or "",
        "scope": readiness["scope"],
        "readiness_status": readiness["status"],
        "academic_integrity": (
            "This directory snapshots the exact analytical inputs for one run. "
            "DEMO freezes are permitted only for software testing and must never be cited as empirical findings."
        ),
        "files": {},
    }
    for name, path in files.items():
        manifest["files"][name] = {"sha256": sha256_file(path), "bytes": int(path.stat().st_size)}
    manifest_path = out / "freeze_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    sums = [f"{entry['sha256']}  {name}" for name, entry in sorted(manifest["files"].items())]
    sums.append(f"{sha256_file(manifest_path)}  freeze_manifest.json")
    (out / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return out, manifest


def verify_freeze(path: Path) -> dict:
    path = Path(path)
    manifest_path = path / "freeze_manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "errors": ["freeze_manifest.json missing"], "files": {}}
    errors: list[str] = []
    checks = {}

    # SHA256SUMS also contains the manifest digest. This catches accidental edits
    # to the manifest itself instead of trusting a modified manifest blindly.
    sums_path = path / "SHA256SUMS.txt"
    listed: dict[str, str] = {}
    if sums_path.exists():
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            if "  " in line:
                digest, name = line.split("  ", 1)
                listed[name.strip()] = digest.strip()
        expected_manifest = listed.get("freeze_manifest.json")
        if expected_manifest:
            actual_manifest = sha256_file(manifest_path)
            ok = actual_manifest == expected_manifest
            checks["freeze_manifest.json"] = {"ok": ok, "expected": expected_manifest, "actual": actual_manifest}
            if not ok:
                errors.append("checksum mismatch: freeze_manifest.json")
    else:
        errors.append("SHA256SUMS.txt missing")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"freeze_manifest.json invalid JSON: {exc}")
        return {"ok": False, "errors": errors, "files": checks}
    for name, meta in manifest.get("files", {}).items():
        p = path / name
        if not p.exists():
            checks[name] = {"ok": False, "reason": "missing"}
            errors.append(f"missing: {name}")
            continue
        actual = sha256_file(p)
        expected = str(meta.get("sha256", ""))
        ok = actual == expected
        checks[name] = {"ok": ok, "expected": expected, "actual": actual}
        if not ok:
            errors.append(f"checksum mismatch: {name}")
        listed_expected = listed.get(name)
        if listed_expected and listed_expected != actual:
            errors.append(f"SHA256SUMS mismatch: {name}")
    return {"ok": not errors, "errors": errors, "files": checks}
