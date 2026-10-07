from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from dash import Dash, Input, Output, State, dcc, html, dash_table, no_update

from agriflow.config import settings
from agriflow.data.repository import DataRepository
from agriflow.data.processing import quality_summary
from agriflow.analytics.coverage import coverage_audit
from agriflow.analytics.selection import commodity_scope_table, SelectionPolicy
from agriflow.analytics.lead_lag import infer_lead_lag_edges
from agriflow.analytics.network import influence_scores
from agriflow.analytics.geography import distance_similarity, distance_effect_summary
from agriflow.analytics.integration import market_integration_pairs
from agriflow.analytics.weather import join_market_weather, event_study, event_study_summary
from agriflow.analytics.events import detect_market_crunches, detect_price_shocks
from agriflow.analytics.supply_price import supply_price_stats
from agriflow.visualization.figures import (
    price_trend, arrivals_price_scatter, coverage_heatmap, state_map, network_figure,
    influence_bar, distance_scatter, weather_price_figure, weather_event_response_figure, crunch_table_figure, ripple_figure,
)

repo = DataRepository()
PRICES = repo.load_prices()
WEATHER = repo.load_weather()
MARKETS = repo.load_markets()
MODE = repo.data_mode()
AUDIT = coverage_audit(PRICES)
SCOPE = commodity_scope_table(PRICES, SelectionPolicy())
GEOJSON = settings.cache_dir / "india_states.geojson"


def _options(values):
    return [{"label": str(v), "value": str(v)} for v in values]


def _market_options(frame: pd.DataFrame):
    cols=[c for c in ["market_id","market","district","state"] if c in frame.columns]
    m=frame[cols].drop_duplicates("market_id").sort_values(["state","district","market"])
    return [{"label": f"{r.market} — {r.district}, {r.state}", "value": r.market_id} for _,r in m.iterrows()]


def _card(title, body):
    return html.Div([html.Div(title, className="label"), html.Div(body, className="value")], className="kpi")


def _filter(commodity: str, state: str, start_date, end_date) -> pd.DataFrame:
    x = PRICES[PRICES.commodity.eq(commodity)].copy()
    if state and state != "All India": x = x[x.state.eq(state)]
    if start_date: x = x[x.date >= pd.Timestamp(start_date)]
    if end_date: x = x[x.date <= pd.Timestamp(end_date)]
    return x


def create_app() -> Dash:
    app = Dash(__name__, assets_folder=str(settings.assets_dir), title="AgriFlow", suppress_callback_exceptions=True)
    commodities = sorted(PRICES.commodity.unique())
    states = ["All India"] + sorted(PRICES.state.unique())
    default_commodity = "Onion" if "Onion" in commodities else commodities[0]
    min_date, max_date = PRICES.date.min(), PRICES.date.max()
    mode_class = "mode-badge mode-real" if MODE == "REAL" else "mode-badge mode-demo"

    app.layout = html.Div(className="app-shell", children=[
        html.Div(className="topbar", children=[
            html.Div(className="brand", children=[
                html.H1("AgriFlow"),
                html.P("Spatiotemporal analysis of mandi price transmission, weather shocks and market integration across India")
            ]),
            html.Div(f"{MODE} DATA", className=mode_class, id="mode-badge")
        ]),
        html.Div(className="control-row", children=[
            html.Div(className="control-card", children=[html.Label("Commodity"), dcc.Dropdown(id="commodity", options=_options(commodities), value=default_commodity, clearable=False)]),
            html.Div(className="control-card", children=[html.Label("State"), dcc.Dropdown(id="state", options=_options(states), value="All India", clearable=False)]),
            html.Div(className="control-card", children=[html.Label("Market"), dcc.Dropdown(id="market", clearable=False)]),
            html.Div(className="control-card", children=[html.Label("Date range"), dcc.DatePickerRange(id="dates", min_date_allowed=min_date.date(), max_date_allowed=max_date.date(), start_date=min_date.date(), end_date=max_date.date(), display_format="DD MMM YYYY")]),
        ]),
        html.Div(id="kpis", className="kpis"),
        dcc.Tabs(id="tabs", value="overview", className="dash-tabs", children=[
            dcc.Tab(label="Overview", value="overview"),
            dcc.Tab(label="India Map", value="map"),
            dcc.Tab(label="Market Influence", value="influence"),
            dcc.Tab(label="Weather & Crunch", value="weather"),
            dcc.Tab(label="Geography", value="geography"),
            dcc.Tab(label="Data Quality", value="quality"),
            dcc.Tab(label="Research Status", value="research"),
            dcc.Tab(label="Methods & Sources", value="methods"),
        ]),
        html.Div(id="tab-content", className="tab-content"),
        dcc.Store(id="selected-map-state"),
    ])

    @app.callback(Output("market","options"), Output("market","value"), Input("commodity","value"), Input("state","value"))
    def update_markets(commodity, state):
        x = PRICES[PRICES.commodity.eq(commodity)]
        if state != "All India": x = x[x.state.eq(state)]
        opts = _market_options(x) if len(x) else []
        vals = [o["value"] for o in opts]
        return opts, (vals[0] if vals else None)

    @app.callback(Output("state","value"), Input("selected-map-state","data"), prevent_initial_call=True)
    def apply_map_state(data):
        if data and data in set(PRICES.state): return data
        return no_update

    @app.callback(Output("kpis","children"), Input("commodity","value"), Input("state","value"), Input("dates","start_date"), Input("dates","end_date"))
    def kpis(commodity,state,start,end):
        x=_filter(commodity,state,start,end)
        return [
            _card("Observations", f"{len(x):,}"),
            _card("Markets", f"{(x.market_id.nunique() if 'market_id' in x else x.market.nunique()):,}"),
            _card("Median modal price", f"₹{x.modal_price.median():,.0f}/q" if len(x) else "—"),
            _card("Date coverage", f"{x.date.min():%d %b %Y} – {x.date.max():%d %b %Y}" if len(x) else "—"),
        ]

    @app.callback(Output("tab-content","children"), Input("tabs","value"), Input("commodity","value"), Input("state","value"), Input("market","value"), Input("dates","start_date"), Input("dates","end_date"))
    def render_tab(tab, commodity, state, market, start, end):
        x=_filter(commodity,state,start,end)
        if tab == "overview":
            stats=supply_price_stats(x)
            assoc = "Insufficient data" if stats["spearman_rho"] is None else f"Spearman ρ={stats['spearman_rho']:.2f}; log-log β={stats['loglog_beta']:.2f} (n={stats['n']:,})"
            return html.Div([
                html.Div("Interpretation guardrail: values on this dashboard are descriptive/statistical. Price leadership and weather effects are not claims of causation.", className="academic-note"),
                html.Div(className="grid-2", children=[html.Div(dcc.Graph(figure=price_trend(x,commodity,state)),className="card"),html.Div(dcc.Graph(figure=arrivals_price_scatter(x,commodity,state)),className="card")]),
                html.Div(className="grid-2", children=[html.Div(dcc.Graph(figure=coverage_heatmap(AUDIT,commodity)),className="card"),html.Div([html.H3("Supply–price association"),html.P(assoc),html.P("The elasticity estimate is associative and does not identify a causal supply curve.",className="section-note")],className="card")])
            ])
        if tab == "map":
            return html.Div([
                html.Div("Click a state polygon when the official GeoJSON cache is available. The global state selector and linked views will update.", className="section-note"),
                html.Div(dcc.Graph(id="india-map", figure=state_map(x,MARKETS,commodity,GEOJSON), style={"height":"650px"}, config={"toImageButtonOptions":{"format":"svg","filename":f"agriflow_{commodity.lower()}_india_state_map"}}), className="card"),
                html.Div(className="grid-2", children=[html.Div(dcc.Graph(figure=price_trend(x,commodity,state)),className="card"),html.Div(dcc.Graph(figure=coverage_heatmap(AUDIT,commodity)),className="card")])
            ])
        if tab == "influence":
            edges=infer_lead_lag_edges(x,commodity,settings.max_lag_days,settings.min_overlap_days,settings.min_edge_corr,settings.fdr_alpha,settings.max_network_markets)
            scores=influence_scores(edges)
            leader = scores.iloc[0].market_id if len(scores) else (market or "")
            shocks=detect_price_shocks(x,commodity)
            leader_shocks=shocks[shocks.market_id.eq(leader)] if not shocks.empty and leader else shocks.iloc[0:0]
            event_date = (leader_shocks.iloc[0].date.date().isoformat() if len(leader_shocks) else (x.date.max().date().isoformat() if len(x) else None))
            leader_options=[{"label":r.market,"value":r.market_id} for _,r in scores.iterrows()] if len(scores) else _market_options(x)
            return html.Div([
                html.Div("Directed edges require daily-return association, temporal precedence, minimum overlap and FDR-adjusted significance. Source-oriented PageRank is calculated on the reversed graph so followers are not mislabeled as leaders. Edges remain candidate transmission relationships, not causal routes.",className="academic-note"),
                html.Div(className="grid-2",children=[html.Div(dcc.Graph(figure=network_figure(edges,MARKETS,scores),style={"height":"600px"},config={"toImageButtonOptions":{"format":"svg","filename":f"agriflow_{commodity.lower()}_leadership_network"}}),className="card"),html.Div(dcc.Graph(figure=influence_bar(scores)),className="card")]),
                html.Div(className="card",children=[html.H3("Price-shock ripple explorer"),html.Div(className="grid-3",children=[
                    html.Div([html.Label("Leader market"),dcc.Dropdown(id="ripple-leader",options=leader_options,value=leader,clearable=False)]),
                    html.Div([html.Label("Baseline date"),dcc.DatePickerSingle(id="ripple-date",date=event_date,min_date_allowed=x.date.min().date() if len(x) else None,max_date_allowed=x.date.max().date() if len(x) else None)]),
                    html.Div([html.Label("Show inferred lags up to (days)"),dcc.Slider(id="ripple-lag",min=1,max=settings.max_lag_days,step=1,value=min(3,settings.max_lag_days),marks={i:str(i) for i in range(1,settings.max_lag_days+1)})])
                ]),dcc.Graph(id="ripple-graph",figure=ripple_figure(x,edges,MARKETS,commodity,leader,event_date,min(3,settings.max_lag_days)),style={"height":"600px"},config={"toImageButtonOptions":{"format":"svg","filename":f"agriflow_{commodity.lower()}_ripple"}})]),
                dash_table.DataTable(data=edges.head(200).round({"corr":3,"p_value":4,"q_value":4}).to_dict("records"),columns=[{"name":c,"id":c} for c in edges.columns],page_size=12,style_table={"overflowX":"auto"},style_header={"fontWeight":"700","backgroundColor":"#E9EEE9"})
            ])
        if tab == "weather":
            joined=join_market_weather(x,WEATHER)
            events=detect_market_crunches(x)
            es=event_study(joined)
            es_sum=event_study_summary(es)
            seven=es_sum[es_sum.horizon_days.eq(7)] if not es_sum.empty else es_sum
            es_summary = "No qualifying declustered weather events." if seven.empty else "; ".join(f"{r.event_sign} anomaly: median +7d price {r.median_price_change_pct:+.1f}% (n={int(r.n)})" for _,r in seven.iterrows())
            return html.Div([
                html.Div("Weather is spatial context, not proof of causality. NASA POWER is gridded MERRA-2-based meteorology; extreme weather days are declustered before the descriptive event study. IMD is retained as the official Indian rainfall reference path.",className="academic-note"),
                html.Div(className="grid-2",children=[html.Div(dcc.Graph(figure=weather_price_figure(joined,market,commodity)),className="card"),html.Div(dcc.Graph(figure=weather_event_response_figure(es_sum)),className="card")]),
                html.Div(className="grid-2",children=[html.Div(dcc.Graph(figure=crunch_table_figure(events)),className="card"),html.Div([html.H3("Weather event-study summary"),html.P(es_summary),html.P("A market crunch is separately flagged when robust arrival collapse and price surge thresholds coincide. Neither screen establishes causality.",className="section-note")],className="card")])
            ])
        if tab == "geography":
            pairs=distance_similarity(x,MARKETS,commodity,settings.min_overlap_days); summary=distance_effect_summary(pairs)
            edges=infer_lead_lag_edges(x,commodity,settings.max_lag_days,settings.min_overlap_days,settings.min_edge_corr,settings.fdr_alpha,settings.max_network_markets)
            integ=market_integration_pairs(x,commodity,edges,settings.min_overlap_days)
            text="Insufficient market pairs." if summary["spearman_rho"] is None else f"Across {summary['pairs']} market pairs, Spearman ρ(distance, return correlation) = {summary['spearman_rho']:.3f}. QAP-style label-permutation p={summary['qap_p_value']:.3g} (conventional pairwise p={summary['p_value']:.3g}, shown only as a secondary diagnostic)."
            table = dash_table.DataTable(data=integ.head(15).round(3).to_dict("records"),columns=[{"name":c.replace("_"," ").title(),"id":c} for c in integ.columns],page_size=10,style_table={"overflowX":"auto"},style_header={"fontWeight":"700","backgroundColor":"#E9EEE9"}) if not integ.empty else html.P("Insufficient data for pairwise integration scores.")
            return html.Div([html.Div("Distance is great-circle distance, not road distance or transport cost. Because market-pair observations are not independent, the dashboard reports a QAP-style label-permutation significance check for distance decay. The integration score remains an exploratory composite and must be read with its component metrics.",className="academic-note"),html.Div(dcc.Graph(figure=distance_scatter(pairs)),className="card"),html.Div(className="grid-2",children=[html.Div([html.H3("Distance-effect statistic"),html.P(text)],className="card"),html.Div([html.H3("Most integrated market pairs"),table],className="card")])])
        if tab == "research":
            freeze_root=settings.output_dir/"freezes"
            dirs=sorted([p for p in freeze_root.glob("*") if p.is_dir()],reverse=True) if freeze_root.exists() else []
            if not dirs:
                return html.Div([
                    html.Div("No empirical scope has been frozen yet. Exploratory dashboard views remain useful, but final-paper claims should be generated only from a verified freeze.",className="academic-note"),
                    html.Div([html.H3("Required empirical gate"),html.P("Run readiness-audit, review all WARN/FAIL gates, then use freeze-scope. The freeze records exact commodity/date scope, data provenance, coordinate/weather coverage and SHA-256 hashes.")],className="card")
                ])
            latest=dirs[0]
            try:
                manifest=json.loads((latest/"freeze_manifest.json").read_text(encoding="utf-8"))
                readiness=json.loads((latest/"readiness.json").read_text(encoding="utf-8"))
                gates=pd.DataFrame(readiness.get("gates",[]))
                gate_table=dash_table.DataTable(data=gates.to_dict("records"),columns=[{"name":c.replace("_"," ").title(),"id":c} for c in gates.columns],page_size=12,style_table={"overflowX":"auto"},style_header={"fontWeight":"700","backgroundColor":"#E9EEE9"}) if not gates.empty else html.P("No gate details available.")
                scope=manifest.get("scope",{})
                return html.Div([
                    html.Div(f"Latest frozen scope: {latest.name}. Status: {manifest.get('readiness_status','unknown')}. Frozen inputs are checksum-protected; rerun verify-freeze before using results in the paper.",className="academic-note"),
                    html.Div(className="grid-3",children=[_card("Frozen commodities",str(len(scope.get("commodities",[])))),_card("Start",scope.get("start_date","—")),_card("End",scope.get("end_date","—"))]),
                    html.Div([html.H3("Readiness gates"),gate_table],className="card"),
                    html.Div([html.H3("Academic integrity"),html.P(manifest.get("academic_integrity","")),html.P("A frozen run is reproducible evidence; it is not itself proof of causality. Network/weather interpretation guardrails still apply.",className="section-note")],className="card")
                ])
            except Exception as exc:
                return html.Div(f"Latest freeze metadata could not be read: {exc}",className="academic-note")
        if tab == "quality":
            q=quality_summary(PRICES)
            qa=pd.DataFrame([q])
            scope_cols=[c for c in ["commodity","states","markets","observations","span_days","median_state_density","arrival_availability","coverage_score","eligible","recommended"] if c in SCOPE.columns]
            scope_view=SCOPE[scope_cols].head(20).copy() if not SCOPE.empty else pd.DataFrame()
            for c in ["median_state_density","arrival_availability","coverage_score"]:
                if c in scope_view: scope_view[c]=scope_view[c].round(3)
            scope_table = dash_table.DataTable(
                data=scope_view.to_dict("records"),
                columns=[{"name":c.replace("_"," ").title(),"id":c} for c in scope_cols],
                page_size=10,style_table={"overflowX":"auto"},
                style_header={"fontWeight":"700","backgroundColor":"#E9EEE9"}
            ) if not scope_view.empty else html.P("No commodity scope audit is available.")
            return html.Div([
                html.Div(className="grid-2",children=[html.Div(dcc.Graph(figure=coverage_heatmap(AUDIT)),className="card"),html.Div([html.H3("Dataset quality summary"),dash_table.DataTable(data=qa.to_dict("records"),columns=[{"name":c.replace("_"," ").title(),"id":c} for c in qa.columns],style_header={"fontWeight":"700","backgroundColor":"#E9EEE9"})],className="card")]),
                html.Div([html.H3("Commodity scope audit"),html.P("The final empirical basket is selected from observed state, market, temporal-density and arrival coverage; score components remain visible for auditability.",className="section-note"),scope_table],className="card"),
                html.Div("Missing reports are never converted to zero. Invalid min/modal/max order is removed from min/max comparisons. Network inference does not bridge non-consecutive reporting gaps.",className="academic-note")
            ])
        return html.Div(className="method-grid",children=[
            html.Div([html.H3("Market data"),html.P("Government of India OGD/AGMARKNET daily price resource; CEDA Agri Market Data historical price/quantity pathway; imports are accepted when API access changes.")],className="card"),
            html.Div([html.H3("Weather"),html.P("NASA POWER Daily API for reproducible historical precipitation/temperature at its meteorological source-grid resolution; IMD rainfall is retained as the official Indian reference path. POWER downloads are checkpointed by grid cell and year.")],className="card"),
            html.Div([html.H3("Lead–lag inference"),html.P("Daily log-price returns, lags 1–7 days by default, minimum aligned overlap, Pearson effect size, Benjamini–Hochberg FDR correction, then directed influence graph.")],className="card"),
            html.Div([html.H3("Geography"),html.P("State boundaries are cached as vector GeoJSON with a provenance sidecar: NIC/BharatMaps is attempted when accessible, with geoBoundaries gbOpen ADM1 (CC BY 4.0) as the reproducible open fallback. Market-pair distance uses the Haversine great-circle formula and is not a transport-cost measure.")],className="card"),
            html.Div([html.H3("Market coordinates"),html.P("Reviewed coordinate imports are preferred. Public OSMF Nominatim is available only as a small, explicit opt-in helper with caching/rate safeguards; it is not used as an unattended pan-India bulk geocoder.")],className="card"),
            html.Div([html.H3("Academic integrity"),html.P("DEMO observations are deterministic synthetic fixtures for software verification only. REAL results must be regenerated from public-source data before inclusion in the final paper.")],className="card"),
            html.Div([html.H3("Project documentation"),html.P("See docs/ for SRS, data specification, analytics specification, architecture, test plan, risk register, traceability matrix and IEEE report outline.")],className="card"),
        ])

    @app.callback(Output("selected-map-state","data"), Input("india-map","clickData"), prevent_initial_call=True)
    def map_click(click):
        if not click or not click.get("points"): return no_update
        p=click["points"][0]
        # Choropleth exposes location; scatter fallback exposes hovertext.
        val=p.get("location") or p.get("hovertext") or p.get("text")
        return val if val in set(PRICES.state) else no_update

    @app.callback(Output("ripple-graph","figure"), Input("ripple-leader","value"),Input("ripple-date","date"),Input("ripple-lag","value"),State("commodity","value"),State("state","value"),State("dates","start_date"),State("dates","end_date"),prevent_initial_call=True)
    def update_ripple(leader,event_date,lag,commodity,state,start,end):
        x=_filter(commodity,state,start,end)
        edges=infer_lead_lag_edges(x,commodity,settings.max_lag_days,settings.min_overlap_days,settings.min_edge_corr,settings.fdr_alpha,settings.max_network_markets)
        return ripple_figure(x,edges,MARKETS,commodity,leader,event_date,lag)

    return app


def run() -> None:
    app=create_app()
    app.run(host=settings.host,port=settings.port,debug=settings.debug)
