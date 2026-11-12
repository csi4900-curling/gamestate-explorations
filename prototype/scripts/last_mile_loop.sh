#!/usr/bin/env bash
# Durable last-mile keeper: run the idempotent health check until the pipeline
# complete marker exists. Designed to be started by a user systemd service.
set -uo pipefail

ROOT=/home/user/curling-project
BASE="$ROOT/validation/full-match-development-2026-10-23"
COMPLETE="$BASE/final/pipeline-complete.json"
LOG="$BASE/last-mile.log"

exec >>"$LOG" 2>&1
while [ ! -f "$COMPLETE" ]; do
  echo "--- $(date '+%F %T') last-mile health check"
  "$ROOT/prototype/scripts/check_pipeline_health.sh" || true
  sleep 300
done
echo "--- $(date '+%F %T') pipeline-complete exists; last-mile loop exiting"
