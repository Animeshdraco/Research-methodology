"""Run leakage-aware forecasting and anomaly experiments on simulated data.

The split is chronological within each device: the first 70% of each hourly
series is used for training and the last 30% is held out. No event labels are
used to train Isolation Forest. All scores describe this simulator only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import f1_score, mean_absolute_error, mean_squared_error, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "analysis" / "data" / "simulated_readings.csv"
RESULTS = ROOT / "analysis" / "results"
FIGURES = ROOT / "analysis" / "figures"
CUT_FRACTION = 0.70
LAGS = (1, 2, 3, 6, 12, 24)


def build_forecast_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Build one-hour-ahead features; features at t predict purified value at t+1."""
    all_parts: list[pd.DataFrame] = []
    for device_id, group in frame.groupby("device_id", sort=True):
        g = group.sort_values("hour_index").copy().reset_index(drop=True)
        # Keep an untouched target copy: forecast rows with a missing target are
        # excluded later rather than being imputed from a future timestamp.
        g["target_tds_observed"] = g["purified_tds_mg_l"]
        g["target_turbidity_observed"] = g["purified_turbidity_ntu"]
        # Forward-fill predictors only; never back-fill from a later observation.
        signal_cols = [
            "raw_ph", "raw_turbidity_ntu", "raw_tds_mg_l", "raw_temp_c",
            "purified_ph", "purified_turbidity_ntu", "purified_tds_mg_l", "purified_temp_c",
        ]
        g[signal_cols] = g[signal_cols].ffill()
        rows = []
        for t in range(max(LAGS), len(g) - 1):
            row: dict[str, float | int | str] = {
                "device_id": device_id,
                "target_hour": int(g.loc[t + 1, "hour_index"]),
                "cut_index": int(np.floor(len(g) * CUT_FRACTION)),
                "target_tds": g.loc[t + 1, "target_tds_observed"],
                "target_turbidity": g.loc[t + 1, "target_turbidity_observed"],
                "persistence_tds": float(g.loc[t, "purified_tds_mg_l"]),
                "persistence_turbidity": float(g.loc[t, "purified_turbidity_ntu"]),
            }
            cols = {
                "raw_tds_mg_l": "raw_tds",
                "raw_turbidity_ntu": "raw_ntu",
                "purified_tds_mg_l": "pure_tds",
                "purified_turbidity_ntu": "pure_ntu",
                "purified_ph": "pure_ph",
                "purified_temp_c": "pure_temp",
            }
            for src, prefix in cols.items():
                for lag in LAGS:
                    row[f"{prefix}_lag{lag}"] = float(g.loc[t - lag + 1, src])
                row[f"{prefix}_mean6"] = float(g.loc[max(0, t - 5):t, src].mean())
                row[f"{prefix}_std6"] = float(g.loc[max(0, t - 5):t, src].std(ddof=0))
            row["hour_sin"] = float(np.sin(2 * np.pi * (t % 24) / 24))
            row["hour_cos"] = float(np.cos(2 * np.pi * (t % 24) / 24))
            rows.append(row)
        all_parts.append(pd.DataFrame(rows))
    return pd.concat(all_parts, ignore_index=True)


def forecast_experiment(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    features = build_forecast_rows(frame)
    features["split"] = np.where(features["target_hour"] < features["cut_index"], "train", "test")
    feature_cols = [c for c in features.columns if any(c.startswith(p) for p in (
        "raw_tds", "raw_ntu", "pure_tds", "pure_ntu", "pure_ph", "pure_temp", "hour_"
    ))]
    records: list[dict] = []
    all_predictions: list[pd.DataFrame] = []

    model_specs = {
        "Linear regression": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LinearRegression()),
        "Random forest": make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(
            n_estimators=250, max_depth=6, min_samples_leaf=2, random_state=42, n_jobs=1
        )),
    }
    for target_name, target_col, persistence_col in (
        ("TDS", "target_tds", "persistence_tds"),
        ("Turbidity", "target_turbidity", "persistence_turbidity"),
    ):
        train = features[(features["split"] == "train") & features[target_col].notna()].copy()
        test = features[(features["split"] == "test") & features[target_col].notna()].copy()
        y_train = train[target_col].to_numpy(dtype=float)
        y_test = test[target_col].to_numpy(dtype=float)
        pred_map = {"Persistence": test[persistence_col].to_numpy(dtype=float)}
        for model_name, model in model_specs.items():
            model.fit(train[feature_cols], y_train)
            pred_map[model_name] = model.predict(test[feature_cols])
        for model_name, pred in pred_map.items():
            records.append({
                "target": target_name,
                "model": model_name,
                "MAE": float(mean_absolute_error(y_test, pred)),
                "RMSE": float(np.sqrt(mean_squared_error(y_test, pred))),
                "n_test": int(len(y_test)),
                "split": "chronological 70/30 per device",
            })
            tmp = test[["device_id", "target_hour"]].copy()
            tmp["target"] = target_name
            tmp["model"] = model_name
            tmp["actual"] = y_test
            tmp["predicted"] = pred
            all_predictions.append(tmp)

    metrics = pd.DataFrame(records)
    predictions = pd.concat(all_predictions, ignore_index=True)
    return metrics, {"feature_count": len(feature_cols), "train_fraction": CUT_FRACTION, "lags": list(LAGS)}, predictions


def anomaly_experiment(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    records = []
    all_scored = []
    for device_id, group in frame.groupby("device_id", sort=True):
        g = group.sort_values("hour_index").copy().reset_index(drop=True)
        cut = int(np.floor(len(g) * CUT_FRACTION))
        cols = [
            "purified_ph", "purified_turbidity_ntu", "purified_tds_mg_l", "purified_temp_c",
            "raw_tds_mg_l", "raw_turbidity_ntu", "dropout_flag",
        ]
        # Preserve the dropout flag as a feature and fill sensor channels with prior readings.
        g[cols[:-1]] = g[cols[:-1]].ffill()
        g["tds_ratio"] = g["purified_tds_mg_l"] / g["raw_tds_mg_l"].replace(0, np.nan)
        g["tds_ratio"] = g["tds_ratio"].ffill()
        feature_cols = cols + ["tds_ratio"]
        for signal in ("purified_ph", "purified_turbidity_ntu", "purified_tds_mg_l", "purified_temp_c"):
            g[f"{signal}_diff"] = g[signal].diff().fillna(0)
            feature_cols.append(f"{signal}_diff")

        X_train = g.loc[:cut - 1, feature_cols].astype(float)
        X_test = g.loc[cut:, feature_cols].astype(float)
        y_test = g.loc[cut:, "anomaly_label"].astype(int).to_numpy()
        model = make_pipeline(SimpleImputer(strategy="median"), IsolationForest(
            n_estimators=400, max_samples="auto", contamination="auto", random_state=42, n_jobs=1
        ))
        model.fit(X_train)
        detector = model[-1]
        train_imputed = model[:-1].transform(X_train)
        train_scores = detector.decision_function(train_imputed)
        # A training-only lower-tail cutoff; test labels are never consulted.
        threshold = float(np.quantile(train_scores, 0.05))
        test_imputed = model[:-1].transform(X_test)
        test_scores = detector.decision_function(test_imputed)
        pred = (test_scores < threshold).astype(int)
        records.append({
            "device_id": device_id,
            "precision": float(precision_score(y_test, pred, zero_division=0)),
            "recall": float(recall_score(y_test, pred, zero_division=0)),
            "F1": float(f1_score(y_test, pred, zero_division=0)),
            "test_rows": int(len(y_test)),
            "positive_test_rows": int(y_test.sum()),
            "threshold_from_training_5th_percentile": threshold,
        })
        scored = g.loc[cut:, ["device_id", "hour_index", "anomaly_type", "anomaly_label"]].copy()
        scored["anomaly_score"] = test_scores
        scored["predicted_anomaly"] = pred
        all_scored.append(scored)

    by_device = pd.DataFrame(records)
    y = pd.concat(all_scored, ignore_index=True)
    overall = {
        "precision": float(precision_score(y["anomaly_label"], y["predicted_anomaly"], zero_division=0)),
        "recall": float(recall_score(y["anomaly_label"], y["predicted_anomaly"], zero_division=0)),
        "F1": float(f1_score(y["anomaly_label"], y["predicted_anomaly"], zero_division=0)),
        "test_rows": int(len(y)),
        "positive_test_rows": int(y["anomaly_label"].sum()),
        "threshold_policy": "5th percentile of training decision_function values, per device",
    }
    return by_device, y, overall


def make_figures(metrics: pd.DataFrame, predictions: pd.DataFrame, anomaly: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for target in ("TDS", "Turbidity"):
        subset = metrics[metrics["target"] == target]
        fig, ax = plt.subplots(figsize=(7.2, 4.0))
        x = np.arange(len(subset))
        ax.bar(x - 0.18, subset["MAE"], width=0.36, label="MAE")
        ax.bar(x + 0.18, subset["RMSE"], width=0.36, label="RMSE")
        ax.set_xticks(x, subset["model"], rotation=12)
        ax.set_ylabel("Error (target units)")
        ax.set_title(f"One-hour-ahead {target} forecast error (simulated test set)")
        ax.legend(frameon=False)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(FIGURES / f"{target.lower()}_forecast_metrics.png", dpi=180)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    for device_id in ("JW-01", "JW-02", "JW-03"):
        one = predictions[(predictions["target"] == "TDS") & (predictions["model"] == "Persistence") & (predictions["device_id"] == device_id)]
        ax.plot(one["target_hour"], one["actual"], label=f"{device_id} actual")
    ax.set_xlabel("Hour index (test window)")
    ax.set_ylabel("Purified TDS (mg/L)")
    ax.set_title("Simulated purified-water TDS in the held-out period")
    ax.legend(frameon=False, ncol=3)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "heldout_tds_series.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    y = anomaly.sort_values(["device_id", "hour_index"])
    for device_id, one in y.groupby("device_id"):
        ax.plot(one["hour_index"], one["anomaly_score"], label=device_id)
    ax.axhline(0, linestyle="--", linewidth=1, label="Zero score")
    ax.set_xlabel("Hour index")
    ax.set_ylabel("Isolation Forest decision score")
    ax.set_title("Anomaly scores in the held-out simulated period")
    ax.legend(frameon=False, ncol=4)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "isolation_forest_scores.png", dpi=180)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        print("Dataset not found; generating it first.")
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("generator", ROOT / "analysis" / "scripts" / "01_generate_data.py")
        module = module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        module.generate().to_csv(DATA_PATH, index=False)

    data = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    forecast_metrics, forecast_meta, predictions = forecast_experiment(data)
    anomaly_by_device, anomaly_scores, anomaly_overall = anomaly_experiment(data)

    forecast_metrics.to_csv(RESULTS / "forecast_metrics.csv", index=False)
    predictions.to_csv(RESULTS / "forecast_predictions.csv", index=False)
    anomaly_by_device.to_csv(RESULTS / "anomaly_metrics_by_device.csv", index=False)
    anomaly_scores.to_csv(RESULTS / "anomaly_test_scores.csv", index=False)

    summary = {
        "dataset": "simulated_readings.csv",
        "records": int(len(data)),
        "devices": int(data["device_id"].nunique()),
        "hours_per_device": int(data.groupby("device_id").size().iloc[0]),
        "seed": 42,
        "forecast": forecast_meta,
        "forecast_metrics": forecast_metrics.to_dict(orient="records"),
        "anomaly_overall": anomaly_overall,
        "anomaly_by_device": anomaly_by_device.to_dict(orient="records"),
        "interpretation": "All scores are synthetic simulator checks. They are not field accuracy or drinking-water certification.",
    }
    (RESULTS / "experiment_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_figures(forecast_metrics, predictions, anomaly_scores)

    print("Forecast metrics (synthetic hold-out):")
    print(forecast_metrics.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nIsolation Forest (synthetic hold-out):")
    print(json.dumps(anomaly_overall, indent=2))
    print("\nAll metrics are simulator-only; do not describe them as field results.")


if __name__ == "__main__":
    main()
