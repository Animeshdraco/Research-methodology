#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
python analysis/scripts/01_generate_data.py --seed 42
python analysis/scripts/02_evaluate_models.py
python analysis/scripts/03_robustness_sweep.py
python backend/seed_demo.py --replace
python -m pytest backend/tests analysis/tests -q
