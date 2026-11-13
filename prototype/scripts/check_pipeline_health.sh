#!/usr/bin/env bash
# Idempotent health check for the full-match pipeline services.
# Safe to run at any time; it starts only missing units.
set -uo pipefail

ROOT=/home/user/curling-project
BASE="$ROOT/validation/full-match-development-2026-10-23"
FINISHED="$BASE/directional-full-match/finished.json"
SKIP="$BASE/final/SKIP-DENSE"
FINISHED="$BASE/directional-full-match/finished.json"
DENSE_RESULT="$BASE/final/two-view-tracking/result.json"
COMPLETE="$BASE/final/pipeline-complete.json"

active() { systemctl --user show -p ActiveState --value "$1" 2>/dev/null | grep -Eq "^(active|activating|reloading)$"; }

if [ -f "$COMPLETE" ]; then
  echo "pipeline-complete exists; no services needed"
  active curling-keep-awake || echo "note: keep-awake inactive after completion"
  exit 0
fi

if [ ! -f "$FINISHED" ]; then
  if ! active curling-directional-full-match.service; then
    echo "starting observation service"
    systemctl --user start --no-block curling-directional-full-match.service
  fi
  if ! active curling-watchdog.service; then
    echo "starting observation watchdog"
    systemd-run --user --unit=curling-watchdog --collect \
      bash -c 'while [ ! -f /home/user/curling-project/validation/full-match-development-2026-10-23/directional-full-match/finished.json ]; do if ! pgrep -f run_resumable_learned_match.py >/dev/null 2>&1; then systemctl --user start --no-block curling-directional-full-match.service; fi; sleep 60; done'
  fi
else
  echo "observation finished"
fi

if ! active curling-keep-awake.service; then
  echo "starting keep-awake"
  systemd-run --user --unit=curling-keep-awake --collect \
    systemd-inhibit --what=idle:sleep --mode=block \
    --who=curling-full-match --why="Full-match observation and dense tracking" \
    sleep infinity
fi

if [ ! -f "$DENSE_RESULT" ] && [ ! -f "$BASE/final/HOLD-DENSE" ] && [ ! -f "$SKIP" ] && ! active curling-dense-when-ready.service; then
  echo "starting dense-when-ready"
  systemd-run --user --unit=curling-dense-when-ready --collect \
    --property=WorkingDirectory="$ROOT" \
    bash "$ROOT/prototype/scripts/launch_dense_full_match.sh"
fi

if [ -f "$SKIP" ]; then
  if [ ! -f "$BASE/final/pipeline-complete.json" ] && ! active curling-finalize-when-ready.service; then
    echo "starting no-dense finalize"
    systemd-run --user --unit=curling-finalize-when-ready --collect \
      --property=WorkingDirectory="$ROOT" \
      bash "$ROOT/prototype/scripts/finalize_without_dense.sh"
  fi
elif [ -f "$DENSE_RESULT" ] && ! active curling-finalize-when-ready.service; then
  echo "starting finalize-when-ready"
  systemd-run --user --unit=curling-finalize-when-ready --collect \
    --property=WorkingDirectory="$ROOT" \
    bash "$ROOT/prototype/scripts/finalize_when_dense_ready.sh"
fi

echo "--- unit status"
for unit in curling-directional-full-match.service curling-watchdog.service \
            curling-keep-awake.service curling-dense-when-ready.service \
            curling-finalize-when-ready.service curling-dense-full-match.service; do
  printf '%-40s %s\n' "$unit" "$(systemctl --user is-active "$unit" 2>/dev/null || true)"
done
