"""Audit the image boundary of source-reviewed Latvia end-six moving paths."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2


SEARCH_BOTTOM_Y = 970  # Existing native-1080p body-template search window.
FRAME_BOTTOM_Y = 1080
SOURCE_START_S = 5670
WITNESS_TIMES_S = (5846, 5847, 5848, 5849)
WITNESS_BOX_XYXY = (1190, 850, 1410, 1080)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def boundary_row(row):
    points = row["compatible_highres_paths"][0]["highres_handle_supported_moving_points"]
    if len(points) < 2:
        raise ValueError("Moving path has fewer than two high-resolution points")
    first, last = points[-2:]
    dt = last["time_s"] - first["time_s"]
    dy = last["center_1080p_px"][1] - first["center_1080p_px"][1]
    if dt <= 0 or dy <= 0:
        raise ValueError("Expected a positive-y, chronological moving tail")
    y = last["center_1080p_px"][1]
    if not 0 <= y < SEARCH_BOTTOM_Y:
        raise ValueError("Saved moving point lies outside the old search window")
    speed = dy / dt
    return {
        "right_proposal_id": row["right_proposal_id"],
        "colour_claim": row["colour_claim"],
        "last_saved_moving_source_time_s": last["time_s"],
        "last_saved_body_center_1080p_px": last["center_1080p_px"],
        "last_observed_vertical_step_px_per_s": round(speed, 3),
        "remaining_to_search_bottom_px": SEARCH_BOTTOM_Y - y,
        "remaining_to_frame_bottom_px": FRAME_BOTTOM_Y - y,
        "constant_image_speed_time_to_frame_bottom_s_diagnostic": round(
            (FRAME_BOTTOM_Y - y) / speed, 3
        ),
    }


def next_second_colour_screen(cap, row):
    points = row["compatible_highres_paths"][0]["highres_handle_supported_moving_points"]
    prior, last = points[-2:]
    dt = last["time_s"] - prior["time_s"]
    source_time = last["time_s"] + 1
    predicted_x = (
        last["center_1080p_px"][0] + (last["center_1080p_px"][0] - prior["center_1080p_px"][0]) / dt
    )
    predicted_y = (
        last["center_1080p_px"][1]
        + (last["center_1080p_px"][1] - prior["center_1080p_px"][1]) / dt
        - 22
    )
    if predicted_y - 90 >= FRAME_BOTTOM_Y:
        return {
            "source_time_s": source_time,
            "status": "predicted_colour_region_outside_frame",
            "colour_components": [],
        }
    cap.set(cv2.CAP_PROP_POS_MSEC, (source_time - SOURCE_START_S) * 1000)
    ok, frame = cap.read()
    if not ok or frame.shape[:2] != (1080, 1920):
        raise ValueError(f"Cannot decode source frame at {source_time}")
    x1, x2 = max(960, int(predicted_x - 100)), min(1920, int(predicted_x + 100))
    y1, y2 = max(650, int(predicted_y - 90)), min(1080, int(predicted_y + 90))
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    if row["colour_claim"] == "yellow":
        mask = cv2.inRange(hsv, (17, 71, 66), (42, 255, 255))
    else:
        mask = cv2.inRange(hsv, (0, 71, 46), (11, 255, 255)) | cv2.inRange(
            hsv, (171, 71, 46), (179, 255, 255)
        )
    count, _, stats, centers = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for i in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[i])
        cx, cy = float(centers[i, 0] + x1), float(centers[i, 1] + y1)
        distance = ((cx - predicted_x) ** 2 + (cy - predicted_y) ** 2) ** 0.5
        if 200 <= area <= 3500 and width >= 7 and height >= 4 and distance <= 30:
            candidates.append(
                {
                    "center_1080p_px": [round(cx, 2), round(cy, 2)],
                    "colour_area_px2": area,
                    "prediction_distance_px": round(distance, 2),
                    "touches_frame_bottom": y1 + y + height >= FRAME_BOTTOM_Y,
                }
            )
    candidates.sort(key=lambda item: item["prediction_distance_px"])
    return {
        "source_time_s": source_time,
        "predicted_cap_center_1080p_px": [round(predicted_x, 2), round(predicted_y, 2)],
        "status": (
            "unique_colour_component_provisional"
            if len(candidates) == 1
            else "abstain_ambiguous_or_absent"
        ),
        "colour_components": candidates,
    }


def witness(cap, time_s):
    cap.set(cv2.CAP_PROP_POS_MSEC, (time_s - SOURCE_START_S) * 1000)
    ok, frame = cap.read()
    if not ok or frame.shape[:2] != (1080, 1920):
        raise ValueError(f"Cannot decode witness source frame at {time_s}")
    x1, y1, x2, y2 = WITNESS_BOX_XYXY
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    yellow = cv2.inRange(hsv, (17, 71, 66), (42, 255, 255))
    count, _, stats, centers = cv2.connectedComponentsWithStats(yellow)
    components = sorted(
        (
            {
                "yellow_pixels": int(stats[i, cv2.CC_STAT_AREA]),
                "center_1080p_px": [
                    round(float(centers[i, 0] + x1), 2),
                    round(float(centers[i, 1] + y1), 2),
                ],
                "touches_frame_bottom": bool(
                    y1 + stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] >= FRAME_BOTTOM_Y
                ),
            }
            for i in range(1, count)
            if stats[i, cv2.CC_STAT_AREA] >= 100
        ),
        key=lambda row: -row["yellow_pixels"],
    )
    return {"source_time_s": time_s, "yellow_components": components}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("body-links", "video", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    links = json.loads(args.body_links.read_text())
    source_hash = digest(args.video)
    if source_hash != links["highres_source_sha256"] or links["source_interval_s"] != [5670, 6670]:
        raise ValueError("High-resolution source differs from linked paths")
    reviewed = [row for row in links["rows"] if row["source_prefix_class"] == "moving_stone_pixels"]
    if len(reviewed) != 16 or any(
        row["body_path_status"] != "unique_compatible_body_path" for row in reviewed
    ):
        raise ValueError("Expected the 16 reviewed, uniquely linked paths")
    rows = [boundary_row(row) for row in reviewed]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Could not open source video")
    try:
        for result, original in zip(rows, reviewed):
            result["next_second_colour_screen"] = next_second_colour_screen(cap, original)
        exemplar = [witness(cap, t) for t in WITNESS_TIMES_S]
    finally:
        cap.release()
    areas = [
        entry["yellow_components"][0]["yellow_pixels"] if entry["yellow_components"] else 0
        for entry in exemplar
    ]
    if not (
        areas[0] >= 100
        and areas[1] >= 100
        and areas[2] >= 100
        and areas[3] == 0
        and exemplar[2]["yellow_components"][0]["touches_frame_bottom"]
    ):
        raise ValueError("Exemplar frame-boundary witness changed")
    output = {
        "status": "postreview_field_of_view_censoring_diagnostic",
        "source_video_sha256": source_hash,
        "body_links_sha256": digest(args.body_links),
        "runner_sha256": digest(Path(__file__)),
        "reviewed_moving_stone_pixel_path_count": len(rows),
        "next_second_unique_colour_component_count": sum(
            row["next_second_colour_screen"]["status"] == "unique_colour_component_provisional"
            for row in rows
        ),
        "highres_body_search_bottom_y_exclusive": SEARCH_BOTTOM_Y,
        "source_frame_bottom_y_exclusive": FRAME_BOTTOM_Y,
        "paths": rows,
        "selected_A401_source_frame_witness": {
            "right_proposal_id": "R01:A401",
            "selection_status": "selected_after_source_review_not_blind_validation",
            "roi_1080p_xyxy": WITNESS_BOX_XYXY,
            "yellow_hsv_range": {"lower": [17, 71, 66], "upper": [42, 255, 255]},
            "source_frames": exemplar,
        },
        "limitations": [
            "Linear image-speed extrapolation is a field-of-view diagnostic, not a physical path or settle estimate.",
            "The A401 yellow pixels were selected after inspecting source frames; continuity is visual evidence, not verified physical identity.",
            "Other path endings can also be caused by occlusion, template failure, or identity changes.",
            "The one-second colour screen was designed on this reviewed source and is not an event detector or verified same-stone trajectory.",
            "The stone leaving this camera does not establish that the other camera observes its destination.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "paths": len(rows),
                "next_second_unique_colour_components": output[
                    "next_second_unique_colour_component_count"
                ],
                "A401_yellow_pixels_by_time": areas,
            }
        )
    )


if __name__ == "__main__":
    main()
