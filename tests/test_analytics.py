from agriflow.analytics.coverage import coverage_audit, commodity_coverage_score
from agriflow.analytics.dispersion import price_dispersion
from agriflow.analytics.supply_price import supply_price_stats


def test_coverage(small_prices):
    a=coverage_audit(small_prices)
    assert len(a)==2
    assert set(a.state)=={'State 1','State 2'}
    rank=commodity_coverage_score(a)
    assert rank.iloc[0].commodity=='Onion'


def test_dispersion(small_prices):
    d=price_dispersion(small_prices)
    assert len(d)==80
    assert d.markets.min()==3


def test_supply_price_stats_has_values(small_prices):
    s=supply_price_stats(small_prices,min_n=10)
    assert s['n']==240
    assert s['spearman_rho'] is not None
    assert s['loglog_beta'] is not None


def test_integration_score(small_prices):
    from agriflow.analytics.integration import market_integration_pairs
    pairs=market_integration_pairs(small_prices,'Onion',min_overlap=30)
    assert len(pairs)==3
    assert pairs.integration_score.between(0,1).all()
