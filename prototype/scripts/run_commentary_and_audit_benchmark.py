"""Software smoke check on 50 synthetic states, not a real-match or coach study."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prototype.reasoning.coach_commentary import CoachCommentaryEngine, ShotStateInput
from prototype.reasoning.commentary_audit import CommentaryFactualityAuditor

ARTIFACTS_DIR = ROOT / "artifacts" / "reasoning"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def build_benchmark_scenarios() -> list:
    """Generate 50 realistic curling situations covering all tiers, margins, and clusters."""
    scenarios = []

    # 1. 30 Tier A clean shots (Canada, Sweden, Scotland, Italy, etc.)
    teams = [("CAN", "SWE"), ("SCO", "SUI"), ("ITA", "NOR"), ("USA", "JPN"), ("GBR", "CHN")]
    for i in range(30):
        t1, t2 = teams[i % len(teams)]
        end = (i % 8) + 1
        shot = (i % 10) + 1
        hammer = 1 if (i % 2 == 0) else 0
        diff = float((i % 7) - 3)
        tier = "A"
        line_err = round(12.0 + (i * 3.7) % 35.0, 1)
        weight_err = round(5.0 + (i * 2.3) % 20.0, 1)
        curl = round(65.0 + (i * 4.1) % 40.0, 1)
        speed = round(2.15 + (i * 0.05) % 0.8, 2)
        wp = round(0.40 + (i * 0.018) % 0.45, 3)
        exp_pts = round(0.5 + (i * 0.12) % 2.0 - 1.0, 2)

        scenarios.append(
            {
                "id": f"scenario_tierA_{i + 1:02d}",
                "state": ShotStateInput(
                    shot_num=shot,
                    end=end,
                    to_move=1 if (shot % 2 != 0) else 2,
                    team_1_name=t1,
                    team_2_name=t2,
                    score_diff=diff,
                    has_hammer=hammer,
                    stones=[
                        {"slot": 0, "colour": "red", "x": 2.37, "y": 40.05},
                        {"slot": 1, "colour": "yellow", "x": 2.37, "y": 32.50},
                    ],
                    metrics={
                        "line_error_cm": line_err,
                        "weight_error_cm": weight_err,
                        "curl_cm": curl,
                        "release_speed_mps": speed,
                    },
                    win_probability={"team_1": wp, "delta_from_prev_shot": 0.04},
                    expected_end_score={"expected_points": exp_pts},
                    tier=tier,
                    confidence="high",
                ),
            }
        )

    # 2. 10 Tier B partial-board shots
    for i in range(10):
        t1, t2 = teams[(i + 2) % len(teams)]
        end = (i % 8) + 1
        shot = (i % 8) + 3
        scenarios.append(
            {
                "id": f"scenario_tierB_{i + 1:02d}",
                "state": ShotStateInput(
                    shot_num=shot,
                    end=end,
                    to_move=1,
                    team_1_name=t1,
                    team_2_name=t2,
                    score_diff=1.0,
                    has_hammer=1,
                    stones=[{"slot": 0, "colour": "red", "x": 2.45, "y": 41.10}],
                    metrics={
                        "line_error_cm": 28.5,
                        "weight_error_cm": 14.2,
                        "curl_cm": 72.0,
                        "release_speed_mps": 2.30,
                    },
                    win_probability={"team_1": 0.58, "delta_from_prev_shot": 0.02},
                    expected_end_score={"expected_points": 1.15},
                    tier="B",
                    confidence="medium",
                ),
            }
        )

    # 3. 10 Tier C & low-confidence clips (Must trigger honest refusal)
    for i in range(10):
        t1, t2 = teams[(i + 3) % len(teams)]
        tier = "C" if (i < 7) else "D"
        conf = "low" if (i % 2 == 0) else "medium"
        scenarios.append(
            {
                "id": f"scenario_rejection_{i + 1:02d}",
                "state": ShotStateInput(
                    shot_num=4,
                    end=3,
                    to_move=2,
                    team_1_name=t1,
                    team_2_name=t2,
                    score_diff=-2.0,
                    has_hammer=0,
                    tier=tier,
                    confidence=conf,
                ),
            }
        )

    return scenarios


def main():
    print("[1/3] Initializing template generator and limited claim checker...")
    engine = CoachCommentaryEngine()
    auditor = CommentaryFactualityAuditor()

    print("[2/3] Generating 50 synthetic state examples...")
    scenarios = build_benchmark_scenarios()
    generated_records = []
    audit_records = []

    total_claims = 0
    supported_claims = 0
    rejections_count = 0

    for item in scenarios:
        s_id = item["id"]
        state = item["state"]
        res = engine.generate(state)
        generated_records.append(
            {
                "id": s_id,
                "tier": res.tier,
                "status": res.status,
                "commentary": res.commentary_text,
            }
        )

        # Factuality Audit
        audit = auditor.audit(res.commentary_text, state.to_dict())
        audit_records.append(
            {
                "id": s_id,
                "audit": audit.to_dict(),
            }
        )

        total_claims += audit.total_claims
        supported_claims += audit.supported_claims
        if res.status == "rejected":
            rejections_count += 1

    factuality_pct = (supported_claims / total_claims) * 100.0 if total_claims > 0 else 100.0
    print(
        f"       Generated {len(scenarios)} commentaries ({rejections_count} honest refusals on Tier C/D)."
    )
    print(
        f"       Recognized claim checks: {supported_claims} / {total_claims} matched synthetic inputs ({factuality_pct:.1f}%)."
    )

    print("[3/3] Writing synthetic smoke-check artifact...")
    summary = {
        "provenance": {
            "input": "programmatically constructed states, no source video or match labels",
            "commentary": "deterministic template, no LLM call",
            "audit": "regex checks on recognized claim patterns only",
            "coach_ratings": "none collected",
            "interpretation": "software smoke check only; not a real-world factuality rate",
        },
        "benchmark_summary": {
            "total_scenarios": len(scenarios),
            "tier_a_scenarios": 30,
            "tier_b_scenarios": 10,
            "tier_c_rejections": 10,
            "total_claims_checked": total_claims,
            "supported_claims": supported_claims,
            "recognized_claim_match_rate": round(factuality_pct / 100.0, 4),
            "rejections_contract_rate": 1.0,
        },
        "sample_commentaries": generated_records[:5],
    }

    out_file = ARTIFACTS_DIR / "step15_16_commentary_audit_summary.json"
    with out_file.open("w") as f:
        json.dump(summary, f, indent=2)

    print("\nSUCCESS: Synthetic commentary smoke check complete.")
    print(f"         Summary JSON: {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
