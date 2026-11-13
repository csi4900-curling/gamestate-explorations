#!/usr/bin/env bash
# Finalize the observation/aggregate deliverable without the CoTracker dense
# stage, after the owner removed it from scope. Waits for the observation's
# finished.json, builds the aggregate plus colour/handoff evidence, writes the
# report/viewer/evaluation, and runs the checklist with --skip-dense.
set -euo pipefail

ROOT=/home/user/curling-project
BASE="$ROOT/validation/full-match-development-2026-10-23"
FINAL="$BASE/final"
FINISHED="$BASE/directional-full-match/finished.json"
DONE="$FINAL/pipeline-complete.json"
CONFIG=/home/user/curling-baseline-recovery-development/prototype/config/learned-directional-two-view-development.example.json
LOG="$BASE/finalize-launch.log"

mkdir -p "$FINAL"
exec >>"$LOG" 2>&1
echo "--- $(date '+%F %T') waiting for $FINISHED"
while [ ! -f "$FINISHED" ]; do
  [ -f "$DONE" ] && exit 0
  sleep 120
done
if [ -f "$DONE" ]; then
  echo "already complete"
  exit 0
fi
RUN=$(python3 -c "import json;print(json.load(open('$FINISHED'))['output'])")
echo "--- $(date '+%F %T') observation finished; run=$RUN; dense skipped by owner decision"

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

if [ ! -f "$FINAL/event-colours.json" ]; then
  echo "classifying post-hoc event colours"
  PYTHONPATH="/home/user/curling-colour-deps:$ROOT" CURLING_PYTHON="$ROOT/.venv-detector/bin/python" \
    "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/classify_event_colours.py" \
    --video "$BASE/source-1080p.mp4" --events "$RUN/events.json" \
    --output "$FINAL/event-colours.json" \
    --config /home/user/curling-colour-integration-development/prototype/config/stone-colour-run.json \
    --references "$BASE/source-line-references-all-ends.json" \
    || echo "colour pass failed; continuing without event colour"
fi
if [ ! -f "$FINAL/handoff-colours.json" ] && [ -f "$FINAL/event-colours.json" ]; then
  echo "checking handoff colour consistency"
  PYTHONPATH="/home/user/curling-colour-deps:$ROOT" CURLING_PYTHON="$ROOT/.venv-detector/bin/python" \
    "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/check_handoff_colours.py" \
    --video "$BASE/source-1080p.mp4" --aggregate "$FINAL/aggregate.json" \
    --match-observations "$RUN/match-observations.jsonl" \
    --event-colours "$FINAL/event-colours.json" \
    --output "$FINAL/handoff-colours.json" \
    --config /home/user/curling-colour-integration-development/prototype/config/stone-colour-run.json \
    || echo "handoff colour check failed; continuing without handoff colour"
fi

COLOUR_ARGS=()
[ -f "$FINAL/event-colours.json" ] && COLOUR_ARGS+=(--event-colours "$FINAL/event-colours.json")
[ -f "$FINAL/handoff-colours.json" ] && COLOUR_ARGS+=(--handoff-colours "$FINAL/handoff-colours.json")

echo "--- $(date '+%F %T') finalizing without dense"
cd "$ROOT"
PYTHONPATH=. "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/finalize_full_match.py" \
  --video "$BASE/source-1080p.mp4" \
  --run-dir "$RUN" --output-dir "$FINAL" --resume \
  --match-state-config "$CONFIG" \
  --references "$BASE/source-line-references-all-ends.json" \
  --score-reference "$BASE/score-systematic-source-review/reference-with-row-context.json" \
  --final-totals "$BASE/score-stage-summary.json" \
  --geometry-review "$BASE/geometry-source-review/summary.json" \
  --identity-review "$BASE/receiving-query-identity-review.json" \
  --identity-conflicts "$BASE/receiving-query-detector-conflicts.json" \
  "${COLOUR_ARGS[@]}"

echo "--- $(date '+%F %T') viewer check"
PYTHONPATH=. "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/verify_rink_viewer.py" \
  --viewer "$FINAL/viewer/index.html" \
  --events L00001,L00017,L00062,L00140

python3 - <<PY
import json
from pathlib import Path
payload = {
    "completed_at": "$(date -Iseconds)",
    "final_dir": "$FINAL",
    "report": "$FINAL/report.md",
    "viewer": "$FINAL/viewer/index.html",
    "dense": "not_run_by_owner_decision",
    "browser_check": "$FINAL/viewer/browser-verification.json",
    "delivery_check": "$FINAL/delivery-check.json",
    "quality_acceptance_verified": False,
    "scope_amendment": "CoTracker/dense removed by owner decision 2026-10-25; all-events dense not run; the original objective's dense requirement is not met.",
    "note": "Observation/aggregate deliverable only. Physical identity, metric trajectory and complete board accuracy remain unmeasured."
}
Path("$DONE").write_text(json.dumps(payload, indent=2) + "\n")
print(json.dumps(payload))
PY

echo "--- $(date '+%F %T') delivery checklist (dense skipped)"
PYTHONPATH=. "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/check_final_delivery.py" \
  --final-dir "$FINAL" --skip-dense
echo "--- $(date '+%F %T') complete"
