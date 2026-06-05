#!/usr/bin/env bash
#
# End-to-end pipeline: Extract + Load (Python) -> Transform + Test (dbt).
# Idempotent and safe to re-run; designed to be driven by cron.
#
#   ./run_pipeline.sh
#
# Cron example (every day at 08:00 — adjust the path):
#   0 8 * * * cd ~/Documents/Development/SpotifyE2EPipeline && ./run_pipeline.sh >> pipeline.log 2>&1
#
set -euo pipefail

# Always run from the repo root (where this script lives).
cd "$(dirname "$0")"

# cron runs with a minimal PATH that won't include Homebrew — add the usual
# locations so `docker` / `colima` resolve whether on Intel or Apple Silicon.
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] pipeline start ==="

# 1. Make sure the Docker engine (Colima) and Postgres are up.
if command -v colima >/dev/null 2>&1; then
    colima status >/dev/null 2>&1 || colima start
fi
docker compose up -d

# 2. Activate the project virtualenv (dbt + extract deps live here).
# shellcheck source=/dev/null
source .venv/bin/activate

# 3. Extract + Load: pull recent plays + Last.fm tags into the raw schema.
echo "--- extract + load ---"
python -m src.load.load_to_postgres

# 4. Transform + Test: build the analytics star schema and run all data tests.
echo "--- dbt build (run + test) ---"
export DBT_SEND_ANONYMOUS_USAGE_STATS=False   # avoids telemetry SSL noise on this machine
cd dbt
dbt build --profiles-dir .

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] pipeline done ==="
