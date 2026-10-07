from agriflow.data.sources.data_gov import DataGovMandiSource
from agriflow.data.sources.nasa_power import NasaPowerSource

class Fake:
    def __init__(self,payload):self.payload=payload;self.last=None
    def request_json(self,method,url,**kwargs):self.last=(method,url,kwargs);return self.payload


def test_data_gov_params():
    f=Fake({'records':[{'state':'Maharashtra'}]})
    s=DataGovMandiSource('key',client=f)
    d=s.fetch_page(state='Maharashtra',commodity='Onion')
    params=f.last[2]['params']
    assert params['api-key']=='key'
    assert params['filters[state.keyword]']=='Maharashtra'
    assert params['filters[commodity]']=='Onion'
    assert d['records'][0]['state']=='Maharashtra'


def test_nasa_power_parse():
    f=Fake({'properties':{'parameter':{'PRECTOTCORR':{'20240101':4.2},'T2M':{'20240101':26.5},'T2M_MAX':{'20240101':31},'T2M_MIN':{'20240101':20}}}})
    s=NasaPowerSource(client=f)
    df=s.fetch_daily(20,75,'2024-01-01','2024-01-01')
    assert df.iloc[0].rainfall_mm==4.2
    assert df.iloc[0].temperature_c==26.5

from agriflow.data.sources.ceda import CedaHistoricalSource, year_windows


def test_ceda_current_contract_and_bearer_header():
    payload={'output':{'type':'success','data':[{'commodity_id':1,'commodity_name':'Onion'}]}}
    f=Fake(payload)
    s=CedaHistoricalSource('secret-token',client=f)
    rows=s.list_commodities()
    assert rows[0]['commodity_name']=='Onion'
    method,url,kwargs=f.last
    assert method=='GET'
    assert url.endswith('/v1/agmarknet/commodities')
    assert kwargs['headers']['Authorization']=='Bearer secret-token'


def test_ceda_prices_payload_uses_id_lists():
    f=Fake({'output':{'type':'success','data':[]}})
    s=CedaHistoricalSource('key',client=f)
    s.fetch_prices(7,27,'2024-01-01','2024-12-31',district_ids=[101],market_ids=[9001,9002])
    body=f.last[2]['json']
    assert body['commodity_id']==7
    assert body['state_id']==27
    assert body['district_id']==[101]
    assert body['market_id']==[9001,9002]
    assert body['from_date']=='2024-01-01'


def test_year_windows_split_cleanly():
    assert year_windows('2023-12-30','2025-01-02') == [
        ('2023-12-30','2023-12-31'),
        ('2024-01-01','2024-12-31'),
        ('2025-01-01','2025-01-02'),
    ]

class RoutingFake:
    def __init__(self):
        self.calls=[]
    def request_json(self,method,url,**kwargs):
        self.calls.append((method,url,kwargs))
        if url.endswith('/agmarknet/markets'):
            return {'output':{'type':'success','data':[{'market_id':10,'market_name':'Lasalgaon'}]}}
        if url.endswith('/agmarknet/prices'):
            return {'output':{'type':'success','data':[{
                'date':'2024-01-02T00:00:00','commodity_id':1,'census_state_id':27,
                'census_district_id':1,'market_id':10,'min_price':100,'max_price':160,'modal_price':130
            }]}}
        if url.endswith('/agmarknet/quantities'):
            return {'output':{'type':'success','data':[{
                'date':'2024-01-02T00:00:00','commodity_id':1,'census_state_id':27,
                'census_district_id':1,'market_id':10,'quantity':42.5
            }]}}
        raise AssertionError(url)


def test_ceda_canonical_market_chunk_merges_quantity():
    s=CedaHistoricalSource('key',client=RoutingFake())
    out=s.canonical_market_chunk(
        {'commodity_id':1,'commodity_name':'Onion'},
        {'census_state_id':27,'census_state_name':'Maharashtra'},
        {'census_state_id':27,'census_state_name':'Maharashtra','census_district_id':1,'census_district_name':'Nashik'},
        '2024-01-01','2024-01-31',include_quantities=True,
    )
    assert len(out)==1
    assert out.iloc[0].market=='Lasalgaon'
    assert out.iloc[0].commodity=='Onion'
    assert out.iloc[0].arrivals==42.5
    assert out.iloc[0].data_mode=='REAL'
