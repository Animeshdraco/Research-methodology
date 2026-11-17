# Local setup and run guide

## Requirements

- Python 3.10 or newer (tested in the authoring environment with Python 3.13).
- A terminal and a browser. No cloud account is required for the local software prototype.

## Install and execute

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
./run_all.sh
./start_local.sh
```

On Windows without Bash, run the commands inside `run_all.sh` individually in the same order. The server command is `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000`.

Open `http://127.0.0.1:8000/` for the API-connected dashboard and `http://127.0.0.1:8000/docs` for the interactive API documentation. The dashboard should show its API-connected/source indicator. Stop the server with Ctrl+C.

## Rebuild and test

`./run_all.sh` regenerates the 504-row synthetic dataset with seed 42, forecast metrics, anomaly scores, ten sensitivity scenarios plus baseline, seeds the SQLite demo database, and runs the automated tests. The seed loader is safe to repeat: it is idempotent by device/timestamp and can also replace the database using `--replace`.

## Development credentials warning

The default `dev-jw01-change-me`, `dev-jw02-change-me` and `dev-jw03-change-me` keys are for local demonstration only. Before any real device experiment, set `JALRAKSHAK_DEVICE_KEYS` to a JSON mapping of device IDs to strong unique keys, configure HTTPS and certificate validation, and do not expose this development server directly to the internet.
