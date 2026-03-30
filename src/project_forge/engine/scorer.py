"""Feasibility scoring for generated ideas."""

from project_forge.models import Idea


def validate_score(idea: Idea) -> Idea:
    """Validate and clamp the feasibility score."""
    idea.feasibility_score = max(0.0, min(1.0, idea.feasibility_score))
    return idea


def is_high_value(idea: Idea, threshold: float = 0.7) -> bool:
    """Check if an idea meets the auto-scaffold threshold."""
    return idea.feasibility_score >= threshold


def score_summary(idea: Idea) -> str:
    """Return a human-readable score summary."""
    score = idea.feasibility_score
    if score >= 0.9:
        tier = "Excellent"
    elif score >= 0.7:
        tier = "Strong"
    elif score >= 0.5:
        tier = "Solid"
    elif score >= 0.3:
        tier = "Speculative"
    else:
        tier = "Moonshot"
    return f"{tier} ({score:.2f})"
