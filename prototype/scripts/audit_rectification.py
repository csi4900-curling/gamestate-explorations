"""Audit other timestamps and known synthetic camera transforms, without refitting."""

import json, sys, cv2, numpy as np, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rectification_core import validate_rings, ring_edges, ring_summary
from vision_core import ViewCalibrator, project

folder = ROOT / "rectification"
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
cal = json.loads((folder / "calibration.json").read_text())
rows = []
synthetic = []
for name, view in cfg["views"].items():
    c = ViewCalibrator(view, ROOT / "vision/frames")
    refined = np.array(cal[name]["refined_H"])
    for file in sorted((ROOT / "vision/frames").glob("*.jpg")):
        if file.name == view["reference_frame"]:
            continue
        image = cv2.imread(str(file))
        _, reg = c.register(image)
        row = {"camera": name, "source_time_s": int(file.stem), "registration": reg["status"]}
        if reg["status"] == "registered":
            inv = np.linalg.inv(np.array(reg["reference_to_current"]))
            H = refined @ inv
            good, q = validate_rings(image, H, view["region"])
            row.update(accepted=good, quality=q)
            inner = ring_edges(image, H, 0.610, view["region"], search_px=5.0)
            row["inner_check"] = ring_summary(H, inner)
        else:
            row.update(accepted=False, reason=reg.get("reason"))
        rows.append(row)
    # These tests have known transformation ground truth; they cannot measure real-camera lens distortion.
    for label, A in [
        ("translation", np.array([[1.0, 0, 9], [0, 1.0, -6], [0, 0, 1.0]])),
        (
            "zoom_perspective",
            np.array([[1.025, 0.002, -7], [-0.001, 1.025, -9], [0.000003, 0, 1.0]]),
        ),
    ]:
        im = cv2.warpPerspective(c.reference, A, (1920, 1080))
        _, reg = c.register(im)
        if reg["status"] != "registered":
            synthetic.append({"camera": name, "case": label, "accepted": False})
            continue
        H = refined @ np.linalg.inv(np.array(reg["reference_to_current"]))
        world = np.array(
            [[x, y] for x in np.linspace(-1.7, 1.7, 9) for y in np.linspace(-1.7, 1.7, 9)]
        )
        px = project(np.linalg.inv(refined), world)
        err = np.linalg.norm(project(H, project(A, px)) - world, axis=1)
        good, q = validate_rings(im, H, view["region"])
        synthetic.append(
            {
                "camera": name,
                "case": label,
                "accepted": good,
                "points": len(world),
                "rmse_m": float(np.sqrt(np.mean(err**2))),
                "max_m": float(err.max()),
            }
        )
result = {
    "core_sha256": hashlib.sha256((ROOT / "rectification_core.py").read_bytes()).hexdigest(),
    "other_timestamp_checks": rows,
    "synthetic_known_motion": synthetic,
    "scope": "Other timestamps from the same recording, previously inspected. Not held-out-match validation. Synthetic transforms test implementation, not physical calibration accuracy.",
}
(folder / "audit.json").write_text(json.dumps(result, indent=2))
print("Accepted other timestamp views:", sum(r["accepted"] for r in rows), "/", len(rows))
print(json.dumps(synthetic, indent=2))
