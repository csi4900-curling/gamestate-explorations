"""Unit tests for factuality audit and multi-coach rating evaluation suite."""

import unittest
from prototype.reasoning.coach_commentary import CoachCommentaryEngine, ShotStateInput
from prototype.reasoning.commentary_audit import (
    CommentaryFactualityAuditor,
    CoachEvaluationSuite,
    compute_cohen_weighted_kappa,
)


class TestCommentaryAudit(unittest.TestCase):
    def setUp(self):
        self.engine = CoachCommentaryEngine()
        self.auditor = CommentaryFactualityAuditor()

    def test_audit_passes_on_grounded_commentary(self):
        inp = ShotStateInput(
            shot_num=4,
            end=2,
            to_move=1,
            team_1_name="SCO",
            team_2_name="SUI",
            score_diff=1.0,
            has_hammer=1,
            metrics={"line_error_cm": 15.0, "weight_error_cm": 6.5, "curl_cm": 70.0},
            win_probability={"team_1": 0.55},
            tier="A",
            confidence="high",
        )
        res = self.engine.generate(inp)
        report = self.auditor.audit(res.commentary_text, inp.to_dict())

        self.assertEqual(report.status, "pass")
        self.assertEqual(report.unsupported_claims, 0)
        self.assertEqual(report.factuality_rate, 1.0)

    def test_audit_flags_hallucinated_metric(self):
        inp = ShotStateInput(
            shot_num=4,
            end=2,
            metrics={"line_error_cm": 15.0},
            tier="A",
            confidence="high",
        )
        hallucinated_text = "In End 2, Shot 4, delivery had a line error of 99.9 cm."
        report = self.auditor.audit(hallucinated_text, inp.to_dict())

        self.assertEqual(report.status, "flagged")
        self.assertGreater(report.error_breakdown["hallucinated_metric"], 0)

    def test_audit_flags_speculation(self):
        inp = ShotStateInput(
            shot_num=4,
            end=2,
            tier="A",
            confidence="high",
        )
        speculative_text = "In End 2, Shot 4, the thrower looked nervous and slipped on the ice."
        report = self.auditor.audit(speculative_text, inp.to_dict())

        self.assertEqual(report.status, "flagged")
        self.assertGreater(report.error_breakdown["unsupported_speculation"], 0)

    def test_weighted_cohen_kappa(self):
        # Perfect agreement
        r1 = [5, 4, 3, 2, 1]
        r2 = [5, 4, 3, 2, 1]
        self.assertAlmostEqual(compute_cohen_weighted_kappa(r1, r2), 1.0)

        # High agreement
        r3 = [5, 4, 3, 2, 2]
        kappa = compute_cohen_weighted_kappa(r1, r3)
        self.assertGreater(kappa, 0.7)

    def test_coach_evaluation_suite(self):
        evals = [
            {
                "clip_id": "c1",
                "coach_1": {"correctness": 5, "usefulness": 4},
                "coach_2": {"correctness": 5, "usefulness": 5},
                "coach_3": {"correctness": 4, "usefulness": 4},
            },
            {
                "clip_id": "c2",
                "coach_1": {"correctness": 4, "usefulness": 5},
                "coach_2": {"correctness": 4, "usefulness": 4},
                "coach_3": {"correctness": 5, "usefulness": 5},
            },
        ]
        res = CoachEvaluationSuite.evaluate_coach_ratings(evals)
        self.assertEqual(res["num_clips_evaluated"], 2)
        self.assertEqual(res["num_coaches"], 3)
        self.assertGreaterEqual(res["correctness"]["mean"], 4.0)
        self.assertGreaterEqual(res["usefulness"]["mean"], 4.0)


if __name__ == "__main__":
    unittest.main()
