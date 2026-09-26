"""Freeze protocol and existing labels before running the automatic benchmark."""

from pathlib import Path
import sys, json, csv, hashlib, datetime
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = ROOT.parent / "feasibility"
OUT = ROOT / "stone-accuracy"
from vision_core import project

manual = json.loads((BASE / "annotations/manual.json").read_text())
Hs = json.loads((BASE / "results/homographies.json").read_text())["matrices"]
comparisons = {
    (r["frame"], r["observation"]): r
    for r in csv.DictReader((BASE / "results/stone_comparisons.csv").open())
}
frames = []
for f in manual["frames"]:
    H = np.array(Hs[f["id"]]) @ np.diag([0.5, 0.5, 1.0])
    inv = np.linalg.inv(H)
    labels = []
    for s in f["stones"]:
        pixel = np.array(s["pixel"], float) * 2
        xy = project(H, [pixel])[0]
        r = comparisons.get((f["id"], s["id"]))
        target = None
        if r and r["matched"] == "True":
            target = [float(r["reference_x_m"]), float(r["reference_y_m"])]
        diameter = np.linalg.norm(
            np.diff(project(inv, [[xy[0] - 0.145, xy[1]], [xy[0] + 0.145, xy[1]]]), axis=0)
        )
        labels.append(
            {
                "id": s["id"],
                "colour": {"R": "red", "Y": "yellow"}[s["colour"]],
                "pixel": pixel.tolist(),
                "matching_radius_px": float(0.75 * diameter),
                "manual_metric_m": (xy * f["diagram_sign"]).tolist(),
                "reference_m": target,
                "reference_id": r["reference"] if target is not None else None,
                "in_house_scope": bool(np.linalg.norm(target if target is not None else xy) <= 2.0),
                "reference_status": "linked_from_existing_manual_audit"
                if target is not None
                else "no_trusted_diagram_link",
            }
        )
    ignores = []
    for s in f["excluded_stones"]:
        pixel = np.array(s["pixel"], float) * 2
        xy = project(H, [pixel])[0]
        diameter = np.linalg.norm(
            np.diff(project(inv, [[xy[0] - 0.145, xy[1]], [xy[0] + 0.145, xy[1]]]), axis=0)
        )
        ignores.append(
            {
                "colour": {"R": "red", "Y": "yellow"}[s["colour"]],
                "pixel": pixel.tolist(),
                "matching_radius_px": float(0.75 * diameter),
                "reason": s["reason"],
            }
        )
    frames.append(
        {
            "id": f["id"],
            "time_s": f["timestamp_s"],
            "end": f["end"],
            "shot": f["shot"],
            "tier": f["tier"],
            "pairing_status": f["pairing_status"],
            "diagram_sign": f["diagram_sign"],
            "image": f["original_image"],
            "H": H.tolist(),
            "labels": labels,
            "ignored_moving_stones": ignores,
            "notes": f["notes"],
            "primary": f["id"] != "t398" and f["pairing_status"] != "excluded_unsettled",
            "evaluation_colours": ["red"]
            if f["pairing_status"] == "partial_stationary"
            else ["red", "yellow"],
        }
    )
files = [
    "prototype/vision_core.py",
    "prototype/stone_accuracy.py",
    "feasibility/annotations/manual.json",
    "feasibility/results/homographies.json",
    "feasibility/results/stone_comparisons.csv",
    "feasibility/sources/owg2018_final_records.csv",
]
protocol = {
    "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "purpose": "Frozen automatic colour-cap detector vs independent published diagram coordinates, using existing manually calibrated frames and fixed identity links.",
    "prediction_model": "colour-cap-baseline-v2, unchanged. No clean background image for this new source; optional reference subtraction disabled.",
    "calibration": "Existing per-frame manual ice calibration; 9 homographies and 2 affine fallbacks. This is conditional on supplied calibration, not automatic whole-video performance.",
    "domain": "Visible labelled stones within 2 m of tee by frozen diagram position, or manual projection when no diagram link. Predictions matched to such stones count even if predicted outside 2 m. Unmatched predictions inside 2 m count as false proposals. Partial frames evaluate red only.",
    "matching": "Colour-constrained maximum-cardinality one-to-one assignment in original pixels, within 0.75 nominal projected stone diameters of existing manual body centre. No metric error gate on automatically matched positions.",
    "position_reference": "Published Olympic shot diagrams via pinned CurlR extraction; not physical survey. Existing manual-to-diagram links fixed before automatic inference; those links were originally selected using a 0.5 m manual-position gate, so reference coverage is selected.",
    "primary_exclusions": [
        "t398 duplicates t414 board; report separately",
        "t469 unsettled; diagnostic only",
        "Moving excluded stones and unobserved/occluded stones have no positional truth",
    ],
    "thresholds_cm": [5, 10, 20, 50],
    "known_limits": [
        "Previously inspected same-match reference collection, not blind evaluation",
        "Repeated stones across shots are correlated",
        "Manual stone labels and calibration from same AI annotator",
        "Automatic detector developed on a different recording; no retuning for this run",
        "Diagram scale approx 1.524 cm/pixel; placement error unknown",
        "No equivalent physical-position reference exists for current Canada–Korea low-angle clip",
    ],
    "sha256": {f: hashlib.sha256((ROOT.parent / f).read_bytes()).hexdigest() for f in files},
    "frames": frames,
}
path = OUT / "protocol.json"
if path.exists():
    raise SystemExit("Protocol already exists; refusing to overwrite evaluation freeze")
path.write_text(json.dumps(protocol, indent=2))
print("Frozen", len(frames), "frames; primary", sum(f["primary"] for f in frames))
