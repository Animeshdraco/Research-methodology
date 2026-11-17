"""Generate a reproducible, explicitly synthetic JalRakshak dataset.

Purpose
-------
Create hourly raw-water and purified-water sensor records for three
illustrative locations. Events are deliberately injected so alert and anomaly
logic can be exercised before field sensors are available.

This is NOT a field dataset and must not be described as measured water data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "analysis" / "data" / "simulated_readings.csv"

UNITS = [
    {"device_id": "JW-01", "district": "Dhanbad", "ph": 7.4, "ntu": 8.0, "tds": 780.0, "temp": 26.5, "eta": 0.90},
    {"device_id": "JW-02", "district": "West Singhbhum", "ph": 7.9, "ntu": 4.0, "tds": 1350.0, "temp": 27.0, "eta": 0.92},
    {"device_id": "JW-03", "district": "Ramgarh", "ph": 7.1, "ntu": 3.0, "tds": 900.0, "temp": 26.0, "eta": 0.90},
]


def generate(seed: int = 42, hours: int = 168) -> pd.DataFrame:
    """Return a seeded hourly dataset with transparent injected events."""
    if hours < 168:
        raise ValueError("hours must be at least 168 to include every documented scenario")

    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    start = pd.Timestamp("2026-11-10T00:00:00Z")

    for unit in UNITS:
        for h in range(hours):
            eps = rng.uniform(-1.0, 1.0, size=8)
            raw_ph = unit["ph"] + 0.15 * eps[0]
            raw_tds = unit["tds"] * (1.0 + 0.06 * eps[1])
            raw_ntu = max(0.5, unit["ntu"] * (1.0 + 0.30 * eps[2]))
            raw_temp = unit["temp"] + 3.0 * np.sin(2 * np.pi * (h - 15) / 24) + 0.4 * eps[3]

            event_names: list[str] = []
            if unit["device_id"] == "JW-01" and 128 <= h <= 133:
                # The increase is a designed test signal, not a measurement.
                raw_ntu += float(rng.uniform(11.0, 66.0))
                event_names.append("turbidity_surge")

            removal_ratio = unit["eta"]
            if unit["device_id"] == "JW-03" and h >= 124:
                fraction = min(1.0, (h - 124) / 43.0)
                removal_ratio = 0.90 - 0.51 * fraction
                event_names.append("membrane_degradation")

            purified_ph = raw_ph + 0.025 * eps[4]
            purified_ntu = max(0.05, 0.15 + 0.04 * raw_ntu + 0.025 * eps[5])
            purified_tds = max(1.0, raw_tds * (1.0 - removal_ratio) + 2.0 * eps[6])
            purified_temp = raw_temp + 0.10 * eps[7]

            if unit["device_id"] == "JW-02" and 140 <= h <= 148:
                drift = 25.0 + (h - 140) * 22.0
                purified_tds += drift
                event_names.append("tds_sensor_drift")

            if unit["device_id"] == "JW-01" and 150 <= h <= 154:
                # A flat sensor value emulates a stuck probe.
                if h == 150:
                    stuck_ph = purified_ph
                purified_ph = stuck_ph
                event_names.append("ph_sensor_stuck")

            dropout = int(unit["device_id"] == "JW-02" and 160 <= h <= 162)
            if dropout:
                purified_tds = np.nan
                event_names.append("tds_reading_dropout")

            rows.append({
                "device_id": unit["device_id"],
                "district": unit["district"],
                "timestamp": start + pd.Timedelta(hours=h),
                "hour_index": h,
                "data_source": "simulated",
                "raw_ph": round(float(raw_ph), 4),
                "raw_turbidity_ntu": round(float(raw_ntu), 4),
                "raw_tds_mg_l": round(float(raw_tds), 3),
                "raw_temp_c": round(float(raw_temp), 3),
                "purified_ph": round(float(purified_ph), 4),
                "purified_turbidity_ntu": round(float(purified_ntu), 4),
                "purified_tds_mg_l": round(float(purified_tds), 3) if np.isfinite(purified_tds) else np.nan,
                "purified_temp_c": round(float(purified_temp), 3),
                "membrane_removal_assumption": round(float(removal_ratio), 4),
                "dropout_flag": dropout,
                "anomaly_type": ";".join(event_names) if event_names else "none",
                "anomaly_label": int(bool(event_names)),
            })

    frame = pd.DataFrame(rows).sort_values(["device_id", "hour_index"]).reset_index(drop=True)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    frame = generate(seed=args.seed, hours=args.hours)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(f"Wrote {len(frame)} simulated rows to {args.output}")
    print(f"Seed: {args.seed}; units: {frame['device_id'].nunique()}; hours/unit: {args.hours}")
    print(f"Injected anomalous rows: {int(frame['anomaly_label'].sum())}")
    print("Reminder: values are synthetic and do not indicate real drinking-water safety.")


if __name__ == "__main__":
    main()
