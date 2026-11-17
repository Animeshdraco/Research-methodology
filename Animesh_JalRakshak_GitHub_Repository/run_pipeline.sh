#!/usr/bin/env bash
# Backwards-compatible entry point for the complete data + API test pipeline.
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_all.sh"
