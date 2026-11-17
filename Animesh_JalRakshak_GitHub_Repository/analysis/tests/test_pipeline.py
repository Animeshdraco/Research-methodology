import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis/scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

def test_generator_reproducibility_and_shape():
    gen = load_script("generator", "01_generate_data.py")
    a = gen.generate(seed=42)
    b = gen.generate(seed=42)
    assert len(a) == 504
    assert a.equals(b)
    assert a.device_id.nunique() == 3
    assert set(a.data_source) == {"simulated"}
    assert a.anomaly_label.sum() > 0

def test_forecast_holdout_excludes_missing_targets():
    ev = load_script("evaluation", "02_evaluate_models.py")
    frame = pd.read_csv(ROOT / "analysis/data/simulated_readings.csv", parse_dates=["timestamp"])
    features = ev.build_forecast_rows(frame)
    assert features.target_tds.isna().sum() == 3
    assert set(features.columns).issuperset({"persistence_tds", "target_tds", "target_turbidity"})

def test_model_metrics_reproducible():
    ev = load_script("evaluation", "02_evaluate_models.py")
    frame = pd.read_csv(ROOT / "analysis/data/simulated_readings.csv", parse_dates=["timestamp"])
    metrics, _, _ = ev.forecast_experiment(frame)
    assert len(metrics) == 6
    assert np.isfinite(metrics[["MAE", "RMSE"]].to_numpy()).all()
    assert set(metrics.model) == {"Persistence", "Linear regression", "Random forest"}

def test_robustness_scenarios_preserve_ground_truth_labels():
    rob = load_script("robustness", "03_robustness_sweep.py")
    frame = pd.read_csv(ROOT / "analysis/data/simulated_readings.csv", parse_dates=["timestamp"])
    for kind, level in (("noise", .05), ("missing", .1), ("drift", .03)):
        altered = rob.scenario_frame(frame, kind, level, 77)
        assert altered.anomaly_label.equals(frame.anomaly_label)
        assert altered.device_id.equals(frame.device_id)
