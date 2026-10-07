from pathlib import Path
import pandas as pd

from agriflow.data.ceda_ingest import CedaHistoricalIngestor


class FakeCeda:
    def list_commodities(self):
        return [{'commodity_id':1,'commodity_name':'Onion'}]
    def list_geographies(self):
        return [
            {'census_state_id':27,'census_state_name':'Maharashtra','census_district_id':1,'census_district_name':'Nashik'},
            {'census_state_id':27,'census_state_name':'Maharashtra','census_district_id':2,'census_district_name':'Pune'},
        ]
    def resolve_commodity(self,name):
        return self.list_commodities()[0]
    def resolve_state(self,name):
        return {'census_state_id':27,'census_state_name':'Maharashtra'}
    def districts_for_state(self,state_id):
        return self.list_geographies()
    def canonical_market_chunk(self,commodity,state,district,start_date,end_date,include_quantities=True):
        if district['census_district_id']==2:
            return pd.DataFrame()
        return pd.DataFrame([{
            'date':'2024-01-02','state':'Maharashtra','district':'Nashik','market':'Lasalgaon',
            'commodity':'Onion','variety':'','grade':'','min_price':100,'max_price':150,'modal_price':125,
            'arrivals':20,'source':'CEDA_AGMARKNET','data_mode':'REAL','source_commodity_id':1,
            'source_state_id':27,'source_district_id':1,'source_market_id':10,
        }])


def test_resumable_ingestor_checkpoints_and_rebuilds(tmp_path: Path):
    ing=CedaHistoricalIngestor(FakeCeda(),tmp_path/'raw',tmp_path/'processed')
    jobs=ing.plan(['Onion'],'2024-01-01','2024-12-31',states=['Maharashtra'])
    assert len(jobs)==2
    first=ing.run(jobs)
    assert first['fetched']==2
    assert first['empty']==1
    second=ing.run(jobs)
    assert second['cached']==2
    daily,out=ing.rebuild_processed()
    assert out.exists()
    assert len(daily)==1
    assert daily.iloc[0].market=='Lasalgaon'
    assert daily.iloc[0].arrivals==20
