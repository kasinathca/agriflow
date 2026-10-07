from __future__ import annotations
import numpy as np
import pandas as pd
import networkx as nx


def _edge_ids(e: pd.Series) -> tuple[str, str]:
    return str(e.get("leader_id", e["leader"])), str(e.get("follower_id", e["follower"]))


def build_graph(edges: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, e in edges.iterrows():
        leader_id, follower_id = _edge_ids(e)
        g.add_node(leader_id, label=str(e.get("leader", leader_id)))
        g.add_node(follower_id, label=str(e.get("follower", follower_id)))
        g.add_edge(
            leader_id,
            follower_id,
            weight=abs(float(e["corr"])),
            corr=float(e["corr"]),
            lag_days=int(e.lag_days),
            q_value=float(e.q_value),
            overlap=int(e.get("overlap", 0)),
        )
    return g


def influence_scores(edges: pd.DataFrame) -> pd.DataFrame:
    """Rank *upstream* price leaders.

    Standard PageRank on leader→follower edges rewards nodes receiving links and can
    therefore rank followers highly. We intentionally run PageRank on the reversed
    graph (`source_pagerank`) so upstream transmitters receive the source-centrality
    contribution. The composite remains exploratory and exposes all components.
    """
    g = build_graph(edges)
    cols = [
        "market_id", "market", "source_pagerank", "pagerank", "out_strength",
        "betweenness", "lead_consistency", "outbound_edges", "median_overlap",
        "influence_score",
    ]
    if g.number_of_nodes() == 0:
        return pd.DataFrame(columns=cols)
    source_pr = nx.pagerank(g.reverse(copy=False), weight="weight")
    btw = nx.betweenness_centrality(g, weight=None, normalized=True)
    out_strength = {n: sum(d.get("weight", 1) for _, _, d in g.out_edges(n, data=True)) for n in g.nodes}
    consistency = {}
    outbound_edges = {}
    median_overlap = {}
    for n in g.nodes:
        ds = [d for _, _, d in g.out_edges(n, data=True)]
        consistency[n] = float(np.mean([1 / max(1, d.get("lag_days", 1)) for d in ds])) if ds else 0.0
        outbound_edges[n] = len(ds)
        overlaps = [d.get("overlap", 0) for d in ds if d.get("overlap", 0)]
        median_overlap[n] = float(np.median(overlaps)) if overlaps else 0.0
    frame = pd.DataFrame({"market_id": list(g.nodes)})
    frame["market"] = frame.market_id.map(lambda n: g.nodes[n].get("label", n))
    mappings = [
        ("source_pagerank", source_pr),
        ("out_strength", out_strength),
        ("betweenness", btw),
        ("lead_consistency", consistency),
    ]
    for name, mapping in mappings:
        frame[name] = frame.market_id.map(mapping).fillna(0.0)
        mx = frame[name].max()
        frame[f"_{name}"] = frame[name] / mx if mx > 0 else 0.0
    frame["outbound_edges"] = frame.market_id.map(outbound_edges).fillna(0).astype(int)
    frame["median_overlap"] = frame.market_id.map(median_overlap).fillna(0.0)
    # Compatibility alias: now explicitly source-oriented rather than sink-oriented PageRank.
    frame["pagerank"] = frame["source_pagerank"]
    frame["influence_score"] = (
        0.35 * frame._source_pagerank
        + 0.35 * frame._out_strength
        + 0.20 * frame._betweenness
        + 0.10 * frame._lead_consistency
    )
    drop = [c for c in frame.columns if c.startswith("_")]
    return frame.drop(columns=drop)[cols].sort_values("influence_score", ascending=False).reset_index(drop=True)
