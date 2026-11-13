"""The verifier must use the exact broadcast-review feature geometry."""

import json
from pathlib import Path

from cap_patch_verifier import context_bbox

ROOT = Path(__file__).resolve().parents[2]


def test_context_bbox_matches_existing_review_samples():
    for name in ("sideview-patch-review-v1", "swiss-patch-review-v1"):
        path = ROOT / "validation/curlobserver-learned-probe" / name / "manifest.json"
        manifest = json.loads(path.read_text())
        for sample in manifest["samples"]:
            assert context_bbox(sample["cap_bbox"]) == sample["crop_bbox"]
