from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from agriflow.forecasting import pipeline


def sample_panel(markets: int = 3, periods: int = 180) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=periods, freq="D")
    rows = []
    for market_number in range(markets):
        for index, date in enumerate(dates):
            rows.append({
                "date": date,
                "state": "Maharashtra",
                "district": f"District {market_number}",
                "market": f"Market {market_number}",
                "market_id": f"market_{market_number}",
                "commodity": "Onion",
                "modal_price": 1000 + market_number * 50 + index * 2 + 30 * np.sin(index / 8),
                "source": "TEST_OFFICIAL",
                "source_tier": "CURATED_OFFICIAL_DERIVED",
                "data_mode": "REAL",
            })
    return pd.DataFrame(rows)


def test_panel_is_sorted_chronologically_and_has_no_duplicate_targets():
    panel = sample_panel().sample(frac=1, random_state=1)
    features, _ = pipeline.build_features(panel)
    assert not features.duplicated(["date", "market_id", "commodity"]).any()
    assert features.equals(features.sort_values(["date", "market_id"]).reset_index(drop=True))


def test_missing_and_nonpositive_prices_are_removed():
    panel = sample_panel()
    panel.loc[0, "modal_price"] = np.nan
    panel.loc[1, "modal_price"] = 0
    _, audit = pipeline.build_features(panel)
    assert audit["invalid_rows_removed"] == 2


def test_insufficient_market_history_is_reported():
    panel = pd.concat([sample_panel(markets=1), sample_panel(markets=1, periods=40).assign(market="Short", market_id="short")])
    _, audit = pipeline.build_features(panel)
    assert "short" in audit["excluded_markets"]


def test_features_are_isolated_by_market_and_backward_looking():
    panel = sample_panel(markets=2)
    features, _ = pipeline.build_features(panel)
    first = features[features.market_id.eq("market_0")].iloc[0]
    source = panel[panel.market_id.eq("market_0")].sort_values("date")
    target_position = source.index[source.date.eq(first.date)][0]
    ordered = source.reset_index(drop=True)
    position = ordered.index[ordered.date.eq(first.date)][0]
    assert first.lag_1 == pytest.approx(ordered.iloc[position - 1].modal_price)
    assert first.lag_7 == pytest.approx(ordered.iloc[position - 7].modal_price)
    assert first.rolling_mean_3 == pytest.approx(ordered.iloc[position - 3:position].modal_price.mean())
    assert first.lag_1 != sample_panel(markets=2).query("market_id == 'market_1'").iloc[position - 1].modal_price
    assert target_position >= 0


def test_temporal_split_uses_shared_date_boundaries():
    features, _ = pipeline.build_features(sample_panel())
    split = pipeline.temporal_split(features)
    assert split.train.date.max() <= split.train_end
    assert split.validation.date.min() > split.train_end
    assert split.test.date.min() > split.validation_end
    assert set(split.train.market_id) == set(split.test.market_id)


def test_all_six_models_produce_predictions_on_identical_cohort():
    features, _ = pipeline.build_features(sample_panel())
    split = pipeline.temporal_split(features)
    fitted = {}
    for name, estimator in pipeline._estimators().items():
        estimator.fit(split.train[pipeline.FEATURE_COLUMNS], split.train[pipeline.TARGET])
        fitted[name] = estimator
    metrics, predictions = pipeline._evaluate_partition(split.test, fitted)
    assert set(metrics.model) == set(pipeline.MODEL_SPECS)
    assert predictions.groupby("model").size().nunique() == 1


def test_models_are_reproducible_and_serializable(tmp_path):
    features, _ = pipeline.build_features(sample_panel())
    split = pipeline.temporal_split(features)
    first = pipeline._estimators()["M4 Random Forest"]
    second = pipeline._estimators()["M4 Random Forest"]
    first.fit(split.train[pipeline.FEATURE_COLUMNS], split.train.modal_price)
    second.fit(split.train[pipeline.FEATURE_COLUMNS], split.train.modal_price)
    expected = first.predict(split.test[pipeline.FEATURE_COLUMNS])
    assert np.allclose(expected, second.predict(split.test[pipeline.FEATURE_COLUMNS]))
    path = tmp_path / "model.joblib"
    joblib.dump(first, path)
    assert np.allclose(expected, joblib.load(path).predict(split.test[pipeline.FEATURE_COLUMNS]))


def test_metric_definitions_match_known_values():
    metrics = pipeline.compute_metrics([100, 200, 300], [110, 190, 330], [90, 210, 290])
    assert metrics["mae"] == pytest.approx(50 / 3)
    assert metrics["mse"] == pytest.approx(1100 / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt(1100 / 3))
    assert metrics["median_absolute_error"] == pytest.approx(10)
    assert metrics["mean_bias_error"] == pytest.approx(10)
    assert metrics["directional_accuracy_pct"] == pytest.approx(100)
    assert metrics["r2"] < 1
    assert metrics["mape_pct"] > 0
    assert metrics["smape_pct"] > 0
    assert metrics["wape_pct"] > 0


def test_percentage_metrics_handle_zero_denominators():
    metrics = pipeline.compute_metrics([0, 0], [0, 1], [0, 0])
    assert metrics["mape_pct"] is None
    assert metrics["wape_pct"] is None
    assert metrics["smape_pct"] == pytest.approx(200)


def test_latest_inference_matches_feature_order():
    panel = sample_panel(markets=1)
    features = pipeline._latest_feature_row(panel)
    assert list(features.columns) == pipeline.FEATURE_COLUMNS
    forecasts = pipeline.forecast_latest(panel, "M0 Persistence", None, ["market_0"])
    assert forecasts.iloc[0].predicted_next_report_price == pytest.approx(panel.iloc[-1].modal_price)


def test_end_to_end_training_writes_real_artifacts(tmp_path):
    prices = tmp_path / "prices.csv"
    output = tmp_path / "forecasting"
    sample_panel().to_csv(prices, index=False)
    metadata = pipeline.run_training(prices, output)
    required = [
        "model_comparison.csv", "validation_metrics.csv", "test_predictions.csv",
        "latest_forecasts.csv", "selected_model.json", "forecast_model.joblib",
        "dataset_manifest.json", "metric_definitions.json", "forecasting_methodology.md",
    ]
    assert all((output / name).exists() for name in required)
    comparison = pd.read_csv(output / "model_comparison.csv")
    assert len(comparison) == 6
    assert metadata["selected_model"] == comparison.sort_values(["validation_mae", "validation_rmse", "model"]).iloc[0].model
    predictions = pd.read_csv(output / "test_predictions.csv")
    assert predictions.groupby("model").size().nunique() == 1
    assert len(list((output / "figures").glob("*.html"))) == 4


def test_dataset_manifest_preserves_unit_and_provenance(tmp_path):
    prices = tmp_path / "prices.csv"
    output = tmp_path / "forecasting"
    sample_panel().to_csv(prices, index=False)
    pipeline.run_training(prices, output)
    manifest = json.loads((output / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["price_unit"] == "INR per quintal"
    assert manifest["source_tier"] == "CURATED_OFFICIAL_DERIVED"


def test_cli_and_dashboard_expose_forecasting():
    from agriflow.cli import build_parser
    from agriflow.ui.app import create_app

    assert build_parser().parse_args(["train-forecast"]).command == "train-forecast"
    app = create_app()
    labels = [tab.label for tab in app.layout.children[3].children]
    assert "Forecasting" in labels


def test_missing_dashboard_artifacts_return_helpful_state(monkeypatch, tmp_path):
    import agriflow.ui.app as dashboard

    monkeypatch.setattr(dashboard, "FORECAST_DIR", Path(tmp_path))
    assert dashboard._load_forecast_view() is None
