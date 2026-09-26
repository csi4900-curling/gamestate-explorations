"""Secondary same-recording cap check; no metric ground truth for Canada–Korea."""

from pathlib import Path
import sys, json, hashlib
import numpy as np, cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vision_core import ViewCalibrator
from body_localization import detect_and_localize, transported_reference_camera
from stone_accuracy import match_observations

cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
refined = json.loads((ROOT / "rectification/calibration.json").read_text())
refs = json.loads((ROOT / "vision/annotations/detection-reference.json").read_text())
cal = {name: ViewCalibrator(view, ROOT / "vision/frames") for name, view in cfg["views"].items()}
rows = []
for f in refs["frames"]:
    name = f["panel"]
    c = cal[name]
    image = cv2.imread(str(ROOT / "vision/frames" / f"{f['timestamp_s']:05d}.jpg"))
    _, r = c.register(
        image, is_reference=f"{f['timestamp_s']:05d}.jpg" == c.view["reference_frame"]
    )
    H = None
    registered = None
    if r["status"] in ["registered", "reference"]:
        A = np.array(r.get("reference_to_current", np.eye(3)))
        H = np.array(refined[name]["refined_H"]) @ np.linalg.inv(A)
        registered = cv2.warpPerspective(c.reference, A, (image.shape[1], image.shape[0]))
    prior = (
        transported_reference_camera(np.array(refined[name]["refined_H"]), H, c.view["region"])
        if H is not None
        else None
    )
    preds, d = detect_and_localize(image, H, c.view, registered, prior)
    preds = [
        p
        for p in preds
        if not any(
            x0 <= p["pixel_center"][0] <= x1 and y0 <= p["pixel_center"][1] <= y1
            for x0, y0, x1, y1 in f["ignore_boxes"]
        )
    ]
    labels = [
        {"colour": colour, "pixel": [x, y], "matching_radius_px": 20} for x, y, colour in f["caps"]
    ]
    pairs, fp, fn = match_observations(preds, labels)
    rows.append(
        {
            "timestamp_s": f["timestamp_s"],
            "camera": name,
            "original_split": f["split"],
            "tp": len(pairs),
            "fp": len(fp),
            "fn": len(fn),
            "localized_proposals": sum(p["ground_position_m"] is not None for p in preds),
            "position_accuracy": None,
        }
    )
summary = {
    split: {
        k: sum(r[k] for r in rows if r["original_split"] == split)
        for k in ["tp", "fp", "fn", "localized_proposals"]
    }
    for split in ["development", "check"]
}
result = {
    "model_sha256": hashlib.sha256((ROOT / "body_localization.py").read_bytes()).hexdigest(),
    "summary": summary,
    "frames": rows,
    "scope": "Existing Canada–Korea cap labels, previously inspected. This checks detection only. Height-corrected metric accuracy remains unmeasured on this recording.",
}
(ROOT / "body-localization/transfer-check.json").write_text(json.dumps(result, indent=2))
print(json.dumps(summary, indent=2))
