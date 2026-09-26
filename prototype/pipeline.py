"""Coarse full-video observation index. No stone positions or calibrated states are inferred."""

from __future__ import annotations
import argparse, json, math, os, time
from pathlib import Path
import cv2
import numpy as np

PROFILES = {"dual_end": "Two side-by-side end views", "single": "Single view"}


def panel_regions(width, height, profile):
    if width < 2 or height < 2:
        raise ValueError("Video dimensions are too small")
    if profile == "single":
        return [("view", 0, 0, width, height)]
    if profile == "dual_end":
        return [("left", 0, 0, width // 2, height), ("right", width // 2, 0, width, height)]
    raise ValueError("Unsupported layout profile")


def sample_times(duration, interval):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Duration must be positive and finite")
    if not math.isfinite(interval) or interval < 1:
        raise ValueError("Sampling interval must be at least one second")
    return np.arange(0, duration, interval).tolist()


def proxy(frame, before, after):
    """Exploration scores only: coloured marking pixels and change inside a fixed board region."""
    height, width = frame.shape[:2]
    roi = frame[int(height * 0.32) : int(height * 0.86), int(width * 0.07) : int(width * 0.93)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Broad blue/green paint cue for the selected 2024 source. Clothing/logos also trigger it.
    mask = cv2.inRange(hsv, np.array([35, 45, 45]), np.array([135, 255, 255]))
    paint_fraction = float(np.mean(mask > 0))
    change = []
    for other in [before, after]:
        if other is None:
            continue
        r = other[int(height * 0.32) : int(height * 0.86), int(width * 0.07) : int(width * 0.93)]
        a = cv2.resize(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (96, 96))
        b = cv2.resize(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), (96, 96))
        change.append(float(np.mean(cv2.absdiff(a, b) > 18)))
    motion = max(change) if change else None
    score = round(
        min(paint_fraction / 0.13, 1) * (1 - min((motion if motion is not None else 1) * 3, 1)), 4
    )
    return {
        "paint_fraction": round(paint_fraction, 5),
        "changed_pixel_fraction": round(motion, 5) if motion is not None else None,
        "review_priority": score,
        "score_meaning": "Heuristic review ordering; not probability, calibration quality, stone stationarity or board completeness.",
    }


def make_observation(panel, t, image, region, metrics):
    return {
        "id": f"{panel}-{round(t * 1000)}",
        "timestamp_s": t,
        "panel": panel,
        "image": image,
        "pixel_region": list(region),
        "coordinate_space": "source_pixels",
        "calibration_status": "unavailable",
        "completeness": "unknown",
        "review_status": "unreviewed",
        "metrics": metrics,
    }


def require_simulation_ready(observation):
    if (
        observation.get("calibration_status") != "validated"
        or observation.get("completeness") != "complete"
        or observation.get("review_status") != "validated"
    ):
        raise ValueError("Observation is not a validated complete game state")
    if not observation.get("game_context") or "stones_m" not in observation:
        raise ValueError("Validated game context and metric stone positions are required")
    return observation


def analyse(video, out, profile="dual_end", interval=10.0, source_url=None):
    video = Path(video).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "thumbs").mkdir(exist_ok=True)
    status = out / "status.json"
    started = time.time()

    def progress(**kw):
        p = out / "status.tmp"
        p.write_text(json.dumps(kw))
        p.replace(status)

    progress(state="running", progress=0, message="Opening video")
    cap = cv2.VideoCapture(str(video))
    try:
        if not cap.isOpened():
            raise ValueError("Cannot open this video")
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps <= 0 or count <= 0:
            raise ValueError("Video duration could not be read")
        duration = count / fps
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        regions = panel_regions(width, height, profile)
        times = sample_times(duration, interval)
        observations = []
        failures = []
        samples = []

        def read(t):
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0, t) * 1000)
            ok, frame = cap.read()
            return frame if ok else None

        for i, t in enumerate(times):
            current = read(t)
            if current is None:
                failures.append({"timestamp_s": t, "reason": "decode_failed"})
                continue
            decoded = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            before = read(t - 1) if t >= 1 else None
            after = read(t + 1) if t + 1 < duration else None
            full = f"thumbs/frame-{i:05d}.jpg"
            preview = current
            if width > 960:
                preview = cv2.resize(current, (960, round(height * 960 / width)))
            if not cv2.imwrite(str(out / full), preview, [cv2.IMWRITE_JPEG_QUALITY, 83]):
                raise RuntimeError("Could not write thumbnail")
            samples.append({"timestamp_s": t, "decoded_timestamp_s": decoded, "image": full})
            for name, x0, y0, x1, y1 in regions:
                crop = current[y0:y1, x0:x1]
                b = before[y0:y1, x0:x1] if before is not None else None
                a = after[y0:y1, x0:x1] if after is not None else None
                observations.append(
                    make_observation(name, t, full, (x0, y0, x1, y1), proxy(crop, b, a))
                )
            if i % 10 == 0 or i == len(times) - 1:
                progress(
                    state="running",
                    progress=round((i + 1) / len(times), 3),
                    message=f"Indexed {i + 1} / {len(times)} times",
                    observations=len(observations),
                )
        if not samples:
            raise ValueError("No sampled frame could be decoded")
        data = {
            "schema_version": "0.1",
            "title": video.stem,
            "source": {
                "file_name": video.name,
                "video_relative_url": os.path.relpath(video, out),
                "original_url": source_url,
                "width": width,
                "height": height,
                "fps": fps,
                "duration_s": duration,
            },
            "profile": profile,
            "profile_note": "User-selected fixed layout; camera/sheet identity is not automatically verified. Left and right name screen regions, not teams.",
            "sampling": {
                "interval_s": interval,
                "motion_offsets_s": [-1, 1],
                "expected_samples": len(times),
                "decoded_samples": len(samples),
                "failures": failures,
            },
            "observations": observations,
            "samples": samples,
            "limitations": [
                "No stone detection, metric calibration, shot boundaries or game reconstruction yet.",
                "Paint and motion proxies can be confused by people, logos, lighting and camera movement.",
                "Low-resolution proxy is for indexing; use original-resolution frames for later calibration.",
                "Evenly spaced sampling can miss short board views.",
                "No reviewed or simulation-ready states are automatically created.",
            ],
            "runtime_s": round(time.time() - started, 2),
        }
        (out / "observations.json").write_text(json.dumps(data, indent=2) + "\n")
        from render import render

        render(data, out / "index.html")
        progress(
            state="complete",
            progress=1,
            message="Timeline ready",
            observations=len(observations),
            runtime_s=data["runtime_s"],
        )
        return data
    except Exception as e:
        progress(state="failed", progress=0, message=str(e))
        raise
    finally:
        cap.release()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--output", required=True)
    p.add_argument("--profile", choices=PROFILES, default="dual_end")
    p.add_argument("--interval", type=float, default=10)
    p.add_argument("--source-url")
    a = p.parse_args()
    r = analyse(a.video, a.output, a.profile, a.interval, a.source_url)
    print(json.dumps({"samples": r["sampling"], "runtime_s": r["runtime_s"]}))
