import pandas as pd

from agriflow.analytics.selection import SelectionPolicy, commodity_scope_table


def _panel():
    rows=[]
    dates=pd.date_range('2024-01-01',periods=30,freq='D')
    for commodity,states,markets in [('Onion',3,3),('Rare Crop',1,1)]:
        for si in range(states):
            for mi in range(markets):
                for d in dates:
                    rows.append({
                        'date':d,'state':f'S{si}','district':f'D{si}','market':f'M{si}_{mi}',
                        'commodity':commodity,'modal_price':100+mi,'min_price':90,'max_price':110,
                        'arrivals':10.0 if commodity=='Onion' else None,'data_mode':'REAL','source':'TEST'
                    })
    return pd.DataFrame(rows)


def test_commodity_scope_selection_prefers_broad_dense_data():
    policy=SelectionPolicy(
        target_count=1,min_states=2,min_markets=3,min_observations=100,
        min_median_state_density=0.5,min_arrival_availability=0.5,min_span_days=20,
    )
    table=commodity_scope_table(_panel(),policy)
    onion=table[table.commodity.eq('Onion')].iloc[0]
    rare=table[table.commodity.eq('Rare Crop')].iloc[0]
    assert bool(onion.eligible)
    assert bool(onion.recommended)
    assert not bool(rare.eligible)
    assert onion.coverage_score > rare.coverage_score
