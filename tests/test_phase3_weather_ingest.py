from pathlib import Path
import pandas as pd

from agriflow.data.weather_ingest import PowerHistoricalIngestor, power_cell


class FakePower:
    def fetch_daily(self, lat, lon, start_date, end_date):
        return pd.DataFrame([{
            'date':pd.Timestamp(start_date),'rainfall_mm':5.0,'temperature_c':25.0,
            'temperature_max_c':30.0,'temperature_min_c':20.0,'lat':lat,'lon':lon,
            'source':'NASA_POWER','data_mode':'REAL'
        }])


def test_power_cell_coarsens_nearby_points():
    assert power_cell(20.11,74.10)==power_cell(20.14,74.12)


def test_power_ingestor_checkpoints_and_rebuilds(tmp_path: Path):
    markets=pd.DataFrame([
        {'state':'Maharashtra','district':'Nashik','market':'A','lat':20.11,'lon':74.10},
        {'state':'Maharashtra','district':'Nashik','market':'B','lat':20.14,'lon':74.12},
    ])
    ing=PowerHistoricalIngestor(FakePower(),tmp_path/'raw',tmp_path/'processed')
    jobs=ing.plan(markets,'2024-01-01','2024-12-31')
    assert len(jobs)==1
    first=ing.run(jobs); second=ing.run(jobs)
    assert first['fetched']==1 and second['cached']==1
    out,path=ing.rebuild_processed(markets)
    assert path.exists()
    assert out.market_id.nunique()==2
    assert out.rainfall_mm.eq(5.0).all()
