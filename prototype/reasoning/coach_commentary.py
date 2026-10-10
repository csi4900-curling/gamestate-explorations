"""Step 15: Grounded Coach Commentary Engine adhering to INLG 2025 hard boundaries.

Enforces:
1. Strict JSON state input contract.
2. Honest rejection state: Refuses Tier C/D or low-confidence clips ('Outside contract, no measurement produced').
3. 'Narrate, never infer': Every statement is mathematically grounded in input JSON fields.
4. Structured prompt builder for LLMs with verification safeguards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import json


@dataclass
class ShotStateInput:
    """Canonical structured input schema matching Playbook Step 15."""

    shot_num: int
    end: int
    last_end: int = 8
    to_move: int = 1  # 1 for Red / Team 1, 2 for Yellow / Team 2
    team_1_name: str = "Team 1"
    team_2_name: str = "Team 2"
    score: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    score_diff: Optional[float] = None
    has_hammer: Optional[int] = None
    stones: List[Dict[str, Any]] = field(default_factory=list)
    shot_vector: Optional[Dict[str, Any]] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    win_probability: Optional[Dict[str, float]] = None
    expected_end_score: Optional[Dict[str, float]] = None
    tier: str = "A"  # "A", "B", "C", "D"
    confidence: str = "high"  # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ShotStateInput:
        return cls(
            shot_num=int(data["shot_num"]),
            end=int(data["end"]),
            last_end=int(data.get("last_end", 8)),
            to_move=int(data.get("to_move", 1)),
            team_1_name=str(data.get("team_1_name", "Team 1")),
            team_2_name=str(data.get("team_2_name", "Team 2")),
            score=list(data.get("score", [0] * 10)),
            score_diff=float(data["score_diff"])
            if "score_diff" in data and data["score_diff"] is not None
            else None,
            has_hammer=int(data["has_hammer"])
            if "has_hammer" in data and data["has_hammer"] is not None
            else None,
            stones=list(data.get("stones", [])),
            shot_vector=data.get("shot_vector"),
            metrics=dict(data.get("metrics", {})),
            win_probability=dict(data["win_probability"]) if data.get("win_probability") else None,
            expected_end_score=dict(data["expected_end_score"])
            if data.get("expected_end_score")
            else None,
            tier=str(data.get("tier", "A")).upper(),
            confidence=str(data.get("confidence", "high")).lower(),
        )


@dataclass
class CommentaryResult:
    """Result of commentary generation with provenance and gating status."""

    status: str  # "accepted" | "rejected"
    tier: str
    confidence: str
    rejection_reason: Optional[str]
    commentary_text: str
    structured_claims: List[Dict[str, Any]]
    input_state: Dict[str, Any]


class CoachCommentaryEngine:
    """Generates verified coaching commentary strictly grounded in structured JSON."""

    def __init__(self, rejection_tiers: Optional[List[str]] = None):
        self.rejection_tiers = [t.upper() for t in (rejection_tiers or ["C", "D"])]

    def generate(self, state: ShotStateInput | Dict[str, Any]) -> CommentaryResult:
        """Generate verified coaching commentary or return explicit rejection state."""
        if isinstance(state, dict):
            inp = ShotStateInput.from_dict(state)
        else:
            inp = state

        # Step 18 Killer Feature: Honest refusal on Tier C/D or low confidence
        if inp.tier in self.rejection_tiers or inp.confidence == "low":
            reason = f"Camera tier {inp.tier} and confidence '{inp.confidence}' are outside validated contract (Tier A/B required)."
            commentary = (
                f"OUTSIDE CONTRACT: Camera tier {inp.tier} with {inp.confidence} tracking confidence. "
                f"Measurement refused to prevent uncalibrated inference. No coach commentary produced."
            )
            return CommentaryResult(
                status="rejected",
                tier=inp.tier,
                confidence=inp.confidence,
                rejection_reason=reason,
                commentary_text=commentary,
                structured_claims=[
                    {
                        "type": "rejection",
                        "tier": inp.tier,
                        "confidence": inp.confidence,
                        "reason": reason,
                    }
                ],
                input_state=inp.to_dict(),
            )

        # Build grounded claims
        claims: List[Dict[str, Any]] = []
        sentences: List[str] = []

        # Claim 1: Game & End Context
        shooting_team = inp.team_1_name if inp.to_move == 1 else inp.team_2_name
        shooting_col = "Red" if inp.to_move == 1 else "Yellow"
        hammer_str = "with hammer advantage" if inp.has_hammer == 1 else "without hammer"

        s1 = f"In End {inp.end}, Shot {inp.shot_num}, {shooting_team} ({shooting_col}) delivered {hammer_str}."
        claims.append(
            {
                "type": "context",
                "end": inp.end,
                "shot_num": inp.shot_num,
                "to_move": inp.to_move,
                "shooting_team": shooting_team,
                "has_hammer": inp.has_hammer,
            }
        )
        sentences.append(s1)

        # Claim 2: Score context if available
        if inp.score_diff is not None:
            lead_str = (
                f"holds a {abs(inp.score_diff):.0f}-point lead"
                if inp.score_diff > 0
                else (
                    f"trails by {abs(inp.score_diff):.0f} points"
                    if inp.score_diff < 0
                    else "is tied"
                )
            )
            s_score = f"{inp.team_1_name} currently {lead_str} over {inp.team_2_name}."
            claims.append(
                {
                    "type": "score",
                    "score_diff": inp.score_diff,
                }
            )
            sentences.append(s_score)

        # Claim 3: Stone placement context
        if inp.stones:
            red_count = sum(1 for s in inp.stones if s.get("colour", "").lower() == "red")
            yellow_count = sum(1 for s in inp.stones if s.get("colour", "").lower() == "yellow")
            s_stones = f"The sheet shows {red_count} Red and {yellow_count} Yellow stones in play."
            claims.append(
                {
                    "type": "stones",
                    "red_count": red_count,
                    "yellow_count": yellow_count,
                    "total_stones": len(inp.stones),
                }
            )
            sentences.append(s_stones)

        # Claim 4: Measured delivery metrics (line error, weight error, curl, speed)
        metrics = inp.metrics
        metric_parts = []
        if "line_error_cm" in metrics:
            metric_parts.append(f"line error of {metrics['line_error_cm']:.1f} cm")
            claims.append({"type": "line_error", "value_cm": metrics["line_error_cm"]})
        if "weight_error_cm" in metrics:
            metric_parts.append(f"weight error of {metrics['weight_error_cm']:.1f} cm")
            claims.append({"type": "weight_error", "value_cm": metrics["weight_error_cm"]})
        if "curl_cm" in metrics:
            metric_parts.append(f"lateral curl of {metrics['curl_cm']:.1f} cm")
            claims.append({"type": "curl", "value_cm": metrics["curl_cm"]})
        if "release_speed_mps" in metrics:
            metric_parts.append(f"release speed of {metrics['release_speed_mps']:.2f} m/s")
            claims.append({"type": "release_speed", "value_mps": metrics["release_speed_mps"]})

        if metric_parts:
            s_metrics = f"Delivery telemetry registered a {', '.join(metric_parts)}."
            sentences.append(s_metrics)

        # Claim 5: Reasoning probabilities (Win probability & Expected end score)
        if inp.win_probability:
            wp = inp.win_probability
            t1_p = wp.get("team_1", 0.5) * 100.0
            delta_str = ""
            if "delta_from_prev_shot" in wp:
                d = wp["delta_from_prev_shot"] * 100.0
                delta_str = f" ({d:+.1f}% shift)"
            s_wp = f"The reasoning model estimates {inp.team_1_name} win probability at {t1_p:.1f}%{delta_str}."
            claims.append(
                {
                    "type": "win_probability",
                    "team_1_pct": t1_p,
                    "delta": wp.get("delta_from_prev_shot"),
                }
            )
            sentences.append(s_wp)

        if inp.expected_end_score and "expected_points" in inp.expected_end_score:
            ep = inp.expected_end_score["expected_points"]
            s_ep = f"Projected end outcome stands at {ep:+.2f} expected points for Team 1."
            claims.append(
                {
                    "type": "expected_points",
                    "expected_points": ep,
                }
            )
            sentences.append(s_ep)

        full_text = " ".join(sentences)
        return CommentaryResult(
            status="accepted",
            tier=inp.tier,
            confidence=inp.confidence,
            rejection_reason=None,
            commentary_text=full_text,
            structured_claims=claims,
            input_state=inp.to_dict(),
        )

    def build_llm_prompt(self, state: ShotStateInput | Dict[str, Any]) -> Dict[str, str]:
        """Build a strict system prompt and user JSON payload for LLM narration."""
        if isinstance(state, ShotStateInput):
            payload = state.to_dict()
        else:
            payload = state

        system_prompt = (
            "You are a professional Olympic curling performance analyst. "
            "You will be given a JSON object containing verified game state, tracking telemetry, and model probabilities. "
            "STRICT GROUNDING RULES:\n"
            "1. Narrate ONLY the facts and numbers present in the JSON. Never guess, infer, or estimate unstated values.\n"
            "2. If tier is 'C' or 'D', or confidence is 'low', output EXACTLY: 'OUTSIDE CONTRACT: Camera tier outside validated bounds. Measurement refused.'\n"
            "3. Do not invent player emotions, psychological states, or tactical motives not supported by metrics.\n"
            "4. Keep commentary concise, professional, and coach-facing (3-4 sentences max)."
        )
        user_message = f"Here is the verified shot telemetry:\n```json\n{json.dumps(payload, indent=2)}\n```\nProvide coach-facing commentary."

        return {
            "system_prompt": system_prompt,
            "user_message": user_message,
        }
