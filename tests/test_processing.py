import pandas as pd

from agriflow.data.processing import (
    aggregate_market_daily,
    merge_market_daily,
    normalize_prices,
    quality_summary,
)


def test_normalize_and_invalid_order():
    df=pd.DataFrame([{'arrival_date':'2024-01-01','state':' X ','district':'D','market':'M','commodity':'Onion','variety':'A','grade':'FAQ','min_price':'2500','modal_price':'2000','max_price':'2300','arrivals':'10'}])
    out=normalize_prices(df)
    assert out.iloc[0].state=='X'
    assert pd.isna(out.iloc[0].min_price) and pd.isna(out.iloc[0].max_price)


def test_aggregate_market_daily_median_and_sum():
    df=pd.DataFrame([
        {'date':'2024-01-01','state':'S','district':'D','market':'M','commodity':'C','variety':'A','grade':'G','min_price':90,'max_price':110,'modal_price':100,'arrivals':10,'source':'X','data_mode':'REAL'},
        {'date':'2024-01-01','state':'S','district':'D','market':'M','commodity':'C','variety':'B','grade':'G','min_price':190,'max_price':210,'modal_price':200,'arrivals':20,'source':'X','data_mode':'REAL'}])
    out=aggregate_market_daily(normalize_prices(df))
    assert out.iloc[0].modal_price==150
    assert out.iloc[0].arrivals==30
    assert out.iloc[0].varieties==2


def test_quality_summary(small_prices):
    q=quality_summary(small_prices)
    assert q['rows']==240 and q['markets']==3 and q['commodities']==1


def test_state_alias_and_dayfirst_date():
    df=pd.DataFrame([{'date':'23/09/2026','state':'NCT of Delhi','district':'D','market':'M','commodity':'Onion','modal_price':2000}])
    out=normalize_prices(df)
    assert out.iloc[0].state=='Delhi'
    assert out.iloc[0].date==pd.Timestamp('2026-09-23')


def test_repeated_market_day_arrival_total_is_not_double_counted():
    rows=pd.DataFrame([
        {'date':'2024-01-01','state':'S','district':'D','market':'M','commodity':'C',
         'variety':'A','modal_price':100,'arrivals':25,'arrival_unit':'tonne'},
        {'date':'2024-01-01','state':'S','district':'D','market':'M','commodity':'C',
         'variety':'B','modal_price':110,'arrivals':25,'arrival_unit':'tonne'},
    ])
    out=aggregate_market_daily(normalize_prices(rows))
    assert out.iloc[0].arrivals==25
    assert out.iloc[0].arrival_unit=='tonne'


def test_mixed_arrival_units_are_not_aggregated():
    rows=pd.DataFrame([
        {'date':'2024-01-01','state':'S','district':'D','market':'M','commodity':'C',
         'variety':'A','modal_price':100,'arrivals':25,'arrival_unit':'tonne'},
        {'date':'2024-01-01','state':'S','district':'D','market':'M','commodity':'C',
         'variety':'B','modal_price':110,'arrivals':2,'arrival_unit':'quintal'},
    ])
    out=aggregate_market_daily(normalize_prices(rows))
    assert pd.isna(out.iloc[0].arrivals)
    assert out.iloc[0].arrival_unit.startswith('MIXED:')


def test_merge_market_daily_preserves_distinct_rows_and_prefers_authority():
    existing=pd.DataFrame([
        {'date':'2024-01-01','state':'S','district':'D','market':'M','market_id':'s__d__m',
         'commodity':'C','modal_price':100,'source_tier':'PRIMARY_OFFICIAL'},
        {'date':'2024-01-02','state':'S','district':'D','market':'M','market_id':'s__d__m',
         'commodity':'C','modal_price':101,'source_tier':'PRIMARY_OFFICIAL'},
    ])
    incoming=pd.DataFrame([
        {'date':'2024-01-01','state':'S','district':'D','market':'M','market_id':'s__d__m',
         'commodity':'C','modal_price':999,'source_tier':'USER_SUPPLIED'},
        {'date':'2024-01-03','state':'S','district':'D','market':'M','market_id':'s__d__m',
         'commodity':'C','modal_price':102,'source_tier':'USER_SUPPLIED'},
    ])
    out=merge_market_daily(existing,incoming)
    assert len(out)==3
    assert out.loc[out.date.eq('2024-01-01'),'modal_price'].iloc[0]==100
