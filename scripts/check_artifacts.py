"""Recompute stored headline metrics and associations without re-running video inference."""

from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from cross_view import connect
from pre_gate_geometry import audit_path
from reproduce import differences


def read(path):
    return json.loads((ROOT / path).read_text())


protocol = read("prototype/stone-accuracy/protocol.json")
for name, expected in protocol["sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
body = read("prototype/body-localization/results.json")
assert (
    hashlib.sha256((ROOT / "prototype/body_localization.py").read_bytes()).hexdigest()
    == body["model_sha256"]
)
primary = [f for f in body["frames"] if f["primary"]]
labels = [r for f in primary for r in f["labels"]]
errors = []
for r in labels:
    if r["error_cm"] is not None:
        calculated = float(
            100 * np.linalg.norm(np.array(r["predicted_metric_m"]) - r["reference_m"])
        )
        assert abs(calculated - r["error_cm"]) < 1e-9
        errors.append(calculated)
assert len(labels) == 48 and len(errors) == 46 and sum(e <= 10 for e in errors) == 40
assert (
    abs(
        np.sqrt(np.mean(np.square(errors)))
        - body["summaries"]["primary_all"]["automatic_position"]["rmse_cm"]
    )
    < 1e-9
)
pred = read("prototype/throw-analysis/predictions.json")
assert (
    hashlib.sha256((ROOT / "prototype/throw_detection.py").read_bytes()).hexdigest()
    == pred["model_sha256"]
)
ref = ROOT / "prototype/throw-analysis/reference.json"
assert (
    hashlib.sha256(ref.read_bytes()).hexdigest()
    == (ref.parent / "reference.sha256").read_text().strip()
)
for r in read("prototype/cross-view/results.json")["throws"]:
    s = read("prototype/throw-segments/" + r["id"] + ".json")
    d = read("prototype/cross-view/" + r["id"] + "-departure.json")
    delta = differences(connect(s, d), r)
    assert not delta, (r["id"], delta)
for r in read("prototype/pre-gate-audit/results.json")["throws"]:
    # Different numerical builds can differ at machine precision (~1e-16 px).
    # Preserve the reproduction runner's fixed 1e-9 tolerance; compare structure too.
    delta = differences(
        audit_path([p["pixel"] for p in r["points"]])["endpoint_line"], r["endpoint_line"]
    )
    assert not delta, (r["id"], delta)
print(
    "Frozen inputs verified; 48-target metrics, 16 cross-view decisions and all pre-gate fits recomputed."
)
