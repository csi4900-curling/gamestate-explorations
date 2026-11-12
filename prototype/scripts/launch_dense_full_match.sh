#!/usr/bin/env bash
# Wait for the observation-only run to finish, build the frozen aggregate, then
# start the all-events dense orchestrator. Safe to run repeatedly.
set -euo pipefail

ROOT=/home/user/curling-project
BASE="$ROOT/validation/full-match-development-2026-10-23"
RUN="$BASE/directional-full-match/attempt-0011"
FINAL="$BASE/final"
CONFIG=/home/user/curling-baseline-recovery-development/prototype/config/learned-directional-two-view-development.example.json
FINISHED="$BASE/directional-full-match/finished.json"
LOG="$BASE/dense-launch.log"

mkdir -p "$FINAL"
exec >>"$LOG" 2>&1
echo "--- $(date '+%F %T') waiting for $FINISHED"
while [ ! -f "$FINISHED" ]; do
  sleep 60
done
echo "--- $(date '+%F %T') observation finished"
if [ -f "$FINAL/HOLD-DENSE" ] || [ -f "$FINAL/SKIP-DENSE" ]; then
  echo "dense stage held by $FINAL/HOLD-DENSE; not starting"
  exit 0
fi
if [ ! -f "$RUN/events.json" ]; then
  echo "events.json missing; refusing to start dense"
  exit 1
fi
if [ -f "$FINAL/two-view-tracking/result.json" ]; then
  echo "dense result already exists; nothing to do"
  exit 0
fi
if [ ! -f "$FINAL/aggregate.json" ]; then
  echo "building aggregate"
  cd "$ROOT"
  PYTHONPATH="$ROOT" "$ROOT/feasibility/scripts/python.sh" -c "
import json
from prototype.scripts.finalize_full_match import build_aggregate
cfg=json.load(open('$CONFIG'))
build_aggregate('$BASE/source-1080p.mp4', '$RUN', '$FINAL/aggregate.json', cfg['local_hog_y_m'])
print('aggregate built')
"
fi
if [ ! -f "$FINAL/resolved-projection-heights.json" ]; then
  python3 -c "
import json
cfg=json.load(open('$CONFIG'))
json.dump(cfg['feature_heights_m'], open('$FINAL/resolved-projection-heights.json','w'), indent=2)
"
fi
if [ ! -f "$FINAL/event-colours.json" ]; then
  echo "classifying post-hoc event colours"
  PYTHONPATH="/home/user/curling-colour-deps:$ROOT" CURLING_PYTHON="$ROOT/.venv-detector/bin/python" \
    "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/classify_event_colours.py" \
    --video "$BASE/source-1080p.mp4" --events "$RUN/events.json" \
    --output "$FINAL/event-colours.json" \
    --config /home/user/curling-colour-integration-development/prototype/config/stone-colour-run.json \
    --references "$BASE/source-line-references-all-ends.json" \
    || echo "colour pass failed; continuing to dense"
fi
if [ ! -f "$FINAL/handoff-colours.json" ]; then
  echo "checking handoff colour consistency"
  PYTHONPATH="/home/user/curling-colour-deps:$ROOT" CURLING_PYTHON="$ROOT/.venv-detector/bin/python" \
    "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/check_handoff_colours.py" \
    --video "$BASE/source-1080p.mp4" --aggregate "$FINAL/aggregate.json" \
    --match-observations "$RUN/match-observations.jsonl" \
    --event-colours "$FINAL/event-colours.json" \
    --output "$FINAL/handoff-colours.json" \
    --config /home/user/curling-colour-integration-development/prototype/config/stone-colour-run.json \
    || echo "handoff colour check failed; continuing to dense"
fi
mkdir -p "$RUN/tracking-progress"
if systemctl --user is-active --quiet curling-dense-full-match.service; then
  echo "dense service already active"
  exit 0
fi
echo "starting dense service"
systemd-run --user --unit=curling-dense-full-match --collect \
  --property=WorkingDirectory="$ROOT" \
  --property=Restart=on-failure --property=RestartSec=30 \
  --setenv=CURLING_PYTHON="$ROOT/.venv-detector/bin/python" \
  --setenv=PYTHONPATH=. \
  "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/full_match_dense.py" \
  --video "$BASE/source-1080p.mp4" --aggregate "$FINAL/aggregate.json" \
  --output "$FINAL/two-view-tracking" \
  --checkpoint "$ROOT/models/cotracker3/scaled_online.pth" \
  --stone-detector-checkpoint "$ROOT/research/shared-stone-detector-2026-10-22/stones_v4.pt" \
  --projection-config "$FINAL/resolved-projection-heights.json" \
  --tracking-progress-dir "$RUN/tracking-progress" \
  --device cpu --threads 4
echo "dense service start requested"
