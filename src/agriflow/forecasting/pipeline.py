from __future__ import annotations

import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from agriflow.config import settings
from agriflow.data.identity import ensure_market_id

RANDOM_SEED = 42
TARGET = "modal_price"
PRICE_UNIT = "INR per quintal"
NUMERIC_FEATURES = [
    "lag_1", "lag_2", "lag_3", "lag_7", "lag_14",
    "rolling_mean_3", "rolling_mean_7", "rolling_mean_14",
    "rolling_std_7", "previous_abs_change", "previous_pct_change",
]
CATEGORICAL_FEATURES = ["market_id"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

MODEL_SPECS: dict[str, dict[str, Any]] = {
    "M0 Persistence": {"type": "baseline", "parameters": "prediction = lag_1"},
    "M1 Lag-7": {"type": "baseline", "parameters": "prediction = lag_7"},
    "M2 Ridge": {"type": "linear", "parameters": "alpha=1.0; standardized numeric features"},
    "M3 Decision Tree": {"type": "tree", "parameters": "max_depth=8; min_samples_leaf=5; random_state=42"},
    "M4 Random Forest": {"type": "ensemble", "parameters": "n_estimators=200; max_depth=12; min_samples_leaf=3; random_state=42"},
    "M5 Hist Gradient Boosting": {"type": "boosting", "parameters": "max_iter=150; learning_rate=0.05; max_leaf_nodes=15; early_stopping=False; random_state=42"},
}


@dataclass(frozen=True)
class SplitData:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    train_end: pd.Timestamp
    validation_end: pd.Timestamp


def _safe_float(value: float) -> float | None:
    return None if not np.isfinite(value) else float(value)


def compute_metrics(y_true, y_pred, previous_price) -> dict[str, float | None]:
    """Compute the ten declared metrics on a common finite cohort."""
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    previous = np.asarray(previous_price, dtype=float)
    valid = np.isfinite(y) & np.isfinite(p) & np.isfinite(previous)
    y, p, previous = y[valid], p[valid], previous[valid]
    if not len(y):
        return {name: None for name in [
            "mae", "mse", "rmse", "r2", "mape_pct", "smape_pct",
            "wape_pct", "median_absolute_error", "mean_bias_error",
            "directional_accuracy_pct",
        ]}
    error = p - y
    absolute = np.abs(error)
    squared = error ** 2
    mae = absolute.mean()
    mse = squared.mean()
    denominator = ((y - y.mean()) ** 2).sum()
    r2 = np.nan if len(y) < 2 or denominator == 0 else 1 - squared.sum() / denominator
    nonzero_y = y != 0
    mape = np.nan if not nonzero_y.any() else 100 * np.mean(absolute[nonzero_y] / np.abs(y[nonzero_y]))
    smape_denominator = np.abs(y) + np.abs(p)
    smape_valid = smape_denominator != 0
    smape = np.nan if not smape_valid.any() else 100 * np.mean(
        2 * absolute[smape_valid] / smape_denominator[smape_valid]
    )
    wape_denominator = np.abs(y).sum()
    wape = np.nan if wape_denominator == 0 else 100 * absolute.sum() / wape_denominator
    actual_direction = np.sign(y - previous)
    predicted_direction = np.sign(p - previous)
    directional = 100 * np.mean(actual_direction == predicted_direction)
    return {
        "mae": _safe_float(mae),
        "mse": _safe_float(mse),
        "rmse": _safe_float(np.sqrt(mse)),
        "r2": _safe_float(r2),
        "mape_pct": _safe_float(mape),
        "smape_pct": _safe_float(smape),
        "wape_pct": _safe_float(wape),
        "median_absolute_error": _safe_float(np.median(absolute)),
        "mean_bias_error": _safe_float(error.mean()),
        "directional_accuracy_pct": _safe_float(directional),
    }


def validate_panel(prices: pd.DataFrame, commodity: str = "Onion") -> tuple[pd.DataFrame, dict[str, int]]:
    required = {"date", "state", "district", "market", "commodity", "modal_price"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Forecasting data is missing required columns: {sorted(missing)}")
    original_rows = len(prices)
    frame = ensure_market_id(prices.copy())
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True).dt.tz_localize(None)
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
    frame = frame[frame["commodity"].astype(str).str.casefold().eq(commodity.casefold())]
    before_invalid = len(frame)
    frame = frame.dropna(subset=["date", "market_id", "modal_price"])
    frame = frame[frame["modal_price"] > 0]
    invalid_rows = before_invalid - len(frame)
    duplicate_rows = int(frame.duplicated(["date", "market_id", "commodity"]).sum())
    frame = frame.drop_duplicates(["date", "market_id", "commodity"], keep="last")
    frame = frame.sort_values(["market_id", "date"]).reset_index(drop=True)
    return frame, {
        "initial_rows": int(original_rows),
        "commodity_rows": int(before_invalid),
        "invalid_rows_removed": int(invalid_rows),
        "duplicate_rows_removed": duplicate_rows,
    }


def build_features(prices: pd.DataFrame, commodity: str = "Onion", min_market_observations: int = 120) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame, audit = validate_panel(prices, commodity)
    counts = frame.groupby("market_id").size()
    eligible = sorted(counts[counts >= min_market_observations].index.tolist())
    excluded = sorted(counts[counts < min_market_observations].index.tolist())
    frame = frame[frame["market_id"].isin(eligible)].copy()
    grouped = frame.groupby("market_id", group_keys=False)["modal_price"]
    for lag in [1, 2, 3, 7, 14]:
        frame[f"lag_{lag}"] = grouped.shift(lag)
    shifted = grouped.shift(1)
    for window in [3, 7, 14]:
        frame[f"rolling_mean_{window}"] = shifted.groupby(frame["market_id"]).transform(
            lambda series, size=window: series.rolling(size, min_periods=size).mean()
        )
    frame["rolling_std_7"] = shifted.groupby(frame["market_id"]).transform(
        lambda series: series.rolling(7, min_periods=7).std(ddof=0)
    )
    frame["previous_abs_change"] = frame["lag_1"] - frame["lag_2"]
    frame["previous_pct_change"] = np.where(
        frame["lag_2"].ne(0), (frame["lag_1"] - frame["lag_2"]) / frame["lag_2"], np.nan
    )
    before_complete = len(frame)
    frame = frame.dropna(subset=FEATURE_COLUMNS + [TARGET]).copy()
    frame = frame[np.isfinite(frame[NUMERIC_FEATURES]).all(axis=1)]
    frame = frame.sort_values(["date", "market_id"]).reset_index(drop=True)
    audit.update({
        "minimum_market_observations": int(min_market_observations),
        "eligible_markets": eligible,
        "excluded_markets": excluded,
        "eligible_market_count": len(eligible),
        "rows_removed_insufficient_lag_history": int(before_complete - len(frame)),
        "modeling_rows": len(frame),
        "feature_count": len(FEATURE_COLUMNS),
    })
    return frame, audit


def temporal_split(frame: pd.DataFrame) -> SplitData:
    dates = np.array(sorted(pd.to_datetime(frame["date"]).unique()))
    if len(dates) < 20:
        raise ValueError("At least 20 unique target dates are required for temporal evaluation.")
    train_idx = max(1, int(np.floor(len(dates) * 0.70)))
    validation_idx = max(train_idx + 1, int(np.floor(len(dates) * 0.85)))
    train_end = pd.Timestamp(dates[train_idx - 1])
    validation_end = pd.Timestamp(dates[validation_idx - 1])
    train = frame[frame.date <= train_end].copy()
    validation = frame[(frame.date > train_end) & (frame.date <= validation_end)].copy()
    test = frame[frame.date > validation_end].copy()
    if min(len(train), len(validation), len(test)) == 0:
        raise ValueError("Temporal split produced an empty partition.")
    return SplitData(train, validation, test, train_end, validation_end)


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric = StandardScaler() if scale else "passthrough"
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("market", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])


def _estimators() -> dict[str, Pipeline]:
    return {
        "M2 Ridge": Pipeline([("preprocess", _preprocessor(True)), ("model", Ridge(alpha=1.0))]),
        "M3 Decision Tree": Pipeline([
            ("preprocess", _preprocessor(False)),
            ("model", DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, random_state=RANDOM_SEED)),
        ]),
        "M4 Random Forest": Pipeline([
            ("preprocess", _preprocessor(False)),
            ("model", RandomForestRegressor(
                n_estimators=200, max_depth=12, min_samples_leaf=3,
                random_state=RANDOM_SEED, n_jobs=-1,
            )),
        ]),
        "M5 Hist Gradient Boosting": Pipeline([
            ("preprocess", _preprocessor(False)),
            ("model", HistGradientBoostingRegressor(
                max_iter=150, learning_rate=0.05, max_leaf_nodes=15,
                random_state=RANDOM_SEED, early_stopping=False,
            )),
        ]),
    }


def _prediction_frame(partition: pd.DataFrame, model_name: str, prediction) -> pd.DataFrame:
    columns = ["date", "market_id", "market", "district", "state", TARGET, "lag_1"]
    out = partition[columns].copy()
    out["model"] = model_name
    out["predicted_price"] = np.asarray(prediction, dtype=float)
    out["residual"] = out["predicted_price"] - out[TARGET]
    return out


def _evaluate_partition(partition: pd.DataFrame, fitted: dict[str, Pipeline]) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions = []
    for name in MODEL_SPECS:
        if name == "M0 Persistence":
            pred = partition["lag_1"].to_numpy()
        elif name == "M1 Lag-7":
            pred = partition["lag_7"].to_numpy()
        else:
            pred = fitted[name].predict(partition[FEATURE_COLUMNS])
        predictions.append(_prediction_frame(partition, name, pred))
    prediction_frame = pd.concat(predictions, ignore_index=True)
    metric_rows = []
    for name, group in prediction_frame.groupby("model", sort=False):
        metrics = compute_metrics(group[TARGET], group.predicted_price, group.lag_1)
        metric_rows.append({"model": name, **MODEL_SPECS[name], **metrics, "n": len(group)})
    return pd.DataFrame(metric_rows), prediction_frame


def _write_figures(comparison: pd.DataFrame, predictions: pd.DataFrame, selected_model: str, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    ordered = comparison.sort_values("mae")
    figure = make_subplots(rows=1, cols=2, subplot_titles=("Held-out MAE", "Held-out RMSE"))
    figure.add_trace(go.Bar(x=ordered.model, y=ordered.mae, name="MAE"), row=1, col=1)
    figure.add_trace(go.Bar(x=ordered.model, y=ordered.rmse, name="RMSE"), row=1, col=2)
    figure.update_layout(title="Forecast model comparison", template="plotly_white", showlegend=False)
    figure.write_html(figures_dir / "model_comparison.html", include_plotlyjs="cdn", full_html=True)

    selected = predictions[predictions.model.eq(selected_model)].copy()
    focus_market = selected.groupby("market_id").size().sort_values(ascending=False).index[0]
    focus = selected[selected.market_id.eq(focus_market)].sort_values("date")
    line = go.Figure([
        go.Scatter(x=focus.date, y=focus.modal_price, name="Actual", mode="lines+markers"),
        go.Scatter(x=focus.date, y=focus.predicted_price, name="Predicted", mode="lines+markers"),
    ])
    line.update_layout(title=f"Actual versus predicted: {focus.market.iloc[0]}", yaxis_title=PRICE_UNIT, template="plotly_white")
    line.write_html(figures_dir / "actual_vs_predicted.html", include_plotlyjs="cdn", full_html=True)

    scatter = px.scatter(selected, x="modal_price", y="predicted_price", hover_data=["market", "date"], title="Actual versus predicted prices")
    low = float(min(selected.modal_price.min(), selected.predicted_price.min()))
    high = float(max(selected.modal_price.max(), selected.predicted_price.max()))
    scatter.add_shape(type="line", x0=low, y0=low, x1=high, y1=high, line={"dash": "dash", "color": "gray"})
    scatter.update_layout(template="plotly_white", xaxis_title=f"Actual ({PRICE_UNIT})", yaxis_title=f"Predicted ({PRICE_UNIT})")
    scatter.write_html(figures_dir / "actual_vs_predicted_scatter.html", include_plotlyjs="cdn", full_html=True)

    residual = px.scatter(selected, x="predicted_price", y="residual", hover_data=["market", "date"], title="Residual diagnostic")
    residual.add_hline(y=0, line_dash="dash", line_color="gray")
    residual.update_layout(template="plotly_white", xaxis_title=f"Predicted ({PRICE_UNIT})", yaxis_title="Prediction - actual")
    residual.write_html(figures_dir / "residual_diagnostic.html", include_plotlyjs="cdn", full_html=True)


def _latest_feature_row(group: pd.DataFrame) -> pd.DataFrame:
    ordered = group.sort_values("date")
    values = ordered.modal_price.astype(float).to_numpy()
    if len(values) < 14:
        raise ValueError("At least 14 prior observations are required for inference.")
    row = {
        "lag_1": values[-1], "lag_2": values[-2], "lag_3": values[-3],
        "lag_7": values[-7], "lag_14": values[-14],
        "rolling_mean_3": values[-3:].mean(), "rolling_mean_7": values[-7:].mean(),
        "rolling_mean_14": values[-14:].mean(), "rolling_std_7": values[-7:].std(ddof=0),
        "previous_abs_change": values[-1] - values[-2],
        "previous_pct_change": (values[-1] - values[-2]) / values[-2] if values[-2] else np.nan,
        "market_id": ordered.market_id.iloc[-1],
    }
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def forecast_latest(prices: pd.DataFrame, selected_model: str, model: Pipeline | None, eligible_markets: list[str]) -> pd.DataFrame:
    clean, _ = validate_panel(prices, "Onion")
    rows = []
    for market_id in eligible_markets:
        group = clean[clean.market_id.eq(market_id)].sort_values("date")
        if len(group) < 14:
            continue
        features = _latest_feature_row(group)
        if selected_model == "M0 Persistence":
            prediction = float(features.lag_1.iloc[0])
        elif selected_model == "M1 Lag-7":
            prediction = float(features.lag_7.iloc[0])
        elif model is not None:
            prediction = float(model.predict(features)[0])
        else:
            raise ValueError("A fitted model is required for the selected machine-learning model.")
        last = group.iloc[-1]
        rows.append({
            "market_id": market_id, "market": last.market, "district": last.district,
            "state": last.state, "last_observed_date": last.date.date().isoformat(),
            "last_observed_price": float(last.modal_price),
            "predicted_next_report_price": prediction, "model": selected_model,
            "forecast_horizon": "next reported market observation",
            "historical_data_through": clean.date.max().date().isoformat(),
        })
    return pd.DataFrame(rows).sort_values(["district", "market"]).reset_index(drop=True)


def _write_methodology(output_dir: Path, metadata: dict[str, Any], comparison: pd.DataFrame) -> None:
    best = metadata["selected_model"]
    display_columns = ["model", "validation_mae", "mae", "rmse", "r2", "directional_accuracy_pct"]
    table = comparison[display_columns].copy()
    for column in display_columns[1:]:
        table[column] = table[column].map(lambda value: "" if pd.isna(value) else f"{value:.3f}")
    markdown_rows = [
        "| " + " | ".join(display_columns) + " |",
        "| " + " | ".join(["---"] * len(display_columns)) + " |",
        *["| " + " | ".join(map(str, row)) + " |" for row in table.itertuples(index=False, name=None)],
    ]
    lines = [
        "# AgriFlow forecasting methodology",
        "",
        "## Task",
        "",
        "Predict the Onion modal wholesale price at the next reported market observation. The irregular observation sequence means this is not a next-day forecast.",
        "",
        "## Data and cohort",
        "",
        f"- Source: {metadata['dataset']['source']} ({metadata['dataset']['source_tier']}).",
        f"- Unit: {PRICE_UNIT}.",
        f"- Eligible markets: {metadata['cohort']['eligible_market_count']} using at least {metadata['cohort']['minimum_market_observations']} observations per market.",
        f"- Modeling rows after lag construction: {metadata['cohort']['modeling_rows']:,}.",
        f"- Split boundaries: train through {metadata['split']['train_end']}; validation through {metadata['split']['validation_end']}; later observations form the test set.",
        "",
        "## Features and leakage control",
        "",
        "Lags 1, 2, 3, 7 and 14; prior-observation rolling means over 3, 7 and 14 reports; prior 7-report standard deviation; previous absolute and percentage change; market identity. Every rolling statistic starts from a one-observation shift.",
        "",
        "## Models and selection",
        "",
        "The experiment compares persistence, lag-7, Ridge, Decision Tree, Random Forest and Histogram Gradient Boosting on the same partitions. Validation MAE selects the model, with validation RMSE as tie-break. The held-out test set does not influence selection.",
        "",
        f"Selected model: **{best}**.",
        "",
        "## Held-out results",
        "",
        "\n".join(markdown_rows),
        "",
        "## Limitations",
        "",
        "The experiment covers Onion markets in four Maharashtra districts and ends in October 2025. It uses reported price history only, so it does not model weather, arrivals, policy changes or transport costs. Results measure historical next-report accuracy and do not represent current quotations.",
    ]
    (output_dir / "forecasting_methodology.md").write_text("\n".join(lines), encoding="utf-8")


def run_training(prices_path: Path | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    prices_path = prices_path or settings.processed_dir / "market_daily.csv"
    output_dir = output_dir or settings.root / "deliverables" / "final_review" / "forecasting"
    output_dir.mkdir(parents=True, exist_ok=True)
    prices = pd.read_csv(prices_path)
    features, audit = build_features(prices)
    split = temporal_split(features)
    fitted: dict[str, Pipeline] = {}
    durations: dict[str, float] = {"M0 Persistence": 0.0, "M1 Lag-7": 0.0}
    for name, estimator in _estimators().items():
        started = time.perf_counter()
        estimator.fit(split.train[FEATURE_COLUMNS], split.train[TARGET])
        durations[name] = time.perf_counter() - started
        fitted[name] = estimator
    validation_metrics, _ = _evaluate_partition(split.validation, fitted)
    validation_metrics["training_seconds"] = validation_metrics.model.map(durations)
    selected = validation_metrics.sort_values(["mae", "rmse", "model"]).iloc[0].model

    train_validation = pd.concat([split.train, split.validation], ignore_index=True)
    final_fitted: dict[str, Pipeline] = {}
    final_durations = dict(durations)
    for name, estimator in _estimators().items():
        started = time.perf_counter()
        estimator.fit(train_validation[FEATURE_COLUMNS], train_validation[TARGET])
        final_durations[name] = time.perf_counter() - started
        final_fitted[name] = estimator
    test_metrics, test_predictions = _evaluate_partition(split.test, final_fitted)
    test_metrics["training_seconds"] = test_metrics.model.map(final_durations)
    test_metrics["selected_on_validation"] = test_metrics.model.eq(selected)
    validation_metrics["selected_on_validation"] = validation_metrics.model.eq(selected)
    comparison = test_metrics.merge(
        validation_metrics[["model", "mae", "rmse"]].rename(columns={"mae": "validation_mae", "rmse": "validation_rmse"}),
        on="model", how="left",
    )
    comparison = comparison[[
        "model", "type", "parameters", "training_seconds", "validation_mae", "validation_rmse",
        "mae", "mse", "rmse", "r2", "mape_pct", "smape_pct", "wape_pct",
        "median_absolute_error", "mean_bias_error", "directional_accuracy_pct", "n",
        "selected_on_validation",
    ]]
    comparison.to_csv(output_dir / "model_comparison.csv", index=False)
    validation_metrics.to_csv(output_dir / "validation_metrics.csv", index=False)
    test_predictions.to_csv(output_dir / "test_predictions.csv", index=False)

    selected_model = final_fitted.get(selected)
    joblib.dump(
        selected_model if selected_model is not None else {
            "model": selected,
            "type": "deterministic_baseline",
            "parameters": MODEL_SPECS[selected]["parameters"],
        },
        output_dir / "forecast_model.joblib",
    )
    latest = forecast_latest(prices, selected, selected_model, audit["eligible_markets"])
    latest.to_csv(output_dir / "latest_forecasts.csv", index=False)

    dataset = {
        "source": ",".join(sorted(prices.get("source", pd.Series(["unknown"])).dropna().astype(str).unique())),
        "source_tier": ",".join(sorted(prices.get("source_tier", pd.Series(["unknown"])).dropna().astype(str).unique())),
        "data_mode": ",".join(sorted(prices.get("data_mode", pd.Series(["unknown"])).dropna().astype(str).unique())),
        "commodity": "Onion", "states": sorted(prices.state.dropna().astype(str).unique().tolist()),
        "districts": sorted(prices.district.dropna().astype(str).unique().tolist()),
        "market_count": int(prices.market_id.nunique()), "processed_rows": len(prices),
        "date_min": str(pd.to_datetime(prices.date).min().date()), "date_max": str(pd.to_datetime(prices.date).max().date()),
        "target": TARGET, "price_unit": PRICE_UNIT,
        "missing_modal_price_rows": int(pd.to_numeric(prices.modal_price, errors="coerce").isna().sum()),
        "file_sha256": sha256(prices_path.read_bytes()).hexdigest(),
        "acquisition_context": "Local completed CEDA Agri Market Data checkpoints; offline training input",
    }
    raw_files = sorted((settings.raw_dir / "ceda_chunks").rglob("*.csv"))
    raw_rows = int(sum(len(pd.read_csv(path)) for path in raw_files))
    dataset.update({"raw_checkpoint_files": len(raw_files), "raw_rows": raw_rows})
    (output_dir / "dataset_manifest.json").write_text(json.dumps(dataset, indent=2), encoding="utf-8")

    selected_test = comparison[comparison.model.eq(selected)].iloc[0]
    persistence = comparison[comparison.model.eq("M0 Persistence")].iloc[0]
    improvement = 100 * (persistence.mae - selected_test.mae) / persistence.mae
    metadata = {
        "selected_model": selected,
        "selection_rule": "lowest validation MAE; validation RMSE tie-break",
        "random_seed": RANDOM_SEED,
        "scikit_learn_version": __import__("sklearn").__version__,
        "target": TARGET, "price_unit": PRICE_UNIT,
        "forecast_horizon": "next reported market observation",
        "features": FEATURE_COLUMNS,
        "split": {
            "train_end": split.train_end.date().isoformat(),
            "validation_end": split.validation_end.date().isoformat(),
            "test_start": split.test.date.min().date().isoformat(),
            "test_end": split.test.date.max().date().isoformat(),
            "train_rows": len(split.train), "validation_rows": len(split.validation), "test_rows": len(split.test),
        },
        "cohort": audit,
        "dataset": dataset,
        "selected_validation_mae": float(validation_metrics.loc[validation_metrics.model.eq(selected), "mae"].iloc[0]),
        "selected_test_mae": float(selected_test.mae),
        "selected_test_rmse": float(selected_test.rmse),
        "persistence_test_mae": float(persistence.mae),
        "mae_improvement_vs_persistence_pct": float(improvement),
        "model_specs": MODEL_SPECS,
    }
    (output_dir / "selected_model.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    definitions = {
        "MAE": {"column": "mae", "unit": PRICE_UNIT, "direction": "lower"},
        "MSE": {"column": "mse", "unit": "squared INR per quintal", "direction": "lower"},
        "RMSE": {"column": "rmse", "unit": PRICE_UNIT, "direction": "lower"},
        "R2": {"column": "r2", "unit": "unitless", "direction": "higher"},
        "MAPE": {"column": "mape_pct", "unit": "percent", "direction": "lower"},
        "sMAPE": {"column": "smape_pct", "unit": "percent", "direction": "lower"},
        "WAPE": {"column": "wape_pct", "unit": "percent", "direction": "lower"},
        "Median absolute error": {"column": "median_absolute_error", "unit": PRICE_UNIT, "direction": "lower"},
        "Mean bias error": {"column": "mean_bias_error", "unit": PRICE_UNIT, "direction": "closer to zero"},
        "Directional accuracy": {"column": "directional_accuracy_pct", "unit": "percent", "direction": "higher", "unchanged_handling": "zero-to-zero counts as a match"},
    }
    (output_dir / "metric_definitions.json").write_text(json.dumps(definitions, indent=2), encoding="utf-8")
    _write_figures(comparison, test_predictions, selected, output_dir / "figures")
    _write_methodology(output_dir, metadata, comparison)
    return metadata


def load_forecast_artifacts(output_dir: Path | None = None) -> tuple[dict[str, Any], Pipeline | None, pd.DataFrame]:
    output_dir = output_dir or settings.root / "deliverables" / "final_review" / "forecasting"
    metadata_path = output_dir / "selected_model.json"
    forecasts_path = output_dir / "latest_forecasts.csv"
    if not metadata_path.exists() or not forecasts_path.exists():
        raise FileNotFoundError("Forecast artifacts are missing. Run `python -m agriflow train-forecast` first.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_path = output_dir / "forecast_model.joblib"
    model = joblib.load(model_path) if model_path.exists() else None
    return metadata, model, pd.read_csv(forecasts_path)
