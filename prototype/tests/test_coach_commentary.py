"""Unit tests for grounded coach commentary engine."""

import unittest
from prototype.reasoning.coach_commentary import CoachCommentaryEngine, ShotStateInput


class TestCoachCommentary(unittest.TestCase):
    def setUp(self):
        self.engine = CoachCommentaryEngine()

    def test_honest_refusal_on_tier_c(self):
        inp = ShotStateInput(
            shot_num=3,
            end=2,
            tier="C",
            confidence="high",
        )
        res = self.engine.generate(inp)
        self.assertEqual(res.status, "rejected")
        self.assertIn("OUTSIDE CONTRACT", res.commentary_text)
        self.assertIn("tier c", res.rejection_reason.lower())

    def test_honest_refusal_on_low_confidence(self):
        inp = ShotStateInput(
            shot_num=3,
            end=2,
            tier="A",
            confidence="low",
        )
        res = self.engine.generate(inp)
        self.assertEqual(res.status, "rejected")
        self.assertIn("OUTSIDE CONTRACT", res.commentary_text)

    def test_accepted_commentary_narrates_metrics(self):
        inp = ShotStateInput(
            shot_num=5,
            end=3,
            to_move=1,
            team_1_name="CAN",
            team_2_name="SWE",
            score_diff=2.0,
            has_hammer=1,
            metrics={
                "line_error_cm": 14.5,
                "weight_error_cm": 8.0,
                "curl_cm": 68.2,
                "release_speed_mps": 2.45,
            },
            win_probability={"team_1": 0.65, "delta_from_prev_shot": 0.05},
            expected_end_score={"expected_points": 1.25},
            tier="A",
            confidence="high",
        )
        res = self.engine.generate(inp)
        self.assertEqual(res.status, "accepted")
        text = res.commentary_text

        # Verify factual narration
        self.assertIn("End 3", text)
        self.assertIn("Shot 5", text)
        self.assertIn("CAN", text)
        self.assertIn("14.5 cm", text)
        self.assertIn("8.0 cm", text)
        self.assertIn("68.2 cm", text)
        self.assertIn("2.45 m/s", text)
        self.assertIn("65.0%", text)
        self.assertIn("+1.25 expected points", text)
        self.assertNotIn("revolutions", text)

    def test_llm_prompt_structure(self):
        inp = ShotStateInput(shot_num=1, end=1, tier="A")
        prompt = self.engine.build_llm_prompt(inp)
        self.assertIn("system_prompt", prompt)
        self.assertIn("user_message", prompt)
        self.assertIn("STRICT GROUNDING RULES", prompt["system_prompt"])


if __name__ == "__main__":
    unittest.main()
