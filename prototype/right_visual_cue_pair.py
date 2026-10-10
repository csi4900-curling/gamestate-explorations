"""Non-decisional review tiers from two independently frozen visual cues."""


def visual_cue_pair(context_tier, patch_positive):
    if context_tier == "context_unavailable_review":
        return "context_unavailable_review"
    if context_tier not in ("clear_context_review", "context_cluttered_review"):
        raise ValueError("Unknown context tier")
    if not isinstance(patch_positive, bool):
        raise ValueError("Patch result must be boolean")
    if context_tier == "clear_context_review" and patch_positive:
        return "both_visual_cues_positive_review"
    if context_tier == "context_cluttered_review" and not patch_positive:
        return "both_visual_cues_weak_review"
    return "visual_cues_disagree_review"


def group_visual_priority(tiers):
    if not tiers:
        raise ValueError("Group has no proposal cues")
    if "both_visual_cues_positive_review" in tiers:
        return "contains_both_visual_cues_positive"
    if "visual_cues_disagree_review" in tiers:
        return "contains_visual_cue_disagreement"
    if "context_unavailable_review" in tiers:
        return "contains_unavailable_context"
    if set(tiers) == {"both_visual_cues_weak_review"}:
        return "all_visual_cues_weak_review"
    raise ValueError("Unknown proposal cue tier")
