import json
from pathlib import Path

from prototype.scripts.scan_norway_end1_sequence_video_boards import sample_plan


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
SOURCE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"


def test_final_counter_gate_stops_before_counterless_yellow_origin():
    sequence = json.loads((BASE / "norway-end1-16-shot-sequence-hypothesis-first.json").read_text())
    counters = json.loads((SOURCE / "counter-replay.json").read_text())
    manifest = json.loads((SOURCE / "shot-review/manifest.json").read_text())
    plans = sample_plan(sequence, counters["counter_events"], manifest["shots"])
    assert len(plans) == 16
    assert max(plans[14]["sampled_times_s"]) <= 1195.4 - 12
    assert plans[15]["anchor_kind"] == "source_receiving_motion_end_not_counter"
    assert plans[15]["sampled_times_s"] == [1217.0, 1219.0, 1221.0, 1223.0, 1225.0]
