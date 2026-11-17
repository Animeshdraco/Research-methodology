"""Load the seed-42 simulator stream into the local SQLite database."""
from __future__ import annotations
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import DEFAULT_DB, create_app, status_for  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="clear prior readings and alerts before loading")
    parser.add_argument("--csv", type=Path, default=ROOT / "analysis/data/simulated_readings.csv")
    args = parser.parse_args()
    if not args.csv.exists():
        raise SystemExit(f"Dataset not found: {args.csv}; run ./run_pipeline.sh first")
    create_app(DEFAULT_DB)  # ensures schema/device registry exists
    frame = pd.read_csv(args.csv, parse_dates=["timestamp"])
    now = datetime.now(timezone.utc).isoformat()
    inserted = skipped = alerts_added = 0
    with sqlite3.connect(DEFAULT_DB, timeout=30) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        if args.replace:
            con.execute("DELETE FROM alerts")
            con.execute("DELETE FROM readings")
        for row in frame.to_dict(orient="records"):
            def number(value):
                return None if pd.isna(value) else float(value)
            raw = {
                "ph": number(row["raw_ph"]), "turbidity_ntu": number(row["raw_turbidity_ntu"]),
                "tds_mg_l": number(row["raw_tds_mg_l"]), "temperature_c": number(row["raw_temp_c"]),
            }
            pure = {
                "ph": number(row["purified_ph"]), "turbidity_ntu": number(row["purified_turbidity_ntu"]),
                "tds_mg_l": number(row["purified_tds_mg_l"]), "temperature_c": number(row["purified_temp_c"]),
            }
            ts = pd.Timestamp(row["timestamp"]).to_pydatetime().astimezone(timezone.utc).isoformat()
            cur = con.execute(
                "INSERT OR IGNORE INTO readings(device_id,timestamp,data_source,raw_json,purified_json,firmware_version,created_at) VALUES(?,?,?,?,?,?,?)",
                (row["device_id"], ts, "simulated", json.dumps(raw, allow_nan=False), json.dumps(pure, allow_nan=False), "simulator-seed-42", now),
            )
            if not cur.rowcount:
                skipped += 1
                continue
            inserted += 1
            reading_id = cur.lastrowid
            for key, value in pure.items():
                event = status_for(key, value)
                if event:
                    severity, message = event
                    con.execute("INSERT INTO alerts(device_id,reading_id,parameter,severity,value,message,created_at) VALUES(?,?,?,?,?,?,?)",
                                (row["device_id"], reading_id, key, severity, value, message, ts))
                    alerts_added += 1
    with sqlite3.connect(DEFAULT_DB) as con:
        count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    print(json.dumps({"inserted": inserted, "duplicates_skipped": skipped, "alerts_added": alerts_added,
                      "database": str(DEFAULT_DB), "total_readings": count,
                      "data_provenance": "simulated only"}, indent=2))

if __name__ == "__main__":
    main()
