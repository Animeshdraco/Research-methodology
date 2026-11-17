"""Run a reproducible synthetic sensitivity sweep for noise, gaps and drift."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "analysis/data/simulated_readings.csv"
OUT = ROOT / "analysis/results/robustness_sweep.csv"
SUMMARY = ROOT / "analysis/results/robustness_summary.json"
MODEL_PATH = ROOT / "analysis/scripts/02_evaluate_models.py"

spec = importlib.util.spec_from_file_location("jalrakshak_eval", MODEL_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

SENSOR_COLS = [
    "raw_ph", "raw_turbidity_ntu", "raw_tds_mg_l", "raw_temp_c",
    "purified_ph", "purified_turbidity_ntu", "purified_tds_mg_l", "purified_temp_c",
]


def scenario_frame(base: pd.DataFrame, kind: str, magnitude: float, seed: int) -> pd.DataFrame:
    df = base.copy(deep=True)
    rng = np.random.default_rng(seed)
    if kind == "noise":
        for col in SENSOR_COLS:
            sd = float(base[col].std(skipna=True))
            df[col] = df[col] + rng.normal(0, sd * magnitude, size=len(df))
        df["purified_turbidity_ntu"] = df["purified_turbidity_ntu"].clip(lower=0)
        df["purified_tds_mg_l"] = df["purified_tds_mg_l"].clip(lower=0)
    elif kind == "missing":
        for device_id, idx in df.groupby("device_id").groups.items():
            sample_idx = np.asarray(list(idx))
            selected = rng.choice(sample_idx, size=int(round(len(sample_idx) * magnitude)), replace=False)
            for col in SENSOR_COLS:
                df.loc[selected, col] = np.nan
    elif kind == "drift":
        for device_id, idx in df.groupby("device_id").groups.items():
            ids = np.asarray(list(idx))
            scale = float(base.loc[ids, "purified_tds_mg_l"].std(skipna=True))
            ramp = np.linspace(0, scale * magnitude, len(ids))
            df.loc[ids, "purified_tds_mg_l"] = df.loc[ids, "purified_tds_mg_l"].to_numpy() + ramp
    else:
        raise ValueError(kind)
    return df


def run() -> pd.DataFrame:
    base = pd.read_csv(DATA, parse_dates=["timestamp"])
    scenarios = [("baseline", 0.0)] + [("noise", x) for x in (0.02, 0.05, 0.10)] + [("missing", x) for x in (0.05, 0.10, 0.20)] + [("drift", x) for x in (0.01, 0.03, 0.05)]
    results = []
    for i, (kind, level) in enumerate(scenarios):
        trial = base if kind == "baseline" else scenario_frame(base, kind, level, 90210 + i)
        fmetrics, _, _ = module.forecast_experiment(trial)
        _, _, anomaly = module.anomaly_experiment(trial)
        for _, row in fmetrics.iterrows():
            results.append({
                "scenario": kind, "magnitude": level, "target": row["target"], "model": row["model"],
                "MAE": row["MAE"], "RMSE": row["RMSE"], "n_test": int(row["n_test"]),
                "anomaly_precision": anomaly["precision"], "anomaly_recall": anomaly["recall"],
                "anomaly_F1": anomaly["F1"], "anomaly_test_rows": anomaly["test_rows"],
                "anomaly_positive_rows": anomaly["positive_test_rows"],
            })
    out = pd.DataFrame(results)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    summary = {
        "dataset": "seed-42 synthetic readings",
        "scenario_count": len(scenarios),
        "scenario_definitions": {
            "noise": "Gaussian noise added independently to each sensor channel; magnitude is a fraction of that channel's dataset standard deviation",
            "missing": "Random sensor-channel rows set missing independently per device; models forward-fill predictors only and omit missing targets",
            "drift": "Linear drift added to purified TDS from zero to magnitude times the device's base purified-TDS standard deviation",
        },
        "results_file": str(OUT.relative_to(ROOT)),
        "interpretation": "Sensitivity results are simulator stress tests only; no external or field validation is implied.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(out.groupby(["scenario", "magnitude", "target", "model"])[["MAE", "RMSE", "anomaly_F1"]].mean().to_string())
    print(f"\nWrote {len(out)} scenario-model rows to {OUT}")
    return out

if __name__ == "__main__":
    run()
