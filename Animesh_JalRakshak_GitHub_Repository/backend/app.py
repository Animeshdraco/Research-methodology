"""JalRakshak API: authenticated sensor ingestion, SQLite persistence and alerts.

The default database and device keys are development-only. Do not expose this
instance to the public internet or connect it to drinking-water decisions.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "backend" / "data" / "jalrakshak.sqlite3"
DASHBOARD = ROOT / "dashboard" / "jalrakshak-dashboard.html"
DEFAULT_KEYS = {"JW-01": "dev-jw01-change-me", "JW-02": "dev-jw02-change-me", "JW-03": "dev-jw03-change-me"}

DEVICES = [
    {"device_id": "JW-01", "name": "Jharia Block Unit", "district": "Dhanbad", "location": "Dhanbad, Jharkhand"},
    {"device_id": "JW-02", "name": "Noamundi Mine Village Unit", "district": "West Singhbhum", "location": "West Singhbhum, Jharkhand"},
    {"device_id": "JW-03", "name": "Patratu Community Unit", "district": "Ramgarh", "location": "Ramgarh, Jharkhand"},
]
STAGES = [
    {"stage_id": "sediment", "name": "Sediment filter", "purpose": "Reduces suspended particles", "remaining_life_pct": 72, "basis": "simulated maintenance estimate"},
    {"stage_id": "carbon", "name": "Activated carbon", "purpose": "Reduces selected organics, odour and taste compounds", "remaining_life_pct": 55, "basis": "simulated maintenance estimate"},
    {"stage_id": "ro", "name": "UF / RO membrane", "purpose": "Membrane selection depends on dissolved contaminant testing", "remaining_life_pct": 22, "basis": "simulated maintenance estimate"},
    {"stage_id": "uv", "name": "UV disinfection", "purpose": "Microbial inactivation only when validated dose and flow are maintained", "remaining_life_pct": 58, "basis": "simulated maintenance estimate"},
]

class SensorSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ph: float | None = Field(default=None, ge=0, le=14)
    turbidity_ntu: float | None = Field(default=None, ge=0, le=10000)
    tds_mg_l: float | None = Field(default=None, ge=0, le=100000)
    temperature_c: float | None = Field(default=None, ge=-10, le=100)

    @field_validator("ph", "turbidity_ntu", "tds_mg_l", "temperature_c")
    @classmethod
    def finite_values(cls, value):
        if value is not None and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("sensor readings must be finite numbers")
        return value

class ReadingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=1, max_length=32)
    timestamp: datetime
    data_source: Literal["simulated", "hardware"]
    raw: SensorSet
    purified: SensorSet
    firmware_version: str | None = Field(default=None, max_length=40)

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value: datetime):
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone, such as Z or +05:30")
        return value.astimezone(timezone.utc)

    @field_validator("raw", "purified")
    @classmethod
    def at_least_one_measurement(cls, value: SensorSet):
        if all(getattr(value, k) is None for k in ("ph", "turbidity_ntu", "tds_mg_l", "temperature_c")):
            raise ValueError("each sensor line must contain at least one measurement")
        return value

class AlertUpdate(BaseModel):
    status: Literal["Open", "Acknowledged", "Resolved"]


def _parse_keys(raw: str | None) -> dict[str, str]:
    if not raw:
        return DEFAULT_KEYS.copy()
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in obj.items()):
            raise ValueError
        return obj
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError("JALRAKSHAK_DEVICE_KEYS must be a JSON object of device_id to key")


def status_for(param: str, value: float | None) -> tuple[str, str] | None:
    if value is None or param == "temperature_c":
        return None
    if param == "ph":
        # IS 10500: pH 6.5-8.5, no relaxation. Outside this range is critical.
        return ("Critical", "pH is outside 6.5-8.5; hold use and confirm with laboratory testing") if not 6.5 <= value <= 8.5 else None
    if param == "turbidity_ntu":
        if value > 5:
            return "Critical", "Turbidity is above 5 NTU; inspect pretreatment and confirm with a lab"
        if value > 1:
            return "Warning", "Turbidity is above the 1 NTU acceptable limit; inspect filters and confirm"
        return None
    if param == "tds_mg_l":
        if value > 2000:
            return "Critical", "TDS is above 2000 mg/L; do not rely on this prototype status"
        if value > 500:
            return "Warning", "TDS is above the 500 mg/L acceptable limit; investigate dissolved constituents"
        return None
    return None


def create_app(db_path: str | Path = DEFAULT_DB, device_keys: dict[str, str] | None = None) -> FastAPI:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    keys = device_keys if device_keys is not None else _parse_keys(os.getenv("JALRAKSHAK_DEVICE_KEYS"))
    app = FastAPI(
        title="JalRakshak Water Quality API",
        version="1.0.0",
        description="Development prototype API. Simulated readings are not evidence of drinking-water safety.",
    )
    app.state.db_path = db_path
    app.state.device_keys = keys

    def json_safe(value):
        if isinstance(value, float) and not math.isfinite(value):
            return str(value)
        if isinstance(value, BaseException):
            return str(value)
        if isinstance(value, dict):
            return {str(k): json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [json_safe(v) for v in value]
        return value

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # Error payloads may include NaN/Infinity as rejected input values;
        # sanitise them before JSON encoding so the API returns a proper 422.
        return JSONResponse(status_code=422, content={"detail": json_safe(exc.errors())})

    def connect():
        con = sqlite3.connect(db_path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        return con

    @contextmanager
    def db():
        con = connect()
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def init_db():
        with db() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY, name TEXT NOT NULL, district TEXT NOT NULL,
                location TEXT NOT NULL, firmware_version TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL REFERENCES devices(device_id),
                timestamp TEXT NOT NULL, data_source TEXT NOT NULL CHECK(data_source IN ('simulated','hardware')),
                raw_json TEXT NOT NULL, purified_json TEXT NOT NULL, firmware_version TEXT,
                created_at TEXT NOT NULL, UNIQUE(device_id, timestamp)
            );
            CREATE INDEX IF NOT EXISTS idx_readings_device_time ON readings(device_id, timestamp DESC);
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL REFERENCES devices(device_id),
                reading_id INTEGER NOT NULL REFERENCES readings(id), parameter TEXT NOT NULL,
                severity TEXT NOT NULL, value REAL NOT NULL, message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Acknowledged','Resolved')),
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_device_time ON alerts(device_id, created_at DESC);
            """)
            now = datetime.now(timezone.utc).isoformat()
            for d in DEVICES:
                con.execute("INSERT OR IGNORE INTO devices(device_id,name,district,location,created_at) VALUES(?,?,?,?,?)",
                            (d["device_id"], d["name"], d["district"], d["location"], now))

    # Initialise immediately. FastAPI imports the app once per process; SQLite
    # handles concurrent requests with short transactions and WAL journalling.
    init_db()

    def require_device_key(x_device_key: Annotated[str | None, Header()] = None):
        if not x_device_key:
            raise HTTPException(401, "Missing X-Device-Key header")
        matches = [device for device, key in keys.items() if hmac.compare_digest(key, x_device_key)]
        if not matches:
            raise HTTPException(401, "Invalid device key")
        return matches[0]

    @app.get("/api/health")
    def health():
        with db() as con:
            count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        return {"status": "ok", "service": "jalrakshak-api", "database": "sqlite", "reading_count": count,
                "evidence_mode": "simulated unless an authenticated hardware reading is explicitly submitted"}

    @app.get("/api/v1/devices")
    def get_devices():
        with db() as con:
            rows = con.execute("SELECT d.*, (SELECT MAX(timestamp) FROM readings r WHERE r.device_id=d.device_id) AS last_seen FROM devices d ORDER BY device_id").fetchall()
        return [dict(r) for r in rows]

    def reading_row(row: sqlite3.Row):
        out = dict(row)
        out["raw"] = json.loads(out.pop("raw_json"))
        out["purified"] = json.loads(out.pop("purified_json"))
        return out

    def insert_reading(con, payload: dict) -> tuple[int, list[dict]]:
        ts = payload["timestamp"]
        if isinstance(ts, datetime):
            ts = ts.astimezone(timezone.utc).isoformat()
        elif isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        device_id = payload["device_id"]
        raw = payload["raw"]
        purified = payload["purified"]
        now = datetime.now(timezone.utc).isoformat()
        try:
            cur = con.execute(
                "INSERT INTO readings(device_id,timestamp,data_source,raw_json,purified_json,firmware_version,created_at) VALUES(?,?,?,?,?,?,?)",
                (device_id, ts, payload["data_source"], json.dumps(raw, allow_nan=False), json.dumps(purified, allow_nan=False), payload.get("firmware_version"), now),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "A reading for this device and timestamp already exists") from exc
        reading_id = cur.lastrowid
        created = []
        for key, value in purified.items():
            event = status_for(key, value)
            if event:
                severity, message = event
                cur = con.execute("INSERT INTO alerts(device_id,reading_id,parameter,severity,value,message,created_at) VALUES(?,?,?,?,?,?,?)",
                                  (device_id, reading_id, key, severity, value, message, ts))
                created.append({"id": cur.lastrowid, "parameter": key, "severity": severity, "value": value, "message": message, "status": "Open"})
        return reading_id, created

    @app.post("/api/v1/readings", status_code=201)
    def create_reading(payload: ReadingIn, authenticated_device: str = Depends(require_device_key)):
        if payload.device_id != authenticated_device:
            raise HTTPException(403, "Device key is not authorised for the supplied device_id")
        with db() as con:
            if not con.execute("SELECT 1 FROM devices WHERE device_id=?", (payload.device_id,)).fetchone():
                raise HTTPException(404, "Unknown device")
            reading_id, created_alerts = insert_reading(con, payload.model_dump(mode="json"))
        return {"id": reading_id, "device_id": payload.device_id, "timestamp": payload.timestamp.isoformat(),
                "data_source": payload.data_source, "created_alerts": created_alerts}

    @app.get("/api/v1/readings")
    def get_readings(device_id: str | None = None, limit: int = Query(100, ge=1, le=1000)):
        with db() as con:
            if device_id and not con.execute("SELECT 1 FROM devices WHERE device_id=?", (device_id,)).fetchone():
                raise HTTPException(404, "Unknown device")
            query = "SELECT * FROM readings" + (" WHERE device_id=?" if device_id else "") + " ORDER BY timestamp DESC LIMIT ?"
            args = (device_id, limit) if device_id else (limit,)
            rows = con.execute(query, args).fetchall()
        return [reading_row(r) for r in rows]

    @app.get("/api/v1/alerts")
    def get_alerts(device_id: str | None = None, status: str | None = None, limit: int = Query(100, ge=1, le=500)):
        if status and status not in {"Open", "Acknowledged", "Resolved"}:
            raise HTTPException(422, "status must be Open, Acknowledged or Resolved")
        sql = "SELECT a.*, d.name AS device_name FROM alerts a JOIN devices d USING(device_id)"
        clauses, args = [], []
        if device_id:
            clauses.append("a.device_id=?"); args.append(device_id)
        if status:
            clauses.append("a.status=?"); args.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY a.created_at DESC LIMIT ?"; args.append(limit)
        with db() as con:
            rows = con.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    @app.patch("/api/v1/alerts/{alert_id}")
    def update_alert(alert_id: int, payload: AlertUpdate):
        with db() as con:
            cur = con.execute("UPDATE alerts SET status=? WHERE id=?", (payload.status, alert_id))
            if not cur.rowcount:
                raise HTTPException(404, "Alert not found")
            row = con.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        return dict(row)

    @app.get("/api/v1/dashboard")
    def dashboard(device_id: str = "JW-01", hours: int = Query(168, ge=1, le=720)):
        with db() as con:
            dev = con.execute("SELECT * FROM devices WHERE device_id=?", (device_id,)).fetchone()
            if not dev:
                raise HTTPException(404, "Unknown device")
            rows = con.execute("SELECT * FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT ?", (device_id, hours)).fetchall()
            alerts = con.execute("SELECT * FROM alerts WHERE device_id=? ORDER BY created_at DESC LIMIT 20", (device_id,)).fetchall()
        readings = [reading_row(r) for r in reversed(rows)]
        return {"device": dict(dev), "readings": readings, "latest": readings[-1] if readings else None,
                "alerts": [dict(a) for a in alerts], "stages": STAGES,
                "evidence_note": "Dataset values are simulated. This dashboard does not certify drinking-water safety."}

    @app.get("/api/v1/experiment-summary")
    def experiment_summary():
        path = ROOT / "analysis" / "results" / "experiment_summary.json"
        if not path.exists():
            return {"status": "not_run", "detail": "Run ./run_pipeline.sh to generate results"}
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(DASHBOARD)

    app.mount("/assets", StaticFiles(directory=ROOT / "dashboard"), name="assets")
    return app

app = create_app()
