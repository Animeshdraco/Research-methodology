from datetime import datetime, timezone
import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from backend.app import create_app

KEYS = {"JW-01": "secret-one", "JW-02": "secret-two", "JW-03": "secret-three"}

@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(tmp_path / "test.sqlite3", KEYS)
    with TestClient(app) as c:
        yield c


def valid_body(device="JW-01", timestamp="2026-11-17T10:00:00Z"):
    return {
        "device_id": device, "timestamp": timestamp, "data_source": "simulated", "firmware_version": "test",
        "raw": {"ph": 7.2, "turbidity_ntu": 3.0, "tds_mg_l": 700, "temperature_c": 25.0},
        "purified": {"ph": 7.1, "turbidity_ntu": 0.7, "tds_mg_l": 400, "temperature_c": 24.9},
    }


def test_health_and_device_registry(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/v1/devices").json()) == 3


def test_authenticated_ingestion_and_persistence(client):
    r = client.post("/api/v1/readings", json=valid_body(), headers={"X-Device-Key": KEYS["JW-01"]})
    assert r.status_code == 201
    assert r.json()["data_source"] == "simulated"
    rows = client.get("/api/v1/readings?device_id=JW-01").json()
    assert len(rows) == 1 and rows[0]["purified"]["tds_mg_l"] == 400


def test_missing_or_wrong_device_key_rejected(client):
    assert client.post("/api/v1/readings", json=valid_body()).status_code == 401
    assert client.post("/api/v1/readings", json=valid_body(), headers={"X-Device-Key": "wrong"}).status_code == 401


def test_key_cannot_impersonate_other_device(client):
    r = client.post("/api/v1/readings", json=valid_body("JW-02"), headers={"X-Device-Key": KEYS["JW-01"]})
    assert r.status_code == 403


def test_duplicate_device_timestamp_rejected(client):
    h = {"X-Device-Key": KEYS["JW-01"]}
    assert client.post("/api/v1/readings", json=valid_body(), headers=h).status_code == 201
    assert client.post("/api/v1/readings", json=valid_body(), headers=h).status_code == 409


def test_out_of_range_sensor_value_rejected(client):
    body = valid_body(); body["purified"]["ph"] = 16
    assert client.post("/api/v1/readings", json=body, headers={"X-Device-Key": KEYS["JW-01"]}).status_code == 422


def test_timezone_is_required(client):
    body = valid_body(timestamp="2026-11-17T10:00:00")
    assert client.post("/api/v1/readings", json=body, headers={"X-Device-Key": KEYS["JW-01"]}).status_code == 422


def test_critical_turbidity_creates_alert(client):
    body = valid_body(); body["purified"]["turbidity_ntu"] = 8.4
    r = client.post("/api/v1/readings", json=body, headers={"X-Device-Key": KEYS["JW-01"]})
    assert r.status_code == 201 and r.json()["created_alerts"][0]["severity"] == "Critical"
    alerts = client.get("/api/v1/alerts?device_id=JW-01&status=Open").json()
    assert len(alerts) == 1
    update = client.patch(f"/api/v1/alerts/{alerts[0]['id']}", json={"status": "Acknowledged"})
    assert update.status_code == 200 and update.json()["status"] == "Acknowledged"


def test_pH_has_no_permissible_band(client):
    body = valid_body(); body["purified"]["ph"] = 8.7
    r = client.post("/api/v1/readings", json=body, headers={"X-Device-Key": KEYS["JW-01"]})
    assert r.status_code == 201
    assert any(x["parameter"] == "ph" and x["severity"] == "Critical" for x in r.json()["created_alerts"])


def test_dashboard_summary_and_readings_endpoint(client):
    h = {"X-Device-Key": KEYS["JW-01"]}
    client.post("/api/v1/readings", json=valid_body(), headers=h)
    d = client.get("/api/v1/dashboard?device_id=JW-01").json()
    assert d["latest"]["device_id"] == "JW-01"
    assert "not certify" in d["evidence_note"]


def test_unknown_device_and_alert_return_404(client):
    assert client.get("/api/v1/dashboard?device_id=NO-SUCH").status_code == 404
    assert client.patch("/api/v1/alerts/999", json={"status": "Resolved"}).status_code == 404


def test_api_docs_and_dashboard_are_served(client):
    assert client.get('/openapi.json').status_code == 200
    response = client.get('/')
    assert response.status_code == 200
    assert 'JalRakshak' in response.text


def test_non_finite_json_value_rejected(client):
    body = valid_body()
    body['raw']['tds_mg_l'] = float('nan')
    response = client.post('/api/v1/readings', content=json.dumps(body), headers={'X-Device-Key': KEYS['JW-01'], 'Content-Type': 'application/json'})
    assert response.status_code == 422
