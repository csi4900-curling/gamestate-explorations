"""Three-way review cue from candidate-surrounding image motion."""


def classify_context(index, *, isolated_at=-0.20, comoving_at=0.20):
    if isolated_at >= comoving_at:
        raise ValueError("Cue bounds must leave an ambiguous interval")
    if index is None:
        return "abstain_insufficient_motion"
    if index <= isolated_at:
        return "isolated_motion_cue"
    if index >= comoving_at:
        return "comoving_context_review"
    return "ambiguous_context"
