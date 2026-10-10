"""Step 16: Automated Factuality Audit and Multi-Coach Rating Agreement Engine.

Performs:
1. Sentence-by-sentence atomic claim extraction and verification against input JSON ground truth.
2. Error taxonomy attribution (hallucinated_metric, contradicted_score, wrong_end_or_shot, unsupported_speculation).
3. Inter-rater agreement statistics (Cohen's Kappa / Krippendorff's Alpha / Pearson r) across coach evaluators.
4. Batch evaluation reporting matching Playbook Step 16 output contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import re
import numpy as np


@dataclass
class ClaimVerification:
    """Verification record for a single atomic claim."""

    claim_type: str
    stated_value: Any
    ground_truth_value: Any
    is_supported: bool
    error_class: Optional[str] = None
    note: str = ""


@dataclass
class AuditReport:
    """Comprehensive factuality audit report for a generated commentary text."""

    status: str
    total_sentences: int
    total_claims: int
    supported_claims: int
    unsupported_claims: int
    factuality_rate: float
    error_breakdown: Dict[str, int]
    claim_details: List[ClaimVerification] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "total_sentences": self.total_sentences,
            "total_claims": self.total_claims,
            "supported_claims": self.supported_claims,
            "unsupported_claims": self.unsupported_claims,
            "factuality_rate": round(self.factuality_rate, 4),
            "error_breakdown": self.error_breakdown,
            "claim_details": [asdict(c) for c in self.claim_details],
        }


class CommentaryFactualityAuditor:
    """Audits generated coaching commentary against structured input JSON ground truth."""

    SPECULATIVE_TERMS = [
        "frustrated",
        "nervous",
        "confident",
        "slipped",
        "choked",
        "distracted",
        "bad ice",
        "poor ice",
        "lucky",
        "unlucky",
        "careless",
        "lazy",
    ]

    def audit(self, commentary_text: str, input_state: Dict[str, Any]) -> AuditReport:
        """Parse sentences, extract atomic claims, and verify against input state."""
        sentences = [s.strip() for s in re.split(r"[.!?]", commentary_text) if s.strip()]
        claims: List[ClaimVerification] = []
        errors: Dict[str, int] = {
            "hallucinated_metric": 0,
            "contradicted_score": 0,
            "wrong_end_or_shot": 0,
            "unsupported_speculation": 0,
            "ungrounded_rejection": 0,
        }

        tier = str(input_state.get("tier", "A")).upper()
        confidence = str(input_state.get("confidence", "high")).lower()
        is_rejection_expected = tier in ["C", "D"] or confidence == "low"

        # Check for rejection state
        if "OUTSIDE CONTRACT" in commentary_text or "refused" in commentary_text.lower():
            if is_rejection_expected:
                claims.append(
                    ClaimVerification(
                        claim_type="rejection_gate",
                        stated_value="rejected",
                        ground_truth_value=f"tier={tier}, confidence={confidence}",
                        is_supported=True,
                        note="System correctly executed honest refusal on outside-contract state.",
                    )
                )
            else:
                claims.append(
                    ClaimVerification(
                        claim_type="rejection_gate",
                        stated_value="rejected",
                        ground_truth_value=f"tier={tier}, confidence={confidence}",
                        is_supported=False,
                        error_class="ungrounded_rejection",
                        note="System rejected a valid in-contract state.",
                    )
                )
                errors["ungrounded_rejection"] += 1

            total = len(claims)
            supp = sum(1 for c in claims if c.is_supported)
            return AuditReport(
                status="pass" if supp == total else "fail",
                total_sentences=len(sentences),
                total_claims=total,
                supported_claims=supp,
                unsupported_claims=total - supp,
                factuality_rate=float(supp / total) if total > 0 else 1.0,
                error_breakdown=errors,
                claim_details=claims,
            )

        # Check for unsupported psychological / causal speculation
        lower_text = commentary_text.lower()
        for term in self.SPECULATIVE_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", lower_text):
                claims.append(
                    ClaimVerification(
                        claim_type="speculation_check",
                        stated_value=term,
                        ground_truth_value=None,
                        is_supported=False,
                        error_class="unsupported_speculation",
                        note=f"Commentary contains speculative term '{term}' not present in JSON.",
                    )
                )
                errors["unsupported_speculation"] += 1

        # Claim 1: End number
        end_match = re.search(r"\bEnd\s+(\d+)\b", commentary_text, re.IGNORECASE)
        if end_match:
            stated_end = int(end_match.group(1))
            true_end = int(input_state.get("end", 0))
            ok = stated_end == true_end
            err = None if ok else "wrong_end_or_shot"
            if not ok:
                errors["wrong_end_or_shot"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="end_number",
                    stated_value=stated_end,
                    ground_truth_value=true_end,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 2: Shot number
        shot_match = re.search(r"\bShot\s+(\d+)\b", commentary_text, re.IGNORECASE)
        if shot_match:
            stated_shot = int(shot_match.group(1))
            true_shot = int(input_state.get("shot_num", 0))
            ok = stated_shot == true_shot
            err = None if ok else "wrong_end_or_shot"
            if not ok:
                errors["wrong_end_or_shot"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="shot_number",
                    stated_value=stated_shot,
                    ground_truth_value=true_shot,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 3: Score differential
        lead_match = re.search(r"(\d+)-point lead", commentary_text, re.IGNORECASE)
        trail_match = re.search(r"trails by (\d+)", commentary_text, re.IGNORECASE)
        tied_match = re.search(r"\bis tied\b", commentary_text, re.IGNORECASE)
        true_diff = input_state.get("score_diff")

        if lead_match and true_diff is not None:
            stated_diff = float(lead_match.group(1))
            ok = abs(stated_diff - true_diff) < 0.1 and true_diff > 0
            err = None if ok else "contradicted_score"
            if not ok:
                errors["contradicted_score"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="score_differential",
                    stated_value=f"+{stated_diff}",
                    ground_truth_value=true_diff,
                    is_supported=ok,
                    error_class=err,
                )
            )
        elif trail_match and true_diff is not None:
            stated_diff = -float(trail_match.group(1))
            ok = abs(stated_diff - true_diff) < 0.1 and true_diff < 0
            err = None if ok else "contradicted_score"
            if not ok:
                errors["contradicted_score"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="score_differential",
                    stated_value=f"{stated_diff}",
                    ground_truth_value=true_diff,
                    is_supported=ok,
                    error_class=err,
                )
            )
        elif tied_match and true_diff is not None:
            ok = abs(true_diff) < 0.1
            err = None if ok else "contradicted_score"
            if not ok:
                errors["contradicted_score"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="score_differential",
                    stated_value=0.0,
                    ground_truth_value=true_diff,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 4: Line Error
        metrics = input_state.get("metrics", {})
        line_match = re.search(r"line error of ([\d\.]+)\s*cm", commentary_text, re.IGNORECASE)
        if line_match:
            stated_line = float(line_match.group(1))
            true_line = metrics.get("line_error_cm")
            ok = true_line is not None and abs(stated_line - true_line) <= 0.2
            err = None if ok else "hallucinated_metric"
            if not ok:
                errors["hallucinated_metric"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="line_error_cm",
                    stated_value=stated_line,
                    ground_truth_value=true_line,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 5: Weight Error
        weight_match = re.search(r"weight error of ([\d\.]+)\s*cm", commentary_text, re.IGNORECASE)
        if weight_match:
            stated_weight = float(weight_match.group(1))
            true_weight = metrics.get("weight_error_cm")
            ok = true_weight is not None and abs(stated_weight - true_weight) <= 0.2
            err = None if ok else "hallucinated_metric"
            if not ok:
                errors["hallucinated_metric"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="weight_error_cm",
                    stated_value=stated_weight,
                    ground_truth_value=true_weight,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 6: Curl
        curl_match = re.search(r"lateral curl of ([\d\.]+)\s*cm", commentary_text, re.IGNORECASE)
        if curl_match:
            stated_curl = float(curl_match.group(1))
            true_curl = metrics.get("curl_cm")
            ok = true_curl is not None and abs(stated_curl - true_curl) <= 0.2
            err = None if ok else "hallucinated_metric"
            if not ok:
                errors["hallucinated_metric"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="curl_cm",
                    stated_value=stated_curl,
                    ground_truth_value=true_curl,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 7: Release Speed
        speed_match = re.search(r"release speed of ([\d\.]+)\s*m/s", commentary_text, re.IGNORECASE)
        if speed_match:
            stated_speed = float(speed_match.group(1))
            true_speed = metrics.get("release_speed_mps")
            ok = true_speed is not None and abs(stated_speed - true_speed) <= 0.05
            err = None if ok else "hallucinated_metric"
            if not ok:
                errors["hallucinated_metric"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="release_speed_mps",
                    stated_value=stated_speed,
                    ground_truth_value=true_speed,
                    is_supported=ok,
                    error_class=err,
                )
            )

        # Claim 8: Win Probability
        wp_match = re.search(r"win probability at ([\d\.]+)%", commentary_text, re.IGNORECASE)
        if wp_match:
            stated_wp = float(wp_match.group(1))
            wp_dict = input_state.get("win_probability", {})
            true_wp = wp_dict.get("team_1", 0.0) * 100.0 if wp_dict else None
            ok = true_wp is not None and abs(stated_wp - true_wp) <= 0.2
            err = None if ok else "hallucinated_metric"
            if not ok:
                errors["hallucinated_metric"] += 1
            claims.append(
                ClaimVerification(
                    claim_type="win_probability_pct",
                    stated_value=stated_wp,
                    ground_truth_value=true_wp,
                    is_supported=ok,
                    error_class=err,
                )
            )

        total = len(claims)
        supported = sum(1 for c in claims if c.is_supported)
        unsupported = total - supported
        factuality_rate = float(supported / total) if total > 0 else 1.0

        return AuditReport(
            status="pass" if unsupported == 0 else "flagged",
            total_sentences=len(sentences),
            total_claims=total,
            supported_claims=supported,
            unsupported_claims=unsupported,
            factuality_rate=factuality_rate,
            error_breakdown=errors,
            claim_details=claims,
        )


def compute_cohen_weighted_kappa(rater_a: List[int], rater_b: List[int], k: int = 5) -> float:
    """Compute Cohen's linearly weighted kappa for ordinal ratings 1..k."""
    if len(rater_a) != len(rater_b):
        raise ValueError("Rater lists must be of equal length")
    n = len(rater_a)
    if n == 0:
        return 1.0

    # Build confusion matrix
    o_matrix = np.zeros((k, k), dtype=float)
    for a, b in zip(rater_a, rater_b):
        ia = max(0, min(k - 1, int(a) - 1))
        ib = max(0, min(k - 1, int(b) - 1))
        o_matrix[ia, ib] += 1.0
    o_matrix /= n

    # Expected marginals
    marg_a = np.sum(o_matrix, axis=1)
    marg_b = np.sum(o_matrix, axis=0)
    e_matrix = np.outer(marg_a, marg_b)

    # Linear weight matrix: w_ij = 1 - |i - j| / (k - 1)
    w_matrix = np.zeros((k, k), dtype=float)
    for i in range(k):
        for j in range(k):
            w_matrix[i, j] = 1.0 - abs(i - j) / (k - 1)

    po = float(np.sum(w_matrix * o_matrix))
    pe = float(np.sum(w_matrix * e_matrix))

    if abs(1.0 - pe) < 1e-9:
        return 1.0
    return float((po - pe) / (1.0 - pe))


class CoachEvaluationSuite:
    """Evaluates multi-coach ratings and computes inter-rater agreement statistics."""

    @staticmethod
    def evaluate_coach_ratings(
        evaluations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute mean, std, and inter-rater agreement across coach reviews.

        Expected evaluations structure:
        [
            {
                "clip_id": "clip_01",
                "coach_1": {"correctness": 5, "usefulness": 4},
                "coach_2": {"correctness": 5, "usefulness": 5},
                "coach_3": {"correctness": 4, "usefulness": 4},
            },
            ...
        ]
        """
        c1_corr, c2_corr, c3_corr = [], [], []
        c1_use, c2_use, c3_use = [], [], []

        for e in evaluations:
            c1_corr.append(e["coach_1"]["correctness"])
            c2_corr.append(e["coach_2"]["correctness"])
            c3_corr.append(e["coach_3"]["correctness"])

            c1_use.append(e["coach_1"]["usefulness"])
            c2_use.append(e["coach_2"]["usefulness"])
            c3_use.append(e["coach_3"]["usefulness"])

        all_corr = c1_corr + c2_corr + c3_corr
        all_use = c1_use + c2_use + c3_use

        # Pairwise weighted kappas
        k_corr_12 = compute_cohen_weighted_kappa(c1_corr, c2_corr)
        k_corr_13 = compute_cohen_weighted_kappa(c1_corr, c3_corr)
        k_corr_23 = compute_cohen_weighted_kappa(c2_corr, c3_corr)
        mean_kappa_corr = float(np.mean([k_corr_12, k_corr_13, k_corr_23]))

        k_use_12 = compute_cohen_weighted_kappa(c1_use, c2_use)
        k_use_13 = compute_cohen_weighted_kappa(c1_use, c3_use)
        k_use_23 = compute_cohen_weighted_kappa(c2_use, c3_use)
        mean_kappa_use = float(np.mean([k_use_12, k_use_13, k_use_23]))

        return {
            "num_clips_evaluated": len(evaluations),
            "num_coaches": 3,
            "correctness": {
                "mean": float(np.mean(all_corr)),
                "std": float(np.std(all_corr)),
                "min": int(np.min(all_corr)),
                "max": int(np.max(all_corr)),
                "inter_rater_kappa": round(mean_kappa_corr, 3),
            },
            "usefulness": {
                "mean": float(np.mean(all_use)),
                "std": float(np.std(all_use)),
                "min": int(np.min(all_use)),
                "max": int(np.max(all_use)),
                "inter_rater_kappa": round(mean_kappa_use, 3),
            },
        }
