import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_2022_ambiguous_counter_ice_tiebreak import (
    select_unique_ice_supported,
)


def options():
    return [
        {"shot_id": "closeup", "origin_probability": 0.98, "max_center_lower_ice_fraction": 0.06},
        {"shot_id": "delivery", "origin_probability": 0.94, "max_center_lower_ice_fraction": 0.48},
        {"shot_id": "low_origin", "origin_probability": 0.04, "max_center_lower_ice_fraction": 0.8},
    ]


class TestAmbiguousCounterIceTiebreak(unittest.TestCase):
    def test_unique_ice_supported_choice_and_ambiguity_abstention(self):
        rows = options()
        self.assertEqual(select_unique_ice_supported(rows), "delivery")
        rows[0]["max_center_lower_ice_fraction"] = 0.4
        self.assertIsNone(select_unique_ice_supported(rows))
        rows[1]["max_center_lower_ice_fraction"] = 0.1
        self.assertEqual(select_unique_ice_supported(rows), "closeup")
        rows[0]["max_center_lower_ice_fraction"] = 0.1
        self.assertIsNone(select_unique_ice_supported(rows))
