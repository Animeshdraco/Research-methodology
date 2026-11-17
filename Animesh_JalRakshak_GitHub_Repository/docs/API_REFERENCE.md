# JalRakshak API reference

Base URL during local development: `http://127.0.0.1:8000`. OpenAPI UI: `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service/database health and current reading count |
| GET | `/api/v1/devices` | Registered device metadata and latest timestamp |
| POST | `/api/v1/readings` | Ingest a sensor record; requires `X-Device-Key` |
| GET | `/api/v1/readings?device_id=JW-01&limit=168` | Read stored time-series values |
| GET | `/api/v1/alerts?device_id=JW-01&status=Open` | List rule-generated alerts |
| PATCH | `/api/v1/alerts/{id}` | Set `Open`, `Acknowledged` or `Resolved` |
| GET | `/api/v1/dashboard?device_id=JW-01&hours=168` | Dashboard-ready device, readings, alerts and stage estimates |
| GET | `/api/v1/experiment-summary` | Read model evaluation summary |

Example ingestion body:

```json
{
  "device_id": "JW-01",
  "timestamp": "2026-11-18T10:00:00Z",
  "data_source": "simulated",
  "firmware_version": "demo-1.0",
  "raw": {"ph": 7.2, "turbidity_ntu": 3.1, "tds_mg_l": 710, "temperature_c": 25.0},
  "purified": {"ph": 7.1, "turbidity_ntu": 0.6, "tds_mg_l": 420, "temperature_c": 24.8}
}
```

Send `POST /api/v1/readings` with header `X-Device-Key: dev-jw01-change-me` only in local demo mode. A separate key is assigned to each device. Timestamps must include an offset or `Z`; repeated device/timestamp pairs are rejected with HTTP 409. Invalid sensor ranges fail validation.

## Interpretation of thresholds

The rule engine uses IS 10500 values as screening thresholds: pH 6.5–8.5 (no relaxation), turbidity 1 NTU acceptable / 5 NTU permissible in absence of an alternate source, and TDS 500 / 2000 mg/L. It raises warnings above the acceptable value and critical alerts above the permissible limit; pH outside 6.5–8.5 is critical. This is a simplified software screening rule, not a legal, clinical or full water-safety determination.
