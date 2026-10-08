from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from hashlib import sha256
from datetime import datetime, timezone
import pandas as pd

from agriflow.config import settings
from agriflow.data.demo import generate_demo
from agriflow.data.processing import normalize_prices, aggregate_market_daily, quality_summary
from agriflow.data.sources.data_gov import DataGovMandiSource
from agriflow.data.sources.ceda import CedaHistoricalSource
from agriflow.data.ceda_ingest import CedaHistoricalIngestor
from agriflow.data.identity import ensure_market_id
from agriflow.data.manual_import import canonicalize_mandi_export
from agriflow.data.provenance import (
    PRIMARY_OFFICIAL, CURATED_OFFICIAL_DERIVED, SECONDARY_MIRROR, USER_SUPPLIED, split_tiers
)
from agriflow.data.weather_ingest import PowerHistoricalIngestor
from agriflow.data.sources.geo import GeographySource
from agriflow.data.sources.nasa_power import NasaPowerSource
from agriflow.analytics.coverage import coverage_audit, commodity_coverage_score
from agriflow.analytics.events import detect_market_crunches
from agriflow.analytics.geography import distance_similarity, distance_effect_summary
from agriflow.analytics.weather import join_market_weather, event_study, event_study_summary
from agriflow.analytics.lead_lag import infer_lead_lag_edges
from agriflow.analytics.network import influence_scores
from agriflow.analytics.integration import market_integration_pairs
from agriflow.analytics.selection import SelectionPolicy, write_selection_report, commodity_scope_table
from agriflow.research.freeze import ReadinessPolicy, empirical_readiness, freeze_scope, verify_freeze
from agriflow.research.runner import analyze_frozen_scope


def _ensure_dirs():
    for p in [settings.demo_dir,settings.raw_dir,settings.processed_dir,settings.cache_dir,settings.output_dir]: p.mkdir(parents=True,exist_ok=True)






def _file_sha256(path: Path) -> str:
    h=sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _record_ingest_provenance(*, source: str, source_tier: str, rows: int, raw_file: Path | None = None, note: str = "") -> None:
    _ensure_dirs()
    record={
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_tier": source_tier,
        "rows": int(rows),
        "raw_file": str(raw_file.relative_to(settings.root)) if raw_file and raw_file.exists() else "",
        "raw_file_sha256": _file_sha256(raw_file) if raw_file and raw_file.exists() else "",
        "note": note,
    }
    path=settings.raw_dir/"ingest_provenance.jsonl"
    with path.open("a",encoding="utf-8") as fh:
        fh.write(json.dumps(record,sort_keys=True)+"\n")

def _update_market_index(daily: pd.DataFrame) -> Path:
    """Create/update the unique real-data market coordinate index without discarding known coordinates."""
    daily=ensure_market_id(daily)
    cols=[c for c in ["market_id","state","district","market"] if c in daily.columns]
    base=daily[cols].drop_duplicates("market_id").copy()
    path=settings.processed_dir/"markets.csv"
    if path.exists():
        old=ensure_market_id(pd.read_csv(path))
        keep=[c for c in ["market_id","state","district","market","lat","lon","coordinate_quality","coordinate_source"] if c in old.columns]
        old=old[keep].drop_duplicates("market_id")
        extra=[c for c in ["lat","lon","coordinate_quality","coordinate_source"] if c in old.columns]
        base=base.merge(old[["market_id"]+extra],on="market_id",how="left")
    else:
        base["lat"]=pd.NA;base["lon"]=pd.NA;base["coordinate_quality"]="unresolved";base["coordinate_source"]=""
    base.to_csv(path,index=False)
    return path

def cmd_init(args):
    _ensure_dirs(); generate_demo(settings.demo_dir)
    print(f"Demo fixture ready in {settings.demo_dir}")
    if args.geojson:
        try:
            p=GeographySource().download_state_geojson(settings.cache_dir/"india_states.geojson")
            print(f"State GeoJSON cached: {p}")
        except Exception as exc:
            print(f"GeoJSON download skipped: {exc}")


def cmd_fetch_current(args):
    _ensure_dirs()
    if not settings.data_gov_api_key:
        raise SystemExit("DATA_GOV_API_KEY is missing. Add it to .env; demo mode requires no key.")
    src=DataGovMandiSource(settings.data_gov_api_key)
    df=src.fetch_dataframe(max_records=args.max_records,state=args.state or "",commodity=args.commodity or "")
    if df.empty: raise SystemExit("No records returned for these filters.")
    raw=settings.raw_dir/"data_gov_current.csv"; df.to_csv(raw,index=False)
    norm=normalize_prices(df.assign(source="DATA_GOV_IN_AGMARKNET",source_tier=PRIMARY_OFFICIAL,data_mode="REAL"))
    daily=aggregate_market_daily(norm); out=settings.processed_dir/"market_daily.csv"; daily.to_csv(out,index=False)
    market_path=_update_market_index(daily)
    _record_ingest_provenance(source="DATA_GOV_IN_AGMARKNET",source_tier=PRIMARY_OFFICIAL,rows=len(daily),raw_file=raw,note="Direct OGD/AGMARKNET API ingestion")
    print(f"Saved {len(daily):,} normalized records to {out}")
    print(f"Market coordinate index: {market_path}")


def cmd_import(args):
    _ensure_dirs(); p=Path(args.path)
    if not p.exists(): raise SystemExit(f"File not found: {p}")
    if args.source_tier not in {USER_SUPPLIED, SECONDARY_MIRROR}:
        raise SystemExit("Generic imports may only be USER_SUPPLIED or SECONDARY_MIRROR. Use the dedicated official-source import command for OGD/CEDA exports.")
    df=pd.read_csv(p)
    if args.source:
        df["source"]=args.source
    if "source" not in df: df["source"]="USER_IMPORT"
    df["source_tier"]=args.source_tier
    df["data_mode"]="REAL"
    norm=normalize_prices(df); daily=aggregate_market_daily(norm)
    out=settings.processed_dir/"market_daily.csv"; daily.to_csv(out,index=False)
    market_path=_update_market_index(daily)
    raw=settings.raw_dir/f"import_{p.name}"
    shutil.copy2(p,raw)
    _record_ingest_provenance(source=args.source or "USER_IMPORT",source_tier=args.source_tier,rows=len(daily),raw_file=raw,note="Generic user CSV import")
    print(f"Imported {len(daily):,} daily market records -> {out}")
    print(f"Source tier: {args.source_tier}")
    print(f"Market coordinate index: {market_path}")


def cmd_import_ceda_csv(args):
    """Import a manually downloaded CEDA Agri-Market portal CSV with explicit provenance."""
    _ensure_dirs(); p=Path(args.path)
    if not p.exists(): raise SystemExit(f"File not found: {p}")
    try:
        canonical=canonicalize_mandi_export(
            pd.read_csv(p), state=args.state, district=args.district,
            market=args.market, commodity=args.commodity,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    canonical["source"]="CEDA_PORTAL_EXPORT"
    canonical["source_tier"]=CURATED_OFFICIAL_DERIVED
    canonical["data_mode"]="REAL"
    norm=normalize_prices(canonical); daily=aggregate_market_daily(norm)
    out=settings.processed_dir/"market_daily.csv"; daily.to_csv(out,index=False)
    market_path=_update_market_index(daily)
    raw=settings.raw_dir/f"ceda_portal_{p.name}"
    shutil.copy2(p,raw)
    _record_ingest_provenance(
        source="CEDA_PORTAL_EXPORT", source_tier=CURATED_OFFICIAL_DERIVED,
        rows=len(daily), raw_file=raw,
        note="Manual export from CEDA Agri-Market Data portal; retain the portal filter/date selection with the project records.",
    )
    print(f"Imported {len(daily):,} CEDA portal market-day rows -> {out}")
    print(f"Source tier: {CURATED_OFFICIAL_DERIVED}")
    print(f"Market coordinate index: {market_path}")


def cmd_import_data_gov_csv(args):
    """Import a manually downloaded official data.gov.in AGMARKNET CSV."""
    _ensure_dirs(); p=Path(args.path)
    if not p.exists(): raise SystemExit(f"File not found: {p}")
    try:
        canonical=canonicalize_mandi_export(
            pd.read_csv(p), state=args.state, district=args.district,
            market=args.market, commodity=args.commodity,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    canonical["source"]="DATA_GOV_IN_AGMARKNET_MANUAL"
    canonical["source_tier"]=PRIMARY_OFFICIAL
    canonical["data_mode"]="REAL"
    norm=normalize_prices(canonical); daily=aggregate_market_daily(norm)
    out=settings.processed_dir/"market_daily.csv"; daily.to_csv(out,index=False)
    market_path=_update_market_index(daily)
    raw=settings.raw_dir/f"data_gov_manual_{p.name}"
    shutil.copy2(p,raw)
    _record_ingest_provenance(
        source="DATA_GOV_IN_AGMARKNET_MANUAL", source_tier=PRIMARY_OFFICIAL,
        rows=len(daily), raw_file=raw,
        note="Manual export from the official Government of India OGD/AGMARKNET resource; retain the download URL/filter/date context with project records.",
    )
    print(f"Imported {len(daily):,} official OGD market-day rows -> {out}")
    print(f"Source tier: {PRIMARY_OFFICIAL}")
    print(f"Market coordinate index: {market_path}")



def cmd_import_coordinates(args):
    _ensure_dirs()
    market_path=settings.processed_dir/"markets.csv"
    if not market_path.exists():
        raise SystemExit("No market index found. Fetch/import market prices first.")
    coord_path=Path(args.path)
    if not coord_path.exists():
        raise SystemExit(f"Coordinate file not found: {coord_path}")
    markets=ensure_market_id(pd.read_csv(market_path))
    coords=ensure_market_id(pd.read_csv(coord_path))
    required={"market_id","lat","lon"}
    if not required.issubset(coords.columns):
        raise SystemExit("Coordinate CSV must contain lat/lon and either market_id or state+district+market columns.")
    coords["lat"]=pd.to_numeric(coords["lat"],errors="coerce")
    coords["lon"]=pd.to_numeric(coords["lon"],errors="coerce")
    coords=coords[coords.lat.between(6,38) & coords.lon.between(67,98)].copy()
    if coords.empty:
        raise SystemExit("No coordinate rows remain after numeric/India-range validation.")
    coords["coordinate_quality"]=coords.get("coordinate_quality", args.quality)
    coords["coordinate_source"]=coords.get("coordinate_source", args.source)
    cols=["market_id","lat","lon","coordinate_quality","coordinate_source"]
    coords=coords[cols].drop_duplicates("market_id",keep="last")
    out=markets.drop(columns=[c for c in cols[1:] if c in markets.columns]).merge(coords,on="market_id",how="left")
    old=markets.set_index("market_id")
    for col in ["lat","lon","coordinate_quality","coordinate_source"]:
        if col in old.columns:
            prior=out.market_id.map(old[col])
            out[col]=out[col].where(out[col].notna(),prior)
    out.to_csv(market_path,index=False)
    matched=int(out[["lat","lon"]].notna().all(axis=1).sum())
    audit=pd.DataFrame({
        "metric":["markets_total","coordinates_resolved","coordinates_unresolved","import_rows_valid"],
        "value":[len(out),matched,len(out)-matched,len(coords)],
    })
    audit.to_csv(settings.output_dir/"coordinate_import_audit.csv",index=False)
    print(f"Coordinate coverage: {matched}/{len(out)} markets -> {market_path}")


def cmd_geocode(args):
    _ensure_dirs()
    if not args.accept_policy:
        raise SystemExit(
            "Public Nominatim use requires an explicit policy acknowledgement. Re-run with --accept-nominatim-policy "
            "after reading https://operations.osmfoundation.org/policies/nominatim/. For pan-India scale, prefer "
            "import-coordinates or an approved/self-hosted geocoder."
        )
    path=settings.processed_dir/"markets.csv"
    if not path.exists():
        raise SystemExit("No market index found. Fetch/import market prices first.")
    markets=ensure_market_id(pd.read_csv(path))
    unresolved=markets[markets[["lat","lon"]].isna().any(axis=1)].head(args.limit).index
    subset=markets.loc[unresolved].copy()
    if subset.empty:
        print(f"All {len(markets)} markets already have coordinates -> {path}")
        return
    resolved=GeographySource().geocode_markets(subset,delay_s=args.delay,max_requests=args.max_requests)
    for col in ["lat","lon","coordinate_quality","coordinate_source"]:
        if col in resolved.columns:
            markets.loc[unresolved,col]=resolved[col].to_numpy()
    markets.to_csv(path,index=False)
    ok=markets[["lat","lon"]].notna().all(axis=1).sum()
    print(f"Coordinate coverage: {ok}/{len(markets)} markets -> {path}")





def _split_values(values):
    """Normalize repeatable/comma-separated CLI values while preserving names with spaces."""
    out=[]
    for value in values or []:
        out.extend(x.strip() for x in str(value).split(",") if x.strip())
    return out


def cmd_ceda_catalog(args):
    _ensure_dirs()
    if not settings.ceda_api_key:
        raise SystemExit("CEDA_API_KEY is missing. Add your CEDA Bearer token to .env.")
    src=CedaHistoricalSource(settings.ceda_api_key)
    ing=CedaHistoricalIngestor(src,settings.raw_dir,settings.processed_dir)
    cp,gp=ing.cache_catalogs()
    commodities=pd.read_csv(cp); geographies=pd.read_csv(gp)
    print(f"Cached {len(commodities):,} commodities -> {cp}")
    print(f"Cached {geographies.census_state_id.nunique():,} states/UTs and {geographies.census_district_id.nunique():,} district IDs -> {gp}")


def cmd_fetch_ceda(args):
    _ensure_dirs()
    if not settings.ceda_api_key:
        raise SystemExit("CEDA_API_KEY is missing. Add your CEDA Bearer token to .env.")
    commodities=_split_values(args.commodity)
    if not commodities:
        raise SystemExit("At least one --commodity is required (repeat the option or use a comma-separated list).")
    states=_split_values(args.state) or None
    src=CedaHistoricalSource(settings.ceda_api_key)
    ing=CedaHistoricalIngestor(src,settings.raw_dir,settings.processed_dir)
    ing.cache_catalogs()
    jobs=ing.plan(commodities,args.start,args.end,states=states,district_limit=args.district_limit)
    print(f"CEDA plan: {len(jobs):,} resumable commodity × district × year jobs")
    if args.dry_run:
        for job in jobs[:25]:
            print(f"  {job.commodity_name} | {job.state_name} | {job.district_name} | {job.start_date}..{job.end_date}")
        if len(jobs)>25: print(f"  ... {len(jobs)-25:,} additional jobs")
        return
    summary=ing.run(
        jobs, include_quantities=not args.no_quantities, force=args.force, fail_fast=args.fail_fast
    )
    print(json.dumps({k:v for k,v in summary.items() if k!='errors'},indent=2))
    if summary['failed']:
        print(f"{summary['failed']} jobs failed; details are retained in data/raw/ceda_chunks/_errors.jsonl")
    try:
        daily,out=ing.rebuild_processed()
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    market_path=_update_market_index(daily)
    print(f"Rebuilt {len(daily):,} canonical market-day records -> {out}")
    print(f"Market coordinate index: {market_path}")
    policy=SelectionPolicy(target_count=args.target_count)
    table,csv_path,json_path=write_selection_report(daily,settings.output_dir,policy)
    rec=table.loc[table.recommended,'commodity'].tolist()
    print(f"Coverage-driven candidates ({len(rec)}): {', '.join(rec) if rec else 'none meet default thresholds yet'}")
    print(f"Scope audit: {csv_path} and {json_path}")


def cmd_scope_audit(args):
    from agriflow.data.repository import DataRepository
    _ensure_dirs()
    prices=DataRepository().load_prices()
    policy=SelectionPolicy(
        target_count=args.target_count,
        min_states=args.min_states,
        min_markets=args.min_markets,
        min_observations=args.min_observations,
        min_median_state_density=args.min_density,
        min_arrival_availability=args.min_arrivals,
        min_span_days=args.min_span_days,
    )
    table,csv_path,json_path=write_selection_report(prices,settings.output_dir,policy)
    cols=['commodity','states','markets','observations','span_days','median_state_density','arrival_availability','coverage_score','eligible','recommended']
    print(table[cols].head(max(args.target_count*2,10)).to_string(index=False))
    print(f"Wrote {csv_path} and {json_path}")


def cmd_geo(args):
    _ensure_dirs(); p=GeographySource().download_state_geojson(settings.cache_dir/"india_states.geojson",provider=args.provider);print(p)


def cmd_weather(args):
    _ensure_dirs()
    markets_path=settings.processed_dir/"markets.csv"
    if not markets_path.exists():
        raise SystemExit("data/processed/markets.csv is required. Import/fetch market data and resolve coordinates first.")
    markets=ensure_market_id(pd.read_csv(markets_path))
    usable=markets.dropna(subset=["lat","lon"])
    if usable.empty:
        raise SystemExit("No usable market coordinates. Run import-coordinates (preferred) or the policy-limited geocoder first.")
    ing=PowerHistoricalIngestor(NasaPowerSource(),settings.raw_dir,settings.processed_dir)
    jobs=ing.plan(usable,args.start,args.end)
    mapping=pd.read_csv(settings.processed_dir/"power_market_cells.csv")
    cell_count = (
    mapping[["power_cell_lat", "power_cell_lon"]]
    .drop_duplicates()
    .shape[0]
    )

    print(
        f"POWER plan: {len(jobs):,} resumable cell × year jobs "
        f"for {len(mapping):,} markets across {cell_count:,} meteorological cells"
    )
    if args.dry_run:
        for job in jobs[:25]:
            print(f"  {job.cell_lat:.3f},{job.cell_lon:.3f} | {job.start_date}..{job.end_date}")
        if len(jobs)>25: print(f"  ... {len(jobs)-25:,} additional jobs")
        return
    summary=ing.run(jobs,force=args.force,fail_fast=args.fail_fast)
    print(json.dumps({k:v for k,v in summary.items() if k!='errors'},indent=2))
    weather,out=ing.rebuild_processed(usable)
    print(f"Rebuilt {len(weather):,} market-weather rows -> {out}")
    if summary["failed"]:
        print(f"{summary['failed']} POWER jobs failed; details retained in data/raw/power_chunks/_errors.jsonl")



def _scope_commodities(prices: pd.DataFrame, values, target_count: int = 10) -> list[str]:
    explicit=_split_values(values)
    if explicit:
        missing=sorted(set(explicit)-set(prices["commodity"].astype(str).unique()))
        if missing:
            raise SystemExit("Commodity not present in current processed data: " + ", ".join(missing))
        return explicit
    table=commodity_scope_table(prices,SelectionPolicy(target_count=target_count))
    recommended=table.loc[table["recommended"],"commodity"].astype(str).tolist() if len(table) else []
    if not recommended:
        raise SystemExit(
            "No commodities meet the default coverage-selection policy. Run scope-audit and pass explicit "
            "--commodity values after reviewing the coverage table."
        )
    return recommended


def _empirical_optional_inputs(mode: str):
    from agriflow.data.repository import DataRepository
    repo=DataRepository()
    if mode=="DEMO":
        return repo.load_markets(),repo.load_weather()
    mp=settings.processed_dir/"markets.csv"
    wp=settings.processed_dir/"weather_daily.csv"
    markets=pd.read_csv(mp) if mp.exists() else pd.DataFrame()
    weather=pd.read_csv(wp) if wp.exists() else pd.DataFrame()
    return markets,weather


def cmd_readiness(args):
    from agriflow.data.repository import DataRepository
    _ensure_dirs(); repo=DataRepository(); prices=repo.load_prices(); mode=repo.data_mode()
    commodities=_scope_commodities(prices,args.commodity,args.target_count)
    markets,weather=_empirical_optional_inputs(mode)
    policy=ReadinessPolicy(
        min_span_days=args.min_span_days,
        min_states=args.min_states,
        min_markets=args.min_markets,
        min_observations=args.min_observations,
        min_arrival_availability=args.min_arrivals,
        min_coordinate_coverage=args.min_coordinates,
        min_weather_market_coverage=args.min_weather,
    )
    report=empirical_readiness(prices,markets,weather,commodities,args.start,args.end,policy)
    out=settings.output_dir/"empirical_readiness.json"
    out.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    rows=pd.DataFrame(report["gates"])
    rows.to_csv(settings.output_dir/"empirical_readiness.csv",index=False)
    print(f"Empirical readiness: {report['status']}")
    print(rows[["gate","status","value","threshold"]].to_string(index=False))
    print(f"Wrote {out}")


def cmd_freeze(args):
    from agriflow.data.repository import DataRepository
    _ensure_dirs(); repo=DataRepository(); prices=repo.load_prices(); mode=repo.data_mode()
    commodities=_scope_commodities(prices,args.commodity,args.target_count)
    markets,weather=_empirical_optional_inputs(mode)
    policy=ReadinessPolicy(
        min_span_days=args.min_span_days,
        min_states=args.min_states,
        min_markets=args.min_markets,
        min_observations=args.min_observations,
        min_arrival_availability=args.min_arrivals,
        min_coordinate_coverage=args.min_coordinates,
        min_weather_market_coverage=args.min_weather,
    )
    try:
        provenance_candidates=[
            settings.raw_dir/"ceda_catalog_commodities.csv",
            settings.raw_dir/"ceda_catalog_geographies.csv",
            settings.raw_dir/"ingest_provenance.jsonl",
            settings.raw_dir/"ceda_chunks"/"_last_run_summary.json",
            settings.raw_dir/"power_chunks"/"_last_run_summary.json",
            settings.processed_dir/"power_market_cells.csv",
            settings.cache_dir/"india_states.source.json",
            settings.output_dir/"commodity_scope_selection.json",
            settings.output_dir/"coordinate_import_audit.csv",
            settings.root/"docs"/"16_DATA_SOURCE_REGISTER.md",
        ]
        path,manifest=freeze_scope(
            prices,markets,weather,commodities,args.start,args.end,
            settings.output_dir/"freezes",label=args.label,
            allow_demo_for_testing=args.allow_demo_for_testing,policy=policy,
            provenance_files=provenance_candidates,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Frozen scope: {path}")
    print(f"Readiness status: {manifest['readiness_status']}")
    print("Integrity manifest: freeze_manifest.json + SHA256SUMS.txt")


def cmd_verify_freeze(args):
    result=verify_freeze(Path(args.path))
    print(json.dumps(result,indent=2))
    if not result["ok"]:
        raise SystemExit(2)


def cmd_analyze_freeze(args):
    try:
        results,summary=analyze_frozen_scope(
            Path(args.path),
            max_lag_days=settings.max_lag_days,
            min_overlap_days=settings.min_overlap_days,
            min_edge_corr=settings.min_edge_corr,
            fdr_alpha=settings.fdr_alpha,
            max_network_markets=settings.max_network_markets,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Frozen-run analysis complete: {results}")
    for commodity,row in summary["commodities"].items():
        leader=(row.get("top_full_period_price_leader") or {}).get("market","—")
        print(f"  {commodity}: {row['lead_lag_edges']} significant edges; top full-period leader={leader}")


def cmd_doctor(args):
    """Offline environment/data readiness report; never prints credential values."""
    from agriflow.data.repository import DataRepository
    _ensure_dirs(); repo=DataRepository()
    report={
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "python":sys.version.split()[0],
        "credentials":{
            "ceda_api_key_configured":bool(settings.ceda_api_key),
            "data_gov_api_key_configured":bool(settings.data_gov_api_key),
        },
        "files":{},
        "recommendations":[],
    }
    real_path=settings.processed_dir/"market_daily.csv"
    report["files"]["market_daily"]=real_path.exists()
    report["files"]["markets"]= (settings.processed_dir/"markets.csv").exists()
    report["files"]["weather_daily"]= (settings.processed_dir/"weather_daily.csv").exists()
    if real_path.exists():
        prices=repo.load_prices()
        report["data_mode"]=repo.data_mode()
        tiers=sorted(split_tiers(prices.get("source_tier",pd.Series(dtype=str)).fillna("").astype(str)))
        report["source_tiers"]=tiers
        report["observations"]=int(len(prices))
        report["states"]=int(prices.state.nunique())
        report["markets"]=int(prices.market_id.nunique())
        report["commodities"]=int(prices.commodity.nunique())
        report["date_min"]=str(pd.to_datetime(prices.date).min().date())
        report["date_max"]=str(pd.to_datetime(prices.date).max().date())
        if not tiers:
            report["recommendations"].append("Re-import/rebuild the dataset so every observation has a source_tier.")
        if any(t not in {PRIMARY_OFFICIAL,CURATED_OFFICIAL_DERIVED} for t in tiers):
            report["recommendations"].append("Current REAL data includes a source tier that is blocked from final-paper freeze; replace it with official OGD/CEDA evidence before reporting claims.")
    else:
        report["data_mode"]="DEMO"
        if not settings.ceda_api_key and not settings.data_gov_api_key:
            report["recommendations"].append("No REAL market dataset or API credential is configured. Obtain a free CEDA/data.gov.in key, or manually download an official CEDA/OGD CSV and use import-ceda-csv or import-data-gov-csv.")
    market_path=settings.processed_dir/"markets.csv"
    if market_path.exists():
        m=pd.read_csv(market_path)
        report["coordinate_coverage"]=round(float(m[["lat","lon"]].notna().all(axis=1).mean()),6) if len(m) and {"lat","lon"}.issubset(m.columns) else 0.0
    weather_path=settings.processed_dir/"weather_daily.csv"
    if weather_path.exists():
        w=pd.read_csv(weather_path)
        report["weather_rows"]=int(len(w))
        report["weather_markets"]=int(w.get("market_id",pd.Series(dtype=str)).nunique())
    freeze_root=settings.output_dir/"freezes"
    dirs=sorted([p for p in freeze_root.glob("*") if p.is_dir()],reverse=True) if freeze_root.exists() else []
    if dirs:
        check=verify_freeze(dirs[0])
        report["latest_freeze"]={"path":str(dirs[0].relative_to(settings.root)),"integrity_ok":bool(check["ok"])}
    out=settings.output_dir/"doctor_report.json"
    out.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    print(json.dumps(report,indent=2,default=str))
    print(f"Wrote {out}")


def cmd_analyze(args):
    from agriflow.data.repository import DataRepository
    repo=DataRepository(); prices=repo.load_prices(); mode=repo.data_mode()
    _ensure_dirs()
    manifest={
        "project":"AgriFlow", "generated_at_utc":datetime.now(timezone.utc).isoformat(), "data_mode":mode,
        "warning":"DEMO outputs are synthetic software-verification fixtures and are not empirical findings." if mode=="DEMO" else "REAL outputs depend on the provenance of imported/fetched source files.",
        "source_tiers":sorted(split_tiers(prices.get("source_tier",pd.Series(dtype=str)).fillna("").astype(str))),
        "analysis_settings":{"max_lag_days":settings.max_lag_days,"min_overlap_days":settings.min_overlap_days,"min_edge_corr":settings.min_edge_corr,"fdr_alpha":settings.fdr_alpha,"max_network_markets":settings.max_network_markets}
    }
    (settings.output_dir/"run_manifest.json").write_text(json.dumps(manifest,indent=2,default=str))
    q=quality_summary(prices); (settings.output_dir/"quality_summary.json").write_text(json.dumps(q,indent=2,default=str))
    audit=coverage_audit(prices);audit.to_csv(settings.output_dir/"coverage_audit.csv",index=False)
    commodity_coverage_score(audit).to_csv(settings.output_dir/"commodity_coverage_ranking.csv",index=False)
    write_selection_report(prices,settings.output_dir,SelectionPolicy())
    detect_market_crunches(prices).to_csv(settings.output_dir/"market_crunch_candidates.csv",index=False)
    for commodity in sorted(prices.commodity.unique()):
        edges=infer_lead_lag_edges(prices,commodity,settings.max_lag_days,settings.min_overlap_days,settings.min_edge_corr,settings.fdr_alpha,settings.max_network_markets)
        edges.to_csv(settings.output_dir/f"lead_lag_{commodity.lower().replace(' ','_')}.csv",index=False)
        influence_scores(edges).to_csv(settings.output_dir/f"influence_{commodity.lower().replace(' ','_')}.csv",index=False)
        market_integration_pairs(prices,commodity,edges,settings.min_overlap_days).to_csv(settings.output_dir/f"integration_{commodity.lower().replace(' ','_')}.csv",index=False)
        pairs=distance_similarity(prices,DataRepository().load_markets(),commodity,settings.min_overlap_days)
        pairs.to_csv(settings.output_dir/f"distance_pairs_{commodity.lower().replace(' ','_')}.csv",index=False)
        (settings.output_dir/f"distance_summary_{commodity.lower().replace(' ','_')}.json").write_text(json.dumps(distance_effect_summary(pairs),indent=2,default=str))
        try:
            joined=join_market_weather(prices[prices.commodity.eq(commodity)],DataRepository().load_weather())
            wes=event_study(joined)
            wes.to_csv(settings.output_dir/f"weather_events_{commodity.lower().replace(' ','_')}.csv",index=False)
            event_study_summary(wes).to_csv(settings.output_dir/f"weather_event_summary_{commodity.lower().replace(' ','_')}.csv",index=False)
        except Exception as exc:
            (settings.output_dir/f"weather_events_{commodity.lower().replace(' ','_')}.error.txt").write_text(str(exc))
    print(f"Analysis exports generated in {settings.output_dir} [{mode} mode]")


def cmd_run(args):
    from agriflow.ui.app import run
    run()


def build_parser():
    p=argparse.ArgumentParser(prog="agriflow",description="AgriFlow data-science pipeline and dashboard")
    sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("init",help="Generate deterministic demo data and optionally cache state GeoJSON");s.add_argument("--no-geojson",dest="geojson",action="store_false");s.set_defaults(func=cmd_init,geojson=True)
    s=sub.add_parser("fetch-current",help="Fetch current AGMARKNET observations from data.gov.in");s.add_argument("--state");s.add_argument("--commodity");s.add_argument("--max-records",type=int,default=5000);s.set_defaults(func=cmd_fetch_current)
    s=sub.add_parser("import-prices",help="Import a generic mandi CSV with explicit provenance");s.add_argument("path");s.add_argument("--source",default="USER_IMPORT");s.add_argument("--source-tier",choices=[USER_SUPPLIED,SECONDARY_MIRROR],default=USER_SUPPLIED,help="Generic imports can only be USER_SUPPLIED or SECONDARY_MIRROR; both are blocked from final-paper freezes");s.set_defaults(func=cmd_import)
    s=sub.add_parser("import-ceda-csv",help="Import a manually downloaded CEDA Agri-Market portal CSV as curated official-derived data");s.add_argument("path");s.add_argument("--state");s.add_argument("--district");s.add_argument("--market");s.add_argument("--commodity");s.set_defaults(func=cmd_import_ceda_csv)
    s=sub.add_parser("import-data-gov-csv",help="Import a manually downloaded official data.gov.in AGMARKNET CSV");s.add_argument("path");s.add_argument("--state");s.add_argument("--district");s.add_argument("--market");s.add_argument("--commodity");s.set_defaults(func=cmd_import_data_gov_csv)
    s=sub.add_parser("ceda-catalog",help="Validate CEDA credentials and cache commodity/geography catalogs");s.set_defaults(func=cmd_ceda_catalog)
    s=sub.add_parser("fetch-ceda",help="Resumable historical market-level CEDA ingestion")
    s.add_argument("--commodity",action="append",required=True,help="Commodity name; repeat or comma-separate")
    s.add_argument("--state",action="append",help="State/UT name; omit for all catalog states")
    s.add_argument("--start",required=True,help="YYYY-MM-DD")
    s.add_argument("--end",required=True,help="YYYY-MM-DD")
    s.add_argument("--district-limit",type=int,help="Validation-only cap per state")
    s.add_argument("--target-count",type=int,default=10,help="Number of coverage-ranked commodities to flag")
    s.add_argument("--no-quantities",action="store_true",help="Fetch prices only")
    s.add_argument("--dry-run",action="store_true",help="Show planned jobs without network calls")
    s.add_argument("--force",action="store_true",help="Refetch completed checkpoint jobs")
    s.add_argument("--fail-fast",action="store_true",help="Abort on first failed API job")
    s.set_defaults(func=cmd_fetch_ceda)
    s=sub.add_parser("scope-audit",help="Rank and select commodities from observed coverage")
    s.add_argument("--target-count",type=int,default=10)
    s.add_argument("--min-states",type=int,default=8)
    s.add_argument("--min-markets",type=int,default=40)
    s.add_argument("--min-observations",type=int,default=2000)
    s.add_argument("--min-density",type=float,default=0.08)
    s.add_argument("--min-arrivals",type=float,default=0.20)
    s.add_argument("--min-span-days",type=int,default=365)
    s.set_defaults(func=cmd_scope_audit)
    s=sub.add_parser("fetch-geojson",help="Download/cache India state GeoJSON with provenance and open fallback");s.add_argument("--provider",choices=["auto","nic","geoboundaries"],default="auto");s.set_defaults(func=cmd_geo)
    s=sub.add_parser("import-coordinates",help="Merge a reviewed market coordinate CSV into markets.csv");s.add_argument("path");s.add_argument("--source",default="USER_REVIEWED_COORDINATES");s.add_argument("--quality",default="imported_reviewed");s.set_defaults(func=cmd_import_coordinates)
    s=sub.add_parser("geocode-markets",help="Small policy-limited Nominatim helper; not intended for pan-India bulk geocoding");s.add_argument("--limit",type=int,default=20);s.add_argument("--max-requests",type=int,default=50);s.add_argument("--delay",type=float,default=1.1);s.add_argument("--accept-nominatim-policy",dest="accept_policy",action="store_true");s.set_defaults(func=cmd_geocode)
    s=sub.add_parser("fetch-weather",help="Resumable NASA POWER weather ingestion at source-grid resolution");s.add_argument("--start",required=True);s.add_argument("--end",required=True);s.add_argument("--dry-run",action="store_true");s.add_argument("--force",action="store_true");s.add_argument("--fail-fast",action="store_true");s.set_defaults(func=cmd_weather)
    s=sub.add_parser("readiness-audit",help="Audit a proposed empirical paper scope before freezing")
    s.add_argument("--commodity",action="append",help="Commodity name; repeat/comma-separate. Omit to use coverage recommendations.")
    s.add_argument("--target-count",type=int,default=10);s.add_argument("--start",required=True);s.add_argument("--end",required=True)
    s.add_argument("--min-span-days",type=int,default=365);s.add_argument("--min-states",type=int,default=3);s.add_argument("--min-markets",type=int,default=8);s.add_argument("--min-observations",type=int,default=500);s.add_argument("--min-arrivals",type=float,default=.20);s.add_argument("--min-coordinates",type=float,default=.70);s.add_argument("--min-weather",type=float,default=.60)
    s.set_defaults(func=cmd_readiness)
    s=sub.add_parser("freeze-scope",help="Snapshot exact paper inputs with readiness report and SHA-256 integrity hashes")
    s.add_argument("--commodity",action="append",help="Commodity name; repeat/comma-separate. Omit to use coverage recommendations.")
    s.add_argument("--target-count",type=int,default=10);s.add_argument("--start",required=True);s.add_argument("--end",required=True);s.add_argument("--label")
    s.add_argument("--allow-demo-for-testing",action="store_true",help="Permit a DEMO freeze for software verification only; never for empirical reporting")
    s.add_argument("--min-span-days",type=int,default=365);s.add_argument("--min-states",type=int,default=3);s.add_argument("--min-markets",type=int,default=8);s.add_argument("--min-observations",type=int,default=500);s.add_argument("--min-arrivals",type=float,default=.20);s.add_argument("--min-coordinates",type=float,default=.70);s.add_argument("--min-weather",type=float,default=.60)
    s.set_defaults(func=cmd_freeze)
    s=sub.add_parser("verify-freeze",help="Recompute and verify all hashes in a frozen empirical snapshot");s.add_argument("path");s.set_defaults(func=cmd_verify_freeze)
    s=sub.add_parser("analyze-freeze",help="Run paper-oriented analyses and temporal robustness checks on a frozen snapshot");s.add_argument("path");s.set_defaults(func=cmd_analyze_freeze)
    s=sub.add_parser("doctor",help="Report local credentials, source tiers, data coverage and empirical prerequisites without network calls");s.set_defaults(func=cmd_doctor)
    s=sub.add_parser("analyze",help="Generate reproducible exploratory analytical CSV outputs");s.set_defaults(func=cmd_analyze)
    s=sub.add_parser("run",help="Launch local dashboard");s.set_defaults(func=cmd_run)
    return p


def main(argv=None):
    args=build_parser().parse_args(argv);args.func(args)

if __name__=="__main__": main()
