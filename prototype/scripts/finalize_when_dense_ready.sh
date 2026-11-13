#!/usr/bin/env bash
# Wait for the all-events dense result, then finalize and browser-check it.
set -euo pipefail

ROOT=/home/user/curling-project
BASE="$ROOT/validation/full-match-development-2026-10-23"
RUN="$BASE/directional-full-match/attempt-0011"
FINAL="$BASE/final"
LOG="$BASE/finalize-launch.log"
DENSE_RESULT="$FINAL/two-view-tracking/result.json"
DONE="$FINAL/pipeline-complete.json"
CONFIG=/home/user/curling-baseline-recovery-development/prototype/config/learned-directional-two-view-development.example.json

mkdir -p "$FINAL"
exec >>"$LOG" 2>&1
echo "--- $(date '+%F %T') waiting for $DENSE_RESULT"
while [ ! -f "$DENSE_RESULT" ]; do
  [ -f "$DONE" ] && exit 0
  sleep 120
done
if [ -f "$DONE" ]; then
  echo "already complete"
  exit 0
fi
echo "--- $(date '+%F %T') dense result present; finalizing"
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
  --event-colours "$FINAL/event-colours.json" \
  --handoff-colours "$FINAL/handoff-colours.json" \
  --dense-dir "$FINAL/two-view-tracking"
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
    "dense_result": "$DENSE_RESULT",
    "browser_check": "$FINAL/viewer/browser-verification.json",
    "delivery_check": "$FINAL/delivery-check.json",
    "quality_acceptance_verified": False,
    "note": "Automated finalization; inspect the report evidence boundary. Physical identity, metric trajectory and complete board accuracy remain unmeasured."
}
Path("$DONE").write_text(json.dumps(payload, indent=2) + "\\n")
print(json.dumps(payload))
PY
echo "--- $(date '+%F %T') delivery checklist"
PYTHONPATH=. "$ROOT/feasibility/scripts/python.sh" "$ROOT/prototype/scripts/check_final_delivery.py" \
  --final-dir "$FINAL"
echo "--- $(date '+%F %T') complete"
