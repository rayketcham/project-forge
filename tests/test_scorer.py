"""Tests for idea scoring."""

from project_forge.engine.scorer import is_high_value, score_summary, validate_score
from project_forge.models import Idea, IdeaCategory


def _make_idea(score: float) -> Idea:
    return Idea(
        name="Test",
        tagline="Test",
        description="Test",
        category=IdeaCategory.AUTOMATION,
        market_analysis="Test",
        feasibility_score=score,
        mvp_scope="Test",
    )


def test_validate_score_clamps_high():
    idea = _make_idea(0.95)
    idea.feasibility_score = 1.5  # bypass validator
    validated = validate_score(idea)
    assert validated.feasibility_score == 1.0


def test_validate_score_clamps_low():
    idea = _make_idea(0.1)
    idea.feasibility_score = -0.5  # bypass validator
    validated = validate_score(idea)
    assert validated.feasibility_score == 0.0


def test_is_high_value_above_threshold():
    assert is_high_value(_make_idea(0.8)) is True


def test_is_high_value_below_threshold():
    assert is_high_value(_make_idea(0.5)) is False


def test_is_high_value_custom_threshold():
    assert is_high_value(_make_idea(0.6), threshold=0.5) is True


def test_score_summary_tiers():
    assert "Excellent" in score_summary(_make_idea(0.95))
    assert "Strong" in score_summary(_make_idea(0.75))
    assert "Solid" in score_summary(_make_idea(0.55))
    assert "Speculative" in score_summary(_make_idea(0.35))
    assert "Moonshot" in score_summary(_make_idea(0.1))
