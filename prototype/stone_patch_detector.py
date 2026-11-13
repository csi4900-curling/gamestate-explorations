"""Research-only coloured-stone proposals and compact patch descriptors.

This component detects image boxes, not throw events or ground positions.
"""

import cv2
import numpy as np

SMALL_SIZES = (14, 18, 24, 30, 38, 48)
CELL_IDS = (np.arange(32)[:, None] // 8) * 4 + (np.arange(32)[None, :] // 8)


def colour_proposals(frame):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    masks = (
        ("red", ((hue < 12) | (hue > 170)) & (saturation > 60) & (value > 40)),
        ("yellow", (hue > 16) & (hue < 43) & (saturation > 60) & (value > 65)),
    )
    proposals = []
    for colour, mask in masks:
        contours, _ = cv2.findContours(
            mask.astype("uint8") * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if cv2.contourArea(contour) < 15 or width > 160 or height > 100:
                continue
            center_x, center_y = x + width / 2, y + height / 2
            if width > 35:
                sizes = sorted({min(160, round(width * scale)) for scale in (1.2, 1.6)})
                offsets = (0.22, 0.38)
            else:
                sizes = SMALL_SIZES
                offsets = (0.0, 0.2)
            for side in sizes:
                for offset in offsets:
                    body_y = center_y + side * offset
                    proposals.append(
                        {
                            "colour": colour,
                            "bbox": [center_x - side / 2, body_y - side / 2, side, side],
                        }
                    )
    return image, proposals


def patch_features(image, bbox):
    x, y, width, height = bbox
    if min(width, height) <= 0:
        raise ValueError("Invalid patch box")
    if x >= 0 and y >= 0 and x + width <= image.shape[1] and y + height <= image.shape[0]:
        padded = image
        center = (float(x + width / 2), float(y + height / 2))
    else:
        # Replicated padding keeps partially visible edge stones in the candidate set.
        pad = int(max(width, height)) + 2
        padded = cv2.copyMakeBorder(image, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        center = (float(x + width / 2 + pad), float(y + height / 2 + pad))
    crop = cv2.getRectSubPix(padded, (max(1, round(width)), max(1, round(height))), center)
    crop = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude, angle = cv2.cartToPolar(gradient_x, gradient_y, angleInDegrees=True)
    orientation = np.floor((angle % 180) / 20).astype(np.int32)
    hog = np.bincount(
        (CELL_IDS * 9 + orientation).ravel(), weights=magnitude.ravel(), minlength=144
    ).reshape(16, 9)
    hog /= np.linalg.norm(hog, axis=1, keepdims=True) + 1e-6
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    histograms = []
    for channel, bins, maximum in ((0, 16, 180), (1, 8, 256), (2, 8, 256)):
        counts = cv2.calcHist([hsv], [channel], None, [bins], [0, maximum]).ravel()
        histograms.append(counts / crop.shape[0] / crop.shape[1])
    return np.concatenate((hog.ravel(), *histograms)).astype(np.float32)


def select_boxes(proposals, scores, threshold, *, nms_iou=0.4):
    """Class-specific greedy NMS after a fixed patch score threshold."""
    if len(proposals) != len(scores):
        raise ValueError("Proposal/score length mismatch")
    ranked = sorted(
        (
            dict(proposal, confidence=float(score))
            for proposal, score in zip(proposals, scores)
            if score >= threshold
        ),
        key=lambda item: -item["confidence"],
    )
    chosen = []
    for item in ranked:
        x, y, w, h = item["bbox"]
        overlap = False
        for kept in chosen:
            if kept["colour"] != item["colour"]:
                continue
            xx, yy, ww, hh = kept["bbox"]
            area = max(0, min(x + w, xx + ww) - max(x, xx)) * max(
                0, min(y + h, yy + hh) - max(y, yy)
            )
            if area / (w * h + ww * hh - area) >= nms_iou:
                overlap = True
                break
        if not overlap:
            chosen.append(item)
    return chosen


def load_model(path):
    with np.load(path, allow_pickle=False) as data:
        return {
            name: data[name].copy()
            for name in ("mean", "scale", "weights", "intercept", "threshold")
        }


def detect_stones(frame, model):
    """Return provisional image boxes; no temporal or delivery confirmation."""
    image, proposals = colour_proposals(frame)
    if not proposals:
        return []
    features = np.stack([patch_features(image, row["bbox"]) for row in proposals])
    scores = ((features - model["mean"]) / model["scale"]) @ model["weights"].ravel()
    scores += model["intercept"].item()
    return select_boxes(proposals, scores, float(model["threshold"]))
