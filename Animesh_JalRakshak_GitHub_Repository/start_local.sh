#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -f backend/data/jalrakshak.sqlite3 ]]; then
  python backend/seed_demo.py --replace
fi
python - <<'PY'
import sqlite3
from pathlib import Path
p = Path('backend/data/jalrakshak.sqlite3')
count = 0
if p.exists():
    with sqlite3.connect(p) as con:
        try:
            count = con.execute('SELECT COUNT(*) FROM readings').fetchone()[0]
        except sqlite3.OperationalError:
            count = 0
if count == 0:
    raise SystemExit('Database has no demo readings. Run: python backend/seed_demo.py --replace')
print(f'Starting local API with {count} stored readings')
PY
exec uvicorn backend.app:app --host 127.0.0.1 --port 8000
