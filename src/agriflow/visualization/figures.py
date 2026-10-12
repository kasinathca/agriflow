from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from agriflow.analytics.events import ripple_snapshot
from agriflow.data.identity import ensure_market_id
from agriflow.data.names import canonical_state
from agriflow.visualization.theme import (
    GOLD,
    GREEN,
    GRID,
    MUTED,
    NAVY,
    PLOTLY_LAYOUT,
    TEAL,
    WHITE,
)

GEO_STATE_PROPERTY_CANDIDATES = (
    "STNAME", "st_nm", "state", "STATE", "NAME_1", "shapeName", "name"
)


def detect_geo_state_property(geojson: dict, data_states: set[str] | None = None) -> str:
    """Return the most plausible ADM1 name property in a GeoJSON collection."""
    features = geojson.get("features") if isinstance(geojson, dict) else None
    if not isinstance(features, list) or not features:
        raise ValueError("GeoJSON has no features")
    properties = [
        feature.get("properties", {})
        for feature in features
        if isinstance(feature, dict) and isinstance(feature.get("properties"), dict)
    ]
    if not properties:
        raise ValueError("GeoJSON features have no properties")

    actual_keys = {str(key).lower(): str(key) for props in properties for key in props}
    candidates = [
        actual_keys[name.lower()]
        for name in GEO_STATE_PROPERTY_CANDIDATES
        if name.lower() in actual_keys
    ]
    if not candidates:
        raise ValueError("GeoJSON has no supported state-name property")

    wanted = {canonical_state(value) for value in (data_states or set()) if canonical_state(value)}

    def score(key: str) -> tuple[int, int, int]:
        values = [canonical_state(props.get(key)) for props in properties]
        nonempty = {value for value in values if value}
        matches = len(nonempty & wanted) if wanted else 0
        priority = -next(
            i for i, name in enumerate(GEO_STATE_PROPERTY_CANDIDATES)
            if name.lower() == key.lower()
        )
        return matches, len(nonempty), priority

    selected = max(candidates, key=score)
    if wanted and score(selected)[0] == 0:
        raise ValueError("GeoJSON state names do not match the selected mandi data")
    return selected


def _signed_ring_area(ring: list) -> float:
    if len(ring) < 3:
        return 0.0
    return sum(
        float(ring[i][0]) * float(ring[(i + 1) % len(ring)][1])
        - float(ring[(i + 1) % len(ring)][0]) * float(ring[i][1])
        for i in range(len(ring))
    ) / 2


def _rewind_plotly_geometry(geometry: dict) -> None:
    """Use clockwise exteriors so d3/Plotly does not render polygon complements."""
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    for polygon in polygons:
        for index, ring in enumerate(polygon):
            area = _signed_ring_area(ring)
            should_reverse = (index == 0 and area > 0) or (index > 0 and area < 0)
            if should_reverse:
                ring.reverse()


def prepare_state_geojson(geojson: dict, data_states: set[str]) -> tuple[dict, str]:
    """Validate a state GeoJSON and add canonical IDs used by Plotly."""
    state_property = detect_geo_state_property(geojson, data_states)
    prepared = json.loads(json.dumps(geojson))
    usable = 0
    matched = 0
    wanted = {canonical_state(value) for value in data_states if canonical_state(value)}
    for feature in prepared.get("features", []):
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        _rewind_plotly_geometry(geometry)
        name = canonical_state(feature["properties"].get(state_property))
        if not name:
            continue
        feature["properties"]["AGRIFLOW_STATE"] = name
        usable += 1
        matched += int(name in wanted)
    if not usable:
        raise ValueError("GeoJSON has no usable Polygon or MultiPolygon state features")
    if not matched:
        raise ValueError("GeoJSON contains no state polygons matching the selected mandi data")
    return prepared, state_property


def _finish(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT)
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, xanchor="left", font=dict(size=16, color=NAVY)))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color=MUTED))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return _finish(fig)


def price_trend(df: pd.DataFrame, commodity: str, state: str | None = None) -> go.Figure:
    x = df[df.commodity.eq(commodity)].copy()
    if state and state != "All India": x = x[x.state.eq(state)]
    if x.empty: return empty_figure("No price observations for the current filters.")
    y = x.groupby("date", as_index=False).modal_price.median()
    fig = px.line(y, x="date", y="modal_price")
    fig.update_traces(line=dict(color=GREEN, width=2.3), hovertemplate="%{x|%d %b %Y}<br>Median modal price: ₹%{y:,.0f}/q<extra></extra>")
    fig.update_yaxes(title="Median modal price (₹/quintal)"); fig.update_xaxes(title=None)
    return _finish(fig, f"{commodity} price trend" + (f" — {state}" if state and state != "All India" else ""))


def arrivals_price_scatter(df: pd.DataFrame, commodity: str, state: str | None = None) -> go.Figure:
    x = df[df.commodity.eq(commodity)].dropna(subset=["arrivals","modal_price"]).copy()
    if state and state != "All India": x=x[x.state.eq(state)]
    if x.empty: return empty_figure("Arrival quantity is unavailable for this selection.")
    sample = x.sample(min(len(x), 2500), random_state=24) if len(x)>2500 else x
    fig = px.scatter(sample, x="arrivals", y="modal_price", color="market", hover_data=["date","state"], opacity=.48)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title="Arrivals (source-normalized quantity)")
    fig.update_yaxes(title="Modal price (₹/quintal)")
    return _finish(fig, "Arrivals versus modal price")


def coverage_heatmap(audit: pd.DataFrame, commodity: str | None = None) -> go.Figure:
    x=audit.copy()
    if commodity: x=x[x.commodity.eq(commodity)]
    if x.empty: return empty_figure("Coverage audit has no rows.")
    if commodity:
        x=x.sort_values("reporting_density")
        fig=px.bar(x, x="reporting_density", y="state", orientation="h", hover_data=["observations","markets","arrival_availability"])
        fig.update_traces(marker_color=TEAL)
        fig.update_xaxes(title="Reporting density", tickformat=".0%")
        fig.update_yaxes(title=None)
        return _finish(fig, f"Reporting coverage — {commodity}")
    pivot=x.pivot_table(index="state",columns="commodity",values="reporting_density",aggfunc="mean")
    fig=px.imshow(pivot, aspect="auto", color_continuous_scale="YlGnBu", zmin=0,zmax=1, labels=dict(color="Density"))
    return _finish(fig,"State × commodity reporting density")


def state_map(df: pd.DataFrame, markets: pd.DataFrame, commodity: str, geojson_path: Path | None = None) -> go.Figure:
    x=df[df.commodity.eq(commodity)].copy()
    if x.empty: return empty_figure("No state values for this commodity.")
    x["state"] = x["state"].map(canonical_state)
    market_col="market_id" if "market_id" in x.columns else "market"
    state=x.groupby("state",as_index=False).agg(modal_price=("modal_price","median"), markets=(market_col,"nunique"), observations=("modal_price","size"))
    if geojson_path and geojson_path.exists():
        try:
            geo=json.loads(geojson_path.read_text(encoding="utf-8"))
            geo, _ = prepare_state_geojson(geo, set(state["state"]))
            fig=px.choropleth(state, geojson=geo, locations="state", featureidkey="properties.AGRIFLOW_STATE", color="modal_price",
                              color_continuous_scale="YlGnBu", hover_data={"markets":True,"observations":True,"modal_price":":,.0f"})
            # Keep a stable national frame even when the current REAL dataset has
            # observations for only one state. Linked panels may still drill down.
            fig.update_geos(visible=False, center=dict(lat=22.5, lon=79), projection_scale=3.7)
            fig.update_layout(coloraxis_colorbar_title="₹/q")
            return _finish(fig, f"Median {commodity} price by state — click a state to drill down")
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            pass
    required = {"state", "lat", "lon"}
    if markets.empty or not required.issubset(markets.columns):
        return empty_figure("State boundary map is unavailable and no fallback coordinates exist.")
    market_coords = markets.copy()
    market_coords["state"] = market_coords["state"].map(canonical_state)
    coords=market_coords.groupby("state",as_index=False).agg(lat=("lat","mean"),lon=("lon","mean"))
    state=state.merge(coords,on="state",how="left").dropna(subset=["lat","lon"])
    if state.empty:
        return empty_figure("State boundary map is unavailable and no matching fallback coordinates exist.")
    fig=px.scatter_geo(state,lat="lat",lon="lon",size="markets",color="modal_price",hover_name="state",
                       hover_data={"markets":True,"observations":True,"modal_price":":,.0f","lat":False,"lon":False},
                       color_continuous_scale="YlGnBu",scope="asia")
    fig.update_geos(center=dict(lat=22.5,lon=79),projection_scale=4.2,showcountries=True,countrycolor=GRID,showland=True,landcolor="#EEF2EE")
    fig.update_layout(coloraxis_colorbar_title="₹/q")
    return _finish(fig, f"{commodity} state overview (GeoJSON fallback mode)")


def network_figure(edges: pd.DataFrame, markets: pd.DataFrame, scores: pd.DataFrame) -> go.Figure:
    if edges.empty: return empty_figure("No significant lead–lag edges meet the current thresholds.")
    m=ensure_market_id(markets)
    coords=m.dropna(subset=["lat","lon"]).drop_duplicates("market_id").set_index("market_id")
    fig=go.Figure()
    for _,e in edges.iterrows():
        a_id=e.get("leader_id",e.leader); b_id=e.get("follower_id",e.follower)
        if a_id not in coords.index or b_id not in coords.index: continue
        a,b=coords.loc[a_id],coords.loc[b_id]
        fig.add_trace(go.Scattergeo(lon=[a.lon,b.lon],lat=[a.lat,b.lat],mode="lines",
                                    line=dict(width=0.7+2.5*abs(float(e["corr"])),color="rgba(43,122,120,.45)"),
                                    hoverinfo="text",text=f"{e.leader} → {e.follower}<br>lag {int(e.lag_days)} d · r={e['corr']:.2f} · q={e.q_value:.3g}",showlegend=False))
    node=scores.merge(m.drop_duplicates("market_id")[["market_id","state","district","lat","lon"]],on="market_id",how="left").dropna(subset=["lat","lon"])
    if not node.empty:
        fig.add_trace(go.Scattergeo(lon=node.lon,lat=node.lat,mode="markers+text",text=node.market,textposition="top center",
                                    customdata=np.stack([node.state,node.influence_score,node.outbound_edges],axis=-1),
                                    hovertemplate="%{text}<br>%{customdata[0]}<br>Influence %{customdata[1]:.3f}<br>Outbound significant edges %{customdata[2]:.0f}<extra></extra>",
                                    marker=dict(size=10+28*node.influence_score,color=node.influence_score,colorscale="YlGnBu",line=dict(width=1,color=WHITE),colorbar=dict(title="Influence")),showlegend=False))
    if not fig.data:
        return empty_figure("Significant lead–lag edges exist, but market coordinates are unavailable.")
    fig.update_geos(center=dict(lat=22.5,lon=79),projection_scale=4.2,showcountries=True,countrycolor=GRID,showland=True,landcolor="#F3F5F2")
    return _finish(fig,"Statistically inferred price-leadership network")


def influence_bar(scores: pd.DataFrame, top_n: int=10) -> go.Figure:
    if scores.empty: return empty_figure("No influence scores available.")
    x=scores.head(top_n).sort_values("influence_score")
    fig=px.bar(x,x="influence_score",y="market",orientation="h",hover_data=["source_pagerank","out_strength","betweenness","lead_consistency","outbound_edges","median_overlap"])
    fig.update_traces(marker_color=GREEN); fig.update_yaxes(title=None); fig.update_xaxes(title="Composite influence score")
    return _finish(fig,"Potential price-leader markets")


def distance_scatter(pairs: pd.DataFrame) -> go.Figure:
    if pairs.empty: return empty_figure("Insufficient coordinate/aligned-return coverage for distance analysis.")
    fig=px.scatter(pairs,x="distance_km",y="return_corr",color="distance_bin",hover_data=["market_a","market_b","overlap"],opacity=.65)
    fig.add_hline(y=0,line_width=1,line_dash="dot",line_color=MUTED)
    fig.update_xaxes(title="Great-circle distance (km)");fig.update_yaxes(title="Daily return correlation")
    return _finish(fig,"Geographic distance versus price co-movement")


def weather_price_figure(joined: pd.DataFrame, market_id: str, commodity: str) -> go.Figure:
    x=ensure_market_id(joined)
    x=x[(x.market_id.eq(market_id)) & (x.commodity.eq(commodity))].sort_values("date")
    required={"rainfall_mm","temperature_c"}
    if x.empty or not required.issubset(x.columns) or not x[list(required)].notna().any().any():
        return empty_figure("REAL weather observations are unavailable for this market.")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=x.date,y=x.modal_price,name="Modal price",line=dict(color=GREEN,width=2),yaxis="y"))
    fig.add_trace(go.Bar(x=x.date,y=x.rainfall_mm,name="Rainfall",marker_color="rgba(43,122,120,.35)",yaxis="y2"))
    fig.add_trace(go.Scatter(x=x.date,y=x.temperature_c,name="Temperature",line=dict(color=GOLD,width=1.3),yaxis="y3"))
    fig.update_layout(yaxis=dict(title="Price (₹/q)"),yaxis2=dict(title="Rain (mm)",overlaying="y",side="right",showgrid=False),
                      yaxis3=dict(title="Temp (°C)",overlaying="y",side="right",anchor="free",position=.92,showgrid=False),legend=dict(orientation="h",y=1.12))
    label=x.market.iloc[0] if len(x) else market_id
    return _finish(fig,f"Weather and price timeline — {label}")


def crunch_table_figure(events: pd.DataFrame, top_n:int=20) -> go.Figure:
    if events.empty: return empty_figure("No market-crunch candidates at the configured thresholds.")
    x=events.head(top_n).copy()
    fig=go.Figure(data=[go.Table(header=dict(values=["Date","Market","Commodity","Price","Arrivals","Price z","Arrival z"],fill_color="#E9EEE9",align="left"),
        cells=dict(values=[x.date.dt.strftime("%Y-%m-%d") if np.issubdtype(x.date.dtype,np.datetime64) else x.date,x.market,x.commodity,x.modal_price.round(0),x.arrivals.round(0),x.price_z.round(2),x.arrival_z.round(2)],align="left"))])
    return _finish(fig,"Detected market-crunch candidates")


def weather_event_response_figure(summary: pd.DataFrame) -> go.Figure:
    if summary.empty: return empty_figure("No declustered weather events meet the configured threshold.")
    fig=px.bar(summary,x="horizon_days",y="median_price_change_pct",color="event_sign",barmode="group",
               hover_data=["n","median_arrival_change_pct"],labels={"horizon_days":"Days after weather event","median_price_change_pct":"Median price response (%)","event_sign":"Weather anomaly sign"})
    fig.add_hline(y=0,line_width=1,line_dash="dot",line_color=MUTED)
    return _finish(fig,"Declustered weather-event price response")


def ripple_figure(df: pd.DataFrame, edges: pd.DataFrame, markets: pd.DataFrame, commodity: str, leader_id: str, event_date: str, horizon: int) -> go.Figure:
    if not leader_id or not event_date: return empty_figure("Choose a leader and shock date to view edge-aligned responses.")
    snap=ripple_snapshot(df,edges,commodity,leader_id,event_date,int(horizon))
    if snap.empty: return empty_figure("No mapped follower responses are observed at the inferred lags within this horizon.")
    m=ensure_market_id(markets).drop_duplicates("market_id").set_index("market_id")
    fig=go.Figure()
    plotted=[]
    for _,r in snap.iterrows():
        if r.leader_id not in m.index or r.follower_id not in m.index: continue
        a,b=m.loc[r.leader_id],m.loc[r.follower_id]
        fig.add_trace(go.Scattergeo(lon=[a.lon,b.lon],lat=[a.lat,b.lat],mode="lines",
            line=dict(width=0.8+2.5*abs(float(r.edge_corr)),color="rgba(23,50,77,.32)"),
            hoverinfo="text",text=f"{r.leader} → {r.follower}<br>inferred lag {int(r.lag_days)} d · r={r.edge_corr:.2f} · q={r.edge_q_value:.3g}",showlegend=False))
        plotted.append(r)
    if not plotted: return empty_figure("Follower responses exist but mapped coordinates are unavailable.")
    node=pd.DataFrame(plotted).merge(m.reset_index()[["market_id","state","lat","lon"]],left_on="follower_id",right_on="market_id",how="left").dropna(subset=["lat","lon"])
    maxabs=max(1,float(node.follower_response_pct.abs().quantile(.95))) if not node.empty else 1
    fig.add_trace(go.Scattergeo(lon=node.lon,lat=node.lat,mode="markers+text",text=node.follower,textposition="top center",
        customdata=np.stack([node.state,node.follower_response_pct,node.lag_days],axis=-1),
        hovertemplate="%{text}<br>%{customdata[0]}<br>Daily response %{customdata[1]:+.1f}%<br>Inferred lag %{customdata[2]:.0f} d<extra></extra>",
        marker=dict(size=12+np.minimum(26,node.follower_response_pct.abs()*2),color=node.follower_response_pct,cmin=-maxabs,cmax=maxabs,colorscale="RdYlGn",reversescale=True,colorbar=dict(title="Follower daily Δ%"),line=dict(width=1,color=WHITE)),showlegend=False))
    if leader_id in m.index:
        a=m.loc[leader_id]; label=snap.iloc[0].leader; shock=snap.iloc[0].leader_shock_pct
        fig.add_trace(go.Scattergeo(lon=[a.lon],lat=[a.lat],mode="markers+text",text=[label],textposition="top center",
            hovertemplate=f"{label}<br>Leader shock {shock:+.1f}%<extra></extra>" if pd.notna(shock) else f"{label}<extra></extra>",
            marker=dict(size=22,symbol="diamond",color=GOLD,line=dict(width=2,color=NAVY)),showlegend=False))
    fig.update_geos(center=dict(lat=22.5,lon=79),projection_scale=4.2,showland=True,landcolor="#F3F5F2",showcountries=True,countrycolor=GRID)
    return _finish(fig,f"Edge-aligned ripple snapshot — {pd.Timestamp(event_date):%d %b %Y}, lags ≤ {horizon} d")

