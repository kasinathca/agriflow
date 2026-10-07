import pandas as pd
from agriflow.analytics.network import build_graph, influence_scores


def test_influence_leader_outscores_leaf():
    edges=pd.DataFrame([
        {'leader':'A','follower':'B','lag_days':1,'corr':.7,'q_value':.01},
        {'leader':'A','follower':'C','lag_days':2,'corr':.6,'q_value':.02},
        {'leader':'B','follower':'C','lag_days':1,'corr':.4,'q_value':.03},])
    g=build_graph(edges); assert g.number_of_edges()==3
    s=influence_scores(edges).set_index('market')
    assert s.loc['A','out_strength']>s.loc['C','out_strength']
    assert s.loc['A','influence_score']>s.loc['C','influence_score']
