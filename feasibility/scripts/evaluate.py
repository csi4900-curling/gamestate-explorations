"""Reproduce manual calibration, independent landmark validation and record comparisons."""

from pathlib import Path
import json, math
import cv2
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
ANN = json.loads((ROOT / "annotations/manual.json").read_text())
RECORDS = pd.read_csv(ROOT / "sources/owg2018_final_records.csv")
RNG = np.random.default_rng(20260923)
GATE_M = 0.50  # fixed before running; unmatched points remain visible in outputs
DIAGRAM_CENTRE = np.array([149.5, 159.5])
DIAGRAM_SCALE = 1.829 / 120

from geometry import project, world, has_projective_basis, fit


def stats(x):
    a = np.asarray(x, dtype=float)
    return (
        dict(
            n=len(a),
            median_cm=float(np.median(a) * 100),
            rmse_cm=float(np.sqrt(np.mean(a * a)) * 100),
            max_cm=float(a.max() * 100),
            p95_cm=float(np.percentile(a, 95) * 100),
        )
        if len(a)
        else dict(n=0)
    )


def dump_csv(name, rows):
    pd.DataFrame(rows).to_csv(OUT / name, index=False)


def font(n):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", n)
    except OSError:
        return ImageFont.load_default(size=n)


summary = []
landmarks = []
comparisons = []
stone_rows = []
homographies = {}
allcheck = []
house_errors = []
frame_house_rmse = []
for f in ANN["frames"]:
    p = np.array(list(f["fit"].values()), float)
    w = np.array([world(k) for k in f["fit"]])
    model = "homography" if has_projective_basis(w) else "affine"
    H = fit(p, w, model)
    homographies[f["id"]] = H.tolist()
    cp = np.array(list(f["check"].values()), float)
    cw = np.array([world(k) for k in f["check"]])
    ce = np.linalg.norm(project(H, cp) - cw, axis=1)
    fe = np.linalg.norm(project(H, p) - w, axis=1)
    allcheck.extend(ce)
    for role, points in [("fit", f["fit"]), ("check", f["check"])]:
        for key, px in points.items():
            pred = project(H, [px])[0]
            gt = world(key)
            landmarks.append(
                dict(
                    frame=f["id"],
                    role=role,
                    landmark=key,
                    x_px=px[0],
                    y_px=px[1],
                    x_m=gt[0],
                    y_m=gt[1],
                    pred_x_m=pred[0],
                    pred_y_m=pred[1],
                    error_cm=float(np.linalg.norm(pred - gt) * 100),
                )
            )
    sp = np.array([s["pixel"] for s in f["stones"]], float)
    pred = project(H, sp) * f["diagram_sign"]
    # Sensitivity of predicted stone centres to independent 1/2-pixel normal noise on calibration clicks.
    sensitivity = {}
    for sigma in [1, 2]:
        deviations = []
        for _ in range(500):
            hp = fit(p + RNG.normal(0, sigma, p.shape), w, model)
            deviations.extend(np.linalg.norm(project(hp, sp) - project(H, sp), axis=1))
        sensitivity[f"fit_click_sigma_{sigma}px_p95_cm"] = float(
            np.percentile(deviations, 95) * 100
        )
    row = dict(
        frame=f["id"],
        model=model,
        homography_identifiable=bool(model == "homography"),
        timestamp_s=f["timestamp_s"],
        end=f["end"],
        shot=f["shot"],
        tier=f["tier"],
        pairing_status=f["pairing_status"],
        fit_points=len(p),
        check_points=len(cp),
        fit_rmse_cm=stats(fe)["rmse_cm"],
        check_median_cm=stats(ce)["median_cm"],
        check_rmse_cm=stats(ce)["rmse_cm"],
        check_max_cm=stats(ce)["max_cm"],
        **sensitivity,
    )
    for s, xy in zip(f["stones"], pred):
        stone_rows.append(
            dict(
                frame=f["id"],
                stone=s["id"],
                colour=s["colour"],
                x_px=s["pixel"][0],
                y_px=s["pixel"][1],
                x_m=xy[0],
                y_m=xy[1],
            )
        )
    ref = RECORDS[(RECORDS.End == f["end"]) & (RECORDS.Shot == f["shot"])]
    assert len(ref) == 1
    ref = ref.iloc[0]
    per = []
    if f["pairing_status"] != "excluded_unsettled":
        for colour in "RY":
            ii = [i for i, s in enumerate(f["stones"]) if s["colour"] == colour]
            truth = []
            refids = []
            for j in range(1, 7):
                x, y = ref[f"{colour}{j}X"], ref[f"{colour}{j}Y"]
                # Diagram top/bottom storage strips are NOT playing surface. Do not match removed/unused stones.
                if np.isfinite(x) and np.isfinite(y) and 0 < x < 299 and 40 < y < 580:
                    truth.append((np.array([x, y]) - DIAGRAM_CENTRE) * DIAGRAM_SCALE)
                    refids.append(f"{colour}{j}")
            if not ii:
                continue
            truth = np.array(truth)
            pp = pred[ii]
            if not len(truth):
                continue
            costs = np.linalg.norm(pp[:, None, :] - truth[None, :, :], axis=2)
            # Dummy columns prevent forcing an observation to a distant stone; one-to-one, colour-constrained.
            aug = np.c_[costs, np.full((len(ii), len(ii)), GATE_M)]
            a, b = linear_sum_assignment(aug)
            for ai, bi in zip(a, b):
                obs = f["stones"][ii[ai]]
                xy = pp[ai]
                valid = bi < len(truth) and costs[ai, bi] < GATE_M
                target = truth[bi] if valid else np.array([np.nan, np.nan])
                err = float(costs[ai, bi]) if valid else np.nan
                house = bool(
                    np.linalg.norm(xy) <= 2.0 and (not valid or np.linalg.norm(target) <= 2.0)
                )
                item = dict(
                    frame=f["id"],
                    end=f["end"],
                    shot=f["shot"],
                    observation=obs["id"],
                    colour=colour,
                    reference=refids[bi] if valid else "",
                    matched=bool(valid),
                    region="house_2m" if house else "outside_house",
                    pred_x_m=float(xy[0]),
                    pred_y_m=float(xy[1]),
                    reference_x_m=float(target[0]),
                    reference_y_m=float(target[1]),
                    error_cm=float(err * 100),
                )
                comparisons.append(item)
                per.append(item)
                if valid and house:
                    house_errors.append(err)
        errors = [v["error_cm"] / 100 for v in per if v["matched"] and v["region"] == "house_2m"]
        st = stats(errors)
        row.update(
            house_matches=st["n"],
            house_rmse_cm=st.get("rmse_cm"),
            house_median_cm=st.get("median_cm"),
            unmatched_observations=sum(not v["matched"] for v in per),
        )
        if errors:
            frame_house_rmse.append(st["rmse_cm"])
    else:
        row.update(
            house_matches=0, house_rmse_cm=None, house_median_cm=None, unmatched_observations=None
        )
    summary.append(row)
    # Visible overlay; green fit points, cyan independent checks, coloured stone circles.
    im = Image.open(ROOT / f["image"]).convert("RGB")
    d = ImageDraw.Draw(im)
    for role, points, col in [("F", f["fit"], "#50f28b"), ("V", f["check"], "#38cfff")]:
        for key, (x, y) in points.items():
            d.line((x - 6, y, x + 6, y), fill=col, width=2)
            d.line((x, y - 6, x, y + 6), fill=col, width=2)
            d.text(
                (x + 7, y - 13),
                role + ":" + key,
                font=font(13),
                fill=col,
                stroke_width=2,
                stroke_fill="black",
            )
    for s in f["stones"]:
        x, y = s["pixel"]
        col = "#ff7373" if s["colour"] == "R" else "#ffdf45"
        d.ellipse((x - 4, y - 4, x + 4, y + 4), outline=col, width=2)
        d.text(
            (x + 7, y + 5), s["id"], font=font(12), fill=col, stroke_width=2, stroke_fill="black"
        )
    banner = Image.new("RGB", (960, 590), "#101b2b")
    banner.paste(im, (0, 50))
    bd = ImageDraw.Draw(banner)
    bd.text(
        (14, 8),
        f"{f['id']} | End {f['end']}, reference shot {f['shot']} | held-out RMSE {row['check_rmse_cm']:.2f} cm",
        font=font(17),
        fill="white",
    )
    bd.text(
        (14, 30),
        "Green F: fitted landmarks    Cyan V: withheld landmarks    Stone labels: manual visible centres",
        font=font(13),
        fill="#b9c9dc",
    )
    banner.save(OUT / f"{f['id']}_annotated.jpg", quality=94)
    # Rectified image: x/y local, 100 px/m, +/- 2.4m. This visual is not independent validation.
    T = np.array([[100, 0, 240], [0, 100, 240], [0, 0, 1]], float)
    rect = cv2.warpPerspective(cv2.imread(str(ROOT / f["image"])), T @ H, (480, 480))
    cv2.imwrite(str(OUT / f"{f['id']}_rectified.jpg"), rect)

dump_csv("calibration_metrics.csv", summary)
dump_csv("landmark_errors.csv", landmarks)
dump_csv("stone_comparisons.csv", comparisons)
dump_csv("measured_stones.csv", stone_rows)
(OUT / "homographies.json").write_text(
    json.dumps(
        dict(
            pixel_space="960x540 annotation image",
            direction="image pixels to local metres",
            matrices=homographies,
        ),
        indent=2,
    )
    + "\n"
)
# Repeat-state consistency, keyed to independently assigned reference IDs; report only shared matches.
a = {v["reference"]: v for v in comparisons if v["frame"] == "t398" and v["matched"]}
b = {v["reference"]: v for v in comparisons if v["frame"] == "t414" and v["matched"]}
repeat = []
for key in sorted(a.keys() & b.keys()):
    delta = math.hypot(
        a[key]["pred_x_m"] - b[key]["pred_x_m"], a[key]["pred_y_m"] - b[key]["pred_y_m"]
    )
    repeat.append(dict(reference=key, disagreement_cm=delta * 100))
dump_csv("repeat_zoom_consistency.csv", repeat)
# Exclude repeat frame t398 for a non-duplicated descriptive house summary. This is NOT a statistical CI.
unique_errors = [
    v["error_cm"] / 100
    for v in comparisons
    if v["matched"] and v["region"] == "house_2m" and v["frame"] != "t398"
]
overhead_errors = [
    v["error_cm"] / 100
    for v in comparisons
    if v["matched"] and v["region"] == "house_2m" and v["frame"] not in ["t100", "t398"]
]
result = dict(
    overhead_house_reference_discrepancy_repeat_excluded=stats(overhead_errors),
    homography_frames=sum(v["model"] == "homography" for v in summary),
    affine_fallback_frames=sum(v["model"] == "affine" for v in summary),
    frames=len(summary),
    unique_end_shot_keys=len(set((f["end"], f["shot"]) for f in ANN["frames"])),
    landmark_validation=stats(allcheck),
    house_reference_discrepancy_all_frames=stats(house_errors),
    house_reference_discrepancy_repeat_excluded=stats(unique_errors),
    repeat_zoom_consistency=stats([v["disagreement_cm"] / 100 for v in repeat]),
    matching_gate_m=GATE_M,
    diagram_centre_px=DIAGRAM_CENTRE.tolist(),
    diagram_metres_per_pixel=DIAGRAM_SCALE,
    monte_carlo_repetitions=500,
    seed=20260923,
)
(OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    pd.DataFrame(summary)[
        [
            "frame",
            "model",
            "check_points",
            "check_rmse_cm",
            "house_matches",
            "house_rmse_cm",
            "unmatched_observations",
        ]
    ].to_string(index=False)
)
print(json.dumps(result, indent=2))
